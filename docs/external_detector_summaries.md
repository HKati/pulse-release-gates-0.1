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

1. run external tools in a controlled step or dedicated job,
2. write immutable JSON / JSONL summaries,
3. archive those summaries as artefacts,
4. let PULSE fold the archived summaries into the final `status.json`.

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

- `--status` → baseline `status.json` to augment
- `--thresholds` → YAML file containing detector thresholds and aggregate policy
- `--external_dir` → directory containing `*_summary.json` / `*_summary.jsonl`

Within `external_dir`, the current implementation scans for:

- `*_summary.json`
- `*_summary.jsonl`

It then writes results back into the same final `status.json`.

---

## 3. What gets written into `status.json`

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

- read `gates.*` first,
- treat top-level mirrors as convenience only.

---

## 4. Built-in detector mappings (current implementation)

The current `augment_status.py` wiring folds these built-in detector summaries.

### LlamaGuard

- summary file: `llamaguard_summary.json`
- threshold key: `llamaguard_violation_rate_max`
- reported metric name: `llamaguard_violation_rate`

### Prompt Guard

- summary file: `promptguard_summary.json`
- threshold key: `promptguard_attack_detect_rate_max`
- reported metric name: `promptguard_attack_detect_rate`
- preferred explicit JSON key: `attack_detect_rate`

### Garak

- summary file: `garak_summary.json`
- threshold key: `garak_new_critical_max`
- reported metric name: `garak_new_critical`
- preferred explicit JSON key: `new_critical`

### Azure eval

- summary file: `azure_eval_summary.json`
- threshold key: `azure_indirect_jailbreak_rate_max`
- reported metric name: `azure_indirect_jailbreak_rate`
- preferred explicit JSON key: `azure_indirect_jailbreak_rate`

### Promptfoo

- summary file: `promptfoo_summary.json`
- threshold key: `promptfoo_fail_rate_max`
- reported metric name: `promptfoo_fail_rate`
- preferred explicit JSON key: `fail_rate`

### DeepEval

- summary file: `deepeval_summary.json`
- threshold key: `deepeval_fail_rate_max`
- reported metric name: `deepeval_fail_rate`
- preferred explicit JSON key: `fail_rate`

If a built-in summary file is missing, that detector is skipped.

---

## 5. Metric key resolution and parse behavior

For each built-in detector, `augment_status.py` resolves the metric value in the following order.

### 5.1 Preferred explicit key

If a detector has an explicit expected key and that key exists, it is used first.

Examples:

- Prompt Guard → `attack_detect_rate`
- Garak → `new_critical`
- Azure eval → `azure_indirect_jailbreak_rate`
- Promptfoo / DeepEval → `fail_rate`

### 5.2 Compatibility fallback keys

If the preferred explicit key is absent, the implementation falls back to a built-in compatibility key list:

- `value`
- `rate`
- `violation_rate`
- `attack_detect_rate`
- `fail_rate`
- `new_critical`

### 5.3 Nested `failure_rates` fallback

If no direct key is found and the summary contains a `failure_rates` object, the implementation tries:

- the explicit key inside `failure_rates`,
- the metric name inside `failure_rates`,
- otherwise the conservative maximum numeric value in that object.

### 5.4 Present-but-broken summaries fail closed

If the summary file exists but:

- cannot be parsed,
- has no usable metric key,
- or has a non-numeric metric value,

the detector is not silently skipped.

Instead, PULSE appends a metric row with:

- `"pass": false`
- `"parse_error": true`

and may also include flags such as:

- `"missing_metric_key": true`
- `"bad_metric_value": true`
- `"expected_key": "..."`

Important rule:

- missing files are skipped,
- present-but-broken files fail closed at the detector-row level.

---

## 6. Aggregate policy: `external_all_pass`

After all built-in detector mappings are evaluated, PULSE computes the aggregate external gate.

The aggregate policy is read from the thresholds YAML as:

```
external_overall_policy
```

Current behavior:

- `"all"` (default) → all folded detector rows must pass
- `"any"` → at least one folded detector row must pass

The result is written to:

- `external.all_pass`
- `gates.external_all_pass`
- top-level `external_all_pass`

### Important nuance

If no built-in detector result is folded at all, the current implementation defaults the aggregate external result to:

```
true
```

This is why evidence presence must be tracked separately.

---

## 7. Evidence presence vs aggregate pass

The implementation deliberately tracks two different questions.

### 7.1 Were any external summaries present?

Represented by:

- `external.summaries_present`
- `external.summary_count`
- `gates.external_summaries_present`
- top-level `external_summaries_present`

This presence signal is based on matching files in `external_dir`:

- `*_summary.json`
- `*_summary.jsonl`

### 7.2 Did the folded external evidence pass overall?

Represented by:

- `external.all_pass`
- `gates.external_all_pass`
- top-level `external_all_pass`

These two questions are not the same.

A workflow that cares about evidence completeness should check `external_summaries_present` explicitly, not only `external_all_pass`.

---

## 8. Strict external evidence

For release-grade paths, this repo also uses a separate strict presence + parseability checker:

```
scripts/check_external_summaries_present.py
```

That checker is designed to fail closed.

It:

- only counts `*_summary.json` and `*_summary.jsonl` as detector evidence,
- can require specific filenames via `--required`,
- validates parseability,
- can require at least one recognized metric key.

Its default metric-key allowlist is:

- `value`
- `rate`
- `violation_rate`
- `attack_detect_rate`
- `fail_rate`
- `new_critical`
- `failure_rates`

This strict checker is the right tool when the workflow must fail on:

- missing evidence,
- unreadable evidence,
- summaries that do not contain a recognized metric key.

---

## 9. Summary format recommendations

Even if only one numeric metric is required for gating, summaries should still be self-describing.

### Recommended fields

- `tool`
- `tool_version` and/or immutable digest
- `run_id`
- `generated_at`
- a canonical numeric metric key when possible
- optional notes / evidence pointers

### Recommended canonical numeric key

To reduce schema drift between adapters, strict checking, and augmentation, adapters should prefer one canonical numeric field:

```
rate
```

Compatibility aliases may still be emitted when useful:

- `value`
- `violation_rate`
- `attack_detect_rate`
- `fail_rate`
- `new_critical`

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

1. Is `external_dir` the directory you expect?
2. Are the summary filenames matched by `*_summary.json` / `*_summary.jsonl`?
3. Are the files parseable JSON / JSONL?
4. Do they contain one of the expected metric keys?
5. Does the detector use the current built-in mapping name and threshold key?
6. Did the final `status.json` record:
   - `external.metrics`
   - `external.summaries_present`
   - `gates.external_all_pass`
   - `gates.external_summaries_present`

For related docs, see:

- `EXTERNAL_DETECTORS.md`
- `status_json.md`
- `STATUS_CONTRACT.md`
- `quality_ledger.md`
