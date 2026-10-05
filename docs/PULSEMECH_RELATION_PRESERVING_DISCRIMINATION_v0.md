# PULSEmech Transition Meter — Relation-preserving discrimination

## Target-relative evidence sufficiency and a finite Workshop witness

```yaml
document_role: supporting_measurement_note
repository_integration_status: documentation_with_companion_source
canonical_dependency: PULSEMECH_TRANSITION_METER.md
proposal_status: derived_workshop_application_with_finite_witness
transition_path_application_status: specified_not_executed
implementation_scope: offline_synthetic_test_harness
measurement_object: target_relative_relation_preservation
canonical_revision_reviewed: d2b184ccb1b1cc433e9f64d7dc0df9b4abff25a4
normative_policy_effect: none
release_authority_effect: none
gate_activation_effect: none
quantum_experiment_status: not_performed
physical_validation_status: not_performed
```

## 1. Starting point and bounded contribution

This note starts from the PULSEmech Workshop machine, its fixed complete-response
boundary, and its before / activation / same-ambient ablation criterion. It also
uses the relation note's target-relative sufficiency condition and nonempty
consistency-set requirement. It does not replace either document.

The concrete extension requirement examined here is:

> A measurement description must preserve the joint relation order needed by its
> declared target. Collecting every local value and every pairwise summary does
> not, by itself, establish that requirement.

The new work in this package is a bounded application of the existing criteria,
with a finite counterexample, a fixed-evaluator measurement machine, exact
consistency enumeration, and executable controls. It is not a claim that the
underlying parity construction is new mathematics, a new quantum law, or a
validated description of physical time.

An n-ary relation is allowed: R(x) need not be interpreted as only a list of
binary edges. A binary graph representation is not prohibited. An auxiliary
relation node or other encoding is acceptable when it preserves the relevant
joint distinctions, evaluation, and ablation response. The criterion is
preservation, not a preference for a notation.

## 2. Declare the target before selecting the witness

Fix a nonempty admissible witness domain W, a system and context boundary, and a
measurement family F. Let P_F(w) be exactly the observations made available by
that family. Let Z(w) be the declared target response or response statistic.

Define the compatible set at evidence e:

```math
K_F(e)=\{w\in W\mid P_F(w)=e\}.
```

Define the remaining possible target values:

```math
V_F(e)=\{Z(w)\mid w\in K_F(e)\}.
```

The three exact-model outcomes are distinct:

* K_F(e) empty: the evidence is incompatible with the declared model and bindings.
* K_F(e) nonempty and V_F(e) a singleton: the target is identified on this boundary.
* K_F(e) nonempty and V_F(e) has several values: the target is unresolved.

The empty set must not be called a successful identification through vacuous
truth. An unresolved set must not be replaced by zero, by a preferred member, or
by a fitted point estimate without an additional declared rule and claim limit.

The declared target need not reconstruct the complete state. Several compatible
states may support one target value. This is target sufficiency, not universal
knowledge of the system.

### 2.1 A necessary preservation test

If there exist w_0 and w_1 with

```math
P_F(w_0)=P_F(w_1),\qquad Z(w_0)\ne Z(w_1).
```

no single-valued function of P_F alone can give the correct target for both.
Equal inputs would require equal outputs. Further processing of that same
projection does not eliminate this witness.

### 2.2 Extension without outcome leakage

An additional independently specified relation observation $\Theta$ gives

```math
P_{F^+}(w)=\bigl(P_F(w),\Theta(w)\bigr).
```

On a fixed model and compatible evidence boundary,

```math
K_{F^+}(e,\theta)\subseteq K_F(e).
```

The target set can shrink, but no reduction is guaranteed: the added observation
may be redundant. The proposed relation must have its own measurement or
reconstruction rule; setting Theta(w) equal to a retrospectively chosen answer
is not a mechanism reconstruction.

Nor does a discriminating relation establish a unique physical cause. Different
mechanisms may implement the same input-output relation. The present witness
identifies a finite record statistic and a measurement-machine capability.

## 3. Exact finite witness: all pairs match, the triple does not

There are three binary carriers A, B, C. Each fixture is a complete materialized
cohort of four jointly bound records, not a random sample used to infer an
unobserved population. Each displayed record occurs once.

| Record | E: even fixture | O: odd fixture |
|---|---|---|
| 1 | 000 | 001 |
| 2 | 011 | 010 |
| 3 | 101 | 100 |
| 4 | 110 | 111 |

Each single carrier has counts (2,2). Each pair, AB, AC, and BC, has counts
(1,1,1,1) over 00,01,10,11, in both fixtures. These summaries are exactly equal,
not merely close within noise.

The operating target is fixed to the empirical fraction of records with an odd
number of active bits. Here $(a_i,b_i,c_i)$ is record $i$ in the four-record cohort:

```math
\begin{aligned}
z(a,b,c)&=(a+b+c)\bmod 2,\\
Z(w)&=\frac{1}{4}\sum_{i=1}^{4}z(a_i,b_i,c_i).
\end{aligned}
```

Thus Z(E)=0 and Z(O)=1. The target function is executable and is not supplied to
the evaluator as a fixture class label. The measurement machine infers its
possible values from the enabled evidence.

Consequently, every one-carrier and two-carrier histogram can agree while the
whole three-carrier operation has a different result. The counterexample is to
the sufficiency of those histograms, not to the existence or correctness of the
individual measurements.

A crucial boundary: the old representation contains pairwise **histograms**,
not pairwise records with shared trial identifiers. Preserving those identifiers
can permit reconstruction of the triple. Such an encoding retains the very
joint binding omitted by the old projection; it is not a counterexample to the
preservation requirement.

### 3.1 Exhaustive compatible domain

The declared domain W contains all histograms of four binary triples. There are
8 possible triples and 330 nonnegative integer count vectors summing to four.
The test harness enumerates every one.

With the single and pair histograms of either fixture, exactly two members of W
remain compatible: E and O. The correct target set is therefore {0,1}.

With the complete bound triple histogram, exactly one member remains. The target
set is {0} for E and {1} for O.

These exact sets depend on the four-record finite-domain contract. They are not
confidence intervals or a population-level identifiability claim.

## 4. Workshop before / activation / ablation mapping

The compared machines retain:

* the ambient source and input types;
* the witness records and declared source context;
* the evaluator `finite_joint_histogram_consistency_v0`;
* the target `empirical_odd_parity_fraction_v0`;
* the complete response type and observation interpretation.

Only enabled measurement bindings change. There is no carrier-removal ablation,
so this witness does not rely on storing a non-neutral value in a disabled
carrier. It exercises the Workshop binding-ablation case.

M_0 enables the one-carrier and pairwise observation bindings. M_1 additionally
enables kappa, the jointly bound triple-histogram accessor. Abl_kappa(M_1)
removes that binding and replays the same evaluator. The evaluator never reads
a fixture label, the precomputed true target, or an unenabled joint accessor.

Its complete response is fixed as:

```text
(definedness,
 semantic assessment state,
 output = (status, compatible histogram count, possible target values),
 consequence = diagnostic_only_no_external_effect)
```

| Machine | E target set | O target set | Distinguishes E/O? |
|---|---|---|---|
| M_0: singles and pairs | {0,1} | {0,1} | No |
| M_1: joint binding added | {0} | {1} | Yes |
| Abl_kappa(M_1) | {0,1} | {0,1} | No |

The old complete responses are equal; the new responses differ; the ablated
responses equal their corresponding old responses. This is a finite diagnostic
measurement-machine discrimination witness under the Workshop conditions.
It is not proof that a new physical dimension has been created.

The observation interpretation is fixed before evaluation; changing the report
format or its projection between machines is not used to create this witness.

### 4.1 Alternative-path control

A second valid joint accessor is added as a backup. When the primary binding is
ablated, the backup preserves discrimination. Only disabling both joint paths
restores the ambiguous result.

The individual primary accessor is therefore not necessary in the backup
configuration. A proof may not ignore the remaining path merely because an
original trace used the primary accessor.

### 4.2 Observation removal is not physical effect removal

The source histograms and their true target values remain unchanged throughout
measurement-binding ablation. What is lost is the meter's evidence-supported
ability to distinguish them. The ablated result is a defined unresolved report,
not a claim that the source operation has become undefined or has zero effect.

### 4.3 Accessor-test scope

The scoped accessor and read traces verify the behavior of this Python evaluator.
They are not an adversarial security boundary, process-isolation proof, or
production enforcement mechanism. No such claim is made.

## 5. Relation order: a general finite witness family

For $n\ge 2$, take the uniform finite ensembles of $n$-bit strings with even and odd
parity. Each ensemble has $2^{n-1}$ rows.

Select any nonempty proper subset $S$ of the carriers, with $|S|=k<n$. Fix any
assignment on $S$. There are $2^{n-k-1}$ completions of either parity, because at least
one unassigned bit remains and it can determine the required parity.

Each proper marginal is therefore uniform, with relative frequency $2^{-k}$, in
both ensembles. Yet full parity is always zero in one and always one in the
other.

Hence there is no fixed marginal-order cutoff k that suffices for every larger
parity target in this observation family. For n carriers, all proper marginal
histograms can agree while the declared n-carrier result differs.

The harness checks n=2 through n=8, covering all 494 nonempty proper projection
scopes. These finite checks accompany the argument; they do not substitute for
its quantifier over n.

This is not a sensor-count lower bound. A single scalar report can encode a
joint n-carrier operation. The relevant order is the support of the relation
being evaluated, not the number of displayed numbers or physical instruments.

The conclusion is relative to the admitted measurement family. A direct verified
parity measurement would be sufficient for this target without reconstructing
the full joint histogram. Full-state reconstruction is not a universal mandate.

## 6. Time and quantum transfer boundaries

### 6.1 What this adds to the time–relation–consequence question

The formalism need not begin by choosing one globally ordered event list. It
begins with the target, the participating carriers and bindings, the admitted
measurement family, and the distinctions that must survive observation.

A domain may bind A, B, C to three roles in one current configuration. It may
instead bind them to three identified stages of one process, provided the
same-process linkage is itself established. Local time labels and pairwise
summaries must not silently stand in for that joint linkage.

For the latter finite interpretation, the target can be implemented by an
accumulator starting at zero and toggling for each active bit. The materialized
rows then specify three-stage inputs. The final toggle state differs between
the two ensembles although their time-slice and two-slice histograms agree.
This is an alternative interpretation of the same finite witness, not a new
physical experiment.

Nothing in the witness proves that elapsed time itself causes the difference,
that time has physical material density, or that a universal definition of time
has been derived. The records may use identical clock labels. What the witness
requires preserving is the multi-part relation that can remain consequential
across those labels. Parity is also insensitive to permuting the component
order; this example is not an order-sensitivity test.

### 6.2 What must not be transferred to quantum data without proof

The binary triple witness has a jointly specified record domain by construction.
It does not establish that outcomes of incompatible quantum measurement contexts
can be pooled into one such domain. A quantum application would need its own
identified preparation, measurement context, admissible joint observations,
uncertainty treatment, and structure/response-preserving mapping.

No quantum raw dataset is analyzed in this package. No quantum causal model,
nonlinearity theorem, or hidden-variable model is inferred from it. The portable
object is the sufficiency and binding test, not the binary ensemble as a theory
of nature.

## 7. Actual offline results

The package executed 36 unit tests successfully. Within that suite:

* all 330 three-bit/four-record joint histograms were recovered when their full
  bound joint evidence was available;
* all 128 subsets of the seven observation scopes were checked for each of E and
  O, including evidence-addition monotonicity;
* all 494 proper scopes for n=2..8 were checked for equal parity-family marginals;
* every whole-row ordering of each four-row fixture preserved the result;
* before / after / ablation and alternative-route controls passed;
* malformed data, mixed contexts, conflicting evidence, and invalid bindings
  did not silently become an identified zero effect.

These are internal checks in 36 test methods, not 330 or 494 independent physical
experiments.

Additional results from the exact enumeration:

| Control | Compatible histograms | Target result |
|---|---:|---|
| No evidence | 330 | {0,1/4,1/2,3/4,1}; unresolved |
| All one-/two-carrier evidence, E or O | 2 | {0,1}; unresolved |
| Full bound triple evidence | 1 | {0} or {1}; identified |
| Contradictory pair relations | 0 | empty; incompatible |
| One-count per-bin tolerance on proper evidence | 116 | {0,1/4,1/2,3/4,1}; unresolved |
| First-carrier count, first-carrier target only | 100 | {1/2}; identified |

The tolerance is an explicit count bound, not a measured calibration or confidence
level. The last row verifies that target sufficiency does not require a unique
full state.

## 8. Bounded result and incorporation point

The current result is an operationally tested preservation requirement:

> Relation coverage is not established merely by covering every component and
> every pair. The relevant joint binding must either be retained, reconstructed
> under an explicit valid rule, or remain visibly unresolved for the target.

The existing Workshop R(x) can host this requirement; no change to vector-space
axioms is required by this witness. The prospective extension is a declared
relation-support and evidence-binding contract at the measurement layer, followed
by a Workshop discrimination witness where a new meter capability is claimed.

The next domain application must identify a concrete difference and the evidence
that carries its joint relation. It must not infer physical completeness from the
success of this finite example. The original local experiment did not modify the
repository. This publication adds documentation and a standalone synthetic
reproduction harness; it changes no active gate, policy, or authority configuration.


### 8.1 Direct contribution to the Transition Meter

The canonical Transition Meter, sections 3–5, identifies the gap between measured
endpoints and an evidence-bound transition identity. Different admissible paths
can have the same measured endpoints. The meter therefore needs evidence that
distinguishes the paths relevant to the claim.

This note addresses a subsequent question: **does the acquired evidence preserve
the relation needed to make that distinction?**

The finite witness shows that adding all local measurements and every pairwise
histogram does not automatically answer that question. Those summaries can still
collapse different joint configurations with different target responses. A high
count of individually covered components or pairs is not, on its own, a proof of
joint-relation sufficiency.

This is a concrete supporting witness for the meter's evidence-adequacy problem.
It is not a replacement proof of transition-path identity. The executed target
is a finite cohort statistic, not the unique causal path of a physical process.

The canonical architecture already preserves relation identity, evidence binding,
alternative paths, and unresolved status. This note does not establish a defect
in a production implementation or assume that the architecture restricts every
relation to a binary edge. It makes one information-loss failure mode explicit
and supplies an executable diagnostic control for it.

### 8.2 Applying the sufficiency rule to transition claims

For a future transition application, fix the system boundary, endpoint identities,
domain rules, and admissible path set $P_K(S_0,S_1)$. Let $e$ be the acquired evidence.
Write $p\sim_K e$ when path $p$ is compatible with $e$ under the declared rule $K$.
Define:

```math
\begin{aligned}
K_{\mathrm{path}}(e)&=\{p\in P_K(S_0,S_1)\mid p\sim_K e\},\\
V_g(e)&=\{g(p)\mid p\in K_{\mathrm{path}}(e)\}.
\end{aligned}
```

Here g is the declared target, fixed before assessment. It may ask whether a named
boundary was crossed, whether a specified relation carried a transition, or which
path identity occurred. A complete path-identity claim requires g to distinguish
the path equivalence classes admitted by that claim; a narrower g cannot silently
stand in for full path identity.

The decision rule is target-relative:

* K_path(e) empty: evidence and the declared model/bindings are incompatible;
* K_path(e) nonempty and V_g(e) singleton: g is identified on that boundary;
* K_path(e) nonempty and V_g(e) has several values: g remains unresolved.

Multiple admissible paths may support the same narrow target value. This can
justify that target without justifying a unique path or a necessary cause.
Conversely, an identified output or consequence does not establish path identity
when different compatible paths produce it.

These exact-set statements apply to a declared exact model. Uncertain times,
measurement noise, missing coverage, and conflicting records require an explicit
compatibility rule. A finite set selected for convenience must not be called an
exhaustive set of physically possible paths. The path application in this section
is a specification derived from the existing sufficiency rule; it is not an
additional executed transition-path experiment in the 36-test suite.

### 8.3 What evidence must preserve

For an application of this note, the supporting record should identify:

| Obligation | Required distinction |
|---|---|
| Relation participants and roles | Which components, stages, inputs, or boundaries jointly support the claim? |
| Joint identity and compatibility | Why do these observations belong to the same admissible configuration, process, trial cohort, or compatible context? |
| Acquisition or reconstruction rule | How is the relation obtained without substituting the target answer for missing evidence? |
| Timing and uncertainty where material | Which intervals, source-clock relations, or ordering constraints affect compatibility? |
| Target-relative sufficiency | Can remaining compatible configurations or paths change the declared result? |

These are proposed documentation obligations, not newly activated schema fields,
gates, or policy conditions. A shared identifier or digest can bind a record's
identity; it does not by itself establish the validity or completeness of the
relation represented by that record.

The contract must accept different faithful encodings. Joint records, verified
joins across shared identifiers, a relation node in a binary graph, or a validated
direct measurement of the target can all be sufficient when the relevant
structure and comparison response are preserved. The parity witness does not
mandate hypergraphs, full-state tomography, a fixed sensor count, or preservation
of every unrelated property.

### 8.4 Canonical placement and status compatibility

| Existing Transition Meter location | Contribution of this supporting note |
|---|---|
| Sections 4–5: endpoint insufficiency and transition identity | Adds an executable case of insufficiency after local and pairwise evidence has been acquired. |
| Sections 14–15: transition identity and evidence structure | Makes the shared relation binding and its reconstruction rule an explicit inspection target. |
| Section 18: separate status axes | Keeps identification, observation, binding, reproduction, causality, and authority distinct. |
| Section 19: evidence coverage | Requires coverage summaries to refer to the claim-critical joint relation, not merely component or pair counts. |
| Sections 20.3, 20.6, 20.7: relation, evidence, alternative-path layers | Supplies a finite before/activation/ablation witness with a preserved backup route. |

The local evaluation values `identified`, `unresolved`, and `incompatible` describe
the target assessment. They must not replace the canonical multiaxial transition
status. Missing access in this diagnostic machine produces a defined unresolved
report; it does not assert an undefined physical transition or a zero effect.

The repository publication comprises this supporting document, its documentation
index entry, and the companion evaluator, regression module, and reference result
under `examples/relation_preserving_discrimination_v0/`. The canonical document's
definitions, status axes, and active authority behavior are unchanged. The companion
is a manually invoked synthetic example, not a new runtime subsystem or CI gate.

### 8.5 Readiness boundary

The material is ready to preserve as a bounded technical document: it includes a
stated claim, a finite counterexample, a general finite-family argument, executable
controls, and explicit transfer limits. The remaining empirical task is to bind a
real transition claim to its domain evidence and demonstrate the claimed
path-relevant discrimination. That task is distinct from publishing this note
and is not a prerequisite for documenting the finite result honestly.

The contribution can be stated without overstating it:

> The Transition Meter must not infer that an evidence set is sufficient merely
> because its local components and pairwise summaries are covered. Sufficiency
> depends on preservation of the joint relation needed by the declared transition
> claim. If compatible alternatives can still change that claim, it stays
> unresolved.

## Reproduction

The companion is versioned in this repository; no local-only archive or external
download is required. Use all files from the same checkout revision:

| File | Role |
|---|---|
| [relation_closure_probe.py](../examples/relation_preserving_discrimination_v0/relation_closure_probe.py) | Fixed evaluator, finite fixtures, and result generator. |
| [test_relation_closure_probe.py](../examples/relation_preserving_discrimination_v0/test_relation_closure_probe.py) | The 36 original synthetic regression tests. |
| [results.json](../examples/relation_preserving_discrimination_v0/results.json) | Preserved deterministic reference result. |

From the repository root, with Python 3.10 or later:

```sh
cd examples/relation_preserving_discrimination_v0
python -m unittest -v test_relation_closure_probe
python relation_closure_probe.py --output results.reproduced.json
python -c "from pathlib import Path; import hashlib; actual=hashlib.sha256(Path('results.reproduced.json').read_bytes()).hexdigest(); expected='cfd0de8d466a53cd3fe4ae748fa46dfad7b3c398ba086106fff453c75c96ccf3'; print(actual); raise SystemExit(0 if actual == expected else 1)"
```

The final command returns a nonzero exit status on a digest mismatch. It hashes
the newly generated bytes, not a result copied from the checked-in reference.
The generator explicitly writes UTF-8 with LF line endings, independently of the
host newline convention. The reference digest also describes UTF-8/LF bytes;
a checkout that translates text files to CRLF can change the on-disk reference
file bytes, but not the expected generated digest.

The evaluator and regression logic are preserved from the original local package.
The only source adjustment for publication makes result-byte serialization
explicit; it does not change the evaluator, fixtures, target, or result content.

No third-party packages, network access, account credentials, or local archive
are needed after checkout. The original execution and the publication recheck
used Python 3.13.5. The recheck passed the same 36 tests and regenerated the same
15,182-byte result. These are local executions, not a repository CI run or a
tested platform matrix. Compatibility with other Python versions is based on the
language features used, not a tested version matrix.

Reference and reproduced `results.json` SHA-256 (UTF-8/LF):

```text
cfd0de8d466a53cd3fe4ae748fa46dfad7b3c398ba086106fff453c75c96ccf3
```

The digest binds the expected result bytes. It does not replace source review,
execution of the commands, proof of the formal claims, or physical validation.

## Sources and boundaries

The PULSE sources were read at the fixed revision below, not assumed to be the
current repository head.

1. [Workshop theorem, especially sections 2.3–5.3](https://github.com/HKati/pulse-release-gates-0.1/blob/d2b184ccb1b1cc433e9f64d7dc0df9b4abff25a4/docs/PULSEMECH_WORKSHOP_DECIMAL_ACCUMULATION_AND_DIMENSION_OPENING_THEOREM_EN_v0.md).
   Reviewed blob: `12f6e736737fa5605496dd8f6afa4ed5fe92c984`.
2. [Relation / Half-Paradox formulation, especially sections 4–6](https://github.com/HKati/pulse-release-gates-0.1/blob/d2b184ccb1b1cc433e9f64d7dc0df9b4abff25a4/docs/PULSEMECH_RELATION_HALF_PARADOX_MATHEMATICAL_PHYSICAL_QUANTUM_FORMULATION_v0.md).
   Reviewed blob: `63933dbf40698c07e779fab40f4a85ba75dd45c1`.
3. [Canonical Transition Meter, especially sections 3–5, 14–20](https://github.com/HKati/pulse-release-gates-0.1/blob/d2b184ccb1b1cc433e9f64d7dc0df9b4abff25a4/PULSEMECH_TRANSITION_METER.md).
   Reviewed blob: `c0301047ebdcb94e40418271fe0c8522cb9baaae`. The core measurement-gap,
   claim-dependent completeness, multiaxial status, coverage, and layer sections
   were reread for this document's incorporation section.
4. [MIT OpenCourseWare, Independence Versus Pairwise Independence](https://ocw.mit.edu/courses/res-6-012-introduction-to-probability-spring-2018/resources/independence-versus-pairwise-independence/).
   Background only: the distinction is not presented as newly discovered
   probability theory. The finite witness, enumeration, and Workshop binding
   comparison in this note are derived and executable without adopting a quantum
   interpretation or relying on an external physical model.

## Műhelyösszefoglaló

```text
Az összes rész és az összes páros összesítés egyezése még nem garantálja
az együttműködés kihatásának egyezését. A véges próbában a háromtagú,
közösen kötött reláció hordozza a megkülönböztető adatot.

A PULSE-mérő bővítése ezt a relációt teszi hozzáférhetővé ugyanannak az
értékelőnek. A kötés kikapcsolásakor az eredmény feloldatlanná válik,
nem nullává; egy megmaradó alternatív kötés megőrzi a különbséget.

A Transition Meterhez a bizonyítékok elégségességi próbáját adja:
a helyi és páros lefedés nem helyettesíti az állítás szempontjából szükséges
közös reláció igazolását. A kihatás azonosítása nem azonos az átmeneti út
azonosításával. A teljes fizikai út rekonstrukciója itt nincs igazolva.

36 helyi teszt sikeres; a dokumentálási újraellenőrzés is 36/36.
Ez mérési szerkezetre adott szintetikus tanú,
nem kvantumkísérlet és nem a teljes fizikai működés igazolása.
```
