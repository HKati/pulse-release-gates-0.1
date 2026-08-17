# PULSEmech Relational Release-Authority Interpretation v0

## Status

```text
document_role:
canonical_interpretation_anchor

interpretation_scope:
artifact_bound_release_authority

primary_object:
specified_release_state_transition

canonical_relation:
R_tau

terminal_state:
D_tau

authority_effect:
none

implementation_effect:
none
```

## Purpose

This document records the canonical relational interpretation of the existing
PULSEmech release-authority mechanism.

It establishes, in one place:

```text
the specified transition under evaluation;
the bound release-authority relation;
the terminal transition-authority state;
the current carrier and enforcement surface;
the reconstruction question used during technical review.
```

The checked-in PULSEmech mechanics remain the authority source.

This document supplies the coordinate system through which those mechanics are
reconstructed and interpreted.

---

## 1. Specified release-state transition

The object evaluated by PULSEmech is a specified release-state transition:

```text
τ
```

`τ` denotes the release-state transition whose authority state is being
determined under an exact subject, run, artifact, policy, required-set, verifier,
and final gate-state relation.

The transition identity scopes the complete release-authority record.

---

## 2. Bound release-authority relation

For the specified transition `τ`, the complete PULSEmech relation is:

```text
Rτ = ⟨S, E, A, P, G, V, F, Dτ⟩
```

where:

```text
S:
exact subject and run identity

E:
exact current-run release evidence

A:
exact artifact and carrier identities

P:
declared release-policy identity

G:
workflow-effective materialized required-gate state

V:
verifier identity and deterministic replay state

F:
final gate-state carrier

Dτ:
terminal transition-authority state for τ
```

`Rτ` is the transition-scoped form of the existing PULSEmech release relation.

The subscript records that every component and every binding belongs to the same
specified transition `τ`.

No component is evaluated as an isolated label.

Each component has meaning through its bound position inside `Rτ`.

---

## 3. Transition-authority state

The terminal authority state is:

```text
Dτ = AuthorityState(
  τ | S, E, A, P, G, V, F
) ∈ {ALLOW, BLOCK}
```

The two states have exact relational meanings.

```text
ALLOW:
every relation required by the selected policy path for τ is present,
identity-bound, verified, materialized, and closed

BLOCK:
the complete relation required by the selected policy path for τ
is not closed
```

`Dτ` is therefore the authority state of the specified release transition.

It is determined from the complete bound relation rather than from one isolated
test result, score, report, gate, artifact, role, or process label.

---

## 4. Current carrier and enforcement surface

In the current PULSEmech implementation, the primary CI terminal result is the
carrier and enforcement surface of `Dτ`.

The primary CI terminal result:

```text
carries the observed ALLOW or BLOCK state;
enforces the fail-closed consequence of that state;
preserves the terminal result of the complete bound relation.
```

The authority meaning belongs to `Dτ`.

The current primary CI terminal result mechanically carries and enforces that
meaning.

---

## 5. Relational release-authority map

```text
                         specified transition τ
                                   │
                                   │ scopes
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    bound authority relation Rτ                        │
│                                                                        │
│  S ──binds────────────────────────────────────► E                      │
│  │                                                                     │
│  └──identifies────────────────────────────────► A                      │
│                                                                        │
│  V ──verifies E and its bindings to S, A, and P                       │
│  V ──supplies replayable per-entry materialization admissibility      │
│                                                                        │
│  P + workflow-effective policy selection                              │
│    + verifier-bound admissibility                                     │
│    ──materialize the complete workflow-effective gate state────────► G │
│                                                                        │
│  G ──is carried in the final gate-state carrier────────────────────► F │
│                                                                        │
│  S + E + A + P + G + V + F ──close as the complete relation Rτ        │
└──────────────────────────────────────┬─────────────────────────────────┘
                                       │ strict fail-closed evaluation
                                       │ by check_gates.py
                                       ▼
                             Dτ = ALLOW | BLOCK
                          transition-authority state
                    carried and enforced by primary CI
```

The named edges are relations:

```text
scopes
binds
identifies
verifies
supplies admissibility
materializes
carries
closes
evaluates
enforces
```

`V` supplies the verified evidence-binding and per-entry materialization
admissibility state.

The separate policy-derived materializer canonically replays that state and
combines it with the workflow-effective policy selection to produce `G`.

`F` carries the resulting materialized gate state.

Strict fail-closed evaluation by
`PULSE_safe_pack_v0/tools/check_gates.py` closes the complete relation `Rτ`
into `Dτ`.

The primary CI terminal result carries and enforces that transition-authority
state.

---

## 6. Canonical reconstruction question

The primary technical-review question is:

> **For the specified transition `τ`, can `Rτ` be reconstructed completely from
> its exact carriers and bindings, and does the observed `Dτ` follow
> deterministically from that bound relation under the declared policy?**

A complete reconstruction establishes:

```text
the identity of τ;
the exact value and carrier of every Rτ component;
the named binding between those components;
the policy-derived required relation;
the verifier and replay state;
the final gate-state carrier;
the resulting Dτ state.
```

The review is complete when the observed `Dτ` can be reproduced from the
reconstructed `Rτ`.

---

## 7. Interpretation order

The canonical reading order is:

```text
specified transition τ
→ bound authority relation Rτ
→ terminal transition-authority state Dτ
→ current carrier and enforcement surface
```

The current implementation execution sequence is the operational traversal used
to produce, bind, verify, materialize, and close this relation.

The relational object is primary.

The execution order is its mechanical realization.

---

## 8. Interpretation anchor

The complete PULSEmech reading can be stated in one sentence:

> **PULSEmech materializes the `ALLOW` or `BLOCK` authority state of a specified
> release-state transition from the verified, policy-bound, reconstructable
> relation among exact current-run evidence, subject and run identity, artifact
> and carrier identity, workflow-effective materialized requirements, verifier
> and replay state, and final gate state.**

Compact form:

```text
object:
τ

bound relation:
Rτ = ⟨S, E, A, P, G, V, F, Dτ⟩

terminal state:
Dτ ∈ {ALLOW, BLOCK}

current carrier:
primary CI terminal result

review operation:
reconstruct Rτ and reproduce Dτ
```

---

## 9. Scope and effect

This interpretation anchor preserves the existing PULSEmech implementation and
authority semantics.

It does not create a new decision type, gate, policy set, carrier, workflow,
authority path, or release effect.

Its repository effect is limited to making the existing relational
release-authority object explicit and directly reconstructable for external
technical analysis.
