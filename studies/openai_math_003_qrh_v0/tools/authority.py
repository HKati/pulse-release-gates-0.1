"""Offline QRH decision, exclusive certificate emission, and independent replay.

The command controls only its fresh output directory. It does not control an
upstream publisher or establish mathematical acceptance. BLOCK reports remain
publishable. A previous ALLOW is never accepted in place of current admission.
"""
from __future__ import annotations

# Direct scripts cannot establish source binding before their imports.
if __name__ == "__main__":
    import sys as _qrh_sys
    print("QRH003_SOURCE_BOUND_LAUNCH_REQUIRED: use source_bound.py with python -I", file=_qrh_sys.stderr)
    raise SystemExit(2)


import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

try:
    from .common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                         canonical_bytes, sha256_bytes, strict_loads, secure_read,
                         exclusive_write)
    from .verify import (verify_bundle, expected_required, no_symlink_path,
                         logical_path, digest, require_object, validate_gate_map)
except ImportError:
    from common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                        canonical_bytes, sha256_bytes, strict_loads, secure_read,
                        exclusive_write)
    from verify import (verify_bundle, expected_required, no_symlink_path,
                        logical_path, digest, require_object, validate_gate_map)


def _error_code(error: Exception) -> str:
    return getattr(error, 'code', 'QRH003_HOST_ERROR')


def _reserve_output(output_dir, input_dir=None) -> Path:
    output = Path(os.path.abspath(os.fspath(output_dir)))
    parent = no_symlink_path(output.parent)
    if not parent.is_dir() or output.name in ('', '.', '..'):
        raise AuditError('QRH003_OUTPUT_PATH_INVALID')
    if input_dir is not None:
        source = Path(os.path.abspath(os.fspath(input_dir)))
        if output == source or source in output.parents or output in source.parents:
            raise AuditError('QRH003_OUTPUT_OVERLAPS_INPUT')
    try:
        # Every path component was checked; the declared host parent is trusted.
        # mkdir is the one atomic reservation: even an empty prior run is refused.
        os.mkdir(output, 0o700)
    except FileExistsError as exc:
        raise AuditError('QRH003_OUTPUT_ALREADY_EXISTS', str(output)) from exc
    return output


def _strict_policy_sets(raw: bytes) -> dict[str, list[str]]:
    """Accept the intentionally small policy grammar, rejecting YAML ambiguity.

    Root scalar metadata plus one `gates:` mapping of bare gate-set names to
    block or inline bare-ID lists. Aliases, merge keys, quoted keys, duplicate
    keys, multiline scalar tricks, tabs and nested mappings are not supported.
    """
    try:
        text = raw.decode('utf-8', 'strict')
    except UnicodeError as exc:
        raise AuditError('QRH003_POLICY_ENCODING') from exc
    root_keys, sets = set(), {}
    in_gates = False
    current = None
    for original in text.splitlines():
        if '\t' in original:
            raise AuditError('QRH003_POLICY_GRAMMAR', 'tabs')
        line = original.split('#', 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        content = line.strip()
        if indent == 0:
            match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?', content)
            if match is None:
                raise AuditError('QRH003_POLICY_GRAMMAR', content)
            key, value = match.groups()
            if key in root_keys:
                raise AuditError('QRH003_DUPLICATE_MAPPING_KEY', key)
            root_keys.add(key)
            in_gates = key == 'gates'
            current = None
            if in_gates and value not in (None, ''):
                raise AuditError('QRH003_POLICY_GRAMMAR', 'gates must be mapping')
            if not in_gates and (not value or any(c in value for c in '&*!{}[]')):
                raise AuditError('QRH003_POLICY_GRAMMAR', 'unsupported root scalar')
        elif indent == 2 and in_gates:
            match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?', content)
            if match is None:
                raise AuditError('QRH003_POLICY_GRAMMAR', content)
            name, value = match.groups()
            if name in sets:
                raise AuditError('QRH003_DUPLICATE_MAPPING_KEY', name)
            sets[name] = []
            current = name
            if value:
                if not value.startswith('[') or not value.endswith(']'):
                    raise AuditError('QRH003_POLICY_GRAMMAR', content)
                inner = value[1:-1].strip()
                values = [] if not inner else [x.strip() for x in inner.split(',')]
                if any(re.fullmatch(r'[A-Za-z0-9_]+', x) is None for x in values):
                    raise AuditError('QRH003_POLICY_GRAMMAR', content)
                sets[name] = values
                current = None
        elif indent == 4 and in_gates and current:
            match = re.fullmatch(r'- ([A-Za-z0-9_]+)', content)
            if match is None:
                raise AuditError('QRH003_POLICY_GRAMMAR', content)
            sets[current].append(match.group(1))
        else:
            raise AuditError('QRH003_POLICY_GRAMMAR', content)
    if 'gates' not in root_keys:
        raise AuditError('QRH003_REQUIRED_SET_MISMATCH', 'missing gates mapping')
    return sets


def _tool_bytes(profile: dict, pulse_root, kind: str) -> tuple[str, bytes]:
    trusted = require_object(profile.get('trusted_anchor'), 'profile.trusted_anchor')
    stem = 'existing_pulse_checker' if kind == 'checker' else 'existing_pulse_policy_parser'
    path = logical_path(trusted.get(stem + '_path'))
    wanted = digest(trusted.get(stem + '_sha256'), stem)
    raw = secure_read(pulse_root, path)
    if sha256_bytes(raw) != wanted:
        raise AuditError('QRH003_PULSE_PRIMITIVE_DIGEST_MISMATCH', path)
    return wanted, raw


def _run_primitive(script: Path, args: list[str], cwd: Path) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, '-I', str(script), *args], cwd=cwd,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
            timeout=30, check=False,
        )
        return {'exit_code': result.returncode, 'stdout': result.stdout,
                'stderr': result.stderr, 'timeout': False}
    except subprocess.TimeoutExpired as exc:
        return {'exit_code': None, 'stdout': exc.stdout or b'',
                'stderr': exc.stderr or b'', 'timeout': True}


def _primitive_summary(record: dict | None, source_sha256=None) -> dict:
    if record is None:
        return {'attempted': False, 'source_sha256': source_sha256, 'exit_code': None,
                'timeout': False, 'stdout_sha256': None, 'stderr_sha256': None}
    return {'attempted': True, 'source_sha256': source_sha256,
            'exit_code': record['exit_code'], 'timeout': record['timeout'],
            'stdout_sha256': sha256_bytes(record['stdout']),
            'stderr_sha256': sha256_bytes(record['stderr'])}


def _declared_certificate_type(verified: dict) -> str:
    """Bind output type to the admitted domain/kind and frozen profile bytes.

    These four types are the supported output contract, not a producer-chosen
    label. A valid type grants no authority without all other release gates.
    """
    supported = {
        ('PRODUCTION', 'technical'): 'qrh003_technical_certificate_v1',
        ('PRODUCTION', 'semantic'): 'qrh003_semantic_certificate_v1',
        ('TEST', 'technical'): 'qrh003_TEST_technical_certificate_v1',
        ('TEST', 'semantic'): 'qrh003_TEST_semantic_certificate_v1',
    }
    domain = verified['anchor']['trust_domain']
    kind = verified['profile_kind']
    expected = supported.get((domain, kind))
    if expected is None:
        raise AuditError('QRH003_CERTIFICATE_PROFILE_BINDING_INVALID')
    profile = require_object(strict_loads(verified['snapshot']['files']['profile.json']), 'profile')
    profiles = require_object(profile.get('certificate_profiles'), 'certificate_profiles')
    declaration = require_object(profiles.get(kind), kind)
    if profile.get('trust_domain') != domain or declaration.get('trust_domain') != domain:
        raise AuditError('QRH003_CERTIFICATE_PROFILE_DOMAIN_MISMATCH', kind)
    if 'certificate_type' not in declaration:
        raise AuditError('QRH003_CERTIFICATE_TYPE_MISSING', kind)
    declared = declaration['certificate_type']
    if not isinstance(declared, str) or declared != expected:
        raise AuditError('QRH003_CERTIFICATE_TYPE_MISMATCH', kind)
    return declared


def _pulse_primitives(verified: dict, status_raw: bytes, pulse_root) -> tuple[dict, dict, list[str], dict]:
    profile = require_object(strict_loads(verified['snapshot']['files']['profile.json']), 'profile')
    kind = verified['profile_kind']
    required = expected_required(kind)
    parser_record = checker_record = None
    parser_digest = checker_digest = None
    exact_materialization = False
    errors, logs = [], {}
    try:
        # Check the output contract before allowing policy/checker success to
        # authorize emission. Contract errors become preserved BLOCK reasons.
        _declared_certificate_type(verified)
        profiles = require_object(profile.get('certificate_profiles'), 'certificate_profiles')
        declaration = require_object(profiles.get(kind), kind)
        policy_set = declaration.get('policy_set')
        if not isinstance(policy_set, str) or re.fullmatch(r'[A-Za-z0-9_]+', policy_set) is None:
            raise AuditError('QRH003_POLICY_SET_ID_INVALID')
        policy_raw = verified['snapshot']['files']['policy.yml']
        parsed_sets = _strict_policy_sets(policy_raw)
        if parsed_sets.get(policy_set) != required:
            raise AuditError('QRH003_REQUIRED_SET_MISMATCH', 'declared policy')
        if pulse_root is None:
            raise AuditError('QRH003_PULSE_RUNTIME_UNAVAILABLE')
        pulse_path = no_symlink_path(pulse_root)
        parser_digest, parser_source = _tool_bytes(profile, pulse_path, 'parser')
        checker_digest, checker_source = _tool_bytes(profile, pulse_path, 'checker')
        with tempfile.TemporaryDirectory(prefix='qrh003-authority-') as temporary:
            work = Path(temporary)
            for name, raw in [('parser.py', parser_source), ('checker.py', checker_source),
                              ('policy.yml', policy_raw), ('status.json', status_raw)]:
                exclusive_write(work / name, raw)
            parser_record = _run_primitive(work / 'parser.py',
                ['--policy', str(work / 'policy.yml'), '--set', policy_set, '--format', 'newline'], work)
            logs['policy_parser.stdout'] = parser_record['stdout']
            logs['policy_parser.stderr'] = parser_record['stderr']
            if parser_record['timeout'] or parser_record['exit_code'] != 0:
                raise AuditError('QRH003_POLICY_PARSER_FAILED')
            try:
                actual = parser_record['stdout'].decode('utf-8', 'strict').splitlines()
            except UnicodeError as exc:
                raise AuditError('QRH003_POLICY_PARSER_OUTPUT_INVALID') from exc
            if actual != required:
                raise AuditError('QRH003_REQUIRED_SET_MISMATCH', 'pinned parser output')
            exact_materialization = True
            checker_record = _run_primitive(work / 'checker.py',
                ['--status', str(work / 'status.json'), '--require', *actual], work)
            logs['checker.stdout'] = checker_record['stdout']
            logs['checker.stderr'] = checker_record['stderr']
            if checker_record['timeout']:
                errors.append('QRH003_PULSE_CHECKER_TIMEOUT')
            elif checker_record['exit_code'] not in (0, 1):
                errors.append('QRH003_PULSE_CHECKER_ERROR')
    except Exception as exc:
        errors.append(_error_code(exc))
        logs['primitive_error.txt'] = (type(exc).__name__ + ': ' + str(exc)).encode('utf-8', 'replace')
    parser_summary = _primitive_summary(parser_record, parser_digest)
    parser_summary['exact_required_set_verified'] = exact_materialization
    return (parser_summary,
            _primitive_summary(checker_record, checker_digest), errors, logs)


def _failure_status(code: str, profile_kind: str) -> dict:
    return {
        'version': 'qrh003_runtime_status_v1', 'created_utc': None,
        'gates': {gate: False for gate in GATE_IDS},
        'metrics': {'run_mode': 'core', 'application_profile': 'openai_math_003_qrh_v0',
                    'run_key': None, 'git_sha': PULSE_COMMIT},
        'qrh': {'record_role': 'admission_failure', 'trust_domain': 'UNVERIFIED',
                'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
                'profile_kind': profile_kind, 'admission_error': code,
                'authority_granted_by_this_status': False},
    }


def _compute(bundle_dir, anchor_path, profile_kind=None, incoming_status=None, pulse_root=None) -> dict:
    verified = None
    logs = {}
    errors = []
    selected = profile_kind or 'technical'
    try:
        expected_required(selected)
        verified = verify_bundle(bundle_dir, anchor_path, profile_kind, incoming_status)
        selected = verified['profile_kind']
        status = verified['status_expected']
    except Exception as exc:
        code = _error_code(exc) if isinstance(exc, (AuditError, OSError, ValueError)) else 'QRH003_UNEXPECTED_ADMISSION_ERROR'
        errors.append(code)
        logs['admission_error.txt'] = (type(exc).__name__ + ': ' + str(exc)).encode('utf-8', 'replace')
        status = _failure_status(errors[0], selected)
    status_raw = canonical_bytes(status)
    required = expected_required(selected) if selected in ('technical', 'semantic') else []
    if verified is not None:
        parser, checker, primitive_errors, logs = _pulse_primitives(verified, status_raw, pulse_root)
        errors.extend(primitive_errors)
        anchor = verified['anchor']
        manifest = verified['snapshot']['manifest']
        bindings = {
            'evidence_manifest_sha256': verified['snapshot']['evidence_manifest_sha256'],
            'manifest_signature_sha256': verified['snapshot']['manifest_signature_sha256'],
            'anchor_sha256': verified['anchor_sha256'],
            'profile_sha256': anchor['profile_sha256'], 'policy_sha256': anchor['policy_sha256'],
            'registry_sha256': anchor['registry_sha256'],
            'verifier_files_sha256': sha256_bytes(canonical_bytes(anchor['verifier_files'])),
        }
        trust_domain, run_key = anchor['trust_domain'], manifest['run_key']
    else:
        parser = _primitive_summary(None)
        checker = _primitive_summary(None)
        bindings = {key: None for key in ('evidence_manifest_sha256', 'manifest_signature_sha256', 'anchor_sha256',
                    'profile_sha256', 'policy_sha256', 'registry_sha256', 'verifier_files_sha256')}
        trust_domain, run_key = 'UNVERIFIED', None
    materialization_verified = parser.get('exact_required_set_verified') is True
    failed = [gate for gate in required if status['gates'].get(gate) is not True]
    if failed:
        errors.append('QRH003_REQUIRED_GATES_NOT_PASSED')
    allow = (verified is not None and not errors and not failed and bool(required)
             and materialization_verified and checker['attempted']
             and checker['exit_code'] == 0 and not checker['timeout'])
    if not allow and not errors:
        errors.append('QRH003_PULSE_CHECKER_REJECTED')
    materialized = {
        'schema_version': 'qrh003_materialized_required_v1', 'run_key': run_key,
        'trust_domain': trust_domain, 'profile_kind': selected,
        'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
        'status_sha256': sha256_bytes(status_raw), **bindings,
        'ordered_gate_ids': required, 'policy_materialization_verified': materialization_verified,
        'policy_parser': parser,
    }
    materialized_raw = canonical_bytes(materialized)
    decision = {
        'schema_version': 'qrh003_decision_v1', 'run_key': run_key,
        'trust_domain': trust_domain, 'profile_kind': selected,
        'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
        'result': 'ALLOW' if allow else 'BLOCK', 'reason_codes': sorted(set(errors)),
        'status_sha256': sha256_bytes(status_raw),
        'materialized_required_sha256': sha256_bytes(materialized_raw), **bindings,
        'required_gate_ids': required, 'failed_required_gates': failed, 'checker': checker,
        'scope': 'offline_command_certificate_only',
        'mathematical_or_community_acceptance_asserted': False,
    }
    return {'verified': verified, 'status': status, 'status_bytes': status_raw,
            'materialized': materialized, 'materialized_bytes': materialized_raw,
            'decision': decision, 'decision_bytes': canonical_bytes(decision), 'logs': logs}


def _certificate(result: dict) -> dict:
    decision = result['decision']
    if decision['result'] != 'ALLOW':
        raise AuditError('QRH003_CERTIFICATE_WITHOUT_ALLOW')
    test = decision['trust_domain'] == 'TEST'
    if decision['trust_domain'] not in ('TEST', 'PRODUCTION'):
        raise AuditError('QRH003_CERTIFICATE_TRUST_DOMAIN')
    verified = result.get('verified')
    if (verified is None or decision['trust_domain'] != verified['anchor']['trust_domain']
            or decision['profile_kind'] != verified['profile_kind']):
        raise AuditError('QRH003_CERTIFICATE_PROFILE_BINDING_INVALID')
    declared_type = _declared_certificate_type(verified)
    return {
        'schema_version': 'qrh003_certificate_v1',
        'certificate_type': declared_type,
        'trust_domain': decision['trust_domain'],
        'evidence_class': 'synthetic_fixture' if test else 'actual_observation',
        'run_key': decision['run_key'], 'subject_commit': SUBJECT_COMMIT,
        'pulse_commit': PULSE_COMMIT, 'profile_kind': decision['profile_kind'],
        'decision_sha256': sha256_bytes(result['decision_bytes']),
        'evidence_manifest_sha256': decision['evidence_manifest_sha256'],
        'anchor_sha256': decision['anchor_sha256'],
        'scope': 'TEST_AUTHORITY_CONTROL_ONLY' if test else 'EXACT_FOUR_CONFIGURATIONS_FIVE_EXPORTS',
        'mathematical_or_community_acceptance_asserted': False,
        'complete_manuscript_or_applications_formalized_asserted': False,
    }


def decide(bundle_dir, anchor_path, output_dir, profile_kind=None,
           incoming_status=None, pulse_root=None) -> dict:
    output = _reserve_output(output_dir, bundle_dir)
    result = _compute(bundle_dir, anchor_path, profile_kind, incoming_status, pulse_root)
    for name, raw in [('status.json', result['status_bytes']),
                      ('materialized_required.json', result['materialized_bytes']),
                      ('decision.json', result['decision_bytes'])]:
        exclusive_write(output / name, raw)
    for name, raw in result['logs'].items():
        exclusive_write(output / name, raw)
    if result['decision']['result'] == 'ALLOW':
        certificate = _certificate(result)
        namespace = 'test_only' if certificate['trust_domain'] == 'TEST' else 'production_certificates'
        os.mkdir(output / namespace, 0o700)
        # Last publication: all prerequisite output bytes already exist and were fsynced.
        exclusive_write(output / namespace / 'certificate.json', canonical_bytes(certificate))
    return result['decision']


def _verified_previous(previous: Path, result: dict) -> tuple[dict, bytes]:
    previous = no_symlink_path(previous)
    raw = secure_read(previous, 'decision.json')
    old = require_object(strict_loads(raw), 'previous decision')
    for name, digest_field in [('status.json', 'status_sha256'),
                               ('materialized_required.json', 'materialized_required_sha256')]:
        content = secure_read(previous, name)
        if sha256_bytes(content) != old.get(digest_field):
            raise AuditError('QRH003_PREVIOUS_DECISION_INPUT_DIGEST_MISMATCH', name)
        parsed = require_object(strict_loads(content), name)
        if name == 'status.json':
            validate_gate_map(parsed.get('gates'))
        elif parsed.get('ordered_gate_ids') != expected_required(old.get('profile_kind')):
            raise AuditError('QRH003_REQUIRED_SET_MISMATCH', name)
    if raw != result['decision_bytes']:
        raise AuditError('QRH003_DECISION_REPLAY_MISMATCH')
    namespace = 'test_only' if old['trust_domain'] == 'TEST' else 'production_certificates'
    certificate_path = previous / namespace / 'certificate.json'
    if old['result'] == 'ALLOW':
        content = secure_read(previous, namespace + '/certificate.json')
        if content != canonical_bytes(_certificate(result)):
            raise AuditError('QRH003_CERTIFICATE_REPLAY_MISMATCH')
    for candidate in ('certificate.json', 'test_only/certificate.json',
                      'production_certificates/certificate.json'):
        if old['result'] == 'ALLOW' and candidate == namespace + '/certificate.json':
            continue
        if os.path.lexists(previous / candidate):
            raise AuditError('QRH003_STALE_OR_WRONG_NAMESPACE_CERTIFICATE')
    return old, raw


def replay(bundle_dir, anchor_path, decision_dir, output_dir, pulse_root=None) -> dict:
    output = _reserve_output(output_dir, bundle_dir)
    previous = no_symlink_path(decision_dir)
    old_bytes = secure_read(previous, 'decision.json')
    old = require_object(strict_loads(old_bytes), 'previous decision')
    kind = old.get('profile_kind')
    result = _compute(bundle_dir, anchor_path, kind, None, pulse_root)
    replay_error = None
    try:
        _verified_previous(previous, result)
    except Exception as exc:
        replay_error = _error_code(exc)
    receipt = {
        'schema_version': 'qrh003_replay_receipt_v1',
        'previous_decision_sha256': sha256_bytes(old_bytes),
        'fresh_decision_sha256': sha256_bytes(result['decision_bytes']),
        'fresh_result': result['decision']['result'],
        'replay_status': 'MATCH' if replay_error is None else 'MISMATCH',
        'reason_code': replay_error, 'certificate_emitted': False,
        'scope': 'decision_reconstruction_only',
        'mathematical_or_community_acceptance_asserted': False,
    }
    exclusive_write(output / 'recomputed_decision.json', result['decision_bytes'])
    exclusive_write(output / 'recomputed_status.json', result['status_bytes'])
    exclusive_write(output / 'recomputed_materialized_required.json', result['materialized_bytes'])
    for name, raw in result['logs'].items():
        exclusive_write(output / name, raw)
    exclusive_write(output / 'replay_receipt.json', canonical_bytes(receipt))
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('decide', 'replay'):
        sub = commands.add_parser(command)
        sub.add_argument('--bundle', required=True)
        sub.add_argument('--anchor', required=True)
        sub.add_argument('--output', required=True)
        sub.add_argument('--pulse-root')
        if command == 'decide':
            sub.add_argument('--profile', choices=['technical', 'semantic'])
            sub.add_argument('--status')
        else:
            sub.add_argument('--decision-dir', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'decide':
            result = decide(args.bundle, args.anchor, args.output, args.profile, args.status, args.pulse_root)
            exit_code = 0 if result['result'] == 'ALLOW' else 1
        else:
            result = replay(args.bundle, args.anchor, args.decision_dir, args.output, args.pulse_root)
            exit_code = 0 if result['replay_status'] == 'MATCH' else 1
        sys.stdout.buffer.write(canonical_bytes(result) + b'\n')
        return exit_code
    except (AuditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
