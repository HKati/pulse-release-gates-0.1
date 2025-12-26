#!/usr/bin/env python3
"""
check_paradox_examples_transitions_case_study_v0_acceptance.py

Canonical entrypoint for the docs example acceptance checker.

The real implementation currently lives here:
  scripts/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py

This wrapper stabilizes the call site for CI and local runs and avoids
"Permission denied" issues (always run via `python ...`).
"""

from __future__ import annotations

import os
import runpy
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "scripts", "check_paradox_examples_transitions_case_study_v0_acceptance.py")

    if not os.path.isfile(target):
        raise SystemExit(f"[acceptance-wrapper] target script not found: {target}")

    # Make argparse/help output refer to the real script path
    sys.argv[0] = target

    # Ensure the target directory is importable (defensive)
    target_dir = os.path.dirname(target)
    if target_dir and target_dir not in sys.path:
        sys.path.insert(0, target_dir)

    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

