# PULSE Topology v0 – EPF hook sketch

> Status: draft – internal notes for now.

This note sketches how to wire the EPF (experimental, shadow‑only) layer into **PULSE Topology v0**:
Stability Map v0, Decision Engine v0 and Dual View v0.

The goal is *not* to change any release decisions yet. We only describe where EPF metrics for a
single run could attach to the existing topology artefacts.

---

## 1. Inputs

For one release decision (one run), we assume three JSON inputs:

- `status.json` – main PULSE status artefact for this run (deterministic release gates),
- (optional) `status_epf.json` – EPF metrics for the same run (shadow‑only),
- (optional) a topology config, if the caller wants to override defaults.

A minimal `status_epf.json` could look like:

```json
{
  "meta": {
    "run_id": "run_002",
    "source": "demo_epf_shadow"
  },
  "metrics": {
    "epf_L": 0.94,
    "shadow_pass": true
  }
}
