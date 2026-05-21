#!/usr/bin/env python3
"""Smoke tests for build_field_point_authority_map_v0.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_field_point_authority_map_v0.py"
CHECKER = ROOT / "scripts" / "check_field_point_authority_map_v0_contract.py"

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "field_point_authority_map_v0"
PASS_INPUT = FIXTURE_DIR / "builder_pass_input.json"
INVALID_INPUT = FIXTURE_DIR / "builder_invalid_input.json"


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


def test_builder_outputs_valid_authority_map() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "field_point_authority_map_v0.json"

        result = _run_builder(PASS_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "field_point_authority_map_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["creates_release_authority"] is False
        assert artifact["result"] == "valid"

        by_id = {
            point["field_point_id"]: point
            for point in artifact["field_points"]
        }

        assert by_id["status-json"]["authority_status"] == "normative_input"
        assert by_id["strict-ci-checking"]["authority_status"] == "normative_enforcement"
        assert by_id["ci-allow-block-decision"]["authority_status"] == "normative_decision"
        assert by_id["readme"]["authority_status"] == "recognition_non_normative"
        assert by_id["quality-ledger"]["authority_status"] == "publication_non_normative"
        assert by_id["hpc-evidence-bundle"]["authority_status"] == "diagnostic_non_normative"


def test_builder_outputs_invalid_authority_map_for_bad_surface_roles() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "field_point_authority_map_v0.json"

        result = _run_builder(INVALID_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        artifact = _read(out_path)
        assert artifact["schema"] == "field_point_authority_map_v0"
        assert artifact["result"] == "invalid"

        check = _run_checker(out_path)

    assert check.returncode == 1
    assert "publication surfaces must not affect release decisions directly" in (
        check.stderr + check.stdout
    )
    assert "recognition surfaces must not affect release decisions directly" in (
        check.stderr + check.stdout
    )


def test_builder_rejects_empty_field_points() -> None:
    payload = _read(PASS_INPUT)
    payload["field_points"] = []

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "bad_input.json"
        out_path = Path(td) / "field_point_authority_map_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)

    assert result.returncode == 1
    assert "field_points" in (result.stderr + result.stdout)


def test_builder_rejects_unknown_normative_path_later_by_checker() -> None:
    payload = _read(PASS_INPUT)
    payload["normative_materialization_path"].append("missing-field-point")

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "field_point_authority_map_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        artifact = _read(out_path)
        assert artifact["result"] == "invalid"

        check = _run_checker(out_path)

    assert check.returncode == 1
    assert "unknown field point" in (check.stderr + check.stdout)


def test_policy_routed_diagnostic_candidate_can_affect_release_decision() -> None:
    payload = _read(PASS_INPUT)

    for point in payload["field_points"]:
        if point["field_point_id"] == "hpc-evidence-bundle":
            point["can_affect_release_decision"] = True
            point["policy_route"] = {
                "policy_path": "pulse_gate_policy_v0.yml",
                "gate_id": "external_all_pass"
            }

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "field_point_authority_map_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)

    assert check.returncode == 0, check.stderr + check.stdout


def test_builder_rejects_short_normative_materialization_path() -> None:
    payload = _read(PASS_INPUT)
    payload["normative_materialization_path"] = [
        "recorded-release-evidence",
        "status-json",
        "declared-gate-policy",
        "strict-ci-checking",
    ]

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "bad_input.json"
        out_path = Path(td) / "field_point_authority_map_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)

    assert result.returncode == 1
    assert "normative_materialization_path" in (result.stderr + result.stdout)
    assert "at least 5" in (result.stderr + result.stdout)


def main() -> int:
    try:
        test_builder_outputs_valid_authority_map()
        test_builder_outputs_invalid_authority_map_for_bad_surface_roles()
        test_builder_rejects_empty_field_points()
        test_builder_rejects_short_normative_materialization_path()
        test_builder_rejects_unknown_normative_path_later_by_checker()
        test_policy_routed_diagnostic_candidate_can_affect_release_decision()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: build_field_point_authority_map_v0 smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
