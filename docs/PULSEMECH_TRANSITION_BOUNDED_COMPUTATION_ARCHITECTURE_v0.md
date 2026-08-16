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

```text
state₀
  → initiating relation change
  → opened transition structure
  → state₁
```

Applied to computation, this produces the following sequence:

```text
bind the incoming event to the exact prior state
  → identify the initiating relation change
  → bind prior and candidate-successor dependency structures
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

```text
input
  → broad or complete reevaluation
  → successor state
```

The Transition Meter-derived model is:

```text
persistent relational state
  → event-bound relation-change detection
  → dependency-transition binding
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

- the prior persistent condition;
- the context in which the event is interpreted;
- the source from which the successor state is derived;
- the reference point for later transitions.

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
3. prior and candidate-successor dependency structures;
4. dependency-structure changes;
5. the polarity-preserving transition-dependency carrier;
6. the affected transition subgraph;
7. the inspected frontier;
8. the materialization domain;
9. the invariant domain.

These objects must not be collapsed into one untyped set.

Let:

\[
R_t : K \rightharpoonup V
\]

be the persistent relational state at logical time \(t\), represented as a partial mapping, where:

- \(K\) is the universe of stable relation or state-element identities;
- \(V\) is the domain of their values, bindings, or statuses;
- \(\operatorname{Dom}(R_t) \subseteq K\) is the set of identities present in the state at time \(t\).

Let:

\[
e_t \in E
\]

be the incoming event.

Let:

\[
\Delta_t^{(0)} \subseteq \mathcal{D}
\]

be the set of initiating state or relation changes directly produced by binding \(e_t\) to \(R_t\).

Let:

\[
G_t^- = (N_t^-, L_t^-)
\]

be the dependency graph bound to the prior state, and let:

\[
G_t^+ = (N_t^+, L_t^+)
\]

be the candidate-successor dependency graph obtained after applying the event-local dependency changes declared for \(e_t\).

Let:

\[
\Delta_t^G =
\bigl(
N_t^{\mathrm{add}},
N_t^{\mathrm{remove}},
L_t^{\mathrm{add}},
L_t^{\mathrm{remove}}
\bigr)
\]

be the dependency-structure delta that relates \(G_t^-\) and \(G_t^+\).

Define the polarity-preserving transition-dependency carrier:

\[
G_t^{\ast} =
\bigl(
N_t^{\ast},
\mathcal{L}_t^{\ast},
\pi_t
\bigr)
\]

where:

\[
N_t^{\ast} = N_t^- \cup N_t^+
\]

and each dependency record in \(\mathcal{L}_t^{\ast}\) preserves whether the dependency is present in the prior graph, the candidate-successor graph, or both:

\[
\pi_t : \mathcal{L}_t^{\ast}
\rightarrow
\{\mathrm{prior\mbox{-}only},\mathrm{successor\mbox{-}only},\mathrm{both}\}
\]

The carrier must preserve prior-only dependencies needed to propagate invalidation after deletion and successor-only dependencies needed to propagate effects opened by addition.

Let:

\[
A_t = \bigl(N_t^A, L_t^A\bigr)
\]

be the affected transition subgraph derived under the bound transition semantics, where:

\[
N_t^A \subseteq N_t^{\ast}
\]

and:

\[
L_t^A \subseteq \mathcal{L}_t^{\ast}
\]

Let:

\[
Q_t \subseteq \mathcal{L}_t^{\ast}
\]

be the inspected frontier set: every dependency record enumerated and evaluated while determining whether propagation continues or stops, including records rejected by the propagation predicates.

Let:

\[
M_t \subseteq K
\]

be the materialization domain: the set of state-element identities that must be recomputed, inserted, deleted, invalidated, replaced, re-bound, reordered, or otherwise changed.

Let:

\[
I_t = \operatorname{Dom}(R_t) \setminus M_t
\]

be the candidate invariant domain of the prior state.

These types express separate stages:

\[
(R_t,e_t,G_t^-)
\rightarrow
(\Delta_t^{(0)},\Delta_t^G,G_t^+)
\rightarrow
G_t^{\ast}
\rightarrow
(A_t,Q_t)
\rightarrow
M_t
\rightarrow
R_{t+1}
\]

---

## 6. Initiating Relation Change

The relation-change detector computes:

\[
\Delta_t^{(0)} = \chi(R_t,e_t)
\]

where \(\chi\) is the declared relation-change detection mechanism.

The initiating change is not merely a numerical delta.

It may represent:

- creation of a relation;
- deletion of a relation;
- modification of a relation value;
- invalidation of an earlier relation;
- changed ordering;
- changed dependency;
- changed reachability;
- satisfaction or violation of a constraint;
- changed binding between an observation and its source;
- contradiction or supersession;
- loss of a previously required condition.

A new event is not automatically equivalent to a new effective transition.

The detector must distinguish among:

- a new effective change;
- a repeated event;
- a stale event;
- a conflicting event;
- an incorrectly ordered event;
- an event already represented in the current state;
- an event that produces no relevant relation change.

---

## 7. Dependency-Graph Transition Binding

Dependency changes are part of the transition object.

A single graph identified only as the graph for the “current state” is insufficient when the event can add or remove dependencies.

If only the prior graph is used, propagation opened by a new dependency can be missed.

If only the candidate-successor graph is used, invalidation that must travel through a removed dependency can be missed.

The architecture therefore binds:

- the exact prior dependency graph \(G_t^-\);
- the declared dependency delta \(\Delta_t^G\);
- the exact candidate-successor dependency graph \(G_t^+\);
- the polarity-preserving carrier \(G_t^{\ast}\);
- the transition rules that assign effect semantics to prior-only, successor-only, and unchanged dependency records.

The relation must be verifiable:

\[
G_t^+ = \operatorname{ApplyGraphDelta}(G_t^-,\Delta_t^G)
\]

A mismatch between the declared delta and the candidate-successor graph leaves the dependency transition unresolved and blocks an affected-closure completeness claim.

---

## 8. Affected Transition Closure

The term **transition path** remains useful for describing one causal or dependency route.

A real change may:

- branch;
- merge;
- form cycles;
- reach several outputs;
- open multiple valid paths;
- invalidate previously reachable paths.

The complete affected object is therefore not necessarily a single path.

It is an affected transition closure represented by:

\[
A_t = \bigl(N_t^A,L_t^A\bigr)
\]

Let the seed-node projection be:

\[
S_t =
\operatorname{Seed}
\bigl(
\Delta_t^{(0)},
\Delta_t^G
\bigr)
\subseteq N_t^{\ast}
\]

The seed set includes nodes directly affected by state changes and endpoints whose transition eligibility changes because a node or dependency was added or removed.

Let the transition-expansion operator be a declared monotone operator:

\[
\operatorname{Expand}_{G_t^{\ast},\Theta_t}
:
\mathcal{P}(N_t^{\ast})
\rightarrow
\mathcal{P}(N_t^{\ast})
\]

where \(\Theta_t\) is the bound propagation semantics, including the treatment of edge polarity, invalidation, ordering, constraints, cycles, and alternative routes.

Define:

\[
\Phi_t(X) =
S_t
\cup
\operatorname{Expand}_{G_t^{\ast},\Theta_t}(X)
\]

The operator \(\Phi_t\) must be monotone on the complete lattice \(\mathcal{P}(N_t^{\ast})\).

The affected node closure is the least fixed point:

\[
N_t^A = \mu X.\Phi_t(X)
\]

Equivalently:

\[
N_t^A =
\mu X
\left(
S_t
\cup
\operatorname{Expand}_{G_t^{\ast},\Theta_t}(X)
\right)
\]

Because \(N_t^{\ast}\) is finite for the bound run, repeated application from the empty set produces an ascending sequence:

\[
X_0 = \varnothing
\]

\[
X_{i+1} = \Phi_t(X_i)
\]

which stabilizes at the least fixed point if the declared closure procedure completes correctly.

The closure construction remains subject to declared:

- propagation predicates;
- dependency-record polarity semantics;
- ordering rules;
- cycle-membership rules;
- termination rules;
- bounded-execution rules.

If an implementation cannot reach or verify the least fixed point within its declared execution bounds, the affected closure remains unresolved.

It must follow the fallback rules in Section 29 and must not emit an affected-closure completeness claim.

### 8.1 Inspected frontier

The closure engine records:

\[
Q_t =
\left\{
\ell \in \mathcal{L}_t^{\ast}
\;\middle|\;
\ell
\text{ was enumerated and evaluated while determining the closure boundary}
\right\}
\]

The inspected frontier includes accepted and rejected candidate dependency records.

A rejected record may still carry computational cost because the propagation predicate had to be evaluated to establish that the closure stops at that boundary.

### 8.2 Semantically affected edges

The affected edge set is defined by the bound transition semantics, not by the incidental traversal order of one implementation:

\[
L_t^A =
\left\{
\ell \in \mathcal{L}_t^{\ast}
\;\middle|\;
\begin{array}{l}
\operatorname{src}(\ell),\operatorname{dst}(\ell) \in N_t^A,\\
\operatorname{Relevant}_{\Theta_t}
\bigl(
\ell,
\Delta_t^{(0)},
\Delta_t^G,
N_t^A
\bigr)
\end{array}
\right\}
\]

A dependency record is semantically relevant when, under \(\Theta_t\), it:

- transmits a positive effect;
- transmits invalidation or withdrawal through a prior-only dependency;
- opens propagation through a successor-only dependency;
- contributes to a merge, constraint, ordering, or alternative route capable of changing the result;
- is required to reconstruct why an affected node is included.

Thus a merge dependency cannot be omitted merely because another predecessor caused the implementation to mark the merge node as visited first.

The affected transition subgraph contains:

1. nodes directly associated with the initiating state or dependency changes;
2. nodes whose validity or output depends on those changes;
3. nodes reached through further valid dependency propagation;
4. every semantically relevant dependency record required by the bound transition semantics;
5. no node or dependency record for which no valid transition relation can be established.

---

## 9. Materialization Domain

The affected transition subgraph and the changed state domain are not necessarily identical.

A transition node may:

- inspect a state element;
- invalidate another node;
- alter reachability;
- produce several state targets;
- affect control or ordering without directly storing a value.

A materialization projection determines:

\[
M_t =
\operatorname{StateTargets}
\bigl(
A_t,
\Delta_t^{(0)},
\Delta_t^G
\bigr)
\]

The set \(M_t\) contains all persistent state identities that must be:

- recomputed;
- inserted;
- deleted;
- invalidated;
- replaced;
- re-bound;
- reordered;
- marked unreachable;
- otherwise changed in the successor state.

The candidate invariant domain is:

\[
I_t = \operatorname{Dom}(R_t) \setminus M_t
\]

New identities introduced by the event may belong to \(M_t\) even when they are not members of \(\operatorname{Dom}(R_t)\).

---

## 10. Successor-State Construction

Let:

\[
\operatorname{Materialize}
\bigl(
R_t,
e_t,
G_t^+,
A_t,
M_t
\bigr)
\]

be the selective materialization operation.

The successor state is:

\[
R_{t+1} =
\operatorname{Materialize}
\bigl(
R_t,
e_t,
G_t^+,
A_t,
M_t
\bigr)
\]

The operation must:

1. preserve all verified invariant state elements;
2. compute or apply all required changes in \(M_t\);
3. create or remove identities where required;
4. use the bound candidate-successor dependency graph;
5. preserve declared ordering and dependency semantics;
6. produce a successor state bound to the prior state and event;
7. expose sufficient evidence for independent verification.

The informal expression:

\[
R_{t+1} = R_t \oplus \Delta_t
\]

may still be used as a summary.

The operator \(\oplus\) must be understood to include the complete verified transition consequences of the initiating state and dependency changes, not merely direct replacement of local values.

---

## 11. Invariant Boundary

The invariant region is not defined merely by non-execution.

A state element does not become proven invariant because the producer omitted it from the selected computation.

For every \(k \in I_t\), the architecture must establish that the initiating event and dependency transition cannot alter the declared semantics of \(R_t(k)\) through any applicable transition route.

The preservation condition is:

\[
R_{t+1}|_{I_t} \equiv R_t|_{I_t}
\]

where \(\equiv\) is a declared equivalence relation.

Depending on the system, this may mean:

- exact byte equality;
- exact value equality;
- structural equivalence;
- observational equivalence;
- a predefined numerical tolerance;
- equivalence under a declared canonicalization.

The equivalence relation must be fixed before evaluation.

It must not be introduced after a discrepancy is observed.

---

## 12. Dependency-Model Completeness

An invariant claim is only as strong as the dependency models and transition rules from which it is derived.

If a relevant dependency is absent from both the bound prior and candidate-successor models, a state element may appear unreachable even though the real computation depends on it.

The architecture therefore requires evidence for:

1. the validity of \(G_t^-\);
2. the validity of \(\Delta_t^G\);
3. the derivation of \(G_t^+\) from \(G_t^-\) and \(\Delta_t^G\);
4. the adequacy of the polarity-preserving carrier \(G_t^{\ast}\);
5. the correctness of the selected affected closure.

The invariant claim is conditional on the bound model:

> The region is invariant under the exact event, prior state, prior dependency graph, dependency delta, candidate-successor dependency graph, transition rules, and declared semantics bound to the computation.

A system must not silently upgrade this conditional claim into a universal statement about undeclared dependencies.

---

## 13. Affected-Closure Soundness and Completeness

A valid transition-bounded computation must satisfy two independent conditions.

### 13.1 Affected-closure soundness

Every node, dependency record, and state element selected as affected must be legitimately connected to an initiating state or dependency change.

For every \(n \in N_t^A\), the system must establish:

\[
\operatorname{ReachableAffected}
\bigl(
\Delta_t^{(0)},
\Delta_t^G,
n,
G_t^{\ast},
\Theta_t
\bigr)
\]

For every \(\ell \in L_t^A\), the system must establish:

\[
\operatorname{Relevant}_{\Theta_t}
\bigl(
\ell,
\Delta_t^{(0)},
\Delta_t^G,
N_t^A
\bigr)
\]

For every \(k \in M_t\), the system must establish:

\[
\operatorname{MaterializationRequired}
\bigl(
k,
A_t,
\Delta_t^{(0)},
\Delta_t^G
\bigr)
\]

Affected-closure soundness prevents arbitrary or unrelated work from being included in the transition claim.

### 13.2 Affected-closure completeness

Every transition node, dependency route, and state element capable of changing the declared result must be included or explicitly resolved.

For every \(n \in N_t^{\ast} \setminus N_t^A\), the system must establish that no valid transition route from \(\Delta_t^{(0)}\) or \(\Delta_t^G\) makes \(n\) transition-eligible under the bound carrier and transition semantics.

For every alternative dependency route capable of changing an affected merge, constraint, order, or output, the system must establish that the route is:

- represented in \(L_t^A\);
- rejected by a recorded propagation predicate; or
- unresolved, in which case completeness must not pass.

For every \(k \in I_t\), the system must establish:

\[
\operatorname{NoRelevantEffect}
\bigl(
\Delta_t^{(0)},
\Delta_t^G,
k,
G_t^{\ast},
\Theta_t
\bigr)
\]

Affected-closure soundness alone may produce an incomplete successor state.

Affected-closure completeness alone may preserve correctness while allowing unnecessary broad recomputation.

Both are required for a strong transition-bounded claim.

---

## 14. Reference Semantics

Let:

\[
F(R_t,e_t,G_t^-)
\]

be the declared complete reference transition, including the event-induced dependency transition.

Let:

\[
T(R_t,e_t,G_t^-,G_t^+,A_t,M_t)
\]

be the transition-bounded computation.

The primary correctness requirement is:

\[
T(R_t,e_t,G_t^-,G_t^+,A_t,M_t)
\equiv
F(R_t,e_t,G_t^-)
\]

The architecture does not require every production execution to perform the complete reference computation.

The experimental and verification program must provide sufficient reference comparisons to establish that the transition-bounded method preserves the declared semantics.

For deterministic bounded experiments, exact equality should be preferred:

\[
T(R_t,e_t,G_t^-,G_t^+,A_t,M_t) =
F(R_t,e_t,G_t^-)
\]

For approximate or learned systems, the comparison criterion must be declared and bound before execution.

---

## 15. Computation-Eligibility Rule

A state element becomes eligible for new computation if at least one declared condition holds:

1. its own relation changed directly;
2. it is reached through a valid dependency route from a directly changed relation;
3. a dependency was added and opens a new effect route;
4. a dependency was removed and its former dependent requires invalidation or reconstruction;
5. a required predecessor was added, removed, invalidated, or reordered;
6. a declared constraint affecting it changed;
7. its prior result lost a condition required for reuse;
8. the system cannot establish that it remains invariant.

The eighth condition is fail-closed.

If invariance cannot be established, the system must:

- expand the affected closure;
- select a broader materialization domain;
- invoke full reference recomputation;
- or block the transition-bounded claim.

It must not silently preserve the prior value.

---

## 16. Computational Cost Model

The target cost is not adequately represented by the number of changed state elements or accepted affected edges alone.

A complete transition cost includes:

\[
C_t =
C_{\mathrm{bind},t}
+
C_{\mathrm{detect},t}
+
C_{\mathrm{graph\mbox{-}bind},t}
+
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t}
+
C_{\mathrm{boundary},t}
+
C_{\mathrm{verify},t}
+
C_{\mathrm{fallback},t}
+
C_{\mathrm{commit},t}
\]

where:

- \(C_{\mathrm{bind},t}\) binds the event to the exact prior state;
- \(C_{\mathrm{detect},t}\) identifies initiating state and relation changes;
- \(C_{\mathrm{graph\mbox{-}bind},t}\) binds and verifies \(G_t^-\), \(\Delta_t^G\), \(G_t^+\), and \(G_t^{\ast}\);
- \(C_{\mathrm{expand},t}\) determines the affected transition closure and evaluates the inspected frontier;
- \(C_{\mathrm{materialize},t}\) computes the changed successor region;
- \(C_{\mathrm{boundary},t}\) establishes the invariant boundary;
- \(C_{\mathrm{verify},t}\) verifies the transition claim;
- \(C_{\mathrm{fallback},t}\) is the actual cost of any broader evaluation or full reference recomputation selected because the transition-bounded path could not be completed or verified; it is zero only when no fallback is executed;
- \(C_{\mathrm{commit},t}\) records and binds the successor state.

The inspected frontier, not only the semantically accepted affected edge set, determines expansion work.

A candidate target form is:

\[
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t} =
O\left(
|N_t^A|
+
|Q_t|
+
\sum_{v \in N_t^A} C_v
\right)
\]

where \(C_v\) is the local computational cost of node \(v\).

Because \(L_t^A \subseteq Q_t\) is not guaranteed to account for rejected frontier records, \(|L_t^A|\) must not be used as the sole edge term in an expansion-cost claim.

The system-wide amortized cost must also include maintenance:

\[
C_{\mathrm{total}} =
C_{\mathrm{initial}}
+
\sum_t
\left(
C_{\mathrm{index\mbox{-}maintenance},t}
+
C_t
\right)
\]

For per-transition reporting under an amortized measurement window, define:

\[
\widehat{C}_t =
C_{\mathrm{index\mbox{-}maintenance},t}
+
C_t
\]

A complete measured result must report \(C_t\), including conditional fallback work, and must also report or amortize \(C_{\mathrm{index\mbox{-}maintenance},t}\) through \(\widehat{C}_t\) or the system-wide total above.

A transition-bounded architecture must not hide global work in:

- event binding;
- change detection;
- dependency graph derivation;
- index construction;
- dependency discovery;
- frontier inspection;
- verification;
- fallback;
- state commitment.

---

## 17. Hidden Global Work

A system that updates five relations after scanning the entire representation has not demonstrated total transition-bounded computation.

It has only moved the state-wide cost into an earlier stage.

A valid cost record must therefore answer:

- Was the complete prior state scanned during event binding?
- Was the complete prior state scanned during change detection?
- Were the prior or candidate dependency graphs rebuilt globally?
- Was the complete dependency carrier traversed?
- How many candidate or frontier dependency records were enumerated and rejected?
- Was a full model pass performed before selecting the affected region?
- Was a complete reference result calculated during the production path?
- Was a global index rebuilt?
- Did a fallback perform complete recomputation?
- Were verification and commitment costs included?
- Were prior maintenance costs amortized into the result?

The architecture concerns actual work, not merely the size of the final write set.

---

## 18. Minimal Computational Architecture

The computation engine requires the following components.

### 18.1 Persistent relational state

The system preserves stable relation identity and state across events.

Required properties may include:

- stable state-element identities;
- versioned values;
- explicit dependency representation;
- deterministic serialization;
- content-addressed state fragments;
- support for partial successor materialization;
- reconstructable transition history.

### 18.2 Event-to-state binder

The binder associates the event with:

- the exact prior-state identity;
- the event identity;
- the event payload or commitment;
- the applicable relation model;
- the applicable prior dependency model;
- the declared dependency-transition rules;
- the logical and observed ordering position.

### 18.3 Relation-change detector

The detector derives \(\Delta_t^{(0)}\) from the bound event and prior state.

### 18.4 Dependency-transition binder

The binder derives and verifies:

\[
G_t^-,\quad \Delta_t^G,\quad G_t^+,\quad G_t^{\ast}
\]

### 18.5 Transition-closure engine

The engine derives:

\[
A_t = (N_t^A,L_t^A)
\]

and records the inspected frontier \(Q_t\).

### 18.6 Materialization projector

The projector derives \(M_t\) from the initiating changes and affected transition closure.

### 18.7 Invariant-boundary mechanism

The mechanism establishes the candidate invariant domain \(I_t\) and records why the affected closure does not extend into it.

### 18.8 Selective materializer

The materializer computes the successor values for \(M_t\) while preserving the verified invariant domain.

### 18.9 Successor-state committer

The committer binds the new state to:

- the prior state;
- the event;
- the initiating state changes;
- the dependency delta;
- the prior and candidate dependency graphs;
- the affected transition closure;
- the inspected frontier record;
- the materialization domain;
- the invariant-domain commitment;
- the implementation identity;
- the computation run.

---

## 19. Separation of Computational and Authority Layers

The architecture contains two distinct layers.

They must not be collapsed.

### 19.1 Transition-bounded computation engine

Its function is:

\[
(R_t,e_t,G_t^-)
\rightarrow
(\Delta_t^{(0)},\Delta_t^G,G_t^+)
\rightarrow
G_t^{\ast}
\rightarrow
(A_t,Q_t)
\rightarrow
M_t
\rightarrow
R_{t+1}
\]

It performs:

- event interpretation;
- relation-change detection;
- dependency-transition binding;
- dependency propagation;
- selective materialization;
- successor construction.

### 19.2 PULSEmech artifact-bound authority layer

Its function is:

```text
bound computation artifacts
  → independent verification
  → ALLOW or BLOCK
```

It determines whether the producer has established that:

- the exact prior state was used;
- the initiating state and dependency changes were valid;
- the prior and candidate dependency graphs were correctly bound;
- the affected closure was sound and complete;
- the inspected frontier and closure boundary were recorded;
- the invariant boundary was justified;
- the successor matched the declared semantics;
- the cost record included all relevant work;
- the claim can be independently reconstructed.

The PULSEmech authority layer does not replace the computation algorithm.

It prevents the algorithm from asserting correctness, locality, or transition-bounded cost without sufficient current-run evidence.

---

## 20. Transition-Compute Artifact Record

A minimum transition-compute record should preserve:

```text
record identity
implementation identity
current-run binding
prior-state binding
event binding
relation-model binding
prior dependency-model binding
dependency-delta binding
candidate-successor dependency-model binding
transition-dependency carrier binding
transition-rule binding
initiating relation-change set
affected transition subgraph
inspected frontier record
propagation-route and semantic-edge evidence
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

```json
{
  "subject": {},
  "run_binding": {},
  "implementation_binding": {},
  "prior_state_binding": {},
  "event_binding": {},
  "relation_model_binding": {},
  "prior_dependency_model_binding": {},
  "dependency_delta_binding": {},
  "successor_dependency_model_binding": {},
  "transition_dependency_carrier_binding": {},
  "transition_rule_binding": {},
  "initiating_relation_change": {},
  "affected_transition_closure": {},
  "inspected_frontier": {},
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

The structural requirement is that no correctness or cost claim exists independently of its run, state, event, dependency transition, affected structure, verifier, and produced artifact.

---

## 21. Verification Axes

Distinct verification questions must remain separate.

### 21.1 Relation-change observation status

Was the initiating change derived from the exact bound event and prior state?

### 21.2 Prior dependency-model binding status

Was the exact prior dependency graph bound to the run?

### 21.3 Dependency-transition validity status

Does the bound dependency delta correctly derive the candidate-successor graph from the prior graph?

### 21.4 Transition-carrier binding status

Does the carrier preserve the prior-only, successor-only, and unchanged dependencies required for propagation and invalidation?

### 21.5 Propagation-route verification status

Can the individual propagation routes inside the affected closure be reconstructed?

### 21.6 Affected-edge semantic status

Does every dependency record included in \(L_t^A\) satisfy the bound semantic relevance predicate independently of traversal order?

### 21.7 Affected-closure soundness status

Does every node, dependency record, and state target included in the affected structure have a valid relation to an initiating change?

### 21.8 Affected-closure completeness status

Were all transition routes capable of affecting the declared result included or explicitly resolved?

### 21.9 Frontier-accounting status

Were all dependency records inspected to establish the closure boundary recorded and included in cost accounting?

### 21.10 Materialization soundness status

Does every selected state target have a valid relation to the initiating change and affected transition closure?

### 21.11 Invariant-preservation status

Was the state outside the materialization domain shown to remain equivalent?

### 21.12 Endpoint-binding status

Are the prior and successor states bound to the exact transition record?

### 21.13 Time-order status

Was the event evaluated from the correct state and in the correct order?

### 21.14 Alternative-path closure status

Were alternative routes that could alter the result included, rejected with evidence, or left unresolved?

### 21.15 Reconstruction reproducibility status

Can an independent verifier reconstruct the same carrier, closure, materialization domain, and decision?

### 21.16 Semantic-equivalence status

Does the selective successor satisfy the declared reference semantics?

### 21.17 Cost-accounting status

Were binding, detection, graph binding, indexing, frontier inspection, propagation, verification, fallback, materialization, and commitment costs included?

These axes must not be collapsed into a single generic confidence field.

---

## 22. Candidate Artifact-Bound Gates

A future implementation may materialize the following candidate required gate set.

### Gate 1 — Prior-state binding

The computation must identify and bind the exact persistent state from which the transition begins.

### Gate 2 — Event binding

The event must be bound to the current run and prior state.

### Gate 3 — Relation-change validity

The initiating relation changes must be derivable from the event and prior state.

### Gate 4 — Dependency-transition binding

The prior dependency graph, dependency delta, candidate-successor graph, polarity-preserving carrier, and transition rules must be bound and mutually consistent.

### Gate 5 — Affected-closure soundness

Every included transition node, dependency record, and state target must have a valid route from an initiating state or dependency change.

### Gate 6 — Affected-closure completeness

All transition routes capable of changing the declared result must be included or explicitly resolved.

### Gate 7 — Frontier integrity

The dependency records inspected to determine the closure boundary must be recorded and included in the cost claim.

### Gate 8 — Invariant preservation

The region outside the materialization domain must remain equivalent under the declared semantics.

### Gate 9 — Successor equivalence

The selective successor must satisfy the complete reference semantics.

### Gate 10 — Cost integrity

The cost record must include all binding, detection, graph derivation, maintenance, frontier inspection, expansion, verification, fallback, materialization, and commitment work.

### Gate 11 — Independent replay

An independent verifier must reconstruct the transition claim from bounded artifacts.

### Gate 12 — Fail-closed decision

Missing, stale, inconsistent, incomplete, or unverifiable evidence must block the transition-bounded claim.

These are proposed research gates.

They are not a declaration that the current PULSEmech policy already implements this gate set.

---

## 23. Difference from Sparsity

Sparsity states that few elements are:

- active;
- present;
- connected;
- selected;
- non-zero.

Transition-bounded computation states:

> Only state elements made computationally eligible by an evidenced relation change and its verified transition consequences become new computation objects.

A sparse activation pattern may still include elements unrelated to the actual change.

An affected transition closure may be dense if one relation change legitimately propagates through a large connected structure.

Therefore:

\[
\text{sparse activity}
\not\Rightarrow
\text{verified transition relevance}
\]

and:

\[
\text{verified transition relevance}
\not\Rightarrow
\text{sparse affected closure}
\]

Sparsity may be an implementation property.

It is not the rule that defines computational eligibility.

---

## 24. Difference from Event-Driven Computation

Event-driven computation schedules work after an event occurs.

An event may trigger:

- a complete handler;
- a broad subsystem;
- all registered subscribers;
- a predetermined pipeline;
- an operation unrelated to the actual scope of the change.

Transition-bounded computation asks:

> Which relations became eligible for new computation because of this exact event, through which declared dependencies, and where did that eligibility end?

Event delivery alone does not establish a transition boundary.

The architecture requires event-bound relation-change, dependency-transition, and closure determination.

---

## 25. Difference from Incremental Computation

Incremental computation may:

- retain prior results;
- propagate deltas;
- track dependencies;
- invalidate affected values;
- avoid from-scratch execution.

Those mechanisms may be used by the proposed computation engine.

The PULSEmech-derived architecture adds a stricter evidentiary and authority structure:

- the initiating relation change is explicit;
- additions and removals in the dependency model are bound;
- the affected closure is an artifact;
- affected edges are defined semantically rather than by traversal history;
- the inspected frontier is recorded;
- the transition boundary is verified;
- the invariant region is part of the claim;
- selective output is compared with declared reference semantics;
- hidden global work is included in the cost claim;
- acceptance is fail-closed;
- the result is independently reconstructable.

The architecture is therefore not defined merely by reuse of prior computation.

It is defined by verified transition eligibility and an artifact-bound claim about the boundary of required computation.

---

## 26. Difference from Caching and Memoization

A cached result may be reused because a key matches or an invalidation signal was not received.

A transition-invariant result is preserved because the system establishes that no relevant transition route from the new event reaches it.

These decisions may produce the same operational result in some cases.

They make different claims.

Caching states:

> The stored result remains reusable under the cache’s validity mechanism.

Transition-bounded computation states:

> The new event did not create a verified computational obligation for this state element.

The second claim requires an explicit relation between the event, dependency transition, affected closure, and invariant boundary.

---

## 27. Difference from Neuromorphic Computation

Neuromorphic systems may use:

- spike events;
- local activation;
- asynchronous processing;
- temporal coding;
- specialized hardware;
- biologically inspired structures.

The Transition Meter does not require:

- biological analogy;
- spikes;
- specialized hardware;
- a specific clock model;
- a particular numerical representation.

Its derivation begins from:

```text
persistent relational state
  → relation and dependency change
  → affected transition closure
  → selective successor materialization
```

Neuromorphic mechanisms may provide a future substrate.

They do not define the architectural principle.

---

## 28. Worst-Case Boundary

The architecture does not assume that every transition is local.

For some event \(e_t\):

\[
|N_t^A| \approx |N_t^{\ast}|
\]

and:

\[
|M_t| \approx |\operatorname{Dom}(R_t)|
\]

A single relation or dependency change may legitimately affect the complete system.

In that case, transition-bounded computation approaches full recomputation.

The architecture does not promise universal sublinear cost.

Its claim is:

> Computation follows the verified affected transition closure, whether that closure is local or system-wide, rather than treating the complete representation as changed by default.

The benefit depends on:

- transition locality;
- dependency structure and dependency changes;
- local operator cost;
- binding and detection cost;
- graph-transition binding cost;
- closure-expansion and frontier-inspection cost;
- verification cost;
- index-maintenance cost;
- event distribution.

---

## 29. Closure Explosion and Fallback

A valid implementation must handle cases in which:

- the affected closure exceeds a configured bound;
- dependency data is incomplete;
- prior and candidate dependency graphs cannot be reconciled;
- closure construction cannot be completed or verified;
- a cyclic computation does not converge;
- event ordering is unresolved;
- concurrent changes interact;
- the invariant boundary cannot be established;
- the reference semantics cannot be verified;
- the transition becomes system-wide.

Permitted outcomes may include:

```text
LOCAL-TRANSITION-PASS
EXPANDED-TRANSITION-PASS
SYSTEM-WIDE-TRANSITION-PASS
FULL-REFERENCE-RECOMPUTE
INSUFFICIENT-DEPENDENCY-TRANSITION-EVIDENCE
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

## 30. Deletion and Negative Change

The architecture must support more than additions.

A relation or dependency may be:

- removed;
- invalidated;
- contradicted;
- disconnected;
- made unreachable;
- superseded;
- deprived of a required predecessor;
- reordered outside a valid sequence.

The absence of a formerly valid relation can open an invalidation transition.

Negative change may propagate through:

- prior-only dependency records;
- dependency loss;
- reachability loss;
- constraint violation;
- removal of derived values;
- reopening of alternative paths;
- rollback of prior conclusions.

The initiating change and dependency-delta models must therefore represent positive and negative effects.

---

## 31. Cycles and Computational Fixed Points

The affected node closure defined in Section 8 determines which nodes are transition-eligible.

A separate question arises when the values computed inside an affected cyclic region depend recursively on one another.

For acyclic dependency structures, affected nodes may be processed in topological order.

For cyclic computational structures, the architecture must declare:

- cycle membership;
- local iteration rules;
- convergence criteria;
- value-level fixed-point semantics;
- maximum iteration bounds;
- non-convergence outcomes.

Let a cyclic affected computational region use an iteration operator:

\[
Y_{n+1} = \Psi(Y_n)
\]

A successful transition requires a declared fixed point:

\[
Y^{\ast} = \Psi(Y^{\ast})
\]

or another explicitly defined and verifiable termination condition.

Failure to reach the declared value-level termination condition must not produce an accepted successor state.

The node-closure fixed point in Section 8 and the value-level fixed point in this section are distinct:

- the first determines the complete affected node set;
- the second determines the computed values of a cyclic affected region.

They must not be collapsed into one status.

---

## 32. Concurrency and Time Order

For concurrent events \(e_a\) and \(e_b\), let:

\[
R_a =
T
\bigl(
R_t,
e_a,
G_t^-,
G_{a|t}^+,
A_{a|t},
M_{a|t}
\bigr)
\]

and:

\[
R_{ab} =
T
\bigl(
R_a,
e_b,
G_{a}^-,
G_{b|a}^+,
A_{b|a},
M_{b|a}
\bigr)
\]

Likewise, let:

\[
R_b =
T
\bigl(
R_t,
e_b,
G_t^-,
G_{b|t}^+,
A_{b|t},
M_{b|t}
\bigr)
\]

and:

\[
R_{ba} =
T
\bigl(
R_b,
e_a,
G_b^-,
G_{a|b}^+,
A_{a|b},
M_{a|b}
\bigr)
\]

Here each affected closure, materialization domain, and candidate-successor dependency graph is derived from the exact state and dependency graph produced by the preceding condition or event.

The following cannot be assumed:

\[
R_{ab} = R_{ba}
\]

The architecture must determine whether the transitions:

- commute;
- conflict;
- share an affected closure;
- produce a combined closure;
- require serialization;
- require rollback;
- require reconstruction from a common prior state.

A transition record must preserve sufficient ordering evidence to establish the exact state and dependency graph from which every initiating change was evaluated.

Time order is part of the computation semantics.

It is not merely execution metadata.

---

## 33. Approximate and Learned Systems

For probabilistic, approximate, or learned systems, exact successor equality may not be available.

The architecture still requires a declared verification target.

This may include:

- predefined numerical tolerance;
- output-distribution distance;
- semantic label equivalence;
- bounded approximation error;
- stability conditions;
- uncertainty propagation;
- path-local approximation rules;
- conditions requiring broader recomputation.

The declaration must be bound before execution.

Approximation does not remove the need to define:

- the prior and candidate dependency models;
- the dependency transition;
- the affected closure;
- the inspected frontier;
- the invariant claim;
- the verification procedure;
- the cost record;
- the failure condition.

---

## 34. Initial Theorem Target

The first formal result should use a deterministic acyclic relational computation graph with no event-induced dependency-graph change.

Let:

\[
G = (N,L)
\]

be a finite directed acyclic dependency graph.

For this initial theorem target, assume:

\[
\Delta_t^G = \varnothing
\]

and therefore:

\[
G_t^- = G_t^+ = G
\]

Let every computational node \(v \in N\) implement a deterministic local function \(f_v\) whose inputs consist only of:

- outputs of predecessor nodes declared by \(G\);
- local inputs explicitly bound to \(v\).

Let \(\Delta_t^{(0)}\) be the complete set of directly observed primitive changes introduced by event \(e_t\).

Let:

\[
S_t =
\operatorname{Seed}
\bigl(
\Delta_t^{(0)}
\bigr)
\subseteq N
\]

be the complete set of graph nodes whose local inputs or source values are directly affected by the initiating relation changes.

Let:

\[
A_t = (N_t^A,L_t^A)
\]

be the descendant closure subgraph of \(S_t\) under \(G\), including \(S_t\), with \(L_t^A\) containing every dependency edge between affected nodes that is semantically capable of contributing to an affected node value.

Let \(Q_t\) contain every outgoing dependency edge inspected while establishing the descendant closure and its boundary.

Let \(M_t\) contain the persistent state outputs produced by nodes in \(N_t^A\), together with every insertion, deletion, or invalidation target directly represented by \(\Delta_t^{(0)}\).

Assume that:

1. \(R_t\) is a semantically valid complete evaluation of \(G\) under the bound input state preceding \(e_t\);
2. every primitive change introduced by \(e_t\) is represented in \(\Delta_t^{(0)}\) and mapped into \(S_t\);
3. local inputs of nodes outside \(S_t\) are unchanged by \(e_t\);
4. every node output depends only on predecessor outputs and bound local inputs declared by \(G\);
5. every local node function is deterministic and free of undeclared side effects;
6. \(G\) contains every dependency capable of affecting the declared successor outputs;
7. nodes in \(N_t^A\) are reevaluated in a valid topological order;
8. state elements outside \(M_t\) retain their prior values.

A candidate theorem is:

> Under these assumptions, reevaluating only the nodes in \(N_t^A\), applying every direct insertion, deletion, and invalidation represented in \(\Delta_t^{(0)}\), and preserving state elements outside \(M_t\) produces the same successor state as complete reevaluation of \(G\) under the post-event input state.

Formally:

\[
T(R_t,e_t,G,G,A_t,M_t) =
F(R_t,e_t,G)
\]

and:

\[
R_{t+1}|_{I_t} \equiv R_t|_{I_t}
\]

The transition-work target for change projection, frontier inspection, affected-subgraph construction, and affected-node evaluation is:

\[
O\left(
|\Delta_t^{(0)}|
+
|N_t^A|
+
|Q_t|
+
\sum_{v \in N_t^A} C_v
\right)
\]

No required event binding, change detection, index maintenance, boundary verification, independent verification, fallback, or commitment cost may be excluded from the complete measured result.

---

## 35. Initial Experimental Program

### Experiment 1 — Exact acyclic relational graph

Use a deterministic directed acyclic graph with explicit reverse dependencies.

Objectives:

- detect exact initiating changes;
- construct the affected descendant closure;
- record accepted affected edges and rejected frontier edges separately;
- selectively recompute affected nodes;
- compare byte-identical output with complete reevaluation;
- record the invariant domain;
- account for all costs.

### Experiment 2 — Branching and merging paths

Use a graph in which one change opens several paths that later merge.

Objectives:

- distinguish a single traversal route from the complete semantically affected subgraph;
- verify affected-closure soundness;
- verify affected-closure completeness;
- include every result-relevant merge dependency independently of traversal order;
- prevent duplicate materialization.

### Experiment 3 — Dependency addition

Add a dependency that opens a previously unavailable propagation route.

Objectives:

- verify successor-only dependency polarity;
- include newly reachable descendants;
- compare selective and complete successor states.

### Experiment 4 — Dependency deletion

Remove a dependency required by downstream results.

Objectives:

- preserve the removed dependency as prior-only transition evidence;
- propagate invalidation through former dependents;
- prevent false invariance under the candidate-successor graph alone.

### Experiment 5 — Relation deletion

Remove a relation required by multiple downstream results.

Objectives:

- measure negative propagation;
- verify invalidation;
- preserve unaffected branches;
- record removed and unreachable targets.

### Experiment 6 — Cyclic relational graph

Introduce cycles and declared value-level fixed-point semantics.

Objectives:

- distinguish node-closure determination from value convergence;
- define bounded iteration;
- establish convergence;
- record iteration cost;
- fail closed on unresolved computation.

### Experiment 7 — Concurrent events

Apply commuting and conflicting event pairs.

Objectives:

- verify ordering;
- bind each event to the exact state and dependency graph it observes;
- identify shared affected regions;
- compare serialized and combined execution;
- detect invalid event-state bindings.

### Experiment 8 — Incomplete dependency model

Intentionally remove a relevant edge from both bound dependency models.

Objectives:

- demonstrate false invariance;
- test dependency-model verification;
- confirm that incomplete evidence blocks the transition-bounded claim.

### Experiment 9 — Learned component boundary

Place a learned component behind a deterministic relational dependency boundary.

Objectives:

- determine whether invocation can be made transition-eligible;
- distinguish transition relevance from sparse activation;
- define an approximate reference criterion;
- identify hidden full-model work.

### Experiment 10 — Hidden-cost and frontier audit

Instrument:

- event binding;
- change detection;
- dependency-graph derivation;
- dependency lookups;
- index maintenance;
- accepted affected edges;
- rejected frontier edges;
- closure traversal;
- materialization;
- invariant-boundary verification;
- independent verification;
- fallback;
- commitment.

Objectives:

- prevent local writes from concealing global reads;
- prevent a small accepted edge set from concealing a large inspected frontier;
- determine the real cost function;
- identify workloads under which the architecture produces a net benefit.

---

## 36. Artifact-Bound Experimental Chain

Each experimental claim should bind:

```text
current run
  → implementation artifact
  → prior-state artifact
  → event artifact
  → relation model
  → prior dependency model
  → dependency delta
  → candidate-successor dependency model
  → polarity-preserving dependency carrier
  → transition rules
  → initiating change
  → affected transition closure
  → inspected frontier
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

- the total representation;
- the exact prior state;
- the exact event;
- the initiating relation and dependency changes;
- the prior and candidate dependency graphs;
- the affected closure;
- the semantic basis for affected-edge membership;
- the inspected frontier and rejected dependency records;
- the reason propagation stopped;
- the materialized state domain;
- the candidate invariant domain;
- the reference result;
- whether hidden global work occurred;
- whether fallback occurred;
- which costs were included;
- which verifier accepted the claim.

---

## 37. Primary Research Questions

1. Can initiating relation changes be detected without complete state scanning?
2. Can event binding avoid mandatory complete-state inspection?
3. Which persistent representations support stable and efficient relation identity?
4. How should prior and candidate-successor dependency graphs be bound when dependencies change?
5. Which dependency carriers preserve both newly opened and removed effect routes?
6. Which dependency structures permit exact affected-closure traversal?
7. Can affected-closure completeness be established at lower cost than complete reevaluation?
8. How can the dependency model itself be verified as adequate for a declared output?
9. How can an invariant region be committed without rereading the complete state?
10. How should rejected frontier edges be recorded and costed?
11. What classes of systems exhibit stable transition locality?
12. When does dependency-index maintenance exceed the computation it avoids?
13. How should closure explosion be detected and represented?
14. How should cyclic computational regions be bounded and verified?
15. How should concurrent transitions be merged, serialized, or blocked?
16. Can learned components expose reliable transition boundaries?
17. Which equivalence claims remain valid for approximate computation?
18. Can earlier transition records serve as reusable evidence for later events?
19. What machine model best expresses transition-bounded complexity?

---

## 38. Falsification Conditions

The research hypothesis is unsupported for a tested system if one or more of the following remain true:

- event binding requires unreported complete-state scanning;
- initiating change detection requires unreported complete-state scanning;
- the affected closure cannot be determined without complete recomputation;
- added dependencies are omitted from propagation;
- removed dependencies are omitted from invalidation propagation;
- affected-edge membership depends on traversal order rather than bound semantics;
- rejected frontier edges are excluded from the expansion-cost record;
- the dependency model omits relevant effects;
- the invariant boundary is assumed rather than established;
- selective materialization fails the declared reference semantics;
- hidden global operations are excluded from the cost record;
- dependency maintenance dominates avoided computation under representative workloads;
- the transition claim cannot be independently reconstructed;
- stale or incorrectly ordered events can produce accepted states;
- unresolved closure is accepted instead of failing closed;
- non-convergent cyclic computation produces an accepted successor;
- a full fallback is reported as local computation;
- the claimed locality disappears under representative events.

These conditions test the central hypothesis directly.

They are not secondary implementation defects.

---

## 39. Strong Form of the Hypothesis

A strong form of the research hypothesis is:

> Given a persistent relational state, an event-bound relation-change detector, bound prior and candidate-successor dependency graphs, a verified dependency delta, a polarity-preserving transition-dependency carrier, a sound and complete affected transition closure, a fully recorded inspected frontier, and an independently verifiable invariant boundary, a successor state can be selectively materialized with semantic equivalence to complete reevaluation while making the affected-region work a function of the verified transition closure and the actual frontier inspected to establish it.

Formally:

\[
T(R_t,e_t,G_t^-,G_t^+,A_t,M_t)
\equiv
F(R_t,e_t,G_t^-)
\]

The complete measured transition cost remains:

\[
C_t =
C_{\mathrm{bind},t}
+
C_{\mathrm{detect},t}
+
C_{\mathrm{graph\mbox{-}bind},t}
+
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t}
+
C_{\mathrm{boundary},t}
+
C_{\mathrm{verify},t}
+
C_{\mathrm{fallback},t}
+
C_{\mathrm{commit},t}
\]

where \(C_{\mathrm{fallback},t}=0\) only when no broader evaluation or full reference recomputation is executed. Otherwise it contains the complete actual fallback cost.

The affected-region target remains:

\[
C_{\mathrm{expand},t}
+
C_{\mathrm{materialize},t} =
f\left(
|\Delta_t^{(0)}|,
|\Delta_t^G|,
|N_t^A|,
|Q_t|,
\sum_{v \in N_t^A} C_v
\right)
\]

A total-cost claim that is independent of the complete prior-state domain additionally requires evidence that:

\[
C_{\mathrm{bind},t}
+
C_{\mathrm{detect},t}
+
C_{\mathrm{graph\mbox{-}bind},t}
+
C_{\mathrm{boundary},t}
+
C_{\mathrm{verify},t}
+
C_{\mathrm{fallback},t}
+
C_{\mathrm{commit},t}
\]

does not conceal mandatory state-wide or graph-wide work.

The complete amortized per-transition result is:

\[
\widehat{C}_t =
C_{\mathrm{index\mbox{-}maintenance},t}
+
C_t
\]

Therefore, independence from the complete prior-state or dependency-graph size also requires evidence that index maintenance does not conceal mandatory state-wide or graph-wide work. If fallback executes, its actual cost remains inside \(C_{\mathrm{fallback},t}\); a full-reference fallback may support successor correctness but must not be reported as a local transition-cost result.

If any binding, detection, graph-binding, boundary, verification, fallback, commitment, or index-maintenance stage scans or rebuilds the complete state or dependency structure, that cost must be reported explicitly and the result must not be described as total transition-bounded computation.

This statement is conditional.

Its purpose is to expose the conditions that must be implemented, measured, and verified.

---

## 40. PULSEmech-Specific Contribution

The proposed architecture does not claim that dependency tracking, delta propagation, selective recomputation, or persistent state are individually new.

The PULSEmech-specific contribution is the structure:

```text
observed relation and dependency change
  → transition eligibility
  → verified affected closure
  → verified invariant boundary
  → bounded materialization
  → artifact-bound authority decision
```

Its defining properties are:

1. **Transition eligibility**  
   New computation requires a valid relation to the initiating change.

2. **Dependency-transition binding**  
   Prior and candidate-successor dependency structures and their delta are part of the transition object.

3. **Explicit affected closure**  
   The complete transition-relevant subgraph becomes a first-class artifact.

4. **Semantic affected-edge identity**  
   Edge membership follows the bound propagation semantics, not incidental traversal order.

5. **Explicit frontier record**  
   Rejected candidate dependencies remain visible as work required to establish the boundary.

6. **Negative boundary claim**  
   The system records not only what became affected, but why the remaining state did not.

7. **Semantic reference binding**  
   The selective successor is evaluated against declared complete semantics.

8. **Complete cost binding**  
   Binding, detection, graph transition, maintenance, frontier inspection, propagation, verification, fallback, and commitment are included.

9. **Independent reconstruction**  
   The producer’s claim is not accepted without independent verification.

10. **Fail-closed authority**  
    An unresolved boundary blocks the transition-bounded claim.

This is more than a scheduling or optimization policy.

It is a computational authority model in which a relation or dependency change creates a bounded and verifiable obligation to compute.

---

## 41. Technical Assessment

The strongest architectural move is the change in computational object.

The system does not begin by assuming that every new event requires another pass over the complete representation.

It first asks which relations became computationally eligible.

The decisive technical problem is the invariant boundary.

Selective recomputation is insufficient by itself.

The architecture must establish that:

- the initiating relation and dependency changes were correctly identified;
- the prior and candidate dependency graphs were correctly related;
- the transition carrier preserved both newly opened and removed effect routes;
- the affected closure was sound;
- the affected closure was complete;
- affected-edge membership was semantic rather than traversal-dependent;
- the inspected frontier was recorded and costed;
- the omitted state could not alter the declared result;
- the successor remained equivalent to the reference semantics;
- the measured cost did not conceal global work.

If these properties can be made bounded, artifact-addressable, and independently verifiable, the result is not merely a faster implementation of the same state-wide computational assumption.

The primary unit of new work becomes the evidenced transition.

---

## 42. Development Boundary

This document defines a foundational architecture, formalization target, and experimental program.

It does not claim that the current PULSEmech repository already implements:

- a persistent relational computation runtime;
- a relation-change detector;
- dependency-transition binding;
- a polarity-preserving dependency carrier;
- a transition-closure engine;
- dependency-model completeness verification;
- invariant-boundary proofs;
- selective successor materialization;
- a production transition-compute gate set.

The existing PULSEmech program provides the artifact-bound authority mechanics through which future implementations and experiments can be:

- bound to their current runs;
- independently verified;
- replayed;
- measured;
- accepted;
- or blocked.

The computation research lane must not alter or weaken the existing release-authority boundary.

Its implementation claims must enter that boundary as evidence-bearing subjects.

---

## 43. Architectural Summary

The proposed model is:

```text
persistent relational state
  → bind the event to the exact prior state
  → detect initiating relation changes
  → bind prior dependency graph
  → bind dependency delta and candidate-successor graph
  → construct the polarity-preserving transition carrier
  → traverse declared transition semantics
  → record the affected transition closure
  → record the inspected frontier
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

> The computation of a persistent intelligent system may be organized around evidence-bound transitions, with computational work determined by the verified affected transition closure and the actual boundary work required to establish it rather than by mandatory repeated processing of the complete representation.

If established, this would not merely accelerate the same computation.

It would change what the system recognizes as requiring computation.
