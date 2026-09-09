#!/usr/bin/env python3
"""Independent, offline validation of the bounded-execution evidence carrier.

The verifier never imports the capture tool or consumer and never launches a
recorded subject program. Its result establishes the checked source/byte/event
relations within the declared trusted-supervisor boundary, not cryptographic
proof that an untrusted producer actually executed its assertions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import argparse as _argparse
import tempfile
import types
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from typing import Any, Mapping

VERSION = 'pulsemech_compute_bounded_execution_evidence_v0'
PROFILE = 'linux_sealed_descriptor_supervisor_v0'
REPOSITORY = 'HKati/pulse-release-gates-0.1'
WORKFLOW = '.github/workflows/pulsemech_compute_bounded_execution_reference.yml'
SCHEMA = 'schemas/pulsemech_compute_bounded_execution_evidence_v0.schema.json'
CHECKER = 'PULSE_safe_pack_v0/tools/check_gates.py'
CONSUMER = 'tools/consume_pulsemech_compute_bounded_result_v0.py'
CAPTURE = 'tools/capture_pulsemech_compute_bounded_execution_v0.py'
VALIDATOR = 'tools/check_pulsemech_compute_bounded_execution_v0.py'
ADAPTER = 'tools/build_pulsemech_compute_bounded_execution_inputs_v0.py'
POLICY = 'pulse_gate_policy_v0.yml'
REGISTRY = 'pulse_gate_registry_v0.yml'
POLICY_HELPER = 'tools/policy_to_require_args.py'
PLANNER = 'tools/plan_pulsemech_integration_v0.py'
REQUEST_SCHEMA = 'schemas/pulsemech_integration_request_v0.schema.json'
COMPONENT_SCHEMA = 'schemas/pulsemech_integration_component_manifest_v0.schema.json'
PLAN_SCHEMA = 'schemas/pulsemech_integration_plan_v0.schema.json'
CONTRACT = 'docs/compute/PULSEMECH_COMPUTE_BOUNDED_EXECUTION_CONTRACT_v0.md'
SOURCE_PATHS = (WORKFLOW, CHECKER, CONSUMER, CAPTURE, VALIDATOR, ADAPTER, POLICY, REGISTRY,
                POLICY_HELPER, PLANNER, REQUEST_SCHEMA, COMPONENT_SCHEMA,
                PLAN_SCHEMA, SCHEMA, CONTRACT,
                "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py",
                "tools/check_pulsemech_compute_subject_input_packet_v0.py",
                "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
                "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py",
                "tools/pulsemech_compute_binding_analyzer_core_v0.py",
                "tools/check_pulsemech_compute_binding_report_v0.py",
                "schemas/pulsemech_compute_binding_report_v0.schema.json",
                "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
                "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
                "tools/build_pulsemech_compute_planned_observed_relation_v0.py",
                "tools/check_pulsemech_compute_planned_observed_relation_v0.py",
                "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
                "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json")
CASES = ('allow', 'block_false', 'missing_required')
MEMBER_LIMIT = 2 * 1024 * 1024
TOTAL_LIMIT = 16 * 1024 * 1024
MAX_MEMBERS = 128
SEALS = 15
BOUNDARY = {'authority_effect':'none','same_run_release_authority_eligible':False,
            'active_gate_eligible':False,'resource_measurement':'unavailable',
            'acquisition_profile':PROFILE,
            'trusted_runtime':'reviewed_supervisor_interpreter_and_host_kernel',
            'visibility':'six_declared_direct_processes_and_their_bound_io'}


class EvidenceError(ValueError):
    """A stable, non-secret diagnostic code, never a raw-input excerpt."""


def need(condition: bool, code: str) -> None:
    if not condition:
        raise EvidenceError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                           allow_nan=False) + '\n').encode('utf-8')
    except (ValueError, TypeError, UnicodeError) as exc:
        raise EvidenceError('canonicalization_failed') from exc


def parse(raw: bytes, *, canonical_required: bool = True) -> dict[str, Any]:
    need(isinstance(raw, bytes) and len(raw) <= MEMBER_LIMIT, 'json_size_or_type')
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'json_duplicate_key')
            result[key] = value
        return result
    def invalid(value):
        raise EvidenceError('json_nonfinite_number')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=invalid, parse_float=invalid if canonical_required else float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise EvidenceError('json_encoding_or_syntax') from exc
    need(isinstance(value, dict), 'json_object_required')
    if canonical_required:
        need(canonical(value) == raw, 'json_not_canonical')
    return value


def timestamp(text: str) -> dt.datetime:
    need(isinstance(text, str) and bool(re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z', text)), 'timestamp_format')
    try:
        return dt.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=dt.timezone.utc)
    except ValueError as exc:
        raise EvidenceError('timestamp_range') from exc


def descriptor(member: str, raw: bytes) -> dict[str, Any]:
    return {'member':member, 'sha256':sha(raw), 'size_bytes':len(raw)}


def safe_member(name: str) -> bool:
    return (isinstance(name, str) and len(name) <= 300
            and bool(re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name))
            and all(x not in ('.','..') for x in name.split('/')))


def pack(members: Mapping[str, bytes]) -> bytes:
    need(0 < len(members) <= MAX_MEMBERS, 'carrier_member_count')
    need(sum(len(raw) for raw in members.values()) <= TOTAL_LIMIT, 'carrier_total_limit')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as z:
        for name, raw in sorted(members.items()):
            need(safe_member(name), 'carrier_member_path')
            need(isinstance(raw, bytes) and len(raw) <= MEMBER_LIMIT, 'carrier_member_limit')
            item = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            item.create_system = 3
            item.external_attr = (stat.S_IFREG | 0o644) << 16
            item.compress_type = zipfile.ZIP_STORED
            z.writestr(item, raw)
    return stream.getvalue()


def unpack(raw: bytes) -> dict[str, bytes]:
    need(isinstance(raw, bytes) and len(raw) <= TOTAL_LIMIT + 128*1024, 'carrier_byte_limit')
    result = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos = z.infolist()
            need(0 < len(infos) <= MAX_MEMBERS, 'carrier_member_count')
            need(len({i.filename for i in infos}) == len(infos), 'carrier_duplicate_member')
            total = 0
            for info in infos:
                need(safe_member(info.filename), 'carrier_member_path')
                need(info.filename not in result, 'carrier_duplicate_member')
                need(not info.is_dir() and stat.S_ISREG(info.external_attr >> 16), 'carrier_member_type')
                need(info.compress_type == zipfile.ZIP_STORED and info.flag_bits & 1 == 0,
                     'carrier_compression_or_encryption')
                need(info.file_size <= MEMBER_LIMIT and info.compress_size == info.file_size,
                     'carrier_member_limit')
                total += info.file_size
                need(total <= TOTAL_LIMIT, 'carrier_total_limit')
                result[info.filename] = z.read(info)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as exc:
        raise EvidenceError('carrier_invalid_zip') from exc
    # This closes local-header discrepancies, trailing bytes, extra fields,
    # duplicate central directories, comments and alternate encodings as well.
    need(pack(result) == raw, 'carrier_not_canonical')
    return result


def read_regular(path: Path, limit: int = TOTAL_LIMIT + 128*1024) -> bytes:
    """Capture through no-follow directory descriptors; never wait on a FIFO."""
    path = Path(path).absolute()
    need('..' not in path.parts, 'source_path_traversal')
    need(os.name=='posix' and hasattr(os,'O_NOFOLLOW') and os.open in os.supports_dir_fd,
         'descriptor_platform_unavailable')
    directory = None
    fd = None
    try:
        directory=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        for part in path.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size<=limit, 'source_type_or_limit')
        chunks,length=[],0
        while True:
            block=os.read(fd,min(65536,limit+1-length))
            if not block:break
            chunks.append(block);length+=len(block)
            need(length<=limit,'source_type_or_limit')
        after=os.fstat(fd)
        need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
             ==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
             and length==before.st_size,'source_changed_during_capture')
        return b''.join(chunks)
    except OSError as exc:
        raise EvidenceError('source_unavailable') from exc
    finally:
        if fd is not None:os.close(fd)
        if directory is not None:os.close(directory)


def git_source_inventory(root: Path, revision: str, paths: tuple[str,...]) -> dict[str,bytes]:
    """Batch-read the fixed inventory, with object-size and content checks.

    This is an immutable-object read, not a cache of a prior validation verdict.
    Every invocation checks the requested commit/tree and all returned blobs.
    """
    need(isinstance(revision,str) and bool(re.fullmatch('[0-9a-f]{40}',revision)), 'git_binding_invalid')
    need(0<len(paths)<=MAX_MEMBERS and len(paths)==len(set(paths)) and all(safe_member(p) for p in paths),'git_inventory_invalid')
    root=Path(root).absolute()
    need(root.is_dir() and all(not p.is_symlink() for p in (root,*root.parents)),'git_root_invalid')
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
         'GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0','HOME':str(root)}
    def run(args,raw=None):
        try:
            p=subprocess.run(['/usr/bin/git','--no-replace-objects','-C',str(root),*args],input=raw,
                env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:raise EvidenceError('git_source_unavailable') from exc
        need(p.returncode==0,'git_source_unavailable');return p.stdout
    need(run(['cat-file','-t',revision])==b'commit\n','git_commit_required')
    entries=run(['ls-tree','-rz',revision,'--',*paths]).split(b'\0')
    need(entries[-1]==b'','git_inventory_tree_invalid');entries.pop()
    ids={}
    for entry in entries:
        meta,sep,pathraw=entry.partition(b'\t');fields=meta.split()
        need(sep==b'\t' and len(fields)==3 and fields[0] in (b'100644',b'100755') and fields[1]==b'blob','git_source_not_regular')
        path=pathraw.decode('utf-8');oid=fields[2]
        need(path in paths and path not in ids and bool(re.fullmatch(b'[0-9a-f]{40}',oid)),'git_inventory_tree_invalid')
        ids[path]=oid
    need(set(ids)==set(paths),'git_source_not_regular')
    request=b''.join(ids[p]+b'\n' for p in paths)
    checks=run(['cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],request).splitlines()
    need(len(checks)==len(paths),'git_inventory_size_invalid')
    sizes={};total=0
    for path,line in zip(paths,checks):
        fields=line.split()
        need(len(fields)==3 and fields[0]==ids[path] and fields[1]==b'blob' and fields[2].isdigit(),'git_inventory_size_invalid')
        size=int(fields[2]);need(size<=MEMBER_LIMIT,'git_blob_limit');sizes[path]=size;total+=size
    need(total<=TOTAL_LIMIT,'git_inventory_total_limit')
    output=run(['cat-file','--batch'],request)
    position=0;result={}
    for path in paths:
        end=output.find(b'\n',position);need(end>=position,'git_inventory_header_missing')
        header=output[position:end].split();size=sizes[path]
        need(header==[ids[path],b'blob',str(size).encode()],'git_inventory_header_mismatch')
        data=output[end+1:end+1+size];position=end+1+size
        need(len(data)==size and output[position:position+1]==b'\n','git_blob_size_mismatch');position+=1
        oid=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest().encode()
        need(oid==ids[path],'git_blob_object_identity_mismatch');result[path]=data
    need(position==len(output),'git_inventory_trailing_bytes')
    return result


def git_blob(root: Path, revision: str, path: str) -> bytes:
    need(bool(re.fullmatch('[0-9a-f]{40}', revision)) and safe_member(path), 'git_binding_invalid')
    root = Path(root).absolute()
    need(root.is_dir() and all(not p.is_symlink() for p in (root,*root.parents)), 'git_root_invalid')
    git = '/usr/bin/git'
    need(Path(git).is_file(), 'trusted_git_unavailable')
    env = {'PATH':'/usr/bin:/bin', 'LC_ALL':'C', 'GIT_CONFIG_NOSYSTEM':'1',
           'GIT_CONFIG_GLOBAL':os.devnull, 'GIT_NO_REPLACE_OBJECTS':'1',
           'GIT_TERMINAL_PROMPT':'0', 'HOME':str(root)}
    def run(args):
        try:
            p = subprocess.run([git,'--no-replace-objects','-C',str(root),*args],
                               env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,timeout=10,check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EvidenceError('git_source_unavailable') from exc
        need(p.returncode == 0, 'git_source_unavailable')
        return p.stdout
    need(run(['cat-file','-t',revision]) == b'commit\n', 'git_commit_required')
    entry = run(['ls-tree','-z',revision,'--',path])
    need(entry.startswith((b'100644 blob ', b'100755 blob '))
         and entry.endswith(b'\t'+path.encode('utf-8')+b'\0')
         and entry.count(b'\0') == 1, 'git_source_not_regular')
    size = run(['cat-file','-s',revision+':'+path])
    need(size.strip().isdigit() and int(size) <= MEMBER_LIMIT, 'git_blob_limit')
    data = run(['cat-file','blob',revision+':'+path])
    need(len(data) == int(size), 'git_blob_size_mismatch')
    return data



def load_reconstruction_module(relative: str, *, repository_root: Path, revision: str):
    """Execute only a fixed reconstruction dependency, after Git/byte checks.

    This does not launch or import the capture implementation or subject consumer.
    A caller-supplied revision is a trust input, not acquisition authentication.
    """
    allowed = {
        "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py",
        "tools/check_pulsemech_compute_subject_input_packet_v0.py",
        "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py",
        "tools/pulsemech_compute_binding_analyzer_core_v0.py",
        "tools/check_pulsemech_compute_binding_report_v0.py",
        "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
        "tools/build_pulsemech_compute_planned_observed_relation_v0.py",
        "tools/check_pulsemech_compute_planned_observed_relation_v0.py",
        "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
    }
    need(relative in allowed, "reconstruction_dependency_not_allowed")
    root = Path(repository_root).absolute()
    raw = git_blob(root, revision, relative)
    need(read_regular(root / relative, MEMBER_LIMIT) == raw,
         "reconstruction_dependency_uncommitted:" + relative)
    name = "_pulse_bounded_reconstruction_" + sha(raw)
    module = types.ModuleType(name)
    module.__file__ = str(root / relative)
    module.__cached__ = None
    module.__pulsemech_source_sha256__ = sha(raw)
    sys.modules[name] = module
    try:
        exec(compile(raw, module.__file__, "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module

def validate_schema(value: dict, *, schema_bytes: bytes | None = None) -> None:
    import jsonschema
    if schema_bytes is None:
        schema_bytes = read_regular(Path(__file__).resolve().parents[1] / SCHEMA, MEMBER_LIMIT)
    schema = parse(schema_bytes, canonical_required=False)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    except (jsonschema.exceptions.SchemaError, RecursionError) as exc:
        raise EvidenceError('evidence_schema_invalid') from exc
    need(not errors, 'evidence_schema_rejected')


def check_context(context: dict, expected: dict) -> None:
    # The expected context is an explicit caller input. A consumer must obtain
    # it independently; copying it from the carrier adds no provenance.
    need(canonical(context) == canonical(expected), 'acquisition_context_mismatch')
    validate_schema({'schema_version':VERSION,'record_type':'pending_state',
                     'context_sha256':sha(canonical(context)), 'case_id':'allow',
                     'state':'pending','authority_effect':'none'})
    status = context.get('record_status')
    if status == 'observed':
        need(context.get('event_name') == 'workflow_dispatch', 'observed_event_invalid')
        identity = f"github:{context['repository']}:{context['run_id']}:{context['run_attempt']}"
        need(context.get('acquisition_id') == identity, 'observed_acquisition_id')
    elif status == 'example':
        need(context.get('event_name') == 'test' and
             context.get('acquisition_id','').startswith('example:'), 'example_identity_required')
    else:
        raise EvidenceError('record_status_invalid')


def strict_yaml(raw: bytes) -> dict:
    import yaml
    class Loader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        result = {}
        for kn, vn in node.value:
            key = loader.construct_object(kn, deep=deep)
            need(isinstance(key, str) and key not in result, 'yaml_duplicate_or_invalid_key')
            result[key] = loader.construct_object(vn, deep=deep)
        return result
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        value = yaml.load(raw.decode('utf-8'), Loader=Loader)
    except (yaml.YAMLError, UnicodeError, RecursionError) as exc:
        raise EvidenceError('yaml_invalid') from exc
    need(isinstance(value, dict), 'yaml_object_required')
    return value


def required_from_sources(policy: bytes, registry: bytes) -> list[str]:
    p, r = strict_yaml(policy), strict_yaml(registry)
    required = p.get('gates',{}).get('core_required')
    need(isinstance(required, list) and 0 < len(required) <= 64
         and all(isinstance(x,str) and bool(re.fullmatch('[a-z][a-z0-9_]*',x)) for x in required),
         'required_gate_list_invalid')
    need(len(set(required)) == len(required), 'required_gate_duplicate')
    need(isinstance(r.get('gates'),dict) and set(required) <= set(r['gates']), 'registry_missing_required')
    return required


def expected_case(context: dict, case: str, code: int, members: Mapping[str, bytes]) -> dict:
    prefix = f'results/{case}/'
    return {'case_id':case,'checker_execution_id':f'execution:{case}:checker',
            'consumer_execution_id':f'execution:{case}:consumer','expected_exit_code':code,
            'status':descriptor(f'inputs/{case}/status.json',members[f'inputs/{case}/status.json']),
            'pending_state':descriptor(f'inputs/{case}/pending.json',members[f'inputs/{case}/pending.json']),
            'checker_outputs':{'stdout':prefix+'checker.stdout','stderr':prefix+'checker.stderr',
                               'result_envelope':prefix+'process_result.json'},
            'consumer_outputs':{'terminal_state':prefix+'terminal_state.json','stderr':prefix+'consumer.stderr'}}


def verify_descriptor(value: dict, members: Mapping[str, bytes]) -> bytes:
    name = value.get('member')
    need(name in members and value == descriptor(name, members[name]), 'member_digest_mismatch')
    return members[name]


def snapshot_expected_context(value: dict) -> dict:
    """Freeze caller context while retaining the acquisition-mismatch boundary."""
    try:
        return parse(canonical(value))
    except EvidenceError as exc:
        raise EvidenceError('acquisition_context_mismatch') from exc


def verify_prelaunch(members: Mapping[str, bytes], *, repository_root: Path,
                     expected_context: dict, expected_prelaunch_sha256: str | None = None) -> dict:
    expected_context=snapshot_expected_context(expected_context)
    need('prelaunch.json' in members, 'prelaunch_missing')
    raw = members['prelaunch.json']
    if expected_prelaunch_sha256 is not None:
        need(sha(raw) == expected_prelaunch_sha256, 'prelaunch_digest_mismatch')
    spec = parse(raw)
    validate_schema(spec)
    need(spec['record_type'] == 'prelaunch', 'prelaunch_kind')
    context = spec['context']
    check_context(context, expected_context)
    timestamp(spec['created_at_utc'])
    need(spec['boundary'] == BOUNDARY, 'boundary_mismatch')
    sources = spec['source_bindings']
    need([s['path'] for s in sources] == sorted(SOURCE_PATHS), 'source_inventory_mismatch')
    committed_sources = git_source_inventory(repository_root,context['source_commit'],tuple(SOURCE_PATHS))
    for entry in sources:
        path = entry['path']
        need(entry['revision'] == context['source_commit'] and entry['member'] == 'sources/'+path,
             'source_binding_mismatch')
        source = committed_sources[path]
        need(entry == {'path':path,'revision':entry['revision'],**descriptor('sources/'+path,source)},
             'source_digest_mismatch')
        need(members.get(entry['member']) == source, 'source_bytes_mismatch')
    # Both the validating program and schema are the exact committed sources,
    # not neighbouring or substituted implementations chosen by the carrier.
    here = Path(__file__).absolute()
    need(here == Path(repository_root).absolute()/VALIDATOR, 'validator_path_mismatch')
    need(read_regular(here,MEMBER_LIMIT) == members['sources/'+VALIDATOR], 'validator_source_mismatch')
    need(read_regular(Path(repository_root)/SCHEMA,MEMBER_LIMIT) == members['sources/'+SCHEMA],
         'validator_schema_mismatch')
    validate_schema(spec, schema_bytes=members['sources/'+SCHEMA])
    required = required_from_sources(members['sources/'+POLICY],members['sources/'+REGISTRY])
    need(spec['required_gate_ids'] == required, 'policy_require_order_mismatch')
    need(members.get('inputs/required.newline') == ('\n'.join(required)+'\n').encode(),
         'policy_helper_output_mismatch')
    names = [x['member'] for x in spec['input_inventory']]
    expected_inputs = ['inputs/required.newline','planner/request.json','planner/components.json','planner/plan.json']
    for case in CASES:
        expected_inputs.extend([f'inputs/{case}/status.json', f'inputs/{case}/pending.json'])
    need(names == sorted(expected_inputs), 'prelaunch_input_inventory')
    for item in spec['input_inventory']:
        verify_descriptor(item,members)
    for case,code in zip(CASES,(0,1,2)):
        gates = {key:True for key in required}
        if code == 1:
            gates[required[0]] = False
        elif code == 2:
            del gates[required[0]]
        need(members[f'inputs/{case}/status.json'] == canonical({'gates':gates}), 'controlled_status_mismatch')
        pending = {'schema_version':VERSION,'record_type':'pending_state',
                   'context_sha256':sha(canonical(context)),'case_id':case,
                   'state':'pending','authority_effect':'none'}
        need(members[f'inputs/{case}/pending.json'] == canonical(pending), 'pending_state_mismatch')
    need(spec['cases'] == [expected_case(context,c,k,members) for c,k in zip(CASES,(0,1,2))],
         'predeclared_case_slots_mismatch')
    need(spec['planner'] == {key:descriptor(name,members[name]) for key,name in (
        ('request','planner/request.json'),('component_manifest','planner/components.json'),
        ('plan','planner/plan.json'))}, 'planner_binding_mismatch')
    # Validate the existing planner's contracts without executing captured code.
    import jsonschema
    for name,schema_path in [('request',REQUEST_SCHEMA),('components',COMPONENT_SCHEMA),('plan',PLAN_SCHEMA)]:
        schema = parse(members['sources/'+schema_path], canonical_required=False)
        doc = parse(members['planner/'+name+'.json'])
        need(not list(jsonschema.Draft202012Validator(schema).iter_errors(doc)), 'planner_contract_rejected')
    plan = parse(members['planner/plan.json'])
    need(plan['source']['policy_sha256'] == sha(members['sources/'+POLICY]), 'planner_policy_mismatch')
    need(plan['authority_boundary']['write_mode'] == 'plan_only', 'planner_not_read_only')
    expected_plan = replay_plan(spec,members,repository_root)
    need(members['planner/plan.json'] == canonical(expected_plan), 'planner_replay_mismatch')
    return spec


def replay_plan(spec: dict, members: Mapping[str,bytes], repository_root: Path) -> dict:
    """Replay the existing planner from checked bytes; never rerun subjects."""
    context = spec['context']
    request = parse(members['planner/request.json'])
    components = parse(members['planner/components.json'])
    need(request['request_id'] == 'bounded_reference_'+sha(canonical(context))
         and request['component_sets'] == ['bounded_reference_v0']
         and request['target_repository'] == {'repository_id':context['repository'],
             'default_branch':'main','ci_provider':'github_actions'}, 'planner_request_mismatch')
    expected_components = [{'id':role,'kind':'file','source_path':path,
                            'target_path':'reference/'+role+'.py','requires':[]}
                           for role,path in [('checker',CHECKER),('consumer',CONSUMER)]]
    need(components['source_repository']==REPOSITORY and components['policy_path']==POLICY
         and components['components']==expected_components, 'planner_component_mismatch')
    sets = components['component_sets']
    need(len(sets)==1 and sets[0]['id']=='bounded_reference_v0'
         and sets[0]['root_components']==['checker','consumer']
         and sets[0]['declared_gate_sets']==['core_required']
         and sets[0]['supported_ci_providers']==['github_actions'], 'planner_component_set_mismatch')
    with tempfile.TemporaryDirectory(prefix='pulse-bounded-plan-replay-') as directory:
        directory = Path(directory)
        source,target = directory/'source',directory/'target'
        source.mkdir();target.mkdir()
        for path in SOURCE_PATHS:
            destination = source/path
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(members['sources/'+path])
        (source/'components.json').write_bytes(members['planner/components.json'])
        (source/'request.json').write_bytes(members['planner/request.json'])
        env = {'PATH':'/usr/bin:/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1',
               'GIT_CONFIG_GLOBAL':os.devnull,'GIT_NO_REPLACE_OBJECTS':'1','HOME':str(directory)}
        def run(args,raw=None):
            try:
                p=subprocess.run(['/usr/bin/git','--no-replace-objects',*args],input=raw,
                    env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=10)
            except (OSError,subprocess.TimeoutExpired) as exc:
                raise EvidenceError('planner_git_unavailable') from exc
            need(p.returncode==0,'planner_git_failed')
            return p.stdout
        raw_commit=run(['-C',str(repository_root),'cat-file','commit',context['source_commit']])
        run(['init','--quiet',str(source)])
        imported=run(['-C',str(source),'hash-object','-w','-t','commit','--stdin'],raw_commit).decode().strip()
        need(imported==context['source_commit'],'planner_source_commit_mismatch')
        (source/'.git/HEAD').write_text('ref: refs/heads/reference\n')
        (source/'.git/refs/heads/reference').write_text(imported+'\n')
        raw = members['sources/'+PLANNER]
        name = '_pulse_bounded_verified_planner_'+sha(raw)
        module = types.ModuleType(name)
        module.__file__ = str(Path(repository_root).absolute()/PLANNER)
        sys.modules[name] = module
        try:
            exec(compile(raw,module.__file__,'exec'),module.__dict__)
            args = _argparse.Namespace(source_root=str(source),target_root=str(target),
                request=str(source/'request.json'),request_schema=str(source/REQUEST_SCHEMA),
                component_manifest=str(source/'components.json'),
                component_manifest_schema=str(source/COMPONENT_SCHEMA),plan_schema=str(source/PLAN_SCHEMA))
            plan,code = module.build_plan(args)
        finally:
            sys.modules.pop(name,None)
        need(code==0 and not any(target.iterdir()),'planner_nonzero_or_mutated_target')
        return plan


def invocation_projection(execution: dict) -> dict:
    return {k:execution[k] for k in ('execution_id','case_id','kind','pid','source_path',
        'source_sha256','arguments','sealed_inputs','started_at_utc','start_monotonic_ns')}


def process_result(spec: dict, prelaunch_sha256: str, execution: dict) -> dict:
    return {'schema_version':VERSION,'record_type':'process_result',
            'context_sha256':sha(canonical(spec['context'])),'prelaunch_sha256':prelaunch_sha256,
            'case_id':execution['case_id'],'execution_id':execution['execution_id'],
            'invocation_sha256':sha(canonical(invocation_projection(execution))),
            'exit_code':execution['exit_code'],'stdout':execution['stdout'],
            'stderr':execution['stderr'],'authority_effect':'none'}


def _expected_arguments(spec: dict, prelaunch_sha256: str, row: dict) -> list[str]:
    fds = {x['logical_role']:f"/proc/self/fd/{x['fd']}" for x in row['sealed_inputs']}
    if row['kind'] == 'checker':
        return ['-I','-S','-B',fds['source'],'--status',fds['status'],
                '--require',*spec['required_gate_ids']]
    return ['-I','-S','-B',fds['source'],'--result',fds['result'],'--stdout',fds['stdout'],
            '--stderr',fds['stderr'],'--pending',fds['pending'],
            '--context-sha256',sha(canonical(spec['context'])),
            '--prelaunch-sha256',prelaunch_sha256,'--case-id',row['case_id'],
            '--checker-execution-id',f"execution:{row['case_id']}:checker"]


def _check_execution(row: dict, spec: dict, prelaunch_sha256: str, members: Mapping[str,bytes]) -> None:
    case, kind = row['case_id'], row['kind']
    source = CHECKER if kind == 'checker' else CONSUMER
    need(row['execution_id'] == f'execution:{case}:{kind}' and row['source_path'] == source,
         'execution_occurrence_mismatch')
    need(row['source_sha256'] == sha(members['sources/'+source]), 'execution_source_mismatch')
    logical = {'source':members['sources/'+source]}
    if kind == 'checker':
        logical['status'] = members[f'inputs/{case}/status.json']
        output_names = (f'results/{case}/checker.stdout', f'results/{case}/checker.stderr')
    else:
        logical.update(result=members[f'results/{case}/process_result.json'],
                       stdout=members[f'results/{case}/checker.stdout'],
                       stderr=members[f'results/{case}/checker.stderr'],
                       pending=members[f'inputs/{case}/pending.json'])
        output_names = (f'results/{case}/terminal_state.json', f'results/{case}/consumer.stderr')
    sealed = row['sealed_inputs']
    need([x['logical_role'] for x in sealed] == sorted(logical), 'execution_input_roles')
    need(len({x['fd'] for x in sealed}) == len(sealed), 'execution_duplicate_descriptor')
    for item in sealed:
        raw = logical[item['logical_role']]
        need(item['seal_mask'] == SEALS and item['sha256'] == sha(raw)
             and item['size_bytes'] == len(raw), 'execution_input_binding_mismatch')
    need(row['arguments'] == _expected_arguments(spec,prelaunch_sha256,row), 'execution_arguments_mismatch')
    need(row['stdout'] == descriptor(output_names[0],members[output_names[0]])
         and row['stderr'] == descriptor(output_names[1],members[output_names[1]]), 'execution_output_binding_mismatch')
    need(timestamp(row['started_at_utc']) <= timestamp(row['completed_at_utc']), 'execution_time_reversal')
    need(row['start_monotonic_ns'] <= row['end_monotonic_ns'], 'execution_monotonic_reversal')
    need(row['end_monotonic_ns'] - row['start_monotonic_ns'] <= 31_000_000_000, 'execution_duration_limit')


@dataclass(frozen=True)
class ValidatedEvidence:
    """A result container, not a capability or substitute for raw input validation."""
    members: Mapping[str, bytes]
    prelaunch: dict[str, Any]
    capture: dict[str, Any]
    carrier_sha256: str
    expected_context: dict[str, Any]
    case_outcomes: tuple[dict[str, Any], ...]


def verify_capture(carrier_bytes: bytes, *, repository_root: Path, expected_context: dict,
                   expected_prelaunch_sha256: str) -> ValidatedEvidence:
    need(bool(re.fullmatch('[0-9a-f]{64}', expected_prelaunch_sha256)), 'expected_prelaunch_required')
    expected_context=snapshot_expected_context(expected_context)
    members = unpack(carrier_bytes)
    spec = verify_prelaunch(members,repository_root=repository_root,expected_context=expected_context,
                            expected_prelaunch_sha256=expected_prelaunch_sha256)
    need('capture.json' in members, 'capture_missing')
    capture = parse(members['capture.json'])
    validate_schema(capture, schema_bytes=members['sources/'+SCHEMA])
    need(capture['record_type'] == 'capture', 'capture_kind')
    check_context(capture['context'],expected_context)
    need(capture['prelaunch_sha256'] == expected_prelaunch_sha256, 'capture_prelaunch_mismatch')
    inventory = capture['member_inventory']
    need([x['member'] for x in inventory] == sorted(set(members)-{'capture.json'}), 'capture_inventory_mismatch')
    for item in inventory:
        verify_descriptor(item,members)
    source_names = {'sources/'+p for p in SOURCE_PATHS}
    input_names = {x['member'] for x in spec['input_inventory']}
    output_names = {name for case in spec['cases'] for group in ('checker_outputs','consumer_outputs')
                    for name in case[group].values()}
    need(set(members) == source_names | input_names | output_names | {'prelaunch.json','capture.json'},
         'capture_members_not_declared')
    rows = capture['executions']
    expected_ids = [f'execution:{case}:{kind}' for case in CASES for kind in ('checker','consumer')]
    need([r['execution_id'] for r in rows] == expected_ids, 'execution_extent_mismatch')
    start,end = timestamp(capture['started_at_utc']),timestamp(capture['completed_at_utc'])
    need(timestamp(spec['created_at_utc']) <= start <= end, 'capture_time_reversal')
    prior_wall, prior_mono = start, -1
    for row in rows:
        _check_execution(row,spec,expected_prelaunch_sha256,members)
        need(prior_wall <= timestamp(row['started_at_utc']) and row['start_monotonic_ns'] >= prior_mono,
             'execution_order_mismatch')
        prior_wall, prior_mono = timestamp(row['completed_at_utc']), row['end_monotonic_ns']
    need(prior_wall <= end, 'capture_terminal_time')
    expected_terminals = sorted(name for c in spec['cases'] for name in c['consumer_outputs'].values())
    need(capture['terminal_roles'] == expected_terminals, 'terminal_extent_mismatch')
    outcomes = []
    for n,case in enumerate(spec['cases']):
        checker,consumer = rows[2*n:2*n+2]
        caseid = case['case_id']
        envelope = members[case['checker_outputs']['result_envelope']]
        need(envelope == canonical(process_result(spec,expected_prelaunch_sha256,checker)),
             'process_result_mismatch')
        validate_schema(parse(envelope),schema_bytes=members['sources/'+SCHEMA])
        need(consumer['exit_code'] == 0 and members[case['consumer_outputs']['stderr']] == b'',
             'consumer_did_not_complete')
        code = checker['exit_code']
        need(code in (0,1,2), 'checker_non_decision_result')
        terminal = parse(members[case['consumer_outputs']['terminal_state']])
        validate_schema(terminal,schema_bytes=members['sources/'+SCHEMA])
        # Independent interpretation: do not import the consumer implementation.
        expected = {'schema_version':VERSION,'record_type':'terminal_state',
                    'context_sha256':sha(canonical(spec['context'])),
                    'prelaunch_sha256':expected_prelaunch_sha256,'case_id':caseid,
                    'checker_execution_id':checker['execution_id'],
                    'state':'ready' if code==0 else 'held',
                    'reason':{0:'all_required_true',1:'required_value_not_true',
                              2:'missing_or_invalid_required_input'}[code],
                    'checker_exit_code':code,'result_sha256':sha(envelope),
                    'pending_state_sha256':case['pending_state']['sha256'],
                    'checker_stdout_sha256':checker['stdout']['sha256'],
                    'checker_stderr_sha256':checker['stderr']['sha256'],'authority_effect':'none'}
        need(terminal == expected, 'terminal_consumption_or_state_mismatch')
        outcomes.append({'case_id':caseid,'actual_exit_code':code,'expected_exit_code':case['expected_exit_code'],
                         'matches_expected':code==case['expected_exit_code'],'terminal_state':terminal['state']})
    return ValidatedEvidence(members,spec,capture,sha(carrier_bytes),dict(expected_context),tuple(outcomes))


def publish_new(path: Path, raw: bytes, *, repository_root: Path) -> None:
    """Atomically link an anonymous staged inode; never unlink a visible path.

    O_TMPFILE makes rollback a descriptor close, so an unrelated replacement
    cannot be deleted in a stat/unlink race. Linking is the final commit point.
    This guarantees non-replacing visibility, not post-crash directory durability.
    """
    path = Path(path).absolute()
    need('..' not in path.parts, 'output_traversal')
    need(not path.is_relative_to(Path(repository_root).resolve()), 'output_inside_repository')
    need(path.name not in ('','.','..'), 'output_name_invalid')
    need(sys.platform == 'linux' and hasattr(os,'O_TMPFILE'), 'anonymous_publication_unavailable')
    parent = path.parent
    need(parent.is_dir(), 'output_parent_unavailable')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    staged = None
    try:
        for part in parent.parts[1:]:
            child = os.open(part,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory); directory = child
        staged = os.open('.',os.O_RDWR | os.O_TMPFILE | os.O_CLOEXEC,0o600,dir_fd=directory)
        view = memoryview(raw)
        while view:
            count = os.write(staged,view)
            need(count > 0,'output_write_failed')
            view = view[count:]
        os.fsync(staged)
        # With explicit dir_fds, Python uses linkat(AT_SYMLINK_FOLLOW) to link
        # this owned anonymous inode. An existing destination yields EEXIST.
        os.link('/proc/self/fd/'+str(staged),path.name,src_dir_fd=directory,
                dst_dir_fd=directory,follow_symlinks=True)
    except FileExistsError as exc:
        raise EvidenceError('output_already_exists') from exc
    except OSError as exc:
        raise EvidenceError('output_publication_failed') from exc
    finally:
        if staged is not None:
            os.close(staged)
        os.close(directory)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--carrier', required=True, type=Path)
    ap.add_argument('--repository-root', required=True, type=Path)
    ap.add_argument('--expected-context', required=True, type=Path)
    ap.add_argument('--expected-prelaunch-sha256', required=True)
    args = ap.parse_args(argv)
    try:
        checked = verify_capture(read_regular(args.carrier),repository_root=args.repository_root,
                                 expected_context=parse(read_regular(args.expected_context,MEMBER_LIMIT)),
                                 expected_prelaunch_sha256=args.expected_prelaunch_sha256)
        sys.stdout.buffer.write(canonical({'ok':True,'profile':PROFILE,
             'carrier_sha256':checked.carrier_sha256,'cases':list(checked.case_outcomes),
             'verification_boundary':'source_bytes_and_event_relations_with_expected_acquisition_context',
             'acquisition_authenticity':'requires_independent_workflow_provenance',
             'authority_effect':'none'}))
        return 0
    except (EvidenceError, KeyError, TypeError, ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc,EvidenceError) else type(exc).__name__
        sys.stdout.buffer.write(canonical({'ok':False,'error':code,'authority_effect':'none'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
