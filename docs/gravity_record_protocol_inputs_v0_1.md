# Gravity Record Protocol Inputs v0.1

This page defines the **raw input bundle** contract used to build a
`gravity_record_protocol_v0_1` artifact.

This is producer-facing: a pipeline, simulator, or measurement harness can emit
this bundle and have it validated fail-closed before we build the contract artifact.

## Files

- Schema: `schemas/gravity_record_protocol_inputs_v0_1.schema.json`
- Contract checker: `scripts/check_gravity_record_protocol_inputs_v0_1_contract.py`
- Builder (raw → contract artifact): `scripts/build_gravity_record_protocol_v0_1.py`

## Diagnostics / probes (non-gating)

- [gravity_record_protocol_decodability_wall_v0_1.md](gravity_record_protocol_decodability_wall_v0_1.md) — Decodability Wall spec (v0.1): operational boundary + critical radius summary (`r_c`); produces optional diagnostic artefacts (not a CI gate).


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


```

## JSONL rawlog adapter (producer-friendly)

This repo supports a minimal JSONL “rawlog” format as a producer-facing input surface for building
a `gravity_record_protocol_inputs_v0_1` bundle.

It is intended to be:
- easy to emit from upstream measurement / simulation code,
- deterministic to rebuild,
- fail-closed when malformed (with explicit `raw_errors`).

---

### Rawlog format (JSON Lines)

One JSON object per line. Empty lines and comment lines starting with `#` are ignored.

Supported record types:

---

### 1) `meta`

Example (single JSON line):

```json
{"type":"meta","source_kind":"demo","provenance":{"generated_at_utc":"...Z","generator":"..."}}
```

Fields:
- `source_kind` (string): `demo | measurement | simulation | pipeline | manual | missing`
- `provenance.generated_at_utc` (string, ISO UTC)
- `provenance.generator` (string)

---

### 2) `station`

Example (single JSON line):

```json
{"type":"station","case_id":"case_demo_ab","station_id":"A","r_areal":100.0,"r_label":"rA"}
```

Fields:
- `case_id` (string, required)
- `station_id` (string, required; must be unique within a case)
- `r_areal` (number|null, optional; finite; bools rejected)
- `r_label` (string|null, optional; non-empty if present)

---

### 3) `point`

Example (single JSON line):

```json
{"type":"point","case_id":"case_demo_ab","profile":"lambda","r":0,"value":1.0,"uncertainty":0.0,"n":1}
```

Fields:
- `case_id` (string, required)
- `profile` (string, required): `lambda | kappa | s | g`
- `r` (number or non-empty string, required)
- `value` (finite number, required; bools rejected)
- `uncertainty` (>=0 finite number, optional)
- `n` (>=0 integer, optional)

Domain constraints (enforced at build-time):
- `lambda.value` must be `> 0`
- `kappa.value` must be in `[0, 1]`

---

## Builder

Script:
- `scripts/build_gravity_record_protocol_inputs_v0_1.py`

Demo rawlog fixture:
- `PULSE_safe_pack_v0/fixtures/gravity_record_protocol_v0_1.rawlog.demo.jsonl`

Build an inputs bundle:

```bash
python scripts/build_gravity_record_protocol_inputs_v0_1.py \
  --rawlog PULSE_safe_pack_v0/fixtures/gravity_record_protocol_v0_1.rawlog.demo.jsonl \
  --out   out/gravity_record_protocol_inputs_v0_1.json \
  --source-kind demo
```

Validate the result (fail-closed contract check):

```bash
python scripts/check_gravity_record_protocol_inputs_v0_1_contract.py \
  --in out/gravity_record_protocol_inputs_v0_1.json
```

---

## Required profiles and “missing” representation

Each case must include both `profiles.lambda` and `profiles.kappa`.

If a required profile has no points in the rawlog, the builder emits an explicit missing profile:

```json
{"status":"MISSING","points":null}
```

This representation prevents “missing required profile key” failures by emitting required profile objects explicitly (`status: "MISSING"`, `points: null`) instead of omitting the profile object entirely.

---

## Fail-closed behavior (builder)

The builder always attempts to write a JSON output bundle (even when the input is malformed), and records producer-facing issues under `raw_errors`.

Exit codes:
- `0` → bundle written **and** `raw_errors` is empty
- `2` → bundle written **and** `raw_errors` is non-empty

Important: the builder is **not** a full contract validator.  
An exit code of `0` means the raw→bundle transformation did not record producer errors, but it does **not** guarantee the output bundle satisfies the full `gravity_record_protocol_inputs_v0_1` contract (e.g. non-empty `cases`, required profiles, etc.).

For contract enforcement, always run:
- `python scripts/check_gravity_record_protocol_inputs_v0_1_contract.py --in <bundle.json>`


