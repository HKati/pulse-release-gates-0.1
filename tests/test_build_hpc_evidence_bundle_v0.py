#!/usr/bin/env python3
"""Smoke tests for build_hpc_evidence_bundle_v0.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_hpc_evidence_bundle_v0.py"
CHECKER = ROOT / "scripts" / "check_hpc_evidence_bundle_v0_contract.py"

COMPLETE_INPUT = (
    ROOT
    / "tests"
    / "fixtures"
    / "hpc_evidence_bundle_v0"
    / "builder_complete_input.json"
)
INCOMPLETE_INPUT = (
    ROOT
    / "tests"
    / "fixtures"
    / "hpc_evidence_bundle_v0"
    / "builder_incomplete_input.json"
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


def test_builder_outputs_complete_valid_bundle() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "hpc_evidence_bundle_v0.json"

        result = _run_builder(COMPLETE_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "hpc_evidence_bundle_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["creates_release_authority"] is False
        assert artifact["result"] == "complete"
        assert all(
            item["evidence_status"] == "present"
            for item in artifact["evidence_items"]
        )


def test_builder_outputs_incomplete_valid_bundle() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "hpc_evidence_bundle_v0.json"

        result = _run_builder(INCOMPLETE_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "hpc_evidence_bundle_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["creates_release_authority"] is False
        assert artifact["result"] == "incomplete"
        assert any(
            item["evidence_status"] != "present"
            for item in artifact["evidence_items"]
        )


def test_builder_rejects_input_without_evidence_items() -> None:
    payload = _read(COMPLETE_INPUT)
    payload["evidence_items"] = []

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "bad_input.json"
        out_path = Path(td) / "hpc_evidence_bundle_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)

    assert result.returncode == 1
    assert "evidence_items" in (result.stderr + result.stdout)


def test_builder_output_with_folded_evidence_without_policy_route_fails_checker() -> None:
    payload = _read(COMPLETE_INPUT)
    payload["evidence_items"][0]["folded_into_status"] = True
    payload["evidence_items"][0].pop("policy_route", None)

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "hpc_evidence_bundle_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)

    assert check.returncode == 1
    assert "lacks policy_route" in (check.stderr + check.stdout)


def test_builder_output_with_folded_evidence_and_policy_route_passes_checker() -> None:
    payload = _read(COMPLETE_INPUT)
    payload["evidence_items"][0]["folded_into_status"] = True
    payload["evidence_items"][0]["policy_route"] = {
        "policy_path": "pulse_gate_policy_v0.yml",
        "gate_id": "external_all_pass"
    }

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "hpc_evidence_bundle_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)

    assert check.returncode == 0, check.stderr + check.stdout


def main() -> int:
    try:
        test_builder_outputs_complete_valid_bundle()
        test_builder_outputs_incomplete_valid_bundle()
        test_builder_rejects_input_without_evidence_items()
        test_builder_output_with_folded_evidence_without_policy_route_fails_checker()
        test_builder_output_with_folded_evidence_and_policy_route_passes_checker()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: build_hpc_evidence_bundle_v0 smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
