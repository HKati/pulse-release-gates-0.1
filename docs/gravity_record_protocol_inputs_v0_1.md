# Gravity Record Protocol Inputs v0.1

This page defines the **raw input bundle** contract used to build a
`gravity_record_protocol_v0_1` artifact.

This is producer-facing: a pipeline, simulator, or measurement harness can emit
this bundle and have it validated fail-closed before we build the contract artifact.

## Files

- Schema: `schemas/gravity_record_protocol_inputs_v0_1.schema.json`
- Contract checker: `scripts/check_gravity_record_protocol_inputs_v0_1_contract.py`
- Builder (raw → contract artifact): `scripts/build_gravity_record_protocol_v0_1.py`

## Minimal contract

Top-level:
- `source_kind` (enum): `demo | measurement | simulation | pipeline | manual | missing`
- `cases` (array, min 1)

Each case:
- `case_id` (string, non-empty)
- `stations` (array, **min 2**)
- `profiles` (object)

Profiles:
- required: `profiles.lambda`, `profiles.kappa`
- optional: `profiles.s`, `profiles.g`

Profile encoding supports two forms (to keep migration flexible):
1) **Status form**
   - `{ "status": "PASS|FAIL|MISSING", "points": [...] }`
   - If `status=PASS`, `points` must be a non-empty array.
2) **Points-only form**
   - `{ "points": [...] }`
   - Interpreted as `status=PASS`.

Points:
- `r`: number or non-empty string label
- `value`: finite number
- Constraints:
  - lambda: `value > 0`
  - kappa: `0 <= value <= 1`
- Optional:
  - `uncertainty` (>=0)
  - `n` (>=0 integer)

## Validation (local)

Validate a raw bundle:

```bash
python scripts/check_gravity_record_protocol_inputs_v0_1_contract.py \
  --in PULSE_safe_pack_v0/fixtures/gravity_record_protocol_v0_1.raw.demo.json
