# Refusal-Delta Evidence Presence Gate v1

## Purpose

This document defines the PULSE-REF plan for promoting `refusal_delta_evidence_present` into release-grade evidence-presence enforcement.

The purpose is to prevent this state from passing release-grade validation:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

A passing refusal-delta gate result must not substitute for missing materialized refusal-delta evidence.

This document prepares the policy change.

It does not modify release authority by itself.

## Current status

The current PULSE-REF fixture and regression layer already demonstrates the target behavior through:

```text
tests/fixtures/release_reference_v1/missing_refusal_delta/status.json
tests/fixtures/release_reference_v1/missing_refusal_delta/expected_outcome.json
tests/test_no_implicit_pass_release_grade.py
```

The fixture sets:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

and the dedicated regression test runs the PULSE-REF guard with:

```bash
--require-gate refusal_delta_evidence_present
```

Expected result:

```text
FAIL
```

This proves the desired release-grade behavior without changing the global gate policy yet.

## Authority boundary

This document does not define release authority.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

The normative path remains:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

This document describes a planned evidence-presence gate promotion.

It does not authorize release, block release, replace `check_gates.py`, or make documentation, fixtures, ledgers, manifests, audit bundles, dashboards, summaries, or publication surfaces normative.

## Core rule

Release-grade paths must not infer PASS from missing refusal-delta evidence.

The following state must fail release-grade validation:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

The required release-grade state is:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
```

## Why this gate is needed

`refusal_delta_pass` records whether the refusal-delta gate passed.

It does not prove that refusal-delta evidence exists.

`refusal_delta_evidence_present` records whether the evidence required to support the refusal-delta result is materialized.

These are separate claims.

For release-grade paths, both must be true when refusal-delta behavior is release-relevant.

## Current fixture proof

The current negative fixture is:

```text
release_reference_v1/missing_refusal_delta
```

It isolates:

```text
refusal_delta_evidence_present = false
```

while keeping non-target gates passing:

```text
refusal_delta_pass = true
detectors_materialized_ok = true
external_summaries_present = true
external_all_pass = true
diagnostics.gates_stubbed = false
```

The dedicated test proves that when `refusal_delta_evidence_present` is required, the fixture fails for the intended reason.

## Current matrix support

The release-reference fixture matrix supports fixture-specific extra required gates through:

```json
"expected_extra_required_gates": [
  "refusal_delta_evidence_present"
]
```

The matrix passes this to the PULSE-REF guard as:

```bash
--require-gate refusal_delta_evidence_present
```

This allows PULSE-REF to test the desired release-grade behavior before global policy promotion.

## Proposed policy promotion

The planned policy promotion is to include:

```text
refusal_delta_evidence_present
```

in the release-grade required gate set when refusal-delta is release-relevant.

Potential policy shape:

```yaml
gates:
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
    - refusal_delta_evidence_present
```

or an equivalent declared release-grade policy section.

## Promotion prerequisites

Before adding `refusal_delta_evidence_present` globally to release-grade policy, the following must be true:

- `missing_refusal_delta` fixture exists and passes matrix validation.
- `tests/test_no_implicit_pass_release_grade.py` passes.
- Release-reference fixture matrix supports extra required gates.
- Existing release-reference fixtures still pass or fail for their intended isolated reasons.
- External summary and envelope fixture matrices still pass.
- The change is documented as a release-grade evidence-presence hardening step.
- The policy change PR explicitly states that release-authority semantics remain declared-policy based.

## Expected behavior after promotion

After policy promotion, release-grade validation should fail whenever:

```text
refusal_delta_evidence_present != true
```

This includes:

- missing gate;
- false gate;
- null value;
- string `"true"`;
- numeric `1`;
- malformed evidence;
- diagnostic-only evidence;
- advisory-only evidence not promoted by declared policy.

PASS requires literal boolean:

```text
refusal_delta_evidence_present = true
```

## Non-release-grade behavior

Legacy, demo, advisory, or diagnostic paths may retain non-release-grade behavior if explicitly labeled.

Such paths must not be confused with release-grade validation.

Permissive behavior must be marked as:

```text
legacy
advisory
diagnostic
non-authoritative
not release-grade
```

Release-grade paths must not inherit permissive fallback semantics.

## Required tests for policy promotion

The policy promotion PR should run:

```bash
python tests/test_no_implicit_pass_release_grade.py
python tests/test_release_reference_fixture_matrix_v1.py
python tests/test_external_summary_envelope_fixture_matrix_v1.py
python tests/test_external_summary_schema_v1.py
python tests/test_external_summary_fixture_matrix_v1.py
```

It should also run a direct guard check:

```bash
python ci/check_release_reference_complete_v1.py \
  --status tests/fixtures/release_reference_v1/missing_refusal_delta/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-detectors-materialized \
  --require-external-summaries \
  --require-gate refusal_delta_evidence_present
```

Expected result:

```text
FAIL
```

Expected failure target:

```text
refusal_delta_evidence_present
```

## Required negative fixture

The required negative fixture is:

```text
tests/fixtures/release_reference_v1/missing_refusal_delta/
```

It must contain:

```text
status.json
expected_outcome.json
```

The expected failure must remain isolated to:

```text
refusal_delta_evidence_present
```

## Required positive fixture target

A future positive fixture may be added:

```text
tests/fixtures/release_reference_v1/refusal_delta_evidence_present/
```

Expected state:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
```

Expected result:

```text
PASS
```

This positive fixture is useful before or alongside global policy promotion.

## Rollout plan

Recommended rollout:

1. Keep `refusal_delta_evidence_present` as fixture-specific extra required gate.
2. Add this promotion plan document.
3. Add a positive fixture where refusal-delta evidence is present.
4. Update `pulse_gate_policy_v0.yml` to include `refusal_delta_evidence_present` in release-grade required gates.
5. Re-run all release-reference and external evidence fixture matrices.
6. Confirm no fixture fails for an unrelated reason.
7. Merge only if the authority boundary remains unchanged.

## Risk

Policy promotion risk is moderate because it changes release-grade required-gate behavior.

The risk is acceptable if the change is:

- explicit;
- documented;
- covered by fixtures;
- covered by direct guard tests;
- limited to release-grade semantics;
- not applied silently to legacy / diagnostic paths.

## Rollback

If policy promotion causes unintended release-grade failures, rollback should remove `refusal_delta_evidence_present` from the global release-required gate set while keeping:

- the `missing_refusal_delta` fixture;
- `tests/test_no_implicit_pass_release_grade.py`;
- this policy promotion document.

This preserves the hardening target while allowing policy rollout to be retried safely.

## Non-goals

This plan does not:

- replace `check_gates.py`;
- make fixture metadata normative;
- make docs normative;
- make refusal-delta diagnostics release authority;
- make ledgers, manifests, audit bundles, dashboards, summaries, or publication surfaces release authority;
- silently change legacy / advisory behavior.

## Summary

`refusal_delta_evidence_present` is the release-grade evidence-presence gate for refusal-delta evidence.

It prevents this unsafe release-grade state:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

from becoming PASS.

The gate should be promoted only through declared policy, with explicit fixture coverage and regression tests.

This strengthens PULSE-REF without creating a second release-decision engine.
