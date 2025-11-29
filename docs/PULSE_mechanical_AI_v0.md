# PULSE Mechanical AI v0 — decision field, not biology

This document gives a conceptual definition of **Mechanical AI (M‑AI)**
as realised by the PULSE stack.

It is intentionally **non-biological** and **non-cognitive**:

- no attempt to imitate humans,
- no attempt to tell a story about “understanding” or “reasoning”,
- instead: a **decision field** with explicit mechanics.

The purpose is to explain **what kind of system PULSE is**, and why it
needs a different language than “learning”, “intelligence” or “AGI”.

---

## 1. Classical learning vs Mechanical AI

### 1.1 Classical learning (closed loop)

In the classical view, learning is a **closed optimisation loop**:

- data → loss → gradient → parameter update,
- repeated many times,
- with task performance as the main metric.

Growth means:

- more data,
- more parameters,
- more compute,
- more layers.

This is **quantitative** growth inside a fixed space.

### 1.2 Mechanical AI (open field)

Mechanical AI starts from a different object:

- not “a learner”,
- but a **field** of possible decisions.

Instead of asking “what did the model learn?”, we ask:

- what does the **decision field** look like?
- where is it:
  - smooth vs curved,
  - stable vs unstable,
  - paradox‑free vs paradox‑rich?

Growth here means:

- more **relations**,
- more **paradox nuclei**,
- more **field structure**,
- more **directions** in which decisions can re‑organise.

This is **qualitative** growth: the field changes dimension and
topology, not just the amount of data.

---

## 2. Paradox as the engine of extension

### 2.1 Classical: error → correction

In a closed optimisation loop:

- error → correction,
- missing pattern → better fit,
- goal → optimisation.

The system moves **inside** a predefined space.

### 2.2 Mechanical: paradox → extension

In a decision field, a paradox is not “a bug”, but a **source**:

- two constraints that cannot be satisfied together,
- a minimal unsatisfiable set (MUS),
- a point where the field cannot remain flat.

In PULSE, paradox structure is made explicit as:

- `paradox_field_v0.json` — paradox atoms,
- each atom is a small, machine‑readable **paradox nucleus**.

Mechanically, a paradox:

- opens a new **local dimension** in the decision field,
- forces the system to **re‑organise** instead of just optimising,
- is a driver of **extension**, not a failure of learning.

The system does not “learn more data”; it **extends its field** around
paradox constraints.

---

## 3. From reward to field stability

### 3.1 Reward‑centric view

In many ML systems, the central object is a **reward / loss function**:

- good outcome → high reward,
- bad outcome → low reward,
- learning → maximise expected reward.

This is powerful but fragile:

- small changes in reward definition can flip behaviour,
- hidden trade‑offs are buried inside a single scalar.

### 3.2 Field‑centric view (PULSE)

PULSE replaces “how good is this run?” with a different question:

> **How stable is the decision field around this run?**

Key artefacts:

- `status.json` — baseline gate results,
- `paradox_field_v0.json` — paradox atoms (MUS structure),
- `stability_map_v0.json` — curvature / Δ‑bend overlay,
- `decision_engine_v0.json` — release_state + stability_type.

Instead of one scalar, we get:

- **RDSI** — Release Decision Stability Index,
- **stability_type** — e.g. `stable_good`, `unstably_good`,
- **Δ‑direction error** — where the field wants to drift,
- **EPF shadow** — how much tension is stored in the field.

Reward is replaced by a **mechanical notion of stability**.

---

## 4. What Mechanical AI does (and does not)

A Mechanical AI system like PULSE:

**Does not:**

- imitate human cognition,
- narrate “understanding” or “reasoning”,
- treat data as semantic content.

**Instead it:**

- treats data as **relations** and constraints,
- treats paradoxes as **field generators**,
- treats decisions as **configurations in a field**.

One possible short definition:

> **Mechanical AI (M‑AI)**  
> – does not “learn” more, it **extends** its field;  
> – does not “know” more, it **re‑organises** constraints;  
> – does not “generalise” by analogy, it **builds relations**.

This is why PULSE focuses on:

- topological artefacts (stability maps, paradox fields),
- field metrics (RDSI, Δ),
- and explicit, inspectable decision traces.

---

## 5. PULSE as a Mechanical AI stack

Concretely, PULSE instantiates Mechanical AI via four layers of
artefacts.

### 5.1 Gates and status artefacts

- `status.json` represents a run as a set of boolean gates:
  - each gate encodes a **structural constraint** (policy, metric,
    safety check, etc.),
  - PULSE does not interpret the gates semantically; it only cares about
    their structure and results.

This is the **surface** that the field overlays attach to.

### 5.2 Paradox field

- `paradox_field_v0.json` detects minimal paradox atoms across runs:
  - each atom is a small set of gates that cannot be satisfied together
    in a given region of configuration space,
  - formally: a minimal unsatisfiable set (MUS).

Each atom is a **field singularity**: a structurally tense region where
the decision field cannot be flat.

### 5.3 Stability map

- `stability_map_v0.json` measures curvature / Δ‑bend over the field:
  - where small perturbations leave decisions unchanged,
  - where they flip outcomes or open up new branches.

This reveals where the decision field is:

- flat vs highly curved,
- robust vs fragile,
- monotone vs oscillating.

### 5.4 Decision engine and trace

- `decision_engine_v0.json` summarises field properties as:
  - `release_state` (e.g. `PROD_OK`, `BLOCK`, `STAGE_ONLY`),
  - `stability_type` (e.g. `stable_good`, `unstably_good`,
    `unstably_bad`),
  - RDSI and other diagnostics.
- `decision_trace_v0.json` records how a final decision emerged from:
  - raw gates,
  - paradox atoms,
  - stability map overlays.

Every step is deterministic and inspectable.  
Governance reads these as **mechanical signals**, not as human‑like
“confidence”.

Together, these artefacts form a **mechanical decision field**:

- no hidden reward,
- no implicit internal heuristics,
- explicit field structure over explicit gates.

---

## 6. Why this matters for AI safety and governance

Mechanical AI is relevant for safety and release governance because it:

- separates:
  - **what the underlying model does internally** (black box),
  - from **how releases are decided** (explicit field overlay);
- gives governance a **field‑level view**:
  - where paradoxes accumulate,
  - where instability clusters,
  - where decisions are “green but tense” (`unstably_good`),
  - where the system systematically drifts in one direction (Δ‑bias).

Instead of asking:

- “Can we make the model more human‑like?”

we can ask:

- “Is this decision mechanically stable in the field we care about?”

PULSE does not solve alignment, but it **changes the coordinate system**:

- from reward → to field stability,
- from behaviour cloning → to paradox and curvature,
- from opaque confidence → to explicit decision traces.

This is what we call **Mechanical AI v0** in the PULSE project.
