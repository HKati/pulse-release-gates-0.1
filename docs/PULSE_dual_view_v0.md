# PULSE Dual View v0 — Human + Agent Interface

This document introduces the **PULSE Dual View v0** format.

The goal is to provide a single artefact that:

- humans can read as a short narrative and risk summary,
- agents can consume as a structured, machine-friendly JSON,
- and both refer to the **same underlying Stability Map + Decision Engine data**.

Dual View v0 is a *projection* on top of:

- `stability_map.json` (single run snapshot),
- optional `stability_history.json` (multi-run trajectory),
- `decision_trace.json` (Decision Engine v0 output).

---

## 1. Dual View artefact

Recommended filename:

```text
PULSE_safe_pack_v0/artifacts/dual_view_v0.json
