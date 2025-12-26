# C4.4 example: reproducible non-fixture transitions input (v0)

This directory contains a small, repo-local transitions drift input set that reproduces a full e2e run:

transitions → paradox_field_v0.json → paradox_edges_v0.jsonl → contract checks

The goal is CI-friendly reproducibility without committing generated outputs.

## Inputs

This example uses fixed filenames (the adapters expect these exact names):

- `pulse_gate_drift_v0.csv`
- `pulse_metric_drift_v0.csv`
- `pulse_overlay_drift_v0.json`
- `pulse_transitions_v0.json` (optional, but included here)

## Reproduce

```bash
set -euo pipefail
mkdir -p out

python scripts/paradox_field_adapter_v0.py \
  --transitions-dir docs/examples/transitions_case_study_v0 \
  --out out/paradox_field_v0.json

python scripts/check_paradox_field_v0_contract.py \
  --in out/paradox_field_v0.json

python scripts/export_paradox_edges_v0.py \
  --in out/paradox_field_v0.json \
  --out out/paradox_edges_v0.jsonl

python scripts/check_paradox_edges_v0_contract.py \
  --in out/paradox_edges_v0.jsonl \
  --atoms out/paradox_field_v0.json

# Acceptance (path depends on repo layout / workflow fallback)
if [ -f scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py ]; then
  python scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py \
    --in out/paradox_edges_v0.jsonl
else
  python scripts/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py \
    --in out/paradox_edges_v0.jsonl
fi

