#!/usr/bin/env python3
"""Smoke tests for hpc_evidence_bundle_v0 contract checker."""

from __future__ import annotations

import hashlib
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
KAGGLE_HPC_MINIMAL_DIAGNOSTIC_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "hpc_evidence_bundle_v0"
    / "kaggle_hpc_minimal_diagnostic.json"
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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def _walk_mapping_keys(value: Any) -> list[str]:
    keys: list[str] = []

    if isinstance(value, dict):
        for key, nested_value in value.items():
            keys.append(str(key))
            keys.extend(_walk_mapping_keys(nested_value))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_mapping_keys(item))

    return keys


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


def test_kaggle_hpc_minimal_diagnostic_fixture_contract_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--in",
            str(KAGGLE_HPC_MINIMAL_DIAGNOSTIC_FIXTURE),
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_kaggle_hpc_minimal_diagnostic_fixture_is_non_authoritative() -> None:
    bundle = _read(KAGGLE_HPC_MINIMAL_DIAGNOSTIC_FIXTURE)

    assert bundle["schema"] == "hpc_evidence_bundle_v0"
    assert bundle["authority_status"] == "diagnostic_non_normative"
    assert bundle["creates_release_authority"] is False

    evidence_items = bundle["evidence_items"]

    assert evidence_items

    for item in evidence_items:
        assert item["folded_into_status"] is False
        assert "policy_route" not in item


def test_kaggle_hpc_minimal_diagnostic_fixture_uses_real_digests() -> None:
    bundle = _read(KAGGLE_HPC_MINIMAL_DIAGNOSTIC_FIXTURE)

    input_manifest_path = ROOT / bundle["input_manifest"]["path"]

    assert input_manifest_path.exists()
    assert _sha256_file(input_manifest_path) == bundle["input_manifest"]["sha256"]

    for item in bundle["evidence_items"]:
        if item["evidence_status"] != "present":
            continue

        artifact_path = ROOT / item["path"]

        assert artifact_path.exists()
        assert _sha256_file(artifact_path) == item["sha256"]


def test_kaggle_hpc_minimal_diagnostic_fixture_has_no_authority_surfaces() -> None:
    bundle = _read(KAGGLE_HPC_MINIMAL_DIAGNOSTIC_FIXTURE)

    forbidden_keys = {
        "verified_artifacts",
        "relation_bindings",
        "status",
        "status_json",
        "release_authority",
        "release_authority_v0",
        "gate_materialization",
        "policy_route",
    }

    keys = set(_walk_mapping_keys(bundle))

    assert not (keys & forbidden_keys)


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
