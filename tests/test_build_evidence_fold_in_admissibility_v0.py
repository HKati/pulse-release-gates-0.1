#!/usr/bin/env python3
"""Smoke tests for build_evidence_fold_in_admissibility_v0.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_evidence_fold_in_admissibility_v0.py"
CHECKER = ROOT / "scripts" / "check_evidence_fold_in_admissibility_v0_contract.py"

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "evidence_fold_in_admissibility_v0"
ADMISSIBLE_INPUT = FIXTURE_DIR / "builder_admissible_input.json"
MIXED_INPUT = FIXTURE_DIR / "builder_mixed_input.json"


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


def test_builder_outputs_admissible_valid_artifact() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"

        result = _run_builder(ADMISSIBLE_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "evidence_fold_in_admissibility_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["creates_release_authority"] is False
        assert artifact["result"] == "admissible"

        candidate = artifact["candidates"][0]
        assert candidate["admissibility"] == "admissible_for_fold_in"
        assert candidate["folded_into_status_requested"] is True
        assert candidate["policy_route"]["gate_id"] == "external_all_pass"


def test_builder_outputs_mixed_valid_artifact() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"

        result = _run_builder(MIXED_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)
        assert artifact["schema"] == "evidence_fold_in_admissibility_v0"
        assert artifact["authority_status"] == "diagnostic_non_normative"
        assert artifact["creates_release_authority"] is False
        assert artifact["result"] == "mixed"

        admissibilities = {
            candidate["candidate_id"]: candidate["admissibility"]
            for candidate in artifact["candidates"]
        }

        assert admissibilities["hpc-detector-summary"] == "admissible_for_fold_in"
        assert admissibilities["pulse-pd-summary"] == "advisory_only"
        assert admissibilities["readme-title"] == "rejected"


def test_builder_rejects_input_without_candidates() -> None:
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "bad_input.json"
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"

        _write(input_path, {"candidates": []})

        result = _run_builder(input_path, out_path)

    assert result.returncode == 1
    assert "candidates" in (result.stderr + result.stdout)


def test_builder_rejects_fold_in_request_without_policy_route() -> None:
    payload = _read(ADMISSIBLE_INPUT)
    payload["candidates"][0]["policy_route"] = None

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)

    assert artifact["result"] == "rejected"
    assert artifact["candidates"][0]["admissibility"] == "rejected"
    assert artifact["candidates"][0]["folded_into_status_requested"] is False
    assert "policy_route" in artifact["candidates"][0]["reason"]


def test_recognition_surface_fold_in_request_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"

        result = _run_builder(MIXED_INPUT, out_path)
        assert result.returncode == 0, result.stderr + result.stdout

        artifact = _read(out_path)
        recognition = next(
            candidate
            for candidate in artifact["candidates"]
            if candidate["candidate_id"] == "readme-title"
        )

    assert recognition["admissibility"] == "rejected"
    assert recognition["folded_into_status_requested"] is False
    assert "Recognition surfaces are not admissible" in recognition["reason"]

def test_builder_rejects_fold_in_request_without_source_artifact_path() -> None:
    payload = _read(ADMISSIBLE_INPUT)
    payload["candidates"][0]["source_artifact"].pop("path", None)

    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"
        out_path = Path(td) / "evidence_fold_in_admissibility_v0.json"
        _write(input_path, payload)

        result = _run_builder(input_path, out_path)
        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        check = _run_checker(out_path)
        assert check.returncode == 0, check.stderr + check.stdout

        artifact = _read(out_path)

    candidate = artifact["candidates"][0]
    assert artifact["result"] == "rejected"
    assert candidate["admissibility"] == "rejected"
    assert candidate["folded_into_status_requested"] is False
    assert candidate["source_artifact"]["path"] == "_missing_source_artifact_path"
    assert "source_artifact.path" in candidate["reason"]


def main() -> int:
    try:
        test_builder_outputs_admissible_valid_artifact()
        test_builder_outputs_mixed_valid_artifact()
        test_builder_rejects_input_without_candidates()
        test_builder_rejects_fold_in_request_without_source_artifact_path()
        test_builder_rejects_fold_in_request_without_policy_route()
        test_recognition_surface_fold_in_request_is_rejected()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: build_evidence_fold_in_admissibility_v0 smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
