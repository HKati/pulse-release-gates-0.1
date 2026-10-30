#!/usr/bin/env python3
"""Bounded offline Q3 v0 postflight comparison; never authorize capture.

Read an explicitly digest-selected expectation and five retained input files.
Recompute native carrier checks using only the two reviewed, hash-pinned modules.
Compare run/job/artifact/log identities and the startup Runner Image record.
Exit 0 means CONSISTENT_OFFLINE, not authenticated evidence or capture permission.
Exit 2 means a retained image mismatch; exit 1 means an invalid/incomplete input.
No network, acquisition, tokenizer, model, dispatch or repository writes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import tempfile
from typing import Any
import zipfile
import zlib

REPOSITORY = 'HKati/pulse-release-gates-0.1'
REPOSITORY_ID = 1061766508
OWNER_ID = 128643840
WORKFLOW = '.github/workflows/q3_reference_acquisition_v0.yml'
WORKFLOW_ID = 396141483
PACK = 'PULSE_safe_pack_v0/'
PROFILE = PACK + 'profiles/q3_native_capture_v0.json'
PROFILE_SHA256 = '31680dc2a8b2a8d367239893e6a7abbc6587f8e6f3c6cff9f580f00425e9c16b'
REVIEWED_CHECKERS = {
    'q3_native_capture_contract_v0.py': '1648bd22e8a0a65c0cf254739a02a0cd44b567a845434891641e6e82cad6e960',
    'check_q3_native_capture_v0.py': '9f4ef119555b96ec52dc7d13deb6e7d507b7b360df179b3b35f11ddfb01e6a6e',
}
INPUTS = ('artifact.zip', 'run.json', 'jobs.json', 'artifact.json', 'job.log')
MAX_ARCHIVE = 64 * 1024**2
MAX_RECORD = 4 * 1024**2
MAX_LOG = 16 * 1024**2
MAX_EXPANDED = 256 * 1024**2
MAX_MEMBERS = 2000
LIMITS = {name: MAX_RECORD for name in INPUTS}
LIMITS.update({'artifact.zip': MAX_ARCHIVE, 'job.log': MAX_LOG})
EXPECTED_FIELDS = set('record_type repository source_commit run_id run_attempt job_id artifact_id '
                      'request_sha256 token_map_sha256 verifier_sha256 inputs source_files'.split())
BOUNDARIES = {
    'evidence_source_authentication': 'not_established_by_offline_comparison',
    'verifier_execution_attested': False,
    'capture_consent': 'not_evaluated', 'capture_handoff_approved': False,
    'new_execution_authorized': False, 'authority_effect': 'none',
    'production_gate_eligible': False, 'current_run_evidence': False,
    'policy_activation': False, 'metric_evaluated': False,
    'tokenization_reperformed': False, 'model_executed': False,
}


class PostflightError(ValueError):
    """Stable codes only; raw evidence and provider messages are not diagnostics."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PostflightError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def encode(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def fields(obj: Any, expected: set[str], code: str) -> None:
    require(type(obj) is dict and set(obj) == expected, code)


def positive(value: Any) -> bool:
    return type(value) is int and 0 < value <= 2**63 - 1


def sha(value: Any, length: int = 64) -> bool:
    return type(value) is str and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value) is not None


def strict_json(raw: bytes) -> Any:
    require(type(raw) is bytes and 0 < len(raw) <= MAX_LOG and not raw.startswith(b'\xef\xbb\xbf'), 'JSON_BOUND')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    def invalid(_):
        raise PostflightError('NONFINITE_JSON')
    def walk(obj, level=0):
        require(level <= 64, 'JSON_DEPTH')
        if type(obj) is str:
            obj.encode('utf-8', 'strict')
        elif type(obj) is float:
            require(math.isfinite(obj), 'NONFINITE_JSON')
        elif type(obj) is dict:
            for key, value in obj.items():
                walk(key, level + 1); walk(value, level + 1)
        elif type(obj) is list:
            for value in obj:
                walk(value, level + 1)
    try:
        obj = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=pairs, parse_constant=invalid)
        walk(obj)
        return obj
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PostflightError('INVALID_JSON') from exc


def safe_read(path: Path, maximum: int) -> bytes:
    """Linux CI reader: refuse symlinks, hardlinks, special files and read races."""
    path = Path(os.path.abspath(path))
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            os.close(parent); parent = nxt
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                    and 0 < before.st_size <= maximum, 'FILE_BOUND')
            chunks = []; size = 0
            while size <= maximum:
                chunk = os.read(fd, min(65536, maximum + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk); size += len(chunk)
            after = os.fstat(fd)
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_nlink, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            require(identity(before) == identity(after) == identity(current)
                    and size == before.st_size, 'FILE_CHANGED')
            return b''.join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def relative(name: Any) -> bool:
    return (type(name) is str and 0 < len(name) <= 1024
            and not PurePosixPath(name).is_absolute() and PurePosixPath(name).as_posix() == name
            and all(p not in ('', '.', '..') for p in name.split('/'))
            and '\\' not in name and ':' not in name
            and all(32 <= ord(c) < 127 for c in name))


def unzip(raw: bytes, maximum_members: int = MAX_MEMBERS) -> dict[str, bytes]:
    """Bound the central directory before ZipFile allocates its member objects."""
    require(type(raw) is bytes and 22 <= len(raw) <= MAX_ARCHIVE, 'ZIP_SIZE')
    end = len(raw) - 22
    require(raw[end:end + 4] == b'PK\x05\x06', 'ZIP_EOCD')  # no comments/ZIP64/multidisk
    _, disk, start_disk, count_disk, count, cd_size, cd_start, comment = struct.unpack_from('<4s4H2IH', raw, end)
    require(disk == start_disk == comment == 0 and count_disk == count
            and 0 < count <= maximum_members and cd_size <= 2 * 1024**2
            and cd_start + cd_size == end, 'ZIP_DIRECTORY_BOUND')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            require(len(members) == count and len({m.filename for m in members}) == count, 'ZIP_DUPLICATE_OR_COUNT')
            require(sum(m.file_size for m in members) <= MAX_EXPANDED, 'ZIP_EXPANDED_BOUND')
            out = {}
            for m in members:
                require(relative(m.filename) and m.orig_filename == m.filename and not m.is_dir(), 'ZIP_PATH')
                require(not m.flag_bits & 1 and stat.S_IFMT(m.external_attr >> 16) in (0, stat.S_IFREG), 'ZIP_MEMBER_TYPE')
                require(m.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        and 0 <= m.file_size <= MAX_ARCHIVE, 'ZIP_MEMBER_BOUND')
                with archive.open(m) as stream:
                    value = stream.read(m.file_size + 1)
                require(len(value) == m.file_size, 'ZIP_MEMBER_SIZE')
                out[m.filename] = value
            return out
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as exc:
        raise PostflightError('ZIP_INVALID') from exc


def selection(raw: bytes, expected_digest: str) -> dict:
    require(sha(expected_digest) and digest(raw) == expected_digest, 'EXPECTATION_DIGEST')
    e = strict_json(raw)
    fields(e, EXPECTED_FIELDS, 'EXPECTATION_FIELDS')
    require(e['record_type'] == 'q3_external_postflight_expectation_v0'
            and e['repository'] == REPOSITORY, 'EXPECTATION_IDENTITY')
    require(sha(e['source_commit'], 40) and type(e['run_id']) is str
            and re.fullmatch(r'[1-9][0-9]{0,18}', e['run_id']) is not None, 'EXPECTATION_SOURCE_RUN')
    require(type(e['run_attempt']) is int and e['run_attempt'] == 1
            and positive(e['job_id']) and positive(e['artifact_id']), 'EXPECTATION_EXECUTION')
    require(all(sha(e[k]) for k in ('request_sha256', 'token_map_sha256', 'verifier_sha256')), 'EXPECTATION_HASH')
    require(digest(safe_read(Path(__file__), MAX_RECORD)) == e['verifier_sha256'], 'VERIFIER_IDENTITY')
    fields(e['inputs'], set(INPUTS), 'EXPECTATION_INPUTS')
    for name, item in e['inputs'].items():
        fields(item, {'sha256', 'size_bytes'}, 'INPUT_FIELDS')
        require(sha(item['sha256']) and positive(item['size_bytes'])
                and item['size_bytes'] <= LIMITS[name], 'INPUT_BOUND')
    require(type(e['source_files']) is dict and len(e['source_files']) == 21, 'SOURCE_SELECTION')
    for name, item in e['source_files'].items():
        require(relative(name), 'SOURCE_PATH')
        fields(item, {'sha256', 'git_blob_sha1', 'size_bytes'}, 'SOURCE_FIELDS')
        require(sha(item['sha256']) and sha(item['git_blob_sha1'], 40)
                and positive(item['size_bytes']) and item['size_bytes'] <= MAX_LOG, 'SOURCE_BOUND')
    return e


def stamp(value: Any) -> datetime:
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?Z', value) is not None, 'TIMESTAMP')
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise PostflightError('TIMESTAMP') from exc


def equal_fields(obj: Any, expected: dict, code: str) -> None:
    require(type(obj) is dict and all(type(obj.get(k)) is type(v) and obj[k] == v
                                    for k, v in expected.items()), code)


def metadata(e: dict, raw: dict[str, bytes]) -> tuple[dict, dict]:
    run, jobs, art = (strict_json(raw[n]) for n in ('run.json', 'jobs.json', 'artifact.json'))
    api = 'https://api.github.com/repos/' + REPOSITORY
    rid = int(e['run_id']); attempt = e['run_attempt']; commit = e['source_commit']
    equal_fields(run, {'id': rid, 'run_attempt': attempt, 'head_sha': commit,
        'path': WORKFLOW, 'workflow_id': WORKFLOW_ID, 'status': 'completed',
        'conclusion': 'success', 'head_branch': 'main', 'event': 'workflow_dispatch',
        'url': f'{api}/actions/runs/{rid}'}, 'RUN_BINDING')
    equal_fields(run.get('head_commit'), {'id': commit}, 'RUN_COMMIT')
    for key in ('repository', 'head_repository'):
        repo = run.get(key)
        equal_fields(repo, {'id': REPOSITORY_ID, 'full_name': REPOSITORY, 'fork': False}, 'RUN_REPOSITORY')
        equal_fields(repo.get('owner'), {'login': 'HKati', 'id': OWNER_ID}, 'RUN_OWNER')
    for key in ('actor', 'triggering_actor'):
        equal_fields(run.get(key), {'login': 'HKati', 'id': OWNER_ID}, 'RUN_ACTOR')
    equal_fields(jobs, {'total_count': 1}, 'JOBS_COMPLETENESS')
    require(type(jobs.get('jobs')) is list and len(jobs['jobs']) == 1, 'JOBS_COMPLETENESS')
    job = jobs['jobs'][0]
    equal_fields(job, {'id': e['job_id'], 'run_id': rid, 'run_attempt': attempt,
        'head_sha': commit, 'head_branch': 'main', 'name': 'acquire',
        'status': 'completed', 'conclusion': 'success',
        'run_url': f'{api}/actions/runs/{rid}', 'url': f'{api}/actions/jobs/{e["job_id"]}'}, 'JOB_BINDING')
    require(job.get('labels') == ['ubuntu-24.04'], 'JOB_PLATFORM')
    require(type(job.get('steps')) is list and all(type(s) is dict for s in job['steps']), 'JOB_STEPS')
    startup = [s for s in job['steps'] if s.get('name') == 'Set up job']
    require(len(startup) == 1, 'STARTUP_STEP')
    equal_fields(startup[0], {'number': 1, 'status': 'completed', 'conclusion': 'success'}, 'STARTUP_STEP')
    require(stamp(run['run_started_at']) <= stamp(job['started_at']) <= stamp(startup[0]['started_at'])
            <= stamp(startup[0]['completed_at']) <= stamp(job['completed_at']) <= stamp(run['updated_at']), 'JOB_TIME_ORDER')
    equal_fields(art, {'id': e['artifact_id'], 'name': f'q3-reference-capture-{rid}-{attempt}',
        'size_in_bytes': e['inputs']['artifact.zip']['size_bytes'],
        'digest': 'sha256:' + e['inputs']['artifact.zip']['sha256'], 'expired': False,
        'url': f'{api}/actions/artifacts/{e["artifact_id"]}'}, 'ARTIFACT_BINDING')
    equal_fields(art.get('workflow_run'), {'id': rid, 'repository_id': REPOSITORY_ID,
        'head_repository_id': REPOSITORY_ID, 'head_branch': 'main', 'head_sha': commit}, 'ARTIFACT_RUN')
    require(stamp(job['started_at']) <= stamp(art['created_at']) <= stamp(job['completed_at'])
            and stamp(art['updated_at']) == stamp(art['created_at'])
            and stamp(art['expires_at']) > stamp(art['created_at']), 'ARTIFACT_CREATION_WINDOW')
    # Creation time + upload-log ID association are NOT an artifact-attempt attestation.
    return job, startup[0]


def inspect_log(raw: bytes, e: dict, startup: dict) -> dict:
    try:
        text = raw.decode('utf-8-sig', 'strict')
    except UnicodeError as exc:
        raise PostflightError('LOG_ENCODING') from exc
    require(len(raw) <= MAX_LOG and '\x00' not in text, 'LOG_BOUND')
    lines = text.splitlines(); parsed = []; continuation = []
    for index, line in enumerate(lines, 1):
        match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?Z) (.*)', line)
        if match is None:
            # GitHub prints this single multiline action input without per-line timestamps.
            # Only its two fixed sibling filenames and final blank line are supported;
            # an unprefixed image group, digest, identity or arbitrary text is rejected.
            require(bool(continuation) and line == continuation.pop(0), 'LOG_LINE_FORMAT')
            continue
        require(not continuation, 'LOG_MULTILINE_TRUNCATED')
        parsed.append((index, stamp(match[1]), match[2]))
        path_input = re.fullmatch(r'  path: (/[^\s]+)/evidence\.zip', match[2])
        if path_input is not None:
            parent = path_input[1]
            require(parent.endswith('/q3-reference-capture/' + e['run_id'] + '-' + str(e['run_attempt'])),
                    'LOG_OUTPUT_PATH')
            continuation = [parent + '/receipt.json', parent + '/failure.json', '']
    require(not continuation, 'LOG_MULTILINE_TRUNCATED')
    starts = [i for i, (_, _, line) in enumerate(parsed) if line == '##[group]Runner Image']
    require(len(starts) == 1, 'LOG_IMAGE_GROUP')
    start = starts[0]; end = start + 1
    while end < len(parsed) and parsed[end][2] != '##[endgroup]':
        require(not parsed[end][2].startswith('##[group]'), 'LOG_IMAGE_NESTING')
        end += 1
    require(end < len(parsed), 'LOG_IMAGE_UNCLOSED')
    require(all(stamp(startup['started_at']) <= t <= stamp(startup['completed_at'])
                for _, t, _ in parsed[start:end + 1]), 'LOG_IMAGE_OUTSIDE_STARTUP')
    content = parsed[start + 1:end]
    versions = [(i, value.removeprefix('Version: ')) for i, _, value in content if value.startswith('Version:')]
    images = [value.removeprefix('Image: ') for _, _, value in content if value.startswith('Image:')]
    require(len(versions) == 1 and images == ['ubuntu-24.04'], 'LOG_IMAGE_FIELDS')
    version = versions[0][1]
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', version) is not None, 'LOG_IMAGE_VALUE')
    payload = '\n'.join(v for _, _, v in parsed)
    for label, expected, width in [('EXPECTED_SOURCE_SHA', e['source_commit'], 40),
                                   ('Q3_NATIVE_REQUEST_SHA256', e['request_sha256'], 64)]:
        # Identify every field occurrence before validating its value. A malformed
        # repeated anchor must not disappear just because it is not hexadecimal.
        occurrences = [line for _, _, line in parsed
                       if re.match(r'\s*' + re.escape(label) + r'(?=[:\s]|$)', line)]
        require(bool(occurrences), 'LOG_REQUEST_SOURCE')
        for line in occurrences:
            match = re.fullmatch(r'\s*' + re.escape(label)
                                 + r': ([0-9a-f]{' + str(width) + r'})', line)
            require(match is not None and match[1] == expected, 'LOG_REQUEST_SOURCE')
    require(re.findall(r'^Complete job name: (\S+)$', payload, re.M) == ['acquire'], 'LOG_JOB')
    require(re.findall(r'^SHA256 digest of uploaded artifact is ([0-9a-f]{64})$', payload, re.M)
            == [e['inputs']['artifact.zip']['sha256']], 'LOG_ARTIFACT_DIGEST')
    require(re.findall(r'^Artifact (\S+) successfully finalized\. Artifact ID (\d+)$', payload, re.M)
            == [(f'q3-reference-capture-{e["run_id"]}-{e["run_attempt"]}', str(e['artifact_id']))], 'LOG_ARTIFACT_ID')
    require(re.findall(r'^Uploaded bytes (\d+)$', payload, re.M)
            == [str(e['inputs']['artifact.zip']['size_bytes'])], 'LOG_ARTIFACT_SIZE')
    return {'value': version, 'image': images[0], 'input': 'job.log',
            'version_line': versions[0][0], 'group_start_line': parsed[start][0],
            'group_end_line': parsed[end][0], 'sha256': digest(raw)}


def native_replay(inner: bytes, source: dict[str, bytes], e: dict) -> dict:
    """Load only reviewed archived checker bytes, never arbitrary supplied Python."""
    for name, pin in REVIEWED_CHECKERS.items():
        require(digest(source[PACK + 'tools/' + name]) == pin, 'UNREVIEWED_NATIVE_CHECKER')
    with tempfile.TemporaryDirectory(prefix='q3-postflight-') as folder:
        root = Path(folder)
        for name in REVIEWED_CHECKERS:
            (root / name).write_bytes(source[PACK + 'tools/' + name])
        path = root / 'evidence.zip'; path.write_bytes(inner)
        spec = importlib.util.spec_from_file_location('q3_postflight_native_replay', root / 'check_q3_native_capture_v0.py')
        require(spec is not None and spec.loader is not None, 'NATIVE_CHECKER_LOAD')
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode; sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
            return module.check_carrier(path, source, digest(inner), e['request_sha256'], e['source_commit'])
        except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
            raise PostflightError('NATIVE_CARRIER_REJECTED') from exc
        finally:
            sys.dont_write_bytecode = previous


def compare(expectation: bytes, expectation_sha256: str, raw: dict[str, bytes]) -> dict:
    e = selection(expectation, expectation_sha256)
    fields(raw, set(INPUTS), 'INPUT_SET')
    for name in INPUTS:
        value = raw[name]; pin = e['inputs'][name]
        require(type(value) is bytes and len(value) == pin['size_bytes']
                and digest(value) == pin['sha256'], 'INPUT_DIGEST_OR_SIZE')
    job, startup = metadata(e, raw)
    image = inspect_log(raw['job.log'], e, startup)
    outer = unzip(raw['artifact.zip'], 2)
    require(set(outer) == {'evidence.zip', 'receipt.json'}, 'ORIGINAL_ARCHIVE_MEMBERS')
    data = unzip(outer['evidence.zip'])
    receipt = strict_json(outer['receipt.json'])
    fields(receipt, set('record_type status mode source_commit archive_sha256 archive_size_bytes '
                        'request_sha256 token_map_sha256 result_sha256 claims'.split()), 'RECEIPT_FIELDS')
    equal_fields(receipt, {'record_type': 'q3_native_capture_receipt_v0', 'status': 'complete',
        'mode': 'token-preflight', 'source_commit': e['source_commit'],
        'archive_sha256': digest(outer['evidence.zip']), 'archive_size_bytes': len(outer['evidence.zip']),
        'request_sha256': e['request_sha256'], 'token_map_sha256': e['token_map_sha256'],
        'result_sha256': digest(data['result.json'])}, 'RECEIPT_BINDING')
    require(digest(data['request.json']) == e['request_sha256']
            and digest(data['token-map.json']) == e['token_map_sha256'], 'REQUEST_TOKEN_MAP_BINDING')
    source = {k[7:]: value for k, value in data.items() if k.startswith('source/')}
    require(set(source) == set(e['source_files']), 'SOURCE_SET')
    for name, value in source.items():
        pin = e['source_files'][name]
        require(digest(value) == pin['sha256'] and blob_id(value) == pin['git_blob_sha1']
                and len(value) == pin['size_bytes'], 'SOURCE_DIGEST_OR_SIZE')
    require(digest(source[PROFILE]) == PROFILE_SHA256, 'PROFILE_UNSUPPORTED')
    require(strict_json(source[PROFILE])['source_files'] == sorted(source), 'PROFILE_SOURCE_SET')
    control = strict_json(data['control-plane.json'])
    equal_fields(control, {'repository': REPOSITORY, 'run_id': e['run_id'], 'run_attempt': e['run_attempt'],
        'source_commit': e['source_commit'], 'workflow': WORKFLOW, 'head_branch': 'main',
        'actor': 'HKati', 'triggering_actor': 'HKati', 'event': 'workflow_dispatch'}, 'CONTROL_BINDING')
    replay = native_replay(outer['evidence.zip'], source, e)
    require(replay.get('complete') is True and replay.get('mode') == 'token-preflight'
            and replay.get('request_sha256') == e['request_sha256']
            and replay.get('token_map_sha256') == e['token_map_sha256'], 'NATIVE_REPLAY_RESULT')
    require(encode(receipt['claims']) == encode(replay['claims']), 'RECEIPT_CLAIMS')
    platform = strict_json(data['platform.json'])
    recorded_image = platform['runner_image']
    require(type(recorded_image) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', recorded_image) is not None,
            'PLATFORM_IMAGE_VALUE')
    match = image['value'] == recorded_image
    return {'record_type': 'q3_external_postflight_comparison_v0',
        'disposition': 'CONSISTENT_OFFLINE' if match else 'REJECT_EXTERNAL_CONTRADICTION',
        'input_integrity': 'PASS', 'source_bound_carrier_check': 'PASS',
        'selection': {k: e[k] for k in ('repository', 'source_commit', 'run_id', 'run_attempt',
            'job_id', 'artifact_id', 'request_sha256', 'token_map_sha256', 'verifier_sha256')},
        'expectation_sha256': expectation_sha256, 'input_bindings': e['inputs'],
        'source_selection_sha256': digest(encode(e['source_files'])),
        'native_checker_sha256': dict(REVIEWED_CHECKERS),
        'image_comparison': {'match': match, 'startup': image,
            'carrier': {'value': recorded_image, 'member': 'platform.json', 'field': 'runner_image',
                        'sha256': digest(data['platform.json'])}},
        'artifact_attempt_attestation': None, 'artifact_creation_window_check': 'PASS_LIMITED',
        'original_complete_status_preserved': True, **BOUNDARIES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expectation', type=Path, required=True)
    parser.add_argument('--expectation-sha256', required=True)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--check-report', type=Path,
                        help='Recompute and compare canonical report bytes; never trust a copied verdict')
    args = parser.parse_args(argv)
    try:
        expected = safe_read(args.expectation, MAX_RECORD)
        selection(expected, args.expectation_sha256)  # reject before reading the larger inputs
        raw = {n: safe_read(args.input_dir / n, LIMITS[n]) for n in INPUTS}
        result = compare(expected, args.expectation_sha256, raw)
        output = encode(result)
        if args.check_report is not None:
            require(safe_read(args.check_report, MAX_RECORD) == output, 'REPORT_RECOMPUTATION_MISMATCH')
        sys.stdout.buffer.write(output)
        return 0 if result['disposition'] == 'CONSISTENT_OFFLINE' else 2
    except (PostflightError, OSError, ValueError, KeyError, TypeError) as exc:
        code = str(exc) if isinstance(exc, PostflightError) else 'INVALID_OR_MISSING_INPUT'
        sys.stderr.buffer.write(encode({'record_type': 'q3_external_postflight_error_v0',
            'disposition': 'REJECT_INVALID_OR_INCOMPLETE', 'error_code': code, **BOUNDARIES}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
