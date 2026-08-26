# PULSEmech Transition Meter

## The Missing Instrument Between Measured States

## Status

```text
document_role: central_architecture_document
architecture_role: transition_measurement_foundation
reference_role: foundational_measurement_principle
measurement_object: evidence_bound_transition_identity
current_concrete_domain: artifact_bound_ai_release_transitions
general_domain_extension: design
authority_effect: none
```

This document defines the central measurement function that PULSEmech is positioned to provide: a **transition meter** for observing, reconstructing, binding, and validating changes in relationships between measured system states.

A transition meter is an instrument class, not necessarily one physical device. It may be implemented through physical instruments, software records, artifact chains, domain verifiers, evidence protocols, or a combined measurement system.

Domain instruments measure states, values, events, rates, flows, trajectories, and local dynamics.

Those measurements do not automatically establish an evidence-bound transition identity across time, instruments, artifacts, system boundaries, or disciplines.

PULSEmech treats that transition identity as a separate measurement object.

The transition meter does not replace domain measurement.

It connects domain measurements through a verifiable transition structure.

Its central question is:

> **Which relation changed, which path opened or closed, what evidence binds that path to the measured states, and what remains unresolved?**

---

## 1. Why the Transition Meter Is a Missing Instrument

The dominant measurement grammar of current science is state-bound.

A domain instrument usually returns an observable bound to an identified object, location, timestamp, or measurement interval.

Examples include:

```text
temperature
pressure
radiation
position
velocity
acceleration
flow
current
frequency
concentration
mass
energy consumption
```

Some of these quantities describe motion, rate, or local dynamics rather than a static condition.

At the instrument output boundary, they are still normally expressed as measured values associated with a defined measurement frame.

They answer forms of:

```text
What is measured?
Where is it measured?
When is it measured?
How much is present?
How fast is it moving?
What difference is visible across the interval?
```

These measurements are essential.

They establish states, values, events, rates, trajectories, and local dynamic behavior with domain-specific precision.

They do not automatically identify the mechanical transition that connects one measured state to another.

The transition meter asks a different class of question:

```text
What changed first?
Which relation changed?
Which transition opened the later path?
Which previous path closed?
Which boundary carried the change?
Which later effect is feedback rather than initiation?
What evidence binds the initiating transition to the observed consequence?
Which alternative transition paths remain admissible?
```

The distinction is:

```text
state
!=
transition
```

and:

```text
measured state difference
!=
measured transition identity
```

and:

```text
observed consequence
!=
measured initiating transition
```

and:

```text
accurate endpoints
!=
verified path between the endpoints
```

Domain sciences may already measure trajectories, reactions, process stages, event sequences, and parts of causal pathways.

The missing object is not every form of dynamic observation.

The missing instrument class is a general mechanism whose primary measurement object is the **evidence-bound identity of the transition itself** across:

```text
time
instruments
artifacts
system boundaries
measurement surfaces
disciplinary boundaries
```

Its measured structure is:

```text
relationship before
→ changed relation
→ path opened, closed, or redirected
→ relationship after
```

bound to:

```text
identified source state
identified target state
ordered time
system boundary
measurement provenance
transition evidence
alternative paths
unresolved links
reproduction status
```

This is why the transition meter is a missing instrument.

Current measurement systems can observe a large consequence with high precision while the initiating transition remains mechanically invisible.

The later state may be fully measurable.

The first relation change may have been:

```text
smaller than the observation threshold
shorter than the sampling interval
located between instruments
located between disciplines
visible only as a changed relation
gone before the consequence became measurable
replaced by feedback that now maintains the result
```

Without a transition measurement, the record may contain:

```text
precise state before
+
precise state after
+
precise large consequence
```

while still lacking:

```text
the measured transition that made the later path possible
```

The transition meter is therefore not another state instrument.

It measures the missing object between measured states.

A JSON document, schema, database row, trace, or evidence packet may carry the resulting record.

The carrier is not the instrument class.

The instrument class is the complete mechanism that:

```text
observes or reconstructs the relation change
binds it to identified states
binds it to time and boundary
verifies the evidence path
preserves alternative paths
preserves unresolved links
separates observation from causal declaration
separates measurement from authority
```

The central position can be stated directly:

> **The decisive part of a system change may remain unmeasured even when both surrounding states and the resulting consequence are measured precisely. The Transition Meter instruments that missing transition.**

---

## 2. Central position

A measured system may provide accurate records of what existed before and what exists after a change.

```text
measured state before
+
measured state after
```

This does not necessarily provide:

```text
the identity of the transition between them
```

The central PULSEmech measurement chain is:

```text
domain instrument
→ domain measurement record
→ domain verification
→ identified state record
→ recorded relation change
→ observed or reconstructed transition path
→ evidence binding
→ unresolved-path preservation
→ independently controlled authority effect
```

The domain remains responsible for the meaning and validity of its own measurements.

PULSEmech is responsible for the mechanical connection between those measurements:

```text
which record belongs to which state
which relation changed
which path is evidenced
which path remains possible
which link is absent
which reconstruction is reproducible
which result must remain non-authoritative
```

The common layer is not a common unit of measurement.

PULSEmech does not convert:

```text
temperature
pressure
velocity
current
policy state
model output
release result
```

into one shared scalar.

It provides a common structure for transition identity:

```text
state identity
+
relation identity
+
path identity
+
time binding
+
boundary binding
+
evidence binding
+
verifier binding
+
unresolved-state preservation
```

---

## 3. The measurement gap

Existing measurement systems can be highly accurate inside their own domains.

They answer questions such as:

```text
What is the value?
Where is the object?
How fast is it moving?
How much did it change?
Which event was detected?
Which threshold was crossed?
Which output was produced?
Which decision state was recorded?
```

When a conclusion depends on how one state became another, additional questions appear:

```text
Which relation changed first?
Which connection carried the change?
Which path became available?
Which previous path became unavailable?
Which boundary did the transition cross?
Which observation belongs to the initiating transition?
Which later observation belongs to feedback?
Which alternative path remains admissible?
What evidence connects the path to both endpoints?
```

The gap does not arise because domain instruments are imprecise.

The gap arises because accurate local measurements do not automatically create a complete, evidence-bound transition record.

A system can therefore be extensively measured while the decisive transition remains unresolved.

---

## 4. State measurement is not transition measurement

Let a system have two measured states:

```text
S0
S1
```

An endpoint measurement may establish:

```text
S0 != S1
```

It may also calculate a difference:

```text
Delta(S0, S1)
```

Neither result uniquely identifies:

```text
T: S0 → S1
```

Several mechanically different transition paths may connect the same measured endpoints.

```text
S0 → path A → S1
S0 → path B → S1
S0 → path C → S1
```

The visible endpoint may be equal or observationally equivalent while the path remains different.

Therefore:

```text
measured state difference
!=
measured transition identity
```

The missing object is not another value attached to `S0` or `S1`.

The missing object is the evidence-bound relationship path that connects them.

---

## 5. Transition Measurement Necessity

### 5.1 Formal statement

Let:

```text
P(S0, S1)
```

be the set of admissible transition paths between measured states `S0` and `S1`.

Let the endpoint measurement function be:

```text
M_E(p) = (S0, S1)
```

for a path:

```text
p ∈ P(S0, S1)
```

If there exist two distinct admissible paths:

```text
p_a != p_b
```

such that:

```text
M_E(p_a) = M_E(p_b)
```

then `M_E` is not injective with respect to transition-path identity.

The endpoint measurements cannot uniquely identify which path occurred.

### 5.2 Consequence

A complete transition claim requires additional path-discriminating evidence that binds at least:

```text
source state
changed relation
transition path
target state
```

Therefore:

> **Where more than one admissible path can connect the same measured endpoints, endpoint measurement alone is insufficient to identify the transition.**

### 5.3 Claim-dependent completeness

Measurement completeness depends on the claim being made.

For a state claim:

```text
What was measured at S0?
What was measured at S1?
```

endpoint records may be sufficient.

For a transition claim:

```text
How did S0 become S1?
```

path evidence is required.

For a causal claim:

```text
Was this path necessary, sufficient, contributory, or merely correlated?
```

additional causal evidence is required.

The transition meter must not silently promote one claim class into another.

---

## 6. Four separate measurement objects

The transition meter separates four objects that are often compressed into one word.

### 6.1 State difference

A state difference records that two measured states are not identical.

```text
Delta_S = Delta(S0, S1)
```

It does not identify the connecting mechanism.

### 6.2 Relation transition

A relation transition records a change in the relation set of the system.

```text
R0 → R1
```

Examples include:

```text
connection opened
connection closed
direction changed
dependency added
dependency removed
authority moved
flow redirected
coupling changed
```

### 6.3 Transition path

A transition path is an ordered sequence of relation transitions and boundary crossings.

```text
p = [e1, e2, ..., en]
```

where each `e_i` is an identified transition element.

```text
S0
→ e1
→ e2
→ ...
→ en
→ S1
```

### 6.4 Transition record

A transition record is the artifact that binds the path to measurements, identities, boundaries, times, evidence, and verifiers.

```text
transition path
+
measurement binding
+
evidence binding
+
verifier binding
+
status
→ transition record
```

A relation transition is not the same object as a full path.

A path is not the same object as its evidence record.

The record is not proof of causal completeness unless the required causal conditions are separately met.

---

## 7. Why small changes may produce large effects

A small initiating change does not need to supply the energy, authority, pressure, information, or flow of the resulting large movement.

It may only need to change the path through which an existing resource can act.

A switch does not generate the energy of a power plant.

It changes whether an existing path is open.

A valve does not create system pressure.

It changes where the pressure can act.

A permission change does not create the capability of a system.

It changes whether the capability can cross an execution boundary.

A small geometric shift does not need to contain the energy of a rotating or fluid system.

It may change coupling, timing, direction, or accessibility.

The relevant chain may be:

```text
small relation change
→ transition path opens or closes
→ existing system capacity follows a different path
→ feedback begins
→ new state becomes self-maintaining
```

The significance of the initiating change is therefore determined by both:

```text
local magnitude
+
system position
```

A locally small transition can be systemically decisive when it changes a high-leverage relation.

---

## 8. Why the initiating transition may disappear from view

The initiating transition may be:

```text
smaller than the normal observation threshold
shorter than the measurement interval
located between instrument surfaces
located between disciplinary boundaries
visible only as a relation change
distributed across multiple systems
absent by the time the later effect is measured
classified as noise because its local magnitude is small
```

By the time a large external consequence appears, the initiating transition may no longer exist as a directly observable event.

The new state may already be maintained by secondary feedback.

A later measurement can then observe:

```text
large consequence
```

without preserving:

```text
initiating transition
```

The consequence may be measured precisely while the path that produced it remains unresolved.

This is not proof that no transition occurred.

It means:

```text
the transition path is not sufficiently instrumented
```

---

## 9. Time binding

A multi-element transition path cannot rely on one aggregate event window or one aggregate observation window.

Each transition element must preserve its own time bindings.

For every ordered element `e_i`, the record should bind at least:

```text
element_id
sequence_index
event_time_binding
observation_time_binding
```

An event-time binding may contain:

```text
instant
or
interval_start
interval_end
precision
uncertainty
clock_or_source_identity
```

An observation-time binding may contain:

```text
instant
or
interval_start
interval_end
precision
uncertainty
observer_or_instrument_identity
```

The element order must be reconstructable from the preserved sequence indexes and time bindings.

A record-level path window may be derived for indexing or display:

```text
path_event_time_summary
path_observation_time_summary
```

It must not substitute for the per-element bindings.

Two paths can share the same aggregate windows while carrying different element orderings.

Verification time remains a separate binding:

```text
record_verification_time:
when a verifier checked the complete record
```

An element-level verification time may also be retained when separate edges are verified independently.

A fourth record time may be required:

```text
authority_time:
when a verified record was permitted to affect an external decision state
```

These times are not interchangeable.

A record may be current at observation time and stale at authority time.

A transition may occur before any observer records it.

A verifier may inspect correct evidence after the relevant system boundary has already changed.

The transition meter must preserve these differences rather than collapsing them into one timestamp or one path-wide window.

---

## 10. The disciplinary boundary problem

A specialist measures within a defined domain.

That boundary is necessary for precision.

The full system may cross several such boundaries.

For example:

```text
astronomy measures orbital or rotational variables
meteorology measures atmospheric variables
oceanography measures ocean variables
hydrology measures water variables
ecology measures biological variables
engineering measures infrastructure variables
```

A transition chain may cross several measurement spaces:

```text
geometry
→ timing
→ ocean response
→ atmospheric circulation
→ soil moisture
→ regional heat distribution
→ infrastructure load
```

Each local measurement may be valid.

The complete transition path does not arise automatically from the collection of local results.

Many accurate partial measurements can still leave these questions open:

```text
which records belong to the same transition
which event preceded which
which boundary carried the effect
which relation changed at each step
which alternative path remains possible
where the chain is broken
```

The missing measurement is often the evidence-bound connection between the measurements.

---

## 11. Domain instruments and the PULSEmech adapter boundary

PULSEmech does not assign domain meaning to measurements that require specialist authority.

The domain measurement chain is:

```text
domain instrument
→ domain measurement record
→ domain verifier
→ domain adapter
→ normalized transition carrier
→ PULSEmech transition verifier
```

### 11.1 Domain responsibility

The domain remains responsible for:

```text
instrument validity
calibration
unit meaning
measurement uncertainty
sampling method
domain-specific acceptance rules
domain-specific causal interpretation
```

### 11.2 Adapter responsibility

The adapter is responsible for preserving the domain result in a transition-compatible carrier.

It binds:

```text
entity identity
state identity
relation identity
event time
observation time
system boundary
measurement reference
domain verifier identity
domain result
```

The adapter must not rewrite a domain conclusion into a stronger claim.

### 11.3 PULSEmech responsibility

PULSEmech is responsible for:

```text
cross-record identity
time ordering
relation-change identity
path continuity
evidence references
alternative-path preservation
boundary coverage
reconstruction status
replay status
authority separation
```

The adapter connects domains without erasing their boundaries.

The normalized carrier provides common transition structure, not common scientific meaning.

---

## 12. The ant-in-the-glass illustration

Consider an ant standing in a glass.

Yesterday the water reached the ant's ankle.

Today it reaches the ant's knee.

The ant can measure the local increase correctly.

That measurement does not establish:

```text
how much water is in the glass
whether the glass is nearly empty or nearly full
where the water came from
whether the glass moved
whether the glass tilted
whether the ant moved downward
where the glass itself stands
whether the glass is part of a larger mechanism
```

The local measurement may be accurate.

The system reconstruction may remain incomplete.

The distinction is:

```text
accurate local measurement
!=
complete transition reconstruction
```

A transition meter would not replace the ant's water-level measurement.

It would attempt to bind the changed relations among:

```text
ant
water
glass
supporting surface
wider environment
```

The illustration does not establish a specific causal path.

It shows why a valid local value does not uniquely identify the system transition.

---

## 13. Definition of the transition meter

A **transition meter** is a measurement mechanism that records and validates changes in system relationships across time, boundaries, instruments, and artifacts.

Its primary object is:

```text
relationship_before
→ transition element
→ relationship_after
```

Its path object is:

```text
source state
→ ordered relation changes
→ boundary crossings
→ target state
```

Its evidence object is:

```text
path identity
+
measurement references
+
artifact identities
+
time bindings
+
verifier identities
+
known alternatives
+
unresolved links
```

A transition meter should be able to answer:

```text
Which entities were connected before the change?
Which relation changed?
Which new path became available?
Which previous path became unavailable?
Which system boundary was crossed?
What evidence binds the path to the source state?
What evidence binds the path to the target state?
Which later effects depend on the transition?
What feedback, if any, maintains, amplifies, or damps the resulting state?
Can the path be independently reconstructed?
Which alternative paths were excluded?
Which alternative paths remain admissible?
Which links remain unobserved?
Where must the result fail closed?
```

---

## 14. Transition identity

A transition cannot be identified only by naming its endpoints.

A minimum transition identity should bind:

```text
transition_id
source_state_ref
target_state_ref
relation_before
relation_after
changed_relations
ordered_transition_elements
path_identity
participating_entities
system_boundary
boundary_crossings
record_verification_time_binding
domain_verifier_binding
transition_verifier_binding
alternative_paths
unresolved_edges
reconstruction_method
status_axes
authority_effect
```

Each ordered transition element must carry its own edge-level bindings:

```text
element_id
sequence_index
source_relation_ref
target_relation_ref
changed_relation
path_effect
event_time_binding
observation_time_binding
time_precision
time_uncertainty
measurement_refs
evidence_refs
domain_verifier_refs
element_observation_status
element_binding_status
element_consistency_status
```

Record-level time bounds and evidence inventories may be included as derived
summaries.

They must not substitute for edge-level time and evidence bindings.

A compact identity form is:

```text
T_id =
(
  source,
  ordered_elements(
    changed_relation,
    path_effect,
    event_time,
    observation_time,
    evidence
  ),
  target,
  boundary,
  record_verifier
)
```

Two transitions with the same source and target state may remain mechanically different.

```text
S0 → path A → S1
```

is not identical to:

```text
S0 → path B → S1
```

The path is part of the transition identity.

The evidence and verifier bindings are part of the record identity.

---

## 15. Required evidence structure

A transition claim must not be accepted because it is plausible.

It requires an evidence path.

A minimal initiating-transition evidence chain is:

```text
observed source state
→ recorded relation change
→ observed or reconstructed ordered path
→ observed target state
```

Persistence, feedback, damping, or termination evidence is a separate optional
post-transition phase:

```text
observed target state
→ optional maintenance-phase evidence
```

The maintenance phase must carry an explicit status when represented:

```text
not_evaluated
not_applicable
transient_transition
no_feedback_observed
feedback_observed
damping_observed
termination_observed
unknown
conflicting
```

Missing maintenance evidence must not invalidate an otherwise complete one-shot
or transient initiating transition.

It must remain `unknown`, `not_evaluated`, or `not_applicable` rather than being
silently converted into a feedback claim.

For a multi-element path, every transition element must preserve:

```text
element identity
sequence index
changed relation
path effect
event-time binding
observation-time binding
measurement references
evidence references
domain verifier references
boundary binding
element observation status
element binding status
element consistency status
```

The complete initiating chain should also preserve:

```text
source identity
target identity
relation identity
path identity
record verification time
transition verifier identity
system boundary
alternative paths
failed paths
excluded paths
unresolved links
```

A missing link must remain visible.

The transition meter must not replace an absent edge with a narrative connector.

---

## 16. Observation, reconstruction, and hypothesis

The meter must distinguish direct observation from reconstruction.

### 16.1 Directly observed transition element

```text
the relation change was recorded at the relevant boundary
```

### 16.2 Reconstructed transition element

```text
the relation change was derived from preserved evidence
under an explicit reconstruction rule
```

### 16.3 Hypothesized transition element

```text
the relation change is an admissible explanation
but lacks sufficient evidence binding
```

These states may appear inside one path.

For example:

```text
edge 1: directly observed
edge 2: reconstructed
edge 3: unresolved
edge 4: directly observed
```

The path must not be promoted to fully observed because some edges are observed.

The record must preserve edge-level status.

---

## 17. Transition measurement versus causal declaration

A sequence does not by itself establish a complete causal claim.

Correlation does not establish necessity.

Reproduction does not automatically establish exclusivity.

The transition meter therefore separates:

```text
transition observed
transition reconstructed
transition temporally ordered
transition causally contributory
transition causally enabling
transition causally sufficient
transition causally necessary
transition causally exclusive
```

These are different mechanical states.

A valid transition record may state:

```text
The relation changed.
The target state followed.
The path was reproduced under the recorded boundary conditions.
Causal sufficiency remains unverified.
```

The causal classification must state what was actually established.

Possible causal statuses include:

```text
not_evaluated
sequence_only
correlated
contributory_supported
enabling_supported
sufficiency_supported
necessity_supported
exclusive_path_supported
conflicting
unresolved
```

The transition meter first records the path.

Causal promotion requires separate evidence criteria.

---

## 18. Multiaxial transition status

A transition record cannot be represented safely by one flat status label.

One record may be:

```text
reconstructed
+
partially bound
+
conflicting
+
not reproduced
+
non-authoritative
```

The status model therefore uses separate axes.

### 18.1 Observation status

```text
directly_observed
partially_observed
reconstructed
hypothesized
not_observed
```

### 18.2 Binding status

```text
bound
partially_bound
unbound
stale
identity_conflict
```

### 18.3 Consistency status

```text
consistent
ambiguous
conflicting
internally_incomplete
```

### 18.4 Reproduction status

```text
reproduced
bounded_replay_only
not_reproduced
not_tested
not_reproducible
```

### 18.5 Causal status

```text
not_evaluated
sequence_only
correlated
contributory_supported
enabling_supported
sufficiency_supported
necessity_supported
exclusive_path_supported
conflicting
unresolved
```

### 18.6 Authority status

```text
none
diagnostic
candidate
authority_bearing
blocked
```

No axis may silently overwrite another.

Any machine-readable minimum record must serialize all six axes explicitly,
preferably within one structured `status_axes` object.

A scalar `record_status` must not replace or collapse them.

A record may remain diagnostically valuable while blocked from external authority.

---

## 19. Evidence coverage instead of aggregated confidence

A single confidence number can hide the mechanical shape of the evidence.

The transition meter should record coverage directly.

Example fields include:

```text
required_edges
directly_observed_edges
reconstructed_edges
hypothesized_edges
unresolved_edges
required_boundaries
observed_boundaries
unobserved_boundaries
excluded_paths
remaining_admissible_paths
element_time_binding_coverage
element_evidence_binding_coverage
artifact_coverage
verifier_coverage
feedback_coverage
```

A useful record says:

```text
7 required transition edges
4 directly observed
2 evidence-bound reconstructed
1 unresolved
3 alternative paths excluded
1 alternative path remains admissible
```

It does not compress this structure into:

```text
83 percent confidence
```

Coverage remains inspectable, reproducible, and mechanically actionable.

---

## 20. Transition meter layers

A practical transition meter requires several distinct layers.

### 20.1 Domain measurement layer

Records domain-specific values, events, rates, flows, or local dynamics.

```text
measurement_0
measurement_1
measurement_2
```

### 20.2 State layer

Binds measurements into identified system states.

```text
S0
S1
S2
```

### 20.3 Relation layer

Records which entities, values, policies, forces, permissions, or flows are connected.

```text
R0
R1
R2
```

### 20.4 Transition-element layer

Records individual changes between relation states.

```text
R0 → R1
```

### 20.5 Path layer

Orders transition elements and boundary crossings.

```text
S0
→ e1
→ e2
→ e3
→ S1
```

### 20.6 Evidence layer

Binds each path element to measurements, artifacts, times, and verifiers.

```text
edge
→ evidence
→ verifier
```

### 20.7 Alternative-path layer

Records paths that remain admissible, conflicting, excluded, or impossible under the preserved evidence.

```text
path_a: supported
path_b: excluded
path_c: unresolved
```

### 20.8 Feedback layer

Records whether a post-transition maintenance phase exists and, where present, what maintains, amplifies, redirects, damps, or terminates the new state.

```text
not_evaluated
not_applicable
transient_transition
no_feedback_observed
positive_feedback
negative_feedback
delayed_feedback
stabilizing_feedback
termination_effect
unknown_feedback
conflicting_feedback
```

The feedback layer is optional for identifying the initiating transition.

It becomes required only for claims about persistence, maintenance, amplification, damping, or termination.

### 20.9 Authority layer

Controls whether the transition record may produce an externally effective conclusion.

```text
diagnostic only
candidate
verified
authority-bearing
blocked
```

The layers are connected.

They are not interchangeable.

---

## 21. Feedback is not the initiating transition

A system may enter a new state through one transition and remain there through another mechanism.

The meter must distinguish:

```text
initiating_transition
```

from:

```text
maintaining_feedback
```

Example:

```text
relation change opens path
→ existing flow moves
→ new state appears
→ feedback maintains new state
```

A later observer may see only the maintaining feedback.

If the feedback is misclassified as the initiating transition, the reconstruction begins too late.

The transition record should therefore distinguish:

```text
initiation evidence
propagation evidence
maintenance evidence
damping evidence
termination evidence
```

Maintenance is not a mandatory final edge of initiating-transition identity.

These later phases are bound where available and classified through an explicit
maintenance status.

A one-shot or transient transition may be complete without persistence or
feedback evidence.

Unknown phases remain explicitly unknown.

---

## 22. The missing-measurement principle

The central principle is:

> **A system may be extensively measured while its decisive transition remains unmeasured.**

This occurs when the measurement surfaces preserve states, events, or local dynamics without preserving the relation change and path identity that connect them.

The absence of a measured path is not evidence that no path exists.

It establishes only:

```text
transition identity unresolved under current instrumentation
```

This distinction is essential where small relation changes can redirect large existing forces, capabilities, permissions, or flows.

---

## 23. Fail-closed requirement

The transition meter must not invent missing paths.

If the evidence shows:

```text
S0
```

and later:

```text
S1
```

but the transition is not observed or reconstructable, the correct result is:

```text
TRANSITION_UNRESOLVED
```

not:

```text
ASSUMED_PATH_CONFIRMED
```

If two paths remain supported, the result is:

```text
TRANSITION_AMBIGUOUS
```

If preserved evidence supports incompatible paths, the result is:

```text
TRANSITION_CONFLICTING
```

If identity or time binding is missing, the result is:

```text
TRANSITION_UNBOUND
```

If a previously valid record no longer matches the current state, boundary, policy, artifact, or verifier, the result is:

```text
TRANSITION_STALE
```

These states are outputs.

They are not failures to produce an answer.

The fail-closed rule preserves the difference between:

```text
known path
unknown path
multiple paths
conflicting paths
invalid binding
```

No missing edge may be silently promoted into a confirmed transition.

---

## 24. Reproduction requirement

A transition record becomes stronger when an independent verifier can reconstruct the same path from the same preserved evidence.

Reproduction requires:

```text
stable artifact identities
preserved source records
ordered event times
ordered observation times
explicit transformation rules
domain verifier identity
transition verifier identity
boundary conditions
alternative-path analysis
deterministic or bounded replay
recorded tool and policy identities
```

A reproduced path must state the scope of reproduction.

```text
exact replay
bounded replay
structural reconstruction
partial reconstruction
```

A transition that cannot be reproduced may still be important.

Its status must remain visible and non-promoted.

---

## 25. Difference from adjacent instruments

### 25.1 Dashboard

A dashboard usually shows:

```text
current value
trend
threshold
alert
```

A transition meter shows:

```text
relationship before
relation change
ordered path
opened or closed route
evidence binding
resulting state
feedback
alternatives
unresolved links
```

The dashboard displays indicators.

The transition meter binds the path between states.

### 25.2 Event log

An event log preserves a sequence of recorded events.

A sequence does not automatically establish:

```text
relation identity
path continuity
boundary coverage
alternative-path exclusion
causal status
authority eligibility
```

The transition meter may consume logs as evidence.

It does not treat log order alone as a complete transition proof.

### 25.3 Distributed trace

A trace can preserve technical call propagation across instrumented components.

It may not capture:

```text
unobserved domain relations
cross-discipline meaning
external physical transitions
alternative admissible paths
evidence sufficiency
authority boundaries
```

A trace can be one carrier inside a transition record.

It is not automatically the complete transition identity.

### 25.4 Causal model

A causal model represents proposed dependency structure.

A transition meter records whether a particular path is observed, reconstructed, unresolved, conflicting, or reproducible under preserved evidence.

The model can propose admissible paths.

The meter records the evidentiary state of a concrete transition.

---

## 26. Why PULSEmech is suited to this function

PULSEmech already treats externally effective decisions as artifact-bound transitions rather than free-standing outputs.

Its existing mechanical principles include:

```text
explicit state identity
artifact binding
policy binding
verifier binding
current-run evidence
deterministic replay
fail-closed behavior
separation of recorded evidence from authority
explicit transition boundaries
prevention of silent state promotion
proof before externally effective change
```

These are the foundations required for transition measurement.

The existing release-authority structure already has the general form:

```text
candidate state
→ evidence-bound decision transition
→ terminal primary CI ALLOW or BLOCK
```

A downstream external effect remains a separately governed execution relation:

```text
terminal ALLOW
+
separately controlled executor
→ possible external state change outside the authority record
```

The transition meter generalizes the measurement object while preserving this separation between measured decision transition and downstream execution.

---

## 27. Release authority as the first concrete transition-meter domain

PULSEmech release authority is the first concrete implementation domain of the broader transition-measurement architecture.

The implemented release-authority path is:

```text
candidate artifact state
→ current-run evidence
→ artifact binding
→ policy binding
→ verifier binding
→ gate-state materialization
→ primary CI ALLOW or BLOCK
```

This is the implemented authority-decision boundary.

It binds:

```text
source artifact state
current-run evidence
artifact, policy, verifier, and gate path
terminal primary-CI ALLOW or BLOCK decision
```

The current transition record does not claim a downstream deployment or
externally effective release state.

Release execution remains separately controlled:

```text
primary CI ALLOW
→ separately governed external executor
→ externally effective release state
```

That executor and its resulting state remain outside the implemented record
unless they are separately observed, evidence-bound, and verified.

```text
primary CI BLOCK
→ terminal non-zero CI result
→ no released target state is implied
```

The project identity remains continuous.

```text
PULSEmech release authority
⊂
PULSEmech transition measurement architecture
```

The release-authority mechanism is the already built domain.

The transition meter names the general measurement class that the existing mechanism instantiates.

This does not weaken the release function.

It explains its broader mechanical position.

### 27.1 External incident case study: restart authority and alternative-path closure

The non-normative
[OpenAI–Hugging Face restart-authority and alternative-path-closure case study](docs/PULSEMECH_EXTERNAL_CASE_STUDY_OPENAI_HUGGING_FACE_RESTART_AUTHORITY_AND_ALTERNATIVE_PATH_CLOSURE_v0.md)
maps a publicly documented external event path onto four PULSEmech subjects:

```text
current-run evidence
+
transition-path verification
+
alternative-path closure
+
authority binding
```

The case study keeps four assertion classes separate:

```text
source fact
≠
retrospective reconstruction
≠
PULSEmech structural classification
≠
PULSEmech fail-closed counterfactual
```

It does not claim that PULSEmech alone would have prevented the incident, that
OpenAI used PULSEmech fields internally, or that the historical OpenAI policy
required the counterfactual closure condition.

Its authority effect is:

```text
none
```

---

## 28. Extension of PULSEmech value

Without the generalized transition layer, PULSEmech verifies whether an externally effective decision is supported by bound evidence.

With the transition layer, PULSEmech can also record how a system moved from one identified state to another.

The extension is:

```text
release authority
→ system transition observability
```

and:

```text
Is this decision allowed?
```

extends to:

```text
Which relation changed?
Which path did the change open or close?
What evidence binds that path?
What now maintains the resulting state?
What remains unresolved?
```

The authority function remains separately controlled.

Observation does not create permission.

Reconstruction does not create authority.

Verification does not create external effect unless an explicit authority policy permits it.

---

## 29. Initial non-authoritative implementation direction

The first general transition-meter implementation should remain shadow-only and non-authoritative.

Possible artifacts include:

```text
transition_observation_v0.json
transition_relation_map_v0.json
transition_path_record_v0.json
transition_evidence_chain_v0.json
transition_feedback_state_v0.json
transition_reconstruction_report_v0.json
```

A minimum record may include:

```text
transition_id
source_state_ref
target_state_ref
relation_before
relation_after
changed_relations
path_identity

status_axes:
  observation_status
  binding_status
  consistency_status
  reproduction_status
  causal_status
  authority_status

transition_elements:
  - element_id
    sequence_index
    source_relation_ref
    target_relation_ref
    changed_relation
    path_effect

    event_time_binding:
      start
      end
      precision
      uncertainty
      clock_or_source_identity

    observation_time_binding:
      start
      end
      precision
      uncertainty
      observer_or_instrument_identity

    measurement_refs
    evidence_refs
    domain_verifier_refs

    element_status:
      observation_status
      binding_status
      consistency_status

record_verification_time
transition_verifier_ref
system_boundary
boundary_crossings
evidence_inventory
reconstruction_method
alternative_paths
excluded_paths
remaining_admissible_paths
unresolved_edges

maintenance_phase:
  maintenance_status
  feedback_evidence_refs
  damping_evidence_refs
  termination_evidence_refs

evidence_coverage
authority_effect
```

Every `transition_elements` entry binds its own evidence and its own event and
observation time.

The record-level `evidence_inventory` is an inventory only.

It must not be accepted as proof for an element that lacks `evidence_refs`.

Any record-level aggregate time bounds are derived summaries only.

They must not replace the ordered element-level time bindings required for path
identity and replay.

Initial authority rule:

```text
authority_effect: none
```

The first purpose is:

```text
observation
binding
reconstruction
conflict preservation
replay
measurement-gap discovery
```

Promotion into an authority-bearing path requires a separate explicit policy process.

---

## 30. Minimal transition test

A candidate transition record should answer:

```text
Is the source state identified?
Is the target state identified?
Was at least one relation change recorded?
Does every transition element bind its own supporting evidence?
Does every transition element carry its own event and observation time binding?
Is the ordered path distinguishable from another path with the same aggregate time window?
Are event, observation, and record-verification times distinguished?
Is the system boundary explicit?
Is there evidence for each opened, closed, or redirected path?
Can the target state be connected without skipping an unobserved edge?
Are reconstructed edges distinguished from observed edges?
Are alternative paths recorded?
Are excluded paths supported by evidence?
Is feedback distinguished from initiation?
Is the maintenance phase optional?
Is its status explicit as observed, no feedback observed, not applicable,
transient, unknown, or conflicting?
Can the path be independently reconstructed?
Does the record preserve unresolved edges?
Is authority effect separately controlled?
```

If a required condition is absent, the record remains incomplete on the corresponding status axis.

No single missing condition should be hidden by an aggregate score.

---

## 31. Candidate application classes

The transition-meter architecture can be applied where measured conclusions depend on the path between states.

Candidate classes include:

```text
AI release systems
model-behavior transitions
security incident reconstruction
software supply chains
physical supply chains
energy systems
infrastructure systems
environmental systems
human-AI workflows
institutional decision paths
legal evidence chains
complex scientific reconstruction
```

Each domain requires its own:

```text
instrument definitions
state schema
relation schema
domain verifier
boundary model
causal criteria
```

The shared PULSEmech layer begins only after those domain meanings are preserved.

The generality lies in transition binding, not in replacing domain expertise.

---

## 32. Boundaries and non-goals

The transition meter does not claim:

```text
that every system transition is fully observable
that endpoint measurement is unnecessary
that domain instruments are incomplete for their intended state claims
that every sequence is causal
that every reproduced path is the only possible path
that all scientific units can be unified
that one verifier can replace domain verification
that uncertainty can always be eliminated
that a transition record automatically grants authority
that all complex systems are deterministic
```

It establishes a narrower mechanical requirement:

```text
when a claim depends on how one state became another,
the transition path requires its own evidence-bound identity
```

---

## 33. Central PULSEmech position

PULSEmech treats the transition meter as a missing instrument class.

Its role is not to produce another explanation.

Its role is to record whether an explanation has a measurable path.

The central relation is:

```text
state measurement
+
relation-change evidence
+
path identity
+
boundary binding
+
verifier binding
→ transition measurement
```

The transition record can then state precisely:

```text
observed
reconstructed
ambiguous
conflicting
unbound
stale
not reproduced
unresolved
authority-blocked
```

This converts uncertainty from prose into mechanical state.

---

## 34. Final statement

The world is not composed only of states.

It is also composed of transitions between states.

A measurement system may establish that a system changed.

It may still leave the path of change unmeasured.

PULSEmech adds the missing measurement question:

> **Is the relation that connects the measured states preserved as an evidence-bound transition path?**

Where the path is measured, it can be inspected.

Where it is reconstructed, the reconstruction can be replayed.

Where alternatives remain, they can be preserved.

Where a link is absent, the record can fail closed.

Where authority is requested, the transition can remain blocked until the required evidence path is complete.

The value of the transition meter is not that it fills the gap with a story.

The value is that it makes the gap measurable.
