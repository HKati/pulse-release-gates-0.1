# PULSE-COMPUTE Admission v0

Status: research note / shadow-only direction  
Normative status: non-normative  
Primary role: preserve a future development thread for compute-admission mechanics

## Purpose

This document preserves a PULSE development thread around pre-compute admission.

The idea is not to replace PULSE release authority, and not to redefine the current PULSEmech release-decision path.

The purpose is to record a possible future direction: using PULSE-style evidence, declared policy, gate materialization, and fail-closed logic before high-cost AI execution is allowed to consume compute.

The core question is:

When is a request, candidate state, or execution plan justified to consume high-cost AI compute under declared policy?

## Current PULSE identity remains unchanged

PULSE remains artifact-bound release authority for AI release decisions.

AI release decisions are made from recorded evidence, declared policy, materialized required gate set, and fail-closed CI enforcement.

PULSEmech converts recorded release evidence into deterministic, fail-closed CI allow/block release decisions before deployment under declared policy.

The current PULSEmech decision path remains:

(recorded release evidence,  
 status.json,  
 declared gate policy,  
 materialized required gate set,  
 strict fail-closed CI checking)  
→ CI allow/block release decision

PULSE-COMPUTE does not change this release-authority identity.

## Development principle

This note is not a final mechanism.

It preserves an open development direction. No research direction, phrase, structure, or mechanism in this note is treated as permanently fixed.

A mechanism remains useful only while it is the most mechanically precise available version. If a better version appears, the better version should replace it.

The purpose of this document is therefore not to close the idea, but to preserve it without forcing it prematurely into the normative release-authority core.

## Motivation

Scaling AI capability only by adding more GPUs is a limited strategy.

More compute can help, but linear accumulation of compute does not automatically equal better development. At some point, the system must learn when high-cost compute is actually necessary, justified, and sufficient.

The relevant mechanical shift is:

from:

more requests  
→ more model runs  
→ more GPU use

to:

request state  
→ evidence state  
→ declared policy  
→ required compute gates  
→ model / review / execution path

The goal is not to replace GPUs.

The goal is to avoid consuming high-cost compute when the request state, evidence state, risk level, or policy state does not justify it.

## Proposed direction

PULSE-COMPUTE may become a pre-compute admission layer.

It would determine, before high-cost AI execution:

- what evidence is required,
- what model capacity is justified,
- what review depth is required,
- what execution path is allowed,
- whether the request should be allowed, blocked, escalated, or routed.

A possible future decision path:

request / candidate state  
→ evidence state  
→ declared compute policy  
→ materialized compute gate set  
→ required model capacity / review depth / execution path  
→ allow / block / escalate / route

## Not a compute router

PULSE-COMPUTE should not be reduced to ordinary model routing.

A model router typically optimizes cost, latency, model choice, or throughput.

PULSE-COMPUTE would instead ask a release-authority-style question before compute is consumed:

Is this request state authorized to consume this level of compute under declared policy and recorded evidence?

This distinction matters.

Routing can be a result of the mechanism, but routing is not the mechanism itself.

## Candidate verdict semantics

A future compute-admission artifact should keep decision verdicts separate from diagnostic states.

Candidate decision verdicts:

- `ALLOW`
- `BLOCK`
- `ESCALATE`
- `ROUTE`

Candidate diagnostic states:

- `OK`
- `DEGRADED`
- `INVALID_INPUT`
- `INCOMPLETE_EVIDENCE`

Diagnostic states are non-authorizing.

High-cost compute may be authorized only when:

- the decision verdict is `ALLOW`,
- the diagnostic state is `OK`,
- all required compute gates are literal boolean `true`,
- the declared compute policy permits the selected execution path.

Any future implementation should treat non-literal truth values as non-PASS.

For required compute gates, only literal boolean `true` should count as PASS. Missing, false, null, string, number, inferred, fallback, or unknown values must not authorize high-cost compute.

## DEGRADED is never authorizing

`DEGRADED` must not be a decision verdict.

In ordinary systems, degraded can mean “still running in reduced mode.” That meaning is unsafe for PULSE-style authority mechanics.

For PULSE-COMPUTE, `DEGRADED` means that the artifact, input state, evidence state, validation path, or execution context is impaired, incomplete, inconsistent, or partially unavailable.

`DEGRADED` is diagnostic-only and never authorizes high-cost compute.

The state:

- `verdict: ALLOW`
- `diagnostic_state: DEGRADED`

should be treated as invalid or fail-closed.

A degraded artifact may help explain why a decision cannot be authorized, but it must not become an authorization path.

## ROUTE is not a bypass

`ROUTE` must not become a hidden authorization path.

`ROUTE` means that the requested execution is not authorized as requested and must be redirected to a declared lower-cost, narrower, safer, or review-bound execution path.

A routed execution path must still be policy-declared.

Routing must not silently convert missing evidence, degraded state, or insufficient review into authorization.

The original high-cost execution remains unauthorized unless a declared policy, required compute gate set, and valid artifact state explicitly authorize it.

## ESCALATE is not ALLOW

`ESCALATE` means the current artifact state is insufficient for an allow decision and requires deeper review, stronger evidence, higher-capacity evaluation, human review, or another declared escalation path.

`ESCALATE` does not authorize the requested high-cost execution.

A future implementation should make the escalation target explicit.

Examples:

- escalate to human review,
- escalate to stronger evidence collection,
- escalate to a higher-assurance validation path,
- escalate to a more capable model for evaluation only,
- escalate to block if required evidence cannot be produced.

## Relationship to PULSEmech

PULSE-COMPUTE is a possible extension of PULSEmech-style mechanics from release authorization toward compute admission.

Release authority asks:

Is this candidate release authorized under recorded evidence, declared policy, materialized required gates, and fail-closed CI checking?

Compute admission asks:

Is this candidate execution authorized to consume this level of compute under recorded evidence, declared compute policy, materialized compute gates, and fail-closed checking?

The mechanics are related, but the authority surfaces must remain separate unless a future declared policy explicitly connects them.

## Non-normative boundary

This document does not define release authority.

It does not change `status.json`.

It does not change declared gate policy.

It does not change materialized required gate sets.

It does not change `check_gates.py`.

It does not change CI release decisions.

It does not add a new normative gate.

It does not create a new release-authority surface.

It preserves a development direction for future implementation.

This document is a preservation note, not an implementation contract.

Any future implementation must introduce its own schema, checker, fixture matrix, and explicit non-interference proof before it can be treated as a contracted shadow surface.

A future implementation should test at least the following cases:

- low-risk request allowed on a lower-cost path,
- cached or small-model route under declared policy,
- uncertain high-value request escalated rather than allowed,
- missing required evidence blocked,
- high-cost execution blocked without required review depth,
- degraded artifact state treated as non-authorizing,
- `ALLOW` with `diagnostic_state: DEGRADED` treated as invalid or fail-closed,
- non-literal truth values rejected for required compute gates.

## Working sentence

PULSE-COMPUTE preserves a possible extension of PULSEmech from release authorization toward compute admission: before high-cost AI execution, it can determine the required evidence, model capacity, review depth, and execution path under declared policy, then allow, block, escalate, or route fail-closed.

## Short summary

PULSE-COMPUTE does not replace GPUs.

PULSE-COMPUTE preserves a possible future shadow-only direction for determining, before high-cost AI execution, what evidence, model capacity, review depth, and execution path are justified under declared policy.

The core principle is:

not every request requires full-machine execution; compute should follow an authorized, sufficient, and policy-declared execution path.

`DEGRADED` is not an authorizing verdict. It is a diagnostic state only.

`ROUTE` is not a bypass. It is a declared alternative execution path.

`ESCALATE` is not authorization. It means the current state is insufficient for an allow decision and requires deeper review, stronger evidence, higher-assurance validation, human review, or another declared escalation path.

This document preserves the direction for future work without changing the current PULSE release-authority core.
