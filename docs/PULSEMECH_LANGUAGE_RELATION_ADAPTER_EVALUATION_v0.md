# PULSEmech Language Relation Adapter Evaluation v0

Status: **LRM-05** preserved candidate import and fixed-set evaluation interface.
Implementation base: `ed1b84119ef2fcd0dcf6997a28efeee0902af27f`, the merged
LRM-04 baseline in `HKati/pulse-release-gates-0.1`.

This package imports saved candidate responses, binds them to a fixed source-only
HU/EN request inventory, and runs the existing independent LRM-02 input verifier.
It preserves every selected case and question, including absent responses,
producer failures, malformed candidates and unresolved mappings. It publishes
admitted candidate input and actual verification artifacts for the existing
LRM-03/04 measurement path.

This is the preserved-response implementation permitted by the
[development plan](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md). It makes
no model call and records no measured provider accuracy. A live extraction
experiment requires a separately specified owner task. LRM-06 offline replay
and diagnostic integration remain separate work.

## 1. Scope and authority boundary

The following questions are kept separate:

1. Was a saved response declared for this request?
2. Do the response bytes match their recorded size and digest?
3. Does the response satisfy the existing input contract and structure rules?
4. Does it preserve the exact requested sources, contexts and question metadata?
5. What does the independent source/representation checker establish?
6. Has the candidate selected the appropriate relation roots for the question?
7. What would a separately executed relation or impact measurement establish?

LRM-05 implements the first five steps. Target-root selection remains explicitly
`scope_selection: "not_verified"` for **every question**, even when both mapping
checks pass. A mapping pass concerns the conveyed source roots under the supplied
family; it is not proof that the candidate selected the right target for the
operational question.

Every question remains `representation_basis: "candidate_only"` and
`claim_scope: "candidate_structures"`. Source mapping success, high confidence,
a provider name or a matching digest cannot elevate that basis.

The report retains all six Transition Meter axes. In particular:

```text
authority_status = none
authority_effect = none
release_authority_activation = false
causal_status = not_evaluated
reproduction_status = not_tested
```

No normative release input, required gate set, release-authority component or
workflow is changed. LRM-05 does not invoke the comparator or impact evaluator.
Its report has no relation-state verdict and no aggregate semantic PASS.

## 2. Fixed source-only requests

The request inventory is
[`examples/language_relation_adapter_v0/requests.json`](../examples/language_relation_adapter_v0/requests.json).
Its identifier is `lrm_hu_en_source_requests_v0`. The runtime pins its exact bytes:

- Size: **37,506 bytes**.
- SHA-256: `a147703b992e7236e839174c9fe72cd71c83e4781ac27a1c81076fb9c222ca22`.
- **23 cases**, **24 questions**: 14 English cases and 9 Hungarian cases.
- Profile: `lrm_finite_reference_profile_v0` with the preserved profile digest.

Each request includes only its case ID, exact profile reference, exact inline
before/after/context source records, and question metadata: `target_id`,
`question`, `granularity`, `description`, and `context_source_ids`.

It contains no reference representations, relation-root IDs, correspondence,
source anchors, interpretation family, coverage assertions, support model or
expected verdict. A declared context source is task input; it is retained even
when it narrows possible readings. No implicit normalization changes source
bytes, whitespace, Unicode or line endings.

A per-request digest is SHA-256 of `canonical_bytes(request)` under the existing
profile-defined encoding. The whole inventory digest binds the original file
bytes. Those two digests identify different objects.

The source-only inventory was prepared from the preserved synthetic LRM-01 case
set as a development step. The evaluation runtime reads this separate pinned
inventory. It does **not** load the reference `cases.json`, `expected.json` or
`contract_examples.json`. Case IDs address requests and output files; they do
not select precomputed semantic answers.

The old corpus is not an extraction gold set. For example, REF13 intentionally
contains an incomplete submitted representation, and REF19–21 are family-state
controls. Comparing a candidate with those authored structures would not by
itself measure extraction correctness. LRM-05 therefore supplies no reference
agreement score and makes no reference-acceptance claim.

### Exporting requests

```bash
python tools/evaluate_language_relation_candidates_v0.py requests \
  --output-dir /work/lrm05-requests
```

This creates exactly `requests.json` in a fresh directory. A producer also needs
the public output contract:

- [`language_relation_profile_v0.json`](../contracts/language_relation_profile_v0.json).
- [`language_relation_input_v0.schema.json`](../schemas/language_relation_input_v0.schema.json).
- [LRM input semantics](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md).

These define the output language and do not supply case-specific reference
answers. Do not give a producer the entire reference corpus or oracle as its
request material.

This input-flow boundary does not prove what a historical producer saw elsewhere.
The report always records `historical_input_isolation: "not_verified"`.

## 3. Preserved response records

[`language_relation_candidate_records_v0.schema.json`](../schemas/language_relation_candidate_records_v0.schema.json)
defines a strict capture index. It binds the exact request inventory, declares
producer metadata and contains at most 64 records. A producer declaration has
an adapter ID/version, nullable provider/model/run identifiers, and one of:

- `record_origin: "synthetic_fixture"` for authored import controls;
- `record_origin: "preserved_model_response"` for saved model responses.

These fields do not authenticate a provider, model or actual execution. The
report retains `producer_authentication: "not_verified"`.

A record contains its record/case IDs, exact request digest, capture status,
response path/size/digest or `null`, reason, nullable confidence, and explicitly
reported unresolved items. Capture statuses are:

| Capture status | Required record shape |
| --- | --- |
| `completed` | A response pin and a null reason. |
| `failed` | No response pin and a nonempty producer-declared failure reason. |
| `unsupported` | No response pin and a nonempty producer-declared limitation. |
| `not_run` | No response pin and a nonempty reason. |

`completed` means the producer declared a saved output; it does not mean the
output is valid or correctly represents the source. A response is exactly one
strict UTF-8 `language_relation_input_v0` JSON object. Markdown fences, prose,
provider envelopes, duplicated keys and non-finite numbers are not repaired or
silently unwrapped. A normalization/import extension needs its own explicit
contract; v0 preserves the actual response bytes.

Unresolved items have a reason, a half-open UTF-8 byte interval in a named request
source, and one or more affected question IDs. The interval must be nonempty,
within the exact source, and aligned to character boundaries. Categories are
referent resolution, implicit context, negation scope, modal scope, paraphrase
correspondence, alternative completeness, target selection and other. There
are at most 32 such items per record. They remain producer declarations,
separate from actual independent-checker diagnostics.

Confidence is nullable or a number from 0 to 1. No threshold consumes it as
acceptance evidence. The negative fixture deliberately gives a wrong candidate
confidence `0.99` to exercise this boundary.

## 4. Admission and independent checking

The importer reads a response once within the selected package root. It rejects
unsafe paths and special files without following symlinks. Every successfully
read bounded response is preserved with its actual size and digest. A mismatch
with the claimed capture pin rejects that case; the report retains both the
submitted pin and the observed bytes. Parsing and admission do not repair it.

Admission requires:

- Strict JSON, the existing input schema and existing cross-record structure
  checks, including types, role signatures, references and expression acyclicity.
- Exact case/profile/source/context agreement with the frozen request. A changed
  source remains invalid even if the producer calculates a fresh digest for it.
- The same question IDs and question metadata. The candidate supplies its own
  `before_ids`, `after_ids` and required coverage-obligation IDs.
- Both representation bases exactly `candidate_only`, with null acceptance and
  verification references.
- Candidate correspondence with no accepted rule/reference, and no supplied
  coverage evidence references.
- Structural comparison only: no processing binding or processing-change claim.
- `impact_model: null`; independently grounded support is outside this importer.
- Provenance consistent with the declared origin. Synthetic fixtures admit
  `synthetic_reference` or `synthetic_contract_example`; preserved model responses
  require `captured_input`.

The importer rejects prohibited claims rather than rewriting the candidate.
The bytes admitted for checking are exactly the bytes pinned in the response
record. The checker receives an isolated temporary snapshot of those bytes, so
a later package-file mutation cannot substitute a different candidate under the
old pin. No trust configuration or acceptance inventory is passed to it.

The existing [`verify_input`](PULSEMECH_LANGUAGE_RELATION_INPUT_VERIFIER_v0.md)
performs source, anchor and controlled-profile mapping checks. Passing admission
only makes the candidate eligible for that checking. A checked candidate may
have a failing source anchor, a proven representation mismatch or an unresolved
source interpretation. Its verification and limitations remain available.

The importer never interprets missing extraction as a broken relation. A
source-mapping failure is distinct from a later relation or impact conclusion.

## 5. Complete inventory and diagnostic states

Every evaluation report has exactly the fixed 23 case rows and all 24 question
rows. It preserves the submitted family state where checking was reached;
`complete`, `unknown`, `empty` and `truncated` are not collapsed.

| Case field | Values and meaning |
| --- | --- |
| `capture_status` | Submitted status, or `missing` / `ambiguous` when no record or multiple records name a selected case. |
| `import_status` | `not_run`, `rejected`, `checked`, or `execution_error`. |
| `mapping_checks` | Actual before/after check records, or explicit `not_run` records with null results. |
| `questions` | Fixed question metadata, candidate selections when checked, actual coverage checks, and the persistent scope/basis limits. |
| `reported_unresolved_items` | The producer's declared issues and source locations; never independent findings. |
| `diagnostics` | Stage, code, bounded reason, affected questions, optional side and origin. |

Duplicate records for a known case make that case ambiguous and rejected. No
first, last or highest-confidence response is selected, and none of its response
paths is read. Unknown extra cases are listed under `unselected_records`, with
`response_read: false`; they cannot change the fixed denominator.

Failures are separated into capture, response reading/binding/parsing, candidate
schema/structure, request binding, prohibited candidate claims, unresolved-item
locations, and independent verification. Checker findings distinguish source
binding failures, representation mismatches, unsupported sources, unresolved
interpretations and resource exhaustion. An actual checker execution exception
is recorded as `execution_error`, not as a semantic mismatch.

A per-case failure does not prevent independent later cases from being checked.
An invalid global capture index, wrong fixed inventory pin or invalid global
configuration is an invalid-input error rather than a successful batch report.

The evaluation schema rejects a `checked` row without a completed capture, one
selected record, observed response/input/verification references, a family state
and candidate selections. An unchecked row cannot carry completed source or
mapping checks, admitted-input references or selected roots. Source and mapping
check kinds, names and cardinalities are constrained separately. These structural
rules prevent contradictory completion records; actual byte and semantic checks
remain necessary.

## 6. Artifact and command contract

```bash
python tools/evaluate_language_relation_candidates_v0.py evaluate \
  --records /work/captures/captures.json \
  --package-root /work/captures \
  --output-dir /work/lrm05-evaluation
```

The index must be within `--package-root`, which defaults to its parent. The
output directory must be fresh and its parent must already exist.

| Output | Binding and purpose |
| --- | --- |
| `requests.json` | Exact pinned request inventory bytes. |
| `records.json` | Exact submitted capture-index bytes. |
| `responses/CASE.bin` | Exact observed response bytes, including a response rejected for a capture-pin mismatch or invalid JSON. |
| `inputs/CASE.json` | Exact admitted candidate bytes for cases that completed the checker. |
| `verifications/CASE.json` | Canonical actual LRM-02 verification, bound to those input bytes. |
| `evaluation.json` | Full case/question accounting, check results, declarations, limits and artifact pins. |

The report binds profile, inventory, capture index, evaluator and checker
identities. Artifact references record relative output paths, exact sizes and
SHA-256 digests. The evaluator identity includes its implementation, CLI,
schemas, fixed request inventory and existing checker dependencies. The
`evaluation_id` derives from the canonical report before that ID is inserted.

`records.json` preserves the original index unchanged, including its original
response locators. It is not rewritten into a runnable capture index for the
output directory. The report's `response_ref` points to each observed output copy;
`submitted_response` retains the original claimed path, size and digest. Repeating
this import uses the original preserved capture package. A self-contained replay
workflow remains LRM-06 work.

The publisher refuses existing output paths, writes files without replacement,
synchronizes them and writes the evaluation report after its referenced payloads.
On a normal publication failure, rollback removes only objects it created and
still owns. It is not a multi-file atomic transaction: interruption may leave an
incomplete directory. Consumers must require the report and verify its bindings.

| Exit code | Meaning |
| --- | --- |
| `0` | The requested export or complete diagnostic batch was published; individual cases can fail or remain unresolved. |
| `2` | Invalid global input/configuration, publication shape or an existing output path. |
| `3` | An execution or publication operation failed. |

A case-specific checker execution failure may still be reported inside a
completed batch. Exit zero is never a source-semantic or release PASS.

### Handing a checked candidate to the existing measurement core

```bash
python tools/measure_language_relations_v0.py \
  --input /work/lrm05-evaluation/inputs/LRM_REF_01.json \
  --package-root /work/lrm05-evaluation \
  --output-dir /work/lrm03-from-candidate
```

The existing CLI performs its own current checking. The saved LRM-05 verification
is evidence of that import check, not an acceptance credential or permission to
skip later checks. Stronger source/comparison/impact premises still require the
separately configured evidence paths described by LRM-02–04.

## 7. Resource and reporting bounds

The importer bounds each response to 1 MiB. Only one unambiguous response per
selected case can be read, so at most 23 such snapshots are admitted for reading.
A candidate is further limited to 20,000 JSON nodes, 256 anchors, 64 coverage
obligations, 256 correspondences, and 256 entities/domains/relations/groups each
per side. The original verifier's finite-profile bounds continue to apply.

The strict reader retains its 4 MiB, 100,000-node and depth-80 limits. The full
report and every published JSON payload must pass that reader before publication.
If the complete batch cannot fit, publication fails as a whole; no successful
prefix may silently omit cases, questions or unresolved items. Diagnostic summaries
limit reasons to 1,024 characters with an explicit truncation marker; original
checker records and exact input payloads are retained separately.

Summary values are operational counts. They include submitted/checked/rejected/
missing/failed/unsupported/ambiguous cases and before/after mapping outcomes, with
fixed-set totals and English/Hungarian breakdowns. Capture and import counts are
different dimensions and need not be added as a single partition.

`model_quality` and `reference_agreement` remain `not_evaluated`. Supported-profile
mapping coverage does not establish general multilingual understanding,
free-language extraction accuracy, real-world truth or a hallucination-reduction
rate. The fixture run demonstrates the importer and checker boundaries.

## 8. Preserved contracts and remaining work

The original profile, input/verification/measurement/manifest schemas, historical
baseline inventory and LRM-01 reference corpus remain unchanged. This package adds
three self-contained schemas whose `$ref` values resolve within their own files:

- [`language_relation_adapter_requests_v0.schema.json`](../schemas/language_relation_adapter_requests_v0.schema.json).
- [`language_relation_candidate_records_v0.schema.json`](../schemas/language_relation_candidate_records_v0.schema.json).
- [`language_relation_adapter_evaluation_v0.schema.json`](../schemas/language_relation_adapter_evaluation_v0.schema.json).

Remaining limits include general free-language interpretation, independently
justified target selection, referent/context resolution outside the controlled
profile, producer authentication and proof of historical input isolation. A
model evaluation must preserve its real request/output capture and declare its
case selection and methodology before reporting quality results. LRM-06 still
supplies the separately planned offline replay and diagnostic integration path.
