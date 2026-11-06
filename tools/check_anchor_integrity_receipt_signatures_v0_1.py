#!/usr/bin/env python3
"""WP2G: authenticate one exact execution-receipt statement, not an execution.

The unchanged WP2F/WP2E/WP2C/WP2A/WP2B chain is executed afresh on retained
bytes. A separately pinned observer policy authorizes a distinct signing key.
Receipt signature validity never establishes that the claimed capture occurred.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'pinned-ed25519-execution-observers-v1'
DOMAIN = 'PULSEMECH-ANCHOR-EXECUTION-RECEIPT-SIGNATURE-V1'
BASE_PINS = ('input', 'carriers', 'record_set', 'signatures', 'trust_policy', 'request', 'receipt')
PIN_NAMES = (*BASE_PINS, 'observer_policy', 'receipt_signature')
SCHEMAS = {
    'policy': 'anchor_integrity_observer_policy_v0_1.schema.json',
    'signature': 'anchor_integrity_execution_receipt_signature_v0_1.schema.json',
    'report': 'anchor_integrity_execution_receipt_signature_report_v0_1.schema.json',
}
STATUSES = {'verified': 'LOCAL_RECEIPT_SIGNATURE_VERIFIED',
            'invalid': 'LOCAL_RECEIPT_SIGNATURE_INVALID',
            'incomplete': 'LOCAL_RECEIPT_SIGNATURE_INCOMPLETE'}
UNPERFORMED = (
    'verifier_execution_attestation', 'observer_identity_authentication',
    'observer_execution_attestation', 'observer_policy_provenance_verification',
    'observer_key_custody_verification', 'observer_independence_verification',
    'request_precommitment_verification', 'challenge_freshness_verification',
    'trusted_clock_verification', 'historical_signing_time_verification',
    'online_revocation_check', 'policy_rollback_protection',
    'process_isolation_verification', 'implementation_closure_verification',
    'runtime_execution_identity_verification', 'semantic_support_verification',
    'independent_anchor_admission', 'cycle_anchor_classification',
    'response_mode_recommendation', 'verified_binding_coverage', 'verified_support_coverage',
)
MAX_POLICY_BYTES = 262144
MAX_SIGNATURE_BYTES = 16384
MAX_RECEIPT_BYTES = 524288
HASH_RE = re.compile(r'[0-9a-f]{64}\Z')
ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def load_execution_checker() -> Any:
    """Only the fixed installed module; evidence cannot select a program."""
    path = ROOT / 'tools/check_anchor_integrity_execution_contract_v0_1.py'
    spec = importlib.util.spec_from_file_location('anchor_wp2g_execution_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('installed_execution_checker_unavailable')
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def signing_bytes(observer_policy_sha256: str, record_policy_sha256: str,
                  key_id: str, receipt_bytes: bytes) -> bytes:
    """Pure Ed25519 with fixed application framing, not Ed25519ctx/ph.

    All prefix fields exclude NUL. The last field is the exact original receipt,
    including whitespace and final newline. No artifact-supplied signing input.
    """
    if (not isinstance(observer_policy_sha256, str) or
            HASH_RE.fullmatch(observer_policy_sha256) is None or
            not isinstance(record_policy_sha256, str) or
            HASH_RE.fullmatch(record_policy_sha256) is None or
            not isinstance(key_id, str) or ID_RE.fullmatch(key_id) is None or
            not isinstance(receipt_bytes, bytes) or len(receipt_bytes) > MAX_RECEIPT_BYTES):
        raise ValueError('invalid_receipt_signature_message_fields')
    return (DOMAIN.encode('ascii') + b'\0' + observer_policy_sha256.encode('ascii') + b'\0' +
            record_policy_sha256.encode('ascii') + b'\0' + key_id.encode('ascii') + b'\0' + receipt_bytes)


def not_run(reason: str = 'receipt_authentication_prerequisites_not_established') -> dict[str, Any]:
    return {'status': 'not_run', 'result': None, 'reason': reason}


def completed(result: str, reason: str | None = None) -> dict[str, Any]:
    return {'status': 'completed', 'result': result, 'reason': reason}


class ReceiptSchemas:
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
            raise self.base.BindingError('schema_invalid_receipt_signature_' + role)


class ReceiptReview:
    def __init__(self, execution: Any, binding_profile: str, trust_domain: str,
                 epoch: int, record_id: str, execution_id: str, challenge: str,
                 observer_id: str) -> None:
        if not isinstance(observer_id, str) or ID_RE.fullmatch(observer_id) is None:
            raise ValueError('invalid_expected_observer_id')
        self.execution = execution
        self.signature = execution.load_signature_checker()
        self.previous = execution.ExecutionReview(self.signature, binding_profile, trust_domain,
                                                   epoch, record_id, execution_id, challenge)
        self.base = self.previous.base
        self.schemas = ReceiptSchemas(self.base)
        self.report: dict[str, Any] = {
            'schema_version': 'anchor_integrity_execution_receipt_signature_report_v0_1',
            'work_package': 'WP2G', 'profile': PROFILE,
            'verification_scope': 'single_exact_receipt_signature_under_caller_pinned_observer_policy',
            'candidate_status': 'diagnostic_only', 'authority_effect': 'none',
            'release_authority_activation': False, 'requested_checks_complete': False,
            'accepted_as_execution_evidence': False, 'accepted_as_semantic_support': False,
            'accepted_as_independent_anchor': False, 'authenticated_receipt_statement': False,
            'status': STATUSES['incomplete'], 'trust_domain': trust_domain,
            'verification_time_epoch': epoch, 'time_source': 'caller_supplied_not_authenticated',
            'selected_record_id': record_id, 'expected_execution_id': execution_id,
            'expected_challenge': challenge, 'expected_observer_id': observer_id,
            'expected_digests': {k: None for k in PIN_NAMES},
            'observed_digests': {k: None for k in PIN_NAMES},
            'execution_contract_check': {'status': None, 'report_sha256': None,
                                          'signer_result': None, 'checked_object_count': None},
            'policy_id': None, 'observer_declaration': None, 'observation_basis': None,
            'key_id': None, 'public_key_sha256': None, 'signed_message_sha256': None,
            'observer_key_authorization': not_run(), 'receipt_signature_check': not_run(),
            'observer_statement_authentication': not_run(),
            'unperformed_checks': {k: not_run('outside_wp2g_receipt_statement_scope') for k in UNPERFORMED},
            'issues': [], 'implementation': {
                'checker_sha256': digest(Path(__file__).read_bytes()),
                'execution_checker_sha256': digest((ROOT / 'tools/check_anchor_integrity_execution_contract_v0_1.py').read_bytes()),
                'record_signature_checker_sha256': digest((ROOT / 'tools/check_anchor_integrity_record_signatures_v0_1.py').read_bytes()),
                'schema_sha256': self.schemas.hashes, 'crypto_backend': None,
            },
        }

    def require(self, condition: bool, code: str) -> None:
        if not condition:
            raise self.base.BindingError(code)

    def issue(self, code: str, severity: str = 'invalid') -> None:
        self.report['issues'].append({'code': code, 'severity': severity})

    def bound_json(self, reader: Any, path: str, role: str, limit: int) -> dict[str, Any]:
        pin = 'observer_policy' if role == 'policy' else 'receipt_signature'
        raw = reader.read(path, 'wp2g.' + pin)
        self.report['observed_digests'][pin] = digest(raw)
        self.require(len(raw) <= limit, pin + '_size_limit')
        self.require(digest(raw) == self.report['expected_digests'][pin], pin + '_digest_mismatch')
        value = self.base.strict_json(raw)
        self.schemas.validate(role, value)
        return value

    def policy(self, reader: Any, path: str) -> dict[str, Any]:
        policy = self.bound_json(reader, path, 'policy', MAX_POLICY_BYTES)
        self.require(policy['trust_domain'] == self.report['trust_domain'], 'observer_trust_domain_mismatch')
        self.require(policy['observer']['observer_id'] == self.report['expected_observer_id'],
                     'observer_policy_selection_mismatch')
        self.require(policy['record_signer_policy_sha256'] == self.report['expected_digests']['trust_policy'],
                     'observer_record_policy_mismatch')
        scope = {'record_id': self.report['selected_record_id'],
                 'execution_id': self.report['expected_execution_id'],
                 'challenge': self.report['expected_challenge'],
                 'request_sha256': self.report['expected_digests']['request']}
        self.require(policy['execution_scope'] == scope, 'observer_execution_scope_mismatch')
        self.base._index(policy['keys'], 'key_id')
        seen: set[bytes] = set()
        for key in policy['keys']:
            self.require(ID_RE.fullmatch(key['key_id']) is not None, 'observer_key_id_noncanonical')
            self.require(HASH_RE.fullmatch(key['public_key_hex']) is not None, 'observer_key_hex_noncanonical')
            raw = bytes.fromhex(key['public_key_hex'])
            self.require(self.signature.point_encoding_allowed(raw), 'observer_weak_or_noncanonical_key')
            self.require(raw not in seen, 'observer_public_key_reused')
            seen.add(raw)
            self.require(digest(raw) == key['public_key_sha256'], 'observer_public_key_digest_mismatch')
            self.require(key['not_before_epoch'] < key['not_after_epoch'], 'observer_validity_interval_invalid')
        self.report['policy_id'] = policy['policy_id']
        return policy

    def run_previous(self, reader: Any, policy_reader: Any, paths: dict[str, str]) -> tuple[Any, Any] | None:
        """Invoke WP2F's existing stages with the same retained-reader boundary."""
        p = self.previous
        p.report['expected_digests'] = {k: self.report['expected_digests'][k] for k in BASE_PINS}
        request = receipt = None
        try:
            request = p.contract(reader, paths['request'], p.report['expected_digests']['request'], 'request')
            receipt = p.contract(reader, paths['receipt'], p.report['expected_digests']['receipt'], 'receipt')
            p.reserve(reader, request, receipt)
            record_set = p.run_signature(reader, policy_reader, paths)
            if record_set is not None:
                p.compare(reader, request, receipt, record_set)
        except self.base.BindingError as exc:
            p.issue(exc.code, severity=exc.severity)
        result = p.finish()
        self.report['execution_contract_check'] = {
            'status': result['status'], 'report_sha256': digest(self.execution.report_bytes(result)),
            'signer_result': result['signature_check']['signer_result'],
            'checked_object_count': len(result['checked_objects']),
        }
        for key in BASE_PINS:
            self.report['observed_digests'][key] = result['observed_digests'][key]
        for item in result['issues']:
            self.issue('execution.' + item['code'], item['severity'])
        if result['status'] != 'LOCAL_EXECUTION_CONTRACT_CONSISTENT':
            return None
        return request, receipt

    def authenticate(self, reader: Any, policy_reader: Any, paths: dict[str, str],
                     policy: dict[str, Any], sig: dict[str, Any], receipt: dict[str, Any]) -> None:
        pins = self.report['expected_digests']
        # Use only bytes retained by the fresh WP2F/WP2E stages. Never reopen.
        raw = reader.cache[paths['receipt']]
        self.require(digest(raw) == pins['receipt'], 'retained_receipt_digest_mismatch')
        self.require(sig['receipt_sha256'] == pins['receipt'] and
                     sig['observer_policy_sha256'] == pins['observer_policy'] and
                     sig['record_signer_policy_sha256'] == pins['trust_policy'] and
                     sig['record_id'] == self.report['selected_record_id'] and
                     sig['execution_id'] == self.report['expected_execution_id'] and
                     sig['observer_id'] == self.report['expected_observer_id'], 'receipt_signature_subject_mismatch')
        self.require(receipt['subject'] == policy['subject'], 'observer_subject_mismatch')
        self.require(receipt['observer'] == policy['observer'], 'observer_tuple_mismatch')
        self.report['observer_declaration'] = receipt['observer']
        self.report['observation_basis'] = receipt['observation_basis']
        record_policy_raw = policy_reader.cache[paths['trust_policy']]
        self.require(digest(record_policy_raw) == pins['trust_policy'], 'retained_record_policy_digest_mismatch')
        record_policy = self.base.strict_json(record_policy_raw)
        # Compare decoded key material, not spellings accepted by an upstream schema.
        record_keys = {bytes.fromhex(k['public_key_hex']) for k in record_policy['keys']}
        self.require(all(bytes.fromhex(k['public_key_hex']) not in record_keys for k in policy['keys']),
                     'observer_key_reuses_verifier_key')
        key = next((k for k in policy['keys'] if k['key_id'] == sig['key_id']), None)
        self.report['key_id'] = sig['key_id']
        denial = None
        if key is None:
            denial = 'observer_key_not_authorized'
        elif key['state'] != 'active':
            denial = 'observer_key_revoked'
        elif not key['not_before_epoch'] <= self.report['verification_time_epoch'] < key['not_after_epoch']:
            denial = 'observer_key_outside_validity'
        elif key['verifier'] != receipt['verifier']:
            denial = 'observer_verifier_scope_mismatch'
        else:
            # WP2F has just matched stdout/request/record; use its retained request.
            request = self.base.strict_json(reader.cache[paths['request']])
            recorded_result = self.previous.report['receipt_declaration']['recorded_result']['result']
            if request['binding']['relation_type'] not in key['relation_types']:
                denial = 'observer_relation_scope_mismatch'
            elif recorded_result not in key['results']:
                denial = 'observer_result_scope_mismatch'
            elif receipt['observation_basis'] not in key['observation_bases']:
                denial = 'observer_observation_basis_not_authorized'
        if denial is not None:
            self.report['observer_key_authorization'] = completed('denied', denial)
            raise self.base.BindingError(denial)
        self.report['observer_key_authorization'] = completed('authorized')
        self.report['public_key_sha256'] = key['public_key_sha256']
        message = signing_bytes(pins['observer_policy'], pins['trust_policy'], sig['key_id'], raw)
        self.report['signed_message_sha256'] = digest(message)
        backend = self.signature.OpenSSLVerifier()
        self.report['implementation']['crypto_backend'] = backend.identity
        valid = backend.verify(bytes.fromhex(key['public_key_hex']), bytes.fromhex(sig['signature_hex']), message)
        self.report['receipt_signature_check'] = completed('valid' if valid else 'invalid')
        self.require(valid, 'execution_receipt_signature_invalid')

    def finish(self) -> dict[str, Any]:
        complete = (self.report['execution_contract_check']['status'] == 'LOCAL_EXECUTION_CONTRACT_CONSISTENT'
                    and self.report['observer_key_authorization']['result'] == 'authorized'
                    and self.report['receipt_signature_check']['result'] == 'valid')
        if not self.report['issues'] and not complete:
            self.issue('receipt_authentication_prerequisites_missing', 'incomplete')
        self.report['issues'] = sorted({(v['severity'], v['code']): v for v in self.report['issues']}.values(),
                                      key=lambda v: (v['severity'], v['code']))
        state = ('invalid' if any(v['severity'] == 'invalid' for v in self.report['issues'])
                 else 'incomplete' if self.report['issues'] else 'verified')
        self.report['status'] = STATUSES[state]
        if state == 'verified':
            self.report['authenticated_receipt_statement'] = True
            label = ('test_key_receipt_signature_verified' if self.report['trust_domain'] == 'TEST'
                     else 'authorized_key_receipt_signature_verified')
            self.report['observer_statement_authentication'] = completed(label)
        self.schemas.validate('report', self.report)
        return self.report


def check_receipt_signature(root: Path, *, paths: dict[str, str], expected_digests: dict[str, str],
                            trust_root: Path, observer_trust_root: Path,
                            binding_profile: str, signature_profile: str, execution_profile: str,
                            receipt_signature_profile: str, trust_domain: str,
                            verification_time_epoch: int, record_id: str,
                            execution_id: str, challenge: str, observer_id: str) -> dict[str, Any]:
    execution = load_execution_checker()
    review = ReceiptReview(execution, binding_profile, trust_domain, verification_time_epoch,
                           record_id, execution_id, challenge, observer_id)
    base = review.base
    try:
        review.require(receipt_signature_profile == PROFILE, 'unsupported_receipt_signature_profile')
        review.require(execution_profile == execution.PROFILE, 'unsupported_execution_profile')
        review.require(signature_profile == review.signature.PROFILE, 'unsupported_record_signature_profile')
        review.require(isinstance(paths, dict) and set(paths) == set(PIN_NAMES), 'invalid_path_roles')
        review.require(isinstance(expected_digests, dict) and set(expected_digests) == set(PIN_NAMES), 'invalid_expected_digest_roles')
        for name in PIN_NAMES:
            value = expected_digests[name]
            review.require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None,
                           'invalid_expected_' + name + '_digest')
            base.safe_relative(paths[name])
            review.report['expected_digests'][name] = value
        roots = (Path(root), Path(trust_root), Path(observer_trust_root))
        try:
            resolved = [p.resolve(strict=True) for p in roots]
        except FileNotFoundError as exc:
            raise base.BindingError('required_root_missing', 'incomplete') from exc
        for i in range(3):
            for j in range(i):
                review.require(not resolved[i].is_relative_to(resolved[j]) and
                               not resolved[j].is_relative_to(resolved[i]), 'policy_roots_not_disjoint')
        with ExitStack() as stack:
            readers = [stack.enter_context(base.BundleReader(p)) for p in roots]
            inode_ids = [(os.fstat(r.fd).st_dev, os.fstat(r.fd).st_ino) for r in readers]
            review.require(len(set(inode_ids)) == 3, 'policy_root_inode_alias')
            reader, policy_reader, observer_reader = readers
            # Reserve before the upstream chain so no input/source/stream can occupy this role.
            reader.reserve(paths['receipt_signature'], 'wp2g.receipt_signature')
            policy = review.policy(observer_reader, paths['observer_policy'])
            sig = review.bound_json(reader, paths['receipt_signature'], 'signature', MAX_SIGNATURE_BYTES)
            previous = review.run_previous(reader, policy_reader, paths)
            if previous is not None:
                _, receipt = previous
                review.authenticate(reader, policy_reader, paths, policy, sig, receipt)
    except base.BindingError as exc:
        review.issue(exc.code, exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle-root', 'trust-root', 'observer-trust-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in PIN_NAMES:
        parser.add_argument('--' + name.replace('_', '-'), required=True)
        parser.add_argument('--expected-' + name.replace('_', '-') + '-sha256', required=True)
    parser.add_argument('--binding-profile', choices=('wp2a', 'wp2b-json-pointer-v1'), required=True)
    parser.add_argument('--signature-profile', choices=('pinned-ed25519-record-signers-v1',), required=True)
    parser.add_argument('--execution-profile', choices=('single-record-execution-contract-v1',), required=True)
    parser.add_argument('--receipt-signature-profile', choices=(PROFILE,), required=True)
    parser.add_argument('--trust-domain', choices=('TEST', 'OPERATOR'), required=True)
    parser.add_argument('--verification-time-epoch', type=int, required=True)
    for name in ('record-id', 'execution-id', 'challenge', 'observer-id'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        result = check_receipt_signature(
            args.bundle_root, paths={k: getattr(args, k) for k in PIN_NAMES},
            expected_digests={k: getattr(args, 'expected_' + k + '_sha256') for k in PIN_NAMES},
            trust_root=args.trust_root, observer_trust_root=args.observer_trust_root,
            binding_profile=args.binding_profile, signature_profile=args.signature_profile,
            execution_profile=args.execution_profile, receipt_signature_profile=args.receipt_signature_profile,
            trust_domain=args.trust_domain, verification_time_epoch=args.verification_time_epoch,
            record_id=args.record_id, execution_id=args.execution_id, challenge=args.challenge,
            observer_id=args.observer_id)
    except Exception as exc:
        print('Anchor receipt-signature error: ' + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report_bytes(result))
    return {STATUSES['verified']: 0, STATUSES['invalid']: 1, STATUSES['incomplete']: 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
