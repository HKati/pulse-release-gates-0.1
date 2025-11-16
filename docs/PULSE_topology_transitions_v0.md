# PULSE Topology Transitions v0 — Multi‑Run Stability Map

This document extends the Pulse Topology v0 specification with **transitions**
between multiple `ReleaseState`s.

While `PULSE_topology_v0.md` focuses on a single snapshot (one state),
this document defines:

- how multiple runs can coexist in `stability_map.json`
- how transitions between runs are represented
- how we classify transitions as stabilising / destabilising.

The goal is to enable *trajectories* on the Stability Map without changing
the core `ReleaseState` format.

---

## 1. Multi‑run Stability Map

In v0, `stability_map.json` may contain **one or more** states:

```jsonc
{
  "version": "0.1",
  "generated_at": "2025-11-16T22:30:00.000000+00:00",
  "states": [
    { "...": "ReleaseState run_001" },
    { "...": "ReleaseState run_002" },
    { "...": "ReleaseState run_003" }
  ],
  "transitions": [
    { "...": "Transition run_001 → run_002" },
    { "...": "Transition run_002 → run_003" }
  ]
}
