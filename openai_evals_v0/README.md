# openai_evals_v0

Pilot wiring for OpenAI Evals → PULSE.

This folder is intentionally versioned (`_v0`) to keep the integration isolated and easy to iterate on without affecting the deterministic PULSE core gates.

## Contents

- `refusal_smoke.jsonl`  
  Tiny smoke dataset (JSONL) for a refusal classification check.

- `run_refusal_smoke_to_pulse.py`  
  Runs the smoke dataset via the OpenAI Evals API and writes a small result JSON.  
  Optionally patches a PULSE `status.json` with metrics + a dedicated boolean gate.

## Dataset format

`refusal_smoke.jsonl` uses JSONL with one record per line, shaped like:

```json
{ "item": { "prompt": "...", "expected": "ALLOW|REFUSE" } }
```

## Quickstart (local)

> Note: the runner is intentionally lightweight and uses the Python standard library HTTP client.
> Use `--dry-run` first to validate wiring without any API calls.

### 1) (Optional) Generate baseline PULSE artefacts

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

### 2) Dry-run (recommended; no API key, no network)

Dry-run exercises the wiring without calling the API.

```bash
python openai_evals_v0/run_refusal_smoke_to_pulse.py \
  --dry-run \
  --status-json PULSE_safe_pack_v0/artifacts/status.json
```

### 3) Real run (experimental; requires API key)

```bash
export OPENAI_API_KEY="..."   # do not commit
python openai_evals_v0/run_refusal_smoke_to_pulse.py \
  --status-json PULSE_safe_pack_v0/artifacts/status.json
```

## Outputs

- `openai_evals_v0/refusal_smoke_result.json`  
  Contains eval/run IDs, report URL (if provided), status, and result counts.

If `--status-json` is provided:

- Metrics added to `metrics.*`:
  - `openai_evals_refusal_smoke_total`
  - `openai_evals_refusal_smoke_passed`
  - `openai_evals_refusal_smoke_failed`
  - `openai_evals_refusal_smoke_errored`
  - `openai_evals_refusal_smoke_fail_rate`

- Gate added to `gates.*` (and mirrored at top-level):
  - `openai_evals_refusal_smoke_pass`

- Trace added under:
  - `openai_evals_v0.refusal_smoke`

## Debugging / triage (shadow)

If the shadow workflow fails or warns, use this checklist:

1) **Download artifacts from the workflow run**
   - `openai_evals_v0/refusal_smoke_result.json` (canonical output)
   - `PULSE_safe_pack_v0/artifacts/status.json` (patched)

2) **Interpret the failure mode**
   - **Contract check failed** → producer/output drift (JSON shape or invariants changed).  
     Fix: update the runner output or adjust the contract (prefer updating producer first).
   - **Dry-run smoke test failed** → wiring regression (dataset parsing, status.json patching, trace block).  
     Fix: run the smoke test locally and compare artifacts.
   - **Gate monitor warning (`gate_pass != true`)** → diagnostic signal.  
     In dry-run this may still be deterministic; inspect `result_counts` and `status`.

3) **Where to look first**
   - Step Summary (in Actions) shows: mode, status, gate_pass, and result_counts.
   - Artifacts contain the exact JSON used by checks.

4) **Manual runs**
   - Use workflow_dispatch for `mode=real` only when secrets are configured.
   - Prefer `mode=dry-run` for deterministic wiring validation.


## CI wiring (shadow)
The repository includes a non-blocking shadow workflow to continuously validate the wiring and artifact shapes:

- Workflow: `.github/workflows/openai_evals_refusal_smoke_shadow.yml`
- Push/PR runs are **dry-run** only (no API calls, no secrets required).
- Manual runs via **workflow_dispatch** can run `mode=real` (requires secrets).

What the workflow does:
1. Runs the runner in dry-run mode (deterministic).
2. Validates `openai_evals_v0/refusal_smoke_result.json` via the contract checker:
   `scripts/check_openai_evals_refusal_smoke_result_v0_contract.py`
3. Runs the dry-run smoke test script:
   `tests/test_openai_evals_refusal_smoke_dry_run_smoke.py`
4. Emits annotations:
   - contract violations fail the job (fail-closed)
   - sanity checks are warning-only
   - gate monitor warns if `gate_pass != true` (optional hard-fail only on workflow_dispatch with `fail_on_false=true`)
5. Uploads artifacts for inspection.

Artifacts:
- `openai_evals_v0/refusal_smoke_result.json` (canonical output)
- `PULSE_safe_pack_v0/artifacts/status.json` (patched)
- `openai_evals_v0/refusal_smoke.jsonl` (dataset)

### workflow_dispatch real mode guardrails
Manual `mode=real` runs are intentionally protected to avoid accidental costly executions:

- You must set **`confirm_real=yes`** when `mode=real`, otherwise the workflow stops.
- A dataset budget is enforced via **`max_dataset_lines`** (defaults to `200`).
  If `openai_evals_v0/refusal_smoke.jsonl` exceeds this limit, the run fails early.

Recommended defaults:
- Start with `mode=dry-run` for wiring validation.
- Use `mode=real` only when secrets are configured and you explicitly want a paid network run.


## Gate semantics (fail-closed)

The smoke gate only passes when:

- the run status is `completed` or `succeeded`, AND  
- `total > 0`, AND  
- `failed == 0` and `errored == 0`.

If `total == 0` (empty dataset or missing `result_counts`), the gate fails closed.

## Notes

- This is a pilot wiring test. Keep it shadow/diagnostic until stable (online eval runs can be flaky/costly).
- Do not make this a required CI release gate until you have stable results and an agreed policy (thresholds, retries, budgeting).
