# No Implicit PASS Release-Grade Test v1

## Purpose

This document describes the PULSE-REF no-implicit-PASS release-grade regression test.

The test proves that release-grade validation must not infer PASS from missing materialized evidence.

The current concrete case is refusal-delta evidence:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

Expected release-grade result:

```text
FAIL
```

## Core rule

Release-grade paths must not infer PASS from missing evidence.

In release-grade validation:

```text
missing evidence -> explicit missing / fail state
```

never:

```text
missing evidence -> implicit PASS
```

This is a hardening rule for PULSE-REF release-grade evidence handling.

## Authority boundary

This document does not define release authority.

The no-implicit-PASS test exercises the existing PULSE-REF completeness guard against fixture evidence.

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

The test, fixture metadata, docs, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

## Related policy document

The evidence presence policy is documented in:

```text
docs/evidence_presence_policy_v1.md
```

That document defines the general rule:

```text
release-grade paths must not infer PASS from missing evidence
```

and identifies refusal-delta evidence as a current hardening target.

## Fixture under test

The release-reference fixture is:

```text
tests/fixtures/release_reference_v1/missing_refusal_delta/status.json
tests/fixtures/release_reference_v1/missing_refusal_delta/expected_outcome.json
```

The fixture sets:

```text
metrics.run_mode = prod
diagnostics.gates_stubbed = false
refusal_delta_pass = true
refusal_delta_evidence_present = false
detectors_materialized_ok = true
external_summaries_present = true
external_all_pass = true
```

This isolates the intended failure mode:

```text
refusal_delta_evidence_present = false
```

All non-target gates remain passing.

## Why refusal_delta_pass is insufficient

`refusal_delta_pass=true` records the result of a refusal-delta gate.

It does not, by itself, prove that materialized refusal-delta evidence exists.

For release-grade validation, the evidence-presence requirement is separate:

```text
refusal_delta_evidence_present = true
```

Therefore this state must fail:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

This prevents missing refusal-delta evidence from becoming implicit release-grade PASS.

## Matrix integration

The release-reference fixture metadata declares:

```json
"expected_extra_required_gates": [
  "refusal_delta_evidence_present"
]
```

The release-reference fixture matrix reads this metadata and passes the extra gate to the guard:

```bash
--require-gate refusal_delta_evidence_present
```

This allows the PULSE-REF fixture matrix to model release-grade evidence-presence requirements while preserving the current declared release-grade policy path.

The matrix test is:

```text
tests/test_release_reference_fixture_matrix_v1.py
```

## Dedicated regression test

The dedicated no-implicit-PASS test is:

```text
tests/test_no_implicit_pass_release_grade.py
```

It verifies that:

- the `missing_refusal_delta` fixture is used;
- `refusal_delta_pass=true`;
- `refusal_delta_evidence_present=false`;
- the guard is run with `--require-gate refusal_delta_evidence_present`;
- the guard fails;
- the structured guard error mentions only `refusal_delta_evidence_present`;
- fixture metadata preserves the authority boundary.

## Direct guard command

The direct command is:

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

Expected failure:

```text
refusal_delta_evidence_present is false
```

## Non-goals

This test does not:

- modify `pulse_gate_policy_v0.yml`;
- modify `check_gates.py`;
- modify release-authority semantics;
- fold evidence into `status.json`;
- make fixture metadata normative;
- make documentation normative;
- make dashboards, ledgers, manifests, audit bundles, summaries, or publication surfaces release authority.

## Current related tests

Run:

```bash
python tests/test_no_implicit_pass_release_grade.py
```

The release-reference fixture matrix should also pass:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

External evidence tests should continue to pass:

```bash
python tests/test_external_summary_envelope_fixture_matrix_v1.py
python tests/test_external_summary_schema_v1.py
python tests/test_external_summary_fixture_matrix_v1.py
```

## Current proof point

The current proof point is:

```text
refusal_delta_pass=true
refusal_delta_evidence_present=false
--require-gate refusal_delta_evidence_present
-> FAIL
```

This demonstrates zero implicit PASS behavior for missing refusal-delta evidence.

## Current policy / profile state

The no-implicit-PASS refusal-delta behavior is represented by current repository
evidence.

Current state includes:

```text
pulse_gate_policy_v0.yml
PULSE_safe_pack_v0/profiles/release_grade_reference_v1.yml
tests/fixtures/release_reference_v1/missing_refusal_delta/
tests/fixtures/release_reference_v1/refusal_delta_evidence_present/
tests/test_no_implicit_pass_release_grade.py
tests/test_release_reference_fixture_matrix_v1.py
```

The policy path includes `refusal_delta_evidence_present` in the release-grade
required gate set.

The release-grade reference profile records that refusal-delta evidence is
required when release-required.

The negative fixture proves:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
→ FAIL
```

The positive fixture proves:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
→ PASS
```

Future work should only describe remaining absent coverage or deliberately
separate implementation tracks.

## Summary

The no-implicit-PASS release-grade test proves that a passing result gate cannot
substitute for missing materialized evidence.

For PULSE-REF release-grade validation:

```text
required evidence must be present
required evidence must be materialized
required evidence must be explicit
missing evidence must fail closed
```

The refusal-delta proof now has both negative and positive fixture coverage:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
→ FAIL

refusal_delta_pass = true
refusal_delta_evidence_present = true
→ PASS
```

This strengthens PULSE without creating a second release-decision engine.
