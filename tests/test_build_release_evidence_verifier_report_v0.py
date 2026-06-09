#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
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
    / "build_release_evidence_verifier_report_v0.py"
)
INPUT_MANIFEST_EXAMPLE = (
    REPO_ROOT / "examples" / "release_evidence_input_manifest_v0.minimal.example.json"
)

HEX40 = "a" * 40
HEX64 = "b" * 64
RUN_KEY = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


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


def _input_manifest(
    *,
    evidence_path: pathlib.Path,
    expected_sha256: str,
) -> dict[str, Any]:
    manifest = copy.deepcopy(_load_json(INPUT_MANIFEST_EXAMPLE))
    manifest["run_identity"]["git_sha"] = HEX40
    manifest["run_identity"]["run_key"] = RUN_KEY
    manifest["subject"]["repository"] = "HKati/pulse-release-gates-0.1"
    manifest["subject"]["commit_sha"] = HEX40
    manifest["subject"]["release_candidate"] = "candidate-v0"
    manifest["policy_binding"]["policy_sha256"] = HEX64
    manifest["registry_binding"]["registry_sha256"] = HEX64
    manifest["candidate_evidence"]["detector_report"]["path"] = str(evidence_path)
    manifest["candidate_evidence"]["detector_report"]["expected_sha256"] = (
        expected_sha256
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["git_sha"] = (
        HEX40
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["run_key"] = (
        RUN_KEY
    )
    return manifest


def test_build_failed_report_without_inputs(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--repository",
        "HKati/pulse-release-gates-0.1",
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
        "--release-candidate",
        "candidate-v0",
    )

    assert result.returncode == 0, result.stderr
    assert "OK: wrote fail-closed release evidence verifier report" in result.stdout

    report = _load_json(out_path)
    assert report["schema_version"] == "release_evidence_verifier_report_v0"
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}
    assert any("does not verify evidence yet" in item for item in report["failed_checks"])
    assert any(
        "no verified relation bindings present" in item
        for item in report["failed_checks"]
    )


def test_candidate_evidence_is_recorded_but_not_verified(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_payload = {
        "schema_version": "detector_report_v0",
        "result": "candidate-only",
    }
    evidence_path.write_text(json.dumps(evidence_payload), encoding="utf-8")
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--repository",
        "HKati/pulse-release-gates-0.1",
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
        "--release-candidate",
        "candidate-v0",
        "--evidence",
        f"detector_evidence={evidence_path}",
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    assert len(report["evidence_inputs"]) == 1
    evidence_input = report["evidence_inputs"][0]
    assert evidence_input["kind"] == "detector_evidence"
    assert evidence_input["sha256"] == hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest()
    assert evidence_input["schema_version"] == "detector_report_v0"
    assert evidence_input["provenance"]["trusted"] is False
    assert evidence_input["provenance"]["verification_status"] == "not_verified"


def test_input_manifest_records_existing_candidate_without_verifying(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_payload = {
        "schema_version": "detector_report_v0",
        "result": "candidate-only",
    }
    evidence_path.write_text(json.dumps(evidence_payload), encoding="utf-8")
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    assert len(report["evidence_inputs"]) == 1
    evidence_input = report["evidence_inputs"][0]
    assert evidence_input["kind"] == "detector_evidence"
    assert evidence_input["sha256"] == evidence_sha256
    assert evidence_input["schema_version"] == "detector_report_v0"
    assert evidence_input["provenance"]["trusted"] is False
    assert evidence_input["provenance"]["verification_status"] == "not_verified"
    assert evidence_input["provenance"]["candidate_evidence_id"] == "detector_report"
    assert evidence_input["provenance"]["expected_sha256"] == evidence_sha256
    assert evidence_input["provenance"]["actual_sha256_matches_expected"] is True

    assert any(
        "input manifest expectations are recorded only" in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected candidate evidence recorded but not verified: detector_report"
        in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected relation binding pending verification: detector_report_to_subject_commit"
        in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected gate materialization pending verification: detectors_materialized_ok"
        in item
        for item in report["failed_checks"]
    )
    assert any(
        "input manifest expectation comparison is fail-closed and descriptive only"
        in item
        for item in report["warnings"]
    )


def test_input_manifest_digest_mismatch_records_failed_report(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "detector_report_v0",
                "result": "candidate-only",
            }
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=HEX64,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert any(
        "candidate evidence digest mismatch: detector_report" in item
        for item in report["failed_checks"]
    )
    assert report["evidence_inputs"][0]["provenance"][
        "actual_sha256_matches_expected"
    ] is False
    actual_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    evidence_input = report["evidence_inputs"][0]

    assert evidence_input["sha256"] == actual_sha256
    assert evidence_input["provenance"]["expected_sha256"] == HEX64
    assert evidence_input["sha256"] != evidence_input["provenance"]["expected_sha256"]

    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_missing_candidate_writes_failed_report(
    tmp_path: pathlib.Path,
) -> None:
    missing_evidence = tmp_path / "missing_detector_report.json"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=missing_evidence,
            expected_sha256=HEX64,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["evidence_inputs"] == []
    assert any(
        "candidate evidence declared by manifest is missing" in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected candidate evidence not recorded: detector_report" in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected gate materialization candidate evidence not recorded: "
        "detectors_materialized_ok -> detector_report" in item
        for item in report["failed_checks"]
    )


def test_invalid_input_manifest_fails_closed_without_report(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{}", encoding="utf-8")

    manifest = _input_manifest(
        evidence_path=evidence_path,
        expected_sha256=HEX64,
    )
    manifest["expected_gate_materialization"][
        "detectors_materialized_ok"
    ]["materialization_allowed_without_verifier"] = True

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert result.returncode != 0
    assert "release evidence input manifest failed validation" in result.stderr
    assert not out_path.exists()


def test_input_manifest_cannot_be_combined_with_direct_evidence(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{}", encoding="utf-8")
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--evidence",
        f"detector_evidence={evidence_path}",
    )

    assert result.returncode != 0
    assert "--input-manifest cannot be combined with --evidence" in result.stderr
    assert not out_path.exists()


def test_invalid_evidence_kind_fails_closed(tmp_path: pathlib.Path) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
        "--evidence",
        f"unsupported_kind={evidence_path}",
    )

    assert result.returncode != 0
    assert "unsupported evidence kind" in result.stderr
    assert not out_path.exists()


def test_missing_evidence_file_fails_closed(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    missing = tmp_path / "missing_detector_report.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
        "--evidence",
        f"detector_evidence={missing}",
    )

    assert result.returncode != 0
    assert "candidate evidence file not found" in result.stderr
    assert not out_path.exists()


def test_pass_or_allow_are_never_emitted(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verifier_decision"] not in {"PASS", "ALLOW", "PROD-PASS"}
