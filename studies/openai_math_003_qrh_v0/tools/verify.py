"""Strict offline admission of a QRH bundle against an external host anchor.

Signatures authenticate an authorized collector statement, not mathematical truth.
The independent evaluator consumes only authenticated receipts. No supplied gate
Boolean is used as evidence. The host and this Python process are trusted.
"""
from __future__ import annotations

# Direct scripts cannot establish source binding before their imports.
if __name__ == "__main__":
    import sys as _qrh_sys
    print("QRH003_SOURCE_BOUND_LAUNCH_REQUIRED: use source_bound.py with python -I", file=_qrh_sys.stderr)
    raise SystemExit(2)


import argparse
import datetime as dt
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any

try:
    from . import audit
    from .common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                         canonical_bytes, sha256_bytes, strict_loads, secure_read,
                         verify_signed_receipt, _open_dir, verify_source_anchor)
except ImportError:
    import audit
    from common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                        canonical_bytes, sha256_bytes, strict_loads, secure_read,
                        verify_signed_receipt, _open_dir, verify_source_anchor)

PROFILE_ROOT = Path(__file__).absolute().parents[1]
MINIMUM_VERIFIER_FILES = frozenset({
    'tools/common.py', 'tools/audit.py', 'tools/collect.py',
    'tools/verify.py', 'tools/authority.py',
    'tools/acquire.py', 'tools/source_closure.py', 'tools/preflight.py',
    'tools/run_tests.py',
    'tools/prepare.py', 'tools/transition_report.py', 'source_bound.py',
})
MANIFEST_KEYS = frozenset({
    'schema_version', 'trust_domain', 'run_key', 'created_utc', 'subject_commit',
    'pulse_commit', 'profile_kind', 'artifacts', 'receipts',
})
RECEIPT_KEYS = frozenset({
    'schema_version', 'kind', 'trust_domain', 'evidence_class', 'run_key',
    'subject_commit', 'pulse_commit', 'collector_sha256',
    'capture_policy_sha256', 'created_utc', 'body',
})
RESERVED_INPUT_PATHS = frozenset({
    'manifest.json', 'manifest.signature.json', 'status.json', 'materialized_required.json', 'decision.json',
    'certificate.json', 'replay_receipt.json',
})
BUNDLE_CONTROL_PATHS = frozenset({'manifest.json', 'manifest.signature.json'})
MAX_TOTAL_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_ARTIFACT_COUNT = 100000
STATE_NAMES = frozenset({
    'claim_released', 'artifact_identity_bound', 'formalization_present',
    'formalization_scope_bound', 'dependency_closure_complete',
    'clean_build_reproduced', 'axiom_profile_verified',
    'claim_to_theorem_binding_verified', 'independent_lean_review',
    'independent_mathematical_domain_review', 'community_acceptance',
})


def fail(code: str, detail: str = '') -> None:
    raise AuditError(code, detail)


def require_object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        fail('QRH003_OBJECT_REQUIRED', label)
    return value


def exact_keys(value: dict, keys: set | frozenset, label: str) -> None:
    if set(value) != set(keys):
        fail('QRH003_RECORD_FIELDS_MISMATCH', label)


def digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        fail('QRH003_DIGEST_INVALID', label)
    return value


def logical_path(value: Any) -> str:
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or '\x00' in value or value.startswith('/')
            or any(p in ('', '.', '..') for p in value.split('/'))
            or str(PurePosixPath(value)) != value):
        fail('QRH003_UNSAFE_PATH', repr(value))
    return value


def utc_timestamp(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.endswith('Z'):
        fail('QRH003_TIMESTAMP_INVALID', label)
    try:
        result = dt.datetime.fromisoformat(value[:-1] + '+00:00')
        if result.tzinfo is None:
            raise ValueError('missing timezone')
    except ValueError:
        fail('QRH003_TIMESTAMP_INVALID', label)


def no_symlink_path(path: os.PathLike | str) -> Path:
    """Reject existing symlinks, including ancestors. secure_read pins FDs later."""
    result = Path(os.path.abspath(os.fspath(path)))
    current = Path(result.anchor)
    for part in result.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            fail('QRH003_INPUT_MISSING', str(current))
        if stat.S_ISLNK(mode):
            fail('QRH003_SYMLINK_REJECTED', str(current))
    return result


def expected_required(profile_kind: str) -> list[str]:
    if profile_kind == 'technical':
        return list(GATE_IDS[:10])
    if profile_kind == 'semantic':
        return list(GATE_IDS)
    fail('QRH003_PROFILE_UNKNOWN', repr(profile_kind))


def validate_gate_map(gates: Any) -> dict:
    require_object(gates, 'gates')
    if set(gates) != set(GATE_IDS):
        fail('QRH003_GATE_SET_MISMATCH', 'exact thirteen gate IDs required')
    if any(type(gates[k]) is not bool for k in GATE_IDS):
        fail('QRH003_GATE_NOT_LITERAL_BOOLEAN', 'Boolean gates required')
    return gates


def _load_anchor(anchor_path: Path, bundle_root: Path) -> tuple[dict, bytes]:
    path = no_symlink_path(anchor_path)
    if path == bundle_root or bundle_root in path.parents:
        fail('QRH003_ANCHOR_INSIDE_BUNDLE', str(path))
    raw = secure_read(path.parent, path.name, max_bytes=1024 * 1024)
    anchor = require_object(strict_loads(raw), 'anchor')
    required = {
        'schema_version', 'trust_domain', 'subject_commit', 'pulse_commit',
        'profile_sha256', 'policy_sha256', 'registry_sha256', 'verifier_files',
        'collector_keys', 'required_sets', 'source_binding',
    }
    if not required <= set(anchor):
        fail('QRH003_ANCHOR_INCOMPLETE', ','.join(sorted(required - set(anchor))))
    if anchor['schema_version'] != 'qrh003_anchor_v1':
        fail('QRH003_ANCHOR_VERSION', str(anchor['schema_version']))
    if anchor['trust_domain'] not in ('PRODUCTION', 'TEST'):
        fail('QRH003_TRUST_DOMAIN_INVALID', 'anchor')
    if anchor['subject_commit'] != SUBJECT_COMMIT or anchor['pulse_commit'] != PULSE_COMMIT:
        fail('QRH003_SUBJECT_COMMIT_MISMATCH', 'external anchor')
    for key in ('profile_sha256', 'policy_sha256', 'registry_sha256'):
        digest(anchor[key], key)
    sets = require_object(anchor['required_sets'], 'required_sets')
    if set(sets) != {'technical', 'semantic'}:
        fail('QRH003_REQUIRED_SET_MISMATCH', 'anchor set names')
    for kind in ('technical', 'semantic'):
        if sets[kind] != expected_required(kind):
            fail('QRH003_REQUIRED_SET_MISMATCH', kind)
    verifier = require_object(anchor['verifier_files'], 'verifier_files')
    if not MINIMUM_VERIFIER_FILES <= set(verifier):
        fail('QRH003_VERIFIER_ANCHOR_INCOMPLETE', 'loaded authority modules')
    for name, wanted in verifier.items():
        logical_path(name)
        digest(wanted, name)
        actual = secure_read(PROFILE_ROOT, name)
        if sha256_bytes(actual) != wanted:
            fail('QRH003_VERIFIER_ANCHOR_MISMATCH', name)
    verify_source_anchor(anchor, PROFILE_ROOT)
    return anchor, raw


def _trusted_keys(anchor: dict) -> dict[str, dict]:
    keys = anchor['collector_keys']
    if not isinstance(keys, list):
        fail('QRH003_COLLECTOR_KEYS_INVALID')
    result = {}
    for key in keys:
        require_object(key, 'collector key')
        required = {'key_id', 'public_key_hex', 'trust_domain', 'collector_sha256',
                    'capture_policy_sha256', 'allowed_kinds'}
        if not required <= set(key):
            fail('QRH003_COLLECTOR_KEY_INCOMPLETE')
        key_id = key['key_id']
        if not isinstance(key_id, str) or not key_id or key_id in result:
            fail('QRH003_COLLECTOR_KEY_ID_INVALID')
        if key['trust_domain'] != anchor['trust_domain']:
            fail('QRH003_COLLECTOR_TRUST_DOMAIN_MISMATCH', key_id)
        if not isinstance(key['public_key_hex'], str) or not re.fullmatch(r'[0-9a-f]{64}', key['public_key_hex']):
            fail('QRH003_COLLECTOR_KEY_INVALID', key_id)
        digest(key['collector_sha256'], 'collector_sha256')
        digest(key['capture_policy_sha256'], 'capture_policy_sha256')
        allowed = key['allowed_kinds']
        if (not isinstance(allowed, list) or not allowed
                or any(not isinstance(k, str) or not k for k in allowed)
                or len(allowed) != len(set(allowed))):
            fail('QRH003_COLLECTOR_ALLOWED_KINDS_INVALID', key_id)
        result[key_id] = key
    return result


def _verify_manifest_signature(root: Path, manifest_bytes: bytes,
                               keys: dict[str, dict]) -> tuple[dict, bytes]:
    """Authenticate the complete artifact set, including otherwise unreferenced logs.

    The detached seal is not a member of that set and is not signed recursively.
    It signs the exact stored manifest bytes, not a reparsed representation.
    """
    raw = secure_read(root, 'manifest.signature.json', max_bytes=65536)
    seal = require_object(strict_loads(raw), 'manifest signature')
    exact_keys(seal, {'schema_version', 'key_id', 'manifest_sha256', 'signature_hex'},
               'manifest signature')
    if seal['schema_version'] != 'qrh003_manifest_signature_v1':
        fail('QRH003_MANIFEST_SEAL_VERSION')
    if digest(seal['manifest_sha256'], 'manifest seal digest') != sha256_bytes(manifest_bytes):
        fail('QRH003_MANIFEST_SEAL_DIGEST_MISMATCH')
    key_id = seal['key_id']
    if not isinstance(key_id, str) or key_id not in keys:
        fail('QRH003_MANIFEST_SEAL_SIGNER_UNAUTHORIZED', str(key_id))
    key = keys[key_id]
    if 'bundle_seal' not in key['allowed_kinds']:
        fail('QRH003_MANIFEST_SEAL_ROLE_UNAUTHORIZED', key_id)
    signature = seal['signature_hex']
    if not isinstance(signature, str) or re.fullmatch(r'[0-9a-f]{128}', signature) is None:
        fail('QRH003_MANIFEST_SEAL_SIGNATURE_INVALID')
    if not verify_signed_receipt(manifest_bytes, signature, key['public_key_hex']):
        fail('QRH003_MANIFEST_SEAL_SIGNATURE_INVALID')
    return seal, raw


def _verify_bundle_inventory(root: Path, artifact_paths: set[str]) -> None:
    """Observe an exact physical inventory without following directory links.

    The manifest and its detached signature are the only root control files.
    Every other regular file must be listed; directories must be implied by a
    listed path. This admission-time observation does not lock the filesystem
    against later writers. Evaluation uses the separately authenticated bytes
    already held in the snapshot, never an unlisted physical file.
    """
    expected_files = artifact_paths | BUNDLE_CONTROL_PATHS
    expected_dirs = set()
    for name in expected_files:
        parts = name.split('/')
        expected_dirs.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    seen_files, seen_dirs = set(), set()
    frames = []

    def directory_stamp(info):
        return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns)

    def push_directory(fd, relative, listed_info=None):
        try:
            before = os.fstat(fd)
            if listed_info is not None and (
                    before.st_dev, before.st_ino) != (
                        listed_info.st_dev, listed_info.st_ino):
                fail('QRH003_BUNDLE_CHANGED_DURING_ADMISSION', relative)
            iterator = os.scandir(fd)
        except BaseException:
            os.close(fd)
            raise
        frames.append((fd, relative, before, iterator))

    try:
        # _open_dir pins every root ancestor with O_DIRECTORY | O_NOFOLLOW.
        push_directory(_open_dir(root), '')
        while frames:
            fd, relative, before, iterator = frames[-1]
            entry = next(iterator, None)
            if entry is None:
                if directory_stamp(os.fstat(fd)) != directory_stamp(before):
                    fail('QRH003_BUNDLE_CHANGED_DURING_ADMISSION', relative or '.')
                frames.pop()
                iterator.close()
                os.close(fd)
                continue
            name = relative + '/' + entry.name if relative else entry.name
            info = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                fail('QRH003_SYMLINK_REJECTED', name)
            if stat.S_ISDIR(info.st_mode):
                if name not in expected_dirs or name in seen_dirs:
                    fail('QRH003_BUNDLE_INVENTORY_MISMATCH', name)
                seen_dirs.add(name)
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY |
                                os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                push_directory(child, name, info)
            elif stat.S_ISREG(info.st_mode):
                if name not in expected_files or name in seen_files:
                    fail('QRH003_BUNDLE_INVENTORY_MISMATCH', name)
                seen_files.add(name)
            else:
                fail('QRH003_NONREGULAR_BUNDLE_ENTRY', name)
    except OSError as exc:
        fail('QRH003_BUNDLE_INVENTORY_UNREADABLE', str(exc))
    finally:
        for fd, _, _, iterator in frames:
            iterator.close()
            os.close(fd)
    if seen_files != expected_files or seen_dirs != expected_dirs:
        fail('QRH003_BUNDLE_INVENTORY_MISMATCH', 'missing declared paths')


def make_status(snapshot: dict, anchor: dict, evaluation: dict,
                anchor_sha256: str, profile_kind: str) -> dict:
    """Runtime envelope; the root adapter may supply the full published schema."""
    builder = getattr(audit, 'build_status', None)
    if builder is not None:
        status = builder(snapshot, anchor, evaluation, anchor_sha256, profile_kind)
    else:
        m = snapshot['manifest']
        status = {
            'version': 'qrh003_runtime_status_v1', 'created_utc': m['created_utc'],
            'gates': evaluation['gates'],
            'metrics': {'run_mode': 'core', 'application_profile': 'openai_math_003_qrh_v0',
                        'run_key': m['run_key'], 'git_sha': PULSE_COMMIT},
            'qrh': {'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
                    'trust_domain': m['trust_domain'], 'profile_kind': profile_kind,
                    'evidence_manifest_sha256': snapshot['evidence_manifest_sha256'],
                    'anchor_sha256': anchor_sha256,
                    'profile_sha256': anchor['profile_sha256'],
                    'policy_sha256': anchor['policy_sha256'],
                    'registry_sha256': anchor['registry_sha256'],
                    'evaluations': evaluation['evaluations'], 'states': evaluation['states'],
                    'limitations': evaluation['limitations'],
                    'authority_granted_by_this_status': False,
                    'community_acceptance_is_derived': False},
        }
    require_object(status, 'generated status')
    validate_gate_map(status.get('gates'))
    if canonical_bytes(status['gates']) != canonical_bytes(evaluation['gates']):
        fail('QRH003_STATUS_BUILDER_GATE_MISMATCH')
    return status


def verify_bundle(bundle_dir: os.PathLike | str, anchor_path: os.PathLike | str,
                  profile_kind: str | None = None,
                  incoming_status: os.PathLike | str | None = None) -> dict:
    root = no_symlink_path(bundle_dir)
    if not root.is_dir():
        fail('QRH003_BUNDLE_NOT_DIRECTORY')
    anchor, anchor_bytes = _load_anchor(Path(anchor_path), root)
    raw = secure_read(root, 'manifest.json', max_bytes=32 * 1024 * 1024)
    manifest = require_object(strict_loads(raw), 'manifest')
    exact_keys(manifest, MANIFEST_KEYS, 'manifest')
    if manifest['schema_version'] != 'qrh003_bundle_v1':
        fail('QRH003_MANIFEST_VERSION')
    if manifest['trust_domain'] != anchor['trust_domain']:
        fail('QRH003_TEST_ORIGIN_IN_PRODUCTION', 'manifest domain differs from anchor')
    if manifest['subject_commit'] != SUBJECT_COMMIT or manifest['pulse_commit'] != PULSE_COMMIT:
        fail('QRH003_SUBJECT_COMMIT_MISMATCH', 'manifest')
    if (not isinstance(manifest['run_key'], str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', manifest['run_key'])):
        fail('QRH003_RUN_KEY_INVALID')
    utc_timestamp(manifest['created_utc'], 'manifest')
    selected = manifest['profile_kind'] if profile_kind is None else profile_kind
    expected_required(selected)
    if selected != manifest['profile_kind']:
        fail('QRH003_PROFILE_SCOPE_MISMATCH')
    keys = _trusted_keys(anchor)
    manifest_seal, manifest_seal_bytes = _verify_manifest_signature(root, raw, keys)
    artifacts = manifest['artifacts']
    if not isinstance(artifacts, list) or not artifacts or len(artifacts) > MAX_ARTIFACT_COUNT:
        fail('QRH003_ARTIFACT_SET_INVALID')
    files = {}
    total = 0
    artifact_classes = {}
    for artifact in artifacts:
        require_object(artifact, 'artifact')
        exact_keys(artifact, {'path', 'sha256', 'bytes', 'role', 'evidence_class'}, 'artifact')
        name = logical_path(artifact['path'])
        if name in files or name.split('/', 1)[0] in RESERVED_INPUT_PATHS:
            fail('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED', name)
        wanted = digest(artifact['sha256'], name)
        length = artifact['bytes']
        if type(length) is not int or length < 0 or length > 134217728:
            fail('QRH003_ARTIFACT_SIZE_INVALID', name)
        total += length
        if total > MAX_TOTAL_ARTIFACT_BYTES:
            fail('QRH003_ARTIFACT_BUDGET_EXCEEDED')
        if not isinstance(artifact['role'], str) or not artifact['role']:
            fail('QRH003_ARTIFACT_ROLE_INVALID', name)
        cls = artifact['evidence_class']
        if cls not in ('actual_observation', 'synthetic_fixture'):
            fail('QRH003_EVIDENCE_CLASS_INVALID', name)
        if anchor['trust_domain'] == 'PRODUCTION' and cls != 'actual_observation':
            fail('QRH003_SYNTHETIC_EVIDENCE_IN_PRODUCTION', name)
        content = secure_read(root, name)
        if len(content) != length or sha256_bytes(content) != wanted:
            fail('QRH003_SUBJECT_DIGEST_MISMATCH', name)
        files[name] = content
        artifact_classes[name] = cls
    for name, key in [('profile.json', 'profile_sha256'), ('policy.yml', 'policy_sha256'),
                      ('gate_registry.yml', 'registry_sha256')]:
        if name not in files:
            fail('QRH003_SUBJECT_CRITICAL_FILE_MISSING', name)
        if sha256_bytes(files[name]) != anchor[key]:
            fail('QRH003_POLICY_ANCHOR_MISMATCH', name)
    receipts = manifest['receipts']
    if not isinstance(receipts, list):
        fail('QRH003_RECEIPT_SET_INVALID')
    authenticated = []
    seen_paths = set()
    seen_receipt_digests = set()
    for record in receipts:
        require_object(record, 'receipt wrapper')
        exact_keys(record, {'payload_path', 'signature_hex', 'key_id'}, 'receipt wrapper')
        name = logical_path(record['payload_path'])
        if name not in files:
            fail('QRH003_RECEIPT_PAYLOAD_MISSING', name)
        receipt_digest = sha256_bytes(files[name])
        if name in seen_paths or receipt_digest in seen_receipt_digests:
            fail('QRH003_RECEIPT_SCOPE_REUSED', name)
        seen_paths.add(name)
        seen_receipt_digests.add(receipt_digest)
        key_id = record['key_id']
        if not isinstance(key_id, str) or key_id not in keys:
            fail('QRH003_COLLECTOR_UNAUTHORIZED', str(key_id))
        key = keys[key_id]
        signature = record['signature_hex']
        if not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{128}', signature):
            fail('QRH003_RECEIPT_SIGNATURE_INVALID', name)
        if not verify_signed_receipt(files[name], signature, key['public_key_hex']):
            fail('QRH003_RECEIPT_SIGNATURE_INVALID', name)
        payload = require_object(strict_loads(files[name]), 'receipt payload')
        exact_keys(payload, RECEIPT_KEYS, 'receipt payload')
        if payload['schema_version'] != 'qrh003_capture_v1':
            fail('QRH003_RECEIPT_VERSION', name)
        for field in ('trust_domain', 'run_key', 'subject_commit', 'pulse_commit'):
            if payload[field] != manifest[field]:
                fail('QRH003_RECEIPT_SCOPE_MISMATCH', field + ':' + name)
        if payload['kind'] not in key['allowed_kinds']:
            fail('QRH003_COLLECTOR_KIND_UNAUTHORIZED', str(payload['kind']))
        if payload['collector_sha256'] != key['collector_sha256']:
            fail('QRH003_COLLECTOR_ANCHOR_MISMATCH', name)
        if payload['capture_policy_sha256'] != key['capture_policy_sha256']:
            fail('QRH003_CAPTURE_POLICY_ANCHOR_MISMATCH', name)
        if ('capture_policy.json' in files and
                sha256_bytes(files['capture_policy.json']) != key['capture_policy_sha256']):
            fail('QRH003_CAPTURE_POLICY_ARTIFACT_MISMATCH', name)
        if payload['evidence_class'] != artifact_classes[name]:
            fail('QRH003_EVIDENCE_CLASS_RECLASSIFIED', name)
        if anchor['trust_domain'] == 'PRODUCTION' and payload['evidence_class'] != 'actual_observation':
            fail('QRH003_SYNTHETIC_EVIDENCE_IN_PRODUCTION', name)
        utc_timestamp(payload['created_utc'], name)
        require_object(payload['body'], 'receipt body')
        # Payload is untouched; authentication facts live beside it, not inside it.
        authenticated.append(payload)
    _verify_bundle_inventory(root, set(files))
    snapshot = {'manifest': manifest, 'manifest_bytes': raw, 'files': files,
                'receipts': authenticated, 'evidence_manifest_sha256': sha256_bytes(raw),
                'manifest_signature': manifest_seal,
                'manifest_signature_sha256': sha256_bytes(manifest_seal_bytes)}
    evaluation = require_object(audit.evaluate(snapshot, anchor, selected), 'evaluation')
    if set(evaluation) != {'gates', 'evaluations', 'states', 'limitations'}:
        fail('QRH003_EVALUATOR_RESULT_INVALID')
    validate_gate_map(evaluation['gates'])
    require_object(evaluation['evaluations'], 'evaluations')
    if set(evaluation['evaluations']) != set(GATE_IDS):
        fail('QRH003_EVALUATION_GATE_SET_MISMATCH')
    require_object(evaluation['states'], 'states')
    if set(evaluation['states']) != STATE_NAMES:
        fail('QRH003_EVALUATION_STATE_SET_MISMATCH')
    for gate, record in evaluation['evaluations'].items():
        require_object(record, 'gate evaluation')
        if set(record) != {'state', 'reason_codes', 'evidence_refs'}:
            fail('QRH003_EVALUATION_RECORD_INVALID', gate)
        if not isinstance(record['state'], str):
            fail('QRH003_EVALUATION_RECORD_INVALID', gate)
        for field in ('reason_codes', 'evidence_refs'):
            if (not isinstance(record[field], list)
                    or any(not isinstance(value, str) or not value for value in record[field])):
                fail('QRH003_EVALUATION_RECORD_INVALID', gate)
        allowed_pass_states = {'VERIFIED', 'SOURCE_MAP_BOUND'} if gate == GATE_IDS[1] else {'VERIFIED'}
        if evaluation['gates'][gate] != (record['state'] in allowed_pass_states):
            fail('QRH003_EVALUATOR_GATE_STATE_MISMATCH', gate)
        if evaluation['gates'][gate] and (not record['evidence_refs'] or
                any(ref not in files for ref in record['evidence_refs'])):
            fail('QRH003_VERIFIED_EVIDENCE_REFERENCE_MISSING', gate)
    if (not isinstance(evaluation['limitations'], list)
            or any(not isinstance(value, str) for value in evaluation['limitations'])):
        fail('QRH003_EVALUATOR_LIMITATIONS_INVALID')
    anchor_sha256 = sha256_bytes(anchor_bytes)
    status = make_status(snapshot, anchor, evaluation, anchor_sha256, selected)
    if incoming_status is not None:
        path = no_symlink_path(incoming_status)
        supplied = require_object(strict_loads(secure_read(path.parent, path.name)), 'incoming status')
        validate_gate_map(supplied.get('gates'))
        if canonical_bytes(supplied) != canonical_bytes(status):
            fail('QRH003_FOREIGN_OR_STALE_STATUS', 'does not match independently regenerated status')
    return {'snapshot': snapshot, 'anchor': anchor, 'anchor_sha256': anchor_sha256,
            'evaluation': evaluation, 'status_expected': status, 'profile_kind': selected}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--anchor', required=True)
    parser.add_argument('--profile', choices=['technical', 'semantic'])
    parser.add_argument('--status')
    args = parser.parse_args(argv)
    try:
        result = verify_bundle(args.bundle, args.anchor, args.profile, args.status)
        summary = {'admission': 'VERIFIED_INPUTS', 'gates': result['evaluation']['gates'],
                   'certificate_emitted': False}
        sys.stdout.buffer.write(canonical_bytes(summary) + b'\n')
        return 0 if all(result['evaluation']['gates'][g] is True
                        for g in expected_required(result['profile_kind'])) else 1
    except (AuditError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
