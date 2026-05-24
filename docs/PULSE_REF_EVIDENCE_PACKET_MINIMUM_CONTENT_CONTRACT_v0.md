# PULSE-REF Evidence Packet Minimum Content Contract v0

Status: planning contract  
Authority status: non-normative  
Scope: future PULSE-REF evidence packet content requirements  
Release-grade status: not release-grade evidence  
Verifier status: not a verifier  
Decision status: does not authorize, block, override, or create release authority

## Purpose

This document defines the minimum content expectations for a future PULSE-REF evidence packet.

It follows the already materialized evidence packet layout skeleton.

The layout skeleton proves that the canonical packet paths can physically exist.

This document defines what those paths must eventually contain before a future packet can be considered content-prepared for release-grade reference evaluation.

This document does not make any packet release-grade.

This document does not validate a packet.

This document does not run RA1.

This document does not create release authority.

## Core boundary

A PULSE-REF evidence packet is not merely a run.

A PULSE-REF evidence packet is a closed, digest-backed, reconstructable evidence field.

The normative PULSE release decision remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

This document only describes the minimum content that a future evidence packet must carry so that the normative path can be reconstructed and checked.

## Relation to the layout skeleton

The layout skeleton establishes canonical packet paths.

The minimum content contract establishes what must be present in those paths once the packet moves beyond placeholder status.

The distinction is:

```text
layout skeleton
= path shape exists

minimum content contract
= required content classes are identified

release-grade evidence packet
= content is real, digest-backed, schema/contract-valid, reconstructable, and verifier-checked

release authority
= only the declared-policy gate-enforcement CI outcome
```

## Minimum packet identity content

A packet must include stable identity attributes (for example packet id, scope id, creation timestamp, and version marker) sufficient to correlate all artifacts to one evidence packet instance.

## Minimum run identity content

A future packet must bind the packet to a specific run identity.

Minimum run identity content:

- CI provider or execution environment;
- run ID;
- run number or equivalent;
- run attempt;
- workflow name;
- workflow ref or path;
- commit SHA;
- event type or trigger class;
- run URL or archived run reference, when available.

Run identity is not release authority.

Run identity supports reconstruction.

## Minimum status artifact content

`status.json` must include explicit outcome states, decision context pointers, and integrity references required to evaluate whether the packet can be considered complete for release evaluation.

## Minimum materialized gate-set content

The packet must enumerate the materialized required gate set and each gate's evaluated outcome so policy conformance can be reconstructed without inference.

## Minimum CI outcome content

The packet must carry the CI outcome record proving strict fail-closed CI gate enforcement and preserving the declared-policy allow/block release decision.

## Minimum negative conditions

A packet is not valid for release-grade use when required identity, status, gate-set, or CI outcome evidence is missing, placeholder-only, unverifiable, or contradictory.

## This document does not change:

- The authoritative release policy source.
- The requirement that gate outcomes be policy-declared and fail-closed.
- The rule that release authority is created only by the declared-policy gate-enforcement CI outcome.
- Existing verifier responsibilities and separation of duties.
