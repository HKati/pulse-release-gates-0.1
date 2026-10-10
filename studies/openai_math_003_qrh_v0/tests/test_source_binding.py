"""Source/cache and subprocess regressions; synthetic TEST evidence only."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_authority as authority_fixtures
from tools import authority, collect, common, prepare

ROOT = Path(__file__).absolute().parents[1]


class SourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qrh-binding-TEST-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.root = self.home / 'study'
        runtime = common.source_runtime()
        # Copy only the already authenticated bytes, never an ambient cache.
        for name, raw in runtime.files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        (self.root / 'SOURCE_MANIFEST.json').write_bytes(runtime.manifest_raw)
        self.manifest_hash = runtime.manifest_sha256
        self.fixture = authority_fixtures.AuthorityBoundaryTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        for name in ('source_identity', 'scope_binding', 'authority_boundary_tests'):
            self.fixture.files['observations/' + name + '.json'] = common.canonical_bytes({
                'record_role': 'TEST_OBSERVER_FIXTURE_ONLY', 'tests': []})
        self.fixture.rebind()
        self.output = self.home / 'decision'

    def argv(self, command, arguments):
        return [sys.executable, '-I', str(self.root / 'source_bound.py'),
                '--root', str(self.root), '--source-manifest-sha256', self.manifest_hash,
                command, *map(str, arguments)]

    def invoke(self, command='authority', arguments=None, env=None):
        if arguments is None:
            arguments = ['decide', '--bundle', self.fixture.bundle,
                         '--anchor', self.fixture.anchor_path, '--output', self.output,
                         '--pulse-root', self.root / 'reference/pulse_runtime']
        return subprocess.run(self.argv(command, arguments), capture_output=True,
                              text=True, timeout=40, env=env, cwd=self.home)

    def blocked(self, result):
        self.assertEqual(result.returncode, 1, result.stderr)
        decision = common.read_json(self.output / 'decision.json')
        self.assertEqual(decision['trust_domain'], 'TEST')
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertEqual(decision['reason_codes'], ['QRH003_REQUIRED_GATES_NOT_PASSED'])
        self.assertTrue(decision['checker']['attempted'])
        self.assertEqual(decision['checker']['exit_code'], 1)
        self.assertFalse(list(self.output.rglob('certificate.json')))
        return decision

    def rejected(self, result, code):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(code, result.stderr)
        self.assertFalse(self.output.exists())

    def poison(self, name='tools/audit.py', mode='unchecked', payload=None):
        path = self.root / name
        raw = path.read_bytes()
        if payload is None:
            payload = '''
def evaluate(snapshot, anchor, profile_kind):
    if anchor['trust_domain'] != 'TEST':
        raise RuntimeError('SYNTHETIC_PAYLOAD_TEST_ONLY')
    return {'gates': {g: True for g in GATE_IDS},
            'evaluations': {g: {'state': 'VERIFIED', 'reason_codes': [],
                'evidence_refs': ['evidence/control.json']} for g in GATE_IDS},
            'states': {n: {'state': 'NOT_ASSESSED', 'reason_codes': [],
                'evidence_refs': []} for n in STATE_NAMES},
            'limitations': ['TEST BYTECODE INJECTION ONLY']}
'''
        code = compile(raw + payload.encode(), str(path), 'exec')
        if mode == 'timestamp':
            header = struct.pack('<III', 0, int(path.stat().st_mtime), len(raw))
        else:
            header = struct.pack('<I', 3 if mode == 'checked' else 1) + importlib.util.source_hash(raw)
        cache = Path(importlib.util.cache_from_source(str(path)))
        cache.parent.mkdir(exist_ok=True)
        cache.write_bytes(importlib.util.MAGIC_NUMBER + header + marshal.dumps(code))
        self.assertEqual(path.read_bytes(), raw)

    def runtime(self):
        live = common.source_runtime()
        return type(live)(self.root, live.manifest_raw, live.manifest_sha256)

    def collector(self):
        config = self.home / 'prepared'
        key = self.home / 'key'
        prepare.prepare(config, key, 'TEST')
        return collect.Collector(config, key, self.home / 'collected', 'source-binding-TEST', 'technical')

    def test_clean_decision_bytes_match_bound_API(self):
        self.blocked(self.invoke())
        expected = authority._compute(self.fixture.bundle, self.fixture.anchor_path,
                                      pulse_root=ROOT / 'reference/pulse_runtime')
        for filename, key in [('status.json', 'status_bytes'),
                              ('materialized_required.json', 'materialized_bytes'),
                              ('decision.json', 'decision_bytes')]:
            self.assertEqual((self.output / filename).read_bytes(), expected[key])

    def test_unchecked_hash_cache_cannot_promote_BLOCK(self):
        self.poison()
        self.blocked(self.invoke())

    def test_timestamp_cache_cannot_promote_BLOCK(self):
        self.poison(mode='timestamp')
        self.blocked(self.invoke())

    def test_checked_hash_cache_cannot_promote_BLOCK(self):
        self.poison(mode='checked')
        self.blocked(self.invoke())

    def test_entrypoint_and_common_caches_never_execute(self):
        for name in ('tools/authority.py', 'tools/verify.py', 'tools/common.py'):
            self.poison(name, payload='\nraise RuntimeError("POISON_EXECUTED")\n')
        self.blocked(self.invoke())

    def test_unlisted_package_initializer_never_executes(self):
        (self.root / 'tools/__init__.py').write_text('raise RuntimeError("PACKAGE_EXECUTED")\n')
        self.blocked(self.invoke())

    def test_prepare_binds_actual_source_and_leaves_native_capture_absent(self):
        self.poison('tools/prepare.py', payload='\nraise RuntimeError("PREPARE_CACHE")\n')
        for domain in ('TEST', 'PRODUCTION'):
            with self.subTest(domain=domain):
                config = self.home / domain
                p = self.invoke('prepare', ['--output', config, '--private-key', self.home / (domain + '.key'),
                                           '--trust-domain', domain])
                self.assertEqual(p.returncode, 0, p.stderr)
                anchor = common.read_json(config / 'anchor.json')
                self.assertEqual(anchor['source_binding'], common.source_runtime().contract())
                self.assertEqual(anchor['verifier_files'], dict(common.source_runtime().verifier_files))
                self.assertEqual(anchor['subject_commit'], common.SUBJECT_COMMIT)
                policy = common.read_json(config / 'capture_policy.json')
                self.assertEqual(policy['native_proof_capture_adapter'], 'NOT_IMPLEMENTED')
        self.assertFalse(list(self.home.rglob('certificate.json')))

    def test_replay_BLOCK_is_MATCH_and_observer_has_no_authority(self):
        self.poison()
        self.blocked(self.invoke())
        replay = self.home / 'replay'
        p = self.invoke('authority', ['replay', '--bundle', self.fixture.bundle,
            '--anchor', self.fixture.anchor_path, '--decision-dir', self.output,
            '--output', replay, '--pulse-root', self.root / 'reference/pulse_runtime'])
        self.assertEqual(p.returncode, 0, p.stderr)
        receipt = common.read_json(replay / 'replay_receipt.json')
        self.assertEqual((receipt['fresh_result'], receipt['replay_status']), ('BLOCK', 'MATCH'))
        report = self.home / 'transition.json'
        p = self.invoke('transition_report', ['--bundle', self.fixture.bundle,
            '--anchor', self.fixture.anchor_path, '--decision-dir', self.output,
            '--replay-dir', replay, '--output', report])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(common.read_json(report)['authority_effect'], 'NONE')

    def test_verify_uses_real_evaluator_despite_poisoned_cache(self):
        self.poison()
        p = self.invoke('verify', ['--bundle', self.fixture.bundle, '--anchor', self.fixture.anchor_path])
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(json.loads(p.stdout)['admission'], 'VERIFIED_INPUTS')
        self.assertFalse(all(json.loads(p.stdout)['gates'].values()))

    def test_missing_file_rejected_before_study_code(self):
        (self.root / 'tools/audit.py').unlink()
        self.rejected(self.invoke(), 'No such file')

    def test_modified_source_rejected_before_study_code(self):
        with (self.root / 'tools/audit.py').open('ab') as f:
            f.write(b'\nraise RuntimeError("MUST_NOT_EXECUTE")\n')
        self.rejected(self.invoke(), 'QRH_BIND_SOURCE_DIGEST_MISMATCH')

    def test_source_symlink_rejected(self):
        p = self.root / 'tools/audit.py'
        p.unlink()
        p.symlink_to(ROOT / 'tools/audit.py')
        self.rejected(self.invoke(), 'Too many levels')

    def test_parent_symlink_rejected(self):
        (self.root / 'tools').rename(self.root / 'real-tools')
        (self.root / 'tools').symlink_to('real-tools', target_is_directory=True)
        self.rejected(self.invoke(), 'Not a directory')

    def test_fifo_rejected_without_blocking(self):
        p = self.root / 'tools/audit.py'
        p.unlink()
        os.mkfifo(p)
        self.rejected(self.invoke(), 'QRH_BIND_FILE_TYPE_OR_SIZE')

    def test_wrong_manifest_pin_rejected(self):
        self.manifest_hash = '0' * 64
        self.rejected(self.invoke(), 'QRH_BIND_MANIFEST_DIGEST_MISMATCH')

    def test_modified_manifest_cannot_approve_modified_source(self):
        p = self.root / 'SOURCE_MANIFEST.json'
        m = json.loads(p.read_text())
        m['files'][0]['sha256'] = '0' * 64
        p.write_text(json.dumps(m))
        self.rejected(self.invoke(), 'QRH_BIND_MANIFEST_DIGEST_MISMATCH')

    def test_old_anchor_without_binding_blocks(self):
        del self.fixture.anchor['source_binding']
        self.fixture.write_anchor()
        p = self.invoke()
        self.assertEqual(p.returncode, 1)
        d = common.read_json(self.output / 'decision.json')
        self.assertEqual(d['result'], 'BLOCK')
        self.assertIn('QRH003_ANCHOR_INCOMPLETE', d['reason_codes'])

    def test_different_loaded_source_binding_blocks(self):
        self.fixture.anchor['source_binding']['source_manifest_sha256'] = '0' * 64
        self.fixture.write_anchor()
        p = self.invoke()
        self.assertEqual(p.returncode, 1)
        self.assertIn('QRH003_SOURCE_BINDING_ANCHOR_MISMATCH',
                      common.read_json(self.output / 'decision.json')['reason_codes'])

    def test_loaded_source_digest_checked_even_if_disk_check_is_bypassed_in_TEST(self):
        bad = copy.deepcopy(self.fixture.anchor)
        bad['verifier_files']['tools/audit.py'] = '0' * 64
        with mock.patch.object(common, 'secure_read', return_value=b'not the anchored code'):
            with self.assertRaisesRegex(common.AuditError, 'LOADED_SOURCE_ANCHOR_MISMATCH'):
                # Only the target record is bad; check it first for this control.
                bad['verifier_files'] = {'tools/audit.py': '0' * 64,
                    **{k: v for k, v in bad['verifier_files'].items() if k != 'tools/audit.py'}}
                common.verify_source_anchor(bad, ROOT)

    def test_direct_legacy_scripts_stop_before_poisoned_import(self):
        self.poison('tools/common.py', payload='\nraise RuntimeError("IMPORT_EXECUTED")\n')
        for name in ('prepare', 'collect', 'verify', 'authority', 'transition_report',
                     'preflight', 'run_tests', 'acquire', 'source_closure'):
            with self.subTest(command=name):
                p = subprocess.run([sys.executable, '-B', str(self.root / ('tools/' + name + '.py')), '--help'],
                                   capture_output=True, text=True, timeout=10)
                self.assertEqual(p.returncode, 2)
                self.assertIn('QRH003_SOURCE_BOUND_LAUNCH_REQUIRED', p.stderr)
                self.assertNotIn('IMPORT_EXECUTED', p.stderr)

    def test_nonisolated_launcher_rejected(self):
        (self.root / 'argparse.py').write_text('raise RuntimeError("EARLY_IMPORT_INJECTION")\n')
        args = self.argv('run_tests', ['--output', self.output])
        args.remove('-I')
        p = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.rejected(p, 'QRH_BIND_ISOLATED_PROCESS_REQUIRED')
        self.assertNotIn('EARLY_IMPORT_INJECTION', p.stderr)

    def test_PYTHONPATH_and_current_directory_do_not_inject_modules(self):
        (self.home / 'sitecustomize.py').write_text('raise RuntimeError("SITE_INJECTION")\n')
        (self.home / 'json.py').write_text('raise RuntimeError("JSON_INJECTION")\n')
        self.blocked(self.invoke(env=dict(os.environ, PYTHONPATH=str(self.home), PYTHONINSPECT='1')))

    def test_preloaded_study_module_context_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'PRELOADED_STUDY_MODULE'):
            self.runtime().install()

    def test_unanchored_namespace_import_has_no_filesystem_fallback(self):
        with self.assertRaisesRegex(RuntimeError, 'UNANCHORED_IMPORT'):
            self.runtime().find_spec('tools.unlisted')

    def test_post_capture_path_replacement_does_not_replace_code_object(self):
        runtime = self.runtime()
        original = runtime.code['tools.audit'][1]
        p = self.root / 'tools/audit.py'
        replacement = p.with_suffix('.new')
        replacement.write_text('raise RuntimeError("REPLACEMENT")\n')
        replacement.replace(p)
        self.assertIs(runtime.code['tools.audit'][1], original)
        namespace = {'__name__': 'tools.audit', '__package__': 'tools'}
        exec(original, namespace)
        self.assertTrue(callable(namespace['evaluate']))

    def test_post_capture_inplace_write_does_not_replace_code_object(self):
        runtime = self.runtime()
        (self.root / 'tools/audit.py').write_text('raise RuntimeError("OVERWRITE")\n')
        namespace = {'__name__': 'tools.audit', '__package__': 'tools'}
        exec(runtime.code['tools.audit'][1], namespace)
        self.assertTrue(callable(namespace['evaluate']))

    def test_tests_and_runner_caches_are_ignored(self):
        for name in ('tools/run_tests.py', 'tests/test_common.py'):
            self.poison(name, payload='\nraise RuntimeError("TEST_CACHE_EXECUTED")\n')
        report = self.home / 'tests.json'
        p = self.invoke('run_tests', ['--output', report, '--pattern', 'test_common.py'])
        self.assertEqual(p.returncode, 0, p.stderr)
        cases = common.read_json(report)['tests']
        self.assertTrue(cases)
        self.assertTrue(all(x['outcome'] == 'PASS' for x in cases))

    def test_unlisted_test_file_is_not_executed_or_counted(self):
        (self.root / 'tests/test_unlisted.py').write_text('raise RuntimeError("UNLISTED_TEST_EXECUTED")\n')
        p = self.invoke('run_tests', ['--output', self.output, '--pattern', 'test_unlisted.py'])
        self.rejected(p, 'QRH003_TEST_PATTERN_MATCHED_NO_ANCHORED_TESTS')

    def test_collector_boundary_subprocess_uses_sealed_source_binding(self):
        for name in ('tools/run_tests.py', 'tests/test_common.py'):
            self.poison(name, payload='\nraise RuntimeError("CHILD_CACHE_EXECUTED")\n')
        runtime, collector = self.runtime(), self.collector()
        report = collector.output / 'child-tests.json'
        with mock.patch.object(collect, 'source_runtime', return_value=runtime):
            r = collector.study_command('boundary-control', 'run_tests',
                ['--output', report, '--pattern', 'test_common.py'], 30)
        self.assertEqual(r['return_code'], 0)
        self.assertEqual(r['source_binding'], runtime.contract())
        self.assertIn('/proc/self/fd/', r['argv'][2])
        self.assertTrue(all(t['outcome'] == 'PASS' for t in common.read_json(report)['tests']))

    def test_collector_preflight_subprocess_ignores_poisoned_cache(self):
        self.poison('tools/preflight.py', payload='\nraise RuntimeError("PREFLIGHT_CACHE_EXECUTED")\n')
        runtime, collector = self.runtime(), self.collector()
        out = collector.output / 'preflight-control'
        with mock.patch.object(collect, 'source_runtime', return_value=runtime):
            r = collector.study_command('preflight-control', 'preflight',
                                        ['--output', out, '--timeout-seconds', '0.1'], 30)
        self.assertEqual(r['return_code'], 2)  # Missing qualified native tools => BLOCK.
        record = common.read_json(out / 'preflight.json')
        self.assertEqual(record['overall_state'], 'BLOCK')
        self.assertEqual(r['source_binding'], runtime.contract())
        self.assertNotIn('PREFLIGHT_CACHE_EXECUTED', (collector.output / r['stderr_path']).read_text())

    def test_child_source_mutation_is_captured_as_failure(self):
        runtime, collector = self.runtime(), self.collector()
        (self.root / 'tools/preflight.py').write_text('raise RuntimeError("UNTRUSTED_CHILD")\n')
        with mock.patch.object(collect, 'source_runtime', return_value=runtime):
            r = collector.study_command('failed-child', 'preflight',
                                        ['--output', self.home / 'no-output'], 10)
        self.assertEqual(r['return_code'], 2)
        self.assertFalse((self.home / 'no-output').exists())
        self.assertIn('SOURCE_DIGEST_MISMATCH', (collector.output / r['stderr_path']).read_text())

    def test_child_launcher_and_manifest_are_sealed_and_FDs_close(self):
        runtime = self.runtime()
        with runtime.child('preflight', ['--help']) as (argv, descriptors):
            self.assertEqual(os.pread(descriptors[0], 1000000, 0), runtime.files['source_bound.py'])
            self.assertEqual(os.pread(descriptors[1], 1000000, 0), runtime.manifest_raw)
            for fd in descriptors:
                with self.assertRaises(OSError):
                    os.pwrite(fd, b'X', 0)
        for fd in descriptors:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_child_has_no_mutable_launcher_fallback(self):
        runtime, collector = self.runtime(), self.collector()
        (self.root / 'source_bound.py').write_text('raise RuntimeError("MUTABLE_LAUNCHER_EXECUTED")\n')
        with mock.patch.object(collect, 'source_runtime', return_value=runtime):
            r = collector.study_command('launcher-replaced', 'preflight', ['--help'], 10)
        self.assertEqual(r['return_code'], 2)
        stderr = (collector.output / r['stderr_path']).read_text()
        self.assertIn('SOURCE_DIGEST_MISMATCH:source_bound.py', stderr)
        self.assertNotIn('MUTABLE_LAUNCHER_EXECUTED', stderr)

    def test_unsupported_child_command_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'CHILD_COMMAND_UNSUPPORTED'):
            with self.runtime().child('authority', []):
                self.fail('must not launch')

    def test_collector_refuses_anchor_without_current_binding(self):
        config, key = self.home / 'config', self.home / 'key'
        prepare.prepare(config, key, 'TEST')
        a = common.read_json(config / 'anchor.json')
        del a['source_binding']
        (config / 'anchor.json').write_bytes(common.canonical_bytes(a))
        with self.assertRaisesRegex(common.AuditError, 'SOURCE_BINDING_ANCHOR_MISMATCH'):
            collect.Collector(config, key, self.home / 'never', 'TEST', 'technical')
        self.assertFalse((self.home / 'never').exists())
