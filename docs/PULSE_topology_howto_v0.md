# PULSE Topology HOWTO v0

This HOWTO shows how to run the **PULSE topology layer** on top of an
existing PULSE safe pack run.

The goal is to go from:

> `status.json` → `stability_map.json` → `decision_trace.json` →
> `dual_view_v0.json`

in a few simple commands.

For full details of the topology specs, see:

- `PULSE_topology_overview_v0.md`
- `PULSE_topology_v0.md`
- `PULSE_paradox_module_v0.md`
- `PULSE_paradox_resolution_v0.md`
- `PULSE_decision_engine_v0.md`
- `PULSE_topology_transitions_v0.md`
- `PULSE_dual_view_v0.md`

---

## 0. Prerequisites

You need:

- a working PULSE safe pack run that produces:

  ```text
  PULSE_safe_pack_v0/artifacts/status.json
  PULSE_safe_pack_v0/artifacts/status_epf.json   # optional, EPF metrics
