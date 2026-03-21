# Parameter Golf submission evidence v0

This note defines a **shadow-only, CI-neutral** companion contract for the
OpenAI Parameter Golf challenge.

## Why this layer exists

Parameter Golf submissions bundle several kinds of claims that are easy for
humans to understand informally but harder to compare consistently across many
PRs:

- artifact accounting (`code_bytes`, compressed model bytes, total bytes),
- evaluation mode details (standard / sliding window / test-time training),
- wallclock claims,
- optional statistical-evidence metadata for record attempts.

The aim here is modest:
make those claims **machine-readable** without changing PULSE release gates and
without forcing a heavy framework into the counted challenge path.

## Contract shape

Canonical schema:
`schemas/parameter_golf_submission_evidence_v0.schema.json`

Typical fields:
- `submission_type`
- `artifact.*`
- `train.*`
- `evaluation.*`
- `stats.*`
- `provenance.*`

## Verifier

Use:
```bash
python tools/verify_parameter_golf_submission_v0.py \
  --evidence examples/parameter_golf_submission_evidence_v0.example.json
```

Strict mode:
```bash
python tools/verify_parameter_golf_submission_v0.py \
  --evidence examples/parameter_golf_submission_evidence_v0.example.json \
  --strict
```

## Intended behavior

- malformed JSON or schema violations => invalid
- semantic inconsistencies => warnings by default
- `--strict` upgrades warnings to non-zero exit

Examples of semantic warnings:
- `total_bytes_int8_zlib != code_bytes + model_bytes_int8_zlib`
- artifact exceeds its own declared limit
- sliding-window mode without stride
- `p_value` present but `n_runs` absent
- record submission with no log list and no exemption reason

## Boundary

This layer is **not normative** for PULSE release gating.
It is designed as a companion surface for an external challenge, not as a new
required gate set.
