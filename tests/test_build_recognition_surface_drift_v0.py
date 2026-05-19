#!/usr/bin/env python3
"""Smoke tests for build_recognition_surface_drift_v0.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_recognition_surface_drift_v0.py"
CHECKER = ROOT / "scripts" / "check_recognition_surface_drift_v0_contract.py"

STABLE_INPUT = (
    ROOT
    / "tests"
    / "fixtures"
    / "recognition_surface_drift_v0"
    / "builder_stable_input.json"
)
CONTAMINATED_INPUT = (
    ROOT
    / "tests"
    / "fixtures"
    / "recognition_surface_drift_v0"
    / "builder_contaminated_input.json"
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_builder(input_path: Path, out_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--input",
            str(input_path),
            "--out",
            str(out_path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_checker(out_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--in",
            str(out_path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def test_builder_outputs_stable_valid_artifact() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "recognition_surface_drift_v0.json"

        result = _run_builder(STABLE_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "recognition_surface_drift_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["result"] == "stable"
        assert artifact["drift"]["drift_score"] == 0
        assert artifact["drift"]["identity_classification_changed"] is False
        assert artifact["drift"]["authority_boundary_changed"] is False
        assert artifact["drift"]["normative_path_changed"] is False
        assert artifact["drift"]["mechanical_claims_changed"] is False


def test_builder_outputs_contaminated_valid_artifact() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "recognition_surface_drift_v0.json"

        result = _run_builder(CONTAMINATED_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "recognition_surface_drift_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["result"] == "contaminated"
        assert artifact["drift"]["drift_score"] >= 0.5
        assert artifact["drift"]["identity_classification_changed"] is True
        assert artifact["drift"]["authority_boundary_changed"] is True
        assert artifact["drift"]["normative_path_changed"] is True
        assert artifact["drift"]["mechanical_claims_changed"] is True


def test_builder_rejects_input_without_mechanism_first_baseline() -> None:
    payload = _read(STABLE_INPUT)
    for run in payload["analysis_runs"]:
        run["condition"] = "recognition_surface_variant"

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "bad_input.json"
        out_path = Path(td) / "recognition_surface_drift_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)

    assert result.returncode == 1
    assert "mechanism_first" in (result.stderr + result.stdout)


def test_smoke() -> None:
    test_builder_outputs_stable_valid_artifact()
    test_builder_outputs_contaminated_valid_artifact()
    test_builder_rejects_input_without_mechanism_first_baseline()


def main() -> int:
    try:
        test_smoke()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: build_recognition_surface_drift_v0 smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
