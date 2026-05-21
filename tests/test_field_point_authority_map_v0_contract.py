#!/usr/bin/env python3
"""Smoke tests for field_point_authority_map_v0 contract checker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_field_point_authority_map_v0_contract.py"

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "field_point_authority_map_v0"
PASS = FIXTURE_DIR / "pass.json"
INVALID_RECOGNITION = FIXTURE_DIR / "invalid_recognition_surface_authority.json"
INVALID_PUBLICATION = FIXTURE_DIR / "invalid_publication_surface_affects_release.json"


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
    result = _run(PASS)
    assert result.returncode == 0, result.stderr + result.stdout


def test_invalid_recognition_surface_authority_fails() -> None:
    result = _run(INVALID_RECOGNITION)
    assert result.returncode == 1
    assert "recognition surfaces must not declare normative authority" in (
        result.stderr + result.stdout
    )


def test_invalid_publication_surface_affects_release_fails() -> None:
    result = _run(INVALID_PUBLICATION)
    assert result.returncode == 1
    assert "publication surfaces must not affect release decisions directly" in (
        result.stderr + result.stdout
    )


def test_unknown_normative_path_member_fails() -> None:
    payload = _read(PASS)
    payload["normative_materialization_path"].append("missing-field-point")
    payload["result"] = "invalid"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "unknown field point" in (result.stderr + result.stdout)


def test_non_normative_field_point_cannot_affect_release_without_policy_route() -> None:
    payload = _read(PASS)

    for point in payload["field_points"]:
        if point["field_point_id"] == "hpc-evidence-bundle":
            point["can_affect_release_decision"] = True
            point["policy_route"] = None

    payload["result"] = "invalid"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "policy_route" in (result.stderr + result.stdout)


def test_policy_routed_diagnostic_candidate_can_affect_release_decision() -> None:
    payload = _read(PASS)

    for point in payload["field_points"]:
        if point["field_point_id"] == "hpc-evidence-bundle":
            point["can_affect_release_decision"] = True
            point["policy_route"] = {
                "policy_path": "pulse_gate_policy_v0.yml",
                "gate_id": "external_all_pass"
            }

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "good.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 0, result.stderr + result.stdout


def test_result_must_match_semantic_validity() -> None:
    payload = _read(PASS)
    payload["result"] = "invalid"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "result must be" in (result.stderr + result.stdout)


def main() -> int:
    try:
        test_pass_fixture_is_valid()
        test_invalid_recognition_surface_authority_fails()
        test_invalid_publication_surface_affects_release_fails()
        test_unknown_normative_path_member_fails()
        test_non_normative_field_point_cannot_affect_release_without_policy_route()
        test_policy_routed_diagnostic_candidate_can_affect_release_decision()
        test_result_must_match_semantic_validity()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: field_point_authority_map_v0 contract smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
