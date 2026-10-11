"""Prevent target identification from promoting observation, cause or authority."""
from copy import deepcopy
from dataclasses import replace
import unittest

from comparison_probe import (FIXTURE_NAMES, SMALL, field_status_view, geometry_evidence,
                              geometry_status_view, load_fixture)
from make_fixtures import rewrite_artifact
from test_independent_review import with_sensor_loss
from test_missing_domain import with_missing_target_sample


class StatusBindingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b, cls.c = (load_fixture(name) for name in FIXTURE_NAMES)

    def test_s01_all_six_axes_are_explicit_and_non_authoritative(self):
        expected_keys = {'observation_status', 'binding_status', 'consistency_status',
                         'reproduction_status', 'causal_status', 'authority_status'}
        views = [field_status_view(f) for f in (self.a, self.b, self.c)]
        views += [geometry_status_view(geometry_evidence(f, paths))
                  for f in (self.a, self.b, self.c)
                  for paths in ((), ('primary_support',), ('backup_support',))]
        for view in views:
            with self.subTest(claim=view['claim_id'], result=view['target_assessment']):
                axes = view['status_axes']
                self.assertEqual(set(axes), expected_keys)
                self.assertEqual(axes['reproduction_status'], 'bounded_replay_only')
                self.assertEqual(axes['causal_status'], 'not_evaluated')
                self.assertEqual(axes['authority_status'], 'diagnostic')
                self.assertEqual(view['authority_effect'], 'none')
                self.assertFalse(view['physical_transition_path_evaluated'])

    def test_s02_identified_narrow_target_does_not_complete_endpoint_bindings(self):
        view = geometry_status_view(geometry_evidence(self.b))
        self.assertEqual(view['target_assessment']['identification_status'], 'IDENTIFIED')
        self.assertEqual(view['target_assessment']['compatible_candidate_count'], 2)
        self.assertEqual(view['status_axes']['observation_status'], 'partially_observed')
        self.assertEqual(view['status_axes']['binding_status'], 'partially_bound')
        self.assertEqual(view['status_axes']['consistency_status'], 'consistent')

    def test_s03_unbound_is_not_an_empty_compatible_set(self):
        packet = replace(geometry_evidence(self.a, ('primary_support',)), reference_binding_valid=False)
        view = geometry_status_view(packet)
        self.assertIsNone(view['target_assessment']['compatible_candidate_count'])
        self.assertIsNone(view['target_assessment']['possible_target_values'])
        self.assertEqual(view['status_axes']['binding_status'], 'unbound')
        self.assertEqual(view['status_axes']['consistency_status'], 'internally_incomplete')

    def test_s04_conflicting_endpoint_receipts_remain_conflicting(self):
        packet = replace(geometry_evidence(self.a, ('primary_support',)), backup_support=SMALL)
        view = geometry_status_view(packet)
        self.assertEqual(view['target_assessment']['identification_status'], 'INCOMPATIBLE')
        self.assertEqual(view['target_assessment']['compatible_candidate_count'], 0)
        self.assertEqual(view['status_axes']['binding_status'], 'identity_conflict')
        self.assertEqual(view['status_axes']['consistency_status'], 'conflicting')

    def test_s05_measured_difference_does_not_complete_unobserved_samples(self):
        missing = with_missing_target_sample(self.a)
        view = field_status_view(missing)
        self.assertEqual(view['target_assessment']['global_scalar_field_identity'], 'UNRESOLVED')
        self.assertEqual(view['status_axes']['consistency_status'], 'ambiguous')
        state = deepcopy(missing['artifacts']['target_state']['payload'])
        state['field_observations']['cell:000'] = '0'
        rewrite_artifact(missing, 'target_state', state)
        different = field_status_view(missing)
        self.assertEqual(different['target_assessment']['global_scalar_field_identity'], 'IDENTIFIED_DIFFERENT')
        self.assertEqual(different['status_axes']['consistency_status'], 'consistent')
        self.assertEqual(different['status_axes']['binding_status'], 'bound')
        self.assertEqual(different['status_axes']['observation_status'], 'partially_observed')

    def test_s06_sensor_loss_does_not_promote_scalar_identity_from_geometry(self):
        fixture = with_sensor_loss(self.a)
        geometric = geometry_status_view(geometry_evidence(fixture, ('primary_support',)))
        scalar = field_status_view(fixture)
        self.assertEqual(geometric['target_assessment']['possible_target_values'], (1,))
        self.assertEqual(geometric['status_axes']['consistency_status'], 'consistent')
        self.assertEqual(scalar['target_assessment']['global_scalar_field_identity'], 'UNRESOLVED')
        self.assertEqual(scalar['status_axes']['observation_status'], 'partially_observed')
        self.assertEqual(scalar['status_axes']['consistency_status'], 'ambiguous')


if __name__ == '__main__':
    unittest.main(verbosity=2)
