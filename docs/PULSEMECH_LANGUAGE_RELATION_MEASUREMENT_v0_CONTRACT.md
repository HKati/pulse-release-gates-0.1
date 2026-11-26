# PULSEmech Language Relation Measurement v0 — Contract

Status: LRM-01 contract foundation. The source mapping verifier, relation
comparator, impact evaluator, automatic extractor and replay runner are not
implemented by this package.

Profile: `lrm_finite_reference_profile_v0`.

Planning source: commit
`47a3add6667542df6ef176285ed02bb1a741d9cf`, tree
`6d425c83e16fdc95cb2cfe1645a8060f3336dfaf` in
`HKati/pulse-release-gates-0.1`.

The [development plan](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md)
defines LRM-01 through LRM-06 and acceptance obligations A01–A24. The
[baseline inventory](../contracts/language_relation_measurement_v0_baseline.json)
binds the source documents. The
[profile](../contracts/language_relation_profile_v0.json) specifies the initial
logic, controlled source grammar, resource bounds and interpretation rules.

## 1. Measurement object and boundary

The object is a selected relation or relation group conveyed by a preserved
source communication, compared with a preserved processed communication in a
bound context. The instrument records preservation, change, breakage,
unresolved obligations, introduced relations and separately justified impact.

The following stages remain distinct:

1. Parse an artifact without duplicate JSON keys.
2. Validate its structural schema.
3. Bind its exact source, subject, context, profile and processing records.
4. Establish the admissible representation basis.
5. Evaluate the selected relational question.
6. Establish a separately scoped consequence, if supported.

None of these stages creates release authority. The v0 values are always
`authority_effect: "none"` and `release_authority_activation: false`.
Result artifacts serialize all six Transition Meter axes, with
`authority_status: "none"`.

LRM-01's contract tests inspect schema constraints, declared fixture integrity
and registration. Passing them does not execute stages 3–6 on natural language.
A fixture byte/anchor check is a test of that fixture's binding, not the new
runtime semantic verifier.

## 2. Required invariants

1. Preserved linguistic form does not establish preserved relation structure.
2. Equal words do not establish equal meaning or entity/event identity.
3. Changed words do not establish changed relations.
4. An introduced relation has its own evidence path and does not inherit the
   source assertion's evidence status.
5. An adapter's interpretation cannot alone prove its own correctness.
6. A relation difference does not alone establish a consequence.
7. An unresolved state cannot silently become a successful measurement claim.
8. An n-ary relation retains its full tuple and role structure whenever the
   measurement depends on joint relations.

Faithful representation is distinct from the truth of the represented claim
in the world. A preserved false assertion may be faithfully preserved.

## 3. Schema surface

The four Draft 2020-12 schemas are self-contained. Every `$ref` resolves into
the same document's `$defs`; validation requires no network retrieval. Their
`$id` values identify schemas and are not an instruction to fetch remote data.
All defined object shapes reject undeclared properties.

| Artifact | Schema |
| --- | --- |
| Input | `schemas/language_relation_input_v0.schema.json` |
| Verification | `schemas/language_relation_verification_v0.schema.json` |
| Measurement | `schemas/language_relation_measurement_v0.schema.json` |
| Manifest | `schemas/language_relation_manifest_v0.schema.json` |

JSON Schema checks shape and selected state combinations. It does not prove
hash correctness, source truth, reference resolution, independent acceptance,
coverage completeness, semantic equivalence or causal sufficiency. The
cross-record checks specified below are separate implementation obligations.

The runtime loader must reject duplicate keys before ordinary object
construction. A duplicate-key document cannot become valid by retaining its
last value. Types are not implicitly coerced.

## 4. Input contract

The input's `schema_version` is `language_relation_input_v0` and its
`artifact_kind` is `language_relation_input`. `case_id` identifies a case; it
must never select a precomputed judgment. The profile reference contains its
ID and the SHA-256 of its exact preserved bytes.

| Field | Required meaning |
| --- | --- |
| `sources` | At least the original and processed communications; optional context sources. |
| `source_anchors` | Half-open UTF-8 byte intervals in identified sources. |
| `representations` | Explicit `before` and `after` representations. |
| `interpretations` | The joint admissible interpretation/correspondence family and its completeness state. |
| `correspondence` | Candidate or justified entity, event, relation and relation-group mappings. |
| `coverage_obligations` | The source scope and interpretation work needed by each selected target. |
| `measurement_request` | Target questions, granularity, required obligations and processing-claim scope. |
| `processing_binding` | A concrete input/output processing link, or `null`. |
| `representation_basis` | Separate submitted basis records for the two representations. |
| `impact_model` | Explicit finite claims and support rules, or `null`. |

### 4.1 Exact sources and anchors

Each source records `source_id`, `role`, `language`, nullable `revision`,
`encoding: "utf-8"`, `content_sha256`, `byte_length` and a content carrier.
The carrier is either `inline_utf8` with `text`, or `package_path` with a
relative `path`. Inline text is useful for self-contained reference fixtures;
its UTF-8 encoding reconstructs the bytes to which the length and digest refer.

A runtime must resolve exactly one `before` source and one `after` source and
match them to the two representations. Context source IDs are explicit.
It must verify each claimed length and digest against actual bytes.

An anchor records `anchor_id`, `source_id`, `start_byte`, `end_byte` and the
digest of the selected bytes. The interval is `[start_byte, end_byte)`;
require `0 <= start_byte < end_byte <= source byte_length`. Both bounds must
fall on UTF-8 character boundaries. The selected byte digest is checked
independently of the whole-source digest.

No implicit Unicode, line-ending or whitespace normalization precedes this
binding. Any future normalizing adapter preserves the original bytes and a
separate position correspondence; it cannot silently redefine these offsets.

### 4.2 Entities, relations and groups

A representation records its ID, source ID, entities, finite domains, relations
and relation groups. Entity IDs carry types and source labels. Identical
labels on two sides are not an identity proof. Domains enumerate entity IDs;
an empty finite domain is a known domain, not a missing interpretation family.

A relation has a `relation_id`, recursive `expression`, source `anchor_ids`,
`discourse_type`, `modality` and nullable `speaker_entity_id`. The outer fields
type the communicated relation. Nested `CONTEXT` expressions preserve inner
speech or modality scopes. A group contains explicit relation IDs and does not
reduce them to pairwise links.

| Expression | Required structure |
| --- | --- |
| `ATOM` | Predicate and ordered role/value arguments. A value is an entity ID, bound variable or relation ID. |
| `NOT` | One operand. |
| `AND`, `OR` | Two or more operands; `OR` is inclusive. |
| `IMPLIES` | Separate antecedent and consequent. |
| `FORALL`, `EXISTS` | Bound variable, finite domain ID and body. |
| `REF` | Reference to an explicitly declared relation. |
| `CONTEXT` | Discourse type, modality, speaker and nested body. |

The profile declares predicate signatures, including complete role tuples.
An argument referring to a relation has proposition type. A variable takes
the types of its declared domain. The runtime checks predicates, role names,
role multiplicity, argument types, lexical binding and all references.

Expression references must be well founded for finite evaluation. A cyclic
`REF` graph is not a recursively true proposition. Evidence-support cycles
are represented separately in the support model and remain subject to grounded
closure rules.

The controlled source grammar is narrower than the relation model. It defines
exact HU/EN productions for approval and winning atoms, Boolean composition,
finite quantification, quotation, permission and obligation. Other declared
predicates can occur in documented reference annotations; their presence does
not claim a controlled natural-language parser for those predicates. Free
language, pronouns, ellipsis and unsupported inflection remain candidate or
reference input until an appropriate checker exists.

### 4.3 Correspondence and joint interpretations

A correspondence has an ID, a kind, nonempty `before_ids` and `after_ids`, a
basis, a nullable rule/reference ID and source anchors. Relation-group mapping
permits one-to-many or many-to-many surface reformulation. An unmatched
original relation is not automatically broken; an unmatched processed relation
is not automatically a new semantic assertion.

An interpretation variant records together:

- original relation IDs;
- processed relation IDs;
- correspondence IDs;
- context constraints.

These form one admissible joint configuration. A before-side pronoun choice
and an after-side choice constrained by the same context cannot be combined
as an unrestricted Cartesian product.

The variant's `before_relation_ids` and `after_relation_ids` select the roots
conveyed under that interpretation. Other relation declarations may name
subexpressions, proposition arguments or ground atoms for references and
witnesses. Declaring such a relation does not add it as an asserted root, does
not make its Boolean value true and does not establish a world fact. Its
discourse and modality fields describe its context if used; they are not
evidence that it occurred.

The family has four structurally distinct states:

| `state` | `variants` and meaning |
| --- | --- |
| `complete` | Nonempty; the declared relevant family is enumerated; `reason` is `null`. |
| `unknown` | Empty list with reason; a necessary binding or interpretation is unavailable. |
| `empty` | Empty list with reason; the specified constraints admit no variant. |
| `truncated` | A possibly empty partial enumeration with an explicit limit reason. |

The initial limit is 64 joint variants, 12 expanded Boolean atoms and 256 AST
nodes per variant. Limits are planned resource bounds, not benchmark results.
An empty family provides no vacuous preservation proof. Truncation provides
no exhaustive preservation or impact-free conclusion. A separately checked
counterexample remains a valid refutation of a universal preservation claim;
it does not establish which reading occurred or a complete result set.

### 4.4 Targets and coverage

Every target names its question and granularity, before/after IDs, required
coverage-obligation IDs and context sources. Coverage obligations name their
target, source scope, side, kind, state, evidence references and missing reason.

An input `fulfilled` state is a submitted annotation. It is not verified
coverage by itself. A runtime must check its source scope and supporting
record before using it to close a measurement obligation.

A target can be identified despite unrelated unresolved source material if
all alternatives remaining relevant to that target give the same result and
the required local obligations are closed. The instrument records why other
uncertainty is irrelevant. It does not replace local assessment with a single
whole-document confidence number.

An entire condition-group change and one lost subrelation may both be
recorded, but cannot be counted as independent failures without a declared
target/granularity rule.

### 4.5 Processing identity

`processing_claim: "structural_comparison"` permits a structural comparison
with no processing record. `processing_claim: "processing_change"` requires
`processing_binding` containing the processing ID, both source IDs, relevant
context IDs and evidence references.

Schema presence is not processing verification. The runtime checks that the
preserved evidence connects these exact input and output instances to this
operation. Without that binding, a source-to-source difference cannot be
promoted to an observed change during the named processing event.

## 5. Representation basis and independent acceptance

| Basis | Required result scope | Permitted claim |
| --- | --- | --- |
| `candidate_only` | `candidate_structures` | Structural diagnostic about the submitted candidate representations. |
| `accepted_reference` | `reference_interpretation` | Result conditional on the exact independently accepted reference annotation. |
| `profile_verified` | `controlled_source_profile` | Result within the supported source grammar after separate source-to-representation verification. |

Non-candidate input bases require a verification reference and an acceptance
reference. The acceptance reference names an inventory, entry and content
digest. The verifier's accepted inventory is configured independently of the
submitted package. A supplied inventory, its own hash, or a caller's
`profile_verified` string cannot authorize itself.

The verifier resolves the actual record's subject, exact input/profile
digests, completed checks, method and scope. A stale record does not become
current when an outer package is rehashed. The source mapper cannot act as
its own independent checker by calling its mapping function twice. Shared
byte-reading utilities do not remove the requirement for a separate semantic
checking path.

The result basis is no stronger than its weakest necessary representation,
correspondence or context premise. A candidate premise constrains the result
to `candidate_structures`; a necessary accepted-reference premise makes the
result conditional on that reference. Different target scopes remain explicit.

Every target result and impact record carries its basis and `claim_scope`.
An introduced-relation record is bound to its target and inherits only that
target's assertion boundary, not the source relation's evidence status.
Reports or diagram projections cannot omit these boundaries. Standalone
exports must carry the target boundary with the exported record.

The initial reference corpus is `synthetic_reference` with `candidate_only`
bases. Its annotations are not an invented owner-acceptance record. Expected
semantic results are conditional specification oracles, kept outside the input.

## 6. Verification artifact

`verification.json` binds `input_ref`, `profile_ref`, checker identity and
individual checks. A check names its kind, targets, execution state, nullable
result, reason and evidence references.

| Check execution | Result requirement |
| --- | --- |
| `not_run` or `error` | `result: null`; a nonempty reason is required. |
| `completed` | Result is `pass`, `fail` or `unresolved`. |
| Completed `fail` or `unresolved` | A nonempty reason is required. |

The before/after `basis_records` state the accepted basis, scope, actual check
IDs and acceptance reference. Non-candidate records require check IDs and an
acceptance reference. Cross-record validation requires exactly one record per
side and checks the truth of any elevation; schema validity alone cannot do so.

An unsuccessful or unperformed semantic check does not erase a successful
source-byte check. The separate records preserve both facts.

## 7. Measurement artifact

`measurement.json` binds the exact input, verification artifacts, profile and
evaluator. `execution.status` distinguishes a completed evaluation from an
unperformed or failed run. A `not_run` or `error` record has `results: null`,
a nonempty reason and no asserted witnesses, impacts or introduced relations.

A completed evaluation has nonempty target results. Completed evaluation is
not synonymous with a favorable relation outcome.

### 7.1 Relation state

| State | Obligation |
| --- | --- |
| `PRESERVED` | Justified correspondence and relevant coverage establish preservation under the declared profile and scope. |
| `CHANGED` | A justified correspondence exists and a relevant role, operator, condition, scope or communication binding differs. |
| `BROKEN` | Adequate processed-side coverage establishes that the original relation has no required continuation. |
| `UNDETERMINED` | Required evidence is absent, evaluation is incomplete or admissible variants yield distinct states. |

Missing extraction alone does not establish `BROKEN`. Complete candidate
structures may support a structural `PRESERVED` diagnosis while the source's
semantic preservation remains unverified; the mandatory scope identifies
that restriction.

### 7.2 Local assessment

| State | Meaning |
| --- | --- |
| `UNBOUND` | A necessary binding is missing and the compatible family is unknown. |
| `INCOMPATIBLE` | The bound, evaluated model has no compatible variant. |
| `UNRESOLVED` | Multiple target outcomes remain or required evaluation is incomplete. |
| `IDENTIFIED` | The relevant, nonempty and sufficiently closed family yields one target result. |

`IDENTIFIED` requires a nonempty compatible-variant list and one possible
relation state. That state must equal `relation_state`. Other assessment
states use `UNDETERMINED` and retain a reason. `CHANGED` and `BROKEN` require
a witness reference. A count or flag does not prove that the declared family
was completely evaluated; this is an evaluator obligation.

The target result also preserves required and closed obligation IDs, actual
verification IDs, witnesses and any reason. Non-candidate results require
verification IDs whose bound records actually support the claimed basis.

### 7.3 Introduced relations and witnesses

An introduced relation names a target and distinguishes `new_expression`,
`new_content`, `derived_explicitization`, `externally_supported` and
`unresolved`. It has its own support state and evidence or derivation path.
A supported record requires an evidence or derivation reference. Derivation
and external-support classes require their respective paths.

Proving introduction requires relevant original-side coverage. Without that
coverage, only the absence of an established correspondence can be asserted.
An entailment explicitly written in the output is not automatically a novel
semantic constraint; its derivation must be checked.

Witnesses name their target and relevant joint variants. They can preserve
role/operator differences, configurations, derivations, absence evidence,
alternative loss or support paths. A valuation binds values to declared atoms.
The runtime checks all referenced atoms, relations, premises and rules against
the exact profile. A prose description alone is not an independently checked
consequence proof.

In a valuation entry, `atom_id` is an alias for an existing `relation_id` in
the preserved input, not a new AST identifier or a free-form label. It must
resolve unambiguously to one named relation whose expression is a ground
`ATOM`: all arguments resolve to concrete entities or bound proposition
references, with no variable argument. Relation IDs used by a witness must
be unique across the two representations in that case. A compound target
that needs a valuation therefore declares its relevant ground atoms as
named helper relations, without automatically adding them to the variant's
asserted root lists. Every valuation contains at most one entry per `atom_id`.

The witness binds the valuation to its selected joint variants, target and
typed context. It supplies a hypothetical configuration for evaluating the
compared conditions; it is not observation evidence or an additional factual
premise. The checker verifies the applicable domain/context constraints and
requires corresponding atoms to receive compatible values under the
justified entity/relation correspondence. Valuations from different variants
or contexts cannot be spliced together to manufacture a difference. Any atom
needed by the claimed evaluation but not assigned or otherwise determined by
the preserved constraints leaves that witness incomplete. A Boolean witness
does not convert quotation, permission, obligation or supposition into an
observed event.

### 7.4 Impact and support

The input impact model declares claims, base-claim markers, evidence/source
references, conjunctive support rules, withdrawn claims and selected targets.
Markers are submitted data; only appropriately bound and verified bases seed
closure. The evaluator retains alternative support paths and explicitly
records unsupported cycles and claim/negation conflicts.

Closure is recomputed after withdrawal without seeding the old derived result.
An alternative remaining path may retain support. A closed unsupported cycle
cannot manufacture a base claim. Conflict does not permit arbitrary inference.

Every impact record identifies its target, basis, scope, conclusion and
supporting witnesses. Model possibility, condition satisfaction and support
change require witnesses. Mere reachability is `possible_impact` with an
unresolved conclusion. `observed_consequence` requires separate event evidence
and a witness; it cannot use a `candidate_only` basis.

Observed event evidence alone does not prove exclusive causation, necessity
or sufficiency. The corresponding causal axis remains separately justified.
For multi-target effects, the evaluator compares joint answer structures in
common configurations, not only independently aggregated answer sets.

### 7.5 Transition Meter axes

The artifact serializes `observation_status`, `binding_status`,
`consistency_status`, `reproduction_status`, `causal_status` and
`authority_status` within `status_axes`. Values are the canonical Transition
Meter values; `authority_status` is restricted to `none` for this extension.
No local relation result overwrites another axis.

Unresolved records identify the affected targets, obligation, reason code,
source anchors and explanatory detail. They survive reports and projections.

## 8. Manifest, deterministic bytes and replay

`manifest.json` binds the historical source baseline, optional implementation
base, profile, evaluator and package payloads. Each payload has a relative path,
role, byte length and SHA-256. Paths must stay inside the package, be unique,
and resolve without escaping through `..`, absolute paths or symlinks.
The manifest does not list itself or the mutable replay receipt as payloads.

Cross-record validation checks every payload against actual bytes and requires
the input, verification, measurement, source carriers, profile, schemas and
evaluator needed by the declared replay. Dependencies and independently
accepted reference objects must also be preserved when required. A remote URL
alone is not an offline dependency.

`replay` names the relative entrypoint, deterministic output paths and
`replay_receipt.json`. A real replay reconstructs source verification,
comparison and impact from preserved inputs, using the declared code and
profile. Comparing two saved reports is not replay. No new model call is part
of deterministic replay. A missing evaluator remains a reproducibility gap;
the runner cannot silently substitute current `main`.

The profile fixes UTF-8 output, indentation, key ordering, semantic-set
ordering, ordered argument/operand preservation and a terminal LF. Input
digests refer to exact stored bytes. This is a profile-specific serialization
rule, without a claim of JCS conformance.

A replay receipt records the new run's time, environment, evaluator binding,
execution state and comparison outcome. Its changing timestamp does not
change the deterministic original measurement core. A successful command may
produce a valid `CHANGED` or `UNDETERMINED` diagnostic; process exit status is
not a release-authority decision.

## 9. Synthetic examples and acceptance boundary

`synthetic_reference` inputs and `synthetic_contract_example` outputs are
specification material. Illustrative completed checks and result states in
those files are not records of executed source verification or measurement.
Consumers must retain provenance and must not ingest them as observed-run
evidence. Placeholder evaluator identities in synthetic examples do not claim
that the evaluator exists.

The fixture oracle `expected.json` is available only to the test controller.
Neither the automatic adapter nor the comparator may consume its labels or
use a case ID as a judgment lookup. Renaming a case cannot change its measured
semantic outcome. Raw adapter inputs exclude reference annotations and expected
labels; using source communications alone is a later LRM-05 obligation.

LRM-01 records testable contracts and a reference corpus. LRM-02 supplies the
separate source/representation checks; LRM-03 supplies the comparator; LRM-04
supplies impact evaluation; LRM-05 measures extraction; LRM-06 supplies actual
replay and diagnostic integration. A schema pass does not mark those later
work packages complete.

## 10. Release-authority and existing-component boundary

The normative chain remains:

recorded release evidence → `status.json` → declared gate policy → materialized
required gate set → `check_gates.py` → primary CI allow/block.

LRM artifacts are diagnostic. Their presence, absence or content changes must
not alter a release result on unchanged normative inputs. Contract/code tests
may fail CI when an implementation is broken; this does not turn a language
diagnosis into release evidence.

The existing Anchor input, field-comparison geometry and Paradox Diagram edge
semantics retain their meanings. Any language diagram is an explicitly scoped
diagnostic projection. It is not proof of its own source representation.
Shared runtime refactoring or authority integration requires a separate,
explicit implementation task and contract.
