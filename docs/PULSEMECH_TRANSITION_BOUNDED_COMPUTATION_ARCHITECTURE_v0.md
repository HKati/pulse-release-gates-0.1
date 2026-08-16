# PULSEmech Transition-Bounded Computation Architecture

## Derivation of a Computational Model from the PULSEmech Transition Meter

**Document status:** Foundational research architecture
**Implementation status:** Formalization and experimental design
**Program context:** PULSEmech — Artifact-Bound Release Authority for AI Release Decisions

---

## 1. Purpose

This document applies the PULSEmech Transition Meter directly to the problem of computation.

The objective is not to adopt an existing sparse, event-driven, reactive, incremental, cached, differential, or neuromorphic architecture and rename it as PULSEmech.

Techniques from those fields may later serve as implementation instruments. They do not define the architecture developed here.

The objective is to determine what computational model follows from the Transition Meter when the primary measured object is not a state in isolation, but the evidence-bound transition between states.

The central research hypothesis is:

> In a persistent state-bearing system, the computational work caused by a new event may be bounded by the verified affected transition closure rather than by mandatory reprocessing of the complete representation.

The primary question is therefore not:

> How can the same complete recomputation be made faster?

It is:

> Why should a relation that has not changed, and has not become affected by a changed relation, become a new computation object?

The proposed architecture changes the criterion by which computation becomes necessary.

---

## 2. Starting Point: The Transition Meter

State-oriented measurement asks:

> What is the current state?

The PULSEmech Transition Meter asks:

> What changed first?
> Which relation changed?
> Which later transitions became reachable because of that change?
> How far did the effect propagate?
> Where did the propagation stop?
> What remained invariant?

Its basic structure is:

```
state₀
  → initiating relation change
  → opened transition structure
  → state₁
```

Applied to computation, this produces the following sequence:

```
bind the incoming event to the exact prior state
  → identify the initiating relation change
  → determine the affected transition closure
  → determine the state elements requiring materialization
  → establish the invariant boundary
  → materialize the affected successor region
  → preserve the invariant remainder
  → bind and verify the successor state
```

A new input does not automatically make the complete representation a new computation object.

---

## 3. Scope of the Comparison

This architecture is not contrasted with all forms of existing computation.

Many existing systems already use dependency tracking, memoization, cache invalidation, delta propagation, partial recomputation, or event-triggered execution.

The relevant comparison is narrower.

A from-scratch or state-wide reevaluation model can be represented as:

```
input
  → broad or complete reevaluation
  → successor state
```

The Transition Meter-derived model is:

```
persistent relational state
  → event-bound relation-change detection
  → verified affected transition closure
  → selective materialization
  → successor persistent state
```

The distinction is not merely that fewer operations may occur.

The distinction is that an operation becomes eligible for new computation only through a declared and verifiable relation to the initiating change.

---

## 4. Primary Computational Object

The complete state remains necessary.

It provides:

* the prior persistent condition;
* the context in which the event is interpreted;
* the source from which the successor state is derived;
* the reference point for later transitions.

It does not follow that the complete state must be recomputed whenever a new event arrives.

The primary computational object is:

> The verified transition induced by an event and the complete set of state elements made computationally eligible through that transition.

The successor state is the persistent result of the transition.

The affected transition closure is the object over which new computation is performed.

---

## 5. Typed Formal Model

The architecture distinguishes among the following objects:

1. persistent relational state;
2. initiating relation changes;
3. transition dependencies;
4. the affected transition subgraph;
5. the materialization domain;
6. the invariant domain.

These objects must not be collapsed into one untyped set.

Let:

[
R_t : K \rightharpoonup V
]

be the persistent relational state at logical time (t), represented as a partial mapping, where:

* (K) is the universe of stable relation or state-element identities;
* (V) is the domain of their values, bindings, or statuses;
* (\operatorname{Dom}(R_t) \subseteq K) is the set of identities present in the state at time (t).

Let:

[
e_t \in E
]

be the incoming event.

Let:

[
\Delta_t^{(0)} \subseteq \mathcal{D}
]

be the set of initiating relation changes directly produced by binding (e_t) to (R_t).

Let:

[
G_t = (N_t, L_t)
]

be the declared transition-dependency graph applicable to the current state and computation rules, where:

* (N_t) is the finite set of transition-relevant computational or relational nodes for the bound run;
* (L_t \subseteq N_t \times N_t) is the set of directed dependency or propagation edges.

Let:

[
A_t = \left(N_t^{A}, L_t^{A}\right)
]

be the affected transition subgraph of (G_t), where:

[
N_t^{A} \subseteq N_t
]

and:

[
L_t^{A}
\subseteq
L_t
\cap
\left(
N_t^{A} \times N_t^{A}
\right)
]

Let:

[
M_t \subseteq K
]

be the materialization domain: the set of state-element identities that must be recomputed, inserted, deleted, invalidated, replaced, re-bound, reordered, or otherwise changed.

Let:

[
I_t =
\operatorname{Dom}(R_t) \setminus M_t
]

be the candidate invariant domain of the prior state.

These types express separate stages:

[
e_t
\rightarrow
\Delta_t^{(0)}
\rightarrow
A_t
\rightarrow
M_t
\rightarrow
R_{t+1}
]

---

## 6. Initiating Relation Change

The relation-change detector computes:

[
\Delta_t^{(0)} = \chi(R_t, e_t)
]

where (\chi) is the declared relation-change detection mechanism.

The initiating change is not merely a numerical delta.

It may represent:

* creation of a relation;
* deletion of a relation;
* modification of a relation value;
* invalidation of an earlier relation;
* changed ordering;
* changed dependency;
* changed reachability;
* satisfaction or violation of a constraint;
* changed binding between an observation and its source;
* contradiction or supersession;
* loss of a previously required condition.

A new event is not automatically equivalent to a new effective transition.

The detector must distinguish among:

* a new effective change;
* a repeated event;
* a stale event;
* a conflicting event;
* an incorrectly ordered event;
* an event already represented in the current state;
* an event that produces no relevant relation change.

---

## 7. Affected Transition Closure

The term **transition path** remains useful for describing one causal or dependency route.

A real change may:

* branch;
* merge;
* form cycles;
* reach several outputs;
* open multiple valid paths;
* invalidate previously reachable paths.

The complete affected object is therefore not necessarily a single path.

It is an affected transition closure represented by the affected transition subgraph:

[
A_t =
\left(
N_t^{A},
L_t^{A}
\right)
]

Let the seed-node projection be:

[
S_t =
\operatorname{Seed}
\left(
\Delta_t^{(0)}
\right)
\subseteq N_t
]

Let the transition-expansion operator be a declared monotone operator:

[
\operatorname{Expand}_{G_t}
:
\mathcal{P}(N_t)
\rightarrow
\mathcal{P}(N_t)
]

The operator returns the nodes made transition-eligible from the supplied node set under the bound dependency graph, propagation predicates, and transition rules.

Define:

[
\Phi_t(X)
=========

S_t
\cup
\operatorname{Expand}_{G_t}(X)
]

The operator (\Phi_t) must be monotone on the complete lattice:

[
\mathcal{P}(N_t)
]

The affected node closure is the least fixed point:

[
N_t^{A}
=======

\mu X.\Phi_t(X)
]

Equivalently:

[
N_t^{A}
=======

\mu X
\left(
S_t
\cup
\operatorname{Expand}_{G_t}(X)
\right)
]

Because (N_t) is finite for the bound run, repeated application from the empty set produces an ascending sequence:

[
X_0 = \varnothing
]

[
X_{i+1} = \Phi_t(X_i)
]

which stabilizes at the least fixed point if the declared closure procedure completes correctly.

The closure construction remains subject to declared:

* propagation predicates;
* edge semantics;
* ordering rules;
* cycle-membership rules;
* termination rules;
* bounded-execution rules.

If an implementation cannot reach or verify the least fixed point within its declared execution bounds, the affected closure remains unresolved.

It must follow the fallback rules in Section 28 and must not emit an affected-closure completeness claim.

The affected edge set is:

[
L_t^{A}
=======

\left{
(u,v)
\in L_t
;\middle|;
u,v \in N_t^{A}
\text{ and }
(u,v)
\text{ is traversed or required to reconstruct the closure}
\right}
]

The affected transition subgraph contains:

1. nodes directly associated with the initiating changes;
2. nodes whose validity or output depends on those changes;
3. nodes reached through further valid dependency propagation;
4. edges required to reconstruct why those nodes became affected;
5. no node for which no valid transition route can be established.

---

## 8. Materialization Domain

The affected transition subgraph and the changed state domain are not necessarily identical.

A transition node may:

* inspect a state element;
* invalidate another node;
* alter reachability;
* produce several state targets;
* affect control or ordering without directly storing a value.

A materialization projection determines:

[
M_t =
\operatorname{StateTargets}
\left(
A_t,
\Delta_t^{(0)}
\right)
]

The set (M_t) contains all persistent state identities that must be:

* recomputed;
* inserted;
* deleted;
* invalidated;
* replaced;
* re-bound;
* reordered;
* marked unreachable;
* otherwise changed in the successor state.

The candidate invariant domain is:

[
I_t =
\operatorname{Dom}(R_t)
\setminus
M_t
]

New identities introduced by the event may belong to (M_t) even when they are not members of (\operatorname{Dom}(R_t)).

---

## 9. Successor-State Construction

Let:

[
\operatorname{Materialize}
\left(
R_t,
e_t,
A_t,
M_t
\right)
]

be the selective materialization operation.

The successor state is:

[
R_{t+1}
=======

\operatorname{Materialize}
\left(
R_t,
e_t,
A_t,
M_t
\right)
]

The operation must:

1. preserve all verified invariant state elements;
2. compute or apply all required changes in (M_t);
3. create or remove identities where required;
4. preserve declared ordering and dependency semantics;
5. produce a successor state bound to the prior state and event;
6. expose sufficient evidence for independent verification.

The informal expression:

[
R_{t+1}
=======

R_t
\oplus
\Delta_t
]

may still be used as a summary.

The operator (\oplus) must be understood to include the complete verified transition consequences of the initiating change, not merely direct replacement of local values.

---

## 10. Invariant Boundary

The invariant region is not defined merely by non-execution.

A state element does not become proven invariant because the producer omitted it from the selected computation.

For every:

[
k \in I_t
]

the architecture must establish that the initiating event cannot alter the declared semantics of (R_t(k)) through any applicable transition route.

The preservation condition is:

[
R_{t+1}|*{I_t}
\equiv
R_t|*{I_t}
]

where (\equiv) is a declared equivalence relation.

Depending on the system, this may mean:

* exact byte equality;
* exact value equality;
* structural equivalence;
* observational equivalence;
* a predefined numerical tolerance;
* equivalence under a declared canonicalization.

The equivalence relation must be fixed before evaluation.

It must not be introduced after a discrepancy is observed.

---

## 11. Dependency-Model Completeness

An invariant claim is only as strong as the dependency model from which it is derived.

If a relevant dependency is absent from (G_t), a state element may appear unreachable from the initiating change even though the real computation depends on it.

The architecture therefore requires evidence for both:

1. the correctness of the selected affected closure;
2. the adequacy of the dependency model used to produce it.

The invariant claim is conditional on the bound model:

> The region is invariant under the exact event, prior state, transition rules, dependency model, and declared semantics bound to the computation.

A system must not silently upgrade this conditional claim into a universal statement about undeclared dependencies.

---

## 12. Affected-Closure Soundness and Completeness

A valid transition-bounded computation must satisfy two independent conditions.

### 12.1 Affected-closure soundness

Every node and state element selected as affected must be legitimately connected to the initiating relation change.

For every:

[
n \in N_t^{A}
]

the system must establish:

[
\operatorname{ReachableAffected}
\left(
\Delta_t^{(0)},
n,
G_t
\right)
]

under the bound propagation predicates and transition rules.

For every:

[
k \in M_t
]

the system must establish:

[
\operatorname{MaterializationRequired}
\left(
k,
A_t,
\Delta_t^{(0)}
\right)
]

Affected-closure soundness prevents arbitrary or unrelated work from being included in the transition claim.

### 12.2 Affected-closure completeness

Every transition node and state element capable of changing the declared result must be included in the affected closure or materialization domain.

For every:

[
n \in N_t \setminus N_t^{A}
]

the system must establish that no valid transition route from (\Delta_t^{(0)}) makes (n) transition-eligible under the bound dependency model, propagation predicates, and transition rules.

For every:

[
k \in I_t
]

the system must establish:

[
\operatorname{NoRelevantEffect}
\left(
\Delta_t^{(0)},
k,
G_t
\right)
]

Affected-closure soundness alone may produce an incomplete successor state.

Affected-closure completeness alone may preserve correctness while allowing unnecessary broad recomputation.

Both are required for a strong transition-bounded claim.

---

## 13. Reference Semantics

Let:

[
F(R_t, e_t)
]

be the declared complete reference transition.

Let:

[
T(R_t, e_t, A_t, M_t)
]

be the transition-bounded computation.

The primary correctness requirement is:

[
T(R_t, e_t, A_t, M_t)
\equiv
F(R_t, e_t)
]

The architecture does not require every production execution to perform the complete reference computation.

The experimental and verification program must provide sufficient reference comparisons to establish that the transition-bounded method preserves the declared semantics.

For deterministic bounded experiments, exact equality should be preferred:

[
T(R_t, e_t, A_t, M_t)
=====================

F(R_t, e_t)
]

For approximate or learned systems, the comparison criterion must be declared and bound before execution.

---

## 14. Computation-Eligibility Rule

A state element becomes eligible for new computation if at least one declared condition holds:

1. its own relation changed directly;
2. it is reached through a valid dependency route from a directly changed relation;
3. a required predecessor was added, removed, invalidated, or reordered;
4. a declared constraint affecting it changed;
5. its prior result lost a condition required for reuse;
6. the system cannot establish that it remains invariant.

The sixth condition is fail-closed.

If invariance cannot be established, the system must:

* expand the affected closure;
* select a broader materialization domain;
* invoke full reference recomputation;
* or block the transition-bounded claim.

It must not silently preserve the prior value.

---

## 15. Computational Cost Model

The target cost is not adequately represented by the number of changed state elements alone.

A complete transition cost includes:

[
C_t =
C_{\mathrm{bind},t}
+
C_{\mathrm{detect},t}
+
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t}
+
C_{\mathrm{boundary},t}
+
C_{\mathrm{verify},t}
+
C_{\mathrm{commit},t}
]

where:

* (C_{\mathrm{bind},t}) binds the event to the exact prior state;
* (C_{\mathrm{detect},t}) identifies the initiating relation changes;
* (C_{\mathrm{expand},t}) determines the affected transition closure;
* (C_{\mathrm{materialize},t}) computes the changed successor region;
* (C_{\mathrm{boundary},t}) establishes the invariant boundary;
* (C_{\mathrm{verify},t}) verifies the transition claim;
* (C_{\mathrm{commit},t}) records and binds the successor state.

For the affected transition subgraph:

[
A_t =
\left(
N_t^{A},
L_t^{A}
\right)
]

a candidate target form is:

[
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t}
==========================

O
\left(
|N_t^{A}|
+
|L_t^{A}|
+
\sum_{v \in N_t^{A}} C_v
\right)
]

where (C_v) is the local computational cost of node (v).

The system-wide amortized cost must also include maintenance:

[
C_{\mathrm{total}}
==================

C_{\mathrm{initial}}
+
\sum_t
\left(
C_{\mathrm{index\ maintenance},t}
+
C_t
\right)
]

A transition-bounded architecture must not hide global work in:

* change detection;
* index construction;
* dependency discovery;
* verification;
* fallback;
* state commitment.

---

## 16. Hidden Global Work

A system that updates five relations after scanning the entire representation has not demonstrated transition-bounded computation.

It has only moved the state-wide cost into the detection stage.

A valid cost record must therefore answer:

* Was the complete state scanned?
* Was the complete dependency graph traversed?
* Was a full model pass performed before selecting the affected region?
* Was a complete reference result calculated during the production path?
* Was a global index rebuilt?
* Did a fallback perform complete recomputation?
* Were verification and commitment costs included?
* Were prior maintenance costs amortized into the result?

The architecture concerns actual work, not merely the size of the final write set.

---

## 17. Minimal Computational Architecture

The computation engine requires the following components.

### 17.1 Persistent relational state

The system preserves stable relation identity and state across events.

Required properties may include:

* stable state-element identities;
* versioned values;
* explicit dependency representation;
* deterministic serialization;
* content-addressed state fragments;
* support for partial successor materialization;
* reconstructable transition history.

### 17.2 Event-to-state binder

The binder associates the event with:

* the exact prior-state identity;
* the event identity;
* the event payload or commitment;
* the applicable relation model;
* the applicable dependency model;
* the applicable transition rules;
* the logical and observed ordering position.

### 17.3 Relation-change detector

The detector derives:

[
\Delta_t^{(0)}
]

from the bound event and prior state.

### 17.4 Transition-closure engine

The engine derives:

[
A_t =
\left(
N_t^{A},
L_t^{A}
\right)
]

from the initiating changes and the declared transition-dependency model.

### 17.5 Materialization projector

The projector derives:

[
M_t
]

from the affected transition closure.

### 17.6 Invariant-boundary mechanism

The mechanism establishes the candidate invariant domain:

[
I_t
]

and records why the affected closure does not extend into it.

### 17.7 Selective materializer

The materializer computes the successor values for (M_t) while preserving the verified invariant domain.

### 17.8 Successor-state committer

The committer binds the new state to:

* the prior state;
* the event;
* the initiating change;
* the affected transition closure;
* the materialization domain;
* the invariant-domain commitment;
* the implementation identity;
* the computation run.

---

## 18. Separation of Computational and Authority Layers

The architecture contains two distinct layers.

They must not be collapsed.

### 18.1 Transition-bounded computation engine

Its function is:

[
R_t, e_t
\rightarrow
\Delta_t^{(0)}
\rightarrow
A_t
\rightarrow
M_t
\rightarrow
R_{t+1}
]

It performs:

* event interpretation;
* relation-change detection;
* dependency propagation;
* selective materialization;
* successor construction.

### 18.2 PULSEmech artifact-bound authority layer

Its function is:

[
\text{bound computation artifacts}
\rightarrow
\text{independent verification}
\rightarrow
\text{ALLOW or BLOCK}
]

It determines whether the producer has established that:

* the exact prior state was used;
* the initiating change was valid;
* the affected closure was sound and complete;
* the invariant boundary was justified;
* the successor matched the declared semantics;
* the cost record included all relevant work;
* the claim can be independently reconstructed.

The PULSEmech authority layer does not replace the computation algorithm.

It prevents the algorithm from asserting correctness, locality, or transition-bounded cost without sufficient current-run evidence.

---

## 19. Transition-Compute Artifact Record

A minimum transition-compute record should preserve:

```
record identity
implementation identity
current-run binding
prior-state binding
event binding
relation-model binding
dependency-model binding
transition-rule binding
initiating relation-change set
affected transition subgraph
propagation-route and edge evidence
closure-termination evidence
materialization domain
invariant-domain commitment
successor-state binding
reference-semantics result
verification results
cost measurements
fallback record
decision
```

A candidate structural representation is:

```
{
  "subject": {},
  "run_binding": {},
  "implementation_binding": {},
  "prior_state_binding": {},
  "event_binding": {},
  "relation_model_binding": {},
  "dependency_model_binding": {},
  "transition_rule_binding": {},
  "initiating_relation_change": {},
  "affected_transition_closure": {},
  "materialization_domain": {},
  "invariant_boundary": {},
  "successor_state_binding": {},
  "reference_semantics": {},
  "verification": {},
  "cost_accounting": {},
  "fallback": {},
  "decision": {}
}
```

The exact schema is future implementation work.

The structural requirement is that no correctness or cost claim exists independently of its run, state, event, transition structure, verifier, and produced artifact.

---

## 20. Verification Axes

Distinct verification questions must remain separate.

### 20.1 Relation-change observation status

Was the initiating change derived from the exact bound event and prior state?

### 20.2 Dependency-model binding status

Was the affected closure computed under the exact declared dependency model?

### 20.3 Propagation-route verification status

Can the individual propagation routes inside the affected closure be reconstructed?

### 20.4 Affected-closure soundness status

Does every node and edge included in the affected transition subgraph have a valid, reconstructable relation to an initiating relation change under the bound dependency model and transition rules?

### 20.5 Affected-closure completeness status

Were all transition routes capable of affecting the declared result included?

### 20.6 Materialization soundness status

Does every selected state target have a valid relation to the initiating change and affected transition closure?

### 20.7 Invariant-preservation status

Was the state outside the materialization domain shown to remain equivalent?

### 20.8 Endpoint-binding status

Are the prior and successor states bound to the exact transition record?

### 20.9 Time-order status

Was the event evaluated from the correct state and in the correct order?

### 20.10 Alternative-path closure status

Were alternative routes that could alter the result included, excluded with evidence, or left unresolved?

### 20.11 Reconstruction reproducibility status

Can an independent verifier reconstruct the same closure, materialization domain, and decision?

### 20.12 Semantic-equivalence status

Does the selective successor satisfy the declared reference semantics?

### 20.13 Cost-accounting status

Were detection, indexing, propagation, verification, fallback, materialization, and commitment costs included?

These axes must not be collapsed into a single generic confidence field.

---

## 21. Candidate Artifact-Bound Gates

A future implementation may materialize the following candidate required gate set.

### Gate 1 — Prior-state binding

The computation must identify and bind the exact persistent state from which the transition begins.

### Gate 2 — Event binding

The event must be bound to the current run and prior state.

### Gate 3 — Relation-change validity

The initiating relation changes must be derivable from the event and prior state.

### Gate 4 — Dependency-model binding

The exact dependency and transition model used for propagation must be bound to the run.

### Gate 5 — Affected-closure soundness

Every included transition node, edge, and state target must have a valid route from an initiating change.

### Gate 6 — Affected-closure completeness

All transition routes capable of changing the declared result must be included.

### Gate 7 — Invariant preservation

The region outside the materialization domain must remain equivalent under the declared semantics.

### Gate 8 — Successor equivalence

The selective successor must satisfy the complete reference semantics.

### Gate 9 — Cost integrity

The cost record must include all detection, maintenance, expansion, verification, fallback, materialization, and commitment work.

### Gate 10 — Independent replay

An independent verifier must reconstruct the transition claim from bounded artifacts.

### Gate 11 — Fail-closed decision

Missing, stale, inconsistent, incomplete, or unverifiable evidence must block the transition-bounded claim.

These are proposed research gates.

They are not a declaration that the current PULSEmech policy already implements this gate set.

---

## 22. Difference from Sparsity

Sparsity states that few elements are:

* active;
* present;
* connected;
* selected;
* non-zero.

Transition-bounded computation states:

> Only state elements made computationally eligible by an evidenced relation change and its verified transition consequences become new computation objects.

A sparse activation pattern may still include elements unrelated to the actual change.

An affected transition closure may be dense if one relation change legitimately propagates through a large connected structure.

Therefore:

[
\text{sparse activity}
\not\Rightarrow
\text{verified transition relevance}
]

and:

[
\text{verified transition relevance}
\not\Rightarrow
\text{sparse affected closure}
]

Sparsity may be an implementation property.

It is not the rule that defines computational eligibility.

---

## 23. Difference from Event-Driven Computation

Event-driven computation schedules work after an event occurs.

An event may trigger:

* a complete handler;
* a broad subsystem;
* all registered subscribers;
* a predetermined pipeline;
* an operation unrelated to the actual scope of the change.

Transition-bounded computation asks:

> Which relations became eligible for new computation because of this exact event, through which declared dependencies, and where did that eligibility end?

Event delivery alone does not establish a transition boundary.

The architecture requires event-bound relation-change and closure determination.

---

## 24. Difference from Incremental Computation

Incremental computation may:

* retain prior results;
* propagate deltas;
* track dependencies;
* invalidate affected values;
* avoid from-scratch execution.

Those mechanisms may be used by the proposed computation engine.

The PULSEmech-derived architecture adds a stricter evidentiary and authority structure:

* the initiating relation change is explicit;
* the affected closure is an artifact;
* the transition boundary is verified;
* the invariant region is part of the claim;
* selective output is compared with declared reference semantics;
* hidden global work is included in the cost claim;
* acceptance is fail-closed;
* the result is independently reconstructable.

The architecture is therefore not defined merely by reuse of prior computation.

It is defined by verified transition eligibility and an artifact-bound claim about the boundary of required computation.

---

## 25. Difference from Caching and Memoization

A cached result may be reused because a key matches or an invalidation signal was not received.

A transition-invariant result is preserved because the system establishes that no relevant transition route from the new event reaches it.

These decisions may produce the same operational result in some cases.

They make different claims.

Caching states:

> The stored result remains reusable under the cache’s validity mechanism.

Transition-bounded computation states:

> The new event did not create a verified computational obligation for this state element.

The second claim requires an explicit relation between the event, dependency structure, and invariant boundary.

---

## 26. Difference from Neuromorphic Computation

Neuromorphic systems may use:

* spike events;
* local activation;
* asynchronous processing;
* temporal coding;
* specialized hardware;
* biologically inspired structures.

The Transition Meter does not require:

* biological analogy;
* spikes;
* specialized hardware;
* a specific clock model;
* a particular numerical representation.

Its derivation begins from:

```
persistent relational state
  → relation change
  → affected transition closure
  → selective successor materialization
```

Neuromorphic mechanisms may provide a future substrate.

They do not define the architectural principle.

---

## 27. Worst-Case Boundary

The architecture does not assume that every transition is local.

For some event (e_t):

[
|N_t^{A}|
\approx
|N_t|
]

and:

[
|M_t|
\approx
|\operatorname{Dom}(R_t)|
]

A single relation change may legitimately affect the complete system.

In that case, transition-bounded computation approaches full recomputation.

The architecture does not promise universal sublinear cost.

Its claim is:

> Computation follows the verified affected transition closure, whether that closure is local or system-wide, rather than treating the complete representation as changed by default.

The benefit depends on:

* transition locality;
* dependency structure;
* local operator cost;
* detection cost;
* closure-expansion cost;
* verification cost;
* index-maintenance cost;
* event distribution.

---

## 28. Path Explosion and Fallback

A valid implementation must handle cases in which:

* the affected closure exceeds a configured bound;
* dependency data is incomplete;
* closure construction cannot be completed or verified;
* a cyclic computation does not converge;
* event ordering is unresolved;
* concurrent changes interact;
* the invariant boundary cannot be established;
* the reference semantics cannot be verified;
* the transition becomes system-wide.

Permitted outcomes may include:

```
LOCAL-TRANSITION-PASS
EXPANDED-TRANSITION-PASS
SYSTEM-WIDE-TRANSITION-PASS
FULL-REFERENCE-RECOMPUTE
INSUFFICIENT-DEPENDENCY-EVIDENCE
INSUFFICIENT-CLOSURE-EVIDENCE
INSUFFICIENT-INVARIANCE-EVIDENCE
BLOCK
```

The system must record what actually occurred.

It must not preserve a local or transition-bounded performance label after silently performing complete recomputation.

A full recomputation may still produce a valid successor state.

It does not support a local transition-cost claim.

Failure to reach or verify the least affected fixed point must produce an unresolved-closure or broader fallback outcome.

It must not produce an affected-closure completeness claim.

---

## 29. Deletion and Negative Change

The architecture must support more than additions.

A relation may be:

* removed;
* invalidated;
* contradicted;
* disconnected;
* made unreachable;
* superseded;
* deprived of a required predecessor;
* reordered outside a valid sequence.

The absence of a formerly valid relation can open an invalidation transition.

Negative change may propagate through:

* dependency loss;
* reachability loss;
* constraint violation;
* removal of derived values;
* reopening of alternative paths;
* rollback of prior conclusions.

The initiating change model must therefore represent positive and negative relational effects.

---

## 30. Cycles and Computational Fixed Points

The affected node closure defined in Section 7 determines which nodes are transition-eligible.

A separate question arises when the values computed inside an affected cyclic region depend recursively on one another.

For acyclic dependency structures, affected nodes may be processed in topological order.

For cyclic computational structures, the architecture must declare:

* cycle membership;
* local iteration rules;
* convergence criteria;
* value-level fixed-point semantics;
* maximum iteration bounds;
* non-convergence outcomes.

Let a cyclic affected computational region use an iteration operator:

[
X_{n+1}
=======

\Psi(X_n)
]

A successful transition requires a declared fixed point:

[
X^\ast
======

\Psi(X^\ast)
]

or another explicitly defined and verifiable termination condition.

Failure to reach the declared value-level termination condition must not produce an accepted successor state.

The node-closure fixed point in Section 7 and the value-level fixed point in this section are distinct:

* the first determines the complete affected node set;
* the second determines the computed values of a cyclic affected region.

They must not be collapsed into one status.

---

## 31. Concurrency and Time Order

For concurrent events (e_a) and (e_b), let:

[
R_a
===

T
\left(
R_t,
e_a,
A_{a|t},
M_{a|t}
\right)
]

and:

[
R_{ab}
======

T
\left(
R_a,
e_b,
A_{b|a},
M_{b|a}
\right)
]

Likewise, let:

[
R_b
===

T
\left(
R_t,
e_b,
A_{b|t},
M_{b|t}
\right)
]

and:

[
R_{ba}
======

T
\left(
R_b,
e_a,
A_{a|b},
M_{a|b}
\right)
]

Here:

* (A_{a|t}) and (M_{a|t}) are derived for event (e_a) from (R_t);
* (A_{b|a}) and (M_{b|a}) are derived for event (e_b) from (R_a);
* (A_{b|t}) and (M_{b|t}) are derived for event (e_b) from (R_t);
* (A_{a|b}) and (M_{a|b}) are derived for event (e_a) from (R_b).

The following cannot be assumed:

[
R_{ab}
======

R_{ba}
]

The architecture must determine whether the transitions:

* commute;
* conflict;
* share an affected closure;
* produce a combined closure;
* require serialization;
* require rollback;
* require reconstruction from a common prior state.

A transition record must preserve sufficient ordering evidence to establish the exact state from which every initiating change was evaluated.

Time order is part of the computation semantics.

It is not merely execution metadata.

---

## 32. Approximate and Learned Systems

For probabilistic, approximate, or learned systems, exact successor equality may not be available.

The architecture still requires a declared verification target.

This may include:

* predefined numerical tolerance;
* output-distribution distance;
* semantic label equivalence;
* bounded approximation error;
* stability conditions;
* uncertainty propagation;
* path-local approximation rules;
* conditions requiring broader recomputation.

The declaration must be bound before execution.

Approximation does not remove the need to define:

* the affected closure;
* the invariant claim;
* the verification procedure;
* the cost record;
* the failure condition.

---

## 33. Initial Theorem Target

The first formal result should use a deterministic acyclic relational computation graph.

Let:

[
G =
(N,L)
]

be a finite directed acyclic dependency graph.

Let every computational node:

[
v \in N
]

implement a deterministic local function:

[
f_v
]

whose inputs consist only of:

* outputs of predecessor nodes declared by (G);
* local inputs explicitly bound to (v).

Let:

[
\Delta_t^{(0)}
]

be the complete set of directly observed primitive changes introduced by event (e_t).

Let:

[
S_t
===

\operatorname{Seed}
\left(
\Delta_t^{(0)}
\right)
\subseteq N
]

be the complete set of graph nodes whose local inputs or source values are directly affected by the initiating relation changes.

Let:

[
A_t =
\left(
N_t^{A},
L_t^{A}
\right)
]

be the descendant closure subgraph of (S_t) under (G), including (S_t).

Let (M_t) contain the persistent state outputs produced by nodes in (N_t^{A}), together with every insertion, deletion, or invalidation target directly represented by (\Delta_t^{(0)}).

Assume that:

1. (R_t) is a semantically valid complete evaluation of (G) under the bound input state preceding (e_t);

2. every primitive change introduced by (e_t) is represented in (\Delta_t^{(0)}) and mapped into (S_t);

3. local inputs of nodes outside (S_t) are unchanged by (e_t);

4. every node output depends only on predecessor outputs and bound local inputs declared by (G);

5. every local node function is deterministic and free of undeclared side effects;

6. (G) contains every dependency capable of affecting the declared successor outputs;

7. nodes in (N_t^{A}) are reevaluated in a valid topological order;

8. state elements outside (M_t) retain their prior values.

A candidate theorem is:

> Under these assumptions, reevaluating only the nodes in (N_t^{A}), applying every direct insertion, deletion, and invalidation represented in (\Delta_t^{(0)}), and preserving state elements outside (M_t) produces the same successor state as complete reevaluation of (G) under the post-event input state.

Formally:

[
T(R_t,e_t,A_t,M_t)
==================

F(R_t,e_t)
]

and:

[
R_{t+1}|_{I_t}
==============

R_t|_{I_t}
]

The transition-work target is:

[
O
\left(
|\Delta_t^{(0)}|
+
|N_t^{A}|
+
|L_t^{A}|
+
\sum_{v \in N_t^{A}} C_v
\right)
]

for change projection, affected-subgraph traversal, and affected-node evaluation.

No required binding, index-maintenance, boundary-verification, independent-verification, fallback, or commitment cost may be excluded from the complete measured result.

---

## 34. Initial Experimental Program

### Experiment 1 — Exact acyclic relational graph

Use a deterministic directed acyclic graph with explicit reverse dependencies.

Objectives:

* detect exact initiating changes;
* construct the affected descendant closure;
* selectively recompute affected nodes;
* compare byte-identical output with complete reevaluation;
* record the invariant domain;
* account for all costs.

### Experiment 2 — Branching and merging paths

Use a graph in which one change opens several paths that later merge.

Objectives:

* distinguish a single path from the complete affected subgraph;
* verify affected-closure soundness;
* verify affected-closure completeness;
* prevent duplicate materialization.

### Experiment 3 — Relation deletion

Remove a relation required by multiple downstream results.

Objectives:

* measure negative propagation;
* verify invalidation;
* preserve unaffected branches;
* record removed and unreachable targets.

### Experiment 4 — Cyclic relational graph

Introduce cycles and declared value-level fixed-point semantics.

Objectives:

* distinguish node-closure determination from value convergence;
* define bounded iteration;
* establish convergence;
* record iteration cost;
* fail closed on unresolved computation.

### Experiment 5 — Concurrent events

Apply commuting and conflicting event pairs.

Objectives:

* verify ordering;
* identify shared affected regions;
* compare serialized and combined execution;
* detect invalid event-state bindings.

### Experiment 6 — Incomplete dependency model

Intentionally remove a relevant edge from the declared dependency graph.

Objectives:

* demonstrate false invariance;
* test dependency-model verification;
* confirm that incomplete evidence blocks the transition-bounded claim.

### Experiment 7 — Learned component boundary

Place a learned component behind a deterministic relational dependency boundary.

Objectives:

* determine whether invocation can be made transition-eligible;
* distinguish transition relevance from sparse activation;
* define an approximate reference criterion;
* identify hidden full-model work.

### Experiment 8 — Hidden-cost audit

Instrument:

* event binding;
* change detection;
* dependency lookups;
* index maintenance;
* closure traversal;
* materialization;
* invariant-boundary verification;
* independent verification;
* fallback;
* commitment.

Objectives:

* prevent local writes from concealing global reads;
* determine the real cost function;
* identify workloads under which the architecture produces a net benefit.

---

## 35. Artifact-Bound Experimental Chain

Each experimental claim should bind:

```
current run
  → implementation artifact
  → prior-state artifact
  → event artifact
  → relation model
  → dependency model
  → transition rules
  → initiating change
  → affected transition closure
  → materialization domain
  → invariant commitment
  → selective successor
  → complete reference successor
  → verifier output
  → cost trace
  → fallback record
  → decision
```

A statement such as:

> The system recomputed only 0.2% of the representation.

is insufficient by itself.

The artifact package must establish:

* the total representation;
* the exact prior state;
* the exact event;
* the initiating relation change;
* the affected closure;
* the reason propagation stopped;
* the materialized state domain;
* the candidate invariant domain;
* the reference result;
* whether hidden global work occurred;
* whether fallback occurred;
* which costs were included;
* which verifier accepted the claim.

---

## 36. Primary Research Questions

1. Can initiating relation changes be detected without complete state scanning?

2. Which persistent representations support stable and efficient relation identity?

3. Which dependency structures permit exact affected-closure traversal?

4. Can affected-closure completeness be established at lower cost than complete reevaluation?

5. How can the dependency model itself be verified as adequate for a declared output?

6. How can an invariant region be committed without rereading the complete state?

7. What classes of systems exhibit stable transition locality?

8. When does dependency-index maintenance exceed the computation it avoids?

9. How should closure explosion be detected and represented?

10. How should cyclic computational regions be bounded and verified?

11. How should concurrent transitions be merged, serialized, or blocked?

12. Can learned components expose reliable transition boundaries?

13. Which equivalence claims remain valid for approximate computation?

14. Can earlier transition records serve as reusable evidence for later events?

15. What machine model best expresses transition-bounded complexity?

---

## 37. Falsification Conditions

The research hypothesis is unsupported for a tested system if one or more of the following remain true:

* initiating change detection requires complete state scanning;
* the affected closure cannot be determined without complete recomputation;
* the dependency model omits relevant effects;
* the invariant boundary is assumed rather than established;
* selective materialization fails the declared reference semantics;
* hidden global operations are excluded from the cost record;
* dependency maintenance dominates avoided computation under representative workloads;
* the transition claim cannot be independently reconstructed;
* stale or incorrectly ordered events can produce accepted states;
* unresolved closure is accepted instead of failing closed;
* non-convergent cyclic computation produces an accepted successor;
* a full fallback is reported as local computation;
* the claimed locality disappears under representative events.

These conditions test the central hypothesis directly.

They are not secondary implementation defects.

---

## 38. Strong Form of the Hypothesis

A strong form of the research hypothesis is:

> Given a persistent relational state, an event-bound relation-change detector, a complete and correct transition-dependency model, a sound and complete affected transition closure, and an independently verifiable invariant boundary, a successor state can be selectively materialized with semantic equivalence to complete reevaluation while making the new computational work a function of the affected transition closure and its verification cost.

Formally:

[
T(R_t,e_t,A_t,M_t)
\equiv
F(R_t,e_t)
]

with:

[
C_t =
f
\left(
|\Delta_t^{(0)}|,
|N_t^{A}|,
|L_t^{A}|,
\sum_{v \in N_t^{A}} C_v,
C_{\mathrm{boundary},t},
C_{\mathrm{verify},t},
C_{\mathrm{commit},t}
\right)
]

rather than mandatory direct dependence on the complete prior-state domain:

[
|\operatorname{Dom}(R_t)|
]

This statement is conditional.

Its purpose is to expose the conditions that must be implemented, measured, and verified.

---

## 39. PULSEmech-Specific Contribution

The proposed architecture does not claim that dependency tracking, delta propagation, selective recomputation, or persistent state are individually new.

The PULSEmech-specific contribution is the structure:

[
\text{observed relation change}
\rightarrow
\text{transition eligibility}
\rightarrow
\text{verified affected closure}
\rightarrow
\text{bounded materialization}
\rightarrow
\text{artifact-bound authority decision}
]

Its defining properties are:

1. **Transition eligibility**
   New computation requires a valid relation to the initiating change.

2. **Explicit affected closure**
   The complete transition-relevant subgraph becomes a first-class artifact.

3. **Negative boundary claim**
   The system records not only what became affected, but why the remaining state did not.

4. **Semantic reference binding**
   The selective successor is evaluated against declared complete semantics.

5. **Complete cost binding**
   Detection, maintenance, propagation, verification, fallback, and commitment are included.

6. **Independent reconstruction**
   The producer’s claim is not accepted without independent verification.

7. **Fail-closed authority**
   An unresolved boundary blocks the transition-bounded claim.

This is more than a scheduling or optimization policy.

It is a computational authority model in which a relation change creates a bounded and verifiable obligation to compute.

---

## 40. Technical Assessment

The strongest architectural move is the change in computational object.

The system does not begin by assuming that every new event requires another pass over the complete representation.

It first asks which relations became computationally eligible.

The decisive technical problem is the invariant boundary.

Selective recomputation is insufficient by itself.

The architecture must establish that:

* the initiating relation change was correctly identified;
* the dependency model included all relevant effects;
* the affected closure was sound;
* the affected closure was complete;
* the omitted state could not alter the declared result;
* the successor remained equivalent to the reference semantics;
* the measured cost did not conceal global work.

If these properties can be made bounded, artifact-addressable, and independently verifiable, the result is not merely a faster implementation of the same state-wide computational assumption.

The primary unit of new work becomes the evidenced transition.

---

## 41. Development Boundary

This document defines a foundational architecture, formalization target, and experimental program.

It does not claim that the current PULSEmech repository already implements:

* a persistent relational computation runtime;
* a relation-change detector;
* a transition-closure engine;
* dependency-model completeness verification;
* invariant-boundary proofs;
* selective successor materialization;
* a production transition-compute gate set.

The existing PULSEmech program provides the artifact-bound authority mechanics through which future implementations and experiments can be:

* bound to their current runs;
* independently verified;
* replayed;
* measured;
* accepted;
* or blocked.

The computation research lane must not alter or weaken the existing release-authority boundary.

Its implementation claims must enter that boundary as evidence-bearing subjects.

---

## 42. Architectural Summary

The proposed model is:

```
persistent relational state
  → bind the event to the exact prior state
  → detect the initiating relation change
  → traverse the declared transition dependencies
  → construct the affected transition closure
  → derive the materialization domain
  → establish the invariant boundary
  → selectively materialize the affected successor region
  → preserve the verified invariant region
  → bind the successor state
  → independently verify the transition claim
  → allow or block the claim
```

The central principle is:

> A new event does not make the complete representation a new computation object.

Only a state element that changed directly, or became affected through a verified transition closure, becomes eligible for new computation.

The resulting research hypothesis is:

> The computation of a persistent intelligent system may be organized around evidence-bound transitions, with computational work determined by the verified affected transition closure rather than by mandatory repeated processing of the complete representation.

If established, this would not merely accelerate the same computation.

It would change what the system recognizes as requiring computation.
