# The Workshop Decimal Number System

## A mathematical and operational theorem separating accumulation, place-value carry, and operational dimension opening

```yaml
document_id: pulsemech_workshop_decimal_accumulation_and_dimension_opening_theorem_en_v0
document_status: foundational_workshop_theorem
language: en
version: v0
revision_state: formal_mechanical_closure
scope: workshop_mathematical_and_operational_foundation
normative_policy_effect: none
release_authority_effect: none
gate_activation_effect: none
```

---

## 0. Subject of the document

This document separates four distinct phenomena:

```text
quantitative growth
≠ representational length transition
≠ informational state-space expansion
≠ operational dimension opening
```

The starting theorem is:

> **Growth is not identical to expansion.**

The value of a quantitative coordinate may increase while the system's operational capability profile remains unchanged.

The decimal place-value machine shows that after a finite normalized digit range has closed, the next value requires:

```text
a higher ambient carrier
→ state-dependent activation
→ an actually used carry
→ a new valid transition that did not previously exist
```

This document does not assign vector-space dimension to the `9 → 10` transition.

Its own operational claim is:

> **In the finite normalized place-value machine, the `9 → 10` transition is a reachability opening because without the higher place-value carrier and the carry leading into it, the semantic target state `10` cannot be produced through the same fixed mechanical path.**

A further distinction applies within the operational layer:

```text
operational behavior change
≠ operational dimension opening
```

Operational dimension opening may be proved by two witness classes:

```text
reachability opening
discrimination opening
```

In both cases, ablation of the new operational unit in the same ambient space must remove the newly created reachability or discrimination.

---

# 1. The Workshop simple machine

## 1.1 The model

The Workshop machine is described by the following system:

```math
\mathcal M
=
(X,\Sigma,H,A,R,T,U,\nu,O,C,Q).
```

Its components are:

```text
X
→ ambient state space

Σ
→ space of inputs or operational signals

H
→ set of ambient carriers

A : X → 2^H
→ carriers active in the given state

R : X×Σ → 2^(H×H)
→ bindings enabled in the given state under the given signal

T : X×Σ ⇀ X
→ partial transition function

U : Γ_T → 2^(H×H)
→ bindings actually used by the realized transition

ν : X → 𝒮
→ fixed semantic-state interpretation

O : X → Y
→ output function

C : X×Σ×X → Z
→ consequence function

Q : X → 𝒬
→ quantitative coordinate in an ordered quantitative space
```

The graph of the partial transition function is:

```math
\Gamma_T
=
\{
(x,\sigma,x')\in X\times\Sigma\times X
:
T(x,\sigma)=x'
\}.
```

The function `U` is defined only for realized transitions:

```math
U:
\Gamma_T
\rightarrow
2^{H\times H}.
```

This separates:

```text
ambient architecture
→ H

carrier active in a state
→ A(x)

binding enabled under a signal
→ R(x,σ)

binding actually used by the concrete transition
→ U(x,σ,x')
```

A binding's operational participation is therefore proved not by its mere presence, but by the `U` record bound to the realized transition.

---

## 1.2 Ambient, active, and nonzero carriers

A carrier may belong to the ambient architecture without yet being active in the current state.

```text
ambient carrier
≠ active carrier

active carrier
≠ carrier holding a nonzero value
```

Activity means operational participation.

A carrier is active in state `x` when the fixed state structure and transition mechanism use it to interpret or continue the state:

```math
h\in A(x).
```

An active carrier may currently hold zero.

The set of elements holding nonzero values is a separate object:

```math
N(x)
\subseteq
A(x).
```

This distinction is required for an exact description of the place-value machine and of PULSEmech gate state.

---

## 1.3 Common observation space

Raw state vectors of machines with different internal state spaces cannot serve as decisive comparison witnesses.

The produced target state must be mapped into a common semantic space:

```math
\nu_{\mathcal M}
:
X_{\mathcal M}
\rightarrow
\mathcal S.
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

The common response space is:

```math
\mathcal B
=
\{\mathrm{undefined}\}
\sqcup
\Bigl(
\{\mathrm{defined}\}
\times
\mathcal S
\times
Y
\times
Z
\Bigr).
```

The complete operational response is:

```math
B_{\mathcal M}(x,\sigma)
=
\begin{cases}
\bigl(
\mathrm{defined},
\nu_{\mathcal M}(x'),
O_{\mathcal M}(x'),
C_{\mathcal M}(x,\sigma,x')
\bigr),
&
\text{if }T_{\mathcal M}(x,\sigma)=x',
\\[8pt]
\mathrm{undefined},
&
\text{if }T_{\mathcal M}(x,\sigma)
\text{ is undefined.}
\end{cases}
```

The symbol `\bot` abbreviates transition undefinedness:

```math
T(x,\sigma)=\bot
\quad\Longleftrightarrow\quad
B_{\mathcal M}(x,\sigma)
=
\mathrm{undefined}.
```

The complete response compares:

```text
whether the transition exists
its semantic target state
its output
its consequence
```

A different internal encoding alone does not prove an operational opening.

---

## 1.4 State and input embeddings

Let:

```math
\mathcal M_0
=
(X_0,\Sigma_0,\ldots)
```

be the old machine, and:

```math
\mathcal M_1
=
(X_1,\Sigma_1,\ldots)
```

be the new machine.

The embedding of old states is:

```math
\iota_X:
X_0
\rightarrow
X_1.
```

The embedding of old inputs is:

```math
\iota_\Sigma:
\Sigma_0
\rightarrow
\Sigma_1.
```

On the examined witness domain, the embedding must preserve the meaning of the initial state:

```math
\nu_{\mathcal M_1}
\bigl(
\iota_X(x)
\bigr)
=
\nu_{\mathcal M_0}(x).
```

The old response lifted into the new ambient space is:

```math
\widetilde B_{\mathcal M_0}
\bigl(
\iota_X(x),
\iota_\Sigma(\sigma)
\bigr)
:=
B_{\mathcal M_0}(x,\sigma).
```

Abbreviate:

```math
\operatorname{Def}_{\widetilde{\mathcal M}_0}(W)
:=
\{
w\in W:
\widetilde B_{\mathcal M_0}(w)
\neq
\mathrm{undefined}
\},
```

and:

```math
\ker_W(\widetilde B_{\mathcal M_0})
:=
\{
(w_1,w_2)\in W^2:
\widetilde B_{\mathcal M_0}(w_1)
=
\widetilde B_{\mathcal M_0}(w_2)
\}.
```

If both machines use the same input space:

```math
\Sigma_0=\Sigma_1=\Sigma,
```

then:

```math
\iota_\Sigma
=
\operatorname{id}_{\Sigma}.
```

In the decimal machine the common operational signal is:

```math
\sigma=+1.
```

---

## 1.5 Operational capability profile

Let:

```math
W
\subseteq
X\times\Sigma
```

be a witness domain fixed in advance.

The domain of defined responses is:

```math
\operatorname{Def}_{\mathcal M}(W)
=
\{
w\in W
:
B_{\mathcal M}(w)
\neq
\mathrm{undefined}
\}.
```

The response-equivalence relation is:

```math
\ker_W(B_{\mathcal M})
=
\{
(w_1,w_2)\in W^2
:
B_{\mathcal M}(w_1)
=
B_{\mathcal M}(w_2)
\}.
```

The Workshop operational capability profile is:

```math
\mathfrak O_{\mathcal M}(W)
=
\left(
\operatorname{Def}_{\mathcal M}(W),
\ker_W(B_{\mathcal M})
\right).
```

This object jointly carries:

```text
which witnesses have a valid operational response
which witnesses the machine treats identically
which witnesses the machine can distinguish
```

The two opening forms are:

```text
reachability opening
→ the Def component strictly expands

discrimination opening
→ the kernel strictly refines on the fixed witness domain
```

Operational dimension in this document is neither a scalar nor vector-space dimension.

It is a new capability direction in the `\mathfrak O` profile, proved through ablation.

---

## 1.6 Operational signature

An operational signature may be assigned to system states:

```math
\Omega_{\mathcal M}
:
X
\rightarrow
\mathcal O.
```

The signature contains:

```text
the types and roles of active carriers
the order of bindings enabled under the given signal
the available transition rules
the output classes
the consequence classes
```

The raw quantitative value:

```math
Q(x)
```

is part of the operational signature only when it actually activates a new carrier, binding, or transition rule.

---

# 2. The four-layer calculation order

## 2.1 Quantitative growth

A state change is quantitative growth if:

```math
Q(y)>Q(x).
```

This records a change in the quantitative coordinate.

---

## 2.2 Representational length transition

The length of a normalized base-`b` representation is:

```math
\ell_b(0)=1,
```

and, for `n\geq1`:

```math
\ell_b(n)
=
1+\left\lfloor\log_b n\right\rfloor.
```

A representational length transition occurs when:

```math
\ell_b(n')
>
\ell_b(n).
```

This is a change in the minimum carrier length of the normalized description.

---

## 2.3 Informational state-space expansion

Let:

```math
P:X\rightarrow U
```

be the old state description, and:

```math
h:X\rightarrow H_h
```

be a new coordinate.

The new description is:

```math
P_h=(P,h).
```

Informational state-space expansion occurs when:

```math
\ker(P,h)
\subsetneq
\ker P.
```

This means that the new description distinguishes states that the old description treated as identical.

---

## 2.4 Operational dimension opening

Operational dimension opening occurs when a new or newly active operational unit creates:

```text
new reachability
or
new operational discrimination
```

and its ablation in the same ambient space removes the strict capability change.

The relation among the four layers is:

```text
quantity
→ how large the value is

representation
→ how many minimally active place values are required

information
→ which states the description distinguishes

operational capability
→ which state path or discrimination the machine creates
```

---

# 3. Quantitative growth and mechanical stagnation

## 3.1 Mechanical stagnation

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

The chain is:

```text
quantitative value increases
→ operational signature remains unchanged
→ no new direction appears in the capability profile
→ mechanical stagnation
```

---

## 3.2 First theorem — Quantitative growth is not sufficient for operational opening

### Theorem

```math
Q(y)>Q(x)
```

by itself does not imply:

```math
\Omega_{\mathcal M}(y)
\neq
\Omega_{\mathcal M}(x).
```

Nor does quantitative difference alone imply a change in the operational capability profile on the fixed witness domain.

### Proof

Let:

```math
Q(x_n)=n
```

and, for every `n`:

```math
\Omega_{\mathcal M}(x_n)=\omega.
```

Then:

```math
Q(x_{n+1})>Q(x_n),
```

while the operational signature remains unchanged.

QED.

---

## 3.3 Unbounded growth in one operational direction

Let:

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

while no new operational direction is created.

This is a counterexample to:

```math
\text{unbounded quantitative growth}
\Longrightarrow
\text{operational dimension opening}.
```

---

## 3.4 Vector-space checking example

Let `V` be a normed vector space and:

```math
v\in V,
\qquad
v\neq0.
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
\longrightarrow\infty,
```

while:

```math
\operatorname{span}\{x_n:n\in\mathbb N\}
=
\operatorname{span}\{v\},
```

and:

```math
\dim\operatorname{span}\{x_n:n\in\mathbb N\}=1.
```

Within its own model, this example confirms that unbounded magnitude does not force higher vector-space dimension.

The operation of the Workshop machine defines the Workshop concept of operational dimension.

---

## 3.5 The princess-dress example

Let:

```math
x_n=(\tau,n),
```

where:

```math
\tau
=
\text{“princess dress”},
```

and `n` is the item count.

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

Multiplication of a structural identity is quantitative multiplication of that structural identity.

If quantity activates a new storage, maintenance, distribution, or use relation, the new relation must be examined through a separate operational witness and ablation witness.

---

# 4. The base-`b` place-value machine

## 4.1 Digit range

Let:

```math
D_b
=
\{0,1,\ldots,b-1\},
\qquad
b\geq2.
```

`D_b` is the complete normalized digit range of one place value.

In base ten:

```math
D_{10}
=
\{0,1,2,3,4,5,6,7,8,9\}.
```

---

## 4.2 Fixed-width ambient state space

The machine containing `m` ambient place-value carriers is:

```math
\mathcal M_b^{(m)}.
```

Its ambient carriers are:

```math
H_b^{(m)}
=
\{h_0,h_1,\ldots,h_{m-1}\}.
```

Its state space is:

```math
X_b^{(m)}
=
D_b^m.
```

A state is:

```math
\mathbf d
=
(d_0,d_1,\ldots,d_{m-1}),
```

where `d_0` is the lowest place value.

The value-reading function is:

```math
V_m(\mathbf d)
=
\sum_{k=0}^{m-1}d_kb^k.
```

The semantic-state interpretation is:

```math
\nu_m(\mathbf d)
=
V_m(\mathbf d).
```

The ambient state space contains higher digits padded with zero.

Presence of an ambient carrier is therefore distinct from state-dependent activity.

---

## 4.3 The fixed-width encoder

For every value:

```math
0\leq n\leq b^m-1
```

there is a unique vector:

```math
\operatorname{enc}_m(n)
=
(d_0,\ldots,d_{m-1})
\in D_b^m
```

such that:

```math
n
=
\sum_{k=0}^{m-1}d_kb^k.
```

The encoder `\operatorname{enc}_m` pads the normalized base-`b` representation with zeros in higher places to produce an ambient state vector of length `m`.

Therefore:

```math
\operatorname{enc}_2(9)
=
(9,0),
```

and:

```math
\operatorname{enc}_2(10)
=
(0,1).
```

---

## 4.4 State-dependent active carriers

The minimum normalized length of value `n` is:

```math
\ell_b(0)=1,
```

and, for `n\geq1`:

```math
\ell_b(n)
=
1+\left\lfloor\log_b n\right\rfloor.
```

The active carriers in state `\mathbf d` of the machine with `m` ambient carriers are:

```math
A_b^{(m)}(\mathbf d)
=
\{
h_0,\ldots,h_{\ell_b(V_m(\mathbf d))-1}
\}.
```

The active places holding nonzero digit values are:

```math
N_b^{(m)}(\mathbf d)
=
\{
h_k\in A_b^{(m)}(\mathbf d)
:
d_k\neq0
\}.
```

Examples:

```math
A_{10}^{(2)}(9,0)
=
\{h_0\},
```

```math
A_{10}^{(2)}(0,1)
=
\{h_0,h_1\},
```

```math
N_{10}^{(2)}(0,1)
=
\{h_1\}.
```

Carrier `h_1` is present in the ambient space of state `(9,0)`, but is not yet active.

It becomes active in target state `(0,1)`.

Carrier `h_0` remains active in state `(0,1)` even though its current digit value is zero.

---

## 4.5 The partial `+1` transition

The common input signal is:

```math
\Sigma=\{+1\}.
```

The transition is:

```math
T_m(\mathbf d,+1)
=
\operatorname{enc}_m
\bigl(
V_m(\mathbf d)+1
\bigr)
```

when:

```math
V_m(\mathbf d)<b^m-1.
```

The maximum state is:

```math
\mathbf d_m^{\max}
=
(b-1,\ldots,b-1).
```

For this state:

```math
V_m(\mathbf d_m^{\max})
=
b^m-1,
```

and:

```math
T_m(\mathbf d_m^{\max},+1)
=
\bot.
```

Value `b^m` cannot be carried by `m` ambient digits.

---

## 4.6 Enabled and actually used carries

The carries enabled under signal `+1` are:

```math
R_m(\mathbf d,+1)
=
\left\{
c_{k\rightarrow k+1}
:
0\leq k\leq m-2
\ \land\
d_0=\cdots=d_k=b-1
\right\}.
```

This relation records the carry edges available in the ambient machine and enabled by the saturated lower prefix of the given state.

Let a realized transition satisfy:

```math
T_m(\mathbf d,+1)=\mathbf d'.
```

The carries actually used by the `+1` transition are:

```math
U_m(\mathbf d,+1,\mathbf d')
=
\{
c_{0\rightarrow1},
c_{1\rightarrow2},
\ldots,
c_{r-1\rightarrow r}
\},
```

where `r` is the smallest index such that:

```math
d_r<b-1,
```

and, for every:

```math
0\leq k<r
```

we have:

```math
d_k=b-1.
```

If:

```math
d_0<b-1,
```

then:

```math
U_m(\mathbf d,+1,\mathbf d')
=
\varnothing.
```

At the threshold transition in the machine with `m+1` ambient carriers:

```math
\iota_m(\mathbf d_m^{\max})
=
(b-1,\ldots,b-1,0),
```

and:

```math
T_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
(0,\ldots,0,1).
```

The carries actually used are:

```math
U_{m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr)
=
\{
c_{0\rightarrow1},
\ldots,
c_{m-1\rightarrow m}
\}.
```

The carry edges enabled at the threshold state are:

```math
R_{m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\Bigr)
=
\{
c_{0\rightarrow1},
\ldots,
c_{m-1\rightarrow m}
\}.
```

The highest new binding:

```math
c_{m-1\rightarrow m}
```

is therefore proved both enabled and actually used.

---

## 4.7 Value preservation of place-value carry

Let a temporary coefficient satisfy:

```math
c_k\geq b.
```

Euclidean division gives:

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

The representational structure changes while numerical value is preserved.

In base ten:

```math
10\cdot10^k
=
1\cdot10^{k+1}.
```

```text
ten ones
→ one ten
```

---

## 4.8 Representational length-transition theorem

For every `m\geq1`:

```math
\ell_b(b^m-1)=m,
```

and:

```math
\ell_b(b^m)=m+1.
```

Proof:

```math
b^{m-1}
\leq
b^m-1
<
b^m,
```

so the minimum length of `b^m-1` is `m`.

Furthermore:

```math
b^m
<
b^{m+1},
```

and `b^m` is not less than `b^m`, so its minimum length is `m+1`.

QED.

---

## 4.9 Semantics-preserving embedding

The embedding of a state with `m` ambient carriers into the machine with `m+1` ambient carriers is:

```math
\iota_m
(d_0,\ldots,d_{m-1})
=
(d_0,\ldots,d_{m-1},0).
```

The input embedding is:

```math
\iota_\Sigma(+1)=+1.
```

Semantics is preserved:

```math
\nu_{m+1}
\bigl(
\iota_m(\mathbf d)
\bigr)
=
\nu_m(\mathbf d).
```

The active carriers are also preserved in the embedded state:

```math
A_b^{(m+1)}
\bigl(
\iota_m(\mathbf d)
\bigr)
=
A_b^{(m)}(\mathbf d).
```

Presence of the higher ambient carrier therefore does not create automatic activity.

Activity opens in the target state.

---

# 5. Operational unit and ablation

## 5.1 The operational unit

Let:

```math
\mathcal M_1
=
\mathcal M_0\oplus\kappa.
```

The operational unit `\kappa` may contain:

```text
a new or newly active carrier
a new binding
a new transition rule
or a necessary combination of these
```

The new unit at a place-value threshold is:

```math
\kappa_m
=
(h_m,c_{m-1\rightarrow m}).
```

Here:

```text
h_m
→ the ambient carrier of place value b^m that becomes active in the target state

c_{m-1→m}
→ the highest new carry actually used by the threshold transition
```

---

## 5.2 The `Uses` relation

Let:

```math
T(x,\sigma)=x'.
```

We say that the transition uses `\kappa`:

```math
\operatorname{Uses}_{\kappa}(x,\sigma,x'),
```

if at least one of the following holds:

```text
a carrier of κ becomes active in the target state
a binding of κ appears in the actually used U set
a transition rule of κ is necessary for the realized transition
```

Formally, if:

```math
H_\kappa
\subseteq H
```

is the set of carriers of `\kappa`, and:

```math
E_\kappa
\subseteq H\times H
```

is the set of bindings of `\kappa`, then either of the following is sufficient:

```math
\bigl(
A(x')\setminus A(x)
\bigr)
\cap
H_\kappa
\neq
\varnothing,
```

or:

```math
U(x,\sigma,x')
\cap
E_\kappa
\neq
\varnothing.
```

Both conditions hold in the concrete place-value witness.

---

## 5.3 The ambient ablation machine

Ablation preserves:

```text
the ambient state space
the ambient input space
the state and input types
the fixed semantic interpretation
the output and consequence spaces
```

The `\kappa`-ablation transition is:

```math
T^{-\kappa}(x,\sigma)
=
\begin{cases}
T(x,\sigma),
&
\text{if }T(x,\sigma)=x'
\text{ and }
\neg\operatorname{Uses}_{\kappa}(x,\sigma,x'),
\\[6pt]
\bot,
&
\text{if }T(x,\sigma)=\bot
\text{ or }
\operatorname{Uses}_{\kappa}(x,\sigma,x').
\end{cases}
```

The ablation machine is:

```math
\operatorname{Abl}_{\kappa}(\mathcal M)
=
(X,\Sigma,H,A^{-\kappa},R^{-\kappa},T^{-\kappa},
U^{-\kappa},\nu,O,C,Q).
```

The carrier and binding restrictions are:

```math
A^{-\kappa}(x)
=
A(x)\setminus H_\kappa,
```

```math
R^{-\kappa}(x,\sigma)
=
R(x,\sigma)\setminus E_\kappa.
```

For surviving defined transitions, the usage record is:

```math
U^{-\kappa}(x,\sigma,x')
=
U(x,\sigma,x')\setminus E_\kappa.
```

The `T^{-\kappa}` rule has priority: every transition that uses `\kappa` becomes undefined.

Operational disabling:

```text
does not delete the ambient carrier from the type
does not change the meaning of the witness state
does not replace the observation space
does not modify response interpretation after the fact
```

Abbreviate:

```math
\mathcal M\setminus\kappa
:=
\operatorname{Abl}_{\kappa}(\mathcal M).
```

---

## 5.4 `\kappa`-dependent after-response

If:

```math
B_{\mathcal M_1}(w)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the response of the new machine on witness `w` is `\kappa`-dependent.

This proves that `\kappa` affects the complete after-response.

By itself, it does not prove that ablation restores the operation of the old machine.

---

## 5.5 Restoration ablation witness

A restoration witness binding the complete before–after difference to `\kappa` is:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\widetilde B_{\mathcal M_0}(w).
```

The three responses:

```text
before
after
ablation
```

then satisfy:

```math
\widetilde B_{\mathcal M_0}(w)
\neq
B_{\mathcal M_1}(w),
```

and:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\widetilde B_{\mathcal M_0}(w).
```

This proves that the operational unit `\kappa` creates the examined before–after difference on the fixed witness.

---

# 6. Operational behavior change and dimension opening

## 6.1 Operational behavior change

Let:

```math
W
\subseteq
X_1\times\Sigma_1
```

be the common witness domain.

Operational behavior change occurs if there is a:

```math
w\in W
```

such that:

```math
B_{\mathcal M_1}(w)
\neq
\widetilde B_{\mathcal M_0}(w).
```

If also:

```math
B_{\mathcal M_1}(w)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the complete after-response is `\kappa`-dependent.

If ablation restores the old response:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\widetilde B_{\mathcal M_0}(w),
```

then the before–after difference is bound to `\kappa`.

A mere response change is not yet an operational dimension opening.

---

## 6.2 Reachability opening

A reachability opening occurs on witness domain `W` if:

```math
\operatorname{Def}_{\widetilde{\mathcal M}_0}(W)
\subsetneq
\operatorname{Def}_{\mathcal M_1}(W),
```

and ablation removes the strict expansion.

The strongest local witness is:

```math
\widetilde B_{\mathcal M_0}(w)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}(w)
=
\bigl(
\mathrm{defined},
s,y,z
\bigr),
```

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\mathrm{undefined}.
```

In the capability profile:

```math
w
\notin
\operatorname{Def}_{\widetilde{\mathcal M}_0}(W),
```

```math
w
\in
\operatorname{Def}_{\mathcal M_1}(W),
```

```math
w
\notin
\operatorname{Def}_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(W).
```

This proves a valid state transition that did not previously exist.

---

## 6.3 Discrimination opening

Let:

```math
w_1,w_2\in W.
```

A discrimination opening occurs if:

```math
\widetilde B_{\mathcal M_0}(w_1)
=
\widetilde B_{\mathcal M_0}(w_2),
```

```math
B_{\mathcal M_1}(w_1)
\neq
B_{\mathcal M_1}(w_2),
```

and:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w_1)
=
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w_2).
```

On the fixed witness domain:

```math
\ker_W(B_{\mathcal M_1})
\subsetneq
\ker_W(\widetilde B_{\mathcal M_0}).
```

Ablation removes the new separation.

Global kernel refinement is a separate claim. This theorem proves strict refinement only on the fixed witness domain `W`.

---

## 6.4 Definition of operational dimension opening

> **Operational dimension opening occurs when a new or newly active carrier, binding, or transition rule creates new reachability or new discrimination in the operational capability profile on a fixed witness domain, and ablation in the same ambient space removes that strict capability change.**

The two proof classes are:

```text
reachability witness
discrimination witness
```

The following change is insufficient:

```text
every witness receives the same new response
→ ablation restores every witness to the same old response
```

This may be a `\kappa`-dependent operational behavior change.

If no new defined state transition appears and no previously equivalent witnesses are separated, then no operational dimension opening has been proved.

---
# 7. The `9 → 10` reachability witness

## 7.1 The two machines

Let:

```math
\mathcal M_1
=
\mathcal M_{10}^{(1)},
```

and:

```math
\mathcal M_2
=
\mathcal M_{10}^{(2)}.
```

Ambient carriers:

```math
H_{10}^{(1)}
=
\{h_0\},
```

```math
H_{10}^{(2)}
=
\{h_0,h_1\}.
```

State spaces:

```math
X_{10}^{(1)}
=
D_{10},
```

```math
X_{10}^{(2)}
=
D_{10}^2.
```

The common input is:

```math
+1.
```

The embeddings are:

```math
\iota_X(9)
=
(9,0),
```

```math
\iota_\Sigma(+1)
=
+1.
```

Semantics is preserved:

```math
\nu_2(9,0)
=
9
=
\nu_1(9).
```

---

## 7.2 Change in active carriers

In the embedded initial state:

```math
A_{10}^{(2)}(9,0)
=
\{h_0\}.
```

The higher ambient carrier `h_1` is present but not yet active.

In the target state:

```math
A_{10}^{(2)}(0,1)
=
\{h_0,h_1\}.
```

Therefore:

```math
h_1
\in
A_{10}^{(2)}(0,1)
\setminus
A_{10}^{(2)}(9,0).
```

Carrier `h_1` becomes active in the threshold transition.

---

## 7.3 The old and new transitions

The maximum state of the one-place machine is:

```math
9.
```

For this state:

```math
T_1(9,+1)
=
\bot.
```

Therefore:

```math
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined}.
```

In the machine with two ambient carriers:

```math
T_2((9,0),+1)
=
(0,1).
```

The semantic value of the target state is:

```math
\nu_2(0,1)
=
10.
```

The complete response is:

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

---

## 7.4 The actually used binding

For the realized transition:

```math
U_2
\bigl(
(9,0),
+1,
(0,1)
\bigr)
=
\{c_{0\rightarrow1}\}.
```

The new operational unit is:

```math
\kappa_1
=
(h_1,c_{0\rightarrow1}).
```

We have:

```math
h_1
\in
A_{10}^{(2)}(0,1)\setminus A_{10}^{(2)}(9,0),
```

and:

```math
c_{0\rightarrow1}
\in
U_2((9,0),+1,(0,1)).
```

Therefore:

```math
\operatorname{Uses}_{\kappa_1}
\bigl(
(9,0),
+1,
(0,1)
\bigr).
```

---

## 7.5 Ablation

Ablation preserves:

```math
X_{10}^{(2)}
=
D_{10}^2.
```

The witness state remains:

```math
(9,0).
```

Because the complete transition uses `\kappa_1`:

```math
T_2^{-\kappa_1}((9,0),+1)
=
\bot.
```

Therefore:

```math
B_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\mathrm{undefined}.
```

Under separate ablations:

```math
T_2^{-h_1}((9,0),+1)
=
\bot,
```

and:

```math
T_2^{-c_{0\rightarrow1}}((9,0),+1)
=
\bot.
```

---

## 7.6 Capability-profile witness

Let:

```math
W
=
\{
((9,0),+1)
\}.
```

The old machine's response lifted into the new ambient space is:

```math
\widetilde B_{\mathcal M_1}((9,0),+1)
=
\mathrm{undefined}.
```

Therefore:

```math
\operatorname{Def}_{\widetilde{\mathcal M}_1}(W)
=
\varnothing.
```

In the new machine:

```math
\operatorname{Def}_{\mathcal M_2}(W)
=
W.
```

In the ablation machine:

```math
\operatorname{Def}_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}(W)
=
\varnothing.
```

The strict change is:

```math
\varnothing
\subsetneq
W.
```

Ablation restores the old reachability profile.

This is a complete reachability witness.

---

## 7.7 The theorem of the first decimal opening

### Theorem

In the finite normalized decimal place-value machine, the transition:

```math
9
\longrightarrow
10
```

is an operational dimension opening.

### Proof

The old machine's response is:

```math
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined}.
```

The new machine's response is:

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

After ablation of the new operational unit:

```math
B_{\operatorname{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\mathrm{undefined}.
```

Carrier `h_1` becomes active in the target state, and binding `c_{0\rightarrow1}` is actually used by the transition.

The definedness component of the `\mathfrak O` profile strictly expands and is restored by ablation.

This is a reachability opening.

QED.

---

# 8. The general place-value threshold theorem

## 8.1 Theorem

For every:

```math
b\geq2,
\qquad
m\geq1
```

the transition:

```math
b^m-1
\longrightarrow
b^m
```

is a reachability opening in the extension from the machine with `m` ambient carriers to the machine with `m+1` ambient carriers.

The new operational unit is:

```math
\kappa_m
=
(h_m,c_{m-1\rightarrow m}).
```

---

## 8.2 Proof

The old maximum state is:

```math
\mathbf d_m^{\max}
=
(b-1,\ldots,b-1).
```

In the old machine:

```math
T_m(\mathbf d_m^{\max},+1)
=
\bot.
```

The embedded state is:

```math
\iota_m(\mathbf d_m^{\max})
=
(b-1,\ldots,b-1,0).
```

The embedding preserves semantics:

```math
\nu_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max})
\bigr)
=
b^m-1.
```

In the new machine:

```math
T_{m+1}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
(0,\ldots,0,1).
```

The target-state semantics is:

```math
\nu_{m+1}(0,\ldots,0,1)
=
b^m.
```

The new carrier becomes active:

```math
h_m
\in
A_b^{(m+1)}(0,\ldots,0,1)
\setminus
A_b^{(m+1)}
\bigl(
\iota_m(\mathbf d_m^{\max})
\bigr).
```

The highest new binding is actually used:

```math
c_{m-1\rightarrow m}
\in
U_{m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr).
```

Therefore:

```math
\operatorname{Uses}_{\kappa_m}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr).
```

The ablation transition is:

```math
T_{m+1}^{-\kappa_m}
\bigl(
\iota_m(\mathbf d_m^{\max}),
+1
\bigr)
=
\bot.
```

The old response is undefined, the new response is defined, and the ablation response is undefined again.

This is a reachability opening.

QED.

---

# 9. Not every carry opens a new operational dimension

The transition:

```text
19
→ 20
```

may use a carry binding.

Its minimum representational length is:

```math
\ell_{10}(19)=2,
```

```math
\ell_{10}(20)=2.
```

The higher carrier `h_1` is already active in the initial state.

No new ambient carrier becomes active.

The next place-value opening is:

```text
99
→ 100
```

because:

```math
\ell_{10}(99)=2,
```

```math
\ell_{10}(100)=3.
```

Therefore:

```text
carry
≠ automatically an operational dimension opening

carry into a new necessary higher carrier
+ new reachability
+ ablation in the same ambient space
→ operational dimension opening
```

---

# 10. Informational novelty and operational novelty

## 10.1 Functional informational novelty

A new coordinate `h` carries functionally new information relative to description `P` if no function exists:

```math
f:P(X)\rightarrow H_h,
```

such that:

```math
h=f\circ P.
```

A witness form is:

```math
\exists x,y\in X:
P(x)=P(y)
\land
h(x)\neq h(y).
```

This is informational novelty.

---

## 10.2 Informational novelty without operational effect

It is possible that:

```math
\ker(P,h)
\subsetneq
\ker P,
```

while:

```math
B_{\mathcal M_h}(x,\sigma)
=
B_{\mathcal M}(x,\sigma)
```

for every examined `x,\sigma`.

In this case the new coordinate refines the description but does not change the machine's operational capability profile.

---

## 10.3 Operational novelty without new external information

Let:

```math
g=(g_1,g_2),
```

and:

```math
h(g)=g_1\land g_2.
```

Coordinate `h` is fully derivable from `g`.

Let two states be:

```math
g^{(1)},
\qquad
g^{(2)},
```

such that:

```math
h(g^{(1)})=1,
```

```math
h(g^{(2)})=0.
```

The old decision machine satisfies:

```math
D_0(g^{(1)})
=
D_0(g^{(2)}).
```

The new authority-bearing rule is:

```math
D_1(g)
=
\begin{cases}
\mathrm{ALLOW},
&
h(g)=1,
\\[4pt]
\mathrm{BLOCK},
&
h(g)=0.
\end{cases}
```

Then:

```math
D_1(g^{(1)})
\neq
D_1(g^{(2)}).
```

If ablation of the authority binding gives:

```math
D_{\operatorname{Abl}_{\kappa}}(g^{(1)})
=
D_{\operatorname{Abl}_{\kappa}}(g^{(2)}),
```

then a discrimination opening is proved.

No new external information arrived.

A new operational relation entered operation.

---

# 11. Threshold and activation

Let:

```math
Q(x)\geq q_*.
```

The threshold condition by itself is a quantitative statement.

The machine must separately carry an activation rule:

```math
Q(x)\geq q_*
\Longrightarrow
\kappa
\text{ enters operation}.
```

The complete chain is:

```text
quantitative coordinate increases
→ threshold condition is satisfied
→ activation rule executes
→ new carrier or binding enters operation
→ capability-profile change becomes measurable
```

Operational dimension opening is proved when the capability-profile change is established by a reachability or discrimination witness and by ablation.

In the decimal machine:

```math
d_k=b-1
```

and addition of the next unit initiates the carry.

---

# 12. Formula, semantics, and mechanism

A formal expression has three separate layers:

```text
syntax
→ which symbols constitute the expression

semantics
→ what the symbols mean in the chosen model

mechanism
→ which carrier, binding, state, transition, and consequence the system creates
```

Changing notation may change syntax.

Under a fixed interpretation it may change semantics.

Only a change in the machine's capability profile, proved in operation and through ablation, creates an operational dimension opening.

```text
notation
≠ operational witness

formula
≠ machine

statement
≠ reproduced transition
```

---

# 13. Boundary of the “acquired” state

A state `x` is terminal if:

```math
\forall\sigma\in\Sigma:
T(x,\sigma)=\bot.
```

The label “acquired” is not a terminal-state definition.

A fuller lifecycle is:

```text
absent
→ acquired
→ bound into the system
→ in use
→ maintained
→ modified or degraded
→ withdrawn
```

If a model stops here:

```text
absent
→ became present
→ acquired
```

then the model has cut off the later transitions.

The remaining visible motion is easily flattened into accumulation:

```text
one is acquired
→ two are acquired
→ three are acquired
```

This is a quantitative axis.

A new operational dimension requires a new reachability or discrimination witness.

---

# 14. PULSEmech application

## 14.1 The release-authority response space

Let:

```math
\Theta_{\mathrm{release}}
=
\{
\mathrm{transition\_open},
\mathrm{transition\_closed}
\}.
```

The decision space is:

```math
\mathcal D_{\mathrm{release}}
=
\{
\mathrm{ALLOW},
\mathrm{BLOCK}
\}.
```

The consequence space:

```math
\mathcal Z_{\mathrm{release}}
```

is the space of fixed release-consequence records.

The complete authority-response space is:

```math
\mathcal B_{\mathrm{auth}}
=
\Theta_{\mathrm{release}}
\times
\mathcal D_{\mathrm{release}}
\times
\mathcal Z_{\mathrm{release}}.
```

The complete authority response is:

```math
B_{\mathrm{auth}}(g)
=
\bigl(
\Theta_{\mathrm{release}}(g),
D_{\mathrm{release}}(g),
C_{\mathrm{release}}(g)
\bigr).
```

The positive operational chain of the PULSEmech authority machine is:

```text
recorded current-run evidence
→ exact subject and artifact binding
→ declared policy
→ workflow-effective required-gate materialization
→ deterministic verifier replay
→ strict fail-closed gate evaluation
→ terminal ALLOW or BLOCK
```

---

## 14.2 Quantity and authority

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

be the set of gates.

The following are quantitative increases:

```math
|E'|>|E|,
```

```math
|A_r'|>|A_r|,
```

```math
|G'|>|G|.
```

They open an operational release dimension only when they create new reachability or new discrimination in the authority machine.

---

## 14.3 Candidate and advisory gate

Let `g` be the old authority-bearing gate state and `h` a new gate candidate.

The old response is:

```math
B_{\mathrm{auth},0}
:
G
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

The extended response is:

```math
B_{\mathrm{auth},1}
:
G\times\mathcal H_h
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

A gate in candidate or advisory state does not open a new authority dimension when:

```math
B_{\mathrm{auth},1}(g,h)
=
B_{\mathrm{auth},0}(g)
```

for every permitted `g,h`.

The factorization form is:

```math
B_{\mathrm{auth},1}
=
B_{\mathrm{auth},0}
\circ
\pi_G,
```

where:

```math
\pi_G(g,h)=g.
```

---

## 14.4 The authority-dependency graph

Let:

```math
\mathcal G_{\mathrm{dep}}
=
(N_{\mathrm{dep}},E_{\mathrm{dep}})
```

be the PULSEmech data- and control-dependency graph.

Let:

```math
u\leadsto S
```

mean that a directed data or control path leads from node `u` to some member of sink set `S`.

The authority-bearing sinks are:

```math
S_{\mathrm{auth}}
=
\{
\Theta_{\mathrm{release}},
D_{\mathrm{release}},
C_{\mathrm{release}}
\}.
```

If:

```math
h\not\leadsto S_{\mathrm{auth}},
```

then `h` does not participate in producing the terminal authority response.

The candidate boundary is:

```text
gate candidate
+ absent from the active materialized required set
+ no path to an authority-bearing sink
→ authority response factors through the old gate state
```

---

## 14.5 Active required gate as a discrimination opening

Let:

```math
g_*
```

be a fixed old authority state.

The old machine treats the two states of new gate `h` identically:

```math
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{PASS})
=
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{FAIL}).
```

The new machine with an active materialized required gate satisfies:

```math
B_{\mathrm{auth},1}
(g_*,h=\mathrm{PASS})
\neq
B_{\mathrm{auth},1}
(g_*,h=\mathrm{FAIL}).
```

For example, the decision projection is:

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

After ablation of the authority-bearing binding:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{PASS})
=
B_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{FAIL}).
```

In fail-closed form:

```math
D_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{PASS})
=
D_{\operatorname{Abl}_{\kappa}(\mathcal A_1)}
(g_*,h=\mathrm{FAIL})
=
\mathrm{BLOCK}.
```

On the fixed two-point witness domain, the response-equivalence kernel strictly refines, and ablation removes the new discrimination.

This is a discrimination opening.

---

## 14.6 Derived gate

A gate may be fully derivable from existing evidence.

Its operational value is determined not by informational novelty but by the operational relation it creates in the authority machine.

The proof chain is:

```text
derived gate state
→ current-run evidence binding
→ artifact binding
→ policy binding
→ materialized required gate
→ verifier replay
→ strict fail-closed evaluation
→ separation of cases previously treated identically
→ discrimination removed by ablation
```

This may open a new operational release dimension without new external information.

---

# 15. Boundary of external-theorem transfer

## 15.1 External proof and Workshop-machine application

Let:

```math
\mathsf A_{\mathcal E}
```

be the axiomatic system of an external theory,

```math
\mathcal E
```

be its model,

```math
\mathsf A_{\mathcal W}
```

be the Workshop theory,

and:

```math
\mathcal W
```

be the Workshop model.

If:

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

this does not automatically imply:

```math
\mathcal W
\models
\tau_{\mathcal W}.
```

Application requires two separate proofs:

```text
structure and operation preservation
transfer of the specific property
```

---

## 15.2 Structure and operation preservation

The correspondence maps are:

```math
\phi_X,
\phi_\Sigma,
\phi_H,
\phi_{\mathcal S},
\phi_Y,
\phi_Z.
```

Preservation of active carriers:

```math
\phi_H
\bigl(
A_{\mathcal W}(x)
\bigr)
=
A_{\mathcal E}
\bigl(
\phi_X(x)
\bigr).
```

Preservation of bindings enabled under a signal:

```math
(\phi_H\times\phi_H)
\bigl(
R_{\mathcal W}(x,\sigma)
\bigr)
=
R_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma)
\bigr).
```

Preservation of actually used bindings:

```math
(\phi_H\times\phi_H)
\bigl(
U_{\mathcal W}(x,\sigma,x')
\bigr)
=
U_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma),
\phi_X(x')
\bigr).
```

Transition preservation:

```math
T_{\mathcal W}(x,\sigma)=x'
\Longrightarrow
T_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma)
\bigr)
=
\phi_X(x').
```

Preservation of undefinedness when used by the theorem:

```math
T_{\mathcal W}(x,\sigma)=\bot
\Longleftrightarrow
T_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma)
\bigr)
=
\bot.
```

Semantic state:

```math
\phi_{\mathcal S}
\bigl(
\nu_{\mathcal W}(x')
\bigr)
=
\nu_{\mathcal E}
\bigl(
\phi_X(x')
\bigr).
```

Output:

```math
\phi_Y
\bigl(
O_{\mathcal W}(x')
\bigr)
=
O_{\mathcal E}
\bigl(
\phi_X(x')
\bigr).
```

Consequence:

```math
\phi_Z
\bigl(
C_{\mathcal W}(x,\sigma,x')
\bigr)
=
C_{\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma),
\phi_X(x')
\bigr).
```

A particular theorem may additionally require:

```text
injectivity
reflection of reachability
reflection of response-equivalence classes
preservation of undefinedness in partial transitions
identical quantifier domain
identical system boundary
```

---

## 15.3 Transfer of the specific property

Let:

```math
\operatorname{Tr}_{\phi}
(\tau_{\mathcal W})
```

be the translation of the Workshop property into the external model.

Let:

```math
\mathcal E_{\phi}
```

be the relevant external substructure selected by the image of the correspondence.

The theorem identity must be proved:

```math
\mathcal E_{\phi}
\models
\left(
\tau_{\mathcal E}
\Longleftrightarrow
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\right).
```

The external theorem must hold on the relevant substructure:

```math
\mathcal E_{\phi}
\models
\tau_{\mathcal E}.
```

The translated property must be reflected back:

```math
\mathcal E_{\phi}
\models
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\Longrightarrow
\mathcal W
\models
\tau_{\mathcal W}.
```

The complete chain is:

```math
\mathcal E_{\phi}\models\tau_{\mathcal E}
\Longrightarrow
\mathcal E_{\phi}\models
\operatorname{Tr}_{\phi}(\tau_{\mathcal W})
\Longrightarrow
\mathcal W\models\tau_{\mathcal W}.
```

Therefore:

```text
structural similarity
≠ theorem transfer

identical notation
≠ identical mechanism

external proof
+ operation preservation
+ property transfer
+ required reflection
→ applicable conclusion for the Workshop machine
```

---

# 16. Reproducible proof package

A claim of operational dimension opening contains at least the following records:

```text
before_machine
→ exact identification of the old machine

after_machine
→ exact identification of the new machine

ambient_state_space
→ common ablation state space

ambient_input_space
→ common input space

state_embedding
→ embedding of the old state into the new machine

input_embedding
→ embedding of the old input into the new machine

embedding_preservation
→ preservation of the meaning of the old witness state

change_unit
→ identification of the new carrier, binding, or rule

activation_path
→ how the operational unit becomes active

used_binding_record
→ which bindings the transition actually uses

uses_relation
→ proof that the witness transition uses κ

witness_domain
→ fixed W domain

witness_class
→ reachability_opening or discrimination_opening

before_profile
→ Def and kernel in the old machine

after_profile
→ Def and kernel in the new machine

ablation_contract
→ exact definition of T^{-κ}

ablation_profile
→ Def and kernel in the ablation machine

observation_boundary
→ common semantic-state, output, and consequence spaces

non_opening_change_exclusion
→ exclusion of a mere uniform output substitution

identity_and_binding
→ artifact, run, policy, and verifier binding

external_theorem_transfer_contract
→ proof of operation and property transfer when an external theorem is used

replay
→ deterministic replay
```

For a reachability proof:

```text
before:
the witness is absent from the Def domain

after:
the witness enters the Def domain

ablation:
the witness leaves the Def domain again
```

For a discrimination proof:

```text
before:
two witnesses belong to the same response class

after:
the two witnesses belong to different response classes

ablation:
the two witnesses return to the same response class
```

---

# 17. Main theorem

## The theorem of the Workshop decimal number system and operational dimension opening

Let:

```math
\mathcal M
=
(X,\Sigma,H,A,R,T,U,\nu,O,C,Q)
```

be a Workshop machine.

### I. Quantitative growth

```math
Q(y)>Q(x)
```

by itself does not prove a change in operational signature or capability profile.

### II. Representational length transition

In a finite normalized base-`b` place-value machine:

```math
\ell_b(b^m-1)=m,
```

```math
\ell_b(b^m)=m+1.
```

### III. Informational expansion

A new coordinate `h` expands the description informationally if:

```math
\ker(P,h)
\subsetneq
\ker P.
```

This is neither sufficient nor necessary for every operational dimension opening.

### IV. `\kappa`-dependent operational behavior change

If:

```math
B_{\mathcal M_1}(w)
\neq
\widetilde B_{\mathcal M_0}(w),
```

and:

```math
B_{\mathcal M_1}(w)
\neq
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the after-response carries a `\kappa`-dependent operational behavior change.

If also:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\widetilde B_{\mathcal M_0}(w),
```

then `\kappa` creates the fixed before–after difference on the witness.

### V. Reachability opening

If:

```math
\widetilde B_{\mathcal M_0}(w)
=
\mathrm{undefined},
```

```math
B_{\mathcal M_1}(w)
\neq
\mathrm{undefined},
```

and:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\mathrm{undefined},
```

then `\kappa` creates a reachability opening.

### VI. Discrimination opening

If:

```math
\widetilde B_{\mathcal M_0}(w_1)
=
\widetilde B_{\mathcal M_0}(w_2),
```

```math
B_{\mathcal M_1}(w_1)
\neq
B_{\mathcal M_1}(w_2),
```

and:

```math
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w_1)
=
B_{\operatorname{Abl}_{\kappa}(\mathcal M_1)}(w_2),
```

then `\kappa` creates a discrimination opening.

### VII. The first decimal opening

In the `9 → 10` witness:

```math
T_1(9,+1)=\bot,
```

```math
T_2((9,0),+1)=(0,1),
```

```math
U_2((9,0),+1,(0,1))
=
\{c_{0\rightarrow1}\},
```

```math
h_1
\in
A_{10}^{(2)}(0,1)\setminus A_{10}^{(2)}(9,0),
```

and:

```math
T_2^{-\kappa_1}((9,0),+1)
=
\bot.
```

This is a reachability opening.

### VIII. Boundary of an external theorem

An external theorem may determine a conclusion about the Workshop machine when:

```text
preservation of carrier, binding, state, input, transition,
semantic state, output, and consequence structure is proved

and

transfer of the specific theorem property and the required
reflection are proved
```

QED.

---

# 18. The Workshop calculation order

The complete examination order is:

```text
1. Which quantitative coordinate changed?

2. Which finite digit range closed?

3. Did the minimum length of the normalized representation increase?

4. Which ambient carrier was already present?

5. Which carrier actually became active?

6. Which binding was enabled under the given signal?

7. Which binding was actually used by the realized transition?

8. What are the common state and input embeddings?

9. Does the embedding preserve the meaning of the old witness state?

10. What is the fixed witness domain W?

11. What are the old machine's Def and kernel profiles on W?

12. What are the new machine's Def and kernel profiles on W?

13. Did a reachability or discrimination opening occur?

14. How is T^{-κ} defined?

15. Does ablation remove the strict capability change?

16. Can a mere uniform output substitution be excluded?

17. Which semantic target state, output, or consequence changed?

18. Can the same operation be reproduced with identical bindings?

19. When an external theorem is used, has operation preservation been proved?

20. Have transfer and reflection of the specific property been proved?
```

---

# 19. Workshop theorem

> **Numbers do not open merely because they become larger.**
>
> **The finite place-value machine opens when, after a closed digit range, a higher ambient carrier becomes active, the carry leading into it actually participates in operation, and a valid transition that did not previously exist is thereby created.**
>
> **An operational system opens when a new or newly active carrier, binding, or rule creates new reachability or new discrimination in the fixed capability profile, and ablation in the same ambient space removes that strict change.**

In compact form:

```text
accumulation
→ quantitative growth

place-value threshold
→ representational length transition

new descriptive coordinate
→ possible informational expansion

response change
+ κ-dependent after-response
→ operational behavior change

new Def element
or
strict kernel refinement
+ Usesκ witness
+ restoring ambient ablation
→ operational dimension opening
```

---

# 20. The Workshop principle

> **In the Workshop, we calculate in the decimal number system.**
>
> **The `0–9` range is the complete, inspectable normalized state space of one place value.**
>
> **After the range closes, the next value is not forced into the old carrier.**
>
> **A higher ambient place value is activated, the actually used carry is recorded, and the new reachability is proved in a common observation space.**
>
> **Ambient presence, active participation, nonzero value, and actually used binding are separate states.**
>
> **Expansion is proved by a strict, reproducible, and ablation-reversible change in the operational capability profile.**
>
> **The realized transition carries the operational participation of the binding.**
>
> **An external theorem may connect to the Workshop machine through proved operation preservation, property transfer, and required reflection.**
