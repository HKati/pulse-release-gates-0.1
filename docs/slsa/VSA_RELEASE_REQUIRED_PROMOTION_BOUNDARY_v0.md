# PULSE SLSA VSA — recorded-intake candidate → release-required promotion boundary v0

## WORKMARK

Status: candidate path proven, not release-required.

This document records the stable SLSA VSA recorded-intake candidate state and the boundary that must hold before any future release-required promotion is considered.

## Completed PR sequence

- #2689 — `feat(slsa): register vsa recorded-intake candidate set` ✅
- #2690 — `feat(policy): allow materializing declared gate sets` ✅
- #2691 — `feat(slsa): prove vsa recorded-intake candidate path` ✅

## Stable chain

- SLSA / in-toto evidence intake docs ✅
- SLSA VSA evidence contract ✅
- SLSA VSA intake verifier ✅
- SLSA VSA status fold-in ✅
- SLSA VSA advisory policy gates ✅
- SLSA VSA recorded-intake candidate registration ✅
- Declared gate-set materializer support ✅
- SLSA VSA recorded-intake candidate proof ✅

## Proven candidate path

```text
example evidence
→ ingest_slsa_vsa_evidence_v0.py
→ intake report
→ fold_slsa_vsa_intake_into_status_v0.py
→ status.gates
→ policy_to_require_args.py --set slsa_vsa_recorded_intake_candidate
→ check_gates.py PASS / FAIL proof
```

## Candidate set

```text
slsa_vsa_recorded_intake_candidate
```

Expected gates:

```text
slsa_vsa_present
slsa_vsa_signature_ok
slsa_vsa_subject_matches_artifact
slsa_vsa_predicate_type_ok
slsa_vsa_verifier_trusted
slsa_vsa_resource_uri_matches
slsa_vsa_policy_digest_matches
slsa_vsa_result_passed
slsa_vsa_verified_level_ok
```

## Current boundary

The candidate path is proven, but SLSA VSA is not active release-required enforcement.

The SLSA VSA gates must not be treated as active through:

```text
required
core_required
release_required
prod_required
stage_required
blocking
release_blocking
```

## No current release-authority change

The completed candidate work does not change release-authority behavior.

It does not change:

```text
pulse_gate_policy_v0.yml
PULSE_safe_pack_v0/tools/check_gates.py
.github/workflows/
release_decision_v0 semantics
status.json semantics
```

## Promotion boundary

Any future promotion to an active release-required SLSA lane must be a separate PR.

Before promotion, the repo must define and review:

1. trusted recorded evidence producer requirements;
2. the provenance boundary for evidence accepted by CI;
3. the rule that release-required gates must not be self-declared booleans;
4. the rule that advisory signals cannot be promoted without recorded evidence binding;
5. fail-closed behavior for missing, false, stale, or mismatched VSA evidence;
6. rollback behavior if evidence production fails;
7. the explicit release-authority effect of promotion.

## Anti-confusion rule

Candidate proof is not release-required activation.

Materialized candidate gates prove the path can be checked.

They do not by themselves authorize release blocking or release allowing behavior.

## Next possible PR

```text
docs(slsa): define vsa release-required promotion criteria
```

or, only after criteria are accepted:

```text
feat(slsa): promote vsa recorded-intake to release-required
```

The promotion PR must not be combined with unrelated DOI, Zenodo, citation, README, workflow, or registry work.
