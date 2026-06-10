# PULSE Release Evidence Trusted Verifier Schema-Only Draft Boundary v0

## Purpose

This document records the Stage B boundary for a possible future trusted-verifier schema-only draft.

It does not edit schemas.

It does not add examples.

It does not implement a trusted verifier.

It does not change checker behavior.

It does not change builder behavior.

It does not emit `VERIFIED`.

It does not promote evidence.

It does not satisfy relation bindings.

It does not materialize gates.

It does not write `status.json`.

It does not reopen `--release-grade-materialized`.

The purpose of this document is to define the safe boundary terms and example constraints that must exist before any future schema-only draft or non-authoritative example is considered.

## Current v0 boundary

Current v0 remains diagnostic-only:

```text
verifier_decision = FAILED
provenance.trusted = false
verification_status = not_verified
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

The current builder remains fail-closed and diagnostic-only.

It may record candidate evidence, digest comparisons, subject binding comparisons, run binding comparisons, failed checks, and pre-materialization gaps.

Those facts remain diagnostic visibility.

They are not verification.

They are not trust.

They are not satisfied relation bindings.

They are not gate materialization.

They are not release authority.

## Stage B definition

Stage B means:

```text
schema-only draft / examples, still non-authoritative
```

Stage B does not mean:

```text
trusted verifier implementation
VERIFIED emission
candidate evidence promotion
relation binding satisfaction
gate materialization
status.json writing
release authority
```

Stage B can only describe possible future shapes.

Stage B must not activate them.

## Core boundary

```text
schema-only draft ≠ trusted verifier
schema-only draft ≠ VERIFIED
schema-only draft ≠ verified evidence
schema-only draft ≠ satisfied relation binding
schema-only draft ≠ gate materialization
schema-valid report ≠ release authority
```

## Draft-field boundary

Any future draft field must carry this boundary:

```text
Draft fields do not create trust.
Draft fields do not emit VERIFIED.
Draft fields do not verify candidate evidence.
Draft fields do not satisfy relation bindings.
Draft fields do not materialize gates.
Draft fields do not write status.json.
Draft fields do not affect check_gates.py.
Draft fields do not create release authority.
```

## Safe Stage B candidate surfaces

The safest possible future Stage B draft surfaces are diagnostic-only surfaces.

They must remain optional, non-authoritative, and FAILED.

### Candidate evidence schema validation draft

A future draft may describe candidate evidence schema validation shape.

Possible future concepts:

- candidate schema path
- candidate schema version
- candidate schema digest
- validation status
- validation errors
- validation source
- duplicate-key validation result
- partial-validation unavailable / failed state

Boundary:

```text
candidate schema validation draft ≠ verified evidence
schema-valid candidate ≠ trusted evidence
duplicate-key check ≠ full evidence verification
```

Any example using these fields must remain:

```text
verifier_decision = FAILED
provenance.trusted = false
verification_status = not_verified
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

### Partial verification diagnostic draft

A future draft may describe failed or pending partial verification sub-results.

Possible future diagnostic sub-results:

- digest binding result
- subject binding result
- run binding result
- candidate schema validation result
- verifier identity result
- trust-root result
- relation provenance readiness result

Boundary:

```text
partial pass ≠ verified evidence
partial pass ≠ satisfied relation binding
partial pass ≠ gate materialization
```

All partial verification examples must remain failed / pending / diagnostic.

No partial verification result may populate `verified_artifacts`, `relation_bindings`, or `gate_materialization`.

## High-risk Stage B surfaces

The following surfaces are high-risk and must not be introduced casually.

### Trusted verifier identity

Current fields such as `verifier_id` and `verifier_version` are representation fields only.

They are not trust evidence.

A future trusted verifier identity draft could be misread as self-authorizing trust.

Therefore:

```text
trusted verifier identity draft
→ docs-only placeholder first
→ schema draft only after non-self-authorizing trust wording exists
```

Boundary:

```text
verifier_id ≠ trusted identity
verifier_version ≠ trusted verifier
self-declared identity ≠ trust
```

### Verifier trust root

No current v0 trust-root field exists.

A future trust-root draft can look like a real trust root even when no enforcement exists.

Therefore:

```text
trust root draft
→ docs-only placeholder first
→ avoid realistic authority values in examples
→ schema draft only after source / scope / freshness / allowed identity rules are defined
```

Boundary:

```text
trust root draft ≠ active trust root
placeholder trust root ≠ verifier trust
```

### Relation provenance

Relation provenance belongs to later relation-level verification.

Current builder emits no relation bindings.

Stage B must not demonstrate relation provenance through non-empty `relation_bindings`.

Boundary:

```text
relation provenance draft ≠ verified relation
provenance presence ≠ relation satisfaction
```

### Deterministic relation ID rule

Deterministic relation ID generation requires canonical input fields and canonicalization rules.

Those rules do not exist in current v0.

Boundary:

```text
relation_id rule draft ≠ satisfied relation binding
deterministic-looking ID ≠ verified relation
```

Stage B may record this as docs-only.

Schema draft should wait until canonicalization is defined.

### Gate eligibility

Gate eligibility is not Stage B.

It belongs to Stage G or later.

Boundary:

```text
gate eligibility draft ≠ gate materialization
gate materialization ≠ release authority without declared policy and fail-closed CI
```

### Verified relation prototype

A verified relation prototype is not Stage B.

It belongs to Stage F or later.

Boundary:

```text
verified relation prototype ≠ Stage B
verified relation prototype ≠ gate materialization
```

## Example constraints

If examples are introduced later, they must follow these constraints.

### Allowed first

Docs-only snippets are the safest first form.

They must be visibly incomplete.

They must be labeled non-authoritative.

They must avoid realistic trust-root values.

They must not be placed where test consumers might treat them as accepted verifier outputs.

### Allowed later only by decision

A single JSON example may be considered later only if the workshop explicitly chooses a Stage B schema draft.

That JSON example must remain:

```text
verifier_decision = FAILED
provenance.trusted = false
verification_status = not_verified
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

It should be explicitly named:

```text
non_authoritative_failed_draft
```

### Not allowed in Stage B examples

Stage B examples must not include:

```text
VERIFIED
provenance.trusted = true
verification_status = verified
non-empty verified_artifacts
non-empty relation_bindings
non-empty gate_materialization
realistic trust-root authority values
gate eligibility outputs
status.json writes
release_authority_v0.json writes
report_card.html writes
release-authority audit bundles
```

## Checker boundary

A future checker may validate draft field shape only after a schema draft exists.

That checker must not treat draft fields as promotion.

Future checker duties may include:

- reject self-declared trusted identity
- require trust root for trusted fields
- validate trust-root shape
- validate candidate schema validation result shape
- validate relation provenance completeness
- validate deterministic relation ID fields
- reject ambiguous trusted states
- keep `VERIFIED` unavailable unless the full trusted path exists

Boundary:

```text
checker shape validation ≠ evidence promotion
checker shape validation ≠ release authority
```

## Builder boundary

A future builder may populate draft fields only in a later declared stage.

Future builder duties may include:

- populate trusted verifier identity from a trust root
- validate candidate evidence schema
- parse candidate evidence with duplicate-key rejection
- generate deterministic relation IDs
- populate relation provenance
- represent partial verification results

But until a later trusted stage is declared, builder output must remain:

```text
verifier_decision = FAILED
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

Boundary:

```text
builder draft output ≠ VERIFIED
builder draft output ≠ trusted evidence
builder draft output ≠ gate materialization
```

## Future test strategy

Any future Stage B patch must include tests proving that draft fields do not promote evidence.

Recommended future tests:

- schema accepts draft fields only in non-authoritative FAILED examples
- schema rejects `provenance.trusted = true` without a trust-root-backed trusted path
- schema rejects trusted-looking identity fields without explicit non-authority status
- schema rejects `VERIFIED` examples unless full verified-report requirements are met
- schema rejects draft gate eligibility if it attempts to materialize gates
- builder output remains unchanged
- checker does not treat draft fields as promotion
- checker does not allow self-declared trusted identity
- checker does not treat candidate schema validation success as verified evidence
- checker does not treat relation provenance as verified relation
- checker does not materialize gates from draft fields
- no `status.json`, `report_card.html`, or `release_authority_v0.json` is written
- no gate materialization occurs
- `check_gates.py` behavior is unaffected

## Boundary risks

Stage B must avoid these misread risks:

```text
trusted verifier identity looks like a trusted verifier already exists
trust root draft looks like a real trust root already exists
schema validation result looks like verified evidence
relation provenance looks like verified relation
deterministic relation ID looks like satisfied binding
verified relation prototype looks like gate materialization
schema-valid report looks like release authority
```

Mitigations:

```text
label draft identity as non-authoritative
avoid realistic trust-root values
keep examples FAILED
keep trusted=false
keep verification_status=not_verified
keep verified_artifacts empty
keep relation_bindings empty
keep gate_materialization empty
keep relation ID rule docs-only until canonicalization exists
postpone verified relation prototype to Stage F
postpone gate eligibility to Stage G
restate that checker/schema do not alter status, policy, CI, or release semantics
```

## Stage placement

The trusted-verifier path remains staged:

```text
Stage A — docs-only schema delta map
Stage B — schema-only draft / examples, still non-authoritative
Stage C — checker validation for schema shape, no promotion
Stage D — candidate evidence schema validation result, still FAILED
Stage E — trusted verifier identity / trust root, still no gate materialization
Stage F — non-authoritative verified relation prototype
Stage G — later gate eligibility review under declared policy
```

This document belongs before Stage B schema edits.

It is not itself a schema edit.

## Non-goals

This document does not:

- edit schemas
- add examples
- add JSON fixtures
- change checker behavior
- change builder behavior
- implement trusted verifier identity
- implement trust root
- implement candidate evidence schema validation
- implement relation ID generation
- implement relation provenance
- implement partial verification behavior
- implement gate eligibility
- emit `VERIFIED`
- mark evidence trusted
- mark evidence verified
- satisfy relation bindings
- materialize gates
- write `status.json`
- write `report_card.html`
- write `release_authority_v0.json`
- create release-authority audit bundles
- replace `check_gates.py`
- change release policy
- change gate registry
- change status schemas
- change CI authority path
- reopen `--release-grade-materialized`

## Summary

Stage B must be prepared before it is implemented.

The next safe movement is:

```text
docs-only clarification
→ schema-only draft boundary
→ optional non-authoritative draft fields later
```

Not:

```text
schema draft
→ trusted verifier
```

Current rule:

```text
No Stage B schema field creates trust.
No Stage B example creates verification.
No Stage B draft creates release authority.
```
