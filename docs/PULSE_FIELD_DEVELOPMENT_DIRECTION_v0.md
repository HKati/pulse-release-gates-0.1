# PULSE Field Development Direction v0

## Purpose

This document defines the v0 field development direction for PULSE.

It connects the existing field-oriented PULSE documents into a single
development-direction boundary.

The direction is field-structural review around the existing PULSEmech authority
path.

The document records how future development may review state relations,
evidence bindings, mechanical effects, transition conditions, and release-state
outcomes while preserving the deterministic release-authority base.

## Canonical authority path

Release permission is produced by the PULSEmech authority path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

This path is the release-decision authority.

Field development works around this path by reviewing connected release-state
relations.

## Current base

The current PULSE base is the deterministic artifact-bound release-authority
path.

The base is defined by:

```text
recorded evidence
status.json
declared policy
materialized required gates
strict fail-closed CI
allow/block release decision
```

This base is mechanical.

It requires recorded artifacts, declared policy, materialized gate state, and
strict CI enforcement before release permission can exist.

Field development adds relation-aware release-state transition review around
this base.

## Development model

The v0 field-development model is:

```text
state
→ relation
→ evidence binding
→ mechanical effect
→ transition condition
→ fail-closed transition or permitted release-state outcome
```

This model supports review of how release-state artifacts remain connected
around the authority path.

The deterministic authority path produces the allow/block release decision.

The field-structural layer reviews the relations adjacent to that decision path.

## Outcome vocabulary

This document uses two distinct outcome terms.

The canonical authority path produces:

```text
allow/block release decision
```

Field-structural review classifies transitions as:

```text
fail-closed transition
permitted release-state outcome
```

The first term belongs to the deterministic PULSEmech authority path.

The second pair belongs to relation-aware release-state transition review.

## Core distinction

PULSE separates:

```text
deterministic release-decision authority
```

from:

```text
field-structural release-state review
```

The deterministic authority path produces the release decision.

The field-structural review layer examines the connected state around that path.

A field relation supports release-state review through recorded evidence,
declared policy, materialized gates, explicit transition rules, or strict CI
enforcement.

## Connected field documents

This development direction is aligned with the following existing documents:

```text
docs/PULSE_FIELD_INSTRUMENT_PRINCIPLE_v0.md
docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md
docs/PULSE_FIELD_POINT_AUTHORITY_MAP_v0.md
docs/PULSE_decision_field_v0_overview.md
docs/PULSE_decision_engine_v0.md
docs/PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md
docs/FIELD_REFERENCE_CONTRACT_v0.md
docs/PULSE_RELATIONAL_STATE_TRANSITION_v0.md
docs/PULSE_HARDENING_BOUNDARY_MAP_v0.md
docs/PULSE_TERMINOLOGY_RISK_REGISTER_v0.md
```

These documents provide field, relation, transition, reference, terminology, and
boundary support around the PULSEmech authority path.

## Field direction role

The field development direction has the following role:

```text
development orientation for relation-aware release-state review
```

It may guide future work on:

- release-state relation review;
- evidence-binding review;
- mechanical-effect classification;
- transition-condition review;
- pre-materialization blocking;
- decision-field projection;
- compact downstream decision encoding;
- field-point authority classification;
- terminology and misread boundary control.

## Field-structural review

Field-structural review examines how release-state elements are connected.

It may ask:

```text
Which recorded state is being reviewed?
Which relation is asserted?
Which evidence binding supports the relation?
What mechanical effect follows from the bound relation?
Which transition is being attempted?
Does the transition remain fail-closed or become a permitted release-state outcome?
```

This review is relation-aware.

It preserves the deterministic gate path and reviews the surrounding state
relations.

## State

A state is a recorded release-relevant condition.

A state may include:

- status;
- evidence;
- policy;
- gate state;
- CI result;
- artifact identity;
- detector materialization;
- publication classification;
- verifier result.

A state participates in release review when it is connected to the recorded
release-state relation.

## Relation

A relation is the asserted connection between recorded release-state elements.

A relation may connect:

- evidence to status;
- status to declared policy;
- policy to materialized gates;
- gates to strict CI enforcement;
- detector evidence to release-state materialization;
- public artifacts to recorded release-state identity;
- verifier output to reconstruction context;
- field points to authority roles.

A relation becomes reviewable when its evidence binding is recorded.

Repository presence alone remains outside release-state relation.

## Evidence binding

Evidence binding is the recorded connection that allows a relation to be
reviewed.

Evidence binding may include:

- run identity;
- commit identity;
- artifact path;
- artifact digest;
- policy source;
- gate source;
- status source;
- package identity;
- subject identity;
- freshness binding;
- provenance or binding artifact.

Evidence binding supports relation review.

## Mechanical effect

Mechanical effect means the effect of a bound relation on release-state
eligibility or transition status.

Mechanical effect is derived from recorded artifacts, declared policy,
materialized gates, verifier boundaries, or explicit review rules.

Mechanical effect may classify a relation as:

- no release relevance;
- diagnostic context only;
- advisory context only;
- incomplete transition;
- stale transition;
- mismatched transition;
- fail-closed transition;
- permitted release-state outcome.

Mechanical effect is recorded through the relation between artifact state and
declared release-state rules.

## Transition condition

A transition condition defines whether a recorded state may move toward another
release-state outcome.

The transition condition may depend on:

- evidence completeness;
- gate materialization;
- explicit non-stub diagnostics;
- external evidence materialization;
- public/private artifact classification;
- verifier trust boundary;
- relation consistency;
- strict CI enforcement.

Unclear transition conditions remain fail-closed.

## Fail-closed transition or permitted release-state outcome

The field development direction preserves fail-closed behavior.

A transition remains fail-closed when the relation is missing, unbound,
malformed, stale, subject-mismatched, advisory-only, diagnostic-only,
incomplete, or unenforced.

A permitted release-state outcome exists when the canonical authority path is
satisfied.

The field layer records and reviews the transition relation around that outcome.

## Decision field boundary

The decision field preserves decision-relevant structure around a release state.

It may describe:

- polarity;
- stability;
- completeness;
- boundary pressure;
- instability;
- paradox structure;
- relation state.

These concepts participate in review when they are artifact-derived and
reviewable.

The deterministic release result remains the allow/block release decision
produced by the canonical authority path.

## Decision Engine boundary

The Decision Engine may encode or consume decision-field state.

Decision Engine output is diagnostic by default.

A compact decision representation may support downstream review, diagnostic
routing, or field-state interpretation.

Decision Engine output becomes release-relevant when it is bound through
declared policy, materialized gates, and strict CI enforcement.

## Pre-materialization boundary

Pre-materialization mechanics block unsupported authority before it materializes.

This supports the PULSE principle that unsupported closure is stopped before
release authority is formed.

Pre-materialization blocking preserves the authority path by requiring recorded
evidence, declared policy, materialized gates, and strict CI enforcement for
release permission.

## Field-point authority boundary

Field points may be classified by authority role.

Examples may include:

- normative authority path;
- diagnostic surface;
- audit / reconstruction surface;
- publication / reader surface;
- recognition surface;
- optional analysis surface.

Field-point classification helps prevent diagnostic, reader, audit,
publication, or optional surfaces from being misread as release authority.

## Terminology boundary

The field development direction uses mechanical PULSE terminology:

```text
release-authority base
field-structural review
relation-aware transition mechanics
artifact-bound evidence relation
mechanical effect
fail-closed transition
permitted release-state outcome
```

Deployment, adoption, productization, external integration, and enterprise
packaging terminology belong to separate deployment or adoption layers.

PULSEmech identity remains defined by artifact-bound release authority.

## Third-party / adoption boundary

Third-party integration, onboarding, enterprise deployment, example
repositories, external verifier tooling, and adoption packaging are deployment
or adoption layers.

They may support later usage paths around PULSE.

The current field development direction focuses on the PULSE core:

```text
release-authority base
→ field-structural review
→ relation-aware transition mechanics
```

## Mechanical language rule

PULSE-facing field development uses mechanical claims.

A mechanical claim identifies:

- recorded input;
- relation;
- evidence binding;
- mechanical effect;
- transition condition;
- fail-closed transition or permitted release-state outcome.

Prose-only claims remain outside the release-authority path until connected to
recorded artifacts, declared policy, materialized gates, explicit transition
rules, or strict CI enforcement.

## Development priorities

The current field-development priority is:

```text
PULSEmech identity stability
relation-aware release-state review
evidence-binding review
mechanical-effect classification
transition-condition review
fail-closed transition mechanics
terminology and misread boundary control
```

Deployment and adoption priorities may be developed as later layers around the
core.

The current direction is core development.

## Review sequence v0

A field-development review follows this sequence.

### 1. Identify authority impact

Determine whether the change affects the PULSEmech authority path.

If it affects recorded evidence, `status.json`, declared policy, materialized
gates, strict CI enforcement, or allow/block release decision, review it as
release-authority relevant.

### 2. Identify field relation

Determine which state relation is being introduced, reviewed, or changed.

If no relation is identifiable, the change remains diagnostic or prose-only.

### 3. Verify evidence binding

Determine whether the relation is bound to recorded artifacts, run identity,
commit identity, policy source, gate source, digest, or other reviewable
evidence.

Unbound relations remain non-authorizing.

### 4. Derive mechanical effect

Derive the mechanical effect from recorded artifacts and declared rules.

The effect must follow from artifact state and explicit relation rules.

### 5. Evaluate transition condition

Determine whether the attempted transition is complete, bound, current,
subject-matched, materialized, and enforceable.

Unclear transition conditions remain fail-closed.

### 6. Preserve authority boundary

Confirm that the reviewed transition is evaluated through the canonical
authority path when release permission is claimed.

### 7. Check terminology boundary

Confirm that the wording keeps the change in mechanical PULSE terms:

```text
state
relation
evidence binding
mechanical effect
transition condition
fail-closed transition
permitted release-state outcome
```

## Fail-closed field conditions

A field-structural transition remains fail-closed when any of the following
conditions apply:

```text
state is unrecorded
relation is unasserted
relation is unbound
evidence binding is missing
evidence binding is malformed
evidence is stale
evidence is subject-mismatched
external evidence is present but not materialized
reader surface is presented as authority
publication exposure is presented as release permission
release-grade lane eligibility is presented as release permission
field projection is presented as release authority
Decision Engine output is presented as release permission
adoption layer is presented as PULSEmech identity
hardening layer is presented as PULSEmech definition
mechanical effect is inferred from prose alone
transition condition is unclear
strict CI enforcement is absent where release permission is claimed
```

Any unclear field transition remains fail-closed.

## Future work

Future work may include:

- terminology risk guard;
- rhetoric guard specification;
- field-point authority classifier;
- relation-state transition checker;
- mechanical-effect classifier;
- field-to-status relation inventory;
- pre-materialization transition guard;
- decision-field projection validator;
- external evidence materialization checker;
- publication exposure classifier.

Executable implementations preserve the PULSEmech authority path.

Future tooling fails closed when relations, bindings, effects, or transition
conditions are unclear.

## Summary

The PULSEmech authority path establishes the deterministic release-decision base.

The field development direction extends review around that base by preserving
and examining state relations, evidence bindings, mechanical effects, transition
conditions, and fail-closed transitions or permitted release-state outcomes.

The current direction is:

```text
PULSEmech base
→ field-structural review
→ relation-aware release-state transition mechanics
```
