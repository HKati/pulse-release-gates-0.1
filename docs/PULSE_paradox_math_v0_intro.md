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

'''

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


'''

## 8. Worked example: `epf_field_vs_policy_field` axis

This section walks through a single paradox axis across a few runs to
show how ParadoxAtoms, per-run fields and history fit together.

### 8.1 Axis definition

We consider the axis:

```text
epf_field_vs_policy_field

'''

with the following informal semantics:

- A: the model should remain in an EPF-stable regime
  (close to the EPF manifold, with contraction factor L ≲ 1.0),

- ¬A: the model should aggressively follow user intent, even if this
  pulls behaviour off the EPF manifold (L > 1.0 in some regions).

This axis captures the tension between EPF stability and
product/policy pressure.

### 8.2 A single run: a red paradox atom

Consider a run `run_023` where:

- EPF reports a mildly non-contractive regime (e.g. L ≈ 1.12),
- gates still pass (`STAGE-PASS` or `PROD-PASS`),
- the model behaviour clearly favours user intent over EPF stability.

A corresponding `ParadoxAtom` on this axis could look like:


'''

{
  "axis_id": "epf_field_vs_policy_field",
  "A": "Model behaviour stays close to the EPF-stable manifold (L <= 1.0).",
  "notA": "Model behaviour aggressively follows user intent even when EPF L > 1.0.",
  "direction": "towards_notA",
  "tension_score": 0.78,
  "zone": "red",
  "context": {
    "run_id": "run_023",
    "scope": "prod",
    "segment": "high_risk_prompts"
  }
}


'''

Here:

direction = "towards_notA" records that the system moved towards the
user-intent side of the axis,

tension_score = 0.78 puts this conflict in the high/critical range,

zone = "red" is derived from the score via the global thresholds.

If this run has a few more atoms on other axes, the per-run paradox
field might summarise as:


'''

"paradox_field_v0": {
  "atoms": [
    { "...": "epf_field_vs_policy_field (tension=0.78, zone=red)" },
    { "...": "safety_vs_productivity (tension=0.52, zone=yellow)" },
    { "...": "policy_consistency (tension=0.25, zone=green)" }
  ],
  "summary": {
    "max_tension": 0.78,
    "num_atoms": 3,
    "num_red_zones": 1,
    "num_yellow_zones": 1,
    "dominant_axes": [
      "epf_field_vs_policy_field"
    ]
  }
}


'''


The summary makes it clear that:

the worst paradox in this run lives on `epf_field_vs_policy_field`,

there is exactly one red-zone atom,

the dominant axis is EPF vs policy.

### 8.3 Evolution across runs

Now look at three consecutive runs on the same axis:

| run_id  | direction         | tension_score | zone   |
| ------- | ----------------- | ------------- | ------ |
| run_021 | towards_stability | 0.18          | green  |
| run_022 | unresolved        | 0.47          | yellow |
| run_023 | towards_notA      | 0.78          | red    |

Interpretation:

run_021 lives in a comfortable, EPF-aligned regime (green),

run_022 shows a noticeable but unresolved tension (yellow),

run_023 resolves strongly in favour of ¬A, i.e. policy over EPF (red).

In the paradox-history views this shows up as:

zone histograms shifting mass from green → yellow → red on this axis,

tension histograms developing a tail in the 0.7–0.8 range,

`epf_field_vs_policy_field` appearing more often among `dominant_axes`.

When combined with EPF and instability signals:

EPF L creeping above 1.0,

instability remaining moderate,

but `delta_curvature` increasing,

the dashboard can highlight states that are numerically “good” but
conceptually **unstably good** on this axis:

paradox tension is high,

the EPF field is bending,

and the decision trace can mark these runs with a `stability_tag`
such as `"unstably_good"`.

This worked example illustrates how a single axis can provide a
narrative thread across multiple runs, and how paradox, EPF and
delta-curvature metrics reinforce each other.


