"""Synthetic protocol and real-pipe tests; never actual model inference/systemd."""
import ast
import contextlib
import copy
import errno
import io
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import pytest
from test_q3_native_capture_contract_v0 import ROOT, TOOLS, C, module, offline

W=module('run_q3_reference_subject_v0')
R=module('q3_native_runtime_v0')
P=C.load_profile(ROOT)
FRAME=C.task_frame(ROOT,P)

class Tokenizer:
    is_fast=True
    bos_token_id=1; eos_token_id=2; pad_token_id=2
    def __init__(self,length=7):self.length=length;self.calls=[]
    def apply_chat_template(self,messages,**kw):
        assert kw==dict(tokenize=True,add_generation_prompt=True,truncation=False)
        self.calls.append(copy.deepcopy(messages))
        return [1]+[4]*(self.length-1)
    def decode(self,ids,**kw):
        assert kw==dict(skip_special_tokens=True,clean_up_tokenization_spaces=False)
        return '' if ids==[2] else 'synthetic response'

class Tensor:
    def __init__(self,rows):self.rows=copy.deepcopy(rows);self.shape=(len(rows),len(rows[0]))
    def __getitem__(self,i):return types.SimpleNamespace(tolist=lambda:list(self.rows[i]))

class Torch:
    long='synthetic-long'
    def __init__(self):self.tensors=[];self.seeds=[]
    def tensor(self,rows,**kw):
        assert kw==dict(dtype=self.long,device='cpu')
        value=Tensor(rows);self.tensors.append(value);return value
    def ones_like(self,tensor):return Tensor([[1]*tensor.shape[1]])
    def manual_seed(self,seed):self.seeds.append(seed)
    def inference_mode(self):return contextlib.nullcontext()

class Config:
    def __init__(self,**kw):self.value=kw
    def to_dict(self):return copy.deepcopy(self.value)

class Model:
    def __init__(self,new=None):self.new=[4,2] if new is None else new;self.calls=[]
    def generate(self,**kwargs):
        assert set(kwargs)=={'input_ids','attention_mask','generation_config','use_model_defaults'}
        assert kwargs['use_model_defaults'] is False
        self.calls.append(kwargs)
        return Tensor([kwargs['input_ids'][0].tolist()+self.new])


def commands(rows):
    for row in rows:
        for op in ['PREPARE','GENERATE']:yield (op+' '+row['task_id']+'\n').encode()
    yield b'FINISH\n'


def session(new=None,mutate_command=None,rows=None,tokenizer=None,effective=None):
    tok=tokenizer or Tokenizer();mapping=W.tokenize_frame(tok,FRAME,P)
    if rows is not None:mapping['rows']=mapping['rows'][:rows]
    cmds=list(commands(mapping['rows']))
    if mutate_command:mutate_command(cmds)
    model=Model(new);torch=Torch();emitted=[];stream=iter(cmds)
    args=(model,tok,torch,Config,effective or {**P['generation'],'disable_compile':True},
          {'synthetic':True},mapping,P,{'synthetic_binding':True},lambda:next(stream,b''),emitted.append)
    return args,model,torch,emitted,mapping


def test_all_204_tokenized_before_any_generation_and_no_truncation():
    tok=Tokenizer();mapping=W.tokenize_frame(tok,FRAME,P)
    assert len(tok.calls)==len(mapping['rows'])==204
    assert tok.calls==[t['messages'] for t in FRAME]
    assert [r['ordinal'] for r in mapping['rows']]==list(range(1,205))

@pytest.mark.parametrize('length',[0,7937,8192])
def test_prompt_overflow_rejected_without_shortening(length):
    tok=Tokenizer(length)
    if length==0:tok.apply_chat_template=lambda *a,**k:[]
    with pytest.raises(ValueError):W.tokenize_frame(tok,FRAME,P)

@pytest.mark.parametrize('value',[[True],[49152],[-1],None,'1',[1.0]])
def test_invalid_token_array_rejected(value):
    tok=Tokenizer();tok.apply_chat_template=lambda *a,**k:value
    with pytest.raises(ValueError):W.tokenize_frame(tok,FRAME,P)


def test_full_synthetic_204_protocol_fresh_tensors_and_exact_order():
    args,model,torch,wire,mapping=session();W.capture_session(*args)
    assert len(model.calls)==len(torch.tensors)==204
    assert len({id(t) for t in torch.tensors})==204
    assert torch.seeds==[1729]*204
    records=[C.strict_json(b) for b in wire]
    assert len(records)==409
    assert [r['slot']['task_id'] for r in records if r['record_type']=='q3_response_v0']==[r['task_id'] for r in mapping['rows']]
    assert records[-1]['completed_calls']==204

@pytest.mark.parametrize('fault',['missing_prepare','wrong_task','early_generate','missing_go','extra_go','missing_finish'])
def test_protocol_rejects_missing_or_reordered_control(fault):
    def change(cmd):
        if fault=='missing_prepare':cmd[0]=b''
        elif fault=='wrong_task':cmd[0]=b'PREPARE foreign\n'
        elif fault=='early_generate':cmd[0]=cmd[1]
        elif fault=='missing_go':cmd[1]=b''
        elif fault=='extra_go':cmd[2]=cmd[1]
        elif fault=='missing_finish':cmd[-1]=b''
    args,model,torch,wire,mapping=session(mutate_command=change)
    with pytest.raises(ValueError):W.capture_session(*args)
    assert not any(C.strict_json(x)['record_type']=='q3_session_end_v0' for x in wire)
    if fault in ('missing_prepare','wrong_task','early_generate','missing_go'):assert model.calls==[]
    if fault=='extra_go':assert len(model.calls)==1


def test_length_termination_is_retained_and_stops_before_second_go():
    args,model,torch,wire,mapping=session(new=[4]*256)
    with pytest.raises(ValueError,match='TOKEN_LIMIT'):W.capture_session(*args)
    assert len(model.calls)==1 and len(wire)==2
    r=C.strict_json(wire[-1]);assert r['stop_reason']=='token_limit' and len(r['new_token_ids'])==256


def test_genuine_empty_decoded_response_is_not_fabricated_transport_error():
    args,model,torch,wire,mapping=session(new=[2],rows=1);W.capture_session(*args)
    assert C.strict_json(wire[1])['text']=='' and len(model.calls)==1

@pytest.mark.parametrize('new',[[],[4],[2,4],[2,2],[49152,2],[-1,2],[True,2],[4]*257])
def test_invalid_generation_is_not_completed(new):
    args,model,torch,wire,mapping=session(new=new)
    with pytest.raises(ValueError):W.capture_session(*args)
    assert len(model.calls)==1 and len(wire)==1


def test_prefix_substitution_rejected():
    with pytest.raises(ValueError,match='PREFIX'):W.continuation([1,4],[1,5,2],256)


def test_generation_config_drift_prevents_generate():
    args,model,torch,wire,mapping=session(effective={'wrong':True})
    with pytest.raises(ValueError,match='CONFIGURATION'):W.capture_session(*args)
    assert not model.calls


def pipe_child(code,**limits):
    proc=subprocess.Popen([sys.executable,'-I','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return proc,R.BoundedReader(proc.stdout,**limits)


def finish_child(proc,reader):
    reader.close()
    if proc.poll() is None:proc.kill()
    proc.communicate(timeout=3)


def test_bounded_reader_real_child_frames_and_eof():
    proc,rd=pipe_child("import os;os.write(1,b'first\\nsecond\\n')")
    try:
        deadline=time.monotonic()+3
        assert rd.line(deadline)==b'first\n' and rd.line(deadline)==b'second\n'
        assert rd.finish(deadline)==b'' and rd.eof
    finally:finish_child(proc,rd)

@pytest.mark.parametrize('kind',['partial','frame','total','tail'])
def test_bounded_reader_real_child_rejects_partial_oversized_and_extra(kind):
    payload={'partial':b'no LF','frame':b'0123456789\n','total':b'1\n2\n3\n','tail':b'ok\nextra'}[kind]
    proc,rd=pipe_child('import os;os.write(1,'+repr(payload)+')',frame_limit=5 if kind=='frame' else 100,total_limit=4 if kind=='total' else 100)
    try:
        if kind=='tail':
            assert rd.line(time.monotonic()+3)==b'ok\n';assert rd.finish(time.monotonic()+3)==b'extra'
        else:
            with pytest.raises(ValueError):rd.line(time.monotonic()+3)
    finally:finish_child(proc,rd)


def test_bounded_reader_absolute_deadline_without_output():
    proc,rd=pipe_child('import time;time.sleep(10)')
    try:
        with pytest.raises(ValueError,match='deadline'):rd.line(time.monotonic()+.05)
    finally:finish_child(proc,rd)


def test_lifecycle_registers_service_before_failed_launch(tmp_path,monkeypatch):
    life=R.Lifecycle()
    def failure(s):assert life.services==[s];raise OSError(errno.EMFILE,'synthetic')
    monkeypatch.setattr(R.Service,'start',failure)
    with pytest.raises(OSError):life.start('pulse-q3-'+'a'*24,'preflight',[],tmp_path,Path(sys.executable),tmp_path/'log',time.monotonic()+30)
    assert len(life.services)==1


def test_timer_registration_survives_arm_failure(monkeypatch):
    life=R.Lifecycle();prefix='pulse-q3-'+'a'*24+'-call-001'
    def fail(*a,**k):assert prefix in life.timers;raise OSError('synthetic')
    monkeypatch.setattr(R,'control',fail)
    with pytest.raises(OSError):life.arm(prefix,'pulse-q3-'+'a'*24+'-captureworker.service')
    result=life.cleanup();assert result['cleanup_complete'] is False


def test_cleanup_single_shared_deadline_and_primary_obligation(monkeypatch):
    life=R.Lifecycle();seen=[]
    class S:
        cleanup=None
        def close(self,deadline):seen.append(deadline);raise OSError('synthetic')
    life.services=[S(),S()]
    result=life.cleanup();again=life.cleanup()
    assert not result['cleanup_complete'] and len(set(seen))==1 and not again['cleanup_complete']

@pytest.mark.parametrize('stage',['installer','installcheck','preflight','decodecheck','captureworker'])
def test_service_command_has_external_barrier_and_fixed_isolation(tmp_path,stage):
    unit='pulse-q3-'+'a'*24+'-'+stage+'.service'
    cmd=R.service_command(unit,stage,['/fixed/python','-I','fixed.py'],tmp_path,Path(sys.executable),
                          **({'capture_seconds':100} if stage=='captureworker' else {}))
    assert '--property=PrivateNetwork=yes' in cmd and '--property=User=65534' in cmd
    assert '--property=MemoryMax=4294967296' in cmd and '--property=NoNewPrivileges=yes' in cmd
    assert R.BARRIER in cmd and 'GITHUB_TOKEN' not in ' '.join(cmd)


def test_native_entry_rejects_current_non_native_test_host_before_model_load(tmp_path):
    proc=subprocess.run([sys.executable,'-I','-B',str(TOOLS/'run_q3_reference_subject_v0.py'),
        '--source-root',str(ROOT),'--bundle',str(tmp_path),'--prelaunch',str(tmp_path/'missing'),
        '--expected-prelaunch-sha256','0'*64],capture_output=True,timeout=5)
    assert proc.returncode==2 and not list(tmp_path.iterdir())


def test_no_generation_import_at_top_level_and_checker_has_no_generate_call():
    for path in [TOOLS/'run_q3_reference_subject_v0.py',TOOLS/'acquire_q3_reference_inputs_v0.py',TOOLS/'check_q3_native_capture_v0.py']:
        tree=ast.parse(path.read_text())
        for n in tree.body:
            if isinstance(n,ast.Import):assert all(a.name not in ('torch','transformers') for a in n.names)
            if isinstance(n,ast.ImportFrom):assert n.module not in ('torch','transformers')
        if path.name.startswith('check_'):
            assert not [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate']
            assert 'AutoModelForCausalLM' not in path.read_text()

@pytest.mark.parametrize('mode',['token-preflight','capture_wrong_map','capture_missing_load'])
def test_actual_worker_branch_with_explicit_runtime_doubles_never_generates(tmp_path,monkeypatch,mode):
    # No target dependency import: only the platform and tokenizer seam are replaced.
    from test_q3_native_capture_v0 import evidence
    source,data,r=evidence('token-preflight' if mode=='token-preflight' else 'capture')
    pre=C.strict_json(data['prelaunch.json'])
    if mode=='capture_wrong_map':pre['request']['approved_token_map_sha256']='0'*64
    raw=C.encode(pre);path=tmp_path/'prelaunch.json';path.write_bytes(raw)
    out=io.BytesIO();inp=io.BytesIO(b'TOKENIZE\nFINISH\n' if mode=='token-preflight' else b'TOKENIZE\n')
    with monkeypatch.context() as m:
        m.setattr(W.platform,'python_implementation',lambda:'CPython');m.setattr(W.platform,'python_version',lambda:'3.11.16')
        m.setattr(W.platform,'system',lambda:'Linux');m.setattr(W.platform,'machine',lambda:'x86_64')
        m.setattr(W.platform,'freedesktop_os_release',lambda:{'ID':'ubuntu','VERSION_ID':'24.04'})
        m.setattr(W.os,'getuid',lambda:65534);m.setattr(W.sys,'prefix','synthetic-not-real-venv')
        m.setattr(W.sys,'flags',types.SimpleNamespace(isolated=1))
        m.setattr(W.sys,'stdin',types.SimpleNamespace(buffer=inp));m.setattr(W.sys,'stdout',types.SimpleNamespace(buffer=out))
        m.setattr(W,'load_tokenizer',lambda *a:Tokenizer())
        m.setattr(W,'load_model',lambda *a:pytest.fail('model load before capture boundary'))
        if mode=='token-preflight':assert W.run(ROOT,tmp_path,path,C.digest(raw))==0
        else:
            with pytest.raises(ValueError):W.run(ROOT,tmp_path,path,C.digest(raw))
    rows=[C.strict_json(x) for x in out.getvalue().splitlines()]
    assert len([x for x in rows if x['record_type']=='q3_token_row_v0'])==204
    assert not [x for x in rows if x['record_type']=='q3_response_v0']
    if mode=='token-preflight':assert rows[-1]['completed_calls']==0


def test_complete_supervisor_exchange_with_real_synthetic_child(tmp_path):
    # The real controller/pipe framing exchanges all 204 slots. Model/tokenizer and
    # external timers are explicit test doubles; no systemd or model code executes.
    from test_q3_native_capture_v0 import A,K
    mapping=W.tokenize_frame(Tokenizer(),FRAME,P);binding={'synthetic':'test-only'}
    child=r'''
import sys,types,importlib.util
sys.path.insert(0,sys.argv[1])
from test_q3_native_capture_protocol_v0 import W,C,P,FRAME,Tokenizer,Model,Torch,Config
from test_q3_native_capture_v0 import K
mapping=W.tokenize_frame(Tokenizer(),FRAME,P);binding={'synthetic':'test-only'}
def emit(raw):sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
def read():return sys.stdin.buffer.readline(512)
assert read()==('LOAD '+C.digest(C.encode(mapping))+'\n').encode()
effective={**P['generation'],'disable_compile':True};runtime=K.expected_runtime(P)
ready=C.encode({'record_type':'q3_model_ready_v0','binding':binding,'token_map_sha256':C.digest(C.encode(mapping)),
                'effective_generation':effective,'runtime':runtime})
emit(ready)
subject={'record_type':'q3_capture_subject_v0','binding':binding,'model_ready_sha256':C.digest(ready),'token_map_sha256':C.digest(C.encode(mapping))}
ss=C.digest(C.encode(subject));assert read()==('BIND '+ss+'\n').encode()
binding={**binding,'subject_sha256':ss};emit(C.encode({'record_type':'q3_bound_v0','binding':binding}))
model=Model();W.capture_session(model,Tokenizer(),Torch(),Config,effective,runtime,mapping,P,binding,read,emit)
assert len(model.calls)==204
'''
    proc=subprocess.Popen([sys.executable,'-I','-B','-c',child,str(ROOT/'tests')],stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    class S:
        def __init__(self):
            self.reader=R.BoundedReader(proc.stdout);self.deadline=time.monotonic()+300
            self.runtime_deadline_ns=int(self.deadline*1e9);self.unit='synthetic-worker-no-systemd'
        def send(self,raw):
            start=time.monotonic_ns();os.write(proc.stdin.fileno(),raw);return start
    class L:
        def __init__(self):self.armed=[];self.closed=[]
        def arm(self,prefix,unit):assert len(self.armed)==len(self.closed);self.armed.append(prefix)
        def disarm(self,prefix,deadline):assert self.armed[-1]==prefix;self.closed.append(prefix);return {'closed_ns':time.monotonic_ns()}
    svc=S();life=L();terminal={'attempted_calls':0,'occurrences':[{'task_id':t['task_id'],'ordinal':t['ordinal'],'attempt':1,'status':'not_started'} for t in FRAME]}
    try:
        A.exchange_capture(C,R,life,svc,P,FRAME,mapping,binding,tmp_path,terminal,'synthetic')
        assert svc.reader.finish(svc.deadline)==b''
        assert proc.wait(timeout=3)==0,proc.stderr.read().decode()
        assert terminal['attempted_calls']==204 and len(life.armed)==len(life.closed)==204
        assert all(x['status']=='completed' for x in terminal['occurrences'])
        assert len(list((tmp_path/'calls').glob('*.response.json')))==204
    finally:
        svc.reader.close()
        if proc.poll() is None:proc.kill()
        proc.communicate(timeout=3)


def test_unknown_client_launch_identity_never_claims_reaped(tmp_path,monkeypatch):
    svc=R.Service('pulse-q3-'+'a'*24,'preflight',[],tmp_path,Path(sys.executable),tmp_path/'log',time.monotonic()+30)
    svc.launch_attempted=True
    monkeypatch.setattr(R,'control',lambda *a,**k:subprocess.CompletedProcess(a[0],0,
        b'LoadState=not-found\nActiveState=inactive\nControlGroup=\n',b''))
    with pytest.raises(ValueError,match='client_launch'):svc.close(time.monotonic()+5)
    assert svc.cleanup is None


@pytest.fixture
def phase_pipe(tmp_path, monkeypatch):
    """Real phase/reader/EOF/exit checks; launch and cleanup are test doubles."""
    class PipeService(R.Service):
        def start(self):
            self.process = subprocess.Popen(
                self.command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0)
            self.reader = R.BoundedReader(self.process.stdout)
            self.observation = {'synthetic_pipe_test': True, 'stage': self.stage}
            self.closed_by_phase = False
            return self

        def close(self, deadline):
            self.closed_by_phase = True
            finish_child(self.process, self.reader)
            if close_error[0] is not None:
                raise close_error[0]
            self.cleanup = {'synthetic_pipe_cleanup': True}
            return self.cleanup

    monkeypatch.setattr(R, 'Service', PipeService)
    life = R.Lifecycle()
    close_error = [None]
    logs = tmp_path / 'logs'; logs.mkdir()
    evidence_dir = tmp_path / 'evidence'; evidence_dir.mkdir()
    work = tmp_path / 'work'; work.mkdir()

    def invoke(stage, code, *, seconds=5, args=(), cleanup_error=None):
        close_error[0] = cleanup_error
        return R.phase(
            life, 'pulse-q3-' + 'a' * 24, stage,
            [sys.executable, '-I', '-B', '-c', code, *map(str, args)],
            work, Path(sys.executable), logs, time.monotonic() + seconds,
            evidence_dir)

    invoke.life = life
    invoke.work = work
    invoke.evidence = evidence_dir
    yield invoke
    # An assertion failure in the test must not leave the synthetic child alive.
    for svc in life.services:
        if svc.process is not None and not svc.closed_by_phase:
            finish_child(svc.process, svc.reader)


def test_phase_accepts_actual_installer_acknowledgement_before_eof(phase_pipe):
    # Execute the unchanged INSTALLER body in a child, but replace venv/pip only.
    # Its real success print reaches the real BoundedReader and Service.complete.
    # No dependency installation, systemd service or model execution occurs.
    out = phase_pipe.work / 'installer-output'; out.mkdir()
    driver = r'''
import pathlib, subprocess, sys, venv
class SyntheticEnvBuilder:
    def __init__(self, **kwargs):
        assert kwargs == {'with_pip': True, 'symlinks': False}
    def create(self, path):
        path.mkdir()
        (path / 'synthetic-fixture.txt').write_bytes(b'not a runtime\n')
venv.EnvBuilder = SyntheticEnvBuilder
calls = []
def fake_run(command, **kwargs):
    calls.append(command)
    assert 'pip' in command or 'import importlib.metadata' in command[-1]
    return subprocess.CompletedProcess(command, 0)
subprocess.run = fake_run
'''
    driver += '\nexec(compile(' + repr(R.INSTALLER) + ", '<actual-installer-body>', 'exec'))\n"
    driver += 'assert len(calls) == 3\n'
    svc = phase_pipe('installer', driver, args=(
        phase_pipe.work, phase_pipe.work / 'wheelhouse',
        phase_pipe.work / 'runtime.lock', out))
    assert svc.process.returncode == 0 and svc.reader.eof
    assert svc.closed_by_phase and svc.cleanup == {'synthetic_pipe_cleanup': True}
    assert C.strict_json((phase_pipe.evidence / 'installer-sandbox.json').read_bytes()) == svc.observation
    assert C.strict_json((phase_pipe.evidence / 'installer-cleanup.json').read_bytes()) == svc.cleanup
    assert (out / 'bootstrap.json').is_file()


@pytest.mark.parametrize('payload,exit_code,expected', [
    (b'', 0, 'unexpected_protocol_eof'),
    (b'offline_installation_finished', 0, 'unexpected_protocol_eof'),
    (b'offline_installation_failed\n', 0, 'installer_acknowledgement'),
    (b'offline_installation_finished\r\n', 0, 'installer_acknowledgement'),
    (b'offline_installation_finished \n', 0, 'installer_acknowledgement'),
    (b'offline_installation_finished\noffline_installation_finished\n', 0, 'extra_worker_output'),
    (b'offline_installation_finished\nextra', 0, 'extra_worker_output'),
    (b'offline_installation_finished\n', 72, 'isolated_service_failed'),
])
def test_phase_installer_acknowledgement_rejects_invalid_completion(
        phase_pipe, payload, exit_code, expected):
    code = 'import os;os.write(1,' + repr(payload) + ');os._exit(' + str(exit_code) + ')'
    with pytest.raises(ValueError, match=expected):
        phase_pipe('installer', code)
    svc = phase_pipe.life.services[0]
    assert svc.closed_by_phase and svc.process.poll() is not None
    assert (phase_pipe.evidence / 'installer-cleanup.json').is_file()


@pytest.mark.parametrize('stage', ['installcheck', 'preflight', 'decodecheck'])
@pytest.mark.parametrize('payload', [b'', b'offline_installation_finished\n'])
def test_phase_installer_acknowledgement_is_not_allowed_in_other_phases(
        phase_pipe, stage, payload):
    code = 'import os;os.write(1,' + repr(payload) + ')'
    if payload:
        with pytest.raises(ValueError, match='extra_worker_output'):
            phase_pipe(stage, code)
    else:
        assert phase_pipe(stage, code).process.returncode == 0
    assert phase_pipe.life.services[0].closed_by_phase


@pytest.mark.parametrize('payload', [b'', b'offline_installation_finished\n'])
def test_phase_installer_acknowledgement_does_not_extend_deadline(phase_pipe, payload):
    code = 'import os,time;os.write(1,' + repr(payload) + ');time.sleep(30)'
    with pytest.raises(ValueError, match='external_deadline_expired'):
        phase_pipe('installer', code, seconds=0.3)
    svc = phase_pipe.life.services[0]
    assert svc.closed_by_phase and svc.process.poll() is not None


@pytest.mark.parametrize('payload,expected', [
    (b'offline_installation_finished\n', 'synthetic_cleanup_failure'),
    (b'wrong_ack\n', 'installer_acknowledgement'),
])
def test_phase_installer_acknowledgement_keeps_cleanup_failure_semantics(
        phase_pipe, payload, expected):
    code = 'import os;os.write(1,' + repr(payload) + ')'
    with pytest.raises(Exception, match=expected):
        phase_pipe('installer', code, cleanup_error=OSError('synthetic_cleanup_failure'))
    assert phase_pipe.life.services[0].closed_by_phase
    assert not (phase_pipe.evidence / 'installer-cleanup.json').exists()


@pytest.mark.parametrize('interruption', [OSError('synthetic_read_failure'), KeyboardInterrupt()])
def test_phase_installer_acknowledgement_read_failure_still_closes(
        phase_pipe, monkeypatch, interruption):
    def fail_read(self, deadline):
        raise interruption
    monkeypatch.setattr(R.BoundedReader, 'line', fail_read)
    with pytest.raises(type(interruption)) as caught:
        phase_pipe('installer', 'import time;time.sleep(30)')
    assert caught.value is interruption
    assert phase_pipe.life.services[0].closed_by_phase
