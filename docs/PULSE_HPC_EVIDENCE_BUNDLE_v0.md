# PULSE HPC Evidence Bundle v0

Status: diagnostic evidence contract  
Scope: HPC / compute-scale evidence production  
Authority status: non-normative evidence surface

## Core statement

HPC produces evidence.

HPC does not create release authority.

PULSE release authority materializes only through the declared normative path:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ CI allow/block release decision

## Purpose

`hpc_evidence_bundle_v0` defines a machine-readable contract for recording HPC or compute-scale evidence before that evidence can support release-grade validation.

The bundle records:

- run identity;
- code identity;
- input manifest identity;
- environment identity;
- evidence artifacts;
- summary metrics;
- provenance;
- reconstruction instructions;
- completion status.

The bundle is non-normative by default.

It may support review, diagnostics, reproducibility, or later fold-in work.

It does not authorize, block, override, or create release authority.

## Core rule

Unsupported compute output must not become release authority.

Unrecorded HPC output is not release evidence.

Unverified HPC output is not release evidence.

Unfolded HPC output is not release authority.

Only materialized, policy-routed, gate-enforced evidence can participate in release authority.

## Contract states

The bundle result may be:

- `complete` — declared evidence items are present and digest-backed;
- `incomplete` — one or more evidence items are missing, failed, or unverified;
- `invalid` — the bundle exists but should not be treated as usable diagnostic evidence without repair.

A `complete` bundle is still non-normative.

It means the bundle is internally complete as a diagnostic evidence surface.

It does not mean release is allowed.

## Evidence items

Each evidence item records:

- artifact path;
- evidence role;
- evidence status;
- SHA-256 digest when present;
- whether it has been folded into `status.json`;
- optional policy route if it is folded.

If an evidence item is folded into `status.json`, it must have a declared policy route.

Folded evidence without a policy route is invalid.

## Relation to PULSE-PD

PULSE-PD may produce analysis artifacts that later become part of an HPC evidence bundle.

PULSE-PD remains an optional analysis surface.

Its artifacts do not create release authority unless explicitly folded into recorded release evidence and enforced as required gates under declared policy.

## Relation to recognition surfaces

Large compute runs, polished plots, institutional context, dashboards, and reports may create recognition surfaces.

Recognition surfaces are not authority.

Every recognition claim requires mechanical evidence.

## Summary

HPC output becomes useful to PULSE only when it is materialized, recorded, digest-backed, reconstructable, and role-classified.

HPC produces evidence.

PULSE decides only through the normative evidence-policy-gate-CI path.
