#!/usr/bin/env python3
# scripts/check_gate_metric_tension_acceptance_v0.py

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[acceptance] {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance check for gate_metric_tension atoms")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--min-count", type=int, default=1, help="Minimum required count")
    args = ap.parse_args()

    try:
        data = json.load(open(args.in_path, "r", encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {args.in_path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON: {e}")

    if not isinstance(data, dict):
        die("root must be an object/dict")

    atoms_any = data.get("atoms")
    if not isinstance(atoms_any, list):
        die("$.atoms must be an array/list")

    atoms: List[Dict[str, Any]] = []
    for i, a in enumerate(atoms_any):
        if not isinstance(a, dict):
            die(f"$.atoms[{i}] must be an object/dict")
        atoms.append(a)

    id_to_type: Dict[str, str] = {}
    for a in atoms:
        aid = a.get("atom_id")
        typ = a.get("type")
        if isinstance(aid, str) and isinstance(typ, str):
            id_to_type[aid] = typ

    tensions = [a for a in atoms if a.get("type") == "gate_metric_tension"]
    if len(tensions) < args.min_count:
        die(f"missing gate_metric_tension atoms (found={len(tensions)}, required>={args.min_count})")

    # Verify link integrity & types
    for idx, a in enumerate(tensions):
        ev = a.get("evidence")
        if not isinstance(ev, dict):
            die(f"gate_metric_tension[{idx}] evidence must be an object/dict")

        gate_atom_id = ev.get("gate_atom_id")
        metric_atom_id = ev.get("metric_atom_id")
        if not isinstance(gate_atom_id, str) or not gate_atom_id:
            die(f"gate_metric_tension[{idx}] missing evidence.gate_atom_id")
        if not isinstance(metric_atom_id, str) or not metric_atom_id:
            die(f"gate_metric_tension[{idx}] missing evidence.metric_atom_id")

        if gate_atom_id not in id_to_type:
            die(f"gate_metric_tension[{idx}] broken link gate_atom_id={gate_atom_id!r}")
        if metric_atom_id not in id_to_type:
            die(f"gate_metric_tension[{idx}] broken link metric_atom_id={metric_atom_id!r}")

        if id_to_type[gate_atom_id] != "gate_flip":
            die(f"gate_metric_tension[{idx}] gate_atom_id must link to type gate_flip")
        if id_to_type[metric_atom_id] != "metric_delta":
            die(f"gate_metric_tension[{idx}] metric_atom_id must link to type metric_delta")

    print("[acceptance] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
