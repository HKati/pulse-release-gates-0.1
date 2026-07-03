# PULSEmech dependency single-truth plan v0

## Status

Technical maintenance plan.

This document defines a staged plan for reducing dependency-definition drift in the PULSEmech repository.

It does not change dependency files.

It does not introduce a lockfile.

It does not introduce `pyproject.toml`.

It does not remove `requirements.txt`, `requirements-analysis.txt`, `environment.yml`, or `PULSE_safe_pack_v0/requirements-llamaguard-v0.txt`.

It does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, or release-authority semantics.

## Purpose

PULSEmech currently has multiple dependency declaration surfaces.

These surfaces support different use cases, but they can drift over time if they are not governed by a clear maintenance model.

The purpose of this plan is to define a staged path toward one primary dependency definition and clearly derived installation surfaces.

## Current dependency surfaces

The repository currently uses or references several dependency-related files.

```text
requirements.txt
requirements-analysis.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

These files may serve different audiences:

```text
runtime / CI minimum requirements
analysis or extended tooling requirements
conda / environment reproduction
hosted external-runtime requirements
```

`PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` is part of the hosted external-runtime dependency surface for the `hosted_full_runtime` lane.

It is not part of the Tier 0 self-contained evidence-floor dependency surface.

It is not part of the minimal PULSEmech core runtime dependency surface.

It must not be promoted to core runtime without a later reviewed implementation decision.

The risk is not that multiple files exist.

The risk is that no single relationship between them is documented.

## Problem

When dependency definitions are maintained independently, the repository can develop drift.

Examples of drift:

```text
package present in one file but missing from another
different version bounds for the same package
CI using one dependency surface while local reproduction uses another
analysis tools requiring dependencies not represented in the maintenance model
hosted external-runtime dependencies omitted from dependency review
security scanners observing only part of the dependency set
documentation pointing to an outdated install path
```

Dependency drift weakens reproducibility.

It also makes supply-chain review harder because reviewers cannot immediately identify which dependency declaration is authoritative for which run mode.

## Design goal

The long-term goal is a dependency model with:

```text
one primary dependency definition
clear derived installation surfaces
documented update procedure
CI guard against drift
reviewable dependency changes
```

This plan does not require an immediate migration.

It defines the staged path.

## Non-goals

This plan does not attempt to:

```text
change runtime dependencies immediately
replace all requirements files immediately
force conda users into pip-only workflows
force pip users into conda workflows
introduce a lockfile without review
change CI behavior without a dedicated implementation PR
change release authority
promote hosted external-runtime dependencies into Tier 0 runtime
promote hosted external-runtime dependencies into core runtime
```

## Desired future model

A future dependency model may use:

```text
pyproject.toml
```

as the primary dependency definition for Python packaging metadata and dependency grouping.

Derived or supporting files may then be generated or maintained from that primary definition:

```text
requirements.txt
requirements-analysis.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
lockfile or pinned export
```

The exact tool choice should be decided in a later implementation step.

This plan only records the direction and acceptance criteria.

## Dependency categories

PULSEmech dependencies should be grouped by role.

### Core runtime dependencies

Dependencies required for the minimal PULSEmech runtime and CI gate checks.

Current examples include:

```text
pyyaml
jsonschema
```

The core runtime dependency set should remain small and stable.

Hosted external-runtime dependencies must not be silently added to the core runtime dependency set.

### Test dependencies

Dependencies required to run the repository test surface.

These may include test runners, schema validators, or supporting libraries.

### Analysis dependencies

Dependencies used for optional analysis, diagrams, research surfaces, extended evidence processing, or notebook-like workflows.

These should not silently become required for the minimal core runtime.

### Documentation dependencies

Dependencies used only to build or render documentation should not be required by core release-gating logic.

### External-tool dependencies

Dependencies used to invoke external detector, scanner, evaluator, or attestation tooling should be clearly separated from core runtime dependencies.

### Hosted external-runtime dependencies

Dependencies required only for hosted external-evidence lanes.

Current known surface:

```text
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

This file belongs to the hosted LlamaGuard / hosted external-runtime lane.

It is associated with `hosted_full_runtime`.

It is not part of the Tier 0 self-contained evidence-floor dependency surface.

It is not part of the minimal PULSEmech core runtime dependency surface.

It should be reviewed separately from core runtime dependencies because hosted external-runtime dependencies may involve provider access, model authorization, credentials, runtime cost, and different supply-chain review conditions.

## Required boundaries

A dependency maintenance model should preserve these boundaries.

```text
core runtime dependencies
≠ analysis dependencies

core CI gate dependencies
≠ optional research dependencies

release-authority mechanism dependencies
≠ reader-surface rendering dependencies

hosted external-runtime dependencies
≠ Tier 0 self-contained evidence-floor dependencies

hosted external-runtime dependencies
≠ minimal core runtime dependencies
```

The known hosted LlamaGuard dependency surface is:

```text
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

This surface must remain separate from:

```text
requirements.txt
```

when `requirements.txt` is treated as the minimal core runtime dependency surface.

## Migration stages

### Stage 0 — Current state record

Record the current dependency surfaces.

```text
requirements.txt
requirements-analysis.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

Document their current intended use.

The hosted LlamaGuard requirements file should be recorded as a hosted external-runtime dependency surface, not as Tier 0 or core runtime dependency material.

No file changes are required for Stage 0 beyond documentation of the current state.

### Stage 1 — Dependency surface inventory

Create an inventory of all dependency references in the repository.

Search areas:

```text
requirements*.txt
PULSE_safe_pack_v0/requirements-*.txt
environment.yml
GitHub Actions workflows
documentation install instructions
scripts that invoke pip or conda
tests that assume optional packages
analysis tools
hosted external-runtime dependency surfaces
```

Expected output:

```text
docs/maintenance/PULSEMECH_DEPENDENCY_SURFACE_INVENTORY_v0.md
```

The inventory should explicitly identify which workflows install which dependency surfaces.

It should also identify which tests lock the expected contents or use of those dependency surfaces.

### Stage 2 — Role classification

Classify each dependency into one or more roles:

```text
core-runtime
test
analysis
documentation
external-tooling
hosted-external-runtime
optional
```

A dependency should not be promoted into core runtime unless required for the minimal PULSEmech mechanism.

Hosted external-runtime dependencies should remain classified separately unless a later reviewed implementation decision intentionally changes that boundary.

### Stage 3 — Primary dependency definition proposal

Propose the primary dependency definition format.

Candidate:

```text
pyproject.toml
```

The proposal should define:

```text
project metadata
core dependencies
optional dependency groups
test dependency group
analysis dependency group
documentation dependency group
external-tooling dependency group
hosted external-runtime dependency group
```

No migration should occur until the proposal is reviewed.

### Stage 4 — Derived file strategy

Define which files remain as derived or compatibility surfaces.

Possible derived or compatibility files:

```text
requirements.txt
requirements-analysis.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

The plan should state whether each file is:

```text
primary
derived
compatibility surface
deprecated
manual-only
generated
```

The hosted LlamaGuard requirements surface may remain a separate compatibility surface if the hosted external-runtime lane requires a tightly controlled dependency set.

It should not be folded into the Tier 0 self-contained dependency surface unless the hosted runtime requirement is intentionally promoted by a later reviewed implementation decision.

### Stage 5 — Lock / pin strategy

Define whether and how lockfiles are introduced.

Questions:

```text
Is a lockfile required for CI?
Is a lockfile required for local reproduction?
Should lockfiles be platform-specific?
How are lockfiles updated?
How are security updates handled?
How are optional analysis dependencies pinned?
How are hosted external-runtime dependencies pinned?
Should hosted external-runtime dependencies use a separate lock or export?
```

A lock strategy should not be introduced without a documented update procedure.

### Stage 6 — CI drift guard

Introduce a CI guard only after the dependency model is stable.

The guard should verify:

```text
derived files match the primary definition
dependency groups are not mixed accidentally
core runtime remains minimal
analysis dependencies do not enter minimal runtime unintentionally
hosted external-runtime dependencies do not enter Tier 0 runtime unintentionally
hosted external-runtime dependency surfaces remain covered by drift review
```

### Stage 7 — Documentation update

Update installation documentation only after the dependency model is implemented.

Documentation should clearly describe:

```text
minimal install
test install
analysis install
developer install
optional external-tool install
hosted external-runtime install
```

## Acceptance criteria

A completed dependency single-truth migration should satisfy:

```text
1. One primary dependency definition is identified.
2. Derived dependency surfaces are documented.
3. Core runtime dependencies are separated from analysis and optional dependencies.
4. Hosted external-runtime dependencies are separated from Tier 0 and core runtime dependencies.
5. CI uses the intended dependency surface for each run mode.
6. Local reproduction instructions match CI.
7. Optional analysis dependencies do not become implicit runtime requirements.
8. Hosted external-runtime dependencies do not become implicit Tier 0 requirements.
9. Dependency updates have a documented review path.
10. Drift between primary and derived dependency files is detected.
11. Drift involving hosted external-runtime dependency surfaces is detected.
12. The migration does not change release-authority semantics.
```

## Risk controls

Dependency migration can easily break CI or local reproduction.

Therefore, any implementation should be split into small PRs.

Recommended order:

```text
1. inventory only
2. classification only
3. proposal only
4. pyproject introduction without behavior change
5. derived export generation
6. hosted external-runtime dependency export decision
7. CI guard
8. documentation update
```

Avoid combining all stages into one large PR.

Do not combine dependency migration with workflow semantic changes.

Do not combine dependency migration with release-authority semantic changes.

## Current decision

The current decision is:

```text
do not migrate immediately
do not remove existing dependency files
do not add a lockfile yet
do not change CI dependency installation yet
do not promote hosted external-runtime dependencies to Tier 0 runtime
do not promote hosted external-runtime dependencies to core runtime
document the staged path first
```

## Relationship to release authority

Dependency management supports reproducibility and supply-chain review.

It does not create release authority.

Release authority remains bound to:

```text
recorded evidence
declared policy
workflow-effective materialized gate set
verifier replay
check_gates.py
primary CI allow/block decision
```

Dependency changes may affect the reliability of that path.

Therefore dependency changes should be reviewed carefully, but they do not themselves define the release decision.

## Relationship to developer-first adoption

A developer-first mechanism must be installable and reproducible.

A dependency model is successful if a technical user can identify:

```text
which dependencies are required for the minimal PULSEmech mechanism
which dependencies are only for tests
which dependencies are for analysis
which dependencies are optional
which dependencies are for hosted external-runtime lanes
which dependency definition CI uses
how to reproduce the CI environment locally
how to avoid installing hosted external-runtime dependencies for Tier 0 operation
```

If this cannot be answered, the dependency model is not yet clear enough.

## Relationship to hosted external runtimes

Hosted external model or evaluator dependencies should remain clearly separated from Tier 0 self-contained operation.

A user should be able to run the self-contained evidence floor without installing or authorizing hosted external-runtime dependencies.

Known hosted external-runtime dependency surface:

```text
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

This surface should be documented, inventoried, and reviewed.

It should remain separate from core runtime unless a later implementation deliberately changes that boundary.

External runtime dependencies should be opt-in or policy-required only for the lanes that actually need them.

They should not become implicit requirements for self-contained operation.

## Review questions

Before implementation, reviewers should answer:

```text
1. Which file currently defines the minimal runtime dependency set?
2. Which workflows install dependencies, and from which files?
3. Which dependencies are required only for tests?
4. Which dependencies are required only for analysis or research surfaces?
5. Which dependencies are required for hosted external evidence lanes?
6. Which dependency files belong only to hosted external-runtime lanes?
7. Should PULSE_safe_pack_v0/requirements-llamaguard-v0.txt remain separate from core runtime dependencies?
8. Should pyproject.toml become the primary dependency definition?
9. Which tool should generate derived requirements files?
10. Is a lockfile needed for CI, local reproduction, or both?
11. Should hosted external-runtime dependencies use a separate lock or export?
12. How should dependency updates be reviewed?
13. How should drift between dependency surfaces be detected?
14. How should hosted external-runtime dependency drift be detected?
```

## Proposed next artifact

The next artifact after this plan should be an inventory file:

```text
docs/maintenance/PULSEMECH_DEPENDENCY_SURFACE_INVENTORY_v0.md
```

That file should list:

```text
all dependency files
all workflow dependency installation steps
all documentation install instructions
all dependency-related tests
all optional external-tool dependency surfaces
all hosted external-runtime dependency surfaces
current role of each dependency surface
current Tier 0 versus hosted-runtime boundary
```

## Summary

This plan records a staged path toward a cleaner dependency maintenance model.

The immediate action is documentation and inventory.

The migration itself should happen later, in small reviewed steps.

The target state is:

```text
one primary dependency definition
clearly derived compatibility surfaces
separated runtime / test / analysis / optional dependency groups
separated hosted external-runtime dependency surface
drift detection
reproducible CI and local setup
Tier 0 operation protected from hosted-runtime dependency creep
```
