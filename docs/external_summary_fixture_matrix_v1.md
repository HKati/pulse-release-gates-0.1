# External Summary Fixture Matrix v1

## Purpose

This document describes the PULSE-REF external summary fixture matrix.

The matrix validates canonical `external_summary_v1` fixture artifacts against:

- `schemas/external_summary_v1.schema.json`
- `tests/test_external_summary_fixture_matrix_v1.py`

The matrix is a regression layer for external evidence shape validation.

It is not a release-decision engine.

It does not fold evidence into `status.json`.

It does not create release authority.

## Current executable matrix

The current executable matrix includes fixture directories that contain both:

- `external_summary.json`
- `expected_outcome.json`

The matrix test discovers those directories and validates each `external_summary.json` against:

```text
schemas/external_summary_v1.schema.json
```

The validation result is compared against the fixture metadata in:

```text
expected_outcome.json
```

Run:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
```

## Active fixture cases

### valid

Expected result: PASS.

Purpose:

Validates that a canonical external summary passes schema validation when it includes:

- schema version;
- summary ID;
- tool name and version;
- run metadata;
- dataset / evaluator metadata;
- subject binding;
- subject SHA-256 digest;
- canonical metrics;
- threshold reference;
- raw evidence artifact reference;
- signer / identity information;
- aggregate result;
- authority-boundary statement.

### malformed_missing_tool_version

Expected result: FAIL.

Purpose:

Validates that external summaries missing `tool.version` fail schema validation.

This fixture isolates:

```text
tool.version missing
```

All non-target fields remain valid.

### malformed_missing_subject_digest

Expected result: FAIL.

Purpose:

Validates that external summaries missing `subject.digest` fail schema validation.

This fixture isolates:

```text
subject.digest missing
```

All non-target fields remain valid.

### malformed_bad_sha256

Expected result: FAIL.

Purpose:

Validates that external summaries with malformed subject digest values fail schema validation.

This fixture isolates:

```text
subject.digest = not-a-sha256
```

All non-target fields remain valid.

### malformed_empty_metrics

Expected result: FAIL.

Purpose:

Validates that external summaries with an empty metrics list fail schema validation.

This fixture isolates:

```text
metrics = []
```

All non-target fields remain valid.

### missing_authority_boundary

Expected result: FAIL.

Purpose:

Validates that external summaries missing the authority-boundary statement fail schema validation.

This fixture isolates:

```text
authority_boundary missing
```

All non-target fields remain valid.

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

## Authority boundary

The external summary fixture matrix does not define release authority.

External summaries, expected-outcome metadata, schemas, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

External summaries may become release evidence only through schema, identity, signer, digest, verification, and policy-controlled fold-in to `status.json`.

## Non-interference

The fixture matrix must preserve non-interference:

- it may validate external evidence shape;
- it may compare actual schema-validation outcomes with expected fixture metadata;
- it may detect regressions in malformed evidence handling;
- it must not authorize, block, override, or reinterpret release outside the declared-policy gate-enforcement path.

## How to run

Run the external summary fixture matrix:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
```

Optional syntax check:

```bash
python -m py_compile tests/test_external_summary_fixture_matrix_v1.py
```

The broader external summary schema tests should also pass:

```bash
python tests/test_external_summary_schema_v1.py
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

- valid external summary fixtures pass schema validation;
- malformed external summary fixtures fail schema validation;
- negative fixture failures match the declared expected schema path;
- negative fixture failures are isolated to one intended schema error;
- expected-outcome metadata includes an authority-boundary statement.

## Current coverage

Covered external summary cases:

- valid canonical external summary;
- missing tool version;
- missing subject digest;
- invalid SHA-256 subject digest;
- empty metrics list;
- missing authority-boundary statement.

Covered PULSE-REF hardening properties:

- canonical external evidence shape;
- tool identity requirement;
- subject binding requirement;
- SHA-256 digest requirement;
- non-empty metric requirement;
- explicit authority-boundary requirement;
- isolated malformed evidence failure modes.

## Relationship to external summary contract

This matrix exercises the contract documented in:

```text
docs/external_summary_schema_v1.md
```

The core artifacts are:

```text
schemas/external_summary_v1.schema.json
schemas/external_summary_envelope_v1.schema.json
policy/external_signers_v1.yml
tests/test_external_summary_schema_v1.py
```

The matrix complements those tests by validating concrete public fixture artifacts.

## Pending next layer

The next fixture layer should cover external summary envelopes and unsigned / unverified evidence.

Planned envelope-related cases include:

- valid envelope;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- unverified envelope with `fold_in_allowed=true`;
- unverified envelope with `fold_in_allowed=false`.

The critical envelope rule is:

```text
if policy_context.fold_in_allowed == true:
    verification.verified must be true
```

## Future release-reference integration

After external summary and envelope fixtures are complete, the release-reference fixture matrix can add higher-level cases such as:

- `malformed_summary`
- `unsigned_summary`

Those release-reference fixtures should depend on the external-summary fixture and envelope validation layer rather than encoding malformed evidence only narratively.

## Summary

The external summary fixture matrix makes PULSE-REF external evidence validation executable, repeatable, and auditable.

It strengthens the PULSE-REF release-grade path by proving that external summary artifacts are accepted or rejected according to a canonical schema and explicit expected-outcome metadata.

It does not create release authority.

The release decision remains produced by declared-policy gate enforcement and recorded through the CI outcome.
