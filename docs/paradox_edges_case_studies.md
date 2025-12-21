
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
