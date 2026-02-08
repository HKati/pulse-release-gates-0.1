#!/usr/bin/env python3
"""
render_theory_overlay_v0_md.py

Render a short, human-readable Markdown summary from theory_overlay_v0.json.

Usage:
  python scripts/render_theory_overlay_v0_md.py --in PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json \
    --out PULSE_safe_pack_v0/artifacts/theory_overlay_v0.md

Notes:
- stdlib-only
- deterministic (no timestamps)
- fail-closed: returns non-zero on invalid input
"""

import argparse
import json
import sys
from typing import Any, Dict


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--in", dest="in_path", required=True, help="Input overlay JSON path.")
    ap.add_argument("--out", dest="out_path", required=True, help="Output markdown path.")
    args = ap.parse_args()

    try:
        data = _load_json(args.in_path)
    except FileNotFoundError:
        return _err(f"Input file not found: {args.in_path}")
    except json.JSONDecodeError as e:
        return _err(f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        return _err(f"Top-level JSON must be an object, got {type(data).__name__}")

    schema = data.get("schema")
    if schema != "theory_overlay_v0":
        return _err("schema must be exactly 'theory_overlay_v0'")

    inputs_digest = data.get("inputs_digest", "")
    gates = data.get("gates_shadow", {})
    cases = data.get("cases", [])
    evidence = data.get("evidence", {})

    if not isinstance(inputs_digest, str):
        return _err("inputs_digest must be a string")
    if not isinstance(gates, dict):
        return _err("gates_shadow must be an object")
    if not isinstance(cases, list):
        return _err("cases must be an array")
    if not isinstance(evidence, dict):
        return _err("evidence must be an object")

    # Render
    lines = []
    lines.append("# Theory Overlay v0 (shadow)")
    lines.append("")
    lines.append(f"- schema: `{schema}`")
    lines.append(f"- inputs_digest: `{inputs_digest}`")
    lines.append("")
    lines.append("## Gates (shadow)")
    if not gates:
        lines.append("")
        lines.append("_No gates reported._")
    else:
        # deterministic: sorted keys
        for name in sorted(gates.keys()):
            g = gates.get(name, {})
            if not isinstance(g, dict):
                lines.append(f"- **{name}**: `INVALID` — gate entry is not an object")
                continue
            st = g.get("status", "MISSING")
            reason = g.get("reason", "")
            if reason:
                lines.append(f"- **{name}**: `{st}` — {reason}")
            else:
                lines.append(f"- **{name}**: `{st}`")

    lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append(f"- count: `{len(cases)}`")

    # Keep evidence small + deterministic
    lines.append("")
    lines.append("## Evidence (top-level keys)")
    if evidence:
        for k in sorted(evidence.keys()):
            lines.append(f"- `{k}`")
    else:
        lines.append("_none_")

    lines.append("")

    try:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")
    except OSError as e:
        return _err(f"Failed to write output: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
