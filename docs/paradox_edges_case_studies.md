
Path: docs/paradox_edges_case_studies.md

# Paradox edges case studies (v0)

Edges are **proven co-occurrences** derived from atoms; they do **not** introduce new truth or causality.
Nodes remain atoms. Edges are a downstream-friendly index layer exported as JSONL.

---

## Case study — Fixture: gate_metric_tension (v0)

### Context
- transitions-dir: `tests/fixtures/transitions_gate_metric_tension_v0`
- Goal: Verify deterministic “edges = proven co-occurrences” export (no new truth, no causality).

### Repro (Codex / local)
```bash
python scripts/paradox_field_adapter_v0.py \
  --transitions-dir ./tests/fixtures/transitions_gate_metric_tension_v0 \
  --out ./out/paradox_field_v0.json

python scripts/export_paradox_edges_v0.py \
  --in ./out/paradox_field_v0.json \
  --out ./out/paradox_edges_v0.jsonl

python scripts/check_paradox_field_v0_contract.py \
  --in ./out/paradox_field_v0.json

python scripts/check_paradox_edges_v0_contract.py \
  --in ./out/paradox_edges_v0.jsonl \
  --atoms ./out/paradox_field_v0.json

python scripts/check_paradox_edges_v0_acceptance_v0.py \
  --in ./out/paradox_edges_v0.jsonl \
  --atoms ./out/paradox_field_v0.json \
  --type gate_metric_tension \
  --min-count 1
```

### Evidence (atoms)
- gate_flip atom_id: `c2fe8b5a2a47`
  - gate_id/status: see `out/paradox_field_v0.json` → atom evidence for `c2fe8b5a2a47`
- metric_delta atom_id: `a465b50d4bc6`
  - metric/delta/severity: see `out/paradox_field_v0.json` → atom evidence for `a465b50d4bc6`
- gate_metric_tension atom_id: `5e53007e2108`
  - gate_atom_id: `c2fe8b5a2a47`
  - metric_atom_id: `a465b50d4bc6`

### Evidence (edges)
- edge_id: `b18598803db9ef5e`
- type: `gate_metric_tension`
- src_atom_id: `c2fe8b5a2a47`
- dst_atom_id: `a465b50d4bc6`
- rule: `gate_flip × metric_delta(warn|crit)`

### Why it helped
- Downstream-friendly index: consumers can use edges without re-diffing raw runs, while still linking back to concrete atoms/evidence.
- Evidence-first stays intact: the edge asserts only a proven co-occurrence in the same run-pair drift output (no explanation/causality).

### Follow-up
Add 1–2 real (non-fixture) case studies before any deeper “content enrichment” (C.4).

---

## Case study — Fixture: gate_overlay_tension (v0)

### Context
- transitions-dir: `tests/fixtures/transitions_gate_overlay_tension_v0`
- Goal: Verify deterministic “gate flip + overlay drift” co-occurrence export as edges.

### Repro (Codex / local)
```bash
python scripts/paradox_field_adapter_v0.py \
  --transitions-dir ./tests/fixtures/transitions_gate_overlay_tension_v0 \
  --out ./out/case_study_gate_overlay/paradox_field_v0.json

python scripts/export_paradox_edges_v0.py \
  --in ./out/case_study_gate_overlay/paradox_field_v0.json \
  --out ./out/case_study_gate_overlay/paradox_edges_v0.jsonl

python scripts/check_paradox_field_v0_contract.py \
  --in ./out/case_study_gate_overlay/paradox_field_v0.json

python scripts/check_paradox_edges_v0_contract.py \
  --in ./out/case_study_gate_overlay/paradox_edges_v0.jsonl \
  --atoms ./out/case_study_gate_overlay/paradox_field_v0.json

python scripts/check_paradox_edges_v0_acceptance_v0.py \
  --in ./out/case_study_gate_overlay/paradox_edges_v0.jsonl \
  --atoms ./out/case_study_gate_overlay/paradox_field_v0.json \
  --type gate_overlay_tension \
  --min-count 1
```

### Evidence (atoms)
- gate_flip atom_id: `c2fe8b5a2a47`
- overlay_change atom_id: `0d7beffd4d01`
- gate_overlay_tension atom_id: `3d5daac129f5`
  - gate_atom_id: `c2fe8b5a2a47`
  - overlay_atom_id: `0d7beffd4d01`

### Evidence (edges)
- edge_id: `a5dacfcbfaf6dc62`
- type: `gate_overlay_tension`
- src_atom_id: `c2fe8b5a2a47`
- dst_atom_id: `0d7beffd4d01`
- rule: `gate_flip × overlay_change`

### Why it helped
- Downstream-friendly: quickly surfaces “gate flip + overlay drift” co-occurrence without re-diffing runs.
- Evidence-first: edge is only a proven co-occurrence in the same run-pair drift output (no explanation/causality).

### Follow-up
Add 1–2 real (non-fixture) case studies before deeper “content enrichment” (C.4).

---

## Case study — Synthetic e2e: runA vs runB (v0)

### Context
- runs: `out/case_study_e2e/runA` vs `out/case_study_e2e/runB` (synthetic; not committed)
- transitions-dir: `out/case_study_real/transitions_A_vs_B`
- Goal: Verify deterministic **edges = proven co-occurrences** (no new truth, no causality).

### Evidence (atoms)
- gate_flip atom_id: `45d1909d0a3b`
  - gate_id: `quality_helpfulness` (`quality`)
  - status: `PASS` → `FAIL`

- metric_delta atom_id: `45ee159b769e`
  - metric: `rdsi`
  - delta: `-0.020000000000000018` (rel: `-0.02272727272727275`), severity: `warn`

- overlay_change atom_id: `2ab8f560ea34`
  - overlay: `g_field_v0`
  - changed_keys_count: `1`
  - changed_keys_sample: `['points']`

- gate_metric_tension atom_id: `4d3d159e7623`
  - gate_atom_id: `45d1909d0a3b`
  - metric_atom_id: `45ee159b769e`

- gate_overlay_tension atom_id: `495dddfbafb9`
  - gate_atom_id: `45d1909d0a3b`
  - overlay_atom_id: `2ab8f560ea34`

### Evidence (edges)
- edge_id: `2e819379f5071b99`
  - type: `gate_metric_tension`
  - src_atom_id: `45d1909d0a3b`
  - dst_atom_id: `45ee159b769e`
  - rule: `gate_flip × metric_delta(warn|crit)`

- edge_id: `2a56e9f350e001d4`
  - type: `gate_overlay_tension`
  - src_atom_id: `45d1909d0a3b`
  - dst_atom_id: `2ab8f560ea34`
  - rule: `gate_flip × overlay_change`

### Why it helped
- Downstream-friendly index: consumers can traverse edges without re-diffing raw runs, while still linking back to concrete atoms/evidence.
- Evidence-first stays intact: edges assert only **co-occurrence** in the same run-pair drift output (no explanation/causality).

### Follow-up
Add 1–2 real (non-fixture) case studies before any deeper “content enrichment” (C.4).




