# Release Reference External Evidence Integration v1

## Purpose

This document describes how the PULSE-REF external evidence contract is integrated into the release-reference fixture layer.

The goal is to connect lower-level external evidence validation to the release-grade evidence-to-decision path.

This integration covers:

- canonical external summary schema validation;
- external summary envelope validation;
- signer / verifier / digest requirements;
- verification-before-fold-in;
- release-reference failure modes for malformed and unsigned external evidence.

This document does not define release authority.

It documents how external evidence failures are represented as release-required gate failures before a release-grade decision can pass.

## Authority boundary

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

The following surfaces do not create a second release-decision path:

- external summaries;
- external summary envelopes;
- signer policies;
- schema validators;
- fixture metadata;
- benchmark reports;
- ledgers;
- dashboards;
- release-authority manifests;
- audit bundles;
- publication surfaces.

These surfaces may preserve, explain, validate, or reconstruct evidence.

They do not authorize, block, override, or reinterpret release outside the declared-policy gate-enforcement path.

## External evidence contract layers

PULSE-REF currently separates the external evidence contract into three layers.

### External summary schema

Canonical summary schema:

```text
schemas/external_summary_v1.schema.json
```

Fixture matrix:

```text
tests/test_external_summary_fixture_matrix_v1.py
```

Fixture root:

```text
tests/fixtures/external_summary_v1/
```

This layer validates the shape of external detector, evaluation, or review summaries.

It covers:

- tool identity;
- tool version;
- run metadata;
- subject binding;
- subject digest;
- canonical metrics;
- threshold reference;
- raw evidence artifact reference;
- signing context;
- aggregate result;
- authority-boundary statement.

### External summary envelope schema

Canonical envelope schema:

```text
schemas/external_summary_envelope_v1.schema.json
```

Fixture matrix:

```text
tests/test_external_summary_envelope_fixture_matrix_v1.py
```

Fixture root:

```text
tests/fixtures/external_summary_envelope_v1/
```

This layer validates the wrapper around canonical external summaries.

It covers:

- summary reference;
- summary digest;
- signer identity;
- verification result;
- verifier identity;
- signer policy reference;
- release contribution mode;
- fold-in eligibility;
- authority-boundary statement.

### External signer policy

Signer policy:

```text
policy/external_signers_v1.yml
```

This layer defines release-grade expectations for:

- allowed signing modes;
- signer identity requirements;
- unsigned summary handling;
- verification-before-fold-in;
- digest binding;
- fail-closed behavior for malformed, unsigned, unverified, or signer-mismatched evidence.

## Verification-before-fold-in

The external summary envelope schema enforces the following rule:

```text
if policy_context.fold_in_allowed == true:
    verification.verified must be true
```

The envelope fixture matrix validates both sides of this rule:

```text
unverified_fold_in_allowed      -> FAIL
unverified_fold_in_not_allowed  -> PASS
```

This distinction is important.

PULSE-REF does not say that every unverified external artifact must be discarded.

It says that unverified external evidence must not become release-grade fold-in eligible evidence.

Unverified evidence may be retained as diagnostic or non-authoritative evidence only when:

```text
verification.verified = false
policy_context.fold_in_allowed = false
release_contribution = diagnostic
```

## Release-reference integration

The lower-level external evidence contract is integrated into the release-reference fixture layer through release-required gates.

Relevant release-required gates:

```text
detectors_materialized_ok
external_summaries_present
external_all_pass
```

The current integration pattern is:

```text
external evidence exists
external evidence contract fails
external_all_pass = false
release-grade guard = FAIL
```

This keeps external evidence validation separate from release authority while still ensuring that malformed or unsigned external evidence cannot produce release-grade PASS.

## Active release-reference integration fixtures

### malformed_summary

Fixture:

```text
tests/fixtures/release_reference_v1/malformed_summary/status.json
tests/fixtures/release_reference_v1/malformed_summary/expected_outcome.json
```

Purpose:

Validates fail-closed release-grade behavior when external summaries are present but fail the canonical external summary contract.

The fixture isolates:

```text
external_all_pass = false
```

while keeping:

```text
external_summaries_present = true
detectors_materialized_ok = true
diagnostics.gates_stubbed = false
all non-target required gates = true
```

Expected result:

```text
FAIL
```

Failure mode:

```text
malformed_external_summary_contract
```

### unsigned_summary

Fixture:

```text
tests/fixtures/release_reference_v1/unsigned_summary/status.json
tests/fixtures/release_reference_v1/unsigned_summary/expected_outcome.json
```

Purpose:

Validates fail-closed release-grade behavior when external summaries are present but fail signer / verification policy.

The fixture isolates:

```text
external_all_pass = false
```

while keeping:

```text
external_summaries_present = true
detectors_materialized_ok = true
diagnostics.gates_stubbed = false
all non-target required gates = true
```

Expected result:

```text
FAIL
```

Failure mode:

```text
unsigned_external_summary
```

## Why external_all_pass is the release-reference integration point

The external summary and envelope fixture matrices validate detailed evidence-contract behavior.

The release-reference matrix does not duplicate every schema or signer rule.

Instead, it verifies that the result of those external evidence checks is represented in the release-required gate layer.

For release-grade decisions:

```text
external_all_pass = true
```

means the external evidence contract passed and the evidence is eligible under declared policy.

```text
external_all_pass = false
```

means external evidence failed one or more required contract checks, such as:

- malformed summary;
- malformed envelope;
- unsigned release-grade summary;
- missing signer identity;
- missing verifier identity;
- digest mismatch;
- unverified fold-in attempt;
- signer policy mismatch.

The release-reference layer therefore checks that contract failure is not silently converted into release-grade PASS.

## Matrix coverage

Current related test layers:

```text
tests/test_external_summary_schema_v1.py
tests/test_external_summary_fixture_matrix_v1.py
tests/test_external_summary_envelope_fixture_matrix_v1.py
tests/test_release_reference_fixture_matrix_v1.py
```

The lower-level external evidence matrices validate:

- valid external summary;
- malformed external summary;
- missing tool version;
- missing subject digest;
- invalid SHA-256 digest;
- empty metrics;
- missing authority boundary;
- valid envelope;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- unverified fold-in allowed;
- unverified fold-in not allowed.

The release-reference matrix validates that selected external evidence failures produce release-grade fail-closed behavior through `external_all_pass=false`.

## Failure isolation rule

Each negative release-reference fixture is intended to isolate one failure mode.

For external evidence integration fixtures:

```text
malformed_summary    -> external_all_pass=false
unsigned_summary     -> external_all_pass=false
```

The fixture metadata records the detailed failure mode:

```text
external_summary_contract_failure_mode = malformed_summary
external_summary_contract_failure_mode = unsigned_summary
```

Non-target gates must remain passing.

This avoids masking regressions where a fixture fails for an unrelated reason.

## How to run

Run the release-reference fixture matrix:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

Run the external summary schema tests:

```bash
python tests/test_external_summary_schema_v1.py
```

Run the external summary fixture matrix:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
```

Run the external summary envelope fixture matrix:

```bash
python tests/test_external_summary_envelope_fixture_matrix_v1.py
```

Direct guard check for malformed summary:

```bash
python ci/check_release_reference_complete_v1.py \
  --status tests/fixtures/release_reference_v1/malformed_summary/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-detectors-materialized \
  --require-external-summaries
```

Expected result:

```text
FAIL
```

Direct guard check for unsigned summary:

```bash
python ci/check_release_reference_complete_v1.py \
  --status tests/fixtures/release_reference_v1/unsigned_summary/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-detectors-materialized \
  --require-external-summaries
```

Expected result:

```text
FAIL
```

## Relationship to PULSE-REF hardening

This integration supports the PULSE-REF release-grade hardening track by connecting:

```text
external evidence validation
-> release-required gates
-> fail-closed release-reference behavior
```

It strengthens the release-grade path without creating a second decision engine.

It also prepares later work on:

- non-stubbed release-grade reference runs;
- signed external evidence fold-in;
- provenance and attestation;
- atomic publication snapshots;
- external verification packs;
- benchmark fixtures.

## Non-goals

This integration does not:

- replace `check_gates.py`;
- define release authority inside external summary validators;
- make signer policies normative release-decision engines;
- make envelope validators release-authority engines;
- allow dashboards, ledgers, manifests, audit bundles, or publication surfaces to authorize release;
- fold evidence into `status.json` without declared policy.

## Summary

The external evidence integration layer proves that external summary / envelope / signer-policy failures are reflected in release-grade decision inputs.

Malformed or unsigned external evidence cannot become release-grade PASS.

The integration preserves the PULSE authority boundary:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

Everything else validates, preserves, explains, or reconstructs the evidence and decision trace.
