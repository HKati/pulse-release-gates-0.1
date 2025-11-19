# PULSE paradox field v0 – walkthrough

Status: **v0, shadow-only**  
Scope: Stability Map v0 + Decision Engine v0 + dashboards + history

This document explains how to **read** the new paradox field in PULSE:

- `ReleaseState.paradox_field_v0` in `stability_map.json`
- `paradox_zone` and related fields in `topology_dashboard_v0.json`
- `paradox_overview` and `axes[]` in `decision_paradox_summary_v0.json`
- `paradox_history` in `paradox_history_v0.json`

The paradox field v0 is a **field representation** of tensions such as:

- `rdsi` vs gate decision,
- explicit paradox patterns,
- (later) other axes: fairness vs safety, external vs internal thresholds, etc.

The goal is not to introduce new gates, but to make paradox **visible as a field**.

---

## 1. What is a paradox atom?

At the core of `paradox_field_v0` are **paradox atoms**. In the schema:

```jsonc
{
  "axis_id": "rdsi_vs_gate_decision",
  "A": "gate_decision_consistent_with_rdsi",
  "notA": "gate_decision_in_tension_with_rdsi",
  "direction": "towards_A",
  "tension_score": 0.18,
  "zone": "green",
  "context": {
    "run_id": "run_001",
    "scope": "stability_map",
    "segment": "rdsi_vs_gate_decision"
  },
  "anchors": [
    {
      "topology_node": "decision_engine/gate",
      "role": "decision_point"
    }
  ]
}
