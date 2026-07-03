# PULSEmech required checks and workflow authority map v0

## Status

Technical repository map.

This document describes how PULSEmech release-authority, required checks, workflow families, evidence artifacts, and reader surfaces relate to one another.

It does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, branch protection settings, platform required-check settings, or release-authority semantics.

It is a documentation map for maintainers, reviewers, and external technical readers.

## Purpose

PULSEmech contains several workflow families, test surfaces, evidence artifacts, documentation records, audit artifacts, and publication or reader surfaces.

These surfaces do not all carry the same authority.

This document defines the repository-level map between:

```text
primary release authority
core deterministic checks
release-grade evidence and reference support
guardrail / hygiene checks
advisory / diagnostic / shadow surfaces
reader / publication / maintenance surfaces
```

The purpose is to make the authority boundary visible before a reviewer interprets a workflow result, report, dashboard, document, sidecar, or artifact as a release decision.

## Core release-authority model

PULSEmech release authority is produced by the connected evidence and enforcement path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized gate set
→ verifier replay
→ check_gates.py
→ primary CI allow/block decision
```

No single reader surface, report, dashboard, metadata record, release note, audit bundle, sidecar, or documentation page independently creates release authority.

Release authority depends on the connected path.

## Authority categories

PULSEmech repository surfaces are grouped into six categories.

```text
A. Primary release-authority path
B. Core deterministic lane
C. Release-grade evidence and reference support
D. Guardrail / hygiene checks
E. Advisory / diagnostic / shadow surfaces
F. Reader / publication / maintenance surfaces
```

Each category has a different role.

## A. Primary release-authority path

The primary release-authority path is the normative allow/block path for release-transition decisions.

It is defined by the connection between:

```text
status.json
declared gate policy
workflow-effective materialized gate set
verifier replay
check_gates.py
primary CI outcome
```

The primary path answers:

```text
May this release transition proceed under the declared policy and recorded evidence?
```

The primary path is not replaced by documentation, reader surfaces, dashboards, external summaries, publication metadata, audit bundles, or trace sidecars.

### Primary components

```text
.github/workflows/pulse_ci.yml
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
PULSE_safe_pack_v0/tools/check_gates.py
status.json
workflow-effective materialized gate set
recorded evidence verifier output when connected to the release path
primary CI allow/block result
```

### Primary authority rule

```text
If required release evidence is missing, stale, unverifiable, policy-incomplete, or fails the workflow-effective required gates, the transition must remain blocked.
```

### Primary-path boundary

The primary release-authority path may use supporting artifacts.

Supporting artifacts help reconstruct, review, or audit the decision.

They do not replace:

```text
status.json
declared gate policy
workflow-effective materialized gate set
verifier replay
check_gates.py
primary CI allow/block result
```

## B. Core deterministic lane

The core lane verifies the deterministic base mechanism.

It is narrower than the full release-grade path.

The core lane may validate:

```text
core run mode
core required gates
baseline fixture consistency
schema contract
registry coherence
deterministic tool behavior
```

The core lane is important because it proves the base PULSEmech mechanism can run without relying on optional hosted external evidence.

### Core lane examples

```text
.github/workflows/pulse_core_ci.yml
tests/test_core_baseline_v0.py
core-required gate checks
baseline drift guards
registry sync checks
schema contract checks
```

### Core lane boundary

The core lane is not automatically the same as a completed full release-grade reference run.

A core pass proves the core mechanism.

A completed release-grade reference proof requires the release-grade evidence path, workflow-effective gate requirements, non-stubbed status, verifier replay, and qualification criteria applicable to that run.

## C. Release-grade evidence and reference support

The release-grade evidence path evaluates a stronger release context.

It may include:

```text
recorded release evidence
release evidence input manifest
recorded release evidence verifier report
workflow-effective materialized gate set
release-grade status validation
release decision artifact
artifact provenance binding artifact
audit / trace sidecar
audit / review bundle
reference package
operator handoff report
```

### Release-grade path components

```text
PULSE_safe_pack_v0/tools/build_release_evidence_input_manifest_v0.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/check_gates.py
```

### Implemented release-grade support artifacts

Concrete artifact names should be taken from the workflow, package manifest, verifier output, or reference package being reviewed.

Known implemented artifact names and paths include:

```text
status.json
status_baseline.json
required_gate_evidence_v0.json
release_evidence_input_manifest_v0.json
recorded_release_evidence_verifier_v0.json
release_decision_v0.json
artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

PULSE-REF package contexts may include:

```text
gates/materialized_gate_sets.json
```

The following artifact is an audit / trace sidecar:

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

It supports review and traceability.

It is not an independent release-authority engine.

### Release-grade boundary

A reference artifact, audit sidecar, or audit bundle supports review.

It does not replace the primary enforcement path.

A release-grade reference record should be read as evidence of a run and a reconstruction aid, not as a second release decision engine.

## D. Guardrail / hygiene checks

Guardrail and hygiene checks protect the repository from drift, malformed configuration, unsafe workflow changes, path mistakes, and documentation/contract inconsistency.

They are important for repository integrity.

They are not normally independent release-authority engines unless explicitly wired into the declared release path.

### Guardrail examples

```text
workflow YAML parsing
duplicate key detection
path reference checks
embedded workflow step checks
single run_all invocation guard
status schema validation
test manifest coherence checks
secret scanning
repository hygiene checks
DCO checks
workflow lint checks
attestation action pin checks
reader-surface non-interference checks
```

### Guardrail boundary

A guardrail failure may block CI.

A guardrail pass does not by itself authorize a release transition.

Guardrails protect the conditions around the release-authority path.

They are not a substitute for recorded evidence, declared policy, workflow-effective materialized gates, verifier replay, and check_gates enforcement.

## E. Advisory / diagnostic / shadow surfaces

Advisory, diagnostic, and shadow surfaces may produce useful analysis.

Examples include:

```text
shadow workflows
EPF experiments
recognition-surface drift reports
HPC evidence bundles
external scanner summaries
diagnostic detector reports
research-oriented paradox or topology outputs
```

These surfaces may inform later policy decisions.

They may also become evidence inputs if explicitly admitted by declared policy and verified through the appropriate evidence path.

### Advisory boundary

By default:

```text
advisory output
≠ release authority
```

Diagnostic evidence must not become normative release evidence unless the declared policy admits it and the verifier path confirms it.

## F. Reader / publication / maintenance surfaces

Reader and publication surfaces help humans understand the system.

Maintenance surfaces preserve operational history.

Examples include:

```text
README
documentation files
quality ledger
status summary pages
GitHub Pages output
release notes
audit bundle summaries
publication snapshots
metadata records
recovery ledger
developer positioning notes
SLSA alignment notes
proof plans
authority maps
```

These surfaces may describe or summarize the release-authority path.

They are not the release-authority path.

### Reader-surface boundary

```text
reader surface
≠ release decision
```

A reader surface may point to artifacts.

A reader surface may describe evidence.

A reader surface may summarize a run.

It does not replace the machine-readable evidence and enforcement chain.

## Required checks versus documented checks

This document distinguishes between two meanings of “required.”

### Policy-required

Policy-required means a gate is required by PULSEmech policy or by a materialized gate set.

This is a PULSEmech semantic requirement.

### Platform-required

Platform-required means a GitHub branch protection or repository setting requires a check before merge.

This is a GitHub repository administration requirement.

This document does not define platform branch protection.

This document does not claim that any listed check is configured as a GitHub required check.

This document maps authority categories so that platform settings can be configured consistently with the mechanism.

## Workflow-effective gate set

A release run may involve more than one policy set.

For release-grade interpretation, reviewers should identify the workflow-effective materialized gate set for the run.

That set may include:

```text
required
release_required
```

when both sets are active for the run.

The release decision should not be reconstructed from `release_required` alone if the workflow-effective enforcement path includes both base required gates and release-required gates.

## Test surfaces

The repository contains a broad test surface.

The tools-test manifest includes many release-authority, verifier, materializer, schema, evidence, attestation, reference-package, reader-surface, and fail-closed checks. This breadth is a strength, but it also requires clear authority mapping so that test outputs are not mistaken for release decisions by themselves. :contentReference[oaicite:1]{index=1}

A test may prove a contract, workflow invariant, schema boundary, documentation constraint, or wiring condition.

A test pass is not automatically a release decision unless it participates in the connected release-authority path.

## Workflow family map

| Workflow or surface family | Primary role | Authority category |
|---|---|---|
| `pulse_ci.yml` | Main repository CI and release-gating workflow | Primary release-authority path when enforcing declared policy and workflow-effective materialized gates |
| `pulse_core_ci.yml` | Deterministic core lane | Core deterministic lane |
| workflow lint / repo hygiene workflows | Configuration and repository integrity | Guardrail / hygiene |
| secret scan workflows | Security hygiene and advisory finding surface | Guardrail / advisory |
| Pages publishing workflows | Publish reader surfaces | Reader / publication |
| SARIF upload workflows | Publish analysis output to code-scanning surface | Reader / integration |
| shadow / EPF / research workflows | Produce diagnostic or research evidence | Advisory / diagnostic unless policy-promoted |
| documentation files | Explain state, contracts, operation, and maintenance | Reader / maintenance |
| recovery ledger | Record maintenance and recovery decisions | Maintenance surface, not release authority |
| SLSA alignment note | Explain provenance-to-transition relationship | Technical alignment surface, not release authority |
| developer-first positioning note | Define audience and adoption order | Technical positioning surface, not release authority |
| release-grade proof plan | Define qualification requirements for future run records | Technical plan, not release authority |

## Check family map

| Check family | Examples | Role | Release-authority status |
|---|---|---|---|
| Gate enforcement | `check_gates.py`, policy-derived required gates | Enforces allow/block decision | Normative when used in the primary path |
| Evidence verification | recorded release-evidence verifier, external summary attestation verifier | Verifies evidence admissibility | Normative only when connected to the materialized release path |
| Schema validation | status schema, release evidence schema, manifest schema | Ensures machine-readable contract validity | Supporting / guardrail |
| Workflow wiring smoke tests | workflow structure and pinned action checks | Guards workflow semantics | Guardrail |
| Reader non-interference tests | reader-surface non-authority checks | Prevents surface confusion | Guardrail / semantic protection |
| Exporter tests | JUnit, SARIF, report generation | Publication/integration correctness | Supporting |
| Shadow / diagnostic tests | EPF, recognition drift, HPC evidence, field-point maps | Diagnostic/research correctness | Advisory unless policy-promoted |
| Audit sidecar checks | `release_authority_v0.json` structure and non-interference | Supports audit and reconstruction | Supporting; not an independent authority engine |

## Promotion rule for advisory evidence

Advisory evidence may become release-relevant only through an explicit promotion path.

A valid promotion path should include:

```text
declared policy admission
schema-valid evidence
digest-bound artifact identity
signer or provenance requirement where applicable
verifier replay
workflow-effective materialized gate connection
fail-closed enforcement
```

Without this path, advisory evidence remains advisory.

## External evidence lane

External evidence may be used only under the declared policy and verifier requirements that apply to the run.

For `workflow_dispatch` runs, hosted external evidence may be selected through the `hosted_full_runtime` mode.

For version-tag release paths, hosted external evidence may be required when active policy and workflow-effective gates require it.

Therefore, hosted external evidence must not be described globally as optional.

If external evidence is missing, unverified, unsigned where signing is required, or not admitted by signer policy, it must not silently become release authority.

External evidence must be treated as untrusted until admitted by the verification path.

## Artifact provenance and attestation lane

Artifact provenance and attestation checks can support release evidence.

They should be interpreted as evidence-path controls.

Relevant evidence artifacts may include:

```text
artifact_provenance_binding_v0.json
attestation bundle
attestation envelope
external attestation verifier report
```

A passing provenance or attestation check can support a release decision.

It is not sufficient alone unless the release policy, workflow-effective materialized gates, verifier replay, and CI enforcement also pass.

## Reader-surface non-interference

PULSEmech should preserve reader-surface non-interference.

Reader surfaces may include documentation, summaries, static pages, metadata records, status renderers, and audit summaries.

These surfaces may help readers inspect the system.

They must not override or substitute:

```text
status.json
declared gate policy
workflow-effective materialized gate set
verifier replay
check_gates.py
primary CI result
```

## Audit / trace sidecar interpretation

Audit and trace sidecars help reviewers inspect the decision path.

The implemented release-authority audit / trace sidecar is:

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

This sidecar may record or reference evidence needed for review.

It does not independently authorize a release transition.

If an audit sidecar is missing or malformed, the review package may be incomplete.

That does not mean the sidecar itself is the primary release decision engine.

The primary release decision remains tied to:

```text
status.json
declared gate policy
workflow-effective materialized gate set
verifier replay
check_gates.py
primary CI allow/block result
```

## Maintainer interpretation checklist

Before treating a result as release-authoritative, a maintainer should ask:

```text
1. Which workflow produced the result?
2. Which ref and commit produced the result?
3. Which run mode was used?
4. Which gate policy was applied?
5. Which workflow-effective gate set was materialized?
6. Which evidence artifacts were verified?
7. Which verifier report was used?
8. Which check_gates enforcement step ran?
9. Did the primary CI path allow or block?
10. Is this result a reader surface, advisory report, audit sidecar, or maintenance record instead?
```

## External reviewer interpretation checklist

An external reviewer should distinguish:

```text
mechanism documentation
from
operational release evidence
```

and:

```text
reader surface
from
release-authority path
```

A technical review should identify the machine-readable artifacts that produced the decision.

If a claim cannot be traced to recorded evidence, declared policy, workflow-effective materialized gates, verifier replay, and CI enforcement, it should not be treated as release authority.

## CI failure interpretation rule

When a CI log shows a failure, it must be interpreted in context.

A failed run should be classified by:

```text
ref
commit
workflow
job
test
current reproducibility
relationship to active merge target
```

If a failure does not reproduce on the current branch and targeted test, it should not trigger speculative workflow changes.

If it reproduces on the current branch or an active merge target, it should be fixed before merge.

## Required artifact-name rule

Documentation that guides release proof or evidence review should use implemented artifact names where known.

Avoid invented placeholders when the repository already defines concrete artifacts.

Examples of concrete names:

```text
release_decision_v0.json
artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
gates/materialized_gate_sets.json
```

When a package manifest defines a more specific path, reviewers should follow the manifest.

## Recommended repository follow-up

This document is a map.

It does not configure GitHub branch protection.

Recommended follow-up work may include:

```text
publish a concise required-checks table
document branch-protection expectations separately
document which workflows are intended as required merge checks
document which workflows are advisory only
document the release-grade reference proof path separately
document artifact-name expectations for release-grade packages
```

These follow-up tasks should be implemented as documentation and repository settings updates only after the authority categories are stable.

## Summary

PULSEmech contains multiple workflow, artifact, audit, diagnostic, and reader surfaces.

Only the connected release-authority path produces an allow/block release-transition decision.

The durable interpretation is:

```text
recorded evidence
→ declared policy
→ workflow-effective materialized gate set
→ verifier replay
→ check_gates.py
→ primary CI allow/block result
```

All other surfaces should be interpreted according to their category:

```text
core proof
release-grade evidence support
audit / trace sidecar
guardrail
advisory diagnostic evidence
reader surface
maintenance record
```

This separation reduces misinterpretation and keeps PULSEmech reviewable by developers, maintainers, release engineers, and external technical reviewers.
