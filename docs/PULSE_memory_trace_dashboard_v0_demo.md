# PULSE Memory / Trace Dashboard v0 – Demo

Status: working draft (v0)  
Scope: example-only notebook for exploring the memory / trace artefacts.

This demo notebook shows a compact “dashboard” view on top of the memory / trace
pipeline, driven entirely from a shared module:

- panels live in `_memory_trace_panels_v0_cells.py`
- the notebook only has a tiny driver cell

---

## 1. Prerequisites

Before running this demo, you should already have created the memory / trace
artefacts as described in:

- `docs/PULSE_memory_trace_v0_walkthrough.md`

From those steps you should have these files under `./artifacts/`:

- `stability_map.json`
- `decision_output_v0.json`
- `decision_paradox_summary_v0.json`
- `paradox_history_v0.json`
- `paradox_resolution_v0.json`
- `paradox_resolution_dashboard_v0.json` (optional)
- `delta_log_v0.jsonl` (optional per-run delta log)

The dashboard will run even if some of the optional artefacts are missing; it
will simply skip panels that cannot find their inputs.

---

## 2. Where to find the notebook

The demo lives here:

```text
PULSE_safe_pack_v0/examples/PULSE_memory_trace_dashboard_v0_demo.ipynb
