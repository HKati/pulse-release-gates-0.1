# PULSE topology v0 methods

> CLI-level methods note for topology-related diagnostic artifacts and the
> current Stability Map v0 surface.

This document explains the **current methods surface** for topology-related
artifacts in this repository.

It is intentionally method-oriented:

- which tools and artifact surfaces currently exist
- what they read
- what they emit
- and how their outputs should be read

Important boundary:

- the deterministic release path records the run outcome in archived artifacts
- topology methods are artifact-derived and diagnostic
- topology outputs do not silently rewrite release semantics or act as a second
  release authority

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

The topology family operates **on archived run artifacts**.

The central question is not:

- “how do we replace deterministic release gates?”

It is:

- “how do we preserve structural distinctions from existing deterministic
  artifacts — such as boundary proximity, instability, paradox pressure, or
  evidence incompleteness?”

That means the topology methods layer should stay focused on:

- artifact flow
- input/output contracts
- diagnostic projections and summary surfaces
- evidence-linked interpretation

---

## 2. Release-semantics boundary

The methods layer follows a reading boundary rather than a policy hierarchy:

1. **deterministic release artifacts**
   - record the run outcome and release polarity

2. **optional diagnostic artifacts**
   - EPF shadow
   - paradox / field overlays
   - external evidence context
   - hazard-style signals

3. **topology methods and outputs**
   - stability-oriented summaries
   - decision-engine style outputs
   - dual-view surfaces

If a topology output and the deterministic release artifact appear to diverge,
the role of the topology layer is to surface that divergence explicitly rather
than silently replace the recorded release outcome.

This methods note does not define a new release contract.

---

## 3. Current repo-level tool surface

The current repo-level topology surface is intentionally modest and
artifact-derived.

### 3.1 Paradox field

Tool:

```text
PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py
```

Method role:

- reads a directory of `status.json` artifacts
- derives `paradox_field_v0.json`
- summarizes paradox atoms and a severity score

Use this when you want a structured paradox/field input for later topology
interpretation.

### 3.2 Stability Map v0 (current CLI surface)

Tool:

```text
PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py
```

Current role:

- produces a demo stability-map artifact
- expresses the topology/stability idea in a minimal synthetic form
- is **not yet the same thing as a fully general multi-run production
  stability-map builder**

That distinction matters.

The current repo gives you a working demo surface for Stability Map thinking,
not a claim that the long-term topology stack is already fully generalized.

### 3.3 Decision Engine v0

Tool:

```text
PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py
```

Current method role:

- reads one required `status.json` artifact
- may also read optional overlays such as:
  - `stability_map_v0`
  - `paradox_field_v0`
- emits a compact `decision_engine_v0.json`

Typical fields include compact summary fields such as:

- `release_state`
- `stability_type`

This is a summarization surface, not a replacement for deterministic gating.

---

## 4. Minimal artifact-first pipeline

A clean topology method pipeline looks like this.

### Step 1 — Produce the deterministic run artifact

Required artifact:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

This is the anchor artifact for all later interpretation.

Without this file, topology methods should not fabricate a release reading.

### Step 2 — Optionally produce paradox / field context

Optional artifact family:

- `paradox_field_v0.json`
- related paradox / field summaries

These artifacts are useful when the run contains conflict structure, recurring
boundary tension, or evidence patterns that should be preserved explicitly
rather than flattened into PASS/FAIL.

### Step 3 — Optionally produce stability-map context

Current repo-level surface:

- a demo Stability Map generator

Method intent:

convert release polarity plus diagnostic stability context into a compact
stability-oriented representation.

Conceptually, this is where labels such as:

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `unknown`

become methodologically meaningful as structural descriptions rather than policy
classes.

The exact schema belongs to the schema/artifact layer; the methods layer cares
about how those states are derived, evidence-linked, and interpreted.

### Step 4 — Run the Decision Engine

The Decision Engine then consumes:

- the required baseline `status.json`
- optional topology/paradox/stability inputs

and emits a compact summary artifact.

Typical intent:

compress the current run into a compact read without hiding or replacing the
underlying evidence chain.

### Step 5 — Render optional dual views

The final optional step is to expose the same run in two compatible forms:

- a concise human-readable summary
- a machine-readable compact artifact

This is where the broader “Dual View” idea lives.

---

## 5. Input contracts (method view)

From a methods perspective, the topology family has one required input and
several optional diagnostic inputs.

### Required

- one deterministic `status.json` artifact

### Optional

- Stability Map artifact
- paradox / field artifact
- EPF shadow context
- external evidence context
- other diagnostic overlays that remain artifact-derived

Method rule:

optional inputs may enrich the structural read, but missing optional inputs must
never be silently reinterpreted as stability, completeness, or PASS.

---

## 6. Output contracts (method view)

Topology methods should aim to emit artifacts that answer four questions
cleanly:

1. What release polarity or outcome is recorded in the deterministic artifact chain?
2. What stability profile, uncertainty, or fragility is visible?
3. Which optional signals contributed to that interpretation?
4. Which evidence references allow the interpretation to be reconstructed?

A useful compact output therefore tends to contain:

- recorded release summary
- stability type or uncertainty state
- supporting input references
- short artifact-traceable narrative

Optional compact handling cues, when a renderer chooses to expose them, may
include:

- `routine`
- `caution`
- `deeper review`

Such cues summarize interpretation; they do **not** redefine release policy.

This is a methods rule, not a commitment to one exact renderer layout.

---

## 7. Interpretation rules

### Rule A — Anchor in archived release artifacts

Always anchor interpretation to the deterministic archived artifact chain.

### Rule B — Diagnostic context enriches rather than overrides

EPF, paradox, and other overlays can make the picture more honest or more
granular, but they do not automatically change release policy.

### Rule C — Unknown stays unknown

If key inputs are missing, degraded, or incomplete, the topology layer should
surface uncertainty explicitly rather than manufacture confidence.

### Rule D — Language must remain evidence-linked and audit-friendly

Topology output should be:

- reproducible
- explainable
- traceable back to archived artifacts

Preserving the evidence chain matters more than collapsing everything into a
single label.

---

## 8. Current practical interpretation

Given the current repo surface, a practical reading is:

- `status.json` records the deterministic release outcome
- paradox/field outputs preserve conflict structure when present
- the Stability Map demo expresses the intended stability-typing surface in
  minimal form
- the Decision Engine compresses the available artifact chain into a compact
  summary without erasing evidence links

This means the present methods layer is already useful for:

- demos
- triage workflows
- dashboard experiments
- design validation

while remaining honest that some topology surfaces are still demo/prototype
grade.

---

## 9. Recommended archive bundle

For any run where topology interpretation matters, archive together:

- `status.json`
- `report_card.html`
- `decision_engine_v0.json`, when produced
- `stability_map_v0*.json`, when produced
- `paradox_field_v0.json`, when produced
- EPF shadow artifacts, when relevant
- any human-readable summary generated from the same run

This keeps both the evidence chain and the interpretation chain
reconstructible.

---

## 10. Non-goals of the methods layer

The topology methods layer should not:

- redefine the deterministic release contract
- hide release-policy changes inside diagnostic summaries
- require every optional overlay on every run
- treat missing diagnostics as positive evidence
- imply that a current demo surface is already a fully general production
  method
- function as a hidden second release path or shadow control loop over the main
  CI path

If one of those is ever needed, it should be promoted explicitly through
schema, workflow, and policy review.

---

## 11. Summary

Topology v0 methods are best understood as an artifact-derived diagnostic stack:

- archived deterministic artifacts record the release outcome
- optional paradox / EPF / stability context preserves structural distinctions
  that PASS/FAIL would flatten away
- compact summary surfaces expose that structure without rewriting release
  semantics

Today, the current repo-level tool surface supports that direction through:

- paradox field generation
- a Stability Map demo path
- a Decision Engine that reads baseline artifacts plus optional overlays

That is already enough to support analysis, triage, dashboards, and method
validation without blurring the repository’s release boundary.
