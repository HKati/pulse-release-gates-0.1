#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_evidence_verifier_report_v0 import (
    check_release_evidence_verifier_report,
)


CHECKER = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "check_release_evidence_verifier_report_v0.py"
)
FAILED_EXAMPLE = (
    REPO_ROOT / "examples" / "release_evidence_verifier_report_v0.failed.example.json"
)

HEX40 = "a" * 40
HEX64 = "b" * 64
RUN_KEY = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _verified_artifact(path: str = "artifacts/detectors/detector_report.json") -> dict[str, Any]:
    return {
        "path": path,
        "sha256": HEX64,
        "schema_version": "detector_report_v0",
        "verified": True,
    }


def _relation_binding(
    *,
    relation_id: str = "detector_report_to_subject_commit",
    source: str = "artifacts/detectors/detector_report.json",
    target: str = "subject.commit_sha",
    verified: bool = True,
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "binding_type": "artifact_to_subject",
        "source": source,
        "target": target,
        "verified": verified,
        "evidence": [
            _verified_artifact(source)
        ],
        "failure_reason": None if verified else "relation was not verified",
    }


def _verified_report() -> dict[str, Any]:
    relation_id = "detector_report_to_subject_commit"

    return {
        "schema_version": "release_evidence_verifier_report_v0",
        "created_utc": "2026-01-01T00:00:00Z",
        "verifier_id": "pulse_release_evidence_verifier_v0",
        "verifier_version": "0.1.0",
        "verifier_decision": "VERIFIED",
        "run_identity": {
            "run_mode": "prod",
            "run_key": RUN_KEY,
            "git_sha": HEX40,
        },
        "subject": {
            "repository": "HKati/pulse-release-gates-0.1",
            "commit_sha": HEX40,
            "release_candidate": "candidate-v0",
        },
        "policy_binding": {
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_sha256": HEX64,
            "policy_set": "required+release_required",
        },
        "registry_binding": {
            "registry_path": "pulse_gate_registry_v0.yml",
            "registry_sha256": HEX64,
        },
        "evidence_inputs": [
            {
                "kind": "detector_evidence",
                "path": "artifacts/detectors/detector_report.json",
                "sha256": HEX64,
                "schema_version": "detector_report_v0",
                "subject_binding": {
                    "git_sha": HEX40,
                    "run_key": RUN_KEY,
                },
                "provenance": {
                    "producer": "unit-test"
                },
            }
        ],
        "verified_artifacts": [
            _verified_artifact()
        ],
        "relation_bindings": [
            _relation_binding(relation_id=relation_id)
        ],
        "gate_materialization": {
            "detectors_materialized_ok": {
                "value": True,
                "source": "release_evidence_verifier_report_v0",
                "verified": True,
                "evidence_artifacts": [
                    _verified_artifact()
                ],
                "relation_bindings": [
                    relation_id
                ],
                "policy_relation": "release_required",
            }
        },
        "failed_checks": [],
        "warnings": [],
    }


def test_failed_example_passes_checker() -> None:
    errors = check_release_evidence_verifier_report(FAILED_EXAMPLE)

    assert errors == []


def test_valid_verified_report_passes_checker(tmp_path: pathlib.Path) -> None:
    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, _verified_report())

    errors = check_release_evidence_verifier_report(report_path)

    assert errors == []


def test_missing_relation_id_reference_fails(tmp_path: pathlib.Path) -> None:
    report = _verified_report()
    report["gate_materialization"]["detectors_materialized_ok"]["relation_bindings"] = [
        "missing_relation"
    ]

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    errors = check_release_evidence_verifier_report(report_path)

    assert any("missing relation_id: missing_relation" in error for error in errors)


def test_duplicate_relation_id_fails(tmp_path: pathlib.Path) -> None:
    report = _verified_report()
    report["relation_bindings"].append(
        _relation_binding(
            relation_id="detector_report_to_subject_commit",
            source="artifacts/detectors/other_report.json",
            target="subject.release_candidate",
        )
    )

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    errors = check_release_evidence_verifier_report(report_path)

    assert any(
        "duplicate relation_id in report.relation_bindings" in error
        for error in errors
    )


def test_unverified_referenced_relation_fails(tmp_path: pathlib.Path) -> None:
    report = _verified_report()
    report["relation_bindings"][0] = _relation_binding(verified=False)

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    errors = check_release_evidence_verifier_report(report_path)

    assert any("not verified=true" in error for error in errors)


def test_gate_materialization_without_relation_ids_fails(tmp_path: pathlib.Path) -> None:
    report = _verified_report()
    report["gate_materialization"]["detectors_materialized_ok"]["relation_bindings"] = []

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    errors = check_release_evidence_verifier_report(report_path)

    assert any(
        "gate_materialization.detectors_materialized_ok.relation_bindings"
        in error
        for error in errors
    )


@pytest.mark.parametrize("bad_decision", ["PASS", "ALLOW", "PROD-PASS"])
def test_release_authority_words_are_rejected_as_verifier_decisions(
    tmp_path: pathlib.Path,
    bad_decision: str,
) -> None:
    report = _verified_report()
    report["verifier_decision"] = bad_decision

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    errors = check_release_evidence_verifier_report(report_path)

    assert errors


def test_checker_cli_passes_failed_example() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--report",
            str(FAILED_EXAMPLE),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: release evidence verifier report relation integrity satisfied" in result.stdout


def test_checker_cli_reports_errors(tmp_path: pathlib.Path) -> None:
    report = _verified_report()
    report["gate_materialization"]["detectors_materialized_ok"]["relation_bindings"] = [
        "missing_relation"
    ]

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, report)

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--report",
            str(report_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "ERRORS (fail-closed):" in result.stderr
    assert "missing_relation" in result.stderr


def test_checker_fails_closed_when_jsonschema_unavailable(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import PULSE_safe_pack_v0.tools.check_release_evidence_verifier_report_v0 as checker

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    _write_json(report_path, _verified_report())

    monkeypatch.setattr(checker, "jsonschema", None)

    errors = checker.check_release_evidence_verifier_report(report_path)

    assert any("jsonschema is required" in error for error in errors)
    assert any("partial fallback validation is not allowed" in error for error in errors)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
