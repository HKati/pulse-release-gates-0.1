#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Guard: ensure pulse_ci.yml contains exactly one tools/run_all.py invocation "
            "and it uses explicit --mode."
        )
    )
    ap.add_argument(
        "--workflow",
        default=".github/workflows/pulse_ci.yml",
        help="Path to workflow file (default: .github/workflows/pulse_ci.yml)",
    )
    ap.add_argument(
        "--expected",
        type=int,
        default=1,
        help="Expected number of tools/run_all.py occurrences (default: 1)",
    )
    ap.add_argument(
        "--mode_window_lines",
        type=int,
        default=14,
        help="How many lines after the invocation to scan for --mode (default: 14)",
    )
    args = ap.parse_args()

    wf = pathlib.Path(args.workflow)
    if not wf.exists():
        print(f"FAIL: workflow file not found: {wf}", file=sys.stderr)
        return 1

    lines = wf.read_text(encoding="utf-8").splitlines()

    hits: list[int] = []
    for i, line in enumerate(lines, start=1):
        s = line.lstrip()
        if s.startswith("#"):
            continue
        if "tools/run_all.py" in line:
            hits.append(i)

    if len(hits) != args.expected:
        print(
            f"FAIL: expected {args.expected} tools/run_all.py occurrence(s), found {len(hits)} at lines {hits}",
            file=sys.stderr,
        )
        return 1

    # Enforce explicit --mode near the invocation (same block / next few lines)
    start_idx = hits[0] - 1
    end_idx = min(start_idx + args.mode_window_lines, len(lines))
    window = "\n".join(lines[start_idx:end_idx])

    if "--mode" not in window:
        print(
            f"FAIL: tools/run_all.py invocation at line {hits[0]} missing explicit --mode within next {args.mode_window_lines} lines",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {wf}: exactly {args.expected} invocation(s) and explicit --mode present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
