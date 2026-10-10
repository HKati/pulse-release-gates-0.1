"""Real process, authentication and producer-bypass boundaries; no model runs."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from test_q2_release_intake_v0 import ROOT, TOOLS, IO, LOAD, ADMISSION, metadata_request


def module_at(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


@pytest.fixture
def invocation(tmp_path):
    """Synthetic Git commit identifies only these test bytes, never upstream history."""
    repo=tmp_path/'repo';repo.mkdir()
    extra=('pulse_gate_policy_v0.yml','pulse_gate_registry_v0.yml',
           'PULSE_safe_pack_v0/profiles/required_gate_evaluations_v0.json',
           'schemas/required_gate_evaluation_result_v0.schema.json')
    for name in (*IO.SOURCE_PATHS,*extra):
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    clean={'PATH':'/usr/bin:/bin','HOME':str(tmp_path),'LANG':'C','LC_ALL':'C',
           'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_TERMINAL_PROMPT':'0'}
    commands=[['init','--quiet'],['add','--all'],['-c','user.name=Synthetic offline fixture',
             '-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',
             'commit','--quiet','-m','Synthetic Q2 authentication fixture; not upstream history']]
    for command in commands:
        subprocess.run(['/usr/bin/git',*command],cwd=repo,env=clean,check=True,capture_output=True,timeout=10)
    sha=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=repo,env=clean,timeout=10).decode().strip()
    raw=IO.encode(metadata_request(sha));run='80000000003'
    env={**clean,'GITHUB_REPOSITORY':'HKati/pulse-release-gates-0.1','GITHUB_EVENT_NAME':'workflow_dispatch',
         'GITHUB_REF':'refs/heads/main','GITHUB_SHA':sha,'GITHUB_WORKFLOW_SHA':sha,'GITHUB_WORKFLOW':'PULSE CI',
         'GITHUB_WORKFLOW_REF':'HKati/pulse-release-gates-0.1/.github/workflows/pulse_ci.yml@refs/heads/main',
         'GITHUB_RUN_ID':run,'GITHUB_RUN_ATTEMPT':'1','GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati',
         'GITHUB_ACTIONS':'true','RUNNER_OS':'Linux','RUNNER_ENVIRONMENT':'github-hosted',
         'GITHUB_WORKSPACE':str(repo),'RUNNER_TEMP':str(tmp_path),
         'PULSE_RUN_KEY':f'GITHUB_RUN_ID={run}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI',
         'PULSE_RUN_MODE':'prod', 'SOURCE_DATE_EPOCH':'1577836800',
         LOAD.REQUEST_ENV:raw.decode(),LOAD.DIGEST_ENV:IO.digest(raw),LOAD.TOKEN_ENV:'PRIVATE_TEST_TRANSPORT_TOKEN'}
    event={'inputs':{'strict_external_evidence':'true','llamaguard_evidence_mode':'hosted_full_runtime',
                    'q2_intake_request':raw.decode(),'q2_intake_request_sha256':IO.digest(raw)},
           'ref':'refs/heads/main','sender':{'login':'HKati'},'repository':{'full_name':env['GITHUB_REPOSITORY']}}
    event_path=tmp_path/'event.json';event_path.write_bytes(IO.encode(event));env['GITHUB_EVENT_PATH']=str(event_path)
    return SimpleNamespace(repo=repo,env=env,event=event,event_path=event_path,sha=sha)


@pytest.mark.parametrize('event_ref', ['main', 'refs/heads/main'])
def test_trusted_preselection_and_actual_run_are_separate(invocation,event_ref):
    f=invocation;f.event['ref']=event_ref;f.event_path.write_bytes(IO.encode(f.event))
    request,binding,sources=LOAD.trusted_invocation(f.repo,f.env)
    assert 'run_id' not in request['evaluation_identity']
    assert binding['run_id']==f.env['GITHUB_RUN_ID'] and binding['source_commit']==f.sha
    assert binding['request_sha256']==f.env[LOAD.DIGEST_ENV]
    assert {row['path'] for row in sources}==set(IO.SOURCE_PATHS)
    assert all(row['sha256']==IO.digest((f.repo/row['path']).read_bytes()) for row in sources)


@pytest.mark.parametrize('event_ref', ['refs/tags/main', 'refs/heads/other', 'refs/heads/main/', 'main\n', None, ['main']])
def test_event_ref_cannot_select_a_tag_other_branch_or_alias(invocation,event_ref):
    f=invocation;f.event['ref']=event_ref;f.event_path.write_bytes(IO.encode(f.event))
    with pytest.raises(IO.IntakeError):LOAD.trusted_invocation(f.repo,f.env)


@pytest.mark.parametrize('field,value',[
    ('GITHUB_REPOSITORY','attacker/repository'),('GITHUB_EVENT_NAME','pull_request'),
    ('GITHUB_REF','refs/heads/other'),('GITHUB_WORKFLOW_SHA','0'*40),
    ('GITHUB_WORKFLOW','Other'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_ACTOR','other'),
    ('GITHUB_ACTOR','github-actions[bot]'),('GITHUB_TRIGGERING_ACTOR','github-actions[bot]'),
    ('GITHUB_TRIGGERING_ACTOR','other'),('GITHUB_ACTIONS','false'),('RUNNER_OS','Windows'),
    ('RUNNER_ENVIRONMENT','self-hosted'),('GITHUB_RUN_ID','9000'),('PULSE_RUN_KEY','other'),
    ('GITHUB_WORKSPACE','/tmp'),('GITHUB_WORKFLOW_REF','other')])
def test_matching_request_digest_cannot_authorize_wrong_context(invocation,field,value):
    env={**invocation.env,field:value}
    with pytest.raises(IO.IntakeError):LOAD.trusted_invocation(invocation.repo,env)


@pytest.mark.parametrize('fault',['sender','bot-sender','ref','repository','request','digest','extra-input','source-bytes','source-mode'])
def test_prelaunch_event_and_source_are_independent_authorization_inputs(invocation,fault):
    f=invocation;event=copy.deepcopy(f.event)
    if fault=='sender':event['sender']['login']='other'
    elif fault=='bot-sender':event['sender']['login']='github-actions[bot]'
    elif fault=='ref':event['ref']='other'
    elif fault=='repository':event['repository']['full_name']='other/repo'
    elif fault=='request':event['inputs']['q2_intake_request']='{}'
    elif fault=='digest':event['inputs']['q2_intake_request_sha256']='f'*64
    elif fault=='extra-input':event['inputs']['run_id']='1234'
    elif fault=='source-bytes':
        with (f.repo/IO.PACK/'tools/q2_intake_io_v0.py').open('ab') as stream:stream.write(b'\n')
    else:
        p=f.repo/IO.PACK/'tools/q2_intake_io_v0.py';p.chmod(p.stat().st_mode ^ 0o111)
    f.event_path.write_bytes(IO.encode(event))
    with pytest.raises(IO.IntakeError):LOAD.trusted_invocation(f.repo,f.env)


def test_independent_consumers_reacquire_and_clean_wrong_bytes(invocation,monkeypatch):
    f=invocation;seen=[];parents=[]
    class Transport:
        def __init__(self,token):assert token=='PRIVATE_TEST_TRANSPORT_TOKEN'
        def download(self,repository,identifier,expectation,destination,deadline):
            seen.append((repository,identifier));parents.append(destination.parent)
            assert f.repo not in destination.parents and destination.parent.stat().st_mode & 0o777==0o700
            destination.write_bytes(b'PRIVATE_RAW_RESPONSE_MUST_NOT_ESCAPE')
    monkeypatch.setattr(IO,'GitHubArtifactTransport',Transport)
    for consumer in ['producer','admission']:
        result=LOAD.consume(f.repo,consumer=consumer,environment=f.env)
        assert result['input_valid'] is False and result['metric_pass'] is None
        assert result['checks']['request'] is True and result['cleanup']=='verified_removed'
        assert result['diagnostics']==['q2_digest_mismatch']
        assert b'PRIVATE_' not in IO.encode(result)
    assert len(seen)==2 and seen[0]==seen[1] and parents[0]!=parents[1]
    assert all(not p.exists() for p in parents)


def test_transport_exception_cannot_publish_payload_credentials_or_paths(invocation,monkeypatch):
    class Transport:
        def __init__(self,token):pass
        def download(self,*args):raise RuntimeError('PRIVATE_TEST_TRANSPORT_TOKEN PRIVATE_RAW_RESPONSE /private/capture')
    monkeypatch.setattr(IO,'GitHubArtifactTransport',Transport)
    result=LOAD.consume(invocation.repo,consumer='producer',environment=invocation.env)
    assert result['diagnostics']==['q2_internal_error'] and result['cleanup']=='verified_removed'
    assert b'PRIVATE_' not in IO.encode(result) and b'/private/' not in IO.encode(result)


def test_dispatcher_missing_request_is_invalid_exit_two_with_closed_metadata(invocation):
    f=invocation;env={k:v for k,v in f.env.items() if k not in (LOAD.REQUEST_ENV,LOAD.DIGEST_ENV)}
    plan=json.loads((f.repo/'PULSE_safe_pack_v0/profiles/required_gate_evaluations_v0.json').read_bytes())
    env.update(PULSE_REQUIRED_GATE_ID='q2_consistency_ok',
               PULSE_REQUIRED_GATE_EVALUATION_ID=plan['evaluations']['q2_consistency_ok']['evaluation_id'])
    command=[sys.executable if x=='{python}' else x.replace('{repo_root}',str(f.repo))
             for x in plan['evaluations']['q2_consistency_ok']['command']]
    p=subprocess.run(command,cwd=f.repo,env=env,capture_output=True,timeout=15)
    assert p.returncode==2 and b'PRIVATE_TEST' not in p.stdout+p.stderr
    record=json.loads((f.repo/IO.PUBLIC_RESULT).read_bytes())
    assert record['input_valid'] is False and record['metric_pass'] is None and record['process_exit']==2
    result=json.loads((f.repo/plan['evaluations']['q2_consistency_ok']['result']['artifact']).read_bytes())
    assert result['pass'] is False and result['status']=='failed'
    assert [c['exit_code'] for c in result['checks']]==[2,None]
    assert result['diagnostics']==record['diagnostics']==['q2_request_missing']


def test_valid_negative_check_is_not_invalid_input(tmp_path,monkeypatch):
    from test_q2_release_intake_v0 import synthetic_case,run_case
    case=synthetic_case(tmp_path/'synthetic');record=run_case(case,'producer');record['cleanup']='verified_removed'
    # Dispatcher formatting seam only; the actual synthetic metric was reduced
    # and checked by both unchanged subprocesses before it is supplied here.
    f=tmp_path/'format';shutil.copytree(ROOT/'PULSE_safe_pack_v0',f/'PULSE_safe_pack_v0')
    for name in IO.SOURCE_PATHS:
        target=f/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(ROOT/name,target)
    monkeypatch.setattr(LOAD,'consume',lambda *a,**k:record)
    dispatcher=module_at('q2_dispatcher_format',TOOLS/'evaluate_required_gate_v0.py')
    # build_result has already registered its dispatcher before entering Q2.
    # The shared source must keep that exact reference, not conflict on kind.
    refs={};errors=[]
    dispatcher.add_ref(refs,f,f/dispatcher.TOOL_PATH,'evaluation_tool',None,errors)
    assert not errors
    original_ref=copy.deepcopy(refs[dispatcher.TOOL_PATH])
    checks,diagnostics,warnings=dispatcher.run_q2(SimpleNamespace(repo=f),refs)
    assert refs[dispatcher.TOOL_PATH]==original_ref
    assert [c['passed'] for c in checks]==[True,False] and [c['exit_code'] for c in checks]==[0,1]
    assert diagnostics==['q2_min_eligible_groups_not_met'] and warnings==[]


@pytest.mark.parametrize('case',['missing','closed-invalid','forged-positive','synthetic-positive'])
def test_candidate_without_producer_cannot_admit_a_forged_pass(tmp_path,monkeypatch,case):
    import test_release_grade_candidate_evidence_path_v0 as old
    repo=old._bootstrap_repo(tmp_path,required_gate='q2_consistency_ok')
    candidate=module_at('q2_candidate_bypass',TOOLS/'build_release_grade_candidate_status_v0.py')
    path=repo/'PULSE_safe_pack_v0/artifacts/required_gate_inputs/q2_consistency_ok.json'
    result=json.loads(path.read_bytes());assert result['pass'] is True and result['diagnostics']==[]
    record=LOAD.empty_result(LOAD.load_profile(repo));record['diagnostics']=['q2_request_missing']
    if case in ('forged-positive','synthetic-positive'):
        from test_q2_release_intake_v0 import synthetic_case,run_case
        synthetic=run_case(synthetic_case(tmp_path/'positive',True),'admission')
        synthetic['cleanup']='verified_removed'
        record.update(input_valid=True,metric_pass=True,process_exit=0,checks={k:True for k in record['checks']},
                      cleanup='verified_removed',request_sha256='a'*64,
                      evaluation_binding={**metadata_request()['evaluation_identity'],'workflow_sha':'a'*40,
                                          'run_id':'80000000003','run_attempt':1,'request_sha256':'a'*64},
                      release_artifact=metadata_request()['release_subject'],metrics=synthetic['metrics'],
                      replay_environment=synthetic['replay_environment'],diagnostics=[])
        if case=='synthetic-positive':record['record_status']='synthetic_fixture'
    if case!='missing':
        support=repo/IO.PUBLIC_RESULT;support.write_bytes(IO.encode(record))
        IO.validate(record,IO.read_file(repo/IO.RESULT_SCHEMA,128*1024))
        result['input_artifacts'].append(old._artifact_ref(repo,IO.PUBLIC_RESULT,'q2_intake_metadata','q2_release_intake_result_v0'))
        path.write_bytes(IO.encode(result))
    calls=[];real_consume=LOAD.consume
    def independent(*args,**kwargs):
        calls.append(kwargs['consumer'])
        return real_consume(*args,**{**kwargs,'environment':{}})
    monkeypatch.setattr(LOAD,'consume',independent)
    errors=[]
    candidate._verify_result(repo=repo,gate='q2_consistency_ok',evaluation_id=result['evaluation_id'],result_path=path,
        result_schema=json.loads((repo/'schemas/required_gate_evaluation_result_v0.schema.json').read_bytes()),
        run_identity=result['run_identity'],subject=result['subject'],
        policy_sha=result['policy_binding']['policy_sha256'],registry_sha=result['registry_binding']['registry_sha256'],
        plan_sha=result['plan_binding']['plan_sha256'],errors=errors)
    assert errors==['q2_consistency_ok: q2_admission_rejected']
    assert calls==([] if case=='missing' else ['admission'])


@pytest.mark.parametrize('termination',['timeout','sigterm'])
def test_actual_private_process_cleanup_and_suppressed_output(tmp_path,termination):
    repo=tmp_path/'repo';repo.mkdir();marker=tmp_path/'private-path'
    script=tmp_path/'supervisor.py'
    script.write_text('''import sys, pathlib
sys.path.insert(0, sys.argv[1])
import q2_intake_io_v0 as io
repo, parent, marker = map(pathlib.Path, sys.argv[2:])
try:
    with io.interrupt_boundary(2):
        with io.private_workspace(repo, parent) as work:
            marker.write_text(str(work['path']))
            io.write_new(work['path']/'raw', b'PRIVATE_RAW_RESPONSE')
            io.private_process([sys.executable, '-c', "import time;print('PRIVATE_CREDENTIAL',flush=True);time.sleep(20)"],
                cwd=work['path'], environment=io.replay_environment(work['path']),timeout=15,new_session=True)
except io.IntakeError as exc:
    print(exc.code)
''')
    p=subprocess.Popen([sys.executable,'-I','-B',str(script),str(TOOLS),str(repo),str(tmp_path),str(marker)],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin'})
    if termination=='sigterm':
        end=time.monotonic()+5
        while not marker.exists() and time.monotonic()<end:time.sleep(.01)
        assert marker.exists();p.send_signal(signal.SIGTERM)
    stdout,stderr=p.communicate(timeout=10)
    assert stdout==b'q2_timeout\n' and stderr==b''
    assert not Path(marker.read_text()).exists()


def test_minimal_semantic_environment_has_no_transport_or_generic_credentials(tmp_path):
    env=IO.replay_environment(tmp_path)
    code="import os,sys;assert not any('TOKEN' in k or k.startswith('PULSE_Q2_') for k in os.environ);sys.exit(0)"
    assert IO.private_process([sys.executable,'-I','-B','-c',code],cwd=tmp_path,environment=env,timeout=5)==0


def test_actual_generic_runner_child_receives_no_q2_transport_context(tmp_path):
    import test_release_grade_candidate_evidence_path_v0 as old
    repo=old._bootstrap_repo(tmp_path)
    dispatcher=repo/IO.PACK/'tools/evaluate_required_gate_v0.py'
    source=dispatcher.read_text();marker='from __future__ import annotations\n'
    assert source.count(marker)==1
    source=source.replace(marker,marker+'''import os as _probe_os, json as _probe_json
from pathlib import Path as _ProbePath
_ProbePath('generic-child-context.json').write_text(_probe_json.dumps({k:v for k,v in _probe_os.environ.items() if k.startswith('PULSE_Q2_')}))
''');dispatcher.write_text(source)
    env={**old._base_env(),LOAD.REQUEST_ENV:'PRIVATE_REQUEST_DATA',LOAD.DIGEST_ENV:'a'*64,
         LOAD.TOKEN_ENV:'PRIVATE_TRANSPORT_TOKEN','PULSE_Q2_FUTURE_FIELD':'PRIVATE_EXTRA'}
    # The q1 fixture is intentionally incomplete; only environment isolation is
    # asserted here. All six real recipes are covered by the whole policy test.
    result=old._run_tool(repo,IO.PACK+'tools/run_recorded_required_gate_evaluations_v0.py',
                         '--repo-root',str(repo),'--run-key',old.RUN_KEY,'--git-sha',old.GIT_SHA,env=env)
    assert result.returncode!=0
    assert json.loads((repo/'generic-child-context.json').read_text())=={}
    assert 'PRIVATE_' not in result.stdout+result.stderr



@pytest.mark.parametrize('role',['runner','dispatcher','candidate'])
def test_actual_parent_schema_checks_receive_no_q2_environment(tmp_path,role):
    import test_release_grade_candidate_evidence_path_v0 as old
    repo=old._bootstrap_repo(tmp_path)
    filenames={'runner':'run_recorded_required_gate_evaluations_v0.py',
               'dispatcher':'evaluate_required_gate_v0.py',
               'candidate':'build_release_grade_candidate_status_v0.py'}
    relative=IO.PACK+'tools/'+filenames[role];path=repo/relative
    source=path.read_text();needle='    validator = Draft202012Validator(\n'
    assert source.count(needle)==1
    source=source.replace(needle,"    Path('schema-environment.json').write_text(json.dumps({k:v for k,v in os.environ.items() if k.startswith('PULSE_Q2_')}))\n"+needle)
    path.write_text(source)
    env={**old._base_env(),LOAD.REQUEST_ENV:'PRIVATE_REQUEST_DATA',LOAD.DIGEST_ENV:'a'*64,
         LOAD.TOKEN_ENV:'PRIVATE_TRANSPORT_TOKEN','PULSE_Q2_FUTURE_FIELD':'PRIVATE_EXTRA'}
    args=['--repo-root',str(repo)]
    if role=='runner':args+=['--run-key',old.RUN_KEY,'--git-sha',old.GIT_SHA]
    if role=='dispatcher':
        env.update(PULSE_REQUIRED_GATE_ID='q1_grounded_ok',PULSE_REQUIRED_GATE_EVALUATION_ID='pulse.required.q1_grounded_ok.v0')
        args+=['--gate-id','q1_grounded_ok','--out','PULSE_safe_pack_v0/artifacts/required_gate_inputs/q1_grounded_ok.json']
    process=old._run_tool(repo,relative,*args,env=env)
    assert (repo/'schema-environment.json').is_file(),(process.returncode,process.stderr)
    assert json.loads((repo/'schema-environment.json').read_bytes())=={}
    assert 'PRIVATE_' not in process.stdout+process.stderr


def test_direct_admission_quarantines_credentials_before_public_schema(tmp_path,monkeypatch):
    from test_q2_release_intake_v0 import ADMISSION
    profile=LOAD.load_profile(ROOT);record=LOAD.empty_result(profile);record['diagnostics']=['q2_request_missing']
    public=tmp_path/'closed.json';public.write_bytes(IO.encode(record));seen=[];real_validate=IO.validate
    def schema(value,raw):
        seen.append(True)
        assert not any(k.startswith('PULSE_Q2_') for k in os.environ)
        return real_validate(value,raw)
    def consume(repo,*,consumer,environment):
        assert consumer=='admission' and environment[LOAD.TOKEN_ENV]=='PRIVATE_TRANSPORT'
        return record
    monkeypatch.setenv(LOAD.TOKEN_ENV,'PRIVATE_TRANSPORT');monkeypatch.setattr(IO,'validate',schema)
    monkeypatch.setattr(LOAD,'consume',consume)
    with pytest.raises(IO.IntakeError,match='q2_admission_rejected'):
        ADMISSION.admit(ROOT,public,{}, {})
    assert seen==[True] and LOAD.TOKEN_ENV not in os.environ


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
