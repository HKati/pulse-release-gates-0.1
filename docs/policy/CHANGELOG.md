# Policy and Metric Specs Changelog

This changelog records **semantic** changes that can affect release gating outcomes
(PASS/FAIL/NOT_ELIGIBLE), including:

- `pulse_gate_policy_v0.yml` (required/advisory gate sets and enforcement semantics)
- `metrics/specs/*.yml` (metric definitions and gate semantics, e.g. Q1–Q4)
- Any other contract that changes gating meaning (e.g. dataset manifest contract)

## Rules

1. **If a change can alter a gating outcome, it MUST be recorded here.**
2. **Bump the relevant version** when making semantic changes:
   - Policy: `pulse_gate_policy_v0.yml -> policy.version`
   - Spec: `metrics/specs/* -> spec.version`
3. Pure formatting/comment changes **do not require** a version bump, but may be documented.
4. Prefer entries that answer:
   - What changed?
   - Why?
   - Impact / migration notes (if any)

## Unreleased

- `pulse_gate_policy_v0.yml` / `pulse-gate-policy-v0` (policy 0.1.3):
  - Changed: add `detectors_materialized_ok` to `gates.release_required`.
  - Why: scaffold / placeholder booleans must not be misread as materialized release evidence in release-grade paths.
  - Impact: policy consumers deriving `release_required` now fail closed until detectors are materialized.
  - Migration: wire deterministic producers for the release-grade detector-backed gates before treating scaffold output as passing release evidence.

- `docs/STATUS_CONTRACT.md` / `status contract`:
  - Changed: documented the `meta.relational_gain_shadow` fold-in surface as additive, descriptive, and non-normative shadow metadata.
  - Why: make the public status contract reflect the implemented Relational Gain shadow fold-in behavior.
  - Impact: clarifies consumer expectations for `meta.relational_gain_shadow`; no change to release authority, required gates, or `check_gates.py` behavior.
  - Migration: none. Consumers must continue treating `meta.relational_gain_shadow` as non-normative shadow metadata.

- `docs/STATE_v0.md` / `state v0`:
  - Changed: refreshed the repository state snapshot to reflect the current deterministic release core, shadow contract program, machine-readable shadow layer registry stack, contract-hardened Relational Gain pilot, and the EPF split between the broader research line and the hardened paradox-summary surface.
  - Why: the previous state snapshot no longer matched the current repo shape and understated the current shadow-program maturity.
  - Impact: clarifies the current repository architecture for readers; no change to release authority, required gates, or `check_gates.py` behavior.
  - Migration: none. `docs/STATE_v0.md` remains a descriptive state snapshot, not a normative contract surface.


## 0.1.0 — Initial baseline

### Policy
- Added `pulse_gate_policy_v0.yml` as the canonical required vs advisory gate set definition.
- Required set includes `refusal_delta_pass` and `external_all_pass`.

### Dataset contract
- Added dataset manifest schema: `schemas/dataset_manifest.schema.json`.
- Added dataset manifest example: `examples/dataset_manifest.example.json`.

### Metric specs
- Added Q1 spec: `metrics/specs/q1_groundedness_v0.yml`.
- Added Q2 spec: `metrics/specs/q2_consistency_v0.yml`.
- Added Q3 spec: `metrics/specs/q3_fairness_v0.yml`.
- Added Q4 spec: `metrics/specs/q4_slo_v0.yml`.

### Tooling / CI (informational)
- CI derives the required gate list from `pulse_gate_policy_v0.yml` via `tools/policy_to_require_args.py`.

## Entry template (copy/paste)

### X.Y.Z — <Component> — <Date>
- **Changed:** …
- **Why:** …
- **Impact:** …
- **Migration:** …
