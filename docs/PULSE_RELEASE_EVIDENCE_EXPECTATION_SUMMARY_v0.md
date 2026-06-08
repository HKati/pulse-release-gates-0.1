# PULSE Release Evidence Expectation Summary v0

## Status

Reader / diagnostic summary surface.

This document describes the release evidence expectation summary artifact.

It is not release authority.

It does not verify evidence.

It does not satisfy relation bindings.

It does not materialize gates.

It does not write `status.json`.

It does not reopen `--release-grade-materialized`.

It does not replace `check_gates.py`.

## Purpose

The release evidence expectation summary makes the pre-materialization gap visible.

It reads a valid `release_evidence_verifier_report_v0.json` artifact and summarizes which expected evidence, relation, and gate-materialization states remain pending, missing, mismatched, or unverified.

The summary is a reader surface over the fail-closed verifier report.

It does not create release permission.

## Tool

The builder is:

```text
PULSE_safe_pack_v0/tools/build_release_evidence_expectation_summary_v0.py
```

Example command:

```bash
python PULSE_safe_pack_v0/tools/build_release_evidence_expectation_summary_v0.py \
  --report PULSE_safe_pack_v0/artifacts/release_evidence_verifier_report_v0.json \
  --out PULSE_safe_pack_v0/artifacts/release_evidence_expectation_summary_v0.json
```

## Schema

The schema is:

```text
schemas/release_evidence_expectation_summary_v0.schema.json
```

Example:

```text
examples/release_evidence_expectation_summary_v0.failed.example.json
```

## Output

The summary records:

- source verifier report path
- source verifier report SHA-256 digest
- source verifier decision
- evidence input count
- verified artifact count
- relation binding count
- gate materialization count
- failed check count
- warning count
- classified pre-materialization gaps
- authority boundary flags

## Readiness State

The summary uses:

```text
NOT_READY
REPORT_VERIFIED_NON_AUTHORITY
```

`NOT_READY` means the source verifier report still has failed checks or is not verified.

`REPORT_VERIFIED_NON_AUTHORITY` means the source verifier report is verified, but the summary remains non-authoritative.

The summary does not produce PASS, ALLOW, or release permission.

## Pre-materialization Gap Classes

The summary classifies failed checks into gap kinds such as:

- `candidate_evidence_not_verified`
- `missing_candidate_evidence`
- `digest_mismatch`
- `pending_relation_binding`
- `pending_gate_materialization`
- `missing_gate_candidate_evidence`
- `no_candidate_evidence`
- `no_verified_relation_bindings`
- `no_gate_materialization`
- `other_failed_check`

These are descriptive diagnostic classes.

They do not materialize gates.

## Authority Boundary

The artifact records an explicit authority boundary:

```text
is_release_authority = false
materializes_gates = false
writes_status_json = false
reopens_release_grade_materialization = false
replaces_check_gates = false
```

## Relation to PULSEmech

PULSEmech release authority remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

The expectation summary sits before materialization.

It only helps reveal what remains unverified or unsatisfied.

## Minimal Anchor

The expectation summary makes pending relations visible.

It does not satisfy them.

It makes the pre-materialization gap readable.

It does not close the gap.

## Pre-materialization pipeline contract

The pre-materialization pipeline contract verifies the reader-only chain:

```text
release_evidence_input_manifest_v0
→ release_evidence_verifier_report_v0
→ release_evidence_expectation_summary_v0
