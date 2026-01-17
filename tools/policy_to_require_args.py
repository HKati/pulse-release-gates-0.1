#!/usr/bin/env python3
"""
policy_to_require_args.py

Purpose
-------
Materialize the gate list from `pulse_gate_policy_v0.yml` so CI and local runs
do not need to hardcode `--require ...` arguments.

Outputs
-------
By default prints the selected gate set as a single space-separated line:
  pass_controls_refusal effect_present ...

This is suitable for:
  --require $(python tools/policy_to_require_args.py)

Design constraints
------------------
- No external dependencies (no PyYAML).
- Minimal indentation-based parsing tailored to the policy structure:
    gates:
      required:
        - ...
      advisory:
        - ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List


def _strip_inline_comment(s: str) -> str:
    # Remove inline comments while keeping gate ids clean.
    # Example: "- q1_grounded_ok  # comment" -> "q1_grounded_ok"
    return s.split("#", 1)[0].strip()


def _extract_gate_set(text: str, gate_set: str) -> List[str]:
    """
    Extracts gates from:
      gates:
        <gate_set>:
          - gate_id
    """
    lines = text.splitlines()

    in_gates = False
    in_set = False
    gates_indent = None
    set_indent = None

    out: List[str] = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        # Enter "gates:" block
        if stripped == "gates:":
            in_gates = True
            in_set = False
            gates_indent = indent
            set_indent = None
            continue

        # If we were in gates block and hit a top-level key, exit gates block
        if in_gates and gates_indent is not None and indent <= gates_indent and stripped.endswith(":") and stripped != "gates:":
            in_gates = False
            in_set = False
            gates_indent = None
            set_indent = None

        if not in_gates:
            continue

        # Enter target set, e.g. "required:"
        if stripped == f"{gate_set}:":
            in_set = True
            set_indent = indent
            continue

        # If we are in the target set and hit a sibling key, leave set
        if in_set and set_indent is not None and indent == set_indent and stripped.endswith(":") and stripped != f"{gate_set}:":
            in_set = False
            set_indent = None
            continue

        if not in_set:
            continue

        # Capture list items "- <gate_id>"
        if stripped.startswith("- "):
            item = _strip_inline_comment(stripped[2:])
            if item:
                out.append(item)

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--policy",
        default="pulse_gate_policy_v0.yml",
        help="Path to the gate policy YAML (default: pulse_gate_policy_v0.yml)",
    )
    ap.add_argument(
        "--set",
        default="required",
        choices=["required", "advisory"],
        help="Which gate set to print (default: required)",
    )
    ap.add_argument(
        "--format",
        default="space",
        choices=["space", "newline"],
        help="Output format (default: space)",
    )
    args = ap.parse_args()

    p = Path(args.policy)
    if not p.exists():
        print(f"[policy_to_require_args] Policy file not found: {p}", file=sys.stderr)
        return 2

    text = p.read_text(encoding="utf-8")
    gates = _extract_gate_set(text, args.set)

    if not gates:
        print(f"[policy_to_require_args] No gates found for set: {args.set}", file=sys.stderr)
        return 3

    if args.format == "newline":
        print("\n".join(gates))
    else:
        print(" ".join(gates))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
