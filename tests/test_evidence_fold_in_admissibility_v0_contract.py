#!/usr/bin/env python3
"""Smoke tests for evidence_fold_in_admissibility_v0 contract checker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_evidence_fold_in_admissibility_v0_contract.py"

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "evidence_fold_in_admissibility_v0"
ADMISSIBLE = FIXTURE_DIR / "admissible.json"
ADVISORY_ONLY = FIXTURE_DIR / "advisory_only.json"
REJECTED_RECOGNITION = FIXTURE_DIR / "rejected_recognition_surface.json"


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


def test_admissible_fixture_is_valid() -> None:
    result = _run(ADMISSIBLE)
    assert result.returncode == 0, result.stderr + result.stdout


def test_advisory_only_fixture_is_valid() -> None:
    result = _run(ADVISORY_ONLY)
    assert result.returncode == 0, result.stderr + result.stdout


def test_rejected_recognition_surface_fixture_is_valid() -> None:
    result = _run(REJECTED_RECOGNITION)
    assert result.returncode == 0, result.stderr + result.stdout


def test_admissible_candidate_requires_policy_route() -> None:
    payload = _read(ADMISSIBLE)
    payload["candidates"][0]["policy_route"] = None

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "policy_route" in (result.stderr + result.stdout)


def test_admissible_candidate_requires_verified_status() -> None:
    payload = _read(ADMISSIBLE)
    payload["candidates"][0]["verification_status"] = "unverified"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "verification_status=verified" in (result.stderr + result.stdout)


def test_advisory_only_candidate_must_not_request_fold_in() -> None:
    payload = _read(ADVISORY_ONLY)
    payload["candidates"][0]["folded_into_status_requested"] = True

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "advisory-only evidence must not request status fold-in" in (
        result.stderr + result.stdout
    )


def test_recognition_surface_cannot_be_admissible_for_fold_in() -> None:
    payload = _read(REJECTED_RECOGNITION)
    payload["candidates"][0]["admissibility"] = "admissible_for_fold_in"
    payload["candidates"][0]["result"] = "admissible"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "recognition surfaces are not admissible" in (
        result.stderr + result.stdout
    )


def test_result_must_match_candidate_admissibility_mix() -> None:
    payload = _read(ADMISSIBLE)
    payload["result"] = "advisory_only"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "result must be" in (result.stderr + result.stdout)


def test_admissible_candidate_requires_real_source_artifact_path() -> None:
    payload = _read(ADMISSIBLE)
    payload["candidates"][0]["source_artifact"]["path"] = "_missing_source_artifact_path"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "source_artifact.path" in (result.stderr + result.stdout)


def main() -> int:
    try:
        test_admissible_fixture_is_valid()
        test_advisory_only_fixture_is_valid()
        test_rejected_recognition_surface_fixture_is_valid()
        test_admissible_candidate_requires_policy_route()
        test_admissible_candidate_requires_verified_status()
        test_advisory_only_candidate_must_not_request_fold_in()
        test_recognition_surface_cannot_be_admissible_for_fold_in()
        test_admissible_candidate_requires_real_source_artifact_path()
        test_result_must_match_candidate_admissibility_mix()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: evidence_fold_in_admissibility_v0 contract smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
