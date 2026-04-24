# PULSE Space Relation Map v0

## What this is

`space_relation_map_v0` is a descriptive-only topology artifact for PULSE.

It makes the repository’s authority structure more explicit in
machine-readable form by recording:

- spaces
- elements
- placements
- relations
- invariants

The purpose of this artifact is clarity, topology, and reviewability.

It is not a release-decision artifact.

---

## Current status

Current status: **descriptive only**

The artifact does **not** define shipping outcomes.  
It does **not** override `status.json`.  
It does **not** replace policy-defined gate enforcement.  
It does **not** act as a second decision engine.

Its role is to express how parts of the system relate to each other,
especially around authority boundaries.

---

## Why this exists

PULSE already distinguishes, in prose and workflows, between:

- the normative release core
- guardrail and integrity checks
- publication surfaces
- shadow / diagnostic overlays
- external evidence surfaces

`space_relation_map_v0` begins expressing that structure explicitly and
machine-readably.

This is especially useful for showing:

- what belongs to the core
- what only reads the core
- what may feed the core
- what cannot override the core
- what only becomes normatively relevant if policy/workflow promotes it

---

## Current files

- `examples/space_relation_map_v0.manual.json`
  - hand-authored manual seed artifact

- `schemas/schemas/space_relation_map_v0.schema.json`
  - JSON Schema for the artifact structure

- `tools/validate_space_relation_map.py`
  - validates schema shape and basic reference consistency

- `tools/render_space_relation_map_summary.py`
  - renders a human-readable markdown summary

- `tools/build_space_relation_map_summary.py`
  - validates and renders the topology summary to a canonical output path

- `tests/test_validate_space_relation_map_tool.py`
  - validator smoke test

- `tests/test_render_space_relation_map_summary_tool.py`
  - renderer smoke test

- `tests/test_build_space_relation_map_summary_tool.py`
  - builder smoke test

- `ci/tools-tests.list`
  - includes validator, renderer, and builder topology tool smoke tests

---

## Core concepts

### Spaces

A **space** is a topological domain such as:

- `core`
- `guardrail`
- `shadow`
- `publication`
- `external`

### Elements

An **element** is a named component placed into a space, such as:

- `status_json`
- `gate_policy`
- `check_gates`
- `pulse_ci`
- `quality_ledger`
- `external_summary`
- `paradox_overlay`

### Placements

A **placement** assigns an element to a space.

This is the answer to:
> where does this thing stand?

### Relations

A **relation** describes how one element or space is connected to another.

This is the answer to:
> what kind of connection exists here?

Examples include:

- `reads`
- `materializes`
- `enforces`
- `observes`
- `feeds`
- `anchors_to`
- `cannot_override`
- `may_promote_if_policy`

### Invariants

An **invariant** records a stable topology statement such as:

- only core defines shipping
- publication surfaces do not define shipping
- shadow layers cannot override core
- external evidence only becomes normatively relevant if policy/workflow promotes it

---

## Authority boundary

The most important rule is:

> `space_relation_map_v0` describes authority boundaries;  
> it does not itself become release authority.

Today, release authority still belongs to the established PULSE core,
including the final `status.json`, the policy-defined effective gate set,
and the enforcing workflow/tool path.

---

## Validation

Validate the artifact:

```bash
python tools/validate_space_relation_map.py \
  examples/space_relation_map_v0.manual.json
```

Validate with explicit schema path:

```bash
python tools/validate_space_relation_map.py \
  examples/space_relation_map_v0.manual.json \
  --schema schemas/schemas/space_relation_map_v0.schema.json
```

---

## Rendering

Render a markdown summary:

```bash
python tools/render_space_relation_map_summary.py \
  examples/space_relation_map_v0.manual.json \
  --out /tmp/space_relation_map_v0_summary.md
```
---
## Build

Build the validated topology summary to the canonical repo output path:

```bash
python tools/build_space_relation_map_summary.py
```

Default output:

```text
reports/topology/space_relation_map_v0_summary.md
```
---

## Non-goals in v0

This artifact does not yet do the following:

- CI enforcement of topology invariants  
- policy execution  
- release gating  
- automatic promotion of external evidence  
- graph visualization  
- relation-type-specific semantic proofs  

Those may come later, but they are intentionally out of scope for v0.

---

## Why this matters

This artifact helps make PULSE easier to read correctly.

It reduces the chance that readers confuse:

- authority with presentation  
- shadow diagnostics with release enforcement  
- external evidence with automatically normative evidence  
- readable surfaces with decision surfaces  

In short:

`space_relation_map_v0` helps make PULSE’s structure legible without
flattening it.
