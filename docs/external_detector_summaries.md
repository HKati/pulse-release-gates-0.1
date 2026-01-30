# External detector summaries

This document is the **repo-level implementation guide** for integrating external detector outputs
into PULSE via archived **JSON / JSONL summaries**.

External detectors can enrich PULSE run artefacts (e.g., `status.json`) with additional safety and
quality signals (LLM guards, jailbreak scanners, hosted eval APIs, etc.).

> Policy and modes (gating vs advisory): see [`docs/EXTERNAL_DETECTORS.md`](EXTERNAL_DETECTORS.md).  
> Safe-pack overview: `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`.


## Why summaries (and not live calls)

To preserve **determinism** and **auditability**, the preferred pattern is:

1. Run external tools in a controlled step/job (offline or dedicated CI job).
2. Produce immutable outputs (JSON / JSONL summaries).
3. Archive those outputs as build artefacts (optionally with checksums).
4. Have PULSE **read and merge** the archived summaries into its `status.json` / Quality Ledger.

If a required external artefact is missing, it must never be silently treated as `PASS`.
(If you want strict fail-closed behavior for presence, enforce it explicitly in your workflow or via a
presence gate.)


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

```bash
python augment_status.py \
  --status path/to/status.json \
  --thresholds path/to/thresholds.json \
  --external_dir path/to/external_summaries
```

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

> Recommended strict mode: If you require “evidence completeness” (fail-closed on missing summaries),
> enforce presence explicitly (e.g., a dedicated presence gate such as `external_summaries_present`,
> or a workflow step that validates all required summaries exist and parse successfully).


### Thresholds and per-detector decisions

Thresholds for external detectors live in `thresholds.json`. For each wired detector:

- the `<detector>_max` key defines the **maximum allowed rate** (inclusive), e.g.:

```json
{
  "llamaguard_violation_rate_max": 0.10,
  "promptfoo_fail_rate_max": 0.05,
  "garak_issue_rate_max": 0.02,
  "azure_risk_rate_max": 0.05,
  "promptguard_attack_detect_rate_max": 0.10
}
```

- `augment_status.py` reads the detector value from the summary,
- compares `value <= threshold`,
- and records a metric entry like:

```json
{
  "name": "promptguard_attack_detect_rate",
  "value": 0.20,
  "threshold": 0.10,
  "pass": false
}
```

All per-detector metrics are collected under:

```json
"external": {
  "metrics": [
    { "name": "...", "value": ..., "threshold": ..., "pass": true/false }
  ],
  "all_pass": true/false
}
```


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

```bash
jq -e '.external_all_pass == true' status.json
```

- and downstream tools (e.g. the Quality Ledger) to render both per-detector metrics and
  the aggregate gate in a consistent way.


## Summary format recommendations

Even if only one metric is required per detector, prefer summaries that are:
- self-describing (`tool`, `tool_version` and/or digest, `run_id`, `generated_at`)
- stable (check IDs and keys don’t drift without a migration note)
- evidence-light (store large logs elsewhere; include pointers)

Illustrative minimal JSON shape:

```json
{
  "tool": "example-detector",
  "tool_version": "1.2.3",
  "tool_digest": "sha256:aaaaaaaa...",
  "run_id": "ci-12345",
  "generated_at": "2026-01-29T12:00:00Z",
  "value": 0.03,
  "notes": "Optional metadata and evidence pointers can live here."
}
```


## Security & hygiene

- Treat external summaries as **untrusted input**: validate schema; never execute embedded content.
- Do not embed secrets (API keys) or raw sensitive user data in summaries.
- Prefer immutable artefacts and consider checksums for audit integrity.
- Pin tool versions (or record `name@sha256:...`) so behavior changes are explicit.


## References

- Policy and modes: `docs/EXTERNAL_DETECTORS.md`
- Safe-pack overview: `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`


## Strict external evidence in CI (tags / workflow_dispatch)

By default, `augment_status.py` may compute an aggregate external gate in a way that can appear
trivially passing when **no external summaries were produced** (e.g., detectors were skipped).
This is convenient for day-to-day PR iteration, but it is risky for releases because it can allow
a silent “detectors didn’t run” situation.

To make releases fail-closed, this repository enforces **strict external evidence** under:

- **version tags**: `v*` or `V*`
- **manual runs**: `workflow_dispatch` with `strict_external_evidence=true`

The enforcement is implemented in the main pipeline:

- `.github/workflows/pulse_ci.yml`

### What strict mode does

Strict mode adds two layers:

1) **Pre-augment presence + parseability check (fail-closed)**  
   Before `augment_status.py` runs, CI checks that the external evidence directory contains at least
   one detector summary file and that the file(s) are parseable.

   Implementation: `scripts/check_external_summaries_present.py`

   Semantics (strict):
   - only `*_summary.json` and `*_summary.jsonl` count as detector evidence
   - JSON must be parseable (and JSONL must be parseable line-by-line)
   - if missing/unparseable → the run fails (fail-closed)

2) **Gate enforcement after status augmentation**  
   After `augment_status.py` has folded external metrics into `status.json`, CI enforces both:
   - `external_summaries_present`
   - `external_all_pass`

   This keeps the normative “what blocks shipping” rule simple and policy-driven.

### Where evidence is expected

The strict checker is run against the same directory passed to `augment_status.py` as `--external_dir`.
In the default PULSE CI layout, this directory is:

- `${PACK_DIR}/artifacts/external`

External detector adapters should write their summary artefacts into that directory using the
`*_summary.json` (or `*_summary.jsonl`) naming convention.

### Downstream usage

If you integrate PULSE in another repository and want strict behavior for releases, replicate the
same pattern:

- run `scripts/check_external_summaries_present.py --external_dir <external_dir>` before augmentation
- enforce `external_summaries_present` and `external_all_pass` as required gates for release/tag runs
