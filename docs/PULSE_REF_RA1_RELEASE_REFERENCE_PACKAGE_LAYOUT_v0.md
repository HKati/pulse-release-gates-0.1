# PULSE-REF RA1 Release-Reference Package Layout v0

Status: RA1 package-layout contract  
Scope: PULSE-REF externally verifiable release-reference package  
Authority: documentation-only layout contract  
Date: 2026-05-09

## Core statement

PULSE-REF RA1 defines the expected layout of an externally verifiable release-reference package.

RA1 builds on the RA0 release-authority reconstruction boundary.

RA0 established that release-grade operator handoff must use existing, explicit, non-stubbed, non-scaffolded, policy-consistent status evidence and strict declared-policy gate enforcement.

RA1 defines how the relevant artifacts should be bundled so an external reviewer can reconstruct the release decision from archived evidence.

RA1 does not create a second release-decision engine.

The normative release decision remains:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

The release-reference package preserves and verifies this path.

It does not authorize release independently.

## Purpose

The purpose of the RA1 release-reference package is to bind the release decision trail into one externally inspectable artifact set.

The package should allow an external verifier to answer:

```text
Which status artifact was evaluated?
Which gate policy was used?
Which required gates were materialized?
Which strict gate check was run?
Which CI outcome recorded the decision?
Which audit / manifest / publication surfaces preserve the same run?
```

A release-reference package is not a dashboard.

It is not a narrative summary.

It is not a second decision engine.

It is a preservation and verification structure for the declared-policy release-authority path.

## Package root

A release-reference package SHOULD be rooted under a stable package directory.

Suggested layout:

```text
release_reference_package/
  README.md
  package_manifest.json
  status/
  policy/
  gates/
  handoff/
  release_authority/
  audit/
  ci/
  publication/
  external_evidence/
  digests/
```

The exact directory name may include run identifiers, for example:

```text
pulse_ref_ra1_<run_key>/
pulse_ref_ra1_<utc_date>_<short_sha>/
```

The package root SHOULD be deterministic enough for archiving and reproducible verification.

## Required package manifest

The package SHOULD include:

```text
package_manifest.json
```

This manifest records the package-level identity and artifact digest map.

Suggested fields:

```json
{
  "schema": "pulse_ref_release_reference_package_v0",
  "package_id": "<stable package id>",
  "created_utc": "<ISO-8601 UTC timestamp>",
  "run_key": "<run key>",
  "git_sha": "<git sha>",
  "status_artifact": {
    "path": "status/status.json",
    "sha256": "<sha256>"
  },
  "gate_policy": {
    "path": "policy/pulse_gate_policy_v0.yml",
    "sha256": "<sha256>"
  },
  "operator_handoff_report": {
    "path": "handoff/operator_handoff_report.json",
    "sha256": "<sha256>"
  },
  "release_authority_manifest": {
    "path": "release_authority/release_authority_manifest.json",
    "sha256": "<sha256>"
  },
  "audit_bundle": {
    "path": "audit/",
    "sha256_manifest_path": "digests/audit_bundle_digests.json"
  },
  "ci_outcome": {
    "path": "ci/ci_outcome.json",
    "sha256": "<sha256>"
  },
  "authority_boundary": {
    "normative_decision_path": "status.json -> declared gate policy -> materialized required gates -> strict gate checking -> CI outcome",
    "package_role": "audit_preservation_reconstruction",
    "creates_release_authority": false
  }
}
```

This manifest does not create release authority.

It binds artifacts for external verification.

## Status artifact

The package MUST include the status artifact evaluated by release-grade handoff.

Suggested path:

```text
status/status.json
```

The status artifact SHOULD be byte-identical to the artifact referenced by the operator handoff report.

The package manifest SHOULD record:

```text
status/status.json sha256
```

The handoff report SHOULD also record status digest fields:

```text
status_sha256_before_run
status_sha256_after_generation
status_sha256_after_run
```

For release-grade existing-status handoff, the digest SHOULD remain stable across handoff checking unless the selected path intentionally rewrites the artifact.

## Declared gate policy

The package MUST include the declared gate policy used to materialize required gate sets.

Suggested path:

```text
policy/pulse_gate_policy_v0.yml
```

The package manifest SHOULD record:

```text
policy/pulse_gate_policy_v0.yml sha256
```

If the status artifact declares:

```text
metrics.gate_policy_sha256
metrics.gate_policy_path
```

then those values must match the packaged policy artifact.

The policy artifact remains the source for materialized required gate sets.

## Gate registry

The package SHOULD include the gate registry used to interpret gate identities.

Suggested path:

```text
policy/pulse_gate_registry_v0.yml
```

The registry supports interpretation and consistency checking.

It does not create release authority independently.

## Materialized gate sets

The package SHOULD include materialized gate sets.

Suggested path:

```text
gates/materialized_gate_sets.json
```

Suggested content:

```json
{
  "schema": "pulse_ref_materialized_gate_sets_v0",
  "policy_path": "policy/pulse_gate_policy_v0.yml",
  "policy_sha256": "<sha256>",
  "sets": {
    "required": ["<gate id>"],
    "release_required": ["<gate id>"]
  },
  "effective_required_gates": ["<gate id>"]
}
```

For release-grade reconstruction, the effective required gate set is the ordered union of:

```text
gates.required
gates.release_required
```

The materialized gate set record is a reconstruction aid.

The normative enforcement remains strict gate checking over the declared policy-derived required gates.

## Operator handoff report

The package MUST include the operator handoff report.

Suggested path:

```text
handoff/operator_handoff_report.json
```

The report SHOULD include:

```text
gate_mode = release-grade
status_source.mode = existing
status_source.status_path
status_source.status_sha256_before_run
status_source.status_sha256_after_generation
status_source.status_sha256_after_run
materialized_gate_sets
effective_required_gates
commands
errors
warnings
ok
```

The handoff report reconstructs and verifies release-grade handoff.

It does not authorize release independently.

## Release authority manifest

The package SHOULD include the release authority manifest.

Suggested path:

```text
release_authority/release_authority_manifest.json
```

The manifest SHOULD preserve:

```text
status artifact reference
gate policy reference
materialized gate set reference
strict gate-check command reference
CI outcome reference
audit bundle reference
```

The release authority manifest is an audit and preservation surface.

It does not create release authority.

## Audit bundle

The package SHOULD include or reference an audit bundle.

Suggested path:

```text
audit/
```

The audit bundle SHOULD preserve relevant artifacts needed to reconstruct the decision.

Possible contents:

```text
audit/status.json
audit/pulse_gate_policy_v0.yml
audit/operator_handoff_report.json
audit/release_authority_manifest.json
audit/external_summaries/
audit/junit.xml
audit/sarif.json
audit/quality_ledger_section.md
```

The audit bundle SHOULD include a digest manifest.

Suggested path:

```text
digests/audit_bundle_digests.json
```

## CI outcome

The package MUST include a CI outcome record or reference.

Suggested path:

```text
ci/ci_outcome.json
```

Suggested fields:

```json
{
  "schema": "pulse_ref_ci_outcome_v0",
  "provider": "github_actions",
  "workflow": "<workflow name>",
  "run_id": "<run id>",
  "run_url": "<url>",
  "commit_sha": "<sha>",
  "gate_check_job": "<job name>",
  "gate_check_conclusion": "success",
  "created_utc": "<timestamp>"
}
```

The CI outcome is part of the normative decision record because the PULSE release decision is recorded through CI enforcement.

## Publication snapshot

The package SHOULD include publication-surface references.

Suggested path:

```text
publication/publication_snapshot.json
```

Suggested fields:

```json
{
  "schema": "pulse_ref_publication_snapshot_v0",
  "quality_ledger_url": "<url>",
  "status_json_url": "<url>",
  "release_authority_manifest_url": "<url>",
  "audit_bundle_url": "<url>",
  "snapshot_created_utc": "<timestamp>",
  "creates_release_authority": false
}
```

Publication surfaces do not create release authority.

They preserve and expose the release state.

## External evidence

The package SHOULD include external evidence artifacts when they contribute to release-grade checking.

Suggested path:

```text
external_evidence/
```

Possible contents:

```text
external_evidence/summaries/
external_evidence/envelopes/
external_evidence/signers_policy.yml
external_evidence/verification_results.json
```

External evidence must respect the verification-before-fold-in boundary.

Evidence that is malformed, unsigned, unverified when fold-in is allowed, stale, or diagnostic-only must not become release authority.

## Digest manifest

The package SHOULD include a digest manifest covering package artifacts.

Suggested path:

```text
digests/package_digests.json
```

Suggested content:

```json
{
  "schema": "pulse_ref_package_digests_v0",
  "algorithm": "sha256",
  "created_utc": "2026-05-09T00:00:00Z",
  "package_id": "pulse-ref-ra1-example",
  "artifacts": {
    "status/status.json": "0000000000000000000000000000000000000000000000000000000000000000",
    "policy/pulse_gate_policy_v0.yml": "1111111111111111111111111111111111111111111111111111111111111111",
    "gates/materialized_gate_sets.json": "2222222222222222222222222222222222222222222222222222222222222222",
    "handoff/operator_handoff_report.json": "3333333333333333333333333333333333333333333333333333333333333333",
    "ci/ci_outcome.json": "4444444444444444444444444444444444444444444444444444444444444444"
  },
  "authority_boundary": {
    "digest_role": "artifact_integrity_verification",
    "creates_release_authority": false
  }
}
```

The `artifacts` field is an object map from package-relative artifact paths to SHA-256 digests.

This map form is intentional.

It avoids representing the same artifact path multiple times in a normal parsed JSON object and supports deterministic external verification.

Array-style entries such as:

```json
[
  {
    "path": "status/status.json",
    "sha256": "..."
  }
]
```

are not the RA1 package digests schema form.

Producers that use array-style internal representations should normalize them into the package digest object-map form before validation.

The digest manifest supports reproducibility and external verification.

It does not create release authority.


## Minimum viable RA1 package

A minimum RA1 package SHOULD include:

```text
package_manifest.json
status/status.json
policy/pulse_gate_policy_v0.yml
policy/pulse_gate_registry_v0.yml
gates/materialized_gate_sets.json
handoff/operator_handoff_report.json
release_authority/release_authority_manifest.json
ci/ci_outcome.json
digests/package_digests.json
README.md
```

This minimum package should be enough for an external verifier to reconstruct:

```text
status artifact
declared policy
required gate set
strict gate check
CI outcome
authority boundary
```

## Verification procedure

An external verifier should be able to perform the following procedure:

```text
1. Read package_manifest.json.
2. Verify SHA-256 digests for packaged artifacts.
3. Confirm status/status.json matches the handoff report status digest.
4. Confirm policy/pulse_gate_policy_v0.yml matches declared policy metadata if present.
5. Materialize required + release_required gate sets from packaged policy.
6. Compare materialized gates to gates/materialized_gate_sets.json.
7. Run strict gate checking over status/status.json.
8. Confirm operator_handoff_report.json records the same effective required gates and outcome.
9. Confirm ci/ci_outcome.json records the CI outcome for the same commit/run.
10. Confirm release_authority_manifest.json preserves the same artifact references.
```

The verifier should reject the package if any required artifact is missing, digest-mismatched, stale, or inconsistent with the declared-policy release path.

## Authority boundary

The RA1 package must preserve the PULSE authority boundary.

Normative path:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

Package surfaces:

```text
package_manifest.json
operator_handoff_report.json
release_authority_manifest.json
audit bundle
publication snapshot
digest manifest
README.md
```

are audit / preservation / reconstruction surfaces.

They do not create release authority.

## Relation to RA0

RA0 established:

```text
release-grade handoff preconditions
no implicit PASS evidence presence
external evidence validation
verification-before-fold-in
release-reference fixture matrix
operator handoff digest traceability
```

RA1 packages these into an externally verifiable artifact layout.

RA1 should not weaken RA0 preconditions.

RA1 should not introduce any second release-decision path.

## What this contract does not implement

This document does not implement package generation.

This document does not change gate policy.

This document does not change check_gates.py.

This document does not change CI behavior.

This document does not make policy hash/path mandatory for all status artifacts.

This document defines the target package layout for the next implementation phase.

## Summary

PULSE-REF RA1 defines how release-reference artifacts should be packaged for external verification.

The package binds:

```text
status
policy
materialized gates
operator handoff report
release authority manifest
audit bundle
CI outcome
publication snapshot
digests
```

into one externally inspectable structure.

The package preserves and verifies release authority.

It does not create release authority.
