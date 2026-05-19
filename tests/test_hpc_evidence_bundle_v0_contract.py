#!/usr/bin/env python3
"""Smoke tests for hpc_evidence_bundle_v0 contract checker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_hpc_evidence_bundle_v0_contract.py"
COMPLETE_FIXTURE = ROOT / "tests" / "fixtures" / "hpc_evidence_bundle_v0" / "complete.json"
INCOMPLETE_FIXTURE = ROOT / "tests" / "fixtures" / "hpc_evidence_bundle_v0" / "incomplete.json"


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


def test_complete_fixture_is_valid() -> None:
    result = _run(COMPLETE_FIXTURE)
    assert result.returncode == 0, result.stderr + result.stdout


def test_incomplete_fixture_is_valid_diagnostic_artifact() -> None:
    result = _run(INCOMPLETE_FIXTURE)
    assert result.returncode == 0, result.stderr + result.stdout


def test_complete_bundle_rejects_missing_evidence_item() -> None:
    payload = _read(COMPLETE_FIXTURE)
    payload["result"] = "complete"
    payload["evidence_items"][0]["evidence_status"] = "missing"
    payload["evidence_items"][0]["sha256"] = None

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "complete bundle cannot contain non-present evidence item" in (
        result.stderr + result.stdout
    )


def test_present_evidence_requires_valid_sha256() -> None:
    payload = _read(COMPLETE_FIXTURE)
    payload["evidence_items"][0]["sha256"] = "not-a-sha"

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "sha256" in (result.stderr + result.stdout)


def test_folded_evidence_requires_policy_route() -> None:
    payload = _read(COMPLETE_FIXTURE)
    payload["evidence_items"][0]["folded_into_status"] = True
    payload["evidence_items"][0].pop("policy_route", None)

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "lacks policy_route" in (result.stderr + result.stdout)


def test_folded_evidence_with_policy_route_is_valid() -> None:
    payload = _read(COMPLETE_FIXTURE)
    payload["evidence_items"][0]["folded_into_status"] = True
    payload["evidence_items"][0]["policy_route"] = {
        "policy_path": "pulse_gate_policy_v0.yml",
        "gate_id": "external_all_pass"
    }

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "good.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 0, result.stderr + result.stdout


def test_creates_release_authority_true_is_rejected() -> None:
    payload = _read(COMPLETE_FIXTURE)
    payload["creates_release_authority"] = True

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bad.json"
        _write(path, payload)
        result = _run(path)

    assert result.returncode == 1
    assert "creates_release_authority" in (result.stderr + result.stdout)


def main() -> int:
    try:
        test_complete_fixture_is_valid()
        test_incomplete_fixture_is_valid_diagnostic_artifact()
        test_complete_bundle_rejects_missing_evidence_item()
        test_present_evidence_requires_valid_sha256()
        test_folded_evidence_requires_policy_route()
        test_folded_evidence_with_policy_route_is_valid()
        test_creates_release_authority_true_is_rejected()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: hpc_evidence_bundle_v0 contract smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
