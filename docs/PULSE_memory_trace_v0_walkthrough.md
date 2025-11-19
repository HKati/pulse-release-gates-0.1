# PULSE Memory / Trace v0 – Walkthrough

Status: working draft (v0)  
Scope: experimental / shadow-only trace views on top of PULSE Topology v0.

This document explains how to build **trace-style artefacts** from the
existing PULSE pipelines:

- decision-level trace (how release decisions evolve over runs), and
- paradox-level trace (how paradox axes and resolution plans change).

It is meant as a **human-facing guide** for reading the JSON files,
not as a formal spec. For the high-level design, see:

- `docs/PULSE_memory_trace_summariser_v0_design_note.md`
- `docs/FUTURE_LIBRARY.md` (Memory / trace summariser v0 section)

---

## 1. Prerequisites

Before using the memory / trace tools, you should have already run the
EPF shadow + paradox pipelines, as described in:

- `docs/PULSE_epf_shadow_pipeline_v0_walkthrough.md`
- `docs/PULSE_paradox_field_v0_walkthrough.md`
- `docs/PULSE_paradox_resolution_v0_walkthrough.md`

From those steps you should have these artefacts:

- `stability_map.json`
- `decision_output_v0.json`
- `decision_paradox_summary_v0.json`
- `paradox_resolution_v0.json`
- `paradox_resolution_dashboard_v0.json`

All tools mentioned below live under:

```text
PULSE_safe_pack_v0/tools/
