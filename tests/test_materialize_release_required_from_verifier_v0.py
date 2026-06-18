#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.materialize_release_required_from_verifier_v0 import (
    materialize_release_required_from_verifier,
)

TOOL = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "materialize_release_required_from_verifier_v0.py"
)

COMMIT_SHA = "a" * 40
RUN_KEY = "run-prod-2026-01-01"
RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]

POLICY_TEXT = """policy:
  id: pulse-gate-policy-v0
  version: "0.1.5"
  enforcement:
    required_missing: FAIL
    required_false: FAIL
    advisory_missing: WARN
    advisory_false: WARN
    unknown_gate_in_status: WARN
    external_detectors_default: ADVISORY

gates:
  required:
    - q1_grounded_ok
  core_required:
    - q1_grounded_ok
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
    - refusal_delta_evidence_present
  advisory:
    - external_summaries_present
"""

REGISTRY_TEXT = """version: gate_registry_v0
gates:
  q1_grounded_ok:
    category: quality
  detectors_materialized_ok:
    category: controls
  external_summaries_present:
    category: external
  external_all_pass:
    category: external
  refusal_delta_evidence_present:
    category: controls
"""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_text(path: pathlib.Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _status_payload(policy_path: pathlib.Path, policy_sha: str) -> dict[str, Any]:
    return {
        "version": "1.0.0-prod",
        "created_utc": "2026-01-01T00:00:00Z",
        "metrics": {
            "run_mode": "prod",
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "gate_policy_path": str(policy_path.resolve()),
            "gate_policy_sha256": policy_sha,
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
        },
        "gates": {
            "q1_grounded_ok": True,
        },
    }


def _verifier_payload(policy_sha: str, registry_sha: str) -> dict[str, Any]:
    return {
        "schema_version": "recorded_release_evidence_verifier_v0",
        "report_version": "0.2.0",
        "status": "verified",
        "errors": [],
        "run_identity": {
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "verified_subjects": {
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "commit_sha": COMMIT_SHA,
        },
        "policy_binding": {
            "policy_set": "required+release_required",
            "policy_sha256": policy_sha,
        },
        "registry_binding": {
            "registry_sha256": registry_sha,
        },
        "gate_materialization_admissibility": {
            gate_id: {
                "status": "verified",
                "admissible": True,
                "errors": [],
            }
            for gate_id in RELEASE_REQUIRED_GATES
        },
    }


def _build_fixture(
    tmp_path: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    registry_path = tmp_path / "pulse_gate_registry_v0.yml"
    policy_sha = _write_text(policy_path, POLICY_TEXT)
    registry_sha = _write_text(registry_path, REGISTRY_TEXT)

    status_path = tmp_path / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
    verifier_path = (
        tmp_path
        / "PULSE_safe_pack_v0"
        / "artifacts"
        / "recorded_release_evidence_verifier_v0.json"
    )

    _write_json(status_path, _status_payload(policy_path, policy_sha))
    _write_json(verifier_path, _verifier_payload(policy_sha, registry_sha))
    return status_path, verifier_path, policy_path, registry_path


def test_materializes_release_required_gates_from_verified_report(
    tmp_path: pathlib.Path,
) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    status, materialized_gates, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert errors == []
    assert materialized_gates == RELEASE_REQUIRED_GATES
    assert status is not None
    assert status["gates"]["q1_grounded_ok"] is True
    for gate_id in RELEASE_REQUIRED_GATES:
        assert status["gates"][gate_id] is True


def test_cli_writes_materialized_status(tmp_path: pathlib.Path) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)
    out_path = tmp_path / "PULSE_safe_pack_v0" / "artifacts" / "status.materialized.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--status",
            str(status_path),
            "--verifier-report",
            str(verifier_path),
            "--policy",
            str(policy_path),
            "--registry",
            str(registry_path),
            "--out",
            str(out_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    written = _read_json(out_path)
    for gate_id in RELEASE_REQUIRED_GATES:
        assert written["gates"][gate_id] is True


def test_rejects_status_report_identity_mismatch(tmp_path: pathlib.Path) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    status = _read_json(status_path)
    status["metrics"]["git_sha"] = "b" * 40
    _write_json(status_path, status)

    materialized, _, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert materialized is None
    assert any(
        "status.metrics.git_sha must match verifier_report.run_identity.git_sha" in error
        for error in errors
    )


def test_rejects_status_policy_metadata_mismatch(tmp_path: pathlib.Path) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    status = _read_json(status_path)
    status["metrics"]["gate_policy_sha256"] = "d" * 64
    _write_json(status_path, status)

    materialized, _, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert materialized is None
    assert any(
        "status.metrics.gate_policy_sha256 does not match the current policy file" in error
        for error in errors
    )


def test_rejects_verified_report_with_top_level_errors(tmp_path: pathlib.Path) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    verifier = _read_json(verifier_path)
    verifier["errors"] = ["unexpected-top-level-error"]
    _write_json(verifier_path, verifier)

    materialized, _, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert materialized is None
    assert any(
        "verifier_report.errors must be absent or empty before materialization" in error
        for error in errors
    )


@pytest.mark.parametrize("field_name", ["gates_stubbed", "scaffold"])
def test_rejects_stubbed_or_scaffold_status(
    tmp_path: pathlib.Path,
    field_name: str,
) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    status = _read_json(status_path)
    status["diagnostics"][field_name] = True
    _write_json(status_path, status)

    materialized, _, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert materialized is None
    assert any(
        f"status.diagnostics.{field_name} must not be true" in error
        for error in errors
    )


def test_fails_when_policy_required_gate_is_missing_from_admissibility(
    tmp_path: pathlib.Path,
) -> None:
    status_path, verifier_path, policy_path, registry_path = _build_fixture(tmp_path)

    verifier = _read_json(verifier_path)
    del verifier["gate_materialization_admissibility"]["external_all_pass"]
    _write_json(verifier_path, verifier)

    materialized, _, errors = materialize_release_required_from_verifier(
        status_path=status_path,
        verifier_report_path=verifier_path,
        policy_path=policy_path,
        registry_path=registry_path,
    )

    assert materialized is None
    assert any(
        "verifier_report.gate_materialization_admissibility.external_all_pass must be an object"
        in error
        for error in errors
    )
