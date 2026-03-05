# PULSE Dual View v0 — Human + Machine Read

This document introduces **PULSE Dual View v0** as a paired presentation
surface over the same archived run interpretation.

The goal is not to create a second decision source.

The goal is to expose the same run in two compatible forms:

- a concise human-readable summary
- a structured machine-readable representation

Both views must remain traceable to the same underlying archived artifact
chain and must preserve the same release-semantics boundary.

Dual View v0 is currently built from derived artifacts consumed by the shipped
CLI surface:

- a Stability Map artifact passed via `--stability-map`
- a Decision Trace artifact passed via `--decision-trace`

Those builder inputs are themselves downstream projections over the archived run
evidence chain.

Dual View does not define a new release contract, and it must not silently
rewrite the recorded run outcome.

---

## 1. Dual View artifact

Recommended filename:

```text
PULSE_safe_pack_v0/artifacts/dual_view_v0.json
```

`dual_view_v0.json` is a presentation artifact.

It exists to make the same run interpretation legible in two aligned modes:

- a human-facing compact summary
- a machine-facing structured record

The current shipped builder derives this artifact from Stability Map and
Decision Trace inputs rather than from `status.json` alone.

A valid Dual View output should make it easy to answer:

- What run interpretation is being presented?
- Which stability-oriented state is being surfaced?
- Which archived artifacts support that reading?
- How can the same interpretation be consumed by both humans and tools?

---

## 2. Method boundary

Dual View v0 follows the same boundary as the rest of the topology family:

- deterministic archived artifacts record the run outcome
- optional diagnostic artifacts preserve additional structure
- derived artifacts such as Stability Map and Decision Trace compact parts of
  that structure
- Dual View renders those materials into aligned human and machine surfaces

This means Dual View is a **read surface**, not a hidden control surface.

It may summarize:

- release polarity or recorded outcome
- stability posture
- uncertainty or incompleteness
- paradox / conflict structure
- artifact references

It must not silently replace the recorded result in the deterministic artifact
chain.

---

## 3. Input surface

From a methods perspective, Dual View v0 has a current builder contract
and a broader evidence context.

### Current CLI builder contract

Required inputs for the shipped builder are:

- Stability Map input supplied via `--stability-map`
- Decision Trace input supplied via `--decision-trace`

The current builder/schema path expects state-level information from the
Stability Map side and companion summary/trace information from the Decision
Trace side.

A Dual View output is therefore **not currently built from `status.json` alone**.

### Broader evidence context

The broader archived evidence chain may also include:

- deterministic `status.json`
- paradox / field artifacts
- EPF shadow artifacts
- report-card style outputs
- other archived diagnostic overlays

These artifacts may not all be consumed directly by the current Dual View
builder, but they remain part of the evidence chain from which the Stability
Map and Decision Trace views are derived.

Method rule:

- direct Dual View inputs must match the shipped CLI/schema contract
- upstream archived artifacts should remain reconstructible from those derived
  inputs
- missing optional diagnostic context must not be rewritten as confidence,
  stability, or PASS

---

## 4. Human and machine alignment

The core requirement of Dual View is **alignment**.

The human-readable surface and the machine-readable surface must describe the
same run-level interpretation.

That means:

- the same state and summary posture should appear in both views
- the same supporting derived artifacts should be recoverable from both views
- any compression in the human summary should remain faithful to the structured
  fields underneath it

The human-facing layer may be shorter.

The machine-facing layer may be more explicit.

But they should not imply different conclusions.

---

## 5. Interpretation rules

### Rule A — Document the shipped contract accurately

This methods note should describe the builder and schema surface that currently
ships in the repo.

### Rule B — Archived evidence remains the anchor

Even when Dual View is built from derived inputs, those inputs should remain
traceable back to the archived artifact chain.

### Rule C — Diagnostic structure should be preserved

Where available, stability, paradox, EPF, or evidence-completeness signals
should be carried through rather than collapsed into a single PASS/FAIL-style
summary.

### Rule D — Unknown stays unknown

If supporting context is missing, degraded, or incomplete, the Dual View should
surface that uncertainty explicitly.

---

## 6. Practical reading

A practical reading of Dual View v0 is:

- the current shipped builder consumes Stability Map and Decision Trace inputs
- those inputs should remain traceable to the archived deterministic and
  diagnostic artifact chain
- `dual_view_v0.json` presents the same interpretation in aligned
  human-readable and machine-readable forms

In that sense, Dual View is not a new decision layer.

It is a **legibility layer over already-derived run interpretation**.

---

## 7. Non-goals

Dual View v0 should not:

- define a separate release policy
- function as a second release authority
- document a future input contract as though it were already shipped
- hide policy changes inside presentation language
- treat missing diagnostic context as positive evidence
- present human and machine summaries that drift apart semantically

---

## 8. Summary

PULSE Dual View v0 is best understood as a presentation layer with two aligned
surfaces:

- one for human reading
- one for machine consumption

In the current shipped repo surface, that layer is built from Stability Map and
Decision Trace inputs, which should remain traceable to the broader archived
artifact chain.

Dual View improves readability and integration value, but it does not redefine
the recorded run outcome.
