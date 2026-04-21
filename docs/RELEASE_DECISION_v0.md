## Summary

This PR adds `release_decision_v0`, a first-class machine-readable artifact
that materializes the documented PULSE release levels:

- `FAIL`
- `STAGE-PASS`
- `PROD-PASS`

from `status.json`, the repo-level gate policy, and the selected target lane.

## Why

PULSE already defines release authority through:

- `status.json`
- materialized required gate sets
- `check_gates.py`
- the primary release-gating workflow

The README also exposes release levels (`FAIL`, `STAGE-PASS`, `PROD-PASS`).
Those levels should not be removed or weakened. They should be implemented
as explicit mechanics.

This PR adds the missing materialization layer.

## What changes

Adds:

- `docs/RELEASE_DECISION_v0.md`
- `schemas/release_decision_v0.schema.json`
- `PULSE_safe_pack_v0/tools/materialize_release_decision.py`
- `tests/test_release_decision_v0_smoke.py`

Optionally wires the smoke test into:

- `ci/tools-tests.list`

## Release semantics

The materializer does not change existing gate semantics.

It reads:

- `status.json`
- `pulse_gate_policy_v0.yml`
- selected target: `stage` or `prod`

and writes:

- `PULSE_safe_pack_v0/artifacts/release_decision_v0.json`

## Target behavior

### Stage

`STAGE-PASS` requires:

- all `required` gates are literal `true`
- `detectors_materialized_ok` is literal `true`
- no stubbed/scaffold diagnostics are present

External evidence is recorded as advisory for stage.

### Prod

`PROD-PASS` requires:

- all `required` gates are literal `true`
- all `release_required` gates are literal `true`
- no stubbed/scaffold diagnostics are present

External evidence is required for prod through `release_required`.

## Non-goals

This PR does not:

- change `check_gates.py`
- mutate `status.json`
- promote any shadow layer
- implement break-glass override
- change existing CI release semantics
- make README the source of truth

## Validation

Adds smoke coverage for:

- stage pass
- prod pass
- prod fail on missing release evidence
- stage fail on stubbed status
- non-literal `"true"` failing closed

## Follow-ups

Recommended next PRs:

1. Render `release_decision_v0.json` in the Quality Ledger.
2. Wire release decision materialization into the primary release workflow.
3. Add `break_glass_override_v0` contract and ledger rendering.

---

# PULSE Release Decision v0

## Purpose

`release_decision_v0` is the machine-readable artifact that materializes
the documented PULSE release levels:

- `FAIL`
- `STAGE-PASS`
- `PROD-PASS`

from repository-controlled release evidence.

It exists so release-level labels are not inferred by a README, a renderer,
a dashboard, or private maintainer memory.

The release level is derived from:

- `status.json`
- the repo-level gate policy
- the target release lane
- deterministic true-only gate evaluation
- explicit release conditions such as detector materialization and no-stub evidence

## Non-goals

`release_decision_v0` does not:

- replace `check_gates.py`
- mutate `status.json`
- promote any shadow layer
- reinterpret diagnostic artifacts as release authority
- implement break-glass override
- turn a failed gate into a passing gate

Break-glass override, if implemented later, must be a separate audited
governance artifact. It must not rewrite the gate verdict.

## Inputs

The materializer reads:

PULSE_safe_pack_v0/artifacts/status.json  
pulse_gate_policy_v0.yml  

The selected target is explicit:

stage  
prod  

## Output

The materializer writes:

PULSE_safe_pack_v0/artifacts/release_decision_v0.json  

The output schema is:

schemas/release_decision_v0.schema.json  

## Release levels

### FAIL

FAIL means the selected release target is not allowed.

A decision is FAIL if any selected required gate is:

- missing  
- false  
- null  
- a string such as "true"  
- a number such as 1  
- or any value other than the literal JSON boolean true  

A decision is also FAIL if required release conditions are not satisfied.

### STAGE-PASS

STAGE-PASS is the first release-level decision above a local/core smoke.

It requires:

- all gates in the required policy set are literal true  
- detectors_materialized_ok is literal true  
- no stubbed gate diagnostics are present  
- no scaffold diagnostics are present  

External evidence may still be advisory at this level, but the decision artifact
must say so explicitly through:

"external_evidence_mode": "advisory"

### PROD-PASS

PROD-PASS requires:

- all gates in the required policy set are literal true  
- all gates in the release_required policy set are literal true  
- no stubbed gate diagnostics are present  
- no scaffold diagnostics are present  

Because release_required includes external evidence gates, production
decisions require:

- detectors_materialized_ok  
- external_summaries_present  
- external_all_pass  

to be literal true.

The decision artifact records:

"external_evidence_mode": "required"

## Active gate sets

For target = stage:

required  

plus stage release conditions.

For target = prod:

required + release_required  

## Stub and scaffold handling

A release decision must not treat scaffolded or stubbed evidence as a real
stage/prod pass.

The materializer treats the following as blocking release-level pass:

- diagnostics.gates_stubbed == true  
- metrics.gates_stubbed == true  
- meta.diagnostics.gates_stubbed == true  
- diagnostics.scaffold == true  
- metrics.scaffold == true  
- meta.diagnostics.scaffold == true  
- a non-empty/non-real stub_profile  

This keeps local smoke and scaffold states useful without allowing them to be
misread as release-grade evidence.

## Relationship to check_gates.py

check_gates.py remains the small deterministic true-only gate checker.

release_decision_v0 uses the same literal-true rule and records the higher
release-level decision.

The intended flow is:

status.json  
+ pulse_gate_policy_v0.yml  
+ target lane  
↓  
materialize_release_decision.py  
↓  
release_decision_v0.json  
↓  
Quality Ledger / CI summary / audit record  

## Relationship to Quality Ledger

The Quality Ledger should render release_decision_v0.json.

It should not independently invent or redefine release-level labels.

The correct direction is:

release_decision_v0.json → Quality Ledger  

not:

Quality Ledger → release decision  

## Example: stage pass

```json
{
  "schema": "pulse_release_decision_v0",
  "target": "stage",
  "release_level": "STAGE-PASS",
  "active_gate_sets": ["required"],
  "required_gates_passed": true,
  "conditions": {
    "detectors_materialized_ok": true,
    "no_stubbed_gates": true,
    "external_evidence_mode": "advisory"
  },
  "blocking_reasons": []
}

```
## Example: prod pass

{
  "schema": "pulse_release_decision_v0",
  "target": "prod",
  "release_level": "PROD-PASS",
  "active_gate_sets": ["required", "release_required"],
  "required_gates_passed": true,
  "conditions": {
    "detectors_materialized_ok": true,
    "external_summaries_present": true,
    "external_all_pass": true,
    "no_stubbed_gates": true,
    "external_evidence_mode": "required"
  },
  "blocking_reasons": []
}

## Example: fail

{
  "schema": "pulse_release_decision_v0",
  "target": "prod",
  "release_level": "FAIL",
  "active_gate_sets": ["required", "release_required"],
  "required_gates_passed": false,
  "blocking_reasons": [
    "external_summaries_present: missing required gate"
  ]
}

## Maintenance rule

Any change to release-level semantics must update:

- this document
- schemas/release_decision_v0.schema.json
- PULSE_safe_pack_v0/tools/materialize_release_decision.py
- release-decision tests
- and Quality Ledger rendering if visible output changes
```
