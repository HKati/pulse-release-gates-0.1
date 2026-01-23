# PULSE Paradox Core v0

The **Paradox Core v0** is a deterministic, reviewer-friendly projection of the Paradox field.
It exists to make Paradox/field outputs **auditable and stable**, before any UI/diagram rendering.

**Scope:** diagnostic overlay (CI-neutral by default).  
**Important:** the core release decision remains defined by `status.json` + `check_gates.py` + required CI gates.

---

## What it is

Paradox Core v0 is an artefact (`paradox_core_v0.json`) built from:

- a Paradox field artefact (atoms)
- optional edges (JSONL)

It produces a **Core**: a minimal, deterministic subset of atoms and their induced edges, suitable for reviewers.

**Edges are non-causal in v0:** association/co-occurrence only.

---

## Inputs

### Paradox field

Expected input: `paradox_field_v0.json`.

The builder supports both shapes:

- **Unwrapped**
  - `{ "schema": "...", "atoms": [...], "run_context": {...}, ... }`
- **Wrapped**
  - `{ "paradox_field_v0": { "schema": "...", "atoms": [...], ... }, ... }`

If wrapped, the builder unwraps `paradox_field_v0` before reading `atoms`, `run_context`, and metadata.

### Paradox edges (optional)

Optional input: `paradox_edges_v0.jsonl` (one JSON object per line).

If provided, the Core includes the **induced subgraph** of edges where both endpoints are Core atoms.

---

## Output artefact

### paradox_core_v0.json

Produced by: `scripts/paradox_core_projection_v0.py`

Key properties:

- deterministic top‑K selection by a metric (`severity` by default)
- deterministic tie-break: `atom_id` lexicographic ascending
- canonical ordering:
  - atoms: `(core_rank asc, atom_id asc)`
  - edges: `(src asc, dst asc, type asc, edge_id asc)`
- includes deterministic input hashes:
  - `inputs.field_sha256`
  - `inputs.edges_sha256` (or `null` when not provided)

Schema:
- `schemas/PULSE_paradox_core_v0.schema.json`

Contract checker:
- `scripts/check_paradox_core_v0_contract.py`

---

## Core selection rule (v0)

Selection method: `topk_metric_then_atom_id`

1) Score each atom by the configured metric (default: `severity`).
2) Sort descending by score.
3) Tie-break: ascending `atom_id`.
4) Take the first `k` atoms.
5) If edges are provided, keep only edges whose endpoints are within the Core.

Notes:

- Missing metric values are treated as `0.0` (deterministic; tracked via `stats.missing_metric_atoms`).
- Edge semantics remain association/co-occurrence only (non-causal).

---

## CLI quickstart

### Build core projection

```bash
python scripts/paradox_core_projection_v0.py \
  --field path/to/paradox_field_v0.json \
  --edges path/to/paradox_edges_v0.jsonl \
  --out out/paradox_core_v0.json \
  --k 12 \
  --metric severity
```

Edges are optional:

```bash
python scripts/paradox_core_projection_v0.py \
  --field path/to/paradox_field_v0.json \
  --out out/paradox_core_v0.json \
  --k 12 \
  --metric severity
```

### Contract check (fail-closed, overlay-local)

```bash
python scripts/check_paradox_core_v0_contract.py \
  --in out/paradox_core_v0.json
```

---

## Reviewer output: Markdown summary

A stable reviewer-facing summary can be produced from the core artefact.

**Tool**
- `scripts/inspect_paradox_core_v0.py`

**Example**

```bash
python scripts/inspect_paradox_core_v0.py \
  --in out/paradox_core_v0.json \
  --out out/paradox_core_summary_v0.md
```

This summary is deterministic (no timestamps, canonical ordering) and includes the explicit note:

- edges are non-causal (co-occurrence/association only)
- CI-neutral by default unless explicitly promoted

---

## Determinism & audit notes

Paradox Core v0 is audit-compatible if:

- inputs are pinned (runner image + dependency versions + CPU/GPU mode where relevant)
- any sampling/permutation upstream is seeded and recorded
- the builder output remains canonical-ordered and stable
- no silent external variability is introduced (external calls must be recorded as inputs or avoided)

The core artefact records input SHA256 hashes to make “what produced this output” traceable.

---

## Non-goals (v0)

- No causal inference (edges are not “A causes B”).
- No release gating (this artefact does not flip PASS/FAIL).
- No UI rendering (SVG/HTML diagram rendering is a separate, later step and must be pinned + regression-tested).

---

## Next steps (planned)

- Core → Render (SVG) with a pinned toolchain and golden-file regression tests.
- Optional Pages publishing of the core artefact + summary (as static artefacts only; Pages must not compute semantics).

