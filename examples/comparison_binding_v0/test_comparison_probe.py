"""The twelve original geometric/binding checks, made reproducible."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as Q
import unittest

from comparison_probe import (FULL, SMALL, FIXTURE_NAMES, candidate_curvature,
    candidate_volume, evaluate_geometry, geometry_evidence, load_fixture, replay)
from make_fixtures import rewrite_artifact


class BaseTwelveChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b, cls.c = (load_fixture(name) for name in FIXTURE_NAMES)

    def test_t01_equal_curvature_projection(self):
        self.assertEqual(candidate_curvature((Q(2), FULL)), Q(1,4))
        self.assertEqual(candidate_curvature((Q(2), FULL)), candidate_curvature((Q(2), SMALL)))

    def test_t02_opposite_bound_volume_changes(self):
        self.assertEqual(candidate_volume((Q(2), FULL)), Q(8))
        self.assertEqual(candidate_volume((Q(2), SMALL)), Q(1,8))

    def test_t03_fixed_support_contraction_control(self):
        self.assertEqual(candidate_curvature((Q(1,2), FULL)), Q(4))
        self.assertEqual(candidate_volume((Q(1,2), FULL)), Q(1,8))

    def test_t04_curvature_only_is_unresolved(self):
        expected = ('defined', 'UNRESOLVED', 2, (-1,1), 'diagnostic_only')
        self.assertEqual(replay(self.a), expected)
        self.assertEqual(replay(self.c), expected)

    def test_t05_bound_full_support_identifies_expansion(self):
        self.assertEqual(replay(self.a, ('primary_support',)),
                         ('defined', 'IDENTIFIED', 1, (1,), 'diagnostic_only'))

    def test_t06_bound_reduced_support_identifies_extent_reduction(self):
        self.assertEqual(replay(self.c, ('primary_support',)),
                         ('defined', 'IDENTIFIED', 1, (-1,), 'diagnostic_only'))

    def test_t07_backup_survives_primary_ablation_for_a(self):
        self.assertEqual(replay(self.a, ('backup_support',)), replay(self.a, ('primary_support',)))

    def test_t08_backup_survives_primary_ablation_for_c(self):
        self.assertEqual(replay(self.c, ('backup_support',)), replay(self.c, ('primary_support',)))

    def test_t09_narrow_target_does_not_require_unique_configuration(self):
        self.assertEqual(replay(self.b), ('defined', 'IDENTIFIED', 2, (-1,), 'diagnostic_only'))

    def test_t10_missing_reference_binding_is_unbound(self):
        evidence = replace(geometry_evidence(self.a, ('primary_support',)), reference_binding_valid=False)
        self.assertEqual(evaluate_geometry(evidence), ('defined', 'UNBOUND', None, None, 'diagnostic_only'))

    def test_t11_changed_unmapped_observer_is_unbound(self):
        fixture = deepcopy(self.a)
        frame = deepcopy(fixture['artifacts']['target_frame']['payload'])
        frame['operator_id'] = 'unmapped_operator_v1'
        rewrite_artifact(fixture, 'target_frame', frame)
        self.assertEqual(replay(fixture, ('primary_support',)),
                         ('defined', 'UNBOUND', None, None, 'diagnostic_only'))

    def test_t12_conflicting_supports_do_not_vacuously_identify(self):
        evidence = replace(geometry_evidence(self.a, ('primary_support',)), backup_support=SMALL)
        self.assertEqual(evaluate_geometry(evidence),
                         ('defined', 'INCOMPATIBLE', 0, (), 'diagnostic_only'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
