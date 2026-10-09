"""Deterministic, conservative evidence-to-status adapter for QRH 003.

v0.1 authenticates source observations and execution preflight. Native proof
capture is deliberately not an admitted production route until implemented and
validated on a conforming runner. Its absence remains a required-gate failure.
Content rules below can be exercised under TEST; they cannot promote TEST
records or arbitrary signed producer reports into production proof evidence.
"""
from __future__ import annotations

from collections import Counter
import json

try:
    from .common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                         canonical_bytes, sha256_bytes, strict_loads)
except ImportError:
    from common import (AuditError, GATE_IDS, SUBJECT_COMMIT, PULSE_COMMIT,
                        canonical_bytes, sha256_bytes, strict_loads)

STATE_NAMES = (
    "claim_released", "artifact_identity_bound", "formalization_present",
    "formalization_scope_bound", "dependency_closure_complete",
    "clean_build_reproduced", "axiom_profile_verified",
    "claim_to_theorem_binding_verified", "independent_lean_review",
    "independent_mathematical_domain_review", "community_acceptance",
)
CLAIM_IDS = ("qrh003_zeta", "qrh003_dirichlet", "qrh003_hecke_qsqrt_minus3",
             "qrh003_siegel_uniform")
AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})
PRODUCTION_KINDS = frozenset({"source_identity", "dependency_inventory",
    "source_closure", "scope_binding", "execution_preflight",
    "authority_boundary_tests", "run_failure"})


def outcome(ok, reasons=(), refs=(), *, success="VERIFIED", failure="BLOCK"):
    return {"state": success if ok else failure, "reason_codes": list(reasons),
            "evidence_refs": list(refs)}


def rule_scope(configurations, expected, declared_claims, declared_exports):
    """Source-level coverage only; equality here is not Lean elaboration."""
    if (set(declared_claims) != set(CLAIM_IDS) or len(declared_claims) != 4
            or set(declared_exports) != {n for c in expected for n in c['theorem_exports']}
            or len(declared_exports) != 5 or len(configurations) != 4):
        return outcome(False, ["QRH003_CLAIM_OR_EXPORT_OMITTED"])
    for actual, wanted in zip(configurations, expected):
        for name in ("claim_id", "path", "sha256", "challenge_module",
                     "solution_module", "theorem_exports"):
            if actual.get(name) != wanted.get(name):
                return outcome(False, ["QRH003_SCOPE_MAPPING_MISMATCH"])
    return outcome(True, success="SOURCE_MAP_BOUND")


def rule_axioms(records, expected_exports, standard_declarations):
    """A TESTable content rule, not a substitute for authenticated kernel capture."""
    if not records or {r.get('theorem') for r in records} != set(expected_exports):
        return outcome(False, ["QRH003_AXIOM_EXPORT_OMITTED"])
    if len(records) != len(expected_exports):
        return outcome(False, ["QRH003_RECEIPT_SCOPE_REUSED"])
    for record in records:
        axioms = record.get("axioms")
        if not isinstance(axioms, list) or any(not isinstance(a, dict) for a in axioms):
            return outcome(False, ["QRH003_AXIOM_RECORD_INVALID"])
        names = [a.get("name") for a in axioms]
        if "sorryAx" in names:
            return outcome(False, ["QRH003_SOLUTION_SORRYAX_REACHABLE"])
        if len(names) != len(set(names)) or not set(names) <= AXIOMS:
            return outcome(False, ["QRH003_AXIOM_OR_DECLARATION_NOT_ALLOWED"])
        for axiom in axioms:
            expected = standard_declarations.get(axiom['name'])
            if not expected or axiom.get("declaration_sha256") != expected:
                return outcome(False, ["QRH003_AXIOM_OR_DECLARATION_NOT_ALLOWED"])
        if record.get("kernel_check_state") != "ACCEPTED":
            return outcome(False, ["QRH003_KERNEL_RESULT_UNVERIFIED"])
    return outcome(True)


def rule_builds(records, configuration_ids, toolchain_sha256):
    expected = {(build, config) for build in ("A", "B") for config in configuration_ids}
    if {(r.get("build_id"), r.get("configuration_id")) for r in records} != expected:
        return outcome(False, ["QRH003_BUILD_CONFIGURATION_OMITTED"])
    if len(records) != len(expected):
        return outcome(False, ["QRH003_RECEIPT_SCOPE_REUSED"])
    invocations, workspaces = [], []
    identities = {"A": set(), "B": set()}
    cache_lineage = {"A": set(), "B": set()}
    for record in records:
        if (record.get("timed_out") is not False or record.get("oom_killed") is not False
                or record.get("resource_failure") is not False):
            return outcome(False, ["QRH003_BUILD_RESOURCE_FAILURE"])
        if type(record.get("return_code")) is not int or record["return_code"] != 0:
            return outcome(False, ["QRH003_BUILD_EXIT_NONZERO"])
        if record.get("toolchain_sha256") != toolchain_sha256 or not toolchain_sha256:
            return outcome(False, ["QRH003_TOOLCHAIN_BINARY_BINDING_MISMATCH"])
        if record.get("precompiled_audited_proofs") is not False:
            return outcome(False, ["QRH003_UNVERIFIED_PRECOMPILED_CACHE"])
        if record.get("shared_audited_proof_base") is not None:
            return outcome(False, ["QRH003_BUILD_ENVIRONMENTS_NOT_INDEPENDENT"])
        for key in ("invocation_id", "workspace_id", "environment_id", "cache_lineage_id"):
            if not isinstance(record.get(key), str) or not record[key]:
                return outcome(False, ["QRH003_BUILD_IDENTITY_INCOMPLETE"])
        invocations.append(record['invocation_id'])
        workspaces.append(record['workspace_id'])
        identities[record['build_id']].add(record['environment_id'])
        cache_lineage[record['build_id']].add(record['cache_lineage_id'])
    if len(set(invocations)) != len(invocations):
        return outcome(False, ["QRH003_RECEIPT_SCOPE_REUSED"])
    if len(set(workspaces)) != len(workspaces):
        return outcome(False, ["QRH003_CONFIGURATION_MUTABLE_WORKSPACE_SHARED"])
    if identities['A'] & identities['B'] or cache_lineage['A'] & cache_lineage['B']:
        return outcome(False, ["QRH003_BUILD_ENVIRONMENTS_NOT_INDEPENDENT"])
    return outcome(True)


def rule_formal_match(records, expected_exports):
    if {r.get('theorem') for r in records} != set(expected_exports) or len(records) != len(expected_exports):
        return outcome(False, ["QRH003_FORMAL_EXPORT_OMITTED"])
    for record in records:
        if record.get('comparator_compatibility_state') != 'VERIFIED':
            return outcome(False, ["QRH003_COMPARATOR_COMPATIBILITY_UNVERIFIED"])
        for name in ('type_sha256', 'definition_closure_sha256', 'universe_safety_sha256'):
            challenge = record.get('challenge', {}).get(name)
            solution = record.get('solution', {}).get(name)
            if not challenge or challenge != solution:
                return outcome(False, ["QRH003_FORMAL_DECLARATION_OR_DEFINITION_MISMATCH"])
        if record.get('kernel_check_state') != 'ACCEPTED':
            return outcome(False, ["QRH003_KERNEL_RESULT_UNVERIFIED"])
    return outcome(True)


def rule_projection(build_a, build_b):
    """The projection is explicit, and omission of any semantic component blocks."""
    required = {'theorem', 'type_sha256', 'definition_closure_sha256', 'axioms',
                'universe_safety_sha256', 'kernel_check_state'}
    for side in (build_a, build_b):
        if not side or any(set(record) != required for record in side):
            return outcome(False, ['QRH003_CROSS_RUN_PROJECTION_INCOMPLETE'])
    ordered = lambda records: sorted(records, key=lambda row: row['theorem'])
    if canonical_bytes(ordered(build_a)) != canonical_bytes(ordered(build_b)):
        return outcome(False, ['QRH003_CROSS_RUN_SEMANTIC_PROJECTION_MISMATCH'])
    return outcome(True)


def rule_review(records, scope_digest, subject_authors):
    if not isinstance(records, list) or len(records) != 2:
        return outcome(False, ["QRH003_INDEPENDENT_REVIEW_MISSING"])
    if {r.get('role') for r in records} != {'lean', 'mathematical_domain'}:
        return outcome(False, ["QRH003_INDEPENDENT_REVIEW_MISSING"])
    if len({r.get('person_id') for r in records}) != 2:
        return outcome(False, ["QRH003_REVIEW_ROLES_SAME_PERSON"])
    for record in records:
        if record.get('scope_digest') != scope_digest:
            return outcome(False, ["QRH003_LEAN_REVIEW_SCOPE_STALE"])
        if record.get('person_id') in subject_authors or record.get('authored_subject') is not False:
            return outcome(False, ["QRH003_REVIEWER_AUTHORED_AUDITED_OBJECT"])
        if (record.get('identity_authenticated') is not True or
                record.get('competence_verified') is not True or
                record.get('conflicts_cleared') is not True):
            return outcome(False, ["QRH003_REVIEWER_INDEPENDENCE_OR_COMPETENCE_UNRESOLVED"])
    return outcome(True)


def _observation(snapshot, kind):
    records = [r for r in snapshot['receipts'] if r.get('kind') == kind]
    if len(records) != 1:
        return None, []
    body = records[0].get('body', {})
    path = body.get('observation_path')
    data = snapshot['files'].get(path)
    if not isinstance(data, bytes) or sha256_bytes(data) != body.get('observation_sha256'):
        raise AuditError('QRH003_EVIDENCE_REFERENCE_INVALID', kind)
    result = strict_loads(data)
    if not isinstance(result, dict):
        raise AuditError('QRH003_OBSERVATION_NOT_OBJECT', kind)
    return result, [path]


def source_anchor_check(files, mapping):
    """Recheck each declared manuscript/scope/signature slice from frozen bytes.

    External definition references are identifiers in the scope map; their
    semantic meaning is not certified by this syntactic slice operation.
    """
    sources = mapping.get('source_artifacts', {})
    checked, reasons = 0, []
    def visit(node):
        nonlocal checked
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            required = {'source_ref', 'byte_start_0_based', 'byte_end_exclusive', 'excerpt_raw_sha256'}
            if required <= set(node):
                source = sources.get(node['source_ref'], {})
                if source.get('repository') == 'https://github.com/openai/math':
                    raw = files.get('upstream/' + source.get('path', ''))
                    start, end = node['byte_start_0_based'], node['byte_end_exclusive']
                    if (raw is None or type(start) is not int or type(end) is not int
                            or start < 0 or end < start or end > len(raw)
                            or sha256_bytes(raw[start:end]) != node['excerpt_raw_sha256']
                            or source.get('commit') != SUBJECT_COMMIT):
                        reasons.append('QRH003_SOURCE_STATEMENT_ANCHOR_MISMATCH')
                    else:
                        checked += 1
            for value in node.values():
                visit(value)
    visit(mapping.get('claims', []))
    if checked == 0:
        reasons.append('QRH003_SOURCE_STATEMENT_ANCHORS_MISSING')
    return {'checked_source_slices': checked, 'reason_codes': sorted(set(reasons)),
            'semantic_correspondence': 'NOT_REVIEWED'}


def evaluate(snapshot, anchor, profile_kind):
    manifest, files = snapshot['manifest'], snapshot['files']
    profile = strict_loads(files['profile.json'])
    for record in snapshot['receipts']:
        if manifest['trust_domain'] == 'PRODUCTION' and record['kind'] not in PRODUCTION_KINDS:
            raise AuditError('QRH003_PRODUCTION_CAPTURE_ADAPTER_UNIMPLEMENTED', record['kind'])
    evaluations = {name: outcome(False, ['QRH003_EVIDENCE_NOT_PRESENT'], failure='NOT_RUN')
                   for name in GATE_IDS}

    identity, identity_refs = _observation(snapshot, 'source_identity')
    critical = profile.get('critical_artifacts', [])
    identity_reasons = []
    if not critical or identity is None:
        identity_reasons.append('QRH003_SUBJECT_CRITICAL_FILE_MISSING')
    if identity is not None:
        if identity.get('expected_commit') != SUBJECT_COMMIT:
            identity_reasons.append('QRH003_SUBJECT_COMMIT_MISMATCH')
        if identity.get('source_identity_status') != 'VERIFIED':
            identity_reasons.append('QRH003_GIT_IDENTITY_NOT_VERIFIED')
    for item in critical:
        raw = files.get('upstream/' + item['path'])
        if raw is None:
            identity_reasons.append('QRH003_SUBJECT_CRITICAL_FILE_MISSING')
        elif sha256_bytes(raw) != item['sha256'] or len(raw) != item['bytes']:
            identity_reasons.append('QRH003_SUBJECT_DIGEST_MISMATCH')
    evaluations[GATE_IDS[0]] = outcome(not identity_reasons, sorted(set(identity_reasons)), identity_refs)

    scope, scope_refs = _observation(snapshot, 'scope_binding')
    if scope is not None:
        scope_result = rule_scope(scope.get('configurations', []), profile['configurations'],
                                 scope.get('claim_ids', []), scope.get('theorem_exports', []))
        scope_result['evidence_refs'] = scope_refs
        evaluations[GATE_IDS[1]] = scope_result
        mapping_bytes = files.get('claim_map.json')
        if mapping_bytes is None or sha256_bytes(mapping_bytes) != profile.get('claim_map_sha256'):
            evaluations[GATE_IDS[1]] = outcome(False, ['QRH003_CLAIM_MAP_DIGEST_MISMATCH'], scope_refs)
        else:
            anchors = source_anchor_check(files, strict_loads(mapping_bytes))
            if anchors['reason_codes']:
                evaluations[GATE_IDS[1]] = outcome(False, anchors['reason_codes'], scope_refs + ['claim_map.json'])
        for config in profile['configurations']:
            raw = files.get('upstream/' + config['path'])
            if raw is None or sha256_bytes(raw) != config['sha256']:
                evaluations[GATE_IDS[1]] = outcome(False, ['QRH003_SCOPE_MAPPING_MISMATCH'], scope_refs)
                break
            parsed = strict_loads(raw)
            if (parsed.get('challenge_module') != config['challenge_module'] or
                    parsed.get('solution_module') != config['solution_module'] or
                    parsed.get('theorem_names') != config['theorem_exports'] or
                    parsed.get('definition_names') != [] or
                    set(parsed.get('permitted_axioms', [])) != AXIOMS):
                evaluations[GATE_IDS[1]] = outcome(False, ['QRH003_SCOPE_MAPPING_MISMATCH'], scope_refs)
                break

    closure, closure_refs = _observation(snapshot, 'source_closure')
    dependencies, dependency_refs = _observation(snapshot, 'dependency_inventory')
    closure_reasons = []
    if closure is None:
        closure_reasons.append('QRH003_SOURCE_CLOSURE_NOT_RETRIEVED')
    else:
        details_path = closure.get('acquisition_details_path')
        details_bytes = files.get(details_path)
        if details_bytes is None or sha256_bytes(details_bytes) != closure.get('acquisition_details_sha256'):
            raise AuditError('QRH003_ACQUISITION_DETAIL_BINDING_INVALID')
        if closure.get('discovery_status') != 'MATCH':
            closure_reasons.append('QRH003_SOURCE_IMPORT_UNRESOLVED')
        if closure.get('source_identity_status') != 'VERIFIED':
            closure_reasons.append('QRH003_SOURCE_IDENTITY_INCOMPLETE')
        if closure.get('provider_universe_status') != 'MATCH':
            closure_reasons.append('QRH003_PROVIDER_UNIVERSE_PARTIAL')
    if dependencies is None or dependencies.get('discovery_status') != 'MATCH':
        closure_reasons.append('QRH003_LOCKED_DEPENDENCY_RETRIEVAL_PARTIAL')
    # Preserve the original gate's stronger meaning: a static fixed point
    # alone never establishes actual Lean/Lake source resolution.
    closure_reasons.append('QRH003_COMPILER_SOURCE_RESOLUTION_NOT_RUN')
    evaluations[GATE_IDS[2]] = outcome(not closure_reasons, closure_reasons, closure_refs + dependency_refs,
                                      failure='INCOMPLETE')

    # No native proof execution happened in this implementation's production
    # collector. A producer cannot add all-true build JSON to fill this gap.
    for name in GATE_IDS[3:7]:
        evaluations[name] = outcome(False, ['QRH003_NATIVE_PROOF_CAPTURE_NOT_IMPLEMENTED'], failure='NOT_RUN')
    preflight, preflight_refs = _observation(snapshot, 'execution_preflight')
    if preflight is not None:
        # Even successful preflight is only a necessary condition. Actual
        # protected execution must also be captured by a validated adapter.
        reasons = list(preflight.get('reason_codes', []))
        reasons.append('QRH003_PROTECTED_PROOF_EXECUTION_NOT_OBSERVED')
        evaluations[GATE_IDS[7]] = outcome(False, reasons, preflight_refs, failure='BLOCK')
    evaluations[GATE_IDS[8]] = outcome(False,
        ['QRH003_AB_INVOCATION_BINDING_AND_SEMANTIC_PROJECTION_NOT_RUN'],
        ['profile.json', 'policy.yml', 'gate_registry.yml'], failure='INCOMPLETE')

    boundary, boundary_refs = _observation(snapshot, 'authority_boundary_tests')
    if boundary is not None:
        required = set(profile.get('required_boundary_test_ids', []))
        observed = boundary.get('tests', [])
        passed = {r.get('id') for r in observed if r.get('outcome') == 'PASS'}
        ok = (bool(required) and required <= passed and boundary.get('return_code') == 0
              and type(boundary.get('return_code')) is int
              and boundary.get('timed_out') is False
              and len(observed) == len({r.get('id') for r in observed})
              and all(r.get('outcome') == 'PASS' for r in observed))
        evaluations[GATE_IDS[9]] = outcome(ok, [] if ok else ['QRH003_BOUNDARY_TEST_COVERAGE_INCOMPLETE'], boundary_refs)
    for name in GATE_IDS[10:]:
        evaluations[name] = outcome(False, ['QRH003_INDEPENDENT_SEMANTIC_REVIEW_NOT_PRESENT'], failure='NOT_REVIEWED')
    failure, failure_refs = _observation(snapshot, 'run_failure')
    if failure is not None:
        for name in GATE_IDS[2:10]:
            evaluations[name] = outcome(False,
                sorted(set(evaluations[name]['reason_codes'] + ['QRH003_COLLECTION_PARTIAL_FAILURE'])),
                evaluations[name]['evidence_refs'] + failure_refs, failure='INCOMPLETE')
    gates = {name: evaluations[name]['state'] in ('VERIFIED', 'SOURCE_MAP_BOUND') for name in GATE_IDS}
    states = {
        'claim_released': outcome(evaluations[GATE_IDS[0]]['state'] == 'VERIFIED', [], identity_refs, success='RECORDED', failure='UNKNOWN'),
        'artifact_identity_bound': evaluations[GATE_IDS[0]],
        'formalization_present': outcome(bool(scope), [], scope_refs, success='RECORDED', failure='UNKNOWN'),
        'formalization_scope_bound': evaluations[GATE_IDS[1]],
        'dependency_closure_complete': evaluations[GATE_IDS[2]],
        'clean_build_reproduced': evaluations[GATE_IDS[4]],
        'axiom_profile_verified': evaluations[GATE_IDS[6]],
        'claim_to_theorem_binding_verified': outcome(False, ['QRH003_SOURCE_MAP_ONLY_NO_ELABORATION_OR_REVIEW'], scope_refs, failure='INCOMPLETE'),
        'independent_lean_review': evaluations[GATE_IDS[11]],
        'independent_mathematical_domain_review': evaluations[GATE_IDS[12]],
        'community_acceptance': outcome(False, ['QRH003_COMMUNITY_ACCEPTANCE_NOT_ASSESSED'], failure='NOT_ASSESSED'),
    }
    return {'gates': gates, 'evaluations': evaluations, 'states': states,
            'limitations': [
        'v0.1 admits actual source/preflight/boundary observations; native proof capture is not implemented or admitted.',
        'The source import graph is static; it is not a compiler-resolved build closure.',
        'An Ed25519 receipt authenticates an authorized local collector statement under the declared host TCB.',
        'External anchor custody and reviewer independence are not established by a locally generated key.',
        'No QRH Lean build, Comparator execution, target axiom audit, or independent expert review is implied.',
        'The complete manuscript and later applications are outside any technical certificate claim.',
        'A verified BLOCK report is not a proof that the mathematical claim is false.',
    ]}


def build_status(snapshot, anchor, evaluation, anchor_sha256, profile_kind):
    m = snapshot['manifest']
    return {
        'version': 'qrh003_runtime_status_v1', 'created_utc': m['created_utc'],
        'gates': evaluation['gates'],
        'metrics': {'run_mode': 'core', 'application_profile': 'openai_math_003_qrh_v0',
                    'run_key': m['run_key'], 'git_sha': PULSE_COMMIT},
        'qrh': {
            'subject_commit': SUBJECT_COMMIT, 'pulse_commit': PULSE_COMMIT,
            'trust_domain': m['trust_domain'], 'profile_kind': profile_kind,
            'evidence_manifest_sha256': snapshot['evidence_manifest_sha256'],
            'manifest_signature_sha256': snapshot.get('manifest_signature_sha256'),
            'anchor_sha256': anchor_sha256, 'profile_sha256': anchor['profile_sha256'],
            'policy_sha256': anchor['policy_sha256'], 'registry_sha256': anchor['registry_sha256'],
            'evaluations': evaluation['evaluations'], 'states': evaluation['states'],
            'limitations': evaluation['limitations'], 'authority_granted_by_this_status': False,
            'community_acceptance_is_derived': False,
            'transition_meter': {
                'relation_change_observation_status': 'OBSERVED_ARTIFACT_RELATIONS_ONLY',
                'transition_path_verification_status': 'PARTIAL',
                'endpoint_binding_status': 'INPUT_BOUND_DECISION_REQUIRES_AUTHORITY_REPLAY',
                'time_order_status': 'COLLECTOR_RECORDED_NO_EXTERNAL_TRUSTED_TIMESTAMP',
                'alternative_path_closure_status': 'LOCAL_EMITTER_BOUNDARY_ONLY',
                'reconstruction_reproducibility_status': 'DECISION_REPLAY_REQUIRED',
                'causal_sufficiency_status': 'NOT_APPLICABLE_TO_MATHEMATICAL_TRUTH',
                'causal_necessity_status': 'NOT_APPLICABLE_TO_MATHEMATICAL_TRUTH',
            },
            'implementation_capabilities': {
                'source_identity_collection': True, 'static_source_closure_collection': True,
                'signed_local_observation_capture': True, 'offline_authority_replay': True,
                'native_proof_capture': False, 'independent_lean_review_intake': False,
                'independent_domain_review_intake': False,
            },
            'verified_subconditions': {
                'external_anchor_code_and_policy_binding': 'VERIFIED_BY_INPUT_ADMISSION',
                'native_execution_receipt_uniqueness': 'NOT_RUN',
                'ab_semantic_projection': 'NOT_RUN',
            },
        },
    }
