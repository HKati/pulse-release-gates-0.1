#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description="Fail-closed contract check for paradox_field_v0.json")
    ap.add_argument("--transitions-dir", required=True, help="Directory containing pulse_*_drift_v0 outputs")
    ap.add_argument("--out", required=True, help="Output paradox_field_v0.json path")
    args = ap.parse_args()

    # 1) Generate paradox field from transitions drift (must succeed)
    subprocess.check_call([
        sys.executable,
        "scripts/paradox_field_adapter_v0.py",
        "--transitions-dir", args.transitions_dir,
        "--out", args.out,
    ])

    # 2) Contract checks (fail-closed)
    if not os.path.isfile(args.out):
        raise SystemExit(f"[check] missing output json: {args.out}")

    o = json.load(open(args.out, "r", encoding="utf-8"))
    root = o.get("paradox_field_v0")
    if not isinstance(root, dict):
        raise SystemExit("[check] missing paradox_field_v0 root object")

    atoms = root.get("atoms")
    if not isinstance(atoms, list) or len(atoms) == 0:
        raise SystemExit("[check] atoms must be a non-empty list")

    # must contain gate_overlay_tension
    tensions = [a for a in atoms if isinstance(a, dict) and a.get("type") == "gate_overlay_tension"]
    if not tensions:
        raise SystemExit("[check] missing gate_overlay_tension atoms")

    t0 = tensions[0]
    if not t0.get("title"):
        raise SystemExit("[check] tension atom must have title")

    ev = t0.get("evidence", {})
    if not isinstance(ev, dict):
        raise SystemExit("[check] tension atom evidence must be an object")

    if not ev.get("gate_atom_id"):
        raise SystemExit("[check] tension evidence missing gate_atom_id")
    if not ev.get("overlay_atom_id"):
        raise SystemExit("[check] tension evidence missing overlay_atom_id")

    print("[check] OK: paradox_field_v0 atoms + tension contract")


if __name__ == "__main__":
    main()
