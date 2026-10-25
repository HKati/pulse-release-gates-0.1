#!/usr/bin/env python3
"""Independent Q3 input/install/token/carrier checks. Never run a model.

Installed-byte and mount checks derive from the reviewed Q2 independent checker;
no Q2 module, generation worker, supervisor or metric producer is imported.
"""
from __future__ import annotations
import argparse
import base64
import configparser
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import urllib.parse
import zipfile
_spec=importlib.util.spec_from_file_location('q3_capture_contract',Path(__file__).with_name('q3_native_capture_contract_v0.py'))
C=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(C)
check=C.require
sha=C.digest
encoded=C.encode
parse=C.strict_json
def fields(obj,names,code='FIELDS'):
    return C.fields(obj,set(names.split()) if type(names) is str else names,code)
def relative(name):
    # Wheel payload paths may contain '+' and other ordinary filename characters.
    # Keep traversal/absolute/control-character rejection without narrowing the
    # original fixed wheel representation to repository-source filename syntax.
    check(type(name) is str and 0 < len(name) <= 4096, 'relative_path_type')
    p=PurePosixPath(name)
    check(not p.is_absolute() and p.as_posix()==name and '\\' not in name
          and ':' not in name and not any(ord(c)<32 or ord(c)==127 for c in name)
          and all(x not in ('', '.', '..') for x in name.split('/')), 'unsafe_relative_path')
    return name
def read(path, maximum=512 * 1024 * 1024):
    return C.safe_read(path, maximum)
RECORD_DIR='PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/'
MODEL_MAP='PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json'
LOCK='PULSE_safe_pack_v0/requirements-q2-reference-v0.lock'

def put(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
    C.write_new(path,raw,0o644)
ARCHIVE_SHA = 'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9'


ARCHIVE_SIZE = 508460811


RECORDS = {
    'preparation.json': '832b3626e846c96e5d65052ea54c966aabf0ed5f3976ecc5d3b4a3ced006ef4f',
    'q2-runtime-preparation-check.json': '8676b29834f376b44f08f96b19d60d1ab79a9f565167aabd25513cf8694037e3',
    'q2_reference_model_files_v0.json': 'b91289806a62957e2613f21afa950d4bf48b917074fde16d3e94681764d74078',
    'requirements-q2-reference-v0.lock': '60cec54ed62df95b299cdeaf386afc7ed0b72f4fb7ec466cf82905bb40168d0f',
}


MAX_JSON = 16 * 1024 * 1024


MAX_FILE = 512 * 1024 * 1024


MAX_TOTAL = 1536 * 1024 * 1024


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
    return {'record_type': 'q3_native_installation_check_v0', 'distributions': distributions,
            'wheel_payload_file_count': len(wheel_owned),
            'generated_non_worker_launchers': sorted(launchers & set(actual)),
            'bootstrap_inventory_sha256': sha(bootstrap_raw),
            'pip_report_sha256': sha(read(pip_report)), 'inventory': actual_rows,
            'authority_effect': 'none', 'production_gate_eligible': False}


def verify_run_mount(value, unit):
    """Recheck retained kernel mount records without importing the supervisor.

    These are observations from the trusted external collector, not a child's
    declaration and not a proof against a malicious host. Missing old-format
    /run evidence is rejected, never silently grandfathered as qualified.
    """
    check(type(unit) is str and re.fullmatch(r'pulse-q3-[a-f0-9]{24}-[a-z]+\.service', unit), 'sandbox_unit')
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



def verify_archive(archive, destination, source):
    p=C.load_profile(source);C.verify_fixed_inputs(source,p)
    original={name:read(source/RECORD_DIR/name) for name in RECORDS}
    for name,b in original.items():check(sha(b)==RECORDS[name],'original_metadata')
    prep=parse(original['preparation.json'])
    check(len(prep['files'])==76 and len(prep['wheels'])==30,'original_extent')
    raw=read(archive,ARCHIVE_SIZE)
    check(len(raw)==ARCHIVE_SIZE and sha(raw)==ARCHIVE_SHA,'runtime_archive_digest')
    check(not destination.exists() and not destination.is_symlink(),'runtime_destination_exists')
    expected={'q2-runtime-preparation/'+r['path']:r for r in prep['files']}
    expected['q2-runtime-preparation/preparation.json']={'path':'preparation.json','size':len(original['preparation.json']),'sha256':RECORDS['preparation.json']}
    expected['q2-runtime-preparation-check.json']={'path':'q2-runtime-preparation-check.json','size':len(original['q2-runtime-preparation-check.json']),'sha256':RECORDS['q2-runtime-preparation-check.json']}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist()
        check(len(infos)==78 and len({i.filename for i in infos})==78
              and set(i.filename for i in infos)==set(expected),'runtime_archive_scope')
        total=0
        for i in infos:
            relative(i.filename);r=expected[i.filename]
            check(not i.is_dir() and not i.flag_bits&1 and stat.S_IFMT(i.external_attr>>16) in (0,stat.S_IFREG),'runtime_archive_type')
            C.integer(r['size'],0,MAX_FILE,'runtime_member_size')
            check(i.file_size==r['size'],'runtime_member_size');total+=i.file_size
            check(total<=MAX_TOTAL,'runtime_archive_total')
        destination.mkdir(mode=0o700);os.chmod(destination,0o700)
        for i in infos:
            r=expected[i.filename];b=z.read(i)
            check(len(b)==r['size'] and sha(b)==r['sha256'],'runtime_member_digest')
            path=(destination/'bundle'/r['path'] if i.filename.startswith('q2-runtime-preparation/') else destination/r['path'])
            put(path,b)
    modelmap=parse(read(source/MODEL_MAP))
    for row in modelmap['files']:
        b=read(destination/'bundle'/row['path'],MAX_FILE)
        check(len(b)==row['size'] and sha(b)==row['sha256'],'model_bytes')
    check(read(source/LOCK).splitlines()[1:]==original['requirements-q2-reference-v0.lock'].splitlines()[1:],'lock_identity')
    return {'record_type':'q3_runtime_input_check_v0','archive_sha256':ARCHIVE_SHA,
            'archive_size':ARCHIVE_SIZE,'member_count':78,'wheel_count':30,'claims':dict(C.CLAIMS)}


def validate_token_map(value,frame,p):
    fields(value,{'record_type','profile_sha256','model_revision','task_file_sha256','rows'})
    check(value['record_type']=='q3_token_map_v0' and value['profile_sha256']==C.PROFILE_SHA256
          and value['model_revision']==p['model_revision']
          and value['task_file_sha256']==p['fixed_inputs'][C.FRAME+'TASKS_DRAFT.jsonl'],'token_map_identity')
    check(type(value['rows']) is list and len(value['rows'])==len(frame)==204,'token_map_extent')
    for task,row in zip(frame,value['rows']):
        fields(row,{'task_id','ordinal','input_ids','messages_sha256','logical_request_sha256'})
        check(row['task_id']==task['task_id'] and type(row['ordinal']) is int
              and row['ordinal']==task['ordinal'],'token_map_order')
        ids=row['input_ids']
        check(type(ids) is list and 1<=len(ids)<=p['limits']['max_prompt_tokens']
              and all(type(i) is int and 0<=i<49152 for i in ids),'token_id_bound')
        check(row['messages_sha256']==sha(encoded(task['messages']))
              and row['logical_request_sha256']==sha(task['logical_request_text'].encode()),'token_map_input')
    return value


def expected_runtime(p):
    return {'torch':'2.8.0+cpu','transformers':'4.57.6','device':'cpu','dtype':'float32',
            'attention':'eager','threads':1,'interop_threads':1,'deterministic':True,
            'model_class':'LlamaForCausalLM','evaluation':True,'seed':p['seed'],
            'compile':False,'quantization':'none'}


def validate_generation(value,p):
    check(type(value) is dict,'generation_shape')
    for k,v in p['generation'].items():check(encoded(value.get(k))==encoded(v),'generation_setting')
    check(value.get('disable_compile') is True,'generation_compile')


def check_response(response,ready,task,row,binding,effective,runtime,p):
    slot={'task_id':task['task_id'],'ordinal':task['ordinal'],'attempt':1}
    fields(ready,{'record_type','binding','slot','input_ids','effective_generation','runtime'})
    check(ready['record_type']=='q3_slot_ready_v0' and encoded(ready['binding'])==encoded(binding)
          and encoded(ready['slot'])==encoded(slot) and encoded(ready['input_ids'])==encoded(row['input_ids'])
          and encoded(ready['effective_generation'])==encoded(effective)
          and encoded(ready['runtime'])==encoded(runtime),'slot_ready')
    fields(response,{'record_type','binding','slot','input_ids','new_token_ids','text','text_utf8_base64',
                     'stop_reason','effective_generation','runtime'})
    check(response['record_type']=='q3_response_v0' and encoded(response['binding'])==encoded(binding)
          and encoded(response['slot'])==encoded(slot) and encoded(response['input_ids'])==encoded(row['input_ids'])
          and encoded(response['effective_generation'])==encoded(effective)
          and encoded(response['runtime'])==encoded(runtime),'response_identity')
    ids=response['new_token_ids']
    check(type(ids) is list and 1<=len(ids)<=p['generation']['max_new_tokens']
          and all(type(i) is int and 0<=i<49152 for i in ids),'response_token_bound')
    if ids[-1]==2:
        check(2 not in ids[:-1] and response['stop_reason']=='eos','response_eos')
    else:
        check(2 not in ids and len(ids)==p['generation']['max_new_tokens']
              and response['stop_reason']=='token_limit','response_termination')
    check(type(response['text']) is str and len(response['text'].encode())<=p['limits']['max_response_utf8_bytes'],'response_text_bound')
    check(response['text_utf8_base64']==base64.b64encode(response['text'].encode()).decode(),'response_text_bytes')
    return response['stop_reason']=='eos'


def validate_protocol(source,data,require_complete=True):
    """Reconstruct source/task/binding/order/count/terminal evidence, not its verdict."""
    p=C.load_profile(source);frame=C.task_frame(source,p)
    def get(name):
        check(name in data,'evidence_member_missing');return parse(data[name])
    request=C.validate_request(data['request.json'],p)
    pre=get('prelaunch.json');platform=get('platform.json');control=get('control-plane.json')
    fields(pre,set('record_type request source_commit run_id run_attempt source_files platform_sha256 control_plane_sha256 installation_sha256 started_at clock_relation'.split()))
    fields(platform,set('os architecture python runner_image kernel libc bootstrap_python_sha256 contract historical_platform_equivalence'.split()))
    fields(control,set('run_id run_attempt source_commit repository repository_private event workflow head_branch actor triggering_actor clock_relation'.split()))
    check(pre['clock_relation']==control['clock_relation']=='not_verified','clock_claim')
    check(C.sha256_string(platform['bootstrap_python_sha256']) and all(type(platform[k]) is str and 0<len(platform[k])<=256 for k in ['runner_image','kernel'])
          and type(platform['libc']) is list and len(platform['libc'])==2 and all(type(x) is str for x in platform['libc']),'platform_fields')
    import datetime
    stamp=pre['started_at']
    check(type(stamp) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{6})?\+00:00',stamp),'start_time')
    datetime.datetime.fromisoformat(stamp)
    check(pre['record_type']=='q3_native_prelaunch_v0' and pre['request']==request
          and pre['source_commit']==request['source_commit'] and pre['run_attempt']==1,'prelaunch_binding')
    C.integer(pre['run_attempt'],1,1)
    check(type(pre['run_id']) is str and re.fullmatch(r'[1-9][0-9]{0,19}',pre['run_id']),'run_id')
    check(control['run_id']==pre['run_id'] and control['source_commit']==pre['source_commit']
          and type(control['run_attempt']) is int and control['run_attempt']==1 and control['actor']=='HKati'
          and control['triggering_actor']=='HKati' and control['repository']==C.REPOSITORY
          and control['event']=='workflow_dispatch' and control['workflow']==C.WORKFLOW
          and control['head_branch']=='main' and control['repository_private'] is False,'control_plane')
    check(platform['contract']=='q3_observed_ubuntu24_cpu_runtime_v0'
          and platform['os']=='ubuntu-24.04' and platform['architecture']=='x86_64'
          and platform['python']=='3.11.16' and platform['historical_platform_equivalence'] is False,'platform_contract')
    check(pre['platform_sha256']==sha(data['platform.json'])
          and pre['control_plane_sha256']==sha(data['control-plane.json'])
          and pre['installation_sha256']==sha(data['installation.json']),'prelaunch_records')
    check(set(pre['source_files'])==set(p['source_files']),'source_scope')
    for path,digest in pre['source_files'].items():
        check('source/'+path in data and sha(data['source/'+path])==digest
              and data['source/'+path]==C.source_read(source,path),'source_byte_binding')
    binding={'prelaunch_sha256':sha(data['prelaunch.json']),'source_commit':pre['source_commit'],
             'run_id':pre['run_id'],'run_attempt':1}
    ready=get('worker-ready.json')
    check(encoded(ready)==encoded({'record_type':'q3_worker_ready_v0','binding':binding,'mode':request['mode']}),'worker_ready')
    token_map=validate_token_map(get('token-map.json'),frame,p);map_sha=sha(data['token-map.json'])
    check(data['token-map.json']==encoded(token_map),'token_map_encoding')
    for row in token_map['rows']:
        check(encoded(get('tokens/'+row['task_id']+'.json'))==encoded({'record_type':'q3_token_row_v0','binding':binding,'row':row}),'original_token_record')
    check(encoded(get('token-map-end.json'))==encoded({'record_type':'q3_token_map_end_v0','binding':binding,
          'token_map_sha256':map_sha,'task_count':204}),'token_end')
    terminal=get('terminal.json')
    fields(terminal,set('record_type mode binding complete error_code attempted_calls occurrences worker_exit_code stdout_eof worker_deadline_ns worker_exit_observed_ns ended_at'.split()))
    check(terminal['record_type']=='q3_capture_terminal_v0','terminal_type')
    check(terminal['mode']==request['mode'] and encoded(terminal['binding'])==encoded(binding),'terminal_binding')
    C.integer(terminal['worker_deadline_ns'],1,2**63-1)
    C.integer(terminal['attempted_calls'],0,204)
    check(type(terminal['occurrences']) is list and len(terminal['occurrences'])==204,'terminal_extent')
    if require_complete:
        check(terminal['complete'] is True and terminal['error_code'] is None
              and type(terminal['worker_exit_code']) is int and terminal['worker_exit_code']==0
              and terminal['stdout_eof'] is True,'terminal_incomplete')
        C.integer(terminal['worker_exit_observed_ns'],1,terminal['worker_deadline_ns'])
        end=terminal['ended_at']
        check(type(end) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{6})?\+00:00',end),'end_time')
        check(datetime.datetime.fromisoformat(end)>=datetime.datetime.fromisoformat(stamp),'wall_clock_backwards')
    result_binding=binding
    if request['mode']=='capture':
        check(request['approved_token_map_sha256']==map_sha,'approved_token_map')
        mr=get('model-ready.json');fields(mr,{'record_type','binding','token_map_sha256','effective_generation','runtime'})
        validate_generation(mr['effective_generation'],p)
        check(encoded(mr['runtime'])==encoded(expected_runtime(p))
              and mr['record_type']=='q3_model_ready_v0' and mr['binding']==binding
              and mr['token_map_sha256']==map_sha,'model_ready')
        subject={'record_type':'q3_capture_subject_v0','binding':binding,
                 'model_ready_sha256':sha(data['model-ready.json']),'token_map_sha256':map_sha}
        check(data['subject.json']==encoded(subject),'subject_record')
        result_binding={**binding,'subject_sha256':sha(data['subject.json'])}
        check(encoded(get('bound.json'))==encoded({'record_type':'q3_bound_v0','binding':result_binding}),'bound_record')
        examples=[]
        previous_received=0
        for task,row,occ in zip(frame,token_map['rows'],terminal['occurrences']):
            check(occ['task_id']==task['task_id'] and type(occ['ordinal']) is int and occ['ordinal']==task['ordinal']
                  and type(occ['attempt']) is int and occ['attempt']==1,'occurrence_order')
            if require_complete:check(occ['status']=='completed','occurrence_incomplete')
            fields(occ,set('task_id ordinal attempt status intent_saved_ns watchdog_arm_begin_ns generation_start_ns generation_deadline_ns response_received_ns watchdog_closed_ns'.split()))
            stem='calls/'+task['task_id']
            response=get(stem+'.response.json');slot_ready=get(stem+'.ready.json')
            eos=check_response(response,slot_ready,task,row,result_binding,mr['effective_generation'],mr['runtime'],p)
            if require_complete:check(eos,'length_termination_not_complete')
            intent=get(stem+'.intent.json')
            check(intent=={'task_id':task['task_id'],'ordinal':task['ordinal'],'binding':result_binding,
                           'intent':'before_GO','attempt':1},'call_intent')
            for key in ['intent_saved_ns','watchdog_arm_begin_ns','generation_start_ns','generation_deadline_ns','response_received_ns','watchdog_closed_ns']:
                C.integer(occ[key],1,2**63-1)
            check(previous_received<=occ['intent_saved_ns']<=occ['watchdog_arm_begin_ns']<=occ['generation_start_ns']
                  <=occ['response_received_ns']<=occ['generation_deadline_ns']<=terminal['worker_deadline_ns']
                  and occ['generation_deadline_ns']-occ['generation_start_ns']==60*1000000000
                  and occ['response_received_ns']<=occ['watchdog_closed_ns']<=terminal['worker_exit_observed_ns'],'call_order_or_deadline')
            previous_received=occ['watchdog_closed_ns']
            check(data[stem+'.utf8']==response['text'].encode(),'original_text')
            examples.append({'example_id':task['task_id'],'prompt':task['prompt'],'response':response['text'],
                             'context':task['context'],'metadata':{'task_form':task['task_form']}})
        check(terminal['attempted_calls']==204,'attempt_total')
        expected_examples=b''.join(encoded(e) for e in examples)
        if 'examples.jsonl' in data:check(data['examples.jsonl']==expected_examples,'examples_projection')
    else:
        for occ in terminal['occurrences']:fields(occ,{'task_id','ordinal','attempt','status'})
        check(terminal['attempted_calls']==0 and all(o['status']=='not_requested'
              and o['task_id']==t['task_id'] and type(o['ordinal']) is int and o['ordinal']==t['ordinal']
              and type(o['attempt']) is int and o['attempt']==1 for o,t in zip(terminal['occurrences'],frame)),'preflight_generation')
        expected_examples=None
    if require_complete:
        check(encoded(get('session-end.json'))==encoded({'record_type':'q3_session_end_v0','binding':result_binding,
              'completed_calls':204 if request['mode']=='capture' else 0}),'session_end')
    return request,token_map,expected_examples


def verify_live_tokens(source,bundle,evidence):
    """Independent native tokenizer execution; no model class or generate call."""
    data=read_evidence(evidence)
    request,token_map,examples=validate_protocol(source,data)
    p=C.load_profile(source);frame=C.task_frame(source,p)
    # Independently bind the tokenizer inputs, not just its self-reported name.
    model_map=parse(read(source/MODEL_MAP))
    check({x.name for x in (bundle/'model').iterdir()}=={Path(x['path']).name for x in model_map['files']},'tokenizer_file_scope')
    for row in model_map['files']:
        raw=read(bundle/relative(row['path']))
        check(len(raw)==row['size'] and sha(raw)==row['sha256'],'tokenizer_file_binding')
    import transformers
    from transformers import AutoTokenizer, GenerationConfig
    check(transformers.__version__=='4.57.6' and Path(transformers.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()),'token_check_runtime')
    tokenizer=AutoTokenizer.from_pretrained(str(bundle/'model'),local_files_only=True,trust_remote_code=False,use_fast=True)
    check(tokenizer.is_fast and (tokenizer.bos_token_id,tokenizer.eos_token_id,tokenizer.pad_token_id)==(1,2,2),'token_check_configuration')
    if request['mode']=='capture':
        expected=GenerationConfig(**p['generation'],disable_compile=True).to_dict()
        check(encoded(parse(data['model-ready.json'])['effective_generation'])==encoded(expected),'resolved_generation')
    for task,row in zip(frame,token_map['rows']):
        ids=tokenizer.apply_chat_template(task['messages'],tokenize=True,add_generation_prompt=True,truncation=False)
        check(encoded(ids)==encoded(row['input_ids']),'native_prompt_token_mismatch')
        if request['mode']=='capture':
            response=parse(data['calls/'+task['task_id']+'.response.json'])
            text=tokenizer.decode(response['new_token_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
            check(type(text) is str and text==response['text'],'native_decode_mismatch')
    return {'record_type':'q3_native_token_check_v0','request_sha256':sha(data['request.json']),
            'prelaunch_sha256':sha(data['prelaunch.json']),'token_map_sha256':sha(data['token-map.json']),
            'checked_tasks':204,'checked_responses':204 if request['mode']=='capture' else 0,
            'tokenization_reperformed':True,'generation_executed':False,
            'examples_sha256':sha(examples) if examples is not None else None,'claims':dict(C.CLAIMS)},examples


def read_evidence(root):
    out={};total=0
    for path in sorted(root.rglob('*')):
        check(not path.is_symlink(),'evidence_symlink')
        if path.is_dir():continue
        name=relative(path.relative_to(root).as_posix())
        b=read(path,16*1024*1024);total+=len(b)
        check(total<=256*1024*1024 and len(out)<2000,'evidence_bound');out[name]=b
    return out


def duration(value):
    check(type(value) is str and bool(value),'duration_shape')
    scales={'h':3600000000,'min':60000000,'s':1000000,'ms':1000,'us':1};out=0
    for token in value.split():
        m=re.fullmatch(r'([0-9]+)(h|min|s|ms|us)',token)
        check(m is not None,'duration_shape');out+=int(m[1])*scales[m[2]]
    return out


def verify_sandbox(value,stage):
    names=set('stage unit pid host_netns child_netns uid no_new_privs capabilities ipv4_blocked ipv6_blocked memory_max memory_swap_max pids_max cpu_max properties run_mount'.split())
    if stage=='captureworker':names.add('capture_runtime_seconds')
    fields(value,names,'sandbox_fields')
    check(value['stage']==stage and type(value['pid']) is int and value['pid']>1,'sandbox_stage')
    check(type(value['unit']) is str and re.fullmatch(r'pulse-q3-[a-f0-9]{24}-'+stage+r'\.service',value['unit']),'sandbox_unit')
    check(all(type(value[k]) is str and re.fullmatch(r'net:\[[0-9]+\]',value[k]) for k in ['host_netns','child_netns'])
          and value['host_netns']!=value['child_netns'],'sandbox_network_namespace')
    check(type(value['uid']) is int and value['uid']==65534 and value['no_new_privs'] is True
          and value['capabilities']=='0000000000000000' and value['ipv4_blocked'] is True
          and value['ipv6_blocked'] is True,'sandbox_privilege_or_network')
    check({k:value[k] for k in ['memory_max','memory_swap_max','pids_max','cpu_max']}==
          {'memory_max':'4294967296','memory_swap_max':'0','pids_max':'64','cpu_max':'100000 100000'},'sandbox_limits')
    props=value['properties']
    fields(props,set('PrivateNetwork NoNewPrivileges ProtectSystem ProtectHome KillMode SendSIGKILL User Group CapabilityBoundingSet RestrictAddressFamilies RuntimeMaxUSec'.split()))
    for key,v in {'PrivateNetwork':'yes','NoNewPrivileges':'yes','ProtectSystem':'strict','ProtectHome':'yes',
                  'KillMode':'control-group','SendSIGKILL':'yes','User':'65534','Group':'65534',
                  'CapabilityBoundingSet':'','RestrictAddressFamilies':'AF_UNIX'}.items():
        check(props[key]==v,'sandbox_properties')
    seconds={'installer':480,'installcheck':300,'preflight':300,'decodecheck':300}.get(stage)
    if stage=='captureworker':seconds=C.integer(value['capture_runtime_seconds'],1,14400)
    check(seconds is not None and duration(props['RuntimeMaxUSec'])==seconds*1000000,'sandbox_runtime_limit')
    verify_run_mount(value['run_mount'],value['unit'])


def verify_lifecycle(data,mode):
    life=parse(data['lifecycle.json'])
    fields(life,{'cleanup_complete','errors','services','timers','private_tree_removed'})
    check(life['cleanup_complete'] is True and life['private_tree_removed'] is True and life['errors']==[],'cleanup_incomplete')
    stages=['installer','installcheck','captureworker' if mode=='capture' else 'preflight','decodecheck']
    check(type(life['services']) is list and len(life['services'])==4,'service_extent')
    units=[]
    for stage,closed in zip(stages,life['services']):
        check(type(closed) is dict,'service_closure')
        fields(closed,{'unit','launch_attempted','properties','cgroup_empty_or_removed','client_reaped'})
        sbname=('worker' if stage in ('preflight','captureworker') else stage)+'-sandbox.json'
        sb=parse(data[sbname]);verify_sandbox(sb,stage)
        check(closed['unit']==sb['unit'] and closed['launch_attempted'] is True
              and closed['cgroup_empty_or_removed'] is True and closed['client_reaped'] is True,'service_cleanup')
        prop=closed['properties'];fields(prop,{'LoadState','ActiveState','ControlGroup'})
        check(prop['LoadState'] in ('loaded','not-found') and prop['ActiveState']=='inactive'
              and prop['ControlGroup'] in ('','/system.slice/'+closed['unit']),'service_active')
        cname=('worker' if stage in ('preflight','captureworker') else stage)+'-cleanup.json'
        check(encoded(parse(data[cname]))==encoded(closed),'closure_binding')
        units.append(closed['unit'])
    check(len(set(units))==4 and len({u.split('-')[2] for u in units})==1,'service_prefix')
    expected=204 if mode=='capture' else 0
    check(type(life['timers']) is list and len(life['timers'])==expected,'timer_extent')
    prefix=units[0].rsplit('-',1)[0]
    terminal=parse(data['terminal.json'])
    for idx,item in enumerate(life['timers'],1):
        fields(item,{'prefix','closure'});name=prefix+f'-call-{idx:03d}'
        check(item['prefix']==name,'timer_order')
        close=item['closure'];fields(close,{'units','closed_ns'})
        check(type(close['units']) is list and len(close['units'])==2,'timer_units')
        for u,suffix in zip(close['units'],['.timer','.service']):
            fields(u,{'unit','LoadState','ActiveState'})
            check(u['unit']==name+'-watchdog'+suffix and u['LoadState'] in ('loaded','not-found')
                  and u['ActiveState']=='inactive','timer_not_inactive')
        check(type(close['closed_ns']) is int and close['closed_ns']==terminal['occurrences'][idx-1]['watchdog_closed_ns'],'timer_time_binding')
    return life


def expected_members(p,frame,mode):
    common={'request.json','prelaunch.json','platform.json','control-plane.json','input-check.json',
            'bootstrap.json','pip-report.json','installation.json','worker-ready.json','token-map.json',
            'token-map-end.json','session-end.json','terminal.json','token-check.json','lifecycle.json',
            'installer-sandbox.json','installer-cleanup.json','installcheck-sandbox.json','installcheck-cleanup.json',
            'worker-sandbox.json','worker-cleanup.json','decodecheck-sandbox.json','decodecheck-cleanup.json'}
    common|={'source/'+n for n in p['source_files']}
    common|={'tokens/'+t['task_id']+'.json' for t in frame}
    if mode=='capture':
        common|={'model-ready.json','subject.json','bound.json','examples.jsonl'}
        common|={'calls/'+t['task_id']+suffix for t in frame for suffix in ['.ready.json','.intent.json','.response.json','.utf8']}
    return common


def validate_installation_record(data):
    """Verify retained installation evidence. Does not re-read absent wheel payloads."""
    installed=parse(data['installation.json'])
    fields(installed,{'record_type','distributions','wheel_payload_file_count','generated_non_worker_launchers',
                     'bootstrap_inventory_sha256','pip_report_sha256','inventory','authority_effect','production_gate_eligible'})
    check(installed['record_type']=='q3_native_installation_check_v0'
          and installed['bootstrap_inventory_sha256']==sha(data['bootstrap.json'])
          and installed['pip_report_sha256']==sha(data['pip-report.json'])
          and installed['authority_effect']=='none' and installed['production_gate_eligible'] is False,'installation_binding')
    prep=parse(data['source/'+RECORD_DIR+'preparation.json'])
    wheels={row['name']:row for row in prep['wheels']}
    check(type(installed['distributions']) is dict and set(installed['distributions'])==set(wheels),'installed_package_closure')
    inventory=installed['inventory'];check(type(inventory) is list and 0<len(inventory)<=100000,'installed_inventory')
    rows={}
    for row in inventory:
        check(type(row) is dict and type(row.get('path')) is str,'installed_inventory_row')
        name=relative(row['path']);check(name not in rows,'installed_inventory_duplicate')
        if 'symlink' in row:
            fields(row,{'path','symlink'});check(name=='lib64' and row['symlink']=='lib','installed_inventory_link')
        else:
            fields(row,{'path','size','sha256','mode'})
            C.integer(row['size'],0,MAX_FILE);C.integer(row['mode'],0,0o7777)
            check(C.sha256_string(row['sha256']) and row['mode']&0o022==0,'installed_inventory_identity')
        rows[name]=row
    C.integer(installed['wheel_payload_file_count'],1,len(rows),'wheel_payload_count')
    check(type(installed['generated_non_worker_launchers']) is list
          and len(installed['generated_non_worker_launchers'])==len(set(installed['generated_non_worker_launchers'])),'launcher_scope')
    for name in installed['generated_non_worker_launchers']:
        check(type(name) is str and name.startswith('bin/') and name in rows,'launcher_path')
    before=frozen_bootstrap_inventory(data['bootstrap.json'])
    check('bin/python' in before and 'pyvenv.cfg' in before and set(before)<=set(rows),'bootstrap_required')
    for name in ['bin/python','pyvenv.cfg']:
        check(before[name]==rows[name],'bootstrap_record_drift')
    report=parse(data['pip-report.json'])
    check(report.get('version')=='1' and type(report.get('install')) is list
          and len(report['install'])==len(wheels),'retained_pip_closure')
    seen=set()
    for item in report['install']:
        name=normalized(item['metadata']['name']);check(name in wheels and name not in seen,'retained_pip_package');seen.add(name)
        wheel=wheels[name];check(item['metadata']['version']==wheel['version'],'retained_pip_version')
        url=urllib.parse.urlsplit(item['download_info']['url'])
        check(url.scheme=='file' and not url.netloc and not url.query and not url.fragment
              and urllib.parse.unquote(url.path).endswith('/bundle/'+wheel['path']),'retained_pip_origin')
        check(item['download_info']['archive_info']['hashes'].get('sha256')==wheel['sha256'],'retained_pip_digest')
        entry=installed['distributions'][name];fields(entry,{'version','metadata'})
        check(entry['version']==wheel['version'] and type(entry['metadata']) is str
              and entry['metadata'].startswith('lib/python3.11/site-packages/')
              and entry['metadata'].endswith('.dist-info/METADATA') and entry['metadata'] in rows,'retained_distribution_metadata')
    return installed


def validate_complete(source,data):
    request,token_map,examples=validate_protocol(source,data)
    p=C.load_profile(source);frame=C.task_frame(source,p)
    check(set(data)==expected_members(p,frame,request['mode']),'complete_evidence_scope')
    verify_lifecycle(data,request['mode'])
    live=parse(data['token-check.json'])
    expected={'record_type':'q3_native_token_check_v0','request_sha256':sha(data['request.json']),
              'prelaunch_sha256':sha(data['prelaunch.json']),'token_map_sha256':sha(data['token-map.json']),
              'checked_tasks':204,'checked_responses':204 if request['mode']=='capture' else 0,
              'tokenization_reperformed':True,'generation_executed':False,
              'examples_sha256':sha(examples) if examples is not None else None,'claims':dict(C.CLAIMS)}
    check(encoded(live)==encoded(expected),'recorded_token_check')
    inp=parse(data['input-check.json'])
    check(inp=={'record_type':'q3_runtime_input_check_v0','archive_sha256':ARCHIVE_SHA,'archive_size':ARCHIVE_SIZE,
                'member_count':78,'wheel_count':30,'claims':dict(C.CLAIMS)},'recorded_input_check')
    validate_installation_record(data)
    return {'record_type':'q3_carrier_reconstruction_v0','complete':True,'mode':request['mode'],
            'request_sha256':sha(data['request.json']),'token_map_sha256':sha(data['token-map.json']),
            'native_origin_reacquired':False,'tokenization_reperformed':False,
            'metric_recomputed':False,'claims':dict(C.CLAIMS)}


def check_carrier(archive,source,expected_archive_sha256,expected_request_sha256,expected_source_commit):
    check(C.sha256_string(expected_archive_sha256) and C.sha256_string(expected_request_sha256),'external_anchor_required')
    raw=read(archive,256*1024*1024)
    check(sha(raw)==expected_archive_sha256,'carrier_external_digest')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist();check(0<len(infos)<=2000 and len({i.filename for i in infos})==len(infos),'carrier_count')
        data={};total=0
        for i in infos:
            relative(i.filename)
            check(not i.is_dir() and not i.flag_bits&1 and stat.S_IFMT(i.external_attr>>16) in (0,stat.S_IFREG)
                  and i.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'carrier_member_type')
            C.integer(i.file_size,0,16*1024*1024);total+=i.file_size;check(total<=256*1024*1024,'carrier_size')
            data[i.filename]=z.read(i)
    check('result.json' in data and 'request.json' in data,'carrier_required_members')
    result=parse(data.pop('result.json'))
    fields(result,{'record_type','mode','status','error_code','source_commit','request_sha256','inventory','claims'})
    check(result['record_type']=='q3_native_capture_result_v0'
          and result['source_commit']==expected_source_commit
          and sha(data['request.json'])==expected_request_sha256==result['request_sha256']
          and encoded(result['claims'])==encoded(C.CLAIMS),'carrier_result_binding')
    actual={n:{'size_bytes':len(b),'sha256':sha(b)} for n,b in sorted(data.items())}
    check(encoded(result['inventory'])==encoded(actual),'carrier_inventory')
    request=C.validate_request(data['request.json'],C.load_profile(source))
    check(request['source_commit']==expected_source_commit and result['mode']==request['mode'],'carrier_request')
    if result['status']=='complete':
        check(result['error_code'] is None,'complete_with_error')
        return validate_complete(source,data)
    check(result['status']=='incomplete' and type(result['error_code']) is str
          and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}',result['error_code']),'failure_status')
    return {'record_type':'q3_carrier_reconstruction_v0','complete':False,'mode':request['mode'],
            'request_sha256':expected_request_sha256,'failure_inventory_verified':True,
            'native_origin_reacquired':False,'tokenization_reperformed':False,
            'metric_recomputed':False,'claims':dict(C.CLAIMS)}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase',required=True,choices=['verify-inputs','verify-installation','verify-tokens','check-carrier'])
    ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--archive',type=Path);ap.add_argument('--staging',type=Path)
    ap.add_argument('--bundle',type=Path);ap.add_argument('--venv',type=Path)
    ap.add_argument('--bootstrap-inventory',type=Path);ap.add_argument('--pip-report',type=Path)
    ap.add_argument('--evidence',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--expected-archive-sha256');ap.add_argument('--expected-request-sha256');ap.add_argument('--expected-source-commit')
    args=ap.parse_args(argv)
    try:
        C.load_profile(args.source_root)
        if args.phase=='verify-inputs':
            check(args.archive is not None and args.staging is not None,'input_arguments')
            out=verify_archive(args.archive,args.staging,args.source_root)
        elif args.phase=='verify-installation':
            check(all(x is not None for x in [args.venv,args.bundle,args.bootstrap_inventory,args.pip_report]),'installation_arguments')
            out=verify_installation(args.venv,args.bundle,args.bootstrap_inventory,args.pip_report)
        elif args.phase=='verify-tokens':
            check(args.bundle is not None and args.evidence is not None,'token_arguments')
            out,examples=verify_live_tokens(args.source_root,args.bundle,args.evidence)
            if examples is not None:C.write_new(args.output.parent/'examples.jsonl',examples,0o644)
        else:
            check(args.archive is not None and args.expected_source_commit is not None,'carrier_arguments')
            C.source_snapshot(args.source_root,args.expected_source_commit,C.load_profile(args.source_root))
            out=check_carrier(args.archive,args.source_root,args.expected_archive_sha256,
                              args.expected_request_sha256,args.expected_source_commit)
        C.write_new(args.output,encoded(out),0o644)
        return 0 if out.get('complete',True) else 1
    except Exception:
        print('Q3 independent check rejected; no success artifact claimed.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
