#!/usr/bin/env python3
"""Finite Q3 native lifecycle; no Q2 runtime import or mutation.

Isolation/install patterns derived from qualify_q2_reference_runtime_v0.py at
Git blob f060a7c5d7086c33556af1ca3b60c5c50fbd9cb2 (Apache-2.0 repository code).
Q3 limits and protocol are separately declared; no historical-host equality.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

_spec = importlib.util.spec_from_file_location('q3_capture_contract', Path(__file__).with_name('q3_native_capture_contract_v0.py'))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
require = C.require
NativeQualificationError = C.ContractError
strict_json = C.strict_json
safe_read = C.safe_read
sha = C.digest
encode = C.encode
MAX_CONTROL = C.MAX_CONTROL
STAGES = {'installer': 480, 'installcheck': 300, 'preflight': 300, 'decodecheck': 300}
CAPTURE_STAGES = {}
PROPERTIES = {
    'User': '65534', 'Group': '65534', 'PrivateNetwork': 'yes',
    'RestrictAddressFamilies': 'AF_UNIX', 'SystemCallArchitectures': 'native',
    'SystemCallFilter': '~connect sendto sendmsg sendmmsg',
    'NoNewPrivileges': 'yes', 'CapabilityBoundingSet': '', 'ProtectSystem': 'strict',
    'ProtectHome': 'yes', 'PrivateDevices': 'yes', 'ProtectControlGroups': 'yes',
    'ProtectKernelTunables': 'yes', 'ProtectKernelModules': 'yes',
    'RestrictNamespaces': 'yes', 'RestrictSUIDSGID': 'yes', 'LockPersonality': 'yes',
    'RestrictRealtime': 'yes', 'InaccessiblePaths': '/tmp',
    'TemporaryFileSystem': '/run:rw,nosuid,nodev,noexec,size=16M,mode=0755',
    'MemoryMax': '4294967296', 'MemorySwapMax': '0', 'TasksMax': '64',
    'CPUQuota': '100%', 'CPUQuotaPeriodSec': '100ms', 'LimitNOFILE': '256',
    'LimitFSIZE': '536870912', 'LimitCORE': '0',
    'KillMode': 'control-group', 'SendSIGKILL': 'yes', 'TimeoutStopSec': '1s',
}


OBSERVED_PROPERTIES = ('MainPID', 'PrivateNetwork', 'NoNewPrivileges', 'ProtectSystem',
    'ProtectHome', 'KillMode', 'SendSIGKILL', 'User', 'Group', 'CapabilityBoundingSet',
    'RestrictAddressFamilies', 'RuntimeMaxUSec')


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


def service_command(unit, stage, command, work, python, *, capture_seconds=None):
    require((stage in STAGES or stage in CAPTURE_STAGES or stage == 'captureworker') and re.fullmatch(r'pulse-q3-[a-f0-9]{24}-[a-z]+\.service', unit), 'service_identity')
    if stage == 'captureworker':
        require(type(capture_seconds) is int and 1 <= capture_seconds <= 14400, 'capture_lifetime_bound')
        seconds = capture_seconds
    else:
        require(capture_seconds is None, 'no_generic_runtime_override')
        seconds = {**STAGES, **CAPTURE_STAGES}[stage]
    props = {**PROPERTIES, 'RuntimeMaxSec': str(seconds),
             'ReadWritePaths': str(work), 'WorkingDirectory': str(work)}
    args = ['/usr/bin/systemd-run', '--quiet', '--pipe', '--wait', '--unit=' + unit]
    args += ['--property=' + k + '=' + v for k, v in props.items()]
    args += ['/usr/bin/env', '-i', *(k + '=' + v for k, v in clean_env(work).items()),
             str(python), '-I', '-B', '-c', BARRIER, *map(str, command)]
    return args


RUN_MOUNTINFO_BYTES = 256 * 1024


RUN_MOUNTINFO_LINES = 4096


def run_mount_entries(text):
    require(type(text) is str and 0 < len(text.encode('utf-8')) <= RUN_MOUNTINFO_BYTES
            and text.endswith('\n') and '\x00' not in text, 'run_mountinfo_bound')
    lines = text.splitlines()
    require(0 < len(lines) <= RUN_MOUNTINFO_LINES, 'run_mountinfo_bound')
    entries = []; identifiers = set()
    def path(word):
        require(re.search(r'\\(?!040|011|012|134)', word) is None, 'run_mountinfo_escape')
        value = re.sub(r'\\(040|011|012|134)', lambda m: chr(int(m[1], 8)), word)
        require(value.startswith('/') and (value == '/' or
                all(p not in ('', '.', '..') for p in value[1:].split('/'))), 'run_mountinfo_path')
        return value
    for line in lines:
        parts = line.split(' ')
        require(parts.count('-') == 1, 'run_mountinfo_record')
        pivot = parts.index('-')
        require(pivot >= 6 and len(parts) == pivot + 4 and all(parts)
                and re.fullmatch(r'[1-9][0-9]*', parts[0])
                and re.fullmatch(r'[1-9][0-9]*', parts[1])
                and re.fullmatch(r'(0|[1-9][0-9]*):(0|[1-9][0-9]*)', parts[2]), 'run_mountinfo_record')
        require(parts[0] not in identifiers, 'run_mountinfo_duplicate_id')
        identifiers.add(parts[0])
        entries.append({'device': parts[2], 'root': path(parts[3]), 'target': path(parts[4]),
                        'options': set(parts[5].split(',')), 'fstype': parts[pivot + 1],
                        'super_options': parts[pivot + 3].split(',')})
    return entries


def validate_run_mount(value, unit):
    require(type(unit) is str and re.fullmatch(r'pulse-q3-[a-f0-9]{24}-[a-z]+\.service', unit), 'service_identity')
    require(type(value) is dict and set(value) == {'host_namespace', 'child_namespace',
            'host_mountinfo', 'child_mountinfo', 'mount_stats'}, 'run_mount_fields')
    require(all(type(value[k]) is str and re.fullmatch(r'mnt:\[[1-9][0-9]*\]', value[k])
            for k in ('host_namespace', 'child_namespace'))
            and value['host_namespace'] != value['child_namespace'], 'mount_namespace_not_separate')
    host = run_mount_entries(value['host_mountinfo'])
    child = run_mount_entries(value['child_mountinfo'])
    run = [e for e in child if e['target'] == '/run']
    require(len(run) == 1, 'run_mount_missing_or_stacked')
    run = run[0]
    require(run['fstype'] == 'tmpfs' and run['root'] == '/'
            and run['device'].startswith('0:') and run['device'] != '0:0'
            and run['device'] not in {e['device'] for e in host}, 'host_run_not_hidden')
    require({'nosuid', 'nodev', 'noexec'} <= run['options']
            and not ({'suid', 'dev', 'exec'} & run['options'])
            and len(run['options'] & {'ro', 'rw'}) == 1, 'run_mount_flags')
    sizes = [o for o in run['super_options'] if o.startswith('size=')]
    require(len(sizes) == 1, 'run_tmpfs_size')
    size = re.fullmatch(r'size=([1-9][0-9]*)([kKmMgG]?)', sizes[0])
    require(size is not None and int(size[1]) * (1024 ** {'': 0, 'k': 1, 'm': 2, 'g': 3}[size[2].lower()])
            == 16 * 1024 * 1024, 'run_tmpfs_size')
    mounts = [e for e in child if e['target'] == '/run' or e['target'].startswith('/run/')]
    targets = [e['target'] for e in mounts]
    require(len(mounts) <= 4 and len(set(targets)) == len(targets), 'run_submount_scope')
    stats = value['mount_stats']
    require(type(stats) is dict and set(stats) == set(targets), 'run_mount_stat_scope')
    for entry in mounts:
        target = entry['target']; s = stats[target]
        require(type(s) is dict and set(s) == {'device', 'inode', 'uid', 'gid', 'mode'}
                and type(s['device']) is str and s['device'] == entry['device']
                and all(type(s[k]) is int for k in ('inode', 'uid', 'gid', 'mode'))
                and s['inode'] > 0 and s['uid'] == 0 and s['gid'] == 0
                and stat.S_ISDIR(s['mode']), 'run_mount_stat')
        if target == '/run':
            require(s['mode'] == stat.S_IFDIR | 0o755, 'run_root_permissions')
            continue
        # systemd >=252 needs its per-unit incoming bind mount even with an
        # empty /run. It is root-only (0600), never traversable by UID 65534.
        # ProtectHome / credential masks may also remain as inert 0000 dirs.
        # Do not forbid this necessary plumbing or allow arbitrary host binds.
        require('ro' in entry['options'] and 'rw' not in entry['options'], 'run_submount_writable')
        if target == '/run/systemd/incoming':
            roots = {'/systemd/propagate/' + unit, '/run/systemd/propagate/' + unit}
            require(entry['root'] in roots and s['mode'] == stat.S_IFDIR | 0o600,
                    'run_incoming_not_private')
        else:
            require(target in ('/run/user', '/run/credentials')
                    and entry['root'] in ('/systemd/inaccessible/dir', '/run/systemd/inaccessible/dir')
                    and s['mode'] == stat.S_IFDIR, 'run_unexpected_submount')
    return value


def read_mountinfo(pid):
    # procfs reports size zero; do not use safe_read's regular-file size rule.
    with open(f'/proc/{pid}/mountinfo', 'rb') as stream:
        raw = stream.read(RUN_MOUNTINFO_BYTES + 1)
    require(len(raw) <= RUN_MOUNTINFO_BYTES, 'run_mountinfo_bound')
    return raw.decode('utf-8')


def observe_run_mount(pid, unit):
    require(type(pid) is int and pid > 1, 'run_mount_pid')
    host_namespace = os.readlink('/proc/self/ns/mnt')
    child_namespace = os.readlink(f'/proc/{pid}/ns/mnt')
    host = read_mountinfo('self'); child = read_mountinfo(pid)
    mounts = [e for e in run_mount_entries(child)
              if e['target'] == '/run' or e['target'].startswith('/run/')]
    require(len(mounts) <= 4, 'run_submount_scope')
    snapshots = {}
    for entry in mounts:
        target = entry['target']
        # Follow procfs's root magic link, not Path.resolve(), so lookup occurs
        # in this process's actual mount view. Do not follow a final symlink.
        s = os.stat(f'/proc/{pid}/root' + target, follow_symlinks=False)
        snapshots[target] = {'device': f'{os.major(s.st_dev)}:{os.minor(s.st_dev)}',
                            'inode': s.st_ino, 'uid': s.st_uid, 'gid': s.st_gid, 'mode': s.st_mode}
    require(os.readlink('/proc/self/ns/mnt') == host_namespace
            and os.readlink(f'/proc/{pid}/ns/mnt') == child_namespace, 'mount_namespace_changed')
    return validate_run_mount({'host_namespace': host_namespace, 'child_namespace': child_namespace,
            'host_mountinfo': host, 'child_mountinfo': child, 'mount_stats': snapshots}, unit)


def observe_service(unit, stage, frame, host_netns, *, capture_seconds=None):
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
    if stage == 'captureworker':
        require(type(capture_seconds) is int and 1 <= capture_seconds <= 14400
                and duration_microseconds(props.get('RuntimeMaxUSec', '')) == capture_seconds * 1000000,
                'capture_runtime_max_not_enforced')
    else:
        require(capture_seconds is None, 'no_generic_runtime_override')
        require(duration_microseconds(props.get('RuntimeMaxUSec', '')) == {**STAGES, **CAPTURE_STAGES}[stage] * 1000000, 'runtime_max_not_enforced')
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
    run_mount = observe_run_mount(pid, unit)
    return {'stage': stage, 'unit': unit, 'pid': pid, 'host_netns': host_netns, 'child_netns': child_netns,
            'uid': 65534, 'no_new_privs': True, 'capabilities': '0000000000000000',
            'ipv4_blocked': frame['ipv4_blocked'], 'ipv6_blocked': frame['ipv6_blocked'],
            **values, 'properties': props, 'run_mount': run_mount,
            **({'capture_runtime_seconds': capture_seconds} if stage == 'captureworker' else {})}


def duration_microseconds(value):
    """Parse systemd's exact integral duration display; no floats or infinity."""
    require(type(value) is str and bool(value), 'systemd_duration_shape')
    scales = {'h': 3600000000, 'min': 60000000, 's': 1000000, 'ms': 1000, 'us': 1}
    total = 0
    for token in value.split():
        m = re.fullmatch(r'([0-9]+)(h|min|s|ms|us)', token)
        require(m is not None, 'systemd_duration_shape')
        total += int(m[1]) * scales[m[2]]
    return total



def save(path, raw, mode=0o644):
    """Only below a fresh supervisor-owned workspace."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    C.write_new(path, raw, mode)


def private_directory(path, *, uid=0, gid=0, mode=0o700):
    path.mkdir(mode=0o700)
    observed = path.lstat()
    require(stat.S_ISDIR(observed.st_mode), 'private_directory_type')
    os.chmod(path, mode, follow_symlinks=False)
    os.chown(path, uid, gid, follow_symlinks=False)
    current = path.lstat()
    require((current.st_dev, current.st_ino) == (observed.st_dev, observed.st_ino)
            and stat.S_IMODE(current.st_mode) == mode and current.st_uid == uid
            and current.st_gid == gid, 'private_directory_identity_or_mode')
    return path


def platform_context():
    require(os.geteuid() == 0, 'root_supervisor_required')
    require(platform.python_implementation() == 'CPython' and platform.python_version() == '3.11.16', 'python_target')
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'machine_target')
    osr = platform.freedesktop_os_release()
    require(osr.get('ID') == 'ubuntu' and osr.get('VERSION_ID') == '24.04', 'os_target')
    require(Path('/proc/1/comm').read_text().strip() == 'systemd'
            and Path('/sys/fs/cgroup/cgroup.controllers').is_file(), 'systemd_cgroup_required')
    image = os.environ.get('ImageVersion', '')
    require(os.environ.get('ImageOS') == 'ubuntu24' and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', image), 'image_missing')
    return {'os': 'ubuntu-24.04', 'architecture': 'x86_64', 'python': platform.python_version(),
            'runner_image': image, 'kernel': platform.release(), 'libc': list(platform.libc_ver()),
            'bootstrap_python_sha256': sha(safe_read(Path(sys.executable).resolve(), 128*1024*1024)),
            'contract': 'q3_observed_ubuntu24_cpu_runtime_v0', 'historical_platform_equivalence': False}


class BoundedReader:
    """Per-frame and aggregate bounds; deadline cannot be extended by trickle IO."""
    def __init__(self, stream, total_limit=64*1024*1024, frame_limit=1024*1024):
        self.fd = stream.fileno(); self.buffer = b''; self.total = 0
        self.limit = total_limit; self.frame_limit = frame_limit; self.eof = False
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.fd, selectors.EVENT_READ)

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        require(remaining > 0 and bool(self.selector.select(remaining)), 'external_deadline_expired')
        raw = os.read(self.fd, 65536)
        if not raw:
            self.eof = True; return
        self.total += len(raw)
        require(self.total <= self.limit, 'protocol_total_bound')
        self.buffer += raw
        first = self.buffer.find(b'\n')
        require((first + 1 if first >= 0 else len(self.buffer)) <= self.frame_limit, 'protocol_frame_bound')

    def line(self, deadline):
        while b'\n' not in self.buffer:
            require(not self.eof, 'unexpected_protocol_eof')
            self.receive(deadline)
        raw, self.buffer = self.buffer.split(b'\n', 1)
        require(len(raw) + 1 <= self.frame_limit, 'protocol_frame_bound')
        return raw + b'\n'

    def finish(self, deadline):
        while not self.eof: self.receive(deadline)
        raw = self.buffer; self.buffer = b''
        return raw

    def close(self):
        self.selector.close()


class Service:
    """Construction is IO-free. The caller registers this object before start."""
    def __init__(self, prefix, stage, command, work, python, log, phase_deadline):
        self.unit = prefix + '-' + stage + '.service'; self.stage = stage
        self.command = command; self.work = work; self.python = python
        self.log_path = log; self.phase_deadline = phase_deadline
        self.log = None; self.process = None; self.reader = None
        self.observation = None; self.cleanup = None; self.launch_attempted = False
        self.runtime_deadline_ns = None; self.deadline = phase_deadline

    def start(self):
        require(not self.launch_attempted, 'service_already_started')
        now = time.monotonic_ns()
        seconds = (min(14400, (int(self.phase_deadline * 1e9) - now) // 1000000000)
                   if self.stage == 'captureworker' else STAGES[self.stage])
        require(seconds >= 1 and time.monotonic() + seconds <= self.phase_deadline + 1, 'phase_exhausted')
        self.runtime_deadline_ns = now + seconds*1000000000
        self.deadline = min(self.phase_deadline, self.runtime_deadline_ns/1e9 + 5)
        self.log = self.log_path.open('xb'); os.fchmod(self.log.fileno(), 0o600)
        args = service_command(self.unit, self.stage, self.command, self.work, self.python,
                               **({'capture_seconds': seconds} if self.stage == 'captureworker' else {}))
        self.launch_attempted = True  # An interrupted Popen still creates a cleanup obligation.
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.log, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'},
            start_new_session=True, bufsize=0)
        self.reader = BoundedReader(self.process.stdout)
        frame = strict_json(self.reader.line(min(self.deadline, time.monotonic()+20)))
        self.observation = observe_service(self.unit, self.stage, frame, os.readlink('/proc/self/ns/net'),
            **({'capture_seconds': seconds} if self.stage == 'captureworker' else {}))
        self.send(b'EXEC\n')
        return self

    def send(self, data):
        require(type(data) is bytes and 0 < len(data) <= 512, 'control_command_bound')
        require(self.process is not None and self.process.poll() is None, 'service_terminated')
        fd = self.process.stdin.fileno(); os.set_blocking(fd, False)
        start = time.monotonic_ns()
        try: count = os.write(fd, data)
        except BlockingIOError as exc: raise C.ContractError('control_pipe_blocked') from exc
        require(count == len(data), 'incomplete_control_write')
        return start

    def complete(self, *, empty_tail=True):
        tail = self.reader.finish(self.deadline)
        require(not empty_tail or tail == b'', 'extra_worker_output')
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'phase_exhausted')
        rc = self.process.wait(timeout=remaining)
        require(rc == 0, 'isolated_service_failed')
        return rc

    def close(self, deadline):
        if self.cleanup is not None: return self.cleanup
        def ctl(args, max_seconds=10):
            remaining = deadline-time.monotonic()
            require(remaining > 0, 'cleanup_deadline')
            return control(args, timeout=min(max_seconds, remaining), check=False)
        if self.launch_attempted:
            for args in (['/usr/bin/systemctl','kill','--kill-whom=all','--signal=KILL',self.unit],
                         ['/usr/bin/systemctl','stop',self.unit]):
                try: ctl(args)
                except Exception: pass  # Actual quiescence below, never this exit code, is authoritative.
        if self.process is not None:
            if self.process.poll() is None:
                try: os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            self.process.wait(timeout=max(0.01, min(5, deadline-time.monotonic())))
            for stream in (self.process.stdin,self.process.stdout):
                if stream: stream.close()
        if self.reader: self.reader.close()
        if self.log: self.log.close()
        if self.launch_attempted:
            q = ctl(['/usr/bin/systemctl','show',self.unit,'--no-pager',
                     '--property=LoadState,ActiveState,ControlGroup'])
            values = dict(x.split('=',1) for x in q.stdout.decode('utf-8').splitlines() if '=' in x)
            require(q.returncode in (0,1,4) and set(values)=={'LoadState','ActiveState','ControlGroup'}, 'cleanup_observation')
            require(values['LoadState'] in ('loaded','not-found') and values['ActiveState']=='inactive'
                    and values['ControlGroup'] in ('','/system.slice/'+self.unit), 'service_not_inactive')
            cg = Path('/sys/fs/cgroup/system.slice') / self.unit
            if cg.exists():
                require(all(not p.read_text().strip() for p in [cg/'cgroup.procs',*cg.rglob('cgroup.procs')]), 'cgroup_not_empty')
        else: values = None
        require(not self.launch_attempted or self.process is not None, 'client_launch_identity_unavailable')
        self.cleanup = {'unit':self.unit,'launch_attempted':self.launch_attempted,
                        'properties':values,'cgroup_empty_or_removed':True,
                        'client_reaped': self.process is None or self.process.poll() is not None}
        return self.cleanup


class Lifecycle:
    """Register before side effects. One shared final cleanup grace, not per unit."""
    def __init__(self):
        self.services=[]; self.timers={}; self.cleanup_deadline=None

    def start(self, *args):
        svc=Service(*args); self.services.append(svc)
        return svc.start()

    def arm(self,prefix,worker_unit):
        require(re.fullmatch(r'pulse-q3-[a-f0-9]{24}-call-[0-9]{3}',prefix), 'timer_identity')
        require(prefix not in self.timers, 'timer_reuse')
        self.timers[prefix]=None
        unit=prefix+'-watchdog'
        control(['/usr/bin/systemd-run','--quiet','--unit='+unit,'--on-active=65s',
                 '--timer-property=AccuracySec=1us','--timer-property=RandomizedDelaySec=0',
                 '/usr/bin/systemctl','kill','--kill-whom=all','--signal=KILL',worker_unit])
        control(['/usr/bin/systemctl','is-active','--quiet',unit+'.timer'])
        return unit+'.timer'

    def disarm(self,prefix,deadline):
        require(prefix in self.timers, 'unregistered_timer')
        if self.timers[prefix] is not None: return self.timers[prefix]
        names=[prefix+'-watchdog.timer',prefix+'-watchdog.service']
        remaining=deadline-time.monotonic();require(remaining>0,'cleanup_deadline')
        control(['/usr/bin/systemctl','stop',*names],timeout=min(15,remaining),check=False)
        rows=[]
        for name in names:
            remaining=deadline-time.monotonic();require(remaining>0,'cleanup_deadline')
            result=control(['/usr/bin/systemctl','show',name,'--no-pager','--property=LoadState,ActiveState'],
                           timeout=min(5,remaining),check=False)
            values=dict(x.split('=',1) for x in result.stdout.decode().splitlines() if '=' in x)
            require(result.returncode in (0,1,4) and set(values)=={'LoadState','ActiveState'}
                    and values['LoadState'] in ('loaded','not-found') and values['ActiveState']=='inactive', 'timer_not_inactive')
            rows.append({'unit':name,**values})
        self.timers[prefix]={'units':rows,'closed_ns':time.monotonic_ns()}
        return self.timers[prefix]

    def cleanup(self):
        if self.cleanup_deadline is None: self.cleanup_deadline=time.monotonic()+180
        errors=[]
        for prefix,value in self.timers.items():
            if value is None:
                try:self.disarm(prefix,self.cleanup_deadline)
                except BaseException:errors.append('timer_cleanup_unverified')
        for svc in reversed(self.services):
            try:svc.close(self.cleanup_deadline)
            except BaseException:errors.append('service_cleanup_unverified')
        return {'cleanup_complete':not errors,'errors':errors,
                'services':[s.cleanup for s in self.services],
                'timers':[{'prefix':k,'closure':v} for k,v in self.timers.items()]}


def phase(life,prefix,stage,command,work,python,logs,deadline,evidence):
    svc=life.start(prefix,stage,command,work,python,logs/(stage+'.log'),deadline)
    error=None
    try:svc.complete()
    except BaseException as exc:error=exc
    try:closed=svc.close(min(deadline,time.monotonic()+30))
    except BaseException as exc:
        if error is None:error=exc
        closed=None
    if svc.observation is not None:save(evidence/(stage+'-sandbox.json'),encode(svc.observation))
    if closed is not None:save(evidence/(stage+'-cleanup.json'),encode(closed))
    if error is not None:raise error
    return svc
