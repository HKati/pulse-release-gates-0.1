# PULSE `status.json` Contract (public alpha)

This page documents the minimal stable public contract for PULSE `status.json`.

The normative source of truth remains:

- `schemas/status/status_v1.schema.json`

For a fuller field-by-field walkthrough, see [status_json.md](status_json.md).

---

## Minimal stable example

```json
{
  "version": "1.0.0-core",
  "created_utc": "2026-02-17T12:34:56Z",
  "metrics": {
    "run_mode": "core"
  },
  "gates": {
    "pass_controls_refusal": true,
    "pass_controls_sanit": true,
    "sanitization_effective": true,
    "q1_grounded_ok": true,
    "q4_slo_ok": true
  }
}
```

This is a minimal stable example, not an exhaustive field catalog.

---

## Required stable fields

The current schema requires these top-level fields:

- `version` — non-empty string  
- `created_utc` — creation timestamp string  
- `metrics` — object containing at least `run_mode`  
- `gates` — object mapping gate ids to booleans  

`metrics.run_mode` must be one of:

- `demo`
- `core`
- `prod`

---

## Gate semantics

Gate outcomes live normatively under:

```
status["gates"]
```

For release enforcement, PASS is strict:

- a gate PASSES only if its value is the literal boolean `true`
- `false`, `null`, missing values, strings, and numbers are **not** PASS  
- Missing required gates fail closed.

---

## Optional additive fields

The schema also allows additive fields such as:

- `meta`
- `external`
- top-level convenience mirrors like `refusal_delta_pass`, `external_all_pass`, and `external_summaries_present`

Example:

```json
{
  "external": {
    "all_pass": false,
    "summaries_present": true,
    "summary_count": 2,
    "metrics": [
      {
        "name": "promptguard_attack_detect_rate",
        "value": 0.20,
        "threshold": 0.10,
        "pass": false
      }
    ]
  },
  "external_all_pass": false
}
```

Consumers should read `gates.*` first when available and treat top-level mirrors as convenience only.

---

## Typical lifecycle

Typical pipeline flow:

- `PULSE_safe_pack_v0/tools/run_all.py` writes the status artifact.
- Optional augmentation may add derived metrics or external summaries.
- `PULSE_safe_pack_v0/tools/check_gates.py` enforces required gates on the final `status.json`.

---

## Contract evolution

This is a public-alpha contract:

- the schema is the normative compatibility boundary  
- additive fields are allowed  
- semantic changes to stable fields should be documented in the changelog and related docs  
