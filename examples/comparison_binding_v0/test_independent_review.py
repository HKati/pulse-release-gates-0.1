"""Independent review counterexamples, separate from the original inventory."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from itertools import product
import unittest

from comparison_probe import (ContractError, FIXTURE_NAMES, FULL, SMALL, GeometryEvidence,
                              compare_field, evaluate_geometry, geometry_evidence,
                              load_fixture, replay, resolve)
from make_fixtures import refresh_references


def with_sensor_loss(fixture):
    fixture = deepcopy(fixture)
    fixture['artifacts']['target_coverage']['payload']['cells'] = sorted(SMALL)
    fixture['artifacts']['target_state']['payload']['field_observations'] = {'cell:000': '1'}
    return refresh_references(fixture)


class IndependentReviewChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_fixture(FIXTURE_NAMES[0])

    def test_r01_per_cell_matrix_preserves_missingness_and_measured_zero(self):
        cell = 'cell:063'
        modes = ('outside', 'unobserved', 'zero', 'one')
        for source_mode, target_mode in product(modes, repeat=2):
            with self.subTest(source=source_mode, target=target_mode):
                fixture = deepcopy(self.base)
                for label, mode in zip(('source', 'target'), (source_mode, target_mode)):
                    artifacts = fixture['artifacts']
                    if mode == 'outside':
                        artifacts[label + '_support']['payload']['cells'].remove(cell)
                    if mode in ('outside', 'unobserved'):
                        artifacts[label + '_coverage']['payload']['cells'].remove(cell)
                        del artifacts[label + '_state']['payload']['field_observations'][cell]
                    else:
                        artifacts[label + '_state']['payload']['field_observations'][cell] = (
                            '0' if mode == 'zero' else '1')
                refresh_references(fixture)
                report = compare_field(fixture)
                actual = report['deltas'][cell]
                if source_mode == target_mode == 'outside':
                    expected = ('outside_both_supports', None)
                elif source_mode == 'outside':
                    expected = ('outside_source_support', None)
                elif target_mode == 'outside':
                    expected = ('outside_target_support', None)
                elif 'unobserved' in (source_mode, target_mode):
                    expected = ('unobserved', None)
                    self.assertEqual(report['global_scalar_field_identity'], 'UNRESOLVED')
                else:
                    expected = ('observed', str(int(target_mode == 'one') - int(source_mode == 'one')))
                self.assertEqual((actual['status'], actual['value']), expected)

    def test_r02_both_endpoints_reject_null_and_omitted_bindings(self):
        for endpoint, key, mutation in product(('source', 'target'),
                ('system_support', 'observation_coverage'), ('unknown', 'null', 'omitted')):
            with self.subTest(endpoint=endpoint, key=key, mutation=mutation):
                fixture = deepcopy(self.base)
                binding = fixture['comparison_binding'][endpoint]
                if mutation == 'unknown':
                    binding[key] = {'status': 'unknown', 'reason': 'independent review control'}
                    report = compare_field(fixture)
                    self.assertEqual(report['status'], 'UNBOUND')
                    self.assertTrue(all(item['value'] is None for item in report['deltas'].values()))
                else:
                    if mutation == 'null':
                        binding[key] = None
                    else:
                        del binding[key]
                    with self.assertRaises(ContractError):
                        compare_field(fixture)

    def test_r03_claimed_coverage_cannot_hide_missing_or_null_sample(self):
        for label, mode in product(('source', 'target'), ('absent', 'null')):
            with self.subTest(endpoint=label, sample=mode):
                fixture = deepcopy(self.base)
                values = fixture['artifacts'][label + '_state']['payload']['field_observations']
                if mode == 'absent':
                    del values['cell:063']
                else:
                    values['cell:063'] = None
                refresh_references(fixture)
                with self.assertRaises(ContractError):
                    compare_field(fixture)

    def test_r04_internal_evidence_requires_explicit_types_and_binding_flags(self):
        packet = geometry_evidence(self.base, ('primary_support',))
        for flag in ('reference_binding_valid', 'observation_binding_valid'):
            for invalid in ('false', 0, 1, None):
                with self.subTest(flag=flag, invalid=invalid):
                    with self.assertRaises(ContractError):
                        evaluate_geometry(replace(packet, **{flag: invalid}))
            self.assertEqual(evaluate_geometry(replace(packet, **{flag: False})),
                             ('defined', 'UNBOUND', None, None, 'diagnostic_only'))
            kwargs = dict(source_curvature=Fraction(1), target_curvature=Fraction(1, 4),
                          reference_binding_valid=True, observation_binding_valid=True)
            del kwargs[flag]
            with self.assertRaises(TypeError):
                GeometryEvidence(**kwargs)
        for change in ({'target_curvature': 0.25}, {'source_curvature': 1},
                       {'primary_support': set(FULL)}, {'backup_support': frozenset({'foreign:cell'})}):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    evaluate_geometry(replace(packet, **change))
        with self.assertRaises(ContractError):
            evaluate_geometry({'reference_binding_valid': True})

    def test_r05_sensor_loss_is_not_system_support_reduction(self):
        # Keep A's physical/declared support fixed; acquire only C's one cell.
        sensor_loss = with_sensor_loss(self.base)
        reduced_support = load_fixture(FIXTURE_NAMES[2])
        target_states = [resolve(f, f['comparison_binding']['target']['state_ref'])
                         for f in (sensor_loss, reduced_support)]
        for key in ('curvature_observation', 'field_observations'):
            self.assertEqual(target_states[0][key], target_states[1][key])
        self.assertEqual(replay(sensor_loss), replay(reduced_support))
        self.assertEqual(replay(sensor_loss, ('primary_support',))[1:4], ('IDENTIFIED', 1, (1,)))
        self.assertEqual(replay(reduced_support, ('primary_support',))[1:4], ('IDENTIFIED', 1, (-1,)))
        field = compare_field(sensor_loss)
        self.assertEqual(field['global_scalar_field_identity'], 'UNRESOLVED')
        self.assertEqual(field['deltas']['cell:063'],
                         {'status': 'unobserved', 'value': None, 'missing_endpoints': ['target']})
        self.assertEqual(compare_field(reduced_support)['deltas']['cell:063'],
                         {'status': 'outside_target_support', 'value': None})


if __name__ == '__main__':
    unittest.main(verbosity=2)
