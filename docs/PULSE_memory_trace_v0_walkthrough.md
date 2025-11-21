# PULSE Memory / Trace v0 – Walkthrough

Status: working draft (v0)  
Scope: experimental / shadow-only trace views on top of PULSE Topology v0.

This document explains how to build trace-style artefacts from the existing PULSE pipelines:

- decision-level trace (how release decisions evolve over runs), and
- paradox-level trace (how paradox axes and resolution plans change).

It is meant as a human-facing guide for reading the JSON files, not as a formal spec. For the high-level design, see:

- `docs/PULSE_memory_trace_summariser_v0_design_note.md`
- `docs/FUTURE_LIBRARY.md` (Memory / trace summariser v0 section)

---

## 1. Prerequisites

Before using the memory / trace tools, you should already have run the EPF shadow + paradox pipelines, as described in:

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

## Running the full memory / trace demo

Once you have `stability_map.json` and the EPF/paradox fields in place, you can
run the full memory / trace pipeline from the repo root:

```bash
# 1) Enrich stability map with EPF + paradox fields
python PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py \
  --map ./artifacts/stability_map.json

# 2) Build Decision Engine v0 view
python PULSE_safe_pack_v0/tools/build_decision_output_v0.py \
  --map ./artifacts/stability_map.json

# 3) Summarise each run (per-run paradox + EPF summary)
python PULSE_safe_pack_v0/tools/summarise_decision_paradox_v0.py \
  --input ./artifacts/decision_output_v0.json \
  --output ./artifacts/decision_paradox_summary_v0.json

# 4) Aggregate history across runs
python PULSE_safe_pack_v0/tools/summarise_paradox_history_v0.py \
  --input ./artifacts/decision_paradox_summary_v0*.json \
  --output ./artifacts/paradox_history_v0.json

# 5) Build paradox resolution plan
python PULSE_safe_pack_v0/tools/build_paradox_resolution_v0.py \
  --input ./artifacts/paradox_history_v0.json \
  --output ./artifacts/paradox_resolution_v0.json

# 6) Optional: resolution dashboard v0 (human-facing overview)
python PULSE_safe_pack_v0/tools/build_paradox_resolution_dashboard_v0.py \
  --input ./artifacts/paradox_resolution_v0.json \
  --output ./artifacts/paradox_resolution_dashboard_v0.json

# 7) Optional: topology dashboard v0 (state/transition table)
python PULSE_safe_pack_v0/tools/build_topology_dashboard_v0.py \
  --map ./artifacts/stability_map.json \
  --output ./artifacts/topology_dashboard_v0.json
