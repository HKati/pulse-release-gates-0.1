# Q1 Reference Groundedness Track

This page defines the shadow-first reference track for Q1 groundedness in PULSE.

The goal is to make one measurement lane concrete without pulling the repository
toward a classic library/product shape.

This track is intentionally introduced in small, separable steps:

1. artefact contract
2. example artefact
3. track overview
4. deterministic runner
5. tests
6. optional shadow fold-in

## Current status

Current scope:

- schema contract exists:
  `schemas/metrics/q1_groundedness_summary_v0.schema.json`
- example artefact exists:
  `examples/q1_groundedness_summary.example.json`

Not added yet:

- runner
- `run_all.py` integration
- gate promotion
- policy changes

## Contract

The canonical schema title is:

`Q1 Reference Groundedness Summary Contract (v0)`

This contract is artifact-first.

It defines the summary produced by a deterministic reference run, not a service,
not a library API, and not a live evaluation endpoint.

Core fields:

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

## Example artefact

A minimal example artefact is provided at:

`examples/q1_groundedness_summary.example.json`

It is intended for:

- schema consumers
- future tests
- future runner validation
- human readers trying to understand the contract quickly

The provenance path inside the example is illustrative for now.
The concrete input-manifest path will be finalized with the runner PR.

## Semantics

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

Any future promotion into release gating should happen only after:

- runner stability
- fixture coverage
- repeatable outputs
- clear fold-in semantics

## Why this exists

PULSE is strongest when findings become explicit release artefacts.

This reference track exists to reduce the “framework scaffold” feeling by making
one measurement lane concrete while preserving the repo’s current character:

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
- a replacement for the existing core/status/gate triad

## Planned next steps

Follow-up work for this track should proceed in this order:

1. deterministic runner
2. smoke / contract tests
3. optional shadow fold-in into reporting surfaces
4. only then, consider promotion discussion

## References

- `schemas/metrics/q1_groundedness_summary_v0.schema.json`
- `examples/q1_groundedness_summary.example.json`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/quality_ledger.md`
