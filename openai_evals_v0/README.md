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

## Gate semantics (fail-closed)

The smoke gate only passes when:

- the run status is `completed` or `succeeded`, AND  
- `total > 0`, AND  
- `failed == 0` and `errored == 0`.

If `total == 0` (empty dataset or missing `result_counts`), the gate fails closed.

## Notes

- This is a pilot wiring test. Keep it shadow/diagnostic until stable (online eval runs can be flaky/costly).
- Do not make this a required CI release gate until you have stable results and an agreed policy (thresholds, retries, budgeting).
