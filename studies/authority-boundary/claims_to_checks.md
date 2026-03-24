# Authority Boundary Study — Claims to Checks

This document maps the study claims to concrete reproduction checks.

It is non-normative. Core release semantics remain anchored to the
current schema, policy, evaluator, status artifact, and CI entrypoint.

---

## Boundary Anchors

Authority-bearing inputs for this study are:

- `schemas/status/status_v1.schema.json`
- `pulse_gate_policy_v0.yml`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `PULSE_safe_pack_v0/artifacts/status.json`
- `.github/workflows/pulse_ci.yml`

Explanatory docs may clarify these mechanics, but they do not replace
them.

---

## Study Policy Pin

Each repro check must declare the policy slice it exercises.

For the initial minimal fixture set, pin:

```text
policy file: pulse_gate_policy_v0.yml
policy slice: core_required

Current core_required gates:

pass_controls_refusal
pass_controls_sanit
sanitization_effective
q1_grounded_ok
q4_slo_ok
```

This keeps the first study fixtures small and aligned with the current
minimal stable public example.

---

## Fixture Hygiene

Unless a claim explicitly targets schema invalidity, each fixture should
remain valid against schemas/status/status_v1.schema.json.

That means the initial minimal fixtures should include at least:

- version
- created_utc
- metrics.run_mode
- gates

and all values under gates should be booleans.

---

## Check Execution Order

Unless a claim explicitly targets schema invalidity, evaluate fixtures in
this order:

1. Validate the candidate status.json against  
   `schemas/status/status_v1.schema.json`.

2. Select the declared policy slice from  
   `pulse_gate_policy_v0.yml`.

3. Run  
   `PULSE_safe_pack_v0/tools/check_gates.py`  
   with the declared required gate list.

4. Record exit code and stdout/stderr as the observable outcome.

Canonical exit-code meaning from check_gates.py:

- `0` = all required gates PASS  
- `1` = at least one required gate is present but not literal true  
- `2` = invalid/missing status OR one or more required gates are missing  

---

## Claims and Checks

### C1. Reproducibility under Fixed Artifacts

**Claim**

For fixed normative gate state, schema version, evaluator version, and
policy slice, repeated evaluation yields the same release decision.

**Minimal fixtures**

- repro/cases/core_pass.status.json

**Check**

- Hold the fixture bytes fixed.
- Hold the schema file fixed.
- Hold the policy slice fixed (core_required).
- Re-run schema validation and gate evaluation multiple times.

**Expected result**

- Schema validation succeeds each time.
- check_gates.py returns 0 each time.
- The PASS/FAIL outcome is identical across repetitions.

---

### C2. Fail-Closed on Missing Required Gate

**Claim**

If a required gate is absent from an otherwise schema-valid
status.json, release evaluation fails closed.

**Minimal fixtures**

- repro/cases/core_missing_q4.status.json

**Check**

- Keep the file schema-valid at the top level.
- Omit q4_slo_ok from gates.
- Evaluate against the pinned core_required set.

**Expected result**

- Schema validation succeeds.
- check_gates.py returns 2.
- The observable result reports a missing required gate.

**Reason**

Missing required gates are a policy/evaluator failure, not necessarily a
schema failure.

---

### C3. Fail on Present-but-False Required Gate

**Claim**

If a required gate is present but set to literal false, release
evaluation fails.

**Minimal fixtures**

- repro/cases/core_false_q4.status.json

**Check**

- Keep all required keys present.
- Set q4_slo_ok: false.
- Evaluate against the pinned core_required set.

**Expected result**

- Schema validation succeeds.
- check_gates.py returns 1.
- The observable result reports q4_slo_ok as a FAIL gate with value false.

---

### C4. Schema Boundary Precedes Gate Interpretation

**Claim**

A status.json that violates the normative schema must be treated as
invalid at the schema boundary. Study conclusions must not rely on
direct evaluator behavior over schema-invalid fixtures.

**Minimal fixtures**

- repro/cases/schema_invalid_non_boolean_gate.status.json

**Check**

- Set a gate value to a non-boolean value (e.g. "true" as a string).
- Validate against schemas/status/status_v1.schema.json.

**Expected result**

- Schema validation fails.
- The fixture is marked schema-invalid and is not used as a canonical
  release-evaluation case.

**Reason**

Under the current schema, gate values are boolean-typed.

---

### C5. Non-Override of Diagnostics

**Claim**

Diagnostics, summaries, overlays, meta.*, external.*, and top-level
convenience mirrors do not change the release decision when the
normative gates object is unchanged.

**Minimal fixtures**

- repro/cases/core_diag_variant_a.status.json
- repro/cases/core_diag_variant_b.status.json

**Check**

- Keep the gates object structurally identical between both fixtures.
- Vary only non-authoritative fields such as:
  - external.*
  - meta.*
  - top-level convenience mirrors
  - narrative summaries / rationale text
- Evaluate both fixtures against the same pinned policy slice.

**Expected result**

- Both fixtures pass schema validation.
- Both runs return the same exit code.
- Both runs produce the same PASS/FAIL outcome.

---

### C6. Decision Impact Requires Explicit Promotion

**Claim**

A diagnostic signal may affect release decisions only after explicit
promotion into the normative path via schema/policy/evaluator change.

**Minimal fixtures**

- none in the initial minimal set

**Check**

- Compare current evaluation before and after introducing a new
  diagnostic-only signal that is not part of the pinned required gate set.

**Expected result**

- Under the current pinned policy slice, no decision change occurs.
- A decision change is legitimate only after an explicit, versioned
  promotion path is documented and implemented.

---

## Planned Initial Fixture Set

```text
repro/cases/
  core_pass.status.json
  core_missing_q4.status.json
  core_false_q4.status.json
  schema_invalid_non_boolean_gate.status.json
  core_diag_variant_a.status.json
  core_diag_variant_b.status.json
```

---

## Notes

This file is a study mapping, not a release contract.

If the schema, policy file, or evaluator behavior changes, this file
must be reviewed for drift.

If a future study uses a different policy slice than core_required,
that choice must be stated explicitly in the fixture notes.
