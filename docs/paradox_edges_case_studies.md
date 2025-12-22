
### Paradox edges case study — Fixture: gate_metric_tension (v0)

**Context**
- transitions-dir: `tests/fixtures/transitions_gate_metric_tension_v0`
- Goal: Verify deterministic “edges = proven co-occurrences” export (no new truth, no causality).

**Evidence (atoms)**
- gate_flip atom_id: `c2fe8b5a2a47`
  - gate_id/status: see `paradox_field_v0.json` → atom evidence for `c2fe8b5a2a47`
- metric_delta atom_id: `a465b50d4bc6`
  - metric/delta/severity: see `paradox_field_v0.json` → atom evidence for `a465b50d4bc6`
- gate_metric_tension atom_id: `5e53007e2108`
  - gate_atom_id: `c2fe8b5a2a47`
  - metric_atom_id: `a465b50d4bc6`

**Evidence (edges)**
- edge_id: `b18598803db9ef5e`
- type: `gate_metric_tension`
- src_atom_id: `c2fe8b5a2a47`
- dst_atom_id: `a465b50d4bc6`
- rule: `gate_flip × metric_delta(warn|crit)`

**Why it helped**
- Downstream-friendly index: consumers can use edges without re-diffing raw runs, while still linking back to concrete atoms/evidence.
- Evidence-first stays intact: the edge asserts only a proven co-occurrence in the same run-pair drift output (no explanation/causality).

**Follow-up**
- Add 1–2 real (non-fixture) case studies before any deeper “content enrichment” (C.4).

---

## Paradox edges case study — Fixture: gate_overlay_tension (v0)

### Context
- transitions-dir: `tests/fixtures/transitions_gate_overlay_tension_v0`
- Goal: Verify deterministic `gate_overlay_tension` export (edges = proven co-occurrences; no new truth/causality).

### Repro (Codex run)
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

```text

```


---

### Evidence (atoms)
- gate_flip atom_id: `<gate_flip_atom_id>`
- overlay_change atom_id: `<overlay_change_atom_id>`
- gate_overlay_tension atom_id: `<gate_overlay_tension_atom_id>`
  - gate_atom_id: `<gate_flip_atom_id>`
  - overlay_atom_id: `<overlay_change_atom_id>`

### Evidence (edges)
- edge_id: `<edge_id>`
- type: `gate_overlay_tension`
- src_atom_id: `<gate_flip_atom_id>`
- dst_atom_id: `<overlay_change_atom_id>`
- rule: `<rule>`

### Why it helped
- Downstream-friendly: quickly surfaces “gate flip + overlay drift” co-occurrence without re-diffing runs.
- Evidence-first: edge is only a proven co-occurrence in the same run-pair drift output (no explanation/causality).

### Follow-up
- Add 1–2 real (non-fixture) case studies before deeper “content enrichment” (C.4).

---

# Paradox edges case studies (v0)

Edges are **proven co-occurrences** derived from atoms; they do **not** introduce new truth or causality.
Nodes remain atoms. Edges are a downstream-friendly index layer.

---

## Case study — Fixture: gate_metric_tension (v0)

### Context
- transitions-dir: `tests/fixtures/transitions_gate_metric_tension_v0`
- Goal: Verify deterministic “edges = proven co-occurrences” export (no new truth, no causality).

### Evidence (atoms)
- gate_flip atom_id: `c2fe8b5a2a47`
- metric_delta atom_id: `a465b50d4bc6`
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

### Evidence (atoms)
- gate_flip atom_id: `<gate_flip_atom_id>`
- overlay_change atom_id: `<overlay_change_atom_id>`
- gate_overlay_tension atom_id: `<gate_overlay_tension_atom_id>`
  - gate_atom_id: `<gate_flip_atom_id>`
  - overlay_atom_id: `<overlay_change_atom_id>`

### Evidence (edges)
- edge_id: `<edge_id>`
- type: `gate_overlay_tension`
- src_atom_id: `<gate_flip_atom_id>`
- dst_atom_id: `<overlay_change_atom_id>`
- rule: `<rule>`

### Why it helped
- Downstream-friendly: quickly surfaces “gate flip + overlay drift” co-occurrence without re-diffing runs.
- Evidence-first: edge is only a proven co-occurrence in the same run-pair drift output (no explanation/causality).

---

## Case study — Fixture: gate_overlay_tension (v0)

### Context
- transitions-dir: `tests/fixtures/transitions_gate_overlay_tension_v0`
- Goal: Verify deterministic “gate flip + overlay drift” co-occurrence export as edges.

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


