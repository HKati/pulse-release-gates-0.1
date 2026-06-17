# Recorded release-evidence verifier v0

## Purpose

This document defines the recorded release-evidence verifier prerequisite surface for release-grade materialization.

The verifier checks whether candidate detector materialization artifacts, canonical external summaries, and refusal-delta evidence are sufficiently bound to:

    run identity
    → subject binding
    → declared policy context
    → trusted provenance expectations
    → raw evidence digest
    → expected gate materialization relations

The verifier is prerequisite-only.

It does not compute release authority.
It does not replace `check_gates.py`.
It does not change `status.json` semantics.
It does not promote diagnostic or reader surfaces into release authority.

## Status

- stage: implemented prerequisite checker
- normative: false
- authority role: prerequisite evidence-binding checker
- tool: `PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py`
- test coverage: `tests/test_check_recorded_release_evidence_v0.py`
- tools-test coverage: `ci/tools-tests.list`
- output artifact: `PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json`
- release-required fold-in status: not enabled in this step

## Why this exists

`--release-grade-materialized` must remain fail-closed until release-required detector materialization, canonical external summary, and refusal-delta artifacts are verified rather than merely declared.

Local JSON files can exist and still be wrong.

The missing step was not another dashboard or summary.
The missing step was a machine-readable verifier that proves candidate artifacts are:

- present
- digest-bound
- subject-bound
- run-bound
- policy-bound
- provenance-checked
- raw-evidence-bound
- relation-bound to the declared release-required gates

## Inputs

The verifier consumes:

- `release_evidence_input_manifest_v0.json`
- repository-relative candidate artifact paths declared in that manifest
- repository-relative raw evidence paths declared inside those candidate artifacts

The manifest remains the declaration surface.
The verifier answers whether those declarations are actually satisfied.

## Candidate artifact minimum shape

Each candidate artifact is expected to provide at least:

- `schema_version`
- `run_identity.git_sha`
- `run_identity.run_key`
- `run_identity.run_mode`
- `subject_binding.git_sha`
- `subject_binding.run_key`
- `policy_binding.policy_set`
- `policy_binding.policy_sha256`
- `provenance.trusted_producer`
- `raw_evidence_binding.path`
- `raw_evidence_binding.sha256`
- `required_for_gates[]`

The verifier reads the candidate artifact itself.
It does not trust the manifest alone.

## Verification path

For every candidate evidence item marked `verification_required=true`, the verifier checks:

1. artifact presence
2. artifact sha256 against `expected_sha256`
3. `schema_version` match
4. `run_identity` match
5. `subject_binding` match
6. `policy_binding` match
7. trusted producer requirement when declared
8. raw evidence presence
9. raw evidence sha256 match
10. `required_for_gates` match

Then it checks the declared relation bindings:

- `artifact_to_subject`
- `artifact_to_gate`

Then it checks gate materialization admissibility:

- candidate evidence IDs are verified
- relation binding IDs are satisfied
- `expected_value=true`
- `policy_relation=release_required`
- `materialization_allowed_without_verifier=false`

## Output artifact

The verifier writes:

    PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json

Minimum output contents:

- report schema/version
- verifier status: `verified | failed`
- manifest path/digest/schema version
- run identity
- subject
- policy binding
- registry binding when present
- per-evidence verification results
- per-relation verification results
- per-gate admissibility results
- verified subject summary
- fail-closed error list

## Authority boundary

The verifier is not release authority.

Its role is:

    candidate detector/external/refusal artifact
    → recorded evidence verification
    → admissibility report
    → later release-grade materialization input

The normative release decision remains:

    recorded release evidence
    → status.json
    → declared gate policy
    → workflow-effective required gate set
    → check_gates.py
    → primary CI allow/block decision

## CLI

Example:

```bash
python PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py \
  --manifest PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json \
  --repo-root . \
  --out-json PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

Success output:

    OK: recorded release-evidence verification satisfied

Failure output:

    ERRORS (fail-closed):
      - ...

## Non-goals

This verifier is not:

- a new release gate
- a replacement for `check_gates.py`
- a replacement for `status.json`
- a second release-decision engine
- automatic promotion of detector/external/refusal artifacts into release-required truth values
- a policy override

## Follow-up

A later PR may allow `--release-grade-materialized` to fold only verifier-admitted evidence into release-required gate booleans.

That later step must remain:

- policy-derived
- explicit
- fail-closed
- non-shadow
- non-reader-authoritative
