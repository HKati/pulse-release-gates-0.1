# PULSEmech / Paradoxon Diagram

## H1 — Measurement target and repair claims

**Date:** 2026-11-08  
**Status:** research case specification; hand-derived example; not an executed experiment  
**Primary workstream:** Paradoxon Diagram / Transition Meter  
**Prospective reuse:** LRM-03 and LRM-04 through an explicitly supported domain mapping  
**Source baseline:** `b764073a1d551ceb718b6b55066b924b28fd2d78`  
**Authority effect:** `none`  
**Release authority activation:** `false`

H1 is a working name for this case, not a replacement for the cyclic-impact
plan's C01–C10 family, a new executable profile, or an implemented output
status. The example, its evidence views and its expected distinctions are
specified here by hand. No H1 program, candidate, model experiment or workflow
was executed to produce this document.

## 1. Research question and intended contribution

> Measuring a consequence does not by itself identify its cause, and treating
> a consequence does not by itself establish repair of the generating mechanism.

Two questions must remain visible together:

1. Is the selected measurement object suitable for the stated operational
   question, with a justified relation to that question?
2. Given that object and the available evidence, is the proposed inference
   and intervention justified?

Different measurement, inference and intervention objects are not inherently
a defect. Their relations need justification. A precisely measured object can
be relevant while still failing to distinguish the alternatives that matter
for a repair claim.

H1 supplies one fully specified counterexample to an unjustified inference
from an improved immediate measurement to a repaired generating rule. It also
supplies a positive control: a change to that rule with preserved useful
operation. The example makes measurement selection reviewable without
claiming a general relevance detector.

This case is a deliberately bounded way to examine the problem. Its queue
and task vocabulary does not define the limits of the broader inquiry.

## 2. Exact subject, requirements and scope

The subject is one task generator, one normal processor and one named
duplicate backlog, `Q`. There are exactly two admitted request occurrences,
`r0` and `r1`, in that order. They are distinct instances of the same declared
request class.

Before considering either intervention, define the intended operation:

- For each admitted request, generate exactly one task for its specified useful
  effect and process that task once.
- A task is useful because it fulfils that predeclared request obligation.
  Usefulness is not assigned retrospectively to favour an intervention.
- Creating a second task for the same obligation is the examined generation
  fault. This is distinct from executing that extra task.
- The normal processor completes the first task. Any extra task is retained
  in `Q` and is not executed in this case.

The concrete useful effect for each `r` is the change of its named
`served(r)` state from `false` to `true`, once. Initially `served(r0)` and
`served(r1)` are both `false`. Only processing `(r, 1)` changes the matching
state; neither intervention changes a `served` value. The witness binds the
request, that task occurrence and this exact state change.

Task occurrence identities are `(request_id, occurrence_number)`. Thus
`(r0, 2)` and `(r1, 2)` are different extras even when a count is equal.
The useful-operation witness for a request identifies its first task and its
specified useful effect; a count alone is not that witness.

The generator's actual rule **within this declared model** is represented by
`b`:

| Rule value | Meaning of the complete rule in this case |
|---|---|
| `b = 2` | Emit the first task and one extra task for every admitted request. |
| `b = 1` | Emit only the first task for every admitted request. |

This is a definition of the example's mechanism. A submitted parameter value
in an external system would not, without further evidence, establish that
system's actual generating rule.

The case has one common starting segment and two alternative interventions.
They are alternative descriptions, not consecutive interventions or two
executed runs. They exhaust the alternatives declared for this case; they do
not exhaust real repair strategies, environments or generating mechanisms.

The finite horizon ends after `r1`. There are no other requests, retries,
filters, background drains, failures, hidden producers, concurrent writes or
changes of observation boundary. No intervention occurs between T1 and T2.
A changed environment would require a new or revised scope.

## 3. Defined transitions and observation points

Start before `r0` with `b = 2` and an empty `Q`.

A normal request transition `cycle(r)` has this order:

1. The generator emits `(r, 1)` and, exactly when `b = 2`, `(r, 2)`.
2. The processor completes `(r, 1)` for the predeclared useful effect.
3. If emitted, `(r, 2)` is retained in `Q`.

There is no other queue modification in a normal transition. Each transition
finishes before the next listed action. Observations at T0, T1 and T2 cover
the whole named queue at that point; `q = |Q|` is its length.

- **T0:** after `cycle(r0)`, before either intervention.
- **T1:** after the entire selected intervention, before `r1`.
- **T2:** after `cycle(r1)`, with no intervening cleanup.

The interventions are exactly:

| Variant | Intervention | Actual changed object in the model |
|---|---|---|
| A | Remove all existing entries from `Q`; leave `b = 2`. | The accumulated consequence. |
| B | Set `b = 1`, then remove all existing entries from `Q`. | The generating rule and the accumulated consequence. |

The intervention ordering in B is fixed for this case. Removing an existing
extra does not undo the historical fact that it was generated.

## 4. Hand-derived comparison

The following table follows from the definitions above. It is not captured
runtime output or a report of executed tests.

| Point | Variant | Rule `b` | Complete queue `Q` | `q` | Useful-operation evidence in the full description |
|---|---|---:|---|---:|---|
| T0 | Common | 2 | `{(r0, 2)}` | 1 | `(r0, 1)` completed its specified effect once. |
| T1 | A | 2 | `{}` | 0 | The earlier `r0` completion remains; `r1` has not occurred. |
| T1 | B | 1 | `{}` | 0 | The earlier `r0` completion remains; `r1` has not occurred. |
| T2 | A | 2 | `{(r1, 2)}` | 1 | `(r1, 1)` completed; two task occurrences were emitted for `r1`. |
| T2 | B | 1 | `{}` | 0 | `(r1, 1)` completed; only that task was emitted for `r1`. |

At T1 both variants have an empty queue. Nevertheless, A retains the faulty
generating rule and B changes it. At T2 the renewed extra in A is linked to
`r1` by its identity and the stipulated transition; `q = 1` alone would not
identify its origin.

Let the selected immediate observation be only the bound queue measurement
at T1. Both alternatives produce the same observation while differing on the
generating-rule repair claim. That observation therefore does not determine
the repair claim within even this two-alternative family.

The stronger distinction is obtained from the defined mechanism and the
bound transition description, not from temporal succession alone.

## 5. Measurement-object selection must be reviewed

Suitability is relative to a question. It is not a universal property of a
metric, and exact identity binding does not establish suitability.

| Operational question | Proposed measurement or evidence object | Justified role | Remaining limit |
|---|---|---|---|
| Is the existing backlog empty at T1? | Complete `Q` observation at T1 and its count. | Directly establishes emptiness in the declared observation boundary. | Says nothing by itself about a later request or the generating rule. |
| Has the generating rule been repaired? | Only `q = 0` at T1. | Relevant evidence about a consequence of generation and cleanup. | Does not distinguish A and B; insufficient for rule repair. |
| What did the intervention change? | Its bound operation description and the rule before and after it. | Distinguishes queue removal from rule modification in the model. | A real operation record would require evidence of its application and semantics. |
| Did the next named request behave as required? | Emission identities for `r1` and its useful-effect witness. | Establishes the specified request's behaviour when complete and correctly bound. | One request record alone does not establish a universal rule or future behaviour. |
| Was the cleanup command reported successful? | The cleanup return message. | Evidence about that reported command outcome. | Does not by itself establish complete queue observation or generator repair. |

The relation from generation to `Q` is specified in Section 3. That makes
`Q` relevant to the examined consequence. It does not make every claim about
the generator decidable from `Q`.

Completeness of queue observation at T1 does not establish completeness of
the evidence required for the repair claim. Likewise, absence of a demonstrated
relation to the operational question leaves relevance unresolved; it does not
automatically prove irrelevance.

For future cases, state the operational question, the selected object, the
relation that makes it relevant, observation coverage and the alternatives it
must distinguish. If irrelevance is claimed, that claim needs its own
scope-bound justification. H1 does not implement automatic target selection
or a general irrelevant-target detector.

## 6. Keep the claims separate

| Claim | Exact meaning within H1 |
|---|---|
| Current consequence removed | All entries in the named queue are absent at T1. |
| Generating rule repaired | The post-intervention rule is `b = 1`, so its defined generation for the remaining admitted request meets the one-task requirement. |
| Next useful operation preserved | `r1` occurs and its first task completes the predeclared useful effect once. |
| Next generation requirement met | Exactly one task is emitted for `r1`. |
| Permanent or general repair | A claim beyond H1's finite horizon and declared mechanism; not established by this case. |

The first claim is true for A and B in the full model. The second and fourth
are false for A and true for B. The third is true for both. These judgments
are consequences of the explicit case rules; they are not empirical
observations.

A zero queue produced by stopping useful work would not establish the third
or fourth claim. No shutdown alternative is silently added to the two-variant
core: the separate useful-operation obligation prevents a future
implementation from treating missing activity as successful repair.

## 7. Evidence views and the knowledge boundary

An examiner receives a specified evidence view, not the author's complete
knowledge of the example. All rows below are documentary controls on the
same case, not new executions.

### 7.1. Endpoint-only view

The allowed premises are:

- the named subject, operational question and meanings of the queue and rule;
- the two permitted intervention alternatives, without identifying which
  occurred;
- the common T0 description;
- the whole-queue observation boundary and the T1 result `q = 0`.

The view excludes the intervention identity, its operation record, the
post-intervention rule, all T2 data and the expected repair judgment.
A/B labels and case identifiers are organisational metadata, never premises
from which a checker may look up the answer.

Both A and B are compatible with this view. The queue-emptiness claim is
supported; the rule-repair claim is **unknown from the supplied evidence**.
It would be incorrect either to declare repair or to declare persistence of
the fault from this view alone.

### 7.2. Complete A view

Add the exact A operation, its unchanged rule and the full bound description
of `cycle(r1)`. The statement that the existing backlog was cleared is
supported. The rule-repair claim is refuted **within the model**, and renewed
extra generation for `r1` is shown by the stipulated transition.

This does not make the honest, limited cleanup claim false.

### 7.3. Complete B view

Add the exact B operations, their rule change and the full bound description
of `cycle(r1)`, including its useful effect. Rule repair, the one-task
requirement for `r1` and useful operation are supported **within the declared
model**.

The conclusion is conditional on the stated semantics and scope. The example
does not supply an external system's source-to-model correspondence, a native
event trace or independent causal validation.

### 7.4. Partial B rule view without a later occurrence premise

This view supplies the bound B operation, its post-intervention rule and T1.
It supplies no witness or premise that `r1` actually occurred, that
`cycle(r1)` completed, or that `served(r1)` changed. The complete variant
description and its later schedule are not implicit premises of this view.

The rule's conditional behaviour is specified, but an intended or permitted
request is not evidence of its occurrence. The later useful completion
therefore cannot be asserted from this view. If completion of the whole
normal `cycle(r1)` is instead supplied as an applicable premise, its defined
useful effect follows within the model; absence of a duplicate event record
must not force that derivable conclusion to unknown.

## 8. Four connected review obligations

| Link under review | Required check in H1 | Unjustified shortcut to avoid |
|---|---|---|
| Operational question → measurement object | Explain why the selected queue, rule or request event addresses the question, and whether it distinguishes the relevant alternatives. | Treating an exactly bound measurement as automatically sufficient. |
| Measurement → conclusion | Limit a T1 queue observation to what all compatible alternatives support. | Turning “the queue is empty” into “the generating rule is repaired.” |
| Conclusion / declared goal → intervention | Check whether the actual changed object meets the stated goal. Cleanup meets a cleanup goal; rule repair requires the rule change. | Treating a consequence-directed action as evidence that the cause was changed. |
| Intervention → result | Bind the operation, rule, request and useful effect to one variant under the same assumptions. | Inferring causal repair from a later improved number alone. |

In this model, attribution uses the explicitly defined transitions and the
exclusion of other changes. For a real subject those premises require
evidence; a timestamp order cannot substitute for them.

## 9. Minimal evidence requirements and unknown results

“Enough” below means enough for the named claim in this stipulated case.
It is not a universal sufficiency standard for real-world causation.
The gaps in the last column leave a conclusion unknown only where no other
applicable evidence or valid derivation discharges the same obligation.
An observed occurrence and a consequence derived within the model remain
different claims.

| Claim or relation | Evidence sufficient within the case | When the broader conclusion stays unknown |
|---|---|---|
| Observed queue emptiness at T1 | Correct queue identity, observation point and whole-queue coverage with `q = 0`. | Missing observation, changed queue boundary or incomplete coverage; a modeled empty queue is not a performed measurement. |
| Relevance of the queue to the examined consequence | The declared generation/retention relation and the question's scope. | That relation has not been established for the actual subject. |
| A/B discrimination | Exact intervention/rule evidence applicable to the same variant; the full transition description checks its consequence. | Only the shared endpoint is supplied. |
| Generator-rule repair in B | Bound pre/post rule definitions, the specified rule-changing operation and its application in the model. | A reported setting or one favourable output is the only evidence about an external generator. |
| Preserved useful operation for `r1` | An identified request, its predeclared useful effect and the matching completion witness. | No request, absent completion record or an unrelated task's record. |
| Renewed extra generation in A | The bound `r1` emission of `(r1, 2)`, with the unchanged generating rule. | A queue count without task/request identity or transition support. |
| Applicability to a real system | A separately reviewed mapping of subject, source, rule, environment, observations and exclusions. | H1 alone supplies no such mapping or runtime evidence. |

A missing observation is not a measured zero. Missing repair evidence is not
evidence that the faulty mechanism persists. A record from another variant,
request, source version or environment cannot silently fill an obligation.

“Supported,” “refuted in the model,” “unknown” and “inapplicable evidence” are
explanatory judgments here, not additions to any preserved v0 output schema.
There is no aggregate PASS and no release decision.

## 10. Acceptance controls for a later bounded implementation

These are expected distinctions to preserve if implementation is subsequently
authorised. They have not been run.

| Evidence view / claim | Required distinction |
|---|---|
| Either endpoint-only view / queue empty at T1 | Supported within the declared observation boundary. |
| Either endpoint-only view / generator repaired | Unknown, with both compatible alternatives retained. |
| Complete A / generator repaired | Refuted in the model, with the unchanged rule and `r1` extra as the witness. |
| Complete B / bounded repair with useful operation | Supported in the model, with rule-change and useful-operation witnesses kept distinct. |
| Complete A / existing extras removed | Supported as the explicitly limited mitigation claim. |
| Missing T1 observation / measured zero | No observation result may be fabricated. |
| Partial B rule view from Section 7.4 / later useful operation occurred | Unknown for occurrence, without erasing independently supported rule information. Do not supply an implicit complete-cycle premise. |
| A record combined with B's rule or an unrelated request's completion | The mismatched evidence is inapplicable; do not assemble a positive witness across subjects. |
| Changed measurement boundary or an additional drain/filter | The closed H1 assumptions do not apply; retain unresolved scope instead of forcing an A/B answer. |
| Label changed while evidence is held fixed | The judgment must follow the evidence, not the case label. |

A supported subclaim must not be erased merely because a different obligation
is unresolved. Conversely, several individually favourable fragments cannot
be combined unless they describe a common applicable configuration. [3, 5]

## 11. Containment and repair boundaries

A separately specified intervention may correctly interrupt a harmful
propagation path while leaving the generator unchanged. It should be assessed
against that declared containment goal. It is neither automatically a failed
intervention nor evidence that the generating rule was repaired.

H1 does not include such a filter or containment mechanism among its two
alternatives. This boundary prevents its minimal example from becoming a
general rule that only source removal can count as a successful intervention.

The example also does not show that every recurring symptom has one unchanged
cause. Repeated counts, similar wording and later recurrence need their own
identity, mechanism and applicability evidence.

## 12. Placement in the existing work

The following is a correspondence to existing definitions and plans, not a
claim that their entire scope has been implemented by H1.

| Existing work | H1 correspondence | Preserved limit |
|---|---|---|
| Cyclic-impact research, C07 | Incomplete repair support remains unresolved. | H1 does not close the full C01–C10 family. |
| Cyclic-impact research, C09 | Useful operation is defined independently of the preferred repair result. | One named useful witness does not establish all operational viability conditions. |
| Cyclic-impact research, C10 | Queue state, generating rule and repair claim cannot exchange meanings without an explicit relation. | No general semantic-change detector is asserted. |
| Paradoxon relational and M1–M3 definitions | Declare subject, semantics, identity, compatible alternatives and a common witness. | Model support, applicability and observed impact remain different obligations. |
| Transition Meter | Compare the transition and its evidence, not only favourable endpoints. | Observation, binding, consistency, reproduction, causal assessment and authority remain separate. |
| LRM-03 | Prospective mapping to role/identity (A06), added claims (A11), and claim scope (A24). | H1 is not an already executable LRM fixture. |
| LRM-04 | Prospective mapping to support/persistence (A16), common-configuration impact witnesses (A17), and observed-event binding (A18). | A modeled difference is not a recorded occurrence. |

These correspondences use the cyclic plan, relational definitions, M1–M3
contract, Transition Meter and LRM plan/contract at the source baseline.
[1–6]

LRM-02 already documents source, span, structure and evidence-binding checks
for its supported input contract. Its independent controlled-source grammar
is finite and explicit. Binding an already supplied measurement target does
not establish that the target was suitable for an external operational
question. [7]

Ordinary English or Hungarian prose about queues, repair and causes is not
silently an accepted input to that frozen grammar. Executable reuse would
first need an explicit supported domain representation, semantics and
evidence obligations, with any necessary profile change separately designed.
H1 neither edits the existing profile nor adds a new completion prerequisite
to LRM-03 or LRM-04.

The preserved W1 result supplies a narrower historical correspondence:
P00 and N08 have equal final sink size and audit count but different relation
results because of support at the effect. That is evidence for the importance
of the bound path in those recorded cases; it is not an H1 execution.
Its `CAPTURE_COMPLETED_UNATTESTED` status and unresolved runner-image
provenance remain intact. H1 needs no repeat of W1. [8]

## 13. Smallest follow-on and stopping point

This documentation step completes the case definition, hand derivation,
evidence views and future acceptance obligations. It establishes the logical
insufficiency of the selected endpoint projection for the stated repair
claim. It does not establish a programmed recognition capability.

If executable work is later selected, keep the first scope bounded:

1. Map H1's objects and claims to an explicitly supported representation.
   Identify what existing binding, comparison and support mechanisms can
   actually express.
2. Supply the declared model separately from each examiner's evidence view.
   Keep expected judgments and variant labels outside the premises.
3. Add only the missing checks needed for the controls in Section 10. Preserve
   independent subclaims, unknown results and applicable common witnesses.
4. Review coverage and limitations before specifying any empirical experiment.
   A real execution needs its own subject, environment, observation plan and
   authorisation.

No general causal inference system, new architecture, release gate, authority
extension or automatic metric-selection system is proposed by this package.
The normative release-authority chain is unchanged.

## 14. Sources and provenance

The repository references below pin the inspected source baseline,
`b764073a1d551ceb718b6b55066b924b28fd2d78`. Existing documents may retain
their own older source snapshots and historical statuses; those records are
not rewritten by this case.

The problem statement and the requirement to review measurement-object
selection come from the owner's research handoff and follow-up discussion
dated 2026-11-08. The A/B model and the hand-derived evidence views are this
document's proposed case, not an extracted historical experiment.

1. [Cyclic-impact research v0.1, especially Sections 8–10](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_PARADOX_CYCLIC_IMPACT_RESEARCH_v0_1.md).
2. [Relations and compatible change v0.2](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md).
3. [M1–M3 definition contract v0.2, especially subject, semantics, identity and common-configuration requirements](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md).
4. [Transition Meter, especially Sections 4, 14–19 and 29–32](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/PULSEMECH_TRANSITION_METER.md).
5. [Language Relation Measurement v0 plan, work packages and A01–A24 acceptance cases](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md).
6. [Language Relation Measurement v0 contract](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md).
7. [LRM-02 source-bound input verifier, especially Sections 3–7](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/PULSEMECH_LANGUAGE_RELATION_INPUT_VERIFIER_v0.md).
8. [Preserved W1 native execution 41852641211/1, especially Sections 4–5](https://github.com/HKati/pulse-release-gates-0.1/blob/b764073a1d551ceb718b6b55066b924b28fd2d78/docs/experiments/PD_SM_02_W1_NATIVE_EXECUTION_41852641211_v0.md).
