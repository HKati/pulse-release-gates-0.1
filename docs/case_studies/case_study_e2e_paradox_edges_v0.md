# Case study (E2E): transitions → paradox_field_v0 → paradox_edges_v0 (v0)

**Goal:** Demonstrate an evidence-first, deterministic pipeline from run drift to paradox atoms and edges.
**Important:** We do **not** commit generated `out/*.json` / `out/*.jsonl` artefacts. This doc captures the reproducible commands + a short summary only.

## Commands (Codex-run, reproducible)

```bash
# 1) transitions drift (A vs B)
python scripts/pulse_transitions_v0.py \
  --a ./out/case_study_e2e/runA \
  --b ./out/case_study_e2e/runB \
  --out ./out/case_study_e2e/transitions_A_vs_B

# 2) paradox atoms from transitions
python scripts/paradox_field_adapter_v0.py \
  --transitions-dir ./out/case_study_e2e/transitions_A_vs_B \
  --out ./out/case_study_e2e/paradox_field_v0.json

# 3) export edges (atoms → edges)
python scripts/export_paradox_edges_v0.py \
  --in ./out/case_study_e2e/paradox_field_v0.json \
  --out ./out/case_study_e2e/paradox_edges_v0.jsonl

# 4) contracts / acceptance
python scripts/check_paradox_field_v0_contract.py \
  --in ./out/case_study_e2e/paradox_field_v0.json

python scripts/check_paradox_edges_v0_contract.py \
  --in ./out/case_study_e2e/paradox_edges_v0.jsonl \
  --atoms ./out/case_study_e2e/paradox_field_v0.json

python scripts/check_paradox_edges_v0_acceptance_v0.py \
  --in ./out/case_study_e2e/paradox_edges_v0.jsonl \
  --atoms ./out/case_study_e2e/paradox_field_v0.json \
  --min-count 1

Output summary (from Codex run)

ATOM COUNT: 3

ATOM TYPES: gate_flip: 1, metric_delta: 1, gate_metric_tension: 1

EDGE COUNT: 1

EDGE TYPES: gate_metric_tension: 1

Sample edge
{
  "dst_atom_id": "a465b50d4bc6",
  "edge_id": "b18598803db9ef5e",
  "rule": "gate_flip × metric_delta(warn|crit)",
  "run_context": {
    "run_pair_id": "644c1161d952",
    "transitions_gate_csv_sha1": "edfa6c87b3b3281d7dfa8b1e4ef442d603a559da",
    "transitions_json_sha1": "a27d609eb586e276c4b8126e96b3772cd74075ab",
    "transitions_metric_csv_sha1": "4aedbc2c6889cdbcec6edc4119eb6ddc03ac5bb6",
    "transitions_overlay_json_sha1": "5f36b2ea290645ee34d943220a14b54ee5ea5be5"
  },
  "severity": "crit",
  "src_atom_id": "c2fe8b5a2a47",
  "tension_atom_id": "5e53007e2108",
  "type": "gate_metric_tension"
}

Interpretation contract (v0)

Edges are proven co-occurrences derived from atoms; they do not introduce new truth or causality.
