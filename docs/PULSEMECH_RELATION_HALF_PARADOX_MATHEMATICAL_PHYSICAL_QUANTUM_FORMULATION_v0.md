# PULSEmech Relation and Half-Paradox — Mathematical, Physical, and Quantum-Mechanical Formulation v0

**Status:** Technical note  
**Technical scope:** Mathematical systems, classical mechanics, control theory, information theory, finite-dimensional quantum mechanics, and PULSEmech decision mechanics  
**Normative impact:** None  
**Release authority:** None  
**Policy impact:** None  
**Runtime impact:** None  

## 1. Purpose

This note formulates the PULSEmech terms **relation**, **half-paradox**,
**complete paradox**, **sparse time**, **dense time**, and **tick–tock–tek**
through mathematical, classical-physical, control-theoretic,
information-theoretic, quantum-mechanical, and PULSEmech decision structures.

The document analyzes one mechanical failure mode:

```text
a partial state, projection, marginal, measurement, or local description
is treated as sufficient for a larger state or decision
without satisfying the corresponding sufficiency condition
```

The selected partial description may be correct within its declared scope.

The failure begins when the target is enlarged without adding the state
variables, conditions, correlations, or evidence required by that larger
target.

The central distinction is:

```text
partial but sufficient for the declared target
≠ half-paradox

partial and insufficient for the declared target,
but treated as complete
= half-paradox
```

The note uses standard mathematical and physical structures to make that
distinction testable.

---

## 2. Formal scope and term definitions

The terms **half-paradox** and **complete paradox** label two
target-relative information states.

### 2.1 Half-paradox

A half-paradox is a partial description whose validity range is exceeded.

```text
valid partial observation
+ missing relation
+ missing condition set
+ missing consequence path
+ enlarged target
= half-paradox
```

### 2.2 Complete paradox

A complete paradox is the relation-bearing description required to evaluate
the relevant partial descriptions against the declared target.

No symmetry, equal-weight, equal-probability, or equal-physical-status
assumption is included.

The description contains the state variables, transformations, conditions,
correlations, and consequence paths required by the target.

### 2.3 Relative completeness

Completeness is always relative to a target.

A measurement set may be insufficient for full state reconstruction while
remaining sufficient for one narrow decision.

Therefore this note distinguishes:

```text
state completeness
decision completeness
```

A model is state-complete for a declared state space when it can distinguish
all physically distinct admissible states.

A model is decision-complete when it contains enough information to determine
the declared decision, even if it does not reconstruct every state variable.


### 2.4 Technical contribution

The mathematical ingredients used in this note are standard.

The technical contribution is their unified target-relative use for classifying
when a valid partial representation becomes an insufficient complete decision
basis, together with the corresponding PULSEmech decision-mechanism mapping.

---

## 3. General mathematical system

Let a system be represented by:

```math
\Sigma =
\left(
\mathcal X,
\Theta,
\mathcal U,
\Phi,
\mathcal Y,
H,
\mathcal C,
\mathcal R
\right).
```

Where:

- $\mathcal X$ is the admissible state space;
- $\Theta$ is the condition or parameter space;
- $\mathcal U$ is the input or control space;
- $\Phi$ is the state-transition map;
- $\mathcal Y$ is the observation space;
- $H$ is the measurement or observation map;
- $\mathcal C$ is the consequence map;
- $\mathcal R$ is the declared relation or constraint structure.

For a discrete transition:

```math
x_{k+1} = \Phi(x_k,u_k,\theta_k),
```

```math
y_k = H(x_k,\theta_k),
```

```math
c_k = \mathcal C(x_k,u_k,x_{k+1},\theta_k).
```

A relation may be represented as a family of constraints:

```math
\mathcal R_j(x,u,\theta)=0,
```

or inequalities:

```math
g_j(x,u,\theta)\le 0.
```

The system is not determined by one isolated value.

Its operating description is carried by the connected tuple:

```math
(x,\theta,u,\Phi,H,\mathcal C,\mathcal R).
```

Removing any component may be harmless for a narrow target.

It becomes a half-paradox when the removed component can change the declared
result.

---

## 4. Half-paradox as a non-injective projection

Let:

```math
\pi_A:\mathcal X\rightarrow\mathcal X_A
```

be a projection onto a partial state.

The projection is non-injective when there exist physically distinct states
$x_1$ and $x_2$ such that:

```math
x_1\not\sim x_2,
```

but:

```math
\pi_A(x_1)=\pi_A(x_2).
```

The symbol $\sim$ permits physically irrelevant equivalences, such as a gauge
equivalence or global phase.

If $\pi_A$ is non-injective, the partial state does not uniquely determine the
full physical state.

A half-paradox occurs when the inference:

```math
\pi_A(x)\mapsto x
```

is treated as unique even though it is not.

The mechanical defect is not that $\pi_A(x)$ is false.

The defect is that distinct compatible states have been collapsed into one
visible value.

### 4.1 Exact consistency set

The exact consistency-set statements in this section assume a deterministic,
noise-free observation model.

For an observation $y$, define:

```math
\mathcal K(y)
=
\left\{
x\in\mathcal X:
H(x)=y
\right\}.
```

A valid exact reconstruction requires both:

```math
\mathcal K(y)\ne\varnothing
```

and:

```math
\left|\mathcal K(y)/{\sim}\right|=1.
```

The non-emptiness condition states that at least one admissible state is
compatible with the observation.

The quotient-cardinality condition states that all compatible states belong to
one physically equivalent class.

If:

```math
\mathcal K(y)=\varnothing,
```

the observation is incompatible with the declared exact model.

If multiple inequivalent compatible states remain, full-state reconstruction
is non-unique.

### 4.2 Noisy observations

For noisy observations, exact equality must be replaced by a declared
statistical or tolerance model.

Examples include:

- a tolerance consistency set;
- a likelihood function;
- a confidence region;
- a credible region;
- a posterior distribution.

A tolerance set may be written as:

```math
\mathcal K_\varepsilon(y)
=
\left\{
x\in\mathcal X:
\left\|H(x)-y\right\|\le\varepsilon
\right\},
```

where the norm, tolerance, and measurement units must be declared.

A forced point estimate must not be confused with unique state reconstruction.

### 4.3 Uncertainty set instead of forced certainty

The correct output of an incomplete exact measurement is not an invented unique
state.

It is the remaining admissible set:

```math
x\in\mathcal K(y).
```

For a noisy model, the correct carrier is the declared tolerance set,
likelihood, confidence region, or posterior distribution.

The half-paradox replaces the remaining uncertainty with an unsupported point
estimate and then forgets that the replacement occurred.

---

## 5. Decision sufficiency

Full state reconstruction is not required for every valid decision.

Let:

```math
D:\mathcal X\rightarrow\mathcal D
```

be a declared decision function.

A partial observation $\pi_A(x)$ is sufficient for that decision if there
exists a function $\widetilde D$ such that:

```math
D(x)=\widetilde D(\pi_A(x))
```

for every admissible $x$.

Equivalent failure criterion:

```math
\exists x_1,x_2\in\mathcal X:
\pi_A(x_1)=\pi_A(x_2)
\quad\text{and}\quad
D(x_1)\ne D(x_2).
```

If such $x_1,x_2$ exist, the projection is not sufficient for the declared
decision.

This gives a precise half-paradox test:

```text
same visible partial state
+ different correct decisions
= partial state is insufficient for that decision
```

A partial view is not defective merely because it is partial.

It is insufficient when the decision rule exceeds the information carried by
the view.

---

## 6. Signal detection, observation refinement, identifiability, and admissible control

The operational chain is:

```text
detectable residual
→ observation refinement
→ consistency-set reduction
→ target-relative identifiability
→ constraint evaluation
→ admissible control transition
```

### 6.1 Residual signal

Let $\widehat y(t)$ be the output predicted by the current model and $y(t)$ the
recorded output.

Define the residual:

```math
r_y(t)=y(t)-\widehat y(t).
```

A signal is detected when, for a declared norm and threshold:

```math
\|r_y(t)\|>\varepsilon.
```

The norm, threshold, sampling interval, and measurement units must be declared.

### 6.2 Observation refinement

Observation refinement expands the observation map:

```math
H
\longrightarrow
H^+
=
(H,h_{m+1},\ldots,h_{m+q}).
```

The intended result is a smaller consistency set:

```math
\mathcal K_{H^+}(y^+)
\subseteq
\mathcal K_H(y).
```

The refinement is sufficient for the declared target when the remaining
compatible equivalence classes no longer produce different target results.

### 6.3 Identifiability and target sufficiency

For an exact deterministic observation model, unique full-state
identification requires:

```math
\mathcal K(y)\ne\varnothing
\quad\land\quad
\left|\mathcal K(y)/{\sim}\right|=1.
```

For exact decision sufficiency, the decision must be constant over a non-empty
consistency set:

```math
\mathcal K(y)\ne\varnothing
```

and:

```math
D(x)=d_*
\qquad
\forall x\in\mathcal K(y)
```

for one declared decision value $d_*$.

For noisy observations, exact consistency must be replaced by the declared
tolerance, likelihood, confidence-region, or posterior model.

A point estimate produced by an estimator is not, by itself, proof of unique
state identification.

State identification and decision sufficiency do not require the existence of
an available control input.

### 6.4 Constraint binding after state identification

This section defines only a mechanical constraint-binding analogue.

Let:

```math
\mathcal U_{\mathrm{adm}}(x,\theta)
=
\left\{
u\in\mathcal U:
g_j(x,u,\theta)\le 0
\ \forall j
\right\}.
```

Before the relevant state and parameter relation is identified,
$\mathcal U_{\mathrm{adm}}$ may be unevaluable.

After identification, the applicable constraints and consequence map become
computable.

The ordering is:

```text
identified state relation
→ computable consequence map
→ computable admissible-control set
```

not:

```text
control transition
→ state relation inferred retroactively
```

### 6.5 Reachable admissible controls and transition

Let $\mathcal U_{\mathrm{reach}}(x)$ be the set of control inputs the system can
realize from state $x$.

Define the executable control set:

```math
\mathcal U_{\mathrm{exec}}(x,\theta)
=
\mathcal U_{\mathrm{adm}}(x,\theta)
\cap
\mathcal U_{\mathrm{reach}}(x).
```

The set may be empty, a singleton, or contain multiple admissible controls.

After selecting:

```math
u\in\mathcal U_{\mathrm{exec}}(x,\theta),
```

the transition is:

```math
x^+=\Phi(x,u,\theta),
```

and the consequence is:

```math
c=\mathcal C(x,u,x^+,\theta).
```

The selected control input determines the realized transition and consequence
within the already evaluated constraint structure.

---

## 7. Observability as a formal relation test

Consider a continuous-time linear time-invariant system:

```math
\dot x(t)=Ax(t)+Bu(t),
```

```math
y(t)=Cx(t).
```

For an $n$-dimensional state, define the observability matrix:

```math
\mathcal O
=
\begin{bmatrix}
C\\
CA\\
CA^2\\
\vdots\\
CA^{n-1}
\end{bmatrix}.
```

The system is observable when:

```math
\mathrm{rank}(\mathcal O)=n.
```

If:

```math
\mathrm{rank}(\mathcal O)<n,
```

there exists a nonzero unobservable direction:

```math
v\in\ker(\mathcal O).
```

Then, under the same input history and the same known system matrices, the
distinct initial states:

```math
x_0
```

and:

```math
x_0+v
```

produce the same output history.

Treating that output history as a unique full state is a mathematical
half-paradox.

The output is real.

The unique-state inference is not supported.

This is the exact finite-dimensional LTI observability criterion.

Noise, unknown inputs, parameter uncertainty, time variation, and nonlinear
dynamics require their own declared observability or identifiability model.

### 7.1 Target-relative observability

A system need not be fully observable to support a narrow decision.

If the declared decision is insensitive to every unobservable direction, then
the available observation may still be decision-complete.

The required question is not:

```text
Is every hidden variable known?
```

It is:

```text
Can any hidden compatible state change the declared decision?
```

---

## 8. Classical probability: marginals do not determine relation

Let $A$ and $B$ be two binary variables.

### 8.1 Independent distribution

```math
p_{\mathrm{ind}}(a,b)=\frac14
```

for all four pairs.

Then:

```math
p_A(0)=p_A(1)=\frac12,
```

```math
p_B(0)=p_B(1)=\frac12.
```

### 8.2 Perfectly correlated distribution

Let:

```math
p_{\mathrm{corr}}(0,0)=\frac12,
```

```math
p_{\mathrm{corr}}(1,1)=\frac12,
```

and the other two probabilities be zero.

The marginals are still:

```math
p_A(0)=p_A(1)=\frac12,
```

```math
p_B(0)=p_B(1)=\frac12.
```

The local distributions are identical in both cases.

The relations are not.

For the independent distribution:

```math
I(A;B)=0.
```

For the perfectly correlated distribution:

```math
I(A;B)=1\ \text{bit}.
```

Therefore:

```text
same marginals
≠ same joint state
```

A marginal treated as the full joint distribution is a direct probabilistic
half-paradox.

---

## 9. Post-processing cannot restore lost state information

Let $X$ be the underlying state, $Y$ an observation, and $M$ a downstream
metadata record, score, certificate, or summary generated only from $Y$:

```math
X\rightarrow Y\rightarrow M.
```

The data-processing inequality gives:

```math
I(X;M)\le I(X;Y).
```

A downstream representation cannot contain more information about $X$ than the
observation from which it was generated.

Therefore:

```text
incomplete observation
→ downstream representation
```

cannot become:

```text
complete state reconstruction
```

through formatting, signing, scoring, or metadata transformation alone.

A cryptographic signature can authenticate the origin and integrity of $M$.

It does not add state distinctions absent from $Y$.

```text
cryptographic authenticity
≠ informational completeness
```

A downstream representation may preserve or summarize information.

It cannot reconstruct distinctions already destroyed by a non-injective
projection unless new independent evidence is introduced.

---

## 10. Classical mechanics: lever relation

For an ideal lever in static equilibrium:

```math
\sum \tau = 0.
```

With effort force $F_e$, effort arm $d_e$, load force $F_l$, and load arm
$d_l$:

```math
F_e d_e = F_l d_l.
```

The ideal mechanical advantage is:

```math
\mathrm{MA}
=
\frac{F_l}{F_e}
=
\frac{d_e}{d_l}.
```

For an ideal quasistatic and lossless displacement, the input and output work
magnitudes satisfy:

```math
\left|F_e\,\delta s_e\right|
=
\left|F_l\,\delta s_l\right|.
```

Equivalently, with a signed virtual-displacement convention:

```math
F_e\,\delta s_e
+
F_l\,\delta s_l
=
0.
```

The smaller effort force is related to a larger displacement or arm.

The load force alone does not determine the operating requirement.

The effort force alone does not determine the result.

The relation is carried by force, distance, geometry, and support.

A force-only description is a half-paradox if it is used to infer the complete
lever operation.

Real levers additionally contain friction, deformation, finite mass, and other
losses.

Those conditions belong to the relation rather than to the isolated force
value.

---

## 11. Classical mechanics: harmonic oscillator state

For a one-dimensional harmonic oscillator:

```math
H(q,p)
=
\frac{p^2}{2m}
+
\frac{kq^2}{2}.
```

The state is:

```math
x=
\begin{bmatrix}
q\\
p
\end{bmatrix}.
```

The dynamics are:

```math
\dot q=\frac{p}{m},
```

```math
\dot p=-kq.
```

Two states may have the same position:

```math
q_1=q_2,
```

but different momenta:

```math
p_1\ne p_2.
```

Their future trajectories differ immediately because:

```math
\dot q_1\ne\dot q_2.
```

Therefore:

```text
position
≠ complete oscillator state
```

Treating $q$ alone as the full state is a half-paradox for trajectory
prediction.

It may still be sufficient for a target that depends only on instantaneous
position.

Again, sufficiency is target-relative.

---

## 12. Geometric optics: mirror relation

Let a mirror plane be defined by a unit normal vector $n$ and scalar $d$:

```math
n\cdot x=d.
```

The reflected point corresponding to a physical point $x$ is:

```math
x'
=
x
-
2(n\cdot x-d)n.
```

The virtual image position is not an independent object position.

It is generated by the reflection relation.

The observed appearance also depends on:

- source position;
- mirror geometry;
- propagation of light;
- observation point;
- occlusion and aperture conditions.

The mechanical relations include:

```text
physical object ↔ virtual image
real object position ↔ apparent image position
incident direction ↔ reflected direction
observer position ↔ observed appearance
```

Treating the apparent image coordinate $x'$ as an independent physical object
coordinate removes the transformation that created it.

That is a geometric half-paradox.

---

## 13. Sparse time and dense time as dynamical regimes

**Sparse time** and **dense time** are workshop terms.

They do not mean that physical time itself has a material density.

They describe the operational density, reach, and return speed of connected
state transitions.

Consider a networked dynamical system:

```math
\dot x_i
=
f_i(x_i)
+
\sum_j a_{ij}g_{ij}(x_i,x_j).
```

A regime should not be reduced to one unlabelled scalar.

Useful measurement axes include:

| Quantity | Symbol | Typical unit |
|---|---:|---:|
| event rate | $\lambda$ | $\mathrm{s}^{-1}$ |
| mean coupling degree | $\bar k$ | dimensionless |
| graph edge density | $\eta$ | dimensionless |
| feedback latency | $\tau_f$ | $\mathrm{s}$ |
| propagation velocity | $v_p$ | $\mathrm{m\,s^{-1}}$ or hops $\mathrm{s}^{-1}$ |
| spectral abscissa | $\alpha(J)$ | $\mathrm{s}^{-1}$ |
| finite-time response gain | $\left\|e^{Jt}\right\|$ | dimensionless |

Where $J$ is the Jacobian of the dynamics around the operating point:

```math
J
=
\left.
\frac{\partial F}{\partial x}
\right|_{x=x_*}.
```

The spectral abscissa is:

```math
\alpha(J)
=
\max_{\lambda\in\sigma(J)}
\mathrm{Re}\lambda.
```

For the local LTI model, the spectral abscissa characterizes asymptotic
exponential behavior.

It does not by itself bound all finite-time transient amplification when $J$ is
non-normal.

A finite-time response measure may instead use:

```math
\left\|e^{Jt}\right\|.
```

The norm and the time interval must be declared.

### 13.1 Sparse operational time

A sparse regime tends toward:

```text
low event rate
low coupling degree or edge density
long feedback latency
limited propagation reach
```

A consequence may return slowly or remain local.

### 13.2 Dense operational time

A dense regime tends toward:

```text
high event rate
high coupling degree or edge density
short feedback latency
broad propagation reach
```

A local transition can reach many dependent states before the originating
state is re-evaluated.

### 13.3 Density is not instability

High coupling density does not by itself imply instability.

Linearized perturbations evolve approximately as:

```math
\delta x(t)
\approx
e^{J(t-t_0)}
\delta x(t_0).
```

Asymptotic growth or decay depends on the eigenstructure, damping, feedback
sign, delay, and nonlinear operating region.

Finite-time growth also depends on modal geometry and non-normality.

A system with:

```math
\alpha(J)<0
```

may still exhibit transient amplification when:

```math
\left\|e^{Jt}\right\|>1
```

over a finite interval.

A dense stable system may attenuate disturbances rapidly.

A dense asymptotically stable but non-normal system may transiently amplify
disturbances before decay.

A dense unstable system may amplify them persistently.

The workshop distinction concerns consequence reach and feedback structure,
not an automatic stability verdict.

---

## 14. Tick–tock–tek as a response map

The workshop sequence:

```text
tick → tock → tek
```

can be represented mechanically.

### 14.1 Tick: recorded state

```math
\mathrm{tick}
=
x(t_0).
```

### 14.2 Tock: transition

```math
\mathrm{tock}
=
x(t_1)
=
\Phi_{t_1,t_0}(x(t_0),u,\theta).
```

### 14.3 Tek: propagated consequence

For a perturbation introduced in component $i$, define a response kernel:

```math
G_{ji}(t,t_0)
=
\frac{\partial x_j(t)}
{\partial x_i(t_0)}.
```

Then:

```math
\delta x_j(t)
\approx
G_{ji}(t,t_0)\,
\delta x_i(t_0).
```

The **tek** is the response field:

```text
which components changed
by how much
after what delay
through which coupling path
with what return effect
```

To compare components with different physical units, define normalized states:

```math
\widetilde x_j=\frac{x_j}{s_j},
```

where $s_j$ carries the unit of $x_j$.

A dimensionless average impact measure over $[t_0,T]$ may then be written:

```math
\mathcal I_i(T)
=
\frac{1}{T-t_0}
\sum_j
w_j
\int_{t_0}^{T}
\left|
\frac{\partial \widetilde x_j(t)}
{\partial \widetilde x_i(t_0)}
\right|
dt,
```

with dimensionless weights $w_j$.

This is one possible operational measure, not a universal physical definition
of impact.

The important structure is:

```text
state
→ transition
→ propagated response
→ returned state change
```

---

## 15. Quantum-mechanical formal scope

The quantum sections use finite-dimensional Hilbert spaces, density operators,
positive-operator-valued measurements, informational completeness,
noncommuting observables, reduced states, partial trace, and reduced
open-system dynamics under explicitly stated assumptions.

These structures provide formal test cases for:

```text
projection
measurement context
state reconstruction
correlation loss
reduced-state information loss
```

Unless otherwise stated, all quantum systems in the following sections are
finite-dimensional.

---

## 16. Quantum state and measurement relation

A quantum state is represented by a density operator:

```math
\rho\ge 0,
```

```math
\mathrm{Tr}\rho=1.
```

A measurement is represented by a positive-operator-valued measure:

```math
\{E_k\},
```

with:

```math
E_k\ge 0,
```

```math
\sum_k E_k=I.
```

The outcome probabilities are:

```math
p(k|\rho)
=
\mathrm{Tr}(\rho E_k).
```

Define the measurement map:

```math
\mathcal M_E(\rho)
=
\left(
\mathrm{Tr}(\rho E_1),
\ldots,
\mathrm{Tr}(\rho E_m)
\right).
```

If there exist distinct states $\rho_1\ne\rho_2$ such that:

```math
\mathcal M_E(\rho_1)
=
\mathcal M_E(\rho_2),
```

the measurement is not informationally complete for the declared state class.

Treating that probability vector as a unique full quantum state is a quantum
half-paradox in the workshop sense.

The measured probabilities are valid.

The unique-state inference is not.

---

## 17. Informational completeness and tomography

A POVM is informationally complete for arbitrary $d$-dimensional density
operators when its effects span the real vector space of Hermitian operators,
which has dimension $d^2$.

Operationally, informational completeness means:

```math
\mathcal M_E(\rho_1)
=
\mathcal M_E(\rho_2)
\Longrightarrow
\rho_1=\rho_2.
```

Quantum state tomography uses repeated measurements on identically prepared
systems and an informationally sufficient measurement design to estimate
$\rho$.

For pure states, reconstruction is only required up to global phase:

```math
|\psi\rangle
\sim
e^{i\phi}|\psi\rangle.
```

The formal lesson is:

```text
one outcome
≠ state

one expectation value
≠ state

one measurement basis
≠ generally complete state information

informationally complete measurement relation
→ state reconstruction becomes possible
```

The complete paradox is not one side of a measurement opposition.

It is the full state–measurement–probability relation required for the declared
reconstruction target.

---

## 18. Noncommuting observables

Let $A$ and $B$ be self-adjoint observables.

If:

```math
[A,B]=AB-BA\ne 0,
```

their measurement statistics cannot generally be reduced to one shared set of
simultaneously sharp values.

For states and operators for which the variances and commutator expectation are
defined, the Robertson relation is:

```math
\Delta A\,\Delta B
\ge
\frac12
\left|
\mathrm{Tr}
\left(
\rho[A,B]
\right)
\right|.
```

This does not mean:

```text
A is true and B is false
```

or:

```text
A and B are equally true
```

It means that the state, operators, and measurement context form a relation
whose constraints cannot be replaced by one isolated observable.

The half-paradox is not the existence of noncommutation.

It is treating one measurement context as if it exhausted the state properties
relevant to every other context.

---

## 19. Entanglement: identical local states, different global relation

Consider the Bell state:

```math
|\Phi^+\rangle
=
\frac{|00\rangle+|11\rangle}{\sqrt2}.
```

Its density operator is:

```math
\rho_{\Phi}
=
|\Phi^+\rangle\langle\Phi^+|.
```

The reduced state of subsystem $A$ is:

```math
\rho_A
=
\mathrm{Tr}_B(\rho_{\Phi})
=
\frac{I_2}{2}.
```

The same is true for subsystem $B$.

Now consider the separable mixed state:

```math
\rho_{\mathrm{mix}}
=
\frac12|00\rangle\langle00|
+
\frac12|11\rangle\langle11|.
```

Its reduced states are also:

```math
\mathrm{Tr}_B(\rho_{\mathrm{mix}})
=
\frac{I_2}{2},
```

```math
\mathrm{Tr}_A(\rho_{\mathrm{mix}})
=
\frac{I_2}{2}.
```

The local states are identical.

The global states are not.

Their purities differ:

```math
\mathrm{Tr}(\rho_{\Phi}^2)=1,
```

```math
\mathrm{Tr}(\rho_{\mathrm{mix}}^2)=\frac12.
```

The Bell state contains coherent quantum correlation terms that the separable
mixture does not.

Therefore:

```text
same local reduced states
≠ same global quantum state
```

Treating $\rho_A$ and $\rho_B$ as sufficient to reconstruct the global state is
a direct quantum half-paradox.

The missing object is the relation carried by the correlations.

---

## 20. Partial trace as relation loss

For a joint system–environment state:

```math
\rho_{SE}(0),
```

with global unitary evolution:

```math
\rho_{SE}(t)
=
U(t)\rho_{SE}(0)U^\dagger(t),
```

the reduced system state is:

```math
\rho_S(t)
=
\mathrm{Tr}_E
\left[
\rho_{SE}(t)
\right].
```

The partial trace removes explicit environment degrees of freedom and
system–environment correlation detail.

The reduced trajectory need not be unitary even when the global trajectory is
unitary.

Under Markovian quantum-dynamical-semigroup assumptions, a reduced evolution
may be represented in GKLS form:

```math
\frac{d\rho}{dt}
=
-\frac{i}{\hbar}[H,\rho]
+
\sum_\mu
\left(
L_\mu\rho L_\mu^\dagger
-
\frac12
\left\{
L_\mu^\dagger L_\mu,
\rho
\right\}
\right).
```

The reduced equation is not the full closed-system state.

It is an effective relation after environment degrees of freedom have been
removed or compressed.

Treating reduced dynamics as the complete global dynamics without stating the
reduction assumptions is a half-paradox.

---

## 21. Quantum measurement does not create global completeness

A valid quantum measurement can produce a correct outcome while leaving much
of the pre-measurement state unidentified.

This is not a defect.

The defect appears only if the outcome is promoted beyond its information
content.

```text
valid outcome
+ unsupported completeness inference
= half-paradox
```

Similarly:

```text
verified local operator expectation
≠ complete density operator

verified subsystem state
≠ complete joint state

verified reduced dynamics
≠ complete system–environment dynamics
```

The mathematical carrier of completeness is injectivity or target sufficiency,
not the visual authority of a measurement label.

---

## 22. Dense operational time in quantum networks

For a many-component quantum system, increased coupling density can increase
the number of channels through which correlations and perturbations propagate.

This note does not define a quantum density of time.

The workshop term **dense time** may be applied operationally only through
declared quantities such as:

- interaction graph degree;
- interaction strengths, with energy units;
- characteristic correlation time, in seconds;
- decoherence time, in seconds;
- propagation or response bounds;
- number of coupled degrees of freedom;
- feedback or control latency.

A high number of couplings does not automatically imply rapid instability.

The Hamiltonian, dissipation, locality, symmetry, initial state, and control
structure determine propagation.

The correct statement is:

```text
more coupling paths
→ potentially broader consequence reach

not:

more coupling paths
→ automatic instability
```

No quantum-mechanical statement in this note depends on treating the workshop
term dense time as a formal quantum observable.

---

## 23. PULSEmech as a connected decision relation

Let:

- $E$ be recorded current-run evidence;
- $S$ be final machine-readable state;
- $P$ be declared policy;
- $\ell$ be the selected workflow lane;
- $r$ be the current-run identity against which evidence and final state are
  bound;
- $G_{\mathrm{eff}}$ be the workflow-effective materialized required gate set;
- $\Gamma(P,\ell)$ be the gate set declared by policy for lane $\ell$;
- $B(E,S,r)$ be the current-run evidence/state binding predicate;
- $V(P,\ell,G_{\mathrm{eff}})$ be materialization and lane-contract validity;
- $Q(S,G_{\mathrm{eff}})$ be strict gate evaluation.

Define materialization and lane-contract validity as:

```math
V(P,\ell,G_{\mathrm{eff}})
=
\begin{cases}
1,
&
G_{\mathrm{eff}}=\Gamma(P,\ell)
\ \land\
\text{materialization completed successfully}
\\
&
\land\
\text{$G_{\mathrm{eff}}$ satisfies the declared lane contract},
\\[4pt]
0,
&
\text{otherwise}.
\end{cases}
```

For a release-authorizing lane, the lane contract includes:

```math
G_{\mathrm{eff}}\ne\varnothing.
```

It may also include additional declared requirements, such as the exact policy
identity, policy digest, gate-set identity, and atomic materialization result.

Let:

```math
\mathrm{dom}(S)
```

denote the set of gate keys explicitly present in the final machine-readable
state.

Define strict gate evaluation as:

```math
Q(S,G_{\mathrm{eff}})
=
\begin{cases}
1,
&
G_{\mathrm{eff}}
\subseteq
\mathrm{dom}(S)
\ \land\
\forall g\in G_{\mathrm{eff}},
\ S[g]=\mathrm{true},
\\[4pt]
0,
&
\text{otherwise}.
\end{cases}
```

Here, $\mathrm{true}$ means the literal boolean value required by the strict
gate contract.

A missing gate key is not interpreted as false, true, null, or unknown.

It causes:

```math
Q(S,G_{\mathrm{eff}})=0.
```

A simplified decision relation is then:

```math
D(E,S,P,\ell,r)
=
\begin{cases}
\mathrm{allow},
&
B(E,S,r)=1
\ \land\
V(P,\ell,G_{\mathrm{eff}})=1
\ \land\
Q(S,G_{\mathrm{eff}})=1,
\\[4pt]
\mathrm{block},
&
\text{otherwise}.
\end{cases}
```

This decomposition is explicitly fail-closed:

```text
missing or invalid run binding
→ block

missing, failed, partial, or lane-invalid materialization
→ block

empty effective gate set where the lane contract forbids emptiness
→ block

missing required gate key
→ block

false, null, non-boolean, or malformed required gate value
→ block
```

No isolated carrier is sufficient.

```text
evidence without current-run binding
≠ release state

status without declared policy
≠ effective requirement set

policy without successful materialization
≠ workflow-effective gates

empty or lane-invalid materialized set
≠ valid effective gate set

gate identifier absent from final state
≠ passing gate

gate values without strict evaluation
≠ release decision

attestation without evidence admission
≠ materialized gate state

package verification without primary CI decision
≠ release authority
```

The PULSEmech mechanism is the connected relation:

```text
recorded evidence
→ final status
→ declared policy
→ valid workflow-effective materialized gates
→ strict fail-closed enforcement
→ primary CI allow/block decision
```

An isolated report, derived metadata record, attestation, or package is a
projection of that relation.

It becomes a half-paradox only when treated as the complete authority path.
---

## 24. Mechanical review tests

Before accepting a partial representation as sufficient, ask:

1. What is the declared full state space?
2. What physical equivalences are intentionally quotiented out?
3. What projection or measurement produced the visible value?
4. Is the projection injective on the admissible state class?
5. If not, what is the remaining consistency set?
6. Is full state reconstruction actually required?
7. Is the partial view sufficient for the declared decision?
8. Can two compatible hidden states require different decisions?
9. What independent measurement would separate those states?
10. What condition or parameter changes the relation?
11. What correlations are removed by marginalization or partial trace?
12. What consequence map connects transition to later state?
13. What are the units of every propagation or density measure?
14. Is the operational-time regime described by explicit axes?
15. Does a downstream label introduce new evidence, or only post-process an old observation?
16. Is a quantum measurement being treated as more informative than its POVM permits?
17. Is a reduced quantum state being treated as a complete joint state?
18. Was the workflow-effective gate set successfully and atomically materialized?
19. Does the materialized gate set exactly match the declared lane policy?
20. Does the lane contract require a non-empty gate set, and is that condition satisfied?
21. Are all required gate identifiers explicitly present in the final state domain?
22. Does the final PULSE decision still require the connected evidence–policy–materialization–gate–enforcement path?

---

## 25. Formal propositions

### Proposition 1 — projection loss

If $\pi_A$ is non-injective on the admissible physical state space, then the
partial state $\pi_A(x)$ does not uniquely determine $x$.

For exact reconstruction, the compatibility set must also be non-empty.

For noisy reconstruction, uniqueness requires a declared statistical or
tolerance model.

### Proposition 2 — decision insufficiency

A partial observation is insufficient for decision $D$ if two admissible states
share the same observation and require different decisions.

### Proposition 3 — partial does not mean defective

A partial observation is valid for a declared decision when the decision
factors through that observation.

### Proposition 4 — post-processing limit

A downstream label generated only from an observation cannot restore state
information lost by that observation.

### Proposition 5 — marginal relation loss

Equal marginals do not imply equal joint distributions or equal correlations.

### Proposition 6 — local quantum state loss

Equal reduced density operators do not imply equal global quantum states.

### Proposition 7 — measurement completeness

A quantum measurement identifies a state only when the measurement map is
injective on the declared state class, modulo physical equivalence.

### Proposition 8 — noncommutation is relational

Noncommuting observables impose joint statistical constraints; they do not
justify replacing one measurement context with a complete state inference.

### Proposition 9 — dense time is an operational regime

Sparse time and dense time describe declared coupling, propagation, and
feedback axes. They are not new physical dimensions or observables.

### Proposition 10 — impact requires propagation

A state transition is not a complete consequence description until its
propagated response and return path are included.

### Proposition 11 — PULSE authority is relational

PULSE release authority is carried by the connected evidence–state–policy–
materialization–enforcement path, not by any isolated report or artifact.

A valid allow result additionally requires:

- current-run evidence/state binding;
- successful lane-valid materialization;
- any lane-required non-empty gate-set condition;
- explicit presence of every required gate key;
- literal-true evaluation of every required gate.

---

## 26. Compact mechanical anchor

```text
projection
≠ full state

marginal
≠ joint relation

measurement outcome
≠ quantum state

reduced state
≠ global state

certificate
≠ restored information

transition
≠ propagated consequence

high coupling density
≠ automatic instability

attestation
≠ evidence admission

empty or invalid materialized gate set
≠ valid effective gate set

missing required gate key
≠ passing gate

package verification
≠ primary release decision

partial but decision-sufficient
≠ half-paradox

partial and decision-insufficient,
treated as complete
= half-paradox
```

---

## 27. References

1. R. E. Kalman, “On the General Theory of Control Systems,” Proceedings of the
   First International Congress of the International Federation of Automatic
   Control, Moscow, 1960.

2. R. E. Kalman, “Mathematical Description of Linear Dynamical Systems,”
   *Journal of the Society for Industrial and Applied Mathematics, Series A:
   Control*, vol. 1, no. 2, pp. 152–192, 1963.

3. C. E. Shannon, “A Mathematical Theory of Communication,” *Bell System
   Technical Journal*, vol. 27, pp. 379–423 and 623–656, 1948.

4. G. M. D’Ariano, M. G. A. Paris, and M. F. Sacchi, “Quantum Tomography,”
   arXiv:quant-ph/0302028, 2003.

5. G. M. D’Ariano, P. Perinotti, and M. F. Sacchi, “Informationally complete
   measurements on bipartite quantum systems: comparing local with global
   measurements,” arXiv:quant-ph/0507104, 2005.

6. H. P. Robertson, “The Uncertainty Principle,” *Physical Review*, vol. 34,
   pp. 163–164, 1929.

7. G. Lindblad, “On the Generators of Quantum Dynamical Semigroups,”
   *Communications in Mathematical Physics*, vol. 48, pp. 119–130, 1976.

8. V. Gorini, A. Kossakowski, and E. C. G. Sudarshan, “Completely positive
   dynamical semigroups of N-level systems,” *Journal of Mathematical Physics*,
   vol. 17, pp. 821–825, 1976.

---

## 28. Closing statement

The half-paradox is mechanically defined by an exceeded information boundary.

A projection may be valid.

A marginal may be valid.

A local state may be valid.

A measurement outcome may be valid.

A derived record may accurately preserve a completed check.

None becomes a complete state or decision merely by being correct within its
own declared scope.

The complete paradox restores the relation required by the target:

```text
state
+ conditions
+ transformation
+ measurement
+ correlation
+ consequence
+ declared decision boundary
```

In mathematics, the test is injectivity or decision sufficiency.

In classical physics, the test is whether omitted variables can change the
trajectory, balance relation, or conserved quantity.

In control theory, the test is observability or target-relative
identifiability.

In information theory, the test is whether the retained representation
preserves the distinctions required by the target.

In quantum mechanics, the test is informational completeness and preservation
of global correlation.

In PULSEmech, the test is whether the recorded
evidence–state–policy–materialization–enforcement path remains connected.

> The half-paradox is a valid fragment operating beyond its information limit.  
> The complete paradox is the restored relation that makes the limit explicit.
