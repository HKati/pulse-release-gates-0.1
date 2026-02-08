#!/usr/bin/env python3
"""
check_theory_overlay_v0_contract.py

Fail-closed contract checks for theory_overlay_v0.json without external deps.

Expected usage (matches workflow):
  python scripts/check_theory_overlay_v0_contract.py --in path/to/theory_overlay_v0.json

Also supports positional fallback:
  python scripts/check_theory_overlay_v0_contract.py path/to/theory_overlay_v0.json
"""

import argparse
import json
import sys
from typing import Any


REQUIRED_TOP_KEYS = ["schema", "inputs_digest", "gates_shadow", "cases", "evidence"]
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "MISSING"}


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--in",
        dest="in_path",
        default=None,
        help="Input JSON path (theory_overlay_v0.json).",
    )
    ap.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Input JSON path (positional fallback).",
    )
    args = ap.parse_args()

    path = args.in_path or args.path
    if not path:
        return _err("No input provided. Use --in <path> or positional <path>.")

    try:
        data = _load_json(path)
    except FileNotFoundError:
        return _err(f"Input file not found: {path}")
    except json.JSONDecodeError as e:
        return _err(f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        return _err(f"Top-level JSON must be an object, got {type(data).__name__}")

    for k in REQUIRED_TOP_KEYS:
        if k not in data:
            return _err(f"Missing top-level key: {k}")

    if data["schema"] != "theory_overlay_v0":
        return _err("schema must be exactly 'theory_overlay_v0'")

    if not isinstance(data["inputs_digest"], str) or not data["inputs_digest"]:
        return _err("inputs_digest must be a non-empty string")

    gates = data["gates_shadow"]
    if not isinstance(gates, dict):
        return _err("gates_shadow must be an object")

    for gname, gval in gates.items():
        if not isinstance(gname, str) or not gname:
            return _err("gates_shadow keys must be non-empty strings")
        if not isinstance(gval, dict):
            return _err(f"gate '{gname}' must be an object")
        if "status" not in gval:
            return _err(f"gate '{gname}' missing required field: status")
        st = gval["status"]
        if st not in ALLOWED_GATE_STATUSES:
            return _err(f"gate '{gname}' has invalid status: {st}")

    if not isinstance(data["cases"], list):
        return _err("cases must be an array")

    if not isinstance(data["evidence"], dict):
        return _err("evidence must be an object")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
