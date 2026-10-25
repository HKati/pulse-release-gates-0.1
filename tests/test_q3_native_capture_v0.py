"""Explicitly synthetic Q3 carrier/native-boundary regressions, never real capture.

Kernel observations and installed payload inventories here are fabricated TEST
DOUBLES. Passing these tests does not assert native qualification or inference.
"""
import base64
import copy
import errno
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import types
import zipfile
import pytest
from jsonschema import Draft202012Validator
from test_q3_native_capture_contract_v0 import ROOT, TOOLS, C, module, request, offline
from test_q3_native_capture_protocol_v0 import Tokenizer, W, R, P, FRAME
K=module('check_q3_native_capture_v0')
A=module('acquire_q3_reference_inputs_v0')


def sandbox(stage):
    unit='pulse-q3-'+'a'*24+'-'+stage+'.service'
    value={'stage':stage,'unit':unit,'pid':12345,'host_netns':'net:[100]','child_netns':'net:[101]',
        'uid':65534,'no_new_privs':True,'capabilities':'0000000000000000','ipv4_blocked':True,'ipv6_blocked':True,
        'memory_max':'4294967296','memory_swap_max':'0','pids_max':'64','cpu_max':'100000 100000',
        'properties':{k:R.PROPERTIES[k] for k in ['PrivateNetwork','NoNewPrivileges','ProtectSystem','ProtectHome',
            'KillMode','SendSIGKILL','User','Group','CapabilityBoundingSet','RestrictAddressFamilies']},
        'run_mount':{'host_namespace':'mnt:[100]','child_namespace':'mnt:[101]',
            'host_mountinfo':'1 2 0:1 / /run rw,nosuid,nodev - tmpfs tmpfs rw,size=16384k\n',
            'child_mountinfo':'1 2 0:2 / /run rw,nosuid,nodev,noexec - tmpfs tmpfs rw,size=16384k\n',
            'mount_stats':{'/run':{'device':'0:2','inode':1,'uid':0,'gid':0,'mode':stat.S_IFDIR|0o755}}}}
    seconds={'installer':480,'installcheck':300,'preflight':300,'decodecheck':300,'captureworker':14400}[stage]
    value['properties']['RuntimeMaxUSec']=str(seconds)+'s'
    if stage=='captureworker':value['capture_runtime_seconds']=seconds
    return value


def closure(stage):
    unit=sandbox(stage)['unit']
    return {'unit':unit,'launch_attempted':True,'properties':{'LoadState':'loaded','ActiveState':'inactive','ControlGroup':''},
            'cgroup_empty_or_removed':True,'client_reaped':True}


def installation_data(source):
    prep=C.strict_json(source[K.RECORD_DIR+'preparation.json'])
    bootstrap=[{'path':'bin/python','size':1,'sha256':'a'*64,'mode':0o755},
               {'path':'pyvenv.cfg','size':1,'sha256':'b'*64,'mode':0o644}]
    installed=list(bootstrap);distributions={};items=[]
    for row in prep['wheels']:
        path='lib/python3.11/site-packages/'+row['name']+'-'+row['version']+'.dist-info/METADATA'
        installed.append({'path':path,'size':1,'sha256':'c'*64,'mode':0o644})
        distributions[row['name']]={'version':row['version'],'metadata':path}
        items.append({'metadata':{'name':row['name'],'version':row['version']},
                      'download_info':{'url':'file:///var/lib/synthetic-q3/bundle/'+row['path'],
                                       'archive_info':{'hashes':{'sha256':row['sha256']}}}})
    pip={'version':'1','pip_version':'test-only','install':items}
    output={'record_type':'q3_native_installation_check_v0','distributions':distributions,
        'wheel_payload_file_count':30,'generated_non_worker_launchers':[],
        'bootstrap_inventory_sha256':C.digest(C.encode(bootstrap)), 'pip_report_sha256':C.digest(C.encode(pip)),
        'inventory':installed,'authority_effect':'none','production_gate_eligible':False}
    return {'bootstrap.json':C.encode(bootstrap),'pip-report.json':C.encode(pip),'installation.json':C.encode(output)}


def evidence(mode='token-preflight'):
    """Synthetic test-only full carrier. There is no production CLI for this."""
    source={name:(ROOT/name).read_bytes() for name in P['source_files']}
    data={'source/'+n:b for n,b in source.items()};data.update(installation_data(source))
    r=request(mode);mapping=W.tokenize_frame(Tokenizer(),FRAME,P)
    if mode=='capture':r['approved_token_map_sha256']=C.digest(C.encode(mapping))
    data['request.json']=C.encode(r)
    platform={'os':'ubuntu-24.04','architecture':'x86_64','python':'3.11.16','runner_image':'synthetic-test-only',
        'kernel':'synthetic','libc':['glibc','synthetic'],'bootstrap_python_sha256':'d'*64,
        'contract':'q3_observed_ubuntu24_cpu_runtime_v0','historical_platform_equivalence':False}
    plane={'run_id':'12345','run_attempt':1,'source_commit':r['source_commit'],'repository':C.REPOSITORY,
        'repository_private':False,'event':'workflow_dispatch','workflow':C.WORKFLOW,'head_branch':'main',
        'actor':'HKati','triggering_actor':'HKati','clock_relation':'not_verified'}
    data['platform.json']=C.encode(platform);data['control-plane.json']=C.encode(plane)
    pre={'record_type':'q3_native_prelaunch_v0','request':r,'source_commit':r['source_commit'],
        'run_id':'12345','run_attempt':1,'source_files':{n:C.digest(b) for n,b in source.items()},
        'platform_sha256':C.digest(data['platform.json']),'control_plane_sha256':C.digest(data['control-plane.json']),
        'installation_sha256':C.digest(data['installation.json']),'started_at':'2026-10-24T00:00:00+00:00','clock_relation':'not_verified'}
    data['prelaunch.json']=C.encode(pre)
    binding={'prelaunch_sha256':C.digest(data['prelaunch.json']),'source_commit':r['source_commit'],'run_id':'12345','run_attempt':1}
    data['worker-ready.json']=C.encode({'record_type':'q3_worker_ready_v0','binding':binding,'mode':mode})
    data['token-map.json']=C.encode(mapping);ms=C.digest(data['token-map.json'])
    for row in mapping['rows']:data['tokens/'+row['task_id']+'.json']=C.encode({'record_type':'q3_token_row_v0','binding':binding,'row':row})
    data['token-map-end.json']=C.encode({'record_type':'q3_token_map_end_v0','binding':binding,'token_map_sha256':ms,'task_count':204})
    full=binding;occ=[];timers=[];examples=[];generation={**P['generation'],'disable_compile':True};runtime=K.expected_runtime(P)
    if mode=='capture':
        data['model-ready.json']=C.encode({'record_type':'q3_model_ready_v0','binding':binding,
             'token_map_sha256':ms,'effective_generation':generation,'runtime':runtime})
        data['subject.json']=C.encode({'record_type':'q3_capture_subject_v0','binding':binding,
             'model_ready_sha256':C.digest(data['model-ready.json']),'token_map_sha256':ms})
        full={**binding,'subject_sha256':C.digest(data['subject.json'])}
        data['bound.json']=C.encode({'record_type':'q3_bound_v0','binding':full})
    for task,row in zip(FRAME,mapping['rows']):
        slot={'task_id':task['task_id'],'ordinal':task['ordinal'],'attempt':1}
        if mode=='capture':
            stem='calls/'+task['task_id'];moment=task['ordinal']*100_000_000_000
            ready={'record_type':'q3_slot_ready_v0','binding':full,'slot':slot,'input_ids':row['input_ids'],
                   'effective_generation':generation,'runtime':runtime}
            text='synthetic response'
            response={**ready,'record_type':'q3_response_v0','new_token_ids':[4,2],'text':text,
                      'text_utf8_base64':base64.b64encode(text.encode()).decode(),'stop_reason':'eos'}
            data[stem+'.ready.json']=C.encode(ready);data[stem+'.response.json']=C.encode(response);data[stem+'.utf8']=text.encode()
            data[stem+'.intent.json']=C.encode({**slot,'binding':full,'intent':'before_GO'})
            occ.append({**slot,'status':'completed','intent_saved_ns':moment,'watchdog_arm_begin_ns':moment+1,
                'generation_start_ns':moment+2,'generation_deadline_ns':moment+2+60_000_000_000,
                'response_received_ns':moment+3,'watchdog_closed_ns':moment+4})
            prefix='pulse-q3-'+'a'*24+f"-call-{task['ordinal']:03d}"
            timers.append({'prefix':prefix,'closure':{'units':[{'unit':prefix+'-watchdog'+suffix,
                 'LoadState':'not-found','ActiveState':'inactive'} for suffix in ['.timer','.service']], 'closed_ns':moment+4}})
            examples.append({'example_id':task['task_id'],'prompt':task['prompt'],'response':text,
                             'context':task['context'],'metadata':{'task_form':task['task_form']}})
        else:occ.append({**slot,'status':'not_requested'})
    if mode=='capture':data['examples.jsonl']=b''.join(C.encode(x) for x in examples)
    data['session-end.json']=C.encode({'record_type':'q3_session_end_v0','binding':full,'completed_calls':204 if mode=='capture' else 0})
    terminal={'record_type':'q3_capture_terminal_v0','mode':mode,'binding':binding,'complete':True,'error_code':None,
        'attempted_calls':204 if mode=='capture' else 0,'occurrences':occ,'worker_exit_code':0,'stdout_eof':True,
        'worker_deadline_ns':30_000_000_000_000,'worker_exit_observed_ns':29_000_000_000_000,
        'ended_at':'2026-10-24T00:30:00+00:00'}
    data['terminal.json']=C.encode(terminal)
    data['token-check.json']=C.encode({'record_type':'q3_native_token_check_v0','request_sha256':C.digest(data['request.json']),
        'prelaunch_sha256':C.digest(data['prelaunch.json']),'token_map_sha256':ms,'checked_tasks':204,
        'checked_responses':204 if mode=='capture' else 0,'tokenization_reperformed':True,'generation_executed':False,
        'examples_sha256':C.digest(data['examples.jsonl']) if mode=='capture' else None,'claims':dict(C.CLAIMS)})
    data['input-check.json']=C.encode({'record_type':'q3_runtime_input_check_v0','archive_sha256':K.ARCHIVE_SHA,
        'archive_size':K.ARCHIVE_SIZE,'member_count':78,'wheel_count':30,'claims':dict(C.CLAIMS)})
    services=[]
    for stage in ['installer','installcheck','captureworker' if mode=='capture' else 'preflight','decodecheck']:
        stem='worker' if stage in ('captureworker','preflight') else stage
        data[stem+'-sandbox.json']=C.encode(sandbox(stage));data[stem+'-cleanup.json']=C.encode(closure(stage))
        services.append(closure(stage))
    data['lifecycle.json']=C.encode({'cleanup_complete':True,'errors':[],'services':services,'timers':timers,'private_tree_removed':True})
    return source,data,r


def mutate(data,name,fn):
    value=C.strict_json(data[name]);fn(value);data[name]=C.encode(value)

@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_complete_synthetic_carrier_roundtrip_and_schema(tmp_path,mode):
    source,data,r=evidence(mode);assert K.validate_complete(source,data)['complete'] is True
    raw,result=A.build_carrier(C,data,r,'complete',None);archive=tmp_path/'evidence.zip';archive.write_bytes(raw)
    schema=json.loads((ROOT/'schemas/metrics/q3_native_capture_result_v0.schema.json').read_text())
    Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(result)
    checked=K.check_carrier(archive,source,C.digest(raw),C.digest(data['request.json']),r['source_commit'])
    assert checked['complete'] is True and checked['native_origin_reacquired'] is False
    assert checked['metric_recomputed'] is False and checked['tokenization_reperformed'] is False
    if mode=='capture':assert len(data['examples.jsonl'].splitlines())==204
    else:assert 'examples.jsonl' not in data

@pytest.mark.parametrize('fault',['extra_member','missing_member','source','ordinal','attempt_bool','run_bool','end_count',
    'empty_expected','token_ids','token_hash','cleanup_false','private_tree','cleanup_service','host_net','uid','cpu',
    'mount_ns','mount_flags','mount_size','mode','installation_empty','pip_empty','bootstrap_empty','install_version',
    'claim','clock','date','receipt_generation','runtime_claim'])
def test_coherent_rehash_cannot_hide_preflight_defects(tmp_path,fault):
    source,data,r=evidence()
    if fault=='extra_member':data['extra.json']=b'{}'
    elif fault=='missing_member':data.pop('tokens/'+FRAME[0]['task_id']+'.json')
    elif fault=='source':data['source/'+C.FRAME+'COMMON_INSTRUCTIONS.txt']+=b'x'
    elif fault=='ordinal':mutate(data,'terminal.json',lambda x:x['occurrences'][0].update(ordinal=2))
    elif fault=='attempt_bool':mutate(data,'terminal.json',lambda x:x['occurrences'][0].update(attempt=True))
    elif fault=='run_bool':mutate(data,'control-plane.json',lambda x:x.update(run_attempt=True))
    elif fault=='end_count':mutate(data,'session-end.json',lambda x:x.update(completed_calls=1))
    elif fault=='empty_expected':mutate(data,'terminal.json',lambda x:x.update(occurrences=[]))
    elif fault=='token_ids':mutate(data,'token-map.json',lambda x:x['rows'][0].update(input_ids=[True]))
    elif fault=='token_hash':mutate(data,'token-map.json',lambda x:x['rows'][0].update(messages_sha256='0'*64))
    elif fault=='cleanup_false':mutate(data,'lifecycle.json',lambda x:x.update(cleanup_complete=False))
    elif fault=='private_tree':mutate(data,'lifecycle.json',lambda x:x.update(private_tree_removed=False))
    elif fault=='cleanup_service':mutate(data,'lifecycle.json',lambda x:x['services'].pop())
    elif fault=='host_net':mutate(data,'worker-sandbox.json',lambda x:x.update(child_netns=x['host_netns']))
    elif fault=='uid':mutate(data,'worker-sandbox.json',lambda x:x.update(uid=0))
    elif fault=='cpu':mutate(data,'worker-sandbox.json',lambda x:x.update(cpu_max='max 100000'))
    elif fault=='mount_ns':mutate(data,'worker-sandbox.json',lambda x:x['run_mount'].update(child_namespace='mnt:[100]'))
    elif fault=='mount_flags':mutate(data,'worker-sandbox.json',lambda x:x['run_mount'].update(child_mountinfo=x['run_mount']['child_mountinfo'].replace(',noexec','')))
    elif fault=='mount_size':mutate(data,'worker-sandbox.json',lambda x:x['run_mount'].update(child_mountinfo=x['run_mount']['child_mountinfo'].replace('16384k','32768k')))
    elif fault=='mode':mutate(data,'terminal.json',lambda x:x.update(mode='capture'))
    elif fault=='installation_empty':mutate(data,'installation.json',lambda x:x.update(inventory=[]))
    elif fault=='pip_empty':mutate(data,'pip-report.json',lambda x:x.update(install=[]))
    elif fault=='bootstrap_empty':data['bootstrap.json']=b'[]\n'
    elif fault=='install_version':mutate(data,'installation.json',lambda x:x['distributions']['torch'].update(version='other'))
    elif fault=='claim':mutate(data,'input-check.json',lambda x:x['claims'].update(authority_effect='allow'))
    elif fault=='clock':mutate(data,'prelaunch.json',lambda x:x.update(clock_relation='synchronized'))
    elif fault=='date':mutate(data,'prelaunch.json',lambda x:x.update(started_at='2026-10-24T24:00:00+00:00'))
    elif fault=='receipt_generation':mutate(data,'token-check.json',lambda x:x.update(generation_executed=True))
    elif fault=='runtime_claim':mutate(data,'platform.json',lambda x:x.update(historical_platform_equivalence=True))
    raw,_=A.build_carrier(C,data,r,'complete',None);path=tmp_path/'bad.zip';path.write_bytes(raw)
    with pytest.raises((ValueError,KeyError)):
        K.check_carrier(path,source,C.digest(raw),C.digest(data['request.json']),r['source_commit'])

@pytest.mark.parametrize('fault',['response_text','response_base64','response_tokens','response_prefix','ready','intent','deadline',
    'timing_bool','partial','no_eof','exit_bool','no_finish','projection','timer','additional_call','generation'])
def test_capture_negative_cases_survive_carrier_rehash(tmp_path,fault):
    source,data,r=evidence('capture');stem='calls/'+FRAME[0]['task_id']
    if fault=='response_text':mutate(data,stem+'.response.json',lambda x:x.update(text='changed'))
    elif fault=='response_base64':mutate(data,stem+'.response.json',lambda x:x.update(text_utf8_base64='AAAA'))
    elif fault=='response_tokens':mutate(data,stem+'.response.json',lambda x:x.update(new_token_ids=[4]*256,stop_reason='token_limit'))
    elif fault=='response_prefix':mutate(data,stem+'.response.json',lambda x:x.update(input_ids=[1,99]))
    elif fault=='ready':mutate(data,stem+'.ready.json',lambda x:x['slot'].update(task_id='foreign'))
    elif fault=='intent':mutate(data,stem+'.intent.json',lambda x:x.update(intent='after_GO'))
    elif fault=='deadline':mutate(data,'terminal.json',lambda x:x['occurrences'][0].update(response_received_ns=10**15))
    elif fault=='timing_bool':mutate(data,'terminal.json',lambda x:x['occurrences'][0].update(intent_saved_ns=True))
    elif fault=='partial':mutate(data,'terminal.json',lambda x:x['occurrences'][1].update(status='not_started'))
    elif fault=='no_eof':mutate(data,'terminal.json',lambda x:x.update(stdout_eof=False))
    elif fault=='exit_bool':mutate(data,'terminal.json',lambda x:x.update(worker_exit_code=False))
    elif fault=='no_finish':data.pop('session-end.json')
    elif fault=='projection':data['examples.jsonl']=data['examples.jsonl'].replace(b'synthetic response',b'changed',1)
    elif fault=='timer':mutate(data,'lifecycle.json',lambda x:x['timers'][0]['closure']['units'][0].update(ActiveState='active'))
    elif fault=='additional_call':data['calls/extra.response.json']=b'{}'
    elif fault=='generation':mutate(data,'model-ready.json',lambda x:x['effective_generation'].update(do_sample=True))
    raw,_=A.build_carrier(C,data,r,'complete',None);path=tmp_path/'bad.zip';path.write_bytes(raw)
    with pytest.raises((ValueError,KeyError)):
        K.check_carrier(path,source,C.digest(raw),C.digest(data['request.json']),r['source_commit'])


def test_incomplete_archive_stays_incomplete_even_with_inventory_match(tmp_path):
    r=request();data={'request.json':C.encode(r),'partial.bin':b'synthetic incomplete bytes'}
    source={n:(ROOT/n).read_bytes() for n in P['source_files']}
    raw,_=A.build_carrier(C,data,r,'incomplete','CAPTURE_INTERRUPTED');path=tmp_path/'partial.zip';path.write_bytes(raw)
    out=K.check_carrier(path,source,C.digest(raw),C.digest(data['request.json']),r['source_commit'])
    assert out['complete'] is False and out['failure_inventory_verified'] is True

@pytest.mark.parametrize('fault',['archive','request','commit'])
def test_external_anchor_not_self_selected(tmp_path,fault):
    source,data,r=evidence();raw,_=A.build_carrier(C,data,r,'complete',None);path=tmp_path/'e.zip';path.write_bytes(raw)
    anchors=[C.digest(raw),C.digest(data['request.json']),r['source_commit']]
    anchors[['archive','request','commit'].index(fault)]='0'*(40 if fault=='commit' else 64)
    with pytest.raises(ValueError):K.check_carrier(path,source,*anchors)

@pytest.mark.parametrize('name',['../escape','/absolute','dir/../escape','a//b','a\\b'])
def test_carrier_unsafe_member_names_rejected(tmp_path,name):
    path=tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as z:z.writestr(name,b'{}')
    raw=path.read_bytes()
    with pytest.raises(ValueError):K.check_carrier(path,ROOT,C.digest(raw),'a'*64,'b'*40)


def test_no_artifact_or_network_acquisition_on_bad_entry(tmp_path,monkeypatch):
    monkeypatch.setattr(A,'api_bytes',lambda *a,**k:pytest.fail('network before guard'))
    monkeypatch.setattr(A,'load_sealed',lambda *a,**k:pytest.fail('helper before guard'))
    assert A.main(['--repo-root',str(tmp_path),'--source-commit','a'*40,'--request','{}','--request-sha256',C.digest(b'{}')])==2
    assert not list(tmp_path.iterdir())


def test_read_large_binary_uses_binary_limit_not_control_limit(tmp_path):
    path=tmp_path/'native.so';raw=b'x'*(C.MAX_CONTROL+1);path.write_bytes(raw)
    assert K.read(path)==raw
    with pytest.raises(ValueError):K.read(path,C.MAX_CONTROL)

@pytest.mark.parametrize('fault',['write','import','chmod'])
def test_setup_failure_removes_owned_workspace_before_any_launch(tmp_path,monkeypatch,fault):
    work=tmp_path/'new';source={n:(ROOT/n).read_bytes() for n in P['source_files']}
    if fault=='write':monkeypatch.setattr(C,'write_new',lambda *a,**k:(_ for _ in ()).throw(OSError('write')))
    elif fault=='import':monkeypatch.setattr(A,'load_sealed',lambda *a,**k:(_ for _ in ()).throw(OSError('import')))
    else:
        original=A.os.chmod;calls=[]
        def bad(*a,**k):
            calls.append(1)
            if len(calls)==1:raise OSError('chmod')
            return original(*a,**k)
        monkeypatch.setattr(A.os,'chmod',bad)
    with pytest.raises(A.EntryRejected) as caught:A.setup_workspace(C,source,work)
    assert caught.value.cleanup_complete is True and not work.exists()


def test_setup_never_removes_preexisting_directory(tmp_path):
    work=tmp_path/'existing';work.mkdir();(work/'sentinel').write_bytes(b'keep')
    with pytest.raises(A.EntryRejected) as caught:A.setup_workspace(C,{},work)
    assert caught.value.cleanup_complete is False and (work/'sentinel').read_bytes()==b'keep'


def test_setup_reports_cleanup_failure(tmp_path,monkeypatch):
    work=tmp_path/'new'
    monkeypatch.setattr(A,'load_sealed',lambda *a,**k:(_ for _ in ()).throw(OSError('import')))
    monkeypatch.setattr(A.shutil,'rmtree',lambda *a,**k:(_ for _ in ()).throw(OSError('cleanup')))
    with pytest.raises(A.EntryRejected) as caught:A.setup_workspace(C,{},work)
    assert caught.value.cleanup_complete is False and work.is_dir()


def test_failure_code_never_echoes_secret_paths_or_raw_exceptions():
    assert A.failure_code(OSError('/secret/token'))=='RUNTIME_OR_EVIDENCE_UNAVAILABLE'
    assert A.failure_code(ValueError('secret = value'))=='RUNTIME_OR_EVIDENCE_UNAVAILABLE'
    assert A.failure_code(KeyboardInterrupt())=='CAPTURE_INTERRUPTED'

@pytest.mark.parametrize('fault',['check','chown','readback'])
def test_failed_handoff_never_leaves_success_receipt(tmp_path,monkeypatch,fault):
    source,data,r=evidence();out=tmp_path/'out';out.mkdir()
    if fault=='check':monkeypatch.setattr(K,'check_carrier',lambda *a,**k:(_ for _ in ()).throw(ValueError('injected')))
    elif fault=='chown':monkeypatch.setattr(A.os,'fchown',lambda *a,**k:(_ for _ in ()).throw(OSError('injected')))
    else:
        original=C.safe_read
        def bad(path,*args,**kw):
            raw=original(path,*args,**kw)
            if Path(path).name=='receipt.json' and (out/'receipt.json').exists():return b'wrong'
            return raw
        monkeypatch.setattr(C,'safe_read',bad)
    with pytest.raises((ValueError,OSError)):A.publish(C,K,source,out,os.getuid(),os.getgid(),data,r,'complete',None)
    assert not (out/'receipt.json').exists()


def test_successful_handoff_exact_bytes_and_modes(tmp_path):
    source,data,r=evidence();out=tmp_path/'out';out.mkdir()
    receipt=A.publish(C,K,source,out,os.getuid(),os.getgid(),data,r,'complete',None)
    assert set(p.name for p in out.iterdir())=={'evidence.zip','receipt.json'}
    assert stat.S_IMODE(out.stat().st_mode)==0o700
    assert all(stat.S_IMODE(p.stat().st_mode)==0o600 for p in out.iterdir())
    assert C.strict_json((out/'receipt.json').read_bytes())==receipt

@pytest.mark.parametrize('fault',['empty','bool','duplicate','mode','symlink'])
def test_bootstrap_rows_fail_closed(fault):
    rows=[{'path':'bin/python','size':1,'sha256':'a'*64,'mode':0o755}]
    if fault=='empty':rows=[]
    elif fault=='bool':rows[0]['size']=True
    elif fault=='duplicate':rows.append(copy.deepcopy(rows[0]))
    elif fault=='mode':rows[0]['mode']=0o10000
    elif fault=='symlink':rows=[{'path':'bin/python','symlink':'/outside'}]
    with pytest.raises(ValueError):K.frozen_bootstrap_inventory(C.encode(rows))

@pytest.mark.parametrize('value',['','1d','infinity','-1s','1.5s',True])
def test_duration_parser_rejects_unbounded_or_ambiguous_values(value):
    with pytest.raises(ValueError):K.duration(value)


def test_publication_preserves_a_substituted_member(tmp_path,monkeypatch):
    source,data,r=evidence();out=tmp_path/'out';out.mkdir()
    original=K.check_carrier
    def replaced(path,*args,**kwargs):
        result=original(path,*args,**kwargs)
        path.rename(out/'owned-original.zip')
        path.write_bytes(b'unrelated replacement')
        return result
    monkeypatch.setattr(K,'check_carrier',replaced)
    with pytest.raises(ValueError,match='REPLACED'):
        A.publish(C,K,source,out,os.getuid(),os.getgid(),data,r,'complete',None)
    assert (out/'evidence.zip').read_bytes()==b'unrelated replacement'
    assert (out/'owned-original.zip').exists() and not (out/'receipt.json').exists()


def test_fixed_wheel_plus_filename_is_safe_not_source_path_relaxation():
    name='lib/python3.11/site-packages/torch-2.8.0+cpu.dist-info/METADATA'
    assert K.relative(name)==name
    with pytest.raises(ValueError):C.relative(name)

@pytest.mark.parametrize('mode,fault',[('token-preflight',None),('capture',None),('capture','decode'),
    ('capture','worker'),('token-preflight','cleanup'),('token-preflight','source')])
def test_actual_controller_to_publication_with_explicit_native_doubles(tmp_path,monkeypatch,mode,fault):
    """Real controller/files/carrier; synthetic host/install/process/token phases.

    This checks orchestration, error retention and final independent validation.
    It is explicitly not a native observation or actual model/tokenizer call.
    """
    source,fixture,r=evidence(mode);raw=C.encode(r);out=tmp_path/'out';out.mkdir()
    host=tmp_path/'host';host.mkdir();loaded={};actual_path=Path;active=[]
    monkeypatch.setattr(A,'Path',lambda x:host if x=='/var/lib' else actual_path(x))
    monkeypatch.setattr(A,'control_plane',lambda *a:C.strict_json(fixture['control-plane.json']))
    monkeypatch.setattr(A,'output_destination',lambda *a:(out,os.getuid(),os.getgid()))
    monkeypatch.setattr(A,'download_runtime',lambda *a:None)
    monkeypatch.setattr(A.shutil,'disk_usage',lambda *a:types.SimpleNamespace(free=10*1024**3))
    original_load=A.load_sealed
    def loader(name,path):
        mod=original_load(name,path)
        if name=='q3_verified_independent_checker':
            def archive(archive,destination,sources):
                (destination/'bundle/wheelhouse').mkdir(parents=True)
                return C.strict_json(fixture['input-check.json'])
            mod.verify_archive=archive;loaded['K']=mod
        if name=='q3_verified_runtime':
            loaded['R']=mod
            mod.freeze=lambda *a:None  # explicitly no root/isolation claim in this double
            def private(path,**kwargs):
                path.mkdir();os.chmod(path,kwargs.get('mode',0o700));return path
            mod.private_directory=private
            mod.platform_context=lambda:C.strict_json(fixture['platform.json'])
            class Reader:
                buffer=b''
                def __init__(self,svc):self.svc=svc;self.selector=types.SimpleNamespace(select=lambda t:bool(svc.queue))
                def line(self,deadline):
                    assert time.monotonic()<deadline
                    if not self.svc.queue:raise ValueError('synthetic_protocol_eof')
                    return self.svc.queue.pop(0)
            class Svc:
                def __init__(self,prefix,stage,command,work,python,log,deadline):
                    self.unit=prefix+'-'+stage+'.service';self.stage=stage;self.deadline=deadline
                    self.runtime_deadline_ns=int(deadline*1e9);self.observation=sandbox(stage)
                    self.observation['unit']=self.unit;self.cleanup=None;self.queue=[];self.reader=Reader(self);self.ended=False
                    self.ev=work.parent/'evidence';self.pre=C.strict_json((self.ev/'prelaunch.json').read_bytes())
                    self.binding={'prelaunch_sha256':C.digest((self.ev/'prelaunch.json').read_bytes()),
                        'source_commit':r['source_commit'],'run_id':'12345','run_attempt':1}
                    self.mapping=W.tokenize_frame(Tokenizer(),FRAME,P);self.calls=0;self.next=0
                    self.queue.append(C.encode({'record_type':'q3_worker_ready_v0','binding':self.binding,'mode':mode}))
                    active.append(self)
                def send(self,cmd):
                    start=time.monotonic_ns()
                    if cmd==b'TOKENIZE\n':
                        self.queue.extend(C.encode({'record_type':'q3_token_row_v0','binding':self.binding,'row':row}) for row in self.mapping['rows'])
                        self.queue.append(C.encode({'record_type':'q3_token_map_end_v0','binding':self.binding,
                            'token_map_sha256':C.digest(C.encode(self.mapping)),'task_count':204}))
                    elif cmd.startswith(b'LOAD '):
                        self.ready={'record_type':'q3_model_ready_v0','binding':self.binding,
                            'token_map_sha256':C.digest(C.encode(self.mapping)),
                            'effective_generation':{**P['generation'],'disable_compile':True},'runtime':K.expected_runtime(P)}
                        self.queue.append(C.encode(self.ready))
                    elif cmd.startswith(b'BIND '):
                        self.full={**self.binding,'subject_sha256':cmd[5:-1].decode()}
                        self.queue.append(C.encode({'record_type':'q3_bound_v0','binding':self.full}))
                    elif cmd.startswith(b'PREPARE '):
                        task=FRAME[self.next];assert cmd==('PREPARE '+task['task_id']+'\n').encode()
                        self.slot={'task_id':task['task_id'],'ordinal':task['ordinal'],'attempt':1}
                        self.slotready={'record_type':'q3_slot_ready_v0','binding':self.full,'slot':self.slot,
                            'input_ids':self.mapping['rows'][self.next]['input_ids'],
                            'effective_generation':self.ready['effective_generation'],'runtime':self.ready['runtime']}
                        self.queue.append(C.encode(self.slotready))
                    elif cmd.startswith(b'GENERATE '):
                        assert cmd==('GENERATE '+FRAME[self.next]['task_id']+'\n').encode();self.calls+=1
                        if fault!='worker':
                            text='synthetic response'
                            self.queue.append(C.encode({**self.slotready,'record_type':'q3_response_v0',
                              'new_token_ids':[4,2],'text':text,'text_utf8_base64':base64.b64encode(text.encode()).decode(),'stop_reason':'eos'}))
                        self.next+=1
                    elif cmd==b'FINISH\n':
                        self.queue.append(C.encode({'record_type':'q3_session_end_v0','binding':self.full if mode=='capture' else self.binding,
                                                  'completed_calls':self.calls}));self.ended=True
                    else:raise AssertionError('unrecognized synthetic command')
                    return start
                def complete(self):assert self.ended and not self.queue
                def close(self,deadline):
                    self.cleanup=closure(self.stage);self.cleanup['unit']=self.unit;return self.cleanup
            class Life:
                def __init__(self):self.services=[];self.timers=[]
                def start(self,*args):s=Svc(*args);self.services.append(s);return s
                def arm(self,prefix,unit):self.timers.append({'prefix':prefix,'closure':None})
                def disarm(self,prefix,deadline):
                    assert self.timers[-1]['prefix']==prefix
                    close={'units':[{'unit':prefix+'-watchdog'+suffix,'LoadState':'not-found','ActiveState':'inactive'} for suffix in ['.timer','.service']],
                           'closed_ns':time.monotonic_ns()};self.timers[-1]['closure']=close;return close
                def cleanup(self):
                    for svc in self.services:
                        if svc.cleanup is None:svc.close(time.monotonic()+5)
                    for timer in self.timers:
                        if timer['closure'] is None:timer['closure']={'synthetic_unfinished_timer':True}
                    return {'cleanup_complete':fault!='cleanup','errors':['synthetic_cleanup'] if fault=='cleanup' else [],
                            'services':[s.cleanup for s in self.services],'timers':self.timers}
            mod.Lifecycle=Life
            def phase(life,prefix,stage,command,work,python,logs,deadline,ev):
                sb=sandbox(stage);sb['unit']=prefix+'-'+stage+'.service';cl=closure(stage);cl['unit']=sb['unit']
                life.services.append(types.SimpleNamespace(cleanup=cl))
                mod.save(ev/(stage+'-sandbox.json'),C.encode(sb));mod.save(ev/(stage+'-cleanup.json'),C.encode(cl))
                if stage=='installer':
                    (work/'venv/bin').mkdir(parents=True);(work/'venv/bin/python').write_bytes(b'synthetic-not-executable')
                    for name in ['bootstrap.json','pip-report.json']:mod.save(work/name,fixture[name])
                elif stage=='installcheck':mod.save(work/'installation.json',fixture['installation.json'])
                else:
                    if fault=='decode':raise ValueError('synthetic_decode_failure')
                    checker=loaded['K'];d=checker.read_evidence(ev)
                    req,mapping,examples=checker.validate_protocol(ev.parent/'source',d)
                    check={'record_type':'q3_native_token_check_v0','request_sha256':C.digest(d['request.json']),
                        'prelaunch_sha256':C.digest(d['prelaunch.json']),'token_map_sha256':C.digest(d['token-map.json']),
                        'checked_tasks':204,'checked_responses':204 if mode=='capture' else 0,
                        'tokenization_reperformed':True,'generation_executed':False,
                        'examples_sha256':C.digest(examples) if examples is not None else None,'claims':dict(C.CLAIMS)}
                    mod.save(work/'token-check.json',C.encode(check))
                    if examples is not None:mod.save(work/'examples.jsonl',examples)
                    if fault=='source':
                        path=ev.parent/'source'/C.FRAME/'COMMON_INSTRUCTIONS.txt';os.chmod(path,0o600);path.write_bytes(b'changed')
            mod.phase=phase
        return mod
    monkeypatch.setattr(A,'load_sealed',loader)
    rc=A.execute(C,P,r,source,ROOT,raw,{'GITHUB_TOKEN':'synthetic-token-never-sent','GITHUB_RUN_ID':'12345'})
    assert rc==(0 if fault is None else 1)
    receipt=C.strict_json((out/'receipt.json').read_bytes());assert receipt['status']==('complete' if fault is None else 'incomplete')
    assert all(s.calls==0 for s in active) if mode=='token-preflight' else all(s.calls==(1 if fault=='worker' else 204) for s in active)
    if fault!='cleanup':assert not list(host.iterdir())
    if fault is None:
        result=K.check_carrier(out/'evidence.zip',source,receipt['archive_sha256'],C.digest(raw),r['source_commit'])
        assert result['complete'] is True and result['native_origin_reacquired'] is False
    else:assert (out/'failure.json').is_file()


@pytest.mark.parametrize('fault',['late_exit','missing_end','backwards_end','hour24'])
def test_terminal_clock_evidence_cannot_be_missing_or_late(fault):
    source,data,r=evidence()
    def change(x):
        if fault=='late_exit':x['worker_exit_observed_ns']=x['worker_deadline_ns']+1
        elif fault=='missing_end':x['ended_at']=None
        elif fault=='backwards_end':x['ended_at']='2026-10-23T23:59:00+00:00'
        else:x['ended_at']='2026-10-24T24:00:00+00:00'
    mutate(data,'terminal.json',change)
    with pytest.raises(ValueError):K.validate_complete(source,data)
