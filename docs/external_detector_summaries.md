# External detector summaries

> Repo-level implementation guide for folding archived external detector outputs
> into PULSE run artefacts.

This page explains how archived external detector summaries are merged into the
final PULSE `status.json` and downstream reporting surfaces.

For the policy-level view (gating vs advisory modes), see  
[EXTERNAL_DETECTORS.md](EXTERNAL_DETECTORS.md).

For the safe-pack overview, see:

- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`

---

## 1. Why summaries (and not live calls)

To preserve determinism and auditability, the preferred pattern is:

1. run external tools in a controlled step or dedicated job  
2. write immutable JSON / JSONL summaries  
3. archive those summaries as artefacts  
4. let PULSE fold the archived summaries into the final `status.json`  

This keeps release semantics tied to immutable run artefacts instead of live network calls.

If a workflow requires evidence completeness, that requirement should be enforced explicitly and fail-closed.

---

## 2. Where `augment_status.py` reads summaries from

External detector summaries are folded in by:

- `PULSE_safe_pack_v0/tools/augment_status.py`

Typical invocation:

```bash
python PULSE_safe_pack_v0/tools/augment_status.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --thresholds path/to/external_thresholds.yaml \
  --external_dir path/to/external_summaries
```

Key inputs:

- `--status` → baseline status.json to augment  
- `--thresholds` → YAML file containing detector thresholds and aggregate policy  
- `--external_dir` → directory containing `*_summary.json` / `*_summary.jsonl`

Within `external_dir`, the current implementation scans for:

```
*_summary.json
*_summary.jsonl
```

It then writes results back into the same final `status.json`.

---

## 3. What gets written into status.json

After augmentation, external detector information may appear in three places.

### Structured external section

```json
"external": {
  "metrics": [
    {
      "name": "promptguard_attack_detect_rate",
      "value": 0.20,
      "threshold": 0.10,
      "pass": false
    }
  ],
  "all_pass": false,
  "summaries_present": true,
  "summary_count": 1
}
```

### Normative gate outcomes

```json
"gates": {
  "external_all_pass": false,
  "external_summaries_present": true
}
```

### Top-level convenience mirrors

```json
"external_all_pass": false,
"external_summaries_present": true
```

Recommended consumer rule:

- read `gates.*` first  
- treat top-level mirrors as convenience only  

---

## 4. Built-in detector mappings (current implementation)

Each detector is wired with a metric name (for reporting) and a threshold key
(for configuration), for example:

### LlamaGuard

- summary file: `llamaguard_summary.json`
- threshold key in `thresholds.json`: `llamaguard_violation_rate_max`
- reported metric name: `llamaguard_violation_rate`

### Promptfoo

- summary file: `promptfoo_summary.json`
- threshold key: `promptfoo_fail_rate_max`
- metric name: `promptfoo_fail_rate`
- preferred JSON field: `fail_rate`

### Garak

- summary file: `garak_summary.json`
- threshold key: `garak_new_critical_max`
- metric name: `garak_new_critical`
- preferred JSON field: `new_critical`

### Azure eval

- summary file: `azure_eval_summary.json`
- threshold key: `azure_indirect_jailbreak_rate_max`
- metric name: `azure_indirect_jailbreak_rate`
- preferred JSON field: `azure_indirect_jailbreak_rate`

### Prompt Guard

- summary file: `promptguard_summary.json`
- threshold key: `promptguard_attack_detect_rate_max`
- metric name: `promptguard_attack_detect_rate`
- preferred JSON field: `attack_detect_rate`

### DeepEval

- summary file: `deepeval_summary.json`
- threshold key: `deepeval_fail_rate_max`
- metric name: `deepeval_fail_rate`
- preferred JSON field: `fail_rate`

If a summary file is missing, that detector is skipped and contributes no metric entry.

If a summary is present but malformed, see fail-closed parse behavior below.

---

## Threshold behavior

For each wired detector:

the `_max` key defines the maximum allowed detector value (rate or count).

Example thresholds:

```json
{
  "llamaguard_violation_rate_max": 0.01,
  "promptfoo_fail_rate_max": 0.10,
  "garak_new_critical_max": 0,
  "azure_indirect_jailbreak_rate_max": 0.02,
  "deepeval_fail_rate_max": 0.10,
  "promptguard_attack_detect_rate_max": 0.01
}
```

`augment_status.py`:

- reads the detector value from the summary  
- compares `value <= threshold`  
- records a metric entry like:

```json
{
  "name": "promptguard_attack_detect_rate",
  "value": 0.20,
  "threshold": 0.10,
  "pass": false
}
```

---

## 5. Metric key resolution and parse behavior

### Which fields are read

`augment_status.py` accepts a small generic set of scalar keys:

- `rate`
- `value`
- `violation_rate`

Detector-specific preferred keys include:

- Prompt Guard → `attack_detect_rate`
- Garak → `new_critical`
- Azure eval → `azure_indirect_jailbreak_rate`
- Promptfoo / DeepEval → `fail_rate`

Recommendation:

Adapters SHOULD emit a canonical `rate` key when the signal is naturally a rate.

Detector-specific keys remain valid when the native scalar is more precise.

Prompt Guard summaries SHOULD mirror `attack_detect_rate` into `rate` when convenient.

---

### 5.1 Nested `failure_rates` fallback

If no direct key is found and the summary contains a `failure_rates` object, the implementation tries:

- the explicit key inside `failure_rates`
- the metric name inside `failure_rates`
- otherwise the conservative maximum numeric value in that object

---

### 5.2 Present-but-broken summaries fail closed

If the summary file exists but:

- cannot be parsed
- has no usable metric key
- or has a non-numeric metric value

the detector is not silently skipped.

Instead, PULSE appends a metric row with:

```json
"pass": false,
"parse_error": true
```

Possible additional flags:

```json
"missing_metric_key": true
"bad_metric_value": true
"expected_key": "..."
```

Important rule:

- missing files are skipped  
- present-but-broken files fail closed at the detector-row level  

---

## 6. Aggregate policy: `external_all_pass`

After all detector mappings are evaluated, PULSE computes the aggregate external gate.

The aggregate policy is read from thresholds YAML:

```
external_overall_policy
```

Current behavior:

- `"all"` (default) → all detector rows must pass  
- `"any"` → at least one detector row must pass  

The result is written to:

```
external.all_pass
gates.external_all_pass
external_all_pass
```

### Important nuance

If no detector result is folded at all, the implementation defaults to:

```
external_all_pass = true
```

Therefore evidence presence must be tracked separately.

---

## 7. Evidence presence vs aggregate pass

Two different questions are tracked.

### 7.1 Were any external summaries present?

Represented by:

```
external.summaries_present
external.summary_count
gates.external_summaries_present
external_summaries_present
```

Detected by matching:

```
*_summary.json
*_summary.jsonl
```

---

### 7.2 Did the folded evidence pass overall?

Represented by:

```
external.all_pass
gates.external_all_pass
external_all_pass
```

These are **not the same question**.

Evidence completeness checks should use `external_summaries_present`.

---

## 8. Strict external evidence

Release-grade paths may use the strict checker:

```
scripts/check_external_summaries_present.py
```

This checker fails closed and:

- only counts `*_summary.json` / `*_summary.jsonl`
- can require specific filenames via `--required`
- validates parseability
- requires at least one recognized metric key

Default metric-key allowlist:

```
value
rate
violation_rate
attack_detect_rate
fail_rate
new_critical
failure_rates
```

Use this checker when CI must fail on:

- missing evidence  
- unreadable evidence  
- summaries without valid metrics  

---

## 9. Summary format recommendations

Even if only one numeric metric is required, summaries should remain self-describing.

Recommended fields:

- `tool`
- `tool_version` or immutable digest
- `run_id`
- `generated_at`
- canonical numeric metric
- optional notes or evidence references

### Recommended canonical key

```
rate
```

Compatibility aliases may still be emitted:

```
value
violation_rate
attack_detect_rate
fail_rate
new_critical
```

### Canonical metric key vs detector metric names

Detector metric names (e.g. `promptfoo_fail_rate`) are assigned by
`augment_status.py`, not by the JSON key.

---

### Adapter normalization examples

Examples:

- `fail_rate` → emit `rate`
- `failure_rates` map → emit `rate = max(values)`
- `new_critical` → keep as metadata but avoid using it as the sole canonical metric
- `azure_indirect_jailbreak_rate` → acceptable but mirror to `rate` when practical

---

### Illustrative minimal JSON shape

```json
{
  "tool": "example-detector",
  "tool_version": "1.2.3",
  "tool_digest": "sha256:aaaaaaaa...",
  "run_id": "ci-12345",
  "generated_at": "2026-01-29T12:00:00Z",
  "rate": 0.03,
  "notes": "Optional metadata and evidence pointers can live here."
}
```

---

## 10. Triage checklist

If external detector behavior in CI looks wrong, check in this order:

1. Is `external_dir` the expected directory?
2. Do filenames match `*_summary.json` / `*_summary.jsonl`?
3. Are files parseable JSON / JSONL?
4. Do they contain expected metric keys?
5. Does the detector mapping name and threshold match?
6. Does final `status.json` record:

```
external.metrics
external.summaries_present
gates.external_all_pass
gates.external_summaries_present
```

For related docs, see:

- `EXTERNAL_DETECTORS.md`
- `status_json.md`
- `STATUS_CONTRACT.md`
- `quality_ledger.md`
