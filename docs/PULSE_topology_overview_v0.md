# PULSE topology overview (v0)

High-level overview of topology v0 as the field-structural family over archived PULSE run artifacts.

This note gives the high-level picture of topology v0.

It explains:

- what topology is for,
- how Stability Map v0, the decision field, the Decision Engine, EPF-sensitive inputs, and paradox / field inputs fit together,
- how topology remains separate from release semantics.

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

## Important boundary

- release polarity is read from deterministic archived artifacts
- topology outputs remain artifact-derived
- topology outputs do not silently mutate the recorded release result
- missing signal families remain explicitly missing
- the same release polarity may correspond to different stability states

---

## Reading convention

Relations in this overview are to be read as:

- region  
- adjacency  
- boundary  
- co-occurrence  
- pressure  
- distortion  
- concentration  
- transition relations  

They are **not** to be read as simple causal arrows unless explicitly stated.

---

## References

For conceptual detail, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_epf_hook_v0.md`

For methods / pipeline details, see:

- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_v0_case_study.md`

---

# 1. What topology v0 is

Topology v0 is the broader field-structural family for reading archived PULSE run artifacts.

It preserves distinctions that flat PASS/FAIL summaries, scalar gate results, and single labels do not carry on their own.

Important preserved distinctions include:

- region membership
- boundary proximity
- adjacency between states
- local distortion
- instability / fragility
- paradox pressure
- evidence completeness

A flat deterministic result tells you what the run recorded.  
Topology tells you what kind of field configuration that recorded result occupies.

Topology is therefore not a second gate engine and not a prose-only interpretation surface.  
It is a structural read that can later be rendered in compact human or machine forms.

---

# 2. Why topology exists

The same operational release result can arise from materially different field conditions.

For example:

- a positive result can be robust or boundary-close
- a negative result can be cleanly separated or pressure-loaded
- two runs with the same polarity can differ in instability, paradox concentration, or evidence completeness

Topology exists to preserve that non-equivalence.

---

# 3. Topology family at a glance

The topology family is best read as a set of related structural roles.

### Topology v0
The broader field-structural family over archived artifacts.

### Stability Map v0
The minimal carrier for a single run’s:

- release polarity
- stability classification
- evidence completeness
- contributing signal families

### Decision field
The decision-oriented projection of topology structure for a single run.

### Decision Engine v0
A compact downstream encoding derived from archived evidence and topology-related inputs.

### Paired human / machine views
Compatible renderings of the same archived read for different consumers without changing the evidence chain.

### EPF shadow hook
A high-value boundary-sensitive and perturbation-sensitive input family for topology.

### Paradox / field outputs
Conflict-structure inputs that topology can preserve without flattening them into one gate result.

These are related roles inside one field-oriented family, not competing release authorities.

---

# 4. Core topology coordinates

A topology read is easiest to understand through three persistent coordinates.

## A. Release polarity

Release polarity is derived from deterministic archived artifacts.

Typical values:

- positive
- negative
- unknown / incomplete

This is a coarse abstraction of the deterministic release result, not a replacement for named contract states.

---

## B. Stability classification

Stability classification is derived from field-sensitive signal families.

Typical values:

- stable
- unstable / fragile
- paradox-loaded
- unknown

This coordinate preserves whether the same polarity sits in a robust, pressured, distorted, or under-observed region.

---

## C. Evidence completeness / signal availability

Topology should keep explicit track of:

- which signal families were present
- which were missing
- where the read is limited by degraded evidence

Missing inputs must remain visible as absence; they must not be silently converted into stability, calmness, or positivity.

Common materialized state families may include:

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `unknown`

These are topology encodings, not replacement release semantics.

---

# 5. What topology reads

Topology should remain artifact-derived.

Its natural inputs are archived artifacts such as:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- optional topology artifacts already materialized for the same run, such as `stability_map_v0*.json`
- `paradox_field_v0.json`, when produced
- optional EPF shadow outputs
- optional external evidence summaries
- other signal-family artifacts when materialized

This keeps topology:

- reproducible
- reviewable
- auditable
- traceable back to immutable run artifacts

It should not depend on hidden live computation that creates new release meaning.

---

# 6. Relationship to release semantics

Topology is adjacent to release semantics, but it is not the release contract.

Deterministic archived artifacts carry the recorded release result.  
Topology reads that result together with field-sensitive signals and preserves distinctions that the flat result does not carry on its own.

That means:

- topology may enrich the read
- topology may expose stability state families
- topology may support compact downstream encodings
- topology must not silently rewrite release semantics

If release behavior needs to change, that belongs in explicit contract, policy, workflow, and schema changes.

---

# 7. Relationship between the main topology components

## Stability Map v0
The Stability Map is the minimal single-run carrier of polarity + stability + completeness.

It is the smallest state form that still retains the structural distinctions topology is meant to preserve.

---

## Decision field
The decision field is the decision-oriented projection of topology.

It makes polarity, stability, pressure, distortion, and completeness legible in one compact structural read.

---

## Decision Engine v0
The Decision Engine may compress archived evidence into compact downstream labels such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`
- `UNKNOWN`

These are downstream encodings of a broader field read unless the release contract explicitly promotes them.

---

## Paired human / machine renderings

The same run may be exposed in both:

- a concise human-readable rendering
- a structured machine-readable rendering

Both should remain reconstructible from the same archived evidence.

---

# 8. Relationship to EPF shadow

EPF shadow is a high-value topology input because it exposes perturbation sensitivity and disagreement patterns near decision boundaries.

Relevant EPF contributions include:

- near-boundary flips under small perturbation
- disagreement clustering
- repeated fragility around a gate family
- local pressure near a release boundary

Valid EPF use in topology:

- distinguish robust positive from boundary-close positive
- raise instability classification when perturbation repeatedly changes outcomes
- mark pressure concentration near thresholds
- keep boundary sensitivity visible in the archived read

Invalid EPF use in topology:

- silently overrule the deterministic baseline
- reinterpret one shadow disagreement as a policy rewrite
- treat missing EPF artifacts as stability or calmness

---

# 9. Relationship to paradox / field outputs

Paradox / field outputs expose conflict structure that topology can preserve without flattening it into one gate result.

Useful preserved distinctions include:

- recurrence within a gate family
- locality versus spread of tension
- isolated versus systemic fragility
- clustering versus separation of conflict patterns
- concentration versus diffusion of paradox pressure

These outputs enrich topology when present.

Their absence must be represented as absence, not as zero tension.

---

# 10. How to read one run

A practical reading order for one run is:

1. Read the deterministic archived baseline  
   - `status.json`  
   - report card / ledger artifacts  

2. Read optional signal families  
   - EPF shadow outputs  
   - paradox / field outputs  
   - external evidence summaries  

3. Read topology projections  
   - Stability Map or related topology artifacts  
   - decision-field read  
   - compact downstream encodings  

This keeps interpretation anchored to archived artifacts rather than summary language.

---

# 11. Typical topology reads

### Stable positive
Typical pattern:

- positive polarity
- stable classification
- low boundary pressure
- no concentrated paradox structure

### Unstable positive
Typical pattern:

- positive polarity
- unstable / fragile or paradox-loaded classification
- elevated boundary sensitivity
- pressure concentration or disagreement clustering

### Stable negative
Typical pattern:

- negative polarity
- stable or low-ambiguity classification
- cleaner separation from relevant boundaries

### Unstable / paradox-loaded negative
Typical pattern:

- negative polarity
- fragility, ambiguity, or concentrated paradox pressure
- structurally stressed failure region

### Unknown
Typical pattern:

- key artifacts missing
- evidence incomplete
- signal availability degraded

Constraint:

```
unknown must not be remapped to positive by topology alone
```

---

# 12. What topology is good for

Topology is especially useful for:

- archive inspection
- dashboards
- decision-field views
- distinguishing robust from boundary-close states
- preserving field structure across repeated runs
- design validation and method prototyping
- keeping instability and paradox concentration explicit

It is **not** the right place to hide release-policy changes.

---

# 13. Non-goals

Topology v0 should not:

- replace deterministic gate evaluation
- hide release-policy changes inside topology labels
- require every signal family on every run
- treat missing diagnostics as positive evidence
- collapse the run into a single scalar or prose-only label
- become a live online control loop
- make release behavior depend on undocumented runtime state

If one of those becomes necessary, it should be introduced through explicit contract or policy changes.

---

# 14. Design invariants

A healthy topology family keeps these invariants stable:

- release polarity remains derivable from deterministic artifacts
- topology remains artifact-derived
- the same release polarity may correspond to different stability reads
- missing inputs remain explicitly missing
- missing diagnostics never imply stability or positivity
- outputs remain traceable to archived artifacts
- relation language defaults to region, adjacency, boundary, pressure, distortion, concentration, or transition relations unless explicitly marked causal
- topology language must not become an implicit release-policy rewrite
