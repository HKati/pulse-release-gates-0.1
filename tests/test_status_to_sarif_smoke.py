#!/usr/bin/env python3
"""
Smoke test for PULSE_safe_pack_v0/tools/status_to_sarif.py.

Hermetic CLI usage: does not rely on env-driven defaults.
Runnable both as pytest module and standalone script.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "status_to_sarif.py"


def _run(
    status_path: pathlib.Path,
    out_path: pathlib.Path,
    require: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PULSE_STATUS", None)
    env.pop("PULSE_SARIF", None)
    cmd = [sys.executable, str(EXPORTER), "--status", str(status_path), "--out", str(out_path)]
    if require is not None:
        cmd.extend(["--require", *require])

    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )


def test_status_to_sarif_smoke() -> None:
    assert EXPORTER.is_file(), f"Exporter not found at {EXPORTER}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"
        out_path = td / "sarif.json"

        status = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"gate_a": True, "gate_b": False, "gate_c": True},
        }
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        r = _run(status_path, out_path)
        if r.returncode != 0:
            raise AssertionError(f"SARIF exporter failed: exit={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

        assert out_path.is_file(), "Expected SARIF output file to be created"
        sarif = json.loads(out_path.read_text(encoding="utf-8"))

        assert sarif.get("version") == "2.1.0"
        runs = sarif.get("runs") or []
        assert runs and isinstance(runs, list)

        results = runs[0].get("results") or []
        # Only gate_b fails
        rule_ids = [result.get("ruleId") for result in results]
        assert rule_ids == ["gate_b"], f"Unexpected SARIF results: {rule_ids}"


def test_status_to_sarif_require_filter() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"
        out_path = td / "sarif_required.json"

        status = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"gate_a": True, "gate_b": False, "gate_c": False},
        }
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        r = _run(status_path, out_path, require=["gate_c", "missing_gate"])
        if r.returncode != 0:
            raise AssertionError(f"SARIF exporter failed: exit={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

        assert "::warning::SARIF filter gate not present in status.json: missing_gate" in r.stdout

        sarif = json.loads(out_path.read_text(encoding="utf-8"))
        runs = sarif.get("runs") or []
        assert runs and isinstance(runs, list)

        rules = runs[0].get("tool", {}).get("driver", {}).get("rules") or []
        assert [rule.get("id") for rule in rules] == ["gate_c"]

        results = runs[0].get("results") or []
        assert [result.get("ruleId") for result in results] == ["gate_c"]


def test_status_to_sarif_require_empty_selects_no_gates() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"
        out_path = td / "sarif_required_empty.json"

        status = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"gate_a": True, "gate_b": False, "gate_c": False},
        }
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        r = _run(status_path, out_path, require=[])
        if r.returncode != 0:
            raise AssertionError(f"SARIF exporter failed: exit={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

        sarif = json.loads(out_path.read_text(encoding="utf-8"))
        runs = sarif.get("runs") or []
        assert runs and isinstance(runs, list)

        rules = runs[0].get("tool", {}).get("driver", {}).get("rules") or []
        assert rules == []

        results = runs[0].get("results") or []
        assert results == []


def main() -> int:
    try:
        test_status_to_sarif_smoke()
        test_status_to_sarif_require_filter()
        test_status_to_sarif_require_empty_selects_no_gates()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: status_to_sarif smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
