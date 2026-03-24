# PULSE decision field overview (v0)

> High-level overview of the decision-field layer inside topology v0.

This note defines the decision field as a decision-oriented, field-structural projection over archived PULSE run artifacts.

It makes decision-relevant structure legible without flattening a run to bare PASS/FAIL and without silently rewriting the deterministic release result.

It does not define release semantics. Release semantics are specified in:

* `docs/STATE_v0.md`
* `docs/status_json.md`
* `docs/STATUS_CONTRACT.md`

Important boundary:

* release polarity is read from deterministic archived artifacts;
* decision-field outputs remain artifact-derived;
* decision-field outputs do not silently mutate the recorded release result;
* missing signal families remain explicitly missing.

For the broader topology picture, see:

* `docs/PULSE_topology_overview_v0.md`
* `docs/PULSE_topology_v0_design_note.md`
* `docs/PULSE_topology_epf_hook_v0.md`

For methods / pipeline details, see:

* `docs/PULSE_topology_v0_methods.md`
* `docs/PULSE_topology_v0_case_study.md`

---

## 1. What the decision field is

The decision field is a decision-oriented read of the topology surface for a single archived run.

Its purpose is not to decide from scratch and not to replace deterministic gate evaluation.

Its purpose is to preserve decision-relevant structure that a flat deterministic result does not carry on its own, including:

* release polarity
* stability classification
* boundary proximity
* local pressure or distortion
* evidence completeness
* concentration of instability or paradox structure

Downstream renderers may summarize this read for humans or tools, but the decision field itself is the structural projection, not the summary wording.

---

## 2. Why it exists

The same deterministic release result can arise from materially different field conditions.

A run may be:

* clearly separated from relevant boundaries,
* boundary-close under perturbation,
* locally unstable,
* paradox-loaded,
* or only partially observed because key signal families are missing.

Those distinctions matter for honest interpretation, archive reading, and downstream compact encodings.

The decision field exists to preserve those distinctions in decision-oriented form.

---

## 3. Core decision-field coordinates

The decision field is easiest to read as a compact structural projection with three persistent components.

### A. Release polarity

Release polarity is derived from deterministic archived artifacts.

Typical values:

* positive
* negative
* unknown / incomplete

Release polarity is a coarse abstraction of the deterministic release result, not a replacement for named contract states.

### B. Stability classification

Stability classification is derived from field-sensitive signal families.

Typical values:

* stable
* unstable / fragile
* paradox-loaded
* unknown

This classification tells you whether the same polarity sits in a robust, pressured, distorted, or under-observed region.

### C. Evidence completeness / signal availability

A decision-field read should keep explicit track of:

* which signal families were present,
* which were missing,
* and where the read is limited by degraded evidence.

Missing inputs must remain visible as absence; they must not be silently converted into stability, calmness, or positivity.

---

## 4. Relationship to topology

The decision field belongs to the broader topology family.

A clean conceptual split is:

* topology v0 = the broader field-structural family
* Stability Map v0 = the minimal carrier of polarity + stability + completeness
* decision field = the decision-oriented projection of that structure
* Decision Engine v0 = a compact downstream encoding derived from archived evidence

These are related roles, not competing release authorities.

The decision field therefore sits inside the topology picture as the place where structural distinctions become legible in decision-relevant coordinates.

---

## 5. What the decision field reads

The decision field should remain artifact-derived.

Its natural inputs are archived artifacts such as:

* `PULSE_safe_pack_v0/artifacts/status.json`
* `PULSE_safe_pack_v0/artifacts/report_card.html`
* `stability_map_v0*.json`, when produced
* `paradox_field_v0.json`, when produced
* optional EPF shadow outputs
* optional external evidence summaries

This keeps the decision-field read:

* reproducible,
* reviewable,
* auditable,
* and traceable back to immutable run artifacts.

It should not depend on hidden live computation that creates new release meaning.

---

## 6. What the decision field tries to express

The decision field is useful when bare PASS/FAIL is not enough.

Typical questions include:

* is this positive result robust or boundary-close?
* is this negative result cleanly separated or pressure-loaded?
* is instability local or concentrated?
* is paradox structure isolated or recurring?
* is the read materially limited by missing evidence?

That means the decision field is less about narrative posture and more about preserving a structurally honest decision read.

When materialized, this may align with state families such as:

* `stable_good`
* `unstably_good`
* `stable_bad`
* `unstably_bad`
* `unknown`

Those are field encodings, not replacement release semantics.

---

## 7. Relationship to the Decision Engine

A decision field is richer than a single compact label, but it pairs naturally with Decision Engine v0.

For example, a Decision Engine may compress archived evidence into labels such as:

* `BLOCK`
* `STAGE_ONLY`
* `PROD_OK`
* `UNKNOWN`

Those labels are downstream encodings of a broader field read.

Unless explicitly promoted through the release contract, they do not redefine release semantics.

A useful rule is:

* the decision field preserves structure;
* the Decision Engine compresses selected parts of that structure for downstream use.

---

## 8. Relationship to EPF shadow

EPF shadow is a high-value input to the decision field because it exposes boundary sensitivity and perturbation behavior near decision thresholds.

Relevant EPF contributions include:

* near-boundary flips under small perturbation
* disagreement clustering
* repeated fragility around a gate family
* local pressure near a release boundary

Valid EPF use in the decision field:

* distinguish robust positive from boundary-close positive
* raise instability classification when perturbation repeatedly changes outcomes
* mark pressure concentration near a threshold
* keep boundary sensitivity visible in the archived read

Invalid EPF use in the decision field:

* silently overrule the deterministic baseline
* reinterpret one shadow disagreement as a policy rewrite
* treat missing EPF artifacts as stability or calmness

---

## 9. Relationship to paradox / field outputs

Paradox / field outputs expose conflict structure that the decision field can preserve in decision-oriented form.

Useful preserved distinctions include:

* recurrence within a gate family
* locality versus spread of tension
* isolated versus systemic fragility
* clustering versus separation of conflict patterns

These outputs enrich the decision-field read when present.

Their absence must be represented as absence, not as zero tension.

---

## 10. Typical interpretation patterns

### Case A — Deterministic positive result, quiet diagnostics

A decision-field read may show:

* positive polarity
* stable classification
* low boundary pressure
* no concentrated paradox structure

### Case B — Deterministic positive result, noisy diagnostics

A decision-field read may show:

* positive polarity
* unstable / fragile or paradox-loaded classification
* elevated boundary sensitivity
* pressure concentration or disagreement clustering

The polarity can stay positive while the stability read changes materially.

### Case C — Deterministic negative result, cleaner separation

A decision-field read may show:

* negative polarity
* stable or low-ambiguity classification
* limited boundary pressure
* no material paradox concentration

### Case D — Repeated disagreement in one gate family

A decision-field read may keep the same polarity while surfacing:

* recurrent local instability
* low separation around a threshold
* concentrated paradox pressure
* evidence that the same region remains structurally stressed

---

## 11. Recommended reading order

A practical reading order for one run is:

1. Read the deterministic archived baseline

   * `status.json`
   * report card / ledger artifacts

2. Read optional signal families

   * EPF shadow outputs
   * paradox / field outputs
   * external evidence summaries, when present

3. Read the decision-field projection

   * polarity
   * stability classification
   * completeness markers
   * boundary / paradox / instability markers

This keeps the decision-field interpretation anchored to archived evidence.

---

## 12. Non-goals

The decision field should not:

* replace deterministic gate evaluation
* hide release-policy changes inside topology language
* require every signal family on every run
* treat missing diagnostics as positive evidence
* collapse the run into a single prose-only summary
* become a live online control loop
* make release behavior depend on undocumented runtime state

If one of those becomes necessary, it should be introduced through explicit contract or policy changes.

---

## 13. Design invariants

A healthy decision-field layer keeps these invariants stable:

* release polarity remains derivable from deterministic artifacts
* the decision field remains artifact-derived
* the same release polarity may correspond to different stability reads
* missing inputs remain explicitly missing
* missing diagnostics never imply stability or positivity
* outputs remain traceable to archived artifacts
* relation language defaults to boundary, adjacency, pressure, distortion, concentration, or transition unless explicitly marked causal
* decision-field language must not become an implicit release-policy rewrite

---

## 14. Summary

The decision field is a decision-oriented, field-structural projection over archived PULSE artifacts.

It exists to preserve decision-relevant distinctions that a flat deterministic result loses, especially:

* polarity
* stability
* completeness
* boundary pressure
* instability concentration
* paradox structure

It remains artifact-derived, reproducible from archived evidence, and separate from the release-semantics contract.
