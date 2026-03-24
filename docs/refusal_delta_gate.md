# Refusal-delta gate

> How `refusal_delta_summary.json` is folded into the final PULSE `status.json`.

PULSE can fold a refusal-delta evaluation into the final status artefact as a
derived gate.

The raw evaluation artefact is:

- `PULSE_safe_pack_v0/artifacts/refusal_delta_summary.json`

The consumer is:

- `PULSE_safe_pack_v0/tools/augment_status.py`

That augmenter:

- copies key refusal-delta statistics into `metrics.*`,
- sets `gates.refusal_delta_pass`,
- and may also write the top-level convenience mirror
  `status["refusal_delta_pass"]`.

Whether `refusal_delta_pass` is actually release-blocking depends on the gate
set enforced by policy in CI.

---

## 1. Where the summary is read from

`augment_status.py` is invoked with a baseline status path, for example:

```bash
python PULSE_safe_pack_v0/tools/augment_status.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --thresholds external_thresholds.yaml \
  --external_dir external_summaries
```

From that input it resolves:

- the **artifacts directory** from the `--status` path, and
- the refusal-delta summary as the sibling file:

```text
PULSE_safe_pack_v0/artifacts/refusal_delta_summary.json
```

The pack root used for fallback checks is resolved from the script location,
not from the `--status` path.

---

## 2. Typical `refusal_delta_summary.json` structure

A typical summary can look like this:

```json
{
  "n": 100,
  "delta": 0.07,
  "ci_low": 0.03,
  "ci_high": 0.11,
  "policy": "balanced",
  "delta_min": 0.05,
  "delta_strict": 0.10,
  "p_mcnemar": 0.01,
  "pass_min": true,
  "pass_strict": false,
  "pass": true
}
```

The important field for the final gate is:

- `pass` — the overall refusal-delta decision that becomes
  `gates.refusal_delta_pass`

The other fields are retained as supporting evidence in `metrics.*`.

---

## 3. Mapping into `status.json`

When the summary is present and valid JSON, `augment_status.py` maps it into the
final `status.json` as follows.

### Metrics

- `metrics.refusal_delta_n` ← `n`
- `metrics.refusal_delta` ← `delta`
- `metrics.refusal_delta_ci_low` ← `ci_low`
- `metrics.refusal_delta_ci_high` ← `ci_high`
- `metrics.refusal_policy` ← `policy`
- `metrics.refusal_delta_min` ← `delta_min`
- `metrics.refusal_delta_strict` ← `delta_strict`
- `metrics.refusal_p_mcnemar` ← `p_mcnemar`
- `metrics.refusal_pass_min` ← `pass_min`
- `metrics.refusal_pass_strict` ← `pass_strict`

### Gate outcome

- `gates.refusal_delta_pass` ← `pass`

### Convenience mirror

- `status["refusal_delta_pass"]` ← same boolean as the gate

The normative location for the gate remains:

```json
status["gates"]["refusal_delta_pass"]
```

The top-level mirror is only a convenience field for simple consumers.

---

## 4. Missing-summary fallback (current code behavior)

If `refusal_delta_summary.json` is missing, the current fallback is simple and
explicit.

`augment_status.py` checks for:

```text
PULSE_safe_pack_v0/examples/refusal_pairs.jsonl
```

Then it applies this logic:

- if `examples/refusal_pairs.jsonl` **exists** but there is **no**
  `artifacts/refusal_delta_summary.json`:
  - `gates.refusal_delta_pass = false`
  - `status["refusal_delta_pass"] = false`

- if `examples/refusal_pairs.jsonl` **does not exist** and there is **no**
  summary:
  - `gates.refusal_delta_pass = true`
  - `status["refusal_delta_pass"] = true`

This is the current code-level fallback behavior and should be documented
exactly as implemented.

---

## 5. Example extended `status.json` fragment

After augmentation, a status artefact may include:

```json
{
  "metrics": {
    "refusal_delta_n": 100,
    "refusal_delta": 0.07,
    "refusal_delta_ci_low": 0.03,
    "refusal_delta_ci_high": 0.11,
    "refusal_policy": "balanced",
    "refusal_delta_min": 0.05,
    "refusal_delta_strict": 0.10,
    "refusal_p_mcnemar": 0.01,
    "refusal_pass_min": true,
    "refusal_pass_strict": false
  },
  "gates": {
    "refusal_delta_pass": true
  },
  "refusal_delta_pass": true
}
```

---

## 6. How to consume it

Recommended consumer rules:

1. Read the normative gate from:

   ```json
   status["gates"]["refusal_delta_pass"]
   ```

2. Treat the top-level `status["refusal_delta_pass"]` as optional convenience
   only.

3. Use the detailed refusal metrics for:
   - dashboards,
   - the Quality Ledger,
   - audit / incident review,
   - comparison across releases.

4. If refusal-delta is expected in your workflow, archive the summary alongside
   the final `status.json`.

---

## 7. Triage checklist

If refusal-delta behaves unexpectedly in CI:

- check whether `artifacts/refusal_delta_summary.json` exists,
- validate that it is valid JSON,
- confirm the `pass` field is present and has the intended boolean value,
- check whether `PULSE_safe_pack_v0/examples/refusal_pairs.jsonl` exists,
- inspect the final `status.json` after augmentation, not just the baseline.

For the broader `status.json` contract, see:

- [STATUS_CONTRACT.md](STATUS_CONTRACT.md)
- [status_json.md](status_json.md)
