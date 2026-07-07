# PULSE SLSA VSA — release-required promotion criteria v0

## WORKMARK

Status: criteria document only.

This document defines the criteria that must be satisfied before any future SLSA VSA recorded-intake lane can be promoted from non-active candidate proof to active release-required enforcement.

This document does not activate SLSA VSA as release-required.

## Current state

The SLSA VSA recorded-intake candidate path is complete and proven.

Completed sequence:

```text
#2689 — register non-active slsa_vsa_recorded_intake_candidate
#2690 — allow declared gate-set materialization
#2691 — prove recorded-intake candidate path
```

Boundary document:

```text
docs/slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md
```

## Promotion is a separate decision

Candidate proof is not release-required activation.

Materialized candidate gates prove that the path can be checked.

They do not by themselves authorize release blocking or release allowing behavior.

Any future promotion must be a separate PR.

## Required promotion criteria

Before SLSA VSA can be added to any active release-required lane, all criteria below must be satisfied.

### 1. Trusted recorded evidence producer

A promotion PR must identify the trusted evidence producer that generates or supplies the SLSA VSA evidence accepted by CI.

The producer must be bound to the current release artifact or release candidate.

The producer must not be a manually copied status boolean.

The producer must not be a local self-declared status patch.

### 2. Artifact binding

The accepted VSA evidence must bind to the release artifact subject.

The subject name and digest must match the artifact under evaluation.

A mismatch must fail closed.

### 3. Policy binding

The accepted VSA evidence must bind to the expected policy identity or policy digest.

A missing, stale, unexpected, or mismatched policy digest must fail closed.

### 4. Verifier trust boundary

The verifier identity must be explicitly trusted.

An unknown verifier must fail closed.

A missing verifier identity must fail closed.

### 5. Recorded signal boundary

The current recorded-intake path uses:

```text
recorded_signal_only
```

This means the lane records and checks supplied signal values, but it is not yet a cryptographic signature verification lane.

A promotion PR must explicitly state whether it is still using `recorded_signal_only` or whether a stronger signature verification mode has been introduced.

If still using `recorded_signal_only`, the release-required boundary must document why the producer is trusted enough for release blocking.

### 6. Anti-self-declared-boolean rule

Release-required SLSA VSA gates must not be created by copying booleans directly into `status.json`.

They must be derived from recorded evidence through a reviewed intake and fold-in path.

The accepted path must be:

```text
recorded evidence
→ intake report
→ validated checks
→ folded status.gates
→ policy materialization
→ check_gates.py
```

### 7. Advisory-to-required separation

Advisory SLSA VSA gates cannot be promoted merely because they exist in the advisory set.

Promotion requires explicit release-required policy change and test coverage.

Candidate proof and advisory registration are not sufficient by themselves.

### 8. Fail-closed behavior

A promotion PR must prove fail-closed behavior for at least:

```text
missing VSA evidence
invalid VSA schema
subject digest mismatch
resource URI mismatch
policy digest mismatch
unknown verifier
verificationResult != PASSED
missing verified level
false SLSA VSA gate
missing SLSA VSA gate
stale or mismatched intake report
```

### 9. CI provenance boundary

The promotion PR must identify where in CI the evidence is produced, read, verified, folded, and enforced.

The CI path must avoid ambiguous artifact reuse.

The CI path must avoid using stale evidence from a previous run.

The CI path must make the evidence source auditable.

### 10. Release-authority effect

A promotion PR must explicitly state the release-authority effect.

It must say whether SLSA VSA gates become part of:

```text
release_required
prod_required
release_blocking
```

or another active release-authority set.

The effect must be visible in the PR title, PR body, policy changelog, and tests.

### 11. Rollback behavior

A promotion PR must define rollback behavior.

At minimum, rollback must be possible by removing the SLSA VSA gates from the active release-required lane while preserving the non-active candidate proof history.

Rollback must not require deleting evidence docs, schemas, examples, or candidate proof tests.

### 12. Required tests before promotion

A promotion PR must include tests proving:

```text
active policy materialization includes the promoted SLSA VSA gates
valid recorded evidence passes the active lane
missing evidence fails closed
false evidence fails closed
mismatched evidence fails closed
check_gates.py remains generic
candidate proof still passes
advisory behavior remains non-blocking unless explicitly promoted
```

## Expected promotion PR shape

A future promotion PR should be small and explicit.

Expected changed files may include:

```text
pulse_gate_policy_v0.yml
docs/policy/CHANGELOG.md
tests/...
ci/tools-tests.list
tests/fixtures/core_baseline_v0/status.normalized.json
```

Workflow changes should only be included if the promotion requires a new CI evidence-production step.

## Forbidden bundling

A promotion PR must not be bundled with unrelated work.

Do not combine promotion with:

```text
DOI changes
Zenodo changes
CITATION changes
README title changes
unrelated workflow cleanup
unrelated registry expansion
unrelated release packaging
```

## Current non-activation statement

At the time of this document, SLSA VSA is not active as:

```text
required
core_required
release_required
prod_required
stage_required
blocking
release_blocking
```

The current state remains:

```text
non-active candidate proof complete
release-required promotion not yet performed
```
