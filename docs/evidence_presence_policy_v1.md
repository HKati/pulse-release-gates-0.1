# Evidence Presence Policy v1

## Purpose

This document defines the PULSE-REF evidence presence policy for release-grade paths.

The goal is to prevent missing, absent, implicit, legacy, fallback, or non-materialized evidence from being converted into release-grade PASS.

This policy supports the PULSE-REF hardening track by making evidence presence explicit before release-grade gate enforcement.

## Authority boundary

This document does not define a second release-decision engine.

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

Evidence presence policy strengthens the recorded evidence layer.

It does not authorize, block, override, reinterpret, or replace the declared-policy gate-enforcement path.

## Core rule

Release-grade paths must not infer PASS from missing evidence.

In release-grade paths:

```text
missing evidence -> explicit missing / fail state
```

never:

```text
missing evidence -> implicit PASS
```

Required evidence must be:

- present;
- materialized;
- valid under the relevant schema or contract;
- bound to the current run, subject, dataset, or release candidate where applicable;
- folded into `status.json` only after declared policy permits it;
- represented as explicit gate state.

## Release-grade evidence requirements

The following evidence classes are release-grade relevant.

### Detector evidence

Release-grade behavior:

```text
detectors_materialized_ok must be literal true
```

Required meaning:

- detector evidence exists;
- detector output is materialized;
- detector result is not stubbed;
- detector output is bound to the candidate release state;
- detector result is represented in `status.json`.

Missing or non-materialized detector evidence must fail closed.

### External summary evidence

Release-grade behavior:

```text
external_summaries_present must be literal true
external_all_pass must be literal true
```

Required meaning:

- external summaries are present;
- external summaries validate against the external summary contract;
- external envelopes validate against the envelope contract where applicable;
- signer / verifier / digest requirements are satisfied where applicable;
- external evidence is not unsigned, malformed, stale, signer-mismatched, or fold-in-ineligible.

Missing external summaries must fail closed.

Malformed or unsigned external summaries must fail closed.

Unverified external evidence may be retained as diagnostic evidence only when explicitly not fold-in eligible.

### Refusal-delta evidence

Release-grade behavior should require explicit refusal-delta evidence presence when refusal-delta gates are release-required.

Recommended gate:

```text
refusal_delta_evidence_present
```

Expected release-grade semantics:

```text
refusal_delta_evidence_present = true
refusal_delta_pass = true
```

Missing refusal-delta evidence must not be converted into PASS by legacy fallback behavior.

### Audit bundle evidence

Release-grade reference paths should require an audit bundle when the path declares audit-bundle preservation.

The audit bundle is not a decision engine.

It preserves the decision trace.

Missing audit bundle may fail reference qualification, but it does not create an independent release decision.

### Release-authority manifest evidence

Release-authority manifests preserve the decision trace.

They do not generate the release decision.

A release-grade reference path may require a manifest for reconstructibility, but the manifest remains non-normative.

## Legacy / advisory behavior

Some legacy or onboarding paths may retain permissive behavior for ease of development.

Examples:

- demo mode;
- core smoke mode;
- advisory-only detector summaries;
- diagnostic evidence retention.

Those paths must not be confused with release-grade paths.

Any permissive fallback must be explicitly labeled as:

```text
legacy
advisory
diagnostic
non-authoritative
not release-grade
```

Release-grade paths must not inherit permissive legacy fallback semantics.

## Explicit missing states

Missing release-grade evidence should produce explicit states such as:

```text
missing
not_materialized
not_verified
not_signed
schema_invalid
digest_mismatch
signer_mismatch
not_fold_in_allowed
```

These states should be represented in diagnostics, evidence metadata, or gate failure output.

They must not be hidden behind a passing aggregate.

## Required gate behavior

Required gates must pass only on literal boolean `true`.

The following must not pass:

- `false`
- `null`
- missing key
- string `"true"`
- numeric `1`
- malformed evidence
- stale evidence
- unsigned release-grade evidence
- non-materialized release-grade evidence
- diagnostic-only evidence
- advisory-only evidence not promoted by declared policy

## External evidence integration

PULSE-REF already separates external evidence into:

```text
external_summary_v1
external_summary_envelope_v1
external_signers_v1
```

The release-reference layer integrates external evidence contract results through:

```text
external_summaries_present
external_all_pass
```

Current release-reference external evidence failure fixtures include:

```text
release_reference_v1/malformed_summary
release_reference_v1/unsigned_summary
```

Those fixtures validate that malformed or unsigned external evidence produces:

```text
external_all_pass = false
```

and therefore release-grade FAIL.

## Refusal-delta hardening target

The next evidence-presence hardening target is refusal-delta evidence.

Current hardening objective:

```text
release-grade paths must not allow missing refusal-delta evidence to become implicit PASS
```

Recommended release-grade behavior:

```text
refusal_delta_evidence_present = false
-> release-grade FAIL
```

Recommended policy addition:

```text
release_required:
  - refusal_delta_evidence_present
```

or equivalent declared policy promotion when refusal-delta is release-relevant.

## Non-interference

Evidence presence policy must preserve non-interference.

It may:

- require evidence to exist;
- require evidence to be materialized;
- require evidence to be schema-valid;
- require evidence to be signer-valid;
- require evidence to be fold-in eligible;
- require explicit missing/fail states.

It must not:

- create a second release-decision path;
- make dashboards normative;
- make ledgers normative;
- make manifests normative;
- make audit bundles normative;
- let advisory evidence silently become release authority;
- let missing evidence silently become PASS.

## Fixture coverage

Current PULSE-REF fixture coverage includes:

```text
release_reference_v1/pass
release_reference_v1/missing_external
release_reference_v1/stubbed
release_reference_v1/false_gate
release_reference_v1/implicit_fallback_attempt
release_reference_v1/malformed_summary
release_reference_v1/unsigned_summary
```

The `implicit_fallback_attempt` fixture already validates non-materialized detector evidence:

```text
detectors_materialized_ok = false
-> FAIL
```

The next recommended fixture category is:

```text
release_reference_v1/missing_refusal_delta
```

Expected target behavior:

```text
refusal_delta_evidence_present = false
-> FAIL
```

## Test expectations

Evidence presence tests should verify:

- missing required evidence fails closed;
- non-materialized detector evidence fails closed;
- missing external summaries fail closed;
- malformed external summaries fail closed;
- unsigned release-grade summaries fail closed;
- missing refusal-delta evidence fails closed when release-required;
- diagnostic-only retained evidence does not become release authority;
- advisory-only evidence does not become release authority unless promoted by policy.

## How to run current related tests

Release reference fixture matrix:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

External summary schema tests:

```bash
python tests/test_external_summary_schema_v1.py
```

External summary fixture matrix:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
```

External summary envelope fixture matrix:

```bash
python tests/test_external_summary_envelope_fixture_matrix_v1.py
```

## Future implementation work

Future commits should add:

- `refusal_delta_evidence_present` gate;
- release-grade refusal-delta evidence presence fixture;
- no-implicit-PASS release-grade tests;
- evidence presence policy schema;
- release-reference fixture for missing refusal-delta evidence;
- release-grade path wiring so missing refusal-delta evidence cannot pass silently.

Potential future files:

```text
schemas/evidence_presence_policy_v1.json
tests/test_no_implicit_pass_release_grade.py
tests/test_refusal_delta_presence_policy.py
tests/fixtures/release_reference_v1/missing_refusal_delta/status.json
tests/fixtures/release_reference_v1/missing_refusal_delta/expected_outcome.json
```

## Summary

PULSE-REF evidence presence policy ensures that release-grade decisions are based on materialized, valid, policy-bound evidence.

Missing evidence must be visible.

Missing evidence must fail closed when release-required.

Missing evidence must not become PASS through implicit fallback.

This strengthens the PULSE release-authority boundary without creating a second decision engine.
