# PULSE Decision Engine EPF v0 - Design note

> Status: draft (design note only)  
> Scope: how EPF shadow signals can be surfaced in compact summary/read surfaces without changing deterministic release semantics.

This note describes how experimental EPF shadow signals can be carried from archived comparison artifacts into Decision Engine and Dual View surfaces.

The goal is NOT to introduce a second release path.

EPF remains an optional diagnostic signal family: it can highlight boundary sensitivity, perturbation response, or locally unstable behavior, but it must not silently rewrite the recorded deterministic run outcome or CI pass/fail behavior.

This page does not define release semantics. Release semantics are specified in:

- docs/STATE_v0.md
- docs/status_json.md
- docs/STATUS_CONTRACT.md
- pulse_gate_policy_v0.yml
- .github/workflows/pulse_ci.yml

## Important boundary

- Deterministic archived artifacts carry the recorded release result for a run.
- EPF shadow is diagnostic and CI-neutral by default.
- EPF surfacing may enrich stability-oriented summaries.
- EPF surfacing must NOT silently mutate the recorded baseline result or CI behavior.
- Missing EPF evidence must remain explicit (missing != clean).

Related docs:

- EPF workflow: docs/PULSE_epf_shadow_quickstart_v0.md, docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md
- EPF triage: docs/PARADOX_RUNBOOK.md
- EPF <-> topology relation: docs/PULSE_topology_epf_hook_v0.md
- Decision Engine overview: docs/PULSE_decision_engine_v0.md
- Dual View: docs/PULSE_dual_view_v0.md
- Topology overview: docs/PULSE_topology_overview_v0.md, docs/PULSE_decision_field_v0_overview.md

---

## 1. Design intent

The purpose of surfacing EPF is to preserve structural distinctions that a single release label would otherwise flatten away.

In particular:

- the same release polarity can coexist with different stability profiles
- a "good" outcome near a boundary is not equivalent to a robustly stable one
- missing EPF context is not positive evidence
- diagnostic concern should become visible without becoming a hidden policy override

This design note treats EPF as a diagnostic read over archived evidence, not as a release authority.

---

## 2. EPF carriers (where EPF evidence can appear)

EPF can appear in multiple artifact surfaces depending on which workflow paths were used for the run.

### 2.1 EPF shadow workflow outputs (comparison surface)

In the current shadow A/B workflow, EPF evidence may be visible via:

- status_baseline.json (baseline-side output)
- status_epf.json (shadow-side output)
- epf_report.txt (human-readable delta summary)
- epf_paradox_summary.json (machine-readable delta summary)

Current workflow convention:

- baseline decisions are read from status_baseline.json["decisions"]
- EPF-side decisions are read from status_epf.json["experiments"]["epf"]
- EPF entries may be raw scalars/bools, or dict objects that contain "decision" (preferred)

This is an archived comparison surface. It is NOT a policy rewrite surface.

### 2.2 Stability/topology-oriented carriers (per-run or per-state)

On the stability/topology side of the repository, EPF may appear as a diagnostic block in a run- or state-level carrier.

A representative shape is:

```json
{
  "epf": {
    "available": true,
    "L": 0.94,
    "shadow_pass": true
  }
}
```

A practical reading:

- available: whether EPF shadow evidence is present for the run/state
- L: a compact perturbation / contraction-style scalar (scale depends on producer)
- shadow_pass: whether the shadow evaluation remained within an expected region

The exact derivation and thresholding logic belongs to the producing method.

This note is about how EPF information should be surfaced and interpreted downstream, not about redefining producers.

---

## 3. EPF semantics

EPF should be read as a boundary / perturbation signal family.

It is useful when a run appears acceptable at the deterministic release level but still shows signs of fragility, instability, or boundary sensitivity under a nearby shadow view.

EPF can help distinguish cases such as:

- apparently good and stable
- apparently good but boundary-sensitive
- apparently bad and stably bad
- apparently bad with unstable or paradox-heavy structure
- unknown because EPF evidence is missing or degraded

Important design point:

EPF can refine the structural read WITHOUT redefining the recorded release outcome.

---

## 4. Decision Engine surfacing

Decision Engine should treat EPF as an optional diagnostic input that enriches a compact run summary.

It may surface EPF through fields such as:

- EPF availability
- coarse EPF posture
- numeric EPF signals (when present)
- evidence references to originating artifact(s)
- a short, non-policy summary string (optional)

Example machine-readable surface:

```json
{
  "epf_signal": {
    "available": true,
    "shadow_pass": true,
    "L": 0.94,
    "posture": "epf_boundary_sensitive",
    "evidence_refs": [
      "status_epf.json",
      "epf_paradox_summary.json",
      "epf_report.txt"
    ],
    "summary": "EPF shadow available; signal suggests near-boundary or locally unstable behavior."
  }
}
```

Notes:

- field names may vary by renderer or artifact version
- semantic stability matters more than exact spelling

Behavioral rules:

- EPF may influence stability_type (or similar stability posture summaries)
- EPF may influence reviewer/triage cues
- EPF must NOT silently overwrite the recorded baseline release outcome
- EPF absence must remain visible as absence (do not convert missing into confidence)

Decision Engine should surface EPF, not promote it into a hidden second gate.

---

## 5. Dual View surfacing

Dual View should expose the same EPF meaning in both aligned surfaces:

- a concise human-readable summary
- a structured machine-readable representation

Human-facing examples:

- "EPF shadow available; signal is clean."
- "EPF shadow available; result appears boundary-sensitive."
- "EPF shadow unavailable; stability interpretation remains incomplete."

Machine-facing requirements:

- whether EPF was present
- whether the shadow signal passed or raised concern
- any coarse EPF posture label
- references back to supporting artifact(s)

If a legacy path still uses older surface names (for example trace-style inputs), EPF meaning should remain stable across those surfaces.

Compression is allowed. Semantic drift is not.

---

## 6. Interpretation rules

### Rule A - Recorded release outcome stays recorded

EPF must not silently replace or rewrite the deterministic outcome captured in archived run artifacts.

### Rule B - Structural detail is the point

EPF exists to preserve distinctions such as fragility, instability, boundary proximity, or local non-contractive behavior.

### Rule C - Missing stays missing

If EPF evidence is not available, downstream surfaces should say so explicitly.

Missing EPF is NOT equivalent to:

- safe
- stable
- PASS
- low risk

### Rule D - Human and machine surfaces must agree

Any EPF summary shown to humans must match the structured fields shown to tools.

### Rule E - Evidence links should remain reconstructible

A reader should be able to follow EPF surfacing back to the originating artifact chain without ambiguity.

---

## 7. Suggested coarse posture vocabulary

To avoid overclaiming precision, downstream surfaces should prefer a small, audit-friendly EPF vocabulary.

Examples include:

- epf_clear
- epf_boundary_sensitive
- epf_concerning
- epf_unavailable
- epf_unknown

These are summary labels. They are not substitutes for the underlying evidence and must not be treated as automatic release-policy classes.

---

## 8. Non-goals

This design note does NOT propose that EPF should:

- redefine release policy
- act as a second release authority
- silently override status.json
- turn missing EPF context into positive evidence
- hide threshold changes inside renderer language
- collapse stability interpretation into a single opaque score

If any of those behaviors are ever desired, they should be introduced explicitly through schema/workflow/policy review.

---

## 9. Summary

EPF in Decision Engine / Dual View should be understood as a diagnostic surface for boundary-sensitive structure.

Its purpose is to make local instability, perturbation sensitivity, or evidence incompleteness visible in compact summary artifacts.

That additional visibility is valuable precisely because it does NOT rewrite the deterministic release outcome.

Design goal:

- preserve the recorded outcome
- surface EPF as optional structural context
- keep both human and machine views aligned
- keep the evidence chain reconstructible
