from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "ci" / "check_release_no_stub_status.py"


def run_guard(payload: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        status = Path(tmpdir) / "status.json"
        status.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(TOOL), "--status", str(status)],
            text=True,
            capture_output=True,
        )


def test_fails_on_missing_diagnostics() -> None:
    result = run_guard({"gates": {"detectors_materialized_ok": True}})
    assert result.returncode != 0


def test_fails_on_non_object_diagnostics() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": None,
        }
    )
    assert result.returncode != 0


def test_fails_on_unmaterialized_detectors() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": False},
            "diagnostics": {"gates_stubbed": False, "scaffold": False},
        }
    )
    assert result.returncode != 0


def test_fails_on_missing_gates_stubbed() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": {"scaffold": False},
        }
    )
    assert result.returncode != 0


def test_fails_on_non_boolean_gates_stubbed() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": {"gates_stubbed": "false", "scaffold": False},
        }
    )
    assert result.returncode != 0


def test_fails_on_stubbed_true() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": {"gates_stubbed": True, "scaffold": False},
        }
    )
    assert result.returncode != 0


def test_fails_on_scaffold_true() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": {"gates_stubbed": False, "scaffold": True},
        }
    )
    assert result.returncode != 0


def test_passes_on_materialized_explicit_non_stub_status() -> None:
    result = run_guard(
        {
            "gates": {"detectors_materialized_ok": True},
            "diagnostics": {"gates_stubbed": False, "scaffold": False},
        }
    )
    assert result.returncode == 0, result.stderr
