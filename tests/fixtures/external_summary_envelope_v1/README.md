# External Summary Envelope Fixtures v1

## Purpose

This fixture set prepares concrete envelope artifacts for PULSE-REF release-grade external evidence validation.

The fixtures exercise the canonical external summary envelope contract defined by:

- `schemas/external_summary_envelope_v1.schema.json`
- `schemas/external_summary_v1.schema.json`
- `policy/external_signers_v1.yml`

The envelope fixture set validates digest binding, signer identity, verifier identity, policy context, and verification-before-fold-in behavior.

This fixture set is not a release-decision engine.

It provides test inputs for validating external evidence verification state before any policy-controlled fold-in to `status.json`.

## Authority boundary

External summary envelope fixtures do not define release authority.

External summaries, envelopes, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, summaries, and publication surfaces do not create a second release-decision path.

The normative release decision remains produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

## Fixture categories

### valid

Expected outcome: PASS.

Represents a canonical external summary envelope that satisfies `external_summary_envelope_v1`.

The valid envelope includes:

- envelope schema version;
- envelope ID;
- reference to an `external_summary_v1` artifact;
- summary digest;
- signing mode and identity;
- verification result;
- verifier identity;
- signer policy reference;
- release contribution mode;
- fold-in eligibility;
- authority-boundary statement.

### missing_summary_digest

Expected outcome: FAIL.

Represents an envelope missing `summary_digest`.

Release-grade external evidence must bind the envelope to the external summary artifact by digest.

### missing_signing_identity

Expected outcome: FAIL.

Represents an envelope missing `signing.identity`.

Release-grade external evidence must identify the signer, workflow, KMS identity, or explicit unsigned identity marker.

### missing_verifier_identity

Expected outcome: FAIL.

Represents an envelope missing verifier identity, such as `verification.verifier.name`.

Release-grade external evidence must record which verifier checked the signature or attestation state.

### unverified_fold_in_allowed

Expected outcome: FAIL.

Represents an envelope where:

```text
verification.verified = false
policy_context.fold_in_allowed = true
```

This is invalid.

The envelope schema enforces verification-before-fold-in:

```text
if policy_context.fold_in_allowed == true:
    verification.verified must be true
```

### unverified_fold_in_not_allowed

Expected outcome: PASS.

Represents an envelope where:

```text
verification.verified = false
policy_context.fold_in_allowed = false
```

This state is allowed for retained diagnostic or non-fold-in evidence.

It does not authorize release and must not become release-grade evidence unless later verified and allowed by policy.

## Expected runner behavior

A future fixture-discovery test should:

1. discover envelope fixture directories;
2. load each `envelope.json`;
3. load each `expected_outcome.json`;
4. validate the envelope against `schemas/external_summary_envelope_v1.schema.json`;
5. compare the validation result against the expected outcome;
6. fail if an invalid envelope passes schema validation;
7. fail if a valid envelope is rejected;
8. preserve the authority boundary.

## Initial directory layout

```text
tests/fixtures/external_summary_envelope_v1/
  README.md
  valid/
  missing_summary_digest/
  missing_signing_identity/
  missing_verifier_identity/
  unverified_fold_in_allowed/
  unverified_fold_in_not_allowed/
```

## Non-goals

This fixture set does not define release authority.

This fixture set does not fold external evidence into `status.json`.

This fixture set does not replace `check_gates.py`.

This fixture set does not make external tools, summaries, envelopes, signer policies, verification reports, ledgers, manifests, audit bundles, dashboards, or publication surfaces normative.

## Relationship to external summary fixtures

The external summary fixture matrix validates the shape of canonical external summary artifacts.

This envelope fixture set validates the wrapper around those summaries:

- digest binding;
- signer identity;
- verification state;
- policy context;
- fold-in eligibility;
- authority-boundary statement.

Both layers are required before external evidence can be safely considered for policy-controlled fold-in to `status.json`.

## Future work

Future commits should add:

- `valid/envelope.json`
- `valid/expected_outcome.json`
- malformed envelope fixtures;
- fixture-discovery tests for `external_summary_envelope_v1`;
- signer-policy fixture tests;
- unsigned-summary fixture cases;
- later release-reference fixtures for `unsigned_summary`.

These fixtures prepare the release-grade path for detecting unsigned, unverified, or fold-in-ineligible external evidence without relying on dashboard interpretation or hidden maintainer explanation.
