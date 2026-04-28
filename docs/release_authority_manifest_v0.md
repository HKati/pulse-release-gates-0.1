
# Release Authority Manifest v0

## Purpose

`release_authority_v0.json` is the audit manifest for the PULSE
release-authority chain.

Its role is to record, in one machine-readable artifact, which evidence,
policy, evaluator, workflow lane, and required gate set produced a release
decision.

It is an audit and traceability surface.

It is not a new release-decision engine.

---

## Status

Current status:

```text
stage: v0 contract surface implemented
normative: false
default artifact path: PULSE_safe_pack_v0/artifacts/release_authority_v0.json
primary CI artifact wiring: not yet promoted into the main release workflow
```

Implemented v0 surfaces:

- schema:
  - `schemas/release_authority_v0.schema.json`
- builder:
  - `PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py`
- checker:
  - `PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py`
- canonical fixtures:
  - `tests/fixtures/release_authority_v0/core_pass.json`
  - `tests/fixtures/release_authority_v0/core_fail_missing_gate.json`
- regression tests:
  - `tests/test_check_release_authority_manifest_v0.py`
  - `tests/test_build_release_authority_manifest_v0.py`
  - `tests/test_release_authority_manifest_non_interference.py`
- tools-test manifest coverage:
  - `ci/tools-tests.list`

This document describes the v0 manifest contract and its authority boundary.

It does not change:

- release semantics,
- gate policy,
- `status.json` semantics,
- CI behavior,
- checker behavior for existing release gates,
- shadow-layer authority.

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

The release authority manifest binds these surfaces into one auditable decision
record.

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

## Artifact path

Default builder output path:

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

The path is intentionally under `artifacts/` because the manifest describes a
specific run, not a static repository policy.

At the current v0 stage, the builder can produce this artifact, and tests cover
its behavior. The manifest is not yet required as a primary release workflow
output.

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

## Manifest shape

The v0 manifest shape is validated by:

```text
schemas/release_authority_v0.schema.json
```

A representative Core PASS manifest:

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
    },
    "evaluator": {
      "path": "PULSE_safe_pack_v0/tools/check_gates.py",
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
    "release_required_materialized": false,
    "advisory_gates": [
      "external_summaries_present",
      "external_all_pass"
    ]
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
    "status_meta_foldins": [],
    "advisory_gates_present": [
      "external_summaries_present",
      "external_all_pass"
    ],
    "publication_surfaces_present": []
  }
}
```

A representative missing-required-gate manifest is tracked in:

```text
tests/fixtures/release_authority_v0/core_fail_missing_gate.json
```

That fixture models a fail-closed audit state where an effective required gate is
missing from `required_gate_results`, listed under `missing_required_gates`, and
the decision state is `FAIL`.

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

The builder also records the evaluator path and hash.

Recommended for each artifact:

- `path`
- `sha256`

Policy and registry entries may also include their declared IDs / versions.

`inputs.gate_policy.version` is optional. When the policy does not define a
version, the builder omits the field rather than emitting an empty string. Numeric
versions such as `0` are preserved as non-empty strings.

The manifest hashes file bytes, not rendered text.

---

### `authority`

Required.

Records which policy lane carried release authority for this run.

Fields include:

- `policy_set`
- `effective_required_gates`
- `release_required_materialized`
- `advisory_gates`

`effective_required_gates` describes the gate set actually enforced or audited
for this run, not merely a policy-defined set that exists in the repository.

This distinction matters because a policy-defined set can exist without being
active in every lane.

---

### `evaluation`

Required.

Records the deterministic evaluator result over the effective required gate set.

Fields include:

- `evaluator`
- `evaluator_sha256`
- `required_gate_results`
- `failed_required_gates`
- `missing_required_gates`

The manifest does not reinterpret gate values.

For required gates, PASS remains strict:

```text
literal true = PASS
false / null / missing / non-boolean = not PASS
```

`required_gate_results` may be empty when all effective required gates are
missing from `status.json`. In that case, the missing gate set carries the
fail-closed audit state, and the decision state must be `FAIL`.

---

### `decision`

Required.

Records the release decision state derived from evaluation.

Current v0 values include:

```text
PASS
FAIL
STAGE-PASS
PROD-PASS
UNKNOWN
```

The checker requires `decision.state = FAIL` when `failed_required_gates` or
`missing_required_gates` is non-empty.

`fail_closed` must be `true`.

---

### `diagnostics`

Optional, but recommended.

Records diagnostic and shadow surfaces present during the run.

Fields include:

- `shadow_surfaces_present`
- `shadow_surfaces_non_normative`
- `status_meta_foldins`
- `advisory_gates_present`
- `publication_surfaces_present`

Diagnostic information is descriptive only unless a policy explicitly promotes a
signal into the required gate set.

The checker rejects diagnostic surfaces marked as normative by default.

---

## Builder

Builder path:

```text
PULSE_safe_pack_v0/tools/build_release_authority_manifest_v0.py
```

The builder can derive a manifest from:

- a recorded `status.json`,
- `pulse_gate_policy_v0.yml`,
- `pulse_gate_registry_v0.yml`,
- an evaluator path,
- and workflow/run context arguments or environment variables.

Covered builder scenarios include:

- Core PASS manifest generation,
- missing required gate → FAIL manifest generation,
- failed required gate → FAIL manifest generation,
- all required gates missing → FAIL manifest generation,
- release-grade `required+release_required` manifest generation,
- missing policy version omitted,
- numeric `policy.version: 0` preserved as `"0"`.

---

## Checker

Checker path:

```text
PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py
```

The checker validates:

- JSON Schema conformance,
- required gate result consistency,
- missing gate representation,
- failed gate representation,
- `FAIL` decisions for failed or missing required gates,
- non-normative diagnostic surfaces,
- malformed non-object / null top-level sections without traceback output.

The checker reports normal validation errors for malformed manifests.

---

## Tests and fixtures

Canonical fixtures:

```text
tests/fixtures/release_authority_v0/core_pass.json
tests/fixtures/release_authority_v0/core_fail_missing_gate.json
```

Regression tests:

```text
tests/test_check_release_authority_manifest_v0.py
tests/test_build_release_authority_manifest_v0.py
tests/test_release_authority_manifest_non_interference.py
```

Both tests include top-level pytest runners so they execute correctly when invoked
through `ci/tools-tests.list` with:

```text
python "$t"
```

---

## CI manifest coverage

The tools-test manifest includes:

```text
tests/test_check_release_authority_manifest_v0.py
tests/test_build_release_authority_manifest_v0.py
```

This ensures the release-authority checker and builder regression tests run under
the repository tools-test path.

The manifest is not yet wired as a primary `pulse_ci.yml` artifact output.

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

For release-grade runs, the manifest distinguishes:

```text
policy-defined required sets
workflow-effective enforce set
```

For example, a release-grade run may enforce or audit:

```text
required + release_required
```

while a Core lane may enforce or audit:

```text
core_required
```

The manifest records the workflow-effective set represented for the run.

---

## Non-interference requirement

Adding or building the release authority manifest must not change the release
outcome.

The expected proof shape is:

```text
run check_gates.py without manifest
run check_gates.py with manifest generation
same status.json
same required gate set
same release outcome
```

The current v0 builder and checker are adjacent audit tooling and do not modify
`status.json`, gate policy, or existing gate-checker behavior.

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

## Remaining implementation work

Current v0 surfaces exist and are tested.

Remaining future work may include:

1. optional wiring into the primary `pulse_ci.yml` artifact upload path,
2. optional renderer / Quality Ledger link to the manifest,
3. optional end-to-end workflow-level non-interference coverage after primary CI
   artifact wiring,
4. optional run metadata enrichment (`run_id`, `attempt`, actor),
5. optional artifact references for additional diagnostic surfaces.

Any future promotion into primary workflow output should remain documentation-only
or artifact-only unless accompanied by an explicit policy change.

---

## Reviewer checklist

When reviewing release-authority manifest changes, check:

1. Does the change preserve `status.json` as the evidence source?
2. Does it preserve `check_gates.py` as the evaluator?
3. Does it record the workflow-effective required gate set?
4. Does it distinguish required, release-required, and advisory surfaces?
5. Does it treat shadow layers as non-normative by default?
6. Does it hash input artifacts?
7. Does it avoid recomputing or redefining gate semantics?
8. Does it include non-interference test coverage where behavior changes?
9. Does it remain an audit manifest rather than a second decision engine?

---

## Summary

`release_authority_v0.json` makes the release-authority chain explicit.

It answers:

```text
What evidence was evaluated?
Which policy carried authority?
Which required gates were represented?
Which evaluator produced the result?
Which diagnostics were present but non-normative?
What release decision record was produced?
```

That is the audit surface between the existing `status.json`, gate policy, CI
enforcement, and Quality Ledger.
