```markdown
# The PULSE status artefact (`status.json`)

> Central machine-readable artefact for one PULSE run.

PULSE safe-packs produce a single machine-readable status artefact for each run:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

This file is the anchor for:

- CI enforcement
- derived-signal augmentation
- human-readable reporting
- audit / archival / diffing

A single status.json should correspond to exactly one concrete run and one release candidate / model/service configuration.

---

## 1. Source of truth

The stable public contract is defined by:

```text
schemas/status/status_v1.schema.json
```

That schema currently requires the top-level fields:

- version
- created_utc
- metrics
- gates

and it requires `metrics.run_mode` to be one of:

- demo
- core
- prod

For the concise public contract, see `STATUS_CONTRACT.md`.

Local validation helper:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

---

## 2. Authority boundary

The current repository model uses a single final `status.json` artefact, but its fields do not all have the same semantic role.

### Normative authority

The normative release-relevant surface is:

```text
status["gates"]
```

interpreted in the context of:

- the active policy / workflow-required gate set
- `status["metrics"]["run_mode"]`

### Required contract / provenance anchors

These fields are still part of the public contract and must validate:

- `status["version"]`
- `status["created_utc"]`
- `status["metrics"]`
- `status["gates"]`

However:

- `version` and `created_utc` are not themselves gate outcomes
- they are required contract / provenance fields, not release decisions

### Non-authoritative / descriptive layers

These are additive and non-normative unless a future policy explicitly promotes them:

- top-level convenience mirrors
- external
- `meta.*`
- renderer-friendly summaries
- provenance hints under `metrics.*`

### No top-level decision authority

`status.json` should not contain a top-level decision field overriding `gates.*`.

Any PASS / FAIL summary must be derived from:

- `gates.*`
- required gate set
- policy / workflow context

---

## 3. Artefact lifecycle

Typical flow:

1. `run_all.py` → baseline `status.json`
2. `augment_status.py` → enrichment:
   - refusal-delta metrics and gate
   - external summaries
   - mirror fields
   - shadow fold-ins (`meta.*`)
3. `check_gates.py` → enforcement
4. renderers (e.g. Quality Ledger) → read final artefact

`status_baseline.json` is intermediate only.

Final authority = final `status.json`.

---

## 4. High-level shape

```json
{
  "version": "1.0.0-core",
  "created_utc": "2026-02-17T12:34:56Z",
  "metrics": {
    "run_mode": "core",
    "RDSI": 0.92,
    "git_sha": "abcdef1234...",
    "run_key": "GITHUB_RUN_ID=...|GITHUB_RUN_NUMBER=...",
    "gate_policy_path": "pulse_gate_policy_v0.yml",
    "gate_policy_sha256": "..."
  },
  "gates": {
    "q1_grounded_ok": true,
    "q4_slo_ok": true,
    "refusal_delta_pass": true,
    "external_all_pass": true,
    "external_summaries_present": false
  },
  "external": {
    "all_pass": true,
    "summaries_present": false,
    "summary_count": 0,
    "metrics": []
  },
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
  },
  "refusal_delta_pass": true,
  "external_all_pass": true,
  "external_summaries_present": false
}
```

---

## 5. Required stable fields

### version
Non-empty string.

### created_utc
Timestamp string.

### metrics
Must include:
- `metrics.run_mode`

### gates
Map of gate_id → boolean.

---

## 6. Run modes

`metrics.run_mode` ∈:

- demo
- core
- prod

### v0 meaning of `prod`

For v0, `prod` should be read as a **guarded release lane**, not as a claim that
every final production detector is already fully wired.

Current `run_all.py` behavior is intentionally asymmetric:

- `demo` and `core` start from all-true baseline gates for smoke / core paths
- `prod` starts from a fail-closed placeholder baseline until real detectors
  replace the stubs

Therefore, in v0:

- `run_mode=prod` means the run is in the guarded release lane
- it does **not** mean the lane is already a fully feature-complete, final
  production measurement lane
- this is a semantic interpretation rule for operators and maintainers, not a
  change to gate logic

---

## 7. metrics

- descriptive
- additive
- non-normative

---

## 8. gates

Normative decision layer.

Strict PASS:

```text
value === true
```

Missing → fail closed.

---

## 9. Top-level mirrors

Examples:

- `refusal_delta_pass`
- `external_all_pass`

Rule:

```text
gates first
```

---

## 10. meta.*

Rules:

- all-or-nothing
- source fidelity
- normative isolation
- absence is neutral

---

## 11. external

### Two signals:

**Presence:**
- `gates.external_summaries_present`
- `external.summaries_present`

**Aggregate:**
- `gates.external_all_pass`
- `external.all_pass`

### Critical rule:

```text
external_all_pass ≠ evidence exists
```

### Release-grade condition:

```text
external_summaries_present == true
AND
external_all_pass == true
```

---

## 12. Tools

- run_all.py → baseline
- augment_status.py → enrichment
- check_gates.py → enforcement
- validate_status_schema.py → validation

---

## 13. Consumer guidance

- validate first
- read gates first
- meta = descriptive
- do not infer presence from pass

---

## 14. Contract evolution

Boundary:

```text
schemas/status/status_v1.schema.json
```

---

## See also

- STATUS_CONTRACT.md
- quality_ledger.md
- refusal_delta_gate.md
- RUNBOOK.md
```
