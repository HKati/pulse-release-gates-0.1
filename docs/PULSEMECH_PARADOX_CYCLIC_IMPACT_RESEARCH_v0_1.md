# PULSEmech / Paradoxon Diagram

## Cyclic Impact of Repairs

**Version:** 0.1  
**Date:** 2026-11-01  
**Standing:** research question, bounded source assessment and proposed case design  
**Scope:** documentation; no new experiment or implementation in this delivery  
**Authority effect:** none

## 1. The question introduced by a repair

A repair changes some part of a structure. Establishing that a selected local
condition holds after that change leaves a further question: which relations
and compatible courses remain possible, and can they permit the previous
failure again?

The workshop contribution specifies four connected questions:

1. Which relations ceased to hold because of the repair?
2. Which relations and supporting conditions remained?
3. Which new relations or joint possibilities became available?
4. Can the resulting structure permit the previous failure again, including
   through a different route?

This develops the inquiry in
[Relations, Conditions and Compatible Change v0.2](PULSEMECH_PARADOX_RELATIONS_AND_COMPATIBLE_CHANGE_v0_2.md).
The subject is the consequence of the changed relations under specified
conditions. An event sequence, graph representation or particular detector
becomes relevant only when its meaning and coverage are established for the
chosen case.

The work belongs within the existing Paradoxon Diagram and Transition Meter
research direction. Its first deliverable is a precise, inspectable case and
its claim boundary. It does not require introducing a new instrument or
changing the release decision path.

## 2. The inspected starting point

The source assessment below is limited to selected implementation files,
test sources and existing result documents at main commit
`25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5`, read on 2026-11-01.
It is not a complete repository audit. Tests and experiments were not rerun
for this document; historical execution statements are attributed to their
preserved result documents.

| Capability | What the inspected material supports | Boundary |
|---|---|---|
| Required gate decision | `check_gates.py` requires literal boolean `True` for every declared required gate and rejects missing or malformed required status. [S1] | This evaluates required status obligations; it does not itself establish every underlying observation or physical enforcement effect. |
| Bound evidence and observation checking | The W1 record checker validates selected source/archive bindings and specified observation and relation conditions. [S2] | Its report retains `acquisition_authenticity = NOT_VERIFIED` and `model_native_correspondence = UNRESOLVED`. |
| Joint relation distinctions | M1–M3 provides a bounded formal candidate; a separate finite relation demonstrator has implementation and test sources. [S3, S4] | The selected examples do not establish arbitrary-system coverage. |
| Alternative support after a binding is removed | The finite relation demonstrator includes a declared backup observation path. [S4] | This is a known alternative in a specified example, not general discovery of a new failure route introduced by a repair. |
| Ungrounded proof-support cycles | The pre-execution checker computes grounded closure, detects a positive cycle in the rule graph, and can report `UNRESOLVED_CYCLE`. [S5] | A support cycle is not a recurring operational failure. A detected cycle does not create its own justification. |
| Recorded refusal of an ungrounded-cycle case | The preserved PD-SM-02 scratch result reports N10 blocked before output creation. [S6] | This is a recorded bounded case; it is not a newly executed result or proof of general cyclic-impact recognition. |
| General return of a failure through a changed operational route | Not established by the inspected source scope. | The present research unit addresses a bounded version of this question. |

The statement that missing evidence blocks progression is conditional on the
relevant evidence obligation being represented and checked in the selected
path. A required-gate failure cannot be generalized into a claim that every
unknown relation anywhere in a system has been detected or physically blocked.

The existing support-cycle guard is an important reusable capability within its
own meaning. It must retain that meaning when connected to this work.

## 3. Fix the subject and the failure condition

Before comparing a proposed repair with its starting configuration, identify:

- the subject and the identities that must remain distinguishable;
- the precise failure condition and any useful operation that must remain;
- the relations and condition meanings relevant to that failure;
- the change being considered and the surrounding conditions held fixed;
- the range of alternatives and permitted operations included in the case;
- the observations or other support available for those descriptions.

The failure condition must keep its meaning across the comparison. A changed
definition of success cannot silently count as removal of the original
failure. A different subject likewise requires an explicit correspondence.

The participants and relations need not be fixed to a binary edge list. A
failure can require several conditions together. Alternative ways of
satisfying a condition and dependencies between relations must be retained
where they affect the question.

## 4. Account for what the repair changes

The comparison should account for the following distinctions without forcing
an unknown relation into one of the established categories:

| Finding | Meaning within the declared comparison |
|---|---|
| Ceased | A relation established in the starting case no longer holds in the changed case. |
| Retained | The relevant meaning, binding and conditions continue to hold under the declared correspondence. |
| Newly possible or established | The changed description admits a relation or combination previously excluded, or provides support for its holding. Possibility and establishment remain distinct. |
| Changed applicability or meaning | The condition applies to another participant or configuration, or the comparison requires a separate semantic correspondence. |
| Unresolved | Available information does not settle the required comparison. |

Removing a relation from a model does not demonstrate its removal from the
subject. Finding a relation in a model does not demonstrate that it newly
arose in the subject. The source of the change claim must be recorded.

A useful outcome explains how the changed relations affect the failure
condition. A count of removed and added relations alone does not provide that
explanation. Nor does removing one path remove every alternative path.

## 5. Distinguish three kinds of return

**Exact return** concerns repetition of the specified complete state under its
identity contract.

**Structural recurrence** concerns repetition of the relations and conditions
relevant to a declared question under a justified correspondence. Other values
can differ. The correspondence must retain every distinction required for the
recurrence claim.

**Renewed failure possibility** concerns the original failure condition being
possible again. The structure producing that possibility can differ from the
earlier one and can be acyclic within the examined course.

These claims are not interchangeable. An exact return includes recurrence of
the structure represented by that complete state when its meanings and
context remain unchanged. Neither kind of return by itself establishes a
failure. Repeated error text does not establish an identical failure mechanism.
A new course to a failure need not return to its starting configuration.

The amount of recorded activity can increase while a relevant organization
recurs. If a counter is irrelevant to the permitted operations in a fully
specified case, its growth need not prevent a recurrence claim about that
organization. If that counter changes a budget, an identity, a prerequisite or
an accumulated consequence, it must be retained.

An abbreviated representation can contain a cycle that cannot be completed in
the full case. A completed modeled return can also consume a resource required
for repetition. Therefore one return, a repeatable course and indefinite
recurrence require different support.

## 6. What makes a proposed route possible

A proposed route must specify what connects its parts. If it denotes an
operational course, the selected case needs explicit operation meanings,
preconditions, effects and bindings. Order then belongs to that particular
operational claim; it is not imposed on the entire relational inquiry.

At minimum, examine whether:

1. The participating subject and protected identities remain aligned.
2. The conditions for each part can hold together with the earlier parts and
   the consequences they retain.
3. Required resources, permissions, observations and supporting relations
   remain available at the point where they are used.
4. No step relies on a condition established only after it was needed.
5. Alternative support and alternative routes are included where relevant.
6. The route reaches the same precisely stated failure condition.

Separately possible steps do not necessarily compose into one possible course.
For example, a first step may require a resource that the next step assumes
was never consumed. Different subject bindings can also make an apparently
connected description unusable as one course.

A course established inside a specified model is a model witness. Establishing
its feasibility for a particular subject additionally requires support for the
applicability of the operations and their jointly satisfiable conditions.
Establishing that the course actually occurred requires evidence of the
relevant occurrences. Missing support leaves the affected claim unresolved.

## 7. A completely specified illustrative repair

This hand-worked case uses a small operational description solely to make the
research question inspectable. It is not a model of the entire instrument or
an observation of an actual incident.

### 7.1 Subject, states and fixed meaning

There is one fixed subject. Its mode is `A`, `B` or `F`, and its counter `n`
is a nonnegative integer. The complete state is `(mode, n)`.

- `A` is a configuration satisfying the selected local condition.
- `B` is an intermediate configuration.
- `F` is the designated failure configuration.

The failure condition is exactly `mode = F`. Each permitted move increases
`n` by one. In this case the counter has no effect on the availability of a
move; there are no omitted resources, guards, external inputs or subjects.
Each listed rule applies to every nonnegative `n`. No unlisted moves are
permitted.

### 7.2 The repair's complete relation inventory

| Rule | Starting description | Changed description |
|---|---|---|
| `(A,n)` to `(F,n+1)` | Present | Removed |
| `(F,n)` to `(A,n+1)` | Present | Retained |
| `(A,n)` to `(B,n+1)` | Absent | Added |
| `(B,n)` to `(F,n+1)` | Absent | Added |

The local inspection at `(A,0)` finds that the failure condition is false and
the direct old move to `F` has been removed. The changed description nevertheless
permits the following complete course:

| Position in this specified course | Complete state | Selected failure condition |
|---|---|---|
| 0 | `(A,0)` | False |
| 1 | `(B,1)` | False |
| 2 | `(F,2)` | True |
| 3 | `(A,3)` | False |

The counter grows throughout. The complete state has not returned to `(A,0)`.
The mode and its available relations have returned to those at `A`, and the
same course is enabled again from `(A,3)` because every rule is independent of
the counter. The same failure is reached through a newly introduced route.

This establishes a modeled structural recurrence and renewed failure
possibility under the fully stated rules. It establishes no actual occurrence.
The position numbers belong to this chosen course, not to a universal time
coordinate for the underlying inquiry.

### 7.3 Controls that change the conclusion

**Counter-dependent limit.** If every move additionally requires `n < 3`, the
first course can finish at `(A,3)`, but cannot start again there. Discarding the
counter would create a false repeatability claim.

**Acyclic return of the failure.** If the retained `F`-to-`A` rule is removed,
the new course still reaches `F`. Renewed failure possibility is established,
but this course contains no return to `A`.

**Different subjects.** If the added `A`-to-`B` rule applies only to subject X
and `B`-to-`F` only to distinct subject Y, the displayed course is not a course
for one fixed subject. It requires a separately established relation that the
case has not supplied.

**Unknown enabling condition.** In a different case, suppose `B`-to-`F`
additionally requires a guard whose satisfaction at `(B,1)` has not been
established. The displayed course is then only a candidate for that case.
The fully specified unguarded example does not establish the guarded course's
feasibility.

These controls keep the analysis sensitive to the relation meanings and
conditions that enable the course. The drawing or spelling of a cycle is
insufficient.

## 8. Proposed first bounded case family

The first research package should specify the cases and expected distinctions
before implementing an evaluator. The following are proposed obligations,
not executed tests or a frozen preregistration.

| Case | Required distinction |
|---|---|
| C01 — quantity increase | A larger counter alone does not establish a new operational distinction or recurrence. |
| C02 — new route after repair | The changed structure reaches the fixed failure despite removal of the direct old route. |
| C03 — structural recurrence | An explicit compatible course returns to the relevant relations while a non-controlling counter increases. |
| C04 — consumed condition | A counter limit or consumed resource prevents repetition; an abbreviated cycle must not override it. |
| C05 — incompatible bindings | Individually described steps fail to form one course for the fixed subject. |
| C06 — acyclic failure | A new route reaches the failure without a cycle; the failure finding is retained without a cyclicity claim. |
| C07 — incomplete support | Missing support remains unresolved rather than being converted into a confirmed route or a safety result. |
| C08 — support cycle | The existing ungrounded-support case remains a justification issue and is not promoted into an operational recurrence finding. |
| C09 — preserved useful operation | A repair removes the examined failure possibilities while retaining a specified useful-operation witness; complete shutdown alone is insufficient for that target. |
| C10 — meaning change | A revised subject or failure meaning requires an explicit comparison; identical labels do not conceal the change. |

For C09, a conclusion excluding failures requires a nonempty declared domain
and coverage of the relevant continuations in that domain. Failure to find a
route during a bounded search is not a general absence proof. The useful
operation and its witness must be specified independently of the preferred
repair result.

## 9. The record needed to review a finding

A review record should allow another examiner to reconstruct:

- the exact subject, failure meaning and comparison scope;
- the starting and changed descriptions, including the permitted variations;
- the relation and condition changes, with unknown parts preserved;
- any identity correspondence and the justification for omitted coordinates;
- the full witness for a proposed course, including joint prerequisites;
- whether recurrence concerns the complete state, a justified structural
  correspondence, or only renewed failure possibility;
- the support for the model, its applicability to the subject and any actual
  observation, assessed separately;
- the useful-operation witness when the claim includes a successful repair;
- the coverage limit and the remaining unresolved questions.

The finding can be a justified modeled possibility, a feasibility claim bound
to a subject, a recorded occurrence, an exclusion established within scope,
or an unresolved candidate. These are different kinds of claim, not
interchangeable labels for release authorization.

## 10. Development sequence and stopping point

The next bounded unit is to finalize the meanings and full case descriptions
for C01–C10. The existing examples should be reused where their meanings match:
the N10 support-cycle guard, alternative support in the relation demonstrator,
and the M1–M3 distinctions between compatibility, applicability and actual
impact. Each reuse needs a named correspondence; a matching label is
insufficient.

A later implementation can provide an independently checkable comparison and
witness for that selected family. Only after its coverage and limitations are
reviewed should an actual observation study be specified. An operational
experiment would require its own scope and authorization.

The present outcome is a source-grounded research question and a proposed case
family. No new detector, production gate or experimental result is asserted.

## 11. Sources

Repository links below pin the inspected main snapshot
`25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5`. The user's supplied capability table
was historical input; Section 2 replaces broad labels with statements supported
by this limited read-only source inspection.

**[W]** User-supplied workshop contribution, 2026-11-01, preserved separately as
`MUHELYFORRAS_MENNYISEG_ES_CIKLIKUS_KIHATAS_2026-11-01.txt`. The first passage
motivates the quantity/recurrence question; the second supplies the four repair
questions. The accompanying commentary is not adopted as a set of universal
premises.

**[S1]** [Required-gate checker](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/PULSE_safe_pack_v0/tools/check_gates.py)
and [fail-closed test source](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/tests/test_check_gates_fail_closed.py).

**[S2]** [W1 record checker](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/tools/check_paradox_w1_records_v0.py),
especially input admission, observation checking and the final report boundary.

**[S3]** [M1–M3 definition contract](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md),
Sections 4–6, on joint possibilities, persistence and grounded applicability.

**[S4]** [Relation-preserving discrimination note](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/docs/PULSEMECH_RELATION_PRESERVING_DISCRIMINATION_v0.md),
[finite probe source](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/examples/relation_preserving_discrimination_v0/relation_closure_probe.py)
and [test source](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/examples/relation_preserving_discrimination_v0/test_relation_closure_probe.py).

**[S5]** [Pre-execution checker](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/examples/paradox_preexecution_impact_v0/check_impact.py),
`evidence_closure` and its assessment reporting, with the
[N10 test source](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/examples/paradox_preexecution_impact_v0/test_preexecution.py).

**[S6]** [Preserved PD-SM-02 scratch result](https://github.com/HKati/pulse-release-gates-0.1/blob/25aec1ad8045afdf2ca6ba3ffcd2c6446faf31c5/docs/PULSEMECH_PARADOX_PREEXECUTION_SCRATCH_RESULT_v0.md),
Section 5, N10, and its stated execution boundary. This document reports a
historical result; this inspection did not rerun or independently attest it.
