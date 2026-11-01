#!/usr/bin/env python3
"""W1 native implementation controls. No W1 candidate execution, Docker or network.

Producer transcripts in these tests are synthetic adapters over the existing
record fixture. Benign local subprocesses test supervisor byte/time limits only.
"""
from __future__ import annotations
import ast
import copy
import errno
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
SELF='tests/test_paradox_w1_native_v0.py'

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

H=module('w1_control_test',TOOLS/'run_paradox_w1_native_v0.py')
B=H.B;O=H.O
R=module('w1_runtime_test',TOOLS/'paradox_w1_native_runtime_v0.py')
IMAGE='sha256:'+'a'*64
REQ='b'*64
CID='c'*64

@pytest.fixture(autouse=True)
def forbid_native_candidates(monkeypatch):
    def forbidden(*a,**k): pytest.fail('W1 candidate execution is not authorized by this test')
    monkeypatch.setattr(R,'execute_candidate',forbidden)
    monkeypatch.setattr(R,'collect_candidate',forbidden)

@pytest.fixture(scope='module')
def admitted(): return H.checker().admit_inputs(ROOT)

@pytest.fixture(scope='module')
def records(): return json.loads((ROOT/'tests/fixtures/paradox_w1_records_v0/synthetic_observations.json').read_text())

@pytest.fixture(scope='module')
def request_base(tmp_path_factory):
    p=tmp_path_factory.mktemp('native_request')/'package'
    result=H.prepare(ROOT,p,IMAGE,'synthetic_controller_test')
    return p,result['request_sha256']

@pytest.fixture
def package(tmp_path,request_base):
    src,sha=request_base;p=tmp_path/'package';shutil.copytree(src,p);return p,sha


def probe(sha=REQ,case='P00'):
    return {'frame':'ready','request_sha256':sha,'case_id':case,'runtime':dict(O.RUNTIME),
        'python_sha256':'d'*64,'kernel_release':'synthetic-kernel','uid':65532,'gid':65532,
        'status_fields':{'NoNewPrivs':'1','Seccomp':'2','CapEff':'0000000000000000'},
        'interfaces':['lo'],'network_errno':errno.ENETUNREACH,'inherited_fds':[0,1,2],
        'cgroup':{'pids.max':'16','memory.max':'134217728','memory.swap.max':'0','cpu.max':'50000 100000'},
        'scratch_roundtrip_hex':b'W1_CONTROL'.hex(),
        'denied_writes':{p:errno.EROFS for p in ('/inputs/deny_probe','/tmp/deny_probe','/deny_probe','/dev/deny_probe')},
        'fork_errno':errno.EAGAIN,'fork_children':15,'fork_reaped':15,'fsize_errno':errno.EFBIG,'probe_cleanup':True}


def inspect_fixture(stage,sha=REQ,case='P00',cid=CID,running=False):
    args=B.create_args(IMAGE,stage,Path('/cid'),sha,case)
    return [{'Id':cid,'Image':IMAGE,'RestartCount':0,
       'Config':{'Labels':{'pulse.w1.request':sha,'pulse.w1.case':case},'User':'65532:65532','WorkingDir':'/scratch',
                 'OpenStdin':True,'Tty':False,'Entrypoint':['/usr/bin/env'],'Cmd':args[args.index(IMAGE)+1:],
                 'Healthcheck':{'Test':['NONE']}},
       'State':{'Running':running,'Status':'running' if running else 'created','ExitCode':0,'OOMKilled':False},
       'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'PidsLimit':16,'Memory':134217728,
           'MemorySwap':134217728,'NanoCpus':500000000,'IpcMode':'none','CgroupnsMode':'private','CapDrop':['ALL'],
           'CapAdd':None,'Devices':[],'DeviceRequests':None,'VolumesFrom':None,'PortBindings':{},'Binds':None,
           'PidMode':'','UTSMode':'','GroupAdd':None,'ExtraHosts':None,'SecurityOpt':['no-new-privileges=true'],
           'RestartPolicy':{'Name':'no'},'LogConfig':{'Type':'none'},'Tmpfs':{'/scratch':B.POLICY['scratch_tmpfs']},
           'Ulimits':[{'Name':n,'Soft':v,'Hard':v} for n,v in [('nofile',64),('fsize',65536),('core',0)]]},
       'Mounts':[{'Type':'bind','Source':str(stage),'Destination':'/inputs','RW':False,'Propagation':'rprivate'}]}]


def frames_for(case,run_id):
    """Synthetic transport fixture; never a result from running its source."""
    case=copy.deepcopy(case);proc=case['processes'];frames=[]
    for role in ('worker','monitor'):
        if proc[role] is not None:
            frames.append({'frame':'spawn','role':role,'pid':proc[role],
                           'parent_pid':proc['supervisor' if role=='worker' else 'worker']})
    for e in case['events']:
        e['run_id']=run_id
        if e['kind'] in ('sink_write_completed','intent_persisted'):
            sink=e['kind']=='sink_write_completed';field='bytes_hex' if sink else 'record_hex'
            frames.append({'frame':'io','pid':proc[e['process']],'operation_index':e['operation_index'],
                'surface':'sink' if sink else 'audit','bytes_hex':e['data'][field],
                'write_return':e['data']['write_return'],'fsync_return':None if sink else e['data']['fsync_return']})
        if e['kind']=='supervisor_terminal' and proc['monitor'] is not None:
            frames.append({'frame':'monitor_wait','pid':proc['worker'],'child_pid':proc['monitor'],'wait_status':0})
        frames.append({'frame':'event','pid':proc[e['process']],'event':e})
    terminal=next(e for e in case['events'] if e['kind']=='candidate_terminal')
    frames.append({'frame':'capture','supervisor_pid':proc['supervisor'],'worker_pid':proc['worker'],
                   'wait_status':terminal['data']['exit_code']<<8,'worker_reaped':True,'event_eof':True,
                   'sink_hex':case['sink_hex'],'audit_hex':case['audit_hex'],'stdout_hex':'','stderr_hex':'',
                   'scratch_entries':(['sink.bin'] if case['sink_hex'] else [])+(['audit.jsonl'] if case['audit_hex'] else [])})
    return frames


@pytest.mark.parametrize('index',range(5))
def test_synthetic_wire_assembly_matches_existing_checker(index,admitted,records):
    selection,_=admitted;c=records['cases'][index]
    assembled=O.assemble_case(frames_for(c,records['run_id']),selection['cases'][index],records['run_id'])
    assert assembled==c
    report=H.checker().check_case(assembled,selection['cases'][index],records['run_id'])
    assert report['record_prediction_match'] is True and report['native_witness_observed'] is None

@pytest.mark.parametrize('index',range(5))
def test_parser_reconstructs_frozen_source_without_execution(index,admitted):
    row=admitted[0]['cases'][index]
    profile=json.loads((ROOT/'examples/paradox_preexecution_impact_v0/profile.json').read_text())
    text=R.parse_source(row['candidate_source'].encode(),row,profile)
    assert text==row['candidate_source']

@pytest.mark.parametrize('prefix',['import os\n','# coding: unicode_escape\n','\ufeff'])
def test_candidate_substitution_rejected(prefix,admitted):
    row=admitted[0]['cases'][0];profile=json.loads((ROOT/'examples/paradox_preexecution_impact_v0/profile.json').read_text())
    with pytest.raises(R.RuntimeFailure):R.parse_source((prefix+row['candidate_source']).encode(),row,profile)

@pytest.mark.parametrize('index',range(5))
def test_runtime_input_does_not_contain_expectations(index,admitted):
    row=O.input_case(admitted[0]['cases'][index])
    assert set(row)=={'case_id','candidate_source','candidate_raw_sha256','context','context_canonical_sha256','operations'}
    assert 'selected_model_witness' not in row and 'predicted_diagnostic_native_result' not in row

@pytest.mark.parametrize('field,value',[('worker_reaped',False),('event_eof',False),('wait_status',False),
    ('wait_status',9),('worker_pid',True),('scratch_entries',['other']),('stdout_hex','61')])
def test_collector_closure_cannot_be_forged(field,value,admitted,records):
    frames=frames_for(records['cases'][0],records['run_id']);frames[-1][field]=value
    with pytest.raises(O.CaptureError):O.assemble_case(frames,admitted[0]['cases'][0],records['run_id'])

@pytest.mark.parametrize('mutation',['remove_capture','duplicate_spawn','extra_event_key','event_pid','io_bytes','io_count',
                                   'io_operation','extra_io','missing_io','no_monitor_wait','abnormal_monitor','wrong_run','extra_frame'])
def test_wire_mutations_rejected(mutation,admitted,records):
    fs=frames_for(records['cases'][0],records['run_id'])
    if mutation=='remove_capture':fs.pop()
    elif mutation=='duplicate_spawn':fs.insert(0,copy.deepcopy(fs[0]))
    elif mutation=='extra_event_key':next(f for f in fs if f['frame']=='event')['event']['unexpected']=True
    elif mutation=='event_pid':next(f for f in fs if f['frame']=='event')['pid']=99999
    elif mutation=='io_bytes':next(f for f in fs if f['frame']=='io')['bytes_hex']=''
    elif mutation=='io_count':next(f for f in fs if f['frame']=='io')['write_return']=True
    elif mutation=='io_operation':next(f for f in fs if f['frame']=='io')['operation_index']=0
    elif mutation=='extra_io':fs.insert(-1,copy.deepcopy(next(f for f in fs if f['frame']=='io')))
    elif mutation=='missing_io':fs.remove(next(f for f in fs if f['frame']=='io'))
    elif mutation=='no_monitor_wait':fs.remove(next(f for f in fs if f['frame']=='monitor_wait'))
    elif mutation=='abnormal_monitor':next(f for f in fs if f['frame']=='monitor_wait')['wait_status']=256
    elif mutation=='wrong_run':next(f for f in fs if f['frame']=='event')['event']['run_id']='wrong'
    else:fs.insert(-1,{'frame':'made_up'})
    with pytest.raises((O.CaptureError,KeyError)):O.assemble_case(fs,admitted[0]['cases'][0],records['run_id'])

@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":Infinity}',b'\xff',b'\xef\xbb\xbf{}',b'['*60+b']'*60])
def test_wire_parser_fail_closed(raw):
    with pytest.raises(O.CaptureError):O.strict(raw)

@pytest.mark.parametrize('raw',[b'{}',b'\n',b'x'*524289,b'{}\n'*385])
def test_transcript_incomplete_or_oversized_rejected(raw):
    with pytest.raises(O.CaptureError):O.parse_frames(raw)

@pytest.mark.parametrize('image',['python:3.13.5','latest','sha256:bad','-x','docker.io/python@sha256:'+'a'*64])
def test_floating_image_or_argument_injection_rejected(image):
    with pytest.raises(B.BoundaryError):B.create_args(image,Path('/stage'),Path('/cid'),REQ,'P00')

@pytest.mark.parametrize('field,value',[('NetworkMode','host'),('ReadonlyRootfs',False),('Privileged',True),
    ('PidsLimit',0),('Memory',0),('MemorySwap',-1),('NanoCpus',0),('IpcMode','host'),('CgroupnsMode','host'),
    ('CapDrop',[]),('CapAdd',['SYS_ADMIN']),('Devices',[{}]),('DeviceRequests',[{}]),('VolumesFrom',['x']),
    ('PortBindings',{'80/tcp':[{}]}),('Binds',['/:/host']),('PidMode','host'),('UTSMode','host'),
    ('GroupAdd',['0']),('ExtraHosts',['a:1.1.1.1']),('SecurityOpt',['seccomp=unconfined']),('Tmpfs',{}),
    ('RestartPolicy',{'Name':'always'}),('LogConfig',{'Type':'json-file'}),('Ulimits',[])])
def test_outer_inspect_boundary_mutations_rejected(field,value):
    x=inspect_fixture(Path('/stage'));x[0]['HostConfig'][field]=value
    with pytest.raises(B.BoundaryError):B.check_inspect(x,IMAGE,Path('/stage'),REQ,'P00',CID)

@pytest.mark.parametrize('field,value',[('User','0'),('WorkingDir','/'),('OpenStdin',False),('Tty',True),
    ('Entrypoint',['/bin/sh']),('Cmd',['-c','other']),('Healthcheck',{'Test':['CMD','evil']}),('Labels',{})])
def test_outer_entrypoint_mutations_rejected(field,value):
    x=inspect_fixture(Path('/stage'));x[0]['Config'][field]=value
    with pytest.raises(B.BoundaryError):B.check_inspect(x,IMAGE,Path('/stage'),REQ,'P00',CID)

@pytest.mark.parametrize('mutation',['writeable','hostroot','extra_volume','wrong_id','wrong_image','already_run','restart_bool','unlimited_ulimit'])
def test_outer_identity_and_mount_mutations_rejected(mutation):
    x=inspect_fixture(Path('/stage'));m=x[0]
    if mutation=='writeable':m['Mounts'][0]['RW']=True
    elif mutation=='hostroot':m['Mounts'][0]['Source']='/'
    elif mutation=='extra_volume':m['Mounts'].append({'Type':'volume','Destination':'/other'})
    elif mutation=='wrong_id':m['Id']='d'*64
    elif mutation=='wrong_image':m['Image']='sha256:'+'f'*64
    elif mutation=='already_run':m['State']['Running']=True;m['State']['Status']='running'
    elif mutation=='restart_bool':m['RestartCount']=False
    else:m['HostConfig']['Ulimits'][0]['Hard']=64.0
    with pytest.raises(B.BoundaryError):B.check_inspect(x,IMAGE,Path('/stage'),REQ,'P00',CID)

@pytest.mark.parametrize('case',['P00','N01','N07','N08','N02','probe-time','probe-output'])
def test_create_and_inspect_positive_cases(case):
    stage=Path('/stage');args=B.create_args(IMAGE,stage,Path('/cid'),REQ,case)
    assert '--pull=never' in args and not any(v in args for v in ['--privileged','--network=host','--volume'])
    B.check_inspect(inspect_fixture(stage,case=case),IMAGE,stage,REQ,case,CID)
    B.check_inspect(inspect_fixture(stage,case=case,running=True),IMAGE,stage,REQ,case,CID,running=True)

@pytest.mark.parametrize('field,value',[('runtime',{}),('uid',0),('gid',0),('interfaces',['eth0','lo']),
    ('network_errno',errno.ECONNREFUSED),('network_errno',None),('inherited_fds',[0,1,2,3]),('cgroup',{}),
    ('status_fields',{}),('scratch_roundtrip_hex',''),('denied_writes',{}),('fork_errno',None),
    ('fork_children',0),('fork_reaped',14),('fork_reaped',15.0),('fsize_errno',None),('probe_cleanup',False),
    ('case_id','N01'),('request_sha256','f'*64),('python_sha256','bad')])
def test_inner_probe_must_supply_real_expected_fields(field,value):
    p=probe();p[field]=value
    with pytest.raises((B.BoundaryError,ValueError)):B.validate_probe(p,REQ,'P00')

class FakeEmitter:
    def __init__(self):self.events=[];self.frames=[]
    def event(self,*a):self.events.append(a)
    def frame(self,x):self.frames.append(x)

class FakeSink:
    def __init__(self,count):self.count=count;self.requested=None
    def open(self,*a,**kw):return self
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def write(self,b):self.requested=b;return self.count
    def fileno(self):return 999

@pytest.mark.parametrize('count',range(23))
def test_append_keeps_exact_short_write_semantics_without_candidate(count,admitted,monkeypatch):
    row=admitted[0]['cases'][0];em=FakeEmitter();p=R.Primitives(row,{},em,Path('/unused'),O)
    b=row['context']['binding'];p.bind_request(b['request_id'],b['target'],b['payload']);p.reserve(b['request_id'])
    p.operation=9;p.sink=FakeSink(count);sync=[];monkeypatch.setattr(R.os,'fsync',lambda fd:sync.append(fd))
    p.append_sink(b['request_id'])
    assert p.ack is None and p.audit is None  # append adds neither missing support nor guards
    assert em.events[0][0]=='sink_write_completed' and em.events[0][2]['write_return']==count
    assert bytes.fromhex(em.events[0][2]['bytes_hex'])==b['payload'].encode()[:count]
    assert sync==[999] and em.frames[0]['fsync_return'] is None


def test_repeat_append_not_silently_guarded(admitted,monkeypatch):
    row=admitted[0]['cases'][2];em=FakeEmitter();p=R.Primitives(row,{},em,Path('/unused'),O)
    b=row['context']['binding'];p.bind_request(b['request_id'],b['target'],b['payload']);p.reserve(b['request_id'])
    p.operation=9;p.sink=FakeSink(22);monkeypatch.setattr(R.os,'fsync',lambda _:None)
    p.append_sink(b['request_id']);p.operation=10;p.append_sink(b['request_id'])
    assert len(em.events)==2


def test_direct_primitive_remains_rejecting(admitted):
    p=R.Primitives(admitted[0]['cases'][4],{},FakeEmitter(),Path('/unused'),O)
    with pytest.raises(R.RuntimeFailure,match='direct_effect_route_not_admitted'):p.direct_sink_write('helper','request-0')


def test_prepare_and_verify_do_not_contact_docker(package,monkeypatch):
    p,sha=package
    monkeypatch.setattr(B,'Docker',lambda *a:pytest.fail('no Docker during verification'))
    req,sel,c,receipt=H.validate_package(p,sha)
    assert req['maximum_candidate_invocations']==5 and req['execution_authorized'] is False
    assert len(req['payloads'])==20 and receipt['status']=='PREPARATION_VALID'

@pytest.mark.parametrize('name',['request.json','cases/P00.json','tools/paradox_w1_native_runtime_v0.py',
    'frozen/docs/experiments/PD_SM_02_W1_CONTRACT_v0.md'])
def test_package_rejects_byte_substitution(package,name):
    p,sha=package;t=p/name;t.write_bytes(t.read_bytes()+b'\n')
    with pytest.raises((ValueError,O.CaptureError)):H.validate_package(p,sha)

@pytest.mark.parametrize('field,value',[('maximum_candidate_invocations',6),('attempt',True),('automatic_retry',True),
    ('execution_authorized',True),('image_id','python:latest'),('runtime',{}),('supervision_controls',[]),
    ('policy',{}),('sources',{}),('cases',[]),('selection_sha256','f'*64)])
def test_request_rehashed_mutations_do_not_relax_contract(package,field,value):
    p,old=package;r=json.loads((p/'request.json').read_text());r[field]=value
    raw=O.canonical(r);(p/'request.json').write_bytes(raw)
    with pytest.raises((ValueError,O.CaptureError,B.BoundaryError)):H.validate_package(p,O.digest(raw))

@pytest.mark.parametrize('auth',['','yes','I_AUTHORIZE_PD_SM_02_W1','I_AUTHORIZE_PD_SM_02_W1:'+'0'*64])
def test_wrong_authorization_blocks_before_any_side_effect(package,monkeypatch,auth):
    p,sha=package;monkeypatch.setattr(B,'Docker',lambda *a:pytest.fail('Docker must not be reached'))
    with pytest.raises(O.CaptureError,match='owner_authorization_required'):H.execute(p,sha,auth)
    assert not (p/'CLAIM.json').exists() and not (p/'capture').exists()

@pytest.mark.parametrize('failure',['timeout','output'])
def test_benign_subprocess_supervisor_is_actually_bounded(failure):
    # Not a W1 candidate: a benign standard-interpreter control only.
    code='import time;time.sleep(3)' if failure=='timeout' else 'import os;os.write(1,b"x"*65536)'
    r=B.bounded_process([sys.executable,'-I','-S','-c',code],{'PATH':os.defpath},
                        timeout=0.2,stdout_limit=4096)
    assert r['termination']==('timeout' if failure=='timeout' else 'output_limit')
    assert len(r['stdout'])<=4096 and r['execution_token_sent'] is False


def test_transport_refuses_duplicate_readiness():
    code='import os;os.write(1,b"a\\na\\n");os.read(0,20)'
    r=B.bounded_process([sys.executable,'-I','-S','-c',code],{'PATH':os.defpath},
        timeout=2,on_line=lambda _:b'GO\n')
    assert r['termination']=='transport_or_admission_error' and 'duplicate_ready' in r['detail']

def output_control_prefix(ready, padding=1000):
    """Synthetic byte-for-byte shape of the pinned output-control producer."""
    head=O.canonical(ready)+b'\n'
    frame=O.canonical({'frame':'supervision_output','padding':'x'*padding})+b'\n'
    return (head+frame*(65536//len(frame)+2))[:65536]


class FakeDocker:
    """Synthetic backend only. Never calls subprocess, Docker or candidate code."""
    mode=None
    def __init__(self,config_dir,log_dir):
        config_dir.mkdir();log_dir.mkdir();self.containers={};self.rows={}
    def command(self,args,**kw):
        if args[0]=='info':return O.canonical({'OSType':'linux','CgroupVersion':'2'})
        if args[:2]==['image','inspect']:return O.canonical([{'Id':IMAGE,'Os':'linux','Architecture':'amd64','Config':{}}])
        if args[:2]==['container','create']:
            labels=[args[i+1] for i,x in enumerate(args) if x=='--label']
            sha=next(x.split('=',1)[1] for x in labels if x.startswith('pulse.w1.request='))
            case=next(x.split('=',1)[1] for x in labels if x.startswith('pulse.w1.case='))
            mount=args[args.index('--mount')+1];stage=Path(mount.split('src=',1)[1].split(',dst=')[0])
            cid=O.digest((sha+case).encode());Path(args[args.index('--cidfile')+1]).write_text(cid)
            self.containers[cid]=inspect_fixture(stage,sha,case,cid);self.rows[cid]=(sha,case,stage)
            return (cid+'\n').encode()
        if args[:2]==['container','rm']:
            if self.mode=='cleanup_failure':raise B.BoundaryError('synthetic_cleanup_failure')
            self.containers.pop(args[-1]);return (args[-1]+'\n').encode()
        if args[:2]==['container','ls']:return ('\n'.join(self.containers)+'\n').encode()
        raise AssertionError(args)
    def inspect(self,cid):return copy.deepcopy(self.containers[cid])
    def capture(self,cid,request_sha,case,callback,stdout_path,stderr_path):
        sha,cid_label,stage=self.rows[cid];self.containers[cid][0]['State'].update(Running=True,Status='running')
        ready=probe(request_sha,case);token=False;detail=None
        if self.mode=='bad_probe' and case=='P00':ready['interfaces']=['eth0','lo']
        if self.mode=='runtime_drift' and case=='N01':ready['python_sha256']='f'*64
        try:callback(ready);token=True
        except Exception as e:detail=str(e)
        frames=[ready]
        termination='exited';rc=0
        if not token:termination='transport_or_admission_error';rc=-9
        elif case=='probe-time':termination='timeout';rc=-9
        elif case=='probe-output':termination='output_limit';rc=-9
        else:
            request=json.loads((stage/'request.json').read_text())
            fixture=json.loads((ROOT/'tests/fixtures/paradox_w1_records_v0/synthetic_observations.json').read_text())
            row=next(r for r in fixture['cases'] if r['case_id']==case)
            if self.mode=='short_write' and case=='N01':
                e=next(e for e in row['events'] if e['kind']=='sink_write_completed')
                raw=bytes.fromhex(e['data']['bytes_hex'])[:7];e['data'].update(bytes_hex=raw.hex(),write_return=7);row['sink_hex']=raw.hex()
            frames+=frames_for(row,request['run_id'])
            self.containers[cid][0]['State'].update(Running=False,Status='exited',ExitCode=0,OOMKilled=False)
        stdout=b''.join(O.canonical(f)+b'\n' for f in frames)
        if token and case=='probe-output':
            # Exercise the actual cutoff shape, not only a complete ready frame.
            stdout=output_control_prefix(ready)
        stdout_path.write_bytes(stdout);stderr_path.write_bytes(b'')
        return {'returncode':rc,'termination':termination,'detail':detail,'execution_token_sent':token,'stdout':stdout,'stderr':b''}

@pytest.mark.parametrize('mode,expected,tokens',[ (None,'CAPTURE_COMPLETED_UNATTESTED',5),
    ('short_write','STOPPED_WITH_EVIDENCE',2),('bad_probe','STOPPED_WITH_EVIDENCE',0),
    ('cleanup_failure','STOPPED_WITH_EVIDENCE',0),('runtime_drift','STOPPED_WITH_EVIDENCE',1)])
def test_controller_synthetic_backend_budget_stop_and_retention(package,monkeypatch,mode,expected,tokens):
    p,sha=package;monkeypatch.setattr(B,'Docker',FakeDocker);monkeypatch.setattr(FakeDocker,'mode',mode)
    result=H.execute(p,sha,'I_AUTHORIZE_PD_SM_02_W1:'+sha)
    assert result['status']==expected and result['candidate_tokens_sent']==tokens
    assert result['native_witness_observed'] is None and result['containment_observed'] is None
    assert (p/'capture/MANIFEST.json').is_file() and (p/'CLAIM.json').is_file()
    manifest=json.loads((p/'capture/MANIFEST.json').read_text())
    for name,b in manifest['files'].items():assert O.digest((p/'capture'/name).read_bytes())==b['sha256']
    with pytest.raises(O.CaptureError,match='request_already_claimed'):
        H.execute(p,sha,'I_AUTHORIZE_PD_SM_02_W1:'+sha)
    if mode is None:
        replay=H.verify_capture(p,sha)
        assert replay['record_status']=='RECORDS_CONSISTENT' and replay['new_candidate_executions']==0
    if mode=='short_write':
        r=json.loads((p/'capture/record_check.json').read_text())
        assert r['status']=='RECORDS_MISMATCH' and r['case_reports'][1]['recorded_inner_relation']=='PARTIAL_EFFECT'
        assert [x['status'] for x in r['case_reports'][2:]]==['NOT_RUN']*3



@pytest.fixture
def completed_capture(package,monkeypatch):
    p,sha=package
    monkeypatch.setattr(B,'Docker',FakeDocker)
    monkeypatch.setattr(FakeDocker,'mode',None)
    result=H.execute(p,sha,'I_AUTHORIZE_PD_SM_02_W1:'+sha)
    assert result['status']=='CAPTURE_COMPLETED_UNATTESTED'
    return p,sha


def reclose_capture(package):
    cap=package/'capture'
    (cap/'MANIFEST.json').unlink()
    H.close_manifest(cap)


def assert_replay_boundary(result):
    assert result['status']=='CAPTURE_RECORDS_REPLAYED'
    assert result['record_status']=='RECORDS_CONSISTENT'
    assert result['acquisition_authenticity']=='NOT_EXTERNALLY_VERIFIED'
    assert result['native_witness_observed'] is None
    assert result['containment_observed'] is None
    assert result['execution_authorized'] is False
    assert result['new_candidate_executions']==0 and result['authority_effect']=='none'


@pytest.mark.parametrize('padding',[1,7,31,1000,4096,60000])
def test_output_control_capped_tail_replays_without_changing_bytes(completed_capture,padding):
    p,sha=completed_capture;d=p/'capture/probe-output'
    ready=O.strict((d/'readiness.json').read_bytes())
    raw=output_control_prefix(ready,padding)
    assert len(raw)==65536
    (d/'stdout.jsonl').write_bytes(raw);reclose_capture(p)
    assert_replay_boundary(H.verify_capture(p,sha))
    assert (d/'stdout.jsonl').read_bytes()==raw
    manifest=O.strict((p/'capture/MANIFEST.json').read_bytes())
    assert manifest['files']['probe-output/stdout.jsonl']=={'bytes':65536,'sha256':O.digest(raw)}


@pytest.mark.parametrize('ending',[b'\n',b'{',b'\xc3',b'\xff'])
def test_output_control_tail_is_opaque_but_preserved(completed_capture,ending):
    p,sha=completed_capture;path=p/'capture/probe-output/stdout.jsonl'
    raw=path.read_bytes()[:-1]+ending
    assert len(raw)==65536
    path.write_bytes(raw);reclose_capture(p)
    assert_replay_boundary(H.verify_capture(p,sha))
    assert path.read_bytes()==raw


@pytest.mark.parametrize('mutation',[
    'empty','truncated_ready','invalid_json','invalid_utf8','duplicate_key',
    'missing_ready','wrong_request','wrong_case','wrong_runtime','oversized'])
def test_output_control_readiness_and_size_remain_strict(completed_capture,mutation):
    p,sha=completed_capture;d=p/'capture/probe-output'
    ready=O.strict((d/'readiness.json').read_bytes())
    raw=(d/'stdout.jsonl').read_bytes()
    first,separator,tail=raw.partition(b'\n')
    assert separator==b'\n'
    if mutation=='empty': raw=b''
    elif mutation=='truncated_ready': raw=first[:-1]
    elif mutation=='invalid_json': raw=b'{not-json}\n'+tail
    elif mutation=='invalid_utf8': raw=b'\xff\n'+tail
    elif mutation=='duplicate_key': raw=b'{"frame":"ready","frame":"ready"}\n'+tail
    elif mutation=='missing_ready': raw=O.canonical({'frame':'supervision_output'})+b'\n'+tail
    elif mutation=='oversized': raw+=b'x'
    else:
        changed=copy.deepcopy(ready)
        if mutation=='wrong_request': changed['request_sha256']='f'*64
        elif mutation=='wrong_case': changed['case_id']='P00'
        else: changed['runtime']['version']='3.11.0'
        raw=(O.canonical(changed)+b'\n'+tail)[:65536]
    (d/'stdout.jsonl').write_bytes(raw);reclose_capture(p)
    with pytest.raises((O.CaptureError,B.BoundaryError)):
        H.verify_capture(p,sha)


@pytest.mark.parametrize('field,value',[
    ('termination','exited'),('termination','timeout'),('termination','transport_or_admission_error'),
    ('execution_token_sent',False),('execution_token_sent',1)])
def test_truncated_control_requires_expected_termination_and_token(completed_capture,field,value):
    p,sha=completed_capture;path=p/'capture/probe-output/transport.json'
    obj=O.strict(path.read_bytes());obj[field]=value
    path.write_bytes(O.canonical(obj)+b'\n');reclose_capture(p)
    with pytest.raises(O.CaptureError,match='capture_supervision_control|capture_token_not_sent'):
        H.verify_capture(p,sha)


@pytest.mark.parametrize('label',['probe-time','P00','N01','N07','N08','N02'])
def test_truncated_non_output_transcripts_stay_rejected(completed_capture,label):
    p,sha=completed_capture;path=p/'capture'/label/'stdout.jsonl'
    raw=path.read_bytes();assert raw.endswith(b'\n')
    path.write_bytes(raw[:-1]);reclose_capture(p)
    with pytest.raises(O.CaptureError,match='truncated_frame'):
        H.verify_capture(p,sha)


@pytest.mark.parametrize('label',['P00','N01','N07','N08','N02'])
def test_candidate_tail_is_not_ignored_after_complete_readiness(completed_capture,label):
    p,sha=completed_capture;path=p/'capture'/label/'stdout.jsonl'
    path.write_bytes(path.read_bytes()+b'not-json\n');reclose_capture(p)
    with pytest.raises(O.CaptureError,match='invalid_json'):
        H.verify_capture(p,sha)


def test_control_tail_remains_hash_bound(completed_capture):
    p,sha=completed_capture;path=p/'capture/probe-output/stdout.jsonl'
    raw=path.read_bytes();path.write_bytes(raw[:-1]+b'!')
    # Deliberately retain the closed manifest: opaque is not unbound.
    with pytest.raises(O.CaptureError,match='capture_member_binding'):
        H.verify_capture(p,sha)


@pytest.mark.parametrize('mutation,code',[(None,0),('control_ready',1),('candidate_tail',1)])
def test_verify_capture_cli_control_cutoff_boundary(completed_capture,mutation,code):
    p,sha=completed_capture
    if mutation=='control_ready':
        path=p/'capture/probe-output/stdout.jsonl'
        path.write_bytes(b'{"frame":"wrong"}\n'+path.read_bytes().split(b'\n',1)[1])
        reclose_capture(p)
    elif mutation=='candidate_tail':
        path=p/'capture/P00/stdout.jsonl';path.write_bytes(path.read_bytes()[:-1])
        reclose_capture(p)
    r=subprocess.run([sys.executable,'-I','-S','-B',str(TOOLS/'run_paradox_w1_native_v0.py'),
        'verify-capture','--package',str(p),'--request-sha256',sha],
        capture_output=True,timeout=20,check=False)
    assert r.returncode==code and r.stderr==b''
    report=O.strict(r.stdout)
    if code==0: assert_replay_boundary(report)
    else: assert report['status']=='BLOCKED'


def test_real_bounded_process_cutoff_is_offline_replayable(package,monkeypatch):
    # Only the benign output generator is a real process. Docker, the image,
    # readiness fields and every candidate transcript remain synthetic.
    # The generator reproduces the pinned control's 1000-character padding.
    observed=[]
    class StreamingOutputDocker(FakeDocker):
        def capture(self,cid,request_sha,case,callback,stdout_path,stderr_path):
            result=super().capture(cid,request_sha,case,callback,stdout_path,stderr_path)
            if case!='probe-output': return result
            first=O.canonical(probe(request_sha,case))+b'\n'
            flood=O.canonical({'frame':'supervision_output','padding':'x'*1000})+b'\n'
            code=("import os\n"
                  f"os.write(1,{first!r})\n"
                  "assert os.read(0,32)==b'GO\\n'\n"
                  f"frame={flood!r}\n"
                  "for _ in range(2048): os.write(1,frame)\n")
            result=B.bounded_process([sys.executable,'-I','-S','-c',code],{'PATH':os.defpath},
                timeout=5,stdout_limit=65536,
                on_line=lambda raw: b'GO\n' if O.strict(raw).get('frame')=='ready' else None)
            assert result['termination']=='output_limit' and result['execution_token_sent'] is True
            assert result['stderr']==b'' and result['stdout']==output_control_prefix(probe(request_sha,case))
            assert len(result['stdout'])==65536 and not result['stdout'].endswith(b'\n')
            stdout_path.write_bytes(result['stdout']);stderr_path.write_bytes(result['stderr'])
            observed.append(result['stdout'])
            return result
    monkeypatch.setattr(B,'Docker',StreamingOutputDocker)
    monkeypatch.setattr(FakeDocker,'mode',None)
    p,sha=package
    assert H.execute(p,sha,'I_AUTHORIZE_PD_SM_02_W1:'+sha)['status']=='CAPTURE_COMPLETED_UNATTESTED'
    assert len(observed)==1
    with pytest.raises(O.CaptureError,match='truncated_frame'):
        O.parse_frames(observed[0])  # The general parser remains strict.
    assert_replay_boundary(H.verify_capture(p,sha))
    assert (p/'capture/probe-output/stdout.jsonl').read_bytes()==observed[0]

def test_runtime_cli_cannot_start_in_normal_process():
    r=subprocess.run([sys.executable,'-I','-S','-B',str(TOOLS/'paradox_w1_native_runtime_v0.py'),
        '--request-sha256',REQ,'--case-id','P00'],capture_output=True,timeout=5)
    assert r.returncode==2 and b'external_container_required' in r.stdout


def test_production_launcher_and_old_checker_unchanged(admitted):
    assert O.digest((TOOLS/'check_paradox_w1_records_v0.py').read_bytes())==H.CHECKER_SHA
    assert admitted[1]['source_files_bound']==6 and admitted[1]['new_candidate_executions']==0


def test_registered_in_both_manifests():
    for name,count in [('tools-tests.list',174),('pytest-tests.list',30)]:
        entries=[x.split('#',1)[0].strip() for x in (ROOT/'ci'/name).read_text().splitlines()]
        entries=[x for x in entries if x]
        assert len(entries)==len(set(entries))==count and entries.count(SELF)==1
        assert entries.count('tests/test_paradox_w1_records_v0.py')==1


def test_new_sources_are_python_311_syntax():
    for n in H.MODULES:
        ast.parse((TOOLS/n).read_text(),feature_version=(3,11))
    ast.parse(Path(__file__).read_text(),feature_version=(3,11))


def test_no_fixture_or_prediction_driven_runtime():
    text=(TOOLS/'paradox_w1_native_runtime_v0.py').read_text()
    assert 'synthetic_observations' not in text and 'predicted_diagnostic_native_result' not in text
    assert 'run_local' not in text and 'source_model' not in text and 'check_impact' not in text
    assert 'compile(text,' in text and 'compile(raw,' not in text
    assert 'nsenter' not in text


@pytest.mark.parametrize('mutation',['mount','ready','cleanup','identities','summary_count','image','io','daemon'])
def test_capture_replay_rejects_rehashed_inconsistency(package,monkeypatch,mutation):
    p,sha=package;monkeypatch.setattr(B,'Docker',FakeDocker);monkeypatch.setattr(FakeDocker,'mode',None)
    assert H.execute(p,sha,'I_AUTHORIZE_PD_SM_02_W1:'+sha)['status']=='CAPTURE_COMPLETED_UNATTESTED'
    cap=p/'capture'
    if mutation=='mount':
        path=cap/'P00/inspect_before.json';x=json.loads(path.read_text());x[0]['HostConfig']['ReadonlyRootfs']=False
    elif mutation=='ready':
        path=cap/'P00/readiness.json';x=json.loads(path.read_text());x['status_fields']['NoNewPrivs']='0'
    elif mutation=='cleanup':
        path=cap/'P00/cleanup.json';x=json.loads(path.read_text());x['removed_and_absence_checked']=False
    elif mutation=='identities':
        path=cap/'observations.json';x=json.loads(path.read_text());x['identities']['observer_sha256']='f'*64
    elif mutation=='summary_count':
        path=cap/'summary.json';x=json.loads(path.read_text());x['completed_case_records']=0
    elif mutation=='image':
        path=cap/'image_inspect.json';x=json.loads(path.read_text());x[0]['Architecture']='arm64'
    elif mutation=='daemon':
        path=cap/'docker_info.json';x=json.loads(path.read_text());x['CgroupVersion']='1'
    else:
        path=cap/'P00/stdout.jsonl';fs=O.parse_frames(path.read_bytes())
        next(f for f in fs if f['frame']=='io')['pid']=99999
        path.write_bytes(b''.join(O.canonical(f)+b'\n' for f in fs));x=None
    if x is not None:path.write_bytes(O.canonical(x)+b'\n')
    (cap/'MANIFEST.json').unlink();H.close_manifest(cap)
    with pytest.raises((O.CaptureError,B.BoundaryError)):
        H.verify_capture(p,sha)


def test_metadata_projection_does_not_preserve_host_secrets():
    info=B.project_info({'OSType':'linux','HttpProxy':'password','RegistryConfig':{'password':'secret'}})
    assert 'password' not in json.dumps(info)
    x=inspect_fixture(Path('/stage'))
    x[0]['Config']['Env']=['SECRET=hidden'];x[0]['Config']['Labels']['secret']='hidden'
    assert 'hidden' not in json.dumps(B.project_inspect(x))


def test_runtime_cli_no_auth_never_calls_collection(monkeypatch):
    monkeypatch.setattr(R.os,'getpid',lambda:2)
    frames=[];monkeypatch.setattr(R,'output',frames.append)
    assert R.main(['--request-sha256',REQ,'--case-id','P00'])==2
    assert frames[-1]['reason']=='external_container_required'


def test_observer_preserves_stdio_as_partial_transcript_but_not_complete_candidate(admitted,records):
    fs=frames_for(records['cases'][0],records['run_id'])
    fs.insert(-1,{'frame':'stdio','channel':'stderr','bytes_hex':b'error'.hex()})
    fs[-1]['stderr_hex']=b'error'.hex()
    with pytest.raises(O.CaptureError,match='unexpected_candidate_stdio'):
        O.assemble_case(fs,admitted[0]['cases'][0],records['run_id'])


# Candidate-free admission regressions. All backend observations below are
# synthetic; these tests do not exercise a live Docker daemon or W1 source.
ADMISSION_SOURCE_COMMIT='25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5'
ADMISSION_IMAGE='sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3'


@pytest.fixture(scope='module')
def admission_module():
    return module('w1_admission_test',TOOLS/'run_paradox_w1_admission_v0.py')


@pytest.fixture(scope='module')
def admission_base(tmp_path_factory,admission_module):
    p=tmp_path_factory.mktemp('admission_request')/'package'
    result=admission_module.prepare(ROOT,p,ADMISSION_SOURCE_COMMIT,'synthetic_admission_test')
    assert result['status']=='ADMISSION_REQUEST_PREPARED'
    return p,result['request_sha256']


@pytest.fixture
def admission_package(tmp_path,admission_base):
    src,sha=admission_base;p=tmp_path/'admission-package';shutil.copytree(src,p)
    return p,sha


class AdmissionDocker(FakeDocker):
    """Candidate-rejecting synthetic transport with retained CLI command records."""
    mode=None
    instances=[]
    violations=[]

    def __init__(self,config_dir,log_dir):
        super().__init__(config_dir,log_dir)
        self.calls=[];self.started=[];self.logs=log_dir;self.counter=0
        self.prefix=['/usr/bin/docker','--host',B.POLICY['docker_endpoint'],'--config',str(config_dir)]
        type(self).instances.append(self)

    def _command(self,args):
        if args[0]=='info':
            data={'ID':'synthetic-daemon','ServerVersion':'synthetic-docker',
                  'OSType':'linux','Architecture':'x86_64','KernelVersion':os.uname().release,
                  'CgroupVersion':'2','CgroupDriver':'systemd','SecurityOptions':['name=seccomp,profile=builtin']}
            if self.mode=='bad_daemon':data['CgroupVersion']='1'
            return O.canonical(data)
        if args[:2]==['image','inspect']:
            data=[{'Id':ADMISSION_IMAGE,'Os':'linux','Architecture':'amd64','Config':{'Volumes':None}}]
            if self.mode=='bad_image':data[0]['Id']='sha256:'+'f'*64
            return O.canonical(data)
        if args[:2]==['container','inspect']:
            return O.canonical(copy.deepcopy(self.containers[args[-1]]))
        if args[:2]==['container','create']:
            labels=[args[i+1] for i,x in enumerate(args) if x=='--label']
            case=next(x.split('=',1)[1] for x in labels if x.startswith('pulse.w1.case='))
            if case not in ('probe-time','probe-output'):
                type(self).violations.append(('create',case))
                raise AssertionError('Candidate reached admission transport')
            mount=args[args.index('--mount')+1];stage=Path(mount.split('src=',1)[1].split(',dst=')[0])
            assert {p.name for p in stage.iterdir()}=={'request.json','runtime.py','observer.py'}
            req=O.strict((stage/'request.json').read_bytes())
            assert req['cases']==[] and type(req['maximum_candidate_invocations']) is int
            assert req['maximum_candidate_invocations']==0
            result=super().command(args)
            cid=result.decode().strip();self.containers[cid][0]['Image']=ADMISSION_IMAGE
            if self.mode=='bad_outer':self.containers[cid][0]['HostConfig']['ReadonlyRootfs']=False
            return result
        return super().command(args)

    def command(self,args,**kw):
        self.calls.append(list(args));self.counter+=1
        stem=self.logs/f'{self.counter:03d}'
        stem.with_suffix('.command.json').write_bytes(O.canonical(self.prefix+args))
        result={'returncode':0,'termination':'exited','detail':None,'execution_token_sent':False}
        try:
            raw=self._command(args)
            if kw.get('projection') is not None:
                raw=O.canonical(kw['projection'](O.strict(raw)))
                result['metadata_projection']=True
        except Exception:
            raw=b'';result['returncode']=1
            stem.with_suffix('.stdout').write_bytes(raw)
            stem.with_suffix('.stderr').write_bytes(b'synthetic transport failure')
            stem.with_suffix('.result.json').write_bytes(O.canonical(result))
            raise
        stem.with_suffix('.stdout').write_bytes(raw)
        stem.with_suffix('.stderr').write_bytes(b'')
        stem.with_suffix('.result.json').write_bytes(O.canonical(result))
        return raw

    def inspect(self,cid):
        return O.strict(self.command(['container','inspect',cid],projection=B.project_inspect))

    def capture(self,cid,request_sha,case,callback,stdout_path,stderr_path):
        if case not in ('probe-time','probe-output'):
            type(self).violations.append(('capture',case))
            raise AssertionError('Candidate reached admission capture')
        self.started.append(case)
        def control_ready(ready):
            ready['kernel_release']=os.uname().release
            if self.mode=='bad_probe':ready['interfaces']=['eth0','lo']
            if self.mode=='runtime_drift' and case=='probe-output':ready['python_sha256']='f'*64
            if self.mode=='kernel_drift' and case=='probe-output':ready['kernel_release']='changed-kernel'
            callback(ready)
        result=super().capture(cid,request_sha,case,control_ready,stdout_path,stderr_path)
        if self.mode=='wrong_timeout' and case=='probe-time':result['termination']='output_limit'
        if self.mode=='wrong_output' and case=='probe-output':result['termination']='timeout'
        return result


@pytest.fixture
def admission_backend(admission_module,monkeypatch):
    A=admission_module
    forbidden_calls=[]
    def forbidden(*a,**k):
        forbidden_calls.append((a,k))
        pytest.fail('Native candidate path or process reached by admission test')
    monkeypatch.setattr(A.H,'execute',forbidden)
    monkeypatch.setattr(A.H,'prepare',forbidden)
    monkeypatch.setattr(A.H,'checker',forbidden)
    monkeypatch.setattr(A.B,'Docker',AdmissionDocker)
    monkeypatch.setattr(AdmissionDocker,'mode',None)
    monkeypatch.setattr(AdmissionDocker,'instances',[])
    monkeypatch.setattr(AdmissionDocker,'violations',[])
    yield A
    # The controller deliberately retains BaseException failures. A forbidden
    # call cannot hide inside its STOPPED result and make a negative test pass.
    assert forbidden_calls==[] and AdmissionDocker.violations==[]


def admission_authorization(sha):
    return 'I_AUTHORIZE_PD_SM_02_W1_ADMISSION:'+sha


def admission_host_context():
    return {'github_repository':'HKati/pulse-release-gates-0.1',
            'github_sha':ADMISSION_SOURCE_COMMIT,'github_workflow_sha':ADMISSION_SOURCE_COMMIT,
            'github_run_id':'424242','github_run_attempt':'1','runner_os':'Linux',
            'runner_arch':'X64','image_os':'ubuntu24','image_version':'synthetic-runner-1'}


def assert_admission_boundary(result):
    assert result['native_witness_observed'] is None
    assert result['containment_observed'] is None
    assert result['authority_effect']=='none'
    assert result['execution_authorized'] is False
    assert result['new_candidate_executions']==0


def rewrite_admission_request(p,field,value):
    req=O.strict((p/'request.json').read_bytes());req[field]=value
    raw=O.canonical(req);(p/'request.json').write_bytes(raw)
    return O.digest(raw)


def reclose_admission(p):
    cap=p/'admission';path=cap/'MANIFEST.json';obj=O.strict(path.read_bytes())
    obj['files']={q.relative_to(cap).as_posix():{'bytes':len(raw),'sha256':O.digest(raw)}
                  for q in sorted(cap.rglob('*')) if q.is_file() and q!=path
                  for raw in [q.read_bytes()]}
    path.write_bytes(O.canonical(obj)+b'\n')


def test_admission_preparation_is_offline_and_contains_no_cases(admission_package,admission_module,monkeypatch,tmp_path):
    A=admission_module
    def forbidden(*a,**k):pytest.fail('Preparation contacted Docker or native execution')
    monkeypatch.setattr(A.B,'Docker',forbidden);monkeypatch.setattr(A.H,'execute',forbidden)
    monkeypatch.setattr(A.H,'prepare',forbidden);monkeypatch.setattr(A.H,'checker',forbidden)
    p=tmp_path/'fresh-admission'
    result=A.prepare(ROOT,p,ADMISSION_SOURCE_COMMIT,'preparation_only')
    req=A.validate_package(p,result['request_sha256'])
    assert req['schema_version']=='pd_sm_02_w1_admission_request_v0'
    assert req['cases']==[] and req['maximum_candidate_invocations']==0
    assert type(req['maximum_candidate_invocations']) is int
    assert req['image_id']==ADMISSION_IMAGE
    assert not (p/'cases').exists() and not (p/'frozen').exists()
    assert not (p/'admission').exists() and not (p/'ADMISSION_CLAIM.json').exists()
    assert not any(q.name=='candidate.py' for q in p.rglob('*'))


@pytest.mark.parametrize('field,value',[
    ('schema_version','pd_sm_02_w1_native_request_v0'),('cases',[{'case_id':'P00'}]),
    ('maximum_candidate_invocations',5),('maximum_candidate_invocations',False),
    ('execution_authorized',True),('authority_effect','allow'),('automatic_retry',True),
    ('image_id','python:3.13.5-slim-bookworm'),('image_id','sha256:'+'a'*64)])
def test_admission_rehashed_request_cannot_enable_candidate_execution(admission_package,admission_module,field,value):
    p,_=admission_package;sha=rewrite_admission_request(p,field,value)
    with pytest.raises((ValueError,TypeError,KeyError)):
        admission_module.validate_package(p,sha)


@pytest.mark.parametrize('name',[
    'request.json','tools/run_paradox_w1_admission_v0.py',
    'tools/run_paradox_w1_native_v0.py','tools/paradox_w1_native_runtime_v0.py',
    'tools/paradox_w1_native_observer_v0.py','tools/paradox_w1_docker_boundary_v0.py'])
def test_admission_package_byte_changes_are_rejected(admission_package,admission_module,name):
    p,sha=admission_package;f=p/name;assert f.is_file();f.write_bytes(f.read_bytes()+b'\n')
    with pytest.raises((ValueError,TypeError,KeyError)):
        admission_module.validate_package(p,sha)


@pytest.mark.parametrize('auth',['','I_AUTHORIZE_PD_SM_02_W1:'+REQ,'I_AUTHORIZE_PD_SM_02_W1_ADMISSION:'+REQ])
def test_admission_wrong_authorization_precedes_side_effects(admission_package,admission_module,monkeypatch,auth):
    p,sha=admission_package
    def forbidden(*a,**k):pytest.fail('Docker contacted before admission authorization')
    monkeypatch.setattr(admission_module.B,'Docker',forbidden)
    with pytest.raises(ValueError):admission_module.run_admission(p,sha,auth)
    assert not (p/'admission').exists() and not (p/'ADMISSION_CLAIM.json').exists()


def test_native_controller_rejects_the_zero_budget_admission_request(admission_package):
    p,sha=admission_package
    with pytest.raises((ValueError,TypeError,KeyError)):
        H.validate_package(p,sha)


@pytest.mark.parametrize('mode,expected_controls',[
    (None,2),('bad_daemon',0),('bad_image',0),('bad_outer',0),('bad_probe',1),
    ('cleanup_failure',1),('runtime_drift',2),('kernel_drift',2),
    ('wrong_timeout',1),('wrong_output',2)])
def test_admission_stops_without_any_candidate_on_all_backend_paths(
        admission_package,admission_backend,monkeypatch,mode,expected_controls):
    A=admission_backend;p,sha=admission_package;monkeypatch.setattr(AdmissionDocker,'mode',mode)
    result=A.run_admission(p,sha,admission_authorization(sha),host_context=admission_host_context())
    expected='ADMISSION_COMPLETED_UNATTESTED' if mode is None else 'ADMISSION_STOPPED_WITH_EVIDENCE'
    assert result['status']==expected
    assert_admission_boundary(result)
    assert (p/'admission/MANIFEST.json').is_file() and (p/'ADMISSION_CLAIM.json').is_file()
    replay=A.verify_admission(p,sha)
    assert replay['status']=='ADMISSION_RECORDS_REPLAYED' and replay['admission_status']==expected
    assert_admission_boundary(replay)
    started=[c for instance in AdmissionDocker.instances for c in instance.started]
    assert started==['probe-time','probe-output'][:expected_controls]
    for instance in AdmissionDocker.instances:
        assert all(call[:2] not in (['image','pull'],['container','run']) for call in instance.calls)
    with pytest.raises(ValueError):A.run_admission(p,sha,admission_authorization(sha),host_context=admission_host_context())


@pytest.fixture
def admission_completed(admission_package,admission_backend):
    A=admission_backend;p,sha=admission_package
    result=A.run_admission(p,sha,admission_authorization(sha),host_context=admission_host_context())
    assert result['status']=='ADMISSION_COMPLETED_UNATTESTED'
    return p,sha,A


def test_admission_replay_is_offline_and_does_not_authorize_native_run(admission_completed,monkeypatch):
    p,sha,A=admission_completed
    def forbidden(*a,**k):pytest.fail('Offline replay tried to start a process')
    monkeypatch.setattr(A.B,'Docker',forbidden);monkeypatch.setattr(subprocess,'Popen',forbidden)
    result=A.verify_admission(p,sha)
    assert result['status']=='ADMISSION_RECORDS_REPLAYED'
    assert result['admission_status']=='ADMISSION_COMPLETED_UNATTESTED'
    assert_admission_boundary(result)
    assert not (p/'CLAIM.json').exists() and not (p/'capture').exists()


@pytest.mark.parametrize('mutation',[
    'ready','image','daemon','mount','cleanup','token','time_termination','output_termination',
    'ready_transcript','runtime_drift','kernel_drift','authority','candidate_count','extra_candidate'])
def test_admission_replay_rejects_rehashed_false_success(admission_completed,mutation):
    p,sha,A=admission_completed;cap=p/'admission';x=None
    if mutation=='ready':
        path=cap/'probe-time/readiness.json';x=O.strict(path.read_bytes());x['interfaces']=['eth0','lo']
    elif mutation=='image':
        path=cap/'image_inspect.json';x=O.strict(path.read_bytes());x[0]['Id']='sha256:'+'f'*64
    elif mutation=='daemon':
        path=cap/'docker_info.json';x=O.strict(path.read_bytes());x['CgroupVersion']='1'
    elif mutation=='mount':
        path=cap/'probe-time/inspect_running.json';x=O.strict(path.read_bytes());x[0]['Mounts'][0]['RW']=True
    elif mutation=='cleanup':
        path=cap/'probe-time/cleanup.json';x=O.strict(path.read_bytes());x['removed_and_absence_checked']=False
    elif mutation=='token':
        path=cap/'probe-time/transport.json';x=O.strict(path.read_bytes());x['execution_token_sent']=False
    elif mutation in ('time_termination','output_termination'):
        label='probe-time' if mutation=='time_termination' else 'probe-output'
        path=cap/label/'transport.json';x=O.strict(path.read_bytes());x['termination']='exited'
    elif mutation=='ready_transcript':
        path=cap/'probe-time/stdout.jsonl';raw=path.read_bytes();path.write_bytes(raw.replace(sha.encode(),REQ.encode()))
    elif mutation in ('runtime_drift','kernel_drift'):
        path=cap/'probe-output/readiness.json';x=O.strict(path.read_bytes())
        x['python_sha256' if mutation=='runtime_drift' else 'kernel_release']='f'*64
        transcript=cap/'probe-output/stdout.jsonl'
        transcript.write_bytes((O.canonical(x)+b'\n'+transcript.read_bytes().partition(b'\n')[2])[:65536])
    elif mutation in ('authority','candidate_count'):
        path=cap/'summary.json';x=O.strict(path.read_bytes())
        x['authority_effect' if mutation=='authority' else 'new_candidate_executions']='allow' if mutation=='authority' else 1
    else:
        (cap/'P00').mkdir();(cap/'P00/candidate.py').write_text('raise RuntimeError("never executed")\n')
    if x is not None:path.write_bytes(O.canonical(x)+b'\n')
    reclose_admission(p)
    with pytest.raises((ValueError,TypeError,KeyError)):
        A.verify_admission(p,sha)


@pytest.mark.parametrize('label',['probe-time','probe-output'])
def test_admission_replay_rejects_missing_control_even_with_new_manifest(admission_completed,label):
    p,sha,A=admission_completed;shutil.rmtree(p/'admission'/label);reclose_admission(p)
    with pytest.raises((ValueError,OSError,KeyError)):A.verify_admission(p,sha)


@pytest.mark.parametrize('ending',[b'{',b'\xc3',b'\xff'])
def test_admission_output_truncation_is_narrow_and_hash_bound(admission_completed,ending):
    p,sha,A=admission_completed;path=p/'admission/probe-output/stdout.jsonl'
    raw=path.read_bytes();assert len(raw)==65536
    changed=raw[:-1]+ending;path.write_bytes(changed)
    with pytest.raises(ValueError):A.verify_admission(p,sha)
    reclose_admission(p)
    assert A.verify_admission(p,sha)['status']=='ADMISSION_RECORDS_REPLAYED'
    assert path.read_bytes()==changed


def test_admission_timeout_transcript_stays_strict(admission_completed):
    p,sha,A=admission_completed;path=p/'admission/probe-time/stdout.jsonl'
    raw=path.read_bytes();assert raw.endswith(b'\n');path.write_bytes(raw[:-1]);reclose_admission(p)
    with pytest.raises(ValueError):A.verify_admission(p,sha)


@pytest.mark.parametrize('field,value',[
    ('github_repository','elsewhere/other'),('github_sha','f'*40),
    ('github_workflow_sha','e'*40),('github_run_attempt','2'),
    ('runner_os','Windows'),('runner_arch','ARM64'),('image_os','ubuntu22'),
    ('image_version',''),('github_run_id','not-a-run')])
def test_admission_host_context_rejection_prevents_docker(
        admission_package,admission_backend,field,value):
    A=admission_backend;p,sha=admission_package;ctx=admission_host_context();ctx[field]=value
    result=A.run_admission(p,sha,admission_authorization(sha),host_context=ctx)
    assert result['status']=='ADMISSION_STOPPED_WITH_EVIDENCE'
    assert_admission_boundary(result)
    assert AdmissionDocker.instances==[]
    assert (p/'ADMISSION_CLAIM.json').is_file() and (p/'admission/MANIFEST.json').is_file()


@pytest.mark.parametrize('context',[None,{}, {'unknown':'value'}])
def test_admission_requires_complete_host_context(admission_package,admission_backend,context):
    A=admission_backend;p,sha=admission_package
    result=A.run_admission(p,sha,admission_authorization(sha),host_context=context)
    assert result['status']=='ADMISSION_STOPPED_WITH_EVIDENCE'
    assert_admission_boundary(result)
    assert AdmissionDocker.instances==[]


@pytest.mark.parametrize('mutation',['missing','extra','wrong_image','wrong_control','cleanup_inventory'])
def test_admission_command_record_replay_is_bound(admission_completed,mutation):
    p,sha,A=admission_completed;logs=p/'admission/docker_commands'
    commands=sorted(logs.glob('*.command.json'));assert commands
    if mutation=='missing':
        commands[0].unlink()
    elif mutation=='extra':
        source=commands[0]
        (logs/'999.command.json').write_bytes(source.read_bytes())
    else:
        target=None
        for command in commands:
            args=O.strict(command.read_bytes())
            if mutation=='wrong_image' and 'create' in args:
                args[args.index(ADMISSION_IMAGE)]='sha256:'+'f'*64;target=command;break
            if mutation=='wrong_control' and 'create' in args:
                args[args.index('pulse.w1.case=probe-time')]='pulse.w1.case=P00';target=command;break
            if mutation=='cleanup_inventory' and 'container' in args and 'ls' in args:
                target=command.with_name(command.name.replace('.command.json','.stdout'))
                target.write_bytes((p/'admission/probe-time/container.cid').read_bytes());break
        assert target is not None
        if mutation!='cleanup_inventory':target.write_bytes(O.canonical(args))
    reclose_admission(p)
    with pytest.raises((ValueError,TypeError,KeyError,OSError)):
        A.verify_admission(p,sha)


def test_admission_extra_package_file_cannot_smuggle_a_candidate(admission_package,admission_module):
    p,sha=admission_package;(p/'candidate.py').write_text('raise RuntimeError("never executed")\n')
    with pytest.raises((ValueError,TypeError,KeyError)):
        admission_module.validate_package(p,sha)


def test_admission_claim_is_not_a_native_claim(admission_completed):
    p,sha,A=admission_completed
    native_claim=p/'CLAIM.json'
    native_claim.write_bytes((p/'ADMISSION_CLAIM.json').read_bytes())
    with pytest.raises((ValueError,TypeError,KeyError)):
        A.validate_package(p,sha)



def admission_workflow():
    import yaml
    path=ROOT/'.github/workflows/paradox_w1_admission_v0.yml'
    return yaml.load(path.read_bytes(),Loader=yaml.BaseLoader)


def test_admission_workflow_is_single_manual_readonly_job():
    data=admission_workflow()
    assert set(data['on'])=={'workflow_dispatch'}
    assert set(data['on']['workflow_dispatch']['inputs'])=={'source_commit','acknowledgement'}
    assert data['permissions']=={'contents':'read'}
    assert data['concurrency']['cancel-in-progress']=='false'
    assert set(data['jobs'])=={'admission'}
    job=data['jobs']['admission']
    assert job['runs-on']=='ubuntu-24.04' and job['timeout-minutes']=='15'
    assert job['if']=="github.repository == 'HKati/pulse-release-gates-0.1'"
    for step in job['steps']:
        assert step.get('continue-on-error','false')=='false'
        if 'uses' in step:assert re.fullmatch(r'[^@]+@[0-9a-f]{40}',step['uses'])


def test_admission_workflow_requires_owner_main_source_and_first_attempt():
    steps=admission_workflow()['jobs']['admission']['steps']
    assert steps[0]['id']=='guard'
    guard=steps[0]['run']
    for text in ['test "$GITHUB_EVENT_NAME" = workflow_dispatch',
                 'test "$GITHUB_REF" = refs/heads/main','test "$GITHUB_ACTOR" = HKati',
                 'test "$GITHUB_ACTOR_ID" = 128643840','test "$GITHUB_TRIGGERING_ACTOR" = HKati',
                 'test "$GITHUB_RUN_ATTEMPT" = 1','test "$PD_SOURCE_COMMIT" = "$GITHUB_SHA"',
                 'test "$GITHUB_SHA" = "$GITHUB_WORKFLOW_SHA"',
                 'test "$PD_ADMISSION_ACKNOWLEDGEMENT" = ADMISSION_ONLY_ZERO_CANDIDATES']:
        assert text in guard
    checkout=next(x for x in steps if x['id']=='checkout')
    assert checkout['with']['ref']=='${{ github.sha }}'
    assert checkout['with']['persist-credentials']=='false'
    assert checkout['with']['fetch-depth']=='1'
    paths=checkout['with']['sparse-checkout'].splitlines()
    assert '/tools/run_paradox_w1_admission_v0.py' in paths
    assert '/.github/workflows/paradox_w1_admission_v0.yml' in paths
    assert not any(p.startswith(('/examples/','/tests/','/docs/evidence/')) for p in paths)


def test_admission_workflow_acquires_only_pinned_image_outside_controls():
    steps=admission_workflow()['jobs']['admission']['steps'];by_id={s['id']:s for s in steps}
    order=[s['id'] for s in steps]
    assert order.index('verify') < order.index('image') < order.index('admission')
    image=by_id['image']['run']
    assert 'docker.io/library/python@sha256:a7cb177dc60dfa77b223192cd0d9e6ce1aac7cf9a569023d68e7c91b6371a718' in image
    assert ADMISSION_IMAGE in image
    assert 'image pull --platform linux/amd64 "$pd_image_reference"' in image
    assert 'test "$(cat "$out/image-inspect.stdout")" = "$pd_expected_image"' in image
    assert '--host unix:///var/run/docker.sock --config "$pd_docker_config"' in image
    assert 'timeout --signal=TERM --kill-after=10s 240s' in image
    assert 'image pull' not in by_id['admission']['run']
    assert 'python:3.13.5-slim-bookworm' not in image


def test_admission_workflow_contains_no_candidate_launch_or_write_authority():
    data=admission_workflow();runs='\n'.join(s.get('run','') for s in data['jobs']['admission']['steps'])
    text=(ROOT/'.github/workflows/paradox_w1_admission_v0.yml').read_text()
    assert 'run_paradox_w1_admission_v0.py run-admission' in runs
    assert '--authorize-admission "I_AUTHORIZE_PD_SM_02_W1_ADMISSION:$PD_REQUEST_SHA256"' in runs
    for forbidden in ['I_AUTHORIZE_PD_SM_02_W1:', 'run_paradox_w1_native_v0.py execute',
                      '--case-id','git push','gh workflow run','workflow_dispatch --',
                      'contents: write','actions: write','id-token: write','secrets.']:
        assert forbidden not in text


def test_admission_workflow_replays_and_preserves_failed_attempts():
    steps={s['id']:s for s in admission_workflow()['jobs']['admission']['steps']}
    for key in ('replay','record','upload'):
        assert steps[key]['if']=="always() && steps.guard.outcome == 'success'"
    assert 'verify-admission' in steps['replay']['run']
    assert 'ADMISSION_COMPLETED_UNATTESTED' in steps['record']['run']
    assert "raise SystemExit(0 if completed else 1)" in steps['record']['run']
    upload=steps['upload']['with']
    assert upload['overwrite']=='false' and upload['retention-days']=='30'
    assert upload['if-no-files-found']=='error'
    assert upload['path']=='${{ runner.temp }}/pd-sm-02-w1-admission/'



def test_admission_preserved_package_replays_after_moving(admission_completed,tmp_path):
    p,sha,A=admission_completed;portable=tmp_path/'downloaded-admission'
    shutil.copytree(p,portable)
    shutil.rmtree(p)
    result=A.verify_admission(portable,sha)
    assert result['status']=='ADMISSION_RECORDS_REPLAYED'
    assert result['admission_status']=='ADMISSION_COMPLETED_UNATTESTED'
    assert_admission_boundary(result)


@pytest.mark.parametrize('mode,exitcode',[(None,0),('bad_daemon',2),('bad_probe',2),('cleanup_failure',2)])
def test_admission_cli_preserves_failure_exit_status(admission_package,admission_backend,monkeypatch,capsys,mode,exitcode):
    A=admission_backend;p,sha=admission_package;monkeypatch.setattr(AdmissionDocker,'mode',mode)
    context=p.parent/'host-context.json';context.write_bytes(O.canonical(admission_host_context()))
    code=A.main(['run-admission','--package',str(p),'--request-sha256',sha,
                 '--authorize-admission',admission_authorization(sha),'--host-context',str(context)])
    report=O.strict(capsys.readouterr().out.encode())
    assert code==exitcode and report['status']==('ADMISSION_COMPLETED_UNATTESTED' if mode is None else 'ADMISSION_STOPPED_WITH_EVIDENCE')
    assert_admission_boundary(report)
    code=A.main(['verify-admission','--package',str(p),'--request-sha256',sha])
    replay=O.strict(capsys.readouterr().out.encode())
    assert code==exitcode and replay['admission_status']==report['status']
    assert_admission_boundary(replay)



def test_admission_unknown_context_value_never_enters_retained_evidence(admission_package,admission_backend):
    p,sha=admission_package;A=admission_backend
    context=admission_host_context();marker=b'TOKEN_LEAK_TEST_DO_NOT_SAVE'
    context['unapproved_metadata']=marker.decode()
    report=A.run_admission(p,sha,admission_authorization(sha),host_context=context)
    assert report['status']=='ADMISSION_STOPPED_WITH_EVIDENCE'
    assert AdmissionDocker.instances==[]
    for path in (p/'admission').rglob('*'):
        if path.is_file():assert marker not in path.read_bytes()
    assert marker not in (p/'ADMISSION_CLAIM.json').read_bytes()
    assert_admission_boundary(A.verify_admission(p,sha))


def test_admission_stopped_summary_cannot_skip_failed_first_control(admission_completed):
    p,sha,A=admission_completed;path=p/'admission/summary.json'
    summary=O.strict(path.read_bytes())
    summary.update(status='ADMISSION_STOPPED_WITH_EVIDENCE',controls_completed=[],reason='synthetic failure')
    assert summary['controls_started']==['probe-time','probe-output']
    path.write_bytes(O.canonical(summary)+b'\n');reclose_admission(p)
    with pytest.raises(ValueError):A.verify_admission(p,sha)


def test_admission_orphan_command_output_cannot_hide_in_reclosed_manifest(admission_completed):
    p,sha,A=admission_completed;logs=p/'admission/docker_commands'
    (logs/'015.stdout').write_bytes(b'orphan output')
    reclose_admission(p)
    with pytest.raises(ValueError):A.verify_admission(p,sha)


@pytest.mark.parametrize('mutation',['case_argument','entrypoint','image','extra_label','stage_root','cidfile_root'])
def test_admission_stopped_evidence_still_checks_exact_create_command(admission_completed,mutation):
    p,sha,A=admission_completed;cap=p/'admission'
    path=cap/'summary.json';summary=O.strict(path.read_bytes())
    summary.update(status='ADMISSION_STOPPED_WITH_EVIDENCE',controls_completed=['probe-time'],reason='synthetic second control failure')
    path.write_bytes(O.canonical(summary)+b'\n')
    path=None
    for candidate in sorted((cap/'docker_commands').glob('*.command.json')):
        args=O.strict(candidate.read_bytes())
        if 'create' in args and 'pulse.w1.case=probe-output' in args:
            path=candidate;break
    assert path is not None
    if mutation=='case_argument':args[-1]='P00'
    elif mutation=='entrypoint':args[args.index('--entrypoint=/usr/bin/env')]='--entrypoint=/bin/sh'
    elif mutation=='image':args[args.index(ADMISSION_IMAGE)]='sha256:'+'f'*64
    elif mutation=='extra_label':
        pos=args.index('create')+1;args[pos:pos]=['--label','pulse.w1.case=P00']
    elif mutation=='stage_root':
        idx=args.index('--mount')+1
        args[idx]='type=bind,src=/different/stage/probe-output,dst=/inputs,readonly'
    else:
        args[args.index('--cidfile')+1]='/different/admission/probe-output/container.cid'
    path.write_bytes(O.canonical(args));reclose_admission(p)
    with pytest.raises((ValueError,TypeError,KeyError)):
        A.verify_admission(p,sha)


def test_admission_current_source_is_python311_syntax():
    ast.parse((TOOLS/'run_paradox_w1_admission_v0.py').read_text(),feature_version=(3,11))



def admission_path_guard(workflow_path,repo_root,monkeypatch):
    guard=module('w1_actual_path_guard',ROOT/'ci/check_path_refs_exist.py')
    monkeypatch.setattr(guard,'ROOT',repo_root)
    monkeypatch.setattr(guard,'iter_workflow_files',lambda:[workflow_path])
    missing=[];guard.check_workflows(missing)
    return missing


def test_admission_workflow_passes_actual_static_path_guard(monkeypatch):
    workflow_path=ROOT/'.github/workflows/paradox_w1_admission_v0.yml'
    assert admission_path_guard(workflow_path,ROOT,monkeypatch)==[]


def test_admission_actual_path_guard_rejects_checkout_prefix(tmp_path,monkeypatch):
    workflow_path=tmp_path/'.github/workflows/paradox_w1_admission_v0.yml'
    workflow_path.parent.mkdir(parents=True)
    raw=(ROOT/'.github/workflows/paradox_w1_admission_v0.yml').read_text()
    raw=raw.replace('python3 -I -S -B tools/', 'python3 -I -S -B tooling/tools/')
    workflow_path.write_text(raw)
    correct=tmp_path/'tools/run_paradox_w1_admission_v0.py';correct.parent.mkdir()
    correct.write_bytes((TOOLS/correct.name).read_bytes())
    assert admission_path_guard(workflow_path,tmp_path,monkeypatch)==[
        ('.github/workflows/paradox_w1_admission_v0.yml','tooling/tools/run_paradox_w1_admission_v0.py')]*4


@pytest.mark.parametrize('step_id',['prepare','verify','admission','replay'])
def test_admission_workflow_script_resolves_in_checkout(tmp_path,admission_module,step_id):
    import shlex
    data=admission_workflow();job=data['jobs']['admission'];steps={s['id']:s for s in job['steps']}
    workspace=tmp_path/'workspace';checkout=workspace/steps['checkout']['with']['path']
    (checkout/'tools').mkdir(parents=True)
    for name in admission_module.MODULES:
        (checkout/'tools'/name).write_bytes((TOOLS/name).read_bytes())
    step=steps[step_id];script=step['run']
    guard=module('w1_runtime_path_guard',ROOT/'ci/check_path_refs_exist.py')
    calls=[line for line in script.splitlines() if guard.PY_CALL_RE.search(line)]
    assert len(calls)==1
    line=calls[0];args=shlex.split(line.rstrip().removesuffix('\\'))
    # Execute the real CLI help from the checkout context reached by this step;
    # none of the prepare/execute/replay operations themselves is invoked.
    args[0]=sys.executable;args.append('--help')
    prefix=script.split(line,1)[0]
    directory_commands=re.findall(r'(?m)^\s*cd\s+[^\n]+$',prefix)
    check_script='set -euo pipefail\n'+'\n'.join(directory_commands)+'\nexec '+shlex.join(args)+'\n'
    initial=step.get('working-directory',job.get('defaults',{}).get('run',{}).get('working-directory','.'))
    initial=initial.replace('${{ github.workspace }}',str(workspace))
    cwd=Path(initial) if Path(initial).is_absolute() else workspace/initial
    result=subprocess.run(['bash','-c',check_script],cwd=cwd,
        env={'PATH':os.defpath,'GITHUB_WORKSPACE':str(workspace),'RUNNER_TEMP':str(tmp_path)},
        capture_output=True,text=True,timeout=10,check=False)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'usage:' in result.stdout and result.stderr==''


def test_admission_replay_without_request_does_not_require_checkout(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    runner=tmp_path/'runner';out=runner/'pd-sm-02-w1-admission';out.mkdir(parents=True)
    job=admission_workflow()['jobs']['admission'];step=next(s for s in job['steps'] if s['id']=='replay')
    initial=step.get('working-directory',job.get('defaults',{}).get('run',{}).get('working-directory','.'))
    initial=initial.replace('${{ github.workspace }}',str(workspace))
    cwd=Path(initial) if Path(initial).is_absolute() else workspace/initial
    result=subprocess.run(['bash','-c',step['run']],cwd=cwd,
        env={'PATH':os.defpath,'GITHUB_WORKSPACE':str(workspace),'RUNNER_TEMP':str(runner)},
        capture_output=True,text=True,timeout=10,check=False)
    assert result.returncode==0,result.stdout+result.stderr
    assert (out/'replay.status').read_text()=='NOT_RUN_NO_PREPARED_REQUEST\n'
    assert not (workspace/'tooling').exists() and not (out/'package').exists()


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__]))
