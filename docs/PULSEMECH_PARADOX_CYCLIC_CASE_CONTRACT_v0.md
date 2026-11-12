# PULSEmech / Paradoxon Diagram

## Bounded cyclic repair case contract v0

**Date:** 2026-11-12  
**Status:** research input and hand-derived reference specification  
**Source baseline:** `1fbc52660cb1085b6cd419ff733000e7afe163f7`  
**Workstream:** Paradoxon Diagram / Transition Meter  
**Authority effect:** `none`  
**Production gate eligible:** `false`

## 1. Purpose and stopping point

This package maps the already complete hand-worked repair in the cyclic-impact
plan, Section 7, and its four controls into explicit machine-readable inputs,
separate expected judgments and named checking obligations. It continues the
next bounded unit identified by the retained W1 assessment, Section 9. The hand
derivation is reused, not presented as a new finding. [S1, S2]

The selected question is whether removing a direct failure relation leaves a
new compatible failure route, a return to a mode, or a repeatable relation
pattern. These are different questions. A larger counter, a repeated mode
label or a favourable endpoint does not answer all of them.

There are five complete case descriptions and six questions per case. The
30 entries in the reference file are hand-derived expected judgments. They
are not 30 executed tests, observed events or results from an implemented
cyclic evaluator. The package supplies no evaluator or native experiment.

The representation is deliberately limited to this research unit. It does
not define the limits of the wider relational inquiry, provide a general
causal inference system, or close the entire C01–C10 case family.

## 2. Repository files and their roles

| File | Role |
|---|---|
| [This contract](PULSEMECH_PARADOX_CYCLIC_CASE_CONTRACT_v0.md) | Definitions, evidence obligations, reuse boundaries and acceptance requirements. |
| [Case inputs](../examples/paradox_cyclic_case_v0/cases.json) | Complete before/after inventories, domains, conditions and queries. No expected outcomes. |
| [Expected reference](../examples/paradox_cyclic_case_v0/expected.json) | Manually derived judgments, admitted prefixes and reasoning; outside evaluator premises. |
| [Structural schema](../schemas/paradox_cyclic_case_contract_v0.schema.json) | JSON shapes for the two data files; not a relation or proof checker. |

The schema uses JSON Schema Draft 2020-12 and distinguishes the input and
reference formats through their `format` fields. References within the schema
are local. Structural admission does not verify a subject binding, predicate
fact, transition, recurrence argument or real-world applicability.

The reference file binds the exact raw bytes of `cases.json`, including its
final LF, through `input_file_sha256`. Its `case_id` values join reference
records to inputs only. An evaluator must not infer a judgment from a case
identifier, its position, a source-case label, or this reference file.

The source baseline identifies the inspected repository context. It is not
the identity of a new execution, and it is not an assertion that these new
files were already present at that commit.

## 3. Representation and unchanged meanings

Each case is self-contained. It shares one domain, failure meaning, predicate
declaration set and query between its `before` and `after` descriptions.
The correspondence between these two descriptions is the identity on those
objects. They are compared model descriptions, not two recorded runs.

### 3.1 State and subject

A complete state is `(subject_id, mode, counter)`.

- `subject_id` belongs to the case's declared, nonempty subject domain.
- `mode` belongs to its declared, nonempty mode domain.
- `counter` is an exact nonnegative mathematical integer.
- Every rule preserves the subject and increments the counter by exactly one.
- The failure condition is exactly equality with `failure_condition.mode_equals`.

The supplied cases use modes `A`, `B`, `F`, initial state
`(subject-X, A, 0)`, and failure mode `F`. These spellings are identifiers;
the field bindings give them meaning. Consistent renaming must preserve
answers. Rules cannot change subject, reset the counter, or introduce an
unlisted operation under this representation.

No counter value is treated as a universal time, a physical duration or a
probability. Its role is the one defined by these rules and guards.

### 3.2 Complete rule inventories

A rule records its local identifier, subject, source mode, target mode,
guard and counter increment. For a fixed interpretation of declared
predicates, it is enabled exactly when its subject and source mode match
the current state and its guard is true. Its effect is its declared target
mode and `counter + 1` for the same subject.

The inventories are closed: no unlisted transition is permitted. An empty
set of eligible rules means that no next transition exists in the declared
model. If several rules are enabled, each gives a permitted alternative;
their order in the JSON array has no operational meaning.

`complete_rule_inventory: true` declares that model scope. It does not prove
that an external system has no hidden rules, concurrent changes or resources.
A complete rule inventory can still contain a predicate with unknown truth.

The three guard forms are:

| Guard | Exact meaning at the rule's starting state |
|---|---|
| `unconditional` | True. |
| `counter_below`, `limit = L` | `counter < L`, with exact integer comparison. |
| `predicate`, `predicate_id = p` | The value of declared `p(subject_id, mode, counter)`. |

The language contains no code strings, calls, arbitrary expressions,
implicit subject transfers or implicit conjunctions. A later need for an
additional operator requires an explicit extension; it is not silently
accepted through prose or an unknown JSON field.

### 3.3 Predicate knowledge and joint interpretations

A predicate denotes one immutable total Boolean function on the case's
declared state domain. Its supplied facts constrain that function at exact
state keys. The same key has the same value wherever it is used, including
both descriptions. Different counter values can have different values.

A missing fact is unknown, not false or true. An undeclared predicate is
invalid input, not an unknown declared predicate. Duplicate keys within a
predicate's fact inventory, including contradictory values, are rejected.
The consistent interpretation set must be nonempty; contradiction must not
produce a vacuous positive conclusion.

For K04, `permit` has an empty fact inventory. Constant true, constant false,
and a function true only at `(subject-X, B, 1)` are distinct, consistent
interpretations. A witness must use one joint interpretation throughout;
selecting a different interpretation at each step cannot manufacture support.

The supplied facts are premises of this modeled example. Accepting them
here is not external verification of a sensor, source claim or platform.

## 4. Measurement-object selection

The operational question is declared before choosing the inspected object.
This preserves H1's distinction between a relevant measurement and one that
actually discriminates between the alternatives needed by a claim. [S3]

| Question | Object that must be inspected | Why a smaller observation is insufficient |
|---|---|---|
| Was the direct old relation removed? | Before/after relation meanings for the same subject and failure target. | A changed rule identifier alone does not show relation removal. |
| Is the displayed new failure route feasible? | Each step, its subject and its guard at the bound starting state. | Unbound arrows do not supply joint feasibility. |
| Does a course return to the mode after failure? | A compatible course with the failure visit and later mode return. | A terminal mode label alone does not show such a course. |
| Can the complete state return? | The complete state coordinates and their transition semantics. | Repeated mode labels omit the increasing counter. |
| May the counter be omitted? | Enabled projected successors and the failure predicate over all declared states for the selected subject. | Agreement at one reachable state does not establish all-state preservation. |
| Is the selected pattern repeatable? | A return word and justification for its joint enabling conditions at every repetition. | One admitted traversal does not establish another. |

The chosen representation is sufficient to pose these bounded questions.
It does not establish that the same observations would be sufficient for an
external operational problem. Useful-operation preservation, actual repair
success and external causation are not questions assessed by this package.

## 5. Six separate questions

Let `s` be the selected subject, `q0 = (s, m0, n0)` the initial state, and
`F` the declared failure mode. Except Q1, the questions concern the complete
`after` inventory. Claims are interpreted separately for every consistent
complete interpretation of the declared predicate facts.

### Q1 — `direct_route_removed`

The before inventory contains a direct rule from `m0` to `F` for `s`, and
the complete after inventory contains no such rule. The comparison uses
subject and source/target meanings, not a disappearing `rule_id`.

This asks about the direct relation's removal from the inventory. Disabling
a retained relation with a false guard is a different change. This claim
does not establish absence of indirect failure routes.

### Q2 — `new_failure_route_feasible`

The exact mode sequence in `displayed_new_failure_route_modes`, starting
at `q0`, can be followed through admitted after rules for `s`. Each step
must use its actual starting counter and one joint predicate interpretation.
Its last mode must be `F`.

The supplied sequence is `A, B, F`. This is the feasibility of that displayed
route, not an exhaustive safety question about all possible routes. The
word "new" identifies the comparison task; relation differences must still
be checked against the before inventory. In these fixtures `A`-to-`B` and
`B`-to-`F` were absent before and are added after, with K03's different
subject on the latter preserved.

### Q3 — `failure_then_mode_return`

There is a finite compatible course from `q0` that reaches `F` and subsequently
returns to `(s, m0, n)` for some counter `n`. The return must occur after the
failure visit. A subject change cannot satisfy the claim.

This is one return to a mode for the same subject. It does not assert equality
of complete states or restoration of enabled relations. K01 deliberately
establishes Q3 while refuting Q5 and Q6.

### Q4 — `complete_state_return`

There is a nonempty compatible course from `q0` back to that exact complete
state, including its original counter. This question does not require a
failure visit. All five supplied cases refute it: after any positive number
`j` of admitted moves, the counter equals `n0 + j`, which differs from `n0`.

This argument is conditional on admitted moves and is valid even when the
feasibility of a particular guarded course is unknown.

### Q5 — `counter_projection_sound`

The projection retains `(subject_id, mode)` and omits the counter. Its scope
is **all declared after-states for the selected subject**, not just the
displayed course or currently known reachable states.

For a fixed predicate interpretation, let `S(m,n)` be the set of target modes
of all after rules enabled at `(s,m,n)`. Soundness here requires:

1. For every declared mode `m` and every nonnegative `n1`, `n2`,
   `S(m,n1) = S(m,n2)`.
2. The failure predicate has the same value at `(s,m,n1)` and `(s,m,n2)`.

Target sets use relation meanings; array order and rule identifier spelling
do not affect them. Empty successor sets are compared too. Because rules
preserve subjects and increment the counter within its declared domain,
these conditions preserve the projected steps and failure meaning under
the stated omission.

Counter-independent guards, projected effects and failure meaning supply a
sufficient argument for the base case. A projection refutation needs a
counterexample or other valid argument; failure of one sufficient proof
method alone is not such a refutation.

### Q6 — `repeatable_structural_return`

There is a nonempty finite after-rule word of length `L` that starts at `q0`,
returns to the same subject and mode, visits `F`, and remains jointly enabled
at every repetition. More precisely, the same word is admitted from
`(s,m0,n0+kL)` for every nonnegative integer `k`; each traversal returns to
`(s,m0,n0+(k+1)L)` and visits the failure mode.

This specifies recurrence of that selected operational pattern. It is not
a claim that the complete state recurs, that every execution chooses it,
or that a physical system will follow it. No fairness or inevitability is
assumed. It is also not a search for every possible later recurrence after
an arbitrary unexamined prefix.

A sound counter projection plus the compatible return word is a sufficient
certificate in the base case. Q5 is not the definition of Q6: a particular
reachable pattern may repeat even if a projection over other declared states
is unsound. Q5's failure therefore cannot by itself refute Q6.

## 6. Meaning of the reference judgments

| Judgment | Meaning for the particular model claim |
|---|---|
| `ESTABLISHED_IN_MODEL` | Every complete predicate interpretation consistent with the supplied facts satisfies the claim. |
| `REFUTED_IN_MODEL` | Every consistent complete interpretation excludes the claim. |
| `UNRESOLVED` | The supplied knowledge permits both outcomes; it does not select between them. |

In cases without unknown predicates, the interpretation set is effectively
one fixed model. For an existential course claim, its witness must belong
to the interpretation in which it is claimed. Steps from incompatible
interpretations cannot be combined. A uniform witness is a convenient
sufficient certificate where available, not an automatic change of quantifiers.

These are scoped reference judgments for this contract. They are not current
W1 output statuses, release decisions or statements of external truth.

Well-formed input, semantic admission, valid certificate and model judgment
are separate obligations. Invalid input, unsupported evaluation scope,
resource exhaustion or a malformed certificate must have separate processing
outcomes in a later implementation. None is evidence of a refuted model
claim. A checker that cannot establish a claim must not manufacture one of
these reference judgments as though it had completed the stated analysis.
This package introduces no executable processing-status format.

## 7. Five complete cases and their references

`K00`–`K04` are opaque local identifiers. C-family correspondences appear
only in the reference file and this explanation, not as evaluator hints.

| Input | Source correspondence | Complete change relative to the shared illustrative pattern |
|---|---|---|
| K00 | C02/C03 | Before: `A→F`, `F→A`. After: `F→A`, `A→B`, `B→F`, all unconditional for subject-X. |
| K01 | C04 | Each rule in both inventories additionally requires `counter < 3`; the after course is otherwise K00's. |
| K02 | C06 | The after inventory contains only `A→B`, `B→F`; `F→A` is removed as well. |
| K03 | C05 | The after `A→B` rule belongs to subject-X and `B→F` to distinct subject-Y; the query remains bound to subject-X. |
| K04 | C07 | After `B→F` requires declared `permit(subject_id,mode,counter)`; its fact inventory is empty. Other after rules are unconditional. |

Every JSON case repeats its full before/after inventories; none depends on
an implicit patch to another case. K01 applies the guard uniformly to both
descriptions to make its comparison self-contained. The control relevant
to the source example is its guarded after course. For K03, subject-Y is
explicitly declared, but subject transfer is not an admitted operation.

The reference matrix abbreviates the judgments as E, R and U:

| Case | Q1 direct removed | Q2 displayed failure route | Q3 failure then mode return | Q4 complete-state return | Q5 counter projection | Q6 repeatable pattern |
|---|---|---|---|---|---|---|
| K00 | E | E | E | R | E | E |
| K01 | E | E | E | R | R | R |
| K02 | E | E | R | R | E | R |
| K03 | E | R | R | R | E | R |
| K04 | E | U | U | R | U | U |

### 7.1 Positive recurrence witness

K00's admitted course is:

`(subject-X,A,0) → (subject-X,B,1) → (subject-X,F,2) → (subject-X,A,3)`.

The after-rule word is `r2, r3, r1`. For every `k >= 0`, the same rules admit:

`(subject-X,A,3k) → (subject-X,B,3k+1) → (subject-X,F,3k+2) → (subject-X,A,3k+3)`.

The proof uses the complete rule definitions: the subject is preserved,
the guards are unconditional, the counter remains nonnegative, and the
projected effects and failure meaning are fixed. Arbitrarily many finite
traversals sampled by a test would not replace this argument.

### 7.2 Guard-bound termination

K01 admits the same first course. Its three guards are checked at counters
0, 1 and 2, so the first return to `(subject-X,A,3)` is admitted. No rule is
enabled there. More generally, strict increments and the `counter < 3`
condition bound every course from counter 0 to at most three moves.

For Q5, `(subject-X,A,0)` and `(subject-X,A,3)` have the same projection but
different successor sets. For Q6, the finite bound supplies the separate
refutation of repetition. A repeated `A` label is not enough.

### 7.3 Failure without return

K02 admits the failure prefix, and its complete after inventory has no rule
starting at `F`. That closure supports its no-return result. The fixture
contains no mandatory reference to an absent after rule; the case is valid
input with a negative relation result, not a malformed-reference test.

### 7.4 Subject incompatibility

K03 reaches `(subject-X,B,1)`. The next displayed relation belongs to
subject-Y, and no eligible subject-X rule leaves B. The selected subject's
reachable mode closure is A then B. Rules for Y cannot be spliced into it.
These refutations have the declared model and query scope; they do not
establish general safety of an external system.

### 7.5 Missing guard support

K04 has an admitted prefix ending at `(subject-X,B,1)`. Constant true and
constant false interpretations of `permit` support different Q2/Q3/Q6
answers while satisfying all supplied facts. For Q5, constant true preserves
the projection, whereas true only at `(subject-X,B,1)` gives different B
successors at counters 1 and 4. The reference therefore retains U.

Even a future supplied fact `permit(subject-X,B,1) = true` would establish
only the first guarded step and first return. It would not establish the
needed values at counters 4, 7 and later repetitions. Q4 remains refuted
independently by the strictly increasing counter.

## 8. Admission, binding and proof obligations

### 8.1 Beyond structural schema validation

A later input checker must additionally establish:

- Unique case IDs; unique rule IDs within each phase; unique predicate IDs
  within each case. IDs in different cases are not shared evidence.
- Membership of all rule, initial-state, query and fact subjects and modes
  in the case's domains. The failure target is a declared mode.
- The selected subject equals the initial state's subject; the displayed
  route starts at its initial mode and ends at the failure mode.
- Guard predicate references resolve within the same case.
- Predicate fact keys are unique and consistent; unprovided values remain
  unknown. Duplicate JSON object keys are rejected before object construction.
- Integers retain exact mathematical values. Booleans are not integers;
  floating-point rounding must not alter a counter, guard or comparison.
- Shared meanings are fixed across the two descriptions. Additional fields
  cannot silently supply a hidden transition or change operator semantics.

The schema does not prove these cross-field or byte-parsing properties.
It also does not prove the truth of a reference judgment.

### 8.2 Exact inputs and independently checked witnesses

A future result must identify the exact case-bundle bytes, selected case,
query, contract version and checking semantics. Witness steps must resolve
to rules and states in those bound inputs. A record from another case or
source cannot fill a missing step merely because labels match.

Before comparison with the reference file, verify its raw input digest,
require matching `source_baseline` values, and require unique reference
`case_id` values with an exact one-to-one match to the input cases. Missing,
duplicate or extra reference rows are reference-binding errors, not model
refutations. The schema alone does not establish this correspondence.

`admitted_prefix` in the reference file contains only steps justified by the
supplied model and current facts. Its states must start at the case's initial
state; the number of rule IDs is one less than the number of states. Each
step preserves its subject, increments its counter exactly once, and satisfies
the named rule's guard. K04 stops before its unknown guarded step.

These prefixes and the reasoning strings are hand-derived reference material.
The strings are not executable proof scripts, and schema acceptance does not
validate their arguments. The eventual runtime certificate encoding is not
introduced here; its mandatory content and checking obligations are specified
below before any implementation is selected.

### 8.3 Minimum proof content by claim

| Claim | Minimum sufficient support in these fixtures |
|---|---|
| Q1 | Bound before/after inventory comparison using the relation's subject and source/target meanings. |
| Q2 positive | Every displayed step, exact state update, same subject, and jointly supported guards. |
| Q2 negative | A necessary step cannot be admitted within the fixed displayed sequence; do not generalise to all routes. |
| Q3 positive | A compatible course with a bound failure visit followed by the selected subject's mode return. |
| Q3 negative | Coverage of the relevant continuations under the complete inventory, such as K02's terminal F or K03's subject-X closure. A failed candidate witness alone is insufficient. |
| Q4 negative | The strict-increment invariant covering every permitted rule and every nonempty course. |
| Q5 positive | The all-state preservation argument for projected successors and failure, with guard dependencies retained. |
| Q5 negative | A pair of states with equal projection and unequal projected successors or failure values. |
| Q6 positive | A bound return word plus an argument covering every repetition with compatible enabling conditions, such as K00's induction. |
| Q6 negative | An independent exclusion argument, such as K01's finite bound or the complete continuation exclusions in K02/K03. |
| Unresolved | Explicit compatible interpretations giving different outcomes, with each whole witness using one interpretation; retain the missing support. |

No bounded exploration that simply fails to find a path may be reported as
an exclusion without the required coverage argument. A malformed submitted
proof must not change a true or unknown model claim into a refuted one.

## 9. Reuse map and implementation limits

The following correspondences reuse existing obligations and distinctions.
They are not claims that these functions already accept the new case format.

| Existing source | Legitimate correspondence | Remaining domain-specific work |
|---|---|---|
| Relations and Compatible Change v0.2, Sections 2–5 [S4] | Explicit identities, meanings, variations and jointly held conditions. | Preserve the meanings of the rule objects, failure predicate and counter projection. |
| M1–M3, Sections 3–6 [S5] | One identity correspondence, compatible variants, common witnesses and separation of model support from applicability and observation. | Bind all course steps and unknown guard uses to one case and interpretation; justify recurrence rather than just shape. |
| H1, Sections 5–7 and 13 [S3] | Review the measurement target and separate premises, evidence views and expected outcomes. | Check route and persistence questions against the intended object; keep the reference file outside evaluator premises. |
| W1 `_event_graph()` and `check_case()` [S6] | Exact subject/source/context binding and support at the relevant event. | Add an explicit correspondence to operational state transitions; the W1 event grammar is unchanged. |
| PD-SM-02 `independently_parse()`, `check_model()`, `evidence_closure()` [S7] | Independent model/source checking and grounded support obligations. | Provide a checker for this new representation; the existing closed candidate language does not accept it automatically. |
| Finite relation-preservation probe [S8] | Exact joint consistency and alternative compatible support. | The counter domain and recurrence argument require their own scope; a finite histogram result cannot supply them. |

Three meanings of a cycle remain distinct. W1 `_event_graph()` rejects cycles
in the order of event occurrences. PD-SM-02 `evidence_closure()` identifies
possible ungrounded support cycles without creating facts. This contract
concerns recurrence of an operational relation pattern through distinct
states. The first two mechanisms are not operational recurrence evaluators.

The existing LRM workstream can be considered for later reuse only through
an explicitly supported correspondence. This package changes no LRM grammar,
profile or completion requirement, and it grants no release authority.

## 10. Acceptance requirements for a later evaluator

The five reference rows are a starting coverage obligation. A later evaluator
must compute from admitted inputs and independently check any proof material;
the following requirements prevent a fixture-label implementation:

1. Rename case IDs and reorder cases: per-case model judgments are preserved
   after matching the renamed identities.
2. Rename rule, subject and mode identifiers consistently, including all
   references and the failure target: judgments are preserved.
3. Reorder each rule inventory: the result does not acquire an execution order.
4. Remove or alter the expected file: computation from the same case inputs
   is unchanged. Reference comparison may fail; the model result must not.
5. Preserve K01's distinct results: one mode return, unsound counter omission,
   and excluded repetition. Do not infer Q6 directly from Q5.
6. Preserve K02's feasible failure route and no-return result simultaneously.
7. Preserve K03's subject obstruction. Changing the B-to-F rule to subject-X
   removes that obstruction and requires recomputation from the changed model.
8. With only K04's first required fact true, establish the first route and
   mode return while retaining unresolved later repetition and all-state
   projection. With that fact false, refute the displayed route while leaving
   the all-state projection question unresolved.
9. A fixed predicate interpretation may depend on the counter. Do not infer
   counter independence from the word "immutable" or choose inconsistent
   interpretations for successive steps.
10. Keep Q4 refuted by strict increments even when some route guards are
    unknown. Unknown subclaims must not erase independent conclusions.
11. Reject malformed inputs separately: duplicate JSON keys or identities,
    undeclared bindings, contradictory facts, nonintegral counters, Boolean
    counters, hidden fields and an unsupported counter update are not
    relation refutations.
12. Detect an input/reference digest mismatch before reference comparison;
    do not change model judgments to accommodate the mismatched expected file.
13. Require real coverage for negative existential claims and a parametric
    argument for Q6; a chosen search depth is not an absence or recurrence proof.
14. Keep model judgment, external applicability, actual observation and
    authority separate in any later report.

These are specified future acceptance requirements, not a report of executed
regressions. Tests needed by a later implementation must be registered through
the repository's existing process when that implementation is prepared.
This package changes neither CI inventory nor workflows.

## 11. Preparation checks and next implementation boundary

Package preparation checks JSON syntax and structural schema conformance,
the declared identity inventories and local references, the raw input digest,
the five-case/six-question correspondence, document links and the ZIP's exact
four-file inventory. Independent semantic review checks the hand-derived
matrix and the distinctions explained above.

Those checks do not run a cyclic evaluator, replay W1, execute candidates,
observe recurrence or validate external acquisition. The new JSON files are
model inputs and manual references; original W1 evidence is untouched.

The next implementation, if selected, is a bounded input/claim checker and
independent witness checker for this declared representation. Its first job
is to discharge the stated obligations for these five cases, including the
negative and unknown cases. Its supported domain, proof encoding and resource
limits must be explicit. Unsupported obligations stay unsupported rather
than being made to fit a different existing grammar.

No new W1 acquisition is needed for this contract. The historical host-image
discrepancy remains unresolved, and the W1 result remains
`CAPTURE_COMPLETED_UNATTESTED`. This contract is not a new native result,
complete C01–C10 coverage, a general repair verifier or a production gate.

## 12. Source references

All repository sources below are pinned to the inspected baseline. The new
representation and hand-derived reference encoding are this package's
contribution; the underlying illustrative repair and controls are from S1.

**[S1]** [Cyclic Impact of Repairs v0.1, Sections 7–10](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/docs/PULSEMECH_PARADOX_CYCLIC_IMPACT_RESEARCH_v0_1.md).

**[S2]** [W1 relation and provenance assessment, especially Section 9](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/docs/experiments/PD_SM_02_W1_RELATION_AND_PROVENANCE_ASSESSMENT_v0.md).

**[S3]** [H1 measurement-target and repair case](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/docs/PULSEMECH_PARADOX_MEASUREMENT_TARGET_AND_REPAIR_CASE_v0.md).

**[S4]** [Relations and Compatible Change v0.2](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/docs/PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md).

**[S5]** [M1–M3 Definition Contract v0.2](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md).

**[S6]** [W1 record checker](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/tools/check_paradox_w1_records_v0.py).

**[S7]** [PD-SM-02 pre-execution source/model checker](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/examples/paradox_preexecution_impact_v0/check_impact.py).

**[S8]** [Finite relation-preserving discrimination probe](https://github.com/HKati/pulse-release-gates-0.1/blob/1fbc52660cb1085b6cd419ff733000e7afe163f7/examples/relation_preserving_discrimination_v0/relation_closure_probe.py).
