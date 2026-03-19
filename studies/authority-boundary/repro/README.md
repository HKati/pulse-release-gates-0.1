# Authority Boundary Study — Reproduction Notes

This directory contains the minimal reproduction surface for the
authority-boundary study.

It is non-normative. Canonical release semantics remain defined by the
schema, policy, evaluator, status artifact, and CI entrypoint named in
the study root README.

---

## Execution Context

Run the commands below from the repository root.

The command paths intentionally mirror the current CI helper layout
under `tools/` and `PULSE_safe_pack_v0/tools/`.

---

## Canonical Study Pin

```text
schema: schemas/status/status_v1.schema.json
policy file: pulse_gate_policy_v0.yml
policy slice: core_required
evaluator: PULSE_safe_pack_v0/tools/check_gates.py
```

---

## Canonical Execution Order

For schema-valid fixtures, use this order:

1. Validate the fixture against the status v1 schema.
2. Derive the required gate list from the pinned policy slice.
3. Evaluate gates with check_gates.py.
4. Record exit code and stdout/stderr.

For the schema-invalid fixture, stop at step 1. Do not treat direct
gate-evaluator output as canonical for that case.

---

## Command Template

```bash
SCHEMA="schemas/status/status_v1.schema.json"
POLICY="pulse_gate_policy_v0.yml"
POLICY_SET="core_required"
STATUS="studies/authority-boundary/repro/cases/core_pass.status.json"

REQ_STR="$(python tools/policy_to_require_args.py --policy "$POLICY" --set "$POLICY_SET" --format space)"
read -r -a REQ <<< "$REQ_STR"

python tools/validate_status_schema.py \
  --schema "$SCHEMA" \
  --status "$STATUS"

python PULSE_safe_pack_v0/tools/check_gates.py \
  --status "$STATUS" \
  --require "${REQ[@]}"
```

---

## Fixtures and Expected Outcomes

| Fixture | Schema valid | Gate evaluation | Expected exit | Canonical meaning |
|--------|--------------|----------------|--------------|-------------------|
| repro/cases/core_pass.status.json | yes | yes | 0 | all required gates PASS |
| repro/cases/core_missing_q4.status.json | yes | yes | 2 | missing required gate |
| repro/cases/core_false_q4.status.json | yes | yes | 1 | present-but-false required gate |
| repro/cases/schema_invalid_non_boolean_gate.status.json | no | no | n/a | schema boundary failure |
| repro/cases/core_diag_variant_a.status.json | yes | yes | 0 | PASS with favorable diagnostics |
| repro/cases/core_diag_variant_b.status.json | yes | yes | 0 | PASS with adverse diagnostics |

---

## Non-Override Pair Check

The canonical C5 comparison is:

- repro/cases/core_diag_variant_a.status.json
- repro/cases/core_diag_variant_b.status.json

Their gates objects must remain identical. Only non-authoritative
layers may differ.

Optional verification:

```bash
python - <<'PY'
import json
from pathlib import Path

a = json.loads(Path("studies/authority-boundary/repro/cases/core_diag_variant_a.status.json").read_text())
b = json.loads(Path("studies/authority-boundary/repro/cases/core_diag_variant_b.status.json").read_text())

assert a["gates"] == b["gates"]
print("OK: normative gates are identical across diagnostic variants")
PY
```

---

## Canonical Observables

Use these as the primary observables for this study:

- schema validation success/failure
- derived required gate list for core_required
- check_gates.py exit code
- check_gates.py stdout/stderr

Human-readable renderers may be useful for inspection, but they are not
the canonical oracle for study conclusions.

---

## Notes

If the schema, policy file, or evaluator behavior changes, this file
must be reviewed for drift.

If a future study pins a different policy slice, state that change
explicitly here and in claims_to_checks.md.

schema_invalid_non_boolean_gate.status.json intentionally omits
policy-resolution metadata so it cannot be mistaken for a canonical
gate-evaluation case when schema validation is skipped.
