# PULSE topology ↔ EPF hook (v0)

> Conceptual bridge between EPF shadow inputs and topology v0 as an artifact-derived field family.

This note explains how EPF shadow artifacts connect to topology v0.

It defines the hook as a structural relation between:

- deterministic archived release artifacts
- EPF shadow artifacts
- topology outputs derived from archived evidence

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

Important boundary:

- release polarity is read from deterministic archived artifacts
- EPF shadow remains a diagnostic signal family
- topology outputs remain artifact-derived
- topology outputs do not silently mutate the recorded release result
- missing EPF artifacts remain explicitly missing

Reading convention:

- relations in this note are to be read as **boundary, adjacency, co-occurrence, pressure, distortion, concentration, or transition relations**
- they are **not to be read as simple causal arrows unless explicitly stated**

For the current EPF experiment flow, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`
- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PARADOX_RUNBOOK.md`

For the broader topology picture, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_decision_field_v0_overview.md`

For methods / pipeline details, see:

- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_v0_case_study.md`

---

## 1. Why this hook exists

Deterministic run artifacts record the release result, but they do not by themselves preserve perturbation sensitivity near decision boundaries.

The same release polarity can arise from materially different local conditions.

For example, a run may be:

- robustly separated from a relevant boundary
- boundary-close under small perturbation
- locally fragile
- disagreement-clustered
- pressure-loaded around one gate family

The EPF ↔ topology hook exists so that topology can preserve that boundary-sensitive structure without silently rewriting release semantics.

---

## 2. What EPF shadow contributes

In topology terms, EPF shadow is a boundary-sensitive and perturbation-sensitive signal family.

When archived EPF artifacts are present, they may expose:

- near-threshold flips under small perturbation
- disagreement clustering
- repeated fragility around a gate family
- accumulation of local pressure near a threshold
- other instability-bearing patterns when materialized

This makes EPF valuable for topology because topology is trying to retain field structure that flat decision outputs do not carry on their own.

EPF is therefore not a second release authority.

It is a high-value input family for reading boundary pressure, fragility, and local instability.

---

## 3. What topology reads from EPF

When topology reads archived EPF artifacts, it should read them as signals about:

- boundary proximity
- perturbation sensitivity
- local instability / fragility
- pressure concentration
- disagreement clustering
- possible paradox accumulation
- evidence completeness when EPF is absent or degraded

These are structural signals.

They are not, by themselves, a replacement for deterministic release semantics.

---

## 4. The intended hook

A clean conceptual split is:

- deterministic archived artifacts carry the recorded release result
- EPF shadow artifacts expose perturbation-sensitive boundary behavior
- topology preserves the combined structural read when archived evidence is available

Within that broader topology picture:

- Stability Map v0 carries polarity + stability + completeness
- the decision field exposes a decision-oriented projection of that structure
- Decision Engine v0 may compress selected parts of that read into compact downstream labels

These are related roles over one archived evidence chain.

They are not competing release authorities.

---

## 5. Current artifact relationship

A practical artifact view of the hook is:

### 5.1 Deterministic archived artifacts

Core baseline artifacts include:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

These artifacts carry the recorded release result and the archived baseline read for the run.

### 5.2 EPF shadow artifacts

The current EPF experiment path may additionally produce artifacts such as:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

These artifacts provide perturbation-sensitive comparison context for the same run or experiment branch.

### 5.3 Topology artifacts

Topology-related artifacts may include, when produced:

- `stability_map_v0*.json`
- `paradox_field_v0.json`
- `decision_engine_v0.json`

This hook is intentionally artifact-first and conceptual.

It defines how archived EPF outputs may enrich topology reads; it does not claim that every topology component already consumes live EPF shadow outputs on every run.

---

## 6. Good topology-level uses of EPF

Valid uses of EPF shadow inside topology include:

### A. Distinguishing robust positive from boundary-close positive

A deterministic positive result may still sit close to a threshold boundary.

EPF helps topology preserve the difference between:

- a cleanly stable positive
- a technically positive but pressure-loaded positive

### B. Raising instability classification when perturbations repeatedly flip outcomes

If small perturbations repeatedly change local outcomes, topology can use that to mark:

- fragility
- instability concentration
- boundary stress

without silently changing the recorded release polarity.

### C. Contributing to paradox / tension structure

When disagreement patterns cluster in one gate family or local region, topology can preserve that as:

- paradox pressure
- recurring local tension
- concentrated instability

### D. Keeping absence explicit

If EPF artifacts are missing, degraded, or not produced for a run, topology should expose that absence rather than silently interpreting it as calmness or stability.

---

## 7. What EPF should not do inside topology

EPF should **not** be used to:

- silently overrule deterministic baseline artifacts
- convert one shadow disagreement into a policy rewrite
- remap a negative operational result to positive from shadow context alone
- remap a positive operational result to negative without explicit contract support
- treat missing EPF artifacts as stability, calmness, or positivity
- imply that topology has become a live control loop over EPF behavior

A useful check is:

if a topology output would make a reader think “this overrules the recorded deterministic release result,” the hook has become too strong.

---

## 8. Practical reading order

A practical reading order for one run is:

1. Read the deterministic archived baseline
   - `status.json`
   - report card / ledger artifacts

2. Read EPF shadow artifacts, when present
   - `status_baseline.json`
   - `status_epf.json`
   - `epf_report.txt`
   - `epf_paradox_summary.json`

3. Read other field-sensitive artifacts, when present
   - paradox / field outputs
   - external evidence summaries
   - other signal-family artifacts

4. Read topology projections
   - Stability Map artifacts
   - decision-field read
   - compact downstream encodings, when produced

This is an evidence-trace order, not a hierarchy of release authority.

It keeps interpretation anchored to archived artifacts.

---

## 9. Interpretation patterns

### Case 1 — Deterministic positive, EPF quiet

Topology may read this as:

- positive polarity
- stable classification
- low boundary pressure
- no concentrated disagreement structure

### Case 2 — Deterministic positive, EPF repeatedly disagrees

Topology may read this as:

- positive polarity
- unstable / fragile or paradox-loaded classification
- elevated boundary sensitivity
- local pressure concentration

The polarity can remain positive while the stability read changes materially.

### Case 3 — Deterministic negative, EPF differs

Topology may read this as:

- negative polarity
- boundary-sensitive or fragile negative state
- possible false-separation pressure
- need for more explicit structural interpretation

But the hook must not convert this into an automatic unblock.

### Case 4 — EPF missing or degraded

Topology should read this as:

- reduced evidence completeness
- limited boundary-sensitive visibility
- explicit absence of one signal family

It should not read this as stability.

---

## 10. Design invariants

A healthy EPF ↔ topology hook keeps these invariants stable:

- release polarity remains derivable from deterministic archived artifacts
- EPF enriches the field read rather than overwriting it
- topology remains artifact-derived
- missing EPF inputs remain explicitly missing
- missing EPF diagnostics never imply stability or positivity
- the same release polarity may correspond to different stability reads
- outputs remain traceable to archived artifacts
- relation language defaults to boundary, adjacency, pressure, distortion, concentration, or transition unless explicitly marked causal
- the hook must not become an implicit release-policy rewrite

---

## 11. Summary

The EPF ↔ topology hook is best understood as a structural bridge between:

- deterministic archived release artifacts
- EPF shadow artifacts
- topology outputs derived from archived evidence

Its job is to let topology preserve:

- boundary pressure
- perturbation sensitivity
- local fragility
- disagreement clustering
- paradox concentration
- evidence completeness

without silently changing release semantics.

EPF is therefore a high-value topology input family, not a second release authority.
