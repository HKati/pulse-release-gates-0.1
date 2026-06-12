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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import PULSE_safe_pack_v0.tools.build_release_evidence_verifier_report_v0 as builder


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
    candidate_git_sha: str = HEX40,
    candidate_run_key: str = RUN_KEY,
    run_identity_git_sha: str = HEX40,
    run_identity_run_key: str = RUN_KEY,
    subject_commit_sha: str = HEX40,
) -> dict[str, Any]:
    manifest = copy.deepcopy(_load_json(INPUT_MANIFEST_EXAMPLE))

    manifest["run_identity"]["git_sha"] = run_identity_git_sha
    manifest["run_identity"]["run_key"] = run_identity_run_key

    manifest["subject"]["repository"] = "HKati/pulse-release-gates-0.1"
    manifest["subject"]["commit_sha"] = subject_commit_sha
    manifest["subject"]["release_candidate"] = "candidate-v0"

    manifest["policy_binding"]["policy_sha256"] = HEX64
    manifest["registry_binding"]["registry_sha256"] = HEX64

    manifest["candidate_evidence"]["detector_report"]["path"] = str(evidence_path)
    manifest["candidate_evidence"]["detector_report"]["expected_sha256"] = (
        expected_sha256
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["git_sha"] = (
        candidate_git_sha
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["run_key"] = (
        candidate_run_key
    )

    return manifest


def _assert_failed_non_authoritative_report(report: dict[str, Any]) -> None:
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def _candidate_schema_validation(report: dict[str, Any]) -> dict[str, Any]:
    assert report["evidence_inputs"]

    provenance = report["evidence_inputs"][0]["provenance"]

    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"

    diagnostic = provenance["candidate_schema_validation"]

    assert isinstance(diagnostic, dict)

    return diagnostic


def _build_report_from_manifest(
    *,
    manifest_path: pathlib.Path,
    commit_sha: str = HEX40,
    run_key: str = RUN_KEY,
) -> dict[str, Any]:
    return builder.build_report(
        policy_path=(REPO_ROOT / "pulse_gate_policy_v0.yml").resolve(),
        registry_path=(REPO_ROOT / "pulse_gate_registry_v0.yml").resolve(),
        repository="HKati/pulse-release-gates-0.1",
        commit_sha=commit_sha,
        run_key=run_key,
        release_candidate="candidate-v0",
        evidence_args=[],
        input_manifest_path=manifest_path,
    )


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
    assert any(
        "no gate materialization performed" in item
        for item in report["failed_checks"]
    )
    assert any(
        "no candidate evidence inputs were supplied" in item
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
    assert evidence_input["subject_binding"]["git_sha"] == HEX40
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY
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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)

    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}
    assert len(report["evidence_inputs"]) == 1

    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert evidence_input["kind"] == "detector_evidence"
    assert evidence_input["sha256"] == evidence_sha256
    assert evidence_input["schema_version"] == "detector_report_v0"
    assert evidence_input["subject_binding"]["git_sha"] == HEX40
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY

    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert provenance["candidate_evidence_id"] == "detector_report"
    assert provenance["expected_sha256"] == evidence_sha256
    assert provenance["actual_sha256_matches_expected"] is True
    assert provenance["candidate_subject_git_sha"] == HEX40
    assert provenance["candidate_subject_run_key"] == RUN_KEY
    assert provenance["manifest_subject_commit_sha"] == HEX40
    assert provenance["manifest_run_identity_git_sha"] == HEX40
    assert provenance["manifest_run_identity_run_key"] == RUN_KEY
    assert provenance["report_subject_commit_sha"] == HEX40
    assert provenance["report_run_identity_git_sha"] == HEX40
    assert provenance["report_run_identity_run_key"] == RUN_KEY
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True

    failed_checks = "\n".join(report["failed_checks"])

    assert "candidate evidence digest mismatch: detector_report" not in failed_checks
    assert (
        "candidate evidence subject git_sha mismatch against subject commit: detector_report"
        not in failed_checks
    )
    assert (
        "candidate evidence subject git_sha mismatch against run identity: detector_report"
        not in failed_checks
    )
    assert (
        "candidate evidence run_key mismatch against run identity: detector_report"
        not in failed_checks
    )
    assert any(
        "input manifest expectations are recorded only" in item
        for item in report["failed_checks"]
    )
    assert any(
        "expected candidate evidence recorded but not verified: detector_report" in item
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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)

    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    failed_checks = "\n".join(report["failed_checks"])

    assert "candidate evidence digest mismatch: detector_report" in failed_checks

    actual_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert evidence_input["sha256"] == actual_sha256
    assert provenance["expected_sha256"] == HEX64
    assert evidence_input["sha256"] != provenance["expected_sha256"]
    assert provenance["actual_sha256_matches_expected"] is False
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True


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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)

    assert report["verifier_decision"] == "FAILED"
    assert report["evidence_inputs"] == []
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    failed_checks = "\n".join(report["failed_checks"])

    assert "candidate evidence declared by manifest is missing" in failed_checks
    assert "expected candidate evidence not recorded: detector_report" in failed_checks
    assert (
        "expected gate materialization candidate evidence not recorded: "
        "detectors_materialized_ok -> detector_report"
    ) in failed_checks


def test_invalid_input_manifest_fails_closed_without_report(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{}", encoding="utf-8")

    manifest = _input_manifest(
        evidence_path=evidence_path,
        expected_sha256=HEX64,
    )
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "materialization_allowed_without_verifier"
    ] = True

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
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


def test_input_manifest_records_candidate_subject_run_binding_without_verifying(
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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert evidence_input["subject_binding"]["git_sha"] == HEX40
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY
    assert provenance["candidate_subject_git_sha"] == HEX40
    assert provenance["candidate_subject_run_key"] == RUN_KEY
    assert provenance["manifest_subject_commit_sha"] == HEX40
    assert provenance["manifest_run_identity_git_sha"] == HEX40
    assert provenance["manifest_run_identity_run_key"] == RUN_KEY
    assert provenance["report_subject_commit_sha"] == HEX40
    assert provenance["report_run_identity_git_sha"] == HEX40
    assert provenance["report_run_identity_run_key"] == RUN_KEY
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_subject_commit_mismatch_stays_failed(
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    candidate_git_sha = "a" * 40
    subject_commit_sha = "c" * 40

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
            candidate_git_sha=candidate_git_sha,
            run_identity_git_sha=candidate_git_sha,
            subject_commit_sha=subject_commit_sha,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        candidate_git_sha,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    failed_checks = "\n".join(report["failed_checks"])
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert (
        "candidate evidence subject git_sha mismatch against subject commit: "
        "detector_report"
    ) in failed_checks
    assert provenance["subject_git_sha_matches_subject_commit"] is False
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True
    assert evidence_input["subject_binding"]["git_sha"] == candidate_git_sha
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_run_identity_git_sha_mismatch_stays_failed(
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    candidate_git_sha = "a" * 40
    run_identity_git_sha = "d" * 40

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
            candidate_git_sha=candidate_git_sha,
            run_identity_git_sha=run_identity_git_sha,
            subject_commit_sha=candidate_git_sha,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        candidate_git_sha,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    failed_checks = "\n".join(report["failed_checks"])
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert (
        "candidate evidence subject git_sha mismatch against run identity: "
        "detector_report"
    ) in failed_checks
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is False
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True
    assert evidence_input["subject_binding"]["git_sha"] == candidate_git_sha
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_run_key_mismatch_stays_failed(
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    candidate_run_key = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"
    manifest_run_key = "GITHUB_RUN_ID=2|GITHUB_RUN_NUMBER=2|GITHUB_WORKFLOW=PULSE CI"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
            candidate_run_key=candidate_run_key,
            run_identity_run_key=manifest_run_key,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        HEX40,
        "--run-key",
        candidate_run_key,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    failed_checks = "\n".join(report["failed_checks"])
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert (
        "candidate evidence run_key mismatch against run identity: "
        "detector_report"
    ) in failed_checks
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is False
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True
    assert provenance["run_key_matches_report_run_identity"] is True
    assert evidence_input["subject_binding"]["git_sha"] == HEX40
    assert evidence_input["subject_binding"]["run_key"] == candidate_run_key

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_subject_run_binding_normalizes_git_sha_case(
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    lowercase_sha = "a" * 40
    uppercase_sha = "A" * 40

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
            candidate_git_sha=lowercase_sha,
            run_identity_git_sha=uppercase_sha,
            subject_commit_sha=uppercase_sha,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        uppercase_sha,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    failed_checks = "\n".join(report["failed_checks"])
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert (
        "candidate evidence subject git_sha mismatch against subject commit: "
        "detector_report"
    ) not in failed_checks
    assert (
        "candidate evidence subject git_sha mismatch against run identity: "
        "detector_report"
    ) not in failed_checks
    assert evidence_input["subject_binding"]["git_sha"] == lowercase_sha
    assert evidence_input["subject_binding"]["run_key"] == RUN_KEY
    assert provenance["manifest_subject_commit_sha"] == uppercase_sha
    assert provenance["manifest_run_identity_git_sha"] == uppercase_sha
    assert provenance["report_subject_commit_sha"] == uppercase_sha
    assert provenance["report_run_identity_git_sha"] == uppercase_sha
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is True
    assert provenance["subject_git_sha_matches_report_run_identity"] is True

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_explicit_report_identity_override_mismatch_stays_failed(
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    manifest_sha = "a" * 40
    override_sha = "d" * 40
    manifest_run_key = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"
    override_run_key = "GITHUB_RUN_ID=2|GITHUB_RUN_NUMBER=2|GITHUB_WORKFLOW=PULSE CI"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
            candidate_git_sha=manifest_sha,
            candidate_run_key=manifest_run_key,
            run_identity_git_sha=manifest_sha,
            run_identity_run_key=manifest_run_key,
            subject_commit_sha=manifest_sha,
        ),
    )

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        override_sha,
        "--run-key",
        override_run_key,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    failed_checks = "\n".join(report["failed_checks"])
    evidence_input = report["evidence_inputs"][0]
    provenance = evidence_input["provenance"]

    assert report["run_identity"]["git_sha"] == override_sha
    assert report["run_identity"]["run_key"] == override_run_key
    assert report["subject"]["commit_sha"] == override_sha

    assert (
        "candidate evidence subject git_sha mismatch against subject commit: "
        "detector_report"
    ) in failed_checks
    assert (
        "candidate evidence subject git_sha mismatch against run identity: "
        "detector_report"
    ) in failed_checks
    assert (
        "candidate evidence run_key mismatch against run identity: "
        "detector_report"
    ) in failed_checks

    assert evidence_input["subject_binding"]["git_sha"] == manifest_sha
    assert evidence_input["subject_binding"]["run_key"] == manifest_run_key
    assert provenance["subject_git_sha_matches_subject_commit"] is True
    assert provenance["subject_git_sha_matches_run_identity"] is True
    assert provenance["run_key_matches_run_identity"] is True
    assert provenance["subject_git_sha_matches_report_subject_commit"] is False
    assert provenance["subject_git_sha_matches_report_run_identity"] is False
    assert provenance["run_key_matches_report_run_identity"] is False
    assert provenance["report_subject_commit_sha"] == override_sha
    assert provenance["report_run_identity_git_sha"] == override_sha
    assert provenance["report_run_identity_run_key"] == override_run_key

    assert report["verifier_decision"] == "FAILED"
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}


def test_input_manifest_candidate_parse_failed_records_diagnostic(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{not-json", encoding="utf-8")

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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "failed"
    assert diagnostic["errors"]
    assert diagnostic["errors"][0]["code"] == "candidate_parse_failed"


def test_input_manifest_candidate_duplicate_key_records_diagnostic(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text(
        (
            '{"schema_version": "detector_report_v0", '
            '"result": "one", '
            '"result": "two"}'
        ),
        encoding="utf-8",
    )

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
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "failed"
    assert diagnostic["errors"][0]["code"] == "candidate_duplicate_key"
    assert diagnostic["duplicate_key_validation"]["status"] == "failed"
    assert diagnostic["duplicate_key_validation"]["errors"]
    assert (
        diagnostic["duplicate_key_validation"]["errors"][0]["code"]
        == "candidate_duplicate_key"
    )


def test_input_manifest_candidate_schema_unavailable_records_diagnostic(
    tmp_path: pathlib.Path,
) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "unknown_candidate_schema_v0",
                "result": "candidate-only",
            }
        ),
        encoding="utf-8",
    )

    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    manifest = _input_manifest(
        evidence_path=evidence_path,
        expected_sha256=evidence_sha256,
    )
    manifest["candidate_evidence"]["detector_report"][
        "schema_version"
    ] = "unknown_candidate_schema_v0"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    result = _run_tool(
        "--out",
        str(out_path),
        "--input-manifest",
        str(manifest_path),
        "--commit-sha",
        HEX40,
        "--run-key",
        RUN_KEY,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "unavailable"
    assert diagnostic["errors"]
    assert diagnostic["errors"][0]["code"] == "candidate_schema_unavailable"


def test_candidate_schema_file_unavailable_records_diagnostic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    missing_schema_path = tmp_path / "missing_schema.json"
    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(missing_schema_path),
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "unavailable"
    assert diagnostic["errors"][0]["code"] == "candidate_schema_unavailable"


def test_candidate_schema_invalid_records_diagnostic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if builder.jsonschema is None:
        pytest.skip("jsonschema is required for schema-invalid diagnostic path")

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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    schema_path = tmp_path / "invalid_schema.json"
    schema_path.write_text('{"type": 123}', encoding="utf-8")

    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(schema_path),
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "failed"
    assert diagnostic["errors"][0]["code"] == "candidate_schema_invalid"


def test_candidate_validator_unavailable_records_diagnostic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    schema_path = tmp_path / "detector_report_schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(schema_path),
    )
    monkeypatch.setattr(builder, "jsonschema", None)

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "unavailable"
    assert diagnostic["errors"][0]["code"] == "candidate_validator_unavailable"


def test_candidate_schema_validation_failed_records_diagnostic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if builder.jsonschema is None:
        pytest.skip("jsonschema is required for schema-validation failure path")

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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    schema_path = tmp_path / "detector_report_schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": [
                    "required_detector_field",
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(schema_path),
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "failed"
    assert diagnostic["errors"][0]["code"] == "candidate_schema_validation_failed"


def test_candidate_partial_validation_rejected_records_diagnostic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    schema_path = tmp_path / "detector_report_schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }
        ),
        encoding="utf-8",
    )

    class PartialValidationError(Exception):
        pass

    class FakeValidator:
        @staticmethod
        def check_schema(_schema: dict[str, Any]) -> None:
            return None

        def __init__(self, _schema: dict[str, Any]) -> None:
            return None

        def validate(self, _candidate: dict[str, Any]) -> None:
            raise RuntimeError("validator stopped before completion")

    class FakeJsonschema:
        ValidationError = PartialValidationError
        Draft202012Validator = FakeValidator

    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(schema_path),
    )
    monkeypatch.setattr(builder, "jsonschema", FakeJsonschema)

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    diagnostic = _candidate_schema_validation(report)

    assert diagnostic["status"] == "failed"
    assert diagnostic["errors"][0]["code"] == "candidate_partial_validation_rejected"


def test_candidate_schema_validation_success_is_not_represented_under_current_schema(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if builder.jsonschema is None:
        pytest.skip("jsonschema is required for success-not-represented path")

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
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    schema_path = tmp_path / "detector_report_schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": [
                    "schema_version",
                    "result",
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setitem(
        builder.CANDIDATE_SCHEMA_VERSION_TO_PATH,
        "detector_report_v0",
        str(schema_path),
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    report = _build_report_from_manifest(manifest_path=manifest_path)
    _assert_failed_non_authoritative_report(report)

    provenance = report["evidence_inputs"][0]["provenance"]

    assert "candidate_schema_validation" not in provenance
    assert provenance["trusted"] is False
    assert provenance["verification_status"] == "not_verified"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
