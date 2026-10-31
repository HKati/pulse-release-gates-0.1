#!/usr/bin/env python3
"""External Docker boundary for the five fixed W1 candidates.

No pull/build/install. Local Unix daemon only. Command construction is pure;
Docker invocation occurs only through the separately authorized controller.
The daemon, kernel, image and reviewed instrumentation are explicit trust roots.
"""
from __future__ import annotations
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time

POLICY = {
    'id': 'pd_sm_02_w1_docker_linux_v0', 'network': 'none', 'readonly_rootfs': True,
    'user': '65532:65532', 'cap_drop': ['ALL'], 'no_new_privileges': True,
    'pids_limit': 16, 'memory_bytes': 134217728, 'memory_swap_bytes': 134217728,
    'nano_cpus': 500000000, 'ipc': 'none', 'cgroupns': 'private',
    'scratch_tmpfs': 'rw,nosuid,nodev,noexec,size=1048576,mode=0700,uid=65532,gid=65532',
    'case_wall_seconds': 40, 'observer_wall_seconds': 12, 'stdout_bytes': 524288,
    'stderr_bytes': 65536, 'nofile': 64, 'file_size_bytes': 65536,
    'probe_children_max': 20, 'runtime': 'CPython-3.13.5-Linux-x86_64',
    'docker_endpoint': 'unix:///var/run/docker.sock', 'restart': 'no',
}

class BoundaryError(ValueError):
    pass

def need(ok, code):
    if not ok: raise BoundaryError(code)

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def policy_digest():
    return hashlib.sha256(canonical(POLICY)).hexdigest()

def image_id(value):
    need(type(value) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', value), 'image_id_required')
    return value

def create_args(image, stage: Path, cidfile: Path, request_sha: str, case_id: str):
    image_id(image)
    need(re.fullmatch('[0-9a-f]{64}', request_sha) is not None, 'request_sha')
    need(case_id in ('P00', 'N01', 'N07', 'N08', 'N02', 'probe-time', 'probe-output'), 'case_id')
    need(stage.is_absolute() and not any(c in str(stage) for c in ',\n\r\x00'), 'mount_path')
    return ['container', 'create', '--pull=never', '--cidfile', str(cidfile),
            '--label', 'pulse.w1.request=' + request_sha, '--label', 'pulse.w1.case=' + case_id,
            '--network=none', '--read-only', '--user=65532:65532', '--cap-drop=ALL',
            '--security-opt=no-new-privileges=true', '--pids-limit=16', '--memory=134217728',
            '--memory-swap=134217728', '--cpus=0.5', '--ipc=none', '--cgroupns=private',
            '--ulimit=nofile=64:64', '--ulimit=fsize=65536:65536', '--ulimit=core=0:0',
            '--tmpfs', '/scratch:' + POLICY['scratch_tmpfs'],
            '--mount', 'type=bind,src=' + str(stage) + ',dst=/inputs,readonly',
            '--workdir=/scratch', '--restart=no', '--no-healthcheck', '--log-driver=none',
            '--entrypoint=/usr/bin/env', '--interactive', image,
            '-i', 'LANG=C.UTF-8', 'PATH=/usr/local/bin:/usr/bin:/bin',
            '/usr/local/bin/python3', '-I', '-S', '-B', '/inputs/runtime.py',
            '--request-sha256', request_sha, '--case-id', case_id]

def check_image(info, expected):
    need(type(info) is list and len(info) == 1, 'image_inventory')
    x = info[0]
    need(x.get('Id') == image_id(expected) and x.get('Os') == 'linux' and x.get('Architecture') == 'amd64', 'image_identity_platform')
    need(not x.get('Config', {}).get('Volumes'), 'image_declares_extra_volumes')
    return x

def check_inspect(info, image, stage: Path, request_sha, case_id, cid, *, running=False):
    need(type(info) is list and len(info) == 1, 'container_inventory')
    x = info[0]; h = x.get('HostConfig', {}); c = x.get('Config', {})
    need(x.get('Id') == cid and x.get('Image') == image_id(image), 'container_image_identity')
    need(c.get('Labels', {}).get('pulse.w1.request') == request_sha and
         c.get('Labels', {}).get('pulse.w1.case') == case_id, 'container_subject')
    for key, value in {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
                       'PidsLimit': 16, 'Memory': 134217728, 'MemorySwap': 134217728,
                       'NanoCpus': 500000000, 'IpcMode': 'none', 'CgroupnsMode': 'private'}.items():
        need(type(h.get(key)) is type(value) and h[key] == value, 'container_' + key)
    need(h.get('CapDrop') == ['ALL'] and not h.get('CapAdd') and not h.get('Devices') and
         not h.get('DeviceRequests') and not h.get('VolumesFrom') and not h.get('PortBindings') and
         not h.get('Binds') and not h.get('PidMode') and not h.get('UTSMode') and
         not h.get('GroupAdd') and not h.get('ExtraHosts'), 'extra_privilege_or_mount')
    need(h.get('RestartPolicy', {}).get('Name') == 'no' and
         h.get('LogConfig', {}).get('Type') == 'none', 'restart_or_log_driver')
    opts = h.get('SecurityOpt')
    need(opts in (['no-new-privileges'], ['no-new-privileges=true']), 'security_options')
    need(h.get('Tmpfs') == {'/scratch': POLICY['scratch_tmpfs']}, 'tmpfs_policy')
    need(all(type(v.get('Soft')) is int and type(v.get('Hard')) is int for v in h.get('Ulimits', [])), 'ulimit_types')
    limits = {v['Name']: (v['Soft'], v['Hard']) for v in h.get('Ulimits', [])}
    need(len(limits)==len(h.get('Ulimits',[])), 'duplicate_ulimit')
    need(limits == {'nofile': (64,64), 'fsize': (65536,65536), 'core': (0,0)}, 'ulimit_policy')
    mounts = x.get('Mounts', [])
    # Docker may include a tmpfs Mount record, but never an additional bind/volume.
    binds = [m for m in mounts if m.get('Type') != 'tmpfs']
    need(len(binds) == 1, 'mount_inventory')
    m = binds[0]
    need(m.get('Type') == 'bind' and m.get('Source') == str(stage) and
         m.get('Destination') == '/inputs' and m.get('RW') is False and
         m.get('Propagation') in ('rprivate', ''), 'input_mount_policy')
    need(all(m.get('Destination') == '/scratch' for m in mounts if m.get('Type') == 'tmpfs'), 'extra_tmpfs')
    need(c.get('User') == '65532:65532' and c.get('WorkingDir') == '/scratch' and
         c.get('OpenStdin') is True and c.get('Tty') is False and
         c.get('Entrypoint') == ['/usr/bin/env'], 'container_entrypoint')
    expected_cmd = create_args(image, stage, Path('/unused'), request_sha, case_id)
    need(c.get('Cmd') == expected_cmd[expected_cmd.index(image)+1:], 'container_command')
    need(c.get('Healthcheck', {}).get('Test') == ['NONE'], 'healthcheck_not_disabled')
    state = x.get('State', {})
    if running:
        need(state.get('Running') is True and state.get('Status') == 'running', 'container_not_running')
    else:
        need(state.get('Status') == 'created' and state.get('Running') is False, 'container_already_started')
    need(type(x.get('RestartCount')) is int and x['RestartCount'] == 0, 'container_restarted')
    return x

def validate_probe(p, request_sha, case_id):
    need(type(p) is dict and p.get('frame') == 'ready' and p.get('request_sha256') == request_sha
         and p.get('case_id') == case_id, 'probe_subject')
    need(type(p.get('kernel_release')) is str and 0 < len(p['kernel_release']) <= 128, 'kernel_identity')
    need(p.get('runtime') == {'implementation':'CPython','version':'3.13.5','system':'Linux','machine':'x86_64'}, 'runtime_profile')
    need(type(p.get('python_sha256')) is str and re.fullmatch('[0-9a-f]{64}', p['python_sha256']), 'python_identity')
    s = p.get('status_fields', {})
    need(s.get('NoNewPrivs') == '1' and s.get('Seccomp') == '2' and int(s.get('CapEff', '-1'), 16) == 0, 'kernel_controls')
    need(p.get('uid') == 65532 and type(p['uid']) is int and p.get('gid') == 65532, 'runtime_uid')
    need(p.get('interfaces') == ['lo'] and p.get('network_errno') in (errno.ENETUNREACH, errno.EHOSTUNREACH), 'network_not_denied')
    need(p.get('inherited_fds') == [0,1,2], 'unexpected_descriptors')
    need(p.get('cgroup') == {'pids.max':'16','memory.max':'134217728','memory.swap.max':'0','cpu.max':'50000 100000'}, 'cgroup_controls')
    need(p.get('scratch_roundtrip_hex') == b'W1_CONTROL'.hex(), 'scratch_control')
    failures = p.get('denied_writes', {})
    need(set(failures) == {'/inputs/deny_probe', '/tmp/deny_probe', '/deny_probe', '/dev/deny_probe'} and
         all(type(v) is int and v in (errno.EACCES, errno.EROFS, errno.EPERM) for v in failures.values()), 'write_boundary_controls')
    need(type(p.get('fork_errno')) is int and p['fork_errno'] == errno.EAGAIN and
         type(p.get('fork_children')) is int and 1 <= p['fork_children'] <= 16 and
         type(p.get('fork_reaped')) is int and p['fork_reaped'] == p['fork_children'], 'process_limit_probe')
    need(p.get('fsize_errno') == errno.EFBIG and p.get('probe_cleanup') is True, 'file_limit_probe')
    return p

def project_info(x):
    # Never preserve daemon proxy URLs, registry configuration or host environment.
    return {k:x.get(k) for k in ('ID','ServerVersion','OSType','Architecture','KernelVersion',
                                 'CgroupVersion','CgroupDriver','SecurityOptions')}

def project_image(xs):
    return [{k:x.get(k) for k in ('Id','Os','Architecture')} |
            {'Config':{'Volumes':x.get('Config',{}).get('Volumes')}} for x in xs]

def project_inspect(xs):
    result=[]
    for x in xs:
        h=x.get('HostConfig',{});c=x.get('Config',{});state=x.get('State',{})
        keys=('NetworkMode','ReadonlyRootfs','Privileged','PidsLimit','Memory','MemorySwap','NanoCpus',
              'IpcMode','CgroupnsMode','CapDrop','CapAdd','Devices','DeviceRequests','VolumesFrom','PortBindings',
              'Binds','PidMode','UTSMode','GroupAdd','ExtraHosts','RestartPolicy','LogConfig','SecurityOpt','Tmpfs','Ulimits')
        result.append({'Id':x.get('Id'),'Image':x.get('Image'),'RestartCount':x.get('RestartCount'),
            'Mounts':x.get('Mounts',[]),'HostConfig':{k:h.get(k) for k in keys},
            'Config':{k:c.get(k) for k in ('User','WorkingDir','OpenStdin','Tty','Entrypoint','Cmd','Healthcheck')} |
                     {'Labels':{k:c.get('Labels',{}).get(k) for k in ('pulse.w1.request','pulse.w1.case')}},
            'State':{k:state.get(k) for k in ('Running','Status','ExitCode','OOMKilled')}})
    return result

class Docker:
    """Bounded local CLI transport. Never invokes a shell or accepts remote endpoints."""
    def __init__(self, config_dir: Path, log_dir: Path):
        exe = shutil.which('docker')
        need(exe is not None, 'docker_unavailable')
        self.exe = str(Path(exe).resolve()); self.config = config_dir; self.logs = log_dir
        self.counter = 0
        config_dir.mkdir(mode=0o700, exist_ok=False)
        log_dir.mkdir(mode=0o700, exist_ok=False)
        self.prefix = [self.exe, '--host', POLICY['docker_endpoint'], '--config', str(config_dir)]
        self.env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG':'C.UTF-8', 'HOME':str(config_dir)}

    def command(self, args, *, timeout=15, code_ok=(0,), projection=None):
        self.counter += 1; stem = self.logs / f'{self.counter:03d}'
        (stem.with_suffix('.command.json')).write_bytes(canonical(self.prefix + args))
        result = bounded_process(self.prefix + args, self.env, timeout=timeout)
        if projection is not None and result['termination']=='exited' and result['returncode']==0:
            result['stdout']=canonical(projection(json.loads(result['stdout'])))
            result['metadata_projection']=True
        stem.with_suffix('.stdout').write_bytes(result['stdout'])
        stem.with_suffix('.stderr').write_bytes(result['stderr'])
        stem.with_suffix('.result.json').write_bytes(canonical({k:v for k,v in result.items() if k not in ('stdout','stderr')}))
        need(result['termination'] == 'exited' and result['returncode'] in code_ok, 'docker_command_failed:' + args[0])
        return result['stdout']

    def inspect(self, cid):
        return json.loads(self.command(['container', 'inspect', cid],projection=project_inspect))

    def capture(self, cid, request_sha, case_id, ready_callback, stdout_path, stderr_path):
        # A ready_callback validates both independent outer inspection and inner probes.
        probe = ('PROBE:' + request_sha + ':' + case_id + '\n').encode()
        def on_line(raw):
            try:
                def pairs(items):
                    out={}
                    for k,v in items:
                        need(k not in out, 'duplicate_runtime_json_key');out[k]=v
                    return out
                f = json.loads(raw, object_pairs_hook=pairs,
                    parse_constant=lambda _: (_ for _ in ()).throw(BoundaryError('nonfinite_runtime_json')))
            except (ValueError, UnicodeError): raise BoundaryError('invalid_runtime_json')
            if type(f) is dict and f.get('frame') == 'ready':
                ready_callback(f)
                return ('RUN:' + request_sha + ':' + case_id + '\n').encode()
            return None
        return bounded_process(self.prefix + ['container', 'start', '--attach', '--interactive', cid],
                               self.env, timeout=POLICY['case_wall_seconds'], initial=probe,
                               on_line=on_line, stdout_path=stdout_path, stderr_path=stderr_path,
                               after_ready_timeout=0.5 if case_id == 'probe-time' else None,
                               stdout_limit=65536 if case_id == 'probe-output' else POLICY['stdout_bytes'])


def bounded_process(argv, env, *, timeout, initial=b'', on_line=None,
                    stdout_path=None, stderr_path=None, stdout_limit=524288, stderr_limit=65536,
                    after_ready_timeout=None):
    """Drain both pipes with byte/time bounds; retain partial bytes on every failure.

    Killing the CLI does not kill a container. The caller MUST remove the exact
    created container in a finally block and verify absence before continuing.
    """
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env, close_fds=True, start_new_session=True)
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}; pending = bytearray()
    reason = 'exited'; detail = None; sent = False
    sel = selectors.DefaultSelector()
    sinks = {}
    try:
        for name, path in (('stdout',stdout_path), ('stderr',stderr_path)):
            if path is not None: sinks[name] = open(path, 'xb', buffering=0)
        for name, fd in (('stdout',p.stdout), ('stderr',p.stderr)):
            os.set_blocking(fd.fileno(), False); sel.register(fd, selectors.EVENT_READ, name)
        if initial:
            p.stdin.write(initial); p.stdin.flush()
        deadline = time.monotonic() + timeout
        while sel.get_map():
            if time.monotonic() >= deadline: reason = 'timeout'; break
            for key, _ in sel.select(min(0.1, max(0, deadline-time.monotonic()))):
                part = os.read(key.fileobj.fileno(), 8192)
                name = key.data
                if not part: sel.unregister(key.fileobj); continue
                limit = stdout_limit if name == 'stdout' else stderr_limit
                remaining = limit - len(buffers[name])
                kept = part[:max(0,remaining)]
                buffers[name].extend(kept)
                if name in sinks: sinks[name].write(kept)
                if len(part) > remaining: reason = 'output_limit'; break
                if name == 'stdout' and on_line:
                    pending.extend(part)
                    if len(pending) > 65536 and b'\n' not in pending: raise BoundaryError('frame_limit')
                    while b'\n' in pending:
                        line, _, rest = pending.partition(b'\n'); pending[:] = rest
                        need(len(line) <= 65536, 'frame_limit')
                        reply = on_line(bytes(line))
                        if reply is not None:
                            need(not sent, 'duplicate_ready'); sent = True
                            p.stdin.write(reply); p.stdin.flush(); p.stdin.close()
                            if after_ready_timeout is not None:
                                deadline = time.monotonic() + after_ready_timeout
            if reason != 'exited': break
        if reason == 'exited':
            p.wait(timeout=max(0.1, deadline-time.monotonic()))
    except BaseException as exc:
        reason = 'transport_or_admission_error'; detail = type(exc).__name__ + ':' + str(exc)
    finally:
        if p.poll() is None:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait(timeout=5)
        for f in sinks.values(): f.close()
        sel.close()
        for f in (p.stdin,p.stdout,p.stderr):
            if f and not f.closed:
                try: f.close()
                except BrokenPipeError: pass
    return {'returncode':p.returncode,'termination':reason,'detail':detail,
            'execution_token_sent':sent, 'stdout':bytes(buffers['stdout']), 'stderr':bytes(buffers['stderr'])}
