# PULSE topology v0 methods

> CLI-level methods note for the optional topology layer and Stability Map v0
> pipeline.

This document explains the **current methods surface** for topology-related
artifacts in this repository.

It is intentionally method-oriented:

- what the current tools are,
- what they read,
- what they emit,
- and how they should be interpreted.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- topology methods are optional and diagnostic
- topology outputs must not silently rewrite release semantics

For the conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For examples, see:

- `docs/PULSE_topology_v0_case_study.md`
- `docs/PULSE_topology_v0_quickstart_decision_engine_v0.md`
- `docs/PULSE_topology_v0_cli_demo.md`

---

## 1. Method scope

The topology family is meant to work **on top of archived run artifacts**.

The central question is not:

- “how do we replace the baseline release gates?”

It is:

- “how do we derive a stability-oriented interpretation from existing deterministic artifacts?”

That means the topology methods layer should stay focused on:

- artifact flow,
- input/output contracts,
- optional overlays,
- and reviewer-facing summaries.

---

## 2. Normative boundary

Keep this order stable:

1. **deterministic baseline**
   - authoritative release decision

2. **optional diagnostic overlays**
   - EPF shadow
   - paradox / field overlays
   - external evidence context
   - hazard-style signals

3. **topology methods and outputs**
   - stability-oriented summaries
   - decision-engine style outputs
   - dual-view / reviewer surfaces

If a topology output and the deterministic gate path disagree, the deterministic
gate path wins.

This methods note does not define new release policy.

---

## 3. Current repo-level tool surface

The current repo-level topology surface is intentionally modest.

### 3.1 Paradox field

Tool:

```text
PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py
```

Method role:

- reads a directory of `status.json` artifacts
- derives `paradox_field_v0.json`
- summarizes paradox atoms and a severity score

Use this when you want a structured paradox/field input for later topology interpretation.

---

### 3.2 Stability Map v0 (current CLI surface)

Tool:

```
PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py
```

Current role:

- produces a demo stability-map artifact
- represents the topology idea in a minimal synthetic form
- is **not yet the same thing as a fully general multi-run production stability-map builder**

That distinction matters.

The current repo gives you a working demo method surface for Stability Map
thinking, not a claim that the entire long-term topology stack is already
fully generalized.

---

### 3.3 Decision Engine v0

Tool:

```
PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py
```

Current method role:

- reads one required `status.json` artifact
- may also read optional overlays such as:
  - `stability_map_v0`
  - `paradox_field_v0`
- emits a compact `decision_engine_v0.json`

Typical fields include reviewer-facing summaries such as:

- `release_state`
- `stability_type`

This is a summarization layer, not a replacement for deterministic gating.

---

## 4. Minimal artifact-first pipeline

A clean topology method pipeline looks like this.

### Step 1 — Produce the deterministic baseline

Required artifact:

```
PULSE_safe_pack_v0/artifacts/status.json
```

This is the anchor artifact for all later interpretation.

Without this file, topology methods should not pretend to have an authoritative
release view.

---

### Step 2 — Optionally produce paradox / field context

Optional artifact family:

- `paradox_field_v0.json`
- related paradox / field summaries

These artifacts are useful when the run has conflict structure, recurring gate
tension, or reviewer-visible instability that should be described more honestly.

---

### Step 3 — Optionally produce stability-map context

Current repo-level surface:

- a demo Stability Map generator

Method intent:

convert baseline polarity + diagnostic stability context into a compact
stability-oriented representation.

Conceptually, this is where labels such as:

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `unknown`

become methodologically meaningful.

The exact schema belongs to the schema/artifact layer; the methods layer cares
about how those states are derived and interpreted.

---

### Step 4 — Run the Decision Engine

The Decision Engine then consumes:

- the required baseline `status.json`
- optional topology/paradox/stability inputs

and emits a compact reviewer-facing decision artifact.

Typical intent:

compress the current run into a summary posture without hiding the evidence
underneath it.

---

### Step 5 — Render optional dual views

The final optional step is to expose the same run in two compatible forms:

- a concise human-readable reviewer summary
- a machine-readable compact artifact

This is where the broader “Dual View” idea lives.

---

## 5. Input contracts (method view)

From a methods perspective, the topology family has **one required input** and
several optional ones.

### Required

- one deterministic `status.json` artifact

### Optional

- Stability Map artifact
- paradox / field artifact
- EPF shadow context
- external evidence context
- other diagnostic overlays that remain artifact-first

Method rule:

optional inputs may enrich the interpretation, but missing optional inputs must
never be silently reinterpreted as stability or PASS.

---

## 6. Output contracts (method view)

Topology methods should aim to emit artifacts that answer four questions cleanly:

1. What is the baseline release polarity?
2. What is the stability posture?
3. Which optional signals influenced that interpretation?
4. What reviewer posture is suggested?

A useful compact output therefore tends to contain:

- baseline-oriented summary
- stability type
- supporting input references
- short reviewer-facing narrative

Optional compact action posture such as:

- `routine`
- `caution`
- `deeper review`

This is a methods rule, not a commitment to one exact renderer layout.

---

## 7. Interpretation rules

### Rule A — Baseline first

Always anchor interpretation to the deterministic baseline artifact.

### Rule B — Optional context enriches, not overrules

EPF, paradox, and other overlays can make the picture more honest, but they do
not automatically change release policy.

### Rule C — Unknown stays unknown

If key inputs are missing or degraded, the topology layer should surface
uncertainty rather than invent confidence.

### Rule D — Reviewer language must remain audit-friendly

Topology output should be:

- reproducible,
- explainable,
- and traceable back to archived artifacts.

That is more important than squeezing everything into a single label.

---

## 8. Current practical interpretation

Given the current repo surface, a practical reading is:

- `status.json` gives the deterministic baseline
- paradox/field outputs add conflict structure when present
- the Stability Map demo expresses the intended stability-map style of thinking
- the Decision Engine gives a compact reviewer-facing summary

This means the present method layer is already useful for:

- demos
- governance prototypes
- reviewer workflows
- dashboard experiments
- design validation

while still being honest that some topology pieces remain demo/prototype-grade.

---

## 9. Recommended archive bundle

For any run where topology interpretation matters, archive together:

- `status.json`
- `report_card.html`
- `decision_engine_v0.json`, when produced
- `stability_map_v0*.json`, when produced
- `paradox_field_v0.json`, when produced
- EPF shadow artifacts, when relevant
- any reviewer-facing summary generated from the same run

This keeps the full interpretation chain reconstructible.

---

## 10. Non-goals of the methods layer

The topology methods layer should **not**:

- redefine the deterministic release contract
- hide release-policy changes inside diagnostic summaries
- require every optional overlay on every run
- treat missing diagnostics as positive evidence
- imply that a current demo tool is already a full general production method
- become a shadow control loop over the main CI path

If one of those is ever needed, it should be promoted explicitly through policy,
schema, and workflow review.

---

## 11. Summary

Topology v0 methods are best understood as an artifact-first optional method stack:

1. deterministic baseline first
2. optional paradox/stability context second
3. reviewer-facing summaries third

Today, the current repo-level tool surface supports that direction through:

- paradox field generation
- a Stability Map demo path
- and a Decision Engine that reads baseline artifacts plus optional overlays

That is already enough to support analysis, dashboards, and governance
prototyping without blurring the repository’s normative release boundary.
