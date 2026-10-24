#!/usr/bin/env python3
"""Closed Q3 native-capture contract. Construct requests; never dispatch or infer.

The immutable profile and the separately chosen reviewed commit are different
anchors. Source hashes do not authenticate an actor or a native execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any

REPOSITORY = 'HKati/pulse-release-gates-0.1'
PACK = 'PULSE_safe_pack_v0/'
PROFILE = PACK + 'profiles/q3_native_capture_v0.json'
FRAME = PACK + 'examples/q3_native_capture_v0/'
WORKFLOW = '.github/workflows/q3_reference_acquisition_v0.yml'
PROFILE_SHA256 = '31680dc2a8b2a8d367239893e6a7abbc6587f8e6f3c6cff9f580f00425e9c16b'
MAX_CONTROL = 16 * 1024 * 1024
AUTHORIZATIONS = {
    'token-preflight': 'AUTHORIZE_ZERO_GENERATION_TOKEN_PREFLIGHT_AND_30_DAY_ACTIONS_RETENTION',
    'capture': 'AUTHORIZE_204_SINGLE_ATTEMPT_CALLS_AND_30_DAY_ACTIONS_RAW_RETENTION',
}
CLAIMS = {
    'authority_effect': 'none', 'production_gate_eligible': False,
    'current_run_evidence': False, 'policy_activation': False,
    'source_authentication': 'not_established', 'label_correctness': 'not_verified',
    'slice_metadata_correctness': 'not_verified', 'metric_evaluated': False,
}


class ContractError(ValueError):
    """One stable code; never include raw text, credentials or provider errors."""


def require(value: bool, code: str) -> None:
    if not value:
        raise ContractError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def strict_json(raw: bytes, maximum: int = MAX_CONTROL) -> Any:
    require(type(raw) is bytes and 0 < len(raw) <= maximum and not raw.startswith(b'\xef\xbb\xbf'),
            'JSON_ENCODING_OR_SIZE')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'DUPLICATE_JSON_KEY'); out[key] = value
        return out
    def invalid(_):
        raise ContractError('NONFINITE_JSON')
    def walk(v, depth=0):
        require(depth <= 64, 'JSON_DEPTH')
        if type(v) is str:
            v.encode('utf-8', 'strict')
        elif type(v) is float:
            require(math.isfinite(v), 'NONFINITE_JSON')
        elif type(v) is list:
            for x in v: walk(x, depth + 1)
        elif type(v) is dict:
            for k, x in v.items(): walk(k, depth + 1); walk(x, depth + 1)
    try:
        out = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=pairs, parse_constant=invalid)
        walk(out)
        return out
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError('INVALID_JSON') from exc


def fields(obj: Any, names: set[str], code: str = 'FIELDS') -> None:
    require(type(obj) is dict and set(obj) == names, code)


def integer(value: Any, low: int, high: int, code: str = 'INTEGER') -> int:
    require(type(value) is int and low <= value <= high, code)
    return value


def sha256_string(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def relative(value: Any) -> str:
    require(type(value) is str and 0 < len(value) <= 1024
            and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', value) is not None
            and all(x not in ('.', '..') for x in value.split('/')), 'UNSAFE_PATH')
    return value


def safe_read(path: Path, maximum: int = MAX_CONTROL) -> bytes:
    """Open every directory component without following links; reject aliases."""
    path = Path(os.path.abspath(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = nxt
        item = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        try:
            a = os.fstat(item)
            require(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= maximum, 'FILE_BOUND')
            chunks = []; count = 0
            while True:
                block = os.read(item, min(65536, maximum + 1 - count))
                if not block: break
                chunks.append(block); count += len(block)
                require(count <= maximum, 'FILE_BOUND')
            b = os.fstat(item)
            st = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            ident = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink)
            require(ident(a) == ident(b) == ident(st) and count == a.st_size, 'FILE_CHANGED')
            return b''.join(chunks)
        finally:
            os.close(item)
    finally:
        os.close(fd)


def write_new(path: Path, raw: bytes, mode: int = 0o600) -> None:
    """Caller controls the existing parent. Never replace any existing entry."""
    require(type(raw) is bytes, 'OUTPUT_TYPE')
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    fd = None; identity = None
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     mode, dir_fd=parent)
        st = os.fstat(fd); identity = (st.st_dev, st.st_ino)
        os.fchmod(fd, mode)
        require(stat.S_IMODE(os.fstat(fd).st_mode) == mode, 'OUTPUT_MODE')
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            require(count > 0, 'OUTPUT_WRITE'); view = view[count:]
        os.fsync(fd)
        os.close(fd); fd = None
        require(safe_read(path, max(MAX_CONTROL, len(raw))) == raw, 'OUTPUT_READBACK')
        os.fsync(parent)
    except BaseException:
        if identity is not None:
            try:
                current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == identity:
                    os.unlink(path.name, dir_fd=parent)
            except OSError:
                pass
        raise
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def source_read(root, name: str) -> bytes:
    """A held immutable-byte snapshot supports final checks after workspace removal.

    Only in-process callers can supply this mapping; no CLI accepts injected code
    or a synthetic-provenance flag. The native controller obtains it from Git-bound
    source_snapshot before any downloaded dependency is executed.
    """
    relative(name)
    if type(root) is dict:
        raw = root.get(name)
        require(type(raw) is bytes and len(raw) <= MAX_CONTROL, 'SOURCE_SNAPSHOT_MEMBER')
        return raw
    return safe_read(root / name)


def load_profile(root: Path) -> dict:
    raw = source_read(root, PROFILE)
    require(digest(raw) == PROFILE_SHA256, 'UNSUPPORTED_PROFILE')
    p = strict_json(raw)
    require(p['repository'] == REPOSITORY and p['workflow'] == WORKFLOW, 'PROFILE_IDENTITY')
    return p


def verify_fixed_inputs(root: Path, p: dict) -> None:
    for name, sha in p['fixed_inputs'].items():
        require(digest(source_read(root, relative(name))) == sha, 'FIXED_INPUT_CHANGED')


def task_frame(root: Path, p: dict) -> list[dict]:
    verify_fixed_inputs(root, p)
    raw = source_read(root, FRAME + 'TASKS_DRAFT.jsonl')
    require(raw.endswith(b'\n') and b'\r' not in raw, 'TASK_REPRESENTATION')
    tasks = [strict_json(line) for line in raw.splitlines()]
    require(len(tasks) == 204, 'TASK_COUNT')
    by_id = {t['task_id']: t for t in tasks}
    require(len(by_id) == 204, 'DUPLICATE_TASK')
    order = strict_json(source_read(root, FRAME + 'TASK_ORDER.json'))['task_ids']
    require(len(order) == 204 and len(set(order)) == 204 and set(order) == set(by_id), 'TASK_ORDER')
    bindings = strict_json(source_read(root, FRAME + 'SOURCE_CONTEXT_BINDINGS.json'))
    sources = {}
    for s in bindings['sources']:
        b = source_read(root, relative(s['path']))
        require(len(b) == s['size_bytes'] and digest(b) == s['sha256']
                and blob_id(b) == s['git_blob_sha1'], 'CONTEXT_SOURCE')
        sources[s['source_id']] = b
    contexts = {}
    for c in bindings['contexts']:
        b = sources[c['source_id']][c['byte_start']:c['byte_end_exclusive']]
        require(len(b) == c['size_bytes'] and digest(b) == c['sha256'] and b.endswith(b'\n'), 'CONTEXT_RANGE')
        contexts[c['context_id']] = b.decode('utf-8')
    instructions = source_read(root, FRAME + 'COMMON_INSTRUCTIONS.txt').decode('utf-8')
    out = []
    for ordinal, task_id in enumerate(order, 1):
        t = by_id[task_id]; c = contexts[t['context_id']]
        require(t['task_form'] in ('contract_lookup', 'rule_application')
                and t['is_observation'] is False and t['is_q1_label'] is False, 'TASK_ROLE')
        prompt = instructions + '\nQuestion:\n' + t['question'] + '\n'
        logical = 'PULSE_Q3_CONTEXT_BEGIN\n' + c + 'PULSE_Q3_CONTEXT_END\n\n' + prompt
        require(digest(t['question'].encode()) == t['question_utf8_sha256']
                and digest(c.encode()) == t['source_context_sha256']
                and digest(prompt.encode()) == t['prompt_utf8_sha256']
                and digest(logical.encode()) == t['logical_request_utf8_sha256']
                and len(logical.encode()) == t['logical_request_size_bytes']
                and len(logical.encode()) <= p['limits']['max_logical_request_utf8_bytes'], 'REQUEST_CONSTRUCTION')
        out.append({'task_id': task_id, 'ordinal': ordinal, 'attempt': 1, 'task_form': t['task_form'],
                    'context': c, 'prompt': prompt, 'logical_request_text': logical,
                    'messages': [{'role': 'system', 'content': p['system_message']},
                                 {'role': 'user', 'content': logical}]})
    return out


def git_bytes(root: Path, args: list[str]) -> bytes:
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_LAZY_FETCH': '1'}
    proc = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
                           '-c', 'core.hooksPath=/dev/null', '-c', 'safe.directory=' + str(root),
                           '-C', str(root), *args], env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=30)
    require(proc.returncode == 0 and len(proc.stdout) <= MAX_CONTROL, 'SOURCE_GIT')
    return proc.stdout


def source_snapshot(root: Path, commit: str, p: dict) -> dict[str, bytes]:
    require(type(commit) is str and re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'SOURCE_COMMIT')
    require(git_bytes(root, ['rev-parse', '--verify', 'HEAD']).decode().strip() == commit, 'CHECKOUT_COMMIT')
    out = {}
    for name in p['source_files']:
        relative(name)
        b = safe_read(root / name)
        require(git_bytes(root, ['cat-file', 'blob', commit + ':' + name]) == b, 'DIRTY_SOURCE')
        out[name] = b
    require(len(out) == len(p['source_files']), 'SOURCE_DUPLICATE')
    return out


def validate_request(raw: bytes, p: dict) -> dict:
    r = strict_json(raw, 128 * 1024)
    fields(r, {'record_type', 'mode', 'repository', 'source_commit', 'profile_sha256',
               'task_file_sha256', 'authorization', 'approved_token_map_sha256', 'limits',
               'claims', 'new_spend_authorized'})
    require(r['record_type'] == 'q3_native_capture_request_v0' and r['repository'] == REPOSITORY, 'REQUEST_IDENTITY')
    require(type(r['mode']) is str and r['mode'] in AUTHORIZATIONS, 'MODE')
    require(type(r['source_commit']) is str and re.fullmatch(r'[a-f0-9]{40}', r['source_commit']), 'SOURCE_COMMIT')
    require(r['profile_sha256'] == PROFILE_SHA256 and
            r['task_file_sha256'] == p['fixed_inputs'][FRAME + 'TASKS_DRAFT.jsonl'], 'REQUEST_INPUT')
    require(r['authorization'] == AUTHORIZATIONS[r['mode']], 'EXPLICIT_AUTHORIZATION')
    require(encode(r['limits']) == encode(p['limits']) and encode(r['claims']) == encode(CLAIMS), 'REQUEST_LIMIT_OR_CLAIM')
    integer(r['new_spend_authorized'], 0, 0, 'SPEND')
    if r['mode'] == 'capture':
        require(sha256_string(r['approved_token_map_sha256']), 'PREFLIGHT_ANCHOR_REQUIRED')
    else:
        require(r['approved_token_map_sha256'] is None, 'PREFLIGHT_IS_NOT_CAPTURE')
    return r


def make_request(root: Path, commit: str, mode: str, authorization: str,
                 approved_token_map_sha256: str | None = None) -> bytes:
    p = load_profile(root); task_frame(root, p); source_snapshot(root, commit, p)
    raw = encode({'record_type': 'q3_native_capture_request_v0', 'mode': mode,
                  'repository': REPOSITORY, 'source_commit': commit, 'profile_sha256': PROFILE_SHA256,
                  'task_file_sha256': p['fixed_inputs'][FRAME + 'TASKS_DRAFT.jsonl'],
                  'authorization': authorization, 'approved_token_map_sha256': approved_token_map_sha256,
                  'limits': p['limits'], 'claims': dict(CLAIMS), 'new_spend_authorized': 0})
    validate_request(raw, p)
    return raw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--mode', choices=tuple(AUTHORIZATIONS), required=True)
    parser.add_argument('--authorization', required=True)
    parser.add_argument('--approved-token-map-sha256')
    args = parser.parse_args(argv)
    try:
        raw = make_request(args.repo_root.absolute(), args.source_commit, args.mode,
                           args.authorization, args.approved_token_map_sha256)
        sys.stdout.buffer.write(raw); sys.stdout.buffer.flush()
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Q3 request rejected; no execution or dispatch.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
