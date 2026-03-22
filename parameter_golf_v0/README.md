# Parameter Golf v0 — shadow-only evidence companion

This directory is intentionally **not** part of the normative PULSE
release-gating path.

Its purpose is to demonstrate a small, machine-readable evidentiary
surface for OpenAI Parameter Golf submissions without changing the
counted submission path, without introducing new PULSE required gates,
and without turning PULSE into the challenge itself.

## What this is

This companion is a **shadow-only, diagnostic** layer.

It is designed to make a submission's evidentiary surface easier to
inspect by separating three concerns:

1. **evidence shape**
   - what a minimal machine-readable evidence artifact looks like

2. **evidence validation**
   - whether that artifact is schema-valid
   - what semantic warnings it raises

3. **review rendering**
   - how the same evidence can be collapsed into a smaller,
     reviewer-facing receipt

## Why this exists

Parameter Golf already asks participants to provide meaningful evidence:
a PR-based submission, a `README.md`, a `submission.json`, training logs,
and runnable code. It also already depends on reproducibility, artifact
accounting, evaluation metadata, and statistical evidence for record
claims.

What is still missing upstream is not evidence in principle, but a small
machine-readable surface that makes those claims easier to inspect
consistently.

This companion exists to prototype that surface in a way that is:

- schema-first,
- audit-friendly,
- CI-neutral,
- non-blocking,
- explicitly non-normative.

## Current v0 scope

The current v0 companion consists of:

- one evidence contract:
  - `schemas/parameter_golf_submission_evidence_v0.schema.json`

- one verifier:
  - `tools/verify_parameter_golf_submission_v0.py`

- one example evidence artifact:
  - `examples/parameter_golf_submission_evidence_v0.example.json`

- one review-receipt renderer:
  - `tools/render_parameter_golf_review_receipt_v0.py`

- one example review receipt:
  - `examples/parameter_golf_submission_review_receipt_v0.example.json`

- one deterministic roundtrip checker:
  - `tools/check_parameter_golf_review_receipt_roundtrip_v0.py`

## What the evidence contract covers

The v0 evidence artifact is intentionally small. It covers:

- artifact accounting
- train metadata
- evaluation metadata
- statistical evidence
- provenance

The v0 contract is not trying to encode the entire challenge. It is
trying to make a minimal review surface explicit.

## What the review receipt is for

The review receipt is a **derived artifact** rendered from evidence.

Its job is not to replace the evidence JSON. Its job is to present a
smaller reviewer-facing surface containing:

- schema-valid / invalid state
- warning summary
- artifact accounting visibility
- evaluation-mode visibility
- training/evaluation wallclock visibility
- statistical-evidence visibility
- explicit shadow-only boundary markers

This is meant to reduce review friction without changing any counted or
normative path.

## Quick start

### 1. Validate the example evidence artifact

```bash
python tools/verify_parameter_golf_submission_v0.py \
  --evidence examples/parameter_golf_submission_evidence_v0.example.json \
  --json
```

### 2. Render a review receipt from the example evidence

```bash
python tools/render_parameter_golf_review_receipt_v0.py \
  --evidence examples/parameter_golf_submission_evidence_v0.example.json \
  --output /tmp/parameter_golf_review_receipt.json
```

### 3. Check the example roundtrip

```bash
python tools/check_parameter_golf_review_receipt_roundtrip_v0.py
```

The roundtrip checker verifies that:

example evidence  
→ receipt renderer  
→ committed example review receipt  

remains deterministic.

## Normative boundary

This work remains strictly shadow-only.

It does not:

- add new PULSE required gates
- mutate status.json
- change CI outcomes
- redefine Parameter Golf rules
- create a new counted submission path
- promote evidence validity into release authority

Missing, malformed, or schema-invalid evidence may be reported as
invalid by the verifier or renderer, but this must not change PULSE
release outcomes unless a future policy explicitly promotes it.

## Non-goals

This companion is not trying to:

- become a Parameter Golf replacement
- enforce upstream challenge rules from inside PULSE
- standardize every possible submission variation
- make review decisions automatically
- harden a diagnostic artifact into authority by convention drift

## Current value of the prototype

At v0, the companion demonstrates three concrete things:

- a submission's evidentiary surface can be expressed in a small,
  machine-readable artifact

- that artifact can be validated and summarized without changing the
  underlying challenge path

- a reviewer-facing receipt can be generated deterministically from the
  same evidence

That is enough to support upstream discussion with a concrete artifact,
rather than only a conceptual proposal.
