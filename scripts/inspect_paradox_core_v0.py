#!/usr/bin/env python3
"""
inspect_paradox_core_v0.py

Deterministic Markdown summary exporter for the Paradox Core projection artifact.

Input:
  - paradox_core_v0.json

Output:
  - paradox_core_summary_v0.md

Design goals:
  - CI-neutral (diagnostic only)
  - deterministic output (no timestamps, no environment-dependent paths)
  - explicit non-causal semantics for edges (co-occurrence/association only)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _escape_md_cell(s: str) -> str:
    # Keep tables stable and readable.
    s = s.replace("|", "\\|")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    return s


def _shorten(s: str, n: int) -> str:
    s = s.strip()
    if n <= 0:
        return s
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)].rstrip() + "…"


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt_float(v: Any, digits: int = 6) -> str:
    f = _as_float(v)
    if f is None:
        return ""
    return f"{f:.{digits}f}"


def _get_atom_ref(a: Dict[str, Any]) -> str:
    """
    A stable “reference” column for reviewers:
    prefer gate_id, then metric_id, then a compact join of gate_ids if present.
    """
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


def _canonical_atom_sort_key(a: Dict[str, Any]) -> Tuple[int, str]:
    rank = a.get("core_rank")
    try:
        r = int(rank)
    except (TypeError, ValueError):
        r = 10**9
    atom_id = _as_str(a.get("atom_id"))
    return (r, atom_id)


def _canonical_edge_sort_key(e: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        _as_str(e.get("src_atom_id")),
        _as_str(e.get("dst_atom_id")),
        _as_str(e.get("edge_type")),
        _as_str(e.get("edge_id")),
    )


def render_summary(core: Dict[str, Any], max_atoms: int, max_edges: int, max_summary_len: int) -> str:
    schema = _as_str(core.get("schema"))
    version = _as_str(core.get("version"))

    selection = core.get("selection") if isinstance(core.get("selection"), dict) else {}
    metric = _as_str(selection.get("metric"))
    k = selection.get("k")

    inputs = core.get("inputs") if isinstance(core.get("inputs"), dict) else {}
    field_sha = _as_str(inputs.get("field_sha256"))
    edges_sha = _as_str(inputs.get("edges_sha256"))

    run_context = core.get("run_context") if isinstance(core.get("run_context"), dict) else {}
    run_id = _as_str(run_context.get("run_id"))

    anchor = core.get("anchor", None)

    stats = core.get("stats") if isinstance(core.get("stats"), dict) else {}

    atoms = core.get("atoms")
    edges = core.get("edges")
    if not isinstance(atoms, list):
        raise ValueError("core.atoms must be a list")
    if not isinstance(edges, list):
        raise ValueError("core.edges must be a list")

    # Enforce canonical ordering locally (even if input is unsorted).
    atoms_sorted = [a for a in atoms if isinstance(a, dict)]
    atoms_sorted.sort(key=_canonical_atom_sort_key)

    edges_sorted = [e for e in edges if isinstance(e, dict)]
    edges_sorted.sort(key=_canonical_edge_sort_key)

    atoms_total = len(atoms_sorted)
    edges_total = len(edges_sorted)

    atoms_view = atoms_sorted
    edges_view = edges_sorted

    truncated_atoms = False
    truncated_edges = False

    if max_atoms > 0 and len(atoms_view) > max_atoms:
        atoms_view = atoms_view[:max_atoms]
        truncated_atoms = True

    if max_edges > 0 and len(edges_view) > max_edges:
        edges_view = edges_view[:max_edges]
        truncated_edges = True

    lines: List[str] = []
    lines.append("# Paradox Core Summary v0")
    lines.append("")
    lines.append("> Diagnostic projection. Edges are association/co-occurrence only (non-causal).")
    lines.append("> This summary must not redefine or flip CI release semantics.")
    lines.append("")

    lines.append("## Identity")
    lines.append(f"- schema: `{_escape_md_cell(schema)}`")
    lines.append(f"- version: `{_escape_md_cell(version)}`")
    if run_id:
        lines.append(f"- run_id: `{_escape_md_cell(run_id)}`")
    if metric:
        lines.append(f"- selection.metric: `{_escape_md_cell(metric)}`")
    if k is not None:
        lines.append(f"- selection.k: `{_escape_md_cell(_as_str(k))}`")
    if field_sha:
        lines.append(f"- inputs.field_sha256: `{_escape_md_cell(field_sha)}`")
    if edges_sha:
        lines.append(f"- inputs.edges_sha256: `{_escape_md_cell(edges_sha)}`")
    if anchor is not None:
        # keep it compact and deterministic
        lines.append(f"- anchor: `{_escape_md_cell(_shorten(_as_str(anchor), 200))}`")
    lines.append("")

    if stats:
        lines.append("## Stats")
        # stable key ordering for readability
        for key in sorted(stats.keys()):
            lines.append(f"- {key}: `{_escape_md_cell(_as_str(stats.get(key)))}`")
        lines.append("")

    lines.append(f"## Core atoms ({atoms_total})")
    if truncated_atoms:
        lines.append(f"_Showing first {len(atoms_view)} atoms (truncated)._")
    lines.append("")
    lines.append("| rank | atom_id | core_score | ref | kind | summary |")
    lines.append("|---:|---|---:|---|---|---|")

    for a in atoms_view:
        atom_id = _as_str(a.get("atom_id"))
        rank = _as_str(a.get("core_rank"))
        score = _fmt_float(a.get("core_score"))
        ref = _get_atom_ref(a)
        kind = _as_str(a.get("kind", a.get("atom_kind", "")))
        summary = _as_str(a.get("summary", a.get("title", a.get("label", ""))))
        summary = _shorten(summary, max_summary_len)

        lines.append(
            "| {rank} | `{atom_id}` | {score} | `{ref}` | `{kind}` | {summary} |".format(
                rank=_escape_md_cell(rank),
                atom_id=_escape_md_cell(atom_id),
                score=_escape_md_cell(score),
                ref=_escape_md_cell(ref),
                kind=_escape_md_cell(kind),
                summary=_escape_md_cell(summary),
            )
        )

    lines.append("")
    lines.append(f"## Core edges ({edges_total})")
    if truncated_edges:
        lines.append(f"_Showing first {len(edges_view)} edges (truncated)._")
    lines.append("")
    lines.append("| src | dst | type | weight | edge_id |")
    lines.append("|---|---|---|---:|---|")

    for e in edges_view:
        src = _as_str(e.get("src_atom_id"))
        dst = _as_str(e.get("dst_atom_id"))
        et = _as_str(e.get("edge_type"))
        w = _fmt_float(e.get("weight"))
        eid = _as_str(e.get("edge_id"))

        lines.append(
            "| `{src}` | `{dst}` | `{et}` | {w} | `{eid}` |".format(
                src=_escape_md_cell(src),
                dst=_escape_md_cell(dst),
                et=_escape_md_cell(et),
                w=_escape_md_cell(w),
                eid=_escape_md_cell(eid),
            )
        )

    lines.append("")
    lines.append("## Notes")
    notes = core.get("notes")
    if isinstance(notes, list) and all(isinstance(x, str) for x in notes):
        for n in notes:
            lines.append(f"- {_escape_md_cell(n)}")
    else:
        lines.append("- Edges are non-causal in v0 (association/co-occurrence only).")
        lines.append("- CI-neutral by default unless explicitly promoted into required gates.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input paradox_core_v0.json")
    ap.add_argument("--out", required=True, help="Output markdown path")
    ap.add_argument("--max-atoms", type=int, default=50, help="Max atoms to display (0 = no limit). Default: 50")
    ap.add_argument("--max-edges", type=int, default=200, help="Max edges to display (0 = no limit). Default: 200")
    ap.add_argument("--max-summary-len", type=int, default=160, help="Max length for summary cells. Default: 160")
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)

    core = _load_json(inp)
    md = render_summary(core, max_atoms=int(args.max_atoms), max_edges=int(args.max_edges), max_summary_len=int(args.max_summary_len))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
