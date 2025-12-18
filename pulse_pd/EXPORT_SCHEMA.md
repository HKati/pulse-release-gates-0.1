# PULSE–PD Export Schema (X contract)

This document defines the minimal, stable input contract for PULSE–PD tools.

## Goal
Make any analysis pipeline (cut-based, BDT, NN, etc.) able to export a feature matrix `X`
and optional identifiers so PULSE–PD can:
- compute DS/MI/GF/PI
- export top PI events
- allow *traceback* to the original analysis (critical for LHC workflows)

---

## Recommended container: NPZ
Use `X.npz` (NumPy `.npz`) as the primary interchange format.

### Required keys
- `X`: float array, shape `(n_events, n_features)`

### Strongly recommended keys
- `feature_names`: list/array of strings, length `n_features`
  - Example: `["pt_lead", "eta_lead", "m_ll", "bdt_score", ...]`

### Optional identifiers (traceback)
Provide at least one of:
- `event_id`: string/int array, shape `(n_events,)`
  - Generic single identifier (works outside HEP too)
OR the HEP triplet:
- `run`: int array, shape `(n_events,)`
- `lumi`: int array, shape `(n_events,)`
- `event`: int array, shape `(n_events,)`

### Optional extras (allowed)
- `weight`: float array, shape `(n_events,)`  (event weight)
- `y`: int array, shape `(n_events,)` (labels for toy/sanity checks; not required)
- any other arrays of shape `(n_events,)` are allowed if you keep naming consistent

---

## CSV support
CSV is supported for numeric-only feature matrices.
If you need identifiers (especially string `event_id`), prefer NPZ.

- With header: column names become `feature_names`.
- Without header: features are indexed `x0..x{d-1}`.

---

## Theta (cut config) compatibility
Cut-based `theta` can refer to features by:
- index: `"feat": 3`
- name: `"feat": "pt_lead"` (requires `feature_names` in NPZ/CSV or `theta.feature_names` mapping)

---

## Example: export in Python
```python
import numpy as np

# X: (n, d)
# run/lumi/event: (n,)
np.savez(
  "X.npz",
  X=X,
  feature_names=np.array(feature_names, dtype=object),
  run=run,
  lumi=lumi,
  event=event,
  weight=weight,   # optional
)

```

---

## PD run artifacts (v0)

When running `python -m pulse_pd.run_cut_pd --out <dir>`, the runner writes a minimal, audit-friendly artifact set.

### `pd_run_meta.json` (run metadata)

A schema-stable run record intended for audit and downstream tooling.

- `schema`: `"pulse_pd/pd_run_meta_v0"`
- `tool`: `"pulse_pd.run_cut_pd"`
- `argv`: list of CLI arguments (for reproducibility)
- `inputs`: `{ x, x_key, theta, dims_requested, out }`
- `resolved`: `{ dims: {x,y}, dim_names: {x,y} }`
- `params`: runner parameters (ds/mi/gf + heatmap + seed)
- `data`: `{ n, d, feature_names, feature_names_source }`
- `traceback_fields_present`: `{ event_id, run, lumi, event, weight }` (best-effort for NPZ)
- `artifacts`: filenames emitted into the output directory

Notes:
- This file is intentionally deterministic (sorted keys; no timestamps) to avoid noisy diffs.

### `pd_zones_v0.jsonl` (zones)

One JSON object per line; each line describes a “zone” derived from `top_pi_bins`.

Per-line object keys:
- `schema`: `"pulse_pd/pd_zone_v0"`
- `rank`: integer rank (1..K)
- `zone_id`: stable id string
- `dims`: `{ x, y, x_name, y_name }`
- `ranges`: `{ x: [min,max], y: [min,max] }`
- `stats`: `{ mean_pi, count }`
- `source`: `"top_pi_bins"`

### `pd_peaks_v0.json` (peaks summary)

A compact summary object derived from `top_pi_bins`, suitable for “Dropzone v0” consumers.

Top-level keys:
- `schema`: `"pulse_pd/pd_peaks_v0"`
- `dims`: `{ x, y, x_name, y_name, feature_names_source }`
- `params`: `{ bins, topk, min_count }`
- `peaks`: list of peak objects
- `source`: `"top_pi_bins"`

Each peak object:
- `rank`
- `zone_id`
- `stats`: `{ mean_pi, count }`
- `bin`: `{ x, y }`
- `ranges`: `{ x: [min,max], y: [min,max] }`
- `center`: `{ x, y }`
