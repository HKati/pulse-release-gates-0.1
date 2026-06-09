# PULSE Release Evidence Relation Binding Promotion Prerequisites v0

## Purpose

This document records the prerequisites for any future relation binding promotion path in the PULSE release evidence verifier line.

It does not implement relation binding promotion.

It does not change release-authority semantics.

It defines the mechanical boundary that must hold before diagnostic binding visibility can ever become verified relation binding evidence.

## Current boundary

The current pre-materialization evidence line may make these bindings visible:

```text
artifact → digest binding
artifact → subject binding
artifact → run binding
subject/run mismatch → expectation summary fallback as other_failed_check
```

These layers are diagnostic-only.

They do not imply:

- verified evidence
- trusted provenance
- satisfied relation binding
- gate materialization
- release authority
- release eligibility

The current verifier report boundary remains:

```text
verifier_decision = FAILED
provenance.trusted = false
verification_status = not_verified
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

## Core mechanical rule

Visible binding is not verified relation binding.

A candidate artifact can be recorded.

A digest can match.

A subject binding can match.

A run binding can match.

But none of these facts alone verifies evidence, satisfies a relation binding, materializes a gate, or creates release authority.

The boundary is:

```text
digest match ≠ verified evidence
subject/run match ≠ satisfied relation binding
relation visibility ≠ verified relation
verified relation ≠ gate materialization
gate materialization ≠ release authority without declared policy and fail-closed CI
```

## Relation binding promotion is not a single step

Any future relation binding promotion path must be staged.

It must not collapse diagnostic visibility, verification, relation satisfaction, gate materialization, and release authority into one operation.

A safe future path would need to separate at least these stages:

```text
Stage A — relation binding readiness documentation and tests
Stage B — trusted-verifier prerequisites review
Stage C — non-authoritative relation binding prototype
Stage D — trusted verifier path
Stage E — later gate materialization eligibility under declared policy
```

Each stage must remain fail-closed unless its required mechanical preconditions are satisfied.

## Required prerequisites before future promotion

Before any future implementation can promote visible bindings into verified `relation_bindings`, the following prerequisites must be defined and tested.

### 1. Trusted verifier identity

A future trusted verifier path must define:

- what verifier identity is trusted
- how verifier identity is represented
- how verifier identity is bound to the report
- how verifier identity is checked
- what happens when verifier identity is missing, stale, mismatched, or self-declared

A self-declared verifier identity must not be enough.

### 2. Verifier trust root

A future path must define an explicit trust root.

The trust root must specify:

- the authority source for verifier trust
- the expected verifier version or profile
- the allowed verification scope
- the failure behavior when the trust root is missing or invalid

Without an explicit trust root, relation binding promotion must remain unavailable.

### 3. Evidence schema validation result

A future relation binding cannot rely only on artifact presence or digest match.

The candidate evidence must have a recorded schema validation result.

The promotion path must define:

- which schema was used
- which schema version was used
- whether validation succeeded
- how validation errors are represented
- whether duplicate-key and partial-validation conditions fail closed

Schema-validity alone is not release authority.

### 4. Artifact digest binding

The candidate artifact must be bound to an expected digest.

Required conditions:

- expected digest is declared
- actual digest is computed
- expected digest and actual digest match
- mismatch fails closed
- missing artifact fails closed
- digest match remains non-authoritative unless all other promotion prerequisites are satisfied

Digest match alone must not verify evidence.

### 5. Subject binding

The candidate artifact must be bound to the expected subject.

The future path must define:

- expected subject identity
- actual report subject identity
- subject commit binding
- subject mismatch behavior
- subject override behavior
- case normalization rules, where applicable

Subject match alone must not satisfy a relation binding.

### 6. Run binding

The candidate artifact must be bound to the expected run identity.

The future path must define:

- expected run identity
- actual report run identity
- run key binding
- run git SHA binding
- run mismatch behavior
- run override behavior

Run match alone must not satisfy a relation binding.

### 7. Relation ID generation rule

A future promoted relation binding must have a stable relation ID rule.

The rule must define:

- how relation IDs are generated
- what fields are included
- whether IDs are deterministic
- how duplicate IDs are rejected
- how relation IDs are referenced by later stages

Duplicate relation IDs must fail closed.

### 8. Relation binding verification status

A future relation binding must represent its verification status explicitly.

The path must define at least:

- pending
- verified
- failed

or an equivalent closed set.

A relation binding must not become verified by default.

### 9. Relation binding provenance

A future verified relation binding must carry provenance.

The provenance must record:

- source artifact
- expected relation
- actual checked relation
- verifier identity
- verifier trust root
- schema validation result
- digest binding result
- subject binding result
- run binding result
- failure reason, when applicable

Missing provenance must fail closed.

### 10. Partial relation verification behavior

Partial verification must not promote the relation.

A future path must define failure behavior for cases such as:

- digest matches but subject mismatches
- digest matches but run mismatches
- subject matches but schema validation fails
- run matches but verifier identity is missing
- relation ID is duplicated
- relation references missing candidate evidence
- relation references an untrusted artifact

Partial success must remain non-authoritative.

### 11. Relation-to-gate eligibility

Verified relation binding must not automatically materialize gates.

A separate rule must define when a verified relation binding is eligible to support a gate materialization entry.

That rule must include:

- declared policy binding
- required gate identity
- relation IDs referenced by gate materialization entries
- missing reference behavior
- dangling reference behavior
- unverified relation reference behavior

Verified relation binding alone must not materialize a gate.

### 12. Declared policy requirement

Gate materialization must remain policy-declared.

A future relation binding promotion path must not bypass:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block decision
```

Relation binding verification is not a replacement for declared gate policy.

### 13. Fail-closed mismatch behavior

Every mismatch must fail closed.

At minimum:

- digest mismatch
- missing candidate evidence
- subject mismatch
- run mismatch
- stale relation
- broken relation
- dangling relation reference
- duplicate relation ID
- unverified referenced relation
- missing policy binding
- missing gate reference
- self-declared materialization

must remain non-authoritative and must not create release eligibility.

## Boundary risks to prevent

Future relation binding work must not accidentally convert diagnostic visibility into release authority.

The following conversions are forbidden:

```text
digest match → verified evidence
recorded candidate evidence → trusted evidence
subject/run match → satisfied relation binding
summary NOT_READY absence → release readiness
green test result → release authority
schema-valid report → release authority
external review text → release authority
live URL → release authority
verified relation → automatic gate materialization
gate materialization → release authority without declared policy and fail-closed CI
```

## Current acceptable v0 fallback

Subject/run mismatch failed checks may currently be summarized as:

```text
other_failed_check
```

This is acceptable in v0 as long as:

- the failed-check messages remain visible
- the summary remains `NOT_READY`
- the summary remains diagnostic-only
- no evidence is verified
- no relation binding is satisfied
- no gate is materialized
- no release authority is created

First-class diagnostic gap classes may be considered later only if there is a concrete reader, schema, or routing need.

Possible future diagnostic classes, if later chosen:

```text
subject_binding_mismatch
run_binding_mismatch
report_identity_override_mismatch
```

Adding those classes would be a schema-visible change and must be handled as a separate PR.

## Non-goals

This document does not:

- implement relation binding promotion
- emit `VERIFIED`
- mark candidate evidence as trusted
- mark candidate evidence as verified
- satisfy relation bindings
- materialize gates
- write `status.json`
- write `report_card.html`
- write `release_authority_v0.json`
- create release-authority audit bundles
- reopen `--release-grade-materialized`
- replace `check_gates.py`
- change release policy
- change gate registry
- change status schemas
- change CI authority path

## Future staged work

Future work, if pursued, should remain staged.

### Stage A — readiness documentation and tests

Goal:

Record and test the current boundary.

Allowed work:

- docs
- tests
- schema review
- checker review

Forbidden work:

- no promotion
- no `VERIFIED`
- no trusted evidence
- no gate materialization

### Stage B — trusted-verifier prerequisites

Goal:

Define what a trusted verifier would require.

Allowed work:

- trust-root design
- verifier identity design
- provenance requirements
- fail-closed mismatch requirements

Forbidden work:

- no release authority
- no status writing
- no gate materialization

### Stage C — non-authoritative relation binding prototype

Goal:

Prototype relation binding representation without authority.

Allowed work:

- non-authoritative relation binding examples
- checker tests
- duplicate / dangling / unverified reference rejection

Forbidden work:

- no release eligibility
- no policy satisfaction
- no materialized required gates

### Stage D — trusted verifier path

Goal:

Evaluate whether a verifier can produce verified relation bindings.

Required before this stage:

- trusted verifier identity
- trust root
- schema validation
- digest binding
- subject binding
- run binding
- provenance
- fail-closed mismatch handling

Forbidden work:

- no release-grade materialization unless separately declared and gated

### Stage E — later gate materialization eligibility

Goal:

Only after verified relation binding exists, evaluate whether relation bindings can support gate materialization.

Required before this stage:

- declared policy
- materialized required gate set
- relation IDs referenced by gate entries
- fail-closed CI enforcement

Forbidden work:

- no gate materialization from diagnostic summary
- no gate materialization from self-declared artifacts
- no gate materialization from live URLs
- no release authority from external review text

## Review questions for future PRs

Every future PR in this area should answer:

1. Does this PR only improve visibility, or does it promote evidence?
2. Does this PR create any non-empty `relation_bindings`?
3. If yes, are the relation bindings verified or diagnostic?
4. What verifier identity is trusted?
5. What trust root is used?
6. What schema was validated?
7. What digest was checked?
8. What subject was checked?
9. What run identity was checked?
10. What happens on partial success?
11. What happens on mismatch?
12. Can any gate be materialized from this output?
13. Can any release-authority artifact be written?
14. Does this PR affect `check_gates.py`, release policy, gate registry, status schemas, or CI authority path?
15. Does this PR reopen `--release-grade-materialized`?

If any answer is unclear, the PR must remain non-authoritative.

## Minimal command set for future checks

For future docs-only changes:

```bash
git diff --check
```

For future verifier / summary changes:

```bash
python -m pytest \
  tests/test_build_release_evidence_verifier_report_v0.py \
  tests/test_build_release_evidence_expectation_summary_v0.py
```

For future checker or schema boundary changes:

```bash
python -m pytest \
  tests/test_check_release_evidence_verifier_report_v0.py
```

For future pre-materialization pipeline changes:

```bash
python -m pytest \
  tests/test_release_evidence_pre_materialization_pipeline_v0.py
```

For tools manifest confirmation:

```bash
python -m pytest tests/test_tools_tests_list_smoke.py
```

## Summary

Relation binding promotion is not a naming change.

It is a mechanical transition from diagnostic visibility toward verified relation state.

That transition requires explicit trusted-verifier identity, trust root, schema validation, digest binding, subject binding, run binding, relation provenance, fail-closed mismatch behavior, and later policy-declared gate eligibility.

Until those prerequisites exist, the current boundary remains:

```text
visible binding ≠ verified relation binding
verified relation binding ≠ gate materialization
gate materialization ≠ release authority without declared policy and fail-closed CI
```
