# PULSE Evidence Fold-In Admissibility v0

Status: diagnostic admissibility contract  
Scope: diagnostic / HPC / PULSE-PD / recognition / external evidence fold-in boundary  
Authority status: non-normative evidence-admissibility surface

## Core statement

A diagnostic surface may observe the field.

Only policy-routed, schema-valid, digest-backed, verified, materialized evidence may enter the recorded release-evidence path.

This document defines the boundary between:

- non-normative diagnostic evidence;
- advisory evidence;
- evidence that is admissible for future fold-in into `status.json`;
- evidence that must remain rejected.

This contract does not fold evidence into `status.json`.

It only records whether a candidate evidence item is admissible for fold-in.

## Normative release path

The normative PULSE release decision remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ CI allow/block release decision

The fold-in admissibility contract does not authorize, block, override, or create release authority.

## Why this exists

PULSE contains role-bearing field points:

- external detector summaries;
- HPC evidence bundles;
- PULSE-PD analysis artifacts;
- recognition-surface drift diagnostics;
- RA1 verifier reports;
- audit bundles;
- publication snapshots;
- diagnostic overlays.

These surfaces may be useful.

They are not release authority by existing.

Before any diagnostic or analysis artifact can become recorded release evidence, it must pass an admissibility boundary.

## Core rule

Unsupported fold-in state  
→ no recorded release evidence

Fold-in requires:

- source artifact path;
- SHA-256 digest;
- source surface role;
- source authority status;
- schema-valid evidence where a schema exists;
- explicit verification status;
- explicit policy route if fold-in is requested;
- explicit target gate if policy-routed;
- explicit non-authority status for the admissibility artifact itself.

## Recognition surfaces

Recognition surfaces are not authority.

A recognition surface may orient attention.

It must not become recorded release evidence by itself.

Examples of recognition surfaces include:

- title;
- summary;
- About text;
- badge;
- DOI metadata;
- citation metadata;
- social preview;
- visual presentation;
- dashboard appearance.

Every recognition claim requires mechanical evidence.

Recognition-surface diagnostics may be recorded as diagnostic artifacts, but a recognition surface itself is not admissible for release-evidence fold-in unless a separate mechanical evidence artifact is provided and policy-routed.

## HPC evidence

HPC output is evidence only when it is materialized, recorded, digest-backed, reconstructable, and role-classified.

An `hpc_evidence_bundle_v0` artifact may become a candidate evidence source.

It is admissible for fold-in only if the specific candidate evidence item has a valid digest, verified status, schema-valid supporting contract, and explicit policy route.

HPC output does not create release authority.

## PULSE-PD evidence

PULSE-PD is an optional analysis surface.

PULSE-PD artifacts may support field diagnostics or evidence exploration.

They do not create release authority.

A PULSE-PD artifact is admissible for fold-in only when it is digest-backed, schema-valid or contract-checked where applicable, verified, and explicitly routed to declared policy.

## External detector evidence

External detector summaries may become release-relevant only through declared evidence contracts.

A detector summary is not admissible merely because it exists.

It must be canonical, schema-valid where applicable, digest-backed, verified, and policy-routed before it can support a required gate.

## Result states

An admissibility artifact may report:

- `admissible` — all candidates are admissible for fold-in;
- `advisory_only` — candidates may support review or diagnosis but are not admissible for fold-in;
- `rejected` — one or more candidates violate admissibility rules;
- `mixed` — at least one candidate is admissible and at least one candidate is advisory-only or rejected.

A result of `admissible` does not mean release is allowed.

It only means the candidate evidence is allowed to enter a future recorded-evidence fold-in process.

## Invariant

Non-normative field points must not enter recorded release evidence without mechanical admissibility.

Admissibility requires mechanical proof.

Every fold-in claim requires mechanical evidence.

Mechanism first; fold-in second; authority only through declared policy.
