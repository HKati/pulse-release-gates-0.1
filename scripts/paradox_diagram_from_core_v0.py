#!/usr/bin/env python3
"""
Paradox Diagram v0 builder (Core -> Diagram).

Diagnostic only. Non-causal by contract.
- Co-occurrence edges are undirected (canonical endpoint order).
- Directed edges (if emitted) are reference-only: atom -> reference.
- Deterministic: stable IDs, canonical ordering, no wall-clock fields.

Usage:
  python scripts/paradox_diagram_from_core_v0.py \
    --core out/paradox_core_v0.json \
    --out  out/paradox_diagram_v0.json

Optional:
  --edges out/paradox_edges_v0.jsonl   (record input sha256 only; no extra semantics in v0)
  --no-reference-edges                (do not emit atom->reference edges)
  --ref-id ref.release_decision       (override reference id; default is v0 standard)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA = "PULSE_paradox_diagram_v0"
VERSION = 0

DEFAULT_REF_ID = "ref.release_decision"
DEFAULT_REF_KIND = "decision"


def _sha256_hex_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_hex_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _id16(prefix: str, payload: str) -> str:
    # Spec: sha256 over canonical string; first 16 hex chars; lowercase.
    # payload must already include the exact "ref\n..." or "atom\n..." prefix rules.
    digest = _sha256_hex_of_text(payload)[:16]
    return f"{prefix}{digest}"


def node_id_reference(ref_id: str) -> str:
    return _id16("r_", "ref\n" + ref_id)


def node_id_atom(core_atom_id: str) -> str:
    return _id16("n_", "atom\n" + core_atom_id)


def edge_id_co_occurrence(a_node_id: str, b_node_id: str) -> str:
    a_id, b_id = sorted([a_node_id, b_node_id])
    return _id16("e_", "co_occurrence\n" + a_id + "\n" + b_id)


def edge_id_reference_relation(atom_node_id: str, ref_node_id: str) -> str:
    return _id16("e_", "reference_relation\n" + atom_node_id + "\n" + ref_node_id)


def _round6(x: float) -> float:
    # Determinism guard: reduce float noise.
    return float(f"{x:.6f}")


def _unwrap_paradox_core(obj: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the core artifact itself (schema == PULSE_paradox_core_v0), or
      - a wrapper object that contains the core artifact as a nested dict.
    """
    if not isinstance(obj, dict):
        raise ValueError("Core input must be a JSON object.")

    if obj.get("schema") == "PULSE_paradox_core_v0":
        return obj

    # Best-effort unwrap: find nested dict with the expected schema.
    # Deterministic search order: sorted keys.
    for k in sorted(obj.keys()):
        v = obj.get(k)
        if isinstance(v, dict) and v.get("schema") == "PULSE_paradox_core_v0":
            return v

    raise ValueError(
        "Could not locate Paradox Core v0 object. Expected schema == 'PULSE_paradox_core_v0' "
        "at top-level or as a nested object."
    )


@dataclass(frozen=True)
class CoreAtom:
    atom_id: str
    rank: int
    title: str


def _parse_core_atoms(core: Dict[str, Any]) -> List[CoreAtom]:
    atoms = core.get("atoms", [])
    if not isinstance(atoms, list):
        raise ValueError("core.atoms must be a list.")

    core_ids = []
    core_block = core.get("core", {})
    if isinstance(core_block, dict):
        core_ids = core_block.get("atom_ids", [])
    if core_ids is None:
        core_ids = []
    if not isinstance(core_ids, list):
        raise ValueError("core.core.atom_ids must be a list if present.")

    atoms_by_id: Dict[str, Dict[str, Any]] = {}
    for a in atoms:
        if isinstance(a, dict) and isinstance(a.get("atom_id"), str):
            atoms_by_id[a["atom_id"]] = a

    # If core_ids present, use it as the definitive core set (deterministic ordering + membership).
    if core_ids:
        result: List[CoreAtom] = []
        for idx, atom_id in enumerate(core_ids):
            if not isinstance(atom_id, str):
                raise ValueError("core.core.atom_ids must contain strings.")
            a = atoms_by_id.get(atom_id, {})
            title = a.get("title") if isinstance(a.get("title"), str) else atom_id
            rank_val = a.get("core_rank")
            if isinstance(rank_val, int) and rank_val >= 1:
                rank = rank_val
            else:
                rank = idx + 1
            result.append(CoreAtom(atom_id=atom_id, rank=rank, title=title))
        return result

    # Fallback: derive core set from atoms that have core_rank (stable sort).
    derived: List[CoreAtom] = []
    for a in atoms:
        if not isinstance(a, dict):
            continue
        atom_id = a.get("atom_id")
        rank_val = a.get("core_rank")
        if isinstance(atom_id, str) and isinstance(rank_val, int) and rank_val >= 1:
            title = a.get("title") if isinstance(a.get("title"), str) else atom_id
            derived.append(CoreAtom(atom_id=atom_id, rank=rank_val, title=title))

    derived.sort(key=lambda x: (x.rank, x.atom_id))
    if derived:
        return derived

    raise ValueError("Could not determine core atoms (no core.core.atom_ids and no atoms with core_rank).")


def _collect_core_edges(core: Dict[str, Any], core_atom_ids: set) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    Aggregate core edges into undirected co-occurrence pairs keyed by (a_node_id, b_node_id).
    Evidence is collected as a list (stable-sorted).
    """
    edges = core.get("edges", [])
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        raise ValueError("core.edges must be a list if present.")

    agg: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for e in edges:
        if not isinstance(e, dict):
            continue
        src = e.get("src_atom_id")
        dst = e.get("dst_atom_id")
        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        if src not in core_atom_ids or dst not in core_atom_ids:
            continue

        a = node_id_atom(src)
        b = node_id_atom(dst)
        a_id, b_id = sorted([a, b])

        # Keep evidence minimal but useful; avoid any wall-clock. Core doesn't carry timestamps by default.
        ev = {
            "core_edge_id": e.get("edge_id"),
            "edge_type": e.get("edge_type") if e.get("edge_type") is not None else e.get("type"),
            "rule": e.get("rule"),
            "severity": e.get("severity"),
            "tension_atom_id": e.get("tension_atom_id"),
            "run_context": e.get("run_context"),
        }

        # Determinism: normalize None values away (keep output compact and stable).
        ev_clean = {k: v for k, v in ev.items() if v is not None}

        agg.setdefault((a_id, b_id), []).append(ev_clean)

    # Determinism: stable-sort evidence lists.
    for k in list(agg.keys()):
        agg[k].sort(key=lambda x: (
            str(x.get("core_edge_id", "")),
            str(x.get("edge_type", "")),
            str(x.get("rule", "")),
            str(x.get("severity", "")),
            str(x.get("tension_atom_id", "")),
        ))

    return agg


def build_diagram(
    core_obj: Dict[str, Any],
    core_sha256: str,
    edges_sha256: Optional[str],
    core_path_hint: str,
    edges_path_hint: Optional[str],
    ref_id: str,
    emit_reference_edges: bool,
) -> Dict[str, Any]:
    core_atoms = _parse_core_atoms(core_obj)
    core_atom_ids = {a.atom_id for a in core_atoms}

    ref_node_id = node_id_reference(ref_id)

    references = [{"ref_id": ref_id, "kind": DEFAULT_REF_KIND}]

    nodes: List[Dict[str, Any]] = []
    # Reference node first (canonical).
    nodes.append(
        {
            "node_id": ref_node_id,
            "kind": "reference",
            "ref_id": ref_id,
            "render_hints": {
                "layer": "reference",
                "order": 0,
                "label": ref_id,
            },
        }
    )

    # Atom nodes (canonical by rank, then atom_id).
    atom_nodes: List[Dict[str, Any]] = []
    for a in core_atoms:
        nid = node_id_atom(a.atom_id)
        atom_nodes.append(
            {
                "node_id": nid,
                "kind": "atom",
                "core_atom_id": a.atom_id,
                "rank": int(a.rank),
                "relation_to_reference": {
                    "ref_id": ref_id,
                    "orientation": "unknown",
                    "weight": _round6(0.0),
                },
                "render_hints": {
                    "layer": "atoms",
                    "order": int(a.rank),
                    "label": a.title,
                },
            }
        )
    atom_nodes.sort(key=lambda x: (x["rank"], x["core_atom_id"]))
    nodes.extend(atom_nodes)

    # Co-occurrence edges (undirected, aggregated).
    pair_evidence = _collect_core_edges(core_obj, core_atom_ids)
    co_edges: List[Dict[str, Any]] = []
    for (a_id, b_id), ev_list in pair_evidence.items():
        co_edges.append(
            {
                "edge_id": edge_id_co_occurrence(a_id, b_id),
                "kind": "co_occurrence",
                "a": a_id,
                "b": b_id,
                "weight": _round6(1.0),
                "evidence": {
                    "core_edges": ev_list
                },
            }
        )
    co_edges.sort(key=lambda e: (e["a"], e["b"], e["edge_id"]))

    # Reference relation edges (optional): atom -> reference only.
    ref_edges: List[Dict[str, Any]] = []
    if emit_reference_edges:
        for a in core_atoms:
            atom_nid = node_id_atom(a.atom_id)
            ref_edges.append(
                {
                    "edge_id": edge_id_reference_relation(atom_nid, ref_node_id),
                    "kind": "reference_relation",
                    "a": atom_nid,
                    "b": ref_node_id,
                    "directed": True,
                    "weight": _round6(0.0),
                    "evidence": {
                        "note": "v0: default attachment to reference anchor (reference-oriented, non-causal)"
                    },
                }
            )
        ref_edges.sort(key=lambda e: (e["a"], e["b"], e["edge_id"]))

    notes = [
        {
            "code": "NON_CAUSAL",
            "text": (
                "This artifact expresses associations (co-occurrence) and reference-oriented relations; "
                "it does not assert causality."
            ),
        },
        {
            "code": "CI_NEUTRAL_DEFAULT",
            "text": (
                "Paradox Diagram v0 is diagnostic by default and must not flip CI release gates unless "
                "explicitly promoted by policy."
            ),
        },
    ]

    inputs: Dict[str, Any] = {
        "paradox_core_v0": {
            "sha256": core_sha256,
            "path_hint": core_path_hint,
        }
    }
    if edges_sha256 is not None:
        inputs["paradox_edges_v0"] = {
            "sha256": edges_sha256,
            "path_hint": edges_path_hint or "",
        }

    out: Dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "inputs": inputs,
        "references": sorted(references, key=lambda r: r["ref_id"]),
        "nodes": nodes,
        "edges": co_edges + ref_edges,
        "notes": notes,
    }

    # Pass-through run_context if present (must remain deterministic).
    rc = core_obj.get("run_context")
    if isinstance(rc, dict) and rc:
        out["run_context"] = rc

    # Final canonical ordering for nodes (defensive).
    def node_sort_key(n: Dict[str, Any]) -> Tuple[int, str]:
        if n.get("kind") == "reference":
            return (0, str(n.get("ref_id", "")))
        return (1, int(n.get("rank", 10**9)), str(n.get("core_atom_id", "")))

    out["nodes"].sort(key=node_sort_key)

    return out


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Paradox Diagram v0 from Paradox Core v0 (deterministic, non-causal).")
    p.add_argument("--core", required=True, help="Path to paradox_core_v0.json")
    p.add_argument("--out", required=True, help="Output path for paradox_diagram_v0.json")
    p.add_argument("--edges", default=None, help="Optional path to paradox_edges_v0.jsonl (recorded as input sha256 only)")
    p.add_argument("--ref-id", default=DEFAULT_REF_ID, help=f"Reference anchor id (default: {DEFAULT_REF_ID})")
    p.add_argument("--no-reference-edges", action="store_true", help="Do not emit atom->reference edges.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    core_path = Path(args.core)
    out_path = Path(args.out)
    edges_path = Path(args.edges) if args.edges else None

    if not core_path.exists():
        print(f"ERROR: core file not found: {core_path}", file=sys.stderr)
        return 2

    core_sha256 = _sha256_hex_of_file(core_path)

    edges_sha256: Optional[str] = None
    edges_hint: Optional[str] = None
    if edges_path is not None:
        if not edges_path.exists():
            print(f"ERROR: edges file not found: {edges_path}", file=sys.stderr)
            return 2
        edges_sha256 = _sha256_hex_of_file(edges_path)
        edges_hint = str(edges_path)

    try:
        with core_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        core_obj = _unwrap_paradox_core(raw)
    except Exception as e:
        print(f"ERROR: failed to read/parse core JSON: {e}", file=sys.stderr)
        return 2

    # Build deterministic diagram.
    diagram = build_diagram(
        core_obj=core_obj,
        core_sha256=core_sha256,
        edges_sha256=edges_sha256,
        core_path_hint=str(core_path),
        edges_path_hint=edges_hint,
        ref_id=str(args.ref_id),
        emit_reference_edges=(not bool(args.no_reference_edges)),
    )

    # Ensure output directory exists.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Canonical JSON dump: stable keys and stable indentation.
    payload = json.dumps(diagram, indent=2, sort_keys=True, ensure_ascii=False)
    out_path.write_text(payload + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
