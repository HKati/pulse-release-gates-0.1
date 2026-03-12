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

```text
status["gates"]
```

For release enforcement, PASS is strict:

- a gate PASSES only if its value is the literal boolean `true`
- `false`, `null`, missing values, strings, and numbers are **not** PASS
- missing required gates fail closed

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

## Optional shadow fold-ins

Some producers may copy selected fields from diagnostic / shadow artefacts into `status.json`
under `meta.*` for visibility only.

These fold-ins are:

- optional,
- additive,
- non-normative,
- and must not alter release decisions, required gate sets, or gate semantics.

### Q1 reference shadow

Recommended location:

```text
status["meta"]["q1_reference_shadow"]
```

Purpose:

Expose a compact summary of a Q1 reference summary artefact for human readers
and renderer surfaces without creating a new required gate or changing release policy.

Suggested shape:

```json
{
  "meta": {
    "q1_reference_shadow": {
      "pass": true,
      "grounded_rate": 0.94,
      "wilson_lower_bound": 0.90,
      "n_eligible": 120,
      "threshold": 0.90,
      "summary_artifact": {
        "path": "out/q1/reference_summary.json",
        "sha256": "..."
      }
    }
  }
}
```

Rules:

1. **Fold-in is all-or-nothing.**  
   If the source artefact is missing, invalid, or not parseable, omit the whole block.

2. **Source fidelity.**  
   Values in `meta.q1_reference_shadow` are copied / mapped from the source summary artefact.  
   They are not recomputed and must not introduce new release semantics.  
   `threshold` mirrors the source summary's `threshold` field and is descriptive only.

3. **Hash meaning.**  
   `summary_artifact.sha256` refers to the raw file bytes of the source summary artefact.

4. **Consumer rule.**  
   Renderers may display this block, but consumers must not treat it as normative gate evidence.

5. **Absence is neutral.**  
   Presence or absence of this block does not change PASS/FAIL, STAGE-PASS/PROD-PASS,
   or required-gate enforcement.

Non-goals:

- no changes under `gates.*`
- no `check_gates.py` behavior change
- no policy change
- no promotion
- no overall decision change

---

## Typical lifecycle

Typical pipeline flow:

- `PULSE_safe_pack_v0/tools/run_all.py` writes the baseline status artefact.
- Optional augmentation may add derived metrics, external summaries, or shadow-only fold-ins under `meta.*`.
- `PULSE_safe_pack_v0/tools/check_gates.py` enforces required gates on the final `status.json`.
- Human-readable renderers read the same final artefact.

---

## Invariants

- **Gate isolation**  
  Presence or absence of `meta.q1_reference_shadow` must not change release outcomes.

- **Read-only presentation**  
  Renderer surfaces may display the block but must not derive normative outcomes from it.

- **Source fidelity**  
  The block is a copy / mapping of selected source-summary fields, not a recomputed decision layer.

---

## Contract evolution

This is a public-alpha contract:

- the schema is the normative compatibility boundary
- additive fields are allowed
- semantic changes to stable fields should be documented in the changelog and related docs
- if any shadow fold-in is later promoted into gating, that promotion must be documented as a separate normative change
