# The Workshop Decimal Number System

## A mathematical and operational theorem separating accumulation, place-value carry, and operational dimension opening

```yaml
document_id: pulsemech_workshop_decimal_accumulation_and_dimension_opening_theorem_en_v0
document_status: foundational_workshop_theorem
language: en
version: v0
scope: workshop_mathematical_and_operational_foundation
normative_policy_effect: none
release_authority_effect: none
gate_activation_effect: none
```

---

## 0. Subject of the document

This document separates the following phenomena:

```text
quantitative growth
≠ representational length transition
≠ informational state-space expansion
≠ operational dimension opening
```

The starting theorem is:

> **Growth is not identical to expansion.**

The value of an existing quantitative coordinate may grow without bound while the system's:

- active carriers;
- operative bindings;
- transition rules;
- outputs;
- consequences

do not open a new operational direction.

The decimal place-value system shows that after a complete finite digit range has been exhausted, the next normalized state requires the activation of a higher place value and a carry into it.

This document does not claim that the `9 → 10` transition increases the classical mathematical dimension of vector spaces.

It states:

> **In a finite normalized place-value machine, the `9 → 10` transition requires a previously inactive higher place value and the carry leading into it to become operational.**

Under the Workshop definition, this is an operational dimension opening because the target state cannot be produced through the same normalized mechanical path without the new carrier–binding unit.

A further boundary applies inside the operational layer:

```text
operational change
≠ operational dimension opening
```

An opening requires new reachability or a new operational discrimination.

---

# 1. Development and proof invariant

## 1.1 Acceptance and proof

A previously accepted concept, view, or theorem does not become a governing rule of the Workshop machine merely because it has historical acceptance.

```text
accepted view
≠ evidence

prior definition
≠ current system boundary

identical notation
≠ identical mechanism

a theorem proved in another model
≠ automatic proof in this model
```

An external theorem may be fully proved within its own axioms, objects, and system boundaries. This does not establish that the same theorem applies unchanged to a system with a different carrier, binding, and transition mechanism.

The role of mathematics in this document is not to force the original Workshop theorem back into a previously fixed conceptual system.

Its role is to:

```text
name the machine
→ separate its states
→ describe its bindings
→ formalize its transition
→ provide an operational witness
→ establish necessity through an ablation test
```

---

## 1.2 Applicability of an external theorem

Let:

```math
\mathsf A_{\mathcal E}
```

be an external theory,

```math
\mathcal E
```

the examined model of the external theory,

```math
\mathsf A_{\mathcal W}
```

the Workshop theory, and:

```math
\mathcal W
```

the examined Workshop model.

If a theorem is derivable in the external theory:

```math
\mathsf A_{\mathcal E}
\vdash
\tau_{\mathcal E},
```

and:

```math
\mathcal E
\models
\mathsf A_{\mathcal E},
```

this alone does not imply:

```math
\mathsf A_{\mathcal W}
\vdash
\tau_{\mathcal W}
```

or:

```math
\mathcal W
\models
\tau_{\mathcal W}.
```

Transfer requires two separate proofs:

```text
1. a structure- and operation-preservation proof
2. a proof that the property stated by the specific theorem transfers
```

Neither proof replaces the other.

### Minimum structure- and operation-preservation requirements

Relative to the object under examination, the correspondence must preserve at least:

```text
carrier
binding
state
input or signal
transition
semantic state
output
consequence
```

Let the state, signal, carrier, semantic-state, output, and consequence maps between the two systems be, respectively:

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

The minimum verification requirement for structure and operation preservation is that every listed component have a fixed and proved preservation or reflection condition.

One strong direct preservation form requires the maps to preserve active carriers and bindings:

```math
\phi_H\bigl(A_{\mathcal W}(x)\bigr)
=
A_{\mathcal E}\bigl(\phi_X(x)\bigr),
```

```math
(\phi_H\times\phi_H)\bigl(R_{\mathcal W}(x)\bigr)
=
R_{\mathcal E}\bigl(\phi_X(x)\bigr),
```

and the transition:

```math
T_{\mathcal W}(x,\sigma)=x'
\;\Longrightarrow\;
T_{\mathcal E}\bigl(\phi_X(x),\phi_\Sigma(\sigma)\bigr)
=
\phi_X(x'),
```

the fixed semantic-state interpretation:

```math
\phi_{\mathcal S}
\bigl(
\nu_{\mathcal W}(x')
\bigr)
=
\nu_{\mathcal E}
\bigl(
\phi_X(x')
\bigr),
```

and the output and consequence:

```math
\phi_Y\bigl(O_{\mathcal W}(x')\bigr)
=
O_{\mathcal E}\bigl(\phi_X(x')\bigr),
```

```math
\phi_Z\bigl(C_{\mathcal W}(x,\sigma,x')\bigr)
=
C_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma),
\phi_X(x')
\bigr).
```

Verification of the listed components is the required minimum. The displayed equalities provide one strong preservation form; a specific correspondence may use different commutation or reflection conditions if their equivalence is proved.

These structural conditions are not universally sufficient for transferring an arbitrary external theorem.

A correspondence may, for example, collapse two carriers, states, or operational responses that are distinct in the Workshop. In that case the image of a transition may formally exist while a distinction that determines the theorem has been lost.

### Transfer of the specific property

Let:

```math
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
```

be the translation, along the fixed correspondence, of the Workshop property `\tau_{\mathcal W}` into the external model.

Let:

```math
\mathcal E_{\phi}
```

denote the external substructure selected by the image of the correspondence and relevant to the proof. The theorem transfer may not rely on objects or relations in the external model that have no proved Workshop counterpart.

The external theorem `\tau_{\mathcal E}` and the translation of the Workshop property must first be proved to identify the same theorem on the relevant substructure:

```math
\mathcal E_{\phi}
\models
\Bigl(
\tau_{\mathcal E}
\;\Longleftrightarrow\;
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\Bigr).
```

This excludes treating an external theorem as identical to the Workshop theorem merely because it uses similar notation while referring to different objects, quantifier domains, or system boundaries.

It must also be proved that the external theorem holds on the relevant substructure:

```math
\mathcal E_{\phi}
\models
\tau_{\mathcal E}.
```

The translated property must then be reflected back to the Workshop machine:

```math
\mathcal E_{\phi}
\models
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\;\Longrightarrow\;
\mathcal W
\models
\tau_{\mathcal W}.
```

The full application chain is:

```math
\mathcal E_{\phi}\models\tau_{\mathcal E}
\;\Longrightarrow\;
\mathcal E_{\phi}\models
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\;\Longrightarrow\;
\mathcal W\models\tau_{\mathcal W}.
```

If a complete bidirectional correspondence between the two models is claimed, both directions of translation and reflection must be proved on the relevant substructure:

```math
\mathcal E_{\phi}\models\tau_{\mathcal E}
\;\Longleftrightarrow\;
\mathcal E_{\phi}\models
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\;\Longleftrightarrow\;
\mathcal W\models\tau_{\mathcal W}.
```

The required condition may depend on the specific theorem. It may require, for example:

```text
injectivity
reflection of distinctions
preservation and reflection of reachability
preservation of undefinedness in partial transitions
faithful preservation of output or consequence classes
identical domains for quantifiers and system boundaries
```

Therefore:

```text
structural similarity
≠ theorem transfer

operation preservation
≠ automatic preservation of every property

external proof
+ proof of transfer for the specific property
→ applicable conclusion for the Workshop machine
```

If structure preservation or transfer of the specific property has not been proved, the external theorem cannot be used to withdraw an observed and reproducible operation in the Workshop.

In that case the external theorem is at most a comparative view, not governing authority.

---

## 1.3 Development boundary

Development must not regress into a prior conceptual system merely because that system is older or more widely accepted.

Regression occurs when development:

```text
reclassifies an operative carrier
→ as mere notation

flattens an active binding
→ into a pre-assumed relation

reduces an operational transition
→ to a numerical difference

ignores a reproducible consequence
→ because of an external definition
```

In the Workshop, an external formalism is a verification tool.

It is not authority.

---

# 2. Conceptual boundaries

## 2.1 The Workshop concept of the “decimal field”

In this document, **decimal field** does not mean the abstract-algebraic concept of a `field`.

The decimal field is the complete normalized digit range of one place value:

```math
D_{10}
=
\{0,1,2,3,4,5,6,7,8,9\}.
```

For a general base `b`:

```math
D_b
=
\{0,1,\ldots,b-1\},
\qquad
b\geq 2.
```

The `0–9` range is complete in the sense that it contains every permitted state of one normalized decimal digit.

---

## 2.2 Mathematical dimension and operational dimension

This document separates two distinct concepts.

### Mathematical dimension

The number of independent coordinates, basis elements, or degrees of freedom in a given mathematical structure, as defined by that structure.

### Operational dimension

In the Workshop, an operational dimension is a new carrier, relation, or transition rule bound into operation whose activation creates at least one of the following two operational openings at the fixed observation boundary:

```text
reachability opening
→ a previously unavailable valid state path becomes reachable

discrimination opening
→ states or inputs previously treated identically receive different operational responses
```

Ablation of the new operational unit in the same ambient space must remove the created reachability or discrimination.

A mere change in operational response does not by itself prove an operational dimension opening.

```text
operational change
≠ automatically a new operational direction

operational change
≠ automatically a new discrimination capability
```

Therefore:

```text
mathematical dimension
≠ operational dimension
```

A correspondence may exist between the two concepts. The correspondence and preservation of the transferred property must be proved separately for each concrete system.

---

## 2.3 Possible, active, and nonzero carriers

Let `H` be the set of possible carriers in the system.

The set of active carriers in a state `x` is:

```math
A(x)\subseteq H.
```

A carrier may be part of the possible architecture without yet participating in operation in the given state.

```text
possible carrier
≠ active carrier

pre-assumed coordinate
≠ coordinate bound into operation

presence
≠ activation
```

Activity means operational participation, not a value test.

A place-value carrier may remain active when its current digit value is zero, provided that it:

```text
is part of the normalized state structure
+ is part of the place-value order
+ participates in the transition mechanism
```

Therefore:

```text
active carrier
≠ carrier holding a nonzero value
```

This distinction is required for an exact description of place-value carry and PULSEmech gate state.

---

# 3. The Workshop simple machine

## 3.1 The model

The Workshop machine is described by the following system:

```math
\mathcal M
=
(X,\Sigma,H,A,R,T,\nu,O,C,Q).
```

Its components are:

```text
X
→ set of possible states

Σ
→ set of inputs or operational signals

H
→ set of possible carriers

A : X → 2^H
→ carriers active in the given state

R : X → 2^(H×H)
→ bindings operative in the given state

T : X×Σ ⇀ X
→ partial transition function

ν : X → 𝒮
→ fixed semantic-state interpretation of the internal state

O : X → Y
→ output function

C : X×Σ×X → Z
→ consequence function

Q : X → 𝒬
→ quantitative coordinate in an ordered quantitative space
```

The partial-transition notation expresses that a valid next state does not exist for every input from every state.

The semantic-state interpretation `ν` is not a label selected after the fact. It is part of the system definition and must be fixed before the operational witness is recorded.

---

## 3.2 Common observation layer and complete operational response

Raw target states of machines with different internal state spaces cannot be compared directly.

The internal target state is therefore mapped into a fixed common semantic state space:

```math
\nu_{\mathcal M}
:
X_{\mathcal M}
\rightarrow
\mathcal S.
```

Observations from the compared machines arrive in common semantic-state, output, and consequence spaces:

```math
\Psi_{\mathcal M}
:
X_{\mathcal M}
\times
\Sigma_{\mathcal M}
\times
X_{\mathcal M}
\rightarrow
\mathcal S
\times
Y
\times
Z.
```

The operational observation is:

```math
\Psi_{\mathcal M}(x,\sigma,x')
=
\bigl(
\nu_{\mathcal M}(x'),
O_{\mathcal M}(x'),
C_{\mathcal M}(x,\sigma,x')
\bigr).
```

If the machines have different native semantic, output, or consequence spaces, fixed maps must project them into the common `\mathcal S`, `Y`, and `Z` spaces before comparison.

The common tagged response type for the complete operational response is:

```math
\mathcal B
=
\{\mathrm{undefined}\}
\sqcup
\bigl(
\{\mathrm{defined}\}
\times
\mathcal S
\times
Y
\times
Z
\bigr).
```

The response function is:

```math
B_{\mathcal M}
:
X_{\mathcal M}
\times
\Sigma_{\mathcal M}
\rightarrow
\mathcal B.
```

The complete operational response is:

```math
B_{\mathcal M}(x,\sigma)
=
\begin{cases}
\bigl(
\mathrm{defined},
\Psi_{\mathcal M}(x,\sigma,x')
\bigr),
& \text{if } T_{\mathcal M}(x,\sigma)=x',\\[6pt]
\mathrm{undefined},
& \text{if } T_{\mathcal M}(x,\sigma)
\text{ is undefined.}
\end{cases}
```

Every compared before, after, and ablation response therefore arrives in the same `\mathcal B` space.

`\mathrm{undefined}` means that the examined mechanism cannot produce a valid next state from the given state under the given signal. In later abbreviated formulas, `⊥` may denote the same transition undefinedness.

The complete response compares:

```text
whether the transition exists
its produced semantic target state
its produced output
its produced consequence
```

The raw internal state vector is not part of the decisive inter-machine comparison. A different internal encoding alone does not prove an operational opening.

The observation boundary must retain the same meaning across the before, after, and ablation runs. When an old state is embedded into a new machine, semantic preservation is required:

```math
\nu_{\mathcal M_1}
\bigl(
\iota(x)
\bigr)
=
\nu_{\mathcal M_0}(x).
```

The interpretation of `ν`, `O`, and `C` may not be chosen after the fact to conceal or manufacture an operational difference.

---

## 3.3 Operational signature

Raw state identity cannot determine whether the mechanism has changed. Two states may have different quantitative values while the same operational rule applies to both.

We therefore assign an operational signature to the system:

```math
\Omega_{\mathcal M}:X\rightarrow\mathcal O.
```

According to the examined system boundary, the operational signature contains:

```text
the types and roles of active carriers
the order of active bindings
the available transition rules
the output classes
the producible consequence classes
```

The raw quantitative value `Q(x)` is not part of the signature unless the quantitative value itself activates a new rule or binding.

The operational signature is not a label selected from an external viewpoint. It is derived from the actual state, binding, and transition structure of the machine.

---
# 4. Quantitative growth and mechanical stagnation

## 4.1 Quantitative growth

A state sequence `x_0,x_1,x_2,…` is quantitatively increasing if:

```math
Q(x_{n+1})>Q(x_n)
```

in at least one quantitative coordinate.

This alone does not state that:

- a new carrier was activated;
- a new binding was created;
- a new transition path opened;
- a new output became reachable;
- a new consequence appeared.

---

## 4.2 Mechanical stagnation

Mechanical stagnation occurs alongside quantitative growth if:

```math
Q(x_{n+1})>Q(x_n)
```

and:

```math
\Omega_{\mathcal M}(x_{n+1})
=
\Omega_{\mathcal M}(x_n).
```

The exact chain is:

```text
quantitative value increases
→ operational signature remains unchanged
→ no new operational direction
→ mechanical stagnation
```

This does not mean that the complete state remained identical.

The quantitative coordinate changed.

The structural and operational order did not open.

---

## 4.3 First theorem — Quantitative growth is not sufficient for expansion

### Theorem

An increase in the value of an existing quantitative coordinate does not by itself prove an operational dimension opening.

Formally:

```math
Q(y)>Q(x)
```

does not imply:

```math
\Omega_{\mathcal M}(y)
\neq
\Omega_{\mathcal M}(x).
```

### Proof

Take a state sequence for which:

```math
Q(x_n)=n
```

and, for every `n`:

```math
\Omega_{\mathcal M}(x_n)=\omega
```

with the same operational signature `ω`.

Then:

```math
Q(x_{n+1})>Q(x_n),
```

while:

```math
\Omega_{\mathcal M}(x_{n+1})
=
\Omega_{\mathcal M}(x_n).
```

The quantity grows, but no new operational signature is created.

QED.

---
# 5. The Decimal Place-Value System

## 5.1 Normalized Representation

Every nonnegative integer `n` has a unique decimal place-value representation:

```math
n
=
\sum_{k=0}^{m} d_k10^k,
```

where:

```math
d_k\in D_{10},
```

and, for `n>0`:

```math
d_m\neq 0.
```

For a general base `b`:

```math
n
=
\sum_{k=0}^{m} d_kb^k,
\qquad
d_k\in D_b.
```

The digit `d_k` is the state associated with place value `b^k`.

---

## 5.2 Representational Length

The minimum digit length of the normalized base-`b` representation is:

```math
\ell_b(0)=1,
```

and, for `n≥1`:

```math
\ell_b(n)
=
\min\{m\geq 1:n<b^m\}
=
1+\left\lfloor\log_b n\right\rfloor.
```

The exponent of the highest nonzero place value is:

```math
m_b(n)
=
\left\lfloor\log_b n\right\rfloor,
\qquad n\geq 1.
```

The relation is:

```math
\ell_b(n)=m_b(n)+1.
```

Examples:

```math
\ell_{10}(9)=1,
\qquad
\ell_{10}(10)=2,
```

```math
\ell_{10}(99)=2,
\qquad
\ell_{10}(100)=3.
```

Representational length is not identical to the number of nonzero digits.

For example:

```math
\ell_{10}(101)=3,
```

while two digits are nonzero.

---

## 5.3 Minimally Active and Nonzero Place-Value Carriers

In the finite normalized Workshop machine, the minimally active place-value carriers required to produce value `n` are:

```math
A_b(n)
=
\{h_0,h_1,\ldots,h_{\ell_b(n)-1}\}.
```

Here `h_k` is the carrier of place value `b^k`.

The place values currently carrying nonzero digit values form the separate set:

```math
N_b(n)
=
\{
 h_k\in A_b(n)
 :
 d_k(n)\neq 0
\}.
```

Therefore:

```math
A_{10}(9)=\{h_0\},
\qquad
N_{10}(9)=\{h_0\},
```

```math
A_{10}(10)=\{h_0,h_1\},
\qquad
N_{10}(10)=\{h_1\}.
```

In state `10`, the current digit value of `h_0` is zero, but `h_0` remains active: it is part of the normalized state structure, the place-value order, and the subsequent transition mechanism.

The higher place value may already belong to the space of possible carriers. At state `10`, it becomes an active and necessary part of the minimum normalized representation.

---

# 6. Place-Value Carry

## 6.1 Carry at One Place Value

Let a temporary coefficient at the `k`-th place value satisfy:

```math
c_k\geq b.
```

By Euclidean division, unique `q` and `r` exist such that:

```math
c_k=bq+r,
\qquad
0\leq r\leq b-1.
```

Then:

```math
c_kb^k
=
rb^k+qb^{k+1}.
```

The value `r` remains at the `k`-th place and `q` moves to the `k+1`-st place value.

In base ten:

```math
10\cdot10^k
=
1\cdot10^{k+1}.
```

The simplest case is:

```math
10\cdot10^0
=
1\cdot10^1.
```

```text
ten ones
→ one ten
```

---

## 6.2 Second Theorem — Carry Preserves Value

### Theorem

A normalizing place-value carry changes the structure of the active representation while preserving the represented numerical value.

### Proof

Since:

```math
c_k=bq+r,
```

multiplication gives:

```math
c_kb^k
=
(bq+r)b^k
=
qb^{k+1}+rb^k.
```

The two forms have identical numerical value.

QED.

---

## 6.3 Third Theorem — Representational Length Transition

### Theorem

For every `m≥1`:

```math
\ell_b(b^m-1)=m
```

and:

```math
\ell_b(b^m)=m+1.
```

### Proof

For the number `b^m-1`:

```math
b^{m-1}\leq b^m-1<b^m.
```

Therefore, the smallest `r` satisfying:

```math
b^m-1<b^r
```

is exactly `r=m`.

Thus:

```math
\ell_b(b^m-1)=m.
```

The number `b^m` is not smaller than `b^m`, but it is smaller than `b^{m+1}`, so:

```math
\ell_b(b^m)=m+1.
```

QED.

---

# 7. The Finite Place-Value Machine

## 7.1 The Machine with `m` Carriers

Let the complete finite normalized base-`b` machine operating with `m` active place-value carriers be denoted by:

```math
\mathcal M_b^{(m)}.
```

Its state space is:

```math
X_b^{(m)}=D_b^m.
```

Digits are ordered from the lowest to the highest place value:

```math
\mathbf d
=
(d_0,d_1,\ldots,d_{m-1}).
```

The value-reading function is:

```math
V_m(\mathbf d)
=
\sum_{k=0}^{m-1} d_kb^k.
```

The common semantic-state interpretation of the place-value machines is:

```math
\nu_m(\mathbf d)
=
V_m(\mathbf d).
```

The machine with `m` carriers can hold exactly the following values in normalized form:

```math
0\leq V_m(\mathbf d)\leq b^m-1.
```

---

## 7.2 The Partial `+1` Transition

Let the operational signal be:

```math
\sigma=+1.
```

The transition of the machine with `m` carriers is:

```math
T_m(\mathbf d,+1)
=
\mathrm{enc}_m\bigl(V_m(\mathbf d)+1\bigr)
```

when:

```math
V_m(\mathbf d)<b^m-1.
```

The maximum state is:

```math
\mathbf d_m^{\max}
=
(b-1,b-1,\ldots,b-1).
```

For this state:

```math
V_m(\mathbf d_m^{\max})=b^m-1.
```

In the machine with `m` carriers:

```math
T_m(\mathbf d_m^{\max},+1)=\bot,
```

because value `b^m` cannot be represented with `m` normalized digits.

---

## 7.3 Activation of the Higher Carrier

The state space of the machine with `m+1` carriers is:

```math
X_b^{(m+1)}=D_b^{m+1}.
```

The embedding of an `m`-carrier state is:

```math
\iota_m(d_0,\ldots,d_{m-1})
=
(d_0,\ldots,d_{m-1},0).
```

The embedding preserves semantics:

```math
\nu_{m+1}
\bigl(
\iota_m(\mathbf d)
\bigr)
=
\nu_m(\mathbf d).
```

At closure of the complete lower field:

```math
T_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
(0,0,\ldots,0,1).
```

The value of the new state is:

```math
V_{m+1}(0,0,\ldots,0,1)=b^m.
```

The operational unit is:

```math
\kappa_m
=
(h_m,c_{m-1\rightarrow m}),
```

where:

- `h_m` is the newly active carrier of place value `b^m`;
- `c_{m-1→m}` is the carry from the saturated lower field into the higher place value.

---

# 8. Operational Change and Operational Dimension Opening

## 8.1 System Extension

Let the initial machine be:

```math
\mathcal M_0
```

and let a machine containing a new carrier, binding, or transition rule be:

```math
\mathcal M_1
=
\mathcal M_0\oplus\kappa.
```

The new operational unit `κ` may contain:

```text
a new active carrier
a new binding between existing carriers
a new transition rule
or a necessary combination of these
```

Not every new element opens an operational dimension.

Presence is not sufficient.

A changed response is not sufficient by itself either.

---

## 8.2 Witness of Operational Change in a Common Observation Space

A witness of operational change is a state `x` and signal `σ` for which the new machine's response, interpreted in the common semantic observation space, differs from the old machine's response:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\mathcal M_0}(x,\sigma),
```

where `ι` embeds the old state into the new system.

On the witness input state, the embedding must preserve semantic state:

```math
\nu_{\mathcal M_1}
\bigl(
\iota(x)
\bigr)
=
\nu_{\mathcal M_0}(x).
```

The operational difference may arise from:

```text
a previously nonexistent transition
a different semantic target state
a different output
a different consequence
```

A mere internal recoding is insufficient. If two different raw target states map to the same fixed semantic state, produce the same output, and produce the same consequence, then their `B` responses are identical.

This condition proves an operational change.

It does not yet prove that a new operational dimension opened.

---

## 8.3 Removal or Ablation Test

Ablation is not a set-theoretic reduction of the state space or input space.

Let:

```math
\mathcal M_1
=
(X_1,\Sigma_1,H_1,A_1,R_1,T_1,\nu_1,O_1,C_1,Q_1).
```

The ablation of operational unit `κ` is:

```math
\operatorname{Abl}_{\kappa}(\mathcal M_1)
=
(X_1,\Sigma_1,H_1,A_1^{-\kappa},R_1^{-\kappa},T_1^{-\kappa},
\nu_1,O_1,C_1,Q_1).
```

The superscript indicates that the active-carrier, binding, or transition effect of `κ` is disabled wherever it appears in that component.

The transition function of the ablation machine is denoted by:

```math
T_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
:=
T_1^{-\kappa}.
```

The following remain unchanged:

```text
the ambient state space
the ambient input space
the types of state and input
the semantic-state interpretation fixed in advance
the output and consequence interpretations
```

Therefore the same witness state `ι(x)` may be provided to both the complete machine and the ablation machine.

The abbreviation:

```math
\mathcal M_1\setminus\kappa
:=
\operatorname{Abl}_{\kappa}(\mathcal M_1)
```

always denotes this operational disabling in this document, not an actual contraction of the state space.

The operational necessity of the new unit for the observed change is proved when `x,σ` exist such that:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma).
```

This ablation witness shows that the operational effect of `κ` is necessary for the observed response difference.

Ablation alone does not determine whether the difference is new reachability, new discrimination, or a mere uniform output change.

---

## 8.4 Operational Behavior Change

> **An operational behavior change occurs when a new or newly active operational unit changes the system's response at the fixed observation boundary, and its ablation in the same ambient space removes or modifies that change.**

Formally, a witness triple `κ,x,σ` is sufficient when:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\mathcal M_0}(x,\sigma)
```

and:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma).
```

This proves a causal operational change at the examined system boundary.

Not every such change is an operational dimension opening.

---

## 8.5 Reachability Opening

A reachability opening occurs when the new operational unit makes available a valid state path that did not exist in the old machine from the same semantic input state, and the path disappears again under ablation.

The strongest direct witness form is:

```math
B_{\mathcal M_0}(x,\sigma)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}(\iota(x),\sigma)
=
\bigl(
\mathrm{defined},
s,y,z
\bigr),
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma)
=
\mathrm{undefined}.
```

The chain is:

```text
old machine
→ no valid target transition

activation of the new unit
→ a valid target transition is created

ablation in the same ambient space
→ the new reachability disappears
```

This is not a mere response substitution.

A previously nonexistent operational path has become reachable.

The `9 → 10` witness belongs to this class.

---

## 8.6 Discrimination Opening

Let two witness pairs be:

```math
w_1=(x_1,\sigma_1),
\qquad
w_2=(x_2,\sigma_2).
```

The operational response-equivalence relation of the old machine is:

```math
w_1\sim_{\mathcal M_0}w_2
\quad\Longleftrightarrow\quad
B_{\mathcal M_0}(x_1,\sigma_1)
=
B_{\mathcal M_0}(x_2,\sigma_2).
```

The new machine receives the states through the semantics-preserving embedding:

```math
\bar w_j
=
(\iota(x_j),\sigma_j),
\qquad
j\in\{1,2\}.
```

A discrimination opening occurs when:

```math
B_{\mathcal M_0}(x_1,\sigma_1)
=
B_{\mathcal M_0}(x_2,\sigma_2),
```

while:

```math
B_{\mathcal M_1}(\iota(x_1),\sigma_1)
\neq
B_{\mathcal M_1}(\iota(x_2),\sigma_2),
```

and the new distinction disappears under ablation of `κ`:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_1),\sigma_1)
=
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_2),\sigma_2).
```

This proves that the new operational unit separated cases that had previously been treated as operationally identical.

In relational form, the new machine's response-equivalence classification is strictly finer on the two-point witness domain.

Let:

```math
W
=
\{\bar w_1,\bar w_2\}.
```

Then:

```math
\ker\!\left(
B_{\mathcal M_1}\big|_W
\right)
\subsetneq
\ker\!\left(
\widetilde B_{\mathcal M_0}\big|_W
\right),
```

where the old response lifted into the new ambient space is:

```math
\widetilde B_{\mathcal M_0}(\iota(x),\sigma)
:=
B_{\mathcal M_0}(x,\sigma).
```

The strict-refinement claim here applies only to the fixed witness domain. A global kernel-refinement claim would additionally require proof that the new machine does not merge other response classes.

A discrimination opening does not require new external information. A new authority-bearing or transition rule created among existing data may separate cases that were previously treated identically.

The PULSEmech required-gate `PASS/BLOCK` witness belongs to this class.

---

## 8.7 Precise Definition of Operational Dimension Opening

> **An operational dimension opening occurs when a new or newly active carrier, binding, or transition rule creates new reachability or a new operational discrimination at the fixed observation boundary, and its ablation in the same ambient space removes that reachability or discrimination.**

Accordingly, this document recognizes two proof-witness classes for operational dimension opening:

```text
reachability witness
or
discrimination witness
```

A mere uniform output change is insufficient.

For example:

```text
ALLOW for every input
→ under a new rule, BLOCK for every input
→ after ablation, ALLOW for every input again
```

is an operational change with ablation dependence.

If no previously nonexistent state path was created and the system did not separate cases that it had previously treated identically, then under this document's definition, the change is not an operational dimension opening.

Therefore:

```text
response change
+ ablation effect
→ operational behavior change

new reachability
or
new operational discrimination
+ ablation effect
→ operational dimension opening
```

A binding alone is not proof.

Its operation is proof.

An operational dimension opening is proved not by just any operational change, but by new reachability or new discrimination capability.

---

# 9. Operational Proof of the Decimal Opening

## 9.1 The Old Machine

Let:

```math
b=10,
\qquad
m=1.
```

The two complete machines in the proof are:

```math
\mathcal M_1
:=
\mathcal M_{10}^{(1)},
\qquad
\mathcal M_2
:=
\mathcal M_{10}^{(2)}.
```

The only active place value is the ones place:

```math
A_{10}^{(1)}=\{h_0\}.
```

The state space is:

```math
X_{10}^{(1)}=D_{10}.
```

The semantic-state interpretation is:

```math
\nu_1(d_0)=d_0.
```

The maximum state is:

```math
x=9.
```

Under signal `+1`, in the one-place normalized machine:

```math
T_1(9,+1)=\bot.
```

Therefore:

```math
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined}.
```

`10` is not a permitted digit in the ones place:

```math
10\notin D_{10}.
```

---

## 9.2 The New Operational Unit

The new operational unit is:

```math
\kappa_1
=
(h_1,c_{0\rightarrow1}).
```

Its components are:

```text
h₁
→ active carrier of the tens place

c₀→₁
→ carry from the ones place into the tens place
```

The old state is embedded as:

```math
\iota_1(9)=(9,0).
```

The semantic-state interpretation of the two-carrier machine is:

```math
\nu_2(d_0,d_1)
=
d_0+10d_1.
```

The embedding preserves the meaning of the initial state:

```math
\nu_2(9,0)
=
9
=
\nu_1(9).
```

The transition of the new machine is:

```math
T_2((9,0),+1)=(0,1).
```

The new semantic target state is:

```math
\nu_2(0,1)
=
V_2(0,1)
=
0\cdot10^0+1\cdot10^1
=
10.
```

The complete operational response is:

```math
B_{\mathcal M_2}((9,0),+1)
=
\bigl(
\mathrm{defined},
10,
O_2(0,1),
C_2((9,0),+1,(0,1))
\bigr).
```

The difference does not follow from the difference between raw state vectors `(9)` and `(0,1)`. In the old machine the transition does not exist; in the new machine it is defined and its fixed semantic state is `10`.

---

## 9.3 Ablation Proof

The ablation runs retain the ambient state space of the two-carrier machine:

```math
X_{10}^{(2)}=D_{10}^2.
```

Therefore `(9,0)` is a well-typed input in the complete machine and in every two-carrier ablation run.

With the higher carrier operationally disabled:

```math
T_{\operatorname{Abl}_{h_1}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

With the carry operationally disabled:

```math
T_{\operatorname{Abl}_{c_{0\rightarrow1}}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

With the complete new unit ablated:

```math
T_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

With the complete new unit active:

```math
T_2((9,0),+1)=(0,1).
```

The observed responses are:

```math
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_2}((9,0),+1)
=
\bigl(
\mathrm{defined},
10,
O_2(0,1),
C_2((9,0),+1,(0,1))
\bigr),
```

```math
B_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\mathrm{undefined}.
```

Therefore:

```text
9
→ saturated ones field

+1
→ no valid normalized successor in the ones place

carry
→ the tens place enters operation

new carrier + new binding
→ the semantic state 10 becomes producible

ablation in the same ambient space
→ state 10 again cannot be produced through this mechanical path
```

The `9 → 10` transition is therefore more than a change in digit length.

The representational measurement is:

```math
\ell_{10}(9)=1,
\qquad
\ell_{10}(10)=2.
```

The operational proof is:

```math
T_1(9,+1)=\bot,
```

```math
T_2((9,0),+1)=(0,1),
```

```math
T_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

---

## 9.4 Fourth Theorem — Operational Opening at the Place-Value Threshold

### Theorem

In a finite normalized base-`b` place-value machine, the transition:

```math
b^m-1
\longrightarrow
b^m
```

requires activation of the `m`-th higher place value and the carry leading into it.

Under the Workshop definition, this operational unit creates a reachability opening and therefore opens an operational dimension.

### Proof

The largest value representable by the machine with `m` carriers is:

```math
b^m-1.
```

Therefore:

```math
T_m(\mathbf d_m^{\max},+1)=\bot.
```

In the machine with `m+1` carriers, activation of the new carrier and the carry gives:

```math
T_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
(0,\ldots,0,1).
```

Its value is:

```math
b^m.
```

After ablation of the complete operational unit `\kappa_m=(h_m,c_{m-1\rightarrow m})` in the same ambient state space `X_b^{(m+1)}`:

```math
T_{\operatorname{Abl}_{\kappa_m}(\mathcal M_b^{(m+1)})}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
\bot.
```

The same conclusion follows if either the operational participation of the new carrier `h_m` or the carry `c_{m-1→m}` is disabled separately.

The embedding preserves the semantic value of the old state:

```math
\nu_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max})
\bigr)
=
\nu_m(\mathbf d_m^{\max})
=
b^m-1.
```

The semantic target state of the new transition is:

```math
\nu_{m+1}(0,\ldots,0,1)=b^m.
```

The new operational unit therefore:

- becomes active;
- enters the transition mechanism;
- is necessary for the target state;
- carries an effect provable by ablation in the same ambient space.

QED.


---

# 10. Not Every Carry Opens a New Operational Dimension

If the higher place value is already active, a later carry may use the existing carrier and binding without activating a new carrier.

For example:

```text
19
→ 20
```

The tens place is already active in the initial state.

The transition changes the digits but does not increase the number of minimally active place values:

```math
\ell_{10}(19)=2,
\qquad
\ell_{10}(20)=2.
```

The next activation of a new carrier occurs at:

```text
99
→ 100
```

because:

```math
\ell_{10}(99)=2,
\qquad
\ell_{10}(100)=3.
```

Therefore:

```text
carry
≠ automatically a new operational dimension

carry into a new necessary higher carrier
+ previously nonexistent state path
+ reachability witness
+ ablation in the same ambient space
→ operational dimension opening
```

---

# 11. Informational Novelty and Operational Novelty

## 11.1 Functional Informational Independence

Let the existing state description be:

```math
P:X\rightarrow U
```

and a new coordinate be:

```math
h:X\rightarrow H_h.
```

Coordinate `h` carries functionally new information relative to `P` if no function exists:

```math
f:P(X)\rightarrow H_h,
```

such that:

```math
h=f\circ P.
```

Formally:

```math
\nexists f:P(X)\rightarrow H_h
\quad\text{such that}\quad
h=f\circ P.
```

Its witness form is:

```math
\exists x,y\in X:
P(x)=P(y)
\land
h(x)\neq h(y).
```

This is functional or informational independence.

It is not linear-algebraic independence.

It is not probabilistic independence.

---

## 11.2 Refinement of State Classes

The identity relation induced by description `P` is:

```math
\ker P
=
\{(x,y)\in X^2:P(x)=P(y)\}.
```

The new description is:

```math
P_h=(P,h).
```

The new coordinate creates informational state-space expansion if:

```math
\ker P_h
\subsetneq
\ker P.
```

This means that the new description distinguishes states that the old description treated as identical.

---

## 11.3 Informational Novelty Is Not Sufficient for Operation

A new coordinate may be informationally novel while neither the transition nor the decision mechanism uses it.

Then:

```text
new information
→ new description
→ no new operational path
```

It is possible that:

```math
\ker P_h\subsetneq\ker P
```

while, for every `x,σ`:

```math
B_{\mathcal M_h}(x,\sigma)
=
B_{\mathcal M}(x,\sigma).
```

Therefore:

```text
informational novelty
≠ operational dimension opening
```

---

## 11.4 Operational Novelty Does Not Require New External Information

A new operational relation may be created among existing data.

Let:

```math
g=(g_1,g_2)
```

and let a derived coordinate be:

```math
h(g)=g_1\land g_2.
```

The coordinate `h` is fully derivable from `g`.

It is not informationally independent.

Let two old states be:

```math
g^{(1)},
\qquad
g^{(2)},
```

such that:

```math
h(g^{(1)})=1,
\qquad
h(g^{(2)})=0.
```

If the old decision system treats the two cases identically:

```math
D_0(g^{(1)})
=
D_0(g^{(2)}),
```

while the new authority-bearing rule is:

```math
D_1(g)
=
\begin{cases}
\mathrm{ALLOW}, & h(g)=1,\\
\mathrm{BLOCK}, & h(g)=0,
\end{cases}
```

then:

```math
D_1(g^{(1)})
\neq
D_1(g^{(2)}).
```

If, after ablation of the authority rule bound to `h`, the two cases again receive the same decision:

```math
D_{\operatorname{Abl}_{\kappa}}
(g^{(1)})
=
D_{\operatorname{Abl}_{\kappa}}
(g^{(2)}),
```

then a complete discrimination witness exists.

No new external information arrived.

A new authority-bearing relation became operative among existing information and separated states that had previously been treated identically.

Therefore:

```text
a functionally new coordinate
is not a necessary condition
for operational dimension opening
```

The decisive condition is new reachability or new operational discrimination, together with necessity established through ablation.

---

# 12. New Relation and New Dimension

The simple form:

```text
new relation
→ new dimension
```

is incomplete.

A new relation may be:

- declared but inactive;
- redundant;
- unreachable;
- incorrectly bound;
- output-inert;
- without consequence.

The technical form is:

```text
new or newly active relation
+ entry into the transition mechanism
+ reproducible reachability or discrimination witness
+ ablation in the same ambient space
+ observable semantic state, output, or consequence
→ operational dimension opening
```

A relation alone is not proof.

Its operation is proof.

---

# 13. The Role of a Quantitative Threshold

A quantitative value may reach a threshold that activates a new carrier or rule.

Let:

```math
Q(x)\geq q_*.
```

The inequality alone does not create a new mechanism.

The system must contain an activation rule:

```math
Q(x)\geq q_*
\;\Longrightarrow\;
\text{activate }\kappa.
```

The complete chain is:

```text
quantitative coordinate increases
→ threshold is met
→ activation rule executes
→ new carrier or binding becomes operative
→ new transition becomes reachable
```

The larger number alone does not create the opening.

The mechanism bound to the threshold and actually executed creates an operational change. It proves an operational dimension opening only when it is also established by a reachability or discrimination witness and by ablation in the same ambient space.

In the decimal machine, the threshold is:

```math
d_k=b-1
```

and addition of the next unit initiates the carry.

---

# 14. Separating Unboundedness from Dimension

## 14.1 Workshop-Machine Counterexample

Let a state sequence be:

```math
x_0,x_1,x_2,\ldots
```

such that:

```math
Q(x_n)=n
```

and:

```math
\Omega_{\mathcal M}(x_n)=\omega
```

for every `n`.

Then:

```math
Q(x_n)\longrightarrow\infty,
```

while no new operational signature is created.

This is a direct counterexample to the false implication:

```math
\text{unbounded quantitative growth}
\;\Longrightarrow\;
\text{operational dimension growth}.
```

---

## 14.2 Vector-Space Counterexample

Let `V` be a normed vector space and:

```math
v\in V,
\qquad
v\neq 0.
```

Define:

```math
x_n=nv.
```

Then:

```math
\lVert x_n\rVert
=
n\lVert v\rVert
\longrightarrow\infty.
```

The complete sequence remains within a single one-dimensional subspace:

```math
\mathrm{span}\{x_n:n\in\mathbb N\}
=
\mathrm{span}\{v\}.
```

Therefore:

```math
\dim
\mathrm{span}\{x_n:n\in\mathbb N\}
=1.
```

Within a specified mathematical model, this example proves that unbounded magnitude does not force a higher vector-space dimension.

It does not define the Workshop concept of operational dimension.

It serves as a checking counterexample.

---

## 14.3 Fifth Theorem — The Infinity Symbol Does Not Open a Mechanism

The notation:

```math
x_n\longrightarrow+\infty
```

describes unboundedness under a chosen definition.

It does not automatically create:

```text
a new carrier
a new binding
a new transition rule
a new output
a new consequence
```

Therefore:

```text
∞
≠ new operational dimension

unbounded linear path
≠ expansion
```

Infinity may be an unbounded quantitative traversal of the same mechanical state class.

---

# 15. Separating Formula from Mechanism

At least three layers must be separated when examining a formal expression:

```text
syntax
→ which symbols constitute the expression

semantics
→ what the symbols mean in the selected model

mechanism
→ which state, binding, transition, and consequence the system creates
```

Mere insertion of a symbol changes only the syntactic structure by itself.

Under fixed semantics, the modification may change the expression's meaning or truth value.

A new operational mechanism still does not follow from this alone.

A mechanical result requires:

```text
defined interpretation
operation
state binding
transition path
reproducible output
proved consequence
```

Therefore:

```text
notation
≠ result

formula
≠ operating machine

assumption
≠ proof

symbol
≠ state transition
```

---

# 16. “Acquired” Is Not a Terminal State

## 16.1 Terminal State

A state `x` is terminal if no operational signal has a valid next state:

```math
\forall\sigma\in\Sigma:
T(x,\sigma)=\bot.
```

The label “acquired” or “obtained” does not by itself prove that a state is terminal.

An actual lifecycle may be:

```text
absent
→ acquired
→ bound into the system
→ in use
→ maintained
→ modified or degraded
→ withdrawn
```

If the model stops here:

```text
absent
→ became present
→ acquired
→ end
```

then the actual process did not end.

The state model was truncated.

---

## 16.2 Consequence of the Truncated Model

If bindings and consequences after acquisition are not represented, the remaining visible motion is:

```text
one is acquired
→ two are acquired
→ three are acquired
→ still more are acquired
```

This is a quantitative axis.

It is not a lifecycle.

It is not new operation.

---

# 17. The Princess-Dress Example

Let the object type be:

```math
\tau
=
\text{“princess dress”}.
```

Let the state be:

```math
x_n=(\tau,n),
```

where `n` is the item count.

If:

```math
Q(x_n)=n
```

and:

```math
\Omega_{\mathcal M}(x_n)=\omega
```

for every `n`, then:

```text
one princess dress
→ ten princess dresses
→ one thousand princess dresses
```

is quantitative growth.

The operational signature did not change.

Therefore:

> **Multiplying a stagnant structural identity is a quantitative increase of the stagnant structure.**

If the quantity activates a new storage, maintenance, distribution, or use relation, the operational witness and ablation test must be examined separately.

Neither conclusion follows from item count alone.

---

# 18. The Workshop Four-Layer Calculation Order

## 18.1 Quantitative Growth

```text
the value of an existing Q coordinate increases
```

Formally:

```math
Q(y)>Q(x).
```

This is only a quantitative fact.

---

## 18.2 Representational Length Transition

```text
the minimum place-value length of the normalized description increases
```

When the semantic values of the examined states are natural numbers, formally:

```math
\ell_b\bigl(\nu(y)\bigr)
>
\ell_b\bigl(\nu(x)\bigr).
```

This is a signal of representational change and carrier activation in the finite place-value machine.

---

## 18.3 Informational State-Space Expansion

```text
the new description distinguishes states that were previously identical
```

Formally:

```math
\ker P_h\subsetneq\ker P.
```

This is a new informational discrimination.

---

## 18.4 Operational Dimension Opening

Within the operational layer, two distinct claims must be separated:

```text
change in operational response
≠ automatically an operational dimension opening
```

An operational dimension opening is proved by one of the following two witness classes.

### Reachability Witness

```math
B_{\mathcal M_0}(x,\sigma)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
\mathrm{undefined},
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma)
=
\mathrm{undefined}.
```

### Discrimination Witness

There exist witnesses `w_1=(x_1,\sigma_1)` and `w_2=(x_2,\sigma_2)` such that:

```math
B_{\mathcal M_0}(x_1,\sigma_1)
=
B_{\mathcal M_0}(x_2,\sigma_2),
```

```math
B_{\mathcal M_1}(\iota(x_1),\sigma_1)
\neq
B_{\mathcal M_1}(\iota(x_2),\sigma_2),
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_1),\sigma_1)
=
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_2),\sigma_2).
```

Therefore:

```text
new state path
or
new operational discrimination
+ necessity established through ablation
→ operational dimension opening
```


---

# 19. PULSEmech Application

## 19.1 Quantity and Release Authority

Let:

```math
E
```

be the set of evidence records,

```math
A_r
```

be the set of artifacts,

and:

```math
G
```

be the set of declared gates.

The following increases do not by themselves prove a new release-decision capability:

```math
|E'|>|E|,
```

```math
|A_r'|>|A_r|,
```

```math
|G'|>|G|.
```

Therefore:

```text
more evidence
≠ automatically stronger release authority

more artifacts
≠ automatically a new decision dimension

more gates
≠ automatically more decision capability
```

---

## 19.2 Candidate and Advisory Gates

Let `g` be the old authority-bearing gate state and `h` a new gate candidate.

The complete operational response of release authority is:

```math
B_{\mathrm{auth}}(g)
=
\bigl(
\Theta_{\mathrm{release}}(g),
D_{\mathrm{release}}(g),
C_{\mathrm{release}}(g)
\bigr).
```

The extended system is:

```math
B'_{\mathrm{auth}}(g,h).
```

The gate has no release-authority effect if, for every permitted `g,h`:

```math
B'_{\mathrm{auth}}(g,h)
=
B_{\mathrm{auth}}(g).
```

An equivalent factorization form is:

```math
B'_{\mathrm{auth}}
=
B_{\mathrm{auth}}\circ\pi_G,
```

where:

```math
\pi_G(g,h)=g.
```

In architectural form:

```math
h
\not\leadsto
\{D_{\mathrm{release}},
\Theta_{\mathrm{release}},
C_{\mathrm{release}}\}.
```

That is, there is no data or control path from `h` to an authority-bearing sink.

The complete PULSE boundary is:

```text
candidate or advisory gate
+ not in the active materialized required gate set
+ no data or control path to an authority-bearing sink
→ no release-authority effect
```

---

## 19.3 Active PULSEmech Dimension

A structural precondition for an operational release dimension is that the following authority-bearing chain actually be created:

```text
gate state
→ current-run evidence binding
→ artifact binding
→ policy binding
→ materialized required gate state
→ deterministic verifier
→ fail-closed gate evaluation
→ ALLOW or BLOCK consequence
```

The presence of the chain alone is not proof of a dimension opening. Proof requires a reachability or discrimination witness.

A PULSEmech required gate typically provides a discrimination-opening witness.

Let `\mathcal A_0` be the old authority machine and `\mathcal A_1` the new authority machine.

Let the old authority function be:

```math
B_{\mathrm{auth},0}:G\rightarrow\mathcal B_{\mathrm{auth}}.
```

Let:

```math
\mathcal H_h
```

be the set of permitted states of the new gate `h`.

The function extended with the new gate is:

```math
B_{\mathrm{auth},1}
:
G\times\mathcal H_h
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

The old system lifted onto the new gate axis is:

```math
\widetilde B_{\mathrm{auth},0}
:=
B_{\mathrm{auth},0}\circ\pi_G,
```

where:

```math
\pi_G(g,h)=g.
```

The old system does not distinguish the two values of gate `h`:

```math
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{PASS})
=
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{FAIL}).
```

In the new system, the active materialized required gate creates a distinction:

```math
B_{\mathrm{auth},1}
(g_*,h=\mathrm{PASS})
\neq
B_{\mathrm{auth},1}
(g_*,h=\mathrm{FAIL}).
```

On the decision projection, for example:

```math
D_{\mathrm{release},1}
(g_*,h=\mathrm{PASS})
=
\mathrm{ALLOW},
```

```math
D_{\mathrm{release},1}
(g_*,h=\mathrm{FAIL})
=
\mathrm{BLOCK}.
```

Ablation of the authority-bearing binding removes the new distinction:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{PASS})
=
B_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{FAIL}).
```

In a fail-closed system, its typical decision form is:

```math
D_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{PASS})
=
D_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{FAIL})
=
\mathrm{BLOCK}.
```

This proves that the new gate did not merely change all outputs of the system. It separated gate states that had previously been treated identically within the authority-bearing transition.

The decisive relation is:

```text
new gate name
≠ new release dimension

new gate file
≠ new release dimension

new or newly active gate binding
+ materialized required state
+ verifier
+ separation of gate states previously treated identically
+ discrimination removed by fail-closed ablation
→ active operational release dimension
```

A PULSEmech extension may also create a reachability opening if it makes a previously nonexistent valid release transition reachable. The gate `PASS/BLOCK` example proves the discrimination class.

---

## 19.4 Derived Gate

A gate may be fully derivable from existing evidence.

It may still create a new operational release relation if it becomes part of a previously nonexistent authority-bearing rule.

Therefore, informational independence is not a necessary condition for operational dimension opening in PULSEmech.

The necessary operational condition is:

```text
new or newly active authority-bearing binding
+ previously nonexistent release reachability
  or
  a new release discrimination between states previously treated identically
+ reproducible decision effect
+ fail-closed ablation witness
```

A derived gate may therefore open an operational dimension not as new data, but as a new operational relation.

---

# 20. Reproducible Proof Package

A claim of operational dimension opening is complete only if the proof contains at least the following records:

```text
before_state
→ exact identification of the initial machine and state

change_unit
→ exact identification of the new carrier, binding, or rule

activation_path
→ the path by which the new unit enters operation

witness_class
→ reachability_opening or discrimination_opening

comparison_domain
→ the fixed state–input domain over which the reachability or discrimination claim holds

witness_input
→ for a reachability witness, the input or signal on which the new state path appears

witness_pair
→ for a discrimination witness, the two state–input pairs treated identically by the old machine and differently by the new machine

observation_boundary
→ the fixed semantic state space and the output and consequence interpretations

embedding_preservation
→ proof that embedding the old witness state into the new machine does not change its meaning

ambient_ablation_contract
→ specification that ablation disables the new unit while retaining the same state and input types

before_response
→ the operational response or response-equivalence relation of the old machine

after_response
→ the operational response or new response discrimination of the new machine

ablation_response
→ the response or response equivalence after operationally disabling the new unit in the same ambient space

semantic_state_output_and_consequence
→ the difference in semantic target state, output, and consequence

non_opening_change_exclusion
→ proof that the change was not merely the same uniform output substitution for every input

identity_and_binding
→ artifact, run, and policy binding of the proof subject

external_theorem_transfer_contract
→ when an external theorem is used, proof of the relevant external substructure, theorem identification, structure preservation, and the required direction of reflection

replay
→ deterministic replay of the same result
```

The minimum logical order for a reachability proof is:

```text
the state path does not exist before activation
→ activation creates it
→ ablation in the same ambient space removes it
→ replay produces the same result
```

The minimum logical order for a discrimination proof is:

```text
before activation, two cases receive the same operational response
→ activation gives them different operational responses
→ ablation in the same ambient space removes the new difference
→ replay produces the same result
```

The proof order for a mere operational change is weaker:

```text
old response: r₀
→ new response under activation: r₁, where r₁ ≠ r₀
→ under ablation, response r₁ disappears or changes
```

This alone is not an operational dimension opening.

The proof package must therefore record the witness class as well.

---

# 21. Main Theorem

## The Theorem of the Workshop Decimal Number System and Operational Dimension Opening

Let:

```math
\mathcal M
=
(X,\Sigma,H,A,R,T,\nu,O,C,Q)
```

be a Workshop machine.

Then the following claims hold separately.

### I. Quantitative Growth

```math
Q(y)>Q(x)
```

does not by itself prove a new operational signature:

```math
Q(y)>Q(x)
\not\Rightarrow
\Omega_{\mathcal M}(y)
\neq
\Omega_{\mathcal M}(x).
```

### II. Representational Length Transition

In a finite normalized base-`b` place-value machine:

```math
\ell_b(b^m-1)=m,
```

```math
\ell_b(b^m)=m+1.
```

Crossing the threshold requires a higher active place-value carrier.

### III. Informational Expansion

A new coordinate `h` expands the state description informationally if:

```math
\ker(P,h)
\subsetneq
\ker P.
```

This is neither sufficient for operational dimension opening nor necessary for every operational opening.

### IV. Operational Behavior Change

Let:

```math
\mathcal M_1
=
\mathcal M_0\oplus\kappa.
```

If `x,σ` exist such that:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\mathcal M_0}(x,\sigma)
```

and:

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma),
```

then `κ` creates a change proved in operation at the examined system boundary.

This alone does not prove an operational dimension opening.

### V. Operational Dimension Opening

An operational dimension opening is proved by at least one of the following two witness classes.

#### V.a Reachability Opening

If `κ,x,σ` exist such that:

```math
B_{\mathcal M_0}(x,\sigma)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}(\iota(x),\sigma)
\neq
\mathrm{undefined},
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x),\sigma)
=
\mathrm{undefined},
```

then `κ` made a previously nonexistent operational path reachable, and ablation proves its necessity.

#### V.b Discrimination Opening

If witnesses `w_1=(x_1,\sigma_1)` and `w_2=(x_2,\sigma_2)` exist such that:

```math
B_{\mathcal M_0}(x_1,\sigma_1)
=
B_{\mathcal M_0}(x_2,\sigma_2),
```

```math
B_{\mathcal M_1}(\iota(x_1),\sigma_1)
\neq
B_{\mathcal M_1}(\iota(x_2),\sigma_2),
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_1),\sigma_1)
=
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}
(\iota(x_2),\sigma_2),
```

then `κ` separated cases that had previously been treated identically, and ablation proves its necessity.

A common condition for both witness classes is that the `B` responses be interpreted in a common observation space fixed in advance, the embedding preserve the meaning of the old witness state, and ablation take place in the same ambient state and input spaces.

A uniform output substitution identical for every input may be an operational change, but it satisfies neither witness class. It is therefore not an operational dimension opening.

### VI. The First Decimal Opening

In the `9 → 10` transition:

```math
T_1(9,+1)=\bot,
```

```math
T_2((9,0),+1)=(0,1),
```

and:

```math
T_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\bot.
```

The embedding preserves the meaning of the initial state, and the semantic value of the new target state is `10`:

```math
\nu_1(9)
=
\nu_2(9,0)
=
9,
\qquad
\nu_2(0,1)=10.
```

In the common observation space:

```math
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_2}((9,0),+1)
=
\bigl(
\mathrm{defined},
10,
O_2(0,1),
C_2((9,0),+1,(0,1))
\bigr),
```

```math
B_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\mathrm{undefined}.
```

This is a reachability opening.

The tens place and the carry leading into it form the operational unit necessary to produce the target state. The witness is not established by the difference between raw state vectors, but by the transition that was previously undefined, then created, and then removed again by ablation.

### VII. Boundary of an External Theorem

A statement proved in an external model may govern a conclusion about the Workshop machine only if two distinct requirements are met:

```text
1. preservation of the carrier, binding, state, input, semantic-state, transition, output, and consequence structures is proved;

2. preservation of the property stated in the concrete theorem, and its reflection in the required direction, are also proved.
```

Historical acceptance substitutes for neither proof.

---

## Proof Summary

A counterexample separates quantitative growth from a change in operational signature.

The place-value length transition at threshold `b^m-1 → b^m` follows directly from the normalized base-`b` representation.

A changed operational response together with ablation dependence proves a causal operational behavior change, but does not by itself prove a new operational dimension.

A reachability witness establishes a previously nonexistent state path. A discrimination witness establishes a new separation between cases previously treated identically. In both witness classes, ablation proves the necessity of the new operational unit.

In the finite place-value machine, the old system with `m` carriers cannot produce state `b^m`. Activation of the new `m+1`-st carrier and the carry leading into it produces the target state. Ablation of the new unit in the same ambient space removes the transition again.

This provides both a reachability witness and a necessity witness.

Informational expansion is separately measurable as refinement of a relation. Operational opening follows not from informational novelty, but from the actual effect of a new or newly active carrier–binding–transition unit that creates new reachability or a new discrimination.

The applicability of an external theorem is determined not by its age or acceptance, but by proof of operation preservation and transfer of the specific property.

QED.

---

# 22. The Workshop Calculation Order

The Workshop does not stop at the question:

> How much did it become?

The complete examination order is:

```text
1. Which quantitative coordinate changed?

2. Which complete finite range closed?

3. Did the minimum length of the normalized representation increase?

4. Which carrier became active?

5. Which binding introduced the new carrier into the transition?

6. At which common semantic observation boundary are the machines compared?

7. Does the embedding preserve the meaning of the old witness state?

8. What was the old machine's response to the same input?

9. What is the new machine's response at the same observation boundary?

10. Which witness class does the change satisfy?
    - reachability opening
    - discrimination opening
    - or only operational behavior change

11. For a reachability witness: was a previously nonexistent valid state path created?

12. For a discrimination witness: which cases previously treated identically were separated by the new mechanism?

13. What happens when the new carrier or binding is ablated in the same ambient space?

14. Does ablation remove the new reachability or new discrimination?

15. Can it be excluded that only the same uniform output substitution occurred for every input?

16. Which semantic target state, output, or consequence changed?

17. Can the same transition or discrimination be reproduced with identical bindings and the same observation boundary?

18. When an external theorem is used, is each of the following proved separately:
    - the operation-preserving correspondence;
    - transfer of the specific property and its required reflection?
```

The examination does not accept mere item-count growth, representational difference, recoding, or uniform output substitution as a dimension opening.

---

# 23. Workshop Theorem

> **Numbers do not open merely because they become larger.**
>
> **The finite place-value machine opens when, after a complete digit range has been exhausted, a higher carrier and the carry leading into it become necessary to produce a previously nonexistent normalized state path.**
>
> **An operational system opens when a new or newly active carrier, binding, or rule makes a new state path reachable or separates cases previously treated identically, and ablation in the same ambient space removes that new reachability or discrimination.**

In compact form:

```text
accumulation
→ quantitative growth

place-value threshold
→ representational length transition

new descriptive coordinate
→ possible informational expansion

response change
+ ablation effect
→ operational behavior change

new active carrier or binding
+ previously nonexistent state path
  or
  new separation of cases previously treated identically
+ fixed observation boundary
+ ablation in the same ambient space
→ operational dimension opening
```

The Workshop does not call a change an operational dimension opening when it merely performs the same output substitution for every input without new reachability or new discrimination.

An external theorem may determine a conclusion about the Workshop machine only when transfer of the specific theorem property is proved in addition to an operation-preserving correspondence.

---

# 24. The Workshop Principle

> **In the Workshop, we calculate in the decimal number system.**
>
> **The `0–9` range is the complete, inspectable normalized state space of one place value.**
>
> **After the range has been exhausted, we do not force the next value into the old carrier.**
>
> **We perform a carry, activate a higher place value, and prove operationally that the new binding is necessary for the previously nonexistent state path.**
>
> **Expansion is determined neither by item count, notation, a uniform output substitution, nor a previously accepted view.**
>
> **Expansion is proved by new reproducible reachability or discrimination capability that disappears when disabled in the same ambient space.**
>
> **A binding alone is not proof. Its operation is proof.**
>
> **An external theorem may become governing in the Workshop machine only through proved operation preservation, property transfer, and reflection in the required direction.**
