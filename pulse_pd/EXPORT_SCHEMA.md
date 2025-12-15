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
