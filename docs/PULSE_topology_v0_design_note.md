# PULSE topology v0 design note

> Conceptual design note for the optional topology layer and Stability Map v0.

This note describes the **design intent** of the topology layer.

It is not the normative release contract.
It is the conceptual layer that explains how topology should sit on top of
deterministic PULSE run artifacts.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- topology is an optional diagnostic / interpretation layer
- topology outputs must not silently rewrite release semantics

For the broader overview, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_epf_hook_v0.md`

For methods / pipeline details, see:

- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_v0_case_study.md`

For the normative boundary, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

## 1. Design scope

The topology layer exists to help reviewers interpret a run beyond raw PASS/FAIL.

The core deterministic layer already answers:

- did the run pass or fail the required gates?
- what metrics were recorded?
- what does the release ledger show?

Topology adds a second kind of question:

- how stable does this run look?
- is this a clean PASS or a fragile PASS?
- where is tension / paradox pressure building?
- what reviewer posture does this run call for?

That makes topology a **review and governance design layer**.

---

## 2. Design goals

The topology layer should satisfy five goals.

### A. Stay artifact-first

Topology should be computed from archived, immutable run artifacts rather than
live hidden computation.

### B. Stay diagnostically useful

Topology should help reviewers see fragility, instability, and tension that do
not fit cleanly into a single gate boolean.

### C. Preserve the normative boundary

Topology must never silently replace the deterministic release decision.

### D. Support compact reviewer summaries

Topology should make it easier to say:

- stable_good
- unstably_good
- stable_bad
- unstably_bad
- unknown

or similar reviewer-facing state language without pretending that those labels
are themselves the source of truth for release gating.

### E. Compose with optional overlays

Topology should be able to consume optional context such as:

- EPF shadow outputs
- paradox / field overlays
- hazard-style overlays
- external evidence context

without requiring all of them to exist on every run.

---

## 3. Core idea: two-axis interpretation

A useful topology design starts from two separate axes.

### Axis 1 — Baseline release polarity

This comes from the deterministic baseline path.

Conceptually:

- positive release state
- negative release state
- unknown / incomplete

This axis is anchored to the actual baseline artifacts and gate enforcement.

### Axis 2 — Stability posture

This is diagnostic.

It asks whether the run looks:

- stable
- fragile / unstable
- paradox-prone / review-heavy
- unknown

This second axis can use optional signals such as:

- EPF shadow disagreement
- boundary sensitivity
- paradox overlays
- hazard or instability indicators

The Stability Map then combines these two axes into a reviewer-facing posture.

---

## 4. Stability Map v0 (design intent)

The Stability Map is the topology layer’s core summary projection.

Its job is to turn one run’s archived evidence into a compact stability-oriented
state that is easy to inspect and compare.

At design level, the Stability Map should answer:

1. Is the baseline run positive or negative?
2. Does the run look stable or fragile?
3. Is there enough evidence to say that honestly?
4. Is reviewer caution warranted?

This is why the Stability Map is not just another metric.
It is a **structured interpretation surface**.

---

## 5. Conceptual state families

At design level, the topology layer should support a small family of reviewer
states.

These are **conceptual state families**, not by themselves the normative release
contract.

### `stable_good`

Use when:

- the deterministic baseline is positive
- and diagnostic signals are quiet enough that the run looks robust

Interpretation:

- ordinary release confidence
- low reviewer concern

### `unstably_good`

Use when:

- the deterministic baseline is still positive
- but shadow / paradox / boundary signals suggest fragility

Interpretation:

- technically acceptable
- operationally fragile
- staging caution or reviewer attention may be appropriate

### `stable_bad`

Use when:

- the deterministic baseline is negative
- and the broader diagnostics do not suggest unusual ambiguity

Interpretation:

- the run is failing, and that failure is not merely a borderline artifact

### `unstably_bad`

Use when:

- the deterministic baseline is negative
- and diagnostic signals show instability, paradox pressure, or unresolved tension

Interpretation:

- failing and fragile
- stronger follow-up or deeper triage likely needed

### `unknown`

Use when:

- key artifacts are missing
- evidence is incomplete
- or the diagnostic context is too degraded to support an honest interpretation

Important rule:

- `unknown` must never be silently upgraded to a positive state.

---

## 6. Transition design

The design note should also define how topology states can change over time or
between runs.

### `stable_good -> unstably_good`

Typical causes:

- new EPF shadow disagreement
- repeated near-threshold fragility
- paradox / field tension appearing around a gate family

Meaning:

- the run still passes deterministically
- but reviewer confidence should drop

### `unstably_good -> stable_good`

Typical causes:

- added evaluation coverage
- reduced boundary sensitivity
- paradox / fragility signals disappearing in repeated runs

Meaning:

- the run remains positive and now also looks calmer

### `stable_bad -> unstably_bad`

Typical causes:

- new instability or paradox pressure layered onto an already failing run
- shadow disagreement suggesting the failure region is noisy or poorly understood

Meaning:

- still failing, but now harder to interpret as a simple deterministic miss

### `unstably_bad -> stable_bad`

Typical causes:

- better evidence
- reduced ambiguity
- a cleaner understanding of why the failure exists

Meaning:

- still negative, but more interpretable and less noisy

### `* -> unknown`

Typical causes:

- missing key artifacts
- broken shadow / overlay inputs
- degraded runs that cannot support an honest stability interpretation

Meaning:

- topology should surface uncertainty rather than invent confidence

---

## 7. Relationship to Decision Engine v0

The Decision Engine is a **consumer** of topology-like summaries, not the
topology layer’s replacement.

A good split is:

- Stability Map = “what posture does this run occupy?”
- Decision Engine = “how do we summarize that posture compactly for reviewers?”

This can lead to reviewer-facing outputs such as:

- `BLOCK`
- `STAGE_ONLY`
- `PROD_OK`
- `UNKNOWN`

But these outputs should remain **diagnostic summaries** unless the repository
explicitly promotes them into normative policy.

The baseline deterministic gate path remains authoritative.

---

## 8. Relationship to EPF shadow

EPF shadow is one of the most useful optional inputs to topology.

EPF helps topology ask:

- is the decision boundary fragile?
- are small perturbations flipping outcomes?
- is this run barely passing rather than comfortably passing?
- is paradox pressure accumulating around a gate family?

That is exactly why EPF belongs in topology as **context**, not as release
authority.

Good EPF use in topology:

- flag boundary pressure
- distinguish robust PASS from fragile PASS
- prioritize reviewer attention
- support governance follow-up

Bad EPF use in topology:

- silently rescuing a failing deterministic baseline
- silently rewriting release semantics from one shadow disagreement
- treating missing EPF artifacts as evidence of calm or stability

---

## 9. Relationship to paradox / field overlays

Paradox / field overlays often capture conflict structure that topology can
summarize at a higher level.

They are useful when the reviewer needs to know:

- whether tension keeps recurring in one gate family
- whether conflict is local or broad
- whether fragility is isolated or systemic

Topology should therefore treat paradox outputs as:

- optional interpretation inputs
- not as a new normative gate layer

This keeps the architecture composable.

---

## 10. Recommended output shape (conceptual)

A topology-oriented output should make it easy to answer:

- what is the baseline release posture?
- what is the stability posture?
- which signals contributed to that interpretation?
- what reviewer action, if any, is suggested?

A compact conceptual shape might therefore include:

- baseline release polarity
- stability type
- supporting signals / overlays
- a short reviewer summary
- optional recommended posture:
  - routine
  - caution
  - deeper review

This design note does not lock the exact schema.
The schema belongs in the methods/schema layer.

---

## 11. Non-goals

Topology v0 should **not** try to do the following:

- replace deterministic gating
- hide policy rewrites inside reviewer language
- require every optional overlay on every run
- turn missing diagnostics into positive evidence
- become a live online control loop
- make release semantics depend on undocumented runtime behavior

If one of those becomes necessary, it should be promoted through explicit policy
and contract changes, not quietly via topology docs.

---

## 12. Design invariants

A healthy topology design keeps these invariants stable:

- deterministic baseline remains normative
- topology remains artifact-first
- optional overlays remain optional
- missing diagnostics never become silent PASS
- reviewer-facing summaries remain reproducible from archived artifacts
- interpretation language does not become an implicit release-policy rewrite

These invariants matter more than any one label or visualization.

---

## 13. Summary

Topology v0 is best understood as:

- a **structured interpretation layer**
- over **deterministic archived run artifacts**
- with a **Stability Map** at its center
- and optional EPF / paradox context around it

Its purpose is not to decide from scratch.

Its purpose is to help reviewers distinguish:

- ordinary confidence,
- fragile confidence,
- clean failure,
- and instability-heavy failure

without blurring the repository’s normative release boundary.
