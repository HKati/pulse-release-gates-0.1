#!/usr/bin/env python3
"""
check_paradox_examples_transitions_case_study_v0_acceptance.py

Thin wrapper to keep the acceptance checker discoverable at:
  scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py

The real implementation currently lives under:
  scripts/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py

This wrapper avoids CI "Permission denied" issues and stabilizes the call site.
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
    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
