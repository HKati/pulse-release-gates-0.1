# Paradox diagram v0

## Purpose

The **Paradox diagram v0** is a *reviewer-friendly projection* of the paradox field:
a compact topology view of **nodes** (paradox states/atoms) and **edges** (tensions).

It is intentionally **lossy**:
- we do **not** discard the underlying data,
- we provide a deterministic *view* that is easy to scan in PR review / CI artifacts.

This diagram is designed to answer in ~30 seconds:
- “Where is the tension cluster?”
- “Which states are most connected / central?”
- “What are the strongest (highest-weight) tensions right now?”

---

## Inputs and outputs

### Inputs
The renderer consumes the standard paradox artifacts:

- `out/paradox_field_v0.json`  
  The node/state registry (IDs + labels) for the paradox field.

- `out/paradox_edges_v0.jsonl`  
  One edge per line, describing tensions between nodes.

> Note: The renderer supports canonical endpoint keys (`src_atom_id`, `dst_atom_id`) and
> common legacy fallbacks (`src_id`, `dst_id`, `src`, `dst`, `from`, `to`, etc.).

### Output
- `out/paradox_diagram_v0.md`  
  A Markdown file that embeds a Mermaid diagram code fence for GitHub rendering.

---

## Generate the diagram locally

Typical invocation (deterministic, stable ordering):

```bash
python scripts/render_paradox_diagram_v0.py \
  --field out/paradox_field_v0.json \
  --edges out/paradox_edges_v0.jsonl \
  --out out/paradox_diagram_v0.md \
  --max-nodes 40 \
  --max-edges 120 \
  --min-weight 0.0


```

## Open the output file

Open the output file in GitHub (or any Markdown renderer that supports Mermaid):

- `out/paradox_diagram_v0.md`

## How to read the diagram

### Nodes

- Each node represents a paradox state/atom from the field.
- The label is intended to be human-readable.
- The underlying node ID is kept stable for reproducibility.
- If you see the same node across runs, it refers to the same underlying atom ID.

### Edges

Each directed edge represents a “tension” relation between two nodes.  
The renderer emits edges in a deterministic order and typically labels edges with:

- an edge type (if present in the source)
- and a weight (if present), representing strength / salience of the tension

**Interpretation guidance:**

- Higher-weight edges are the “strongest tensions” worth inspecting first.
- Clusters of highly connected nodes often indicate a **tension cluster**: a region of the field
  where governance decisions are most sensitive.

## This is a projection, not the full story

The diagram is intentionally constrained:

- `--max-nodes` and `--max-edges` limit clutter and keep the view reviewable.
- `--min-weight` can be used to filter low-signal edges.

If you need completeness, inspect:

- the full `out/paradox_edges_v0.jsonl` (machine-readable)
- and the paradox summaries in CI artifacts.

## Parameters

### `--max-nodes`

Upper bound on the number of nodes included in the diagram.

Recommended defaults:

- 30–50 for PR review
- higher only when generating an offline deep-dive view

### `--max-edges`

Upper bound on the number of edges included in the diagram.

Recommended defaults:

- 80–150 for PR review

### `--min-weight`

Filters edges by weight threshold (inclusive). Use this to remove low-signal edges.

Examples:

- `--min-weight 0.0` include everything (subject to max limits)
- `--min-weight 0.2` show only stronger tensions

## Determinism guarantees

The renderer is designed to be deterministic given the same inputs:

- stable node/edge selection (top-N selection is stable)
- stable sorting (weight/type/src/dst ordering)
- stable output formatting (Mermaid code fence content does not depend on runtime hash order)

This matters for:

- comparing diagrams between runs
- reducing “diagram diff noise” in CI artifacts

## Empty / degenerate cases (fail-closed but reviewer-friendly)

If there are no edges (e.g., fixtures like “empty edges” / “no atoms”):

- the renderer still produces `out/paradox_diagram_v0.md`
- with a clear note that the diagram is empty

This avoids CI failures while keeping the artifact meaningful.

## Troubleshooting

### Missing input file

Ensure the upstream paradox steps produced:

- `out/paradox_field_v0.json`
- `out/paradox_edges_v0.jsonl`

### Diagram renders as code, not a graph

GitHub renders Mermaid in Markdown, but only inside a proper Mermaid code fence.  
Make sure you are viewing the generated `out/paradox_diagram_v0.md` in GitHub (or a Mermaid-capable viewer).

### Too cluttered

Reduce clutter with:

- smaller `--max-nodes`
- smaller `--max-edges`
- higher `--min-weight`
