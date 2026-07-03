# PULSEmech dependency single-truth plan v0

## Status

Technical maintenance plan.

This document defines a staged plan for reducing dependency-definition drift in the PULSEmech repository.

It does not change dependency files.

It does not introduce a lockfile.

It does not introduce `pyproject.toml`.

It does not remove `requirements.txt`, `requirements-analysis.txt`, or `environment.yml`.

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
```

These files may serve different audiences:

```text
runtime / CI minimum requirements
analysis or extended tooling requirements
conda / environment reproduction
```

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

## Required boundaries

A dependency maintenance model should preserve these boundaries.

```text
core runtime dependencies
≠ analysis dependencies

core CI gate dependencies
≠ optional research dependencies

release-authority mechanism dependencies
≠ reader-surface rendering dependencies

hosted external runtime dependencies
≠ Tier 0 self-contained evidence-floor dependencies
```

## Migration stages

### Stage 0 — Current state record

Record the current dependency surfaces.

```text
requirements.txt
requirements-analysis.txt
environment.yml
```

Document their current intended use.

No file changes are required for Stage 0.

### Stage 1 — Dependency surface inventory

Create an inventory of all dependency references in the repository.

Search areas:

```text
requirements*.txt
environment.yml
GitHub Actions workflows
documentation install instructions
scripts that invoke pip or conda
tests that assume optional packages
analysis tools
```

Expected output:

```text
docs/maintenance/PULSEMECH_DEPENDENCY_SURFACE_INVENTORY_v0.md
```

### Stage 2 — Role classification

Classify each dependency into one or more roles:

```text
core-runtime
test
analysis
documentation
external-tooling
optional
```

A dependency should not be promoted into core runtime unless required for the minimal PULSEmech mechanism.

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
```

No migration should occur until the proposal is reviewed.

### Stage 4 — Derived file strategy

Define which files remain as derived or compatibility surfaces.

Possible derived files:

```text
requirements.txt
requirements-analysis.txt
environment.yml
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
```

## Acceptance criteria

A completed dependency single-truth migration should satisfy:

```text
1. One primary dependency definition is identified.
2. Derived dependency surfaces are documented.
3. Core runtime dependencies are separated from analysis and optional dependencies.
4. CI uses the intended dependency surface.
5. Local reproduction instructions match CI.
6. Optional analysis dependencies do not become implicit runtime requirements.
7. Dependency updates have a documented review path.
8. Drift between primary and derived dependency files is detected.
9. The migration does not change release-authority semantics.
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
6. CI guard
7. documentation update
```

Avoid combining all stages into one large PR.

## Current decision

The current decision is:

```text
do not migrate immediately
do not remove existing dependency files
do not add a lockfile yet
do not change CI dependency installation yet
document the staged path first
```

## Relationship to release authority

Dependency management supports reproducibility and supply-chain review.

It does not create release authority.

Release authority remains bound to:

```text
recorded evidence
declared policy
materialized required gate set
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
which dependency definition CI uses
how to reproduce the CI environment locally
```

If this cannot be answered, the dependency model is not yet clear enough.

## Relationship to hosted external runtimes

Hosted external model or evaluator dependencies should remain clearly separated from Tier 0 self-contained operation.

A user should be able to run the self-contained evidence floor without installing or authorizing hosted external runtime dependencies.

External runtime dependencies should be opt-in and documented separately.

## Review questions

Before implementation, reviewers should answer:

```text
1. Which file currently defines the minimal runtime dependency set?
2. Which workflows install dependencies, and from which files?
3. Which dependencies are required only for tests?
4. Which dependencies are required only for analysis or research surfaces?
5. Which dependencies are required for hosted external evidence lanes?
6. Should pyproject.toml become the primary dependency definition?
7. Which tool should generate derived requirements files?
8. Is a lockfile needed for CI, local reproduction, or both?
9. How should dependency updates be reviewed?
10. How should drift between dependency surfaces be detected?
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
current role of each dependency surface
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
drift detection
reproducible CI and local setup
```
