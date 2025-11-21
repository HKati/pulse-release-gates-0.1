# PULSE EPF + Memory status – v0

Status: working draft (v0)  
Scope: summary of the shadow-only EPF / paradox / memory layer on top of PULSE Topology v0.

This note gives a high-level overview of what already exists in the repo around:

- EPF "shadow" signal layer,
- paradox_resolution v0,
- memory / trace summarisation v0,
- trace dashboards built on top of these artefacts,

and outlines a few possible next steps.

It is intentionally human-facing and informal; for full details, see the design notes
and walkthrough documents referenced below.

---

## 1. Where to start reading

Core background docs:

- `docs/PULSE_topology_v0_design_note.md`  
  – Topology v0 layer, release states / transitions, Stability Map concepts.

- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`  
  – How EPF is projected into the Stability Map and Decision Engine v0.

- `docs/PULSE_paradox_resolution_v0_walkthrough.md`  
  – How `paradox_resolution_v0.json` is built from paradox history and how to read it.

- `docs/PULSE_memory_trace_v0_walkthrough.md`  
  – End-to-end memory / trace pipeline over multiple runs and dashboards.

- `docs/FUTURE_LIBRARY.md`  
  – Overview of the Future Library v0 pillars, including the memory / trace summariser.

---

## 2. What exists today (code + artefacts)

### 2.1 Topology v0 + Stability Map

Tools:

- `PULSE_safe_pack_v0/tools/build_stability_map_v0.py`  
  – Builds `stability_map.json` from `status.json` (+ optional EPF status),
    including gate summary, instability components and paradox flags.

- `PULSE_safe_pack_v0/tools/build_decision_output_v0.py`  
  – Builds `decision_output_v0.json`, a shadow-only Decision Engine v0 view
    enriched with paradox / EPF fields and decision trace.

These are the base artefacts that everything else currently sits on.

---

### 2.2 EPF shadow layer

Tools:

- `PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py`  
  – Projects external EPF measurements into `stability_map.json` as:
    - `paradox_field_v0` (paradox atoms + summary)
    - `epf_field_v0` (phi/theta/energy + anchors).

- `PULSE_safe_pack_v0/tools/build_decision_output_v0.py`  
  – Exposes the above fields in `decision_output_v0.json`
    together with the selected `release_state` and `decision_trace[]`.

Status:

- Fully **shadow-only**: gate logic and schemas remain unchanged.
- Safe to run alongside the main gate pipeline.

---

### 2.3 Paradox Resolution v0

Tools:

- `PULSE_safe_pack_v0/tools/summarise_paradox_history_v0.py`  
  – Aggregates many runs of `decision_paradox_summary_v0*.json` into
    `paradox_history_v0.json`.

- `PULSE_safe_pack_v0/tools/build_paradox_resolution_v0.py`  
  – Consumes `paradox_history_v0.json` and produces
    `paradox_resolution_v0.json` with per-axis recommendations.

- `PULSE_safe_pack_v0/tools/build_paradox_resolution_dashboard_v0.py`  
  – Optional dashboard-friendly view (`paradox_resolution_dashboard_v0.json`).

Status:

- Provides a first formalisation of paradox triage / resolution.
- Intended for human planning and dashboards, **not** for automatic gating.

---

### 2.4 Memory / trace summariser v0

Tools:

- `PULSE_safe_pack_v0/tools/summarise_decision_paradox_v0.py`  
  - Input: `decision_output_v0.json` (single run).  
  - Output: `decision_paradox_summary_v0.json` (per-run compact summary).

- `PULSE_safe_pack_v0/tools/summarise_paradox_history_v0.py`  
  - Input: directory of `decision_paradox_summary_v0*.json` files.  
  - Output: `paradox_history_v0.json` with:
    - runs[] (decision, instability, paradox zone, EPF snapshot),
    - per-axis histories,
    - EPF min/max/avg aggregations.

- `PULSE_safe_pack_v0/tools/build_paradox_resolution_v0.py`  
  - Input: `paradox_history_v0.json`.  
  - Output: `paradox_resolution_v0.json` (per-axis severity / priority /
    recommended_focus hints).

The walkthrough in `PULSE_memory_trace_v0_walkthrough.md` explains how to chain
these tools into a full memory / trace pipeline.

---

### 2.5 Dashboards and the trace demo

- `_panels_v0_cells.py` (under `PULSE_safe_pack_v0/examples/`)  
  – Shared module that builds the trace dashboard panels from the memory artefacts.

- `PULSE_safe_pack_v0/examples/PULSE_trace_dashboard_v0_demo.ipynb`  
  – Minimal notebook that:
    - imports `run_all_panels` from `_panels_v0_cells.py`, and  
    - calls `run_all_panels(globals())` as a single driver cell.

The notebook intentionally stays small and delegates all plotting to the shared
module, which makes future edits safer (no embedded JSON blobs).

---

## 3. Invariants and safety constraints

Across the EPF / paradox / memory components described above, the following
invariants are deliberately maintained:

- The main **release gate logic is unchanged**.  
- Existing structures (`status.json`, `stability_map.json`, paradox fields)
  keep their meaning.  
- New fields and artefacts (`paradox_field_v0`, `epf_field_v0`, history /
  dashboards) are **additive** and schema-backed.  
- EPF is treated as an **external sensor** that is projected into the topology
  as a field, not as a hard-coded gate rule.  
- All components can safely run in *shadow mode* alongside the current pipeline.

---

## 4. Roadmap ideas (v1)

This section is intentionally speculative. It lists directions that could be
explored on top of the current v0 stack.

1. **Richer paradox / EPF metrics**
   - time-to-resolution and stability of resolutions across runs,
   - per-axis anomaly scores, EPF "spikes" and drifts.

2. **Additional dashboards**
   - multi-run timelines for paradox zones and EPF energy,
   - heatmaps over axes × runs, highlighting unstable regions,
   - summarised "status board" for humans (current plan, open paradoxes, EPF risk).

3. **APIs and re-use**
   - small, stable Python layer for consuming `*_v0.json` artefacts from other repos,
   - documented CSV exports for quick ad-hoc analysis.

4. **Potential future gate integration**
   - clearly separated experiments where memory / trace signals *inform*
     future release gates,
   - keeping the core v0 artefacts stable while iterating on policies.

These items are deliberately not commitments; they are a starting point for
discussing how the EPF + memory layer should evolve beyond v0.
