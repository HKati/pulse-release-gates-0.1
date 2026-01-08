# PULSE Paradox Diagram v0

**Status:** Spec (v0) • **Layer:** Diagnostic / CI-neutral by default • **Semantics-first** (UI/render comes later)

The **Paradox Diagram v0** is a **reference-oriented relational field** (“viszonytér”) built from Paradox Core outputs.

It is **not** “just a chart”: it is the minimum stable structure that makes reviewer-facing explanation possible without letting the UI invent meaning.

- **nodes**: atoms + explicit reference anchors  
- **edges**: *associations* (co-occurrence) and *reference-relations* (reference-oriented only)  
- **weights**: evidence/association strength (not causality)  
- **constraints**: contract-level invariants that prevent accidental causal interpretation  
- **determinism**: canonical ordering + stable IDs + no wall-clock variability  

> **Non-goal (v0):** no causal inference.  
> An edge never means “A causes B”. It means “A is associated with B” (co-occurrence) or “A is related to a reference anchor”.

---

## 0. Normative language

The keywords **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used in the usual normative sense (requirements vs recommendations).

---

## 1. Inputs and outputs

### 1.1 Inputs

Paradox Diagram v0 is derived from:

- **Required**
  - `paradox_core_v0.json` (Paradox Core v0 artifact)
- **Optional**
  - `paradox_edges_v0.jsonl` (if additional edge evidence fields are needed)

The diagram layer **MUST NOT** require network calls.

### 1.2 Output

- `paradox_diagram_v0.json` — the canonical diagram artifact (machine + reviewer tooling)
- (separate step, later) SVG/HTML rendering derived **only** from `paradox_diagram_v0.json`

---

## 2. Core principles

### 2.1 Evidence-first, non-causal
- Co-occurrence edges express **association / co-occurrence only**.
- The diagram **does not** introduce new truth claims; it re-expresses already observed relationships.

### 2.2 Reference-oriented “orientation”
The “orientation” of the diagram is **not** defined as arrow direction between atoms.

Instead, orientation is defined **only relative to a reference anchor** (e.g., “release decision”; later versions may support multiple anchors).

This prevents the most common failure mode: people reading `atom A → atom B` as causality.

### 2.3 Deterministic and audit-compatible
Given identical inputs (including pinned runner + dependencies upstream), the diagram output **MUST** be stable:

- canonical ordering (nodes/edges),
- stable IDs (hash-based; specified in this document),
- no timestamps or run-dependent counters.

### 2.4 CI-neutral by default
Paradox Diagram v0 is diagnostic. It **MUST NOT** flip Core PASS/FAIL decisions unless a **separate policy** explicitly promotes it.

### 2.5 Pages is static
GitHub Pages (or any static surface) **publishes** diagram artifacts but **MUST NOT** compute or reinterpret semantics.

---

## 3. Terminology

### 3.1 Reference (anchor)
A **reference** is a stable anchor that nodes can be related to, such as:

- `ref.release_decision` (the minimal v0 reference anchor)

v0 **MUST** include at least one reference anchor. Multiple anchors are a later-version concern.

### 3.2 Node
A **node** is either:
- an **atom node** (from Paradox Core; identified by `core_atom_id`), or
- a **reference node** (a dedicated anchor; identified by `ref_id`).

### 3.3 Edge
There are two edge kinds in v0:

1) **`co_occurrence`** edge  
   Association only, **undirected** by contract.

2) **`reference_relation`** edge  
   Relates an atom node to a reference node; **directed only as “atom → reference”** (reference-oriented, not causal).

---

## 4. Semantics and invariants (v0)

### 4.1 Co-occurrence edges MUST be undirected
A co-occurrence edge connects two atom nodes:

- it is represented as an unordered pair `{a, b}`,
- any serialization **MUST** canonicalize it with `a <= b` lexicographically,
- it may carry weight/evidence fields, but **MUST NOT** carry direction.

**Normative rules (v0):**
- `kind == "co_occurrence"` edges are **undirected**.
- `co_occurrence` edges **MUST NOT** include `directed: true`.
- Renderers **MUST NOT** draw arrowheads for `co_occurrence`.

> Implementation note: if an internal implementation stores `src/dst`, those are **canonical endpoints only** (not direction), and the artifact shape **still** follows the undirected contract.

### 4.2 Directed edges are ONLY allowed as reference relations (atom → reference)
Any directed edge in v0 **MUST** be of kind `reference_relation` and **MUST** connect exactly one atom node with exactly one reference node.

**Normative rules (v0):**
- `kind == "reference_relation"` edges are **reference-oriented** and represent: **`a -> b`**.
- For `reference_relation`:
  - `a` **MUST** be an atom node,
  - `b` **MUST** be a reference node,
  - if the `directed` field is present, it **MUST** be `true`.

This is the strongest mechanical guardrail against accidental causality. The only arrow allowed is **toward a reference anchor**.

### 4.3 Orientation lives in reference-relative fields (not atom→atom arrows)
For atom nodes, the diagram **MAY** include a reference-relative relation block.

**Recommended v0 shape (node-level):**
- `relation_to_reference.ref_id` — the reference anchor ID (e.g., `ref.release_decision`)
- `relation_to_reference.orientation` — enum:
  - `unknown` (default in v0; safest)
  - `supports_reference` (node supports/explains the reference state)
  - `challenges_reference` (node is in tension with the reference state)
  - `mixed` (both support and challenge are present)
- `relation_to_reference.weight` — evidence strength for this node→reference relation (see 4.4)

The presence of a `reference_relation` edge and the presence of `relation_to_reference` on a node are complementary:
- `reference_relation` is the **graph edge** (connectivity)
- `relation_to_reference` is the **reference-relative annotation** (orientation semantics)

### 4.4 Weight: meaning, range, and rounding
Weights are **not** causal strength. They are either:
- association strength (for `co_occurrence`), or
- evidence strength (for `reference_relation` / `relation_to_reference`).

**Constraints (v0):**
- `weight` **MUST** satisfy `weight >= 0.0`
- **Recommended range:** `[0.0, 1.0]`

**Determinism rule (v0):**
- Weights **MUST** be emitted as JSON numbers rounded to **6 decimals** at emission time.

### 4.5 Semantics vs render hints
To keep UI/Pages stable and prevent “render becomes meaning”, the artifact **MUST** separate meaning from layout.

**Semantic fields (meaning):** used to interpret the diagram (must be stable across renderers)
- node kind, `core_atom_id`, rank, `relation_to_reference`
- edge kind, endpoints, weights, evidence fields
- references list, inputs/provenance, non-causal notes

**Render-hint fields (UI-only):** optional hints (must not be required for meaning)
- layer labels (`reference` vs `atoms`)
- order keys (e.g. `rank`)
- group tags

**Non-goal (v0):** pixel coordinates are not part of the semantic artifact.

---

## 5. Stable IDs (normative)

IDs are stable only if the spec defines the exact hashing input.

### 5.1 Canonical string encoding
- UTF-8
- newline separator: `\n`
- no extra whitespace
- exact prefixes as specified below
- hex output is lowercase
- take the first 16 hex characters of the SHA-256 digest

### 5.2 Node IDs
**Reference node ID**
- `node_id = "r_" + sha256("ref\n" + ref_id).hex[:16]`

**Atom node ID**
- `node_id = "n_" + sha256("atom\n" + core_atom_id).hex[:16]`

### 5.3 Edge IDs
**Co-occurrence edge ID (undirected)**
- let `a_id = min(node_a, node_b)` and `b_id = max(node_a, node_b)`
- `edge_id = "e_" + sha256("co_occurrence\n" + a_id + "\n" + b_id).hex[:16]`

**Reference relation edge ID (atom → reference)**
- `edge_id = "e_" + sha256("reference_relation\n" + atom_node_id + "\n" + ref_node_id).hex[:16]`

---

## 6. Deterministic ordering (normative)

To keep diffs clean and avoid “random ordering” drift:

- `references[]` sorted by `ref_id` asc
- `nodes[]` canonical order:
  1) reference nodes by `ref_id` asc
  2) atom nodes by `(rank asc, core_atom_id asc)`
- `edges[]` canonical order:
  1) `co_occurrence` edges by `(a_id asc, b_id asc, edge_id asc)`
  2) `reference_relation` edges by `(a_id asc, b_id asc, edge_id asc)`  
     (note: for reference edges, `a_id` is the atom node id, `b_id` is the reference node id)

---

## 7. Run context and audit constraints

The diagram may pass through `run_context`, but **MUST NOT** include non-deterministic values.

**Forbidden in deterministic artifacts:**
- wall-clock timestamps,
- CI run numbers,
- non-pinned random seeds,
- any data that changes while inputs remain identical.

**Required for audit friendliness:**
- `inputs.*.sha256` for each consumed input file

---

## 8. Minimal example (shape only)

This is not a complete schema, just a shape anchor for implementation and review.

```json
{
  "schema": "PULSE_paradox_diagram_v0",
  "version": 0,
  "inputs": {
    "paradox_core_v0": { "sha256": "<hex>" }
  },
  "references": [
    { "ref_id": "ref.release_decision", "kind": "decision" }
  ],
  "nodes": [
    {
      "node_id": "r_<stable>",
      "kind": "reference",
      "ref_id": "ref.release_decision"
    },
    {
      "node_id": "n_<stable>",
      "kind": "atom",
      "core_atom_id": "a_01",
      "rank": 1,
      "relation_to_reference": {
        "ref_id": "ref.release_decision",
        "orientation": "unknown",
        "weight": 0.0
      },
      "render_hints": {
        "layer": "atoms",
        "order": 1
      }
    }
  ],
  "edges": [
    {
      "edge_id": "e_<stable>",
      "kind": "co_occurrence",
      "a": "n_<stable>",
      "b": "n_<stable>",
      "weight": 0.42
    },
    {
      "edge_id": "e_<stable>",
      "kind": "reference_relation",
      "a": "n_<stable>",
      "b": "r_<stable>",
      "directed": true,
      "weight": 0.10
    }
  ],
  "notes": [
    {
      "code": "NON_CAUSAL",
      "text": "This artifact expresses associations (co-occurrence / reference-relative relations); it does not assert causality."
    },
    {
      "code": "CI_NEUTRAL_DEFAULT",
      "text": "Paradox Diagram v0 is diagnostic by default and must not flip CI release gates unless explicitly promoted by policy."
    }
  ]
}
```

---

## 9. Non-goals (v0)

- No causal inference.
- No release gating.
- No Pages-side computation (Pages publishes static outputs only).
- No pixel-precise layout embedded as semantics.

---

## 10. Next steps (planned)

- `schemas/PULSE_paradox_diagram_v0.schema.json`
- `scripts/paradox_diagram_from_core_v0.py` (core → diagram JSON)
- `scripts/check_paradox_diagram_v0_contract.py` + fixtures + tests
- deterministic render from diagram JSON + golden SVG tests
- include diagram artifacts in reviewer bundle and Pages publish
