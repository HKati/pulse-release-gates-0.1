# PULSEmech — Synthetic Data, Information Contribution, and Measurement Saturation

## Status

```text
document_role:
technical_measurement_note

status:
non_normative

empirical_claim_without_bound_measurement:
not_admitted

authority_effect:
none

implementation_effect:
none
```

## 1. Scope

This document defines a bounded procedure for measuring whether an admitted
record or an ordered record window changes an exact claim state.

The procedure applies to records with observed, synthetic, mixed, or unresolved
origin.

The procedure separates:

```text
data volume

record origin

source lineage

claim-state contribution

state-measurement saturation

relation-measurement gaps

transition-measurement gaps
```

Within this document, measured information contribution means a non-empty
verified sequential claim-state delta. It does not mean positive utility,
quality, confidence, or authority.

The document does not assign information contribution from record presence,
record count, record size, origin class, generator count, or surface variation.

The document does not assert that synthetic data is valid, invalid, useful, or
harmful as a class.

The document does not define an entropy result.

The document does not create an implementation or authority mechanism.

---

## 2. Exact measurement identity

Every measurement is bound to:

```text
one exact claim identity

one exact subject boundary

one exact time boundary

one exact evidence-admission rule

one exact relation vocabulary

one exact transition vocabulary

one exact verifier set

one exact canonical-state serializer

one exact ordered record inventory
```

A measurement made under a different identity is a different measurement.

A missing required identity produces no positive conclusion.

Digest values protect stored-byte integrity.

Digest equality does not replace exact-byte comparison.

---

## 3. Record identity

Every admitted record preserves:

```text
record identity

exact content bytes or exact external-content reference

content size

digest algorithm

content digest

source locator

acquisition event identity

producer or observer identity

origin classification

acquisition-status classification
```

A record with unrecoverable content identity cannot enter the measured record
window.

Origin classification and acquisition status are separate.

A synthetically generated artifact can be directly recorded.

Direct recording does not convert synthetic content into an external
observation of the claim represented by that content.

---

## 4. Synthetic provenance

A synthetic record preserves the relation:

```text
source-input inventory
+
generator identity
+
generator revision
+
generation configuration
+
generation event
→
synthetic output identity
```

The source-input inventory can be explicitly empty.

An explicitly empty source-input inventory is different from a missing
source-input inventory.

Synthetic provenance is complete when every required source-input relation is
bound.

Synthetic provenance is partial when at least one required source-input relation
is bound and at least one required source-input relation is missing.

Synthetic provenance is not reconstructable when no required source-input
relation can be recovered.

Synthetic origin does not establish claim-state contribution.

---

## 5. Claim identity

The claim identity contains:

```text
claim identifier

claim type

subject boundary

time boundary

required relation classes

required transition classes

evidence-admission rule

verifier set

measurement-contract identity
```

A record has no measured contribution outside a bound claim identity.

Measurements under different claim identities are not directly comparable
without an explicit compatibility mapping.

---

## 6. Claim-state model

For claim `C` under evidence state `K`, define:

```text
Q_C(K)
=
<
  R_C(K),
  T_C(K),
  U_C(K),
  X_C(K),
  B_C(K),
  L_C(K)
>
```

where:

```text
R_C(K)
=
canonically ordered verified relation identities

T_C(K)
=
canonically ordered verified transition identities

U_C(K)
=
canonically ordered unresolved required relation and transition identities

X_C(K)
=
canonically ordered conflict identities

B_C(K)
=
binding-coverage record

L_C(K)
=
source-lineage state
```

Every member has an exact identity.

Every collection uses the ordering defined by the measurement contract.

The complete state has canonical bytes.

The state digest is calculated from those bytes.

---

## 7. Claim-state equality

Two claim states are equal only when:

```text
their claim identities are equal

their measurement-contract identities are equal

their verifier-set identities are equal

their canonical-serializer identities are equal

their canonical state bytes are equal
```

Digest equality is recorded as an integrity check.

Digest equality is not treated as proof of state equality.

---

## 8. Verified and unresolved objects

A relation enters `R_C(K)` only after the bound verifier confirms its required
identity, participants, evidence, time, and boundary bindings.

A transition enters `T_C(K)` only after the bound verifier confirms its source
state, target state, changed relation, ordered elements, path effect, evidence,
time, and boundary bindings.

A required object with missing bindings enters `U_C(K)` with:

```text
object identity

missing binding class

available evidence identities

last verifier result

resolution requirement
```

A conflict enters `X_C(K)` when admitted evidence supports incompatible
claim-state assignments under the same claim and measurement contract.

No unresolved or conflicting object is replaced by an inferred positive object.

---

## 9. Binding coverage

`B_C(K)` preserves exact required and satisfied identity inventories for:

```text
relations

transitions

transition elements

time bindings

boundary bindings

source-lineage bindings
```

Counts are derived from the identity inventories.

A count without its supporting inventory is incomplete.

---

## 10. Ordered record window

An evaluated window is:

```text
W
=
[r1, r2, ..., rn]
```

The window identity preserves:

```text
claim identity

measurement-contract identity

verifier-set identity

subject boundary

time boundary

record order

record identities
```

Changing record order creates a different window.

A missing record creates an incomplete window.

---

## 11. Sequential claim states

For `W`, define evidence states:

```text
K0
=
evidence state before r1

K1
=
evidence state after r1

K2
=
evidence state after r2

...

Kn
=
evidence state after rn
```

Define:

```text
Qi
=
Q_C(Ki)
```

Every `Qi` is reconstructed under the same claim, measurement contract,
verifier set, subject boundary, and canonical serializer.

A change in any of those identities makes the window non-comparable.

---

## 12. Sequential delta

For each record `ri`, define:

```text
Δi
=
structured difference between Qi and Q(i-1)
```

The delta preserves exact identity inventories for:

```text
added verified relations

removed verified relations

added verified transitions

removed verified transitions

added unresolved objects

resolved unresolved objects

added conflicts

resolved conflicts

binding-coverage changes

source-lineage-state changes
```

`Δi` is empty only when:

```text
every delta inventory is empty
+
canonical bytes of Qi equal canonical bytes of Q(i-1)
```

A later record cannot cancel an earlier non-empty delta for saturation
measurement.

Endpoint equality between `Q0` and `Qn` is insufficient.

---

## 13. Measured record contribution

A record has no measured claim-state contribution when its sequential delta is
empty.

A record has measured claim-state contribution when its sequential delta is
non-empty.

The result preserves the exact changed identities.

The result does not assign a scalar utility, confidence, or quality score.

The result is claim-relative.

---

## 14. Data-volume relation

For every evidence state `Ki`, define:

```text
Vi
=
<admitted record count in Ki, total admitted content bytes in Ki>
```

The measurement also preserves:

```text
origin-class counts

producer counts

empty sequential-delta count

non-empty sequential-delta count
```

Data-volume growth across `W` is established only when:

```text
Vn is component-wise greater than or equal to V0
+
at least one component of Vn is greater than the corresponding component of V0
```

Data-volume growth with no measured claim-state contribution is established only
when:

```text
data-volume growth across W is established
+
every sequential delta is empty
```

Data-volume growth with measured claim-state contribution is established only
when:

```text
data-volume growth across W is established
+
at least one sequential delta is non-empty
```

Neither result is transferred to another claim without a new measurement.

---

## 15. Source-lineage graph

The source-lineage graph contains exact nodes for:

```text
records

external observations

generator executions

transformations

comparisons

verification events
```

Each node and edge has an exact identity.

Lineage completeness and cycle status are separate axes.

### 15.1 Completeness

```text
complete

partial

not reconstructable
```

### 15.2 Cycle status

```text
cycle absent

cycle present

cycle status unresolved
```

A root-source set is emitted only when lineage is complete and the cycle is
absent.

---

## 16. External root-source set

For a record `r`, define:

```text
Root(r)
=
canonically ordered set of reachable external-observation root identities
```

A complete acyclic lineage can produce:

```text
a non-empty root set

an empty root set
```

An empty root set means that no external-observation root is reachable in the
complete bound lineage graph.

An empty root set does not establish shared observed lineage.

---

## 17. Root-source comparison

For two complete acyclic lineages, a shared external root is established only
when:

```text
Root(r1) ∩ Root(r2)
≠
∅
```

Disjoint external roots are established only when:

```text
Root(r1)
≠
∅

Root(r2)
≠
∅

Root(r1) ∩ Root(r2)
=
∅
```

If both sets are empty, the result is:

```text
no external-observation root for either record
```

If one set is empty and one set is non-empty, the result preserves the different
root classes.

No root-source comparison result is emitted when either lineage is partial,
not reconstructable, cyclic, or has unresolved cycle status.

---

## 18. Evidence-independence boundary

Shared or disjoint external roots do not establish:

```text
statistical independence

causal independence

instrument independence

institutional independence
```

Those properties require separate domain-specific measurements.

Different wording does not establish an independent source.

Different generator runs do not establish independent external observations.

Different sampling seeds do not establish independent external observations.

Different generator implementations do not establish independent external
observations.

Synthetic multiplicity is not counted as observational independence without a
separate independence measurement.

---

## 19. Synthetic record and observed comparison

A synthetic record can participate in an observed comparison.

The comparison preserves:

```text
synthetic record identity

external-observation record identity

comparison procedure identity

comparison verifier identity

comparison event identity

comparison result
```

The synthetic record retains synthetic origin.

Any claim-state contribution is derived from the verified comparison delta.

Synthetic origin alone produces no contribution result.

---

## 20. Entropy boundary

This document produces no entropy result.

The terms:

```text
noise

redundancy

conflict

uncertainty

disorder
```

are not treated as entropy measurements.

An entropy result requires a separate measurement contract with a bound
probability space, estimator, numerical representation, arithmetic procedure,
unit, and replay rule.

No entropy value is inferred in this document.

---

## 21. State-record window

A state-record window contains only records classified under the same bound
measurement-object class:

```text
state
```

State-record classification does not imply redundancy.

A state record can produce a non-empty sequential delta.

Every record admission and every `Qi` reconstruction must complete without an
identity, verifier, or serializer failure.

---

## 22. State-measurement saturation

A state-record window `W` is saturated for claim `C` under measurement contract
`M` only when all conditions hold:

```text
1. W is complete and comparable.

2. Every record identity is bound.

3. Every record admission completes under M.

4. Every Q0 ... Qn is reproducible.

5. Every Δ1 ... Δn is empty.

6. At least one required relation or transition object remains in the unresolved
   component of Qn.
```

Condition 5 rejects intermediate changes that later cancel.

Endpoint equality alone is insufficient.

The result is bound to the exact claim, contract, verifier set, ordered window,
subject boundary, and time boundary.

---

## 23. Saturation non-claims

State-measurement saturation under `W` establishes only:

```text
every admitted state record in the exact window produced no measured
claim-state change
+
at least one required relation or transition object remained unresolved
```

It does not establish:

```text
global information exhaustion

future information impossibility

model incapacity

source exhaustion

transition-space saturation

causal closure
```

A different claim, contract, verifier set, record order, subject boundary, or
time boundary requires a new measurement.

---

## 24. Relation-measurement gap

A relation-measurement gap is established when:

```text
state-measurement saturation is established
+
at least one unresolved required relation identity remains
```

The result preserves the complete unresolved relation inventory.

The result does not assert that a future instrument will resolve the gap.

---

## 25. Transition-measurement gap

A transition-measurement gap is established when:

```text
state-measurement saturation is established
+
at least one unresolved required transition or transition-element identity
remains
```

The result preserves the complete unresolved transition inventory.

The result does not assert that a future instrument will resolve the gap.

---

## 26. Required next measurement object

A measured relation or transition gap identifies the unresolved measurement
object.

Required bindings are derived from the unresolved inventory.

Possible required bindings include:

```text
relation-change observation

ordered transition elements

event-time binding

observation-time binding

boundary-crossing evidence

path-effect evidence

alternative-path evidence

transition verifier
```

This is a measurement requirement.

It is not an implementation or authority decision.

---

## 27. PULSEmech relation

The measurement objects map to PULSEmech as follows:

| Measurement object | PULSEmech layer |
|---|---|
| exact record identity | evidence identity |
| origin identity | evidence provenance |
| acquisition status | observation or reconstruction state |
| verified relation inventory | relation layer |
| verified transition inventory | transition and path layers |
| unresolved inventory | unresolved transition state |
| binding coverage | evidence coverage |
| lineage graph | evidence lineage |
| sequential claim-state delta | measured claim-state transition |
| state-measurement saturation | measurement-surface result |
| relation-measurement gap | unresolved relation result |
| transition-measurement gap | unresolved transition result |
| authority effect | separate authority layer |

This document does not change PULSEmech authority.

---

## 28. Proof package

A complete measurement package preserves:

```text
claim identity

measurement-contract identity

canonical-serializer identity

verifier-set identity

ordered record inventory

record identities

origin identities

acquisition-status records

lineage graph

Q0 ... Qn canonical bytes

Q0 ... Qn integrity digests

Δ1 ... Δn exact inventories

saturation result

relation-gap result

transition-gap result

errors

replay identity
```

Canonical bytes determine claim-state equality.

Digests protect stored-byte integrity.

---

## 29. Replay

Replay uses the same:

```text
inputs

claim

measurement contract

verifier set

canonical serializer

ordered record window
```

Replay passes only when:

```text
every canonical claim-state byte sequence matches

every sequential delta inventory matches

the final result bytes match
```

A replay mismatch invalidates the reproduced result.

---

## 30. Fail-closed boundary

No positive result is emitted when a required component is:

```text
missing

identity-unbound

non-comparable

non-reproducible

lineage-incomplete where complete lineage is required

serializer-unbound

verifier-unbound
```

The missing requirement remains explicit.

No missing requirement is replaced by inference.

---

## 31. Prohibited conclusions

The following conclusions require separate measurements and are not produced by
this document:

```text
more records
→
more information

more synthetic records
→
more independent evidence

different surface form
→
different source

different generator run
→
independent external observation

synthetic origin
→
invalid record

observed origin
→
valid record

endpoint equality
→
empty sequential deltas

digest equality
→
canonical-byte equality

state-measurement saturation
→
information exhaustion

relation statement
→
verified relation

transition statement
→
measured transition

entropy terminology
→
entropy measurement

measurement result
→
release authority
```

---

## 32. Implementation boundary

This document defines measurement semantics only.

It creates no:

```text
schema

producer

validator

adapter

test registration

workflow

policy requirement

candidate gate

release decision

release authority
```

Implementation requires a separate reviewed sequence:

```text
schema
→
examples
→
validator
→
producer
→
regression
→
observed replay
→
separate promotion decision
```

---

## 33. Final position

Measured record contribution is determined by the exact sequential difference
between reproducible claim states.

Measured data-volume growth without claim-state contribution requires every
sequential delta in the exact ordered window to be empty.

Measured state-measurement saturation requires:

```text
a complete comparable state-record window

reproducible sequential claim states

empty sequential deltas for every admitted record

a non-empty unresolved relation or transition inventory
```

A relation-measurement gap is determined by the remaining unresolved relation
inventory.

A transition-measurement gap is determined by the remaining unresolved
transition inventory.

Every result is bound to exact inputs, exact measurement semantics, exact
verifiers, canonical bytes, and deterministic replay.
