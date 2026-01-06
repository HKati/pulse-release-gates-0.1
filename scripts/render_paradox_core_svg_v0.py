#!/usr/bin/env python3
"""
render_paradox_core_svg_v0.py

Deterministic SVG renderer for the Paradox Core projection artifact.

Input:
  - paradox_core_v0.json

Output:
  - paradox_core_v0.svg

Design goals:
  - CI-neutral (diagnostic overlay only)
  - deterministic output (no timestamps; stable ordering; stable numeric formatting)
  - pinned toolchain by design (no external layout engines; no extra deps)
  - explicitly non-causal edges (association/co-occurrence only in v0)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _shorten(s: str, n: int) -> str:
    s = s.strip()
    if n <= 0 or len(s) <= n:
        return s
    return s[: max(0, n - 1)].rstrip() + "…"


def _xml_escape(s: str) -> str:
    # Minimal XML escaping for deterministic SVG output.
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _canonical_atom_sort_key(a: Dict[str, Any]) -> Tuple[int, str]:
    try:
        r = int(a.get("core_rank"))
    except (TypeError, ValueError):
        r = 10**9
    return (r, _as_str(a.get("atom_id")))


def _canonical_edge_sort_key(e: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        _as_str(e.get("src_atom_id")),
        _as_str(e.get("dst_atom_id")),
        _as_str(e.get("edge_type")),
        _as_str(e.get("edge_id")),
    )


def _get_atom_ref(a: Dict[str, Any]) -> str:
    if isinstance(a.get("gate_id"), str) and a["gate_id"]:
        return a["gate_id"]
    if isinstance(a.get("metric_id"), str) and a["metric_id"]:
        return a["metric_id"]
    gate_ids = a.get("gate_ids")
    if isinstance(gate_ids, list):
        xs = [x for x in gate_ids if isinstance(x, str) and x.strip()]
        xs.sort()
        if xs:
            return ",".join(xs[:5]) + ("…" if len(xs) > 5 else "")
    return ""


def _fmt_float(v: Any, digits: int = 3) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return f"{f:.{digits}f}"


def render_svg(
    core: Dict[str, Any],
    width: int = 1200,
    node_w: int = 520,
    node_h: int = 64,
    pad: int = 24,
    gap_y: int = 16,
    font_size: int = 13,
    max_summary_len: int = 90,
) -> str:
    atoms_raw = core.get("atoms")
    edges_raw = core.get("edges")

    if not isinstance(atoms_raw, list):
        raise ValueError("core.atoms must be a list")
    if not isinstance(edges_raw, list):
        raise ValueError("core.edges must be a list")

    atoms: List[Dict[str, Any]] = [a for a in atoms_raw if isinstance(a, dict)]
    edges: List[Dict[str, Any]] = [e for e in edges_raw if isinstance(e, dict)]

    atoms.sort(key=_canonical_atom_sort_key)
    edges.sort(key=_canonical_edge_sort_key)

    # Header height (used as y-offset for the diagram body).
    # Must be accounted for in the SVG height to avoid clipping.
    header_h = pad + 120
    y_offset = header_h

    # Deterministic vertical layout: node i at y = pad + i*(node_h+gap_y)
    n = len(atoms)
    body_h = pad * 2 + (n * node_h) + (max(0, n - 1) * gap_y)

    # Include header offset in the final SVG height (fixes clipping).
    height = max(y_offset + body_h, y_offset + 240)

    # Node x positions
    x0 = pad
    x1 = x0 + node_w
    cx = x0 + node_w // 2

    # Build lookup for atom centers
    centers: Dict[str, Tuple[int, int]] = {}
    for i, a in enumerate(atoms):
        atom_id = _as_str(a.get("atom_id"))
        y = pad + i * (node_h + gap_y)
        cy = y + node_h // 2
        centers[atom_id] = (cx, cy)

    schema = _as_str(core.get("schema"))
    version = _as_str(core.get("version"))

    selection = core.get("selection") if isinstance(core.get("selection"), dict) else {}
    metric = _as_str(selection.get("metric"))
    k = _as_str(selection.get("k"))

    inputs = core.get("inputs") if isinstance(core.get("inputs"), dict) else {}
    field_sha = _as_str(inputs.get("field_sha256"))
    edges_sha = _as_str(inputs.get("edges_sha256"))

    run_context = core.get("run_context") if isinstance(core.get("run_context"), dict) else {}
    run_id = _as_str(run_context.get("run_id"))

    # SVG header
    out: List[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )

    # Deterministic style block (no external fonts)
    out.append("<style>")
    out.append("  .title { font-family: monospace; font-size: 16px; font-weight: 700; }")
    out.append("  .meta  { font-family: monospace; font-size: 12px; opacity: 0.85; }")
    out.append("  .node  { fill: #ffffff; stroke: #111111; stroke-width: 1; }")
    out.append("  .edge  { stroke: #111111; stroke-width: 1; opacity: 0.70; }")
    out.append("  .text  { font-family: monospace; font-size: %dpx; }" % font_size)
    out.append("  .small { font-family: monospace; font-size: 11px; opacity: 0.85; }")
    out.append("</style>")

    # Background
    out.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>')

    # Header / metadata (deterministic, no timestamps)
    title = "Paradox Core v0 — SVG (diagnostic, non-causal)"
    out.append(f'<text x="{pad}" y="{pad}" class="title">{_xml_escape(title)}</text>')

    meta_line_1 = f"schema={schema} version={version} metric={metric} k={k}"
    meta_line_2 = f"run_id={run_id}" if run_id else "run_id="
    meta_line_3 = f"field_sha256={field_sha}"
    meta_line_4 = f"edges_sha256={edges_sha if edges_sha else 'null'}"

    out.append(f'<text x="{pad}" y="{pad + 20}" class="meta">{_xml_escape(meta_line_1)}</text>')
    out.append(f'<text x="{pad}" y="{pad + 38}" class="meta">{_xml_escape(meta_line_2)}</text>')
    out.append(f'<text x="{pad}" y="{pad + 56}" class="meta">{_xml_escape(meta_line_3)}</text>')
    out.append(f'<text x="{pad}" y="{pad + 74}" class="meta">{_xml_escape(meta_line_4)}</text>')

    note = "Edges are association/co-occurrence only (non-causal) in v0. CI-neutral by default."
    out.append(f'<text x="{pad}" y="{pad + 96}" class="small">{_xml_escape(note)}</text>')

    # Draw edges first (behind nodes)
    for e in edges:
        src = _as_str(e.get("src_atom_id"))
        dst = _as_str(e.get("dst_atom_id"))
        if src not in centers or dst not in centers:
            continue
        (x_src, y_src) = centers[src]
        (x_dst, y_dst) = centers[dst]

        # Skip self-edges in v0 render
        if src == dst:
            continue

        # Map center coords into shifted coordinates
        y_src_s = y_src + y_offset
        y_dst_s = y_dst + y_offset

        x_src_s = x1
        x_dst_s = x0

        out.append(
            f'<line class="edge" x1="{x_src_s}" y1="{y_src_s}" x2="{x_dst_s}" y2="{y_dst_s}"/>'
        )

    # Draw nodes
    for i, a in enumerate(atoms):
        atom_id = _as_str(a.get("atom_id"))
        rank = _as_str(a.get("core_rank"))
        score = _fmt_float(a.get("core_score"))
        ref = _get_atom_ref(a)
        kind = _as_str(a.get("kind", a.get("atom_kind", "")))

        summary = _as_str(a.get("summary", a.get("title", a.get("label", ""))))
        summary = _shorten(summary, max_summary_len)

        y = y_offset + pad + i * (node_h + gap_y)
        out.append(
            f'<rect class="node" x="{x0}" y="{y}" width="{node_w}" height="{node_h}" rx="8" ry="8" id="{_xml_escape("atom-" + atom_id)}"/>'
        )

        # Text lines (deterministic positions)
        tx = x0 + 12
        ty = y + 20
        line1 = f"[{rank}] {atom_id}  score={score}"
        line2 = f"ref={ref}  kind={kind}" if (ref or kind) else ""
        line3 = summary

        out.append(f'<text class="text" x="{tx}" y="{ty}">{_xml_escape(line1)}</text>')
        if line2:
            out.append(f'<text class="small" x="{tx}" y="{ty + 18}">{_xml_escape(line2)}</text>')
            out.append(f'<text class="small" x="{tx}" y="{ty + 36}">{_xml_escape(line3)}</text>')
        else:
            out.append(f'<text class="small" x="{tx}" y="{ty + 18}">{_xml_escape(line3)}</text>')

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input paradox_core_v0.json")
    ap.add_argument("--out", required=True, help="Output SVG path")
    ap.add_argument("--width", type=int, default=1200, help="SVG width (px). Default: 1200")
    ap.add_argument("--node-w", type=int, default=520, help="Node width (px). Default: 520")
    ap.add_argument("--node-h", type=int, default=64, help="Node height (px). Default: 64")
    ap.add_argument("--max-summary-len", type=int, default=90, help="Max summary length. Default: 90")
    args = ap.parse_args()

    inp = Path(args.inp)
    outp = Path(args.out)

    core = _load_json(inp)
    svg = render_svg(
        core,
        width=int(args.width),
        node_w=int(args.node_w),
        node_h=int(args.node_h),
        max_summary_len=int(args.max_summary_len),
    )

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

