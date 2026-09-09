#!/usr/bin/env python3
"""Prepare exact, non-active inputs for the bounded execution reference.

Preparation is outside the six observed subject processes. It reuses the
existing policy helper and integration planner; their raw input/source bytes
and ordered output are preserved for independent checking.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
import check_pulsemech_compute_bounded_execution_v0 as verify


def _run(command: list[str], *, cwd: Path, input_bytes: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(command,cwd=cwd,input=input_bytes,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=30,check=False,
            env={'PATH':'/usr/bin:/bin','LC_ALL':'C.UTF-8','TZ':'UTC',
                 'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
                 'GIT_NO_REPLACE_OBJECTS':'1','HOME':str(cwd)})
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise verify.EvidenceError('preparation_helper_unavailable') from exc
    verify.need(result.returncode == 0 and len(result.stdout) <= verify.MEMBER_LIMIT,
                'preparation_helper_failed')
    return result.stdout


def _planner_documents(context: dict) -> tuple[dict,dict]:
    request = {'schema_version':'pulsemech_integration_request_v0',
               'request_type':'pulsemech_integration_request',
               'request_id':'bounded_reference_'+verify.sha(verify.canonical(context)),
               'target_repository':{'repository_id':context['repository'],
                                    'default_branch':'main','ci_provider':'github_actions'},
               'component_sets':['bounded_reference_v0'],'write_mode':'plan_only',
               'existing_file_policy':{'identical':'preserve','different':'conflict',
                                        'symlink':'conflict','non_regular':'conflict'}}
    components = {'schema_version':'pulsemech_integration_component_manifest_v0',
                  'manifest_type':'pulsemech_integration_component_manifest',
                  'source_repository':verify.REPOSITORY,'policy_path':verify.POLICY,
                  'components':[{'id':role,'kind':'file','source_path':path,
                                  'target_path':'reference/'+role+'.py','requires':[]}
                                 for role,path in [('checker',verify.CHECKER),('consumer',verify.CONSUMER)]],
                  'component_sets':[{'id':'bounded_reference_v0',
                                     'description':'Plan-only controlled checker and state-consumer reference.',
                                     'root_components':['checker','consumer'],
                                     'declared_gate_sets':['core_required'],
                                     'supported_ci_providers':['github_actions'],
                                     'authority_boundary':'Reference only; authority_effect = none.'}]}
    return request,components


def prepare(*, repository_root: Path, context: dict, created_at_utc: str | None = None) -> bytes:
    root = Path(repository_root).absolute()
    verify.check_context(context,context)
    source_bytes = verify.git_source_inventory(root,context['source_commit'],tuple(verify.SOURCE_PATHS))
    for path in verify.SOURCE_PATHS:
        verify.need(verify.read_regular(root/path,verify.MEMBER_LIMIT) == source_bytes[path],
                    'preparation_uncommitted_source:'+path)
    verify.need(Path(__file__).absolute() == root/verify.ADAPTER,'adapter_entrypoint_path_mismatch')
    members = {'sources/'+path:raw for path,raw in source_bytes.items()}
    request,components = _planner_documents(context)
    with tempfile.TemporaryDirectory(prefix='pulse-bounded-prelaunch-') as temp:
        temp = Path(temp)
        source,target = temp/'source',temp/'target'
        source.mkdir(); target.mkdir()
        for path,raw in source_bytes.items():
            destination = source/path
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(raw)
        # Import the actual commit object, not a fabricated commit claiming its
        # identity. The planner only needs HEAD and this verified sparse view.
        raw_commit = _run(['/usr/bin/git','--no-replace-objects','-C',str(root),
                           'cat-file','commit',context['source_commit']],cwd=temp)
        _run(['/usr/bin/git','init','--quiet',str(source)],cwd=temp)
        imported = _run(['/usr/bin/git','-C',str(source),'hash-object','-w','-t','commit','--stdin'],
                        cwd=temp,input_bytes=raw_commit).decode().strip()
        verify.need(imported == context['source_commit'],'planner_source_commit_mismatch')
        (source/'.git/HEAD').write_text('ref: refs/heads/reference\n')
        (source/'.git/refs/heads/reference').write_text(imported+'\n')
        (source/'request.json').write_bytes(verify.canonical(request))
        (source/'components.json').write_bytes(verify.canonical(components))
        required_raw = _run([sys.executable,'-I','-S','-B',str(source/verify.POLICY_HELPER),
                            '--policy',str(source/verify.POLICY),'--set','core_required',
                            '--format','newline'],cwd=temp)
        required = verify.required_from_sources(source_bytes[verify.POLICY],source_bytes[verify.REGISTRY])
        verify.need(required_raw == ('\n'.join(required)+'\n').encode(), 'helper_policy_order_mismatch')
        members['inputs/required.newline'] = required_raw
        plan_raw = _run([sys.executable,'-I','-B',str(source/verify.PLANNER),
                        '--source-root',str(source),'--target-root',str(target),
                        '--request',str(source/'request.json'),
                        '--request-schema',str(source/verify.REQUEST_SCHEMA),
                        '--component-manifest',str(source/'components.json'),
                        '--component-manifest-schema',str(source/verify.COMPONENT_SCHEMA),
                        '--plan-schema',str(source/verify.PLAN_SCHEMA)],cwd=temp)
        plan = verify.parse(plan_raw)
        verify.need(plan['source']['revision'] == context['source_commit'],'planner_revision_mismatch')
        verify.need(not any(target.iterdir()),'planner_modified_target')
        for path,raw in source_bytes.items():
            verify.need((source/path).read_bytes()==raw,'planner_modified_input')
    members['planner/request.json'] = verify.canonical(request)
    members['planner/components.json'] = verify.canonical(components)
    members['planner/plan.json'] = verify.canonical(plan)
    for case,code in zip(verify.CASES,(0,1,2)):
        gates = {key:True for key in required}
        if code == 1:
            gates[required[0]] = False
        elif code == 2:
            del gates[required[0]]
        members[f'inputs/{case}/status.json'] = verify.canonical({'gates':gates})
        members[f'inputs/{case}/pending.json'] = verify.canonical({
            'schema_version':verify.VERSION,'record_type':'pending_state',
            'context_sha256':verify.sha(verify.canonical(context)),'case_id':case,
            'state':'pending','authority_effect':'none'})
    created = created_at_utc or dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    spec = {'schema_version':verify.VERSION,'record_type':'prelaunch','context':dict(context),
            'created_at_utc':created,'source_bindings':[{'path':p,'revision':context['source_commit'],
                **verify.descriptor('sources/'+p,raw)} for p,raw in sorted(source_bytes.items())],
            'required_gate_ids':required,'selected_policy_set':'core_required',
            'input_inventory':[verify.descriptor(p,b) for p,b in sorted(members.items()) if not p.startswith('sources/')],
            'cases':[verify.expected_case(context,c,k,members) for c,k in zip(verify.CASES,(0,1,2))],
            'planner':{key:verify.descriptor(name,members[name]) for key,name in (
                ('request','planner/request.json'),('component_manifest','planner/components.json'),
                ('plan','planner/plan.json'))},'boundary':dict(verify.BOUNDARY)}
    members['prelaunch.json'] = verify.canonical(spec)
    verify.verify_prelaunch(members,repository_root=root,expected_context=context)
    return verify.pack(members)


def build_subject_input(*, carrier_bytes: bytes, repository_root: Path,
                        expected_context: dict, expected_prelaunch_sha256: str) -> bytes:
    """Delegate construction to the existing core and check the new profile."""
    import types
    revision=expected_context['source_commit']
    root=repository_root.absolute()
    def load(relative):
        raw=verify.git_blob(root,revision,relative)
        verify.need(verify.read_regular(root/relative,verify.MEMBER_LIMIT)==raw,
                    'bounded_dependency_uncommitted:'+relative)
        name='_pulse_bounded_input_dependency_'+verify.sha(raw)
        mod=types.ModuleType(name);mod.__file__=str(root/relative)
        sys.modules[name]=mod
        exec(compile(raw,mod.__file__,'exec'),mod.__dict__)
        return mod
    core=load('tools/pulsemech_compute_subject_input_packet_producer_core_v0.py')
    packet=core.build_bounded_reference_packet(carrier_bytes=carrier_bytes,repository_root=root,
        expected_context=expected_context,expected_prelaunch_sha256=expected_prelaunch_sha256)
    raw=verify.canonical(packet)
    packet_validator=load('tools/check_pulsemech_compute_subject_input_packet_v0.py')
    schema=verify.parse(verify.git_blob(root,revision,
        'schemas/pulsemech_compute_subject_input_packet_v0.schema.json'),canonical_required=False)
    verify.need(not packet_validator.schema_errors(schema,packet),'bounded_subject_schema_rejected')
    checks,errors=packet_validator.check_bounded_reference_packet(packet,packet_text=raw.decode(),
        carrier_bytes=carrier_bytes,repository_root=root,expected_context=expected_context,
        expected_prelaunch_sha256=expected_prelaunch_sha256)
    verify.need(all(checks.values()) and not errors,'bounded_subject_semantic_rejected')
    return raw



def reconstruction_inputs(*, carrier_bytes: bytes, repository_root: Path,
                          expected_context: dict, expected_prelaunch_sha256: str,
                          analysis_run_key: str) -> dict[str, bytes]:
    """Reconstruct through the existing cores and separate validators.

    All values depend only on the preserved capture, expected context and
    source identity. This function never re-executes the observed subject.
    """
    root=repository_root.absolute(); revision=expected_context['source_commit']
    checked=verify.verify_capture(carrier_bytes,repository_root=root,expected_context=expected_context,
                                  expected_prelaunch_sha256=expected_prelaunch_sha256)
    verify.need(verify.read_regular(root/verify.ADAPTER)==verify.git_blob(root,revision,verify.ADAPTER),
                'adapter_reconstruction_source_mismatch')
    def load(path):
        return verify.load_reconstruction_module(path,repository_root=root,revision=revision)
    bridge=load('tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py')
    core=load('tools/pulsemech_compute_binding_analyzer_core_v0.py')
    report_check=load('tools/check_pulsemech_compute_binding_report_v0.py')
    relation_build=load('tools/build_pulsemech_compute_planned_observed_relation_v0.py')
    relation_check=load('tools/check_pulsemech_compute_planned_observed_relation_v0.py')
    materializer=load('tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py')
    subject=build_subject_input(carrier_bytes=carrier_bytes,repository_root=root,expected_context=expected_context,
        expected_prelaunch_sha256=expected_prelaunch_sha256)
    runtime=core.build_bounded_runtime_packet(carrier_bytes=carrier_bytes,repository_root=root,
        expected_context=expected_context,expected_prelaunch_sha256=expected_prelaunch_sha256)
    def captured(raw: bytes, label: str):
        return bridge.CapturedFile(path=Path(label),data=raw,device=0,inode=0,size_bytes=len(raw),sha256=verify.sha(raw))
    common=dict(packet_capture=captured(subject,'subject.json'),carrier_capture=captured(carrier_bytes,'capture.zip'),
        repository_root=root,analysis_run_key=analysis_run_key,bounded_expected_context=expected_context,
        bounded_prelaunch_sha256=expected_prelaunch_sha256)
    baseline=bridge.build_from_captured_inputs(**common).encode()
    runtime_report=bridge.build_from_captured_inputs(**common,runtime_packet_captures=[captured(runtime,'runtime.json')]).encode()
    document=verify.parse(runtime_report)
    verify.need(document['bounded_binding']['baseline_sha256']==verify.sha(baseline),'baseline_projection_identity_mismatch')
    report_inputs=dict(subject_input_bytes=subject,carrier_bytes=carrier_bytes,repository_root=root,
        expected_context=expected_context,expected_prelaunch_sha256=expected_prelaunch_sha256,runtime_packet_bytes=runtime)
    schema_raw=verify.git_blob(root,revision,'schemas/pulsemech_compute_binding_report_v0.schema.json')
    rd,rc=report_check.build_diagnostic(report_check.RuntimeBytesView(schema_raw),report_check.RuntimeBytesView(runtime_report),bounded_inputs=report_inputs)
    verify.need(rc==0,'bounded_report_pipeline_rejected:'+str(rd.get('errors')))
    planraw=checked.members['planner/plan.json'];plan=verify.parse(planraw)
    expectations=relation_build.bounded_expectations_from_prelaunch(checked.prelaunch,
        prelaunch_bytes=checked.members['prelaunch.json'],plan=plan,plan_bytes=planraw)
    er=verify.canonical(expectations)
    relation=relation_build.build_relation_record(plan=plan,plan_bytes=planraw,plan_path_or_uri='sha256:'+verify.sha(planraw),
        report=document,report_bytes=runtime_report,report_path_or_uri='sha256:'+verify.sha(runtime_report),
        packets=[(verify.parse(runtime),runtime,'sha256:'+verify.sha(runtime))],explicit_expectations=expectations,
        relation_id='planned-observed:bounded:'+verify.sha(carrier_bytes),tool_source_revision=revision,
        expectations_bytes=er,bounded_inputs=report_inputs)
    relationraw=verify.canonical(relation)
    relation_inputs={'report_inputs':report_inputs,'report_bytes':runtime_report,'plan_bytes':planraw,'expectations_bytes':er}
    rs=verify.git_blob(root,revision,'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json')
    diag,rc=relation_check.build_diagnostic(schema_path=relation_check.RuntimeBytesView(rs),
        relation_path=relation_check.RuntimeBytesView(relationraw),bounded_inputs=relation_inputs)
    verify.need(rc==0,'bounded_relation_pipeline_rejected:'+str(diag.get('errors')))
    base=verify.canonical({'gates':{}})
    with tempfile.TemporaryDirectory(prefix='pulse-bounded-candidate-') as directory:
        directory=Path(directory)
        (directory/'base_candidate.json').write_bytes(base);(directory/'relation.json').write_bytes(relationraw)
        md,rc=materializer.build_and_write_folded_status(status_path=directory/'base_candidate.json',
            relation_path=directory/'relation.json',schema_path=root/'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json',
            validator_path=root/'tools/check_pulsemech_compute_planned_observed_relation_v0.py',
            output_path=directory/'candidate.json',bounded_inputs=relation_inputs)
        verify.need(rc==0,'bounded_candidate_pipeline_rejected:'+str(md.get('errors')))
        candidate=verify.read_regular(directory/'candidate.json')
    return {'subject.json':subject,'runtime.json':runtime,'baseline.json':baseline,
            'runtime_report.json':runtime_report,'report_diagnostic.json':verify.canonical(rd),
            'plan.json':planraw,'expectations.json':er,'relation.json':relationraw,
            'relation_diagnostic.json':verify.canonical(diag),'base_candidate.json':base,
            'candidate.json':candidate,'materialization.json':verify.canonical(md)}


def workflow_context(*, repository_root: Path, environ: dict[str, str] | None=None) -> dict:
    """Bind the manual reference to the actual triggering GitHub workflow.

    Environment assertions are control-plane inputs inside the stated runner
    trust boundary, not cryptographic attestations produced by this function.
    """
    env=dict(os.environ if environ is None else environ)
    root=repository_root.absolute()
    verify.need(env.get('GITHUB_ACTIONS')=='true' and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch',
                'manual_github_reference_required')
    verify.need(env.get('GITHUB_REPOSITORY')==verify.REPOSITORY and env.get('GITHUB_REF')=='refs/heads/main',
                'reference_repository_or_ref_mismatch')
    verify.need(Path(env.get('GITHUB_WORKSPACE','/')).absolute()==root,'reference_workspace_mismatch')
    expected=env.get('EXPECTED_SOURCE_COMMIT','')
    import re
    verify.need(bool(re.fullmatch('[0-9a-f]{40}',expected)),'reference_expected_commit_required')
    verify.need(env.get('GITHUB_SHA')==expected==env.get('CONTROL_PLANE_REVISION'),
                'reference_trigger_source_mismatch')
    verify.need(env.get('CONTROL_PLANE_WORKFLOW_REF')==verify.REPOSITORY+'/'+verify.WORKFLOW+'@refs/heads/main',
                'reference_workflow_ref_mismatch')
    verify.need(env.get('GITHUB_WORKFLOW')=='PULSEmech bounded execution reference','reference_workflow_name_mismatch')
    numbers=[]
    for key in ('GITHUB_RUN_ID','GITHUB_RUN_NUMBER','GITHUB_RUN_ATTEMPT'):
        raw=env.get(key,'')
        verify.need(bool(re.fullmatch('[1-9][0-9]{0,18}',raw)),'reference_run_number_invalid:'+key)
        numbers.append(int(raw))
    head=_run(['/usr/bin/git','--no-replace-objects','-C',str(root),'rev-parse','HEAD'],cwd=root).decode().strip()
    verify.need(head==expected,'reference_checkout_mismatch')
    context={'record_status':'observed','repository':verify.REPOSITORY,
        'workflow_name':'PULSEmech bounded execution reference','workflow_path':verify.WORKFLOW,
        'run_id':numbers[0],'run_number':numbers[1],'run_attempt':numbers[2],
        'source_commit':expected,'event_name':'workflow_dispatch',
        'acquisition_id':f'github:{verify.REPOSITORY}:{numbers[0]}:{numbers[2]}'}
    verify.check_context(context,context)
    return context


def publish_reference_capsule(*,repository_root: Path,output_directory: Path,members: dict[str,bytes]) -> str:
    """Publish only an already reconstructed outer export; not an admission API."""
    root=repository_root.absolute();directory=output_directory.absolute()
    verify.need(not directory.is_relative_to(root) and not directory.exists() and not directory.is_symlink(),
                'reference_output_must_be_new_and_outside_sources')
    verify.need(set(members)=={'prepared.zip','capture.zip','expected_context.json','expected_prelaunch.sha256','reconstruction.zip'},
                'reference_capsule_inventory_invalid')
    payload=dict(members)
    payload['SHA256SUMS']=(''.join(verify.sha(b)+'  '+n+'\n' for n,b in sorted(payload.items()))).encode()
    packed=verify.pack(payload)
    # Create just the new leaf after all validation/reconstruction has finished.
    # No cleanup deletes a visible output or a competing replacement directory.
    directory.mkdir(mode=0o700,parents=False,exist_ok=False)
    verify.publish_new(directory/'reference_capsule_v0.zip',packed,repository_root=root)
    return verify.sha(packed)


def run_reference(*,repository_root: Path,output_directory: Path) -> str:
    """Owner-dispatched reference only; never called by ordinary PR tests."""
    root=repository_root.absolute(); context=workflow_context(repository_root=root)
    output_directory=output_directory.absolute()
    verify.need(not output_directory.is_relative_to(root) and not output_directory.exists(),
                'reference_output_must_be_new_and_outside_sources')
    # File publication checks every parent with no-follow descriptors. Avoid
    # accepting a pre-existing symlink before invoking the actual acquisition.
    parent=output_directory
    while parent!=parent.parent:
        verify.need(not parent.is_symlink(),'reference_output_parent_symlink');parent=parent.parent
    prepared=prepare(repository_root=root,context=context)
    members=verify.unpack(prepared);h=verify.sha(members['prelaunch.json'])
    builder=verify.load_reconstruction_module('tools/build_pulsemech_compute_planned_observed_relation_v0.py',
        repository_root=root,revision=context['source_commit'])
    prelaunch_expectations=verify.canonical(builder.bounded_expectations_from_prelaunch(verify.parse(members['prelaunch.json']),
        prelaunch_bytes=members['prelaunch.json'],plan=verify.parse(members['planner/plan.json']),plan_bytes=members['planner/plan.json']))
    with tempfile.TemporaryDirectory(prefix='pulse-bounded-reference-') as temp:
        temp=Path(temp);(temp/'prepared.zip').write_bytes(prepared);(temp/'context.json').write_bytes(verify.canonical(context))
        # This file is fixed before launching the subject. The later replay must
        # derive exactly these expectations from the same prelaunch contract.
        (temp/'expectations.json').write_bytes(prelaunch_expectations)
        capture_path=root/verify.CAPTURE
        verify.need(verify.read_regular(capture_path)==members['sources/'+verify.CAPTURE],'reference_capture_source_changed')
        result=subprocess.run([sys.executable,'-I','-B',str(capture_path),'--prepared',str(temp/'prepared.zip'),
            '--expected-context',str(temp/'context.json'),'--expected-prelaunch-sha256',h,
            '--repository-root',str(root),'--output',str(temp/'capture.zip')],cwd=temp,
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,check=False)
        verify.need(result.returncode==0,'reference_acquisition_failed')
        raw=verify.read_regular(temp/'capture.zip')
        verify.need(result.stdout.decode().strip()==verify.sha(raw),'reference_capture_stdout_mismatch')
        # Two separate Python processes reconstruct from the same preserved
        # acquisition. Neither command re-executes the checker or consumer.
        for n in (1,2):
            process=subprocess.run([sys.executable,'-I','-B',str(root/verify.ADAPTER),'reconstruct',
                '--repository-root',str(root),'--expected-context',str(temp/'context.json'),
                '--expected-prelaunch-sha256',h,'--carrier',str(temp/'capture.zip'),
                '--analysis-run-key','analysis:bounded:'+verify.sha(raw),'--output',str(temp/f'reconstruction{n}.zip')],
                cwd=temp,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=480,check=False)
            verify.need(process.returncode==0,'reference_reconstruction_failed:'+str(n))
        one=verify.read_regular(temp/'reconstruction1.zip');two=verify.read_regular(temp/'reconstruction2.zip')
        verify.need(one==two,'reference_reconstruction_not_identical')
        reconstructed=verify.unpack(one)
        verify.need(reconstructed['expectations.json']==prelaunch_expectations,'reference_expectations_changed')
        capsule={'capture.zip':raw,'prepared.zip':prepared,'expected_context.json':verify.canonical(context),
            'expected_prelaunch.sha256':(h+'\n').encode(),'reconstruction.zip':one}
        # The outer checksum manifest binds already finalized members and never
        # claims to authenticate itself or authorize a release.
        return publish_reference_capsule(repository_root=root,output_directory=output_directory,members=capsule)


def main(argv: list[str] | None = None) -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--repository-root',type=Path,required=True)
    prep.add_argument('--context',type=Path,required=True)
    prep.add_argument('--output',type=Path,required=True)
    subject=sub.add_parser('subject-input')
    subject.add_argument('--repository-root',type=Path,required=True)
    subject.add_argument('--expected-context',type=Path,required=True)
    subject.add_argument('--expected-prelaunch-sha256',required=True)
    subject.add_argument('--carrier',type=Path,required=True)
    subject.add_argument('--output',type=Path,required=True)
    runtime=sub.add_parser('runtime-packet')
    replay=sub.add_parser('reconstruct')
    for parser in (runtime,replay):
        parser.add_argument('--repository-root',type=Path,required=True)
        parser.add_argument('--expected-context',type=Path,required=True)
        parser.add_argument('--expected-prelaunch-sha256',required=True)
        parser.add_argument('--carrier',type=Path,required=True)
        parser.add_argument('--output',type=Path,required=True)
    replay.add_argument('--analysis-run-key',required=True)
    reference=sub.add_parser('run-reference')
    reference.add_argument('--repository-root',type=Path,required=True)
    reference.add_argument('--output-directory',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.command=='run-reference':
            print(run_reference(repository_root=args.repository_root,output_directory=args.output_directory))
            return 0
        if args.command=='prepare':
            context=verify.parse(verify.read_regular(args.context,verify.MEMBER_LIMIT))
            result=prepare(repository_root=args.repository_root,context=context)
            output_digest=verify.sha(verify.unpack(result)['prelaunch.json'])
        else:
            context=verify.parse(verify.read_regular(args.expected_context,verify.MEMBER_LIMIT))
            raw=verify.read_regular(args.carrier)
            common=dict(carrier_bytes=raw,repository_root=args.repository_root,expected_context=context,
                expected_prelaunch_sha256=args.expected_prelaunch_sha256)
            if args.command=='subject-input':
                result=build_subject_input(**common)
            elif args.command=='runtime-packet':
                core=verify.load_reconstruction_module('tools/pulsemech_compute_binding_analyzer_core_v0.py',
                    repository_root=args.repository_root,revision=context['source_commit'])
                result=core.build_bounded_runtime_packet(**common)
            else:
                result=verify.pack(reconstruction_inputs(**common,analysis_run_key=args.analysis_run_key))
            output_digest=verify.sha(result)
        verify.publish_new(args.output,result,repository_root=args.repository_root)
        print(output_digest)
        return 0
    except (verify.EvidenceError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        code=str(exc) if isinstance(exc,verify.EvidenceError) else type(exc).__name__
        print('bounded_input_rejected: '+code,file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
