"""Controlled publication regressions. No hosted dispatch, artifact upload or inference."""
import ast
import copy
import ensurepip
import io as bytesio
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import venv
from types import SimpleNamespace
import zipfile

import pytest
import yaml

from test_q2_release_intake_v0 import ROOT, IO, synthetic_case, zipped
from test_q2_required_gate_integration_v0 import invocation
import check_q2_release_capsule_publication_v0 as P
import build_q2_release_capsule_v0 as B


@pytest.fixture
def publication(invocation):
    f = invocation
    for name in P.SOURCE_PATHS:
        target = f.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    for command in (['add', '--all'], ['-c', 'user.name=Offline fixture', '-c', 'user.email=fixture@example.invalid',
                                      '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic publication sources']):
        subprocess.run(['/usr/bin/git', *command], cwd=f.repo, check=True, capture_output=True, timeout=10)
    f.sha = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=f.repo, text=True).strip()
    f.env = {k: v for k, v in f.env.items() if not k.startswith('PULSE_Q2_')}
    f.env.update(GITHUB_SHA=f.sha, GITHUB_WORKFLOW_SHA=f.sha, GITHUB_WORKFLOW='Q2 release capsule publication v0',
                 GITHUB_WORKFLOW_REF=P.REPOSITORY + '/' + P.WORKFLOW + '@refs/heads/main',
                 GITHUB_ACTOR_ID='128643840', PULSE_Q2_PUBLICATION_SOURCE=f.sha,
                 PULSE_Q2_PUBLICATION_TOKEN='PRIVATE_PUBLICATION_CREDENTIAL')
    f.event.update(inputs={'source_commit': f.sha}, sender={'login': 'HKati', 'id': 128643840, 'type': 'User'})
    f.event_path.write_bytes(IO.encode(f.event))
    f.profile = P.load_profile(f.repo)
    return f


def test_publication_binds_all_executed_sources_to_a_real_local_git_fixture(publication):
    f = publication
    binding, sources = P.authorize(f.repo, f.env, f.profile)
    assert binding['source_commit'] == f.sha
    assert {x['path'] for x in sources} == set(P.SOURCE_PATHS)
    assert set(IO.SOURCE_PATHS) < set(P.SOURCE_PATHS)


@pytest.mark.parametrize('field,value', [('GITHUB_ACTOR', 'other'), ('GITHUB_ACTOR_ID', '1'),
    ('GITHUB_TRIGGERING_ACTOR', 'github-actions[bot]'), ('GITHUB_EVENT_NAME', 'pull_request'),
    ('GITHUB_REF', 'refs/tags/main'), ('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_WORKFLOW_SHA', 'b' * 40),
    ('PULSE_Q2_PUBLICATION_SOURCE', 'b' * 40), ('GITHUB_REPOSITORY', 'other/repo'),
    ('GITHUB_WORKFLOW_REF', 'wrong'), ('GITHUB_RUN_ID', '0'), ('RUNNER_ENVIRONMENT', 'self-hosted')])
def test_publication_wrong_invocation_stops_before_transport(publication, monkeypatch, field, value):
    f = publication; f.env[field] = value
    def forbidden(*args): pytest.fail('transport constructed before local authentication')
    monkeypatch.setattr(IO, 'GitHubArtifactTransport', forbidden)
    with pytest.raises(IO.IntakeError): P.supervise(f.repo, 'build', f.env)
    assert not (Path(f.env['RUNNER_TEMP']) / 'q2-capsule-publication').exists()


@pytest.mark.parametrize('fault', ['sender-id', 'sender-type', 'input-extra', 'source-bytes', 'source-mode', 'source-link'])
def test_event_and_dirty_checkout_are_independent_rejections(publication, fault):
    f = publication
    if fault == 'sender-id': f.event['sender']['id'] = '128643840'
    elif fault == 'sender-type': f.event['sender']['type'] = 'Bot'
    elif fault == 'input-extra': f.event['inputs']['url'] = 'https://example.invalid'
    else:
        path = f.repo / P.BUILDER
        if fault == 'source-bytes': path.write_bytes(path.read_bytes() + b'\n')
        elif fault == 'source-mode': path.chmod(path.stat().st_mode ^ 0o111)
        else:
            other = path.with_suffix('.other'); path.rename(other); path.symlink_to(other)
    f.event_path.write_bytes(IO.encode(f.event))
    with pytest.raises(IO.IntakeError): P.authorize(f.repo, f.env, f.profile)


def origin(expected):
    artifact = {'id': expected['artifact_id'], 'name': expected['artifact_name'], 'expired': False,
                'size_in_bytes': expected['archive_size_bytes'], 'digest': 'sha256:' + expected['archive_sha256'],
                'workflow_run': {'id': int(expected['run_id']), 'head_sha': expected['source_commit'],
                                 'repository_id': 1061766508, 'head_repository_id': 1061766508, 'head_branch': 'main'}}
    run = {'id': int(expected['run_id']), 'run_attempt': 1, 'head_sha': expected['source_commit'],
           'repository': {'full_name': P.REPOSITORY}, 'head_repository': {'full_name': P.REPOSITORY},
           'event': 'workflow_dispatch', 'head_branch': 'main'}
    return artifact, run


@pytest.mark.parametrize('fault', ['none', 'expired', 'artifact-id', 'name', 'digest', 'size', 'run-id', 'attempt',
                                 'source', 'repository', 'head-repository', 'artifact-repository', 'event'])
def test_original_artifact_metadata_is_exact(fault):
    expected = P.load_profile(ROOT)['preparation']; a, r = origin(expected)
    if fault == 'expired': a['expired'] = True
    elif fault == 'artifact-id': a['id'] += 1
    elif fault == 'name': a['name'] += '-other'
    elif fault == 'digest': a['digest'] = 'sha256:' + '0' * 64
    elif fault == 'size': a['size_in_bytes'] += 1
    elif fault == 'run-id': r['id'] += 1
    elif fault == 'attempt': r['run_attempt'] = 2
    elif fault == 'source': r['head_sha'] = 'b' * 40
    elif fault == 'repository': r['repository']['full_name'] = 'other/repo'
    elif fault == 'head-repository': r['head_repository']['full_name'] = 'other/repo'
    elif fault == 'artifact-repository': a['workflow_run']['repository_id'] = 1
    elif fault == 'event': r['event'] = 'pull_request'
    if fault == 'none': P.check_origin(a, r, expected)
    else:
        with pytest.raises(IO.IntakeError): P.check_origin(a, r, expected)


@pytest.mark.parametrize('identifier', ['', '0', '-1', '1/zip', '1\n', '1?token=private', '9' * 25])
def test_bad_roundtrip_locator_rejected_before_download(publication, monkeypatch, identifier):
    f = publication; f.env['PULSE_Q2_PUBLICATION_ARTIFACT_ID'] = identifier
    def forbidden(*args): pytest.fail('invalid locator reached transport')
    monkeypatch.setattr(IO, 'GitHubArtifactTransport', forbidden)
    with pytest.raises(IO.IntakeError): P.supervise(f.repo, 'verify-download', f.env)


def tar_case(tmp_path, fault):
    path = tmp_path / 'bootstrap.tar.gz'
    with tarfile.open(path, 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
        for name in ('.', './bin'):
            m = tarfile.TarInfo(name); m.type = tarfile.DIRTYPE; m.mode = 0o755; tar.addfile(m)
        name = {'traversal': '../outside', 'absolute': '/outside', 'alias': './bin/../outside',
                'backslash': './bin\\outside'}.get(fault, './bin/python3.11')
        m = tarfile.TarInfo(name); m.mode = 0o755; m.size = 7
        if fault == 'hardlink': m.type = tarfile.LNKTYPE; m.linkname = '/outside'; m.size = 0
        if fault == 'symlink': m.type = tarfile.SYMTYPE; m.linkname = '../../outside'; m.size = 0
        if fault == 'setuid': m.mode = 0o4755
        tar.addfile(m, bytesio.BytesIO(b'fixture'))
        m = tarfile.TarInfo('./bin/file with spaces'); m.size = 3; m.mode = 0o644
        tar.addfile(m, bytesio.BytesIO(b'abc'))
    expected = {'archive_size_bytes': path.stat().st_size, 'archive_sha256': IO.digest(path.read_bytes()),
                'interpreter_sha256': IO.digest(b'fixture')}
    limits = {'bootstrap_members': 4, 'bootstrap_expanded_bytes': 10, 'bootstrap_member_bytes': 100}
    if fault == 'digest': expected['archive_sha256'] = '0' * 64
    if fault == 'members': limits['bootstrap_members'] = 3
    if fault == 'expanded': limits['bootstrap_expanded_bytes'] = 9
    if fault == 'member-size': limits['bootstrap_member_bytes'] = 6
    return path, expected, limits


@pytest.mark.parametrize('fault', ['none', 'digest', 'traversal', 'absolute', 'alias', 'backslash', 'hardlink',
                                 'symlink', 'setuid', 'members', 'expanded', 'member-size'])
def test_bounded_tar_extraction_validates_before_materializing(tmp_path, fault):
    path, expected, limits = tar_case(tmp_path, fault); destination = tmp_path / 'extracted'
    if fault == 'none':
        B.unpack_bootstrap(path, destination, expected, limits, IO.Deadline(5))
        assert (destination / 'bin/python3.11').read_bytes() == b'fixture'
        assert (destination / 'bin/file with spaces').read_bytes() == b'abc'
    else:
        with pytest.raises(IO.IntakeError): B.unpack_bootstrap(path, destination, expected, limits, IO.Deadline(5))
        assert not destination.exists()
    assert not (tmp_path / 'outside').exists()


@pytest.mark.parametrize('fault', ['none', 'digest', 'missing', 'extra', 'last-file', 'mode', 'link', 'link-kind', 'wrapper'])
def test_independent_payload_verifier_rejects_modified_synthetic_capsules(tmp_path, monkeypatch, fault):
    case = synthetic_case(tmp_path / 'synthetic'); payload = copy.deepcopy(case['capsule'])
    if fault == 'missing': payload.pop('runtime/bin/python')
    elif fault == 'extra': payload['extra'] = (b'extra', 0o100600)
    elif fault == 'last-file':
        name = sorted(n for n in payload if n.startswith('runtime/') and n != 'runtime/lib64')[-1]
        raw, mode = payload[name]; payload[name] = (raw + b'x', mode)
    elif fault == 'mode': payload['runtime/bin/python'] = (payload['runtime/bin/python'][0], 0o100644)
    elif fault == 'link': payload['runtime/lib64'] = (b'../outside', 0o120777)
    elif fault == 'link-kind': payload['runtime/lib64'] = (b'lib', 0o100777)
    elif fault == 'wrapper': payload = {'capsule.zip': ((case['folder'] / 'capsule.zip').read_bytes(), 0o100600)}
    zipped(case['folder'] / 'capsule.zip', payload)
    capsule = case['folder'] / 'capsule.zip'
    # Test-only alternate profile repairs the outer digest to reach member checks.
    expected = {'archive_size_bytes': capsule.stat().st_size, 'archive_sha256': IO.digest(capsule.read_bytes()),
                'capsule_manifest_sha256': case['request']['release_subject']['capsule_manifest_sha256']}
    if fault == 'digest': expected['archive_sha256'] = '0' * 64
    monkeypatch.setattr(P.intake, 'load_profile', lambda _: case['profile'])
    (case['folder'] / 'producer-verdict.json').write_bytes(b'{"status":"MATCH"}\n')
    if fault == 'none':
        result = P.check_capsule(ROOT, case['folder'], {'capsule': expected}, IO.Deadline(30))
        assert result['input_valid'] and result['metric_pass'] is False and result['process_exit'] == 1
        assert result['checks']['request'] is False
    else:
        with pytest.raises(IO.IntakeError): P.check_capsule(ROOT, case['folder'], {'capsule': expected}, IO.Deadline(30))


def test_workflow_has_two_fresh_jobs_and_one_unwrapped_upload():
    text = (ROOT / P.WORKFLOW).read_text(); doc = yaml.load(text, Loader=yaml.BaseLoader)
    assert set(doc['on']) == {'workflow_dispatch'} and set(doc['on']['workflow_dispatch']['inputs']) == {'source_commit'}
    assert doc['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert set(doc['jobs']) == {'build', 'verify_download'}
    assert doc['jobs']['verify_download']['needs'] == 'build'
    raw = []
    for job in doc['jobs'].values():
        assert job['runs-on'] == 'ubuntu-24.04' and job['timeout-minutes'] == '20'
        assert 'GITHUB_ACTOR_ID' in job['steps'][0]['run']
        for step in job['steps']:
            assert 'continue-on-error' not in step and 'inputs.' not in step.get('run', '')
            if step.get('uses', '').startswith('actions/setup-python@'):
                assert step['with']['python-version'] == '3.11.16'
            if step.get('with', {}).get('archive') == 'false': raw.append(step)
    assert len(raw) == 1
    assert raw[0]['uses'] == 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a'
    assert raw[0]['with']['overwrite'] == 'false' and raw[0]['with']['if-no-files-found'] == 'error'
    assert 'secrets.' not in text and 'workflow-dispatch' not in text


def test_checker_has_no_builder_import_or_payload_execution():
    tree = ast.parse((ROOT / P.CHECKER).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert 'build_q2_release_capsule' not in ast.unparse(node)
            assert not any(x in ast.unparse(node) for x in ('torch', 'transformers', 'evaluate_q2_archived_capture'))
    source = (ROOT / P.BUILDER).read_text()
    assert 'extractall' not in source and 'AutoModel' not in source


@pytest.mark.parametrize('phase,artifact,packing,valid', [('preupload_verified', None, True, True),
    ('roundtrip_verified', 90001, False, True), ('roundtrip_verified', None, False, False),
    ('preupload_verified', 90001, True, False), ('roundtrip_verified', 90001, True, False)])
def test_closed_receipts_keep_preupload_separate_from_observed_roundtrip(publication, phase, artifact, packing, valid):
    f = publication; binding, sources = P.authorize(f.repo, f.env, f.profile)
    args = (f.repo, phase, binding, sources, f.profile, artifact, P.environment_record() if packing else None)
    if valid:
        value = P.receipt(*args)
        assert value['authority_effect'] == 'none' and not value['production_gate_eligible']
        assert not value['historical_metric_pass'] and value['historical_process_exit'] == 1
    else:
        with pytest.raises(IO.IntakeError): P.receipt(*args)


@pytest.mark.parametrize('fault', ['none', 'roundtrip', 'main', 'timeout', 'disk', 'cleanup', 'existing', 'symlink', 'hardlink'])
def test_supervisor_isolation_cleanup_and_output_lifecycle(publication, monkeypatch, tmp_path, fault):
    """Control-plane seam test only; payload/transport are deliberately mocked."""
    f = publication; children, stages = [], []
    out = Path(f.env['RUNNER_TEMP']) / 'q2-capsule-publication'
    if fault == 'existing': out.mkdir(); (out / 'keep').write_bytes(b'prior')
    if fault == 'symlink':
        other = tmp_path / 'other'; other.mkdir(); out.symlink_to(other, target_is_directory=True)
    if fault == 'hardlink':
        other = tmp_path / 'other'; other.write_bytes(b'prior'); os.link(other, out)
    monkeypatch.setenv('GITHUB_TOKEN', 'GENERIC_PRIVATE_CREDENTIAL')
    monkeypatch.setenv(P.TOKEN, 'PARENT_PRIVATE_CREDENTIAL')
    monkeypatch.setattr(IO, 'GitHubArtifactTransport', lambda token: SimpleNamespace(token=token))
    monkeypatch.setattr(P, 'api_json', lambda *args: {'object': {'sha': 'b' * 40 if fault == 'main' else f.sha}})
    def download(_transport, _expected, destination, _deadline):
        stages.append(destination.parent)
        destination.write_bytes(b'CONTROLLED_STAGED_BYTES')
    monkeypatch.setattr(P, 'download_artifact', download)
    monkeypatch.setattr(P, 'download_bootstrap', lambda _e, path, _d: path.write_bytes(b'CONTROLLED_INPUT'))
    def child(command, *, cwd, environment, timeout, new_session):
        assert not any('PRIVATE' in v for v in environment.values())
        assert set(environment) == set(IO.replay_environment(cwd)) and 0 < timeout <= 700 and new_session
        assert command[:3] == [sys.executable, '-I', '-B']
        children.append(command)
        (cwd / 'capsule.zip').write_bytes(b'CONTROLLED_STAGED_BYTES')
        (cwd / 'packing-environment.json').write_bytes(IO.encode(P.environment_record()))
        return 0
    monkeypatch.setattr(IO, 'private_process', child)
    def semantic(*args):
        if fault == 'timeout': raise IO.IntakeError('q2_timeout')
        assert not any(k.startswith('PULSE_Q2_') for k in os.environ)
        return {'CONTROLLED_SEMANTIC_SEAM': True}
    installs = []
    monkeypatch.setattr(P, 'install_verifier_dependencies', lambda private, profile, deadline: installs.append(private))
    monkeypatch.setattr(P, 'verify_in_fresh_workspace', semantic)
    monkeypatch.setattr(P, 'copy_verified', lambda source, destination, *args: destination.write_bytes(source.read_bytes()))
    if fault == 'disk': monkeypatch.setattr(P.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    if fault == 'cleanup':
        original = P.shutil.rmtree
        def cleanup(path, *args, **kwargs):
            if Path(path).name.startswith('pulse-q2-intake-'): raise OSError('PRIVATE_CLEANUP_FAILURE')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(P.shutil, 'rmtree', cleanup)
    if fault == 'roundtrip': f.env['PULSE_Q2_PUBLICATION_ARTIFACT_ID'] = '90001'
    if fault in ('none', 'roundtrip'):
        value = P.supervise(f.repo, 'verify-download' if fault == 'roundtrip' else 'build', f.env)
        assert value['status'] == ('roundtrip_verified' if fault == 'roundtrip' else 'preupload_verified')
        assert bool(children) is (fault == 'none')
        assert len(installs) == 1  # Both build and roundtrip use the preserved wheels.
        assert not any(p.exists() for p in stages)
        assert IO.strict_json((out / 'publication.json').read_bytes()) == value
    else:
        with pytest.raises((IO.IntakeError, OSError)): P.supervise(f.repo, 'build', f.env)
        assert not (out / 'publication.json').exists()
        if fault == 'existing': assert (out / 'keep').read_bytes() == b'prior'
        elif fault == 'symlink': assert out.is_symlink()
        elif fault == 'hardlink': assert out.read_bytes() == b'prior'
        else: assert not out.exists()


@pytest.mark.parametrize('job', ['build', 'verify_download'])
@pytest.mark.parametrize('fault', ['none', 'version', 'missing', 'duplicate'])
def test_actual_hygiene_guard_scopes_each_publication_python_pin(tmp_path, job, fault):
    from test_q2_reference_acquisition_v0 import _run_hygiene_python_sync, _q2_workflow_text
    doc = yaml.load((ROOT / P.WORKFLOW).read_bytes(), Loader=yaml.BaseLoader)
    steps = doc['jobs'][job]['steps']
    setup = next(s for s in steps if s.get('uses', '').startswith('actions/setup-python@'))
    if fault == 'version': setup['with']['python-version'] = '3.11.15'
    elif fault == 'missing': steps.remove(setup)
    elif fault == 'duplicate': steps.append(copy.deepcopy(setup))
    result = _run_hygiene_python_sync(tmp_path, q2_text=_q2_workflow_text(),
        extra_workflows={Path(P.WORKFLOW).name: yaml.safe_dump(doc, sort_keys=False)})
    assert result.returncode == (0 if fault == 'none' else 1), result.stdout + result.stderr


@pytest.mark.parametrize('fault', ['none', 'short', 'long', 'changed', 'bad-host', 'userinfo', 'port', 'second-redirect'])
def test_bootstrap_download_is_bounded_and_never_carries_credentials(tmp_path, monkeypatch, fault):
    expected = {'url': P.load_profile(ROOT)['bootstrap']['url'], 'archive_size_bytes': 9,
                'archive_sha256': IO.digest(b'bootstrap')}
    locations = {'bad-host': 'https://evil.invalid/payload',
                 'userinfo': 'https://secret@release-assets.githubusercontent.com/payload',
                 'port': 'https://release-assets.githubusercontent.com:444/payload'}
    location = locations.get(fault, 'https://release-assets.githubusercontent.com/payload?sig=PRIVATE_SIGNED_URL')
    requests = []
    class Response(bytesio.BytesIO):
        status = 200
        headers = {}  # Exercise streaming bounds without Content-Length.
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert 0 < timeout <= 5
            assert request.get_header('Authorization') is None and request.get_header('Cookie') is None
            if len(requests) == 1 or fault == 'second-redirect':
                raise urllib.error.HTTPError(request.full_url, 302, 'private', {'Location': location}, bytesio.BytesIO())
            raw = {'short': b'boot', 'long': b'bootstrap-extra', 'changed': b'changed!!'}.get(fault, b'bootstrap')
            return Response(raw)
    monkeypatch.setattr(P.urllib.request, 'build_opener', lambda *args: Opener())
    if fault == 'none':
        P.download_bootstrap(expected, tmp_path / 'payload', IO.Deadline(5))
        assert (tmp_path / 'payload').read_bytes() == b'bootstrap' and len(requests) == 2
    else:
        with pytest.raises((IO.IntakeError, urllib.error.HTTPError)):
            P.download_bootstrap(expected, tmp_path / 'payload', IO.Deadline(5))


@pytest.mark.parametrize('key', ['preparation', 'capture', 'bootstrap', 'pip'])
def test_each_changed_input_digest_rejects_before_parsing(tmp_path, key):
    p = P.load_profile(ROOT); raw = b'changed-original-input'
    path = tmp_path / 'input'; path.write_bytes(raw)
    with pytest.raises(IO.IntakeError): B.binding(path, p[key], IO.Deadline(5))


def test_cli_diagnostics_do_not_disclose_exception_details(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['checker', 'build', '--repo-root', str(ROOT)])
    def fail(*args): raise RuntimeError('PRIVATE_TOKEN_AND_SIGNED_URL')
    monkeypatch.setattr(P, 'supervise', fail)
    assert P.main() == 2
    assert capsys.readouterr().out == 'q2_internal_error\n'


@pytest.mark.parametrize('fault', ['none', 'empty', 'hash', 'mode', 'size', 'symlink', 'hardlink', 'mutation'])
def test_streamed_runtime_member_is_stable_bounded_and_mode_bound(tmp_path, monkeypatch, fault):
    path = tmp_path / 'member'; raw = b'' if fault == 'empty' else b'fixed-runtime-bytes'
    path.write_bytes(raw); path.chmod(0o755)
    expected = {'size': len(raw), 'sha256': IO.digest(raw), 'mode': 0o755}
    if fault == 'hash': expected['sha256'] = '0' * 64
    elif fault == 'mode': path.chmod(0o644)
    elif fault == 'size': expected['size'] += 1
    elif fault in ('symlink', 'hardlink'):
        other = tmp_path / 'other'; path.rename(other)
        if fault == 'symlink': path.symlink_to(other)
        else: os.link(other, path)
    elif fault == 'mutation':
        original = B.os.read; changed = []
        def read(fd, size):
            block = original(fd, size)
            if block and not changed:
                changed.append(True)
                info = path.stat()
                os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1000))
            return block
        monkeypatch.setattr(B.os, 'read', read)
    target = bytesio.BytesIO()
    if fault in ('none', 'empty'):
        B.checked_stream(path, expected, 100, IO.Deadline(5), target=target, check_mode=True)
        assert target.getvalue() == raw
    else:
        with pytest.raises(IO.IntakeError):
            B.checked_stream(path, expected, 100, IO.Deadline(5), target=target, check_mode=True)


@pytest.mark.parametrize('fault', ['extra', 'preparation', 'capture', 'bootstrap', 'pip', 'capsule', 'limit', 'verifier'])
def test_profile_contract_is_closed_and_original_identities_cannot_drift(tmp_path, fault):
    profile = copy.deepcopy(P.load_profile(ROOT))
    if fault == 'extra': profile['command'] = 'not-allowed'
    elif fault == 'limit': profile['limits']['minimum_free_bytes'] = 0
    elif fault == 'verifier': profile['verifier_wheels'][0]['sha256'] = '0' * 64
    else: profile[fault]['archive_sha256'] = '0' * 64
    for name, raw in ((P.PROFILE, IO.encode(profile)), (P.SCHEMA, (ROOT / P.SCHEMA).read_bytes())):
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    with pytest.raises(IO.IntakeError, match='q2_source_mismatch'): P.load_profile(tmp_path)


@pytest.mark.parametrize('fault', ['none', 'replace-after-digest', 'mutate-after-digest'])
def test_bootstrap_digest_and_parser_share_one_held_file(tmp_path, monkeypatch, fault):
    path, expected, limits = tar_case(tmp_path, 'none')
    replacement = tmp_path / 'replacement.tar.gz'
    with tarfile.open(path, 'r:gz') as source, tarfile.open(replacement, 'w:gz', format=tarfile.USTAR_FORMAT) as target:
        for member in source:
            raw = source.extractfile(member).read() if member.isfile() else None
            if member.name.endswith('file with spaces'): raw = b'xyz'
            target.addfile(member, bytesio.BytesIO(raw) if raw is not None else None)
    opened, parsed = [], []
    original_open, original_parse = IO._open_regular, B._extract_bootstrap
    def observe_open(name):
        if Path(name) == path: opened.append(name)
        return original_open(name)
    def after_digest(stream, *args):
        parsed.append(True)
        if fault == 'replace-after-digest': os.replace(replacement, path)
        elif fault == 'mutate-after-digest': path.write_bytes(replacement.read_bytes())
        return original_parse(stream, *args)
    monkeypatch.setattr(IO, '_open_regular', observe_open)
    monkeypatch.setattr(B, '_extract_bootstrap', after_digest)
    out = tmp_path / 'out'
    if fault == 'none':
        B.unpack_bootstrap(path, out, expected, limits, IO.Deadline(5))
        assert (out / 'bin/file with spaces').read_bytes() == b'abc'
    else:
        with pytest.raises((IO.IntakeError, tarfile.TarError, EOFError, OSError)):
            B.unpack_bootstrap(path, out, expected, limits, IO.Deadline(5))
        if fault == 'replace-after-digest' and (out / 'bin/file with spaces').exists():
            assert (out / 'bin/file with spaces').read_bytes() == b'abc'
    assert len(opened) == 1 and parsed == [True]


def verifier_case(tmp_path):
    """Tiny authored wheel; actual pinned installer, no hosted evidence or network."""
    private = tmp_path / 'private'; private.mkdir(mode=0o700)
    wheel = tmp_path / 'q2_fixture_verifier-1.0-py3-none-any.whl'
    prefix = 'q2_fixture_verifier-1.0.dist-info/'
    zipped(wheel, {
        'q2_fixture_verifier.py': (b'VALUE = "original"\n', 0o100644),
        prefix + 'METADATA': (b'Metadata-Version: 2.1\nName: q2-fixture-verifier\nVersion: 1.0\n', 0o100644),
        prefix + 'WHEEL': (b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n', 0o100644),
        prefix + 'RECORD': (b'', 0o100644)})
    raw = wheel.read_bytes()
    row = {'name': 'q2-fixture-verifier', 'version': '1.0', 'path': 'wheelhouse/' + wheel.name,
           'size': len(raw), 'sha256': IO.digest(raw)}
    prep = private / 'preparation.zip'
    zipped(prep, {'q2-runtime-preparation/' + row['path']: (raw, 0o100600)})
    profile = copy.deepcopy(P.load_profile(ROOT)); profile['verifier_wheels'] = [row]
    profile['preparation'].update(archive_size_bytes=prep.stat().st_size, archive_sha256=IO.digest(prep.read_bytes()))
    profile['limits'].update(preparation_members=1, preparation_expanded_bytes=len(raw), member_bytes=len(raw))
    # CPython 3.11.16's ensurepip ships the same reviewed pip 24.0 wheel.
    pip = Path(ensurepip.__file__).parent / '_bundled' / profile['pip']['filename']
    assert IO.digest(pip.read_bytes()) == profile['pip']['archive_sha256']
    shutil.copyfile(pip, private / profile['pip']['filename'])
    return private, profile


@pytest.mark.parametrize('fault', ['none', 'archive-digest', 'wheel-digest', 'wheel-size', 'pip-digest', 'installer-exit'])
def test_verifier_install_requires_exact_preserved_bytes_and_offline_flags(tmp_path, monkeypatch, fault):
    private, profile = verifier_case(tmp_path)
    if fault == 'archive-digest': profile['preparation']['archive_sha256'] = '0' * 64
    elif fault == 'wheel-digest': profile['verifier_wheels'][0]['sha256'] = '0' * 64
    elif fault == 'wheel-size': profile['verifier_wheels'][0]['size'] += 1
    elif fault == 'pip-digest': (private / profile['pip']['filename']).write_bytes(b'changed-pip')
    calls = []
    def install(command, *, cwd, environment, timeout, new_session):
        calls.append(command)
        for option in ('--isolated', '--no-cache-dir', '--no-index', '--no-deps', '--require-hashes',
                       '--only-binary=:all:', '--force-reinstall', '--no-compile'):
            assert option in command
        assert environment == IO.replay_environment(private) and new_session and timeout <= 90
        assert 'https://' not in ' '.join(command)
        assert (private / 'verifier-requirements.txt').read_text() == (
            'q2-fixture-verifier==1.0 --hash=sha256:' + profile['verifier_wheels'][0]['sha256'] + '\n')
        assert set(p.name for p in (private / 'verifier-wheels').iterdir()) == {'q2_fixture_verifier-1.0-py3-none-any.whl'}
        return 2 if fault == 'installer-exit' else 0
    monkeypatch.setattr(IO, 'private_process', install)
    if fault == 'none': P.install_verifier_dependencies(private, profile, IO.Deadline(30))
    else:
        with pytest.raises(IO.IntakeError): P.install_verifier_dependencies(private, profile, IO.Deadline(30))
    assert bool(calls) is (fault in ('none', 'installer-exit'))


def test_real_offline_pip_replaces_same_version_with_verified_fixture_wheel(tmp_path, monkeypatch):
    private, profile = verifier_case(tmp_path)
    target = tmp_path / 'verifier-venv'
    venv.EnvBuilder(with_pip=False, symlinks=False).create(target)
    python = target / 'bin/python'
    monkeypatch.setattr(P.sys, 'executable', str(python))
    # Force reinstall is material: an existing same-version altered module must
    # not satisfy this install merely because its version metadata matches.
    for iteration in range(2):
        if iteration:
            other = tmp_path / 'second'; other.mkdir()
            private, profile = verifier_case(other)
        P.install_verifier_dependencies(private, profile, IO.Deadline(60))
        result = subprocess.run([str(python), '-I', '-B', '-c',
                                 'import q2_fixture_verifier as q; print(q.VALUE); print(q.__file__)'],
                                capture_output=True, text=True, timeout=10, check=True)
        value, installed = result.stdout.strip().splitlines()
        assert value == 'original'
        if not iteration: Path(installed).write_text('VALUE = "changed"\n')


@pytest.mark.parametrize('fault', ['none', 'missing', 'digest', 'size', 'symlink', 'hardlink', 'existing', 'mutation'])
def test_verification_handoff_copies_only_stable_bound_regular_bytes(tmp_path, monkeypatch, fault):
    source = tmp_path / 'source'; source.write_bytes(b'known-archive-bytes')
    expected = {'archive_size_bytes': source.stat().st_size, 'archive_sha256': IO.digest(source.read_bytes())}
    destination = tmp_path / 'destination'
    if fault == 'missing': source.unlink()
    elif fault == 'digest': expected['archive_sha256'] = '0' * 64
    elif fault == 'size': expected['archive_size_bytes'] += 1
    elif fault in ('symlink', 'hardlink'):
        other = tmp_path / 'other'; source.rename(other)
        if fault == 'symlink': source.symlink_to(other)
        else: os.link(other, source)
    elif fault == 'existing': destination.write_bytes(b'preserve')
    elif fault == 'mutation':
        original = P.os.read
        def read(fd, count):
            raw = original(fd, count)
            if raw:
                s = source.stat(); os.utime(source, ns=(s.st_atime_ns, s.st_mtime_ns + 1000))
            return raw
        monkeypatch.setattr(P.os, 'read', read)
    if fault == 'none':
        P.copy_verified(source, destination, expected, IO.Deadline(5))
        assert destination.read_bytes() == b'known-archive-bytes'
    else:
        with pytest.raises((IO.IntakeError, OSError)): P.copy_verified(source, destination, expected, IO.Deadline(5))
        if fault == 'existing': assert destination.read_bytes() == b'preserve'


@pytest.mark.parametrize('fault', ['none', 'child-failure', 'missing-output', 'forged-output', 'timeout', 'cleanup'])
def test_fresh_semantic_child_has_no_builder_residue_and_cleanup_is_required(publication, monkeypatch, tmp_path, fault):
    f = publication; build = tmp_path / 'build'; build.mkdir(mode=0o700)
    binding, sources = P.authorize(f.repo, f.env, f.profile)
    for filename, key in (('capture.zip', 'capture'), ('capsule.zip', 'capsule')):
        raw = (filename + '-synthetic').encode(); (build / filename).write_bytes(raw)
        f.profile[key].update(archive_size_bytes=len(raw), archive_sha256=IO.digest(raw))
    (build / 'builder-verdict.json').write_text('{"status":"MATCH"}')
    (build / 'groups.json').write_text('builder residue must not enter the verifier')
    children = []
    def child(command, *, cwd, environment, timeout, new_session):
        children.append(cwd)
        assert cwd != build and build not in cwd.parents
        assert {p.name for p in cwd.iterdir()} == {'capture.zip', 'capsule.zip', 'verification-context.json'}
        assert command[:3] == [sys.executable, '-I', '-B'] and command[4] == 'check-private'
        assert command[-1] == str(cwd) and new_session and 0 < timeout <= 180
        assert environment == IO.replay_environment(cwd)
        if fault == 'timeout': raise IO.IntakeError('q2_timeout')
        if fault != 'missing-output':
            value = P.private_verification_record({'binding': binding, 'source_bindings': sources}, f.profile)
            if fault == 'forged-output': value['metric_pass'] = True
            (cwd / 'verification.json').write_bytes(IO.encode(value))
        return 2 if fault == 'child-failure' else 0
    monkeypatch.setattr(IO, 'private_process', child)
    original_cleanup = IO.shutil.rmtree
    if fault == 'cleanup':
        def fail(*args, **kwargs): raise OSError('private cleanup detail')
        monkeypatch.setattr(IO.shutil, 'rmtree', fail)
    args = (f.repo, build, tmp_path, f.profile, binding, sources, IO.Deadline(30))
    if fault == 'none': P.verify_in_fresh_workspace(*args)
    else:
        with pytest.raises((IO.IntakeError, OSError)): P.verify_in_fresh_workspace(*args)
    assert len(children) == 1
    if fault == 'cleanup': original_cleanup(children[0])
    assert not children[0].exists() and (build / 'groups.json').exists()


@pytest.mark.parametrize('fault', ['none', 'credential', 'source', 'extra-context', 'semantics'])
def test_private_checker_entry_validates_context_before_any_success(publication, monkeypatch, tmp_path, fault):
    f = publication; private = tmp_path / 'semantic'; private.mkdir(mode=0o700)
    binding, sources = P.authorize(f.repo, f.env, f.profile)
    context = {'binding': binding, 'source_bindings': sources}
    if fault == 'source': context['source_bindings'][0]['sha256'] = '0' * 64
    elif fault == 'extra-context': context['claimed_match'] = True
    (private / 'verification-context.json').write_bytes(IO.encode(context))
    monkeypatch.setattr(os, 'environ', IO.replay_environment(private))
    if fault == 'credential': monkeypatch.setenv(P.TOKEN, 'forbidden')
    calls = []
    def check(*args):
        calls.append(True)
        if fault == 'semantics': raise IO.IntakeError('q2_subject_mismatch')
    monkeypatch.setattr(P, 'check_capsule', check)
    if fault == 'none':
        P.check_private(f.repo, private)
        assert (private / 'verification.json').read_bytes() == IO.encode(P.private_verification_record(context, f.profile))
    else:
        with pytest.raises(IO.IntakeError): P.check_private(f.repo, private)
        assert not (private / 'verification.json').exists()
    assert bool(calls) is (fault in ('none', 'semantics'))


def test_both_workflow_jobs_use_supervised_preserved_dependencies():
    workflow = yaml.load((ROOT / P.WORKFLOW).read_bytes(), Loader=yaml.BaseLoader)
    for name, job in workflow['jobs'].items():
        assert not any('pip install' in step.get('run', '') for step in job['steps'])
        steps = [s for s in job['steps'] if P.CHECKER in s.get('run', '')]
        assert len(steps) == 1
        assert ('build' if name == 'build' else 'verify-download') in steps[0]['run']
    p = P.load_profile(ROOT)
    assert len(p['verifier_wheels']) == 8
    assert {r['name'] for r in p['verifier_wheels']} == {
        'attrs', 'jsonschema', 'jsonschema-specifications', 'pyyaml', 'referencing', 'rfc8785', 'rpds-py', 'typing-extensions'}


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
