#!/usr/bin/env python3
"""Regression tests for the release-grade status contract schema."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "validate_status_schema.py"
SCHEMA = REPO_ROOT / "schemas" / "status" / "release_grade_status_v1.schema.json"


def _run(status_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--schema",
            str(SCHEMA),
            "--status",
            str(status_path),
            "--max-errors",
            "20",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def _write(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _valid_release_grade_status() -> dict[str, Any]:
    return {
        "version": "1.0.0-prod",
        "created_utc": "2026-05-18T00:00:00Z",
        "metrics": {
            "run_mode": "prod"
        },
        "gates": {
            "detectors_materialized_ok": True,
            "external_summaries_present": True,
            "external_all_pass": True,
            "refusal_delta_evidence_present": True,
            "q1_grounded_ok": True
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
            "stub_profile": "none"
        },
        "external": {
            "all_pass": True,
            "summaries_present": True,
            "summary_count": 1,
            "canonical_summary_count": 1,
            "unrecognized_summary_count": 0,
            "metrics": [
                {
                    "name": "llamaguard_violation_rate",
                    "value": 0.02,
                    "threshold": 0.10,
                    "pass": True
                }
            ]
        }
    }


def _assert_exit(payload: dict[str, Any], expected: int) -> str:
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "status.json"
        _write(path, payload)
        result = _run(path)

    out = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode != expected:
        raise AssertionError(
            f"expected exit {expected}, got {result.returncode}\n{out}"
        )

    return out


def test_release_grade_status_contract_accepts_explicit_prod_non_stub_status() -> None:
    _assert_exit(_valid_release_grade_status(), 0)


def test_release_grade_status_contract_rejects_core_run_mode() -> None:
    payload = _valid_release_grade_status()
    payload["metrics"]["run_mode"] = "core"

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "run_mode" in out


def test_release_grade_status_contract_rejects_missing_diagnostics() -> None:
    payload = _valid_release_grade_status()
    payload.pop("diagnostics")

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "diagnostics" in out


def test_release_grade_status_contract_rejects_non_object_diagnostics() -> None:
    payload = _valid_release_grade_status()
    payload["diagnostics"] = None

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "diagnostics" in out


def test_release_grade_status_contract_rejects_stubbed_diagnostics() -> None:
    payload = _valid_release_grade_status()
    payload["diagnostics"]["gates_stubbed"] = True

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "gates_stubbed" in out


def test_release_grade_status_contract_rejects_non_boolean_stubbed_diagnostics() -> None:
    payload = _valid_release_grade_status()
    payload["diagnostics"]["gates_stubbed"] = "false"

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "gates_stubbed" in out


def test_release_grade_status_contract_rejects_scaffold_diagnostics() -> None:
    payload = _valid_release_grade_status()
    payload["diagnostics"]["scaffold"] = True

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "scaffold" in out


def test_release_grade_status_contract_rejects_missing_detector_materialization() -> None:
    payload = _valid_release_grade_status()
    payload["gates"].pop("detectors_materialized_ok")

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "detectors_materialized_ok" in out


def test_release_grade_status_contract_rejects_false_detector_materialization() -> None:
    payload = _valid_release_grade_status()
    payload["gates"]["detectors_materialized_ok"] = False

    out = _assert_exit(payload, 1)

    assert "::error::" in out
    assert "detectors_materialized_ok" in out


def main() -> int:
    try:
        test_release_grade_status_contract_accepts_explicit_prod_non_stub_status()
        test_release_grade_status_contract_rejects_core_run_mode()
        test_release_grade_status_contract_rejects_missing_diagnostics()
        test_release_grade_status_contract_rejects_non_object_diagnostics()
        test_release_grade_status_contract_rejects_stubbed_diagnostics()
        test_release_grade_status_contract_rejects_non_boolean_stubbed_diagnostics()
        test_release_grade_status_contract_rejects_scaffold_diagnostics()
        test_release_grade_status_contract_rejects_missing_detector_materialization()
        test_release_grade_status_contract_rejects_false_detector_materialization()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: release-grade status contract schema tests passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
