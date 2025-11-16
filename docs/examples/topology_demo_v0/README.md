# PULSE Topology demo run v0

This folder contains a small, synthetic example of the PULSE topology
layer:

- a baseline run with failing gates (`run_001`)
- a fairness-fix run that passes gates (`run_002`)
- the corresponding derived artefacts:
  - Stability Map with two states and one transition
  - Decision Engine output for `run_002`
  - Dual View v0 for `run_002`

The files are:

- `status.run_001.json` — baseline PULSE `status.json` (FAIL)
- `status.run_002.json` — fairness-fix PULSE `status.json` (STAGE-PASS)
- `status_epf.run_002.json` — EPF shadow metrics for `run_002`
- `stability_map.demo.json` — Stability Map with both runs and a transition
- `decision_trace.run_002.demo.json` — Decision Engine v0 output for `run_002`
- `dual_view_v0.run_002.demo.json` — Dual View v0 on top of `run_002`

The shape matches the specs in:

- `PULSE_topology_v0.md`
- `PULSE_paradox_module_v0.md`
- `PULSE_paradox_resolution_v0.md`
- `PULSE_decision_engine_v0.md`
- `PULSE_topology_transitions_v0.md`
- `PULSE_dual_view_v0.md`

## Scenario

- `run_001`
  - baseline model (`commit a1b2c3`)
  - several safety and quality gates FAIL
  - RDSI is low
  - no EPF metrics
  - Stability Map type: `UNSTABLE`

- `run_002`
  - fairness-data fix and retrain (`commit d4e5f6`)
  - all safety and quality gates PASS
  - RDSI improves
  - EPF shadow experiment is contractive (`epf_L < 1.0`, `shadow_pass = true`)
  - Stability Map type: `METASTABLE`
  - Decision Engine action: `STAGE_ONLY` with `LOW` risk

The transition `run_001 → run_002` is classified as `STABILISING` based
on the drop in instability score.

## How to experiment locally

If you want to run the topology tools on these examples:

1. Copy one of the example statuses into the artefact location, e.g.:

   ```bash
   cp docs/examples/topology_demo_v0/status.run_001.json \
      PULSE_safe_pack_v0/artifacts/status.json
