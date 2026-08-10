# PULSEmech — Synthetic Data Information Contribution and Measurement Saturation

## Status

```text
document_role:
mechanical_measurement_contract_and_proof_obligation

status:
non_authoritative_measurement_specification

scope:
synthetic_data_provenance
claim_relative_information_contribution
source_lineage
state_measurement_saturation
relation_measurement_gap
transition_measurement_gap

empirical_claim_without_bound_measurement:
forbidden

authority_effect:
none

implementation_effect:
none

gate_effect:
none
```

## 1. Scope

This document defines measurable objects, deterministic comparison rules, proof
obligations, and bounded result states for:

```text
synthetic-data provenance

claim-relative information contribution

source-lineage reconstruction

record multiplicity

state-measurement saturation

relation-measurement gaps

transition-measurement gaps
```

The document does not assert that synthetic data is harmful.

The document does not assert that synthetic data is informative.

The document does not assign information value from record origin or record
volume.

Every result depends on:

```text
exact input identities

exact claim identity

exact measurement contract

exact verifier identity

deterministic before-state reconstruction

deterministic after-state reconstruction

deterministic delta calculation

replay
```

A missing binding produces an unresolved result.

No missing binding is replaced by inference.

---

## 2. Measurement rule

Within this contract, a record is information-bearing for claim `C` only when
its admission changes the verified claim state under an exact measurement
contract.

The measured relation is:

```text
record r
+
claim C
+
before evidence state K
+
measurement contract M
→
after evidence state K'
→
structured claim-state delta
```

The existence of `r` does not establish information contribution.

The origin class of `r` does not establish information contribution.

The byte size of `r` does not establish information contribution.

The number of records related to `r` does not establish information
contribution.

---

## 3. Exact record identity

Every admitted record requires:

```text
record_id

record_type

exact bytes or exact external-byte reference

byte size

content digest algorithm

content digest

source locator

acquisition event identity

acquisition time binding

producer or observer identity

declared role
```

A record without an exact content identity is:

```text
RECORD_IDENTITY_UNBOUND
```

An unbound record cannot contribute to a verified claim-state delta.

---

## 4. Origin and acquisition are separate axes

Record origin and record acquisition are separate mechanical properties.

### 4.1 Content-origin axis

```text
external_observation

synthetic_generation

mixed

unresolved
```

### 4.2 Acquisition-status axis

```text
directly_recorded

reconstructed

reported

unresolved
```

### 4.3 Declared-role axis

```text
evidence

fixture

example

simulation

counterexample

diagnostic
```

One record can have:

```text
content_origin:
synthetic_generation

acquisition_status:
directly_recorded

declared_role:
fixture
```

This means:

```text
the artifact was directly recorded
+
the artifact content was synthetically generated
+
the artifact is used as a fixture
```

The axes do not overwrite one another.

---

## 5. Observed external record

An external-observation record requires:

```text
target subject identity

observation boundary

instrument or observer identity

measurement procedure identity

event-time binding

observation-time binding

result identity

source provenance
```

The status:

```text
content_origin:
external_observation
```

does not establish:

```text
valid measurement

complete coverage

current binding

causal sufficiency
```

Those properties require separate verification.

---

## 6. Synthetic record

A synthetic record requires:

```text
generator identity

generator version or exact revision

generator execution identity

source-input identities

generation configuration identity

generation event time

output identity

declared synthetic lineage
```

The minimum provenance relation is:

```text
source inputs
+
generator
+
generation configuration
+
generation event
→
synthetic output
```

A synthetic record with incomplete source-input identity is:

```text
SYNTHETIC_LINEAGE_PARTIAL
```

A synthetic record with no reconstructable lineage is:

```text
SYNTHETIC_LINEAGE_UNRESOLVED
```

---

## 7. Claim identity

Every information-contribution measurement is relative to one exact claim.

A claim identity requires:

```text
claim_id

claim_type

subject boundary

time boundary

relation vocabulary

transition vocabulary

evidence-admission policy

verifier set

measurement-contract version
```

Two measurements with different claim identities are not directly comparable.

Two measurements with different relation vocabularies are not directly
comparable.

Two measurements with different verifier sets are not directly comparable
unless an explicit compatibility mapping exists.

---

## 8. Claim-state vector

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
R_C(K):
ordered set of verified relation identities

T_C(K):
ordered set of verified transition identities

U_C(K):
ordered set of unresolved relation or transition-edge identities

X_C(K):
ordered set of conflict identities

B_C(K):
binding-coverage map

L_C(K):
source-lineage classification state
```

Every set is canonically ordered.

Every member has an exact identity.

The complete vector is canonically serialized.

The exact vector bytes have a digest.

---

## 9. Verified relation set

A relation enters `R_C(K)` only when the exact measurement contract verifies:

```text
relation identity

participating entity identities

relation type

source evidence

time binding where required

boundary binding where required

verifier identity

verification result
```

A plausible relation does not enter the verified relation set.

A narrated relation does not enter the verified relation set.

A synthetically generated relation statement does not enter the verified
relation set without the required evidence and verifier result.

---

## 10. Verified transition set

A transition enters `T_C(K)` only when the exact measurement contract verifies:

```text
source-state identity

target-state identity

changed relation

ordered transition elements

path effect

element-level evidence

element-level time binding where required

boundary crossings where required

transition verifier identity

verification result
```

Endpoint equality does not establish transition identity.

Endpoint difference does not establish transition identity.

A transition statement without a verified path remains outside `T_C(K)`.

---

## 11. Unresolved-edge set

An edge enters `U_C(K)` when a required relation or transition element lacks one
or more required bindings.

An unresolved-edge record requires:

```text
edge_id

required relation or transition position

missing binding class

available evidence references

last verifier result

resolution requirement
```

A missing edge remains explicit.

A missing edge is not replaced by a narrative connector.

---

## 12. Conflict set

A conflict enters `X_C(K)` when admitted evidence supports incompatible
claim-state assignments under the same claim and measurement contract.

A conflict identity requires:

```text
conflict_id

conflicting record identities

conflicting relation or transition identities

shared claim identity

verifier result

resolution status
```

A conflict is a measured output.

A conflict is not converted into an aggregate confidence value.

---

## 13. Binding-coverage map

`B_C(K)` records exact coverage for required claim components.

Possible fields include:

```text
required_relations

verified_relations

required_transitions

verified_transitions

required_edges

resolved_edges

unresolved_edges

required_time_bindings

verified_time_bindings

required_boundaries

verified_boundaries

required_source_lineages

resolved_source_lineages
```

Coverage is recorded as counts and exact identity inventories.

Coverage is not compressed into one confidence score.

---

## 14. Source-lineage graph

The source-lineage graph contains:

```text
record nodes

external-observation nodes

generator-execution nodes

transformation nodes

comparison nodes

verification nodes
```

Allowed edge classes include:

```text
observed_from

generated_by

derived_from

transformed_from

compared_with

verified_by
```

Every node and edge has an exact identity.

The graph can be incomplete.

An incomplete graph is marked:

```text
LINEAGE_PARTIAL
```

A graph with an unresolved required parent is marked:

```text
LINEAGE_UNRESOLVED
```

A graph cycle is recorded:

```text
LINEAGE_CYCLE_PRESENT
```

No depth result is produced across an unresolved cycle.

---

## 15. Root-source set

For record `r`, define:

```text
Root(r)
=
ordered set of reachable external-observation root identities
```

The result is valid only when every required parent path is resolved.

Possible states:

```text
ROOT_SET_COMPLETE

ROOT_SET_PARTIAL

ROOT_SET_UNRESOLVED
```

Two records with the same complete root-source set share the same observed root
lineage under the preserved graph.

This does not establish statistical independence.

This does not establish causal independence.

This does not establish instrument independence.

---

## 16. Source-lineage separation

For records `r1` and `r2`, define:

```text
lineage_separation(r1, r2)
```

with possible results:

```text
SHARED_ROOT_SOURCE

DISJOINT_ROOT_SOURCES_UNDER_BOUND_GRAPH

LINEAGE_COMPARISON_UNRESOLVED
```

The result:

```text
DISJOINT_ROOT_SOURCES_UNDER_BOUND_GRAPH
```

means only that the preserved lineage graph contains disjoint external root
identities.

It does not mean:

```text
statistically independent

causally independent

independent instruments

independent institutions
```

Those claims require domain-specific measurement.

---

## 17. Synthetic-generation depth

For an acyclic, complete lineage path, define:

```text
minimum_synthetic_depth(r)

maximum_synthetic_depth(r)
```

as the minimum and maximum number of `generated_by` transitions between `r` and
a reachable external-observation root.

Required outputs:

```text
minimum depth

maximum depth

root identities

path identities

depth status
```

Possible depth states:

```text
DEPTH_MEASURED

DEPTH_PARTIAL

DEPTH_UNRESOLVED

DEPTH_BLOCKED_BY_CYCLE
```

Synthetic-generation depth does not determine information value.

Synthetic-generation depth does not determine validity.

---

## 18. Before-state and after-state

For admitted record `r`:

```text
before_state
=
Q_C(K)
```

```text
after_state
=
Q_C(K ∪ {r})
```

Both states require:

```text
exact input inventories

exact verifier identities

exact measurement-contract identity

canonical state bytes

state digest
```

The measurement is invalid when the before-state and after-state use different
claim definitions or verifier semantics without an explicit compatibility
mapping.

---

## 19. Structured information contribution

Define:

```text
Δ_C(r | K)
=
Q_C(K ∪ {r})
-
Q_C(K)
```

The delta is not a scalar.

The delta contains:

```text
added_verified_relations

removed_verified_relations

added_verified_transitions

removed_verified_transitions

resolved_edges

new_unresolved_edges

added_conflicts

resolved_conflicts

binding_coverage_delta

source_lineage_state_delta
```

Each member is an exact identity inventory.

---

## 20. Information-contribution outputs

Possible outputs include:

```text
RELATION_ADDED

RELATION_REMOVED

TRANSITION_ADDED

TRANSITION_REMOVED

EDGE_RESOLVED

UNRESOLVED_EDGE_ADDED

CONFLICT_ADDED

CONFLICT_RESOLVED

BINDING_COVERAGE_INCREASED

BINDING_COVERAGE_DECREASED

LINEAGE_STATE_CHANGED

NO_CLAIM_STATE_CHANGE
```

Multiple outputs can apply to one record.

No weighting is implied.

No aggregate utility is implied.

---

## 21. No-claim-state-change proof

A record has:

```text
NO_CLAIM_STATE_CHANGE
```

when:

```text
before_state canonical bytes
=
after_state canonical bytes
```

equivalently:

```text
before_state digest
=
after_state digest
```

under the same claim and measurement contract.

This result proves:

```text
the admitted record did not change the measured claim state
```

It does not prove:

```text
the record is useless for every claim

the record is globally redundant

the record has no operational role
```

---

## 22. Synthetic-record multiplicity measurement

For a batch `S` of synthetic records, record:

```text
synthetic_record_count

exact record identities

generator-execution identities

complete root-source sets

partial root-source sets

unresolved root-source sets

before claim-state vector

after claim-state vector

structured delta
```

Possible outputs:

```text
SYNTHETIC_RECORD_GROWTH_WITH_CLAIM_STATE_CHANGE

SYNTHETIC_RECORD_GROWTH_WITH_NO_CLAIM_STATE_CHANGE

SYNTHETIC_MULTIPLICITY_LINEAGE_PARTIAL

SYNTHETIC_MULTIPLICITY_LINEAGE_UNRESOLVED
```

The result is derived from exact counts, exact lineage state, and exact
claim-state comparison.

---

## 23. Independent-evidence boundary

A synthetic record does not count as an independent external observation merely
because:

```text
its surface form differs

its generator run differs

its sampling seed differs

its generator implementation differs
```

Independent external-observation status requires a domain-specific proof
binding:

```text
separate observed subject interaction

separate observation event

separate instrument or observer boundary

separate source lineage

domain independence criteria

verifier result
```

Without that proof, the result is:

```text
INDEPENDENT_EXTERNAL_OBSERVATION_NOT_ESTABLISHED
```

---

## 24. Synthetic comparison with external observation

A synthetic record can participate in an information-bearing comparison.

The measured relation is:

```text
synthetic record
+
external-observation record
+
comparison procedure
+
comparison verifier
→
comparison result
```

The synthetic record retains:

```text
content_origin:
synthetic_generation
```

The comparison result can have:

```text
acquisition_status:
directly_recorded
```

The claim-state contribution is assigned from the verified comparison result,
not from synthetic origin alone.

---

## 25. Entropy measurement boundary

The term `entropy` is prohibited unless the measurement record provides:

```text
mutually exclusive class set

normalized probability distribution

probability-estimation procedure

estimator identity

sample identity

calibration state where required

logarithm base

before distribution

after distribution
```

For a valid probability distribution:

```text
P_C
=
{p1, p2, ..., pn}
```

with:

```text
pi ≥ 0

Σ pi = 1
```

Shannon entropy in bits is:

```text
H_C
=
- Σ pi log2(pi)
```

The measurement result requires exact numerical inputs and deterministic
calculation.

When these prerequisites are absent, the only valid output is:

```text
RELATION_ENTROPY_NOT_MEASURED
```

The word `entropy` is not used as a synonym for:

```text
disorder

noise

redundancy

conflict

uncertainty
```

Those objects are measured separately.

---

## 26. State-record class

A state record reports an identified system state without independently binding
the complete transition path from a preceding state.

A record can be classified as:

```text
measurement_object_class:
state
```

only under an exact state-record contract.

The classification does not imply low information contribution.

A state record can add a new verified relation, resolve an edge, or increase
coverage.

---

## 27. Comparable saturation window

A saturation window `W` requires:

```text
one exact claim identity

one exact measurement-contract version

one exact verifier set

one exact subject boundary

one exact policy boundary where applicable

one exact measurement-object class

predeclared record-count window or time window

complete admitted-record inventory
```

A window with changed measurement semantics is:

```text
SATURATION_WINDOW_NOT_COMPARABLE
```

A window with missing records is:

```text
SATURATION_WINDOW_INCOMPLETE
```

---

## 28. State-measurement saturation

For a comparable window:

```text
W
=
{r1, r2, ..., rn}
```

where every `ri` has:

```text
measurement_object_class:
state
```

state-measurement saturation is established when all conditions hold:

```text
1. every record identity is bound

2. every record is admitted under the same measurement contract

3. the claim-state vector before the window equals the claim-state vector after
   the window

4. no verified relation was added

5. no verified transition was added

6. no unresolved edge was resolved

7. no binding coverage increased

8. at least one required relation or transition edge remains unresolved
```

The valid output is:

```text
STATE_MEASUREMENT_SATURATED_UNDER_BOUND_WINDOW
```

The output is bound to the exact window.

---

## 29. Saturation non-claims

The result:

```text
STATE_MEASUREMENT_SATURATED_UNDER_BOUND_WINDOW
```

does not establish:

```text
global information exhaustion

future information impossibility

model incapacity

data-source exhaustion

transition-space saturation

causal closure
```

It establishes only:

```text
the exact admitted state-record window produced no measured claim-state change
while required unresolved relations or transition edges remained
```

---

## 30. Relation-measurement gap

A relation-measurement gap is established when:

```text
state-measurement saturation is established
+
one or more unresolved required relation identities remain
```

The output is:

```text
RELATION_MEASUREMENT_GAP_PRESENT
```

The output includes the exact unresolved relation inventory.

The output does not assert that a future measurement will resolve the gap.

---

## 31. Transition-measurement gap

A transition-measurement gap is established when:

```text
state-measurement saturation is established
+
one or more unresolved required transition-edge identities remain
```

The output is:

```text
TRANSITION_MEASUREMENT_GAP_PRESENT
```

The output includes the exact unresolved transition-edge inventory.

The output does not assert that a future transition instrument will resolve the
gap.

---

## 32. Transition-measurement requirement

When:

```text
TRANSITION_MEASUREMENT_GAP_PRESENT
```

the next required measurement object is:

```text
the unresolved transition edge or transition path
```

The required input classes are derived from the unresolved-edge records.

Possible required classes include:

```text
relation-change observation

element order

event-time binding

observation-time binding

boundary-crossing evidence

path-effect evidence

alternative-path evidence

transition verifier
```

This result is a measurement requirement.

It is not an implementation decision.

---

## 33. PULSEmech mapping

The measurement objects map to the PULSEmech Transition Meter as follows:

| Measurement object | PULSEmech position |
|---|---|
| exact record identity | evidence identity |
| content-origin axis | evidence provenance |
| acquisition-status axis | observation or reconstruction status |
| verified relation set | relation layer |
| verified transition set | transition and path layers |
| unresolved-edge set | unresolved transition state |
| binding-coverage map | evidence coverage |
| source-lineage graph | provenance and evidence lineage |
| state-measurement saturation | measurement-surface result |
| relation-measurement gap | unresolved relation output |
| transition-measurement gap | unresolved transition output |
| structured claim-state delta | transition-measurement result |
| authority effect | separate authority layer |

Synthetic origin does not replace observation status.

Observation status does not replace synthetic origin.

Authority remains separate.

---

## 34. PULSEmech current implementation boundary

This document does not claim that the current PULSEmech implementation produces:

```text
synthetic lineage graphs

synthetic-generation depth

claim-state vectors

synthetic multiplicity reports

state-measurement saturation results

relation-measurement gap results

transition-measurement gap results
```

The current document defines proof obligations only.

Any implementation requires a separate schema, producer, validator, regression,
observed replay, and promotion decision.

---

## 35. Required measurement-result record

A complete result record requires:

```text
record_type

schema_version

measurement_contract_identity

claim_identity

subject_binding

input_inventory

record_origin_axes

record_role

source_lineage_graph

before_claim_state

after_claim_state

structured_delta

entropy_measurement_state

saturation_window

saturation_result

relation_gap_result

transition_gap_result

verifier_identity

replay_identity

errors

authority_boundary
```

Every referenced artifact requires exact identity.

Every derived field requires a derivation rule identity.

---

## 36. Deterministic evaluation procedure

The evaluation procedure is:

```text
1. validate claim identity

2. validate measurement-contract identity

3. validate every record identity

4. classify content origin

5. classify acquisition status

6. classify declared role

7. reconstruct source-lineage graph

8. validate required lineage edges

9. calculate root-source sets

10. reconstruct before claim-state vector

11. admit the exact record or record batch

12. reconstruct after claim-state vector

13. calculate structured delta

14. evaluate entropy prerequisites

15. evaluate saturation-window comparability

16. evaluate state-measurement saturation

17. evaluate relation-measurement gap

18. evaluate transition-measurement gap

19. serialize canonical result

20. replay and compare exact result bytes
```

A replay mismatch produces:

```text
MEASUREMENT_REPLAY_MISMATCH
```

---

## 37. Fail-closed outputs

Missing required identity:

```text
IDENTITY_UNBOUND
```

Missing required source lineage:

```text
LINEAGE_UNRESOLVED
```

Changed claim contract inside comparison:

```text
CLAIM_COMPARISON_INVALID
```

Changed verifier semantics inside comparison:

```text
VERIFIER_COMPARISON_INVALID
```

Incomplete saturation window:

```text
SATURATION_WINDOW_INCOMPLETE
```

Non-comparable saturation window:

```text
SATURATION_WINDOW_NOT_COMPARABLE
```

Missing entropy prerequisites:

```text
RELATION_ENTROPY_NOT_MEASURED
```

Replay mismatch:

```text
MEASUREMENT_REPLAY_MISMATCH
```

No fail-closed output is replaced by a positive conclusion.

---

## 38. Prohibited inferences

The following inferences are prohibited:

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
independent observation

greater synthetic-generation depth
→
lower validity

synthetic origin
→
invalid record

observed origin
→
valid record

state-measurement saturation
→
information exhaustion

relation present
→
relation verified

transition stated
→
transition measured

entropy language
→
entropy measurement

PASS
→
complete transition evidence

ALLOW
→
self-explanatory authority
```

---

## 39. Measured example — synthetic multiplicity without claim-state change

Input state:

```text
claim:
C1

before verified relations:
[R1]

before verified transitions:
[]

before unresolved edges:
[U1]

observed root source:
O1
```

Synthetic batch:

```text
S1 ... S10

content origin:
synthetic_generation

root source set:
[O1]

declared role:
example
```

Measured after-state:

```text
verified relations:
[R1]

verified transitions:
[]

unresolved edges:
[U1]

binding coverage:
unchanged
```

Deterministic result:

```text
synthetic_record_count:
10

complete root-source sets:
1

claim-state digest before:
equal to claim-state digest after

outputs:
SYNTHETIC_RECORD_GROWTH_WITH_NO_CLAIM_STATE_CHANGE
NO_CLAIM_STATE_CHANGE
```

The result does not classify the records for another claim.

---

## 40. Measured example — synthetic input with observed comparison contribution

Input state:

```text
claim:
C2

unresolved edge:
U2
```

Synthetic record:

```text
S20

content origin:
synthetic_generation

declared role:
test vector
```

Observed comparison:

```text
validator execution:
directly recorded

comparison input:
S20

comparison result:
PASS

verifier identity:
V1
```

After-state:

```text
U2:
resolved

verified relation:
R20 added
```

Structured result:

```text
synthetic record origin:
preserved

observed validator event:
preserved

information contribution:
EDGE_RESOLVED
RELATION_ADDED
```

The information contribution is bound to the observed comparison and verifier
result.

Synthetic origin remains unchanged.

---

## 41. Measured example — incomplete lineage

Synthetic record:

```text
S30
```

Available provenance:

```text
generator identity:
present

source-input identities:
missing
```

Result:

```text
SYNTHETIC_LINEAGE_UNRESOLVED

ROOT_SET_UNRESOLVED

INDEPENDENT_EXTERNAL_OBSERVATION_NOT_ESTABLISHED
```

No source-multiplicity conclusion is emitted.

---

## 42. Proof rule

A result is mechanically established only when:

```text
all required inputs are identity-bound
+
the measurement contract is exact
+
the verifier is exact
+
the before-state is reproducible
+
the after-state is reproducible
+
the structured delta is reproducible
+
the result bytes replay exactly
```

The complete relation is:

```text
exact inputs
+
exact measurement procedure
+
exact verifier
+
deterministic replay
→
measured result
```

No result in this document depends on an unmeasured empirical assumption.

---

## 43. Authority boundary

Every result defined by this document has:

```text
authority_effect:
none
```

A measurement result can become authority-bearing only through a separate,
explicit PULSEmech policy and promotion process.

The following relation is prohibited:

```text
measurement result
→
automatic release authority
```

---

## 44. Final mechanical position

The data-volume result is:

```text
record count changed
+
claim-state vector unchanged
→
NO_CLAIM_STATE_CHANGE
```

The synthetic-multiplicity result is:

```text
synthetic record count increased
+
claim-state vector unchanged
→
SYNTHETIC_RECORD_GROWTH_WITH_NO_CLAIM_STATE_CHANGE
```

The source-lineage result is:

```text
shared complete observed root-source set
→
SHARED_ROOT_SOURCE
```

The saturation result is:

```text
comparable state-record window
+
no claim-state change
+
required unresolved relations or transition edges remain
→
STATE_MEASUREMENT_SATURATED_UNDER_BOUND_WINDOW
```

The transition-gap result is:

```text
state-measurement saturation
+
unresolved required transition edges
→
TRANSITION_MEASUREMENT_GAP_PRESENT
```

Each output is bound to exact inputs, an exact contract, an exact verifier, and
deterministic replay.
