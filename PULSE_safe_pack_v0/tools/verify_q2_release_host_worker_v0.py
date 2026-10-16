#!/usr/bin/env python3
"""Owner-dispatched fixed capsule worker supervision; no release authority.

Only a separately consented workflow_dispatch may reach authenticated acquisition
or launch. The original capsule and worker are never modified. PR/push tests use
explicit synthetic doubles; direct unauthenticated execution rejects before IO.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
import io as byte_io

C = P = K = U = A = native = io = T = ObservedService = None
TOKEN = 'PULSE_Q2_WORKER_TOKEN'
SOURCE = 'PULSE_Q2_WORKER_SOURCE'
REQUEST = 'PULSE_Q2_WORKER_REQUEST'
DIGEST = 'PULSE_Q2_WORKER_REQUEST_SHA256'
NAME = 'Q2 native release-host worker verification v0'
ACTIVE_SERVICES = []
ACTIVE_TIMERS = {}
observed_native = None

def bootstrap_sources(repo, env):
    """Stdlib-only guard before importing any repository helper.

    The pinned checkout/entry-point and Git object database are trusted inputs.
    Dirty helpers are never imported. Execution uses copies of the exact held
    buffers, so a pathname change between verification and import is harmless.
    """
    revision = env.get("GITHUB_SHA", "")
    workflow = ".github/workflows/q2_release_host_worker_verification_v0.yml"
    expected = {"GITHUB_REPOSITORY": "HKati/pulse-release-gates-0.1", "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW_SHA": revision, "GITHUB_WORKFLOW": NAME,
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_ACTOR_ID": "128643840", "GITHUB_JOB": "verify_host", SOURCE: revision,
        "GITHUB_WORKSPACE": str(repo), "GITHUB_WORKFLOW_REF": "HKati/pulse-release-gates-0.1/" + workflow + "@refs/heads/main"}
    if (os.geteuid() != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision) or
            any(env.get(k) != v for k, v in expected.items())):
        raise ValueError("q2_context_rejected")
    clean = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
             "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    def git(args):
        p = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c", "credential.helper=",
            "-c", "core.hooksPath=/dev/null", "-c", "safe.directory=" + str(repo), *args],
            cwd=repo, env=clean, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=15, check=False)
        if p.returncode != 0 or len(p.stdout) > 65536: raise ValueError("q2_source_mismatch")
        return p.stdout
    if git(["rev-parse", "--verify", "HEAD^{commit}"]) != revision.encode() + b"\n":
        raise ValueError("q2_source_mismatch")
    def read(name):
        path = repo / name
        if any(p.is_symlink() for p in (path, *path.parents)): raise ValueError("q2_source_mismatch")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 * 1024**2:
                raise ValueError("q2_source_mismatch")
            raw = bytearray()
            while len(raw) <= 2 * 1024**2:
                chunk = os.read(fd, 65536)
                if not chunk: break
                raw.extend(chunk)
            after = os.fstat(fd)
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(raw) != before.st_size or stamp(before) != stamp(after): raise ValueError("q2_source_mismatch")
            return bytes(raw), "100755" if before.st_mode & 0o111 else "100644"
        finally: os.close(fd)
    def checked(names):
        entries = {}
        for row in git(["ls-tree", "-rz", "--full-tree", revision, "--", *names]).split(b"\0"):
            if row:
                metadata, name = row.split(b"\t"); entries[name.decode("ascii")] = metadata.decode("ascii").split()
        if set(entries) != set(names): raise ValueError("q2_source_mismatch")
        held = {}
        for name in names:
            raw, mode = read(name)
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if entries[name] != [mode, "blob", blob]: raise ValueError("q2_source_mismatch")
            held[name] = raw
        return held
    profile = "PULSE_safe_pack_v0/profiles/q2_release_host_worker_verification_v0.json"
    first = checked([profile, "PULSE_safe_pack_v0/tools/verify_q2_release_host_worker_v0.py"])
    def pairs(items):
        if len({k for k, _ in items}) != len(items): raise ValueError("q2_source_mismatch")
        return dict(items)
    p = json.loads(first[profile].decode("utf-8", "strict"), object_pairs_hook=pairs)
    names = p["source_paths"]
    if (not isinstance(names, list) or not 20 <= len(names) <= 60 or len(set(names)) != len(names) or
            any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", n)
                or ".." in Path(n).parts for n in names)):
        raise ValueError("q2_source_mismatch")
    held = checked(names)
    snapshot = Path(tempfile.mkdtemp(prefix="pulse-q2-worker-bootstrap-", dir="/var/lib"))
    try:
        for name, raw in held.items():
            path = snapshot / name; path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        return snapshot
    except BaseException:
        shutil.rmtree(snapshot)
        raise


def initialize_modules(source):
    global C, P, K, U, A, native, io, T, ObservedService, observed_native
    sys.path.insert(0, str(source / 'PULSE_safe_pack_v0/tools'))
    C = importlib.import_module('q2_release_host_worker_contract_v0')
    P = importlib.import_module('check_q2_release_host_worker_protocol_v0')
    K = importlib.import_module('check_q2_release_host_worker_v0')
    U = importlib.import_module('verify_q2_release_host_tokenizer_v0')
    U.initialize_modules(source)
    native, io, T = U.native, U.io, U.independent
    A = importlib.import_module('acquire_q2_reference_inputs_v0')

    class NativeObservation:
        def __getattr__(self, name): return getattr(native, name)
        def close_capture_service(self, service):
            service.cleanup_verified = False
            result = native.close_capture_service(service)
            service.cleanup_verified = True
            return result
        def watchdog(self, prefix, unit):
            ACTIVE_TIMERS[prefix] = False
            return native.watchdog(prefix, unit)
        def disarm_capture_watchdog(self, prefix):
            result = native.disarm_capture_watchdog(prefix)
            ACTIVE_TIMERS[prefix] = True
            return result
    observed_native = NativeObservation()

    class ReceiptReader:
        """Record raw BIND acknowledgement arrival, not reconstructed text."""
        def __init__(self, wrapped, owner): self.wrapped, self.owner = wrapped, owner
        def __getattr__(self, name): return getattr(self.wrapped, name)
        def line(self, deadline):
            raw = self.wrapped.line(deadline)
            at = time.monotonic_ns()
            if self.owner.awaiting_bound:
                self.owner.bound_raw = raw; self.owner.bound_received_ns = at
                self.owner.awaiting_bound = False
            return raw

    class BoundService(native.Service):
        def __init__(self, *args):
            self.cleanup_verified = False
            ACTIVE_SERVICES.append(self)
            self.commands = []; self.awaiting_bound = False; self.bound_raw = None
            self.bound_received_ns = None; self.eof_ns = self.exit_ns = self.reaped_ns = None
            super().__init__(*args)
            self.reader = ReceiptReader(self.reader, self)
        def send(self, raw):
            if raw == b'EXEC\n':
                C.require(hasattr(self, 'observation'), 'pre_exec_observation_missing')
                self.isolation_observed_ns = time.monotonic_ns()
            stamp = super().send(raw)
            self.commands.append({'command': raw.decode('ascii'), 'written_ns': stamp})
            if raw == b'EXEC\n': self.exec_ns = stamp
            if raw.startswith(b'BIND '): self.awaiting_bound = True
            return stamp
        def complete(self, *, empty_tail=False, deadline=None):
            deadline = min(self.deadline, self.runtime_deadline_ns / 1e9, deadline or self.deadline)
            tail = self.reader.finish(deadline)
            self.eof_ns = time.monotonic_ns()
            C.require(self.reader.eof is True and (not empty_tail or tail == b''), 'stdout_terminal')
            remaining = deadline - time.monotonic(); C.require(remaining > 0, 'terminal_timeout')
            rc = self.process.wait(timeout=remaining)
            self.exit_ns = time.monotonic_ns(); self.reaped_ns = self.exit_ns
            self.actual_exit_code = rc
            C.require(rc == 0, 'native_phase_exit')
            return tail, rc
    ObservedService = BoundService


def authorize(repo, env):
    revision = env.get('GITHUB_SHA', '')
    p = C.load_profile(repo)
    expected = {'GITHUB_REPOSITORY': C.REPOSITORY, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_WORKFLOW_SHA': revision, 'GITHUB_WORKFLOW': NAME,
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_WORKFLOW_REF': C.REPOSITORY + '/' + C.WORKFLOW + '@refs/heads/main',
        'GITHUB_ACTOR': 'HKati', 'GITHUB_TRIGGERING_ACTOR': 'HKati', 'GITHUB_ACTOR_ID': '128643840',
        'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux', 'RUNNER_ENVIRONMENT': 'github-hosted',
        'GITHUB_WORKSPACE': str(repo), SOURCE: revision, 'GITHUB_JOB': 'verify_host'}
    C.require(all(env.get(k) == v for k, v in expected.items()) and
              re.fullmatch(r'[1-9][0-9]{0,23}', env.get('GITHUB_RUN_ID', '')) is not None, 'owner_context')
    C.require(type(env.get(REQUEST)) is str and type(env.get(DIGEST)) is str and env.get('GITHUB_EVENT_PATH'), 'owner_request_missing')
    raw = env[REQUEST].encode('utf-8', 'strict')
    C.check_request(repo, raw, env[DIGEST], revision)
    event = C.parse(C.held_read(Path(env['GITHUB_EVENT_PATH']), 512 * 1024))
    C.same(event.get('inputs'), {'source_commit': revision, 'native_request': env[REQUEST],
                               'native_request_sha256': env[DIGEST]}, 'dispatch_input_binding')
    C.require(event.get('ref') in ('main', 'refs/heads/main') and
              event.get('sender', {}).get('login') == 'HKati' and
              type(event['sender'].get('id')) is int and event['sender']['id'] == 128643840 and
              event['sender'].get('type') == 'User' and
              event.get('repository', {}).get('full_name') == C.REPOSITORY, 'dispatch_owner_binding')
    sources = C.source_closure(repo, revision, p['source_paths'])
    return p, {'repository': C.REPOSITORY, 'workflow': C.WORKFLOW, 'source_commit': revision,
               'run_id': env['GITHUB_RUN_ID'], 'run_attempt': 1, 'job_name': 'verify_host'}, sources, raw


def authenticate_current(client, binding, budget):
    api = U.transport.api_json
    main = api(client, '/git/ref/heads/main', budget)
    C.require(main.get('object', {}).get('sha') == binding['source_commit'], 'current_main_changed')
    run = api(client, '/actions/runs/' + binding['run_id'] + '/attempts/1', budget)
    C.require(type(run.get('id')) is int and str(run['id']) == binding['run_id'] and
              type(run.get('run_attempt')) is int and run['run_attempt'] == 1 and
              run.get('head_sha') == binding['source_commit'] and run.get('event') == 'workflow_dispatch' and
              run.get('head_branch') == 'main' and run.get('path') == C.WORKFLOW and
              run.get('repository', {}).get('full_name') == C.REPOSITORY and
              run.get('head_repository', {}).get('full_name') == C.REPOSITORY, 'current_run_binding')
    for who in ('actor', 'triggering_actor'):
        actor = run.get(who, {})
        C.require(actor.get('login') == 'HKati' and type(actor.get('id')) is int and actor['id'] == 128643840,
                  'current_actor_binding')
    jobs = api(client, '/actions/runs/' + binding['run_id'] + '/attempts/1/jobs?per_page=100', budget)
    C.require(type(jobs.get('total_count')) is int and jobs['total_count'] == 1 and len(jobs.get('jobs', [])) == 1, 'current_job_extent')
    job = jobs['jobs'][0]
    C.require(job.get('name') == 'verify_host' and type(job.get('id')) is int and job['id'] > 0 and
              type(job.get('run_id')) is int and str(job['run_id']) == binding['run_id'] and
              type(job.get('run_attempt')) is int and job['run_attempt'] == 1 and
              job.get('head_sha') == binding['source_commit'] and job.get('status') == 'in_progress', 'current_job_binding')
    return {**binding, 'job_id': str(job['id'])}


def frozen_write(path, raw):
    io.write_new(path, raw)
    os.chown(path, 0, 65534); os.chmod(path, 0o440)


def check_unchanged(root, projection, p, plan, budget):
    T.check_projection(root, projection, p, budget)
    C.require(T.verify_bootstrap(root / 'inputs/bootstrap.tar.gz', p, budget) == plan['bootstrap_lib_sha256'], 'base_library_changed')
    T.check_source_projection(projection, plan['source_bindings'])


def phase_record(phase, service, cleanup, input_recheck, outputs):
    seconds = service.observation.get('capture_runtime_seconds', 180)
    return {'id': phase, 'isolation': service.observation,
        'launch_ns': service.runtime_deadline_ns - seconds * 1_000_000_000,
        'isolation_observed_ns': service.isolation_observed_ns, 'exec_ns': service.exec_ns,
        'stdout_eof_ns': service.eof_ns, 'exit_observed_ns': service.exit_ns,
        'exit_code': service.actual_exit_code, 'cleanup': cleanup, 'cleanup_ns': time.monotonic_ns(),
        'input_recheck': input_recheck, 'outputs': outputs}


def checker_phase(root, private, phase, plan, p, projection, budget):
    expected = {'input_check': ('input-check.json',),
                'tokenizer_check': ('groups.json', 'dataset-manifest.json', 'token-map.json', 'tokenizer-check.json'),
                'reduction_check': ('summary.json', 'summary-check.json', 'reduction-check.json')}[phase]
    work = root / 'work' / phase; work.mkdir(mode=0o700); os.chown(work, 65534, 65534)
    stage = 'reduction' if phase == 'reduction_check' else 'capturecheck'
    python = root / ('verifier/bin/python' if phase == 'input_check' else 'capsule/runtime/bin/python')
    command = [str(python), '-I', '-B', str(root / 'source' / C.CHECKER), '--phase', phase,
               '--root', str(root), '--output', str(work), '--expected-plan-sha256', C.digest(C.encode(plan)),
               '--expected-request-sha256', plan['request_sha256']]
    service = None; error = None; cleanup = None
    try:
        check_unchanged(root, projection, p, plan, budget)
        service = ObservedService('pulse-q2-' + uuid.uuid4().hex[:24], stage, command, work,
                                  root / 'verifier/bin/python', private / (phase + '.stderr'), budget.end)
        tail, _ = service.complete(deadline=budget.end)
        C.require(tail == b'q2_worker_evidence_checked\n', 'checker_stdout')
    except BaseException as exc:
        error = exc
    finally:
        if service is not None:
            try:
                with U.phase_boundary(U.cleanup_seconds(budget)):
                    cleanup = observed_native.close_capture_service(service)
            except BaseException as exc:
                if error is None: error = exc
    if error is not None: raise error
    C.require(cleanup is not None and {f.name for f in work.iterdir()} == set(expected), 'checker_output_extent')
    check_unchanged(root, projection, p, plan, budget)
    outputs = {}
    for name in expected:
        raw = C.held_read(work / name)
        frozen_write(root / 'evidence' / name, raw); outputs[name] = C.digest(raw)
    return phase_record(phase, service, cleanup, 'unchanged', outputs)


def prelaunch(root, plan):
    _, slots = P.fixed_slots(C.held_read(root / 'source' / C.WORKLOAD))
    names = [C.WORKER, C.WORKLOAD, C.PACK + 'profiles/q2_reference_subject_v0.json', C.PACK + 'profiles/q2_reference_model_files_v0.json']
    sources = []
    for name in sorted(names):
        raw = C.held_read(root / 'capsule/source' / name)
        C.require(raw == C.held_read(root / 'source' / name), 'capsule_source_identity')
        sources.append({'path': name, 'size': len(raw), 'sha256': C.digest(raw)})
    b = plan['binding']
    return {'record_type': 'q2_capture_prelaunch_v0', 'record_status': 'native', 'scope': C.SCOPE,
        'context': {k: b[k] for k in ('repository', 'workflow', 'source_commit', 'run_id', 'run_attempt')} |
            {'actor': 'HKati', 'event': 'workflow_dispatch', 'origin': 'owner_dispatched_github_q2_capture'},
        'source_files': sources, 'slots': slots, 'planned_calls': 150, 'limits': P.LIMITS,
        'phase_start_ns': plan['phase_start_ns'], 'phase_deadline_ns': plan['phase_deadline_ns'],
        'started_at': datetime.now(timezone.utc).isoformat(), 'request_sha256': plan['request_sha256'],
        'capsule_sha256': P.CAPSULE_SHA256, 'observer_contract_sha256': plan['observer_contract_sha256'],
        'authority_effect': 'none', 'production_gate_eligible': False}


def worker_phase(root, private, plan, p, projection, budget, execution_state):
    evidence = private / 'native'; evidence.mkdir(mode=0o700); (evidence / 'calls').mkdir(mode=0o700)
    pre = C.parse(C.held_read(root / 'control/capture-prelaunch.json'))
    raw_pre = C.encode(pre); io.write_new(evidence / 'capture-prelaunch.json', raw_pre)
    command = [C.digest(raw_pre) if x == '<bound-prelaunch-sha256>' else x for x in plan['execution']['worker_argv_template']]
    work = root / 'work/worker'; work.mkdir(mode=0o700); os.chown(work, 65534, 65534)
    prefix = 'pulse-q2-' + uuid.uuid4().hex[:24]
    service = None; finished_exchange = False; primary_error = None
    try:
        check_unchanged(root, projection, p, plan, budget)
        service = ObservedService(prefix, 'captureworker', command, work,
            root / 'verifier/bin/python', private / 'worker.stderr', budget.end)
        execution_state['worker_started'] = True
        execution_state['service'] = service
        ready_raw = service.reader.line(min(service.deadline, time.monotonic() + 180))
        ready_ns = time.monotonic_ns()
        ready = C.parse(ready_raw, 128 * 1024)
        C.fields(ready, 'record_type binding effective_generation runtime', 'model_ready_fields')
        C.require(ready['record_type'] == 'q2_capture_model_ready_v0', 'model_ready_type')
        C.same(ready['binding'], {'prelaunch_sha256': C.digest(raw_pre), 'source_commit': plan['binding']['source_commit'],
                   'run_id': plan['binding']['run_id'], 'run_attempt': 1}, 'model_ready_binding')
        C.same(ready['runtime'], P.RUNTIME, 'model_ready_runtime')
        C.require(C.digest(C.encode(ready['effective_generation'])) == P.CONFIGURATION_SHA256, 'model_ready_configuration')
        execution_state['model_ready_observed'] = True
        io.write_new(evidence / 'capture-model-ready.json', ready_raw)
        subject_raw = C.encode({'record_type': 'q2_capture_subject_v0', 'prelaunch_sha256': C.digest(raw_pre),
            'definition_sha256': P.DEFINITION_SHA256, 'worker_sha256': P.WORKER_SHA256,
            'ready_sha256': C.digest(ready_raw), 'effective_generation': ready['effective_generation'],
            'runtime': ready['runtime'], 'authority_effect': 'none', 'production_gate_eligible': False})
        frozen_write(root / 'control/capture-subject.json', subject_raw)
        io.write_new(evidence / 'capture-subject.json', subject_raw)
        occurrences = [{'slot': slot, 'status': 'not_started'} for slot in pre['slots']]
        execution_state['occurrences'] = occurrences
        # Unchanged exchange implementation: no local approximation of the
        # timers, per-call permission, original wire records, FINISH or cleanup.
        terminal = A.capture_session_exchange(observed_native, service, prefix, evidence, pre, subject_raw, pre['slots'], occurrences)
        finished_exchange = True
        check_unchanged(root, projection, p, plan, budget)
        cleanup = terminal['cleanup']
        life = {'record_type': 'q2_worker_protocol_lifecycle_v0', 'observation_basis': 'supplied_external_observer_records',
            'launch_ns': terminal['worker_launch_ns'], 'isolation_observed_ns': service.isolation_observed_ns,
            'exec_ns': service.exec_ns, 'model_ready_received_ns': ready_ns,
            'bound_frame_base64': base64.b64encode(service.bound_raw).decode('ascii'),
            'bound_received_ns': service.bound_received_ns, 'commands': service.commands,
            'stdout_eof_ns': service.eof_ns, 'exit_observed_ns': service.exit_ns, 'process_reaped_ns': service.reaped_ns,
            'cleanup_completed_ns': time.monotonic_ns(), 'exit_code': service.actual_exit_code,
            'client_reaped': cleanup['client_reaped'], 'sandbox': terminal['sandbox'], 'cleanup': cleanup,
            'source_recheck': 'unchanged', 'input_recheck': 'unchanged', 'private_tree_cleanup': 'pending'}
        io.write_new(evidence / 'lifecycle-before-cleanup.json', C.encode(life))
        for path in evidence.rglob('*'):
            if path.is_file():
                destination = root / 'evidence' / path.relative_to(evidence)
                destination.parent.mkdir(mode=0o550, parents=True, exist_ok=True)
                os.chown(destination.parent, 0, 65534)
                frozen_write(destination, C.held_read(path))
        return phase_record('worker', service, cleanup, 'unchanged', {'transcript.json': C.digest(C.encode(terminal))})
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        if service is not None and not finished_exchange:
            # The exchange already attempts cleanup on failure. Re-observe it
            # here as well, including startup/readiness failures before BIND.
            try:
                with U.phase_boundary(U.cleanup_seconds(budget)):
                    observed_native.close_capture_service(service)
            except BaseException:
                # Keep the original execution error. The service remains
                # unverified and the final supervisor rechecks its cleanup.
                if primary_error is None:
                    raise


def native_evidence_zip(buffers):
    C.require(set(buffers) == C.evidence_names(), 'publication_extent')
    C.inventory(buffers)
    out = byte_io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=False) as z:
        for name, raw in sorted(buffers.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 15, 0, 0, 0)); info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o600) << 16; info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, raw)
    C.require(len(out.getvalue()) <= 64 * 1024 * 1024, 'publication_bound')
    return out.getvalue()


def supervise(repo, environment=None, bootstrap_snapshot=None):
    env = dict(os.environ if environment is None else environment)
    token = env.pop(TOKEN, '')
    for key in list(os.environ):
        if key.startswith('PULSE_Q2_'): os.environ.pop(key, None)
    ACTIVE_SERVICES.clear(); ACTIVE_TIMERS.clear()
    budget = T.Budget(1200)
    run_dir = None; destination = None; error = None; buffers = None; result = None
    cleaned = False; bootstrap_cleaned = bootstrap_snapshot is None
    phases = []; state = {'worker_started': False, 'model_ready_observed': False, 'occurrences': []}
    try:
        with U.phase_boundary(1200):
            p, binding, sources, request_raw = authorize(repo, env)
            host = U.host_record(env, p)  # Strict seven-field equality before acquisition/calls.
            parent = Path(env.get('RUNNER_TEMP', '')).absolute()
            C.require(parent.is_dir() and not any(p.is_symlink() for p in (parent, *parent.parents)) and
                      parent != repo and repo not in parent.parents and
                      shutil.disk_usage('/var/lib').free >= p['limits']['minimum_free_bytes'], 'native_output_parent')
            destination = parent / 'q2-native-worker'; destination.mkdir(mode=0o755)
            run_dir = Path(tempfile.mkdtemp(prefix='pulse-q2-worker-', dir='/var/lib')); run_dir.chmod(0o700)
            private = run_dir / 'private'; private.mkdir(mode=0o700)
            root = run_dir / 'projection'; root.mkdir(mode=0o700)
            client = io.GitHubArtifactTransport(token)
            binding = authenticate_current(client, binding, budget)
            for role, filename in T.ARCHIVE_FILES.items():
                U.transport.download_artifact(client, p['inputs'][role], private / filename, budget)
            pub = U.transport.load_profile(repo)
            U.transport.download_bootstrap(pub['bootstrap'], private / 'bootstrap.tar.gz', budget)
            U.transport.download_bootstrap(pub['pip'], private / pub['pip']['filename'], budget)
            del client; token = None
            bootstrap_lib = U.prepare_bootstrap_library(private, p, budget)
            prepared = {'repo': repo, 'path': private}
            prepared['verifier_rows'] = U.prepare_verifier(prepared, root, p, budget)
            T.bind_collector_dependencies(root / 'verifier', prepared['verifier_rows'], p, budget)
            projection, docs = U.materialize(repo, prepared, root, p, sources, budget)
            for name in ('control', 'work', 'evidence'):
                (root / name).mkdir(mode=0o550); os.chown(root / name, 0, 65534)
            plan = {'record_type': 'q2_worker_execution_plan_v0', 'scope': C.SCOPE, 'binding': binding,
                'source_bindings': sources, 'host': host, 'request_sha256': C.digest(request_raw),
                'projection_sha256': C.digest(C.encode(projection)), 'bootstrap_lib_sha256': bootstrap_lib,
                'observer_contract_sha256': C.digest(C.encode({'source_bindings': sources, 'execution': K.execution_plan(root)})),
                'execution': K.execution_plan(root), 'phase_start_ns': budget.start_ns,
                'phase_deadline_ns': budget.start_ns + 1200_000_000_000, **P.NON_AUTHORITY}
            for name, raw in [('request.json', request_raw), ('plan.json', C.encode(plan)), ('projection.json', C.encode(projection))]:
                frozen_write(root / 'control' / name, raw)
                frozen_write(root / 'evidence' / name, raw)
            C.validate_json(repo, 'plan', plan)
            frozen_write(root / 'control/capture-prelaunch.json', C.encode(prelaunch(root, plan)))
            U.expose_projection(run_dir)
            phases.append(checker_phase(root, private, 'input_check', plan, p, projection, budget))
            phases.append(worker_phase(root, private, plan, p, projection, budget, state))
            phases.append(checker_phase(root, private, 'tokenizer_check', plan, p, projection, budget))
            phases.append(checker_phase(root, private, 'reduction_check', plan, p, projection, budget))
            check_unchanged(root, projection, p, plan, budget)
            C.same(C.source_closure(repo, binding['source_commit'], p['source_paths']), sources, 'final_source_changed')
            buffers = {f.relative_to(root / 'evidence').as_posix(): C.held_read(f) for f in (root / 'evidence').rglob('*') if f.is_file()}
            C.require(set(buffers) == C.evidence_names() - {'result.json', 'lifecycle.json'}, 'native_evidence_extent')
            C.inventory(buffers)
            reduction = C.parse(buffers['reduction-check.json'])
            result = {'schema_version': 'q2_release_host_worker_result_v0', 'scope': C.SCOPE,
                'status': 'native_worker_verified', 'binding': binding, 'plan_sha256': C.digest(C.encode(plan)),
                'phases': phases, 'source_recheck': 'unchanged', 'cleanup': 'pending',
                'private_cleanup_completed_ns': None, 'evidence_inventory': [],
                'worker_protocol_completed': True, 'model_ready_observed': True, 'completed_calls': 150,
                'metric_pass': reduction['metric_pass'], 'historical_metric_pass': False,
                'full_release_host_verified': False, 'q2_comparison_accepted': False,
                'clock_relation': 'not_verified', 'resource_measurement': 'unavailable',
                'observation_trust': 'owner_runner_privileged_observer_and_github_control_plane', **P.NON_AUTHORITY}
    except BaseException as exc:
        error = exc
    finally:
        token = None
        # A constructor can fail after creating a service. Keep its object before
        # __init__ and inspect that unit too; deleting files cannot prove cleanup.
        for service in ACTIVE_SERVICES:
            if not getattr(service, 'cleanup_verified', False):
                try:
                    with U.phase_boundary(U.cleanup_seconds(budget)):
                        observed_native.close_capture_service(service)
                except BaseException as exc:
                    if error is None: error = exc
        for prefix, closed in list(ACTIVE_TIMERS.items()):
            if not closed:
                try:
                    with U.phase_boundary(U.cleanup_seconds(budget)):
                        observed_native.disarm_capture_watchdog(prefix)
                except BaseException as exc:
                    if error is None: error = exc
        for path, kind in ((run_dir, 'run'), (bootstrap_snapshot, 'bootstrap')):
            if path is not None:
                try:
                    with U.phase_boundary(U.cleanup_seconds(budget)):
                        shutil.rmtree(path); C.require(not os.path.lexists(path), 'private_cleanup_unverified')
                        if kind == 'run': cleaned = True
                        else: bootstrap_cleaned = True
                except BaseException as exc:
                    if error is None: error = exc
    if error is None:
        try:
            C.require(cleaned and bootstrap_cleaned and buffers is not None and result is not None and
                      all(getattr(s, 'cleanup_verified', False) for s in ACTIVE_SERVICES) and
                      all(ACTIVE_TIMERS.values()), 'private_cleanup_unverified')
            before = C.parse(buffers['lifecycle-before-cleanup.json'])
            buffers['lifecycle.json'] = C.encode({**before, 'private_tree_cleanup': 'verified_removed'})
            result.update(cleanup='verified_removed', private_cleanup_completed_ns=time.monotonic_ns(),
                          evidence_inventory=C.inventory(buffers))
            C.validate_json(repo, 'result', result)
            buffers['result.json'] = C.encode(result)
            # Validate carrier before publication. No fresh tokenizer/model call.
            K.verify_carrier(repo, buffers, C.digest(buffers['result.json']))
            archive = native_evidence_zip(buffers)
            U.atomic_publish(destination, 'evidence.zip', archive)
            U.atomic_publish(destination, 'receipt.json', C.encode({'record_type': 'q2_worker_artifact_receipt_v0',
                'status': 'native_worker_verified', 'binding': result['binding'], 'archive_sha256': C.digest(archive),
                'archive_size_bytes': len(archive), 'result_sha256': C.digest(buffers['result.json']),
                'metric_pass': result['metric_pass'], 'historical_metric_pass': False,
                'cleanup': 'verified_removed', **P.NON_AUTHORITY}))
            return result
        except BaseException as exc:
            error = exc
            if destination is not None:
                for name in ('evidence.zip', 'receipt.json'):
                    try: (destination / name).unlink(missing_ok=True)
                    except OSError: pass
    if destination is not None:
        service = state.get('service')
        # These are command/receipt observations, not an inferred count of model
        # calls that may have occurred after a missing response or host loss.
        go_count = sum(r['command'].startswith('GENERATE ') for r in getattr(service, 'commands', []))
        completed = sum(r.get('status') == 'completed' for r in state['occurrences'])
        failure = {'record_type': 'q2_worker_failure_v0', 'status': 'rejected',
            'worker_started': state['worker_started'], 'model_ready_observed': state['model_ready_observed'],
            'generation_commands_written': go_count, 'completed_response_receipts': completed,
            'cleanup': 'verified_removed' if cleaned and bootstrap_cleaned and
                all(getattr(s, 'cleanup_verified', False) for s in ACTIVE_SERVICES) and all(ACTIVE_TIMERS.values()) else 'not_verified',
            'accepted_native_result': False, 'error_code': 'q2_worker_verification_rejected', **P.NON_AUTHORITY}
        try: U.atomic_publish(destination, 'failure.json', C.encode(failure))
        except Exception: pass
    raise error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    args = parser.parse_args(argv); snapshot = None
    try:
        repo = args.repo_root.resolve(strict=True)
        snapshot = bootstrap_sources(repo, dict(os.environ))
        initialize_modules(snapshot)
        supervise(repo, bootstrap_snapshot=snapshot); snapshot = None
        print('q2_native_worker_verified_no_release_authority')
        return 0
    except Exception:
        print('q2_worker_verification_rejected', file=sys.stderr); return 2
    finally:
        if snapshot is not None:
            try: shutil.rmtree(snapshot)
            except OSError: pass

if __name__ == '__main__':
    raise SystemExit(main())
