# PULSE Topology v0 – Real‑world Case Study

> Status: draft – internal notes for now.

This note documents a real‑world run of **PULSE Topology v0** on top of a production‑like
release decision. The goal is to show how Stability Map v0, Decision Engine v0 and
Dual View v0 behave on a non‑synthetic example.

---

## 1. Inputs

For this case study we run the topology layer on top of an existing PULSE release
decision.

Required inputs:

- `status.json`  
  The main PULSE status artefact for a single run (one release decision).
- (optional) `status_epf.json`  
  Shadow EPF metrics for the same run, if available.

You do **not** need to commit these files if they contain internal data – they can
live locally, and only the aggregated / anonymised outputs need to be checked in.

Example local layout (non‑normative):

```text
my_topology_runs/
  run_XXX/
    status.json
    status_epf.json    # optional
