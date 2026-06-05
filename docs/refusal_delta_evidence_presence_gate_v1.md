# Refusal-Delta Evidence Presence Gate v1

## Purpose

This document records the current PULSE-REF release-grade evidence-presence
behavior for `refusal_delta_evidence_present`.

The purpose is to prevent this state from passing release-grade validation:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

A passing refusal-delta result gate does not substitute for missing materialized
refusal-delta evidence.

The current repository state includes policy, profile, fixture, and regression
evidence for this behavior.

## Current status

`refusal_delta_evidence_present` is now represented in the release-grade
evidence path through current repository evidence.

Current evidence includes:

```text
pulse_gate_policy_v0.yml
PULSE_safe_pack_v0/profiles/release_grade_reference_v1.yml
tests/fixtures/release_reference_v1/missing_refusal_delta/status.json
tests/fixtures/release_reference_v1/missing_refusal_delta/expected_outcome.json
tests/fixtures/release_reference_v1/refusal_delta_evidence_present/status.json
tests/fixtures/release_reference_v1/refusal_delta_evidence_present/expected_outcome.json
tests/test_no_implicit_pass_release_grade.py
tests/test_release_reference_fixture_matrix_v1.py
```

The current negative fixture sets:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

Expected result:

```text
FAIL
```

The current positive fixture sets:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
```

Expected result:

```text
PASS
```

The fixture matrix passes fixture-specific extra required gates through:

```json
"expected_extra_required_gates": [
  "refusal_delta_evidence_present"
]
```

The release-grade reference profile records that refusal-delta evidence is
required when release-required.

## Authority boundary

The current behavior remains declared-policy based.

Release permission is produced by:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ strict gate checking
→ CI outcome
```

`refusal_delta_evidence_present` participates in release-grade validation
through declared policy, profile requirements, fixture evidence, and guard tests.

Documentation, fixtures, ledgers, manifests, audit bundles, dashboards,
summaries, and publication surfaces preserve or explain evidence state; they do
not independently authorize release.

## Core rule

Release-grade paths must not infer PASS from missing refusal-delta evidence.

The following state must fail release-grade validation:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

The required release-grade state is:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
```

## Why this gate is needed

`refusal_delta_pass` records whether the refusal-delta gate passed.

It does not prove that refusal-delta evidence exists.

`refusal_delta_evidence_present` records whether the evidence required to support the refusal-delta result is materialized.

These are separate claims.

For release-grade paths, both must be true when refusal-delta behavior is release-relevant.

## Current fixture proof

The current negative fixture is:

```text
release_reference_v1/missing_refusal_delta
```

It isolates:

```text
refusal_delta_evidence_present = false
```

while keeping non-target gates passing:

```text
refusal_delta_pass = true
detectors_materialized_ok = true
external_summaries_present = true
external_all_pass = true
diagnostics.gates_stubbed = false
```

The dedicated test proves that when `refusal_delta_evidence_present` is required, the fixture fails for the intended reason.

## Current matrix support

The release-reference fixture matrix supports fixture-specific extra required gates through:

```json
"expected_extra_required_gates": [
  "refusal_delta_evidence_present"
]
```

The matrix passes this to the PULSE-REF guard as:

```bash
--require-gate refusal_delta_evidence_present
```

This allows PULSE-REF to preserve the current release-grade evidence-presence behavior through fixture-matrix coverage.

## Current policy and fixture state

The release-grade policy path includes:

```text
release_required:
  - refusal_delta_evidence_present
```

The release-grade reference profile records:

```text
require_refusal_delta_evidence_when_release_required: true
```

The negative fixture proves the fail-closed missing-evidence case:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
→ FAIL
```

The positive fixture proves the materialized-evidence case:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
→ PASS
```

The fixture matrix and dedicated no-implicit-PASS regression test preserve the
expected behavior.

Run:

The current evidence-presence validation should run the following checks:

```bash
python tests/test_no_implicit_pass_release_grade.py
python tests/test_release_reference_fixture_matrix_v1.py
python tests/test_external_summary_envelope_fixture_matrix_v1.py
python tests/test_external_summary_schema_v1.py
python tests/test_external_summary_fixture_matrix_v1.py
```

Direct negative guard check:

```bash
python ci/check_release_reference_complete_v1.py \
  --status tests/fixtures/release_reference_v1/missing_refusal_delta/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-nonscaffolded \
  --require-detectors-materialized \
  --require-external-summaries \
  --require-gate refusal_delta_evidence_present
```

Expected result:

```text
FAIL
```

Expected failure target:

```text
refusal_delta_evidence_present
```

Direct positive guard check:

```bash
python ci/check_release_reference_complete_v1.py \
  --status tests/fixtures/release_reference_v1/refusal_delta_evidence_present/status.json \
  --policy pulse_gate_policy_v0.yml \
  --required-sets required,release_required \
  --allowed-run-modes prod \
  --require-nonstubbed \
  --require-nonscaffolded \
  --require-detectors-materialized \
  --require-external-summaries \
  --require-gate refusal_delta_evidence_present
```

Expected result:

```text
PASS
```

Remaining cleanup surface

Future edits to this document should distinguish current implemented evidence
from future work.

Open future work should be limited to items that are still absent or explicitly
kept as a separate implementation track.

## Non-goals

This document does not:

- replace `check_gates.py`;
- make fixture metadata normative;
- make docs normative;
- make refusal-delta diagnostics release authority;
- make ledgers, manifests, audit bundles, dashboards, summaries, or publication surfaces release authority;
- silently change legacy / advisory behavior.

## Summary

`refusal_delta_evidence_present` is the release-grade evidence-presence gate for
refusal-delta evidence.

It prevents this unsafe release-grade state:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
```

from becoming PASS.

Current repository evidence includes declared policy, release-grade profile
requirements, negative and positive fixtures, fixture-matrix integration, and a
dedicated no-implicit-PASS regression test.

This strengthens the PULSE-REF evidence-presence boundary without creating a
second release-decision engine.
