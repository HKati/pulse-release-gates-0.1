# PULSEmech Transition Meter for Whole-System Discovery

## Evidence-Bound Matching of System-Level Requirements

## Status

```text
document_role: bounded_application_design
architecture_role: transition_meter_domain_application_design
reference_role: whole_system_discovery_contract
measurement_object: evidence_bound_whole_system_match_identity
implementation_status: design
search_or_retrieval_integration_status: not_implemented
authority_effect: none
canonical_dependency: PULSEMECH_TRANSITION_METER.md
revision_date: 2026-09-12
```

This document defines a proposed Transition Meter application for assessing
whether an identified candidate satisfies a declared system-level requirement.
It separates component relevance from evidence-bound satisfaction of the
relations, constraints, and boundaries that make the candidate a complete match.

Its scope covers requirement interpretation, candidate identity, relation-level
evidence, assessment-path reconstruction, match classification, and bounded
reporting. It specifies a design contract, an illustrative record structure,
and verification scenarios. It does not report an implemented search adapter,
a provider benchmark, or completed empirical validation.

**Must** and **must not** define requirements for this proposed application.
They do not amend the canonical Transition Meter, an active release policy,
a gate registry, or an existing authority path. The application remains
non-authoritative even when it establishes a complete candidate match.

The canonical architecture and the concrete release-authority interpretation
are identified in [References](#references).

---

## 1. Central position

A retrieval result can contain relevant tools, documents, standards, and
repositories without establishing a complete match for the requested system.

```text
retrieved components       != identified system
feature overlap            != verified requirement satisfaction
plausible composition      != evidenced relation structure
generated explanation      != reconstructed system identity
high ranking score         != verified complete match
```

Here, **whole-system match** means complete satisfaction of the declared,
claim-critical requirements within an identified boundary. It does not mean
complete knowledge of every property of the candidate.

For a relational system claim, the evaluation must establish which objects are
connected, which relations bind them, which identities and versions are
compatible, and which evidence supports the claimed behavior. Ordering and
transition-path evidence are required where the claim depends on them; they
must not be invented for a purely static requirement.

The proposed application makes the required relation and its evidence status
explicit. Its role is not to add another relevance score, but to preserve the
boundary between a relevant component and an evidenced system-level match.

---

## 2. The component-aggregation error

Let the interpreted user requirement be:

```text
Q = <N_Q, R_Q, C_Q, B_Q>

N_Q = required objects or component roles
R_Q = required relations between those objects
C_Q = constraints and claim conditions
B_Q = permitted system boundary
```

`N_Q` need not name particular products. A role such as "policy verifier" is not
an instruction to prefer one named verifier unless the user explicitly requires
that identity.

Let a candidate be:

```text
C_j = <N_j, R_j, E_j, V_j, B_j, I_j>

N_j = identified candidate objects
R_j = asserted candidate relations, each with its own evidence status
E_j = preserved evidence references
V_j = verifier identities, rules, and results
B_j = declared candidate boundary
I_j = candidate version, configuration, and assessment-time bindings
```

A match requires an evidence-preserving mapping:

```text
M: Q -> C_j
```

`M` must preserve object roles, relation endpoints, direction where meaningful,
required constraints, and boundary conditions. Equivalent implementations are
admissible when the mapping and domain evidence support the requested behavior.
A match does not require identical terminology or file layouts.

### 2.1 The unrecognized absence

An independently inspectable missing-evidence status for a particular required
relation must identify that relation in the evaluation structure.

This is a requirement about reproducible status, not a claim that a system can
never suspect an omission without a predefined field.

```text
required relation represented
-> its support, absence of support, or contradiction can be recorded

required relation omitted from evaluation
-> component coverage may conceal the omission
```

If the evaluator records documents, features, citations, and component scores
but drops a claim-critical relation, a high-coverage result can appear complete
without testing the condition that makes the parts one system.

The Transition Meter application must preserve that unresolved relation. It
does not guarantee discovery of every possible candidate.

### 2.2 The logical gap

Component coverage can have the following form:

```text
For every required feature f,
there exists some candidate c with evidence for f.
```

That does not imply:

```text
There exists one candidate c
with evidence for every required feature and every required relation,
under one jointly compatible system boundary.
```

The first statement permits a different witness for each feature. The second
requires one coherent candidate-level witness, including integration evidence.

There is a second gap even when all features occur within one project. Let a
projection `P_N` retain a system's component inventory but discard its relations.
Two systems can then satisfy:

```text
P_N(C_a) = P_N(C_b)
R_a != R_b
```

For example, both contain an evidence verifier and a release job. In one system
the verifier's failure blocks that exact release; in the other the release job
can proceed independently. The component inventory is equal, while the required
enforcement relation is different.

Consequently, a decision based only on that projection cannot distinguish those
two cases. This is a property of the stated model, not an empirical claim about
a named search provider's internal representation.

### 2.3 Required-set derivation is part of the proof obligation

The adapter must preserve both the original request and the derivation of `Q`.
Each materialized requirement must have a source span or an explicitly declared
derivation rule. Each claim-critical request clause must map to requirements,
an explicitly accepted exclusion, or a visible unresolved interpretation.

Derived requirements must be distinguished from the user's literal wording.
Ambiguity must not be resolved by silently selecting the easiest interpretation.
An exclusion that narrows a required condition must bind explicit acceptance
of the changed request scope and produce a new requirement-set identity. It
cannot preserve a complete-match claim for the broader original request.

The requirement record must bind:

```text
exact query carrier and digest
requirement-set identity and revision
clause-to-requirement trace
explicit additions, exclusions, and unresolved interpretations
materialization rule or procedure identity
interpretation reviewer/verifier and review basis
semantic coverage review status
materialized-set digest
```

A digest establishes the identity of the materialized set. It does not prove
that the set faithfully represents the original request. Semantic coverage
review is a separate, declared dependency; automated completeness must not be
claimed merely because a parser produced a list.

An empty required set, an omitted claim-critical clause, or an unresolved
claim-critical interpretation must block a complete-match claim. Otherwise an
evaluator could certify seven requirements after silently dropping the eighth.

### 2.4 The bounded all-elements rule

Let `K(Q)` be the nonempty set of claim-critical object, relation, and constraint
obligations admitted by the reviewed requirement interpretation. For each
obligation `k`, record one evaluation value:

```text
PASS         accepted evidence satisfies the declared acceptance rule
FAIL         accepted evidence establishes a violation of that rule
UNRESOLVED   the available evidence does not establish either result
```

These are application-local evaluation values, not replacements for the
canonical Transition Meter axes.

The complete-match predicate is:

```text
complete_match(Q, C_j) =
    record_integrity_valid
AND requirement_interpretation_accepted
AND K(Q) is nonempty
AND candidate_identity_version_boundary_bound
AND joint_mapping_consistent
AND for every k in K(Q): evaluate(k, C_j) = PASS
AND assessment_replay_accepted
```

Acceptance is relative to the preserved requirements, evidence, domain rules,
verifier identities, and assessment scope. It is not a truth oracle or a claim
of universal completeness.

Scores may order candidates for inspection. They must not compensate for a
failed or unresolved claim-critical obligation. Evidence from different
versions, runs, or configurations must not be pooled unless the claimed
compatibility relation is itself established.

A composite system is permitted when its boundary is declared and its
integration relations are verified. A collection of unrelated tool references
is not automatically such a composite.

This predicate qualifies one candidate under one accepted requirement set. It
does not establish exhaustive discovery, relative superiority, or uniqueness.
Section 9 defines the distinct outcomes for unassessed candidates, incomplete
support, established violations, and unavailable retrieval.

---

## 3. Evidence acceptance and claim scope

### 3.1 A source reference is not a satisfied obligation

Every claim-critical obligation must declare the evidence needed to evaluate it.
A source can establish that a capability is described without establishing that
the capability is implemented, exercised, or enforced at the required boundary.

| Claim class | Required evidence meaning |
| --- | --- |
| Documented capability | The identified source actually makes the specified claim. |
| Implemented capability | Source or other accepted implementation evidence establishes the specified behavior at the bound revision. |
| Observed behavior | Preserved execution evidence binds the behavior to identified inputs, outputs, conditions, and occurrence. |
| Enforced relation | Evidence establishes that the required condition controls the specified decision boundary; a diagnostic result alone is insufficient. |
| Reproduced assessment | A separate execution reconstructs the declared evaluation result from preserved inputs under identified rules. |

These are different claims, not interchangeable confidence levels. One artifact
may support several claims, but the mapping and acceptance rule for each claim
must be explicit. A successful bounded execution does not prove behavior in
unexamined configurations, and structural source inspection does not itself
establish that a particular execution occurred.

### 3.2 Per-obligation evidence binding

An evidence reference must resolve to an exact preserved carrier and a defined
location or object within it. The reference must identify its applicability to
the candidate, version, configuration, and claim boundary.

```text
obligation
-> candidate object or relation
-> exact evidence location
-> declared acceptance rule
-> identified domain evaluation
-> PASS, FAIL, or UNRESOLVED
```

A source appearing in a document-level inventory provides no support for an
obligation unless the obligation has its own evidence mapping. Several sources
may jointly support a relation when their identities and compatibility are
established. They need not occupy one file or one repository.

Preservation and semantic validity are separate. A digest identifies a carrier
and permits integrity checking against a bound reference; it does not establish
that the carrier's assertions are true. Evidence origin, trust assumptions,
acceptance rules, verifier identity, and evaluation limits must remain explicit.

### 3.3 Unsupported, contradicted, and out of scope

**Unsupported** means that the admitted evidence does not establish the claim.
It does not establish the claim's negation. Missing evidence therefore yields
`UNRESOLVED`, not automatically `FAIL`.

**Contradicted** means that admitted evidence establishes a conflict with the
claim under the declared acceptance rule. A claim-critical contradiction yields
`FAIL` for the affected obligation.

**Out of scope** means that evidence concerns a different version, occurrence,
configuration, or boundary. It cannot be transferred into the current assessment
without an accepted compatibility or applicability relation.

An older source is not automatically stale for a historical claim. Freshness is
relative to the assessed condition and target context, not simply publication
age or retrieval order.

### 3.4 Semantic acceptance boundary

The structural verifier checks identities, mappings, preserved results, and
application rules. Domain methods determine what counts as valid evidence for a
capability. The record must identify those methods and any expert judgments on
which the classification depends.

Replaying an accepted interpretation or domain-review result verifies its use
in the assessment. It does not independently repeat that semantic judgment
unless the declared replay includes the corresponding method. Reproducibility
must not be presented as proof that all accepted premises are correct.

---

## 4. Minimal relational counterexample

Consider a declared requirement:

> The release operation must not proceed unless the identified verifier accepts
> the required evidence for that exact release subject and execution context.

Construct two systems with the same component inventory:

```text
components = {evidence carrier, verifier, policy, release operation, status}

System A:
evidence -> verifier -> required acceptance condition -> release operation
verifier rejection -> release blocked

System B:
evidence -> verifier -> diagnostic status
release operation -> independent execution path
```

Both contain the required component classes. Both can display a successful
verifier result on an accepted input. Only System A contains the stipulated
control dependency in this construction.

A component-only projection cannot distinguish them:

```text
P_N(A) = P_N(B)

required_control_relation(A) = present
required_control_relation(B) = absent
```

This is a counterexample to the inference that matching component inventories
establish matching system behavior. It is a constructed model, not a measurement
of any named implementation.

The distinguishing evidence concerns the relation itself: which verifier result
controls which release operation, under which identities and conditions, and
what happens when the required condition is not satisfied. A negative execution
can test that relation within its captured scope; it does not by itself exclude
all unobserved bypass paths.

The corresponding evaluation outcomes depend on available evidence:

```text
control relation established under the accepted rule -> PASS
independent release path established as a violation -> FAIL
only component inventory available                  -> UNRESOLVED
```

The third case must not be silently converted into either of the first two.

---

## 5. Distributed system identity and discovery coverage

System-level evidence may be distributed across architecture documents,
schemas, policy files, builders, workflows, evidence packets, artifacts,
verifiers, tests, execution records, and reconstruction results.

No single document must contain the entire proof. Retrieving several carriers
does not, however, establish that their identities and relations compose into
the claimed mechanism. Cross-carrier bindings remain separate obligations.

Two failure classes must be distinguished.

**Candidate invisibility:** a potentially matching system is absent from the
observed candidate set. Without an appropriate discovery trace, the cause is
unresolved; absence must not automatically be attributed to ranking, indexing,
or personalization.

**Relation invisibility:** a candidate is available, but an assessment omits or
fails to verify a claim-critical connection and still declares a complete match.

Candidate invisibility concerns discovery coverage. Relation invisibility
concerns unjustified claim promotion. This application constrains the second
and records the limits of the first; it does not guarantee complete discovery.

---

## 6. Cross-domain integration boundary

Specialization is not the defect. The defect is the promotion of correct local
results into a system-level conclusion without an evidenced integration path.

For example, an attestation, policy rule, green workflow, valid signature, and
final status can each be correctly inspected while their joint binding remains
unverified.

The missing questions are:

```text
Does this attestation concern this exact subject and producing run?
Did this policy govern this decision context?
Were all required conditions included?
Did this verifier evaluate those conditions?
Did this workflow outcome carry the authoritative decision?
Can the decision be reconstructed from the preserved evidence?
```

The same logical issue appears in retrieval: correct partial findings do not
prove their composition. The shared instrument is the evidence-bound relation
structure, not a replacement for specialist methods or domain validity.

---

## 7. Transition identity in system discovery

### 7.1 The observed recommendation transition

A search interaction can be represented as:

```text
S0: expressed need, with no match yet established in this record
-> relation assertion: candidate C_j is presented as satisfying Q
-> S1: a displayed recommendation carrying that assertion
```

The changed relation is the **recorded or asserted requirement-to-candidate
relation**. The search does not cause the candidate to acquire the capability.
An assertion transition must not be misreported as a transition in the
candidate's physical or implemented behavior.

### 7.2 Two paths, not one

Separate:

```text
P_provider:
actual discovery, source selection, ranking, and generation path

P_assessment:
recorded requirement derivation, evidence evaluation, and match classification
```

Query and answer carriers may expose the endpoints of `P_provider` without
exposing its internal elements. Those internal elements remain unobserved.

A later evaluator can establish `P_assessment` from preserved evidence. That
record is not a reconstruction of the provider's actual selection process
unless separate evidence binds it to that process.

Consequently:

```text
provider selection path unavailable
can coexist with
candidate match independently verified within a declared scope
```

The reverse is also possible: a well-observed retrieval path can return a
candidate whose required capabilities remain unverified.

### 7.3 Ordered, edge-level binding

Each recorded assessment transition element must preserve its own identity, sequence,
input and output references, changed relation, path effect, evidence,
verification rule, and boundary. Event time and observation time are distinct.
Unknown provider event times must remain unknown; source collection time is
not a substitute for the time a capability began to exist.

A sequence index can establish recorded order without establishing elapsed
time or causality. The canonical six status axes remain explicit. Full causal
closure, provider-internal traces, and feedback evidence are not prerequisites
for a bounded candidate assessment that does not claim them.

The measurement object is:

```text
evidence_bound_whole_system_match_identity
```

It asks which requirements are bound to which exact candidate evidence, what
assessment path was actually executed, what remains unresolved, and which
bounded match statement that record supports.

The scope of `status_axes` must be explicit. For a candidate-assessment record,
the axes describe `P_assessment`. Provider-path visibility is recorded separately
and must not silently overwrite the observation or reproduction status of that
assessment. A separate provider-path record is required for stronger claims
about the actual discovery or generation process.

---

## 8. Illustrative AI release-decision requirement profile

An artifact-bound release-decision requirement can be decomposed into the
following domain profile. The role structure follows the canonical
[PULSEmech Technical Overview](../PULSEMECH_TECHNICAL_OVERVIEW.md), with
application-neutral meanings where equivalent implementations are permitted:

```text
R_release = <S, E, A, P, G, V, F, D_tau>

S     exact release subject and producing-run binding
E     recorded evidence bound to that subject and run
A     artifact or carrier identity
P     policy applicable to the decision context
G     explicitly determined required conditions
V     identified verifier and its evaluation behavior
F     final evaluation state of those conditions
D_tau resulting release-authority decision transition
```

In the concrete PULSEmech mapping, `G` is the materialized required gate set and
`F` is the final gate-state carrier. Those implementation names must not be
silently imposed on every other candidate.

A candidate using a different representation can satisfy the underlying
requirement if its evidence establishes the same requested behavior and
bindings. A literal gate-set artifact is mandatory only when the interpreted
request explicitly requires it.

Illustrative claim-critical relations include:

| Relation obligation | Required meaning |
| --- | --- |
| Subject/run to evidence | The evaluated evidence concerns the exact subject and producing run. |
| Subject to artifact | The decision concerns the identified artifact, not a neighboring version. |
| Policy to decision context | The evaluated policy is the applicable policy for that decision. |
| Policy to required conditions | The evaluated condition set preserves all declared obligations. |
| Verifier to evidence and conditions | The identified verifier evaluated those inputs under the declared rules. |
| Evaluation to final state | The final state derives from that evaluation rather than an unrelated status. |
| Final state to authority decision | Missing or nonpassing required evidence cannot authorize the release. |
| Preserved record to replay | A separate verifier can reconstruct the claimed result within the declared replay boundary. |

This table is an illustrative requirement profile, not a candidate result.
An actual assessment must derive its obligations from its own preserved request
and accepted interpretation. The profile must not be imposed on requests that
do not require these relations.

Evidence for `E` and part of `S` does not automatically establish `P`, `G`, `V`,
`F`, and `D_tau`. Conversely, the absence of PULSEmech-specific names in a
candidate is not evidence of noncompliance with the functional requirement.

---

## 9. Search-adapter status model

### 9.1 Canonical axes and application-local fields

The adapter must serialize all six canonical axes and identify the transition
or assessment they describe. The vocabulary is inherited from the
[canonical Transition Meter](../PULSEMECH_TRANSITION_METER.md), not redefined by
application-local result labels.

| Canonical field | Scope in a candidate-assessment record |
| --- | --- |
| `observation_status` | Which assessment events and evidence acquisitions were observed or reconstructed? |
| `binding_status` | Are the relevant identities, versions, boundaries, and evidence references bound? |
| `consistency_status` | Are the mappings and accepted evidence internally consistent? |
| `reproduction_status` | Has the declared assessment replay been reproduced? |
| `causal_status` | What causal claim, if any, is supported about the identified assessment transition? |
| `authority_status` | Fixed to `none` under this application contract. |

For example, `unbound` and `stale` are binding statuses, while `not_tested` and
`reproduced` are reproduction statuses. No one axis may overwrite another.
Record-level summaries do not replace per-obligation or per-element states.

The following are independently serialized **application-local fields**:

```text
requirement_interpretation_status
candidate_match_status
source_claim_support_status
selection_path_status
alternative_candidate_closure_status
retrieval_status
search_outcome
assessment_coverage_status
complete_match_statement_eligible
```

An unknown provider selection path does not establish a functional violation
by the candidate. `complete_match_statement_eligible` controls the scope of an
evidence-based statement; it grants no release, deployment, device-control,
procurement, or recommendation-execution authority.

### 9.2 Classification prerequisites

Record validation precedes candidate classification. An invalid record yields
`INVALID_RECORD` as a validation outcome, not as a candidate capability class.
It must not produce an accepted match result.

Classification requires an accepted, nonempty requirement interpretation and
an identified candidate assessment boundary. Required identity, version,
configuration, and acceptance-rule bindings must be established to the extent
specified by that boundary. Without these prerequisites, classification remains
`NOT_EVALUATED`, with explicit blockers. Provisional local findings may be
retained but must not be presented as a verified match for the original request.

A demonstrated violation of a claim-critical identity or integration obligation
is evaluated as `FAIL`. Unavailable evidence for that obligation is
`UNRESOLVED`; it is not a demonstrated violation.

### 9.3 Candidate classification

After the prerequisites are satisfied, apply the following precedence:

| Condition | Candidate classification |
| --- | --- |
| Accepted evidence establishes a claim-critical violation (`FAIL`). | `CONFLICTING_MATCH` |
| The complete-match predicate in Section 2.4 is satisfied. | `VERIFIED_COMPLETE_MATCH` |
| No claim-critical violation is established; at least one obligation passes, but the complete-match predicate is not satisfied. | `VERIFIED_PARTIAL_MATCH` |
| No obligation passes and no claim-critical violation is established. | `PLAUSIBLE_UNVERIFIED_MATCH` |

`PLAUSIBLE_UNVERIFIED_MATCH` denotes an unverified candidate hypothesis, not an
accepted plausibility measurement. A partial result verifies only its declared
subset. It does not prove that the remaining capabilities are absent.

Every complete-match blocker must remain explicit. Even when individual
obligations pass, unresolved joint binding or unaccepted replay prevents
complete classification. A submitted complete label is not evidence that the
predicate holds; it must agree with recomputation.

### 9.4 Answer claims are a separate assessment

A generated statement has its own candidate binding, source mapping, and support
assessment. The adapter must distinguish `supported`, `unsupported`,
`contradicted`, and `not_evaluated` for each inspected statement.

A faulty explanation and a valid candidate can coexist. Independently verifying
a candidate later does not retroactively repair the original answer's citations
or reveal the provider's selection path. A source supporting a documented claim
also does not automatically satisfy an implementation-level obligation.

An explanation generated from the verified assessment must preserve the
candidate classification and its blockers. Unverified supplemental statements
must remain explicitly unverified and cannot supply a missing requirement.

### 9.5 Retrieval outcome and assessment coverage

`retrieval.retrieval_status` records terminal-result availability at the
identified retrieval surface within the declared observation boundary. Its
values are `not_evaluated`, `available`, and `unavailable`. `available` includes
a preserved terminal result with an empty candidate inventory. Query acceptance
alone does not establish availability; `unavailable` requires an evaluated
observation boundary, not merely missing or unevaluated fields.

`result.search_outcome` is a derived search-level conclusion, not an alias for
`retrieval.retrieval_status`. For a valid record, apply the following rules in
order; the first matching row determines the outcome. Assessment conditions
refer only to the bound search scope associated with that retrieval observation,
not to an independent candidate assessment obtained by another route.

| Condition | `result.search_outcome` |
| --- | --- |
| `retrieval.retrieval_status = not_evaluated` | `not_evaluated` |
| `retrieval.retrieval_status = unavailable` | `RETRIEVAL_UNAVAILABLE` |
| `retrieval.retrieval_status = available`, but no bound search-assessment scope is established | `not_evaluated` |
| `retrieval.retrieval_status = available` and at least one validated candidate in that scope is `VERIFIED_COMPLETE_MATCH` | `VERIFIED_MATCH_FOUND` |
| `retrieval.retrieval_status = available`, scope coverage is `complete`, and no candidate in that scope is `VERIFIED_COMPLETE_MATCH` | `NO_VERIFIED_MATCH` |
| `retrieval.retrieval_status = available` and scope coverage is `not_evaluated` | `not_evaluated` |
| `retrieval.retrieval_status = available` and scope coverage is `incomplete` | `incomplete` |

`VERIFIED_MATCH_FOUND` establishes an in-scope verified match; it does not make
unfinished scope coverage complete or establish exhaustive discovery. Coverage
and candidate classifications remain independently derived. A serialized
`search_outcome` inconsistent with these rules must be rejected. This derivation
does not overwrite `candidate_match_status` for an independently sourced
candidate, including when retrieval is unavailable.

`NO_VERIFIED_MATCH` and `RETRIEVAL_UNAVAILABLE` are search-level outcomes, not
candidate capability classes.

`NO_VERIFIED_MATCH` means that no complete match was verified within an explicit,
completed assessment scope. The scope must bind the exact candidate inventory,
shared query and requirement-set identities, and each candidate assessment.
An available terminal result with an empty candidate inventory may also be
reported in that limited scope. It does not establish global nonexistence.

`RETRIEVAL_UNAVAILABLE` means that a terminal retrieval result was unavailable
to the assessment within the declared observation boundary. It establishes
neither an empty index nor a failure of any candidate. It can coexist with an
independent assessment of a candidate obtained by another declared route.

An unfinished assessment remains `incomplete`. Invalid or unassessed candidate
records cannot be silently counted as completed negative assessments. An
assessment may be complete as an evaluation procedure while retaining
`UNRESOLVED` obligations; procedural coverage is not evidence completeness.

Observed candidates, evidence-excluded candidates, remaining admissible
candidates, and the unobserved candidate universe must remain distinct.
A complete match for one candidate does not establish that it is the only,
best, or most precise solution. Those require separate comparison criteria
and an appropriate assessment scope.

---

## 10. Transition-aware assessment and replay

The proposed assessment path is:

```text
expressed need
-> exact query record
-> requirement interpretation and coverage review
-> materialized claim-critical obligation set
-> candidate discovery
-> exact candidate and boundary binding
-> per-obligation evidence collection
-> domain-specific evaluation
-> joint identity and integration checks
-> explicit unresolved and conflicting results
-> preserved assessment replay
-> candidate classification
-> bounded explanation
```

Discovery and verification are separate operations. Candidate generation may
use an appropriate retrieval method without granting its ranking or selection
score authority to establish complete satisfaction.

### 10.1 Acyclic proof construction

The proof objects must be constructed in dependency order:

```text
I  = preserved assessment-input manifest
E  = original obligation-evaluation payload derived from I
E' = independently executed replay payload derived from the same I
R  = comparison record binding I, E, E', and the replay rule
O  = final classification envelope derived from I, E, and R
```

`I` binds the query, accepted requirement interpretation, candidate identities,
source snapshots, domain results used as premises, acceptance rules, verifier
revision, and relevant environment parameters. It must not include a final
complete-match conclusion as an input premise.

`E` and `E'` contain the per-obligation results, joint-mapping diagnostics, and
complete-match blockers available before replay acceptance. `R` records whether
the declared comparison succeeded. `O` applies the all-elements predicate and
records the canonical status axes and bounded classification.

A standalone checker must verify the input identities and recompute the
classification from those dependencies. Merely comparing two supplied labels
or trusting a supplied replay-success flag is insufficient. Re-execution uses
an identified verifier in a separate process or other declared isolation
boundary. It need not use a different algorithm; such replay does not eliminate
shared implementation errors.

No object must include its own final digest as a required hashed field. Carrier
identity and reference construction must follow this acyclic dependency graph.

### 10.2 Comparison boundary

The replay contract must specify whether it compares exact bytes or a defined
canonical evaluation payload. Any normalization must have a pinned rule and
its own carrier identity; it must not discard an evaluation-relevant difference.
Execution timestamps and replay-run identities may be preserved separately
rather than forcing unrelated runs to have identical operational metadata.

If replay mismatches or cannot be completed, `assessment_replay_accepted` is
false and a complete-match statement is blocked. The reason must distinguish
mismatch, unavailable input, execution failure, and a check that was not run.
These are application diagnostics, not invented canonical status values.

### 10.3 What replay does not establish

Reissuing a query to a changing external service is a new observation, not
replay of the original assessment. A fresh source page or a different verifier
revision must not silently replace its pinned predecessor.

When an interpretation or domain result is a preserved premise, replay checks
the declared computation from that premise. Independent validation of the
premise requires its own evidence and procedure. Required nondeterministic
checks must retain their reproducibility limits; they cannot be declared
reproduced merely because the final prose is similar.

Assessment replay does not reconstruct the provider's hidden retrieval path,
prove universal discovery, or establish continuing validity after the bound
candidate or requirement context changes.

---

## 11. No-silent-completion rule

For every claim-critical obligation, the record must preserve:

```text
requirement identity and query derivation
candidate mapping and boundary
acceptance-rule identity
evidence references, including exact supporting locations
verifier identity and verification result when verification is claimed
PASS, FAIL, or UNRESOLVED
reason codes and relevant canonical status axes
```

A missing, unbound, stale, unsupported, conflicting, or nonreproducible required
link must block a complete-match statement under the declared acceptance rules. The
adapter must not silently erase the requirement, transfer proof from another
candidate or version, or replace the missing relation with explanatory prose.

Missing evidence maps to `UNRESOLVED`, not automatically to `FAIL`. A stale
artifact is stale relative to the claim and assessment context; an older,
version-pinned source is not automatically stale for a historical claim.

Partial reporting remains permitted. The blocked object is the unsupported
**complete-match statement**, not every useful answer.

The rule applies both before and after classification:

```text
query -> requirements:
no silent deletion or weakening of a claim-critical condition

requirements -> evidence:
no silent cross-candidate or cross-version composition

evaluation -> explanation:
no silent promotion of partial or unresolved support to completeness
```

> Language generation may explain verified edges. It must not manufacture the
> edges required to turn components into a system.

The reporting constraint creates no external authority. Every record in this
application retains `authority_effect: none` and canonical
`authority_status: none`, including a complete candidate assessment.

---

## 12. Non-authoritative record outline

The following YAML specifies field groups and reference relationships. It is
not a shipped schema, a valid observation fixture, or executable verifier input.
`REQUIRED_` strings are explanatory placeholders, not accepted identities.
`null` represents unavailable data in this outline and cannot satisfy a required
binding. The example intentionally contains no completed assessment.

```yaml
record_status: design_example
record_type: whole_system_discovery_v0
record_id: REQUIRED_RECORD_ID
contract_revision: proposed_v0
authority_effect: none

query:
  carrier_ref: REQUIRED_QUERY_CARRIER
  sha256: REQUIRED_QUERY_BYTES_DIGEST
  language: REQUIRED_LANGUAGE
  submitted_event_time: null
  observation_time_binding: REQUIRED_TIME_AND_UNCERTAINTY

retrieval:
  provider_identity: null
  surface_identity: null
  session_class: unknown
  observation_window: null
  retrieval_status: not_evaluated  # Availability observation; Section 9.5.
  candidate_origin_ref: REQUIRED_DISCOVERY_OR_OTHER_ORIGIN_RECORD
  selection_path_status: unavailable

answer:
  carrier_ref: null
  sha256: null
  carrier_kind: unavailable
  terminal_answer_observed: false
  observation_time_binding: null
  claims: []
  # Each claim binds its exact answer location, candidate, obligation refs,
  # source-evidence locations, support status, and assessment/verifier ref.

requirement_set:
  requirement_set_id: REQUIRED_REQUIREMENT_SET_ID
  query_sha256: REQUIRED_QUERY_BYTES_DIGEST
  materialization_rule_ref: REQUIRED_RULE_ID
  materialized_set_sha256: REQUIRED_SET_DIGEST
  derivation_trace_ref: REQUIRED_CLAUSE_TO_REQUIREMENT_TRACE
  interpretation_review_ref: null
  requirement_interpretation_status: unresolved
  explicit_exclusions: []
  unresolved_interpretations: []
  obligations:
    - obligation_id: REQUIRED_OBLIGATION_ID
      obligation_kind: relation
      critical: true
      query_clause_refs: [REQUIRED_QUERY_LOCATION]
      derivation_basis: REQUIRED_LITERAL_OR_DERIVED_BASIS
      source_object_ref: REQUIRED_SOURCE_ROLE
      target_object_ref: REQUIRED_TARGET_ROLE
      relation_type: REQUIRED_RELATION_TYPE
      acceptance_rule_ref: REQUIRED_ACCEPTANCE_RULE

candidate:
  candidate_id: REQUIRED_CANDIDATE_ID
  version_ref: null
  configuration_ref: null
  boundary_ref: null
  assessment_time_binding: REQUIRED_ASSESSMENT_CONTEXT
  mapping_ref: null
  joint_mapping_status: unresolved

sources: []
# Each source binds origin, preserved carrier, digest, version where relevant,
# collection time, and applicability. Evidence refs resolve to exact locations.

evaluation:
  input_manifest_ref: REQUIRED_INPUT_MANIFEST
  input_manifest_sha256: REQUIRED_INPUT_MANIFEST_DIGEST
  obligation_results:
    - obligation_id: REQUIRED_OBLIGATION_ID
      candidate_mapping_ref: null
      evidence_refs: []
      domain_verifier_result_ref: null
      evaluation: UNRESOLVED
      reason_codes: [evidence_unavailable]
  joint_mapping_result_ref: null
  original_evaluation_payload_ref: null

assessment_path:
  source_state_ref: REQUIRED_ASSESSMENT_INPUT_STATE
  target_state_ref: null
  ordered_elements: []
  # Each element binds element_id, sequence_index, input/output refs,
  # relation_before/after, changed_relation, path_effect, boundary,
  # event_time_binding, observation_time_binding, evidence refs,
  # domain verifier refs, and observation/binding/consistency statuses.

verification:
  validation_status: not_evaluated
  assessment_verifier_ref: REQUIRED_PINNED_VERIFIER
  acceptance_rules_ref: REQUIRED_PINNED_RULE_SET
  replay_environment_ref: REQUIRED_REPLAY_ENVIRONMENT
  replay_scope: preserved_candidate_assessment
  comparison_rule_ref: REQUIRED_COMPARISON_RULE
  replay_evaluation_payload_ref: null
  replay_comparison_record_ref: null
  verification_time_binding: null

status_axes_scope: candidate_assessment_path
status_axes:
  observation_status: not_observed
  binding_status: unbound
  consistency_status: internally_incomplete
  reproduction_status: not_tested
  causal_status: not_evaluated
  authority_status: none

assessment_scope:
  scope_id: REQUIRED_ASSESSMENT_SCOPE_ID
  scope_kind: single_candidate
  candidate_set_ref: null
  candidate_set_sha256: null
  candidate_assessment_record_refs: []
  assessment_coverage_status: not_evaluated

alternatives:
  observed_candidates: []
  excluded_candidates: []
  remaining_admissible_candidates: []
  candidate_universe_status: unavailable
  alternative_candidate_closure_status: not_established

result:
  candidate_match_status: NOT_EVALUATED
  complete_match_statement_eligible: false
  complete_match_blockers: [assessment_not_executed]
  unresolved_obligations: [REQUIRED_OBLIGATION_ID]
  violated_obligations: []
  unsupported_answer_claims: []
  contradicted_answer_claims: []
  search_outcome: not_evaluated  # Derived search-level conclusion; Section 9.5.
```

### 12.1 Structural validation requirements

An implementation must define exact enum sets, required fields by claim class,
identifier uniqueness, reference-resolution rules, permitted encodings, and
manifest/digest coverage. Missing mandatory fields, duplicate identifiers,
dangling references, unknown status values, and mistyped values must not be
coerced into passing states. Boolean fields must reject strings and numbers
as substitutes for literal booleans.

The required obligation-ID set must equal the evaluated obligation-ID set for
a completed assessment. Duplicates, omissions, or extra substituted obligations
cannot be concealed by aggregate counts. A required relation's endpoints must
resolve to the mapped objects in the same declared candidate boundary.

The input manifest references the immutable requirement specification, not the
later evaluation results embedded in the reporting envelope. Preserved semantic
review results used as inputs must be distinguished from results produced by
the assessment. This separation preserves the dependency order in Section 10.

### 12.2 Derived summaries and availability

Classifications, coverage summaries, unresolved-item inventories, and eligibility
flags must be recomputed from validated item-level records. A stored complete
label that disagrees with the recomputed predicate must be rejected, not treated
as an alternative accepted verdict.

Unavailable provider or answer fields are permitted only where the claim does
not require them. They must block a provider-answer audit when that audit needs
the missing carrier, but they need not block an independently sourced candidate
assessment. The schema must make these claim-dependent conditions explicit.

A search-level aggregate additionally binds the exact candidate-set scope and
its assessment references. Candidate records with different query or
requirement-set identities cannot be combined into one search conclusion without
an explicit, accepted interpretation mapping.

---

## 13. Required verification scenarios

These are **proposed test requirements**, not implemented or executed tests.
They define rejection boundaries and controls against unjustified rejection.

A runnable suite must first have a fully bound positive control that qualifies
under Sections 2.4 and 9. Each negative case should change one claim-critical property
where possible. Otherwise a rejection could be caused by an unrelated missing
field and would not test the intended semantic boundary.

| ID | Mutation or scenario | Required diagnostic or outcome |
| --- | --- | --- |
| N01 | Give a high-ranked candidate several passing obligations but leave one required relation unsupported. | `VERIFIED_PARTIAL_MATCH`; the score cannot yield complete classification. |
| N02 | Supply valid evidence and a valid policy with no proof that the policy governed the relevant run. | Binding `unbound` for that relation; evaluation `UNRESOLVED`; complete statement blocked. |
| N03 | Add a generated capability claim absent from its cited source. | Claim support `unsupported`, not automatically `contradicted`; no full-match promotion through that claim. |
| N04 | Cite evidence that explicitly contradicts a claim-critical capability assertion. | Preserve the contradiction; obligation `FAIL` and candidate `CONFLICTING_MATCH` under the declared rule. |
| N05 | Use version-bound evidence outside its valid target context without a compatibility proof. | Binding `stale` or `identity_conflict` as justified; no silent version transfer. |
| N06 | Observe query acceptance but no terminal answer within the declared interval. | Search outcome `RETRIEVAL_UNAVAILABLE`, not `NO_VERIFIED_MATCH`; an unfinished candidate review also cannot yield a completed no-match result. |
| N07 | Provide different captured answers for different session classes without a provider trace. | Output divergence recorded; selection cause unresolved. |
| N08 | Expose one candidate but not the candidate universe. | Alternative closure `not_established`; no "only solution" or global nonexistence claim. |
| N09 | Omit a claim-critical request clause while materializing the requirement set. | Interpretation coverage rejected or unresolved; no complete classification even if every retained obligation passes. |
| N10 | Submit an empty obligation set or silently weaken a required condition to optional. | No vacuous complete result; derivation/contract validation rejects or blocks the changed requirement set. |
| N11 | Collect all required features from unrelated projects and present the union as one system. | Joint mapping unresolved or invalid until the declared composite's integration is evidenced. |
| N12 | Combine individually valid evidence from incompatible versions or producing runs. | Identity/integration check blocks completeness. |
| N13 | Put a source in the global inventory but leave a required relation's own evidence reference empty or dangling. | An explicitly absent evidence mapping yields `UNRESOLVED`; a malformed or dangling reference yields `INVALID_RECORD`. Inventory presence cannot pass the obligation. |
| N14 | Alter preserved answer or source bytes while retaining the original digest. | `INVALID_RECORD` at integrity validation; no accepted candidate result. |
| N15 | Replace a pinned snapshot or verifier during replay, or reproduce a different evaluation payload. | Identity rejection or explicit replay mismatch, as applicable; neither a fresh execution nor a mismatching payload establishes accepted replay. |
| N16 | Mark all obligations passing although one required semantic check has no accepted verifier result. | Recomputed obligation unresolved; stored summary cannot promote it. |
| N17 | Preserve a complete candidate proof while the provider selection path remains unavailable. | Do not block solely for unknown selection causality; causal uncertainty and candidate verification remain separate. |
| N18 | Complete an independent candidate proof but retain an unsupported statement in the earlier provider answer. | Candidate qualification does not repair the earlier claim-to-source audit or reconstruct the provider's path. |
| N19 | Change `authority_effect` or canonical `authority_status` away from `none`. | Reject as outside this application contract, even for a complete candidate. |
| N20 | Forge a complete summary, omit or duplicate an obligation ID, or substitute a string/number for a Boolean flag. | Reject the structural violation or recomputed summary mismatch; no default passing result. |
| N21 | Supply only a feature claim in documentation for an obligation explicitly requiring implemented, tested behavior. | Insufficient evidence level; obligation remains unresolved unless the required implementation evidence is supplied. |
| N22 | Remove an assessment element's required time/evidence binding, or replace its event time with source collection time. | Preserve the missing or conflicting binding; no false reconstruction of the affected path. |

N17 is also a non-regression control: fail-closed must apply to the actual claim
requirements, not to unrelated unknowns. A correct implementation must both
reject unsupported promotion and accept a genuinely complete, bounded proof.

Positive controls must additionally demonstrate that an equivalent implementation
with different names can satisfy the functional requirements, and that an
explicitly bound composite can qualify when its integration obligations pass.
The same checks must apply to PULSEmech and to every other candidate; candidate
identity is never an exemption from the contract.

---

## 14. Integration and implementation boundary

The application is a verification layer around candidate assessment, not
necessarily a replacement search engine:

```text
retrieval proposes candidates
-> domain evidence establishes, refutes, or leaves obligations unresolved
-> bound assessment determines classification
-> explanation preserves the classification's limits
```

A minimal implementation requires a versioned record schema, exact input
carriers, an accepted requirement-derivation procedure, domain acceptance rules,
a standalone assessment verifier, an acyclic replay procedure, and controlled
positive and negative fixtures. Each fixture must state whether its inputs are
synthetic, reconstructed, or observed; one status must not substitute for another.

The shared Transition Meter structure is:

```text
identified endpoints
+ changed relation
+ ordered assessment elements
+ element-level evidence, boundary, and time bindings
+ identified verification rules
+ unresolved-edge preservation
+ reproduction status
+ separate authority status
```

Generality lies in this structure. Domain adapters retain responsibility for
the meanings, methods, and acceptance conditions of their own measurements.
A shared record and binding model is not a universal semantic verifier.

The proposed work remains separate from active PULSEmech release mechanics.
This document defines no production endpoint, registers no gate candidate,
changes no workflow, and grants no release authority. Implementation and
validation results require their own source, schema, tests, artifacts, and
bounded proof records.

---

## 15. Boundaries and non-goals

A complete match is relative to the accepted requirements, candidate revision,
configuration, evidence, verification rules, and assessment boundary. It does
not establish unrestricted knowledge of the candidate or correctness beyond
those premises.

The application does not claim exhaustive discovery, a closed candidate
universe, provider-internal causal knowledge, candidate uniqueness, superiority,
priority, or external validation. It does not infer nonexistence from retrieval
absence or infer a hidden selection mechanism from different visible answers.

It does not treat semantic retrieval, graph retrieval, or specialization as
inherently incapable of system-level reasoning. The constrained failure is the
promotion of component evidence into a system-level claim without the required
relation evidence, regardless of the discovery method.

It does not convert documentation into execution proof, carrier integrity into
semantic truth, or replay into independent validation of every premise.
It does not replace domain expertise or claim an implemented search integration.

A partial answer remains permissible. Unknown provider paths remain unknown.
All records and classifications under this application retain
`authority_effect: none` and `authority_status: none`.

---

## 16. Technical conclusion

Component retrieval and whole-system identification have different proof
obligations. Component coverage alone cannot establish the candidate identities,
integration relations, constraints, and decision dependencies required by a
system-level claim.

The proposed application makes those relations explicit assessment objects.
It binds a preserved request to an accepted requirement structure, that structure
to an identified candidate, and the candidate's claimed behavior to evidence,
domain rules, verifier results, and a replayable classification.

```text
retrieved components != identified system

complete match
= all claim-critical obligations satisfied
  within one bound, consistent, reproducibly assessed candidate scope
```

Where a claim-critical relation remains unresolved, the assessment must preserve
that unresolved state. A generated explanation may describe verified relations;
it must not supply the missing relation that would turn a partial match into a
complete system claim.

---

## References

The application depends on the repository architecture below. The pinned
references identify the architectural baseline; the relative links resolve
to the repository's maintained documents.

- [PULSEmech Transition Meter](../PULSEMECH_TRANSITION_METER.md): transition
  identity, element-level evidence and time bindings, canonical status axes,
  domain boundaries, and separation of measurement from authority.
  [Pinned architecture reference](https://github.com/HKati/pulse-release-gates-0.1/blob/8b84a9fd66f4c34b5aa91a92e78d8764cefbe004/PULSEMECH_TRANSITION_METER.md).
- [PULSEmech Technical Overview](../PULSEMECH_TECHNICAL_OVERVIEW.md): the concrete
  artifact-bound release-authority domain and the release relation used to
  construct the illustrative requirement profile in Section 8. The overview,
  not this application design, defines the implementation-state boundary.
  [Pinned architecture reference](https://github.com/HKati/pulse-release-gates-0.1/blob/8b84a9fd66f4c34b5aa91a92e78d8764cefbe004/PULSEMECH_TECHNICAL_OVERVIEW.md).
