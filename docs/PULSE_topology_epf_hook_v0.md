# PULSE topology ↔ EPF hook (v0)

> Conceptual bridge between the EPF shadow layer and the optional topology layer.

This note explains how to think about the relationship between:

- the deterministic baseline release path,
- the EPF shadow comparison path,
- and the optional topology / decision-field overlays.

Important boundary:

- the baseline deterministic path remains the source of truth for release gating
- EPF shadow remains diagnostic and CI-neutral
- the topology layer remains an optional reader / interpreter over archived artefacts

This document is conceptual by design.
It explains the hook between layers; it does not redefine release semantics.

For the current EPF experiment flow, see:

- [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md)
- [PULSE_epf_shadow_pipeline_v0_walkthrough.md](PULSE_epf_shadow_pipeline_v0_walkthrough.md)
- [PARADOX_RUNBOOK.md](PARADOX_RUNBOOK.md)

For the broader topology picture, see:

- [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md)
- [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md)

---

## 1. Why this hook exists

PULSE already has a clear deterministic center:

- one run produces a machine-readable `status.json`
- the main CI path enforces fail-closed gate outcomes
- optional diagnostic layers can be added on top

EPF shadow and topology belong to that optional outer layer, but they are not
the same thing.

A useful mental split is:

- **baseline gates** answer:
  - “What is the deterministic release decision?”

- **EPF shadow** answers:
  - “How fragile does that decision look near the decision boundary?”

- **topology / decision-field overlays** answer:
  - “How should humans interpret the broader stability pattern across the run?”

This file exists to keep those roles distinct.

---

## 2. Normative boundary

The normative release path remains anchored to:

- the final `status.json`
- deterministic gate enforcement
- the primary release CI workflow

That means:

- a passing EPF shadow result must not silently rescue a failing baseline run
- a worrying topology interpretation must not silently rewrite release policy
- a missing shadow artefact must not be reinterpreted as “stable”

Baseline first, shadow second, topology third.

That order should remain stable.

---

## 3. Current artefact relationship

### 3.1 Baseline artefacts

The baseline safe-pack flow produces the core artefacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Interpretation:

- `status.json` = machine-readable release state
- `report_card.html` = human-readable review surface

### 3.2 EPF shadow artefacts

The EPF experiment path can additionally produce comparison artefacts such as:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

Interpretation:

- `status_baseline.json` = deterministic reference inside the EPF experiment
- `status_epf.json` = shadow-side comparison state
- `epf_report.txt` / `epf_paradox_summary.json` = disagreement summaries for triage

### 3.3 Topology artefacts

The topology layer is optional and diagnostic.

Conceptually it reads baseline artefacts and may use optional EPF context to
produce higher-level views such as:

- stability maps
- decision-field overlays
- decision-engine summaries
- reviewer-facing narratives

Important nuance:

- the **conceptual topology model** can use optional EPF signals,
- but some topology components in the repo are still demo / design-note level.

So this hook is intentionally **artifact-first and conceptual**, not a claim that
every topology component already consumes live EPF shadow outputs today.

---

## 4. The intended hook

The intended EPF → topology hook is:

1. **baseline provides the authoritative state**
   - gates, metrics, release outcome

2. **EPF shadow adds fragility context**
   - near-threshold sensitivity
   - shadow disagreement
   - optional contraction / stability hints (for example `epf_L`-style signals)

3. **topology consumes both as interpretation inputs**
   - not to replace the baseline,
   - but to describe whether the run looks:
     - stable,
     - unstable,
     - paradox-prone,
     - or review-heavy.

This means EPF should enrich topology mainly along three axes:

- **boundary sensitivity**
- **local stability / fragility**
- **paradox prioritisation**

---

## 5. What EPF should contribute to topology

Good topology-level uses of EPF shadow include:

### A. Stability context

A deterministic PASS can still be operationally fragile.

EPF shadow is useful when topology wants to say:

- this run is passing, but only narrowly
- this run is passing, but repeatedly fragile near threshold
- this run deserves staging caution rather than confident production language

### B. Boundary-pressure signals

EPF is especially useful near threshold boundaries.

Topology can use that to distinguish:

- “cleanly stable PASS”
from
- “technically PASS, but pressure is accumulating”

### C. Paradox / review prioritisation

When the same kinds of shadow disagreements repeat, topology can surface that as:

- governance pressure,
- reviewer attention,
- or a candidate area for richer coverage and future policy discussion.

### D. More honest reviewer narratives

Without EPF-style shadow context, a topology layer can look cleaner than the run
really is.

With EPF context, topology can say:

- “the release state is acceptable, but it is not comfortably robust”
- “the baseline is authoritative, but the shadow path suggests operational fragility”

That is a real improvement in reviewer honesty.

---

## 6. What EPF should *not* do inside topology

EPF should **not** be used to:

- silently override baseline gate outcomes
- bypass the main CI / policy path
- transform one shadow disagreement into an implicit release-policy rewrite
- treat missing EPF artefacts as evidence of stability
- make topology outputs look more authoritative than the baseline artefacts

A useful check:

If the topology output would cause a reader to think
“this overrules the baseline release decision,”
the hook has become too strong.

---

## 7. Suggested artifact-first flow

A clean layering model is:

### Step 1 — Run the deterministic baseline

Produce and archive:

- `status.json`
- `report_card.html`

### Step 2 — Optionally run EPF shadow

Produce and archive:

- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

### Step 3 — Build optional topology overlays

Read archived artefacts only.

Possible inputs:

- baseline `status.json`
- optional EPF shadow artefacts
- optional paradox / field overlays

### Step 4 — Emit reviewer-facing topology views

Examples:

- stability summaries
- decision-engine outputs
- topology dashboards
- field / paradox views

These outputs remain **diagnostic governance surfaces** unless a future reviewed
policy explicitly promotes them into a normative role.

---

## 8. Interpretation patterns

### Case 1 — Baseline PASS, EPF quiet

Topology can describe this as a relatively stable positive state.

Examples:

- stable_good-like language
- low reviewer concern
- ordinary archival / rollout path

### Case 2 — Baseline PASS, EPF warns or disagrees

Topology can describe this as:

- unstable or review-heavy positive state
- staging caution
- candidate for richer evaluation

But the baseline PASS remains authoritative.

### Case 3 — Baseline FAIL, EPF PASS

Topology may note:

- boundary sensitivity
- possible false-fail pressure
- need for more evidence

But it must **not** convert this into an automatic unblock.

### Case 4 — Repeated shadow disagreement on the same gate family

Topology can escalate this as:

- persistent fragility
- governance debt
- threshold / coverage review candidate

That is a good topology use-case.
It is still not the same thing as a direct policy rewrite.

---

## 9. Decision Engine note

If a topology / decision-engine layer emits diagnostic outputs such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`

those should be interpreted as **review / governance summaries** unless and until
the repository explicitly makes them normative.

The main release decision still belongs to the deterministic gate path.

This distinction matters a lot:
a diagnostic decision-engine vocabulary may overlap with release language,
but it is not automatically the release authority.

---

## 10. Design invariant

Keep this invariant stable:

- **baseline** = normative decision
- **EPF shadow** = fragility / disagreement signal
- **topology** = optional interpretation layer over archived artefacts

As long as that ordering is preserved, the repository can grow richer review
surfaces without blurring release semantics.

---

## 11. Related docs

- [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md)
- [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md)
- [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md)
- [PULSE_epf_shadow_pipeline_v0_walkthrough.md](PULSE_epf_shadow_pipeline_v0_walkthrough.md)
- [PARADOX_RUNBOOK.md](PARADOX_RUNBOOK.md)
- [STATE_v0.md](STATE_v0.md)
- [DRIFT_OVERVIEW.md](DRIFT_OVERVIEW.md)
