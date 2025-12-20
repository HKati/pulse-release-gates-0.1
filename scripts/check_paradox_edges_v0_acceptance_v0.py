#!/usr/bin/env python3
"""
Fixture acceptance check for paradox_edges_v0.jsonl (JSONL edge export).

This is intentionally stricter than the contract check:
- Requires at least --min-count edges (default: 1)
- Optionally requires at least --min-count edges of a given --type
- (optional) if --atoms provided: src/dst must link to existing atoms

Exit codes:
- 0 OK
- 2 acceptance fail
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional, Set, Tuple


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[edges-acceptance] {msg}")


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON in {path}: {e}")


def _extract_atom_ids(obj: Any) -> Set[str]:
    if not isinstance(obj, dict):
        die("--atoms root must be a JSON object/dict")

    root = obj
    if "paradox_field_v0" in obj and isinstance(obj.get("paradox_field_v0"), dict):
        root = obj["paradox_field_v0"]

    atoms = root.get("atoms")
    if not isinstance(atoms, list):
        die("--atoms JSON must contain atoms[]")

    ids: Set[str] = set()
    for i, a in enumerate(atoms):
        if not isinstance(a, dict):
            die(f"--atoms atoms[{i}] must be an object/dict")
        aid = a.get("atom_id")
        if isinstance(aid, str) and aid.strip():
            ids.add(aid.strip())
    return ids


def _read_edges_jsonl(path: str) -> List[Tuple[int, Dict[str, Any]]]:
    out: List[Tuple[int, Dict[str, Any]]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except json.JSONDecodeError as e:
                    die(f"{path}:L{idx} invalid JSONL line: {e}")
                if not isinstance(obj, dict):
                    die(f"{path}:L{idx} each JSONL line must be an object/dict")
                out.append((idx, obj))
    except FileNotFoundError:
        die(f"file not found: {path}")

    if not out:
        die("no JSONL objects found (file is empty or whitespace only)")
    return out


def _req_non_empty_str(d: Dict[str, Any], key: str, where: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        die(f"{where}.{key} must be a non-empty string")
    return v.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance check for paradox_edges_v0.jsonl")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0.jsonl")
    ap.add_argument("--min-count", type=int, default=1, help="Minimum required edges (default: 1)")
    ap.add_argument("--type", dest="edge_type", default="", help="Optional required edge type")
    ap.add_argument(
        "--atoms",
        default="",
        help="Optional: path to paradox_field_v0.json to verify src/dst links",
    )
    args = ap.parse_args()

    atom_ids: Optional[Set[str]] = None
    if args.atoms:
        atom_ids = _extract_atom_ids(_read_json(args.atoms))

    edges = _read_edges_jsonl(args.in_path)

    # Basic required fields + optional link integrity
    typed_hits = 0
    for lineno, e in edges:
        where = f"{args.in_path}:L{lineno}"
        eid = _req_non_empty_str(e, "edge_id", where)
        ety = _req_non_empty_str(e, "type", where)
        src = _req_non_empty_str(e, "src_atom_id", where)
        dst = _req_non_empty_str(e, "dst_atom_id", where)

        if args.edge_type and ety == args.edge_type:
            typed_hits += 1

        if atom_ids is not None:
            if src not in atom_ids:
                die(f"{where}: broken link src_atom_id {src!r} not found in atoms")
            if dst not in atom_ids:
                die(f"{where}: broken link dst_atom_id {dst!r} not found in atoms")

        # keep lints happy; variables are validated above
        _ = (eid, ety, src, dst)

    if len(edges) < args.min_count and not args.edge_type:
        die(f"missing edges (found={len(edges)}, required>={args.min_count})")

    if args.edge_type:
        if typed_hits < args.min_count:
            die(
                f"missing required edges of type={args.edge_type!r} "
                f"(found={typed_hits}, required>={args.min_count})"
            )

    print("[edges-acceptance] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
