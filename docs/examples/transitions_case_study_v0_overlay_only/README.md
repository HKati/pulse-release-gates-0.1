# C4.4 example: overlay-only tension (v0)

This directory contains a small, non-fixture transitions drift input set that reproduces a full e2e run:

transitions → paradox_field_v0.json → paradox_edges_v0.jsonl → contract checks

This example is intentionally different from `transitions_case_study_v0`:
- it produces a **gate flip**
- it includes an allowlisted **g_field_v0 overlay drift**
- metric deltas are **info-only** (below warn/crit), so **no gate_metric_tension** is expected

## Reproduce

```bash
mkdir -p out

python scripts/paradox_field_adapter_v0.py \
  --transitions-dir docs/examples/transitions_case_study_v0_overlay_only \
  --out out/paradox_field_v0_overlay_only.json

python scripts/check_paradox_field_v0_contract.py --in out/paradox_field_v0_overlay_only.json

python scripts/export_paradox_edges_v0.py \
  --in out/paradox_field_v0_overlay_only.json \
  --out out/paradox_edges_v0_overlay_only.jsonl

python scripts/check_paradox_edges_v0_contract.py \
  --in out/paradox_edges_v0_overlay_only.jsonl \
  --atoms out/paradox_field_v0_overlay_only.json


```

Expected behavior (high-level)

paradox_field_v0.meta.run_context is present

edge run_context matches the field meta.run_context on exporter-allowed keys

atoms include:

gate_flip

overlay_change (g_field_v0)

gate_overlay_tension

edges include:

at least one gate_overlay_tension

no gate_metric_tension (metrics are below warn/crit thresholds)

Notes

Do not commit generated outputs under out/**.
