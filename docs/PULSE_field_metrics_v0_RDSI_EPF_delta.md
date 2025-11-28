# PULSE Field Metrics v0 – RDSI, EPF tension, Δ-direction error

This document describes a first, conceptual version of **field-level
metrics** used in the PULSE Decision Field v0 layer:

- **RDSI** – Release Decision Stability Index
- **EPF tension** – Evaluation / Paradox Frontier “shadow field” tension
- **Δ-direction error** – directional drift away from a stable field state
- **meta-state** – a compact label for the field regime

These metrics are intended as a **future-facing library** for
Decision Field v0 and beyond. They are not yet fully standardised or
implemented across all tools, but serve as a target vocabulary for
field-level stability.

---

## 1. Design goals

Traditional metrics answer questions like:

- “How accurate is the model?”
- “Did this release pass the gates?”

Field-level metrics answer deeper questions:

- “How **stable** is this decision region?”
- “How much **tension** is there between the constraints?”
- “Is the system trying to **escape** the region by drifting toward one
  side of a paradox?”
- “Does the system recognise that it is in a **special field regime**?”

PULSE field metrics are designed to:

1. Be **portable** across different evaluation setups.
2. Align with existing Decision Field v0 artefacts:
   - `status.json`
   - `paradox_field_v0.json`
   - `stability_map_v0`
   - `decision_engine_v0.json`
   - `decision_trace_v0`
3. Expose **structure** (paradox, curvature, direction) rather than
   a single scalar score.

---

## 2. RDSI – Release Decision Stability Index

### 2.1. Intuition

RDSI is a scalar in `[0, 1]` that measures how **stable** a release
decision is under small perturbations:

- input variations (data shifts, seeds),
- config / threshold variations,
- sampling variations.

Rough intuition:

- `RDSI ≈ 1.0`  
  → decisions are very stable across perturbations.
- `RDSI ≈ 0.0`  
  → decisions frequently change (flip gates, flip release_state, etc.).

In Pulse Demo v1, an RDSI of `0.91` is used as an example of a **stable
paradox region**: the system recognises the paradox and consistently
maps it to a stable field state (e.g. “paradox-state / stabilised”).

### 2.2. Conceptual definition

Given a set of runs `{r₁, r₂, …, rₙ}` for the same release candidate,
each with:

- a `status.json`,
- and optionally a `decision_engine_v0` overlay,

we can say, informally:

- “stable” if:
  - the **effective decision** (e.g. release_state, and possibly the
    relevant stability_type) does not change across the runs,
- “unstable” if:
  - there are flips between key decision labels across the runs.

RDSI then measures the fraction of stability across such runs, possibly
weighted by:

- the importance of certain gates,
- the severity of flips (e.g. PROD_OK → BLOCK vs PROD_OK → STAGE_ONLY).

This document does **not** prescribe a single formula, but frames RDSI
as:

> a field-level stability index that answers  
> “how often does the decision survive small shocks?”

---

## 3. EPF tension – shadow field tension around the decision

### 3.1. Intuition

EPF (Evaluation / Paradox Frontier) tension measures how much
**latent conflict** exists in the neighbourhood of a decision, even when
the final outcome looks “clean”.

Sources of tension include:

- paradox atoms in `paradox_field_v0`,
- high curvature in `stability_map_v0`,
- borderline gate configurations in `status.json`.

High EPF tension means:

- the local field is “hot”:
  - nearby conditions would easily produce paradoxes or flips,
  - multiple constraints are pulling in different directions.

Low EPF tension means:

- the local field is “cool”:
  - constraints are mostly aligned,
  - small changes do not create strong conflicts.

### 3.2. Conceptual components

EPF tension can be thought of as a function of:

- paradox structure:
  - number of atoms,
  - severity of atoms,
  - overlap between atoms and gates relevant for this release;
- curvature structure:
  - `delta_bend` values in nearby stability cells;
- proximity to boundaries:
  - how close gates are to their thresholds,
  - how often “near-miss” behaviours appear in traces.

A stylised view:

- `EPF_tension ≈ f(paradox_density, curvature, boundary_proximity)`

In the Demo v1 narrative, a **low EPF tension** is part of the picture
for a “stabilised paradox state”:

> “the field around the paradox does not overheat; the paradox is
> acknowledged and contained in a dedicated region.”

---

## 4. Δ-direction error – escape drift from a stable state

### 4.1. Intuition

Δ-direction error measures:

> “How much is the system trying to **run away** from a stabilised
> field state in a problematic direction?”

For paradox regions, a “direction” might be:

- “leaning toward true” vs “leaning toward false”,
- “leaning toward SLO” vs “leaning toward fairness”,
- “leaning toward speed” vs “leaning toward safety”.

A low Δ-direction error means:

- the system is genuinely **holding** the paradox / tradeoff as a
  stable state, rather than collapsing it to one side.

A high Δ-direction error suggests:

- the system is internally biased:
  - its trajectories in decision space tend to move away from the
    symmetric point,
  - even if the final output looks balanced.

### 4.2. Conceptual definition

Consider a local neighbourhood in the decision field defined by:

- a central configuration (e.g. baseline thresholds / conditions),
- small perturbations along interpretable axes:
  - e.g. fairness_threshold ± ε, SLO_budget ± ε, etc.

Δ-direction error is conceptually:

- the **vector of drifts** in decision outcomes as we move along these
  axes, summarised into a scalar:

  - how asymmetric the drifts are,
  - how far they move us from the “neutral” point.

In a paradox region:

- if the model repeatedly attempts to collapse to one side
  (“always push toward SLO at the expense of fairness”),  
  Δ-direction error is high.

- if the model recognises the paradox as a legitimate state and
  resists collapsing,  
  Δ-direction error is low.

In Demo v1, `Δ-direction error = 0.03` is used to illustrate:

- an almost neutral, paradox-aware equilibrium.

---

## 5. Meta-state – labelling the field regime

Beyond scalar metrics, it is useful to have a compact **meta-state**
label, e.g.:

- `"stable_field"`
- `"paradox_field_stabilised"`
- `"paradox_field_unstable"`
- `"boundary_region"`
- `"unknown_field_state"`

This meta-state:

- is not a replacement for the metrics,
- but a **human-facing label** that summarises the field regime.

It can be derived from:

- the presence/absence of paradox atoms,
- curvature patterns,
- RDSI and EPF levels,
- Δ-direction error.

For example, a regime with:

- high RDSI,
- non-zero paradox structure,
- low EPF tension,
- low Δ-direction error,

could be described as:

> `"paradox_field_stabilised"`.

---

## 6. Relation to Decision Field v0 artefacts

Field metrics do not live in isolation. They are designed to align with:

- `status.json`
  - base layer: gates and metrics,
- `paradox_field_v0.json`
  - structural paradox information,
- `stability_map_v0`
  - curvature / Δ-bend across local regions,
- `decision_engine_v0.json`
  - `release_state` and `stability_type` as coarse labels,
- `decision_trace_v0`
  - stepwise evolution of the decision.

A typical usage might be:

- store RDSI, EPF tension, Δ-direction error and meta-state in:
  - a field metrics overlay, or
  - extended summaries inside `decision_engine_v0`, or
  - derived views / dashboards.

This document does not fix where these metrics must be stored, only how
they are conceptually **connected** to the existing field artefacts.

---

## 7. Implementation notes

- This is a **v0 conceptual spec**, not a final standard:
  - precise formulas and storage formats are deliberately left open,
  - different teams may start with different approximations.

- Field metrics should be:
  - computed from **ensembles** of runs / perturbations,
  - sensitive to structural patterns (paradox, curvature),
  - interpretable by both humans and tooling.

- It is recommended to:
  - log enough context to reconstruct how the metric was computed,
  - keep metrics stable over time, or version them clearly when
    definitions change.

---

## 8. Summary

PULSE field metrics extend the Decision Field v0 layer by adding:

- **RDSI** – “How stable is this decision across shocks?”
- **EPF tension** – “How much conflict lives around this decision?”
- **Δ-direction error** – “Is the system trying to escape the stable state?”
- **meta-state** – “What kind of field regime are we in?”

Together, they move metrics beyond “how good is the model?” toward:

> “How stable, tense, and self-aware is the decision field in which
> this release lives?”
