#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "status_to_summary.py"


def run(status_path: pathlib.Path) -> dict:
    env = os.environ.copy()
    # hermetikus: ne az env döntsön a státuszról
    env.pop("PULSE_STATUS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)

    p = subprocess.run(
        [sys.executable, str(TOOL), "--status", str(status_path), "--gate-flags-json"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise AssertionError(
            f"status_to_summary failed: exit={p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return json.loads(p.stdout)


def test_status_to_summary_gate_flags() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"

        # v1-min: gates + metrics + created_utc
        status = {
            "version": "1.0.0-test",
            "created_utc": "2026-02-18T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {
                "gate_00_false": False,
                "gate_01_str": "true",
                "gate_02_true": True,
            },
        }
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        payload = run(status_path)
        rows = payload.get("gate_flags")
        assert isinstance(rows, list) and rows, "Expected non-empty gate_flags"

        ids = [r.get("gate_id") for r in rows]
        assert ids == sorted(ids), f"Expected sorted gate ids, got: {ids}"

        by_id = {r["gate_id"]: r for r in rows}
        assert by_id["gate_02_true"]["flag"] == "PASS"
        assert by_id["gate_00_false"]["flag"] == "FAIL"
        assert by_id["gate_01_str"]["flag"] == "FAIL"


def main() -> int:
    try:
        test_status_to_summary_gate_flags()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: status_to_summary gate flags smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
