# PULSE Topology v0 — Stability Map & Decision Engine Foundation

This document introduces the `stability_map.json` artefact.

The goal of the Stability Map is **not** to replace or override the existing
deterministic release gates. Instead, it sits *above* them and provides:

- a topological view over one or more PULSE runs (states and transitions),
- a scalar **instability score** per run,
- simple **state types** (STABLE / METASTABLE / UNSTABLE / PARADOX / COLLAPSE),
- the foundation for a stability‑based Decision Engine in later versions.

---

## 1. File layout

The new artefact lives alongside existing PULSE outputs in the safe pack:

```text
PULSE_safe_pack_v0/
  artifacts/
    status.json
    status_epf.json          # optional, EPF shadow layer
    stability_map.json       # NEW: stability topology (this document)
