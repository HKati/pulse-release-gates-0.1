#!/usr/bin/env python3
"""
paradox_core_projection_v0.py

Deterministic "core projection" builder for the Paradox field.

Inputs:
  - paradox_field_v0.json (atoms)
  - paradox_edges_v0.jsonl (edges; optional)
Output:
  - paradox_core_v0.json (stable ordering, stable IDs)

Design goals:
  - CI-neutral (diagnostic overlay)
  - evidence-first, non-causal edges
  - deterministic output (no wall-clock timestamps; stable ordering; stable IDs)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCHEMA_NAME = "PULSE_paradox_core_v0"
SCHEMA_VERSION = "v0"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _unwrap_paradox_field_v0(field: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept both formats:
    - unwrapped: {"schema": "...", "atoms": [...], ...}
    - wrapped:   {"paradox_field_v0": {"schema": "...", "atoms": [...], ...}, ...}

    Many repo scripts/adapters emit the wrapped form; we must support it to avoid
    silently producing an empty core on normal inputs.
    """
    inner = field.get("paradox_field_v0")
    if isinstance(inner, dict):
        return inner
    return field


def _stable_edge_id(src: str, dst: str, edge_type: str) -> str:
    # Minimal stable ID: endpoints + type. (Weight/evidence are properties, not identity.)
    s = f"{src}\n{dst}\n{edge_type}".encode("utf-8")
    return "e_" + _sha256_bytes(s)[:16]


def _get_atom_id(atom: Dict[str, Any]) -> str:
    if "atom_id" in atom and isinstance(atom["atom_id"], str):
        return atom["atom_id"]
    if "id" in atom and isinstance(atom["id"], str):
        return atom["id"]
    raise ValueError("Atom missing atom_id/id string field")


def _get_numeric(atom: Dict[str, Any], key: str) -> float:
    v = atom.get(key, 0.0)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _select_metric(metric: str, atom: Dict[str, Any]) -> float:
    # v0: prefer explicit metric; missing -> 0.0 (still deterministic)
    return _get_numeric(atom, metric)


def _canonical_json_dump(obj: Any) -> str:
    # Stable JSON formatting for determinism comparisons.
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def build_core(
    field: Dict[str, Any],
    edges: List[Dict[str, Any]],
    k: int,
    metric: str,
) -> Dict[str, Any]:
    field = _unwrap_paradox_field_v0(field)

    atoms = field.get("atoms", [])
    if not isinstance(atoms, list):
        raise ValueError("Field 'atoms' must be a list")

    # Rank atoms by metric desc, then atom_id asc (deterministic tie-break).
    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    missing_metric = 0

    for a in atoms:
        if not isinstance(a, dict):
            continue
        atom_id = _get_atom_id(a)
        score = _select_metric(metric, a)
        if metric not in a:
            missing_metric += 1
        # rounding to reduce float noise (deterministic representation)
        score = float(f"{score:.6f}")
        scored.append((score, atom_id, a))

    scored.sort(key=lambda t: (-t[0], t[1]))

    k_eff = max(0, int(k))
    core_scored = scored[:k_eff] if k_eff > 0 else []

    core_atom_ids = [atom_id for (_, atom_id, _) in core_scored]
    core_set = set(core_atom_ids)

    # Build core atoms with rank and score embedded (without losing evidence fields).
    core_atoms: List[Dict[str, Any]] = []
    for i, (score, atom_id, a) in enumerate(core_scored, start=1):
        core_atom = dict(a)  # keep evidence fields intact
        core_atom["atom_id"] = atom_id  # normalize key
        core_atom["core_rank"] = i
        core_atom["core_score"] = score
        core_atoms.append(core_atom)

    # Canonical order for core atoms: rank asc, then atom_id asc
    core_atoms.sort(key=lambda x: (int(x["core_rank"]), str(x["atom_id"])))

    # Filter edges to induced subgraph on core atoms.
    core_edges: List[Dict[str, Any]] = []
    total_edges = 0

    for e in edges:
        if not isinstance(e, dict):
            continue
        total_edges += 1

        src = e.get("src_atom_id", e.get("src"))
        dst = e.get("dst_atom_id", e.get("dst"))
        edge_type = e.get("edge_type", e.get("type", "co_occurs"))

        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        if not isinstance(edge_type, str):
            edge_type = "co_occurs"

        if src not in core_set or dst not in core_set:
            continue

        edge_id = e.get("edge_id", e.get("id"))
        if not isinstance(edge_id, str) or not edge_id.strip():
            edge_id = _stable_edge_id(src, dst, edge_type)

        out_e = dict(e)
        out_e["edge_id"] = edge_id
        out_e["src_atom_id"] = src
        out_e["dst_atom_id"] = dst
        out_e["edge_type"] = edge_type
        core_edges.append(out_e)

    # Canonical order for edges: src, dst, type, edge_id
    core_edges.sort(
        key=lambda x: (
            str(x.get("src_atom_id", "")),
            str(x.get("dst_atom_id", "")),
            str(x.get("edge_type", "")),
            str(x.get("edge_id", "")),
        )
    )

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "selection": {
            "k": k_eff,
            "metric": metric,
            "method": "topk_metric_then_atom_id",
            "tie_break": "atom_id_lex_asc",
            "edge_policy": "induced_subgraph_on_core_atoms",
            "non_causal_edges": True,
        },
        "inputs": {
            "field_schema": field.get("schema", field.get("schema_version", "unknown")),
        },
        "run_context": field.get("run_context", {}),
        # Anchor may exist in some field outputs; pass through if present.
        "anchor": field.get("anchor", field.get("reference", None)),
        "stats": {
            "atoms_total": len([a for a in atoms if isinstance(a, dict)]),
            "edges_total": total_edges,
            "core_atoms": len(core_atoms),
            "core_edges": len(core_edges),
            "missing_metric_atoms": missing_metric,
        },
        "atoms": core_atoms,
        "edges": core_edges,
        "core": {
            "atom_ids": [a["atom_id"] for a in core_atoms],
            "edge_ids": [e["edge_id"] for e in core_edges],
        },
        "notes": [
            "Edges are co-occurrence/association only (non-causal) in v0.",
            "This artifact is diagnostic by default and must not flip CI release gates unless explicitly promoted.",
        ],
    }

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--edges", required=False, help="Path to paradox_edges_v0.jsonl (optional)")
    ap.add_argument("--out", required=True, help="Output path for paradox_core_v0.json")
    ap.add_argument("--k", type=int, default=12, help="Core size (top-k atoms). Default: 12")
    ap.add_argument(
        "--metric",
        default="severity",
        help="Atom metric used for ranking (default: severity). Missing values are treated as 0.0.",
    )
    args = ap.parse_args()

    field_path = Path(args.field)
    edges_path = Path(args.edges) if args.edges else None
    out_path = Path(args.out)

    field = _load_json(field_path)
    edges = _load_jsonl(edges_path) if edges_path else []

    out_obj = build_core(field=field, edges=edges, k=args.k, metric=args.metric)

    # Add deterministic input hashes (safe for determinism).
    out_obj["inputs"]["field_sha256"] = _sha256_file(field_path)
    if edges_path and edges_path.exists():
        out_obj["inputs"]["edges_sha256"] = _sha256_file(edges_path)
    else:
        out_obj["inputs"]["edges_sha256"] = None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_canonical_json_dump(out_obj), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

