#!/usr/bin/env python3
"""Closed Q2 capsule worker contract. No transport, model load or dispatch."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# The CLI only constructs request bytes; native use imports this held source
# after the collector's stdlib owner/Git guard.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_q2_release_host_worker_protocol_v0 import (ProtocolError, require, encode,
    digest, parse, held_read, same, fields, integer, SCOPE, REPOSITORY, WORKFLOW,
    WORKER, WORKLOAD, WORKER_SHA256, WORKLOAD_SHA256, CONFIGURATION_SHA256,
    CAPSULE_SHA256, DEFINITION_SHA256, LIMITS, RUNTIME, NON_AUTHORITY)

PACK = 'PULSE_safe_pack_v0/'
TOOLS = PACK + 'tools/'
PROFILE = PACK + 'profiles/q2_release_host_worker_verification_v0.json'
REQUEST_SCHEMA = 'schemas/q2_release_host_worker_request_v0.schema.json'
RESULT_SCHEMA = 'schemas/q2_release_host_worker_result_v0.schema.json'
SELF = TOOLS + 'q2_release_host_worker_contract_v0.py'
COLLECTOR = TOOLS + 'verify_q2_release_host_worker_v0.py'
CHECKER = TOOLS + 'check_q2_release_host_worker_v0.py'
PROTOCOL = TOOLS + 'check_q2_release_host_worker_protocol_v0.py'
EXCHANGE = TOOLS + 'acquire_q2_reference_inputs_v0.py'
OLD_PROFILE = PACK + 'profiles/q2_release_host_tokenizer_verification_v0.json'
NAME = 'Q2 native release-host worker verification v0'
CONSENT = 'AUTHORIZE_150_FRESH_CALLS_AND_30_DAY_ACTIONS_RAW_EVIDENCE_RETENTION'
PHASES = ('input_check', 'worker', 'tokenizer_check', 'reduction_check')
# No schema/role genericization of the old tokenizer-only profile.
NEW_SOURCES = (PROFILE, REQUEST_SCHEMA, RESULT_SCHEMA, SELF, COLLECTOR, CHECKER,
               PROTOCOL, EXCHANGE, WORKER, WORKFLOW)


def load_profile(source: Path) -> dict:
    raw = held_read(source / PROFILE, 256 * 1024)
    p = parse(raw)
    schema = parse(held_read(source / REQUEST_SCHEMA, 512 * 1024))
    same(p, schema['$defs']['profile']['const'], 'profile_contract_changed')
    old = parse(held_read(source / OLD_PROFILE, 256 * 1024))
    names = sorted(set(old['source_paths']) | set(NEW_SOURCES))
    require(p['source_paths'] == names, 'source_extent')
    require(p['scope'] == SCOPE and p['record_type'] == 'q2_release_host_worker_profile_v0', 'profile_scope')
    same(p['inputs'], old['inputs'], 'fixed_inputs_changed')
    for key in ('bootstrap', 'bootstrap_python_sha256', 'bootstrap_prefix', 'bootstrap_home',
                'publication_profile', 'verifier_wheels', 'capsule_members', 'capsule_expanded_bytes',
                'interpreter_entries', 'verifier_interpreter_entries', 'runtime_versions',
                'configuration_sha256', 'definition_sha256', 'platform_keys', 'archived_platform_requirements'):
        same(p[key], old[key], 'inherited_contract_changed')
    same(p['native_requirements'], old['archived_platform_requirements'], 'strict_platform_changed')
    same(p['claims'], NON_AUTHORITY, 'authority_contract_changed')
    same(p['worker_limits'], LIMITS, 'worker_limits_changed')
    require(p['phases'] == list(PHASES) and p['consent'] == CONSENT and
            p['platform_contract'] == 'strict_archived_platform_identity_v0', 'phase_contract_changed')
    return p


def source_closure(source: Path, revision: str, names: list[str]) -> list[dict]:
    """Verify held bytes and modes against exact Git objects, with no remote IO."""
    require(re.fullmatch('[0-9a-f]{40}', revision or '') is not None, 'source_shape')
    require(type(names) is list and 20 <= len(names) <= 60 and names == sorted(set(names)), 'source_extent')
    clean = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
             'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
             'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_REPLACE_OBJECTS': '1'}
    def git(args):
        result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'credential.helper=',
             '-c', 'core.hooksPath=/dev/null', '-c', 'safe.directory=' + str(source), *args],
             cwd=source, env=clean, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
             stderr=subprocess.DEVNULL, timeout=15, check=False)
        require(result.returncode == 0 and len(result.stdout) <= 65536, 'source_unavailable')
        return result.stdout
    require(git(['rev-parse', '--verify', 'HEAD^{commit}']) == revision.encode() + b'\n', 'source_head_changed')
    entries = {}
    for line in git(['ls-tree', '-rz', '--full-tree', revision, '--', *names]).split(b'\0'):
        if line:
            metadata, path = line.split(b'\t'); entries[path.decode('ascii')] = metadata.decode('ascii').split()
    require(set(entries) == set(names), 'source_extent')
    rows = []
    for name in names:
        require(re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name) is not None and
                '..' not in Path(name).parts, 'source_path')
        raw = held_read(source / name, 2 * 1024 * 1024)
        mode = '100755' if (source / name).stat().st_mode & 0o111 else '100644'
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(entries[name] == [mode, 'blob', blob], 'source_bytes_changed')
        rows.append({'path': name, 'size_bytes': len(raw), 'sha256': digest(raw)})
    return rows


def request_for(source: Path, revision: str) -> dict:
    require(re.fullmatch('[0-9a-f]{40}', revision or '') is not None, 'source_shape')
    p = load_profile(source)
    return {'schema_version': 'q2_release_host_worker_request_v0', 'scope': SCOPE,
            'source_commit': revision, 'profile_sha256': digest(held_read(source / PROFILE)),
            'inputs': p['inputs'], 'workload_sha256': WORKLOAD_SHA256,
            'worker_sha256': WORKER_SHA256, 'planned_calls': 150,
            'consent': CONSENT, 'platform_contract': p['platform_contract'],
            'retention': p['retention'], **NON_AUTHORITY}


def check_request(source: Path, raw: bytes, expected: str, revision: str) -> dict:
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected) is not None and
            digest(raw) == expected, 'request_digest_changed')
    value = parse(raw, 32768)
    same(value, request_for(source, revision), 'request_contract_changed')
    return value


def evidence_names() -> set[str]:
    names = {'request.json', 'plan.json', 'projection.json', 'input-check.json',
             'capture-prelaunch.json', 'capture-subject.json', 'capture-model-ready.json',
             'transcript.json', 'lifecycle-before-cleanup.json', 'lifecycle.json',
             'tokenizer-check.json', 'token-map.json', 'groups.json', 'dataset-manifest.json',
             'summary.json', 'summary-check.json', 'reduction-check.json', 'result.json'}
    for i in range(1, 151):
        stem = f'calls/q2fx-{(i-1)//3+1:03d}-r{(i-1)%3+1:02d}'
        for suffix in ('.ready.json', '.response.json', '.intent.json', '.utf8'):
            names.add(stem + suffix)
    return names


def inventory(buffers: dict[str, bytes]) -> list[dict]:
    require(type(buffers) is dict and 0 < len(buffers) <= 700, 'evidence_extent')
    require(sum(len(v) for v in buffers.values()) <= 64 * 1024 * 1024, 'evidence_bound')
    rows = []
    for path, raw in sorted(buffers.items()):
        require(type(path) is str and not Path(path).is_absolute() and
                '..' not in Path(path).parts and '\\' not in path and type(raw) is bytes and
                len(raw) <= 16 * 1024 * 1024, 'evidence_path')
        rows.append({'path': path, 'size_bytes': len(raw), 'sha256': digest(raw)})
    return rows


def validate_json(source: Path, definition: str, obj: dict) -> None:
    from jsonschema import Draft202012Validator
    s = parse(held_read(source / RESULT_SCHEMA, 512 * 1024))
    validator = Draft202012Validator({'$ref': '#/$defs/' + definition, '$defs': s['$defs']})
    require(validator.is_valid(obj), 'worker_schema_rejected')


def main(argv=None):
    import argparse
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo-root', type=Path, required=True)
    a.add_argument('--source-commit', required=True)
    a.add_argument('--authorize-150-and-actions-retention', action='store_true')
    args = a.parse_args(argv)
    try:
        require(args.authorize_150_and_actions_retention is True, 'explicit_future_owner_consent_required')
        source = args.repo_root.resolve(strict=True)
        p = load_profile(source)
        source_closure(source, args.source_commit, p['source_paths'])
        # This constructs request bytes only; the authenticated owner dispatch is
        # still required. Nothing here calls GitHub or starts a worker.
        sys.stdout.buffer.write(encode(request_for(source, args.source_commit)))
        return 0
    except Exception:
        sys.stderr.write('q2_worker_request_rejected\n'); return 2

if __name__ == '__main__':
    raise SystemExit(main())
