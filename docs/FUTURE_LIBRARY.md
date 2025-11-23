# PULSE Future Library v0

Status: working draft (v0)  
Scope: experimental / shadow-only components built on top of PULSE Topology v0.

The Future Library is a staging area for next-generation PULSE components that
are **wired into the topology**, but do **not** yet drive the main release gate
logic. They are meant to run in *shadow* mode, expose richer fields, and feed
dashboards / analysis / memory.

Current pillars:

1. Topology v0 family  
2. EPF signal layer (shadow-only)  
3. Paradox Resolution v0  
4. Topology dashboards v0  
5. Memory / trace summariser v0  

Below is a map of what exists today (code + docs), and how it fits together.

---

## 1. Topology v0 family

Core references for the PULSE topology layer and Stability Map.

**Design & schema**

- `docs/PULSE_topology_v0_design_note.md`  
  – Topology v0 layer, states / transitions, Stability Map concepts.

- `schemas/PULSE_stability_map_v0.schema.json`  
  – Stability Map v0 schema, extended with:
  - `ReleaseState.paradox_field_v0`
  - `ReleaseState.epf_field_v0`

**Tools**

- `PULSE_safe_pack_v0/tools/build_stability_map_v0.py`  
  – Builds `stability_map.json` (Topology v0) from `status.json` (+ optional EPF
    status), including gate summary, instability components, paradox flags, etc.

This is the base layer: all other Future Library components currently sit
*on top* of `stability_map.json`.

---

## 2. EPF signal layer (shadow-only)

The EPF signal is treated as an **external sensor** that is projected into
PULSE’s topology as a **field**, not as a new hard-coded gate rule.

**Design**

- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`  
  – End-to-end walkthrough of the EPF shadow pipeline v0:
  - how EPF appears in the Stability Map,
  - how it is exposed in Decision Engine v0,
  - how it is summarised for dashboards / memory.

**Tools**

- `PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py`  
  - Input: `stability_map.json` (Topology v0).  
  - For each `ReleaseState` attaches:
    - `paradox_field_v0` (paradox atoms + summary)
    - `epf_field_v0` (EPF physical field: phi/theta/energy + anchors)

- `PULSE_safe_pack_v0/tools/build_decision_output_v0.py`  
  - Input: enriched `stability_map.json` (with `paradox_field_v0` + `epf_field_v0`).  
  - Output: `decision_output_v0.json` (shadow-only Decision Engine v0 view) with:
    - selected `release_state`
    - `paradox_field_v0` / `epf_field_v0`
    - `decision_trace[]` (with `paradox_stamp`)
    - `dual_view.paradox_panel_v0`

This pillar is fully shadow-only: it does **not** change the gate logic, only
adds a rich EPF / paradox field layer.

---

## 3. Paradox Resolution v0

First formalisation of paradox handling in PULSE. Shadow-only planning artefact on top of paradox history.

**Design**

- `docs/PULSE_paradox_resolution_v0_design_note.md`  
  – conceptual design for paradox triage / resolution.
- `docs/PULSE_paradox_resolution_v0_walkthrough.md`  
  – how `paradox_resolution_v0.json` is built from history and how to read it.

**Tools**

- `PULSE_safe_pack_v0/tools/build_paradox_resolution_v0.py`
  - Input: `paradox_history_v0.json` (from `summarise_paradox_history_v0.py`)
  - Output: `paradox_resolution_v0.json`
  - Per-axis entry:
    - `axis_id`, `runs_seen`, `times_dominant`
    - `max_tension`, `avg_tension`
    - `severity` (LOW/MEDIUM/HIGH/CRITICAL)
    - `priority` (1–4, 1 = highest)
    - `recommended_focus[]` (generic, non-binding focus hints)

**Notes**

- Gate logic is not modified.  
- Heuristics are simple v0 rules that can be tuned in later versions.  
- The artefact is meant for human triage / planning, not as an automatic policy.

---

## 4. Topology dashboards v0

Flattened, dashboard-friendly views on top of the Stability Map.

**Design**

- `docs/PULSE_topology_dashboards_v0_design_note.md`  
  – Initial ideas for topology dashboards:
  - state-level rows,
  - transition-level views,
  - integration with paradox / EPF fields.

**Tools**

- `PULSE_safe_pack_v0/tools/build_topology_dashboard_v0.py`  
  - Input: `stability_map.json` (Topology v0, ideally with EPF/paradox fields).  
  - Output: `topology_dashboard_v0.json`, containing:
    - `states[]`: one row per `ReleaseState`:
      - id, label
      - decision, type
      - instability_score
      - paradox_zone + paradox_max_tension
      - EPF snapshot (phi/theta)
      - headline string for dashboards / logs
    - `transitions[]`: simplified view:
      - from, to, label
      - delta_instability, delta_rdsi, delta_epf_L
      - category, tags[]

This is the main entry point for visual dashboards over the topology.

---

## 5. Memory / trace summariser v0

Aggregated, cross-run view of paradox and EPF behaviour over time:
a first **memory layer** for the EPF / paradox field.

**Design**

- `docs/PULSE_memory_trace_summariser_v0_design_note.md`  
  – High-level design for memory / trace summarisation:
  - how to compress many runs into a small set of metrics,
  - how to project paradox axes into history.

**Tools**

- `PULSE_safe_pack_v0/tools/summarise_decision_paradox_v0.py`  
  - Input: `decision_output_v0.json` (single run).  
  - Output: `decision_paradox_summary_v0.json`, a compact per-run summary:
    - run_id, decision, type
    - stability snapshot (rdsi, instability_score)
    - paradox overview (max_tension, dominant_axes, per-axis stats)
    - EPF overview (phi_potential, theta_distortion, energy_delta)

- `PULSE_safe_pack_v0/tools/summarise_paradox_history_v0.py`  
  - Input: directory of `decision_paradox_summary_v0*.json` files.  
  - Output: `paradox_history_v0.json`, containing:
    - `runs[]`: per-run records (decision, instability, paradox zone, EPF snapshot)
    - `paradox_history`:
      - zone_counts (green/yellow/red/unknown)
      - max_tension_overall
      - per-axis history (runs_seen, times_dominant, max/avg tension)
    - `epf_history`:
      - min/max/avg for phi_potential and theta_distortion

**Walkthrough & demo**

- `docs/PULSE_memory_trace_v0_walkthrough.md`  
  – Step‑by‑step walkthrough for running the full memory / trace demo
    and interpreting the artefacts.

- `PULSE_safe_pack_v0/examples/PULSE_trace_dashboard_v0_demo.ipynb`  
  – Demo notebook that renders Pareto coverage of paradox axes,
    instability × RDSI quadrants, and decision streaks based on the
    trace artefacts.
### Developer tools (current & future)

#### Decision trace schema validator (dev utility)

- Path: `PULSE_safe_pack_v0/tools/validate_decision_trace_v0.py`
- Purpose: validate `decision_trace_v0.json` artefacts against
  `schemas/PULSE_decision_trace_v0.schema.json` using `jsonschema`.
- Scope: developer‑only helper for local validation and optional CI usage.
- Does not change any PULSE gate logic or CI behaviour.
- Future option: wire into CI to guard decision trace exports, or extend
  with additional schema checks as new trace fields appear.

This is the first working version of a “memory / trace summariser v0” for the
EPF / paradox field.

---

## 6. Invariants for the Future Library v0

Across all of the above, the following invariants hold:

- The main **release gate logic is unchanged**.  
- Existing structures (`status.json`, `stability_map.json`, `paradox`, `epf`)
  keep their meaning.  
- New fields (`paradox_field_v0`, `epf_field_v0`, dashboards, history) are
  **additive** and schema-backed.  
- EPF is treated as an **external sensor** projected into the PULSE topology
  as a field, not as a direct gate rule.  
- All Future Library components are safe to run in *shadow mode* alongside
  the existing pipeline.
