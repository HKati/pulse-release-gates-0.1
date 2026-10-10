import importlib.util
import argparse
import errno
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from tools import preflight as pf


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


class PreflightPinnedExecutionTests(unittest.TestCase):
    """Harmless local fixtures exercise byte binding, not native QRH isolation."""

    def tool(self, root, text='#!/bin/sh\necho 4.34.1\n'):
        path = root / 'candidate'
        path.write_text(text)
        path.chmod(0o755)
        return path

    def replace_tool(self, path, marker, method):
        changed = '#!/bin/sh\necho unpinned > "' + str(marker) + '"\necho 4.34.1\n'
        if method == 'atomic':
            replacement = path.with_name('replacement')
            replacement.write_text(changed)
            replacement.chmod(0o755)
            os.replace(replacement, path)
        else:
            path.write_text(changed)

    def assert_fd_closed(self, descriptor):
        with self.assertRaises(OSError) as error:
            os.fstat(descriptor)
        self.assertEqual(error.exception.errno, errno.EBADF)

    def landrun_args(self, path, digest):
        args = argparse.Namespace(preflight_timeout=12)
        for name in ('lean', 'lake', 'landrun', 'comparator', 'lean4export'):
            setattr(args, name, str(path) if name == 'landrun' else None)
            setattr(args, name + '_sha256', digest if name == 'landrun' else None)
        return args

    def landrun_fixture(self, root):
        return self.tool(root, '#!/bin/sh\nif [ "$1" = "--version" ]; then\n'
            '  echo "landrun version TEST-fixture"\nelse\n'
            '  echo "PINNED_STRICT_FIXTURE"\nfi\n')

    def test_pinned_version_executes_sealed_bytes_after_source_mutation(self):
        for method in ('atomic', 'in_place'):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                tool = self.tool(root)
                digest = pf.sha256(tool)
                marker = root / 'UNPINNED_EXECUTED'
                recorder = pf.Recorder(root / 'result')
                actual_command, descriptors = recorder.command, []
                def mutate_then_run(*args, **kwargs):
                    descriptors.extend(kwargs['pass_fds'])
                    self.replace_tool(tool, marker, method)
                    return actual_command(*args, **kwargs)
                with mock.patch.object(recorder, 'command', side_effect=mutate_then_run):
                    result = pf.probe_tool('lean', str(tool), digest, recorder, r'4\.34\.1')
                self.assertEqual(result['state'], 'PASS')
                self.assertFalse(marker.exists())
                self.assertNotEqual(pf.sha256(tool), digest)
                execution = result['details']['execution']
                self.assertEqual(execution['executable_binding']['sha256'], digest)
                self.assertTrue(execution['argv'][0].startswith('/proc/self/fd/'))
                self.assertEqual(len(descriptors), 1)
                self.assert_fd_closed(descriptors[0])

    def test_snapshot_seals_prevent_write_growth_and_shrink(self):
        with tempfile.TemporaryDirectory() as folder:
            tool = self.tool(Path(folder))
            digest = pf.sha256(tool)
            with pf.executable_snapshot(tool) as snapshot:
                descriptor = snapshot['fd']
                self.assertEqual(snapshot['sha256'], digest)
                self.assertEqual(pf.fcntl.fcntl(descriptor, pf.F_GET_SEALS) & pf.EXECUTABLE_SEALS,
                                 pf.EXECUTABLE_SEALS)
                for operation in (lambda: os.pwrite(descriptor, b'x', 0),
                                  lambda: os.ftruncate(descriptor, 0),
                                  lambda: os.ftruncate(descriptor, snapshot['bytes'] + 1)):
                    with self.subTest(operation=operation), self.assertRaises(OSError) as error:
                        operation()
                    self.assertEqual(error.exception.errno, errno.EPERM)
                self.assertEqual(pf.sha256(snapshot['path']), digest)
            self.assert_fd_closed(descriptor)

    def test_source_mutation_during_copy_cannot_reuse_original_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = self.tool(root, '#!/bin/sh\necho 4.34.1\n# A\n')
            digest = pf.sha256(tool)
            source_identity = (tool.stat().st_dev, tool.stat().st_ino)
            recorder = pf.Recorder(root / 'result')
            actual_read, changed = os.read, []
            def mutate_source_before_read(descriptor, count):
                current = os.fstat(descriptor)
                if not changed and (current.st_dev, current.st_ino) == source_identity:
                    tool.write_text('#!/bin/sh\necho 4.34.1\n# B\n')
                    changed.append(True)
                return actual_read(descriptor, count)
            with mock.patch.object(pf.os, 'read', side_effect=mutate_source_before_read), \
                    mock.patch.object(recorder, 'command') as launch:
                result = pf.probe_tool('lean', str(tool), digest, recorder, r'4\.34\.1')
            self.assertTrue(changed)
            self.assertEqual(result['reason_code'], 'TOOL_DIGEST_MISMATCH_LEAN')
            launch.assert_not_called()

    def test_snapshot_creation_and_sealing_failures_never_fall_back_to_path(self):
        for failure in ('create', 'add_seals', 'missing_seals'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                tool = self.tool(root)
                digest = pf.sha256(tool)
                recorder = pf.Recorder(root / 'result')
                actual_create, actual_fcntl, descriptors = os.memfd_create, pf.fcntl.fcntl, []
                def create(*args, **kwargs):
                    if failure == 'create':
                        raise OSError(errno.ENOSYS, 'TEST unavailable memfd')
                    descriptor = actual_create(*args, **kwargs)
                    descriptors.append(descriptor)
                    return descriptor
                def control(descriptor, command, *args):
                    if failure == 'add_seals' and command == pf.F_ADD_SEALS:
                        raise OSError(errno.EPERM, 'TEST seal refusal')
                    if failure == 'missing_seals' and command == pf.F_GET_SEALS:
                        return 0
                    return actual_fcntl(descriptor, command, *args)
                with mock.patch.object(pf.os, 'memfd_create', side_effect=create), \
                        mock.patch.object(pf.fcntl, 'fcntl', side_effect=control), \
                        mock.patch.object(recorder, 'command') as launch:
                    result = pf.probe_tool('lean', str(tool), digest, recorder, r'4\.34\.1')
                self.assertEqual(result['reason_code'], 'TOOL_SNAPSHOT_UNAVAILABLE_LEAN')
                self.assertEqual(result['details']['execution'], 'NOT_RUN')
                launch.assert_not_called()
                for descriptor in descriptors:
                    self.assert_fd_closed(descriptor)

    def test_missing_unpinned_and_nonexecutable_tools_are_not_launched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = self.tool(root)
            digest = pf.sha256(tool)
            for case, path, pin, expected in (
                    ('missing', None, digest, 'TOOL_UNAVAILABLE_LEAN'),
                    ('unpinned', str(tool), None, 'TOOL_DIGEST_UNPINNED_LEAN'),
                    ('not_executable', str(tool), digest, 'TOOL_NOT_EXECUTABLE_LEAN')):
                with self.subTest(case=case):
                    if case == 'not_executable':
                        tool.chmod(0o644)
                    recorder = pf.Recorder(root / case)
                    with mock.patch.object(recorder, 'command') as launch:
                        result = pf.probe_tool('lean', path, pin, recorder, r'4\.34\.1')
                    self.assertEqual(result['reason_code'], expected)
                    launch.assert_not_called()

    def test_version_timeout_preserves_output_and_closes_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = self.tool(root, '#!' + sys.executable + '\n'
                'import time\nprint("4.34.1", flush=True)\ntime.sleep(2)\n')
            recorder = pf.Recorder(root / 'result', timeout_seconds=0.1)
            actual_command, descriptors = recorder.command, []
            def capture_fd(*args, **kwargs):
                descriptors.extend(kwargs['pass_fds'])
                return actual_command(*args, **kwargs)
            with mock.patch.object(recorder, 'command', side_effect=capture_fd):
                result = pf.probe_tool('lean', str(tool), pf.sha256(tool), recorder, r'4\.34\.1')
            self.assertEqual(result['state'], 'FAIL')
            self.assertEqual(result['details']['execution']['state'], 'TIMEOUT')
            self.assertIn('4.34.1', result['details']['version_stdout'])
            self.assert_fd_closed(descriptors[0])

    def test_strict_landrun_rechecks_pin_after_version_path_mutation(self):
        for method in ('atomic', 'in_place'):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                tool = self.landrun_fixture(root)
                args = self.landrun_args(tool, pf.sha256(tool))
                marker = root / 'UNPINNED_EXECUTED'
                actual_probe = pf.probe_tool
                def mutate_after_version(*call_args, **kwargs):
                    result = actual_probe(*call_args, **kwargs)
                    if call_args[0] == 'landrun' and not kwargs.get('command_name'):
                        self.assertEqual(result['state'], 'PASS')
                        self.replace_tool(tool, marker, method)
                    return result
                with mock.patch.object(pf, 'probe_tool', side_effect=mutate_after_version):
                    observations = pf.collect(args, pf.Recorder(root / 'result'))
                strict = next(item for item in observations if item['id'] == 'landrun_strict_execution')
                self.assertEqual(strict['state'], 'FAIL')
                self.assertEqual(strict['details']['tool_reason_code'], 'TOOL_DIGEST_MISMATCH_LANDRUN')
                self.assertEqual(strict['details']['record'], 'NOT_RUN')
                self.assertFalse(marker.exists())

    def test_strict_landrun_executes_only_its_verified_snapshot(self):
        for method in ('atomic', 'in_place'):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                tool = self.landrun_fixture(root)
                digest = pf.sha256(tool)
                args = self.landrun_args(tool, digest)
                marker = root / 'UNPINNED_EXECUTED'
                recorder = pf.Recorder(root / 'result')
                actual_command, descriptors = recorder.command, []
                def mutate_before_strict(name, *call_args, **kwargs):
                    descriptors.extend(kwargs['pass_fds'])
                    if name == 'landrun_strict_true':
                        self.replace_tool(tool, marker, method)
                    return actual_command(name, *call_args, **kwargs)
                with mock.patch.object(recorder, 'command', side_effect=mutate_before_strict):
                    observations = pf.collect(args, recorder)
                strict = next(item for item in observations if item['id'] == 'landrun_strict_execution')
                self.assertEqual(strict['state'], 'PASS')
                self.assertIn('PINNED_STRICT_FIXTURE', strict['details']['stdout'])
                self.assertEqual(strict['details']['record']['executable_binding']['sha256'], digest)
                self.assertFalse(marker.exists())
                self.assertEqual(len(descriptors), 2)
                for descriptor in descriptors:
                    self.assert_fd_closed(descriptor)

    def test_memfd_execution_refusal_is_blocking_without_path_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = self.tool(root)
            recorder = pf.Recorder(root / 'result')
            with mock.patch.object(pf.subprocess, 'run', side_effect=PermissionError('TEST memfd execution denied')) as launch:
                result = pf.probe_tool('lean', str(tool), pf.sha256(tool), recorder, r'4\.34\.1')
            self.assertEqual(result['state'], 'FAIL')
            self.assertEqual(result['details']['execution']['state'], 'EXECUTION_ERROR')
            self.assertEqual(launch.call_count, 1)
            self.assertTrue(launch.call_args.args[0][0].startswith('/proc/self/fd/'))
            self.assert_fd_closed(launch.call_args.kwargs['pass_fds'][0])

    def test_nonregular_swap_is_rejected_without_blocking_open(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fifo = root / 'candidate'
            os.mkfifo(fifo)
            recorder = pf.Recorder(root / 'result')
            # Model a regular-file check followed by a FIFO at the same path.
            with mock.patch.object(pf.Path, 'is_file', return_value=True), \
                    mock.patch.object(recorder, 'command') as launch:
                result = pf.probe_tool('lean', str(fifo), '0' * 64, recorder, r'4\.34\.1')
            self.assertEqual(result['reason_code'], 'TOOL_SNAPSHOT_UNAVAILABLE_LEAN')
            launch.assert_not_called()

    def test_oversized_tool_is_rejected_before_snapshot_allocation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = root / 'oversized'
            with tool.open('wb') as stream:
                stream.truncate(pf.MAX_TOOL_SNAPSHOT_BYTES + 1)
            tool.chmod(0o755)
            recorder = pf.Recorder(root / 'result')
            with mock.patch.object(pf.os, 'memfd_create') as allocate, \
                    mock.patch.object(recorder, 'command') as launch:
                result = pf.probe_tool('lean', str(tool), '0' * 64, recorder, r'4\.34\.1')
            self.assertEqual(result['reason_code'], 'TOOL_SNAPSHOT_UNAVAILABLE_LEAN')
            self.assertIn('snapshot byte limit', result['details']['snapshot_error'])
            allocate.assert_not_called()
            launch.assert_not_called()

    def test_presence_only_probe_does_not_execute_the_verified_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = self.tool(root)
            recorder = pf.Recorder(root / 'result')
            with mock.patch.object(recorder, 'command') as launch:
                result = pf.probe_tool('comparator', str(tool), pf.sha256(tool), recorder)
            self.assertEqual(result['state'], 'PASS')
            self.assertEqual(result['details']['execution'], 'NOT_RUN')
            launch.assert_not_called()

    def test_harmless_elf_executes_through_the_sealed_descriptor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = Path(shutil.which('true')).read_bytes()
            self.assertEqual(original[:4], b'\x7fELF')
            tool = root / 'elf-fixture'
            tool.write_bytes(original)
            tool.chmod(0o755)
            recorder = pf.Recorder(root / 'result')
            result = pf.probe_tool('true_fixture', str(tool), pf.sha256(tool), recorder,
                                   command_args=[], command_name='elf_fixture')
            self.assertEqual(result['state'], 'PASS')
            self.assertEqual(result['details']['execution']['exit_code'], 0)
            self.assertEqual(result['details']['execution']['executable_binding']['method'], 'LINUX_SEALED_MEMFD')


if __name__ == '__main__':
    unittest.main()
