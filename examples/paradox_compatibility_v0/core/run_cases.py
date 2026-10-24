"""Run only the frozen PD-SM-01-E0 cases in a new local output directory.
No repository writes, imports of production helpers, package installs or CI.
The Linux seccomp filter denies network socket creation in this process tree.
This is controlled test isolation, not a filesystem or PULSEbox sandbox.
"""
from __future__ import annotations

import argparse
import ast
import copy
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_reference as ref

PROGRAMS = {
    'field_producer': 'scripts/paradox_field_adapter_v0.py',
    'edge_exporter': 'scripts/export_paradox_edges_v0.py',
    'field_checker': 'scripts/check_paradox_field_v0_contract.py',
    'edge_checker': 'scripts/check_paradox_edges_v0_contract.py',
    'example_acceptance': 'scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py',
}
STAGES = ('field_checker','edge_checker','example_acceptance')
SCENARIOS = ('E00','E10','E11','E12','E13','E20','E30','E40')
CONTROLS = ('G01','G02','G03','G04','G05','G06')
STREAM_LIMIT = 2 * 1024 * 1024
WORKSPACE_LIMIT = 64 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()+b'\n')


def file_record(path):
    path = Path(path); raw = path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}


def network_filter():
    """Deny networking syscalls through the host libseccomp, without downloads.
    Architecture-specific syscall numbers are resolved by libseccomp, not guessed.
    Inherited by children. Failure is an explicit environment failure.
    """
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes=[ctypes.c_uint32]; lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]; lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    lib.seccomp_load.argtypes=[ctypes.c_void_p]; lib.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7fff0000)
    if not ctx: raise RuntimeError('NETWORK_ISOLATION_UNAVAILABLE: init')
    denied = []
    try:
        for name in ('socket','socketpair','connect','bind','listen','accept','accept4','sendto','sendmsg','sendmmsg','recvfrom','recvmsg','recvmmsg','shutdown'):
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr < 0 or lib.seccomp_rule_add(ctx,0x00050000 | errno.EPERM,nr,0) != 0:
                raise RuntimeError('NETWORK_ISOLATION_UNAVAILABLE: '+name)
            denied.append(name)
        if lib.seccomp_load(ctx) != 0:
            raise RuntimeError('NETWORK_ISOLATION_UNAVAILABLE: load')
    finally:
        lib.seccomp_release(ctx)
    # Test the effective restriction, without attempting any external connection.
    import socket
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.close()
    except PermissionError as exc:
        if exc.errno != errno.EPERM: raise
    else:
        raise RuntimeError('network filter probe unexpectedly succeeded')
    return {'mechanism':'libseccomp syscall filter','library':'libseccomp.so.2',
            'denied_syscalls':denied,'socket_probe':'EPERM','scope':'process tree',
            'filesystem_confinement':'not_enforced','security_sandbox_claim':False}


def child_limits():
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(STREAM_LIMIT,STREAM_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))


class ProcessRunner:
    def __init__(self, output):
        self.output = Path(output).resolve()
        self.work = self.output/'workspace'; self.work.mkdir(parents=True)
        (self.work/'home').mkdir(); (self.work/'tmp').mkdir()
        self.env={'PATH':'/usr/bin:/bin','HOME':str(self.work/'home'),
                  'TMPDIR':str(self.work/'tmp'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
        self.calls=[]

    def run(self, label, command, inputs=(), timeout=30.0):
        if timeout <= 0 or timeout > 30: raise ValueError('invalid timeout')
        target=self.output/'logs'/label
        target.parent.mkdir(parents=True,exist_ok=True)
        stdout=target.with_suffix('.stdout'); stderr=target.with_suffix('.stderr')
        if stdout.exists() or stderr.exists(): raise ValueError('duplicate invocation label')
        record={'label':label,'argv':[str(x) for x in command],'cwd':str(self.work),
                'environment':self.env,'input_files':[file_record(p) for p in inputs],
                'started_utc':datetime.now(timezone.utc).isoformat(),
                'timeout_seconds':timeout,'execution':'NOT_RUN','returncode':None,
                'normal_completion':False,'stdout':None,'stderr':None}
        if len(command)>3 and Path(command[3]).is_file():
            record['program']=file_record(command[3])
        start=time.monotonic(); state='COMPLETED'; proc=None
        with stdout.open('xb') as out, stderr.open('xb') as err:
            try:
                proc=subprocess.Popen([str(x) for x in command],cwd=self.work,env=self.env,
                                      stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                                      close_fds=True,start_new_session=True,preexec_fn=child_limits)
                while proc.poll() is None:
                    if time.monotonic()-start>timeout:
                        state='TIMEOUT'; os.killpg(proc.pid,signal.SIGKILL);break
                    if sum(p.stat().st_size for p in self.output.rglob('*') if p.is_file())>WORKSPACE_LIMIT:
                        state='WORKSPACE_LIMIT'; os.killpg(proc.pid,signal.SIGKILL);break
                    time.sleep(0.01)
                proc.wait(timeout=3)
                record['returncode']=proc.returncode
                if state=='COMPLETED' and proc.returncode<0: state='PROCESS_ERROR'
            except Exception as exc:
                state='PROCESS_ERROR'; record['runner_error']=type(exc).__name__+': '+str(exc)
                if proc and proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        record.update(execution=state,elapsed_seconds=time.monotonic()-start,
                      ended_utc=datetime.now(timezone.utc).isoformat(),
                      stdout=file_record(stdout),stderr=file_record(stderr))
        record['normal_completion']=state=='COMPLETED' and record['returncode'] is not None and record['returncode']>=0
        record['python_traceback']=b'Traceback (most recent call last)' in stderr.read_bytes()
        if record['python_traceback']: record['normal_completion']=False
        write_json(target.with_suffix('.json'),record);self.calls.append(record)
        return record


def checked_logs(observation):
    if not isinstance(observation,dict): return False
    for key in ('stdout','stderr'):
        item=observation.get(key)
        if not isinstance(item,dict): return False
        path=Path(item.get('path',''))
        if not path.is_file() or sha(path.read_bytes())!=item.get('sha256'): return False
    return True


def compare_program(expected, actual, witness=True):
    if not checked_logs(actual): return 'INCOMPLETE'
    if actual.get('execution')!='COMPLETED' or actual.get('normal_completion') is not True:
        return 'INCOMPLETE'
    rc=actual.get('returncode')
    if type(rc) is not int: return 'INCOMPLETE'
    fragment=expected.get('diagnostic_fragment')
    if expected.get('exit_code')=='nonzero':
        if rc<=0 or not witness: return 'MISMATCH'
        if not fragment or fragment not in Path(actual['stderr']['path']).read_text(errors='replace'):
            return 'MISMATCH'
    elif rc!=expected.get('exit_code'):
        return 'MISMATCH'
    return 'MATCH'


def compare_case(expected, observed):
    if not isinstance(observed,dict) or observed.get('coverage_status')!='COMPLETE_FOR_DECLARED_CASE':
        return 'INCOMPLETE',{'coverage':'INCOMPLETE'}
    if observed.get('mutation_manifest',{}).get('verified') is not True:
        return 'INCOMPLETE',{'mutation':'INCOMPLETE'}
    ref_file=observed.get('reference_result_file')
    if not isinstance(ref_file,dict) or not Path(ref_file.get('path','')).is_file():
        return 'INCOMPLETE',{'reference_result':'INCOMPLETE'}
    if sha(Path(ref_file['path']).read_bytes())!=ref_file.get('sha256'):
        return 'INCOMPLETE',{'reference_result':'DIGEST_MISMATCH'}
    programs=observed.get('program_observations',{})
    checks={k:compare_program(v,programs.get(k),observed['mutation_manifest'].get('witness_verified') is True)
            for k,v in expected['existing_programs'].items()}
    reference_stage=observed.get('reference_observation')
    checks['reference_process']=compare_program({'exit_code':0,'diagnostic_fragment':None},reference_stage)
    for k in ('reference_relation_assessment','reference_source_assessment',
              'proof_applicability_assessment','carrier_assessment','authority_effect'):
        checks[k]='INCOMPLETE' if k not in observed else 'MATCH' if observed[k]==expected[k] else 'MISMATCH'
    if observed.get('semantic_preservation_required'):
        checks['semantic_preservation']='MATCH' if observed.get('semantic_preserved') is True else 'MISMATCH'
    result='INCOMPLETE' if 'INCOMPLETE' in checks.values() else 'MISMATCH' if 'MISMATCH' in checks.values() else 'MATCH'
    return result,checks


def complete_summary(expectations, cases, controls):
    required=[x['scenario_id'] for x in expectations['scenarios']]
    if len(cases)!=len(required) or sorted(cases)!=sorted(required): return 'INCOMPLETE'
    if sorted(controls)!=sorted(CONTROLS): return 'INCOMPLETE'
    results=[]
    for row in expectations['scenarios']:
        result,_=compare_case(row['expected'],cases[row['scenario_id']]);results.append(result)
    for group in controls.values():
        evidence=group.get('evidence')
        evidence_ok=isinstance(evidence,dict) and Path(evidence.get('path','')).is_file()
        if evidence_ok: evidence_ok=sha(Path(evidence['path']).read_bytes())==evidence.get('sha256')
        if group.get('execution')!='COMPLETED' or not evidence_ok:
            return 'INCOMPLETE'
        results.append(group.get('result','INCOMPLETE'))
    return 'INCOMPLETE' if 'INCOMPLETE' in results else 'MISMATCH' if any(v!='MATCH' for v in results) else 'MATCH'


def verify_sources(bundle):
    manifest=ref.strict_json((bundle/'preparation/SOURCE_BINDINGS.json').read_bytes())
    if manifest['selected_snapshot']!=ref.SNAPSHOT: raise ValueError('wrong source snapshot')
    records=[]
    for row in manifest['files']:
        p=bundle/'source'/row['path']
        if p.is_symlink() or not p.is_file(): raise ValueError('missing or symlink source: '+row['path'])
        raw=p.read_bytes(); actual=ref.blob(raw)
        if actual!=row['expected_git_blob_sha1']: raise ValueError('SOURCE_MISMATCH: '+row['path'])
        records.append({'path':row['path'],'git_blob_sha1':actual,'sha256':sha(raw),'bytes':len(raw)})
    return records


def dump_field(value):
    return json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()


def dump_edges(value):
    return b''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()+b'\n' for x in value)


def make_envelope(field,edges,subject,evidence,certificate=None):
    result={'field':field,'edges':edges,'subject':subject,'evidence':evidence}
    if certificate is not None: result['presented_certificate']=certificate
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bundle-root',type=Path,default=HERE.parent)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); bundle=args.bundle_root.resolve(); output=args.output.resolve()
    if output.exists(): ap.error('output must be new; retain existing results')
    if platform.python_implementation()!='CPython' or platform.python_version()!='3.13.5' or platform.system()!='Linux':
        ap.error('ENVIRONMENT_UNAVAILABLE: this run profile requires CPython 3.13.5 Linux')
    sources_before=verify_sources(bundle)
    expectations=ref.strict_json((HERE/'case_expectations.json').read_bytes())
    original=(bundle/'preparation/case_expectations.json').read_bytes()
    revision=ref.strict_json((bundle/'ENVIRONMENT_PROFILE_REVISION.json').read_bytes())
    if (HERE/'case_expectations.json').read_bytes()!=original or sha(original)!=revision['historical_expectations_sha256']:
        ap.error('frozen expectations mismatch')
    if revision['change']['selected_value']!=platform.python_version(): ap.error('profile revision mismatch')
    if tuple(s['scenario_id'] for s in expectations['scenarios'])!=SCENARIOS: ap.error('scenario set changed')
    output.mkdir(parents=True); isolation=network_filter()
    environment={'profile_revision':revision,'actual_python':sys.version,'executable':str(Path(sys.executable).resolve()),
       'executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'platform':platform.platform(),
       'uname':list(platform.uname()),'os_release':Path('/etc/os-release').read_text(),
       'isolation':isolation,'credentials_forwarded':False,'third_party_python_packages_used':False,
       'package_installations':False,'repository_write':False,'ci_dispatched':False,'authority_effect':'none'}
    write_json(output/'environment.json',environment);write_json(output/'sources_before.json',sources_before)
    freeze={'expectations_sha256':sha(original),'source_snapshot':ref.SNAPSHOT,
            'files':{p.name:sha(p.read_bytes()) for p in sorted(HERE.iterdir()) if p.is_file()},
            'profile_revision_sha256':sha((bundle/'ENVIRONMENT_PROFILE_REVISION.json').read_bytes()),
            'frozen_before_producer_execution':True}
    write_json(output/'freeze.json',freeze)
    source_dir=bundle/'source/docs/examples/transitions_case_study_v0'
    evidence={n:(source_dir/n).read_bytes().decode('utf-8') for n in ref.INPUT_BLOBS}
    admitted,missing,invalid=ref.admitted_sources(evidence)
    if missing or invalid: raise ValueError('incomplete baseline evidence')
    reference_field,reference_edges,subjects=ref.reconstruct(admitted)
    write_json(output/'independent_reference_before_execution.json',
               {'field':reference_field,'edges':reference_edges,'subjects':subjects})
    runner=ProcessRunner(output)
    inputs=runner.work/'inputs';inputs.mkdir()
    for name in ref.INPUT_BLOBS: (inputs/name).write_bytes((source_dir/name).read_bytes());(inputs/name).chmod(0o444)
    base=runner.work/'out/base';base.mkdir(parents=True)
    field_path=base/'paradox_field_v0.json';edge_path=base/'paradox_edges_v0.jsonl'
    python=str(Path(sys.executable).resolve())
    cmd=lambda name,more:[python,'-I','-B',str(bundle/'source'/PROGRAMS[name]),*map(str,more)]
    producer=runner.run('construction/field',cmd('field_producer',['--transitions-dir','inputs','--out',field_path]),list(inputs.iterdir()))
    if producer['returncode']!=0: raise RuntimeError('baseline producer did not succeed')
    exporter=runner.run('construction/edges',cmd('edge_exporter',['--in',field_path,'--out',edge_path]),[field_path])
    if exporter['returncode']!=0: raise RuntimeError('baseline exporter did not succeed')
    field_raw=field_path.read_bytes();edge_raw=edge_path.read_bytes()
    baseline=ref.strict_json(field_raw);edge_base=[ref.strict_json(x) for x in edge_raw.splitlines() if x.strip()]
    ref.complete_lookup(baseline,edge_base)
    before_projection=ref.semantic_projection(baseline,edge_base)
    mismatches=ref.differences(ref.semantic_projection(reference_field,reference_edges),before_projection)
    write_json(output/'baseline_source_comparison.json',{'differences':mismatches,'matched':not mismatches,
            'source':'independent reference frozen before producer execution',
            'actual_atom_count':len(baseline['paradox_field_v0']['atoms']),'actual_edge_count':len(edge_base),
            'carrier_files':[file_record(field_path),file_record(edge_path)]})
    if mismatches: raise RuntimeError('BASELINE_SOURCE_MISMATCH; variants not executed')
    cases={};baseline_certificate=None
    for spec in expectations['scenarios']:
        sid=spec['scenario_id'];folder=runner.work/'cases'/sid;folder.mkdir(parents=True)
        field=copy.deepcopy(baseline);edges=copy.deepcopy(edge_base);ev=copy.deepcopy(evidence)
        subject=copy.deepcopy(subjects['cpu_util' if spec['selected_subject']=='cpu' else 'p99_latency'])
        selected_old=baseline_certificate if sid=='E40' else None
        kind=spec['mutation_contract']['kind']; details={'kind':kind,'semantic_changes':[],
                                                       'verified':False,'witness_verified':False}
        fbytes=field_raw;ebytes=edge_raw
        if sid=='E10':
            field['paradox_field_v0']['atoms'].reverse();edges.reverse()
        elif sid=='E11':
            field['paradox_field_v0']['atoms'].reverse();fbytes=dump_field(field)
            keys=[ref.order_key(x,'atom_id') for x in field['paradox_field_v0']['atoms']]
            if not any(a>b for a,b in zip(keys,keys[1:])): raise ValueError('missing field-order stimulus')
            details['descending_pairs']=[i for i,(a,b) in enumerate(zip(keys,keys[1:])) if a>b]
        elif sid=='E12':
            edges.reverse();ebytes=b''.join(reversed(edge_raw.splitlines(keepends=True)))
            keys=[ref.order_key(x,'edge_id') for x in edges]
            if not any(a>b for a,b in zip(keys,keys[1:])): raise ValueError('missing edge-order stimulus')
            details['descending_pairs']=[i for i,(a,b) in enumerate(zip(keys,keys[1:])) if a>b]
        elif sid=='E13':
            field=ref.strict_json((runner.work/'cases/E11/paradox_field_v0.json').read_bytes())
            edges=[ref.strict_json(x) for x in (runner.work/'cases/E12/paradox_edges_v0.jsonl').read_bytes().splitlines() if x.strip()]
            field['paradox_field_v0']['atoms'].sort(key=lambda x:ref.order_key(x,'atom_id'))
            edges.sort(key=lambda x:ref.order_key(x,'edge_id'))
            fbytes=dump_field(field);ebytes=dump_edges(edges)
            details['restored_from']=['E11','E12'];details['producer_rerun']=False
        elif sid=='E20':
            indexes=[i for i,e in enumerate(edges) if e['edge_id']==subject['edge_id']]
            if len(indexes)!=1: raise ValueError('ambiguous mutation target')
            edges[indexes[0]]['dst_atom_id']=subjects['cpu_util']['metric_atom_id'];ebytes=dump_edges(edges)
            changes=ref.differences(edge_base,edges);details['semantic_changes']=changes
            if len(changes)!=1 or changes[0]['path']!='/'+str(indexes[0])+'/dst_atom_id':
                raise ValueError('mutation is not one destination change')
        elif sid=='E30':
            del ev['pulse_metric_drift_v0.csv'];details['withheld']=['pulse_metric_drift_v0.csv']
            details['fresh_reference_subprocess']=True;details['previous_certificate_passed']=False
        elif sid=='E40':
            details['previous_subject']=subjects['p99_latency'];details['new_subject']=subject
            details['global_correspondence']={'replacement_declared':True,'old':subjects['p99_latency'],'new':subject}
        fp=folder/'paradox_field_v0.json';ep=folder/'paradox_edges_v0.jsonl'
        fp.write_bytes(fbytes);ep.write_bytes(ebytes)
        # All changes are independently inspected before interpreting any child result.
        if sid in ('E00','E10','E30','E40') and (fbytes!=field_raw or ebytes!=edge_raw):
            raise ValueError('unexpected carrier-byte mutation')
        if sid=='E20' and fbytes!=field_raw: raise ValueError('field mutated in endpoint-only case')
        details.update(verified=True,witness_verified=True,
                       field_byte_identity_to_baseline=fbytes==field_raw,
                       edge_byte_identity_to_baseline=ebytes==edge_raw,
                       parsed_field_changes=ref.differences(baseline,ref.strict_json(fbytes)),
                       parsed_edge_changes=ref.differences(edge_base,[ref.strict_json(x) for x in ebytes.splitlines() if x.strip()]))
        write_json(folder/'mutation_manifest.json',details)
        observations={}
        for stage in STAGES:
            argv=['--in',fp] if stage=='field_checker' else ['--in',ep,'--atoms',fp]
            observations[stage]=runner.run(sid+'/'+stage,cmd(stage,argv),[fp] if stage=='field_checker' else [ep,fp])
        env_path=folder/'reference_input.json';ref_path=folder/'reference_output.json'
        if sid=='E10':
            projection=ref.semantic_projection(field,edges)
            write_json(folder/'permuted_mathematical_view.json',{'field':field,'edges':edges,
                'semantic_equal_to_baseline':projection==before_projection})
            if projection!=before_projection: raise ValueError('semantic permutation changed the relation')
            # Carrier order and mathematical enumeration are distinct inputs.
            field=copy.deepcopy(baseline);edges=copy.deepcopy(edge_base)
        envelope=make_envelope(field,edges,subject,ev,selected_old);write_json(env_path,envelope)
        ro=runner.run(sid+'/reference',[python,'-I','-B',HERE/'independent_reference.py','--input',env_path,'--output',ref_path],[env_path])
        result=ref.strict_json(ref_path.read_bytes()) if ref_path.exists() and ro['returncode']==0 else {}
        if sid=='E00': baseline_certificate=result.get('certificate')
        observed={**result,'scenario_id':sid,'source_profile_identity':revision['profile_id'],
            'program_observations':observations,'reference_observation':ro,
            'reference_result_file':file_record(ref_path) if ref_path.exists() else None,
            'mutation_manifest':details,'carrier_digests':{'field':sha(fbytes),'edges':sha(ebytes)},
            'semantic_preservation_required':sid in ('E10','E11','E12','E13'),
            'semantic_preserved':result.get('semantic_projection_sha256')==ref.digest(before_projection),
            'authority_effect':'none'}
        match,checks=compare_case(spec['expected'],observed)
        observed['expected_vs_observed']=match;observed['comparison_details']=checks
        write_json(folder/'scenario_result.json',{'expected':spec['expected'],'observed':observed})
        cases[sid]=observed
        print(sid,match,result.get('reference_relation_assessment'),result.get('reference_source_assessment'),flush=True)
        if sid=='E00' and match!='MATCH': raise RuntimeError('baseline prerequisite failed')
    import test_harness
    context={'bundle':bundle,'output':output,'runner':runner,'baseline':baseline,'edges':edge_base,
             'subjects':subjects,'evidence':evidence,'cases':cases,'expectations':expectations,
             'python':python,'cmd':cmd,'certificate':baseline_certificate}
    controls,regressions=test_harness.run_controls(context)
    sources_after=verify_sources(bundle);write_json(output/'sources_after.json',sources_after)
    unchanged=sources_before==sources_after
    current={p.name:sha(p.read_bytes()) for p in sorted(HERE.iterdir()) if p.is_file()}
    frozen=current==freeze['files']
    summary=complete_summary(expectations,cases,controls)
    if not unchanged or not frozen or not regressions['successful']: summary='MISMATCH'
    report={'profile_id':revision['profile_id'],'selected_snapshot':ref.SNAPSHOT,
       'historical_semantic_snapshot':expectations['historical_semantic_snapshot'],
       'execution_status':'COMPLETED','experiment_comparison':summary,
       'scenario_results':{k:v['expected_vs_observed'] for k,v in cases.items()},
       'controls':controls,'regressions':regressions,'sources_unchanged':unchanged,
       'harness_and_expectations_unchanged_since_freeze':frozen,
       'program_invocations':len(runner.calls),'all_scenarios':cases,
       'observed_facts_are_local_fixture_results':True,'authority_effect':'none',
       'repository_write':False,'ci_dispatched':False,
       'limitations':['No physical monitoring/enforcement experiment.',
          'No general D2/D3/D4 closure, physical causality or time-emergence proof.',
          'Reference and producers share the pinned specification; not organizationally independent validation.',
          'Only CPython 3.13.5 Linux executed; no cross-version equivalence claim.',
          'Socket syscalls denied; filesystem access is controlled by design, not a proven sandbox.']}
    write_json(output/'RESULTS.json',report)
    print('OVERALL',summary,'controls',len(controls),'regression_tests',regressions['tests_run'],flush=True)
    return 0 if summary=='MATCH' else 1


if __name__=='__main__':
    raise SystemExit(main())
