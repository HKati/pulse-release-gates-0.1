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
import inspect
import textwrap
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
    assert len(f.plan['source_inventory']) == len(BUILDER.SOURCE_ROLES) == 56


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
        assert diagnostic['member_count'] == len(expected_members) == 61
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
    assert set(states) == set(templates) and len(states) == 62
    assert Counter(s['content_status'] for s in states.values()) == {
        'exact_digest': 21, 'unavailable': 41,
    }
    assert packet['coverage']['state_records'] == 62
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
    assert len(packet['state_observations']) == 62
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
    assert len(packet['state_observations']) == 62


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


# ---------------------------------------------------------------------------
# R2 schema foundation. These are normative-definition checks, not a replacement
# mapping, observed acquisition, supported R2 wire record, or acceptance proof.
# The root record branches intentionally remain unchanged in this checkpoint.
# ---------------------------------------------------------------------------
R2_PROFILE_ID = 'pulsemech_step5c_post_run_state_evidence_v1'
R2_DEFINITION_PREFIX = 'post_run_state_evidence_v1_'
R2_CONTRACT_PATH = (
    ROOT / 'docs/compute/PULSEMECH_COMPUTE_WHOLE_RUNTIME_OBSERVATION_CONTRACT_v0.md'
)
R2_CONTRACT_ROLE_ROWS = re.findall(
    r'^\| `(state:step5c:[^`]+)` \| `([^`]+)` \|\s*$',
    R2_CONTRACT_PATH.read_text(encoding='utf-8'), re.M,
)
R2_CONTRACT_ROLES = dict(R2_CONTRACT_ROLE_ROWS)
R2_SUBJECT_SELECTORS = {
    'complete_release_grade_reference_package': 'complete-release-grade-reference-package-{subject_run_id}-1',
    'package_completeness_report': 'release-grade-package-completeness-{subject_run_id}-1',
    'package_verification_report': 'release-grade-reference-package-verification-{subject_run_id}-1',
    'release_grade_recorded_path': 'release-grade-recorded-path-{subject_run_id}-1',
    'pre_attestation_pulse_artifacts': 'pulse-pre-attestation-{subject_run_id}-1',
    'advisory_reference_bundle': 'release-grade-reference-run-v0',
}
R2_LIMITATIONS = {
    'pre_insertion_ledger_content': 'unavailable',
    'pre_insertion_ledger_transition': 'unproved',
    'final_binding_signed_receipt': 'unavailable',
    'final_binding_signature_verification': 'unproved',
    'original_runtime_argv_receipt': 'unproved',
    'original_runtime_read_relationships': 'not_complete',
    'whole_runtime_relational_coverage': 'partial',
    'wider_fixed_source_runtime_comparison': 'not_complete',
    'resource_coverage': 'unavailable',
    'generic_runtime_coverage': 'partial',
}


def r2_definition_example():
    """Normative configuration built from the contract, never from the schema."""
    return {
        'evidence_profile': R2_PROFILE_ID,
        'topology_profile': 'pulse_ci_hosted_release_grade_v0',
        'role_obligations': dict(R2_CONTRACT_ROLES),
        'required_subject_archives': dict(R2_SUBJECT_SELECTORS),
        'required_provider_artifact': {
            'workflow_path': '.github/workflows/pulsemech_compute_current_run_export_candidate.yml',
            'artifact_name_template': 'pulsemech-compute-current-run-export-candidate-{subject_run_id}-1',
            'source_run_kind': 'provider',
        },
        'limitations': dict(R2_LIMITATIONS),
        'authority_boundary': copy.deepcopy(ACQUIRER.AUTHORITY_BOUNDARY),
    }


def r2_definition_validator():
    # Explicitly select an inactive definition for its schema-unit test.
    # The production root schema is not changed to reference it.
    return jsonschema.Draft202012Validator({
        '$schema': EVIDENCE_SCHEMA['$schema'],
        '$defs': EVIDENCE_SCHEMA['$defs'],
        '$ref': '#/$defs/' + R2_DEFINITION_PREFIX + 'definition',
    })


def _schema_definition_reachability(schema):
    pending = [value['$ref'].removeprefix('#/$defs/') for value in schema['oneOf']]
    reached = set()
    def references(value):
        if isinstance(value, dict):
            ref = value.get('$ref')
            if isinstance(ref, str) and ref.startswith('#/$defs/'):
                yield ref.removeprefix('#/$defs/')
            for child in value.values():
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        pending.extend(references(schema['$defs'][name]))
    return reached


def test_r2_normative_definition_matches_the_complete_contract_inventory():
    assert len(R2_CONTRACT_ROLE_ROWS) == len(R2_CONTRACT_ROLES) == 62
    assert all(role.startswith('state:step5c:') for role in R2_CONTRACT_ROLES)
    assert R2_CONTRACT_ROLES['state:step5c:quality-ledger-pre-authority'] == 'required_explicit_content_gap'
    assert R2_CONTRACT_ROLES['state:step5c:artifact-binding-attestation'] == 'required_action_metadata_with_receipt_gap'
    assert R2_CONTRACT_ROLES['state:step5c:advisory-reference-bundle'] == 'exact_preserved_tree_and_carrier'
    assert len(R2_SUBJECT_SELECTORS) == 6
    jsonschema.Draft202012Validator.check_schema(EVIDENCE_SCHEMA)
    r2_definition_validator().validate(r2_definition_example())


def test_r2_schema_foundation_is_not_reachable_from_active_record_branches():
    assert EVIDENCE_SCHEMA['oneOf'] == [
        {'$ref': '#/$defs/prelaunch_plan'},
        {'$ref': '#/$defs/dispatch_receipt'},
        {'$ref': '#/$defs/capture_manifest'},
        {'$ref': '#/$defs/verification_record'},
    ]
    added = {name for name in EVIDENCE_SCHEMA['$defs'] if name.startswith(R2_DEFINITION_PREFIX)}
    assert len(added) == 6
    assert not added.intersection(_schema_definition_reachability(EVIDENCE_SCHEMA))
    assert not jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).is_valid(r2_definition_example())


def test_r2_root_activation_changes_are_detected_by_the_reachability_check():
    schema = copy.deepcopy(EVIDENCE_SCHEMA)
    target = R2_DEFINITION_PREFIX + 'definition'
    schema['oneOf'].append({'$ref': '#/$defs/' + target})
    assert target in _schema_definition_reachability(schema)


@pytest.mark.parametrize('field', list(r2_definition_example()))
def test_r2_definition_rejects_missing_top_level_fields(field):
    value = r2_definition_example()
    del value[field]
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('field,value', [
    ('evidence_profile', None), ('evidence_profile', ''),
    ('evidence_profile', 'pulse_ci_hosted_release_grade_v0'),
    ('evidence_profile', 'pulsemech_step5c_post_run_state_evidence_v0'),
    ('evidence_profile', R2_PROFILE_ID + '\n'),
    ('topology_profile', R2_PROFILE_ID), ('topology_profile', 'future_topology'),
])
def test_r2_definition_rejects_missing_stale_unknown_or_swapped_identity(field, value):
    example = r2_definition_example()
    example[field] = value
    assert not r2_definition_validator().is_valid(example)


@pytest.mark.parametrize('role', sorted(R2_CONTRACT_ROLES))
def test_r2_every_review_role_remains_mandatory_in_the_definition(role):
    value = r2_definition_example()
    del value['role_obligations'][role]
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('role', sorted(R2_CONTRACT_ROLES))
def test_r2_role_obligation_cannot_be_reassigned_to_another_admitted_strength(role):
    value = r2_definition_example()
    original = value['role_obligations'][role]
    value['role_obligations'][role] = (
        'exact_preserved_content' if original == 'required_explicit_content_gap'
        else 'required_explicit_content_gap'
    )
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('role', sorted(R2_SUBJECT_SELECTORS))
@pytest.mark.parametrize('mutation', ['remove', 'rename'])
def test_r2_each_selected_subject_archive_is_exactly_required(role, mutation):
    value = r2_definition_example()
    if mutation == 'remove':
        del value['required_subject_archives'][role]
    else:
        value['required_subject_archives'][role] += '-other'
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('field', ['workflow_path', 'artifact_name_template', 'source_run_kind'])
def test_r2_provider_cannot_be_selected_as_a_subject_archive(field):
    value = r2_definition_example()
    value['required_provider_artifact'][field] = {
        'workflow_path': '.github/workflows/pulse_ci.yml',
        'artifact_name_template': 'pulse-pre-attestation-{subject_run_id}-1',
        'source_run_kind': 'subject',
    }[field]
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('field', sorted(R2_LIMITATIONS))
@pytest.mark.parametrize('mutation', ['remove', 'promote'])
def test_r2_declared_limitations_cannot_be_erased_or_promoted_to_completion(field, mutation):
    value = r2_definition_example()
    if mutation == 'remove':
        del value['limitations'][field]
    else:
        value['limitations'][field] = 'complete'
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('field', ['role_obligations', 'required_subject_archives',
                                   'required_provider_artifact', 'limitations', 'authority_boundary'])
def test_r2_definition_rejects_unknown_nested_fields(field):
    value = r2_definition_example()
    value[field]['unexpected'] = True
    assert not r2_definition_validator().is_valid(value)


@pytest.mark.parametrize('field,value', [('ok', True), ('I', 'complete'),
                                       ('E', 'complete'), ('runtime_observed', True)])
def test_r2_normative_definition_is_not_a_verification_result(field, value):
    example = r2_definition_example()
    example[field] = value
    assert not r2_definition_validator().is_valid(example)


@pytest.mark.parametrize('field', ['same_run_release_authority_eligible', 'active_gate_eligible'])
def test_r2_definition_does_not_authorize_release(field):
    example = r2_definition_example()
    example['authority_boundary'][field] = True
    assert not r2_definition_validator().is_valid(example)


@pytest.mark.parametrize('field', ['evidence_profile', 'state_evidence_profile'])
def test_r2_tag_cannot_upgrade_a_legacy_plan_through_the_current_checker(source_fixture, tmp_path, field):
    f = source_fixture
    document = copy.deepcopy(f.plan)
    document[field] = R2_PROFILE_ID if field == 'evidence_profile' else r2_definition_example()
    raw = canonical(document)
    path = tmp_path / 'not_an_r2_plan.json'
    path.write_bytes(raw)
    assert not jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).is_valid(document)
    result = cli(f.root, TOOL_NAMES[1], [
        '--repository-root', f.root, '--plan', path,
        '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example',
    ])
    assert result.returncode != 0
    error = json.loads(result.stdout or result.stderr)
    assert error['ok'] is False and error['errors']


# ---------------------------------------------------------------------------
# Active source-grounded ledger/report mapping. Expected semantic answers below
# come from workflow command arguments, not either plan table. Fault-injection
# tests exercise the source-equation boundary; they are not acquired evidence.
# ---------------------------------------------------------------------------
def mapping_source_document():
    return yaml.load((ROOT / BUILDER.SUBJECT_WORKFLOW_PATH).read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def independent_source_argument(document, ordinal, tool, option):
    source = document['jobs']['release_grade_recorded_path']['steps'][ordinal - 1]['run']
    invocations = [shlex.split(line) for line in source.replace('\\\n', ' ').splitlines()
                   if line.strip().startswith('python ') and ('/' + tool + '"') in line]
    assert len(invocations) == 1
    argv = invocations[0]
    assert argv.count(option) == 1
    value = argv[argv.index(option) + 1]
    return value.replace('${PACK_DIR}', 'PULSE_safe_pack_v0').replace('${GITHUB_WORKSPACE}/', '')


SOURCE_LEDGER_OUTPUTS = [
    ('quality-ledger-pre-authority', 13, 'render_quality_ledger.py', '--out', '#pre-authority-insertion'),
    ('final-status-summary', 14, 'status_to_summary.py', '--out_json', ''),
    ('release-decision', 15, 'materialize_release_decision.py', '--out', ''),
    ('release-decision-ledger-section', 16, 'render_release_decision_ledger_section.py', '--out', ''),
    ('release-authority-manifest', 17, 'build_release_authority_manifest_v0.py', '--out', ''),
    ('quality-ledger-final', 18, 'insert_release_authority_manifest_ledger_section.py', '--report', ''),
    ('release-decision-report', 19, 'insert_release_decision_ledger_section.py', '--out', ''),
]


@pytest.mark.parametrize('role,ordinal,tool,option,suffix', SOURCE_LEDGER_OUTPUTS)
def test_source_mapping_outputs_come_from_actual_workflow(source_fixture, role, ordinal, tool, option, suffix):
    states = {row['state_id']: row for row in source_fixture.plan['state_templates']}
    row = states['state:step5c:' + role]
    assert row['path_or_uri'] == independent_source_argument(mapping_source_document(), ordinal, tool, option) + suffix
    assert row['producer_occurrence_id'] == f'execution:step5c:step:release_grade_recorded_path:{ordinal:03}'
    assert row['required'] is True and row['content_requirement'] == 'exact_digest'


@pytest.mark.parametrize('role,variable', [('release-grade-junit', 'PULSE_JUNIT'), ('release-grade-sarif', 'PULSE_SARIF')])
def test_source_mapping_export_paths_use_actual_environment_assignment(source_fixture, role, variable):
    raw = mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][22]['run']
    value = re.findall(r'^export ' + variable + r'="([^"]+)"$', raw, re.M)
    assert len(value) == 1
    state = next(s for s in source_fixture.plan['state_templates'] if s['state_id'] == 'state:step5c:' + role)
    assert state['path_or_uri'] == value[0].replace('${PACK_DIR}', 'PULSE_safe_pack_v0')


def test_source_mapping_advisory_and_pre_attestation_locators_follow_source(source_fixture):
    document = mapping_source_document()
    source = document['jobs']['release_grade_recorded_path']['steps'][24]['run']
    directory = re.findall(r'^BUNDLE_DIR="([^"]+)"$', source, re.M)
    assert len(directory) == 1
    artifact = document['jobs']['pulse']['steps'][36]['with']['name']
    states = {s['state_id']: s for s in source_fixture.plan['state_templates']}
    assert states['state:step5c:advisory-reference-bundle']['path_or_uri'] == directory[0] + '/'
    assert states['state:step5c:pre-attestation-pulse-artifacts']['path_or_uri'] == ('artifact://' + artifact.replace('${{ github.run_id }}', '{workflow_run_id}').replace('${{ github.run_attempt }}', '1'))


@pytest.mark.parametrize('ordinal,inputs,outputs', [
    (13, ['final-status'], ['quality-ledger-pre-authority']),
    (14, ['final-status'], ['final-status-summary']),
    (15, ['final-status', 'gate-policy'], ['release-decision']),
    (16, ['release-decision'], ['release-decision-ledger-section']),
    (17, ['final-status', 'gate-policy', 'gate-registry'], ['release-authority-manifest']),
    (18, ['quality-ledger-pre-authority', 'release-authority-manifest'], ['quality-ledger-final']),
    (19, ['quality-ledger-final', 'release-decision-ledger-section'], ['release-decision-report']),
    (20, ['final-status', 'quality-ledger-final'], []),
])
def test_source_mapping_closed_step_equations_and_reverse_edges(source_fixture, ordinal, inputs, outputs):
    plan = source_fixture.plan
    job = next(j for j in plan['jobs'] if j['source_job_id'] == 'release_grade_recorded_path')
    step = job['steps'][ordinal - 1]
    state_ids = lambda names: sorted('state:step5c:' + name for name in names)
    assert step['input_state_ids'] == state_ids(inputs)
    assert step['output_state_ids'] == state_ids(outputs)
    reverse = sorted(s['state_id'] for s in plan['state_templates'] if step['occurrence_id'] in s['required_consumer_occurrence_ids'])
    assert reverse == state_ids(inputs)
    # Source validation is independent of the equality between two plans.
    PLAN_CHECKER._verify_source_ledger_equations(plan, mapping_source_document())


@pytest.mark.parametrize('mutation', ['section_path', 'summary_to_composer', 'composed_to_parity', 'prior_state_alias', 'producer'])
def test_source_mapping_same_wrong_answer_on_both_sides_is_rejected(source_fixture, mutation):
    plan = copy.deepcopy(source_fixture.plan)
    states = {s['state_id'].removeprefix('state:step5c:'): s for s in plan['state_templates']}
    job = next(j for j in plan['jobs'] if j['source_job_id'] == 'release_grade_recorded_path')
    if mutation == 'section_path':
        states['release-decision-ledger-section']['path_or_uri'] = 'PULSE_safe_pack_v0/artifacts/release_decision_ledger_section_v0.html'
    elif mutation in ('summary_to_composer', 'composed_to_parity'):
        ordinal, role = (19, 'final-status-summary') if mutation == 'summary_to_composer' else (20, 'release-decision-report')
        target = job['steps'][ordinal - 1]
        target['input_state_ids'].append('state:step5c:' + role)
        target['input_state_ids'].sort()
        states[role]['required_consumer_occurrence_ids'].append(target['occurrence_id'])
        states[role]['required_consumer_occurrence_ids'].sort()
    elif mutation == 'prior_state_alias':
        states['quality-ledger-pre-authority']['path_or_uri'] = states['quality-ledger-final']['path_or_uri']
    else:
        states['quality-ledger-final']['producer_occurrence_id'] = job['steps'][12]['occurrence_id']
    # Simulate a common-mode semantic defect after both plan reconstructions.
    builder_answer, checker_answer = canonical(plan), canonical(copy.deepcopy(plan))
    assert builder_answer == checker_answer and digest(builder_answer) == digest(checker_answer)
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(plan)
    with pytest.raises(PLAN_CHECKER.PlanError, match='source_mapping_'):
        PLAN_CHECKER._verify_source_ledger_equations(json.loads(builder_answer), mapping_source_document())


@pytest.mark.parametrize('mutation', ['section_path', 'consumer'])
def test_real_plan_checker_rejects_rehashed_source_mapping_error(source_fixture, tmp_path, mutation):
    f = source_fixture
    plan = copy.deepcopy(f.plan)
    states = {s['state_id']: s for s in plan['state_templates']}
    if mutation == 'section_path':
        states['state:step5c:release-decision-ledger-section']['path_or_uri'] = 'PULSE_safe_pack_v0/artifacts/wrong.html'
    else:
        role = states['state:step5c:final-status-summary']
        role['required_consumer_occurrence_ids'].append('execution:step5c:step:release_grade_recorded_path:019')
        role['required_consumer_occurrence_ids'].sort()
    raw = canonical(plan); target = tmp_path / 'source-mapping-mutant.json'; target.write_bytes(raw)
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(plan)
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', target,
        '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(raw), '--expected-record-status', 'example'])
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout)
    assert diagnostic['ok'] is False and diagnostic['error_code'].startswith('source_mapping_')


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', ['duplicate_command', 'duplicate_out', 'wrong_tool_path', 'shell_output', 'traversal_output', 'unknown_output', 'inplace_changed', 'wrong_report_consumer', 'duplicate_export', 'ambiguous_bundle'])
def test_source_mapping_rejects_unsupported_or_ambiguous_forms(side, mutation):
    doc = mapping_source_document()
    steps = doc['jobs']['release_grade_recorded_path']['steps']
    if mutation == 'duplicate_command': steps[15]['run'] += '\n' + steps[15]['run']
    elif mutation == 'duplicate_out': steps[15]['run'] += '\n'  # append to the invocation, not a new command
    elif mutation == 'wrong_tool_path': steps[15]['run'] = steps[15]['run'].replace('${PACK_DIR}/tools/', '${PACK_DIR}/other/')
    elif mutation in ('shell_output', 'traversal_output', 'unknown_output'):
        value = {'shell_output': '$(touch /tmp/not-executed)', 'traversal_output': '${PACK_DIR}/../outside.html', 'unknown_output': '${UNREVIEWED_ROOT}/section.html'}[mutation]
        steps[15]['run'] = steps[15]['run'].replace('${PACK_DIR}/artifacts/release_decision_v0_ledger_section.html', value)
    elif mutation == 'inplace_changed': steps[17]['run'] = steps[17]['run'].rstrip() + ' --out "${PACK_DIR}/artifacts/new.html"\n'
    elif mutation == 'wrong_report_consumer': steps[19]['run'] = steps[19]['run'].replace('/artifacts/report_card.html', '/artifacts/report_card.with_release_decision.html')
    elif mutation == 'duplicate_export': steps[22]['run'] += '\nexport PULSE_JUNIT="${PACK_DIR}/artifacts/reports/other.xml"\n'
    elif mutation == 'ambiguous_bundle': steps[24]['run'] += '\nBUNDLE_DIR="${RUNNER_TEMP}/other"\n'
    if mutation == 'duplicate_out':
        steps[15]['run'] = steps[15]['run'].rstrip() + ' --out "${PACK_DIR}/artifacts/second.html"\n'
    tool = BUILDER if side == 'builder' else PLAN_CHECKER
    function = tool._ledger_source_projection if side == 'builder' else tool._source_ledger_expectations
    with pytest.raises(tool.PlanError, match='source_mapping_'):
        function(doc)


@pytest.mark.parametrize('path', [
    'PULSE_safe_pack_v0/tools/insert_release_authority_manifest_ledger_section.py',
    'PULSE_safe_pack_v0/tools/insert_release_decision_ledger_section.py',
    'PULSE_safe_pack_v0/tools/check_quality_ledger_status_parity.py',
])
def test_source_mapping_called_semantics_are_exact_prepared_sources(source_fixture, tmp_path, path):
    f = source_fixture
    source = (f.root / path).read_bytes()
    row = next(s for s in f.plan['source_inventory'] if s['path'] == path)
    assert row['sha256'] == digest(source) and row['size_bytes'] == len(source)
    assert row['git_blob_sha1'] == hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
    for module in (BUILDER, PLAN_CHECKER):
        assert sum(p == path for _, p in module.SOURCE_ROLES) == 1
    prepared = prepared_fixture_members(f)
    assert prepared['sources/' + path] == source


def test_source_mapping_builder_and_checker_extractors_are_distinct():
    first = inspect.getsource(BUILDER._ledger_source_projection)
    second = inspect.getsource(PLAN_CHECKER._source_ledger_expectations)
    assert ast.dump(ast.parse(textwrap.dedent(first)), include_attributes=False) != ast.dump(ast.parse(textwrap.dedent(second)), include_attributes=False)
    checker_source = (ROOT / 'tools' / (TOOL_NAMES[1] + '.py')).read_text()
    tree = ast.parse(checker_source)
    imports = [name.name for n in ast.walk(tree) if isinstance(n, ast.Import) for name in n.names]
    imports += [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any('build_pulsemech_compute_whole_runtime' in name for name in imports)
    check = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_plan')
    function_calls = [n.func.id for n in ast.walk(check) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert '_verify_source_ledger_equations' in function_calls


def test_source_mapping_keeps_old_evidence_stop_and_inactive_r2_root(source_fixture):
    packet = runtime_projection_example(source_fixture)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, packet, {})
    assert len(source_fixture.plan['state_templates']) == 62
    assert 'evidence_profile' not in source_fixture.plan
    assert len(EVIDENCE_SCHEMA['oneOf']) == 4



@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', ['extra_flag', 'missing_flag', 'noncanonical_root'])
def test_source_mapping_rejects_changed_cli_contract(side, mutation):
    doc = mapping_source_document()
    target = doc['jobs']['release_grade_recorded_path']['steps'][18]
    if mutation == 'extra_flag': target['run'] = target['run'].rstrip() + ' --unexpected "anything"\n'
    elif mutation == 'missing_flag': target['run'] = target['run'].replace('  --section "${PACK_DIR}/artifacts/release_decision_v0_ledger_section.html" \\\n', '')
    else: target['run'] = target['run'].replace('${PACK_DIR}/artifacts/report_card.with_release_decision.html', 'prefix${PACK_DIR}/artifacts/other.html')
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    func = module._ledger_source_projection if side == 'builder' else module._source_ledger_expectations
    with pytest.raises(module.PlanError, match='source_mapping_'):
        func(doc)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', [
    'PULSE_safe_pack_v0/tools/insert_release_authority_manifest_ledger_section.py',
    'PULSE_safe_pack_v0/tools/insert_release_decision_ledger_section.py',
    'PULSE_safe_pack_v0/tools/check_quality_ledger_status_parity.py',
])
def test_source_mapping_rejects_semantic_source_drift_even_with_recomputed_blob(source_fixture, monkeypatch, side, path):
    from dataclasses import replace
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    original = module._read_git_object
    def changed(*args, **kwargs):
        obj = original(*args, **kwargs)
        if kwargs.get('path') == path:
            data = obj.data + b'\n# changed semantics profile test\n'
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            return replace(obj, data=data, blob_sha1=blob)
        return obj
    monkeypatch.setattr(module, '_read_git_object', changed)
    with pytest.raises(module.PlanError, match='reviewed_source_profile_mismatch'):
        module._load_sources(source_fixture.root, source_fixture.sha)


@pytest.mark.parametrize('mutation', ['path', 'edge'])
def test_actual_both_state_constructors_can_agree_wrongly_but_source_check_blocks(source_fixture, mutation):
    answers = []
    source = mapping_source_document()
    for module in (BUILDER, PLAN_CHECKER):
        jobs, steps, _ = module._build_jobs(copy.deepcopy(source))
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, copy.deepcopy(source),
                                      module._load_sources(source_fixture.root, source_fixture.sha))
        if mutation == 'path':
            next(s for s in states if s['state_id'] == 'state:step5c:release-decision-ledger-section')['path_or_uri'] = 'PULSE_safe_pack_v0/artifacts/common-wrong.html'
        else:
            role = 'state:step5c:final-status-summary'
            target = steps[('release_grade_recorded_path', 19)]
            target['input_state_ids'] = sorted(target['input_state_ids'] + [role])
            state = next(s for s in states if s['state_id'] == role)
            state['required_consumer_occurrence_ids'] = sorted(state['required_consumer_occurrence_ids'] + [target['occurrence_id']])
        plan = copy.deepcopy(source_fixture.plan)
        plan['jobs'], plan['state_templates'] = jobs, states
        answers.append(canonical(plan))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='source_mapping_'):
        PLAN_CHECKER._verify_source_ledger_equations(json.loads(answers[0]), source)


# ---------------------------------------------------------------------------
# Recorded-evidence/status source family. Expectations use reviewed source
# defaults and CLI arguments; these tests do not claim observed read receipts.
# The original release tools are never changed or executed as a release run.
# ---------------------------------------------------------------------------
RECORDED_SOURCE_TOOLS = (
    'PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py',
    'PULSE_safe_pack_v0/tools/build_release_evidence_input_manifest_v0.py',
    'PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py',
    'PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py',
    'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py',
    'PULSE_safe_pack_v0/tools/check_gates.py',
    'tools/policy_to_require_args.py',
    'tools/validate_status_schema.py',
    'ci/check_release_no_stub_status.py',
)
RECORDED_REVIEW_ROLES = frozenset({
    'pre-materialization-status', 'recorded-release-candidate-envelopes',
    'recorded-candidate-index', 'release-evidence-input-manifest',
    'recorded-release-evidence-verifier', 'materialized-release-required-gate-set',
    'final-status', 'gate-policy', 'gate-registry',
})


@pytest.fixture(scope='module')
def recorded_source_objects(source_fixture):
    return BUILDER._load_sources(source_fixture.root, source_fixture.sha)


def recorded_source_module(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    function = module._recorded_source_projection if side == 'builder' else module._source_recorded_expectations
    return module, function


def reviewed_literal_default(path, flag):
    # Read the called tool's argparse binding and literal declaration, not the
    # plan builder, checker, generated plan or profile-obligation table.
    tree = ast.parse((ROOT / path).read_bytes())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    bindings = [n for n in ast.walk(main) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == 'add_argument'
                and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == flag]
    assert len(bindings) == 1
    default = next(kw.value for kw in bindings[0].keywords if kw.arg == 'default')
    assert isinstance(default, ast.Name)
    assignments = [n.value for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == default.id for t in n.targets)]
    assert len(assignments) == 1
    value = ast.literal_eval(assignments[0])
    assert isinstance(value, str)
    return value


@pytest.mark.parametrize('role,path,flag,suffix', [
    ('pre-materialization-status', RECORDED_SOURCE_TOOLS[0], '--status', '#pre-release-required-materialization'),
    ('recorded-release-candidate-envelopes', RECORDED_SOURCE_TOOLS[0], '--out-dir', '/'),
    ('recorded-candidate-index', RECORDED_SOURCE_TOOLS[0], '--index', ''),
    ('release-evidence-input-manifest', RECORDED_SOURCE_TOOLS[1], '--out', ''),
    ('final-status', RECORDED_SOURCE_TOOLS[0], '--status', ''),
])
def test_recorded_mapping_locators_follow_called_tool_defaults(source_fixture, role, path, flag, suffix):
    state = next(s for s in source_fixture.plan['state_templates'] if s['state_id'] == 'state:step5c:' + role)
    assert state['path_or_uri'] == reviewed_literal_default(path, flag) + suffix
    assert state['required'] is True and state['content_requirement'] == 'exact_digest'


def test_recorded_mapping_verifier_and_logical_projection_are_distinct(source_fixture):
    states = {s['state_id'].removeprefix('state:step5c:'): s for s in source_fixture.plan['state_templates']}
    assert states['recorded-release-evidence-verifier']['path_or_uri'] == independent_source_argument(
        mapping_source_document(), 8, 'check_recorded_release_evidence_v0.py', '--out-json')
    projection = states['materialized-release-required-gate-set']
    assert projection['path_or_uri'] == ('projection://' + states['final-status']['path_or_uri']
                                        + '#policy-selected-release_required-gate-values')
    assert projection['role'] == 'policy_selected_release_required_status_gate_values'
    assert projection['required_consumer_occurrence_ids'] == []
    assert not any(projection['state_id'] in s['input_state_ids'] for j in source_fixture.plan['jobs'] for s in j['steps'])
    assert projection['path_or_uri'] != 'status://gates/release_required'
    # No original runtime-argv receipt is manufactured by this mapping repair.
    arguments = states['effective-required-argument-list']
    assert arguments['producer_occurrence_id'] is None
    assert arguments['required_consumer_occurrence_ids'] == []
    assert arguments['role'] == 'source_derived_required_arguments_runtime_receipt_unavailable'
    assert arguments['path_or_uri'] != projection['path_or_uri']


@pytest.mark.parametrize('ordinal,inputs,outputs', [
    (6, ['pre-materialization-status', 'gate-policy', 'gate-registry'],
     ['recorded-candidate-index', 'recorded-release-candidate-envelopes']),
    (7, ['recorded-candidate-index', 'recorded-release-candidate-envelopes', 'pre-materialization-status', 'gate-policy', 'gate-registry'],
     ['release-evidence-input-manifest']),
    (8, ['release-evidence-input-manifest', 'recorded-release-candidate-envelopes', 'pre-materialization-status', 'gate-policy', 'gate-registry'],
     ['recorded-release-evidence-verifier']),
    (9, ['pre-materialization-status', 'release-evidence-input-manifest', 'recorded-release-evidence-verifier',
         'recorded-release-candidate-envelopes', 'gate-policy', 'gate-registry'],
     ['final-status', 'materialized-release-required-gate-set']),
    (10, ['final-status'], []), (11, ['final-status'], []), (12, ['final-status', 'gate-policy'], []),
])
def test_recorded_mapping_selected_family_equations(source_fixture, recorded_source_objects, ordinal, inputs, outputs):
    plan = source_fixture.plan
    step = next(j for j in plan['jobs'] if j['source_job_id'] == 'release_grade_recorded_path')['steps'][ordinal - 1]
    selected = {'state:step5c:' + role for role in RECORDED_REVIEW_ROLES}
    ids = lambda roles: {'state:step5c:' + role for role in roles}
    assert set(step['input_state_ids']) & selected == ids(inputs)
    assert set(step['output_state_ids']) & selected == ids(outputs)
    reverse = {s['state_id'] for s in plan['state_templates'] if step['occurrence_id'] in s['required_consumer_occurrence_ids']}
    assert reverse & selected == ids(inputs)
    PLAN_CHECKER._verify_source_recorded_equations(plan, mapping_source_document(), recorded_source_objects)


def test_recorded_mapping_manifest_checks_pre_status_bytes_in_source():
    source = ast.parse((ROOT / RECORDED_SOURCE_TOOLS[1]).read_bytes())
    functions = {n.name: n for n in source.body if isinstance(n, ast.FunctionDef)}
    check = functions['_validate_source_bindings']
    dictionaries = [n for n in ast.walk(check) if isinstance(n, ast.Dict)]
    assert any(any(isinstance(k, ast.Constant) and k.value == 'candidate_status'
                   and isinstance(v, ast.Name) and v.id == 'STATUS_PATH' for k, v in zip(d.keys, d.values)) for d in dictionaries)
    calls = lambda node: {n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert '_verify_digest_ref' in calls(check)
    assert '_sha256' in calls(functions['_verify_digest_ref'])
    assert any('_validate_source_bindings' in calls(f) for name, f in functions.items() if name != '_validate_source_bindings')


def test_recorded_mapping_gate_projection_matches_actual_materializer_source():
    source = ast.parse((ROOT / RECORDED_SOURCE_TOOLS[3]).read_bytes())
    assignments = [n for n in ast.walk(source) if isinstance(n, ast.Assign)]
    assert any(isinstance(n.value, ast.Constant) and n.value.value is True
               and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == 'gates'
                       and isinstance(t.slice, ast.Name) and t.slice.id == 'gate_id' for t in n.targets) for n in assignments)
    assert any(isinstance(n.value, ast.Name) and n.value.id == 'gates'
               and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == 'status'
                       and isinstance(t.slice, ast.Constant) and t.slice.value == 'gates' for t in n.targets) for n in assignments)
    assert 'status://gates/release_required' not in (ROOT / RECORDED_SOURCE_TOOLS[3]).read_text()


@pytest.mark.parametrize('role', ['pre-materialization-status', 'recorded-release-candidate-envelopes'])
def test_recorded_mapping_new_roles_remain_strict_and_unobserved(source_fixture, role):
    plan = source_fixture.plan
    states = {s['state_id']: s for s in plan['state_templates']}
    assert len(states) == 62
    state = states['state:step5c:' + role]
    assert state['required'] is True and state['content_requirement'] == 'exact_digest'
    assert state['state_id'] in R2_CONTRACT_ROLES
    packet = runtime_projection_example(source_fixture)
    observation = next(s for s in packet['state_observations'] if s['state_id'] == state['state_id'])
    assert observation['content_status'] == 'unavailable'
    assert observation['sha256'] is None and observation['size_bytes'] is None
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(plan, packet, {})
    assert 'evidence_profile' not in plan and len(EVIDENCE_SCHEMA['oneOf']) == 4


def test_recorded_mapping_restore_does_not_replace_content_origin(source_fixture):
    states = {s['state_id']: s for s in source_fixture.plan['state_templates']}
    before = states['state:step5c:pre-materialization-status']
    after = states['state:step5c:final-status']
    assert before['producer_occurrence_id'] == 'execution:step5c:step:pulse:013'
    assert after['producer_occurrence_id'] == 'execution:step5c:step:release_grade_recorded_path:009'
    assert before['path_or_uri'].split('#')[0] == after['path_or_uri']
    assert before['path_or_uri'] != after['path_or_uri']
    assert 'execution:step5c:step:release_grade_recorded_path:004' in before['required_consumer_occurrence_ids']


def corrupt_recorded_mapping(plan, mutation):
    states = {s['state_id'].removeprefix('state:step5c:'): s for s in plan['state_templates']}
    job = next(j for j in plan['jobs'] if j['source_job_id'] == 'release_grade_recorded_path')
    def edge(ordinal, role, *, remove=False):
        step = job['steps'][ordinal - 1]
        values = step['input_state_ids']
        reverse = states[role]['required_consumer_occurrence_ids']
        state_id = 'state:step5c:' + role
        if remove:
            values.remove(state_id); reverse.remove(step['occurrence_id'])
        else:
            values.append(state_id); reverse.append(step['occurrence_id'])
        values.sort(); reverse.sort()
    if mutation == 'index_path': states['recorded-candidate-index']['path_or_uri'] += '.wrong'
    elif mutation == 'manifest_path': states['release-evidence-input-manifest']['path_or_uri'] += '.wrong'
    elif mutation == 'pre_state_alias': states['pre-materialization-status']['path_or_uri'] = states['final-status']['path_or_uri']
    elif mutation == 'envelopes_alias': states['recorded-release-candidate-envelopes']['path_or_uri'] = states['recorded-candidate-index']['path_or_uri']
    elif mutation == 'wrong_producer': states['pre-materialization-status']['producer_occurrence_id'] = job['steps'][3]['occurrence_id']
    elif mutation == 'index_to_verifier': edge(8, 'recorded-candidate-index')
    elif mutation == 'registry_to_gate_checker': edge(12, 'gate-registry')
    elif mutation == 'projection_to_checker': edge(12, 'materialized-release-required-gate-set')
    elif mutation == 'erase_manifest_pre_status': edge(7, 'pre-materialization-status', remove=True)
    elif mutation == 'unjustified_pre_state_consumer': edge(25, 'pre-materialization-status')
    elif mutation == 'extra_envelope_writer':
        step = job['steps'][4]
        step['output_state_ids'] = sorted(step['output_state_ids'] + ['state:step5c:recorded-release-candidate-envelopes'])
    else: raise AssertionError(mutation)
    return plan


RECORDED_MAPPING_MUTATIONS = [
    'index_path', 'manifest_path', 'pre_state_alias', 'envelopes_alias', 'wrong_producer',
    'index_to_verifier', 'registry_to_gate_checker', 'projection_to_checker',
    'erase_manifest_pre_status', 'unjustified_pre_state_consumer', 'extra_envelope_writer',
]


@pytest.mark.parametrize('mutation', RECORDED_MAPPING_MUTATIONS)
def test_recorded_mapping_common_wrong_answer_is_rejected(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_recorded_mapping(copy.deepcopy(source_fixture.plan), mutation)
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(bad)
    one, two = canonical(bad), canonical(copy.deepcopy(bad))
    assert one == two and digest(one) == digest(two)
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_mapping_'):
        PLAN_CHECKER._verify_source_recorded_equations(json.loads(one), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['index_path', 'index_to_verifier', 'erase_manifest_pre_status', 'pre_state_alias'])
def test_recorded_mapping_real_checker_rejects_rehashed_false_plan(source_fixture, tmp_path, mutation):
    f = source_fixture
    bad = corrupt_recorded_mapping(copy.deepcopy(f.plan), mutation)
    raw = canonical(bad)
    path = tmp_path / 'source-mapping-error.json'; path.write_bytes(raw)
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', path,
                 '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(raw), '--expected-record-status', 'example'])
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout or result.stderr)
    assert diagnostic['ok'] is False
    assert diagnostic['error_code'].startswith('recorded_mapping_')


@pytest.mark.parametrize('mutation', ['index_path', 'index_to_verifier'])
def test_recorded_mapping_actual_two_constructors_cannot_hide_shared_defect(source_fixture, recorded_source_objects, mutation):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        jobs, steps, _ = module._build_jobs(mapping_source_document())
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, mapping_source_document(), recorded_source_objects)
        result = copy.deepcopy(source_fixture.plan)
        result['jobs'], result['state_templates'] = jobs, states
        answers.append(canonical(corrupt_recorded_mapping(result, mutation)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_mapping_'):
        PLAN_CHECKER._verify_source_recorded_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('path', RECORDED_SOURCE_TOOLS)
def test_recorded_mapping_pins_and_preserves_called_source(source_fixture, recorded_source_objects, path):
    data = (ROOT / path).read_bytes()
    expected_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    for module in (BUILDER, PLAN_CHECKER):
        assert module._RECORDED_SEMANTIC_PINS[path] == expected_blob
        assert sum(relative == path for _, relative in module.SOURCE_ROLES) == 1
    entry = next(row for row in source_fixture.plan['source_inventory'] if row['path'] == path)
    assert entry['sha256'] == digest(data)
    assert prepared_fixture_members(source_fixture)['sources/' + path] == data


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', RECORDED_SOURCE_TOOLS)
def test_recorded_mapping_semantic_change_rehashed_object_is_rejected(source_fixture, monkeypatch, side, path):
    module, _ = recorded_source_module(side)
    original = module._read_git_object
    def changed(*args, **kwargs):
        obj = original(*args, **kwargs)
        if kwargs.get('path') == path:
            data = obj.data + b'\n# altered reviewed semantic source in a negative example\n'
            obj = replace(obj, data=data, blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
        return obj
    monkeypatch.setattr(module, '_read_git_object', changed)
    with pytest.raises(module.PlanError, match='reviewed_source_profile_mismatch'):
        module._load_sources(source_fixture.root, source_fixture.sha)


RECORDED_SOURCE_CHANGES = [
    (6, '--repo-root "${GITHUB_WORKSPACE}"', '--repo-root "${GITHUB_WORKSPACE}" --unknown "value"'),
    (6, '--repo-root "${GITHUB_WORKSPACE}"', '--repo-root "${GITHUB_WORKSPACE}" --repo-root "${GITHUB_WORKSPACE}"'),
    (6, '--repo-root "${GITHUB_WORKSPACE}"', '--repo-root "elsewhere"'),
    (6, 'build_recorded_release_candidates_v0.py', 'unreviewed_candidate.py'),
    (7, '--repo-root "${GITHUB_WORKSPACE}"', ''),
    (8, '--manifest "${PACK_DIR}/artifacts/release_evidence_input_manifest_v0.json"', '--manifest "${PACK_DIR}/artifacts/other.json"'),
    (8, '--out-json "${PACK_DIR}/artifacts/recorded_release_evidence_verifier_v0.json"', '--out-json "${PACK_DIR}/artifacts/other.json"'),
    (9, '--status "${PACK_DIR}/artifacts/status.json"', '--status "${PACK_DIR}/artifacts/status_baseline.json"'),
    (9, '--out "${PACK_DIR}/artifacts/status.json"', '--out "${PACK_DIR}/artifacts/other.json"'),
    (9, '--policy "${GITHUB_WORKSPACE}/pulse_gate_policy_v0.yml"', '--policy "other.yml"'),
    (10, '--status "${PACK_DIR}/artifacts/status.json"', '--status "${PACK_DIR}/artifacts/other.json"'),
    (11, '--status "${PACK_DIR}/artifacts/status.json"', '--status "${PACK_DIR}/artifacts/status_baseline.json"'),
    (12, '--set required', '--set release_required'),
    (12, '--format newline', '--format space'),
    (12, '--require "${EFFECTIVE_GATES[@]}"', '--require "${OTHER_GATES[@]}"'),
]


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('ordinal,old,new', RECORDED_SOURCE_CHANGES)
def test_recorded_mapping_rejects_unsupported_workflow_source(recorded_source_objects, side, ordinal, old, new):
    document = mapping_source_document()
    target = document['jobs']['release_grade_recorded_path']['steps'][ordinal - 1]
    assert old in target['run'], (ordinal, old)
    target['run'] = target['run'].replace(old, new)
    module, project = recorded_source_module(side)
    with pytest.raises(module.PlanError, match='(?:recorded|source)_mapping_'):
        project(document, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_recorded_mapping_rejects_missing_source_even_when_other_side_agrees(recorded_source_objects, side):
    module, project = recorded_source_module(side)
    sources = dict(recorded_source_objects)
    del sources[RECORDED_SOURCE_TOOLS[1]]
    with pytest.raises(module.PlanError, match='recorded_mapping_source_missing'):
        project(mapping_source_document(), sources)


def test_recorded_mapping_independent_predicate_precedes_reconstruction():
    first = ast.parse(textwrap.dedent(inspect.getsource(BUILDER._recorded_source_projection)))
    second = ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER._source_recorded_expectations)))
    assert ast.dump(first, include_attributes=False) != ast.dump(second, include_attributes=False)
    body = ast.parse(inspect.getsource(PLAN_CHECKER.check_plan)).body[0]
    calls = [(n.lineno, n.func.id) for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    predicate = min(line for line, name in calls if name == '_verify_source_recorded_equations')
    equality_input = min(line for line, name in calls if name == '_reconstruct_expected_plan')
    assert predicate < equality_input
    module_tree = ast.parse((ROOT / 'tools' / (TOOL_NAMES[1] + '.py')).read_bytes())
    imported = [a.name for n in ast.walk(module_tree) if isinstance(n, ast.Import) for a in n.names]
    imported += [n.module or '' for n in ast.walk(module_tree) if isinstance(n, ast.ImportFrom)]
    assert not any('build_pulsemech_compute_whole_runtime' in name for name in imported)


# ---------------------------------------------------------------------------
# Package content/publication mapping. Example metadata remains unobserved.
# Expected publication selectors are read from the subject workflow, not from
# either generated state table or from an alleged package verifier verdict.
# ---------------------------------------------------------------------------
PACKAGE_MAPPING_TOOLS = (
    'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py',
    'PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py',
    'tools/check_release_grade_package_complete_v1.py',
)
PACKAGE_MAPPING_ROLES = (
    'complete-release-grade-reference-package', 'package-completeness-report',
    'package-verification-report', 'package-digest-inventory', 'package-run-metadata',
)
PACKAGE_S = 'assemble_release_grade_reference_package'
PACKAGE_V = 'verify_release_grade_reference_package'


def package_source_projection(side, source_fixture, workflow=None, sources=None):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    function = module._package_source_projection if side == 'builder' else module._source_package_expectations
    objects = BUILDER._load_sources(source_fixture.root, source_fixture.sha) if sources is None else sources
    return function(mapping_source_document() if workflow is None else workflow, objects)


def package_states(plan):
    return {s['state_id'].removeprefix('state:step5c:'): s for s in plan['state_templates']}


@pytest.mark.parametrize('role,job,number,old_producer', [
    ('complete-release-grade-reference-package', PACKAGE_S, 6, 5),
    ('package-completeness-report', PACKAGE_V, 6, 5),
    ('package-verification-report', PACKAGE_V, 8, 7),
])
def test_package_mapping_archive_identity_comes_from_publisher(source_fixture, role, job, number, old_producer):
    raw = mapping_source_document()['jobs'][job]['steps'][number - 1]
    name = raw['with']['name'].replace('${{ github.run_id }}', '{workflow_run_id}').replace('${{ github.run_attempt }}', '1')
    assert raw['uses'].startswith('actions/upload-artifact@')
    states = package_states(source_fixture.plan)
    assert states[role]['path_or_uri'] == 'artifact://' + name
    expected = f'execution:step5c:step:{job}:{number:03d}'
    assert states[role]['producer_occurrence_id'] == expected
    all_steps = [s for j in source_fixture.plan['jobs'] for s in j['steps']]
    assert {s['occurrence_id'] for s in all_steps if states[role]['state_id'] in s['output_state_ids']} == {expected}
    assert expected != f'execution:step5c:step:{job}:{old_producer:03d}'


@pytest.mark.parametrize('role,filename,writer', [
    ('package-digest-inventory', 'package_digest_inventory_v0.json', '_write_digest_inventory'),
    ('package-run-metadata', 'run_metadata_v0.json', '_write_run_metadata'),
])
def test_package_mapping_metadata_writers_and_readers_are_source_bound(source_fixture, role, filename, writer):
    state = package_states(source_fixture.plan)[role]
    assert state['path_or_uri'] == '${RUNNER_TEMP}/complete-release-grade-reference-package/' + filename
    assert state['producer_occurrence_id'] == f'execution:step5c:step:{PACKAGE_S}:005'
    expected = {f'execution:step5c:step:{PACKAGE_S}:006', f'execution:step5c:step:{PACKAGE_V}:005', f'execution:step5c:step:{PACKAGE_V}:007'}
    assert set(state['required_consumer_occurrence_ids']) == expected
    assert state['required'] is True and state['content_requirement'] == 'exact_digest'
    assert state['authority_bearing'] is False
    assembly_tree = ast.parse((ROOT / PACKAGE_MAPPING_TOOLS[0]).read_bytes())
    # Independently demonstrate the named writer invocation and exact filename.
    literals = {n.value for n in ast.walk(assembly_tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert filename in literals
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == writer for n in ast.walk(assembly_tree))
    for path in PACKAGE_MAPPING_TOOLS[1:]:
        tree = ast.parse((ROOT / path).read_bytes())
        declaration = next(n.value for n in tree.body if isinstance(n, ast.AnnAssign)
                           and isinstance(n.target, ast.Name) and n.target.id == 'REQUIRED_FILES')
        assert filename in ast.literal_eval(declaration)
    packet = runtime_projection_example(source_fixture)
    observed = next(row for row in packet['state_observations'] if row['state_id'] == state['state_id'])
    assert observed['content_status'] == 'unavailable'
    assert observed['sha256'] is None and observed['size_bytes'] is None


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_package_mapping_separates_local_outputs_from_archive_locators(source_fixture, side):
    facts = package_source_projection(side, source_fixture)
    assert facts['local_outputs'] == {
        'complete-release-grade-reference-package': '${RUNNER_TEMP}/complete-release-grade-reference-package',
        'package-completeness-report': '${RUNNER_TEMP}/release_grade_package_completeness_v1.json',
        'package-verification-report': '${RUNNER_TEMP}/release_grade_reference_package_verification_v0.json',
    }
    assert all(facts['locators'][r].startswith('artifact://') for r in PACKAGE_MAPPING_ROLES[:3])
    assert len(set(facts['locators'].values())) == 5
    assert set(facts['assembly_download_names']) == {
        'pulse-report', 'release-grade-recorded-path-${{ github.run_id }}-${{ github.run_attempt }}',
        'release-authority-audit-bundle', 'release-authority-artifact-binding-v0',
    }


@pytest.mark.parametrize('role', ['advisory-reference-bundle', 'artifact-binding-attestation'])
def test_package_mapping_does_not_invent_missing_s4_download(source_fixture, role):
    state = package_states(source_fixture.plan)[role]
    occurrence = f'execution:step5c:step:{PACKAGE_S}:004'
    assert occurrence not in state['required_consumer_occurrence_ids']
    step = next(s for j in source_fixture.plan['jobs'] for s in j['steps'] if s['occurrence_id'] == occurrence)
    assert state['state_id'] not in step['input_state_ids']
    assert state['required'] is True  # absence of a route is not scope removal


def corrupt_package_mapping(plan, role, mutation):
    state = package_states(plan)[role]
    all_steps = {s['occurrence_id']: s for j in plan['jobs'] for s in j['steps']}
    key = state['state_id']
    if mutation == 'locator':
        state['path_or_uri'] = 'artifact://same-wrong-answer-{workflow_run_id}-1'
    elif mutation == 'producer':
        for step in all_steps.values():
            step['output_state_ids'] = [r for r in step['output_state_ids'] if r != key]
        wrong = f'execution:step5c:step:{PACKAGE_S}:004'
        state['producer_occurrence_id'] = wrong
        all_steps[wrong]['output_state_ids'] = sorted(all_steps[wrong]['output_state_ids'] + [key])
    elif mutation == 'extra_writer':
        step = all_steps['execution:step5c:step:pulse:022']
        step['output_state_ids'] = sorted(step['output_state_ids'] + [key])
    elif mutation == 'consumer':
        wrong = 'execution:step5c:step:pulse:022'
        state['required_consumer_occurrence_ids'] = sorted(set(state['required_consumer_occurrence_ids']) | {wrong})
        all_steps[wrong]['input_state_ids'] = sorted(set(all_steps[wrong]['input_state_ids']) | {key})
    elif mutation == 'strength':
        state['content_requirement'] = 'metadata_only'
    elif mutation == 'omission':
        plan['state_templates'] = [s for s in plan['state_templates'] if s['state_id'] != key]
        for step in all_steps.values():
            for field in ('input_state_ids', 'output_state_ids'):
                step[field] = [r for r in step[field] if r != key]
    else:
        raise AssertionError(mutation)
    return plan


@pytest.mark.parametrize('role', PACKAGE_MAPPING_ROLES)
@pytest.mark.parametrize('mutation', ['locator', 'producer', 'extra_writer', 'consumer', 'strength', 'omission'])
def test_package_mapping_shared_false_answers_fail_source_predicate(source_fixture, recorded_source_objects, role, mutation):
    bad = corrupt_package_mapping(copy.deepcopy(source_fixture.plan), role, mutation)
    # A matching constructor's answer cannot serve as the semantic oracle.
    assert canonical(bad) == canonical(copy.deepcopy(bad))
    with pytest.raises(PLAN_CHECKER.PlanError, match='package_mapping_'):
        PLAN_CHECKER._verify_source_package_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('role', ['advisory-reference-bundle', 'artifact-binding-attestation'])
def test_package_mapping_false_download_edge_is_rejected(source_fixture, recorded_source_objects, role):
    plan = copy.deepcopy(source_fixture.plan)
    row = package_states(plan)[role]
    target = f'execution:step5c:step:{PACKAGE_S}:004'
    row['required_consumer_occurrence_ids'] = sorted(row['required_consumer_occurrence_ids'] + [target])
    step = next(s for j in plan['jobs'] for s in j['steps'] if s['occurrence_id'] == target)
    step['input_state_ids'] = sorted(step['input_state_ids'] + [row['state_id']])
    with pytest.raises(PLAN_CHECKER.PlanError, match='package_mapping_unacquired_input'):
        PLAN_CHECKER._verify_source_package_equations(plan, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('role,mutation', [
    ('complete-release-grade-reference-package', 'producer'),
    ('package-completeness-report', 'locator'),
    ('package-run-metadata', 'consumer'),
    ('package-digest-inventory', 'omission'),
])
def test_package_mapping_real_checker_rejects_rehashed_false_plan(source_fixture, tmp_path, role, mutation):
    f = source_fixture
    plan = corrupt_package_mapping(copy.deepcopy(f.plan), role, mutation)
    raw = canonical(plan)
    path = tmp_path / 'bad-package-plan.json'; path.write_bytes(raw)
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', path,
        '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(raw), '--expected-record-status', 'example'])
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout)
    assert diagnostic['ok'] is False and diagnostic['error_code'].startswith('package_mapping_')


@pytest.mark.parametrize('role', PACKAGE_MAPPING_ROLES[:3])
def test_package_mapping_actual_constructors_cannot_share_false_publisher(source_fixture, recorded_source_objects, role):
    answers = []
    workflow = mapping_source_document()
    for module in (BUILDER, PLAN_CHECKER):
        jobs, steps, operations = module._build_jobs(workflow)
        states = module._build_states(steps, tuple(s['case_id'] for s in source_fixture.plan['model_inference_templates']), workflow, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        answers.append(canonical(corrupt_package_mapping(plan, role, 'producer')))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='package_mapping_'):
        PLAN_CHECKER._verify_source_package_equations(json.loads(answers[0]), workflow, recorded_source_objects)


@pytest.mark.parametrize('path', PACKAGE_MAPPING_TOOLS)
def test_package_mapping_sources_are_in_exact_prepared_carrier(source_fixture, path):
    payload = (source_fixture.root / path).read_bytes()
    row = next(r for r in source_fixture.plan['source_inventory'] if r['path'] == path)
    assert row['sha256'] == digest(payload) and row['size_bytes'] == len(payload)
    assert prepared_fixture_members(source_fixture)['sources/' + path] == payload
    for module in (BUILDER, PLAN_CHECKER):
        assert sum(p == path for _, p in module.SOURCE_ROLES) == 1


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', PACKAGE_MAPPING_TOOLS)
def test_package_mapping_rehashed_semantic_source_drift_is_rejected(source_fixture, recorded_source_objects, side, path):
    sources = dict(recorded_source_objects)
    old = sources[path]; payload = old.data + b'\n# changed reviewed semantic source\n'
    sources[path] = replace(old, data=payload, blob_sha1=hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest())
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    with pytest.raises(module.PlanError, match='package_mapping_semantic_source_drift'):
        package_source_projection(side, source_fixture, sources=sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', PACKAGE_MAPPING_TOOLS)
def test_package_mapping_missing_source_is_rejected(source_fixture, recorded_source_objects, side, path):
    sources = dict(recorded_source_objects); del sources[path]
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    with pytest.raises(module.PlanError, match='package_mapping_source_missing'):
        package_source_projection(side, source_fixture, sources=sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', [
    'duplicate_command', 'extra_flag', 'missing_flag', 'wrong_tool', 'wrong_source_run',
    'duplicate_assignment', 'dynamic_directory', 'traversal_directory', 'wrong_package_dir',
    'wrong_publication_path', 'unbound_artifact_name', 'wrong_download_name', 'cross_run_download',
    'extra_advisory_download', 'receipt_download_substitution', 'report_alias', 'report_inside_package',
    'unpinned_upload', 'missing_output_guard', 'wrong_input_root', 'step_order',
])
def test_package_mapping_unsupported_source_forms_fail(source_fixture, recorded_source_objects, side, mutation):
    workflow = mapping_source_document()
    s = workflow['jobs'][PACKAGE_S]['steps']; v = workflow['jobs'][PACKAGE_V]['steps']
    if mutation == 'duplicate_command': s[4]['run'] += '\n' + s[4]['run']
    elif mutation == 'extra_flag': v[4]['run'] = v[4]['run'].rstrip() + ' --extra "x"\n'
    elif mutation == 'missing_flag': v[4]['run'] = v[4]['run'].replace('--output', '--other')
    elif mutation == 'wrong_tool': v[4]['run'] = v[4]['run'].replace('tools/check_', 'other/check_')
    elif mutation == 'wrong_source_run': s[4]['run'] = s[4]['run'].replace('--run-id "${GITHUB_RUN_ID}"', '--run-id "123"')
    elif mutation == 'duplicate_assignment': s[3]['run'] += '\nCOMPLETE_PACKAGE_DIR="${RUNNER_TEMP}/other"\n'
    elif mutation in ('dynamic_directory', 'traversal_directory'):
        value = '$(touch /tmp/must-not-execute)' if mutation == 'dynamic_directory' else '${RUNNER_TEMP}/../outside'
        s[3]['run'] = s[3]['run'].replace('COMPLETE_PACKAGE_DIR="${RUNNER_TEMP}/complete-release-grade-reference-package"', 'COMPLETE_PACKAGE_DIR="' + value + '"')
    elif mutation == 'wrong_package_dir': v[4]['run'] = v[4]['run'].replace('/complete-release-grade-reference-package', '/different')
    elif mutation == 'wrong_publication_path': v[5]['with']['path'] = '${{runner.temp}}/other.json'
    elif mutation == 'unbound_artifact_name': s[5]['with']['name'] = 'unbound-artifact'
    elif mutation == 'wrong_download_name': v[3]['run'] = v[3]['run'].replace('--name "complete-release-', '--name "wrong-release-')
    elif mutation == 'cross_run_download': v[3]['run'] = v[3]['run'].replace('gh run download "${GITHUB_RUN_ID}"', 'gh run download "123"')
    elif mutation == 'extra_advisory_download': s[3]['run'] += '\ngh run download "${GITHUB_RUN_ID}" --repo "${GITHUB_REPOSITORY}" --name "release-grade-reference-run-v0" --dir "${PULSE_REPORT_DIR}"\n'
    elif mutation == 'receipt_download_substitution': s[3]['run'] = s[3]['run'].replace('--name "release-authority-artifact-binding-v0"', '--name "attestation-receipt"')
    elif mutation == 'report_alias':
        v[3]['run'] = v[3]['run'].replace('release_grade_reference_package_verification_v0.json', 'release_grade_package_completeness_v1.json')
        v[7]['with']['path'] = '${{runner.temp}}/release_grade_package_completeness_v1.json'
    elif mutation == 'report_inside_package':
        v[4]['run'] = v[4]['run'].replace('/release_grade_package_completeness_v1.json', '/complete-release-grade-reference-package/report.json')
        v[5]['with']['path'] = '${{runner.temp}}/complete-release-grade-reference-package/report.json'
    elif mutation == 'unpinned_upload': s[5]['uses'] = 'actions/upload-artifact@main'
    elif mutation == 'missing_output_guard': v[5]['with']['if-no-files-found'] = 'warn'
    elif mutation == 'wrong_input_root': s[4]['run'] = s[4]['run'].replace('--recorded-path-dir "${RECORDED_PATH_DIR}"', '--recorded-path-dir "${PULSE_REPORT_DIR}"')
    elif mutation == 'step_order': v[4], v[5] = v[5], v[4]
    else: raise AssertionError(mutation)
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    with pytest.raises(module.PlanError, match='package_mapping_'):
        package_source_projection(side, source_fixture, workflow, recorded_source_objects)


def test_package_mapping_source_predicate_precedes_reconstruction():
    code = (ROOT / 'tools' / (TOOL_NAMES[1] + '.py')).read_text()
    tree = ast.parse(code)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_plan')
    calls = {n.func.id: n.lineno for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls['_verify_source_package_equations'] < calls['_reconstruct_expected_plan']
    imports = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names]
    assert not any('build_pulsemech_compute_whole_runtime' in name for name in imports)


def test_package_mapping_keeps_legacy_stop_and_inactive_r2_profile(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert 'evidence_profile' not in source_fixture.plan
    assert len(EVIDENCE_SCHEMA['oneOf']) == 4
    packet = runtime_projection_example(source_fixture)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, packet, {})
    assert packet['coverage']['coverage_status'] == 'partial'



# P37/R4 source-declared preservation is separate from runtime acceptance.
PREATTEST_LOCAL_ROLES = (
    'pre-materialization-status', 'status-baseline', 'required-gate-evidence',
    'self-contained-evidence-floor', 'llamaguard-raw-evidence',
    'llamaguard-evaluator-manifest', 'llamaguard-summary',
)
PREATTEST_RESTORED_ROLES = PREATTEST_LOCAL_ROLES[:4]
PREATTEST_MUTATIONS = (
    'missing_upload_status', 'missing_upload_baseline', 'missing_upload_evidence',
    'missing_upload_floor', 'missing_upload_raw', 'missing_upload_manifest', 'missing_upload_summary',
    'missing_restore_baseline', 'missing_restore_evidence', 'missing_restore_floor', 'missing_restore_archive',
    'final_status_upload', 'final_status_restore', 'external_restore', 'policy_upload',
    'publisher_as_origin', 'restorer_as_origin', 'extra_writer', 'wrong_archive_locator',
    'optional_baseline', 'metadata_archive', 'reverse_only', 'forward_only', 'extra_archive_reader',
    'reverse_orphan', 'missing_role',
)


def preattest_source_method(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    return module, (module._preattest_preservation_source_projection if side == 'builder'
                    else module._source_preattest_preservation_expectations)


@pytest.mark.parametrize('role', PREATTEST_LOCAL_ROLES)
def test_preattest_each_upload_input_is_bound_in_both_directions(source_fixture, role):
    rows, steps = provenance_rows(source_fixture.plan)
    step = steps[('pulse', 37)]; row = rows[role]
    assert row['path_or_uri'].split('#', 1)[0] in mapping_source_document()['jobs']['pulse']['steps'][36]['with']['path'].splitlines()
    assert row['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in row['required_consumer_occurrence_ids']


@pytest.mark.parametrize('role', PREATTEST_RESTORED_ROLES)
def test_preattest_each_restore_input_is_bound_in_both_directions(source_fixture, role):
    rows, steps = provenance_rows(source_fixture.plan)
    step = steps[('release_grade_recorded_path', 4)]; row = rows[role]
    body = mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][3]['run']
    assert 'copy_required_artifact "' + Path(row['path_or_uri'].split('#', 1)[0]).name + '"' in body
    assert row['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in row['required_consumer_occurrence_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_preattest_source_selectors_and_unmodeled_extent_remain_explicit(source_fixture, recorded_source_objects, side):
    _, method = preattest_source_method(side)
    doc = mapping_source_document(); facts = method(doc, recorded_source_objects)
    upload = doc['jobs']['pulse']['steps'][36]['with']
    body = doc['jobs']['release_grade_recorded_path']['steps'][3]['run']
    # Independent oracle: actual workflow selectors and copy invocations, not
    # the state constructor or an expected producer/consumer mapping table.
    assert facts['upload_paths'] == sorted(upload['path'].splitlines())
    copied = [shlex.split(line)[1] for line in body.splitlines() if line.startswith('copy_required_artifact "')]
    assert facts['restored_paths'] == sorted('PULSE_safe_pack_v0/artifacts/' + name for name in copied)
    extra = sorted('PULSE_safe_pack_v0/artifacts/' + name for name in
                   ('status_summary_baseline.md', 'status_summary_baseline.json', 'refusal_delta_summary.json'))
    assert facts['unmodeled_upload_paths'] == facts['unmodeled_restore_paths'] == extra
    assert (len(facts['upload_paths']), len(facts['restored_paths']), len(facts['locators'])) == (10, 7, 8)
    assert set(extra).isdisjoint(row['path_or_uri'] for row in source_fixture.plan['state_templates'])
    assert facts['download_directory'] == '${RUNNER_TEMP}/pulse-pre-attestation'
    assert facts['locators']['pre-attestation-pulse-artifacts'] == 'artifact://pulse-pre-attestation-{workflow_run_id}-1'


def test_preattest_source_projections_agree_without_builder_execution(source_fixture, recorded_source_objects):
    doc = mapping_source_document()
    built = BUILDER._preattest_preservation_source_projection(doc, recorded_source_objects)
    with patch.object(BUILDER, '_preattest_preservation_source_projection', side_effect=AssertionError('builder must not run')):
        checked = PLAN_CHECKER._source_preattest_preservation_expectations(doc, recorded_source_objects)
    assert canonical(built) == canonical(checked)
    # The independent source checker reaches the actual P23 input/output
    # arguments and R4 hash loop, rather than importing the builder's projection.
    source = inspect.getsource(PLAN_CHECKER._source_preattest_preservation_expectations)
    assert '_preattest_preservation_source_projection(' not in source
    assert 'summary["--in"]' in source and 'for artifact in ' in source


def corrupt_preattest_plan(original, mutation):
    plan = copy.deepcopy(original); rows, steps = provenance_rows(plan)
    publish, restore = ('pulse', 37), ('release_grade_recorded_path', 4)
    def edge(role, key, add):
        row, step = rows[role], steps[key]; sid, oid = row['state_id'], step['occurrence_id']
        if add:
            step['input_state_ids'] = sorted(set(step['input_state_ids']) | {sid})
            row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {oid})
        else:
            step['input_state_ids'] = [v for v in step['input_state_ids'] if v != sid]
            row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v != oid]
    names = {'status': 'pre-materialization-status', 'baseline': 'status-baseline', 'evidence': 'required-gate-evidence',
             'floor': 'self-contained-evidence-floor', 'raw': 'llamaguard-raw-evidence',
             'manifest': 'llamaguard-evaluator-manifest', 'summary': 'llamaguard-summary',
             'archive': 'pre-attestation-pulse-artifacts'}
    if mutation.startswith('missing_upload_'): edge(names[mutation.removeprefix('missing_upload_')], publish, False)
    elif mutation.startswith('missing_restore_'): edge(names[mutation.removeprefix('missing_restore_')], restore, False)
    elif mutation in ('final_status_upload', 'final_status_restore'):
        key = publish if mutation.endswith('upload') else restore
        edge('pre-materialization-status', key, False); edge('final-status', key, True)
    elif mutation == 'external_restore': edge('llamaguard-raw-evidence', restore, True)
    elif mutation == 'policy_upload': edge('gate-policy', publish, True)
    elif mutation in ('publisher_as_origin', 'restorer_as_origin'):
        role = 'self-contained-evidence-floor'; row = rows[role]
        for step in steps.values(): step['output_state_ids'] = [v for v in step['output_state_ids'] if v != row['state_id']]
        target = steps[publish if mutation.startswith('publisher') else restore]
        target['output_state_ids'] = sorted([*target['output_state_ids'], row['state_id']])
        row['producer_occurrence_id'] = target['occurrence_id']
    elif mutation == 'extra_writer': steps[('pulse', 36)]['output_state_ids'].append(rows['self-contained-evidence-floor']['state_id'])
    elif mutation == 'wrong_archive_locator': rows['pre-attestation-pulse-artifacts']['path_or_uri'] += '-other-run'
    elif mutation == 'optional_baseline': rows['status-baseline']['required'] = False
    elif mutation == 'metadata_archive': rows['pre-attestation-pulse-artifacts']['content_requirement'] = 'metadata_only'
    elif mutation == 'reverse_only': rows['status-baseline']['required_consumer_occurrence_ids'].remove(steps[restore]['occurrence_id'])
    elif mutation == 'forward_only': steps[publish]['input_state_ids'].remove(rows['self-contained-evidence-floor']['state_id'])
    elif mutation == 'extra_archive_reader': edge('pre-attestation-pulse-artifacts', ('pulse', 38), True)
    elif mutation == 'reverse_orphan': rows['final-status']['required_consumer_occurrence_ids'].append(steps[restore]['occurrence_id'])
    elif mutation == 'missing_role':
        sid = rows['status-baseline']['state_id']
        plan['state_templates'] = [v for v in plan['state_templates'] if v['state_id'] != sid]
        for step in steps.values():
            for field in ('input_state_ids', 'output_state_ids'): step[field] = [v for v in step[field] if v != sid]
    else: raise AssertionError(mutation)
    return plan


@pytest.mark.parametrize('mutation', PREATTEST_MUTATIONS)
def test_preattest_coordinated_forgery_is_rejected_against_source(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_preattest_plan(source_fixture.plan, mutation)
    with pytest.raises(PLAN_CHECKER.PlanError, match='preservation_mapping_'):
        PLAN_CHECKER._verify_source_preattest_preservation_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_upload_floor', 'final_status_restore', 'publisher_as_origin'])
def test_preattest_equal_constructor_errors_do_not_replace_source_checks(source_fixture, recorded_source_objects, mutation):
    results = []
    for module in (BUILDER, PLAN_CHECKER):
        doc = mapping_source_document(); jobs, steps, _ = module._build_jobs(doc)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        results.append(canonical(corrupt_preattest_plan(plan, mutation)))
    assert results[0] == results[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='preservation_mapping_'):
        PLAN_CHECKER._verify_source_preattest_preservation_equations(json.loads(results[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_restore_floor', 'missing_upload_raw', 'metadata_archive', 'extra_archive_reader'])
def test_preattest_rehashed_schema_valid_forgery_fails_actual_checker_cli(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_preattest_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'forged-preservation-plan.json'; path.write_bytes(raw)
    args = list(source_fixture.check_args); args[args.index('--plan') + 1] = path
    args[args.index('--expected-plan-sha256') + 1] = digest(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], args)
    report = json.loads(result.stdout)
    assert result.returncode != 0 and report['ok'] is False
    expected = {'missing_restore_floor': 'preservation_mapping_step_io_mismatch',
                'missing_upload_raw': 'preservation_mapping_step_io_mismatch',
                'metadata_archive': 'preservation_mapping_requirement_mismatch',
                'extra_archive_reader': 'preservation_mapping_archive_readers_mismatch'}
    assert report['error_code'] == expected[mutation]


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'rehashed'])
def test_preattest_workflow_identity_cannot_be_replaced(source_fixture, recorded_source_objects, side, fault):
    module, method = preattest_source_method(side); sources = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del sources[path]
    else:
        obj = sources[path]; raw = obj.data + b'\n# different source\n'
        sources[path] = replace(obj, data=raw, blob_sha1=module._sha1_git_blob(raw))
    with pytest.raises(module.PlanError, match='preservation_mapping_source_'):
        method(mapping_source_document(), sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['upload_omission', 'upload_duplicate', 'archive_name', 'other_run',
                                  'other_repository', 'copy_omission', 'hash_omission', 'restore_target'])
def test_preattest_source_drift_is_rejected_not_silently_reinterpreted(source_fixture, recorded_source_objects, side, fault):
    doc = mapping_source_document(); upload = doc['jobs']['pulse']['steps'][36]
    restore = doc['jobs']['release_grade_recorded_path']['steps'][3]
    if fault == 'upload_omission': upload['with']['path'] = '\n'.join(upload['with']['path'].splitlines()[:-1])
    elif fault == 'upload_duplicate': upload['with']['path'] += upload['with']['path'].splitlines()[0] + '\n'
    elif fault == 'archive_name': upload['with']['name'] += '-wrong'
    elif fault == 'other_run': restore['run'] = restore['run'].replace('gh run download "${GITHUB_RUN_ID}"', 'gh run download "42"')
    elif fault == 'other_repository': restore['run'] = restore['run'].replace('--repo "${GITHUB_REPOSITORY}"', '--repo "example/other"')
    elif fault == 'copy_omission': restore['run'] = restore['run'].replace('copy_required_artifact "status_baseline.json"\n', '')
    elif fault == 'hash_omission': restore['run'] = restore['run'].replace('sha256sum "${artifact}"', ':')
    elif fault == 'restore_target': restore['run'] = restore['run'].replace('cp "${src}" "${CANONICAL_ARTIFACTS}/${name}"', 'cp "${src}" "${DOWNLOAD_DIR}/${name}"')
    module, method = preattest_source_method(side)
    with pytest.raises(module.PlanError, match='preservation_mapping_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_preattest_installation_preserves_origins_and_all_outside_duties(source_fixture, recorded_source_objects, side):
    module, _ = preattest_source_method(side); doc = mapping_source_document()
    old_jobs, old_steps, _ = module._build_jobs(doc)
    with patch.object(module, '_install_preattest_preservation_projection', return_value=None):
        old_states = module._build_states(old_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    jobs, steps, _ = module._build_jobs(doc)
    states = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    owned = {steps[key]['occurrence_id'] for key in [('pulse', 37), ('release_grade_recorded_path', 4)]}
    assert len(states) == len(old_states) == 62
    for old, new in zip(old_states, states):
        old = copy.deepcopy(old); new = copy.deepcopy(new)
        for row in (old, new): row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v not in owned]
        assert old == new
    for key, step in steps.items():
        if step['occurrence_id'] not in owned: assert step == old_steps[key]
    assert steps[('release_grade_recorded_path', 4)]['output_state_ids'] == []
    assert steps[('pulse', 37)]['output_state_ids'] == ['state:step5c:pre-attestation-pulse-artifacts']


@pytest.mark.parametrize('fault', [None, 'missing_floor', 'empty_baseline', 'symlink_evidence', 'download_failure'])
def test_preattest_actual_restore_shell_with_local_mock_download(source_fixture, tmp_path, fault):
    root, incoming, runner, bindir = [tmp_path / v for v in ('workspace', 'incoming', 'runner', 'bin')]
    for directory in (root, incoming, runner, bindir): directory.mkdir()
    doc = mapping_source_document(); paths = doc['jobs']['pulse']['steps'][36]['with']['path'].splitlines()
    before = {}
    for relative in paths:
        p = incoming / relative; p.parent.mkdir(parents=True, exist_ok=True)
        before[relative] = ('synthetic preservation input: ' + relative + '\n').encode(); p.write_bytes(before[relative])
    base = 'PULSE_safe_pack_v0/artifacts/'
    if fault == 'missing_floor': (incoming / (base + 'self_contained_pulse_evidence_floor_v0.json')).unlink()
    elif fault == 'empty_baseline': (incoming / (base + 'status_baseline.json')).write_bytes(b'')
    elif fault == 'symlink_evidence':
        p = incoming / (base + 'required_gate_evidence_v0.json'); p.unlink()
        outside = tmp_path / 'not-an-artifact'; outside.write_bytes(b'synthetic link target\n'); p.symlink_to(outside)
    # This local stand-in records and verifies argv and copies only synthetic
    # files. No gh installation, credentials, workflow dispatch or API call.
    stub = bindir / 'gh'
    expected = ['run', 'download', '10001', '--repo', 'example/step5c', '--name',
                'pulse-pre-attestation-10001-1', '--dir', str(runner / 'pulse-pre-attestation')]
    stub.write_text('#!' + sys.executable + '\n' +
        'import json, pathlib, shutil, sys\n' +
        'expected = ' + repr(expected) + '\n' +
        'assert sys.argv[1:] == expected\n' +
        'pathlib.Path(' + repr(str(tmp_path / 'download-argv.json')) + ').write_text(json.dumps(sys.argv[1:]))\n' +
        ('raise SystemExit(7)\n' if fault == 'download_failure' else '') +
        'shutil.copytree(' + repr(str(incoming)) + ', expected[-1], dirs_exist_ok=True, symlinks=True)\n')
    stub.chmod(0o755)
    env = {'PATH': str(bindir) + ':/usr/bin:/bin', 'HOME': str(tmp_path), 'LANG': 'C', 'LC_ALL': 'C',
           'GITHUB_WORKSPACE': str(root), 'RUNNER_TEMP': str(runner), 'GITHUB_RUN_ID': '10001',
           'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REPOSITORY': 'example/step5c'}
    body = doc['jobs']['release_grade_recorded_path']['steps'][3]['run']
    result = subprocess.run(['/bin/bash', '-c', body], cwd=root, env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=30)
    assert json.loads((tmp_path / 'download-argv.json').read_text()) == expected
    if fault is not None:
        assert result.returncode != 0
        if fault != 'download_failure': assert b'::error::' in result.stdout
        if fault == 'missing_floor':
            # The historical restore is not transactional. Earlier copies may
            # remain after failure; this is not a successfully accepted capsule.
            assert (root / (base + 'status.json')).read_bytes() == before[base + 'status.json']
    else:
        assert result.returncode == 0, result.stderr
        restored = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        names = [shlex.split(line)[1] for line in body.splitlines() if line.startswith('copy_required_artifact "')]
        assert restored == {base + name: before[base + name] for name in names}
        hashes = {line.split(None, 1)[1].strip(): line.split(None, 1)[0]
                  for line in result.stdout.decode().splitlines()}
        assert hashes == {str(root / relative): digest(raw) for relative, raw in restored.items()}
        assert len(restored) == 7 and not (root / (base + 'external')).exists()


def test_preattest_mapping_does_not_promote_runtime_completion(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62 and len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary']['authority_effect'] == 'none'
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


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


# ---------------------------------------------------------------------------
# R12 source-derived required arguments. A separate role, not an observed argv
# receipt. The local shell oracle below records only its own synthetic run.
# ---------------------------------------------------------------------------
REQUIRED_ARGUMENT_STATE = 'state:step5c:effective-required-argument-list'
REQUIRED_ARGUMENT_INPUTS = (
    '.github/workflows/pulse_ci.yml', 'pulse_gate_policy_v0.yml',
    'tools/policy_to_require_args.py', 'PULSE_safe_pack_v0/tools/check_gates.py',
)


def required_argument_facts(side, source_fixture, *, workflow=None, sources=None):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    method = (module._required_arguments_source_projection if side == 'builder'
              else module._source_required_argument_expectations)
    return method(mapping_source_document() if workflow is None else workflow,
                  BUILDER._load_sources(source_fixture.root, source_fixture.sha)
                  if sources is None else sources)


def test_required_argument_role_is_present_and_not_a_runtime_receipt(source_fixture):
    matches = [s for s in source_fixture.plan['state_templates'] if s['state_id'] == REQUIRED_ARGUMENT_STATE]
    assert len(matches) == 1, 'The contracted source-derived required-argument role must be represented.'
    state = matches[0]
    assert state['role'] == 'source_derived_required_arguments_runtime_receipt_unavailable'
    assert state['state_type'] == 'other'
    assert state['required'] is True and state['content_requirement'] == 'exact_digest'
    assert state['producer_occurrence_id'] is None
    assert state['required_consumer_occurrence_ids'] == []
    assert state['authority_bearing'] is False and state['mutation_class'] == 'none'
    assert state['path_or_uri'].startswith('projection://pulse_gate_policy_v0.yml#r12-source-required-arguments/sha256/')
    for job in source_fixture.plan['jobs']:
        for step in job['steps']:
            assert REQUIRED_ARGUMENT_STATE not in step['input_state_ids'] + step['output_state_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_required_argument_derivation_matches_real_policy_cli(source_fixture, side):
    f = source_fixture
    facts = required_argument_facts(side, f)
    derived = facts['derivation']
    actual_sets = {}
    for name in ('required', 'release_required'):
        result = cli(f.root, 'policy_to_require_args', ['--policy', f.root / 'pulse_gate_policy_v0.yml',
                                                      '--set', name, '--format', 'newline'])
        require_cli_success(result)
        actual_sets[name] = result.stdout.decode('utf-8').splitlines()
    assert derived['policy_set_members'] == actual_sets
    actual_union = list(dict.fromkeys(actual_sets['required'] + actual_sets['release_required']))
    assert derived['ordered_required_gate_ids'] == actual_union
    assert len(actual_sets['required']) == 19 and len(actual_sets['release_required']) == 4
    assert len(actual_union) == 23
    assert derived['selected_sets'] == ['required', 'release_required']
    assert derived['original_runtime_argv_receipt'] == 'unavailable'
    assert derived['source_derived_only'] is True and derived['authority_effect'] == 'none'
    assert facts['derivation_sha256'] == digest(canonical(derived))
    assert facts['locator'].endswith('/' + facts['derivation_sha256'])
    state = next(s for s in f.plan['state_templates'] if s['state_id'] == REQUIRED_ARGUMENT_STATE)
    assert state['path_or_uri'] == facts['locator']


def test_required_argument_exact_r12_shell_oracle_on_synthetic_status(source_fixture, tmp_path):
    """Run the unmodified bounded R12 body, with real helpers and a local argv tap."""
    f = source_fixture
    document = mapping_source_document()
    body = document['jobs']['release_grade_recorded_path']['steps'][11]['run']
    # This guard fixes which shell text this test is permitted to execute.
    assert digest(body.encode()) == 'dababaec377d50eb83daa95fab958009089db11a207214bdbab1ea0156a0f81a'
    root = tmp_path / 'r12-local-example'; root.mkdir()
    for relative in REQUIRED_ARGUMENT_INPUTS[1:]:
        target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((f.root / relative).read_bytes())
    policy = yaml.safe_load((root / 'pulse_gate_policy_v0.yml').read_text())
    status_path = root / 'PULSE_safe_pack_v0/artifacts/status.json'
    status_path.parent.mkdir(parents=True)
    status_path.write_text(json.dumps({'gates': {g: True for g in policy['gates']['required']
                                               + policy['gates']['release_required']}}))
    recorder = root / 'local_argv_tap.py'
    recorder.write_text('import json, os, sys\nfrom pathlib import Path\n'
                        'Path(os.environ["LOCAL_ARGV_TAP"]).write_text(json.dumps(sys.argv[1:]))\n')
    prefix = r'''
python() {
  case "$1" in
    tools/policy_to_require_args.py) ;;
    PULSE_safe_pack_v0/tools/check_gates.py)
      "$LOCAL_PYTHON" "$LOCAL_ARGV_RECORDER" "$@" || return $? ;;
    *) return 97 ;;
  esac
  "$LOCAL_PYTHON" "$@"
}
'''
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C', 'LC_ALL': 'C',
           'PACK_DIR': 'PULSE_safe_pack_v0', 'LOCAL_PYTHON': sys.executable,
           'LOCAL_ARGV_RECORDER': str(recorder), 'LOCAL_ARGV_TAP': str(root / 'LOCAL_ONLY_argv.json')}
    result = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', prefix + body], cwd=root,
                            env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    require_cli_success(result)
    actual = json.loads((root / 'LOCAL_ONLY_argv.json').read_text())
    facts = required_argument_facts('checker', f)['derivation']
    assert actual[:4] == [facts['checker_path'], '--status', facts['status_selector'], '--require']
    assert actual[4:] == facts['ordered_required_gate_ids']
    assert b'[OK] All required gates PASS' in result.stdout
    # No local tap or synthetic execution is promoted into the source plan.
    assert facts['original_runtime_argv_receipt'] == 'unavailable'


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', REQUIRED_ARGUMENT_INPUTS)
def test_required_argument_source_digests_are_exact_and_already_preserved(source_fixture, side, path):
    facts = required_argument_facts(side, source_fixture)
    bindings = facts['derivation']['source_bindings']
    record = next(row for row in bindings if row['path'] == path)
    data = (source_fixture.root / path).read_bytes()
    assert record == {'path': path, 'sha256': digest(data)}
    assert sum(row['path'] == path for row in bindings) == 1
    assert prepared_fixture_members(source_fixture)['sources/' + path] == data


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', REQUIRED_ARGUMENT_INPUTS)
@pytest.mark.parametrize('mutation', ['missing', 'changed_rehashed'])
def test_required_argument_rejects_missing_or_rehashed_source(source_fixture, recorded_source_objects, side, path, mutation):
    objects = dict(recorded_source_objects)
    if mutation == 'missing':
        objects.pop(path)
    else:
        obj = objects[path]; data = obj.data + b'\n# synthetic drift; not a new reviewed profile\n'
        objects[path] = replace(obj, data=data, blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    with pytest.raises(module.PlanError, match='required_argument_'):
        required_argument_facts(side, source_fixture, sources=objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', [
    'reverse_order', 'omit_deduplication', 'unquoted_expansion', 'replace_selected_set',
    'empty_guard_removed', 'extra_command', 'duplicate_command', 'changed_status', 'renamed_step',
])
def test_required_argument_changed_shell_semantics_fail_closed(source_fixture, side, mutation):
    doc = mapping_source_document()
    step = doc['jobs']['release_grade_recorded_path']['steps'][11]
    changes = {
        'reverse_order': ('for gate in "${REQUIRED_GATES[@]}" "${RELEASE_REQUIRED_GATES[@]}";',
                          'for gate in "${RELEASE_REQUIRED_GATES[@]}" "${REQUIRED_GATES[@]}";'),
        'omit_deduplication': ('if [[ -z "${SEEN[${gate}]+x}" ]]; then', 'if true; then'),
        'unquoted_expansion': ('--require "${EFFECTIVE_GATES[@]}"', '--require ${EFFECTIVE_GATES[@]}'),
        'replace_selected_set': ('--set release_required', '--set advisory'),
        'empty_guard_removed': ('if (( ${#REQUIRED_GATES[@]} == 0 )); then', 'if false; then'),
        'changed_status': ('STATUS="${PACK_DIR}/artifacts/status.json"', 'STATUS="${PACK_DIR}/artifacts/status_baseline.json"'),
    }
    if mutation in changes:
        old, new = changes[mutation]; assert old in step['run']; step['run'] = step['run'].replace(old, new)
    elif mutation == 'extra_command': step['run'] += '\necho unexpected\n'
    elif mutation == 'duplicate_command': step['run'] += '\n' + step['run']
    else: step['name'] = 'Different source step'
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    with pytest.raises(module.PlanError, match='required_argument_'):
        required_argument_facts(side, source_fixture, workflow=doc)


def corrupt_required_argument_role(plan, mutation):
    rows = plan['state_templates']
    state = next(row for row in rows if row['state_id'] == REQUIRED_ARGUMENT_STATE)
    r12 = next(job for job in plan['jobs'] if job['source_job_id'] == 'release_grade_recorded_path')['steps'][11]
    if mutation == 'omitted': rows.remove(state)
    elif mutation == 'duplicate': rows.append(copy.deepcopy(state))
    elif mutation == 'false_digest': state['path_or_uri'] = state['path_or_uri'].rsplit('/', 1)[0] + '/' + '0' * 64
    elif mutation == 'runtime_receipt': state['role'] = 'observed_runtime_argv_receipt'
    elif mutation == 'optional': state['required'] = False
    elif mutation == 'weaker_content': state['content_requirement'] = 'metadata_only'
    elif mutation == 'false_producer':
        state['producer_occurrence_id'] = r12['occurrence_id']; r12['output_state_ids'].append(REQUIRED_ARGUMENT_STATE)
    elif mutation == 'false_consumer':
        state['required_consumer_occurrence_ids'] = [r12['occurrence_id']]; r12['input_state_ids'].append(REQUIRED_ARGUMENT_STATE)
    elif mutation == 'unpaired_input': r12['input_state_ids'].append(REQUIRED_ARGUMENT_STATE)
    elif mutation == 'unpaired_output': r12['output_state_ids'].append(REQUIRED_ARGUMENT_STATE)
    elif mutation == 'gate_value_alias':
        state['path_or_uri'] = next(row for row in rows if row['state_id'] == 'state:step5c:materialized-release-required-gate-set')['path_or_uri']
    elif mutation == 'authority_promotion': state['authority_bearing'] = True
    else: raise AssertionError(mutation)
    rows.sort(key=lambda row: row['state_id'])
    for job in plan['jobs']:
        for step in job['steps']:
            step['input_state_ids'].sort(); step['output_state_ids'].sort()
    return plan


@pytest.mark.parametrize('mutation', [
    'omitted', 'duplicate', 'false_digest', 'runtime_receipt', 'optional', 'weaker_content',
    'false_producer', 'false_consumer', 'unpaired_input', 'unpaired_output',
    'gate_value_alias', 'authority_promotion',
])
def test_required_argument_common_false_mapping_rejected(source_fixture, recorded_source_objects, mutation):
    plan = corrupt_required_argument_role(copy.deepcopy(source_fixture.plan), mutation)
    with pytest.raises(PLAN_CHECKER.PlanError, match='required_argument_'):
        PLAN_CHECKER._verify_source_required_argument_equations(plan, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['omitted', 'false_digest', 'runtime_receipt', 'unpaired_input'])
def test_required_argument_real_checker_cli_rejects_rehashed_plan(source_fixture, tmp_path, mutation):
    f = source_fixture
    plan = corrupt_required_argument_role(copy.deepcopy(f.plan), mutation)
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(plan)
    raw = canonical(plan); target = tmp_path / 'false-arguments-plan.json'; target.write_bytes(raw)
    result = cli(f.root, TOOL_NAMES[1], ['--repository-root', f.root, '--plan', target,
        '--expected-source-commit', f.sha, '--expected-plan-sha256', digest(raw), '--expected-record-status', 'example'])
    assert result.returncode != 0
    diagnostic = json.loads(result.stdout)
    assert diagnostic['ok'] is False and diagnostic['error_code'].startswith('required_argument_')


@pytest.mark.parametrize('mutation', ['false_digest', 'runtime_receipt', 'false_producer'])
def test_required_argument_actual_two_constructors_cannot_hide_shared_error(source_fixture, recorded_source_objects, mutation):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        workflow = mapping_source_document()
        jobs, steps, _ = module._build_jobs(workflow)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        answers.append(canonical(corrupt_required_argument_role(plan, mutation)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='required_argument_'):
        PLAN_CHECKER._verify_source_required_argument_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('required,release', [(['z_gate', 'a_gate', 'z_gate'], ['a_gate', 'b_gate']),
                                            (['one'], ['one']), (['third', 'first'], ['second'])])
def test_required_argument_policy_parser_preserves_duplicates_and_source_order(side, required, release):
    data = ('gates:\n  required:\n' + ''.join('    - ' + g + '\n' for g in required)
            + '  release_required:\n' + ''.join('    - ' + g + '\n' for g in release)).encode()
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    parse = module._required_argument_policy_sets if side == 'builder' else module._source_required_policy_members
    # Pure parser cases do not authorize a changed policy in the pinned profile.
    assert parse(data) == {'required': required, 'release_required': release}


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('data', [
    b'gates:\n  required: []\n  release_required:\n    - gate\n',
    b'gates:\n  required:\n  release_required:\n    - gate\n',
    b'gates:\n  required:\n    - gate\n',
    b'gates:\n  required:\n    - "quoted"\n  release_required:\n    - gate\n',
    b'gates:\n  required:\n    - $(not_executed)\n  release_required:\n    - gate\n',
    b'gates:\n  required:\n    - gate\n  required:\n    - other\n  release_required:\n    - gate\n',
    b'\xff',
])
def test_required_argument_unsupported_policy_dialect_rejected(side, data):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    parse = module._required_argument_policy_sets if side == 'builder' else module._source_required_policy_members
    with pytest.raises(module.PlanError):
        parse(data)


def test_required_argument_predicate_runs_before_expected_reconstruction():
    source = inspect.getsource(PLAN_CHECKER.check_plan)
    assert source.index('_verify_source_required_argument_equations(') < source.index('_reconstruct_expected_plan(')
    builder_tree = ast.dump(ast.parse(textwrap.dedent(inspect.getsource(BUILDER._required_arguments_source_projection))), include_attributes=False)
    checker_tree = ast.dump(ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER._source_required_argument_expectations))), include_attributes=False)
    assert builder_tree != checker_tree


def test_required_argument_role_remains_unavailable_until_runtime_integration(source_fixture):
    plan = source_fixture.plan
    assert len(plan['state_templates']) == 62
    assert len(plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in plan
    packet = runtime_projection_example(source_fixture)
    state = next(row for row in packet['state_observations'] if row['state_id'] == REQUIRED_ARGUMENT_STATE)
    assert state['content_status'] == 'unavailable'
    assert state['sha256'] is None and state['size_bytes'] is None
    assert state['producer_execution_id'] is None
    assert packet['coverage']['coverage_status'] == 'partial'
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(plan, packet, {})


# ---------------------------------------------------------------------------
# Source-grounded audit/advisory preservation regressions. These inspect the
# workflow and use synthetic files; no hosted run or artifact is acquired.
# ---------------------------------------------------------------------------
BUNDLE_COPY_INPUTS = [
    (22, 'final-status', 'PULSE_safe_pack_v0/artifacts/status.json'),
    (22, 'quality-ledger-final', 'PULSE_safe_pack_v0/artifacts/report_card.html'),
    (22, 'release-authority-manifest', 'PULSE_safe_pack_v0/artifacts/release_authority_v0.json'),
    (25, 'final-status', 'PULSE_safe_pack_v0/artifacts/status.json'),
    (25, 'quality-ledger-final', 'PULSE_safe_pack_v0/artifacts/report_card.html'),
    (25, 'release-authority-manifest', 'PULSE_safe_pack_v0/artifacts/release_authority_v0.json'),
    (25, 'release-authority-audit-bundle', 'PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle'),
    (25, 'llamaguard-summary', 'PULSE_safe_pack_v0/artifacts/external/*_summary.json'),
    (25, 'release-grade-junit', 'PULSE_safe_pack_v0/artifacts/reports/junit.xml'),
    (25, 'release-grade-sarif', 'PULSE_safe_pack_v0/artifacts/reports/sarif.json'),
]
BUNDLE_COPY_MUTATIONS = [
    'missing_audit', 'missing_advisory', 'audit_locator', 'advisory_locator',
    'audit_upload_as_producer', 'advisory_upload_as_producer',
    'missing_audit_status', 'extra_audit_decision', 'missing_advisory_summary',
    'advisory_postcondition_reader', 'audit_download_reader', 'missing_audit_assembler',
    'missing_audit_upload', 'missing_audit_report_upload', 'advisory_assembler_reader',
    'audit_optional', 'advisory_optional', 'audit_metadata_only', 'advisory_unavailable',
    'advisory_authority_promotion', 'input_locator', 'unpaired_copy_input',
]


def bundle_copy_module(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    function = module._bundle_source_projection if side == 'builder' else module._source_bundle_expectations
    return module, function


def bundle_plan_steps(plan):
    return {(j['source_job_id'], s['source_ordinal']): s for j in plan['jobs'] for s in j['steps']}


@pytest.mark.parametrize('number,role,source_path', BUNDLE_COPY_INPUTS)
def test_bundle_copy_inputs_are_supported_by_literal_source(source_fixture, number, role, source_path):
    raw = mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][number - 1]['run']
    cp_commands = [shlex.split(line) for line in raw.replace('\\\n', ' ').splitlines() if line.strip().startswith('cp ')]
    source_paths = [words[2] if words[1] == '-a' else words[1] for words in cp_commands]
    source_paths = [path.replace('${PACK_DIR}', 'PULSE_safe_pack_v0') for path in source_paths]
    assert source_path in source_paths
    plan = source_fixture.plan
    step = bundle_plan_steps(plan)[('release_grade_recorded_path', number)]
    state = next(s for s in plan['state_templates'] if s['state_id'] == 'state:step5c:' + role)
    assert state['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in state['required_consumer_occurrence_ids']
    if '*' not in source_path:
        assert state['path_or_uri'].rstrip('/') == source_path
    else:
        assert state['path_or_uri'].rsplit('/', 1)[0] == source_path.rsplit('/', 1)[0]
        assert state['path_or_uri'].endswith('_summary.json')


@pytest.mark.parametrize('number,roles,output', [
    (22, ['final-status', 'quality-ledger-final', 'release-authority-manifest'], 'release-authority-audit-bundle'),
    (25, ['advisory-reference-bundle'], 'advisory-reference-bundle'),
])
def test_bundle_copy_step_closure(source_fixture, recorded_source_objects, number, roles, output):
    # Source independently enumerates the seven selected R25 input roles.
    if number == 25:
        roles = [role for n, role, _ in BUNDLE_COPY_INPUTS if n == number]
    expected = sorted('state:step5c:' + role for role in roles)
    step = bundle_plan_steps(source_fixture.plan)[('release_grade_recorded_path', number)]
    assert step['input_state_ids'] == expected
    assert step['output_state_ids'] == ['state:step5c:' + output]
    assert sorted(s['state_id'] for s in source_fixture.plan['state_templates']
                  if step['occurrence_id'] in s['required_consumer_occurrence_ids']) == expected
    PLAN_CHECKER._verify_source_bundle_equations(source_fixture.plan, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('role,producer,readers', [
    ('release-authority-audit-bundle', 22,
     [('release_grade_recorded_path', 25), ('release_grade_recorded_path', 28),
      ('release_grade_recorded_path', 31), ('assemble_release_grade_reference_package', 5)]),
    ('advisory-reference-bundle', 25, [('release_grade_recorded_path', 32)]),
])
def test_bundle_content_origin_and_direct_readers(source_fixture, role, producer, readers):
    steps = bundle_plan_steps(source_fixture.plan)
    row = next(s for s in source_fixture.plan['state_templates'] if s['state_id'] == 'state:step5c:' + role)
    assert row['producer_occurrence_id'] == steps[('release_grade_recorded_path', producer)]['occurrence_id']
    expected = sorted(steps[key]['occurrence_id'] for key in readers)
    assert row['required_consumer_occurrence_ids'] == expected
    assert sorted(s['occurrence_id'] for s in steps.values() if row['state_id'] in s['input_state_ids']) == expected
    assert row['required'] is True and row['content_requirement'] == 'exact_digest'
    assert row['authority_bearing'] is (role == 'release-authority-audit-bundle')


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_bundle_source_copy_inventory_handoff_and_conditions(source_fixture, recorded_source_objects, side):
    _, method = bundle_copy_module(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    document = mapping_source_document()
    steps = document['jobs']['release_grade_recorded_path']['steps']
    assert [len(facts['copies'][r]) for r in BUILDER._BUNDLE_ROLES] == [3, 7]
    assert facts['publications']['release-authority-audit-bundle']['name'] == steps[27]['with']['name']
    assert facts['publications']['advisory-reference-bundle']['name'] == steps[31]['with']['name']
    assert facts['conditions'] == {'assembly': steps[24]['if'], 'publication': steps[31]['if']}
    assert facts['package_member'] == 'release-authority-audit-bundle'
    glob = next(r for r in facts['copies']['advisory-reference-bundle'] if r['role'] == 'llamaguard-summary')
    assert glob['copy_kind'] == 'selected_member_of_source_glob'
    assert '*' in glob['source_selector']
    assert not any('artifact_id' in entry for entries in facts['copies'].values() for entry in entries)
    assert facts == bundle_copy_module('checker' if side == 'builder' else 'builder')[1](document, recorded_source_objects)


def corrupt_bundle_copy_plan(plan, mutation):
    plan = copy.deepcopy(plan)
    states = {s['state_id'].removeprefix('state:step5c:'): s for s in plan['state_templates']}
    steps = bundle_plan_steps(plan)
    def edge(role, job, number, add):
        row = states[role]; step = steps[(job, number)]
        oid, sid = step['occurrence_id'], row['state_id']
        if add:
            row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {oid})
            step['input_state_ids'] = sorted(set(step['input_state_ids']) | {sid})
        else:
            row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v != oid]
            step['input_state_ids'] = [v for v in step['input_state_ids'] if v != sid]
    audit, advisory = 'release-authority-audit-bundle', 'advisory-reference-bundle'
    if mutation.startswith('missing_') and mutation in ('missing_audit', 'missing_advisory'):
        sid = states[audit if mutation == 'missing_audit' else advisory]['state_id']
        plan['state_templates'] = [s for s in plan['state_templates'] if s['state_id'] != sid]
        for step in steps.values():
            for key in ('input_state_ids', 'output_state_ids'):
                step[key] = [v for v in step[key] if v != sid]
    elif mutation in ('audit_locator', 'advisory_locator'):
        states[audit if mutation == 'audit_locator' else advisory]['path_or_uri'] += 'wrong'
    elif mutation in ('audit_upload_as_producer', 'advisory_upload_as_producer'):
        role, number = (audit, 28) if mutation == 'audit_upload_as_producer' else (advisory, 32)
        sid = states[role]['state_id']
        for step in steps.values():
            step['output_state_ids'] = [v for v in step['output_state_ids'] if v != sid]
        publisher = steps[('release_grade_recorded_path', number)]
        publisher['output_state_ids'] = sorted(publisher['output_state_ids'] + [sid])
        states[role]['producer_occurrence_id'] = publisher['occurrence_id']
    elif mutation in ('audit_optional', 'advisory_optional'):
        states[audit if mutation.startswith('audit') else advisory]['required'] = False
    elif mutation in ('audit_metadata_only', 'advisory_unavailable'):
        states[audit if mutation.startswith('audit') else advisory]['content_requirement'] = 'metadata_only' if mutation.startswith('audit') else 'unavailable'
    elif mutation == 'advisory_authority_promotion':
        states[advisory]['authority_bearing'] = True
    elif mutation == 'input_locator':
        states['llamaguard-summary']['path_or_uri'] = 'PULSE_safe_pack_v0/artifacts/external/wrong_summary.json'
    elif mutation == 'unpaired_copy_input':
        steps[('release_grade_recorded_path', 22)]['input_state_ids'].remove('state:step5c:final-status')
    else:
        role, job, number, add = {
            'missing_audit_status': ('final-status', 'release_grade_recorded_path', 22, False),
            'extra_audit_decision': ('release-decision', 'release_grade_recorded_path', 22, True),
            'missing_advisory_summary': ('llamaguard-summary', 'release_grade_recorded_path', 25, False),
            'advisory_postcondition_reader': (advisory, 'release_grade_recorded_path', 26, True),
            'audit_download_reader': (audit, 'assemble_release_grade_reference_package', 4, True),
            'missing_audit_assembler': (audit, 'assemble_release_grade_reference_package', 5, False),
            'missing_audit_upload': (audit, 'release_grade_recorded_path', 28, False),
            'missing_audit_report_upload': (audit, 'release_grade_recorded_path', 31, False),
            'advisory_assembler_reader': (advisory, 'assemble_release_grade_reference_package', 5, True),
        }[mutation]
        edge(role, job, number, add)
    return plan


@pytest.mark.parametrize('mutation', BUNDLE_COPY_MUTATIONS)
def test_bundle_common_wrong_plan_fails_source_predicate(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_bundle_copy_plan(source_fixture.plan, mutation)
    # Equal, independently serialized false answers still need source truth.
    first, second = canonical(bad), canonical(copy.deepcopy(bad))
    assert first == second
    with pytest.raises(PLAN_CHECKER.PlanError, match='bundle_mapping_'):
        PLAN_CHECKER._verify_source_bundle_equations(json.loads(first), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_audit_status', 'audit_download_reader', 'advisory_postcondition_reader'])
def test_bundle_actual_constructors_shared_error_still_rejected(source_fixture, recorded_source_objects, mutation):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        document = mapping_source_document()
        jobs, steps, _ = module._build_jobs(document)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        answers.append(canonical(corrupt_bundle_copy_plan(plan, mutation)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='bundle_mapping_'):
        PLAN_CHECKER._verify_source_bundle_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_audit_status', 'missing_advisory_summary', 'audit_download_reader', 'advisory_postcondition_reader'])
def test_bundle_rehashed_forged_plan_fails_real_checker_cli(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_bundle_copy_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'forged-plan.json'; path.write_bytes(raw)
    args = list(source_fixture.check_args)
    args[args.index('--plan') + 1] = path
    args[args.index('--expected-plan-sha256') + 1] = digest(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], args)
    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report['ok'] is False and 'bundle_mapping_' in result.stdout.decode()


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', ['.github/workflows/pulse_ci.yml', 'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py'])
@pytest.mark.parametrize('mutation', ['missing', 'rehashed'])
def test_bundle_semantic_source_substitution_rejected(source_fixture, recorded_source_objects, side, path, mutation):
    module, method = bundle_copy_module(side)
    objects = dict(recorded_source_objects)
    if mutation == 'missing':
        del objects[path]
    else:
        original = objects[path]; changed = original.data + b'\n# changed source example\n'
        objects[path] = replace(original, data=changed, blob_sha1=module._sha1_git_blob(changed))
    with pytest.raises(module.PlanError, match='bundle_mapping_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', ['copy_input', 'copy_destination', 'copy_flag', 'summary_glob',
                                     'advisory_condition', 'publication_condition', 'publication_name',
                                     'publication_path', 'download_name', 'assembler_argument'])
def test_bundle_changed_workflow_not_silently_reinterpreted(source_fixture, recorded_source_objects, side, mutation):
    document = mapping_source_document()
    rows = document['jobs']['release_grade_recorded_path']['steps']
    if mutation == 'copy_input': rows[21]['run'] = rows[21]['run'].replace('/status.json', '/status_baseline.json')
    elif mutation == 'copy_destination': rows[21]['run'] = rows[21]['run'].replace('${BUNDLE}/status.json', '${BUNDLE}/../status.json')
    elif mutation == 'copy_flag': rows[24]['run'] = rows[24]['run'].replace('cp -a ', 'cp -r ')
    elif mutation == 'summary_glob': rows[24]['run'] = rows[24]['run'].replace('*_summary.json', '*.json')
    elif mutation == 'advisory_condition': rows[24]['if'] = '${{ always() }}'
    elif mutation == 'publication_condition': rows[31]['if'] = '${{ always() }}'
    elif mutation == 'publication_name': rows[27]['with']['name'] += '-changed'
    elif mutation == 'publication_path': rows[27]['with']['path'] = 'PULSE_safe_pack_v0/artifacts/'
    elif mutation == 'download_name':
        item = document['jobs']['assemble_release_grade_reference_package']['steps'][3]
        item['run'] = item['run'].replace('--name "release-authority-audit-bundle"', '--name "other-bundle"')
    else:
        item = document['jobs']['assemble_release_grade_reference_package']['steps'][4]
        item['run'] = item['run'].replace('--audit-bundle-dir "${AUDIT_BUNDLE_DIR}"', '--audit-bundle-dir "${RECORDED_PATH_DIR}"')
    module, method = bundle_copy_module(side)
    with pytest.raises(module.PlanError, match='bundle_mapping_workflow_drift'):
        method(document, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('body', ['cp -r "${PACK_DIR}/a" "${BUNDLE}/b"',
                                 'cp "${PACK_DIR}/a" "${BUNDLE}/b"; echo changed',
                                 'cp "${PACK_DIR}/a" "${BUNDLE}/b" "extra"',
                                 'cp "$(not_executed)" "${BUNDLE}/b"',
                                 'cp "${PACK_DIR}/a" "${BUNDLE}/b"\ncp "${PACK_DIR}/a" "${BUNDLE}/b"'])
def test_bundle_unsupported_copy_grammar_rejected(side, body):
    module, _ = bundle_copy_module(side)
    parser = module._bundle_copy_commands if side == 'builder' else module._source_bundle_copies
    with pytest.raises(module.PlanError, match='bundle_mapping_copy_'):
        parser({'run': body})


@pytest.mark.parametrize('extra_summary', [False, True])
def test_bundle_actual_copy_shells_match_synthetic_preservation(tmp_path, source_fixture, recorded_source_objects, extra_summary):
    document = mapping_source_document()
    root = tmp_path / 'workspace'; pack = root / 'PULSE_safe_pack_v0'; temporary = tmp_path / 'temp'
    temporary.mkdir(); (pack / 'artifacts/external').mkdir(parents=True); (pack / 'artifacts/reports').mkdir()
    files = {
        'artifacts/status.json': b'{"example":"status"}\n',
        'artifacts/report_card.html': b'<p>synthetic ledger</p>\n',
        'artifacts/release_authority_v0.json': b'{"example":"authority"}\n',
        'artifacts/external/llamaguard_summary.json': b'{"example":"summary"}\n',
        'artifacts/reports/junit.xml': b'<testsuites/>\n',
        'artifacts/reports/sarif.json': b'{"example":"sarif"}\n',
    }
    if extra_summary:
        files['artifacts/external/additional_summary.json'] = b'{"example":"outside selected state roles"}\n'
    for path, raw in files.items(): (pack / path).write_bytes(raw)
    env_file = tmp_path / 'github-env'
    environment = {'PATH': '/usr/bin:/bin', 'PACK_DIR': str(pack), 'RUNNER_TEMP': str(temporary), 'GITHUB_ENV': str(env_file)}
    # Exact source bodies, controlled local paths. No production/release tool,
    # inference, API, artifact upload or actual GitHub environment is invoked.
    for ordinal in (22, 25):
        body = document['jobs']['release_grade_recorded_path']['steps'][ordinal - 1]['run']
        result = subprocess.run(['/bin/bash', '-c', body], cwd=root, env=environment,
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
    audit = pack / 'artifacts/release_authority_audit_bundle'
    advisory = temporary / 'release-grade-reference-run-v0'
    assert {p.name for p in audit.iterdir()} == {'status.json', 'report_card.html', 'release_authority_v0.json'}
    for name in ('status.json', 'report_card.html', 'release_authority_v0.json'):
        assert (audit / name).read_bytes() == files['artifacts/' + name]
        assert (advisory / 'release-authority-audit-bundle' / name).read_bytes() == files['artifacts/' + name]
        assert (advisory / 'artifacts' / name).read_bytes() == files['artifacts/' + name]
    assert (advisory / 'reports/junit.xml').read_bytes() == files['artifacts/reports/junit.xml']
    assert (advisory / 'reports/sarif.json').read_bytes() == files['artifacts/reports/sarif.json']
    assert len([p for p in advisory.rglob('*') if p.is_file()]) == 9 + int(extra_summary)
    assert env_file.read_text().strip() == 'REFERENCE_BUNDLE_DIR=' + str(advisory)
    facts = BUILDER._bundle_source_projection(document, recorded_source_objects)
    assert len(facts['copy_inputs'][BUILDER._step_id('release_grade_recorded_path', 25)]) == 7
    # Seven selected roles do not claim that a runtime glob had seven members.
    if extra_summary:
        assert (advisory / 'artifacts/external/additional_summary.json').is_file()


def test_bundle_mapping_does_not_change_role_inventory_or_runtime_acceptance(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    source = (SOURCES / 'check_pulsemech_compute_whole_runtime_observation_v0.py').read_text()
    assert 'declared_state_evidence_incomplete' in source
    assert not any('artifact_id' in s for s in source_fixture.plan['state_templates'])


# Provenance mapping: fixed source declarations, not hosted read receipts.
PROVENANCE_INPUTS = [
    ('--status', 'final-status'), ('--policy', 'gate-policy'),
    ('--ledger', 'quality-ledger-final'), ('--release-decision', 'release-decision'),
    ('--release-authority-manifest', 'release-authority-manifest'),
]
PROVENANCE_READERS = [
    ('release_grade_recorded_path', 26), ('release_grade_recorded_path', 29),
    ('release_grade_recorded_path', 33), ('attest_release_grade_artifact_binding', 1),
    ('attest_release_grade_artifact_binding', 2), ('assemble_release_grade_reference_package', 5),
    ('verify_release_grade_reference_package', 5), ('verify_release_grade_reference_package', 7),
]
PROVENANCE_MUTATIONS = [
    'missing_policy', 'missing_ledger', 'pre_ledger_alias', 'composed_ledger_alias',
    'source_argv_input', 'self_read', 'package_download_reader', 'missing_attestation_hash',
    'missing_attestation_action', 'missing_package_copy', 'missing_postcondition_hash',
    'missing_secondary_upload', 'missing_package_json_reader', 'publisher_as_producer',
    'wrong_locator', 'optional', 'metadata_only', 'wrong_mutation_class',
    'reverse_only', 'forward_only', 'missing_role',
]


def provenance_method(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    return module, (module._provenance_source_projection if side == 'builder'
                    else module._source_provenance_expectations)


def provenance_rows(plan):
    return ({row['state_id'].removeprefix('state:step5c:'): row for row in plan['state_templates']},
            bundle_plan_steps(plan))


@pytest.mark.parametrize('flag,role', PROVENANCE_INPUTS)
def test_provenance_r21_actual_file_input_is_mapped(source_fixture, flag, role):
    body = mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][20]['run']
    command = next(shlex.split(line) for line in body.replace('\\\n', ' ').splitlines()
                   if 'python "${PACK_DIR}/tools/build_artifact_provenance_binding_v0.py"' in line)
    location = command[command.index(flag) + 1].replace('${PACK_DIR}/', 'PULSE_safe_pack_v0/').replace('${GITHUB_WORKSPACE}/', '')
    states, steps = provenance_rows(source_fixture.plan)
    r21 = steps[('release_grade_recorded_path', 21)]
    assert states[role]['path_or_uri'] == location
    assert states[role]['state_id'] in r21['input_state_ids']
    assert r21['occurrence_id'] in states[role]['required_consumer_occurrence_ids']


@pytest.mark.parametrize('job,ordinal', PROVENANCE_READERS)
def test_provenance_content_readers_have_both_references(source_fixture, job, ordinal):
    states, steps = provenance_rows(source_fixture.plan)
    row = states['artifact-provenance-binding']; step = steps[(job, ordinal)]
    assert row['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in row['required_consumer_occurrence_ids']


def test_provenance_exact_reader_set_preserves_hash_vs_transfer_distinction(source_fixture):
    states, steps = provenance_rows(source_fixture.plan)
    row = states['artifact-provenance-binding']
    assert row['required_consumer_occurrence_ids'] == sorted(steps[k]['occurrence_id'] for k in [*PROVENANCE_READERS, ('release_grade_recorded_path', 31)])
    assert row['producer_occurrence_id'] == steps[('release_grade_recorded_path', 21)]['occurrence_id']
    assert row['state_id'] not in steps[('assemble_release_grade_reference_package', 4)]['input_state_ids']
    raw = mapping_source_document()['jobs']['attest_release_grade_artifact_binding']['steps'][0]['run']
    assert 'sha256sum "attestation-subject/artifact_provenance_binding_v0.json"' in raw
    assert row['state_id'] not in steps[('release_grade_recorded_path', 21)]['input_state_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_provenance_projection_is_source_only_and_pins_both_semantic_tools(source_fixture, recorded_source_objects, side):
    module, method = provenance_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    assert facts == provenance_method('checker' if side == 'builder' else 'builder')[1](mapping_source_document(), recorded_source_objects)
    assert facts['package_member'] == 'artifacts/artifact_provenance_binding_v0.json'
    assert facts['attestation_subject'] == 'attestation-subject/artifact_provenance_binding_v0.json'
    assert facts['policy_sets'] == ['required', 'release_required']
    inventory = {row['path']: row for row in source_fixture.plan['source_inventory']}
    for path in (module._PROVENANCE_BUILD, module._PROVENANCE_VERIFY):
        assert inventory[path]['git_blob_sha1'] == module._PROVENANCE_SOURCE_PINS[path]
        assert inventory[path]['sha256'] == digest((source_fixture.root / path).read_bytes())
    assert set(facts) == {'locator', 'input_locators', 'producer', 'consumers', 'package_member',
                         'attestation_subject', 'publication_name', 'policy_sets'}


def corrupt_provenance_plan(original, mutation):
    plan = copy.deepcopy(original)
    states, steps = provenance_rows(plan)
    row = states['artifact-provenance-binding']; sid = row['state_id']
    r21 = steps[('release_grade_recorded_path', 21)]
    def edge(role, key, add):
        record = states[role]; target = steps[key]; occurrence = target['occurrence_id']; state_id = record['state_id']
        if add:
            target['input_state_ids'] = sorted(set(target['input_state_ids']) | {state_id})
            record['required_consumer_occurrence_ids'] = sorted(set(record['required_consumer_occurrence_ids']) | {occurrence})
        else:
            target['input_state_ids'] = [v for v in target['input_state_ids'] if v != state_id]
            record['required_consumer_occurrence_ids'] = [v for v in record['required_consumer_occurrence_ids'] if v != occurrence]
    if mutation in ('missing_policy', 'missing_ledger'):
        edge('gate-policy' if mutation == 'missing_policy' else 'quality-ledger-final', ('release_grade_recorded_path', 21), False)
    elif mutation in ('pre_ledger_alias', 'composed_ledger_alias'):
        edge('quality-ledger-final', ('release_grade_recorded_path', 21), False)
        edge('quality-ledger-pre-authority' if mutation == 'pre_ledger_alias' else 'release-decision-report', ('release_grade_recorded_path', 21), True)
    elif mutation in ('source_argv_input', 'self_read'):
        edge('effective-required-argument-list' if mutation == 'source_argv_input' else 'artifact-provenance-binding', ('release_grade_recorded_path', 21), True)
    elif mutation == 'package_download_reader':
        edge('artifact-provenance-binding', ('assemble_release_grade_reference_package', 4), True)
    elif mutation.startswith('missing_') and mutation != 'missing_role':
        key = {
            'missing_attestation_hash': ('attest_release_grade_artifact_binding', 1),
            'missing_attestation_action': ('attest_release_grade_artifact_binding', 2),
            'missing_package_copy': ('assemble_release_grade_reference_package', 5),
            'missing_postcondition_hash': ('release_grade_recorded_path', 26),
            'missing_secondary_upload': ('release_grade_recorded_path', 33),
            'missing_package_json_reader': ('verify_release_grade_reference_package', 7),
        }[mutation]
        edge('artifact-provenance-binding', key, False)
    elif mutation == 'publisher_as_producer':
        r21['output_state_ids'] = []
        steps[('release_grade_recorded_path', 29)]['output_state_ids'] = [sid]
        row['producer_occurrence_id'] = steps[('release_grade_recorded_path', 29)]['occurrence_id']
    elif mutation == 'wrong_locator': row['path_or_uri'] += '.wrong'
    elif mutation == 'optional': row['required'] = False
    elif mutation == 'metadata_only': row['content_requirement'] = 'metadata_only'
    elif mutation == 'wrong_mutation_class': row['mutation_class'] = 'preservation_output'
    elif mutation == 'reverse_only': states['gate-policy']['required_consumer_occurrence_ids'].remove(r21['occurrence_id'])
    elif mutation == 'forward_only': r21['input_state_ids'].remove(states['gate-policy']['state_id'])
    elif mutation == 'missing_role':
        plan['state_templates'] = [s for s in plan['state_templates'] if s['state_id'] != sid]
        for step in steps.values():
            for key in ('input_state_ids', 'output_state_ids'): step[key] = [v for v in step[key] if v != sid]
    else: raise AssertionError(mutation)
    return plan


@pytest.mark.parametrize('mutation', PROVENANCE_MUTATIONS)
def test_provenance_equal_wrong_plans_fail_source_predicate(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_provenance_plan(source_fixture.plan, mutation)
    assert canonical(bad) == canonical(copy.deepcopy(bad))
    with pytest.raises(PLAN_CHECKER.PlanError, match='provenance_mapping_'):
        PLAN_CHECKER._verify_source_provenance_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_policy', 'missing_ledger', 'package_download_reader'])
def test_provenance_actual_constructors_common_error_is_not_accepted(source_fixture, recorded_source_objects, mutation):
    results = []
    for module in (BUILDER, PLAN_CHECKER):
        document = mapping_source_document()
        jobs, steps, _ = module._build_jobs(document)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        results.append(canonical(corrupt_provenance_plan(plan, mutation)))
    assert results[0] == results[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='provenance_mapping_'):
        PLAN_CHECKER._verify_source_provenance_equations(json.loads(results[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_policy', 'missing_ledger', 'package_download_reader', 'optional'])
def test_provenance_rehashed_forgery_fails_real_checker_cli(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_provenance_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'forged-provenance-plan.json'; path.write_bytes(raw)
    args = list(source_fixture.check_args)
    args[args.index('--plan') + 1] = path
    args[args.index('--expected-plan-sha256') + 1] = digest(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], args)
    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report['ok'] is False
    # Existing ledger/recorded predicates may reject an overlapping forged
    # input first; it must still fail at a source-mapping boundary.
    assert any(v in report['error_code'] for v in ('provenance_mapping_', 'source_mapping_', 'recorded_mapping_'))


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', [
    'PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py',
    'PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py',
    '.github/workflows/pulse_ci.yml',
    'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py',
])
@pytest.mark.parametrize('mutation', ['missing', 'rehashed'])
def test_provenance_changed_semantic_source_never_inherits_old_mapping(source_fixture, recorded_source_objects, side, path, mutation):
    module, method = provenance_method(side)
    objects = dict(recorded_source_objects)
    if mutation == 'missing': del objects[path]
    else:
        previous = objects[path]; raw = previous.data + b'\n# not the reviewed semantic source\n'
        objects[path] = replace(previous, data=raw, blob_sha1=module._sha1_git_blob(raw))
    with pytest.raises(module.PlanError, match='provenance_mapping_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', ['ledger_version', 'verifier_target', 'publication_target',
                                     'attestation_hash', 'attestation_subject', 'package_transfer'])
def test_provenance_workflow_drift_requires_reviewed_profile(source_fixture, recorded_source_objects, side, mutation):
    doc = mapping_source_document(); rows = doc['jobs']['release_grade_recorded_path']['steps']
    if mutation == 'ledger_version': rows[20]['run'] = rows[20]['run'].replace('report_card.html', 'report_card.with_release_decision.html')
    elif mutation == 'verifier_target': rows[20]['run'] = rows[20]['run'].replace('--binding ', '--other-binding ')
    elif mutation == 'publication_target': rows[28]['with']['path'] += '.other'
    elif mutation == 'attestation_hash':
        step = doc['jobs']['attest_release_grade_artifact_binding']['steps'][0]
        step['run'] = step['run'].replace('sha256sum ', 'echo ')
    elif mutation == 'attestation_subject': doc['jobs']['attest_release_grade_artifact_binding']['steps'][1]['with']['subject-path'] += '.other'
    else:
        step = doc['jobs']['assemble_release_grade_reference_package']['steps'][3]
        step['run'] = step['run'].replace('--dir "${ARTIFACT_BINDING_DIR}"', '--dir "${RECORDED_PATH_DIR}"')
    module, method = provenance_method(side)
    with pytest.raises(module.PlanError, match='provenance_mapping_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('tamper_role', [None, 'final-status', 'gate-policy', 'quality-ledger-final', 'release-decision', 'release-authority-manifest'])
def test_provenance_exact_r21_shell_uses_five_synthetic_contents(source_fixture, tmp_path, tamper_role):
    root = tmp_path / 'synthetic-r21'; pack = root / 'PULSE_safe_pack_v0'
    (pack / 'tools').mkdir(parents=True); (pack / 'artifacts').mkdir()
    for relative in (BUILDER._PROVENANCE_BUILD, BUILDER._PROVENANCE_VERIFY):
        (root / relative).write_bytes((source_fixture.root / relative).read_bytes())
    files = {
        'final-status': ('PULSE_safe_pack_v0/artifacts/status.json', canonical({
            'metrics': {'run_id': '73001', 'run_key': 'GITHUB_RUN_ID=73001|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=synthetic',
                        'git_sha': source_fixture.sha, 'run_mode': 'prod'},
            'gates': {'example_required': True, 'example_release': True}})),
        'gate-policy': ('pulse_gate_policy_v0.yml', b'gates:\n  required: [example_required]\n  release_required: [example_release]\n'),
        'quality-ledger-final': ('PULSE_safe_pack_v0/artifacts/report_card.html', b'<p>synthetic final ledger</p>\n'),
        'release-decision': ('PULSE_safe_pack_v0/artifacts/release_decision_v0.json', b'{"label":"PROD-PASS"}\n'),
        'release-authority-manifest': ('PULSE_safe_pack_v0/artifacts/release_authority_v0.json', b'{"example":"authority"}\n'),
    }
    for relative, raw in files.values(): (root / relative).write_bytes(raw)
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'PACK_DIR': 'PULSE_safe_pack_v0', 'GITHUB_WORKSPACE': str(root), 'HOME': str(tmp_path)}
    body = mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][20]['run']
    # Exact source shell, actual existing tools, only synthetic local inputs.
    result = subprocess.run(['/bin/bash', '-c', body], cwd=root, env=env,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    binding_path = root / 'PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json'
    binding = json.loads(binding_path.read_bytes())
    bound = [row for row in binding['binding_subjects'] if not row['path'].startswith('inline:')]
    assert len(bound) == 5
    for row in bound:
        p = Path(row['path']); p = p if p.is_absolute() else root / p
        assert row['sha256'] == digest(p.read_bytes())
    for relative, raw in files.values(): assert (root / relative).read_bytes() == raw
    if tamper_role is not None:
        relative, raw = files[tamper_role]; (root / relative).write_bytes(raw + b'changed\n')
        bad = subprocess.run([sys.executable, '-I', '-B', str(root / BUILDER._PROVENANCE_VERIFY),
                              '--binding', str(binding_path)], cwd=root, env=env,
                             stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        assert bad.returncode == 1 and b'MISMATCH:' in bad.stderr


def test_provenance_mapping_keeps_full_role_extent_and_unaccepted_evidence(source_fixture):
    plan = source_fixture.plan
    assert len(plan['state_templates']) == 62 and len(plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    packet = runtime_projection_example(source_fixture)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(plan, packet, {})
    assert 'evidence_profile' not in plan
    assert plan['authority_boundary']['authority_effect'] == 'none'


# Baseline / self-contained floor: source-declared reads, not hosted receipts.
FLOOR_ROLE_INPUTS = [
    ('--status', 'pre-materialization-status'),
    ('--policy', 'gate-policy'),
    ('--registry', 'gate-registry'),
    ('--required-gate-evidence', 'required-gate-evidence'),
]
FLOOR_LOCAL_EQUATIONS = [
    (14, ['pre-materialization-status'], ['status-baseline']),
    (15, ['status-baseline'], []),
    (16, ['pre-materialization-status'], []),
    (18, ['gate-policy', 'gate-registry', 'pre-materialization-status',
          'required-gate-evidence'], ['self-contained-evidence-floor']),
    (19, ['self-contained-evidence-floor'], []),
]
FLOOR_PLAN_MUTATIONS = [
    'missing_status', 'missing_policy', 'missing_registry', 'missing_evidence',
    'final_status_alias', 'baseline_as_floor_status', 'missing_copy_input',
    'final_status_copy_input', 'guard_reads_final', 'baseline_guard_reads_status',
    'floor_self_read', 'missing_upload_input', 'publisher_as_producer',
    'status_producer_as_copy', 'duplicate_writer', 'wrong_floor_locator',
    'wrong_baseline_locator', 'optional_floor', 'metadata_floor',
    'optional_baseline', 'metadata_baseline', 'wrong_mutation_class',
    'reverse_only', 'forward_only', 'missing_floor', 'missing_baseline',
]


def floor_source_method(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    return module, (module._baseline_floor_source_projection if side == 'builder'
                    else module._source_baseline_floor_expectations)


@pytest.mark.parametrize('number,inputs,outputs', FLOOR_LOCAL_EQUATIONS)
def test_floor_baseline_selected_local_equations_match_source_roles(source_fixture, number, inputs, outputs):
    states, steps = provenance_rows(source_fixture.plan)
    step = steps[('pulse', number)]
    assert step['input_state_ids'] == sorted('state:step5c:' + v for v in inputs)
    assert step['output_state_ids'] == sorted('state:step5c:' + v for v in outputs)
    reverse = sorted(row['state_id'] for row in states.values()
                     if step['occurrence_id'] in row['required_consumer_occurrence_ids'])
    assert reverse == step['input_state_ids']


@pytest.mark.parametrize('flag,role', FLOOR_ROLE_INPUTS)
def test_floor_each_actual_file_loader_has_a_selected_input(source_fixture, flag, role):
    body = mapping_source_document()['jobs']['pulse']['steps'][17]['run']
    command = next(shlex.split(line) for line in body.replace('\\\n', ' ').splitlines()
                   if 'python "${PACK_DIR}/tools/build_self_contained_pulse_evidence_floor_v0.py"' in line)
    path = command[command.index(flag) + 1].replace('${PACK_DIR}/', 'PULSE_safe_pack_v0/')
    rows, steps = provenance_rows(source_fixture.plan)
    expected = path + ('#pre-release-required-materialization' if flag == '--status' else '')
    assert rows[role]['path_or_uri'] == expected
    assert rows[role]['state_id'] in steps[('pulse', 18)]['input_state_ids']
    assert steps[('pulse', 18)]['occurrence_id'] in rows[role]['required_consumer_occurrence_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_floor_source_projection_separates_versions_and_pins_dependency(source_fixture, recorded_source_objects, side):
    module, method = floor_source_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    other = floor_source_method('checker' if side == 'builder' else 'builder')[1]
    assert facts == other(mapping_source_document(), recorded_source_objects)
    assert set(facts) == {'locators', 'producers', 'steps'}
    assert len(facts['locators']) == 6 and len(facts['steps']) == 5
    assert facts['producers'] == {
        'status-baseline': module._step_id('pulse', 14),
        'self-contained-evidence-floor': module._step_id('pulse', 18),
    }
    inventory = {row['path']: row for row in source_fixture.plan['source_inventory']}
    dep = inventory[module._FLOOR_BUILD_PATH]
    assert dep['git_blob_sha1'] == '2f7776e609ef7ef2fb8fcd40d5ee30e46ed46f6a'
    assert dep['sha256'] == digest((ROOT / module._FLOOR_BUILD_PATH).read_bytes())
    states, steps = provenance_rows(source_fixture.plan)
    assert states['pre-materialization-status']['producer_occurrence_id'] == steps[('pulse', 13)]['occurrence_id']
    assert states['final-status']['producer_occurrence_id'] == steps[('release_grade_recorded_path', 9)]['occurrence_id']
    for number in (14, 16, 18):
        assert states['final-status']['state_id'] not in steps[('pulse', number)]['input_state_ids']
    # Hashing the newly written floor within P18 is not a fabricated extra
    # source-declared occurrence or a step-level self dependency.
    assert states['self-contained-evidence-floor']['state_id'] not in steps[('pulse', 18)]['input_state_ids']


def corrupt_floor_plan(original, mutation):
    plan = copy.deepcopy(original)
    rows, steps = provenance_rows(plan)
    def edge(role, ordinal, add):
        row = rows[role]; step = steps[('pulse', ordinal)]
        sid, oid = row['state_id'], step['occurrence_id']
        if add:
            step['input_state_ids'] = sorted(set(step['input_state_ids']) | {sid})
            row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {oid})
        else:
            step['input_state_ids'] = [x for x in step['input_state_ids'] if x != sid]
            row['required_consumer_occurrence_ids'] = [x for x in row['required_consumer_occurrence_ids'] if x != oid]
    missing = {'missing_status': 'pre-materialization-status', 'missing_policy': 'gate-policy',
               'missing_registry': 'gate-registry', 'missing_evidence': 'required-gate-evidence'}
    if mutation in missing:
        edge(missing[mutation], 18, False)
    elif mutation in ('final_status_alias', 'baseline_as_floor_status'):
        edge('pre-materialization-status', 18, False)
        edge('final-status' if mutation == 'final_status_alias' else 'status-baseline', 18, True)
    elif mutation in ('missing_copy_input', 'final_status_copy_input'):
        edge('pre-materialization-status', 14, False)
        if mutation == 'final_status_copy_input': edge('final-status', 14, True)
    elif mutation == 'guard_reads_final':
        edge('pre-materialization-status', 16, False); edge('final-status', 16, True)
    elif mutation == 'baseline_guard_reads_status':
        edge('status-baseline', 15, False); edge('pre-materialization-status', 15, True)
    elif mutation == 'floor_self_read': edge('self-contained-evidence-floor', 18, True)
    elif mutation == 'missing_upload_input': edge('self-contained-evidence-floor', 19, False)
    elif mutation in ('publisher_as_producer', 'status_producer_as_copy'):
        role, old, new = ('self-contained-evidence-floor', 18, 19) if mutation == 'publisher_as_producer' else ('status-baseline', 14, 13)
        sid = rows[role]['state_id']
        steps[('pulse', old)]['output_state_ids'].remove(sid)
        steps[('pulse', new)]['output_state_ids'].append(sid)
        steps[('pulse', new)]['output_state_ids'].sort()
        rows[role]['producer_occurrence_id'] = steps[('pulse', new)]['occurrence_id']
    elif mutation == 'duplicate_writer':
        steps[('pulse', 17)]['output_state_ids'].append(rows['self-contained-evidence-floor']['state_id'])
    elif mutation.startswith('wrong_') and mutation.endswith('_locator'):
        role = 'self-contained-evidence-floor' if mutation == 'wrong_floor_locator' else 'status-baseline'
        rows[role]['path_or_uri'] += '.wrong'
    elif mutation.startswith(('optional_', 'metadata_')):
        role = 'self-contained-evidence-floor' if mutation.endswith('_floor') else 'status-baseline'
        if mutation.startswith('optional_'): rows[role]['required'] = False
        else: rows[role]['content_requirement'] = 'metadata_only'
    elif mutation == 'wrong_mutation_class': rows['self-contained-evidence-floor']['mutation_class'] = 'preservation_output'
    elif mutation == 'reverse_only': rows['gate-registry']['required_consumer_occurrence_ids'].remove(steps[('pulse', 18)]['occurrence_id'])
    elif mutation == 'forward_only': steps[('pulse', 18)]['input_state_ids'].remove(rows['gate-registry']['state_id'])
    elif mutation in ('missing_floor', 'missing_baseline'):
        sid = rows['self-contained-evidence-floor' if mutation == 'missing_floor' else 'status-baseline']['state_id']
        plan['state_templates'] = [x for x in plan['state_templates'] if x['state_id'] != sid]
        for step in steps.values():
            for key in ('input_state_ids', 'output_state_ids'):
                step[key] = [x for x in step[key] if x != sid]
    else: raise AssertionError(mutation)
    return plan


@pytest.mark.parametrize('mutation', FLOOR_PLAN_MUTATIONS)
def test_floor_coordinated_mapping_tamper_fails_source_predicate(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_floor_plan(source_fixture.plan, mutation)
    assert canonical(bad) == canonical(copy.deepcopy(bad))
    with pytest.raises(PLAN_CHECKER.PlanError, match='floor_mapping_'):
        PLAN_CHECKER._verify_source_baseline_floor_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_policy', 'final_status_alias', 'publisher_as_producer'])
def test_floor_actual_constructors_shared_wrong_answer_is_rejected(source_fixture, recorded_source_objects, mutation):
    results = []
    for module in (BUILDER, PLAN_CHECKER):
        doc = mapping_source_document(); jobs, steps, _ = module._build_jobs(doc)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        results.append(canonical(corrupt_floor_plan(plan, mutation)))
    assert results[0] == results[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='floor_mapping_'):
        PLAN_CHECKER._verify_source_baseline_floor_equations(json.loads(results[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_registry', 'missing_copy_input', 'publisher_as_producer', 'metadata_floor'])
def test_floor_rehashed_schema_valid_forgery_fails_real_checker_cli(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_floor_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'forged-floor-plan.json'; path.write_bytes(raw)
    args = list(source_fixture.check_args)
    args[args.index('--plan') + 1] = path
    args[args.index('--expected-plan-sha256') + 1] = digest(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], args)
    assert result.returncode != 0
    report = json.loads(result.stdout)
    # The full pre-status reader closure is checked by the recorded predicate
    # first; the other three forgeries reach the local floor predicate.
    expected_error = {
        'missing_registry': 'floor_mapping_step_io_mismatch',
        'missing_copy_input': 'recorded_mapping_new_role_consumer_mismatch',
        'publisher_as_producer': 'floor_mapping_producer_mismatch',
        'metadata_floor': 'floor_mapping_requirement_mismatch',
    }[mutation]
    assert report['ok'] is False and report['error_code'] == expected_error


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', [
    '.github/workflows/pulse_ci.yml',
    'PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py',
    'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py',
    'tools/validate_status_schema.py',
])
@pytest.mark.parametrize('mutation', ['missing', 'rehashed'])
def test_floor_semantic_source_drift_cannot_inherit_old_equations(source_fixture, recorded_source_objects, side, path, mutation):
    module, method = floor_source_method(side); sources = dict(recorded_source_objects)
    if mutation == 'missing': del sources[path]
    else:
        old = sources[path]; raw = old.data + b'\n# different reviewed source required\n'
        sources[path] = replace(old, data=raw, blob_sha1=module._sha1_git_blob(raw))
    with pytest.raises(module.PlanError, match='floor_mapping_source_'):
        method(mapping_source_document(), sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('mutation', ['copy_target', 'schema_target', 'status_guard', 'floor_status', 'floor_policy', 'floor_registry', 'floor_evidence', 'upload_target'])
def test_floor_changed_workflow_is_not_silently_adapted(source_fixture, recorded_source_objects, side, mutation):
    doc = mapping_source_document(); rows = doc['jobs']['pulse']['steps']
    if mutation == 'copy_target': rows[13]['run'] = rows[13]['run'].replace('status_baseline.json', 'wrong_baseline.json')
    elif mutation == 'schema_target': rows[14]['run'] = rows[14]['run'].replace('status_baseline.json', 'status.json')
    elif mutation == 'status_guard': rows[15]['run'] = rows[15]['run'].replace('status.json', 'status_baseline.json')
    elif mutation == 'upload_target': rows[18]['with']['path'] += '.wrong'
    else:
        old, new = {
            'floor_status': ('--status "${PACK_DIR}/artifacts/status.json"', '--status "${PACK_DIR}/artifacts/status_baseline.json"'),
            'floor_policy': ('pulse_gate_policy_v0.yml', 'wrong_policy.yml'),
            'floor_registry': ('pulse_gate_registry_v0.yml', 'wrong_registry.yml'),
            'floor_evidence': ('required_gate_evidence_v0.json', 'wrong_evidence.json'),
        }[mutation]
        assert old in rows[17]['run']; rows[17]['run'] = rows[17]['run'].replace(old, new)
    module, method = floor_source_method(side)
    with pytest.raises(module.PlanError, match='floor_mapping_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('fault', [None, 'status_false', 'evidence_run', 'registry_missing', 'policy_missing', 'baseline_only_changed'])
def test_floor_actual_shell_reads_current_pre_materialization_files_only(source_fixture, tmp_path, fault):
    root = tmp_path / 'synthetic-floor'; pack = root / 'PULSE_safe_pack_v0'
    (pack / 'tools').mkdir(parents=True); (pack / 'artifacts').mkdir()
    dep = BUILDER._FLOOR_BUILD_PATH
    (root / dep).write_bytes((ROOT / dep).read_bytes())
    run_key = 'GITHUB_RUN_ID=73|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
    status = {'gates': {'example_required': True}, 'metrics': {
        'git_sha': source_fixture.sha, 'run_key': run_key, 'run_mode': 'prod'}}
    evidence = {'schema_version': 'required_gate_evidence_v0',
                'run_identity': {'git_sha': source_fixture.sha, 'run_key': run_key},
                'gates': {'example_required': {'value': True, 'status': 'passed', 'diagnostics': []}}}
    files = {
        'status': ('PULSE_safe_pack_v0/artifacts/status.json', canonical(status)),
        'gate_policy': ('pulse_gate_policy_v0.yml', b'gates:\n  required: [example_required]\n'),
        'gate_registry': ('pulse_gate_registry_v0.yml', b'gates:\n  example_required: {}\n'),
        'required_gate_evidence': ('PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json', canonical(evidence)),
    }
    for relative, raw in files.values(): (root / relative).write_bytes(raw)
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'PACK_DIR': 'PULSE_safe_pack_v0', 'GITHUB_WORKSPACE': str(root), 'HOME': str(tmp_path),
           'GITHUB_REPOSITORY': 'example/step5c', 'GITHUB_SHA': source_fixture.sha,
           'GITHUB_WORKFLOW_REF': 'example/step5c/.github/workflows/pulse_ci.yml@refs/heads/main',
           'PULSE_RUN_KEY': run_key, 'PULSE_CREATED_UTC': '2020-01-01T00:00:00Z'}
    rows = mapping_source_document()['jobs']['pulse']['steps']
    # Resolve only this literal Actions expression into its fixed declared pack
    # directory. Both shell snippets execute only under this synthetic root.
    copy_body = rows[13]['run'].replace('${{ env.PACK_DIR }}', 'PULSE_safe_pack_v0')
    copy_result = subprocess.run(['/bin/bash', '-c', copy_body], cwd=root, env=env,
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    assert copy_result.returncode == 0, copy_result.stderr
    baseline = pack / 'artifacts/status_baseline.json'
    assert baseline.read_bytes() == files['status'][1]
    if fault == 'status_false':
        status['gates']['example_required'] = False
        (root / files['status'][0]).write_bytes(canonical(status))
    elif fault == 'evidence_run':
        evidence['run_identity']['run_key'] += '-other'
        (root / files['required_gate_evidence'][0]).write_bytes(canonical(evidence))
    elif fault == 'registry_missing': (root / files['gate_registry'][0]).write_bytes(b'gates:\n  another_gate: {}\n')
    elif fault == 'policy_missing': (root / files['gate_policy'][0]).write_bytes(b'gates:\n  release_required: [example_required]\n')
    elif fault == 'baseline_only_changed': baseline.write_bytes(b'not the floor input\n')
    before = {relative: (root / relative).read_bytes() for relative, _ in files.values()}
    result = subprocess.run(['/bin/bash', '-c', rows[17]['run']], cwd=root, env=env,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    out = pack / 'artifacts/self_contained_pulse_evidence_floor_v0.json'
    if fault not in (None, 'baseline_only_changed'):
        assert result.returncode != 0 and b'ERROR:' in result.stderr
        assert not out.exists()
    else:
        assert result.returncode == 0, result.stderr
        floor = json.loads(out.read_bytes())
        assert {item['role'] for item in floor['artifacts']} == set(files)
        for item in floor['artifacts']:
            relative, _ = files[item['role']]
            assert item['path'] == relative
            assert item['sha256'] == digest((root / relative).read_bytes())
        assert floor['authority_boundary']['creates_release_authority'] is False
        assert floor['authority_boundary']['materializes_status'] is False
    assert before == {relative: (root / relative).read_bytes() for relative in before}


def test_floor_local_mapping_preserves_global_extent_and_runtime_acceptance_stop(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    rows, steps = provenance_rows(source_fixture.plan)
    assert rows['status-baseline']['state_id'] != rows['pre-materialization-status']['state_id']
    assert rows['status-baseline']['state_id'] != rows['final-status']['state_id']
    assert 'evidence_profile' not in source_fixture.plan
    packet = runtime_projection_example(source_fixture)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, packet, {})
    assert source_fixture.plan['authority_boundary']['authority_effect'] == 'none'



@pytest.mark.parametrize('ordinal', [13, 17, 19])
def test_floor_recorded_reader_closure_rejects_unreviewed_additions(source_fixture, recorded_source_objects, ordinal):
    bad = copy.deepcopy(source_fixture.plan)
    rows, steps = provenance_rows(bad)
    row, step = rows['pre-materialization-status'], steps[('pulse', ordinal)]
    assert row['state_id'] not in step['input_state_ids']
    step['input_state_ids'] = sorted(step['input_state_ids'] + [row['state_id']])
    row['required_consumer_occurrence_ids'] = sorted(row['required_consumer_occurrence_ids'] + [step['occurrence_id']])
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_mapping_new_role_consumer_mismatch'):
        PLAN_CHECKER._verify_source_recorded_equations(bad, mapping_source_document(), recorded_source_objects)


# ---------------------------------------------------------------------------
# Reviewed smoke-job budget amendment. Only the job time budget changes;
# exact source identity, complete execution and failure propagation stay strict.
# ---------------------------------------------------------------------------
def test_smoke_budget_is_the_only_subject_workflow_byte_change():
    raw = (ROOT / BUILDER.SUBJECT_WORKFLOW_PATH).read_bytes()
    before_job, job_bytes = raw.split(b'  tools-tests:\n')
    assert job_bytes.count(b'    timeout-minutes: 30\n') == 1
    restored = before_job + b'  tools-tests:\n' + job_bytes.replace(
        b'    timeout-minutes: 30\n', b'    timeout-minutes: 15\n', 1)
    old_blob = hashlib.sha1(b'blob ' + str(len(restored)).encode() + b'\0' + restored).hexdigest()
    assert old_blob == 'adae42c8e9777d357ab5400ced5765de7059ed1e'
    job = yaml.load(raw, Loader=yaml.BaseLoader)['jobs']['tools-tests']
    assert job['timeout-minutes'] == '30'
    assert 'continue-on-error' not in job
    assert all('continue-on-error' not in step for step in job['steps'])


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_smoke_budget_all_workflow_pins_require_the_same_reviewed_bytes(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    path = module.SUBJECT_WORKFLOW_PATH
    data = (ROOT / path).read_bytes()
    current = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert current == 'ad1f165ad695c65827c590cbef9466e300d6b6e9'
    assert module.EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1 == current
    for values in vars(module).values():
        if isinstance(values, dict) and path in values:
            assert values[path] == current


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('minutes', [15, 31])
def test_smoke_budget_stale_or_unreviewed_rehashed_sources_fail_closed(
    source_fixture, monkeypatch, side, minutes,
):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    read = module._read_git_object
    def changed(*args, **kwargs):
        obj = read(*args, **kwargs)
        if kwargs.get('path') == module.SUBJECT_WORKFLOW_PATH:
            prefix, job = obj.data.split(b'  tools-tests:\n')
            data = prefix + b'  tools-tests:\n' + job.replace(
                b'    timeout-minutes: 30\n',
                ('    timeout-minutes: %s\n' % minutes).encode(), 1)
            assert data != obj.data
            new_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            obj = replace(obj, data=data, blob_sha1=new_blob)
        return obj
    monkeypatch.setattr(module, '_read_git_object', changed)
    with pytest.raises(module.PlanError, match='reviewed_source_profile_mismatch'):
        module._load_sources(source_fixture.root, source_fixture.sha)


@pytest.mark.parametrize('first_exit', [0, 7])
def test_smoke_budget_unchanged_runner_finishes_or_propagates_failure(tmp_path, first_exit):
    workflow = yaml.load((ROOT / BUILDER.SUBJECT_WORKFLOW_PATH).read_bytes(), Loader=yaml.BaseLoader)
    step = next(s for s in workflow['jobs']['tools-tests']['steps']
                if s['name'].strip() == 'Run exporter + release-authority smoke tests')
    (tmp_path / 'ci').mkdir()
    (tmp_path / 'ci/tools-tests.list').write_text('first.py\nsecond.py\n')
    (tmp_path / 'first.py').write_text('raise SystemExit(%d)\n' % first_exit)
    (tmp_path / 'second.py').write_text("from pathlib import Path\nPath('second-ran').write_text('yes')\n")
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin',
           'HOME': str(tmp_path), 'LANG': 'C', 'LC_ALL': 'C'}
    result = subprocess.run(['bash', '--noprofile', '--norc', '-c', step['run']],
                            cwd=tmp_path, env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=20)
    assert result.returncode == first_exit, result.stderr.decode(errors='replace')
    assert (tmp_path / 'second-ran').exists() is (first_exit == 0)
    assert (b'Exporter + release-authority smoke tests OK\n' in result.stdout) is (first_exit == 0)


def test_smoke_budget_new_workflow_is_preserved_without_evidence_promotion(source_fixture):
    data = (ROOT / BUILDER.SUBJECT_WORKFLOW_PATH).read_bytes()
    row = next(row for row in source_fixture.plan['source_inventory']
               if row['path'] == BUILDER.SUBJECT_WORKFLOW_PATH)
    assert row['sha256'] == digest(data)
    assert prepared_fixture_members(source_fixture)['sources/' + BUILDER.SUBJECT_WORKFLOW_PATH] == data
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})

# ---------------------------------------------------------------------------
# LlamaGuard current/attested preservation mapping. These are source and local
# copy/hash regressions, not live inference or verified attestation evidence.
# ---------------------------------------------------------------------------
LG_PRESERVATION_CURRENT = ('llamaguard-raw-evidence', 'llamaguard-evaluator-manifest', 'llamaguard-summary')
LG_PRESERVATION_ATTESTED = LG_PRESERVATION_CURRENT + ('llamaguard-attestation-bundle', 'llamaguard-attestation-envelope', 'llamaguard-attestation-verifier')
LG_PRESERVATION_STEPS = (
    ('pulse', 24, LG_PRESERVATION_CURRENT),
    ('attest_llamaguard_current_run_summary', 4, LG_PRESERVATION_CURRENT),
    ('attest_llamaguard_current_run_summary', 8, LG_PRESERVATION_ATTESTED),
    ('release_grade_recorded_path', 5, LG_PRESERVATION_ATTESTED),
)
LG_PRESERVATION_MUTATIONS = (
    'missing_current_raw', 'missing_download_summary', 'missing_attested_raw', 'missing_restore_manifest',
    'policy_reader', 'threshold_upload', 'prearchive_alias', 'signed_receipt_alias',
    'publisher_origin', 'restore_origin', 'duplicate_writer', 'wrong_path', 'optional',
    'metadata_only', 'non_authority', 'mutation_class', 'missing_role', 'reverse_only',
    'forward_only', 'unrelated_reverse_reader',
)


def lg_preservation_method(side):
    if side == 'builder': return BUILDER, BUILDER._llamaguard_preservation_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_llamaguard_preservation_expectations


@pytest.mark.parametrize('job,ordinal,role', [(j, n, role) for j, n, roles in LG_PRESERVATION_STEPS for role in roles])
def test_lg_preservation_source_selected_content_has_reciprocal_step_input(source_fixture, job, ordinal, role):
    rows, steps = provenance_rows(source_fixture.plan)
    row, step = rows[role], steps[(job, ordinal)]
    # Oracle is the literal workflow upload path, not either plan constructor.
    publisher = ('pulse', 24) if len(next(r for j, n, r in LG_PRESERVATION_STEPS if (j, n) == (job, ordinal))) == 3 else ('attest_llamaguard_current_run_summary', 8)
    raw = mapping_source_document()['jobs'][publisher[0]]['steps'][publisher[1] - 1]
    assert row['path_or_uri'] in raw['with']['path'].splitlines()
    assert row['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in row['required_consumer_occurrence_ids']
    assert step['output_state_ids'] == []


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_preservation_projection_closes_copy_hash_lists_not_attestation_proof(source_fixture, recorded_source_objects, side):
    _, method = lg_preservation_method(side)
    doc = mapping_source_document(); facts = method(doc, recorded_source_objects)
    assert len(facts['locators']) == 6 and len(facts['steps']) == 4 and len(facts['handoffs']) == 2
    for handoff, (j, n, roles) in zip(facts['handoffs'], (LG_PRESERVATION_STEPS[0], LG_PRESERVATION_STEPS[2])):
        paths = doc['jobs'][j]['steps'][n - 1]['with']['path'].splitlines()
        assert handoff['upload_paths'] == handoff['restore_paths'] == handoff['hash_paths'] == paths
        assert len(paths) == len(roles)
        assert handoff['archive_state_modeled'] is False
    assert [x['artifact_name_template'] for x in facts['handoffs']] == [
        'llamaguard-current-run-{workflow_run_id}-1', 'llamaguard-attested-current-run-{workflow_run_id}-1']
    assert [x['requires_nonempty'] for x in facts['handoffs']] == [False, True]
    assert set(facts) == {'locators', 'origins', 'steps', 'handoffs'}
    assert facts['origins']['llamaguard-attestation-bundle'] == BUILDER._step_id('attest_llamaguard_current_run_summary', 5)
    # These artifact names are source selectors; neither an artifact ID nor a
    # captured signed receipt/cryptographic success is manufactured here.
    assert 'artifact_id' not in repr(facts) and 'signature_verified' not in repr(facts)


def test_lg_preservation_independent_checker_uses_hash_oracle_without_builder(source_fixture, recorded_source_objects):
    doc = mapping_source_document()
    built = BUILDER._llamaguard_preservation_source_projection(doc, recorded_source_objects)
    with patch.object(BUILDER, '_llamaguard_preservation_source_projection', side_effect=AssertionError('builder prohibited')):
        checked = PLAN_CHECKER._source_llamaguard_preservation_expectations(doc, recorded_source_objects)
        PLAN_CHECKER._verify_source_llamaguard_preservation_equations(source_fixture.plan, doc, recorded_source_objects)
    assert canonical(built) == canonical(checked)
    code = inspect.getsource(PLAN_CHECKER._source_llamaguard_preservation_expectations)
    assert 'for artifact in ' in code and '_llamaguard_preservation_source_projection(' not in code


def corrupt_lg_preservation_plan(original, mutation):
    plan = copy.deepcopy(original); rows, steps = provenance_rows(plan)
    current = ('pulse', 24); download = ('attest_llamaguard_current_run_summary', 4)
    attested = ('attest_llamaguard_current_run_summary', 8); restore = ('release_grade_recorded_path', 5)
    def edge(role, target, add):
        row, step = rows[role], steps[target]; sid, oid = row['state_id'], step['occurrence_id']
        if add:
            step['input_state_ids'] = sorted(set(step['input_state_ids']) | {sid})
            row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {oid})
        else:
            step['input_state_ids'] = [v for v in step['input_state_ids'] if v != sid]
            row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v != oid]
    omissions = {'missing_current_raw': ('llamaguard-raw-evidence', current),
                 'missing_download_summary': ('llamaguard-summary', download),
                 'missing_attested_raw': ('llamaguard-raw-evidence', attested),
                 'missing_restore_manifest': ('llamaguard-evaluator-manifest', restore)}
    if mutation in omissions: edge(*omissions[mutation], False)
    elif mutation == 'policy_reader': edge('external-signer-policy', restore, True)
    elif mutation == 'threshold_upload': edge('threshold-policy', current, True)
    elif mutation == 'prearchive_alias': edge('pre-attestation-pulse-artifacts', download, True)
    elif mutation == 'signed_receipt_alias': edge('artifact-binding-attestation', attested, True)
    elif mutation in ('publisher_origin', 'restore_origin'):
        row = rows['llamaguard-attestation-verifier']; sid = row['state_id']
        for step in steps.values(): step['output_state_ids'] = [v for v in step['output_state_ids'] if v != sid]
        target = steps[attested if mutation == 'publisher_origin' else restore]
        target['output_state_ids'] = sorted([*target['output_state_ids'], sid])
        row['producer_occurrence_id'] = target['occurrence_id']
    elif mutation == 'duplicate_writer': steps[restore]['output_state_ids'].append(rows['llamaguard-attestation-verifier']['state_id'])
    elif mutation == 'wrong_path': rows['llamaguard-attestation-verifier']['path_or_uri'] += '.other'
    elif mutation == 'optional': rows['llamaguard-attestation-verifier']['required'] = False
    elif mutation == 'metadata_only': rows['llamaguard-attestation-verifier']['content_requirement'] = 'metadata_only'
    elif mutation == 'non_authority': rows['llamaguard-attestation-verifier']['authority_bearing'] = False
    elif mutation == 'mutation_class': rows['llamaguard-attestation-verifier']['mutation_class'] = 'preservation_output'
    elif mutation == 'missing_role':
        sid = rows['llamaguard-attestation-verifier']['state_id']
        plan['state_templates'] = [v for v in plan['state_templates'] if v['state_id'] != sid]
        for step in steps.values():
            for key in ('input_state_ids', 'output_state_ids'): step[key] = [v for v in step[key] if v != sid]
    elif mutation == 'reverse_only': rows['llamaguard-raw-evidence']['required_consumer_occurrence_ids'].remove(steps[restore]['occurrence_id'])
    elif mutation == 'forward_only': steps[restore]['input_state_ids'].remove(rows['llamaguard-raw-evidence']['state_id'])
    elif mutation == 'unrelated_reverse_reader': rows['final-status']['required_consumer_occurrence_ids'].append(steps[restore]['occurrence_id'])
    else: raise AssertionError(mutation)
    return plan


@pytest.mark.parametrize('mutation', LG_PRESERVATION_MUTATIONS)
def test_lg_preservation_source_predicate_rejects_coordinated_wrong_mapping(source_fixture, recorded_source_objects, mutation):
    bad = corrupt_lg_preservation_plan(source_fixture.plan, mutation)
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_preservation_'):
        PLAN_CHECKER._verify_source_llamaguard_preservation_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_restore_manifest', 'policy_reader', 'publisher_origin'])
def test_lg_preservation_equal_constructor_errors_are_not_source_proof(source_fixture, recorded_source_objects, mutation):
    results = []
    for module in (BUILDER, PLAN_CHECKER):
        doc = mapping_source_document(); jobs, steps, _ = module._build_jobs(doc)
        states = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'], plan['state_templates'] = jobs, states
        results.append(canonical(corrupt_lg_preservation_plan(plan, mutation)))
    assert results[0] == results[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_preservation_'):
        PLAN_CHECKER._verify_source_llamaguard_preservation_equations(json.loads(results[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['missing_current_raw', 'policy_reader', 'publisher_origin', 'metadata_only'])
def test_lg_preservation_rehashed_schema_valid_plan_fails_isolated_checker(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_lg_preservation_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'forged-lg-preservation.json'; path.write_bytes(raw)
    args = list(source_fixture.check_args); args[args.index('--plan') + 1] = path
    args[args.index('--expected-plan-sha256') + 1] = digest(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], args)
    report = json.loads(result.stdout)
    expected = {'missing_current_raw': 'lg_preservation_step_io_mismatch',
                'policy_reader': 'lg_preservation_step_io_mismatch',
                'publisher_origin': 'lg_preservation_origin_mismatch',
                'metadata_only': 'lg_preservation_requirement_mismatch'}
    assert result.returncode != 0 and report['ok'] is False and report['error_code'] == expected[mutation]


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'rehashed'])
def test_lg_preservation_new_source_identity_does_not_inherit_review(source_fixture, recorded_source_objects, side, fault):
    module, method = lg_preservation_method(side); sources = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del sources[path]
    else:
        obj = sources[path]; raw = obj.data + b'\n# different source\n'
        sources[path] = replace(obj, data=raw, blob_sha1=module._sha1_git_blob(raw))
    with pytest.raises(module.PlanError, match='lg_preservation_source_'):
        method(mapping_source_document(), sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['upload_omission', 'upload_duplicate', 'name', 'run', 'repository', 'copy_destination', 'hash', 'empty_check'])
def test_lg_preservation_changed_source_is_not_reinterpreted(source_fixture, recorded_source_objects, side, fault):
    doc = mapping_source_document(); upload = doc['jobs']['attest_llamaguard_current_run_summary']['steps'][7]
    reader = doc['jobs']['release_grade_recorded_path']['steps'][4]
    if fault == 'upload_omission': upload['with']['path'] = '\n'.join(upload['with']['path'].splitlines()[:-1])
    elif fault == 'upload_duplicate': upload['with']['path'] += upload['with']['path'].splitlines()[0] + '\n'
    elif fault == 'name': upload['with']['name'] += '-different'
    else:
        old, new = {'run': ('gh run download "${GITHUB_RUN_ID}"', 'gh run download "77"'),
                    'repository': ('--repo "${GITHUB_REPOSITORY}"', '--repo "example/other"'),
                    'copy_destination': ('cp "${src}" "${dst}"', 'cp "${src}" "${DOWNLOAD_DIR}/wrong"'),
                    'hash': ('sha256sum "${artifact}"', ':'),
                    'empty_check': (' || ! -s "${artifact}"', '')}[fault]
        assert old in reader['run']; reader['run'] = reader['run'].replace(old, new)
    module, method = lg_preservation_method(side)
    with pytest.raises(module.PlanError, match='lg_preservation_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_preservation_scoped_installation_keeps_every_outside_duty(source_fixture, recorded_source_objects, side):
    module, _ = lg_preservation_method(side); doc = mapping_source_document()
    _, previous_steps, _ = module._build_jobs(doc)
    with patch.object(module, '_install_llamaguard_preservation_projection', return_value=None):
        previous_states = module._build_states(previous_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    _, steps, _ = module._build_jobs(doc)
    states = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    owned = {steps[(j, n)]['occurrence_id'] for j, n, _ in LG_PRESERVATION_STEPS}
    assert len(states) == len(previous_states) == 62
    for old, new in zip(previous_states, states):
        old, new = copy.deepcopy(old), copy.deepcopy(new)
        for row in (old, new): row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v not in owned]
        assert old == new
    for key, step in steps.items():
        if step['occurrence_id'] not in owned: assert step == previous_steps[key]
    assert all(not steps[(j, n)]['output_state_ids'] for j, n, _ in LG_PRESERVATION_STEPS)
    # R5 copies and hashes artifacts; it is not the attestation policy verifier.
    assert 'state:step5c:external-signer-policy' not in steps[('release_grade_recorded_path', 5)]['input_state_ids']


@pytest.mark.parametrize('phase', ['current', 'attested'])
@pytest.mark.parametrize('fault', [None, 'missing', 'empty', 'symlink', 'download_failure'])
def test_lg_preservation_actual_copy_shell_is_bounded_local_evidence(source_fixture, tmp_path, phase, fault):
    root, incoming, runner, bindir = [tmp_path / v for v in ('workspace', 'incoming', 'runner', 'bin')]
    for directory in (root, incoming, runner, bindir): directory.mkdir()
    job, ordinal = ('attest_llamaguard_current_run_summary', 4) if phase == 'current' else ('release_grade_recorded_path', 5)
    publisher_job, publisher_n = ('pulse', 24) if phase == 'current' else ('attest_llamaguard_current_run_summary', 8)
    doc = mapping_source_document(); selected = doc['jobs'][publisher_job]['steps'][publisher_n - 1]['with']['path'].splitlines()
    payloads = {relative: ('synthetic opaque input: ' + relative + '\n').encode() for relative in selected}
    for relative, raw in payloads.items():
        p = incoming / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    # Alter the final selected file so a late failure exposes non-transactional
    # copies. Neither original shell is claimed to publish a valid capsule.
    last = incoming / selected[-1]
    if fault == 'missing': last.unlink()
    elif fault == 'empty': last.write_bytes(b''); payloads[selected[-1]] = b''
    elif fault == 'symlink':
        last.unlink(); target = tmp_path / 'outside'; target.write_bytes(b'not an artifact\n'); last.symlink_to(target)
    archive = 'llamaguard-current-run' if phase == 'current' else 'llamaguard-attested-current-run'
    expected = ['run', 'download', '10001', '--repo', 'example/step5c', '--name', archive + '-10001-1', '--dir', str(runner / archive)]
    stub = bindir / 'gh'
    stub.write_text('#!' + sys.executable + '\nimport json,pathlib,shutil,sys\nexpected=' + repr(expected) + '\n'
                    'assert sys.argv[1:] == expected\n'
                    'pathlib.Path(' + repr(str(tmp_path / 'argv.json')) + ').write_text(json.dumps(sys.argv[1:]))\n' +
                    ('raise SystemExit(7)\n' if fault == 'download_failure' else '') +
                    'shutil.copytree(' + repr(str(incoming)) + ',expected[-1],dirs_exist_ok=True,symlinks=True)\n')
    stub.chmod(0o755)
    env = {'PATH': str(bindir) + ':/usr/bin:/bin', 'HOME': str(tmp_path), 'LANG': 'C', 'LC_ALL': 'C',
           'GITHUB_WORKSPACE': str(root), 'RUNNER_TEMP': str(runner), 'GITHUB_RUN_ID': '10001',
           'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REPOSITORY': 'example/step5c'}
    body = doc['jobs'][job]['steps'][ordinal - 1]['run']
    result = subprocess.run(['/bin/bash', '-c', body], cwd=root, env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=30)
    assert json.loads((tmp_path / 'argv.json').read_text()) == expected
    accepted = fault is None or (fault == 'empty' and phase == 'current')
    if accepted:
        assert result.returncode == 0, result.stderr
        restored = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        assert restored == payloads
        hashes = {line.split(None, 1)[1].strip(): line.split(None, 1)[0] for line in result.stdout.decode().splitlines()}
        assert hashes == {str(root / relative): digest(raw) for relative, raw in payloads.items()}
    else:
        assert result.returncode != 0
        if fault == 'download_failure': assert result.returncode == 7
        else:
            assert b'::error::' in result.stdout
            assert (root / selected[0]).read_bytes() == payloads[selected[0]]
    # No network, actual attestation action, signer-policy check or model runs.
    assert 'attest verify' not in body and 'check_external_summary_attestation' not in body


def test_lg_preservation_keeps_full_state_profile_unfinished(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary']['authority_effect'] == 'none'
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


# ---------------------------------------------------------------------------
# L5/L6/L7 source-declared attestation reads. Synthetic unit data is never a
# Sigstore-valid attestation or an observed whole-runtime acceptance record.
# ---------------------------------------------------------------------------
LG_ATTEST_JOB = 'attest_llamaguard_current_run_summary'
LG_ATTEST_SOURCE_PATHS = (
    'PULSE_safe_pack_v0/tools/build_llamaguard_attestation_envelope_v1.py',
    'PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py',
)
LG_ATTEST_INPUT_CASES = (
    (5, 'llamaguard-summary', 'summary'),
    (6, 'llamaguard-summary', 'summary'),
    (6, 'llamaguard-raw-evidence', 'raw_evidence'),
    (6, 'llamaguard-evaluator-manifest', 'evaluator_manifest'),
    (6, 'llamaguard-dataset', 'dataset'),
    (6, 'external-signer-policy', 'signer_policy'),
    (6, 'threshold-policy', 'threshold_policy'),
    (6, 'workflow-source', 'workflow'),
    (6, 'llamaguard-attestation-bundle', 'bundle_out'),
    (7, 'llamaguard-summary', 'summary'),
    (7, 'llamaguard-attestation-envelope', 'out'),
    (7, 'external-signer-policy', 'signer_policy'),
    (7, 'llamaguard-attestation-bundle', 'bundle_out'),
)


@pytest.fixture(scope='module')
def lg_attestation_envelope_tool():
    path = ROOT / LG_ATTEST_SOURCE_PATHS[0]
    raw = path.read_bytes()
    assert hashlib.sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest() == 'ecbef6ce1d2a48b5c466b79c916d1161de9df377'
    spec = importlib.util.spec_from_file_location('step5c_lg_envelope_semantic_unit', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def lg_attestation_method(side):
    if side == 'builder': return BUILDER, BUILDER._llamaguard_attestation_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_llamaguard_attestation_expectations


@pytest.mark.parametrize('ordinal,role,attribute', LG_ATTEST_INPUT_CASES)
def test_lg_attestation_actual_source_has_reciprocal_step_input(source_fixture, lg_attestation_envelope_tool, ordinal, role, attribute):
    # Expected paths come from the actual called tool's argparse defaults,
    # not the two graph constructors or their source-extraction helpers.
    args = lg_attestation_envelope_tool._parser().parse_args([
        '--bundle-source', '/synthetic/action-bundle', '--attestation-id', '1',
        '--attestation-url', 'https://example.invalid/synthetic', '--attestation-action-ref', 'synthetic-only'])
    rows, steps = provenance_rows(source_fixture.plan)
    row, step = rows[role], steps[(LG_ATTEST_JOB, ordinal)]
    assert row['path_or_uri'] == getattr(args, attribute)
    if ordinal == 5:
        assert mapping_source_document()['jobs'][LG_ATTEST_JOB]['steps'][4]['with']['subject-path'] == row['path_or_uri']
    assert row['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in row['required_consumer_occurrence_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_attestation_resolves_copy_and_digest_reads_not_verification_claims(source_fixture, recorded_source_objects, side):
    module, method = lg_attestation_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    assert len(facts['locators']) == 10 and len(facts['steps']) == 3
    assert sorted(len(x['inputs']) for x in facts['steps'].values()) == [1, 4, 8]
    assert facts['bundle_handoff'] == {
        'action_output_selector': '${{ steps.attest_llamaguard_summary.outputs.bundle-path }}',
        'canonical_preservation_path': 'PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json',
        'preservation_occurrence_id': module._step_id(LG_ATTEST_JOB, 6),
        'content_origin_occurrence_id': module._step_id(LG_ATTEST_JOB, 5),
        'source_requires_byte_identity': True}
    assert 'signature_verified' not in repr(facts) and 'artifact_id' not in repr(facts)
    l7 = facts['steps'][module._step_id(LG_ATTEST_JOB, 7)]
    assert not set(l7['inputs']) & {'threshold-policy', 'llamaguard-raw-evidence', 'llamaguard-dataset', 'llamaguard-evaluator-manifest'}


def test_lg_attestation_independent_checker_never_calls_plan_builder(source_fixture, recorded_source_objects):
    workflow = mapping_source_document()
    built = BUILDER._llamaguard_attestation_source_projection(workflow, recorded_source_objects)
    with patch.object(BUILDER, '_llamaguard_attestation_source_projection', side_effect=AssertionError('builder prohibited')):
        checked = PLAN_CHECKER._source_llamaguard_attestation_expectations(workflow, recorded_source_objects)
        PLAN_CHECKER._verify_source_llamaguard_attestation_equations(source_fixture.plan, workflow, recorded_source_objects)
    assert canonical(built) == canonical(checked)
    function = ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER.check_plan)))
    names = {node.func.id: node.lineno for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert names['_verify_source_llamaguard_attestation_equations'] < names['_reconstruct_expected_plan']


def corrupt_lg_attestation_plan(original, mutation):
    plan = copy.deepcopy(original); rows, steps = provenance_rows(plan)
    if mutation.startswith('omit:') or mutation.startswith('invent:'):
        kind, ordinal, role = mutation.split(':', 2); row, step = rows[role], steps[(LG_ATTEST_JOB, int(ordinal))]
        sid, oid = row['state_id'], step['occurrence_id']
        if kind == 'omit':
            step['input_state_ids'] = [v for v in step['input_state_ids'] if v != sid]
            row['required_consumer_occurrence_ids'] = [v for v in row['required_consumer_occurrence_ids'] if v != oid]
        else:
            step['input_state_ids'] = sorted(set(step['input_state_ids']) | {sid})
            row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {oid})
    elif mutation == 'wrong_path': rows['llamaguard-dataset']['path_or_uri'] = 'wrong/dataset.jsonl'
    elif mutation == 'copy_is_new_origin': rows['llamaguard-attestation-bundle']['producer_occurrence_id'] = steps[(LG_ATTEST_JOB, 6)]['occurrence_id']
    elif mutation == 'extra_writer': steps[(LG_ATTEST_JOB, 6)]['output_state_ids'].append(rows['llamaguard-attestation-bundle']['state_id'])
    elif mutation == 'missing_reverse': rows['llamaguard-dataset']['required_consumer_occurrence_ids'].remove(steps[(LG_ATTEST_JOB, 6)]['occurrence_id'])
    elif mutation == 'optional': rows['llamaguard-dataset']['required'] = False
    elif mutation == 'metadata_only': rows['llamaguard-dataset']['content_requirement'] = 'metadata_only'
    elif mutation == 'non_authority_input': rows['external-signer-policy']['authority_bearing'] = False
    elif mutation == 'missing_role': plan['state_templates'].remove(rows['llamaguard-dataset'])
    elif mutation == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(rows['llamaguard-dataset']))
    elif mutation == 'duplicate_step': next(job for job in plan['jobs'] if job['source_job_id'] == LG_ATTEST_JOB)['steps'].append(copy.deepcopy(steps[(LG_ATTEST_JOB, 6)]))
    else: raise AssertionError(mutation)
    return plan


LG_ATTEST_MUTATIONS = tuple('omit:' + str(n) + ':' + role for n, role, _ in LG_ATTEST_INPUT_CASES) + (
    'invent:7:threshold-policy', 'invent:7:llamaguard-raw-evidence', 'invent:5:external-signer-policy',
    'wrong_path', 'copy_is_new_origin', 'extra_writer', 'missing_reverse', 'optional', 'metadata_only',
    'non_authority_input', 'missing_role', 'duplicate_role', 'duplicate_step',
)


@pytest.mark.parametrize('mutation', LG_ATTEST_MUTATIONS)
def test_lg_attestation_source_predicate_rejects_wrong_maps(source_fixture, recorded_source_objects, mutation):
    wrong = corrupt_lg_attestation_plan(source_fixture.plan, mutation)
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_attestation_'):
        PLAN_CHECKER._verify_source_llamaguard_attestation_equations(wrong, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['omit:6:llamaguard-raw-evidence', 'invent:7:threshold-policy', 'wrong_path', 'metadata_only'])
def test_lg_attestation_agreeing_wrong_constructors_are_not_source_evidence(source_fixture, recorded_source_objects, mutation):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        doc = mapping_source_document(); jobs, steps, _ = module._build_jobs(doc)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
        answers.append(canonical(corrupt_lg_attestation_plan(plan, mutation)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_attestation_'):
        PLAN_CHECKER._verify_source_llamaguard_attestation_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['omit:5:llamaguard-summary', 'omit:6:llamaguard-raw-evidence', 'omit:7:llamaguard-attestation-bundle', 'invent:7:threshold-policy'])
def test_lg_attestation_rehashed_schema_valid_plan_fails_real_checker(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_lg_attestation_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-plan.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == 'lg_attestation_step_io_mismatch'


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', LG_ATTEST_SOURCE_PATHS)
@pytest.mark.parametrize('fault', ['missing', 'bytes', 'path'])
def test_lg_attestation_semantic_sources_are_exact(source_fixture, recorded_source_objects, side, path, fault):
    module, method = lg_attestation_method(side); sources = dict(recorded_source_objects)
    if fault == 'missing': del sources[path]
    elif fault == 'bytes': sources[path] = replace(sources[path], data=sources[path].data + b'\n# unreviewed\n')
    else: sources[path] = replace(sources[path], path='other/tool.py')
    with pytest.raises(module.PlanError, match='lg_attestation_source_'):
        method(mapping_source_document(), sources)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['subject', 'bundle_source', 'signer', 'out'])
def test_lg_attestation_changed_workflow_is_not_silently_remapped(recorded_source_objects, side, fault):
    doc = mapping_source_document(); steps = doc['jobs'][LG_ATTEST_JOB]['steps']
    if fault == 'subject': steps[4]['with']['subject-path'] = 'wrong/summary.json'
    elif fault == 'bundle_source': steps[5]['run'] = steps[5]['run'].replace('outputs.bundle-path', 'outputs.other-path')
    elif fault == 'signer': steps[6]['run'] = steps[6]['run'].replace('policy/external_signers_v1.yml', 'policy/other.yml')
    else: steps[6]['run'] = steps[6]['run'].replace('llamaguard_attestation_verifier_v1.json', 'other-report.json')
    module, method = lg_attestation_method(side)
    with pytest.raises(module.PlanError, match='lg_attestation_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_attestation_installation_preserves_all_outside_bindings(recorded_source_objects, side):
    module, _ = lg_attestation_method(side); doc = mapping_source_document()
    _, old_steps, _ = module._build_jobs(doc)
    with patch.object(module, '_install_llamaguard_attestation_projection', return_value=None):
        old_states = module._build_states(old_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    _, new_steps, _ = module._build_jobs(doc)
    new_states = module._build_states(new_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    owned = {module._step_id(LG_ATTEST_JOB, n) for n in (5, 6, 7)}
    assert len(old_states) == len(new_states) == 62
    for old, new in zip(old_states, new_states):
        old, new = copy.deepcopy(old), copy.deepcopy(new)
        for row in (old, new): row['required_consumer_occurrence_ids'] = [x for x in row['required_consumer_occurrence_ids'] if x not in owned]
        assert old == new
    for key, step in new_steps.items():
        if step['occurrence_id'] not in owned: assert step == old_steps[key]
        assert step['output_state_ids'] == old_steps[key]['output_state_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', LG_ATTEST_SOURCE_PATHS)
def test_lg_attestation_called_sources_in_committed_and_prepared_inventory(source_fixture, side, path):
    module, _ = lg_attestation_method(side)
    assert sum(p == path for _, p in module.SOURCE_ROLES) == 1
    rows = [r for r in source_fixture.plan['source_inventory'] if r['path'] == path]
    assert len(rows) == 1 and rows[0]['sha256'] == digest((ROOT / path).read_bytes())
    members = prepared_fixture_members(source_fixture)
    assert any(data == (ROOT / path).read_bytes() for data in members.values())


@pytest.mark.parametrize('fault', [None, 'empty', 'duplicate', 'nonfinite', 'missing', 'symlink', 'same_path', 'not_object'])
def test_lg_attestation_real_bundle_persistence_keeps_bytes_not_signature_claim(tmp_path, lg_attestation_envelope_tool, fault):
    tool = lg_attestation_envelope_tool; src = tmp_path / 'action-output.json'; dst = tmp_path / 'canonical-bundle.json'
    raw = b'{ "synthetic-unit-only": true, "not-a-valid-signature": [1, 2] }\n'
    src.write_bytes(raw)
    if fault == 'empty': src.write_bytes(b'')
    elif fault == 'duplicate': src.write_bytes(b'{"duplicate":1,"duplicate":2}')
    elif fault == 'nonfinite': src.write_bytes(b'{"bad":NaN}')
    elif fault == 'missing': src.unlink()
    elif fault == 'symlink':
        target = tmp_path / 'target'; target.write_bytes(raw); src.unlink(); src.symlink_to(target)
    elif fault == 'same_path': dst = src
    elif fault == 'not_object': src.write_bytes(b'[]')
    if fault is not None:
        with pytest.raises(tool.EnvelopeError): tool._persist_bundle(src, dst)
        if dst != src: assert not dst.exists()
    else:
        result, hashed = tool._persist_bundle(src, dst)
        assert src.read_bytes() == dst.read_bytes() == raw and hashed == digest(raw)
        assert result == json.loads(raw)
        assert not list(tmp_path.glob('.llamaguard_summary.bundle.*'))


@pytest.mark.parametrize('fault', [None, 'raw_digest', 'dataset_digest', 'manifest_missing'])
def test_lg_attestation_actual_summary_binding_reads_three_files(tmp_path, lg_attestation_envelope_tool, fault):
    tool = lg_attestation_envelope_tool
    dataset, raw, manifest = (tmp_path / name for name in ('dataset.jsonl', 'raw.jsonl', 'manifest.json'))
    for p in (dataset, raw, manifest): p.write_bytes(('synthetic-unit:' + p.name + '\n').encode())
    sha = 'a' * 40; repository = 'HKati/pulse-release-gates-0.1'; signer = tool.EXPECTED_SIGNER_IDENTITY
    summary = {'schema_version': tool.SUMMARY_SCHEMA_VERSION, 'summary_id': 'synthetic-unit', 'tool': {'name': 'llamaguard'},
        'run': {'generated_at': EXAMPLE_START, 'dataset_digest': digest(dataset.read_bytes())},
        'subject': {'kind': 'release_candidate', 'digest_algorithm': 'sha256', 'digest': digest(sha.encode())},
        'threshold_ref': {'key': tool.EXPECTED_THRESHOLD_KEY, 'uri': tool.THRESHOLD_POLICY_REL},
        'evidence': {'raw_artifact_uri': raw.name, 'raw_artifact_digest': digest(raw.read_bytes())},
        'signing': {'mode': tool.EXPECTED_SIGNING_MODE, 'identity': signer},
        'result': {'passed': True, 'release_contribution': 'required'},
        'extensions': {'repository': repository, 'source_commit': sha, 'dataset_path': dataset.name, 'evaluator_source': manifest.name},
        'metrics': [{'key': 'llamaguard_violation_rate', 'passed': True}]}
    if fault == 'raw_digest': summary['evidence']['raw_artifact_digest'] = '0' * 64
    elif fault == 'dataset_digest': summary['run']['dataset_digest'] = '0' * 64
    elif fault == 'manifest_missing': manifest.unlink()
    kwargs = dict(repo_root=tmp_path, summary=summary, source_digest=sha, repository=repository, signer_identity=signer,
                  verified_at=tool._parse_utc(EXAMPLE_END, 'synthetic unit')[1], raw_path=raw, dataset_path=dataset, evaluator_manifest_path=manifest)
    if fault is not None:
        with pytest.raises(tool.EnvelopeError): tool._validate_summary(**kwargs)
    else:
        with patch.object(tool, '_sha256_file', wraps=tool._sha256_file) as read:
            result = tool._validate_summary(**kwargs)
        assert [call.args[0] for call in read.call_args_list] == [dataset, raw, manifest]
        assert result['raw_sha256'] == digest(raw.read_bytes())
        assert result['dataset_sha256'] == digest(dataset.read_bytes())
        assert result['evaluator_manifest_sha256'] == digest(manifest.read_bytes())


def test_lg_attestation_mapping_still_cannot_satisfy_runtime_completion(source_fixture):
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert len(source_fixture.plan['state_templates']) == 62
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


# ---------------------------------------------------------------------------
# P22/P23 source-declared production and ingestion. The actual ingester hashes
# the dataset/manifest; it does not admit their identity or validate case IDs.
# ---------------------------------------------------------------------------
LG_PRODUCTION_ADAPTER = 'PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py'
LG_PRODUCTION_NEW_INPUTS = ('llamaguard-dataset',) + tuple(
    'llamaguard-output:' + case for case in (
        'benign_factual_response', 'violent_harm_refusal', 'credential_theft_refusal',
        'private_address_refusal', 'self_harm_support', 'hate_content_refusal'))


@pytest.fixture(scope='module')
def lg_production_tools():
    result = {}
    for name, path, expected in (
        ('runner', 'PULSE_safe_pack_v0/tools/run_llamaguard_current_evidence_v0.py', '058edf0d16383db41a5a4500caf4b484321d2e57'),
        ('ingester', LG_PRODUCTION_ADAPTER, 'b0e0479c4939110b08350655be234badffa189f1'),
    ):
        target = ROOT / path; data = target.read_bytes()
        assert hashlib.sha1(('blob ' + str(len(data)) + '\0').encode() + data).hexdigest() == expected
        spec = importlib.util.spec_from_file_location('step5c_production_unit_' + name, target)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        result[name] = module
    return result


def lg_production_method(side):
    if side == 'builder': return BUILDER, BUILDER._llamaguard_production_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_llamaguard_production_expectations


@pytest.mark.parametrize('role', LG_PRODUCTION_NEW_INPUTS)
def test_lg_production_missing_source_read_is_present(source_fixture, lg_production_tools, role):
    # The expected sequence is obtained from the original producer's real
    # dataset reader, not the mapping tools. Reading the fixture is not inference.
    dataset = 'PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl'
    cases = lg_production_tools['runner']._load_cases(ROOT / dataset)
    expected = ['llamaguard-dataset'] + ['llamaguard-output:' + row['case_id'] for row in cases]
    assert role in expected
    rows, steps = provenance_rows(source_fixture.plan)
    p23 = steps[('pulse', 23)]
    assert rows[role]['state_id'] in p23['input_state_ids']
    assert p23['occurrence_id'] in rows[role]['required_consumer_occurrence_ids']
    if role == 'llamaguard-dataset': assert rows[role]['path_or_uri'] == dataset
    else: assert rows[role]['producer_occurrence_id'] == steps[('pulse', 22)]['occurrence_id']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_production_source_reads_preserve_ingester_limits(recorded_source_objects, side):
    module, method = lg_production_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    assert len(facts['locators']) == 17
    assert facts['ingest_read_modes'] == {
        'llamaguard-raw-evidence': 'classification_parse_and_digest', 'llamaguard-dataset': 'digest_only',
        'llamaguard-evaluator-manifest': 'digest_only', 'threshold-policy': 'threshold_parse'}
    boundary = facts['classification_handoff']
    assert len(boundary['case_ids']) == 6 and len(set(boundary['case_ids'])) == 6
    assert boundary['producer_emits_one_record_per_case'] is True
    assert boundary['ingester_traverses_all_records'] is True
    assert boundary['ingester_checks_case_identity'] is False
    assert boundary['observed_consumption_proved'] is False
    assert len(facts['steps'][module._step_id('pulse', 22)]['inputs']) == 7
    assert len(facts['steps'][module._step_id('pulse', 22)]['outputs']) == 8
    assert len(facts['steps'][module._step_id('pulse', 23)]['inputs']) == 10
    assert facts['steps'][module._step_id('pulse', 23)]['outputs'] == ['llamaguard-summary']


def test_lg_production_separate_source_predicate_precedes_reconstruction(source_fixture, recorded_source_objects):
    workflow = mapping_source_document()
    first = BUILDER._llamaguard_production_source_projection(workflow, recorded_source_objects)
    with patch.object(BUILDER, '_llamaguard_production_source_projection', side_effect=AssertionError('builder forbidden')):
        second = PLAN_CHECKER._source_llamaguard_production_expectations(workflow, recorded_source_objects)
        PLAN_CHECKER._verify_source_llamaguard_production_equations(source_fixture.plan, workflow, recorded_source_objects)
    assert canonical(first) == canonical(second)
    tree = ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER.check_plan)))
    calls = {n.func.id: n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls['_verify_source_llamaguard_production_equations'] < calls['_reconstruct_expected_plan']


def corrupt_lg_production_plan(original, mutation):
    plan = copy.deepcopy(original); rows, steps = provenance_rows(plan)
    p22, p23 = steps[('pulse', 22)], steps[('pulse', 23)]
    if mutation.startswith('omit:'):
        role = mutation[5:]; row = rows[role]
        p23['input_state_ids'] = [sid for sid in p23['input_state_ids'] if sid != row['state_id']]
        row['required_consumer_occurrence_ids'] = [oid for oid in row['required_consumer_occurrence_ids'] if oid != p23['occurrence_id']]
    elif mutation.startswith('invent:'):
        _, number, role = mutation.split(':', 2); step = steps[('pulse', int(number))]; row = rows[role]
        step['input_state_ids'] = sorted(set(step['input_state_ids']) | {row['state_id']})
        row['required_consumer_occurrence_ids'] = sorted(set(row['required_consumer_occurrence_ids']) | {step['occurrence_id']})
    elif mutation == 'wrong_case_locator': rows[LG_PRODUCTION_NEW_INPUTS[1]]['path_or_uri'] += '-wrong'
    elif mutation == 'wrong_case_origin': rows[LG_PRODUCTION_NEW_INPUTS[1]]['producer_occurrence_id'] = p23['occurrence_id']
    elif mutation == 'extra_writer': p23['output_state_ids'].append(rows[LG_PRODUCTION_NEW_INPUTS[1]]['state_id'])
    elif mutation == 'missing_reverse': rows['llamaguard-dataset']['required_consumer_occurrence_ids'].remove(p23['occurrence_id'])
    elif mutation == 'optional': rows[LG_PRODUCTION_NEW_INPUTS[1]]['required'] = False
    elif mutation == 'metadata_only': rows[LG_PRODUCTION_NEW_INPUTS[1]]['content_requirement'] = 'metadata_only'
    elif mutation == 'non_authority': rows[LG_PRODUCTION_NEW_INPUTS[1]]['authority_bearing'] = False
    elif mutation == 'missing_role': plan['state_templates'].remove(rows[LG_PRODUCTION_NEW_INPUTS[1]])
    elif mutation == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(rows[LG_PRODUCTION_NEW_INPUTS[1]]))
    elif mutation == 'duplicate_step': next(job for job in plan['jobs'] if job['source_job_id'] == 'pulse')['steps'].append(copy.deepcopy(p23))
    elif mutation == 'self_input': p23['input_state_ids'].append(rows['llamaguard-summary']['state_id'])
    else: raise AssertionError(mutation)
    return plan


LG_PRODUCTION_MUTATIONS = tuple('omit:' + role for role in LG_PRODUCTION_NEW_INPUTS) + (
    'invent:22:threshold-policy', 'invent:23:external-signer-policy', 'invent:23:workflow-source',
    'wrong_case_locator', 'wrong_case_origin', 'extra_writer', 'missing_reverse', 'optional',
    'metadata_only', 'non_authority', 'missing_role', 'duplicate_role', 'duplicate_step', 'self_input')


@pytest.mark.parametrize('mutation', LG_PRODUCTION_MUTATIONS)
def test_lg_production_source_predicate_rejects_false_graph(source_fixture, recorded_source_objects, mutation):
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_production_'):
        PLAN_CHECKER._verify_source_llamaguard_production_equations(
            corrupt_lg_production_plan(source_fixture.plan, mutation), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['omit:llamaguard-dataset', 'omit:' + LG_PRODUCTION_NEW_INPUTS[1], 'invent:22:threshold-policy'])
def test_lg_production_common_wrong_answers_are_rejected(source_fixture, recorded_source_objects, mutation):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        workflow = mapping_source_document(); jobs, steps, _ = module._build_jobs(workflow)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
        answers.append(canonical(corrupt_lg_production_plan(plan, mutation)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='lg_production_'):
        PLAN_CHECKER._verify_source_llamaguard_production_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('mutation', ['omit:llamaguard-dataset', 'omit:' + LG_PRODUCTION_NEW_INPUTS[1],
                                      'invent:22:threshold-policy', 'invent:23:external-signer-policy'])
def test_lg_production_rehashed_plan_rejected_by_isolated_checker(source_fixture, tmp_path, mutation):
    raw = canonical(corrupt_lg_production_plan(source_fixture.plan, mutation))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-plan.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == 'lg_production_step_io_mismatch'


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('path', [LG_PRODUCTION_ADAPTER, 'PULSE_safe_pack_v0/tools/run_llamaguard_current_evidence_v0.py',
                                 'PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl'])
@pytest.mark.parametrize('fault', ['missing', 'bytes', 'path'])
def test_lg_production_sources_reject_drift(recorded_source_objects, side, path, fault):
    module, method = lg_production_method(side); objects = dict(recorded_source_objects)
    if fault == 'missing': del objects[path]
    elif fault == 'bytes':
        raw = objects[path].data + b'\n'
        # Recomputing the object's blob identity does not revise the reviewed pin.
        objects[path] = replace(objects[path], data=raw, blob_sha1=hashlib.sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest())
    else: objects[path] = replace(objects[path], path='different/source.py')
    with pytest.raises(module.PlanError, match='lg_production_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['dataset', 'input', 'output', 'version'])
def test_lg_production_logical_workflow_substitution_rejected(recorded_source_objects, side, fault):
    workflow = mapping_source_document(); step = workflow['jobs']['pulse']['steps'][22]
    replacements = {'dataset': ('--dataset', '--different-dataset'), 'input': ('--in ', '--other-input '),
                    'output': ('llamaguard_summary.json', 'other-summary.json'),
                    'version': ('${LLAMAGUARD_VERSION}', 'unreviewed-version')}
    before, after = replacements[fault]; assert before in step['run']
    step['run'] = step['run'].replace(before, after)
    module, method = lg_production_method(side)
    with pytest.raises(module.PlanError, match='lg_production_workflow_drift'):
        method(workflow, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_production_retains_unselected_graph_fields(recorded_source_objects, side):
    module, _ = lg_production_method(side); workflow = mapping_source_document()
    _, before_steps, _ = module._build_jobs(workflow)
    with patch.object(module, '_install_llamaguard_production_projection', return_value=None):
        before_states = module._build_states(before_steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
    _, after_steps, _ = module._build_jobs(workflow)
    after_states = module._build_states(after_steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
    owned = {module._step_id('pulse', n) for n in (22, 23)}
    for old, new in zip(before_states, after_states):
        old, new = copy.deepcopy(old), copy.deepcopy(new)
        for row in (old, new): row['required_consumer_occurrence_ids'] = [oid for oid in row['required_consumer_occurrence_ids'] if oid not in owned]
        assert old == new
    for key, step in after_steps.items():
        if step['occurrence_id'] not in owned: assert step == before_steps[key]
        assert step['output_state_ids'] == before_steps[key]['output_state_ids']
    assert len(before_states) == len(after_states) == 62


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_lg_production_adapter_is_exactly_once_in_source_and_preparation(source_fixture, side):
    module, _ = lg_production_method(side)
    assert sum(path == LG_PRODUCTION_ADAPTER for _, path in module.SOURCE_ROLES) == 1
    entries = [row for row in source_fixture.plan['source_inventory'] if row['path'] == LG_PRODUCTION_ADAPTER]
    assert len(entries) == 1 and entries[0]['sha256'] == digest((ROOT / LG_PRODUCTION_ADAPTER).read_bytes())
    assert (ROOT / LG_PRODUCTION_ADAPTER).read_bytes() in prepared_fixture_members(source_fixture).values()


@pytest.mark.parametrize('fault', [None, 'empty', 'bad_label', 'duplicate_key', 'nonfinite', 'not_object'])
def test_lg_production_real_classification_reader_boundaries(tmp_path, lg_production_tools, fault):
    tool = lg_production_tools['ingester']; path = tmp_path / 'synthetic-raw.jsonl'
    record = {'case_id': 'synthetic', 'input': 'synthetic input', 'output': 'synthetic output',
              'llamaguard': {'label': 'unsafe', 'categories': ['S1', 'S1']}}
    raw = json.dumps(record) + '\n'
    if fault == 'empty': raw = '\n'
    elif fault == 'bad_label': record['llamaguard']['label'] = 'unknown'; raw = json.dumps(record) + '\n'
    elif fault == 'duplicate_key': raw = '{"input":"a","input":"b"}\n'
    elif fault == 'nonfinite': raw = '{"value":NaN}\n'
    elif fault == 'not_object': raw = '[]\n'
    path.write_text(raw)
    if fault is None: assert tool._read_llamaguard_jsonl(path) == (1, 1, {'S1': 1})
    else:
        with pytest.raises(tool.ProducerError): tool._read_llamaguard_jsonl(path)


def test_lg_production_ingester_does_not_verify_case_identity(tmp_path, lg_production_tools):
    tool = lg_production_tools['ingester']; path = tmp_path / 'synthetic-repeated-case.jsonl'
    record = {'case_id': 'same-case-twice', 'input': 'synthetic', 'output': 'synthetic', 'llamaguard': {'label': 'safe'}}
    path.write_text((json.dumps(record) + '\n') * 2)
    # This real source behavior is a qualification, not an admission rule for
    # Step 5C evidence. No runtime verifier is called or weakened here.
    assert tool._read_llamaguard_jsonl(path) == (2, 0, {})


@pytest.mark.parametrize('fault', [None, 'raw_missing', 'dataset_missing', 'manifest_missing'])
def test_lg_production_hash_only_input_helper_is_not_content_admission(tmp_path, lg_production_tools, fault):
    tool = lg_production_tools['ingester']; root = Path(os.path.commonpath([str(ROOT), str(tmp_path)]))
    raw, dataset, manifest, thresholds = (tmp_path / name for name in ('raw.jsonl', 'dataset.jsonl', 'manifest.json', 'thresholds.yaml'))
    raw.write_text(json.dumps({'input': 'synthetic', 'output': 'synthetic', 'llamaguard': {'label': 'safe'}}) + '\n')
    # Deliberately not a dataset/manifest JSON document: the helper hashes them,
    # proving why a successful adapter is not evidence of their admission.
    dataset.write_bytes(b'synthetic hash input, not parsed dataset\n')
    manifest.write_bytes(b'synthetic hash input, not parsed manifest\n')
    thresholds.write_text('llamaguard_violation_rate_max: 0.5\n')
    if fault is not None: {'raw_missing': raw, 'dataset_missing': dataset, 'manifest_missing': manifest}[fault].unlink()
    # Only the summary-construction subroutine is under test. Schema validation
    # is explicitly excluded here, not replaced in any runtime/acceptance path.
    with patch.object(tool, '_validate_summary_schema') as schema, \
         patch.object(tool, '_sha256_file', wraps=tool._sha256_file) as hashes:
        args = dict(repo_root=root, raw_path=raw, dataset_path=dataset, evaluator_manifest_path=manifest,
                    schema_path=tmp_path / 'excluded-unit-schema.json', thresholds_path=thresholds,
                    run_id='synthetic-unit', generated_at=EXAMPLE_START, release_candidate='main',
                    git_sha='a' * 40, repository='HKati/pulse-release-gates-0.1',
                    signer_identity='synthetic-unit', tool_version='synthetic-unit', adapter_version='synthetic-unit')
        if fault is not None:
            with pytest.raises(tool.ProducerError): tool._build_summary(**args)
            schema.assert_not_called()
        else:
            result = tool._build_summary(**args)
            assert [call.args[0] for call in hashes.call_args_list] == [raw, dataset, Path(tool.__file__).resolve(), manifest]
            assert result['run']['dataset_digest'] == digest(dataset.read_bytes())
            assert result['evidence']['raw_artifact_digest'] == digest(raw.read_bytes())
            assert result['extensions']['classification_counts']['total'] == 1
            assert all(value is False for value in result['extensions']['producer_boundary'].values())
            schema.assert_called_once()


def test_lg_production_mapping_keeps_completion_closed(source_fixture):
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert len(source_fixture.plan['state_templates']) == 62
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


# ---------------------------------------------------------------------------
# P36 pre-attestation postconditions: seven existing content roles are hashed
# before publication. The other three selected files stay explicitly unmodeled.
# ---------------------------------------------------------------------------
PRE_ATTEST_POSTCONDITION_ROLES = (
    'pre-materialization-status', 'status-baseline', 'required-gate-evidence',
    'self-contained-evidence-floor', 'llamaguard-raw-evidence',
    'llamaguard-evaluator-manifest', 'llamaguard-summary',
)


def pre_attest_postcondition_method(side):
    if side == 'builder':
        return BUILDER, BUILDER._pre_attestation_postcondition_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_pre_attestation_postcondition_expectations


def pre_attest_checked_source_paths():
    # Read the literal source array independently of either plan tool.
    body = mapping_source_document()['jobs']['pulse']['steps'][35]['run']
    lines = body.splitlines()
    start = lines.index('REQUIRED_FILES=(') + 1
    end = lines.index(')', start)
    return [shlex.split(line)[0].replace('${PACK_DIR}/', 'PULSE_safe_pack_v0/')
            for line in lines[start:end]]


@pytest.mark.parametrize('role', PRE_ATTEST_POSTCONDITION_ROLES)
def test_pre_attest_postcondition_each_hashed_role_has_reciprocal_input(source_fixture, role):
    rows, steps = provenance_rows(source_fixture.plan)
    row, check = rows[role], steps[('pulse', 36)]
    assert row['path_or_uri'].split('#', 1)[0] in pre_attest_checked_source_paths()
    assert row['state_id'] in check['input_state_ids']
    assert check['occurrence_id'] in row['required_consumer_occurrence_ids']
    assert row['producer_occurrence_id'] != check['occurrence_id']
    assert check['output_state_ids'] == []


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_pre_attest_postcondition_keeps_full_selector_and_partial_role_extent(recorded_source_objects, side):
    module, method = pre_attest_postcondition_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    assert facts['checked_paths'] == pre_attest_checked_source_paths()
    assert len(facts['checked_paths']) == 10
    assert len(facts['locators']) == 7
    assert facts['unmodeled_checked_paths'] == sorted('PULSE_safe_pack_v0/artifacts/' + name for name in (
        'status_summary_baseline.md', 'status_summary_baseline.json', 'refusal_delta_summary.json'))
    assert facts['steps'] == {module._step_id('pulse', 36): {
        'inputs': sorted(PRE_ATTEST_POSTCONDITION_ROLES), 'outputs': []}}
    assert facts['read_basis'] == 'source_declared_file_hash_read'
    assert facts['observed_read_receipt'] is False
    assert facts['semantic_content_admission'] is False
    assert facts['origins']['pre-materialization-status'] == module._step_id('pulse', 13)
    assert facts['locators']['pre-materialization-status'].endswith('#pre-release-required-materialization')


def test_pre_attest_postcondition_checker_is_separate_and_precedes_equality(source_fixture, recorded_source_objects):
    workflow = mapping_source_document()
    expected = BUILDER._pre_attestation_postcondition_source_projection(workflow, recorded_source_objects)
    with patch.object(BUILDER, '_pre_attestation_postcondition_source_projection', side_effect=AssertionError('builder forbidden')):
        actual = PLAN_CHECKER._source_pre_attestation_postcondition_expectations(workflow, recorded_source_objects)
        PLAN_CHECKER._verify_source_pre_attestation_postcondition_equations(source_fixture.plan, workflow, recorded_source_objects)
    assert canonical(actual) == canonical(expected)
    tree = ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER.check_plan)))
    calls = {n.func.id: n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls['_verify_source_pre_attestation_postcondition_equations'] < calls['_reconstruct_expected_plan']


def corrupt_pre_attest_postcondition_plan(original, fault):
    plan = copy.deepcopy(original); rows, steps = provenance_rows(plan)
    step = steps[('pulse', 36)]; row = rows['llamaguard-summary']
    if fault.startswith('omit:'):
        row = rows[fault[5:]]
        step['input_state_ids'].remove(row['state_id'])
        row['required_consumer_occurrence_ids'].remove(step['occurrence_id'])
    elif fault.startswith('invent:'):
        row = rows[fault[7:]]
        step['input_state_ids'] = sorted(step['input_state_ids'] + [row['state_id']])
        row['required_consumer_occurrence_ids'] = sorted(row['required_consumer_occurrence_ids'] + [step['occurrence_id']])
    elif fault == 'wrong_locator': row['path_or_uri'] += '.different'
    elif fault == 'wrong_origin': row['producer_occurrence_id'] = step['occurrence_id']
    elif fault == 'extra_writer': step['output_state_ids'] = [row['state_id']]
    elif fault == 'missing_reverse': row['required_consumer_occurrence_ids'].remove(step['occurrence_id'])
    elif fault == 'optional': row['required'] = False
    elif fault == 'metadata_only': row['content_requirement'] = 'metadata_only'
    elif fault == 'non_authority': row['authority_bearing'] = False
    elif fault == 'mutation_class': row['mutation_class'] = 'advisory_output'
    elif fault == 'missing_role': plan['state_templates'].remove(row)
    elif fault == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(row))
    elif fault == 'missing_step': next(j for j in plan['jobs'] if j['source_job_id'] == 'pulse')['steps'].remove(step)
    elif fault == 'duplicate_step': next(j for j in plan['jobs'] if j['source_job_id'] == 'pulse')['steps'].append(copy.deepcopy(step))
    else: raise AssertionError(fault)
    return plan


PRE_ATTEST_POSTCONDITION_FAULTS = tuple('omit:' + role for role in PRE_ATTEST_POSTCONDITION_ROLES) + (
    'invent:gate-policy', 'invent:final-status', 'invent:pre-attestation-pulse-artifacts',
    'wrong_locator', 'wrong_origin', 'extra_writer', 'missing_reverse', 'optional',
    'metadata_only', 'non_authority', 'mutation_class', 'missing_role', 'duplicate_role',
    'missing_step', 'duplicate_step',
)


@pytest.mark.parametrize('fault', PRE_ATTEST_POSTCONDITION_FAULTS)
def test_pre_attest_postcondition_predicate_rejects_false_mapping(source_fixture, recorded_source_objects, fault):
    with pytest.raises(PLAN_CHECKER.PlanError, match='pre_attest_postcondition_'):
        PLAN_CHECKER._verify_source_pre_attestation_postcondition_equations(
            corrupt_pre_attest_postcondition_plan(source_fixture.plan, fault), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault', ['omit:llamaguard-summary', 'invent:pre-attestation-pulse-artifacts'])
def test_pre_attest_postcondition_equal_false_constructors_are_not_proof(source_fixture, recorded_source_objects, fault):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        workflow = mapping_source_document(); jobs, steps, _ = module._build_jobs(workflow)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
        answers.append(canonical(corrupt_pre_attest_postcondition_plan(plan, fault)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='pre_attest_postcondition_step_io_mismatch'):
        PLAN_CHECKER._verify_source_pre_attestation_postcondition_equations(
            json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault,code', [
    ('omit:llamaguard-summary', 'pre_attest_postcondition_step_io_mismatch'),
    ('invent:gate-policy', 'pre_attest_postcondition_step_io_mismatch'),
    ('invent:pre-attestation-pulse-artifacts', 'preservation_mapping_archive_readers_mismatch'),
    ('omit:pre-materialization-status', 'recorded_mapping_new_role_consumer_mismatch'),
])
def test_pre_attest_postcondition_rehashed_forgery_fails_real_checker(source_fixture, tmp_path, fault, code):
    raw = canonical(corrupt_pre_attest_postcondition_plan(source_fixture.plan, fault))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-plan.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == code


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'bytes', 'path'])
def test_pre_attest_postcondition_reviewed_source_cannot_be_substituted(recorded_source_objects, side, fault):
    module, method = pre_attest_postcondition_method(side); objects = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del objects[path]
    elif fault == 'bytes':
        data = objects[path].data.replace(b'  sha256sum "${artifact}"', b'  sha256sum "${artifact}" || true')
        assert data != objects[path].data
        objects[path] = replace(objects[path], data=data, blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    else: objects[path] = replace(objects[path], path='different/workflow.yml')
    with pytest.raises(module.PlanError, match='pre_attest_postcondition_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['guard', 'hash', 'member', 'early_success'])
def test_pre_attest_postcondition_changed_logical_workflow_rejected(recorded_source_objects, side, fault):
    document = mapping_source_document(); step = document['jobs']['pulse']['steps'][35]
    if fault == 'guard': step['if'] = '${{ always() }}'
    elif fault == 'hash': step['run'] = step['run'].replace('sha256sum "${artifact}"', 'true')
    elif fault == 'member': step['run'] = step['run'].replace('refusal_delta_summary.json', 'another.json')
    else: step['run'] = 'exit 0\n' + step['run']
    module, method = pre_attest_postcondition_method(side)
    with pytest.raises(module.PlanError, match='pre_attest_postcondition_workflow_drift'):
        method(document, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_pre_attest_postcondition_installer_only_changes_owned_inputs(recorded_source_objects, side):
    module, _ = pre_attest_postcondition_method(side); workflow = mapping_source_document()
    _, before_steps, _ = module._build_jobs(workflow)
    with patch.object(module, '_install_pre_attestation_postcondition_projection', return_value=None):
        before = module._build_states(before_steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
    _, after_steps, _ = module._build_jobs(workflow)
    after = module._build_states(after_steps, module.EXPECTED_CASE_IDS, workflow, recorded_source_objects)
    oid = module._step_id('pulse', 36)
    for old, new in zip(before, after):
        old, new = copy.deepcopy(old), copy.deepcopy(new)
        for row in (old, new): row['required_consumer_occurrence_ids'] = [x for x in row['required_consumer_occurrence_ids'] if x != oid]
        assert old == new
    for key, step in after_steps.items():
        if key != ('pulse', 36): assert step == before_steps[key]
        else:
            old, new = copy.deepcopy(before_steps[key]), copy.deepcopy(step)
            old.pop('input_state_ids'); new.pop('input_state_ids'); assert old == new
    assert len(before) == len(after) == 62


@pytest.mark.parametrize('index', [0, 9])
@pytest.mark.parametrize('fault', ['missing', 'empty', 'symlink', 'directory'])
def test_pre_attest_postcondition_real_shell_fails_closed_at_each_boundary(tmp_path, index, fault):
    paths = pre_attest_checked_source_paths()
    for name in paths:
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'SYNTHETIC HASHABLE BYTES; NOT AN ATTESTATION\n')
    target = tmp_path / paths[index]; target.unlink()
    if fault == 'empty': target.touch()
    elif fault == 'directory': target.mkdir()
    elif fault == 'symlink':
        source = tmp_path / 'source.txt'; source.write_text('SYNTHETIC\n'); target.symlink_to(source)
    script = mapping_source_document()['jobs']['pulse']['steps'][35]['run']
    result = subprocess.run(['/bin/bash', '-c', script], cwd=tmp_path,
        env={'PATH': '/usr/bin:/bin', 'PACK_DIR': str(tmp_path / 'PULSE_safe_pack_v0')},
        capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'postconditions satisfied' not in result.stdout
    assert '::error::release-grade pre-attestation artifact' in result.stdout
    hashes = [line for line in result.stdout.splitlines() if re.match(r'^[0-9a-f]{64}  ', line)]
    assert len(hashes) == index


def test_pre_attest_postcondition_real_shell_hashes_all_ten_without_semantic_admission(tmp_path):
    paths = pre_attest_checked_source_paths(); data = b'SYNTHETIC NON-JSON CONTENT\n'
    for name in paths:
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    script = mapping_source_document()['jobs']['pulse']['steps'][35]['run']
    result = subprocess.run(['/bin/bash', '-c', script], cwd=tmp_path,
        env={'PATH': '/usr/bin:/bin', 'PACK_DIR': str(tmp_path / 'PULSE_safe_pack_v0')},
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    assert result.stdout.splitlines() == [digest(data) + '  ' + str(tmp_path / name) for name in paths] + [
        'OK: release-grade pre-attestation artifact postconditions satisfied']
    assert all((tmp_path / name).read_bytes() == data for name in paths)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob('*') if p.is_file()) == sorted(paths)


def test_pre_attest_postcondition_unmodeled_file_is_not_optional_in_original_shell(tmp_path):
    paths = pre_attest_checked_source_paths()
    for name in paths:
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'SYNTHETIC\n')
    missing = 'PULSE_safe_pack_v0/artifacts/status_summary_baseline.md'
    (tmp_path / missing).unlink()
    script = mapping_source_document()['jobs']['pulse']['steps'][35]['run']
    result = subprocess.run(['/bin/bash', '-c', script], cwd=tmp_path,
        env={'PATH': '/usr/bin:/bin', 'PACK_DIR': str(tmp_path / 'PULSE_safe_pack_v0')},
        capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and missing in result.stdout
    assert 'postconditions satisfied' not in result.stdout


def test_pre_attest_postcondition_hash_failure_does_not_reach_success(tmp_path):
    paths = pre_attest_checked_source_paths()
    for name in paths:
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'SYNTHETIC\n')
    mock_bin = tmp_path / 'mock-bin'; mock_bin.mkdir()
    mock = mock_bin / 'sha256sum'
    mock.write_text('#!/bin/bash\nprintf "synthetic hash failure\\n" >&2\nexit 86\n')
    mock.chmod(0o700)
    script = mapping_source_document()['jobs']['pulse']['steps'][35]['run']
    result = subprocess.run(['/bin/bash', '-c', script], cwd=tmp_path,
        env={'PATH': str(mock_bin), 'PACK_DIR': str(tmp_path / 'PULSE_safe_pack_v0')},
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 86
    assert result.stdout == '' and result.stderr == 'synthetic hash failure\n'


def test_pre_attest_postcondition_mapping_keeps_completion_and_inventory_unchanged(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary']['authority_effect'] == 'none'
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


# ---------------------------------------------------------------------------
# R26 final-file postconditions: retain final versions, all 25 selectors, and
# the distinction between a file-content hash and a directory-entry predicate.
# ---------------------------------------------------------------------------
FINAL_POSTCONDITION_ROLES = (
    'final-status', 'status-baseline', 'final-status-summary', 'required-gate-evidence',
    'recorded-candidate-index', 'release-evidence-input-manifest',
    'recorded-release-evidence-verifier', 'release-decision', 'release-decision-ledger-section',
    'quality-ledger-final', 'release-decision-report', 'release-authority-manifest',
    'artifact-provenance-binding', 'release-grade-junit', 'release-grade-sarif',
    'llamaguard-raw-evidence', 'llamaguard-evaluator-manifest', 'llamaguard-summary',
    'llamaguard-attestation-bundle', 'llamaguard-attestation-envelope', 'llamaguard-attestation-verifier',
)
FINAL_POSTCONDITION_UNMODELED = (
    'status_summary.md', 'status_summary_baseline.md', 'status_summary_baseline.json',
    'refusal_delta_summary.json',
)
FINAL_POSTCONDITION_DIRECTORIES = (
    'PULSE_safe_pack_v0/artifacts/recorded_release_candidates',
    'PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle',
)


def final_postcondition_method(side):
    if side == 'builder':
        return BUILDER, BUILDER._final_artifact_postcondition_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_final_artifact_postcondition_expectations


def final_postcondition_script():
    return mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][25]['run']


def final_checked_source_paths():
    # Literal test-side source extraction, not a call into either implementation.
    lines = final_postcondition_script().splitlines()
    start = lines.index('REQUIRED_FILES=(') + 1
    end = lines.index(')', start)
    return [shlex.split(line)[0].replace('${PACK_DIR}/', 'PULSE_safe_pack_v0/') for line in lines[start:end]]


@pytest.mark.parametrize('role', FINAL_POSTCONDITION_ROLES)
def test_final_postcondition_each_final_file_has_reciprocal_input(source_fixture, role):
    states, steps = provenance_rows(source_fixture.plan)
    row, consumer = states[role], steps[('release_grade_recorded_path', 26)]
    # No fragment stripping: pre-status/pre-ledger are not the selected version.
    assert row['path_or_uri'] in final_checked_source_paths()
    assert row['state_id'] in consumer['input_state_ids']
    assert consumer['occurrence_id'] in row['required_consumer_occurrence_ids']
    assert row['producer_occurrence_id'] != consumer['occurrence_id']
    assert consumer['output_state_ids'] == []


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_final_postcondition_complete_source_extent_is_not_complete_state_coverage(recorded_source_objects, side):
    module, method = final_postcondition_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    assert facts['checked_paths'] == final_checked_source_paths()
    assert len(facts['checked_paths']) == 25 and len(facts['locators']) == 21
    assert facts['unmodeled_checked_paths'] == sorted('PULSE_safe_pack_v0/artifacts/' + p for p in FINAL_POSTCONDITION_UNMODELED)
    assert facts['metadata_only_directory_checks'] == list(FINAL_POSTCONDITION_DIRECTORIES)
    assert facts['publication_only_selectors'] == sorted([
        FINAL_POSTCONDITION_DIRECTORIES[0] + '/**',
        'PULSE_safe_pack_v0/artifacts/self_contained_pulse_evidence_floor_v0.json'])
    assert facts['steps'] == {module._step_id('release_grade_recorded_path', 26): {
        'inputs': sorted(FINAL_POSTCONDITION_ROLES), 'outputs': []}}
    assert facts['read_basis'] == 'source_declared_file_hash_read'
    assert facts['observed_read_receipt'] is facts['semantic_content_admission'] is facts['directory_content_read'] is False
    assert facts['origins']['final-status'] == module._step_id('release_grade_recorded_path', 9)
    assert facts['origins']['quality-ledger-final'] == module._step_id('release_grade_recorded_path', 18)
    assert facts['origins']['llamaguard-attestation-bundle'] == module._step_id('attest_llamaguard_current_run_summary', 5)


def test_final_postcondition_source_predicate_is_separate_and_precedes_equality(source_fixture, recorded_source_objects):
    document = mapping_source_document()
    expected = BUILDER._final_artifact_postcondition_source_projection(document, recorded_source_objects)
    with patch.object(BUILDER, '_final_artifact_postcondition_source_projection', side_effect=AssertionError('builder forbidden')):
        actual = PLAN_CHECKER._source_final_artifact_postcondition_expectations(document, recorded_source_objects)
        PLAN_CHECKER._verify_source_final_artifact_postcondition_equations(source_fixture.plan, document, recorded_source_objects)
    assert canonical(expected) == canonical(actual)
    tree = ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER.check_plan)))
    calls = {n.func.id: n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls['_verify_source_final_artifact_postcondition_equations'] < calls['_reconstruct_expected_plan']


def corrupt_final_postcondition_plan(original, fault):
    plan = copy.deepcopy(original)
    states, steps = provenance_rows(plan)
    reader = steps[('release_grade_recorded_path', 26)]; oid = reader['occurrence_id']
    if ':' in fault:
        operation, role = fault.split(':', 1); state = states[role]; sid = state['state_id']
        if operation == 'omit':
            reader['input_state_ids'].remove(sid)
            state['required_consumer_occurrence_ids'].remove(oid)
        elif operation == 'invent':
            reader['input_state_ids'] = sorted(set(reader['input_state_ids']) | {sid})
            state['required_consumer_occurrence_ids'] = sorted(set(state['required_consumer_occurrence_ids']) | {oid})
        elif operation == 'reverse': state['required_consumer_occurrence_ids'].remove(oid)
        else: raise AssertionError(fault)
    elif fault == 'locator': states['quality-ledger-final']['path_or_uri'] += '#pre-authority-insertion'
    elif fault == 'origin': states['final-status']['producer_occurrence_id'] = BUILDER._step_id('pulse', 13)
    elif fault == 'writer': reader['output_state_ids'] = [states['final-status']['state_id']]
    elif fault == 'required': states['final-status-summary']['required'] = False
    elif fault == 'content': states['llamaguard-attestation-bundle']['content_requirement'] = 'metadata_only'
    elif fault == 'authority': states['release-grade-junit']['authority_bearing'] = True
    elif fault == 'mutation': states['final-status']['mutation_class'] = 'none'
    elif fault == 'missing_role': plan['state_templates'].remove(states['status-baseline'])
    elif fault == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(states['status-baseline']))
    elif fault == 'missing_step':
        for job in plan['jobs']:
            job['steps'] = [s for s in job['steps'] if s['occurrence_id'] != oid]
    elif fault == 'duplicate_step':
        for job in plan['jobs']:
            if reader in job['steps']: job['steps'].append(copy.deepcopy(reader)); break
    else: raise AssertionError(fault)
    return plan


@pytest.mark.parametrize('fault,code', [
    ('omit:final-status', 'step_io'), ('omit:quality-ledger-final', 'step_io'),
    ('omit:llamaguard-summary', 'step_io'), ('omit:recorded-candidate-index', 'step_io'),
    ('invent:pre-materialization-status', 'step_io'), ('invent:quality-ledger-pre-authority', 'step_io'),
    ('invent:self-contained-evidence-floor', 'step_io'), ('invent:recorded-release-candidate-envelopes', 'step_io'),
    ('invent:release-authority-audit-bundle', 'step_io'), ('invent:advisory-reference-bundle', 'step_io'),
    ('invent:gate-policy', 'step_io'), ('invent:materialized-release-required-gate-set', 'step_io'),
    ('reverse:release-grade-junit', 'reverse_inputs'), ('locator', 'locator'), ('origin', 'origin'),
    ('writer', 'writer'), ('required', 'duty'), ('content', 'duty'), ('authority', 'duty'), ('mutation', 'duty'),
    ('missing_role', 'role_missing'), ('duplicate_role', 'duplicate_role'),
    ('missing_step', 'step_missing'), ('duplicate_step', 'duplicate_step'),
])
def test_final_postcondition_rejects_false_files_versions_and_duties(source_fixture, recorded_source_objects, fault, code):
    bad = corrupt_final_postcondition_plan(source_fixture.plan, fault)
    with pytest.raises(PLAN_CHECKER.PlanError, match='final_postcondition_' + code):
        PLAN_CHECKER._verify_source_final_artifact_postcondition_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault', ['omit:final-status', 'invent:release-authority-audit-bundle', 'invent:self-contained-evidence-floor'])
def test_final_postcondition_equal_false_constructors_do_not_close_source_evidence(source_fixture, recorded_source_objects, fault):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        document = mapping_source_document(); jobs, steps, _ = module._build_jobs(document)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
        answers.append(canonical(corrupt_final_postcondition_plan(plan, fault)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='final_postcondition_step_io_mismatch'):
        PLAN_CHECKER._verify_source_final_artifact_postcondition_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault,code', [
    ('omit:llamaguard-summary', 'final_postcondition_step_io_mismatch'),
    ('omit:final-status-summary', 'final_postcondition_step_io_mismatch'),
    ('invent:self-contained-evidence-floor', 'final_postcondition_step_io_mismatch'),
    ('invent:pre-materialization-status', 'recorded_mapping_new_role_consumer_mismatch'),
])
def test_final_postcondition_rehashed_false_plan_fails_real_checker(source_fixture, tmp_path, fault, code):
    raw = canonical(corrupt_final_postcondition_plan(source_fixture.plan, fault))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-final-plan.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == code


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'path', 'bytes'])
def test_final_postcondition_rejects_substituted_workflow_bytes(recorded_source_objects, side, fault):
    module, method = final_postcondition_method(side); objects = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del objects[path]
    elif fault == 'path': objects[path] = replace(objects[path], path='different/workflow.yml')
    else:
        data = objects[path].data.replace(b'  sha256sum "${artifact}"', b'  sha256sum "${artifact}" || true')
        assert data != objects[path].data
        objects[path] = replace(objects[path], data=data, blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    with pytest.raises(module.PlanError, match='final_postcondition_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['array', 'hash', 'directory_read', 'empty_directory', 'publication', 'early_success'])
def test_final_postcondition_rejects_logical_source_drift(recorded_source_objects, side, fault):
    module, method = final_postcondition_method(side); document = mapping_source_document()
    rows = document['jobs']['release_grade_recorded_path']['steps']; step = rows[25]
    if fault == 'array': step['run'] = step['run'].replace('status_summary.md', 'another-summary.md')
    elif fault == 'hash': step['run'] = step['run'].replace('sha256sum "${artifact}"', 'true')
    elif fault == 'directory_read': step['run'] += 'find "${PACK_DIR}/artifacts/recorded_release_candidates" -type f -exec cat {} +\n'
    elif fault == 'empty_directory': step['run'] = step['run'].replace('! -d', '! -s')
    elif fault == 'publication': rows[32]['with']['path'] = rows[32]['with']['path'].replace('status_summary.md\n', '')
    else: step['run'] = 'exit 0\n' + step['run']
    with pytest.raises(module.PlanError, match='final_postcondition_workflow_drift'):
        method(document, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_final_postcondition_only_r26_inputs_and_inverse_links_change(recorded_source_objects, side):
    module, method = final_postcondition_method(side); document = mapping_source_document()
    _, old_steps, _ = module._build_jobs(document)
    with patch.object(module, '_install_final_artifact_postcondition_projection', return_value=None):
        old_states = module._build_states(old_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    _, new_steps, _ = module._build_jobs(document)
    new_states = module._build_states(new_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    oid = module._step_id('release_grade_recorded_path', 26)
    assert len(old_states) == len(new_states) == 62
    delta = 0
    for before, after in zip(old_states, new_states):
        old, new = copy.deepcopy(before), copy.deepcopy(after)
        delta += int(oid not in old['required_consumer_occurrence_ids'] and oid in new['required_consumer_occurrence_ids'])
        for row in (old, new): row['required_consumer_occurrence_ids'] = [r for r in row['required_consumer_occurrence_ids'] if r != oid]
        assert old == new
    assert delta == 18
    for key in new_steps:
        if key != ('release_grade_recorded_path', 26): assert old_steps[key] == new_steps[key]
        else:
            old, new = copy.deepcopy(old_steps[key]), copy.deepcopy(new_steps[key])
            assert set(old['input_state_ids']) <= set(new['input_state_ids'])
            assert len(new['input_state_ids']) - len(old['input_state_ids']) == 20
            old.pop('input_state_ids'); new.pop('input_state_ids'); assert old == new


def make_final_postcondition_files(root):
    paths = final_checked_source_paths()
    for index, name in enumerate(paths):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('SYNTHETIC NON-JSON FILE %d; NOT ATTESTED\n' % index).encode())
    for directory in FINAL_POSTCONDITION_DIRECTORIES: (root / directory).mkdir()
    return paths


def run_final_postcondition_shell(root, path='/usr/bin:/bin'):
    return subprocess.run(['/bin/bash', '-c', final_postcondition_script()], cwd=root,
        env={'PATH': path, 'PACK_DIR': str(root / 'PULSE_safe_pack_v0')},
        capture_output=True, text=True, timeout=15)


def test_final_postcondition_real_shell_checks_25_files_but_only_two_directory_entries(tmp_path):
    paths = make_final_postcondition_files(tmp_path)
    before = {name: (tmp_path / name).read_bytes() for name in paths}
    result = run_final_postcondition_shell(tmp_path)
    assert result.returncode == 0
    assert result.stdout.splitlines() == [digest(before[name]) + '  ' + str(tmp_path / name) for name in paths] + [
        'OK: final release-grade artifact postconditions satisfied']
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before
    # Empty directories are allowed by R26; contents and the floor are NOT read.
    assert all(list((tmp_path / directory).iterdir()) == [] for directory in FINAL_POSTCONDITION_DIRECTORIES)
    assert not (tmp_path / 'PULSE_safe_pack_v0/artifacts/self_contained_pulse_evidence_floor_v0.json').exists()
    for directory in FINAL_POSTCONDITION_DIRECTORIES:
        (tmp_path / directory / 'invalid-child.json').write_bytes(b'NOT VALID JSON\n')
        (tmp_path / directory / 'dangling-child').symlink_to(tmp_path / 'not-present')
    repeated = run_final_postcondition_shell(tmp_path)
    assert repeated.returncode == 0 and repeated.stdout == result.stdout


@pytest.mark.parametrize('index', [0, 24])
@pytest.mark.parametrize('fault', ['missing', 'empty', 'symlink', 'directory'])
def test_final_postcondition_real_shell_file_failures_do_not_reach_success(tmp_path, index, fault):
    paths = make_final_postcondition_files(tmp_path); target = tmp_path / paths[index]; target.unlink()
    if fault == 'empty': target.touch()
    elif fault == 'directory': target.mkdir()
    elif fault == 'symlink': target.symlink_to(tmp_path / paths[1])
    result = run_final_postcondition_shell(tmp_path)
    assert result.returncode != 0
    assert '::error::final release-grade artifact' in result.stdout
    assert 'postconditions satisfied' not in result.stdout
    hashes = [line for line in result.stdout.splitlines() if re.match(r'^[0-9a-f]{64}  ', line)]
    assert len(hashes) == index


@pytest.mark.parametrize('directory', FINAL_POSTCONDITION_DIRECTORIES)
@pytest.mark.parametrize('fault', ['missing', 'file', 'symlink'])
def test_final_postcondition_real_shell_directory_metadata_failure_after_hashes(tmp_path, directory, fault):
    paths = make_final_postcondition_files(tmp_path); target = tmp_path / directory; target.rmdir()
    if fault == 'file': target.write_bytes(b'SYNTHETIC FILE NOT DIRECTORY\n')
    elif fault == 'symlink':
        real = tmp_path / 'real-directory'; real.mkdir(); target.symlink_to(real, target_is_directory=True)
    result = run_final_postcondition_shell(tmp_path)
    assert result.returncode != 0 and 'postconditions satisfied' not in result.stdout
    assert 'is missing or symlinked' in result.stdout
    assert len([line for line in result.stdout.splitlines() if re.match(r'^[0-9a-f]{64}  ', line)]) == len(paths) == 25


@pytest.mark.parametrize('name', FINAL_POSTCONDITION_UNMODELED)
def test_final_postcondition_unmodeled_files_still_required_by_original_shell(tmp_path, name):
    make_final_postcondition_files(tmp_path)
    (tmp_path / 'PULSE_safe_pack_v0/artifacts' / name).unlink()
    result = run_final_postcondition_shell(tmp_path)
    assert result.returncode != 0 and name in result.stdout
    assert 'postconditions satisfied' not in result.stdout


def test_final_postcondition_hash_failure_propagates_without_success(tmp_path):
    make_final_postcondition_files(tmp_path)
    bin_dir = tmp_path / 'mock-bin'; bin_dir.mkdir(); tool = bin_dir / 'sha256sum'
    tool.write_text('#!/bin/bash\nprintf "synthetic hash failure\\n" >&2\nexit 86\n'); tool.chmod(0o700)
    result = run_final_postcondition_shell(tmp_path, str(bin_dir))
    assert result.returncode == 86 and result.stdout == ''
    assert result.stderr == 'synthetic hash failure\n'


def test_final_postcondition_keeps_completion_barrier_and_all_inventories(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})



# ---------------------------------------------------------------------------
# R33 publication declarations: 26 named files plus one candidate-tree pattern.
# A source-selected tree is neither an acquired archive nor observed members.
# ---------------------------------------------------------------------------
RECORDED_PUBLICATION_ROLES = (*FINAL_POSTCONDITION_ROLES,
    'self-contained-evidence-floor', 'recorded-release-candidate-envelopes')


def recorded_publication_method(side):
    if side == 'builder':
        return BUILDER, BUILDER._recorded_publication_source_projection
    return PLAN_CHECKER, PLAN_CHECKER._source_recorded_publication_expectations


def recorded_publication_source_paths():
    rows = mapping_source_document()['jobs']['release_grade_recorded_path']['steps']
    matches = [(i, row) for i, row in enumerate(rows, 1)
               if row.get('name') == 'Upload release-grade recorded path artifacts']
    assert [i for i, _ in matches] == [33]
    return matches[0][1]['with']['path'].splitlines()


@pytest.mark.parametrize('role', RECORDED_PUBLICATION_ROLES)
def test_recorded_publication_each_input_has_reciprocal_source_binding(source_fixture, role):
    states, steps = provenance_rows(source_fixture.plan)
    state, publication = states[role], steps[('release_grade_recorded_path', 33)]
    selector = state['path_or_uri'] + ('**' if role == 'recorded-release-candidate-envelopes' else '')
    assert selector in recorded_publication_source_paths()
    assert state['state_id'] in publication['input_state_ids']
    assert publication['occurrence_id'] in state['required_consumer_occurrence_ids']
    assert publication['output_state_ids'] == []
    assert state['producer_occurrence_id'] != publication['occurrence_id']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_recorded_publication_separates_named_files_tree_and_unmodeled_remainder(recorded_source_objects, side):
    module, method = recorded_publication_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    paths = recorded_publication_source_paths()
    assert facts['ordered_selectors'] == paths and len(paths) == 27
    assert facts['exact_file_selectors'] == [p for p in paths if not p.endswith('/**')]
    assert len(facts['exact_file_selectors']) == 26
    tree = reviewed_literal_default(RECORDED_SOURCE_TOOLS[0], '--out-dir') + '/'
    assert facts['tree_selectors'] == [tree + '**']
    assert facts['locators']['recorded-release-candidate-envelopes'] == tree
    assert facts['role_selectors']['recorded-release-candidate-envelopes'] == tree + '**'
    assert len(facts['locators']) == 23
    assert facts['unmodeled_file_selectors'] == sorted('PULSE_safe_pack_v0/artifacts/' + p
                                                      for p in FINAL_POSTCONDITION_UNMODELED)
    assert facts['publication_only_roles'] == ['recorded-release-candidate-envelopes', 'self-contained-evidence-floor']
    assert facts['artifact_name_template'] == 'release-grade-recorded-path-${{ github.run_id }}-${{ github.run_attempt }}'
    assert facts['action_uses'] == mapping_source_document()['jobs']['release_grade_recorded_path']['steps'][32]['uses']
    assert facts['if_no_files_found'] == 'error' and facts['retention_days'] == 30
    assert facts['read_basis'] == 'source_declared_publication_input'
    assert facts['observed_read_receipt'] is facts['archive_membership_observed'] is facts['semantic_content_admission'] is False
    assert not {'artifact_id', 'artifact_digest', 'observed_members', 'archive_members'} & set(facts)
    assert facts['steps'] == {module._step_id('release_grade_recorded_path', 33): {
        'inputs': sorted(RECORDED_PUBLICATION_ROLES), 'outputs': []}}
    assert facts['origins']['self-contained-evidence-floor'] == module._step_id('pulse', 18)
    assert facts['origins']['recorded-release-candidate-envelopes'] == module._step_id('release_grade_recorded_path', 6)


def test_recorded_publication_checker_source_predicate_precedes_constructor_equality(source_fixture, recorded_source_objects):
    document = mapping_source_document()
    expected = BUILDER._recorded_publication_source_projection(document, recorded_source_objects)
    with patch.object(BUILDER, '_recorded_publication_source_projection', side_effect=AssertionError('builder forbidden')):
        actual = PLAN_CHECKER._source_recorded_publication_expectations(document, recorded_source_objects)
        PLAN_CHECKER._verify_source_recorded_publication_equations(source_fixture.plan, document, recorded_source_objects)
    assert canonical(expected) == canonical(actual)
    calls = {n.func.id: n.lineno for n in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(PLAN_CHECKER.check_plan))))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert calls['_verify_source_recorded_publication_equations'] < calls['_reconstruct_expected_plan']


def corrupt_recorded_publication_plan(original, fault):
    plan = copy.deepcopy(original)
    states, steps = provenance_rows(plan)
    reader = steps[('release_grade_recorded_path', 33)]; oid = reader['occurrence_id']
    if ':' in fault:
        operation, role = fault.split(':', 1)
        state = states[role]; sid = state['state_id']
        if operation == 'omit':
            reader['input_state_ids'].remove(sid); state['required_consumer_occurrence_ids'].remove(oid)
        elif operation == 'invent':
            reader['input_state_ids'] = sorted(set(reader['input_state_ids']) | {sid})
            state['required_consumer_occurrence_ids'] = sorted(set(state['required_consumer_occurrence_ids']) | {oid})
        elif operation == 'reverse': state['required_consumer_occurrence_ids'].remove(oid)
        else: raise AssertionError(fault)
    elif fault == 'locator': states['quality-ledger-final']['path_or_uri'] += '#pre-authority-insertion'
    elif fault == 'tree_locator': states['recorded-release-candidate-envelopes']['path_or_uri'] += '**'
    elif fault == 'origin': states['self-contained-evidence-floor']['producer_occurrence_id'] = oid
    elif fault == 'writer': reader['output_state_ids'] = [states['final-status']['state_id']]
    elif fault == 'required': states['recorded-release-candidate-envelopes']['required'] = False
    elif fault == 'content': states['recorded-release-candidate-envelopes']['content_requirement'] = 'metadata_only'
    elif fault == 'authority': states['release-grade-junit']['authority_bearing'] = True
    elif fault == 'mutation': states['final-status']['mutation_class'] = 'none'
    elif fault == 'missing_role': plan['state_templates'].remove(states['status-baseline'])
    elif fault == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(states['status-baseline']))
    elif fault == 'missing_step':
        for job in plan['jobs']: job['steps'] = [s for s in job['steps'] if s['occurrence_id'] != oid]
    elif fault == 'duplicate_step':
        for job in plan['jobs']:
            if reader in job['steps']: job['steps'].append(copy.deepcopy(reader)); break
    else: raise AssertionError(fault)
    return plan


@pytest.mark.parametrize('fault,code', [
    ('omit:final-status', 'step_io'), ('omit:quality-ledger-final', 'step_io'),
    ('omit:llamaguard-summary', 'step_io'), ('omit:self-contained-evidence-floor', 'step_io'),
    ('omit:recorded-release-candidate-envelopes', 'step_io'),
    ('invent:pre-materialization-status', 'step_io'), ('invent:quality-ledger-pre-authority', 'step_io'),
    ('invent:release-authority-audit-bundle', 'step_io'), ('invent:advisory-reference-bundle', 'step_io'),
    ('invent:gate-policy', 'step_io'), ('invent:materialized-release-required-gate-set', 'step_io'),
    ('reverse:release-grade-junit', 'reverse_inputs'), ('reverse:self-contained-evidence-floor', 'reverse_inputs'),
    ('locator', 'locator'), ('tree_locator', 'locator'), ('origin', 'origin'), ('writer', 'writer'),
    ('required', 'duty'), ('content', 'duty'), ('authority', 'duty'), ('mutation', 'duty'),
    ('missing_role', 'role_missing'), ('duplicate_role', 'duplicate_role'),
    ('missing_step', 'step_missing'), ('duplicate_step', 'duplicate_step'),
])
def test_recorded_publication_rejects_false_inputs_and_weakened_duties(source_fixture, recorded_source_objects, fault, code):
    bad = corrupt_recorded_publication_plan(source_fixture.plan, fault)
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_publication_' + code):
        PLAN_CHECKER._verify_source_recorded_publication_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault', ['omit:self-contained-evidence-floor', 'omit:recorded-release-candidate-envelopes',
                                   'invent:release-authority-audit-bundle'])
def test_recorded_publication_equal_false_constructors_still_rejected(source_fixture, recorded_source_objects, fault):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        document = mapping_source_document(); jobs, steps, _ = module._build_jobs(document)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
        answers.append(canonical(corrupt_recorded_publication_plan(plan, fault)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_publication_step_io_mismatch'):
        PLAN_CHECKER._verify_source_recorded_publication_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault,code', [
    ('omit:self-contained-evidence-floor', 'recorded_publication_step_io_mismatch'),
    ('omit:final-status-summary', 'recorded_publication_step_io_mismatch'),
    ('omit:recorded-release-candidate-envelopes', 'recorded_mapping_new_role_consumer_mismatch'),
    ('invent:pre-materialization-status', 'recorded_mapping_new_role_consumer_mismatch'),
])
def test_recorded_publication_rehashed_false_plan_fails_real_checker(source_fixture, tmp_path, fault, code):
    raw = canonical(corrupt_recorded_publication_plan(source_fixture.plan, fault))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-publication-plan.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == code


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'path', 'bytes'])
def test_recorded_publication_rejects_missing_or_rehashed_source(recorded_source_objects, side, fault):
    module, method = recorded_publication_method(side); objects = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del objects[path]
    elif fault == 'path': objects[path] = replace(objects[path], path='different/workflow.yml')
    else:
        data = objects[path].data.replace(b'recorded_release_candidates/**', b'recorded_release_candidates/*')
        assert data != objects[path].data
        objects[path] = replace(objects[path], data=data,
            blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    with pytest.raises(module.PlanError, match='recorded_publication_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing_unmodeled', 'wildcard', 'audit_tree', 'name', 'condition',
                                  'action', 'retention', 'error_mode', 'duplicate', 'reorder'])
def test_recorded_publication_rejects_logical_selector_drift(recorded_source_objects, side, fault):
    module, method = recorded_publication_method(side); document = mapping_source_document()
    step = document['jobs']['release_grade_recorded_path']['steps'][32]; options = step['with']
    if fault == 'missing_unmodeled': options['path'] = options['path'].replace('PULSE_safe_pack_v0/artifacts/status_summary.md\n', '')
    elif fault == 'wildcard': options['path'] = options['path'].replace('/**', '/*')
    elif fault == 'audit_tree': options['path'] = options['path'].replace('recorded_release_candidates/**', 'release_authority_audit_bundle/**')
    elif fault == 'name': options['name'] = 'release-grade-recorded-path-latest'
    elif fault == 'condition': step['if'] = 'always()'
    elif fault == 'action': step['uses'] = 'actions/upload-artifact@v7'
    elif fault == 'retention': options['retention-days'] = '1'
    elif fault == 'error_mode': options['if-no-files-found'] = 'ignore'
    elif fault == 'duplicate': options['path'] += 'PULSE_safe_pack_v0/artifacts/status.json\n'
    else: options['path'] = '\n'.join(reversed(options['path'].splitlines())) + '\n'
    with pytest.raises(module.PlanError, match='recorded_publication_workflow_drift'):
        method(document, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_recorded_publication_only_r33_inputs_and_inverse_links_change(recorded_source_objects, side):
    module, _ = recorded_publication_method(side); document = mapping_source_document()
    _, before_steps, _ = module._build_jobs(document)
    with patch.object(module, '_install_recorded_publication_projection', return_value=None):
        before_states = module._build_states(before_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    _, after_steps, _ = module._build_jobs(document)
    after_states = module._build_states(after_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    oid = module._step_id('release_grade_recorded_path', 33)
    assert len(before_states) == len(after_states) == 62
    additions = 0
    for a, b in zip(before_states, after_states):
        before, after = copy.deepcopy(a), copy.deepcopy(b)
        additions += int(oid not in before['required_consumer_occurrence_ids'] and oid in after['required_consumer_occurrence_ids'])
        for row in (before, after): row['required_consumer_occurrence_ids'] = [r for r in row['required_consumer_occurrence_ids'] if r != oid]
        assert before == after
    assert additions == 20
    for key in after_steps:
        if key != ('release_grade_recorded_path', 33): assert before_steps[key] == after_steps[key]
        else:
            before, after = copy.deepcopy(before_steps[key]), copy.deepcopy(after_steps[key])
            assert set(before['input_state_ids']) <= set(after['input_state_ids'])
            assert len(after['input_state_ids']) - len(before['input_state_ids']) == 22
            before.pop('input_state_ids'); after.pop('input_state_ids'); assert before == after


@pytest.mark.parametrize('ordinal', [26, 32])
def test_recorded_publication_candidate_reader_closure_still_rejects_arbitrary_consumers(source_fixture, recorded_source_objects, ordinal):
    plan = copy.deepcopy(source_fixture.plan); states, steps = provenance_rows(plan)
    role = states['recorded-release-candidate-envelopes']; wrong = steps[('release_grade_recorded_path', ordinal)]
    wrong['input_state_ids'] = sorted(set(wrong['input_state_ids']) | {role['state_id']})
    role['required_consumer_occurrence_ids'] = sorted(set(role['required_consumer_occurrence_ids']) | {wrong['occurrence_id']})
    with pytest.raises(PLAN_CHECKER.PlanError, match='recorded_mapping_new_role_consumer_mismatch'):
        PLAN_CHECKER._verify_source_recorded_equations(plan, mapping_source_document(), recorded_source_objects)


def test_recorded_publication_keeps_r26_hash_extent_distinct(source_fixture):
    states, steps = provenance_rows(source_fixture.plan)
    r26, r33 = steps[('release_grade_recorded_path', 26)], steps[('release_grade_recorded_path', 33)]
    assert set(r33['input_state_ids']) - set(r26['input_state_ids']) == {
        states['self-contained-evidence-floor']['state_id'], states['recorded-release-candidate-envelopes']['state_id']}
    assert set(r26['input_state_ids']) <= set(r33['input_state_ids'])
    assert states['release-authority-audit-bundle']['state_id'] not in r33['input_state_ids']
    assert len(r26['input_state_ids']) == 21 and len(r33['input_state_ids']) == 23


def test_recorded_publication_keeps_runtime_intake_and_completion_unfinished(source_fixture):
    assert len(source_fixture.plan['state_templates']) == 62
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert 'evidence_profile' not in source_fixture.plan
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    packet = runtime_projection_example(source_fixture)
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, packet, {})
    state = next(row for row in packet['state_observations']
                 if row['state_id'] == 'state:step5c:recorded-release-candidate-envelopes')
    assert state['content_status'] == 'unavailable'
    assert state['sha256'] is None and state['size_bytes'] is None


# R27/R30 literal-file publications are source declarations, not new authority.
_AUTHORITY_PUBLICATION_INPUTS = [
    (27, 'release-authority-manifest'),
    (30, 'final-status'),
    (30, 'release-decision'),
    (30, 'release-decision-ledger-section'),
    (30, 'release-decision-report'),
]


def authority_publication_method(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    method = (module._authority_publication_source_projection if side == 'builder'
              else module._source_authority_publication_expectations)
    return module, method


@pytest.mark.parametrize('ordinal,role', _AUTHORITY_PUBLICATION_INPUTS)
def test_authority_publication_has_each_literal_file_input(source_fixture, ordinal, role):
    states, steps = provenance_rows(source_fixture.plan)
    step = steps[('release_grade_recorded_path', ordinal)]
    assert states[role]['state_id'] in step['input_state_ids']
    assert step['occurrence_id'] in states[role]['required_consumer_occurrence_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_authority_publication_matches_the_exact_source_files(recorded_source_objects, side):
    module, method = authority_publication_method(side)
    doc = mapping_source_document(); facts = method(doc, recorded_source_objects)
    prefix = 'PULSE_safe_pack_v0/artifacts/'
    expected = {27: [prefix + 'release_authority_v0.json'],
                30: [prefix + name for name in ['status.json', 'release_decision_v0.json',
                    'release_decision_v0_ledger_section.html', 'report_card.with_release_decision.html']]}
    assert set(facts['locators']) == {role for _, role in _AUTHORITY_PUBLICATION_INPUTS}
    assert facts['unmodeled_file_selectors'] == []
    assert facts['observed_read_receipt'] is False
    assert facts['archive_membership_observed'] is False
    assert facts['semantic_content_admission'] is False
    assert facts['read_basis'] == 'source_declared_publication_input'
    for ordinal, paths in expected.items():
        oid = module._step_id('release_grade_recorded_path', ordinal)
        published = facts['publications'][oid]
        raw = doc['jobs']['release_grade_recorded_path']['steps'][ordinal - 1]
        assert published['ordered_file_selectors'] == paths == raw['with']['path'].splitlines()
        assert published['action_uses'] == raw['uses']
        assert published['artifact_name'] == raw['with']['name']
        assert published['if_no_files_found'] == 'error'
        assert published['retention_days'] == 30
        assert facts['steps'][oid] == {'inputs': sorted(role for pos, role in _AUTHORITY_PUBLICATION_INPUTS
                                                       if pos == ordinal), 'outputs': []}
    assert facts['origins'] == {role: module._step_id('release_grade_recorded_path', ordinal)
        for role, ordinal in [('final-status', 9), ('release-decision', 15),
            ('release-decision-ledger-section', 16), ('release-authority-manifest', 17),
            ('release-decision-report', 19)]}


def test_authority_publication_separate_source_extractors_agree(recorded_source_objects):
    answers = [method(mapping_source_document(), recorded_source_objects)
               for _, method in map(authority_publication_method, ['builder', 'checker'])]
    assert canonical(answers[0]) == canonical(answers[1])


def corrupt_authority_publication_plan(original, fault):
    plan = copy.deepcopy(original); states, steps = provenance_rows(plan)
    r27, r30 = [steps[('release_grade_recorded_path', i)] for i in (27, 30)]
    def relation(row, role, present):
        state = states[role]; sid, oid = state['state_id'], row['occurrence_id']
        row['input_state_ids'] = sorted((set(row['input_state_ids']) | {sid}) if present
                                       else (set(row['input_state_ids']) - {sid}))
        state['required_consumer_occurrence_ids'] = sorted(
            (set(state['required_consumer_occurrence_ids']) | {oid}) if present
            else (set(state['required_consumer_occurrence_ids']) - {oid}))
    if fault.startswith('omit:'):
        _, pos, role = fault.split(':'); relation(steps[('release_grade_recorded_path', int(pos))], role, False)
    elif fault.startswith('invent:'): relation(r30, fault.split(':', 1)[1], True)
    elif fault == 'swap_publications':
        relation(r27, 'release-authority-manifest', False); relation(r27, 'release-decision', True)
        relation(r30, 'release-decision', False); relation(r30, 'release-authority-manifest', True)
    elif fault == 'reverse':
        states['release-decision-report']['required_consumer_occurrence_ids'].remove(r30['occurrence_id'])
    elif fault == 'duplicate_input': r30['input_state_ids'].append(states['release-decision']['state_id'])
    elif fault == 'order': r30['input_state_ids'].reverse()
    elif fault == 'locator': states['release-decision-report']['path_or_uri'] = 'PULSE_safe_pack_v0/artifacts/report_card.html'
    elif fault == 'origin': states['release-authority-manifest']['producer_occurrence_id'] = r27['occurrence_id']
    elif fault == 'writer': r27['output_state_ids'].append(states['release-authority-manifest']['state_id'])
    elif fault == 'required': states['release-decision']['required'] = False
    elif fault == 'content': states['release-decision']['content_requirement'] = 'metadata_only'
    elif fault == 'authority': states['release-decision']['authority_bearing'] = False
    elif fault == 'mutation': states['final-status']['mutation_class'] = 'none'
    elif fault == 'missing_role': plan['state_templates'].remove(states['release-decision-report'])
    elif fault == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(states['release-decision']))
    elif fault == 'missing_step':
        for job in plan['jobs']: job['steps'] = [s for s in job['steps'] if s['occurrence_id'] != r27['occurrence_id']]
    elif fault == 'duplicate_step':
        job = next(j for j in plan['jobs'] if r27 in j['steps']); job['steps'].append(copy.deepcopy(r27))
    else: raise AssertionError(fault)
    return plan


@pytest.mark.parametrize('fault,code', [
    ('omit:27:release-authority-manifest', 'step_io'),
    ('omit:30:final-status', 'step_io'), ('omit:30:release-decision', 'step_io'),
    ('omit:30:release-decision-ledger-section', 'step_io'), ('omit:30:release-decision-report', 'step_io'),
    ('invent:pre-materialization-status', 'step_io'), ('invent:quality-ledger-final', 'step_io'),
    ('invent:quality-ledger-pre-authority', 'step_io'), ('invent:artifact-provenance-binding', 'step_io'),
    ('invent:gate-policy', 'step_io'), ('swap_publications', 'step_io'),
    ('reverse', 'reverse_inputs'), ('duplicate_input', 'step_io'), ('order', 'step_io'),
    ('locator', 'locator'), ('origin', 'origin'), ('writer', 'writer'),
    ('required', 'duty'), ('content', 'duty'), ('authority', 'duty'), ('mutation', 'duty'),
    ('missing_role', 'role_missing'), ('duplicate_role', 'duplicate_role'),
    ('missing_step', 'step_missing'), ('duplicate_step', 'duplicate_step'),
])
def test_authority_publication_rejects_false_supplied_edges(source_fixture, recorded_source_objects, fault, code):
    bad = corrupt_authority_publication_plan(source_fixture.plan, fault)
    with pytest.raises(PLAN_CHECKER.PlanError, match='authority_publication_' + code):
        PLAN_CHECKER._verify_source_authority_publication_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault', ['omit:27:release-authority-manifest',
                                   'omit:30:release-decision-report', 'swap_publications'])
def test_authority_publication_equal_wrong_constructors_are_not_sufficient(source_fixture, recorded_source_objects, fault):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        document = mapping_source_document(); jobs, steps, _ = module._build_jobs(document)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
        answers.append(canonical(corrupt_authority_publication_plan(plan, fault)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='authority_publication_step_io_mismatch'):
        PLAN_CHECKER._verify_source_authority_publication_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault,code', [
    ('omit:27:release-authority-manifest', 'authority_publication_step_io_mismatch'),
    ('omit:30:release-decision-report', 'authority_publication_step_io_mismatch'),
    ('invent:artifact-provenance-binding', 'provenance_mapping_consumers_mismatch'),
    ('swap_publications', 'authority_publication_step_io_mismatch'),
])
def test_authority_publication_rehashed_false_plan_fails_real_checker(source_fixture, tmp_path, fault, code):
    raw = canonical(corrupt_authority_publication_plan(source_fixture.plan, fault))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-authority-publication.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == code


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'wrong_path', 'rehashed_bytes'])
def test_authority_publication_rejects_changed_workflow_bytes(recorded_source_objects, side, fault):
    module, method = authority_publication_method(side); objects = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del objects[path]
    elif fault == 'wrong_path': objects[path] = replace(objects[path], path='other/pulse_ci.yml')
    else:
        data = objects[path].data + b'\n# Unreviewed workflow bytes.\n'
        objects[path] = replace(objects[path], data=data,
            blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    with pytest.raises(module.PlanError, match='authority_publication_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['name', 'action', 'condition', 'retention', 'error_mode',
                                   'omit_file', 'duplicate_file', 'reorder', 'wildcard', 'wrong_version'])
def test_authority_publication_rejects_logical_workflow_drift(recorded_source_objects, side, fault):
    module, method = authority_publication_method(side); doc = mapping_source_document()
    row = doc['jobs']['release_grade_recorded_path']['steps'][29]; options = row['with']
    if fault == 'name': options['name'] = 'release-decision-latest'
    elif fault == 'action': row['uses'] = 'actions/upload-artifact@v7'
    elif fault == 'condition': row['if'] = 'always()'
    elif fault == 'retention': options['retention-days'] = '1'
    elif fault == 'error_mode': options['if-no-files-found'] = 'ignore'
    elif fault == 'omit_file': options['path'] = '\n'.join(options['path'].splitlines()[1:]) + '\n'
    elif fault == 'duplicate_file': options['path'] += options['path'].splitlines()[0] + '\n'
    elif fault == 'reorder': options['path'] = '\n'.join(reversed(options['path'].splitlines())) + '\n'
    elif fault == 'wildcard': options['path'] = 'PULSE_safe_pack_v0/artifacts/**'
    else: options['path'] = options['path'].replace('report_card.with_release_decision.html', 'report_card.html')
    with pytest.raises(module.PlanError, match='authority_publication_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_authority_publication_changes_only_two_input_sets_and_three_reader_links(recorded_source_objects, side):
    module, _ = authority_publication_method(side); document = mapping_source_document()
    _, before_steps, _ = module._build_jobs(document)
    with patch.object(module, '_install_authority_publication_projection', return_value=None):
        before_states = module._build_states(before_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    _, after_steps, _ = module._build_jobs(document)
    after_states = module._build_states(after_steps, module.EXPECTED_CASE_IDS, document, recorded_source_objects)
    controlled = {module._step_id('release_grade_recorded_path', pos) for pos in (27, 30)}
    forward = reverse = 0
    for a, b in zip(before_states, after_states, strict=True):
        a, b = copy.deepcopy(a), copy.deepcopy(b)
        assert set(a['required_consumer_occurrence_ids']) <= set(b['required_consumer_occurrence_ids'])
        reverse += len(set(b['required_consumer_occurrence_ids']) - set(a['required_consumer_occurrence_ids']))
        for row in (a, b): row['required_consumer_occurrence_ids'] = [x for x in row['required_consumer_occurrence_ids'] if x not in controlled]
        assert a == b
    for key in before_steps:
        a, b = copy.deepcopy(before_steps[key]), copy.deepcopy(after_steps[key])
        if a['occurrence_id'] in controlled:
            assert a['input_state_ids'] == []
            forward += len(b['input_state_ids'])
            a.pop('input_state_ids'); b.pop('input_state_ids')
        assert a == b
    assert forward == 5 and reverse == 3
    assert len(before_states) == len(after_states) == 62


def test_authority_publication_keeps_other_selectors_and_runtime_boundary(source_fixture, recorded_source_objects):
    states, steps = provenance_rows(source_fixture.plan)
    for pos in (27, 30):
        step = steps[('release_grade_recorded_path', pos)]
        assert step['output_state_ids'] == []
        assert states['artifact-provenance-binding']['state_id'] not in step['input_state_ids']
        assert states['gate-policy']['state_id'] not in step['input_state_ids']
    r33 = PLAN_CHECKER._source_recorded_publication_expectations(mapping_source_document(), recorded_source_objects)
    assert len(r33['ordered_selectors']) == 27 and len(r33['unmodeled_file_selectors']) == 4
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    assert 'evidence_profile' not in source_fixture.plan
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


# R31: selected physical roles under artifacts/**, not observed glob membership.
_REPORT_PUBLICATION_ROLES = [
    'artifact-provenance-binding', 'final-status', 'final-status-summary',
    'llamaguard-attestation-bundle', 'llamaguard-attestation-envelope',
    'llamaguard-attestation-verifier', 'llamaguard-evaluator-manifest',
    'llamaguard-raw-evidence', 'llamaguard-summary', 'quality-ledger-final',
    'recorded-candidate-index', 'recorded-release-candidate-envelopes',
    'recorded-release-evidence-verifier', 'release-authority-audit-bundle',
    'release-authority-manifest', 'release-decision', 'release-decision-ledger-section',
    'release-decision-report', 'release-evidence-input-manifest', 'release-grade-junit',
    'release-grade-sarif', 'required-gate-evidence', 'self-contained-evidence-floor',
    'status-baseline',
]


def report_publication_method(side):
    module = BUILDER if side == 'builder' else PLAN_CHECKER
    method = (module._report_publication_source_projection if side == 'builder'
              else module._source_report_publication_expectations)
    return module, method


@pytest.mark.parametrize('role', _REPORT_PUBLICATION_ROLES)
def test_report_publication_has_each_selected_physical_input(source_fixture, role):
    states, steps = provenance_rows(source_fixture.plan)
    row = steps[('release_grade_recorded_path', 31)]
    assert states[role]['state_id'] in row['input_state_ids']
    assert row['occurrence_id'] in states[role]['required_consumer_occurrence_ids']


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_report_publication_preserves_four_selectors_and_unresolved_membership(recorded_source_objects, side):
    module, method = report_publication_method(side)
    facts = method(mapping_source_document(), recorded_source_objects)
    tree = 'PULSE_safe_pack_v0/artifacts/**'
    assert facts['ordered_selectors'] == [tree, 'badges/*.svg', 'reports/junit.xml', 'reports/sarif.json']
    assert facts['artifact_name'] == 'pulse-report'
    assert facts['artifact_tree_root'] == 'PULSE_safe_pack_v0/artifacts/'
    assert facts['action_uses'] == 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a'
    assert facts['if_no_files_found'] == 'error' and facts['retention_days'] == 30
    assert sorted(facts['locators']) == _REPORT_PUBLICATION_ROLES
    assert facts['tree_roles'] == ['recorded-release-candidate-envelopes', 'release-authority-audit-bundle']
    assert sum(not path.endswith('/') for path in facts['locators'].values()) == 22
    assert set(facts['role_selectors'].values()) == {tree}
    assert facts['unmodeled_literal_selectors'] == ['reports/junit.xml', 'reports/sarif.json']
    assert facts['unmodeled_pattern_selectors'] == ['badges/*.svg']
    assert facts['known_unmodeled_artifact_paths'] == ['PULSE_safe_pack_v0/artifacts/' + name for name in
        ['refusal_delta_summary.json', 'status_summary.md', 'status_summary_baseline.json', 'status_summary_baseline.md']]
    assert facts['locators']['release-grade-junit'] == 'PULSE_safe_pack_v0/artifacts/reports/junit.xml'
    assert facts['locators']['release-grade-sarif'] == 'PULSE_safe_pack_v0/artifacts/reports/sarif.json'
    assert not set(facts['root_report_selectors']) & set(facts['locators'].values())
    for field in ('tree_membership_enumerated', 'selected_roles_exhaust_source_tree',
                  'archive_membership_observed', 'observed_read_receipt', 'semantic_content_admission'):
        assert facts[field] is False
    assert facts['read_basis'] == 'source_declared_publication_input'
    assert facts['steps'] == {module._step_id('release_grade_recorded_path', 31):
                              {'inputs': _REPORT_PUBLICATION_ROLES, 'outputs': []}}


def test_report_publication_separate_source_extractors_agree(recorded_source_objects):
    answers = [method(mapping_source_document(), recorded_source_objects)
               for _, method in map(report_publication_method, ['builder', 'checker'])]
    assert canonical(answers[0]) == canonical(answers[1])


@pytest.mark.parametrize('locator,expected', [
    ('PULSE_safe_pack_v0/artifacts/status.json', True),
    ('PULSE_safe_pack_v0/artifacts/reports/junit.xml', True),
    ('PULSE_safe_pack_v0/artifacts/recorded_release_candidates/', True),
    ('PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/', True),
    ('reports/junit.xml', False), ('reports/sarif.json', False),
    ('PULSE_safe_pack_v0/artifacts-other/status.json', False),
    ('PULSE_safe_pack_v0/artifacts/status.json#pre-release-required-materialization', False),
    ('PULSE_safe_pack_v0/artifacts/report_card.html#pre-authority-insertion', False),
    ('PULSE_safe_pack_v0/artifacts/../profiles/policy.yaml', False),
    ('PULSE_safe_pack_v0/artifacts//status.json', False),
    ('PULSE_safe_pack_v0/artifacts/.hidden/file.json', False),
    ('PULSE_safe_pack_v0/artifacts/**', False),
    ('PULSE_safe_pack_v0/artifacts/', False),
    ('${RUNNER_TEMP}/release-grade-reference-run-v0/', False),
    ('artifact://llamaguard_raw.jsonl#example/classification', False),
])
def test_report_publication_lexical_join_does_not_strip_versions_or_cross_roots(locator, expected):
    for module in (BUILDER, PLAN_CHECKER):
        assert module._report_publication_covers_locator('PULSE_safe_pack_v0/artifacts/', locator) is expected
        assert module._report_publication_covers_locator('PULSE_safe_pack_v0/artifacts', locator) is False


def corrupt_report_publication_plan(original, fault):
    plan = copy.deepcopy(original); states, steps = provenance_rows(plan)
    row = steps[('release_grade_recorded_path', 31)]; oid = row['occurrence_id']
    def relation(role, present):
        state = states[role]; sid = state['state_id']
        row['input_state_ids'] = sorted((set(row['input_state_ids']) | {sid}) if present
                                       else (set(row['input_state_ids']) - {sid}))
        state['required_consumer_occurrence_ids'] = sorted(
            (set(state['required_consumer_occurrence_ids']) | {oid}) if present
            else (set(state['required_consumer_occurrence_ids']) - {oid}))
    if fault.startswith('omit:'): relation(fault.split(':', 1)[1], False)
    elif fault.startswith('invent:'): relation(fault.split(':', 1)[1], True)
    elif fault == 'reverse': states['final-status-summary']['required_consumer_occurrence_ids'].remove(oid)
    elif fault == 'duplicate_input': row['input_state_ids'].append(row['input_state_ids'][0])
    elif fault == 'order': row['input_state_ids'].reverse()
    elif fault == 'root_junit_alias': states['release-grade-junit']['path_or_uri'] = 'reports/junit.xml'
    elif fault == 'root_sarif_alias': states['release-grade-sarif']['path_or_uri'] = 'reports/sarif.json'
    elif fault == 'origin': states['release-decision-report']['producer_occurrence_id'] = oid
    elif fault == 'writer': row['output_state_ids'].append(states['release-decision-report']['state_id'])
    elif fault == 'required': states['final-status-summary']['required'] = False
    elif fault == 'content': states['final-status-summary']['content_requirement'] = 'metadata_only'
    elif fault == 'authority': states['final-status-summary']['authority_bearing'] = False
    elif fault == 'mutation': states['final-status']['mutation_class'] = 'none'
    elif fault == 'missing_role': plan['state_templates'].remove(states['final-status-summary'])
    elif fault == 'duplicate_role': plan['state_templates'].append(copy.deepcopy(states['final-status-summary']))
    elif fault == 'missing_step':
        for job in plan['jobs']: job['steps'] = [s for s in job['steps'] if s['occurrence_id'] != oid]
    elif fault == 'duplicate_step':
        job = next(j for j in plan['jobs'] if row in j['steps']); job['steps'].append(copy.deepcopy(row))
    else: raise AssertionError(fault)
    return plan


@pytest.mark.parametrize('fault,code', [
    ('omit:final-status', 'step_io'), ('omit:self-contained-evidence-floor', 'step_io'),
    ('omit:artifact-provenance-binding', 'step_io'), ('omit:recorded-release-candidate-envelopes', 'step_io'),
    ('omit:release-authority-audit-bundle', 'step_io'), ('omit:release-grade-junit', 'step_io'),
    ('invent:pre-materialization-status', 'step_io'), ('invent:quality-ledger-pre-authority', 'step_io'),
    ('invent:advisory-reference-bundle', 'step_io'), ('invent:materialized-release-required-gate-set', 'step_io'),
    ('invent:effective-required-argument-list', 'step_io'),
    ('invent:llamaguard-output:benign_factual_response', 'step_io'),
    ('reverse', 'reverse_inputs'), ('duplicate_input', 'step_io'), ('order', 'step_io'),
    ('root_junit_alias', 'locator'), ('root_sarif_alias', 'locator'), ('origin', 'origin'), ('writer', 'writer'),
    ('required', 'duty'), ('content', 'duty'), ('authority', 'duty'), ('mutation', 'duty'),
    ('missing_role', 'role_missing'), ('duplicate_role', 'duplicate_role'),
    ('missing_step', 'step_missing'), ('duplicate_step', 'duplicate_step'),
])
def test_report_publication_rejects_false_submitted_relations(source_fixture, recorded_source_objects, fault, code):
    bad = corrupt_report_publication_plan(source_fixture.plan, fault)
    with pytest.raises(PLAN_CHECKER.PlanError, match='report_publication_' + code):
        PLAN_CHECKER._verify_source_report_publication_equations(bad, mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault', ['omit:final-status', 'omit:self-contained-evidence-floor', 'root_junit_alias'])
def test_report_publication_equal_false_constructors_are_insufficient(source_fixture, recorded_source_objects, fault):
    answers = []
    for module in (BUILDER, PLAN_CHECKER):
        doc = mapping_source_document(); jobs, steps, _ = module._build_jobs(doc)
        plan = copy.deepcopy(source_fixture.plan); plan['jobs'] = jobs
        plan['state_templates'] = module._build_states(steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
        answers.append(canonical(corrupt_report_publication_plan(plan, fault)))
    assert answers[0] == answers[1]
    with pytest.raises(PLAN_CHECKER.PlanError, match='report_publication_'):
        PLAN_CHECKER._verify_source_report_publication_equations(json.loads(answers[0]), mapping_source_document(), recorded_source_objects)


@pytest.mark.parametrize('fault,code', [
    ('omit:self-contained-evidence-floor', 'report_publication_step_io_mismatch'),
    ('omit:final-status-summary', 'report_publication_step_io_mismatch'),
    ('omit:artifact-provenance-binding', 'provenance_mapping_consumers_mismatch'),
    ('omit:recorded-release-candidate-envelopes', 'recorded_mapping_new_role_consumer_mismatch'),
])
def test_report_publication_rehashed_false_plan_fails_real_checker(source_fixture, tmp_path, fault, code):
    raw = canonical(corrupt_report_publication_plan(source_fixture.plan, fault))
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(json.loads(raw))
    path = tmp_path / 'false-report-publication.json'; path.write_bytes(raw)
    result = cli(source_fixture.root, TOOL_NAMES[1], ['--repository-root', source_fixture.root,
        '--plan', path, '--expected-source-commit', source_fixture.sha, '--expected-plan-sha256', digest(raw),
        '--expected-record-status', 'example'])
    assert result.returncode != 0
    assert json.loads(result.stdout)['error_code'] == code


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['missing', 'wrong_path', 'rehashed_bytes'])
def test_report_publication_rejects_unreviewed_workflow_source(recorded_source_objects, side, fault):
    module, method = report_publication_method(side); objects = dict(recorded_source_objects)
    path = module.SUBJECT_WORKFLOW_PATH
    if fault == 'missing': del objects[path]
    elif fault == 'wrong_path': objects[path] = replace(objects[path], path='other/pulse_ci.yml')
    else:
        data = objects[path].data + b'\n# Not reviewed.\n'
        objects[path] = replace(objects[path], data=data,
            blob_sha1=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
    with pytest.raises(module.PlanError, match='report_publication_source_'):
        method(mapping_source_document(), objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
@pytest.mark.parametrize('fault', ['source_root', 'recursive_pattern', 'badge_pattern', 'root_report',
                                   'name', 'action', 'omit_selector', 'duplicate_selector'])
def test_report_publication_rejects_logical_selector_drift(recorded_source_objects, side, fault):
    module, method = report_publication_method(side); doc = mapping_source_document()
    row = doc['jobs']['release_grade_recorded_path']['steps'][30]; options = row['with']
    if fault == 'source_root': options['path'] = options['path'].replace('artifacts/**', 'artifacts-other/**')
    elif fault == 'recursive_pattern': options['path'] = options['path'].replace('artifacts/**', 'artifacts/*')
    elif fault == 'badge_pattern': options['path'] = options['path'].replace('*.svg', '**')
    elif fault == 'root_report': options['path'] = options['path'].replace('\nreports/', '\nPULSE_safe_pack_v0/artifacts/reports/')
    elif fault == 'name': options['name'] = 'report-latest'
    elif fault == 'action': row['uses'] = 'actions/upload-artifact@v7'
    elif fault == 'omit_selector': options['path'] = '\n'.join(options['path'].splitlines()[:-1]) + '\n'
    else: options['path'] += options['path'].splitlines()[0] + '\n'
    with pytest.raises(module.PlanError, match='report_publication_workflow_drift'):
        method(doc, recorded_source_objects)


@pytest.mark.parametrize('side', ['builder', 'checker'])
def test_report_publication_changes_only_one_input_set_and_selected_readers(recorded_source_objects, side):
    module, _ = report_publication_method(side); doc = mapping_source_document()
    _, before_steps, _ = module._build_jobs(doc)
    with patch.object(module, '_install_report_publication_projection', return_value=None):
        before_states = module._build_states(before_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    _, after_steps, _ = module._build_jobs(doc)
    after_states = module._build_states(after_steps, module.EXPECTED_CASE_IDS, doc, recorded_source_objects)
    oid = module._step_id('release_grade_recorded_path', 31)
    added = 0
    for a, b in zip(before_states, after_states, strict=True):
        a, b = copy.deepcopy(a), copy.deepcopy(b)
        assert set(a['required_consumer_occurrence_ids']) <= set(b['required_consumer_occurrence_ids'])
        added += len(set(b['required_consumer_occurrence_ids']) - set(a['required_consumer_occurrence_ids']))
        for value in (a, b): value['required_consumer_occurrence_ids'] = [x for x in value['required_consumer_occurrence_ids'] if x != oid]
        assert a == b
    for key in before_steps:
        a, b = copy.deepcopy(before_steps[key]), copy.deepcopy(after_steps[key])
        if a['occurrence_id'] == oid:
            assert a.pop('input_state_ids') == ['state:step5c:release-authority-audit-bundle']
            assert b.pop('input_state_ids') == ['state:step5c:' + role for role in _REPORT_PUBLICATION_ROLES]
        assert a == b
    assert added == 21
    assert len(before_states) == len(after_states) == 62


@pytest.mark.parametrize('role,other_reader', [('artifact-provenance-binding', 32),
                                              ('recorded-release-candidate-envelopes', 26),
                                              ('recorded-release-candidate-envelopes', 32)])
def test_report_publication_extends_old_closures_only_for_r31(source_fixture, recorded_source_objects, role, other_reader):
    plan = copy.deepcopy(source_fixture.plan); states, steps = provenance_rows(plan)
    state = states[role]; step = steps[('release_grade_recorded_path', other_reader)]
    step['input_state_ids'] = sorted(set(step['input_state_ids']) | {state['state_id']})
    state['required_consumer_occurrence_ids'] = sorted(set(state['required_consumer_occurrence_ids']) | {step['occurrence_id']})
    method = (PLAN_CHECKER._verify_source_provenance_equations if role == 'artifact-provenance-binding'
              else PLAN_CHECKER._verify_source_recorded_equations)
    code = 'provenance_mapping_' if role == 'artifact-provenance-binding' else 'recorded_mapping_'
    with pytest.raises(PLAN_CHECKER.PlanError, match=code):
        method(plan, mapping_source_document(), recorded_source_objects)


def test_report_publication_keeps_generic_and_complete_acceptance_boundaries(source_fixture, recorded_source_objects):
    states, steps = provenance_rows(source_fixture.plan)
    r31 = steps[('release_grade_recorded_path', 31)]
    assert r31['output_state_ids'] == []
    assert len(r31['input_state_ids']) == 24
    assert states['self-contained-evidence-floor']['state_id'] not in steps[('release_grade_recorded_path', 26)]['input_state_ids']
    assert states['recorded-release-candidate-envelopes']['state_id'] not in steps[('release_grade_recorded_path', 26)]['input_state_ids']
    assert states['release-authority-audit-bundle']['state_id'] not in steps[('release_grade_recorded_path', 33)]['input_state_ids']
    assert len(source_fixture.plan['source_inventory']) == 56
    assert len(prepared_fixture_members(source_fixture)) == 61
    assert source_fixture.plan['authority_boundary'] == BUILDER.AUTHORITY_BOUNDARY
    assert 'evidence_profile' not in source_fixture.plan
    with pytest.raises(VERIFIER.VerificationError, match='declared_state_evidence_incomplete'):
        VERIFIER._require_declared_state_completion(source_fixture.plan, runtime_projection_example(source_fixture), {})


if __name__ == '__main__':
    # The registered CI script runs the WHOLE program. No command-line filters
    # or environment-supplied plugin/options can silently trim it.
    for key in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_CURRENT_TEST'):
        os.environ.pop(key, None)
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    raise SystemExit(pytest.main(['-q', '-o', 'addopts=', str(Path(__file__).resolve())], plugins=[_CompleteProgramGuard()]))
