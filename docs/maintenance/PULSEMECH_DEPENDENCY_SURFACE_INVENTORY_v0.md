# PULSEmech dependency surface inventory v0

## Status

Technical maintenance inventory.

This document records the current dependency declaration, installation, and review surfaces known in the PULSEmech repository.

It does not change dependency files.

It does not introduce a lockfile.

It does not introduce a new primary dependency definition.

It does not remove or deprecate any current dependency surface.

It does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, or release-authority semantics.

## Purpose

The purpose of this inventory is to make dependency surfaces explicit before any dependency single-truth migration is attempted.

The inventory supports:

```text
reproducibility review
supply-chain review
CI/local environment comparison
Tier 0 versus hosted-runtime boundary review
future drift detection
```

This document is an inventory.

It is not a migration.

## Current known dependency surfaces

The repository currently contains or references the following dependency surfaces.

```text
requirements.txt
requirements-analysis.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

Each surface has a different role.

## Surface summary

| Dependency surface | Current role | Runtime category | Tier 0 core? | Hosted runtime? |
|---|---|---:|---:|---:|
| `requirements.txt` | Minimal runtime / CI dependency surface | core-runtime | yes | no |
| `requirements-analysis.txt` | Optional analysis / extended tooling surface | analysis | no | no |
| `environment.yml` | Conda / environment reproduction surface | environment compatibility | no, unless explicitly used | no |
| `PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` | Hosted LlamaGuard / hosted external-runtime surface | hosted-external-runtime | no | yes |

## Surface: requirements.txt

### Path

```text
requirements.txt
```

### Current role

`requirements.txt` is treated as the minimal core runtime / CI dependency surface.

It should remain small and stable.

It should not silently absorb:

```text
analysis dependencies
documentation rendering dependencies
hosted external-runtime dependencies
research-only dependencies
notebook-only dependencies
```

### Boundary

```text
requirements.txt
= minimal PULSEmech runtime / CI dependency surface

requirements.txt
≠ hosted external-runtime dependency surface
```

### Review rule

A dependency should enter `requirements.txt` only if it is required for the minimal PULSEmech mechanism or core CI gate checks.

## Surface: requirements-analysis.txt

### Path

```text
requirements-analysis.txt
```

### Current role

`requirements-analysis.txt` is the analysis / extended tooling surface.

It may support:

```text
analysis scripts
research surfaces
optional reporting
extended evidence exploration
diagnostic tooling
```

### Boundary

```text
requirements-analysis.txt
≠ minimal core runtime
```

Analysis dependencies should not silently become Tier 0 runtime requirements.

### Review rule

A dependency should remain in the analysis surface unless it is required by the minimal release-authority mechanism.

## Surface: environment.yml

### Path

```text
environment.yml
```

### Current role

`environment.yml` is an environment reproduction / compatibility surface.

It may support users who prefer Conda-style setup.

### Boundary

```text
environment.yml
≠ primary dependency source by default
```

Unless a later reviewed decision changes the dependency model, `environment.yml` should be treated as a compatibility surface.

### Review rule

The relationship between `environment.yml` and the other dependency surfaces should be explicitly documented before any generated-file or drift-check strategy is introduced.

## Surface: hosted LlamaGuard requirements

### Path

```text
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

### Current role

`PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` is the hosted external-runtime dependency surface for the `hosted_full_runtime` lane.

It is associated with hosted LlamaGuard / external evaluator operation.

### Boundary

```text
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
≠ Tier 0 self-contained evidence-floor dependency surface

PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
≠ minimal PULSEmech core runtime dependency surface
```

This file must not be promoted to Tier 0 or core runtime without a later reviewed implementation decision.

### Review rule

Hosted external-runtime dependencies should be reviewed separately from minimal core runtime dependencies because they may involve:

```text
provider access
model authorization
credentials
runtime cost
hosted service availability
different supply-chain review conditions
```

## Known workflow install surfaces

This inventory records known workflow-specific dependency installation surfaces.

These entries are dependency surfaces even when they are not represented by a standalone requirements file.

| Workflow | Install surface | Dependency source | Category | Notes |
|---|---|---|---|---|
| `.github/workflows/pulse_ci.yml` | Hosted LlamaGuard runtime install | `PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` | hosted-external-runtime | Installed for the `hosted_full_runtime` release path. |
| `.github/workflows/docs_hygiene.yml` | Documentation / citation validation install | `cffconvert` inline pip install | documentation / workflow-specific | Used for `CITATION.cff` validation. |
| `.github/workflows/make_org.yml` | OpenGraph image generation install | `Pillow>=10,<12` inline pip install | documentation / workflow-specific | Used for generated image surfaces. |
| `.github/workflows/gravity_record_protocol_v0_1_shadow.yml` | Shadow contract fixture install | `jsonschema==4.23.0` inline pip install | shadow / workflow-specific | Used for gravity record protocol shadow fixtures. |

Workflow-specific inline installs must be inventoried because they can drift outside the main dependency files.

They are not automatically part of the minimal core runtime dependency surface.

They should be classified by lane and reviewed before any dependency single-truth migration.

## Known test / guard surfaces

The inventory should track tests that enforce dependency-surface boundaries.

Known relevant test or guard categories include:

```text
minimal core runtime dependency guard
analysis dependency manifest guard
hosted LlamaGuard workflow wiring guard
tools-tests manifest coherence guard
workflow install-surface guards
```

Known test examples include:

```text
tests/test_tools_tests_list_smoke.py
tests/test_analysis_dependency_manifest.py
tests/test_llamaguard_current_run_workflow_wiring_v0.py
```

These tests should be reviewed before dependency migration because they may lock expected dependency files or expected runtime surfaces.

## Inventory rules

Dependency inventory entries should record:

```text
path
role
runtime category
workflow usage
test coverage
Tier 0 relationship
hosted-runtime relationship
migration status
drift risk
```

## Runtime categories

Use these categories when classifying dependency surfaces.

```text
core-runtime
test
analysis
documentation
environment-compatibility
external-tooling
hosted-external-runtime
optional
unknown
```

A dependency surface may have more than one category only when the overlap is documented.

## Tier 0 boundary

Tier 0 self-contained operation should remain separated from hosted external-runtime dependencies.

A user should be able to run the self-contained evidence floor without installing or authorizing hosted external-runtime dependencies.

Therefore:

```text
Tier 0 self-contained dependency set
must not require
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

unless a later reviewed implementation intentionally changes that boundary.

## Hosted runtime boundary

Hosted external-runtime dependency surfaces should remain explicit.

A hosted runtime dependency surface may be required for a lane such as:

```text
hosted_full_runtime
```

but this does not make it part of:

```text
Tier 0 self-contained operation
minimal core runtime
default local smoke path
```

## Drift risks

Known drift risks include:

```text
a package appears in one dependency file but not another
different version bounds are used for the same package
CI uses one surface while local instructions use another
analysis dependencies leak into core runtime
hosted external-runtime dependencies leak into Tier 0 runtime
security scanners miss hosted runtime dependency surfaces
documentation points to an outdated install command
workflow tests assert a dependency surface not recorded in the plan
workflow-specific inline installs drift outside dependency review
```

## Current inventory table

| Path | Role | Category | Tier 0 | Hosted runtime | Migration status |
|---|---|---|---:|---:|---|
| `requirements.txt` | Minimal runtime / CI dependency surface | core-runtime | yes | no | existing |
| `requirements-analysis.txt` | Analysis / extended tooling | analysis | no | no | existing |
| `environment.yml` | Conda / environment reproduction | environment-compatibility | no, unless selected by user | no | existing |
| `PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` | Hosted LlamaGuard dependencies | hosted-external-runtime | no | yes | existing |
| `.github/workflows/docs_hygiene.yml` inline install | `cffconvert` for citation validation | documentation / workflow-specific | no | no | existing |
| `.github/workflows/make_org.yml` inline install | `Pillow>=10,<12` for OpenGraph image generation | documentation / workflow-specific | no | no | existing |
| `.github/workflows/gravity_record_protocol_v0_1_shadow.yml` inline install | `jsonschema==4.23.0` for shadow contract fixtures | shadow / workflow-specific | no | no | existing |

## Current decision

The current decision is:

```text
inventory only
no migration
no lockfile
no pyproject introduction
no dependency file changes
no workflow install changes
no CI behavior changes
```

## Review checklist

Before any dependency migration, reviewers should verify:

```text
1. Which dependency files exist?
2. Which workflows install each file?
3. Which workflows use inline dependency installs?
4. Which tests assert each dependency surface?
5. Which file represents minimal core runtime?
6. Which file represents analysis dependencies?
7. Which file represents hosted external-runtime dependencies?
8. Which dependency surfaces are used by Tier 0?
9. Which dependency surfaces are used only by hosted runtime lanes?
10. Which surfaces are compatibility surfaces?
11. Which surfaces are workflow-specific inline installs?
12. Which surfaces are intended to become derived files later?
13. Which drift guards already exist?
14. Which drift guards are missing?
```

## Migration readiness checklist

A dependency single-truth migration should not begin until this inventory can answer:

```text
minimal install path
test install path
analysis install path
hosted runtime install path
workflow install path
workflow-specific inline install path
local reproduction path
security scanner coverage path
```

If any of these paths are unclear, migration should wait.

## Relationship to release authority

Dependency inventory supports reproducibility and supply-chain review.

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

Dependency changes can affect the reliability of that path.

They do not define the release decision.

## Relationship to developer-first adoption

Developer-first adoption requires a clear installation and reproduction model.

A technical user should be able to tell:

```text
what to install for minimal PULSEmech operation
what to install for tests
what to install for analysis
what to install for hosted external runtime
what not to install for Tier 0
which workflow-specific inline installs exist
```

This inventory is the first step toward that clarity.

## Follow-up work

Recommended follow-up work:

```text
1. Verify all workflow dependency install commands.
2. Verify all documentation install instructions.
3. Verify all tests that lock dependency-surface expectations.
4. Build a dependency role classification table.
5. Decide whether a primary dependency definition is needed.
6. Decide which files remain compatibility surfaces.
7. Decide how workflow-specific inline installs should be represented in a future single-truth model.
8. Design drift detection only after the inventory is stable.
```

## Summary

This inventory records the current dependency surfaces and their intended roles.

The key boundary is:

```text
requirements.txt
→ minimal core runtime / CI surface

requirements-analysis.txt
→ analysis surface

environment.yml
→ environment reproduction surface

PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
→ hosted external-runtime surface

workflow-specific inline installs
→ documented workflow-specific surfaces
```

The hosted LlamaGuard dependency surface is intentionally recorded.

Workflow-specific inline installs are intentionally recorded.

They must remain separate from Tier 0 and minimal core runtime unless a later reviewed implementation decision changes that boundary.
