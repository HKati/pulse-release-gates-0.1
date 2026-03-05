# PULSE Dual View v0 — Human + Machine Read

This document introduces **PULSE Dual View v0** as a paired presentation
surface over the same archived artifact chain.

The goal is not to create a second decision source.

The goal is to expose the same run in two compatible forms:

- a concise human-readable summary
- a structured machine-readable representation

Both views must remain traceable to the **same underlying archived artifacts**
and must preserve the same release-semantics boundary.

Dual View v0 is therefore best understood as a **projection layer** over
artifact-derived diagnostic outputs, such as:

- deterministic run artifacts (for example `status.json`)
- optional stability-oriented artifacts (for example `stability_map_v0*.json`)
- optional paradox / field artifacts (for example `paradox_field_v0.json`)
- compact summary artifacts (for example `decision_engine_v0.json`)

It does not define a new release contract, and it must not silently rewrite the
recorded run outcome.

---

## 1. Dual View artifact

Recommended filename:

```text
PULSE_safe_pack_v0/artifacts/dual_view_v0.json
```

`dual_view_v0.json` is a presentation artifact.

It exists to make the same archived run legible in two aligned modes:

- a human-facing compact summary
- a machine-facing structured record

The Dual View artifact should therefore be derived from already archived
artifacts rather than treated as an independent authority.

A valid Dual View output should make it easy to answer:

- What run outcome is recorded in the deterministic artifact chain?
- What stability, uncertainty, or paradox-related structure is also visible?
- Which archived artifacts support that reading?
- How can the same interpretation be consumed by both humans and tools?

---

## 2. Method boundary

Dual View v0 follows the same boundary as the rest of the topology family:

- deterministic archived artifacts record the run outcome
- optional diagnostic artifacts preserve additional structure
- Dual View renders those materials into aligned human and machine surfaces

This means Dual View is a **read surface**, not a hidden control surface.

It may summarize:

- release polarity
- stability posture
- uncertainty or incompleteness
- paradox / conflict structure
- artifact references

It must not silently replace the recorded result in the deterministic artifact
chain.

---

## 3. Input surface

From a methods perspective, Dual View v0 has one anchor input and several
optional diagnostic inputs.

### Required anchor

- deterministic `status.json`

### Optional diagnostic inputs

- `decision_engine_v0.json`
- `stability_map_v0*.json`
- `paradox_field_v0.json`
- EPF shadow artifacts
- other archived diagnostic overlays that remain artifact-derived

Method rule:

missing optional inputs must remain visible as missing context, not be
reinterpreted as confidence, stability, or PASS.

---

## 4. Human and machine alignment

The core requirement of Dual View is **alignment**.

The human-readable surface and the machine-readable surface must describe the
same run-level interpretation.

That means:

- the same release outcome should appear in both views
- the same stability or uncertainty posture should appear in both views
- the same supporting artifacts should be recoverable from both views
- any compression in the human summary should remain faithful to the structured
  fields underneath it

The human-facing layer may be shorter.

The machine-facing layer may be more explicit.

But they should not imply different conclusions.

---

## 5. Interpretation rules

### Rule A — Artifact chain first

Always anchor the Dual View output in archived artifacts from the same run.

### Rule B — Diagnostic structure is preserved, not flattened away

Where available, stability, paradox, EPF, or evidence-completeness signals
should be carried through rather than collapsed into a single PASS/FAIL-style
summary.

### Rule C — Unknown stays unknown

If supporting context is missing, degraded, or incomplete, the Dual View should
surface that uncertainty explicitly.

### Rule D — Summary must remain traceable

A reader or tool should be able to move from Dual View back to the supporting
artifact chain without ambiguity.

---

## 6. Practical reading

A practical reading of Dual View v0 is:

- `status.json` records the deterministic run outcome
- optional topology / paradox / EPF artifacts preserve structural detail
- `decision_engine_v0.json` may compress parts of that detail into a compact
  summary surface
- `dual_view_v0.json` presents the same interpretation in aligned
  human-readable and machine-readable forms

In that sense, Dual View is not a new decision layer.

It is a **legibility layer over the same archived evidence chain**.

---

## 7. Non-goals

Dual View v0 should not:

- define a separate release policy
- function as a second release authority
- hide policy changes inside presentation language
- treat missing diagnostic context as positive evidence
- present human and machine summaries that drift apart semantically

---

## 8. Summary

PULSE Dual View v0 is best understood as an artifact-derived presentation layer
with two aligned surfaces:

- one for human reading
- one for machine consumption

Both surfaces should remain faithful to the same archived artifact chain and
should preserve the same release-semantics boundary.

Dual View improves readability and integration value, but it does not redefine
the recorded run outcome.
