# Anchor Integrity v0.1 — claim/evidence contract candidate

**Status:** diagnostic contract candidate
**Source baseline:** `34431ec8ebe305a83273ffd39b78f083219f03e6`
**Authority effect:** `none`
**Release-authority activation:** `false`
**Work package:** 1 — baseline, schemas, examples and negative contract tests

## 1. Purpose

Anchor Integrity v0.1 corrects two semantic defects in the v0 diagnostic
surface before any additional runtime layer is built:

1. A ratio derived from heterogeneous PULSE gate signals is an operational
   proxy. It is not claim-level evidence coverage.
2. A relation or cycle check that did not run has no measured result. It must
   not be represented as `low` risk or as a successful check.

The v0.1 contract introduces explicit carriers for:

```text
claim
→ evidence item
→ source identity and content binding
→ exact locator
→ subject/run binding
→ recorded relation-verification result
→ claim disposition
→ diagnostic response recommendation
```

The contract does not assert that a source is true. It records whether the
specified relation was materialized and whether the declared verification
steps were completed.

## 2. Work-package boundary

This work package adds only:

- a source-bound v0 baseline inventory;
- five JSON Schema contracts;
- five positive example documents;
- negative schema-contract tests;
- an encoded historical-source fixture and offline byte-binding regressions;
- registration of the test in the two existing CI manifests;
- a documentation-index reference.

It does not add or change:

- the v0 adapter or renderer;
- a v0.1 runtime adapter;
- automatic claim extraction;
- a cycle detector;
- semantic entailment inference;
- response enforcement;
- `status.json`;
- declared gate policy;
- materialized required gate sets;
- `check_gates.py`;
- primary-CI allow/block behavior;
- release authority.

## 3. Required separation

The following states are not interchangeable:

```text
legacy gate-signal ratio
≠ anchor presence
≠ source identity verification
≠ source integrity verification
≠ locator resolution
≠ subject binding
≠ relation verification
≠ claim support
≠ response recommendation
≠ release authority
```

A later adapter may aggregate only states whose individual records are present
and valid. Missing stages must remain missing.

## 4. Contract files

| Contract | Role |
|---|---|
| `anchor_integrity_claim_packet_v0_1.schema.json` | Materialized claim set and exact claim locators |
| `anchor_integrity_evidence_packet_v0_1.schema.json` | Source identities, evidence locators, integrity checks and subject binding |
| `anchor_integrity_relation_verification_packet_v0_1.schema.json` | Recorded claim-to-evidence relation results |
| `anchor_integrity_input_v0_1.schema.json` | Digest-bound input set for a future deterministic candidate adapter |
| `anchor_integrity_output_v0_1.schema.json` | Diagnostic candidate result, coverage layers, claim dispositions and response recommendation |

All five contracts fix:

```json
{
  "candidate_status": "diagnostic_only",
  "authority_effect": "none"
}
```

The input and output contracts additionally fix:

```json
{
  "release_authority_activation": false
}
```

## 5. Claim-set materialization

A claim-level denominator exists only after a claim set has been explicitly
materialized. The claim packet records:

- `claim_set_id`;
- materialization status and method;
- source-response identity and digest;
- one stable `claim_id` per claim;
- claim text and digest;
- exact character, JSON-pointer or line locator;
- claim type and explicit qualifiers.

v0.1 does not perform automatic claim extraction. A different decomposition of
the same response is a different claim set and must receive a different
`claim_set_id`.

Materialization states are:

```text
complete
partial
invalid
```

A partial or invalid claim set cannot produce a whole-response coverage value.
Observed counts may still be retained outside a whole-response coverage claim.

## 6. Evidence and source binding

The evidence packet separates source-level and evidence-item-level checks.

A source record contains:

- stable `source_id`;
- source type;
- canonical identifier;
- revision, when available;
- content SHA-256;
- source-identity verification state;
- source-integrity verification state.

An evidence item contains:

- stable `evidence_id`;
- bound `source_id`;
- exact locator;
- evidence-content SHA-256;
- locator-verification state;
- expected and observed subject/run identities;
- subject-binding verification state.

Source presence is not support. A source may exist and still be mismatched,
corrupt, unresolved, bound to a different subject, insufficient or
contradictory.

### 6.1. Example source bytes and digest reconstruction

The example source is `scripts/anchor_integrity_adapter_v0.py` at the pinned
baseline commit `34431ec8ebe305a83273ffd39b78f083219f03e6`, not the current
working-tree version of that file. Its exact 11,457 bytes have:

```text
Git blob SHA-1:
3f4afe26be361fddda153f72dd20803183a85a8e

Whole-source SHA-256:
3ceb60e9ca0a5d3a7d142bc91f5f51ca0376f54a37f33c3f359774f25c42f1d0
```

The regression fixture
[`adapter_v0_34431ec8.source.json`](../tests/fixtures/anchor_integrity_v0_1/adapter_v0_34431ec8.source.json)
stores those bytes as base64 data. Tests decode them and independently check
the pinned commit/path metadata, byte length, Git blob identity and SHA-256.
They do not import or execute the adapter, call the network or require Git
history. A later working-tree adapter change must not silently rebind this
historical example. Text checkout conversion of the JSON carrier does not
change the decoded source bytes.

For this example's `line_range` locator, line numbers are one-based and both
endpoints are inclusive. Split the original bytes at LF boundaries and retain
each selected line's original terminator. Do not trim whitespace, decode and
re-encode text, normalize line endings or add a final newline. The evidence
item selects lines **100 through 142**, the complete proxy-computation
function including the arithmetic at line 139. Its `content_sha256` hashes
only that selected byte sequence, not the whole file.

Packet-link digests hash the exact stored UTF-8 JSON file bytes, including
the final newline; they do not hash a parsed or reserialized JSON object.
After evidence changes, refresh the relation packet's evidence binding,
then the input packet bindings, and finally the output's `input_sha256`.
The contract regression checks each of these links against actual bytes.

These checks establish this fixed fixture's source and packet-byte bindings.
They do not authenticate an external verifier, prove semantic entailment,
validate the legacy-overlay reference, implement a general runtime binding
validator or make the illustrative `supported` result release authority.

## 7. Measurement state and result

Every check keeps execution state separate from result.

Allowed execution states are:

```text
not_requested
not_run
completed
invalid_input
failed
not_applicable
```

Mechanical rule:

```text
status != completed
→ result = null
→ reason is required
```

A completed check must carry a result from the result set declared for that
check. The schema rejects a non-null result when the check did not complete.

This rule directly prevents:

```json
{
  "status": "not_run",
  "result": "low"
}
```

## 8. Relation verification

The relation-verification packet records an external or separately prepared
verifier result. The contract does not infer semantic support merely because a
source or locator exists.

Allowed relation results are:

```text
supported
contradicted
insufficient
unresolved
```

A completed relation result must have a non-null `verifier_record_id`. A
non-completed relation check must have:

```json
{
  "result": null,
  "verifier_record_id": null
}
```

## 9. Supported-claim preconditions

The output schema permits `disposition = supported` only when the same claim
result records all of the following:

```text
source_identity_status = verified
AND source_integrity_status = verified
AND locator_status = resolved
AND subject_binding_status = satisfied
AND relation_verification_status = completed
AND relation_result = supported
AND contradiction_status = none
```

A claim cannot become supported through source presence, a positive legacy
signal, a non-run relation check or a reader-surface label.

## 10. Coverage layers

The v0.1 output separates three coverage layers:

| Layer | Meaning |
|---|---|
| `anchor_presence_coverage` | Materialized claims with at least one referenced anchor |
| `verified_binding_coverage` | Claims with verified source identity, integrity, locator and subject binding |
| `verified_support_coverage` | Claims with a completed supporting relation result |

The v0 gate-derived ratio is retained only as:

```json
{
  "semantic_class": "operational_proxy",
  "is_claim_evidence_coverage": false
}
```

If claim-set materialization is `partial` or `invalid`, all three
whole-response coverage metrics must be:

```json
{
  "status": "not_applicable",
  "numerator": null,
  "denominator": null,
  "value": null
}
```

The schema does not yet prove that `value = numerator / denominator`; that
arithmetic and count reconciliation belongs to the future deterministic
validator.

## 11. Typed cycle-check boundary

The contract reserves a cycle-check result for the evidence-dependency
subgraph only. It does not classify every Paradoxon Diagram cycle as a defect.

Reserved dependency-edge types are:

```text
supported_by_claim
derived_from_claim
evidence_depends_on_claim
claim_depends_on_claim
```

Completed result values are:

```text
no_unanchored_cycle_detected
unanchored_cycle_detected
anchored_cycle_observed
```

`low`, `medium` and `high` are not valid cycle-check results.

Work package 1 does not implement the detector. Therefore its example output
records:

```json
{
  "status": "not_run",
  "result": null,
  "algorithm": null,
  "reason": "typed_cycle_detector_not_implemented_in_work_package_1"
}
```

## 12. Diagnostic response recommendation

The output contract permits these non-enforcing recommendations:

```text
ALLOW_SUPPORTED
ASK_FOR_ANCHOR
BOUNDARY
BOUNDARY_CONTRADICTION
PARTIAL_BOUNDARY
SILENCE
```

Every recommendation is fixed to:

```json
{
  "authority": "diagnostic_only",
  "enforced": false
}
```

`SILENCE` is not a generic substitute for an unimplemented check. It is a
recorded diagnostic recommendation only. Production response enforcement is
outside v0.1.

## 13. Normative non-interference

The candidate contracts and examples are outside the normative chain:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ check_gates.py
→ primary CI allow/block
```

This work package must not modify any element in that chain. The diagnostic
artifacts are not inputs to `status.json`, gate-set materialization or
`check_gates.py`.

Reader surfaces, Pages, Markdown renderers and diagnostic reports cannot
promote the candidate into release authority.

## 14. Explicitly not implemented

The output schema preserves the following exact boundary:

```text
automatic_claim_extraction
general_semantic_entailment_verification
production_response_enforcement
release_authority_integration
real_world_hallucination_reduction_measurement
```

No hallucination-reduction percentage may be claimed from the schema fixtures.
The fixture suite tests contract behavior, not production accuracy.

## 15. Contract-test matrix

The first test package verifies at least these cases:

1. all five schemas are valid Draft 2020-12 schemas;
2. all five positive examples validate;
3. diagnostic-only and authority-none fields are fixed;
4. release-authority activation cannot be enabled;
5. the legacy ratio cannot be labelled claim-evidence coverage;
6. a non-run check cannot carry a result;
7. `low` is not a cycle-check result;
8. a supported claim requires all binding and relation preconditions;
9. incomplete claim materialization cannot produce whole-response coverage;
10. evidence requires a source identity and exact locator;
11. a completed relation check requires a verifier record;
12. a non-completed relation check cannot retain a verifier result;
13. response recommendations remain non-enforcing;
14. unexpected fields are rejected;
15. the test is registered exactly once in both CI manifests;
16. the baseline inventory remains source-commit bound;
17. the preserved source bytes match the pinned Git blob and SHA-256;
18. the source and selected-content digests are reconstructed separately;
19. example packet links match exact stored file bytes;
20. stale digests, changed source bytes, invalid line ranges and rehashed
    outer packets cannot conceal a wrong source-content binding.

## 16. Acceptance boundary for work package 1

Work package 1 is complete when:

- the targeted contract test passes;
- the schemas and examples are deterministic JSON;
- the baseline inventory names the exact v0 source commit and v0 source blobs;
- both test manifests contain the new test exactly once;
- no workflow, runtime, policy, status, gate or authority file changes;
- no v0 source file changes;
- no runtime or measured-improvement claim is introduced.

The next work package may implement the deterministic candidate validator and
binding checks against these contracts. It must not revise the meaning of a
missing or non-completed measurement.
