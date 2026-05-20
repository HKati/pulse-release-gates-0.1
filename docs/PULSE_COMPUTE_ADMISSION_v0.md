# PULSE-COMPUTE Admission v0

Status: research note / shadow-only direction  
Normative status: non-normative  
Primary role: preserve a future development thread for compute-admission mechanics

## Purpose

This document preserves a PULSE development thread around pre-compute admission.

The idea is not to replace PULSE release authority, and not to redefine the current PULSEmech release-decision path. The purpose is to record a possible future extension: using PULSE-style evidence, policy, gate materialization, and fail-closed logic before high-cost AI execution is allowed to consume compute.

The core question is:

When is a request, candidate state, or execution plan justified to consume high-cost AI compute under declared policy?

## Current PULSE identity remains unchanged

PULSE remains an artifact-first release-governance / release-authority system for AI applications.

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

In this workshop, no development direction is treated as permanently fixed. A statement, structure, or mechanism is valid only until a better, more precise, more mechanically sound version replaces it.

The purpose of this document is therefore not to close the idea, but to preserve it without forcing it prematurely into the normative release-authority core.

## Motivation

Scaling AI capability only by adding more GPUs is a limited strategy.

More compute can help, but linear accumulation of compute does not automatically equal better development. At some point, the system must learn when high-cost compute is actually necessary, justified, and sufficient.

The relevant mechanical shift is:

from:
more requests → more model runs → more GPU use

to:
request state → evidence state → declared policy → required compute gates → model / review / execution path

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

A model router typically optimizes cost, latency, or model selection.

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

## DEGRADED is never authorizing

`DEGRADED` must not be a decision verdict.

In ordinary systems, degraded can mean “still running in reduced mode.” That meaning is unsafe for PULSE-style authority mechanics.

For PULSE-COMPUTE, `DEGRADED` means that the artifact, input state, evidence state, validation path, or execution context is impaired, incomplete, inconsistent, or partially unavailable.

`DEGRADED` is diagnostic-only and never authorizes high-cost compute.

The state:

verdict: ALLOW
diagnostic_state: DEGRADED

should be treated as invalid or fail-closed.

## ROUTE is not a bypass

`ROUTE` must not become a hidden authorization path.

`ROUTE` means that the requested execution is not authorized as requested and must be redirected to a declared lower-cost, narrower, safer, or review-bound execution path.

A routed execution path must still be policy-declared.

## Relationship to PULSEmech

PULSE-COMPUTE is a possible extension of PULSEmech logic from release authorization to compute admission.

Release authority asks:

Is this candidate release authorized under recorded evidence, declared policy, materialized gates, and fail-closed CI checking?

Compute admission asks:

Is this candidate execution authorized to consume this level of compute under recorded evidence, declared compute policy, materialized compute gates, and fail-closed checking?

The mechanics are related, but the authority surfaces must remain separate unless a future policy explicitly connects them.

## Non-normative boundary

This document does not define release authority.

It does not change `status.json`.

It does not change `check_gates.py`.

It does not change CI release decisions.

It does not add a new normative gate.

It preserves a development direction for future implementation.

## Future implementation sketch

A future implementation may add:

- `schemas/compute_admission_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_compute_admission_v0_contract.py`
- `tests/fixtures/compute_admission_v0/`
- `tests/test_check_compute_admission_v0_contract.py`
- optional shadow registry entry with `normative: false`

The first implementation should remain shadow-only unless explicitly promoted by declared policy.

## Working sentence

PULSE-COMPUTE extends PULSEmech from release authorization toward compute admission: before high-cost AI execution, it can determine the required evidence, model capacity, review depth, and execution path under declared policy, then allow, block, escalate, or route fail-closed.

## Short Hungarian summary

A PULSE-COMPUTE nem a GPU-k kiváltása.

A PULSE-COMPUTE célja annak vizsgálata, hogy a nagy költségű AI-futtatás előtt megállapítható-e: milyen bizonyíték, modellkapacitás, ellenőrzési mélység és futtatási út indokolt.

A lényeg:

nem minden kéréshez teljes gép kell,
hanem jogosult, elégséges és policy által engedett számítási út.

Ez a dokumentum csak rögzíti az irányt, hogy később vissza lehessen térni rá.
