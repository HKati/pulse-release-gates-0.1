#!/usr/bin/env python3
"""
render_paradox_diagram_svg_v0.py

Deterministic SVG renderer for Paradox Diagram v0.

Input:
  --in   paradox_diagram_v0.json (or wrapper JSON containing it)

Output:
  --out  paradox_diagram_v0.svg

Design goals:
  - deterministic layout and serialization (no timestamps)
  - render derives ONLY from the diagram artifact (no --edges required)
  - non-causal guardrails:
      * co_occurrence edges are rendered without arrowheads
      * reference_relation edges render arrow toward the reference node only
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DIAGRAM_SCHEMA = "PULSE_paradox_diagram_v0"


def _fail(msg: str) -> None:
    raise SystemExit(msg)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_diagram_obj(raw: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the diagram artifact itself (schema == PULSE_paradox_diagram_v0), or
      - a wrapper object containing a nested diagram artifact (possibly deeply nested).

    Deterministic unwrap:
      - dict keys scanned in sorted order
      - lists scanned in index order
    """
    if not isinstance(raw, dict):
        _fail("Input must be a JSON object (dict).")

    def walk(x: Any) -> Optional[Dict[str, Any]]:
        if isinstance(x, dict):
            if x.get("schema") == DIAGRAM_SCHEMA:
                return x
            for k in sorted(x.keys(), key=lambda kk: str(kk)):
                res = walk(x.get(k))
                if res is not None:
                    return res
        elif isinstance(x, list):
            for item in x:
                res = walk(item)
                if res is not None:
                    return res
        return None

    found = walk(raw)
    if found is None:
        _fail(f"Could not locate diagram object with schema == {DIAGRAM_SCHEMA}.")
    return found


def _safe_int(x: Any, default: int) -> int:
    if isinstance(x, bool):
        return default
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        try:
            return int(x)
        except Exception:
            return default
    return default


def _node_sort_key(n: Dict[str, Any]) -> Tuple[int, str, int, str]:
    # reference nodes first by ref_id asc, then atoms by (rank asc, core_atom_id asc)
    if n.get("kind") == "reference":
        return (0, str(n.get("ref_id", "")), 0, "")
    rank = _safe_int(n.get("rank"), 10**9)
    return (1, "", rank, str(n.get("core_atom_id", "")))


def _edge_group(kind: str) -> int:
    if kind == "co_occurrence":
        return 0
    if kind == "reference_relation":
        return 1
    return 9


def _edge_sort_key(e: Dict[str, Any]) -> Tuple[int, str, str, str]:
    return (
        _edge_group(str(e.get("kind", ""))),
        str(e.get("a", "")),
        str(e.get("b", "")),
        str(e.get("edge_id", "")),
    )


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _fmt_weight(w: Any) -> str:
    # stable, compact weight formatting for display only (not semantic)
    try:
        x = float(w)
    except Exception:
        return ""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input paradox_diagram_v0.json (or wrapper)")
    ap.add_argument("--out", dest="out_path", required=True, help="Output SVG path")
    ap.add_argument("--title", default="Paradox Diagram v0", help="SVG title (default: Paradox Diagram v0)")

    # Layout knobs (kept simple, deterministic defaults)
    ap.add_argument("--width", type=int, default=1200, help="SVG width (default: 1200)")
    ap.add_argument("--node-w", type=int, default=520, help="Node width (default: 520)")
    ap.add_argument("--node-h", type=int, default=64, help="Node height (default: 64)")
    ap.add_argument("--row-gap", type=int, default=18, help="Vertical gap between nodes (default: 18)")
    ap.add_argument("--col-gap", type=int, default=120, help="Horizontal gap between columns (default: 120)")
    ap.add_argument("--margin", type=int, default=24, help="Outer margin (default: 24)")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    if not in_path.exists():
        _fail(f"Input not found: {in_path}")

    raw = _load_json(in_path)
    diagram = _find_diagram_obj(raw)

    nodes = diagram.get("nodes")
    edges = diagram.get("edges")

    if not isinstance(nodes, list) or not nodes:
        _fail("Diagram nodes must be a non-empty list.")
    if not isinstance(edges, list):
        edges = []

    # canonical order for deterministic rendering
    node_objs: List[Dict[str, Any]] = [n for n in nodes if isinstance(n, dict)]
    node_objs.sort(key=_node_sort_key)

    ref_nodes = [n for n in node_objs if n.get("kind") == "reference"]
    atom_nodes = [n for n in node_objs if n.get("kind") == "atom"]

    # Build position maps
    margin = int(args.margin)
    node_w = int(args.node_w)
    node_h = int(args.node_h)
    row_gap = int(args.row_gap)
    col_gap = int(args.col_gap)

    x_ref = margin
    x_atom = margin + node_w + col_gap

    # Height based on max rows in either column
    rows = max(len(ref_nodes), len(atom_nodes), 1)
    height = margin * 2 + rows * node_h + (rows - 1) * row_gap

    # Keep width at least enough for two columns
    width = max(int(args.width), x_atom + node_w + margin)

    pos: Dict[str, Tuple[int, int]] = {}
    for i, n in enumerate(ref_nodes):
        nid = str(n.get("node_id", ""))
        y = margin + i * (node_h + row_gap)
        if nid:
            pos[nid] = (x_ref, y)

    for i, n in enumerate(atom_nodes):
        nid = str(n.get("node_id", ""))
        y = margin + i * (node_h + row_gap)
        if nid:
            pos[nid] = (x_atom, y)

    # Prepare edges (sorted deterministically)
    edge_objs: List[Dict[str, Any]] = [e for e in edges if isinstance(e, dict)]
    edge_objs.sort(key=_edge_sort_key)

    title = str(args.title)

    lines: List[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append(f"  <title>{_esc(title)}</title>")
    lines.append("  <defs>")
    # Arrow marker for reference-only edges
    lines.append(
        '    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
    )
    lines.append('      <path d="M 0 0 L 10 5 L 0 10 z" fill="#111" />')
    lines.append("    </marker>")
    lines.append("  </defs>")

    # Background
    lines.append(f'  <rect x="0" y="0" width="{width}" height="{height}" fill="#fff" />')

    # --- Edges first (behind nodes) ---
    lines.append('  <g id="edges" stroke="#111" stroke-width="2" fill="none">')

    def mid_left(nid: str) -> Tuple[float, float]:
        x, y = pos[nid]
        return (x, y + node_h / 2.0)

    def mid_right(nid: str) -> Tuple[float, float]:
        x, y = pos[nid]
        return (x + node_w, y + node_h / 2.0)

    def center(nid: str) -> Tuple[float, float]:
        x, y = pos[nid]
        return (x + node_w / 2.0, y + node_h / 2.0)

    for e in edge_objs:
        kind = str(e.get("kind", ""))
        a = str(e.get("a", ""))
        b = str(e.get("b", ""))
        if not a or not b:
            continue
        if a not in pos or b not in pos:
            continue

        if kind == "reference_relation":
            x1, y1 = mid_left(a)   # atom left edge
            x2, y2 = mid_right(b)  # reference right edge
            lines.append(
                f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#arrow)" />'
            )

        elif kind == "co_occurrence":
            x1, y1 = center(a)
            x2, y2 = center(b)
            lines.append(f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" opacity="0.75" />')

    lines.append("  </g>")

    # --- Nodes ---
    lines.append('  <g id="nodes" stroke="#111" stroke-width="2" fill="#fff">')

    def draw_node(n: Dict[str, Any]) -> None:
        nid = str(n.get("node_id", ""))
        if not nid or nid not in pos:
            return
        x, y = pos[nid]
        kind = str(n.get("kind", ""))

        lines.append(f'    <rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="10" ry="10" />')

        if kind == "reference":
            label1 = str(n.get("ref_id", "reference"))
            label2 = "reference"
        else:
            core_atom_id = str(n.get("core_atom_id", "atom"))
            rank = n.get("rank")
            label1 = f"{rank}. {core_atom_id}" if isinstance(rank, int) else core_atom_id

            label2 = ""
            rel = n.get("relation_to_reference")
            if isinstance(rel, dict):
                orient = rel.get("orientation")
                if isinstance(orient, str) and orient and orient != "unknown":
                    label2 = f"orientation: {orient}"
                else:
                    w = _fmt_weight(rel.get("weight"))
                    if w:
                        label2 = f"ref-weight: {w}"

        tx = x + 14
        ty1 = y + 24
        ty2 = y + 46

        lines.append(
            f'    <text x="{tx}" y="{ty1}" font-size="14" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, &quot;Liberation Mono&quot;, &quot;Courier New&quot;, monospace">{_esc(label1)}</text>'
        )
        if label2:
            lines.append(
                f'    <text x="{tx}" y="{ty2}" font-size="12" opacity="0.85" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, &quot;Liberation Mono&quot;, &quot;Courier New&quot;, monospace">{_esc(label2)}</text>'
            )

    for n in node_objs:
        draw_node(n)

    lines.append("  </g>")

    lines.append(
        '  <g id="note" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, &quot;Liberation Mono&quot;, &quot;Courier New&quot;, monospace" font-size="12" opacity="0.85">'
    )
    lines.append(f'    <text x="{margin}" y="{height - 10}">Non-causal: co_occurrence = association only; arrows are reference-only.</text>')
    lines.append("  </g>")

    lines.append("</svg>")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
