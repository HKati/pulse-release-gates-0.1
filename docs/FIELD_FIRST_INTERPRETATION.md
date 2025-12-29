# Field-first interpretation

This document is a **reading guide** for PULSE artifacts.  
It is **non-normative**: contracts, schemas and CI checks remain the source of truth.

## Core idea
PULSE should be read **field-first**:

- PULSE builds a **relational field snapshot** (a stable configuration).
- Views and questions are **projections** over that field.
- Release decisions remain **deterministic and fail-closed**.

This is not “simplification”. It is a stable interpretation order that preserves the
system’s multi-layer structure (gates + overlays + diagnostics).

## What this is NOT
- Not “token-based knowledge” or an agent memory.
- Not an event stream that “causes” decisions.
- Not a causal graph: **edges are co-occurrence evidence links, not causality claims**.
- Not a query-driven controller: **questions do not trigger decisions**.

## Field, relations, projections

### Field (stable configuration)
A **field** is the stable, audit-friendly configuration PULSE produces and validates:
- Deterministic gates and metrics (`status.json`)
- Optional diagnostic overlays (G-field, EPF, paradox, hazard, etc.)
- A stable fingerprint when available (`run_context.run_pair_id`)

Stability here is practical: required artifacts exist, contracts pass, and fingerprints
stay consistent across derived outputs.

### Relations (relational memory)
Relational memory is stored as **evidence-first relations**, not as “facts”:
- `paradox_field_v0.json`:
  - atoms represent observed drift (gate flip / metric delta / overlay change)
  - tension atoms represent co-occurrence (gate × metric, gate × overlay)
- `paradox_edges_v0.jsonl`:
  - edges index co-occurrence between atom endpoints and tension atoms

These artifacts do not introduce new truth; they preserve evidence and link integrity.

### Projections (views over the field)
A **projection** is a view rendered from the field:
- HTML report card / Quality Ledger
- `scripts/inspect_paradox_v0.py` → markdown summary
- GitHub Actions step summary excerpt

A projection may answer “what changed?” or “why did we block?”, but it does not
mutate the field and does not act as a trigger.

## Paradox as diagnostics (not illustration)
The paradox layer is a **diagnostic detector**:
- It detects **inconsistent relational patterns** (tension/co-occurrence under drift)
- It remains evidence-first and contract-driven
- It supports audit and triage without changing deterministic gate outcomes

## Practical reading order (recommended)
1) Verify contracts (field/edges) and required artifacts exist.
2) Read the field snapshot (gates + overlays + run_context).
3) Inspect relational diagnostics (atoms → tensions → edges).
4) Use projections (report/summary) for human navigation.

If the configuration is not stable (missing artifacts / contract fails), PULSE is
fail-closed by design.

## Naming conventions for clarity
To avoid confusion with classic pipelines:
- Use **field / configuration / overlay / diagnostics / projection**
- Avoid anthropomorphic labels (“thinks”, “intent”) and causal labels (“decision graph”)
- Prefer “projection view” over “query-driven” wording
