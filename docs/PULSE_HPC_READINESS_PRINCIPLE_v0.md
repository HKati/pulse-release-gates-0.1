# PULSE HPC Readiness Principle v0

Status: workshop principle  
Scope: HPC / compute-scale validation / release-grade evidence production  
Authority status: non-normative explanatory document

## Core statement

PULSE must be ready for HPC-scale evidence production.

HPC does not create release authority.

HPC produces evidence.

PULSE converts materialized, recorded, verified evidence into release decisions only through the declared normative path:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI checking  
→ CI allow/block release decision

## Why this matters

PULSE is being prepared for release-grade validation beyond small local or repository-only runs.

HPC-scale runs may produce larger detector outputs, repeated evaluation traces, stability measurements, PULSE-PD artifacts, external summaries, provenance records, package manifests, and audit bundles.

These artifacts may support release-grade validation.

They do not become release authority by existing.

The release decision remains bound to materialized evidence, declared policy, required gate evaluation, and CI-recorded outcome.

## HPC evidence principle

HPC output is evidence only when it is:

- explicit;
- recorded;
- reproducible or reconstructable;
- bound to input manifests;
- bound to run identity;
- bound to code identity;
- bound to environment identity where relevant;
- schema-valid where a schema exists;
- digestable and packageable where used as release-reference evidence;
- folded into `status.json` only through declared evidence contracts;
- enforced only through declared policy and materialized required gates.

Unrecorded compute output is not release evidence.

Unverified compute output is not release evidence.

Unfolded compute output is not release authority.

## Authority boundary

HPC systems, clusters, notebooks, dashboards, logs, job schedulers, and analysis reports do not authorize release.

They may produce or preserve evidence.

They may support diagnostics.

They may support review.

They may support reproducibility.

They may support release-reference package construction.

They must not authorize, block, override, or create a second release-decision path.

## Runtime separation

PULSE keeps runtime surfaces separated by role.

### Core release-authority runtime

The minimal core runtime supports the deterministic release-authority path.

It must remain small, explicit, and reproducible.

### Optional analysis runtime

The optional analysis runtime supports PULSE-PD, field diagnostics, plotting, toy generators, and related non-normative analysis surfaces.

Analysis dependencies must remain explicit and separate from the minimal core runtime.

### HPC / compute-scale runtime

The HPC runtime may include additional compute, detector, model, accelerator, scheduler, storage, and provenance dependencies.

Those dependencies must be declared in their own runtime surface before they are treated as reproducible evidence infrastructure.

HPC dependencies must not silently drift into the core release-authority runtime.

## Required HPC evidence fields

Any future HPC evidence bundle should preserve at least:

- run identifier;
- code revision;
- input manifest;
- dataset or sample identity;
- seed / deterministic configuration where applicable;
- environment identity;
- hardware or accelerator class where relevant;
- detector configuration;
- thresholds or policy references;
- output artifact paths;
- artifact digests;
- summary metrics;
- failure / missing-evidence status;
- provenance notes;
- reconstruction instructions.

The exact schema may evolve, but the principle does not change:

HPC output must be materialized before it can support release-grade validation.

## Relation to PULSE-PD

PULSE-PD is an optional analysis surface.

It can support field analysis, decision-field diagnostics, event export, and future HPC-scale evidence exploration.

It does not create release authority.

PULSE-PD artifacts become release-relevant only if explicitly folded into recorded release evidence and enforced as required gates under declared policy.

## Relation to recognition-surface drift

HPC results can also create recognition surfaces.

Large compute runs, charts, plots, summaries, institutional context, and polished reports may change how a reviewer or model interprets the system.

Those recognition surfaces are not authority.

Every recognition claim requires mechanical evidence.

## Relation to pre-materialization mechanics

PULSE pre-materialization mechanics prevents unsupported authority from materializing.

For HPC readiness, this means:

unsupported compute output  
→ no release authority

unrecorded HPC result  
→ no release authority

unverified HPC artifact  
→ no release authority

unfolded analysis output  
→ no release authority

Only materialized, policy-routed, gate-enforced evidence can participate in release authority.

## Development rule

When adding HPC-related functionality, classify the component before describing its value.

Ask:

1. Does it produce evidence?
2. Does it record evidence?
3. Does it verify evidence?
4. Does it fold evidence into `status.json`?
5. Does declared policy enforce it as a required gate?
6. Is it diagnostic only?
7. Is it a recognition surface?
8. Is it an audit / reconstruction surface?
9. Is it part of optional analysis runtime?
10. Is it part of core release-authority runtime?

If the answer is unclear, the component is non-normative until explicitly routed through declared policy and enforced as a required gate.

## Summary

PULSE must be able to run at HPC scale.

HPC produces evidence.

PULSE decides only through the normative evidence-policy-gate-CI path.

Compute scale does not create authority.

Materialized, verified, policy-routed evidence can support authority.

Unsupported compute state cannot.
