# External Summary Envelope Fixture Matrix v1

## Purpose

This document describes the PULSE-REF external summary envelope fixture matrix.

The matrix validates canonical `external_summary_envelope_v1` fixture artifacts against:

- `schemas/external_summary_envelope_v1.schema.json`
- `tests/test_external_summary_envelope_fixture_matrix_v1.py`

The matrix is a regression layer for external evidence envelope validation.

It is not a release-decision engine.

It does not fold evidence into `status.json`.

It does not create release authority.

## Current executable matrix

The current executable matrix includes fixture directories that contain both:

- `envelope.json`
- `expected_outcome.json`

The matrix test discovers those directories and validates each `envelope.json` against:

```text
schemas/external_summary_envelope_v1.schema.json
```

The validation result is compared against the fixture metadata in:

```text
expected_outcome.json
```

Run:

```bash
python tests/test_external_summary_envelope_fixture_matrix_v1.py
```

## Active fixture cases

### valid

Expected result: PASS.

Purpose:

Validates that a canonical external summary envelope passes schema validation when it includes:

- envelope schema version;
- envelope ID;
- reference to a canonical external summary;
- summary digest;
- signing mode and identity;
- verification result;
- verifier identity;
- signer policy reference;
- release contribution mode;
- fold-in eligibility;
- authority-boundary statement.

### missing_summary_digest

Expected result: FAIL.

Purpose:

Validates that envelopes missing `summary_digest` fail schema validation.

This fixture isolates:

```text
summary_digest missing
```

All non-target fields remain valid.

### missing_signing_identity

Expected result: FAIL.

Purpose:

Validates that envelopes missing `signing.identity` fail schema validation.

This fixture isolates:

```text
signing.identity missing
```

All non-target fields remain valid.

### missing_verifier_identity

Expected result: FAIL.

Purpose:

Validates that envelopes missing `verification.verifier.name` fail schema validation.

This fixture isolates:

```text
verification.verifier.name missing
```

All non-target fields remain valid.

### unverified_fold_in_allowed

Expected result: FAIL.

Purpose:

Validates the verification-before-fold-in rule.

This fixture isolates:

```text
verification.verified = false
policy_context.fold_in_allowed = true
```

This state must fail.

### unverified_fold_in_not_allowed

Expected result: PASS.

Purpose:

Validates the positive control for retained non-fold-in evidence.

This fixture uses:

```text
verification.verified = false
policy_context.fold_in_allowed = false
policy_context.release_contribution = diagnostic
```

This state may pass schema validation because the evidence is explicitly not fold-in eligible and does not define release authority.

## Failure isolation rule

Each negative fixture is intended to isolate one schema failure mode.

The matrix test requires FAIL fixtures to declare:

```text
expected_failure.json_schema_error_path
```

and it verifies that the schema validation failure matches that expected path.

For stricter isolation, the matrix also checks:

- exactly one schema-validation error is produced;
- missing-property fixtures fail via the `required` validator;
- invalid-value fixtures fail on the declared invalid value;
- `expected_failure.non_target_fields_valid` is true.

This prevents a negative fixture from passing the matrix while hiding additional unrelated schema errors.

## Digest binding

The matrix checks digest binding where fixture metadata declares it.

For envelope fixtures that reference the valid external summary fixture:

```text
tests/fixtures/external_summary_v1/valid/external_summary.json
```

the matrix verifies that:

```text
envelope.summary_ref.summary_id == summary.summary_id
envelope.summary_digest.value == summary.evidence.summary_digest
```

This ensures the envelope is bound to the referenced external summary artifact.

## Verification-before-fold-in

The envelope schema enforces:

```text
if policy_context.fold_in_allowed == true:
    verification.verified must be true
```

The fixture matrix validates both sides:

```text
unverified_fold_in_allowed      → FAIL
unverified_fold_in_not_allowed  → PASS
```

This prevents unverified evidence from being marked as fold-in eligible while allowing non-authoritative diagnostic retention.

## Authority boundary

The external summary envelope fixture matrix does not define release authority.

External summaries, envelopes, expected-outcome metadata, schemas, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

External summaries and envelopes may become release evidence only through schema, identity, signer, digest, verification, and policy-controlled fold-in to `status.json`.

## Non-interference

The fixture matrix must preserve non-interference:

- it may validate external envelope shape;
- it may compare actual schema-validation outcomes with expected fixture metadata;
- it may detect regressions in malformed or unverified evidence handling;
- it must not authorize, block, override, or reinterpret release outside the declared-policy gate-enforcement path.

## How to run

Run the envelope fixture matrix:

```bash
python tests/test_external_summary_envelope_fixture_matrix_v1.py
```

Optional syntax check:

```bash
python -m py_compile tests/test_external_summary_envelope_fixture_matrix_v1.py
```

The broader external summary schema tests should also pass:

```bash
python tests/test_external_summary_schema_v1.py
```

The external summary fixture matrix should pass:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
```

The release reference fixture matrix should continue to pass:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

## Expected result

Current expected result:

```text
Ran 3 tests
OK
```

The matrix passes when:

- valid envelope fixtures pass schema validation;
- malformed envelope fixtures fail schema validation;
- negative fixture failures match the declared expected schema path;
- negative fixture failures are isolated to one intended schema error;
- digest binding matches the referenced external summary where declared;
- verification-before-fold-in metadata is consistent;
- expected-outcome metadata includes an authority-boundary statement.

## Current coverage

Covered envelope cases:

- valid envelope;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- unverified evidence marked fold-in eligible;
- unverified evidence retained as non-fold-in diagnostic evidence.

Covered PULSE-REF hardening properties:

- canonical envelope shape;
- summary digest binding;
- signer identity requirement;
- verifier identity requirement;
- verification-before-fold-in enforcement;
- non-authoritative diagnostic retention;
- explicit authority-boundary requirement;
- isolated malformed / unverified evidence failure modes.

## Relationship to external summary contract

This matrix exercises the envelope layer of the contract documented in:

```text
docs/external_summary_schema_v1.md
```

The core artifacts are:

```text
schemas/external_summary_v1.schema.json
schemas/external_summary_envelope_v1.schema.json
policy/external_signers_v1.yml
tests/test_external_summary_schema_v1.py
tests/test_external_summary_fixture_matrix_v1.py
```

The envelope matrix complements those tests by validating concrete public envelope fixture artifacts.

## Future release-reference integration

After external summary and envelope fixtures are complete, the release-reference fixture matrix can add higher-level cases such as:

- `malformed_summary`
- `unsigned_summary`

Those release-reference fixtures should depend on the external-summary and envelope validation layers rather than encoding malformed evidence only narratively.

## Summary

The external summary envelope fixture matrix makes PULSE-REF external evidence verification executable, repeatable, and auditable.

It proves that envelope artifacts are accepted or rejected according to canonical schema rules, digest binding, signer / verifier identity requirements, and verification-before-fold-in constraints.

It does not create release authority.

The release decision remains produced by declared-policy gate enforcement and recorded through the CI outcome.
