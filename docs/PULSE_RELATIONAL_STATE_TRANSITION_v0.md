# PULSE Relational State Transition Layer v0

## Purpose

PULSEmech defines the artifact-bound release-decision authority path.

The relational state transition layer defines a review model for evaluating
whether recorded elements associated with a pre-deployment release decision are
connected through state, relation, evidence binding, mechanical effect, and
decision transition.

This v0 document is definitional.

It does not introduce a separate PULSE identity.

It does not modify the existing release-decision authority path.

## Authority boundary

This document does not change PULSEmech release authority.

It does not add a gate.

It does not change policy.

It does not change `check_gates.py` behavior.

It does not modify schemas.

It does not alter workflow mechanics.

It does not create a second release-decision engine.

It defines review concepts for evaluating state transitions above the existing
artifact-bound release-authority path.

The PULSEmech authority path remains the only path that can produce release
permission.

## Canonical PULSEmech authority path

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

This path remains unchanged by the relational state transition layer.

The relational layer may review how release-state elements remain connected
above this path.

It may not loosen, bypass, replace, or reinterpret this path.

## Relational transition model

The v0 relational transition model is:

```text
state
→ relation
→ evidence binding
→ mechanical effect / kihatás
→ decision transition
→ fail-closed or permitted release state
```

This model does not replace the PULSEmech authority path.

It defines how recorded release-state elements are reviewed as connected state
transitions.

The release decision remains bound to the PULSEmech authority path.

## Core rule

The core v0 rule is:

```text
Relation plus evidence binding determines whether an element can participate in
a release-state transition.
```

Repository existence alone does not confer release authority.

A repository element can participate in a release-state transition only when it
is bound into the recorded release-state relation and its mechanical effect can
be derived from the PULSEmech authority path.

## Core terms

### State

A state is a recorded pre-deployment condition within the artifact-bound release
path.

A state may include recorded release evidence, `status.json`, declared policy,
materialized gates, CI results, and related provenance identifiers when they are
bound into the same release-state relation.

A loose repository item is not a release state by itself.

A live surface is not a release state by itself.

A historical note is not a release state by itself.

A prose statement is not a release state by itself.

A recorded state becomes release-relevant only when it is bound into the
release-state relation.

### Relation

A relation is the asserted and reviewable connection between recorded elements
that belong to the same release-state path.

Relation is not inferred from repository presence alone.

Relation is not inferred from prose alone.

Relation is not inferred from name similarity alone.

Relation is not inferred from file proximity alone.

A repository element becomes release-relevant only when it is bound into the
recorded release-state relation.

Relation defines whether an element can be reviewed as part of a connected
release-state transition.

### Evidence binding

Evidence binding is the provenance connection that allows a relation to be
asserted.

A release-state relation requires shared or explicitly linked binding across the
relevant recorded elements.

The binding should be reviewable through release identifiers such as:

- run identity;
- commit identity;
- policy source;
- artifact source.

Where available, additional identifiers may strengthen the binding, including:

- `created_utc`;
- artifact digest;
- attestation source;
- recorded output location;
- workflow run reference;
- generated artifact path.

Without evidence binding, an element remains diagnostic context only.

It cannot become a release-state transition element.

### Mechanical effect / kihatás

Mechanical effect, or kihatás, means the derived effect of a bound transition on
release-state eligibility.

It is not a general effect claim.

It is not a narrative claim.

It is not inferred from prose.

It is derived from recorded artifacts, declared policy, materialized gates, and
the defined transition rule.

Mechanical effect answers this question:

```text
What does this bound transition mechanically change about release-state
eligibility?
```

The answer may be:

- no release relevance;
- diagnostic context only;
- incomplete transition;
- stale transition;
- mismatched transition;
- fail-closed transition;
- permitted release-state transition.

Mechanical effect is release-state specific.

It does not create authority outside the PULSEmech path.

### Decision transition

A decision transition is the movement from a recorded, evidence-bound state
toward a release-state outcome.

The outcome can become a permitted release state only when the existing
PULSEmech authority path is satisfied.

If the transition is incomplete, unbound, mismatched, stale, or unclear, the
transition remains fail-closed.

A decision transition does not create a second decision engine.

It reviews whether a bound state can participate in the existing PULSEmech
release-decision path.

## Invariants

The v0 relational state transition layer is constrained by the following
invariants.

### 1. No unbound element can become a decision element

An element that is not bound into the recorded release-state relation cannot
participate in a release decision.

It may remain historical context, diagnostic context, documentation context, or
review context.

It is not release authority.

### 2. Repository presence is not release authority

The presence of a file, text block, note, URL, badge, summary, rendered page, or
historical artifact in the repository does not make it release-authoritative.

Release authority comes only from the PULSEmech authority path.

### 3. Evidence binding is required before relation can be asserted

A relation cannot be asserted from similarity, naming, location, or prose alone.

A relation requires evidence binding across the relevant release-state elements.

Without evidence binding, the element remains outside the release-state
transition.

### 4. A relation without shared release identity is diagnostic context only

A relation without shared or explicitly linked run identity, commit identity,
policy source, and artifact source is diagnostic context only.

It cannot become a release-state transition.

It cannot create release permission.

### 5. Mechanical effect cannot be inferred from prose

A prose statement may describe an intended state, but it does not create
release-state eligibility.

Mechanical effect must be derived from recorded artifacts, declared policy,
materialized gates, and the defined transition rule.

### 6. Unclear transition remains fail-closed

If the relation, evidence binding, mechanical effect, or transition outcome is
unclear, the transition remains fail-closed.

Ambiguity cannot create release permission.

### 7. The relational layer must not override PULSEmech

The relational state transition layer must not override the PULSEmech authority
path.

It may review how state transitions remain connected above the existing
authority path.

It may not loosen, bypass, replace, or reinterpret the release-decision
authority.

## Review sequence v0

A relational state transition review follows this sequence.

### 1. Identify the candidate state

Identify the recorded state being reviewed.

The candidate state must be tied to recorded release artifacts or it remains
context only.

### 2. Identify the claimed relation

Identify which elements are claimed to belong to the same release-state path.

The relation must not be inferred from name similarity, file location,
repository presence, or prose alone.

### 3. Verify evidence binding

Check whether the relation is bound through shared or explicitly linked release
identifiers.

The review should look for run identity, commit identity, policy source,
artifact source, and any available artifact provenance identifiers.

If the binding cannot be verified, the element remains diagnostic context only.

### 4. Derive mechanical effect

Derive the mechanical effect on release-state eligibility from recorded
artifacts, declared policy, materialized gates, and the defined transition rule.

Do not derive mechanical effect from prose alone.

### 5. Evaluate the decision transition

Evaluate whether the transition can move toward a permitted release state under
the existing PULSEmech authority path.

If the transition is incomplete, unclear, stale, mismatched, or unbound, it
remains fail-closed.

## Live surfaces and recorded artifacts

A live publication surface is not release authority by default.

A rendered page, README text, badge, summary, or external publication surface can
participate in a release-state transition only when it is explicitly bound as a
recorded artifact in the same release-state relation.

A stale surface may be useful diagnostic evidence.

It does not become release authority unless the PULSEmech authority path binds it
into the recorded decision path.

## Historical and diagnostic material

Historical material may explain why a repository element exists.

Diagnostic material may support review of a mismatch, stale surface, missing
binding, or incomplete transition.

Neither historical material nor diagnostic material becomes release authority by
presence alone.

A historical or diagnostic element can participate in a release-state transition
only if it is bound into the recorded release-state relation and its mechanical
effect is derived from the PULSEmech authority path.

## Failure modes

The relational layer treats the following cases as fail-closed or diagnostic
only.

### Unbound element

An element exists, but no release-state binding is present.

Result:

```text
diagnostic context only
```

### Mismatched relation

Elements appear related, but their run identity, commit identity, policy source,
or artifact source does not match or cannot be explicitly linked.

Result:

```text
diagnostic context only
```

### Prose-only transition

A text statement describes a release condition, but the mechanical effect cannot
be derived from recorded artifacts, declared policy, materialized gates, and the
defined transition rule.

Result:

```text
fail-closed
```

### Stale surface

A rendered or live surface does not match the recorded release-state relation.

Result:

```text
diagnostic context only unless explicitly bound as a recorded artifact
```

### Unclear transition

The transition path cannot be verified.

Result:

```text
fail-closed
```

## v0 scope

This v0 layer defines review concepts only.

It does not add executable behavior.

It does not add a schema.

It does not add a policy rule.

It does not add a gate.

It does not change CI behavior.

It does not change release tags.

It does not change DOI or Zenodo behavior.

Future work may define machine-readable relational transition artifacts only if
they preserve the PULSEmech authority boundary.

## Summary

PULSEmech defines the artifact-bound release-decision authority path.

The relational state transition layer defines a review model for evaluating how
state, relation, evidence binding, mechanical effect, and decision transition
remain connected above that authority path.

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

A repository element becomes release-relevant only when it is bound into the
recorded release-state relation.

Repository existence alone does not confer release authority.

Relation plus evidence binding determines whether an element can participate in
a release-state transition.
