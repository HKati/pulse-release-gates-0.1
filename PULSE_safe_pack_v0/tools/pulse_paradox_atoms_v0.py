#!/usr/bin/env python3
"""Compatibility wrapper for the nested paradox-atoms tool."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve()
    target = (
        here.parent
        / "PULSE_safe_pack_v0"
        / "tools"
        / "pulse_paradox_atoms_v0.py"
    )

    if not target.is_file():
        print(f"error: target script not found: {target}", file=sys.stderr)
        return 1

    return subprocess.call([sys.executable, str(target), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
