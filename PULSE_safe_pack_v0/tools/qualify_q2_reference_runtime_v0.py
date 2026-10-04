#!/usr/bin/env python3
"""Owner-only native qualification of the adopted Q2 runtime; one unscored call.

This is a new path, not a rewrite/rebinding of the historical preparation.
No model import occurs here. Installation, worker and decode checker execute in
separate, externally inspected systemd services. Unsupported isolation BLOCKs.
The prepare-runtime commands are deliberately untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

PACK = 'PULSE_safe_pack_v0/'
TOOLS = PACK + 'tools/'
SELF = TOOLS + 'qualify_q2_reference_runtime_v0.py'
CHECKER = TOOLS + 'check_q2_reference_qualification_v0.py'
WORKER = TOOLS + 'run_q2_reference_subject_v0.py'
OLD_CHECKER = TOOLS + 'check_q2_reference_capture_v0.py'
WF = '.github/workflows/q2_reference_acquisition_v0.yml'
SELECTION = PACK + 'profiles/q2_reference_subject_v0.json'
WORKLOAD = PACK + 'examples/q2_reference_field_extraction_v0/requests.json'
MODEL_MAP = PACK + 'profiles/q2_reference_model_files_v0.json'
LOCK = PACK + 'requirements-q2-reference-v0.lock'
DIAGNOSTIC = PACK + 'profiles/q2_reference_diagnostic_v0.json'
SCHEMA = 'schemas/metrics/q2_reference_qualification_v0.schema.json'
RECORD_DIR = PACK + 'examples/q2_runtime_preparation_v0/run_37148637546/'
RECORD_NAMES = ('preparation.json', 'q2-runtime-preparation-check.json',
                'q2_reference_model_files_v0.json', 'requirements-q2-reference-v0.lock')
SOURCES = tuple(sorted((SELF, CHECKER, WORKER, OLD_CHECKER, WF, SELECTION, WORKLOAD,
                        MODEL_MAP, LOCK, DIAGNOSTIC, SCHEMA, *(RECORD_DIR + n for n in RECORD_NAMES))))
REPOSITORY = 'HKati/pulse-release-gates-0.1'
PREPARATION_SOURCE = '77fc5d51896568db50a2a87f650711a65db8fe8c'
PREPARATION_RUN = '37148637546'
ARCHIVE_SHA = 'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9'
ARCHIVE_SIZE = 508460811
MAX_CONTROL = 16 * 1024 * 1024
STAGES = {'installer': 480, 'installcheck': 300, 'worker': 180, 'decodecheck': 180}
GENERATION_NS = 15_000_000_000
# The response still has exactly 15 seconds from the GO write boundary.
# This separate pre-armed backstop includes a bounded arming/cleanup allowance;
# it must never consume the response window or authorize a late response.
WATCHDOG_SECONDS = 20
PROPERTIES = {
    'User': '65534', 'Group': '65534', 'PrivateNetwork': 'yes',
    'RestrictAddressFamilies': 'AF_UNIX', 'SystemCallArchitectures': 'native',
    'SystemCallFilter': '~connect sendto sendmsg sendmmsg',
    'NoNewPrivileges': 'yes', 'CapabilityBoundingSet': '', 'ProtectSystem': 'strict',
    'ProtectHome': 'yes', 'PrivateDevices': 'yes', 'ProtectControlGroups': 'yes',
    'ProtectKernelTunables': 'yes', 'ProtectKernelModules': 'yes',
    'RestrictNamespaces': 'yes', 'RestrictSUIDSGID': 'yes', 'LockPersonality': 'yes',
    'RestrictRealtime': 'yes', 'InaccessiblePaths': '/run /tmp',
    'MemoryMax': '4294967296', 'MemorySwapMax': '0', 'TasksMax': '64',
    'CPUQuota': '100%', 'CPUQuotaPeriodSec': '100ms', 'LimitNOFILE': '256',
    'LimitFSIZE': '536870912', 'LimitCORE': '0',
    'KillMode': 'control-group', 'SendSIGKILL': 'yes', 'TimeoutStopSec': '1s',
}
OBSERVED_PROPERTIES = ('MainPID', 'PrivateNetwork', 'NoNewPrivileges', 'ProtectSystem',
    'ProtectHome', 'KillMode', 'SendSIGKILL', 'User', 'Group', 'CapabilityBoundingSet',
    'RestrictAddressFamilies', 'RuntimeMaxUSec')
# The wrapper cannot start the target before the parent has checked its actual
# process namespace, privileges, cgroup limits and systemd service properties.
BARRIER = r'''
import errno,json,os,socket,sys
blocked=[]
for family in (socket.AF_INET,socket.AF_INET6):
    try:
        s=socket.socket(family,socket.SOCK_STREAM);s.close();blocked.append(False)
    except OSError as e:
        blocked.append(e.errno in (errno.EPERM,errno.EACCES,errno.EAFNOSUPPORT))
print(json.dumps({'pid':os.getpid(),'ipv4_blocked':blocked[0],'ipv6_blocked':blocked[1]},separators=(',',':')),flush=True)
if sys.stdin.buffer.readline(16)!=b'EXEC\n':sys.exit(71)
os.execv(sys.argv[1],sys.argv[1:])
'''
# Standard-library bootstrap only. Both ensurepip and pip run inside the already
# verified network namespace. Its pip is recorded, not called an adopted wheel.
INSTALLER = r'''
import hashlib,json,os,pathlib,stat,subprocess,sys,venv
base,wh,lock,out=map(pathlib.Path,sys.argv[1:])
v=base/'venv'
venv.EnvBuilder(with_pip=True,symlinks=False).create(v)
# Python 3.11 ensurepip may install setuptools as a bootstrap convenience.
# It is not in the adopted closure and must not inject a startup .pth file.
with (out/'bootstrap-pip.log').open('xb') as log:
    removed=subprocess.run([str(v/'bin/python'),'-I','-B','-m','pip','--isolated',
        '--disable-pip-version-check','--no-input','uninstall','-y','setuptools'],
        stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=30)
    if removed.returncode:sys.exit(73)
    checked=subprocess.run([str(v/'bin/python'),'-I','-B','-c',
        "import importlib.metadata as m; assert {d.metadata['Name'].lower() for d in m.distributions()}=={'pip'}"],
        stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=30)
    if checked.returncode:sys.exit(74)
def remove_caches():
    for p in sorted(v.rglob('*'),reverse=True):
        if p.is_file() and p.suffix in ('.pyc','.pyo'):p.unlink()
        elif p.is_dir() and p.name=='__pycache__':p.rmdir()
def inventory():
    rows=[]
    for p in sorted(v.rglob('*')):
        rel=p.relative_to(v).as_posix()
        if p.is_symlink():
            if rel!='lib64' or os.readlink(p)!='lib':raise ValueError('bootstrap_link')
            rows.append({'path':rel,'symlink':'lib'})
        elif p.is_file():
            data=p.read_bytes()
            rows.append({'path':rel,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mode':stat.S_IMODE(p.stat().st_mode)})
    return rows
def save(name,value):
    with (out/name).open('x') as f:json.dump(value,f,sort_keys=True,separators=(',',':'));f.write('\n')
remove_caches()
save('bootstrap.json',inventory())
command=[str(v/'bin/python'),'-I','-B','-m','pip','--isolated','--disable-pip-version-check','--no-input',
         'install','--no-index','--find-links',str(wh),'--require-hashes','--only-binary=:all:',
         '--no-cache-dir','--no-compile','--force-reinstall','-r',str(lock),'--report',str(out/'pip-report.json')]
with (out/'pip-install.log').open('xb') as log:
    done=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=450)
if done.returncode:sys.exit(72)
remove_caches()
print('offline_installation_finished',flush=True)
'''


class NativeQualificationError(ValueError):
    pass


def require(test, code):
    if not test:
        raise NativeQualificationError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def strict_json(raw):
    require(len(raw) <= MAX_CONTROL and not raw.startswith(b'\xef\xbb\xbf'), 'control_json_bound')
    def pairs(values):
        out = {}
        for k, v in values:
            require(k not in out, 'duplicate_control_key'); out[k] = v
        return out
    def bad(_):
        raise NativeQualificationError('nonfinite_control_number')
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)
    # Roundtrip with allow_nan=False also rejects an overflowing JSON exponent.
    encode(obj)
    return obj


def safe_read(path, maximum=MAX_CONTROL):
    path = path.absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'linked_control_input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        require(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= maximum, 'control_input_bound')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            raw = f.read(maximum + 1)
        b = os.fstat(fd)
        require((a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) ==
                (b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns) and len(raw) == a.st_size,
                'control_input_changed')
        return raw
    finally:
        os.close(fd)


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())


def clean_env(home):
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(home),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PYTHONNOUSERSITE': '1',
            'PYTHONDONTWRITEBYTECODE': '1', 'PIP_CONFIG_FILE': '/dev/null',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'HF_HUB_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
            'TOKENIZERS_PARALLELISM': 'false', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}


def control(command, timeout=15, *, check=True):
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env={'PATH': os.defpath, 'LANG': 'C.UTF-8'}, timeout=timeout)
    if check:
        require(result.returncode == 0, 'external_control_failed')
    require(len(result.stdout) <= MAX_CONTROL, 'external_control_output_bound')
    return result


def check_context(repo, expected, env):
    require(os.geteuid() == 0, 'root_supervisor_required')
    require(re.fullmatch('[0-9a-f]{40}', expected), 'source_sha_shape')
    for key, value in {
        'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_ACTOR': 'HKati', 'GITHUB_TRIGGERING_ACTOR': 'HKati',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': expected, 'GITHUB_WORKFLOW_SHA': expected,
        'GITHUB_WORKFLOW_REF': f'{REPOSITORY}/{WF}@refs/heads/main', 'ImageOS': 'ubuntu24',
    }.items():
        require(env.get(key) == value, 'owner_dispatch_context_mismatch')
    run_id = env.get('GITHUB_RUN_ID', '')
    image = env.get('ImageVersion', '')
    require(re.fullmatch('[1-9][0-9]{0,19}', run_id) and re.fullmatch('[A-Za-z0-9_.-]{1,128}', image), 'run_image_identity')
    require(platform.python_implementation() == 'CPython' and platform.python_version() == '3.11.16', 'native_python_required')
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'native_platform_required')
    osr = platform.freedesktop_os_release()
    require(osr.get('ID') == 'ubuntu' and osr.get('VERSION_ID') == '24.04', 'native_os_required')
    require(Path('/proc/1/comm').read_text().strip() == 'systemd' and Path('/sys/fs/cgroup/cgroup.controllers').is_file(),
            'systemd_unified_cgroup_required')
    require(control(['/usr/bin/git', '--no-replace-objects', '-c', 'safe.directory=' + str(repo),
                     '-C', str(repo), 'rev-parse', 'HEAD']).stdout.decode().strip() == expected,
            'checkout_identity')
    require(Path(__file__).resolve() == (repo / SELF).resolve(), 'supervisor_source_location')
    return {'repository': REPOSITORY, 'source_commit': expected, 'workflow': WF, 'run_id': run_id,
            'run_attempt': 1, 'actor': 'HKati', 'event': 'workflow_dispatch', 'runner_image': image,
            'python': platform.python_version(), 'os': 'ubuntu-24.04', 'architecture': 'x86_64',
            'kernel': platform.release(), 'libc': list(platform.libc_ver()),
            'bootstrap_python_sha256': sha(safe_read(Path(sys.executable).resolve(strict=True), 128 * 1024 * 1024)),
            'origin': 'owner_dispatched_github_native_diagnostic'}


def snapshot_sources(repo, target, expected):
    rows = []
    for name in SOURCES:
        raw = safe_read(repo / name)
        original = control(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
            '-c', 'safe.directory=' + str(repo), '-c', 'core.hooksPath=/dev/null', '-C', str(repo), 'cat-file', 'blob', f'{expected}:{name}'], timeout=30).stdout
        require(raw == original, 'source_checkout_bytes')
        save(target / name, raw)
        rows.append({'path': name, 'size': len(raw), 'sha256': sha(raw)})
    return rows


def freeze(root):
    """Root owns the immutable inputs; model/installer UID cannot change them."""
    require(os.geteuid() == 0, 'freeze_requires_root')
    for p in [root, *root.rglob('*')]:
        if p.is_symlink():
            require(p.relative_to(root).as_posix() in ('lib64', 'venv/lib64') and os.readlink(p) == 'lib', 'unexpected_frozen_link')
            os.lchown(p, 0, 0)
        else:
            st = p.lstat()
            require(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode), 'unexpected_frozen_file')
            require(st.st_nlink == 1 or stat.S_ISDIR(st.st_mode), 'frozen_hardlink')
            os.chown(p, 0, 0)
            os.chmod(p, stat.S_IMODE(st.st_mode) & ~0o022)


def writable_directory(path):
    path.mkdir(mode=0o700)
    os.chown(path, 65534, 65534)


class BoundedReader:
    """Deadline-aware framing; no blocking readline and no unbounded capture."""
    def __init__(self, stream, limit=1024 * 1024):
        self.fd = stream.fileno(); self.buffer = b''; self.total = 0; self.limit = limit
        self.selector = selectors.DefaultSelector(); self.selector.register(self.fd, selectors.EVENT_READ)
        self.eof = False

    def line(self, deadline):
        while b'\n' not in self.buffer:
            if self.eof:
                require(not self.buffer, 'unterminated_protocol_record')
                raise NativeQualificationError('unexpected_protocol_eof')
            self._receive(deadline)
        line, self.buffer = self.buffer.split(b'\n', 1)
        return line + b'\n'

    def _receive(self, deadline):
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'external_deadline_expired')
        require(bool(self.selector.select(remaining)), 'external_deadline_expired')
        chunk = os.read(self.fd, 65536)
        if not chunk:
            self.eof = True
            return
        self.total += len(chunk)
        require(self.total <= self.limit, 'protocol_output_bound')
        self.buffer += chunk

    def finish(self, deadline):
        while not self.eof:
            self._receive(deadline)
        tail = self.buffer; self.buffer = b''
        return tail

    def close(self):
        self.selector.close()


def service_command(unit, stage, command, work, python):
    require(stage in STAGES and re.fullmatch(r'pulse-q2-[a-f0-9]{24}-[a-z]+\.service', unit), 'service_identity')
    props = {**PROPERTIES, 'RuntimeMaxSec': str(STAGES[stage]),
             'ReadWritePaths': str(work), 'WorkingDirectory': str(work)}
    args = ['/usr/bin/systemd-run', '--quiet', '--pipe', '--wait', '--unit=' + unit]
    args += ['--property=' + k + '=' + v for k, v in props.items()]
    args += ['/usr/bin/env', '-i', *(k + '=' + v for k, v in clean_env(work).items()),
             str(python), '-I', '-B', '-c', BARRIER, *map(str, command)]
    return args


def observe_service(unit, stage, frame, host_netns):
    require(type(frame) is dict and set(frame) == {'pid', 'ipv4_blocked', 'ipv6_blocked'}, 'isolation_barrier_fields')
    pid = frame['pid']
    require(type(pid) is int and pid > 1 and frame['ipv4_blocked'] is True and frame['ipv6_blocked'] is True,
            'network_family_filter_unavailable')
    result = control(['/usr/bin/systemctl', 'show', unit, '--no-pager',
                      '--property=' + ','.join(OBSERVED_PROPERTIES)])
    props = dict(line.split('=', 1) for line in result.stdout.decode().splitlines() if '=' in line)
    require(props.pop('MainPID', '') == str(pid), 'service_pid_substitution')
    for key in ('PrivateNetwork', 'NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'KillMode',
                'SendSIGKILL', 'User', 'Group', 'CapabilityBoundingSet', 'RestrictAddressFamilies'):
        require(props.get(key) == PROPERTIES[key], 'service_property_not_enforced')
    require(props.get('RuntimeMaxUSec') == {180: '3min', 300: '5min', 480: '8min'}[STAGES[stage]], 'runtime_max_not_enforced')
    child_netns = os.readlink(f'/proc/{pid}/ns/net')
    require(child_netns != host_netns, 'network_namespace_not_isolated')
    status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
    require(status.get('Uid', '').split() == ['65534'] * 4 and status.get('Gid', '').split() == ['65534'] * 4,
            'service_privilege_not_dropped')
    require(status.get('NoNewPrivs', '').strip() == '1' and status.get('CapEff', '').strip() == '0000000000000000',
            'service_privileges_not_bounded')
    cgroups = Path(f'/proc/{pid}/cgroup').read_text().splitlines()
    require(len(cgroups) == 1 and cgroups[0].startswith('0::/'), 'unified_cgroup_missing')
    cgroup = cgroups[0][3:]
    require(cgroup.endswith('/' + unit) and '..' not in Path(cgroup).parts, 'service_cgroup_identity')
    root = Path('/sys/fs/cgroup') / cgroup.lstrip('/')
    values = {k: (root / filename).read_text().strip() for k, filename in
              {'memory_max': 'memory.max', 'memory_swap_max': 'memory.swap.max',
               'pids_max': 'pids.max', 'cpu_max': 'cpu.max'}.items()}
    require(values == {'memory_max': '4294967296', 'memory_swap_max': '0',
                       'pids_max': '64', 'cpu_max': '100000 100000'}, 'cgroup_limits_not_enforced')
    return {'stage': stage, 'unit': unit, 'pid': pid, 'host_netns': host_netns, 'child_netns': child_netns,
            'uid': 65534, 'no_new_privs': True, 'capabilities': '0000000000000000',
            'ipv4_blocked': frame['ipv4_blocked'], 'ipv6_blocked': frame['ipv6_blocked'],
            **values, 'properties': props}


STARTUP_DIAGNOSTIC_SECONDS = 2.0
STARTUP_DIAGNOSTIC_BYTES = 64 * 1024
STARTUP_DIAGNOSTIC_REAP_SECONDS = 1.0
STARTUP_STATUS_PROPERTIES = (
    'Id', 'LoadState', 'ActiveState', 'SubState', 'Result', 'MainPID',
    'ExecMainCode', 'ExecMainStatus', 'ExecMainStartTimestamp',
    'ExecMainExitTimestamp',
)


def bounded_startup_diagnostic(command):
    """Retain a bounded raw prefix; a diagnostic never grants authority.

    Do not use control()/communicate(): their PIPE capture is only size-checked
    after allocation. Both stderr and stdout share this in-flight byte budget.
    A fresh process group bounds descendants even if its leader exits early.
    """
    deadline = time.monotonic() + STARTUP_DIAGNOSTIC_SECONDS
    proc = None; selector = None; raw = bytearray()
    result = {'command': list(command), 'capture_status': 'unavailable',
              'exit_code': None, 'output_limit_bytes': STARTUP_DIAGNOSTIC_BYTES,
              'timeout_seconds': STARTUP_DIAGNOSTIC_SECONDS,
              'reap_timeout_seconds': STARTUP_DIAGNOSTIC_REAP_SECONDS}
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
                 'SYSTEMD_PAGER': 'cat', 'SYSTEMD_COLORS': '0'}, bufsize=0)
        selector = selectors.DefaultSelector()
        os.set_blocking(proc.stdout.fileno(), False)
        selector.register(proc.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                result['capture_status'] = 'timeout'; break
            chunk = os.read(proc.stdout.fileno(), min(16384, STARTUP_DIAGNOSTIC_BYTES + 1 - len(raw)))
            if not chunk:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    result['capture_status'] = 'timeout'; break
                result['exit_code'] = proc.wait(timeout=remaining)
                result['capture_status'] = 'complete' if result['exit_code'] == 0 else 'command_failed'
                break
            raw.extend(chunk)
            if len(raw) > STARTUP_DIAGNOSTIC_BYTES:
                del raw[STARTUP_DIAGNOSTIC_BYTES:]
                result['capture_status'] = 'output_limit'; break
    except subprocess.TimeoutExpired:
        result['capture_status'] = 'timeout'
    except Exception as exc:
        # Preserve only the class, not a possibly credential-bearing message.
        result['capture_error_type'] = type(exc).__name__
    finally:
        if proc is not None:
            # Never wait for EOF from a surviving descendant after a timeout.
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            except OSError as exc: result['kill_error_type'] = type(exc).__name__
            try: proc.wait(timeout=STARTUP_DIAGNOSTIC_REAP_SECONDS)
            except subprocess.SubprocessError as exc: result['reap_error_type'] = type(exc).__name__
            if proc.stdout is not None: proc.stdout.close()
        if selector is not None: selector.close()
    # An exit caused by our diagnostic cleanup is not an observed service exit.
    result['output_bytes'] = len(raw); result['output_sha256'] = sha(raw)
    return result, bytes(raw)


def startup_diagnostic_command(unit, kind):
    require(re.fullmatch(r'pulse-q2-[a-f0-9]{24}-[a-z]+\.service', unit), 'service_identity')
    if kind == 'status':
        return ['/usr/bin/systemctl', 'show', '--no-pager',
                '--property=' + ','.join(STARTUP_STATUS_PROPERTIES), '--', unit]
    require(kind == 'journal', 'startup_diagnostic_kind')
    # --unit also retains PID 1's messages ABOUT the service. A bare
    # _SYSTEMD_UNIT match would omit precisely those early setup failures.
    return ['/usr/bin/journalctl', '--boot=0', '--no-pager', '--quiet',
            '--lines=80', '--output=short-iso-precise', '--unit=' + unit]


def preserve_startup_failure(service, phase, error, log):
    """Snapshot before stop/reset, always clean up, then publish raw evidence.

    At most two read-only diagnostic commands, each 2s + 1s reap. The first
    bounded snapshot precedes cleanup so stop cannot erase the original status.
    No diagnostic file flush occurs before service.close(). The journal is read
    afterwards; unavailable/truncated data remains explicitly non-authorizing.
    """
    code = str(error) if isinstance(error, NativeQualificationError) else ''
    record = {'record_type': 'q2_native_startup_failure_v0',
              'unit': service.unit, 'stage': service.stage, 'startup_phase': phase,
              'error_code': code if re.fullmatch(r'[a-z0-9_]{1,128}', code) else 'startup_exception',
              'exception_type': type(error).__name__, 'authority_effect': 'none',
              'native_runtime_qualified': False, 'capture_dispatch_authorized': False,
              'client_exit_code_before_cleanup': None, 'client_exit_code_after_cleanup': None,
              'diagnostics': {}}
    captures = []
    def capture(kind, timing):
        metadata = {'observation_timing': timing, 'capture_status': 'unavailable'}
        record['diagnostics'][kind] = metadata
        try:
            command = startup_diagnostic_command(service.unit, kind)
            captured, raw = bounded_startup_diagnostic(command)
            metadata.update(captured)
            name = service.stage + '-startup-' + kind + '.log'
            metadata['path'] = name
            captures.append((name, raw, metadata))
        except Exception as exc:
            metadata['capture_error_type'] = type(exc).__name__
    try:
        if service.process is not None:
            record['client_exit_code_before_cleanup'] = service.process.poll()
        capture('status', 'before_service_cleanup')
    except Exception as exc:
        record['snapshot_error_type'] = type(exc).__name__
    finally:
        try:
            service._startup_cleanup_attempted = True
            service.close()
        except Exception as exc:
            record['cleanup_error_type'] = type(exc).__name__
    if service.process is not None:
        record['client_exit_code_after_cleanup'] = service.process.poll()
    capture('journal', 'after_service_cleanup')
    # Keep raw bytes separate from interpretation, including invalid UTF-8.
    for name, raw, metadata in captures:
        try:
            save(log.parent / name, raw)
            metadata['published'] = True
        except Exception as exc:
            metadata['published'] = False
            metadata['publication_error_type'] = type(exc).__name__
    save(log.parent / (service.stage + '-startup-failure.json'), encode(record))


class Service:
    def __init__(self, prefix, stage, command, work, python, log, phase_deadline):
        self.stage = stage; self.unit = prefix + '-' + stage + '.service'
        # Taken before launching systemd: a conservative lower bound on its
        # RuntimeMaxSec expiry, not the client's additional exit/cleanup margin.
        self.runtime_deadline_ns = time.monotonic_ns() + STAGES[stage] * 1_000_000_000
        self.deadline = min(phase_deadline, self.runtime_deadline_ns / 1e9 + 5)
        self.log = log.open('xb'); self.process = None; self.reader = None
        startup_phase = 'service_launch'
        try:
            self.process = subprocess.Popen(service_command(self.unit, stage, command, work, python),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                env={'PATH': os.defpath, 'LANG': 'C.UTF-8'}, start_new_session=True, bufsize=0)
            startup_phase = 'barrier_read'
            self.reader = BoundedReader(self.process.stdout)
            frame = strict_json(self.reader.line(min(self.deadline, time.monotonic() + 20)))
            startup_phase = 'isolation_observation'
            self.observation = observe_service(self.unit, stage, frame, os.readlink('/proc/self/ns/net'))
            startup_phase = 'exec_authorization'
            self.send(b'EXEC\n')
        except BaseException as exc:
            self._startup_cleanup_attempted = False
            try:
                preserve_startup_failure(self, startup_phase, exc, log)
            except BaseException:
                # Diagnostic/publication failure must not replace the original
                # cause or skip mandatory cleanup. It never permits a retry.
                if not self._startup_cleanup_attempted:
                    try: self.close()
                    except BaseException: pass
                try: print('Q2 startup failure diagnostics unavailable; original failure retained', file=sys.stderr)
                except Exception: pass
            raise

    def send(self, data):
        require(type(data) is bytes and 0 < len(data) <= 512, 'control_command_bound')
        require(self.process.poll() is None, 'service_terminated_before_command')
        # Both fixed commands fit the POSIX atomic-pipe-write minimum. Do not
        # let a blocked stdin write or buffered flush hide in the timing boundary.
        fd = self.process.stdin.fileno()
        os.set_blocking(fd, False)
        # Timestamp before the atomic write: a post-write scheduler pause must
        # not move the deadline forward after the child was already authorized.
        authorization_ns = time.monotonic_ns()
        try:
            written = os.write(fd, data)
        except BlockingIOError as exc:
            raise NativeQualificationError('control_pipe_not_writable') from exc
        require(written == len(data), 'incomplete_control_write')
        return authorization_ns

    def complete(self, *, empty_tail=False, deadline=None):
        deadline = min(self.deadline, deadline or self.deadline)
        tail = self.reader.finish(deadline)
        if empty_tail:
            require(tail == b'', 'extra_worker_output')
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'external_deadline_expired')
        rc = self.process.wait(timeout=remaining)
        require(rc == 0, 'isolated_service_failed')
        return tail, rc

    def close(self):
        # Kill the full systemd cgroup, including descendants, not just a Python
        # timer thread or the systemd-run client process. Stop even on failure.
        for command in (['/usr/bin/systemctl', 'kill', '--kill-whom=all', '--signal=KILL', self.unit],
                        ['/usr/bin/systemctl', 'stop', self.unit]):
            try: control(command, timeout=10, check=False)
            except (OSError, subprocess.SubprocessError, NativeQualificationError): pass
        if self.process is not None:
            if self.process.poll() is None:
                try: os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: pass
            for stream in (self.process.stdin, self.process.stdout):
                if stream: stream.close()
        if self.reader: self.reader.close()
        self.log.close()


def watchdog(prefix, worker_unit):
    unit = prefix + '-watchdog'
    control(['/usr/bin/systemd-run', '--quiet', '--unit=' + unit, '--on-active=' + str(WATCHDOG_SECONDS) + 's',
             '--timer-property=AccuracySec=1us', '--timer-property=RandomizedDelaySec=0',
             '/usr/bin/systemctl', 'kill', '--kill-whom=all', '--signal=KILL', worker_unit])
    control(['/usr/bin/systemctl', 'is-active', '--quiet', unit + '.timer'])
    return unit + '.timer'


def remove_watchdog(prefix):
    try:
        control(['/usr/bin/systemctl', 'stop', prefix + '-watchdog.timer', prefix + '-watchdog.service'], check=False)
    except (OSError, subprocess.SubprocessError, NativeQualificationError):
        pass


def exchange_diagnostic(service, prefix, output, phase_deadline):
    """One GO; no fsync/control call inside the 15-second response interval.

    The intent is durable before GO. Its observed write-boundary time and original
    response are retained after stopping the worker, including failure paths.
    The pre-armed timer is a separate bounded fail-stop backstop; acceptance
    never uses its longer interval as the generation budget.
    """
    start_record = None; response_raw = None; observation = None
    try:
        save(output / 'worker-sandbox.json', encode(service.observation))
        save(output / 'generation-intent.json', encode({
            'call_id': 'diagnostic-0001', 'attempt': 1, 'generation_seconds': 15,
            'state': 'permission_recorded_before_GO', 'scored': False, 'retries': 0}))
        arm_begin = time.monotonic_ns()
        timer = watchdog(prefix, service.unit)
        # OnActiveSec cannot start before its creation request. Never grant GO
        # unless even this earliest possible expiry leaves the complete window.
        # The existing whole-worker and phase caps must also leave that window.
        ceiling = min(arm_begin + WATCHDOG_SECONDS * 1_000_000_000,
                      service.runtime_deadline_ns, int(phase_deadline * 1e9))
        require(time.monotonic_ns() + GENERATION_NS < ceiling,
                'full_generation_window_unavailable')
        generation_start = service.send(b'GENERATE diagnostic-0001\n')
        generation_deadline = generation_start + GENERATION_NS
        start_record = {'call_id': 'diagnostic-0001', 'attempt': 1,
            'generation_start_ns': generation_start, 'generation_deadline_ns': generation_deadline,
            'watchdog_unit': timer, 'watchdog_armed': True,
            'watchdog_arm_begin_ns': arm_begin,
            'watchdog_earliest_deadline_ns': arm_begin + WATCHDOG_SECONDS * 1_000_000_000,
            'state': 'GO_written_timing_retained_after_worker_stop'}
        # Also reject loss of the full window before the nonblocking write.
        # Such an incomplete attempt is stopped, never given a shorter window
        # and then reported as a successful qualification.
        require(generation_deadline < ceiling, 'full_generation_window_unavailable')
        response_raw = service.reader.line(generation_deadline / 1e9)
        received = time.monotonic_ns()
        require(received <= generation_deadline, 'late_generation_response')
        # A timely original response ends the response budget. Process exit has
        # only the remainder of the already-armed backstop/stage/phase caps;
        # no deadline is extended and no second model call is authorized.
        _, rc = service.complete(empty_tail=True, deadline=ceiling / 1e9)
        observation = {'sandbox': service.observation, 'generation_start_ns': generation_start,
                       'response_received_ns': received, 'generation_deadline_ns': generation_deadline,
                       'watchdog_armed': True, 'watchdog_unit': timer, 'worker_exit_code': rc}
    finally:
        # Stop before any potentially slow evidence flush, including rejection
        # paths. Preserve a received response even when it is late or exit fails.
        try:
            service.close()
        finally:
            remove_watchdog(prefix)
            if start_record is not None:
                save(output / 'generation-start.json', encode(start_record))
            if response_raw is not None:
                save(output / 'original-response.json', response_raw)
            if observation is not None:
                save(output / 'occurrence.json', encode(observation))
    return response_raw


def bounded_local(command, log, deadline):
    """Stdlib input checker is also externally bounded before model installation."""
    seconds = min(180.0, deadline - time.monotonic())
    require(seconds > 0, 'phase_budget_exhausted')
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
        resource.setrlimit(resource.RLIMIT_FSIZE, (536870912, 536870912))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with log.open('xb') as out:
        proc = subprocess.Popen(list(map(str, command)), stdin=subprocess.DEVNULL, stdout=out, stderr=out,
            env=clean_env(log.parent), start_new_session=True, preexec_fn=limits)
        try:
            require(proc.wait(timeout=seconds) == 0, 'input_checker_rejected')
        finally:
            # Also terminate descendants if the leader already exited.
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=5)


def run_service(prefix, stage, command, work, python, output, deadline):
    service = Service(prefix, stage, command, work, python, output / (stage + '.log'), deadline)
    try:
        service.complete()
        save(output / (stage + '-sandbox.json'), encode(service.observation))
        return service.observation
    finally:
        service.close()


def qualify(repo, archive, output, expected, confirmed):
    require(confirmed, 'explicit_unscored_diagnostic_confirmation_required')
    repo = repo.resolve(strict=True); archive = archive.absolute(); output = output.absolute()
    require(not output.exists() and not output.is_symlink() and not output.is_relative_to(repo), 'output_not_fresh_external_directory')
    require(not any(p.is_symlink() for p in output.parents), 'output_parent_link')
    context = check_context(repo, expected, dict(os.environ))
    destination = output
    destination.mkdir(mode=0o700)
    start_ns = time.monotonic_ns(); deadline = time.monotonic() + 1200
    prefix = 'pulse-q2-' + uuid.uuid4().hex[:24]
    stage_root = Path(tempfile.mkdtemp(prefix=prefix + '-', dir='/var/tmp'))
    stage_root.chmod(0o755)
    # ProtectHome=yes deliberately hides the runner's home/temp directories.
    # Services read root-owned evidence in /var/tmp; only final publication
    # copies it into RUNNER_TEMP. Never weaken ProtectHome to expose the checkout.
    output = stage_root / 'evidence'
    output.mkdir(mode=0o755)
    terminal = 'failed'; error_code = 'incomplete'; service = None
    python = Path(sys.executable).resolve(strict=True)
    try:
        sources = stage_root / 'source'; source_rows = snapshot_sources(repo, sources, expected)
        freeze(sources)
        raw = safe_read(archive, ARCHIVE_SIZE)
        require(len(raw) == ARCHIVE_SIZE and sha(raw) == ARCHIVE_SHA, 'original_archive_digest')
        copy_archive = stage_root / 'original.zip'; save(copy_archive, raw); del raw
        preflight_path = output / 'input-check.json'
        bounded_local([python, '-I', '-B', sources / CHECKER, 'verify-inputs',
            '--archive', copy_archive, '--staging', stage_root / 'staged', '--source-root', sources,
            '--repo-root', repo, '--expected-source-sha', expected, '--output', preflight_path],
            output / 'input-check.log', deadline)
        preflight = strict_json(safe_read(preflight_path))
        require(preflight['source_files'] == source_rows and preflight['preparation_source_commit'] == PREPARATION_SOURCE,
                'input_checker_source_identity')
        bundle = stage_root / 'staged/bundle'
        # The root staging directory was intentionally private during extraction;
        # only the verified, frozen payload subtree becomes readable by services.
        (stage_root / 'staged').chmod(0o755); bundle.chmod(0o755); freeze(bundle)
        install_work = stage_root / 'install'; writable_directory(install_work)
        run_service(prefix, 'installer', [python, '-I', '-B', '-c', INSTALLER,
            install_work, bundle / 'wheelhouse', sources / LOCK, install_work],
            install_work, python, output, deadline)
        venv = install_work / 'venv'
        freeze(venv)
        for name in ('bootstrap.json', 'bootstrap-pip.log', 'pip-report.json', 'pip-install.log'):
            save(output / name, safe_read(install_work / name))
        # Nobody must not retain a writable parent from which to replace the venv.
        freeze(install_work); install_work.chmod(0o755)
        checking = stage_root / 'installcheck'; writable_directory(checking)
        install_command = [python, '-I', '-B', sources / CHECKER, 'verify-installation',
            '--venv', venv, '--bundle', bundle, '--bootstrap-inventory', output / 'bootstrap.json',
            '--pip-report', output / 'pip-report.json', '--output', checking / 'installation.json']
        # Evidence is readable, but remains root-owned outside writable service paths.
        output.chmod(0o755)
        run_service(prefix, 'installcheck', install_command, checking, python, output, deadline)
        installation_raw = safe_read(checking / 'installation.json')
        installation = strict_json(installation_raw)
        save(output / 'installation.json', installation_raw)
        freeze(checking)
        selected = safe_read(sources / SELECTION); workload = safe_read(sources / WORKLOAD)
        prelaunch = {'record_type': 'q2_native_prelaunch_v0', 'context': context, 'source_files': source_rows,
            'preparation_source_commit': PREPARATION_SOURCE, 'preparation_run_id': PREPARATION_RUN,
            'artifact_sha256': ARCHIVE_SHA, 'selection_sha256': sha(selected), 'workload_sha256': sha(workload),
            'diagnostic_sha256': sha(safe_read(sources / DIAGNOSTIC)), 'installation_sha256': sha(installation_raw),
            'environment_inventory_sha256': sha(encode(installation['inventory'])),
            'limits': {'generation_seconds': 15, 'phase_seconds': 1200, 'memory_bytes': 4294967296, 'tasks': 64},
            'authority_effect': 'none', 'production_gate_eligible': False, 'scored_call_count': 0}
        pre_raw = encode(prelaunch); save(output / 'prelaunch.json', pre_raw)
        worker_work = stage_root / 'worker'; writable_directory(worker_work)
        service = Service(prefix, 'worker', [venv / 'bin/python', '-I', '-B', sources / WORKER,
            '--source-root', sources, '--bundle', bundle, '--prelaunch', output / 'prelaunch.json',
            '--expected-prelaunch-sha256', sha(pre_raw)], worker_work, python, output / 'worker.log', deadline)
        ready_raw = service.reader.line(min(service.deadline, deadline))
        ready = strict_json(ready_raw)
        require(ready.get('record_type') == 'q2_native_model_ready_v0', 'model_ready_required')
        save(output / 'model-ready.json', ready_raw)
        # exchange_diagnostic owns cleanup even when authorization/receipt fails.
        worker_service = service; service = None
        response_raw = exchange_diagnostic(worker_service, prefix, output, deadline)
        response = strict_json(response_raw)
        save(output / 'original-continuation.utf8', response['text'].encode('utf-8'))
        decode_work = stage_root / 'decodecheck'; writable_directory(decode_work)
        run_service(prefix, 'decodecheck', [venv / 'bin/python', '-I', '-B', sources / CHECKER, 'verify-diagnostic',
            '--source-root', sources, '--bundle', bundle, '--venv', venv,
            '--prelaunch', output / 'prelaunch.json', '--installation', output / 'installation.json',
            '--response', output / 'original-response.json', '--ready', output / 'model-ready.json',
            '--observation', output / 'occurrence.json',
            '--bootstrap-inventory', output / 'bootstrap.json', '--pip-report', output / 'pip-report.json',
            '--installer-observation', output / 'installer-sandbox.json',
            '--installcheck-observation', output / 'installcheck-sandbox.json',
            '--expected-source-sha', expected, '--expected-run-id', context['run_id'],
            '--expected-source-inventory-sha256', sha(encode(source_rows)),
            '--expected-prelaunch-sha256', sha(pre_raw),
            '--expected-response-sha256', sha(response_raw), '--output', decode_work / 'diagnostic-check.json'],
            decode_work, python, output, deadline)
        checked_raw = safe_read(decode_work / 'diagnostic-check.json'); checked = strict_json(checked_raw)
        require(checked.get('native_runtime_qualified') is True
                and checked.get('original_decoding_verified') is True
                and checked.get('single_unscored_diagnostic_verified') is True
                and checked.get('response_sha256') == sha(response_raw)
                and checked.get('prelaunch_sha256') == sha(pre_raw), 'diagnostic_checker_rejected')
        save(output / 'diagnostic-check.json', checked_raw)
        require(time.monotonic() <= deadline, 'phase_budget_exhausted')
        # A bounded source snapshot makes later offline replay independent of a
        # moving checkout. Model/wheel payloads stay in the original artifact.
        for row in source_rows:
            save(output / 'source' / row['path'], safe_read(sources / row['path']))
        terminal = 'qualified'; error_code = None
    except NativeQualificationError as exc:
        error_code = str(exc)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        error_code = 'runtime_or_evidence_unavailable'
    finally:
        if service is not None: service.close()
        remove_watchdog(prefix)
        evidence = []
        for p in sorted(output.rglob('*')):
            if p.is_file() and not p.is_symlink():
                raw = safe_read(p)
                evidence.append({'path': p.relative_to(output).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
        report = {'record_type': 'q2_reference_qualification_v0', 'status': terminal,
            'native_runtime_qualified': terminal == 'qualified', 'diagnostic_call_limit': 1,
            'scored_call_count': 0, 'capture_dispatch_authorized': False,
            'production_gate_eligible': False, 'authority_effect': 'none', 'error_code': error_code,
            'context': context, 'preparation_source_commit': PREPARATION_SOURCE,
            'preparation_run_id': PREPARATION_RUN, 'artifact_sha256': ARCHIVE_SHA,
            'phase_start_ns': start_ns, 'phase_end_ns': time.monotonic_ns(), 'evidence': evidence,
            'limitations': ['GitHub host and bootstrap CPython/pip remain trusted',
                            'one diagnostic does not establish 150-call capture viability',
                            'no score, acquisition completeness, release admission or malicious-platform proof']}
        save(output / 'qualification.json', encode(report))
        # Return byte-identical artifacts to the invoking owner only after all
        # services have stopped. The live evidence directory is never below home.
        for p in sorted(output.rglob('*')):
            if p.is_file():
                save(destination / p.relative_to(output), safe_read(p))
        uid = int(os.environ.get('SUDO_UID', os.getuid()))
        gid = int(os.environ.get('SUDO_GID', os.getgid()))
        for p in [destination, *destination.rglob('*')]:
            os.chown(p, uid, gid); os.chmod(p, 0o700 if p.is_dir() else 0o600)
        shutil.rmtree(stage_root)
    print('Q2 native diagnostic qualification ' + terminal + '; no scored capture or release authority')
    return 0 if terminal == 'qualified' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    native = sub.add_parser('qualify-runtime')
    native.add_argument('--repo-root', type=Path, required=True)
    native.add_argument('--archive', type=Path, required=True)
    native.add_argument('--output-dir', type=Path, required=True)
    native.add_argument('--expected-source-sha', required=True)
    native.add_argument('--confirm-one-unscored-diagnostic', action='store_true')
    args = parser.parse_args(argv)
    def terminated(signum, frame):
        raise NativeQualificationError('external_phase_timeout')
    signal.signal(signal.SIGTERM, terminated)
    try:
        return qualify(args.repo_root, args.archive, args.output_dir, args.expected_source_sha,
                       args.confirm_one_unscored_diagnostic)
    except (NativeQualificationError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Q2 qualification refused before native execution', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
