"""Fresh source/preflight collector for the isolated QRH 003 pilot.

There is deliberately no sign-arbitrary-JSON CLI and no command that executes
an OpenAI proof. Only named operations below can create admissible receipts.
The local operator, Python/crypto/Git, OS and hardware are declared trusted.
This does not authenticate an external institution or create expert review.
"""
from __future__ import annotations

# Direct scripts cannot establish source binding before their imports.
if __name__ == "__main__":
    import sys as _qrh_sys
    print("QRH003_SOURCE_BOUND_LAUNCH_REQUIRED: use source_bound.py with python -I", file=_qrh_sys.stderr)
    raise SystemExit(2)


import argparse
import datetime as dt
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import time
import traceback

try:
    from .common import (AuditError, SUBJECT_COMMIT, PULSE_COMMIT,
        canonical_bytes, sha256_bytes, sha256_file, strict_loads, secure_read,
        read_json, exclusive_write, write_json, source_runtime, verify_source_anchor)
    from . import acquire, source_closure
except ImportError:
    from common import (AuditError, SUBJECT_COMMIT, PULSE_COMMIT,
        canonical_bytes, sha256_bytes, sha256_file, strict_loads, secure_read,
        read_json, exclusive_write, write_json, source_runtime, verify_source_anchor)
    import acquire
    import source_closure

ROOT = Path(__file__).absolute().parents[1]


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def progress(phase, **fields):
    print(canonical_bytes({'phase': phase, **fields}).decode('utf-8'), flush=True)


class Collector:
    def __init__(self, prepared, private_key, output, run_key, profile_kind):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        self.prepared, self.output = Path(prepared).absolute(), Path(output).absolute()
        key_path = Path(private_key).absolute()
        if self.output.exists():
            raise AuditError('QRH003_OUTPUT_NAMESPACE_NOT_FRESH', str(self.output))
        if self.output == key_path or self.output in key_path.parents:
            raise AuditError('QRH003_PRIVATE_KEY_INSIDE_BUNDLE')
        if self.output == self.prepared or self.output in self.prepared.parents or self.prepared in self.output.parents:
            raise AuditError('QRH003_ANCHOR_BUNDLE_DIRECTORIES_OVERLAP')
        self.anchor = read_json(self.prepared / 'anchor.json')
        if self.anchor['subject_commit'] != SUBJECT_COMMIT or self.anchor['pulse_commit'] != PULSE_COMMIT:
            raise AuditError('QRH003_SUBJECT_COMMIT_MISMATCH')
        self._verify_code()
        mode = key_path.lstat().st_mode
        if not stat.S_ISREG(mode) or stat.S_IMODE(mode) & 0o077:
            raise AuditError('QRH003_PRIVATE_KEY_PERMISSIONS_UNSAFE')
        seed = secure_read(key_path.parent, key_path.name, max_bytes=64)
        self.key = Ed25519PrivateKey.from_private_bytes(seed)
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        keys = [k for k in self.anchor['collector_keys'] if k['public_key_hex'] == public]
        if len(keys) != 1:
            raise AuditError('QRH003_COLLECTOR_UNAUTHORIZED')
        self.key_record = keys[0]
        self.created = utc_now()
        self.run_key, self.profile_kind = run_key, profile_kind
        self.artifacts, self.receipts, self.artifact_names = [], [], set()
        self.output.mkdir(parents=True, mode=0o700)
        admitted_config_bytes = {}
        for name, field in (('profile.json', 'profile_sha256'), ('policy.yml', 'policy_sha256'),
                            ('gate_registry.yml', 'registry_sha256')):
            data = secure_read(self.prepared, name)
            if sha256_bytes(data) != self.anchor[field]:
                raise AuditError('QRH003_POLICY_ANCHOR_MISMATCH', name)
            admitted_config_bytes[name] = data
            self.add(name, data, 'declared_policy')
        for name in ('claim_map.json', 'capture_policy.json'):
            data = secure_read(self.prepared, name)
            admitted_config_bytes[name] = data
            self.add(name, data, 'declared_capture_or_scope_policy')
        self.profile = strict_loads(admitted_config_bytes['profile.json'])
        policy_hash = sha256_bytes(admitted_config_bytes['capture_policy.json'])
        if policy_hash != self.key_record['capture_policy_sha256']:
            raise AuditError('QRH003_CAPTURE_POLICY_ANCHOR_MISMATCH')
        if self.key_record['collector_sha256'] != sha256_file(Path(__file__).absolute()):
            raise AuditError('QRH003_COLLECTOR_ANCHOR_MISMATCH')

    def _verify_code(self):
        verify_source_anchor(self.anchor, ROOT)

    def add(self, name, data, role):
        if name in self.artifact_names:
            raise AuditError('QRH003_DUPLICATE_ARTIFACT', name)
        if Path(name).is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or '\\' in name:
            raise AuditError('QRH003_UNSAFE_PATH', name)
        target = self.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        exclusive_write(target, data)
        self.artifact_names.add(name)
        cls = 'actual_observation' if self.anchor['trust_domain'] == 'PRODUCTION' else 'synthetic_fixture'
        self.artifacts.append({'path': name, 'sha256': sha256_bytes(data), 'bytes': len(data),
                               'role': role, 'evidence_class': cls})

    def register_existing(self, directory):
        for path in sorted(Path(directory).rglob('*')):
            if not path.is_file() and not path.is_symlink():
                continue
            name = path.relative_to(self.output).as_posix()
            if name in self.artifact_names:
                continue
            data = secure_read(self.output, name)
            self.artifact_names.add(name)
            cls = 'actual_observation' if self.anchor['trust_domain'] == 'PRODUCTION' else 'synthetic_fixture'
            self.artifacts.append({'path': name, 'sha256': sha256_bytes(data), 'bytes': len(data),
                                   'role': 'raw_execution_evidence', 'evidence_class': cls})

    def observation(self, kind, obj):
        if kind not in self.key_record['allowed_kinds']:
            raise AuditError('QRH003_COLLECTOR_KIND_UNAUTHORIZED', kind)
        data = canonical_bytes(obj) + b'\n'
        observation_path = 'observations/' + kind + '.json'
        self.add(observation_path, data, kind)
        payload = {
            'schema_version': 'qrh003_capture_v1', 'kind': kind,
            'trust_domain': self.anchor['trust_domain'],
            'evidence_class': 'actual_observation' if self.anchor['trust_domain'] == 'PRODUCTION' else 'synthetic_fixture',
            'run_key': self.run_key, 'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
            'collector_sha256': self.key_record['collector_sha256'],
            'capture_policy_sha256': self.key_record['capture_policy_sha256'],
            'created_utc': utc_now(),
            'body': {'observation_path': observation_path, 'observation_sha256': sha256_bytes(data)},
        }
        raw = canonical_bytes(payload) + b'\n'
        receipt_path = 'receipts/' + kind + '.json'
        self.add(receipt_path, raw, 'authenticated_collector_receipt')
        self.receipts.append({'payload_path': receipt_path,
            'signature_hex': self.key.sign(raw).hex(), 'key_id': self.key_record['key_id']})

    def command(self, name, argv, timeout, *, pass_fds=(), binding=None):
        """Capture real process status; no interpretation of the word success."""
        started, tick = utc_now(), time.monotonic()
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TZ') if key in os.environ}
        environment['PYTHONNOUSERSITE'] = '1'
        timed_out, return_code, out, err, failure = False, None, b'', b'', None
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=environment, close_fds=True,
                pass_fds=pass_fds, start_new_session=True)
            try:
                out, err = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                out, err = process.communicate()
            return_code = process.returncode
        except OSError as exc:
            failure = str(exc)
        self.add('processes/' + name + '.stdout', out, 'process_stdout')
        self.add('processes/' + name + '.stderr', err, 'process_stderr')
        record = {'argv': argv, 'started_utc': started, 'ended_utc': utc_now(),
                  'environment': environment,
                  'elapsed_seconds': round(time.monotonic() - tick, 6), 'return_code': return_code,
                  'timed_out': timed_out, 'execution_error': failure,
                  'stdout_path': 'processes/' + name + '.stdout', 'stdout_sha256': sha256_bytes(out),
                  'stderr_path': 'processes/' + name + '.stderr', 'stderr_sha256': sha256_bytes(err)}
        if binding is not None:
            record['source_binding'] = binding
        self.add('processes/' + name + '.json', canonical_bytes(record) + b'\n', 'process_result')
        return record

    def study_command(self, name, command, arguments, timeout):
        runtime = source_runtime()
        with runtime.child(command, arguments) as (argv, pass_fds):
            return self.command(name, argv, timeout, pass_fds=pass_fds,
                                binding=runtime.contract())

    def finish(self):
        self._verify_code()
        manifest = {'schema_version': 'qrh003_bundle_v1', 'trust_domain': self.anchor['trust_domain'],
            'run_key': self.run_key, 'created_utc': utc_now(), 'subject_commit': SUBJECT_COMMIT,
            'pulse_commit': PULSE_COMMIT, 'profile_kind': self.profile_kind,
            'artifacts': sorted(self.artifacts, key=lambda row: row['path']),
            'receipts': self.receipts}
        manifest_bytes = canonical_bytes(manifest) + b'\n'
        exclusive_write(self.output / 'manifest.json', manifest_bytes)
        if 'bundle_seal' not in self.key_record['allowed_kinds']:
            raise AuditError('QRH003_MANIFEST_SEAL_KEY_UNAUTHORIZED')
        write_json(self.output / 'manifest.signature.json', {
            'schema_version': 'qrh003_manifest_signature_v1',
            'key_id': self.key_record['key_id'],
            'manifest_sha256': sha256_bytes(manifest_bytes),
            'signature_hex': self.key.sign(manifest_bytes).hex(),
        })
        return {'bundle': str(self.output), 'run_key': self.run_key,
                'manifest_sha256': sha256_file(self.output / 'manifest.json'),
                'artifact_count': len(self.artifacts), 'receipt_count': len(self.receipts),
                'native_qrh_build_executed': False, 'certificate_emitted': False}


def collect(args):
    collector = Collector(args.prepared, args.private_key, args.output, args.run_key, args.profile)
    try:
        progress('source_identity')
        critical = collector.profile['critical_artifacts']
        result = acquire.verify_git_snapshot(args.source_root, SUBJECT_COMMIT,
            [r['path'] for r in critical], expected_url='https://github.com/openai/math',
            expected_sha256={r['path']: r['sha256'] for r in critical})
        collector.observation('source_identity', {
            'schema_version': 'qrh003_source_identity_observation_v1',
            'expected_commit': SUBJECT_COMMIT, 'source_identity_status': result['status'],
            'collection_started_utc': collector.created, 'result': result})
        for item in critical:
            try:
                collector.add('upstream/' + item['path'], secure_read(args.source_root, item['path']), 'pinned_upstream_source')
            except AuditError as exc:
                # A missing source remains in the identity receipt and blocks;
                # no fabricated placeholder is inserted into the bundle.
                progress('source_unavailable', path=item['path'], reason_code=exc.code)
        progress('acquisition_inventory')
        acquired = acquire.collect_acquisition(args.source_root, args.dependency_root,
            lean_source_root=args.lean_source_root, effective_destination=args.effective_destination,
            fetch_missing=False)
        acquisition_bytes = canonical_bytes(acquired) + b'\n'
        collector.add('observations/acquisition_details.json', acquisition_bytes, 'source_acquisition_detail')
        collector.observation('dependency_inventory', acquired['dependencies'])
        progress('static_import_closure')
        closure = source_closure.resolve_static_source_closure(acquired['source_roots'],
            collector.profile['source_roots'], provider_universe_status=acquired['provider_universe_status'])
        closure['acquisition_details_path'] = 'observations/acquisition_details.json'
        closure['acquisition_details_sha256'] = sha256_bytes(acquisition_bytes)
        collector.observation('source_closure', closure)
        configs = collector.profile['configurations']
        collector.observation('scope_binding', {
            'schema_version': 'qrh003_scope_observation_v1',
            'configurations': configs,
            'claim_ids': [c['claim_id'] for c in configs],
            'theorem_exports': [n for c in configs for n in c['theorem_exports']],
            'mapping_basis': 'PINNED_CONFIG_BYTES_AND_SOURCE_ANCHORS_RECHECKED_BY_VERIFIER',
            'formal_theorem_identity': 'NOT_RUN', 'semantic_correspondence': 'NOT_REVIEWED'})
        progress('execution_preflight')
        preflight_dir = collector.output / 'preflight'
        command = ['--output', str(preflight_dir),
                   '--timeout-seconds', str(args.preflight_timeout)]
        if args.toolchain_root:
            command.extend(['--toolchain-root', str(args.toolchain_root)])
        if args.landrun:
            command.extend(['--landrun', str(args.landrun)])
        if args.landrun_sha256:
            command.extend(['--landrun-sha256', args.landrun_sha256])
        for name in ('comparator', 'lean4export'):
            path, digest = getattr(args, name), getattr(args, name + '_sha256')
            if path:
                command.extend(['--' + name, str(path)])
            if digest:
                command.extend(['--' + name + '-sha256', digest])
        process = collector.study_command('preflight', 'preflight', command,
                                          timeout=max(60, args.preflight_timeout * 10))
        collector.register_existing(preflight_dir)
        if (preflight_dir / 'preflight.json').is_file():
            preflight = read_json(preflight_dir / 'preflight.json')
        else:
            preflight = {'schema_version': 'qrh003_preflight_v1', 'overall_state': 'BLOCK',
                         'reason_codes': ['QRH003_PREFLIGHT_PROCESS_FAILED'], 'observations': []}
        preflight['collector_process'] = process
        preflight['source_artifact_path'] = 'preflight/preflight.json'
        preflight['raw_ref_base'] = 'preflight/'
        if process['timed_out'] or process['execution_error'] is not None or process['return_code'] not in (0, 2):
            preflight['overall_state'] = 'BLOCK'
            preflight.setdefault('reason_codes', []).append('QRH003_PREFLIGHT_PROCESS_FAILED')
        collector.observation('execution_preflight', preflight)
        progress('authority_boundary_tests')
        report_path = collector.output / 'test_execution.json'
        test_process = collector.study_command('boundary_tests', 'run_tests', [
            '--output', str(report_path)], timeout=args.test_timeout)
        if report_path.is_file():
            # register_existing is directory-oriented; add the produced file
            # without copying or overwriting its already complete bytes.
            data = secure_read(collector.output, 'test_execution.json')
            if 'test_execution.json' not in collector.artifact_names:
                collector.artifact_names.add('test_execution.json')
                collector.artifacts.append({'path': 'test_execution.json', 'sha256': sha256_bytes(data),
                    'bytes': len(data), 'role': 'raw_test_execution',
                    'evidence_class': 'actual_observation' if collector.anchor['trust_domain'] == 'PRODUCTION' else 'synthetic_fixture'})
            test_report = strict_loads(data)
        else:
            test_report = {'tests': [], 'return_code': test_process['return_code'], 'timed_out': test_process['timed_out']}
        test_report['collector_process'] = test_process
        if test_process['return_code'] != 0 or test_process['timed_out']:
            test_report['return_code'] = test_process['return_code']
            test_report['timed_out'] = test_process['timed_out']
        collector.observation('authority_boundary_tests', test_report)
    except Exception as exc:
        collector.observation('run_failure', {'schema_version': 'qrh003_failure_v1',
            'exception_type': type(exc).__name__, 'reason': str(exc),
            'traceback': traceback.format_exc(), 'native_qrh_build_executed': False})
        progress('collection_partial_failure', reason=str(exc))
    return collector.finish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--private-key', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-key', default='qrh003-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(4))
    parser.add_argument('--profile', choices=['technical', 'semantic'], default='technical')
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--dependency-root', type=Path, required=True)
    parser.add_argument('--lean-source-root', type=Path)
    parser.add_argument('--effective-destination', type=Path)
    parser.add_argument('--toolchain-root', type=Path)
    parser.add_argument('--landrun', type=Path)
    parser.add_argument('--landrun-sha256')
    parser.add_argument('--comparator', type=Path)
    parser.add_argument('--comparator-sha256')
    parser.add_argument('--lean4export', type=Path)
    parser.add_argument('--lean4export-sha256')
    parser.add_argument('--preflight-timeout', type=float, default=12)
    parser.add_argument('--test-timeout', type=float, default=180)
    args = parser.parse_args(argv)
    for source in (args.source_root, args.dependency_root, args.lean_source_root):
        if source and (source.absolute() == args.output.absolute() or source.absolute() in args.output.absolute().parents):
            parser.error('bundle output must be outside all source repositories')
    if args.effective_destination is not None:
        effective = args.effective_destination.absolute()
        for reserved in (args.output.absolute(), args.prepared.absolute(), args.private_key.absolute()):
            if effective == reserved or effective in reserved.parents or reserved in effective.parents:
                parser.error('effective sources must not overlap bundle, public anchor configuration, or private key paths')
    try:
        progress('completed', **collect(args))
        return 0
    except (AuditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
