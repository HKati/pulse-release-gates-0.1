# PULSE Release-Grade Next Run Plan v0

## Purpose

PULSE is an artifact-bound release-authority system for AI release decisions.

This document defines the next release-grade reference run plan for PULSE.

The goal is to move from core/smoke/scaffold demonstration toward the first recorded, non-stubbed, non-scaffolded, release-grade reference state.

This plan does not redefine PULSEmech.

It prepares the next proof state for PULSEmech:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ declared-policy CI allow/block release decision

The release-grade reference run is the next anchor for fellowship-stage and HPC-supported validation work.

## Run terminology

In this plan, “run” means the recorded, artifact-bound reference state produced by a run.

It includes the preserved `status.json`, declared policy, materialized required gate set, declared-policy gate-enforcement CI outcome, release authority manifest, audit bundle, artifact hashes, reader-surface parity checks, and reconstruction evidence.

It does not mean an ephemeral CI event by itself.

A release-grade reference run is accepted only when its recorded artifacts reconstruct the declared-policy release decision.

## Core thesis

PULSE already has a working release-authority materialization path.

The next step is to produce a reference run where that materialization path operates on release-grade evidence rather than scaffolded or stubbed surfaces.

The release-grade next run must show that PULSE can preserve:

- recorded evidence
- declared policy
- materialized required gates
- strict fail-closed enforcement
- external evidence when required
- audit reconstruction
- reader-surface parity
- archived artifact identity
- deterministic declared-policy allow/block decision  

The run should be small enough to audit and strong enough to serve as the baseline for later HPC candidate-state validation.

## Authority boundary

Release authority remains limited to the declared PULSEmech path.

The release-grade reference run is authorized only through:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ declared-policy CI allow/block release decision

Reader, audit, preservation, publication, HPC, and diagnostic surfaces may render, preserve, inspect, or support reconstruction and consistency review of the decision.

They do not create a second release-decision engine.

A live URL is not release authority by itself.

A public surface is relevant to authority review only when bound to the recorded run identity and source artifact.

## Target state

The target state is the first PULSE release-grade reference run with materialized evidence.

The target run should satisfy:

- selected release-grade lane is declared
- recorded `status.json` artifact is produced
- required gate set is derived from declared policy
- required gate set is materialized before enforcement
- strict true-only gate evaluation is used
- no required release-grade gate is missing
- no required release-grade gate is false
- no required release-grade gate is non-boolean
- detector evidence is materialized
- external summaries are present when required by policy
- external summaries pass when required by policy
- scaffolded release-grade state is rejected
- stubbed gate surface is rejected
- release authority manifest is produced
- audit bundle is produced
- Quality Ledger rendering is produced
- reader-surface parity is checked
- artifact hashes are recorded
- run identity is preserved
- decision can be reconstructed from archived artifacts

## Run identity

The release-grade reference run must preserve a stable run identity.

Required identity fields:

- `run_id`
- `git_sha`
- `created_utc`
- selected lane
- workflow name
- workflow run ID when available
- artifact source
- artifact hash when available
- policy path
- policy hash
- recorded `status.json` path
- recorded `status.json` hash
- materialized required gate set hash
- manifest hash
- audit bundle hash
- Quality Ledger hash when available

A reader surface may display the state.

The recorded artifact identity is the authority anchor.

## Required inputs

The release-grade reference run should start from recorded inputs.

Required inputs:

- declared gate policy
- selected release lane
- recorded release evidence
- status schema version
- required gate registry when used
- materialization script or process
- external detector summary artifacts when required
- threshold profile when relevant
- environment profile
- CI workflow definition
- expected artifact output list

The run must not depend on unstated live state.

## Declared policy and lane

The selected lane must be explicit.

The declared policy must define:

- required gates for the selected lane
- advisory gates for the selected lane
- release-required gates when applicable
- external evidence requirements when applicable
- detector materialization requirements
- strict failure behavior
- allowed evidence types
- expected boolean gate semantics

The selected lane must be recorded in the run artifacts.

The effective required gate set must be derived from this declared policy.

## Materialized required gate set

The required gate set must be materialized before CI enforcement.

The materialized gate set should be preserved as an artifact or recorded in the release authority manifest.

Materialization must be reproducible from:

- declared policy
- selected lane
- policy version or hash
- materialization command or process
- repository commit SHA

A release-grade reference run must fail closed if:

- the required gate set cannot be materialized
- the materialized gate set is missing
- the materialized gate set does not match declared policy
- the enforced gate set differs from the materialized gate set
- the materialized gate set cannot be reconstructed

## Recorded `status.json` artifact

The release-grade reference run must produce a recorded `status.json` artifact.

The recorded `status.json` artifact must be bound to the selected run.

It should include or be associated with:

- schema version
- run mode or release-grade mode
- selected lane
- gate values
- diagnostics relevant to release-grade eligibility
- external summary state when required
- detector materialization state
- run metadata
- created UTC timestamp
- git SHA or equivalent source identity
- artifact source

For release-grade reference use, the recorded `status.json` artifact must not represent a scaffolded or stubbed release-grade state.

## Non-stubbed requirement

The release-grade reference run must operate on materialized evidence.

A release-grade candidate must block if required evidence is represented only by stubbed, scaffolded, fallback, placeholder, or all-true smoke state.

The run should explicitly check:

- `diagnostics.gates_stubbed` is explicitly `false`, or an equivalent current status-contract field explicitly records non-stubbed evidence
- `diagnostics.scaffold` is explicitly `false`, or an equivalent current status-contract field explicitly records non-scaffolded evidence
- missing, malformed, non-boolean, stripped, or fallback release-grade diagnostics fail closed unless the current status contract defines a stricter equivalent field
- stub profile markers are absent from release-grade evidence
- detector materialization evidence is present when required
- required external summaries are present when required
- required external summaries pass when required
- release-grade evidence is not inferred from advisory-only surfaces

The exact field names should follow the current status contract.

The rule is mechanical:

release-grade PASS cannot be inferred from missing, stubbed, scaffolded, fallback, or placeholder evidence.

## External evidence requirement

External evidence participates in release authority only when declared policy requires it.

When required, external detector summaries must be:

- present
- schema-valid
- source-identifiable
- bound to the run
- included in the recorded evidence set
- represented in `status.json`
- included or referenced in the audit bundle
- reflected correctly in reader surfaces
- enforced through required gates

The release-grade reference run must fail closed if required external evidence is:

- missing
- malformed
- false
- not all-pass when all-pass is required
- inconsistent with `status.json`
- inconsistent with the release authority manifest
- not bound to the run identity

## Pre-run failure fixtures

Before accepting the release-grade reference run, the following failure fixtures should be defined or verified.

Minimum failure fixtures:

- missing required gate
- false required gate
- non-boolean required gate
- missing `status.json`
- malformed `status.json`
- schema-invalid `status.json`
- missing declared policy
- required gate set mismatch
- missing external summary when required
- failing external summary when required
- malformed external summary when required
- stubbed detector state
- scaffolded release-grade state
- manifest hash mismatch
- audit bundle incomplete
- Quality Ledger mismatch
- live/public surface mismatch
- advisory-only failure
- shadow-only drift

Expected behavior:

- required gate failures block
- required artifact failures block
- required external evidence failures block
- manifest and audit reconstruction failures block release-grade reference acceptance
- reader parity mismatches block release-grade reference acceptance
- advisory-only failures do not block unless policy declares them required
- shadow-only drift does not alter release permission unless policy promotes a specific output

## Pass criteria

A release-grade reference run passes only when all required conditions are met.

Pass criteria:

1. selected release lane is recorded
2. declared policy is recorded or hash-bound
3. required gate set is materialized from declared policy
4. enforced gate set matches materialized required gate set
5. recorded `status.json` artifact is schema-valid
6. every required gate is literal boolean `true`
7. no required gate is missing
8. no required gate is non-boolean
9. release-grade evidence is non-stubbed
10. release-grade evidence is non-scaffolded
11. detector evidence is materialized when required
12. external summaries are present when required
13. external summaries pass when required
14. release authority manifest is produced
15. audit bundle is produced
16. Quality Ledger rendering is produced
17. reader-surface parity is verified
18. artifact hashes are recorded
19. run identity is preserved
20. release decision can be reconstructed from archived artifacts
21. declared-policy gate-enforcement CI outcome matches reconstructed gate evaluation

A release-grade reference run is not accepted merely because a public page displays a passing state.

It is accepted when recorded artifacts reconstruct the declared-policy CI decision.

## Block criteria

The release-grade reference run must block or fail reference acceptance when any required condition fails.

Block criteria:

- missing required evidence
- missing required gate
- required gate is false
- required gate is non-boolean
- invalid `status.json`
- missing declared policy
- missing materialized required gate set
- enforced gate set differs from materialized gate set
- required detector evidence is not materialized
- required external summaries are missing
- required external summaries fail
- release-grade state is stubbed
- release-grade state is scaffolded
- release decision cannot be reconstructed
- release authority manifest is missing when required
- audit bundle is missing when required
- audit bundle is incomplete
- artifact hash mismatch
- reader-surface parity mismatch
- live/public state is used as a substitute for recorded evidence

The failure behavior is fail-closed.

## Required output artifacts

The release-grade reference run should produce or preserve:

- recorded `status.json`
- declared policy snapshot or policy hash
- materialized required gate set
- external detector summaries when required
- release authority manifest
- audit bundle
- Quality Ledger rendering
- CI result
- gate evaluation output
- reconstruction report
- reader-surface parity report
- artifact hash list
- run metadata
- git SHA
- run ID
- created UTC timestamp
- environment profile
- reproduction command

These artifacts should be sufficient to reconstruct the release decision without relying on mutable live surfaces.

## Release authority manifest requirements

The release authority manifest should record:

- manifest schema version
- run ID
- git SHA
- created UTC timestamp
- selected lane
- policy path
- policy hash
- recorded `status.json` path
- recorded `status.json` hash
- materialized required gate set
- materialized required gate set hash
- declared-policy gate-enforcement CI outcome
- gate evaluation result
- external summary references when required
- audit bundle reference
- Quality Ledger reference
- artifact hash list
- reconstruction command when available

The manifest preserves the trace.

It does not create a second decision engine.

## Audit bundle requirements

The audit bundle should preserve the evidence and decision artifacts needed to reconstruct the run.

Minimum audit bundle contents:

- recorded `status.json`
- declared policy snapshot or hash record
- materialized required gate set
- release authority manifest
- external summaries when required
- gate evaluation output
- CI metadata
- Quality Ledger rendering or hash
- artifact hash list
- reconstruction report when available
- environment profile
- reproduction instructions

The audit bundle should be complete enough for an external reviewer to reconstruct the release decision from archived artifacts.

## Reader-surface parity requirements

Reader surfaces must preserve parity with recorded source artifacts.

Reader surfaces include:

- Quality Ledger
- report card
- badges
- Pages rendering
- summary views

Parity must be checked against the same run identity:

- `run_id`
- `git_sha`
- `created_utc`
- artifact source
- artifact hash when available

Reader-surface parity checks should cover:

- decision state
- gate states
- required gate set
- run mode
- selected lane
- diagnostic flags relevant to release-grade eligibility
- external summary state when rendered
- artifact source
- run metadata

A reader surface may explain.

A reader surface may summarize.

A reader surface may link.

A reader surface must not silently diverge from the recorded artifact it renders.

## Reconstruction requirement

The release-grade reference decision must be reconstructable from archived artifacts.

A reconstruction check should verify:

- recorded `status.json` loads and validates
- declared policy is available or hash-bound
- required gate set can be materialized or matched
- enforced gate set equals materialized required gate set
- all required gates are literal boolean `true` for pass candidates
- block candidates fail closed
- declared-policy gate-enforcement CI outcome matches reconstructed gate result 
- manifest hashes match artifact hashes
- audit bundle contains required artifacts
- reader surfaces match recorded source artifacts

The reconstruction result should be preserved as part of the reference run evidence.

## Minimal release-grade reference fixture set

The next run plan should be supported by a minimal fixture set.

Recommended fixture set:

| Fixture | Expected result | Purpose |
|---|---|---|
| `pass_non_stubbed` | pass | Baseline release-grade candidate with complete materialized evidence |
| `missing_required_gate` | block | Missing required gate fails closed |
| `false_required_gate` | block | Required false gate fails closed |
| `non_boolean_required_gate` | block | Only literal boolean true passes |
| `missing_external_required` | block | Required external evidence must materialize |
| `failing_external_required` | block | Required external evidence must pass |
| `stubbed_release_grade` | block | Stubbed release-grade state rejected |
| `scaffolded_release_grade` | block | Scaffolded release-grade state rejected |
| `manifest_mismatch` | block reference acceptance | Manifest integrity enforced |
| `audit_bundle_incomplete` | block reference acceptance | Audit bundle completeness enforced |
| `reader_surface_mismatch` | block reference acceptance | Reader parity enforced |
| `advisory_only_failure` | no block unless policy requires | Advisory boundary confirmed |
| `shadow_only_drift` | no release-decision change | Shadow boundary confirmed |

This fixture set becomes the immediate bridge toward HPC candidate-state batches.

## Suggested implementation phases

### Phase 1 — Documentation anchor

Deliverable:

- `docs/PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md`

Purpose:

Define the target state, evidence requirements, pass criteria, block criteria, and artifact expectations for the first release-grade reference run.

### Phase 2 — Fixture contract

Deliverables:

- release-grade reference fixture directory
- pass fixture
- fail-closed fixtures
- reader parity mismatch fixture
- manifest mismatch fixture
- audit bundle incomplete fixture
- fixture expectation table
- regression tests

Purpose:

Lock the expected release-grade behavior before producing the reference run.

### Phase 3 — Reference run artifact contract

Deliverables:

- manifest requirements
- audit bundle requirements
- reconstruction requirements
- reader parity requirements
- artifact hash requirements

Purpose:

Ensure the reference run can be reviewed and reconstructed from archived evidence.

### Phase 4 — First non-stubbed release-grade reference run

Deliverables:

- recorded `status.json`
- materialized required gate set
- external summaries when required
- release authority manifest
- audit bundle
- Quality Ledger rendering
- CI result
- reconstruction report
- parity report

Purpose:

Produce the first release-grade PULSE reference state.

### Phase 5 — HPC baseline handoff

Deliverables:

- baseline candidate state
- failure-mode candidate states
- artifact hashes
- reconstruction outputs
- expected decision table
- HPC evidence bundle plan

Purpose:

Use the release-grade reference state as the anchor for large-scale HPC validation.

## Relationship to HPC validation

The release-grade reference run is the baseline for later HPC validation.

HPC should not start from an undefined release state.

HPC validation should start from:

- one accepted release-grade reference candidate
- a controlled set of fail-closed candidate states
- recorded expected decisions
- reproducible artifact identities
- reconstruction checks
- reader parity checks

The HPC validation stage can then scale this field across many candidate release states.

The sequence is:

1. define the release-grade next run
2. lock release-grade fixtures
3. produce non-stubbed release-grade reference run
4. archive artifacts
5. reconstruct decision
6. scale candidate-state validation through HPC

## Relationship to PULSE-COMPUTE

PULSE-COMPUTE is a future pre-compute admission research layer.

The release-grade next run plan focuses on release-decision integrity.

The release-grade reference run may later provide evidence useful for compute-admission research.

Compute-admission authority remains a separate future policy question.

## Success criteria

This plan succeeds when PULSE has a documented and executable path to the first release-grade reference run.

The reference run is successful when:

1. release-grade target state is declared
2. required evidence is materialized
3. required gates are materialized
4. required gates pass only through literal boolean `true`
5. stubbed release-grade evidence is rejected
6. scaffolded release-grade evidence is rejected
7. external evidence is enforced when required
8. manifest is produced
9. audit bundle is produced
10. reader parity is verified
11. decision is reconstructable
12. archived artifacts preserve run identity
13. declared-policy CI decision and reconstructed decision match
14. the resulting reference state can anchor HPC validation

## Follow-up work

Immediate follow-up work:

- create release-grade reference fixture suite
- create manifest mismatch fixture
- create audit bundle incomplete fixture
- create reader-surface parity fixture
- create non-stubbed pass fixture
- add release-grade reference fixture tests
- define HPC evidence bundle schema
- define HPC validation batch plan
- produce first non-stubbed release-grade reference run

## Closing statement

The next PULSE proof state is a non-stubbed, non-scaffolded, release-grade reference run.

This run anchors the fellowship-stage validation path.

It shows that PULSE release authority is exercised before deployment from recorded evidence, declared policy, materialized gates, and strict fail-closed CI enforcement.

The release-grade reference run is not the end state.

It is the first strong anchor for large-scale evidence-to-decision validation.

PULSEmech remains the release-authority mechanism.

HPC becomes the validation field.
