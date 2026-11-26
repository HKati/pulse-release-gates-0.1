"""Repository Q3 preservation regressions. No acquisition, inference or network.

The 28 historical review tests are ported unchanged apart from fixture loading.
A successful test run preserves (does not remove) the historical handoff block.
"""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / 'tools/check_q3_preflight_preservation_v0.py'
SPEC = importlib.util.spec_from_file_location('q3_repository_preservation', TOOL)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ARCHIVE = REPO_ROOT / M.PACKAGE_RELATIVE_PATH

class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        context = M.preserved_package(ARCHIVE)
        cls.root = context.__enter__()
        cls.addClassCleanup(context.__exit__, None, None, None)
        cls.log = (cls.root / 'evidence/workflow_job_121350855532.log').read_bytes()
        cls.prior = M.zip_members((cls.root / 'prior_review/Q3_TOKEN_PREFLIGHT_POSTFLIGHT_40253690074.zip').read_bytes())
        cls.snapshot = M.strict_json(cls.prior['reviewed_source_snapshot.json'])
        cls.delta = M.strict_json((cls.root / 'source/source_delta.json').read_bytes())
        cls.current_workflow = (cls.root / 'source/current_q3_reference_acquisition_v0.yml').read_bytes()

    def log_reject(self, old, new, code):
        self.assertIn(old, self.log)
        with self.assertRaisesRegex(M.ReviewError, code):
            M.inspect_log(self.log.replace(old, new))

    def test_preserved_package_replay_is_blocked_not_promoted(self):
        result = M.verify(self.root, check_manifest=False)
        self.assertEqual(result['source_bound_carrier_check'], 'PASS')
        self.assertEqual(result['source_paths_compared'], 21)
        self.assertEqual(result['prompt_tokens']['total'], 144752)
        self.assertEqual(result['runner_image_review']['review_disposition'],
                         'REJECT_AND_REQUIRE_NEW_TOKEN_PREFLIGHT')
        self.assertFalse(result['runner_image_review']['capture_handoff_approved'])
        self.assertFalse(result['this_review_tokenizer_executed'])

    def test_matching_images_do_not_authorize_capture(self):
        row = M.compare_images('20261023.334.3', '20261023.334.3')
        self.assertTrue(row['match'])
        self.assertFalse(row['capture_handoff_approved'])
        self.assertFalse(row['new_execution_authorized'])
        self.assertEqual(row['authority_effect'], 'none')

    def test_missing_image_fails_closed(self):
        for value in ('', None, 0, True, 'bad image'):
            with self.subTest(value=value), self.assertRaises(M.ReviewError):
                M.compare_images(value, '20261023.334.3')

    def test_original_log_startup_image_is_selected(self):
        self.assertEqual(M.inspect_log(self.log), '20261012.334.1')

    def test_runner_provisioner_version_is_not_image_version(self):
        changed = self.log.replace(b'Version: 20261021.618', b'Version: unrelated-provisioner')
        self.assertEqual(M.inspect_log(changed), '20261012.334.1')

    def test_missing_image_group_rejected(self):
        self.log_reject(b'##[group]Runner Image\n', b'##[group]Not Runner Image\n', 'LOG_IMAGE_GROUP')

    def test_duplicate_image_group_rejected(self):
        with self.assertRaisesRegex(M.ReviewError, 'LOG_IMAGE_GROUP'):
            M.inspect_log(self.log + b'\n##[group]Runner Image\nVersion: wrong\n##[endgroup]')

    def test_ambiguous_image_version_rejected(self):
        self.log_reject(b'Version: 20261012.334.1', b'Version: 20261012.334.1 Version: other', 'LOG_IMAGE_VERSION')

    def test_wrong_image_os_rejected(self):
        self.log_reject(b'Image: ubuntu-24.04', b'Image: windows-2025', 'LOG_IMAGE_OS')

    def test_wrong_job_rejected(self):
        self.log_reject(b'Complete job name: acquire', b'Complete job name: verify', 'LOG_JOB')

    def test_wrong_source_commit_rejected(self):
        self.log_reject(('EXPECTED_SOURCE_SHA: ' + M.OLD).encode(),
                        ('EXPECTED_SOURCE_SHA: ' + '0'*40).encode(), 'LOG_SOURCE')

    def test_wrong_upload_digest_rejected(self):
        self.log_reject(('SHA256 digest of uploaded artifact is ' + M.OUTER).encode(),
                        ('SHA256 digest of uploaded artifact is ' + '0'*64).encode(), 'LOG_ARTIFACT_DIGEST')

    def test_wrong_artifact_id_rejected(self):
        self.log_reject(b'successfully finalized. Artifact ID 12621038763',
                        b'successfully finalized. Artifact ID 123456789', 'LOG_ARTIFACT_IDENTITY')

    def test_wrong_run_artifact_name_rejected(self):
        self.log_reject(b'Artifact q3-reference-capture-40253690074-1 successfully finalized.',
                        b'Artifact q3-reference-capture-40253690075-1 successfully finalized.', 'LOG_ARTIFACT_IDENTITY')

    def test_wrong_attempt_artifact_name_rejected(self):
        self.log_reject(b'Artifact q3-reference-capture-40253690074-1 successfully finalized.',
                        b'Artifact q3-reference-capture-40253690074-2 successfully finalized.', 'LOG_ARTIFACT_IDENTITY')

    def test_wrong_uploaded_size_rejected(self):
        self.log_reject(b'Uploaded bytes 5897022', b'Uploaded bytes 5897023', 'LOG_ARTIFACT_SIZE')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(M.ReviewError, 'DUPLICATE_JSON_KEY'):
            M.strict_json(b'{"ok":false,"ok":true}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(M.ReviewError, 'NONFINITE_JSON'):
            M.strict_json(b'{"v":NaN}')

    def test_zip_traversal_rejected(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as z:
            z.writestr('../bad', b'x')
        with self.assertRaisesRegex(M.ReviewError, 'ZIP_PATH'):
            M.zip_members(raw.getvalue())

    def test_duplicate_zip_member_rejected(self):
        raw = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(raw, 'w') as z:
                z.writestr('same', b'x'); z.writestr('same', b'y')
        with self.assertRaisesRegex(M.ReviewError, 'ZIP_DUPLICATE'):
            M.zip_members(raw.getvalue())

    def test_zip_symlink_rejected(self):
        raw = io.BytesIO(); entry = zipfile.ZipInfo('link')
        entry.create_system = 3; entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(raw, 'w') as z:
            z.writestr(entry, b'elsewhere')
        with self.assertRaisesRegex(M.ReviewError, 'ZIP_TYPE'):
            M.zip_members(raw.getvalue())

    def test_historical_source_mutation_rejected(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['files'][M.WORKFLOW]['content'] += '# changed\n'
        with self.assertRaisesRegex(M.ReviewError, 'HISTORICAL_BLOB'):
            M.verify_sources(snapshot, self.delta, self.current_workflow)

    def test_current_workflow_mutation_rejected(self):
        with self.assertRaisesRegex(M.ReviewError, 'DELTA_CURRENT_BINDING'):
            M.verify_sources(self.snapshot, self.delta, self.current_workflow + b'# changed\n')

    def test_missing_source_path_rejected(self):
        delta = copy.deepcopy(self.delta); delta['rows'].pop()
        with self.assertRaisesRegex(M.ReviewError, 'SOURCE_CLOSURE'):
            M.verify_sources(self.snapshot, delta, self.current_workflow)

    def test_false_source_equality_rejected(self):
        delta = copy.deepcopy(self.delta); delta['rows'][0]['byte_identity_by_git_blob'] = True
        with self.assertRaisesRegex(M.ReviewError, 'DELTA_EQUALITY'):
            M.verify_sources(self.snapshot, delta, self.current_workflow)

    def test_changed_comparison_commit_rejected(self):
        delta = copy.deepcopy(self.delta); delta['reviewed_main_commit'] = '0' * 40
        with self.assertRaisesRegex(M.ReviewError, 'SOURCE_COMMITS'):
            M.verify_sources(self.snapshot, delta, self.current_workflow)

    def test_manifest_detects_missing_extra_and_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'a').write_bytes(b'a')
            (root/'SHA256SUMS.txt').write_text(M.digest(b'a')+'  a\n')
            M.verify_file_manifest(root)
            (root/'a').write_bytes(b'changed')
            with self.assertRaisesRegex(M.ReviewError, 'PACKAGE_MANIFEST'):
                M.verify_file_manifest(root)
            (root/'a').unlink()
            with self.assertRaisesRegex(M.ReviewError, 'PACKAGE_MANIFEST'):
                M.verify_file_manifest(root)
            (root/'a').write_bytes(b'a'); (root/'extra').write_bytes(b'x')
            with self.assertRaisesRegex(M.ReviewError, 'PACKAGE_MANIFEST'):
                M.verify_file_manifest(root)

    def test_nested_manifest_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'nested').mkdir()
            (root/'SHA256SUMS.txt').write_text('')
            (root/'nested/SHA256SUMS.txt').write_text('unlisted')
            with self.assertRaisesRegex(M.ReviewError, 'PACKAGE_MANIFEST'):
                M.verify_file_manifest(root)


class RepositoryIntegrationTests(unittest.TestCase):
    def test_new_module_registered_once_in_both_ci_manifests(self):
        relative = Path(__file__).relative_to(REPO_ROOT).as_posix()
        for name in ('ci/tools-tests.list', 'ci/pytest-tests.list'):
            entries = [line.split('#', 1)[0].strip()
                       for line in (REPO_ROOT / name).read_text().splitlines()]
            entries = [line for line in entries if line]
            self.assertEqual(len(entries), len(set(entries)))
            self.assertEqual(entries.count(relative), 1)

    def test_exact_archive_and_committed_checksum(self):
        raw = M.read_selected_archive(ARCHIVE)
        self.assertEqual(len(raw), M.PACKAGE_SIZE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), M.PACKAGE_SHA256)
        self.assertEqual((ARCHIVE.parent / 'SHA256SUMS.txt').read_text(),
                         M.PACKAGE_SHA256 + '  ' + ARCHIVE.name + '\n')

    def test_cli_returns_expected_historical_block_not_integrity_error(self):
        before = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run([sys.executable, '-I', '-B', str(TOOL)], cwd=cwd,
                                  capture_output=True, text=True, timeout=45)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stderr, '')
        result = json.loads(proc.stdout)
        self.assertEqual(result['source_bound_carrier_check'], 'PASS')
        self.assertEqual(result['runner_image_review']['reconciliation'], 'UNRESOLVED_MISMATCH')
        self.assertFalse(result['runner_image_review']['capture_handoff_approved'])
        self.assertFalse(result['runner_image_review']['new_execution_authorized'])
        self.assertEqual(result['authority_effect'], 'none')
        self.assertEqual(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), before)

    def test_altered_archive_rejected_before_zip_parse(self):
        raw = bytearray(ARCHIVE.read_bytes()); raw[-1] ^= 1
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'altered.zip'; path.write_bytes(raw)
            with mock.patch.object(M, 'zip_members', side_effect=AssertionError('must not parse')):
                with self.assertRaisesRegex(M.ReviewError, 'PRESERVATION_IDENTITY'):
                    M.verify_archive(path)

    def test_short_and_long_archives_rejected(self):
        raw = ARCHIVE.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'wrong-size.zip'
            for data in (raw[:-1], raw + b'x'):
                path.write_bytes(data)
                with self.assertRaisesRegex(M.ReviewError, 'PRESERVATION_SIZE'):
                    M.read_selected_archive(path)

    def test_missing_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(OSError):
                M.read_selected_archive(Path(folder) / 'missing.zip')

    def test_archive_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'linked.zip'
            path.symlink_to(ARCHIVE)
            with self.assertRaisesRegex(M.ReviewError, 'PRESERVATION_SYMLINK'):
                M.read_selected_archive(path)

    def test_symlink_parent_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'linked'
            path.symlink_to(ARCHIVE.parent, target_is_directory=True)
            with self.assertRaisesRegex(M.ReviewError, 'PRESERVATION_SYMLINK'):
                M.read_selected_archive(path / ARCHIVE.name)

    def test_temporary_tree_removed_after_success_and_exception(self):
        with M.preserved_package(ARCHIVE) as root:
            self.assertTrue(root.is_dir())
        self.assertFalse(root.exists())
        with self.assertRaisesRegex(RuntimeError, 'controlled'):
            with M.preserved_package(ARCHIVE) as failed_root:
                raise RuntimeError('controlled')
        self.assertFalse(failed_root.exists())

    def test_cli_error_never_claims_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = subprocess.run([sys.executable, '-I', '-B', str(TOOL),
                                   '--archive', str(Path(folder) / 'missing.zip')],
                                  capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, '')
        result = json.loads(proc.stderr)
        self.assertFalse(result['capture_handoff_approved'])
        self.assertFalse(result['new_execution_authorized'])
        self.assertEqual(result['authority_effect'], 'none')


if __name__ == '__main__':
    unittest.main()
