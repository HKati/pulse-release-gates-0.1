#!/usr/bin/env python3
"""Offline W1 input/trace controls. Fixtures are synthetic, never native runs."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/check_paradox_w1_records_v0.py'
FIXTURE = ROOT / 'tests/fixtures/paradox_w1_records_v0/synthetic_observations.json'
SELF = 'tests/test_paradox_w1_records_v0.py'
_spec = importlib.util.spec_from_file_location('w1_record_checker_under_test', TOOL)
assert _spec and _spec.loader
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


@pytest.fixture(scope='module')
def admitted():
    return C.admit_inputs(ROOT)


@pytest.fixture
def record():
    return json.loads(FIXTURE.read_bytes())


def evaluate(record, admitted):
    return C.check_observations(C.canonical(record), admitted[0])


def not_run(case):
    case.update(status='NOT_RUN',processes=None,events=[],message_links=[],sink_hex=None,audit_hex=None)


def stop_after(record,index):
    for c in record['cases'][index+1:]: not_run(c)


def event(case,kind,n=0):
    return [e for e in case['events'] if e['kind']==kind][n]


def reject(record,admitted):
    try:
        result=evaluate(record,admitted)
    except C.Invalid:
        return
    assert result['status'] != 'RECORDS_CONSISTENT'
    assert result['native_witness_observed'] is None
    assert result['execution_authorized'] is False


def renumber(case):
    for role in case['processes']:
        seq=0
        for e in case['events']:
            if e['process']==role:
                seq+=1;e['sequence']=seq


def test_frozen_inputs_and_original_archive_admitted(admitted):
    selection,r=admitted
    assert r['status']=='PREPARATION_VALID'
    assert (r['archive_manifest_entries_verified'],r['source_files_bound'],
            r['selected_cases_bound'],r['selected_archived_members_bound'])==(471,6,5,38)
    assert r['selection_sha256']==C.SELECTION_SHA
    assert r['verifier_source_sha256']==hashlib.sha256(TOOL.read_bytes()).hexdigest()
    assert selection['case_order']==['P00','N01','N07','N08','N02']
    assert r['experiment_execution_status']=='NOT_RUN'
    assert r['new_candidate_executions']==0 and r['execution_authorized'] is False


def test_synthetic_records_conform_but_cannot_establish_native_observation(record,admitted):
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_CONSISTENT'
    assert r['complete_case_records']==5 and r['matching_primary_witness_records']==3
    assert [x['recorded_inner_relation'] for x in r['case_reports']]==[
        'SATISFIED','VIOLATED','VIOLATED','VIOLATED','NO_EFFECT']
    assert r['evidence_origin']=='synthetic_fixture'
    assert r['native_witness_observed'] is None
    assert r['model_native_correspondence']=='UNRESOLVED'
    assert r['containment_observed'] is None and r['execution_authorized'] is False
    assert r['acquisition_authenticity']=='NOT_VERIFIED' and r['authority_effect']=='none'


def test_identical_terminal_bytes_do_not_erase_n08_prefix(record,admitted):
    assert record['cases'][0]['sink_hex']==record['cases'][3]['sink_hex']
    assert record['cases'][0]['audit_hex']==record['cases'][3]['audit_hex']
    r=evaluate(record,admitted)['case_reports']
    assert r[0]['effect_support'][0]['false_support']==[]
    assert r[3]['effect_support'][0]['false_support']==['ack','audit','intent']


def test_n07_two_observed_write_events_not_a_44_byte_summary(record,admitted):
    r=evaluate(record,admitted)['case_reports'][2]
    assert [e['bytes'] for e in r['effect_support']]==[22,22]
    assert r['effect_support'][0]['false_support']==[]
    assert r['effect_support'][1]['false_support']==['single_use']


def test_n02_remains_refusal_not_a_native_violation(record,admitted):
    r=evaluate(record,admitted)['case_reports'][4]
    assert r['recorded_inner_relation']=='NO_EFFECT' and r['effect_count']==0
    assert r['terminal']['error_code']=='direct_effect_route_not_admitted'
    assert r['native_witness_observed'] is None


def test_unverified_record_origin_does_not_authenticate_events(record,admitted):
    record['evidence_origin']='unverified_observation_record'
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_CONSISTENT'
    assert r['acquisition_authenticity']=='NOT_VERIFIED'
    assert r['native_witness_observed'] is None and r['containment_observed'] is None


def test_deterministic_report_for_same_raw_bytes(record,admitted):
    raw=C.canonical(record)
    assert C.canonical(C.check_observations(raw,admitted[0]))==C.canonical(C.check_observations(raw,admitted[0]))


def test_collector_list_order_is_not_used_as_cross_process_time(record,admitted):
    before=evaluate(record,admitted)
    for case in record['cases']: case['events'].reverse()
    after=evaluate(record,admitted)
    assert after['status']=='RECORDS_CONSISTENT'
    assert after['case_reports']==before['case_reports']


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',
                               b'{"x":1e9999}',b'{"x":"\\ud800"}',b'\xef\xbb\xbf{}',b'\xff'])
def test_strict_json_rejects_duplicate_nonfinite_and_invalid_text(raw):
    with pytest.raises(C.Invalid): C.strict(raw)


def test_deep_json_rejected():
    with pytest.raises(C.Invalid): C.strict(b'['*80+b'0'+b']'*80)


@pytest.mark.parametrize('key,value',[
    ('schema_version','wrong'),('subject','normal_admission'),('evidence_origin','native_verified'),
    ('selection_sha256','0'*64),('source_binding_sha256','0'*64),('attempt',True),('attempt',2),
    ('run_id',''),('run_id','different/run'),('cases',[]),('identities',{}),('runtime',{}),
])
def test_header_mutations_fail_closed(record,admitted,key,value):
    record[key]=value
    with pytest.raises(C.Invalid): evaluate(record,admitted)


@pytest.mark.parametrize('key',['native_witness_observed','containment_observed','execution_authorized','safety_pass'])
def test_self_certifying_header_field_not_accepted(record,admitted,key):
    record[key]=True
    with pytest.raises(C.Invalid,match='record_shape'): evaluate(record,admitted)


@pytest.mark.parametrize('key,value',[
    ('case_id','N01'),('candidate_sha256','0'*64),('context_sha256','0'*64),
    ('scenario','wrong_ack'),('attempt',True),('attempt',2),('status','PASS')])
def test_case_binding_mutations(record,admitted,key,value):
    record['cases'][0][key]=value
    with pytest.raises(C.Invalid): evaluate(record,admitted)


def test_duplicate_or_reordered_cases(record,admitted):
    record['cases'][1]=copy.deepcopy(record['cases'][0])
    with pytest.raises(C.Invalid,match='case_binding'): evaluate(record,admitted)


@pytest.mark.parametrize('key,value',[
    ('case_id','N01'),('run_id','other-run'),('attempt',True),('attempt',2),
    ('sequence',True),('sequence',0),('operation_index',True),('kind','gate_allow'),
    ('process','unknown')])
def test_event_binding_and_type_mutations(record,admitted,key,value):
    event(record['cases'][0],'op_begin')[key]=value
    reject(record,admitted)


def test_duplicate_event_identity(record,admitted):
    c=record['cases'][0];c['events'][1]['event_id']=c['events'][0]['event_id']
    with pytest.raises(C.Invalid,match='duplicate_event_id'): evaluate(record,admitted)


def test_sequence_gap_incomplete_not_vacuous_success(record,admitted):
    c=record['cases'][0];event(c,'op_begin')['sequence']+=100
    stop_after(record,0)
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_INCOMPLETE' and r['complete_case_records']==0


@pytest.mark.parametrize('which',['worker','monitor','supervisor'])
def test_pid_boolean_is_not_integer_identity(record,admitted,which):
    record['cases'][0]['processes'][which]=True
    with pytest.raises(C.Invalid): evaluate(record,admitted)


def test_pid_aliases_not_allowed(record,admitted):
    c=record['cases'][0];c['processes']['monitor']=c['processes']['worker']
    with pytest.raises(C.Invalid,match='process_identity_collision'):evaluate(record,admitted)


def test_cross_case_splice_cannot_reuse_p00_messages_for_n08(record,admitted):
    record['cases'][3]['events']=copy.deepcopy(record['cases'][0]['events'])
    reject(record,admitted)


def test_source_operation_argument_substitution(record,admitted):
    event(record['cases'][0],'op_begin')['data']['args']=['helper']
    with pytest.raises(C.Invalid,match='source_operation_binding'):evaluate(record,admitted)


def test_binding_operation_cannot_move_to_end(record,admitted):
    c=record['cases'][0]
    begins=[e for e in c['events'] if e['kind']=='op_begin']
    begins[1]['data'],begins[-1]['data']=begins[-1]['data'],begins[1]['data']
    with pytest.raises(C.Invalid,match='source_operation_binding'):evaluate(record,admitted)


@pytest.mark.parametrize('kind',['op_begin','op_end','sink_write_completed','intent_persisted',
                               'request_receive','ack_receive','candidate_terminal','supervisor_terminal'])
def test_missing_required_event_cannot_pass(record,admitted,kind):
    c=record['cases'][0];c['events'].remove(event(c,kind));renumber(c)
    stop_after(record,0);reject(record,admitted)


def test_missing_message_edges_not_repaired_with_collection_order(record,admitted):
    c=record['cases'][0];c['message_links']=[]
    stop_after(record,0)
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_INCOMPLETE'
    assert r['case_reports'][0]['reason']=='unpaired_communication'


@pytest.mark.parametrize('field,value',[('channel','time'),('send','missing'),
                                      ('receive','missing'),('payload_sha256','0'*64)])
def test_message_link_mutations(record,admitted,field,value):
    record['cases'][0]['message_links'][0][field]=value
    with pytest.raises(C.Invalid):evaluate(record,admitted)


def test_reverse_message_link_rejected(record,admitted):
    l=record['cases'][0]['message_links'][0];l['send'],l['receive']=l['receive'],l['send']
    with pytest.raises(C.Invalid,match='communication_direction'):evaluate(record,admitted)


def test_cycle_in_observed_order_rejected(record,admitted):
    c=record['cases'][0]
    send=event(c,'request_send');recv=event(c,'ack_receive')
    send['sequence'],recv['sequence']=recv['sequence'],send['sequence']
    with pytest.raises(C.Invalid,match='event_order_cycle'):evaluate(record,admitted)


def test_unrelated_ack_cannot_be_bound_by_rehashing_link(record,admitted):
    c=record['cases'][0];raw=C.canonical({'recorded':True,'request_sha256':'0'*64})+b'\n'
    for kind in ('ack_send','ack_receive'):event(c,kind)['data']['payload_hex']=raw.hex()
    next(l for l in c['message_links'] if l['channel']=='ack')['payload_sha256']=C.sha(raw)
    with pytest.raises(C.Invalid,match='request_ack_identity'):evaluate(record,admitted)


def test_audit_for_other_request_cannot_support_effect(record,admitted):
    c=record['cases'][0];e=event(c,'intent_persisted')
    value=json.loads(bytes.fromhex(e['data']['record_hex']));value['request']['request_id']='request-1'
    raw=C.canonical(value)+b'\n';e['data'].update(record_hex=raw.hex(),write_return=len(raw));c['audit_hex']=raw.hex()
    with pytest.raises(C.Invalid,match='intent_record_binding'):evaluate(record,admitted)


@pytest.mark.parametrize('field,value',[('write_return',True),('fsync_return',False),('fsync_return',1)])
def test_intent_return_types_and_persistence_checked(record,admitted,field,value):
    event(record['cases'][0],'intent_persisted')['data'][field]=value
    with pytest.raises(C.Invalid):evaluate(record,admitted)


@pytest.mark.parametrize('field,value',[('write_return',True),('write_return',44),('bytes_hex','zz')])
def test_effect_return_types_and_size_checked(record,admitted,field,value):
    event(record['cases'][0],'sink_write_completed')['data'][field]=value
    with pytest.raises(C.Invalid):evaluate(record,admitted)


def test_effect_actual_request_must_match_reservation(record,admitted):
    event(record['cases'][0],'sink_write_completed')['data']['request']['request_id']='request-1'
    with pytest.raises(C.Invalid,match='effect_request_reservation_binding'):evaluate(record,admitted)


def test_n07_combined_terminal_bytes_cannot_replace_two_write_completions(record,admitted):
    c=record['cases'][2];writes=[e for e in c['events'] if e['kind']=='sink_write_completed']
    c['events'].remove(writes[1]);writes[0]['data']['write_return']=44;renumber(c)
    stop_after(record,2);reject(record,admitted)


@pytest.mark.parametrize('field',['sink_hex','audit_hex'])
def test_terminal_file_bytes_must_equal_recorded_operations(record,admitted,field):
    record['cases'][0][field]+='00'
    with pytest.raises(C.Invalid,match='terminal_'):evaluate(record,admitted)


def test_late_support_cannot_be_relabelled_as_prior_support(record,admitted):
    c=record['cases'][3];e=event(c,'sink_write_completed')
    e['data']['support']={'intent':True,'ack':True,'audit':True}
    with pytest.raises(C.Invalid,match='effect_data'):evaluate(record,admitted)


def test_declared_timestamps_are_not_accepted_as_order_edges(record,admitted):
    event(record['cases'][0],'sink_write_completed')['timestamp_ns']=0
    with pytest.raises(C.Invalid,match='event_shape'):evaluate(record,admitted)


def test_n02_fake_native_completion_rejected(record,admitted):
    c=record['cases'][4];end=event(c,'op_end',len([e for e in c['events'] if e['kind']=='op_end'])-1)
    end['data']={'outcome':'RETURNED','error_code':None}
    reject(record,admitted)


@pytest.mark.parametrize('field,value',[('child_pid',True),('child_pid',99999),
    ('child_terminal_event','missing'),('normal_exit',1),('normal_exit',False),('exit_code',True),('exit_code',42)])
def test_supervisor_terminal_must_bind_actual_child_record(record,admitted,field,value):
    event(record['cases'][0],'supervisor_terminal')['data'][field]=value
    with pytest.raises(C.Invalid):evaluate(record,admitted)


def test_incomplete_attempt_and_not_run_suffix_preserved(record,admitted):
    record['cases'][1]['status']='INCOMPLETE';stop_after(record,1)
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_INCOMPLETE' and r['complete_case_records']==1
    assert [x['status'] for x in r['case_reports']][2:]==['NOT_RUN']*3
    assert r['matching_primary_witness_records']==0


def test_continuing_after_incomplete_attempt_rejected(record,admitted):
    record['cases'][0]['status']='INCOMPLETE'
    with pytest.raises(C.Invalid,match='stop_rule_violation'):evaluate(record,admitted)


def test_not_run_cannot_carry_historical_observation(record,admitted):
    record['cases'][0]['status']='NOT_RUN';stop_after(record,0)
    with pytest.raises(C.Invalid,match='not_run_contains_observations'):evaluate(record,admitted)


def test_all_not_run_not_classified_as_success(record,admitted):
    for c in record['cases']:not_run(c)
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_INCOMPLETE' and r['complete_case_records']==0


def test_partial_write_retained_as_mismatch_not_safety_pass(record,admitted):
    c=record['cases'][0];write=event(c,'sink_write_completed')
    raw=bytes.fromhex(write['data']['bytes_hex'])[:7]
    write['data'].update(bytes_hex=raw.hex(),write_return=7);c['sink_hex']=raw.hex()
    ends=[e for e in c['events'] if e['kind']=='op_end'];ends[-1]['data']={'outcome':'RAISED','error_code':'runtime_sink_short_write'}
    event(c,'candidate_terminal')['data']={'status':'FAILED','exit_code':1,'error_code':'runtime_sink_short_write'}
    event(c,'supervisor_terminal')['data']['exit_code']=1
    stop_after(record,0)
    r=evaluate(record,admitted)
    assert r['status']=='RECORDS_MISMATCH'
    assert r['case_reports'][0]['recorded_inner_relation']=='PARTIAL_EFFECT'
    assert r['case_reports'][0]['sink_bytes']==7
    assert r['case_reports'][0]['record_prediction_match'] is False


@pytest.fixture
def input_copy(tmp_path,admitted):
    root=tmp_path/'repo';exp=root/'docs/experiments';exp.mkdir(parents=True)
    for name in ('CONTRACT_v0.md','SELECTION_v0.json','SOURCE_BINDING_v0.json'):
        rel='docs/experiments/PD_SM_02_W1_'+name
        shutil.copyfile(ROOT/rel,root/rel)
    binding=json.loads((exp/'PD_SM_02_W1_SOURCE_BINDING_v0.json').read_bytes())
    for rel in [binding['archive']['repository_path']]+[x['repository_path'] for x in binding['source_files']]:
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
    return root


@pytest.mark.parametrize('name,reason',[
    ('SELECTION_v0.json','selection_identity'),('SOURCE_BINDING_v0.json','source_binding_identity'),
    ('CONTRACT_v0.md','contract_identity')])
def test_frozen_planning_file_cannot_be_silently_replaced(input_copy,name,reason):
    p=input_copy/'docs/experiments'/('PD_SM_02_W1_'+name);p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(C.Invalid,match=reason):C.admit_inputs(input_copy)


@pytest.mark.parametrize('name',list(C.BLOBS))
def test_current_program_data_bytes_must_match_historical_snapshot(input_copy,name):
    p=input_copy/'examples/paradox_preexecution_impact_v0'/name
    p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(C.Invalid,match='checkout_source_binding'):C.admit_inputs(input_copy)


def test_archive_identity_checked_before_decompression(input_copy,monkeypatch):
    p=input_copy/'docs/evidence/PD_SM_02_SCRATCH_PILOT_20261027/PD_SM_02_SCRATCH_PILOT_20261027.zip'
    raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
    monkeypatch.setattr(C.zipfile,'ZipFile',lambda *a,**kw:pytest.fail('must not open mutated carrier'))
    with pytest.raises(C.Invalid,match='archive_identity'):C.admit_inputs(input_copy)


def test_missing_archive_never_manufactures_input_receipt(input_copy):
    (input_copy/'docs/evidence/PD_SM_02_SCRATCH_PILOT_20261027/PD_SM_02_SCRATCH_PILOT_20261027.zip').unlink()
    with pytest.raises(OSError):C.admit_inputs(input_copy)


def test_terminal_input_symlink_rejected(tmp_path):
    target=tmp_path/'target';target.write_bytes(b'{}')
    link=tmp_path/'link'
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip('symlink creation unavailable in this test environment')
    with pytest.raises(C.Invalid,match='input_symlink'):C.read_regular(link,100)


def test_oversized_json_rejected_before_parse():
    with pytest.raises(C.Invalid,match='json_size'):C.strict(b' '* (4*1024*1024+1))


def test_cli_no_native_effect_no_repo_mutation(tmp_path):
    output=tmp_path/'stdout.json'
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in ROOT.rglob('*') if p.is_file()}
    result=subprocess.run([sys.executable,'-I','-S','-B',str(TOOL),'--repo-root',str(ROOT),
                           '--observations',str(FIXTURE)],capture_output=True,timeout=20,check=False)
    assert result.returncode==0,result.stderr.decode()
    r=json.loads(result.stdout)
    assert r['status']=='RECORDS_CONSISTENT'
    assert r['new_candidate_executions']==0 and r['execution_authorized'] is False
    assert not output.exists() and result.stderr==b''
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in ROOT.rglob('*') if p.is_file()}
    assert after==before
    assert r['verifier_source_sha256']==hashlib.sha256(TOOL.read_bytes()).hexdigest()


def test_cli_missing_record_structured_error(tmp_path):
    result=subprocess.run([sys.executable,'-I','-S','-B',str(TOOL),'--repo-root',str(ROOT),
         '--observations',str(tmp_path/'absent.json')],capture_output=True,timeout=20,check=False)
    assert result.returncode==1 and result.stderr==b''
    assert json.loads(result.stdout)['status']=='INVALID_RECORD_OR_INPUT'


def test_cli_incomplete_is_nonzero(record,admitted,tmp_path):
    for c in record['cases']:not_run(c)
    path=tmp_path/'incomplete.json';path.write_bytes(C.canonical(record))
    result=subprocess.run([sys.executable,'-I','-S','-B',str(TOOL),'--repo-root',str(ROOT),
         '--observations',str(path)],capture_output=True,timeout=20,check=False)
    assert result.returncode==2 and json.loads(result.stdout)['status']=='RECORDS_INCOMPLETE'


def test_no_project_runtime_import_or_execution_in_checker():
    tree=ast.parse(TOOL.read_text(),feature_version=(3,11))
    modules=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):modules.update(a.name.split('.')[0] for a in node.names)
        if isinstance(node,ast.ImportFrom):modules.add((node.module or '').split('.')[0])
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            assert node.func.id not in {'exec','eval','compile','__import__'}
    assert not modules & {'subprocess','socket','ctypes','importlib','source_model','check_impact','run_local'}
    for text in ('os.fork(', 'os.system(', 'extractall(', 'write_bytes(', 'write_text('):
        assert text not in TOOL.read_text()


def test_registered_once_in_both_manifests_and_expected_counts():
    for name,count in [('tools-tests.list',173),('pytest-tests.list',29)]:
        entries=[s.split('#',1)[0].strip() for s in (ROOT/'ci'/name).read_text().splitlines()]
        entries=[s for s in entries if s]
        assert len(entries)==len(set(entries))==count
        assert entries.count(SELF)==1
        assert entries.count('tests/test_q3_external_postflight_v0.py')==1
        assert entries.count('tests/test_check_pages_source_binding_v0.py')==1


def test_all_existing_inventory_count_consumers_synchronized():
    consumers=['test_q2_reference_acquisition_v0.py','test_q2_hosted_intake_workflow_v0.py',
        'test_pulsemech_compute_bounded_execution_v0.py',
        'test_pulsemech_compute_current_run_export_candidate_workflow_v0.py',
        'test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py',
        'test_q2_release_host_tokenizer_v0.py','test_q2_release_host_tokenizer_workflow_v0.py',
        'test_q2_release_host_worker_v0.py','test_q3_native_capture_workflow_v0.py']
    for name in consumers:
        text=(ROOT/'tests'/name).read_text()
        assert len(re.findall(r'==\s*173\b',text))==1,name
        assert not re.search(r'==\s*172\b',text),name
        ast.parse(text,feature_version=(3,11))
    for name in ('test_q2_release_host_tokenizer_workflow_v0.py','test_q2_release_host_worker_v0.py'):
        assert r'==\s*173\b' in (ROOT/'tests'/name).read_text()
    pages=(ROOT/'tests/test_check_pages_source_binding_v0.py').read_text()
    postflight=(ROOT/'tests/test_q3_external_postflight_v0.py').read_text()
    assert '("tools-tests.list",173)' in pages and '("pytest-tests.list",29)' in pages
    assert "('tools-tests.list',173)" in postflight and "('pytest-tests.list',29)" in postflight


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__]))
