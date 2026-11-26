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
    # The transport fixture has an explicitly configured synthetic controller;
    # bind the worker to those exact source bytes, not inactive production ROOT.
    source_root=tmp_path/'synthetic-source'
    for name,body in source.items():
        target=source_root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
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
        if mode=='token-preflight':assert W.run(source_root,tmp_path,path,C.digest(raw))==0
        else:
            with pytest.raises(ValueError):W.run(source_root,tmp_path,path,C.digest(raw))
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


def cleanup_show(values, returncode=0):
    raw = ''.join(key + '=' + value + '\n' for key, value in values.items()).encode()
    return subprocess.CompletedProcess(['synthetic-systemctl-show'], returncode, raw, b'')


@pytest.fixture
def cleanup_service(tmp_path, monkeypatch):
    """Exercise real cleanup logic with a fake client, systemctl and cgroup tree."""
    calls = []; events = []

    class Client:
        pid = 987654321
        returncode = 2
        running = False
        wait_error = None
        waited = False

        def __init__(self):
            self.stdin = io.BytesIO(); self.stdout = io.BytesIO()

        def poll(self):
            return None if self.running else self.returncode

        def wait(self, *, timeout):
            assert 0 < timeout <= 5
            events.append('reap_client'); self.waited = True
            if self.wait_error is not None:
                raise self.wait_error
            return self.returncode

    svc = R.Service('pulse-q3-' + 'a' * 24, 'captureworker', [], tmp_path,
                    Path(sys.executable), tmp_path / 'unused.log', time.monotonic() + 30)
    svc.launch_attempted = True; svc.process = Client()
    svc.reader = io.BytesIO(); svc.log = io.BytesIO()
    cgroups = tmp_path / 'cgroups'; cgroups.mkdir()
    cg = cgroups / svc.unit; cg.mkdir()
    (cg / 'cgroup.events').write_bytes(b'populated 0\nfrozen 0\n')
    (cg / 'cgroup.procs').write_bytes(b'')
    monkeypatch.setattr(R, 'CLEANUP_CGROUP_ROOT', cgroups)
    initial = {'LoadState': 'loaded', 'ActiveState': 'failed',
               'ControlGroup': '/system.slice/' + svc.unit,
               'MainPID': '0', 'ControlPID': '0', 'Job': ''}
    final = {**initial, 'ActiveState': 'inactive'}
    fixture = types.SimpleNamespace(service=svc, client=svc.process, cg=cg,
        initial=initial, final=final, calls=calls, events=events,
        replies=None, command_results={}, on_reset=None, show_count=0)

    def control(command, *, timeout=15, check=True):
        assert command[0] == '/usr/bin/systemctl' and check is False
        assert 0 < timeout <= 10
        operation = command[1]
        assert operation in ('kill', 'stop', 'show', 'reset-failed')
        assert svc.unit in command
        calls.append(list(command)); events.append(operation)
        if operation == 'show':
            assert '--all' in command and '--no-pager' in command
            assert '--property=' + ','.join(R.CLEANUP_SHOW_FIELDS) in command
            index = fixture.show_count; fixture.show_count += 1
            if fixture.replies is not None:
                assert index < len(fixture.replies), 'unexpected additional observation'
                reply = fixture.replies[index]
                if isinstance(reply, BaseException):
                    raise reply
                return reply
            return cleanup_show(fixture.initial if index == 0 else fixture.final)
        if operation == 'reset-failed' and fixture.on_reset is not None:
            fixture.on_reset()
        result = fixture.command_results.get(operation, 0)
        if isinstance(result, BaseException):
            raise result
        return subprocess.CompletedProcess(command, result, b'', b'')

    def killpg(pid, sig):
        assert pid == fixture.client.pid and sig == R.signal.SIGKILL
        events.append('kill_client_group')

    monkeypatch.setattr(R, 'control', control)
    monkeypatch.setattr(R.os, 'killpg', killpg)
    life = R.Lifecycle(); life.services.append(svc); fixture.life = life
    return fixture


@pytest.mark.parametrize('final_load', ['loaded', 'not-found'])
@pytest.mark.parametrize('cgroup_present', [True, False])
def test_failed_quiescent_service_resets_once_and_keeps_complete_shapes(
        cleanup_service, final_load, cgroup_present):
    f = cleanup_service; svc = f.service
    f.final.update(LoadState=final_load, ControlGroup='')
    if not cgroup_present:
        (f.cg / 'cgroup.events').unlink(); (f.cg / 'cgroup.procs').unlink(); f.cg.rmdir()

    def verify_before_reset():
        assert f.client.waited and f.client.poll() is not None
        notes = svc.cleanup_details
        observed = next(n['properties'] for n in notes if 'properties' in n)
        assert observed['MainPID'] == observed['ControlPID'] == '0' and observed['Job'] == ''
        assert any(n['step'] == 'cgroup_before_reset' and n['cgroup']['state'] in (
            'unpopulated', 'absent') for n in notes)

    f.on_reset = verify_before_reset
    result = f.life.cleanup()
    assert result == {'cleanup_complete': True, 'errors': [],
                      'services': [svc.cleanup], 'timers': []}
    assert svc.cleanup == {'unit': svc.unit, 'launch_attempted': True,
        'properties': {'LoadState': final_load, 'ActiveState': 'inactive', 'ControlGroup': ''},
        'cgroup_empty_or_removed': True, 'client_reaped': True}
    assert f.events == ['kill', 'stop', 'reap_client', 'show', 'reset-failed', 'show']
    assert f.client.waited and f.client.stdin.closed and f.client.stdout.closed
    assert svc.reader.closed and svc.log.closed
    detail = f.life.cleanup_details['services'][0]
    assert detail['unit'] == svc.unit and detail['step'] == 'complete' and detail['error'] is None
    notes = detail['observations']
    before = next(n for n in notes if n.get('step') == 'cgroup_before_reset')
    after = next(n for n in notes if n.get('step') == 'cgroup_final')
    assert before['cgroup'] == after['cgroup'] == (
        {'state': 'unpopulated', 'populated': 0, 'local_process_count': 0}
        if cgroup_present else {'state': 'absent'})
    assert [n['properties']['ActiveState'] for n in notes if 'properties' in n] == ['failed', 'inactive']
    old_calls = copy.deepcopy(f.calls)
    assert f.life.cleanup() == result and f.calls == old_calls


@pytest.mark.parametrize('fault,expected', [
    ('main_pid', 'service_not_quiescent'),
    ('control_pid', 'service_not_quiescent'),
    ('pending_job', 'service_not_quiescent'),
    ('foreign_cgroup', 'cleanup_unit_identity'),
    ('unloaded_failed', 'cleanup_failed_unit_identity'),
    ('active', 'service_not_inactive'),
    ('unknown_client', 'client_launch_identity_unavailable'),
    ('unreaped_client', 'cleanup_operation_timeout'),
    ('populated', 'cgroup_not_empty'),
    ('local_process', 'cgroup_not_empty'),
    ('missing_events', 'cleanup_operation_failed'),
    ('missing_procs', 'cleanup_operation_failed'),
])
def test_failed_service_never_resets_without_every_quiescence_proof(
        cleanup_service, fault, expected):
    f = cleanup_service
    if fault == 'main_pid': f.initial['MainPID'] = '123'
    elif fault == 'control_pid': f.initial['ControlPID'] = '124'
    elif fault == 'pending_job': f.initial['Job'] = '125'
    elif fault == 'foreign_cgroup': f.initial['ControlGroup'] = '/system.slice/other.service'
    elif fault == 'unloaded_failed': f.initial['LoadState'] = 'not-found'
    elif fault == 'active': f.initial['ActiveState'] = 'active'
    elif fault == 'unknown_client': f.service.process = None
    elif fault == 'unreaped_client':
        f.client.running = True
        f.client.wait_error = subprocess.TimeoutExpired(['/secret/command'], 5)
    elif fault == 'populated': (f.cg / 'cgroup.events').write_bytes(b'populated 1\nfrozen 0\n')
    elif fault == 'local_process': (f.cg / 'cgroup.procs').write_bytes(b'123\n')
    elif fault == 'missing_events': (f.cg / 'cgroup.events').unlink()
    elif fault == 'missing_procs': (f.cg / 'cgroup.procs').unlink()
    result = f.life.cleanup()
    assert result == {'cleanup_complete': False, 'errors': ['service_cleanup_unverified'],
                      'services': [None], 'timers': []}
    assert f.service.cleanup is None and not any(c[1] == 'reset-failed' for c in f.calls)
    detail = f.life.cleanup_details['services'][0]
    assert detail['error']['code'] == expected
    assert b'/secret' not in C.encode(f.life.cleanup_details)


@pytest.mark.parametrize('fault', ['active', 'failed', 'main_pid', 'control_pid', 'pending_job',
                                  'foreign_cgroup', 'populated', 'local_process'])
def test_reset_success_never_replaces_final_quiescence_proof(cleanup_service, fault):
    f = cleanup_service
    if fault in ('active', 'failed'): f.final['ActiveState'] = fault
    elif fault == 'main_pid': f.final['MainPID'] = '123'
    elif fault == 'control_pid': f.final['ControlPID'] = '124'
    elif fault == 'pending_job': f.final['Job'] = '125'
    elif fault == 'foreign_cgroup': f.final['ControlGroup'] = '/system.slice/other.service'
    elif fault == 'populated':
        f.on_reset = lambda: (f.cg / 'cgroup.events').write_bytes(b'populated 1\nfrozen 0\n')
    elif fault == 'local_process':
        f.on_reset = lambda: (f.cg / 'cgroup.procs').write_bytes(b'123\n')
    result = f.life.cleanup()
    assert result['cleanup_complete'] is False and result['services'] == [None]
    assert result['errors'] == ['service_cleanup_unverified']
    assert [c[1] for c in f.calls].count('reset-failed') == 1 and f.show_count == 2


@pytest.mark.parametrize('fault', ['duplicate', 'missing', 'extra', 'no_equals', 'no_newline',
    'invalid_utf8', 'oversize', 'field_oversize', 'negative_pid', 'ambiguous_pid',
    'control_pid_text', 'zero_job', 'job_text', 'returncode'])
def test_cleanup_rejects_ambiguous_or_unbounded_show_before_reset(cleanup_service, fault):
    f = cleanup_service; raw = cleanup_show(f.initial).stdout; returncode = 0
    if fault == 'duplicate': raw = raw.replace(b'ControlPID=0\n', b'MainPID=0\n')
    elif fault == 'missing': raw = raw.replace(b'ControlPID=0\n', b'')
    elif fault == 'extra': raw += b'Unexpected=value\n'
    elif fault == 'no_equals': raw = raw.replace(b'Job=\n', b'Job\n')
    elif fault == 'no_newline': raw = raw[:-1]
    elif fault == 'invalid_utf8': raw = raw.replace(b'Job=\n', b'Job=\xff\n')
    elif fault == 'oversize': raw = b'X' * 4097
    elif fault == 'field_oversize': raw = raw.replace(b'Job=\n', b'Job=' + b'1' * 257 + b'\n')
    elif fault == 'negative_pid': raw = raw.replace(b'MainPID=0\n', b'MainPID=-1\n')
    elif fault == 'ambiguous_pid': raw = raw.replace(b'MainPID=0\n', b'MainPID=00\n')
    elif fault == 'control_pid_text': raw = raw.replace(b'ControlPID=0\n', b'ControlPID=False\n')
    elif fault == 'zero_job': raw = raw.replace(b'Job=\n', b'Job=0\n')
    elif fault == 'job_text': raw = raw.replace(b'Job=\n', b'Job=none\n')
    elif fault == 'returncode': returncode = 3
    f.replies = [subprocess.CompletedProcess(['synthetic-show'], returncode, raw, b'/secret/stderr')]
    result = f.life.cleanup()
    assert result['cleanup_complete'] is False and f.service.cleanup is None
    assert not any(c[1] == 'reset-failed' for c in f.calls)
    notes = f.life.cleanup_details['services'][0]['observations']
    observed = next(n for n in notes if 'stdout_sha256' in n)
    assert observed['stdout_size_bytes'] == len(raw) and observed['stdout_sha256'] == C.digest(raw)
    assert b'/secret' not in C.encode(f.life.cleanup_details)


@pytest.mark.parametrize('fault,expected', [
    ('empty_events', 'cleanup_cgroup_events'),
    ('missing_population', 'cleanup_cgroup_events'),
    ('duplicate_population', 'cleanup_cgroup_events'),
    ('invalid_population', 'cleanup_cgroup_events'),
    ('oversize_events', 'cleanup_cgroup_bound'),
    ('oversize_procs', 'cleanup_cgroup_bound'),
    ('root_is_file', 'cleanup_cgroup_type'),
    ('root_is_symlink', 'cleanup_cgroup_type'),
])
def test_cleanup_cgroup_invalid_observation_is_never_absence(cleanup_service, fault, expected):
    f = cleanup_service
    payload = {'empty_events': b'', 'missing_population': b'frozen 0\n',
               'duplicate_population': b'populated 0\npopulated 0\n',
               'invalid_population': b'populated 2\n', 'oversize_events': b'x' * 4097}
    if fault in payload: (f.cg / 'cgroup.events').write_bytes(payload[fault])
    elif fault == 'oversize_procs': (f.cg / 'cgroup.procs').write_bytes(b' ' * 4097)
    else:
        (f.cg / 'cgroup.events').unlink(); (f.cg / 'cgroup.procs').unlink(); f.cg.rmdir()
        if fault == 'root_is_file': f.cg.write_bytes(b'not a cgroup')
        else: f.cg.symlink_to(f.cg.parent, target_is_directory=True)
    with pytest.raises(ValueError, match=expected):
        R.cleanup_cgroup(f.service.unit, time.monotonic() + 5)


def test_cleanup_cgroup_disappearing_root_is_reobserved_as_absent(cleanup_service, monkeypatch):
    f = cleanup_service; original = Path.open

    def disappear(path, *args, **kwargs):
        if path == f.cg / 'cgroup.events':
            (f.cg / 'cgroup.events').unlink(); (f.cg / 'cgroup.procs').unlink(); f.cg.rmdir()
            raise FileNotFoundError(errno.ENOENT, 'synthetic removal')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', disappear)
    assert R.cleanup_cgroup(f.service.unit, time.monotonic() + 5) == {'state': 'absent'}


def test_cleanup_cgroup_permission_failure_cannot_masquerade_as_absence(cleanup_service, monkeypatch):
    f = cleanup_service; original = Path.open

    def deny(path, *args, **kwargs):
        if path == f.cg / 'cgroup.events':
            raise PermissionError(errno.EACCES, '/secret/token')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', deny)
    result = f.life.cleanup()
    assert result['cleanup_complete'] is False and f.cg.is_dir()
    detail = f.life.cleanup_details['services'][0]
    assert detail['error'] == {'code': 'cleanup_operation_failed',
                              'exception_type': 'PermissionError', 'errno': errno.EACCES}
    assert detail['step'] == 'cgroup_before_reset'
    assert not any(c[1] == 'reset-failed' for c in f.calls)
    assert b'/secret' not in C.encode(f.life.cleanup_details)


@pytest.mark.parametrize('kind', ['os_error', 'timeout', 'unsafe_contract', 'safe_contract', 'interrupt'])
def test_cleanup_error_preserves_safe_identity_without_exception_payload(kind):
    exc = {'os_error': OSError(errno.EACCES, '/secret/token'),
           'timeout': subprocess.TimeoutExpired(['/secret/command'], 5, output=b'secret-output', stderr=b'secret-error'),
           'unsafe_contract': R.C.ContractError('secret = value'),
           'safe_contract': R.C.ContractError('cgroup_not_empty'),
           'interrupt': KeyboardInterrupt('/secret/token')}[kind]
    value = R.cleanup_error(exc)
    assert value['code'] == {'timeout': 'cleanup_operation_timeout',
                            'safe_contract': 'cgroup_not_empty'}.get(kind, 'cleanup_operation_failed')
    assert value['exception_type'] == type(exc).__name__
    assert value['errno'] == (errno.EACCES if kind == 'os_error' else None)
    assert b'secret' not in C.encode(value)


def test_cleanup_command_errors_are_retained_but_fresh_state_is_authoritative(cleanup_service):
    f = cleanup_service
    f.command_results.update(kill=subprocess.TimeoutExpired(['/secret/command'], 1),
                             stop=4, **{'reset-failed': 1})
    result = f.life.cleanup()
    assert result['cleanup_complete'] is True
    notes = f.life.cleanup_details['services'][0]['observations']
    assert any(n['step'] == 'kill' and n.get('error', {}).get('code') == 'cleanup_operation_timeout' for n in notes)
    assert any(n['step'] == 'stop' and n.get('returncode') == 4 for n in notes)
    assert any(n['step'] == 'reset_failed' and n.get('returncode') == 1 for n in notes)
    assert b'/secret' not in C.encode(f.life.cleanup_details)


def test_cleanup_closed_handle_failure_keeps_other_cleanup_observations(cleanup_service):
    f = cleanup_service

    class BrokenHandle:
        def close(self):
            raise OSError(errno.EIO, '/secret/handle')

    f.client.stdin = BrokenHandle()
    result = f.life.cleanup()
    assert result['cleanup_complete'] is False and f.service.cleanup is None
    assert f.client.stdout.closed and f.service.reader.closed and f.service.log.closed
    notes = f.life.cleanup_details['services'][0]['observations']
    assert any(n['step'] == 'close_stdin' and n.get('error', {}).get('errno') == errno.EIO for n in notes)
    assert any(n['step'] == 'cgroup_final' and n['cgroup']['state'] == 'unpopulated' for n in notes)
    assert b'/secret' not in C.encode(f.life.cleanup_details)


def test_expired_cleanup_deadline_never_starts_control_or_reset(cleanup_service):
    f = cleanup_service
    with pytest.raises(ValueError, match='cleanup_deadline'):
        f.service.close(time.monotonic() - 1)
    assert f.calls == [] and not f.client.waited and f.service.cleanup is None


def test_repeated_cleanup_failures_keep_original_bounded_diagnostics(cleanup_service):
    f = cleanup_service; f.initial['Job'] = '125'; deadline = time.monotonic() + 30
    first = None
    for _ in range(10):
        f.show_count = 0
        with pytest.raises(ValueError, match='service_not_quiescent'):
            f.service.close(deadline)
        if first is None: first = copy.deepcopy(f.service.cleanup_details)
    assert len(f.service.cleanup_details) == 32 and f.service.cleanup_details_truncated is True
    assert f.service.cleanup_details[:len(first)] == first
    assert f.service.cleanup is None and not any(c[1] == 'reset-failed' for c in f.calls)


@pytest.mark.parametrize('reset_result', ['still_failed', 'nonzero', 'timeout', 'uncertain_os_error'])
def test_phase_and_final_cleanup_never_repeat_reset_but_can_observe_later_closure(
        cleanup_service, reset_result):
    f = cleanup_service; svc = f.service
    f.final['ActiveState'] = 'failed'
    outcome = {'still_failed': 0, 'nonzero': 1,
               'timeout': subprocess.TimeoutExpired(['/secret/reset-command'], 5),
               'uncertain_os_error': OSError(errno.EIO, '/secret/reset-result')}[reset_result]
    f.command_results['reset-failed'] = outcome
    expected = type(outcome) if isinstance(outcome, BaseException) else ValueError
    with pytest.raises(expected):
        svc.close(time.monotonic() + 30)
    assert svc.cleanup is None and svc.reset_failed_attempted is True
    assert [c[1] for c in f.calls].count('reset-failed') == 1

    # A later lifecycle pass must observe the unresolved state without issuing
    # reset again, even if the mocked reset command would now return success.
    f.command_results['reset-failed'] = 0; f.show_count = 0
    unresolved = f.life.cleanup(); grace = f.life.cleanup_deadline
    assert unresolved == {'cleanup_complete': False, 'errors': ['service_cleanup_unverified'],
                          'services': [None], 'timers': []}
    detail = f.life.cleanup_details['services'][0]
    assert detail['error']['code'] == 'cleanup_reset_already_attempted'
    assert [c[1] for c in f.calls].count('reset-failed') == 1
    assert b'/secret' not in C.encode(f.life.cleanup_details)

    # Failure or timeout of the one reset attempt does not prohibit a later,
    # independent inactive-state and empty-cgroup proof within the same grace.
    f.initial['ActiveState'] = 'inactive'; f.show_count = 0
    closed = f.life.cleanup()
    assert closed['cleanup_complete'] is True and closed['errors'] == []
    assert closed['services'] == [svc.cleanup]
    assert svc.cleanup['properties']['ActiveState'] == 'inactive'
    assert svc.cleanup['client_reaped'] is True and svc.cleanup['cgroup_empty_or_removed'] is True
    assert f.life.cleanup_deadline == grace and svc.reset_failed_attempted is True
    assert [c[1] for c in f.calls].count('reset-failed') == 1
