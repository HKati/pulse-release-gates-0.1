# PULSEmech recovery ledger v0

## Purpose

This ledger records operational maintenance, recovery, containment, and verification decisions for the PULSEmech repository.

It is a repository maintenance document.

It is not a release-authority source.

It does not define gate policy, verifier behavior, materializer behavior, workflow enforcement, schema behavior, or release-authority semantics.

## Entry format

Each entry should record:

```text
date
area
status
scope
evidence
decision
next action
```

Operational incidents and recovery decisions should be recorded here instead of being embedded in permanent technical alignment documents.

---

## 2026-07-02 — PULSEmech / SLSA provenance-to-transition alignment

### Area

```text
documentation
supply-chain alignment
provenance
release-transition model
```

### Status

```text
completed
verified
merged
```

### Scope

Added:

```text
docs/PULSEMECH_SLSA_PROVENANCE_TO_TRANSITION_v0.md
```

### Evidence

Post-merge verification result:

```text
PASS
```

Verified:

```text
file exists on merged repository state
professional technical alignment note
no temporary Zenodo / DOI incident content
no rhetorical/slogan terms
all fenced JSON blocks parse as valid JSON
SLSA example uses expected in-toto / SLSA predicate values
PULSEmech examples use project-specific release-transition predicate
no SLSA conformance claim
no certification claim
no compliance status claim
no claim that PULSEmech replaces SLSA
documentation-only merge
```

### Impact

```text
workflow change: no
runtime code change: no
gate policy change: no
verifier/materializer/schema change: no
release-authority semantic change: no
```

### Decision

```text
closed
```

---

## 2026-07-02 — Artifact provenance attestation wiring CI failure

### Area

```text
CI
tools-tests
artifact provenance attestation wiring
```

### Status

```text
triaged
closed unless reproduced
```

### Observed failure

A previous `tools-tests` run failed in:

```text
tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

with:

```text
ValueError: substring not found
```

The failure occurred while the test was looking for the pinned `actions/attest` reference inside the extracted attestation workflow block.

The uploaded CI log showed the `tools-tests` manifest running 99 entries and failing at the artifact provenance binding attestation wiring smoke test after many preceding release-authority, verifier, materializer, schema, evidence, attestation, reader-surface, and fail-closed checks had passed.

### Current verification

The targeted test was rerun on the current branch.

```text
python tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

Result:

```text
PASS
```

The workflow `actions/attest` references are pinned to the expected immutable SHA, and the test `ATTEST_SHA` matches that value.

### Decision

```text
No current branch defect found.
Treat the previous failure as stale / branch-specific unless reproduced.
No workflow patch.
No attestation pin change.
No test change.
```

### Next action

```text
If the failure appears again on current main or an active merge target, reproduce first with the targeted test before changing workflow or test code.
```

---

## 2026-07-02 — Dependabot actions/attest pin update

### Area

```text
dependency update
attestation boundary
GitHub Actions
```

### Status

```text
blocked intentionally
not merged
```

### Scope

Dependabot proposed updating the pinned `actions/attest` action.

### Decision

Do not merge automatic attestation action pin changes without manual provenance/security review.

### Reason

The attestation action is part of the artifact provenance and release-evidence path.

Changing the pinned attestation action is not treated as a routine dependency update.

### Impact

```text
workflow semantic risk: medium
release-authority boundary risk: medium
```

### Next action

```text
Future attestation action pin changes require coordinated review of workflow references, test constants, attestation envelope metadata, and provenance verification expectations.
```

---

## 2026-07-02 — Zenodo version-record correction request

### Area

```text
Zenodo
software version records
citation routing
repository identity
```

### Status

```text
waiting for Zenodo Support
```

### Scope

Three unintended GitHub-triggered Zenodo software version records were identified as requiring correction / deletion.

### Records

```text
1. pulsemech-tier0-floor-preservation-20260629
   10.5281/zenodo.21031131

2. pulsemech-tier0-floor-20260628-b
   10.5281/zenodo.21006429

3. tier0-self-contained-evidence-floor-2026-06-27
   10.5281/zenodo.21003082
```

### Protected identifiers

The following identifiers are protected and must remain unchanged:

```text
Concept DOI / all versions:
10.5281/zenodo.17214908

Retained repository software citation DOI:
10.5281/zenodo.17373002

Preprint / documentation DOI:
10.5281/zenodo.17833583
```

### Current boundary

```text
No new GitHub release.
No new Zenodo publication.
No new DOI.
No tag changes.
No GitHub-Zenodo integration changes without Zenodo guidance.
```

### External status

A project-side confirmation email was sent to Zenodo Support from the EPLabsAI account.

### Decision

```text
waiting
```

---

## 2026-07-02 — Tier 0 repository documentation records

### Area

```text
documentation
Tier 0 self-contained evidence floor
publication-surface snapshot
```

### Status

```text
present
no restore needed
```

### Files verified present

```text
docs/TIER0_SELF_CONTAINED_PULSE_RUN_2026-06-27.md
docs/PULSEMECH_TIER0_PUBLICATION_SNAPSHOT_v0.md
```

### Decision

```text
No duplicate restore.
No GitHub release.
No Zenodo publication.
No DOI action.
closed
```

---

## 2026-07-02 — Hosted external-evidence lane status

### Area

```text
README state
signer identity
attested external evidence
hosted runtime lane
```

### Status

```text
policy-declared
workflow-wired
operational hosted runtime proof deferred
```

### Existing implementation evidence

The signer policy declares an exact GitHub Actions workflow identity for release-grade LlamaGuard summary attestations:

```text
repo:HKati/pulse-release-gates-0.1:workflow:.github/workflows/pulse_ci.yml
```

The LlamaGuard tool policy admits this exact identity group for release-grade contribution.

The workflow contains an opt-in hosted external-evidence path controlled by:

```text
strict_external_evidence=true
llamaguard_evidence_mode=hosted_full_runtime
```

The workflow path includes:

```text
current-run LlamaGuard evidence download
canonical evidence copy
actions/attest attestation of llamaguard_summary.json
attestation envelope construction
cryptographic verification replay
attested evidence artifact upload
release-grade recorded path continuation
```

### Decision

The previous `Pending` wording is not precise enough.

The status should distinguish implemented policy/wiring from deferred hosted runtime execution.

### README status target

```text
Exact operational release-grade signer identity:
Implemented at policy/wiring level — exact GitHub Actions workflow identity declared for release-grade LlamaGuard summaries; hosted runtime proof deferred.

Current-run attested external-evidence production lane:
Implemented as opt-in workflow lane — hosted_full_runtime attestation, envelope, verification, and recorded-path wiring present; operational hosted runtime proof deferred; Tier 0 does not require hosted runtime.
```

### Reason

Hosted runtime execution may require external provider access and substantial cost.

Tier 0 self-contained evidence-floor operation does not require hosted runtime access.

### Decision

```text
README clarification recommended.
No workflow change.
No runtime code change.
No gate policy change.
No release-authority semantic change.
```

---

## Open items

### Zenodo support response

```text
status: waiting
next action: wait for Zenodo Support response
```

### README hosted external-evidence status clarification

```text
status: ready for documentation-only update
next action: replace imprecise Pending rows with policy/wiring implemented + hosted proof deferred wording
```

### Developer-first positioning

```text
status: next documentation work
candidate file:
docs/PULSEMECH_DEVELOPER_FIRST_POSITIONING_v0.md
```

### Required checks and workflow authority map

```text
status: planned
candidate file:
docs/PULSEMECH_REQUIRED_CHECKS_AND_WORKFLOW_AUTHORITY_v0.md
```

### Dependency single-truth plan

```text
status: planned
candidate file:
docs/maintenance/PULSEMECH_DEPENDENCY_SINGLE_TRUTH_PLAN_v0.md
```
