# Q1 Reference Groundedness Track

This page defines the shadow-first reference track for Q1 groundedness in PULSE.

The goal is to make one measurement lane concrete without pulling the
repository toward a classic library / package / service shape.

This track is intentionally artifact-first and introduced in separable steps:

1. schema contract
2. example summary artefact
3. track overview
4. deterministic runner
5. checked-in input manifest
6. checked-in labels fixture
7. smoke / integrity / golden-path tests
8. optional shadow fold-in later

## Current status

Current state on `main`:

- schema contract exists:
  `schemas/metrics/q1_groundedness_summary_v0.schema.json`
- deterministic runner exists:
  `PULSE_safe_pack_v0/tools/build_q1_reference_summary.py`
- checked-in input manifest exists:
  `examples/q1_reference_input_manifest.json`
- checked-in labels fixture exists:
  `examples/q1_reference_labels.pass_120.jsonl`
- checked-in summary example exists:
  `examples/q1_groundedness_summary.example.json`
- checked-in smoke / regression tests exist:
  - `tests/test_build_q1_reference_summary.py`
  - `tests/test_q1_reference_input_manifest_example.py`
  - `tests/test_q1_reference_fixture_integrity.py`
  - `tests/test_q1_reference_golden_path.py`

Not added yet:

- `run_all.py` integration
- reporting-surface fold-in
- gate promotion
- policy changes

## Contract

The canonical schema title is:

`Q1 Reference Groundedness Summary Contract (v0)`

This contract is artifact-first.

It defines the summary produced by a deterministic reference run, not a
service, not a library API, and not a live evaluation endpoint.

Core fields include:

- `spec_id`
- `spec_version`
- `run_id`
- `created_utc`
- `n`
- `score`
- `threshold`
- `pass`
- `method`
- `provenance`

## Checked-in artefacts

The checked-in Q1 reference lane is now anchored by these artefacts:

- input manifest:
  `examples/q1_reference_input_manifest.json`
- labels fixture:
  `examples/q1_reference_labels.pass_120.jsonl`
- summary example:
  `examples/q1_groundedness_summary.example.json`

These artefacts are intended to stay deterministic, checked-in, and
self-contained.

The current checked-in fixture is a canonical 120-row pass fixture used for:

- schema consumers
- deterministic rebuilds
- regression tests
- provenance integrity checks
- human readers trying to understand the lane quickly

The provenance path inside the checked-in summary example is no longer
illustrative-only; it now points at the checked-in manifest and labels fixture.

## Deterministic semantics

This track is currently:

- deterministic
- artifact-first
- shadow-first
- non-normative

That means:

- it does not gate shipping yet
- it does not modify the required gate set
- it does not change `check_gates.py`
- it does not change the status contract yet
- it does not promote Q1 reference output into normative release policy

The current reference decision rule is:

1. compute `grounded_rate` over eligible examples
2. compute Wilson lower bound at `alpha = 0.05`
3. PASS iff `n_eligible >= 100` and `wilson_lower_bound >= 0.85`
4. FAIL otherwise

## Regression guards

The checked-in artefact chain is protected by focused tests:

- runner smoke:
  `tests/test_build_q1_reference_summary.py`
- manifest example smoke:
  `tests/test_q1_reference_input_manifest_example.py`
- fixture integrity smoke:
  `tests/test_q1_reference_fixture_integrity.py`
- golden-path smoke:
  `tests/test_q1_reference_golden_path.py`

Together these lock down the chain:

`manifest -> labels fixture -> runner -> summary example`

This is intentional.

The purpose is to keep the lane concrete without drifting into package /
service / productization work.

## Why this exists

PULSE is strongest when findings become explicit release artefacts.

This reference track exists to reduce the “framework scaffold” feeling by
making one measurement lane concrete while preserving the repo’s current
character:

- deterministic
- fail-closed where normative
- artifact-first
- governance-aware
- shadow-capable

## Non-goals

This track is not:

- a package extraction effort
- a hosted evaluation service
- a generic library rewrite
- automatic promotion into normative release gates
- a replacement for the existing core / status / gate triad

## Next steps

Follow-up work for this track should proceed in this order:

1. optional shadow fold-in into reporting surfaces
2. observe stability of the checked-in artefact chain over time
3. only then, discuss whether any promotion is justified
4. keep policy / normative triad unchanged unless there is a compelling reason

## References

- `schemas/metrics/q1_groundedness_summary_v0.schema.json`
- `PULSE_safe_pack_v0/tools/build_q1_reference_summary.py`
- `examples/q1_reference_input_manifest.json`
- `examples/q1_reference_labels.pass_120.jsonl`
- `examples/q1_groundedness_summary.example.json`
- `tests/test_build_q1_reference_summary.py`
- `tests/test_q1_reference_input_manifest_example.py`
- `tests/test_q1_reference_fixture_integrity.py`
- `tests/test_q1_reference_golden_path.py`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/quality_ledger.md`
