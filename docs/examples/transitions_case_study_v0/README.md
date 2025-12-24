# C4.4 example: reproducible non-fixture transitions input (v0)

This directory contains a small, non-fixture transitions drift input set that reproduces a full e2e run:

transitions → paradox_field_v0.json → paradox_edges_v0.jsonl → contract checks

## Reproduce

```bash
mkdir -p out

python scripts/paradox_field_adapter_v0.py \
  --transitions-dir docs/examples/transitions_case_study_v0 \
  --out out/paradox_field_v0.json

python scripts/check_paradox_field_v0_contract.py --in out/paradox_field_v0.json

python scripts/export_paradox_edges_v0.py \
  --in out/paradox_field_v0.json \
  --out out/paradox_edges_v0.jsonl

python scripts/check_paradox_edges_v0_contract.py --in out/paradox_edges_v0.jsonl
python scripts/check_paradox_edges_v0_acceptance_v0.py --in out/paradox_edges_v0.jsonl


```

Expected run_context (stable for this example)

run_pair_id: 3171fcc1fc47
transitions_gate_csv_sha1: 0b23b3f9f7c0327484afe9d5ca36f7a482eafd84
transitions_metric_csv_sha1: 78d179ec69c3ba506efc467b36c46513270110fe
transitions_overlay_json_sha1: fa475eb7fe00a607c4b510b7dbbda944ed9c742c
transitions_json_sha1: f8ed75d20643814c6bf7c1a6ce7b7af90cae0e1f

```Expected atom ids (stable for this example)

gate_flip (gate_latency_budget): 61aa57d5f75b
metric_delta (p99_latency): fcb7779bbe74
metric_delta (cpu_util): c580b44b5324
overlay_change (paradox_field_v0): 451e35d82fc0

gate_metric_tension (gate × p99_latency): f5c720a2599a
gate_metric_tension (gate × cpu_util): 621a91f73ac2
gate_overlay_tension (gate × paradox_field_v0): 64306cf439b0


```
Notes

Do not commit generated outputs under out/**.


