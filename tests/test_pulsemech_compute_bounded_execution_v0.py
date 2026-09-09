"""Bounded-execution regressions; local acquisitions are explicitly examples."""
from __future__ import annotations
import copy
import errno
import fcntl
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import check_pulsemech_compute_bounded_execution_v0 as v
import capture_pulsemech_compute_bounded_execution_v0 as c
import build_pulsemech_compute_bounded_execution_inputs_v0 as a
import consume_pulsemech_compute_bounded_result_v0 as consumer

@pytest.fixture(scope='module')
def example():
    rev=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()
    ctx={'record_status':'example','repository':v.REPOSITORY,'workflow_name':'PULSEmech bounded execution reference',
         'workflow_path':v.WORKFLOW,'run_id':1,'run_number':1,'run_attempt':1,'source_commit':rev,
         'event_name':'test','acquisition_id':'example:permanent-bounded-regression'}
    prep=a.prepare(repository_root=ROOT,context=ctx)
    h=v.sha(v.unpack(prep)['prelaunch.json'])
    raw=c.capture(prep,repository_root=ROOT,expected_context=ctx,expected_prelaunch_sha256=h)
    return ctx,h,prep,raw

def checked(example,raw=None,ctx=None,h=None):
    return v.verify_capture(example[3] if raw is None else raw,repository_root=ROOT,
        expected_context=example[0] if ctx is None else ctx,expected_prelaunch_sha256=example[1] if h is None else h)

def revise(raw,edit):
    m=v.unpack(raw);d=v.parse(m['capture.json']);edit(d,m)
    d['member_inventory']=[v.descriptor(k,b) for k,b in sorted(m.items()) if k!='capture.json']
    m['capture.json']=v.canonical(d)
    return v.pack(m)

@pytest.mark.parametrize('case,code,state',[('allow',0,'ready'),('block_false',1,'held'),('missing_required',2,'held')])
def test_actual_outcomes(example,case,code,state):
    result=checked(example)
    row=next(x for x in result.case_outcomes if x['case_id']==case)
    assert row==dict(case_id=case,actual_exit_code=code,expected_exit_code=code,matches_expected=True,terminal_state=state)
    terminal=v.parse(result.members[f'results/{case}/terminal_state.json'])
    assert terminal['checker_exit_code']==code and terminal['state']==state and terminal['authority_effect']=='none'

def test_distinct_occurrences_and_terminal_roles(example):
    r=checked(example)
    assert [x['execution_id'] for x in r.capture['executions']]==[f'execution:{case}:{k}' for case in v.CASES for k in ('checker','consumer')]
    assert len(r.capture['terminal_roles'])==6
    assert r.prelaunch['boundary']['resource_measurement']=='unavailable'

def test_offline_checker_import_independence():
    import ast
    names=[]
    for n in ast.walk(ast.parse((ROOT/v.VALIDATOR).read_bytes())):
        if isinstance(n,ast.Import):names.extend(x.name for x in n.names)
        if isinstance(n,ast.ImportFrom):names.append(n.module or '')
    assert not any(x.startswith(('capture_pulsemech','consume_pulsemech','build_pulsemech_compute_bounded')) for x in names)

def test_reverification_does_not_run_subject(example,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('unexpected acquisition')
    monkeypatch.setattr(c,'capture',forbidden)
    one,two=checked(example),checked(example)
    assert one.case_outcomes==two.case_outcomes
    assert v.pack(one.members)==example[3]==v.pack(two.members)

def test_fixed_preparation_determinism(example):
    timestamp=v.parse(v.unpack(example[2])['prelaunch.json'])['created_at_utc']
    assert a.prepare(repository_root=ROOT,context=example[0],created_at_utc=timestamp)==example[2]

def test_fresh_acquisition_has_distinct_event_times(example):
    raw=c.capture(example[2],repository_root=ROOT,expected_context=example[0],expected_prelaunch_sha256=example[1])
    one,two=checked(example),checked(example,raw)
    assert one.case_outcomes==two.case_outcomes
    assert one.capture['started_at_utc']!=two.capture['started_at_utc']

@pytest.mark.parametrize('field,value',[('run_id',2),('run_id',True),('run_id',1.0),('run_attempt',2),('source_commit','a'*40),('acquisition_id','example:other'),('record_status','observed')])
def test_wrong_expected_context(example,field,value):
    ctx=dict(example[0]);ctx[field]=value
    with pytest.raises(v.EvidenceError,match='context_mismatch'):checked(example,ctx=ctx)

@pytest.mark.parametrize('h',['0'*64,'','G'*64,'a'*63])
def test_expected_prelaunch_is_required(example,h):
    with pytest.raises(v.EvidenceError):checked(example,h=h)

MUTATIONS=['missing_execution','duplicate_execution','reverse_execution','wrong_case','observer_substitution',
 'pid_zero','source_digest','argument_substitution','missing_seal','missing_input','duplicate_fd','wrong_input_digest',
 'missing_stdout_eof','missing_stderr_eof','signal_result','consumer_failure','start_after_end','monotonic_reverse',
 'duration_limit','out_of_order','terminal_missing','terminal_extra','terminal_fake_consumer','undeclared_field',
 'capture_wrong_context','capture_wrong_prelaunch','capture_incomplete','output_wrong_member']
@pytest.mark.parametrize('mutation',MUTATIONS)
def test_extent_and_execution_rejections(example,mutation):
    def edit(d,m):
        r=d['executions'][0]
        if mutation=='missing_execution':d['executions'].pop()
        elif mutation=='duplicate_execution':d['executions'][-1]=copy.deepcopy(r)
        elif mutation=='reverse_execution':d['executions'].reverse()
        elif mutation=='wrong_case':r['case_id']='block_false'
        elif mutation=='observer_substitution':r['kind']='observer'
        elif mutation=='pid_zero':r['pid']=0
        elif mutation=='source_digest':r['source_sha256']='0'*64
        elif mutation=='argument_substitution':r['arguments'][-1]='other_gate'
        elif mutation=='missing_seal':r['sealed_inputs'][0]['seal_mask']=7
        elif mutation=='missing_input':r['sealed_inputs'].pop()
        elif mutation=='duplicate_fd':r['sealed_inputs'][0]['fd']=r['sealed_inputs'][1]['fd']
        elif mutation=='wrong_input_digest':r['sealed_inputs'][0]['sha256']='0'*64
        elif mutation=='missing_stdout_eof':r['stdout_eof']=False
        elif mutation=='missing_stderr_eof':r['stderr_eof']=False
        elif mutation=='signal_result':r['exit_code']=-9
        elif mutation=='consumer_failure':d['executions'][1]['exit_code']=2
        elif mutation=='start_after_end':r['started_at_utc']='2999-01-01T00:00:00.000000Z'
        elif mutation=='monotonic_reverse':r['end_monotonic_ns']=0
        elif mutation=='duration_limit':r['end_monotonic_ns']=r['start_monotonic_ns']+32_000_000_000
        elif mutation=='out_of_order':d['executions'][1]['start_monotonic_ns']=0
        elif mutation=='terminal_missing':d['terminal_roles'].pop()
        elif mutation=='terminal_extra':d['terminal_roles'].append('results/new.txt')
        elif mutation=='terminal_fake_consumer':d['terminal_roles'][0]='results/allow/checker.stdout'
        elif mutation=='undeclared_field':d['verified']=True
        elif mutation=='capture_wrong_context':d['context']['run_attempt']=2
        elif mutation=='capture_wrong_prelaunch':d['prelaunch_sha256']='0'*64
        elif mutation=='capture_incomplete':d['capture_status']='partial'
        elif mutation=='output_wrong_member':r['stdout']['member']='results/block_false/checker.stdout'
    with pytest.raises(v.EvidenceError):checked(example,revise(example[3],edit))

@pytest.mark.parametrize('case',v.CASES)
@pytest.mark.parametrize('stream',['stdout','stderr'])
def test_raw_stream_mutation_with_rehashed_inventory(example,case,stream):
    raw=revise(example[3],lambda d,m:m.__setitem__(f'results/{case}/checker.{stream}',b'changed'))
    with pytest.raises(v.EvidenceError):checked(example,raw)

@pytest.mark.parametrize('field,value',[('case_id','block_false'),('checker_execution_id','execution:block_false:checker'),
 ('context_sha256','0'*64),('result_sha256','0'*64),('pending_state_sha256','0'*64),('state','held'),
 ('checker_exit_code',True),('release_allowed',True)])
def test_false_consumption_rejected_beyond_outer_digest(example,field,value):
    def edit(d,m):
        name='results/allow/terminal_state.json';t=v.parse(m[name]);t[field]=value;m[name]=v.canonical(t)
        d['executions'][1]['stdout']=v.descriptor(name,m[name])
    with pytest.raises(v.EvidenceError):checked(example,revise(example[3],edit))

@pytest.mark.parametrize('change',['policy_order','case_recipe','source_sha','source_bytes','planner_output','extra_input','unknown_field'])
def test_prelaunch_with_coherently_changed_outer_digest(example,change):
    m=v.unpack(example[2]);s=v.parse(m['prelaunch.json'])
    if change=='policy_order':s['required_gate_ids'].reverse()
    elif change=='case_recipe':
        name='inputs/allow/status.json';m[name]=v.canonical({'gates':{}});s['cases'][0]['status']=v.descriptor(name,m[name])
        s['input_inventory']=[v.descriptor(x['member'],m[x['member']]) for x in s['input_inventory']]
    elif change=='source_sha':s['source_bindings'][0]['sha256']='0'*64
    elif change=='source_bytes':
        e=s['source_bindings'][0];m[e['member']]+=b'\n';e.update(v.descriptor(e['member'],m[e['member']]))
    elif change=='planner_output':
        name='planner/plan.json';plan=v.parse(m[name]);plan['request_id']='forged_schema_valid';m[name]=v.canonical(plan)
        s['planner']['plan']=v.descriptor(name,m[name]);s['input_inventory']=[v.descriptor(x['member'],m[x['member']]) for x in s['input_inventory']]
    elif change=='extra_input':m['inputs/unplanned.txt']=b'new';s['input_inventory'].append(v.descriptor('inputs/unplanned.txt',b'new'))
    elif change=='unknown_field':s['source_verified']=True
    m['prelaunch.json']=v.canonical(s)
    with pytest.raises(v.EvidenceError):v.verify_prelaunch(m,repository_root=ROOT,expected_context=example[0],expected_prelaunch_sha256=v.sha(m['prelaunch.json']))

@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":Infinity}',b'\xef\xbb\xbf{}\n',b'[]\n',b'{"x":"\xff"}',b'{}',b'{"x": 1}\n',b'{\n  "x": 1.0\n}\n'])
def test_json_rejections(raw):
    with pytest.raises(v.EvidenceError):v.parse(raw)

@pytest.mark.parametrize('name',['../escape','/absolute','a/../../x','a\\x','a//x','.','a/./x'])
def test_unsafe_carrier_paths(name):
    with pytest.raises(v.EvidenceError):v.pack({name:b'x'})

@pytest.mark.parametrize('mutation',['duplicate','directory','symlink','compression','trailing','comment','extra'])
def test_carrier_structure_rejections(mutation):
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as z:
        item=zipfile.ZipInfo('safe.txt');item.create_system=3;item.external_attr=(stat.S_IFREG|0o644)<<16
        if mutation=='directory':item.filename='safe/';item.external_attr=(stat.S_IFDIR|0o755)<<16
        elif mutation=='symlink':item.external_attr=(stat.S_IFLNK|0o777)<<16
        elif mutation=='compression':item.compress_type=zipfile.ZIP_DEFLATED
        elif mutation=='extra':item.extra=b'\x01\x00\x00\x00'
        z.writestr(item,b'x')
        if mutation=='duplicate':
            with pytest.warns(UserWarning):z.writestr(item,b'y')
        if mutation=='comment':z.comment=b'comment'
    with pytest.raises(v.EvidenceError):v.unpack(raw.getvalue()+(b'trailing' if mutation=='trailing' else b''))

@pytest.mark.parametrize('operation',['write','truncate','grow','remove_seals'])
def test_descriptor_seals(operation):
    fd=c.sealed_buffer('negative',b'original')
    try:
        with pytest.raises(OSError) as error:
            if operation=='write':os.pwrite(fd,b'x',0)
            elif operation=='truncate':os.ftruncate(fd,0)
            elif operation=='grow':os.ftruncate(fd,100)
            else:fcntl.fcntl(fd,fcntl.F_ADD_SEALS,0)
        assert error.value.errno==errno.EPERM
        assert os.pread(fd,8,0)==b'original'
    finally:os.close(fd)

def test_timeout_reaps_owned_process():
    p=subprocess.Popen([sys.executable,'-I','-S','-c','import time; time.sleep(3)'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    with pytest.raises(v.EvidenceError,match='timeout'):c._read_bounded_process(p,time.monotonic()+0.03)
    assert p.poll() is not None

def test_stream_limit_reaps_owned_process(monkeypatch):
    monkeypatch.setattr(c,'STREAM_LIMIT_BYTES',128)
    p=subprocess.Popen([sys.executable,'-I','-S','-c','import sys; sys.stdout.write("x"*200000)'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    with pytest.raises(v.EvidenceError,match='stream_limit'):c._read_bounded_process(p,time.monotonic()+3)
    assert p.poll() is not None

def test_publication_preserves_existing(tmp_path):
    path=tmp_path/'result.zip';path.write_bytes(b'unrelated')
    with pytest.raises(v.EvidenceError,match='already_exists'):v.publish_new(path,b'new',repository_root=ROOT)
    assert path.read_bytes()==b'unrelated' and list(tmp_path.iterdir())==[path]

@pytest.mark.parametrize('mode',['repository','traversal','parent_symlink','leaf_symlink'])
def test_output_path_guards(tmp_path,mode):
    path=tmp_path/'result.zip'
    if mode=='repository':path=ROOT/'must-not-be-written.zip'
    elif mode=='traversal':path=tmp_path/'..'/'not-written.zip'
    elif mode=='parent_symlink':(tmp_path/'link').symlink_to(tmp_path,target_is_directory=True);path=tmp_path/'link'/'result.zip'
    else:path.symlink_to(tmp_path/'other')
    with pytest.raises(v.EvidenceError):v.publish_new(path,b'x',repository_root=ROOT)
    assert not (ROOT/'must-not-be-written.zip').exists()

@pytest.mark.parametrize('existing',[False,True])
def test_prepublication_failure_closes_only_anonymous_inode(tmp_path,monkeypatch,existing):
    path=tmp_path/'result.zip'
    if existing:path.write_bytes(b'unrelated')
    def failing(fd):raise OSError(errno.EIO,'injected prepublication failure')
    monkeypatch.setattr(v.os,'fsync',failing)
    with pytest.raises(v.EvidenceError):v.publish_new(path,b'owned',repository_root=ROOT)
    if existing:assert path.read_bytes()==b'unrelated'
    else:assert not path.exists()
    assert not list(tmp_path.glob('.pulse-bounded-*'))


def test_publication_race_preserves_competing_writer(tmp_path,monkeypatch):
    path=tmp_path/'result.zip';original=v.os.link
    def competing(src,dst,**kwargs):
        path.write_bytes(b'competing writer')
        return original(src,dst,**kwargs)
    monkeypatch.setattr(v.os,'link',competing)
    with pytest.raises(v.EvidenceError,match='already_exists'):
        v.publish_new(path,b'owned',repository_root=ROOT)
    assert path.read_bytes()==b'competing writer'
    assert list(tmp_path.iterdir())==[path]


def test_publication_has_no_visible_path_cleanup(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('visible path unlink attempted')
    monkeypatch.setattr(v.os,'unlink',forbidden)
    path=tmp_path/'result.zip';v.publish_new(path,b'owned',repository_root=ROOT)
    assert path.read_bytes()==b'owned'


def test_consumer_rejects_mutable_paths(tmp_path):
    path=tmp_path/'input.json';path.write_bytes(b'{}\n')
    p=subprocess.run([sys.executable,'-I','-S',str(ROOT/v.CONSUMER),'--result',str(path),'--stdout',str(path),'--stderr',str(path),'--pending',str(path),'--context-sha256','a'*64,'--prelaunch-sha256','b'*64,'--case-id','allow','--checker-execution-id','execution:allow:checker'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert p.returncode==2 and p.stdout==b''

def test_complete_foundation_cli(example,tmp_path):
    ctx=tmp_path/'context.json';ctx.write_bytes(v.canonical(example[0]));prepared=tmp_path/'prepared.zip';carrier=tmp_path/'carrier.zip'
    def run(path,args):return subprocess.run([sys.executable,'-I',str(ROOT/path),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
    p=run(v.ADAPTER,['prepare','--repository-root',str(ROOT),'--context',str(ctx),'--output',str(prepared)])
    assert p.returncode==0,p.stderr.decode()
    h=p.stdout.decode().strip()
    p=run(v.CAPTURE,['--repository-root',str(ROOT),'--expected-context',str(ctx),'--expected-prelaunch-sha256',h,'--prepared',str(prepared),'--output',str(carrier)])
    assert p.returncode==0,p.stderr.decode()
    p=run(v.VALIDATOR,['--repository-root',str(ROOT),'--expected-context',str(ctx),'--expected-prelaunch-sha256',h,'--carrier',str(carrier)])
    assert p.returncode==0,p.stderr.decode()
    assert v.parse(p.stdout)['ok'] is True


@pytest.fixture(scope='module')
def pipeline(example):
    outputs=a.reconstruction_inputs(carrier_bytes=example[3],repository_root=ROOT,
        expected_context=example[0],expected_prelaunch_sha256=example[1],analysis_run_key='analysis:bounded:permanent')
    return outputs


def report_sources(example,pipeline):
    return {'subject_input_bytes':pipeline['subject.json'],'carrier_bytes':example[3],
        'repository_root':ROOT,'expected_context':example[0],'expected_prelaunch_sha256':example[1],
        'runtime_packet_bytes':pipeline['runtime.json']}


def relation_sources(example,pipeline):
    return {'report_inputs':report_sources(example,pipeline),'report_bytes':pipeline['runtime_report.json'],
        'plan_bytes':pipeline['plan.json'],'expectations_bytes':pipeline['expectations.json']}


def dependency(example,path):
    return v.load_reconstruction_module('tools/'+path,repository_root=ROOT,revision=example[0]['source_commit'])


def test_bounded_connected_chain_preserves_exact_occurrences_and_outcomes(example,pipeline):
    baseline=v.parse(pipeline['baseline.json']);report=v.parse(pipeline['runtime_report.json'])
    relation=v.parse(pipeline['relation.json']);md=v.parse(pipeline['materialization.json'])
    assert baseline['compute_nodes']==[] and baseline['edges']==[]
    assert report['bounded_binding']['baseline_sha256']==v.sha(pipeline['baseline.json'])
    assert len(report['compute_nodes'])==len(relation['expectations'])==len(relation['observations'])==6
    assert relation['summary']['comparison_complete'] is True
    assert relation['coverage']['runtime_observation_status']=='partial'
    assert relation['bounded_comparison']['resource_coverage_status']=='unavailable'
    assert report['resource_summary']=={'axes':{}}
    assert [(c['actual_exit_code'],c['terminal_state']) for c in report['bounded_binding']['case_outcomes']]==[(0,'ready'),(1,'held'),(2,'held')]
    assert md['output_status_written'] is True and md['record_status']=='example'
    assert all(type(x) is bool for x in md['candidate_gates'].values())
    assert v.parse(pipeline['candidate.json'])['gates']==md['candidate_gates']
    for row in relation['relations'].values():
        assert len(row['observation_ids'])==1
        expected=relation['expectations'][row['expectation_id']]['expected_compute']['selector']['bounded_execution_id']
        actual=relation['observations'][row['observation_ids'][0]]['execution_identity']['bounded_execution_id']
        assert actual==expected


def test_bounded_packet_and_recorder_ownership_remain_distinct(example,pipeline):
    report=v.parse(pipeline['runtime_report.json']);packet=v.parse(pipeline['runtime.json'])
    assert len([r for r in packet['executions'] if r['execution_scope']=='subject'])==6
    projection=[r for r in packet['executions'] if r['execution_scope']!='subject']
    assert len(projection)==1 and projection[0]['capture_status']!='complete'
    assert packet['producer']['producer_source']=='tools/pulsemech_compute_binding_analyzer_core_v0.py'
    states={s['state_id']:s for s in report['state_nodes']}
    assert all(states[s]['producer_node_id'] is None for s in report['bounded_binding']['recorder_result_state_ids'])
    assert len(report['bounded_binding']['terminal_state_ids'])==6
    assert 'decision' not in report['subject']


@pytest.mark.parametrize('target,mutation',[('report','baseline'),('report','case_outcome'),('relation','joint_locators'),('relation','occurrence')])
def test_bounded_schema_valid_forgery_rejected_by_source_replay(example,pipeline,target,mutation):
    if target=='report':
        checker=dependency(example,'check_pulsemech_compute_binding_report_v0.py')
        doc=v.parse(pipeline['runtime_report.json'])
        if mutation=='baseline':doc['bounded_binding']['baseline_sha256']='0'*64
        else:doc['bounded_binding']['case_outcomes'][0]['actual_exit_code']=1
        errors=checker.check_bounded_source_replay(doc,v.canonical(doc),report_sources(example,pipeline))
    else:
        checker=dependency(example,'check_pulsemech_compute_planned_observed_relation_v0.py')
        doc=v.parse(pipeline['relation.json'])
        if mutation=='joint_locators':
            old_plan=doc['plan_binding']['path_or_uri'];old_report=doc['observation_bindings']['compute_binding_report']['path_or_uri']
            raw=v.canonical(doc).replace(old_plan.encode(),b'sha256:'+b'a'*64).replace(old_report.encode(),b'sha256:'+b'b'*64)
            doc=v.parse(raw)
        else:
            first=next(iter(doc['observations'].values()));first['execution_identity']['bounded_execution_id']='execution:missing_required:consumer'
        errors=checker.check_bounded_relation_replay(doc,relation_sources(example,pipeline))
    assert errors


def test_bounded_report_exact_bytes_not_text_normalization(example,pipeline):
    checker=dependency(example,'check_pulsemech_compute_binding_report_v0.py')
    raw=pipeline['runtime_report.json'].replace(b'\n',b'\r\n')
    assert checker.check_bounded_source_replay(v.parse(pipeline['runtime_report.json']),raw,report_sources(example,pipeline))


def test_bounded_candidate_rejects_invalid_relation_without_output(example,pipeline,tmp_path):
    materializer=dependency(example,'fold_pulsemech_compute_planned_observed_relation_into_status_v0.py')
    doc=v.parse(pipeline['relation.json']);doc['plan_binding']['path_or_uri']='sha256:'+'0'*64
    (tmp_path/'relation.json').write_bytes(v.canonical(doc));(tmp_path/'base.json').write_bytes(pipeline['base_candidate.json'])
    output=tmp_path/'candidate.json'
    report,rc=materializer.build_and_write_folded_status(status_path=tmp_path/'base.json',relation_path=tmp_path/'relation.json',
        schema_path=ROOT/'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json',
        validator_path=ROOT/'tools/check_pulsemech_compute_planned_observed_relation_v0.py',output_path=output,
        bounded_inputs=relation_sources(example,pipeline))
    assert rc!=0 and not output.exists() and report['output_status_written'] is False


def test_bounded_candidate_preserves_preexisting_output(example,pipeline,tmp_path):
    materializer=dependency(example,'fold_pulsemech_compute_planned_observed_relation_into_status_v0.py')
    for name in ('relation.json','base_candidate.json'):(tmp_path/name).write_bytes(pipeline[name])
    output=tmp_path/'candidate.json';output.write_bytes(b'unrelated')
    report,rc=materializer.build_and_write_folded_status(status_path=tmp_path/'base_candidate.json',relation_path=tmp_path/'relation.json',
        schema_path=ROOT/'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json',
        validator_path=ROOT/'tools/check_pulsemech_compute_planned_observed_relation_v0.py',output_path=output,
        bounded_inputs=relation_sources(example,pipeline))
    assert rc!=0 and output.read_bytes()==b'unrelated' and report['output_status_written'] is False


def _write_pipeline_inputs(example,pipeline,directory):
    for name,raw in pipeline.items():(directory/name).write_bytes(raw)
    (directory/'capture.zip').write_bytes(example[3]);(directory/'context.json').write_bytes(v.canonical(example[0]))
    return ['--repository-root',str(ROOT),'--expected-context',str(directory/'context.json'),
        '--expected-prelaunch-sha256',example[1],'--carrier',str(directory/'capture.zip')]


def test_bounded_reconstruction_in_a_second_process_is_byte_identical(example,pipeline,tmp_path):
    common=_write_pipeline_inputs(example,pipeline,tmp_path)
    output=tmp_path/'replayed.zip'
    process=subprocess.run([sys.executable,'-I','-B',str(ROOT/v.ADAPTER),'reconstruct',*common,
        '--analysis-run-key','analysis:bounded:permanent','--output',str(output)],
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300,check=False)
    assert process.returncode==0,(process.stdout.decode(),process.stderr.decode())
    assert output.read_bytes()==v.pack(pipeline)
    assert process.stdout.decode().strip()==v.sha(output.read_bytes())


def test_bounded_direct_cli_entrypoints_consume_the_same_inputs(example,pipeline,tmp_path):
    common=_write_pipeline_inputs(example,pipeline,tmp_path)
    reportargs=common+['--subject-input',str(tmp_path/'subject.json'),'--runtime-packet',str(tmp_path/'runtime.json')]
    commands=[
      ('build_pulsemech_compute_binding_report_from_subject_input_v0.py',
       common+['--packet',str(tmp_path/'subject.json'),'--runtime-packet',str(tmp_path/'runtime.json'),
               '--analysis-run-key','analysis:bounded:permanent'],pipeline['runtime_report.json']),
      ('check_pulsemech_compute_binding_report_v0.py',reportargs+['--schema',str(ROOT/'schemas/pulsemech_compute_binding_report_v0.schema.json'),
        '--report',str(tmp_path/'runtime_report.json')],None),
      ('build_pulsemech_compute_planned_observed_relation_v0.py',reportargs+['--plan',str(tmp_path/'plan.json'),
        '--compute-report',str(tmp_path/'runtime_report.json'),'--expectations',str(tmp_path/'expectations.json'),
        '--relation-id',v.parse(pipeline['relation.json'])['comparison_identity']['relation_record_id']],pipeline['relation.json']),
      ('check_pulsemech_compute_planned_observed_relation_v0.py',reportargs+['--plan',str(tmp_path/'plan.json'),
        '--compute-report',str(tmp_path/'runtime_report.json'),'--expectations',str(tmp_path/'expectations.json'),
        '--relation',str(tmp_path/'relation.json')],None),
      ('fold_pulsemech_compute_planned_observed_relation_into_status_v0.py',reportargs+['--plan',str(tmp_path/'plan.json'),
        '--compute-report',str(tmp_path/'runtime_report.json'),'--expectations',str(tmp_path/'expectations.json'),
        '--relation',str(tmp_path/'relation.json'),'--status',str(tmp_path/'base_candidate.json'),
        '--output',str(tmp_path/'cli_candidate.json')],None)]
    for name,args,expected in commands:
        process=subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools'/name),*args],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,check=False)
        assert process.returncode==0,(name,process.stdout.decode(),process.stderr.decode())
        if expected is not None:assert process.stdout==expected,name
        else:assert v.parse(process.stdout)['ok'] is True,name
    assert (tmp_path/'cli_candidate.json').read_bytes()==pipeline['candidate.json']


def test_bounded_reader_rejects_fifo_without_waiting(tmp_path):
    fifo=tmp_path/'input';os.mkfifo(fifo)
    with pytest.raises(v.EvidenceError,match='source_type_or_limit'):v.read_regular(fifo)


def test_bounded_batch_source_inventory_matches_exact_git_blobs(example):
    paths=(v.CHECKER,v.CONSUMER,v.POLICY)
    result=v.git_source_inventory(ROOT,example[0]['source_commit'],paths)
    assert result=={path:v.git_blob(ROOT,example[0]['source_commit'],path) for path in paths}


def test_bounded_batch_rejects_missing_nonregular_source(example):
    with pytest.raises(v.EvidenceError):v.git_source_inventory(ROOT,example[0]['source_commit'],('tools',))


def test_bounded_manual_workflow_and_registration_contract():
    import yaml
    workflow=yaml.load((ROOT/v.WORKFLOW).read_text(),Loader=yaml.BaseLoader)
    assert set(workflow['on'])=={'workflow_dispatch'}
    assert workflow['permissions']=={'contents':'read'}
    job=workflow['jobs']['reference']
    assert job['permissions']=={'contents':'read'} and job['runs-on']=='ubuntu-24.04'
    assert job['timeout-minutes']=='20'
    assert job['steps'][0]['with']['persist-credentials']=='false'
    assert job['steps'][0]['with']['fetch-depth']=='0'
    assert 'run-reference' in job['steps'][3]['run']
    entries=[line.split('#',1)[0].strip() for line in (ROOT/'ci/tools-tests.list').read_text().splitlines()]
    entries=[x for x in entries if x]
    assert len(entries)==len(set(entries))==154
    assert entries.count('tests/test_pulsemech_compute_bounded_execution_v0.py')==1


def _simulated_workflow_env(example):
    """Control-plane parsing fixture, not a genuine observed acquisition."""
    rev=example[0]['source_commit']
    return {'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REPOSITORY':v.REPOSITORY,
        'GITHUB_REF':'refs/heads/main','GITHUB_WORKSPACE':str(ROOT),'EXPECTED_SOURCE_COMMIT':rev,'GITHUB_SHA':rev,
        'CONTROL_PLANE_REVISION':rev,'CONTROL_PLANE_WORKFLOW_REF':v.REPOSITORY+'/'+v.WORKFLOW+'@refs/heads/main',
        'GITHUB_WORKFLOW':'PULSEmech bounded execution reference','GITHUB_RUN_ID':'123','GITHUB_RUN_NUMBER':'4','GITHUB_RUN_ATTEMPT':'1'}


@pytest.mark.parametrize('field,value',[('GITHUB_ACTIONS','false'),('GITHUB_EVENT_NAME','pull_request'),
    ('GITHUB_REPOSITORY','other/repo'),('GITHUB_REF','refs/heads/unreviewed'),('GITHUB_WORKSPACE','/'),
    ('EXPECTED_SOURCE_COMMIT',''),('GITHUB_SHA','a'*40),('CONTROL_PLANE_REVISION','b'*40),
    ('CONTROL_PLANE_WORKFLOW_REF','other'),('GITHUB_WORKFLOW','other'),('GITHUB_RUN_ID','0'),
    ('GITHUB_RUN_NUMBER','01'),('GITHUB_RUN_ATTEMPT','-1')])
def test_bounded_reference_refuses_unbound_control_plane(example,field,value):
    env=_simulated_workflow_env(example);env[field]=value
    with pytest.raises(v.EvidenceError):a.workflow_context(repository_root=ROOT,environ=env)


def test_bounded_control_plane_parser_keeps_one_run_and_three_cases(example):
    context=a.workflow_context(repository_root=ROOT,environ=_simulated_workflow_env(example))
    assert context['run_id']==123 and context['run_attempt']==1
    assert context['acquisition_id']==f'github:{v.REPOSITORY}:123:1'
    # This exercises parser behavior only. No observed fixture is acquired.
    assert example[0]['record_status']=='example'


@pytest.mark.parametrize('relative',[v.CAPTURE,v.CONSUMER,v.ADAPTER,'tools/arbitrary.py'])
def test_bounded_offline_loader_does_not_execute_acquisition_programs(example,relative):
    with pytest.raises(v.EvidenceError,match='dependency_not_allowed'):
        v.load_reconstruction_module(relative,repository_root=ROOT,revision=example[0]['source_commit'])



def test_bounded_outer_capsule_creates_new_parent_and_never_replaces(tmp_path):
    payload={name:b'test-only publication payload' for name in ('prepared.zip','capture.zip','expected_context.json',
        'expected_prelaunch.sha256','reconstruction.zip')}
    directory=tmp_path/'reference'
    digest=a.publish_reference_capsule(repository_root=ROOT,output_directory=directory,members=payload)
    capsule=directory/'reference_capsule_v0.zip';saved=capsule.read_bytes()
    assert digest==v.sha(saved)
    members=v.unpack(saved)
    assert set(members)==set(payload)|{'SHA256SUMS'}
    assert members['SHA256SUMS']==(''.join(v.sha(raw)+'  '+name+'\n' for name,raw in sorted(payload.items()))).encode()
    with pytest.raises((v.EvidenceError,OSError)):
        a.publish_reference_capsule(repository_root=ROOT,output_directory=directory,members=payload)
    assert capsule.read_bytes()==saved


def test_bounded_observed_packet_projection_schema_is_not_example_only(example):
    # Pure representation test. This context is simulated; no capture or
    # workflow evidence is relabelled, accepted or preserved as an observed run.
    from types import SimpleNamespace
    core=dependency(example,'pulsemech_compute_binding_analyzer_core_v0.py')
    source=checked(example)
    context=dict(source.expected_context,record_status='observed',event_name='workflow_dispatch',
        acquisition_id=f"github:{v.REPOSITORY}:1:1")
    simulated=SimpleNamespace(expected_context=context,prelaunch=source.prelaunch,capture=source.capture,
        members=source.members,carrier_sha256=source.carrier_sha256)
    packet=core._bounded_packet_projection(simulated,v)
    validator=dependency(example,'check_pulsemech_compute_runtime_observation_packet_v0.py')
    class View:
        def __init__(self,raw):self.raw=raw
        def read_bytes(self):return self.raw
        def read_text(self,encoding='utf-8'):return self.raw.decode(encoding)
    diagnostic,rc=validator.build_diagnostic(schema_path=View(source.members['sources/'+core.BOUNDED_RUNTIME_SCHEMA]),
        packet_path=View(v.canonical(packet)))
    assert rc==0,diagnostic
    assert example[0]['record_status']=='example' and source.capture['context']['record_status']=='example'


def test_bounded_replay_dependency_modified_before_loading_is_not_executed(example,tmp_path):
    import importlib.util
    clone=tmp_path/'clone'
    subprocess.run(['/usr/bin/git','-c','advice.detachedHead=false','clone','--quiet','--no-hardlinks',str(ROOT),str(clone)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=True)
    marker=tmp_path/'must-not-exist'
    checker=clone/'tools/check_pulsemech_compute_binding_report_v0.py'
    checker.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n')
    for filename in ('build_pulsemech_compute_planned_observed_relation_v0.py','check_pulsemech_compute_planned_observed_relation_v0.py'):
        path=clone/'tools'/filename;name='_bounded_bootstrap_negative_'+filename.replace('.','_')
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        spec.loader.exec_module(module)
        with pytest.raises(ValueError,match='bootstrap_source_mismatch'):
            module._bounded_report_checker(clone,example[0])
        assert not marker.exists()


if __name__=='__main__':raise SystemExit(pytest.main([__file__,'-q']))
