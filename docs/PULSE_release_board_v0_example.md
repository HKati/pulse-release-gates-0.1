# PULSE Release Board v0 – mini governance example

This document shows a **minimal governance board view** built on top of
PULSE Decision Field v0 artefacts.

The goal is to illustrate how a release board might reason over:

- release_state (from decision_engine_v0),
- stability_type (field regime),
- RDSI (Release Decision Stability Index),
- field tension (EPF),
- Δ-direction error (drift),
- and resulting governance actions.

This is a schematic example, not a full UI specification.

---

## 1. Mini release board (ASCII layout)

Below is a small ASCII-style board that combines decision and field
signals for four fictional releases.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PULSE RELEASE BOARD v0                              │
│                         (Decision Field + Governance)                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ release_id   | release_state  | stability_type   | RDSI  | EPF  | Δ-dir |   │
│              |                |                  |       |      | error |   │
├──────────────┼────────────────┼──────────────────┼───────┼──────┼───────┤   │
│ rel-prod-001 | PROD_OK        | stable_good      | 0.97  | low  | 0.02  │   │
│              |                |                  |       |      |       │   │
│              | → Action: ship to prod with       |       |      |       │   │
│              |   standard monitoring.            |       |      |       │   │
├──────────────┼────────────────┼──────────────────┼───────┼──────┼───────┤   │
│ rel-prod-002 | PROD_OK        | unstably_good    | 0.88  | high | 0.11  │   │
│              |                |                  |       |      |       │   │
│              | → Action: ship, but classify as   |       |      |       │   │
│              |   "green but tense"; require      |       |      |       │   │
│              |   extra monitoring and field      |       |      |       │   │
│              |   review (paradox & Δ analysis).  |       |      |       │   │
├──────────────┼────────────────┼──────────────────┼───────┼──────┼───────┤   │
│ rel-stage-003| STAGE_ONLY     | boundary         | 0.65  | med  | 0.18  │   │
│              |                |                  |       |      |       │   │
│              | → Action: keep in stage; more     |       |      |       │   │
│              |   Decision Field mapping needed   |       |      |       │   │
│              |   (stability map + paradox field).|       |      |       │   │
├──────────────┼────────────────┼──────────────────┼───────┼──────┼───────┤   │
│ rel-block-004| BLOCK          | unstably_bad     | 0.42  | high | 0.25  │   │
│              |                |                  |       |      |       │   │
│              | → Action: do not ship. Escalate   |       |      |       │   │
│              |   to safety / policy. Investigate |       |      |       │   │
│              |   paradox atoms and gate design.  |       |      |       │   │
└──────────────┴────────────────┴──────────────────┴───────┴──────┴───────┘


---


## 2. Column meanings (mechanical view)

- `release_state` (from `decision_engine_v0`)

  - `PROD_OK` → required gates pass; green from a pure gating perspective.  
  - `STAGE_ONLY` → only allowed in stage.  
  - `BLOCK` → release is blocked.

- `stability_type` (from `decision_engine_v0`)

  - `stable_good` → field overlays show a stable, low‑tension region.  
  - `unstably_good` → gates pass, but the field around this decision is structurally tense.  
  - `boundary` → decision lives near a field boundary (for example, a trade‑off front).  
  - `unstably_bad` → both gates and field overlays indicate high risk / instability.

- `RDSI` (Release Decision Stability Index)

  - scalar in \[0, 1] approximating how often the decision survives shocks  
    (perturbations, reruns, configuration changes).  
  - `0.97` → almost invariant; `0.42` → highly volatile.

- `EPF` (tension band)

  - qualitative field tension around the decision region:  
    `low` / `med` / `high`.  
  - derived from paradox structure, curvature and proximity to field boundaries.

- `Δ-dir error` (directional error)

  - approximate measure of drift away from a balanced field state:  
    - small (~0.0) → symmetric; paradox can be held as a stable regime,  
    - larger values → the system tends to escape toward one side.

- `Action`

  - governance decision based on all of the above:  
    - ship,  
    - ship with caution,  
    - keep in stage,  
    - block and escalate.

---

## 3. How this maps to PULSE artefacts

Each row in the board corresponds to a set of PULSE artefacts:

- `status.json`  
  - base gate results and classical metrics.

- `paradox_field_v0.json`  
  - paradox atoms and severity; informs EPF tension and `stability_type`.

- `stability_map_v0.json`  
  - curvature / Δ-bend; informs whether the region is flat, boundary or highly curved.

- `decision_engine_v0.json`  
  - combines gates + paradox + stability overlays into:
    - `release_state`,
    - `stability_type`,
    - summaries for each layer.

- optional field metrics overlay  
  - RDSI, EPF tension band, Δ-direction error,  
  - derived from ensembles or additional analysis.

The board is simply a human-facing surface over these mechanical signals.

---

## 4. Governance patterns in this board

- `rel-prod-001` (`PROD_OK` + `stable_good`)

  - high RDSI, low EPF, low Δ-dir error  
  → stable and low tension → ship to prod with standard monitoring.

- `rel-prod-002` (`PROD_OK` + `unstably_good`)

  - good gates, but higher EPF and noticeable Δ-dir error  
  → green but structurally tense → ship, but as "green but tense",  
    with extra monitoring and field review.

- `rel-stage-003` (`STAGE_ONLY` + `boundary`)

  - mid RDSI, medium EPF, moderate Δ-dir error  
  → boundary region → keep in stage; require more Decision Field mapping  
    (stability map + paradox field) before allowing prod.

- `rel-block-004` (`BLOCK` + `unstably_bad`)

  - low RDSI, high EPF, high Δ-dir error  
  → unstable and risky → block release, escalate to safety/policy,  
    investigate paradox atoms and gate design.

---

## 5. Usage as a template

This mini release board can be used as:

- a template for internal release/approval boards that want to consume
  PULSE Decision Field artefacts,
- a conceptual starting point for dashboards:
  - columns,
  - labels,
  - colour regimes,
- a communication tool for explaining field stability and paradox to
  non‑technical stakeholders.

It shows how a mechanical decision field (`status.json`, paradox field,
stability map, decision engine) becomes a governance surface:
a small table of releases, each annotated with stability, tension and
drift, plus the human action.

