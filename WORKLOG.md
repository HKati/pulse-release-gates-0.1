# WORKLOG

Purpose: internal bookkeeping for assembly coherence (mechanical discontinuities only).
Not a product audit. Not a roadmap. Not a “finished gating engine” demand.

## Mechanical priorities
1) CI determinism (single `run_all.py` per job; clean artifact chain)
2) Phantom / missing tool references
3) Ambiguous scaffold labeling

## Mechanical invariants
- CI: per job, `run_all.py` runs exactly once, with an explicit mode.
- Artifacts: explicit artifact dir; no overwrite/drift across steps.
- Phantom tools: missing tool references produce an explicit, consistent SKIP.
- Scaffold: scaffold/stub behavior is machine-readable (no “looks like PASS”).

## Active items
- WL-0001 — CI: single run_all invocation (prevent artifact overwrite / mode drift)
- WL-0002 — CI: centralize release-grade flags (mode + policy set)

## Ledger

### WL-0001 — CI: single run_all invocation
- Discontinuity: multiple run_all invocations can overwrite artifacts and introduce mode drift.
- Change: ensure a single run_all invocation per job (explicit `--mode`).
- Files: `.github/workflows/pulse_ci.yml`
- Verification: CI green; only one run_all call remains.
- Links: PR=<add>, commit=<add>, issue=<optional>

### WL-0002 — CI: centralize release-grade flags (mode + policy set)
- Discontinuity: duplicated release-grade/mode/policy logic across steps can drift.
- Change: compute once (`PULSE_IS_RELEASE`, `PULSE_MODE`, `PULSE_POLICY_SET`), export via `GITHUB_ENV`, reuse everywhere.
- Files: `.github/workflows/pulse_ci.yml`
- Verification: CI green; no duplicated calculations remain.
- Links: PR=<add>, commit=<add>, issue=<optional>

### WL-0005 — Deterministic baseline status.json writer
- Discontinuity: run_all writes status.json without sorted keys while augment_status rewrites with sort_keys.
- Change: write baseline status.json via the deterministic writer (sort_keys + indent).
- Files: PULSE_safe_pack_v0/tools/run_all.py
- Verification: CI green; baseline/augmented formatting no longer drifts.
- Links: PR=<add>, commit=<add>
