# Examples

This directory contains small, repo-local example inputs intended to be reproducible and CI-friendly.

## Available examples

### 1) transitions_case_study_v0

Path:
- `docs/examples/transitions_case_study_v0/`

What it covers:
- transitions drift inputs (gate/metric/overlay)
- end-to-end run: transitions → paradox_field_v0.json → paradox_edges_v0.jsonl → contract checks
- run_context present on field meta and edges (useful for downstream correlation)

How to run:
- See `docs/examples/transitions_case_study_v0/README.md`

## Notes

- Do not commit generated outputs under `out/**`.
- Example input filenames are intentionally fixed (e.g. `pulse_overlay_drift_v0.json`) because the adapters expect those names.
- CI smoke runs these examples to prevent drift and catch missing/renamed inputs early.
