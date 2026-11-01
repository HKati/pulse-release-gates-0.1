#!/usr/bin/env python3
"""Prepare, run or replay the separate zero-candidate W1 environment admission.

Only the fixed benign timeout/output controls are reachable. This entrypoint
never calls native execute, prepares a native request or supplies a candidate.
Image acquisition is a separate, explicitly dispatched host workflow step.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('w1_admission_native_helpers', HERE / 'run_paradox_w1_native_v0.py')
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
B, O = H.B, H.O
need, canonical, digest, read_regular = O.need, O.canonical, O.digest, H.read_regular

MODULES = (*H.MODULES, 'run_paradox_w1_admission_v0.py')
CONTROLS = ('probe-time', 'probe-output')
TARGET_PATH = 'docs/experiments/PD_SM_02_W1_ADMISSION_TARGET_v0.json'
TARGET_SHA256 = '45425f14011ef6a8ce228c6928325d5882d668537fd06c3963ab7c3e64245a3b'
WORKFLOW_PATH = '.github/workflows/paradox_w1_admission_v0.yml'
IMAGE_PATH = 'docs/experiments/PD_SM_02_W1_IMAGE_v0/'
SOURCE_MAP = {**{'tools/' + n: 'tools/' + n for n in MODULES},
              'workflow.yml': WORKFLOW_PATH, 'target/target.json': TARGET_PATH,
              **{'target/' + n + '.json': IMAGE_PATH + n + '.json' for n in ('index', 'manifest', 'config')}}
CLAIM = 'ADMISSION_CLAIM.json'
CAPTURE = 'admission'
COMPLETED = 'ADMISSION_COMPLETED_UNATTESTED'
STOPPED = 'ADMISSION_STOPPED_WITH_EVIDENCE'
MANIFEST_SCHEMA = 'pd_sm_02_w1_admission_manifest_v0'
HOST_KEYS = {'github_repository', 'github_sha', 'github_workflow_sha', 'github_run_id',
             'github_run_attempt', 'runner_os', 'runner_arch', 'image_os', 'image_version'}
BOUNDARY = {'maximum_candidate_invocations': 0, 'candidate_tokens_sent': 0,
            'new_candidate_executions': 0, 'execution_authorized': False,
            'native_witness_observed': None, 'containment_observed': None,
            'model_native_correspondence': 'UNRESOLVED', 'authority_effect': 'none'}


def source_inventory(payloads):
    return {SOURCE_MAP[p]: {'bytes': len(raw), 'sha256': digest(raw),
                           'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}
            for p, raw in sorted(payloads.items())}


def inventory(payloads):
    return {p: {'bytes': len(raw), 'sha256': digest(raw)} for p, raw in sorted(payloads.items())}


def target_from(payloads):
    raw = payloads['target/target.json']
    need(digest(raw) == TARGET_SHA256, 'selected_target_identity')
    target = O.strict(raw)
    metadata = target['metadata']
    for name in ('index', 'manifest', 'config'):
        body = payloads['target/' + name + '.json']
        need(metadata[name] == {'repository_path': IMAGE_PATH + name + '.json',
                                 'bytes': len(body), 'sha256': digest(body)}, 'registry_metadata_binding')
    index = O.strict(payloads['target/index.json'])
    manifest = O.strict(payloads['target/manifest.json'])
    config = O.strict(payloads['target/config.json'])
    image = target['image']
    need('sha256:' + digest(payloads['target/index.json']) == image['index_digest'], 'registry_index_identity')
    need('sha256:' + digest(payloads['target/manifest.json']) == image['manifest_digest'], 'registry_manifest_identity')
    need('sha256:' + digest(payloads['target/config.json']) == image['image_id'], 'registry_config_identity')
    matches = [x for x in index['manifests'] if x.get('platform') == {'architecture': 'amd64', 'os': 'linux'}]
    need(len(matches) == 1 and matches[0]['digest'] == image['manifest_digest']
         and matches[0]['size'] == len(payloads['target/manifest.json']), 'registry_platform_descriptor')
    need(manifest['config']['digest'] == image['image_id']
         and manifest['config']['size'] == len(payloads['target/config.json']), 'registry_config_descriptor')
    need(config.get('os') == 'linux' and config.get('architecture') == 'amd64'
         and not config.get('config', {}).get('Volumes'), 'registry_config_platform')
    need('PYTHON_VERSION=3.13.5' in config['config']['Env'], 'registry_declared_python')
    need(manifest['annotations']['org.opencontainers.image.revision'] == image['source_commit'], 'image_source_annotation')
    need(image['pull_reference'] == 'docker.io/library/python@' + image['manifest_digest'], 'image_pull_identity')
    return target


def prepare(repo: Path, output: Path, source_commit: str, run_id: str):
    """Freeze exact local bytes, without Docker, subprocesses or authorization.

    source_commit is a declared source reference. The hosted workflow checks it
    against both checked-out HEAD and workflow SHA. Offline hashes alone do not
    authenticate a Git origin or a platform identity.
    """
    need(type(source_commit) is str and re.fullmatch('[0-9a-f]{40}', source_commit), 'source_commit')
    need(type(run_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}', run_id), 'run_id')
    repo, output = Path(repo).resolve(), Path(output).absolute()
    need(not output.exists() and not output.is_symlink(), 'output_exists')
    need(repo != output.resolve() and repo not in output.resolve().parents, 'output_inside_repository')
    need(not any(p.is_symlink() for p in output.parents), 'output_symlink_parent')
    payloads = {dest: read_regular(repo / src) for dest, src in SOURCE_MAP.items()}
    sources = {n: digest(read_regular(HERE / n)) for n in MODULES}
    need(all(digest(payloads['tools/' + n]) == sources[n] for n in MODULES), 'preparation_source_closure')
    target = target_from(payloads)
    request = {'schema_version': 'pd_sm_02_w1_admission_request_v0', 'subject': O.SUBJECT,
               'purpose': 'candidate_free_environment_admission', 'source_commit': source_commit,
               'run_id': run_id, 'attempt': 1, 'image_id': target['image']['image_id'],
               'runtime': dict(O.RUNTIME), 'policy': B.POLICY, 'policy_sha256': B.policy_digest(),
               'target_sha256': TARGET_SHA256, 'sources': sources,
               'source_files': source_inventory(payloads), 'payloads': inventory(payloads),
               'cases': [], 'supervision_controls': list(CONTROLS),
               'maximum_candidate_invocations': 0, 'automatic_retry': False,
               'execution_authorized': False, 'authority_effect': 'none'}
    output.mkdir(mode=0o700)
    for name, raw in payloads.items():
        p = output / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    raw = canonical(request)
    (output / 'request.json').write_bytes(raw)
    return {'status': 'ADMISSION_REQUEST_PREPARED', 'request_sha256': digest(raw),
            'request_path': str(output / 'request.json'), **BOUNDARY}


def validate_package(package: Path, expected_sha: str):
    package = Path(package)
    need(type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_sha), 'request_sha_required')
    raw = read_regular(package / 'request.json', 131072)
    need(digest(raw) == expected_sha, 'request_digest_mismatch')
    req = O.strict(raw, 131072)
    need(canonical(req) == raw, 'request_not_canonical')
    O.keys(req, {'schema_version', 'subject', 'purpose', 'source_commit', 'run_id', 'attempt', 'image_id',
                 'runtime', 'policy', 'policy_sha256', 'target_sha256', 'sources', 'source_files', 'payloads',
                 'cases', 'supervision_controls', 'maximum_candidate_invocations', 'automatic_retry',
                 'execution_authorized', 'authority_effect'}, 'admission_request_shape')
    need(req['schema_version'] == 'pd_sm_02_w1_admission_request_v0'
         and req['subject'] == O.SUBJECT and req['purpose'] == 'candidate_free_environment_admission', 'admission_request_role')
    need(type(req['source_commit']) is str and re.fullmatch('[0-9a-f]{40}', req['source_commit']), 'source_commit')
    need(type(req['run_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}', req['run_id']), 'run_id')
    need(type(req['attempt']) is int and req['attempt'] == 1
         and type(req['maximum_candidate_invocations']) is int and req['maximum_candidate_invocations'] == 0
         and req['cases'] == [] and req['supervision_controls'] == list(CONTROLS), 'zero_candidate_budget')
    need(req['automatic_retry'] is False and req['execution_authorized'] is False
         and req['authority_effect'] == 'none', 'admission_authority')
    need(req['runtime'] == O.RUNTIME and canonical(req['policy']) == canonical(B.POLICY)
         and req['policy_sha256'] == B.policy_digest(), 'admission_profile')
    sources = {n: digest(read_regular(HERE / n)) for n in MODULES}
    need(req['sources'] == sources, 'admission_source_closure')
    payloads = {p: read_regular(package / p) for p in SOURCE_MAP}
    need(req['payloads'] == inventory(payloads) and req['source_files'] == source_inventory(payloads), 'admission_payload_binding')
    need(all(digest(payloads['tools/' + n]) == sources[n] for n in MODULES), 'staged_source_closure')
    target = target_from(payloads)
    need(req['target_sha256'] == TARGET_SHA256 and req['image_id'] == target['image']['image_id'], 'admission_target_binding')
    allowed = set(SOURCE_MAP) | {'request.json', CLAIM}
    allowed_dirs = {str(Path(p).parent) for p in allowed if str(Path(p).parent) != '.'}
    for p in package.rglob('*'):
        need(not p.is_symlink(), 'package_symlink')
        rel = p.relative_to(package).as_posix()
        if rel == CAPTURE or rel.startswith(CAPTURE + '/'):
            continue  # Validated as a separate closed evidence inventory below.
        mode = p.stat().st_mode
        need((stat.S_ISDIR(mode) and rel in allowed_dirs) or
             (stat.S_ISREG(mode) and rel in allowed), 'unexpected_admission_package_member')
    return req


def check_host(host, req):
    O.keys(host, {'system', 'machine', 'kernel_release', 'controller_runtime', 'context'}, 'host_shape')
    need(host['system'] == 'Linux' and host['machine'] == 'x86_64', 'host_platform')
    need(type(host['kernel_release']) is str and 0 < len(host['kernel_release']) <= 128, 'host_kernel')
    need(type(host['controller_runtime']) is str and 0 < len(host['controller_runtime']) <= 128, 'host_controller')
    ctx = host['context']
    O.keys(ctx, HOST_KEYS, 'selected_host_context_required')
    need(all(type(v) is str and 0 < len(v) <= 256 for v in ctx.values()), 'host_context_values')
    need(ctx['github_repository'] == 'HKati/pulse-release-gates-0.1'
         and ctx['github_sha'] == req['source_commit'] and ctx['github_workflow_sha'] == req['source_commit']
         and re.fullmatch('[1-9][0-9]*', ctx['github_run_id']) and ctx['github_run_attempt'] == '1', 'host_source_run_binding')
    need(ctx['runner_os'] == 'Linux' and ctx['runner_arch'] == 'X64' and ctx['image_os'] == 'ubuntu24', 'selected_host_profile')
    return host


def check_daemon(info):
    need(type(info) is dict and info.get('OSType') == 'linux'
         and info.get('Architecture') in ('x86_64', 'amd64')
         and str(info.get('CgroupVersion')) == '2', 'docker_cgroup_v2_required')
    for key in ('ID', 'ServerVersion', 'KernelVersion'):
        need(type(info.get(key)) is str and 0 < len(info[key]) <= 256, 'docker_identity_' + key)


def claim_record(req, sha):
    return {'schema_version': 'pd_sm_02_w1_admission_claim_v0', 'request_sha256': sha,
            'run_id': req['run_id'], 'attempt': 1, 'admission_only_acknowledged': True,
            'maximum_candidate_invocations': 0, 'automatic_retry': False, 'authority_effect': 'none'}


def _replay_control(cap, req, sha, label, runtime_lock):
    need(label in CONTROLS, 'admission_control_only')
    d = cap / label
    cid = read_regular(d / 'container.cid', 128).decode().strip()
    need(re.fullmatch('[0-9a-f]{64}', cid), 'admission_container_id')
    before = O.strict(read_regular(d / 'inspect_before.json'))
    mounts = [m for m in before[0]['Mounts'] if m.get('Type') == 'bind']
    need(len(mounts) == 1, 'admission_mount_inventory')
    stage = Path(mounts[0]['Source'])
    B.check_inspect(before, req['image_id'], stage, sha, label, cid)
    running = O.strict(read_regular(d / 'inspect_running.json'))
    B.check_inspect(running, req['image_id'], stage, sha, label, cid, running=True)
    ready = O.strict(read_regular(d / 'readiness.json'))
    B.validate_probe(ready, sha, label)
    actual = {k: ready[k] for k in ('runtime', 'python_sha256', 'kernel_release')}
    need(not runtime_lock or runtime_lock == actual, 'admission_runtime_drift')
    runtime_lock.update(actual)
    cleanup = O.strict(read_regular(d / 'cleanup.json'))
    need(cleanup == {'container_id': cid, 'removed_and_absence_checked': True,
                     'scratch_disposal': 'container_tmpfs_removed', 'error': None}, 'admission_cleanup')
    tr = O.strict(read_regular(d / 'transport.json'))
    O.keys(tr, {'returncode', 'termination', 'detail', 'execution_token_sent'}, 'admission_transport_shape')
    need(tr['execution_token_sent'] is True and type(tr['returncode']) is int
         and tr['detail'] is None, 'admission_control_token')
    need(tr['termination'] == ('timeout' if label == 'probe-time' else 'output_limit'), 'admission_supervision_control')
    raw = read_regular(d / 'stdout.jsonl')
    need(read_regular(d / 'stderr.bin') == b'', 'admission_control_stderr')
    if label == 'probe-output':
        need(len(raw) == 65536, 'admission_output_control_size')
        first, newline, _tail = raw.partition(b'\n')
        need(newline == b'\n', 'admission_readiness_incomplete')
        frames = O.parse_frames(first + newline)
    else:
        frames = O.parse_frames(raw)
    need(frames == [ready], 'admission_readiness_transcript')
    return {'container_id': cid, 'stage': stage, 'before': before, 'running': running}


def _command_records(cap, req, sha):
    folder = cap / 'docker_commands'
    if not folder.exists():
        return []
    paths = sorted(folder.glob('*.command.json'))
    need([p.name for p in paths] == [f'{i:03d}.command.json' for i in range(1, len(paths) + 1)], 'docker_command_sequence')
    expected_files = {f'{i:03d}.{suffix}' for i in range(1, len(paths) + 1)
                      for suffix in ('command.json', 'stdout', 'stderr', 'result.json')}
    need({p.name for p in folder.iterdir()} == expected_files, 'docker_command_file_inventory')
    records = []
    prefix = None
    original_capture, stage_parent = None, None
    known_cids, created_labels = set(), set()
    for p in paths:
        stem = p.name.split('.')[0]
        argv = O.strict(read_regular(p))
        need(type(argv) is list and len(argv) >= 6 and all(type(x) is str for x in argv), 'docker_command_shape')
        current = argv[:5]
        need(Path(current[0]).is_absolute() and current[1:4] == ['--host', B.POLICY['docker_endpoint'], '--config']
             and Path(current[4]).is_absolute(), 'docker_command_endpoint')
        need(prefix is None or prefix == current, 'docker_command_prefix_drift')
        prefix = current
        stdout = read_regular(folder / (stem + '.stdout'))
        stderr = read_regular(folder / (stem + '.stderr'))
        result = O.strict(read_regular(folder / (stem + '.result.json')))
        args = argv[5:]
        # Refuse candidate starts, arbitrary exec/build/pull and unrecognized verbs,
        # even in partial evidence. The raw command prefix stays manifest-bound.
        admitted = args == ['info', '--format', '{{json .}}'] or args == ['image', 'inspect', req['image_id']]
        if args[:2] == ['container', 'create']:
            labels = [args[i + 1] for i, x in enumerate(args[:-1]) if x == '--label']
            matching = [c for c in CONTROLS if 'pulse.w1.case=' + c in labels]
            need(len(matching) == 1, 'admission_create_control')
            label = matching[0]
            need(label not in created_labels and list(CONTROLS)[len(created_labels)] == label, 'admission_create_sequence')
            created_labels.add(label)
            need('--mount' in args and '--cidfile' in args, 'admission_create_paths')
            mount = args[args.index('--mount') + 1]
            match = re.fullmatch(r'type=bind,src=(.+),dst=/inputs,readonly', mount)
            need(match is not None, 'admission_create_mount')
            stage = Path(match.group(1))
            cidfile = Path(args[args.index('--cidfile') + 1])
            need(stage.is_absolute() and stage.name == label and cidfile.is_absolute()
                 and cidfile.parts[-3:] == (CAPTURE, label, 'container.cid'), 'admission_create_paths')
            need(original_capture is None or original_capture == cidfile.parent.parent, 'admission_capture_parent_drift')
            need(stage_parent is None or stage_parent == stage.parent, 'admission_stage_parent_drift')
            original_capture, stage_parent = cidfile.parent.parent, stage.parent
            need(current[4] == str(stage.parent / 'docker-config'), 'admission_config_stage_binding')
            need(args == B.create_args(req['image_id'], stage, cidfile, sha, label), 'admission_create_arguments')
            observed_cid = stdout.decode().strip()
            cidpath = cap / label / 'container.cid'
            if cidpath.exists():
                stored_cid = read_regular(cidpath, 128).decode().strip()
                need(re.fullmatch('[0-9a-f]{64}', stored_cid), 'admission_command_cid')
                known_cids.add(stored_cid)
                if re.fullmatch('[0-9a-f]{64}', observed_cid):
                    need(observed_cid == stored_cid, 'admission_command_cid')
            elif re.fullmatch('[0-9a-f]{64}', observed_cid):
                known_cids.add(observed_cid)
            admitted = True
        if args[:2] == ['container', 'inspect']:
            admitted = len(args) == 3 and args[2] in known_cids
        elif args[:2] == ['container', 'rm']:
            admitted = len(args) == 4 and args[2] == '--force' and args[3] in known_cids
        elif args[:2] == ['container', 'ls']:
            admitted = args == ['container', 'ls', '--all', '--no-trunc', '--format', '{{.ID}}']
        need(admitted, 'unexpected_docker_admission_command')
        records.append((args, stdout, stderr, result))
    return records


def _check_success_commands(cap, req, sha, controls):
    records = _command_records(cap, req, sha)
    need(len(records) == 14, 'admission_command_count')
    need(len({c['container_id'] for c in controls.values()}) == 2, 'admission_container_reuse')
    expected = [(['info', '--format', '{{json .}}'], O.strict(read_regular(cap / 'docker_info.json'))),
                (['image', 'inspect', req['image_id']], O.strict(read_regular(cap / 'image_inspect.json')))]
    for label in CONTROLS:
        c = controls[label]
        cid, stage = c['container_id'], c['stage']
        expected.extend([
            (B.create_args(req['image_id'], stage, cap / label / 'container.cid', sha, label), ('cid', cid)),
            (['container', 'inspect', cid], c['before']),
            (['container', 'inspect', cid], c['running']),
            (['container', 'inspect', cid], ('cleanup_inspect', cid)),
            (['container', 'rm', '--force', cid], ('cid', cid)),
            (['container', 'ls', '--all', '--no-trunc', '--format', '{{.ID}}'], ('absence', cid)),
        ])
    for (args, stdout, stderr, result), (want, content) in zip(records, expected):
        # Paths in preserved create commands belong to the original capture host.
        # The portable evidence may have moved; bind the original absolute cidfile
        # by its fixed control suffix and parent shared by both control commands.
        if args[:2] == ['container', 'create']:
            idx = want.index('--cidfile') + 1
            actual_cidfile = Path(args[idx]) if len(args) > idx else Path('.')
            need(actual_cidfile.is_absolute() and actual_cidfile.parts[-3:] == (CAPTURE, want[-1], 'container.cid'), 'admission_cidfile_path')
            want = list(want)
            want[idx] = str(actual_cidfile)
        need(args == want, 'admission_command_binding')
        need(result.get('termination') == 'exited' and type(result.get('returncode')) is int
             and result['returncode'] == 0 and result.get('detail') is None
             and result.get('execution_token_sent') is False, 'admission_command_result')
        need(len(stderr) <= B.POLICY['stderr_bytes'], 'admission_command_stderr_limit')
        if isinstance(content, tuple):
            kind, cid = content
            if kind == 'cid':
                need(stdout.decode().strip() == cid, 'admission_command_cid')
            elif kind == 'absence':
                need(cid not in stdout.decode().splitlines(), 'admission_command_absence')
            else:
                xs = O.strict(stdout)
                need(type(xs) is list and len(xs) == 1 and xs[0]['Id'] == cid
                     and xs[0]['Image'] == req['image_id']
                     and xs[0]['Config']['Labels']['pulse.w1.request'] == sha, 'admission_cleanup_inspect')
        else:
            need(O.strict(stdout) == content, 'admission_command_output_binding')


def _capture_files(cap):
    result = {}
    top_files = {'summary.json', 'host_context.json', 'docker_info.json', 'image_inspect.json', 'MANIFEST.json'}
    control_files = {'container.cid', 'inspect_before.json', 'inspect_running.json', 'readiness.json',
                     'stdout.jsonl', 'stderr.bin', 'transport.json', 'cleanup.json', 'inspect_terminal.json'}
    for p in sorted(cap.rglob('*')):
        need(not p.is_symlink(), 'admission_evidence_symlink')
        parts = p.relative_to(cap).parts
        mode = p.stat().st_mode
        if stat.S_ISDIR(mode):
            need(len(parts) == 1 and parts[0] in (*CONTROLS, 'docker_commands'), 'admission_evidence_directory')
            continue
        need(stat.S_ISREG(mode), 'admission_evidence_regular_file')
        allowed = len(parts) == 1 and parts[0] in top_files
        if len(parts) == 2:
            allowed = (parts[0] in CONTROLS and parts[1] in control_files) or (
                parts[0] == 'docker_commands' and re.fullmatch(r'[0-9]{3}\.(command\.json|stdout|stderr|result\.json)', parts[1]))
        need(allowed, 'unexpected_admission_evidence')
        if parts != ('MANIFEST.json',):
            result['/'.join(parts)] = read_regular(p, 8 * 1024 * 1024)
    return result


def close_manifest(cap):
    H.write_json(cap / 'MANIFEST.json', {'schema_version': MANIFEST_SCHEMA,
                 'files': inventory(_capture_files(cap)), 'authority_effect': 'none'})


def run_admission(package, expected_sha, authorization, host_context=None):
    need(authorization == 'I_AUTHORIZE_PD_SM_02_W1_ADMISSION:' + expected_sha, 'admission_authorization_required')
    package = Path(package).absolute()
    req = validate_package(package, expected_sha)
    need(not (package / CLAIM).exists() and not (package / CAPTURE).exists(), 'admission_already_claimed')
    H.write_json(package / CLAIM, claim_record(req, expected_sha))
    cap = package / CAPTURE
    cap.mkdir(mode=0o700)
    summary = {'schema_version': 'pd_sm_02_w1_admission_summary_v0', 'status': STOPPED,
               'request_sha256': expected_sha, 'source_commit': req['source_commit'],
               'admission_only_acknowledged': True, 'acquisition_authenticity': 'PROJECT_LOCAL_UNATTESTED',
               'controls_started': [], 'controls_completed': [], 'reason': None, **BOUNDARY}
    try:
        need(sys.platform == 'linux', 'linux_controller_required')
        host = {'system': platform.system(), 'machine': platform.machine(), 'kernel_release': platform.release(),
                'controller_runtime': platform.python_implementation() + '-' + platform.python_version(),
                'context': {} if host_context is None else host_context}
        check_host(host, req)
        H.write_json(cap / 'host_context.json', host)
        with tempfile.TemporaryDirectory(prefix='pulse-w1-admission-', dir='/tmp') as tmp:
            root = Path(tmp)
            root.chmod(0o755)
            backend = B.Docker(root / 'docker-config', cap / 'docker_commands')
            info = O.strict(backend.command(['info', '--format', '{{json .}}'], projection=B.project_info))
            H.write_json(cap / 'docker_info.json', info)
            check_daemon(info)
            need(info['KernelVersion'] == host['kernel_release'], 'daemon_host_kernel_binding')
            img = O.strict(backend.command(['image', 'inspect', req['image_id']], projection=B.project_image))
            H.write_json(cap / 'image_inspect.json', img)
            B.check_image(img, req['image_id'])
            runtime_lock, replay_lock, replayed = {}, {}, {}
            for label in CONTROLS:
                summary['controls_started'].append(label)
                # No candidate row, candidate bytes, native request or execute call.
                H.one_container(backend, package, req, None, label, expected_sha, cap / label, root, runtime_lock)
                replayed[label] = _replay_control(cap, req, expected_sha, label, replay_lock)
                need(replay_lock['kernel_release'] == host['kernel_release'], 'container_host_kernel_binding')
                summary['controls_completed'].append(label)
            _check_success_commands(cap, req, expected_sha, replayed)
            summary['status'] = COMPLETED
    except BaseException as exc:
        summary['reason'] = type(exc).__name__ + ':' + str(exc)
    finally:
        H.write_json(cap / 'summary.json', summary)
        close_manifest(cap)
    return summary


def verify_admission(package, expected_sha):
    """Replay preserved records only; never run a process, container or control."""
    package = Path(package)
    req = validate_package(package, expected_sha)
    need(O.strict(read_regular(package / CLAIM)) == claim_record(req, expected_sha), 'admission_claim_binding')
    cap = package / CAPTURE
    manifest = O.strict(read_regular(cap / 'MANIFEST.json'))
    O.keys(manifest, {'schema_version', 'files', 'authority_effect'}, 'admission_manifest_shape')
    need(manifest['schema_version'] == MANIFEST_SCHEMA and manifest['authority_effect'] == 'none', 'admission_manifest_role')
    files = _capture_files(cap)
    need(manifest['files'] == inventory(files), 'admission_manifest_binding')
    summary = O.strict(read_regular(cap / 'summary.json'))
    expected_keys = {'schema_version', 'status', 'request_sha256', 'source_commit', 'admission_only_acknowledged',
                     'acquisition_authenticity', 'controls_started', 'controls_completed', 'reason'} | set(BOUNDARY)
    O.keys(summary, expected_keys, 'admission_summary_shape')
    need(summary['schema_version'] == 'pd_sm_02_w1_admission_summary_v0' and summary['request_sha256'] == expected_sha
         and summary['source_commit'] == req['source_commit'] and summary['admission_only_acknowledged'] is True
         and summary['acquisition_authenticity'] == 'PROJECT_LOCAL_UNATTESTED', 'admission_summary_binding')
    need(canonical({k: summary[k] for k in BOUNDARY}) == canonical(BOUNDARY), 'admission_claim_boundary')
    started, completed = summary['controls_started'], summary['controls_completed']
    need(type(started) is list and type(completed) is list and started == list(CONTROLS[:len(started)])
         and completed == started[:len(completed)] and len(started) - len(completed) <= 1,
         'admission_control_sequence')
    dirs = {p.name for p in cap.iterdir() if p.is_dir() and p.name in CONTROLS}
    need(dirs.issubset(set(started)) and set(completed).issubset(dirs), 'admission_control_directory_binding')
    need(summary['status'] in (COMPLETED, STOPPED), 'admission_summary_status')
    _command_records(cap, req, expected_sha)  # Also inspect attempted commands on failed runs.
    replay_lock, replayed = {}, {}
    if completed or summary['status'] == COMPLETED:
        host = check_host(O.strict(read_regular(cap / 'host_context.json')), req)
        info = O.strict(read_regular(cap / 'docker_info.json'))
        check_daemon(info)
        need(info['KernelVersion'] == host['kernel_release'], 'daemon_host_kernel_binding')
        B.check_image(O.strict(read_regular(cap / 'image_inspect.json')), req['image_id'])
        for label in completed:
            replayed[label] = _replay_control(cap, req, expected_sha, label, replay_lock)
            need(replay_lock['kernel_release'] == host['kernel_release'], 'container_host_kernel_binding')
    if summary['status'] == COMPLETED:
        need(started == list(CONTROLS) and completed == list(CONTROLS) and summary['reason'] is None, 'admission_completion_claim')
        _check_success_commands(cap, req, expected_sha, replayed)
    else:
        need(type(summary['reason']) is str and len(summary['reason']) > 0, 'admission_failure_reason')
    return {'status': 'ADMISSION_RECORDS_REPLAYED', 'admission_status': summary['status'],
            'request_sha256': expected_sha, 'controls_replayed': completed, 'manifest_members': len(files),
            'acquisition_authenticity': 'NOT_EXTERNALLY_VERIFIED', **BOUNDARY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--repo-root', type=Path, default=HERE.parent)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--run-id', required=True)
    for verb in ('verify', 'run-admission', 'verify-admission'):
        p = sub.add_parser(verb)
        p.add_argument('--package', type=Path, required=True)
        p.add_argument('--request-sha256', required=True)
        if verb == 'run-admission':
            p.add_argument('--authorize-admission', required=True)
            p.add_argument('--host-context', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = prepare(args.repo_root, args.output, args.source_commit, args.run_id)
        elif args.command == 'run-admission':
            context = O.strict(read_regular(args.host_context)) if args.host_context else None
            result = run_admission(args.package, args.request_sha256, args.authorize_admission, context)
        elif args.command == 'verify-admission':
            result = verify_admission(args.package, args.request_sha256)
        else:
            validate_package(args.package, args.request_sha256)
            result = {'status': 'ADMISSION_REQUEST_VALID_NOT_AUTHORIZED', **BOUNDARY}
        print(canonical(result).decode())
        return 2 if result.get('status') == STOPPED or result.get('admission_status') == STOPPED else 0
    except (O.CaptureError, B.BoundaryError, ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        print(canonical({'status': 'BLOCKED', 'reason': type(exc).__name__ + ':' + str(exc), **BOUNDARY}).decode())
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
