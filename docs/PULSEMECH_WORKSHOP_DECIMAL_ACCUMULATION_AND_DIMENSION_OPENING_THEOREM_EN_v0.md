# The Workshop Decimal Number System

## A formal operational theorem of accumulation, place-value carry, and dimension opening

```yaml
document_id: pulsemech_workshop_decimal_accumulation_and_dimension_opening_theorem_en_v0
document_status: foundational_workshop_theorem
revision_state: formal_operational_theorem
language: en
version: v0
scope: finite_place_value_and_release_authority_mechanics
normative_policy_effect: none
release_authority_effect: none
gate_activation_effect: none
```

---

## 0. Purpose and system boundary

This document formalizes the Workshop theorem:

> **Growth is not identical to expansion.**

It separates four different events:

```text
quantitative growth
≠ representational length transition
≠ informational state-space expansion
≠ operational dimension opening
```

The theorem is not a redefinition of classical vector-space dimension.

The term **operational dimension opening** is defined here for a machine with explicit:

```text
carriers
bindings
states
inputs
transition rules
semantic states
outputs
consequences
```

An operational dimension opens when a newly active carrier–binding or authority-bearing relation creates either:

1. a previously unavailable operational path; or
2. a previously unavailable operational distinction;

and the new capability disappears when the responsible operational unit is disabled and the same mechanism is replayed in the same ambient system.

The central proof order is:

```text
before activation
→ capability absent

activation
→ capability present

same-ambient ablation
→ capability absent again

replay
→ the same relation is reproduced
```

This is a proof of operation, not a proof from notation alone.

---

# 1. Development and theorem-transfer boundary

## 1.1 Acceptance is not proof

A concept, definition, or theorem does not govern the Workshop machine merely because it is older or widely accepted.

```text
accepted view
≠ evidence

prior terminology
≠ current system boundary

identical symbol
≠ identical mechanism

a theorem proved in another model
≠ automatic proof in this model
```

A theorem may be correct in its own axioms and still be inapplicable to a machine with different carriers, bindings, states, or transition rules.

The role of mathematics in this document is to describe and test the Workshop machine correctly. It is not to force the machine back into a previously fixed conceptual box.

## 1.2 Applicability of an external theorem

Let:

```math
\mathcal W
```

be a Workshop machine and:

```math
\mathcal E
```

an external model.

An external theorem may be applied to the Workshop machine only after two distinct obligations are proved.

### Obligation A — structure and operation preservation

There must be fixed maps for the relevant states, inputs, carriers, semantic states, outputs, and consequences:

```math
\phi_X,
\qquad
\phi_\Sigma,
\qquad
\phi_H,
\qquad
\phi_{\mathcal S},
\qquad
\phi_Y,
\qquad
\phi_Z.
```

On the witness domain under examination, the correspondence must preserve the active machine structure and the complete operational response.

Where the transferred property depends on carriers, the carrier map must preserve the operationally enabled subset and active participation. In particular, the relevant correspondence must satisfy the declared analogue of:

```math
\phi_H\bigl(E_H^{\mathcal W}\bigr)
=
E_H^{\mathcal E},
```

and preserve the active carrier relation on the witness states.

At minimum, it must preserve:

```text
ambient carrier type where relevant
operationally enabled carrier participation
active carrier participation
active bindings
transition definedness
semantic target state
observed output
observed consequence
ablation contract and replay semantics
```

For the complete operational response defined later, let:

```math
\phi_B
```

be the componentwise observation map induced by:

```math
\phi_{\mathcal S},
\qquad
\phi_Y,
\qquad
\phi_Z,
```

with `defined` and `undefined` preserved exactly.

One direct preservation condition is:

```math
\phi_B\bigl(B_{\mathcal W}(x,\sigma)\bigr)
=
B_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma)
\bigr).
```

The same condition must hold for the ablated replay when an ablation result is used in the proof.

### Obligation B — transfer of the specific theorem property

A structural correspondence alone is not enough.

The property stated by the external theorem must be translated explicitly, and the required direction of preservation or reflection must be proved.

If:

```math
\tau_{\mathcal W}
```

is the Workshop property and:

```math
\mathrm{Tr}_{\phi}(\tau_{\mathcal W})
```

its external translation, then an external conclusion is usable only if the proof establishes the required implication back to the Workshop machine:

```math
\mathcal E
\models
\mathrm{Tr}_{\phi}(\tau_{\mathcal W})
\quad\Longrightarrow\quad
\mathcal W
\models
\tau_{\mathcal W}.
```

If the mapping collapses distinct Workshop states, carriers, bindings, or responses that matter to the theorem, the transfer is not valid for that theorem.

## 1.3 Consequence

A statement about classical dimension, infinite coordinate spaces, or another abstract object cannot negate an operational opening in the Workshop machine unless it is proved to preserve and reflect the exact machine and witness relation used here.

```text
external authority
≠ theorem authority

operation-preserving correspondence
+ property transfer
+ required reflection
→ applicable external result
```

---

# 2. Core distinctions

## 2.1 Quantitative growth

A quantitative coordinate changes from one value to a larger value.

```math
Q(x_1)>Q(x_0).
```

This says that a quantity increased.

It does not state that a new carrier, binding, path, distinction, or consequence became available.

## 2.2 Representational length transition

A normalized numeral requires more places than before.

For base:

```math
b\ge 2,
```

the normalized digit length is:

```math
\ell_b(0)=1,
```

and for:

```math
n\ge 1,
```

```math
\ell_b(n)
=
1+\left\lfloor\log_b n\right\rfloor.
```

A change in:

```math
\ell_b(n)
```

is a representational length transition.

It is not by itself a proof of classical mathematical dimension growth or operational dimension opening.

## 2.3 Informational state-space expansion

A new state coordinate adds information when it distinguishes states that the existing state description could not distinguish.

Let:

```math
P:X\to U
```

be the existing state description and:

```math
h:X\to V
```

an additional coordinate.

The coordinate is functionally new relative to:

```math
P
```

when no function:

```math
f:P(X)\to V
```

satisfies:

```math
h=f\circ P.
```

Equivalently, there exist:

```math
x,y\in X
```

such that:

```math
P(x)=P(y)
```

and:

```math
h(x)\ne h(y).
```

This is informational expansion.

It is neither necessary nor sufficient for operational dimension opening.

## 2.4 Operational dimension opening

Operational dimension opening is a property of what the machine can do.

It requires a new operational reachability or a new operational discrimination, together with an ablation witness showing that the responsible operational unit is necessary for that capability.

```text
new data
≠ automatically new operation

new operation
≠ necessarily new external data

new reachability or discrimination
+ same-mechanism ablation
→ operational dimension opening
```

---

# 3. The Workshop simple machine

## 3.1 Machine model

A Workshop machine is:

```math
\mathcal M
=
(
X,
\Sigma,
H,
E_H,
A,
R,
\Lambda,
\mathrm{Eval},
\nu,
O,
C,
Q
).
```

The components are:

- `X`: ambient state space;
- `Σ`: input or signal space;
- `H`: ambient carrier type represented by the state space;
- `E_H ⊆ H`: carriers operationally enabled for evaluation;
- `A(x) ⊆ E_H`: carriers active in state `x`;
- `R(x)`: active bindings in state `x`;
- `Λ`: available transition rules;
- `Eval`: the fixed transition evaluator;
- `ν`: semantic-state interpretation;
- `O`: machine-local output function;
- `C`: machine-local consequence function;
- `Q`: quantitative observation.

The distinction between:

```text
ambient carrier type H
≠ operationally enabled carrier set E_H
```

is required for same-ambient carrier ablation. A carrier may remain representable by the unchanged state type while being unavailable to the evaluator.

The partial transition function is derived from the evaluator:

```math
T_{\mathcal M}(x,\sigma)
=
\mathrm{Eval}
\bigl(
x,
\sigma;
E_H,
A,
R,
\Lambda
\bigr).
```

The result may be undefined.

The evaluator identity is part of the machine identity. A valid before–after–ablation comparison does not replace the evaluator with a different decision rule.

## 3.2 Common observation codomain

Different machines may use different internal state representations, output encodings, and consequence-record types.

A raw internal difference is not sufficient evidence of an operational opening.

Before witnesses are selected, a machine comparison fixes common observation spaces:

```math
\mathcal S,
\qquad
\mathcal Y_{\mathrm{obs}},
\qquad
\mathcal Z_{\mathrm{obs}}.
```

For every compared machine:

```math
\mathcal M,
```

its internal state is mapped into the common semantic-state space:

```math
\nu_{\mathcal M}:X_{\mathcal M}\to\mathcal S.
```

The machine-local functions have types:

```math
O_{\mathcal M}
:
X_{\mathcal M}
\to
Y_{\mathcal M},
```

and:

```math
C_{\mathcal M}
:
X_{\mathcal M}
\times
\Sigma_{\mathcal M}
\times
X_{\mathcal M}
\to
Z_{\mathcal M}.
```

Fixed observation maps are then required:

```math
\omega^O_{\mathcal M}
:
Y_{\mathcal M}
\to
\mathcal Y_{\mathrm{obs}},
```

```math
\omega^C_{\mathcal M}
:
Z_{\mathcal M}
\to
\mathcal Z_{\mathrm{obs}}.
```

Define the observed output and consequence by:

```math
\overline O_{\mathcal M}
=
\omega^O_{\mathcal M}\circ O_{\mathcal M},
```

and:

```math
\overline C_{\mathcal M}(x,\sigma,x')
=
\omega^C_{\mathcal M}
\bigl(
C_{\mathcal M}(x,\sigma,x')
\bigr).
```

The fixed common response codomain is the tagged sum:

```math
\mathcal R_{\mathrm{obs}}
=
\{\mathrm{undefined}\}
\;\uplus\;
\Bigl(
\{\mathrm{defined}\}
\times
\mathcal S
\times
\mathcal Y_{\mathrm{obs}}
\times
\mathcal Z_{\mathrm{obs}}
\Bigr).
```

The complete operational response is therefore a well-typed function:

```math
B_{\mathcal M}
:
X_{\mathcal M}
\times
\Sigma_{\mathcal M}
\to
\mathcal R_{\mathrm{obs}},
```

with:

```math
B_{\mathcal M}(x,\sigma)
=
\begin{cases}
\bigl(
\mathrm{defined},
\nu_{\mathcal M}(x'),
\overline O_{\mathcal M}(x'),
\overline C_{\mathcal M}(x,\sigma,x')
\bigr),
&
T_{\mathcal M}(x,\sigma)=x',
\\[6pt]
\mathrm{undefined},
&
T_{\mathcal M}(x,\sigma)
\text{ is undefined.}
\end{cases}
```

If the machines already use common output or consequence types, the corresponding observation maps may be identities.

The spaces and observation maps are fixed before the before–after–ablation responses are evaluated. They may not be selected afterward to create or erase the claimed difference.

The comparison can therefore change only because of one or more of the following observed relations:

```text
transition definedness
semantic target state
observed output
observed consequence
```

A mere internal recoding does not establish an opening.

## 3.3 State and input embeddings

Let:

```math
\mathcal M_0
```

be an old machine and:

```math
\mathcal M_1
```

an extended machine.

A well-typed comparison requires both a state embedding and an input embedding:

```math
\iota_X:X_0\to X_1,
```

```math
\iota_\Sigma:\Sigma_0\to\Sigma_1.
```

The state embedding must preserve the meaning of the old state before the new transition is applied:

```math
\nu_1\bigl(\iota_X(x)\bigr)
=
\nu_0(x).
```

When the input spaces differ, the comparison must declare a common signal-semantics space:

```math
\mathcal I
```

and maps:

```math
\mu_i:\Sigma_i\to\mathcal I
\qquad(i\in\{0,1\}).
```

The input embedding must preserve signal meaning:

```math
\mu_1\bigl(\iota_\Sigma(\sigma)\bigr)
=
\mu_0(\sigma).
```

When:

```math
\Sigma_0=\Sigma_1
```

with the same declared signal semantics, the input embedding may be the identity map.

For a witness:

```math
w=(x,\sigma)
\in
X_0\times\Sigma_0,
```

define the complete witness embedding:

```math
\widehat\iota(w)
:=
\bigl(
\iota_X(x),
\iota_\Sigma(\sigma)
\bigr).
```

Where unchanged-state outputs or consequences are compared, their values after the embeddings must agree in the common observation codomain.

The embeddings themselves must not create the claimed operational difference.

This document uses the shorthand:

```math
B_{\mathcal M}(w)
:=
B_{\mathcal M}(x,\sigma).
```

---

# 4. Same-ambient ablation and replay

## 4.1 Operational unit

An operational unit is a typed set of machine components:

```math
\kappa
=
(
H_\kappa,
R_\kappa,
\Lambda_\kappa
).
```

It may contain:

```text
one or more operationally enabled carriers
one or more bindings
one or more transition or authority rules
```

## 4.2 Same-ambient ablation

The notation:

```math
\mathrm{Abl}_{\kappa}(\mathcal M_1)
```

means operational disabling in the same ambient state and input spaces.

It does not mean replacing the machine with a smaller state or input type.

The ablated machine preserves:

```text
ambient state space
ambient input space
ambient carrier type
witness-state type
common response codomain
semantic-state interpretation
output-observation interpretation
consequence-observation interpretation
evaluator identity
```

It disables only the operational participation of the components in:

```math
\kappa.
```

The reduced operational structures are:

```math
E_H^{-\kappa}
=
E_H\setminus H_\kappa,
```

```math
A^{-\kappa}(x)
=
A(x)\cap E_H^{-\kappa},
```

```math
R^{-\kappa}(x)
=
R(x)\setminus R_\kappa,
```

and:

```math
\Lambda^{-\kappa}
=
\Lambda\setminus\Lambda_\kappa.
```

The ambient carrier type:

```math
H
```

remains unchanged, but the evaluator receives only:

```math
E_H^{-\kappa}.
```

The evaluator contract is carrier-scoped:

```math
\mathrm{ReadCarriers}_{\mathrm{Eval}}
(x,\sigma;E_H,A,R,\Lambda)
\subseteq
E_H.
```

It therefore cannot read, activate, or traverse a carrier that has been disabled operationally.

### Carrier-neutral witness requirement

A machine whose states store carrier-local values must declare a neutral value for each carrier. Neutrality means that the carrier contributes no semantic-state, observed-output, or observed-consequence difference on the declared comparison boundary.

The machine must also declare a carrier support function:

```math
\mathrm{supp}_H(x)
=
\{
h\in H:
\text{the value carried by }h\text{ in }x\text{ is non-neutral}
\}.
```

For carrier-removal ablation, the admissible witness domain is:

```math
W^0_\kappa
=
\{
(x,\sigma):
\mathrm{supp}_H(x)\cap H_\kappa
=
\varnothing
\}.
```

A carrier-removal ablation witness must belong to:

```math
W^0_\kappa.
```

A witness with a non-neutral value in a disabled carrier is not an `undefined` ablation result. It is an ill-formed witness for this ablation contract and may not be used as evidence of capability removal.

The neutral-witness requirement keeps the ambient state type unchanged while preventing a disabled carrier from remaining semantically or observationally present through stored non-neutral data.

If a system intends to compare non-neutral values in disabled carriers, it must declare and prove a separate masking or projection contract. No such masking is inferred by this document.

### Reduced-mechanism replay

For an admissible witness, the ablated transition is not stipulated from the original transition-use record.

It is recomputed by the same evaluator:

```math
T_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(x,\sigma)
=
\mathrm{Eval}
\bigl(
x,
\sigma;
E_H^{-\kappa},
A^{-\kappa},
R^{-\kappa},
\Lambda^{-\kappa}
\bigr).
```

This requirement preserves fallback paths.

If another valid path remains after ablation, the replay must return that path. The proof may not declare the response undefined merely because the original path used:

```math
\kappa.
```

## 4.3 The ablation principle

```text
remove the claimed cause
→ replay the same mechanism
→ observe the resulting capability
```

The ablation response must be produced by the machine.

It may not be inserted as an assumed value solely to complete the proof.

---

# 5. Operational change and operational dimension opening

## 5.1 Operational change, sensitivity, and restoration

Let:

```math
w=(x,\sigma)
```

be a witness in the old machine.

An operational change occurs at:

```math
w
```

when:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
\ne
B_{\mathcal M_0}(w).
```

The new response is **ablation-sensitive** to:

```math
\kappa
```

when:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
\ne
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w)\bigr).
```

Ablation sensitivity proves that disabling:

```math
\kappa
```

changes the new response under replay. It does not by itself prove that the entire pre-change response has been restored. The old, new, and ablated responses may otherwise be three distinct values.

**Exact response restoration** is proved only when:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w)\bigr)
=
B_{\mathcal M_0}(w).
```

Operational-dimension proofs do not always require exact tuple restoration. They require restoration of the precise capability relation being claimed:

```text
reachability opening
→ the definedness relation returns to the old relation

discrimination opening
→ the equality relation between the witnesses returns to the old relation
```

Every causal statement must identify which of the following was actually reproduced:

```text
ablation sensitivity
exact response restoration
reachability restoration
discrimination restoration
```

Operational change alone is not yet operational dimension opening.

## 5.2 Reachability opening

A **reachability opening at witness**:

```math
w=(x,\sigma)
```

is proved when:

```math
B_{\mathcal M_0}(w)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
=
\bigl(
\mathrm{defined},
s,
y,
z
\bigr),
```

and:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w)\bigr)
=
\mathrm{undefined}.
```

The ablated response restores the old definedness relation at the witness. In this reachability case it also equals the complete old response because both are the same tagged value:

```math
\mathrm{undefined}.
```

This proves that a previously unavailable operational path became reachable through:

```math
\kappa.
```

The claim is local to the witness unless a larger witness-domain inclusion is separately proved.

A stronger domain-expansion claim over a witness set:

```math
W
```

uses the old witness domain as the comparison base:

```math
\mathrm{Def}_{\mathcal M_0}(W)
=
\{
w\in W:
B_{\mathcal M_0}(w)
\text{ is defined}
\},
```

```math
\mathrm{Def}^{\widehat\iota}_{\mathcal M_1}(W)
=
\{
w\in W:
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
\text{ is defined}
\}.
```

The stronger claim requires:

```math
\mathrm{Def}_{\mathcal M_0}(W)
\subsetneq
\mathrm{Def}^{\widehat\iota}_{\mathcal M_1}(W).
```

The local reachability theorem does not silently assert this stronger global relation.

## 5.3 Discrimination opening

Let:

```math
w_1=(x_1,\sigma_1)
```

and:

```math
w_2=(x_2,\sigma_2)
```

be two witnesses.

A **discrimination opening** is proved when the old machine treats them identically:

```math
B_{\mathcal M_0}(w_1)
=
B_{\mathcal M_0}(w_2),
```

the new machine distinguishes them:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w_1)\bigr)
\ne
B_{\mathcal M_1}\bigl(\widehat\iota(w_2)\bigr),
```

and the distinction disappears when the responsible operational unit is ablated and the same evaluator is replayed:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w_1)\bigr)
=
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w_2)\bigr).
```

This restores the old equality relation between the two witnesses. It does not assert that each ablated response separately equals its exact old tuple unless those additional equalities are proved.

### Projection-scoped discrimination

A claim may be restricted to one fixed response projection when that projection is declared before witness selection and before any old, new, or ablated response is evaluated.

Fix one map:

```math
\rho
:
\mathcal R_{\mathrm{obs}}
\to
\mathcal R_{\rho}.
```

The same:

```math
\rho
```

must be used for every machine in the comparison:

```math
\mathcal M_0,
\qquad
\mathcal M_1,
\qquad
\mathrm{Abl}_{\kappa}(\mathcal M_1).
```

Define:

```math
B^{\rho}_{\mathcal M}
=
\rho\circ B_{\mathcal M}.
```

A projection-scoped discrimination opening is proved by applying the same old-equal, new-unequal, ablated-equal relations to:

```math
B^{\rho}.
```

A machine-indexed family of independently chosen projection maps is not admissible for this comparison. Different maps could create or erase a distinction even when the complete machine responses are unchanged.

The resulting claim is limited to the named projection. It does not imply that the complete operational responses are equal or unequal in the same way.

The PULSEmech release-decision theorem later uses this form with one policy-fixed release-decision projection on the common response space.

A uniform output replacement for every witness is an operational change. It is not a discrimination opening because it creates no new distinction between witnesses.

## 5.4 Definition

Under this document, an **operational dimension opening** is established by at least one of the following:

```text
reachability opening
or
discrimination opening
```

with:

```text
fixed system boundary
fixed common response codomain
fixed complete-response boundary or one fixed projection shared across every compared machine
fixed state and input embeddings
fixed evaluator identity
same-ambient ablation
admissible carrier-neutral witness when carriers are removed
recomputed ablation response
restoration of the claimed capability relation
reproduced result
```

The word `dimension` refers to a new operational direction of the defined machine. It does not assert growth of classical vector-space dimension.

---

# 6. Quantitative growth and mechanical stagnation

## 6.1 Quantitative growth

Let:

```math
Q:X\to V
```

be an ordered quantitative observation.

A transition or sequence exhibits quantitative growth if:

```math
Q(x_{n+1})>Q(x_n).
```

This condition states only that a measured amount increased.

## 6.2 Mechanical stagnation

Let:

```math
W
```

be a fixed witness domain and let the old witnesses be embedded into the compared machine.

The machines are operationally unchanged on:

```math
W
```

when:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
=
B_{\mathcal M_0}(w)
\qquad
\text{for every }w\in W.
```

If quantity grows while this relation remains true, the change is mechanical stagnation on the declared witness domain.

No inference is made from a coarse list of carrier types or rule names alone. The complete operational response is the deciding object.

## 6.3 First theorem — growth does not imply opening

### Theorem

Quantitative growth alone does not imply an operational dimension opening.

### Proof

The condition:

```math
Q(x_{n+1})>Q(x_n)
```

contains no requirement that:

- a previously undefined transition becomes defined;
- two previously equal responses become different;
- a new carrier becomes operationally necessary;
- a new binding enters the transition mechanism;
- an output or consequence changes.

A machine may therefore satisfy quantitative growth while its complete response remains unchanged on the witness domain:

```math
B_{\mathcal M_1}\circ\widehat\iota
=
B_{\mathcal M_0}.
```

Then neither a reachability opening nor a discrimination opening is present.

Therefore:

```math
\text{quantitative growth}
\not\Rightarrow
\text{operational dimension opening}.
```

QED.

---

# 7. The decimal place-value system

## 7.1 The Workshop decimal field

The phrase **decimal field** is a Workshop term.

It does not mean an algebraic field.

The precise digit set is:

```math
D_{10}
=
\{0,1,2,3,4,5,6,7,8,9\}.
```

More generally, for base:

```math
b\ge 2,
```

```math
D_b
=
\{0,1,\ldots,b-1\}.
```

This is the complete normalized digit range of one place-value carrier.

## 7.2 Normalized representation

For base:

```math
b\ge 2,
```

define the normalized digit length by:

```math
\ell_b(0)=1,
```

and:

```math
\ell_b(n)
=
1+\left\lfloor\log_b n\right\rfloor
\qquad(n\ge 1).
```

Let:

```math
m(n)
=
\ell_b(n)-1.
```

Every natural number:

```math
n
```

has a unique normalized base-`b` representation:

```math
n
=
\sum_{k=0}^{m(n)}d_kb^k,
```

where:

```math
d_k\in D_b.
```

The zero case is fixed explicitly:

```math
n=0
\quad\Longrightarrow\quad
m(n)=0
\quad\text{and}\quad
d_0=0.
```

For a positive number, the highest digit is nonzero:

```math
n>0
\quad\Longrightarrow\quad
d_{m(n)}\ne 0.
```

Therefore an arbitrary longer all-zero prefix is not another normalized representation of zero.

For:

```math
m\ge 1,
```

at the threshold:

```math
b^m-1
\longrightarrow
b^m,
```

```math
\ell_b(b^m-1)=m,
```

and:

```math
\ell_b(b^m)=m+1.
```

This is a representational length transition.

## 7.3 Active and nonzero carriers

Let:

```math
h_k
```

be the carrier of place value:

```math
b^k.
```

The minimally active carriers of a normalized number are:

```math
A_b(n)
=
\{h_k:0\le k<\ell_b(n)\}.
```

The carriers currently holding a nonzero digit are:

```math
N_b(n)
=
\{h_k\in A_b(n):d_k(n)\ne 0\}.
```

These sets are different.

For decimal ten:

```math
A_{10}(10)
=
\{h_0,h_1\},
```

while:

```math
N_{10}(10)
=
\{h_1\}.
```

The units carrier:

```math
h_0
```

is active even though its current digit value is zero. It remains part of the normalized state structure and the transition mechanism.

```text
active carrier
≠ nonzero carrier
```

---

# 8. Carry as a value-preserving binding

## 8.1 One-place carry

If a temporary coefficient at place:

```math
k
```

reaches or exceeds the base, Euclidean division gives unique:

```math
q,r
```

such that:

```math
c_k=bq+r,
```

with:

```math
0\le r<b.
```

Therefore:

```math
c_kb^k
=
r b^k
+
q b^{k+1}.
```

The value is preserved while the normalized representation is reorganized across carriers.

## 8.2 Carry theorem

### Theorem

Place-value carry preserves the represented numerical value.

### Proof

From:

```math
c_k=bq+r,
```

multiplication by:

```math
b^k
```

gives:

```math
c_kb^k
=
q b^{k+1}
+
r b^k.
```

The value before and after carry is identical.

QED.

## 8.3 Decimal threshold

At the first decimal threshold:

```math
10\cdot 10^0
=
1\cdot 10^1.
```

In Workshop form:

```text
ten units
→ one ten
→ higher place-value carrier
→ new carry binding
```

The numerical identity is value-preserving.

The operational theorem concerns the machine path required to produce the normalized successor.

---

# 9. The finite place-value machine

## 9.1 The machine with `m` carriers

Fix:

```math
b\ge 2
```

and:

```math
m\ge 1.
```

The ambient state space is:

```math
X_m
=
D_b^m.
```

The ambient carriers are:

```math
H_m
=
\{h_0,h_1,\ldots,h_{m-1}\}.
```

In the unablated machine, every ambient carrier is operationally enabled:

```math
E_{H,m}
=
H_m.
```

The semantic interpretation is:

```math
\nu_m(d_0,\ldots,d_{m-1})
=
\sum_{k=0}^{m-1}d_kb^k.
```

The active-carrier function is:

```math
A_m(x)
=
A_b\bigl(\nu_m(x)\bigr)\cap E_{H,m}.
```

Therefore:

```math
A_m(x)
\subseteq
E_{H,m}.
```

The neutral value at every place-value carrier is:

```math
0.
```

For:

```math
x=(d_0,\ldots,d_{m-1}),
```

the carrier support is:

```math
\mathrm{supp}_{H_m}(x)
=
\{
h_k\in H_m:
d_k\ne 0
\}.
```

The quantitative observation and numerical output are:

```math
Q_m(x)=\nu_m(x),
```

```math
O_m(x)=\nu_m(x).
```

For a defined increment transition:

```math
x\xrightarrow{+1}x',
```

the consequence record is:

```math
C_m(x,+1,x')
=
\bigl(
\nu_m(x),
+1,
\nu_m(x')
\bigr).
```

All machines in this finite family use the same observation codomains:

```math
\mathcal S
=
\mathbb N,
```

```math
\mathcal Y_{\mathrm{obs}}
=
\mathbb N,
```

and:

```math
\mathcal Z_{\mathrm{obs}}
=
\mathbb N
\times
\{+1\}
\times
\mathbb N.
```

The semantic-state, output-observation, and consequence-observation maps are the displayed numerical maps, so the old, extended, and ablated complete responses inhabit one common response codomain.

The enabled adjacent carry bindings are state-independent in this finite machine:

```math
R_m(x)
=
\{c_{k\to k+1}:0\le k<m-1\}
\qquad
\text{for every }x\in X_m.
```

The rule set:

```math
\Lambda_m
```

contains the local increment rule, the zero-and-carry rule, and the undefined-boundary rule stated in the next subsection.

The signal set contains:

```math
+1.
```

The transition evaluator is the fixed local increment-and-carry evaluator described below.

## 9.2 Increment-and-carry evaluator

Given:

```math
x=(d_0,\ldots,d_{m-1}),
```

and signal:

```math
+1,
```

the evaluator begins at:

```math
h_0.
```

For each place:

```math
h_k,
```

it applies exactly one of the following rules.

### Local increment

If:

```math
d_k<b-1,
```

replace:

```math
d_k
```

with:

```math
d_k+1
```

and stop.

### Carry

If:

```math
d_k=b-1,
```

replace:

```math
d_k
```

with:

```math
0,
```

then follow the enabled carry binding:

```math
c_{k\to k+1}
```

to the operationally enabled higher carrier:

```math
h_{k+1}.
```

The higher carrier may be inactive in the source state. Reaching it through an enabled carry binding activates it in the normalized target state.

### Undefined boundary

If:

- the current place is saturated;
- no operationally enabled higher carrier exists; or
- no enabled carry binding reaches it;

then the transition is undefined.

The evaluator does not invent an unavailable carrier or binding.

## 9.3 Maximum state of the old machine

The maximum normalized state of the `m`-carrier machine is:

```math
x_m^{\max}
=
(b-1,b-1,\ldots,b-1).
```

Its semantic value is:

```math
\nu_m(x_m^{\max})
=
b^m-1.
```

Every carrier is saturated.

The old machine has no carrier:

```math
h_m
```

and no carry binding:

```math
c_{m-1\to m}.
```

Therefore:

```math
T_m(x_m^{\max},+1)
=
\bot.
```

The normalized successor is not reachable in that machine.

## 9.4 Extension by one operational unit

Define the new operational unit:

```math
\kappa_m
=
\bigl(
\{h_m\},
\{c_{m-1\to m}\},
\Lambda_{\kappa_m}
\bigr).
```

The extended machine has:

```math
H_{m+1}
=
H_m\cup\{h_m\}.
```

Before ablation, every ambient carrier of the extended machine is operationally enabled:

```math
E_{H,m+1}
=
H_{m+1}.
```

The old state embeds into the extended ambient state space by:

```math
\iota_m(d_0,\ldots,d_{m-1})
=
(d_0,\ldots,d_{m-1},0).
```

The embedding preserves semantic value:

```math
\nu_{m+1}(\iota_m(x))
=
\nu_m(x).
```

The signal spaces are identical, so the input embedding is the identity:

```math
\iota_{\Sigma,m}(+1)
=
+1.
```

The complete witness embedding is therefore:

```math
\widehat\iota_m(x,+1)
=
\bigl(\iota_m(x),+1\bigr).
```

With:

```math
\kappa_m
```

enabled, the same increment-and-carry evaluator produces:

```math
T_{m+1}
\bigl(
\iota_m(x_m^{\max}),
+1
\bigr)
=
(0,0,\ldots,0,1).
```

The semantic target is:

```math
\nu_{m+1}(0,\ldots,0,1)
=
b^m.
```

## 9.5 Same-ambient ablation

The ablated machine retains the ambient state space:

```math
X_{m+1}
```

and the ambient carrier type:

```math
H_{m+1}.
```

It removes the new higher carrier from the operationally enabled carrier set:

```math
E_{H,m+1}^{-\kappa_m}
=
H_m,
```

disables:

```math
c_{m-1\to m},
```

and disables the corresponding rules:

```math
\Lambda_{\kappa_m}.
```

The embedded maximum-state witness is neutral on the carrier removed by the ablation:

```math
\mathrm{supp}_{H_{m+1}}
\bigl(
\iota_m(x_m^{\max})
\bigr)
\cap
\{h_m\}
=
\varnothing,
```

because:

```math
\iota_m(x_m^{\max})
=
(b-1,\ldots,b-1,0).
```

The witness therefore belongs to the carrier-neutral ablation domain.

The same increment-and-carry evaluator is replayed with the reduced operational structures.

The carry propagates through all lower saturated places and reaches the disabled final carry edge.

The evaluator cannot activate:

```math
h_m
```

because:

```math
h_m
\notin
E_{H,m+1}^{-\kappa_m}.
```

No alternative carry path exists in this machine.

Therefore:

```math
T_{\mathrm{Abl}_{\kappa_m}(\mathcal M_{m+1})}
\bigl(
\iota_m(x_m^{\max}),
+1
\bigr)
=
\bot.
```

The undefined result is produced by replay of the reduced mechanism. It is not inserted by definition from the original path.

---

# 10. Operational opening at a place-value threshold

## 10.1 General theorem

### Theorem

For every:

```math
b\ge 2
```

and:

```math
m\ge 1,
```

the extension from the finite normalized `m`-carrier place-value machine to the corresponding `m+1`-carrier machine creates a reachability opening at the witness:

```math
w_m
=
(x_m^{\max},+1),
```

provided the new operational unit:

```math
\kappa_m
```

contains the higher carrier and the final carry binding required by the fixed evaluator.

### Proof

In the old machine:

```math
B_{\mathcal M_m}
(x_m^{\max},+1)
=
\mathrm{undefined}.
```

In the extended machine:

```math
B_{\mathcal M_{m+1}}
\bigl(
\iota_m(x_m^{\max}),
+1
\bigr)
```

is defined and has semantic target:

```math
b^m.
```

In the same ambient state and input spaces, disabling:

```math
\kappa_m
```

and replaying the same evaluator gives:

```math
B_{\mathrm{Abl}_{\kappa_m}(\mathcal M_{m+1})}
\bigl(
\iota_m(x_m^{\max}),
+1
\bigr)
=
\mathrm{undefined}.
```

The three response relations satisfy the definition of a reachability opening at:

```math
w_m.
```

Therefore the higher carrier–binding unit opens a new operational direction of the finite normalized place-value machine.

QED.

## 10.2 Decimal corollary — `9 → 10`

For:

```math
b=10
```

and:

```math
m=1,
```

the old machine has:

```math
X_1=D_{10}
```

and:

```math
T_1(9,+1)=\bot.
```

Embed:

```math
9
```

as:

```math
\iota_1(9)=(9,0).
```

The embedding preserves meaning:

```math
\nu_2(9,0)=9.
```

Activate:

```math
\kappa_1
=
\bigl(
\{h_1\},
\{c_{0\to1}\},
\Lambda_{\kappa_1}
\bigr).
```

Then:

```math
T_2((9,0),+1)
=
(0,1),
```

and:

```math
\nu_2(0,1)=10.
```

Disable:

```math
\kappa_1
```

in the same two-place ambient machine and replay the same evaluator:

```math
T_{\mathrm{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

The witness is:

```text
old finite machine
→ no normalized successor

higher carrier + carry binding
→ normalized successor 10

same-ambient ablation
→ successor unavailable again
```

This is an operational opening under the definition of this document.

It is not a claim that the classical mathematical dimension of the natural-number line increased at ten.

## 10.3 What is proved

The proof establishes:

```text
a complete lower place-value range was exhausted
→ the old normalized machine had no successor path
→ a higher carrier and binding entered operation
→ a new normalized state became reachable
→ removing the operational unit removed that reachability
```

The proof is not based solely on:

```text
the number of digits
or
the visual form of 10
```

The operation is the evidence.

---

# 11. Informational novelty and operational novelty

## 11.1 Informational novelty is not sufficient

A machine may record a new coordinate:

```math
h
```

that is functionally independent of the old description:

```math
P.
```

If the transition evaluator, output, and consequence functions never read or use:

```math
h,
```

then the complete operational response remains unchanged.

The state description became richer.

No operational dimension opened.

```text
new information
+ no operational binding
→ no operational opening
```

## 11.2 Informational novelty is not necessary

Let:

```math
h(g)
=
g_1\land g_2.
```

The coordinate:

```math
h
```

is fully derived from the existing state:

```math
g.
```

It introduces no new external information.

If a new decision mechanism makes its result authority-bearing, the machine may begin to distinguish cases that it previously treated identically.

Therefore:

```text
derived coordinate
+ new operative binding
→ possible operational opening
```

The source of the opening is the new working relation, not informational independence alone.

## 11.3 Exact separation

```text
informational expansion
→ new state distinction is representable

operational opening
→ new reachability or discrimination is executable
```

Neither relation implies the other without additional conditions.

---

# 12. Quantity, unboundedness, and infinity

## 12.1 Unbounded magnitude does not imply a new direction

Let:

```math
V
```

be a normed vector space and let:

```math
v\ne 0.
```

Define:

```math
x_n=nv.
```

Then:

```math
\|x_n\|
=
n\|v\|
\longrightarrow
\infty.
```

The sequence is unbounded.

Every element remains in:

```math
\mathrm{span}\{v\},
```

which has dimension one.

Therefore:

```math
\text{unbounded magnitude}
\not\Rightarrow
\text{new independent direction}.
```

This classical example supports the separation between growth and expansion. It does not define the Workshop operational opening.

## 12.2 The infinity symbol does not supply a mechanism

The statement:

```math
x_n\to\infty
```

states an unboundedness relation.

It does not create:

```text
a carrier
a binding
a transition rule
a semantic target state
an output
a consequence
```

Therefore:

```text
infinity notation
≠ operational dimension opening
```

A formula cannot replace a missing machine path.

---

# 13. Formula, state, and mechanism

A formal expression has distinct layers:

```text
syntax
semantics
operation
```

Inserting a symbol changes syntax.

Under an already fixed semantics, it may also change the expression's meaning or truth value.

It does not by itself create an operational mechanism.

A mechanical conclusion requires:

```text
defined carrier
defined binding
defined transition rule
fixed common observation boundary
executable witness
reproduced consequence
```

Therefore:

```text
notation
≠ result

formula
≠ mechanism

assumption
≠ proof

symbolic presence
≠ operational activation
```

---

# 14. “Acquired” is not a terminal state

## 14.1 Terminal state

In a transition system, a state is terminal only when no outgoing transition is available from it.

Formally, state:

```math
x
```

is terminal when:

```math
T(x,\sigma)
```

is undefined for every admissible input:

```math
\sigma.
```

The label:

```text
acquired
```

does not make a state terminal by itself.

## 14.2 Truncated acquisition model

A truncated model may contain only:

```text
absent
→ acquired
→ end
```

A fuller machine contains further relations:

```text
acquired
→ bound into use
→ maintained
→ transformed or degraded
→ produces consequences
→ retired or replaced
```

If the post-acquisition mechanism is removed from the model, the only visible motion may become repeated acquisition:

```text
acquired one
→ acquired another
→ acquired more
```

This is multiplicity growth caused by a truncated state model.

---

# 15. The princess-dress example

Let:

```math
\tau
```

be the object type:

```text
princess dress
```

and let:

```math
x_n=(\tau,n)
```

record the number of identical objects.

Then:

```text
one princess dress
→ ten princess dresses
→ one thousand princess dresses
```

may satisfy:

```math
Q(x_{1000})>Q(x_1).
```

If the objects retain the same role and no new operative binding, state path, output, or consequence is created, then the change is quantitative accumulation.

```text
more instances
+ same operative relation
→ no operational opening
```

If the objects are organized into a new working system and that relation creates new reachability or discrimination, the opening is caused by the new relation.

The count is not the proof.

---

# 16. PULSEmech application

## 16.1 Release authority is operational

Fix an active policy identity:

```math
\pi
```

and verifier identity:

```math
v.
```

For this application, the compared PULSEmech machines:

```math
\mathcal P_0,
\qquad
\mathcal P_1,
\qquad
\mathrm{Abl}_{\kappa_h}(\mathcal P_1)
```

use the same ambient evaluator-input type:

```math
I_{\mathcal P}.
```

The state and input embeddings on this fixed ambient type are identities. Each PULSEmech machine is an instance of the Workshop machine and therefore has the Section 3 complete response:

```math
B_{\mathcal P}
:
I_{\mathcal P}
\to
\mathcal R_{\mathrm{obs}}.
```

The same common response codomain and the same semantic, output, and consequence observation boundaries are used for the pre-activation, post-activation, and ablated machines.

Let the release-decision codomain be:

```math
\mathcal D
=
\{\mathrm{ALLOW},\mathrm{BLOCK}\}.
```

Let:

```math
\mathcal U_\pi
```

be the fixed product of every other response component that policy:

```math
\pi
```

makes authority-bearing. If there are no additional components, this space is a singleton.

The complete authority-response codomain is the fixed tuple type:

```math
\mathcal A_\pi
=
\mathcal D
\times
\mathcal U_\pi.
```

Before PASS/FAIL witnesses are selected, policy:

```math
\pi
```

fixes one authority projection on the common Workshop response space:

```math
\rho^{\pi}_{\mathrm{auth}}
:
\mathcal R_{\mathrm{obs}}
\to
\mathcal A_\pi.
```

The exact same projection is used for every compared PULSEmech machine. Define:

```math
B^{\mathrm{auth}}_{\mathcal P}
=
\rho^{\pi}_{\mathrm{auth}}
\circ
B_{\mathcal P}
:
I_{\mathcal P}
\to
\mathcal A_\pi.
```

For:

```math
z\in I_{\mathcal P},
```

write the two tuple components as:

```math
B^{\mathrm{auth}}_{\mathcal P}(z)
=
\bigl(
d_{\mathcal P}(z),
U^{\mathrm{auth}}_{\mathcal P}(z)
\bigr).
```

Define the fixed tuple projection:

```math
\pi_{\mathcal D}
:
\mathcal A_\pi
\to
\mathcal D,
```

by:

```math
\pi_{\mathcal D}(d,u)=d.
```

The single policy-fixed release-decision projection on the common Workshop response space is:

```math
\rho^{\pi}_{\mathrm{decision}}
=
\pi_{\mathcal D}
\circ
\rho^{\pi}_{\mathrm{auth}}
:
\mathcal R_{\mathrm{obs}}
\to
\mathcal D.
```

The scalar release-decision function is therefore:

```math
D^{\mathrm{release}}_{\mathcal P}
=
\rho^{\pi}_{\mathrm{decision}}
\circ
B_{\mathcal P}
=
\pi_{\mathcal D}
\circ
B^{\mathrm{auth}}_{\mathcal P}.
```

Consequently:

```math
d_{\mathcal P}(z)
=
D^{\mathrm{release}}_{\mathcal P}(z).
```

Complete authority-response comparisons use:

```math
B^{\mathrm{auth}}_{\mathcal P}.
```

Scalar `ALLOW` and `BLOCK` comparisons use:

```math
D^{\mathrm{release}}_{\mathcal P}.
```

The maps:

```math
\rho^{\pi}_{\mathrm{auth}}
```

and:

```math
\rho^{\pi}_{\mathrm{decision}}
```

are fixed once for the entire comparison. They may not vary between the old, new, and ablated machines.

The complete tuple is never equated directly to a scalar decision.

On the declared PULSEmech witness domain, the evaluator response must be defined. If the common response boundary permits an `undefined` value, policy:

```math
\pi
```

must assign its deterministic fail-closed authority image through the same fixed projection. A machine-specific fallback projection is not permitted.

Metadata-only differences are excluded from:

```math
\mathcal U_\pi
```

unless the active policy explicitly gives them release-authority effect.

PULSEmech release authority is not created by the presence of more files, gates, records, or labels.

```text
more evidence records
≠ more release authority

more artifacts
≠ more release authority

more gate names
≠ more release authority
```

A gate becomes authority-bearing only through a complete operational path.

A representative path is:

```text
current-run evidence
→ artifact and run binding
→ policy binding
→ required-gate materialization
→ deterministic verification
→ gate evaluation
→ ALLOW or BLOCK
```
## 16.2 Authority dependency model

Let:

```math
\Gamma_0=(V_0,E_0)
```

be the pre-activation dependency graph and:

```math
\Gamma_1=(V_1,E_1)
```

the post-activation dependency graph of the release evaluator.

Let:

```math
s_{\mathrm{release}}
```

be the release-decision sink, and let:

```math
S_{\mathrm{auth}}
```

be the set of all authority-bearing response sinks under policy:

```math
\pi.
```

For graph nodes:

```math
p,q\in V_0\cup V_1,
```

let:

```math
\mathrm{Paths}_{\Gamma}(p,q)
```

denote the active data- or control-dependency paths from:

```math
p
```

to:

```math
q.
```

Let:

```math
\mathrm{Eval}_{\pi,v}
```

be the fixed deterministic evaluator identified by policy identity:

```math
\pi
```

and verifier identity:

```math
v.
```

The authority response and the release-decision projection are produced by this evaluator from the materialized graph and gate state.

Each graph is required to be dependency-complete for its authority evaluation: every data or control dependency by which a node can influence an authority-bearing sink is represented in the graph.

The evaluator may not use an unrecorded side path outside the declared dependency graph.

## 16.3 Candidate or advisory presence

Let:

```math
h
```

be a candidate or advisory gate.

Choose two otherwise identical evaluator inputs:

```math
z_{\mathrm{PASS}}
```

and:

```math
z_{\mathrm{FAIL}},
```

which differ only in the verified value of:

```math
h.
```

If:

```math
\mathrm{Paths}_{\Gamma_0}
(h,s_{\mathrm{release}})
=
\varnothing,
```

then the value of:

```math
h
```

cannot change the release decision under the dependency-complete evaluator:

```math
D^{\mathrm{release}}_{\mathcal P_0}
(z_{\mathrm{PASS}})
=
D^{\mathrm{release}}_{\mathcal P_0}
(z_{\mathrm{FAIL}}).
```

If:

```math
\mathrm{Paths}_{\Gamma_0}(h,s)
=
\varnothing
\qquad
\text{for every }s\in S_{\mathrm{auth}},
```

then the stronger complete-tuple equality follows:

```math
B^{\mathrm{auth}}_{\mathcal P_0}
(z_{\mathrm{PASS}})
=
B^{\mathrm{auth}}_{\mathcal P_0}
(z_{\mathrm{FAIL}}).
```

No release-sink path is sufficient for the release-decision claim. Complete authority-response equality is asserted only under the stronger all-authority-sinks condition.

This is presence without release-decision authority.

```text
candidate or advisory gate
+ no path to the release sink
→ no release-decision dimension
```

## 16.4 Activation of an authority-bearing gate

Let the operational unit:

```math
\kappa_h
```

contain the components that make:

```math
h
```

a release-required condition:

```text
required-set materialization
current-run evidence binding
artifact binding
policy binding
verifier binding
authority dependency nodes and edges
release-evaluation rule
```

Under the same fixed policy and evaluator, use the same two inputs that differ only in the verified value of:

```math
h.
```

If:

```math
D^{\mathrm{release}}_{\mathcal P_1}
(z_{\mathrm{PASS}})
=
\mathrm{ALLOW},
```

and:

```math
D^{\mathrm{release}}_{\mathcal P_1}
(z_{\mathrm{FAIL}})
=
\mathrm{BLOCK},
```

then the new authority path creates a release-decision discrimination that the previous machine did not have.

Because the release decision is a component of the complete authority tuple, this also implies:

```math
B^{\mathrm{auth}}_{\mathcal P_1}
(z_{\mathrm{PASS}})
\ne
B^{\mathrm{auth}}_{\mathcal P_1}
(z_{\mathrm{FAIL}}).
```

## 16.5 Authority-complete ablation

A valid authority ablation preserves:

```text
ambient gate-state type
policy identity
verifier identity
evaluator identity
all unrelated graph nodes and edges
release-decision codomain
complete authority-response codomain
```

It disables exactly the selected authority-bearing components of:

```math
\kappa_h
```

and produces a reduced dependency graph:

```math
\Gamma_1^{-\kappa_h}.
```

For the ablation to prove removal of the claimed release-decision relation, the selected unit must be an **authority-complete cut** for:

```math
h.
```

The required no-remaining-path condition is:

```math
\mathrm{Paths}_{\Gamma_1^{-\kappa_h}}
(h,s_{\mathrm{release}})
=
\varnothing.
```

If any alternate data or control path remains, the ablation does not prove that the selected unit removes the authority relation.

After the cut is materialized, the same evaluator is replayed:

```math
\mathrm{Eval}_{\pi,v}.
```

The ablated result is produced by the evaluator. It is not manually assigned.

The required release-decision restoration relation is an explicit replay result:

```math
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{PASS}})
=
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{FAIL}}).
```

For example, a declared fail-closed evaluator may produce:

```math
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{PASS}})
=
\mathrm{BLOCK},
```

and:

```math
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{FAIL}})
=
\mathrm{BLOCK}.
```

The exact equal decision depends on the declared evaluator. Equality must be observed under replay; it is not inferred from the word `ablation` alone.

Complete authority-response equality:

```math
B^{\mathrm{auth}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{PASS}})
=
B^{\mathrm{auth}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{FAIL}})
```

is a stronger claim. It may be used only when all authority-bearing tuple components are observed to be equal.

Exact restoration of each pre-activation tuple is also a stronger claim and is not required for restoration of the release-decision equality relation.

## 16.6 PULSEmech release-decision discrimination theorem

### Theorem

A gate opens an operational release-decision dimension when:

1. its values were previously release-decision-indistinguishable;
2. a bound, materialized, verified authority path makes those values produce different release decisions;
3. the selected ablation unit forms an authority-complete cut, leaving no active path from the gate to the release sink;
4. replay of the same evaluator restores release-decision equality.

### Proof

Before activation:

```math
D^{\mathrm{release}}_{\mathcal P_0}
(z_{\mathrm{PASS}})
=
D^{\mathrm{release}}_{\mathcal P_0}
(z_{\mathrm{FAIL}}).
```

After activation:

```math
D^{\mathrm{release}}_{\mathcal P_1}
(z_{\mathrm{PASS}})
\ne
D^{\mathrm{release}}_{\mathcal P_1}
(z_{\mathrm{FAIL}}).
```

The authority-complete cut satisfies:

```math
\mathrm{Paths}_{\Gamma_1^{-\kappa_h}}
(h,s_{\mathrm{release}})
=
\varnothing.
```

After same-ambient authority ablation and evaluator replay:

```math
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{PASS}})
=
D^{\mathrm{release}}_{\mathrm{Abl}_{\kappa_h}(\mathcal P_1)}
(z_{\mathrm{FAIL}}).
```

The single fixed response projection used for all three compared machines is:

```math
\rho^{\pi}_{\mathrm{decision}}
:
\mathcal R_{\mathrm{obs}}
\to
\mathcal D.
```

For every compared PULSEmech machine:

```math
\mathcal P
\in
\left\{
\mathcal P_0,
\mathcal P_1,
\mathrm{Abl}_{\kappa_h}(\mathcal P_1)
\right\},
```

its projection-scoped response is:

```math
B^{\rho^{\pi}_{\mathrm{decision}}}_{\mathcal P}
=
\rho^{\pi}_{\mathrm{decision}}
\circ
B_{\mathcal P}
=
D^{\mathrm{release}}_{\mathcal P}.
```

The old-equal, new-unequal, and ablated-equal relations above are therefore exactly the Section 5.3 discrimination relations under one common projection. The old equality relation is broken by activation and restored by authority-complete ablation replay.

Therefore:

```math
\kappa_h
```

opens an operational release-decision dimension.

QED.

## 16.7 Derived gate

The gate:

```math
h
```

may be fully derived from existing evidence.

Its derivability does not prevent an operational opening.

The deciding relation is:

```text
derived result
+ binding
+ required materialization
+ verifier
+ complete authority path
+ release-decision distinction
+ authority-complete-cut ablation replay
→ operational release-decision dimension
```

No new external information is required when a new authority-bearing relation is created from existing information.

---

# 17. Reproducible proof package

A claim of operational dimension opening must record enough information to reproduce the machine comparison.

The minimum proof package contains:

```yaml
system_boundary:
old_machine_identity:
new_machine_identity:
ambient_state_space:
old_input_space:
new_input_space:
common_input_semantics_space:
common_semantic_state_space:
common_output_observation_space:
common_consequence_observation_space:
output_observation_maps:
consequence_observation_maps:
complete_response_codomain:
response_boundary_used_for_the_claim:
response_projection_map_if_applicable:
single_projection_identity_across_old_new_and_ablation_if_applicable:
response_projection_codomain_if_applicable:
pulse_complete_response_map_to_common_codomain_if_applicable:
authority_projection_from_common_response_if_applicable:
release_decision_projection_from_common_response_if_applicable:
projection_composition_identity_result_if_applicable:
evaluator_identity:
quantitative_coordinate:
state_embedding:
input_embedding:
input_semantics_space:
input_semantics_preservation_result:
witness_embedding:
embedding_preservation_result:
evaluator_carrier_access_contract_if_applicable:
operational_unit_identity:
activation_components:
ablation_components:
operationally_enabled_carriers_before:
operationally_enabled_carriers_after:
operationally_enabled_carriers_after_ablation:
carrier_neutrality_predicate_if_applicable:
carrier_neutral_witness_result_if_applicable:
same_ambient_ablation_contract:
witness_type:
witness_inputs:
before_response:
after_response:
ablation_response:
ablation_sensitivity_result:
exact_response_restoration_result_if_claimed:
capability_restoration_relation:
replay_result:
authority_response_tuple_if_applicable:
release_decision_projection_if_applicable:
authority_dependency_graph_if_applicable:
authority_cut_components_if_applicable:
no_remaining_authority_path_result_if_applicable:
negative_controls:
```

For a reachability witness, the recorded response relation must be:

```text
before: undefined
after: defined
ablation: undefined
```

For a discrimination witness, under the fixed response boundary used by the claim, it must be:

```text
before: equal responses
after: unequal responses
ablation: equal responses
```

A record of:

```text
new response ≠ ablated response
```

proves ablation sensitivity only. It does not prove exact restoration unless the package also records:

```text
ablated response = old response
```

For carrier-removal ablation, the proof package must show that the embedded witness is carrier-neutral on every disabled carrier. A non-neutral witness is invalid under this ablation contract and may not be recorded as an `undefined` proof result.

For a PULSEmech release-decision discrimination claim, the proof package must separately record:

```text
complete PULSE response in the common Workshop response codomain
one policy-fixed authority projection from that common response
one policy-fixed release-decision projection from that common response
complete authority-response tuple type
composition identity linking the complete response, authority response, and release decision
release-decision projection identity reused across old, new, and ablated machines
dependency-complete graph
authority-complete cut
no remaining gate-to-release-sink path
same-evaluator replayed decision equality
```

The proof package must also confirm:

```text
same common response codomain
same fixed response projection across old, new, and ablated machines when projection-scoped
same evaluator identity
semantics-preserving state embedding
semantics-preserving input embedding
recomputed ablation response
no manual substitution of the ablation result
restoration of the exact capability relation claimed
```

## 17.1 Negative controls

The following cases must not be accepted as operational dimension openings without additional evidence:

```text
quantity increases but complete responses remain equal

internal representation changes but common observed responses remain equal

outputs or consequences are compared without a common observation codomain

states are embedded but inputs are neither identical nor embedded

new information is recorded but no transition or authority path reads it

every witness receives the same new output and no new discrimination appears

new response differs from ablated response but the claimed old capability relation is not restored

a carrier-removal witness contains non-neutral data in a disabled carrier

the original path is deleted without replaying the reduced mechanism

an authority ablation leaves an alternate gate-to-release-sink path

a complete authority tuple is equated directly to the scalar ALLOW or BLOCK

different machine-indexed projections create or erase the claimed distinction

a PULSE decision response is not derived as a fixed projection of the common complete response

zero is represented by arbitrary-length all-zero tuples

an external theorem is cited without operation-preserving transfer
```

These controls protect the theorem from both false expansion and false reduction.

---

# 18. Main theorem

## The Workshop theorem of quantitative growth and operational dimension opening

Let:

```math
\mathcal M_0
```

and:

```math
\mathcal M_1
```

be machines compared through:

```text
a fixed common response codomain
+ one fixed response projection across all compared machines when projection-scoped
+ a semantics-preserving state embedding
+ a semantics-preserving input embedding
+ a fixed evaluator identity
```

Let:

```math
\kappa
```

be the operational unit introduced or activated in:

```math
\mathcal M_1.
```

Then the following statements hold.

### I. Quantitative growth

```math
Q(x_1)>Q(x_0)
```

alone does not imply either reachability opening or discrimination opening.

Therefore:

```math
\text{quantitative growth}
\not\Rightarrow
\text{operational dimension opening}.
```

### II. Representational length transition

```math
\ell_b(n_1)>\ell_b(n_0)
```

states that the normalized representation became longer.

It does not by itself prove classical dimension growth or operational opening.

### III. Informational expansion

A functional refinement of the state description proves informational novelty.

It does not prove that the new information participates in the machine.

Operational opening may also occur without informational novelty when an existing or derived value enters a new operative relation.

### IV. Operational change and restoration

If:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
\ne
B_{\mathcal M_0}(w),
```

then an operational change occurred at:

```math
w.
```

If:

```math
B_{\mathcal M_1}\bigl(\widehat\iota(w)\bigr)
\ne
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w)\bigr),
```

then the new response is ablation-sensitive to:

```math
\kappa.
```

This inequality alone does not prove restoration of the pre-change response.

Exact response restoration requires:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}
\bigl(\widehat\iota(w)\bigr)
=
B_{\mathcal M_0}(w).
```

For operational-dimension opening, the reachability or discrimination relation specified in Part V must be restored under replay.

### V. Operational dimension opening

An operational dimension opens when the operational change takes one of two precise forms on the fixed complete-response boundary or on one explicitly named projection applied unchanged to every compared machine.

#### V.a Reachability opening

A witness that was undefined becomes defined, and becomes undefined again after admissible same-ambient ablation replay.

#### V.b Discrimination opening

Two witnesses that previously had equal responses receive different responses, and the equality relation is restored after admissible same-ambient ablation replay.

The discrimination case does not require each ablated tuple to equal its corresponding old tuple unless exact response restoration is separately claimed.

### VI. Decimal opening

In the finite normalized base-`b` place-value machine, the transition:

```math
b^m-1
\longrightarrow
b^m
```

is undefined in the `m`-carrier machine, defined after activation of the higher carrier and final carry binding, and undefined again after same-ambient ablation of that unit.

The embedded witness is neutral on the newly disabled higher carrier, and the reduced evaluator has no alternative carry path.

Therefore it is a reachability opening of the finite normalized place-value machine.

For decimal:

```math
9\longrightarrow10
```

is the first instance.

### VII. PULSEmech opening

A candidate or advisory gate with no active path to the release sink does not create release-decision authority.

A bound, materialized, verified gate opens an operational release-decision dimension when:

```text
its PASS and FAIL values were previously decision-equal
→ activation makes the release decisions unequal
→ an authority-complete cut removes every gate-to-release-sink path
→ replay of the same evaluator restores decision equality
```

Scalar `ALLOW` and `BLOCK` relations are evaluated through the single policy-fixed map `\rho^{\pi}_{\mathrm{decision}}` from the common response space, not by equating the complete authority-response tuple to a scalar and not by changing projections between machines.

### VIII. External theorem boundary

No external theorem overrides these conclusions by historical acceptance or terminology alone.

Applicability requires:

```text
structure and operation preservation
+ transfer of the specific property
+ reflection in the required direction
```

on the machine and witness under examination.

## Proof summary

Parts I–III follow from the definitions and explicit counterexamples separating amount, representation, information, and operation.

Part IV follows from the well-typed common response comparison and distinguishes ablation sensitivity from exact or capability restoration.

Part V is the definition of operational dimension opening used in this document.

Part VI is proved by the finite increment-and-carry machine, its carrier-neutral embedded witness, and its same-ambient reduced-mechanism replay.

Part VII is proved by the single policy-fixed PULSEmech projection from the common response space, the dependency-complete authority graph, the authority-complete cut, and same-evaluator replay.

Part VIII follows from the theorem-transfer obligations in Section 1.

QED.

---

# 19. The Workshop calculation order

The Workshop does not stop at the question:

> How much did it become?

The complete calculation order is:

```text
1. Which quantitative coordinate changed?

2. Which finite unit or range was completed?

3. Which carrier became active?

4. Which binding entered operation?

5. Which transition became reachable?

6. Which previously equal cases became distinguishable?

7. What semantic state, output, or consequence changed?

8. Does disabling the claimed operational unit remove the capability?

9. Does replay reproduce the same result?
```

The decisive question is not whether a relation is present in the description.

The decisive question is whether it operates and whether the claimed capability depends on it.

---

# 20. Workshop theorem

> **Numbers do not open merely because their values become larger.**
>
> **A complete place-value range closes when its normalized carrier can no longer produce the next state.**
>
> **A higher carrier and its binding open a new operational direction when they make that state reachable, and the reachability disappears when the unit is disabled and the same mechanism is replayed.**

In compact form:

```text
accumulation
→ quantitative growth

place-value threshold
→ representational length transition

new state distinction
→ informational expansion

new reachability or discrimination
+ restored capability relation under ablation replay
→ operational dimension opening
```

---

# 21. The Workshop principle

> **In the Workshop, we calculate in decimal.**
>
> **After a complete decimal unit closes, we do not treat the next state as merely more of the unchanged same.**
>
> **We identify the higher carrier, the new binding, the transition it enables, and the consequence it produces.**
>
> **A binding alone is not proof. Its operation is proof.**
