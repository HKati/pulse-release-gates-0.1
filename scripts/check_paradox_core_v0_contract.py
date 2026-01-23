#!/usr/bin/env python3
"""
check_paradox_core_v0_contract.py

Fail-closed contract checker for paradox_core_v0.json.

This is overlay-local strictness: it should fail for missing fields,
broken links, or non-canonical ordering.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCHEMA_NAME = "PULSE_paradox_core_v0"
SCHEMA_VERSION = "v0"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(msg: str) -> None:
    raise SystemExit(f"[contract FAIL] {msg}")


def _is_sorted(items: List[Any], key_fn) -> bool:
    keys = [key_fn(x) for x in items]
    return keys == sorted(keys)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input paradox_core_v0.json")
    args = ap.parse_args()

    p = Path(args.inp)
    obj = _load(p)

    if obj.get("schema") != SCHEMA_NAME:
        _fail(f"schema must be {SCHEMA_NAME}")
    if obj.get("version") != SCHEMA_VERSION:
        _fail(f"version must be {SCHEMA_VERSION}")

    sel = obj.get("selection", {})
    if not isinstance(sel, dict):
        _fail("selection must be an object")
    for k in ["k", "metric", "method", "tie_break", "edge_policy"]:
        if k not in sel:
            _fail(f"selection missing '{k}'")

    atoms = obj.get("atoms")
    edges = obj.get("edges")
    core = obj.get("core")

    if not isinstance(atoms, list):
        _fail("atoms must be a list")
    if not isinstance(edges, list):
        _fail("edges must be a list")
    if not isinstance(core, dict):
        _fail("core must be an object")

    atom_ids: List[str] = []
    ranks: List[int] = []

    for a in atoms:
        if not isinstance(a, dict):
            _fail("atoms entries must be objects")
        atom_id = a.get("atom_id")
        if not isinstance(atom_id, str) or not atom_id:
            _fail("atom missing atom_id")
        r = a.get("core_rank")
        if not isinstance(r, int):
            _fail("atom missing core_rank (int)")
        atom_ids.append(atom_id)
        ranks.append(r)

    # rank must be 1..N with no gaps
    n = len(atoms)
    if sorted(ranks) != list(range(1, n + 1)):
        _fail("core_rank must be contiguous 1..N")

    # canonical ordering: (core_rank asc, atom_id asc)
    if not _is_sorted(atoms, lambda x: (int(x["core_rank"]), str(x["atom_id"]))):
        _fail("atoms not in canonical order (core_rank, atom_id)")

    if len(set(atom_ids)) != len(atom_ids):
        _fail("duplicate atom_id in atoms")

    core_atom_ids = core.get("atom_ids")
    if not isinstance(core_atom_ids, list) or any(not isinstance(x, str) for x in core_atom_ids):
        _fail("core.atom_ids must be a list[str]")
    if core_atom_ids != atom_ids:
        _fail("core.atom_ids must match atoms[].atom_id in the same order")

    edge_ids: List[str] = []
    for e in edges:
        if not isinstance(e, dict):
            _fail("edges entries must be objects")
        src = e.get("src_atom_id")
        dst = e.get("dst_atom_id")
        et = e.get("edge_type")
        eid = e.get("edge_id")
        if not isinstance(src, str) or not isinstance(dst, str):
            _fail("edge missing src_atom_id/dst_atom_id")
        if src not in set(atom_ids) or dst not in set(atom_ids):
            _fail("edge endpoints must be within core atoms")
        if not isinstance(et, str) or not et:
            _fail("edge missing edge_type")
        if not isinstance(eid, str) or not eid:
            _fail("edge missing edge_id")
        edge_ids.append(eid)

    # canonical ordering: (src, dst, type, edge_id)
    if not _is_sorted(edges, lambda x: (str(x["src_atom_id"]), str(x["dst_atom_id"]), str(x["edge_type"]), str(x["edge_id"]))):
        _fail("edges not in canonical order (src, dst, type, edge_id)")

    if len(set(edge_ids)) != len(edge_ids):
        _fail("duplicate edge_id in edges")

    core_edge_ids = core.get("edge_ids")
    if not isinstance(core_edge_ids, list) or any(not isinstance(x, str) for x in core_edge_ids):
        _fail("core.edge_ids must be a list[str]")
    if core_edge_ids != edge_ids:
        _fail("core.edge_ids must match edges[].edge_id in the same order")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
