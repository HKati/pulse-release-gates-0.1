# STABILITY_FIELD_MAP_v0

> Conceptual map of the main “fields” used by PULSE for stability and
> governance: RDSI, EPF, Stability Map types, G-field overlays and drift
> indicators.

This document is **descriptive**: it explains what each field family means,
where it comes from, how it is typically used, and what it is *not* meant
to do. It does **not** define the JSON schemas; those live next to the
artefacts (status.json, stability_map_v0.json, etc.).

---

## 0. How to read this map

Each section follows the same pattern:

- **Field family** – the conceptual “bucket” (e.g. RDSI, EPF, Stability Map).
- **Example fields** – typical keys / symbols you will see in artefacts.
- **Definition** – what the field family represents.
- **Input source(s)** – which artefacts or logs feed it.
- **Typical usage** – where this is expected to show up in practice.
- **Not for** – common misuses to avoid.

The goal is to make it easier to:

- name new APIs and dashboards consistently,
- avoid overloading a field with the wrong responsibility,
- review Governance Pack changes against a shared mental model.

---

## 1. RDSI – Release Decision Stability Index

**Field family**

- RDSI, sometimes written as `rdsi` or `rdsi_score`.

**Example fields**

- `rdsi.score`
- `rdsi.bucket` (e.g. `HIGH`, `MEDIUM`, `LOW`)
- `rdsi.components[]` (per-gate or per-dimension contributions)

**Definition**

RDSI is a **scalar index** summarising:

- how stable the release decision is over time, and
- how robust it is against small changes in conditions (e.g. sample variance).

Intuitively: “How confident are we that repeating this evaluation under
similar conditions would lead to the **same** PASS/FAIL decision?”

**Input source(s)**

- historical `status.json` artefacts,
- gate outcomes across runs (PASS/FAIL, borderline cases),
- internal stability heuristics (e.g. gate variability, margin to thresholds).

**Typical usage**

- Quality Ledger summary: “RDSI: HIGH (0.88)” in the release card.
- Stability Map components: one of the terms in the instability score.
- Governance: quick “risk flag” for how much weight to put on a single run.

**Not for**

- Detailed root-cause analysis (RDSI is **not** a diagnostic).
- Comparing model performance across entirely different tasks or products.
- Acting as a hard gate on its own without context (it is a *supporting* signal).

---

## 2. EPF – Experimental/Probabilistic Fields

**Field family**

- EPF metrics that treat evaluation as **experiments** instead of pure counts.

**Example fields**

- `metrics.epf_L` – EPF score or loss-like aggregated metric.
- `metrics.epf_p_value`
- `metrics.epf_ci_low`, `metrics.epf_ci_high`
- per-gate EPF entries under `gates[].epf_*`.

**Definition**

EPF is a layer of metrics that:

- treat the evaluation as a sampling process,
- compute confidence intervals and/or test statistics,
- express uncertainty and variation explicitly.

It is meant to answer: “Given the sample we observed, how strong is our
evidence that this gate or metric behaves as intended?”

**Input source(s)**

- same raw test data as for deterministic gates,
- paired or repeated measurements (e.g. A/B setups, control vs treatment),
- EPF computation tooling (not necessarily part of the core pack).

**Typical usage**

- Quality Ledger “EPF band” around core metrics (e.g. groundedness).
- Paradox analysis: cases where EPF suggests “OK” but deterministic gates fail,
  or vice versa.
- Governance Playbook: justification for “monitoring only” vs “block” decisions.

**Not for**

- Replacing deterministic invariants (I-gates) for hard safety guarantees.
- Hiding behind “non-significant” results when the effect size is obviously bad.
- Claiming formal statistical guarantees beyond the assumptions of the experiment.

---

## 3. Stability Map – field types & instability score

**Field family**

- Stability Map fields summarising runs along “stability” dimensions.

**Example fields**

- `stability_map_v0.instability_score`
- `stability_map_v0.stability_type`  
  (e.g. `stable_good`, `unstably_good`, `high_tension`, `paradox_heavy`)
- `stability_map_v0.components[]`  
  (per-gate or per-dimension instability contributions)
- `stability_map_v0.notes[]` (short drift / tension notes)

**Definition**

The Stability Map is a **compressed view** over:

- safety gate outcomes (I-gates),
- quality gate outcomes (Q-gates),
- RDSI and EPF components,
- detected paradoxes / tensions.

It maps these into:

- a single **instability score**, and
- a coarse **stability type** label.

**Input source(s)**

- historical and current `status.json`,
- RDSI and EPF metrics (if available),
- optional overlays (paradox, G-field, drift).

**Typical usage**

- Decision Engine input: `stability_type` and `instability_score` drive rules.
- Governance dashboard: “heatmap” of stability vs time / versions.
- Release review: highlighting “high tension” or “paradox heavy” releases.

**Not for**

- Fine-grained debugging at the test-case level.
- Replacing raw gate outcomes in compliance reports (it is an aggregate).
- Mixing together unrelated products/models without segmentation.

---

## 4. Paradox & Tension fields

**Field family**

- Fields that capture **tensions** between different objectives:

  - safety vs utility,
  - refusal vs productivity,
  - fairness vs SLO.

**Example fields**

- `paradox_field_v0.paradox_score`
- `paradox_field_v0.cases[]` (e.g. “safe but useless”, “risky but informative”)
- `paradox_tags[]` on gates or scenarios
- references from `decision_trace[]` entries.

**Definition**

Paradox / tension fields mark places where:

- deterministically “good” outcomes carry hidden risks, or
- stricter safety would unacceptably degrade utility.

They are **markers for trade-offs**, not binary pass/fail signals.

**Input source(s)**

- joint analysis of:
  - safety metrics (refusals, sanitisation, etc.),
  - utility metrics (coverage, helpfulness, task success),
- EPF or other experimental overlays highlighting conflicts.

**Typical usage**

- Governance Playbook: “If paradox_score is high in fairness vs SLO, consider…”.
- Decision Engine: flagging `stability_type = high_tension` or `paradox_heavy`.
- Design discussions: identifying areas needing policy or product-level choices.

**Not for**

- Automatically blocking releases without human review.
- Treating paradox presence as a bug that must always be “fixed”.
- Hiding trade-offs (these fields are meant to *surface* them).

---

## 5. G-field & GPT usage overlays

**Field family**

- Fields derived from the **G-field**: model topology and usage overlays,
  especially around external GPTs and providers.

**Example fields**

- `g_field_v0.nodes[]`, `g_field_v0.edges[]`
- `g_field_v0.providers[]` (internal vs external)
- `gpt_external_detection_v0.external_call_ratio`
- `gpt_external_detection_v0.high_risk_provider_calls`
- `g_field_stability_v0.stability_score`

**Definition**

G-field & GPT overlays describe:

- which models are called where (topology),
- how often external vs internal providers are used,
- where calls touch “high-risk” providers or configurations.

They answer: “What is the **runtime AI footprint** of this system, provider-wise?”

**Input source(s)**

- `logs/model_invocations.jsonl` or equivalent invocation logs,
- environment / config metadata (provider labels, risk classifications),
- optional EPF overlays linking quality differences to provider choices.

**Typical usage**

- Governance dashboards: dependency on external GPTs over time.
- Risk board inputs: where high-risk providers are used, how often.
- Decision Field snapshots: links from PULSE outcomes to G-field views.

**Not for**

- Evaluating safety/quality of the model content by itself.
- Enforcing low-level infra policies (that’s still infra/security tooling).
- Precise billing or cost accounting (these are governance-level aggregates).

---

## 6. Drift indicators & history fields

**Field family**

- Fields that encode **change over time**: drift, regressions, shifts.

**Example fields**

- `status_history.jsonl` entries with:
  - `run_id`, `timestamp`, `model_version`, `gate_summary`, `rdsi`, etc.
- `drift_summary_v0.json` (if implemented)
- `delta` fields from `diff_runs_minimal.py` output:
  - `delta.gates[]` (e.g. `pass → fail`, `margin_shrink`),
  - `delta.metrics[]` (e.g. latency, cost, refusal rates).

**Definition**

Drift indicators capture:

- how gate outcomes and metrics change across runs,
- whether there is a consistent trend in a “bad” direction,
- which parts of the system are becoming unstable or fragile.

**Input source(s)**

- appended `status.json` artefacts (history),
- differences computed between pairs or windows of runs,
- optional labels (e.g. “new model version”, “policy change”).

**Typical usage**

- Stability Map inputs: drift as a component in the instability score.
- Release reviews: “what changed since last release?” summaries.
- Alerts or dashboards: flagging sudden drops in safety/quality.

**Not for**

- Exact root cause attribution (drift is a *symptom*).
- Replacing good observability on the underlying services.
- Single-run decisions (drift requires a time window by definition).

---

## 7. Summary table (cheat sheet)

High-level cheat sheet of the field families:

| Family        | Example fields                              | Primary question                                  |
|---------------|---------------------------------------------|---------------------------------------------------|
| **RDSI**      | `rdsi.score`, `rdsi.bucket`                 | How stable/robust is this release decision?       |
| **EPF**       | `metrics.epf_L`, `epf_ci_low/high`          | How strong is the experimental evidence?          |
| **Stability** | `stability_type`, `instability_score`       | Is this run stable, unstable or high-tension?     |
| **Paradox**   | `paradox_score`, `paradox_tags[]`           | Where are the trade-offs between safety/utility?  |
| **G-field**   | `g_field_v0.*`, `external_call_ratio`       | How do we depend on internal vs external GPTs?    |
| **Drift**     | `status_history`, `delta.gates[]/metrics[]` | How are things changing over time?                |

Use this map when:

- naming new fields or overlays,
- wiring Stability Map and Decision Engine inputs,
- writing governance docs and dashboards.

The goal is consistency: people should be able to guess **what a field is for**  
from its name and family, before reading the implementation.
