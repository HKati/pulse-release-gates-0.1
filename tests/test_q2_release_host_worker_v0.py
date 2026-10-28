#!/usr/bin/env python3
"""Offline integration for Q2-2/Q2-3: no live model, host or GitHub calls.

The source worker CLI and capture exchange run as real local processes with
explicit toy model/tokenizer and kernel/timer/transport fixtures. Such fixtures
prove implementation behavior, never native provenance or model execution.
"""
from __future__ import annotations
import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import types
import zipfile

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'PULSE_safe_pack_v0/tools'
sys.path.insert(0, str(TOOLS))
import q2_release_host_worker_contract_v0 as C
import check_q2_release_host_worker_protocol_v0 as P
import check_q2_release_host_worker_v0 as K
import verify_q2_release_host_worker_v0 as S

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), m.__dict__)
    return m

F = module('q2_worker_synthetic_protocol_fixtures', ROOT / 'tests/test_q2_release_host_worker_protocol_v0.py')

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network in offline integration tests')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


class _FixtureModuleView:
    """Override a module reference in this test only, never the shared module."""
    def __init__(self, original, **overrides):
        self._original = original
        self.__dict__.update(overrides)

    def __getattr__(self, name):
        return getattr(self._original, name)


def synthetic_privileged_filesystem(monkeypatch, tmp_path):
    """Model root-only filesystem operations inside one disposable fixture.

    File bytes, held-descriptor IO, exclusive publication and actual removal
    remain real. Ownership and root's ability to write frozen directories are
    explicitly synthetic: directories retain owner write access for the test
    process. Files still receive their actual requested permission bits.
    Nothing is created in /var/lib; the native location and UID/GID requests
    are checked, recorded and mapped only into this test's temporary directory.
    Neither this helper nor its records establish native isolation/ownership.
    """
    base = tmp_path.absolute()
    real_os, real_tempfile = os, tempfile
    ownership, modes, allocated = [], [], []

    def local(path):
        path = Path(path).absolute()
        assert base in path.parents and '..' not in path.parts, 'fixture_path_scope'
        assert not any(p.is_symlink() for p in (path, *path.parents)), 'fixture_link'
        info = path.stat()
        assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'fixture_kind'
        return path, info

    def chown(path, uid, gid):
        path, info = local(path)
        assert type(uid) is int and type(gid) is int, 'fixture_owner_type'
        assert (uid, gid) in ((0, 0), (0, 65534), (65534, 65534)), 'fixture_owner_scope'
        ownership.append((path, uid, gid))
        if stat.S_ISDIR(info.st_mode):
            real_os.chmod(path, stat.S_IMODE(info.st_mode) | 0o700)

    def chmod(path, mode):
        path, info = local(path)
        assert type(mode) is int and mode in (0o440, 0o550, 0o700), 'fixture_mode_scope'
        modes.append((path, mode))
        real_os.chmod(path, mode | 0o700 if stat.S_ISDIR(info.st_mode) else mode)

    def mkdtemp(*, prefix, dir):
        assert dir == '/var/lib', 'fixture_native_parent'
        assert prefix in ('pulse-q2-worker-', 'pulse-q2-worker-bootstrap-'), 'fixture_native_prefix'
        result = Path(real_tempfile.mkdtemp(prefix=prefix, dir=base))
        # Drop a fixture parent's inherited setgid bit; retain the native 0700 contract.
        result.chmod(0o700)
        allocated.append(result)
        return str(result)

    view = _FixtureModuleView(real_os, chown=chown, chmod=chmod)
    monkeypatch.setattr(S, 'os', view)
    monkeypatch.setattr(S, 'tempfile', _FixtureModuleView(real_tempfile, mkdtemp=mkdtemp))
    if S.U is not None:
        monkeypatch.setattr(S.U, 'os', view)
    return types.SimpleNamespace(ownership=ownership, modes=modes, allocated=allocated)


def source_rows(root=ROOT, *, platform_contract=C.STRICT_PLATFORM):
    return [{'path': n, 'size_bytes': len((root / n).read_bytes()), 'sha256': C.digest((root / n).read_bytes())}
            for n in C.load_profile(root, platform_contract=platform_contract)['source_paths']]


def projection_sources(rows):
    return [{'path': r['path'], 'origin': 'source:' + r['path'], 'archive_mode': None,
        'kind': 'file', 'uid': 0, 'gid': 65534, 'mode': 0o440,
        'size_bytes': r['size_bytes'], 'sha256': r['sha256']} for r in rows]


def source_fixture(path, *, platform_contract=C.STRICT_PLATFORM):
    """Disposable Git fixture, never a project development commit or remote."""
    path.mkdir()
    for name in C.load_profile(ROOT, platform_contract=platform_contract)['source_paths']:
        dest = path / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(path), 'LANG': 'C', 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
           'GIT_AUTHOR_NAME': 'Synthetic fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
           'GIT_COMMITTER_NAME': 'Synthetic fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
    for cmd in (['init', '-q'], ['add', '.'], ['-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic source-binding fixture']):
        r = subprocess.run(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', *cmd], cwd=path, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        assert r.returncode == 0, r.stderr
    revision = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=path, env=env).decode().strip()
    assert subprocess.check_output(['/usr/bin/git', 'remote'], cwd=path, env=env) == b''
    return revision

@pytest.fixture(scope='module')
def git_source(tmp_path_factory):
    p = tmp_path_factory.mktemp('q2-local-source') / 'repo'
    return p, source_fixture(p)


def owner_environment(source, revision, tmp_path, *, platform_contract=C.STRICT_PLATFORM):
    request = C.encode(C.request_for(source, revision, platform_contract=platform_contract)).decode()
    event = tmp_path / 'event.json'
    event.write_bytes(C.encode({'ref': 'main', 'sender': {'login': 'HKati', 'id': 128643840, 'type': 'User'},
        'repository': {'full_name': C.REPOSITORY}, 'inputs': {'source_commit': revision,
        'native_request': request, 'native_request_sha256': C.digest(request.encode())}}))
    return {'GITHUB_REPOSITORY': C.REPOSITORY, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_WORKFLOW_SHA': revision, 'GITHUB_WORKFLOW': C.NAME,
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_WORKFLOW_REF': C.REPOSITORY + '/' + C.WORKFLOW + '@refs/heads/main',
        'GITHUB_ACTOR': 'HKati', 'GITHUB_TRIGGERING_ACTOR': 'HKati', 'GITHUB_ACTOR_ID': '128643840',
        'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux', 'RUNNER_ENVIRONMENT': 'github-hosted',
        'GITHUB_WORKSPACE': str(source), S.SOURCE: revision, 'GITHUB_SHA': revision,
        'GITHUB_JOB': 'verify_host', 'GITHUB_RUN_ID': '123456', 'GITHUB_EVENT_PATH': str(event),
        'RUNNER_TEMP': str(tmp_path), S.REQUEST: request, S.DIGEST: C.digest(request.encode()), S.TOKEN: 'synthetic-no-network-token'}


def rebind_trace(f, plan):
    """Only synthetic fixture construction; never rewrites an acquired run."""
    pre = f['pre']; pre['request_sha256'] = plan['request_sha256']; pre['observer_contract_sha256'] = plan['observer_contract_sha256']
    pre.update(phase_start_ns=plan['phase_start_ns'], phase_deadline_ns=plan['phase_deadline_ns'])
    identity0 = {'prelaunch_sha256': C.digest(C.encode(pre)), 'source_commit': pre['context']['source_commit'],
                 'run_id': pre['context']['run_id'], 'run_attempt': 1}
    f['ready']['binding'] = identity0
    f['subject'].update(prelaunch_sha256=identity0['prelaunch_sha256'], ready_sha256=C.digest(C.encode(f['ready'])))
    identity = {**identity0, 'subject_sha256': C.digest(C.encode(f['subject']))}
    f['terminal']['binding'] = identity; f['terminal']['session_end']['binding'] = identity
    f['life']['commands'][1]['command'] = 'BIND ' + identity['subject_sha256'] + '\n'
    f['life']['bound_frame_base64'] = base64.b64encode(C.encode({'record_type': 'q2_capture_bound_v0', 'binding': identity})).decode()
    for i, (raw_response, raw_ready) in enumerate(f['records']):
        response, ready = C.parse(raw_response), C.parse(raw_ready)
        response['binding'] = identity; ready['binding'] = identity
        f['records'][i] = C.encode(response), C.encode(ready)
        for kind, raw in zip(('response', 'ready'), f['records'][i]):
            f['terminal']['occurrences'][i][kind].update(size=len(raw), sha256=C.digest(raw))
    return f


def phase_fixture(name, prefix, begin, end, outputs):
    stage = 'captureworker' if name == 'worker' else ('reduction' if name == 'reduction_check' else 'capturecheck')
    obs = F.sandbox(); obs['stage'] = stage; obs['unit'] = 'pulse-q2-' + prefix * 24 + '-' + stage + '.service'
    if stage != 'captureworker':
        del obs['capture_runtime_seconds']; obs['properties']['RuntimeMaxUSec'] = '3min'
    cleanup = {'unit': obs['unit'], 'properties': {'LoadState': 'not-found', 'ActiveState': 'inactive', 'ControlGroup': ''},
               'cgroup_empty_or_removed': True, 'client_reaped': True}
    return {'id': name, 'isolation': obs, 'launch_ns': begin, 'isolation_observed_ns': begin+10,
        'exec_ns': begin+20, 'stdout_eof_ns': end-20, 'exit_observed_ns': end-10, 'exit_code': 0,
        'cleanup': cleanup, 'cleanup_ns': end, 'input_recheck': 'unchanged', 'outputs': outputs}


def carrier_fixture(tmp_path, unknown=False, plan_override=None, source=ROOT, *, platform_contract=C.STRICT_PLATFORM):
    """Original toy worker + actual frozen metric CLIs; all host records synthetic."""
    if plan_override is not None and plan_override.get('record_type') == 'q2_worker_execution_plan_v1':
        platform_contract = C.REVIEWED_PLATFORM
    p = C.load_profile(source, platform_contract=platform_contract)
    rows = source_rows(source, platform_contract=platform_contract)
    revision = plan_override['binding']['source_commit'] if plan_override is not None else 'c'*40
    request = C.encode(C.request_for(source, revision, platform_contract=platform_contract))
    projection = {'record_type': 'q2_tokenizer_projection_v0', 'trees': {'source': projection_sources(rows),
                  'inputs': [], 'capsule': [], 'historical': [], 'verifier': []}}
    plan = {'record_type': 'q2_worker_execution_plan_v0', 'scope': C.SCOPE,
        'binding': {'repository': C.REPOSITORY, 'workflow': C.WORKFLOW, 'source_commit': 'c'*40,
                    'run_id': '123456', 'run_attempt': 1, 'job_name': 'verify_host', 'job_id': '999'},
        'source_bindings': rows, 'host': p['native_requirements'], 'request_sha256': C.digest(request),
        'projection_sha256': C.digest(C.encode(projection)), 'bootstrap_lib_sha256': '3'*64,
        'execution': K.execution_plan(Path('/var/lib/pulse-q2-worker-synth001/projection')),
        'phase_start_ns': 1_000_000_000, 'phase_deadline_ns': 1201_000_000_000, **P.NON_AUTHORITY}
    plan['observer_contract_sha256'] = C.digest(C.encode({'source_bindings': rows, 'execution': plan['execution']}))
    plan.update(C.plan_platform_fields(p, plan['host']))
    if plan_override is not None:
        plan = copy.deepcopy(plan_override)
    trace = F.fixture_trace(unknown)
    trace['pre']['context']['source_commit'] = revision
    f = rebind_trace(trace, plan)
    before = {**f['life'], 'private_tree_cleanup': 'pending'}
    data = C.encode(f['pre']), C.encode(f['subject']), C.encode(f['ready']), C.encode(f['terminal']), before, f['records']
    got = K.reconstruct(source, plan, data, f['configuration'],
        lambda m: [1, 10+len(m[1]['content'])],
        lambda ids: ' synthetic exact value\n' if ids == [41,2] else 'synthetic-limit')
    groups = got['groups_bytes']; manifest = K.dataset_manifest(groups, f['pre'], f['terminal'])
    workload = C.parse(f['workload_raw'])
    tokenmap = C.encode({'record_type': 'q2_worker_independent_token_map_v0',
        'input_tokens': [{'messages_sha256': C.digest(C.encode(workload['groups'][i//3]['request']['messages'])),
                         'input_ids': C.parse(pair[0])['input_ids']} for i,pair in enumerate(f['records'])],
        'decoded_continuations': [{'token_ids': C.parse(pair[0])['new_token_ids'], 'text': C.parse(pair[0])['text']} for pair in f['records']]})
    tokencheck = {'record_type': 'q2_worker_tokenizer_check_v0', 'plan_sha256': C.digest(C.encode(plan)),
        'transcript_sha256': C.digest(data[3]), 'lifecycle_before_cleanup_sha256': C.digest(C.encode(before)),
        'groups_sha256': C.digest(groups), 'manifest_sha256': C.digest(manifest), 'token_map_sha256': C.digest(tokenmap),
        'configuration_sha256': P.CONFIGURATION_SHA256, 'verified_calls': 150, 'runtime_versions': p['runtime_versions'],
        'tokenizer_module': 'lib/python3.11/site-packages/transformers/tokenization_utils_fast.py',
        'private_tree_cleanup': 'pending', 'native_origin_reacquired': False, **P.NON_AUTHORITY}
    inputcheck = {'record_type': 'q2_worker_input_check_v0', 'plan_sha256': C.digest(C.encode(plan)),
        'projection_sha256': plan['projection_sha256'], 'request_sha256': plan['request_sha256'],
        'original_inputs_verified': True, 'worker_bytes_verified': True, 'historical_metric_pass': False, **P.NON_AUTHORITY}
    buffers = {'request.json': request, 'plan.json': C.encode(plan), 'projection.json': C.encode(projection),
        'input-check.json': C.encode(inputcheck), 'capture-prelaunch.json': data[0], 'capture-subject.json': data[1],
        'capture-model-ready.json': data[2], 'transcript.json': data[3], 'lifecycle-before-cleanup.json': C.encode(before),
        'lifecycle.json': C.encode(f['life']), 'tokenizer-check.json': C.encode(tokencheck), 'token-map.json': tokenmap,
        'groups.json': groups, 'dataset-manifest.json': manifest}
    for slot, pair in zip(f['pre']['slots'], f['records']):
        stem = 'calls/' + slot['call_id']
        buffers[stem+'.response.json'], buffers[stem+'.ready.json'] = pair
        buffers[stem+'.utf8'] = C.parse(pair[0])['text'].encode()
        buffers[stem+'.intent.json'] = C.encode({'slot': slot, 'binding': f['terminal']['binding'],
            'generation_seconds': 15, 'retries': 0, 'intent': 'before_GO'})
    root=tmp_path/'metric'; (root/'evidence').mkdir(parents=True); output=root/'output'; output.mkdir()
    for name in ('groups.json','dataset-manifest.json','tokenizer-check.json'):
        (root/'evidence'/name).write_bytes(buffers[name])
    reduced=K.reduction_check(root,source,p,plan,output)
    buffers['reduction-check.json']=C.encode(reduced)
    for name in ('summary.json','summary-check.json'): buffers[name]=(output/name).read_bytes()
    assert reduced['metric_pass'] is (not unknown)
    expected={'input_check':('input-check.json',),'worker':('transcript.json',),
              'tokenizer_check':('groups.json','dataset-manifest.json','token-map.json','tokenizer-check.json'),
              'reduction_check':('summary.json','summary-check.json','reduction-check.json')}
    phases=[]
    for (name,prefix,begin,end) in [('input_check','b',1_100_000_000,1_400_000_000),
        ('worker','a',1_500_000_000,305_200_000_000),('tokenizer_check','c',306_000_000_000,307_000_000_000),
        ('reduction_check','d',308_000_000_000,309_000_000_000)]:
        phase=phase_fixture(name,prefix,begin,end,{n:C.digest(buffers[n]) for n in expected[name]})
        if name=='worker':
            for key in ('launch_ns','isolation_observed_ns','exec_ns','stdout_eof_ns','exit_observed_ns','exit_code'):
                phase[key]=f['life'][key]
            phase['isolation']=copy.deepcopy(f['life']['sandbox']);phase['cleanup']=copy.deepcopy(f['life']['cleanup'])
        phases.append(phase)
    result={'schema_version':'q2_release_host_worker_result_v0','scope':C.SCOPE,'status':'native_worker_verified',
        'binding':plan['binding'],'plan_sha256':C.digest(buffers['plan.json']),'phases':phases,
        'source_recheck':'unchanged','cleanup':'verified_removed','private_cleanup_completed_ns':310_000_000_000,
        'evidence_inventory':C.inventory(buffers),'worker_protocol_completed':True,'model_ready_observed':True,'completed_calls':150,
        'metric_pass':not unknown,'historical_metric_pass':False,'full_release_host_verified':False,
        'q2_comparison_accepted':False,'clock_relation':'not_verified','resource_measurement':'unavailable',
        'observation_trust':'owner_runner_privileged_observer_and_github_control_plane',**P.NON_AUTHORITY}
    result.update(C.result_platform_fields(p, plan['host']))
    buffers['result.json']=C.encode(result)
    return buffers

@pytest.fixture(scope='module')
def good_carrier(tmp_path_factory):
    return carrier_fixture(tmp_path_factory.mktemp('q2-carrier'))


def test_full_synthetic_carrier_schema_and_separate_reconstruction(good_carrier):
    buffers=good_carrier
    for name,definition in [('plan.json','plan'),('result.json','result'),('capture-prelaunch.json','worker_prelaunch'),
        ('tokenizer-check.json','tokenizer_check'),('reduction-check.json','reduction_check'),
        ('lifecycle.json','worker_lifecycle'),('lifecycle-before-cleanup.json','worker_lifecycle_before_cleanup')]:
        C.validate_json(ROOT,definition,C.parse(buffers[name]))
    result=K.verify_carrier(ROOT,buffers,C.digest(buffers['result.json']))
    assert result['evidence_reconstructed'] is True
    assert all(result[n] is False for n in ('native_origin_reacquired','tokenization_reperformed','metric_recomputed',
        'production_gate_eligible','active_gate_eligible','same_run_release_authority_eligible'))
    assert result['authority_effect']=='none' and result['historical_metric_pass'] is False


def test_complete_synthetic_measurement_can_preserve_metric_fail(tmp_path):
    b=carrier_fixture(tmp_path,unknown=True)
    result=K.verify_carrier(ROOT,b,C.digest(b['result.json']))
    assert result['evidence_reconstructed'] is True
    r=C.parse(b['reduction-check.json']); summary=C.parse(b['summary.json'])
    assert r['builder_exit']==1 and r['checker_exit']==0 and r['metric_pass'] is False
    assert summary['counts']['groups_eligible']==49 and C.parse(b['result.json'])['worker_protocol_completed'] is True


def test_closed_profile_request_schema_and_source_fixture(git_source,tmp_path):
    source,revision=git_source
    rows=C.source_closure(source,revision,C.load_profile(source)['source_paths'])
    assert len(rows)==39 and rows==source_rows(source)
    raw=C.encode(C.request_for(source,revision))
    request=C.check_request(source,raw,C.digest(raw),revision)
    Draft202012Validator(C.parse((source/C.REQUEST_SCHEMA).read_bytes())).validate(request)
    assert request['planned_calls']==150 and request['consent']==C.CONSENT
    S.initialize_modules(source)
    p,binding,observed,selected=S.authorize(source,owner_environment(source,revision,tmp_path))
    assert selected==raw and rows==observed and binding['run_id']=='123456'
    assert p['native_requirements']==p['archived_platform_requirements']

@pytest.mark.parametrize('field', ['scope','source_commit','profile_sha256','inputs','workload_sha256','worker_sha256',
    'planned_calls','consent','platform_contract','retention','authority_effect','production_gate_eligible',
    'active_gate_eligible','same_run_release_authority_eligible','unexpected'])
def test_coherently_hashed_request_changes_reject(field):
    request=C.request_for(ROOT,'c'*40);request[field]=None
    raw=C.encode(request)
    with pytest.raises(P.ProtocolError):C.check_request(ROOT,raw,C.digest(raw),'c'*40)

@pytest.mark.parametrize('field',['GITHUB_REPOSITORY','GITHUB_EVENT_NAME','GITHUB_REF','GITHUB_WORKFLOW_SHA',
    'GITHUB_WORKFLOW','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_ACTOR','GITHUB_TRIGGERING_ACTOR',
    'GITHUB_ACTOR_ID','GITHUB_ACTIONS','RUNNER_OS','RUNNER_ENVIRONMENT','GITHUB_WORKSPACE','GITHUB_SHA',
    'GITHUB_JOB','GITHUB_RUN_ID',S.SOURCE,S.REQUEST,S.DIGEST,'GITHUB_EVENT_PATH'])
def test_wrong_owner_context_rejects_before_source_or_transport(git_source,tmp_path,monkeypatch,field):
    source,revision=git_source;S.initialize_modules(source)
    env=owner_environment(source,revision,tmp_path);env[field]='wrong'
    monkeypatch.setattr(C,'source_closure',lambda *a,**k:pytest.fail('wrong origin reached source acceptance'))
    with pytest.raises((P.ProtocolError,ValueError)):S.authorize(source,env)

@pytest.mark.parametrize('fault',['inputs','actor','actor_id','actor_bool','sender_type','repository','ref','missing'])
def test_dispatch_event_is_separately_bound(git_source,tmp_path,fault):
    source,revision=git_source;S.initialize_modules(source);env=owner_environment(source,revision,tmp_path)
    path=Path(env['GITHUB_EVENT_PATH']);obj=C.parse(path.read_bytes())
    if fault=='inputs':obj['inputs']['native_request']+=' '
    elif fault=='actor':obj['sender']['login']='other'
    elif fault=='actor_id':obj['sender']['id']=1
    elif fault=='actor_bool':obj['sender']['id']=True
    elif fault=='sender_type':obj['sender']['type']='Bot'
    elif fault=='repository':obj['repository']['full_name']='other/repo'
    elif fault=='ref':obj['ref']='other'
    else:obj.pop('sender')
    path.write_bytes(C.encode(obj))
    with pytest.raises(P.ProtocolError):S.authorize(source,env)

@pytest.mark.parametrize('fault',['absent','changed_digest','trailing_lf','duplicate','bom','false_count'])
def test_exact_request_bytes_and_json_reject(git_source,fault):
    source,revision=git_source;raw=C.encode(C.request_for(source,revision));expected=C.digest(raw)
    if fault=='absent':raw=b''
    elif fault=='changed_digest':expected='0'*64
    elif fault=='trailing_lf':raw+=b'\n'
    elif fault=='duplicate':raw=b'{"scope":"a","scope":"b"}';expected=C.digest(raw)
    elif fault=='bom':raw=b'\xef\xbb\xbf'+raw;expected=C.digest(raw)
    else:o=C.parse(raw);o['planned_calls']=True;raw=C.encode(o);expected=C.digest(raw)
    with pytest.raises(P.ProtocolError):C.check_request(source,raw,expected,revision)


def test_metadata_only_request_cli_needs_explicit_flag(git_source):
    source,revision=git_source
    base=[sys.executable,'-I','-B',str(source/C.SELF),'--repo-root',str(source),'--source-commit',revision]
    no=subprocess.run(base,capture_output=True,timeout=20)
    assert no.returncode==2 and not no.stdout
    yes=subprocess.run(base+['--authorize-150-and-actions-retention'],capture_output=True,timeout=20)
    assert yes.returncode==0,yes.stderr
    assert yes.stdout==C.encode(C.request_for(source,revision)) and yes.stderr==b''


def test_collector_rejects_unauthorized_cli_before_import():
    result=subprocess.run([sys.executable,'-I','-B',str(TOOLS/'verify_q2_release_host_worker_v0.py'),
        '--repo-root',str(ROOT)],env={'PATH':'/usr/bin:/bin','LANG':'C'},capture_output=True,timeout=10)
    assert result.returncode==2 and result.stdout==b'' and result.stderr==b'q2_worker_verification_rejected\n'


def reissue(b):
    """Synthetic mutation control only. An actual selected digest is immutable."""
    result=C.parse(b['result.json'])
    result['evidence_inventory']=C.inventory({n:raw for n,raw in b.items() if n!='result.json'})
    b['result.json']=C.encode(result)
    return C.digest(b['result.json'])

@pytest.mark.parametrize('fault',['missing','extra','wrong_result_digest','phase_reorder','phase_reuse','phase_exit_bool',
    'phase_output_digest','phase_late','phase_overlap','phase_no_isolation','phase_no_cleanup','input_check_plan',
    'worker_lifecycle','source_bytes','source_path','observer','root','command','plan_clock','projection',
    'cleanup_pending','cleanup_rebinding','token_map_token','token_map_hash','token_count','metric_pass',
    'builder_exit','builder_stdout','reduction_plan','checker_result','original_utf8','intent','authority','cleanup_clock'])
def test_carrier_negative_matrix(good_carrier,fault):
    b=dict(good_carrier);r=C.parse(b['result.json']);original=C.digest(b['result.json'])
    def change(n,fn):o=C.parse(b[n]);fn(o);b[n]=C.encode(o)
    if fault=='missing':b.pop('calls/q2fx-050-r03.response.json')
    elif fault=='extra':b['extra.json']=b'{}'
    elif fault=='wrong_result_digest':original='0'*64
    elif fault=='phase_reorder':r['phases'][0],r['phases'][1]=r['phases'][1],r['phases'][0]
    elif fault=='phase_reuse':r['phases'][2]['isolation']=r['phases'][0]['isolation'];r['phases'][2]['cleanup']=r['phases'][0]['cleanup']
    elif fault=='phase_exit_bool':r['phases'][0]['exit_code']=False
    elif fault=='phase_output_digest':r['phases'][0]['outputs']['input-check.json']='0'*64
    elif fault=='phase_late':r['phases'][2]['exit_observed_ns']+=181_000_000_000
    elif fault=='phase_overlap':r['phases'][2]['launch_ns']=1
    elif fault=='phase_no_isolation':r['phases'][0]['isolation']['uid']=0
    elif fault=='phase_no_cleanup':r['phases'][0]['cleanup']['client_reaped']=False
    elif fault=='input_check_plan':change('input-check.json',lambda o:o.update(plan_sha256='0'*64))
    elif fault=='worker_lifecycle':r['phases'][1]['exec_ns']+=1
    elif fault=='source_bytes':change('plan.json',lambda o:o['source_bindings'][0].update(sha256='0'*64))
    elif fault=='source_path':change('plan.json',lambda o:o['source_bindings'][0].update(path='other.py'))
    elif fault=='observer':change('plan.json',lambda o:o.update(observer_contract_sha256='0'*64))
    elif fault=='root':change('plan.json',lambda o:o['execution']['worker_argv_template'].__setitem__(0,'/tmp/python'))
    elif fault=='command':change('plan.json',lambda o:o['execution']['worker_argv_template'].__setitem__(5,'diagnostic'))
    elif fault=='plan_clock':change('plan.json',lambda o:o.update(phase_deadline_ns=o['phase_deadline_ns']+1))
    elif fault=='projection':change('projection.json',lambda o:o['trees']['source'][0].update(sha256='0'*64))
    elif fault=='cleanup_pending':change('lifecycle.json',lambda o:o.update(private_tree_cleanup='pending'))
    elif fault=='cleanup_rebinding':change('lifecycle.json',lambda o:o.update(exec_ns=o['exec_ns']+1))
    elif fault=='token_map_token':change('token-map.json',lambda o:o['decoded_continuations'][0].update(token_ids=[42,2]))
    elif fault=='token_map_hash':change('token-map.json',lambda o:o['input_tokens'][0].update(messages_sha256='0'*64))
    elif fault=='token_count':change('token-map.json',lambda o:o['input_tokens'].pop())
    elif fault=='metric_pass':r['metric_pass']=not r['metric_pass']
    elif fault=='builder_exit':change('reduction-check.json',lambda o:o.update(builder_exit=1))
    elif fault=='builder_stdout':change('reduction-check.json',lambda o:o.update(builder_stdout_sha256='0'*64))
    elif fault=='reduction_plan':change('reduction-check.json',lambda o:o.update(plan_sha256='0'*64))
    elif fault=='checker_result':change('summary-check.json',lambda o:o.update(ok=False))
    elif fault=='original_utf8':b['calls/q2fx-001-r01.utf8']=b'substituted'
    elif fault=='intent':change('calls/q2fx-001-r01.intent.json',lambda o:o.update(retries=1))
    elif fault=='authority':r['production_gate_eligible']=True
    else:r['private_cleanup_completed_ns']=1
    b['result.json']=C.encode(r)
    expected=original if fault=='wrong_result_digest' else reissue(b)
    with pytest.raises((ValueError,IndexError,KeyError,StopIteration)):K.verify_carrier(ROOT,b,expected)


def test_inner_archive_roundtrip_closed_read_and_cli(good_carrier,tmp_path):
    S.initialize_modules(ROOT)
    raw=S.native_evidence_zip(good_carrier);archive=tmp_path/'evidence.zip';archive.write_bytes(raw)
    result=C.digest(good_carrier['result.json'])
    assert K.read_carrier(archive,C.digest(raw))==good_carrier
    cmd=[sys.executable,'-I','-B',str(TOOLS/'check_q2_release_host_worker_v0.py'),'--phase','check-evidence',
         '--root',str(archive),'--source',str(ROOT),'--expected-result-sha256',result,'--expected-archive-sha256',C.digest(raw)]
    run=subprocess.run(cmd,capture_output=True,timeout=20)
    assert run.returncode==0 and run.stdout==b'q2_worker_evidence_checked\n',run.stderr
    wrong=subprocess.run(cmd[:-1]+['0'*64],capture_output=True,timeout=20)
    assert wrong.returncode==2 and not wrong.stdout


def test_precleanup_verification_cannot_claim_cleanup(good_carrier):
    b=good_carrier;f=F.fixture_trace();plan=C.parse(b['plan.json'])
    records=[(b['calls/'+s['call_id']+'.response.json'],b['calls/'+s['call_id']+'.ready.json']) for s in f['pre']['slots']]
    data=(*(b[n] for n in ('capture-prelaunch.json','capture-subject.json','capture-model-ready.json','transcript.json')),
          C.parse(b['lifecycle-before-cleanup.json']),records)
    got=K.reconstruct(ROOT,plan,data,f['configuration'],lambda m:[1,10+len(m[1]['content'])],lambda ids:' synthetic exact value\n')
    assert got['private_tree_cleanup_verified'] is False and got['native_origin_verified'] is False


def runtime_fixture(monkeypatch,tmp_path,*,fault='none'):
    """Real source worker process and pipe/barrier; kernel and timers are doubles."""
    S.initialize_modules(ROOT);N=S.native
    synthetic_privileged_filesystem(monkeypatch, tmp_path)
    root=tmp_path/'projection';private=tmp_path/'private';root.mkdir();private.mkdir()
    for sub in ('source','capsule/source','control','work','evidence'):(root/sub).mkdir(parents=True,exist_ok=True)
    for name in (C.WORKER,C.WORKLOAD,C.PACK+'profiles/q2_reference_subject_v0.json',C.PACK+'profiles/q2_reference_model_files_v0.json'):
        for sub in ('source','capsule/source'):
            p=root/sub/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    budget=K.T.Budget(1200);request=C.encode(C.request_for(ROOT,'c'*40))
    plan={'binding':{'repository':C.REPOSITORY,'workflow':C.WORKFLOW,'source_commit':'c'*40,'run_id':'123456','run_attempt':1},
        'request_sha256':C.digest(request),'observer_contract_sha256':'2'*64,
        'phase_start_ns':budget.start_ns,'phase_deadline_ns':budget.start_ns+1200_000_000_000,
        'execution':K.execution_plan(root)}
    (root/'control/capture-prelaunch.json').write_bytes(C.encode(S.prelaunch(root,plan)))
    config=private/'fixture-config.json';config.write_bytes(C.encode(F.FIXED_CONFIGURATION));counter=private/'toy-model-call-counter.txt'
    shim=F.TOY_CLI
    if fault=='ready':shim=shim.replace("'threads':1", "'threads':2")
    elif fault=='truncated':shim=shim.replace("state['calls']+=1", "state['calls']+=1\n        if state['calls']==1: raise ValueError('synthetic model failure')")
    elif fault=='exit':shim=shim.replace('raise SystemExit(rc)','raise SystemExit(7 if rc==0 else rc)')
    elif fault=='extra':shim=shim.replace('raise SystemExit(rc)',"print('EXTRA',flush=True)\nraise SystemExit(rc)")
    child=private/'worker-fixture.py'
    child.write_text("import sys\nprint('{\"synthetic_barrier\":true}',flush=True)\nassert sys.stdin.buffer.readline()==b'EXEC\\n'\n"+shim)
    observed=[];controls=[]
    def command(unit,stage,argv,work,python,**kwargs):
        assert stage=='captureworker' and argv[4:6]==['--mode','capture-reference']
        assert argv[3]==str(root/'capsule/source'/C.WORKER)
        observed.append(list(argv))
        return [sys.executable,'-I','-B',str(child),str(ROOT),str(root/'control/capture-prelaunch.json'),
                str(root/'control/capture-subject.json'),str(counter),str(config)]
    def observe(unit,stage,frame,hostnet,**kwargs):
        assert frame=={'synthetic_barrier':True}
        obs=F.sandbox();obs['unit']=unit
        obs['capture_runtime_seconds']=kwargs['capture_seconds'];obs['properties']['RuntimeMaxUSec']=str(kwargs['capture_seconds'])+'s'
        return obs
    def close(service):
        controls.append('close')
        proc=service.process
        if proc.poll() is None:proc.kill()
        proc.wait(timeout=5)
        service.reader.close();proc.stdin.close();proc.stdout.close();service.log.close()
        if fault=='cleanup':raise N.NativeQualificationError('synthetic_cleanup_unverified')
        return {'unit':service.unit,'properties':{'LoadState':'not-found','ActiveState':'inactive','ControlGroup':''},
                'cgroup_empty_or_removed':True,'client_reaped':True}
    def watchdog(prefix,unit):
        controls.append('arm')
        if fault=='watchdog':raise N.NativeQualificationError('synthetic_timer_failure')
        return prefix+'-watchdog.timer'
    def disarm(prefix):
        controls.append('disarm')
        if fault=='timer_cleanup':raise N.NativeQualificationError('synthetic_timer_cleanup_unverified')
        return {'record_type':'q2_capture_watchdog_closed_v0','stop_returncode':0,'units':[
            {'unit':prefix+'-watchdog.'+s,'LoadState':'not-found','ActiveState':'inactive'} for s in ('timer','service')],
            'closed_ns':time.monotonic_ns()}
    monkeypatch.setattr(N,'service_command',command);monkeypatch.setattr(N,'observe_service',observe)
    monkeypatch.setattr(N,'close_capture_service',close);monkeypatch.setattr(N,'watchdog',watchdog)
    monkeypatch.setattr(N,'disarm_capture_watchdog',disarm)
    monkeypatch.setattr(S,'check_unchanged',lambda *args:None)
    return root,private,plan,budget,counter,observed,controls


def test_actual_collector_worker_adapter_full_protocol(monkeypatch,tmp_path):
    root,private,plan,budget,counter,observed,controls=runtime_fixture(monkeypatch,tmp_path)
    state={'worker_started':False,'model_ready_observed':False,'occurrences':[]}
    record=S.worker_phase(root,private,plan,C.load_profile(ROOT),{},budget,state)
    assert int(counter.read_text())==150 and len(observed)==1
    assert controls.count('arm')==controls.count('disarm')==150 and controls.count('close')==1
    assert record['exit_code']==0 and state['worker_started'] and state['model_ready_observed']
    assert all(o['status']=='completed' for o in state['occurrences'])
    data=K.read_protocol(root/'evidence')
    got=K.reconstruct(ROOT,plan,data,F.FIXED_CONFIGURATION,lambda m:[1,10+len(m[1]['content'])],lambda ids:' synthetic exact value\n')
    assert got['protocol_reconstructed'] is True and got['private_tree_cleanup_verified'] is False
    service=state['service'];assert service.process.poll()==0 and service.cleanup_verified is True
    assert len(service.commands)==303 and service.commands[0]['command']=='EXEC\n'
    assert len([p for p in (root/'evidence/calls').iterdir()])==600

@pytest.mark.parametrize('fault',['ready','truncated','exit','extra','cleanup','watchdog','timer_cleanup'])
def test_actual_worker_adapter_failure_closes_without_acceptance(monkeypatch,tmp_path,fault):
    root,private,plan,budget,counter,observed,controls=runtime_fixture(monkeypatch,tmp_path,fault=fault)
    state={'worker_started':False,'model_ready_observed':False,'occurrences':[]}
    with pytest.raises((ValueError,KeyError)):
        S.worker_phase(root,private,plan,C.load_profile(ROOT),{},budget,state)
    assert len(observed)==1 and 'close' in controls and state['service'].process.poll() is not None
    assert not (root/'evidence/lifecycle-before-cleanup.json').exists()
    if fault=='ready':assert not any(c['command'].startswith('GENERATE') for c in state['service'].commands)
    if fault in ('cleanup','timer_cleanup'):assert not state['service'].cleanup_verified or not all(S.ACTIVE_TIMERS.values())



def workflow_document():
    return yaml.load((ROOT / C.WORKFLOW).read_text(), Loader=yaml.BaseLoader)


def test_manual_workflow_three_inputs_pins_permissions_retention():
    doc = workflow_document()
    assert doc['name'] == C.NAME and set(doc['on']) == {'workflow_dispatch'}
    assert set(doc['on']['workflow_dispatch']['inputs']) == {'source_commit','native_request','native_request_sha256'}
    assert all(r['required']=='true' and r['type']=='string' for r in doc['on']['workflow_dispatch']['inputs'].values())
    assert doc['permissions'] == {'contents':'read','actions':'read'}
    assert doc['concurrency']['cancel-in-progress']=='false' and set(doc['jobs'])=={'verify_host'}
    job=doc['jobs']['verify_host'];steps=job['steps']
    assert job['runs-on']=='ubuntu-24.04' and job['timeout-minutes']=='30'
    assert steps[1]['with']=={'ref':'${{ github.sha }}','persist-credentials':'false'}
    assert [s['uses'] for s in steps if 'uses' in s]==[
        'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
        'actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0',
        'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a']
    assert steps[2]['with']=={'python-version':'3.11.16'}
    assert steps[3]['env']=={S.TOKEN:'${{ github.token }}'} and steps[-1]['if']=='always()'
    assert steps[-1]['with']['retention-days']=='30' and steps[-1]['with']['overwrite']=='false'
    assert steps[-1]['with']['if-no-files-found']=='error'
    assert steps[-1]['with']['path'].splitlines()==[
        '${{ runner.temp }}/q2-native-worker/'+n for n in ('evidence.zip','receipt.json','failure.json')]
    assert '${{' not in '\n'.join(s.get('run','') for s in steps)
    for name in ('GITHUB_EVENT_NAME','GITHUB_ACTOR_ID','GITHUB_TRIGGERING_ACTOR','GITHUB_RUN_ATTEMPT',
                 'GITHUB_REF','GITHUB_SHA','GITHUB_WORKFLOW_SHA'):
        assert name in steps[0]['run']
    allowlist=steps[3]['run'].split('--preserve-env=',1)[1].split()[0].split(',')
    for name in (S.TOKEN,S.REQUEST,S.DIGEST,S.SOURCE,'GITHUB_JOB','ImageVersion','GITHUB_EVENT_PATH'):
        assert name in allowlist
    assert len(allowlist)==len(set(allowlist))


COUNT_CONSUMERS=(
    'test_q2_reference_acquisition_v0.py','test_q2_hosted_intake_workflow_v0.py',
    'test_pulsemech_compute_bounded_execution_v0.py',
    'test_pulsemech_compute_current_run_export_candidate_workflow_v0.py',
    'test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py',
    'test_q2_release_host_tokenizer_v0.py','test_q2_release_host_tokenizer_workflow_v0.py')


def test_both_programs_once_and_all_seven_manifest_consumers():
    entries=[l.split('#',1)[0].strip() for l in (ROOT/'ci/tools-tests.list').read_text().splitlines()]
    entries=[l for l in entries if l]
    assert len(entries)==len(set(entries))==167
    for n in ('tests/test_q2_release_host_worker_protocol_v0.py','tests/test_q2_release_host_worker_v0.py'):
        assert entries.count(n)==1 and n not in (ROOT/'ci/pytest-tests.list').read_text()
        assert 'pytest.main([__file__])' in (ROOT/n).read_text()
    for n in COUNT_CONSUMERS:
        text=(ROOT/'tests'/n).read_text()
        assert re.search(r'==\s*167\b',text) and not re.search(r'==\s*165\b',text)


@pytest.fixture(scope='module')
def hygiene_fixture():
    return module('q2_worker_original_hygiene_fixture',ROOT/'tests/test_q2_reference_acquisition_v0.py')


def test_actual_hygiene_accepts_new_exact_workflow(hygiene_fixture,tmp_path):
    run=hygiene_fixture._run_hygiene_python_sync(tmp_path,q2_text=hygiene_fixture._q2_workflow_text())
    assert run.returncode==0,run.stdout+run.stderr


@pytest.mark.parametrize('fault',['floating','wrong_patch','wrong_job','duplicate','missing','other_job'])
def test_actual_hygiene_rejects_worker_pin_drift(hygiene_fixture,tmp_path,fault):
    doc=workflow_document();job=doc['jobs']['verify_host'];setup=job['steps'][2]
    if fault=='floating':setup['with']['python-version']='3.11'
    elif fault=='wrong_patch':setup['with']['python-version']='3.11.17'
    elif fault=='wrong_job':doc['jobs']['wrong']=doc['jobs'].pop('verify_host')
    elif fault=='duplicate':job['steps'].append(copy.deepcopy(setup))
    elif fault=='missing':job['steps'].remove(setup)
    else:doc['jobs']['other']={'steps':[copy.deepcopy(setup)]}
    run=hygiene_fixture._run_hygiene_python_sync(tmp_path,q2_text=hygiene_fixture._q2_workflow_text(),
        extra_workflows={Path(C.WORKFLOW).name:yaml.safe_dump(doc)})
    assert run.returncode==1,run.stdout+run.stderr


@pytest.mark.parametrize('fault',['unchanged','renamed','name','authority','permissions','trigger','retention','argv','pin'])
def test_exact_workflow_carrier_classification(tmp_path,fault):
    classifier=module('q2_worker_carrier_classifier',ROOT/'scripts/build_normative_shadow_inventory_v0.py')
    path=tmp_path/C.WORKFLOW;path.parent.mkdir(parents=True)
    text=(ROOT/C.WORKFLOW).read_text()
    if fault=='renamed':path=path.with_name('q2_worker_other.yml')
    elif fault=='name':text=text.replace(C.NAME,'Different workflow')
    elif fault=='authority':text+='\n# materialize_release_decision\n'
    elif fault=='permissions':text=text.replace('contents: read','contents: write')
    elif fault=='trigger':text=text.replace('  workflow_dispatch:','  push:')
    elif fault=='retention':text=text.replace('retention-days: 30','retention-days: 90')
    elif fault=='argv':text=text.replace('verify_q2_release_host_worker_v0.py','other.py')
    elif fault=='pin':text=text.replace('3.11.16','3.11.17')
    path.write_text(text)
    got=classifier.classify_workflow(path,repo_root=tmp_path)
    if fault=='unchanged':
        assert got['carrier_class']=='audit_preservation' and got['authority_impacting']=='no'
        assert all(got[n] is False for n in ('required_gate_participation','attestation_participation','release_path_participation'))
    else:assert got['primary_role']=='unclassified workflow'


def test_request_cli_constructs_only_exact_owner_bytes(git_source):
    source,revision=git_source
    command=[sys.executable,'-I','-B',str(source/C.SELF),'--repo-root',str(source),'--source-commit',revision]
    no=subprocess.run(command,capture_output=True,timeout=20)
    assert no.returncode==2 and no.stdout==b''
    yes=subprocess.run(command+['--authorize-150-and-actions-retention'],capture_output=True,timeout=20)
    assert yes.returncode==0 and yes.stdout==C.encode(C.request_for(source,revision)) and not yes.stderr


@pytest.mark.parametrize('fault',['none','wrong_actor','dirty_helper','wrong_workflow'])
def test_stdlib_preimport_bootstrap_holds_committed_bytes(git_source,tmp_path,monkeypatch,fault):
    source,revision=git_source;env=owner_environment(source,revision,tmp_path)
    fixture=tmp_path/'copy'
    if fault=='dirty_helper':
        shutil.copytree(source,fixture);source=fixture;env=owner_environment(source,revision,tmp_path)
        (source/C.CHECKER).write_text('raise AssertionError("dirty helper imported")\n')
    if fault=='wrong_actor':env['GITHUB_ACTOR']='other'
    if fault=='wrong_workflow':env['GITHUB_WORKFLOW_REF']='wrong'
    # Root identity and /var/lib placement are synthetic; Git and held IO remain real.
    fs = synthetic_privileged_filesystem(monkeypatch, tmp_path)
    monkeypatch.setattr(S.os,'geteuid',lambda:0)
    if fault!='none':
        with pytest.raises(ValueError):S.bootstrap_sources(source,env)
    else:
        snapshot=S.bootstrap_sources(source,env)
        try:
            assert snapshot.parent == tmp_path and fs.allocated == [snapshot]
            assert stat.S_IMODE(snapshot.stat().st_mode)==0o700
            assert all((snapshot/n).read_bytes()==(source/n).read_bytes() for n in C.load_profile(source)['source_paths'])
        finally:shutil.rmtree(snapshot)


def api_fixture(binding):
    actor={'login':'HKati','id':128643840}
    run={'id':int(binding['run_id']),'run_attempt':1,'head_sha':binding['source_commit'],
        'event':'workflow_dispatch','head_branch':'main','path':C.WORKFLOW,
        'repository':{'full_name':C.REPOSITORY},'head_repository':{'full_name':C.REPOSITORY},
        'actor':copy.deepcopy(actor),'triggering_actor':copy.deepcopy(actor)}
    jobs={'total_count':1,'jobs':[{'name':'verify_host','id':999,'run_id':int(binding['run_id']),
        'run_attempt':1,'head_sha':binding['source_commit'],'status':'in_progress'}]}
    return [{'object':{'sha':binding['source_commit']}},run,jobs]


@pytest.mark.parametrize('fault',['none','main','run_id','attempt','sha','event','branch','path','repository','head_repository',
    'actor','triggering_actor','actor_bool','total','job_id','job_attempt','job_run','job_sha','job_status','job_name'])
def test_control_plane_exact_origin_and_job(git_source,tmp_path,monkeypatch,fault):
    source,revision=git_source;S.initialize_modules(source)
    _,binding,_,_=S.authorize(source,owner_environment(source,revision,tmp_path));responses=api_fixture(binding)
    main,run,jobs=responses;job=jobs['jobs'][0]
    if fault=='main':main['object']['sha']='0'*40
    elif fault=='run_id':run['id']+=1
    elif fault=='attempt':run['run_attempt']=True
    elif fault=='sha':run['head_sha']='0'*40
    elif fault in ('event','path'):run[fault]='wrong'
    elif fault=='branch':run['head_branch']='other'
    elif fault in ('repository','head_repository'):run[fault]['full_name']='other/repo'
    elif fault in ('actor','triggering_actor'):run[fault]['login']='other'
    elif fault=='actor_bool':run['actor']['id']=True
    elif fault=='total':jobs['total_count']=2
    elif fault=='job_id':job['id']=True
    elif fault=='job_attempt':job['run_attempt']=2
    elif fault=='job_run':job['run_id']+=1
    elif fault=='job_sha':job['head_sha']='0'*40
    elif fault=='job_status':job['status']='completed'
    elif fault=='job_name':job['name']='wrong'
    endpoints=[]
    def api(client,path,budget):
        endpoints.append(path);return responses[len(endpoints)-1]
    monkeypatch.setattr(S.U.transport,'api_json',api)
    if fault=='none':
        assert S.authenticate_current(object(),binding,S.T.Budget())=={**binding,'job_id':'999'}
        assert endpoints==['/git/ref/heads/main','/actions/runs/123456/attempts/1','/actions/runs/123456/attempts/1/jobs?per_page=100']
    else:
        with pytest.raises(P.ProtocolError):S.authenticate_current(object(),binding,S.T.Budget())


@pytest.mark.parametrize('fault',['none','empty_dir','symlink','duplicate','extra','wrong_hash'])
def test_carrier_physical_closed_extent(good_carrier,tmp_path,fault):
    if fault in ('none','empty_dir','symlink'):
        directory=tmp_path/'evidence';directory.mkdir()
        for name,raw in good_carrier.items():
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        if fault=='empty_dir':(directory/'unused').mkdir()
        elif fault=='symlink':(directory/'another').symlink_to(directory/'calls',target_is_directory=True)
        if fault=='none':assert K.read_carrier(directory)==good_carrier
        else:
            with pytest.raises(P.ProtocolError):K.read_carrier(directory)
    else:
        raw=S.native_evidence_zip(good_carrier)
        stream=io.BytesIO(raw)
        if fault in ('duplicate','extra'):
            with zipfile.ZipFile(stream,'a') as z:z.writestr('result.json' if fault=='duplicate' else 'extra.json',b'{}')
        data=stream.getvalue();path=tmp_path/'evidence.zip';path.write_bytes(data)
        with pytest.raises(P.ProtocolError):K.read_carrier(path,'0'*64 if fault=='wrong_hash' else C.digest(data))


def full_supervisor_fixture(monkeypatch,tmp_path,git_source,fault,*,platform_contract=C.STRICT_PLATFORM):
    """Real orchestration/file custody; archive, host, service execution are fixtures.

    The separate worker adapter tests run real toy CLI processes. This test does
    not turn supplied host records into observed native isolation or inference.
    """
    source,revision=git_source;S.initialize_modules(source)
    fs = synthetic_privileged_filesystem(monkeypatch, tmp_path)
    # The orchestration test does not execute these argv paths. Keep the exact
    # native path grammar in its synthetic plan while real IO stays in tmp_path.
    # The independent carrier checker and its path rejection remain unchanged.
    def synthetic_execution_plan(root):
        assert root.parent in fs.allocated and root.name == 'projection'
        assert re.fullmatch(r'pulse-q2-worker-[a-z0-9_]{8}', root.parent.name)
        return K.execution_plan(Path('/var/lib') / root.parent.name / 'projection')
    monkeypatch.setattr(S, 'K', _FixtureModuleView(K, execution_plan=synthetic_execution_plan))
    env=owner_environment(source,revision,tmp_path,platform_contract=platform_contract)
    real_budget=S.T.Budget
    def budget(*args):
        b=real_budget(*args);b.start_ns=1_000_000_000;return b
    monkeypatch.setattr(S.T,'Budget',budget)
    monkeypatch.setattr(S,'time',types.SimpleNamespace(monotonic_ns=lambda:310_000_000_000,monotonic=time.monotonic))
    monkeypatch.setattr(S.U,'host_record',lambda e,p:copy.deepcopy(p['native_requirements']))
    monkeypatch.setattr(S.shutil,'disk_usage',lambda p:types.SimpleNamespace(free=32*1024**3))
    endpoints=[];responses=api_fixture({'run_id':'123456','source_commit':revision})
    def api(client,path,b):endpoints.append(path);return responses[len(endpoints)-1]
    monkeypatch.setattr(S.U.transport,'api_json',api)
    monkeypatch.setattr(S.io,'GitHubArtifactTransport',lambda token:object())
    downloads=[]
    def download(client,identity,path,b):
        assert len(endpoints)==3
        downloads.append(path.name);path.write_bytes(b'SYNTHETIC ARCHIVE TRANSPORT FIXTURE')
    def bootstrap(identity,path,b):downloads.append(path.name);path.write_bytes(b'SYNTHETIC BOOTSTRAP FIXTURE')
    monkeypatch.setattr(S.U.transport,'download_artifact',download)
    monkeypatch.setattr(S.U.transport,'download_bootstrap',bootstrap)
    monkeypatch.setattr(S.U,'prepare_bootstrap_library',lambda *a:'3'*64)
    monkeypatch.setattr(S.U,'prepare_verifier',lambda *a:[])
    monkeypatch.setattr(S.T,'bind_collector_dependencies',lambda *a:None)
    roots=[];phase_calls=[];carrier={};checks=[]
    def materialize(repo,prepared,root,p,rows,b):
        roots.append(root)
        for name in p['source_paths']:
            target=root/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((repo/name).read_bytes())
        for name in (C.WORKER,C.WORKLOAD,C.PACK+'profiles/q2_reference_subject_v0.json',C.PACK+'profiles/q2_reference_model_files_v0.json'):
            target=root/'capsule/source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((repo/name).read_bytes())
        return {'record_type':'q2_tokenizer_projection_v0','trees':{'source':projection_sources(rows),
            'inputs':[],'capsule':[],'historical':[],'verifier':[]}},{}
    monkeypatch.setattr(S.U,'materialize',materialize)
    def unchanged(*args):
        checks.append('recheck')
        if fault=='recheck' and len(phase_calls)==4:raise P.ProtocolError('synthetic source drift')
    monkeypatch.setattr(S,'check_unchanged',unchanged)
    def phase(name,root,private,plan,p,projection,b,state=None):
        phase_calls.append(name)
        if name=='input_check':
            data=carrier_fixture(tmp_path/'carrier',plan_override=plan,source=source)
            carrier.update(data)
        if fault==name:raise P.ProtocolError('synthetic phase failure')
        selected={'input_check':['input-check.json'],
            'worker':['capture-prelaunch.json','capture-subject.json','capture-model-ready.json','transcript.json','lifecycle-before-cleanup.json']+
                [n for n in carrier if n.startswith('calls/')],
            'tokenizer_check':['groups.json','dataset-manifest.json','token-map.json','tokenizer-check.json'],
            'reduction_check':['summary.json','summary-check.json','reduction-check.json']}[name]
        for n in selected:
            target=root/'evidence'/n;target.parent.mkdir(parents=True,exist_ok=True);S.frozen_write(target,carrier[n])
        if state is not None:
            state.update(worker_started=True,model_ready_observed=True,occurrences=C.parse(carrier['transcript.json'])['occurrences'])
        return next(r for r in C.parse(carrier['result.json'])['phases'] if r['id']==name)
    monkeypatch.setattr(S,'checker_phase',lambda root,private,name,*args:phase(name,root,private,*args))
    monkeypatch.setattr(S,'worker_phase',lambda root,private,*args:phase('worker',root,private,*args))
    actual_rmtree=shutil.rmtree
    if fault=='cleanup':
        def fail_rmtree(path,*args,**kwargs):
            if roots and Path(path)==roots[0].parent:raise OSError('synthetic removal failure')
            return actual_rmtree(path,*args,**kwargs)
        monkeypatch.setattr(S.shutil,'rmtree',fail_rmtree)
    if fault=='publication':
        actual_publish=S.U.atomic_publish
        def fail_publish(directory,name,raw):
            if name=='receipt.json':raise OSError('synthetic receipt publication failure')
            return actual_publish(directory,name,raw)
        monkeypatch.setattr(S.U,'atomic_publish',fail_publish)
    if fault=='final_verifier':
        monkeypatch.setattr(K,'verify_carrier',lambda *a:(_ for _ in ()).throw(P.ProtocolError('synthetic final rejection')))
    return source,env,roots,phase_calls,downloads,actual_rmtree


@pytest.mark.parametrize('fault',['none','input_check','worker','tokenizer_check','reduction_check','cleanup','recheck','publication','final_verifier'])
def test_full_supervisor_atomic_custody_and_rejection(monkeypatch,tmp_path,git_source,fault):
    source,env,roots,phases,downloads,remove=full_supervisor_fixture(monkeypatch,tmp_path,git_source,fault)
    try:
        if fault=='none':
            result=S.supervise(source,environment=env)
            output=tmp_path/'q2-native-worker';receipt=C.parse((output/'receipt.json').read_bytes())
            assert result['cleanup']=='verified_removed' and result['completed_calls']==150
            assert all(result[n] is False for n in ('production_gate_eligible','active_gate_eligible','same_run_release_authority_eligible','historical_metric_pass','q2_comparison_accepted'))
            archive=(output/'evidence.zip').read_bytes()
            assert C.digest(archive)==receipt['archive_sha256']
            buffers=K.read_carrier(output/'evidence.zip',receipt['archive_sha256'])
            assert K.verify_carrier(source,buffers,receipt['result_sha256'])['evidence_reconstructed'] is True
            assert phases==list(C.PHASES) and len(downloads)==6 and not (output/'failure.json').exists()
        else:
            with pytest.raises((P.ProtocolError,ValueError,OSError)):S.supervise(source,environment=env)
            output=tmp_path/'q2-native-worker'
            assert not (output/'receipt.json').exists() and not (output/'evidence.zip').exists()
            failure=C.parse((output/'failure.json').read_bytes())
            assert failure['accepted_native_result'] is False and failure['authority_effect']=='none'
            assert failure['cleanup']==('not_verified' if fault=='cleanup' else 'verified_removed')
            if fault in C.PHASES:assert phases==list(C.PHASES[:C.PHASES.index(fault)+1])
        if fault!='cleanup':assert all(not r.parent.exists() for r in roots)
    finally:
        for r in roots:
            if r.parent.exists():remove(r.parent)



def test_available_python_313_stops_smoke_before_manifest(tmp_path):
    other=shutil.which('python3.13')
    if other is None:
        pytest.skip('separate Python 3.13 interpreter is not installed')
    original=module('q2_worker_older_hosted_smoke_fixture',ROOT/'tests/test_q2_hosted_intake_workflow_v0.py')
    result=original._run_actual_tools_smoke_step(tmp_path,other)
    assert result.returncode==1 and '::error::Q2 smoke replay environment mismatch:' in result.stdout
    assert not (tmp_path/'smoke_reached').exists() and 'Traceback' not in result.stderr


def checker_projection_fixture(tmp_path,good_carrier):
    root=tmp_path/'projection';(root/'control').mkdir(parents=True);(root/'source').mkdir()
    selected=C.request_contract(good_carrier['request.json'])
    for name in C.load_profile(ROOT,platform_contract=selected)['source_paths']:
        dest=root/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    plan=C.parse(good_carrier['plan.json']);plan['execution']=K.execution_plan(root)
    plan['observer_contract_sha256']=C.digest(C.encode({'source_bindings':plan['source_bindings'],'execution':plan['execution']}))
    for name,raw in [('plan.json',C.encode(plan)),('request.json',good_carrier['request.json']),('projection.json',good_carrier['projection.json'])]:
        (root/'control'/name).write_bytes(raw)
    return root,plan


@pytest.mark.parametrize('fault',['none','plan_digest','request_digest','plan_noncanonical','source_bytes','projection_bytes',
    'host','execution','clock','observer','profile','bootstrap'])
def test_checker_preconditions_and_projection_bindings(tmp_path,good_carrier,monkeypatch,fault):
    root,plan=checker_projection_fixture(tmp_path,good_carrier);expected=C.digest(C.encode(plan));request=plan['request_sha256']
    if fault=='plan_digest':expected='0'*64
    elif fault=='request_digest':request='0'*64
    elif fault=='plan_noncanonical':(root/'control/plan.json').write_bytes(C.encode(plan)+b' ');expected=C.digest((root/'control/plan.json').read_bytes())
    elif fault=='source_bytes':(root/'source'/C.WORKER).write_bytes(b'changed')
    elif fault=='projection_bytes':(root/'control/projection.json').write_bytes(b'{}')
    elif fault=='host':plan['host']['kernel']='other'
    elif fault=='execution':plan['execution']['worker_argv_template'][5]='diagnostic'
    elif fault=='clock':plan['phase_deadline_ns']+=1
    elif fault=='observer':plan['observer_contract_sha256']='0'*64
    elif fault=='profile':(root/'source'/C.PROFILE).write_bytes(b'{}')
    if fault in ('host','execution','clock','observer'):
        (root/'control/plan.json').write_bytes(C.encode(plan));expected=C.digest(C.encode(plan))
    # Native directory/mode/bootstrap predicates are explicit fixtures in this
    # contract test; the unchanged underlying guards have separate regressions.
    checks=[]
    monkeypatch.setattr(K.T,'check_projection',lambda *a:checks.append('projection'))
    monkeypatch.setattr(K.T,'verify_bootstrap',lambda *a:'0'*64 if fault=='bootstrap' else '3'*64)
    if fault=='none':
        source,p,result,projection=K.control_inputs(root,expected,request)
        assert result==plan and source==root/'source' and checks==['projection']
    else:
        with pytest.raises((P.ProtocolError,ValueError,KeyError)):K.control_inputs(root,expected,request)


@pytest.mark.parametrize('fault',['none','native_target','runtime_version','module_origin','tokenizer_origin','cuda',
    'special_ids','configuration','input_tokens','decoded_text'])
def test_actual_tokenizer_phase_with_explicit_module_doubles(tmp_path,good_carrier,monkeypatch,fault):
    root=tmp_path/'projection';evidence=root/'evidence';evidence.mkdir(parents=True)
    for name,raw in good_carrier.items():
        target=evidence/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    output=root/'output';output.mkdir();runtime=root/'capsule/runtime'
    p=C.load_profile(ROOT);plan=C.parse(good_carrier['plan.json'])
    import rfc8785 as genuine_jcs
    dump=genuine_jcs.dumps
    loader_calls=[];tokenizer_calls=[]
    class ToyTokenizer:
        __module__='q2_explicit_tokenizer_fixture'
        is_fast=True;bos_token_id=1;eos_token_id=2;pad_token_id=2
        def apply_chat_template(self,messages,*,tokenize,add_generation_prompt):
            assert tokenize is True and add_generation_prompt is True
            tokenizer_calls.append('input')
            return [1,999] if fault=='input_tokens' else [1,10+len(messages[1]['content'])]
        def decode(self,ids,*,skip_special_tokens,clean_up_tokenization_spaces):
            assert skip_special_tokens is True and clean_up_tokenization_spaces is False
            tokenizer_calls.append('decode')
            return 'wrong' if fault=='decoded_text' else ' synthetic exact value\n'
    class AutoTokenizer:
        @staticmethod
        def from_pretrained(path,**kwargs):
            assert path==str(root/'capsule/model') and kwargs=={'local_files_only':True,'trust_remote_code':False,'use_fast':True}
            loader_calls.append(path);tok=ToyTokenizer()
            if fault=='special_ids':tok.pad_token_id=7
            return tok
    class GenerationConfig:
        def __init__(self,**kwargs):assert kwargs['disable_compile'] is True
        def to_dict(self):
            cfg=copy.deepcopy(F.FIXED_CONFIGURATION)
            if fault=='configuration':cfg['max_new_tokens']=31
            return cfg
    modules={name:types.ModuleType(name) for name in ('rfc8785','transformers','torch','tokenizers','q2_explicit_tokenizer_fixture')}
    for name,m in modules.items():
        m.__file__=str(runtime/'lib/python3.11/site-packages'/name/'__init__.py')
    modules['rfc8785'].dumps=dump
    modules['torch'].version=types.SimpleNamespace(cuda='unexpected' if fault=='cuda' else None)
    modules['transformers'].AutoTokenizer=AutoTokenizer;modules['transformers'].GenerationConfig=GenerationConfig
    if fault=='module_origin':modules['torch'].__file__='/outside/torch.py'
    if fault=='tokenizer_origin':modules['q2_explicit_tokenizer_fixture'].__file__='/outside/tokenizer.py'
    for name,m in modules.items():monkeypatch.setitem(sys.modules,name,m)
    def versions(name):return 'wrong' if fault=='runtime_version' and name=='torch' else p['runtime_versions'][name]
    monkeypatch.setattr(K.importlib.metadata,'version',versions)
    def target(*args):
        if fault=='native_target':raise ValueError('synthetic target mismatch')
    monkeypatch.setattr(K.T,'native_target',target)
    if fault=='none':
        result=K.tokenizer_check(root,ROOT,p,plan,output)
        C.validate_json(ROOT,'tokenizer_check',result)
        assert len(loader_calls)==1 and tokenizer_calls.count('input')==tokenizer_calls.count('decode')==150
        assert result['native_origin_reacquired'] is False
        for name in ('groups.json','dataset-manifest.json','token-map.json'):
            assert (output/name).read_bytes()==good_carrier[name]
    else:
        with pytest.raises((P.ProtocolError,ValueError,KeyError)):K.tokenizer_check(root,ROOT,p,plan,output)
        assert list(output.iterdir())==[]
        if fault in ('native_target','runtime_version','module_origin','cuda'):assert loader_calls==[]


def test_synthetic_privileged_io_is_local_and_does_not_patch_shared_modules(monkeypatch, tmp_path):
    S.initialize_modules(ROOT)
    original_chown, original_chmod, original_mkdtemp = os.chown, os.chmod, tempfile.mkdtemp
    actual_uid, actual_gid = os.geteuid(), os.getegid()
    with monkeypatch.context() as patch:
        fs = synthetic_privileged_filesystem(patch, tmp_path)
        assert os.chown is original_chown and os.chmod is original_chmod
        assert tempfile.mkdtemp is original_mkdtemp and os.geteuid() == actual_uid
        for prefix in ('pulse-q2-worker-', 'pulse-q2-worker-bootstrap-'):
            root = Path(S.tempfile.mkdtemp(prefix=prefix, dir='/var/lib'))
            assert root.parent == tmp_path and root in fs.allocated
            S.os.chown(root, 0, 65534); S.os.chmod(root, 0o550)
            payload = root / 'payload.json'
            S.frozen_write(payload, b'{"fixture":"synthetic"}\n')
            assert payload.read_bytes() == b'{"fixture":"synthetic"}\n'
            assert (payload.stat().st_uid, payload.stat().st_gid) == (actual_uid, actual_gid)
            assert stat.S_IMODE(payload.stat().st_mode) == 0o440
            assert (root, 0, 65534) in fs.ownership and (root, 0o550) in fs.modes
            assert (payload, 0, 65534) in fs.ownership
            with pytest.raises((FileExistsError, ValueError)):
                S.frozen_write(payload, b'overwrite is forbidden')
            shutil.rmtree(root)
            assert not root.exists()
    assert S.os is os and S.tempfile is tempfile
    assert S.U.os is os and os.chown is original_chown


@pytest.mark.parametrize('fault', ['outside', 'symlink', 'parent_link', 'owner', 'owner_bool',
                                  'mode', 'temporary_parent', 'temporary_prefix'])
def test_synthetic_privileged_io_rejects_scope_drift(monkeypatch, tmp_path, fault):
    S.initialize_modules(ROOT)
    synthetic_privileged_filesystem(monkeypatch, tmp_path)
    target = tmp_path / 'target'; target.mkdir()
    if fault == 'outside':
        operation = lambda: S.os.chown(tmp_path.parent, 0, 65534)
    elif fault == 'symlink':
        link = tmp_path / 'link'; link.symlink_to(target, target_is_directory=True)
        operation = lambda: S.os.chown(link, 0, 65534)
    elif fault == 'parent_link':
        link = tmp_path / 'link'; link.symlink_to(target, target_is_directory=True)
        (target / 'child').write_bytes(b'fixture')
        operation = lambda: S.os.chown(link / 'child', 0, 65534)
    elif fault == 'owner':
        operation = lambda: S.os.chown(target, 123, 456)
    elif fault == 'owner_bool':
        operation = lambda: S.os.chown(target, False, 65534)
    elif fault == 'mode':
        operation = lambda: S.os.chmod(target, 0o777)
    elif fault == 'temporary_parent':
        operation = lambda: S.tempfile.mkdtemp(prefix='pulse-q2-worker-', dir='/tmp')
    else:
        operation = lambda: S.tempfile.mkdtemp(prefix='other-', dir='/var/lib')
    with pytest.raises(AssertionError, match='fixture_'):
        operation()



# Separate native-platform v1 regressions. All hosts and model responses below
# remain explicitly synthetic; no Actions dispatch, weight loading or native run.
PRESERVED_PLATFORM_V0_SHA256 = {'PULSE_safe_pack_v0/profiles/q2_release_host_worker_verification_v0.json': 'daf0da5abfa0df925deb4c71db5d3f2d17dbb020bbbda99725018874b583ab00', 'schemas/q2_release_host_worker_request_v0.schema.json': '31810ae143c93456455c403f724c410eda547c666c70083da41abd61f0982fd5', 'schemas/q2_release_host_worker_result_v0.schema.json': 'e23e23af0a5115c96870cdf2b1309c30ae99c2166346a62a94c0bed14fa2b01e', 'PULSE_safe_pack_v0/profiles/q2_release_host_tokenizer_verification_v0.json': '82dc4088cea2521a031a63c5476d51434753780f9ad62f02d2ae5cafa053c83f', 'PULSE_safe_pack_v0/tools/verify_q2_release_host_tokenizer_v0.py': '35d10538f3321a006b9ff657db81dea4c6a65f928b763181afd3c644c4ac9efd', 'PULSE_safe_pack_v0/tools/check_q2_release_host_tokenizer_v0.py': 'ae1d4ebd38e05c8d50ba4f330f98c8976bc19be756001ecf2e714620b8b1f99b', 'PULSE_safe_pack_v0/tools/check_q2_release_host_worker_protocol_v0.py': '68f4ba73adecb97a8025d8af33873ea01e2d7ba2567a36bc6accff774569c1ae', 'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py': '37c932272da1579c3e1bf821fb5bde671ae756ede99aceb7deac58c85ee4b172', 'PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py': '8ba3bc7fbd922883f9db64ba53301603e8846bd4d2015f1ba5dfcf28e1d7a2da'}

@pytest.mark.parametrize('path,expected', sorted(PRESERVED_PLATFORM_V0_SHA256.items()))
def test_platform_v1_preserves_strict_and_historical_sources(path,expected):
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected


@pytest.fixture(scope='module')
def git_source_v1(tmp_path_factory):
    p=tmp_path_factory.mktemp('q2-local-native-v1-source')/'repo'
    return p,source_fixture(p,platform_contract=C.REVIEWED_PLATFORM)


@pytest.fixture(scope='module')
def native_v1_carrier(tmp_path_factory):
    return carrier_fixture(tmp_path_factory.mktemp('q2-native-v1-carrier'),platform_contract=C.REVIEWED_PLATFORM)


def test_platform_v1_is_explicit_and_legacy_remains_default(git_source_v1):
    source,revision=git_source_v1
    old=C.load_profile(source)
    p=C.load_profile(source,platform_contract=C.REVIEWED_PLATFORM)
    assert len(old['source_paths'])==39 and len(p['source_paths'])==42
    assert old['native_requirements']==old['archived_platform_requirements']
    assert p['archived_platform_requirements']==old['archived_platform_requirements']
    assert p['native_requirements']['runner_image']=='20261012.334.1'
    assert p['archived_platform_requirements']['runner_image']=='20261004.327.1'
    assert C.request_for(source,revision)['schema_version']=='q2_release_host_worker_request_v0'
    for contract,schema_path in [(C.STRICT_PLATFORM,C.REQUEST_SCHEMA),(C.REVIEWED_PLATFORM,C.REQUEST_SCHEMA_V1)]:
        value=C.request_for(source,revision,platform_contract=contract);raw=C.encode(value)
        Draft202012Validator(C.parse((source/schema_path).read_bytes())).validate(value)
        assert C.check_request(source,raw,C.digest(raw),revision)==value
        assert C.source_closure(source,revision,C.load_profile(source,platform_contract=contract)['source_paths'])


@pytest.mark.parametrize('value', [None,True,1,'','latest','reviewed_native_platform_v2',{},[]])
def test_platform_v1_no_implicit_profile_or_fallback(value):
    with pytest.raises(P.ProtocolError):C.load_profile(ROOT,platform_contract=value)


@pytest.mark.parametrize('schema,contract', [
    ('q2_release_host_worker_request_v0',C.REVIEWED_PLATFORM),
    ('q2_release_host_worker_request_v1',C.STRICT_PLATFORM),
    ('q2_release_host_worker_request_v2',C.REVIEWED_PLATFORM),
    (None,C.REVIEWED_PLATFORM),('q2_release_host_worker_request_v1',None),
    (True,C.REVIEWED_PLATFORM),('q2_release_host_worker_request_v1','latest')])
def test_platform_v1_schema_contract_crossovers_reject(schema,contract):
    raw=C.encode({'schema_version':schema,'platform_contract':contract})
    with pytest.raises(P.ProtocolError):C.request_contract(raw)


@pytest.mark.parametrize('field', ['schema_version','scope','source_commit','profile_sha256','inputs',
    'workload_sha256','worker_sha256','planned_calls','consent','platform_contract','retention',
    'native_profile_id','authority_effect','production_gate_eligible','active_gate_eligible',
    'same_run_release_authority_eligible','unexpected'])
def test_platform_v1_rehashed_request_changes_reject(field):
    value=C.request_for(ROOT,'c'*40,platform_contract=C.REVIEWED_PLATFORM);value[field]=None;raw=C.encode(value)
    with pytest.raises(P.ProtocolError):C.check_request(ROOT,raw,C.digest(raw),'c'*40)


@pytest.mark.parametrize('field', ['python','bootstrap_python_sha256','os','architecture','runner_image','kernel','libc'])
@pytest.mark.parametrize('fault', ['changed','missing','boolean'])
def test_platform_v1_each_host_field_is_mandatory(field,fault):
    p=C.load_profile(ROOT,platform_contract=C.REVIEWED_PLATFORM);host=copy.deepcopy(p['native_requirements'])
    if fault=='missing':del host[field]
    else:host[field]=False if fault=='boolean' else ['wrong'] if field=='libc' else 'wrong'
    with pytest.raises(P.ProtocolError):C.platform_evaluation(p,host)


def test_platform_v1_reports_admission_not_identity_or_comparability():
    p=C.load_profile(ROOT,platform_contract=C.REVIEWED_PLATFORM);out=C.platform_evaluation(p,p['native_requirements'])
    assert out['native_requirement_fields_match'] is True
    assert all(out['native_requirement_matches'].values())
    assert out['historical_platform_matches']['runner_image'] is False
    assert sum(out['historical_platform_matches'].values())==6
    assert out['full_archived_platform_match'] is False and out['historical_comparability']=='not_established'
    assert out['q2_comparison_accepted'] is False and out['full_release_host_verified'] is False
    with pytest.raises(P.ProtocolError):C.plan_platform_fields(C.load_profile(ROOT),p['native_requirements'])
    for image in ['20261004.327.1','20261019.335.1','ubuntu-24.04','latest','20261012.334.1\n']:
        host={**p['native_requirements'],'runner_image':image}
        with pytest.raises(P.ProtocolError):C.platform_evaluation(p,host)


@pytest.mark.parametrize('key', ['inputs','bootstrap','retention','worker_limits','claims','archived_platform_requirements',
    'native_requirements','source_paths','native_profile_id','platform_contract','record_type','unexpected'])
def test_platform_v1_coherent_profile_and_schema_tampering_reject(git_source_v1,tmp_path,key):
    source,_=git_source_v1;fixture=tmp_path/'source';shutil.copytree(source,fixture)
    p=C.parse((fixture/C.PROFILE_V1).read_bytes());p[key]=None
    schema=C.parse((fixture/C.REQUEST_SCHEMA_V1).read_bytes());schema['$defs']['profile']['const']=p
    (fixture/C.PROFILE_V1).write_bytes(C.encode(p));(fixture/C.REQUEST_SCHEMA_V1).write_bytes(C.encode(schema))
    with pytest.raises((P.ProtocolError,KeyError,TypeError)):C.load_profile(fixture,platform_contract=C.REVIEWED_PLATFORM)


def test_platform_v1_metadata_cli_requires_separate_version_and_consent(git_source_v1):
    source,revision=git_source_v1
    argv=[sys.executable,'-I','-B',str(source/C.SELF),'--repo-root',str(source),'--source-commit',revision]
    denied=subprocess.run(argv+['--platform-contract',C.REVIEWED_PLATFORM],capture_output=True,timeout=20)
    assert denied.returncode==2 and denied.stdout==b''
    for contract in [C.STRICT_PLATFORM,C.REVIEWED_PLATFORM]:
        run=subprocess.run(argv+['--platform-contract',contract,'--authorize-150-and-actions-retention'],capture_output=True,timeout=20)
        assert run.returncode==0 and run.stderr==b''
        assert run.stdout==C.encode(C.request_for(source,revision,platform_contract=contract))
    assert subprocess.check_output(['/usr/bin/git','remote'],cwd=source)==b''


@pytest.mark.parametrize('fault',['none','wrong_digest','mixed_version','dirty_profile','dirty_schema','dirty_checker','duplicate'])
def test_platform_v1_stdlib_guard_selects_only_committed_extent(git_source_v1,tmp_path,monkeypatch,fault):
    original,revision=git_source_v1;source=tmp_path/'fixture';shutil.copytree(original,source)
    env=owner_environment(source,revision,tmp_path,platform_contract=C.REVIEWED_PLATFORM)
    fs=synthetic_privileged_filesystem(monkeypatch,tmp_path);monkeypatch.setattr(S.os,'geteuid',lambda:0)
    if fault=='wrong_digest':env[S.DIGEST]='0'*64
    elif fault=='mixed_version':
        obj=C.parse(env[S.REQUEST].encode());obj['platform_contract']=C.STRICT_PLATFORM
        env[S.REQUEST]=C.encode(obj).decode();env[S.DIGEST]=C.digest(env[S.REQUEST].encode())
    elif fault.startswith('dirty_'):
        name={'dirty_profile':C.PROFILE_V1,'dirty_schema':C.REQUEST_SCHEMA_V1,'dirty_checker':C.CHECKER}[fault]
        (source/name).write_bytes(b'raise AssertionError("must not execute")\n')
    elif fault=='duplicate':
        env[S.REQUEST]='{"schema_version":"other",'+env[S.REQUEST][1:]
        env[S.DIGEST]=C.digest(env[S.REQUEST].encode())
    if fault!='none':
        with pytest.raises(ValueError):S.bootstrap_sources(source,env)
        assert fs.allocated==[]
    else:
        snapshot=S.bootstrap_sources(source,env)
        try:
            expected=C.load_profile(source,platform_contract=C.REVIEWED_PLATFORM)['source_paths']
            assert len(expected)==42
            assert sorted(p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file())==expected
            assert all((snapshot/n).read_bytes()==(source/n).read_bytes() for n in expected)
        finally:shutil.rmtree(snapshot)


@pytest.mark.parametrize('unknown',[False,True])
def test_platform_v1_complete_carrier_and_valid_metric_fail(tmp_path,unknown):
    data=carrier_fixture(tmp_path,unknown=unknown,platform_contract=C.REVIEWED_PLATFORM)
    result=K.verify_carrier(ROOT,data,C.digest(data['result.json']))
    assert len(data)==618 and result['record_type']=='q2_worker_carrier_reconstruction_v1'
    assert result['evidence_reconstructed'] is True
    assert result['platform_evaluation']['full_archived_platform_match'] is False
    assert result['platform_evaluation']['historical_comparability']=='not_established'
    assert C.parse(data['result.json'])['metric_pass'] is (not unknown)
    assert C.parse(data['reduction-check.json'])['builder_exit']==int(unknown)
    assert C.parse(data['reduction-check.json'])['checker_exit']==0
    assert all(result[k] is False for k in ['native_origin_reacquired','tokenization_reperformed','metric_recomputed'])


@pytest.mark.parametrize('field', ['native_profile_id','observed_platform','native_requirements','archived_platform_requirements',
    'native_requirement_matches','historical_platform_matches','native_requirement_fields_match',
    'full_archived_platform_match','historical_comparability','q2_comparison_accepted','full_release_host_verified',
    'authority_effect','production_gate_eligible','active_gate_eligible','same_run_release_authority_eligible','unexpected'])
@pytest.mark.parametrize('target',['plan','result'])
def test_platform_v1_independent_reconstruction_rejects_rehashed_claims(native_v1_carrier,field,target):
    data=dict(native_v1_carrier);value=C.parse(data[target+'.json']);evaluation=value['platform_evaluation']
    evaluation[field]=(False if field=='native_requirement_fields_match' else
                       True if field not in ('authority_effect','historical_comparability') else 'accepted')
    data[target+'.json']=C.encode(value)
    final=C.parse(data['result.json'])
    final['evidence_inventory']=C.inventory({k:v for k,v in data.items() if k!='result.json'})
    data['result.json']=C.encode(final)
    with pytest.raises((P.ProtocolError,ValueError,KeyError)):K.verify_carrier(ROOT,data,C.digest(data['result.json']))


@pytest.mark.parametrize('fault',['plan_downgrade','result_downgrade','legacy_request','missing_plan_evaluation','missing_result_evaluation'])
def test_platform_v1_cross_version_carrier_rejects(native_v1_carrier,fault):
    data=dict(native_v1_carrier)
    if fault=='legacy_request':data['request.json']=C.encode(C.request_for(ROOT,'c'*40))
    else:
        target='plan' if 'plan' in fault else 'result';obj=C.parse(data[target+'.json'])
        if 'missing' in fault:del obj['platform_evaluation']
        elif target=='plan':obj['record_type']='q2_worker_execution_plan_v0'
        else:obj['schema_version']='q2_release_host_worker_result_v0'
        data[target+'.json']=C.encode(obj)
    final=C.parse(data['result.json']);final['evidence_inventory']=C.inventory({k:v for k,v in data.items() if k!='result.json'})
    data['result.json']=C.encode(final)
    with pytest.raises((P.ProtocolError,ValueError,KeyError)):K.verify_carrier(ROOT,data,C.digest(data['result.json']))


@pytest.mark.parametrize('fault',['none','input_check','worker','tokenizer_check','reduction_check','cleanup','recheck','publication','final_verifier'])
def test_platform_v1_full_supervisor_custody_and_failures(monkeypatch,tmp_path,git_source_v1,fault):
    source,env,roots,phases,downloads,remove=full_supervisor_fixture(monkeypatch,tmp_path,git_source_v1,fault,
                                                                 platform_contract=C.REVIEWED_PLATFORM)
    try:
        output=tmp_path/'q2-native-worker'
        if fault=='none':
            result=S.supervise(source,environment=env)
            assert result['schema_version']=='q2_release_host_worker_result_v1'
            assert result['platform_evaluation']['native_requirement_fields_match'] is True
            assert result['platform_evaluation']['full_archived_platform_match'] is False
            assert result['q2_comparison_accepted'] is False and result['full_release_host_verified'] is False
            receipt=C.parse((output/'receipt.json').read_bytes())
            data=K.read_carrier(output/'evidence.zip',receipt['archive_sha256'])
            checked=K.verify_carrier(source,data,receipt['result_sha256'])
            assert checked['platform_evaluation']==result['platform_evaluation']
            assert phases==list(C.PHASES) and len(downloads)==6
        else:
            with pytest.raises((P.ProtocolError,ValueError,OSError)):S.supervise(source,environment=env)
            assert not (output/'receipt.json').exists() and not (output/'evidence.zip').exists()
            rejected=C.parse((output/'failure.json').read_bytes())
            assert rejected['accepted_native_result'] is False and rejected['authority_effect']=='none'
            assert rejected['cleanup']==('not_verified' if fault=='cleanup' else 'verified_removed')
        if fault!='cleanup':assert all(not p.parent.exists() for p in roots)
    finally:
        for p in roots:
            if p.parent.exists():remove(p.parent)


@pytest.mark.parametrize('field',['python','bootstrap_python_sha256','os','architecture','runner_image','kernel','libc'])
def test_platform_v1_host_mismatch_stops_before_acquisition(monkeypatch,tmp_path,git_source_v1,field):
    source,env,roots,phases,downloads,_=full_supervisor_fixture(monkeypatch,tmp_path,git_source_v1,'none',
                                                             platform_contract=C.REVIEWED_PLATFORM)
    # An explicitly synthetic observation tests orchestration order, not the kernel.
    def wrong_host(env,p):
        observed=copy.deepcopy(p['native_requirements']);observed[field]='not-allowed';return observed
    monkeypatch.setattr(S.U,'host_record',wrong_host)
    with pytest.raises(P.ProtocolError):S.supervise(source,environment=env)
    assert downloads==[] and phases==[] and roots==[]
    assert not (tmp_path/'q2-native-worker/evidence.zip').exists()




def test_platform_v1_request_binds_selected_profile_and_preserves_default_bytes():
    # Captured from the unmodified baseline constructor using a synthetic revision.
    strict = C.encode(C.request_for(ROOT, 'c' * 40))
    assert len(strict) == 2762
    assert C.digest(strict) == '9b5910eed0b36682d0807196508e81fe545d0273c92c1087c6f61619c2a14f4a'
    value = C.request_for(ROOT, 'c' * 40, platform_contract=C.REVIEWED_PLATFORM)
    selected_hash = hashlib.sha256((ROOT / C.PROFILE_V1).read_bytes()).hexdigest()
    old_hash = hashlib.sha256((ROOT / C.PROFILE).read_bytes()).hexdigest()
    assert value['profile_sha256'] == selected_hash != old_hash
    value['profile_sha256'] = old_hash
    raw = C.encode(value)
    with pytest.raises(P.ProtocolError, match='request_contract_changed'):
        C.check_request(ROOT, raw, C.digest(raw), 'c' * 40)


@pytest.mark.parametrize('fault', ['none','plan_digest','request_digest','plan_noncanonical','source_bytes','projection_bytes',
    'host','execution','clock','observer','profile','bootstrap'])
def test_platform_v1_actual_phase_control_bindings(tmp_path,native_v1_carrier,monkeypatch,fault):
    # Reuse the actual native-phase entry precondition test, with the v1 source
    # extent and carrier. Only filesystem/archived bootstrap observations are
    # test doubles, as in the existing v0 version of this test.
    test_checker_preconditions_and_projection_bindings(tmp_path,native_v1_carrier,monkeypatch,fault)


@pytest.mark.parametrize('target', ['plan','result'])
@pytest.mark.parametrize('field', ['observed_platform','native_requirements','archived_platform_requirements',
    'native_requirement_matches','historical_platform_matches','native_requirement_fields_match',
    'full_archived_platform_match','historical_comparability','q2_comparison_accepted','full_release_host_verified'])
def test_platform_v1_checker_recomputes_even_without_schema_predicate(native_v1_carrier,monkeypatch,target,field):
    # Isolate the independently recomputed semantic comparison. Production still
    # applies both the closed schema and this check; no repository guard changes.
    data = dict(native_v1_carrier)
    value = C.parse(data[target + '.json'])
    evaluation = value['platform_evaluation']
    if isinstance(evaluation[field], dict):
        evaluation[field]['runner_image'] = 'substituted' if field.endswith('platform') or field.endswith('requirements') else True
        if field == 'native_requirement_matches':
            evaluation[field]['runner_image'] = False
    elif isinstance(evaluation[field], bool):
        evaluation[field] = not evaluation[field]
    else:
        evaluation[field] = 'established'
    data[target + '.json'] = C.encode(value)
    final = C.parse(data['result.json'])
    final['plan_sha256'] = C.digest(data['plan.json'])
    final['evidence_inventory'] = C.inventory({k:v for k,v in data.items() if k != 'result.json'})
    data['result.json'] = C.encode(final)
    validate = C.validate_json
    def shared_schema(source, definition, obj):
        if definition not in ('plan','result'):
            return validate(source, definition, obj)
    monkeypatch.setattr(C, 'validate_json', shared_schema)
    with pytest.raises(P.ProtocolError, match=target + '_platform_evaluation'):
        K.verify_carrier(ROOT, data, C.digest(data['result.json']))


@pytest.mark.parametrize('count', [39,41,43])
def test_platform_v1_schema_rejects_wrong_source_extent(native_v1_carrier,count):
    plan = C.parse(native_v1_carrier['plan.json'])
    rows = plan['source_bindings']
    plan['source_bindings'] = rows[:count] if count <= len(rows) else rows + [rows[-1]]
    with pytest.raises(P.ProtocolError, match='worker_schema_rejected'):
        C.validate_json(ROOT, 'plan', plan)




def test_platform_v1_phase_selection_and_digest_use_one_held_request(tmp_path,native_v1_carrier,monkeypatch):
    root,plan=checker_projection_fixture(tmp_path,native_v1_carrier)
    held=C.held_read;reads=[]
    def read(path,*args,**kwargs):
        if path==root/'control/request.json':
            reads.append(path)
            assert len(reads)==1, 'Request must not change between selection and validation'
        return held(path,*args,**kwargs)
    monkeypatch.setattr(C,'held_read',read)
    monkeypatch.setattr(K.T,'check_projection',lambda *args:None)
    monkeypatch.setattr(K.T,'verify_bootstrap',lambda *args:'3'*64)
    _,p,observed,_=K.control_inputs(root,C.digest(C.encode(plan)),plan['request_sha256'])
    assert p['platform_contract']==C.REVIEWED_PLATFORM and observed==plan and len(reads)==1

if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
