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
- fail-closed: returns non-zero on invalid or incomplete input
"""

import argparse
import json
import sys
from typing import Any, Dict


REQUIRED_TOP_KEYS = ["schema", "inputs_digest", "gates_shadow", "cases", "evidence"]
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "MISSING"}


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt(value: Any) -> str:
    return "_n/a_" if value is None else str(value)


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

    # Fail-closed: required keys must be present (schema contract minimum)
    for k in REQUIRED_TOP_KEYS:
        if k not in data:
            return _err(f"Missing required top-level key: {k}")

    schema = data["schema"]
    if schema != "theory_overlay_v0":
        return _err("schema must be exactly 'theory_overlay_v0'")

    inputs_digest = data["inputs_digest"]
    gates = data["gates_shadow"]
    cases = data["cases"]
    evidence = data["evidence"]

    if not isinstance(inputs_digest, str) or not inputs_digest:
        return _err("inputs_digest must be a non-empty string")
    if not isinstance(gates, dict):
        return _err("gates_shadow must be an object")
    if not isinstance(cases, list):
        return _err("cases must be an array")
    if not isinstance(evidence, dict):
        return _err("evidence must be an object")

    # Optional but useful: validate minimal gate entry shape
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

    # Render (deterministic ordering)
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
        for name in sorted(gates.keys()):
            g = gates[name]
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

    lines.append("")
    lines.append("## Evidence (top-level keys)")
    if evidence:
        for k in sorted(evidence.keys()):
            lines.append(f"- `{k}`")
    else:
        lines.append("_none_")

    rh = evidence.get("release_hypothesis")
    if isinstance(rh, dict):
        rh_status = _fmt(rh.get("status"))
        lines.append(f"- evidence_status: `{rh_status}`")

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
