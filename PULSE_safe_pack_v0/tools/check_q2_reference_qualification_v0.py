#!/usr/bin/env python3
"""Independent Q2 native-qualification checks; no model generation or authority.

The preparation checker is an independent input verifier, not a producer.
This module never imports/invokes the qualification supervisor or model worker.
Heavy imports occur only in the explicit, isolated verify-diagnostic phase.
"""
from __future__ import annotations

import argparse
import base64
import configparser
import copy
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import urllib.parse
import zipfile

PACK = 'PULSE_safe_pack_v0/'
TOOLS = PACK + 'tools/'
SELF = TOOLS + 'check_q2_reference_qualification_v0.py'
OLD_CHECKER = TOOLS + 'check_q2_reference_capture_v0.py'
WORKER = TOOLS + 'run_q2_reference_subject_v0.py'
SUPERVISOR = TOOLS + 'qualify_q2_reference_runtime_v0.py'
WORKFLOW = '.github/workflows/q2_reference_acquisition_v0.yml'
SELECTION = PACK + 'profiles/q2_reference_subject_v0.json'
WORKLOAD = PACK + 'examples/q2_reference_field_extraction_v0/requests.json'
MODEL_MAP = PACK + 'profiles/q2_reference_model_files_v0.json'
LOCK = PACK + 'requirements-q2-reference-v0.lock'
DIAGNOSTIC = PACK + 'profiles/q2_reference_diagnostic_v0.json'
SCHEMA = 'schemas/metrics/q2_reference_qualification_v0.schema.json'
RECORD_DIR = PACK + 'examples/q2_runtime_preparation_v0/run_37148637546/'
ORIGINAL_SOURCE = '77fc5d51896568db50a2a87f650711a65db8fe8c'
ORIGINAL_RUN = '37148637546'
ARCHIVE_SHA = 'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9'
ARCHIVE_SIZE = 508460811
RECORDS = {
    'preparation.json': '832b3626e846c96e5d65052ea54c966aabf0ed5f3976ecc5d3b4a3ced006ef4f',
    'q2-runtime-preparation-check.json': '8676b29834f376b44f08f96b19d60d1ab79a9f565167aabd25513cf8694037e3',
    'q2_reference_model_files_v0.json': 'b91289806a62957e2613f21afa950d4bf48b917074fde16d3e94681764d74078',
    'requirements-q2-reference-v0.lock': '60cec54ed62df95b299cdeaf386afc7ed0b72f4fb7ec466cf82905bb40168d0f',
}
FIXED_FILES = {
    SELECTION: 'e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e',
    WORKLOAD: 'fa0412c6a702e220e5d0c8b09a5e854fe35ac89d4801977eeee0f2a6e5cae997',
    MODEL_MAP: '7df82db50a623326e12c333b69e5ef621c169bdddc663425fd8ed8e4be307de2',
    LOCK: 'b5933b3e6867357ab906fe87b92eed9450a30687f3617ac9e3bd9501ae28a8de',
    **{RECORD_DIR + name: sha for name, sha in RECORDS.items()},
}
SOURCE_PATHS = tuple(sorted({SELF, OLD_CHECKER, WORKER, SUPERVISOR, WORKFLOW,
                             DIAGNOSTIC, SCHEMA, *FIXED_FILES}))
MAX_JSON = 16 * 1024 * 1024
MAX_FILE = 512 * 1024 * 1024
MAX_TOTAL = 1536 * 1024 * 1024
GENERATION = dict(do_sample=False, num_beams=1, num_return_sequences=1,
                  max_new_tokens=32, min_new_tokens=0, use_cache=True,
                  repetition_penalty=1.0, length_penalty=1.0, no_repeat_ngram_size=0,
                  bos_token_id=1, eos_token_id=2, pad_token_id=2)
DEFINITION_SHA = '688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5'
DIAGNOSTIC_VALUE = {
    'record_type': 'q2_reference_diagnostic_v0', 'call_id': 'diagnostic-0001',
    'attempt': 1, 'scored': False, 'retries': 0, 'generation_seed': 1729,
    'messages': [
        {'role': 'system', 'content': 'Read the short record. Return only the requested value, copied exactly from the record. Do not explain your answer.'},
        {'role': 'user', 'content': 'Record: diagnostic_marker=quartz.\nRequested field: diagnostic_marker.'},
    ],
    'generation': GENERATION,
    'per_generation_timeout_seconds': 15, 'authority_effect': 'none',
}


class QualificationCheckError(ValueError):
    """Stable non-sensitive error code."""


def check(condition, code):
    if not condition:
        raise QualificationCheckError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def parse(raw):
    check(len(raw) <= MAX_JSON and not raw.startswith(b'\xef\xbb\xbf'), 'json_bound_or_bom')
    def pairs(items):
        out = {}
        for key, value in items:
            check(key not in out, 'duplicate_json_key')
            out[key] = value
        return out
    def bad(_):
        raise QualificationCheckError('nonfinite_json')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)
        def walk(v, depth=0):
            check(depth <= 64, 'json_depth')
            if isinstance(v, str):
                v.encode('utf-8')
            elif type(v) is float:
                check(math.isfinite(v), 'nonfinite_json')
            elif type(v) is list:
                for x in v: walk(x, depth + 1)
            elif type(v) is dict:
                for k, x in v.items(): walk(k, depth + 1); walk(x, depth + 1)
        walk(value)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise QualificationCheckError('invalid_json') from exc


def fields(value, names, code):
    check(type(value) is dict and set(value) == set(names.split()), code)


def relative(name):
    check(type(name) is str and 0 < len(name) <= 4096, 'relative_path_type')
    p = PurePosixPath(name)
    check(not p.is_absolute() and p.as_posix() == name and '\\' not in name
          and ':' not in name and all(x not in ('', '.', '..') for x in name.split('/')),
          'unsafe_relative_path')
    return p


def read(path, limit=MAX_FILE):
    path = Path(path).absolute()
    for p in (path, *path.parents):
        check(not p.is_symlink(), 'linked_input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        check(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= limit,
              'input_type_or_size')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        b = os.fstat(fd)
        check((a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) ==
              (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns)
              and len(raw) == a.st_size and path.lstat().st_ino == a.st_ino,
              'input_changed')
        return raw
    finally:
        os.close(fd)


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        out.write(raw); out.flush(); os.fsync(out.fileno())


def git_blob(repo, commit, name):
    check(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'invalid_source_commit')
    relative(name)
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-c', 'safe.directory=' + str(repo), '-c', 'core.hooksPath=/dev/null',
        '-C', str(repo), 'cat-file', 'blob', f'{commit}:{name}'],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={'PATH': os.defpath, 'HOME': str(repo), 'LANG': 'C.UTF-8'}, timeout=30)
    check(result.returncode == 0, 'source_git_blob_unavailable')
    return result.stdout


def check_sources(root, repo, commit):
    rows = []
    for name in SOURCE_PATHS:
        raw = read(root / name, MAX_JSON)
        check(raw == git_blob(repo, commit, name), 'consumer_source_mismatch')
        if name in FIXED_FILES:
            check(sha(raw) == FIXED_FILES[name], 'fixed_repository_input_changed')
        rows.append({'path': name, 'size': len(raw), 'sha256': sha(raw)})
    check(parse(read(root / DIAGNOSTIC)) == DIAGNOSTIC_VALUE, 'diagnostic_changed')
    return rows


def adopted_inputs(root):
    raws = {}
    for name, digest in FIXED_FILES.items():
        raw = read(root / name, MAX_JSON)
        check(sha(raw) == digest, 'fixed_repository_input_changed')
        raws[name] = raw
    original = {name: raws[RECORD_DIR + name] for name in RECORDS}
    prep = parse(original['preparation.json'])
    check(prep['context']['source_commit'] == ORIGINAL_SOURCE
          and prep['context']['run_id'] == ORIGINAL_RUN
          and type(prep['context']['run_attempt']) is int and prep['context']['run_attempt'] == 1,
          'historical_preparation_rebound')
    adopted = parse(raws[MODEL_MAP]); candidate = parse(original['q2_reference_model_files_v0.json'])
    check(adopted['files'] == candidate['files'] and adopted['native_runtime_qualified'] is False
          and adopted['authority_effect'] == 'none', 'adopted_map_promoted')
    check(raws[LOCK].splitlines()[1:] == original['requirements-q2-reference-v0.lock'].splitlines()[1:],
          'adopted_lock_entry_changed')
    check(len(prep['files']) == 76 and len(prep['wheels']) == 30, 'original_inventory_changed')
    return prep, original, adopted


def unpack_verified_archive(archive, destination, prep, original):
    """The entire fixed archive is hashed BEFORE ZIP parsing or payload use."""
    raw = read(archive, ARCHIVE_SIZE)
    check(len(raw) == ARCHIVE_SIZE and sha(raw) == ARCHIVE_SHA, 'original_archive_mismatch')
    check(not destination.exists() and not destination.is_symlink(), 'staging_exists')
    # Original upload-artifact has a common parent, retaining the preparation
    # directory name. Rootless exports are not silently substituted for it.
    expected = {'q2-runtime-preparation/' + r['path']: r for r in prep['files']}
    expected['q2-runtime-preparation/preparation.json'] = {
        'path': 'preparation.json', 'size': len(original['preparation.json']),
        'sha256': RECORDS['preparation.json']}
    external = 'q2-runtime-preparation-check.json'
    expected[external] = {'path': external, 'size': len(original[external]), 'sha256': RECORDS[external]}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        check(len(infos) == 78 and len({i.filename for i in infos}) == 78, 'archive_member_count')
        check(set(i.filename for i in infos) == set(expected), 'archive_member_scope')
        total = 0
        for item in infos:
            relative(item.filename)
            mode = item.external_attr >> 16
            check(not item.is_dir() and not item.flag_bits & 1 and
                  (stat.S_IFMT(mode) in (0, stat.S_IFREG)), 'archive_special_member')
            row = expected[item.filename]
            check(type(row['size']) is int and item.file_size == row['size']
                  and 0 <= item.file_size <= MAX_FILE, 'archive_member_size')
            total += item.file_size
            check(total <= MAX_TOTAL, 'archive_total_size')
        destination.mkdir(mode=0o700)
        for item in infos:
            data = z.read(item)
            row = expected[item.filename]
            check(len(data) == row['size'] and sha(data) == row['sha256'], 'archive_payload_digest')
            if item.filename == external:
                check(data == original[external], 'original_checker_changed')
                put(destination / external, data)
            else:
                put(destination / 'bundle' / row['path'], data)
    return destination / 'bundle'


def check_prepared_bytes(bundle, source_root, repo):
    # The old independent checker's source is itself in the checked consumer
    # closure. Its historical git lookup must use ORIGINAL_SOURCE, never the
    # consumer commit. No producer/worker module is imported here.
    spec = importlib.util.spec_from_file_location('q2_original_independent_checker', source_root / OLD_CHECKER)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    # The root supervisor reads a runner-owned checkout. Supply the new
    # independent reader's exact-path safe.directory exception, not a global
    # wildcard or a rewrite of the historical checker/source identity.
    old.git_blob = git_blob
    return old.inspect_bundle(bundle, RECORDS['preparation.json'], ORIGINAL_SOURCE, ORIGINAL_RUN, repo)


def tree_inventory(root):
    rows = []; total = 0
    for p in sorted(root.rglob('*')):
        name = p.relative_to(root).as_posix()
        if p.is_symlink():
            check(name == 'lib64' and os.readlink(p) == 'lib', 'environment_symlink')
            rows.append({'path': name, 'symlink': 'lib'})
        elif p.is_dir():
            continue
        else:
            raw = read(p)
            total += len(raw)
            check(total <= 4 * 1024**3 and len(rows) < 100000, 'environment_inventory_bound')
            check(not name.endswith(('.pyc', '.pyo')), 'compiled_python_cache_forbidden')
            rows.append({'path': name, 'size': len(raw), 'sha256': sha(raw),
                         'mode': stat.S_IMODE(p.stat().st_mode)})
    return rows


def normalized(name):
    check(type(name) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', name), 'distribution_name')
    return re.sub('[-_.]+', '-', name).lower()


def installed_path(member, distribution):
    relative(member)
    parts = PurePosixPath(member).parts
    if len(parts) >= 3 and parts[0].endswith('.data'):
        kind = parts[1]; tail = '/'.join(parts[2:])
        prefixes = {'purelib': 'lib/python3.11/site-packages/',
                    'platlib': 'lib/python3.11/site-packages/', 'scripts': 'bin/',
                    'data': '', 'headers': f'include/site/python3.11/{distribution}/'}
        check(kind in prefixes, 'unsupported_wheel_data_scheme')
        return prefixes[kind] + tail, kind == 'scripts'
    return 'lib/python3.11/site-packages/' + member, False


def frozen_bootstrap_inventory(raw):
    """Derive the expected post-freeze rows without rewriting the bootstrap.

    The bootstrap inventory precedes installation and root ownership. The
    supervisor deterministically removes only group/other write permission
    (mode & ~0o022). Keep every other field and bit exact, including hashes,
    sizes, symlink targets and owner/execute/special permission bits.
    """
    rows = parse(raw)
    check(type(rows) is list and 0 < len(rows) <= 100000, 'bootstrap_inventory_shape')
    result = {}
    for row in rows:
        check(type(row) is dict and type(row.get('path')) is str, 'bootstrap_inventory_row')
        name = row['path']; relative(name)
        check(name not in result, 'duplicate_bootstrap_path')
        if 'symlink' in row:
            fields(row, 'path symlink', 'bootstrap_inventory_row')
            check(name == 'lib64' and row['symlink'] == 'lib', 'bootstrap_inventory_symlink')
            result[name] = dict(row)
        else:
            fields(row, 'path size sha256 mode', 'bootstrap_inventory_row')
            check(type(row['size']) is int and 0 <= row['size'] <= MAX_FILE
                  and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256'])
                  and type(row['mode']) is int and 0 <= row['mode'] <= 0o7777,
                  'bootstrap_inventory_value')
            result[name] = {**row, 'mode': row['mode'] & ~0o022}
    return result


def verify_installation(venv, bundle, bootstrap, pip_report):
    """Compare installed wheel payloads to fixed wheel bytes, not their RECORD claims.

    Generated launchers/installation metadata are tracked separately. The worker
    never executes those launchers. Bootstrap pip/interpreter is separately bound,
    and not misrepresented as one of the thirty adopted distributions.
    """
    preparation_raw = read(bundle / 'preparation.json')
    check(sha(preparation_raw) == RECORDS['preparation.json'], 'installation_preparation_not_fixed')
    prep = parse(preparation_raw)
    expected_packages = {row['name']: row['version'] for row in prep['wheels']}
    report = parse(read(pip_report))
    check(report.get('version') == '1' and type(report.get('install')) is list
          and len(report['install']) == len(expected_packages), 'installation_report_closure')
    downloads = {}
    by_name = {r['name']: r for r in prep['wheels']}
    for item in report['install']:
        name = normalized(item['metadata']['name']); version = item['metadata']['version']
        check(name not in downloads and expected_packages.get(name) == version, 'installed_distribution_substitution')
        url = urllib.parse.urlsplit(item['download_info']['url'])
        row = by_name[name]
        check(url.scheme == 'file' and not url.netloc and not url.query and not url.fragment
              and Path(urllib.parse.unquote(url.path)) == bundle / row['path'], 'nonlocal_installation')
        hashes = item['download_info']['archive_info']['hashes']
        check(hashes.get('sha256') == row['sha256'], 'install_report_wheel_hash')
        downloads[name] = version
    check(downloads == expected_packages, 'incomplete_installed_closure')
    actual_rows = tree_inventory(venv)
    actual = {x['path']: x for x in actual_rows}
    bootstrap_raw = read(bootstrap)
    before = frozen_bootstrap_inventory(bootstrap_raw)
    wheel_owned = {}; generated = set(); launchers = set(); distributions = {}
    base = 'lib/python3.11/site-packages/'
    for row in prep['wheels']:
        wheel = read(bundle / row['path'])
        check(len(wheel) == row['size'] and sha(wheel) == row['sha256'], 'wheel_changed_after_preflight')
        with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
            infos = archive.infolist()
            check(len(infos) <= 50000 and len({x.filename for x in infos}) == len(infos), 'wheel_members')
            for info in infos:
                if info.is_dir():
                    relative(info.filename.rstrip('/')); continue
                relative(info.filename)
                check(stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG), 'wheel_special_file')
                check(info.file_size <= MAX_FILE, 'wheel_member_size')
                member = info.filename
                dst, script = installed_path(member, row['name'])
                if member.endswith('.dist-info/RECORD'):
                    generated.add(dst); continue
                raw = archive.read(info)
                if script and raw.startswith((b'#!python\n', b'#!pythonw\n')):
                    raw = ('#!' + str(venv / 'bin/python') + '\n').encode() + raw.split(b'\n', 1)[1]
                check(dst not in wheel_owned, 'wheel_payload_collision')
                check(dst in actual and sha(read(venv / dst)) == sha(raw), 'installed_payload_mismatch')
                wheel_owned[dst] = sha(raw)
                if member.endswith('.dist-info/METADATA'):
                    dist_dir = dst.rsplit('/', 1)[0]
                    generated.update(dist_dir + '/' + suffix for suffix in ('INSTALLER', 'REQUESTED', 'direct_url.json'))
                    distributions[row['name']] = {'version': row['version'], 'metadata': dst}
                if member.endswith('.dist-info/entry_points.txt'):
                    ep = configparser.ConfigParser(interpolation=None)
                    ep.optionxform = str; ep.read_string(raw.decode('utf-8'))
                    for section in ('console_scripts', 'gui_scripts'):
                        for name in ep[section] if ep.has_section(section) else ():
                            check(re.fullmatch('[A-Za-z0-9_.-]+', name) is not None, 'entrypoint_name')
                            launchers.add('bin/' + name)
    allowed_bootstrap = set()
    for name, row in before.items():
        if name in wheel_owned or name in generated or name in launchers:
            continue
        check(actual.get(name) == row, 'bootstrap_runtime_changed')
        allowed_bootstrap.add(name)
    # Extra executable/importable files are not legitimized by a rehashed RECORD.
    for name in actual:
        check(name in wheel_owned or name in allowed_bootstrap or name in generated or name in launchers,
              'unowned_installed_file')
    for name in generated & set(actual):
        raw = read(venv / name, MAX_JSON)
        if name.endswith('/INSTALLER'):
            check(raw == b'pip\n', 'installer_metadata')
        elif name.endswith('/REQUESTED'):
            check(raw == b'', 'requested_metadata')
        elif name.endswith('/direct_url.json'):
            value = parse(raw); url = urllib.parse.urlsplit(value.get('url', ''))
            check(url.scheme == 'file' and not url.netloc and
                  Path(urllib.parse.unquote(url.path)) in {bundle / r['path'] for r in prep['wheels']},
                  'installed_direct_url')
        elif name.endswith('/RECORD'):
            for rec in csv.reader(io.StringIO(raw.decode('utf-8'))):
                check(len(rec) == 3, 'installed_record_shape')
                p = (venv / base / rec[0]).resolve()
                check(p.is_relative_to(venv), 'installed_record_escape')
                if rec[0].endswith(('.pyc', '.pyo')):
                    check(not p.exists(), 'installed_bytecode'); continue
                data = read(p)
                if rec[1]:
                    check(rec[1] == 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                          and rec[2] == str(len(data)), 'installed_record_digest')
                else:
                    check(p == venv / name and rec[2] == '', 'unhashed_installed_record')
    cfg = read(venv / 'pyvenv.cfg', MAX_JSON).decode()
    check('include-system-site-packages = false' in cfg, 'system_site_packages_enabled')
    return {'record_type': 'q2_native_installation_check_v0', 'distributions': distributions,
            'wheel_payload_file_count': len(wheel_owned),
            'generated_non_worker_launchers': sorted(launchers & set(actual)),
            'bootstrap_inventory_sha256': sha(bootstrap_raw),
            'pip_report_sha256': sha(read(pip_report)), 'inventory': actual_rows,
            'authority_effect': 'none', 'production_gate_eligible': False}


def native_target():
    check(platform.python_implementation() == 'CPython' and platform.python_version() == '3.11.16', 'native_python_required')
    check(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'native_machine_required')
    osr = platform.freedesktop_os_release()
    check(osr.get('ID') == 'ubuntu' and osr.get('VERSION_ID') == '24.04', 'native_ubuntu_required')




def verify_run_mount(value, unit):
    """Recheck retained kernel mount records without importing the supervisor.

    These are observations from the trusted external collector, not a child's
    declaration and not a proof against a malicious host. Missing old-format
    /run evidence is rejected, never silently grandfathered as qualified.
    """
    check(type(unit) is str and re.fullmatch(r'pulse-q2-[a-f0-9]{24}-[a-z]+\.service', unit), 'sandbox_unit')
    fields(value, 'host_namespace child_namespace host_mountinfo child_mountinfo mount_stats', 'run_mount_fields')
    host_ns = value['host_namespace']; child_ns = value['child_namespace']
    check(type(host_ns) is str and type(child_ns) is str and host_ns != child_ns
          and re.fullmatch(r'mnt:\[[1-9][0-9]*\]', host_ns)
          and re.fullmatch(r'mnt:\[[1-9][0-9]*\]', child_ns), 'mount_namespace_not_separate')
    def decoded_path(word):
        check(re.search(r'\\(?!040|011|012|134)', word) is None, 'run_mountinfo_escape')
        word = re.sub(r'\\(040|011|012|134)', lambda m: chr(int(m.group(1), 8)), word)
        check(word.startswith('/') and (word == '/' or
              all(x not in ('', '.', '..') for x in word[1:].split('/'))), 'run_mountinfo_path')
        return word
    def parse_mounts(raw):
        check(type(raw) is str and 0 < len(raw.encode('utf-8')) <= 262144
              and raw.endswith('\n') and '\x00' not in raw, 'run_mountinfo_bound')
        lines = raw.splitlines(); check(0 < len(lines) <= 4096, 'run_mountinfo_bound')
        seen = set(); result = []
        for line in lines:
            words = line.split(' ')
            check(words.count('-') == 1, 'run_mountinfo_record')
            index = words.index('-')
            check(index >= 6 and len(words) == index + 4 and all(words)
                  and re.fullmatch(r'[1-9][0-9]*', words[0])
                  and re.fullmatch(r'[1-9][0-9]*', words[1])
                  and re.fullmatch(r'(0|[1-9][0-9]*):(0|[1-9][0-9]*)', words[2]), 'run_mountinfo_record')
            check(words[0] not in seen, 'run_mountinfo_duplicate_id'); seen.add(words[0])
            result.append((words[2], decoded_path(words[3]), decoded_path(words[4]),
                           set(words[5].split(',')), words[index + 1], words[index + 3].split(',')))
        return result
    host = parse_mounts(value['host_mountinfo']); child = parse_mounts(value['child_mountinfo'])
    roots = [row for row in child if row[2] == '/run']
    check(len(roots) == 1, 'run_mount_missing_or_stacked')
    device, root, _, options, fs, super_options = roots[0]
    check(fs == 'tmpfs' and root == '/' and device.startswith('0:') and device != '0:0'
          and all(row[0] != device for row in host), 'host_run_not_hidden')
    check({'nosuid', 'nodev', 'noexec'} <= options and not ({'suid', 'dev', 'exec'} & options)
          and len(options & {'ro', 'rw'}) == 1, 'run_mount_flags')
    size_options = [option[5:] for option in super_options if option.startswith('size=')]
    check(len(size_options) == 1, 'run_tmpfs_size')
    match = re.fullmatch(r'([1-9][0-9]*)([kKmMgG]?)', size_options[0])
    check(match is not None, 'run_tmpfs_size')
    multiplier = {'':1, 'k':1024, 'm':1048576, 'g':1073741824}[match[2].lower()]
    check(int(match[1]) * multiplier == 16777216, 'run_tmpfs_size')
    subtree = [row for row in child if row[2] == '/run' or row[2].startswith('/run/')]
    names = [row[2] for row in subtree]
    check(len(names) <= 4 and len(set(names)) == len(names), 'run_submount_scope')
    stats = value['mount_stats']
    check(type(stats) is dict and set(stats) == set(names), 'run_mount_stat_scope')
    for dev, source, target, flags, _, _super_options in subtree:
        s = stats[target]; fields(s, 'device inode uid gid mode', 'run_mount_stat')
        check(type(s['device']) is str and s['device'] == dev
              and all(type(s[k]) is int for k in ('inode', 'uid', 'gid', 'mode'))
              and s['inode'] > 0 and s['uid'] == s['gid'] == 0 and stat.S_ISDIR(s['mode']), 'run_mount_stat')
        if target == '/run':
            check(s['mode'] == 0o40755, 'run_root_permissions')
        else:
            check('ro' in flags and 'rw' not in flags, 'run_submount_writable')
            if target == '/run/systemd/incoming':
                check(source in ('/systemd/propagate/' + unit, '/run/systemd/propagate/' + unit)
                      and s['mode'] == 0o40600, 'run_incoming_not_private')
            else:
                check(target in ('/run/user', '/run/credentials')
                      and source in ('/systemd/inaccessible/dir', '/run/systemd/inaccessible/dir')
                      and s['mode'] == 0o40000, 'run_unexpected_submount')


def verify_sandbox_observation(value, stage):
    fields(value, 'stage unit pid host_netns child_netns uid no_new_privs capabilities '
                  'ipv4_blocked ipv6_blocked memory_max memory_swap_max pids_max cpu_max '
                  'properties run_mount', 'sandbox_fields')
    check(value['stage'] == stage and type(value['pid']) is int and value['pid'] > 0, 'sandbox_stage')
    check(re.fullmatch(r'pulse-q2-[a-f0-9]{24}-[a-z]+\.service', value['unit'])
          and value['unit'].endswith('-' + stage + '.service'), 'sandbox_unit')
    check(all(type(value[k]) is str and re.fullmatch(r'net:\[[0-9]+\]', value[k])
              for k in ('host_netns', 'child_netns')) and value['host_netns'] != value['child_netns'],
          'network_namespace_not_separate')
    check(type(value['uid']) is int and value['uid'] == 65534 and value['no_new_privs'] is True
          and value['capabilities'] == '0000000000000000' and value['ipv4_blocked'] is True
          and value['ipv6_blocked'] is True, 'sandbox_privilege_or_network')
    check(value['memory_max'] == '4294967296' and value['memory_swap_max'] == '0'
          and value['pids_max'] == '64' and value['cpu_max'] == '100000 100000', 'cgroup_limits')
    props = value['properties']
    fields(props, 'PrivateNetwork NoNewPrivileges ProtectSystem ProtectHome KillMode SendSIGKILL '
                  'User Group CapabilityBoundingSet RestrictAddressFamilies RuntimeMaxUSec', 'sandbox_property_scope')
    for k, v in {'PrivateNetwork': 'yes', 'NoNewPrivileges': 'yes', 'ProtectSystem': 'strict',
                 'ProtectHome': 'yes', 'KillMode': 'control-group', 'SendSIGKILL': 'yes',
                 'User': '65534', 'Group': '65534', 'CapabilityBoundingSet': '',
                 'RestrictAddressFamilies': 'AF_UNIX'}.items():
        check(props.get(k) == v, 'service_property_mismatch')
    check(props.get('RuntimeMaxUSec') == {'installer': '8min', 'installcheck': '5min',
          'worker': '3min', 'decodecheck': '3min'}.get(stage), 'service_runtime_limit')
    verify_run_mount(value['run_mount'], value['unit'])


def validate_tokens_and_text(response, expected_input, decode):
    fields(response, 'record_type binding call_id attempt scored input_ids new_token_ids '
                     'text text_utf8_base64 stop_reason effective_generation runtime', 'response_fields')
    check(response['record_type'] == 'q2_native_diagnostic_response_v0'
          and response['call_id'] == 'diagnostic-0001' and type(response['attempt']) is int
          and response['attempt'] == 1 and response['scored'] is False, 'diagnostic_occurrence')
    for name, maximum in (('input_ids', 4096), ('new_token_ids', 32)):
        ids = response[name]
        check(type(ids) is list and 1 <= len(ids) <= maximum and
              all(type(i) is int and 0 <= i < 49152 for i in ids), 'invalid_token_inventory')
    check(response['input_ids'] == expected_input, 'input_tokens_changed')
    ids = response['new_token_ids']
    if ids[-1] == 2:
        check(2 not in ids[:-1] and response['stop_reason'] == 'eos', 'eos_record_mismatch')
    else:
        check(len(ids) == 32 and 2 not in ids and response['stop_reason'] == 'token_limit', 'incomplete_generation')
    check(type(response['text']) is str, 'text_type')
    raw = response['text'].encode('utf-8')
    check(response['text_utf8_base64'] == base64.b64encode(raw).decode('ascii'), 'original_text_bytes')
    check(decode(ids) == response['text'], 'independent_decoding_mismatch')


def verify_diagnostic(source_root, bundle, venv, prelaunch_raw, installation_raw, response_raw, ready_raw, observation,
                      bootstrap, pip_report, installer_observation, installcheck_observation,
                      expected_source, expected_run, expected_source_inventory):
    native_target()
    check(sys.flags.isolated and sys.prefix != sys.base_prefix
          and Path(sys.prefix).resolve() == venv.resolve(), 'checker_not_in_verified_venv')
    pre = parse(prelaunch_raw); installation = parse(installation_raw)
    response = parse(response_raw); ready = parse(ready_raw)
    for value, raw in ((pre, prelaunch_raw), (installation, installation_raw), (response, response_raw), (ready, ready_raw)):
        check(encoded(value) == raw, 'noncanonical_native_record')
    fields(pre, 'record_type context source_files preparation_source_commit preparation_run_id '
                'artifact_sha256 selection_sha256 workload_sha256 diagnostic_sha256 '
                'installation_sha256 environment_inventory_sha256 limits authority_effect '
                'production_gate_eligible scored_call_count', 'prelaunch_fields')
    check(re.fullmatch('[0-9a-f]{40}', expected_source) and re.fullmatch('[1-9][0-9]{0,19}', expected_run),
          'external_context_shape')
    check(pre['context']['source_commit'] == expected_source and pre['context']['run_id'] == expected_run
          and pre['context']['repository'] == 'HKati/pulse-release-gates-0.1'
          and type(pre['context']['run_attempt']) is int and pre['context']['run_attempt'] == 1
          and pre['context']['actor'] == 'HKati' and pre['context']['event'] == 'workflow_dispatch'
          and pre['context']['workflow'] == WORKFLOW, 'external_context_mismatch')
    check(sha(encoded(pre['source_files'])) == expected_source_inventory, 'external_source_inventory')
    verify_sandbox_observation(installer_observation, 'installer')
    verify_sandbox_observation(installcheck_observation, 'installcheck')
    check(pre['record_type'] == 'q2_native_prelaunch_v0' and pre['authority_effect'] == 'none'
          and pre['production_gate_eligible'] is False and type(pre['scored_call_count']) is int
          and pre['scored_call_count'] == 0, 'prelaunch_authority')
    check(pre['preparation_source_commit'] == ORIGINAL_SOURCE and pre['preparation_run_id'] == ORIGINAL_RUN
          and pre['artifact_sha256'] == ARCHIVE_SHA, 'historical_binding')
    check(pre['selection_sha256'] == FIXED_FILES[SELECTION] and pre['workload_sha256'] == FIXED_FILES[WORKLOAD],
          'selected_input_binding')
    check(encoded(pre['limits']) == encoded({'generation_seconds': 15, 'phase_seconds': 1200,
                            'memory_bytes': 4294967296, 'tasks': 64}), 'limits_changed')
    check(sha(installation_raw) == pre['installation_sha256'], 'installation_binding')
    recomputed_installation = verify_installation(venv, bundle, bootstrap, pip_report)
    check(encoded(recomputed_installation) == installation_raw, 'installation_recomputation_mismatch')
    check(tree_inventory(venv) == installation['inventory'] and
          sha(encoded(installation['inventory'])) == pre['environment_inventory_sha256'], 'runtime_mutated')
    selected = parse(read(source_root / SELECTION)); diagnostic = parse(read(source_root / DIAGNOSTIC))
    check(encoded(diagnostic) == encoded(DIAGNOSTIC_VALUE) and sha(read(source_root / DIAGNOSTIC)) == pre['diagnostic_sha256'],
          'unfixed_diagnostic')
    for row in pre['source_files']:
        relative(row['path']); raw = read(source_root / row['path'], MAX_JSON)
        check(len(raw) == row['size'] and sha(raw) == row['sha256'], 'source_mutated')
    check([r['path'] for r in pre['source_files']] == list(SOURCE_PATHS), 'source_scope')
    adopted_inputs(source_root)
    model_map = parse(read(source_root / MODEL_MAP))
    for row in model_map['files']:
        raw = read(bundle / row['path'])
        check(sha(raw) == row['sha256'] and len(raw) == row['size'], 'model_mutated')
    # Shared pinned tokenizer/JCS libraries are explicit common dependencies.
    # There is no model import, model load, model call or producer invocation.
    import importlib.metadata
    import rfc8785
    import transformers
    from transformers import AutoTokenizer, GenerationConfig
    for module in (rfc8785, transformers):
        check(Path(module.__file__).resolve().is_relative_to(venv.resolve()), 'checker_module_outside_venv')
    check(importlib.metadata.version('transformers') == '4.57.6'
          and importlib.metadata.version('torch') == '2.8.0+cpu'
          and importlib.metadata.version('rfc8785') == '0.1.4', 'installed_versions')
    check(sha(rfc8785.dumps(selected['release_subject']['definition'])) == DEFINITION_SHA, 'definition_jcs')
    check(rfc8785.dumps({'a': 1.0, 'b': -0.0}) == b'{"a":1,"b":0}', 'jcs_number_profile')
    check(rfc8785.dumps({'\ue000': 1, '\U00010000': 2}) == '{"\U00010000":2,"\ue000":1}'.encode(), 'jcs_utf16_order')
    tokenizer = AutoTokenizer.from_pretrained(str(bundle / 'model'), local_files_only=True,
                                              trust_remote_code=False, use_fast=True)
    check(tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id) == (1, 2, 2),
          'loaded_tokenizer_identity')
    ids = tokenizer.apply_chat_template(diagnostic['messages'], tokenize=True, add_generation_prompt=True)
    validate_tokens_and_text(response, ids, lambda x: tokenizer.decode(x, skip_special_tokens=True,
                                                                      clean_up_tokenization_spaces=False))
    binding = {'prelaunch_sha256': sha(prelaunch_raw), 'source_commit': pre['context']['source_commit'],
               'run_id': pre['context']['run_id'], 'run_attempt': 1}
    check(encoded(response['binding']) == encoded(binding), 'cross_source_run_response')
    config = GenerationConfig(**GENERATION, disable_compile=True).to_dict()
    check(encoded(response['effective_generation']) == encoded(config), 'effective_generation_changed')
    expected_runtime = {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'device': 'cpu', 'dtype': 'torch.float32',
                        'attention': 'eager', 'threads': 1, 'interop_threads': 1, 'deterministic': True,
                        'evaluation': True, 'model_class': 'LlamaForCausalLM', 'seed': 1729,
                        'model_defaults': False, 'compile': False, 'quantization': 'none'}
    check(encoded(response['runtime']) == encoded(expected_runtime), 'effective_runtime_changed')
    fields(ready, 'record_type binding input_ids effective_generation runtime', 'ready_fields')
    check(ready['record_type'] == 'q2_native_model_ready_v0' and encoded(ready['binding']) == encoded(binding)
          and ready['input_ids'] == ids and encoded(ready['effective_generation']) == encoded(config)
          and encoded(ready['runtime']) == encoded(expected_runtime), 'model_ready_mismatch')
    fields(observation, 'sandbox generation_start_ns response_received_ns generation_deadline_ns '
                        'watchdog_armed watchdog_unit worker_exit_code', 'occurrence_observation_fields')
    verify_sandbox_observation(observation['sandbox'], 'worker')
    prefix = observation['sandbox']['unit'].removesuffix('-worker.service')
    check(installer_observation['unit'] == prefix + '-installer.service'
          and installcheck_observation['unit'] == prefix + '-installcheck.service'
          and observation['watchdog_unit'] == prefix + '-watchdog.timer', 'cross_invocation_sandbox_record')
    start = observation['generation_start_ns']; end = observation['response_received_ns']
    check(type(start) is int and type(end) is int and 0 < start <= end
          and observation['generation_deadline_ns'] == start + 15_000_000_000
          and end <= observation['generation_deadline_ns'], 'external_generation_deadline')
    check(observation['watchdog_armed'] is True and
          re.fullmatch(r'pulse-q2-[a-f0-9]{24}-watchdog\.timer', observation['watchdog_unit'])
          and type(observation['worker_exit_code']) is int and observation['worker_exit_code'] == 0,
          'watchdog_or_terminal_failure')
    return {'record_type': 'q2_native_diagnostic_check_v0', 'prelaunch_sha256': sha(prelaunch_raw),
            'response_sha256': sha(response_raw), 'ready_sha256': sha(ready_raw),
            'original_decoding_verified': True, 'single_unscored_diagnostic_verified': True,
            'native_runtime_qualified': True, 'qualification_scope': 'one_unscored_diagnostic',
            'authority_effect': 'none', 'production_gate_eligible': False, 'scored_call_count': 0,
            'trust_boundary': 'reviewed_collector_pinned_dependencies_and_GitHub_host',
            'malicious_platform_resistance': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='phase', required=True)
    inputs = sub.add_parser('verify-inputs')
    inputs.add_argument('--archive', type=Path, required=True)
    inputs.add_argument('--staging', type=Path, required=True)
    inputs.add_argument('--source-root', type=Path, required=True)
    inputs.add_argument('--repo-root', type=Path, required=True)
    inputs.add_argument('--expected-source-sha', required=True)
    inputs.add_argument('--output', type=Path, required=True)
    install = sub.add_parser('verify-installation')
    install.add_argument('--venv', type=Path, required=True)
    install.add_argument('--bundle', type=Path, required=True)
    install.add_argument('--bootstrap-inventory', type=Path, required=True)
    install.add_argument('--pip-report', type=Path, required=True)
    install.add_argument('--output', type=Path, required=True)
    diagnostic = sub.add_parser('verify-diagnostic')
    for flag in ('source-root', 'bundle', 'venv', 'prelaunch', 'installation', 'response', 'ready', 'observation', 'bootstrap-inventory', 'pip-report',
                 'installer-observation', 'installcheck-observation', 'output'):
        diagnostic.add_argument('--' + flag, type=Path, required=True)
    diagnostic.add_argument('--expected-prelaunch-sha256', required=True)
    diagnostic.add_argument('--expected-response-sha256', required=True)
    diagnostic.add_argument('--expected-source-sha', required=True)
    diagnostic.add_argument('--expected-run-id', required=True)
    diagnostic.add_argument('--expected-source-inventory-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        if args.phase == 'verify-inputs':
            rows = check_sources(args.source_root, args.repo_root, args.expected_source_sha)
            prep, originals, _ = adopted_inputs(args.source_root)
            bundle = unpack_verified_archive(args.archive, args.staging, prep, originals)
            check_prepared_bytes(bundle, args.source_root, args.repo_root)
            result = {'record_type': 'q2_native_input_check_v0', 'archive_sha256': ARCHIVE_SHA,
                      'preparation_source_commit': ORIGINAL_SOURCE, 'preparation_run_id': ORIGINAL_RUN,
                      'consumer_source_commit': args.expected_source_sha, 'source_files': rows,
                      'authority_effect': 'none', 'production_gate_eligible': False}
        elif args.phase == 'verify-installation':
            native_target()
            result = verify_installation(args.venv, args.bundle, args.bootstrap_inventory, args.pip_report)
        else:
            pre = read(args.prelaunch); response = read(args.response)
            check(sha(pre) == args.expected_prelaunch_sha256 and sha(response) == args.expected_response_sha256,
                  'external_record_expectation_mismatch')
            result = verify_diagnostic(args.source_root, args.bundle, args.venv, pre,
                read(args.installation), response, read(args.ready), parse(read(args.observation)),
                args.bootstrap_inventory, args.pip_report, parse(read(args.installer_observation)),
                parse(read(args.installcheck_observation)), args.expected_source_sha, args.expected_run_id,
                args.expected_source_inventory_sha256)
        put(args.output, encoded(result))
        print('Q2 qualification check completed; no release authority')
        return 0
    except (QualificationCheckError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError,
            zipfile.BadZipFile, ImportError) as exc:
        # Only our own stable error codes, never an arbitrary exception message,
        # path, environment, generated text or downloaded content. This line is
        # retained in the phase log even when no successful output is produced.
        code = 'invalid_or_unavailable_evidence'
        if type(exc) is QualificationCheckError and len(exc.args) == 1:
            candidate = exc.args[0]
            if type(candidate) is str and re.fullmatch('[a-z][a-z0-9_]{0,95}', candidate):
                code = candidate
        print('Q2 qualification check rejected: ' + code, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
