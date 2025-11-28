# PULSE Decision Field v0 – Topology + Decision Engine overview

This document gives a high-level overview of the **Decision Field v0**
layer in PULSE:

- how the different artefacts fit together:
  - `status.json`
  - `paradox_field_v0.json`
  - `stability_map_v0`
  - `decision_engine_v0.json`
  - (optionally) `decision_trace_v0`
  - and `Pulse Demo v1`,
- and how they collectively define a **decision field** instead of a
  single pass/fail surface.

It is a conceptual hub that points to the more detailed docs and examples.

---

## 1. Motivation – from pass/fail to decision field

Classic eval pipelines reduce everything to:

- a single score (e.g. accuracy, RDSI),
- or a small set of gating decisions (pass/fail).

This is powerful, but it hides:

- **paradoxical regions** (incompatible constraints that all look “correct”),
- **curved / unstable regions** (small changes in conditions flip the outcome),
- **meta-states** (e.g. being in a paradox field vs a simple region).

PULSE Decision Field v0 introduces an explicit **field view**:

> Instead of just “did we pass?”, we ask:
>  
> **“Where in the decision field are we, and how stable is that region?”**

This is expressed through a small stack of artefacts.

---

## 2. Layer 1 – `status.json` (baseline PULSE safe pack)

Produced by the standard PULSE safe pack:

- path: `PULSE_safe_pack_v0/artifacts/status.json` (by default)
- contains:
  - `gates` → boolean gate flags (policy, safety, quality, SLO, etc.),
  - `metrics` → scalar signals (e.g. RDSI),
  - metadata about the run.

In Decision Field v0, `status.json` is:

- the **base layer**:
  - it defines what “green” / “red” means at the gate level,
  - it is the source of truth for the initial `release_state`.

Related docs:

- (core PULSE docs)
- `docs/PULSE_topology_v0_cli_demo.md` – CLI path from `status.json` to overlays.

---

## 3. Layer 2 – `paradox_field_v0.json` (paradox atoms)

PULSE mines **paradox atoms** over the gate patterns by looking at:

- multiple `status.json` artefacts in a directory, and
- minimal unsatisfiable sets (MUS) of gates.

The resulting artefact:

- path: `PULSE_safe_pack_v0/artifacts/paradox_field_v0.json`
- root object: `paradox_field_v0`
- key contents:
  - `atoms[]`:
    - each atom has:
      - `gates`: a small set of gate identifiers,
      - `minimal`: whether this is a MUS,
      - `severity`: an approximate weight / impact.

Interpretation:

- each atom represents a **local paradox**:
  - a set of constraints that cannot all be satisfied together in a
    particular region of the field,
  - e.g. fairness vs SLO, safety vs latency.

In Decision Field v0, `paradox_field_v0` exposes:

- **where** structural tensions live,
- **which** combinations of gates keep causing trouble.

Related docs:

- `docs/PULSE_topology_v0_mini_example_fairness_slo_epf.md`
- `docs/PULSE_topology_v0_cli_demo.md`

---

## 4. Layer 3 – `stability_map_v0` (field curvature / topology)

Stability maps capture a coarse notion of:

- **curvature** in the decision field,
- over regions defined by a small number of axes (e.g. fairness threshold,
  SLO budget, EPF settings).

A demo stability map:

- path: `PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json`
- root object: `stability_map_v0`
- key contents:
  - `cells[]`:
    - `axes`: parameter ranges for this cell,
    - `delta_bend`: a small integer capturing curvature in this region.

Interpretation:

- `delta_bend ≈ 0` → locally flat / linear region,
- `delta_bend > 0` → curved / unstable region.

In Decision Field v0, `stability_map_v0` provides:

- a **geometric signal**:
  - how sensitive this region is,
  - whether small changes are likely to flip decisions.

Related docs:

- `docs/PULSE_topology_v0_cli_demo.md`
- `docs/PULSE_topology_v0_governance_patterns.md`

---

## 5. Layer 4 – `decision_engine_v0.json` (field-aware decision overlay)

The Decision Engine v0 combines:

- `status.json`
- `paradox_field_v0.json` (optional)
- `stability_map_v0` (optional)

into a compact overlay:

- path: `PULSE_safe_pack_v0/artifacts/decision_engine_v0.json`
- root object: `decision_engine_v0`
- key fields:
  - `release_state`:
    - `PROD_OK`, `STAGE_ONLY`, `BLOCK`, `UNKNOWN`
  - `stability_type`:
    - `stable_good`, `unstably_good`,
    - `stable_bad`, `unstably_bad`,
    - `boundary_simple`, `boundary`, `unknown`
  - `status_summary`, `stability_summary`, `paradox_summary`:
    - small summaries of each layer.

Interpretation:

- `release_state` says “what is the coarse decision?”
- `stability_type` says “what kind of region are we in?”

Examples:

- `PROD_OK + stable_good`  
  → green, locally flat, no strong paradox/curvature signals.

- `PROD_OK + unstably_good`  
  → green, but in a curved / paradox-rich region.

- `BLOCK + unstably_bad`  
  → blocked and in a structurally tense region.

Related docs:

- `docs/PULSE_decision_engine_v0_spec.md`
- `docs/PULSE_topology_v0_governance_patterns.md`
- `docs/PULSE_decision_engine_v0_unstably_good_example.md`
- `docs/PULSE_decision_engine_v0_unstably_bad_example.md`

---

## 6. Layer 5 – Decision trace and dual views (optional)

While Decision Engine v0 is a **summary**, the decision trace captures a
more detailed **path** through the decision field:

- `decision_trace_v0`:
  - a sequence of steps/events that show how the decision was built up
    over time (or over different overlays),
  - potentially including intermediate release_state / stability_type
    at each step.

A dual-view artefact (e.g. `dual_view_v0`) can capture:

- the **machine** view:
  - raw gates, metrics, atoms, cells,
- the **human** view:
  - curated explanations,
  - governance decisions,
  - sign-offs.

These are optional in Decision Field v0, but they are natural extensions
once the field vocabulary (`release_state`, `stability_type`, paradox
atoms, curvature) is in place.

Related tools/docs (if present):

- `PULSE_safe_pack_v0/tools/validate_decision_trace_v0.py`
- `PULSE_safe_pack_v0/tools/build_dual_view_v0.py`
- future docs for decision_trace / dual_view.

---

## 7. Layer 6 – Pulse Demo v1 (paradox stability showcase)

`docs/PULSE_demo_v1_paradox_stability_showcase.md` presents a focused,
narrative demo:

- a paradoxical prompt (liar sentence),
- typical unstable behaviour from classical LLMs,
- a Pulse-style **field-level response**:
  - identifying a paradox state instead of forcing true/false.

It also introduces illustrative field metrics:

- RDSI – Release Decision Stability Index,
- EPF shadow field tension,
- Δ-direction error,
- a meta-state signal.

These are:

- **not yet a formal schema**,
- but a **target for future implementations** of field-level stability
  metrics over paradoxical regions.

---

## 8. How the pieces fit together

A typical Decision Field v0 flow looks like:

1. **Run the safe pack**

   - produce `status.json` with gates and metrics.

2. **Build the paradox field**

   - run `pulse_paradox_atoms_v0.py` on one or more status artefacts,
   - get `paradox_field_v0.json`.

3. **(Optional) Build a stability map**

   - run a demo or real stability map builder,
   - get `stability_map_v0*.json`.

4. **Run Decision Engine v0**

   - combine `status.json` + `paradox_field_v0.json` + `stability_map_v0`,
   - get `decision_engine_v0.json` with `release_state` and `stability_type`.

5. **Use in governance / dashboards**

   - release boards:
     - use `release_state` + `stability_type` + summaries.
   - dashboards:
     - highlight `unstably_good`, `boundary`, `unstably_bad` regions.

6. **(Optional) Extend with decision traces and dual views**

   - generate `decision_trace_v0` for path-level visibility,
   - generate `dual_view_v0` for combined human/machine perspectives.

---

## 9. Summary

Decision Field v0 is the **conceptual layer** that ties together:

- **status (gates + metrics)** → “what happened?”
- **paradox field** → “which constraints are in tension?”
- **stability map** → “how curved / sensitive is this region?”
- **decision engine overlay** → “what is the coarse decision and what kind of
  region is it?”
- **demo and examples** → “how does this look in practice?”

It moves PULSE beyond:

- “just another safety config” or
- “just another eval score”,

towards a **field-level representation of decisions** where paradox,
curvature and structural tension are:

- explicit,
- measurable,
- and available to both machines and governance processes.
