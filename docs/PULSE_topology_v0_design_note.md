# PULSE topology v0 design note

Conceptual design note for topology v0 and Stability Map v0.

This note defines topology v0 as a structural, field-oriented read over archived PULSE run artifacts.

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

Topology is derived from the same archived artifacts and must not silently mutate the operational release result recorded by the deterministic run path.

Reading convention:

- relations in this note are to be read as **region, adjacency, boundary, co-occurrence, pressure, distortion, or transition relations**
- they are **not to be read as simple causal arrows unless explicitly stated**

For the broader overview, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_epf_hook_v0.md`

For methods / pipeline details, see:

- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_v0_case_study.md`

For the release-semantics boundary, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

# 1. Design scope

Topology v0 preserves field structure that flat PASS/FAIL summaries and scalar gate results do not carry.

The topology component is used to retain and expose:

- region membership  
- boundary proximity  
- adjacency between states  
- local distortion  
- instability / fragility  
- recurring paradox pressure or tension concentration  

The deterministic run path already records gate outcomes, measured values, and release artifacts. Topology does not replace that record. It preserves structural distinctions within the same evidence.

Topology is introduced because the same operational release result can arise from materially different field configurations. A flat decision result does not preserve whether a run is boundary-close, locally distorted, paradox-loaded, or unstable under nearby perturbation.

---

# 2. Design goals

Topology v0 should satisfy the following goals.

### A. Stay artifact-derived

Topology must be derivable from archived, immutable run artifacts rather than hidden live computation.

### B. Preserve field distinctions

Topology must retain distinctions that are lost in flat decision summaries, including:

- region  
- boundary  
- adjacency  
- distortion  
- instability  
- concentrated paradox pressure  

### C. Preserve release semantics

Topology must not silently change the operational release result recorded by the deterministic run path.

### D. Support stability classification

Topology may expose:

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `unknown`

or equivalent state families, provided that those state families remain reproducible from archived artifacts and do not replace the underlying signal structure.

### E. Compose with non-uniform signal families

Topology should be able to consume:

- EPF shadow outputs  
- paradox / field outputs  
- hazard-style signals  
- external evidence  

when present, without assuming uniform availability across runs.

---

# 3. Core structure: two-axis map

A topology read is organized along two axes.

### Axis 1 — Release polarity

This axis is derived from deterministic run artifacts.

Possible values:

- positive  
- negative  
- unknown / incomplete  

This axis records the operational release result carried by archived artifacts.

---

### Axis 2 — Stability classification

This axis is derived from field-sensitive signals.

Possible values:

- stable  
- unstable / fragile  
- paradox-loaded  
- unknown  

Signals may include:

- EPF shadow disagreement  
- boundary sensitivity  
- paradox signals  
- hazard or instability indicators  

The same release polarity can correspond to different stability classifications.  
Topology exists to preserve that non-equivalence.

The Stability Map stores the pairing of these axes together with contributing signals and evidence completeness.

---

# 4. Stability Map v0

Stability Map v0 is the minimal topology carrier for a single run.

At minimum, it must preserve:

- release polarity  
- stability classification  
- evidence completeness  
- contributing signal families  
- boundary / paradox / instability markers when present  

It is not a scalar confidence score and not a narrative summary.  
It is the smallest state form that still retains the structural distinctions topology is meant to preserve.

---

# 5. Conceptual state families

Topology v0 should support the following state families as pairings of release polarity and stability classification.

These state families are **not the release contract**.

---

### stable_good

Minimal condition set:

- release polarity = positive  
- stability classification = stable  

Typical signal pattern:

- low boundary sensitivity  
- no material EPF disagreement  
- no concentrated paradox pressure  

---

### unstably_good

Minimal condition set:

- release polarity = positive  
- stability classification = unstable / fragile  

Typical signal pattern:

- near-threshold behavior  
- elevated boundary sensitivity  
- EPF disagreement, paradox pressure, or both  

---

### stable_bad

Minimal condition set:

- release polarity = negative  
- stability classification = stable  

Typical signal pattern:

- negative result without elevated ambiguity or instability  

---

### unstably_bad

Minimal condition set:

- release polarity = negative  
- stability classification = unstable / fragile or paradox-loaded  

Typical signal pattern:

- negative result with instability, ambiguity, or concentrated paradox pressure  

---

### unknown

Minimal condition set:

- key artifacts missing  
- evidence incomplete  
- signal availability degraded  

Constraint:

```
unknown must not be remapped to positive by topology alone
```

---

# 6. Transition design

Transition labels describe changes between runs or re-evaluations with different evidence.  
They do not justify silent reinterpretation of a fixed artifact set.

---

### stable_good → unstably_good

Typical causes:

- new EPF shadow disagreement  
- repeated near-threshold sensitivity  
- emerging local paradox pressure  

Invariant:

- release polarity remains positive  
- stability classification changes from stable to fragile  

---

### unstably_good → stable_good

Typical causes:

- added evidence coverage  
- reduced boundary sensitivity  
- disappearance of instability or paradox signals across repeated runs  

Invariant:

- release polarity remains positive  
- stability classification changes from fragile to stable  

---

### stable_bad → unstably_bad

Typical causes:

- new instability or paradox pressure added to an already negative run  
- shadow disagreement indicating a noisy or weakly separated failure region  

Invariant:

- release polarity remains negative  
- stability classification changes from stable to fragile or paradox-loaded  

---

### unstably_bad → stable_bad

Typical causes:

- improved evidence completeness  
- reduced ambiguity  
- cleaner separation of the negative region  

Invariant:

- release polarity remains negative  
- stability classification changes from fragile or paradox-loaded to stable  

---

### * → unknown

Typical causes:

- missing key artifacts  
- broken signal inputs  
- degraded evidence completeness  

Invariant:

- topology surfaces absence rather than inventing stability or confidence  

---

# 7. Relationship to Decision Engine v0

Topology and Decision Engine v0 are distinct components.

Topology produces a **structural state description from archived artifacts**.

Decision Engine v0 may consume that state description and project it to compact operational labels such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`
- `UNKNOWN`

Unless explicitly specified in:

- `STATE_v0.md`
- `status_json.md`
- `STATUS_CONTRACT.md`

those downstream labels **do not redefine release semantics**.

---

# 8. Relationship to EPF shadow

EPF shadow is a high-value topology input because it exposes perturbation sensitivity and disagreement patterns near decision boundaries.

Relevant EPF contributions include:

- boundary pressure  
- near-boundary flips under small perturbation  
- disagreement clustering  
- accumulation of instability around a gate family  

Valid EPF use in topology:

- mark boundary pressure  
- separate robust positive from boundary-close positive  
- increase instability classification when repeated perturbations flip outcomes  
- contribute to paradox / tension accumulation when disagreement clusters  

Invalid EPF use in topology:

- remap a negative operational result to positive from a single shadow disagreement  
- remap a positive operational result to negative without explicit contract support  
- treat missing EPF artifacts as calmness or stability  

---

# 9. Relationship to paradox / field outputs

Paradox / field outputs expose conflict structure that topology can preserve without flattening it into one gate result.

Useful preserved distinctions include:

- recurrence within a gate family  
- locality versus spread of tension  
- isolated versus systemic fragility  
- clustering versus separation of conflict patterns  

Topology may ingest these outputs when available.  
Their absence must be represented as absence, not as zero tension.

Paradox / field outputs are signal families for topology.  
They do not by themselves create undocumented release semantics.

---

# 10. Recommended output shape

A topology output should expose, at minimum:

- release polarity  
- stability classification  
- evidence completeness  
- contributing signal families  
- missing-input markers  
- boundary / paradox / instability markers when present  
- derived state family, if materialized  

This design note does **not lock the exact schema**.  
The exact schema belongs in the **methods / schema layer**.

---

# 11. Non-goals

Topology v0 should **not** try to do the following:

- replace deterministic gate evaluation  
- hide release-semantic changes inside topology labels  
- require every signal family on every run  
- interpret missing diagnostics as stability, calmness, or positivity  
- collapse topology into a single scalar or compact narrative label  
- become a live online control loop  
- make release behavior depend on undocumented runtime state  

If any of those become necessary, they must be introduced through **explicit contract or policy changes** rather than through topology text.

---

# 12. Design invariants

A healthy topology design keeps these invariants stable:

- release polarity remains derivable from deterministic artifacts and is not mutated by topology  
- topology remains artifact-derived  
- relation language defaults to adjacency, co-occurrence, pressure, distortion, or transition unless explicitly marked causal  
- missing inputs remain explicitly missing  
- missing diagnostics never imply stability or positivity  
- the same release polarity may correspond to different stability classifications, and topology must preserve that distinction  
- topology states remain reproducible from archived artifacts  
- topology language must not become an implicit release-policy rewrite  

---

# 13. Summary

Topology v0 is a **field-structural read over archived PULSE artifacts**.

Its central carrier is the **Stability Map**, which pairs:

- release polarity  
- stability classification  
- contributing signals  

It exists to preserve distinctions that flat decision outputs lose, especially:

- region  
- boundary  
- adjacency  
- distortion  
- instability  
- paradox pressure  

It does **not redefine release semantics**, and it must remain reproducible from archived evidence.

---

# Commit / PR / merge szöveg ehhez az első körhöz

## Commit title

```
docs(topology): restore engineering detail in design note
```

## Commit body

```
restore field-structural topology mechanics

remove narrative, reviewer, and governance framing

keep release-semantics boundary explicit without hierarchy language

preserve valid references and scope boundaries
```

## PR title

```
Restore engineering detail in PULSE_topology_v0_design_note.md
```

## PR body

```
Why: The file drifted from field-structural engineering content toward narrative and flattening language.

Restored: topology as a structural read over archived artifacts; region, boundary, adjacency, distortion, instability, and paradox-pressure handling.

Removed: source-of-truth wording, reviewer/governance framing, compact-summary language, and other flattening phrases.

Preserved: release-semantics boundary, cross-references, and current file scope.

Not in scope: new language-problem element, repo-wide terminology pass, unrelated docs.
```
