# PULSE–PD HEP adapters (v0)

This folder contains “HEP-native” adapters that export analysis features from common HEP formats into the **PULSE–PD input schema** (`X.npz`).

Design goals:
- keep the **core PD package** lightweight,
- keep HEP I/O deps **optional** (installed only by users who need them),
- produce **traceback-ready** exports (run/lumi/event/event_id, optional weight).

---

## What is exported (NPZ schema)

Required:
- `X` — float array, shape `(n, d)`
- `feature_names` — list/array of feature names, length `d`

Optional identifiers (for traceback):
- `run` — int array, shape `(n,)`
- `lumi` — int array, shape `(n,)`
- `event` — int array, shape `(n,)`
- `event_id` — string or int array, shape `(n,)`  
  (If not present, some exporters can generate it from `run:lumi:event`.)

Optional:
- `weight` — float array, shape `(n,)`

See also: `pulse_pd/EXPORT_SCHEMA.md`.

---

## Export ROOT → X.npz (uproot)

Module:
- `pulse_pd/hep/export_uproot_npz.py`

Dependency:
```bash
pip install uproot
```

Example (flat scalar branches):

```bash
python -m pulse_pd.hep.export_uproot_npz \
  --root /path/to/file.root \
  --tree Events \
  --features "pt_lead,eta_lead,phi_lead" \
  --out pulse_pd/artifacts_run/X_from_root.npz \
  --run-branch run \
  --lumi-branch luminosityBlock \
  --event-branch event \
  --weight-branch weight
```

Notes:

Only flat (1D) branches are supported for features.

Jagged / variable-length branches will fail fast (derive scalars upstream).

Run PD on exported X.npz (cut-based v0)
```bash
python -m pulse_pd.run_cut_pd \
  --x pulse_pd/artifacts_run/X_from_root.npz \
  --theta pulse_pd/examples/theta_cuts_example.json \
  --dims 0 1 \
  --out pulse_pd/artifacts_run
```

Export top-PI events:

```bash
python -m pulse_pd.export_top_pi_events \
  --x pulse_pd/artifacts_run/X_from_root.npz \
  --theta pulse_pd/examples/theta_cuts_example.json \
  --out pulse_pd/artifacts_run/top_pi_events.csv \
  --topn 200
```

If X.npz contains event_id or run/lumi/event, the CSV exporter includes those columns for traceback.

Legacy alias: `python -m pulse_pd.hep.export_root_npz ...` is supported, but `export_uproot_npz` is the canonical entrypoint.

Troubleshooting (quick)

“dtype=object” / jagged arrays: you likely selected a variable-length branch.
Export only scalar/flat branches, or add a preprocessing step in your analysis.

Length mismatch between branches: ensure all exported branches correspond to the same event selection and have identical entry counts.

Missing branches: check the exact branch names in your ROOT tree (case-sensitive).
