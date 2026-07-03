# PULSEmech dependency single-truth plan v0

## Status

Technical dependency-surface plan.

This document does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, branch protection settings, or release-authority semantics.

## Purpose

PULSEmech should keep dependency authority explicit so reviewers can distinguish the self-contained evidence-floor runtime from hosted external-runtime lanes.

## Current dependency surfaces

The current dependency surfaces are:

```text
requirements.txt
environment.yml
PULSE_safe_pack_v0/requirements-llamaguard-v0.txt
```

`requirements.txt` remains the current canonical core runtime dependency surface for the repository’s self-contained PULSE evidence floor.

`environment.yml` is a broader convenience environment and must not be treated as the canonical core runtime definition by itself.

`PULSE_safe_pack_v0/requirements-llamaguard-v0.txt` is part of the hosted external-runtime dependency surface for the `hosted_full_runtime` lane.

It is not part of the Tier 0 self-contained evidence-floor dependency surface and must not be promoted to core runtime.

## Hosted external-runtime boundary

The hosted external-runtime dependency surface exists to support optional or policy-required hosted evidence lanes when the active workflow-effective policy requires them.

It must remain separate from the Tier 0 self-contained evidence-floor dependency surface so that hosted model dependencies, provider credentials, provider availability, and external runtime authorization do not silently become core runtime requirements.

## Single-truth rule

Dependency documentation and workflow interpretation should preserve these boundaries:

```text
Tier 0 self-contained evidence floor
→ core runtime dependency surface

hosted_full_runtime lane
→ hosted external-runtime dependency surface
```

A dependency may move between surfaces only through an explicit reviewed change that updates the workflow contract, documentation, and any affected tests.
