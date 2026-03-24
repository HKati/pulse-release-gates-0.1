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
pulse_gate_policy_v0.yml: add core_required gate set (minimal deterministic Core CI); required/advisory enforcement semantics unchanged.

- Q3 fairness: fail-closed when dataset manifest or `dataset_manifest.slices.dimensions` is missing/empty; Q3 gating now FAILs without declared slices (spec `q3_fairness_v0` bumped to 0.1.1). (PR: #936)

- q3_fairness_v0 (spec 0.1.1): Require non-empty dataset slice dimensions; fail-closed when missing/empty to prevent fairness checks from being skipped.

 HKati-patch-558331
- pulse-gate-policy-v0 (policy 0.1.2): introduce a dedicated `release_required` set for external-evidence release gating, while keeping `external_all_pass` in `required` for the currently enforced release-grade paths. This prepares the policy split without weakening live release gating. (PR: #1352)

- External evidence strict precheck: accept `azure_indirect_jailbreak_rate` as a recognized metric key in `scripts/check_external_summaries_present.py` so strict-mode metric-key checking stays aligned with the canonical Azure detector path.
  - **Why:** the canonical Azure fold-in path already uses `azure_indirect_jailbreak_rate`, but the strict precheck did not recognize it by default.
  - **Impact:** minimal Azure summaries exposing the canonical key no longer fail strict checks spuriously.
  - **Migration:** none required.
 main

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
