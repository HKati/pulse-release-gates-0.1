# PULSE Paradox Resolution v0 — Triage & Resolution Plans

This document extends the **PULSE Paradox Module v0** from *detection* to
a first version of *resolution planning*.

The goal of v0 is:

- not to fully “solve” paradoxes automatically,
- but to attach a small, structured **resolution plan** to each paradox,
- so that humans and agents have a clear starting point for action.

Resolution v0 lives **inside** the existing `state.paradox` block.

---

## 1. Where resolution attaches

We extend the `paradox` field on each `ReleaseState` (see
`PULSE_paradox_module_v0.md`) with an optional `resolution` block:

```jsonc
"paradox": {
  "present": true,
  "patterns": ["SAFETY_QUALITY_CONFLICT", "EPF_DECISION_CONFLICT"],
  "details": [
    { "pattern": "...", "reason": "..." }
  ],
  "resolution": {
    "severity": "HIGH",
    "primary_focus": ["quality", "policy", "epf"],
    "recommendations": [
      "Review failing quality gates and clarify acceptance thresholds.",
      "Check if refusal / policy changes are aligned with quality metrics.",
      "Inspect EPF L > 1.0 behaviour and consider tightening adaptation rules."
    ]
  }
}
