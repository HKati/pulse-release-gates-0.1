#!/usr/bin/env python3
"""
check_paradox_empty_edges_v0_acceptance.py — acceptance check for the empty-edges regression case.

This fixture protects a valid scenario:
- paradox_field_v0.json contains meta.run_context (stable fingerprint)
- paradox_edges_v0.jsonl is empty (0 edges)

Rationale:
Edges are JSONL and have no file-level header. If there are zero tension atoms, the
exporter may legitimately emit zero edges, thus there is no per-edge run_context to compare.
Contract checks must remain compatible with this case.

Usage:
  python scripts/check_paradox_empty_edges_v0_acceptance.py \
    --field out/empty_edges/paradox_field_v0.json \
    --edges out/empty_edges/paradox_edges_v0.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[empty-edges-acceptance] {msg}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _field_root(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        die("field must be a JSON object")
    inner = obj.get("paradox_field_v0")
    if isinstance(inner, dict):
        return inner
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance: field has run_context, edges JSONL is empty (0 edges).")
    ap.add_argument("--field", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--edges", required=True, help="Path to paradox_edges_v0.jsonl")
    args = ap.parse_args()

    if not os.path.isfile(args.field):
        die(f"--field not found: {args.field}")
    if not os.path.isfile(args.edges):
        die(f"--edges not found: {args.edges}")

    field_obj = _read_json(args.field)
    root = _field_root(field_obj)

    meta = root.get("meta")
    if not isinstance(meta, dict):
        die("field meta must be an object/dict")

    run_ctx = meta.get("run_context")
    if not isinstance(run_ctx, dict):
        die("field meta.run_context must be present and an object/dict in this fixture")

    rpid = run_ctx.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die("field meta.run_context.run_pair_id must be a non-empty string")

    # Edges must be empty: no non-blank JSONL lines.
    edges_count = 0
    first_edge_hint = ""
    with open(args.edges, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            edges_count += 1
            if not first_edge_hint:
                # Best-effort parse for debugging hints
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        first_edge_hint = f"edge_id={obj.get('edge_id')!r} type={obj.get('type')!r}"
                    else:
                        first_edge_hint = f"non-dict JSON at line {line_no}"
                except Exception:
                    first_edge_hint = f"unparseable JSON at line {line_no}"
            # No need to read further in this acceptance.
            break

    if edges_count != 0:
        extra = f" ({first_edge_hint})" if first_edge_hint else ""
        die(f"expected 0 edges, found {edges_count}{extra}")

    print(f"[empty-edges-acceptance] OK (run_pair_id={rpid.strip()} edges=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
