# External Summary Fixtures v1

## Purpose

This fixture set prepares concrete external-evidence artifacts for PULSE-REF release-grade validation.

The fixtures exercise the canonical external summary contract defined by:

- `schemas/external_summary_v1.schema.json`
- `schemas/external_summary_envelope_v1.schema.json`
- `policy/external_signers_v1.yml`

The fixture set is not a release-decision engine.

It provides test inputs for validating external evidence shape, digest binding, signer / identity requirements, and verification-before-fold-in behavior before any policy-controlled fold-in to `status.json`.

## Authority boundary

External summary fixtures do not define release authority.

External summaries, envelopes, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

## Fixture categories

### valid

Expected outcome: PASS.

Represents a canonical external summary that satisfies the `external_summary_v1` schema:

- valid schema version;
- tool name and version;
- generated timestamp;
- subject binding;
- subject digest;
- canonical metric list;
- threshold reference;
- raw artifact reference;
- signer / identity information;
- aggregate result;
- authority-boundary statement.

### malformed_missing_tool_version

Expected outcome: FAIL.

Represents an external summary missing `tool.version`.

Release-grade external evidence must identify the producing tool and version.

### malformed_missing_subject_digest

Expected outcome: FAIL.

Represents an external summary missing `subject.digest`.

Release-grade external evidence must be bound to the evaluated subject.

### malformed_bad_sha256

Expected outcome: FAIL.

Represents an external summary with an invalid SHA-256 digest.

Release-grade evidence must not accept malformed digest bindings.

### malformed_empty_metrics

Expected outcome: FAIL.

Represents an external summary with an empty `metrics` list.

Release-grade external evidence must contain at least one canonical metric.

### missing_authority_boundary

Expected outcome: FAIL.

Represents an external summary missing the authority-boundary statement.

Release-grade evidence artifacts must make clear that the external summary does not define release authority.

## Related envelope fixture categories

Envelope fixture categories will be added under a related fixture set after this summary fixture layer is established.

Planned envelope cases include:

- valid envelope;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- unverified envelope with `fold_in_allowed=true`;
- unverified envelope with `fold_in_allowed=false`.

The critical release-grade rule is:

```text
if policy_context.fold_in_allowed == true:
    verification.verified must be true
```

## Expected runner behavior

A future fixture-discovery test should:

1. discover external summary fixture directories;
2. load each `external_summary.json`;
3. load each `expected_outcome.json`;
4. validate the summary against `schemas/external_summary_v1.schema.json`;
5. compare the validation result against the expected outcome;
6. fail if an invalid summary passes schema validation;
7. fail if a valid summary is rejected;
8. preserve the authority boundary.

## Initial directory layout

```text
tests/fixtures/external_summary_v1/
  README.md
  valid/
  malformed_missing_tool_version/
  malformed_missing_subject_digest/
  malformed_bad_sha256/
  malformed_empty_metrics/
  missing_authority_boundary/
```

## Non-goals

This fixture set does not define release authority.

This fixture set does not fold external evidence into `status.json`.

This fixture set does not replace `check_gates.py`.

This fixture set does not make external tools, summaries, envelopes, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, or publication surfaces normative.

## Future work

Future commits should add:

- `valid/external_summary.json`
- `valid/expected_outcome.json`
- malformed summary fixtures;
- fixture-discovery tests for `external_summary_v1`;
- envelope fixture directories;
- envelope fixture-discovery tests;
- later release-reference fixtures for `malformed_summary` and `unsigned_summary`.

These fixtures prepare the release-grade path for detecting malformed and unsigned external evidence without relying on dashboard interpretation or hidden maintainer explanation.
