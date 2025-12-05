# PULSE Governance Pack (v0)

> From PASS/FAIL gates to governance-ready decision fields.  
> The Governance Pack is an *optional* layer on top of PULSE Core.

---

## 0. Scope

PULSE Core answers:

- “Is this model / release safe enough and within basic SLOs to ship?”

The Governance Pack answers:

- “*How* safe and stable is it over time?”
- “Where are the tensions and paradoxes between safety and utility?”
- “What decision should we record: **BLOCK**, **STAGE-ONLY**, or **PROD-OK**, and why?”

All components in this pack are **CI-neutral by default**:

- they read existing PULSE artefacts (status.json, overlays, history),
- they emit additional JSON/markdown/HTML views,
- they do *not* change PASS/FAIL unless you explicitly wire them into CD.

---

## 1. Components

### 1.1 Stability Map

**Goal:** aggregate PULSE runs into a single “stability field” for a model line.

- **Inputs**
  - historical `status.json` artefacts (per run),
  - optional EPF / paradox overlays.
- **Output**
  - `stability_map_v0.json` with e.g.:
    - per-gate stability categories (`stable_good`, `unstably_good`, `high_tension`),
    - instability score and contributing components,
    - drift notes and timestamps.
- **Primary users**
  - ML leads, safety engineers, governance boards.

The Stability Map does *not* change CI status; it is a diagnostic view.

---

### 1.2 Decision Engine (shadow)

**Goal:** turn the Stability Map + current run into a structured decision object.

- **Inputs**
  - latest `status.json`,
  - `stability_map_v0.json`,
  - paradox / EPF overlays (if available).
- **Output**
  - `decision_engine_v0.json`, containing at minimum:
    - `release_state` ∈ {`fail`, `stage_only`, `prod_ok`},
    - `stability_type` (e.g. `stable_good`, `high_tension`),
    - `decision_trace[]` (rule hits, gate IDs, paradox links, short explanations).
- **Behaviour**
  - runs in **shadow mode** by default (no change to PASS/FAIL),
  - can later be used to gate prod deploys or drive human approvals.

The Decision Engine is a **policy surface**: rules should be small, explicit and auditable.

---

### 1.3 EPF & Paradox Playbook

**Goal:** make EPF and paradox signals actionable for humans.

- **Artefact**
  - `docs/PULSE_EPF_PARADOX_PLAYBOOK_v0.md`, answering questions like:
    - when is a gate considered “paradox-heavy”,
    - what it means if EPF is consistently better/worse than the baseline,
    - what to do in typical trade-off cases:
      - fairness vs SLO,
      - refusal policy vs utility,
      - hallucination vs productivity.
- **Usage**
  - referenced from the Quality Ledger and decision traces,
  - used in release reviews, post-mortems, and governance meetings.

The Playbook turns abstract metrics into concrete “if X, consider doing Y” patterns.

---

### 1.4 G-field & GPT overlays

**Goal:** give governance a compact view of dependency on internal vs external models and providers.

- **Inputs**
  - `g_field_v0.json` (G-field snapshot),
  - optional `g_field_stability_v0.json`,
  - `g_epf_overlay_v0.json` (bridge from EPF to G-field),
  - `gpt_external_detection_v0.json` (usage stats from `logs/model_invocations.jsonl`).
- **Output**
  - `g_snapshot_report_v0.md` or HTML:
    - key KPIs (external GPT call ratio, vendor mix, high-risk provider usage),
    - present / missing overlays,
    - short narrative for risk / governance boards.

The G-field is intended to answer questions like:

- “How much do we depend on external GPTs?”
- “Where are we using more models than the risk board is aware of?”

---

### 1.5 History & Drift tools

**Goal:** create a minimal history trail that higher-level tools can build on.

Candidate scripts:

- `scripts/append_status_history.py`
  - appends each run’s `status.json` to `logs/status_history.jsonl`,
  - can be called at the end of the PULSE CI job.
- `scripts/diff_runs_minimal.py`
  - compares two runs gate-by-gate,
  - emits a small JSON or markdown diff summary.

These scripts are deliberately small; they are foundations for future dashboards.

---

## 2. Integration patterns

The Governance Pack is designed to run **after** PULSE Core.

Typical pattern:

1. Core CI job runs and enforces the minimal gate set (fail-closed).
2. Governance jobs (separate workflows or jobs) consume:
   - `status.json`,
   - historical logs,
   - overlays (EPF, paradox, G-field).
3. Governance artefacts are published as:
   - markdown or HTML snapshots,
   - dashboards,
   - attachments to risk / release review tickets.

Examples:

- A nightly job that builds `stability_map_v0.json` from the latest history.
- A per-release job that generates `decision_engine_v0.json` in shadow mode.
- An on-demand job that produces the `g_snapshot_report_v0` for a specific branch or environment.

In all cases, CI for shipping code remains **fail-closed** on Core gates.

---

## 3. Roadmap (suggested)

This document only describes v0. A suggested evolution:

- **v0.1 — layout & schemas**
  - finalise JSON Schemas for `stability_map_v0` and `decision_engine_v0`,
  - provide at least one concrete example for each artefact.
- **v0.2 — minimal implementation**
  - first Stability Map builder over `logs/status_history.jsonl`,
  - first Decision Engine ruleset (small, explainable rules).
- **v0.3 — dashboards & UX**
  - lightweight Decision-Field dashboard (HTML/markdown),
  - links from Quality Ledger and G snapshot reports.
- **v1.0 — production governance profile**
  - documented decision policies for `BLOCK` / `STAGE-ONLY` / `PROD-OK`,
  - at least one real-world case study using the full Governance Pack.

---

## 4. Ownership

Suggested roles:

- **Field / topology owner**
  - Stability Map & Decision Engine design,
  - field definitions and stability types.
- **Governance lead**
  - EPF & Paradox Playbook,
  - decision policies and escalation paths.
- **Runtime / infra owner**
  - history logging, drift tooling, artefact storage,
  - simple dashboards and publishing.
- **Docs owner**
  - governance docs,
  - snapshot copy and examples kept up to date.

The Governance Pack is intentionally modular: teams can adopt it piece by piece,  
without touching the Core fail-closed gates.
