"""Standard-library controls of the matrix supervisor.

Synthetic records test the comparator; they are NOT interpreter observations.
The real eight-case experiment is run separately by matrix.py.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matrix as m


def synthetic_rows():
    return [{'requested_version': version, 'status': 'MATCH',
             'observed': {'version': version, 'implementation': 'CPython', 'platform': 'Linux', 'machine': 'x86_64'},
             'semantic_view_sha256': 'a' * 64, 'sources_unchanged': True,
             'frozen_core_unchanged': True, 'completed_scenarios': 8, 'controls': 6,
             'regression_test_methods': 18, 'program_invocations': 48}
            for version in m.VERSIONS]


def synthetic_report():
    observation = {'execution': 'COMPLETED', 'normal_completion': True, 'returncode': 0,
                   'stdout': {'path': 'synthetic.stdout'}, 'stderr': {'path': 'synthetic.stderr'}}
    cases = {}
    for sid in m.SCENARIOS:
        row = {key: None for key in m.VIEW_KEYS}
        row.update(scenario_id=sid, expected_vs_observed='MATCH',
                   coverage_status='COMPLETE_FOR_DECLARED_CASE', authority_effect='none',
                   mutation_manifest={'verified': True}, comparison_details={'test': 'MATCH'},
                   program_observations={name: copy.deepcopy(observation) for name in m.STAGES},
                   reference_observation=copy.deepcopy(observation), reference_result_file={'synthetic': True})
        cases[sid] = row
    return {'execution_status': 'COMPLETED', 'experiment_comparison': 'MATCH',
            'selected_snapshot': m.SOURCE_SNAPSHOT, 'authority_effect': 'none',
            'sources_unchanged': True, 'harness_and_expectations_unchanged_since_freeze': True,
            'all_scenarios': cases, 'scenario_results': {sid: 'MATCH' for sid in m.SCENARIOS},
            'controls': {name: {'result': 'MATCH', 'execution': 'COMPLETED', 'evidence': {'synthetic': True}}
                         for name in m.CONTROLS},
            'regressions': {'successful': True, 'tests_run': 18, 'errors': 0, 'failures': 0,
                            'records': [{'test': 'synthetic_' + str(i), 'result': 'MATCH'} for i in range(18)],
                            'log': {'synthetic': True}}}


class MatrixControls(unittest.TestCase):
    def test_01_package_core_identity(self):
        contract = m.verify_package(HERE)
        self.assertEqual(contract['required_versions'], list(m.VERSIONS))

    def test_02_only_explicit_environment_adaptation(self):
        original = (HERE / 'core/run_cases.py').read_text()
        for version in m.VERSIONS:
            updated = m.adapt_runner(original, version)
            self.assertIn('platform.python_version()!=' + repr(version), updated)
            # Reverse the three declared substitutions, nothing else.
            restored = updated.replace('platform.python_version()!=' + repr(version), "platform.python_version()!='3.13.5'")
            restored = restored.replace('this separate compatibility profile requires CPython ' + version + ' Linux',
                                        'this run profile requires CPython 3.13.5 Linux')
            restored = restored.replace('This individual record covers only CPython ' + version +
                                        ' Linux; the cross-record comparison is separate.',
                                        'Only CPython 3.13.5 Linux executed; no cross-version equivalence claim.')
            self.assertEqual(restored, original)

    def test_03_changed_environment_template_rejected(self):
        with self.assertRaises(ValueError): m.adapt_runner('unexpected program', '3.13.5')

    def test_04_unknown_version_rejected(self):
        with self.assertRaises(ValueError): m.adapt_runner('', '9.9.9')

    def test_05_no_results_not_pass(self):
        self.assertEqual(m.finalize([])['status'], 'INCOMPLETE')

    def test_06_one_version_not_portability(self):
        self.assertFalse(m.finalize(synthetic_rows()[2:3])['cross_version_compatibility_established_for_declared_profile'])

    def test_07_missing_version_not_pass(self):
        self.assertEqual(m.finalize(synthetic_rows()[:-1])['status'], 'INCOMPLETE')

    def test_08_duplicate_version_not_pass(self):
        rows = synthetic_rows(); rows[-1] = copy.deepcopy(rows[0])
        self.assertEqual(m.finalize(rows)['status'], 'INCOMPLETE')

    def test_09_synthetic_complete_equal_views(self):
        self.assertEqual(m.finalize(synthetic_rows())['status'], 'MATCH')

    def test_10_different_semantic_views(self):
        rows = synthetic_rows(); rows[-1]['semantic_view_sha256'] = 'b' * 64
        self.assertEqual(m.finalize(rows)['status'], 'MISMATCH')

    def test_11_interpreter_label_cannot_override_observation(self):
        row = synthetic_rows()[0]['observed']; row['version'] = '3.13.5'
        with self.assertRaisesRegex(ValueError, 'VERSION_MISMATCH'): m.validate_probe(row, '3.11.14')

    def test_12_different_platform_not_silent_equivalence(self):
        row = synthetic_rows()[0]['observed']; row['platform'] = 'Windows'
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_DECLARED'): m.validate_probe(row, '3.11.14')

    def test_13_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError): m.strict_json(b'{"result":0,"result":1}')

    def test_14_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError): m.strict_json(b'{"result":NaN}')

    def test_15_duplicate_interpreter_argument_rejected(self):
        with self.assertRaises(ValueError): m.parse_interpreters(['3.13.5=/one', '3.13.5=/two'])

    def test_16_relative_interpreter_argument_rejected(self):
        with self.assertRaises(ValueError): m.parse_interpreters(['3.13.5=python'])

    def test_17_missing_scenario_rejected(self):
        report = synthetic_report(); del report['all_scenarios']['E30']
        with self.assertRaisesRegex(ValueError, 'SCENARIO_COVERAGE'): m.semantic_view(report)

    def test_18_missing_control_rejected(self):
        report = synthetic_report(); del report['controls']['G04']
        with self.assertRaisesRegex(ValueError, 'CONTROL_COVERAGE'): m.semantic_view(report)

    def test_19_failed_regression_rejected(self):
        report = synthetic_report(); report['regressions']['failures'] = 1
        with self.assertRaisesRegex(ValueError, 'REGRESSION'): m.semantic_view(report)

    def test_20_missing_program_stage_rejected(self):
        report = synthetic_report(); del report['all_scenarios']['E20']['program_observations']['edge_checker']
        with self.assertRaisesRegex(ValueError, 'MISSING_PROGRAM_STAGE'): m.semantic_view(report)

    def test_21_timeout_not_expected_rejection(self):
        report = synthetic_report(); report['all_scenarios']['E20']['program_observations']['edge_checker']['execution'] = 'TIMEOUT'
        with self.assertRaisesRegex(ValueError, 'ABNORMAL'): m.semantic_view(report)

    def test_22_missing_semantic_digest_rejected(self):
        rows = synthetic_rows()
        for row in rows: del row['semantic_view_sha256']
        self.assertEqual(m.finalize(rows)['status'], 'INCOMPLETE')

    def test_23_tampered_log_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root / 'log'; p.write_bytes(b'changed')
            record = {'path': str(p), 'bytes': 7, 'sha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'DIGEST_MISMATCH'): m.verify_references(record, root)

    def test_24_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'actual').write_text('input'); (root / 'link').symlink_to(root / 'actual')
            with self.assertRaisesRegex(ValueError, 'symlink'): m.regular_under(root, 'link')

    def test_25_traversal_input_rejected(self):
        with self.assertRaisesRegex(ValueError, 'relative path'): m.regular_under(HERE, '../matrix.py')

    def test_26_reference_input_change_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); shutil.copytree(HERE, root / 'package'); package = root / 'package'
            (package / 'core/independent_reference.py').write_text('# changed\n')
            with self.assertRaisesRegex(ValueError, 'changed historical core'): m.verify_package(package)

    def test_27_synthetic_complete_report_projected(self):
        self.assertEqual(set(m.semantic_view(synthetic_report())), set(m.SCENARIOS))

    def test_28_control_failure_cannot_be_hidden(self):
        report = synthetic_report(); report['controls']['G01']['result'] = 'MISMATCH'
        with self.assertRaisesRegex(ValueError, 'FAILED_OR_MISSING_CONTROL'): m.semantic_view(report)

    def test_29_missing_log_cannot_be_hidden(self):
        report = synthetic_report(); del report['all_scenarios']['E00']['reference_observation']['stderr']
        with self.assertRaisesRegex(ValueError, 'MISSING_LOG'): m.semantic_view(report)

    def test_30_identical_claims_wrong_actual_version_not_pass(self):
        rows = synthetic_rows(); rows[0]['observed']['version'] = '3.13.5'
        self.assertEqual(m.finalize(rows)['status'], 'INCOMPLETE')


    def test_31_absence_of_source_reconstruction_is_preserved(self):
        report = synthetic_report(); row = report['all_scenarios']['E30']
        del row['source_differences']
        row.update(reference_source_assessment='UNRESOLVED', missing_source_premises=['metric-source'],
                   proof_applicability_assessment='NOT_JUSTIFIED', certificate=None)
        result = m.semantic_view(report)['E30']['source_differences']
        self.assertEqual(result, {'present': False, 'value': None})

    def test_32_missing_source_differences_cannot_hide_justified_claim(self):
        report = synthetic_report(); row = report['all_scenarios']['E00']
        del row['source_differences']; row['reference_source_assessment'] = 'JUSTIFIED_WITHIN_FIXTURE_BOUNDARY'
        with self.assertRaisesRegex(ValueError, 'UNEXPLAINED_MISSING'): m.semantic_view(report)

    def test_33_missing_is_not_empty_reconstruction(self):
        report = synthetic_report(); row = report['all_scenarios']['E30']
        del row['source_differences']
        row.update(reference_source_assessment='UNRESOLVED', missing_source_premises=['metric-source'],
                   proof_applicability_assessment='NOT_JUSTIFIED', certificate=None)
        absent = m.semantic_view(report)['E30']['source_differences']
        row['source_differences'] = []
        self.assertNotEqual(absent, m.semantic_view(report)['E30']['source_differences'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
