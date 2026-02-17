#!/usr/bin/env python3
"""
Compatibility wrapper for refusal-delta computation.

Some workflows/tools historically referenced:
  PULSE_safe_pack_v0/tools/refusal_delta.py

The current canonical implementation lives in:
  PULSE_safe_pack_v0/tools/refusal_delta_calc.py

This wrapper delegates execution to refusal_delta_calc.py to avoid pack-layout drift.
"""

from __future__ import annotations

import pathlib
import runpy
import sys


def main() -> int:
    here = pathlib.Path(__file__).resolve()
    target = here.with_name("refusal_delta_calc.py")

    if not target.exists():
        print(f"ERROR: refusal_delta_calc.py not found at {target}", file=sys.stderr)
        return 1

    try:
        # Delegate to the real implementation, preserving sys.argv.
        runpy.run_path(str(target), run_name="__main__")
        return 0
    except SystemExit as e:
        # Propagate the underlying script's exit code (best-effort).
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
