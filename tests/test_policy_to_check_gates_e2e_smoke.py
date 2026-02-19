#!/usr/bin/env python3
"""
E2E smoke: policy_to_require_args -> check_gates

Locks down the normative flow:
- materialize required gate list from pulse_gate_policy_v0.yml
- enforce it via PULSE_safe_pack_v0/tools/check_gates.py
- assert exit codes:
  * 0: all required gates literal True
  * 1: required gate present but not literal True
  * 2: missing required gate
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_TOOL = ROOT / "tools" / "policy_to_require_args.py"
POLICY_FILE = ROOT / "pulse_gate_policy_v0.yml"
CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # hermetic: avoid accidental env-driven paths influencing behavior
    env.pop("PULSE_STATUS", None)
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_rc(p: subprocess.CompletedProcess[str], expected: int) -> None:
    if p.returncode != expected:
        raise AssertionError(
            f"Unexpected return code: expected={expected} got={p.returncode}\n"
            f"CMD: {' '.join(p.args) if isinstance(p.args, list) else p.args}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def _materialize_required() -> list[str]:
    assert POLICY_TOOL.is_file(), f"Missing tool: {POLICY_TOOL}"
    assert POLICY_FILE.is_file(), f"Missing policy: {POLICY_FILE}"

    p = _run(
        [
            sys.executable,
            str(POLICY_TOOL),
            "--policy",
            str(POLICY_FILE),
            "--set",
            "required",
            "--format",
            "newline",
        ]
    )
    _assert_rc(p, 0)

    gates = [ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()]
    if not gates:
        raise AssertionError("Required gate list is empty (unexpected).")

    # sanity: avoid accidental duplicates in required list materialization
    if len(gates) != len(set(gates)):
        raise AssertionError(f"Duplicate gate ids in required list: {gates}")

    return gates


def _write_status(path: pathlib.Path, gates: dict) -> None:
    status = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": gates,
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_policy_to_check_gates_e2e_smoke() -> None:
    assert CHECK_GATES.is_file(), f"Missing tool: {CHECK_GATES}"

    required = _materialize_required()
    pivot = required[0]

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # Case 1: all required gates True => rc 0
        status_ok = td / "status_ok.json"
        _write_status(status_ok, {g: True for g in required})
        p = _run([sys.executable, str(CHECK_GATES), "--status", str(status_ok), "--require", *required])
        _assert_rc(p, 0)

        # Case 2: one required gate present but False => rc 1
        status_fail = td / "status_fail.json"
        gates = {g: True for g in required}
        gates[pivot] = False
        _write_status(status_fail, gates)
        p = _run([sys.executable, str(CHECK_GATES), "--status", str(status_fail), "--require", *required])
        _assert_rc(p, 1)

        # Case 3: one required gate missing => rc 2 (missing dominates)
        status_missing = td / "status_missing.json"
        gates = {g: True for g in required}
        gates.pop(pivot, None)
        _write_status(status_missing, gates)
        p = _run([sys.executable, str(CHECK_GATES), "--status", str(status_missing), "--require", *required])
        _assert_rc(p, 2)


def main() -> int:
    try:
        test_policy_to_check_gates_e2e_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: policy -> check_gates e2e smoke passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
