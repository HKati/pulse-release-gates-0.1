# PULSEmech / Paradoxon Diagram

## Mechanical definition contract v0.2 — initial development

### M1–M3: structural impact, persistence conditions and evidence applicability

**Date:** 2026-10-22  
**Document role:** research contract candidate, with derivations and hand-worked reference cases  
**Starting point:** the v0.1 mechanical analysis, the v0.2 research plan and its five review clarifications  
**Source basis:** `HKati/pulse-release-gates-0.1`, the previously selected snapshot `bb3c4791bc9399d0085d10d0d29d6d8a5e2cbfca`; not an assessment of the current `main` implementation state  
**Authority effect:** `none`  
**Execution state:** no implementation or experimental execution; no machine-checked theorem proving

```text
document_status: research_contract_candidate
implementation_status: not_implemented
software_test_status: NOT_RUN
machine_checked_proofs: not_performed
authority_effect: none
```

> This document develops the mathematics of the plan's first unit. Its definitions are candidates; its theorems follow from their stated assumptions. It does not claim that the new representation is already a verified model of the complete Paradoxon mechanics, and it grants no execution permission.

**Repository edition:** English translation of `PULSEmech_Paradoxon_M1_M3_definicios_szerzodes_v0_2.md`. The mathematical content, equations, theorem identifiers, reference cases and claim boundaries are retained. The Hungarian workshop source has SHA-256 `831d72685739571c11d672e364f591e04442e721b0912efaf394c7165131e24e`. This edition adds publication-status metadata and repository-facing wording; it does not promote the research into implementation or authority.

## 0. Result and claim boundary

This initial development provides three connected contracts.

**M1:** structural impact is examined through an answer structure bound to a common configuration. Identical individual possibilities must not conceal differences in joint conditions. The comparison separately handles permitted renaming, protected identities and changes in the pairing between variants.

**M2:** changes in condition satisfaction, configuration-dependent obligations and the meaning of a condition are distinguished. A fixed predicate can express configuration-dependent persistence conditions. The declared policy does not become model data that the candidate may rewrite.

**M3:** the proof record carries a checkable derivation, precise semantics and applicability bindings. Conjunctive and alternative evidence support are preserved. Mutual references must not generate their own justification; loss of one piece of evidence must not automatically remove an alternative justification.

The development also clarifies the scope of the isolation claim and provides hand-worked analyses of the K01–K10 reference cases. These are not executed software tests.

The following status markers are used:

| Marker | Meaning |
|---|---|
| D | A concept or boundary documented in the named source; not automatically a general scientific proof. |
| J | A definition or contract proposed in this document. |
| T | A mathematical derivation given here under explicit assumptions. |
| H | An open research hypothesis or mapping obligation. |

The T marker does not imply Lean checking, program execution or independent external acceptance.

## 1. Documented foundation and the mapping obligation

In the pinned glossary, an Anchor is a reference frame; an Atom is an auditable, evidence-bound unit; an Edge in v0 is an association; Orientation is an Anchor-relative reading; and Core is a substructure that preserves orientation and reviewer interpretation. None of these automatically establishes causality, temporal order or complete impact coverage. [S1]

| Documented foundation | Use in this candidate | Connection still to be established |
|---|---|---|
| Anchor | Fixes the examination context and comparison rules. | The selected context covers the relevant mechanical distinctions. |
| Atom | An identified, typed element that can be bound to evidence. | The examples' elements map to actual Paradoxon data. |
| Edge | Retains its existing association semantics. | Every new condition, support or impact relation has its own semantics. |
| Orientation | A reading under the named Anchor. | It is not used as a time direction or causal proof. |
| Core | The existing reviewer projection. | Its sufficiency must be proved separately for a new impact claim. |

Higher-arity relations, the joint answer structure and proof closure are new proposals. Renaming existing association edges does not establish them.

Capability states remain separate: source-documented meaning; the present mathematical candidate; later implementation; actual execution evidence; and authority integration. There is no silent promotion between them.

## 2. The first finite profile: F0 [J]

### 2.1. What is selected here?

F0 consists of the MON-0 example in Section 5.3, the K01–K10 cases in Section 10 and their explicitly named variants. Each case has its own fully specified finite domain. This is not the class of all relational systems below some size bound, nor a complete space of physical possibilities.

The central binary examples use `D = {0,1}`. A three-variable example starts from the complete domain `D³`, containing eight valuations. The monitoring example has three binary variables. The identity examples enumerate their elements explicitly. The proof examples use a finite set of statements and a finite set of positive inference rules.

The following contract must be recorded for every case:

| Profile component | Required content |
|---|---|
| Subject and types | Which elements, roles, relations and value domains are present in the model? |
| Semantics | The meaning of relations and conditions, not merely their names. |
| Context | Anchor, system boundary and environmental conditions held fixed in the comparison. |
| Identity | Which names may be changed; which identities are protected? |
| Variants | The partial descriptions being examined and the exact subject of the modification. |
| Questions | Which individual and joint distinctions must be preserved? |
| Reference | Separately specified equations, case enumeration or derivation. |
| Claim boundary | Separation of a model result, actual-system binding and an execution claim. |

### 2.2. Explicit mathematical assumptions

Classical two-valued set-based logic is selected as an examination tool for complete F0 configurations. Partial knowledge is represented by multiple compatible configurations; justification is handled by a separate assessment state. A two-valued complete configuration is not a claim that all reality or all Paradoxon mechanics is two-valued.

The finite carriers, evaluable conditions and named questions are restrictive choices. A relevant case that cannot be represented without loss in this profile requires an extension or an applicability limit; it must not be silently transformed into a suitable case.

Operational relations may be mutual and cyclic. The first proof-support subprofile uses positive rules with finite premise sets. This is a limit of the proof instrument, not a prohibition on mechanical mutuality. Coinductive proof is not excluded in general, but F0 justification closure does not replace its separate soundness contract.

No global time, event sequence, probability, temporal transition operator or causal graph is assumed as a foundation. Variant indices and derivation levels are not time coordinates.

### 2.3. Three different kinds of completeness

**Example completeness:** the case analysis covers every valuation of one concrete finite example.

**Profile-method completeness:** the method preserves the required property for every input in the selected class. This requires a general proof or justified coverage of the complete class.

**Actual-system coverage:** the relevant real possibilities have counterparts in the model. The hand-worked examples do not establish this.

This document gives complete hand derivations for several examples and several conditional general theorems. Fidelity to the complete Paradoxon mechanics and actual-system coverage remain open.

## 3. Shared notation and comparability [J]

The v0.1 configuration candidate is retained:

$$
C=(A,R,\iota,\nu).
$$

The semantic environment is separately denoted by $\theta$: types, value domains, relation interpretations and definitions. The Anchor $\alpha$ binds the examination context. The selected configuration family is $\mathcal C_{\alpha,\theta}$.

The compatible completions of a partial description are:

$$
\Omega^{\lambda}
=\Omega_{\alpha,\theta}(B^{\lambda})
=\{C\in\mathcal C_{\alpha,\theta}:C\models_{\theta}B^{\lambda}\}.
$$

The requirement to be preserved is not used in advance to filter out every violating configuration. Structural possibilities and the desired requirement are separate objects.

### 3.1. Identity contract

The correspondence $J$ binds the entire comparison. It is type-correct and identifies roles that remain, are added, disappear or are replaced. A missing element may have a predefined `absent` value; this is not the same as unknown identity or missing observation.

A permitted renaming uses the same mapping for elements, relation arguments, questions and associated references. A separate renaming must not be chosen for each question merely to hide its difference.

Protected identities — for example, a specific artifact, run occurrence, verifier, target and evidence carrier — must not become interchangeable merely because graphs look alike. A digest is a binding datum; by itself it does not establish content correctness or producer trustworthiness.

### 3.2. Changes in semantics

The same symbol with a different meaning is not the same question. If $\theta_u\ne\theta_v$, a separate meaning-preserving translation contract is required. Without it, neither structural identity nor a precise semantic impact may be claimed. The fact that meaning has changed may be recorded, but the comparison remains unresolved.

An empty $\Omega^\lambda$ is a separate inconsistency result. Equality of empty sets must not produce a result asserting valid operation.

## 4. M1 — Structural impact

### 4.1. Joint answer structure [J]

Let the finite question profile be:

$$
\mathcal Q=\{q_1,\ldots,q_m\}.
$$

Question values may be logical values, typed role bindings, condition tables or finite relational structures. They need not be collapsed into a single number.

After meaning and identity alignment, each question has a common value domain $D_i$. Define:

$$
\Phi^\lambda_{\Pi,J}(C)
=(q_1^\lambda(C),\ldots,q_m^\lambda(C)),
$$

$$
\mathcal A^\lambda_{\Pi,J}
=\{\Phi^\lambda_{\Pi,J}(C):C\in\Omega^\lambda\}.
$$

Every entry of the vector comes from the same configuration. The coordinate listing is a data organization, not a temporal order.

The profile may carry role bindings, joint admissibility, conditions, support and obligations as separate questions. Their common-configuration binding is nevertheless preserved.

**Structural difference in the space of possibilities:** for appropriately comparable, nonempty variants,

$$
\mathcal A^u_{\Pi,J}\ne\mathcal A^v_{\Pi,J}.
$$

The directed differences are:

$$
D^-_{u,v}=\mathcal A^u_{\Pi,J}\setminus\mathcal A^v_{\Pi,J},
\qquad
D^+_{u,v}=\mathcal A^v_{\Pi,J}\setminus\mathcal A^u_{\Pi,J}.
$$

Minus and plus denote the direction of comparison, not event time or causal direction.

### 4.2. T1 — Separate answer sets are insufficient [T]

Let

$$
S^u=\{(0,0),(1,1)\},\qquad
S^v=\{(0,1),(1,0)\}.
$$

The projection onto either coordinate is $\{0,1\}$ in both variants. The joint sets differ: $(0,0)\in S^u$, but $(0,0)\notin S^v$. Therefore, equality of the separate answer sets does not imply equality of the joint answer structure. The distinction is fully established because every member of both finite sets is specified.

### 4.3. T2 — Exactly what does the joint answer structure preserve? [T]

For two comparable variants in the same value space $D=D_1\times\cdots\times D_m$,

$$
\mathcal A^u=\mathcal A^v
$$

if and only if, for every predicate $h:D\to\{0,1\}$, the two variants agree on whether there exists an admissible answer vector satisfying $h$.

**Proof.** An existential statement has the same result on equal sets. If the sets differ, choose an element $a$ in their symmetric difference and define $h_a(x)=1$ exactly when $x=a$. One variant then has a witness and the other does not. For nonempty sets, preservation of all corresponding universal properties follows as well. □

**Limit:** the theorem concerns properties of the data preserved by $\Phi$. It does not state that $\Phi$ contains every mechanically relevant datum.

If the selected relevance equivalence is $\approx_\Pi$, full discrimination fidelity is a separate obligation:

$$
\Phi(C)=\Phi(C')\quad\Longleftrightarrow\quad C\approx_\Pi C'.
$$

The two-way condition excludes both loss of a relevant distinction and a spurious distinction caused by permitted renaming. Relevance equivalence must not be defined retrospectively as nothing more than equality of $\Phi$; that would make the fidelity claim circular.

### 4.4. Variant pairing is a separate object [J/T]

The pairing between variants may change even when their possible answers are identical. If the candidate asserts such a correspondence, let:

$$
\mathcal M_{uv}\subseteq\Omega^u\times\Omega^v.
$$

This is a justified configuration pairing, not a default temporal transition. It must not automatically be chosen as the entire Cartesian product.

The profile-bound paired structure is:

$$
\mathcal D_{\Pi,J}(\mathcal M_{uv})
=\{(\Phi^u(C),\Phi^v(C')):(C,C')\in\mathcal M_{uv}\}.
$$

Example: both variants have possibilities $\{0,1\}$. The identity pairing is $\{(0,0),(1,1)\}$, while the swapping pairing is $\{(0,1),(1,0)\}$. The possibility sets on the two sides are equal; the paired structures are not.

**Consequence:** $\mathcal A^u=\mathcal A^v$ is equality of possibility spaces, not a general proof that a particular candidate modification has no effect. If the requirement is paired preservation, it must be proved for every relevant pair whose coverage is justified. A critical case omitted from the pairing must not disappear from the assessment.

### 4.5. The boundary beyond relationships among questions

Neither the joint answer vector nor the paired structure is a universal completeness solution. If joint compatibility of multiple configurations, a relation between configuration families or another higher-level property is relevant, it needs its own carrier and preservation obligation. F0 does not claim completeness without such data.

### 4.6. M1 result contract

Every comparison must preserve profile identity, semantics, the global correspondence $J$, nonemptiness, the joint answer structure, any required pairing relation, the distinguishing witness or identity proof, and the coverage boundary.

An identical subprofile does not establish complete absence of impact. An incomparable or incomplete critical part must not receive a verified-identity result.

## 5. M2 — Persistence conditions and mutual conditional impact

### 5.1. Clarifying the v0.1 predicate [J]

The fixed form $K_r(C)$ is not inherently too narrow. The configuration may contain the relationships, roles and parameters relevant to persistence. Thus, not every configuration-dependent change requires new $K_r^\lambda$ semantics.

A condition may be represented by the descriptive object:

$$
k=\langle id,\ semantic\_ref,\ scope,\ roles,\ body\rangle.
$$

In F0, `body` is a declared relational condition or truth table, not arbitrary executable code. The meaning of evaluation $\operatorname{Eval}_\theta(k,C)$ belongs to the fixed semantics. Once the condition bound to the examined configuration is selected:

$$
K_r(C)=\operatorname{Eval}_\theta(\operatorname{cond}(r,C),C).
$$

Condition data in a configuration may change, but may not rewrite their own checking semantics or the protected policy. For mutual operational conditions, joint satisfiability is examined; conditions are not required to be evaluable in a pre-existing event order.

### 5.2. Four changes to distinguish

| Change | Meaning | Required check |
|---|---|---|
| Change in satisfaction | The same condition receives a different evaluation. | Binding of the affected configurations and evidence. |
| Configuration-dependent instantiation | The same rule applies to different roles or elements. | Completeness of the obligation domain, for example for a new delegated executor. |
| Change in a condition description or its semantics | The previous mechanical description is corrected, extended or given a different meaning. | Meaning alignment, the limits of the original description and proof transfer. |
| Policy change | The prescribed protective requirement itself changes. | Separate authorization; not the candidate's automatic correction. |

These four distinctions are not four a priori separate physical mechanisms. They check what was changed and which claim the evidence permits.

### 5.3. Fixed requirement, new obligation — MON-0 [J/T]

Consider a primary executor and a possible delegated executor. The variables are:

- $d$: the delegated executor can perform a protected operation according to the model;
- $m_p$: the primary executor has the required monitoring binding;
- $m_d$: the delegated executor has the required monitoring binding.

All three variables are binary. The primary executor's presence and useful operation are held fixed in this example. The mandatory protective statement is:

$$
I(C)=m_p\land(\neg d\lor m_d).
$$

The complete domain is $\{0,1\}^3$, with coordinate order $(d,m_p,m_d)$.

The initial description is:

$$
\Omega^u=\{(0,1,0),(0,1,1)\}.
$$

Both members satisfy $I$. Admitting delegated operation without establishing its monitoring gives:

$$
\Omega^v=\{(1,1,0),(1,1,1)\}.
$$

Configuration $(1,1,0)$ is a violating witness. The appropriately restricted candidate

$$
\Omega^a=\{(1,1,1)\}
$$

satisfies $I$.

**Derived finding:** the meaning of the invariant has not changed. Applicability of the delegated role has opened a new, concrete proof obligation. Simply replacing $I$ by $m_p$ would weaken the protective statement rather than repair the violation.

These are analytic model claims. The actual interpretation of $d$, $m_p$ and $m_d$ requires separate bindings for capabilities, monitoring events, identities and the treatment of missing paths. This example is not an executed monitoring pilot.

### 5.4. Conditional completion family [J]

Let $q_r$ describe the relevant persistence or applicability of one relation, let $q_S$ describe the joint conditions of other relations, and let $z$ denote the fixed environmental boundary data. Define:

$$
\mathcal F^\lambda_{r\mid S,z}(\eta)
=
\{q_r(C):C\in\Omega^\lambda,\ q_S(C)=\eta,\ q_z(C)=z\}.
$$

This gives the $r$-possibilities that remain compatible under the specified joint condition. The value $\eta$ is not a time point, and fixing a condition is not a claim of a physically executed intervention.

The domain of admissible $\eta$ values is also part of the conditional structure. The disappearance of a previously possible condition configuration must not be hidden by omitting its empty subset from the representation.

### 5.5. Direct, indirect and mutual meanings [J]

**Direct impact relative to a primitive:** a distinguishing conditional difference is justified by the semantics of one selected primitive relation and its stated environment.

**Composite impact:** the difference follows from the joint conditions of several relations. The composition must be jointly compatible; individually possible steps do not imply the existence of one common witness.

**Mutual conditional sensitivity:** there are comparable, nonempty conditional families in which a variant of the condition on $s$ distinguishes the possibilities of $r$, and a separate witness establishes the reverse direction. This is relational conditional sensitivity, not automatically a causal interaction.

Example:

$$
S=\{(0,0),(1,1)\}.
$$

Under $s=0$, $r=0$; under $s=1$, $r=1$; the reverse holds as well. The structure is mutual and consistent. No first event is designated.

A differing shared environment, differing meaning or incomplete conditional coverage rules out an unconditional impact claim. A graph direction without evidence does not replace these obligations.

### 5.6. Preservation and refutation

Requirement preservation by a variant is:

$$
\Omega^\lambda\ne\varnothing
\quad\land\quad
\forall C\in\Omega^\lambda:I(C).
$$

A violating witness in the model is:

$$
C_*\in\Omega^\lambda
\quad\land\quad
\neg I(C_*).
$$

The latter statement does not automatically become an actual violation if the model is an over-approximation and realizability of $C_*$ has not been established. Model soundness and applicability to the actual system are separate proof tasks; the author's background material on abstract interpretation also emphasizes this distinction. [S6]

Useful operation is a separate predicate $U(C)$. Achieving protection by eliminating all operations is insufficient when the policy also requires $U$.

## 6. M3 — Evidence record, reuse and justification closure

### 6.1. The proof record [J]

The candidate record is:

$$
\mathsf P=
\langle\varphi,\Gamma,\pi,E,\theta,V,\mathcal S,\beta\rangle.
$$

| Component | Required meaning |
|---|---|
| $\varphi$ | A precise statement, including types and definitions. |
| $\Gamma$ | Assumptions, conditions and accepted axioms actually used in the derivation. |
| $\pi$ | A checkable derivation or certificate, not merely a producer assertion. |
| $E$ | Referenced evidence carriers and relevant provenance or measurement data. |
| $\theta$ | The semantic environment that determines meaning. |
| $V$ | Checking rules and verifier identity. |
| $\mathcal S$ | Applicability domain and conditions. |
| $\beta$ | Subject, artifact, run, environment and target bindings where required. |

This record is not a renaming of an existing PULSEmech schema. Before implementation, semantically suitable existing fields must be reused; a new name must not create new authority.

Checking $\Gamma\vdash_{\theta,V}^{\pi}\varphi$ establishes a conditional mathematical statement. Current application separately requires the relevant assumptions and $\beta$ bindings to be established. Acceptance by a proof checker is not the same as correctness of the intended meaning of the statement; the official Lean validation guide explicitly distinguishes these matters. [S4]

An assumption inventory may be conservatively complete, but must not be called minimal merely because the derivation refers to its members. An assumption can occur in one proof without being necessary for another proof.

### 6.2. T3 — Semantic transfer of a proof [T]

Let the original, established statement be:

$$
\forall C_u\in X_u:\varphi_u(C_u).
$$

Let $X_v$ be the target domain, and let $T\subseteq X_v\times X_u$ be a specified correspondence. Assume:

1. $X_v\ne\varnothing$;
2. for every $C_v\in X_v$, there exists $C_u\in X_u$ such that $T(C_v,C_u)$;
3. for every such pair, the following semantic bridge has been established:

$$
T(C_v,C_u)\Rightarrow
\bigl(\varphi_u(C_u)\Rightarrow\varphi_v(C_v)\bigr).
$$

Then:

$$
\forall C_v\in X_v:\varphi_v(C_v).
$$

**Proof.** Take an arbitrary target element. Coverage provides an original element corresponding to it. The original theorem holds for that element, and the semantic bridge transfers the property. Since the target element was arbitrary, the statement holds for every target element. Nonemptiness rules out merely vacuous satisfaction on an empty target. □

**Key point:** one suitable pair does not establish universal transfer. The semantic bridge is a substantive obligation, not a new prose label.

At certificate level, transfer may also proceed by providing, after a type-correct translation, a new justification for every assumption used by the old derivation while preserving the soundness of every inference rule used. The corresponding leaves of the proof tree can then be replaced. If these conditions do not hold, the theorem may remain true, but a different derivation is required.

### 6.3. Application to the monitoring example

Let the original assumptions be:

$$
\Gamma_u=\{m_p=1,d=0\}.
$$

They imply $I=m_p\land(\neg d\lor m_d)$. The new assumptions

$$
\Gamma_v=\{m_p=1,d=1\}
$$

do not establish the old assumption $d=0$, and valuation $m_d=0$ is a counterexample to $I$. Reusing the old proof unchanged would be incorrect.

Adding a justification of $m_d=1$ makes $I$ derivable again. This is not retrospective validation of the old $d=0$ assumption; it is a proof appropriate to the new configuration.

### 6.4. Conjunctive and alternative support [J]

Let $\mathcal X$ be a finite set of precisely typed statements. A positive support rule is:

$$
P_r\Longrightarrow c_r,
\qquad P_r\subseteq\mathcal X,\ c_r\in\mathcal X.
$$

The members of $P_r$ are required **together** to apply this rule. Separate rules with the same conclusion may provide alternative derivations. The complete rule set is denoted by $\mathcal H_\lambda$; its rules belong to the semantics and bindings valid in context $\lambda$.

Example:

$$
\{e_1,e_2\}\Longrightarrow c,
\qquad
\{e_3\}\Longrightarrow c.
$$

In this selected rule system, support has the form:

$$
(e_1\land e_2)\lor e_3.
$$

The $e_i$ denote accepted evidence statements bound to the claim, not mere file presence. The example does not define, in general, which physical measurement constitutes sufficient evidence.

A rule without premises may only be an explicitly accepted axiom, a checked logical identity or a declared base statement. It must not arise from arbitrary producer output.

### 6.5. Justification closure without temporal order [J]

Let $\mathcal B_\lambda\subseteq\mathcal X$ be the set of separately accepted base statements in the context. Define:

$$
L_\lambda=
\bigcap\left\{
S\subseteq\mathcal X:
\mathcal B_\lambda\subseteq S
\ \land\
\forall r\in\mathcal H_\lambda\,
(P_r\subseteq S\Rightarrow c_r\in S)
\right\}.
$$

This is the least set of statements containing the bases and closed under the rules. The intersection exists: $\mathcal X$ itself belongs to the family being intersected.

The definition uses set inclusion, not mechanical time. An iteration index in a later computation would be a technical derivation level; it would not imply event order or the emergence of physical time.

### 6.6. T4 — Closure has finite, grounded derivations [T]

In the positive F0 rule profile with finite premise sets, $c\in L_\lambda$ exactly when $c$ has a finite proof tree whose leaves are accepted base statements or explicitly permitted premise-free rules.

**Proof.** Let $S_0=\mathcal B_\lambda$, and let $S_{n+1}$ contain $S_n$ together with the conclusions of all rules whose premises belong to $S_n$. The sequence is increasing; since $\mathcal X$ is finite, at most $|\mathcal X|$ strict expansions can occur. The stable set is closed. By induction, every closed set containing the bases contains every $S_n$, so the stable set is $L_\lambda$. Each newly added statement obtains a finite tree from the rules used; conversely, induction on tree height places every conclusion in the closure. □

The theorem does not claim that every true mathematical or physical statement is derivable in this rule language. Absence from the closure means lack of justification in this profile, not falsity of the subject-matter claim.

### 6.7. T5 — A self-contained proof cycle is not self-justification [T]

Let $Y\subseteq\mathcal X$ be a group of statements such that:

- $Y\cap\mathcal B_\lambda=\varnothing$;
- every rule with a conclusion in $Y$ requires at least one premise in $Y$.

Then:

$$
Y\cap L_\lambda=\varnothing.
$$

**Proof.** $\mathcal X\setminus Y$ contains every base statement. No rule whose premises hold entirely within it can lead into $Y$, since that would already require a premise from $Y$. Thus $\mathcal X\setminus Y$ is closed, and the least closure is a subset of it. □

Example: $p\Rightarrow q$ and $q\Rightarrow p$, without a base statement. The closure is empty. If $p$ is a separately accepted base, the closure is $\{p,q\}$. Mechanical mutuality is permitted in both cases; the grounding of justification differs.

This is consistent with the general proof-theoretic distinction between unconditional circular self-justification and recursive or coinductive proof with explicit soundness conditions. [S5] F0 establishes a theorem only for its own positive closure profile here.

### 6.8. T6 — Why continuing from the old closure is insufficient after evidence withdrawal [T]

With the same two rules, let the original base be $\mathcal B_u=\{p\}$, giving $L_u=\{p,q\}$. If the target view has $\mathcal B_v=\varnothing$, the correct new closure is $L_v=\varnothing$.

The old set $\{p,q\}$ is nevertheless still closed under the two rules. A procedure that merely checks mutual support among old conclusions may therefore incorrectly retain them.

**Consequence:** after withdrawal of a base, or a change in a rule or binding, the least closure justified by the new bases must be restored. An incremental method may be used, but must preserve the correctness of grounded derivations; old closedness alone is insufficient.

The example compares contexts. It does not introduce global time into the mechanical model.

### 6.9. Alternatives and proof dependency [J/T]

For fixed $\mathcal H_\lambda$ and context, let $\operatorname{Cl}_{\mathcal H_\lambda}(U)$ denote the closure generated from base $U$. The family of minimal supports drawn from the accepted bases is:

$$
\mathfrak S_\lambda(c)=
\min_{\subseteq}
\{U\subseteq\mathcal B_\lambda:
 c\in\operatorname{Cl}_{\mathcal H_\lambda}(U)\}.
$$

In the finite domain, every derivable statement has such a minimal support; for a premise-free justification it may be the empty set. Minimality is relative only to the specified rules and bases, not to every conceivable proof.

In the $e_1,e_2,e_3$ example, the known supports are $\{e_1,e_2\}$ and $\{e_3\}$. Loss of $e_1$ does not remove justification of $c$ if $e_3$ remains acceptable. If only $e_2$ remains acceptable, $c$ cannot be derived from these rules.

Rule identity and its context-dependent validity are themselves dependencies that must be preserved. Under changed rules, the old support inventory must not be reused unchanged merely because the evidence files remain available.

The support family may become large; this definition does not imply a cheap or scalable search algorithm.

### 6.10. Reassessment obligation and meaning

Dependency reachability may identify **potentially affected** statements. This is a conservative worklist, not automatic refutation or total loss of proof.

The following outcomes must be handled separately for every affected statement:

| Outcome | Conclusion |
|---|---|
| Retained, bound derivation | Applicability can be established for the exact new context. |
| Alternative bound derivation | The original certificate may cease to apply while the statement remains justifiable. |
| No grounded derivation in this profile | The statement is not justified here; this is not the same as falsity. |
| Appropriately bound counterexample | The selected model claim is refuted; an actual violation requires actual-system binding. |
| Unresolved contradictory evidence | The conflict must be preserved, not resolved by an arbitrary PASS. |
| Unknown semantic or subject binding | Current applicability is unresolved. |

Carrier integrity, proof correctness, current applicability of assumptions and authority eligibility are separate claims.

The historical $\mathsf P_u$ is preserved. A new applicability assessment is a new linked record, not a rewrite of the old decision.

**Run-binding limit:** mathematical proof transfer does not turn historical measurement evidence into an observation from a new run. The pinned PULSEmech description binds behavior evidence to the run that produced it. [S3] If policy requires current-run evidence, a general lemma or old replay cannot replace it.

## 7. Present result for a shared operational–epistemic structure [J/H]

M1–M3 can distinguish operational relations, persistence conditions, statements and their support within the same typed carrier. Joint configuration discrimination and conditional completion can be defined for each, provided that types and semantics are specified.

This does not yet establish a single shared physical mechanism. In particular, the existence of an operational relationship and its justification are not the same predicate. Proof closure expresses the selected justification rules, not a law that creates the operational world.

A concrete test is now available for examining the common foundation: the same joint answer structure must expose operational, epistemic and mixed impact while preserving the distinctions between types. An operational relationship $\ell=1$ may lose justification without a claim that $\ell=0$. Conversely, subject binding or an operational condition may change while the evidence file remains unchanged.

**Result obtained:** a shared, type-preserving descriptive candidate and checkable operations.

**Open result:** does this common description imply a stronger mechanical unity, beyond data modelling alone, in the selected concrete Paradoxon application?

## 8. The exact subject of isolation — preparation for M5

### 8.1. T7 — Projection preservation under a fixed boundary [T]

Let the complete declared configuration relation of the two variants be:

$$
S^a=\{(u,v,z):z\in Z,\ u\in U_z^a,\ v\in V_z\},
\qquad a\in\{u_0,v_0\}.
$$

Here $Z$ is the same in both variants; the meaning and identity of the $V,z$ roles are preserved; and for every $z\in Z$, $U_z^a\ne\varnothing$. The factorization describes the complete relation, not a sample.

Then:

$$
\pi_{V,Z}(S^{u_0})
=\pi_{V,Z}(S^{v_0})
=\{(v,z):z\in Z,\ v\in V_z\}.
$$

**Proof.** Every member of either projection belongs to the set on the right. Conversely, for any $(v,z)$ on the right, nonemptiness permits a choice of $u\in U_z^a$ in either variant, so the pair appears in both projections. □

The theorem concerns the $V,Z$ projection. The full requirement additionally needs a justified connection between the model and the actual system.

### 8.2. What does not follow from the theorem?

If an additional proof relationship $p$ is not included in $V,Z$, its preservation does not follow. For example, one variant may have $p=y$ and the other $p=1-y$. In both cases, the possible values of $y$ are $\{0,1\}$, but the $(y,p)$ relation is $\{00,11\}$ in one and $\{01,10\}$ in the other.

For complete structural isolation, the target profile must contain every operational, conditional and support datum whose preservation is claimed. For a paired candidate, preservation within the pairing is a separate obligation as well.

Violating factorization, nonemptiness or the shared boundary invalidates applicability. A counterexample in which these assumptions fail does not refute the conditional theorem above; it shows that the theorem does not apply to that system. This distinction must also be retained in further M5 results.

## 9. Architectural and proof interface

### 9.1. Roles

| Layer | Role prepared by this document | Unchanged boundary |
|---|---|---|
| Paradoxon Diagram | Relation variants, joint answer structures, conditional impact and open obligations. | No independent release permission. |
| Transition Meter | Binding statements to evidence; distinguishing reconstruction from observation. | An a priori mathematical possibility does not become observed execution. |
| PULSEmech release authority | Later admission of evidence from a separately accepted adapter under the existing policy. | The complete authority chain is unchanged; no parallel decision engine. |
| PULSEbox and target receiver | Later, separately established operation enforcement. | This document does not claim a built, non-bypassable execution boundary. |

The Transition Meter source separately treats observation, binding, consistency, reproduction, causality and authority status; no axis may override another. [S2] This document does not redefine existing enum values.

### 9.2. Candidate evidence package — not an implemented schema

A later research result must carry at least the following content:

| Content | Why it is required |
|---|---|
| Profile, semantics and Anchor | Makes the examined claim identifiable. |
| Source variants and subject identities | Prevents silent application of the assessment to a different candidate. |
| Global correspondence | Prevents a difference from being hidden differently for each question. |
| Question profile and joint answer structure | Prevents joint relationships from being separated into independent indicators. |
| Pairing relation, where required | Preserves variant- or operation-dependent requirements that would be lost in endpoint sets. |
| Requirements and condition descriptions | Separates mechanical conditions from protected policy. |
| Derivation, certificate and assumptions | Makes the producer's result checkable. |
| Model and system coverage | Prevents a bounded conclusion from becoming an unrestricted claim. |
| Gaps, conflicts and counterexamples | Preserves unverified parts. |
| Authority boundary | The package initially has only `authority_effect: none`. |

### 9.3. Decision and actual effect

The analysis result, authority decision and actual receiver-side effect are three separate objects. A mathematical theorem does not establish target-side blocking. The pinned PULSEmech release chain connects subject, evidence, artifact, policy, required-set, verifier and final-state bindings to the terminal primary-CI result. [S3]

This research does not change the strict checker, policy materialization, the meaning of required gates or CI. The proposed interfaces do not authorize such changes.

### 9.4. Fail-closed application rule

If the selected policy makes a condition or evidence mandatory and it is not established, the specific protected operation must not obtain permission through the existing authority chain. This does not mean that every unresolved diagnostic datum automatically stops all operation.

An alternative proof may be used only for the same mandatory claim, with appropriate bindings and policy acceptance. It may not override the original requirement. A correction is a new, identified candidate; its own intermediate effects and applicability must also be examined.

## 10. K01–K10 — hand-worked reference cases

**Shared status:** author-provided mathematical derivations, not executed program tests. The reference content consists of the fully specified small sets and equations. No independent human validation or validation using a separate implementation is claimed.

### K01 — Joint structure beyond separate values

**K01a.** Domain $D^2$. The two sets are $\{00,11\}$ and $\{01,10\}$. Every individual projection is $D$, but the joint sets differ. Witness $00$ is present in one and absent from the other.

**K01b.** Domain $D^3$. One variant is:

$$
S=\{000,011,101,110\},
\qquad x\oplus y\oplus z=0.
$$

The other is the complete $D^3$. Every pairwise projection is $D^2$ in both. Configuration $001$ appears only in the complete cube. The ternary relationship cannot be reconstructed from the pairwise projections.

In the parity variant, $x=0$ implies $y=z$, while $x=1$ implies $y\ne z$. The individual $y,z$ possibilities nevertheless remain unchanged. XOR is linear over $\mathbb F_2$; this example establishes a higher-order relationship, not general nonlinearity.

**Acceptance condition:** the joint answer profile detects the difference; individual or pairwise projections must not receive an unjustified completeness classification.

### K02 — Identity, renaming and pairing

**K02a: permitted renaming.** The first singleton configuration has elements $\{p,a\}$ and the sole relation $\operatorname{Assoc}(p,a)$. The second singleton has elements $\{p,b\}$ and the sole relation $\operatorname{Assoc}(p,b)$. Identity $p$ is protected; $a,b$ are labels occupying an anonymous internal role. The correspondence is $J(p)=p$, $J(a)=b$, and acts in the same way on the relation and question references. There are no other variables or conditions. Normalized to the common anonymous role, the binding question gives the same result. A difference in the raw name does not establish mechanical impact.

**K02b: protected binding replacement.** The explicitly identified elements are $\{p,m_0,m_1\}$. The first variant has monitoring binding $(p,m_0)$, and the second has $(p,m_1)$. Both monitors have protected identities and $J$ may not exchange them. The binding question differs even if both diagrams draw only one edge.

**K02c: identical possibilities, different pairing.** Both sides have possibility set $D$. The identity pairing is $\{00,11\}$ and the swapping pairing is $\{01,10\}$. The M1 paired structure distinguishes them.

**Acceptance condition:** permitted renaming must not create a false impact, and a changed protected binding or pairing must not yield false identity.

### K03 — Mutuality is not self-justification

**K03a: mechanical mutuality.** Over the binary domain, $x=y$ has solution set $\{00,11\}$. Both conditional directions mutually restrict possibilities, yet the relation is consistent.

**K03b: justification cycle.** Statements $\{p,q\}$, rules $p\Rightarrow q$ and $q\Rightarrow p$. Without a base, closure is empty. With base $p$, both are derivable.

**K03c: loss of a base.** If accepted base $p$ is withdrawn, the cycle cannot by itself maintain justification of $p,q$. The correct new closure is empty; the earlier record is still preserved.

**Acceptance condition:** mechanical cycles must not be prohibited in general, but a self-contained proof cycle must not be accepted as grounded justification.

### K04 — Empty configuration family

Domain $D^2$, with conditions:

$$
x=y,\qquad y=1-x.
$$

Substitution into the first condition yields $x=1-x$, hence $2x=1$. Neither $x=0$ nor $x=1$ is a solution. The solution set is empty.

**Acceptance condition:** the outcome is model inconsistency, not an invariant-preservation PASS. Moving to the real numbers would introduce a new domain; its solution $x=y=1/2$ must not silently repair the binary profile.

### K05 — Subject-matter existence and evidence applicability

The coordinates are $(\ell,b)$, where $\ell$ denotes existence of the monitoring relationship and $b$ denotes current admissibility of the particular justification. Both are binary in the complete model, but represent differently typed statements.

The original singleton is $\{(1,1)\}$. After a bound rejection, the new singleton is $\{(1,0)\}$. The subject-matter projection remains unchanged: $\ell=1$. The required $\ell\land b$ for justified compliance no longer holds through this proof path.

Mere lack of access to evidence does not justify asserting $b=0$ as an observed fact. A partial model reflecting the available knowledge may be $\{(1,0),(1,1)\}$: this example separately assumes that the relationship exists, while the presence of an admissible justification is unresolved.

**Acceptance condition:** missing evidence must not imply $\ell=0$, and unknown $b$ must not automatically become true.

### K06 — Alternative justification and conjunctive premises

Statement set $\{e_1,e_2,e_3,c\}$; rules $\{e_1,e_2\}\Rightarrow c$ and $\{e_3\}\Rightarrow c$.

| Accepted bases | Is $c$ derivable in this profile? | Reason |
|---|---|---|
| $\{e_1,e_2\}$ | Yes. | Both premises of the first rule are present. |
| $\{e_3\}$ | Yes. | The second rule is independently sufficient. |
| $\{e_2,e_3\}$ | Yes. | The second route remains available despite absence of $e_1$. |
| $\{e_2\}$ | No. | The first route is incomplete and the second base is absent. |
| $\varnothing$ | No. | There is no accepted base. |

**Acceptance condition:** the AND–OR structure must not be flattened into reference edges without semantics. Nonderivability is not the same as falsity of $c$.

### K07 — Projection isolation and its scope

**K07a.** Domain $D^2$, roles $(x,y)$. Let

$$
S^u=\{0\}\times D,
\qquad
S^v=\{1\}\times D.
$$

Both $y$ projections are $D$. This is the special case of T7 with no explicit boundary coordinate.

**K07b.** Extend the roles with a support coordinate $p$. In the first variant, $p=y$; in the second, $p=1-y$. The $y$ projection is still unchanged, but the $(y,p)$ projection differs.

**Acceptance condition:** the first result establishes only preservation of the selected $y$ profile. The extended profile must not be classified as unchanged.

### K08 — Omitted shared condition

The separately specified mathematical reference is the complete relation $x=y$. When $x=0$, only $y=0$ is permitted; when $x=1$, only $y=1$ is permitted.

The faulty extraction omits $x=y$ and asserts independent roles $x,y$. It therefore returns $y\in D$ in both variants and could incorrectly report complete invariance.

**Acceptance condition:** the separately specified reference exposes the loss of information. Self-checking of the faulty model alone cannot establish the presence of the missing condition. This is a system–model binding case, not a refutation of the isolation theorem.

### K09 — Valid endpoints, violating operational configuration

Let $a,b\in D$ denote the bindings of two monitors, with requirement $I=a\lor b$. The selected endpoint configurations are $(1,0)$ and $(0,1)$; both satisfy the requirement.

The declared possible configurations of one candidate operation are:

$$
\mathcal W_{bad}=\{(1,0),(0,0),(0,1)\}.
$$

Element $(0,0)$ is a violating witness. Another candidate has set:

$$
\mathcal W_{good}=\{(1,0),(1,1),(0,1)\}.
$$

Every member satisfies $I$.

These sets introduce no global event order. A later execution profile must separately establish that these are indeed the relevant configurations possible during the operation, and that the operational requirements are also preserved.

**Acceptance condition:** proof of the endpoints does not replace examination of the candidate operation's complete relevant impact domain.

### K10 — Storage and processing order

A permuted enumeration of a finite relation represents the same set. For example, listings `00,11` and `11,00` encode the same relation $S$. After correct decoding, $\mathcal A$ is unchanged.

The definition of positive rule closure is also independent of rule enumeration order. Processing that reaches the least closure and eventually accounts for every applicable rule produces the same result. A single, non-closed left-to-right pass does not justify a completeness claim.

Raw bytes, digests and signatures may differ when the listing order changes. Semantic identity does not imply byte identity, and does not make an original signature valid for a different carrier.

**Acceptance condition:** the mechanical conclusion preserves permitted representational identity; carrier and evidence bindings remain exact.

## 11. Representation and refutation obligations

### 11.1. What constitutes a substantive failure?

| Failure or limit | Consequence |
|---|---|
| Identical separate answers conceal a joint distinction. | An M1 representation failure in the selected profile. |
| The same symbol with different meanings is classified as identical. | Missing semantic alignment. |
| A protected identity can be replaced through renaming. | An incorrect identity contract. |
| A condition change automatically weakens policy. | A violated authority boundary. |
| A proof cycle yields justification without a base. | The M3 closure rule or its implementation is incorrect. |
| Loss of one piece of evidence removes a valid alternative proof. | Loss of the support structure. |
| Projection preservation is taken to imply complete absence of structural impact. | An overstrong result claim. |
| A model omits a relevant path while calling itself complete. | An incorrect coverage claim. |

### 11.2. What is not a refutation?

Violating the assumptions of a conditional theorem demonstrates inapplicability, not falsity of the theorem. A method's time limit is not a mathematical impossibility proof. Success on one reference case is not a general fidelity theorem. Missing evidence is not a subject-matter refutation.

The common-mechanics hypothesis is not, by itself, refuted because the F0 proof language cannot express every phenomenon. The suitability of this particular representation is, however, limited if it could carry a distinction required for the selected task only by conflating types.

### 11.3. The open question of time and causality

No physical time is derived from this relational contract at this stage. Derivation order, order by set inclusion, variant pairing and a local order later examined for a concrete execution are separate concepts. None automatically inherits another's meaning.

Causal meaning requires additional domain-specific, checkable conditions. A difference between conditional completion families is presently a result of the declared relational semantics.

## 12. Completion inventory for the first unit

| Subject | Present result | What remains open? |
|---|---|---|
| F0 finite profile | The concrete example family, domains and semantic limits are specified. | Not a complete actual-system profile. |
| M1 joint answer structure | Definition, discrimination theorem and counterexamples are given. | Lossless mapping of the concrete Paradoxon representation. |
| M1 pairing | Changed pairing is distinguished from unchanged possibility sets. | Actual evidence for an operation-specific pairing. |
| M2 persistence condition | Configuration dependence and semantic change are separated; monitoring example derived. | Actual executor and monitoring coverage. |
| M3 proof transfer | Conditional transfer and required bindings are specified. | Mapping to concrete existing proof carriers. |
| M3 AND–OR and cycles | Positive closure, groundedness and a withdrawal counterexample are given. | Other logical profiles and efficient incremental implementation. |
| M4 common mechanical foundation | A shared type-preserving descriptive candidate. | Proof of stronger mechanical unity. |
| M5 isolation | The exact subject of the earlier theorem and its countercheck are recorded. | Further isolation theorems for the complete selected target profile. |
| K01–K10 | Hand derivations and acceptance conditions are given. | Independent checking; later software trials remain `NOT_RUN`. |
| Authority integration | Boundary and required evidence content are specified. | No implementation or activation. |

**This development does not close decision points D2 (representation fidelity), D3 (common mechanics) or D4 (pilot readiness).** D1 (definitions) now has concrete, reviewable text and derivations; this document's own classification does not substitute for its acceptance.

The mathematical derivations are elementary conditional statements. The document makes no novelty claim or claim of a general physical proof.

## 13. The next bounded research result

After M1–M3, the next planning unit should trace one concrete Paradoxon example through a complete mapping: source-bound Atoms and relations; the precise persistence requirement; the global correspondence $J$; the joint answer structure; conditional completions; proof supports; and witnesses of impact.

This must show that the candidate actually preserves the meaning of the Diagram's documented elements rather than merely renaming an independently correct general constraint model as Paradoxon. Missing sources or mappings must remain separate results; no invented mechanical connection should replace them.

Time-like properties and causality can be examined from this foundation only under additional conditions. A benefit against correction overload will later require its own comparative measurement; these definitions do not imply that the computation cost of the assessment is lower than the correction cost it prevents.

This repository edition preserves research documentation only. It introduces no implementation, executable tests, workflow or project execution. Publication of the document does not authorize implementation or a pilot run.

## 14. Sources and source binding

S1–S3 are the sources of the targeted reading at the previously selected repository snapshot. The research did not perform a new full repository survey, test execution or assessment of current `main` implementation state. S4–S6 are methodological background; the Paradoxon mechanics are not derived from them.

### S1 — PULSE GLOSSARY v0

[Source at the pinned commit](https://github.com/HKati/pulse-release-gates-0.1/blob/bb3c4791bc9399d0085d10d0d29d6d8a5e2cbfca/docs/GLOSSARY_v0.md)

Targeted reading recorded in the workshop source: lines 1–135, especially Anchor, Atom, Edge, Orientation, Core and the conditions for deterministic field outputs. Returned Git blob SHA: `109cf0132ada650e6e82f295c3fa9db68067410c`.

### S2 — PULSEmech Transition Meter

[Source at the pinned commit](https://github.com/HKati/pulse-release-gates-0.1/blob/bb3c4791bc9399d0085d10d0d29d6d8a5e2cbfca/PULSEMECH_TRANSITION_METER.md)

Targeted reading recorded in the workshop source: lines 1140–1362; preservation of missing edges; observation, reconstruction and hypothesis; causal distinctions; and the six status axes. Returned Git blob SHA: `2f785ad833358c43ddb0148f4534ca5d0f0c6042`.

### S3 — PULSEmech Technical Overview

[Source at the pinned commit](https://github.com/HKati/pulse-release-gates-0.1/blob/bb3c4791bc9399d0085d10d0d29d6d8a5e2cbfca/PULSEMECH_TECHNICAL_OVERVIEW.md)

Targeted reading recorded in the workshop source: lines 76–202; release-transition mechanics, run binding and the complete authority tuple. Returned Git blob SHA: `fb35551000c19e3e4c5ff7ae70750706087255aa`.

### S4 — Lean Language Reference: Validating a Lean Proof

[Official guide](https://lean-lang.org/doc/reference/latest/ValidatingProofs/)

Distinction used: proof checking, assumptions and the intended meaning of a formal statement. Live documentation; access date recorded in the workshop source: 2026-10-22. No Lean execution and no tool-selection decision.

### S5 — Lean Language Reference: Recursive Definitions

[Official reference](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/)

Distinction used: unconditional circular self-justification versus recursive or fixed-point definitions with soundness conditions. Live documentation; access date recorded in the workshop source: 2026-10-22. The F0 derivations T4–T6 are provided independently within this document.

### S6 — Patrick Cousot: Abstract Interpretation

[Author's background material](https://www.di.ens.fr/~cousot/AI/)

Distinction used: correctness of a model-level conclusion versus its validity for a concrete system. Access date recorded in the workshop source: 2026-10-22. This document does not claim that the entire Paradoxon mechanics reduces to abstract interpretation.

### Workshop antecedents

- Mechanical hypothesis and definition analysis v0.1, 2026-10-22.
- Mechanical research plan v0.2, 2026-10-22.
- The plan's five clarifications: joint question structure; semantics of condition change; proof transfer and circularity; scope of isolation; advance specification of the finite profile.

These were supplied as workshop texts for this task; they are not asserted to be separately committed repository documents. The PULSEbox role retained here is the planned boundary declared in those antecedents; this document has not verified a new PULSEbox implementation.

---

**Handoff summary:** an M1–M3 definition contract candidate; seven conditional theorems with derivations; hand-worked reference cases from the K01–K10 family; representation limits; and an unchanged authority boundary. The historical v0.1 text remains unchanged; this is a separate v0.2 development.
