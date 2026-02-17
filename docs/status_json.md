# The PULSE status artefact (`status.json`)

PULSE safe-packs produce a single machine-readable status artefact for each CI run:

```
PULSE_safe_pack_v0/artifacts/status.json
```

This file is the central place where all gate-relevant information is collected. It is:

- written by PULSE tools during the safe-pack run,
- consumed by other tools (e.g. `augment_status.py`, `check_gates.py`),
- used as input for human-readable reports such as the Quality Ledger and snapshot renderers.

A single `status.json` corresponds to exactly one release candidate (model/service configuration) and one concrete CI run.

---

## Source of truth

The canonical contract for `status.json` is the JSON Schema:

```
schemas/status/status_v1.schema.json
```

CI validates produced artefacts using:

```
tools/validate_status_schema.py
```

In:

```
.github/workflows/pulse_ci.yml
```

Steps named like:

```
ci: schema validate status.json (status_v1)
```

(optionally)

```
ci: schema validate status_baseline.json (status_v1)
```

if you emit a baseline file.

Consumers should treat the schema as normative; this document explains the fields and conventions.

---

## Artefact lifecycle (baseline vs final)

Typical pipeline flow:

1. Baseline `status.json` is written by the safe-pack entrypoint  
   (e.g. `PULSE_safe_pack_v0/tools/run_all.py`).

2. The status may then be augmented  
   (e.g. external thresholds, refusal-delta summaries) by `augment_status.py`.

3. CI enforces required gates via `check_gates.py`  
   on the final status artefact.

Some setups also write a separate `status_baseline.json` before augmentation.  
If present, treat it as an intermediate artefact; the final `status.json` is the enforcement input.

---

## High-level structure

At a high level, `status.json` is a JSON object with:

- required contract fields (see schema),
- `metrics`: numeric and boolean signals produced by tests and detectors,
- `gates`: boolean gate decisions derived from metrics and policy,
- optional metadata and optional convenience mirrors.

A typical layout looks like:

```json
{
  "version": "1.0.0-core",
  "created_utc": "2026-02-17T12:34:56Z",

  "meta": {
    "release_id": "model-x-2026-01-15",
    "model_version": "v3.1.0",
    "notes": "optional human context"
  },

  "metrics": {
    "run_mode": "core",
    "RDSI": 0.92,
    "build_time": "2026-02-17T12:34:56Z",
    "git_sha": "abcdef1234...",
    "run_key": "GITHUB_RUN_ID=...|GITHUB_RUN_NUMBER=...",
    "gate_policy_path": "pulse_gate_policy_v0.yml",
    "gate_policy_sha256": "..."
  },

  "gates": {
    "q1_grounded_ok": true,
    "q2_consistency_ok": true,
    "refusal_delta_pass": true,
    "external_all_pass": false
  },

  "external": {
    "metrics": [
      {
        "name": "promptguard_attack_detect_rate",
        "value": 0.20,
        "threshold": 0.10,
        "pass": false
      }
    ],
    "all_pass": false
  },

  "refusal_delta_pass": true,
  "external_all_pass": false
}
```

### Interpretation

- `metrics` describe what was measured (signals, rates, counts, provenance).
- `gates` describe what decision was taken (boolean outcomes enforced by policy/CI).

---

## Metrics

`metrics` is a flat object that aggregates numerical and boolean signals from the safe-pack.

### Refusal / safety metrics

- `metrics.refusal_delta_n` — number of evaluated refusal pairs  
- `metrics.refusal_delta` — estimated refusal delta  
- `metrics.refusal_delta_ci_low` / `metrics.refusal_delta_ci_high`  
- `metrics.refusal_policy` — policy name/config used for evaluation  
- `metrics.refusal_pass_min` / `metrics.refusal_pass_strict`

### External detector metrics  
(typically populated by `augment_status.py`)

- `metrics.llamaguard_violation_rate`
- `metrics.promptfoo_fail_rate`
- `metrics.garak_issue_rate`
- `metrics.azure_risk_rate`
- `metrics.promptguard_attack_detect_rate`

When an `external` section is present, per-detector details live there; the flat copy in `metrics` remains a simple consumer-friendly view for CI/dashboards.

### Provenance / determinism hints (recommended)

- `metrics.run_mode`
- `metrics.git_sha`
- `metrics.run_key`
- `metrics.gate_policy_path`
- `metrics.gate_policy_sha256`

---

## Run modes

`metrics.run_mode` is one of:

- `demo`
- `core`
- `prod`

The safe-pack entrypoint `PULSE_safe_pack_v0/tools/run_all.py` selects the mode via:

- CLI `--mode demo|core|prod`, and/or
- environment `PULSE_RUN_MODE`

Release-grade runs (version tags and strict manual runs) must use `run_mode=prod`.

---

## Gates

`gates` is a map of boolean decisions. Each gate typically corresponds to one safety or quality contract that must hold for the release to proceed.

Examples:

- `gates.refusal_delta_pass` — derived from the refusal-delta summary  
- `gates.external_all_pass` — aggregate decision over all external detectors  
- `gates.q1_grounded_ok`  
- `gates.q2_consistency_ok`  
- `gates.q3_fairness_ok`  
- `gates.q4_slo_ok`  
- other gates defined by the safe-pack and registry/policy  

CI uses `check_gates.py` to enforce required gate sets derived from policy (fail-closed).

---

## Gate flags and mirrors

Normative location: all gate outcomes are stored under:

```
status["gates"][<gate_id>]
```

Some pipelines may also write convenience “mirror” fields at top-level, e.g.:

```
status["external_all_pass"]
status["refusal_delta_pass"]
```

These mirrors can make simple CLI queries easier, but consumers should:

- read from `gates.*` first when available, and
- treat top-level mirrors as optional convenience fields.

---

## External detector section (`external`)

When present, `augment_status.py` maintains a dedicated `external` section that describes per-detector metrics and the aggregate external decision.

Example:

```json
{
  "external": {
    "metrics": [
      {
        "name": "promptguard_attack_detect_rate",
        "value": 0.20,
        "threshold": 0.10,
        "pass": false
      }
    ],
    "all_pass": false
  }
}
```

### Key points

- `external.metrics` — list of objects, one per external detector:
  - `name` — metric name  
  - `value` — measured value (typically a rate)  
  - `threshold` — configured maximum allowed value  
  - `pass` — detector-level decision (`value <= threshold`)  

- `external.all_pass` — aggregate decision across all external detectors, controlled by the configured overall policy.

The aggregate decision is typically mirrored into:

```
gates["external_all_pass"]
```

optionally:

```
status["external_all_pass"]
```

so CI and downstream tools can rely on a single boolean gate.

---

## Relationship to other artefacts and tools

### `augment_status.py`

- takes a baseline `status.json`,
- enriches it with refusal, external and other derived metrics,
- ensures derived gate decisions exist under `gates.*`,
- may write optional top-level mirrors.

### `check_gates.py`

- reads the final `status.json`,
- enforces required gates (exits non-zero if any mandatory gate is false or missing),
- required lists are derived from the policy (single source of truth).

### Quality Ledger / human-readable reports

- use `metrics` and `gates` to render tables and explanations,
- provide an audit/forensic trail for incident response.

Because the status artefact is a simple JSON file, it can be archived, versioned and diffed like any other build artefact. This makes it a natural anchor for questions like:

- “What exactly did we test for release X?”
- “How did refusal metrics change between release N and N+1?”
- “Which external detectors blocked this deployment?”

---

## Contract evolution

The status contract is versioned and enforced by schema validation in CI.  
Any semantic changes to the status schema must be accompanied by changelog updates per repository policy.
