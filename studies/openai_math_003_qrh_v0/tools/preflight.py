#!/usr/bin/env python3
"""Read-only Linux/toolchain preflight. Never builds QRH or emits an ALLOW.

Python 3.10+ standard library only. Tool execution requires an expected SHA-256;
unverified or mismatched executables are hashed but are not executed. Write each
run to a NEW output directory. This is a host observation, not build evidence.
"""
import argparse
import ctypes
import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import time

REQUIRED = ('linux', 'unprivileged_uid', 'capabilities', 'procfs_app_path',
            'landlock_abi', 'af_unix_guard', 'lean', 'lake', 'landrun',
            'landrun_strict_execution', 'comparator', 'lean4export', 'no_runtime_interposition')

# Observed from the GitHub release asset whose complete archive SHA-256 is
# 47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4.
# Defaults apply only to this Linux x86_64 release; overrides remain explicit.
LINUX_X86_64_DEFAULT_PINS = {
    'lean': 'e8baaa71855a616dc351028f3ad2200051b0671f423a1696a100e809302d5550',
    'lake': '6f53827dab18010d6c690d14c8401cacabc1db958edb3552a877ed4cf1dd995d',
    'landrun': '6ada66a06669e8994e174a7271af2db636308e55a0d6ec896cc7d326b46727f6',
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def result_state(observations):
    by_id = {o['id']: o for o in observations}
    reasons = []
    for name in REQUIRED:
        item = by_id.get(name)
        if item is None:
            reasons.append('MISSING_OBSERVATION_' + name.upper())
        elif item.get('state') != 'PASS':
            reasons.append(item.get('reason_code') or ('UNVERIFIED_' + name.upper()))
    return ('BLOCK' if reasons else 'READY_FOR_CONTROLLED_RUN'), reasons


class Recorder:
    def __init__(self, output, timeout_seconds=12):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output / 'raw').mkdir()
        self.raw_refs = []
        self.timeout_seconds = timeout_seconds

    def raw(self, name, data):
        path = self.output / 'raw' / name
        path.write_bytes(data)
        ref = {'path': str(path.relative_to(self.output)), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        self.raw_refs.append(ref)
        return ref

    def command(self, name, argv, timeout=None, cwd=None):
        timeout = self.timeout_seconds if timeout is None else timeout
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        before = time.monotonic()
        # Do not inherit dynamic-library interposition or Lean search-path overrides.
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'TZ') if k in os.environ}
        try:
            run = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=timeout, close_fds=True)
            out, err, code, state = run.stdout, run.stderr, run.returncode, 'COMPLETED'
        except subprocess.TimeoutExpired as exc:
            out, err, code, state = exc.stdout or b'', exc.stderr or b'', None, 'TIMEOUT'
        except (OSError, ValueError) as exc:
            out, err, code, state = b'', repr(exc).encode(), None, 'EXECUTION_ERROR'
        record = {'argv': argv, 'cwd': str(cwd) if cwd else None, 'started_utc': started,
                  'duration_s': time.monotonic() - before, 'exit_code': code, 'state': state,
                  'stdout_ref': self.raw(name + '.stdout', out),
                  'stderr_ref': self.raw(name + '.stderr', err)}
        self.raw(name + '.command.json', (json.dumps(record, indent=2) + '\n').encode())
        return record, out.decode(errors='replace'), err.decode(errors='replace')


def probe_tool(name, path, expected_sha256, recorder, version_pattern=None):
    detail = {'requested_path': path, 'expected_sha256': expected_sha256, 'execution': 'NOT_RUN'}
    item = {'id': name, 'state': 'UNAVAILABLE', 'reason_code': 'TOOL_UNAVAILABLE_' + name.upper(), 'details': detail}
    if not path or not Path(path).is_file():
        return item
    resolved = Path(path).resolve()
    detail.update({'resolved_path': str(resolved), 'sha256': sha256(resolved),
                   'bytes': resolved.stat().st_size, 'mode': oct(resolved.stat().st_mode & 0o777)})
    if not expected_sha256:
        item.update(state='NOT_VERIFIED', reason_code='TOOL_DIGEST_UNPINNED_' + name.upper())
        return item
    if detail['sha256'] != expected_sha256:
        item.update(state='FAIL', reason_code='TOOL_DIGEST_MISMATCH_' + name.upper())
        return item
    if not os.access(resolved, os.X_OK):
        item.update(state='FAIL', reason_code='TOOL_NOT_EXECUTABLE_' + name.upper())
        return item
    if version_pattern is not None:
        record, out, err = recorder.command(name + '_version', [str(resolved), '--version'])
        detail.update(execution=record, version_stdout=out, version_stderr=err)
        if record['exit_code'] != 0 or not re.search(version_pattern, out + err):
            item.update(state='FAIL', reason_code='TOOL_VERSION_FAILED_' + name.upper())
            return item
    item.update(state='PASS', reason_code=None)
    return item


def collect(args, recorder):
    observations = []
    def add(name, state, details, reason=None):
        observations.append({'id': name, 'state': state, 'reason_code': reason, 'details': details})
    linux = platform.system() == 'Linux'
    add('linux', 'PASS' if linux else 'FAIL', {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()}, 'UNSUPPORTED_PLATFORM' if not linux else None)
    uid = os.geteuid() if hasattr(os, 'geteuid') else None
    add('unprivileged_uid', 'PASS' if uid is not None and uid != 0 else 'FAIL', {'euid': uid, 'uid': os.getuid() if hasattr(os, 'getuid') else None}, 'PRIVILEGED_OR_UNKNOWN_UID' if uid in (None, 0) else None)
    status = {}
    try:
        raw = Path('/proc/self/status').read_bytes()
        recorder.raw('proc_self_status', raw)
        status = dict(line.split(':', 1) for line in raw.decode().splitlines() if ':' in line)
        status = {k: v.strip() for k, v in status.items()}
    except OSError as exc:
        status = {'error': str(exc)}
    caps = {k: status.get(k) for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb', 'NoNewPrivs', 'Seccomp', 'Seccomp_filters')}
    cap_ok = caps.get('CapEff') == '0000000000000000' and caps.get('CapPrm') == '0000000000000000'
    add('capabilities', 'PASS' if cap_ok else 'FAIL', caps, None if cap_ok else 'CAPABILITIES_NOT_UNPRIVILEGED')
    paths = {}
    for path in ('/proc/self/exe', '/proc/' + str(os.getpid()) + '/exe'):
        try:
            paths[path] = {'target': os.readlink(path)}
        except OSError as exc:
            paths[path] = {'errno': exc.errno, 'error': str(exc)}
    path_ok = len({v.get('target') for v in paths.values()}) == 1 and all('target' in v for v in paths.values())
    add('procfs_app_path', 'PASS' if path_ok else 'FAIL', {'getpid': os.getpid(), 'lookups': paths}, None if path_ok else 'PROCFS_PID_NAMESPACE_MISMATCH')
    # Linux generic syscall numbering is 444 on the two supported release architectures.
    landlock = {'syscall_number': 444, 'flags': 'LANDLOCK_CREATE_RULESET_VERSION', 'abi': None}
    if linux and platform.machine() in ('x86_64', 'aarch64'):
        libc = ctypes.CDLL(None, use_errno=True)
        ctypes.set_errno(0)
        value = libc.syscall(444, 0, 0, 1)
        number = ctypes.get_errno()
        landlock.update(abi=value if value >= 0 else None, result=value, errno=number, error=errno.errorcode.get(number))
    abi_ok = isinstance(landlock['abi'], int) and landlock['abi'] > 0
    add('landlock_abi', 'PASS' if abi_ok else 'FAIL', landlock, None if abi_ok else 'LANDLOCK_UNAVAILABLE')
    unix = {}
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.close()
        unix['creation'] = 'ALLOWED'
    except OSError as exc:
        unix.update(creation='DENIED', errno=exc.errno, error=str(exc))
    guarded = unix.get('errno') in (errno.EPERM, errno.EACCES, errno.EAFNOSUPPORT)
    add('af_unix_guard', 'PASS' if guarded else 'FAIL', unix, None if guarded else 'AF_UNIX_GUARD_UNVERIFIED')
    interposition = {k: os.environ[k] for k in ('LD_PRELOAD', 'LD_AUDIT') if os.environ.get(k)}
    add('no_runtime_interposition', 'FAIL' if interposition else 'PASS', {'present_variable_names': sorted(interposition)}, 'UNREVIEWED_RUNTIME_INTERPOSITION' if interposition else None)
    for name, pattern in [('lean', r'\b4\.34\.1\b'), ('lake', r'Lean version 4\.34\.1\b'), ('landrun', r'landrun version'), ('comparator', None), ('lean4export', None)]:
        observations.append(probe_tool(name, getattr(args, name), getattr(args, name + '_sha256'), recorder, pattern))
    landrun_item = next(o for o in observations if o['id'] == 'landrun')
    if landrun_item['state'] == 'PASS':
        true = shutil.which('true')
        if true:
            # No --best-effort, --unrestricted-*, or fake-landrun is permitted.
            argv = [landrun_item['details']['resolved_path']]
            for path in ('/usr', '/bin', '/lib', '/lib64'):
                if Path(path).exists():
                    argv.extend(['--rox', path])
            if Path('/etc/ld.so.cache').exists():
                argv.extend(['--ro', '/etc/ld.so.cache'])
            argv.extend(['--', true])
            record, out, err = recorder.command('landrun_strict_true', argv)
            ok = record['exit_code'] == 0
            add('landrun_strict_execution', 'PASS' if ok else 'FAIL', {'record': record, 'stdout': out, 'stderr': err}, None if ok else 'LANDRUN_STRICT_EXECUTION_FAILED')
        else:
            add('landrun_strict_execution', 'UNAVAILABLE', {}, 'TRUE_BINARY_UNAVAILABLE')
    else:
        add('landrun_strict_execution', 'NOT_VERIFIED', {'execution': 'NOT_RUN'}, 'LANDRUN_BINARY_NOT_VERIFIED')
    resources = {'cpu_count': os.cpu_count(), 'cpu_affinity_count': len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
                 'disk': dict(zip(('total_bytes', 'used_bytes', 'free_bytes'), shutil.disk_usage(recorder.output)))}
    for path in ('/proc/meminfo', '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory.swap.max', '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/pids.max'):
        try:
            raw = Path(path).read_bytes()
            resources[path] = raw.decode().strip()
            recorder.raw(path.lstrip('/').replace('/', '__'), raw)
        except OSError as exc:
            resources[path] = {'error': str(exc)}
    add('resources', 'OBSERVED', resources)
    add('comparator_exporter_compatibility', 'NOT_VERIFIED', {'reason': 'Binary hashes/presence do not prove compatible comparison/export. A separately bound fixture and target audit are required.'})
    return observations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New result directory; an existing directory is refused.')
    parser.add_argument('--toolchain-root', help='Lean 4.34.1 installation directory; supplies bin/lean and bin/lake.')
    parser.add_argument('--timeout-seconds', type=float, default=12, help='Per-command timeout, default 12 seconds.')
    for name in ('lean', 'lake', 'landrun', 'comparator', 'lean4export'):
        parser.add_argument('--' + name)
        parser.add_argument('--' + name + '-sha256', dest=name + '_sha256')
    args = parser.parse_args(argv)
    if args.timeout_seconds <= 0:
        parser.error('--timeout-seconds must be positive')
    if args.toolchain_root:
        for name in ('lean', 'lake'):
            if not getattr(args, name):
                setattr(args, name, str(Path(args.toolchain_root) / 'bin' / name))
    if platform.system() == 'Linux' and platform.machine() == 'x86_64':
        for name, digest in LINUX_X86_64_DEFAULT_PINS.items():
            if getattr(args, name) and not getattr(args, name + '_sha256'):
                setattr(args, name + '_sha256', digest)
    recorder = Recorder(args.output, timeout_seconds=args.timeout_seconds)
    try:
        observations = collect(args, recorder)
        state, reasons = result_state(observations)
    except Exception as exc:
        recorder.raw('unhandled_error.txt', repr(exc).encode())
        observations, state, reasons = [], 'BLOCK', ['PREFLIGHT_INTERNAL_ERROR']
    result = {'schema_version': 'qrh003_preflight_v1', 'record_role': 'HOST_PREFLIGHT_OBSERVATION',
              'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'overall_state': state, 'reason_codes': reasons, 'authority_effect': 'NONE',
              'observations': observations, 'details': {'required_observations': list(REQUIRED),
              'profile': 'unprivileged_linux_landlock_no_af_unix_no_interposition_lean4341',
              'qrh_build': 'NOT_RUN', 'comparator_target_audit': 'NOT_RUN',
              'resource_adequacy': 'NOT_ASSESSED', 'script_sha256': sha256(__file__)},
              'raw_refs': recorder.raw_refs}
    (recorder.output / 'preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'overall_state': state, 'reason_codes': reasons, 'result': str(recorder.output / 'preflight.json')}))
    return 2 if state == 'BLOCK' else 0


if __name__ == '__main__':
    raise SystemExit(main())
