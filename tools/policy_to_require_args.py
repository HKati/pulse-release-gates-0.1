#!/usr/bin/env python3
"""
policy_to_require_args.py

Purpose
-------
Materialize gate IDs from `pulse_gate_policy_v0.yml` so CI and local runs do not
hardcode `--require ...` lists.

Behavior
--------
- `--set required`:
    - missing set OR empty set => error (non-zero)
- `--set core_required`:
    - missing set OR empty set => error (non-zero)
- `--set release_required`:
    - missing set OR empty set => error (non-zero)
- `--set advisory`:
    - missing set OR empty set => valid (exit 0, print nothing)

Supports inline list forms:
  advisory: []
  required: [a, b, c]
  core_required: [a, b, c]
  release_required: [a, b, c]

Design constraints
------------------
- No external dependencies (no PyYAML).
- Minimal parsing tailored to the policy layout under:
    gates:
      required: ...
      core_required: ...
      release_required: ...
      advisory: ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def _strip_inline_comment(s: str) -> str:
    # Keep it simple: drop anything after '#'
    return s.split("#", 1)[0].strip()


def _parse_inline_list(value: str) -> List[str]:
    """
    Parses:
      "[]" -> []
      "[a, b]" -> ["a", "b"]
    """
    v = value.strip()
    if not (v.startswith("[") and v.endswith("]")):
        return []

    inner = v[1:-1].strip()
    if not inner:
        return []

    parts = [p.strip() for p in inner.split(",")]
    return [p for p in parts if p]


def _extract_gate_set(text: str, gate_set: str) -> Tuple[bool, List[str]]:
    """
    Extracts gates from:

      gates:
        <gate_set>:
          - gate_id

    Also supports:
        <gate_set>: []
        <gate_set>: [a, b, c]

    Returns:
      (found_set, gates)
    """
    lines = text.splitlines()

    in_gates = False
    in_set = False
    gates_indent = None
    set_indent = None
    found_set = False

    out: List[str] = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        clean = _strip_inline_comment(stripped)
        if not clean:
            continue

        indent = len(line) - len(line.lstrip(" "))

        # Enter "gates:" block
        if clean == "gates:":
            in_gates = True
            in_set = False
            gates_indent = indent
            set_indent = None
            continue

        # Leave "gates:" block when we hit a top-level (or same-level) mapping key
        if in_gates and gates_indent is not None and indent <= gates_indent and ":" in clean and clean != "gates:":
            in_gates = False
            in_set = False
            gates_indent = None
            set_indent = None

        if not in_gates:
            continue

        # If we are inside a set and hit a sibling key (including inline values), leave the set
        if in_set and set_indent is not None and indent == set_indent and ":" in clean and not clean.startswith("-"):
            key = clean.split(":", 1)[0].strip()
            if key and key != gate_set:
                in_set = False
                set_indent = None
                # do not continue; allow processing of the current line below

        # Enter target set: "<gate_set>:" or "<gate_set>: []" or "<gate_set>: [a,b]"
        if ":" in clean and not clean.startswith("-"):
            key, rest = clean.split(":", 1)
            key = key.strip()
            rest = rest.strip()

            if key == gate_set:
                found_set = True
                set_indent = indent

                # Inline list form
                if rest.startswith("[") and rest.endswith("]"):
                    out.extend(_parse_inline_list(rest))
                    in_set = False
                    continue

                # Multi-line list form
                in_set = True
                continue

        if not in_set:
            continue

        # Capture list items "- gate_id"
        if clean.startswith("- "):
            gate_id = _strip_inline_comment(clean[2:])
            if gate_id:
                out.append(gate_id)

    return found_set, out


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
        choices=["required", "core_required", "release_required", "advisory"],
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
    found_set, gates = _extract_gate_set(text, args.set)

    # Advisory is optional and may be empty.
    if args.set == "advisory":
        if not found_set or not gates:
            return 0

    # Required-like sets (required, core_required, release_required)
    # must exist and must be non-empty.
    if not found_set:
        print(f"[policy_to_require_args] Gate set not found: {args.set}", file=sys.stderr)
        return 3

    if not gates:
        print(f"[policy_to_require_args] Gate set is empty: {args.set}", file=sys.stderr)
        return 3

    if args.format == "newline":
        print("\n".join(gates))
    else:
        print(" ".join(gates))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
