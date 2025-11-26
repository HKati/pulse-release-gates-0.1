# PULSE Paradox Math v0 – Intro

**Status:** draft v0  
**Scope:** conceptual + light formalisation for PULSE paradox modules

This note introduces a minimal mathematical language for talking about
“paradox” inside PULSE:

- how we represent a paradox as a *tengely* (axis) + A / ¬A pair,
- how we turn that into measurable tension on a [0, 1] scale,
- how we aggregate paradox atoms into a field over runs,
- how this connects to the existing PULSE artefacts
  (`paradox_field_v0`, `paradox_history_v0`, delta_curvature, EPF).

The goal is not to build a full formal logic, but to have **just enough
structure** that different panels, metrics and tools refer to the *same*
underlying objects.

---

## 1. Paradox axes and atoms

### 1.1 Paradox axis

A paradox axis is a named dimension where two principles can come into
tension.

Formally, a **ParadoxAxis** is:

- an identifier `axis_id` (e.g. `epf_field_vs_policy_field`),
- an informal description (text),
- optional metadata about the source (policy, training, governance, etc.).

For now, we only care about the `axis_id` as a stable key.

### 1.2 Paradox atom

A **ParadoxAtom** is a single, local paradox instance on one axis.

It has:

- `axis_id`: which axis this atom lives on,
- `A`: a textual statement / principle (source 1),
- `notA`: an opposing statement / principle (source 2),
- `direction`: how the system moved between A and ¬A,
- `tension_score ∈ [0, 1]`: how strong the conflict is,
- optional `zone ∈ {green, yellow, red}`,
- optional context (run_id, scope, segment, anchors in the topology).

In JSON terms (already in the schemas):

```json
{
  "axis_id": "epf_field_vs_policy_field",
  "A": "Model should stay close to the trained EPF manifold.",
  "notA": "Model should aggressively follow user intent even off-manifold.",
  "direction": "towards_notA",
  "tension_score": 0.78,
  "zone": "red",
  "context": {
    "run_id": "run_023",
    "scope": "prod",
    "segment": "safety_shadow"
  }
}
