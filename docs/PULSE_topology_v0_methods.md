# PULSE Topology v0 — Methods

This note gives a practical, CLI‑oriented overview of the **Topology v0** layer:

- how to build a **Stability Map v0** from `status.json` + `status_epf.json`,
- how to run the **Decision Engine v0** on top of the Stability Map,
- how to build a **Dual View v0** artefact for human + agent inspection.

It is intentionally minimal and follows the topology demo layout under:

- `docs/examples/topology_demo_v0/`
- `.github/workflows/pulse_topology_demo.yml`


## 1. Inputs and artefacts

Topology v0 consumes existing PULSE outputs and produces *derived* artefacts.

### 1.1 Primary inputs

For a single run `run_002`, the typical inputs are:

- `status.json`  
  Deterministic PULSE release gates output (safety & quality groups, metrics, RDSI).

- `status_epf.json`  
  EPF shadow metrics and instability components for the same run.

Both files are usually produced by the main PULSE CI workflow and stored under:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/status_epf.json`

(or an equivalent location in your repo).

### 1.2 Topology artefacts

Topology v0 builds three additional JSON artefacts:

- **Stability Map v0**
  - Two‑level structure with:
    - states (baseline run, fairness‑fix run, …)
    - transitions between states
  - stability score + instability components per state
  - optional EPF instability flag / shadow signal

- **Decision Trace v0**
  - Structured trace of the decision engine for one target state:
    - risk level
    - release decision (`BLOCK`, `STAGE_ONLY`, `PROD_OK`)
    - per‑gate details (safety, quality, paradox handling)
  - intended to be human‑readable and machine‑checkable.

- **Dual View v0**
  - Combined **human view**:
    - headline
    - risk summary
    - paradox summary
    - timeline highlights
  - and **agent view**:
    - action
    - risk level
    - instability
    - paradox
    - decision
    - history
  - exported as a single JSON document.

In the demo, the artefacts live under:

- `PULSE_safe_pack_v0/artifacts/stability_map.demo.ci.json`
- `PULSE_safe_pack_v0/artifacts/decision_trace.demo.ci.json`
- `PULSE_safe_pack_v0/artifacts/dual_view_v0.demo.ci.json`


## 2. Building a Stability Map v0

Script:

```text
PULSE_safe_pack_v0/tools/build_stability_map.py
