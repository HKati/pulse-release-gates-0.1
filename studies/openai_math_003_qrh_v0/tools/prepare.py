"""Create a new run configuration and external local-operator trust anchor.

The generated anchor is a reviewable starting trust configuration, not a claim
that an independent institution has approved the code or collector identity.
The private Ed25519 seed is created outside the evidence bundle, never copied
to it. Existing files are never overwritten.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import sys

try:
    from .common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
        canonical_bytes, sha256_bytes, sha256_file, read_json, secure_read,
        exclusive_write, write_json)
    from .audit import PRODUCTION_KINDS
except ImportError:
    from common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
        canonical_bytes, sha256_bytes, sha256_file, read_json, secure_read,
        exclusive_write, write_json)
    from audit import PRODUCTION_KINDS

ROOT = Path(__file__).absolute().parents[1]
CHECKER_PATH = 'PULSE_safe_pack_v0/tools/check_gates.py'
CHECKER_SHA = '3a85ed757d5569e87364bd5de511dc1985c60d97e29ee3f782e08197fa4f5c8f'
PARSER_PATH = 'tools/policy_to_require_args.py'
PARSER_SHA = '5f4dc19c96d2204c8273f32269917ebbb9b57e2efe0c710756ae4f9712fdd94e'


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def prepare(output, private_key_path, trust_domain='PRODUCTION', required_test_ids=()):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    output, key_path = Path(output).absolute(), Path(private_key_path).absolute()
    if trust_domain not in ('PRODUCTION', 'TEST'):
        raise AuditError('QRH003_TRUST_DOMAIN_INVALID')
    if output == key_path or output in key_path.parents:
        raise AuditError('QRH003_PRIVATE_KEY_INSIDE_PUBLIC_CONFIG')
    if output.exists() or key_path.exists():
        raise AuditError('QRH003_OUTPUT_NAMESPACE_NOT_FRESH')
    output.mkdir(parents=True, mode=0o700)
    if not key_path.parent.is_dir():
        raise AuditError('QRH003_PRIVATE_KEY_DIRECTORY_MISSING')
    pins = read_json(ROOT / 'reference/source_pins.json')
    configurations = read_json(ROOT / 'reference/configurations.json')
    claim_bytes = secure_read(ROOT, 'reference/claim_map.json')
    native_kinds = sorted(PRODUCTION_KINDS | {'bundle_seal'})
    capture_policy = {
        'schema_version': 'qrh003_capture_policy_v1', 'trust_domain': trust_domain,
        'source_only_collector': True, 'admissible_kinds': native_kinds,
        'untrusted_native_upstream_execution': 'FORBIDDEN_IN_THIS_COLLECTOR',
        'native_proof_capture_adapter': 'NOT_IMPLEMENTED',
        'private_key_custody': 'LOCAL_OPERATOR_FILE_OUTSIDE_BUNDLE',
        'host_tcb': 'Python, cryptography, Git, OS, hardware and the pinned collector code',
        'external_identity_certification': 'NOT_ESTABLISHED_BY_KEY_GENERATION',
        'timestamp_authentication': 'LOCAL_CLOCK_ONLY',
        'source_observation_route': 'FRESH_CURRENT_COLLECTOR_EXECUTION',
        'historical_unsigned_observation_admission': 'BLOCK',
        'stdout_success_word_is_proof': False,
    }
    profile = {
        'schema_version': 'qrh003_profile_v1', 'profile_id': 'openai_math_003_qrh_v0',
        'revision': 'implementation-v0.1.1', 'trust_domain': trust_domain,
        'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
        'critical_artifacts': pins['files'], 'configurations': configurations,
        'claim_map_sha256': sha256_bytes(claim_bytes),
        'required_claim_ids': [c['claim_id'] for c in configurations],
        'required_theorem_exports': [n for c in configurations for n in c['theorem_exports']],
        'source_roots': sorted(set([c['solution_module'] for c in configurations] +
                                   [c['challenge_module'] for c in configurations])),
        'axiom_allowlist': ['propext', 'Quot.sound', 'Classical.choice'],
        'execution_requirements': {
            'minimum_builds': 2, 'build_ids': ['A', 'B'],
            'configurations_per_build': 4, 'theorem_axiom_audits_per_build': 5,
            'upstream_toolchain': 'leanprover/lean4:v4.34.1',
            'lean_source_commit': '5045d0056413266e57c625dcd7c365b10e377c52',
            'lean_archive_sha256': '47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4',
            'proof_cache_shared_between_builds': False,
            'mutable_configuration_workspace_shared': False,
            'privileged_builder_allowed': False,
            'network_after_acquisition': 'DENIED',
            'resource_budget_binding': 'REQUIRED_BEFORE_NATIVE_EXECUTION',
            'native_capture_adapter_status': 'NOT_IMPLEMENTED',
        },
        'trusted_anchor': {
            'existing_pulse_checker_path': CHECKER_PATH,
            'existing_pulse_checker_sha256': CHECKER_SHA,
            'existing_pulse_policy_parser_path': PARSER_PATH,
            'existing_pulse_policy_parser_sha256': PARSER_SHA,
        },
        'required_boundary_test_ids': list(required_test_ids),
        'certificate_profiles': {},
        'excluded_claims': [
            'Mathematical or community acceptance', 'Whole manuscript formalization',
            'Later applications including least quadratic nonresidues and modular square roots',
            'Independent expert review inferred from a successful build',
        ],
    }
    for kind, ids in [('technical', GATE_IDS[:10]), ('semantic', GATE_IDS)]:
        profile['certificate_profiles'][kind] = {
            'policy_set': 'qrh003_' + kind + '_certificate',
            'policy_id': 'qrh003-' + kind + '-certificate-v1',
            'required_gates': list(ids),
            'certificate_type': ('qrh003_' if trust_domain == 'PRODUCTION' else 'qrh003_TEST_') + kind + '_certificate_v1',
            'trust_domain': trust_domain,
            'scope': 'Four pinned configurations and five exports only',
        }
    # Keep the small YAML grammar explicit and compatible with the pinned
    # PULSE materializer. Its output must still match the external exact list.
    policy_lines = ['version: qrh003_policy_v1', 'policy_id: qrh003-release-authority-v1',
                    'required_missing: FAIL', 'required_false: FAIL', 'gates:']
    for kind, ids in [('technical', GATE_IDS[:10]), ('semantic', GATE_IDS)]:
        policy_lines.append('  qrh003_' + kind + '_certificate:')
        policy_lines.extend('    - ' + gate for gate in ids)
    policy = ('\n'.join(policy_lines) + '\n').encode('utf-8')
    registry = ('gates:\n' + ''.join('  ' + name + ':\n    description: QRH003 evidence gate\n' for name in GATE_IDS)).encode('utf-8')
    config_bytes = {
        'profile.json': canonical_bytes(profile) + b'\n', 'policy.yml': policy,
        'gate_registry.yml': registry,
        'capture_policy.json': canonical_bytes(capture_policy) + b'\n',
        'claim_map.json': claim_bytes,
    }
    for name, data in config_bytes.items():
        exclusive_write(output / name, data)
    key = Ed25519PrivateKey.generate()
    raw_key = key.private_bytes(serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    exclusive_write(key_path, raw_key)
    verifier_files = {}
    for path in sorted(list((ROOT / 'tools').glob('*.py')) + list((ROOT / 'tests').glob('*.py'))):
        verifier_files[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    key_id = trust_domain.lower() + '-local-' + sha256_bytes(public)[:20]
    anchor = {
        'schema_version': 'qrh003_anchor_v1', 'trust_domain': trust_domain,
        'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
        'profile_sha256': sha256_bytes(config_bytes['profile.json']),
        'policy_sha256': sha256_bytes(policy), 'registry_sha256': sha256_bytes(registry),
        'verifier_files': verifier_files,
        'collector_keys': [{
            'key_id': key_id, 'public_key_hex': public.hex(), 'trust_domain': trust_domain,
            'collector_sha256': verifier_files['tools/collect.py'],
            'capture_policy_sha256': sha256_bytes(config_bytes['capture_policy.json']),
            'allowed_kinds': native_kinds,
        }],
        'required_sets': {'technical': list(GATE_IDS[:10]), 'semantic': list(GATE_IDS)},
        'anchor_origin': 'LOCAL_OPERATOR_BOOTSTRAP_REQUIRES_EXTERNAL_CUSTODY_FOR_EXTERNAL_AUTHORITY',
        'created_utc': utc_now(),
        'reference_data': {str(path.relative_to(ROOT)): sha256_file(path)
                           for path in sorted((ROOT / 'reference').glob('*.json'))},
    }
    write_json(output / 'anchor.json', anchor)
    return {'configuration_directory': str(output), 'anchor_path': str(output / 'anchor.json'),
            'key_id': key_id, 'trust_domain': trust_domain, 'authority_granted': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--private-key', type=Path, required=True)
    parser.add_argument('--trust-domain', choices=['PRODUCTION', 'TEST'], default='PRODUCTION')
    parser.add_argument('--required-tests', type=Path,
                        help='JSON list of exact unittest IDs required by the boundary gate')
    args = parser.parse_args(argv)
    try:
        ids = read_json(args.required_tests) if args.required_tests else []
        if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
            raise AuditError('QRH003_BOUNDARY_TEST_IDS_INVALID')
        result = prepare(args.output, args.private_key, args.trust_domain, ids)
        sys.stdout.buffer.write(canonical_bytes(result) + b'\n')
        return 0
    except (AuditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
