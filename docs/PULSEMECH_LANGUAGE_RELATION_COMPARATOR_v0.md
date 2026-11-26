# PULSEmech Language Relation Comparator v0

Status: LRM-03 implementation contract for finite, source-bound relation
comparison. It extends the LRM-02 verifier and emits the existing verification
and measurement artifact formats. It does not implement downstream impact,
automatic language extraction or an offline replay runner.

Implementation base: commit
`b764073a1d551ceb718b6b55066b924b28fd2d78` in
`HKati/pulse-release-gates-0.1`, after the LRM-02 integration and its review fixes.

The historical LRM-01 planning baseline remains commit
`47a3add6667542df6ef176285ed02bb1a741d9cf`, tree
`6d425c83e16fdc95cb2cfe1645a8060f3336dfaf`. That historical binding and the
implementation base identify different things. The
[LRM-01 contract](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md),
[finite profile](../contracts/language_relation_profile_v0.json), four original
schemas and reference fixtures remain preserved. The profile's recorded
`contract_only` stage and unimplemented list are historical artifact fields;
this document records the added runtime capability without changing their
bytes or their pinned digest.

## 1. Measurement boundary

The comparator consumes an explicit input representation, its joint
interpretations, target selections, correspondence premises and coverage
obligations. It compares the selected relations within those boundaries. Its
answer is conditional on the representation basis recorded for each target.

| Result basis | Claim scope | Meaning in this implementation |
| --- | --- | --- |
| `candidate_only` | `candidate_structures` | A diagnostic about the supplied finite structures under their explicit candidate premises. It does not verify extraction or source meaning. |
| `accepted_reference` | `reference_interpretation` | A result conditional on exact source acceptance and separately accepted comparison premises. |
| `profile_verified` | `controlled_source_profile` | Available to LRM-02 source-basis records; LRM-03 does not establish this stronger basis for a comparison target. |

The last restriction is deliberate. The preserved profile defines identity
requirements and permitted rewrites, but it does not prove that two
participants or events are the same across source instances. An accepted
comparison reference remains a necessary premise even when both source
representations have been independently checked against the controlled
grammar. The target's strongest current basis is therefore
`accepted_reference`. A necessary candidate premise restricts its result to
`candidate_structures`.

Equal words, labels, role patterns or truth values do not establish identity.
Single-direction entailment does not establish general relation preservation.
Neither preservation nor an accepted reference establishes real-world truth.

Every output keeps `authority_effect: "none"`,
`release_authority_activation: false` and `authority_status: "none"`.
The comparator does not write normative release inputs, activate a gate or
modify the release-authority chain.

## 2. Runtime entry points

Run from a repository checkout with the existing Python dependencies:

```bash
python tools/measure_language_relations_v0.py \
  --input /work/case/input.json \
  --package-root /work/case \
  --output-dir /work/results/lrm03-run-001
```

For independently accepted source and comparison evidence, add both
configuration arguments:

```bash
python tools/measure_language_relations_v0.py \
  --input /work/case/input.json \
  --package-root /work/case \
  --trust-config /work/source-trust/config.json \
  --comparison-trust-config /work/comparison-trust/config.json \
  --output-dir /work/results/lrm03-run-002
```

`--package-root` defaults to the input file's parent. Each trust configuration
and every payload it pins must be outside the submitted package. The operator
selects those configurations independently of the package. The source trust
format remains the
[LRM-02 format](PULSEMECH_LANGUAGE_RELATION_INPUT_VERIFIER_v0.md); the additional
comparison review format is described in section 5.

The output directory must be a fresh path whose parent already exists. The
command creates it and writes exactly two diagnostic files:

| File | Schema and purpose |
| --- | --- |
| `verification.json` | [`language_relation_verification_v0.schema.json`](../schemas/language_relation_verification_v0.schema.json): fresh source checks and the comparison's actual review, correspondence and coverage checks. |
| `measurement.json` | [`language_relation_measurement_v0.schema.json`](../schemas/language_relation_measurement_v0.schema.json): target states, scopes, witnesses, introduced relations and unresolved obligations. |

The publisher refuses an existing output directory, including a symlink. It
opens new files without replacement, synchronizes the files and directory,
and removes only files it created if publication fails normally. This is not
a multi-file atomic transaction: an abrupt process or machine interruption
can leave an incomplete directory. A consumer must require both files and
check their recorded binding. There is no replay receipt or package manifest
in this CLI output.

| Exit code | Meaning |
| --- | --- |
| `0` | Diagnostic execution completed. Individual targets may be changed, broken, unbound, incompatible or unresolved. |
| `2` | Invalid input/configuration or an already existing output path. |
| `3` | An input/output operation or runtime consistency check failed. |

Exit zero is not a preservation or release decision. The CLI does not offer
an aggregate semantic PASS.

The Python API is:

```python
from pathlib import Path
from tools.language_relation_v0.comparator import (
    evaluator_reference,
    measure_bundle,
    measure_input,
)

bundle = measure_bundle(
    Path("/work/case/input.json"),
    package_root=Path("/work/case"),
    trust_config=Path("/work/source-trust/config.json"),
    comparison_trust_config=Path("/work/comparison-trust/config.json"),
)
measurement = bundle["measurement"]
verification = bundle["verification"]
```

The three keyword paths are optional. `measure_input` accepts the same
arguments and returns only the measurement. `measure_bundle` is the public
choice when preserving the verification artifact alongside it.
`evaluator_reference()` returns the current evaluator's tool ID, version and
content digest.

## 3. Fresh verification and artifact binding

The comparator invokes `verify_input` on the actual input path. It does not
accept a previously produced verification report as a substitute for that
execution. LRM-02 still owns strict JSON/schema/structure loading, raw source
and span binding, the separate controlled-language source check, acceptance
resolution and processing-instance checks.

The exact raw input digest is compared across the source-verification and
comparison steps, and the input bytes are read again before return. A changed
input prevents publication. External review files are checked against their
configured raw-byte digests before parsing. No whitespace, line-ending or
Unicode normalization substitutes for those bindings.

The combined verification preserves the source check outcomes and adds
performed LRM-03 checks. Its checker identity names the combined evaluator.
The measurement's `verification_refs` binds the verification ID and the digest
of its deterministic serialized bytes. Target results name that verification
ID. Cross-reference checks also require exactly one result per requested
target, target-owned coverage obligations, known variants and relations, and
valid witness references.

`evaluator_reference()` binds the LRM-02 checker files plus the comparator,
finite algebra, comparison-evidence resolver, CLI and the schemas used by the
new implementation. A code or schema change therefore changes the evaluator
content identity. Profile-defined serialization is deterministic; it is not
advertised as JCS serialization. Artifact IDs are derived from their content,
and no timestamp is added to the deterministic core.

The status axes start from the source verifier's axes; a newly executed
failed comparison check sets `consistency_status` to `conflicting`. A
`CHANGED` relation is a diagnostic outcome and does not by itself mean a
failed check. LRM-03 does not set `causal_status` or `reproduction_status` to
a successful state merely because comparison finished. Repeated
deterministic output is useful for testing, but is not the LRM-06 replay
receipt.

## 4. Finite comparison and assessment

### 4.1 Relation and identity model

The runtime works on complete role-bound argument tuples, including ternary
relations. It retains relation groups, proposition arguments, finite domains,
speakers, discourse type, modality and the declared operator tree. It does
not reduce a higher-arity relation to its pairwise projections.

Each interpretation is one joint choice of before roots, after roots,
correspondences and context constraints. The evaluator does not form an
unconstrained product of independent before/after readings. A correspondence
used in one variant cannot silently become a premise in another.

Entity and event identity requires a one-to-one selected mapping of compatible
types. Conflicting identity assignments, unresolved proposition identity and
missing necessary identity prevent a conclusive comparison. Relation/group
correspondence must cover the selected comparison boundary before it can
establish `PRESERVED`. A partial match cannot stand for a complete group
correspondence. A group withdrawal can establish `CHANGED` when its retained
after-side relations are fully mapped, the missing original continuation is
checked, and sufficient processed-side source coverage is closed.

Permitted structural rewrites are the profile's bound-variable renaming,
AND/OR permutation and association within a context, substitution through
admitted identity premises, and explicit group decomposition/recomposition.
Argument roles and multiplicity remain significant. Boolean equivalence is
available only for a selected plain `condition_impact` target; ordinary
relation comparison uses the permitted structural rewrites. Typed quotation,
supposition, permission, obligation and observed-event contexts are not
silently erased to obtain a Boolean equivalence.

REF dependencies are followed. A helper reached only under negation,
disjunction, implication, quantification or a typed context cannot be selected
as a free assertion by discarding its ancestors. Transparent plain-assertion
REF/AND decomposition is supported; selecting an enclosing expression retains
its full scope.

### 4.2 Four relation states and four assessment states

| Relation state | Operational meaning |
| --- | --- |
| `PRESERVED` | Admitted correspondence, comparison and required coverage establish the same selected relation within the target's claim scope. |
| `CHANGED` | A checked role, operator, context, condition or interpretation-family difference has a witness. |
| `BROKEN` | Sufficient processed-side scope and continuation checking establish loss of the selected original relation. |
| `UNDETERMINED` | A relation answer is not established under the required premises and scope. |

Missing extraction, missing correspondence or an empty target selection alone
cannot establish `BROKEN`. The actual processed roots and explicit mapped
groups must still be considered for possible continuation. Unresolved
identity leaves continuation unresolved.

For a plain condition target, continuation checking also considers Boolean
equivalence of actual roots and declared groups. An unspecified joint subset
of several processed conditions remains an unresolved selection; the
comparator does not invent that subset and declare it absent.

| Assessment state | Meaning |
| --- | --- |
| `IDENTIFIED` | Required target obligations are closed and the complete relevant joint family yields one conclusive answer. |
| `UNRESOLVED` | Outcomes disagree, necessary evaluation is incomplete, or a required premise cannot be accepted. |
| `UNBOUND` | Necessary source/processing binding or the interpretation family is not established. |
| `INCOMPATIBLE` | The declared family is empty, or no declared joint variant satisfies the supported context constraints. |

`possible_relation_states` and `compatible_variant_ids` preserve the outcomes
actually inspected. A completed run can contain an unresolved target and a
useful identified target together. Interpretation preservation compares the
alternatives in the declared joint family; loss of alternatives can be a
change even when one retained reading is individually preserved. This does
not identify which reading occurred in the world.

The runtime enforces the preserved finite bounds: at most 64 joint variants,
12 expanded Boolean atoms and 256 expression nodes per joint variant.
Unsupported nesting, expansion, typed Boolean contexts or exceeded limits
remain explicit incomplete checks. `unknown`, `empty` and `truncated` family
states are distinct. Truncation cannot establish exhaustive preservation or
absence; a checked difference witness from an inspected variant can remain
available without promoting the entire target to a complete answer.

### 4.3 Coverage and locality

An input `fulfilled` field is a submitted obligation state. The comparator
must still perform the check that closes the relevant scope. Candidate
comparison can close supported finite-model obligations only within
`candidate_structures`; it cannot turn that closure into source-extraction
completeness or an external context review. Required context/evidence work
does not become completed merely because the selected expression compares
successfully.

Independent reference closure resolves the target's own obligation IDs,
exact source IDs and actual completed review checks. A rejected required
review premise prevents closure of that target; it is not a successful
candidate fallback. Absent stronger acceptance can leave an explicitly
conditional candidate diagnostic, retaining its weaker basis.

The comparison-review resolver is target-local. Unselected correspondence
checks and another target's incomplete obligation do not replace the current
target's result. A required context source is collected from the target,
its obligations regardless of their side, used anchors, relation/proposition
dependencies, finite domains, speakers and joint context constraints.

There is an inherited limitation at the source-verification boundary:
LRM-02 aggregates context-source binding, and an unavailable/invalid required
source can prevent comparison for the submitted input as a whole. The new
target-local comparison review does not claim to make those earlier byte and
mapping failures local. Resource limits also apply to a declared joint
variant, not only its smallest selected subexpression.

## 5. Independent comparison review

The additive schema is
[`language_relation_comparison_evidence_v0.schema.json`](../schemas/language_relation_comparison_evidence_v0.schema.json).
It contains the two tagged document forms below and does not alter the four
LRM-01 schemas or LRM-02 trust format.

### 5.1 Configuration and record subjects

The configuration form is:

```json
{
  "schema_version": "language_relation_comparison_trust_config_v0",
  "review_files": [
    {"path": "target-main.json", "content_sha256": "<raw review SHA-256>"}
  ],
  "authority_effect": "none",
  "release_authority_activation": false
}
```

Angle-bracket values in documentation examples are placeholders, not
schema-valid digests or supplied evidence. A review is created from the
independent reviewer's actual checks of the final input. Copying the example,
inventing a reference string or moving input claims into another directory
does not supply that acceptance premise.

A review record has the following required fields:

| Field | Required binding |
| --- | --- |
| `schema_version` | `language_relation_comparison_review_v0`. |
| `verification_id` | Unique ID of this independently configured review. |
| `input_ref` | Input artifact ID and SHA-256 of the exact final input bytes. |
| `profile_ref` | The input's exact profile ID and digest. |
| `target_id` | One measurement target in this input. |
| `basis`, `method`, `claim_scope` | `accepted_reference`, `independent_comparison_reference_review`, `reference_interpretation`. |
| `checker_ref` | Reviewer tool/process ID, version and content identity. This is a recorded premise, not cryptographic authentication. |
| `reviewed_variant_ids` | The entire declared family, including variants later found incompatible. |
| `correspondence_checks` | Named correspondence IDs, exact reference IDs and actual execution states. |
| `coverage_checks` | Target-owned obligation IDs, exact source-ID sets and actual execution states. |
| `family_check` | Actual execution state and the exact declared family state. |
| `context_check` | Actual execution state and every relevant context-source ID. |
| `addition_checks` | Separately named after-side relations and support evidence; an empty list supplies no addition support. |
| `authority_effect`, `release_authority_activation` | `none`, `false`. |

Each check has `check_id`, `status`, `result` and `reason`. A completed check
records `pass`, `fail` or `unresolved`. A `not_run` or `error` check has a null
result and a nonempty reason. A failed/unresolved check also carries a reason.
Successful checks cannot be inferred from the presence of a row.

### 5.2 Exact correspondence, coverage and context checks

A correspondence check additionally contains `correspondence_id` and
`reference_id`. The input row must itself name `accepted_reference`, and its
`rule_or_reference_id` must equal that checked reference ID. Both `candidate`
and `profile_rule` rows prevent reference elevation. A profile rule such as
`IDENTITY_01` states a requirement; its name is not identity evidence.

A coverage check additionally contains `obligation_id` and `source_ids`.
Closure requires the input obligation to name this review's
`verification_id` in `evidence_refs`, to have submitted state `fulfilled`,
and to match the completed passing review check's source-ID set. The
obligation must belong to the selected target. Original-side coverage is
necessary for a novelty claim; processed-side coverage is necessary for a
broken-relation claim. A reviewed obligation still has to be sufficient for
that particular claim.

`family_check.family_state` and `reviewed_variant_ids` must exactly match the
declared family. A review of a partial family does not make it complete.
`context_check.context_source_ids` must include the actual relevant context
sources, including context-role sources carried by `both`, `before` or
`after` obligations and sources reached through used anchors. Additional
valid context IDs may be reviewed without transferring acceptance to a
different target.

The loader permits extra valid correspondence checks in a target record, but
only the checks necessary to the current comparison contribute acceptance.
It rejects duplicate paths, verification IDs, check IDs, duplicate checked
subjects and multiple reviews of the same exact input/profile/target.
Unknown or foreign-target subjects, stale input/profile bindings and changed
reference/source scopes cannot produce successful resolution.

The configuration and payloads use existing regular-file, relative-path,
no-symlink and strict-JSON readers. Limits include 128 review files and
16 MiB of aggregate review bytes; existing per-file limits also apply.
Raw pin mismatch, unsafe paths, invalid schema and duplicate identities are
invalid configuration. A structurally valid missing or unsuccessful review
is an explicit unresolved/failed diagnostic.

The resolver returns review IDs, check/reference IDs, the raw review digest
and raw configuration digest in its evidence references. These bind selected
bytes. They do not authenticate a reviewer or establish independence merely
from filesystem location.

### 5.3 Resolver API

```python
from tools.language_relation_v0.comparison_evidence import ComparisonTrust

store = ComparisonTrust.load(comparison_config_path, package_root)
review = store.target_review(
    document,
    fresh_input_ref,
    target_id,
    correspondence_ids=used_correspondence_ids,
    variant_ids=all_declared_variant_ids,
)
support = store.addition_support(
    document, fresh_input_ref, target_id, after_relation_id
)
```

`load(None, package_root)` returns an empty store. `target_review` returns
`result`, `reason`, `basis`, `claim_scope`, `evidence_refs`,
`verification_ids`, `closed_obligation_ids`,
`accepted_correspondence_ids`, `family_checked` and `context_checked`.
Partial accepted IDs remain visible when another required check is
unresolved; they are not an aggregate passing review.

`relevant_context_ids(document, target_id, correspondence_ids)` exposes the
same target/premise context closure used by the resolver. A caller must use
the current raw input reference and the mappings actually needed by its
claim. Resolving review evidence does not replace source verification or
finite comparison.

Both `target_review` and `relevant_context_ids` also accept the optional
keyword `relation_ids_by_side={"before": [...], "after": [...]}`. These
side-owned, unique relation IDs extend the context dependency closure; they
do not replace the original target's roots or change the exact input/target
subject. For an addition, the comparator supplies the union of its original
premise roots and the specific after-side addition. This includes context
anchors used only by an unpaired new relation, even if that relation has no
correspondence row. The same independently configured review must actually
cover that larger context scope before the addition can inherit an accepted
target boundary.

## 6. Introduced relations and separate support

After-side roots without an established continuation are introduction
candidates. They are not automatically new semantic content. The comparator
requires sufficient original scope, a stable outcome across the relevant
joint family and its own admitted identity premises before assigning a
conclusive novelty class.

| Novelty | Required conclusion |
| --- | --- |
| `new_expression` | An admitted original claim is preserved under a new explicit expression. |
| `derived_explicitization` | The satisfiable original premises establish the added relation in each retained joint variant. |
| `externally_supported` | The relation has its own separately resolved reference support. |
| `new_content` | The inspected original scope does not establish a continuation/derivation and no accepted separate support is resolved. |
| `unresolved` | Identity, source scope, variant completeness or necessary evidence is insufficient for the novelty decision. |

Each introduced record carries its target ID, evidence state, evidence
references, source-coverage IDs and, where applicable, a derivation witness.
It inherits the target's assertion boundary, not any original relation's
evidence status. Its own necessary premises must fit that boundary: a
candidate-only identity outside an otherwise accepted target cannot supply
an accepted derivation. The original target may remain identified while the
addition stays unresolved.

The combined verification contains a separate check for each assessed
addition. Evidence references may identify the checks used to classify an
unsupported addition; their presence alone does not change its
`evidence_status` to `supported`.

Finite derivation uses all conjunctive original premises in one variant and
repeats the check separately for every retained variant. It does not combine
premises across mutually exclusive readings. Inconsistent premises do not
establish arbitrary additions. Typed quotation/modal/event statements do
not become ordinary asserted consequences through this path.

An external addition check names `relation_id`, a nonempty list of
`evidence_refs` and its own actual check state. It must resolve to a completed
passing check in an exact independently configured review. A passing target
review with `addition_checks: []` supplies no addition support. This check
establishes conditional reference support only; observed-event verification
and downstream effects remain outside LRM-03.

## 7. Witnesses

Witnesses name their target, variants, before/after relation IDs, rule and
premise references and a concrete description. The implementation produces
role/operator differences, common-configuration differences, absence,
alternative-loss and derivation witnesses as applicable.

For a Boolean configuration, every exported `atom_id` must name one
unambiguous ground `ATOM` relation already present in the input. Its value
must cover the selected comparison and context constraints completely. The
runtime re-evaluates the serialized valuation before accepting it as a
difference witness. If the input lacks a complete ground-atom alias set, the
runtime retains a structural role/operator witness instead of inventing
atom IDs. A quantified difference can therefore be diagnosed without
claiming an exported valuation that the preserved input cannot identify.

A configuration witness is a hypothetical common model assignment. It does
not assert that those values occurred. An absence witness is conditional on
its recorded coverage; an alternative-loss witness is conditional on the
declared family; a derivation witness is conditional on its premises and
profile. A witness never supplies an omitted independent source or identity
check.

## 8. Existing component reuse

| Existing component | LRM-03 use and retained boundary |
| --- | --- |
| [LRM development plan](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md) | Supplies A05–A15, A21 and A24 as implementation/acceptance obligations. |
| [LRM input/measurement contract](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md) | Retains the existing relation, variant, target, evidence and output vocabulary. |
| [LRM-02 verifier](PULSEMECH_LANGUAGE_RELATION_INPUT_VERIFIER_v0.md) | Recomputes source binding, independent source mapping, acceptance and processing checks; its implementation and trust format remain unchanged. |
| `language_relation_v0/io.py` and `trust.py` | Reuses strict JSON, safe reads, digests, duplicate detection and the external-configuration boundary. No package-provided self-acceptance path is added. |
| [Finite profile](../contracts/language_relation_profile_v0.json) | Fixes the permitted operators, typed contexts, rewrites, domains, limits, serialization and claim boundaries. |
| [Mechanical transition language](PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md) | Supplies the existing relational transition interpretation. The comparator adds a language input path without changing Transition Meter vocabulary. |
| [Relation-preserving discrimination](PULSEMECH_RELATION_PRESERVING_DISCRIMINATION_v0.md) | Preserves selected roles, conditions and higher-arity structure instead of using surface similarity. |
| [Paradox relations and compatible change](PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md) | Retains joint compatibility and unresolved alternatives; no diagram projection or authority transition is introduced here. |
| [Anchor Integrity](ANCHOR_INTEGRITY_v0_1_CONTRACT.md) | Keeps exact subject/source evidence boundaries; a diagnostic relation witness is not a new release-authority anchor. |
| [Recognition-surface poisoning](PULSE_RECOGNITION_SURFACE_POISONING_v0.md) | Maintains the distinction between an attractive/expected-looking representation and independently checked evidence. |

## 9. Verification coverage and remaining work

The comparator regression module is
[`test_language_relation_comparator_v0.py`](../tests/test_language_relation_comparator_v0.py).
The original expected corpus is read only by the test controller. Runtime
inputs contain no expected verdict file, and the evaluator does not infer
results from case names. Case renaming can change the input/content identity
without changing the semantic target answer.

The tests exercise permitted rewrites, role and identity changes, operators
and finite quantifiers, communication boundaries, complete/incomplete
absence, additions with separate evidence, higher-arity differences, coupled
variants, local results, family/limit states and witness binding. Trust
regressions exercise stale/raw-tampered records, unsafe paths, unperformed
or failed reviews, target-local scope, candidate premises and exact evidence
closure. These are synthetic, bounded controls. They are not a measured
accuracy claim for unrestricted Hungarian or English extraction.

The development sequence remains:

| Work package | Remaining responsibility |
| --- | --- |
| LRM-04 | Persistence/support evaluation, downstream modeled impact, alternative support paths, recomputation after withdrawal and separately bound observed consequences. LRM-03 emits `impacts: []` and `support: null`. A `condition_impact` request currently compares the selected conditions and records that downstream impact is not evaluated. |
| LRM-05 | Automatic candidate import/extraction and provider-independent evaluation on fixed source cases. LRM-03 does not call a model or convert confidence into acceptance. |
| LRM-06 | Offline recomputation, execution receipts, diagnostic integration, optional diagram projection and verification that diagnostic presence/content cannot change normative release evaluation. The two current artifacts are inputs to that later work, not a completed replay capsule. |

The delivered comparator is therefore a finite diagnostic component within
the existing PULSEmech measurement path. Its usable conclusion is the target
state together with its basis, scope, actual checks, witnesses and unresolved
obligations; none of those fields may be dropped when exporting a result.
