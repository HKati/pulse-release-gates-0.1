# PULSE–PD (Paradoxon Diagram) — v0

PULSE–PD is a meta-measurement module that evaluates the *decision field* of an analysis:
it measures where and how an event becomes “signal” or “background” at the decision moment (θ),
instead of measuring the event itself.

**Not new physics. Not a new detector. Not an event-level tagger.**
It highlights *where to look* by quantifying paradox-like regions near decision boundaries.

---

## Where PULSE–PD sits in an analysis pipeline

Detector hits  
→ reconstruction (tracks/clusters)  
→ feature set `X`  
→ selection cuts / decision parameters `θ`  
→ classifier / likelihood  
→ physics result

**PULSE–PD measures here:** at **selection / decision time** (θ).

---

## Core quantities

### DS — Decision Stability
How often the decision flips under small perturbations of decision parameters.

Intuition:
- DS ≈ 1: stable decision surface
- DS ≈ 0: brittle / unstable

### MI — Model Inconsistency
Variance of decisions across multiple “equally valid” models/parameterizations.

Intuition:
- MI high: multiple valid views disagree → blind spot candidate

### GF — Gate Friction (decision sharpness / tension)
Sensitivity of decision probability with respect to feature changes.

Intuition:
- GF high: tiny feature drift → large decision change

### PI — Paradox Index
A combined indicator that increases when:
- DS ↓, MI ↑, GF ↑

v0 uses:
- `PI = (1 - DS) * MI * GF` (with optional normalization)

---

## Inputs / outputs

### Input data contract
See `pulse_pd/EXPORT_SCHEMA.md`.

Recommended input container: **NPZ** (`X.npz`):
- Required: `X` (n_events, n_features)
- Recommended: `feature_names` (n_features)
- Optional traceback identifiers:
  - `event_id` OR HEP triplet: `run`, `lumi`, `event`
  - optional `weight`

### Outputs
Depending on the entrypoint:
- PD scatter plot (DS vs MI colored by PI)
- PI heatmap over selected feature dimensions
- JSON summary (basic stats, top PI bins)
- CSV export of top PI events (with identifiers if present)

---

## Quickstart (toy end-to-end)

# 1) Generate a toy dataset (NPZ with IDs)
python -m pulse_pd.examples.make_toy_X \
  --out pulse_pd/examples/X_toy.npz \
  --n 5000 \
  --seed 0

# 2) Run cut-based PD and write artifacts
python -m pulse_pd.run_cut_pd \
  --x pulse_pd/examples/X_toy.npz \
  --theta pulse_pd/examples/theta_cuts_example.json \
  --dims 0 1 \
  --out pulse_pd/artifacts_run

# Expected artifacts:
# - pulse_pd/artifacts_run/pd_scatter.png
# - pulse_pd/artifacts_run/pi_heatmap.png
# - pulse_pd/artifacts_run/pd_summary.json

# 3) Export top PI events to CSV (traceback-ready)
python -m pulse_pd.export_top_pi_events \
  --x pulse_pd/examples/X_toy.npz \
  --theta pulse_pd/examples/theta_cuts_example.json \
  --out pulse_pd/artifacts_run/top_pi_events.csv \
  --topn 200

# If X.npz contains event_id or run/lumi/event,
# the CSV will include those columns.

---

## Theta: cut-based configuration

{
  "k": 8.0,
  "sigma": 0.02,
  "cuts": [
    { "feat": 0, "op": ">", "thr": 0.0, "sigma": 0.02, "scale": 1.0 },
    { "feat": 1, "op": ">", "thr": 0.0, "sigma": 0.02, "scale": 1.0 }
  ]
}

## Named feature cuts (preferred for real pipelines)

# You can reference features by name
# (requires feature_names in X.npz or an explicit mapping in theta)

{
  "cuts": [
    { "feat": "pt_lead", "op": ">", "thr": 25.0 },
    { "feat": "eta_lead", "op": "<", "thr": 2.4 }
  ]
}

---

## Interpreting results (v0 guidance)

High PI does not claim new physics.

High PI suggests a region where:
- the decision is unstable (DS low),
- multiple admissible views disagree (MI high),
- the decision boundary is sharp or tense (GF high).

Use the top PI CSV to trace back to original events/regions and inspect:
- boundary neighborhoods (cuts / thresholds),
- “discarded” bands previously considered uninteresting,
- regions sensitive to small parameter shifts.

---

## Development notes

This is v0: the goal is a minimal, inspectable implementation.

Preferred runtime target: standard Linux / CI.

Plotting requires matplotlib (runner).
CSV export is matplotlib-free.

---

## Next steps

Add a small adapter stub that exports real analysis features into X.npz following the schema.

Add a minimal CI smoke test that generates toy X and runs the exporter
(to prevent regressions).


