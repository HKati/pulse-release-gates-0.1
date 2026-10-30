#!/usr/bin/env python3
"""Offline verifier for the selected historical Q3 preservation package.

This is a historical regression reader, NOT a generic capture-handoff gate.
No network, tokenizer, model, dispatch, or repository writes.

Exit 0: integrity checks succeeded and selected external image fields matched;
        this does NOT authorize capture or establish full acceptance.
Exit 2: preserved evidence is internally verifiable, but image comparison blocks
        this historical token-map handoff (the expected result for this package).
Exit 1: integrity, identity, parsing, or evidence checks failed.

Only the two digest-pinned historical checker modules are loaded, in a temporary
folder. Other archive code is never executed. Temporary files are removed.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import os
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, Iterator
import zipfile

OLD = 'a9de035d1b3ac227359ca78a98274abe4c9ee186'
CURRENT = '72e8973e54d8f94422c0dabb264b8316ac8e4de6'
OUTER = '7228d89f93ea69a7129c7d1bc915f5a8b3b800f0ef862280605178c602e6f317'
PRIOR = '1455bb7dfdc45f96be7eadeddd609292b53d4451d0031631b91965a9e3aa1f5f'
INNER = 'b792a17d63142f0378af19a8ed7c65176356b91d7c9de3e0c9943f72db46a60a'
REQUEST = '41847879273f27e2132fed1f04b2201105f7c9eb0136b88a5ee8152961819c90'
TOKENMAP = '2c7bbb375614c5d4e7eb6766fec2da61ee3f557f55dd9a09ceac6d508c8c4c04'
WORKFLOW = '.github/workflows/q3_reference_acquisition_v0.yml'
RUN = '40253690074'
ARTIFACT_ID = '12621038763'
ARTIFACT_NAME = 'q3-reference-capture-40253690074-1'
CHECKER_BLOBS = {
    'q3_native_capture_contract_v0.py': '800bc41c73cb4a377b61fb5ae24c16b91c732981',
    'check_q3_native_capture_v0.py': '8515b30765c6a3f7509a4aaf4e5d7d105ea96b9b',
}

class ReviewError(ValueError):
    pass

def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewError(code)

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()

def strict_json(raw: bytes) -> Any:
    require(type(raw) is bytes and 0 < len(raw) <= 16 * 1024**2, 'JSON_SIZE')
    require(not raw.startswith(b'\xef\xbb\xbf'), 'JSON_BOM')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    def invalid(_):
        raise ReviewError('NONFINITE_JSON')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ReviewError('INVALID_JSON') from exc

def relative(name: str) -> bool:
    p = PurePosixPath(name)
    return (bool(name) and not p.is_absolute() and p.as_posix() == name
            and not any(part in ('', '.', '..') for part in name.split('/'))
            and '\\' not in name and ':' not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name))

def zip_members(raw: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(0 < len(infos) <= 2000, 'ZIP_COUNT')
            require(len({i.filename for i in infos}) == len(infos), 'ZIP_DUPLICATE')
            require(sum(i.file_size for i in infos) <= 256 * 1024**2, 'ZIP_TOTAL')
            out = {}
            for item in infos:
                require(relative(item.filename), 'ZIP_PATH')
                require(not item.is_dir() and not item.flag_bits & 1, 'ZIP_MEMBER')
                require(stat.S_IFMT(item.external_attr >> 16) in (0, stat.S_IFREG), 'ZIP_TYPE')
                require(item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'ZIP_COMPRESSION')
                require(0 <= item.file_size <= 16 * 1024**2, 'ZIP_MEMBER_SIZE')
                out[item.filename] = archive.read(item)
            return out
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ReviewError('ZIP_INVALID') from exc

def inspect_log(raw: bytes) -> str:
    text = raw.decode('utf-8-sig', 'strict')
    groups = re.findall(r'##\[group\]Runner Image\r?\n(.*?)##\[endgroup\]', text, re.S)
    require(len(groups) == 1, 'LOG_IMAGE_GROUP_AMBIGUOUS')
    versions = re.findall(r'\bVersion: ([A-Za-z0-9_.-]+)', groups[0])
    require(len(versions) == 1, 'LOG_IMAGE_VERSION_AMBIGUOUS')
    require(re.findall(r'\bImage: ([A-Za-z0-9_.-]+)', groups[0]) == ['ubuntu-24.04'], 'LOG_IMAGE_OS')
    commits = re.findall(r'EXPECTED_SOURCE_SHA: ([0-9a-f]{40})', text)
    require(bool(commits) and set(commits) == {OLD}, 'LOG_SOURCE_BINDING')
    require(re.findall(r'Complete job name: (\S+)', text) == ['acquire'], 'LOG_JOB_BINDING')
    uploads = re.findall(r'SHA256 digest of uploaded artifact is ([0-9a-f]{64})', text)
    require(uploads == [OUTER], 'LOG_ARTIFACT_DIGEST')
    finalized = re.findall(r'Artifact (\S+) successfully finalized\. Artifact ID (\d+)', text)
    require(finalized == [(ARTIFACT_NAME, ARTIFACT_ID)], 'LOG_ARTIFACT_IDENTITY')
    require(re.findall(r'Uploaded bytes (\d+)', text) == ['5897022'], 'LOG_ARTIFACT_SIZE')
    return versions[0]

def compare_images(startup: Any, observed: Any) -> dict[str, Any]:
    for value in (startup, observed):
        require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value) is not None,
                'IMAGE_VALUE_INVALID')
    match = startup == observed
    return {'startup_job_log_image': startup, 'retained_platform_image': observed,
            'match': match, 'reconciliation': 'MATCH' if match else 'UNRESOLVED_MISMATCH',
            'capture_handoff_approved': False, 'new_execution_authorized': False,
            'authority_effect': 'none',
            'review_disposition': 'NO_AUTHORIZATION_FROM_IMAGE_MATCH_ALONE' if match
                else 'REJECT_AND_REQUIRE_NEW_TOKEN_PREFLIGHT'}

def verify_sources(snapshot: dict, delta: dict, current_workflow: bytes) -> dict[str, bytes]:
    require(snapshot['source_commit'] == OLD and delta['historical_commit'] == OLD
            and delta['reviewed_main_commit'] == CURRENT, 'SOURCE_COMMITS')
    source = {}
    for name, item in snapshot['files'].items():
        require(relative(name), 'SOURCE_PATH')
        raw = item['content'].encode('utf-8')
        require(git_blob(raw) == item['sha'], 'HISTORICAL_BLOB')
        source[name] = raw
    rows = delta['rows']
    require(len(source) == len(rows) == 21 and len({r['path'] for r in rows}) == 21
            and {r['path'] for r in rows} == set(source), 'SOURCE_CLOSURE')
    profile = strict_json(source['PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json'])
    require(set(profile['source_files']) == set(source), 'DECLARED_SOURCE_CLOSURE')
    changes = []
    for row in rows:
        name = row['path']; old = source[name]
        current = current_workflow if name == WORKFLOW else old
        require(git_blob(old) == row['historical_git_blob_sha1']
                and digest(old) == row['historical_sha256']
                and len(old) == row['historical_size_bytes'], 'DELTA_HISTORICAL_BINDING')
        require(git_blob(current) == row['reviewed_main_git_blob_sha1']
                and digest(current) == row['reviewed_main_sha256']
                and len(current) == row['reviewed_main_size_bytes'], 'DELTA_CURRENT_BINDING')
        require(type(row['byte_identity_by_git_blob']) is bool
                and row['byte_identity_by_git_blob'] == (old == current), 'DELTA_EQUALITY')
        if old != current:
            changes.append(name)
    require(changes == [WORKFLOW] and delta['unchanged_paths'] == 20 and delta['changed_paths'] == 1,
            'DELTA_SCOPE')
    expected = source[WORKFLOW].replace(
        b'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a',
        b'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9')
    require(expected == current_workflow and git_blob(current_workflow) ==
            'a5adfa8f9c883760acc694f32951ae6a4c788d76', 'WORKFLOW_DELTA')
    return source

def verify_file_manifest(root: Path) -> None:
    expected = {}
    for line in (root / 'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
        value, name = line.split('  ', 1)
        require(re.fullmatch(r'[0-9a-f]{64}', value) is not None and relative(name), 'MANIFEST_ENTRY')
        require(name not in expected, 'MANIFEST_DUPLICATE')
        expected[name] = value
    actual = {}
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'PACKAGE_SYMLINK')
        if path.is_file() and path != root / 'SHA256SUMS.txt':
            name = path.relative_to(root).as_posix()
            actual[name] = digest(path.read_bytes())
    require(actual == expected, 'PACKAGE_MANIFEST')

def verify(root: Path, *, check_manifest: bool = True) -> dict[str, Any]:
    if check_manifest:
        verify_file_manifest(root)
    outer_raw = (root / 'original' / (ARTIFACT_NAME + '.zip')).read_bytes()
    require(len(outer_raw) == 5897022 and digest(outer_raw) == OUTER, 'ORIGINAL_IDENTITY')
    original = zip_members(outer_raw)
    require(set(original) == {'evidence.zip', 'receipt.json'}, 'OUTER_MEMBERS')
    require(digest(original['evidence.zip']) == INNER, 'INNER_IDENTITY')
    prior_raw = (root / 'prior_review/Q3_TOKEN_PREFLIGHT_POSTFLIGHT_40253690074.zip').read_bytes()
    require(digest(prior_raw) == PRIOR, 'PRIOR_REVIEW_IDENTITY')
    prior = zip_members(prior_raw)
    require(prior['evidence.zip'] == original['evidence.zip']
            and prior['receipt.json'] == original['receipt.json'], 'PRIOR_ORIGINAL_BINDING')
    source = verify_sources(strict_json(prior['reviewed_source_snapshot.json']),
        strict_json((root / 'source/source_delta.json').read_bytes()),
        (root / 'source/current_q3_reference_acquisition_v0.yml').read_bytes())
    data = zip_members(original['evidence.zip'])
    receipt = strict_json(original['receipt.json'])
    require(receipt['source_commit'] == OLD and receipt['request_sha256'] == REQUEST
            and receipt['archive_sha256'] == INNER and receipt['token_map_sha256'] == TOKENMAP
            and receipt['status'] == 'complete' and receipt['mode'] == 'token-preflight', 'RECEIPT')
    require(digest(data['request.json']) == REQUEST and digest(data['token-map.json']) == TOKENMAP,
            'REQUEST_TOKENMAP')
    for name, raw in source.items():
        require(data['source/' + name] == raw, 'ARCHIVED_SOURCE_BYTES')
    for name in ['platform.json', 'receipt.json', 'workflow_job_121350855532.log',
                 'run_metadata.json', 'jobs_metadata.json', 'artifact_metadata.json']:
        require((root / 'evidence' / name).read_bytes() == prior[name], 'PRESERVED_EVIDENCE_COPY')
    image = inspect_log(prior['workflow_job_121350855532.log'])
    platform = strict_json(data['platform.json'])
    control = strict_json(data['control-plane.json'])
    require(control['run_id'] == RUN and control['run_attempt'] == 1
            and control['source_commit'] == OLD, 'RUN_BINDING')
    prelaunch = strict_json(data['prelaunch.json'])
    require(prelaunch['platform_sha256'] == digest(data['platform.json']), 'PLATFORM_BINDING')
    tokenmap = strict_json(data['token-map.json'])
    counts = [len(row['input_ids']) for row in tokenmap['rows']]
    require(len(counts) == len({r['task_id'] for r in tokenmap['rows']}) == 204, 'TASKS')
    terminal = strict_json(data['terminal.json'])
    require(terminal['attempted_calls'] == 0 and len(terminal['occurrences']) == 204
            and all(r['status'] == 'not_requested' for r in terminal['occurrences']), 'ZERO_GENERATION')
    with tempfile.TemporaryDirectory(prefix='q3-review-') as directory:
        temporary = Path(directory)
        for name, expected_blob in CHECKER_BLOBS.items():
            raw = source['PULSE_safe_pack_v0/tools/' + name]
            require(git_blob(raw) == expected_blob, 'CHECKER_SOURCE')
            (temporary / name).write_bytes(raw)
        spec = importlib.util.spec_from_file_location('q3_held_checker', temporary / 'check_q3_native_capture_v0.py')
        require(spec is not None and spec.loader is not None, 'CHECKER_LOAD')
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
            archive = temporary / 'evidence.zip'; archive.write_bytes(original['evidence.zip'])
            replay = module.check_carrier(archive, source, INNER, REQUEST, OLD)
        finally:
            sys.dont_write_bytecode = previous
    require(replay == strict_json((root / 'checks/carrier_replay.json').read_bytes()), 'REPLAY_RECORD')
    image_review = compare_images(image, platform['runner_image'])
    result = {'record_type': 'q3_token_preflight_reconciliation_check_v0',
              'integrity_checks': 'PASS', 'source_bound_carrier_check': 'PASS',
              'historical_source_commit': OLD, 'reviewed_main_commit': CURRENT,
              'source_paths_compared': 21, 'unchanged_source_paths': 20,
              'changed_source_paths': [WORKFLOW],
              'task_count': len(counts), 'prompt_tokens': {'minimum': min(counts), 'maximum': max(counts), 'total': sum(counts)},
              'recorded_generation_calls': 0,
              'this_review_model_executed': False, 'this_review_tokenizer_executed': False,
              'native_origin_reauthenticated': False,
              'source_bound_replay': replay, 'runner_image_review': image_review,
              'original_complete_status_preserved': True,
              'repository_modified': False, 'workflow_dispatched': False,
              'production_gate_eligible': False, 'current_run_evidence': False,
              'policy_activation': False, 'metric_evaluated': False, 'authority_effect': 'none'}
    if check_manifest:
        require(strict_json((root / 'checks/verification.json').read_bytes()) == result,
                'RECORDED_VERIFICATION_DIFFERS')
    return result


PACKAGE_SHA256 = '0a91f36c1e7e738b27ab29a5428e3243a31e9840a4907f01dceabaccceca0c4e'
PACKAGE_SIZE = 2996419
PACKAGE_RELATIVE_PATH = 'preservation/q3_token_preflight_v0/run_40253690074_attempt_1/Q3_TOKEN_PREFLIGHT_RECONCILIATION_40253690074.zip'
DEFAULT_ARCHIVE = Path(__file__).resolve().parents[1] / PACKAGE_RELATIVE_PATH


def read_selected_archive(path: Path) -> bytes:
    """Read one exact ordinary archive before parsing or loading nested code."""
    path = Path(os.path.abspath(os.fspath(path)))
    for component in (path, *path.parents):
        require(not component.is_symlink(), 'PRESERVATION_SYMLINK')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'PRESERVATION_FILE_TYPE')
        require(before.st_size == PACKAGE_SIZE, 'PRESERVATION_SIZE')
        chunks = []
        remaining = PACKAGE_SIZE + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                'PRESERVATION_CHANGED_DURING_READ')
    finally:
        os.close(fd)
    require(len(raw) == PACKAGE_SIZE and digest(raw) == PACKAGE_SHA256,
            'PRESERVATION_IDENTITY')
    return raw


@contextmanager
def preserved_package(path: Path = DEFAULT_ARCHIVE) -> Iterator[Path]:
    """Unpack only the digest-pinned package into an isolated temporary tree."""
    members = zip_members(read_selected_archive(path))
    with tempfile.TemporaryDirectory(prefix='q3-preserved-') as folder:
        root = Path(folder)
        for name, raw in members.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
        yield root


def verify_archive(path: Path = DEFAULT_ARCHIVE) -> dict[str, Any]:
    with preserved_package(path) as root:
        return verify(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=DEFAULT_ARCHIVE,
                        help='Exact preserved ZIP, verified against the committed digest')
    args = parser.parse_args(argv)
    try:
        result = verify_archive(args.archive)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result['runner_image_review']['match'] else 2
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'integrity_checks': 'ERROR', 'error': str(exc),
                          'capture_handoff_approved': False,
                          'new_execution_authorized': False,
                          'authority_effect': 'none'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
