"""TEST-only content rules. These synthetic records never certify QRH proofs."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audit
from common import read_json, canonical_bytes, SUBJECT_COMMIT, PULSE_COMMIT


class TestContentRules(unittest.TestCase):
    def setUp(self):
        self.configs = read_json(ROOT / 'reference/configurations.json')
        self.exports = [n for c in self.configs for n in c['theorem_exports']]
        self.claims = [c['claim_id'] for c in self.configs]
        self.standard = {name: str(i + 1) * 64 for i, name in enumerate(sorted(audit.AXIOMS))}

    def rejected(self, result, reason):
        self.assertEqual('BLOCK', result['state'])
        self.assertIn(reason, result['reason_codes'])

    def axiom_records(self):
        return [{'theorem': n, 'kernel_check_state': 'ACCEPTED',
                 'axioms': [{'name': 'propext', 'declaration_sha256': self.standard['propext']}]}
                for n in self.exports]

    def builds(self):
        return [{'build_id': b, 'configuration_id': c, 'return_code': 0,
                 'timed_out': False, 'oom_killed': False, 'resource_failure': False,
                 'toolchain_sha256': 'a' * 64, 'precompiled_audited_proofs': False,
                 'shared_audited_proof_base': None, 'invocation_id': b + c,
                 'workspace_id': b + '-workspace-' + c, 'environment_id': b,
                 'cache_lineage_id': b + '-cold-source'}
                for b in ('A', 'B') for c in self.claims]

    def test_scope_positive_control_four_claims_five_exports(self):
        self.assertEqual('SOURCE_MAP_BOUND', audit.rule_scope(self.configs, self.configs,
                         self.claims, self.exports)['state'])

    def test_scope_omitted_fifth_export_reaches_content_rule(self):
        self.rejected(audit.rule_scope(self.configs, self.configs, self.claims, self.exports[:-1]),
                      'QRH003_CLAIM_OR_EXPORT_OMITTED')

    def test_scope_changed_solution_module_reaches_content_rule(self):
        changed = copy.deepcopy(self.configs)
        changed[0]['solution_module'] = 'FakeProof'
        self.rejected(audit.rule_scope(changed, self.configs, self.claims, self.exports),
                      'QRH003_SCOPE_MAPPING_MISMATCH')

    def test_axiom_standard_subset_control(self):
        records = self.axiom_records()
        records[0]['axioms'] = []  # An axiom-free theorem is allowed.
        self.assertEqual('VERIFIED', audit.rule_axioms(records, self.exports, self.standard)['state'])

    def test_sorry_ax_reaches_axiom_evaluator(self):
        records = self.axiom_records()
        records[-1]['axioms'].append({'name': 'sorryAx', 'declaration_sha256': 'b' * 64})
        self.rejected(audit.rule_axioms(records, self.exports, self.standard),
                      'QRH003_SOLUTION_SORRYAX_REACHABLE')

    def test_custom_axiom_reaches_axiom_evaluator(self):
        records = self.axiom_records()
        records[0]['axioms'] = [{'name': 'my_axiom', 'declaration_sha256': 'b' * 64}]
        self.rejected(audit.rule_axioms(records, self.exports, self.standard),
                      'QRH003_AXIOM_OR_DECLARATION_NOT_ALLOWED')

    def test_standard_named_axiom_with_wrong_origin(self):
        records = self.axiom_records()
        records[0]['axioms'][0]['declaration_sha256'] = 'b' * 64
        self.rejected(audit.rule_axioms(records, self.exports, self.standard),
                      'QRH003_AXIOM_OR_DECLARATION_NOT_ALLOWED')

    def test_axiom_duplicate_export_not_independent_evidence(self):
        records = self.axiom_records()
        records.append(copy.deepcopy(records[0]))
        self.rejected(audit.rule_axioms(records, self.exports, self.standard),
                      'QRH003_RECEIPT_SCOPE_REUSED')

    def test_build_identity_positive_control(self):
        self.assertEqual('VERIFIED', audit.rule_builds(self.builds(), self.claims, 'a' * 64)['state'])

    def test_build_nonzero_even_with_success_log(self):
        records = self.builds()
        records[-1].update(return_code=1, stdout='success success success')
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_EXIT_NONZERO')

    def test_build_timeout_blocks(self):
        records = self.builds()
        records[0]['timed_out'] = True
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_RESOURCE_FAILURE')

    def test_build_oom_blocks(self):
        records = self.builds()
        records[0]['oom_killed'] = True
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_RESOURCE_FAILURE')

    def test_build_toolchain_changed(self):
        records = self.builds()
        records[0]['toolchain_sha256'] = 'c' * 64
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_TOOLCHAIN_BINARY_BINDING_MISMATCH')

    def test_build_cloned_environment(self):
        records = self.builds()
        for record in records:
            record['environment_id'] = 'same-host-snapshot'
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_ENVIRONMENTS_NOT_INDEPENDENT')

    def test_build_shared_writable_cache(self):
        records = self.builds()
        for record in records:
            record['cache_lineage_id'] = 'shared-cache'
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_ENVIRONMENTS_NOT_INDEPENDENT')

    def test_build_shared_immutable_audited_proof_base(self):
        records = self.builds()
        for record in records:
            record['shared_audited_proof_base'] = 'immutable-proof-image'
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_BUILD_ENVIRONMENTS_NOT_INDEPENDENT')

    def test_build_duplicate_invocation(self):
        records = self.builds()
        records[-1]['invocation_id'] = records[0]['invocation_id']
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_RECEIPT_SCOPE_REUSED')

    def test_build_shared_configuration_workspace(self):
        records = self.builds()
        records[1]['workspace_id'] = records[0]['workspace_id']
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_CONFIGURATION_MUTABLE_WORKSPACE_SHARED')

    def test_opaque_precompiled_cache_blocks(self):
        records = self.builds()
        records[0]['precompiled_audited_proofs'] = True
        self.rejected(audit.rule_builds(records, self.claims, 'a' * 64), 'QRH003_UNVERIFIED_PRECOMPILED_CACHE')

    def formal_records(self):
        declaration = {'type_sha256': '1' * 64, 'definition_closure_sha256': '2' * 64,
                       'universe_safety_sha256': '3' * 64}
        return [{'theorem': name, 'challenge': copy.deepcopy(declaration),
                 'solution': copy.deepcopy(declaration), 'kernel_check_state': 'ACCEPTED',
                 'comparator_compatibility_state': 'VERIFIED'} for name in self.exports]

    def test_formal_equality_control(self):
        self.assertEqual('VERIFIED', audit.rule_formal_match(self.formal_records(), self.exports)['state'])

    def test_formal_weakening_cannot_hide_under_same_filename(self):
        records = self.formal_records()
        records[0]['solution']['type_sha256'] = '4' * 64
        self.rejected(audit.rule_formal_match(records, self.exports), 'QRH003_FORMAL_DECLARATION_OR_DEFINITION_MISMATCH')

    def test_changed_definition_with_same_type_blocks(self):
        records = self.formal_records()
        records[0]['solution']['definition_closure_sha256'] = '4' * 64
        self.rejected(audit.rule_formal_match(records, self.exports), 'QRH003_FORMAL_DECLARATION_OR_DEFINITION_MISMATCH')

    def test_comparator_compatibility_cannot_be_assumed(self):
        records = self.formal_records()
        records[0]['comparator_compatibility_state'] = 'NOT_VERIFIED'
        self.rejected(audit.rule_formal_match(records, self.exports), 'QRH003_COMPARATOR_COMPATIBILITY_UNVERIFIED')

    def projection(self):
        return [{'theorem': name, 'type_sha256': '1' * 64, 'definition_closure_sha256': '2' * 64,
                 'axioms': ['propext'], 'universe_safety_sha256': '3' * 64,
                 'kernel_check_state': 'ACCEPTED'} for name in self.exports]

    def test_projection_may_ignore_record_order(self):
        a = self.projection()
        self.assertEqual('VERIFIED', audit.rule_projection(a, list(reversed(a)))['state'])

    def test_projection_must_not_hide_axiom_change(self):
        a, b = self.projection(), self.projection()
        # Both sides remain inside the permitted standard axiom allowlist.
        # The projection must detect a difference even if each axiom gate passes.
        b[0]['axioms'].append('Classical.choice')
        self.rejected(audit.rule_projection(a, b), 'QRH003_CROSS_RUN_SEMANTIC_PROJECTION_MISMATCH')

    def test_projection_must_include_definitions(self):
        a, b = self.projection(), self.projection()
        del b[0]['definition_closure_sha256']
        self.rejected(audit.rule_projection(a, b), 'QRH003_CROSS_RUN_PROJECTION_INCOMPLETE')

    def reviews(self):
        return [{'role': role, 'person_id': 'person-' + role, 'scope_digest': 'a' * 64,
                 'authored_subject': False, 'identity_authenticated': True,
                 'competence_verified': True, 'conflicts_cleared': True}
                for role in ('lean', 'mathematical_domain')]

    def test_stale_review_content_blocks(self):
        records = self.reviews()
        records[0]['scope_digest'] = 'b' * 64
        self.rejected(audit.rule_review(records, 'a' * 64, []), 'QRH003_LEAN_REVIEW_SCOPE_STALE')

    def test_one_person_two_keys_is_not_two_reviewers(self):
        records = self.reviews()
        records[1]['person_id'] = records[0]['person_id']
        records[0]['key_id'], records[1]['key_id'] = 'different-key-a', 'different-key-b'
        self.rejected(audit.rule_review(records, 'a' * 64, []), 'QRH003_REVIEW_ROLES_SAME_PERSON')

    def test_author_cannot_self_certify_independence(self):
        records = self.reviews()
        self.rejected(audit.rule_review(records, 'a' * 64, [records[0]['person_id']]),
                      'QRH003_REVIEWER_AUTHORED_AUDITED_OBJECT')

    def test_unknown_competence_or_conflict_blocks(self):
        records = self.reviews()
        records[0]['conflicts_cleared'] = None
        self.rejected(audit.rule_review(records, 'a' * 64, []),
                      'QRH003_REVIEWER_INDEPENDENCE_OR_COMPETENCE_UNRESOLVED')

    def test_no_silent_promotion_from_presence_to_proof_or_community(self):
        profile = {'critical_artifacts': [], 'configurations': self.configs}
        snapshot = {'manifest': {'trust_domain': 'PRODUCTION'}, 'receipts': [],
                    'files': {'profile.json': canonical_bytes(profile)}}
        result = audit.evaluate(snapshot, {}, 'technical')
        for gate in audit.GATE_IDS[2:]:
            self.assertIs(result['gates'][gate], False)
        self.assertEqual('NOT_ASSESSED', result['states']['community_acceptance']['state'])
        self.assertEqual('NOT_RUN', result['states']['clean_build_reproduced']['state'])

    def test_signed_producer_build_not_implemented_production_route(self):
        from common import AuditError
        snapshot = {'manifest': {'trust_domain': 'PRODUCTION'},
                    'receipts': [{'kind': 'build_execution'}],
                    'files': {'profile.json': canonical_bytes({})}}
        with self.assertRaises(AuditError) as result:
            audit.evaluate(snapshot, {}, 'technical')
        self.assertEqual('QRH003_PRODUCTION_CAPTURE_ADAPTER_UNIMPLEMENTED', result.exception.code)


if __name__ == '__main__':
    unittest.main()
