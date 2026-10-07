"""Synthetic payload relations, unchanged real subprocess replay, fail-closed cases."""
import copy
import json
import shutil
import stat
import subprocess
import sys

import pytest

from test_q2_release_intake_v0 import (
    ROOT, TOOLS, IO, LOAD, PRODUCER, ADMISSION, synthetic_case, zipped, snapshot, run_case,
)


@pytest.mark.parametrize('consumer',['producer','admission'])
@pytest.mark.parametrize('positive',[False,True],ids=['verified-negative','synthetic-positive'])
def test_full_synthetic_payload_and_unchanged_replay(tmp_path,consumer,positive):
    case=synthetic_case(tmp_path/'case',positive)
    result=run_case(case,consumer)
    assert result['record_status']=='synthetic_fixture'
    assert result['input_valid'] is True and result['metric_pass'] is positive
    assert result['process_exit']==(0 if positive else 1)
    assert all(result['checks'].values()) and result['metrics']['groups_eligible']==(50 if positive else 49)
    assert result['metrics']['responses_total']==150 and result['current_inference_count']==0
    assert result['release_host_environment']=='not_observed' and result['production_gate_eligible'] is False
    assert case['raw']['summary.json']==(case['folder']/'summary.json').read_bytes()


@pytest.mark.parametrize('consumer',['producer','admission'])
@pytest.mark.parametrize('attack',[
    'worker','source-selection','model','missing-model','runtime','runtime-mode','python',
    'link-target','link-as-file','extra-link','missing-link','extra-wrapper','missing-runtime',
    'configuration','runtime-configuration','launch','platform-claim','definition','copied-manifest-only',
])
def test_same_outer_request_cannot_hide_wrong_subject(tmp_path,consumer,attack):
    case=synthetic_case(tmp_path/'case')
    members=case['capsule']
    if attack=='worker':
        name='source/'+IO.WORKER;raw,mode=members[name];members[name]=(raw+b'\n',mode)
    elif attack=='source-selection':
        name='source/'+IO.SELECTION_PATH;raw,mode=members[name];members[name]=(raw+b' ',mode)
    elif attack=='model':members['model/model.safetensors']=(b'wrong-model',stat.S_IFREG|0o644)
    elif attack=='missing-model':del members['model/tokenizer.json']
    elif attack=='runtime':members['runtime/lib/python3.11/site-packages/synthetic.py']=(b'changed',stat.S_IFREG|0o644)
    elif attack=='runtime-mode':
        name='runtime/lib/python3.11/site-packages/synthetic.py';members[name]=(members[name][0],stat.S_IFREG|0o755)
    elif attack=='python':members['runtime/bin/python']=(b'wrong-interpreter',stat.S_IFREG|0o755)
    elif attack=='link-target':members['runtime/lib64']=(b'../lib',stat.S_IFLNK|0o777)
    elif attack=='link-as-file':members['runtime/lib64']=(b'lib',stat.S_IFREG|0o644)
    elif attack=='extra-link':members['runtime/unreviewed-link']=(b'lib',stat.S_IFLNK|0o777)
    elif attack=='missing-link':del members['runtime/lib64']
    elif attack=='extra-wrapper':members['wrapper.py']=(b'raise RuntimeError("PAYLOAD_MUST_NOT_RUN")',stat.S_IFREG|0o755)
    elif attack=='missing-runtime':del members['runtime/lib/python3.11/site-packages/synthetic.py']
    elif attack=='copied-manifest-only':members={'capsule.json':members['capsule.json']}
    else:
        doc=json.loads(members['capsule.json'][0])
        if attack=='configuration':doc['configuration']['effective_generation']['max_new_tokens']=64
        elif attack=='runtime-configuration':doc['configuration']['runtime']['threads']=2
        elif attack=='launch':doc['launch']['argv_template'].append('--unreviewed-wrapper')
        elif attack=='platform-claim':doc['platform_scope']['release_host_verification']='verified'
        elif attack=='definition':doc['definition_sha256']='f'*64
        members['capsule.json']=(IO.encode(doc),stat.S_IFREG|0o600)
        case['request']['release_subject']['capsule_manifest_sha256']=IO.digest(IO.encode(doc))
    zipped(case['folder']/'capsule.zip',members)
    case['request']['release_subject'].update(snapshot(case['folder']/'capsule.zip'))
    with pytest.raises(IO.IntakeError):run_case(case,consumer)


@pytest.mark.parametrize('consumer',['producer','admission'])
def test_manifest_repair_cannot_turn_wrong_bytes_into_identity(tmp_path,consumer):
    case=synthetic_case(tmp_path/'case')
    # The immutable capture expectation is kept; editing both capsule claims and
    # its externally bound archive digest still cannot change measured subject bytes.
    case['capsule']['model/model.safetensors']=(b'WRONG',stat.S_IFREG|0o644)
    zipped(case['folder']/'capsule.zip',case['capsule'])
    case['request']['release_subject'].update(snapshot(case['folder']/'capsule.zip'))
    with pytest.raises(IO.IntakeError,match='q2_subject_mismatch'):run_case(case,consumer)


def rebind_synthetic_capture(case):
    members=case['members']
    report=json.loads(members['capture.json'][0])
    report['evidence']=[{'path':k,'size':len(v[0]),'sha256':IO.digest(v[0])}
                        for k,v in sorted(members.items()) if k!='capture.json']
    members['capture.json']=(IO.encode(report),stat.S_IFREG|0o600)
    for name in case['profile']['capture_file_bindings']:
        data=members[name][0]
        case['profile']['capture_file_bindings'][name]={'sha256':IO.digest(data),'size_bytes':len(data)}
    case['profile']['capture_expanded_bytes']=sum(len(v[0]) for v in members.values())
    zipped(case['folder']/'capture.zip',members)
    case['profile']['capture_expectation'].update(snapshot(case['folder']/'capture.zip'))
    case['request']['capture_expectation']=copy.deepcopy(case['profile']['capture_expectation'])


@pytest.mark.parametrize('consumer',['producer','admission'])
def test_forged_pass_with_consistent_public_claims_fails_real_recomputation(tmp_path,consumer):
    case=synthetic_case(tmp_path/'case',False)
    for name in ('summary.json','reduction.json','summary-check.json','capture.json'):
        doc=json.loads(case['members'][name][0])
        if name=='summary.json':doc['pass']=True
        elif name=='summary-check.json':doc['recomputed_pass']=True
        else:doc['metric_pass']=True
        if name=='reduction.json':
            doc['builder_exit_code']=0
            doc['summary_sha256']=IO.digest(case['members']['summary.json'][0])
        if name=='capture.json':doc['status']='captured_metric_pass'
        case['members'][name]=(IO.encode(doc),stat.S_IFREG|0o600)
    rebind_synthetic_capture(case)
    with pytest.raises(IO.IntakeError,match='q2_summary_mismatch'):run_case(case,consumer)


@pytest.mark.parametrize('consumer',['producer','admission'])
def test_wrong_replay_environment_is_invalid_not_metric_fail(tmp_path,consumer):
    case=synthetic_case(tmp_path/'case')
    case['profile']['replay_environment']['unicode']='99.0.0'
    with pytest.raises(IO.IntakeError,match='q2_replay_environment'):run_case(case,consumer)


def test_actual_other_python_rejects_original_replay_environment():
    executable=shutil.which('python3.12')
    if executable is None:pytest.skip('separate Python 3.12 interpreter not installed')
    source="import sys; from pathlib import Path; sys.path.insert(0,"+repr(str(TOOLS))+"); import load_q2_release_intake_v0 as l, evaluate_q2_archived_capture_v0 as e; e.check_replay_environment(l.load_profile(Path("+repr(str(ROOT))+")))"
    run=subprocess.run([executable,'-I','-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert run.returncode!=0 and b'q2_replay_environment' in run.stderr


def test_changed_reducer_source_is_rejected_before_replay(tmp_path):
    case=synthetic_case(tmp_path/'case')
    repo=tmp_path/'changed';repo.mkdir()
    for path in case['profile']['replay_sources']:
        target=repo/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    with (repo/IO.REDUCER).open('ab') as stream:stream.write(b'\n')
    with pytest.raises(IO.IntakeError,match='q2_digest_mismatch'):
        PRODUCER.replay(repo,case['folder'],case['raw'],case['profile'],IO.Deadline(5))



@pytest.mark.parametrize('consumer',['producer','admission'])
@pytest.mark.parametrize('corrupt_last',[False,True],ids=['complete-cardinality','last-runtime-file-mismatch'])
def test_full_runtime_inventory_cardinality_uses_actual_synthetic_member_bytes(tmp_path,consumer,corrupt_last):
    case=synthetic_case(tmp_path/'large',runtime_file_count=18485)
    assert case['profile']['record_status']=='synthetic_fixture'
    runtime=[n for n in case['capsule'] if n.startswith('runtime/') and n!='runtime/lib64']
    assert len(runtime)==18485
    if corrupt_last:
        name=sorted(n for n in runtime if 'synthetic_runtime_file_' in n)[-1]
        raw,mode=case['capsule'][name];case['capsule'][name]=(raw+b'CORRUPTED_LAST_MEMBER',mode)
        zipped(case['folder']/'capsule.zip',case['capsule'])
        case['request']['release_subject'].update(snapshot(case['folder']/'capsule.zip'))
        with pytest.raises(IO.IntakeError,match='q2_subject_mismatch'):run_case(case,consumer)
    else:
        result=run_case(case,consumer)
        assert result['input_valid'] is True and result['metric_pass'] is False
        assert result['process_exit']==1 and result['record_status']=='synthetic_fixture'


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
