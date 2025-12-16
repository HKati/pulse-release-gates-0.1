# PULSE–PD Dropzone (v0)
Status: field-notes / staging  
Purpose: single-file capture of PD v0 specification + operator protocol blocks. Append-only. No polishing.

---

## 1) PULSE–PD — Paradox Diagram (v0 → next phase) — summary (8 points)

### 0. Motivation (why this exists)
PULSE–PD (Paradox Diagram) is an instrumentation layer for **decision-field diagnostics**: it surfaces regions where an analysis decision is unstable, internally inconsistent across admissible model variants, or dominated by a steep boundary.

**Scope statement (repo-facing):**  
PULSE–PD does not introduce new physical hypotheses, detector instrumentation, or event-level measurements.  
It quantifies properties of the **decision function** (cuts / classifiers / likelihood thresholds) that maps reconstructed features to an accept/reject outcome (signal-like vs background-like) within an analysis pipeline.

The “paradox” is treated as an **indicator of decision-field tension**, not as an error condition.

### 1. Where PULSE–PD sits in the pipeline
PULSE–PD attaches at the **closure point**: where the analysis decides whether an event is accepted or rejected under a selection rule or decision boundary.

It is not upstream of reconstruction, and not downstream of the final physics result; it operates at the stage where interpretive closure is applied.

### 2. Dimensions (v0) — not “axes”
D1 — Decision Stability (DS)  
Measures whether small parameter perturbations change the binary decision.

D2 — Model Inconsistency (MI)  
Measures disagreement across a set of *equally admissible* model variants / parameterizations for the same input.

D3 — Gate Friction / Boundary Sharpness (GF)  
Measures how steep or “tight” the decision boundary is in feature space (small input perturbations cause large decision probability change).

### 3. Paradox Index (PI) — v0 definition
PI highlights co-occurrence of instability + inconsistency + sharp boundary:

PI = (1 − DS) · MI_n · GF_n

Interpretation (operational):
- PI ≈ 0 → no paradox indication under v0 protocol
- PI ↑ → region worth inspection (not a conclusion)

PI does not claim *what* is present, only *where* inspection is warranted.

### 4. Practical operation (what PD does / does not do)
PULSE–PD marks regions and produces artifacts. It does not:
- discard events,
- declare new physics,
- replace the analysis interpretation.

It measures decision behavior **during closure**, not after-the-fact.

### 5. Why this is typically missed
Standard pipelines optimize for final selection outcomes (average/smooth/exclude).  
PULSE–PD measures the closure logic itself: where a decision appears stable only because the pipeline collapses or thresholds the field.

### 6. LHC-compatibility (conceptual)
No hardware changes required. Integration points:
- cut-based selections,
- classifier score thresholds,
- likelihood boundaries,
- low-significance / background-dominated zones (as decision-field regions).

### 7. First implementation phase (realistic)
Open data + simple cut-based or lightweight classifier pipeline.
Outputs:
- PD scatter (DS/MI/GF),
- PI map / timeline,
- flagged regions (WATCH/PEAK) for follow-up.

### 8. Why this matters inside PULSE
PULSE governs release decisions via deterministic gates.
PULSE–PD extends the system with a diagnostic layer for *where closure is unstable*, enabling targeted review rather than broad narrative.

Next phase: bind PD to a concrete measurement target and run PD over region×time slices with a deterministic perturb protocol.

---

## 2) PULSE–PD Operator Prompt (v0) — paste-ready

**Role:** You are a PULSE–PD operator.  
You do not interpret physics. You do not rewrite definitions. You produce artifacts and stop.

### Non-negotiable rules
1. No refactors. No “improvements” to core definitions.
2. No deletions. Append-only outputs.
3. Core invariants are read-only (PD definitions, perturb protocol, normalization).
4. No narrative conclusions. Only marking and artifact emission.
5. Produce artifacts, then stop.

### Mandatory steps (strict order)
Step 1 — Validate (fixed seed, v0 protocol, required inputs present)  
Step 2 — Compute (DS/MI/GF/PI for region × time)  
Step 3 — Zone (OK/WATCH/PEAK via run-level percentiles)  
Step 4 — Driver (argmax of {1−DS, MI_n, GF_n} with deterministic tie-break)  
Step 5 — Recommend (where/when/what-to-adjust; no conclusions)  
Step 6 — Freeze (export artifacts; end run)

### Required outputs (v0 artifact set)
- `pd_run_meta.json`
- `pd_metrics.jsonl`
- `pd_zones_v0.jsonl`
- `pd_peaks_v0.json`
- `pd_run_report_v0.md`
- `pi_map.*` / `pi_timeline.*` / `pi_components.*` (format/tooling-defined)

### Forbidden
- Interpretive claims (e.g., “this implies new physics”).
- Any rewriting of PD core definitions.
- Any refactoring beyond the run outputs.

### Allowed closing line (verbatim)
“The run marked where closure is not stable.”

---

## 3) PD mechanics blocks (v0)

### PI zones (v0)
Define `PI_all` as PI computed over **all region × time samples** in the run.

Thresholds:
- `t_watch = percentile(PI_all, 80)`
- `t_peak  = percentile(PI_all, 95)`

Zones (per sample):
- OK: `PI < t_watch`
- WATCH: `t_watch ≤ PI < t_peak`
- PEAK: `PI ≥ t_peak`

Stable vs transient peaks:
- `STABLE_PEAK` if a PEAK repeats in ≥ k time windows (default: k = 2)
- else `TRANSIENT_PEAK`

Driver label:
- `driver = argmax({1−DS, MI_n, GF_n})`
- Deterministic tie-break order (v0): `(1−DS) > MI_n > GF_n`

### Normalization (v0)
Compute run-level percentiles over all samples:
- `MI_p10, MI_p90 = percentile(MI_all, 10), percentile(MI_all, 90)`
- `GF_p10, GF_p90 = percentile(GF_all, 10), percentile(GF_all, 90)`

Normalize and clip:
- `MI_n = clip((MI - MI_p10) / (MI_p90 - MI_p10 + eps), 0, 1)`
- `GF_n = clip((GF - GF_p10) / (GF_p90 - GF_p10 + eps), 0, 1)`

Then:
- `PI = (1−DS) * MI_n * GF_n`

Where:
- `eps` is a small constant to avoid divide-by-zero (v0: eps = 1e-12).

### Perturb protocol (v0)
Deterministic run:
- fixed seed (e.g., 42)
- fixed sampling count N (e.g., 64)
- fixed window set (time windows predefined)

Threshold perturbations (one parameter at a time):
- `Δθ ∈ {−2ε, −ε, 0, +ε, +2ε}`

Time shifts on predefined windows:
- `Δt ∈ {−1, 0, +1}` (window index shifts)

Spatial shifts on a fixed grid (if applicable):
- `{N, S, E, W, none}`

Feature perturbations (GF only):
- `Δx ∈ {−δ, +δ}` on selected features

MI model set:
- predefined deterministic ensemble `m1..mk` (fixed membership and order)

### Decision schemas (v0)
All schemas must define a binary closure decision:
- `decide(x, θ) -> {0, 1}`

A) Cut-based
- `decide(x, θ)` via threshold logic over features / derived quantities

B) Probabilistic
- `prob(x, θ) -> [0, 1]`
- `decide(x, θ) = 1{ prob(x, θ) >= p_min }`

C) Classifier score
- `score(x, θ)` real-valued
- `decide(x, θ) = 1{ score(x, θ) >= score_min }`

Perturb thresholds for DS; model-set drives MI; feature perturbations drive GF.

---

## Notes
- This file is intentionally append-only during field phase.
- Later: split into documentation modules and code once the operator protocol stabilizes.
