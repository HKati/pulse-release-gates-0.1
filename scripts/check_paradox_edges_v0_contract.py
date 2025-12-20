#!/usr/bin/env python3
"""
Fail-closed contract check for paradox_edges_v0.jsonl (JSONL edge export).

What it guarantees:
- file is readable JSONL (each non-empty line is a JSON object)
- required fields exist and are non-empty strings:
    edge_id, type, src_atom_id, dst_atom_id
- edge_id is unique
- (optional) if --atoms is provided: src/dst atom ids must exist in paradox_field_v0.json
- ordering is not "random": edges must be non-decreasing by either:
    A) edge_id
   OR
    B) (type, src_atom_id, dst_atom_id, edge_id)
  (we accept either to avoid coupling too tightly to exporter internals)

Exit codes:
- 0 OK
- 2 contract fail
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[edges-contract] {msg}")


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON in {path}: {e}")


def _extract_atom_ids(obj: Any) -> Set[str]:
    """
    Accept both shapes:
      A) {"paradox_field_v0": {"meta": {...}, "atoms": [...]}}
      B) {"meta": {...}, "atoms": [...]}
    """
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


def _iter_jsonl_lines(path: str) -> Iterable[Tuple[int, str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                yield idx, s
    except FileNotFoundError:
        die(f"file not found: {path}")


def _req_non_empty_str(d: Dict[str, Any], key: str, where: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        die(f"{where}.{key} must be a non-empty string")
    return v.strip()


def _non_decreasing(keys: List[Tuple[Any, ...]]) -> bool:
    for i in range(1, len(keys)):
        if keys[i - 1] > keys[i]:
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract check for paradox_edges_v0.jsonl")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0.jsonl")
    ap.add_argument(
        "--atoms",
        default="",
        help="Optional: path to paradox_field_v0.json to verify src/dst links",
    )
    args = ap.parse_args()

    atom_ids: Optional[Set[str]] = None
    if args.atoms:
        atom_ids = _extract_atom_ids(_read_json(args.atoms))

    edge_ids: Set[str] = set()
    key_by_edge_id: List[Tuple[str]] = []
    key_by_struct: List[Tuple[str, str, str, str]] = []

    line_count = 0
    for lineno, raw in _iter_jsonl_lines(args.in_path):
        line_count += 1
        where = f"{args.in_path}:L{lineno}"
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            die(f"{where}: invalid JSONL line: {e}")

        if not isinstance(obj, dict):
            die(f"{where}: each JSONL line must be an object/dict")

        eid = _req_non_empty_str(obj, "edge_id", where)
        ety = _req_non_empty_str(obj, "type", where)
        src = _req_non_empty_str(obj, "src_atom_id", where)
        dst = _req_non_empty_str(obj, "dst_atom_id", where)

        if eid in edge_ids:
            die(f"{where}: duplicate edge_id {eid!r}")
        edge_ids.add(eid)

        # Optional link integrity vs atoms
        if atom_ids is not None:
            if src not in atom_ids:
                die(f"{where}: broken link src_atom_id {src!r} not found in atoms")
            if dst not in atom_ids:
                die(f"{where}: broken link dst_atom_id {dst!r} not found in atoms")

        key_by_edge_id.append((eid,))
        key_by_struct.append((ety, src, dst, eid))

    if line_count == 0:
        die("no JSONL objects found (file is empty or whitespace only)")

    # Deterministic-ish ordering check (accept either strategy)
    ok_edge_id = _non_decreasing(key_by_edge_id)
    ok_struct = _non_decreasing(key_by_struct)
    if not (ok_edge_id or ok_struct):
        die(
            "edges are not deterministically ordered; expected non-decreasing by either "
            "(edge_id) OR (type, src_atom_id, dst_atom_id, edge_id)"
        )

    print("[edges-contract] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # allow piping into head, etc.
        sys.exit(0)
