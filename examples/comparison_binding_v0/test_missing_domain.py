"""Separate controls for missing coverage, removed support and measured zero."""
from copy import deepcopy
import unittest

from comparison_probe import (ContractError, FIXTURE_NAMES, SMALL, compare_field,
                              field_status_view, geometry_evidence, geometry_status_view,
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


def with_endpoint_support(fixture, label, cells):
    """Bind a known endpoint support and its actual samples to the same cells."""
    fixture = deepcopy(fixture)
    for suffix in ('support', 'coverage'):
        name = label + '_' + suffix
        payload = deepcopy(fixture['artifacts'][name]['payload'])
        payload['cells'] = sorted(cells)
        rewrite_artifact(fixture, name, payload)
    name = label + '_state'
    state = deepcopy(fixture['artifacts'][name]['payload'])
    state['field_observations'] = {
        cell: state['field_observations'][cell] for cell in sorted(cells)}
    rewrite_artifact(fixture, name, state)
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

    def test_z07_unknown_source_support_keeps_replay_and_status_views_unbound(self):
        paths = ((), ('primary_support',), ('backup_support',),
                 ('primary_support', 'backup_support'))
        for name in FIXTURE_NAMES:
            fixture = load_fixture(name)
            fixture['comparison_binding']['source']['system_support'] = {
                'status': 'unknown', 'reason': 'source membership receipt unavailable'}
            validate_fixture(fixture)
            self.assertEqual(field_status_view(fixture)['status_axes']['binding_status'], 'unbound')
            for enabled in paths:
                with self.subTest(fixture=name, paths=enabled):
                    self.assertEqual(replay(fixture, enabled),
                                     ('defined', 'UNBOUND', None, None, 'diagnostic_only'))
                    view = geometry_status_view(geometry_evidence(fixture, enabled))
                    self.assertEqual(view['target_assessment']['identification_status'], 'UNBOUND')
                    self.assertIsNone(view['target_assessment']['compatible_candidate_count'])
                    self.assertIsNone(view['target_assessment']['possible_target_values'])
                    self.assertEqual(view['status_axes']['binding_status'], 'unbound')
                    self.assertEqual(view['status_axes']['consistency_status'], 'internally_incomplete')

    def test_z08_two_known_empty_supports_cannot_identify_a_scalar_field(self):
        for name in FIXTURE_NAMES:
            with self.subTest(fixture=name):
                fixture = with_endpoint_support(load_fixture(name), 'source', ())
                fixture = with_endpoint_support(fixture, 'target', ())
                validate_fixture(fixture)
                report = compare_field(fixture)
                self.assertEqual(report['status'], 'INCOMPATIBLE')
                self.assertEqual(report['global_scalar_field_identity'], 'UNRESOLVED')
                self.assertTrue(all(item['status'] == 'outside_both_supports'
                                    and item['value'] is None for item in report['deltas'].values()))
                view = field_status_view(fixture)
                self.assertEqual(view['status_axes']['observation_status'], 'not_observed')
                self.assertEqual(view['status_axes']['binding_status'], 'bound')
                self.assertEqual(view['status_axes']['consistency_status'], 'conflicting')

    def test_z09_known_nonfull_source_stays_outside_the_geometric_profile(self):
        for cells in (SMALL, frozenset()):
            with self.subTest(source_support=cells):
                fixture = with_endpoint_support(self.a, 'source', cells)
                validate_fixture(fixture)
                with self.assertRaisesRegex(ContractError, 'fixed source support'):
                    geometry_evidence(fixture, ('primary_support',))
                # One known empty endpoint still proves support inequality;
                # it must not be confused with unknown support or empty equality.
                self.assertEqual(compare_field(fixture)['global_scalar_field_identity'],
                                 'NOT_EQUAL_SUPPORT')


if __name__ == '__main__':
    unittest.main(verbosity=2)
