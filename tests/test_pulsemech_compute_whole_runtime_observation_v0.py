"""Permanent Step 5C contract, acquisition, capture and workflow regressions.

All run/job/artifact IDs and clock values below are deterministic EXAMPLES.
The source fixture is a new local Git repository, never an upstream commit.
HTTP and artifact retrieval use a rejecting in-memory transport: no live
workflow, model inference, network request or production decision is performed.

The lightweight Step 3F envelope fixture exercises the capture intake boundary;
it is not a complete release-grade proof and must not be called one. Positive
source-bound plan checks execute the real isolated CLIs. Negative tests require
rejection at the intended boundary, including recomputed-container-hash attacks.

This program intentionally fails when the implementation violates its contract.
No xfail/skip or substituted success diagnostic masks a broken connected path.
"""
from __future__ import annotations
import ast
import copy
import io
import shutil
import socket
import stat
import zipfile
from dataclasses import replace
from collections import Counter
import jsonschema
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/pulsemech_compute_whole_runtime_observation_reference.yml'
SOURCES = ROOT / 'tools'
DOC = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
JOBS = DOC['jobs']

def load_module(name):
    spec = importlib.util.spec_from_file_location('step5c_regression_' + name, SOURCES / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

ACQUIRER = load_module('acquire_pulsemech_compute_whole_runtime_observation_v0')

def code_for(job, phrase):
    step = next(s for s in JOBS[job]['steps'] if phrase in s['name'])
    match = re.search(r"python -I -B - <<'PY'\n(.*?)\nPY(?:\n|$)", step['run'], re.S)
    assert match
    return compile(match[1], '<workflow:' + step['name'] + '>', 'exec')

ACQ_GUARD = code_for('acquisition', 'Validate reviewed main')
VER_GUARD = code_for('verification', 'Validate independent job')
BIND = code_for('acquisition', 'Bind the four')
INTAKE = code_for('verification', 'Verify exact handoff')

@pytest.fixture
def env(tmp_path):
    root = tmp_path / 'repository'
    temp = tmp_path / 'runner-temp'
    root.mkdir(); temp.mkdir()
    return {
        'SOURCE_COMMIT_INPUT': 'a' * 40,
        'GITHUB_REPOSITORY': ACQUIRER.REPOSITORY,
        'GITHUB_WORKFLOW': ACQUIRER.REFERENCE_WORKFLOW_NAME,
        'GITHUB_WORKFLOW_REF': f'{ACQUIRER.REPOSITORY}/{ACQUIRER.REFERENCE_WORKFLOW_PATH}@refs/heads/main',
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_SHA': 'a' * 40,
        'GITHUB_WORKFLOW_SHA': 'a' * 40,
        'GITHUB_RUN_ATTEMPT': '1',
        'GITHUB_RUN_ID': '12345',
        'GITHUB_RUN_NUMBER': '7',
        'RUNNER_OS': 'Linux',
        'RUNNER_ENVIRONMENT': 'github-hosted',
        'GITHUB_WORKSPACE': str(root),
        'RUNNER_TEMP': str(temp),
        'GITHUB_OUTPUT': str(tmp_path / 'workflow-output'),
        'HANDOFF_ARTIFACT_ID': '23456',
        'EXPECTED_PLAN_SHA256': 'b' * 64,
    }

def execute(code, env):
    namespace = {'__name__': '__workflow_step5c_regression__'}
    with patch.dict(os.environ, env, clear=True):
        exec(code, namespace)
    return namespace


def fake_git(env, *, head=None, main=None, dirty=False, fail=False, timeout=False):
    expected_root = Path(env['GITHUB_WORKSPACE']).resolve()
    def run(command, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired(command, 60)
        assert command[:4] == ['/usr/bin/git', '--no-replace-objects', '-c', 'credential.helper=']
        assert kwargs['timeout'] == 60 and kwargs['cwd'] == expected_root
        assert kwargs['env']['GIT_CONFIG_GLOBAL'] == '/dev/null'
        assert 'GITHUB_TOKEN' not in kwargs['env']
        tail = command[4:]
        if tail == ['rev-parse', '--show-toplevel']:
            output = str(expected_root).encode() + b'\n'
        elif tail == ['rev-parse', '--verify', 'HEAD^{commit}']:
            output = (head or 'a' * 40).encode() + b'\n'
        elif tail == ['diff', '--name-only', 'HEAD', '--']:
            output = b'changed.py\n' if dirty else b''
        elif tail == ['ls-remote', '--exit-code', 'https://github.com/HKati/pulse-release-gates-0.1.git', 'refs/heads/main']:
            output = (main or 'a' * 40).encode() + b'\trefs/heads/main\n'
        else:
            raise AssertionError('Unexpected Git command: ' + repr(command))
        return SimpleNamespace(returncode=1 if fail else 0, stdout=output, stderr=b'')
    return run


def context_bytes(env):
    context = ACQUIRER._reference_context_from_environment(
        source_commit=env['SOURCE_COMMIT_INPUT'], record_status='observed', environment=env,
    )
    return ACQUIRER._canonical_json_bytes(ACQUIRER._expected_context_document(
        context=context, expected_plan_sha256=env['EXPECTED_PLAN_SHA256'],
    ))


def bindings_for(directory):
    return {
        path.name: {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size_bytes': path.stat().st_size}
        for path in sorted(directory.iterdir())
    }


def rebind(env, directory):
    env['HANDOFF_FILE_BINDINGS'] = json.dumps(bindings_for(directory), sort_keys=True)


@pytest.fixture
def inputs(env):
    directory = Path(env['RUNNER_TEMP']) / 'pulsemech-step5c-verification' / 'input'
    directory.mkdir(parents=True)
    (directory / 'prepared.zip').write_bytes(b'LOCAL TRANSPORT TEST ONLY: NOT A STEP5C CARRIER\n')
    (directory / 'capture.zip').write_bytes(b'LOCAL TRANSPORT TEST ONLY: NOT AN ACQUISITION\n')
    (directory / 'expected_plan.sha256').write_text(env['EXPECTED_PLAN_SHA256'] + '\n')
    (directory / 'expected_context.json').write_bytes(context_bytes(env))
    rebind(env, directory)
    return directory


def test_workflow_closed_dispatch_and_permissions():
    assert DOC['name'] == ACQUIRER.REFERENCE_WORKFLOW_NAME
    assert set(DOC['on']) == {'workflow_dispatch'}
    assert DOC['on']['workflow_dispatch']['inputs'] == {
        'source_commit': {'description': 'Exact reviewed main commit (40 lowercase hexadecimal digits).', 'required': 'true', 'type': 'string'}
    }
    assert DOC['permissions'] == {'contents': 'read'}
    assert set(JOBS) == {'acquisition', 'verification'}
    assert JOBS['acquisition']['permissions'] == {'contents': 'read', 'actions': 'write'}
    assert JOBS['verification']['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert JOBS['verification']['needs'] == 'acquisition'
    assert DOC['concurrency']['cancel-in-progress'] == 'false'
    assert int(JOBS['acquisition']['timeout-minutes']) >= 90 + 45
    assert int(JOBS['verification']['timeout-minutes']) > 60


def test_action_pins_and_handoff_selector():
    expected = {
        'actions/checkout': '3d3c42e5aac5ba805825da76410c181273ba90b1',
        'actions/setup-python': '5fda3b95a4ea91299a34e894583c3862153e4b97',
        'actions/upload-artifact': '043fb46d1a93c77aae656e7c1c64a875d1fc6a0a',
        'actions/download-artifact': 'd3f86a106a0bac45b974a628896c90dbdf5c8093',
    }
    for job in JOBS.values():
        assert job['runs-on'] == 'ubuntu-24.04'
        for step in job['steps']:
            assert 'continue-on-error' not in step and 'if' not in step
            if 'uses' in step:
                action, pin = step['uses'].split('@')
                assert expected[action] == pin and re.fullmatch('[0-9a-f]{40}', pin)
                options = step.get('with', {})
                if action == 'actions/checkout':
                    assert options == {'ref': '${{ github.sha }}', 'fetch-depth': '0', 'persist-credentials': 'false'}
                if action == 'actions/setup-python':
                    assert options['python-version'] == '3.11'
                if action == 'actions/upload-artifact':
                    assert options['overwrite'] == 'false'
                    assert options['if-no-files-found'] == 'error'
                    assert options['compression-level'] == '0'
                if action == 'actions/download-artifact':
                    assert options['artifact-ids'] == '${{ needs.acquisition.outputs.handoff_artifact_id }}'
                    assert options['run-id'] == '${{ github.run_id }}'
                    assert options['repository'] == '${{ github.repository }}'
                    assert 'name' not in options and 'pattern' not in options


RUNS = [(name, n, step['run']) for name, job in JOBS.items() for n, step in enumerate(job['steps']) if 'run' in step]
@pytest.mark.parametrize('job,n,script', RUNS)
def test_all_shell_blocks_parse(job, n, script):
    result = subprocess.run(['bash', '-n'], input=script + '\n', text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert '${{' not in script


INLINE = [match.group(1) for _, _, script in RUNS if (match := re.search(r"python -I -B - <<'PY'\n(.*?)\nPY(?:\n|$)", script, re.S))]
@pytest.mark.parametrize('source', INLINE)
def test_inline_python_parses_under_311_grammar(source):
    ast.parse(source, feature_version=(3, 11))


def cli_calls():
    result = []
    for _, _, script in RUNS:
        for line in script.replace('\\\n', ' ').splitlines():
            if line.strip().startswith('python -I -B tools/'):
                tokens = shlex.split(line)
                if '>' in tokens:
                    tokens = tokens[:tokens.index('>')]
                result.append((Path(tokens[3]).stem, tokens[4:]))
    return result


@pytest.mark.parametrize('name,arguments', cli_calls())
def test_workflow_arguments_match_actual_committed_parsers(name, arguments):
    module = load_module(name)
    if name == 'check_pulsemech_compute_whole_runtime_observation_v0':
        parsed = module.parse_args(arguments)
    elif name == 'check_pulsemech_compute_whole_runtime_observation_plan_v0':
        parsed = module._parse_checker_args(arguments)
    elif name == 'capture_pulsemech_compute_whole_runtime_observation_v0':
        with patch.object(sys, 'argv', [name, *arguments]):
            parsed = module._parse_args()
    else:
        parsed = module._parse_args(arguments)
    assert getattr(parsed, 'record_status', getattr(parsed, 'expected_record_status', None)) == 'observed'


@pytest.mark.parametrize('code', [ACQ_GUARD, VER_GUARD])
def test_valid_control_plane(code, env):
    with patch('subprocess.run', fake_git(env)):
        execute(code, env)


MUTATIONS = [
    ('GITHUB_REPOSITORY', 'other/repository'), ('GITHUB_WORKFLOW', 'Other workflow'),
    ('GITHUB_WORKFLOW_REF', 'wrong'), ('GITHUB_EVENT_NAME', 'push'),
    ('GITHUB_REF', 'refs/heads/other'), ('GITHUB_SHA', 'c' * 40),
    ('GITHUB_WORKFLOW_SHA', 'c' * 40), ('GITHUB_RUN_ATTEMPT', '2'),
    ('GITHUB_RUN_ID', '0'), ('GITHUB_RUN_NUMBER', '01'),
    ('RUNNER_OS', 'Windows'), ('RUNNER_ENVIRONMENT', 'self-hosted'),
]
@pytest.mark.parametrize('key,value', MUTATIONS)
@pytest.mark.parametrize('code', [ACQ_GUARD, VER_GUARD])
def test_control_plane_substitution_rejected(code, env, key, value):
    env[key] = value
    with patch('subprocess.run', fake_git(env)), pytest.raises(SystemExit, match='step5c_workflow_context_rejected'):
        execute(code, env)


@pytest.mark.parametrize('revision', ['', 'A' * 40, 'a' * 39, 'a' * 41, 'a' * 40 + '\n'])
def test_invalid_reviewed_revision_rejected(env, revision):
    env['SOURCE_COMMIT_INPUT'] = revision
    with patch('subprocess.run', fake_git(env)), pytest.raises(SystemExit, match='source_commit'):
        execute(ACQ_GUARD, env)


@pytest.mark.parametrize('options', [{'head': 'c' * 40}, {'main': 'c' * 40}, {'dirty': True}, {'fail': True}, {'timeout': True}])
def test_source_and_remote_failures_reject_before_dispatch(env, options):
    with patch('subprocess.run', fake_git(env, **options)), pytest.raises(SystemExit, match='step5c_workflow_context_rejected'):
        execute(ACQ_GUARD, env)


@pytest.mark.parametrize('selector', ['', '0', '-1', '23456,789', ' 23456', 'True'])
def test_empty_or_ambiguous_artifact_selector_rejected_before_download(env, selector):
    env['HANDOFF_ARTIFACT_ID'] = selector
    with patch('subprocess.run', fake_git(env)), pytest.raises(SystemExit, match='artifact_id'):
        execute(VER_GUARD, env)


def test_existing_verification_destination_is_preserved(env):
    base = Path(env['RUNNER_TEMP']) / 'pulsemech-step5c-verification'
    base.mkdir(); marker = base / 'unrelated'; marker.write_bytes(b'preserve')
    with patch('subprocess.run', fake_git(env)), pytest.raises(SystemExit, match='output_already_exists'):
        execute(VER_GUARD, env)
    assert marker.read_bytes() == b'preserve'


def test_handoff_builder_copies_exact_context_and_binds_four_files(env):
    base = Path(env['RUNNER_TEMP']) / 'pulsemech-step5c'
    handoff = base / 'handoff'; handoff.mkdir(parents=True)
    acquisition = base / 'acquisition'; acquisition.mkdir()
    original = context_bytes(env)
    (acquisition / 'expected_context.json').write_bytes(original)
    for name, raw in {'prepared.zip': b'example prepared', 'capture.zip': b'example capture', 'expected_plan.sha256': (env['EXPECTED_PLAN_SHA256']+'\n').encode()}.items():
        (handoff / name).write_bytes(raw)
    execute(BIND, env)
    line = Path(env['GITHUB_OUTPUT']).read_text().strip()
    assert line.startswith('file_bindings=')
    assert json.loads(line.split('=', 1)[1]) == bindings_for(handoff)
    assert (handoff / 'expected_context.json').read_bytes() == original
    assert {p.stat().st_mode & 0o777 for p in handoff.iterdir()} == {0o444}
    with pytest.raises(FileExistsError):
        execute(BIND, env)
    assert (handoff / 'expected_context.json').read_bytes() == original


def test_exact_transport_inputs_accept_and_are_not_rewritten(env, inputs):
    before = {p.name: p.read_bytes() for p in inputs.iterdir()}
    execute(INTAKE, env)
    assert before == {p.name: p.read_bytes() for p in inputs.iterdir()}


NAMES = ['prepared.zip', 'capture.zip', 'expected_context.json', 'expected_plan.sha256']
@pytest.mark.parametrize('name', NAMES)
def test_tampered_payload_rejected(env, inputs, name):
    p = inputs / name; raw = p.read_bytes(); p.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(SystemExit, match='file_digest'):
        execute(INTAKE, env)


@pytest.mark.parametrize('name', NAMES)
def test_missing_payload_rejected(env, inputs, name):
    (inputs / name).unlink()
    with pytest.raises(SystemExit, match='file_membership'):
        execute(INTAKE, env)


def test_extra_payload_rejected(env, inputs):
    (inputs / 'extra.txt').write_bytes(b'extra')
    with pytest.raises(SystemExit, match='file_membership'):
        execute(INTAKE, env)


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_nonregular_or_aliased_payload_rejected(env, inputs, name, kind):
    path = inputs / name; target = inputs.parent / 'outside'; path.rename(target)
    if kind == 'symlink':
        path.symlink_to(target)
    else:
        os.link(target, path)
    with pytest.raises(SystemExit, match='file_shape'):
        execute(INTAKE, env)


@pytest.mark.parametrize('value', [True, -1, 0, 2**40, '4', 4.0])
def test_invalid_binding_size_rejected(env, inputs, value):
    bindings = json.loads(env['HANDOFF_FILE_BINDINGS'])
    bindings['capture.zip']['size_bytes'] = value
    env['HANDOFF_FILE_BINDINGS'] = json.dumps(bindings)
    with pytest.raises(SystemExit, match='binding_size'):
        execute(INTAKE, env)


@pytest.mark.parametrize('value', ['', '{', 'null', '[]', '{"x":NaN}'])
def test_malformed_binding_document_rejected(env, inputs, value):
    env['HANDOFF_FILE_BINDINGS'] = value
    with pytest.raises(SystemExit, match='step5c_handoff_rejected'):
        execute(INTAKE, env)


def test_duplicate_binding_key_rejected(env, inputs):
    raw = env['HANDOFF_FILE_BINDINGS']
    env['HANDOFF_FILE_BINDINGS'] = '{"capture.zip":{},' + raw[1:]
    with pytest.raises(SystemExit, match='duplicate_key'):
        execute(INTAKE, env)


CONTEXT_CHANGES = [
    ('reference_run_id', 999), ('reference_run_number', 8), ('reference_run_attempt', 2),
    ('reference_workflow_ref', 'wrong'), ('reference_event_name', 'push'),
    ('source_commit', 'd' * 40), ('expected_plan_sha256', 'c' * 64),
    ('repository', 'other/repository'), ('record_status', 'example'),
    ('collector_run_key', 'wrong'), ('acquisition_id', 'step5c-acquisition:999-1'),
]
@pytest.mark.parametrize('key,value', CONTEXT_CHANGES)
def test_rehashed_cross_run_or_context_substitution_still_rejected(env, inputs, key, value):
    path = inputs / 'expected_context.json'; value_map = json.loads(path.read_bytes())
    value_map[key] = value; path.write_bytes(ACQUIRER._canonical_json_bytes(value_map)); rebind(env, inputs)
    with pytest.raises(SystemExit, match='reference_context'):
        execute(INTAKE, env)


def test_rehashed_authority_promotion_rejected(env, inputs):
    path = inputs / 'expected_context.json'; doc = json.loads(path.read_bytes())
    doc['authority_boundary']['active_gate_eligible'] = True
    path.write_bytes(ACQUIRER._canonical_json_bytes(doc)); rebind(env, inputs)
    with pytest.raises(SystemExit, match='reference_context'):
        execute(INTAKE, env)


def test_rehashed_plan_digest_substitution_rejected(env, inputs):
    (inputs / 'expected_plan.sha256').write_text('c' * 64 + '\n'); rebind(env, inputs)
    with pytest.raises(SystemExit, match='plan_digest'):
        execute(INTAKE, env)


def test_upload_only_capsule_after_actual_verifier_entrypoint():
    steps = JOBS['verification']['steps']
    final = steps[-1]
    assert final['uses'].startswith('actions/upload-artifact@')
    assert final['with']['path'].endswith('/reference/reference_capsule_v0.zip')
    command = steps[-2]['run']
    assert 'run-reference --repository-root' in command
    assert '--expected-plan-digest' in command
    assert 'always()' not in command and 'continue-on-error' not in command
    assert 'acquire_pulsemech' not in '\n'.join(s.get('run', '') for s in steps)
    assert 'capture_pulsemech' not in '\n'.join(s.get('run', '') for s in steps)

# ---------------------------------------------------------------------------
# Actual source-bound planning and finite, network-free example acquisition.
# ---------------------------------------------------------------------------
BUILDER = load_module('build_pulsemech_compute_whole_runtime_observation_plan_v0')
PLAN_CHECKER = load_module('check_pulsemech_compute_whole_runtime_observation_plan_v0')
CAPTURER = load_module('capture_pulsemech_compute_whole_runtime_observation_v0')
VERIFIER = load_module('check_pulsemech_compute_whole_runtime_observation_v0')
TOOL_NAMES = [
    'build_pulsemech_compute_whole_runtime_observation_plan_v0',
    'check_pulsemech_compute_whole_runtime_observation_plan_v0',
    'acquire_pulsemech_compute_whole_runtime_observation_v0',
    'capture_pulsemech_compute_whole_runtime_observation_v0',
    'check_pulsemech_compute_whole_runtime_observation_v0',
]
EXAMPLE_SUBJECT_ID = 10001
EXAMPLE_PROVIDER_ID = 10002
EXAMPLE_REFERENCE_ID = 10003
EXAMPLE_START = '2000-01-01T00:00:00Z'
EXAMPLE_END = '2000-01-01T00:10:00Z'
EXAMPLE_EXPIRY = '2000-04-01T00:00:00Z'


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def cli(root, tool, args, *, isolated=True, timeout=60):
    command = [sys.executable, *(['-I'] if isolated else []), '-B', str(root / 'tools' / (tool + '.py')), *map(str, args)]
    clean = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C', 'LC_ALL': 'C',
             'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0'}
    return subprocess.run(command, cwd=root, env=clean, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def require_cli_success(result):
    assert result.returncode == 0, (result.returncode, result.stdout.decode(errors='replace'), result.stderr.decode(errors='replace'))


@pytest.fixture(scope='module')
def source_fixture(tmp_path_factory):
    """Commit exact current input bytes in an explicitly synthetic local repo."""
    directory = tmp_path_factory.mktemp('step5c-source-example')
    root = directory / 'repository'
    root.mkdir()
    # This fixture needs no network, historical upstream object, copied .git,
    # source-pin substitution, or synthetic implementation dependency.
    for _, relative in BUILDER.SOURCE_ROLES:
        source = ROOT / relative
        assert source.is_file() and not source.is_symlink(), relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        target.chmod(0o644)
    env_git = {'PATH': '/usr/bin:/bin', 'HOME': str(directory), 'LANG': 'C', 'LC_ALL': 'C',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
               'GIT_AUTHOR_NAME': 'Step5C deterministic example', 'GIT_AUTHOR_EMAIL': 'example@example.invalid',
               'GIT_COMMITTER_NAME': 'Step5C deterministic example', 'GIT_COMMITTER_EMAIL': 'example@example.invalid',
               'GIT_AUTHOR_DATE': EXAMPLE_START, 'GIT_COMMITTER_DATE': EXAMPLE_START}
    for args in [['init', '-q'], ['add', '--all'], ['commit', '-q', '-m', 'Synthetic local Step5C test source; not an upstream commit']]:
        result = subprocess.run(['/usr/bin/git', '-C', str(root), *args], env=env_git, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
    sha = subprocess.check_output(['/usr/bin/git', '-C', str(root), 'rev-parse', 'HEAD'], env=env_git, timeout=10).decode().strip()
    build_args = ['--repository-root', root, '--source-commit', sha, '--record-status', 'example']
    build = cli(root, TOOL_NAMES[0], build_args)
    require_cli_success(build)
    plan_path = directory / 'prelaunch-plan.json'
    plan_path.write_bytes(build.stdout)
    check_args = ['--repository-root', root, '--plan', plan_path, '--expected-source-commit', sha,
                  '--expected-plan-sha256', digest(build.stdout), '--expected-record-status', 'example']
    checked = cli(root, TOOL_NAMES[1], check_args)
    require_cli_success(checked)
    diagnostic = directory / 'prelaunch-plan-diagnostic.json'
    diagnostic.write_bytes(checked.stdout)
    return SimpleNamespace(root=root, directory=directory, sha=sha, plan=json.loads(build.stdout),
                           plan_path=plan_path, plan_raw=build.stdout, plan_digest=digest(build.stdout),
                           diagnostic=diagnostic, diagnostic_doc=json.loads(checked.stdout),
                           build_args=build_args, check_args=check_args)


def test_real_plan_cli_and_independent_checker(source_fixture):
    f = source_fixture
    assert f.plan['record_status'] == 'example'
    assert f.diagnostic_doc['ok'] is True and f.diagnostic_doc['errors'] == []
    assert all(v is True for v in f.diagnostic_doc['checks'].values())
    assert f.diagnostic_doc['plan']['byte_identical_to_independent_reconstruction'] is True
    assert f.diagnostic_doc['plan']['sha256'] == f.plan_digest
    assert f.plan['plan_identity']['source_commit'] == f.sha
    assert len(f.plan['source_inventory']) == len(BUILDER.SOURCE_ROLES) == 35


def test_two_separate_plan_processes_are_byte_identical(source_fixture):
    f = source_fixture
    first = cli(f.root, TOOL_NAMES[0], f.build_args)
    second = cli(f.root, TOOL_NAMES[0], f.build_args)
    require_cli_success(first); require_cli_success(second)
    assert first.stdout == second.stdout == f.plan_raw


def test_prelaunch_plan_exact_extent_and_occurrences(source_fixture):
    plan = source_fixture.plan
    jobs = plan['jobs']
    steps = [s for j in jobs for s in j['steps']]
    instantiated = [s for s in steps if s['expected_runtime_presence']]
    assert len(jobs) == 8 and len(steps) == 147 and len(instantiated) == 145
    assert Counter(j['expected_terminal_result'] for j in jobs) == {'success': 7, 'skipped': 1}
    assert Counter(s['expected_terminal_result'] for s in instantiated) == {'success': 101, 'skipped': 44}
    assert len({j['occurrence_id'] for j in jobs}) == 8
    assert len({s['occurrence_id'] for s in steps}) == 147
    for job in jobs:
        for ordinal, step in enumerate(job['steps'], 1):
            assert step['source_ordinal'] == ordinal
            assert step['occurrence_id'].endswith(f':{ordinal:03d}')
    assert len(plan['model_inference_templates']) == 6


@pytest.mark.parametrize('mutation', ['job_omitted', 'step_omitted', 'step_reordered', 'condition_changed',
                                    'skip_reclassified', 'source_ordinal', 'action_pin', 'shell_digest',
                                    'policy_digest', 'inference_omitted', 'model_revision', 'authority'])
def test_rehashed_plan_mutations_fail_independent_reconstruction(source_fixture, tmp_path, mutation):
    f = source_fixture
    plan = copy.deepcopy(f.plan)
    steps = plan['jobs'][0]['steps']
    if mutation == 'job_omitted': plan['jobs'].pop()
    elif mutation == 'step_omitted': steps.pop()
    elif mutation == 'step_reordered': steps[0], steps[1] = steps[1], steps[0]
    elif mutation == 'condition_changed': steps[1]['if_expression'] = '${{ false }}'
    elif mutation == 'skip_reclassified': next(s for s in steps if s['expected_terminal_result'] == 'skipped')['expected_terminal_result'] = 'success'
    elif mutation == 'source_ordinal': steps[0]['source_ordinal'] = 99
    elif mutation == 'action_pin': next(s for s in steps if s['source']['kind'] == 'github_action')['source']['action_commit_sha'] = 'a' * 40
    elif mutation == 'shell_digest': next(s for s in steps if s['source']['kind'] == 'shell')['source']['run_sha256'] = 'b' * 64
    elif mutation == 'policy_digest': next(s for s in plan['source_inventory'] if s['path'] == 'pulse_gate_policy_v0.yml')['sha256'] = 'c' * 64
    elif mutation == 'inference_omitted': plan['model_inference_templates'].pop()
    elif mutation == 'model_revision': plan['model_inference_templates'][0]['model_revision'] = 'd' * 40
    elif mutation == 'authority': plan['authority_boundary']['active_gate_eligible'] = True
    path = tmp_path / 'tampered-plan.json'; path.write_bytes(canonical(plan))
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', path,
                 '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(path.read_bytes()),
                 '--expected-record-status', 'example'])
    assert result.returncode != 0, 'A rehashed mutated plan was accepted'
    error = json.loads(result.stdout or result.stderr)
    assert error['ok'] is False and error['errors']


@pytest.mark.parametrize('name', TOOL_NAMES)
def test_all_production_entrypoints_reject_nonisolated_python(name):
    result = cli(ROOT, name, ['--help'], isolated=False)
    assert result.returncode == 2
    assert b'isolated_python_required' in result.stdout + result.stderr


@pytest.mark.parametrize('name', [TOOL_NAMES[1], TOOL_NAMES[4]])
def test_independent_checker_does_not_import_producer_modules(name):
    tree = ast.parse((SOURCES / (name + '.py')).read_text())
    forbidden = {TOOL_NAMES[0], TOOL_NAMES[2], TOOL_NAMES[3]}
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or '')
    assert not forbidden.intersection(imports)


def example_run(role, source_commit):
    subject = role == 'subject'
    identifier = EXAMPLE_SUBJECT_ID if subject else EXAMPLE_PROVIDER_ID
    return {'id': identifier, 'name': ACQUIRER.SUBJECT_WORKFLOW_NAME if subject else ACQUIRER.PROVIDER_WORKFLOW_NAME,
            'path': ACQUIRER.SUBJECT_WORKFLOW_PATH if subject else ACQUIRER.PROVIDER_WORKFLOW_PATH,
            'event': 'workflow_dispatch', 'head_branch': 'main', 'head_sha': source_commit,
            'run_number': 11 if subject else 12, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
            'url': f'https://api.github.com/repos/{ACQUIRER.REPOSITORY}/actions/runs/{identifier}',
            'html_url': f'https://github.com/{ACQUIRER.REPOSITORY}/actions/runs/{identifier}',
            'repository': {'full_name': ACQUIRER.REPOSITORY}, 'head_repository': {'full_name': ACQUIRER.REPOSITORY},
            'created_at': EXAMPLE_START, 'run_started_at': EXAMPLE_START, 'updated_at': EXAMPLE_END}


def example_jobs(plan, source_commit):
    rows = []
    for ordinal, job in enumerate(plan['jobs'], 1):
        steps = []
        for step in job['steps']:
            if not step['expected_runtime_presence']: continue
            steps.append({'name': step['name'], 'number': len(steps) + 2,
                          'status': 'completed', 'conclusion': step['expected_terminal_result'],
                          'started_at': EXAMPLE_START, 'completed_at': EXAMPLE_END})
        rows.append({'id': 20000 + ordinal, 'name': job['display_name'], 'run_id': EXAMPLE_SUBJECT_ID,
                     'run_attempt': 1, 'head_sha': source_commit, 'status': 'completed',
                     'conclusion': job['expected_terminal_result'], 'started_at': EXAMPLE_START,
                     'completed_at': EXAMPLE_END, 'steps': steps, 'labels': ['ubuntu-24.04'],
                     'runner_name': 'example-hosted-runner', 'runner_id': 30000 + ordinal,
                     'runner_group_id': 1, 'runner_group_name': 'GitHub Actions'})
    return rows


def run_kwargs(role, source_commit):
    row = example_run(role, source_commit)
    return dict(role=role, run_id=row['id'], source_commit=source_commit,
                workflow_name=row['name'], workflow_path=row['path'],
                expected_run_url=row['url'], expected_html_url=row['html_url'], require_terminal=True)


@pytest.mark.parametrize('role', ['subject', 'provider'])
def test_exact_terminal_run_identity_accepts(role):
    ACQUIRER._run_identity_checks(example_run(role, 'a' * 40), **run_kwargs(role, 'a' * 40))


RUN_CHANGES = [('id', 999), ('name', 'wrong'), ('path', 'wrong'), ('event', 'push'),
               ('head_branch', 'other'), ('head_sha', 'b' * 40), ('run_attempt', 2),
               ('run_number', True), ('url', 'https://example.invalid/run'),
               ('html_url', 'https://example.invalid/run'), ('repository', {'full_name': 'other/repo'}),
               ('head_repository', {'full_name': 'other/repo'}), ('status', 'in_progress'),
               ('conclusion', 'cancelled'), ('conclusion', 'failure'), ('conclusion', 'timed_out'),
               ('created_at', 'invalid'), ('updated_at', '1999-01-01T00:00:00Z')]
@pytest.mark.parametrize('role', ['subject', 'provider'])
@pytest.mark.parametrize('field,value', RUN_CHANGES)
def test_terminal_run_substitutions_reject(role, field, value):
    row = example_run(role, 'a' * 40); row[field] = value
    with pytest.raises(ACQUIRER.AcquisitionError):
        ACQUIRER._run_identity_checks(row, **run_kwargs(role, 'a' * 40))


@pytest.mark.parametrize('role', ['subject', 'provider'])
def test_dispatch_receipt_urls_agree_with_exact_id(role):
    row = example_run(role, 'a' * 40)
    receipt = {'workflow_run_id': row['id'], 'run_url': row['url'], 'html_url': row['html_url']}
    result = ACQUIRER._dispatch_response(receipt, role=role)
    assert result['workflow_run_id'] == row['id']


@pytest.mark.parametrize('field,value', [('workflow_run_id', True), ('workflow_run_id', 0),
    ('workflow_run_id', '10001'), ('workflow_run_id', -1), ('run_url', 'https://api.github.com/repos/other/repo/actions/runs/10001'),
    ('html_url', 'https://github.com/HKati/pulse-release-gates-0.1/actions/runs/999'), ('html_url', None)])
def test_dispatch_response_substitution_rejects(field, value):
    row = example_run('subject', 'a' * 40)
    receipt = {'workflow_run_id': row['id'], 'run_url': row['url'], 'html_url': row['html_url']}
    receipt[field] = value
    with pytest.raises(ACQUIRER.AcquisitionError): ACQUIRER._dispatch_response(receipt, role='subject')


def test_declared_job_step_extent_accepts(source_fixture):
    f = source_fixture
    counts = CAPTURER._match_subject_jobs(f.plan, example_jobs(f.plan, f.sha), subject_run_id=EXAMPLE_SUBJECT_ID, source_commit=f.sha)
    assert isinstance(counts, dict)
    assert len(example_jobs(f.plan, f.sha)) == 8
    assert sum(len(j['steps']) for j in example_jobs(f.plan, f.sha)) == 145


@pytest.mark.parametrize('mutation', ['missing_job', 'duplicate_job', 'wrong_job_run', 'wrong_job_attempt',
    'wrong_job_source', 'required_job_skipped', 'skipped_job_runs', 'missing_step', 'duplicate_step',
    'step_reordered', 'required_step_skipped', 'skipped_step_runs', 'unexpected_step', 'job_cancelled'])
def test_declared_extent_mutations_reject(source_fixture, mutation):
    f = source_fixture; rows = example_jobs(f.plan, f.sha)
    if mutation == 'missing_job': rows.pop()
    elif mutation == 'duplicate_job': rows[-1] = copy.deepcopy(rows[0])
    elif mutation == 'wrong_job_run': rows[0]['run_id'] = 999
    elif mutation == 'wrong_job_attempt': rows[0]['run_attempt'] = 2
    elif mutation == 'wrong_job_source': rows[0]['head_sha'] = 'b' * 40
    elif mutation == 'required_job_skipped': rows[0]['conclusion'] = 'skipped'
    elif mutation == 'skipped_job_runs': next(j for j in rows if j['conclusion'] == 'skipped')['conclusion'] = 'success'
    elif mutation == 'missing_step': rows[0]['steps'].pop()
    elif mutation == 'duplicate_step': rows[0]['steps'].insert(1, copy.deepcopy(rows[0]['steps'][0]))
    elif mutation == 'step_reordered': rows[0]['steps'][0], rows[0]['steps'][1] = rows[0]['steps'][1], rows[0]['steps'][0]
    elif mutation == 'required_step_skipped': rows[0]['steps'][0]['conclusion'] = 'skipped'
    elif mutation == 'skipped_step_runs': next(s for s in rows[0]['steps'] if s['conclusion'] == 'skipped')['conclusion'] = 'success'
    elif mutation == 'unexpected_step': rows[0]['steps'].append({**rows[0]['steps'][0], 'name': 'Post attacker-controlled step'})
    elif mutation == 'job_cancelled': rows[0]['conclusion'] = 'cancelled'
    with pytest.raises(CAPTURER.CaptureError):
        CAPTURER._match_subject_jobs(f.plan, rows, subject_run_id=EXAMPLE_SUBJECT_ID, source_commit=f.sha)


def test_lifecycle_metadata_does_not_replace_declared_steps(source_fixture):
    f = source_fixture; rows = example_jobs(f.plan, f.sha)
    life = {'name': 'Set up job', 'number': 1, 'status': 'completed', 'conclusion': 'success',
            'started_at': EXAMPLE_START, 'completed_at': EXAMPLE_END}
    rows[0]['steps'].insert(0, life)
    counts = CAPTURER._match_subject_jobs(f.plan, rows, subject_run_id=EXAMPLE_SUBJECT_ID, source_commit=f.sha)
    assert counts['platform_lifecycle_record_count'] == 1
    assert counts['raw_platform_step_record_count'] == 146
    rows[0]['steps'].pop(1)
    with pytest.raises(CAPTURER.CaptureError):
        CAPTURER._match_subject_jobs(f.plan, rows, subject_run_id=EXAMPLE_SUBJECT_ID, source_commit=f.sha)


def example_zip(members):
    """Deterministic fixture packer independent of the production packer."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o444) << 16
            archive.writestr(info, raw)
    return output.getvalue()


def example_model_rows(plan):
    # Opaque, controlled public-fixture-like strings, never user content.
    return [{'case_id': item['case_id'], 'input': 'EXAMPLE controlled input ' + item['case_id'],
             'output': 'EXAMPLE controlled output ' + item['case_id'],
             'model': {'id': item['model_id'], 'revision': item['model_revision']},
             'inference': {'prompt_tokens': 10, 'generated_tokens': 2},
             'llamaguard': {'label': 'safe', 'categories': []}}
            for item in plan['model_inference_templates']]


def provider_fixture(plan, source_commit, *, model_rows=None, subject_override=None):
    """Capture-envelope fixture ONLY; not a valid full Step 3F evidence proof."""
    raw_rows = model_rows if model_rows is not None else example_model_rows(plan)
    raw_model = b''.join(json.dumps(row, sort_keys=True).encode() + b'\n' for row in raw_rows)
    subject_artifacts = {}
    layout = {'outer_prefix': 'example-current-run/',
              'original_artifacts_prefix': 'example-current-run/original-github-artifacts/'}
    for role, name_template, _ in ACQUIRER.SUBJECT_TERMINAL_ARTIFACT_TEMPLATES:
        name = name_template.format(run_id=EXAMPLE_SUBJECT_ID) + '.zip'
        subject_artifacts[role] = example_zip(
            {VERIFIER.LLAMAGUARD_RAW_MEMBER: raw_model} if role == 'complete_release_grade_reference_package'
            else {'fixture-only.json': canonical({'record_status': 'example', 'purpose': role})})
        layout[CAPTURER.SUBJECT_DOWNLOAD_ROLES[role][1]] = name
    relative_members = {'original-github-artifacts/' + layout[CAPTURER.SUBJECT_DOWNLOAD_ROLES[role][1]]: raw
                        for role, raw in subject_artifacts.items()}
    checksums = ''.join(f'{digest(raw)}  {name}\n' for name, raw in sorted(relative_members.items())).encode()
    carrier = example_zip({**{'example-current-run/' + name: raw for name, raw in relative_members.items()},
                           'example-current-run/SHA256SUMS': checksums})
    carrier_name = 'example-current-run-carrier-v0.zip'
    subject = {'workflow_run_id': EXAMPLE_SUBJECT_ID, 'workflow_run_attempt': 1, 'source_commit': source_commit}
    if subject_override: subject.update(subject_override)
    binding = {'sha256': digest(carrier), 'size_bytes': len(carrier)}
    # Legacy intake requires observed in these two records. The enclosing
    # acquisition/plan/manifest remain EXAMPLE; no actual run is asserted.
    expectation = {'record_status': 'observed', 'subject': subject, 'carrier': binding, 'archive_layout': layout}
    packet = {'record_status': 'observed', 'subject': subject, 'carrier': binding}
    payloads = {'carrier.json': canonical({**binding, 'staged_relative_path': carrier_name}),
                'expectation.json': canonical(expectation), 'subject-input-packet.json': canonical(packet),
                'source-run-resolution.json': canonical({'fixture_only': True}),
                'source-artifact-selection.json': canonical({'fixture_only': True}), carrier_name: carrier}
    manifest = {'schema_version': 'pulsemech_compute_current_run_export_candidate_output_manifest_v0',
                'document_type': 'pulsemech_compute_current_run_export_candidate_output_manifest',
                'manifest_scope': 'all_candidate_files_except_this_manifest',
                'authority_boundary': CAPTURER.EXPECTED_CANDIDATE_AUTHORITY_BOUNDARY,
                'source_run_id': EXAMPLE_SUBJECT_ID, 'source_run_attempt': 1, 'subject_revision': source_commit,
                'file_count': len(payloads),
                'files': [{'path': name, 'sha256': digest(raw), 'size_bytes': len(raw)} for name, raw in sorted(payloads.items())]}
    payloads['candidate-output-manifest.json'] = canonical(manifest)
    return subject_artifacts, example_zip({'candidate/' + name: raw for name, raw in payloads.items()})


def artifact_row(identifier, name, raw, source_commit, run_id):
    return {'id': identifier, 'name': name, 'size_in_bytes': len(raw), 'digest': 'sha256:' + digest(raw),
            'expired': False, 'created_at': EXAMPLE_END, 'expires_at': EXAMPLE_EXPIRY,
            'workflow_run': {'id': run_id, 'head_sha': source_commit, 'head_branch': 'main'}}


class ExampleTransport:
    """Exact endpoint allowlist; any unexpected or live request is a test error."""
    def __init__(self, plan, source_commit, *, change=None):
        self.calls = []
        self.source_commit = source_commit
        self.change = change
        self.subject = example_run('subject', source_commit)
        self.provider = example_run('provider', source_commit)
        self.jobs = example_jobs(plan, source_commit)
        self.provider_jobs = [{**self.jobs[0], 'id': 22000, 'run_id': EXAMPLE_PROVIDER_ID,
                               'name': 'Build non-active current-run candidate', 'steps': []}]
        artifacts, envelope = provider_fixture(plan, source_commit)
        self.downloads = {}
        self.subject_artifacts = []
        for index, (role, name, _) in enumerate(ACQUIRER.SUBJECT_TERMINAL_ARTIFACT_TEMPLATES, 1):
            identifier = 40000 + index
            raw = artifacts[role]
            self.downloads[identifier] = raw
            self.subject_artifacts.append(artifact_row(identifier, name.format(run_id=EXAMPLE_SUBJECT_ID), raw, source_commit, EXAMPLE_SUBJECT_ID))
        self.downloads[40004] = envelope
        self.provider_artifacts = [artifact_row(40004, ACQUIRER.PROVIDER_ARTIFACT_TEMPLATE.format(subject_run_id=EXAMPLE_SUBJECT_ID),
                                                envelope, source_commit, EXAMPLE_PROVIDER_ID)]

    def request(self, *, method, endpoint, body, max_response_bytes):
        self.calls.append((method, endpoint, body))
        prefix = f'repos/{ACQUIRER.REPOSITORY}/actions/runs/'
        if endpoint == ACQUIRER.MAIN_REF_ENDPOINT:
            assert method == 'GET' and body is None
            document = {'ref': 'refs/heads/main', 'object': {'type': 'commit', 'sha': self.source_commit}}
        elif endpoint in (ACQUIRER.SUBJECT_DISPATCH_ENDPOINT, ACQUIRER.PROVIDER_DISPATCH_ENDPOINT):
            assert method == 'POST'
            subject = endpoint == ACQUIRER.SUBJECT_DISPATCH_ENDPOINT
            expected = {'ref': 'main', 'inputs': dict(ACQUIRER.SUBJECT_DISPATCH_INPUTS) if subject else {'source_run_id': str(EXAMPLE_SUBJECT_ID)}}
            assert json.loads(body) == expected
            row = self.subject if subject else self.provider
            document = {'workflow_run_id': row['id'], 'run_url': row['url'], 'html_url': row['html_url']}
        elif endpoint in (prefix + str(EXAMPLE_SUBJECT_ID), prefix + str(EXAMPLE_PROVIDER_ID)):
            assert method == 'GET' and body is None
            document = self.subject if endpoint.endswith(str(EXAMPLE_SUBJECT_ID)) else self.provider
        elif endpoint == prefix + f'{EXAMPLE_SUBJECT_ID}/attempts/1/jobs?per_page=100&page=1':
            document = {'total_count': len(self.jobs), 'jobs': self.jobs}
        elif endpoint == prefix + f'{EXAMPLE_PROVIDER_ID}/attempts/1/jobs?per_page=100&page=1':
            document = {'total_count': len(self.provider_jobs), 'jobs': self.provider_jobs}
        elif endpoint == prefix + f'{EXAMPLE_SUBJECT_ID}/artifacts?per_page=100&page=1':
            document = {'total_count': len(self.subject_artifacts), 'artifacts': self.subject_artifacts}
        elif endpoint == prefix + f'{EXAMPLE_PROVIDER_ID}/artifacts?per_page=100&page=1':
            document = {'total_count': len(self.provider_artifacts), 'artifacts': self.provider_artifacts}
        else:
            raise AssertionError('Unplanned request, including any run-list lookup: ' + endpoint)
        document = copy.deepcopy(document)
        status = 200
        if self.change:
            changed = self.change(method, endpoint, document, self)
            if changed is not None: status, document = changed
        raw = canonical(document) if document is not None else b''
        assert len(raw) <= max_response_bytes
        return ACQUIRER.HttpExchange(status, {}, raw, EXAMPLE_START, EXAMPLE_END)

    def download_artifact(self, *, endpoint, destination, max_bytes):
        match = re.fullmatch(r'repos/HKati/pulse-release-gates-0\.1/actions/artifacts/(\d+)/zip', endpoint)
        assert match is not None, endpoint
        raw = self.downloads[int(match[1])]
        assert len(raw) <= max_bytes
        self.calls.append(('DOWNLOAD', endpoint, None))
        with open(destination, 'xb') as handle: handle.write(raw)
        return ACQUIRER.DownloadResult(len(raw), digest(raw))


def reference_context(source_commit):
    return ACQUIRER.ReferenceContext(
        record_status='example', repository=ACQUIRER.REPOSITORY,
        workflow_name=ACQUIRER.REFERENCE_WORKFLOW_NAME, workflow_path=ACQUIRER.REFERENCE_WORKFLOW_PATH,
        workflow_ref=f'{ACQUIRER.REPOSITORY}/{ACQUIRER.REFERENCE_WORKFLOW_PATH}@refs/heads/main',
        event_name='workflow_dispatch', ref='refs/heads/main', source_commit=source_commit,
        run_id=EXAMPLE_REFERENCE_ID, run_number=13, run_attempt=1,
        acquisition_id=f'step5c-acquisition:example-{EXAMPLE_REFERENCE_ID}-1',
        collector_run_key=f'GITHUB_RUN_ID={EXAMPLE_REFERENCE_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={ACQUIRER.REFERENCE_WORKFLOW_NAME}',
        collector_execution_id='execution:step5c:collector:post-run-platform-export')


def acquire_example(source_fixture, destination, transport):
    f = source_fixture
    # Load the REAL implementation at its exact fixture installation path.
    spec = importlib.util.spec_from_file_location('step5c_example_installed_acquirer', f.root / 'tools' / (TOOL_NAMES[2] + '.py'))
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    context = module.ReferenceContext(**reference_context(f.sha).__dict__)
    with patch.object(socket, 'create_connection', side_effect=AssertionError('Live network is forbidden in examples')):
        return module.acquire_observation(repository_root=f.root, source_commit=f.sha,
             plan_path=f.plan_path, plan_diagnostic_path=f.diagnostic, expected_plan_sha256=f.plan_digest,
             output_directory=destination, record_status='example', reference_context=context, transport=transport,
             monotonic=lambda: 0.0, sleep=lambda _: pytest.fail('Completed example runs must not poll'))


@pytest.fixture(scope='module')
def acquisition_fixture(source_fixture, tmp_path_factory):
    f = source_fixture; directory = tmp_path_factory.mktemp('step5c-acquisition-example')
    transport = ExampleTransport(f.plan, f.sha)
    result = acquire_example(f, directory / 'acquisition', transport)
    return SimpleNamespace(directory=directory, output=directory / 'acquisition', result=result, transport=transport)


def test_actual_acquisition_uses_exact_dispatch_receipts(acquisition_fixture, source_fixture):
    f = acquisition_fixture
    posts = [(endpoint, json.loads(body)) for method, endpoint, body in f.transport.calls if method == 'POST']
    assert len(posts) == 2
    assert posts[0][0] == ACQUIRER.SUBJECT_DISPATCH_ENDPOINT
    assert posts[1] == (ACQUIRER.PROVIDER_DISPATCH_ENDPOINT, {'ref': 'main', 'inputs': {'source_run_id': str(EXAMPLE_SUBJECT_ID)}})
    assert all('return_run_details' not in body for _, body in posts)
    index = json.loads((f.output / ACQUIRER.ACQUISITION_INDEX_MEMBER).read_bytes())
    assert index['ok'] is True and index['record_status'] == 'example'
    assert index['subject']['run_id'] == EXAMPLE_SUBJECT_ID
    assert index['provider']['run_id'] == EXAMPLE_PROVIDER_ID
    assert (f.output / 'expected_context.json').is_file()
    assert len([call for call in f.transport.calls if call[0] == 'DOWNLOAD']) == 4


def construct_capture(source_fixture, acquisition_fixture, name='capture.zip'):
    f = source_fixture; a = acquisition_fixture
    spec = importlib.util.spec_from_file_location('step5c_example_installed_capture', f.root / 'tools' / (TOOL_NAMES[3] + '.py'))
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    path = a.directory / name
    result = module.build_capture(repository_root=f.root, source_commit=f.sha, plan_path=f.plan_path,
             plan_diagnostic_path=f.diagnostic, expected_plan_sha256=f.plan_digest,
             acquisition_directory=a.output, output_path=path, record_status='example')
    with zipfile.ZipFile(path) as archive: members = {name: archive.read(name) for name in archive.namelist()}
    return SimpleNamespace(path=path, result=result, members=members, manifest=json.loads(members['capture.json']))


def test_actual_capture_closes_its_declared_inventory(source_fixture, acquisition_fixture):
    f = construct_capture(source_fixture, acquisition_fixture, 'capture-inventory.zip')
    assert f.manifest['ok'] is True and f.manifest['record_status'] == 'example'
    inventory = f.manifest['member_inventory']['members']
    assert {row['member'] for row in inventory} == set(f.members) - {'capture.json'}
    for row in inventory:
        raw = f.members[row['member']]
        assert row['sha256'] == digest(raw) and row['size_bytes'] == len(raw)
    assert len(f.manifest['carrier_member_bindings']) == 6
    assert all(row['source_run_attempt'] == 1 for row in f.manifest['artifact_bindings'])
    assert f.manifest['authority_boundary']['active_gate_eligible'] is False


def test_capture_determinism_from_same_acquired_bytes(source_fixture, acquisition_fixture):
    f = source_fixture; a = acquisition_fixture
    capture_fixture = construct_capture(f, a, 'capture-first.zip')
    target = a.directory / 'capture-second.zip'
    result = cli(f.root, TOOL_NAMES[3], ['--repository-root', f.root, '--source-commit', f.sha,
                 '--plan', f.plan_path, '--plan-diagnostic', f.diagnostic, '--expected-plan-sha256', f.plan_digest,
                 '--acquisition-directory', a.output, '--output', target, '--record-status', 'example'])
    require_cli_success(result)
    assert target.read_bytes() == capture_fixture.path.read_bytes()


@pytest.mark.parametrize('raw', [b'\xef\xbb\xbf{}\n', b'{"a":1,"a":2}\n', b'{"n":NaN}\n', b'{"n":Infinity}\n',
    b'[]\n', b'null\n', b'{', b'{"s":"\xff"}\n'])
def test_strict_json_rejects_invalid_input_acquisition_and_verifier(raw):
    with pytest.raises(ACQUIRER.AcquisitionError): ACQUIRER._strict_json_object(raw, label='example')
    with pytest.raises(VERIFIER.VerificationError): VERIFIER.parse_json_bytes(raw, label='example')


@pytest.mark.parametrize('raw', [b'{"a": 1}\n', b'{\n  "z": 0,\n  "a": 1\n}\n', b'{}', b'{\n  "s": "e\\u0301"\n}\n'])
def test_noncanonical_stored_json_rejected(raw):
    with pytest.raises(VERIFIER.VerificationError): VERIFIER.parse_json_bytes(raw, label='example')


def test_canonical_json_accepts_exact_bytes_and_checks_size():
    raw = canonical({'a': 1, 'message': 'example', 'flag': True})
    assert VERIFIER.parse_json_bytes(raw, label='example') == json.loads(raw)
    with pytest.raises(VERIFIER.VerificationError, match='json_size_out_of_range'):
        VERIFIER.parse_json_bytes(raw, label='example', maximum=len(raw)-1)


def test_canonical_zip_round_trip_and_no_extraction():
    members = {'a.json': canonical({'record_status': 'example'}), 'nested/b.bin': b'example'}
    raw = example_zip(members)
    assert VERIFIER.read_canonical_zip_bytes(raw, label='example', maximum_members=2, maximum_bytes=1024) == members
    assert VERIFIER.deterministic_zip_bytes(members, maximum_members=2, maximum_bytes=1024) == raw


@pytest.mark.parametrize('mutation', ['duplicate', 'traversal', 'absolute', 'backslash', 'directory', 'symlink',
    'wrong_mode', 'compression', 'timestamp', 'member_comment', 'archive_comment', 'extra_field', 'reverse_order', 'crc'])
def test_unsafe_or_noncanonical_zip_rejected(mutation):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name in (['b', 'a'] if mutation == 'reverse_order' else ['a']):
            if mutation == 'traversal': name = '../a'
            elif mutation == 'absolute': name = '/a'
            elif mutation == 'backslash': name = 'x\\a'
            elif mutation == 'directory': name = 'a/'
            info = zipfile.ZipInfo(name, (1980,1,1,0,0,0))
            info.create_system = 3; info.external_attr = (stat.S_IFREG | 0o444) << 16
            if mutation == 'symlink': info.external_attr = (stat.S_IFLNK | 0o777) << 16
            elif mutation == 'wrong_mode': info.external_attr = (stat.S_IFREG | 0o644) << 16
            elif mutation == 'compression': info.compress_type = zipfile.ZIP_DEFLATED
            elif mutation == 'timestamp': info.date_time = (2000,1,1,0,0,0)
            elif mutation == 'member_comment': info.comment = b'comment'
            elif mutation == 'extra_field': info.extra = b'\xfe\xca\x00\x00'
            archive.writestr(info, b'EXAMPLE-PAYLOAD')
            if mutation == 'duplicate':
                with pytest.warns(UserWarning, match='Duplicate name'): archive.writestr(copy.copy(info), b'other')
        if mutation == 'archive_comment': archive.comment = b'comment'
    raw = stream.getvalue()
    if mutation == 'crc': raw = raw.replace(b'EXAMPLE-PAYLOAD', b'EXAMPLE-PAYLOAE', 1)
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.read_canonical_zip_bytes(raw, label='example', maximum_members=5, maximum_bytes=1024)


@pytest.mark.parametrize('max_members,max_bytes', [(1, 1024), (10, 3)])
def test_zip_count_and_expansion_limits(max_members, max_bytes):
    raw = example_zip({'a': b'abc', 'b': b'def'})
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.read_canonical_zip_bytes(raw, label='example', maximum_members=max_members, maximum_bytes=max_bytes)


def test_publication_is_nonreplacing_and_preserves_competing_file(tmp_path):
    target = tmp_path / 'output.zip'; original = b'unrelated existing bytes'; target.write_bytes(original)
    with pytest.raises(VERIFIER.VerificationError, match='output_already_exists'):
        VERIFIER.publish_bytes(target, b'new bytes')
    assert target.read_bytes() == original
    target.unlink()
    assert VERIFIER.publish_bytes(target, b'new bytes') == (digest(b'new bytes'), 9)
    assert stat.S_IMODE(target.stat().st_mode) == 0o444


def test_publication_race_never_unlinks_competing_destination(tmp_path, monkeypatch):
    target = tmp_path / 'output.zip'; original = b'competing writer'
    actual = VERIFIER._rename_noreplace
    def compete(source, destination):
        destination.write_bytes(original)
        return actual(source, destination)
    monkeypatch.setattr(VERIFIER, '_rename_noreplace', compete)
    with pytest.raises(VERIFIER.VerificationError, match='output_already_exists'):
        VERIFIER.publish_bytes(target, b'new bytes')
    assert target.read_bytes() == original
    assert {p.name for p in tmp_path.iterdir()} == {'output.zip'}


@pytest.mark.parametrize('field,value', [('id', True), ('id', 0), ('expired', True), ('size_in_bytes', 0),
    ('size_in_bytes', True), ('size_in_bytes', 2**30), ('digest', 'sha256:' + 'A'*64),
    ('digest', 'b'*64), ('expires_at', EXAMPLE_START), ('created_at', 'invalid'),
    ('workflow_run', {'id': 999}), ('workflow_run', {'id': EXAMPLE_SUBJECT_ID, 'head_sha': 'b'*40})])
def test_artifact_identity_size_expiry_digest_rejections(field, value):
    row = artifact_row(40001, 'example', b'fixture', 'a'*40, EXAMPLE_SUBJECT_ID); row[field] = value
    with pytest.raises(ACQUIRER.AcquisitionError):
        ACQUIRER._artifact_metadata(row, expected_run_id=EXAMPLE_SUBJECT_ID, source_commit='a'*40, max_single_bytes=1024)


def test_artifact_metadata_exact_positive():
    row = artifact_row(40001, 'example', b'fixture', 'a'*40, EXAMPLE_SUBJECT_ID)
    result = ACQUIRER._artifact_metadata(row, expected_run_id=EXAMPLE_SUBJECT_ID, source_commit='a'*40, max_single_bytes=1024)
    assert result['sha256'] == digest(b'fixture') and result['size_bytes'] == 7


class PageTransport:
    def __init__(self, pages): self.pages = iter(pages); self.calls = []
    def request(self, **kwargs):
        self.calls.append(kwargs)
        return ACQUIRER.HttpExchange(200, {}, canonical(next(self.pages)), EXAMPLE_START, EXAMPLE_END)


def collect_pages(tmp_path, pages):
    transport = PageTransport(pages)
    result = ACQUIRER._collect_pages(transport=transport, staging=tmp_path, role='example',
        endpoint_prefix=f'repos/{ACQUIRER.REPOSITORY}/actions/runs/{EXAMPLE_SUBJECT_ID}/attempts/1/jobs',
        array_key='jobs', member_prefix='jobs', max_items=200, max_json_bytes=10000, id_field='id')
    return result, transport


def test_pagination_closes_exactly_and_preserves_raw_pages(tmp_path):
    pages = [{'total_count': 2, 'jobs': [{'id': 1}]}, {'total_count': 2, 'jobs': [{'id': 2}]}]
    result, transport = collect_pages(tmp_path, pages)
    assert result.total_count == 2 and [r['id'] for r in result.rows] == [1,2]
    assert len(transport.calls) == 2 and len(result.members) == 2
    assert [tmp_path.joinpath(member).read_bytes() for member in result.members] == [canonical(p) for p in pages]


@pytest.mark.parametrize('pages', [
    [{'total_count': 2, 'jobs': [{'id':1}]}, {'total_count':2, 'jobs':[]}],
    [{'total_count': 2, 'jobs': [{'id':1}]}, {'total_count':2, 'jobs':[{'id':1}]}],
    [{'total_count': 2, 'jobs': [{'id':1}]}, {'total_count':3, 'jobs':[{'id':2}]}],
    [{'total_count': 201, 'jobs': []}], [{'total_count': True, 'jobs': []}],
    [{'total_count': 1, 'jobs': [{'id':True}]}], [{'total_count': 0, 'jobs': [{'id':1}]}],
    [{'total_count': 1, 'jobs': None}],
])
def test_pagination_failure_is_not_complete_extent(tmp_path, pages):
    with pytest.raises(ACQUIRER.AcquisitionError): collect_pages(tmp_path, pages)


@pytest.mark.parametrize('status,body', [(204,b''), (200,b''), (500,b'{}'), (200,b'{"workflow_run_id":1}')])
def test_dispatch_without_exact_response_is_rejected(tmp_path, status, body):
    class Transport:
        def request(self, **kwargs):
            return ACQUIRER.HttpExchange(status, {}, body, EXAMPLE_START, EXAMPLE_END)
    schema = json.loads((ROOT / 'schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json').read_bytes())
    with pytest.raises(ACQUIRER.AcquisitionError):
        ACQUIRER._dispatch(transport=Transport(), staging=tmp_path, schema=schema, source_commit='a'*40,
            record_status='example', role='subject', request_document={'ref':'main','inputs':dict(ACQUIRER.SUBJECT_DISPATCH_INPUTS)},
            endpoint=ACQUIRER.SUBJECT_DISPATCH_ENDPOINT, workflow_name=ACQUIRER.SUBJECT_WORKFLOW_NAME,
            workflow_path=ACQUIRER.SUBJECT_WORKFLOW_PATH, request_member='request.json', response_member='response.json',
            receipt_member='receipt.json', max_json_bytes=4096)
    assert not (tmp_path / 'receipt.json').exists()


def test_queued_run_reaches_finite_timeout_without_success():
    row = example_run('subject', 'a'*40); row['status'] = 'queued'; row['conclusion'] = None
    transport = PageTransport([row, row])
    times = iter([0.0, 2.0])
    kwargs = run_kwargs('subject','a'*40); kwargs.pop('require_terminal')
    with pytest.raises(ACQUIRER.AcquisitionError, match='subject_wait_timeout'):
        ACQUIRER._wait_for_run(transport=transport, **kwargs, wait_seconds=1, max_json_bytes=10000,
             poll_interval_seconds=1, monotonic=lambda: next(times), sleep=lambda _: pytest.fail('Unexpected sleep'))
    assert len(transport.calls) == 1


# ---------------------------------------------------------------------------
# Producer/verifier integration. These are required PASS expectations, not
# expected failures. They intentionally expose current implementation defects.
# ---------------------------------------------------------------------------
GENERIC_SCHEMA = json.loads((ROOT / 'schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json').read_bytes())
EVIDENCE_SCHEMA = json.loads((ROOT / 'schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json').read_bytes())


def schema_errors(document, definition):
    schema = {'$schema': GENERIC_SCHEMA['$schema'], '$ref': '#/$defs/' + definition, '$defs': GENERIC_SCHEMA['$defs']}
    return [f'{list(error.path)}: {error.message}' for error in jsonschema.Draft202012Validator(schema).iter_errors(document)]


def minimal_capture_identity():
    return {'capture_id': 'step5c-capture:example-unit-boundary', 'capture_completed_utc': EXAMPLE_END,
            'capture_started_utc': EXAMPLE_END,
            'collector_run_key': f'GITHUB_RUN_ID={EXAMPLE_REFERENCE_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={ACQUIRER.REFERENCE_WORKFLOW_NAME}'}


def test_prepared_carrier_cli_accepts_checked_in_schema(source_fixture, tmp_path):
    f = source_fixture; target = tmp_path / 'prepared.zip'
    result = cli(f.root, TOOL_NAMES[4], ['prepare', '--repository-root', f.root, '--source-commit', f.sha,
                 '--plan', f.plan_path, '--plan-diagnostic', f.diagnostic,
                 '--expected-plan-sha256', f.plan_digest, '--output', target, '--record-status', 'example'])
    require_cli_success(result)
    assert target.is_file() and json.loads(result.stdout)['ok'] is True


def test_capture_response_bindings_are_consumable_by_independent_verifier(source_fixture):
    f = source_fixture
    rows = example_jobs(f.plan, f.sha)
    raw = canonical({'total_count': len(rows), 'jobs': rows})
    member = 'acquisition/subject/jobs-page-0001.json'
    # The schema and the real capture producer use `role`, not response_role.
    binding = {'role': 'subject_jobs_page', 'descriptor': {'member': member, 'sha256': digest(raw), 'size_bytes': len(raw)}}
    jsonschema.Draft202012Validator({'$ref': '#/$defs/raw_response_binding', '$defs': EVIDENCE_SCHEMA['$defs']}).validate(binding)
    result = VERIFIER._capture_job_rows({member: raw}, {'raw_response_bindings': [binding]})
    assert result == rows


def test_real_plan_step_ordinals_project_to_153_distinct_subject_executions(source_fixture):
    f = source_fixture; rows = example_jobs(f.plan, f.sha)
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    executions, index = VERIFIER._job_and_step_records(f.plan, rows, key)
    assert len(executions) == len(index) == 153
    assert len({row['execution_id'] for row in executions}) == 153
    assert sum(row['execution_kind'] == 'workflow_step' for row in executions) == 145
    for execution in executions:
        assert not schema_errors(execution, 'execution_record')


def test_collector_projection_matches_unchanged_runtime_contract(source_fixture):
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    collector = VERIFIER._collector_record(source_fixture.plan, {'capture_identity': minimal_capture_identity()}, key)
    assert collector['execution_scope'] == 'observation_collector'
    assert collector['run_binding']['subject_run_key'] == key
    assert collector['run_binding']['execution_run_key'] != key
    errors = schema_errors(collector, 'execution_record')
    assert errors == [], '\n'.join(errors)


def inference_projection(source_fixture, *, mutate=None):
    f = source_fixture; rows = example_model_rows(f.plan)
    if mutate: mutate(rows)
    _, envelope = provider_fixture(f.plan, f.sha, model_rows=rows)
    parent = f.plan['model_inference_templates'][0]['parent_occurrence_id']
    # A dependency stub for this specific helper only, not an accepted runtime
    # execution record or a replacement for the connected projection test.
    index = {parent: {'timing': VERIFIER._timing(EXAMPLE_START, EXAMPLE_END),
                     'input_state_ids': [], 'output_state_ids': [], 'external_call_ids': [],
                     'model_inference_ids': [], 'resource_measurement_ids': []}}
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    states, inferences = VERIFIER._build_states_and_inferences(f.plan, index,
        {'capture_identity': minimal_capture_identity()}, envelope, key, f'pulse-ci-current-run:{EXAMPLE_SUBJECT_ID}:1')
    return states, inferences, rows, index


def test_controlled_inference_hashing_preserves_privacy_and_occurrences(source_fixture):
    states, inferences, rows, index = inference_projection(source_fixture)
    assert len(inferences) == 6 and len({r['inference_id'] for r in inferences}) == 6
    state_map = {s['state_id']: s for s in states}
    for row, template in zip(rows, source_fixture.plan['model_inference_templates']):
        assert state_map[template['input_state_id']]['sha256'] == digest(row['input'].encode())
        assert state_map[template['output_state_id']]['sha256'] == digest(row['output'].encode())
    projected = canonical({'states': states, 'inferences': inferences})
    for row in rows:
        assert row['input'].encode() not in projected and row['output'].encode() not in projected
    assert all(r['usage']['total_tokens'] == 12 for r in inferences)
    assert len(next(iter(index.values()))['model_inference_ids']) == 6


@pytest.mark.parametrize('part', ['state', 'inference'])
def test_model_projection_matches_unchanged_generic_schema(source_fixture, part):
    states, inferences, _, _ = inference_projection(source_fixture)
    rows, definition = (states, 'state_observation') if part == 'state' else (inferences, 'model_inference_record')
    errors = [(row.get('state_id', row.get('inference_id')), schema_errors(row, definition)) for row in rows]
    failures = [(identifier, problems) for identifier, problems in errors if problems]
    assert failures == [], repr(failures[:2])


@pytest.mark.parametrize('mutation', ['wrong_model', 'wrong_revision', 'missing_model', 'missing_revision'])
def test_wrong_or_absent_observed_model_identity_cannot_use_plan_as_evidence(source_fixture, mutation):
    def change(rows):
        if mutation == 'wrong_model': rows[0]['model']['id'] = 'other/model'
        elif mutation == 'wrong_revision': rows[0]['model']['revision'] = 'b' * 40
        elif mutation == 'missing_model': rows[0].pop('model')
        elif mutation == 'missing_revision': rows[0]['model'].pop('revision')
    with pytest.raises(VERIFIER.VerificationError): inference_projection(source_fixture, mutate=change)


@pytest.mark.parametrize('field,value', [('prompt_tokens', True), ('prompt_tokens', -1),
    ('prompt_tokens', '10'), ('generated_tokens', None), ('generated_tokens', -1), ('generated_tokens', 1.5)])
def test_invalid_token_counts_reject(source_fixture, field, value):
    def change(rows): rows[0]['inference'][field] = value
    with pytest.raises(VERIFIER.VerificationError, match='model_usage_mismatch'):
        inference_projection(source_fixture, mutate=change)


@pytest.mark.parametrize('mutation', ['missing_case', 'duplicate_case', 'wrong_case'])
def test_inference_extent_cannot_be_repaired_by_names_or_equal_bytes(source_fixture, mutation):
    def change(rows):
        if mutation == 'missing_case': rows.pop()
        elif mutation == 'duplicate_case': rows[-1] = copy.deepcopy(rows[0])
        else: rows[0]['case_id'] = 'not-the-planned-case'
    with pytest.raises(VERIFIER.VerificationError): inference_projection(source_fixture, mutate=change)


def prepared_fixture_members(source_fixture):
    """Independently encode the declared prepared-carrier member contract."""
    f = source_fixture
    members = {
        'prelaunch-plan.json': f.plan_raw,
        'prelaunch-plan-diagnostic.json': f.diagnostic.read_bytes(),
        'expected-plan.sha256': (f.plan_digest + '\n').encode(),
        'source-inventory.json': canonical({'schema_version': 'pulsemech_compute_whole_runtime_observation_prepared_sources_v0',
             'record_status': 'example', 'repository': ACQUIRER.REPOSITORY, 'source_commit': f.sha,
             'members': f.plan['source_inventory'], 'authority_boundary': VERIFIER.AUTHORITY_BOUNDARY, 'errors': [], 'ok': True}),
        'dispatch-inputs.json': canonical({'subject': f.plan['subject_dispatch'], 'provider': f.plan['provider_dispatch'],
                                         'authority_boundary': VERIFIER.AUTHORITY_BOUNDARY}),
    }
    for row in f.plan['source_inventory']: members['sources/' + row['path']] = (f.root / row['path']).read_bytes()
    return members


def read_prepared_example(source_fixture, path):
    f = source_fixture
    return VERIFIER.read_prepared(path, source_commit=f.sha, expected_digest=f.plan_digest,
                                   record_status='example', schema=EVIDENCE_SCHEMA)


def test_independently_encoded_prepared_fixture_accepts(source_fixture, tmp_path):
    f = source_fixture; path = tmp_path / 'prepared.zip'
    members = prepared_fixture_members(f); path.write_bytes(example_zip(members))
    plan, restored, raw = read_prepared_example(f, path)
    assert plan == f.plan and restored == members and raw == path.read_bytes()


@pytest.mark.parametrize('mutation', ['extra_member', 'changed_dispatch_inputs'])
def test_prepared_carrier_is_closed_and_preserves_exact_dispatch_inputs(source_fixture, tmp_path, mutation):
    members = prepared_fixture_members(source_fixture)
    if mutation == 'extra_member': members['unreviewed.txt'] = b'unreviewed'
    else: members['dispatch-inputs.json'] = canonical({'subject': {'ref': 'other'}, 'provider': {}, 'authority_boundary': VERIFIER.AUTHORITY_BOUNDARY})
    path = tmp_path / 'tampered.zip'; path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError): read_prepared_example(source_fixture, path)


@pytest.mark.parametrize('mutation', ['missing_source', 'source_bytes', 'plan_bytes', 'diagnostic_bytes', 'expected_digest'])
def test_prepared_identity_mutations_reject(source_fixture, tmp_path, mutation):
    members = prepared_fixture_members(source_fixture)
    source = next(name for name in members if name.startswith('sources/'))
    if mutation == 'missing_source': members.pop(source)
    elif mutation == 'source_bytes': members[source] += b'\n'
    elif mutation == 'plan_bytes': members['prelaunch-plan.json'] += b'\n'
    elif mutation == 'diagnostic_bytes': members['prelaunch-plan-diagnostic.json'] = canonical({'ok': True})
    else: members['expected-plan.sha256'] = ('b'*64+'\n').encode()
    path = tmp_path / 'tampered.zip'; path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError): read_prepared_example(source_fixture, path)


# Source-schema intake is not a relaxation of canonical generated records.
def test_source_schema_formatting_does_not_change_record_serialization():
    raw = b'{ "type": "object", "properties": {} }\n'
    expected = {'type': 'object', 'properties': {}}
    assert VERIFIER.parse_source_schema(raw) == expected
    assert CAPTURER._json_object(raw, label='source_schema', canonical=False) == expected
    with pytest.raises(VERIFIER.VerificationError, match='noncanonical_json'):
        VERIFIER.parse_json_bytes(raw, label='generated_record')
    with pytest.raises(CAPTURER.CaptureError, match='noncanonical_json'):
        CAPTURER._json_object(raw, label='generated_record', canonical=True)


@pytest.mark.parametrize('raw', [
    b'\xef\xbb\xbf{}\n', b'{"type":"object","type":"array"}\n',
    b'{"maximum":NaN}\n', b'{"maximum":Infinity}\n', b'[]\n',
    b'{"title":"\xff"}\n', b'{"title":"e\\u0301"}\n',
])
def test_source_schema_still_rejects_unsafe_json(raw):
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.parse_source_schema(raw)
    with pytest.raises(CAPTURER.CaptureError):
        CAPTURER._json_object(raw, label='source_schema', canonical=False)


@pytest.mark.parametrize('mutation', [
    'schema_version', 'record_status', 'repository', 'authority_boundary',
    'errors', 'numeric_ok',
])
def test_prepared_source_metadata_cannot_disagree_with_plan(source_fixture, tmp_path, mutation):
    members = prepared_fixture_members(source_fixture)
    record = json.loads(members['source-inventory.json'])
    if mutation == 'schema_version': record['schema_version'] = 'unreviewed_v1'
    elif mutation == 'record_status': record['record_status'] = 'observed'
    elif mutation == 'repository': record['repository'] = 'other/repository'
    elif mutation == 'authority_boundary': record['authority_boundary']['active_gate_eligible'] = True
    elif mutation == 'errors': record['errors'] = ['unresolved']
    else: record['ok'] = 1  # Python equality alone must not equate 1 with True.
    members['source-inventory.json'] = canonical(record)
    path = tmp_path / 'changed-source-metadata.zip'
    path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError, match='prepared_source_inventory_mismatch'):
        read_prepared_example(source_fixture, path)


def test_prepared_dispatch_still_requires_canonical_record_bytes(source_fixture, tmp_path):
    members = prepared_fixture_members(source_fixture)
    doc = json.loads(members['dispatch-inputs.json'])
    members['dispatch-inputs.json'] = json.dumps(doc, separators=(',', ':')).encode()
    path = tmp_path / 'noncanonical-dispatch.zip'
    path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError, match='noncanonical_json'):
        read_prepared_example(source_fixture, path)


def test_prepared_schema_bytes_remain_bound_to_source_digest(source_fixture, tmp_path):
    members = prepared_fixture_members(source_fixture)
    member = 'sources/' + VERIFIER.SCHEMA_PATH
    members[member] += b'\n'
    path = tmp_path / 'changed-schema-source.zip'
    path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError, match='prepared_source_identity_mismatch'):
        read_prepared_example(source_fixture, path)


def test_reconstruction_launcher_uses_two_real_isolated_child_processes(tmp_path):
    # Executable stand-in for PROCESS LAUNCH mechanics only. It is not a fake
    # accepted Step5C reconstruction and is not used by any verifier-validity test.
    root = tmp_path / 'launch-boundary'; (root / 'tools').mkdir(parents=True)
    code = r'''import hashlib,json,pathlib,sys
assert sys.flags.isolated == 1 and sys.flags.ignore_environment == 1
args=sys.argv[1:]
assert args[0] == 'reconstruct'
out=pathlib.Path(args[args.index('--output')+1]); raw=b'EXAMPLE PROCESS-BOUNDARY OUTPUT; NOT A STEP5C CARRIER\n'
with out.open('xb') as handle: handle.write(raw)
print(json.dumps({'ok':True,'output_sha256':hashlib.sha256(raw).hexdigest(),'output_size_bytes':len(raw),
'inventory_sha256':hashlib.sha256(b'example').hexdigest(),'inventory_size_bytes':7,'subject_run_id':10001}))
'''
    (root / VERIFIER.VERIFIER_PATH).write_text(code)
    results = [VERIFIER._spawn_reconstruction(ordinal=i, root=root, source_commit='a'*40,
        prepared=tmp_path/'prepared.zip', capture=tmp_path/'capture.zip', expected_context=tmp_path/'expected.json',
        expected_digest=tmp_path/'plan.sha256', output=tmp_path/f'reconstruction-{i}.zip', record_status='example') for i in (1,2)]
    assert results[0].process_id != results[1].process_id
    assert results[0].output.read_bytes() == results[1].output.read_bytes()
    assert results[0].sha256 == results[1].sha256


def test_failed_reconstruction_child_is_not_a_reference(tmp_path):
    root = tmp_path / 'launch-boundary'; (root/'tools').mkdir(parents=True)
    (root / VERIFIER.VERIFIER_PATH).write_text('raise SystemExit(2)\n')
    output = tmp_path/'reconstruction.zip'
    with pytest.raises(VERIFIER.VerificationError, match='reconstruction_process_failed'):
        VERIFIER._spawn_reconstruction(ordinal=1, root=root, source_commit='a'*40,
            prepared=tmp_path/'prepared.zip', capture=tmp_path/'capture.zip', expected_context=tmp_path/'expected.json',
            expected_digest=tmp_path/'plan.sha256', output=output, record_status='example')
    assert not output.exists()


def test_source_contains_no_hidden_live_test_dispatch():
    tree = ast.parse(Path(__file__).read_text())
    # All outbound-capable production calls in this test program receive an
    # explicit example transport. There is no live-transport construction.
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == 'LiveGitHubTransport' for node in ast.walk(tree))


# The verifier calls this existing local proof builder; its workflow is not
# dispatched. Bind the exact source before observation, in both independent
# plan implementations, rather than removing the verifier's requirement.
STEP3G_BASELINE_SOURCE = (
    'tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py'
)
STEP3G_BASELINE_ROLE = 'current_run_artifact_observed_proof_builder'


def test_existing_baseline_source_is_declared_once_by_both_plan_tools():
    expected = (STEP3G_BASELINE_ROLE, STEP3G_BASELINE_SOURCE)
    for tool in (BUILDER, PLAN_CHECKER):
        assert tool.SOURCE_ROLES.count(expected) == 1
        assert sum(path == STEP3G_BASELINE_SOURCE for _, path in tool.SOURCE_ROLES) == 1
        assert len({role for role, _ in tool.SOURCE_ROLES}) == len(tool.SOURCE_ROLES)
        assert len({path for _, path in tool.SOURCE_ROLES}) == len(tool.SOURCE_ROLES)
    assert VERIFIER.STEP3G_PROOF_BUILDER_PATH == STEP3G_BASELINE_SOURCE


def test_existing_baseline_source_descriptor_matches_exact_git_bytes(source_fixture):
    f = source_fixture
    raw = (f.root / STEP3G_BASELINE_SOURCE).read_bytes()
    rows = [row for row in f.plan['source_inventory'] if row['path'] == STEP3G_BASELINE_SOURCE]
    assert rows == [{
        'role': STEP3G_BASELINE_ROLE,
        'path': STEP3G_BASELINE_SOURCE,
        'revision': f.sha,
        'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\x00' + raw).hexdigest(),
        'sha256': digest(raw),
        'size_bytes': len(raw),
        'executable': False,
    }]
    assert raw == (ROOT / STEP3G_BASELINE_SOURCE).read_bytes()
    assert f.diagnostic_doc['checks']['source_inventory_matches_git_objects'] is True


@pytest.mark.parametrize('mutation', [
    'omitted', 'role', 'path', 'revision', 'git_blob_sha1', 'sha256',
    'size_bytes', 'executable',
])
def test_rehashed_baseline_source_descriptor_cannot_bypass_plan_checker(
    source_fixture, tmp_path, mutation,
):
    f = source_fixture
    plan = copy.deepcopy(f.plan)
    row = next(row for row in plan['source_inventory'] if row['path'] == STEP3G_BASELINE_SOURCE)
    if mutation == 'omitted':
        plan['source_inventory'].remove(row)
    elif mutation == 'role':
        row['role'] = 'unreviewed_baseline_role'
    elif mutation == 'path':
        row['path'] = 'tools/unreviewed_baseline_proof_v0.py'
        plan['source_inventory'].sort(key=lambda item: item['path'])
    elif mutation in ('revision', 'git_blob_sha1'):
        row[mutation] = '0' * 40
    elif mutation == 'sha256':
        row['sha256'] = '0' * 64
    elif mutation == 'size_bytes':
        row['size_bytes'] += 1
    else:
        row['executable'] = not row['executable']
    # These mutations remain schema-valid and receive a newly computed external
    # digest. Rejection must come from independent source reconstruction.
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(plan)
    raw = canonical(plan)
    path = tmp_path / 'changed-baseline-source-plan.json'
    path.write_bytes(raw)
    result = cli(f.root, TOOL_NAMES[1], [
        '--repository-root', f.root, '--plan', path,
        '--expected-source-commit', f.sha,
        '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example',
    ])
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout or result.stderr)
    assert diagnostic['ok'] is False
    assert diagnostic['error_code'] == 'plan_reconstruction_mismatch'


def baseline_prepare_args(f, target):
    return [
        'prepare', '--repository-root', f.root, '--source-commit', f.sha,
        '--plan', f.plan_path, '--plan-diagnostic', f.diagnostic,
        '--expected-plan-sha256', f.plan_digest, '--output', target,
        '--record-status', 'example',
    ]


def test_two_real_prepares_preserve_the_complete_declared_source_set(
    source_fixture, tmp_path,
):
    f = source_fixture
    archives = []
    expected_members = prepared_fixture_members(f)
    source_member = 'sources/' + STEP3G_BASELINE_SOURCE
    for ordinal in (1, 2):
        target = tmp_path / f'prepared-{ordinal}.zip'
        result = cli(f.root, TOOL_NAMES[4], baseline_prepare_args(f, target))
        require_cli_success(result)
        raw = target.read_bytes()
        diagnostic = json.loads(result.stdout)
        assert diagnostic['ok'] is True
        assert diagnostic['record_status'] == 'example'
        assert diagnostic['output_sha256'] == digest(raw)
        assert diagnostic['output_size_bytes'] == len(raw)
        assert diagnostic['member_count'] == len(expected_members) == 40
        assert diagnostic['authority_boundary'] == VERIFIER.AUTHORITY_BOUNDARY
        plan, members, stored_raw = read_prepared_example(f, target)
        assert plan == f.plan and stored_raw == raw
        assert members == expected_members
        assert members[source_member] == (f.root / STEP3G_BASELINE_SOURCE).read_bytes()
        archives.append(raw)
    assert archives[0] == archives[1]


@pytest.mark.parametrize('mutation', ['omitted', 'changed_bytes'])
def test_prepared_baseline_source_cannot_be_removed_or_substituted(
    source_fixture, tmp_path, mutation,
):
    members = prepared_fixture_members(source_fixture)
    member = 'sources/' + STEP3G_BASELINE_SOURCE
    if mutation == 'omitted':
        members.pop(member)
        expected_error = 'prepared_source_member_missing'
    else:
        members[member] += b'\n# substituted baseline source\n'
        expected_error = 'prepared_source_identity_mismatch'
    # Rebuild the archive, including its ZIP CRCs, instead of relying on a
    # corrupt transport container to trigger rejection.
    path = tmp_path / 'changed-baseline-source.zip'
    path.write_bytes(example_zip(members))
    with pytest.raises(VERIFIER.VerificationError, match=expected_error):
        read_prepared_example(source_fixture, path)


def test_real_prepare_still_preserves_an_existing_destination(source_fixture, tmp_path):
    f = source_fixture
    target = tmp_path / 'existing-prepared.zip'
    original = b'Existing destination must remain unchanged.\n'
    target.write_bytes(original)
    result = cli(f.root, TOOL_NAMES[4], baseline_prepare_args(f, target))
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout or result.stderr)
    assert diagnostic['ok'] is False
    assert diagnostic['error_code'] == 'output_already_exists'
    assert target.read_bytes() == original



# ---------------------------------------------------------------------------
# Runtime projection repair: unchanged generic schema and semantic validator.
# These dictionaries are synthetic unit inputs, not verified capture carriers.
# In particular, exercising an observed-profile branch is NOT live acquisition.
# ---------------------------------------------------------------------------
GENERIC_VALIDATOR = load_module('check_pulsemech_compute_runtime_observation_packet_v0')


def runtime_projection_inputs(source_fixture, *, profile='example'):
    f = source_fixture
    jobs = example_jobs(f.plan, f.sha)
    member = 'acquisition/subject/jobs-page-0001.json'
    raw = canonical({'total_count': len(jobs), 'jobs': jobs})
    artifacts, envelope = provider_fixture(f.plan, f.sha)
    identity = minimal_capture_identity()
    # The generic example profile uses an inclusive simulated observation
    # window. The observed post-run profile admits earlier subject metadata.
    if profile == 'example':
        identity['capture_started_utc'] = EXAMPLE_START
    manifest = {
        'record_status': profile,
        'subject': {'run_id': EXAMPLE_SUBJECT_ID, 'run_number': 11, 'run_attempt': 1,
                    'head_sha': f.sha, 'event': 'workflow_dispatch'},
        'capture_identity': identity,
        'raw_response_bindings': [
            {'role': 'subject_jobs_page',
             'descriptor': {'member': member, 'sha256': digest(raw), 'size_bytes': len(raw)}}
        ],
    }
    members = {member: raw, VERIFIER.CAPTURE_PROVIDER_ENVELOPE_MEMBER: envelope}
    metadata, bindings = [], []
    for offset, (role, name_template, relative) in enumerate(ACQUIRER.SUBJECT_TERMINAL_ARTIFACT_TEMPLATES, 1):
        name, payload = name_template.format(run_id=EXAMPLE_SUBJECT_ID), artifacts[role]
        identifier, path = 40000 + offset, 'acquisition/' + relative
        members[path] = payload
        row = artifact_row(identifier, name, payload, f.sha, EXAMPLE_SUBJECT_ID)
        metadata.append(row)
        bindings.append({
            'artifact_role': 'subject_terminal_artifact', 'source_run_kind': 'subject',
            'artifact_id': identifier, 'artifact_name': name,
            'source_run_id': EXAMPLE_SUBJECT_ID, 'source_run_attempt': 1,
            'created_utc': EXAMPLE_END, 'expires_utc': EXAMPLE_EXPIRY, 'expired': False,
            'size_bytes': len(payload), 'github_sha256': digest(payload),
            'exact_bytes_in_capture': True, 'downloaded_member': path,
            'downloaded_sha256': digest(payload), 'downloaded_size_bytes': len(payload),
        })
    page_member = 'acquisition/subject/artifacts-page-0001.json'
    page_raw = canonical({'total_count': len(metadata), 'artifacts': metadata})
    members[page_member] = page_raw
    manifest['raw_response_bindings'].append({'role': 'subject_artifacts_page',
        'descriptor': {'member': page_member, 'sha256': digest(page_raw), 'size_bytes': len(page_raw)}})
    manifest['artifact_bindings'] = bindings
    return manifest, members


def runtime_projection_example(source_fixture, *, profile='example'):
    manifest, members = runtime_projection_inputs(source_fixture, profile=profile)
    return VERIFIER.build_runtime_packet(
        plan=source_fixture.plan, capture_manifest=manifest,
        capture_members=members, record_status=profile,
    )


@pytest.mark.parametrize('profile', ['example', 'observed'])
def test_projected_packet_matches_full_unchanged_generic_contract(source_fixture, profile):
    packet = runtime_projection_example(source_fixture, profile=profile)
    jsonschema.Draft202012Validator(GENERIC_SCHEMA).validate(packet)
    checks, errors = GENERIC_VALIDATOR.semantic_checks(packet)
    assert errors == [] and checks and all(checks.values()), (checks, errors)
    assert packet['record_status'] == profile
    assert packet['subject']['workflow_run_number'] == 11
    assert packet['coverage']['coverage_status'] == 'partial'
    assert len(packet['executions']) == 154
    assert len(packet['model_inferences']) == 6
    assert packet['resource_measurements'] == []
    assert packet['coverage']['resource_axes_unavailable'] == VERIFIER.RESOURCE_AXES
    assert packet['observation_boundary']['observer_in_subject_totals'] is False
    assert packet['observation_boundary']['subject_artifacts_mutated'] is False
    assert packet['packet_identity']['canonicalization'] == 'json-sort-keys-utf8-newline'
    assert packet['producer']['collection_mode'] == ('example' if profile == 'example' else 'post_run_platform_export')
    assert packet['packet_identity']['packet_scope'] == ('example' if profile == 'example' else 'subject_run')


@pytest.mark.parametrize('profile', ['example', 'observed'])
def test_projected_packet_real_isolated_generic_validator_cli(source_fixture, tmp_path, profile):
    packet_path = tmp_path / 'synthetic-projection-only.json'
    packet_path.write_bytes(canonical(runtime_projection_example(source_fixture, profile=profile)))
    result = cli(source_fixture.root, 'check_pulsemech_compute_runtime_observation_packet_v0', [
        '--schema', source_fixture.root / 'schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json',
        '--packet', packet_path,
    ])
    require_cli_success(result)
    diagnostic = json.loads(result.stdout)
    assert diagnostic['ok'] is True and diagnostic['schema_valid'] is True
    assert diagnostic['checks'] and all(diagnostic['checks'].values())


@pytest.mark.parametrize('mutation', [
    'subject_binding', 'collector_scope', 'collector_mutation', 'authority_digest',
    'state_producer', 'inference_parent', 'token_total', 'record_count',
    'duplicate_inference', 'false_complete_coverage',
])
def test_generic_validator_rejects_mutated_runtime_projection(source_fixture, mutation):
    packet = runtime_projection_example(source_fixture)
    collector = next(e for e in packet['executions'] if e['execution_scope'] == 'observation_collector')
    inference = packet['model_inferences'][0]
    if mutation == 'subject_binding': inference['subject_run_key'] = 'different-run'
    elif mutation == 'collector_scope': collector['execution_scope'] = 'subject'
    elif mutation == 'collector_mutation': packet['observation_boundary']['subject_artifacts_mutated'] = True
    elif mutation == 'authority_digest': packet['authority_inputs']['policy']['sha256'] = 'e' * 64
    elif mutation == 'state_producer': packet['state_observations'][0]['producer_execution_id'] = 'execution:missing'
    elif mutation == 'inference_parent': inference['parent_execution_id'] = collector['execution_id']
    elif mutation == 'token_total': inference['usage']['total_tokens'] += 1
    elif mutation == 'record_count': packet['coverage']['execution_records'] -= 1
    elif mutation == 'duplicate_inference': packet['model_inferences'].append(copy.deepcopy(inference))
    else: packet['coverage']['coverage_status'] = 'complete'
    schema_failures = list(jsonschema.Draft202012Validator(GENERIC_SCHEMA).iter_errors(packet))
    if not schema_failures:
        checks, errors = GENERIC_VALIDATOR.semantic_checks(packet)
        assert errors and not all(checks.values()), mutation


def test_source_step_numbers_are_not_platform_numbers(source_fixture):
    f = source_fixture
    jobs = example_jobs(f.plan, f.sha)
    expected = {s['occurrence_id']: s['source_ordinal'] for j in f.plan['jobs']
                for s in j['steps'] if s['expected_runtime_presence']}
    for job in jobs:
        for number, step in enumerate(job['steps'], 500): step['number'] = number
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    records, _ = VERIFIER._job_and_step_records(f.plan, jobs, key)
    for record in records:
        assert type(record['job_id']) is int
        if record['execution_kind'] == 'workflow_step':
            assert record['step_number'] == expected[record['execution_id']]
        assert record['result']['exit_code'] is None
        assert record['result']['outcome'] in ('success', 'skipped')
        assert record['command_identity']['arguments_sha256'] is None
        environment = record['execution_environment']
        assert environment['identity_status'] == 'partial'
        assert all(environment[k] is None for k in ('architecture', 'runtime_version', 'image_identity', 'image_digest'))


@pytest.mark.parametrize('mutation', [
    'duplicate_job', 'duplicate_job_id', 'missing_job', 'unknown_job',
    'cross_run', 'other_attempt', 'other_source', 'unfinished_job',
    'job_wrong_result', 'unexpected_step', 'duplicate_step', 'missing_step',
    'step_wrong_result', 'step_unfinished', 'skipped_job_has_steps',
])
def test_independent_projection_rejects_extent_and_identity_drift(source_fixture, mutation):
    f = source_fixture; jobs = example_jobs(f.plan, f.sha)
    first = jobs[0]
    if mutation == 'duplicate_job': jobs.append(copy.deepcopy(first))
    elif mutation == 'duplicate_job_id': jobs[-1]['id'] = first['id']
    elif mutation == 'missing_job': jobs.pop()
    elif mutation == 'unknown_job': jobs[-1]['name'] = 'unplanned job'
    elif mutation == 'cross_run': first['run_id'] += 1
    elif mutation == 'other_attempt': first['run_attempt'] = 2
    elif mutation == 'other_source': first['head_sha'] = 'e' * 40
    elif mutation == 'unfinished_job': first['status'] = 'in_progress'
    elif mutation == 'job_wrong_result': first['conclusion'] = 'skipped'
    elif mutation == 'unexpected_step':
        extra = copy.deepcopy(first['steps'][0]); extra['name'] = 'unplanned command'; first['steps'].append(extra)
    elif mutation == 'duplicate_step': first['steps'].insert(0, copy.deepcopy(first['steps'][0]))
    elif mutation == 'missing_step': first['steps'].pop()
    elif mutation == 'step_wrong_result': first['steps'][0]['conclusion'] = 'skipped'
    elif mutation == 'step_unfinished': first['steps'][0]['status'] = 'in_progress'
    else:
        skipped = next(j for j in jobs if j['conclusion'] == 'skipped')
        skipped['steps'] = [copy.deepcopy(first['steps'][0])]
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._job_and_step_records(f.plan, jobs, key)


def test_reviewed_lifecycle_records_remain_outside_subject_extent(source_fixture):
    f = source_fixture; jobs = example_jobs(f.plan, f.sha)
    base = copy.deepcopy(jobs[0]['steps'][0])
    jobs[0]['steps'].insert(0, dict(base, name='Set up job'))
    for name in ('Post Checkout', 'Post Set up Python', 'Complete job'):
        jobs[0]['steps'].append(dict(base, name=name))
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    records, index = VERIFIER._job_and_step_records(f.plan, jobs, key)
    assert len(records) == len(index) == 153
    assert not any(r['step_name'] in {'Set up job', 'Post Checkout', 'Post Set up Python', 'Complete job'} for r in records)


@pytest.mark.parametrize('field,value', [
    ('id', None), ('id', ''), ('id', True), ('id', []),
    ('revision', None), ('revision', ''), ('revision', True), ('revision', []),
])
def test_observed_model_identity_never_coerces_or_defaults(source_fixture, field, value):
    def mutate(rows): rows[0]['model'][field] = value
    with pytest.raises(VERIFIER.VerificationError, match='model_(identity|revision)_mismatch'):
        inference_projection(source_fixture, mutate=mutate)


def test_inference_parameters_and_model_revision_come_from_records(source_fixture):
    def mutate(rows):
        for row in rows:
            row['inference'].update({'manual_seed': 0, 'do_sample': False, 'num_beams': 1,
                                     'pad_token_id': 0, 'max_new_tokens': 32, 'device': 'cpu',
                                     'torch_threads': 2, 'total_tokens': 12})
    _, inferences, rows, _ = inference_projection(source_fixture, mutate=mutate)
    expected_model = source_fixture.plan['model_inference_templates'][0]
    recorded = {'manual_seed': 0, 'do_sample': False, 'num_beams': 1, 'pad_token_id': 0,
                'max_new_tokens': 32, 'device': 'cpu', 'torch_threads': 2}
    for inference in inferences:
        assert inference['model_identity']['model_id'] == expected_model['model_id']
        assert inference['model_identity']['model_revision'] == expected_model['model_revision']
        assert inference['model_identity']['model_content_digest_status'] == 'provider_revision_only'
        assert inference['model_identity']['model_sha256'] is None
        assert inference['provider_request_id_sha256'] is None
        assert inference['parameters'] == {
            'parameters_sha256': digest(canonical(recorded)), 'temperature': None,
            'top_p': None, 'max_output_tokens': 32, 'seed': 0, 'deterministic_mode': True,
        }


def test_missing_parameters_and_per_case_times_are_not_invented(source_fixture):
    _, inferences, _, _ = inference_projection(source_fixture)
    for inference in inferences:
        assert inference['parameters'] == {
            'parameters_sha256': digest(canonical({})), 'temperature': None,
            'top_p': None, 'max_output_tokens': None, 'seed': None, 'deterministic_mode': False,
        }
        assert inference['timing'] == VERIFIER._timing(None, None)
        assert inference['result']['exit_code'] is None
    collector = VERIFIER._collector_record(source_fixture.plan, {'capture_identity': minimal_capture_identity()}, 'example-subject-key')
    assert collector['timing'] == VERIFIER._timing(None, None)
    assert collector['result']['exit_code'] is None
    assert collector['command_identity']['command_sha256'] is None


@pytest.mark.parametrize('field,value', [
    ('manual_seed', True), ('max_new_tokens', True), ('max_new_tokens', -1),
    ('max_new_tokens', '32'), ('max_new_tokens', None), ('do_sample', 0),
    ('num_beams', -1), ('temperature', -0.1), ('top_p', 1.1), ('top_p', True),
])
def test_invalid_recorded_inference_parameters_reject(source_fixture, field, value):
    def mutate(rows): rows[0]['inference'][field] = value
    with pytest.raises(VERIFIER.VerificationError, match='model_parameters_invalid'):
        inference_projection(source_fixture, mutate=mutate)


@pytest.mark.parametrize('value', [11, 13, True, '12', None])
def test_recorded_token_total_must_equal_the_exact_integer_sum(source_fixture, value):
    def mutate(rows): rows[0]['inference']['total_tokens'] = value
    with pytest.raises(VERIFIER.VerificationError, match='model_usage_mismatch'):
        inference_projection(source_fixture, mutate=mutate)


def test_observed_generation_cannot_exceed_recorded_limit(source_fixture):
    def mutate(rows): rows[0]['inference']['max_new_tokens'] = 1
    with pytest.raises(VERIFIER.VerificationError, match='model_usage_mismatch'):
        inference_projection(source_fixture, mutate=mutate)


# ---------------------------------------------------------------------------
# Subject external-operation invocation boundaries. These remain synthetic
# projection tests, not a live acquisition, HTTP trace or full Step 5C replay.
# ---------------------------------------------------------------------------
def external_projection_inputs(source_fixture):
    f = source_fixture
    key = f'GITHUB_RUN_ID={EXAMPLE_SUBJECT_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    _, index = VERIFIER._job_and_step_records(f.plan, example_jobs(f.plan, f.sha), key)
    return copy.deepcopy(f.plan), index, key


def external_template_and_step(plan):
    steps = {s['occurrence_id']: s for j in plan['jobs'] for s in j['steps']}
    template = next(t for t in plan['external_operation_templates']
                    if t['owner'] == 'subject' and t['required']
                    and steps[t['parent_occurrence_id']]['expected_terminal_result'] == 'success'
                    and steps[t['parent_occurrence_id']]['source']['kind'] == 'github_action')
    return template, steps[template['parent_occurrence_id']]


@pytest.mark.parametrize('profile', ['example', 'observed'])
def test_external_projection_accounts_for_every_instantiated_subject_template(source_fixture, profile):
    plan = source_fixture.plan
    packet = runtime_projection_example(source_fixture, profile=profile)
    steps = {s['occurrence_id']: s for j in plan['jobs'] for s in j['steps']}
    templates = plan['external_operation_templates']
    subject = [t for t in templates if t['owner'] == 'subject']
    expected = {t['call_id'] for t in subject if steps[t['parent_occurrence_id']]['expected_runtime_presence']}
    calls = packet['external_calls']
    assert {c['call_id'] for c in calls} == expected
    assert len(calls) == len(expected) == 51
    assert len(subject) == 53 and len(templates) == 64
    assert Counter(c['result']['outcome'] for c in calls) == {'success': 29, 'skipped': 6, 'unknown': 16}
    assert packet['coverage']['external_call_records'] == len(calls)
    assert packet['coverage']['external_call_capture_status'] == 'partial'
    assert packet['coverage']['coverage_status'] == 'partial'
    assert len(packet['executions']) == 154 and len(packet['model_inferences']) == 6
    assert packet['resource_measurements'] == []
    assert 'external_api_calls' in packet['coverage']['resource_axes_unavailable']
    assert 'retry_count' in packet['coverage']['resource_axes_unavailable']
    index = {row['execution_id']: row for row in packet['executions']}
    for call in calls:
        parent = index[call['parent_execution_id']]
        assert parent['execution_scope'] == 'subject'
        assert parent['external_call_ids'].count(call['call_id']) == 1
    actual_refs = [v for row in packet['executions'] for v in row['external_call_ids']]
    assert Counter(actual_refs) == Counter(expected)
    outside = {t['call_id'] for t in templates if t['owner'] != 'subject'}
    assert not outside.intersection(actual_refs)
    collector = next(row for row in packet['executions'] if row['execution_scope'] == 'observation_collector')
    assert collector['external_call_ids'] == []
    jsonschema.Draft202012Validator(GENERIC_SCHEMA).validate(packet)
    checks, errors = GENERIC_VALIDATOR.semantic_checks(packet)
    assert errors == [] and all(checks.values()), (checks, errors)


def test_external_projection_preserves_absence_of_request_bodies_and_exact_call_times(source_fixture):
    packet = runtime_projection_example(source_fixture)
    for call in packet['external_calls']:
        assert call['capture_status'] == 'partial'
        assert call['request']['method'] == 'OTHER'
        assert call['request']['authorization_material_included'] is False
        assert call['request']['cookies_included'] is False
        assert call['response']['set_cookie_included'] is False
        assert call['response']['status_code'] is None
        assert call['provider_request_id_sha256'] is None
        assert call['service_identity']['endpoint_origin'] is None
        assert call['service_identity']['api_version'] is None
        assert call['service_identity']['identity_status'] == 'partial'
        assert call['timing'] == {'timing_status': 'unknown', 'started_utc': None,
                                 'completed_utc': None, 'duration_ms': None,
                                 'timestamp_source': 'unknown', 'duration_source': 'unknown'}
        assert call['result']['exit_code'] is None
        assert call['resource_measurement_ids'] == []
        for side in ('request', 'response'):
            payload = call[side]['payload']
            assert payload['body_sha256'] is None and payload['body_size_bytes'] is None
            assert payload['raw_body_included'] is False and payload['state_ids'] == []
        if call['result']['outcome'] == 'skipped':
            assert call['request']['payload']['capture_status'] == 'not_recorded'
            assert call['response']['payload']['capture_status'] == 'not_recorded'
            assert call['request']['payload']['metadata_sha256'] is None
            assert call['response']['payload']['metadata_sha256'] is None


def test_external_shell_steps_do_not_supply_successful_individual_call_results(source_fixture):
    packet = runtime_projection_example(source_fixture)
    templates = {t['call_id']: t for t in source_fixture.plan['external_operation_templates']}
    index = {row['execution_id']: row for row in packet['executions']}
    calls = [c for c in packet['external_calls'] if c['service_identity']['transport'] == 'other']
    assert len(calls) == 16
    for call in calls:
        parent = index[call['parent_execution_id']]
        assert parent['result']['outcome'] == 'success'
        assert call['result'] == {'result_status': 'unknown', 'lifecycle_status': 'unknown',
                                 'outcome': 'unknown', 'exit_code': None}
        assert call['response']['payload']['capture_status'] == 'not_recorded'
        assert call['request']['payload']['capture_status'] == templates[call['call_id']]['capture_requirement']


def test_external_action_metadata_digests_bind_exact_source_occurrence_and_platform_result(source_fixture):
    packet = runtime_projection_example(source_fixture)
    index = {row['execution_id']: row for row in packet['executions']}
    calls = [c for c in packet['external_calls'] if c['service_identity']['transport'] == 'github_actions'
             and c['result']['outcome'] == 'success']
    assert len(calls) == 29
    for call in calls:
        parent = index[call['parent_execution_id']]
        request = {'boundary': 'github_action_invocation', 'call_id': call['call_id'],
                   'parent_execution_id': parent['execution_id'], 'subject_run_key': call['subject_run_key'],
                   'source_identity': parent['source_identity'], 'command_identity': parent['command_identity']}
        response = {'boundary': 'github_action_platform_result', 'call_id': call['call_id'],
                    'parent_execution_id': parent['execution_id'], 'subject_run_key': call['subject_run_key'],
                    'job_id': parent['job_id'], 'job_attempt': parent['job_attempt'],
                    'source_ordinal': parent['step_number'], 'step_name': parent['step_name'],
                    'platform_result': parent['result']}
        assert call['request']['payload']['metadata_sha256'] == digest(canonical(request))
        assert call['response']['payload']['metadata_sha256'] == digest(canonical(response))
        assert call['request']['payload']['capture_status'] == 'metadata_only'
        assert call['response']['payload']['capture_status'] == 'metadata_only'


@pytest.mark.parametrize('mutation', [
    'empty_templates', 'missing_template', 'duplicate_template', 'unknown_owner',
    'owner_changed', 'wrong_parent', 'required_false', 'required_integer',
    'unknown_operation_class', 'different_action_class', 'exact_capture_without_evidence',
    'missing_step_reference', 'duplicate_step_reference', 'unmatched_step_reference',
    'authorization_included', 'cookies_included',
])
def test_external_projection_rejects_template_reference_and_visibility_drift(source_fixture, mutation):
    plan, index, key = external_projection_inputs(source_fixture)
    template, step = external_template_and_step(plan)
    identifier = template['call_id']
    if mutation == 'empty_templates': plan['external_operation_templates'] = []
    elif mutation == 'missing_template': plan['external_operation_templates'].remove(template)
    elif mutation == 'duplicate_template': plan['external_operation_templates'].append(copy.deepcopy(template))
    elif mutation == 'unknown_owner': template['owner'] = 'unknown'
    elif mutation == 'owner_changed': template['owner'] = 'supervisor'
    elif mutation == 'wrong_parent': template['parent_occurrence_id'] = 'execution:step5c:collector:post-run-platform-export'
    elif mutation == 'required_false': template['required'] = False
    elif mutation == 'required_integer': template['required'] = 1
    elif mutation == 'unknown_operation_class': template['operation_class'] = 'invented_service'
    elif mutation == 'different_action_class': template['operation_class'] = 'github_artifact_upload'
    elif mutation == 'exact_capture_without_evidence': template['capture_requirement'] = 'exact_digest'
    elif mutation == 'missing_step_reference': step['external_operation_ids'].remove(identifier)
    elif mutation == 'duplicate_step_reference': step['external_operation_ids'].append(identifier)
    elif mutation == 'unmatched_step_reference': step['external_operation_ids'].append('call:step5c:undeclared-operation')
    elif mutation == 'authorization_included': template['authorization_material_included'] = True
    elif mutation == 'cookies_included': template['cookies_included'] = True
    old_index = copy.deepcopy(index)
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._build_external_call_records(plan, index, key)
    assert index == old_index, 'Failure mutated execution records'


@pytest.mark.parametrize('mutation', [
    'missing', 'collector_scope', 'wrong_kind', 'identity', 'parent_job', 'workflow',
    'step_name', 'source_ordinal', 'attempt', 'boolean_attempt', 'run_key',
    'execution_run_key', 'binding_mode', 'source_digest', 'action_pin',
    'command_digest', 'result', 'fabricated_exit_code',
])
def test_external_projection_rejects_wrong_parent_run_source_and_terminal_evidence(source_fixture, mutation):
    plan, index, key = external_projection_inputs(source_fixture)
    template, step = external_template_and_step(plan)
    parent = index[template['parent_occurrence_id']]
    if mutation == 'missing': index.pop(template['parent_occurrence_id'])
    elif mutation == 'collector_scope': parent['execution_scope'] = 'observation_collector'
    elif mutation == 'wrong_kind': parent['execution_kind'] = 'workflow_job'
    elif mutation == 'identity': parent['execution_id'] += ':other'
    elif mutation == 'parent_job': parent['parent_execution_id'] += ':other'
    elif mutation == 'workflow': parent['workflow_name'] = 'Another workflow'
    elif mutation == 'step_name': parent['step_name'] = 'Another step'
    elif mutation == 'source_ordinal': parent['step_number'] += 1
    elif mutation == 'attempt': parent['job_attempt'] = 2
    elif mutation == 'boolean_attempt': parent['job_attempt'] = True
    elif mutation == 'run_key': parent['run_binding']['subject_run_key'] = 'another-subject'
    elif mutation == 'execution_run_key': parent['run_binding']['execution_run_key'] = 'another-execution'
    elif mutation == 'binding_mode': parent['run_binding']['binding_mode'] = 'post_run_observer'
    elif mutation == 'source_digest': parent['source_identity']['source_sha256'] = '0' * 64
    elif mutation == 'action_pin': parent['source_identity']['action_commit_sha'] = '0' * 40
    elif mutation == 'command_digest': parent['command_identity']['command_sha256'] = '0' * 64
    elif mutation == 'result': parent['result']['outcome'] = 'failure'
    elif mutation == 'fabricated_exit_code': parent['result']['exit_code'] = 0
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._build_external_call_records(plan, index, key)


@pytest.mark.parametrize('mutation', ['unexpected_parent', 'parent_job_not_skipped', 'missing_parent_job'])
def test_external_projection_does_not_invent_uninstantiated_occurrences(source_fixture, mutation):
    plan, index, key = external_projection_inputs(source_fixture)
    template = next(t for t in plan['external_operation_templates'] if t['owner'] == 'subject' and t['required'] is False)
    parent_id = template['parent_occurrence_id']
    job = next(j for j in plan['jobs'] if any(s['occurrence_id'] == parent_id for s in j['steps']))
    if mutation == 'unexpected_parent': index[parent_id] = {'execution_id': parent_id}
    elif mutation == 'parent_job_not_skipped': index[job['occurrence_id']]['result']['outcome'] = 'success'
    elif mutation == 'missing_parent_job': index.pop(job['occurrence_id'])
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._build_external_call_records(plan, index, key)


def test_external_projection_is_deterministic_and_does_not_mutate_its_inputs(source_fixture):
    plan, index, key = external_projection_inputs(source_fixture)
    before_plan, before_index = copy.deepcopy(plan), copy.deepcopy(index)
    first = VERIFIER._build_external_call_records(plan, index, key)
    second = VERIFIER._build_external_call_records(plan, index, key)
    assert canonical(first) == canonical(second)
    assert plan == before_plan and index == before_index
    assert [c['call_id'] for c in first] == sorted(c['call_id'] for c in first)
    assert canonical(runtime_projection_example(source_fixture)) == canonical(runtime_projection_example(source_fixture))


@pytest.mark.parametrize('mutation', ['omit_both', 'change_class', 'change_visibility', 'change_parent_and_reference'])
def test_rehashed_external_plan_changes_reject_through_real_independent_plan_checker(source_fixture, tmp_path, mutation):
    f = source_fixture
    plan = copy.deepcopy(f.plan)
    template, step = external_template_and_step(plan)
    if mutation == 'omit_both':
        step['external_operation_ids'].remove(template['call_id'])
        plan['external_operation_templates'].remove(template)
    elif mutation == 'change_class': template['operation_class'] = 'github_artifact_upload'
    elif mutation == 'change_visibility': template['capture_requirement'] = 'not_recorded'
    elif mutation == 'change_parent_and_reference':
        other = next(s for j in plan['jobs'] for s in j['steps'] if s['occurrence_id'] != step['occurrence_id'])
        step['external_operation_ids'].remove(template['call_id'])
        other['external_operation_ids'].append(template['call_id'])
        other['external_operation_ids'].sort()
        template['parent_occurrence_id'] = other['occurrence_id']
    path = tmp_path / 'rehashed-external-plan.json'
    path.write_bytes(canonical(plan))
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', path,
                 '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(path.read_bytes()),
                 '--expected-record-status', 'example'])
    assert result.returncode != 0, 'Rehashing cannot change the independently reconstructed operation graph'
    diagnostic = json.loads(result.stdout or result.stderr)
    assert diagnostic['ok'] is False and diagnostic['errors']


@pytest.mark.parametrize('mutation', ['delete_record', 'duplicate_record', 'wrong_parent', 'wrong_run', 'missing_reverse_reference'])
def test_generic_validator_rejects_external_record_binding_damage(source_fixture, mutation):
    packet = runtime_projection_example(source_fixture)
    call = packet['external_calls'][0]
    parent = next(e for e in packet['executions'] if e['execution_id'] == call['parent_execution_id'])
    if mutation == 'delete_record': packet['external_calls'].pop(0)
    elif mutation == 'duplicate_record': packet['external_calls'].insert(0, copy.deepcopy(call))
    elif mutation == 'wrong_parent': call['parent_execution_id'] = packet['observation_boundary']['collector_execution_id']
    elif mutation == 'wrong_run': call['subject_run_key'] = 'another-run'
    elif mutation == 'missing_reverse_reference': parent['external_call_ids'].remove(call['call_id'])
    _, errors = GENERIC_VALIDATOR.semantic_checks(packet)
    assert errors, 'External relation corruption must not remain valid'


def test_external_verdict_guard_accepts_the_declared_partial_invocation_projection(source_fixture):
    packet = runtime_projection_example(source_fixture)
    original = copy.deepcopy(packet)
    VERIFIER._require_external_projection_extent(source_fixture.plan, packet)
    assert packet == original


@pytest.mark.parametrize('mutation', [
    'erase_call_reference_and_count', 'erase_all_calls_references_and_count',
    'change_service', 'invent_http_status', 'invent_call_time', 'promote_capture_complete',
    'boolean_record_count',
])
def test_external_verdict_guard_rejects_self_consistent_erasure_or_strength_inflation(source_fixture, mutation):
    packet = runtime_projection_example(source_fixture)
    if mutation == 'erase_call_reference_and_count':
        call = packet['external_calls'].pop(0)
        parent = next(e for e in packet['executions'] if e['execution_id'] == call['parent_execution_id'])
        parent['external_call_ids'].remove(call['call_id'])
        packet['coverage']['external_call_records'] -= 1
    elif mutation == 'erase_all_calls_references_and_count':
        packet['external_calls'] = []
        for row in packet['executions']: row['external_call_ids'] = []
        packet['coverage']['external_call_records'] = 0
        packet['coverage']['external_call_capture_status'] = 'none'
    elif mutation == 'change_service': packet['external_calls'][0]['service_identity']['provider'] = 'another-provider'
    elif mutation == 'invent_http_status': packet['external_calls'][0]['response']['status_code'] = 200
    elif mutation == 'invent_call_time':
        parent_id = packet['external_calls'][0]['parent_execution_id']
        parent = next(e for e in packet['executions'] if e['execution_id'] == parent_id)
        packet['external_calls'][0]['timing'] = copy.deepcopy(parent['timing'])
    elif mutation == 'promote_capture_complete': packet['coverage']['external_call_capture_status'] = 'complete'
    elif mutation == 'boolean_record_count': packet['coverage']['external_call_records'] = True
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._require_external_projection_extent(source_fixture.plan, packet)


def test_real_verification_record_rejects_erased_external_extent_before_success_record(source_fixture, tmp_path):
    f = source_fixture
    packet = runtime_projection_example(f)
    packet['external_calls'] = []
    for row in packet['executions']: row['external_call_ids'] = []
    packet['coverage']['external_call_records'] = 0
    packet['coverage']['external_call_capture_status'] = 'none'
    # Generic internal consistency is not a prelaunch extent proof.
    jsonschema.Draft202012Validator(GENERIC_SCHEMA).validate(packet)
    checks, errors = GENERIC_VALIDATOR.semantic_checks(packet)
    assert not errors and all(checks.values())
    prepared = VERIFIER.deterministic_zip_bytes(
        prepared_fixture_members(f), maximum_members=VERIFIER.MAX_PREPARED_MEMBERS,
        maximum_bytes=VERIFIER.MAX_PREPARED_BYTES,
    )
    destination = tmp_path / 'must-not-exist'
    with pytest.raises(VERIFIER.VerificationError, match='external_operation_extent_mismatch'):
        VERIFIER._verification_record(
            root=f.root, source_commit=f.sha, prepared_path=destination, prepared_raw=prepared,
            capture_path=destination, capture_raw=b'', expected_context_path=destination,
            expected_context_raw=b'', expected_digest_path=destination, expected_digest_raw=b'',
            capture_manifest={}, reconstruction_members={VERIFIER.RUNTIME_PACKET_MEMBER: canonical(packet)},
            reconstruction_raw=b'', reconstructions=[], schema=EVIDENCE_SCHEMA, record_status='example',
        )
    assert not destination.exists()


# ---------------------------------------------------------------------------
# Declared state inventory and terminal ZIP binding. These are synthetic
# projection/negative-acceptance tests, not a successful full Step 5C replay.
# ---------------------------------------------------------------------------
STATE_SOURCE_IDS = (
    'state:step5c:workflow-source', 'state:step5c:gate-policy',
    'state:step5c:gate-registry', 'state:step5c:threshold-policy',
    'state:step5c:external-signer-policy', 'state:step5c:llamaguard-dataset',
)
STATE_TERMINAL_IDS = (
    'state:step5c:complete-release-grade-reference-package',
    'state:step5c:package-completeness-report',
    'state:step5c:package-verification-report',
)


@pytest.mark.parametrize('profile', ['example', 'observed'])
def test_declared_state_inventory_preserves_all_requirements_and_honest_gaps(source_fixture, profile):
    f = source_fixture
    packet = runtime_projection_example(f, profile=profile)
    states = {s['state_id']: s for s in packet['state_observations']}
    templates = {s['state_id']: s for s in f.plan['state_templates']}
    assert set(states) == set(templates) and len(states) == 57
    assert Counter(s['content_status'] for s in states.values()) == {
        'exact_digest': 21, 'unavailable': 36,
    }
    assert packet['coverage']['state_records'] == 57
    assert packet['coverage']['state_digest_capture_status'] == 'partial'
    assert packet['coverage']['coverage_status'] == 'partial'
    assert 'post_decision_state_unavailable' in packet['coverage']['unobserved_reasons']
    for state_id, state in states.items():
        template = templates[state_id]
        assert state['authority_bearing'] is template['authority_bearing']
        assert state['mutation_class'] == template['mutation_class']
        assert state['subject_run_key'] == packet['subject']['subject_run_key']
        assert state['release_candidate_id'] == packet['subject']['release_candidate_id']
        assert state['observer_execution_id'] == packet['observation_boundary']['collector_execution_id']
        assert state['secret_material_included'] is False
        if state['content_status'] == 'unavailable':
            assert state['sha256'] is None and state['size_bytes'] is None
            assert state['producer_execution_id'] is None
            assert all(state_id not in e['input_state_ids'] + e['output_state_ids'] for e in packet['executions'])
    jsonschema.Draft202012Validator(GENERIC_SCHEMA).validate(packet)
    checks, errors = GENERIC_VALIDATOR.semantic_checks(packet)
    assert not errors and all(checks.values())


@pytest.mark.parametrize('state_id', STATE_SOURCE_IDS)
def test_declared_source_state_uses_exact_plan_id_path_and_source_binding(source_fixture, state_id):
    f = source_fixture
    packet = runtime_projection_example(f)
    state = next(s for s in packet['state_observations'] if s['state_id'] == state_id)
    template = next(s for s in f.plan['state_templates'] if s['state_id'] == state_id)
    source = next(s for s in f.plan['source_inventory'] if s['path'] == template['path_or_uri'])
    assert state['path_or_uri'] == source['path']
    assert state['content_status'] == 'exact_digest'
    assert state['sha256'] == source['sha256'] == digest((f.root / source['path']).read_bytes())
    assert state['size_bytes'] == source['size_bytes']
    assert state['producer_execution_id'] is None and state['authority_bearing'] is True
    # Do not convert expected consumers into proven observed reads.
    assert all(state_id not in e['input_state_ids'] + e['output_state_ids'] for e in packet['executions'])


@pytest.mark.parametrize('case_index', range(6))
def test_inference_states_keep_declared_production_and_authority_identity(source_fixture, case_index):
    f = source_fixture; states, _, _, index = inference_projection(f)
    actual = {s['state_id']: s for s in states}
    templates = {s['state_id']: s for s in f.plan['state_templates']}
    inference = f.plan['model_inference_templates'][case_index]
    for field in ('input_state_id', 'output_state_id'):
        state = actual[inference[field]]; template = templates[inference[field]]
        assert state['path_or_uri'] == template['path_or_uri']
        assert state['state_type'] == 'release_evidence'
        assert state['authority_bearing'] is True
        assert state['producer_execution_id'] == template['producer_occurrence_id']
    assert actual[inference['input_state_id']]['producer_execution_id'] is None
    assert actual[inference['output_state_id']]['producer_execution_id'] == inference['parent_occurrence_id']
    assert inference['input_state_id'] in index[inference['parent_occurrence_id']]['input_state_ids']
    assert inference['output_state_id'] in index[inference['parent_occurrence_id']]['output_state_ids']


@pytest.mark.parametrize('state_id', STATE_TERMINAL_IDS)
def test_terminal_state_binds_captured_archive_without_inventing_producer_or_read(source_fixture, state_id):
    f = source_fixture; manifest, members = runtime_projection_inputs(f)
    before = dict(members)
    packet = VERIFIER.build_runtime_packet(plan=f.plan, capture_manifest=manifest,
        capture_members=members, record_status='example')
    state = next(s for s in packet['state_observations'] if s['state_id'] == state_id)
    name = state['path_or_uri'].removeprefix('artifact://')
    binding = next(b for b in manifest['artifact_bindings'] if b['artifact_name'] == name)
    assert state['sha256'] == binding['github_sha256'] == digest(members[binding['downloaded_member']])
    assert state['size_bytes'] == len(members[binding['downloaded_member']])
    assert state['media_type'] == 'application/zip' and state['content_status'] == 'exact_digest'
    assert state['producer_execution_id'] is None
    assert all(state_id not in e['input_state_ids'] + e['output_state_ids'] for e in packet['executions'])
    assert members == before


def test_real_capture_to_declared_state_projection_keeps_capture_bytes_unchanged(source_fixture, acquisition_fixture):
    f = source_fixture
    captured = construct_capture(f, acquisition_fixture, 'capture-for-state-projection.zip')
    before = captured.path.read_bytes()
    packet = VERIFIER.build_runtime_packet(plan=f.plan, capture_manifest=captured.manifest,
        capture_members=captured.members, record_status='example')
    assert len(packet['state_observations']) == 57
    VERIFIER._require_state_projection(f.plan, packet, captured.manifest, captured.members)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(f.plan, packet, {})
    assert captured.path.read_bytes() == before


def state_rebind_artifact_page(manifest, members, page, ordinal=1):
    path = f'acquisition/subject/artifacts-page-{ordinal:04d}.json'
    raw = canonical(page); members[path] = raw
    binding = next(b for b in manifest['raw_response_bindings'] if b['descriptor']['member'] == path)
    binding['descriptor'] = {'member': path, 'sha256': digest(raw), 'size_bytes': len(raw)}


@pytest.mark.parametrize('artifact_index', range(3))
@pytest.mark.parametrize('mutation', [
    'wrong_run', 'wrong_attempt', 'wrong_artifact_id', 'wrong_name',
    'wrong_download_member', 'changed_bytes_rehashed_capture_binding',
    'wrong_size', 'missing_bytes', 'missing_binding', 'duplicate_binding',
    'wrong_source_revision', 'wrong_branch', 'expired_metadata',
    'raw_digest_disagrees', 'raw_size_disagrees', 'boolean_attempt',
])
def test_terminal_state_rejects_mismatched_capture_metadata_or_exact_bytes(source_fixture, artifact_index, mutation):
    f=source_fixture; manifest, members=runtime_projection_inputs(f)
    binding = manifest['artifact_bindings'][artifact_index]
    page = json.loads(members['acquisition/subject/artifacts-page-0001.json'])
    raw_row = page['artifacts'][artifact_index]
    if mutation == 'wrong_run': binding['source_run_id'] += 1
    elif mutation == 'wrong_attempt': binding['source_run_attempt'] = 2
    elif mutation == 'wrong_artifact_id': binding['artifact_id'] += 50
    elif mutation == 'wrong_name': binding['artifact_name'] += '-copy'
    elif mutation == 'wrong_download_member': binding['downloaded_member'] += '-copy'
    elif mutation == 'changed_bytes_rehashed_capture_binding':
        member = binding['downloaded_member']; members[member] += b'changed'
        binding['github_sha256'] = binding['downloaded_sha256'] = digest(members[member])
        binding['size_bytes'] = binding['downloaded_size_bytes'] = len(members[member])
    elif mutation == 'wrong_size': binding['downloaded_size_bytes'] += 1
    elif mutation == 'missing_bytes': members.pop(binding['downloaded_member'])
    elif mutation == 'missing_binding': manifest['artifact_bindings'].pop(artifact_index)
    elif mutation == 'duplicate_binding': manifest['artifact_bindings'].append(copy.deepcopy(binding))
    elif mutation == 'wrong_source_revision': raw_row['workflow_run']['head_sha'] = 'e' * 40
    elif mutation == 'wrong_branch': raw_row['workflow_run']['head_branch'] = 'other'
    elif mutation == 'expired_metadata': raw_row['expired'] = True
    elif mutation == 'raw_digest_disagrees': raw_row['digest'] = 'sha256:' + 'd' * 64
    elif mutation == 'raw_size_disagrees': raw_row['size_in_bytes'] += 1
    else: binding['source_run_attempt'] = True
    state_rebind_artifact_page(manifest, members, page)
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.build_runtime_packet(plan=f.plan, capture_manifest=manifest,
            capture_members=members, record_status='example')


@pytest.mark.parametrize('mutation', [
    'missing_page', 'duplicate_page', 'duplicate_artifact', 'wrong_page_digest',
    'wrong_total', 'empty_rows', 'boolean_total', 'oversized_total',
])
def test_terminal_state_metadata_page_closure_is_fail_closed(source_fixture, mutation):
    f=source_fixture; manifest, members=runtime_projection_inputs(f)
    page=json.loads(members['acquisition/subject/artifacts-page-0001.json'])
    if mutation == 'missing_page': members.pop('acquisition/subject/artifacts-page-0001.json')
    elif mutation == 'duplicate_page': manifest['raw_response_bindings'].append(copy.deepcopy(manifest['raw_response_bindings'][-1]))
    elif mutation == 'wrong_page_digest': manifest['raw_response_bindings'][-1]['descriptor']['sha256'] = 'd' * 64
    else:
        if mutation == 'duplicate_artifact': page['artifacts'][1]=copy.deepcopy(page['artifacts'][0])
        elif mutation == 'wrong_total': page['total_count'] += 1
        elif mutation == 'empty_rows': page['artifacts']=[]
        elif mutation == 'boolean_total': page['total_count']=True
        else: page['total_count']=257
        state_rebind_artifact_page(manifest,members,page)
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.build_runtime_packet(plan=f.plan,capture_manifest=manifest,
            capture_members=members,record_status='example')


def test_terminal_state_accepts_bounded_complete_multiple_pages(source_fixture):
    f=source_fixture; manifest,members=runtime_projection_inputs(f)
    page=json.loads(members['acquisition/subject/artifacts-page-0001.json'])
    values=page['artifacts']
    state_rebind_artifact_page(manifest,members,{'total_count':3,'artifacts':values[:1]})
    second='acquisition/subject/artifacts-page-0002.json'
    raw=canonical({'total_count':3,'artifacts':values[1:]});members[second]=raw
    manifest['raw_response_bindings'].append({'role':'subject_artifacts_page',
        'descriptor':{'member':second,'sha256':digest(raw),'size_bytes':len(raw)}})
    packet=VERIFIER.build_runtime_packet(plan=f.plan,capture_manifest=manifest,capture_members=members,record_status='example')
    assert len(packet['state_observations']) == 57


@pytest.mark.parametrize('mutation', [
    'delete_state_and_count','invent_digest','invent_producer','invent_consumer',
    'wrong_source_digest','wrong_path','wrong_authority_flag','wrong_mutation_class',
    'wrong_run','wrong_candidate','boolean_count','promote_digest_coverage',
])
def test_state_projection_guard_rejects_erasure_and_unsupported_promotions(source_fixture, mutation):
    f=source_fixture; manifest,members=runtime_projection_inputs(f)
    packet=runtime_projection_example(f)
    missing=next(s for s in packet['state_observations'] if s['content_status']=='unavailable')
    if mutation=='delete_state_and_count':
        packet['state_observations'].remove(missing);packet['coverage']['state_records']-=1
    elif mutation=='invent_digest':
        missing.update(content_status='exact_digest',sha256='a'*64,size_bytes=5)
    elif mutation=='invent_producer': missing['producer_execution_id']=packet['executions'][0]['execution_id']
    elif mutation=='invent_consumer':
        # Consumption is a separate obligation: this mutation must also be
        # rejected without turning declared expected reads into observations.
        packet['executions'][0]['input_state_ids'].append(missing['state_id'])
    elif mutation=='wrong_source_digest': next(s for s in packet['state_observations'] if s['state_id']==STATE_SOURCE_IDS[0])['sha256']='b'*64
    elif mutation=='wrong_path': missing['path_or_uri']='other/path'
    elif mutation=='wrong_authority_flag': missing['authority_bearing']=not missing['authority_bearing']
    elif mutation=='wrong_mutation_class': missing['mutation_class']='preservation_output'
    elif mutation=='wrong_run': missing['subject_run_key']='other-run'
    elif mutation=='wrong_candidate': missing['release_candidate_id']='other-candidate'
    elif mutation=='boolean_count': packet['coverage']['state_records']=True
    else: packet['coverage']['state_digest_capture_status']='complete'
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER._require_state_projection(f.plan,packet,manifest,members)


def test_state_projection_guard_accepts_exact_partial_projection_without_mutation(source_fixture):
    f=source_fixture;manifest,members=runtime_projection_inputs(f);packet=runtime_projection_example(f)
    before=copy.deepcopy(packet)
    VERIFIER._require_state_projection(f.plan,packet,manifest,members)
    assert packet==before


def test_state_completion_rejects_even_with_available_downstream_output_bytes(source_fixture):
    f=source_fixture;packet=runtime_projection_example(f)
    # Stand-ins only on a rejection path; these are NOT valid replay outputs.
    outputs={name:b'example rejection-only output\n' for name in VERIFIER.DERIVED_STATE_MEMBERS.values()}
    outputs[VERIFIER.RUNTIME_PACKET_MEMBER]=canonical(packet)
    with pytest.raises(VERIFIER.VerificationError,match='declared_state_evidence_incomplete') as caught:
        VERIFIER._require_declared_state_completion(f.plan,packet,outputs)
    missing=set(caught.value.detail.split(','))
    assert 'state:step5c:final-status' in missing
    assert set(STATE_TERMINAL_IDS) <= missing  # exact ZIP bytes do not prove the producing step
    assert not set(VERIFIER.DERIVED_STATE_MEMBERS) & missing


def test_real_verification_record_cannot_publish_complete_state_extent_from_partial_packet(source_fixture,tmp_path):
    f=source_fixture;manifest,members=runtime_projection_inputs(f);packet=runtime_projection_example(f)
    prepared=VERIFIER.deterministic_zip_bytes(prepared_fixture_members(f),
        maximum_members=VERIFIER.MAX_PREPARED_MEMBERS,maximum_bytes=VERIFIER.MAX_PREPARED_BYTES)
    capture_members={**members,VERIFIER.CAPTURE_MANIFEST_MEMBER:canonical(manifest)}
    capture=VERIFIER.deterministic_zip_bytes(capture_members,
        maximum_members=VERIFIER.MAX_CAPTURE_MEMBERS,maximum_bytes=VERIFIER.MAX_CAPTURE_BYTES)
    destination=tmp_path/'must-not-exist'
    with pytest.raises(VERIFIER.VerificationError,match='declared_state_evidence_incomplete'):
        VERIFIER._verification_record(root=f.root,source_commit=f.sha,
            prepared_path=destination,prepared_raw=prepared,capture_path=destination,capture_raw=capture,
            expected_context_path=destination,expected_context_raw=b'',expected_digest_path=destination,
            expected_digest_raw=b'',capture_manifest=manifest,
            reconstruction_members={VERIFIER.RUNTIME_PACKET_MEMBER:canonical(packet)},
            reconstruction_raw=b'',reconstructions=[],schema=EVIDENCE_SCHEMA,record_status='example')
    assert not destination.exists()


class _CompleteProgramGuard:
    """Direct-script CI execution must collect and finish the complete program."""
    def __init__(self):
        self.selected = 0
        self.completed = set()
        self.omitted = False
        self.incomplete = False

    def pytest_collection_finish(self, session):
        self.selected = len(session.items)

    def pytest_deselected(self, items):
        if items: self.omitted = True

    def pytest_runtest_logreport(self, report):
        if report.skipped or hasattr(report, 'wasxfail'): self.incomplete = True
        if report.when == 'call': self.completed.add(report.nodeid)

    def pytest_sessionfinish(self, session, exitstatus):
        if self.selected == 0 or self.omitted or self.incomplete or len(self.completed) != self.selected:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


if __name__ == '__main__':
    # The registered CI script runs the WHOLE program. No command-line filters
    # or environment-supplied plugin/options can silently trim it.
    for key in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_CURRENT_TEST'):
        os.environ.pop(key, None)
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    raise SystemExit(pytest.main(['-q', '-o', 'addopts=', str(Path(__file__).resolve())], plugins=[_CompleteProgramGuard()]))
