#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tests" / "tools" / "generate_core_baseline_v0.py"


def test_core_baseline_v0() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, (
        f"baseline check failed\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    )
