#!/usr/bin/env python3
"""
Stable entrypoint wrapper for the overlay-only docs example acceptance checker.

Why:
- CI should call `python scripts/...` consistently.
- The actual implementation lives under `scripts/scripts/`.

This wrapper delegates to:
  scripts/scripts/check_paradox_examples_transitions_case_study_v0_overlay_only_acceptance.py
"""

from __future__ import annotations

import os
import runpy
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(
        here,
        "scripts",
        "check_paradox_examples_transitions_case_study_v0_overlay_only_acceptance.py",
    )

    if not os.path.isfile(target):
        raise SystemExit(f"[overlay-only-acceptance-wrapper] target not found: {target}")

    # Preserve CLI argv, but make argv[0] point at the delegated script for nicer errors/help.
    sys.argv[0] = target
    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
