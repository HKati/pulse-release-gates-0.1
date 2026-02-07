#!/usr/bin/env python3
"""
Regression test: paradox diagram input v0 contract must reject booleans for numeric metrics.

Why:
- In Python, bool is a subclass of int, so naive isinstance(v, (int, float)) checks
  can accidentally accept JSON true/false as valid numbers.
- We lock in strict typing: numeric metrics must be real numbers, not booleans.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    # tests/... -> repo root
    return Path(__file__).resolve().parents[1]


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_contract_rejects_bool_metrics() -> None:
    root = _repo_root()
    script = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    assert script.exists(), f"missing contract checker script: {script}"

    # Minimal schema-shaped input, but with boolean values for numeric fields
    # (these MUST be rejected by the contract).
    bad = {
        "schema_version": "paradox_diagram_input_v0",
        "timestamp_utc": "2026-02-06T00:00:00+00:00",
        "shadow": True,
        "decision_key": "NORMAL",
        "decision_raw": "NORMAL",
        "metrics": {
            "settle_time_p95_ms": True,
            "settle_time_budget_ms": False,
            "downstream_error_rate": True,
            "paradox_density": False,
        },
    }

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        inp = base / "paradox_diagram_input_v0.json"
        _write_json(inp, bad)

        # Use absolute path + run from repo root to avoid CWD-dependent failures.
        p = subprocess.run(
            [sys.executable, str(script), "--in", str(inp)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )

        # Non-zero is the key invariant: bools must NOT be accepted as numbers.
        if p.returncode == 0:
            raise AssertionError(
                "Expected contract checker to reject bool metrics, but it exited 0.\n"
                f"stdout:\n{p.stdout}\n\nstderr:\n{p.stderr}\n"
            )
