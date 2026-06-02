# PULSE Mechanical AI v0 — Decision-Field Terminology Note

## Purpose

This document defines **Mechanical AI (M-AI)** as project terminology for PULSE decision-field artifacts.

The term is used to describe an artifact-level representation of decisions, constraints, paradox structures, and stability diagnostics.

It does not describe:

```text
biological cognition
human-like understanding
consciousness
AGI capability
model-internal reasoning
model-training behavior
```

Mechanical AI, in this document, refers to a PULSE-style decision-field representation built from explicit artifacts.

The purpose is to define terminology without implying that PULSE imitates humans, trains a model, or claims cognitive capability.

## Boundary

Mechanical AI is a terminology layer.

It is not a separate release-authority path.

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Mechanical AI terminology may describe how PULSE artifacts represent decision fields, paradox constraints, stability signals, and trace structure.

It does not redefine release authority.

## 1. Training-loop View vs Decision-Field Artifact View

### 1.1 Training-loop view

In a classical model-training view, the central process is an optimization loop:

```text
data
→ loss
→ gradient
→ parameter update
```

This process is repeated to improve task performance under a selected objective.

Growth in this view may involve:

```text
more data
more parameters
more compute
more training steps
more layers
```

This is quantitative growth inside a training system.

### 1.2 Decision-field artifact view

Mechanical AI, as used in PULSE, does not refer to training a model.

It refers to a decision-field artifact view.

The central object is:

```text
a represented field of possible decisions
```

rather than:

```text
a learner model
```

The review question changes from:

```text
What did the model learn?
```

to:

```text
What decision field is represented by the recorded artifacts?
```

A PULSE decision-field artifact may describe:

```text
gate states
constraint relations
paradox structures
stability regions
directional drift
release-state boundaries
```

This is a structural artifact view.

It does not assert that the underlying model understands, reasons, or learns in a biological sense.

## 2. Paradox as a Field-Extension Trigger

### 2.1 Closed optimization view

In a closed optimization view, an error is typically handled as:

```text
error
→ correction
→ better fit under the same objective
```

The system moves inside a predefined task and objective space.

### 2.2 PULSE decision-field view

In a decision-field representation, a paradox is represented as a field-extension trigger.

A paradox-oriented structure may include:

```text
two constraints that cannot be jointly satisfied
a minimal unsatisfiable set or MUS-like structure
a local region where a binary decision surface is not stable
a point where the represented field cannot remain flat
```

In PULSE artifacts, paradox structure may be represented through:

```text
paradox_field_v0.json
```

where each recorded atom describes a local paradox / constraint structure.

Mechanically, a paradox artifact may:

```text
mark a local field-extension point
identify a structurally tense decision region
record a constraint re-organization requirement
prevent the case from being flattened into a single binary label
```

This is not model learning.

It is artifact-level representation around paradox constraints.

## 3. From Reward Reading to Stability Diagnostics

### 3.1 Reward-centric reading

In many ML systems, one central object is a reward or loss function:

```text
better outcome
→ lower loss or higher reward
```

This is effective for training, but it can hide structural tensions inside a single scalar.

Examples of hidden tension:

```text
trade-offs inside one reward score
unstable behavior under small perturbations
green-looking outputs with fragile decision surfaces
conflicting constraints that are not visible in the scalar
```

### 3.2 Stability-diagnostic reading

PULSE uses a different inspection object.

Instead of asking only:

```text
How good is this run?
```

PULSE can also ask:

```text
How stable is the represented decision field around this run?
```

Relevant artifacts may include:

```text
status.json
paradox_field_v0.json
stability_map_v0.json
decision_engine_v0.json
decision_trace_v0.json
```

Relevant diagnostic signals may include:

```text
RDSI
stability_type
Δ-direction error
EPF shadow / tension signal
```

This terminology does not claim to replace reward functions in model training.

It describes a PULSE artifact view where stability diagnostics are explicit and inspectable.

## 4. What Mechanical AI Means in PULSE

Mechanical AI in PULSE means:

```text
decision artifacts are represented as field structures
constraints are made explicit
paradox structures are recorded as field-extension points
stability diagnostics are exposed as artifacts
decision traces are inspectable
```

Mechanical AI in PULSE does not mean:

```text
human-like cognition
biological intelligence
AGI capability
semantic understanding claim
model-internal consciousness
model-training method
```

A concise project definition:

```text
Mechanical AI (M-AI) is a PULSE terminology layer for artifact-bound decision-field representation.

It records constraints, paradox structures, stability diagnostics, and decision traces without making biological, cognitive, or AGI claims.
```

A compact contrast:

```text
training loop
= updates model parameters under an objective

PULSE decision-field representation
= records and inspects decision artifacts, constraint relations, paradox structures, and stability diagnostics
```

## 5. PULSE as a Mechanical AI Artifact Stack

PULSE instantiates Mechanical AI terminology through artifact layers.

These layers are inspectable and deterministic at the artifact level.

### 5.1 Gates and status artifacts

Primary artifact:

```text
status.json
```

`status.json` represents a run through recorded fields such as:

```text
gates
metrics
diagnostics
metadata / traceability fields
```

Gate values encode structural constraints and recorded check outcomes.

The PULSE release-authority path does not rely on narrative confidence.

It relies on recorded gate state, declared policy, materialized required gates, and fail-closed enforcement.

### 5.2 Paradox field

Optional / diagnostic artifact:

```text
paradox_field_v0.json
```

A paradox field records paradox atoms or constraint structures.

A paradox atom may represent:

```text
a local incompatibility
a minimal unsatisfiable set or MUS-like structure
a field region where a simple binary state is insufficient
```

This artifact is diagnostic unless promoted through declared policy and required-gate enforcement.

### 5.3 Stability map

Optional / diagnostic artifact:

```text
stability_map_v0.json
```

A stability map may record:

```text
curvature
Δ-bend
local robustness
decision-flip regions
perturbation sensitivity
```

It helps identify where the represented decision field is:

```text
flat or curved
stable or unstable
robust or fragile
monotone or oscillating
```

This is a diagnostic representation.

It does not become release authority unless explicitly folded into recorded evidence and enforced as a required gate under declared policy.

### 5.4 Decision engine and trace artifacts

Possible decision-field artifacts:

```text
decision_engine_v0.json
decision_trace_v0.json
```

These may summarize:

```text
release_state
stability_type
RDSI
field diagnostics
trace from gates to decision
```

A decision trace records how a decision representation was derived from recorded artifacts.

A trace carrier does not become a second decision engine unless explicitly declared and enforced.

## 6. Mechanical Decision Field

Together, PULSE artifacts can form a mechanical decision field:

```text
recorded gates
+ declared policy
+ materialized required gate set
+ paradox / stability overlays
+ decision trace
+ public reader artifacts
+ provenance / binding artifacts
```

The normative release-authority path remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Other artifacts may review, explain, bind, attest, or diagnose the path.

They do not replace it.

## 7. Why This Matters for AI Safety and Release Authority

Mechanical AI terminology is relevant because it separates:

```text
underlying model behavior
```

from:

```text
release-decision mechanics
```

PULSE does not need to claim that it understands the model internally.

PULSE records the release decision path externally through artifacts.

This allows review of:

```text
which gates passed
which gates failed
which required gates were materialized
which evidence was present
which paradox / stability regions were observed
which artifact relationship was bound
which attestation subject was used
```

This is useful for AI safety and release authority because it makes the release boundary inspectable.

## 8. Diagnostic Coordinate Shift

PULSE does not solve alignment by itself.

Mechanical AI terminology describes a diagnostic coordinate shift:

```text
from reward-only reading
to stability-diagnostic reading

from opaque confidence
to recorded decision traces

from implicit shadow signals
to explicit carrier roles

from narrative assurance
to artifact-bound evidence
```

This shift supports release-authority review.

It does not replace runtime safety, model evaluation, external validation, or independent audit.

## 9. Carrier Boundary

Mechanical AI artifacts may occupy different carrier roles.

| Carrier | Role |
|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement |
| Reader carrier | Presents recorded state |
| Trace carrier | Preserves reconstruction trace |
| Diagnostic / shadow carrier | Records candidate evidence or field diagnostics |
| Binding carrier | Carries digest-backed artifact relation |
| Attestation carrier | Attests the binding carrier |
| External verification carrier | Reviews the recorded artifact relationship |

A Mechanical AI artifact is not authority merely because it is structured, diagnostic, or machine-readable.

Authority participation requires:

```text
recorded evidence inclusion
declared policy reference
required-gate enforcement
strict fail-closed path
```

## 10. Boundary Held by This Document

This document defines terminology.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The term **Mechanical AI v0** in PULSE means:

```text
artifact-bound decision-field representation
```

not:

```text
biological cognition
human-like intelligence
AGI capability
model-training behavior
```

## 11. Final Definition

Mechanical AI v0 is PULSE project terminology for:

```text
an artifact-bound decision-field representation
that records constraints, paradox structures, stability diagnostics,
and decision traces without biological, cognitive, or AGI claims.
```

The release-authority mechanism remains PULSEmech:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```
