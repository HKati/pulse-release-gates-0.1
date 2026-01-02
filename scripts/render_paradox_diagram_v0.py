#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    typ: str
    weight: float


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RuntimeError(f"Missing file: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON: {path}: {e}") from e


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise RuntimeError(f"Missing file: {path}")
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception as e:
                    raise RuntimeError(f"Invalid JSONL at {path}:{i}: {e}") from e
                if not isinstance(obj, dict):
                    raise RuntimeError(f"Expected JSON object at {path}:{i}, got {type(obj).__name__}")
                rows.append(obj)
        return rows
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to read JSONL: {path}: {e}") from e


def _first_key(d: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for k in keys:
        if k in d:
            return d[k]
    return None


def _to_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return str(x)


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _escape_mermaid_label(s: str, *, max_len: int = 80) -> str:
    """
    Mermaid flowchart labels are safest when they are short, single-line, and do not contain quotes/pipes.
    """
    s = " ".join(s.split())  # collapse whitespace/newlines
    s = s.replace('"', "'").replace("|", "/")
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _canonical_pair(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _extract_edges(rows: List[Dict[str, Any]]) -> Tuple[List[Edge], Dict[str, int]]:
    stats = {
        "rows_total": 0,
        "rows_skipped_missing_endpoints": 0,
        "rows_missing_weight": 0,
        "rows_missing_type": 0,
        "rows_self_loop": 0,
    }

    out: List[Edge] = []
    for r in rows:
        stats["rows_total"] += 1

        src = _to_str(_first_key(r, ["src_id", "src", "a", "from"]))
        dst = _to_str(_first_key(r, ["dst_id", "dst", "b", "to"]))

        if not src or not dst:
            stats["rows_skipped_missing_endpoints"] += 1
            continue

        if src == dst:
            stats["rows_self_loop"] += 1
            continue

        typ = _to_str(_first_key(r, ["type", "edge_type"])) or "tension"
        if "type" not in r and "edge_type" not in r:
            stats["rows_missing_type"] += 1

        w = _to_float(_first_key(r, ["weight", "w", "score"]))
        if w is None:
            w = 0.0
            stats["rows_missing_weight"] += 1

        a, b = _canonical_pair(src, dst)
        out.append(Edge(src=a, dst=b, typ=typ, weight=w))

    return out, stats


def _dedupe_edges(edges: List[Edge]) -> List[Edge]:
    """
    Keep max-weight edge per (src,dst,type). Deterministic tie-break: keep lexicographically smaller repr.
    """
    best: Dict[Tuple[str, str, str], Edge] = {}
    for e in edges:
        k = (e.src, e.dst, e.typ)
        prev = best.get(k)
        if prev is None:
            best[k] = e
        else:
            if e.weight > prev.weight:
                best[k] = e
            elif e.weight == prev.weight:
                # deterministic tie-break (rare): keep stable string-min
                if (e.src, e.dst, e.typ) < (prev.src, prev.dst, prev.typ):
                    best[k] = e
    return list(best.values())


def _sort_edges(edges: List[Edge]) -> List[Edge]:
    return sorted(edges, key=lambda e: (-e.weight, e.typ, e.src, e.dst))


def _score_nodes(edges: List[Edge]) -> Dict[str, float]:
    score: Dict[str, float] = {}
    for e in edges:
        score[e.src] = score.get(e.src, 0.0) + e.weight
        score[e.dst] = score.get(e.dst, 0.0) + e.weight
    return score


def _select_nodes(edges: List[Edge], max_nodes: int) -> List[str]:
    score = _score_nodes(edges)
    nodes = list(score.keys())
    nodes_sorted = sorted(nodes, key=lambda n: (-score.get(n, 0.0), n))
    return nodes_sorted[:max_nodes]


def _node_alias_map(nodes_sorted: List[str]) -> Dict[str, str]:
    # deterministic aliases: n0, n1, ...
    return {node_id: f"n{i}" for i, node_id in enumerate(nodes_sorted)}


def _extract_run_context(field_obj: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(field_obj, dict):
        return None
    rc = field_obj.get("run_context")
    if isinstance(rc, dict) and rc:
        return rc
    return None


def _render_markdown(
    *,
    title: str,
    field_path: Optional[Path],
    edges_path: Path,
    out_path: Path,
    direction: str,
    max_nodes: int,
    max_edges: int,
    min_weight: float,
    edge_labels: bool,
) -> str:
    field_obj = None
    run_context = None
    if field_path is not None:
        field_obj = _read_json(field_path)
        run_context = _extract_run_context(field_obj)

    rows = _read_jsonl(edges_path)
    edges_raw, edge_stats = _extract_edges(rows)

    # If endpoints are missing, that's a real problem → fail-closed.
    if edge_stats["rows_skipped_missing_endpoints"] > 0 and edge_stats["rows_total"] > 0:
        raise RuntimeError(
            f"Edges with missing endpoints: {edge_stats['rows_skipped_missing_endpoints']} "
            f"(total rows={edge_stats['rows_total']}). Contract likely broken."
        )

    edges_filtered = [e for e in edges_raw if e.weight >= min_weight]
    edges_dedup = _dedupe_edges(edges_filtered)
    edges_sorted = _sort_edges(edges_dedup)

    # pre-trim edges to help node scoring
    edges_trimmed = edges_sorted[:max_edges] if max_edges > 0 else edges_sorted

    # node selection
    if edges_trimmed:
        nodes_sorted = _select_nodes(edges_trimmed, max_nodes=max_nodes)
        nodes_set = set(nodes_sorted)
        edges_in_nodes = [e for e in edges_sorted if e.src in nodes_set and e.dst in nodes_set]
        edges_in_nodes = _sort_edges(edges_in_nodes)[:max_edges] if max_edges > 0 else _sort_edges(edges_in_nodes)
    else:
        nodes_sorted = []
        edges_in_nodes = []

    # labels (v0: use node id as label; field-aware labels can be added later)
    node_labels: Dict[str, str] = {nid: nid for nid in nodes_sorted}
    alias = _node_alias_map(nodes_sorted)

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("Generated by `scripts/render_paradox_diagram_v0.py`.")
    lines.append("")
    lines.append("## Inputs")
    if field_path is not None:
        lines.append(f"- field: `{field_path.as_posix()}`")
    else:
        lines.append("- field: *(not provided)*")
    lines.append(f"- edges: `{edges_path.as_posix()}`")
    lines.append("")
    lines.append("## Params")
    lines.append(f"- direction: `{direction}`")
    lines.append(f"- max_nodes: `{max_nodes}`")
    lines.append(f"- max_edges: `{max_edges}`")
    lines.append(f"- min_weight: `{min_weight}`")
    lines.append(f"- edge_labels: `{edge_labels}`")
    lines.append("")
    lines.append("## Counts")
    lines.append(f"- rows_total: `{edge_stats['rows_total']}`")
    lines.append(f"- edges_raw: `{len(edges_raw)}`")
    lines.append(f"- edges_after_min_weight: `{len(edges_filtered)}`")
    lines.append(f"- edges_after_dedupe: `{len(edges_dedup)}`")
    lines.append(f"- edges_rendered: `{len(edges_in_nodes)}`")
    lines.append(f"- nodes_rendered: `{len(nodes_sorted)}`")
    if edge_stats["rows_missing_weight"] > 0:
        lines.append(f"- WARNING: edges_missing_weight_treated_as_0: `{edge_stats['rows_missing_weight']}`")
    lines.append("")

    if run_context:
        # keep it compact and deterministic (sorted keys)
        rc_keys = sorted(run_context.keys())
        lines.append("## Run context (from field)")
        for k in rc_keys:
            v = run_context.get(k)
            try:
                v_str = json.dumps(v, ensure_ascii=False)
            except Exception:
                v_str = str(v)
            v_str = _escape_mermaid_label(v_str, max_len=120)
            lines.append(f"- `{k}`: {v_str}")
        lines.append("")

    lines.append("## Diagram (Mermaid)")
    lines.append("")
    lines.append("```mermaid")
    lines.append(f"flowchart {direction}")

    if not edges_in_nodes:
        # empty but still valid
        lines.append('  empty["No edges to render (empty or filtered)."]')
    else:
        # nodes
        for nid in nodes_sorted:
            a = alias[nid]
            lbl = _escape_mermaid_label(node_labels.get(nid, nid))
            lines.append(f'  {a}["{lbl}"]')

        # edges
        for e in edges_in_nodes:
            a = alias[e.src]
            b = alias[e.dst]
            if edge_labels:
                lbl = _escape_mermaid_label(f"{e.typ} {e.weight:.3g}", max_len=60)
                # Mermaid edge labels use pipes: ---|label| ---
                lines.append(f"  {a} ---|{lbl}| {b}")
            else:
                lines.append(f"  {a} --- {b}")

    lines.append("```")
    lines.append("")
    lines.append("## Legend")
    lines.append("- Nodes are identifiers from the paradox tension surface (projection view).")
    lines.append("- Edge labels are `<type> <weight>` where weight is taken from `paradox_edges_v0.jsonl` (co-occurrence strength).")
    lines.append("- This is diagnostic only; it does not change any CI gates or release decisions.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Render paradox_edges_v0 as a deterministic Mermaid diagram (Markdown).")
    p.add_argument("--field", type=str, default=None, help="Path to paradox_field_v0.json (optional).")
    p.add_argument("--edges", type=str, required=True, help="Path to paradox_edges_v0.jsonl (required).")
    p.add_argument("--out", type=str, required=True, help="Output markdown path (e.g., out/paradox_diagram_v0.md).")
    p.add_argument("--title", type=str, default="Paradox diagram v0 (projection)", help="Markdown title (H1).")
    p.add_argument("--direction", type=str, default="LR", help="Mermaid flow direction (LR, TD, etc.).")
    p.add_argument("--max-nodes", type=int, default=40, help="Max nodes to render.")
    p.add_argument("--max-edges", type=int, default=120, help="Max edges to render.")
    p.add_argument("--min-weight", type=float, default=0.0, help="Filter edges with weight < min_weight.")
    p.add_argument("--no-edge-labels", action="store_true", help="Disable edge labels (type/weight).")
    args = p.parse_args(argv)

    field_path = Path(args.field) if args.field else None
    edges_path = Path(args.edges)
    out_path = Path(args.out)

    try:
        out_md = _render_markdown(
            title=args.title,
            field_path=field_path,
            edges_path=edges_path,
            out_path=out_path,
            direction=args.direction,
            max_nodes=max(1, args.max_nodes),
            max_edges=max(0, args.max_edges),
            min_weight=args.min_weight,
            edge_labels=(not args.no_edge_labels),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_md + "\n", encoding="utf-8")
        return 0
    except Exception as e:
        print(f"[render_paradox_diagram_v0] ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
