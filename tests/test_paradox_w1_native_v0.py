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


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__]))
