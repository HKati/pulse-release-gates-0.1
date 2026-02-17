#!/usr/bin/env python3
"""
Compile-time smoke test for critical safe-pack tools.

Purpose:
- Catch SyntaxError / IndentationError / import-time failures early in CI.
- Keep it deterministic and fast (no execution of tools, only compilation).

This is a guardrail against "script exists but cannot even run" regressions.
"""

from __future__ import annotations

import pathlib
import py_compile
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _error(path: pathlib.Path, msg: str) -> None:
    print(f"::error file={path}::{msg}")


def _warn(path: pathlib.Path, msg: str) -> None:
    print(f"::warning file={path}::{msg}")


def main() -> int:
    targets = [
        # Safe-pack entrypoints / critical path tools
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py",
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "augment_status.py",
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py",
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "refusal_delta.py",
        # Reporting helpers used by snapshot pipeline
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "status_to_summary.py",
        REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "update_artifacts_for_snapshot.py",
    ]

    ok = True

    for p in targets:
        if not p.exists():
            _error(p, "Missing expected tool file")
            ok = False
            continue

        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            _error(p, f"py_compile failed: {e}")
            ok = False

    # Soft hint for contributors: if you intentionally delete/rename tools, update this list.
    if ok:
        print(f"OK: compiled {len(targets)} safe-pack tool(s)")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
