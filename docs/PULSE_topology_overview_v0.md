# PULSE Topology Overview v0

This document gives a high-level overview of the **PULSE topology layer**
built on top of the existing PULSE safe pack.

It connects the individual specs:

- `PULSE_topology_v0.md`
- `PULSE_paradox_module_v0.md`
- `PULSE_paradox_resolution_v0.md`
- `PULSE_decision_engine_v0.md`
- `PULSE_topology_transitions_v0.md`
- `PULSE_dual_view_v0.md`

and the corresponding tools under `PULSE_safe_pack_v0/tools/`.

The goal is to answer:

> “Given the standard PULSE artefacts, what is the end‑to‑end path from
>  raw run → Stability Map → Paradox → Decision Engine → Dual View?”

---

## 1. Inputs from the PULSE safe pack

The topology layer assumes the standard PULSE safe pack produces:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/status_epf.json` *(optional)*

At a minimum, `status.json` contains:

- gate results (`gates`), including safety / quality information,
- high‑level decision (e.g. release level),
- metrics such as RDSI,
- metadata (run id, commit, tags, etc.).

`status_epf.json` adds EPF‑related metrics where available.

These artefacts are **not** changed by the topology layer; they remain the
source of truth for deterministic, fail‑closed release gates.

---

## 2. Derived artefacts and tools

The topology layer introduces a set of derived artefacts, each produced by
a small, rule-based tool.

### 2.1 Stability Map (`stability_map.json`)

**Spec:** `PULSE_topology_v0.md`  
**Tool:** `tools/build_stability_map.py`

Output:

```text
PULSE_safe_pack_v0/artifacts/stability_map.json
