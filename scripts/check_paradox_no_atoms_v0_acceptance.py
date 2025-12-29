#!/usr/bin/env python3
"""
check_paradox_no_atoms_v0_acceptance.py

Acceptance check for tests/fixtures/transitions_no_atoms_v0.

Asserts:
- paradox_field_v0.json contains zero atoms
- paradox_edges_v0.jsonl contains zero edges (no non-empty JSONL lines)
- if meta.run_context is present, it contains a non-empty run_pair_id

Usage:
  python scripts/check_paradox_no_atoms_v0_acceptance.py \
    --field out/no_atoms/paradox_field_v0.json \
    --edges out/no_atoms/paradox_edges_v0.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[no-atoms-acceptance] {msg}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance check for transitions_no_atoms_v0 fixture.")
    ap.add_argument("--field", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--edges", required=True, help="Path to paradox_edges_v0.jsonl")
    args = ap.parse_args()

    if not os.path.isfile(args.field):
        die(f"field file not found: {args.field}")
    if not os.path.isfile(args.edges):
        die(f"edges file not found: {args.edges}")

    obj = _read_json(args.field)
    if not isinstance(obj, dict):
        die("field JSON must be an object at top-level")

    root = obj.get("paradox_field_v0", obj)
    if not isinstance(root, dict):
        die("field root must be an object (either $.paradox_field_v0 or $)")

    atoms = root.get("atoms")
    if not isinstance(atoms, list):
        die("$.atoms must be a list")
    if len(atoms) != 0:
        die(f"expected zero atoms, found {len(atoms)}")

    # Optional meta.run_context checks (fail-closed if present)
    meta_any = root.get("meta")
    if meta_any is not None:
        if not isinstance(meta_any, dict):
            die("$.meta must be an object/dict when present")

        rc_any = meta_any.get("run_context")
        if rc_any is not None:
            if not isinstance(rc_any, dict):
                die("$.meta.run_context must be an object/dict when present")
            rpid = rc_any.get("run_pair_id")
            if not isinstance(rpid, str) or not rpid.strip():
                die("$.meta.run_context.run_pair_id must be a non-empty string when run_context is present")

    # edges JSONL must be empty (no non-empty lines)
    non_empty = []
    with open(args.edges, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            non_empty.append((line_no, line[:200]))
            if len(non_empty) >= 3:
                break

    if non_empty:
        sample = "; ".join([f"line {ln}: {snip!r}" for ln, snip in non_empty])
        die(f"expected zero edges, but found non-empty JSONL lines (sample: {sample})")

    print("[no-atoms-acceptance] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
