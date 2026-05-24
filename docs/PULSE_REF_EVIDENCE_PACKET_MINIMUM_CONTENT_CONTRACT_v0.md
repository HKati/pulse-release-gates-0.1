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

## Minimum policy and registry content

A future packet must include the declared gate policy and gate registry used for the packet run.

Minimum policy and registry content:

- policy artifact path;
- policy artifact SHA-256 digest;
- policy identifier or version, when available;
- selected policy set;
- gate registry artifact path;
- gate registry artifact SHA-256 digest;
- registry identifier or version, when available;
- evidence that required gates are registry-backed.

Policy and registry content is reconstruction context and policy provenance.

It does not create release authority by document presence.

## Minimum materialized gate-set content

A future packet must include the materialized required gate set used for CI gate enforcement.

Minimum materialized gate-set content:

- materialized gate-set artifact path;
- materialized gate-set SHA-256 digest;
- policy source path;
- policy source SHA-256 digest;
- required gate set;
- release-required gate set, when applicable;
- effective required gate set;
- ordering rule for effective gates;
- duplicate-gate handling rule.

The materialized required gate set is required because release authority depends on the concrete gate set enforced by CI.

## Minimum CI outcome content

A future packet must include the CI outcome that records the declared-policy gate-enforcement result.

Minimum CI outcome content:

- CI provider;
- workflow name;
- workflow path or workflow ref;
- run ID;
- run attempt;
- commit SHA;
- event type;
- gate-check command or recorded command reference;
- gate-check conclusion;
- run URL or archived run reference;
- CI outcome artifact path;
- CI outcome artifact SHA-256 digest.

The CI outcome records the declared-policy allow/block result.

CI outcome content does not replace status, policy, materialized gates, or strict gate checking.

## Minimum release-authority manifest content

A future packet must include a release-authority manifest as an audit and trace artifact.

Minimum release-authority manifest content:

- manifest artifact path;
- manifest SHA-256 digest;
- run identity;
- status artifact reference;
- policy artifact reference;
- registry artifact reference;
- materialized gate-set reference;
- effective required gates;
- required gate evaluation summary;
- declared decision state;
- fail-closed indicator;
- authority-boundary statement;
- shadow and diagnostic non-normative statement.

The release-authority manifest records and reconstructs the decision path.

It is not a second decision engine.

## Minimum audit bundle content

A future packet must include or reference an audit bundle that preserves the evidence trail.

Minimum audit bundle content:

- audit bundle path or archive reference;
- audit bundle SHA-256 digest;
- included artifact inventory;
- status artifact reference;
- release-authority manifest reference;
- report card or reader-surface reference, when present;
- CI outcome reference;
- package digest reference;
- reconstruction instruction reference.

The audit bundle preserves evidence and supports reconstruction.

It does not authorize, block, override, or create release authority.

## Minimum package digest content

A future packet must include a digest manifest for package payload artifacts.

Minimum package digest content:

- digest manifest path;
- digest manifest SHA-256 digest;
- package ID;
- run key;
- artifact path list;
- artifact SHA-256 digest map;
- payload inventory;
- missing-artifact handling rule;
- unexpected-artifact handling rule.

Package digest content binds the packet payload to a reconstructable artifact set.

## Minimum operator handoff content

A future packet must include operator handoff content for reconstructing the packet decision path.

Minimum operator handoff content:

- handoff artifact path;
- handoff artifact SHA-256 digest;
- gate mode;
- status source;
- generated or existing status path;
- status digest before and after handoff, when applicable;
- materialized gate sets;
- effective required gates;
- command list or command references;
- tool paths and tool digests, when available;
- authority-boundary statement.

Operator handoff content supports human and machine reconstruction.

It does not create release authority.

## Minimum publication snapshot content

A future packet must include publication snapshot content when public surfaces are part of the packet.

Minimum publication snapshot content:

- publication snapshot artifact path;
- publication snapshot SHA-256 digest;
- package ID;
- run key;
- git SHA;
- publication URL or archived reference, when available;
- CI outcome URL or archived reference;
- publication timestamp, when available;
- listed public surfaces;
- authority-boundary statement.

Publication surfaces are reader or recognition surfaces.

They do not create a second release-decision path.

## Minimum reconstruction instructions

A future packet must include reconstruction instructions.

Minimum reconstruction instructions:

- packet root;
- expected canonical paths;
- command sequence for verifier or future checker use;
- status artifact location;
- policy and registry artifact locations;
- materialized gate-set artifact location;
- CI outcome artifact location;
- digest verification step;
- authority-boundary reminder;
- expected fail-closed behavior when required artifacts are missing.

Reconstruction instructions make the packet inspectable.

They do not validate release-grade evidence by themselves.

## Optional external evidence content

A future packet may include external evidence content.

Optional external evidence content:

- external summary artifact paths;
- external summary digests;
- detector names;
- detector versions;
- schema references;
- signer or attestation references, when available;
- subject artifact digests;
- fold-in status;
- external summary verification status.

External evidence remains optional unless declared policy requires it.

When policy requires external evidence, missing or non-materialized external evidence must fail closed.

## Optional HPC evidence content

A future packet may include HPC evidence content.

Optional HPC evidence content:

- HPC evidence bundle path;
- HPC evidence bundle digest;
- compute environment reference;
- run identity;
- job identity;
- input artifact digests;
- output artifact digests;
- reproducibility notes;
- authority-role classification.

HPC evidence produces candidate evidence.

It does not create release authority by compute scale alone.

## Optional recognition-surface evidence content

A future packet may include recognition-surface evidence content.

Optional recognition-surface evidence content:

- README or front-door snapshot reference;
- repository About text snapshot reference, when available;
- release notes snapshot reference, when available;
- DOI or citation surface reference, when available;
- drift-audit reference;
- recognition-surface classification.

Recognition surfaces help external readers find and classify the work.

They do not authorize, block, override, or create release authority.

## Field-point authority classification

A future packet should classify included field points by authority role.

Field-point authority classification:

- normative materialization path;
- normative input;
- normative enforcement;
- audit or reconstruction surface;
- diagnostic surface;
- publication or reader surface;
- recognition surface;
- optional analysis surface;
- candidate evidence surface;
- non-normative surface.

Each field point must preserve its declared authority status unless explicitly promoted through declared policy and enforced as a required gate.

## Evidence fold-in admissibility content

A future packet may include evidence fold-in admissibility content.

Evidence fold-in admissibility content:

- candidate evidence ID;
- source surface type;
- source artifact path;
- source artifact digest;
- schema-valid status;
- digest-valid status;
- verification status;
- fold-in requested status;
- policy route, when fold-in is requested;
- gate ID, when fold-in is requested;
- admissibility result.

Admissibility is not release permission.

Admissibility only states whether candidate evidence can enter a future policy-routed fold-in path.

## Minimum negative conditions

A future content-bearing checker must reject packet states where required content is missing, contradictory, or authority-unsafe.

Minimum negative conditions:

- missing packet identity;
- missing run identity;
- missing status artifact;
- missing declared policy;
- missing gate registry;
- missing materialized required gate set;
- missing CI outcome;
- missing package digests;
- missing reconstruction instructions;
- status artifact not bound to run identity;
- materialized gate set not bound to policy;
- CI outcome not bound to the same commit or run;
- audit, publication, recognition, diagnostic, or handoff surfaces claiming release authority;
- advisory or diagnostic evidence treated as required evidence without declared policy routing;
- missing required evidence interpreted as PASS.

Negative conditions must fail closed.

## Minimum positive conditions

A future content-bearing checker may accept packet content only when the required packet evidence is complete, bound, digest-backed, and reconstructable.

Minimum positive conditions:

- packet identity is present;
- run identity is present;
- status artifact is present;
- declared policy is present;
- gate registry is present;
- materialized required gate set is present;
- CI outcome is present;
- release-authority manifest is present;
- audit bundle or audit references are present;
- package digests are present;
- reconstruction instructions are present;
- authority-boundary statements are present;
- all required artifacts are digest-backed;
- all required references are consistent.

Positive conditions are packet-completeness conditions.

They are not a release decision by themselves.

## Relation to future checkers

This minimum content contract is a planning bridge for future content-bearing checkers.

Relation to future checkers:

- it defines expected content anchors;
- it does not validate release-grade evidence;
- it does not run a package verifier;
- it does not enforce release policy;
- it does not replace future schema or verifier checks;
- it provides a stable checklist for future checker implementation.

Future checkers may convert these content requirements into structured validation rules.

## Relation to RA1 verifier

This minimum content contract is related to the RA1 verifier but does not replace it.

Relation to RA1 verifier:

- RA1 verifies a concrete release-reference package;
- this document defines minimum content expectations for future packet preparation;
- this document is not a verifier;
- this document does not run RA1;
- this document does not relax RA1;
- this document does not replace RA1;
- this document does not authorize release authority.

RA1 remains the stricter package-verification path for concrete release-reference packages.

## Scope exclusions

This document is a planning and content contract only.

It excludes:

- release policy changes;
- gate registry changes;
- `check_gates.py` behavior changes;
- status schema changes;
- workflow behavior changes;
- release gate changes;
- RA1 verifier changes;
- README front-door changes;
- Zenodo metadata changes;
- citation metadata changes;
- DOI record changes;
- GitHub release changes.

This document does not change:

- the normative PULSE release decision path;
- the authority status of Quality Ledger;
- the authority status of release-authority manifests;
- the authority status of audit bundles;
- the authority status of publication surfaces;
- the authority status of diagnostic surfaces;
- the authority status of recognition surfaces;
- the authority status of optional analysis surfaces;
- release semantics.

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
