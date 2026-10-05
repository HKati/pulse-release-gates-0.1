"""Offline startup-failure regressions; no native runtime/isolation qualification.

Real harmless subprocesses exercise framing, byte/time bounds and group cleanup.
Systemd observations below are explicitly synthetic. No model is imported or
executed, and these tests cannot substitute for an owner-dispatched native run.
"""
from __future__ import annotations

import ast
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


# /run isolation correction. Fixtures below describe kernel records explicitly;
# they are not native observations and cannot qualify the selected Q2 runtime.
import io
import stat
from types import SimpleNamespace

CHECKER_PATH = ROOT / 'PULSE_safe_pack_v0/tools/check_q2_reference_qualification_v0.py'
CHECKER_SPEC = importlib.util.spec_from_file_location('q2_run_mount_checker_under_test', CHECKER_PATH)
K = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(K)


def synthetic_run_mount(unit=UNIT, plumbing=True):
    host = ('10 1 8:1 / / rw,relatime - ext4 /dev/sda1 rw\n'
            '11 10 0:20 / /run rw,nosuid,nodev - tmpfs tmpfs rw\n')
    child = ('20 1 8:1 / / ro,relatime - ext4 /dev/sda1 rw\n'
             '21 20 0:30 / /run rw,nosuid,nodev,noexec - tmpfs tmpfs rw,size=16384k,mode=755\n')
    stats = {'/run': {'device': '0:30', 'inode': 1, 'uid': 0, 'gid': 0, 'mode': 0o40755}}
    if plumbing:
        child += ('22 21 0:20 /systemd/propagate/' + unit +
                  ' /run/systemd/incoming ro,nosuid,nodev master:1 - tmpfs tmpfs rw\n'
                  '23 21 0:20 /systemd/inaccessible/dir /run/user ro,nosuid,nodev - tmpfs tmpfs rw\n'
                  '24 21 0:20 /systemd/inaccessible/dir /run/credentials ro,nosuid,nodev - tmpfs tmpfs rw\n')
        for path, mode in [('/run/systemd/incoming', 0o40600), ('/run/user', 0o40000),
                           ('/run/credentials', 0o40000)]:
            stats[path] = {'device': '0:20', 'inode': 9, 'uid': 0, 'gid': 0, 'mode': mode}
    return {'host_namespace': 'mnt:[1]', 'child_namespace': 'mnt:[2]',
            'host_mountinfo': host, 'child_mountinfo': child, 'mount_stats': stats}


def validate_mount(implementation, value, unit=UNIT):
    if implementation == 'supervisor':
        return N.validate_run_mount(value, unit)
    return K.verify_run_mount(value, unit)


@pytest.mark.parametrize('implementation', ['supervisor', 'checker'])
@pytest.mark.parametrize('stage', ['installer', 'installcheck', 'worker', 'decodecheck'])
@pytest.mark.parametrize('plumbing', [False, True])
def test_run_mount_accepts_distinct_tmpfs_and_inert_systemd_plumbing(implementation, stage, plumbing):
    unit = PREFIX + '-' + stage + '.service'
    validate_mount(implementation, synthetic_run_mount(unit, plumbing), unit)


@pytest.mark.parametrize('implementation', ['supervisor', 'checker'])
def test_run_mount_accepts_stricter_readonly_effective_tmpfs(implementation):
    value = synthetic_run_mount()
    value['child_mountinfo'] = value['child_mountinfo'].replace('/run rw,', '/run ro,')
    validate_mount(implementation, value)


MOUNT_MUTATIONS = [
    'same_namespace', 'bad_namespace', 'missing_run', 'stacked_run', 'host_device',
    'bind_subdirectory', 'not_tmpfs', 'missing_noexec', 'missing_nodev', 'missing_nosuid',
    'missing_access_flag', 'conflicting_access_flags', 'host_bind_under_run',
    'cross_unit_incoming', 'incoming_host_root', 'readable_incoming', 'executable_incoming',
    'writable_incoming_mount', 'readable_user_mask', 'wrong_mask_root', 'unknown_mask',
    'writable_run_directory', 'unprivileged_owner', 'unprivileged_group',
    'symlink_run', 'missing_stat', 'extra_stat', 'wrong_stat_device', 'bool_inode',
    'empty_host_mountinfo', 'bad_line', 'truncated_record', 'duplicate_id',
    'escaped_host_bind', 'unsafe_path', 'bad_escape', 'oversized', 'too_many_lines',
    'missing_evidence_field', 'extra_evidence_field', 'no_fresh_device',
    'missing_size', 'larger_size', 'smaller_size', 'duplicate_size', 'fake_size',
    'conflicting_suid', 'conflicting_dev', 'conflicting_exec',
]


def mutate_run_mount(value, mutation):
    child = value['child_mountinfo']
    if mutation == 'same_namespace': value['child_namespace'] = value['host_namespace']
    elif mutation == 'bad_namespace': value['child_namespace'] = 'declared_private'
    elif mutation == 'missing_run': child = '\n'.join(l for l in child.splitlines() if ' /run ' not in l) + '\n'
    elif mutation == 'stacked_run': child += '25 21 0:31 / /run rw,nosuid,nodev,noexec - tmpfs tmpfs rw\n'
    elif mutation == 'host_device': child = child.replace('0:30', '0:20'); value['mount_stats']['/run']['device'] = '0:20'
    elif mutation == 'bind_subdirectory': child = child.replace('0:30 / /run', '0:30 /source /run')
    elif mutation == 'not_tmpfs': child = child.replace('/run rw,nosuid,nodev,noexec - tmpfs', '/run rw,nosuid,nodev,noexec - ext4')
    elif mutation in ('missing_noexec', 'missing_nodev', 'missing_nosuid'):
        child = child.replace(',' + mutation.removeprefix('missing_'), '')
    elif mutation == 'missing_access_flag': child = child.replace('/run rw,', '/run ')
    elif mutation == 'conflicting_access_flags': child = child.replace('/run rw,', '/run ro,rw,')
    elif mutation in ('host_bind_under_run', 'escaped_host_bind'):
        path = '/run/host' if mutation == 'host_bind_under_run' else r'/run/\150ost'
        child += '25 21 0:20 /systemd ' + path + ' ro - tmpfs tmpfs rw\n'
        value['mount_stats']['/run/host'] = {'device':'0:20','inode':8,'uid':0,'gid':0,'mode':0o40755}
    elif mutation == 'cross_unit_incoming': child = child.replace('/propagate/' + UNIT, '/propagate/' + UNIT.replace('a', 'b'))
    elif mutation == 'incoming_host_root': child = child.replace('/systemd/propagate/' + UNIT, '/')
    elif mutation == 'readable_incoming': value['mount_stats']['/run/systemd/incoming']['mode'] = 0o40604
    elif mutation == 'executable_incoming': value['mount_stats']['/run/systemd/incoming']['mode'] = 0o40601
    elif mutation == 'writable_incoming_mount': child = child.replace('/run/systemd/incoming ro,', '/run/systemd/incoming rw,')
    elif mutation == 'readable_user_mask': value['mount_stats']['/run/user']['mode'] = 0o40400
    elif mutation == 'wrong_mask_root': child = child.replace('/systemd/inaccessible/dir', '/user')
    elif mutation == 'unknown_mask':
        child = child.replace('/run/user ', '/run/other ')
        value['mount_stats']['/run/other'] = value['mount_stats'].pop('/run/user')
    elif mutation == 'writable_run_directory': value['mount_stats']['/run']['mode'] = 0o40777
    elif mutation == 'unprivileged_owner': value['mount_stats']['/run']['uid'] = 65534
    elif mutation == 'unprivileged_group': value['mount_stats']['/run']['gid'] = 65534
    elif mutation == 'symlink_run': value['mount_stats']['/run']['mode'] = stat.S_IFLNK | 0o755
    elif mutation == 'missing_stat': del value['mount_stats']['/run']
    elif mutation == 'extra_stat': value['mount_stats']['/other'] = dict(value['mount_stats']['/run'])
    elif mutation == 'wrong_stat_device': value['mount_stats']['/run']['device'] = '0:99'
    elif mutation == 'bool_inode': value['mount_stats']['/run']['inode'] = True
    elif mutation == 'empty_host_mountinfo': value['host_mountinfo'] = ''
    elif mutation == 'bad_line': child += 'garbage\n'
    elif mutation == 'truncated_record': child = child.rstrip('\n')
    elif mutation == 'duplicate_id': child += child.splitlines()[0] + '\n'
    elif mutation == 'unsafe_path': child = child.replace(' /run ', ' /run/../run ')
    elif mutation == 'bad_escape': child = child.replace(' /run ', r' /\run ')
    elif mutation == 'oversized': child += 'x' * 262144 + '\n'
    elif mutation == 'too_many_lines': child = ''.join(f'{n+1} 1 0:1 / /x rw - tmpfs t rw\n' for n in range(4097))
    elif mutation == 'missing_evidence_field': del value['host_mountinfo']
    elif mutation == 'extra_evidence_field': value['declared_safe'] = True
    elif mutation == 'no_fresh_device': value['host_mountinfo'] += '90 1 0:30 / /somewhere rw - tmpfs tmpfs rw\n'
    elif mutation == 'missing_size': child = child.replace(',size=16384k', '')
    elif mutation == 'larger_size': child = child.replace('size=16384k', 'size=32768k')
    elif mutation == 'smaller_size': child = child.replace('size=16384k', 'size=8192k')
    elif mutation == 'duplicate_size': child = child.replace('size=16384k', 'size=16384k,size=16384k')
    elif mutation == 'fake_size': child = child.replace('size=16384k', 'size=16watts')
    elif mutation.startswith('conflicting_'): child = child.replace('/run rw,','/run rw,'+mutation.removeprefix('conflicting_')+',')
    else: raise AssertionError(mutation)
    value['child_mountinfo'] = child
    return value


@pytest.mark.parametrize('implementation', ['supervisor', 'checker'])
@pytest.mark.parametrize('mutation', MOUNT_MUTATIONS)
def test_run_mount_rejects_missing_weak_or_substituted_evidence(implementation, mutation):
    value = mutate_run_mount(synthetic_run_mount(), mutation)
    with pytest.raises((N.NativeQualificationError, K.QualificationCheckError)):
        validate_mount(implementation, value)


@pytest.mark.parametrize('stage', ['installer', 'installcheck', 'worker', 'decodecheck'])
def test_run_mount_service_command_preserves_other_controls(stage, tmp_path):
    command = N.service_command(PREFIX + '-' + stage + '.service', stage,
                                ['/never-executed'], tmp_path, Path(sys.executable))
    props = dict(arg[len('--property='):].split('=', 1) for arg in command if arg.startswith('--property='))
    assert props['InaccessiblePaths'] == '/tmp'
    assert props['TemporaryFileSystem'] == '/run:rw,nosuid,nodev,noexec,size=16M,mode=0755'
    assert props['PrivateNetwork'] == 'yes'
    assert props['RestrictAddressFamilies'] == 'AF_UNIX'
    assert props['SystemCallFilter'] == '~connect sendto sendmsg sendmmsg'
    assert props['ProtectHome'] == 'yes' and props['ProtectSystem'] == 'strict'
    assert props['NoNewPrivileges'] == 'yes' and props['CapabilityBoundingSet'] == ''
    assert props['User'] == props['Group'] == '65534'
    assert props['MemoryMax'] == '4294967296' and props['MemorySwapMax'] == '0'
    assert props['TasksMax'] == '64' and props['CPUQuota'] == '100%'
    assert props['RuntimeMaxSec'] == str({'installer':480,'installcheck':300,'worker':180,'decodecheck':180}[stage])
    assert N.GENERATION_NS == 15_000_000_000 and N.WATCHDOG_SECONDS == 20


@pytest.fixture
def mount_kernel(monkeypatch):
    value = synthetic_run_mount(); calls = []
    original_stat = os.stat
    original_readlink = os.readlink
    original_read_text = Path.read_text
    def readlink(path, *args, **kwargs):
        path = os.fspath(path)
        if path == '/proc/self/ns/mnt': return value['host_namespace']
        if path == '/proc/123/ns/mnt': return value['child_namespace']
        if path == '/proc/self/ns/net': return 'net:[1]'
        if path == '/proc/123/ns/net': return 'net:[2]'
        return original_readlink(path, *args, **kwargs)
    def read_mountinfo(pid):
        calls.append(('mountinfo', pid))
        return value['host_mountinfo' if pid == 'self' else 'child_mountinfo']
    def stat_call(path, *args, **kwargs):
        path = os.fspath(path) if not isinstance(path, int) else path
        if isinstance(path, str) and path.startswith('/proc/123/root/run'):
            calls.append(('stat', path, kwargs.get('follow_symlinks')))
            s = value['mount_stats'][path.removeprefix('/proc/123/root')]
            major, minor = map(int, s['device'].split(':'))
            return SimpleNamespace(st_dev=os.makedev(major,minor),st_ino=s['inode'],st_uid=s['uid'],st_gid=s['gid'],st_mode=s['mode'])
        return original_stat(path, *args, **kwargs)
    def read_text(path, *args, **kwargs):
        name = str(path)
        if name == '/proc/123/status':
            return 'Uid:\t65534\t65534\t65534\t65534\nGid:\t65534\t65534\t65534\t65534\nNoNewPrivs:\t1\nCapEff:\t0000000000000000\n'
        if name == '/proc/123/cgroup': return '0::/system.slice/' + UNIT + '\n'
        if name.startswith('/sys/fs/cgroup/system.slice/' + UNIT + '/'):
            return {'memory.max':'4294967296','memory.swap.max':'0','pids.max':'64','cpu.max':'100000 100000'}[path.name]
        return original_read_text(path, *args, **kwargs)
    monkeypatch.setattr(N, 'read_mountinfo', read_mountinfo, raising=False)
    monkeypatch.setattr(os, 'readlink', readlink)
    monkeypatch.setattr(os, 'stat', stat_call)
    monkeypatch.setattr(Path, 'read_text', read_text)
    return value, calls


def test_run_mount_collector_reads_actual_proc_paths_and_checks_them(mount_kernel):
    value, calls = mount_kernel
    assert N.observe_run_mount(123, UNIT) == value
    assert calls[:2] == [('mountinfo', 'self'), ('mountinfo', 123)]
    assert set((c[1], c[2]) for c in calls if c[0] == 'stat') == {
        ('/proc/123/root' + p, False) for p in value['mount_stats']}


def test_run_mount_collector_rejects_namespace_change(mount_kernel, monkeypatch):
    _, calls = mount_kernel
    original = N.os.readlink; seen = 0
    def changed(path, *args, **kwargs):
        nonlocal seen
        if path == '/proc/123/ns/mnt':
            seen += 1
            return 'mnt:[2]' if seen == 1 else 'mnt:[3]'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(N.os, 'readlink', changed)
    with pytest.raises(N.NativeQualificationError, match='^mount_namespace_changed$'):
        N.observe_run_mount(123, UNIT)


@pytest.mark.parametrize('fault', ['missing', 'oversized', 'invalid_utf8'])
def test_run_mount_proc_read_is_bounded_and_has_no_fallback(monkeypatch, fault):
    requests = []
    class Stream(io.BytesIO):
        def read(self, size=-1):
            requests.append(size)
            return super().read(size)
    def opening(path, mode):
        assert path == '/proc/123/mountinfo' and mode == 'rb'
        if fault == 'missing': raise FileNotFoundError(path)
        return Stream(b'x' * 262145 if fault == 'oversized' else b'\xff\n')
    monkeypatch.setattr(N, 'open', opening, raising=False)
    with pytest.raises((N.NativeQualificationError, UnicodeError, FileNotFoundError)):
        N.read_mountinfo(123)
    assert requests == ([] if fault == 'missing' else [262145])


def test_run_mount_parser_reads_real_local_proc_without_claiming_isolation():
    # Read only the current process. No mount, systemd unit or model is started.
    assert N.run_mount_entries(N.read_mountinfo('self'))


@pytest.mark.parametrize('mutation', [None, 'same_namespace', 'host_device', 'missing_noexec',
                                      'executable_incoming', 'writable_run_directory'])
def test_run_mount_verification_precedes_exec_and_keeps_startup_failure(startup, mount_kernel, monkeypatch, mutation):
    run, events, output = startup
    value, reads = mount_kernel
    if mutation:
        mutate_run_mount(value, mutation)
    frame = {'pid':123, 'ipv4_blocked':True, 'ipv6_blocked':True}
    body = ('import sys,json; print(' + repr(json.dumps(frame)) + ',flush=True); '
            'raise SystemExit(0 if sys.stdin.buffer.readline(16)==b"EXEC\\n" else 71)')
    monkeypatch.setattr(N, 'service_command', lambda *args: python_command(body))
    def control(command, timeout=15, *, check=True):
        events.append(('control', command[1], timeout))
        props = {k:N.PROPERTIES[k] for k in N.OBSERVED_PROPERTIES if k in N.PROPERTIES}
        props.update(MainPID='123', RuntimeMaxUSec='8min')
        return subprocess.CompletedProcess(command,0, ''.join(k+'='+v+'\n' for k,v in props.items()).encode(), b'')
    monkeypatch.setattr(N,'control',control)
    original_send = N.Service.send
    def send(service, data):
        events.append(('send',data))
        return original_send(service,data)
    monkeypatch.setattr(N.Service,'send',send)
    if mutation:
        service = None
        try:
            with pytest.raises(N.NativeQualificationError): service = run()
        finally:
            if service is not None: service.close()
        assert not any(e[0]=='send' for e in events)
        report=json.loads((output/'installer-startup-failure.json').read_bytes())
        assert report['startup_phase']=='isolation_observation'
        assert report['native_runtime_qualified'] is False
        assert events.count(('close',))==1
    else:
        service=run()
        try:
            assert service.observation['run_mount']==value
            assert ('send',b'EXEC\n') in events and reads
            assert service.complete(empty_tail=True)[1]==0
        finally: service.close()
        assert not (output/'installer-startup-failure.json').exists()


def test_run_mount_regressions_remain_in_registered_pytest_module():
    targets=[x.strip() for x in (ROOT/'ci/pytest-tests.list').read_text().splitlines()
             if x.strip() and not x.lstrip().startswith('#')]
    assert targets.count('tests/test_q2_native_startup_diagnostics_v0.py')==1


def test_run_mount_checker_stays_separate_from_supervisor():
    tree=ast.parse(CHECKER_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all('qualify_q2_reference_runtime_v0' not in x.name for x in node.names)
        if isinstance(node, ast.ImportFrom):
            assert 'qualify_q2_reference_runtime_v0' not in (node.module or '')
    old=synthetic_run_mount()
    del old['mount_stats']
    with pytest.raises(K.QualificationCheckError): K.verify_run_mount(old,UNIT)


@pytest.mark.parametrize('stage', ['installer', 'installcheck', 'worker', 'decodecheck'])
def test_run_mount_checker_requires_run_evidence_on_every_stage(stage):
    value = {'stage':stage,'unit':PREFIX+'-'+stage+'.service','pid':123,
             'host_netns':'net:[1]','child_netns':'net:[2]','uid':65534,
             'no_new_privs':True,'capabilities':'0000000000000000',
             'ipv4_blocked':True,'ipv6_blocked':True,'memory_max':'4294967296',
             'memory_swap_max':'0','pids_max':'64','cpu_max':'100000 100000',
             'properties':{k:N.PROPERTIES[k] for k in N.OBSERVED_PROPERTIES if k in N.PROPERTIES}}
    value['properties']['RuntimeMaxUSec']={'installer':'8min','installcheck':'5min',
                                          'worker':'3min','decodecheck':'3min'}[stage]
    # This old-format observation was accepted by the original checker. There
    # is no compatibility fallback for absent /run evidence after this change.
    with pytest.raises(K.QualificationCheckError, match='^sandbox_fields$'):
        K.verify_sandbox_observation(value,stage)


@pytest.mark.parametrize('implementation', ['supervisor', 'checker'])
@pytest.mark.parametrize('size', ['16777216', '16m', '16M', '16384K'])
def test_run_mount_checks_effective_size_without_display_unit_assumptions(implementation,size):
    value=synthetic_run_mount()
    value['child_mountinfo']=value['child_mountinfo'].replace('size=16384k','size='+size)
    validate_mount(implementation,value)
