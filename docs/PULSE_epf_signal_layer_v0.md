# PULSE: EPF signal layer v0

> v0 design note for the *External Physical Field* (EPF) signal that is attached
> to the Stability Map and consumed by the paradox / memory tooling as a
> shadow-only sensor.

In v0, the EPF is treated as an *external sensor* over the system’s
operational “physics”, not as a direct decision rule.

- It does **not** decide anything.
- It does **not** override gate logic.
- It is a *numerical field* that we attach to each Stability Map snapshot,
  so that later analysis (paradox history, dashboards, delta-log) can
  reason about “how tense the environment was” when a decision was made.

The long‑term goal is to:

- make the “physical” state of the system visible next to topology / paradox,
- support better triage for risky situations,
- and keep the core gate logic clean and deterministic.

This note defines the v0 shape and semantics of the EPF field.

---

## 1. EPF as an external field

Conceptually, EPF is a *physical field* defined over the system:

- it measures *tension* in the environment,
- it measures *deformation* of the system,
- and it tracks *energy* changes between runs.

In v0 we model this as a small JSON object attached to each
`ReleaseState` in the Stability Map:

```json
"epf_field_v0": {
  "phi_potential": 0.37,
  "theta_distortion": 0.12,
  "energy_delta": -0.05
}
