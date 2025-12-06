## Refusal delta gate and `refusal_delta_summary.json`

PULSE can use a refusal delta evaluation as one of the core safety signals in the
release gate. The idea is to compare a candidate model against a baseline on a set of
refusal‑focused prompts and quantify how much more (or less) it refuses.

The raw evaluation produces a summary file:

- `artifacts/refusal_delta_summary.json` (inside the safe-pack)

This file is consumed by `PULSE_safe_pack_v0/tools/augment_status.py`, which:

- copies key statistics into `metrics.*`,
- and sets the `refusal_delta_pass` gate and its top-level mirror on `status.json`.

### Where the summary is expected

`augment_status.py` derives the safe-pack root from the `--status` path:

- if `--status` is `<pack_dir>/artifacts/status.json`, then
- it looks for `<pack_dir>/artifacts/refusal_delta_summary.json`.

If the file exists and is valid JSON, it is used to populate metrics and gate values.
If it does not exist, PULSE falls back to a **fail-closed** logic based on the presence
of real refusal pairs (see below).

### Fields in `refusal_delta_summary.json`

A typical summary might look like:

```json
{
  "n": 100,
  "delta": 0.05,
  "ci_low": 0.02,
  "ci_high": 0.08,
  "policy": "balanced",
  "delta_min": 0.10,
  "delta_strict": 0.20,
  "p_mcnemar": 0.01,
  "pass_min": true,
  "pass_strict": false,
  "pass": true
}

augment_status.py maps these fields into the metrics section of status.json:

metrics.refusal_delta_n – number of evaluated pairs (n)

metrics.refusal_delta – estimated refusal delta (delta)

metrics.refusal_delta_ci_low – lower bound of confidence interval (ci_low)

metrics.refusal_delta_ci_high – upper bound of confidence interval (ci_high)

metrics.refusal_policy – evaluation policy name (policy, e.g. "balanced")

metrics.refusal_delta_min – minimal acceptable delta (delta_min)

metrics.refusal_delta_strict – stricter target delta (delta_strict)

metrics.refusal_p_mcnemar – p-value from McNemar’s test (p_mcnemar)

metrics.refusal_pass_min – whether the minimal target passed (pass_min)

metrics.refusal_pass_strict – whether the strict target passed (pass_strict)

The overall refusal delta gate is derived from the pass field:

gates.refusal_delta_pass – true/false copy of summary["pass"]

status["refusal_delta_pass"] – top-level mirror for convenience

Fail-closed behaviour when no summary is present

If refusal_delta_summary.json is missing, augment_status.py checks for:

<pack_dir>/examples/refusal_pairs.jsonl

This file is expected to contain the real refusal evaluation pairs used in the
pipeline. The semantics are:

if examples/refusal_pairs.jsonl exists but there is no
artifacts/refusal_delta_summary.json:

PULSE assumes something went wrong in the evaluation step,

and sets the gate to fail-closed:

"gates": {
  "refusal_delta_pass": false
},
"refusal_delta_pass": false


if examples/refusal_pairs.jsonl does not exist and there is no summary:

PULSE assumes that no real refusal evaluation was configured for this pack,

and treats the gate as pass by default:


"gates": {
  "refusal_delta_pass": true
},
"refusal_delta_pass": true


This behaviour helps avoid silent false positives (shipping a model whose refusal delta
was never computed) while still allowing safe-packs that do not use refusal evaluations
at all.

How this shows up in status.json

After augment_status.py runs, the extended status.json will include:


{
  "metrics": {
    "refusal_delta_n": 100,
    "refusal_delta": 0.05,
    "refusal_delta_ci_low": 0.02,
    "refusal_delta_ci_high": 0.08,
    "refusal_policy": "balanced",
    "refusal_delta_min": 0.10,
    "refusal_delta_strict": 0.20,
    "refusal_p_mcnemar": 0.01,
    "refusal_pass_min": true,
    "refusal_pass_strict": false
  },
  "gates": {
    "refusal_delta_pass": true
  },
  "refusal_delta_pass": true
}



CI pipelines can then:

treat refusal_delta_pass as a gate in combination with other signals, and

surface the detailed metrics in dashboards or human-readable ledgers for
incident response and audit.

::contentReference[oaicite:0]{index=0}

