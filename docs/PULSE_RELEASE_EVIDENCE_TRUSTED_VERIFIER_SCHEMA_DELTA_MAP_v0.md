# PULSE Release Evidence Trusted Verifier Schema Delta Map v0

## Purpose

This document records the future schema delta map for a possible trusted verifier path in the PULSE release evidence verifier line.

It does not implement a trusted verifier.

It does not emit `VERIFIED`.

It does not promote candidate evidence.

It does not satisfy relation bindings.

It does not materialize gates.

It does not write `status.json`.

It does not reopen `--release-grade-materialized`.

The purpose of this document is to separate the current diagnostic-only v0 boundary from the future schema, checker, builder, and test surfaces that would be required before a trusted verifier or verified relation binding path could be designed.

## Current v0 boundary

Current v0 remains diagnostic-only.

The current verifier report boundary is:

```text
verifier_decision = FAILED
provenance.trusted = false
verification_status = not_verified
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

The current builder may record candidate evidence, digest comparison, subject binding comparison, run binding comparison, and expectation gaps.

Those recorded facts are diagnostic visibility.

They are not verification.

They are not trusted evidence.

They are not satisfied relation bindings.

They are not gate materialization.

They are not release authority.

## Core boundary

The current boundary remains:

```text
trusted verifier prerequisites ≠ VERIFIED
digest match ≠ verified evidence
subject/run match ≠ satisfied relation binding
relation visibility ≠ verified relation
verified relation ≠ gate materialization
gate materialization ≠ release authority without declared policy and fail-closed CI
```

## Current implemented surface

Current v0 already provides several prerequisite-adjacent mechanics.

### Verifier report identity representation

The verifier report has required identity fields:

```text
verifier_id
verifier_version
```

These are representation fields.

They are not trusted identity.

They are not trust-root-backed.

They do not authorize evidence verification.

### Diagnostic binding visibility

Current v0 can record and compare:

```text
artifact → digest binding
artifact → subject binding
artifact → run binding
```

These comparisons may produce failed checks and expectation summary gaps.

They do not verify evidence.

They do not satisfy relation bindings.

They do not materialize gates.

### Relation binding scaffolding

The verifier report schema can represent `relation_bindings`.

The checker already protects several relation-reference boundaries, including duplicate relation IDs, missing relation references, unverified referenced relations, and gate materialization entries without relation IDs.

Current builder behavior remains closed:

```text
relation_bindings = []
gate_materialization = {}
verified_artifacts = []
```

### Current diagnostic-only builder

The current builder intentionally stays in the pre-materialization lane:

```text
FAILED report only
no VERIFIED
no trusted evidence
no verified artifacts
no satisfied relation bindings
no gate materialization
no status.json writing
no check_gates.py replacement
no release-grade materialization reopening
```

## Schema delta map

| Area | Current state | Future schema delta | Future checker duty | Future builder duty | Future tests | Current v0 action |
| --- | --- | --- | --- | --- | --- | --- |
| Trusted verifier identity | `verifier_id` and `verifier_version` exist as required representation fields. They are not trust evidence. | Later add a non-self-authorizing trusted verifier identity object, with stable verifier identity, version, profile, and binding metadata. | Validate trusted identity shape only after a trusted-verifier stage exists. Reject missing, malformed, stale, mismatched, or self-declared trusted identity when trusted path is enabled. | Populate trusted identity only from a trust-root-backed configuration. Do not infer trust from arbitrary CLI input, candidate evidence, or existing `verifier_id`. | Missing identity, malformed identity, unknown identity, trusted-looking identity without trust root, mismatched identity. | schema review later |
| Verifier identity binding to report | Current report identity is represented but not cryptographically or policy-bound to report content. | Later add report-binding evidence, such as report digest, canonical report binding, created_by, or equivalent. | Confirm identity binding matches the report under canonical report construction rules. Fail closed on mismatch or stale binding. | Generate identity binding only after canonical report construction rules exist. | Tampered report identity, stale report binding, mismatched report digest. | implementation later |
| Verifier version / profile binding | `verifier_version` exists. No allowed-version or allowed-profile policy exists. | Later add verifier profile and trusted version/profile constraints, likely referenced by trust root. | Enforce allowed identity/version/profile combinations. | Emit profile only from trusted configuration. | Unsupported version, unsupported profile, version/profile mismatch. | schema review later |
| Self-declared identity rejection | Docs already say a self-declared verifier identity is not enough. Current implementation does not enforce trusted identity. | Distinguish claimed identity from trusted identity, or forbid trusted fields unless trust-root evidence is present. | Reject self-declared trusted identity without valid trust-root binding. | Never infer trust from `verifier_id` alone. | Report with trusted-looking `verifier_id` but no trust root. | keep out of current v0 |
| Trust root | No trust-root field exists in report or manifest schemas. | Later add `verifier_trust_root`, `trust_root_binding`, or equivalent. Include authority/source, digest/path/URI, scope, freshness metadata, and allowed verifier identities. | Require trust root only when trusted verifier path is enabled. Fail closed if absent, malformed, stale, mismatched, or out of scope. | Load trust root from declared controlled source. Do not synthesize from evidence inputs. | Missing trust root, malformed trust root, unrecognized authority, digest mismatch, stale trust root, scope mismatch. | schema review later |
| Candidate evidence schema validation result | Input manifest records candidate `schema_version`. Report evidence inputs may carry schema hints. Candidate evidence is not validated against its declared schema as a promotion input. | Later add candidate evidence validation result per candidate artifact: schema path, schema version, optional schema digest, validation status, validation errors, and validation source. | Validate candidate artifact against declared schema. Fail closed on schema load failure, validation failure, duplicate keys, or partial validation. | Run candidate validation and record result, while keeping current stage `FAILED` until trusted path exists. | Valid candidate remains non-authoritative, invalid schema, wrong schema, schema digest mismatch, validation errors included. | schema review later |
| Candidate artifact duplicate-key validation | Input manifest duplicate keys are fail-closed. Candidate artifact duplicate-key validation is not implemented. | Add duplicate-key rejection for candidate artifact parsing before schema validation. | Candidate artifact duplicate keys must fail closed. No partial fallback. | Use duplicate-key rejecting loader for candidate artifacts. | Candidate evidence duplicate key cannot be promoted and remains failed. | implementation later |
| Partial validation unavailable | Manifest/report validators fail closed when `jsonschema` is unavailable. Candidate validation unavailable is not represented. | Candidate validation result must have no best-effort success state. Validator/schema unavailable means failed. | Block validation success when validator or schema is unavailable. | Record validation failure reason. | Validator unavailable, schema unavailable, partial parse only. | implementation later |
| Deterministic relation ID rule | Relation IDs are accepted as strings. Duplicate IDs are rejected by checker. No deterministic generation rule exists. | Later define `relation_id_rule` or canonical deterministic generation from selected fields. | Recompute expected relation ID and reject non-canonical IDs when deterministic IDs are enabled. | Generate IDs from canonical inputs, not arbitrary labels. | Same inputs produce same ID; changed canonical field changes ID; duplicate/collision fails closed. | docs-only later |
| Relation ID input fields | Current relation bindings have `binding_type`, `source`, `target`; input manifest expected relations have binding type, source evidence ID, target, optional gate. | Define canonical relation ID fields, likely including relation type, source candidate, target identity, expected gate, subject/run/policy/registry identity, and candidate digest. | Ensure relation ID reflects canonical fields and scope. | Use identical canonicalization across builder and checker. | Reproducibility, collision, field-change tests. | schema review later |
| Relation ID collision behavior | Duplicate relation IDs are rejected. Deterministic collision behavior is not separately classified. | Add explicit collision / duplicate failure reason if deterministic relation IDs are introduced. | Reject duplicate or colliding IDs before relation verification. | Emit failed check and no verified relation on collision. | Collision fixture, duplicate ID fixture, duplicate gate reference fixture. | test-only later |
| Relation binding provenance | Current relation binding schema has basic fields and optional failure reason. It does not contain rich relation-level provenance. | Add relation provenance object with source artifact, expected relation, actual checked relation, verifier identity, trust root, candidate schema validation result, digest binding result, subject binding result, run binding result, and failure reason. | Validate provenance completeness for verified relations. Fail closed if required sub-results are missing or failed. | Populate provenance only from actual checks, not inferred from candidate presence. | Missing provenance on verified relation, failed digest/subject/run/schema sub-result blocks verified relation. | schema review later |
| Expected vs actual relation provenance | Candidate-level diagnostic provenance records some expected/actual digest and subject/run comparison data. Relation-level expected/actual relation is not represented. | Later promote checked facts into relation-level expected/actual relation fields only after trust root and candidate validation exist. | Cross-check expected relation against actual checked relation. | Build relation provenance from checked facts. | Expected/actual relation mismatch. | implementation later |
| Partial verification: digest match + subject mismatch | Current builder records digest and subject comparison independently and keeps report failed. | Later relation-level result should represent per-condition pass/fail and final relation status. | Digest success must not override subject failure. | Emit relation failure reason for subject mismatch. | Digest match + subject mismatch remains unverified. | test-only later |
| Partial verification: digest match + run mismatch | Current builder records run mismatch failed checks and keeps report failed. | Add run-binding result inside candidate/relation provenance. | Run mismatch blocks verified relation. | Emit run-binding failure reason. | Digest match + run mismatch remains unverified. | test-only later |
| Partial verification: subject match + schema validation failure | Candidate schema validation result is absent, so this cannot be enforced yet. | Add candidate schema validation result and require it for relation verification. | Schema failure blocks relation verification even if subject matches. | Record schema failure and keep report failed until later staged path. | Subject match + schema validation failed remains unverified. | schema review later |
| Partial verification: run match + missing verifier identity | Trusted identity and trust root are absent. | Trusted identity / trust-root fields required before relation verification. | Missing trusted identity blocks trusted path. | Emit missing identity failed check. | Run match + missing trusted verifier remains unverified. | implementation later |
| Partial verification: duplicate relation ID | Checker already rejects duplicate relation IDs. | Later deterministic ID layer should classify duplicate vs collision if deterministic generation exists. | Reject before verification and materialization. | Do not emit verified relation when duplicate/collision exists. | Duplicate generated relation ID fails closed. | test-only later |
| Partial verification: missing candidate evidence | Input manifest checker rejects dangling candidate references; builder records missing candidate failed checks. | Relation-level provenance should carry missing source candidate status or equivalent. | Missing source candidate blocks relation verification. | Emit failure reason and no verified relation. | Relation references missing candidate evidence. | implementation later |
| Partial verification: untrusted artifact | Current candidate provenance records `trusted = false` and `verification_status = not_verified`. | Candidate trust/validation result must remain untrusted unless verifier identity, trust root, schema, digest, subject, and run checks pass. | Relation referencing untrusted artifact is unverified. | Keep artifact untrusted until all preconditions pass. | Relation references untrusted artifact. | implementation later |
| Gate eligibility: declared policy binding | Report has policy binding. Input manifest gate expectations can include policy relation and materialization restrictions. | Later add explicit declared policy binding for gate eligibility, including policy digest, gate identity, relation requirements, and scope. | Verify policy binding and required relation set before gate eligibility. | Emit gate eligibility only when policy and verified relations are satisfied. | Policy digest mismatch, missing policy relation, undeclared gate. | schema review later |
| Gate eligibility: required gate identity | Gate materialization entries are schema modeled. Current builder emits none. | Add stable required gate identity and canonical gate registry binding. | Validate gate exists in registry/policy and is required. | Materialize only declared required gates, never arbitrary booleans. | Unknown gate, non-required gate, registry mismatch. | schema review later |
| Gate eligibility: verified relation IDs | Checker already rejects missing, duplicate, and unverified relation references when gate materialization entries exist. | Later require declared relation IDs from policy/gate eligibility, not merely any verified relation. | Missing, dangling, unverified, or undeclared relation references block gate eligibility. | Populate only after verified relation set exists. | Missing relation ref, dangling ref, unverified ref, undeclared ref. | test-only later |
| Gate eligibility: non-release-authority boundary | Expectation summary has explicit false authority-boundary flags. Pipeline tests assert no authority artifacts are created. | Later gate eligibility must remain non-release-authority until declared policy plus fail-closed CI enforcement exists. | Reject treating schema-valid report, verified relation, or gate materialization as release authority absent policy + CI. | Do not write `status.json` or reopen `--release-grade-materialized` until a separate declared stage. | Verified relation prototype does not materialize gates; gate materialization prototype does not imply release authority. | keep out of current v0 |

## Boundary risks

Future schema work must avoid semantic overloading.

The main risk is adding fields that look trusted before the trust path exists.

### Risk: verifier identity looks trusted

Current `verifier_id` and `verifier_version` are required representation fields.

They are not trusted identity.

They are not trust-root-backed.

They must not be read as proof of trust.

### Risk: digest match looks like verified evidence

Current digest comparison records diagnostic provenance.

It does not populate `verified_artifacts`.

It does not verify evidence.

### Risk: subject/run match looks like satisfied relation binding

Current subject/run comparison records diagnostic booleans and failed checks.

It does not populate `relation_bindings`.

It does not satisfy relation bindings.

### Risk: relation visibility looks like verified relation

Manifest expected relations are expectations.

Builder records them as pending verification.

They are not verified relations.

### Risk: verified relation looks like gate materialization

Future verified relation binding must not automatically materialize gates.

Gate materialization requires a separate declared policy and verified relation eligibility rule.

### Risk: gate materialization looks like release authority

Gate materialization is still not release authority unless connected to the declared release-authority path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gates
→ strict fail-closed CI enforcement
→ pre-deployment allow/block decision
```

### Risk: schema-valid report looks like release authority

Schema validity proves shape.

It does not prove release authority.

The verifier report checker validates report structure and relation-reference integrity.

It does not change status, gate policy, CI behavior, or release semantics.

## Minimal staged plan

Do not collapse the trusted verifier path into one PR.

The staged path is:

```text
Stage A — docs-only schema delta map
Stage B — schema-only draft / examples, still non-authoritative
Stage C — checker validation for schema shape, no promotion
Stage D — candidate evidence schema validation result, still FAILED
Stage E — trusted verifier identity / trust root, still no gate materialization
Stage F — non-authoritative verified relation prototype
Stage G — later gate eligibility review under declared policy
```

### Stage A — docs-only schema delta map

Record this schema delta map and boundary language.

No schema edits.

No builder changes.

No checker changes.

No workflow changes.

No promotion.

### Stage B — schema-only draft / examples

Add draft fields or examples for future trusted verifier identity, trust root, candidate validation result, relation provenance, and deterministic relation IDs.

Examples must remain explicitly non-authoritative.

No `VERIFIED`.

No gate materialization.

### Stage C — checker validation for schema shape

Teach checkers to validate new field shapes.

Reject ambiguous or self-declared trusted states.

Still no evidence promotion.

Still no verified relations.

Still no gates.

### Stage D — candidate evidence schema validation result

Add candidate artifact schema validation result.

Add duplicate-key fail-closed candidate parsing.

Add validation errors and partial-validation rejection.

Still keep report failed and diagnostic-only.

### Stage E — trusted verifier identity / trust root

Add trust-root-backed trusted verifier identity checks.

Missing, stale, mismatched, self-declared, or out-of-scope trust root remains fail-closed.

Still no gate materialization.

### Stage F — non-authoritative verified relation prototype

Introduce deterministic relation ID generation and relation-level provenance.

Any verified relation prototype remains non-release-authority.

It must not materialize gates.

### Stage G — later gate eligibility review

Only after policy binding, gate identity, verified relation references, and fail-closed CI are defined should gate eligibility be reviewed.

Even then, gate materialization must not be treated as release authority until the separate release-authority path is declared and enforced.

## Future review questions

Every future PR in this area must answer:

1. Does this PR change only documentation, or does it change schema / checker / builder behavior?
2. Does this PR introduce a trusted verifier identity?
3. If yes, what trust root backs it?
4. Does this PR allow any report to emit `VERIFIED`?
5. Does this PR allow candidate evidence to become trusted?
6. Does this PR allow candidate evidence to become verified?
7. Does this PR create non-empty `relation_bindings`?
8. If yes, are those relation bindings diagnostic, pending, failed, or verified?
9. Does this PR define deterministic relation ID generation?
10. Does this PR define relation-level provenance?
11. Does this PR define candidate-evidence schema validation result?
12. Does this PR define partial verification behavior?
13. Does this PR allow gate materialization?
14. If yes, what declared policy and verified relation IDs authorize it?
15. Does this PR write or modify `status.json`?
16. Does this PR affect `check_gates.py`?
17. Does this PR affect release policy, gate registry, status schemas, or CI authority path?
18. Does this PR reopen `--release-grade-materialized`?
19. Does this PR create release authority from verifier output?
20. If any answer is unclear, does the PR fail closed?

## Non-goals

This document does not:

- implement a trusted verifier
- define a trust root
- add schema fields
- change checker behavior
- change builder behavior
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

## Recommended checks for future patches

For docs-only changes:

```bash
git diff --check
```

For verifier report schema / checker changes:

```bash
python -m pytest \
  tests/test_release_evidence_verifier_report_schema_v0.py \
  tests/test_check_release_evidence_verifier_report_v0.py
```

For verifier builder / expectation summary changes:

```bash
python -m pytest \
  tests/test_build_release_evidence_verifier_report_v0.py \
  tests/test_build_release_evidence_expectation_summary_v0.py
```

For input manifest and pre-materialization pipeline changes:

```bash
python -m pytest \
  tests/test_release_evidence_input_manifest_v0.py \
  tests/test_release_evidence_pre_materialization_pipeline_v0.py
```

For tools manifest confirmation:

```bash
python -m pytest tests/test_tools_tests_list_smoke.py
```

## Summary

Current v0 remains closed.

The repository currently has diagnostic binding visibility, relation-binding schema/checker scaffolding, and fail-closed pre-materialization gap reporting.

It does not have trusted verifier identity, verifier trust root, candidate-evidence schema validation result, deterministic relation ID generation, relation-level provenance, full partial-verification behavior, or gate eligibility from verified relations.

The correct next movement is not:

```text
visible binding → VERIFIED
```

The correct staged movement is:

```text
visible binding
→ schema delta map
→ trusted verifier prerequisites
→ later schema/checker/builder stages
```

Current rule:

```text
No current v0 patch is required for trusted verifier implementation.
Current v0 remains diagnostic-only.
```
