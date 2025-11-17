# PULSE Topology v0  
Stability Map, Decision Engine and Dual View

## 1. Introduction

PULSE provides deterministic, fail-closed release gates for AI systems.  
The core pack focuses on **safety** and **product quality**:

- safety invariants and guardrails (Iₗ–Iᵣ),
- product-facing quality gates (Q₁–Q₄),
- a human-readable Quality Ledger and stability index (RDSI),
- CI wiring for reproducible, auditable decisions.

PULSE Topology v0 is an **optional diagnostic layer** that sits *on top* of the
deterministic release gates. It does **not** change `status.json` or CI behaviour.
Instead, it:

- reorganises existing artefacts into a **Stability Map** of runs,
- derives a **Decision Engine** trace on top of the release gates,
- exposes a shared **Dual View** JSON as a human + agent interface.

This design note describes the goals, structure and current status of
PULSE Topology v0.

---

## 2. Motivation

The core PULSE pack answers a hard question:

> “Is this release allowed to ship?”  

via deterministic PASS/FAIL gates and a fail-closed policy.

In practice, teams also need to understand:

- **how stable** their release decisions are,
- **how a sequence of runs** (experiments, fixes, rollbacks) behaves as a *trajectory*,
- **why** a technically PASSing run might still be structurally unstable,
- how to give both **humans and agents** a compact narrative of the decision.

Topology v0 addresses these gaps by:

1. turning individual CI runs into **ReleaseStates** with instability scores,
2. connecting runs with **ReleaseTransitions** that capture change and risk,
3. deriving a **Decision Trace** that explains the current recommended action,
4. projecting everything into a **Dual View** JSON that humans can read and agents can parse.

---

## 3. Design overview

Topology v0 is intentionally small and rule-based. It introduces no new CI
decisions; it only derives additional views from existing artefacts.

The layer consists of three main components:

1. **Stability Map v0**
2. **Decision Engine v0**
3. **Dual View v0**

The repository ships with:

- topology schemas under `schemas/` (Stability Map, Decision Trace, Dual View),
- concept docs under `docs/`,
- an example topology demo under `docs/examples/topology_demo_v0/`,
- a demo workflow in `.github/workflows/pulse_topology_demo.yml`.

---

## 4. Stability Map v0

### 4.1 ReleaseState

A **ReleaseState** is a structured snapshot of a single PULSE run at release time.
In v0 it aggregates:

- meta:
  - `run_id`, `commit`, `model_name`, `timestamp`,
- release decision:
  - `release_level` ∈ {`FAIL`, `STAGE-PASS`, `PROD-PASS`},
- gate outcomes and metrics:
  - safety and quality gates from `status.json`,
  - stability index (RDSI) and other metrics,
- derived instability:
  - `instability.score` ∈ [0, 1],
  - `instability.components` (safety / quality / RDSI / EPF),
- paradox signal:
  - whether structural contradictions were detected,
- optional EPF shadow information (if available):
  - `epf_L`, `shadow_pass`, etc.

The formal JSON shape is defined in
`schemas/PULSE_stability_map_v0.schema.json`
and documented in `docs/PULSE_topology_v0.md`.

### 4.2 ReleaseTransition

A **ReleaseTransition** connects two ReleaseStates:

- `from` → `to` (run identifiers),
- `label`: short human summary of the change
  (e.g. *"fairness data fix + retrain"*),
- `delta_instability` and `delta_rds`,
- `category` ∈ {`STABILISING`, `DESTABILISING`, `NEUTRAL`},
- optional tags.

Transitions allow us to talk about **trajectories**:

- from a failing baseline to a candidate release,
- from a stable release into a risky follow-up experiment.

### 4.3 Stability Map artefact

A Stability Map v0 artefact is a JSON object:

- `version`: schema version,
- `generated_at`: timestamp,
- `states`: list of ReleaseStates,
- `transitions`: list of ReleaseTransitions.

In the demo, the map is built by:

```bash
python PULSE_safe_pack_v0/tools/build_stability_map.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --status-epf PULSE_safe_pack_v0/artifacts/status_epf.json \
  --out PULSE_safe_pack_v0/artifacts/stability_map.json
