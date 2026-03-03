# PULSE topology overview (v0)

> High-level overview of the optional topology layer on top of deterministic
> PULSE release artefacts.

The topology layer is a **diagnostic overlay**.

It exists to help humans interpret:

- release stability,
- field / paradox tension,
- reviewer-facing decision context,
- and the difference between “deterministically passing” and “operationally robust”.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- the topology layer is optional
- topology outputs do not silently rewrite release semantics

For the EPF ↔ topology conceptual bridge, see:

- `docs/PULSE_topology_epf_hook.md`

For the current repository state and normative boundary, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

## 1. What the topology layer is

PULSE already has a deterministic center:

- one run produces a machine-readable `status.json`
- the main CI path enforces fail-closed gate semantics
- the Quality Ledger explains the run for humans

The topology layer is the next optional layer on top of that core.

Its role is to answer questions like:

- “How stable does this run look?”
- “Is this a clean PASS or a fragile PASS?”
- “Where is paradox / tension pressure accumulating?”
- “How should a reviewer interpret the broader state of the run?”

That makes topology a **review and governance layer**, not a second gate engine.

---

## 2. Normative boundary

Keep this order stable:

1. **baseline deterministic gating**
   - authoritative release decision

2. **shadow / optional diagnostic signals**
   - EPF shadow
   - paradox-related diagnostic artefacts
   - hazard overlays
   - other reviewer-facing overlays

3. **topology interpretation**
   - stability summaries
   - decision-field views
   - optional decision-engine outputs
   - dashboard / narrative overlays

This ordering matters.

A topology output must never silently overrule the baseline deterministic
release outcome.

If a topology artifact and the normative gate path disagree, the deterministic
gate path wins.

---

## 3. Current conceptual components

The current topology family is best understood as three closely related ideas.

### 3.1 Stability Map v0

The Stability Map is the “where does this run sit?” view.

Conceptually it aggregates:

- the core `status.json`
- optional EPF / fragility context
- optional field or paradox overlays

Its job is to summarize the run into a stability-oriented interpretation, not to
replace the underlying gate outcomes.

Examples of what it might express:

- stable positive state
- unstable positive state
- fragile or review-heavy state
- unresolved / paradox-prone state

### 3.2 Decision Engine v0

The Decision Engine is a **diagnostic summarizer**.

It can emit reviewer-oriented states such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`
- `UNKNOWN`

Those should be read as governance-facing interpretation outputs unless and
until the repository explicitly promotes them into normative policy.

That distinction is important:

- the vocabulary can resemble release language,
- but the baseline deterministic gate path remains authoritative.

### 3.3 Dual View v0

The Dual View is the idea that the same run can be rendered in two compatible
forms:

- a concise human-readable narrative
- a structured machine-readable summary

This is especially useful for:

- reviewer workflows
- PR summaries
- dashboards
- agent / tooling consumption without losing human interpretability

---

## 4. What topology reads

Topology is intended to be **artifact-first**.

Its natural inputs are archived run artefacts such as:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- optional EPF shadow outputs
- optional paradox / field overlays
- optional detector summaries, when relevant to interpretation

This is a strong design choice:

- topology should read immutable artefacts,
- not create hidden release semantics through live ad hoc computation.

---

## 5. Relationship to EPF shadow

EPF shadow and topology are related, but they are not the same layer.

A useful split is:

- **baseline gates**
  - tell you the deterministic release decision

- **EPF shadow**
  - tells you where the decision may be fragile near thresholds

- **topology**
  - tells you how to interpret the broader pattern formed by those signals

Good topology uses of EPF include:

- surfacing boundary sensitivity
- distinguishing clean PASS from fragile PASS
- highlighting repeated paradox candidates
- prioritizing reviewer attention

Bad topology uses of EPF would be:

- silently rescuing a baseline FAIL
- silently converting one shadow warning into a policy rewrite
- treating missing shadow artefacts as evidence of stability

For the detailed bridge, see:

- `docs/PULSE_topology_epf_hook_v0.md`

---

## 6. Relationship to paradox / field views

Topology and paradox are adjacent, not identical.

### Paradox / field artifacts

These are useful for showing:

- tension,
- co-occurrence structure,
- instability clusters,
- or unresolved conflict around gate families.

### Topology layer

Topology turns those signals into a larger interpretive picture:

- is the run locally stable?
- is it operationally fragile?
- is reviewer caution warranted?
- does this look like accumulating governance debt?

So paradox artifacts are often **inputs** to topology interpretation, not the
whole topology layer by themselves.

---

## 7. Recommended reading of a run

A practical reading order is:

1. **Read the baseline deterministic run**
   - `status.json`
   - Quality Ledger / report card

2. **Check optional shadow / overlay signals**
   - EPF shadow outputs
   - paradox or field overlays
   - hazard overlays, if present

3. **Use topology outputs last**
   - to summarize and interpret
   - not to replace the evidence below them

This order keeps topology honest.

---

## 8. Typical interpretation patterns

### Case A — Clean deterministic PASS, quiet diagnostics

Topology can describe this as a stable or ordinary positive state.

Typical reviewer implication:

- low concern
- ordinary archival / rollout path

### Case B — Deterministic PASS, noisy shadow / paradox signals

Topology can describe this as:

- unstable positive state
- fragile PASS
- staging caution
- review-heavy positive state

Important: baseline PASS still remains normative.

### Case C — Deterministic FAIL, calmer diagnostics

Topology may note that the run is less unstable than expected, but it must not
convert a baseline FAIL into a silent unblock.

### Case D — Repeated disagreement on the same gate family

Topology is especially useful here.

It can elevate the pattern into:

- governance attention,
- threshold review candidate,
- need for richer evaluation coverage,
- or candidate for future policy discussion.

That is exactly the kind of “bigger than one run” interpretation topology is
good at.

---

## 9. What topology is good for

The topology layer is especially valuable for:

- reviewer summaries
- governance dashboards
- stability narratives
- decision-field style interpretation
- prioritizing follow-up work
- distinguishing robust from merely passing systems

It is **not** the right place to hide release-policy changes.

If release semantics need to change, that belongs in:

- policy,
- the main gating workflow,
- the canonical contracts,
- and reviewed change history.

---

## 10. Design invariants

A healthy topology layer keeps these invariants stable:

- baseline deterministic gating stays normative
- topology stays artifact-first
- topology remains reproducible from archived artefacts
- optional shadow context remains optional
- missing diagnostic artefacts never become silent PASS signals
- reviewer language does not become an implicit policy rewrite

If one of these invariants changes, the canonical docs should change in the same
reviewed update.

---

## 11. Related docs

- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PARADOX_RUNBOOK.md`
- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`
