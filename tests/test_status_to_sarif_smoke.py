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


def _run(status_path: pathlib.Path, out_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PULSE_STATUS", None)
    env.pop("PULSE_SARIF", None)
    return subprocess.run(
        [sys.executable, str(EXPORTER), "--status", str(status_path), "--out", str(out_path)],
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
        rule_ids = [r.get("ruleId") for r in results]
        assert rule_ids == ["gate_b"], f"Unexpected SARIF results: {rule_ids}"


def main() -> int:
    try:
        test_status_to_sarif_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: status_to_sarif smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
