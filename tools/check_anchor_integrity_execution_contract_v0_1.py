#!/usr/bin/env python3
"""WP2F: check recorded execution prerequisites, never attest an execution.

A fresh WP2E signature check authenticates only the existing verifier record.
Request, receipt, inputs and output are separately caller-pinned or hash-bound
DATA. They are not covered by that record signature. No verifier or observer
is executed, and no historical process observation is authenticated here.
"""
from __future__ import annotations

import argparse
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
PROFILE = 'single-record-execution-contract-v1'
PIN_NAMES = ('input', 'carriers', 'record_set', 'signatures', 'trust_policy', 'request', 'receipt')
SCHEMAS = {k: f'anchor_integrity_execution_{k}_v0_1.schema.json'
           for k in ('request', 'receipt', 'result', 'contract_report')}
STATUSES = {'consistent': 'LOCAL_EXECUTION_CONTRACT_CONSISTENT',
            'invalid': 'LOCAL_EXECUTION_CONTRACT_INVALID',
            'incomplete': 'LOCAL_EXECUTION_CONTRACT_INCOMPLETE'}
UNPERFORMED = (
    'verifier_execution_attestation', 'observer_identity_authentication',
    'observer_execution_attestation', 'request_precommitment_verification',
    'challenge_freshness_verification', 'process_isolation_verification',
    'implementation_closure_verification', 'runtime_execution_identity_verification',
    'semantic_support_verification', 'independent_anchor_admission',
    'cycle_anchor_classification', 'response_mode_recommendation',
    'verified_binding_coverage', 'verified_support_coverage',
)
ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
HASH_RE = re.compile(r'[0-9a-f]{64}\Z')
MAX_CONTRACT_BYTES = 524288


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def load_signature_checker() -> Any:
    """Only installed trusted code; no bundle-controlled module names or paths."""
    path = ROOT / 'tools/check_anchor_integrity_record_signatures_v0_1.py'
    spec = importlib.util.spec_from_file_location('anchor_wp2f_signature_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('installed_signature_checker_unavailable')
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def not_run() -> dict[str, Any]:
    return {'status': 'not_run', 'result': None,
            'reason': 'execution_contract_is_not_execution_attestation'}


class ExecutionSchemas:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.hashes: dict[str, str] = {}
        self.validators: dict[str, Any] = {}
        for role, filename in SCHEMAS.items():
            raw = (ROOT / 'schemas' / filename).read_bytes()
            schema = base.strict_json(raw)
            base._assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.validators[role] = jsonschema.Draft202012Validator(schema)
            self.hashes[filename] = digest(raw)

    def validate(self, role: str, value: Any) -> None:
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise self.base.BindingError('schema_invalid_execution_' + role)


class ExecutionReview:
    def __init__(self, signature: Any, binding_profile: str, trust_domain: str,
                 epoch: int, record_id: str, execution_id: str, challenge: str) -> None:
        for value in (record_id, execution_id):
            if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
                raise ValueError('invalid_external_selection')
        if not isinstance(challenge, str) or HASH_RE.fullmatch(challenge) is None:
            raise ValueError('invalid_external_challenge')
        self.signature = signature
        self.records = signature.load_record_checker()
        self.base = self.records.load_binding_checker()
        self.previous = signature.SignatureReview(self.records, self.base, binding_profile,
                                                  trust_domain, epoch)
        self.schemas = ExecutionSchemas(self.base)
        self.complete = False
        self.report = {
            'schema_version': 'anchor_integrity_execution_contract_report_v0_1',
            'work_package': 'WP2F', 'profile': PROFILE,
            'verification_scope': 'single_record_recorded_execution_byte_bindings',
            'candidate_status': 'diagnostic_only', 'authority_effect': 'none',
            'release_authority_activation': False, 'requested_checks_complete': False,
            'accepted_as_execution_evidence': False, 'accepted_as_semantic_support': False,
            'accepted_as_independent_anchor': False,
            'status': STATUSES['incomplete'], 'selected_record_id': record_id,
            'expected_execution_id': execution_id, 'expected_challenge': challenge,
            'expected_digests': {k: None for k in PIN_NAMES},
            'observed_digests': {k: None for k in PIN_NAMES},
            'signature_check': {'status': None, 'report_sha256': None, 'signer_result': None},
            'contract_check': not_run(), 'receipt_declaration': None,
            'checked_objects': [], 'issues': [],
            'unperformed_checks': {k: not_run() for k in UNPERFORMED},
            'implementation': {
                'checker_sha256': digest(Path(__file__).read_bytes()),
                'signature_checker_sha256': digest((ROOT / 'tools/check_anchor_integrity_record_signatures_v0_1.py').read_bytes()),
                'schema_sha256': self.schemas.hashes,
            },
        }

    def issue(self, code: str, object_id: str = 'execution', severity: str = 'invalid') -> None:
        self.report['issues'].append({'code': code, 'object_id': object_id, 'severity': severity})

    def require(self, condition: bool, code: str) -> None:
        if not condition:
            raise self.base.BindingError(code)

    def remember(self, role: str, path: str, raw: bytes) -> None:
        self.report['checked_objects'].append({'role': role, 'path': path,
                                               'sha256': digest(raw), 'size_bytes': len(raw)})

    def contract(self, reader: Any, path: str, expected: str, role: str) -> dict[str, Any]:
        raw = reader.read(path, 'wp2f.' + role)
        self.report['observed_digests'][role] = digest(raw)
        self.require(len(raw) <= MAX_CONTRACT_BYTES, role + '_size_limit')
        self.require(digest(raw) == expected, role + '_digest_mismatch')
        value = self.base.strict_json(raw)
        self.schemas.validate(role, value)
        self.remember(role, path, raw)
        return value

    def material(self, reader: Any, ref: dict[str, Any], role: str) -> bytes:
        raw = reader.read(ref['path'], 'wp2f.' + role)
        self.require(len(raw) == ref['size_bytes'], role + '_size_mismatch')
        self.require(digest(raw) == ref['sha256'], role + '_digest_mismatch')
        self.remember(role, ref['path'], raw)
        return raw

    def reserve(self, reader: Any, request: dict[str, Any], receipt: dict[str, Any]) -> None:
        for role in ('entrypoint', 'runtime_manifest'):
            reader.reserve(request[role]['path'], 'wp2f.' + role)
        for role, ref in request['inputs'].items():
            reader.reserve(ref['path'], 'wp2f.input.' + role)
        for role in ('stdout', 'stderr'):
            reader.reserve(receipt[role]['path'], 'wp2f.' + role)

    def run_signature(self, reader: Any, policy_reader: Any, paths: dict[str, str]) -> dict[str, Any] | None:
        """Same reader for the fresh WP2E chain and all new material bindings."""
        p = self.previous
        pins = self.report['expected_digests']
        for key in PIN_NAMES[:5]:
            p.report['expected_digests'][key] = pins[key]
        record_set = None
        try:
            policy = p.policy(policy_reader, paths['trust_policy'], pins['trust_policy'])
            manifest = p.bound_json(reader, paths['signatures'], pins['signatures'], 'manifest')
            self.require(manifest['record_set_binding'] == {'path': paths['record_set'], 'sha256': pins['record_set']},
                         'signature_manifest_record_set_mismatch')
            self.require(manifest['trust_policy_sha256'] == pins['trust_policy'], 'signature_manifest_policy_mismatch')
            self.base._index(manifest['signatures'], 'record_id')
            for entry in manifest['signatures']:
                reader.reserve(entry['path'], 'wp2e.signature:' + entry['record_id'])
            record_set = p.capture_previous(reader, paths['input'], paths['carriers'], paths['record_set'])
            if record_set is not None:
                p.authenticate(reader, policy, manifest, record_set, paths['input'])
        except self.base.BindingError as exc:
            p.issue(exc.code, 'bundle', exc.severity)
        result = p.finish()
        self.report['signature_check'] = {
            'status': result['status'], 'report_sha256': digest(self.signature.report_bytes(result)),
            'signer_result': result['signer_authentication']['result'],
        }
        for key in PIN_NAMES[:5]:
            self.report['observed_digests'][key] = result['observed_digests'][key]
        for issue in result['issues']:
            self.issue('base.' + issue['code'], issue['object_id'], issue['severity'])
        return record_set if result['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED' else None

    def compare(self, reader: Any, request: dict[str, Any], receipt: dict[str, Any], record_set: dict[str, Any]) -> None:
        rid = self.report['selected_record_id']
        entries = {x['record_id']: x for x in record_set['records']}
        if rid not in entries:
            raise self.base.BindingError('selected_signed_record_missing', 'incomplete')
        entry = entries[rid]
        # Only bytes retained by the successful base check, never a path reopen.
        raw = reader.cache[entry['path']]
        self.require(digest(raw) == entry['sha256'], 'retained_record_digest_mismatch')
        record = self.base.strict_json(raw)
        self.require(receipt['record_binding'] == {'record_id': rid, 'sha256': digest(raw)}, 'receipt_record_mismatch')
        self.require(receipt['request_sha256'] == self.report['expected_digests']['request'], 'receipt_request_mismatch')
        for key, expected in (('execution_id', self.report['expected_execution_id']),
                              ('challenge', self.report['expected_challenge'])):
            self.require(request[key] == receipt[key] == expected, 'external_' + key + '_mismatch')
        for key in ('subject', 'verifier'):
            self.require(request[key] == receipt[key] == record[key], key + '_mismatch')
        self.require(request['binding'] == record['binding'], 'request_binding_mismatch')
        self.require(request['invocation'] == receipt['invocation'], 'invocation_mismatch')
        env = request['invocation']['environment']
        self.require(len({v['name'] for v in env}) == len(env), 'duplicate_environment_name')
        ep = self.material(reader, request['entrypoint'], 'entrypoint')
        self.require(digest(ep) == request['verifier']['implementation_sha256'] == receipt['entrypoint_sha256'],
                     'entrypoint_identity_mismatch')
        runtime = self.material(reader, request['runtime_manifest'], 'runtime_manifest')
        self.require(digest(runtime) == receipt['runtime_manifest_sha256'], 'runtime_manifest_mismatch')
        expected_input = {'claim_text': record['binding']['claim_digest'],
                          'evidence_content': record['binding']['evidence_sha256'],
                          'source_content': record['binding']['source_sha256']}
        for role, expected in expected_input.items():
            data = self.material(reader, request['inputs'][role], 'input.' + role)
            self.require(digest(data) == expected == receipt['input_sha256'][role], 'execution_input_' + role + '_mismatch')
        stdout = self.material(reader, receipt['stdout'], 'stdout')
        stderr = self.material(reader, receipt['stderr'], 'stderr')
        self.require(len(stdout) <= request['limits']['max_stdout_bytes'], 'stdout_limit_exceeded')
        self.require(len(stderr) <= request['limits']['max_stderr_bytes'], 'stderr_limit_exceeded')
        process = receipt['process']
        self.report['receipt_declaration'] = {'observation_basis': receipt['observation_basis'],
                                               'process': process, 'recorded_result': None}
        if process['state'] != 'completed':
            self.issue('recorded_process_' + process['state'], rid, 'incomplete')
            return
        self.require(process['duration_ms'] <= request['limits']['timeout_ms'], 'recorded_duration_exceeds_limit')
        if not process['stdout_complete'] or not process['stderr_complete']:
            self.issue('recorded_stream_incomplete', rid, 'incomplete')
            return
        # stdout is data in one fixed output contract, never code or a command.
        output = self.base.strict_json(stdout)
        self.schemas.validate('result', output)
        for key in ('execution_id', 'challenge', 'subject', 'verifier', 'binding'):
            self.require(output[key] == request[key], 'stdout_' + key + '_mismatch')
        self.require(output['request_sha256'] == self.report['expected_digests']['request'], 'stdout_request_mismatch')
        self.require(output['verification'] == record['verification'], 'stdout_signed_record_result_mismatch')
        self.report['receipt_declaration']['recorded_result'] = output['verification']
        self.complete = True

    def finish(self) -> dict[str, Any]:
        if not self.complete and not self.report['issues']:
            self.issue('execution_contract_prerequisites_missing', severity='incomplete')
        self.report['issues'] = sorted({(i['severity'], i['object_id'], i['code']): i
                                       for i in self.report['issues']}.values(),
                                      key=lambda i: (i['severity'], i['object_id'], i['code']))
        issues = self.report['issues']
        state = ('invalid' if any(i['severity'] == 'invalid' for i in issues)
                 else 'incomplete' if issues else 'consistent')
        self.report['status'] = STATUSES[state]
        if state == 'consistent':
            self.report['contract_check'] = {'status': 'completed',
                                             'result': 'recorded_execution_bindings_match', 'reason': None}
        self.schemas.validate('contract_report', self.report)
        return self.report


def check_execution_contract(root: Path, *, paths: dict[str, str], expected_digests: dict[str, str],
                             trust_root: Path, binding_profile: str, signature_profile: str,
                             trust_domain: str, verification_time_epoch: int,
                             execution_profile: str, record_id: str,
                             execution_id: str, challenge: str) -> dict[str, Any]:
    signature = load_signature_checker()
    review = ExecutionReview(signature, binding_profile, trust_domain, verification_time_epoch,
                             record_id, execution_id, challenge)
    base = review.base
    try:
        review.require(execution_profile == PROFILE, 'unsupported_execution_profile')
        review.require(signature_profile == signature.PROFILE, 'unsupported_signature_profile')
        review.require(isinstance(paths, dict) and set(paths) == set(PIN_NAMES), 'invalid_path_roles')
        review.require(isinstance(expected_digests, dict) and set(expected_digests) == set(PIN_NAMES), 'invalid_expected_digest_roles')
        for name in PIN_NAMES:
            value = expected_digests[name]
            review.require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, 'invalid_expected_' + name + '_digest')
            base.safe_relative(paths[name])
            review.report['expected_digests'][name] = value
        try:
            a, b = Path(root).resolve(strict=True), Path(trust_root).resolve(strict=True)
        except FileNotFoundError as exc:
            raise base.BindingError('required_root_missing', 'incomplete') from exc
        review.require(not a.is_relative_to(b) and not b.is_relative_to(a), 'trust_root_not_separate_from_bundle')
        with base.BundleReader(root) as reader, base.BundleReader(trust_root) as policy_reader:
            aa, bb = os.fstat(reader.fd), os.fstat(policy_reader.fd)
            review.require((aa.st_dev, aa.st_ino) != (bb.st_dev, bb.st_ino), 'trust_root_aliases_bundle')
            request = review.contract(reader, paths['request'], expected_digests['request'], 'request')
            receipt = review.contract(reader, paths['receipt'], expected_digests['receipt'], 'receipt')
            review.reserve(reader, request, receipt)
            record_set = review.run_signature(reader, policy_reader, paths)
            if record_set is not None:
                review.compare(reader, request, receipt, record_set)
    except base.BindingError as exc:
        review.issue(exc.code, severity=exc.severity)
    return review.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-root', type=Path, required=True)
    parser.add_argument('--trust-root', type=Path, required=True)
    for name in PIN_NAMES:
        parser.add_argument('--' + name.replace('_', '-'), required=True)
        parser.add_argument('--expected-' + name.replace('_', '-') + '-sha256', required=True)
    parser.add_argument('--binding-profile', choices=('wp2a', 'wp2b-json-pointer-v1'), required=True)
    parser.add_argument('--signature-profile', choices=('pinned-ed25519-record-signers-v1',), required=True)
    parser.add_argument('--execution-profile', choices=(PROFILE,), required=True)
    parser.add_argument('--trust-domain', choices=('TEST', 'OPERATOR'), required=True)
    parser.add_argument('--verification-time-epoch', type=int, required=True)
    parser.add_argument('--record-id', required=True)
    parser.add_argument('--execution-id', required=True)
    parser.add_argument('--challenge', required=True)
    args = parser.parse_args(argv)
    try:
        report = check_execution_contract(
            args.bundle_root, paths={k: getattr(args, k) for k in PIN_NAMES},
            expected_digests={k: getattr(args, 'expected_' + k + '_sha256') for k in PIN_NAMES},
            trust_root=args.trust_root, binding_profile=args.binding_profile,
            signature_profile=args.signature_profile, trust_domain=args.trust_domain,
            verification_time_epoch=args.verification_time_epoch, execution_profile=args.execution_profile,
            record_id=args.record_id, execution_id=args.execution_id, challenge=args.challenge)
    except Exception as exc:
        print('Anchor execution-contract error: ' + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report_bytes(report))
    return {STATUSES['consistent']: 0, STATUSES['invalid']: 1, STATUSES['incomplete']: 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
