"""Regression and bounded exhaustive checks for the local synthetic witness."""
from fractions import Fraction
from itertools import combinations, permutations
import json
import unittest

import relation_closure_probe as p


class RelationProbeTests(unittest.TestCase):
    def test_domain_has_exactly_330_unique_histograms(self):
        domain = p.enumerate_histograms(p.Domain())
        self.assertEqual(len(domain), 330)
        self.assertEqual(len(set(domain)), 330)
        self.assertTrue(all(sum(h.counts) == 4 for h in domain))

    def test_fixtures_are_distinct_and_valid(self):
        self.assertNotEqual(p.EVEN, p.ODD)
        self.assertEqual(p.EVEN.domain, p.ODD.domain)

    def test_all_singleton_marginals_are_identical(self):
        for scope in p.all_scopes(3, 1):
            self.assertEqual(p.marginal(p.EVEN, scope), (2, 2))
            self.assertEqual(p.marginal(p.ODD, scope), (2, 2))

    def test_all_pair_marginals_are_identical(self):
        for scope in combinations(range(3), 2):
            self.assertEqual(p.marginal(p.EVEN, scope), (1, 1, 1, 1))
            self.assertEqual(p.marginal(p.ODD, scope), (1, 1, 1, 1))

    def test_full_joint_counts_are_not_identical(self):
        self.assertNotEqual(p.marginal(p.EVEN, (0, 1, 2)), p.marginal(p.ODD, (0, 1, 2)))

    def test_actual_fixture_targets_differ(self):
        self.assertEqual(p.odd_fraction(p.EVEN), Fraction(0))
        self.assertEqual(p.odd_fraction(p.ODD), Fraction(1))

    def test_old_complete_responses_are_equal_and_unresolved(self):
        a, _ = p.run_machine(p.BEFORE, p.EVEN)
        b, _ = p.run_machine(p.BEFORE, p.ODD)
        self.assertEqual(a, b)
        self.assertEqual(a.definedness, 'defined')
        self.assertEqual(a.output.status, 'unresolved')
        self.assertEqual(a.output.compatible_histogram_count, 2)
        self.assertEqual(a.output.possible_target_values, (Fraction(0), Fraction(1)))

    def test_new_complete_responses_discriminate(self):
        a, _ = p.run_machine(p.AFTER, p.EVEN)
        b, _ = p.run_machine(p.AFTER, p.ODD)
        self.assertNotEqual(a, b)
        self.assertEqual(a.output.possible_target_values, (Fraction(0),))
        self.assertEqual(b.output.possible_target_values, (Fraction(1),))
        self.assertEqual(a.output.compatible_histogram_count, 1)
        self.assertEqual(b.output.compatible_histogram_count, 1)

    def test_ablation_restores_old_complete_response_for_both_fixtures(self):
        for fixture in (p.EVEN, p.ODD):
            old, _ = p.run_machine(p.BEFORE, fixture)
            ablated, _ = p.run_machine(p.ABLATED, fixture)
            self.assertEqual(old, ablated)

    def test_evaluator_target_and_response_shape_are_fixed(self):
        for machine in (p.BEFORE, p.AFTER, p.ABLATED, p.WITH_BACKUP):
            self.assertEqual(machine.evaluator_id, p.EVALUATOR_ID)
            self.assertEqual(machine.target_id, p.TARGET_ID)
            response, _ = p.run_machine(machine, p.EVEN)
            self.assertEqual(tuple(response.as_json()), ('definedness', 'semantic_state', 'output', 'consequence'))
            self.assertEqual(response.consequence, 'diagnostic_only_no_external_effect')

    def test_disabled_joint_binding_is_not_read(self):
        for machine in (p.BEFORE, p.ABLATED):
            _, source = p.run_machine(machine, p.ODD)
            self.assertTrue(all(len(scope) <= 2 for _, scope in source.read_trace))
            self.assertNotIn(p.JOINT.binding_id, [binding_id for binding_id, _ in source.read_trace])

    def test_unauthorized_direct_joint_read_is_rejected(self):
        source = p.EvidenceSource(p.EVEN, p.BEFORE.bindings)
        with self.assertRaises(PermissionError):
            source.read(p.JOINT)
        self.assertEqual(source.read_trace, [])

    def test_primary_ablation_preserves_backup_discrimination(self):
        machine = p.WITH_BACKUP.ablate(frozenset({p.JOINT.binding_id}))
        a, a_source = p.run_machine(machine, p.EVEN)
        b, b_source = p.run_machine(machine, p.ODD)
        self.assertNotEqual(a, b)
        self.assertEqual(a.output.possible_target_values, (Fraction(0),))
        self.assertEqual(b.output.possible_target_values, (Fraction(1),))
        for source in (a_source, b_source):
            self.assertIn((p.JOINT_BACKUP.binding_id, p.JOINT_BACKUP.scope), source.read_trace)
            self.assertNotIn((p.JOINT.binding_id, p.JOINT.scope), source.read_trace)

    def test_ablation_of_all_joint_routes_restores_equality(self):
        machine = p.WITH_BACKUP.ablate(frozenset({p.JOINT.binding_id, p.JOINT_BACKUP.binding_id}))
        a, _ = p.run_machine(machine, p.EVEN)
        b, _ = p.run_machine(machine, p.ODD)
        self.assertEqual(a, b)
        self.assertEqual(a, p.run_machine(p.BEFORE, p.EVEN)[0])

    def test_duplicate_valid_route_does_not_invent_information(self):
        for fixture in (p.EVEN, p.ODD):
            self.assertEqual(p.run_machine(p.AFTER, fixture)[0], p.run_machine(p.WITH_BACKUP, fixture)[0])

    def test_measurement_ablation_does_not_change_source_target(self):
        for fixture in (p.EVEN, p.ODD):
            before_counts, before_target = fixture.counts, p.odd_fraction(fixture)
            p.run_machine(p.AFTER, fixture)
            p.run_machine(p.ABLATED, fixture)
            self.assertEqual(fixture.counts, before_counts)
            self.assertEqual(p.odd_fraction(fixture), before_target)

    def test_whole_record_reordering_does_not_change_results(self):
        for rows in (p.EVEN_ROWS, p.ODD_ROWS):
            baseline = p.histogram_from_rows(rows)
            for ordering in permutations(rows):
                permuted = p.histogram_from_rows(ordering)
                self.assertEqual(permuted, baseline)
                self.assertEqual(p.run_machine(p.AFTER, permuted)[0], p.run_machine(p.AFTER, baseline)[0])

    def test_all_proper_projections_for_n_2_through_8(self):
        result = p.parity_family_check(8)
        self.assertEqual(result['proper_projection_checks'], 494)
        self.assertEqual(len(result['cases']), 7)

    def test_all_330_joint_histograms_are_exactly_recovered(self):
        for fixture in p.enumerate_histograms(p.Domain()):
            response, _ = p.run_machine(p.AFTER, fixture)
            self.assertEqual(response.output.status, 'identified')
            self.assertEqual(response.output.compatible_histogram_count, 1)
            self.assertEqual(response.output.possible_target_values, (p.odd_fraction(fixture),))

    def test_scope_addition_is_monotone_over_all_128_scope_sets(self):
        scopes = p.all_scopes(3)
        for fixture in (p.EVEN, p.ODD):
            reports = {}
            for mask in range(1 << len(scopes)):
                observations = [p.Observation(p.Domain(), scope, p.marginal(fixture, scope), 'fixed')
                                for i, scope in enumerate(scopes) if mask & (1 << i)]
                reports[mask] = p.infer(p.Domain(), observations)
                self.assertIn(p.odd_fraction(fixture), reports[mask].possible_target_values)
            for mask, old in reports.items():
                for i in range(len(scopes)):
                    if not mask & (1 << i):
                        new = reports[mask | (1 << i)]
                        self.assertLessEqual(new.compatible_histogram_count, old.compatible_histogram_count)
                        self.assertTrue(set(new.possible_target_values) <= set(old.possible_target_values))

    def test_no_evidence_is_not_zero_effect(self):
        response = p.infer(p.Domain(), [])
        self.assertEqual(response.status, 'unresolved')
        self.assertEqual(response.compatible_histogram_count, 330)
        self.assertEqual(response.possible_target_values, tuple(Fraction(k, 4) for k in range(5)))

    def test_incompatible_relations_do_not_produce_vacuous_identification(self):
        observations = [p.Observation(p.Domain(), (0, 1), (2, 0, 0, 2), 'fixed'),
                        p.Observation(p.Domain(), (1, 2), (2, 0, 0, 2), 'fixed'),
                        p.Observation(p.Domain(), (0, 2), (0, 2, 2, 0), 'fixed')]
        result = p.infer(p.Domain(), observations)
        self.assertEqual(result.status, 'incompatible')
        self.assertEqual(result.compatible_histogram_count, 0)
        self.assertEqual(result.possible_target_values, ())

    def test_conflicting_duplicate_scope_is_not_silently_overwritten(self):
        observations = [p.Observation(p.Domain(), (0,), (4, 0), 'fixed'),
                        p.Observation(p.Domain(), (0,), (0, 4), 'fixed')]
        self.assertEqual(p.infer(p.Domain(), observations).status, 'incompatible')

    def test_unbound_contexts_cannot_be_pooled(self):
        observations = [p.Observation(p.Domain(), (0,), (2, 2), 'run_A'),
                        p.Observation(p.Domain(), (1,), (2, 2), 'run_B')]
        with self.assertRaises(p.EvidenceError):
            p.infer(p.Domain(), observations)

    def test_domain_mismatch_cannot_be_pooled(self):
        observation = p.Observation(p.Domain(2, 4), (0,), (2, 2), 'fixed')
        with self.assertRaises(p.EvidenceError):
            p.infer(p.Domain(), [observation])

    def test_target_sufficiency_does_not_require_full_state(self):
        observation = p.Observation(p.Domain(), (0,), (2, 2), 'fixed')
        result = p.infer(p.Domain(), [observation], target=p.first_bit_fraction)
        self.assertEqual(result.status, 'identified')
        self.assertGreater(result.compatible_histogram_count, 1)
        self.assertEqual(result.possible_target_values, (Fraction(1, 2),))

    def test_declared_count_tolerance_expands_the_admissible_set(self):
        observations = [p.Observation(p.Domain(), scope, p.marginal(p.EVEN, scope), 'fixed')
                        for scope in p.all_scopes(3, 2)]
        exact = p.infer(p.Domain(), observations)
        bounded = p.infer(p.Domain(), observations, count_tolerance=1)
        self.assertGreater(bounded.compatible_histogram_count, exact.compatible_histogram_count)
        self.assertTrue(set(exact.possible_target_values) <= set(bounded.possible_target_values))
        self.assertEqual(bounded.status, 'unresolved')

    def test_invalid_scopes_are_rejected(self):
        for scope in ((), (0, 0), (1, 0), (3,), (True,)):
            with self.assertRaises(p.EvidenceError):
                p.validate_scope(scope, 3)

    def test_invalid_counts_are_rejected(self):
        for counts in ((1, 1), (1.0, 3), (-1, 5), (True, 3)):
            with self.assertRaises(p.EvidenceError):
                p.Observation(p.Domain(), (0,), counts, 'fixed')

    def test_invalid_rows_and_domains_are_rejected(self):
        for rows in (((0, 0),), ((0, 0, 2),), ((True, 0, 0),)):
            with self.assertRaises(ValueError):
                p.histogram_from_rows(rows)
        for args in ((0, 4), (5, 4), (3, 0), (3, 5), (True, 4)):
            with self.assertRaises(ValueError):
                p.Domain(*args)

    def test_empty_context_is_rejected(self):
        with self.assertRaises(p.EvidenceError):
            p.Observation(p.Domain(), (0,), (2, 2), '')

    def test_invalid_tolerance_is_rejected(self):
        for tolerance in (-1, 0.5, True):
            with self.assertRaises(ValueError):
                p.infer(p.Domain(), [], count_tolerance=tolerance)

    def test_duplicate_binding_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            p.Machine((p.JOINT, p.JOINT))

    def test_posthoc_evaluator_or_target_replacement_is_rejected(self):
        with self.assertRaises(ValueError):
            p.Machine(p.PROPER_BINDINGS, evaluator_id='replacement')
        with self.assertRaises(ValueError):
            p.Machine(p.PROPER_BINDINGS, target_id='chosen_after_results')

    def test_unknown_ablation_id_is_rejected(self):
        with self.assertRaises(ValueError):
            p.AFTER.ablate(frozenset({'not_a_binding'}))

    def test_report_replay_is_deterministic(self):
        first = json.dumps(p.make_report(), sort_keys=True)
        second = json.dumps(p.make_report(), sort_keys=True)
        self.assertEqual(first, second)
        self.assertFalse(p.make_report()['quantum_experiment'])
        self.assertFalse(p.make_report()['population_inference'])
        self.assertEqual(p.make_report()['authority_effect'], 'none')


if __name__ == '__main__':
    unittest.main(verbosity=2)
