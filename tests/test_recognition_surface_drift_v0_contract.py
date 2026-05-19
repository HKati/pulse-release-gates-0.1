#!/usr/bin/env python3
"""Smoke tests for recognition_surface_drift_v0 contract checker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_recognition_surface_drift_v0_contract.py"
PASS_FIXTURE = ROOT / "tests" / "fixtures" / "recognition_surface_drift_v0" / "pass.json"
CONTAMINATED_FIXTURE = (
    ROOT / "tests" / "fixtures" / "recognition_surface_drift_v0" / "contaminated.json"
)


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--in", str(path)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_pass_fixture_is_valid() -> None:
    result = _run(PASS_FIXTURE)
    assert result.returncode == 0, result.stderr + result.stdout


def test_contaminated_fixture_is_valid_diagnostic_artifact() -> None:
    result = _run(CONTAMINATED_FIXTURE)
    assert result.returncode == 0, result.stderr + result.stdout


def test_stable_result_rejects_changed_drift_dimensions() -> None:
    payload = _read(PASS_FIXTURE)
    payload["drift"]["identity_classification_changed"] = True

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "stable result must not report changed drift dimensions" in (
        result.stderr + result.stdout
    )


def test_contaminated_result_requires_changed_drift_dimension() -> None:
    payload = _read(CONTAMINATED_FIXTURE)
    payload["drift"]["identity_classification_changed"] = False
    payload["drift"]["authority_boundary_changed"] = False
    payload["drift"]["normative_path_changed"] = False
    payload["drift"]["mechanical_claims_changed"] = False

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "contaminated result must report at least one changed drift dimension" in (
        result.stderr + result.stdout
    )


def test_smoke() -> None:
    test_pass_fixture_is_valid()
    test_contaminated_fixture_is_valid_diagnostic_artifact()
    test_stable_result_rejects_changed_drift_dimensions()
    test_contaminated_result_requires_changed_drift_dimension()


def main() -> int:
    try:
        test_smoke()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: recognition_surface_drift_v0 contract smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
