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
- `delta_log_v0.jsonl` – per‑run delta log (one JSON object per line).


#### How to read these plots in practice

A few quick rules of thumb when you're looking at the paradox histograms:

- **Mostly green, tension mass near zero**  
  The experiment is spending almost all its time in the safe zone. Occasional
  yellow runs are fine as long as the tension histogram stays tightly
  concentrated near zero.

- **A long yellow tail with rare red spikes**  
  This usually means the system is probing the boundary of the safe region.
  Check whether the tail got heavier after a specific change (new model
  version, new prompt family, new deployment cohort).

- **Noticeable shift of mass towards high tension**  
  When the “max tension” histogram clearly moves right over time, treat it as
  an early warning sign. The gates might still pass, but you are running with
  less margin than before.

- **Frequent red runs, heavy high‑tension tail**  
  This is usually a bad sign: either the paradox configuration is too lax, or
  the underlying behaviour actually got riskier. In either case, don't blindly
  accept this as the new normal – investigate and document the change.

Whenever you change paradox tuning, use these plots as a quick sanity check
that you did not accidentally move a lot of probability mass into the
high‑tension regime.


#### Typical EPF patterns

In practice, EPF is most useful when you watch it side‑by‑side with paradox
tension:

- **Flat, low EPF distortion while tension moves around**  
  Good: the system is exploring different paradox regimes without the EPF
  signal going unstable.

- **EPF distortion spikes exactly when tension jumps**  
  This is often what you want from a shadow EPF: it reacts when the model is
  pushed into strange corners of the paradox configuration.

- **EPF distortion slowly creeping up over many runs**  
  Treat this as a “boiling frog” pattern. Nothing obviously broke in a single
  run, but the baseline got worse. It’s usually worth checking recent changes
  in prompts, routing policies, or model versions.

- **EPF stuck in a permanently high state**  
  Either the EPF configuration is too sensitive, or the underlying behaviour
  really is degraded. In both cases, the shadow panel has done its job: you
  should decide whether to re‑tune EPF or tighten the release gates.


```markdown
All tools mentioned below live under: `PULSE_safe_pack_v0/tools/`

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

...


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
  --dir ./artifacts \
  --pattern "decision_paradox_summary_v0*.json" \
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

# 8) Append delta log entry (optional but recommended)
python3 PULSE_safe_pack_v0/tools/append_delta_log_v0.py \
  --delta-log ./artifacts/delta_log_v0.jsonl \
  --source local-demo

This last step appends a single JSON line entry to `delta_log_v0.jsonl`,
capturing a compact snapshot of the run (decision, stability, paradox and EPF
snapshots, plus optional git metadata).


## New panels in the memory / trace dashboard v0

### Paradox histograms (zones and tensions)

**Inputs:** `paradox_history_v0.json`.

This group of views shows how paradox behaviour is distributed across runs, not just over time:

- **Paradox zone histogram** – how many runs ended in each zone (green / yellow / red / unknown).
- **Paradox zone histogram (weighted)** – same zones, but each run is weighted by its overall tension / risk, so a few very tense runs can dominate.
- **Paradox tension histogram** – distribution of the scalar "max tension" metric across runs (low / medium / high tails).

Use these plots when you want to:

- see whether the experiment mostly lives in the safe zone, or keeps touching yellow / red,
- check for heavy tails (e.g. many low-tension runs with a small cluster of very high-tension ones),
- sanity‑check that paradox tuning changes actually move mass between the buckets.

All of these panels are read‑only: they do not influence any gate decisions.

### EPF signal overview (optional)

**Inputs:** `paradox_history_v0.json` (for alignment) and, if present, `epf_history_v0.json`.

When EPF shadow is enabled, the dashboard adds an EPF section that plots per‑run aggregates for the EPF field, for example:

- min / max / average `phi_potential`,
- min / max / average `theta_distortion`,
- a simple trend line over run index.

The goal is to answer questions such as:

- "Did the EPF signal react when paradox tension changed?"
- "Are we slowly drifting into a regime where EPF distortion is always high?"

If EPF artefacts are missing, the panel quietly skips rendering and prints a short note in the console; the rest of the dashboard continues to work.

These panels are developer‑facing diagnostics only. They are safe to run in shadow mode and do not affect any gate behaviour.
