# PULSEmech — Language Relation Measurement v0 plan

## 1. Status, purpose, and completion boundary

This document records the **LRM-01** development workstream. LRM-01 supplies
contracts, a finite language profile, synthetic reference fixtures, and contract
tests. It does not supply a runtime language adapter, source-to-representation
verifier, relation comparator, impact evaluator, or replay executable.

The development target is to measure the preservation, modification, loss, and
introduction of relations conveyed through natural language, together with their
persistence conditions and supportable consequences. The measured object is the
selected relation or relation group in its bound context. Wording is its carrier.

Build the deterministic measurement core on an explicitly bounded language
profile and documented reference interpretations first. Connect automatic
candidate extraction through that interface afterwards. Extraction, source
verification, comparison, and impact evaluation remain separately assessable.

The complete v0 must identify preserved relations in supported positive controls
and provide checkable witnesses for supported differences. Returning an unresolved
result for every input does not satisfy the development target. A locally
identifiable result must survive an unrelated unresolved part of the utterance.

The companion [technical contract](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md)
defines record semantics and the boundary between structural validation and
semantic verification. Passing the LRM-01 tests establishes the tested contract
properties only. It does not establish successful natural-language extraction or
measurement performance.

## 2. Fixed source baseline and integration base

- Repository: `HKati/pulse-release-gates-0.1`.
- Historical source commit: `47a3add6667542df6ef176285ed02bb1a741d9cf`.
- Historical source tree: `6d425c83e16fdc95cb2cfe1645a8060f3336dfaf`.
- Source inventory: [language_relation_measurement_v0_baseline.json](../contracts/language_relation_measurement_v0_baseline.json).

The source inventory preserves commit, tree, path, and Git blob identities. A
later implementation base is a separate integration record. Rechecking a newer
`main` must not rewrite the historical source baseline. A content digest records
identity; it does not establish semantic correctness or trust in the source.

### Reuse map

| Existing component | Reused obligation or method | LRM implementation boundary |
| --- | --- | --- |
| Transition Meter | Domain adapter, path and evidence binding, six canonical status axes. | The language profile defines and checks the language-specific representation. |
| Mechanical Transition Language | Preserve the visible operational relation through wording. | Documentation conventions do not constitute an automatic language parser. |
| Relation Preserving Discrimination | Target-relative sufficiency, higher-arity relations, and a nonempty compatible family. | The existing finite demonstrator is not a general natural-language comparator. |
| Paradoxon v0.2 and M1–M3 | Joint conditions, correspondence, persistence, and grounded support closure. | LRM implements a bounded language application of these obligations. |
| Anchor Integrity v0.1 | Separate source, locator, subject/run binding, and actual check state. | The existing contracts and examples do not provide a general semantic verifier. |
| Field Comparison Binding | Bind domain, correspondence, target, and coverage. | The scalar-field metric and existing geometric meanings are not relabeled as language semantics. |
| PD-SM-02 pre-execution impact | Separate mapper and source checker; witness-supported modeled impact. | The existing closed MON-1 program-language profile is not a natural-language parser. |
| Recognition Surface Poisoning and drift | Vary the communication surface while preserving a recorded internal reference. | The existing literal field/list comparison is not a semantic language comparator. |
| Paradox Diagram schema | A diagnostic view whose claims remain tied to their inputs. | A projection cannot verify its own source representation or replace higher-arity records with pairwise edges. |

LRM uses a new versioned namespace. Existing Anchor inputs, comparison-binding
metrics, and Paradox Diagram edge meanings retain their definitions. Source
references pinned to the historical commit are listed in section 12.

## 3. First profile and representation boundary

The initial profile is `lrm_finite_reference_profile_v0`, recorded in
[language_relation_profile_v0.json](../contracts/language_relation_profile_v0.json).
It uses finite, explicitly declared domains. It covers typed participants,
role-bound relations of any supported arity, `NOT`, `AND`, inclusive `OR`,
`IMPLIES`, and finite-domain `FORALL` and `EXISTS`. A relation argument may itself
refer to an assertion or relation where the profile admits that type.

Keep assertion, quotation, supposition, permission, obligation, and observed
event distinct. Cross-type inference requires an explicit named profile rule.
Permission does not establish an observed event; quoted content does not become
the system's own factual assertion.

The controlled-language part has a finite template inventory with explicit
syntax, permitted names, and semantic construction rules. Free text remains a
candidate or a documented reference interpretation until an appropriate checking
method is available. HU and EN examples exercise the declared profile; they do
not establish general multilingual coverage.

Initial proposed resource bounds are 12 expanded Boolean atoms, 64 jointly
compatible interpretation/correspondence variants, and 256 expression nodes per
variant. These are design limits, not measured performance results. Limit values
and exhaustion behavior are part of the bound profile.

### Representation bases

| Basis | Claim boundary |
| --- | --- |
| `profile_verified` | A separate checker has checked the source/representation mapping within the supported controlled-language profile. |
| `accepted_reference` | The result is conditional on an explicitly accepted, content-bound reference interpretation. |
| `candidate_only` | Structural diagnosis of submitted candidate representations only; no verified claim about the meaning conveyed by the source. |

The initial corpus uses `synthetic_reference` provenance and
`candidate_only` bases on both sides. Its wrapper records
`reference_status: "draft_synthetic_references"`. The separate oracle is a
conditional specification under the supplied reference interpretation; it is
not a measurement result or an owner-acceptance record. Submitted `fulfilled`
coverage remains an annotation pending the separate checking path.

An accepted profile/reference inventory is fixed independently of the submitted
measurement package. A package cannot bootstrap its own acceptance by including
an acceptance flag and its digest. A check must resolve the actual record,
subject, method, input bindings, and acceptance premise. Reference acceptance
does not establish the real-world truth of the utterance.

Every target result retains its `representation_basis` and `claim_scope`, with
the binding to the verification record used. The scopes are
`controlled_source_profile`, `reference_interpretation`, and
`candidate_structures`. Reports and diagram projections preserve these fields.
An `IDENTIFIED` or `PRESERVED` diagnosis on candidate structures cannot silently
become a source-semantic claim.

## 4. Measurement path and algorithm plan

1. Bind the measurement question, profile, targets, required obligations,
   relevant context, and level of detail.
2. Preserve the original and processed utterances as separate exact source
   instances. Bind the processing event when claiming that a change occurred in
   that particular operation.
3. Obtain candidate representations while preserving unresolved parts, source
   anchors, and globally coupled alternatives.
4. Run a separate source/representation check or resolve the documented
   reference acceptance. Check states and actual results remain distinct.
5. Build only jointly compatible combinations of original interpretation,
   processed interpretation, correspondence, and common context.
6. Compare the selected relations or relation groups under the declared profile.
   Record checkable difference witnesses or the closure needed for a preservation
   claim.
7. Assess named downstream targets using explicit premises, rules, and common
   configurations. Retain alternative support routes and unresolved obligations.
8. Preserve the deterministic measurement result and its inputs separately from
   the receipt of a particular replay execution.

Strict loading rejects duplicate JSON keys, invalid types, duplicate identifiers,
and dangling references. Source and locator checks use the original UTF-8 bytes;
normalization must not silently change the bound source. Any normalized view
needs its own recorded mapping to the preserved bytes.

Correspondence may link relation groups and support a sentence split or merge.
The same role pattern does not identify two different participants or events.
Wording equality is not a preservation proof. A wording change is not by itself
a relational change, and one-way entailment is not a universal equivalence rule.

Do not combine context-dependent alternatives as an unrestricted Cartesian
product. Unknown variants, an actually empty compatible family, and a truncated
search are distinct. No vacuous preservation follows from an empty family. A
checked counterexample can refute universal preservation even if later search
is truncated; it does not establish the full result set or identify the actual
reading across all unresolved alternatives.

Coverage is target-relative. Missing extraction alone does not establish a
broken relation. Proving a target-side addition also requires sufficient
coverage of the relevant original domain. Distinguish a newly worded consequence
already derivable from the original premises from new semantic content.

The comparator never receives the expected fixture labels. Case identifiers do
not select precomputed answers. Changing a case identifier alone must leave the
semantic result unchanged.

### Relation states and local assessment

| Relation state | Required meaning |
| --- | --- |
| `PRESERVED` | The selected relation/group retains its profile-defined meaning and conditions under sufficient correspondence and target coverage. |
| `CHANGED` | A supported correspondence exists, but a relevant role, operator, condition, scope, modality, or communication binding differs. |
| `BROKEN` | Sufficiently covered target-side material has no continuation meeting the recorded preservation requirement for the original relation. |
| `UNDETERMINED` | Required binding, interpretation, coverage, or rule is missing, or compatible variants support different classifications. |

Each classification belongs to a target and a level of assessment. A changed
condition group and a lost subrelation may both be recorded but must not be
counted as two independent errors without an explicit aggregation definition.
Introduced relations are recorded separately with their own support paths.

Local assessment is separate: `UNBOUND`, `INCOMPATIBLE`, `UNRESOLVED`, or
`IDENTIFIED`. An unperformed or unfinished check has no result and records its
reason. A completed but unresolved analysis is not a successful preservation
result. Invalid input, execution failure, and semantic uncertainty remain
separate states.

### Persistence and impact

Evaluate an impact claim for a named target using the same common configuration
for its joint premises. Preserve joint answer structure when several targets
are assessed; equal marginal answer sets do not prove preserved joint behavior.

Use grounded base records and positive typed support rules in v0. Conjunctive
premises are required jointly. Alternative proof routes remain separate. A
self-supporting cycle creates no foundation. After evidence withdrawal,
recompute closure from remaining bases instead of retaining old derived results
as new premises. Report a fact/negation conflict explicitly without deriving
arbitrary consequences from it.

Record modeled possibility changes, condition-satisfaction changes, support
changes, and independently observed consequences as distinct impact types.
Graph reachability alone identifies a target for further assessment. It does
not establish that a consequence occurred.

## 5. Artifact and replay design

| Artifact | Role |
| --- | --- |
| `input.json` | Measurement request, exact-source references, both representations, interpretations, correspondence, coverage, and acceptance references. |
| `verification.json` | Actual check states/results, methods, claim scopes, and exact subject/input/profile bindings. |
| `measurement.json` | Deterministic target results, representation bases/scopes, introduced relations, witnesses, impact, unresolved obligations, and status axes. |
| `manifest.json` | Payload paths, sizes, SHA-256 values, profile/code/source-baseline bindings, and replay requirements. |
| Preserved source/context/profile files | Exact bytes needed to reconstruct the declared measurement. |
| `replay_receipt.json` | Execution-specific time, environment, evaluator binding, and recomputation result; separate from the original deterministic measurement digest. |

The manifest enumerates payloads and does not hash itself. Resolve paths inside
the package boundary. Byte integrity is distinct from semantic verification.
The profile fixes deterministic output encoding, key order, ordering of
semantically unordered lists, and the final LF. Role-bearing or sequence-bearing
lists preserve their order. This encoding is not a claim of compliance with a
general JSON canonicalization standard.

Replay recomputes verification, comparison, and impact from the preserved inputs;
it does not merely compare two stored reports. Preserve the needed evaluator,
profiles, schemas, and dependency identities for offline replay. A remote commit
URL alone is insufficient. Missing evaluator identity remains a binding gap;
replay cannot silently use current `main` instead. No new model call is needed
for replay of the recorded deterministic measurement core.

## 6. Work packages and dependencies

LRM-01 fixes the contract. LRM-02 provides input checking. LRM-03 and LRM-04 build
the first functioning measurement core on that checked boundary. LRM-05 evaluates
automatic candidates against the established interface. LRM-06 closes the
preservation, replay, and diagnostic integration path. The authority boundary
applies in every work package.

| Package | Deliverable | Acceptance and completion claim |
| --- | --- | --- |
| **LRM-01 — Profile and contract** | English plan/contract, baseline inventory, profile, four schemas, HU/EN fixtures, separate expected results, and contract tests. | Valid Draft 2020-12 schemas; positive examples accepted and prohibited combinations rejected; unknown/empty/truncated states distinct; test registered once in each manifest. Completion means the tested contract is recorded. |
| **LRM-02 — Source binding and separate representation check** | Strict loader; digest, locator, subject/run checks; separate controlled-language interpreter; reference-acceptance resolution. | A01–A04 and A22. Rehashing a wrapper cannot validate an old check for changed source bytes. Mapping errors are detected independently of adapter self-assessment. |
| **LRM-03 — Relation comparator** | Four relation states, group correspondence, role/operator differences, alternative loss, target-side additions, and difference witnesses. | A05–A15, A21, and A24. Positive preservation controls succeed; higher-arity differences and useful target-local results are recognized. |
| **LRM-04 — Persistence and impact** | Condition/support changes, common-configuration witnesses or derivations, surviving alternative routes, and separate observed-event references. | A16–A18. Grounded support, cycles, alternative routes, and recomputation after withdrawal behave as declared. |
| **LRM-05 — Automatic adapter evaluation** | Model/provider-independent candidate import, extraction records, and separated error categories on a fixed HU/EN set. | All selected cases remain in the result inventory, including failures and unsupported cases; no reference or expected-label leakage; confidence is not acceptance evidence. |
| **LRM-06 — Replay and diagnostic integration** | Offline replay, execution receipt, diagnostic report, and documented diagram projection if needed. | A19, A20, and A23. Actual recomputation matches the deterministic core; exports preserve axes, scopes, and unresolved states; diagnostic artifacts do not affect normative release evaluation. |

A first LRM-05 implementation may import preserved model responses. A live model
experiment requires a separately specified owner task. Report accuracy and
coverage only for the declared case set and profile. Synthetic regressions do
not establish general natural-language accuracy or a general hallucination
reduction rate.

The companion [H1 measurement-target and repair case](PULSEMECH_PARADOX_MEASUREMENT_TARGET_AND_REPAIR_CASE_v0.md)
belongs primarily to Paradoxon Diagram and Transition Meter research. It
separates the suitability of a measurement target for an operational question
from the checking of an already selected target. Future reuse in LRM-03 or
LRM-04 requires an explicit mapping of the case's objects, claims and evidence
obligations into a supported domain profile. H1 is currently a hand-worked
specification, not an executable LRM fixture. This reference adds no
work-package completion prerequisite and changes no preserved v0 grammar,
schema or A01–A24 acceptance obligation.

## 7. LRM-01 file boundary

### New files — 13

```text
docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md
docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md
contracts/language_relation_measurement_v0_baseline.json
contracts/language_relation_profile_v0.json
schemas/language_relation_input_v0.schema.json
schemas/language_relation_verification_v0.schema.json
schemas/language_relation_measurement_v0.schema.json
schemas/language_relation_manifest_v0.schema.json
examples/language_relation_measurement_v0/README.md
examples/language_relation_measurement_v0/cases.json
examples/language_relation_measurement_v0/expected.json
examples/language_relation_measurement_v0/contract_examples.json
tests/test_language_relation_contract_v0.py
```

### Targeted changes to existing files — 2

```text
ci/pytest-tests.list
ci/tools-tests.list
```

Register `tests/test_language_relation_contract_v0.py` exactly once in each
manifest. Preserve unrelated entries and their order. If a manifest has changed
since preparation, insert the required entry into the current file rather than
overwriting it with a historical full copy.

LRM-01 adds no runtime adapter, model invocation, workflow change, `status.json`
writer, gate-policy change, root README/CHANGELOG change, publication-identifier
change, or Q2/Q3 change. Existing Anchor and Paradoxon implementation files are
outside this package's change list.

Later proposed runtime namespace: `tools/language_relation_v0/`, with separate
binding, profile, comparator, impact, and report modules. Proposed entrypoints:

```text
tools/check_language_relation_input_v0.py
tools/measure_language_relations_v0.py
tools/replay_language_relation_measurement_v0.py
```

These runtime paths are planned and are not delivered by LRM-01. A successfully
produced `CHANGED` or `UNDETERMINED` diagnosis is not itself an execution failure.
Future CLI exit codes must separately document invalid input and execution
failure; they are not release-authority decisions.

## 8. Acceptance obligations A01–A24

These are development obligations, not executed results and not a fixed count of
test functions. Each may require several positive and negative fixtures. Current
LRM-01 checks cover contract properties only; later packages must establish their
runtime obligations through actual execution.

| ID | Obligation | Checkable acceptance condition |
| --- | --- | --- |
| A01 | Source and locator | Whole-source and selected-span digests can be independently reconstructed. Changed bytes, invalid UTF-8 boundaries, and shifted spans produce binding failures. |
| A02 | Subject and processing | A record for another utterance, context, or processing event cannot replace the record for the actual input. |
| A03 | Strict structure | Duplicate keys/identifiers, prohibited fields, and unresolved references are rejected. |
| A04 | Actual check state | An unperformed check has a null result. Verifier subject binding resolves. The submitted package cannot establish its own accepted-reference root. |
| A05 | Permitted rewrite | Checked paraphrase, renaming, and sentence splitting preserve the selected relation; surface change alone causes no false error. |
| A06 | Role and identity | Role reversal is detected despite equal vocabulary. An equal role pattern does not identify different events. |
| A07 | Negation and quantifier | “Not all” and “none” differ on a suitable finite-domain witness. The quantified domain is part of the input. |
| A08 | Joint conditions | AND/OR and only-if/if changes record the operator/direction difference and a checkable witness. |
| A09 | Communication and modality | Permission cannot silently become occurrence, or quotation become direct assertion; the type change is recorded. |
| A10 | Missing versus broken | The same absent extracted relation is treated differently under complete and incomplete relevant coverage. Missing extraction alone is not `BROKEN`. |
| A11 | Target-side addition | Unsupported content, separately supported additions, and consequences derived from the original premises are distinguished. No evidence status is automatically inherited. |
| A12 | Higher-arity relation | Different ternary relations with equal individual and pairwise projections are not classified as preserved. |
| A13 | Coupled alternatives | Shared referent/context choices remain coupled. Forbidden combinations cannot enter the compatible family. |
| A14 | Useful local result | Under global ambiguity, a fully covered target with the same answer in every allowed relevant variant may be `IDENTIFIED`. |
| A15 | Unknown, empty, truncated | The three states differ. Truncation cannot establish universal preservation or absence of impact; an independently checked counterexample remains usable. |
| A16 | Grounded support | A cycle without a grounded base supplies no support. A surviving alternative path may retain support. Withdrawal triggers recomputation from remaining bases. |
| A17 | Impact witness | Every established modeled impact has a common configuration or checkable derivation. Reachability alone is insufficient. |
| A18 | Observed consequence | A possibility change remains a model claim. An observed event needs separate source, subject/run, and event binding. |
| A19 | Actual replay | Recomputation from preserved inputs matches the deterministic result; no new model call and no substitution of stored-report equality for replay. |
| A20 | Authority boundary | With unchanged normative inputs, release evaluation is unchanged by presence, absence, or content changes of the LRM artifact. |
| A21 | Oracle exclusion | The evaluator receives no expected file or verdict label. Renaming the case identifier leaves the semantic result unchanged. |
| A22 | Wrong representation | A separate controlled-profile checker catches an AND/OR distinction lost identically on both sides; false preservation cannot pass through. |
| A23 | Core versus receipt | A new replay timestamp/environment receipt does not change the deterministic measurement core; evaluator version is checked. |
| A24 | Fidelity and claim scope | Faithful preservation does not prove real-world truth. Output and projections retain representation basis and claim scope; candidates do not become source verification. |

## 9. Status axes and release-authority separation

Retain all six canonical axes:

- `observation_status`
- `binding_status`
- `consistency_status`
- `reproduction_status`
- `causal_status`
- `authority_status`

Local relation assessment cannot overwrite observation, binding, causal, or other
canonical status. In LRM v0:

```text
authority_status = none
authority_effect = none
release_authority_activation = false
```

The normative chain remains:

`recorded release evidence → status.json → declared gate policy → materialized required gate set → check_gates.py → primary CI allow/block`

LRM diagnostic artifacts are not added to that chain. Schema-valid artifacts,
verified evidence, relation satisfaction, and release authority remain distinct.
A code regression test may correctly fail CI. The non-interference requirement
prevents a diagnostic language artifact from becoming a hidden normative
release-decision input; it does not prohibit testing LRM code.

## 10. Parallel development and handoff

Every work package has its own allowed paths and dependencies. Before applying a
prepared package, recheck new-path collisions, manifest entries, and relevant
changes in shared contracts against the actual implementation base. Do not
rewrite files owned by another workstream merely because `main` advanced.
Extracting shared validator code is a separate change with identified consumers
and regressions; LRM-01 does not refactor existing runtime code.

A handoff records the selected base, exact new/modified paths, full files or
targeted patches, actually executed checks, checks not performed, and the
supported completion claim. Work provenance is part of the deliverable.

Repository application requires the owner's separately specified task. Where a
single commit and push is authorized, restrict it to the named branch and files.
The owner opens the PR and performs the merge. Delivery of this plan or package
does not authorize workflow dispatch, a live model run, or release-authority
activation.

## 11. Open extraction questions and next implementation

LRM-05 must separately assess referent resolution, implicit/missing context,
negation and modal scope, correspondence across free paraphrases, and whether
retained alternatives cover the selected question. Each unresolved item records
its reason, source location, and affected target. Candidate confidence is not
independent verification.

Freeze the reference inventory before evaluation. Keep failures in the inventory
and compare later improvements by replaying the same cases. Add new cases as a
separate expansion instead of silently replacing difficult cases.

After LRM-01 contract acceptance, implement LRM-02 against this boundary. LRM-02
through LRM-04 together provide the first functioning relation measurement core.
Automatic extraction quality remains a separately measured development result.

## 12. Pinned source references

The paths below are pinned to the historical source commit. The baseline JSON
records their Git blob identities. These are source references, not evidence of
new test execution or new LRM runtime results.

- **S1** [PULSEMECH_TRANSITION_METER.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/PULSEMECH_TRANSITION_METER.md)
- **S2** [docs/PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md)
- **S3** [docs/PULSEMECH_RELATION_PRESERVING_DISCRIMINATION_v0.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSEMECH_RELATION_PRESERVING_DISCRIMINATION_v0.md)
- **S4** [docs/PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md)
- **S5** [docs/ANCHOR_INTEGRITY_v0_1_CONTRACT.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/ANCHOR_INTEGRITY_v0_1_CONTRACT.md)
- **S6** [docs/PULSE_RECOGNITION_SURFACE_POISONING_v0.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSE_RECOGNITION_SURFACE_POISONING_v0.md)
- **S7** [docs/PULSEMECH_FIELD_COMPARISON_BINDING_v0.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSEMECH_FIELD_COMPARISON_BINDING_v0.md)
- **S8** [docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md)
- **S9** [examples/paradox_preexecution_impact_v0/README.md](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/examples/paradox_preexecution_impact_v0/README.md)
- **S10** [examples/paradox_preexecution_impact_v0/check_impact.py](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/examples/paradox_preexecution_impact_v0/check_impact.py)
- **S11** [scripts/build_recognition_surface_drift_v0.py](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/scripts/build_recognition_surface_drift_v0.py)
- **S12** [schemas/PULSE_paradox_diagram_v0.schema.json](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/schemas/PULSE_paradox_diagram_v0.schema.json)
- **S13** [tests/test_anchor_integrity_v0_1_contract.py](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/tests/test_anchor_integrity_v0_1_contract.py)
- **S14** [ci/pytest-tests.list](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/ci/pytest-tests.list)
- **S15** [ci/tools-tests.list](https://github.com/HKati/pulse-release-gates-0.1/blob/47a3add6667542df6ef176285ed02bb1a741d9cf/ci/tools-tests.list)
