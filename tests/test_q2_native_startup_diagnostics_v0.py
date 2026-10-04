"""Offline startup-failure regressions; no native runtime/isolation qualification.

Real harmless subprocesses exercise framing, byte/time bounds and group cleanup.
Systemd observations below are explicitly synthetic. No model is imported or
executed, and these tests cannot substitute for an owner-dispatched native run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'PULSE_safe_pack_v0/tools/qualify_q2_reference_runtime_v0.py'
SPEC = importlib.util.spec_from_file_location('q2_startup_diagnostics_under_test', PATH)
N = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(N)
PREFIX = 'pulse-q2-' + 'a' * 24
UNIT = PREFIX + '-installer.service'
STATUS = b'Id=' + UNIT.encode() + b'\nResult=exit-code\nExecMainCode=1\nExecMainStatus=226\n'
JOURNAL = b'SYNTHETIC ONLY: service startup failed before its barrier.\n'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('offline regression attempted networking')
    monkeypatch.setattr(socket, 'create_connection', reject)
    monkeypatch.setattr(socket.socket, 'connect', reject)


def python_command(body):
    return [sys.executable, '-I', '-S', '-B', '-c', body]


@pytest.fixture
def startup(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(N, 'service_command', lambda *args: python_command('raise SystemExit(7)'))
    def control(command, timeout=15, *, check=True):
        events.append(('control', command[1], timeout))
        return subprocess.CompletedProcess(command, 0, b'', b'')
    monkeypatch.setattr(N, 'control', control)
    original_close = N.Service.close
    def close(service):
        events.append(('close',))
        original_close(service)
    monkeypatch.setattr(N.Service, 'close', close)
    def diagnostic(command):
        kind = 'status' if command[0] == '/usr/bin/systemctl' else 'journal'
        events.append(('diagnostic', kind))
        raw = STATUS if kind == 'status' else JOURNAL
        return {'command': command, 'capture_status': 'complete', 'exit_code': 0,
                'output_bytes': len(raw), 'output_sha256': hashlib.sha256(raw).hexdigest()}, raw
    monkeypatch.setattr(N, 'bounded_startup_diagnostic', diagnostic, raising=False)
    original_save = N.save
    def save(path, raw):
        events.append(('save', path.name))
        original_save(path, raw)
    monkeypatch.setattr(N, 'save', save)
    def run(stage='installer'):
        return N.Service(PREFIX, stage, ['/never-executed'], tmp_path,
                         Path(sys.executable), tmp_path / (stage + '.log'), time.monotonic() + 30)
    return run, events, tmp_path


@pytest.mark.parametrize('stage', tuple(N.STAGES))
def test_startup_eof_keeps_original_error_and_stage_evidence(startup, monkeypatch, stage):
    run, events, output = startup
    def no_exec(*args):
        pytest.fail('failed barrier must never authorize EXEC')
    monkeypatch.setattr(N.Service, 'send', no_exec)
    with pytest.raises(N.NativeQualificationError, match='^unexpected_protocol_eof$'):
        run(stage)
    report = json.loads((output / (stage + '-startup-failure.json')).read_bytes())
    assert report['unit'] == PREFIX + '-' + stage + '.service'
    assert report['stage'] == stage and report['startup_phase'] == 'barrier_read'
    assert report['error_code'] == 'unexpected_protocol_eof'
    assert report['native_runtime_qualified'] is False
    assert report['capture_dispatch_authorized'] is False
    assert report['authority_effect'] == 'none'
    assert report['client_exit_code_before_cleanup'] in (None, 7)
    assert report['client_exit_code_after_cleanup'] in (7, -9)
    assert (output / (stage + '.log')).read_bytes() == b''
    for kind, raw, timing in [('status', STATUS, 'before_service_cleanup'),
                             ('journal', JOURNAL, 'after_service_cleanup')]:
        entry = report['diagnostics'][kind]
        assert entry['observation_timing'] == timing and entry['published'] is True
        assert N.safe_read(output / entry['path']) == raw
        assert entry['output_sha256'] == hashlib.sha256(raw).hexdigest()
        assert entry['output_bytes'] == len(raw)
    assert events.index(('diagnostic', 'status')) < events.index(('close',))
    assert events.index(('close',)) < events.index(('diagnostic', 'journal'))
    assert events.count(('close',)) == 1
    assert all(i > events.index(('close',)) for i, event in enumerate(events) if event[0] == 'save')
    assert ('control', 'kill', 10) in events and ('control', 'stop', 10) in events


@pytest.mark.parametrize('failure,phase,expected', [
    ('launch', 'service_launch', FileNotFoundError),
    ('json', 'barrier_read', json.JSONDecodeError),
    ('isolation', 'isolation_observation', N.NativeQualificationError),
    ('exec', 'exec_authorization', N.NativeQualificationError),
])
def test_startup_reports_exact_failed_phase_without_inventing_cause(startup, monkeypatch, failure, phase, expected):
    run, events, output = startup
    frame = {'pid': 123, 'ipv4_blocked': True, 'ipv6_blocked': True}
    body = "import time; print(" + repr(json.dumps(frame)) + ", flush=True); time.sleep(10)"
    if failure == 'launch':
        monkeypatch.setattr(N, 'service_command', lambda *args: ['/nonexistent-q2-test-executable'])
    else:
        if failure == 'json':
            body = "print('{not-json}', flush=True)"
        monkeypatch.setattr(N, 'service_command', lambda *args: python_command(body))
    def observe(*args):
        if failure == 'isolation':
            raise N.NativeQualificationError('synthetic_isolation_rejection')
        return {'synthetic': True}
    def send(*args):
        if failure == 'exec':
            raise N.NativeQualificationError('synthetic_exec_rejection')
        pytest.fail('failed startup must not send EXEC')
    monkeypatch.setattr(N, 'observe_service', observe)
    monkeypatch.setattr(N.Service, 'send', send)
    with pytest.raises(expected):
        run()
    report = json.loads((output / 'installer-startup-failure.json').read_bytes())
    assert report['startup_phase'] == phase
    assert report['exception_type'] == expected.__name__
    assert events.count(('close',)) == 1


def test_successful_synthetic_barrier_has_no_failure_collection(startup, monkeypatch):
    run, events, output = startup
    body = "import os,json,sys; print(json.dumps({'pid':os.getpid(),'ipv4_blocked':True,'ipv6_blocked':True}),flush=True); assert sys.stdin.buffer.readline()==b'EXEC\\n'"
    monkeypatch.setattr(N, 'service_command', lambda *args: python_command(body))
    monkeypatch.setattr(N, 'observe_service', lambda *args: {'synthetic': True})
    service = run()
    try:
        assert service.complete() == (b'', 0)
    finally:
        service.close()
    assert not any(event[0] == 'diagnostic' for event in events)
    assert not list(output.glob('*-startup-*'))


def test_collection_exceptions_never_mask_failure_or_skip_cleanup(startup, monkeypatch):
    run, events, output = startup
    def unavailable(command):
        raise RuntimeError('SYNTHETIC_SECRET_must_not_appear_in_report')
    monkeypatch.setattr(N, 'bounded_startup_diagnostic', unavailable)
    with pytest.raises(N.NativeQualificationError, match='unexpected_protocol_eof'):
        run()
    raw = (output / 'installer-startup-failure.json').read_bytes()
    report = json.loads(raw)
    assert b'SYNTHETIC_SECRET' not in raw
    assert all(row['capture_status'] == 'unavailable' for row in report['diagnostics'].values())
    assert all(row['capture_error_type'] == 'RuntimeError' for row in report['diagnostics'].values())
    assert events.count(('close',)) == 1


def test_publication_failure_preserves_original_error_without_second_cleanup(startup, monkeypatch, capsys):
    run, events, output = startup
    def disk_error(*args):
        raise OSError('synthetic disk failure')
    monkeypatch.setattr(N, 'save', disk_error)
    with pytest.raises(N.NativeQualificationError, match='unexpected_protocol_eof'):
        run()
    assert events.count(('close',)) == 1
    assert 'original failure retained' in capsys.readouterr().err


def test_cleanup_error_is_secondary_to_original_failure(startup, monkeypatch):
    run, events, output = startup
    close = N.Service.close
    def closes_then_reports_error(service):
        close(service)
        raise OSError('synthetic cleanup error')
    monkeypatch.setattr(N.Service, 'close', closes_then_reports_error)
    with pytest.raises(N.NativeQualificationError, match='unexpected_protocol_eof'):
        run()
    report = json.loads((output / 'installer-startup-failure.json').read_bytes())
    assert report['cleanup_error_type'] == 'OSError'
    assert report['error_code'] == 'unexpected_protocol_eof'
    assert events.count(('close',)) == 1


def test_early_collector_failure_still_invokes_cleanup_once(startup, monkeypatch):
    run, events, output = startup
    def unavailable(*args):
        raise RuntimeError('synthetic collector initialization failure')
    monkeypatch.setattr(N, 'preserve_startup_failure', unavailable)
    with pytest.raises(N.NativeQualificationError, match='unexpected_protocol_eof'):
        run()
    assert events.count(('close',)) == 1


@pytest.mark.parametrize('unit', ['*.service', '--all', 'pulse-q2-/../x.service', UNIT+'\n', ''])
def test_diagnostic_scope_rejects_invalid_unit_patterns(unit):
    with pytest.raises(N.NativeQualificationError, match='service_identity'):
        N.startup_diagnostic_command(unit, 'journal')


def test_diagnostic_commands_are_read_only_finite_and_exact_unit_scoped():
    status = N.startup_diagnostic_command(UNIT, 'status')
    journal = N.startup_diagnostic_command(UNIT, 'journal')
    assert status[:3] == ['/usr/bin/systemctl', 'show', '--no-pager']
    assert status[-2:] == ['--', UNIT]
    assert '--property=' + ','.join(N.STARTUP_STATUS_PROPERTIES) in status
    assert journal == ['/usr/bin/journalctl', '--boot=0', '--no-pager', '--quiet',
                       '--lines=80', '--output=short-iso-precise', '--unit=' + UNIT]
    assert N.STARTUP_DIAGNOSTIC_BYTES == 65536
    assert N.STARTUP_DIAGNOSTIC_SECONDS == 2.0
    assert N.STARTUP_DIAGNOSTIC_REAP_SECONDS == 1.0
    with pytest.raises(N.NativeQualificationError):
        N.startup_diagnostic_command(UNIT, 'restart')


@pytest.mark.parametrize('size', [0, 1, 127, 128, 129, 1_048_576])
def test_real_diagnostic_output_is_bounded_while_reading(monkeypatch, size):
    monkeypatch.setattr(N, 'STARTUP_DIAGNOSTIC_BYTES', 128)
    result, raw = N.bounded_startup_diagnostic(python_command('import os; os.write(1,b"x"*'+str(size)+')'))
    assert raw == b'x' * min(size, 128)
    assert result['output_bytes'] == len(raw)
    assert result['output_sha256'] == hashlib.sha256(raw).hexdigest()
    assert result['capture_status'] == ('output_limit' if size > 128 else 'complete')
    assert result['exit_code'] == (None if size > 128 else 0)


def test_real_diagnostic_retains_raw_stderr_and_nonzero_exit():
    result, raw = N.bounded_startup_diagnostic(python_command('import os; os.write(1,b"out\\x00"); os.write(2,b"err\\xff"); raise SystemExit(23)'))
    assert raw == b'out\x00err\xff'
    assert result['capture_status'] == 'command_failed'
    assert result['exit_code'] == 23


@pytest.mark.parametrize('close_output', [False, True])
def test_real_stuck_diagnostic_cannot_outlive_its_budget(monkeypatch, close_output):
    monkeypatch.setattr(N, 'STARTUP_DIAGNOSTIC_SECONDS', 1.0)
    monkeypatch.setattr(N, 'STARTUP_DIAGNOSTIC_REAP_SECONDS', 0.30)
    body = 'import os,time; os.write(1,b"partial"); '
    if close_output:
        body += 'os.close(1); os.close(2); '
    body += 'time.sleep(10)'
    start = time.monotonic()
    result, raw = N.bounded_startup_diagnostic(python_command(body))
    assert time.monotonic() - start < 3.0
    assert result['capture_status'] == 'timeout'
    assert raw == b'partial' and result['exit_code'] is None


def test_real_descendant_holding_output_pipe_is_killed(monkeypatch, tmp_path):
    if not hasattr(os, 'fork'):
        pytest.skip('POSIX process group regression')
    monkeypatch.setattr(N, 'STARTUP_DIAGNOSTIC_SECONDS', 1.0)
    pidfile = tmp_path / 'child.pid'
    body = f'''import os,time,pathlib
pid=os.fork()
if pid:
    pathlib.Path({str(pidfile)!r}).write_text(str(pid))
    os._exit(0)
time.sleep(20)
'''
    result, raw = N.bounded_startup_diagnostic(python_command(body))
    assert result['capture_status'] == 'timeout'
    pid = int(pidfile.read_text())
    status = Path('/proc') / str(pid) / 'stat'
    deadline = time.monotonic() + 1
    while status.exists() and time.monotonic() < deadline:
        try:
            if status.read_text().split(') ', 1)[1].split()[0] == 'Z':
                break
        except FileNotFoundError:
            break
        time.sleep(0.01)
    assert not status.exists() or status.read_text().split(') ', 1)[1].split()[0] == 'Z'


def test_missing_diagnostic_command_is_unavailable_not_success():
    result, raw = N.bounded_startup_diagnostic(['/nonexistent-q2-diagnostic-command'])
    assert result['capture_status'] == 'unavailable'
    assert result['capture_error_type'] == 'FileNotFoundError'
    assert result['exit_code'] is None and raw == b''


def test_diagnostic_child_does_not_inherit_credentials(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'synthetic-not-a-credential')
    monkeypatch.setenv('PYTHONPATH', '/synthetic')
    monkeypatch.setenv('SYSTEMD_PAGER', 'unsafe-pager')
    result, raw = N.bounded_startup_diagnostic(python_command('import os,json; print(json.dumps(dict(os.environ)))'))
    env = json.loads(raw)
    assert result['capture_status'] == 'complete'
    assert 'GH_TOKEN' not in env and 'PYTHONPATH' not in env
    assert env['SYSTEMD_PAGER'] == 'cat'


def test_actual_supervisor_publishes_synthetic_startup_evidence_and_stays_failed(startup, monkeypatch):
    _, events, root = startup
    repo = root / 'repo'; repo.mkdir()
    archive = root / 'input.zip'; archive.write_bytes(b'SYNTHETIC_NO_RUNTIME')
    output = root / 'published'
    context = {'source_commit': 'a'*40, 'run_id': '12345', 'origin': 'synthetic_only'}
    monkeypatch.setattr(N, 'check_context', lambda *args: context)
    monkeypatch.setattr(N, 'snapshot_sources', lambda *args: [])
    monkeypatch.setattr(N, 'freeze', lambda *args: None)
    monkeypatch.setattr(N, 'writable_directory', lambda path: path.mkdir())
    monkeypatch.setattr(N.os, 'chown', lambda *args: None)
    monkeypatch.setattr(N, 'ARCHIVE_SIZE', archive.stat().st_size)
    monkeypatch.setattr(N, 'ARCHIVE_SHA', hashlib.sha256(archive.read_bytes()).hexdigest())
    def synthetic_preflight(command, log, deadline):
        log.write_bytes(b'SYNTHETIC_PREFLIGHT_ONLY\n')
        (log.parent.parent / 'staged/bundle').mkdir(parents=True)
        (log.parent / 'input-check.json').write_bytes(N.encode({
            'source_files': [], 'preparation_source_commit': N.PREPARATION_SOURCE}))
    monkeypatch.setattr(N, 'bounded_local', synthetic_preflight)
    assert N.qualify(repo, archive, output, 'a'*40, True) == 1
    report = json.loads((output / 'qualification.json').read_bytes())
    assert report['status'] == 'failed' and report['error_code'] == 'unexpected_protocol_eof'
    assert report['native_runtime_qualified'] is False and report['scored_call_count'] == 0
    assert report['capture_dispatch_authorized'] is False and report['production_gate_eligible'] is False
    indexed = {row['path']: row for row in report['evidence']}
    for name in ('installer-startup-failure.json', 'installer-startup-status.log', 'installer-startup-journal.log'):
        raw = (output / name).read_bytes()
        assert indexed[name]['size'] == len(raw)
        assert indexed[name]['sha256'] == hashlib.sha256(raw).hexdigest()
    assert not (output / 'generation-start.json').exists()
    assert events.count(('close',)) == 1


@pytest.mark.parametrize('when', ['status', 'journal'])
def test_interrupted_diagnostic_cannot_skip_cleanup_or_replace_eof(startup, monkeypatch, when):
    run, events, output = startup
    diagnostic = N.bounded_startup_diagnostic
    def interrupted(command):
        kind = 'status' if command[0] == '/usr/bin/systemctl' else 'journal'
        if kind == when:
            raise SystemExit('synthetic diagnostic interruption')
        return diagnostic(command)
    monkeypatch.setattr(N, 'bounded_startup_diagnostic', interrupted)
    with pytest.raises(N.NativeQualificationError, match='unexpected_protocol_eof'):
        run()
    assert events.count(('close',)) == 1
