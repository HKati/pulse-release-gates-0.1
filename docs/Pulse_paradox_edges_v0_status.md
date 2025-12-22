# FILE: docs/PULSE_paradox_edges_v0_status.md

# Paradox edges v0 — status and roadmap (evidence-first)

## TL;DR
The goal of paradox edges v0 is to produce a **downstream-friendly index** while keeping the system **evidence-first**:
- **Edges are proven co-occurrences** derived from atoms.
- Edges do **not** introduce new truth and do **not** assert causality.
- **Nodes remain atoms**. Edges are just a lightweight linkage/index layer.

## What’s implemented (v0)

### Transitions / drift foundation (A)
- `scripts/pulse_transitions_v0.py`
  - Gate normalization supports dict-shaped gates with `status: PASS/FAIL` (not only `pass/ok`).
  - Gate drift CSV includes `group`, `status_a`, `status_b` for audit/triage.
  - Overlay drift supports optional overlays (e.g. `g_field_v0.json`, `paradox_field_v0.json`) with a top-level diff.

### Paradox field adapter (B/C.1)
- `scripts/paradox_field_adapter_v0.py`
  - Generates `paradox_field_v0.json` (`meta` + `atoms`).
  - Deterministic atom ordering: `severity → type → atom_id`.
  - Core atom types:
    - `gate_flip`
    - `metric_delta`
    - `overlay_change`

### C.2 — `gate_metric_tension`
- Emits `gate_metric_tension` atoms when:
  - a `gate_flip` exists, and
  - a `metric_delta` exists with severity `warn|crit`,
  - both derived from the same `--transitions-dir` run-pair drift output.
- Fixture:
  - `tests/fixtures/transitions_gate_metric_tension_v0/`

### C.2.5 — `gate_overlay_tension`
- Emits `gate_overlay_tension` atoms when:
  - a `gate_flip` exists, and
  - an `overlay_change` exists with non-empty `changed_keys`,
  - both derived from the same `--transitions-dir` run-pair drift output.
- Fixture:
  - `tests/fixtures/transitions_gate_overlay_tension_v0/`

### C.3 — `paradox_edges_v0.jsonl` export (index layer)
- `scripts/export_paradox_edges_v0.py`
  - Exports edges as JSONL.
  - Edges remain “proven co-occurrence” signals (no causality / no new truth).
- Checks:
  - `scripts/check_paradox_edges_v0_contract.py`
  - `scripts/check_paradox_edges_v0_acceptance_v0.py`
- CI smoke:
  - `.github/workflows/paradox_edges_smoke.yml`

### Case studies (docs)
- `docs/paradox_edges_case_studies.md`
- `docs/case_studies/case_study_e2e_paradox_edges_v0.md`





