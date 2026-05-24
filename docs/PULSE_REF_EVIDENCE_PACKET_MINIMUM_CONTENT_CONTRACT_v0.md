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
