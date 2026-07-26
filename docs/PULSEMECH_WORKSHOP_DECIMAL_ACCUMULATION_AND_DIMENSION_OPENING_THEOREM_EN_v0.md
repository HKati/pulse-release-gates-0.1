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
(X,\Sigma,H,\Lambda,A,R,T,U,\nu,O,C,Q).
```

Its components are:

```text
X
→ ambient state space

Σ
→ space of inputs or operational signals

H
→ set of ambient carriers

Λ
→ set of transition-rule identities

A : X → 2^H
→ carriers active in the given state

R : X×Σ → 2^(H×H)
→ bindings enabled in the given state under the given signal

T : X×Σ ⇀ X
→ partial transition function

U = (U_H,U_E,U_Λ)
→ transition-use record

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

The transition-use record is defined only for realized transitions:

```math
U_H:
\Gamma_T
\rightarrow
2^H,
```

```math
U_E:
\Gamma_T
\rightarrow
2^{H\times H},
```

```math
U_\Lambda:
\Gamma_T
\rightarrow
2^\Lambda.
```

The three components record:

```text
U_H(x,σ,x')
→ carriers actually read, written, or otherwise required by the realized transition

U_E(x,σ,x')
→ bindings actually traversed by the realized transition

U_Λ(x,σ,x')
→ transition-rule identities actually executed by the realized transition
```

This separates:

```text
ambient architecture
→ H and Λ

carrier active in a state
→ A(x)

binding enabled under a signal
→ R(x,σ)

carrier actually used by the concrete transition
→ U_H(x,σ,x')

binding actually used by the concrete transition
→ U_E(x,σ,x')

rule actually executed by the concrete transition
→ U_Λ(x,σ,x')
```

Operational participation is therefore proved by the use record bound to the
realized transition. It is not inferred from architectural presence or from
new activation alone.

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

The combined embedding is:

```math
\iota_{X\Sigma}(x,\sigma)
=
\bigl(
\iota_X(x),
\iota_\Sigma(\sigma)
\bigr).
```

On the examined embedded witness domain, the embedding must preserve the
meaning of the initial state:

```math
\nu_{\mathcal M_1}
\bigl(
\iota_X(x)
\bigr)
=
\nu_{\mathcal M_0}(x).
```

A comparison may also add a new axis that has no old-machine coordinate, as in
the PULSEmech gate example. The old response must therefore be defined on the
entire fixed witness domain through an explicit comparison pullback.

For transition machines, let:

```math
\mathcal D_0
=
X_0\times\Sigma_0,
```

```math
\mathcal D_1
=
X_1\times\Sigma_1.
```

More generally, `\mathcal D_i` denotes the explicitly typed domain of the
response function under comparison.

Let:

```math
W
\subseteq
\mathcal D_1
```

be the witness domain, and let:

```math
p_0:
W
\rightarrow
\mathcal D_0
```

be fixed before the comparison.

The old response lifted to every point of `W` is:

```math
\widetilde B_{\mathcal M_0}(w)
:=
B_{\mathcal M_0}
\bigl(
p_0(w)
\bigr).
```

On points that are images of old witnesses, the pullback must satisfy:

```math
p_0
\bigl(
\iota_{X\Sigma}(x,\sigma)
\bigr)
=
(x,\sigma).
```

Two important special cases are:

```text
embedding-image comparison
→ W lies in the image of ι_XΣ
→ p₀ is the inverse of ι_XΣ on W

new-axis comparison
→ W contains several values of a new coordinate over one old state
→ p₀ forgets the new coordinate through a fixed projection
```

For the PULSEmech gate axis:

```math
p_0
=
\pi_G.
```

This makes the old response well-defined at both:

```text
(g*, h=PASS)
(g*, h=FAIL)
```

even though the old machine has no `h` coordinate.

Abbreviate:

```math
\mathrm{Def}_{\widetilde{\mathcal M}_0}(W)
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
\mathrm{id}_{\Sigma}.
```

In the decimal machine the common operational signal is:

```math
\sigma=+1.
```

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
\mathrm{Def}_{\mathcal M}(W)
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
\mathrm{Def}_{\mathcal M}(W),
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
→ response equivalence strictly refines on a proved comparison domain
```

For a two-point discrimination witness:

```math
W_{12}
=
\{w_1,w_2\},
```

the three complete-response conditions:

```text
old responses equal
new responses different
ablation responses equal
```

directly imply strict kernel refinement on `W_{12}`.

For a larger witness domain `W`, strict kernel refinement additionally requires
the no-merging condition:

```math
B_{\mathcal M_1}(u)
=
B_{\mathcal M_1}(v)
\Longrightarrow
\widetilde B_{\mathcal M_0}(u)
=
\widetilde B_{\mathcal M_0}(v)
```

for every `u,v\in W`, together with at least one old-equivalent pair separated
by the new machine.

Operational dimension in this document is neither a scalar nor vector-space
dimension.

It is a new capability direction in the `\mathfrak O` profile, proved through
a fixed witness domain and ablation.

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
\mathrm{span}\{x_n:n\in\mathbb N\}
=
\mathrm{span}\{v\},
```

and:

```math
\dim\mathrm{span}\{x_n:n\in\mathbb N\}=1.
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
\mathrm{enc}_m(n)
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

The encoder `\mathrm{enc}_m` pads the normalized base-`b` representation with zeros in higher places to produce an ambient state vector of length `m`.

Therefore:

```math
\mathrm{enc}_2(9)
=
(9,0),
```

and:

```math
\mathrm{enc}_2(10)
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
\mathrm{enc}_m
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

## 4.6 Enabled bindings and realized transition-use records

The carry bindings enabled under signal `+1` are:

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

This relation records the carry edges available in the ambient machine and
enabled by the saturated lower prefix of the given state.

Let a realized transition satisfy:

```math
T_m(\mathbf d,+1)=\mathbf d'.
```

The fixed place-value evaluator reads the active source digits and the
fixed-width encoder writes the active target digits. Its realized carrier-use
record is therefore:

```math
U_{H,m}(\mathbf d,+1,\mathbf d')
=
A_b^{(m)}(\mathbf d)
\cup
A_b^{(m)}(\mathbf d').
```

This record includes carriers that were already active before the transition.
For example, the tens carrier is actually used by `10 → 11` even though it does
not become newly active in that transition.

The carry bindings actually traversed by the `+1` transition are:

```math
U_{E,m}(\mathbf d,+1,\mathbf d')
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
0\leq k<r,
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
U_{E,m}(\mathbf d,+1,\mathbf d')
=
\varnothing.
```

Let:

```math
\lambda_{+1}^{(m)}
\in
\Lambda_m
```

identify the fixed-width increment-and-normalization rule of the `m`-carrier
machine. Every realized `+1` transition records:

```math
U_{\Lambda,m}(\mathbf d,+1,\mathbf d')
=
\{
\lambda_{+1}^{(m)}
\}.
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

The carriers actually used are:

```math
U_{H,m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr)
=
\{
h_0,\ldots,h_m
\}.
```

The carry bindings actually used are:

```math
U_{E,m+1}
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

The carry bindings enabled at the threshold state are:

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

Therefore the higher carrier:

```math
h_m
```

is present in the realized carrier-use record, and the highest new binding:

```math
c_{m-1\rightarrow m}
```

is proved both enabled and actually traversed.

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

An operational unit is represented by the identities it can contribute to a
realized transition:

```math
\kappa
=
(H_\kappa,E_\kappa,\Lambda_\kappa),
```

where:

```text
H_κ
→ carrier identities belonging to κ

E_κ
→ binding identities belonging to κ

Λ_κ
→ transition-rule identities belonging to κ
```

The operational unit may therefore contain:

```text
a new or newly active carrier
a new binding
a new transition rule
or a necessary combination of these
```

The new unit at a place-value threshold is abbreviated as:

```math
\kappa_m
=
(h_m,c_{m-1\rightarrow m}),
```

with the exact identity sets:

```math
H_{\kappa_m}
=
\{h_m\},
```

```math
E_{\kappa_m}
=
\{c_{m-1\rightarrow m}\},
```

```math
\Lambda_{\kappa_m}
=
\varnothing.
```

Here:

```text
h_m
→ the ambient carrier of place value b^m that is used by the target state

c_{m-1→m}
→ the highest new carry traversed by the threshold transition
```

## 5.2 The `Uses` relation

Let:

```math
T(x,\sigma)=x'.
```

We say that the realized transition uses `\kappa`:

```math
\mathrm{Uses}_{\kappa}(x,\sigma,x'),
```

exactly when at least one component of `\kappa` appears in the realized
transition-use record:

```math
U_H(x,\sigma,x')
\cap
H_\kappa
\neq
\varnothing,
```

or:

```math
U_E(x,\sigma,x')
\cap
E_\kappa
\neq
\varnothing,
```

or:

```math
U_\Lambda(x,\sigma,x')
\cap
\Lambda_\kappa
\neq
\varnothing.
```

This definition records actual participation. It detects carriers that were
already active before the transition as well as carriers that become active in
the target state.

The activation difference:

```math
\bigl(
A(x')\setminus A(x)
\bigr)
\cap
H_\kappa
\neq
\varnothing
```

is a separate opening witness. It may show that a carrier became newly active,
but it is not the definition of transition use.

In the concrete `9 → 10` place-value witness:

```text
h₁
→ appears in U_H

c₀→₁
→ appears in U_E

h₁
→ also becomes newly active
```

The use record and the activation witness therefore agree, while remaining
formally distinct.

## 5.3 The ambient ablation machine

Ablation preserves:

```text
the ambient state space
the ambient input space
the state and input types
the ambient carrier and rule-identity types
the fixed semantic interpretation
the output and consequence spaces
```

The `\kappa`-ablation transition is the following total definition over the
partial-transition result:

```math
T^{-\kappa}(x,\sigma)
=
\begin{cases}
\bot,
&
\text{if }T(x,\sigma)=\bot,
\\[6pt]
\bot,
&
\text{if }T(x,\sigma)=x'
\text{ and }
\mathrm{Uses}_{\kappa}(x,\sigma,x'),
\\[6pt]
x',
&
\text{if }T(x,\sigma)=x'
\text{ and }
\neg\mathrm{Uses}_{\kappa}(x,\sigma,x').
\end{cases}
```

The target `x'` is evaluated only in branches where:

```math
T(x,\sigma)=x'
```

has already bound it.

The ablation machine is:

```math
\mathrm{Abl}_{\kappa}(\mathcal M)
=
(X,\Sigma,H,\Lambda,A^{-\kappa},R^{-\kappa},T^{-\kappa},
U^{-\kappa},\nu,O,C,Q).
```

The carrier and enabled-binding restrictions are:

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

For every transition that survives `T^{-\kappa}`, the use record is:

```math
U_H^{-\kappa}(x,\sigma,x')
=
U_H(x,\sigma,x')\setminus H_\kappa,
```

```math
U_E^{-\kappa}(x,\sigma,x')
=
U_E(x,\sigma,x')\setminus E_\kappa,
```

```math
U_\Lambda^{-\kappa}(x,\sigma,x')
=
U_\Lambda(x,\sigma,x')\setminus\Lambda_\kappa.
```

The `T^{-\kappa}` rule has priority: every realized transition whose use record
intersects `\kappa` becomes undefined.

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
\mathrm{Abl}_{\kappa}(\mathcal M).
```

## 5.4 `\kappa`-dependent after-response

If:

```math
B_{\mathcal M_1}(w)
\neq
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the response of the new machine on witness `w` is `\kappa`-dependent.

This proves that `\kappa` affects the complete after-response.

By itself, it does not prove that ablation restores the operation of the old machine.

---

## 5.5 Restoration ablation witness

A restoration witness binding the complete before–after difference to `\kappa` is:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the complete after-response is `\kappa`-dependent.

If ablation restores the old response:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\widetilde B_{\mathcal M_0}(w),
```

then the before–after difference is bound to `\kappa`.

A mere response change is not yet an operational dimension opening.

---

## 6.2 Reachability opening

A reachability opening occurs on witness domain `W` if:

```math
\mathrm{Def}_{\widetilde{\mathcal M}_0}(W)
\subsetneq
\mathrm{Def}_{\mathcal M_1}(W),
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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\mathrm{undefined}.
```

In the capability profile:

```math
w
\notin
\mathrm{Def}_{\widetilde{\mathcal M}_0}(W),
```

```math
w
\in
\mathrm{Def}_{\mathcal M_1}(W),
```

```math
w
\notin
\mathrm{Def}_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(W).
```

This proves a valid state transition that did not previously exist.

---

## 6.3 Discrimination opening

Let two distinct witnesses be:

```math
w_1,
\qquad
w_2.
```

Fix the comparison domain to exactly the witnessed pair:

```math
W_{12}
=
\{w_1,w_2\}.
```

A discrimination opening occurs on `W_{12}` if:

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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w_1)
=
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w_2).
```

On the two-point domain, the old kernel contains the off-diagonal witness pair,
while the new kernel does not. Therefore:

```math
\ker_{W_{12}}(B_{\mathcal M_1})
\subsetneq
\ker_{W_{12}}(\widetilde B_{\mathcal M_0}).
```

Ablation restores the old response equivalence on `W_{12}`.

For a larger domain `W`, the same strict inclusion may be claimed only when the
no-merging condition is also proved:

```math
B_{\mathcal M_1}(u)
=
B_{\mathcal M_1}(v)
\Longrightarrow
\widetilde B_{\mathcal M_0}(u)
=
\widetilde B_{\mathcal M_0}(v)
```

for all `u,v\in W`.

The local theorem requires only the fixed two-point witness domain. It does not
claim a global refinement without the additional preservation proof.

### 6.3.1 Response-level discrimination corollary

Let:

```math
\mathcal D
```

be a fixed response domain, and let:

```math
\widetilde B_0,
\qquad
B_1,
\qquad
B_1^{-\kappa}
:
\mathcal D
\rightarrow
\mathcal B
```

be three complete response functions of the same type.

For distinct witnesses:

```math
w_1,w_2\in\mathcal D,
```

fix:

```math
W_{12}
=
\{w_1,w_2\}.
```

If:

```math
\widetilde B_0(w_1)
=
\widetilde B_0(w_2),
```

```math
B_1(w_1)
\neq
B_1(w_2),
```

and:

```math
B_1^{-\kappa}(w_1)
=
B_1^{-\kappa}(w_2),
```

then:

```math
\ker_{W_{12}}(B_1)
\subsetneq
\ker_{W_{12}}(\widetilde B_0),
```

and the `\kappa`-ablation response removes the new complete-response
discrimination on `W_{12}`.

The ablated response:

```math
B_1^{-\kappa}
```

must be produced by an explicitly typed ablated evaluator. Its domain and
codomain are the same as those of `B_1`.

A completed response may not be replaced after evaluation and then presented as
an ablation result.

For a transition machine, the required construction is:

```math
B_1^{-\kappa}
=
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}.
```

For an evaluator whose structural input is not a transition machine, let:

```math
\mathfrak S
```

be its typed structural-state space, let:

```math
\mathrm{Eval}
:
\mathfrak S\times\mathcal D
\rightarrow
\mathcal B,
```

and let:

```math
\mathrm{Abl}_{\kappa}^{\mathfrak S}
:
\mathfrak S
\rightarrow
\mathfrak S
```

disable `\kappa` in that structural state before evaluation.

For a fixed evaluator state `s_1\in\mathfrak S`, the two responses are then:

```math
B_1(w)
=
\mathrm{Eval}(s_1,w),
```

and:

```math
B_1^{-\kappa}(w)
=
\mathrm{Eval}
\bigl(
\mathrm{Abl}_{\kappa}^{\mathfrak S}(s_1),
w
\bigr).
```

The restored equality on `W_{12}` must follow from the evaluator contract and
the ablated structural state. It may not be introduced by a post-hoc constant
substitution on already-produced responses.

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

## 7.4 The actually used carriers and binding

For the realized transition, the carrier-use record is:

```math
U_{H,2}
\bigl(
(9,0),
+1,
(0,1)
\bigr)
=
\{h_0,h_1\}.
```

The binding-use record is:

```math
U_{E,2}
\bigl(
(9,0),
+1,
(0,1)
\bigr)
=
\{c_{0\rightarrow1}\}.
```

The rule-use record is:

```math
U_{\Lambda,2}
\bigl(
(9,0),
+1,
(0,1)
\bigr)
=
\{\lambda_{+1}^{(2)}\}.
```

The new operational unit is:

```math
\kappa_1
=
(h_1,c_{0\rightarrow1}).
```

Its exact identity sets satisfy:

```math
H_{\kappa_1}
=
\{h_1\},
```

```math
E_{\kappa_1}
=
\{c_{0\rightarrow1}\}.
```

Therefore:

```math
U_{H,2}((9,0),+1,(0,1))
\cap
H_{\kappa_1}
=
\{h_1\},
```

and:

```math
U_{E,2}((9,0),+1,(0,1))
\cap
E_{\kappa_1}
=
\{c_{0\rightarrow1}\}.
```

Hence:

```math
\mathrm{Uses}_{\kappa_1}
\bigl(
(9,0),
+1,
(0,1)
\bigr).
```

Separately, the activation witness is:

```math
h_1
\in
A_{10}^{(2)}(0,1)
\setminus
A_{10}^{(2)}(9,0).
```

The transition thus records both actual use and new activation.

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
B_{\mathrm{Abl}_{\kappa_1}(\mathcal M_2)}
((9,0),+1)
=
\mathrm{undefined}.
```

For the separate carrier-only and binding-only ablations, define:

```math
\kappa_{h_1}
=
(\{h_1\},\varnothing,\varnothing),
```

```math
\kappa_{c_{0\rightarrow1}}
=
(\varnothing,\{c_{0\rightarrow1}\},\varnothing).
```

Then:

```math
T_2^{-\kappa_{h_1}}((9,0),+1)
=
\bot,
```

and:

```math
T_2^{-\kappa_{c_{0\rightarrow1}}}((9,0),+1)
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

Fix the comparison pullback on this singleton domain:

```math
p_0
\bigl(
((9,0),+1)
\bigr)
=
(9,+1).
```

The old machine's response lifted into the new ambient space is therefore:

```math
\widetilde B_{\mathcal M_1}((9,0),+1)
=
B_{\mathcal M_1}(9,+1)
=
\mathrm{undefined}.
```

Therefore:

```math
\mathrm{Def}_{\widetilde{\mathcal M}_1}(W)
=
\varnothing.
```

In the new machine:

```math
\mathrm{Def}_{\mathcal M_2}(W)
=
W.
```

In the ablation machine:

```math
\mathrm{Def}_{\mathrm{Abl}_{\kappa_1}(\mathcal M_2)}(W)
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
B_{\mathrm{Abl}_{\kappa_1}(\mathcal M_2)}
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

The new carrier is also present in the realized carrier-use record:

```math
h_m
\in
U_{H,m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr).
```

The highest new binding is present in the realized binding-use record:

```math
c_{m-1\rightarrow m}
\in
U_{E,m+1}
\Bigl(
\iota_m(\mathbf d_m^{\max}),
+1,
(0,\ldots,0,1)
\Bigr).
```

Therefore:

```math
\mathrm{Uses}_{\kappa_m}
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

The old response is undefined, the new response is defined, and the ablation
response is undefined again.

This is a reachability opening.

QED.

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

For this local decision-only example, define the complete response of the
decision machine to be the decision value itself:

```math
\mathcal B_D
=
\{
\mathrm{ALLOW},
\mathrm{BLOCK}
\}.
```

Let:

```math
\mathcal G_D
```

be the state space of this local decision-only machine.

```math
B_{D,0}
:
\mathcal G_D
\rightarrow
\mathcal B_D,
```

```math
B_{D,1}
:
\mathcal G_D
\rightarrow
\mathcal B_D.
```

The old complete response satisfies:

```math
B_{D,0}(g^{(1)})
=
B_{D,0}(g^{(2)}).
```

The new authority-bearing response is:

```math
B_{D,1}(g)
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
B_{D,1}(g^{(1)})
\neq
B_{D,1}(g^{(2)}).
```

Let the complete response of the ablated decision machine be:

```math
B_{D,1}^{-\kappa}
:
\mathcal G_D
\rightarrow
\mathcal B_D.
```

If ablation of the authority binding restores complete-response equality:

```math
B_{D,1}^{-\kappa}(g^{(1)})
=
B_{D,1}^{-\kappa}(g^{(2)}),
```

then the fixed two-point decision machine has a discrimination opening.

Here the response is not a projection of a larger tuple: by definition,
`B_D` is the entire response of the local decision-only machine.

No new external information arrived.

A new operational relation entered operation.

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

Let the transition-state set be:

```math
\Theta_{\mathrm{release}}
=
\{
\mathrm{transition\_open},
\mathrm{transition\_closed}
\}.
```

Let the decision space be:

```math
\mathcal D_{\mathrm{release}}
=
\{
\mathrm{ALLOW},
\mathrm{BLOCK}
\}.
```

Let:

```math
\mathcal Z_{\mathrm{release}}
```

be the space of fixed release-consequence records.

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

Let:

```math
\mathcal G
```

be the release-authority gate-state space.

The transition-state evaluator is:

```math
\theta_{\mathrm{release}}
:
\mathcal G
\rightarrow
\Theta_{\mathrm{release}}.
```

The decision evaluator is:

```math
d_{\mathrm{release}}
:
\mathcal G
\rightarrow
\mathcal D_{\mathrm{release}}.
```

The consequence evaluator is:

```math
c_{\mathrm{release}}
:
\mathcal G
\rightarrow
\mathcal Z_{\mathrm{release}}.
```

The complete authority response is:

```math
B_{\mathrm{auth}}(g)
=
\bigl(
\theta_{\mathrm{release}}(g),
d_{\mathrm{release}}(g),
c_{\mathrm{release}}(g)
\bigr).
```

The set `\Theta_{\mathrm{release}}` and the evaluator
`\theta_{\mathrm{release}}` are distinct typed objects.

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
G_{\mathrm{ids}}
```

be the set of declared gate identities.

The following are quantitative increases:

```math
|E'|>|E|,
```

```math
|A_r'|>|A_r|,
```

```math
|G_{\mathrm{ids}}'|>|G_{\mathrm{ids}}|.
```

They open an operational release dimension only when they create new reachability or new discrimination in the authority machine.

---

## 14.3 Candidate and advisory gate

Let `g\in\mathcal G` be the old authority-bearing gate state and `h` a new gate candidate.

The old response is:

```math
B_{\mathrm{auth},0}
:
\mathcal G
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

The extended response is:

```math
B_{\mathrm{auth},1}
:
\mathcal G\times\mathcal H_h
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

Define the projection:

```math
\pi_G(g,h)=g.
```

The old response lifted across the entire new gate axis is:

```math
\widetilde B_{\mathrm{auth},0}
:=
B_{\mathrm{auth},0}
\circ
\pi_G.
```

Therefore:

```math
\widetilde B_{\mathrm{auth},0}(g,h)
=
B_{\mathrm{auth},0}(g)
```

for every permitted `g,h`.

A gate in candidate or advisory state does not open a new authority dimension
when:

```math
B_{\mathrm{auth},1}
=
\widetilde B_{\mathrm{auth},0}.
```

Equivalently:

```math
B_{\mathrm{auth},1}
=
B_{\mathrm{auth},0}
\circ
\pi_G.
```

The projection `\pi_G` is the comparison pullback `p_0` for this new-axis
witness domain.

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

mean that a directed data or control path leads from node `u` to some member
of sink set `S`.

The authority-bearing evaluator nodes are:

```math
S_{\mathrm{auth}}
=
\{
\theta_{\mathrm{release}},
d_{\mathrm{release}},
c_{\mathrm{release}}
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
+ no path to an authority-bearing evaluator
→ authority response factors through the old gate state
```

## 14.5 Active required gate as a discrimination opening

Let:

```math
g_*
```

be a fixed old authority state.

Fix the two-point witness domain:

```math
W_h
=
\{
(g_*,h=\mathrm{PASS}),
(g_*,h=\mathrm{FAIL})
\}.
```

Because the old response is lifted by `\pi_G`, it is defined at both points and
treats them identically:

```math
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{PASS})
=
\widetilde B_{\mathrm{auth},0}
(g_*,h=\mathrm{FAIL}).
```

The active materialized required gate produces complete-response separation:

```math
B_{\mathrm{auth},1}
(g_*,h=\mathrm{PASS})
\neq
B_{\mathrm{auth},1}
(g_*,h=\mathrm{FAIL}).
```

Let the decision projection be:

```math
\pi_D
:
\mathcal B_{\mathrm{auth}}
\rightarrow
\mathcal D_{\mathrm{release}},
```

and define:

```math
d_{\mathrm{release},1}
:=
\pi_D
\circ
B_{\mathrm{auth},1}.
```

Its decision projection may, for example, satisfy:

```math
d_{\mathrm{release},1}
(g_*,h=\mathrm{PASS})
=
\mathrm{ALLOW},
```

```math
d_{\mathrm{release},1}
(g_*,h=\mathrm{FAIL})
=
\mathrm{BLOCK}.
```

The decision projection illustrates one differing component. The
discrimination proof itself uses the complete `B_{\mathrm{auth},1}` response.

### Authority-dependency ablation and evaluator replay

Let the typed authority dependency-graph space be:

```math
\mathfrak D_{\mathrm{auth}}
=
\left\{
(N_{\mathrm{dep}},E)
\ \middle|\
E\subseteq E_{\mathrm{dep}}
\right\}.
```

For any dependency-graph state:

```math
\mathcal D
=
(N_{\mathrm{dep}},E)
\in
\mathfrak D_{\mathrm{auth}},
```

write:

```math
u
\leadsto_{\mathcal D}
S
```

when a directed path in `\mathcal D` leads from node `u` to an element of
node set `S`.

Let the complete authority evaluator be:

```math
\mathrm{Eval}_{\mathrm{auth}}
:
\mathfrak D_{\mathrm{auth}}
\times
\mathcal G
\times
\mathcal H_h
\rightarrow
\mathcal B_{\mathrm{auth}}.
```

The active required-gate response is generated from the original dependency
graph:

```math
B_{\mathrm{auth},1}(g,h)
=
\mathrm{Eval}_{\mathrm{auth}}
\bigl(
\mathcal G_{\mathrm{dep}},
g,
h
\bigr).
```

Let:

```math
n_h
\in
N_{\mathrm{dep}}
```

be the node carrying the materialized required-gate value, and let:

```math
E_{\kappa}^{\mathrm{dep}}
\subseteq
E_{\mathrm{dep}}
```

be the exact authority-dependency edge cut used by that gate value on its path
to the authority-bearing evaluator set `S_{\mathrm{auth}}`.

The original graph contains the required path:

```math
n_h
\leadsto_{\mathcal G_{\mathrm{dep}}}
S_{\mathrm{auth}}.
```

Define the authority-dependency ablation on graph state:

```math
\mathrm{Abl}_{\kappa}^{\mathrm{dep}}
:
\mathfrak D_{\mathrm{auth}}
\rightarrow
\mathfrak D_{\mathrm{auth}},
```

```math
\mathrm{Abl}_{\kappa}^{\mathrm{dep}}
(N_{\mathrm{dep}},E)
=
\bigl(
N_{\mathrm{dep}},
E\setminus E_{\kappa}^{\mathrm{dep}}
\bigr).
```

The ablated dependency graph is:

```math
\mathcal G_{\mathrm{dep}}^{-\kappa}
:=
\mathrm{Abl}_{\kappa}^{\mathrm{dep}}
\bigl(
\mathcal G_{\mathrm{dep}}
\bigr).
```

The edge cut is required to remove every authority-bearing path from the
materialized gate node:

```math
n_h
\not\leadsto_{\mathcal G_{\mathrm{dep}}^{-\kappa}}
S_{\mathrm{auth}}.
```

The original evaluator execution carries an actual dependency-use record:

```math
U_{\mathrm{dep}}^{\mathrm{auth}}
:
\mathfrak D_{\mathrm{auth}}
\times
\mathcal G
\times
\mathcal H_h
\rightarrow
2^{E_{\mathrm{dep}}}.
```

For a graph state `\mathcal D=(N_{\mathrm{dep}},E)`, require:

```math
U_{\mathrm{dep}}^{\mathrm{auth}}
(\mathcal D,g,h)
\subseteq
E.
```

For both required-gate witnesses, the original evaluation actually traverses
the ablated edge cut:

```math
U_{\mathrm{dep}}^{\mathrm{auth}}
\bigl(
\mathcal G_{\mathrm{dep}},
g_*,
h=\mathrm{PASS}
\bigr)
\cap
E_{\kappa}^{\mathrm{dep}}
\neq
\varnothing,
```

and:

```math
U_{\mathrm{dep}}^{\mathrm{auth}}
\bigl(
\mathcal G_{\mathrm{dep}},
g_*,
h=\mathrm{FAIL}
\bigr)
\cap
E_{\kappa}^{\mathrm{dep}}
\neq
\varnothing.
```

Let the fixed fail-closed consequence evaluator be:

```math
c_{\mathrm{fc}}
:
\mathcal G
\rightarrow
\mathcal Z_{\mathrm{release}}.
```

Define the complete fail-closed response:

```math
b_{\mathrm{fc}}(g)
=
\bigl(
\mathrm{transition\_closed},
\mathrm{BLOCK},
c_{\mathrm{fc}}(g)
\bigr).
```

The authority evaluator has the following fail-closed structural contract for
the materialized required gate:

```math
n_h
\not\leadsto_{\mathcal D}
S_{\mathrm{auth}}
\Longrightarrow
\mathrm{Eval}_{\mathrm{auth}}
(\mathcal D,g,h)
=
b_{\mathrm{fc}}(g)
```

for every:

```math
\mathcal D\in\mathfrak D_{\mathrm{auth}},
\qquad
g\in\mathcal G,
\qquad
h\in\mathcal H_h.
```

This contract evaluates the ablated dependency structure. It does not overwrite
an already-produced response.

For a concrete PULSEmech proof, the implication above is a proof obligation over
the recorded evaluator implementation. The edge cut, absence of every alternate
required path, evaluator identity, evaluator replay, and resulting complete
fail-closed response must all be recorded and reproduced.

Define the complete ablated authority response by evaluator replay over the
ablated graph:

```math
B_{\mathrm{auth},1}^{-\kappa}(g,h)
:=
\mathrm{Eval}_{\mathrm{auth}}
\bigl(
\mathcal G_{\mathrm{dep}}^{-\kappa},
g,
h
\bigr).
```

Because the required path is absent in
`\mathcal G_{\mathrm{dep}}^{-\kappa}`, the fail-closed evaluator contract gives:

```math
B_{\mathrm{auth},1}^{-\kappa}
(g_*,h=\mathrm{PASS})
=
b_{\mathrm{fc}}(g_*)
=
B_{\mathrm{auth},1}^{-\kappa}
(g_*,h=\mathrm{FAIL}).
```

Let:

```math
d_{\mathrm{release},1}^{-\kappa}
```

be the decision projection of `B_{\mathrm{auth},1}^{-\kappa}`. By the
definition of `b_{\mathrm{fc}}`:

```math
d_{\mathrm{release},1}^{-\kappa}
(g_*,h=\mathrm{PASS})
=
d_{\mathrm{release},1}^{-\kappa}
(g_*,h=\mathrm{FAIL})
=
\mathrm{BLOCK}.
```

On `W_h`, the complete-response kernel strictly refines:

```math
\ker_{W_h}(B_{\mathrm{auth},1})
\subsetneq
\ker_{W_h}(\widetilde B_{\mathrm{auth},0}).
```

Authority-dependency ablation removes the required path before evaluation, and
evaluator replay removes the new complete-response discrimination.

When the graph identity, edge cut, original dependency-use records,
no-alternate-path condition, evaluator identity, fail-closed evaluator contract,
and evaluator replay are all recorded and reproduced, the PULSEmech
required-gate application is an instance of the response-level discrimination
corollary in Section 6.3.1.

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
→ discrimination removed by authority-dependency ablation and evaluator replay
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
\phi_\Lambda,
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

Preservation of actually used carriers:

```math
\phi_H
\bigl(
U_{H,\mathcal W}(x,\sigma,x')
\bigr)
=
U_{H,\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma),
\phi_X(x')
\bigr).
```

Preservation of actually used bindings:

```math
(\phi_H\times\phi_H)
\bigl(
U_{E,\mathcal W}(x,\sigma,x')
\bigr)
=
U_{E,\mathcal E}
\bigl(
\phi_X(x),
\phi_\Sigma(\sigma),
\phi_X(x')
\bigr).
```

Preservation of actually executed transition-rule identities:

```math
\phi_\Lambda
\bigl(
U_{\Lambda,\mathcal W}(x,\sigma,x')
\bigr)
=
U_{\Lambda,\mathcal E}
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
preservation of the comparison pullback
identical quantifier domain
identical system boundary
```

## 15.3 Transfer of the specific property

Let:

```math
\mathrm{Tr}_{\phi}
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
\mathrm{Tr}_{\phi}(\tau_{\mathcal W})
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
\mathrm{Tr}_{\phi}(\tau_{\mathcal W})
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
\mathrm{Tr}_{\phi}(\tau_{\mathcal W})
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

A claim of operational dimension opening contains at least the following
records:

```text
before_system
→ exact identification of the old transition machine or old evaluator structural state

after_system
→ exact identification of the new transition machine or new evaluator structural state

ambient_structure
→ common transition-machine type or common evaluator structural-state type

ambient_input_domain
→ common witness-input domain

state_embedding
→ embedding of old states when the witness lies in the embedding image

input_embedding
→ embedding of old inputs when the witness lies in the embedding image

comparison_pullback
→ total map p₀ from every point of the fixed witness domain to an old-machine input

comparison_preservation
→ proof that the pullback preserves the old witness meaning and response

change_unit
→ exact transition-machine unit or exact response-dependency unit

ablation_realization
→ transition_machine or dependency_evaluator

activation_path
→ how the operational unit becomes active

used_carrier_record
→ U_H for a transition-machine realization

used_binding_record
→ U_E for a transition-machine realization

used_rule_record
→ U_Λ for a transition-machine realization

uses_relation
→ proof that a transition-machine witness use record intersects κ

response_dependency_record
→ original dependency graph, exact E_κ^dep edge cut, U_dep^auth traversal, authority-bearing sink set, and proof that no required alternate path survives for a dependency-evaluator realization

witness_domain
→ fixed W domain

witness_class
→ reachability_opening or discrimination_opening

kernel_scope
→ exact two-point domain or a proved no-merging condition for a larger domain

before_profile
→ Def and kernel in the lifted old response

after_profile
→ Def and kernel in the new machine

ablation_contract
→ exact three-branch T^{-κ} definition for a transition-machine realization,
  or exact dependency-edge deletion, evaluator contract, and evaluator-replay proof obligation for a dependency-evaluator realization

ablation_profile
→ Def and kernel in the ablation machine or in the response generated by the ablated dependency evaluator

observation_boundary
→ common semantic-state, output, and consequence spaces

complete_response_contract
→ exact B response used for discrimination, including every compared component

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
the two-point witness pair belongs to one complete-response class

after:
the pair belongs to two complete-response classes

ablation:
the pair returns to one complete-response class
```

A larger-domain kernel claim additionally records the no-merging proof.

# 17. Main theorem

## The theorem of the Workshop decimal number system and operational dimension opening

Let:

```math
\mathcal M
=
(X,\Sigma,H,\Lambda,A,R,T,U,\nu,O,C,Q)
```

be a Workshop machine, with:

```math
U=(U_H,U_E,U_\Lambda).
```

Then the following claims hold separately.

### I. Quantitative growth

```math
Q(y)>Q(x)
```

by itself does not prove a change in operational signature or capability
profile.

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

This is neither sufficient nor necessary for every operational dimension
opening.

### IV. `\kappa`-dependent operational behavior change

Let `W\subseteq\mathcal D_1` carry a total comparison pullback:

```math
p_0:
W
\rightarrow
\mathcal D_0,
```

and let:

```math
\widetilde B_{\mathcal M_0}
=
B_{\mathcal M_0}\circ p_0.
```

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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w),
```

then the after-response carries a `\kappa`-dependent operational behavior
change.

If also:

```math
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
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
B_{\mathrm{Abl}_{\kappa}(\mathcal M_1)}(w)
=
\mathrm{undefined},
```

then `\kappa` creates a reachability opening.

### VI. Discrimination opening

Let:

```math
\widetilde B_0,
\qquad
B_1,
\qquad
B_1^{-\kappa}
:
\mathcal D
\rightarrow
\mathcal B
```

be complete responses of one common type.

The ablated response must be generated before response interpretation by one of
the typed realizations:

```text
transition-machine realization
→ B₁^{-κ} is generated by the ablated transition machine

dependency-evaluator realization
→ B₁^{-κ} is generated by replaying the same evaluator on the ablated structural state
```

Fix:

```math
W_{12}
=
\{w_1,w_2\}.
```

If:

```math
\widetilde B_0(w_1)
=
\widetilde B_0(w_2),
```

```math
B_1(w_1)
\neq
B_1(w_2),
```

and:

```math
B_1^{-\kappa}(w_1)
=
B_1^{-\kappa}(w_2),
```

then:

```math
\ker_{W_{12}}(B_1)
\subsetneq
\ker_{W_{12}}(\widetilde B_0),
```

and `\kappa` creates a discrimination opening on the fixed pair.

The restored equality must follow from the ablated machine or ablated evaluator
structure and its replay contract. A post-hoc substitution on completed
responses is not an ablation proof.

A larger-domain strict-refinement claim additionally requires the no-merging
condition.

### VII. The first decimal opening

In the `9 → 10` witness:

```math
T_1(9,+1)=\bot,
```

```math
T_2((9,0),+1)=(0,1),
```

```math
U_{H,2}((9,0),+1,(0,1))
=
\{h_0,h_1\},
```

```math
U_{E,2}((9,0),+1,(0,1))
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

An external theorem may determine a conclusion about the Workshop machine
when:

```text
preservation of carrier, binding, state, input, transition,
transition-use records, semantic state, output, and consequence is proved

and

transfer and required reflection of the specific theorem property are proved
```

QED.

# 18. The Workshop calculation order

The examination order consists of a common proof core and conditional
mechanism-specific branches.

```text
Common proof core

1. What are the exact before and after systems or structural states?

2. What is the complete fixed witness domain W?

3. Is the old response defined on every point of W through a total comparison pullback p₀?

4. What are the old and new complete-response Def and kernel profiles on W?

5. For discrimination, is W exactly the witnessed pair, or has no-merging been proved on the larger domain?

6. Did a reachability or complete-response discrimination opening occur?

7. Which ablation realization is used?
   - transition_machine
   - dependency_evaluator

Only the selected realization branch is required for the witness. The other
branch is not an applicable proof requirement.

Quantitative and place-value branch, when the claim concerns a numerical threshold

8. Which quantitative coordinate changed?

9. Which finite digit range closed?

10. Did the minimum length of the normalized representation increase?

Transition-machine branch

11. Which ambient carrier was already present?

12. Which carrier became newly active?

13. Which carriers were actually read, written, or otherwise required?

14. Which binding was enabled under the signal?

15. Which binding was actually traversed?

16. Which transition-rule identity was executed?

17. How is the three-branch T^{-κ} function defined?

18. Does U_H, U_E, or U_Λ intersect H_κ, E_κ, or Λ_κ?

Dependency-evaluator branch

19. What is the exact original dependency graph?

20. Which E_κ^dep edge cut is removed before evaluation?

21. Does the original U_dep^auth record traverse that cut?

22. Does the ablated graph remove every required and alternate required path to S_auth?

23. Is the same recorded evaluator replayed on the ablated graph?

24. Which complete response follows from the proved fail-closed evaluator contract?

Common closure

25. Does the response generated from the selected ablated structure remove the strict capability change?

26. Can a mere uniform output substitution, post-hoc response replacement, or decision-only projection be excluded?

27. Which semantic target state, output, or consequence changed?

28. Can the result be reproduced with identical transition-use records or identical dependency-graph and evaluator records?

29. When an external theorem is used, has operation preservation been proved?

30. Have transfer and reflection of the specific property been proved?
```

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
+ actual transition-use or authority-dependency-use witness
+ restoring response derived from the selected ablated structure
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
