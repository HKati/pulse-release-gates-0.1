"""Negative publication boundaries; controlled metadata is not hosted evidence."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from test_q2_release_intake_v0 import ROOT, IO, LOAD, ADMISSION
from test_q2_required_gate_integration_v0 import invocation


@pytest.fixture
def negative(invocation, monkeypatch):
    f = invocation
    request, binding, sources = LOAD.trusted_invocation(f.repo, f.env)
    value = LOAD.empty_result(LOAD.load_profile(f.repo))
    value.update(input_valid=True, metric_pass=False, process_exit=1,
                 checks={k: True for k in value['checks']}, cleanup='verified_removed',
                 request_sha256=binding['request_sha256'], evaluation_binding=binding,
                 release_artifact=request['release_subject'], source_bindings=sources,
                 replay_environment={'implementation': 'CPython', 'python': [3, 11, 16], 'unicode': '14.0.0'},
                 diagnostics=['q2_min_eligible_groups_not_met'],
                 metrics={'groups_total': 50, 'groups_eligible': 49, 'consistent': 49, 'inconsistent': 0,
                          'unknown': 1, 'responses_total': 150, 'responses_eligible': 147,
                          'wilson_lower_bound': 0.9273, 'threshold': 0.9, 'min_n_eligible_groups': 50})
    IO.validate(value, (ROOT / IO.RESULT_SCHEMA).read_bytes())
    path = f.repo / IO.PUBLIC_RESULT
    path.parent.mkdir(parents=True)
    path.write_bytes(IO.encode(value))
    calls = []
    def consume(repo, *, consumer, environment):
        assert repo == f.repo and consumer == 'admission' and environment == f.env
        assert not any(k.startswith('PULSE_Q2_') for k in os.environ)
        calls.append(consumer)
        return copy.deepcopy(value)
    monkeypatch.setattr(LOAD, 'consume', consume)
    return f, value, calls


def test_verified_negative_has_zero_outer_exit_but_keeps_metric_failure(negative, monkeypatch):
    f, value, calls = negative
    monkeypatch.setattr(sys, 'argv', ['checker', '--repo-root', str(f.repo), '--verify-recorded-negative'])
    monkeypatch.setattr(os, 'environ', dict(f.env))
    assert ADMISSION.main() == 0
    observed = IO.strict_json((f.repo / ADMISSION.INDEPENDENT_RESULT).read_bytes())
    assert observed == value and calls == ['admission']
    assert observed['metric_pass'] is False and observed['process_exit'] == 1
    assert observed['authority_effect'] == 'none' and observed['production_gate_eligible'] is False


@pytest.mark.parametrize('fault', ['pass', 'input-invalid', 'capture', 'request', 'subject', 'replay', 'summary',
                                 'cleanup', 'source', 'run', 'attempt', 'digest', 'artifact', 'schema', 'synthetic'])
def test_changed_producer_cannot_be_certified(negative, fault):
    f, value, calls = negative
    changed = copy.deepcopy(value)
    if fault == 'pass':
        changed.update(metric_pass=True, process_exit=0, diagnostics=[])
    elif fault == 'input-invalid':
        changed.update(input_valid=False, metric_pass=None, metrics=None, process_exit=2)
    elif fault in changed['checks']:
        changed['checks'][fault] = False
    elif fault == 'cleanup': changed['cleanup'] = 'not_established'
    elif fault == 'source': changed['source_bindings'][0]['sha256'] = 'b' * 64
    elif fault == 'run': changed['evaluation_binding']['run_id'] = '9999'
    elif fault == 'attempt': changed['evaluation_binding']['run_attempt'] = 2
    elif fault == 'digest': changed['request_sha256'] = 'c' * 64
    elif fault == 'artifact': changed['release_artifact']['artifact_id'] += 1
    elif fault == 'schema': changed['unreviewed'] = True
    else: changed['record_status'] = 'synthetic_fixture'
    (f.repo / IO.PUBLIC_RESULT).write_bytes(IO.encode(changed))
    with pytest.raises(IO.IntakeError):
        ADMISSION.verify_recorded_negative(f.repo, environment=f.env)
    assert not (f.repo / ADMISSION.INDEPENDENT_RESULT).exists()


@pytest.mark.parametrize('fault', ['pass', 'request', 'capture', 'subject', 'replay', 'summary', 'cleanup', 'empty-sources'])
def test_even_matching_invalid_records_cannot_pass(negative, fault):
    f, value, _ = negative
    if fault == 'pass': value.update(metric_pass=True, process_exit=0, diagnostics=[])
    elif fault == 'cleanup': value['cleanup'] = 'not_established'
    elif fault == 'empty-sources': value['source_bindings'] = []
    else: value['checks'][fault] = False
    (f.repo / IO.PUBLIC_RESULT).write_bytes(IO.encode(value))
    with pytest.raises(IO.IntakeError):
        ADMISSION.verify_recorded_negative(f.repo, environment=f.env)
    assert not (f.repo / ADMISSION.INDEPENDENT_RESULT).exists()


@pytest.mark.parametrize('fault', ['missing', 'malformed', 'producer-link', 'parent-link', 'hardlink', 'existing-output'])
def test_unsafe_or_stale_public_paths_are_rejected(negative, tmp_path, fault):
    f, value, calls = negative
    path = f.repo / IO.PUBLIC_RESULT
    if fault == 'missing': path.unlink()
    elif fault == 'malformed': path.write_bytes(b'PRIVATE_BAD_JSON')
    elif fault in ('producer-link', 'hardlink'):
        other = tmp_path / 'other'; other.write_bytes(path.read_bytes()); path.unlink()
        if fault == 'hardlink': os.link(other, path)
        else: path.symlink_to(other)
    elif fault == 'parent-link':
        other = tmp_path / 'records'; path.parent.rename(other); path.parent.symlink_to(other, target_is_directory=True)
    else: (f.repo / ADMISSION.INDEPENDENT_RESULT).write_bytes(b'prior-output')
    with pytest.raises((IO.IntakeError, OSError)):
        ADMISSION.verify_recorded_negative(f.repo, environment=f.env)
    assert not calls
    if fault == 'existing-output':
        assert (f.repo / ADMISSION.INDEPENDENT_RESULT).read_bytes() == b'prior-output'


@pytest.mark.parametrize('fault', ['timeout', 'write', 'producer-race'])
def test_handled_failure_leaves_no_accepted_output(negative, monkeypatch, fault):
    f, value, _ = negative
    if fault == 'timeout':
        def consume(*args, **kwargs): raise IO.IntakeError('q2_timeout')
        monkeypatch.setattr(LOAD, 'consume', consume)
    elif fault == 'write':
        def fail(*args, **kwargs): raise OSError('PRIVATE_IO_ERROR')
        monkeypatch.setattr(ADMISSION.os, 'link', fail)
    else:
        def consume(*args, **kwargs):
            (f.repo / IO.PUBLIC_RESULT).write_bytes(IO.encode({**value, 'cleanup': 'not_established'}))
            return copy.deepcopy(value)
        monkeypatch.setattr(LOAD, 'consume', consume)
    with pytest.raises((IO.IntakeError, OSError)):
        ADMISSION.verify_recorded_negative(f.repo, environment=f.env)
    assert not (f.repo / ADMISSION.INDEPENDENT_RESULT).exists()
    assert not list((f.repo / IO.PUBLIC_RESULT).parent.glob('.q2-negative-*'))


def test_existing_pass_only_admission_still_rejects_a_verified_negative(negative):
    f, _, calls = negative
    with pytest.raises(IO.IntakeError, match='q2_admission_rejected'):
        ADMISSION.admit(f.repo, f.repo / IO.PUBLIC_RESULT,
                        {'git_sha': f.sha, 'run_mode': 'prod', 'run_key': f.env['PULSE_RUN_KEY']},
                        {'commit_sha': f.sha, 'repository': f.env['GITHUB_REPOSITORY']}, environment=f.env)
    assert calls == ['admission']


@pytest.mark.parametrize('gate,verify,request_text,digest,expected,calls', [
    (1, 0, 'request', 'digest', 1, 2), (7, 2, 'request', 'digest', 7, 2),
    (0, 0, 'request', 'digest', 1, 2), (0, 2, 'request', 'digest', 1, 2),
    (0, 0, '', '', 0, 1), (9, 0, '', '', 9, 1),
    (0, 2, 'request', '', 1, 2), (0, 2, '', 'digest', 1, 2)])
def test_actual_required_gate_shell_preserves_failure(tmp_path, gate, verify, request_text, digest, expected, calls):
    doc = yaml.load((ROOT / '.github/workflows/pulse_ci.yml').read_bytes(), Loader=yaml.BaseLoader)
    step = next(s for s in doc['jobs']['pulse']['steps'] if
                s.get('name') == 'release-grade record current-run required-gate evidence')
    commands = tmp_path / 'commands'; commands.mkdir()
    shim = commands / 'python'
    shim.write_text('#!/bin/sh\nprintf "call\\n" >> "$CALLS"\n'
                    'case "$1" in *run_recorded_required_gate_evaluations_v0.py) exit "$GATE";; '
                    '*check_q2_release_intake_v0.py) exit "$VERIFY";; *) exit 88;; esac\n')
    shim.chmod(0o755)
    env = {'PATH': str(commands) + os.pathsep + os.defpath, 'CALLS': str(tmp_path / 'calls'),
           'GATE': str(gate), 'VERIFY': str(verify), 'PACK_DIR': 'PULSE_safe_pack_v0',
           'GITHUB_WORKSPACE': str(tmp_path), 'GITHUB_SHA': 'a' * 40, 'PULSE_RUN_KEY': 'synthetic-only',
           'GITHUB_REPOSITORY': 'HKati/pulse-release-gates-0.1', 'GITHUB_REF_NAME': 'main',
           LOAD.REQUEST_ENV: request_text, LOAD.DIGEST_ENV: digest}
    result = subprocess.run(['bash', '-c', step['run']], cwd=tmp_path, env=env, capture_output=True, timeout=10)
    assert result.returncode == expected, result.stderr
    assert len((tmp_path / 'calls').read_text().splitlines()) == calls


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
