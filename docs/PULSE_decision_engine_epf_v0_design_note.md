# PULSE Decision Engine EPF v0 – Design Note

> Status: draft – design note only.  
> Scope: how Decision Engine v0 and Dual View v0 can surface the EPF
> shadow signal already present in Stability Map v0.

This note describes how the experimental EPF shadow signal, already
embedded in Stability Map v0, can be surfaced in:

- the Decision Engine v0 (`decision_trace.json`), and
- Dual View v0 (combined human + agent view),

without changing any deterministic release-gate logic.

We treat EPF as an **optional diagnostic layer**: it can highlight
concerning regions (non-contractive behaviour), but it must not change
`status.json` or CI pass/fail behaviour.

---

## 1. Inputs

Decision Engine v0 already consumes Stability Map v0 artefacts, which
include, for each `ReleaseState`, an `epf` block of the form:

```json
"epf": {
  "available": true,
  "L": 0.94,
  "shadow_pass": true
}
