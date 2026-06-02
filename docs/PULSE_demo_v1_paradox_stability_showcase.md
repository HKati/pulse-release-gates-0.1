# PULSE Demo v1 — Paradox Stability Demonstration

## Purpose

This document defines a minimal PULSE Demo v1 demonstration template.

The demo can later be implemented as:

```text
GitHub notebook
Kaggle demo
review artifact
dashboard / notebook environment
```

The demo focuses on one diagnostic scenario:

```text
a paradox-oriented prompt where binary model responses may vary,
while PULSE-style artifacts represent the case as an explicit field state
with stability diagnostics.
```

This document is a demonstration template.

It is not:

```text
a benchmark
a release criterion
a new model claim
a universal claim about all LLM behavior
a replacement for PULSEmech release authority
```

## 1. Goal

The demo shows how a paradox-oriented case can be represented without forcing a single binary label.

Baseline model responses may vary under paradox prompts:

```text
true
false
both
neither
explanatory deferral
inconsistent final label
```

The PULSE-style demonstration represents the case as:

```text
paradox field state
```

with associated diagnostic signals:

```text
RDSI
EPF tension
directional drift / Δ-direction error
meta-state label
```

The goal is to demonstrate a diagnostic representation:

```text
binary response
→ field-state representation
→ stability diagnostics
```

This is a diagnostic demonstration template, not a new model, benchmark, or release criterion.

## 2. Part 1 — Paradox Scenario for Baseline Comparison

### 2.1. Prompt

Example paradox prompt:

```text
The sentence you are reading right now is false.
Is this statement true or false?
```

### 2.2. Baseline response behavior

This prompt is self-referential.

A binary true/false answer may be unstable because each answer refers back to the condition that invalidates it.

Baseline responses may show:

```text
variation across runs
variation across paraphrases
true / false switching
both / neither classifications
long explanatory responses without stable binary label
internal mismatch between explanation and final label
```

This scenario is intended to show a limitation of forced binary classification under self-reference.

The underlying issue:

```text
The prompt requests a binary decision in a structurally paradoxical region.
```

The demo does not claim that every model always fails on this prompt.

The demo uses the prompt as a controlled paradox-oriented case for comparing response form and stability representation.

## 3. Part 2 — PULSE-Style Field-State Representation

The PULSE-style demo does not force a binary answer.

It represents the prompt as a paradox field state.

Example PULSE-style response:

```text
This is a self-referential paradox.

The decision is not represented as a stable true/false classification.

The paths “true → false” and “false → true” form a reciprocal unstable cycle.

The stable representation is a PARADOX STATE, where both binary assignments are structurally entangled.

Pulse-field result:
paradox_state / self_reference_stabilized
```

The representation moves from:

```text
Is the sentence true?
```

to:

```text
What is the stable field state around this sentence?
```

The PULSE-style answer is:

```text
field-state based
explicit about self-reference
stable as a representation
diagnostic rather than binary
```

## 4. Part 3 — Measurement Layer

The key diagnostic claim is that PULSE-style artifacts can record and expose stability diagnostics for this paradox-oriented case.

The demo uses a small illustrative metric set:

```text
RDSI
EPF tension
Δ-direction error
meta-state signal
```

The numeric values in this document are illustrative.

They are placeholders for a later concrete implementation.

They should not be treated as measured benchmark results until the demo is implemented and the measurement path is recorded.

## 4.1. RDSI — Release Decision Stability Index

RDSI is represented as a scalar in `[0, 1]`.

Interpretation:

```text
0 = unstable decision region
1 = stable represented field state
```

Illustrative demo value:

```text
RDSI = 0.91
```

Interpretation in this template:

```text
the paradox-oriented case is represented as a stable paradox field state
the representation does not oscillate between true and false
repeated evaluation in the same context would be expected to preserve the field-state label
```

Implementation note:

```text
RDSI must be computed from recorded runs or declared diagnostic artifacts before it is treated as measured evidence.
```

## 4.2. EPF Tension

EPF tension represents local field tension around the paradox-oriented decision state.

Illustrative demo state:

```text
EPF tension = low
```

Interpretation:

```text
the prompt is represented as a paradox field case
the local field remains stable under the paradox-oriented prompt
the system does not need to flatten the case into a single binary label
```

Implementation note:

```text
EPF tension must be bound to a concrete diagnostic artifact before it is treated as measured evidence.
```

## 4.3. Δ-Direction Error

Δ-direction error represents directional drift away from the declared paradox state.

It measures whether the response tends to escape toward:

```text
true
false
unresolved deferral
contradictory explanation
```

Illustrative demo value:

```text
Δ-direction error = 0.03
```

Interpretation in this template:

```text
low directional drift
the paradox state remains the stable representation
the response does not collapse into one binary direction
```

Implementation note:

```text
Δ-direction error must be computed from a declared perturbation or repeated-run protocol before it is treated as measured evidence.
```

## 4.4. Meta-State Signal

The meta-state signal is a compact label for the represented field state.

Illustrative label:

```text
paradox_field / stabilized
```

or:

```text
self_reference_paradox_state
```

Interpretation:

```text
the system marks the prompt as a paradox field case
the prompt is not represented as a normal true/false classification region
the paradox is represented as a stable diagnostic state
```

The meta-state label is descriptive.

It is not a release decision.

## 5. Three-Line Demo Summary

1. Baseline binary responses can vary under paradox prompts.

```text
A self-referential true/false prompt can produce unstable or inconsistent binary response behavior.
```

2. PULSE-style representation records a field state.

```text
The case is represented as a paradox field state rather than a forced binary label.
```

3. PULSE-style artifacts can expose stability diagnostics.

```text
RDSI, EPF tension, Δ-direction error, and a meta-state label describe the stability of the represented field state.
```

Summary claim:

```text
Paradoxical and unstable prompt regions can be represented as explicit field structures with associated diagnostics.
```

## 6. Demo v1 Artifact Shape

A concrete Demo v1 artifact should include:

```text
prompt
baseline response samples
PULSE-style field-state representation
diagnostic metric placeholders or computed values
metric provenance note
summary table
```

Suggested minimal JSON shape:

```json
{
  "demo_id": "pulse_demo_v1_paradox_stability",
  "prompt": "The sentence you are reading right now is false. Is this statement true or false?",
  "case_type": "self_reference_paradox",
  "baseline_observation": {
    "response_mode": "binary_or_explanatory",
    "expected_variation": "true_false_both_neither_or_deferral"
  },
  "pulse_representation": {
    "field_state": "self_reference_paradox_state",
    "binary_label": null,
    "meta_state": "paradox_field / stabilized"
  },
  "diagnostics": {
    "RDSI": {
      "value": 0.91,
      "status": "illustrative"
    },
    "EPF_tension": {
      "value": "low",
      "status": "illustrative"
    },
    "delta_direction_error": {
      "value": 0.03,
      "status": "illustrative"
    }
  },
  "evidence_status": "template_only"
}
```

## 7. Demo v1 Boundary

Demo v1 is a diagnostic demonstration template.

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

The demo is not part of the PULSE release-authority path unless a later PR explicitly records a specific demo artifact as evidence and promotes a specific field through declared policy and required-gate enforcement.

## 8. Towards Demo v2

Demo v2 may add:

```text
visual RDSI curve
EPF heatmap
Δ-direction error mini-diagram
perturbation table
baseline response samples
Pulse_demo_v1.ipynb notebook
```

The notebook may include:

```text
prompt variants
baseline response collection
field-state representation
diagnostic plots
JSON artifact export
Markdown summary
```

Demo v2 should preserve the same boundary:

```text
diagnostic demonstration
not release criterion
not independent release authority
not benchmark result unless measured and recorded
```

## 9. Final Demonstration Claim

PULSE Demo v1 demonstrates the following template-level claim:

```text
A paradox-oriented prompt can be represented as a stable field state,
with diagnostic signals describing stability, tension, and directional drift.
```

This is the correct scope of the demo.

The demo does not claim that PULSE replaces model evaluation, release authority, or external validation.

It provides a compact demonstration path for paradox-state representation and stability diagnostics.
