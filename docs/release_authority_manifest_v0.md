
# Release Authority Manifest v0

## Purpose

`release_authority_v0.json` is a proposed audit manifest for the PULSE
release-authority chain.

Its role is to record, in one machine-readable artifact, which evidence,
policy, evaluator, workflow lane, and required gate set produced a release
decision.

It is an audit and traceability surface.

It is not a new release-decision engine.

---

## Status

This document specifies the intended v0 shape and authority boundary for the
future release authority manifest.

Current status:

```text
stage: proposed
normative: false
artifact: PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

This document does not change:

- release semantics,
- gate policy,
- `status.json` semantics,
- CI behavior,
- checker behavior,
- shadow-layer authority.

Implementation should happen in a later change set with a schema, builder,
fixtures, tests, and CI artifact wiring.

---

## Background

PULSE already separates release authority across several stable surfaces:

- `status.json` records machine-readable gate and metric evidence.
- `pulse_gate_policy_v0.yml` declares required, release-required, core-required,
  and advisory gate sets.
- `pulse_gate_registry_v0.yml` records stable gate identity and intent.
- `check_gates.py` evaluates required gates fail-closed.
- `.github/workflows/pulse_ci.yml` materializes the workflow-effective gate set
  and enforces it in CI.
- The Quality Ledger renders the release state for human review.
- Shadow registries and overlays provide diagnostic evidence without changing
  release authority by default.

The release authority manifest should bind these surfaces into one auditable
decision record.

---

## Core rule

The release authority manifest records the release decision chain.

It must not redefine the decision chain.

The normative release path remains:

```text
release evidence
→ status.json
→ declared gate policy
→ check_gates.py
→ primary CI release workflow
→ release decision record
```

The manifest must be derived from that path.

---

## Proposed artifact path

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

The path is intentionally under `artifacts/` because the manifest describes a
specific run, not a static repository policy.

---

## High-level model

The manifest binds five categories:

```text
run identity
+ recorded inputs
+ authority materialization
+ deterministic evaluation result
+ diagnostic / shadow context
```

In compact form:

```text
release_authority_v0 =
  bind(
    run_identity,
    input_artifacts,
    declared_policy,
    effective_required_gate_set,
    evaluator_result,
    diagnostic_context
  )
```

---

## Proposed minimal shape

```json
{
  "schema_version": "release_authority_v0",
  "created_utc": "2026-04-27T00:00:00Z",
  "run_identity": {
    "run_mode": "core",
    "workflow_name": "PULSE CI",
    "event_name": "pull_request",
    "ref": "refs/pull/123/merge",
    "git_sha": "0000000000000000000000000000000000000000"
  },
  "inputs": {
    "status_json": {
      "path": "PULSE_safe_pack_v0/artifacts/status.json",
      "sha256": "..."
    },
    "gate_policy": {
      "path": "pulse_gate_policy_v0.yml",
      "policy_id": "pulse-gate-policy-v0",
      "version": "0.1.3",
      "sha256": "..."
    },
    "gate_registry": {
      "path": "pulse_gate_registry_v0.yml",
      "version": "gate_registry_v0",
      "sha256": "..."
    }
  },
  "authority": {
    "policy_set": "core_required",
    "effective_required_gates": [
      "pass_controls_refusal",
      "pass_controls_sanit",
      "sanitization_effective",
      "q1_grounded_ok",
      "q4_slo_ok"
    ],
    "release_required_materialized": false
  },
  "evaluation": {
    "evaluator": "PULSE_safe_pack_v0/tools/check_gates.py",
    "evaluator_sha256": "...",
    "required_gate_results": {
      "pass_controls_refusal": true,
      "pass_controls_sanit": true,
      "sanitization_effective": true,
      "q1_grounded_ok": true,
      "q4_slo_ok": true
    },
    "failed_required_gates": [],
    "missing_required_gates": []
  },
  "decision": {
    "state": "PASS",
    "fail_closed": true
  },
  "diagnostics": {
    "shadow_surfaces_present": [],
    "shadow_surfaces_non_normative": true,
    "status_meta_foldins": []
  }
}
```

---

## Field semantics

### `schema_version`

Required.

Identifies the manifest contract.

Allowed v0 value:

```text
release_authority_v0
```

---

### `created_utc`

Required.

UTC timestamp for the manifest creation time.

This is the manifest creation time, not necessarily the original `status.json`
creation time.

---

### `run_identity`

Required.

Describes the run context that produced the release decision record.

Recommended fields:

- `run_mode`
- `workflow_name`
- `event_name`
- `ref`
- `git_sha`
- optional `run_id`
- optional `attempt`
- optional `actor`

`run_mode` should mirror `status.metrics.run_mode` when available.

---

### `inputs`

Required.

Records the primary input artifacts and their hashes.

At minimum:

- `status_json`
- `gate_policy`
- `gate_registry`

Recommended for each artifact:

- `path`
- `sha256`

Policy and registry entries may also include their declared IDs / versions.

The manifest should hash file bytes, not rendered text.

---

### `authority`

Required.

Records which policy lane carried release authority for this run.

Recommended fields:

- `policy_set`
- `effective_required_gates`
- `release_required_materialized`

`effective_required_gates` should describe the gate set actually enforced by the
workflow for this run, not merely a policy-defined set that exists in the repo.

This distinction matters because a policy-defined set can exist without being
active in every lane.

---

### `evaluation`

Required.

Records the deterministic evaluator result over the effective required gate set.

Recommended fields:

- `evaluator`
- `evaluator_sha256`
- `required_gate_results`
- `failed_required_gates`
- `missing_required_gates`

The manifest should not reinterpret gate values.

For required gates, PASS remains strict:

```text
literal true = PASS
false / null / missing / non-boolean = not PASS
```

---

### `decision`

Required.

Records the release decision state derived from evaluation.

Initial v0 values may include:

```text
PASS
FAIL
STAGE-PASS
PROD-PASS
UNKNOWN
```

The builder should use the existing PULSE decision vocabulary where available.

`fail_closed` should be `true` for standard PULSE release-authority runs.

---

### `diagnostics`

Optional, but recommended.

Records diagnostic and shadow surfaces present during the run.

Recommended fields:

- `shadow_surfaces_present`
- `shadow_surfaces_non_normative`
- `status_meta_foldins`
- optional `advisory_gates_present`
- optional `publication_surfaces_present`

Diagnostic information is descriptive only unless a policy explicitly promotes
a signal into the required gate set.

---

## Shadow and diagnostic handling

Shadow layers may appear in the manifest as diagnostic context.

They must not be treated as release authority unless explicitly promoted.

Examples of non-normative diagnostic context:

- `meta.relational_gain_shadow`
- EPF shadow artifacts
- Paradox summaries
- G-field overlays
- hazard overlays
- theory overlays
- Pages and dashboard surfaces

The manifest may record their presence, artifact path, and hash.

It must not silently convert them into required gates.

---

## Release-grade behavior

For release-grade runs, the manifest should clearly distinguish:

```text
policy-defined required sets
workflow-effective enforce set
```

For example, a release-grade run may enforce:

```text
required + release_required
```

while a Core lane may enforce:

```text
core_required
```

The manifest should record the workflow-effective set actually enforced.

---

## Non-interference requirement

Adding the release authority manifest must not change the release outcome.

The expected proof shape is:

```text
run check_gates.py without manifest
run check_gates.py with manifest generation
same status.json
same required gate set
same release outcome
```

Implementation should include a regression test for this property.

---

## Non-goals

The release authority manifest is not:

- a replacement for `status.json`,
- a replacement for `pulse_gate_policy_v0.yml`,
- a replacement for `check_gates.py`,
- a dashboard,
- a shadow-layer promotion mechanism,
- a second release-decision engine,
- or a place to redefine gate semantics.

---

## Proposed implementation plan

A future implementation should add the following in separate, reviewable steps.

### Step 1 — Schema

```text
schemas/release_authority_v0.schema.json
```

The schema should validate required top-level fields and basic artifact shapes.

### Step 2 — Builder

```text
tools/build_release_authority_manifest_v0.py
```

or, if the implementation belongs inside the safe-pack:

```text
PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py
```

The builder should:

1. read `status.json`,
2. read the gate policy,
3. materialize or receive the workflow-effective required gate set,
4. evaluate or consume the evaluator result,
5. hash declared input files,
6. write `release_authority_v0.json`.

### Step 3 — Fixtures

Suggested fixtures:

```text
tests/fixtures/release_authority_v0/core_pass.json
tests/fixtures/release_authority_v0/core_fail_missing_gate.json
tests/fixtures/release_authority_v0/prod_release_required.json
tests/fixtures/release_authority_v0/shadow_context_non_normative.json
```

### Step 4 — Contract checker

```text
PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py
```

The checker should validate:

- schema conformance,
- required gate result consistency,
- missing-gate fail-closed representation,
- shadow non-normativity,
- and artifact reference shape.

### Step 5 — Non-interference tests

Add tests proving manifest generation does not alter:

- `status.json`,
- required gate sets,
- `check_gates.py` outcomes,
- release semantics.

### Step 6 — CI artifact wiring

Upload the manifest as a CI artifact after gate enforcement.

The manifest should be produced for audit and replay, not for changing the
current run outcome.

---

## Reviewer checklist

When reviewing an implementation of `release_authority_v0.json`, check:

1. Does it preserve `status.json` as the evidence source?
2. Does it preserve `check_gates.py` as the evaluator?
3. Does it record the workflow-effective required gate set?
4. Does it distinguish required, release-required, and advisory surfaces?
5. Does it treat shadow layers as non-normative by default?
6. Does it hash input artifacts?
7. Does it avoid recomputing or redefining gate semantics?
8. Does it include non-interference test coverage?
9. Does it remain an audit manifest rather than a second decision engine?

---

## Summary

`release_authority_v0.json` should make the release-authority chain explicit.

It should answer:

```text
What evidence was evaluated?
Which policy carried authority?
Which required gates were enforced?
Which evaluator produced the result?
Which diagnostics were present but non-normative?
What release decision record was produced?
```

That is the missing audit surface between the existing `status.json`, gate policy,
CI enforcement, and Quality Ledger.
