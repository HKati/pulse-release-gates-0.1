#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1] 
TOOL = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_release_evidence_expectation_summary_v0.py"
)
EXAMPLE = (
    REPO_ROOT
    / "examples"
    / "release_evidence_expectation_summary_v0.failed.example.json"
)
SCHEMA = REPO_ROOT / "schemas" / "release_evidence_expectation_summary_v0.schema.json"

HEX40 = "a" * 40
HEX64 = "b" * 64
RUN_KEY = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            *args,
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _failed_verifier_report() -> dict[str, Any]:
    return {
        "schema_version": "release_evidence_verifier_report_v0",
        "created_utc": "2026-01-01T00:00:00Z",
        "verifier_id": "pulse_release_evidence_verifier_v0",
        "verifier_version": "0.1.0",
        "verifier_decision": "FAILED",
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
                    "trusted": False,
                    "verification_status": "not_verified",
                    "candidate_evidence_id": "detector_report",
                },
            }
        ],
        "verified_artifacts": [],
        "relation_bindings": [],
        "gate_materialization": {},
        "failed_checks": [
            "trusted release-evidence verifier skeleton does not verify evidence yet",
            "expected candidate evidence recorded but not verified: detector_report",
            "expected relation binding pending verification: detector_report_to_subject_commit",
            "expected relation binding pending verification: detector_report_to_gate",
            "expected gate materialization pending verification: detectors_materialized_ok",
            "input manifest expectations are recorded only; verification is not implemented",
            "input manifest expected relation bindings are not verified by skeleton",
            "input manifest expected gate materialization bindings are not materialized by skeleton",
        ],
        "warnings": [
            "input manifest expectation comparison is fail-closed and descriptive only",
            "input manifest declares 1 candidate evidence item(s), 2 expected relation binding(s), and 1 expected gate materialization item(s)",
        ],
    }


def test_schema_and_example_exist() -> None:
    assert SCHEMA.exists()
    assert EXAMPLE.exists()
    assert TOOL.exists()


def test_example_summary_validates() -> None:
    try:
        import jsonschema
    except Exception:  # pragma: no cover
        pytest.fail("jsonschema is required for summary schema tests")

    schema = _load_json(SCHEMA)
    example = _load_json(EXAMPLE)

    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(example)


def test_build_summary_from_failed_report(tmp_path: pathlib.Path) -> None:
    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    out_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    _write_json(report_path, _failed_verifier_report())

    result = _run_tool(
        "--report",
        str(report_path),
        "--out",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr
    assert "OK: wrote release evidence expectation summary" in result.stdout

    summary = _load_json(out_path)

    assert summary["schema_version"] == "release_evidence_expectation_summary_v0"
    assert summary["source_report"]["verifier_decision"] == "FAILED"
    assert summary["summary"]["verifier_readiness"] == "NOT_READY"

    assert summary["summary"]["evidence_inputs_total"] == 1
    assert summary["summary"]["verified_artifacts_total"] == 0
    assert summary["summary"]["relation_bindings_total"] == 0
    assert summary["summary"]["gate_materialization_total"] == 0

    assert summary["summary"]["candidate_evidence_not_verified_count"] == 1
    assert summary["summary"]["pending_relation_binding_count"] == 2
    assert summary["summary"]["pending_gate_materialization_count"] == 1

    gap_kinds = {gap["kind"] for gap in summary["pre_materialization_gaps"]}
    assert "candidate_evidence_not_verified" in gap_kinds
    assert "pending_relation_binding" in gap_kinds
    assert "pending_gate_materialization" in gap_kinds

    assert summary["authority_boundary"]["is_release_authority"] is False
    assert summary["authority_boundary"]["materializes_gates"] is False
    assert summary["authority_boundary"]["writes_status_json"] is False
    assert summary["authority_boundary"]["reopens_release_grade_materialization"] is False
    assert summary["authority_boundary"]["replaces_check_gates"] is False


def test_invalid_verifier_report_fails_closed_without_summary(
    tmp_path: pathlib.Path,
) -> None:
    report = _failed_verifier_report()
    report.pop("relation_bindings")

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    out_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    _write_json(report_path, report)

    result = _run_tool(
        "--report",
        str(report_path),
        "--out",
        str(out_path),
    )

    assert result.returncode != 0
    assert "release evidence verifier report failed validation" in result.stderr
    assert not out_path.exists()


def test_digest_mismatch_gap_is_classified(tmp_path: pathlib.Path) -> None:
    report = _failed_verifier_report()
    report["failed_checks"].append("candidate evidence digest mismatch: detector_report")

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    out_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    _write_json(report_path, report)

    result = _run_tool(
        "--report",
        str(report_path),
        "--out",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr

    summary = _load_json(out_path)
    assert summary["summary"]["digest_mismatch_count"] == 1
    assert any(
        gap["kind"] == "digest_mismatch" and gap["id"] == "detector_report"
        for gap in summary["pre_materialization_gaps"]
    )


def test_no_candidate_evidence_gap_is_classified(tmp_path: pathlib.Path) -> None:
    report = _failed_verifier_report()
    report["evidence_inputs"] = []
    report["failed_checks"] = [
        "no candidate evidence inputs were supplied",
        "no verified relation bindings present",
        "no gate materialization performed",
    ]

    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    out_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    _write_json(report_path, report)

    result = _run_tool(
        "--report",
        str(report_path),
        "--out",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr

    summary = _load_json(out_path)
    gap_kinds = {gap["kind"] for gap in summary["pre_materialization_gaps"]}

    assert "no_candidate_evidence" in gap_kinds
    assert "no_verified_relation_bindings" in gap_kinds
    assert "no_gate_materialization" in gap_kinds


def test_failed_source_report_cannot_be_marked_ready_by_schema() -> None:
    try:
        import jsonschema
    except Exception:  # pragma: no cover
        pytest.fail("jsonschema is required for summary schema tests")

    schema = _load_json(SCHEMA)
    summary = _load_json(EXAMPLE)

    summary["source_report"]["verifier_decision"] = "FAILED"
    summary["summary"]["verifier_readiness"] = "REPORT_VERIFIED_NON_AUTHORITY"

    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(summary))

    assert errors


def test_summary_never_claims_release_authority(tmp_path: pathlib.Path) -> None:
    report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    out_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    _write_json(report_path, _failed_verifier_report())

    result = _run_tool(
        "--report",
        str(report_path),
        "--out",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr

    summary = _load_json(out_path)
    boundary = summary["authority_boundary"]

    assert boundary == {
        "is_release_authority": False,
        "materializes_gates": False,
        "reopens_release_grade_materialization": False,
        "replaces_check_gates": False,
        "writes_status_json": False,
    }


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
