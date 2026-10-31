#!/usr/bin/env python3
"""W1 input admission and offline observation-record consistency checker.

Read-only, standard-library only. Never imports or executes a candidate, mapper,
launcher, archived program or workflow. Record consistency is not authenticated
native observation, containment verification, execution permission or authority.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import math
import os
import re
import stat
import sys
import json
from pathlib import Path, PurePosixPath
import zipfile

BASE = 'd04264496365ee681167b194b5a9aebb4991374a'
ARCHIVE_SHA = 'c63f2ee6e2dfae21ec3736fbd99f8169b8c5b7a06a28c8a8a3e7dad2ac2fcd18'
MANIFEST_SHA = '26083c5fffbfdbc4cef002db59663d6a0a262d5f36a737f8dcd4a5f20484d178'
PREFIX = 'PD_SM_02_SCRATCH_PILOT_20261027/'
ORDER = ['P00', 'N01', 'N07', 'N08', 'N02']
BLOBS = {'check_impact.py':'3cef3a623bafff032f993c96357a29294068f0d4', 'fixtures.json':'76542b40898d5c13deb9163addfed9fddb47ebe0', 'profile.json':'1cd2e5928ff86e745deb8fb5a991e718448cfd7c', 'run_local.py':'dbde9517f39082a854f31ef8b97be200c9efeb75', 'source_model.py':'5c81b43f4bf5d02118058627c48371f8996b4d70', 'test_preexecution.py':'2571640af4893df8ec1e364ac39d412c4a1401ce'}
ROLES = dict(zip(ORDER, ['positive_control','primary_witness','primary_witness','primary_witness','primitive_refusal_control']))
EXPECTED_NUMBERS = {'P00':(1,22,1),'N01':(1,22,0),'N07':(2,44,1),'N08':(1,22,1),'N02':(0,0,0)}
FALSE_SUPPORT = {'P00':[], 'N01':['ack','audit','intent'], 'N07':['single_use'], 'N08':['ack','audit','intent'], 'N02':None}
ORDER_PREDICTIONS = {
 'P00':'matching intent persistence and matching ACK precede the sole effect',
 'N01':'one successful write occurs without any monitor-request operation or intent record',
 'N07':'two distinct successful writes for request-0 follow one reservation and one matching intent',
 'N08':'the successful write completes before broker_request begins; later matching intent/ACK do not repair the earlier prefix',
 'N02':'direct_sink_write rejects before any sink write; no native counterexample confirmation is predicted',
}
class Invalid(ValueError):
    """A closed input/record contract was not met."""
    pass

class Incomplete(Invalid):
    """Available records do not close the required observation prefix."""
    pass

def require(ok: bool, code: str) -> None:
    if not ok:
        raise Invalid(code)

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def canonical(value: object) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result

def strict(raw: bytes):
    require(type(raw) is bytes and len(raw) <= 4 * 1024 * 1024, 'json_size')
    require(not raw.startswith(b"\xef\xbb\xbf"), 'json_bom')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
             parse_constant=lambda value: (_ for _ in ()).throw(Invalid('nonfinite_json')))
        def walk(item, depth=0):
            require(depth <= 64, 'json_depth')
            if isinstance(item, float):
                require(math.isfinite(item), 'nonfinite_json')
            elif isinstance(item, str):
                item.encode('utf-8')
            elif isinstance(item, dict):
                for key, child in item.items():
                    key.encode('utf-8'); walk(child, depth+1)
            elif isinstance(item, list):
                for child in item: walk(child, depth+1)
        walk(value)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise Invalid('invalid_json') from exc

def archive_records(raw: bytes):
    require(sha(raw)==ARCHIVE_SHA and len(raw)==329950, 'archive_identity')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        require(len(names)==len(set(names))==473, 'archive_member_set')
        for name in names:
            p=PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and name.startswith(PREFIX), 'unsafe_archive_path')
        require(all(not i.is_dir() and not (i.flag_bits & 1) and
                    stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
                    for i in z.infolist()), 'archive_member_type')
        require(sum(i.file_size for i in z.infolist()) <= 64 * 1024 * 1024,
                'archive_expansion_limit')
        records={n[len(PREFIX):]:z.read(n) for n in names}
    require(sha(records['MANIFEST.json'])==MANIFEST_SHA, 'manifest_identity')
    manifest=strict(records['MANIFEST.json'])
    require(manifest['file_count']==len(manifest['files'])==471, 'manifest_count')
    paths=[row['path'] for row in manifest['files']]
    require(len(set(paths))==471, 'manifest_duplicate_path')
    require(set(records)==set(paths)|{'MANIFEST.json','MANIFEST.sha256'}, 'manifest_closed_inventory')
    for row in manifest['files']:
        b=records[row['path']]
        require(len(b)==row['bytes'] and sha(b)==row['sha256'], 'manifest_entry:'+row['path'])
    return records

def operations_from_text(text: str, profile: dict) -> list:
    module=ast.parse(text)
    require(len(module.body)==1 and isinstance(module.body[0],ast.FunctionDef), 'candidate_shape')
    fn=module.body[0]
    require(fn.name=='candidate', 'candidate_entrypoint')
    a=fn.args
    require(not fn.decorator_list and fn.returns is None and
            not getattr(fn, 'type_params', []) and not a.posonlyargs and
            not a.args and a.vararg is None and not a.kwonlyargs and
            a.kwarg is None and not a.defaults and not a.kw_defaults,
            'candidate_function_shape')
    aliases={}; result=[]
    for item in fn.body:
        if isinstance(item,ast.Assign):
            require(len(item.targets)==1 and isinstance(item.targets[0],ast.Name), 'candidate_assignment')
            require(isinstance(item.value,ast.Constant) and type(item.value.value) is str, 'candidate_constant')
            name=item.targets[0].id
            require(name not in aliases and name not in profile['candidate_language']['primitives']
                    and not name.startswith('__'), 'candidate_local_binding')
            aliases[name]=item.value.value
            continue
        require(isinstance(item,ast.Expr) and isinstance(item.value,ast.Call), 'candidate_statement')
        call=item.value
        require(isinstance(call.func,ast.Name) and not call.keywords, 'candidate_call')
        prim=call.func.id
        require(prim in profile['candidate_language']['primitives'], 'candidate_primitive')
        spec=profile['candidate_language']['primitives'][prim]
        args=[]
        for arg in call.args:
            if isinstance(arg,ast.Constant) and type(arg.value) is str:
                args.append(arg.value)
            elif isinstance(arg,ast.Name) and arg.id in aliases:
                args.append(aliases[arg.id])
            else: raise Invalid('candidate_arg')
        require(len(args)==spec['arity'], 'candidate_arity')
        for value,domain in zip(args,spec['arg_domains']):
            require(value in profile['domains'][domain], 'candidate_domain')
        result.append({'index':len(result),'primitive':prim,'args':args,'kind':spec['kind'],
                       'line':call.lineno,'column':call.col_offset,
                       'source_fragment_sha256':sha((ast.get_source_segment(text,item) or '').encode())})
    return result

def validate(selection: dict, binding: dict, records: dict, raw_selection: bytes | None = None):
    require(selection.get('schema_version')=='pd_sm_02_w1_selection_v0', 'selection_schema')
    require(binding.get('schema_version')=='pd_sm_02_w1_source_binding_v0', 'binding_schema')
    require(selection.get('experiment_id')==binding.get('experiment_id')=='PD-SM-02-W1', 'experiment_identity')
    require(selection.get('authority_effect')==binding.get('authority_effect')=='none', 'authority_boundary')
    require(selection.get('status')=='PREREGISTERED_NOT_RUN', 'preparation_status')
    require(selection.get('execution_authorization') is False and binding.get('owner_authorization_for_w1') is False, 'no_authorization')
    require(selection.get('native_harness_implemented') is False, 'no_harness_claim')
    require(type(selection.get('new_candidate_execution_count')) is int and selection['new_candidate_execution_count']==0, 'no_new_execution_count')
    require(selection.get('observations') is None, 'no_observation_claim')
    require(all(binding.get(k) is False for k in ['new_execution','new_model_replay','hosted_ci_verification']), 'no_execution_or_ci_claim')
    require(binding.get('inspected_repository_commit')==BASE, 'inspected_source')
    require(binding.get('historical_implementation_commit')=='4cb5f7dbe00cfbaf5bd50f77423e4d671fa71905', 'historical_implementation')
    require(binding.get('historical_result_preservation_commit')=='5bb3cae1ea562cbfde4b80f7bc3878bf3d92f6be', 'historical_preservation')
    require(binding['archive']['raw_sha256']==ARCHIVE_SHA and binding['archive']['manifest_raw_sha256']==MANIFEST_SHA, 'archive_binding')
    require(binding['archive']['bytes']==329950 and binding['archive']['manifest_entries']==471 and binding['archive']['members']==473, 'archive_counts')
    if raw_selection is not None:
        require(sha(raw_selection)==binding['selection']['raw_sha256'] and len(raw_selection)==binding['selection']['bytes'], 'selection_raw_binding')
    require(selection.get('case_count')==5 and selection.get('case_order')==ORDER, 'case_order')
    require(selection.get('primary_witness_case_ids')==['N01','N07','N08'] and selection.get('control_case_ids')==['P00','N02'], 'role_partition')
    require(selection.get('maximum_new_candidate_invocations')==5 and type(selection['maximum_new_candidate_invocations']) is int, 'invocation_budget')
    require(selection.get('automatic_retry') is False, 'no_automatic_retry')
    require([x.get('case_id') for x in selection['cases']]==ORDER, 'case_inventory')
    require(len(binding['source_files'])==6 and {x['repository_path'].split('/')[-1] for x in binding['source_files']}==set(BLOBS), 'source_inventory')
    for row in binding['source_files']:
        name=row['repository_path'].split('/')[-1]
        require(row['repository_path']=='examples/paradox_preexecution_impact_v0/'+name and row['archive_member']=='implementation_snapshot/'+name, 'source_path')
        raw=records[row['archive_member']]
        require(blob(raw)==row['git_blob_sha1']==BLOBS[name], 'source_git_blob')
        require(sha(raw)==row['raw_sha256'] and len(raw)==row['bytes'], 'source_raw_binding')
    runtime=records['implementation_snapshot/run_local.py'].decode()
    nodes={n.name:n for n in ast.walk(ast.parse(runtime)) if isinstance(n,ast.FunctionDef)}
    required_regions={'_compile_runtime_candidate','_monitor','bind_request','reserve','broker_request','append_sink','direct_sink_write'}
    require({r['symbol'] for r in binding['source_regions']}==required_regions and len(binding['source_regions'])==len(required_regions), 'source_region_inventory')
    for row in binding['source_regions']:
        n=nodes[row['symbol']]
        segment='\n'.join(runtime.splitlines()[n.lineno-1:n.end_lineno]).encode()
        require(row['start_line']==n.lineno and row['end_line']==n.end_lineno and row['line_slice_sha256']==sha(segment), 'source_region_binding')
    direct=nodes['direct_sink_write']
    require(len(direct.body)==1 and isinstance(direct.body[0],ast.Raise), 'native_direct_refusal_shape')
    require('direct_effect_route_not_admitted' in ast.get_source_segment(runtime,direct), 'native_direct_refusal_code')
    profile=strict(records['implementation_snapshot/profile.json'])
    fixture=strict(records['implementation_snapshot/fixtures.json'])
    cases={c['case_id']:c for c in fixture['cases']}
    healthy=next(s for s in profile['environment_scenarios'] if s['id']=='healthy')
    require(selection.get('scenario')==healthy, 'scenario_binding')
    require(selection.get('profile_canonical_sha256')==sha(canonical(profile)), 'profile_canonical_binding')
    require(selection.get('remaining_case_ids_out_of_scope')==[c['case_id'] for c in fixture['cases'] if c['case_id'] not in ORDER], 'out_of_scope_partition')
    bound_members=0
    for i,row in enumerate(selection['cases']):
        cid=row['case_id']; original=cases[cid];stem=f'cases/{cid}/'
        require(row['role']==ROLES[cid] and row['planned_order']==i+1, 'case_role')
        require(row['w1_execution_status']=='NOT_RUN' and row['w1_observed_result'] is None, 'case_not_run')
        candidate=records[stem+'inputs/candidate.py']
        require(row['candidate_source'].encode()==candidate==original['candidate_source'].encode(), 'candidate_source_binding')
        require(row['candidate_raw_sha256']==sha(candidate), 'candidate_digest')
        context=strict(records[stem+'inputs/context.json'])
        require(row['context']==context==original['context'], 'context_binding')
        require(row['context_canonical_sha256']==sha(canonical(context)), 'context_canonical_binding')
        require(row['historical_context_raw_sha256']==sha(records[stem+'inputs/context.json']), 'context_raw_binding')
        require(row['scenario_id']=='healthy' and row['attempt_index']==0, 'case_scenario')
        model=strict(records[stem+'records/model.json'])
        require(row['operations']==model['operations']==operations_from_text(row['candidate_source'],profile), 'operation_mapping')
        a=strict(records[stem+'records/assessment.json'])
        result=strict(records[stem+'CASE_RESULT.json'])
        require(row['historical_assessment']==a['assessment']==original['expected_assessment'], 'historical_assessment')
        require(row['historical_native_status']==result['execution_observation_status'], 'historical_native_status')
        terminal=None if cid=='P00' else 'checker_replay_not_eligible'
        require(row['historical_authorized_terminal']==terminal, 'historical_terminal')
        if terminal:
            require(records[stem+'logs/04_authorized_launch_attempt.stderr'].decode().rstrip().endswith('LaunchError: '+terminal), 'actual_archived_terminal')
        h=next(s for s in a['finite_scenarios'] if s.get('scenario')=='healthy')
        require(row['historical_healthy_projection_canonical_sha256']==sha(canonical(h)), 'healthy_projection_binding')
        if cid=='P00': require(row['selected_model_witness'] is None, 'positive_has_no_counterexample')
        else:
            choices=[(j,w) for j,w in enumerate(a['counterexamples']) if w['scenario']=='healthy' and w['attempt']==0 and (cid!='N02' or w['route']=='direct_sink_write')]
            require(len(choices)==1, 'unique_witness')
            j,w=choices[0];op=model['operations'][w['operation_index']]
            expected={'json_pointer':f'/counterexamples/{j}','canonical_sha256':sha(canonical(w)), 'witness':w,'source_line':op['line'],'source_fragment_sha256':op['source_fragment_sha256']}
            require(row['selected_model_witness']==expected, 'witness_binding')
        pred=row['predicted_diagnostic_native_result'];nums=EXPECTED_NUMBERS[cid]
        require(tuple(pred.get(k) for k in ['effect_count','sink_bytes','audit_records'])==nums, 'prediction_counts')
        require(pred['candidate_terminal']==('PRIMITIVE_REFUSED' if cid=='N02' else 'COMPLETED'), 'prediction_terminal')
        require(pred['terminal_error_code']==('direct_effect_route_not_admitted' if cid=='N02' else None), 'prediction_error')
        require(pred['falsified_support_at_selected_effect']==FALSE_SUPPORT[cid], 'prediction_support')
        require(pred['order_obligation']==ORDER_PREDICTIONS[cid], 'prediction_order')
        require(row['prediction_basis']=='STATIC_SOURCE_INSPECTION_ONLY_NOT_NEW_OBSERVATION', 'prediction_not_observation')
        suffixes=['inputs/candidate.py','inputs/context.json','records/model.json','records/assessment.json','records/preflight.json','CASE_RESULT.json','logs/04_authorized_launch_attempt.stderr']
        if cid=='P00':suffixes+=['scratch_output/sink.bin','scratch_output/monitor.jsonl','scratch_output/RESULT.json']
        require([m['path'] for m in row['archive_members']]==[stem+s for s in suffixes], 'case_member_inventory')
        for m in row['archive_members']:
            b=records[m['path']]
            require(m['bytes']==len(b) and m['raw_sha256']==sha(b), 'case_member_binding')
            bound_members+=1
    return {'status':'PREPARATION_VALID','archive_manifest_entries_verified':471,'source_files_bound':6,'selected_cases_bound':5,'selected_archived_members_bound':bound_members,'primary_witnesses':3,'controls':2,'experiment_execution_status':'NOT_RUN','new_candidate_executions':0,'new_mapper_checker_replay':False,'authority_effect':'none'}

# These are the immutable planning bytes merged in #2967, not current-main aliases.
SELECTION_SHA = 'a04ff29eba4fda99e575f1984bfa9e91622fdd02d4ddfb2e01966e25967d5620'
BINDING_SHA = 'b43c3995b0661d828b5e433c1041c28ee5a9bf4d99ebe095b1d1f0bd892010c3'
CONTRACT_SHA = 'dd744fa97835627d68bb6b66e38885d8f9115e959f081b4b8645c257c75c91a0'
SCHEMA = 'pd_sm_02_w1_observation_record_v0'
REPORT = 'pd_sm_02_w1_record_check_v0'
SUBJECT = 'pd_sm_02_w1_diagnostic_healthy_v0'
RUNTIME = {'implementation':'CPython', 'version':'3.13.5', 'system':'Linux', 'machine':'x86_64'}
IDENTITY_KEYS = {'harness_sha256', 'observer_sha256', 'containment_config_sha256',
                 'runtime_manifest_sha256', 'run_request_sha256'}
MAX_EVENTS = 128


def exact_keys(value, keys, code):
    require(type(value) is dict and set(value) == set(keys), code)


def integer(value, low, high, code):
    require(type(value) is int and low <= value <= high, code)


def hex_bytes(value, maximum, code):
    require(type(value) is str and len(value) <= maximum * 2 and
            re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None, code)
    return bytes.fromhex(value)


def read_regular(path: Path, limit: int) -> bytes:
    """Bounded single-open read; do not follow a terminal symlink or accept a FIFO."""
    require(not path.is_symlink(), 'input_symlink')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) |
                 getattr(os, 'O_NONBLOCK', 0))
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode), 'input_not_regular')
        require(info.st_size <= limit, 'input_size_limit')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        require(len(raw) <= limit, 'input_size_limit')
        return raw
    finally:
        os.close(fd)


def admit_inputs(repo: Path):
    """Bind full planning files, archived records and six current program/data files."""
    exp = repo / 'docs/experiments'
    selection_raw = read_regular(exp / 'PD_SM_02_W1_SELECTION_v0.json', 128 * 1024)
    binding_raw = read_regular(exp / 'PD_SM_02_W1_SOURCE_BINDING_v0.json', 32 * 1024)
    contract_raw = read_regular(exp / 'PD_SM_02_W1_CONTRACT_v0.md', 64 * 1024)
    require(sha(selection_raw) == SELECTION_SHA, 'selection_identity')
    require(sha(binding_raw) == BINDING_SHA, 'source_binding_identity')
    require(sha(contract_raw) == CONTRACT_SHA, 'contract_identity')
    selection, binding = strict(selection_raw), strict(binding_raw)
    archive_raw = read_regular(repo / binding['archive']['repository_path'], 329950)
    records = archive_records(archive_raw)
    receipt = validate(selection, binding, records, selection_raw)
    for row in binding['source_files']:
        raw = read_regular(repo / row['repository_path'], 256 * 1024)
        require(raw == records[row['archive_member']], 'checkout_source_binding:'+row['repository_path'])
    receipt.update(schema_version='pd_sm_02_w1_input_receipt_v0',
                   selection_sha256=SELECTION_SHA, source_binding_sha256=BINDING_SHA,
                   contract_sha256=CONTRACT_SHA, archive_sha256=ARCHIVE_SHA,
                   historical_source_commit=BASE, execution_authorized=False,
                   native_witness_observed=None, containment_observed=None,
                   verifier_source_sha256=sha(read_regular(Path(__file__),512*1024)))
    return selection, receipt


def _event_graph(case, row, run_id):
    """Build only process-local edges and byte-matched request/ACK communication edges."""
    events = case['events']
    require(type(events) is list and 1 <= len(events) <= MAX_EVENTS, 'event_inventory')
    processes = case['processes']
    exact_keys(processes, {'worker','monitor','supervisor'}, 'process_inventory')
    for role in ('worker','supervisor'):
        integer(processes[role], 1, 2**31-1, 'process_id')
    if processes['monitor'] is not None:
        integer(processes['monitor'], 1, 2**31-1, 'monitor_process_id')
    pids = [p for p in processes.values() if p is not None]
    require(len(pids) == len(set(pids)), 'process_identity_collision')
    by_id, by_process = {}, {name:[] for name in processes}
    allowed_kinds = {'candidate_start', 'op_begin', 'op_end', 'request_send',
        'request_receive', 'intent_persisted', 'ack_send', 'ack_receive',
        'sink_write_completed', 'candidate_terminal', 'supervisor_terminal'}
    for e in events:
        exact_keys(e, {'event_id','run_id','case_id','attempt','process','sequence',
                       'operation_index','kind','data'}, 'event_shape')
        require(type(e['event_id']) is str and
                re.fullmatch(r'[A-Za-z0-9_-]{1,64}',e['event_id']), 'event_id')
        require(e['event_id'] not in by_id, 'duplicate_event_id')
        require(e['run_id'] == run_id and e['case_id'] == row['case_id'], 'event_subject')
        integer(e['attempt'], 1, 1, 'event_attempt')
        require(e['process'] in by_process and processes[e['process']] is not None,
                'event_process')
        integer(e['sequence'], 1, MAX_EVENTS, 'event_sequence')
        require(e['kind'] in allowed_kinds and type(e['data']) is dict, 'event_kind')
        if e['kind'] in {'candidate_start','candidate_terminal','supervisor_terminal'}:
            require(e['operation_index'] is None, 'terminal_operation_index')
        else:
            integer(e['operation_index'], 0, len(row['operations'])-1, 'event_operation')
        by_id[e['event_id']] = e
        by_process[e['process']].append(e)
    edges = {eid:set() for eid in by_id}
    for process, items in by_process.items():
        items.sort(key=lambda e:e['sequence'])
        seq = [e['sequence'] for e in items]
        if seq != list(range(1,len(items)+1)):
            raise Incomplete('process_sequence_gap_or_duplicate:'+process)
        for left,right in zip(items,items[1:]):
            edges[left['event_id']].add(right['event_id'])
    links = case['message_links']
    require(type(links) is list and len(links) <= 2, 'communication_inventory')
    linked = set()
    for link in links:
        exact_keys(link, {'channel','send','receive','payload_sha256'}, 'communication_shape')
        channel = link['channel']
        require(channel in ('request','ack'), 'communication_channel')
        require(link['send'] in by_id and link['receive'] in by_id, 'communication_endpoint')
        se,revent=by_id[link['send']],by_id[link['receive']]
        expected = ('worker','monitor') if channel=='request' else ('monitor','worker')
        require((se['process'],revent['process'])==expected and
                se['kind']==channel+'_send' and revent['kind']==channel+'_receive',
                'communication_direction')
        require(se['operation_index']==revent['operation_index'], 'communication_operation')
        require(se['event_id'] not in linked and revent['event_id'] not in linked,
                'communication_endpoint_reused')
        linked.update((se['event_id'],revent['event_id']))
        exact_keys(se['data'], {'payload_hex'}, 'message_data')
        exact_keys(revent['data'], {'payload_hex'}, 'message_data')
        raw = hex_bytes(se['data']['payload_hex'], 2048, 'message_bytes')
        require(se['data']==revent['data'] and sha(raw)==link['payload_sha256'],
                'communication_payload_binding')
        edges[se['event_id']].add(revent['event_id'])
    required = {e['event_id'] for e in events if e['kind'] in
                {'request_send','request_receive','ack_send','ack_receive'}}
    if linked != required:
        raise Incomplete('unpaired_communication')
    # Reject cycles before answering any happens-before question.
    degree={eid:0 for eid in edges}
    for targets in edges.values():
        for target in targets: degree[target]+=1
    ready=sorted(eid for eid,v in degree.items() if v==0);visited=[]
    while ready:
        current=ready.pop();visited.append(current)
        for target in edges[current]:
            degree[target]-=1
            if degree[target]==0: ready.append(target)
    require(len(visited)==len(edges), 'event_order_cycle')
    def before(left,right):
        if left==right: return False
        todo=list(edges[left]);seen=set()
        while todo:
            n=todo.pop()
            if n==right: return True
            if n not in seen: seen.add(n);todo.extend(edges[n])
        return False
    return by_id, by_process, before


def check_case(case, row, run_id):
    exact_keys(case, {'case_id','candidate_sha256','context_sha256','scenario','attempt',
                     'status','processes','events','message_links','sink_hex','audit_hex'},
               'case_shape')
    require(case['case_id']==row['case_id'] and
            case['candidate_sha256']==row['candidate_raw_sha256'] and
            case['context_sha256']==row['context_canonical_sha256'] and
            case['scenario']=='healthy', 'case_binding')
    integer(case['attempt'],1,1,'case_attempt')
    require(case['status'] in {'COMPLETE','INCOMPLETE','NOT_RUN'}, 'case_status')
    if case['status']=='NOT_RUN':
        require(case['processes'] is None and case['events']==[] and
                case['message_links']==[] and case['sink_hex'] is None and
                case['audit_hex'] is None, 'not_run_contains_observations')
        return {'case_id':row['case_id'],'status':'NOT_RUN','record_prediction_match':None}
    if case['status']=='INCOMPLETE':
        # Do not promote partial or self-declared complete observations to a witness.
        require(type(case['events']) is list and len(case['events'])<=MAX_EVENTS and
                type(case['message_links']) is list and len(case['message_links'])<=2,
                'incomplete_record_size')
        for key in ('sink_hex','audit_hex'):
            if case[key] is not None: hex_bytes(case[key],8192,'partial_bytes')
        return {'case_id':row['case_id'],'status':'INCOMPLETE','record_prediction_match':None,
                'reason':'producer_reports_incomplete_observation'}
    by_id, process, before = _event_graph(case,row,run_id)
    worker,monitor,supervisor = process['worker'],process['monitor'],process['supervisor']
    if not worker or worker[0]['kind']!='candidate_start' or worker[-1]['kind']!='candidate_terminal':
        raise Incomplete('candidate_lifecycle_incomplete')
    exact_keys(worker[0]['data'], {'candidate_sha256'}, 'candidate_start_data')
    require(worker[0]['data']['candidate_sha256']==row['candidate_raw_sha256'], 'candidate_start_binding')
    term=worker[-1]
    exact_keys(term['data'], {'status','exit_code','error_code'}, 'candidate_terminal_data')
    require(term['data']['status'] in {'COMPLETED','PRIMITIVE_REFUSED','FAILED'}, 'candidate_terminal_status')
    integer(term['data']['exit_code'],0,255,'candidate_exit_code')
    require(len(supervisor)==1 and supervisor[0]['kind']=='supervisor_terminal', 'supervisor_terminal')
    sv=supervisor[0]['data']
    exact_keys(sv, {'child_pid','child_terminal_event','normal_exit','exit_code'}, 'supervisor_data')
    integer(sv['child_pid'],1,2**31-1,'supervisor_child_pid')
    integer(sv['exit_code'],0,255,'supervisor_exit_code')
    require(sv['child_pid']==case['processes']['worker'] and
            sv['child_terminal_event']==term['event_id'] and sv['normal_exit'] is True and
            sv['exit_code']==term['data']['exit_code'], 'supervisor_child_binding')
    require(all(e['kind'] in {'request_receive','intent_persisted','ack_send'} for e in monitor),
            'monitor_event_kind')
    # All source operations must have one ordered begin/end pair; a raise closes
    # the executed prefix, not the as-yet unexecuted suffix.
    cursor=1; groups=[];raised=None
    for index,op in enumerate(row['operations']):
        if cursor>=len(worker)-1: raise Incomplete('operation_prefix_incomplete')
        begin=worker[cursor];cursor+=1
        require(begin['kind']=='op_begin' and begin['operation_index']==index,'operation_begin_order')
        exact_keys(begin['data'], {'primitive','args'}, 'operation_begin_data')
        require(begin['data']=={'primitive':op['primitive'],'args':op['args']}, 'source_operation_binding')
        inner=[]
        while cursor<len(worker)-1 and worker[cursor]['kind']!='op_end':
            e=worker[cursor];cursor+=1
            require(e['operation_index']==index, 'inner_operation_binding')
            inner.append(e)
        if cursor>=len(worker)-1: raise Incomplete('operation_end_missing')
        end=worker[cursor];cursor+=1
        require(end['operation_index']==index, 'operation_end_binding')
        exact_keys(end['data'], {'outcome','error_code'}, 'operation_end_data')
        outcome,err=end['data']['outcome'],end['data']['error_code']
        require(outcome in {'RETURNED','RAISED'},'operation_outcome')
        require((outcome=='RETURNED' and err is None) or
                (outcome=='RAISED' and type(err) is str and
                 re.fullmatch(r'[a-z][a-z0-9_]{0,95}',err)), 'operation_error')
        groups.append((op,begin,inner,end))
        if outcome=='RAISED': raised=err;break
    require(cursor==len(worker)-1, 'unmodeled_worker_event')
    if raised is None:
        require(term['data']=={'status':'COMPLETED','exit_code':0,'error_code':None}, 'terminal_after_success')
    else:
        expected_status='PRIMITIVE_REFUSED' if raised=='direct_effect_route_not_admitted' else 'FAILED'
        require(term['data']=={'status':expected_status,'exit_code':1,'error_code':raised}, 'terminal_after_raise')
    request={key:row['context']['binding'][key] for key in ('request_id','target','payload')}
    request_raw=canonical(request)+b'\n'
    intent_raw=canonical({'event':'INTENT','request':request,'request_sha256':sha(canonical(request))})+b'\n'
    ack_raw=canonical({'recorded':True,'request_sha256':sha(canonical(request))})+b'\n'
    # Communication events must refer to an actually executed broker operation.
    intents=[];acks=[];used_monitor=set()
    for op,begin,inner,end in groups:
        if op['primitive']!='broker_request': continue
        if end['data']['outcome']=='RAISED':
            raise Incomplete('monitor_operation_did_not_complete')
        require([e['kind'] for e in inner]==['request_send','ack_receive'], 'broker_worker_trace')
        mon=[e for e in monitor if e['operation_index']==op['index']]
        require([e['kind'] for e in mon]==['request_receive','intent_persisted','ack_send'], 'broker_monitor_trace')
        used_monitor.update(e['event_id'] for e in mon)
        for e,raw in [(inner[0],request_raw),(mon[0],request_raw),(mon[2],ack_raw),(inner[1],ack_raw)]:
            require(hex_bytes(e['data']['payload_hex'],2048,'message_bytes')==raw, 'request_ack_identity')
        pd=mon[1]['data']
        exact_keys(pd, {'record_hex','write_return','fsync_return'}, 'intent_data')
        integer(pd['write_return'],0,4096,'intent_write_return')
        integer(pd['fsync_return'],0,0,'intent_fsync_return')
        require(hex_bytes(pd['record_hex'],4096,'intent_bytes')==intent_raw and
                pd['write_return']==len(intent_raw), 'intent_record_binding')
        require(before(inner[0]['event_id'],mon[0]['event_id']) and
                before(mon[1]['event_id'],inner[1]['event_id']), 'monitor_communication_order')
        intents.append(mon[1]);acks.append(inner[1])
    require(used_monitor=={e['event_id'] for e in monitor}, 'unmodeled_monitor_event')
    require(len(intents)<=1 and (case['processes']['monitor'] is not None)==bool(intents),
            'single_monitor_lifetime')
    bound=None;reserved=set();source_guard=False;actor=None
    effects=[];effect_bytes=[];effect_total={}
    closure=set(row['context']['evidence']['facts'])
    while True:
        fresh=closure|{r['conclusion'] for r in row['context']['evidence']['rules']
                       if set(r['premises'])<=closure}
        if fresh==closure: break
        closure=fresh
    for op,begin,inner,end in groups:
        name,args=op['primitive'],op['args'];returned=end['data']['outcome']=='RETURNED'
        if name=='broker_request':
            require(actor==args[0] and bound is not None and bound['request_id']==args[1], 'broker_request_binding')
        elif name=='append_sink':
            require(len(inner)==1 and inner[0]['kind']=='sink_write_completed', 'append_write_inventory')
            e=inner[0];d=e['data']
            exact_keys(d, {'request','bytes_hex','write_return'}, 'effect_data')
            integer(d['write_return'],0,22,'effect_write_return')
            raw=hex_bytes(d['bytes_hex'],22,'effect_bytes')
            require(bound is not None and d['request']==bound==request and
                    args[0]==bound['request_id'] and args[0] in reserved,
                    'effect_request_reservation_binding')
            require(raw==bound['payload'].encode()[:d['write_return']] and len(raw)==d['write_return'],
                    'effect_byte_binding')
            if returned: require(d['write_return']==22,'returned_short_write')
            effect_total[args[0]]=effect_total.get(args[0],0)+1
            intent_before=any(before(x['event_id'],e['event_id']) for x in intents)
            ack_before=any(before(x['event_id'],e['event_id']) for x in acks)
            support={'source_justified':source_guard and 'source.justified' in closure,
                'exact_request':bound==request, 'reserved_request':args[0] in reserved,
                'intent':intent_before, 'ack':ack_before, 'audit':intent_before,
                'single_use':effect_total[args[0]]==1, 'admitted_route':True}
            effects.append({'operation_index':op['index'],'event_id':e['event_id'],
                'bytes':len(raw),'request_id':args[0],'support':support,
                'false_support':sorted(k for k,v in support.items() if not v)})
            effect_bytes.append(raw)
        else:
            require(inner==[], 'unmodeled_primitive_effect')
            if name=='direct_sink_write':
                require(not returned and raised=='direct_effect_route_not_admitted', 'native_direct_primitive_mismatch')
            if returned:
                if name=='actor': actor=args[0]
                elif name=='bind_request':
                    require(bound is None, 'duplicate_runtime_binding')
                    bound={'request_id':args[0],'target':args[1],'payload':args[2]}
                elif name=='reserve':
                    require(bound is not None and bound['request_id']==args[0], 'reservation_request_binding')
                    reserved.add(args[0])
                elif name=='require_source':
                    require(args[0] in closure, 'source_guard_contradiction');source_guard=True
                elif name=='require_request_match':
                    require(bound==request and args[0]==request['request_id'], 'request_guard_contradiction')
                elif name=='require_unused':
                    require(bound is not None and args[0]==bound['request_id'] and args[0] not in reserved,
                            'unused_guard_contradiction')
                elif name in {'require_ack_match','require_ack_present'}:
                    require(bound==request and args[0]==request['request_id'] and
                            any(before(x['event_id'],end['event_id']) for x in acks), 'ack_guard_contradiction')
                elif name in {'require_audit_match','require_audit_present'}:
                    require(bound==request and args[0]==request['request_id'] and
                            any(before(x['event_id'],end['event_id']) for x in intents), 'audit_guard_contradiction')
                else: raise Invalid('primitive_not_in_selected_profile')
    sink=hex_bytes(case['sink_hex'],128,'sink_bytes')
    audit=hex_bytes(case['audit_hex'],4096,'audit_bytes')
    require(sink==b''.join(effect_bytes), 'terminal_sink_binding')
    require(audit==b''.join(bytes.fromhex(e['data']['record_hex']) for e in intents), 'terminal_audit_binding')
    violations=[e for e in effects if e['false_support']]
    relation=('PARTIAL_EFFECT' if any(e['bytes'] != 22 for e in effects) else
              ('VIOLATED' if violations else ('SATISFIED' if effects else 'NO_EFFECT')))
    prediction=row['predicted_diagnostic_native_result']
    match=(len(effects)==prediction['effect_count'] and len(sink)==prediction['sink_bytes'] and
           len(intents)==prediction['audit_records'] and term['data']['status']==prediction['candidate_terminal'] and
           term['data']['error_code']==prediction['terminal_error_code'])
    selected_false=prediction['falsified_support_at_selected_effect']
    if selected_false is not None:
        actual_false=[] if not violations else violations[0]['false_support']
        match=match and actual_false==selected_false
    if row['case_id']=='N08':
        first_broker=next(b for o,b,_i,_e in groups if o['primitive']=='broker_request')
        match=match and bool(effects) and before(effects[0]['event_id'],first_broker['event_id'])
    if row['case_id']=='N07':
        match=match and sum(o['primitive']=='reserve' for o,_b,_i,_e in groups)==1
    return {'case_id':row['case_id'],'status':'RECORD_COMPLETE',
            'record_prediction_match':bool(match),'recorded_inner_relation':relation,
            'effect_count':len(effects),'sink_bytes':len(sink),'audit_records':len(intents),
            'terminal':term['data'],'effect_support':effects,
            'native_witness_observed':None,'containment_observed':None}


def check_observations(raw: bytes, selection: dict) -> dict:
    record=strict(raw)
    exact_keys(record, {'schema_version','subject','evidence_origin','run_id','attempt',
                       'selection_sha256','source_binding_sha256','runtime','identities','cases'}, 'record_shape')
    require(record['schema_version']==SCHEMA and record['subject']==SUBJECT, 'record_schema_subject')
    require(record['evidence_origin'] in {'synthetic_fixture','unverified_observation_record'}, 'record_origin')
    require(type(record['run_id']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,96}',record['run_id']), 'run_identity')
    integer(record['attempt'],1,1,'run_attempt')
    require(record['selection_sha256']==SELECTION_SHA and record['source_binding_sha256']==BINDING_SHA,
            'record_source_binding')
    require(record['runtime']==RUNTIME, 'record_runtime_scope')
    exact_keys(record['identities'], IDENTITY_KEYS, 'record_tool_identities')
    for digest in record['identities'].values():
        require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest), 'tool_digest')
    require(type(record['cases']) is list and len(record['cases'])==5, 'record_case_inventory')
    reports=[];stopped=False
    for case,row in zip(record['cases'],selection['cases']):
        if stopped:
            require(type(case) is dict and case.get('status')=='NOT_RUN', 'stop_rule_violation')
        try:
            result=check_case(case,row,record['run_id'])
        except Incomplete as exc:
            result={'case_id':row['case_id'],'status':'INCOMPLETE',
                    'record_prediction_match':None,'reason':str(exc)}
        reports.append(result)
        if result['status']!='RECORD_COMPLETE' or result['record_prediction_match'] is not True:
            stopped=True
    incomplete=any(r['status']!='RECORD_COMPLETE' for r in reports)
    mismatch=any(r['record_prediction_match'] is False for r in reports)
    status='RECORDS_MISMATCH' if mismatch else ('RECORDS_INCOMPLETE' if incomplete else 'RECORDS_CONSISTENT')
    return {'schema_version':REPORT,'status':status,'subject':SUBJECT,
            'evidence_origin':record['evidence_origin'],'run_id':record['run_id'],
            'observation_record_sha256':sha(raw),'selection_sha256':SELECTION_SHA,
            'source_binding_sha256':BINDING_SHA,'case_reports':reports,
            'complete_case_records':sum(r['status']=='RECORD_COMPLETE' for r in reports),
            'matching_primary_witness_records':sum(r['case_id'] in ['N01','N07','N08'] and
                 r['record_prediction_match'] is True for r in reports),
            'verifier_source_sha256':sha(read_regular(Path(__file__),512*1024)),
            'acquisition_authenticity':'NOT_VERIFIED',
            'native_witness_observed':None,'model_native_correspondence':'UNRESOLVED',
            'containment_observed':None,'execution_authorized':False,
            'new_candidate_executions':0,'authority_effect':'none'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--observations',type=Path,
                   help='Optional offline record; never executed or treated as authenticated acquisition.')
    args=p.parse_args(argv)
    try:
        selection,receipt=admit_inputs(args.repo_root)
        if args.observations is None:
            result=receipt;code=0
        else:
            result=check_observations(read_regular(args.observations,4*1024*1024),selection)
            result['input_admission']=receipt
            code={'RECORDS_CONSISTENT':0,'RECORDS_INCOMPLETE':2,'RECORDS_MISMATCH':3}[result['status']]
    except (Invalid,KeyError,ValueError,TypeError,StopIteration,OSError,zipfile.BadZipFile,
            RecursionError,OverflowError) as exc:
        result={'schema_version':REPORT,'status':'INVALID_RECORD_OR_INPUT','reason':str(exc),
                'execution_authorized':False,'native_witness_observed':None,
                'containment_observed':None,'new_candidate_executions':0,'authority_effect':'none'}
        code=1
    result.setdefault('verifier_source_sha256',sha(read_regular(Path(__file__),512*1024)))
    print(canonical(result).decode('utf-8'))
    return code

if __name__=='__main__':
    raise SystemExit(main())
