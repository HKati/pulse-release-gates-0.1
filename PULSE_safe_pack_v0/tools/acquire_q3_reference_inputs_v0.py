#!/usr/bin/env python3
"""Owner-only Q3 token preflight / finite capture supervision; no metrics.

The stdlib entry guard precedes helper imports, authenticated acquisition,
installation and subject execution. PR/push is never an execution route.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import types
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

REPOSITORY='HKati/pulse-release-gates-0.1'
WORKFLOW='.github/workflows/q3_reference_acquisition_v0.yml'
CONTRACT='PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py'
PROFILE='PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json'
SELF='PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py'
RUNTIME='PULSE_safe_pack_v0/tools/q3_native_runtime_v0.py'
WORKER='PULSE_safe_pack_v0/tools/run_q3_reference_subject_v0.py'
CHECKER='PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py'
SOURCE_FILES=('.github/workflows/q3_reference_acquisition_v0.yml', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/preparation.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/q2-runtime-preparation-check.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/q2_reference_model_files_v0.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/requirements-q2-reference-v0.lock', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/COMMON_INSTRUCTIONS.txt', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/SOURCE_CONTEXT_BINDINGS.json', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/TASKS_DRAFT.jsonl', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/TASK_ORDER.json', 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json', 'PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json', 'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock', 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py', 'PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py', 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py', 'PULSE_safe_pack_v0/tools/q3_native_runtime_v0.py', 'PULSE_safe_pack_v0/tools/run_q3_reference_subject_v0.py', 'docs/compute/PULSEMECH_Q3_ARCHIVED_INPUT_PREPARATION_v0.md', 'docs/compute/PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md', 'schemas/metrics/q3_native_capture_request_v0.schema.json', 'schemas/metrics/q3_native_capture_result_v0.schema.json')


class EntryRejected(ValueError):
    pass


def entry_require(v):
    if not v:raise EntryRejected('Q3_ENTRY_REJECTED')


def boot_read(path,limit=16*1024*1024):
    entry_require(not any(p.is_symlink() for p in [path,*path.parents]))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        a=os.fstat(fd);entry_require(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=limit)
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(limit+1)
        b=os.fstat(fd)
        entry_require(len(raw)==a.st_size and (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==
                      (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns))
        return raw
    finally:os.close(fd)


def boot_git(root,args):
    p=subprocess.run(['/usr/bin/git','--no-replace-objects','-c','protocol.allow=never',
                      '-c','core.hooksPath=/dev/null','-c','safe.directory='+str(root),'-C',str(root),*args],
                     env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C.UTF-8',
                          'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_LAZY_FETCH':'1'},
                     stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
    entry_require(p.returncode==0 and len(p.stdout)<=16*1024*1024);return p.stdout


def entry_guard(root,commit,raw,request_sha,env):
    entry_require(os.geteuid()==0 and sys.flags.isolated)
    entry_require(type(commit) is str and re.fullmatch(r'[a-f0-9]{40}',commit) is not None)
    entry_require(type(raw) is bytes and len(raw)<=128*1024 and hashlib.sha256(raw).hexdigest()==request_sha)
    expected={'GITHUB_REPOSITORY':REPOSITORY,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
              'GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati','GITHUB_RUN_ATTEMPT':'1',
              'GITHUB_SHA':commit,'GITHUB_WORKFLOW_SHA':commit,
              'GITHUB_WORKFLOW_REF':REPOSITORY+'/'+WORKFLOW+'@refs/heads/main'}
    entry_require(all(env.get(k)==v for k,v in expected.items()))
    entry_require(re.fullmatch(r'[1-9][0-9]{0,19}',env.get('GITHUB_RUN_ID','')) is not None)
    entry_require(Path(__file__).resolve()==(root/SELF).resolve())
    entry_require(boot_git(root,['rev-parse','--verify','HEAD']).decode().strip()==commit)
    snapshot={}
    for name in SOURCE_FILES:
        b=boot_read(root/name);entry_require(boot_git(root,['cat-file','blob',commit+':'+name])==b);snapshot[name]=b
    module=types.ModuleType('q3_held_contract');module.__file__=str(root/CONTRACT)
    exec(compile(snapshot[CONTRACT],module.__file__,'exec'),module.__dict__)
    p=module.load_profile(snapshot)
    module.require(set(p['source_files'])==set(SOURCE_FILES),'SOURCE_SCOPE')
    entry=module.strict_json(raw,128*1024)
    if type(entry) is dict and entry.get('record_type')=='q3_capture_handoff_request_v1':
        module.require(type(entry.get('native_request_utf8')) is str,'HANDOFF_NATIVE_REQUEST')
        native_raw=entry['native_request_utf8'].encode('utf-8')
        r=module.validate_request(native_raw,p)
        module.require(r['mode']=='capture','HANDOFF_CAPTURE_ONLY')
    else:
        r=module.validate_request(raw,p)
        module.require(r['mode']=='token-preflight','CAPTURE_HANDOFF_REQUIRED')
    module.require(r['source_commit']==commit,'REQUEST_SOURCE')
    module.task_frame(snapshot,p)
    return module,p,r,snapshot


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def api_bytes(path,token,limit=16*1024*1024):
    # Paths are constructed by this program, never accepted from the request.
    entry_require(path.startswith('/repos/'+REPOSITORY+'/') or path=='/repos/'+REPOSITORY)
    req=urllib.request.Request('https://api.github.com'+path,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'PULSE-Q3-native-v0'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
        entry_require(response.status==200);raw=response.read(limit+1)
    entry_require(len(raw)<=limit);return raw


def control_plane(C,request,env,token):
    run_id=env['GITHUB_RUN_ID']
    base='/repos/'+REPOSITORY
    run=C.strict_json(api_bytes(base+'/actions/runs/'+run_id+'/attempts/1',token))
    repo=C.strict_json(api_bytes(base,token))
    branch=C.strict_json(api_bytes(base+'/branches/main',token))
    C.require(type(run['id']) is int and str(run['id'])==run_id and type(run['run_attempt']) is int
              and run['run_attempt']==1 and run['head_sha']==request['source_commit']
              and run['head_branch']=='main' and run['event']=='workflow_dispatch'
              and run['path'].split('@',1)[0]==WORKFLOW
              and run['actor']['login']=='HKati' and run['triggering_actor']['login']=='HKati'
              and repo['full_name']==REPOSITORY and repo['private'] is False
              and branch['commit']['sha']==request['source_commit'],'CONTROL_PLANE_MISMATCH')
    return {'run_id':run_id,'run_attempt':1,'source_commit':request['source_commit'],
            'repository':REPOSITORY,'repository_private':False,'event':'workflow_dispatch',
            'workflow':WORKFLOW,'head_branch':'main','actor':'HKati','triggering_actor':'HKati',
            'clock_relation':'not_verified'}


def download_runtime(C,p,token,target,phase_deadline):
    a=p['runtime_archive'];base='/repos/'+REPOSITORY
    meta=C.strict_json(api_bytes(base+'/actions/artifacts/'+str(a['artifact_id']),token))
    C.require(type(meta['id']) is int and meta['id']==a['artifact_id'] and meta['expired'] is False
              and meta['size_in_bytes']==a['size_bytes'] and meta['digest']=='sha256:'+a['sha256']
              and str(meta['workflow_run']['id'])==a['run_id'],'RUNTIME_ARTIFACT_METADATA')
    req=urllib.request.Request('https://api.github.com'+base+'/actions/artifacts/'+str(a['artifact_id'])+'/zip',
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    try:
        response=urllib.request.build_opener(NoRedirect()).open(req,timeout=15)
    except urllib.error.HTTPError as exc:
        C.require(exc.code in (301,302,303,307,308),'RUNTIME_REDIRECT_REQUIRED')
        location=exc.headers.get('Location','');u=urllib.parse.urlsplit(location)
        C.require(u.scheme=='https' and not u.username and not u.password and u.port in (None,443)
                  and u.hostname is not None and (u.hostname.endswith('.blob.core.windows.net')
                  or u.hostname.endswith('.actions.githubusercontent.com')),'RUNTIME_REDIRECT_HOST')
        # No bearer token or ambient request headers are forwarded to signed storage.
        response=urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(location),timeout=15)
    else:
        response.close();raise C.ContractError('RUNTIME_REDIRECT_REQUIRED')
    end=min(phase_deadline,time.monotonic()+180);total=0;h=hashlib.sha256()
    with response, target.open('xb') as f:
        os.fchmod(f.fileno(),0o600)
        while True:
            C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
            b=response.read(65536)
            if not b:break
            total+=len(b);C.require(total<=a['size_bytes'],'RUNTIME_DOWNLOAD_SIZE')
            h.update(b);f.write(b)
        f.flush();os.fsync(f.fileno())
    C.require(total==a['size_bytes'] and h.hexdigest()==a['sha256'],'RUNTIME_ARCHIVE_MISMATCH')


def load_sealed(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod);return mod


def failure_code(exc):
    if isinstance(exc,KeyboardInterrupt):return 'CAPTURE_INTERRUPTED'
    if isinstance(exc,ValueError) and len(exc.args)==1 and type(exc.args[0]) is str:
        code=exc.args[0]
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}',code):return code
    return 'RUNTIME_OR_EVIDENCE_UNAVAILABLE'


def receive_tokens(C,R,svc,frame,p,evidence,binding):
    deadline=min(svc.deadline,time.monotonic()+300)
    ready=svc.reader.line(deadline);R.save(evidence/'worker-ready.json',ready)
    C.require(C.strict_json(ready)=={'record_type':'q3_worker_ready_v0','binding':binding,'mode':p['_mode']},'WORKER_READY')
    svc.send(b'TOKENIZE\n');rows=[]
    for task in frame:
        raw=svc.reader.line(deadline);R.save(evidence/'tokens'/(task['task_id']+'.json'),raw)
        value=C.strict_json(raw)
        C.fields(value,{'record_type','binding','row'})
        C.require(value['record_type']=='q3_token_row_v0' and value['binding']==binding,'TOKEN_ROW_BINDING')
        row=value['row'];C.fields(row,{'task_id','ordinal','input_ids','messages_sha256','logical_request_sha256'})
        C.require(row['task_id']==task['task_id'] and type(row['ordinal']) is int and row['ordinal']==task['ordinal'],'TOKEN_ROW_ORDER')
        ids=row['input_ids'];C.require(type(ids) is list and 1<=len(ids)<=p['limits']['max_prompt_tokens']
            and all(type(i) is int and 0<=i<49152 for i in ids),'TOKEN_BOUNDS')
        C.require(row['messages_sha256']==C.digest(C.encode(task['messages']))
            and row['logical_request_sha256']==C.digest(task['logical_request_text'].encode()),'TOKEN_ROW_INPUT')
        rows.append(row)
    token_map={'record_type':'q3_token_map_v0','profile_sha256':C.PROFILE_SHA256,'model_revision':p['model_revision'],
               'task_file_sha256':p['fixed_inputs'][C.FRAME+'TASKS_DRAFT.jsonl'],'rows':rows}
    token_bytes=C.encode(token_map);sha=C.digest(token_bytes)
    end_raw=svc.reader.line(deadline);R.save(evidence/'token-map-end.json',end_raw)
    C.require(C.strict_json(end_raw)=={'record_type':'q3_token_map_end_v0','binding':binding,'token_map_sha256':sha,'task_count':204},'TOKEN_MAP_END')
    R.save(evidence/'token-map.json',token_bytes)
    return token_map,sha


def exchange_capture(C,R,life,svc,p,frame,token_map,binding,evidence,terminal,prefix):
    map_sha=C.digest(C.encode(token_map));svc.send(('LOAD '+map_sha+'\n').encode())
    raw=svc.reader.line(min(svc.deadline,time.monotonic()+180));R.save(evidence/'model-ready.json',raw)
    ready=C.strict_json(raw)
    C.fields(ready,{'record_type','binding','token_map_sha256','effective_generation','runtime'})
    C.require(ready['record_type']=='q3_model_ready_v0' and ready['binding']==binding and ready['token_map_sha256']==map_sha,'MODEL_READY')
    for key,val in p['generation'].items():
        C.require(C.encode(ready['effective_generation'].get(key))==C.encode(val),'GENERATION_SETTINGS')
    subject={'record_type':'q3_capture_subject_v0','binding':binding,
             'model_ready_sha256':C.digest(raw),'token_map_sha256':map_sha}
    subject_raw=C.encode(subject);R.save(evidence/'subject.json',subject_raw)
    full_binding={**binding,'subject_sha256':C.digest(subject_raw)}
    svc.send(('BIND '+C.digest(subject_raw)+'\n').encode())
    bound=svc.reader.line(min(svc.deadline,time.monotonic()+20));R.save(evidence/'bound.json',bound)
    C.require(C.strict_json(bound)=={'record_type':'q3_bound_v0','binding':full_binding},'BOUND_ACK')
    for task,row,occ in zip(frame,token_map['rows'],terminal['occurrences']):
        name=task['task_id'];stem=evidence/'calls'/name
        occ['status']='preparation_failed'
        svc.send(('PREPARE '+name+'\n').encode())
        ready_raw=svc.reader.line(min(svc.deadline,time.monotonic()+20));R.save(stem.with_suffix('.ready.json'),ready_raw)
        sr=C.strict_json(ready_raw)
        slot={'task_id':name,'ordinal':task['ordinal'],'attempt':1}
        C.require(sr=={'record_type':'q3_slot_ready_v0','binding':full_binding,'slot':slot,
                       'input_ids':row['input_ids'],'effective_generation':ready['effective_generation'],'runtime':ready['runtime']},'SLOT_READY')
        R.save(stem.with_suffix('.intent.json'),C.encode({'task_id':name,'ordinal':task['ordinal'],
                'binding':full_binding,'intent':'before_GO','attempt':1}))
        occ['intent_saved_ns']=time.monotonic_ns()
        timer=prefix+f"-call-{task['ordinal']:03d}"
        arm=time.monotonic_ns();occ['watchdog_arm_begin_ns']=arm;life.arm(timer,svc.unit)
        C.require(time.monotonic_ns()+60*1000000000 < min(arm+65*1000000000,svc.runtime_deadline_ns), 'FULL_RESPONSE_WINDOW_UNAVAILABLE')
        C.require(not svc.reader.buffer and not svc.reader.selector.select(0),'UNSOLICITED_RESPONSE')
        occ['status']='attempt_uncertain';terminal['attempted_calls']+=1
        start=svc.send(('GENERATE '+name+'\n').encode());deadline=start+60*1000000000
        occ['generation_start_ns']=start;occ['generation_deadline_ns']=deadline
        raw=svc.reader.line(deadline/1e9);received=time.monotonic_ns()
        occ['response_received_ns']=received
        # Preserve the exact bounded frame before interpreting content or termination.
        R.save(stem.with_suffix('.response.json'),raw)
        C.require(received<=deadline and len(raw)<=p['limits']['max_raw_frame_bytes'],'RESPONSE_LATE_OR_LARGE')
        close=life.disarm(timer,min(svc.deadline,time.monotonic()+30));occ['watchdog_closed_ns']=close['closed_ns']
        response=C.strict_json(raw)
        C.require(response.get('record_type')=='q3_response_v0' and response.get('binding')==full_binding
                  and response.get('slot')==slot and type(response.get('text')) is str,'RESPONSE_IDENTITY')
        text=response['text'].encode('utf-8');C.require(len(text)<=p['limits']['max_response_utf8_bytes'],'RESPONSE_TEXT_BOUND')
        R.save(stem.with_suffix('.utf8'),text)
        occ['status']='length_terminated' if response.get('stop_reason')=='token_limit' else 'completed'
        C.require(response.get('stop_reason')=='eos','TOKEN_LIMIT_TERMINATION')
    svc.send(b'FINISH\n');end=svc.reader.line(svc.deadline);R.save(evidence/'session-end.json',end)
    C.require(C.strict_json(end)=={'record_type':'q3_session_end_v0','binding':full_binding,'completed_calls':204},'SESSION_END')


def output_destination(C,env):
    uid=int(env.get('SUDO_UID','-1'));gid=int(env.get('SUDO_GID','-1'))
    C.require(0<uid<2**31 and 0<gid<2**31,'OUTPUT_OWNER')
    base=Path(env['RUNNER_TEMP']).absolute()
    C.require(base.is_dir() and not any(p.is_symlink() for p in [base,*base.parents]),'OUTPUT_PARENT')
    parent=base/'q3-reference-capture'
    try:parent.mkdir(mode=0o700);os.chmod(parent,0o700);os.chown(parent,uid,gid)
    except FileExistsError:pass
    st=parent.lstat();C.require(stat.S_ISDIR(st.st_mode) and st.st_uid==uid and stat.S_IMODE(st.st_mode)==0o700,'OUTPUT_PARENT_MODE')
    target=parent/(env['GITHUB_RUN_ID']+'-1')
    target.mkdir(mode=0o700);os.chmod(target,0o700)
    C.require(stat.S_IMODE(target.lstat().st_mode)==0o700,'OUTPUT_DIRECTORY_MODE')
    return target,uid,gid


def build_carrier(C,data,request,status,error):
    C.require('result.json' not in data,'RESULT_RECURSION')
    result={'record_type':'q3_native_capture_result_v0','mode':request['mode'],'status':status,'error_code':error,
            'source_commit':request['source_commit'],'request_sha256':C.digest(data['request.json']),
            'inventory':{n:{'size_bytes':len(b),'sha256':C.digest(b)} for n,b in sorted(data.items())},'claims':dict(C.CLAIMS)}
    all_data={**data,'result.json':C.encode(result)}
    C.require(sum(map(len,all_data.values()))<=256*1024*1024 and len(all_data)<=2000,'CARRIER_BOUND')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
        for name,raw in sorted(all_data.items()):
            C.relative(name);info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.external_attr=(stat.S_IFREG|0o600)<<16
            z.writestr(info,raw)
    return out.getvalue(),result


def publish(C,K,snapshot,output,uid,gid,data,request,status,error):
    archive,result=build_carrier(C,data,request,status,error)
    directory=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    ds=os.fstat(directory);directory_identity=(ds.st_dev,ds.st_ino);owned={}
    def unchanged_directory():
        now=output.lstat()
        C.require(stat.S_ISDIR(now.st_mode) and (now.st_dev,now.st_ino)==directory_identity,'PUBLICATION_DIRECTORY_CHANGED')
    def create(name,raw):
        unchanged_directory();C.write_new(output/name,raw)
        st=os.stat(name,dir_fd=directory,follow_symlinks=False)
        owned[name]=(st.st_dev,st.st_ino)
        unchanged_directory()
    try:
        create('evidence.zip',archive)
        checked=K.check_carrier(output/'evidence.zip',snapshot,C.digest(archive),
                                C.digest(data['request.json']),request['source_commit'])
        C.require(checked['complete']==(status=='complete'),'FINAL_CARRIER_CHECK')
        receipt={'record_type':'q3_native_capture_receipt_v0','status':status,'mode':request['mode'],
                 'archive_sha256':C.digest(archive),'archive_size_bytes':len(archive),
                 'result_sha256':C.digest(C.encode(result)),'request_sha256':C.digest(data['request.json']),
                 'source_commit':request['source_commit'],'token_map_sha256':C.digest(data['token-map.json']) if 'token-map.json' in data else None,
                 'claims':dict(C.CLAIMS)}
        if status=='incomplete':
            create('failure.json',C.encode({'record_type':'q3_native_failure_v0','error_code':error,'complete':False,'claims':dict(C.CLAIMS)}))
        create('receipt.json',C.encode(receipt))
        for name,identity in owned.items():
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
            try:
                st=os.fstat(fd)
                C.require(stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino)==identity,'PUBLISHED_MEMBER_REPLACED')
                # Change only the retained owned object, never a substituted pathname.
                os.fchown(fd,uid,gid);os.fchmod(fd,0o600);os.fsync(fd)
                st=os.fstat(fd);at=os.stat(name,dir_fd=directory,follow_symlinks=False)
                C.require((at.st_dev,at.st_ino)==identity and st.st_uid==uid and st.st_gid==gid
                          and stat.S_IMODE(st.st_mode)==0o600,'PUBLISHED_MEMBER_CUSTODY')
            finally:os.close(fd)
        unchanged_directory();os.fchown(directory,uid,gid);os.fchmod(directory,0o700)
        C.require(C.safe_read(output/'evidence.zip',256*1024*1024)==archive
                  and C.safe_read(output/'receipt.json')==C.encode(receipt),'PUBLISHED_READBACK')
        st=os.fstat(directory)
        C.require(st.st_uid==uid and st.st_gid==gid and stat.S_IMODE(st.st_mode)==0o700,'PUBLISHED_DIRECTORY_CUSTODY')
        unchanged_directory();os.fsync(directory)
        return receipt
    except BaseException:
        # A replacement is preserved; absence/partial publication is never success.
        for name,identity in reversed(list(owned.items())):
            try:
                st=os.stat(name,dir_fd=directory,follow_symlinks=False)
                if (st.st_dev,st.st_ino)==identity:os.unlink(name,dir_fd=directory)
            except OSError:pass
        raise
    finally:os.close(directory)


def setup_workspace(C,snapshot,work):
    """No subject has started here. Never recursively remove an unowned replacement."""
    identity=None
    try:
        work.mkdir(mode=0o700)
        st=work.lstat();identity=(st.st_dev,st.st_ino)
        os.chmod(work,0o700,follow_symlinks=False)
        sources=work/'source';sources.mkdir(mode=0o755);os.chmod(sources,0o755)
        for name,b in snapshot.items():
            path=sources/name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            for parent in path.parents:
                if parent==work:break
                os.chmod(parent,0o755,follow_symlinks=False)
            C.write_new(path,b,0o444)
        R=load_sealed('q3_verified_runtime',sources/RUNTIME)
        K=load_sealed('q3_verified_independent_checker',sources/CHECKER)
        R.freeze(sources);os.chmod(work,0o755)
        evidence=R.private_directory(work/'evidence',mode=0o755)
        logs=R.private_directory(work/'private')
        return R,K,sources,evidence,logs
    except BaseException as exc:
        cleaned=False
        if identity is not None:
            try:
                st=work.lstat()
                if stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==identity:
                    shutil.rmtree(work);cleaned=not work.exists() and not work.is_symlink()
            except OSError:pass
        # Retain original failure and explicit uncertain-cleanup state separately.
        err=EntryRejected(failure_code(exc));err.cleanup_complete=cleaned
        raise err from exc


def setup_failure(C,output,uid,gid,request,exc):
    record={'record_type':'q3_native_setup_failure_v0','complete':False,
            'error_code':failure_code(exc),'cleanup_complete':getattr(exc,'cleanup_complete',False),
            'source_commit':request['source_commit'],'claims':dict(C.CLAIMS)}
    raw=C.encode(record);path=output/'failure.json';C.write_new(path,raw)
    st=path.lstat();identity=(st.st_dev,st.st_ino)
    try:
        os.chown(path,uid,gid,follow_symlinks=False);os.chmod(path,0o600,follow_symlinks=False)
        os.chown(output,uid,gid,follow_symlinks=False);os.chmod(output,0o700,follow_symlinks=False)
        st=path.lstat();C.require((st.st_dev,st.st_ino)==identity and st.st_uid==uid and st.st_gid==gid
                                 and stat.S_IMODE(st.st_mode)==0o600 and C.safe_read(path)==raw,'FAILURE_CUSTODY')
        fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    except BaseException:
        # No success receipt was created; a failed failure-report handoff remains a failure.
        raise
    return 1


def execute(C,p,request,snapshot,root,raw,env):
    # No helper import or network operation before entry_guard returns.
    token=env.get('GITHUB_TOKEN','');C.require(bool(token),'READ_TOKEN_REQUIRED')
    plane=control_plane(C,request,env,token)
    output,uid,gid=output_destination(C,env)
    work=Path('/var/lib')/('pulse-q3-'+uuid.uuid4().hex[:24])
    try:
        R,K,sources,evidence,logs=setup_workspace(C,snapshot,work)
    except BaseException as exc:
        return setup_failure(C,output,uid,gid,request,exc)
    life=R.Lifecycle();phase_deadline=time.monotonic()+p['limits']['acquisition_phase_seconds']
    frame=C.task_frame(snapshot,p)
    status='incomplete';error='CAPTURE_INCOMPLETE';svc=None;terminal=None;data={}
    original_signal={}
    def interrupted(signum,frame):raise KeyboardInterrupt()
    for signum in (signal.SIGTERM,signal.SIGINT):
        original_signal[signum]=signal.signal(signum,interrupted)
    try:
        R.save(evidence/'request.json',raw)
        R.save(evidence/'control-plane.json',C.encode(plane))
        for name,b in snapshot.items():R.save(evidence/'source'/name,b)
        platform=R.platform_context();R.save(evidence/'platform.json',C.encode(platform))
        C.require(shutil.disk_usage(work).free>=6*1024**3,'INSUFFICIENT_WORK_DISK')
        archive=work/'runtime.zip';download_runtime(C,p,token,archive,phase_deadline)
        # Immutable selected bytes are inspected; archive code is never executed here.
        checked=K.verify_archive(archive,work/'staged',sources)
        R.save(evidence/'input-check.json',C.encode(checked))
        bundle=work/'staged/bundle';R.freeze(work/'staged');os.chmod(work/'staged',0o755);os.chmod(bundle,0o755)
        python=Path(sys.executable).resolve()
        install=R.private_directory(work/'install',uid=65534,gid=65534)
        R.phase(life,work.name,'installer',[python,'-I','-B','-c',R.INSTALLER,install,bundle/'wheelhouse',sources/'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock',install],
                install,python,logs,phase_deadline,evidence)
        venv=install/'venv';R.freeze(install);os.chmod(install,0o755)
        for name in ['bootstrap.json','pip-report.json']:R.save(evidence/name,C.safe_read(install/name))
        checking=R.private_directory(work/'installcheck',uid=65534,gid=65534)
        R.phase(life,work.name,'installcheck',[python,'-I','-B',sources/CHECKER,'--phase','verify-installation',
            '--source-root',sources,'--venv',venv,'--bundle',bundle,'--bootstrap-inventory',evidence/'bootstrap.json',
            '--pip-report',evidence/'pip-report.json','--output',checking/'installation.json'],
            checking,python,logs,phase_deadline,evidence)
        R.freeze(checking);installation=C.safe_read(checking/'installation.json')
        R.save(evidence/'installation.json',installation)
        pre={'record_type':'q3_native_prelaunch_v0','request':request,'source_commit':request['source_commit'],
             'run_id':env['GITHUB_RUN_ID'],'run_attempt':1,'source_files':{n:C.digest(b) for n,b in snapshot.items()},
             'platform_sha256':C.digest(C.encode(platform)),'control_plane_sha256':C.digest(C.encode(plane)),
             'installation_sha256':C.digest(installation),
             'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'clock_relation':'not_verified'}
        pre_raw=C.encode(pre);R.save(evidence/'prelaunch.json',pre_raw)
        binding={'prelaunch_sha256':C.digest(pre_raw),'source_commit':request['source_commit'],
                 'run_id':env['GITHUB_RUN_ID'],'run_attempt':1}
        terminal={'record_type':'q3_capture_terminal_v0','mode':request['mode'],'binding':binding,
                  'complete':False,'error_code':'CAPTURE_INCOMPLETE','attempted_calls':0,
                  'occurrences':[{'task_id':t['task_id'],'ordinal':t['ordinal'],'attempt':1,
                   'status':'not_requested' if request['mode']=='token-preflight' else 'not_started'} for t in frame],
                  'worker_exit_code':None,'stdout_eof':False,'worker_deadline_ns':None,
                  'worker_exit_observed_ns':None,'ended_at':None}
        worker_work=R.private_directory(work/'worker',uid=65534,gid=65534)
        stage='preflight' if request['mode']=='token-preflight' else 'captureworker'
        svc=life.start(work.name,stage,[venv/'bin/python','-I','-B',sources/WORKER,'--source-root',sources,
                    '--bundle',bundle,'--prelaunch',evidence/'prelaunch.json','--expected-prelaunch-sha256',C.digest(pre_raw)],
                    worker_work,python,logs/'worker.log',phase_deadline)
        terminal['worker_deadline_ns']=svc.runtime_deadline_ns
        R.save(evidence/'worker-sandbox.json',C.encode(svc.observation))
        token_map,map_sha=receive_tokens(C,R,svc,frame,{**p,'_mode':request['mode']},evidence,binding)
        if request['mode']=='token-preflight':
            svc.send(b'FINISH\n');end=svc.reader.line(svc.deadline);R.save(evidence/'session-end.json',end)
            C.require(C.strict_json(end)=={'record_type':'q3_session_end_v0','binding':binding,'completed_calls':0},'PREFLIGHT_SESSION_END')
        else:
            C.require(map_sha==request['approved_token_map_sha256'],'APPROVED_TOKEN_MAP_MISMATCH')
            exchange_capture(C,R,life,svc,p,frame,token_map,binding,evidence,terminal,work.name)
        svc.complete();terminal.update(worker_exit_code=0,stdout_eof=True,
            worker_exit_observed_ns=time.monotonic_ns(),ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        C.require(terminal['worker_exit_observed_ns']<=terminal['worker_deadline_ns'],'WORKER_TERMINAL_LATE')
        closed=svc.close(min(phase_deadline,time.monotonic()+30));R.save(evidence/'worker-cleanup.json',C.encode(closed))
        terminal.update(complete=True,error_code=None)
        R.save(evidence/'terminal.json',C.encode(terminal))
        decode=R.private_directory(work/'decodecheck',uid=65534,gid=65534)
        R.phase(life,work.name,'decodecheck',[venv/'bin/python','-I','-B',sources/CHECKER,'--phase','verify-tokens',
            '--source-root',sources,'--bundle',bundle,'--evidence',evidence,'--output',decode/'token-check.json'],
            decode,python,logs,phase_deadline,evidence)
        R.freeze(decode);R.save(evidence/'token-check.json',C.safe_read(decode/'token-check.json'))
        if request['mode']=='capture':R.save(evidence/'examples.jsonl',C.safe_read(decode/'examples.jsonl'))
        for name,b in snapshot.items():C.require(C.safe_read(sources/name)==b,'SEALED_SOURCE_CHANGED')
        C.require(time.monotonic()<=phase_deadline,'PHASE_DEADLINE')
        status='complete';error=None
    except BaseException as exc:
        error=failure_code(exc)
        if terminal is not None:
            terminal.update(complete=False,error_code=error)
            if svc is not None and svc.reader is not None and svc.reader.buffer:
                try:R.save(evidence/'unfinished-protocol-prefix.bin',svc.reader.buffer[:1024*1024])
                except Exception:pass
    finally:
        # Preserve the first failure while bounded cleanup runs. Outer workflow/timeout
        # still supplies a hard kill if this process cannot complete its grace.
        for sig in original_signal:signal.signal(sig,signal.SIG_IGN)
        cleanup=life.cleanup()
        if not cleanup['cleanup_complete']:
            status='incomplete';error=error or 'CLEANUP_UNVERIFIED'
        if terminal is not None and not (evidence/'terminal.json').exists():
            try:R.save(evidence/'terminal.json',C.encode(terminal))
            except Exception:status='incomplete';error=error or 'TERMINAL_PRESERVATION_FAILED'
        try:data=K.read_evidence(evidence)
        except Exception:
            status='incomplete';error=error or 'EVIDENCE_READBACK_FAILED';data={'request.json':raw}
        removed=False
        if cleanup['cleanup_complete']:
            try:shutil.rmtree(work);removed=not work.exists() and not work.is_symlink()
            except Exception:pass
        else:
            try:os.chmod(work,0o700)
            except OSError:pass
        cleanup['private_tree_removed']=removed
        data['lifecycle.json']=C.encode(cleanup)
        if not removed:status='incomplete';error=error or 'PRIVATE_TREE_CLEANUP_FAILED'
        try:
            if status=='complete':K.validate_complete(snapshot,data)
        except Exception as exc:status='incomplete';error=failure_code(exc)
        try:receipt=publish(C,K,snapshot,output,uid,gid,data,request,status,error)
        finally:
            for sig,old in original_signal.items():signal.signal(sig,old)
    print('Q3 '+request['mode']+' '+status+'; no labels, metric or release authority.')
    return 0 if status=='complete' else 1



# The v0 execute/publish functions remain the internal native core and historical
# regression seams, not public admission interfaces. Every supported execution
# entry (this CLI and the existing manual workflow) reaches this mandatory path.
HANDOFF_SOURCE='tools/q3_capture_handoff_v1.py'
HANDOFF_SOURCES=('schemas/metrics/q3_capture_handoff_request_v1.schema.json',
                 'tools/acquire_q3_external_postflight_v0.py',
                 'tools/check_q3_external_postflight_v0.py',
                 'tools/q3_capture_handoff_v1.py')


def execute_handoff(C,p,request,snapshot,root,raw,env):
    extra={}
    for name in HANDOFF_SOURCES:
        b=boot_read(root/name,128*1024)
        entry_require(boot_git(root,['cat-file','blob',request['source_commit']+':'+name])==b)
        extra[name]=b
    mod=types.ModuleType('q3_verified_capture_handoff_v1');mod.__file__=str(root/HANDOFF_SOURCE)
    exec(compile(extra[HANDOFF_SOURCE],mod.__file__,'exec',dont_inherit=True),mod.__dict__)
    entry_require(tuple(mod.EXTRA_SOURCES)==HANDOFF_SOURCES)
    return mod.run(C,p,request,snapshot,root,raw,env,extra,execute,control_plane,output_destination)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--source-commit',required=True)
    ap.add_argument('--request',required=True);ap.add_argument('--request-sha256',required=True)
    args=ap.parse_args(argv)
    try:
        raw=args.request.encode('utf-8');root=args.repo_root.absolute();env=dict(os.environ)
        C,p,request,snapshot=entry_guard(root,args.source_commit,raw,args.request_sha256,env)
        if request['mode']=='capture':
            return execute_handoff(C,p,request,snapshot,root,raw,env)
        return execute(C,p,request,snapshot,root,raw,env)
    except BaseException:
        print('Q3 rejected or final publication unavailable; no successful capture claimed.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
