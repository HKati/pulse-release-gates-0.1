#!/usr/bin/env python3
"""
policy_to_require_args.py

Purpose
-------
Materialize gate IDs from `pulse_gate_policy_v0.yml` so CI and local runs
do not hardcode `--require ...` lists.

Behavior
--------
- `--set advisory`:
  - missing set OR empty set => OK, print nothing
- any other `--set`:
  - missing set OR empty set => error, non-zero

Supports multiline and inline list forms:

  gates:
    required:
      - gate_a
      - gate_b

    core_required: [gate_a, gate_b]

    advisory: []

Policy-defined gate sets are accepted. The CLI is not limited to a fixed
hardcoded set list, so non-active proof sets such as
`slsa_vsa_recorded_intake_candidate` can be materialized through the same
policy path.

Design constraints
------------------
- No external dependencies.
- No PyYAML.
- Minimal parser tailored to the `gates:` mapping in `pulse_gate_policy_v0.yml`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def _strip_inline_comment(s: str) -> str:
    """Drop anything after # and trim whitespace."""
    return s.split("#", 1)[0].strip()


def _parse_inline_list(value: str) -> List[str]:
    """
    Parses inline YAML-like lists:

    [] -> []
    [a, b] -> ["a", "b"]
    """
    v = value.strip()
    if not (v.startswith("[") and v.endswith("]")):
        return []

    inner = v[1:-1].strip()
    if not inner:
        return []

    parts = [part.strip() for part in inner.split(",")]
    return [part for part in parts if part]


def _extract_gate_sets(text: str) -> dict[str, List[str]]:
    """
    Return every gate set declared under the top-level `gates:` mapping.

    Supports:

      gates:
        required:
          - gate_a
          - gate_b

        core_required: [gate_a, gate_b]

        advisory: []
    """
    gate_sets: dict[str, List[str]] = {}

    lines = text.splitlines()
    in_gates = False
    current_set: str | None = None
    gates_indent: int | None = None
    set_indent: int | None = None

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        clean = _strip_inline_comment(stripped)
        if not clean:
            continue

        indent = len(line) - len(line.lstrip(" "))

        if clean == "gates:":
            in_gates = True
            current_set = None
            gates_indent = indent
            set_indent = None
            continue

        if (
            in_gates
            and gates_indent is not None
            and indent <= gates_indent
            and ":" in clean
            and clean != "gates:"
        ):
            break

        if not in_gates:
            continue

        if (
            current_set is not None
            and set_indent is not None
            and indent == set_indent
            and ":" in clean
            and not clean.startswith("-")
        ):
            current_set = None
            set_indent = None

        if ":" in clean and not clean.startswith("-"):
            key, rest = clean.split(":", 1)
            key = key.strip()
            rest = rest.strip()

            if key:
                gate_sets.setdefault(key, [])
                current_set = key
                set_indent = indent

                if rest.startswith("[") and rest.endswith("]"):
                    gate_sets[key].extend(_parse_inline_list(rest))
                    current_set = None

                continue

        if current_set is not None and clean.startswith("- "):
            gate_id = _strip_inline_comment(clean[2:])
            if gate_id:
                gate_sets[current_set].append(gate_id)

    return gate_sets


def _extract_gate_set(text: str, gate_set: str) -> Tuple[bool, List[str]]:
    """
    Backward-compatible single-set extractor.

    Kept for callers/tests that may import this helper directly.
    """
    gate_sets = _extract_gate_sets(text)
    return gate_set in gate_sets, gate_sets.get(gate_set, [])


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
        help="Gate set name from pulse_gate_policy_v0.yml (default: required)",
    )

    ap.add_argument(
        "--format",
        default="space",
        choices=["space", "newline"],
        help="Output format (default: space)",
    )

    args = ap.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.exists():
        print(
            f"[policy_to_require_args] Policy file not found: {policy_path}",
            file=sys.stderr,
        )
        return 2

    text = policy_path.read_text(encoding="utf-8")
    gate_sets = _extract_gate_sets(text)

    if args.set == "advisory" and args.set not in gate_sets:
        return 0

    if args.set not in gate_sets:
        print(
            f"[policy_to_require_args] Gate set not found: {args.set}",
            file=sys.stderr,
        )
        return 3

    gates = gate_sets[args.set]

    if args.set == "advisory" and not gates:
        return 0

    if not gates:
        print(
            f"[policy_to_require_args] Gate set is empty: {args.set}",
            file=sys.stderr,
        )
        return 3

    if args.format == "newline":
        print("\n".join(gates))
    else:
        print(" ".join(gates))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
