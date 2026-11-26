#!/usr/bin/env python3
"""WP2E: authenticate exact verifier-record statements under a pinned key policy.

The policy is a caller-supplied trust root outside the evidence bundle. A
signature proves neither real-world identity, verifier execution, semantic
truth nor anchor independence. Existing WP2A/B/C/D modules remain unchanged.
Only a fixed installed OpenSSL 3.x verifier is invoked, without a shell,
network, inherited provider configuration or artifact-selected executable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'pinned-ed25519-record-signers-v1'
DOMAIN = 'PULSEMECH-ANCHOR-RECORD-SIGNATURE-V1'
OPENSSL = '/usr/bin/openssl'
MAX_SIGNATURES = 128
MAX_POLICY_BYTES = 262144
MAX_SIGNATURE_BYTES = 16384
MAX_AUTH_SECONDS = 30.0
CALL_TIMEOUT = 5.0
SCHEMAS = {
    'policy': 'anchor_integrity_signer_policy_v0_1.schema.json',
    'manifest': 'anchor_integrity_record_signatures_v0_1.schema.json',
    'signature': 'anchor_integrity_record_signature_v0_1.schema.json',
    'report': 'anchor_integrity_record_signature_report_v0_1.schema.json',
}
STATUSES = {'verified': 'LOCAL_RECORD_SIGNATURES_VERIFIED',
            'invalid': 'LOCAL_RECORD_SIGNATURES_INVALID',
            'incomplete': 'LOCAL_RECORD_SIGNATURES_INCOMPLETE'}
UNPERFORMED = (
    'external_issuer_identity_verification', 'key_custody_verification',
    'trust_policy_authorization_verification', 'trusted_clock_verification',
    'historical_signing_time_verification', 'online_revocation_check',
    'verifier_execution_attestation', 'source_identity_authentication',
    'semantic_support_verification', 'independent_anchor_admission',
    'cycle_anchor_classification', 'response_mode_recommendation',
    'claim_set_completeness', 'verified_binding_coverage', 'verified_support_coverage',
)
# RFC 8032 section 7.1, test 2. Public verification material, not a secret.
KAT_PUBLIC = bytes.fromhex('3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c')
KAT_MESSAGE = bytes.fromhex('72')
KAT_SIGNATURE = bytes.fromhex(
    '92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da'
    '085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00')
SPKI_PREFIX = bytes.fromhex('302a300506032b6570032100')
FIELD_PRIME = 2**255 - 19
SCALAR_ORDER = 2**252 + 27742317777372353535851937790883648493
# Public Edwards25519 torsion y-coordinates (both x signs are rejected).
# Numeric group constants, cross-checked against libsodium 1.0.18 ref10,
# ge25519_has_small_order. No elliptic-curve arithmetic is implemented here.
SMALL_ORDER_Y = frozenset((
    0, 1, FIELD_PRIME - 1,
    2707385501144840649318225287225658788936804267575313519463743609750303402022,
    55188659117513257062467267217118295137698188065244968500265048394206261417927,
))


def point_encoding_allowed(encoded: bytes) -> bool:
    """Reject noncanonical y and all small-order encodings before OpenSSL.

    This is not an independent curve/main-subgroup membership algorithm.
    OpenSSL still performs the signature equation and point decoding.
    """
    if not isinstance(encoded, bytes) or len(encoded) != 32:
        return False
    y = int.from_bytes(encoded, 'little') & ((1 << 255) - 1)
    return y < FIELD_PRIME and y not in SMALL_ORDER_Y



def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def load_record_checker() -> Any:
    path = ROOT / 'tools' / 'check_anchor_integrity_verifier_records_v0_1.py'
    spec = importlib.util.spec_from_file_location('anchor_records_wp2e_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('record_checker_unavailable')
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def signing_bytes(policy_sha256: str, key_id: str, record_bytes: bytes) -> bytes:
    """Reconstructed fixed-domain message, not caller-supplied signing text.

    policy SHA-256 and key_id are strict ASCII with no NUL. The final field is
    the entire original record file, including whitespace and final newline.
    This is application domain separation, not Ed25519ctx or Ed25519ph.
    """
    if (not isinstance(policy_sha256, str) or
            re.fullmatch(r'[0-9a-f]{64}', policy_sha256) is None or
            not isinstance(key_id, str) or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', key_id) is None or
            not isinstance(record_bytes, bytes) or len(record_bytes) > 8 * 1024 * 1024):
        raise ValueError('invalid_signature_message_fields')
    return (DOMAIN.encode('ascii') + b'\0' + policy_sha256.encode('ascii') + b'\0' +
            key_id.encode('ascii') + b'\0' + record_bytes)


class OpenSSLVerifier:
    """Fixed local backend. Temporary public data only; never a private key.

    The binary, provider and OS are trusted installation components. Its hash
    is an observation, not an attestation of the complete crypto/host closure.
    """
    def __init__(self) -> None:
        self.deadline = time.monotonic() + MAX_AUTH_SECONDS
        self.env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C',
                    'OPENSSL_CONF': '/dev/null'}
        version = self._run(['version'], capture=True)
        text = version.stdout.decode('ascii', errors='strict').strip()
        if version.returncode != 0 or len(text) > 256 or not re.match(r'^OpenSSL 3\.[0-9]+\.', text):
            raise RuntimeError('unsupported_openssl_backend')
        binary_hash = digest(Path(OPENSSL).read_bytes())
        if not self.verify(KAT_PUBLIC, KAT_SIGNATURE, KAT_MESSAGE):
            raise RuntimeError('openssl_positive_self_test_failed')
        altered = bytes([KAT_SIGNATURE[0] ^ 1]) + KAT_SIGNATURE[1:]
        if self.verify(KAT_PUBLIC, altered, KAT_MESSAGE):
            raise RuntimeError('openssl_negative_self_test_failed')
        self.identity = {'path': OPENSSL, 'binary_sha256': binary_hash,
                         'version': text, 'suite': 'ed25519',
                         'known_answer_self_test': 'passed'}

    def _run(self, args: list[str], *, capture: bool = False,
             cwd: str = '/tmp') -> subprocess.CompletedProcess[bytes]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError('signature_verification_time_budget')
        return subprocess.run([OPENSSL, *args], shell=False, cwd=cwd,
                              env=self.env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, check=False,
                              timeout=min(CALL_TIMEOUT, remaining), close_fds=True)

    def verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool:
        if (len(public_key) != 32 or len(signature) != 64 or
                len(message) > 8 * 1024 * 1024 + 256):
            raise ValueError('signature_backend_input_size')
        if (not point_encoding_allowed(public_key) or
                not point_encoding_allowed(signature[:32]) or
                not 0 < int.from_bytes(signature[32:], 'little') < SCALAR_ORDER):
            return False
        # Ed25519 in OpenSSL 3.0 requires a seekable raw message input. Never
        # forward source paths or environment settings to the child process.
        with tempfile.TemporaryDirectory(prefix='anchor-wp2e-', dir='/tmp') as tmp:
            root = Path(tmp)
            for name, data in (('key.der', SPKI_PREFIX + public_key),
                               ('signature.bin', signature), ('message.bin', message)):
                with (root / name).open('xb') as stream:
                    stream.write(data)
            result = self._run(['pkeyutl', '-verify', '-pubin', '-keyform', 'DER',
                                '-inkey', 'key.der', '-rawin', '-in', 'message.bin',
                                '-sigfile', 'signature.bin', '-provider', 'default'], cwd=tmp)
            if result.returncode not in (0, 1):
                raise RuntimeError('openssl_verification_backend_failure')
            return result.returncode == 0


class SignatureSchemas:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.hashes: dict[str, str] = {}
        self.validators: dict[str, Any] = {}
        for role, name in SCHEMAS.items():
            raw = (ROOT / 'schemas' / name).read_bytes()
            schema = base.strict_json(raw)
            base._assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.validators[role] = jsonschema.Draft202012Validator(schema)
            self.hashes[name] = digest(raw)

    def validate(self, role: str, value: Any) -> None:
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise self.base.BindingError('schema_invalid_signature_' + role)


def not_run(reason: str = 'prerequisites_not_established') -> dict[str, Any]:
    return {'status': 'not_run', 'result': None, 'reason': reason}


def completed(result: str, reason: str | None = None) -> dict[str, Any]:
    return {'status': 'completed', 'result': result, 'reason': reason}


class SignatureReview:
    def __init__(self, records: Any, base: Any, binding_profile: str,
                 trust_domain: str, verification_time_epoch: int) -> None:
        if trust_domain not in ('TEST', 'OPERATOR'):
            raise ValueError('invalid_requested_trust_domain')
        if type(verification_time_epoch) is not int or not 0 <= verification_time_epoch <= 253402300799:
            raise ValueError('invalid_verification_time')
        self.records = records
        self.base = base
        self.previous = records.RecordReview(base, binding_profile)
        self.schemas = SignatureSchemas(base)
        impl = self.previous.report['implementation']
        self.report: dict[str, Any] = {
            'schema_version': 'anchor_integrity_record_signature_report_v0_1',
            'work_package': 'WP2E', 'profile': PROFILE,
            'binding_profile': binding_profile,
            'verification_scope': 'exact_record_signatures_under_caller_pinned_policy',
            'candidate_status': 'diagnostic_only', 'authority_effect': 'none',
            'release_authority_activation': False, 'requested_checks_complete': False,
            'accepted_as_semantic_support': False, 'accepted_as_independent_anchor': False,
            'trust_policy_is_external_trust_root': True, 'trust_domain': trust_domain,
            'verification_time_epoch': verification_time_epoch,
            'time_source': 'caller_supplied_not_authenticated',
            'status': STATUSES['incomplete'],
            'expected_digests': {k: None for k in ('input', 'carriers', 'record_set', 'signatures', 'trust_policy')},
            'observed_digests': {k: None for k in ('input', 'carriers', 'record_set', 'signatures', 'trust_policy')},
            'policy_id': None, 'record_check': {'status': None, 'report_sha256': None},
            'signer_authentication': not_run(),
            'counts': {k: None for k in ('required_records', 'listed_signatures', 'admitted_records')},
            'records': [], 'issues': [],
            'unperformed_checks': {k: not_run('outside_wp2e_pinned_signer_scope') for k in UNPERFORMED},
            'implementation': {
                'checker_sha256': digest(Path(__file__).read_bytes()),
                'record_checker_sha256': impl['checker_sha256'],
                'binding_checker_sha256': impl['binding_checker_sha256'],
                'json_pointer_module_sha256': impl['json_pointer_module_sha256'],
                'schema_sha256': {**impl['schema_sha256'], **self.schemas.hashes},
                'crypto_backend': None,
            },
        }

    def issue(self, code: str, object_id: str, severity: str = 'invalid') -> None:
        self.report['issues'].append({'code': code, 'object_id': object_id, 'severity': severity})

    def bound_json(self, reader: Any, path: str, expected: str,
                   role: str, limit: int = 8 * 1024 * 1024) -> dict[str, Any]:
        raw = reader.read(path, 'wp2e.' + role)
        key = {'policy': 'trust_policy', 'manifest': 'signatures'}.get(role)
        if key is not None:
            self.report['observed_digests'][key] = digest(raw)
        if len(raw) > limit:
            raise self.base.BindingError(role + '_size_limit')
        if digest(raw) != expected:
            raise self.base.BindingError(role + '_digest_mismatch')
        value = self.base.strict_json(raw)
        self.schemas.validate(role, value)
        return value

    def policy(self, reader: Any, path: str, expected: str) -> dict[str, Any]:
        policy = self.bound_json(reader, path, expected, 'policy', MAX_POLICY_BYTES)
        if policy['trust_domain'] != self.report['trust_domain']:
            raise self.base.BindingError('trust_domain_mismatch')
        self.base._index(policy['keys'], 'key_id')
        seen: set[str] = set()
        for key in policy['keys']:
            raw = bytes.fromhex(key['public_key_hex'])
            if not point_encoding_allowed(raw):
                raise self.base.BindingError('policy_weak_or_noncanonical_key')
            if key['public_key_hex'] in seen:
                raise self.base.BindingError('policy_public_key_reused')
            seen.add(key['public_key_hex'])
            if digest(raw) != key['public_key_sha256']:
                raise self.base.BindingError('policy_public_key_digest_mismatch')
            if key['not_before_epoch'] >= key['not_after_epoch']:
                raise self.base.BindingError('policy_validity_interval_invalid')
        self.report['policy_id'] = policy['policy_id']
        return policy

    def capture_previous(self, reader: Any, input_path: str, carriers_path: str,
                         record_set_path: str) -> dict[str, Any] | None:
        pins = self.report['expected_digests']
        for k in ('input', 'carriers', 'record_set'):
            self.previous.report['expected_digests'][k] = pins[k]
        record_set = None
        try:
            record_set = self.previous.bound_set(reader, record_set_path, pins['record_set'])
            if len(record_set['records']) > MAX_SIGNATURES:
                raise self.base.BindingError('signature_record_limit')
            self.previous.prepare(reader, record_set, input_path=input_path, input_digest=pins['input'],
                                  carriers_path=carriers_path, carriers_digest=pins['carriers'])
            if self.previous.run_base(reader, input_path, pins['input'], carriers_path, pins['carriers']):
                self.previous.records(reader, record_set, input_path)
        except self.base.BindingError as exc:
            self.previous.issue(exc.code, 'bundle', exc.severity)
        result = self.previous.finish()
        self.report['record_check'] = {'status': result['status'],
                                      'report_sha256': digest(self.records.report_bytes(result))}
        for k, p in (('input', input_path), ('carriers', carriers_path), ('record_set', record_set_path)):
            if p in reader.cache:
                self.report['observed_digests'][k] = digest(reader.cache[p])
        for issue in result['issues']:
            self.issue('base.' + issue['code'], issue['object_id'], issue['severity'])
        return record_set if result['status'] == 'LOCAL_RECORD_BINDINGS_CONSISTENT' else None

    def authenticate(self, reader: Any, policy: dict[str, Any], manifest: dict[str, Any],
                     record_set: dict[str, Any], input_path: str) -> None:
        inp = self.previous.cached_json(reader, input_path)
        if policy['subject'] != inp['subject']:
            raise self.base.BindingError('policy_subject_mismatch')
        records = {r['record_id']: r for r in record_set['records']}
        signatures = self.base._index(manifest['signatures'], 'record_id')
        keys = {k['key_id']: k for k in policy['keys']}
        self.report['counts'].update(required_records=len(records), listed_signatures=len(signatures), admitted_records=0)
        for name in sorted(signatures.keys() - records.keys()):
            self.issue('orphan_signature', name)
        if not records:
            self.issue('no_records_to_authenticate', 'records', 'incomplete')
            return
        backend = None
        for record_id, entry in sorted(records.items()):
            row = {'record_id': record_id, 'record_sha256': entry['sha256'],
                   'signature_sha256': None, 'key_id': None, 'public_key_sha256': None,
                   'signed_message_sha256': None, 'signature_check': not_run(),
                   'policy_check': not_run(), 'admitted_under_policy': False,
                   'accepted_as_semantic_support': False, 'accepted_as_independent_anchor': False}
            self.report['records'].append(row)
            try:
                if record_id not in signatures:
                    raise self.base.BindingError('signature_not_listed', 'incomplete')
                selected = signatures[record_id]
                raw_sig = reader.read(selected['path'], 'wp2e.signature:' + record_id)
                row['signature_sha256'] = digest(raw_sig)
                if len(raw_sig) > MAX_SIGNATURE_BYTES:
                    raise self.base.BindingError('signature_size_limit')
                if digest(raw_sig) != selected['sha256']:
                    raise self.base.BindingError('signature_digest_mismatch')
                sig = self.base.strict_json(raw_sig)
                self.schemas.validate('signature', sig)
                if (sig['record_id'] != record_id or sig['record_sha256'] != entry['sha256'] or
                        sig['trust_policy_sha256'] != self.report['expected_digests']['trust_policy']):
                    raise self.base.BindingError('signature_subject_mismatch')
                row['key_id'] = sig['key_id']
                key = keys.get(sig['key_id'])
                denial = None
                record_raw = reader.cache[entry['path']]
                record = self.previous.cached_json(reader, entry['path'])
                epoch = self.report['verification_time_epoch']
                if key is None:
                    denial = 'signer_key_not_authorized'
                elif key['state'] != 'active':
                    denial = 'signer_key_revoked'
                elif not key['not_before_epoch'] <= epoch < key['not_after_epoch']:
                    denial = 'signer_key_outside_validity'
                elif key['verifier'] != record['verifier']:
                    denial = 'signer_verifier_scope_mismatch'
                elif record['binding']['relation_type'] not in key['relation_types']:
                    denial = 'signer_relation_scope_mismatch'
                elif record['verification']['result'] not in key['results']:
                    denial = 'signer_result_scope_mismatch'
                if denial:
                    row['policy_check'] = completed('denied', denial)
                    raise self.base.BindingError(denial)
                row['policy_check'] = completed('authorized')
                row['public_key_sha256'] = key['public_key_sha256']
                message = signing_bytes(sig['trust_policy_sha256'], sig['key_id'], record_raw)
                row['signed_message_sha256'] = digest(message)
                if backend is None:
                    backend = OpenSSLVerifier()
                    self.report['implementation']['crypto_backend'] = backend.identity
                valid = backend.verify(bytes.fromhex(key['public_key_hex']),
                                       bytes.fromhex(sig['signature_hex']), message)
                row['signature_check'] = completed('valid' if valid else 'invalid')
                if not valid:
                    raise self.base.BindingError('record_signature_invalid')
                row['admitted_under_policy'] = True
                self.report['counts']['admitted_records'] += 1
            except self.base.BindingError as exc:
                if row['signature_check']['status'] == 'not_run':
                    row['signature_check']['reason'] = exc.code
                self.issue(exc.code, record_id, exc.severity)

    def finish(self) -> dict[str, Any]:
        rows = self.report['records']
        issues = self.report['issues']
        counts = self.report['counts']
        complete = (self.report['record_check']['status'] == 'LOCAL_RECORD_BINDINGS_CONSISTENT' and
                    counts['required_records'] is not None and counts['required_records'] > 0 and
                    counts['required_records'] == counts['listed_signatures'] == counts['admitted_records'] == len(rows) and
                    all(r['admitted_under_policy'] for r in rows))
        if not issues and not complete:
            self.issue('authentication_prerequisites_incomplete', 'records', 'incomplete')
        self.report['issues'] = sorted({(x['severity'], x['object_id'], x['code']): x for x in issues}.values(),
                                      key=lambda x: (x['severity'], x['object_id'], x['code']))
        severities = {x['severity'] for x in issues}
        state = 'invalid' if 'invalid' in severities else 'incomplete' if issues else 'verified'
        self.report['status'] = STATUSES[state]
        if state == 'verified':
            result = 'test_key_signatures_verified' if self.report['trust_domain'] == 'TEST' else 'authorized_key_signatures_verified'
            self.report['signer_authentication'] = completed(result)
        self.schemas.validate('report', self.report)
        return self.report


def verify_signatures(root: Path, input_path: str, expected_input_sha256: str,
                      carriers_path: str, expected_carriers_sha256: str,
                      record_set_path: str, expected_record_set_sha256: str,
                      signatures_path: str, expected_signatures_sha256: str, *,
                      trust_root: Path, trust_policy_path: str, expected_trust_policy_sha256: str,
                      binding_profile: str, signature_profile: str,
                      trust_domain: str, verification_time_epoch: int) -> dict[str, Any]:
    records = load_record_checker()
    base = records.load_binding_checker()
    review = SignatureReview(records, base, binding_profile, trust_domain, verification_time_epoch)
    try:
        if signature_profile != PROFILE:
            raise base.BindingError('unsupported_signature_profile')
        for key, value in (('input', expected_input_sha256), ('carriers', expected_carriers_sha256),
                           ('record_set', expected_record_set_sha256), ('signatures', expected_signatures_sha256),
                           ('trust_policy', expected_trust_policy_sha256)):
            if not isinstance(value, str) or base.HASH_RE.fullmatch(value) is None:
                raise base.BindingError('invalid_expected_' + key + '_digest')
            review.report['expected_digests'][key] = value
        try:
            bundle_location, trust_location = Path(root).resolve(strict=True), Path(trust_root).resolve(strict=True)
        except FileNotFoundError as exc:
            raise base.BindingError('required_root_missing', 'incomplete') from exc
        if bundle_location.is_relative_to(trust_location) or trust_location.is_relative_to(bundle_location):
            raise base.BindingError('trust_root_not_separate_from_bundle')
        with base.BundleReader(root) as reader, base.BundleReader(trust_root) as policy_reader:
            a, b = os.fstat(reader.fd), os.fstat(policy_reader.fd)
            if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
                raise base.BindingError('trust_root_aliases_bundle')
            policy = review.policy(policy_reader, trust_policy_path, expected_trust_policy_sha256)
            manifest = review.bound_json(reader, signatures_path, expected_signatures_sha256, 'manifest')
            if manifest['record_set_binding'] != {'path': record_set_path, 'sha256': expected_record_set_sha256}:
                raise base.BindingError('signature_manifest_record_set_mismatch')
            if manifest['trust_policy_sha256'] != expected_trust_policy_sha256:
                raise base.BindingError('signature_manifest_policy_mismatch')
            base._index(manifest['signatures'], 'record_id')
            for entry in manifest['signatures']:
                reader.reserve(entry['path'], 'wp2e.signature:' + entry['record_id'])
            record_set = review.capture_previous(reader, input_path, carriers_path, record_set_path)
            if record_set is not None:
                review.authenticate(reader, policy, manifest, record_set, input_path)
    except base.BindingError as exc:
        review.issue(exc.code, 'bundle', exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-root', type=Path, required=True)
    for name in ('input', 'carriers', 'record-set', 'signatures'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--expected-' + name + '-sha256', required=True)
    parser.add_argument('--trust-root', type=Path, required=True)
    parser.add_argument('--trust-policy', required=True)
    parser.add_argument('--expected-trust-policy-sha256', required=True)
    parser.add_argument('--binding-profile', choices=('wp2a', 'wp2b-json-pointer-v1'), required=True)
    parser.add_argument('--signature-profile', choices=(PROFILE,), required=True)
    parser.add_argument('--trust-domain', choices=('TEST', 'OPERATOR'), required=True)
    parser.add_argument('--verification-time-epoch', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_signatures(
            args.bundle_root, args.input, args.expected_input_sha256,
            args.carriers, args.expected_carriers_sha256, args.record_set, args.expected_record_set_sha256,
            args.signatures, args.expected_signatures_sha256,
            trust_root=args.trust_root, trust_policy_path=args.trust_policy,
            expected_trust_policy_sha256=args.expected_trust_policy_sha256,
            binding_profile=args.binding_profile, signature_profile=args.signature_profile,
            trust_domain=args.trust_domain, verification_time_epoch=args.verification_time_epoch)
    except Exception as exc:
        print('Anchor signature checker error: ' + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report_bytes(report))
    return {STATUSES['verified']: 0, STATUSES['invalid']: 1, STATUSES['incomplete']: 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
