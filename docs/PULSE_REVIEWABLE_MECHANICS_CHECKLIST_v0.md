# PULSE Reviewable Mechanics Checklist v0

## Purpose

This document defines a reproducible mechanical review checklist for PULSE.

The goal is not to replace external review.

The goal is to make the PULSE release path mechanically reviewable before any external reviewer evaluates it.

External review can inspect the mechanism.

External review cannot replace the artifact-bound release-authority path.

## Core boundary

PULSE is not an eval collection, dashboard, runtime guardrail, compliance wrapper, MLOps wrapper, or general governance process.

PULSE is an artifact-bound release-authority mechanism.

The canonical PULSEmech release-authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

Release authority does not arise from narrative text, summaries, dashboards, public Pages, audit manifests, review notes, coverage scores, or external commentary.

Release authority can only arise through the declared artifact-bound path.

## Reviewability rule

PULSE does not rely on peer review as release authority.

PULSE makes the release path mechanically reviewable before external review can evaluate it.

External review may evaluate:

- the design
- the claims
- the implementation
- the reproducibility of the repository
- the integrity of the artifact path
- the fail-closed behavior

External review must not become:

- a gate
- a release decision
- a substitute for `check_gates.py`
- a replacement for declared policy
- a source of release authority

## Normative and non-normative layers

Every artifact or document must be classifiable by role.

Allowed role classes:

- release-authority path artifact
- normative input carrier
- policy carrier
- materialized gate-set carrier
- enforcement carrier
- audit sidecar
- diagnostic surface
- reader-only surface
- publication surface
- shadow / research layer
- non-authority support material

A review must verify that no diagnostic, reader-only, publication, shadow, research, or audit-sidecar layer can silently become release authority.

## Primary release-authority carriers

The primary PULSE release path uses these mechanical carriers.

### 1. Recorded release evidence

Recorded evidence is the upstream material from which release status may be built.

It must be artifact-bound and reproducible.

### 2. `status.json`

`status.json` is a normative input carrier.

It is not release authority by itself.

The normative decision surface inside `status.json` is the gate state consumed by the declared gate policy and strict evaluator.

### 3. Declared gate policy

The gate policy declares which gates are required in a given lane.

The required gate set must come from policy.

It must not be replaced by an undocumented manual `--require` list.

### 4. Workflow-effective materialized required gate set

The workflow-effective required gate set is the policy-derived set of gates that must be true for the selected lane.

Materialized gate-set construction must be reproducible.

### 5. Strict fail-closed CI enforcement

The final enforcement point must be strict and fail-closed.

A required gate passes only if its value is the literal boolean `true`.

Missing, false, null, string, numeric, unknown, or malformed values must not pass.

### 6. Pre-deployment allow/block decision

The final allow/block decision is produced by declared policy plus materialized required gates plus strict fail-closed enforcement.

No reader surface or audit sidecar may override this path.

## Non-authority surfaces

The following surfaces are not release authority by default:

- public Pages
- public `status.json` reader surface
- dashboards
- badges
- summaries
- reports
- Quality Ledger views
- audit bundles
- release-authority sidecars
- external review notes
- shadow layer outputs
- research outputs
- documentation claims

These surfaces may improve visibility.

They may support review.

They may support reproducibility.

They do not authorize release unless explicitly promoted through declared policy, materialized required gates, and fail-closed CI enforcement.

## Audit-sidecar boundary

A release-authority audit manifest or sidecar may record or reconstruct the release-authority chain.

It must not become a second decision engine.

An audit sidecar must not:

- replace `check_gates.py`
- compute a new release decision
- override the primary release path
- materialize gates normatively
- change CI outcome
- turn warning-only audit failure into release permission
- create release authority from its own existence

Audit sidecar failure may be a visibility or traceability issue.

It must not silently rewrite the primary release decision.

### Trace-carrier dependency

An audit sidecar may be required by a later provenance-binding layer as a trace carrier.

That requirement must not be confused with release authority.

A required trace carrier can make the provenance-binding layer fail if the carrier is missing, but it must not replace the primary artifact-bound release-authority path.

Boundary:

```text
required trace carrier ≠ release authority
required trace carrier ≠ primary allow/block decision
required trace carrier ≠ gate materialization
required trace carrier ≠ second decision engine
```


## Public reader-surface boundary

A public reader surface may expose current state.

It must be read according to its declared mode.

For example, a public status showing a core or scaffold state must not be interpreted as release-grade authority.

A reader-surface review must check whether fields such as these indicate non-release-grade state:

- `run_mode`
- `diagnostics.gates_stubbed`
- `diagnostics.scaffold`
- `detectors_materialized_ok`

If the public state is reader-only, scaffolded, core-mode, stubbed, or missing materialized detector evidence, it must not be treated as release-grade proof.

This is not a weakness.

It is boundary discipline.

## Coverage and score boundary

PULSE does not use coverage-score authority.

Metrics may be descriptive.

Metrics may support interpretation.

Metrics may support diagnostics.

Metrics must not become release authority unless explicitly promoted into policy-declared gates and enforced by strict fail-closed CI.

The boundary is:

```text
coverage score ≠ release authority
metric value ≠ gate pass
dashboard value ≠ release permission
summary value ≠ release closure
```

The normative release question is not:

```text
How high is the score?
```

The normative release question is:

```text
Did every workflow-effective required gate evaluate to literal true under declared policy and strict fail-closed enforcement?
```

## Runtime guardrail boundary

PULSE is not a runtime safety guardrail.

PULSE does not operate as prompt moderation, output moderation, topic blocking, tool-call filtering, or interaction-time refusal logic.

PULSE operates at the release boundary.

The relevant question is not whether a single prompt or output is allowed.

The relevant question is whether the artifact/evidence/policy/gate path can produce a supported release closure.

Boundary:

```text
runtime guardrail ≠ release authority
prompt/output moderation ≠ PULSEmech
topic blocking ≠ artifact-bound release decision
```

## Relation binding boundary

Visible binding is not verified relation binding.

The current relation-binding boundary remains:

```text
visible binding ≠ verified relation binding
digest match ≠ verified evidence
subject/run match ≠ satisfied relation binding
verified relation binding ≠ gate materialization
gate materialization ≠ release authority without declared policy and fail-closed CI
```

A future relation-binding promotion path must remain staged.

It must not collapse diagnostic visibility, verification, relation satisfaction, gate materialization, and release authority into one operation.

## External mechanical review checklist

An external reviewer should be able to answer the following questions from a clean repository checkout.

### 1. Artifact path

Can the reviewer follow the artifact path from recorded release evidence to `status.json`, declared policy, materialized required gates, and strict CI enforcement?

Expected result:

The reviewer can identify the artifact path without relying on narrative claims.

### 2. Status schema

Can the reviewer validate the final `status.json` against the base status schema?

For release-grade lanes, can the reviewer also validate the release-grade overlay?

Expected result:

Invalid base status or invalid release-grade overlay fails closed.

### 3. Policy-derived gate set

Can the reviewer reconstruct which policy set was active for the lane?

Examples:

- `core_required`
- `required`
- `release_required`
- `required + release_required`

Expected result:

The materialized required gate set comes from declared policy, not from an undocumented hardcoded list.

### 4. Strict gate evaluator

Can the reviewer prove that the strict evaluator treats only literal boolean `true` as pass?

Expected result:

- `true` passes
- `false` fails
- `null` fails
- `"true"` fails
- `1` fails
- missing required gate fails closed

### 5. Reader-surface non-interference

Can the reviewer modify or remove reader-only surfaces without changing the primary gate outcome?

Reader-only surfaces include:

- Pages snapshots
- HTML reports
- summaries
- ledgers
- publication views
- shadow fold-ins

Expected result:

If `gates.*` and the declared policy path do not change, the strict gate result does not change.

### 6. Audit-sidecar neutrality

Can the reviewer break the audit sidecar without changing the primary release decision?

Expected result:

The sidecar may warn or fail its own validation, but it must not become a second decision engine or rewrite the primary release path.

### 7. Shadow layer non-promotion

Can the reviewer confirm that a shadow layer’s presence does not promote it into release authority?

Expected result:

A shadow layer remains non-normative unless explicitly promoted through policy, materialized required gates, and fail-closed CI.

### 8. Release-grade lane requirements

For release-grade operation, can the reviewer confirm that the required release-grade conditions are enforced?

Examples:

- production run mode
- non-stubbed gates
- non-scaffold state
- materialized detector evidence
- required external evidence presence where declared

Expected result:

Missing release-grade evidence blocks release-grade authority.

### 9. External evidence presence

Can the reviewer remove or corrupt required external evidence and observe fail-closed behavior?

Expected result:

Missing or unparsable required evidence blocks before release authority can materialize.

### 10. No authority from external review

Can the reviewer add external review text without changing the release decision?

Expected result:

External review text remains review input only.

It does not become release authority.

## Internal mechanical review modes

PULSE can be reviewed internally before external review through four modes.

### 1. Mechanical role review

Classify every document and artifact by role:

- authority path
- normative input
- policy carrier
- gate-set carrier
- enforcement carrier
- audit sidecar
- diagnostic
- reader-only
- publication
- shadow
- research
- support material

Goal:

Prevent accidental authority drift.

### 2. External-style reproduction review

Run the repository as if received by an external reviewer:

- clean clone
- documented commands
- expected outputs
- schema validation
- checker outputs
- fail-closed tests
- no hidden local state

Goal:

Reproducibility without workshop context.

### 3. Misread-risk review

Inspect where PULSE can be misread as:

- governance
- benchmark
- dashboard
- ordinary CI
- MLOps wrapper
- compliance wrapper
- runtime guardrail
- release announcement text
- supply-chain framework

Goal:

Protect the mechanical category.

### 4. Boundary attack review

Attempt to move authority from places where authority is not allowed:

- summary
- verifier report
- input manifest
- live URL
- public Pages
- audit sidecar
- green test result
- self-declared artifact
- external review text
- documentation claim

Expected result:

Fail closed.

No diagnostic or reader-only surface may become release authority.

## Minimal release-grade review artifact set

For external reproducibility, a release-grade review package should include at least:

- final `status.json`
- declared gate policy
- policy identifier and digest
- materialized required gate-set artifact
- CI outcome record
- strict gate evaluator reference
- optional audit sidecar
- optional audit bundle
- publication snapshot, if relevant

The package may support reconstruction.

The package must not create new release authority by itself.

## Minimal CI hardening checklist

A minimal but strong CI guard should include:

1. Status schema validation for every normative run.
2. Release-grade overlay validation for release-grade lanes.
3. Policy materialization smoke test.
4. Strict gate evaluator contract tests.
5. Missing required gate fail-closed tests.
6. Reader-surface non-interference tests.
7. Audit-sidecar neutrality tests.
8. External evidence presence tests where release-grade policy requires external evidence.
9. Workflow semantic drift checks for policy, status schema, and canonical docs.
10. Tools manifest smoke tests when tool/test lists are touched.

## Recommended negative tests

Negative tests are the strongest way to protect PULSE boundaries.

Recommended tests:

### True-only gate test

For each required gate, try:

- `true`
- `false`
- `null`
- `"true"`
- `1`
- missing

Expected result:

Only literal boolean `true` passes.

Missing required gate fails closed.

### Schema-first test

Break the base status schema.

Break the release-grade overlay.

Expected result:

Validation exits non-zero.

### Policy materialization test

Change a fixture policy set.

Expected result:

The materialized required gate set changes exactly according to policy.

No hidden hardcoded required list is used.

### Release-grade overlay test

Force invalid release-grade states:

- core run mode
- stubbed gates
- scaffold state
- missing detector materialization

Expected result:

Release-grade lane blocks.

### Reader-surface non-interference test

Modify:

- Pages snapshot
- HTML report
- Quality Ledger view
- summary output
- diagnostic fold-in

without changing the normative gate state.

Expected result:

The strict gate decision remains unchanged.

### Audit-sidecar neutrality test

Break:

- audit manifest builder
- audit manifest checker
- audit bundle upload

Expected result:

The primary release path remains controlled by declared policy and strict gate enforcement.

### External review non-authority test

Add or modify external review text.

Expected result:

No release authority changes.

## Hardening backlog

The following areas may strengthen external reproducibility and provenance.

They must remain supporting layers, not the definition of PULSE:

- signed provenance
- artifact attestations
- external reproducibility bundles
- audit bundle hardening
- supply-chain metadata
- SLSA-style provenance support
- in-toto-style layout support
- Sigstore-style signing support

These may strengthen the infrastructure around PULSEmech.

They must not replace PULSEmech.

They must not redefine release authority.

## Non-goals

This checklist does not:

- implement release authority
- change schemas
- change gate policy
- change gate registry
- change status schemas
- change CI authority path
- promote reader surfaces
- promote summaries
- promote audit sidecars
- promote external review
- reopen release-grade materialization
- replace `check_gates.py`

## Summary

PULSE is reviewable because its release path is artifact-bound, policy-declared, gate-materialized, and fail-closed.

The strongest external review question is:

```text
Can the reviewer reproduce the path from recorded evidence to declared policy, materialized required gates, and strict fail-closed CI enforcement without relying on narrative authority?
```

The strongest boundary is:

```text
External review can inspect the mechanism.
External review cannot replace the artifact-bound release-authority path.
```

The strongest PULSEmech rule remains:

```text
visible information ≠ normative release authority
```
