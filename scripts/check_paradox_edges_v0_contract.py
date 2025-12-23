
# ✅ FILE TO REPLACE (copy-paste the whole file)
# Path: scripts/check_paradox_edges_v0_contract.py

```python
#!/usr/bin/env python3
"""
check_paradox_edges_v0_contract.py — fail-closed contract check for paradox_edges_v0.jsonl

Goals (v0):
- Validate JSONL format (each line is a JSON object)
- Required fields exist with correct types
- edge_id is unique
- Deterministic ordering (accept either):
  A) severity (crit>warn>info) -> type -> edge_id
  B) type -> edge_id
- If --atoms is provided: validate links and expected atom types:
  - gate_metric_tension edge: src=gate_flip, dst=metric_delta, tension_atom_id=gate_metric_tension
  - gate_overlay_tension edge: src=gate_flip, dst=overlay_change, tension_atom_id=gate_overlay_tension
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


SEVERITY_ORDER: Dict[str, int] = {"crit": 0, "warn": 1, "info": 2}
ALLOWED_SEVERITIES = set(SEVERITY_ORDER.keys())

# Known edge types and expected atom types (src, dst, tension)
EDGE_EXPECTATIONS: Dict[str, Tuple[str, str, str]] = {
    "gate_metric_tension": ("gate_flip", "metric_delta", "gate_metric_tension"),
    "gate_overlay_tension": ("gate_flip", "overlay_change", "gate_overlay_tension"),
}


def die(msg: str) -> None:
    raise SystemExit(f"[edges-contract] {msg}")


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


def severity_rank(sev: str) -> int:
    if sev not in SEVERITY_ORDER:
        die(f"severity must be one of {sorted(ALLOWED_SEVERITIES)} (got {sev!r})")
    return SEVERITY_ORDER[sev]


def check_sorted_non_decreasing(keys: List[Tuple[Any, ...]]) -> bool:
    for i in range(1, len(keys)):
        if keys[i - 1] > keys[i]:
            return False
    return True


def load_atoms_map(atoms_path: str) -> Dict[str, str]:
    try:
        with open(atoms_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        die(f"--atoms file not found: {atoms_path}")
    except json.JSONDecodeError as e:
        die(f"--atoms invalid JSON: {e}")

    if not isinstance(data, dict):
        die("--atoms root must be an object/dict")

    root = data.get("paradox_field_v0") if isinstance(data.get("paradox_field_v0"), dict) else data
    atoms = root.get("atoms")
    if not isinstance(atoms, list):
        die("--atoms: missing or invalid atoms list")

    m: Dict[str, str] = {}
    for i, a in enumerate(atoms):
        if not isinstance(a, dict):
            die(f"--atoms: atoms[{i}] must be an object/dict")
        aid = a.get("atom_id")
        typ = a.get("type")
        if not isinstance(aid, str) or not aid:
            die(f"--atoms: atoms[{i}].atom_id must be a non-empty string")
        if not isinstance(typ, str) or not typ:
            die(f"--atoms: atoms[{i}].type must be a non-empty string")
        m[aid] = typ
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract check for paradox_edges_v0.jsonl")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0.jsonl")
    ap.add_argument(
        "--atoms",
        dest="atoms_path",
        default="",
        help="Optional path to paradox_field_v0.json for link/type validation",
    )
    args = ap.parse_args()

    atoms_type_by_id: Dict[str, str] = {}
    if args.atoms_path:
        atoms_type_by_id = load_atoms_map(args.atoms_path)

    try:
        with open(args.in_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        die(f"file not found: {args.in_path}")

    edges: List[Dict[str, Any]] = []
    for ln, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            die(f"{args.in_path}:{ln} invalid JSON: {e}")
        if not isinstance(obj, dict):
            die(f"{args.in_path}:{ln} must be a JSON object/dict per line")
        edges.append(obj)

    if not edges:
        die("edges file is empty (expected >= 1 edge)")

    seen_edge_ids = set()
    keys_sev: List[Tuple[int, str, str]] = []
    keys_type: List[Tuple[str, str]] = []

    for i, e in enumerate(edges):
        path = f"edges[{i}]"

        eid = req_str(e, "edge_id", path)
        if eid in seen_edge_ids:
            die(f"duplicate edge_id: {eid!r}")
        seen_edge_ids.add(eid)

        etype = req_str(e, "type", path)
        sev = req_str(e, "severity", path)
        srank = severity_rank(sev)

        src = req_str(e, "src_atom_id", path)
        dst = req_str(e, "dst_atom_id", path)
        _ = req_str(e, "rule", path)

        # tension_atom_id is required for tension edges
        tension_id = req_str(e, "tension_atom_id", path)

        keys_sev.append((srank, etype, eid))
        keys_type.append((etype, eid))

        # Link/type validation if atoms map provided
        if atoms_type_by_id:
            if src not in atoms_type_by_id:
                die(f"{path} broken link: src_atom_id {src!r} not found in atoms")
            if dst not in atoms_type_by_id:
                die(f"{path} broken link: dst_atom_id {dst!r} not found in atoms")
            if tension_id not in atoms_type_by_id:
                die(f"{path} broken link: tension_atom_id {tension_id!r} not found in atoms")

            # Enforce known edge type expectations
            exp = EDGE_EXPECTATIONS.get(etype)
            if exp is not None:
                exp_src, exp_dst, exp_tension = exp
                if atoms_type_by_id[src] != exp_src:
                    die(
                        f"{path} type mismatch: src_atom_id must be {exp_src!r} "
                        f"(got {atoms_type_by_id[src]!r})"
                    )
                if atoms_type_by_id[dst] != exp_dst:
                    die(
                        f"{path} type mismatch: dst_atom_id must be {exp_dst!r} "
                        f"(got {atoms_type_by_id[dst]!r})"
                    )
                if atoms_type_by_id[tension_id] != exp_tension:
                    die(
                        f"{path} type mismatch: tension_atom_id must be {exp_tension!r} "
                        f"(got {atoms_type_by_id[tension_id]!r})"
                    )

    # Deterministic ordering: accept either scheme A or B (fail-closed if neither)
    ok_a = check_sorted_non_decreasing(keys_sev)
    ok_b = check_sorted_non_decreasing(keys_type)
    if not (ok_a or ok_b):
        die(
            "edges are not deterministically ordered. Expected either:\n"
            "A) severity (crit>warn>info) -> type -> edge_id\n"
            "B) type -> edge_id"
        )

    print("[edges-contract] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
