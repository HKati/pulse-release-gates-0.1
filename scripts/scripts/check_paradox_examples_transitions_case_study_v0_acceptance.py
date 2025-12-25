#!/usr/bin/env python3
"""
check_paradox_examples_transitions_case_study_v0_acceptance.py

Acceptance check for the non-fixture example under:
  docs/examples/transitions_case_study_v0/

This script is intentionally strict and pins a small set of invariants so the
example remains reproducible and CI-friendly.

It validates:
- edges JSONL is readable and non-empty
- run_context contains expected sha1 keys and expected run_pair_id
- must-contain tension edges by tension_atom_id + type

Usage:
  python scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py \
    --in out/paradox_edges_v0.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List


EXPECTED_RUN_CONTEXT: Dict[str, str] = {
    "run_pair_id": "3171fcc1fc47",
    "transitions_gate_csv_sha1": "0b23b3f9f7c0327484afe9d5ca36f7a482eafd84",
    "transitions_metric_csv_sha1": "78d179ec69c3ba506efc467b36c46513270110fe",
    "transitions_overlay_json_sha1": "fa475eb7fe00a607c4b510b7dbbda944ed9c742c",
    "transitions_json_sha1": "f8ed75d20643814c6bf7c1a6ce7b7af90cae0e1f",
}

# Must-contain tension edges for the docs example.
EXPECTED_TENSION_EDGES: List[Dict[str, str]] = [
    {"type": "gate_metric_tension", "tension_atom_id": "f5c720a2599a"},
    {"type": "gate_metric_tension", "tension_atom_id": "621a91f73ac2"},
    {"type": "gate_overlay_tension", "tension_atom_id": "64306cf439b0"},
]


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[examples-acceptance] {msg}")


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            s = raw.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as e:
                die(f"invalid JSONL at line {line_no}: {e}")
            if not isinstance(obj, dict):
                die(f"JSONL line {line_no} must be an object")
            out.append(obj)
    return out


def _req_str(d: Dict[str, Any], k: str, path: str) -> str:
    v = d.get(k)
    if not isinstance(v, str) or not v.strip():
        die(f"{path}.{k} must be a non-empty string")
    return v.strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Acceptance check for docs/examples/transitions_case_study_v0 edges output (JSONL)."
    )
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0.jsonl")
    args = ap.parse_args()

    if not os.path.isfile(args.in_path):
        die(f"file not found: {args.in_path}")

    edges = _read_jsonl(args.in_path)
    if not edges:
        die("edges JSONL is empty")

    # Validate run_context and pin expected keys/values.
    for i, e in enumerate(edges):
        path = f"edges[{i}]"
        _req_str(e, "edge_id", path)
        _req_str(e, "type", path)
        _req_str(e, "severity", path)
        _req_str(e, "src_atom_id", path)
        _req_str(e, "dst_atom_id", path)
        _req_str(e, "tension_atom_id", path)
        _req_str(e, "rule", path)

        rc = e.get("run_context")
        if not isinstance(rc, dict):
            die(f"{path}.run_context must be an object/dict")

        # Ensure expected run_context fields exist and match.
        for k, expected in EXPECTED_RUN_CONTEXT.items():
            got = rc.get(k)
            if not isinstance(got, str) or not got.strip():
                die(f"{path}.run_context.{k} missing or not a non-empty string")
            if got.strip() != expected:
                die(
                    f"{path}.run_context.{k} mismatch: expected {expected!r}, got {got.strip()!r}"
                )

    # Must-contain expected tension edges
    def _has_edge(expect: Dict[str, str]) -> bool:
        et = expect["type"]
        tid = expect["tension_atom_id"]
        for e in edges:
            if e.get("type") == et and e.get("tension_atom_id") == tid:
                return True
        return False

    for ex in EXPECTED_TENSION_EDGES:
        if not _has_edge(ex):
            die(f"missing expected edge: type={ex['type']!r} tension_atom_id={ex['tension_atom_id']!r}")

    print(f"[examples-acceptance] OK (edges={len(edges)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
