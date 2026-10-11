"""Separate controls for missing coverage, removed support and measured zero."""
from copy import deepcopy
import unittest

from comparison_probe import (ContractError, FIXTURE_NAMES, compare_field,
                              load_fixture, replay, validate_fixture)
from make_fixtures import rewrite_artifact


def with_missing_target_sample(fixture, cell='cell:063'):
    fixture = deepcopy(fixture)
    coverage = deepcopy(fixture['artifacts']['target_coverage']['payload'])
    coverage['cells'].remove(cell)
    rewrite_artifact(fixture, 'target_coverage', coverage)
    state = deepcopy(fixture['artifacts']['target_state']['payload'])
    del state['field_observations'][cell]
    rewrite_artifact(fixture, 'target_state', state)
    return fixture


class MissingDomainChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = load_fixture(FIXTURE_NAMES[0])
        cls.c = load_fixture(FIXTURE_NAMES[2])

    def test_z01_missing_sample_cannot_be_zero_filled(self):
        fixture = with_missing_target_sample(self.a)
        report = compare_field(fixture)
        self.assertEqual(report['deltas']['cell:063'],
                         {'status': 'unobserved', 'value': None, 'missing_endpoints': ['target']})
        self.assertEqual(report['deltas']['cell:000']['value'], '0')
        self.assertEqual(report['global_scalar_field_identity'], 'UNRESOLVED')
        # The geometric target may remain identified by its own sufficient
        # evidence; this does not identify the unobserved scalar field.
        self.assertEqual(replay(fixture, ('primary_support',))[1:4], ('IDENTIFIED', 1, (1,)))

    def test_z02_omitted_coverage_binding_is_rejected(self):
        fixture = deepcopy(self.a)
        del fixture['comparison_binding']['target']['observation_coverage']
        with self.assertRaises(ContractError):
            validate_fixture(fixture)

    def test_z03_unknown_coverage_is_not_empty_coverage(self):
        fixture = deepcopy(self.a)
        fixture['comparison_binding']['target']['observation_coverage'] = {
            'status': 'unknown', 'reason': 'coverage receipt not available'}
        report = compare_field(fixture)
        self.assertEqual(report['status'], 'UNBOUND')
        self.assertEqual(report['global_scalar_field_identity'], 'UNRESOLVED')
        self.assertTrue(all(item['value'] is None for item in report['deltas'].values()))
        # A known empty acquisition set is different from unknown coverage.
        empty = deepcopy(self.a)
        coverage = deepcopy(empty['artifacts']['target_coverage']['payload'])
        coverage['cells'] = []
        rewrite_artifact(empty, 'target_coverage', coverage)
        state = deepcopy(empty['artifacts']['target_state']['payload'])
        state['field_observations'] = {}
        rewrite_artifact(empty, 'target_state', state)
        empty_report = compare_field(empty)
        self.assertEqual(empty_report['status'], 'PARTIALLY_OBSERVED')
        self.assertTrue(all(item['status'] == 'unobserved' and item['value'] is None
                            for item in empty_report['deltas'].values()))

    def test_z04_measured_zero_is_preserved_as_a_measurement(self):
        fixture = deepcopy(self.a)
        state = deepcopy(fixture['artifacts']['target_state']['payload'])
        state['field_observations']['cell:063'] = '0'
        rewrite_artifact(fixture, 'target_state', state)
        report = compare_field(fixture)
        self.assertEqual(report['deltas']['cell:063'], {'status': 'observed', 'value': '-1'})
        self.assertEqual(report['global_scalar_field_identity'], 'IDENTIFIED_DIFFERENT')

    def test_z05_removed_support_has_no_numeric_field_extension(self):
        report = compare_field(self.c)
        self.assertEqual(report['deltas']['cell:063'],
                         {'status': 'outside_target_support', 'value': None})
        self.assertEqual(report['global_scalar_field_identity'], 'NOT_EQUAL_SUPPORT')
        self.assertEqual(report['deltas']['cell:000'], {'status': 'observed', 'value': '0'})

    def test_z06_unknown_system_support_is_not_an_empty_system(self):
        fixture = deepcopy(self.c)
        fixture['comparison_binding']['target']['system_support'] = {
            'status': 'unknown', 'reason': 'system membership receipt not available'}
        report = compare_field(fixture)
        self.assertEqual(report['status'], 'UNBOUND')
        self.assertTrue(all(item['value'] is None for item in report['deltas'].values()))
        self.assertEqual(replay(fixture, ('primary_support',))[1:4], ('UNRESOLVED', 2, (-1,1)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
