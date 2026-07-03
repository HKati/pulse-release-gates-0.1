# PULSEmech release-grade reference proof plan v0

## Status

Technical proof plan.

This document defines the evidence, run conditions, artifact set, qualification criteria, and reproduction expectations required before a public non-stubbed PULSEmech release-grade reference run can be recorded.

This document is not a run record.

This document does not claim that a completed public non-stubbed release-grade reference run already exists.

This document does not mark any pending implementation-state item as completed.

This document does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, branch protection settings, README state, release metadata, or release-authority semantics.

## Purpose

PULSEmech already has a self-contained Tier 0 evidence floor and a broad release-authority test surface.

The remaining release-grade maturity question is different:

```text
Can a complete, public, non-stubbed release-grade reference run be reconstructed from recorded evidence, declared policy, workflow-effective materialized gates, verifier replay, and CI enforcement?
```

This proof plan defines the conditions for answering that question.

## Current distinction

PULSEmech has multiple evidence layers.

These layers must not be collapsed into one status.

```text
Tier 0 self-contained evidence floor
→ demonstrates that the base evidence path can run without hosted external model access

Release-grade reference package tests
→ demonstrate package, schema, verifier, wiring, and reference-bundle contracts

Completed public non-stubbed release-grade reference run
→ requires an operational run record with ref + commit identity, run_mode = prod, non-stubbed status, materialized workflow-effective gates, verifier replay, strict check_gates.py enforcement, and reconstructible PASS / PROD-PASS qualification
```

A passing test suite or reference fixture supports the release-grade path.

It is not by itself the completed public release-grade reference run record.

## Proof target

The target proof is a public, reconstructible release-grade reference run.

The proof should show:

```text
recorded ref
recorded commit
run_mode = prod
diagnostics.gates_stubbed = false
diagnostics.scaffold = false
current-run required-gate evidence archived
pre-materialization candidate snapshot preserved
canonical recorded-release candidate envelopes present
candidate index present
workflow-effective materialized gate set recorded
recorded release evidence verified
release-grade status contract validated
workflow-effective gates enforced by check_gates.py
release_decision_v0.json produced
artifact_provenance_binding_v0.json produced
PULSE_safe_pack_v0/artifacts/release_authority_v0.json produced as audit/trace sidecar
audit/review bundle assembled
operator/reviewer can reconstruct the decision from recorded artifacts
reference-run checker accepts the package as PASS / PROD-PASS
```

## Non-targets

This plan does not require immediate hosted external model execution.

Hosted external evidence remains governed by the active policy and workflow-effective gate set.

If active policy requires hosted external evidence, the qualifying run must include and verify the required external evidence artifacts.

If active policy does not require hosted external evidence for the run mode, the run record must state that external evidence was not required for that run.

This plan also does not treat reader surfaces as proof.

The following surfaces may describe or summarize proof state, but they are not the proof itself:

```text
README
documentation page
summary page
release note
metadata record
publication surface
dashboard
```

## Required proof identity

A complete release-grade reference proof must identify the run by ref and commit.

Required identity fields:

```text
repository
ref
commit
workflow name
workflow run id or URL
workflow run attempt
workflow inputs
run mode
CI outcome
```

The ref may be a branch ref or a tag ref.

Examples:

```text
refs/heads/main
refs/tags/v...
refs/tags/V...
```

A branch-only identity is not sufficient for the general release-grade proof model because version-tag release paths are valid release-grade lanes.

## Required proof inputs

A complete release-grade reference proof should identify the following inputs.

```text
repository
ref
commit
workflow name
workflow run id or URL
workflow run attempt
workflow inputs
run_mode = prod
declared gate policy
gate registry
status artifact
pre-materialization status candidate
current-run required-gate evidence
canonical recorded-release candidate envelopes
candidate index
release evidence input manifest
recorded release evidence verifier report
workflow-effective materialized gate set
release decision artifact
artifact provenance binding artifact
audit/trace sidecar
check_gates enforcement command
CI outcome
```

Each evidence-bearing artifact should be identified by path and digest where possible.

## Required run conditions

A qualifying release-grade reference run should satisfy these conditions.

```text
1. The run is produced from a recorded ref and commit.
2. The run uses the intended release-grade path.
3. The run records run_mode = prod.
4. The run does not use stubbed gate state.
5. The run does not use scaffold status for release-grade proof.
6. The declared policy is known and recorded.
7. The workflow-effective materialized gate set is produced.
8. The workflow-effective materialized gate set covers all gates required for the run, including required + release_required when both sets are active.
9. Current-run required-gate evidence is archived.
10. The pre-materialization candidate snapshot is preserved.
11. Canonical recorded-release candidate envelopes are present.
12. The candidate index is present.
13. The recorded release evidence verifier report is produced.
14. The release-grade status schema validation passes.
15. check_gates.py enforces the workflow-effective materialized gate set.
16. release_decision_v0.json is produced.
17. artifact_provenance_binding_v0.json is produced.
18. PULSE_safe_pack_v0/artifacts/release_authority_v0.json is produced as audit/trace sidecar.
19. The final PASS / PROD-PASS qualification is reconstructible from artifacts.
```

## Required artifact set

A completed release-grade reference proof must include or point to the following artifact classes.

```text
status.json
status_baseline.json
required_gate_evidence_v0.json
canonical recorded-release candidate envelopes
recorded-release candidate index
release_evidence_input_manifest_v0.json
recorded_release_evidence_verifier_v0.json
workflow-effective materialized gate set
release_decision_v0.json
artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
release-authority audit bundle
operator handoff report, when produced by the run
CI logs or run link
artifact digest list
```

Concrete PULSE-REF package contexts may use artifact names such as:

```text
gates/materialized_gate_sets.json
```

The implemented release-authority audit/trace sidecar is:

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

This sidecar supports review and traceability.

It is not an independent release-authority engine.

## Required external evidence artifacts

External evidence is required when the active policy and workflow-effective gate set require it.

When required, the release-grade reference proof must include the corresponding external evidence artifacts and verification reports.

Required external evidence may include:

```text
external summary
external raw or evaluator artifact, when applicable
external summary envelope
attestation bundle, when applicable
external attestation verifier report
signer identity or provenance identity
summary digest
subject digest
fold-in admission result
```

The external evidence must satisfy the applicable schema, semantic, signer, digest, subject, and cryptographic attestation verification requirements.

If the active policy does not require external evidence for the run mode, the run record must state that external evidence was not required.

## Hosted external evidence lane

The hosted external evidence lane is governed by workflow context and active policy.

For workflow_dispatch runs, hosted external evidence may be selected through the hosted_full_runtime mode.

For version-tag release paths, hosted external evidence may be required when active policy and workflow-effective gates require it.

Therefore, hosted external evidence must not be described globally as optional.

A hosted external runtime proof should be attempted only when:

```text
provider access is available
model authorization is available
cost is acceptable
credentials are controlled
the workflow path can be run without changing release metadata
the resulting evidence can be verified and reconstructed
```

Tier 0 self-contained evidence-floor operation does not require hosted external runtime access.

## Self-contained release-grade preparation path

Before attempting hosted runtime proof, PULSEmech should maintain a self-contained preparation path.

This path should verify:

```text
policy-to-required-gate materialization
workflow-effective gate set construction
current-run required-gate evidence production
recorded evidence verifier behavior
canonical candidate production
candidate index construction
release-grade candidate evidence path
release-grade status contract
release decision construction
artifact provenance binding
release-authority audit/trace sidecar construction
reference package assembly
reference package verification
audit bundle neutrality
reader-surface non-interference
operator handoff
```

This preparation path reduces risk before any provider-dependent external runtime run.

## Evidence acceptance rules

Evidence should not be accepted into the release-grade proof unless it satisfies the relevant contract.

Required acceptance properties:

```text
schema-valid
regular file, not symlink
digest-bound
policy-admitted
verifier-checked
non-stubbed
non-scaffolded for release-grade proof
traceable to run context
connected to the workflow-effective materialized gate set
```

External evidence additionally requires:

```text
allowed signer or provenance identity where required
verified attestation where required
summary digest match
subject digest match
fold-in allowed only after verification
```

## Block conditions

The reference proof must preserve block semantics.

A release transition should remain blocked if any of the following occur:

```text
run_mode is not prod
diagnostics.gates_stubbed is true
diagnostics.scaffold is true
workflow-effective materialized gate set is missing
workflow-effective materialized gate set is empty
current-run required-gate evidence is missing
pre-materialization candidate snapshot is missing
canonical recorded-release candidates are missing
candidate index is missing
recorded release evidence is missing
required evidence is unverifiable
required evidence digest does not match
required gate is missing
required gate is not literal true
verifier replay fails
release-grade status schema validation fails
check_gates.py fails
release_decision_v0.json is missing
artifact_provenance_binding_v0.json is missing
required external evidence is omitted when active policy requires it
external evidence is admitted without required verification
reader surface is used as substitute for machine-readable evidence
```

A block result is not a tooling failure when it is caused by missing or failed evidence.

A block result is a valid fail-closed release-transition decision.

A block result is not, by itself, a completed public non-stubbed release-grade reference proof.

## Qualification criteria

A public release-grade reference run may be recorded as completed only when the following criteria are met.

```text
1. The run is public or externally inspectable.
2. The ref and commit are recorded.
3. The workflow run and attempt are recorded.
4. The run records run_mode = prod.
5. Stubbed/scaffolded release status is absent.
6. The workflow-effective required gate set is materialized from declared policy and run context.
7. Current-run required-gate evidence is present.
8. Pre-materialization candidate status is preserved.
9. Canonical recorded-release candidate envelopes are present.
10. The candidate index is present.
11. Verifier replay is recorded.
12. check_gates.py enforces the workflow-effective materialized gate set.
13. release_decision_v0.json is present.
14. artifact_provenance_binding_v0.json is present.
15. PULSE_safe_pack_v0/artifacts/release_authority_v0.json is present as audit/trace sidecar.
16. Required external evidence is present and verified when active policy requires it.
17. All required artifacts are present and digest-identifiable.
18. The audit/review bundle is present.
19. The proof record states what was proven and what was not proven.
20. The reference-run checker accepts the package as PASS / PROD-PASS.
```

A fail-closed block may be recorded as a valid blocked transition.

It must not be recorded as a completed qualified release-grade reference proof unless the documented reference-run checker accepts it under the applicable contract.

## Proof record format

After a qualifying run, record the completed public run in the existing run-note file:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

The run note should contain:

```text
run identity
repository
ref
commit
workflow
run id / URL
run attempt
inputs
run_mode = prod
artifact list
digest list
status summary
gate policy
workflow-effective materialized gate set
verifier result
check_gates result
release_decision_v0.json reference
artifact_provenance_binding_v0.json reference
release_authority_v0.json audit/trace sidecar reference
audit bundle reference
reference-run checker result
known limitations
non-claims
reproduction steps
```

This plan file should not be edited into a run record.

A plan and a run record are separate documents.

## Reproduction procedure

A reviewer should be able to reconstruct the release decision using the recorded artifact set.

Minimum reproduction procedure:

```text
1. Check out the recorded commit.
2. Restore or download the recorded artifact set.
3. Verify artifact digests.
4. Load the declared gate policy.
5. Load the gate registry.
6. Load current-run required-gate evidence.
7. Load the pre-materialization candidate snapshot.
8. Load canonical recorded-release candidate envelopes.
9. Load the candidate index.
10. Load the release evidence input manifest.
11. Run the recorded evidence verifier.
12. Materialize the workflow-effective required gate set.
13. Validate the release-grade status contract.
14. Run check_gates.py against the workflow-effective materialized gate set.
15. Verify release_decision_v0.json.
16. Verify artifact_provenance_binding_v0.json.
17. Inspect release_authority_v0.json as audit/trace sidecar.
18. Compare the reproduced result with the recorded CI decision.
19. Confirm the reference-run checker result is PASS / PROD-PASS.
```

The proof is stronger when the reviewer can reproduce the decision without relying on reader surfaces.

## Relationship to existing tests

Existing tests support the proof plan by checking contracts and wiring.

Relevant test families include:

```text
release evidence verifier tests
recorded release evidence tests
release evidence input manifest tests
release evidence pre-materialization pipeline tests
required-gate current-run evaluator coverage tests
release-grade candidate evidence path tests
release-grade status contract tests
materialize release-required tests
release decision tests
artifact provenance binding tests
release-authority audit/trace sidecar tests
release-grade reference run checker tests
release-grade reference package tests
reference package assembly wiring tests
reference package verification wiring tests
audit bundle workflow neutrality tests
reader-surface non-interference tests
```

Passing tests support confidence in the mechanism.

The public reference proof still requires a qualifying run record.

## Relationship to PULSE-REF packages

PULSE-REF packages can support reproducible review.

A PULSE-REF package can provide:

```text
minimal reference package layout
manifest
digest coverage
gates/materialized_gate_sets.json
CI outcome
operator handoff report
publication snapshot
verifier report
operating proof summary
```

A PULSE-REF package is strongest when it is tied to a concrete release-grade run and its recorded evidence artifacts.

## Relationship to SLSA / provenance

SLSA / in-toto-style provenance may support the proof by describing artifact construction and input identity.

PULSEmech still evaluates the release transition separately.

The release-grade proof should preserve this separation:

```text
provenance statement
→ evidence input

PULSEmech verifier and gate path
→ transition decision
```

The artifact provenance binding artifact is part of the evidence chain:

```text
artifact_provenance_binding_v0.json
```

## Relationship to developer-first adoption

The release-grade proof should be readable by technical maintainers.

A developer, release engineer, or external technical reviewer should be able to answer:

```text
What was run?
Which ref and commit produced it?
What evidence was used?
Which policy applied?
Which gates were workflow-effective?
Which verifier replay ran?
Which gates passed?
Which artifact digests bind the result?
Where did CI enforce the decision?
Can the decision be reconstructed?
Did the reference-run checker accept it as PASS / PROD-PASS?
```

If those questions cannot be answered from recorded artifacts, the proof is not complete.

## Deferred hosted-runtime proof

Hosted runtime proof remains deferred when external provider execution is unavailable, unaffordable, unauthorized, or operationally unsuitable.

Deferred hosted runtime proof should be recorded explicitly.

It should not be hidden by changing terminology.

The correct state is:

```text
hosted runtime proof deferred
```

not:

```text
completed
```

until a qualifying hosted run exists.

## Minimum next action

The next practical step is to assemble a self-contained release-grade reference proof candidate without hosted runtime execution.

That candidate should verify:

```text
non-stubbed release-grade status path
current-run required-gate evidence production
canonical recorded-release candidate production
candidate index production
recorded evidence verifier replay
workflow-effective gate materialization
check_gates.py enforcement
release_decision_v0.json production
artifact_provenance_binding_v0.json production
release_authority_v0.json audit/trace sidecar production
reference package assembly
reference package verification
reference-run checker qualification
```

If the self-contained candidate cannot satisfy non-stubbed release-grade criteria, it should be recorded as a preparation milestone rather than a completed public release-grade reference run.

## Summary

This proof plan defines the path from existing PULSEmech evidence mechanisms to a public non-stubbed release-grade reference run.

The plan preserves three boundaries:

```text
Tier 0 self-contained evidence floor is valuable but not identical to a completed public non-stubbed release-grade reference run.

Hosted external runtime proof is deferred until provider access, authorization, cost, and verification conditions are suitable.

A completed release-grade reference run requires ref + commit identity, run_mode = prod, current-run evidence, canonical candidates, workflow-effective materialized gates, verifier replay, check_gates enforcement, release decision artifact, provenance binding artifact, audit/trace sidecar, and PASS / PROD-PASS acceptance by the reference-run checker.
```
