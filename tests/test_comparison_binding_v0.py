"""CI entrypoint for the isolated synthetic comparison-binding companion."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPANION = ROOT / 'examples' / 'comparison_binding_v0'


class ComparisonBindingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = tempfile.TemporaryDirectory(prefix='pulsemech-comparison-binding-')
        cls.addClassCleanup(cls.output.cleanup)
        completed = subprocess.run(
            [sys.executable, '-B', str(COMPANION / 'run_review.py'), '--output-dir', cls.output.name],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)
        cls.report = json.loads((Path(cls.output.name) / 'results.json').read_text('utf-8'))

    def test_companion_runs_all_29_checks_without_skips_or_promotion(self):
        self.assertEqual(self.report['test_result'], 'PASS')
        self.assertEqual(self.report['tests'], {
            name: {'run': count, 'failures': 0, 'errors': 0, 'skipped': 0}
            for name, count in (('base_twelve', 12), ('missing_domain', 6),
                                ('independent_review', 5), ('status_binding', 6))})
        self.assertEqual(self.report['authority_effect'], 'none')
        self.assertFalse(self.report['release_authority_activation'])
        self.assertEqual(self.report['missingness_examples']['missing_target_sample']['value'], None)
        sensor = self.report['sensor_loss_example']
        self.assertTrue(sensor['same_observed_projection_as_fixture_c'])
        self.assertEqual(sensor['bound_volume_change_response'][3], [1])
        self.assertEqual(sensor['fixture_c_bound_volume_change_response'][3], [-1])
        self.assertEqual(sensor['missing_target_sample']['value'], None)

    def test_stored_reference_matches_replay_across_supported_python_versions(self):
        reference = json.loads((COMPANION / 'results.json').read_text('utf-8'))
        # Interpreter provenance may differ; all semantic results and source
        # digests, status views and test inventories must remain identical.
        self.assertEqual({k: v for k, v in self.report.items() if k != 'python_version'},
                         {k: v for k, v in reference.items() if k != 'python_version'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
