# Separation Phase v0 (Diagnostic Overlay)

## Purpose
`separation_phase_v0` is a **CI-neutral diagnostic overlay** that summarizes whether a run is
**meaningfully separable** (events remain distinguishable and decisions remain attributable)
when global ordering assumptions become unreliable.

This overlay is designed to complement (not replace) PULSE’s **normative PASS/FAIL gates**:
- **Normative layer** (core): produces `status.json` and enforces required gates (fail-closed).
- **Diagnostic layer** (this doc): produces `separation_phase_v0.json` to describe *field state*
  and *ordering sensitivity* without changing normative enforcement.

> Important: “Separation phase” is an **operational engineering lens**, not a claim about
> fundamental physics. It is a way to describe when timing/ordering metrics stop being the
> right axis for safety/release reasoning, and separation/stability become the right axis.

---

## Why this exists
Many systems continue to “run” under timing drift, jitter, or ordering instability, but:
- the **meaning** of events becomes harder to isolate,
- the **responsibility/attribution** chain becomes ambiguous,
- decisions may become **order-sensitive** in unexpected ways.

This overlay makes that observable using PULSE artifacts that already exist (primarily
`status.json`, and optionally multiple `status.json` files from permuted or repeated runs).

---

## Inputs and outputs

### Inputs
- Baseline PULSE status:
  - `PULSE_safe_pack_v0/artifacts/status.json` (default)
- Optional additional runs (recommended):
  - multiple `status*.json` files from permutation or re-ordered runs

### Output
- `separation_phase_v0.json` (default output path depends on invocation)

---

## Data contract (schema)
The output MUST conform to:
- `schemas/separation_phase_v0.schema.json`

Contract checking (fail-closed) is provided by:
- `scripts/check_separation_phase_v0_contract.py`

---

## How it works (high-level)
The overlay generator:
- extracts a **gate vector** and an optional **release decision** from each provided `status.json`,
- compares results across runs to estimate **order stability**,
- identifies **unstable** and **threshold-like** gates (gates that flip across runs),
- classifies an operational **field state** and emits a conservative recommendation.

Generator script:
- `scripts/separation_phase_adapter_v0.py`

---

## Core invariants (v0)

### 1) Order Stability
Operational question:
> Does the gate vector remain stable across permissible re-orderings / permutations?

Output fields:
- `invariants.order_stability.method`:
  - `permutations` when multiple runs are provided
  - `rdsi_proxy` when no permutations exist but an RDSI-like metric is available
  - `unknown` otherwise
- `invariants.order_stability.score` in `[0,1]` when measurable
- `invariants.order_stability.unstable_gates`: gates that flip or go missing across runs

Interpretation:
- High score → order assumptions are not driving outcomes.
- Low score → outcomes depend on ordering; treat as higher operational risk.

### 2) Separation Integrity
Operational question:
> Is the release decision stable across runs (baseline + optional permutations)?

Output fields:
- `invariants.separation_integrity.decision_stable` (bool|null)
- `invariants.separation_integrity.notes`

Interpretation:
- If the decision itself flips, separability is strained even if individual gates appear stable.

### 3) Phase/Ordering Dependency (proxy)
Operational question:
> Does the system appear critically dependent on a single global ordering/phase?

Output fields:
- `invariants.phase_dependency.critical_global_phase` (bool|null)

Note:
- v0 uses conservative heuristics. Treat as informational until calibrated.

### 4) Threshold Sensitivity
Operational question:
> Which gates behave like threshold boundaries (flip between PASS/FAIL across runs)?

Output fields:
- `invariants.threshold_sensitivity.threshold_like_gates`

Interpretation:
- These are “watchlist” gates for calibration, margin tracking, and EPF/drift surfacing.

---

## Field states (v0)
The overlay emits a state and a recommended action.

### States
- `FIELD_STABLE`
  - Ordering sensitivity is low; decisions/gates appear stable.
- `FIELD_STRAINED`
  - Some ordering sensitivity or missing stability evidence; proceed with caution.
- `FIELD_COLLAPSED`
  - Strong ordering dependence or instability; treat as a stop signal (diagnostic).
- `UNKNOWN`
  - Insufficient inputs to assess; fail-closed diagnostic stance.

### Recommendation
- `recommendation.gate_action`:
  - `OPEN` / `SLOW` / `CLOSED`
- `recommendation.rationale`:
  - short, human-readable explanation

> Diagnostic rule: when uncertain, the overlay should prefer `UNKNOWN` and `CLOSED`
> recommendation rather than asserting stability without evidence.

---

## Determinism requirements
The overlay must be deterministic and audit-friendly:
- stable ordering of keys and lists (sorted)
- no wall-clock timestamps (optionally use `SOURCE_DATE_EPOCH`)
- stdlib-only behaviour is preferred for CI portability

---

## How to run locally

### Baseline only (RDSI proxy if available)
```bash
python scripts/separation_phase_adapter_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out PULSE_safe_pack_v0/artifacts/separation_phase_v0.json

```
With permutation runs (recommended)

python scripts/separation_phase_adapter_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --permutation-glob "PULSE_safe_pack_v0/artifacts/permutations/status_*.json" \
  --out PULSE_safe_pack_v0/artifacts/separation_phase_v0.json


Contract check

python scripts/check_separation_phase_v0_contract.py \
  --in PULSE_safe_pack_v0/artifacts/separation_phase_v0.json

CI integration guidance (recommended)


Run this overlay in a shadow/diagnostic workflow.


Upload separation_phase_v0.json as an artifact.


Run the contract checker as a CI step.


Do NOT make this a required normative gate until:


thresholds are calibrated,


false positives are understood,


and the signals are stable across representative workloads.





Promotion path (future)
Suggested progression:


Diagnostic-only (current): overlay + artifacts + contract validation


Soft enforcement: warnings / PR comments when FIELD_COLLAPSED


Hard gate: require non-collapsed state only after calibration and stability proof



Troubleshooting


UNKNOWN state:


baseline status.json missing, or no stable signal available


provide permutation runs or ensure status.json includes decision/metrics




Many unstable_gates:


investigate whether gate inputs are nondeterministic


check whether permutations are legitimate (only permute operations that should commute)




Contract check fails:


ensure the generator output matches the schema


lists must be sorted (unstable/threshold-like gate lists)




  

