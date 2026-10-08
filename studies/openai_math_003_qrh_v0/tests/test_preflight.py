import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'preflight.py'
spec = importlib.util.spec_from_file_location('qrh_preflight', SCRIPT)
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)


class PreflightFailClosedTests(unittest.TestCase):
    def test_missing_observations_are_blocking(self):
        state, reasons = pf.result_state([])
        self.assertEqual(state, 'BLOCK')
        self.assertEqual(len(reasons), len(pf.REQUIRED))

    def test_root_or_unavailable_landlock_cannot_be_overridden_by_tool_presence(self):
        observations = [{'id': name, 'state': 'PASS'} for name in pf.REQUIRED]
        for name in ('unprivileged_uid', 'landlock_abi'):
            changed = [dict(item, state='FAIL', reason_code='DENIED') if item['id'] == name else item for item in observations]
            self.assertEqual(pf.result_state(changed), ('BLOCK', ['DENIED']))

    def test_unknown_state_is_not_a_pass(self):
        observations = [{'id': name, 'state': 'PASS'} for name in pf.REQUIRED]
        observations[0]['state'] = 'RECORDED'
        self.assertEqual(pf.result_state(observations)[0], 'BLOCK')

    def test_digest_mismatch_prevents_executable_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'MUST_NOT_EXIST'
            executable = root / 'candidate'
            executable.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\necho 4.34.1\n')
            executable.chmod(0o755)
            result = pf.probe_tool('lean', str(executable), '0' * 64, pf.Recorder(root / 'result'), r'4\.34\.1')
            self.assertEqual(result['reason_code'], 'TOOL_DIGEST_MISMATCH_LEAN')
            self.assertFalse(marker.exists())

    def test_nonzero_version_exit_is_preserved_and_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root / 'candidate'
            executable.write_text('#!/bin/sh\necho "4.34.1"\necho "failed to locate application" >&2\nexit 1\n')
            executable.chmod(0o755)
            recorder = pf.Recorder(root / 'result')
            result = pf.probe_tool('lean', str(executable), pf.sha256(executable), recorder, r'4\.34\.1')
            self.assertEqual(result['state'], 'FAIL')
            self.assertEqual(result['details']['execution']['exit_code'], 1)
            self.assertIn('failed to locate application', result['details']['version_stderr'])
            self.assertEqual(len(recorder.raw_refs), 3)

    def test_timeout_keeps_partial_stdout(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder = pf.Recorder(Path(folder) / 'result')
            record, out, _ = recorder.command('timeout', [sys.executable, '-c', 'import time; print("before", flush=True); time.sleep(1)'], timeout=0.05)
            self.assertEqual(record['state'], 'TIMEOUT')
            self.assertIsNone(record['exit_code'])
            self.assertIn('before', out)

    def test_existing_evidence_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                pf.Recorder(folder)


if __name__ == '__main__':
    unittest.main()
