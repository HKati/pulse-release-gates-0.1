# Authority Boundary Study

This directory contains a focused, reproducible study of one architectural claim:

> In LLM-mediated release workflows, generation and final release authority should be separated.

The study is built on top of PULSE mechanics. It is not a replacement for them, and it does not redefine them.

## Status

This directory is a **research / reproduction surface**.

It is:

- non-authoritative for shipping decisions,
- non-normative for CI pass/fail semantics,
- intended to make a specific systems claim inspectable and testable.

It must not silently change release meaning.

## Normative Boundary

Core release semantics remain defined by the existing PULSE release path
and its authority-bearing artifacts:

- `schemas/status/status_v1.schema.json` — normative `status.json`
  compatibility boundary
- `pulse_gate_policy_v0.yml` — canonical policy source for required /
  advisory gate sets and their enforcement semantics
- `PULSE_safe_pack_v0/tools/check_gates.py` — fail-closed gate evaluator
- `PULSE_safe_pack_v0/artifacts/status.json` — evaluated status artifact
- `.github/workflows/pulse_ci.yml` — CI entrypoint that validates
  `status.json` against the active schema, selects the active policy set,
  derives the enforced required gate list from `pulse_gate_policy_v0.yml`,
  and passes that list to `check_gates.py`

For explanatory contract docs, read:

- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`

This study may analyze, restate, or test those mechanics, but it does
not override them.

It must not validate against stale schema assumptions or stale
required-gate assumptions after schema or policy changes.

## Research Question

Can release-critical decisions in LLM-mediated workflows be stabilized by externalizing final authority into a deterministic evaluator over explicit artifacts?

## Working Hypothesis

PULSE gains release reliability not from rhetoric, prompt style, or model confidence, but from an explicit authority boundary enforced through:

- artifact-based evaluation,
- fail-closed gate semantics,
- deterministic interpretation of normative gate state.

## Operational Invariants

The study is organized around three invariants.

### 1. Reproducibility under fixed artifacts

For fixed normative artifact state, schema version, evaluator version, and gate policy, repeated evaluation yields the same release decision.

### 2. Fail-closed gate semantics

If a required gate is missing, invalid, or not literal `true`, the release decision is `FAIL`.

### 3. Non-override of diagnostics

Diagnostics, summaries, overlays, and auxiliary signals may inform analysis, but they must not change the final release decision unless they are explicitly promoted into the normative gate set by versioned schema/policy/evaluator change.

## What Belongs Here

This study surface may contain:

- a concise paper draft,
- a claims-to-checks mapping,
- minimal repro fixtures,
- expected outcomes for each check,
- notes needed to reproduce the study claim.

## What Does Not Belong Here

The following do **not** belong here:

- ad hoc changes to release semantics,
- undocumented required gates,
- UI-only interpretations presented as shipping authority,
- diagnostic signals treated as authoritative without explicit promotion,
- prose that conflicts with the canonical contract in `docs/`.

## Intended Layout

Files will be added incrementally.

Planned contents:

- `paper.md`
- `claims_to_checks.md`
- `repro/`

## Relation to the Repository

This folder exists to keep a clean separation between:

- **core PULSE release mechanics**, and
- **reproducible research built on top of those mechanics**.

That separation is deliberate.  
PULSE release control should remain grounded in explicit artifacts and policy, not in narrative interpretation.
