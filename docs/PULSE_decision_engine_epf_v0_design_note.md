# PULSE Decision Engine EPF v0 — Design Note

> Status: draft — design note only.  
> Scope: how EPF shadow signals can be surfaced in compact summary/read
> surfaces without changing deterministic release semantics.

This note describes how the experimental EPF shadow signal can be carried from
stability-oriented diagnostic artifacts into Decision Engine and Dual View
surfaces.

The goal is **not** to introduce a second release path.

EPF remains an **optional diagnostic signal family**: it can highlight boundary
sensitivity, perturbation response, or non-contractive behaviour, but it must
not silently rewrite the recorded deterministic run outcome or CI pass/fail
behaviour.

Where current downstream builders or readers still use older surface names
(such as `decision_trace.json`), the EPF semantics described here should remain
stable across those surfaces.

---

## 1. Design intent

The purpose of surfacing EPF is to preserve structural distinctions that a
single release label would otherwise flatten away.

In particular:

- the same release polarity can coexist with different stability profiles
- a "good" outcome near a boundary is not equivalent to a robustly stable one
- missing EPF context is not positive evidence
- diagnostic concern should become visible without becoming a hidden policy
  override

This design note therefore treats EPF as a **diagnostic read** over archived
evidence, not as a release authority.

---

## 2. Current EPF carrier

On the current stability-oriented side of the repo, EPF may appear as a
per-state diagnostic block of the form:

```json
"epf": {
  "available": true,
  "L": 0.94,
  "shadow_pass": true
}
```

A practical reading of these fields is:

- `available`: whether EPF shadow evidence is present for the state/run
- `L`: a compact perturbation/contraction-style scalar or score
- `shadow_pass`: whether the shadow evaluation remained within the expected
  acceptable region

The exact thresholding or derivation logic belongs to the producing method.

This note is about how such EPF information should be surfaced and
interpreted downstream, not about redefining the producer.

---

## 3. EPF semantics

EPF should be read as a boundary / perturbation signal family.

It is useful when a run appears acceptable at the deterministic release level
but still shows signs of instability, fragility, or local non-contractive
behaviour under a nearby shadow view.

That means EPF can help distinguish cases such as:

- apparently good and stable
- apparently good but boundary-sensitive
- apparently bad and stably bad
- apparently bad with unstable or paradox-heavy structure
- unknown because EPF evidence is missing or degraded

The important design point is:

EPF can refine the structural read **without redefining the recorded release
outcome**.

---

## 4. Decision Engine surfacing

The Decision Engine should treat EPF as an optional diagnostic input that
enriches the run summary.

It may surface EPF through fields such as:

- EPF availability
- coarse EPF posture
- source references to the originating artifact
- short explanation text compatible with the rest of the compact summary

For example, a compact summary surface may include a structure like:

```json
"epf_signal": {
  "available": true,
  "shadow_pass": true,
  "L": 0.94,
  "posture": "boundary_sensitive",
  "posture": "epf_boundary_sensitive",
"summary": "EPF shadow available; signal suggests locally unstable or near-boundary behaviour."
}
```

The exact field names may vary by renderer or artifact version.

The important behavioural rules are:

- EPF may influence `stability_type` or related stability-oriented summaries
- EPF may influence reviewer/triage cues
- EPF must not silently overwrite the recorded release outcome
- EPF absence must remain visible as absence, not be converted into confidence

In other words, Decision Engine should **surface EPF**, not promote it into a
hidden second gate.

---

## 5. Dual View surfacing

Dual View should expose the same EPF meaning in both of its aligned surfaces:

- a concise human-readable summary
- a structured machine-readable representation

The human-facing side might say things such as:

- "EPF shadow available; signal is clean."
- "EPF shadow available; result appears boundary-sensitive."
- "EPF shadow unavailable; stability interpretation remains incomplete."

The machine-facing side should preserve the same semantics in structured form,
including:

- whether EPF was present
- whether the shadow signal passed or raised concern
- any coarse EPF posture label
- references back to the relevant supporting artifact(s)

Where the current shipped Dual View path still consumes Stability Map plus
Decision Trace-style inputs, the EPF surface should be serialized there without
semantic drift.

If a future path consolidates more of this compact summary under
`decision_engine_v0.json`, the EPF interpretation should remain the same.

---

## 6. Interpretation rules

### Rule A — Recorded release outcome stays recorded

EPF must not silently replace or rewrite the deterministic outcome captured in
the archived run artifacts.

### Rule B — Structural detail is the point

The value of EPF is to preserve distinctions such as fragility, instability,
boundary proximity, or local non-contractive behaviour.

### Rule C — Missing stays missing

If EPF evidence is not available, the downstream surface should say so
explicitly.

Missing EPF is **not equivalent to**:

- safe
- stable
- PASS
- low risk

### Rule D — Human and machine surfaces must agree

Any EPF summary shown to humans should match the structured fields shown to
tools.

Compression is allowed.  
Semantic drift is not.

### Rule E — Evidence links should remain reconstructible

A reader should be able to follow the EPF surface back to the originating
artifact chain without ambiguity.

---

## 7. Suggested coarse posture vocabulary

To avoid overclaiming precision, downstream surfaces should prefer a small and
audit-friendly EPF vocabulary.

Examples include:

- `epf_clear`
- `epf_boundary_sensitive`
- `epf_concerning`
- `epf_unavailable`
- `epf_unknown`

These are summary labels.

They are not substitutes for the underlying evidence.

They also should not be treated as automatic release-policy classes.

---

## 8. Non-goals

This design note does **not** propose that EPF should:

- redefine release policy
- act as a second release authority
- silently override `status.json`
- turn missing EPF context into positive evidence
- hide threshold changes inside renderer language
- collapse stability interpretation into a single opaque score

If any of those behaviours are ever desired, they should be introduced
explicitly through schema, workflow, and policy review.

---

## 9. Summary

EPF in Decision Engine / Dual View should be understood as a **diagnostic
surface for boundary-sensitive structure**.

Its purpose is to make local instability, perturbation sensitivity, or evidence
incompleteness visible in compact summary artifacts.

That additional visibility is valuable precisely because it **does not rewrite
the deterministic release outcome**.

The design goal is therefore:

- preserve the recorded outcome
- surface EPF as optional structural context
- keep both human and machine views aligned
- keep the evidence chain reconstructible
