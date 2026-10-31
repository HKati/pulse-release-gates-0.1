#!/usr/bin/env python3
"""Prepare, explicitly authorize, or verify one bounded W1 diagnostic capture.

Default/help and preparation do not execute candidates or contact Docker.
No image pull, package installation, normal-launch bypass or workflow dispatch.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

BASE = '2890469ee82333f4d34872bbe711cda6ad9b49aa'
CHECKER_SHA = '56fabc69fe654188c3ede2f2537ff576228485e7d8228ef3d2584bd1bc50694b'
MODULES = ('run_paradox_w1_native_v0.py', 'paradox_w1_native_runtime_v0.py',
           'paradox_w1_native_observer_v0.py', 'paradox_w1_docker_boundary_v0.py',
           'check_paradox_w1_records_v0.py')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

HERE = Path(__file__).resolve().parent
O = load_module('w1_native_observer', HERE / 'paradox_w1_native_observer_v0.py')
B = load_module('w1_docker_boundary', HERE / 'paradox_w1_docker_boundary_v0.py')
need, canonical, digest = O.need, O.canonical, O.digest


def read_regular(path, limit=4*1024*1024):
    path=Path(path)
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink_path')
    fd=os.open(path,os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0))
    try:
        st=os.fstat(fd);need(stat.S_ISREG(st.st_mode) and st.st_size<=limit,'regular_file_limit')
        with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(limit+1)
        need(len(raw)<=limit,'file_size');return raw
    finally: os.close(fd)


def checker():
    raw=read_regular(HERE/'check_paradox_w1_records_v0.py')
    need(digest(raw)==CHECKER_SHA,'record_checker_source_identity')
    return load_module('bound_w1_checker',HERE/'check_paradox_w1_records_v0.py')


def _payloads(repo, selection):
    binding=json.loads(read_regular(repo/'docs/experiments/PD_SM_02_W1_SOURCE_BINDING_v0.json'))
    paths=['docs/experiments/PD_SM_02_W1_'+n for n in ('CONTRACT_v0.md','SELECTION_v0.json','SOURCE_BINDING_v0.json')]
    paths += [binding['archive']['repository_path']] + [r['repository_path'] for r in binding['source_files']]
    payloads={'frozen/'+p:read_regular(repo/p) for p in paths}
    payloads.update({'tools/'+n:read_regular(HERE/n) for n in MODULES})
    payloads.update({'cases/'+r['case_id']+'.json':canonical(O.input_case(r)) for r in selection['cases']})
    return payloads


def prepare(repo: Path, output: Path, image: str, run_id: str):
    """Create an owner-reviewable request. No authorization is created."""
    B.image_id(image)
    need(type(run_id) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_id), 'run_id')
    repo=repo.resolve();output=output.absolute()
    need(not output.exists() and not output.is_symlink(),'output_exists')
    need(repo not in output.resolve().parents and output.resolve()!=repo, 'output_inside_repository')
    C=checker(); selection,receipt=C.admit_inputs(repo)
    payloads=_payloads(repo,selection)
    profile=payloads['frozen/examples/paradox_preexecution_impact_v0/profile.json']
    sources={n:digest(payloads['tools/'+n]) for n in MODULES}
    request={'schema_version':'pd_sm_02_w1_native_request_v0','subject':O.SUBJECT,
             'preparation_base':BASE,'run_id':run_id,'attempt':1,'image_id':image,
             'runtime':dict(O.RUNTIME),'policy':B.POLICY,'policy_sha256':B.policy_digest(),
             'selection_sha256':C.SELECTION_SHA,'source_binding_sha256':C.BINDING_SHA,
             'contract_sha256':C.CONTRACT_SHA,'archive_sha256':C.ARCHIVE_SHA,
             'profile_sha256':digest(profile),'sources':sources,
             'maximum_candidate_invocations':5,'supervision_controls':['probe-time','probe-output'],
             'automatic_retry':False,'execution_authorized':False,'authority_effect':'none',
             'cases':[{'case_id':r['case_id'],'input_sha256':digest(payloads['cases/'+r['case_id']+'.json']),
                       'candidate_sha256':r['candidate_raw_sha256']} for r in selection['cases']],
             'payloads':{p:{'bytes':len(raw),'sha256':digest(raw)} for p,raw in sorted(payloads.items())}}
    output.mkdir(parents=False,mode=0o700)
    for name,raw in payloads.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    raw=canonical(request);(output/'request.json').write_bytes(raw)
    return {'status':'REQUEST_PREPARED_NOT_AUTHORIZED','request_sha256':digest(raw),
            'request_path':str(output/'request.json'),'new_candidate_executions':0,
            'execution_authorized':False,'authority_effect':'none'}


def validate_package(package: Path, expected_sha: str):
    need(type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}',expected_sha),'request_sha_required')
    raw=read_regular(package/'request.json',131072)
    need(digest(raw)==expected_sha,'request_digest_mismatch')
    req=O.strict(raw,131072);need(canonical(req)==raw,'request_not_canonical')
    O.keys(req,{'schema_version','subject','preparation_base','run_id','attempt','image_id','runtime','policy','policy_sha256',
                'selection_sha256','source_binding_sha256','contract_sha256','archive_sha256','profile_sha256','sources',
                'maximum_candidate_invocations','supervision_controls','automatic_retry','execution_authorized','authority_effect',
                'cases','payloads'},'request_shape')
    need(req['schema_version']=='pd_sm_02_w1_native_request_v0' and req['subject']==O.SUBJECT and req['preparation_base']==BASE,'request_subject')
    need(type(req['run_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',req['run_id']),'request_run_id')
    need(type(req['attempt']) is int and req['attempt']==1 and type(req['maximum_candidate_invocations']) is int
         and req['maximum_candidate_invocations']==5,'request_budget')
    need(req['supervision_controls']==['probe-time','probe-output'] and req['automatic_retry'] is False
         and req['execution_authorized'] is False and req['authority_effect']=='none','request_authority')
    B.image_id(req['image_id']);need(req['runtime']==O.RUNTIME and canonical(req['policy'])==canonical(B.POLICY)
        and req['policy_sha256']==B.policy_digest(),'request_profile')
    # Bind the executing controller and all helpers, not just copied input bytes.
    need(req['sources']=={n:digest(read_regular(HERE/n)) for n in MODULES},'controller_source_closure')
    C=checker();selection,receipt=C.admit_inputs(package/'frozen')
    expected=_payloads(package/'frozen',selection)
    need(req['payloads']=={p:{'bytes':len(raw),'sha256':digest(raw)} for p,raw in sorted(expected.items())},'request_payload_inventory')
    for p,b in expected.items(): need(read_regular(package/p)==b,'payload_binding:'+p)
    need(req['selection_sha256']==C.SELECTION_SHA and req['source_binding_sha256']==C.BINDING_SHA
         and req['contract_sha256']==C.CONTRACT_SHA and req['archive_sha256']==C.ARCHIVE_SHA,'frozen_binding')
    need(req['profile_sha256']==digest(expected['frozen/examples/paradox_preexecution_impact_v0/profile.json']),'profile_binding')
    need(req['cases']==[{'case_id':r['case_id'],'input_sha256':digest(expected['cases/'+r['case_id']+'.json']),
                       'candidate_sha256':r['candidate_raw_sha256']} for r in selection['cases']],'request_case_inventory')
    allowed=set(expected)|{'request.json'}
    for p in package.rglob('*'):
        need(not p.is_symlink(),'package_symlink')
        if p.is_file() and p.relative_to(package).parts[0] not in ('capture', 'CLAIM.json'):
            need(p.relative_to(package).as_posix() in allowed,'unexpected_package_file')
    return req,selection,C,receipt


def write_json(path, obj):
    raw=canonical(obj)+b'\n'
    with open(path,'xb') as f: f.write(raw);f.flush();os.fsync(f.fileno())


def close_manifest(capture):
    inventory={}
    for p in sorted(capture.rglob('*')):
        need(not p.is_symlink(),'capture_symlink')
        if p.is_file() and p.relative_to(capture).as_posix()!='MANIFEST.json':
            raw=read_regular(p,8*1024*1024);inventory[p.relative_to(capture).as_posix()]={'bytes':len(raw),'sha256':digest(raw)}
    write_json(capture/'MANIFEST.json',{'schema_version':'pd_sm_02_w1_capture_manifest_v0','files':inventory,'authority_effect':'none'})


def stage_inputs(package,req,row,stage):
    stage.mkdir(mode=0o755)
    files={'request.json':read_regular(package/'request.json'),
           'runtime.py':read_regular(package/'tools/paradox_w1_native_runtime_v0.py'),
           'observer.py':read_regular(package/'tools/paradox_w1_native_observer_v0.py')}
    if row is not None:
        files.update({'case.json':canonical(O.input_case(row)),'candidate.py':row['candidate_source'].encode('utf-8'),
                      'profile.json':read_regular(package/'frozen/examples/paradox_preexecution_impact_v0/profile.json')})
    for name,raw in files.items():
        p=stage/name;p.write_bytes(raw);p.chmod(0o444)
    stage.chmod(0o555)
    return {name:digest(raw) for name,raw in files.items()}


def one_container(backend,package,req,row,cid_label,request_sha,case_dir,temp_root,runtime_lock=None):
    case_dir.mkdir(mode=0o700);stage=temp_root/cid_label
    hashes=stage_inputs(package,req,row,stage);cidfile=case_dir/'container.cid';cid=None;removed=False
    ready_rows=[];result=None
    try:
        out=backend.command(B.create_args(req['image_id'],stage,cidfile,request_sha,cid_label))
        cid=out.decode().strip();need(re.fullmatch('[0-9a-f]{64}',cid),'container_id')
        need(read_regular(cidfile,128).decode().strip()==cid,'cidfile_binding')
        before=backend.inspect(cid)
        B.check_inspect(before,req['image_id'],stage,request_sha,cid_label,cid)
        write_json(case_dir/'inspect_before.json',before)
        def ready(frame):
            B.validate_probe(frame,request_sha,cid_label)
            actual={k:frame[k] for k in ('runtime','python_sha256','kernel_release')}
            if runtime_lock is not None:
                need(not runtime_lock or runtime_lock==actual,'observed_runtime_drift')
                runtime_lock.update(actual)
            need(not ready_rows,'duplicate_readiness')
            current=backend.inspect(cid)
            B.check_inspect(current,req['image_id'],stage,request_sha,cid_label,cid,running=True)
            need({p.name:digest(read_regular(p)) for p in stage.iterdir()}==hashes,'staged_input_changed')
            write_json(case_dir/'inspect_running.json',current)
            write_json(case_dir/'readiness.json',frame);ready_rows.append(frame)
        result=backend.capture(cid,request_sha,cid_label,ready,case_dir/'stdout.jsonl',case_dir/'stderr.bin')
        write_json(case_dir/'transport.json',{k:v for k,v in result.items() if k not in ('stdout','stderr')})
        if result['termination']=='exited':
            final=backend.inspect(cid);write_json(case_dir/'inspect_terminal.json',final)
            need(final[0]['State']['Running'] is False and final[0]['State'].get('OOMKilled') is False
                 and final[0]['State'].get('ExitCode')==result['returncode'],'container_terminal_binding')
        need(len(ready_rows)==1 and result['execution_token_sent'] is True,'no_bound_readiness')
        if cid_label=='probe-time': need(result['termination']=='timeout','timeout_probe_failed')
        elif cid_label=='probe-output': need(result['termination']=='output_limit','output_probe_failed')
        else: need(result['termination']=='exited' and result['returncode']==0,'native_capture_incomplete')
    finally:
        cleanup_error=None
        try:
            if cid is None and cidfile.exists():
                candidate=read_regular(cidfile,128).decode().strip()
                if re.fullmatch('[0-9a-f]{64}',candidate): cid=candidate
            if cid is not None:
                info=backend.inspect(cid)
                need(info[0]['Id']==cid and info[0].get('Config',{}).get('Labels',{}).get('pulse.w1.request')==request_sha,'cleanup_subject')
                backend.command(['container','rm','--force',cid])
                remaining=backend.command(['container','ls','--all','--no-trunc','--format','{{.ID}}']).decode().splitlines()
                need(cid not in remaining,'container_cleanup_failed');removed=True
        except BaseException as exc:
            cleanup_error=type(exc).__name__+':'+str(exc)
        finally:
            write_json(case_dir/'cleanup.json',{'container_id':cid,'removed_and_absence_checked':removed,
                       'scratch_disposal':'container_tmpfs_removed' if removed else 'NOT_ESTABLISHED','error':cleanup_error})
            stage.chmod(0o755)
        if cleanup_error is not None: raise O.CaptureError('cleanup_failed:'+cleanup_error)
    return result,ready_rows[0]


def execute(package,expected_sha,authorization):
    # This check occurs before Docker construction, capture creation, or any process.
    need(authorization=='I_AUTHORIZE_PD_SM_02_W1:'+expected_sha,'owner_authorization_required')
    req,selection,C,receipt=validate_package(package,expected_sha)
    need(sys.platform=='linux','linux_controller_required')
    need(not (package/'CLAIM.json').exists() and not (package/'capture').exists(),'request_already_claimed')
    write_json(package/'CLAIM.json',{'request_sha256':expected_sha,'run_id':req['run_id'],'attempt':1,
                                   'owner_command_acknowledged':True,'automatic_retry':False})
    capture=package/'capture';capture.mkdir(mode=0o700)
    runtime_manifest={'image_id':req['image_id'],'declared_profile':req['runtime']}
    identities={'harness_sha256':req['sources']['paradox_w1_native_runtime_v0.py'],
                'observer_sha256':req['sources']['paradox_w1_native_observer_v0.py'],
                'containment_config_sha256':req['policy_sha256'],
                'runtime_manifest_sha256':digest(canonical(runtime_manifest)), 'run_request_sha256':expected_sha}
    record=O.observation(selection,req['run_id'],identities)
    summary={'status':'STOPPED_WITH_EVIDENCE','request_sha256':expected_sha,'authority_effect':'none',
             'owner_command_acknowledged':True,'native_witness_observed':None,'containment_observed':None,
             'acquisition_authenticity':'PROJECT_LOCAL_UNATTESTED','candidate_tokens_sent':0,
             'completed_case_records':0,'supervision_controls_completed':[], 'reason':None}
    try:
        write_json(capture/'input_receipt.json',receipt);write_json(capture/'runtime_manifest.json',runtime_manifest)
        with tempfile.TemporaryDirectory(prefix='pulse-w1-',dir='/tmp') as tmp:
            root=Path(tmp);root.chmod(0o755)
            backend=B.Docker(root/'docker-config',capture/'docker_commands')
            runtime_lock={}
            info=json.loads(backend.command(['info','--format','{{json .}}'],projection=B.project_info))
            need(info.get('OSType')=='linux' and str(info.get('CgroupVersion'))=='2','docker_cgroup_v2_required')
            write_json(capture/'docker_info.json',info)
            img=json.loads(backend.command(['image','inspect',req['image_id']],projection=B.project_image))
            B.check_image(img,req['image_id']);write_json(capture/'image_inspect.json',img)
            # These are two benign supervision controls, not extra candidate invocations.
            for control in ('probe-time','probe-output'):
                one_container(backend,package,req,None,control,expected_sha,capture/control,root,runtime_lock)
                summary['supervision_controls_completed'].append(control)
            for i,row in enumerate(selection['cases']):
                case_dir=capture/row['case_id']
                result,ready=one_container(backend,package,req,row,row['case_id'],expected_sha,case_dir,root,runtime_lock)
                summary['candidate_tokens_sent']+=int(result['execution_token_sent'])
                frames=O.parse_frames(result['stdout'])
                need(frames and frames[0]==ready,'readiness_transcript_binding')
                case=O.assemble_case(frames[1:],row,req['run_id']);record['cases'][i]=case
                report=C.check_observations(canonical(record),selection)
                write_json(case_dir/'record_check.json',report)
                cr=report['case_reports'][i]
                need(cr['status']=='RECORD_COMPLETE' and cr['record_prediction_match'] is True,'case_prediction_or_observation_failure')
                summary['completed_case_records']+=1
            summary['status']='CAPTURE_COMPLETED_UNATTESTED'
    except BaseException as exc:
        summary['reason']=type(exc).__name__+':'+str(exc)
        # A GO token is not proof of invocation; retain the transport counts even if
        # observation assembly failed. Never fill a missing case from its prediction.
        for d in capture.iterdir():
            if d.is_dir() and d.name in O.ORDER and (d/'transport.json').exists():
                tr=O.strict(read_regular(d/'transport.json'))
                idx=list(O.ORDER).index(d.name)
                if record['cases'][idx]['status']=='NOT_RUN' and tr.get('execution_token_sent') is True:
                    record['cases'][idx].update(status='INCOMPLETE')
        summary['candidate_tokens_sent']=sum(O.strict(read_regular(capture/c/'transport.json')).get('execution_token_sent') is True
                    for c in O.ORDER if (capture/c/'transport.json').exists())
    finally:
        write_json(capture/'observations.json',record)
        try: report=C.check_observations(canonical(record),selection)
        except BaseException as exc: report={'status':'INVALID_RECORD_OR_INPUT','reason':str(exc),'authority_effect':'none'}
        write_json(capture/'record_check.json',report)
        summary['completed_case_records']=report.get('complete_case_records',0)
        write_json(capture/'summary.json',summary);close_manifest(capture)
    return summary


def verify_capture(package,expected_sha):
    req,selection,C,receipt=validate_package(package,expected_sha)
    cap=package/'capture';manifest=O.strict(read_regular(cap/'MANIFEST.json'))
    O.keys(manifest,{'schema_version','files','authority_effect'},'manifest_shape')
    need(manifest['schema_version']=='pd_sm_02_w1_capture_manifest_v0' and manifest['authority_effect']=='none','manifest_role')
    paths={p.relative_to(cap).as_posix() for p in cap.rglob('*') if p.is_file() and p.relative_to(cap).as_posix()!='MANIFEST.json'}
    need(paths==set(manifest['files']),'capture_inventory')
    for name,entry in manifest['files'].items():
        p=Path(name);need(not p.is_absolute() and '..' not in p.parts,'capture_path')
        raw=read_regular(cap/p,8*1024*1024)
        need(entry=={'bytes':len(raw),'sha256':digest(raw)},'capture_member_binding')
    raw=read_regular(cap/'observations.json');record=O.strict(raw)
    runtime_manifest={'image_id':req['image_id'],'declared_profile':req['runtime']}
    expected_identities={'harness_sha256':req['sources']['paradox_w1_native_runtime_v0.py'],
        'observer_sha256':req['sources']['paradox_w1_native_observer_v0.py'],
        'containment_config_sha256':req['policy_sha256'],
        'runtime_manifest_sha256':digest(canonical(runtime_manifest)),'run_request_sha256':expected_sha}
    need(record['run_id']==req['run_id'] and record['identities']==expected_identities,'capture_run_binding')
    need(O.strict(read_regular(cap/'runtime_manifest.json'))==runtime_manifest,'capture_runtime_manifest')
    summary=O.strict(read_regular(cap/'summary.json'))
    need(summary['request_sha256']==expected_sha and summary['authority_effect']=='none'
         and summary['native_witness_observed'] is None and summary['containment_observed'] is None,'capture_claim_boundary')
    runtime_lock={}
    def replay_boundary(label):
        d=cap/label;cid=read_regular(d/'container.cid',128).decode().strip()
        need(re.fullmatch('[0-9a-f]{64}',cid),'capture_container_id')
        before=O.strict(read_regular(d/'inspect_before.json'))
        mounts=[m for m in before[0]['Mounts'] if m.get('Type')=='bind']
        need(len(mounts)==1,'capture_mount_inventory');stage=Path(mounts[0]['Source'])
        B.check_inspect(before,req['image_id'],stage,expected_sha,label,cid)
        running=O.strict(read_regular(d/'inspect_running.json'))
        B.check_inspect(running,req['image_id'],stage,expected_sha,label,cid,running=True)
        ready=O.strict(read_regular(d/'readiness.json'));B.validate_probe(ready,expected_sha,label)
        actual={k:ready[k] for k in ('runtime','python_sha256','kernel_release')}
        need(not runtime_lock or runtime_lock==actual,'capture_runtime_drift');runtime_lock.update(actual)
        cleanup=O.strict(read_regular(d/'cleanup.json'))
        need(cleanup=={'container_id':cid,'removed_and_absence_checked':True,
                       'scratch_disposal':'container_tmpfs_removed','error':None},'capture_cleanup')
        transport=O.strict(read_regular(d/'transport.json'))
        need(transport['execution_token_sent'] is True,'capture_token_not_sent')
        if label.startswith('probe-'):
            expected='timeout' if label=='probe-time' else 'output_limit'
            need(transport['termination']==expected,'capture_supervision_control')
        else:
            need(transport['termination']=='exited' and transport['returncode']==0,'capture_transport')
            terminal=O.strict(read_regular(d/'inspect_terminal.json'))
            need(terminal[0]['Id']==cid and terminal[0]['Image']==req['image_id'] and
                 terminal[0]['State']['Running'] is False and terminal[0]['State']['OOMKilled'] is False
                 and terminal[0]['State']['ExitCode']==0,'capture_container_terminal')
        frames=O.parse_frames(read_regular(d/'stdout.jsonl'))
        need(frames and frames[0]==ready,'capture_readiness_binding')
        return frames
    if any(c['status']=='COMPLETE' for c in record['cases']):
        need(summary['supervision_controls_completed']==['probe-time','probe-output'],'capture_missing_controls')
        B.check_image(O.strict(read_regular(cap/'image_inspect.json')),req['image_id'])
        info=O.strict(read_regular(cap/'docker_info.json'))
        need(info.get('OSType')=='linux' and str(info.get('CgroupVersion'))=='2','capture_daemon_profile')
        replay_boundary('probe-time');replay_boundary('probe-output')
    for case,row in zip(record['cases'],selection['cases']):
        if case['status']=='COMPLETE':
            frames=replay_boundary(row['case_id'])
            need(O.assemble_case(frames[1:],row,req['run_id'])==case,'capture_reconstruction')
    report=C.check_observations(canonical(record),selection)
    need(report==O.strict(read_regular(cap/'record_check.json')),'checker_replay_mismatch')
    need(summary['completed_case_records']==report['complete_case_records'],'capture_record_count')
    if summary['status']=='CAPTURE_COMPLETED_UNATTESTED':
        need(report['status']=='RECORDS_CONSISTENT' and summary['candidate_tokens_sent']==5,'capture_completion_claim')
    return {'status':'CAPTURE_RECORDS_REPLAYED','record_status':report['status'],'request_sha256':expected_sha,
            'manifest_members':len(paths),'acquisition_authenticity':'NOT_EXTERNALLY_VERIFIED',
            'native_witness_observed':None,'containment_observed':None,'execution_authorized':False,
            'new_candidate_executions':0,'authority_effect':'none'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--repo-root',type=Path,default=HERE.parent)
    a.add_argument('--output',type=Path,required=True);a.add_argument('--image-id',required=True);a.add_argument('--run-id',required=True)
    for verb in ('verify','execute'):
        a=sub.add_parser(verb);a.add_argument('--package',type=Path,required=True);a.add_argument('--request-sha256',required=True)
        if verb=='execute': a.add_argument('--authorize',required=True)
    a=sub.add_parser('verify-capture');a.add_argument('--package',type=Path,required=True);a.add_argument('--request-sha256',required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='prepare': result=prepare(args.repo_root,args.output,args.image_id,args.run_id)
        elif args.command=='execute': result=execute(args.package,args.request_sha256,args.authorize)
        elif args.command=='verify-capture': result=verify_capture(args.package,args.request_sha256)
        else:
            validate_package(args.package,args.request_sha256)
            result={'status':'REQUEST_VALID_NOT_AUTHORIZED','new_candidate_executions':0,'execution_authorized':False,'authority_effect':'none'}
        print(canonical(result).decode());return 0 if result.get('status')!='STOPPED_WITH_EVIDENCE' else 2
    except (O.CaptureError,B.BoundaryError,ValueError,TypeError,KeyError,OSError,StopIteration) as exc:
        print(canonical({'status':'BLOCKED','reason':type(exc).__name__+':'+str(exc),'execution_authorized':False,
                         'native_witness_observed':None,'authority_effect':'none'}).decode());return 1

if __name__=='__main__':
    raise SystemExit(main())
