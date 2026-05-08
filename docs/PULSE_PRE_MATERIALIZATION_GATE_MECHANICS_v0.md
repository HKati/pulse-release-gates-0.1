# PULSE Pre-Materialization Gate Mechanics v0

Status: conceptual foundation  
Scope: PULSE core mechanics / non-normative explanatory layer

## Core statement

PULSE is pre-materialization gate mechanics for release authority.

It does not primarily correct harmful or unsupported outcomes after they have already become authoritative.

It identifies process states from which an invalid, unsafe, unsupported, or insufficiently evidenced release decision could materialize, and applies declared gates before that unsupported closure is allowed to become release authority.

In this document, "pre-materialization" refers to preventing unsupported authority from materializing. It does not mean preventing evidence from being materialized. PULSE requires evidence to be materialized before it can contribute to release-grade validation.

## Classical recovery pattern

Many recovery-based control systems follow this pattern:

```text
process executes
-> failure materializes
-> failure is detected
-> correction or mitigation is attempted
```

This is a post-materialization model.

It depends on the harmful, invalid, or unsupported state becoming observable after execution or after acceptance.

Such systems may still be useful, but they are not the core PULSE release-authority model.

## PULSE pattern

PULSE follows a pre-materialization pattern:

```text
potential release state appears
-> evidence boundary is checked
-> declared policy is applied
-> required gates are evaluated
-> supported closure is allowed / unsupported closure is blocked
```

The release decision is not produced from intention, narrative, dashboard state, diagnostic interpretation, publication surface, review summary, or informal confidence.

The release decision is produced by declared-policy gate enforcement over materialized status evidence and recorded through the CI outcome.

## Unsupported closure

An unsupported closure is a process state that would become authoritative, releasable, trusted, or operationally accepted without sufficient declared evidence.

Examples include:

- release PASS inferred from missing evidence;
- detector evidence treated as present when it is not materialized;
- refusal-delta success treated as release-sufficient when refusal-delta evidence is absent;
- unsigned, malformed, stale, or unverified external evidence accepted as release-grade;
- advisory signals treated as required release authority without policy promotion;
- diagnostic artifacts treated as normative release authority;
- manifests, ledgers, dashboards, publication surfaces, or summaries mistaken for release decisions;
- agent-generated diagnostic work promoted into authority without declared policy routing.

PULSE gates are positioned to prevent these unsupported closures from becoming release decisions.

## Harmful closure

A harmful closure is an unsupported closure whose acceptance could cause operational harm, safety degradation, audit failure, or false confidence.

PULSE does not need to predict every possible downstream harm.

It blocks the upstream authority error: unsupported evidence must not become release permission.

## Gate position

A PULSE gate is positioned before unsupported closure becomes authoritative.

The gate does not merely describe the failure after it occurs.

It prevents unsupported authority from materializing.

The general mechanical form is:

```text
potential process state
-> required evidence boundary
-> declared gate evaluation
-> allow supported closure / block unsupported closure
```

## Relation to fail-closed behavior

Fail-closed behavior is the operational expression of pre-materialization gate mechanics.

If required evidence is missing, malformed, unsigned, unverified, stale, stubbed, non-materialized, or otherwise unusable, the release path does not infer PASS.

The unsupported closure is blocked.

This is why release-grade PULSE paths must not convert absence, ambiguity, diagnostics, dashboards, summaries, or advisory artifacts into release authority.

## Relation to evidence materialization

PULSE distinguishes between two different uses of "materialization":

```text
evidence materialization:
  required evidence becomes explicit, recorded, inspectable, and usable in status.json

unsupported authority materialization:
  an unsupported state becomes accepted as a release decision
```

PULSE requires the first and blocks the second.

Evidence should materialize.

Unsupported release authority should not.

## Relation to no-implicit-PASS behavior

The no-implicit-PASS rule is a direct instance of pre-materialization gate mechanics.

A missing evidence artifact must not silently become a passing gate.

For example:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
-> release-grade FAIL
```

The system blocks the unsupported closure before the apparent PASS can become release authority.

## Relation to external evidence

External summaries, detector outputs, envelopes, signer identities, and verification metadata may contribute to release-grade validation only when routed through declared evidence contracts and policy-controlled gates.

Malformed, unsigned, stale, unverified, or non-authoritative external evidence must not become release permission.

Verification-before-fold-in is therefore a pre-materialization control: unverified evidence cannot be folded into release authority.

## Relation to manifests, ledgers, dashboards, and audit bundles

Pre-materialization gate mechanics does not create a second release-decision path.

The normative release decision remains produced by:

```text
status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

Ledgers, manifests, audit bundles, dashboards, summaries, publication surfaces, fixtures, and explanatory documents remain non-normative.

They may preserve, explain, reconstruct, publish, or audit a release decision.

They do not authorize, block, override, or create release authority unless their outputs are explicitly routed through the declared policy-controlled path.

## Relation to agent-generated work

Agent-generated plans, tool traces, code changes, review notes, diagnostics, and self-checks may be useful evidence for review or debugging.

They do not become release authority by existing.

A PULSE release decision must remain bound to materialized evidence, declared policy, required gate evaluation, and CI-recorded outcome.

This preserves the boundary between diagnostic work and release authority.

## General mechanical form

The general PULSE form is:

```text
potential process state
-> evidence requirement
-> declared policy
-> required gate set
-> strict gate evaluation
-> supported closure / blocked closure
```

PULSE does not need to know every possible future failure.

It needs to prevent unsupported states from becoming authoritative without declared evidence.

## Summary

PULSE is pre-materialization gate mechanics for release authority.

It acts before unsupported closure becomes a release decision.

Its purpose is not to repair trust after failure, but to prevent unsupported authority from materializing.

The core rule is:

```text
unsupported evidence state
-> no release authority
```

The operational expression is:

```text
missing / malformed / unsigned / unverified / stale / stubbed / non-materialized required evidence
-> fail closed
```
