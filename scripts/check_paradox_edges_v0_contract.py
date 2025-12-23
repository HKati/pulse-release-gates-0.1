#!/usr/bin/env python3
# scripts/check_paradox_field_v0_contract.py
"""
Contract check for paradox_field_v0.json (fail-closed).

Guarantees:
- JSON is readable
- paradox_field_v0.atoms exists and is a list
- atom_id is unique
- severity is one of: crit|warn|info
- deterministic ordering: severity (crit>warn>info) -> type -> atom_id
- tension atoms do not have broken links and link types match
- provenance: gate_flip + metric_delta MUST include evidence.source.row_index (int)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


SEVERITY_ORDER: Dict[str, int] = {"crit": 0, "warn": 1, "info": 2}
ALLOWED_SEVERITIES = set(SEVERITY_ORDER.keys())


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[contract] {msg}")


def as_dict(x: Any, path: str) -> Dict[str, Any]:
    if not isinstance(x, dict):
        die(f"{path} must be an object/dict")
    return x


def as_list(x: Any, path: str) -> List[Any]:
    if not isinstance(x, list):
        die(f"{path} must be an array/list")
    return x


def req_str(d: Dict[str, Any], key: str, path: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        die(f"{path}.{key} must be a non-empty string")
    return v


def req_dict(d: Dict[str, Any], key: str, path: str) -> Dict[str, Any]:
    v = d.get(key)
    if not isinstance(v, dict):
        die(f"{path}.{key} must be an object/dict")
    return v


def req_int(d: Dict[str, Any], key: str, path: str) -> int:
    v = d.get(key)
    # bool is a subclass of int in Python -> exclude it explicitly
    if not isinstance(v, int) or isinstance(v, bool):
        die(f"{path}.{key} must be an int")
    return v


def sort_key(atom: Dict[str, Any], path: str) -> Tuple[int, str, str]:
    sev = req_str(atom, "severity", path)
    if sev not in SEVERITY_ORDER:
        die(f"{path}.severity must be one of {sorted(ALLOWED_SEVERITIES)} (got {sev!r})")
    typ = req_str(atom, "type", path)
    aid = req_str(atom, "atom_id", path)
    return (SEVERITY_ORDER[sev], typ, aid)


def check_non_decreasing(keys: List[Tuple[int, str, str]]) -> None:
    for i in range(1, len(keys)):
        if keys[i - 1] > keys[i]:
            die(
                "atoms are not deterministically ordered; expected non-decreasing by "
                "severity (crit>warn>info), then type, then atom_id"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract check for paradox_field_v0.json")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_field_v0.json")
    args = ap.parse_args()

    try:
        with open(args.in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        die(f"file not found: {args.in_path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON: {e}")

    root0 = as_dict(data, "$")
    # Accept either:
    #  - {"paradox_field_v0": {"meta": ..., "atoms": [...]}}
    #  - {"meta": ..., "atoms": [...]}  (legacy/alternate)
    root = root0.get("paradox_field_v0") if isinstance(root0.get("paradox_field_v0"), dict) else root0

    atoms_any = root.get("atoms")
    if atoms_any is None:
        die("$.paradox_field_v0.atoms (or $.atoms) is missing")
    atoms_list = as_list(atoms_any, "$.atoms")

    atoms: List[Dict[str, Any]] = []
    for i, a in enumerate(atoms_list):
        if not isinstance(a, dict):
            die(f"$.atoms[{i}] must be an object/dict")
        atoms.append(a)

    id_to_atom: Dict[str, Dict[str, Any]] = {}
    keys: List[Tuple[int, str, str]] = []

    for i, a in enumerate(atoms):
        path = f"$.atoms[{i}]"

        aid = req_str(a, "atom_id", path)
        if aid in id_to_atom:
            die(f"duplicate atom_id: {aid!r}")
        id_to_atom[aid] = a

        typ = req_str(a, "type", path)
        req_str(a, "severity", path)

        ev = req_dict(a, "evidence", path)
        src = ev.get("source")

        # C4.1: provenance requirement (fail-closed)
        # gate_flip + metric_delta MUST have evidence.source.row_index (int)
        if typ in ("gate_flip", "metric_delta"):
            if not isinstance(src, dict):
                die(f"{path}.evidence.source must be an object/dict for type={typ!r}")
            req_int(src, "row_index", f"{path}.evidence.source")

        keys.append(sort_key(a, path))

    # deterministic ordering check
    check_non_decreasing(keys)

    def atom_type(aid: str) -> str:
        a = id_to_atom.get(aid)
        if a is None:
            return ""
        t = a.get("type")
        return t if isinstance(t, str) else ""

    # Link integrity checks for known tension types
    for i, a in enumerate(atoms):
        path = f"$.atoms[{i}]"
        typ = a.get("type")
        if not isinstance(typ, str):
            continue

        ev = a.get("evidence")
        if not isinstance(ev, dict):
            die(f"{path}.evidence must be an object/dict")

        if typ == "gate_overlay_tension":
            gate_id = ev.get("gate_atom_id")
            over_id = ev.get("overlay_atom_id")

            if not isinstance(gate_id, str) or not gate_id:
                die(f"{path}.evidence.gate_atom_id must be a non-empty string")
            if not isinstance(over_id, str) or not over_id:
                die(f"{path}.evidence.overlay_atom_id must be a non-empty string")

            if gate_id not in id_to_atom:
                die(f"{path} broken link: gate_atom_id {gate_id!r} not found")
            if over_id not in id_to_atom:
                die(f"{path} broken link: overlay_atom_id {over_id!r} not found")

            if atom_type(gate_id) != "gate_flip":
                die(f"{path} link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(over_id) != "overlay_change":
                die(f"{path} link type mismatch: overlay_atom_id must point to type 'overlay_change'")

        if typ == "gate_metric_tension":
            gate_id = ev.get("gate_atom_id")
            met_id = ev.get("metric_atom_id")

            if not isinstance(gate_id, str) or not gate_id:
                die(f"{path}.evidence.gate_atom_id must be a non-empty string")
            if not isinstance(met_id, str) or not met_id:
                die(f"{path}.evidence.metric_atom_id must be a non-empty string")

            if gate_id not in id_to_atom:
                die(f"{path} broken link: gate_atom_id {gate_id!r} not found")
            if met_id not in id_to_atom:
                die(f"{path} broken link: metric_atom_id {met_id!r} not found")

            if atom_type(gate_id) != "gate_flip":
                die(f"{path} link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(met_id) != "metric_delta":
                die(f"{path} link type mismatch: metric_atom_id must point to type 'metric_delta'")

    print("[contract] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)

