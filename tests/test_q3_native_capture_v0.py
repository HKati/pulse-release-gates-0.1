"""Explicitly synthetic Q3 carrier/native-boundary regressions, never real capture.

Kernel observations and installed payload inventories here are fabricated TEST
DOUBLES. Passing these tests does not assert native qualification or inference.
"""
import ast
import base64
import copy
import errno
from email.message import Message
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


def synthetic_transport_source(source,kind='github-repository-parts-v0'):
    """Bind an explicit TEST descriptor into fabricated source bytes, not ROOT.

    Legacy route fixtures get a made-up commit/path only in this memory copy.
    Release fixtures retain the sealed public identity but fabricate every
    observation; none of these carriers asserts actual provider retrieval.
    """
    source=dict(source)
    configured={'kind':kind,'repository':C.REPOSITORY,
        'commit':'f'*40 if kind=='github-repository-parts-v0' else None,
        'prefix':'synthetic-q3-runtime-parts' if kind=='github-repository-parts-v0' else None}
    if kind=='github-release-assets-v0':configured=copy.deepcopy(A.RUNTIME_TRANSPORT)
    text=source[A.SELF].decode('utf-8');lines=text.splitlines(keepends=True)
    assignments=[node for node in ast.parse(text).body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='RUNTIME_TRANSPORT' for target in node.targets)]
    assert len(assignments)==1
    node=assignments[0]
    source[A.SELF]=(''.join(lines[:node.lineno-1])+'RUNTIME_TRANSPORT = '+repr(configured)+'\n'+
                   ''.join(lines[node.end_lineno:])).encode('utf-8')
    return source,configured


def synthetic_transport_receipt(source,r,configured):
    """Fabricated transport observations, never an actual provider download."""
    parts=[]
    if configured['kind']=='github-repository-parts-v0':
        parts=[{**copy.deepcopy(row),'path':configured['prefix']+'/'+row['filename']}
               for row in A.RUNTIME_PARTS]
    value={'record_type':'q3_runtime_transport_v0','transport':dict(configured),
        'origin':copy.deepcopy(A.RUNTIME_ORIGIN),
        'split_manifest_sha256':A.RUNTIME_SPLIT_MANIFEST_SHA256 if parts else None,
        'parts':parts,'archive_size_bytes':K.ARCHIVE_SIZE,'archive_sha256':K.ARCHIVE_SHA,
        'binding':{'request_sha256':C.digest(C.encode(r)),'source_commit':r['source_commit'],
                   'run_id':'12345','run_attempt':1,'controller_sha256':C.digest(source[A.SELF])},
        'claims':dict(C.CLAIMS)}
    if configured['kind']=='github-release-assets-v0':
        assets={row['filename']:row for row in A.RUNTIME_RELEASE_ASSETS}
        endpoint=lambda row:'https://api.github.com/repos/'+configured['repository']+'/releases/assets/'+str(row['asset_id'])
        metadata=synthetic_release_metadata()
        manifest=assets['Q3_RUNTIME_PARTS.json']
        value.update(record_type='q3_runtime_transport_v1',split_manifest_sha256=A.RUNTIME_SPLIT_MANIFEST_SHA256,
            metadata_checks={'before':metadata,'after':copy.deepcopy(metadata)},
            manifest_asset={**manifest,'endpoint':endpoint(manifest)},
            parts=[{**copy.deepcopy(row),'asset_id':assets[row['filename']]['asset_id'],
                    'endpoint':endpoint(assets[row['filename']])} for row in A.RUNTIME_PARTS])
    return value


def synthetic_release_metadata():
    """Explicit test observations derived from the published documentation record."""
    binding=json.loads((ROOT/'docs/compute/q3_runtime_release_binding_v0/RELEASE_BINDING.json').read_bytes())
    r=binding['release']
    return {'repository':{'id':r['repository_id'],'full_name':r['repository'],'private':False},
            'release':{'id':r['release_id'],'tag_name':r['tag'],'draft':False,'immutable':True},
            'tag':{'ref':'refs/tags/'+r['tag'],'object_type':'commit','commit':r['tag_target_commit']},
            'assets':[{'asset_id':a['asset_id'],'filename':a['name'],'size_bytes':a['size_bytes'],
                       'sha256':a['sha256'],'state':'uploaded'} for a in sorted(binding['assets'],key=lambda a:a['name'])]}


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


def evidence(mode='token-preflight',transport_kind='github-repository-parts-v0'):
    """Synthetic test-only full carrier. There is no production CLI for this."""
    source={name:(ROOT/name).read_bytes() for name in P['source_files']}
    source,transport=synthetic_transport_source(source,transport_kind)
    data={'source/'+n:b for n,b in source.items()};data.update(installation_data(source))
    r=request(mode);mapping=W.tokenize_frame(Tokenizer(),FRAME,P)
    if mode=='capture':r['approved_token_map_sha256']=C.digest(C.encode(mapping))
    data['request.json']=C.encode(r)
    data['runtime-transport.json']=C.encode(synthetic_transport_receipt(source,r,transport))
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
        'installation_sha256':C.digest(data['installation.json']),
        'runtime_transport_sha256':C.digest(data['runtime-transport.json']),
        'started_at':'2026-10-24T00:00:00+00:00','clock_relation':'not_verified'}
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
    ('capture','worker'),('token-preflight','cleanup'),('token-preflight','source'),
    ('token-preflight','transport'),('token-preflight','archive'),
    ('capture','token_limit'),('capture','token_limit_cleanup')])
@pytest.mark.parametrize('kind',['github-repository-parts-v0','github-release-assets-v0'])
def test_actual_controller_to_publication_with_explicit_native_doubles(tmp_path,monkeypatch,mode,fault,kind):
    """Real controller/files/carrier; synthetic host/install/process/token phases.

    This checks orchestration, error retention and final independent validation.
    It is explicitly not a native observation or actual model/tokenizer call.
    """
    source,fixture,r=evidence(mode,kind);raw=C.encode(r);out=tmp_path/'out';out.mkdir()
    host=tmp_path/'host';host.mkdir();loaded={};actual_path=Path;active=[];acquisition_events=[]
    monkeypatch.setattr(A,'Path',lambda x:host if x=='/var/lib' else actual_path(x))
    monkeypatch.setattr(A,'control_plane',lambda *a:C.strict_json(fixture['control-plane.json']))
    monkeypatch.setattr(A,'output_destination',lambda *a:(out,os.getuid(),os.getgid()))
    # Exercise the actual execute -> parts dispatcher -> archive-check route.
    # Only the large byte stream is a TEST DOUBLE; its synthetic bytes never
    # claim to be the real runtime or bypass a production entrypoint.
    transport=C.strict_json(fixture['runtime-transport.json'])['transport']
    monkeypatch.setattr(A,'RUNTIME_TRANSPORT',transport)
    def assembled(contract,parts,identity,target,end,open_part,*,after_verify=None):
        acquisition_events.append('parts')
        assert parts==A.RUNTIME_PARTS and identity==A._runtime_archive_identity()
        if fault=='transport':raise C.ContractError('SYNTHETIC_TRANSPORT_FAILURE')
        target.write_bytes(b'explicit synthetic archive double')
        if after_verify is not None:after_verify()
        return {'size_bytes':K.ARCHIVE_SIZE,'sha256':K.ARCHIVE_SHA,
                'parts':copy.deepcopy(list(A.RUNTIME_PARTS))}
    monkeypatch.setattr(A,'_assemble_runtime_parts',assembled)
    monkeypatch.setattr(A,'download_runtime_artifact',lambda *a,**k:pytest.fail('silent legacy fallback'))
    monkeypatch.setattr(A,'_open_runtime_part',lambda *a,**k:pytest.fail('network from a synthetic carrier'))
    def metadata(*args):
        acquisition_events.append('release-metadata');return synthetic_release_metadata()
    def release_asset(contract,source,asset,end):
        assert asset['filename']=='Q3_RUNTIME_PARTS.json'
        acquisition_events.append('manifest')
        return ShortPartStream((ROOT/'tests/fixtures/q3_runtime_release_v0/Q3_RUNTIME_PARTS.json').read_bytes())
    monkeypatch.setattr(A,'_runtime_release_metadata',metadata)
    monkeypatch.setattr(A,'_open_runtime_release_asset',release_asset)
    monkeypatch.setattr(A.shutil,'disk_usage',lambda *a:types.SimpleNamespace(free=10*1024**3))
    original_load=A.load_sealed
    def loader(name,path):
        mod=original_load(name,path)
        if name=='q3_verified_independent_checker':
            def archive(archive,destination,sources):
                acquisition_events.append('archive')
                assert archive.read_bytes()==b'explicit synthetic archive double'
                if fault=='archive':raise C.ContractError('SYNTHETIC_ARCHIVE_FAILURE')
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
                            capped=fault in ('token_limit','token_limit_cleanup')
                            self.queue.append(C.encode({**self.slotready,'record_type':'q3_response_v0',
                              'new_token_ids':[4]*256 if capped else [4,2],'text':text,
                              'text_utf8_base64':base64.b64encode(text.encode()).decode(),
                              'stop_reason':'token_limit' if capped else 'eos'}))
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
                    self.cleanup_details={'record_type':'q3_native_cleanup_diagnostics_v1',
                        'services':[{'synthetic_cleanup_observation':True}],'timers':[]}
                    failed=fault in ('cleanup','token_limit_cleanup')
                    return {'cleanup_complete':not failed,'errors':['synthetic_cleanup'] if failed else [],
                            'services':[s.cleanup for s in self.services],'timers':self.timers}
            mod.Lifecycle=Life
            def phase(life,prefix,stage,command,work,python,logs,deadline,ev):
                if stage=='installer':acquisition_events.append('installer')
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
    expected_events=['parts']
    if kind=='github-release-assets-v0':expected_events=['release-metadata','manifest']+expected_events
    if fault!='transport':
        if kind=='github-release-assets-v0':expected_events.append('release-metadata')
        expected_events.append('archive')
        if fault!='archive':expected_events.append('installer')
    assert acquisition_events==expected_events
    one_call=fault in ('worker','token_limit','token_limit_cleanup')
    assert all(s.calls==0 for s in active) if mode=='token-preflight' else all(s.calls==(1 if one_call else 204) for s in active)
    if fault not in ('cleanup','token_limit_cleanup'):assert not list(host.iterdir())
    with zipfile.ZipFile(out/'evidence.zip') as archive:
        assert ('lifecycle-diagnostics.json' in archive.namelist()) == (fault is not None)
        if fault in ('token_limit','token_limit_cleanup'):
            result=C.strict_json(archive.read('result.json'))
            terminal=C.strict_json(archive.read('terminal.json'))
            lifecycle=C.strict_json(archive.read('lifecycle.json'))
            diagnostics=C.strict_json(archive.read('lifecycle-diagnostics.json'))
            assert result['error_code']==terminal['error_code']=='TOKEN_LIMIT_TERMINATION'
            assert terminal['attempted_calls']==1
            assert terminal['occurrences'][0]['status']=='length_terminated'
            assert all(row['status']=='not_started' for row in terminal['occurrences'][1:])
            assert lifecycle['cleanup_complete']==lifecycle['private_tree_removed']==(fault=='token_limit')
            assert diagnostics['record_type']=='q3_native_cleanup_diagnostics_v1'
            assert diagnostics['services']==[{'synthetic_cleanup_observation':True}]
            checked=K.check_carrier(out/'evidence.zip',source,receipt['archive_sha256'],C.digest(raw),r['source_commit'])
            assert checked['failure_inventory_verified'] is True and checked['complete'] is False
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


def tiny_transport_parts():
    """Twenty small byte ranges for the private assembler's offline seam."""
    filename='synthetic-runtime.zip'
    blocks=[b'\0synthetic part '+str(i).encode('ascii')+b'!'*i for i in range(1,21)]
    parts=[];offset=0
    for i,block in enumerate(blocks,1):
        parts.append({'index':i,'filename':filename+f'.{i:03d}','size_bytes':len(block),
            'sha256':C.digest(block),'offset_start':offset,'offset_end_exclusive':offset+len(block)})
        offset+=len(block)
    identity={'filename':filename,'size_bytes':offset,'sha256':C.digest(b''.join(blocks))}
    return parts,identity,blocks


class ShortPartStream(io.BytesIO):
    """A short-reading fake response; no sockets or runtime bytes are involved."""
    status=200
    def __init__(self,raw,content_encoding=None):
        super().__init__(raw);self.read_sizes=[];self.headers=Message()
        if content_encoding is not None:
            values=content_encoding if isinstance(content_encoding,list) else [content_encoding]
            for value in values:self.headers['Content-Encoding']=value
    def getheader(self,name,default=None):return self.headers.get(name,default)
    def read(self,size=-1):
        raise AssertionError('buffer-filling read must not hide transport deadline checks')
    def read1(self,size):
        assert 0<size<=65536
        self.read_sizes.append(size)
        return super().read(min(size,3))


def test_private_part_assembler_checks_short_reads_and_original_order(tmp_path):
    parts,identity,blocks=tiny_transport_parts();opened=[];streams=[]
    def open_part(row):
        opened.append(row['index']);stream=ShortPartStream(blocks[row['index']-1]);streams.append(stream);return stream
    path=tmp_path/'runtime.zip'
    observed=A._assemble_runtime_parts(C,parts,identity,path,time.monotonic()+30,open_part)
    assert path.read_bytes()==b''.join(blocks)
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    assert observed=={'size_bytes':identity['size_bytes'],'sha256':identity['sha256'],'parts':parts}
    assert opened==list(range(1,21)) and all(stream.closed for stream in streams)
    assert all(len(stream.read_sizes)>1 for stream in streams)


@pytest.mark.parametrize('fault',['missing','duplicate','reordered','name','path','bool_index','bool_size',
    'offset_gap','offset_overlap','end','extra','digest','total'])
def test_part_inventory_rejected_before_open_or_output(tmp_path,fault):
    parts,identity,blocks=tiny_transport_parts()
    if fault=='missing':parts.pop()
    elif fault=='duplicate':parts[1]=copy.deepcopy(parts[0])
    elif fault=='reordered':parts[0],parts[1]=parts[1],parts[0]
    elif fault=='name':parts[0]['filename']='other.zip.001'
    elif fault=='path':parts[0]['filename']='../'+parts[0]['filename']
    elif fault=='bool_index':parts[0]['index']=True
    elif fault=='bool_size':parts[0]['size_bytes']=True
    elif fault=='offset_gap':parts[1]['offset_start']+=1
    elif fault=='offset_overlap':parts[1]['offset_start']-=1
    elif fault=='end':parts[0]['offset_end_exclusive']+=1
    elif fault=='extra':parts[0]['url']='https://unreviewed.invalid/part'
    elif fault=='digest':parts[0]['sha256']='invalid'
    elif fault=='total':identity['size_bytes']+=1
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError):
        A._assemble_runtime_parts(C,parts,identity,path,time.monotonic()+30,
            lambda row:pytest.fail('invalid manifest reached reader'))
    assert not path.exists()


@pytest.mark.parametrize('fault',['substitution','truncated','oversize','swapped','whole_digest','io_error','interrupt'])
def test_part_byte_failure_removes_partial_output_without_retry(tmp_path,fault):
    parts,identity,blocks=tiny_transport_parts();opened=[];streams=[]
    if fault=='substitution':blocks[1]=b'?'*len(blocks[1])
    elif fault=='truncated':blocks[1]=blocks[1][:-1]
    elif fault=='oversize':blocks[1]+=b'!'
    elif fault=='swapped':blocks[0],blocks[1]=blocks[1],blocks[0]
    elif fault=='whole_digest':identity['sha256']='0'*64
    def open_part(row):
        opened.append(row['index'])
        if row['index']==2 and fault=='io_error':raise OSError('synthetic transport I/O failure')
        stream=ShortPartStream(blocks[row['index']-1]);streams.append(stream)
        if row['index']==2 and fault=='interrupt':
            def interrupted(size):raise KeyboardInterrupt()
            stream.read1=interrupted
        return stream
    path=tmp_path/'runtime.zip'
    expected=KeyboardInterrupt if fault=='interrupt' else OSError if fault=='io_error' else ValueError
    with pytest.raises(expected):A._assemble_runtime_parts(C,parts,identity,path,time.monotonic()+30,open_part)
    assert not path.exists()
    assert len(opened)==len(set(opened)) and opened==list(range(1,len(opened)+1))
    assert all(stream.closed for stream in streams)


def test_part_deadline_is_checked_after_read_and_discards_partial_output(tmp_path,monkeypatch):
    parts,identity,blocks=tiny_transport_parts();clock=[1.0];opened=[]
    monkeypatch.setattr(A.time,'monotonic',lambda:clock[0])
    def open_part(row):
        opened.append(row['index']);stream=ShortPartStream(blocks[row['index']-1]);read=stream.read1
        def expires(size):clock[0]=31.0;return read(size)
        stream.read1=expires;return stream
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError,match='DEADLINE'):A._assemble_runtime_parts(C,parts,identity,path,30.0,open_part)
    assert opened==[1] and not path.exists()


def test_slow_trickle_uses_single_reads_and_rechecks_the_overall_deadline(tmp_path,monkeypatch):
    parts,identity,blocks=tiny_transport_parts();clock=[1.0];opened=[];streams=[]
    monkeypatch.setattr(A.time,'monotonic',lambda:clock[0])
    class Trickle(ShortPartStream):
        def read1(self,size):
            assert 0<size<=65536
            self.read_sizes.append(size);clock[0]+=4.0
            return io.BytesIO.read(self,1)
    def open_part(row):
        opened.append(row['index']);stream=Trickle(blocks[row['index']-1]);streams.append(stream);return stream
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError,match='DEADLINE'):
        A._assemble_runtime_parts(C,parts,identity,path,10.0,open_part)
    # Bytes remain available and each read returned data. The overall deadline,
    # rather than EOF or a socket-inactivity timeout, stops the slow transfer.
    assert opened==[1] and len(streams[0].read_sizes)==3
    assert streams[0].closed and not path.exists()


def test_reader_without_single_read_api_cannot_fall_back_to_buffer_filling_read(tmp_path):
    parts,identity,blocks=tiny_transport_parts();opened=[]
    class Unsupported:
        def __init__(self):self.closed=False
        def __enter__(self):return self
        def __exit__(self,*args):self.closed=True
        def read(self,size):pytest.fail('unsafe read fallback')
    stream=Unsupported()
    def open_part(row):opened.append(row['index']);return stream
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError,match='STREAM_READER'):
        A._assemble_runtime_parts(C,parts,identity,path,time.monotonic()+30,open_part)
    assert opened==[1] and stream.closed and not path.exists()


@pytest.mark.parametrize('kind',['file','symlink'])
def test_part_assembler_never_overwrites_or_removes_preexisting_target(tmp_path,kind):
    parts,identity,blocks=tiny_transport_parts();target=tmp_path/'runtime.zip';original=tmp_path/'original'
    original.write_bytes(b'existing owner bytes')
    if kind=='file':target.write_bytes(b'existing target bytes')
    else:target.symlink_to(original)
    with pytest.raises((FileExistsError,ValueError)):
        A._assemble_runtime_parts(C,parts,identity,target,time.monotonic()+30,
                                 lambda row:pytest.fail('preexisting target reached reader'))
    assert original.read_bytes()==b'existing owner bytes'
    assert target.read_bytes()==(b'existing target bytes' if kind=='file' else b'existing owner bytes')
    assert target.is_symlink()==(kind=='symlink')


def configured_transport():
    return {'kind':'github-repository-parts-v0','repository':C.REPOSITORY,
            'commit':'f'*40,'prefix':'synthetic-q3-runtime-parts'}


def test_inactive_repository_transport_still_cannot_acquire(tmp_path,monkeypatch):
    monkeypatch.setattr(A,'RUNTIME_TRANSPORT',{**configured_transport(),'commit':None,'prefix':None})
    monkeypatch.setattr(A,'api_bytes',lambda *a,**k:pytest.fail('unconfigured source reached API'))
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:pytest.fail('unconfigured source reached HTTP'))
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError,match='UNCONFIGURED'):A.download_runtime(C,P,'test-only-token',path,time.monotonic()+30)
    assert not path.exists()


@pytest.mark.parametrize('fault',['branch','tag','short_commit','uppercase_commit','zero_commit','bool_commit',
    'missing_prefix','absolute_prefix','parent_prefix','encoded_prefix','foreign_repository','unknown_kind','extra_field'])
def test_runtime_source_selection_rejects_unbound_or_unsafe_inputs(tmp_path,monkeypatch,fault):
    source=configured_transport()
    if fault=='branch':source['commit']='main'
    elif fault=='tag':source['commit']='refs/tags/v1'
    elif fault=='short_commit':source['commit']='f'*39
    elif fault=='uppercase_commit':source['commit']='F'*40
    elif fault=='zero_commit':source['commit']='0'*40
    elif fault=='bool_commit':source['commit']=True
    elif fault=='missing_prefix':source['prefix']=None
    elif fault=='absolute_prefix':source['prefix']='/outside'
    elif fault=='parent_prefix':source['prefix']='parts/../outside'
    elif fault=='encoded_prefix':source['prefix']='parts%2f..'
    elif fault=='foreign_repository':source['repository']='someone/another-repository'
    elif fault=='unknown_kind':source['kind']='automatic-fallback'
    elif fault=='extra_field':source['runtime_url']='https://unreviewed.invalid/runtime.zip'
    monkeypatch.setattr(A,'RUNTIME_TRANSPORT',source)
    monkeypatch.setattr(A,'api_bytes',lambda *a,**k:pytest.fail('rejected source reached API'))
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:pytest.fail('rejected source reached HTTP'))
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError):A.download_runtime(C,P,'test-only-token',path,time.monotonic()+30)
    assert not path.exists()


@pytest.mark.parametrize('fault',['part_bytes','part_order','part_count','origin','profile_origin','manifest_pin'])
def test_production_transport_pin_cannot_be_rebound(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(A,'RUNTIME_TRANSPORT',configured_transport());profile=copy.deepcopy(P)
    if fault in ('part_bytes','part_order','part_count'):
        parts=copy.deepcopy(list(A.RUNTIME_PARTS))
        if fault=='part_bytes':parts[0]['sha256']='0'*64
        elif fault=='part_order':parts[0],parts[1]=parts[1],parts[0]
        else:parts.pop()
        monkeypatch.setattr(A,'RUNTIME_PARTS',tuple(parts))
    elif fault=='origin':
        origin=copy.deepcopy(A.RUNTIME_ORIGIN);origin['original_artifact_id']+=1
        monkeypatch.setattr(A,'RUNTIME_ORIGIN',origin)
    elif fault=='profile_origin':profile['runtime_archive']['artifact_id']+=1
    elif fault=='manifest_pin':monkeypatch.setattr(A,'RUNTIME_SPLIT_MANIFEST_SHA256','0'*64)
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:pytest.fail('bad pin reached HTTP'))
    path=tmp_path/'runtime.zip'
    with pytest.raises(ValueError):A.download_runtime(C,profile,'test-only-token',path,time.monotonic()+30)
    assert not path.exists()


def test_original_runtime_identity_and_split_are_not_replaced_by_transport():
    assert A.RUNTIME_ORIGIN=={'filename':'q2-runtime-preparation-37148637546-1.zip','size_bytes':508460811,
        'sha256':'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9',
        'original_run_id':'37148637546','original_run_attempt':1,'original_artifact_id':11282419957,
        'original_source_commit':'77fc5d51896568db50a2a87f650711a65db8fe8c'}
    assert C.digest(C.encode(A.RUNTIME_PARTS))=='0f7af070258c3bb6206c240e00cfe5464169666fbaf9fa9540b68c7ee384d341'
    assert [row['size_bytes'] for row in A.RUNTIME_PARTS]==[25423041]*19+[25423032]
    assert P['runtime_archive']['artifact_id']==11282419957


def test_raw_contents_reader_uses_exact_commit_and_raw_media_type(monkeypatch):
    source=configured_transport();part=A.RUNTIME_PARTS[0];calls=[];response=ShortPartStream(b'synthetic')
    class Opener:
        def open(self,req,timeout):calls.append((req,timeout));return response
    def opener(*handlers):
        assert len(handlers)==1 and isinstance(handlers[0],A.NoRedirect)
        return Opener()
    monkeypatch.setattr(A.urllib.request,'build_opener',opener)
    result=A._open_runtime_part(C,'synthetic-token',source,part,time.monotonic()+5)
    assert result is response and len(calls)==1
    req,timeout=calls[0];headers={k.lower():v for k,v in req.header_items()}
    assert req.full_url==('https://api.github.com/repos/'+C.REPOSITORY+'/contents/'+source['prefix']+'/'+
                          part['filename']+'?ref='+source['commit'])
    assert headers['accept']=='application/vnd.github.raw+json'
    assert headers['authorization']=='Bearer synthetic-token'
    assert headers['accept-encoding']=='identity' and 0<timeout<=5
    response.close()


@pytest.mark.parametrize('encoding',[None,'identity','gzip','br','identity,gzip',['identity','identity']])
def test_raw_contents_requires_unambiguous_identity_encoding(monkeypatch,encoding):
    source=configured_transport();part=A.RUNTIME_PARTS[0]
    response=ShortPartStream(b'synthetic',content_encoding=encoding);calls=[]
    class Opener:
        def open(self,req,timeout):calls.append(req);return response
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *handlers:Opener())
    if encoding in (None,'identity'):
        assert A._open_runtime_part(C,'synthetic-token',source,part,time.monotonic()+5) is response
        response.close()
    else:
        with pytest.raises(ValueError,match='CONTENT_ENCODING'):
            A._open_runtime_part(C,'synthetic-token',source,part,time.monotonic()+5)
        assert response.closed
    assert len(calls)==1 and not response.read_sizes


@pytest.mark.parametrize('fault',[None,'foreign_host','mutable_ref','query','second_redirect','http_404'])
def test_raw_redirect_is_single_exact_source_and_never_forwards_token(monkeypatch,fault):
    source=configured_transport();part=A.RUNTIME_PARTS[0];calls=[];response=ShortPartStream(b'synthetic')
    raw_url='https://raw.githubusercontent.com/'+C.REPOSITORY+'/'+source['commit']+'/'+source['prefix']+'/'+part['filename']
    target=raw_url
    if fault=='foreign_host':target=raw_url.replace('raw.githubusercontent.com','unreviewed.invalid')
    elif fault=='mutable_ref':target=raw_url.replace(source['commit'],'main')
    elif fault=='query':target+='?credential=not-allowed'
    class Opener:
        def open(self,req,timeout):
            calls.append(req)
            if len(calls)==1:
                raise A.urllib.error.HTTPError(req.full_url,404 if fault=='http_404' else 302,'synthetic',{'Location':target},io.BytesIO())
            if fault=='second_redirect':raise A.urllib.error.HTTPError(req.full_url,302,'synthetic',{'Location':raw_url},io.BytesIO())
            return response
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *handlers:Opener())
    if fault is None:
        assert A._open_runtime_part(C,'synthetic-token',source,part,time.monotonic()+5) is response
        assert len(calls)==2 and calls[1].full_url==raw_url
        assert 'authorization' not in {k.lower() for k,v in calls[1].header_items()}
        response.close()
    else:
        with pytest.raises(ValueError):A._open_runtime_part(C,'synthetic-token',source,part,time.monotonic()+5)
        assert len(calls)==(2 if fault=='second_redirect' else 1)
        if len(calls)==2:assert 'authorization' not in {k.lower() for k,v in calls[1].header_items()}


@pytest.mark.parametrize('kind',['github-repository-parts-v0','original-actions-artifact-v0','github-release-assets-v0'])
def test_complete_transport_record_is_source_selected(kind):
    source,data,r=evidence(transport_kind=kind)
    assert K.validate_complete(source,data)['complete'] is True
    receipt=C.strict_json(data['runtime-transport.json'])
    assert receipt['transport']['kind']==kind
    assert receipt['origin']['original_artifact_id']==11282419957
    assert len(receipt['parts'])==(0 if kind=='original-actions-artifact-v0' else 20)


@pytest.mark.parametrize('fault',['missing','extra','kind','commit','prefix','request','source_commit','run_id',
    'attempt_bool','controller','origin','archive_size','archive_hash','manifest','part_missing','part_duplicate',
    'part_order','part_size','part_hash','part_path','authority','stale_digest'])
def test_transport_receipt_coherent_rehash_cannot_hide_wrong_source_or_bytes(fault):
    source,data,r=evidence();value=C.strict_json(data['runtime-transport.json'])
    pre=C.strict_json(data['prelaunch.json'])
    if fault=='missing':data.pop('runtime-transport.json')
    else:
        if fault=='extra':value['ready']=True
        elif fault=='kind':value['transport']['kind']='original-actions-artifact-v0'
        elif fault=='commit':value['transport']['commit']='e'*40
        elif fault=='prefix':
            value['transport']['prefix']='other-parts'
            for row in value['parts']:row['path']='other-parts/'+row['filename']
        elif fault=='request':value['binding']['request_sha256']='0'*64
        elif fault=='source_commit':value['binding']['source_commit']='b'*40
        elif fault=='run_id':value['binding']['run_id']='99999'
        elif fault=='attempt_bool':value['binding']['run_attempt']=True
        elif fault=='controller':value['binding']['controller_sha256']='0'*64
        elif fault=='origin':value['origin']['original_artifact_id']+=1
        elif fault=='archive_size':value['archive_size_bytes']-=1
        elif fault=='archive_hash':value['archive_sha256']='0'*64
        elif fault=='manifest':value['split_manifest_sha256']='0'*64
        elif fault=='part_missing':value['parts'].pop()
        elif fault=='part_duplicate':value['parts'][1]=copy.deepcopy(value['parts'][0])
        elif fault=='part_order':value['parts'][0],value['parts'][1]=value['parts'][1],value['parts'][0]
        elif fault=='part_size':value['parts'][0]['size_bytes']-=1
        elif fault=='part_hash':value['parts'][0]['sha256']='0'*64
        elif fault=='part_path':value['parts'][0]['path']='other/'+value['parts'][0]['filename']
        elif fault=='authority':value['claims']['authority_effect']='allow'
        elif fault=='stale_digest':value['binding']['run_id']='99999'
        data['runtime-transport.json']=C.encode(value)
        if fault!='stale_digest':pre['runtime_transport_sha256']=C.digest(data['runtime-transport.json'])
    with pytest.raises(ValueError,match='runtime_transport'):
        K.validate_runtime_transport(source,data,r,pre)


def test_release_source_cannot_be_promoted_by_fabricated_repository_receipt():
    source,data,r=evidence();source[A.SELF]=(ROOT/A.SELF).read_bytes()
    value=C.strict_json(data['runtime-transport.json'])
    value['binding']['controller_sha256']=C.digest(source[A.SELF])
    data['runtime-transport.json']=C.encode(value)
    pre=C.strict_json(data['prelaunch.json']);pre['runtime_transport_sha256']=C.digest(data['runtime-transport.json'])
    pre['source_files'][A.SELF]=C.digest(source[A.SELF])
    with pytest.raises(ValueError,match='runtime_transport'):
        K.validate_runtime_transport(source,data,r,pre)


def release_provider_fixture():
    """Synthetic API bodies; no provider request is made by any test below."""
    m=synthetic_release_metadata();s=A.RUNTIME_TRANSPORT
    base='https://api.github.com/repos/'+s['repository']
    rows=[{'id':r['asset_id'],'name':r['filename'],'size':r['size_bytes'],
           'digest':'sha256:'+r['sha256'],'state':r['state'],
           'url':base+'/releases/assets/'+str(r['asset_id']),
           'browser_download_url':'https://github.com/'+s['repository']+'/releases/download/'+s['tag']+'/'+r['filename']}
          for r in m['assets']]
    return {'':m['repository'],
            '/releases/'+str(s['release_id']):{**m['release'],'url':base+'/releases/'+str(s['release_id']),
                                              'assets':list(reversed(rows))},
            '/git/ref/tags/'+s['tag']:{'ref':m['tag']['ref'],
                'object':{'type':m['tag']['object_type'],'sha':m['tag']['commit']}}}


def test_shipped_release_plan_agrees_with_published_binding_and_independent_pins():
    source=A.runtime_transport_plan(C,P)
    assert source=={'kind':'github-release-assets-v0','repository':'HKati/pulsemech-q3-runtime-inputs',
        'repository_id':1450778044,'release_id':438650666,'tag':'q2-runtime-37148637546-1-v1',
        'tag_commit':'d4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5'}
    assert C.digest(C.encode(source))==K.RUNTIME_RELEASE_SOURCE_SHA256
    assert C.digest(C.encode(A.RUNTIME_RELEASE_ASSETS))==K.RUNTIME_RELEASE_ASSETS_SHA256
    actual=[{**r,'state':'uploaded'} for r in A.RUNTIME_RELEASE_ASSETS]
    assert actual==synthetic_release_metadata()['assets']
    assert sum(r['size_bytes'] for r in actual)==821365369
    assert len(A.SOURCE_FILES)==21 and set(A.SOURCE_FILES)==set(P['source_files'])


@pytest.mark.parametrize('field,value',[('repository','other/repo'),('repository_id',True),
    ('release_id',438650667),('tag','latest'),('tag_commit','e'*40),('url','https://unreviewed.invalid')])
def test_release_source_cannot_be_reselected_by_descriptor(tmp_path,monkeypatch,field,value):
    source=copy.deepcopy(A.RUNTIME_TRANSPORT);source[field]=value
    monkeypatch.setattr(A,'RUNTIME_TRANSPORT',source)
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:pytest.fail('bad source reached HTTP'))
    with pytest.raises(ValueError,match='RUNTIME_RELEASE_SOURCE'):
        A.download_runtime(C,P,'never-forward-this-token',tmp_path/'runtime.zip',time.monotonic()+30)


@pytest.mark.parametrize('fault',['id','size','hash','name','order','missing','extra'])
def test_release_inventory_source_pin_rejects_mutation(monkeypatch,fault):
    rows=copy.deepcopy(list(A.RUNTIME_RELEASE_ASSETS))
    if fault=='id':rows[0]['asset_id']+=1
    elif fault=='size':rows[0]['size_bytes']+=1
    elif fault=='hash':rows[0]['sha256']='0'*64
    elif fault=='name':rows[0]['filename']='another.json'
    elif fault=='order':rows.reverse()
    elif fault=='missing':rows.pop()
    else:rows[0]['url']='https://unreviewed.invalid'
    monkeypatch.setattr(A,'RUNTIME_RELEASE_ASSETS',tuple(rows))
    with pytest.raises(ValueError,match='RUNTIME_RELEASE_ASSETS_PIN'):A.runtime_transport_plan(C,P)


def test_release_metadata_reads_only_fixed_public_routes(monkeypatch):
    source=A.RUNTIME_TRANSPORT;bodies=release_provider_fixture();calls=[];responses=[]
    monkeypatch.setenv('HTTPS_PROXY','http://unreviewed.invalid:1234')
    monkeypatch.setenv('GITHUB_TOKEN','must-not-leave-this-process')
    class Opener:
        def open(self,req,timeout):
            calls.append(req);assert 0<timeout<=15
            suffix=req.full_url.removeprefix('https://api.github.com/repos/'+source['repository'])
            raw=C.encode(bodies[suffix]);r=ShortPartStream(raw)
            r.headers['Content-Type']='application/json; charset=utf-8'
            r.headers['Content-Length']=str(len(raw));responses.append(r);return r
    def opener(*handlers):
        assert len(handlers)==3
        assert isinstance(handlers[0],A.urllib.request.ProxyHandler) and handlers[0].proxies=={}
        assert isinstance(handlers[1],A.urllib.request.HTTPSHandler)
        assert handlers[1]._context.verify_mode==A.ssl.CERT_REQUIRED
        assert handlers[1]._context.check_hostname is True
        assert isinstance(handlers[2],A.NoRedirect)
        return Opener()
    monkeypatch.setattr(A.urllib.request,'build_opener',opener)
    assert A._runtime_release_metadata(C,source,time.monotonic()+30)==synthetic_release_metadata()
    assert [r.full_url for r in calls]==['https://api.github.com/repos/'+source['repository']+p for p in bodies]
    for req in calls:
        h={k.lower():v for k,v in req.header_items()}
        assert 'authorization' not in h and 'cookie' not in h
        assert h['accept']=='application/vnd.github+json' and h['accept-encoding']=='identity'
    assert all(r.closed and r.read_sizes for r in responses)


@pytest.mark.parametrize('fault',['repo_id','repo_name','private','release_id','release_bool','tag_name','draft',
    'mutable','tag_ref','tag_type','tag_commit','missing','duplicate','extra','asset_id','asset_bool','name','size',
    'digest','state','asset_url','download_url','release_url'])
def test_release_metadata_rejects_wrong_or_incomplete_identity(monkeypatch,fault):
    bodies=release_provider_fixture();source=A.RUNTIME_TRANSPORT
    repo=bodies[''];release=bodies['/releases/'+str(source['release_id'])]
    tag=bodies['/git/ref/tags/'+source['tag']];row=release['assets'][0]
    if fault=='repo_id':repo['id']+=1
    elif fault=='repo_name':repo['full_name']='other/repo'
    elif fault=='private':repo['private']=True
    elif fault=='release_id':release['id']+=1
    elif fault=='release_bool':release['id']=True
    elif fault=='tag_name':release['tag_name']='another-tag'
    elif fault=='draft':release['draft']=True
    elif fault=='mutable':release['immutable']=False
    elif fault=='tag_ref':tag['ref']='refs/heads/main'
    elif fault=='tag_type':tag['object']['type']='tag'
    elif fault=='tag_commit':tag['object']['sha']='e'*40
    elif fault=='missing':release['assets'].pop()
    elif fault=='duplicate':release['assets'][1]=copy.deepcopy(row)
    elif fault=='extra':release['assets'].append(copy.deepcopy(row))
    elif fault=='asset_id':row['id']+=1
    elif fault=='asset_bool':row['id']=True
    elif fault=='name':row['name']='another-file'
    elif fault=='size':row['size']+=1
    elif fault=='digest':row['digest']='sha256:'+'0'*64
    elif fault=='state':row['state']='starter'
    elif fault=='asset_url':row['url']='https://unreviewed.invalid/binary'
    elif fault=='download_url':row['browser_download_url']=row['browser_download_url'].replace(source['tag'],'latest')
    else:release['url']='https://api.github.com/repos/other/repo/releases/'+str(source['release_id'])
    monkeypatch.setattr(A,'_release_api_json',lambda c,s,suffix,end:bodies[suffix])
    with pytest.raises(ValueError,match='RUNTIME_RELEASE_'):
        A._runtime_release_metadata(C,source,time.monotonic()+30)


@pytest.mark.parametrize('fault',['redirect','status','encoding','double_encoding','double_length','length',
    'transfer_length','media','oversize','short','duplicate_json','expired','no_read1'])
def test_release_metadata_reader_rejects_unsafe_http_or_body(monkeypatch,fault):
    body=b'{"id":1}'
    if fault=='oversize':body=b' '*1048577
    elif fault=='duplicate_json':body=b'{"id":1,"id":2}'
    response=ShortPartStream(body);response.headers['Content-Type']='application/json'
    if fault=='status':response.status=206
    elif fault=='encoding':response.headers['Content-Encoding']='gzip'
    elif fault=='double_encoding':
        response.headers['Content-Encoding']='identity';response.headers['Content-Encoding']='identity'
    elif fault=='double_length':
        response.headers['Content-Length']='8';response.headers['Content-Length']='8'
    elif fault=='length':response.headers['Content-Length']='1048577'
    elif fault=='transfer_length':
        response.headers['Content-Length']='8';response.headers['Transfer-Encoding']='chunked'
    elif fault=='media':response.headers.replace_header('Content-Type','text/html')
    elif fault=='short':response.headers['Content-Length']='10'
    elif fault=='no_read1':response.read1=None
    class Opener:
        def open(self,req,timeout):
            if fault=='redirect':
                raise A.urllib.error.HTTPError(req.full_url,302,'synthetic',Message(),io.BytesIO())
            return response
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:Opener())
    end=time.monotonic()+(-1 if fault=='expired' else 30)
    with pytest.raises(ValueError):A._release_api_json(C,A.RUNTIME_TRANSPORT,'',end)
    if fault not in ('redirect','expired'):assert response.closed


@pytest.mark.parametrize('fault',[None,'direct','foreign_host','wrong_repository','wrong_path','userinfo',
    'http','fragment','controls','duplicate_location','second_redirect','wrong_status','wrong_length','gzip'])
def test_release_asset_reader_has_one_credential_free_redirect(monkeypatch,fault):
    source=A.RUNTIME_TRANSPORT;asset=A.RUNTIME_RELEASE_ASSETS[0];calls=[];errors=[]
    url='https://release-assets.githubusercontent.com/github-production-release-asset/1450778044/00000000-1111-2222-3333-444444444444?sig=synthetic'
    if fault=='foreign_host':url=url.replace('release-assets.githubusercontent.com','unreviewed.invalid')
    elif fault=='wrong_repository':url=url.replace('1450778044','1450778045')
    elif fault=='wrong_path':url=url.replace('/github-production-release-asset/','/arbitrary/')
    elif fault=='userinfo':url=url.replace('https://','https://user:password@')
    elif fault=='http':url=url.replace('https:','http:')
    elif fault=='fragment':url+='#other'
    elif fault=='controls':url+='\n'
    response=ShortPartStream(b'synthetic')
    response.headers['Content-Length']=str(asset['size_bytes']+(1 if fault=='wrong_length' else 0))
    if fault=='gzip':response.headers['Content-Encoding']='gzip'
    class Opener:
        def open(self,req,timeout):
            calls.append(req)
            if fault!='direct' and (len(calls)==1 or fault=='second_redirect'):
                h=Message();h['Location']=url
                if fault=='duplicate_location':h['Location']=url
                error=A.urllib.error.HTTPError(req.full_url,307 if fault=='wrong_status' else 302,'synthetic',h,io.BytesIO())
                errors.append(error);raise error
            return response
    monkeypatch.setattr(A.urllib.request,'build_opener',lambda *a,**k:Opener())
    if fault in (None,'direct'):
        assert A._open_runtime_release_asset(C,source,asset,time.monotonic()+30) is response
        assert len(calls)==(1 if fault=='direct' else 2);response.close()
    else:
        with pytest.raises(ValueError):A._open_runtime_release_asset(C,source,asset,time.monotonic()+30)
        assert len(calls)==(2 if fault in ('second_redirect','wrong_length','gzip') else 1)
    assert all(e.closed for e in errors)
    assert calls[0].full_url.endswith('/releases/assets/'+str(asset['asset_id']))
    for req in calls:
        headers={k.lower():v for k,v in req.header_items()}
        assert headers['accept']=='application/octet-stream' and headers['accept-encoding']=='identity'
        assert 'authorization' not in headers and 'cookie' not in headers


@pytest.mark.parametrize('fault',[None,'changed','truncated','extra'])
def test_release_manifest_verifies_real_pinned_fixture_without_network(monkeypatch,fault):
    raw=(ROOT/'tests/fixtures/q3_runtime_release_v0/Q3_RUNTIME_PARTS.json').read_bytes()
    assert len(raw)==7014 and C.digest(raw)==A.RUNTIME_SPLIT_MANIFEST_SHA256
    if fault=='changed':raw=raw.replace(b'508460811',b'508460812',1)
    elif fault=='truncated':raw=raw[:-1]
    elif fault=='extra':raw+=b'\n'
    stream=ShortPartStream(raw)
    monkeypatch.setattr(A,'_open_runtime_release_asset',lambda *args:stream)
    assets=A._runtime_release_assets(C)
    if fault is None:
        record=A._runtime_release_manifest(C,A.RUNTIME_TRANSPORT,assets,time.monotonic()+30)
        assert record['asset_id']==728263266 and record['size_bytes']==7014
        assert record['endpoint'].endswith('/releases/assets/728263266')
    else:
        with pytest.raises(ValueError):A._runtime_release_manifest(C,A.RUNTIME_TRANSPORT,assets,time.monotonic()+30)
    assert stream.closed


@pytest.mark.parametrize('fault',[None,'before','manifest','part','after','after_timeout'])
def test_release_dispatcher_orders_reads_and_cleans_failed_assembly(tmp_path,monkeypatch,fault):
    """Actual private assembler/dispatcher with explicit tiny transport doubles."""
    parts,identity,blocks=tiny_transport_parts();events=[];responses=[]
    assets={p['filename']:{k:p[k] for k in ('filename','size_bytes','sha256')} for p in parts}
    for i,row in enumerate(assets.values(),1):row['asset_id']=i
    monkeypatch.setattr(A,'RUNTIME_PARTS',parts)
    monkeypatch.setattr(A,'_runtime_archive_identity',lambda:identity)
    monkeypatch.setattr(A,'_runtime_release_assets',lambda c:assets)
    def metadata(*args):
        stage='before' if not events else 'after';events.append(stage)
        if fault==stage:raise C.ContractError('SYNTHETIC_METADATA_FAILURE')
        if fault=='after_timeout' and stage=='after':
            monkeypatch.setattr(A.time,'monotonic',lambda:end+1)
        return {'test_only':'fixed-metadata'}
    def manifest(*args):
        events.append('manifest')
        if fault=='manifest':raise C.ContractError('SYNTHETIC_MANIFEST_FAILURE')
        return {'test_only':'manifest'}
    def opened(c,s,row,deadline):
        events.append(row['asset_id']);raw=blocks[row['asset_id']-1]
        if fault=='part' and row['asset_id']==5:raw+=b'changed'
        stream=ShortPartStream(raw);responses.append(stream);return stream
    monkeypatch.setattr(A,'_runtime_release_metadata',metadata)
    monkeypatch.setattr(A,'_runtime_release_manifest',manifest)
    monkeypatch.setattr(A,'_open_runtime_release_asset',opened)
    monkeypatch.setattr(A,'download_runtime_artifact',lambda *a,**k:pytest.fail('fallback'))
    target=tmp_path/'runtime.zip';end=time.monotonic()+30
    if fault is None:
        receipt=A._download_runtime_release(C,A.RUNTIME_TRANSPORT,target,end)
        assert target.read_bytes()==b''.join(blocks)
        assert receipt['archive_sha256']==C.digest(target.read_bytes())
        assert [r['asset_id'] for r in receipt['parts']]==list(range(1,21))
        assert receipt['metadata_checks']['before']==receipt['metadata_checks']['after']
        assert events==['before','manifest',*range(1,21),'after']
        assert all('?sig=' not in r['endpoint'] for r in receipt['parts'])
    else:
        with pytest.raises(ValueError):A._download_runtime_release(C,A.RUNTIME_TRANSPORT,target,end)
        assert not target.exists()
        if fault=='before':assert events==['before']
        elif fault=='manifest':assert events==['before','manifest']
        elif fault=='part':assert events==['before','manifest',*range(1,6)]
        else:assert events==['before','manifest',*range(1,21),'after']
    assert all(r.closed for r in responses)


@pytest.mark.parametrize('fault',['asset_id','manifest_id','manifest_hash','manifest_size','metadata_missing',
    'metadata_before','metadata_after','metadata_asset','metadata_duplicate','endpoint','release_id','bool_id',
    'tag','origin','archive','authority'])
def test_release_receipt_coherent_rehash_still_rejects_substitution(fault):
    source,data,r=evidence(transport_kind='github-release-assets-v0')
    value=C.strict_json(data['runtime-transport.json']);pre=C.strict_json(data['prelaunch.json'])
    if fault=='asset_id':value['parts'][0]['asset_id']+=1
    elif fault=='manifest_id':value['manifest_asset']['asset_id']+=1
    elif fault=='manifest_hash':value['manifest_asset']['sha256']='0'*64
    elif fault=='manifest_size':value['manifest_asset']['size_bytes']+=1
    elif fault=='metadata_missing':del value['metadata_checks']['after']
    elif fault=='metadata_before':value['metadata_checks']['before']['release']['immutable']=False
    elif fault=='metadata_after':value['metadata_checks']['after']['tag']['commit']='0'*40
    elif fault=='metadata_asset':value['metadata_checks']['after']['assets'][0]['state']='starter'
    elif fault=='metadata_duplicate':
        value['metadata_checks']['after']['assets'][1]=copy.deepcopy(value['metadata_checks']['after']['assets'][0])
    elif fault=='endpoint':value['parts'][0]['endpoint']+='?signed=synthetic'
    elif fault=='release_id':value['transport']['release_id']+=1
    elif fault=='bool_id':value['transport']['release_id']=True
    elif fault=='tag':value['transport']['tag']='latest'
    elif fault=='origin':value['origin']['original_artifact_id']+=1
    elif fault=='archive':value['archive_sha256']='0'*64
    else:value['claims']['authority_effect']='allow'
    data['runtime-transport.json']=C.encode(value);pre['runtime_transport_sha256']=C.digest(data['runtime-transport.json'])
    with pytest.raises(ValueError,match='runtime_transport'):K.validate_runtime_transport(source,data,r,pre)


@pytest.mark.parametrize('name,fault',[('RUNTIME_TRANSPORT','release_id'),('RUNTIME_TRANSPORT','tag_commit'),
    ('RUNTIME_RELEASE_ASSETS','asset_id'),('RUNTIME_RELEASE_ASSETS','sha256'),('RUNTIME_RELEASE_ASSETS','duplicate')])
def test_independent_checker_does_not_trust_changed_release_literals(name,fault):
    source={n:(ROOT/n).read_bytes() for n in P['source_files']}
    raw=source[A.SELF].decode();lines=raw.splitlines(keepends=True)
    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    value=ast.literal_eval(node.value)
    if name=='RUNTIME_TRANSPORT':value[fault]=438650667 if fault=='release_id' else 'e'*40
    else:
        rows=list(value)
        if fault=='duplicate':rows[1]=copy.deepcopy(rows[0])
        else:rows[0][fault]=1 if fault=='asset_id' else '0'*64
        value=tuple(rows)
    source[A.SELF]=(''.join(lines[:node.lineno-1])+name+' = '+repr(value)+'\n'+''.join(lines[node.end_lineno:])).encode()
    with pytest.raises(ValueError,match='runtime_transport_release'):K.runtime_transport_source(source)
