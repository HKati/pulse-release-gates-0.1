# External Summary Schema v1

## Purpose

This document describes the PULSE-REF external summary contract for release-grade evidence handling.

PULSE-REF uses canonical external summaries and verification envelopes to make detector, evaluation, and review evidence inspectable before it can be folded into `status.json`.

This document covers:

- `schemas/external_summary_v1.schema.json`
- `schemas/external_summary_envelope_v1.schema.json`
- `policy/external_signers_v1.yml`
- verification-before-fold-in requirements
- signer / identity requirements
- authority-boundary constraints

The external summary contract does not define release authority.

It defines the shape and verification requirements for recorded external evidence before policy-controlled fold-in to `status.json`.

## Authority boundary

External summaries, envelopes, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

External evidence may contribute to release evidence only after schema, identity, signer, digest, verification, and policy checks succeed.

## External summary schema

The canonical external summary schema is:

```text
schemas/external_summary_v1.schema.json
```

It defines the required shape for external detector, evaluation, or review summaries.

Required top-level fields:

- `schema_version`
- `summary_id`
- `tool`
- `run`
- `subject`
- `metrics`
- `threshold_ref`
- `evidence`
- `signing`
- `result`
- `authority_boundary`

The schema requires:

- tool name and version;
- run timestamp;
- subject binding;
- subject digest;
- at least one canonical metric;
- threshold reference;
- raw artifact reference;
- signer / identity information;
- aggregate result;
- authority-boundary statement.

## Tool identity

External summaries must identify the tool or evaluator that produced the evidence.

Required fields:

```text
tool.name
tool.version
```

Optional adapter fields:

```text
tool.adapter
tool.adapter_version
```

Tool identity is required because release-grade evidence must be traceable to a concrete evaluation source and version.

## Subject binding

External summaries must bind the evidence to the evaluated subject.

Required fields:

```text
subject.kind
subject.id
subject.digest_algorithm
subject.digest
```

The digest algorithm is currently:

```text
sha256
```

The digest prevents a summary from being silently reused for a different model, application, dataset, prompt set, or release candidate.

## Metrics

External summaries must contain at least one canonical metric.

Each metric requires:

```text
key
value
passed
```

Optional metric fields include:

```text
unit
threshold
comparator
severity
notes
```

The `passed` field is a boolean. It records the metric-level result under the declared threshold semantics.

Metric names should remain stable across repeated runs so that release-grade evidence can be compared and audited.

## Threshold reference

External summaries must include a threshold reference:

```text
threshold_ref.key
```

Optional fields:

```text
threshold_ref.version
threshold_ref.uri
```

The threshold reference records which threshold policy was used to interpret metrics.

A release-grade system should not infer thresholds from human-readable text or dashboard display.

## Evidence artifact binding

External summaries must point to the archived raw evidence artifact:

```text
evidence.raw_artifact_uri
```

Optional digests:

```text
evidence.raw_artifact_digest
evidence.summary_digest
```

The raw artifact should be retained so that a reviewer can reconstruct how the summary was produced.

## Signing information

External summaries include signer / identity information:

```text
signing.mode
signing.identity
```

Optional fields:

```text
signing.bundle_path
signing.verified
```

The summary schema records signing context. The envelope schema records verification context.

## Aggregate result

External summaries include an aggregate result:

```text
result.passed
```

Optional fields:

```text
result.reason
result.release_contribution
```

The `release_contribution` field may be:

```text
required
advisory
diagnostic
```

A summary marked `required` does not automatically become release authority. It becomes release-relevant only through declared PULSE policy and validated fold-in to `status.json`.

## External summary envelope

The canonical envelope schema is:

```text
schemas/external_summary_envelope_v1.schema.json
```

The envelope binds a canonical external summary to:

- summary reference;
- summary digest;
- signer identity;
- verification status;
- verifier identity;
- signer policy reference;
- fold-in eligibility;
- authority-boundary statement.

Required top-level fields:

- `schema_version`
- `envelope_id`
- `summary_ref`
- `summary_digest`
- `signing`
- `verification`
- `policy_context`
- `authority_boundary`

## Verification-before-fold-in

The envelope schema enforces verification-before-fold-in.

If:

```text
policy_context.fold_in_allowed = true
```

then:

```text
verification.verified = true
```

must also be true.

This prevents internally inconsistent envelopes where unverified external evidence is marked as fold-in eligible.

The following state is invalid:

```text
verification.verified = false
policy_context.fold_in_allowed = true
```

The following state is allowed for retained diagnostic evidence:

```text
verification.verified = false
policy_context.fold_in_allowed = false
```

## Signer policy

The signer policy file is:

```text
policy/external_signers_v1.yml
```

It defines:

- release-grade signing modes;
- allowed signer identity groups;
- unsigned-summary policy;
- fold-in requirements;
- signer / identity verification requirements;
- failure behavior;
- diagnostic allowances.

Important release-grade defaults:

```text
require_schema_valid_summary = true
require_schema_valid_envelope = true
require_summary_digest = true
require_subject_digest = true
require_tool_identity = true
require_tool_version = true
require_threshold_ref = true
require_signer_identity = true
require_verification_before_fold_in = true
allow_unsigned_release_grade = false
allow_unverified_fold_in = false
```

## Unsigned summaries

Unsigned summaries are not allowed for release-grade fold-in.

Release-grade behavior:

```text
unsigned_release_grade_summary = fail_closed
```

Unsigned or unverified summaries may be retained as diagnostic evidence only if explicitly labeled as non-authoritative.

Diagnostic retention does not authorize release.

## Fold-in rules

External evidence may be folded into release evidence only when the relevant schema, signer, digest, verification, and policy checks succeed.

For required release-grade evidence, fold-in requires:

- schema-valid summary;
- schema-valid envelope;
- digest match;
- signer identity;
- allowed signing mode;
- verification success;
- signer policy compatibility;
- subject digest;
- threshold reference;
- policy-controlled fold-in eligibility.

## Failure behavior

The signer policy defines fail-closed behavior for release-grade evidence.

Examples:

```text
malformed_summary = fail_closed
malformed_envelope = fail_closed
missing_summary_digest = fail_closed
missing_subject_digest = fail_closed
missing_signer_identity = fail_closed
signer_identity_not_allowed = fail_closed
signing_mode_not_allowed = fail_closed
fold_in_allowed_true_but_verification_false = fail_closed
unsigned_release_grade_summary = fail_closed
```

## Test coverage

The schema and policy contract is covered by:

```text
tests/test_external_summary_schema_v1.py
```

The tests cover:

- valid `external_summary_v1`;
- missing `tool.version`;
- missing `subject.digest`;
- invalid SHA-256 digest;
- empty metrics;
- missing authority boundary;
- valid `external_summary_envelope_v1`;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- rejection of `fold_in_allowed=true` when `verification.verified=false`;
- acceptance of `fold_in_allowed=false` when `verification.verified=false`;
- signer policy basics.

Run:

```bash
python tests/test_external_summary_schema_v1.py
```

The PULSE-REF release reference fixture matrix should also continue to pass:

```bash
python tests/test_release_reference_fixture_matrix_v1.py
```

## Relationship to release authority

The external summary contract strengthens evidence handling.

It does not decide release.

It does not replace `check_gates.py`.

It does not make external tools, dashboards, summaries, envelopes, signer policies, manifests, audit bundles, or publication surfaces normative.

The release decision remains produced by declared-policy gate enforcement and recorded through the CI outcome.

## Future work

The external summary contract prepares the following PULSE-REF fixture categories:

- `malformed_summary`
- `unsigned_summary`

These should be added after concrete fixture artifacts are created for:

- malformed external summary;
- invalid external summary envelope;
- unsigned release-grade summary;
- unverified envelope marked fold-in eligible;
- signer identity mismatch.

Future implementation work should add:

- external summary fixture files;
- envelope fixture files;
- schema fixture discovery tests;
- signer-policy fixture tests;
- optional external summary validator CLI;
- policy-controlled fold-in checks before `status.json` update.

## Summary

`external_summary_v1` defines the canonical shape of external evidence.

`external_summary_envelope_v1` binds that evidence to digest, signer, verification, and policy context.

`external_signers_v1.yml` defines release-grade signer and verification rules.

Together, these artifacts make external evidence auditable before it can be folded into release evidence.

They do not create release authority.
