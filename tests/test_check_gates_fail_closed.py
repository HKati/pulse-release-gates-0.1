#!/usr/bin/env python3
"""
Smoke test for PULSE_safe_pack_v0/tools/check_gates.py

Locks down fail-closed semantics and exit codes:
- 0: all required gates are literal True
- 1: at least one required gate is present but not literal True
- 2: missing required gate(s) OR status missing/invalid
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"


def _write_status(path: pathlib.Path, gates: dict) -> None:
    status = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": gates,
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(status_path: pathlib.Path, require: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, str(TOOL), "--status", str(status_path), "--require", *require],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_rc(p: subprocess.CompletedProcess[str], rc: int) -> None:
    if p.returncode != rc:
        raise AssertionError(
            f"Unexpected return code: expected={rc} got={p.returncode}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def test_check_gates_fail_closed() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"

        _write_status(
            status_path,
            {
                "gate_true": True,
                "gate_false": False,
                "gate_str": "true",  # should NOT pass
            },
        )

        # PASS
        p = _run(status_path, ["gate_true"])
        _assert_rc(p, 0)

        # FAIL (false)
        p = _run(status_path, ["gate_false"])
        _assert_rc(p, 1)

        # FAIL (non-bool truthy)
        p = _run(status_path, ["gate_str"])
        _assert_rc(p, 1)

        # Missing gate => exit 2
        p = _run(status_path, ["missing_gate"])
        _assert_rc(p, 2)

        # Missing dominates (even if another gate fails)
        p = _run(status_path, ["gate_false", "missing_gate"])
        _assert_rc(p, 2)

        # Duplicate requires should not break
        p = _run(status_path, ["gate_true", "gate_true"])
        _assert_rc(p, 0)


def main() -> int:
    try:
        test_check_gates_fail_closed()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: check_gates fail-closed smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
