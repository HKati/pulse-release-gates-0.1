# PULSE-REF Fixture Matrix v1

## Purpose

This document describes the initial PULSE-REF release reference fixture matrix.

The fixture matrix validates the PULSE-REF release reference completeness guard against positive and negative evidence-to-decision cases.

The matrix is not a release-decision engine. It is a regression layer for testing whether recorded evidence, declared policy, and materialized gate sets produce the expected deterministic, fail-closed release-grade outcome.

## Current executable matrix

The current executable fixture matrix includes fixture directories that contain both:

- `status.json`
- `expected_outcome.json`

The matrix test discovers those directories and runs:

```bash
python ci/check_release_reference_complete_v1.py \
  --status <fixture>/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-detectors-materialized \
  --require-external-summaries
```

The result is compared against `expected_outcome.json`.

## Active fixture cases

### pass

Expected result: PASS.

Purpose:

Validates that a release-grade candidate passes when:

- run mode is `prod`
- diagnostics are non-stubbed
- detector evidence is materialized
- external summaries are present
- external aggregate is passing
- all `required` gates are literal boolean `true`
- all `release_required` gates are literal boolean `true`

### missing_external

Expected result: FAIL.

Purpose:

Validates fail-closed behavior when external summary presence is missing.

This fixture isolates:

- `external_summaries_present: false`

Non-target gates remain passing, including:

- `external_all_pass: true`
- `detectors_materialized_ok: true`

### stubbed

Expected result: FAIL.

Purpose:

Validates fail-closed behavior when diagnostics indicate stubbed evidence.

This fixture isolates:

- `diagnostics.gates_stubbed: true`

All required and release_required gates remain passing.

### scaffolded

Expected result: FAIL.

Purpose:

Validates fail-closed behavior when diagnostics indicate scaffolded release-grade evidence.

This fixture isolates:

- `diagnostics.scaffold: true`

All required and release_required gates remain passing.

Release-grade reference validation must not infer PASS from scaffolded evidence even when gate values appear passing.

### false_gate

Expected result: FAIL.

Purpose:

Validates strict fail-closed required-gate semantics.

This fixture isolates:

- `pass_controls_refusal: false`

All non-target required gates and all release_required gates remain passing.

### implicit_fallback_attempt

Expected result: FAIL.

Purpose:

Validates fail-closed behavior for non-materialized detector evidence.

This fixture isolates:

- `detectors_materialized_ok: false`

All non-target required gates and all non-target release_required gates remain passing.

## Skeleton fixture categories

The following fixture directories exist as skeletons and will be populated later:

- `malformed_summary`
- `unsigned_summary`
- `stale_artifact`
- `publication_mismatch`
- `agent_diagnostic_promoted`

These are not executed by the matrix until both `status.json` and `expected_outcome.json` are present.

## Failure isolation rule

Each negative fixture is intended to isolate one failure mode.

The matrix test requires FAIL fixtures to declare an expected failure target through:

- `expected_failure.gate`, or
- `expected_failure.field`

For FAIL fixtures, the guard must fail for the expected target, and unrelated extra guard errors must not be present.

This prevents a negative fixture from passing the matrix while masking a different regression.

## Authority boundary

The fixture matrix does not define release authority.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

Fixtures, expected-outcome metadata, benchmark reports, ledgers, dashboards, summaries, release-authority manifests, audit bundles, and publication surfaces do not create a second release-decision path.

## Non-interference

The fixture matrix must preserve non-interference:

- it may test release-grade completeness;
- it may compare actual guard outcomes with expected fixture metadata;
- it may detect regressions in fail-closed behavior;
- it must not authorize, block, override, or reinterpret release outside the declared-policy gate-enforcement path.

## How to run

Run the fixture matrix:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

Optional syntax check:

```bash
python -m py_compile tests/test_release_reference_fixture_matrix_v1.py
```

## Expected result

Current expected result:

```text
Ran 2 tests
OK
```

The matrix passes when:

- positive fixture cases pass the guard;
- negative fixture cases fail the guard;
- negative failures mention the intended failing gate or field;
- negative failures do not include unrelated extra guard errors;
- expected-outcome metadata includes the authority-boundary statement.

## Current coverage

Covered fixture cases:

- positive release-grade reference candidate
- missing external summary presence
- stubbed diagnostics
- false required gate
- non-materialized detector evidence / implicit fallback attempt

Covered PULSE-REF hardening properties:

- non-stubbed release-grade qualification
- explicit external evidence presence
- strict required-gate literal-true semantics
- detector materialization requirement
- no implicit PASS from incomplete evidence
- isolated negative fixture failure modes

Pending fixture categories:

- malformed external summary
- unsigned external summary
- stale artifact
- publication mismatch
- agent-produced diagnostic artifact incorrectly promoted to release authority

## Future work

Future work should add concrete `status.json` and `expected_outcome.json` files for the remaining skeleton categories.

The `malformed_summary` and `unsigned_summary` fixtures should be added after external summary schema and signer requirements are formalized.

The `publication_mismatch` fixture should be added after publication consistency checks are implemented.

The `agent_diagnostic_promoted` fixture should be added after agent-produced diagnostic evidence handling is formalized.

## Summary

The PULSE-REF fixture matrix is a regression layer for release-grade evidence-to-decision behavior.

It strengthens the PULSE release-authority system by making positive and negative release-reference cases executable, repeatable, and auditable.

It does not create release authority.

The release decision remains produced by declared-policy gate enforcement and recorded through the CI outcome.
