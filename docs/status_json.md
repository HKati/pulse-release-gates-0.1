# The PULSE status artefact (`status.json`)

> Central machine-readable artefact for one PULSE run.

PULSE safe-packs produce a single machine-readable status artefact for each run:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

This file is the anchor for:

CI enforcement,

derived-signal augmentation,

human-readable reporting,

audit / archival / diffing.

A single status.json should correspond to exactly one concrete run
and one release candidate / model/service configuration.

---

## 1. Source of truth

The stable public contract is defined by:

schemas/status/status_v1.schema.json

That schema currently requires the top-level fields:

version

created_utc

metrics

gates

and it requires metrics.run_mode to be one of:

demo

core

prod

For the concise public contract, see STATUS_CONTRACT.md.

This page is the fuller walkthrough.

Local validation helper:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

---

## 2. Authority boundary

The current repository model uses a single final status.json artefact,
but its fields do not all have the same semantic role.

### Normative authority

The normative release-relevant surface is:

status["gates"]

interpreted in the context of:

the active policy / workflow-required gate set

status["metrics"]["run_mode"]

### Required contract / provenance anchors

These fields are still part of the public contract and must validate:

status["version"]

status["created_utc"]

status["metrics"]

status["gates"]

However:

version and created_utc are not themselves gate outcomes

they are required contract / provenance fields, not release decisions

### Non-authoritative / descriptive layers

These are additive and non-normative unless a future policy explicitly promotes them:

top-level convenience mirrors

external

meta.*

renderer-friendly summaries

provenance hints and reproducibility hints under metrics.*

### No top-level decision authority

status.json should not be treated as having a separate top-level
authority decision field that overrides gates.*.

If a human-readable summary, badge, report card, CLI, or workflow wants an
overall decision such as PASS / FAIL / STAGE-PASS, that value should be
derived from:

gates.*

the required gate set

and the relevant policy / workflow context

It must not silently replace them.

---

## 3. Artefact lifecycle

Typical flow:

PULSE_safe_pack_v0/tools/run_all.py writes the baseline status.json.

PULSE_safe_pack_v0/tools/augment_status.py may enrich that file with:

refusal-delta metrics and gate,

external detector summaries,

convenience mirror fields,

optional shadow-only fold-ins under meta.*.

PULSE_safe_pack_v0/tools/check_gates.py enforces the required gate set on the final status.json.

Renderers such as the Quality Ledger read the same final artefact.

If your workflow also keeps a status_baseline.json, treat it as an
intermediate artefact. The final enforcement input is still the final
status.json.

---

## 4. High-level shape

A typical layout looks like this:

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

Interpretation:

metrics describe what was measured and record useful run/provenance hints

gates describe the boolean decisions derived from those signals

top-level mirror fields are optional convenience copies for simple consumers

external is a structured home for external-detector evidence

meta.* is a good home for optional diagnostic / shadow fold-ins that improve visibility without changing release semantics

---

## 5. Required stable fields

### version

A non-empty string describing the status contract / producer version.

### created_utc

A non-empty timestamp string indicating when the artefact was created.

This is required by the current public contract, but it is not itself a
release-decision field.

### metrics

A JSON object containing measured signals and provenance hints.

At minimum, it must contain:

metrics.run_mode

### gates

A JSON object mapping gate ids to booleans.

This is the normative home for release-relevant gate outcomes.

---

## 6. Run modes

metrics.run_mode is currently one of:

demo

core

prod

The safe-pack entrypoint run_all.py selects the mode via:

CLI: --mode demo|core|prod

or environment: PULSE_RUN_MODE

Treat run_mode as important provenance and policy context.

---

## 7. metrics: measured signals and receipt-like hints

metrics is intentionally additive.

It can contain many fields beyond the required run_mode.

Important rule:

metrics.* may explain, trace, or contextualize decisions

it does not replace the normative role of gates.*

---

## 8. gates: normative release decisions

gates is the normative map of release decisions.

Strict PASS semantics:

a gate PASSES only if its value is the literal boolean true

missing required gates fail closed

---

## 9. Top-level mirrors

Convenience fields such as:

status["refusal_delta_pass"]

status["external_all_pass"]

status["external_summaries_present"]

Recommended rule:

read status["gates"][...] first

---

## 10. Optional shadow fold-ins (meta.*)

meta is a home for optional, non-normative visibility blocks.

Rules:

All-or-nothing fold-in

Source fidelity

Normative isolation

Absence is neutral

---

## 11. External detector section (external)

external distinguishes:

evidence presence

vs

aggregate pass

Important:

external_all_pass ≠ evidence exists

---

## 12. Relationship to the main tools

run_all.py → baseline

augment_status.py → enrichment

check_gates.py → enforcement

validate_status_schema.py → validation

---

## 13. Consumer guidance

Validate first

Read gates first

Treat meta as descriptive

Treat additive fields as normal

---

## 14. Contract evolution

Schema is the compatibility boundary:

schemas/status/status_v1.schema.json

Future changes must be explicit.

---

## See also:

- `STATUS_CONTRACT.md`
- `quality_ledger.md`
- `refusal_delta_gate.md`
- `RUNBOOK.md`
