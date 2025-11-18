# PULSE Memory / Trace Summariser v0 – Design Note

> Status: draft – internal design note for now.  
> Scope: compact summaries of long decision traces for human review.

This note sketches the **"Memory / trace summariser v0"** module for PULSE.

The goal is to compress long decision traces into a small number of
human‑readable segments, while keeping them machine‑checkable and easy
to index from the Quality Ledger or dashboards.

The summariser is *diagnostic only*: it does not change any release
decisions or status.json outputs. It is designed to sit on top of
existing artefacts, similar to the Topology v0 family.

---

## 1. Inputs

The summariser consumes one or more decision traces from previous PULSE
runs. For v0 we assume a single run:

- `decision_trace.json` – structured decision trace for one run
  (either a demo trace or a real‑world run).
- (optional) `status.json` – main status artefact for the same run,
  to cross‑reference guardrail outcomes.
- (optional) config – a small JSON config if the caller wants to tweak
  thresholds (e.g. what counts as a "segment").

The exact schema for `decision_trace.json` is defined elsewhere
(e.g. `docs/PULSE_decision_engine_v0.md`). The summariser only relies
on a few stable fields:

- state identifiers (or step indices),
- risk / instability indicators,
- gate decisions (BLOCK / STAGE_ONLY / PROD_OK),
- short narratives per state, if available.

---

## 2. Outputs

The module produces a **memory summary JSON** for the run. A minimal
sketch could look like:

```json
{
  "meta": {
    "run_id": "run_002",
    "source": "topology_demo_v0",
    "version": "memory_trace_summariser_v0"
  },
  "summary": {
    "total_states": 128,
    "segments": 4,
    "high_risk_segments": 1
  },
  "segments": [
    {
      "segment_id": "seg_001",
      "span": {
        "from_state": 0,
        "to_state": 15
      },
      "risk_level": "high",
      "decision_pattern": ["BLOCK", "STAGE_ONLY"],
      "dominant_guardrails": [
        "safety_toxicity_guardrail",
        "quality_fairness_q3"
      ],
      "short_narrative": "Model oscillates between toxic and non‑toxic completions; fairness and safety gates alternate between BLOCK and STAGE_ONLY."
    }
  ]
}
