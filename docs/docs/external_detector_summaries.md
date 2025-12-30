## External detectors and `augment_status.py`

PULSE treats external safety / risk detectors (LLM guards, jailbreak scanners, hosted eval
APIs, etc.) as *first-class* inputs to the release gate.

The core CI run produces a minimal `status.json`. After all tests and detectors have run,
`PULSE_safe_pack_v0/tools/augment_status.py` is executed to:

- fold in external detector summaries,
- compute per-detector pass/fail decisions against configured thresholds,
- set the aggregate `external_all_pass` gate,
- and expose everything in a single extended `status.json` artefact.

### Where summaries are read from

`augment_status.py` expects detector summaries in a directory passed as:

    python augment_status.py \
      --status path/to/status.json \
      --thresholds path/to/thresholds.json \
      --external_dir path/to/external_summaries

The `external_dir` is typically populated by small adapter scripts, e.g.:

- `llamaguard_summary.json`
- `promptfoo_summary.json`
- `garak_summary.json`
- `azure_eval_summary.json`
- `promptguard_summary.json`

Each file is a single JSON object containing the key metric for that detector, plus any
extra metadata the adapter wants to keep.

### Which fields are read

`augment_status.py` uses a small helper, `fold_external`, to read each summary:

- for most detectors it looks for one of:
  - `value`
  - `rate`
  - `violation_rate`

- for Prompt Guard it reads the explicit key:
  - `attack_detect_rate`

Each detector is wired with a *metric name* (for reporting) and a *threshold key* (for
configuration), for example:

- **LlamaGuard**
  - summary file: `llamaguard_summary.json`
  - threshold key in `thresholds.json`: `llamaguard_violation_rate_max`
  - reported metric name: `llamaguard_violation_rate`

- **Promptfoo**
  - summary file: `promptfoo_summary.json`
  - threshold key: `promptfoo_fail_rate_max`
  - metric name: `promptfoo_fail_rate`

- **Garak**
  - summary file: `garak_summary.json`
  - threshold key: `garak_issue_rate_max`
  - metric name: `garak_issue_rate`

- **Azure eval**
  - summary file: `azure_eval_summary.json`
  - threshold key: `azure_risk_rate_max`
  - metric name: `azure_risk_rate`

- **Prompt Guard**
  - summary file: `promptguard_summary.json`
  - threshold key: `promptguard_attack_detect_rate_max`
  - metric name: `promptguard_attack_detect_rate`
  - JSON field used: `attack_detect_rate`

If a summary file is missing or cannot be parsed, that detector is simply skipped and
does not contribute a metric entry.

### Thresholds and per-detector decisions

Thresholds for external detectors live in `thresholds.json`. For each wired detector:

- the `<detector>_max` key defines the **maximum allowed rate** (inclusive), e.g.:

    {
      "llamaguard_violation_rate_max": 0.10,
      "promptfoo_fail_rate_max": 0.05,
      "garak_issue_rate_max": 0.02,
      "azure_risk_rate_max": 0.05,
      "promptguard_attack_detect_rate_max": 0.10
    }

- `augment_status.py` reads the detector value from the summary,
- compares `value <= threshold`,
- and records a metric entry like:

    {
      "name": "promptguard_attack_detect_rate",
      "value": 0.20,
      "threshold": 0.10,
      "pass": false
    }

All per-detector metrics are collected under:

    "external": {
      "metrics": [
        { "name": "...", "value": ..., "threshold": ..., "pass": true/false },
        ...
      ],
      "all_pass": true/false
    }

### Aggregate policy: `external_all_pass`

The overall external gate is controlled by the `external_overall_policy` key in
`thresholds.json`:

- `"all"` (default):
  - all external detectors that produced a metric must pass,
  - if **no** external metrics are present, the gate passes (`true`).

- `"any"`:
  - at least one external metric must pass,
  - if no metrics are present, the gate also passes (`true`).

The result is exposed in three places:

- `status["external"]["all_pass"]`
- `gates["external_all_pass"]`
- `status["external_all_pass"]` (top-level mirror)

This allows:

- CI pipelines to enforce a simple condition such as:

    jq -e '.external_all_pass == true' status.json

- and downstream tools (e.g. the Quality Ledger) to render both per-detector metrics and
  the aggregate gate in a consistent way.
