# PULSE Topology Dashboards v0 – Design Note

> Status: draft – experimental design note for now.  
> Scope: visual comparison of PULSE Topology v0 runs across releases.  
> Non‑goals: no new release gates, no change to `status.json` or CI decisions.

This note sketches a first "Topology dashboards v0" module for the PULSE future library.
The module does **not** introduce new release behaviour; it only reads existing
topology artefacts (Stability Map v0, Decision Engine v0, Dual View v0) and produces
aggregated views across multiple runs.

The goal is to make it easier for humans to see patterns across releases:

- how stability scores evolve over time,
- where paradox patterns cluster,
- how optional EPF signals line up with the deterministic decisions.

---

## 1. Inputs

The dashboards operate *on top of* existing topology artefacts. For one **run** we assume:

- `stability_map.json` – Stability Map v0 output (per‑type stability, paradox flags, etc.),
- `decision_trace.json` – Decision Engine v0 output (BLOCK / STAGE_ONLY / PROD_OK + explanation),
- `dual_view.json` – Dual View v0 output (human + agent view of the same run),
- (optional) `status_epf.json` – EPF shadow metrics for the same run, if available.

A minimal per‑run layout (non‑normative) could look like:

```text
my_topology_runs/
  run_001/
    stability_map.json
    decision_trace.json
    dual_view.json
    status_epf.json        # optional, shadow‑only
  run_002/
    ...
