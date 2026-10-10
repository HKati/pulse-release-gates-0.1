"""Workflow, transport and source-closure regressions; no GitHub actions run."""
import copy
from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io as bytesio
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import threading
import urllib.error
from types import SimpleNamespace

import pytest
import yaml

from test_q2_release_intake_v0 import ROOT, IO, LOAD, metadata_request, zipped


def workflow(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_bytes(),Loader=yaml.BaseLoader)


def test_two_existing_gate_steps_are_the_only_q2_credential_consumers():
    doc=workflow('pulse_ci.yml');steps=doc['jobs']['pulse']['steps']
    expected={'PULSE_Q2_INTAKE_REQUEST':'${{ github.event.inputs.q2_intake_request }}',
              'PULSE_Q2_INTAKE_REQUEST_SHA256':'${{ github.event.inputs.q2_intake_request_sha256 }}',
              'PULSE_Q2_TRANSPORT_TOKEN':'${{ github.token }}'}
    selected=('release-grade record current-run required-gate evidence',
              'release-grade build non-stubbed prod candidate status')
    assert len(doc['jobs'])==8 and sum(len(j['steps']) for j in doc['jobs'].values())==147
    assert [s['name'] for s in steps if any(k.startswith('PULSE_Q2_') for k in s.get('env',{}))]==list(selected)
    for s in steps:
        scoped={k:v for k,v in s.get('env',{}).items() if k.startswith('PULSE_Q2_')}
        assert scoped==(expected if s['name'] in selected else {})
        assert 'inputs.q2_intake_request' not in s.get('run','')
    assert doc['jobs']['pulse']['permissions']['actions']=='read'
    inputs=doc['on']['workflow_dispatch']['inputs']
    assert set(inputs)=={'strict_external_evidence','llamaguard_evidence_mode','q2_intake_request','q2_intake_request_sha256'}
    for key in ('q2_intake_request','q2_intake_request_sha256'):
        assert inputs[key]['type']=='string' and inputs[key]['required']=='false' and inputs[key]['default']==''
    setup=next(s for s in steps if s.get('uses','').startswith('actions/setup-python@'))
    assert setup['with']['python-version']=='3.11.16'
    names=[s['name'] for s in steps]
    upload=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('actions/upload-artifact@')
                and 'llamaguard-current-run-' in s.get('with',{}).get('name',''))
    assert upload<names.index(selected[0])<names.index(selected[1])
    diagnostics=[s for s in steps[names.index(selected[0])+1:] if s.get('uses','').startswith('actions/upload-artifact@') and 'always()' in s.get('if','')]
    assert diagnostics


def test_reference_metadata_fields_are_data_in_both_existing_jobs():
    doc=workflow('pulsemech_compute_whole_runtime_observation_reference.yml')
    assert set(doc['jobs'])=={'acquisition','verification'}
    for field in ('q2_intake_request','q2_intake_request_sha256'):
        assert doc['on']['workflow_dispatch']['inputs'][field]['required']=='true'
        assert doc['on']['workflow_dispatch']['inputs'][field]['type']=='string'
        for job in doc['jobs'].values():
            assert job['env']['PULSE_'+field.upper()]=='${{ inputs.'+field+' }}'
            assert all('inputs.'+field not in step.get('run','') for step in job['steps'])
    assert all('PULSE_Q2_TRANSPORT_TOKEN' not in job.get('env',{}) for job in doc['jobs'].values())


def test_tools_smoke_setup_pins_the_actual_replay_requirement():
    doc = workflow('pulse_ci.yml')
    profile = json.loads((ROOT / IO.PROFILE_PATH).read_bytes())
    version = '.'.join(map(str, profile['replay_environment']['python']))
    for job_name in ('pulse', 'tools-tests'):
        setups = [step for step in doc['jobs'][job_name]['steps']
                  if step.get('uses', '').startswith('actions/setup-python@')]
        assert len(setups) == 1
        assert setups[0]['with']['python-version'] == version
    assert doc['jobs']['tools-tests']['timeout-minutes'] == '120'
    assert all('continue-on-error' not in step for step in doc['jobs']['tools-tests']['steps'])


def _run_actual_tools_smoke_step(tmp_path, interpreter, profile_fault=None):
    """Run the committed shell step with one harmless manifest entry and real Python."""
    profile_path = tmp_path / IO.PROFILE_PATH
    profile_path.parent.mkdir(parents=True)
    raw = (ROOT / IO.PROFILE_PATH).read_bytes()
    if profile_fault == 'malformed':
        raw = b'not-json: PRIVATE_PROFILE_CONTENT_MUST_NOT_BE_PRINTED'
    elif profile_fault == 'unicode':
        profile = json.loads(raw)
        profile['replay_environment']['unicode'] = '99.0.0'
        raw = IO.encode(profile)
    if profile_fault != 'missing':
        profile_path.write_bytes(raw)
    (tmp_path / 'ci').mkdir()
    (tmp_path / 'ci/tools-tests.list').write_text('tests/smoke_sentinel.py\n')
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/smoke_sentinel.py').write_text(
        "from pathlib import Path\nPath('smoke_reached').write_text('executed')\n")
    commands = tmp_path / 'commands'
    commands.mkdir()
    (commands / 'python').symlink_to(Path(interpreter).resolve())
    steps = workflow('pulse_ci.yml')['jobs']['tools-tests']['steps']
    source = next(step['run'] for step in steps
                  if step.get('name', '').strip() == 'Run exporter + release-authority smoke tests')
    environment = {'PATH': str(commands) + os.pathsep + os.defpath,
                   'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    return subprocess.run(['bash', '-c', source], cwd=tmp_path, env=environment,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)


@pytest.mark.parametrize('fault', [None, 'missing', 'malformed', 'unicode'],
                         ids=['exact-runtime', 'missing-profile', 'malformed-profile', 'unicode-mismatch'])
def test_actual_tools_smoke_step_checks_runtime_before_compiling_or_running(tmp_path, fault):
    result = _run_actual_tools_smoke_step(tmp_path, sys.executable, fault)
    if fault is None:
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Q2 smoke replay environment verified:' in result.stdout
        assert (tmp_path / 'smoke_reached').read_text() == 'executed'
    else:
        assert result.returncode == 1, result.stdout + result.stderr
        assert '::error::Q2 smoke replay environment' in result.stdout
        assert not (tmp_path / 'smoke_reached').exists()
        assert not (tmp_path / 'tests/__pycache__').exists()
        assert 'Traceback' not in result.stderr
        assert 'PRIVATE_PROFILE_CONTENT_MUST_NOT_BE_PRINTED' not in result.stdout + result.stderr


def test_actual_other_python_stops_the_smoke_step_before_the_manifest(tmp_path):
    interpreter = shutil.which('python3.12')
    if interpreter is None:
        pytest.skip('separate Python 3.12 interpreter not installed')
    result = _run_actual_tools_smoke_step(tmp_path, interpreter)
    assert result.returncode == 1, result.stdout + result.stderr
    assert '::error::Q2 smoke replay environment mismatch:' in result.stdout
    assert not (tmp_path / 'smoke_reached').exists()
    assert not (tmp_path / 'tests/__pycache__').exists()
    assert 'Traceback' not in result.stderr


def test_full_current_source_closure_and_all_candidate_pin_families_agree():
    from test_pulsemech_compute_whole_runtime_observation_v0 import BUILDER,PLAN_CHECKER,VERIFIER,CAPTURER
    candidate=IO.PACK+'tools/build_release_grade_candidate_status_v0.py'
    for module in (BUILDER,PLAN_CHECKER):
        assert len(module.SOURCE_ROLES)==60 and len(module._CURRENT_SOURCE_ROLES)==79
        assert len(module._LOCAL_R2_SOURCE_ROLES)==87 and len(module.PUBLIC_R2_SOURCE_ROLES)==92
        paths={p for _,p in module._CURRENT_SOURCE_ROLES}
        assert set(IO.SOURCE_PATHS)<=paths
        expected=module._sha1_git_blob((ROOT/candidate).read_bytes())
        assert all(pins[candidate]==expected for pins in
                   (module._RECORDED_SEMANTIC_PINS,module._FLOOR_SOURCE_PINS,module._RESIDUAL_SOURCE_PINS))
        for path,pin in module._Q2_SOURCE_PINS.items():
            assert pin==module._sha1_git_blob((ROOT/path).read_bytes())
        assert module.EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1==module._sha1_git_blob((ROOT/module.SUBJECT_WORKFLOW_PATH).read_bytes())
    assert dict(VERIFIER._D3_SOURCE_PINS)==CAPTURER._D3_SOURCE_PINS
    assert dict(VERIFIER._LOCAL_R2_RECORDED_INPUT_SOURCES)[IO.PACK+'tools/run_recorded_required_gate_evaluations_v0.py']==BUILDER._sha1_git_blob((ROOT/IO.PACK/'tools/run_recorded_required_gate_evaluations_v0.py').read_bytes())


@pytest.mark.parametrize('side',['builder','checker'])
@pytest.mark.parametrize('fault',['none','digest','source','event','selection','future-id','extra-root'])
def test_plan_projection_binds_exact_prospective_request(side,fault):
    from test_pulsemech_compute_whole_runtime_observation_v0 import BUILDER,PLAN_CHECKER
    module=BUILDER if side=='builder' else PLAN_CHECKER
    request=metadata_request();pin=None
    if fault=='source':request['evaluation_identity']['source_commit']='b'*40
    elif fault=='event':request['evaluation_identity']['event']='pull_request'
    elif fault=='selection':request['selection']['sha256']='b'*64
    elif fault=='future-id':request['evaluation_identity']['run_id']='1234'
    elif fault=='extra-root':request['command']='touch /tmp/should-never-run'
    raw=IO.encode(request);pin='0'*64 if fault=='digest' else IO.digest(raw)
    sources={path:SimpleNamespace(data=(ROOT/path).read_bytes()) for path in
             (IO.PROFILE_PATH,IO.REQUEST_SCHEMA,IO.SELECTION_PATH)}
    if fault!='none':
        with pytest.raises((module.PlanError,ValueError)):
            module._q2_request_projection(sources,'a'*40,'observed',raw.decode(),pin)
    else:
        result=module._q2_request_projection(sources,'a'*40,'observed',raw.decode(),pin)
        assert result=={'q2_intake_request':raw.decode(),'q2_intake_request_sha256':pin}


def test_tools_registration_is_163_and_does_not_expand_pytest_manifest():
    modules=['tests/test_'+n+'.py' for n in ('q2_release_intake_v0','q2_release_subject_binding_v0',
                                           'q2_required_gate_integration_v0','q2_hosted_intake_workflow_v0',
                                           'q2_capsule_publication_v0','q2_negative_intake_verification_v0')]
    entries=[x.strip() for x in (ROOT/'ci/tools-tests.list').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    assert len(entries)==len(set(entries))==163
    pytest_entries=(ROOT/'ci/pytest-tests.list').read_text().splitlines()
    assert all(entries.count(name)==1 and name not in pytest_entries for name in modules)


def test_negative_block_cannot_be_hidden_by_historical_fixture_restoration():
    from test_pulsemech_compute_whole_runtime_observation_v0 import _workflow_before_q2_smoke_runtime
    raw = (ROOT / '.github/workflows/pulse_ci.yml').read_bytes()
    assert raw.count(b'--verify-recorded-negative') == 1
    assert b'--verify-recorded-negative' not in _workflow_before_q2_smoke_runtime(raw)
    with pytest.raises(AssertionError):
        _workflow_before_q2_smoke_runtime(raw.replace(b'--verify-recorded-negative', b'--wrong-verifier'))


class Response(bytesio.BytesIO):
    status=200
    def __init__(self,raw):super().__init__(raw);self.headers={'Content-Length':str(len(raw))}


def transport_case(monkeypatch,raw=b'controlled-private-payload',location=None):
    requests=[]
    class Opener:
        def open(self,request,timeout):
            assert 0<timeout<=5;requests.append(request)
            if location is not None and len(requests)==1:
                raise urllib.error.HTTPError(request.full_url,302,'private transport exception',{'Location':location},bytesio.BytesIO())
            return Response(raw)
    monkeypatch.setattr(IO.urllib.request,'build_opener',lambda *args:Opener())
    transport=IO.GitHubArtifactTransport('PRIVATE_TRANSPORT_CREDENTIAL')
    return transport,requests,{'archive_size_bytes':len(raw),'archive_sha256':IO.digest(raw)}


def test_transport_token_is_absent_from_signed_redirect(monkeypatch,tmp_path):
    transport,requests,expected=transport_case(monkeypatch,location='https://account.blob.core.windows.net/artifact?sig=PRIVATE_SIGNED_LOCATOR')
    out=tmp_path/'capture.zip';transport.download('HKati/pulse-release-gates-0.1',11472726606,expected,out,IO.Deadline(5))
    assert len(requests)==2
    assert requests[0].get_header('Authorization')=='Bearer PRIVATE_TRANSPORT_CREDENTIAL'
    assert requests[1].get_header('Authorization') is None and requests[1].get_header('Cookie') is None
    assert IO.digest(out.read_bytes())==expected['archive_sha256'] and out.stat().st_mode & 0o777==0o600


@pytest.mark.parametrize('url',['http://a.blob.core.windows.net/x','https://evil.invalid/x',
    'https://blob.core.windows.net.evil.invalid/x','https://user:pass@a.blob.core.windows.net/x',
    'https://a.blob.core.windows.net:444/x','https://a.blob.core.windows.net/x#fragment'])
def test_transport_rejects_untrusted_redirect_without_forwarding_credentials(monkeypatch,tmp_path,url):
    transport,requests,expected=transport_case(monkeypatch,location=url)
    with pytest.raises(IO.IntakeError,match='q2_transport_rejected'):
        transport.download('HKati/pulse-release-gates-0.1',1,expected,tmp_path/'capture.zip',IO.Deadline(5))
    assert len(requests)==1


@pytest.mark.parametrize('fault',['short','long','digest','wrong-repository','bool-artifact'])
def test_transport_input_identity_and_stream_bounds(monkeypatch,tmp_path,fault):
    transport,requests,expected=transport_case(monkeypatch)
    repository='HKati/pulse-release-gates-0.1';identifier=1
    if fault=='short':expected['archive_size_bytes']+=1
    elif fault=='long':expected['archive_size_bytes']-=1
    elif fault=='digest':expected['archive_sha256']='0'*64
    elif fault=='wrong-repository':repository='other/repo'
    else:identifier=True
    with pytest.raises(IO.IntakeError):transport.download(repository,identifier,expected,tmp_path/'out',IO.Deadline(5))


def test_archive_member_count_is_bounded_before_central_directory_parse(tmp_path,monkeypatch):
    path=tmp_path/'crafted.zip';zipped(path,{'a':(b'a',0o100644)})
    raw=bytearray(path.read_bytes());struct.pack_into('<HH',raw,len(raw)-22+8,65534,65534);path.write_bytes(raw)
    monkeypatch.setattr(IO.zipfile,'ZipFile',lambda *a,**k:pytest.fail('Unbounded directory must be rejected before parsing'))
    with pytest.raises(IO.IntakeError,match='q2_archive_limit'):
        IO.Archive(path,maximum_bytes=1000,max_members=2,member_bytes=100,expanded_bytes=200,deadline=IO.Deadline(2))


def test_held_archive_digest_must_match_actual_opened_bytes(tmp_path):
    path=tmp_path/'data.zip';zipped(path,{'a':(b'a',0o100644)})
    with pytest.raises(IO.IntakeError,match='q2_digest_mismatch'):
        IO.Archive(path,maximum_bytes=1000,max_members=2,member_bytes=100,expanded_bytes=200,
                   deadline=IO.Deadline(2),expected_sha256='0'*64)


@pytest.fixture
def acquirer():
    from test_pulsemech_compute_whole_runtime_observation_v0 import ACQUIRER
    return ACQUIRER


@pytest.fixture
def reference_owner(tmp_path, acquirer):
    raw = IO.encode(metadata_request()).decode()
    pin = IO.digest(raw.encode())
    event = {'ref': 'refs/heads/main', 'sender': {'login': 'HKati', 'id': 128643840, 'type': 'User'},
             'repository': {'full_name': acquirer.REPOSITORY},
             'inputs': {'source_commit': 'a' * 40, 'q2_intake_request': raw,
                        'q2_intake_request_sha256': pin}}
    path = tmp_path / 'reference-event.json'
    path.write_bytes(IO.encode(event))
    env = {'GITHUB_REPOSITORY': acquirer.REPOSITORY,
           'GITHUB_WORKFLOW': acquirer.REFERENCE_WORKFLOW_NAME,
           'GITHUB_WORKFLOW_REF': acquirer.REPOSITORY + '/' + acquirer.REFERENCE_WORKFLOW_PATH + '@refs/heads/main',
           'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main',
           'GITHUB_SHA': 'a' * 40, 'GITHUB_WORKFLOW_SHA': 'a' * 40,
           'GITHUB_RUN_ID': '80000000002', 'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1',
           'GITHUB_ACTOR': 'HKati', 'GITHUB_ACTOR_ID': '128643840',
           'GITHUB_TRIGGERING_ACTOR': 'HKati', 'GITHUB_EVENT_PATH': str(path),
           'PULSE_Q2_INTAKE_REQUEST': raw, 'PULSE_Q2_INTAKE_REQUEST_SHA256': pin,
           'GITHUB_TOKEN': 'PRIVATE_INSTALLATION_TOKEN',
           'PULSE_Q2_OWNER_DISPATCH_TOKEN': 'PRIVATE_OWNER_DISPATCH_TOKEN'}
    expected = acquirer._canonical_json_bytes({'ref': 'main', 'inputs': {
        **acquirer.SUBJECT_DISPATCH_INPUTS, 'q2_intake_request': raw, 'q2_intake_request_sha256': pin}})
    return SimpleNamespace(env=env, event=event, event_path=path, expected_request=expected)


def test_owner_secret_is_scoped_to_one_existing_reference_step(acquirer):
    doc = workflow('pulsemech_compute_whole_runtime_observation_reference.yml')
    found = []
    for job_id, job in doc['jobs'].items():
        assert acquirer.OWNER_DISPATCH_TOKEN_ENV not in job.get('env', {})
        for step in job['steps']:
            if acquirer.OWNER_DISPATCH_TOKEN_ENV in step.get('env', {}):
                found.append((job_id, step['name']))
                assert step['env'][acquirer.OWNER_DISPATCH_TOKEN_ENV] == '${{ secrets.PULSE_Q2_OWNER_DISPATCH_TOKEN }}'
                assert step['env']['GITHUB_TOKEN'] == '${{ github.token }}'
            assert acquirer.OWNER_DISPATCH_TOKEN_ENV not in step.get('run', '')
    assert found == [('acquisition', 'Acquire exact PULSE CI and Step 3F runs')]
    assert acquirer.OWNER_DISPATCH_TOKEN_ENV not in (ROOT / '.github/workflows/pulse_ci.yml').read_text()
    assert set(doc['on']['workflow_dispatch']['inputs']) == {
        'source_commit', 'q2_intake_request', 'q2_intake_request_sha256'}


@pytest.mark.parametrize('event_ref', ['main', 'refs/heads/main'])
def test_reference_owner_checks_exact_original_request_bytes(acquirer, reference_owner, event_ref):
    f = reference_owner
    f.event['ref'] = event_ref; f.event_path.write_bytes(IO.encode(f.event))
    context = acquirer._reference_context_from_environment(
        source_commit='a' * 40, record_status='observed', environment=f.env)
    assert context.run_id == 80000000002
    fields = acquirer._reference_owner_inputs(source_commit='a' * 40, environment=f.env)
    assert acquirer._canonical_json_bytes({'ref': 'main', 'inputs': fields}) == f.expected_request
    assert f.event_path.read_bytes() == IO.encode(f.event)


@pytest.mark.parametrize('event_ref', ['refs/tags/main', 'refs/heads/other', 'refs/heads/main/', 'main\n', None, ['main']])
def test_reference_event_ref_cannot_select_a_tag_other_branch_or_alias(acquirer, reference_owner, event_ref):
    f = reference_owner
    f.event['ref'] = event_ref; f.event_path.write_bytes(IO.encode(f.event))
    with pytest.raises(acquirer.AcquisitionError, match='q2_reference_event_mismatch'):
        acquirer._reference_owner_inputs(source_commit='a' * 40, environment=f.env)


@pytest.mark.parametrize('fault', [
    'bot-actor', 'other-actor', 'actor-id', 'triggering-actor', 'sender-login', 'sender-id',
    'sender-bool-id', 'sender-type', 'missing-sender', 'repository', 'ref', 'source',
    'request', 'digest', 'extra-input', 'missing-event', 'duplicate-secret-key', 'symlink',
    'hardlink', 'directory', 'oversize', 'digest-env',
])
def test_owner_credential_cannot_authorize_a_different_reference_event(acquirer, reference_owner, fault):
    f = reference_owner
    if fault == 'bot-actor': f.env['GITHUB_ACTOR'] = 'github-actions[bot]'
    elif fault == 'other-actor': f.env['GITHUB_ACTOR'] = 'other'
    elif fault == 'actor-id': f.env['GITHUB_ACTOR_ID'] = '41898282'
    elif fault == 'triggering-actor': f.env['GITHUB_TRIGGERING_ACTOR'] = 'other'
    elif fault == 'sender-login': f.event['sender']['login'] = 'github-actions[bot]'
    elif fault == 'sender-id': f.event['sender']['id'] = 41898282
    elif fault == 'sender-bool-id': f.event['sender']['id'] = True
    elif fault == 'sender-type': f.event['sender']['type'] = 'Bot'
    elif fault == 'missing-sender': del f.event['sender']
    elif fault == 'repository': f.event['repository']['full_name'] = 'other/repo'
    elif fault == 'ref': f.event['ref'] = 'other'
    elif fault == 'source': f.event['inputs']['source_commit'] = 'b' * 40
    elif fault == 'request': f.event['inputs']['q2_intake_request'] += ' '
    elif fault == 'digest': f.event['inputs']['q2_intake_request_sha256'] = 'b' * 64
    elif fault == 'extra-input': f.event['inputs']['run_id'] = '99999999999'
    elif fault == 'missing-event': del f.env['GITHUB_EVENT_PATH']
    elif fault == 'digest-env': f.env['PULSE_Q2_INTAKE_REQUEST_SHA256'] = 'b' * 64
    f.event_path.write_bytes(IO.encode(f.event))
    if fault == 'duplicate-secret-key':
        f.event_path.write_bytes(b'{"PRIVATE_EVENT_PAYLOAD":1,"PRIVATE_EVENT_PAYLOAD":2}')
    elif fault in {'symlink', 'hardlink'}:
        real = f.event_path.with_name('original-event.json'); f.event_path.rename(real)
        if fault == 'symlink': f.event_path.symlink_to(real)
        else: os.link(real, f.event_path)
    elif fault == 'directory': f.event_path.unlink(); f.event_path.mkdir()
    elif fault == 'oversize': f.event_path.write_bytes(b' ' * (512 * 1024 + 1))
    with pytest.raises(acquirer.AcquisitionError) as failure:
        acquirer._reference_owner_inputs(source_commit='a' * 40, environment=f.env)
    diagnostic = acquirer._canonical_json_bytes(acquirer._failure_diagnostic(failure.value, exit_code=1))
    assert b'PRIVATE_' not in diagnostic


@contextmanager
def owner_http_fixture(identity, *, status=200, block_identity=False, declared_size=None):
    """Actual bounded loopback HTTP IO; production host/TLS routing is overridden only here."""
    seen = []
    release = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            seen.append(('GET', self.path, self.headers.get('Authorization'), None))
            if block_identity: release.wait(2)
            self.send_response(status)
            if status == 302: self.send_header('Location', 'https://untrusted.invalid/PRIVATE_REDIRECT')
            self.send_header('Content-Length', str(len(identity) if declared_size is None else declared_size))
            self.end_headers()
            try: self.wfile.write(identity)
            except (BrokenPipeError, ConnectionResetError): pass
        def do_POST(self):
            body = self.rfile.read(int(self.headers['Content-Length']))
            seen.append(('POST', self.path, self.headers.get('Authorization'), body))
            raw = IO.encode({'workflow_run_id': 80000000003,
                'run_url': 'https://api.github.com/repos/HKati/pulse-release-gates-0.1/actions/runs/80000000003',
                'html_url': 'https://github.com/HKati/pulse-release-gates-0.1/actions/runs/80000000003'})
            self.send_response(200); self.send_header('Content-Length', str(len(raw)))
            self.end_headers(); self.wfile.write(raw)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try: yield server.server_address, seen
    finally:
        release.set(); server.shutdown(); server.server_close(); thread.join(3)
        assert not thread.is_alive()


def owner_transport(acquirer, reference_owner, address, monkeypatch, *, timeout=1):
    transport = acquirer.OwnerSubjectDispatchTransport(
        token='PRIVATE_OWNER_DISPATCH_TOKEN', expected_request=reference_owner.expected_request,
        timeout_seconds=timeout)
    def connection(host, port=None):
        assert host == 'api.github.com' and port is None
        return http.client.HTTPConnection(*address, timeout=timeout)
    monkeypatch.setattr(transport, '_connection', connection)
    return transport


def owner_post(acquirer, reference_owner, transport, **changes):
    arguments = dict(method='POST', endpoint=acquirer.SUBJECT_DISPATCH_ENDPOINT,
                     body=reference_owner.expected_request, max_response_bytes=16384)
    return transport.request(**{**arguments, **changes})


def test_owner_dispatch_uses_verified_identity_and_preserves_the_exact_request(acquirer, reference_owner, monkeypatch):
    # Unrelated public profile text does not alter the three authenticated identity fields.
    identity = IO.encode({'login': 'HKati', 'id': 128643840, 'type': 'User', 'bio': 'e\u0301'})
    with owner_http_fixture(identity) as (address, seen):
        transport = owner_transport(acquirer, reference_owner, address, monkeypatch)
        result = owner_post(acquirer, reference_owner, transport)
        assert result.status == 200 and json.loads(result.body)['workflow_run_id'] == 80000000003
        assert [(r[0], r[1]) for r in seen] == [('GET', '/user'), ('POST', '/' + acquirer.SUBJECT_DISPATCH_ENDPOINT)]
        assert all(r[2] == 'Bearer PRIVATE_OWNER_DISPATCH_TOKEN' for r in seen)
        assert seen[1][3] == reference_owner.expected_request
        sent = json.loads(seen[1][3])['inputs']['q2_intake_request']
        assert 'run_id' not in json.loads(sent)['evaluation_identity'] and b'PRIVATE_' not in result.body
        assert transport._token == ''
        with pytest.raises(acquirer.AcquisitionError, match='q2_owner_dispatch_already_used'):
            owner_post(acquirer, reference_owner, transport)
        assert len(seen) == 2


@pytest.mark.parametrize('fault', ['bot', 'wrong-login', 'wrong-id', 'bool-id', 'missing-id',
    'missing-login', 'missing-type', 'duplicate-secret-key', 'invalid-json', 'array', 'expired',
    'forbidden', 'redirect', 'oversize-header', 'oversize-body', 'timeout'])
def test_owner_identity_failures_never_dispatch_or_publish_private_data(acquirer, reference_owner, monkeypatch, fault):
    identity = {'login': 'HKati', 'id': 128643840, 'type': 'User'}
    status = 200; declared = None
    if fault == 'bot': identity.update(login='github-actions[bot]', id=41898282, type='Bot')
    elif fault == 'wrong-login': identity['login'] = 'other'
    elif fault == 'wrong-id': identity['id'] = 12345
    elif fault == 'bool-id': identity['id'] = True
    elif fault.startswith('missing-'): del identity[fault.removeprefix('missing-')]
    elif fault == 'expired': status = 401
    elif fault == 'forbidden': status = 403
    elif fault == 'redirect': status = 302
    raw = IO.encode(identity)
    if fault == 'duplicate-secret-key': raw = b'{"PRIVATE_OWNER_DISPATCH_TOKEN":1,"PRIVATE_OWNER_DISPATCH_TOKEN":2}'
    elif fault == 'invalid-json': raw = b'PRIVATE_RAW_IDENTITY_RESPONSE'
    elif fault == 'array': raw = b'[]'
    elif fault == 'oversize-header': declared = 16385
    elif fault == 'oversize-body': raw = b' ' * 16385
    with owner_http_fixture(raw, status=status, block_identity=fault == 'timeout', declared_size=declared) as (address, seen):
        transport = owner_transport(acquirer, reference_owner, address, monkeypatch, timeout=0.05 if fault == 'timeout' else 1)
        with pytest.raises(acquirer.AcquisitionError) as failure:
            owner_post(acquirer, reference_owner, transport)
        assert len(seen) == 1 and seen[0][0] == 'GET'
        assert transport._token == ''
        diagnostic = acquirer._canonical_json_bytes(acquirer._failure_diagnostic(failure.value, exit_code=1))
        assert b'PRIVATE_' not in diagnostic and b'127.0.0.1' not in diagnostic


@pytest.mark.parametrize('fault', ['provider', 'foreign-repository', 'absolute-url', 'get', 'changed-body', 'download'])
def test_owner_credential_has_no_general_transport_capability(acquirer, reference_owner, monkeypatch, tmp_path, fault):
    transport = acquirer.OwnerSubjectDispatchTransport(
        token='PRIVATE_OWNER_DISPATCH_TOKEN', expected_request=reference_owner.expected_request)
    monkeypatch.setattr(transport, '_connection', lambda *a, **k: pytest.fail('Rejected request reached the network'))
    changes = {}
    if fault == 'provider': changes['endpoint'] = acquirer.PROVIDER_DISPATCH_ENDPOINT
    elif fault == 'foreign-repository': changes['endpoint'] = 'repos/other/repo/actions/workflows/pulse_ci.yml/dispatches'
    elif fault == 'absolute-url': changes['endpoint'] = 'https://api.github.com/' + acquirer.SUBJECT_DISPATCH_ENDPOINT
    elif fault == 'get': changes['method'] = 'GET'
    elif fault == 'changed-body': changes['body'] = reference_owner.expected_request + b' '
    with pytest.raises(acquirer.AcquisitionError, match='q2_owner_dispatch_request_mismatch'):
        if fault == 'download': transport.download_artifact(endpoint='artifacts/1/zip', destination=tmp_path/'out', max_bytes=10)
        else: owner_post(acquirer, reference_owner, transport, **changes)
    assert transport._token == '' and not (tmp_path/'out').exists()


@pytest.mark.parametrize('value', ['', 'a b', 'a\nb', 'a\rb', '\t', '\u00e1', 'a' * 513])
def test_invalid_owner_secret_is_removed_and_never_substituted(acquirer, monkeypatch, value):
    monkeypatch.setenv(acquirer.OWNER_DISPATCH_TOKEN_ENV, value)
    monkeypatch.setenv('GITHUB_TOKEN', 'PRIVATE_FALLBACK_MUST_NOT_BE_USED')
    with pytest.raises(acquirer.AcquisitionError): acquirer._take_owner_dispatch_token()
    assert acquirer.OWNER_DISPATCH_TOKEN_ENV not in os.environ


@pytest.mark.parametrize('fault', ['missing-owner-secret', 'bot-reference', 'wrong-sender', 'same-token', 'token-role-alias'])
def test_real_isolated_cli_rejects_invalid_authorization_without_network(acquirer, reference_owner, tmp_path, fault):
    env = {'PATH': os.environ.get('PATH', os.defpath), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    env.update(reference_owner.env)
    if fault == 'missing-owner-secret': del env[acquirer.OWNER_DISPATCH_TOKEN_ENV]
    elif fault == 'bot-reference': env['GITHUB_ACTOR'] = 'github-actions[bot]'
    elif fault == 'wrong-sender':
        reference_owner.event['sender']['login'] = 'other'
        reference_owner.event_path.write_bytes(IO.encode(reference_owner.event))
    elif fault == 'same-token': env['GITHUB_TOKEN'] = env[acquirer.OWNER_DISPATCH_TOKEN_ENV]
    program = "import runpy,socket,sys\ndef reject(*a,**k): raise RuntimeError('PRIVATE_FORBIDDEN_NETWORK_ATTEMPT')\nsocket.create_connection=reject\nrunpy.run_path(sys.argv[1],run_name='__main__')\n"
    output = tmp_path/'must-not-exist'
    arguments = ['--repository-root', str(ROOT), '--source-commit', 'a'*40,
        '--plan', str(tmp_path/'unused-plan'), '--plan-diagnostic', str(tmp_path/'unused-diagnostic'),
        '--expected-plan-sha256', 'b'*64, '--output-directory', str(output)]
    if fault == 'token-role-alias': arguments += ['--token-env', acquirer.OWNER_DISPATCH_TOKEN_ENV]
    # run_path sees the normal CLI argv; no imported fixture or producer is executed.
    program = program.replace("runpy.run_path(sys.argv[1],run_name='__main__')", "script=sys.argv.pop(1)\nsys.argv[0]=script\nrunpy.run_path(script,run_name='__main__')")
    result = subprocess.run([sys.executable, '-I', '-B', '-c', program, str(ROOT/acquirer.ACQUIRE_PATH), *arguments],
                            env=env, capture_output=True, timeout=15, check=False)
    assert result.returncode == 1 and result.stdout == b''
    diagnostic = json.loads(result.stderr)
    expected = {'missing-owner-secret': 'q2_owner_dispatch_token_missing', 'bot-reference': 'q2_reference_owner_mismatch',
                'wrong-sender': 'q2_reference_event_mismatch', 'same-token': 'q2_owner_dispatch_transport_separation',
                'token-role-alias': 'q2_owner_dispatch_transport_separation'}
    assert diagnostic['error_code'] == expected[fault]
    assert b'PRIVATE_' not in result.stderr and b'Traceback' not in result.stderr
    assert not output.exists()


def test_verified_owner_dispatch_reaches_both_independent_intakes(acquirer, reference_owner, tmp_path, monkeypatch):
    from test_q2_required_gate_integration_v0 import invocation
    subject_root = tmp_path / 'subject'; subject_root.mkdir()
    subject = invocation.__wrapped__(subject_root)
    f = reference_owner
    f.env.update(GITHUB_SHA=subject.sha, GITHUB_WORKFLOW_SHA=subject.sha)
    for key in (LOAD.REQUEST_ENV, LOAD.DIGEST_ENV): f.env[key] = subject.env[key]
    f.event['inputs'] = {'source_commit': subject.sha,
        'q2_intake_request': subject.env[LOAD.REQUEST_ENV],
        'q2_intake_request_sha256': subject.env[LOAD.DIGEST_ENV]}
    f.event_path.write_bytes(IO.encode(f.event))
    fields = acquirer._reference_owner_inputs(source_commit=subject.sha, environment=f.env)
    f.expected_request = acquirer._canonical_json_bytes({'ref': 'main', 'inputs': fields})
    identity = {'login': 'HKati', 'id': 128643840, 'type': 'User'}
    with owner_http_fixture(IO.encode(identity)) as (address, seen):
        transport = owner_transport(acquirer, f, address, monkeypatch)
        result = owner_post(acquirer, f, transport)
        run_id = str(json.loads(result.body)['workflow_run_id'])
        subject.event['inputs'] = json.loads(seen[1][3])['inputs']
        subject.event['sender'] = identity
        subject.event_path.write_bytes(IO.encode(subject.event))
        subject.env['GITHUB_RUN_ID'] = run_id
        subject.env['PULSE_RUN_KEY'] = f'GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    roots = []
    class RejectedArchiveTransport:
        def __init__(self, token): assert token == 'PRIVATE_TEST_TRANSPORT_TOKEN'
        def download(self, repository, identifier, expectation, destination, deadline):
            roots.append(destination.parent)
            destination.write_bytes(b'PRIVATE_DIAGNOSTIC_INVALID_CAPTURE_BYTES')
    monkeypatch.setattr(IO, 'GitHubArtifactTransport', RejectedArchiveTransport)
    for consumer in ('producer', 'admission'):
        result = LOAD.consume(subject.repo, consumer=consumer, environment=subject.env)
        assert result['checks']['request'] is True
        assert result['input_valid'] is False and result['metric_pass'] is None
        assert result['diagnostics'] == ['q2_digest_mismatch']
        assert result['cleanup'] == 'verified_removed'
        assert b'PRIVATE_' not in IO.encode(result)
    assert len(roots) == 2 and roots[0] != roots[1] and all(not p.exists() for p in roots)


def test_owner_secret_is_absent_from_the_actual_plan_checker_child(acquirer, tmp_path, monkeypatch):
    # Process-boundary fixture only: this is not a replacement plan-verification verdict.
    root = tmp_path/'child-boundary'; (root/'tools').mkdir(parents=True)
    script = root/acquirer.PLAN_CHECKER_PATH
    script.write_text("import os,sys\nassert sys.flags.isolated == 1\n"
        "assert not any('PRIVATE_' in value for value in os.environ.values())\n"
        "assert not {'GITHUB_TOKEN','PULSE_Q2_OWNER_DISPATCH_TOKEN','PULSE_Q2_TRANSPORT_TOKEN'} & set(os.environ)\n"
        "sys.stdout.buffer.write(b'{}\\n')\n")
    monkeypatch.setenv('GITHUB_TOKEN', 'PRIVATE_INSTALLATION_TOKEN')
    monkeypatch.setenv('PULSE_Q2_OWNER_DISPATCH_TOKEN', 'PRIVATE_OWNER_DISPATCH_TOKEN')
    monkeypatch.setenv('PULSE_Q2_TRANSPORT_TOKEN', 'PRIVATE_Q2_ARCHIVE_TOKEN')
    acquirer._rerun_plan_checker(root=root, source_commit='a'*40,
        plan_capture=SimpleNamespace(path=tmp_path/'metadata-only-plan.json'),
        diagnostic_capture=SimpleNamespace(path=tmp_path/'diagnostic.json', data=b'{}\n'),
        expected_plan_sha256='b'*64, record_status='example')


@pytest.fixture(scope='module')
def observed_owner_plan(tmp_path_factory):
    import importlib.util
    import test_pulsemech_compute_whole_runtime_observation_v0 as whole
    f = whole.source_fixture.__wrapped__(tmp_path_factory)
    built = whole.cli(f.root, whole.TOOL_NAMES[0], ['--repository-root', f.root,
        '--source-commit', f.sha, '--record-status', 'observed'])
    whole.require_cli_success(built)
    plan = f.directory/'owner-observed-plan.json'; plan.write_bytes(built.stdout)
    pin = whole.digest(built.stdout)
    checked = whole.cli(f.root, whole.TOOL_NAMES[1], ['--repository-root', f.root,
        '--plan', plan, '--expected-source-commit', f.sha, '--expected-plan-sha256', pin,
        '--expected-record-status', 'observed'])
    whole.require_cli_success(checked)
    diagnostic = f.directory/'owner-observed-check.json'; diagnostic.write_bytes(checked.stdout)
    spec = importlib.util.spec_from_file_location('q2_observed_owner_installed_acquirer', f.root/whole.ACQUIRER.ACQUIRE_PATH)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return SimpleNamespace(f=f, module=module, plan=plan, diagnostic=diagnostic, pin=pin,
                           document=json.loads(built.stdout), whole=whole)


@pytest.mark.parametrize('mode', ['owner', 'missing', 'generic', 'wrong-owner', 'request-substitution'])
def test_real_observed_acquirer_uses_only_the_owner_subject_transport(observed_owner_plan, tmp_path, monkeypatch, mode):
    p = observed_owner_plan; module = p.module; whole = p.whole; calls = []
    inputs = p.document['subject_dispatch']['inputs']
    expected = module._canonical_json_bytes({'ref': 'main', 'inputs': inputs})
    reference = SimpleNamespace(expected_request=expected)
    class ObservationTransport:
        def request(self, *, method, endpoint, body, max_response_bytes):
            calls.append((method, endpoint))
            assert method == 'GET', 'The installation transport attempted the Q2 subject POST'
            if endpoint == module.MAIN_REF_ENDPOINT:
                raw = module._canonical_json_bytes({'ref': module.SOURCE_REF,
                    'object': {'type': 'commit', 'sha': p.f.sha}})
                return module.HttpExchange(200, {}, raw, whole.EXAMPLE_START, whole.EXAMPLE_START)
            assert endpoint == f'repos/{module.REPOSITORY}/actions/runs/80000000003'
            raise module.AcquisitionError('synthetic_stop_after_owner_dispatch', stage='test')
        def download_artifact(self, **kwargs): pytest.fail('No archive IO belongs to this authentication probe')
    observer = ObservationTransport()
    context = module.ReferenceContext(**{**whole.reference_context(p.f.sha).__dict__,
        'record_status': 'observed', 'acquisition_id': f'step5c-acquisition:{whole.EXAMPLE_REFERENCE_ID}-1'})
    identity = {'login': 'HKati', 'id': 128643840, 'type': 'User'}
    if mode == 'wrong-owner': identity.update(login='github-actions[bot]', id=41898282, type='Bot')
    output = tmp_path/'absent-acquisition'
    with owner_http_fixture(whole.canonical(identity)) as (address, seen):
        owner = owner_transport(module, reference, address, monkeypatch)
        if mode == 'request-substitution': owner._expected_request += b' '
        provided = None if mode == 'missing' else observer if mode == 'generic' else owner
        with pytest.raises(module.AcquisitionError) as failure:
            module.acquire_observation(repository_root=p.f.root, source_commit=p.f.sha,
                plan_path=p.plan, plan_diagnostic_path=p.diagnostic, expected_plan_sha256=p.pin,
                output_directory=output, record_status='observed', reference_context=context,
                transport=observer, subject_dispatch_transport=provided)
        expected_error = {'owner': 'synthetic_stop_after_owner_dispatch',
            'missing': 'q2_owner_dispatch_transport_required', 'generic': 'q2_owner_dispatch_transport_required',
            'wrong-owner': 'q2_owner_dispatch_identity_mismatch',
            'request-substitution': 'q2_owner_dispatch_request_mismatch'}[mode]
        assert failure.value.code == expected_error
        assert not output.exists() and not list(tmp_path.glob('.step5c-acquisition.*'))
        if mode == 'owner':
            assert [r[0] for r in seen] == ['GET', 'POST']
            assert seen[1][3] == expected and len(calls) == 2
        else:
            assert not any(r[0] == 'POST' for r in seen)
            assert len(calls) == (0 if mode in {'missing', 'generic'} else 1)
        if mode not in {'missing', 'generic'}: assert owner._token == ''


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
