# PULSEmech release-grade reference proof plan v0

## Status

Technical proof plan.

This document defines the evidence, run conditions, artifacts, and review criteria required before a public non-stubbed release-grade reference run can be recorded for PULSEmech.

It is not a run record.

It does not mark any pending implementation-state item as completed.

It does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, branch protection settings, or release-authority semantics.

## Purpose

PULSEmech already has a self-contained Tier 0 evidence floor and a broad release-authority test surface.

The remaining release-grade maturity question is different:

```text
Can a complete, public, non-stubbed release-grade reference run be reconstructed from recorded evidence, declared policy, materialized required gates, verifier replay, and CI enforcement?
```

This proof plan defines the conditions for answering that question.

## Current distinction

PULSEmech has multiple evidence layers.

They should not be collapsed into one status.

```text
Tier 0 self-contained evidence floor
→ demonstrates that the base evidence path can run without hosted external model access

Release-grade reference package tests
→ demonstrate package, schema, verifier, and reference-bundle contracts

Full public non-stubbed release-grade reference run
→ requires an operational run record with non-stubbed status, materialized release-required gates, verifier replay, and enforceable allow/block result
```

A passing test suite or reference fixture is necessary support.

It is not by itself the final public release-grade run record.

## Proof target

The target proof is a public, reconstructible release-grade reference run.

The proof should show:

```text
run_mode = prod
diagnostics.gates_stubbed = false
diagnostics.scaffold = false
release-required gate set materialized
recorded release evidence verified
release-grade status contract validated
release-required gates enforced by check_gates.py
release-authority manifest produced
audit/review bundle assembled
operator/reviewer can reconstruct the decision from recorded artifacts
```

## Non-targets

This plan does not require an immediate hosted external model run.

Hosted external evidence remains a separate operational lane.

A hosted external runtime proof should be attempted only when suitable provider access, model authorization, cost conditions, and verification conditions are available.

This plan also does not treat reader surfaces as proof.

The following surfaces may describe or summarize the proof, but they are not the proof itself:

```text
README
documentation page
summary page
release note
metadata record
publication surface
dashboard
```

## Required proof inputs

A complete release-grade reference proof should identify the following inputs.

```text
repository
branch
commit
workflow name
workflow run id or URL
workflow run attempt
workflow inputs
run mode
declared gate policy
gate registry
status artifact
recorded release evidence artifacts
release evidence input manifest
recorded release evidence verifier report
materialized required gate set
release-authority manifest
check_gates enforcement command
CI outcome
```

Each evidence-bearing artifact should be identified by path and digest where possible.

## Required run conditions

The reference run should satisfy these conditions.

```text
1. The run is produced from a known branch and commit.
2. The run uses the intended release-grade path.
3. The run records run_mode = prod.
4. The run does not use stubbed gate state.
5. The run does not use scaffold status for release-grade proof.
6. The declared policy is known and recorded.
7. The required release gate set is materialized from policy and verifier state.
8. The recorded evidence verifier report is produced.
9. The release-grade status schema validation passes.
10. The release-required gate set is enforced by check_gates.py.
11. The release-authority manifest is produced and reviewable.
12. The final allow/block decision is reconstructible from artifacts.
```

## Required artifact set

A release-grade reference proof should include or point to the following artifact classes.

```text
status.json
status_baseline.json, if applicable
required_gate_evidence_v0.json, if applicable
release_evidence_input_manifest_v0.json
recorded_release_evidence_verifier_v0.json
materialized_required_gates_v0.json, if produced as a separate artifact
release_authority_manifest_v0.json
release decision output, if separate
release-authority audit bundle
operator handoff report, if produced
CI logs or run link
artifact digest list
```

If external evidence is included, it must also include:

```text
external summary
external raw/evaluator artifact, if applicable
external summary envelope
attestation bundle, if applicable
external attestation verifier report
signer identity or provenance identity
fold-in admission result
```

## Hosted external evidence lane

The hosted external evidence lane is treated separately.

It may later produce:

```text
current-run external evaluator output
attested external summary
attestation envelope
cryptographic verification report
attested external-evidence artifact package
release-grade recorded path continuation
```

A hosted external runtime proof is not required for Tier 0 self-contained operation.

It should remain deferred until:

```text
provider access is available
model authorization is available
cost is acceptable
credentials are controlled
the workflow path can be run without changing release metadata
the resulting evidence can be verified and reconstructed
```

## Self-contained release-grade preparation path

Before attempting hosted runtime proof, PULSEmech should maintain a self-contained preparation path.

This path should verify:

```text
policy-to-required-gate materialization
recorded evidence verifier behavior
release-grade candidate evidence path
release-grade status contract
release-authority manifest construction
reference package assembly
reference package verification
audit bundle neutrality
reader-surface non-interference
operator handoff
```

This preparation path reduces risk before any expensive or provider-dependent external runtime run.

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

The run should be considered not qualified if any of the following occur:

```text
run_mode is not prod
diagnostics.gates_stubbed is true
diagnostics.scaffold is true
release-required gate set is empty
required evidence is missing
required evidence is unverifiable
required evidence digest does not match
required gate is missing
required gate is not literal true
verifier replay fails
release-grade status schema validation fails
check_gates.py fails
external evidence is admitted without required verification
reader surface is used as substitute for machine-readable evidence
```

A block result is not a tooling failure if it is caused by missing or failed evidence.

A block result is a valid release-transition decision.

## Qualification criteria

A public release-grade reference run may be recorded only when the following criteria are met.

```text
1. The run is public or externally inspectable.
2. The branch and commit are recorded.
3. The workflow run and attempt are recorded.
4. The run mode is release-grade.
5. Stubbed/scaffolded release status is absent.
6. Required gates are materialized from declared policy.
7. Verifier replay is recorded.
8. check_gates.py enforces the materialized required set.
9. The decision is allow or block and is reconstructible.
10. All required artifacts are present and digest-identifiable.
11. The release-authority manifest is present.
12. The audit/review bundle is present.
13. The proof record states what was proven and what was not proven.
```

## Proof record format

After a qualifying run, create a separate run record.

Candidate file:

```text
docs/PULSEMECH_RELEASE_GRADE_REFERENCE_RUN_RECORD_v0.md
```

The run record should contain:

```text
run identity
branch
commit
workflow
run id / URL
run attempt
inputs
run mode
artifact list
digest list
status summary
gate policy
materialized required gates
verifier result
check_gates result
decision
audit bundle reference
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
6. Load the recorded release evidence.
7. Run the recorded evidence verifier.
8. Materialize the required release gate set.
9. Validate the release-grade status contract.
10. Run check_gates.py against the materialized required set.
11. Compare the reproduced result with the recorded CI decision.
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
release-grade candidate evidence path tests
release-grade status contract tests
materialize release-required tests
release-authority manifest tests
release-grade reference run checker tests
release-grade reference package tests
reference package assembly wiring tests
reference package verification wiring tests
audit bundle workflow neutrality tests
reader-surface non-interference tests
artifact provenance binding tests
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
materialized gate sets
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

## Relationship to developer-first adoption

The release-grade proof should be readable by technical maintainers.

A developer, release engineer, or external technical reviewer should be able to answer:

```text
What was run?
What evidence was used?
Which policy applied?
Which gates were required?
Which verifier replay ran?
Which gates passed or failed?
Which artifact digests bind the result?
Where did CI enforce the decision?
Can the decision be reconstructed?
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
recorded evidence verifier replay
release-required materialization
check_gates.py enforcement
release-authority manifest construction
reference package assembly
reference package verification
```

If the self-contained candidate cannot satisfy non-stubbed release-grade criteria, it should be recorded as a preparation milestone rather than a completed public release-grade reference run.

## Summary

This proof plan defines the path from existing PULSEmech evidence mechanisms to a public non-stubbed release-grade reference run.

The plan preserves three boundaries:

```text
Tier 0 self-contained evidence floor is valuable but not identical to full release-grade operational proof.

Hosted external runtime proof is deferred until provider access, authorization, cost, and verification conditions are suitable.

A completed release-grade reference run requires reconstructible recorded evidence, declared policy, materialized required gates, verifier replay, check_gates enforcement, and a public run record.
```
