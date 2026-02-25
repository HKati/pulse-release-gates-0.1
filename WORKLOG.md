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
- (none)

## Ledger

### WL-0001 — CI: single run_all invocation
- Discontinuity: multiple run_all invocations can overwrite artifacts and introduce mode drift.
- Change: ensure a single run_all invocation per job (explicit `--mode`).
- Files: `.github/workflows/pulse_ci.yml`
- Verification: CI green; only one run_all call remains.
- Links: PR=#1307, commit=6a17cca

### WL-0002 — CI: centralize release-grade flags (mode + policy set)
- Discontinuity: duplicated release-grade/mode/policy logic across steps can drift.
- Change: compute once (`PULSE_IS_RELEASE`, `PULSE_MODE`, `PULSE_POLICY_SET`), export via `GITHUB_ENV`, reuse everywhere.
- Files: `.github/workflows/pulse_ci.yml`
- Verification: CI green; no duplicated calculations remain.
- Links: PR=#1308, commit=6839b2c

### WL-0003 — CI: normalize optional tool SKIP messaging
- Discontinuity: optional/overlay steps emitted `::warning:: ... skipping`, which reads like a defect and creates phantom-feature noise.
- Change: normalize optional tool/artifact absence to explicit `::notice::SKIP: ... (optional)` messaging while preserving exit-0 behavior.
- Files: `.github/workflows/pulse_ci.yml`
- Verification: CI green; missing optional tools/artifacts show explicit `SKIP` notices (not warnings).
- Links: PR=#1309, commit=35c3fae

### WL-0004 — Status: scaffold marker for stub gates
- Discontinuity: stub/scaffold gate outputs can look like real PASS/FAIL without an explicit marker.
- Change: add machine-readable scaffold diagnostics in `status.json` (`status.diagnostics.scaffold`, `status.diagnostics.gates_stubbed`, `status.diagnostics.stub_profile`).
- Files: `PULSE_safe_pack_v0/tools/run_all.py`
- Verification: status.json contains a `diagnostics` object (e.g. `"diagnostics": {...}`) indicating scaffold/stub mode.
- Links: PR=#1310, commit=2dedc93

### WL-0005 — Deterministic baseline status.json writer
- Discontinuity: run_all writes status.json without sorted keys while augment_status rewrites with sort_keys.
- Change: write baseline status.json via the deterministic writer (sort_keys + indent).
- Files: PULSE_safe_pack_v0/tools/run_all.py
- Verification: CI green; baseline/augmented formatting no longer drifts.
- Links: PR=#1311, commit=4c32484

### WL-0006 — Augment status uses baseline artifact directory
- Discontinuity: `augment_status.py` assumed `pack_dir/artifacts` for refusal-delta summary lookup, which can drift from the actual baseline `status.json` artifact directory.
- Change: derive `artifacts_dir` from `dirname(status_path)` so augmentation reads from the same artifact directory as the baseline status.
- Files: `PULSE_safe_pack_v0/tools/augment_status.py`
- Verification: when `refusal_delta_summary.json` exists next to the baseline `status.json`, augmentation reads it from there.
- Links: PR=#1312, commit=052e580

### WL-0007 — CI guard: enforce single run_all invocation
- Discontinuity: a second `tools/run_all.py` call can be accidentally reintroduced, causing artifact overwrite and mode/config drift.
- Change: add a CI guard that fails if `pulse_ci.yml` contains more than one `tools/run_all.py` occurrence or lacks explicit `--mode`.
- Files: `ci/check_single_run_all.py`, `.github/workflows/pulse_ci.yml`, `ci/tools-tests.list`
- Verification: CI fails fast on duplicate run_all or missing --mode; otherwise passes.
- Links: PR=#1313, commits=979dc7d, 1eee6d8, 0326de1

### WL-0008 — CI guard: enforce workflow/script path references exist
- Discontinuity: workflows/manifests can reference missing scripts, creating latent CI failures and drift.
- Change: run path-ref guard in tools smoke suite; remove dead checker references from EPF workflow.
- Files: `ci/check_path_refs_exist.py`, `ci/tools-tests.list`, `.github/workflows/epf_experiment.yml`
- Verification: CI green; guard passes on main; no phantom references remain.
- Links: PR=#1314, commits=85a985b, c740608, 8974901

### WL-0009 — CI: workflow lint guardrails (YAML parse + git commit loop)
- Discontinuity: workflow YAML can fail to parse due to unquoted ':' in step names; CI loop guard was fail-open for `git -c ... commit ...` and similar global-flag forms.
- Change: harden workflow_lint guardrails (colon-name rule + robust git commit detection) to keep CI fail-closed and prevent self-trigger loops in workflows with `contents: write`.
- Files: `.github/workflows/workflow_lint.yml`
- Verification: CI green; workflow-lint passes; git commit loop guard detects `git ... commit` even with global flags and enforces `[skip ci]` / `[ci skip]` on commit commands.
- - Links: PR=#<ADD>, commits=<ADD>
+ - Links: PR=#1318, commits=dfb80c3, d727500

### WL-0010 — Pages: fail-closed mount parsing + regression tests
- Discontinuity: mount/path parsing accepted unsafe mount forms and the existing mount test was not a real regression suite (risk of drift and silent re-breaks).
- Change: validate raw mount input before normalization (fail-closed) and add regression tests that dynamically load the publisher module and assert accept/reject cases.
- Files: `scripts/pages_publish_paradox_core_bundle_v0.py`, `tests/test_pages_publish_paradox_core_bundle_v0.py`
- Verification: CI green; `pytest -q tests/test_pages_publish_paradox_core_bundle_v0.py` → 18 passed.
- Links: PR=#1325, commits=894a850, 47ca0a4, merge=c92b892
