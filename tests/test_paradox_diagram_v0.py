# ================================
# scripts/render_paradox_diagram_svg_v0.py
# ================================
#!/usr/bin/env python3
"""
Deterministic SVG renderer for Paradox Diagram v0.

Goals:
- Render is derived ONLY from paradox_diagram_v0.json (UI/Pages remain static).
- Non-causal: co_occurrence edges are undirected (no arrowheads).
- Reference-oriented: arrowheads only for reference_relation edges, pointing to the reference anchor.
- Deterministic: fixed layout rules, stable ordering, stable SVG formatting, no timestamps.

Layout (v0, pinned):
- Left column: primary reference node
- Right column: atom nodes ordered by (rank asc, core_atom_id asc)
- Vertical spacing is fixed (row gap)
- Edges use fixed routing rules:
  - co_occurrence: straight line between atom centers (no arrows)
  - reference_relation: polyline routed via a fixed elbow, marker-end at reference

Usage:
  python scripts/render_paradox_diagram_svg_v0.py \
    --in  out/paradox_diagram_v0.json \
    --out out/paradox_diagram_v0.svg
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DIAGRAM_SCHEMA = "PULSE_paradox_diagram_v0"


# Pinned layout constants (v0)
SVG_WIDTH = 900
TITLE_Y = 24

TOP_Y = 40
ROW_GAP = 80

NODE_W = 260
NODE_H = 36

X_REF = 40
X_ATOM = 420

FOOTER_H = 80


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _find_diagram_obj(raw: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the diagram artifact itself (schema == PULSE_paradox_diagram_v0), or
      - a wrapper object containing a nested diagram artifact.
    Deterministic unwrap: scan nested dicts in sorted key order.
    """
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object (dict).")

    if raw.get("schema") == DIAGRAM_SCHEMA:
        return raw

    for k in sorted(raw.keys()):
        v = raw.get(k)
        if isinstance(v, dict) and v.get("schema") == DIAGRAM_SCHEMA:
            return v

    raise ValueError(f"Could not locate diagram object with schema == {DIAGRAM_SCHEMA}.")


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _node_sort_key(n: Dict[str, Any]) -> Tuple[int, str, int, str]:
    if n.get("kind") == "reference":
        return (0, str(n.get("ref_id", "")), 0, "")
    return (1, "", int(n.get("rank", 10**9)), str(n.get("core_atom_id", "")))


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


def _label_for_node(n: Dict[str, Any]) -> str:
    rh = n.get("render_hints")
    if isinstance(rh, dict):
        lbl = rh.get("label")
        if isinstance(lbl, str) and lbl:
            return lbl
    # fallback
    if n.get("kind") == "reference":
        rid = n.get("ref_id")
        return rid if isinstance(rid, str) else "reference"
    atom_id = n.get("core_atom_id")
    return atom_id if isinstance(atom_id, str) else "atom"


def _compute_height(n_atoms: int) -> int:
    n = max(1, n_atoms)
    return TOP_Y + (n - 1) * ROW_GAP + NODE_H + FOOTER_H


def _center(x: int, y: int) -> Tuple[int, int]:
    return (x + NODE_W // 2, y + NODE_H // 2)


def render_svg(diagram: Dict[str, Any]) -> str:
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])

    if not isinstance(nodes, list):
        raise ValueError("diagram.nodes must be a list")
    if not isinstance(edges, list):
        raise ValueError("diagram.edges must be a list")

    # Canonical node ordering (defensive; contract should already enforce)
    nodes_sorted = [n for n in nodes if isinstance(n, dict)]
    nodes_sorted.sort(key=_node_sort_key)

    # Choose primary reference node: first reference node by ref_id asc
    ref_nodes = [n for n in nodes_sorted if n.get("kind") == "reference"]
    if not ref_nodes:
        raise ValueError("No reference node present in diagram.nodes")
    ref_node = ref_nodes[0]
    ref_node_id = str(ref_node.get("node_id", ""))

    atom_nodes = [n for n in nodes_sorted if n.get("kind") == "atom"]
    atom_nodes.sort(key=_node_sort_key)

    height = _compute_height(len(atom_nodes))

    # Assign pinned positions
    pos: Dict[str, Tuple[int, int]] = {}

    # Reference at top left
    pos[ref_node_id] = (X_REF, TOP_Y)

    # Atoms on right, top-down by rank
    for i, n in enumerate(atom_nodes):
        nid = str(n.get("node_id", ""))
        pos[nid] = (X_ATOM, TOP_Y + i * ROW_GAP)

    # Canonical edge ordering (defensive)
    edges_sorted = [e for e in edges if isinstance(e, dict)]
    edges_sorted.sort(key=_edge_sort_key)

    lines: List[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{height}" viewBox="0 0 {SVG_WIDTH} {height}">'
    )
    lines.append("  <defs>")
    lines.append(
        '    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
    )
    lines.append('      <path d="M 0 0 L 10 5 L 0 10 z" fill="#000"/>')
    lines.append("    </marker>")
    lines.append("  </defs>")
    lines.append(f'  <rect x="0" y="0" width="{SVG_WIDTH}" height="{height}" fill="#fff"/>')

    # Title
    lines.append(
        f'  <text x="{X_REF}" y="{TITLE_Y}" font-family="monospace" font-size="14" fill="#000">Paradox Diagram v0</text>'
    )

    # Draw edges first (under nodes)
    # co_occurrence: line between atom centers, no arrows
    for e in edges_sorted:
        kind = str(e.get("kind", ""))
        a = str(e.get("a", ""))
        b = str(e.get("b", ""))
        if kind != "co_occurrence":
            continue
        if a not in pos or b not in pos:
            continue
        xa, ya = pos[a]
        xb, yb = pos[b]
        cax, cay = _center(xa, ya)
        cbx, cby = _center(xb, yb)
        lines.append(f'  <line x1="{cax}" y1="{cay}" x2="{cbx}" y2="{cby}" stroke="#000" stroke-width="1.5"/>')

    # reference_relation: polyline atom -> reference, arrowhead toward reference
    ref_right_x = X_REF + NODE_W
    ref_center_y = _center(X_REF, TOP_Y)[1]
    elbow_x = 360  # pinned routing column

    for e in edges_sorted:
        kind = str(e.get("kind", ""))
        if kind != "reference_relation":
            continue
        a = str(e.get("a", ""))
        b = str(e.get("b", ""))
        # Expected: a atom, b reference
        if a not in pos or b not in pos:
            continue

        ax, ay = pos[a]
        _, acy = _center(ax, ay)

        # Start at atom left edge, route to elbow, then to reference center line, then to ref right edge
        start_x = X_ATOM
        start_y = acy

        pts: List[Tuple[int, int]] = [(start_x, start_y)]

        if start_y == ref_center_y:
            pts.append((ref_right_x, ref_center_y))
        else:
            pts.append((elbow_x, start_y))
            pts.append((elbow_x, ref_center_y))
            pts.append((ref_right_x, ref_center_y))

        pts_str = " ".join([f"{x},{y}" for x, y in pts])
        lines.append(
            f'  <polyline points="{pts_str}" fill="none" stroke="#000" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )

    # Draw nodes (boxes + text)
    def draw_node(n: Dict[str, Any]) -> None:
        nid = str(n.get("node_id", ""))
        if nid not in pos:
            return
        x, y = pos[nid]
        label = _esc(_label_for_node(n))
        kind = str(n.get("kind", ""))
        subtitle = nid

        lines.append(
            f'  <rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="6" ry="6" fill="#fff" stroke="#000" stroke-width="1.5"/>'
        )
        lines.append(f'  <text x="{x + 10}" y="{y + 14}" font-family="monospace" font-size="12" fill="#000">{label}</text>')
        lines.append(
            f'  <text x="{x + 10}" y="{y + 28}" font-family="monospace" font-size="10" fill="#000">{_esc(subtitle)}</text>'
        )

        # small kind marker (right-aligned)
        lines.append(
            f'  <text x="{x + NODE_W - 10}" y="{y + 14}" text-anchor="end" font-family="monospace" font-size="10" fill="#000">{_esc(kind)}</text>'
        )

    # Reference first, then atoms
    draw_node(ref_node)
    for n in atom_nodes:
        draw_node(n)

    # Footer notes (non-causal guardrail text)
    foot1_y = height - 40
    foot2_y = height - 24
    lines.append(
        f'  <text x="{X_REF}" y="{foot1_y}" font-family="monospace" font-size="10" fill="#000">NON-CAUSAL: co_occurrence edges are undirected (association only).</text>'
    )
    lines.append(
        f'  <text x="{X_REF}" y="{foot2_y}" font-family="monospace" font-size="10" fill="#000">Arrows are reference-only: atom → reference anchor (not atom → atom causality).</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render Paradox Diagram v0 to deterministic SVG (non-causal).")
    p.add_argument("--in", dest="in_path", required=True, help="Path to paradox_diagram_v0.json")
    p.add_argument("--out", dest="out_path", required=True, help="Output SVG path")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    if not in_path.exists():
        print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        return 2

    try:
        raw = _load_json(in_path)
        diagram = _find_diagram_obj(raw)
    except Exception as e:
        print(f"ERROR: failed to read/unwrap diagram JSON: {e}", file=sys.stderr)
        return 2

    try:
        svg = render_svg(diagram)
    except Exception as e:
        print(f"ERROR: render failed: {e}", file=sys.stderr)
        return 2

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ================================
# tests/test_paradox_diagram_svg_v0.py
# ================================
from __future__ import annotations

import difflib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"

RENDERER = SCRIPTS_DIR / "render_paradox_diagram_svg_v0.py"

DIAGRAM_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "paradox_diagram_v0" / "expected_paradox_diagram_v0.json"
GOLDEN = FIXTURES_DIR / "paradox_diagram_render_v0" / "golden_k2.svg"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_text_equal(actual: str, expected: str, *, label: str) -> None:
    if actual == expected:
        return
    a = actual.splitlines(keepends=True)
    e = expected.splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            e,
            a,
            fromfile=f"expected:{label}",
            tofile=f"actual:{label}",
        )
    )
    raise AssertionError(f"Mismatch for {label}:\n{diff}")


def test_paradox_diagram_svg_v0_golden(tmp_path: Path) -> None:
    assert RENDERER.exists(), f"Missing renderer script: {RENDERER}"
    assert DIAGRAM_FIXTURE.exists(), f"Missing diagram fixture: {DIAGRAM_FIXTURE}"
    assert GOLDEN.exists(), f"Missing golden SVG: {GOLDEN}"

    out_svg = tmp_path / "paradox_diagram_v0.svg"

    cmd = [
        sys.executable,
        str(RENDERER),
        "--in",
        str(DIAGRAM_FIXTURE),
        "--out",
        str(out_svg),
    ]
    res = _run(cmd, cwd=REPO_ROOT)
    assert res.returncode == 0, (
        "Renderer failed:\n"
        f"cmd: {' '.join(cmd)}\n"
        f"stdout:\n{res.stdout}\n"
        f"stderr:\n{res.stderr}\n"
    )
    assert out_svg.exists(), "Renderer did not produce SVG output."

    actual = out_svg.read_text(encoding="utf-8")
    expected = GOLDEN.read_text(encoding="utf-8")
    _assert_text_equal(actual, expected, label="paradox_diagram_v0.svg")

    # Determinism sanity: render twice and compare bytes
    out_svg2 = tmp_path / "paradox_diagram_v0.second.svg"
    cmd2 = [
        sys.executable,
        str(RENDERER),
        "--in",
        str(DIAGRAM_FIXTURE),
        "--out",
        str(out_svg2),
    ]
    res2 = _run(cmd2, cwd=REPO_ROOT)
    assert res2.returncode == 0, f"Second render failed:\n{res2.stderr}"
    assert out_svg2.read_text(encoding="utf-8") == actual, "Renderer output is not deterministic across two runs."


# ================================
# tests/fixtures/paradox_diagram_render_v0/golden_k2.svg
# ================================
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="236" viewBox="0 0 900 236">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#000"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="900" height="236" fill="#fff"/>
  <text x="40" y="24" font-family="monospace" font-size="14" fill="#000">Paradox Diagram v0</text>
  <line x1="550" y1="138" x2="550" y2="58" stroke="#000" stroke-width="1.5"/>
  <polyline points="420,138 360,138 360,58 300,58" fill="none" stroke="#000" stroke-width="1.5" marker-end="url(#arrow)"/>
  <polyline points="420,58 300,58" fill="none" stroke="#000" stroke-width="1.5" marker-end="url(#arrow)"/>
  <rect x="40" y="40" width="260" height="36" rx="6" ry="6" fill="#fff" stroke="#000" stroke-width="1.5"/>
  <text x="50" y="54" font-family="monospace" font-size="12" fill="#000">ref.release_decision</text>
  <text x="50" y="68" font-family="monospace" font-size="10" fill="#000">r_bb3ff61791b9df94</text>
  <text x="290" y="54" text-anchor="end" font-family="monospace" font-size="10" fill="#000">reference</text>
  <rect x="420" y="40" width="260" height="36" rx="6" ry="6" fill="#fff" stroke="#000" stroke-width="1.5"/>
  <text x="430" y="54" font-family="monospace" font-size="12" fill="#000">Latency budget flip</text>
  <text x="430" y="68" font-family="monospace" font-size="10" fill="#000">n_fdd73542b1d24194</text>
  <text x="670" y="54" text-anchor="end" font-family="monospace" font-size="10" fill="#000">atom</text>
  <rect x="420" y="120" width="260" height="36" rx="6" ry="6" fill="#fff" stroke="#000" stroke-width="1.5"/>
  <text x="430" y="134" font-family="monospace" font-size="12" fill="#000">p99 latency delta</text>
  <text x="430" y="148" font-family="monospace" font-size="10" fill="#000">n_11339020e4befbed</text>
  <text x="670" y="134" text-anchor="end" font-family="monospace" font-size="10" fill="#000">atom</text>
  <text x="40" y="196" font-family="monospace" font-size="10" fill="#000">NON-CAUSAL: co_occurrence edges are undirected (association only).</text>
  <text x="40" y="212" font-family="monospace" font-size="10" fill="#000">Arrows are reference-only: atom → reference anchor (not atom → atom causality).</text>
</svg>
