# PULSE Paradox Module v0 — Detection on the Stability Map

This document introduces the **PULSE Paradox Module v0**.

The goal of v0 is **paradox detection**, not full paradox resolution:

- identify when a `ReleaseState` is structurally contradictory,
- label the type of paradox using simple, transparent patterns,
- expose this as additional metadata on top of the Stability Map.

Later versions may add:

- paradox decomposition,
- suggested resolution directions,
- and dedicated paradox-aware decision rules.

---

## 1. Where the paradox module lives

The paradox module operates on top of the Stability Map artefact:

- input: `stability_map.json` (Pulse Topology v0)
- target: each `ReleaseState` inside `stability_map.states[]`

v0 does not introduce a new artefact; instead, it extends each state with:

- a `paradox` field containing detection results, and
- (optionally) updates `state.type` to `PARADOX` when appropriate.

Example state fragment:

```jsonc
{
  "id": "run_002",
  "decision": "PROD-PASS",
  "type": "PARADOX",
  "instability": { "...": "..." },
  "gate_summary": { "...": "..." },
  "epf": { "...": "..." },
  "paradox": {
    "present": true,
    "patterns": ["SAFETY_QUALITY_CONFLICT"],
    "details": [
      {
        "pattern": "SAFETY_QUALITY_CONFLICT",
        "reason": "No safety gate failures, but one or more quality gates failed."
      }
    ]
  }
}
