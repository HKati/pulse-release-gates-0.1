#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_release_grade_package_complete_v1.py"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_check_release_grade_package_complete_v1.py"

PACKAGE_INVENTORY = "package_digest_inventory_v0.json"

SUBJECT_NAME = "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0"
SUBJECT_SHA256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
COMMIT_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY_ID = "pulse-gate-policy-v0"
POLICY_URI = "https://pulse.invalid/policies/pulse-slsa-vsa-policy-v0.json"
POLICY_SHA256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
VERIFIER_ID = "https://pulse.invalid/verifiers/pulsemech-vsa-verifier-v0"
VERIFIED_LEVEL = "SLSA_BUILD_LEVEL_3"
TIME_VERIFIED = "2026-07-04T00:00:00Z"
CURRENT_RUN_KEY = (
    "GITHUB_RUN_ID=1234567890"
    "|GITHUB_RUN_NUMBER=2692"
    "|GITHUB_RUN_ATTEMPT=1"
    "|GITHUB_WORKFLOW=PULSE CI"
)


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_package_files(package_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in package_dir.rglob("*")
        if path.is_file() and path.relative_to(package_dir).as_posix() != PACKAGE_INVENTORY
    )


def rebuild_digest_inventory(package_dir: Path) -> None:
    files = []
    for path in all_package_files(package_dir):
        relative = path.relative_to(package_dir).as_posix()
        files.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    write_json(
        package_dir / PACKAGE_INVENTORY,
        {
            "schema_version": "release_grade_reference_package_digest_inventory_v0",
            "algorithm": "sha256",
            "file_count": len(files),
            "files": files,
        },
    )


def packet_payload() -> dict[str, Any]:
    return {
        "schema_version": "slsa_vsa_trusted_producer_input_packet_v0",
        "packet_type": "slsa_vsa_trusted_producer_input_packet",
        "created_utc": "2026-07-07T00:00:00Z",
        "producer_identity": {
            "producer_id": "pulse_slsa_vsa_trusted_evidence_producer_v0",
            "producer_name": "PULSE SLSA VSA trusted evidence producer",
            "producer_version": "0.1.0",
            "producer_source": "github-actions",
            "ci_workflow_or_job_identity": "PULSE CI / SLSA VSA trusted evidence producer",
        },
        "run_binding": {
            "current_run_id": "1234567890",
            "current_run_number": "2692",
            "current_run_attempt": "1",
            "current_run_key": CURRENT_RUN_KEY,
            "workflow_name": "PULSE CI",
            "job_name": "slsa-vsa-trusted-evidence-producer",
            "commit_sha": COMMIT_SHA,
            "release_candidate_id": "pulse-release-gates-0.1-candidate-v0",
        },
        "artifact_binding": {
            "subject_name": SUBJECT_NAME,
            "subject_sha256": SUBJECT_SHA256,
            "resource_uri": SUBJECT_NAME,
            "release_candidate_id": "pulse-release-gates-0.1-candidate-v0",
            "artifact_digest_sha256": SUBJECT_SHA256,
        },
        "policy_binding": {
            "expected_policy_id": POLICY_ID,
            "expected_policy_uri": POLICY_URI,
            "expected_policy_sha256": POLICY_SHA256,
        },
        "verifier_binding": {
            "expected_verifier_id": VERIFIER_ID,
        },
        "expected_verified_level": VERIFIED_LEVEL,
        "freshness": {
            "expected_time_verified": TIME_VERIFIED,
            "freshness_epoch": "current_run",
        },
        "recorded_signal_mode": "recorded_signal_only",
        "candidate_set": "slsa_vsa_recorded_intake_candidate",
    }


def report_payload() -> dict[str, Any]:
    return {
        "schema_version": "slsa_vsa_trusted_evidence_producer_report_v0",
        "report_type": "slsa_vsa_trusted_evidence_producer_report",
        "created_utc": "2026-07-07T00:00:00Z",
        "producer": {
            "producer_id": "pulse_slsa_vsa_trusted_evidence_producer_v0",
            "producer_name": "PULSE SLSA VSA trusted evidence producer",
            "producer_version": "0.1.0",
            "producer_source": "github-actions",
            "ci_workflow_or_job_identity": "PULSE CI / SLSA VSA trusted evidence producer",
        },
        "run_binding": {
            "current_run_id": "1234567890",
            "current_run_number": "2692",
            "current_run_attempt": "1",
            "current_run_key": CURRENT_RUN_KEY,
            "workflow_name": "PULSE CI",
            "job_name": "slsa-vsa-trusted-evidence-producer",
            "commit_sha": COMMIT_SHA,
            "release_candidate_id": "pulse-release-gates-0.1-candidate-v0",
        },
        "artifact_binding": {
            "subject_name": SUBJECT_NAME,
            "subject_sha256": SUBJECT_SHA256,
            "resource_uri": SUBJECT_NAME,
            "release_candidate_id": "pulse-release-gates-0.1-candidate-v0",
            "artifact_digest_sha256": SUBJECT_SHA256,
            "subject_digest_matches": True,
            "resource_uri_matches": True,
            "release_candidate_matches": True,
            "artifact_digest_matches": True,
        },
        "policy_binding": {
            "expected_policy_id": POLICY_ID,
            "expected_policy_uri": POLICY_URI,
            "expected_policy_sha256": POLICY_SHA256,
            "evidence_policy_id": POLICY_ID,
            "evidence_policy_uri": POLICY_URI,
            "evidence_policy_sha256": POLICY_SHA256,
            "policy_identity_matches": True,
            "policy_digest_matches": True,
        },
        "verifier_binding": {
            "expected_verifier_id": VERIFIER_ID,
            "evidence_verifier_id": VERIFIER_ID,
            "verifier_trusted": True,
        },
        "evidence": {
            "evidence_path": "artifacts/slsa/vsa_evidence.json",
            "evidence_sha256": "c" * 64,
            "evidence_schema_version": "slsa_vsa_evidence_v0",
            "evidence_type": "slsa_vsa",
            "time_verified": TIME_VERIFIED,
            "verification_result": "PASSED",
            "expected_verified_level": VERIFIED_LEVEL,
            "evidence_verified_levels": [VERIFIED_LEVEL],
            "verified_level_ok": True,
        },
        "freshness": {
            "freshness_result": "fresh_current_run",
            "stale_vsa_evidence": False,
            "previous_run_artifact_reuse": False,
            "time_verified_current_run_match": True,
            "current_run_binding_ok": True,
        },
        "recorded_signal_mode": "recorded_signal_only",
        "candidate_set": "slsa_vsa_recorded_intake_candidate",
        "producer_decision": "TRUSTED_EVIDENCE_ACCEPTED",
        "ok": True,
        "failed_checks": [],
        "warnings": [],
    }


def make_complete_package(tmp_path: Path) -> Path:
    package_dir = Path(
        tempfile.mkdtemp(
            prefix="release_grade_package_",
            dir=tmp_path,
        )
    )

    write_json(
        package_dir / "run_metadata_v0.json",
        {
            "schema_version": "release_grade_run_metadata_v0",
            "repository": "HKati/pulse-release-gates-0.1",
            "git_sha": COMMIT_SHA,
            "workflow_ref": (
                "HKati/pulse-release-gates-0.1/.github/workflows/pulse_ci.yml@"
                + COMMIT_SHA
            ),
            "run_id": 1234567890,
            "run_attempt": 1,
            "run_key": CURRENT_RUN_KEY,
            "authority_boundary": {
                "authorizes_release": False,
                "package_only": True,
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "required_gate_evidence_v0.json",
        {
            "schema_version": "required_gate_evidence_v0",
            "gates": {
                "core_required_reference_ok": True,
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "status_baseline.json",
        {
            "schema_version": "status_baseline_v0",
            "metrics": {
                "git_sha": COMMIT_SHA,
                "run_key": CURRENT_RUN_KEY,
            },
            "gates": {
                "core_required_reference_ok": True,
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "recorded_release_candidate_index_v0.json",
        {
            "schema_version": "recorded_release_candidate_index_v0",
            "candidates": ["candidate_0.json"],
        },
    )
    write_json(
        package_dir / "artifacts" / "release_evidence_input_manifest_v0.json",
        {
            "schema_version": "release_evidence_input_manifest_v0",
            "inputs": [
                "status_baseline.json",
                "slsa_vsa_trusted_producer_report_v0.json",
                "external/llamaguard_raw.jsonl",
            ],
        },
    )
    write_json(
        package_dir / "artifacts" / "recorded_release_evidence_verifier_v0.json",
        {
            "schema_version": "recorded_release_evidence_verifier_v0",
            "status": "verified",
            "errors": [],
        },
    )

    write_text(
        package_dir / "artifacts" / "external" / "llamaguard_raw.jsonl",
        json.dumps(
            {
                "schema_version": "llamaguard_raw_evidence_record_v0",
                "run": {
                    "repository": "HKati/pulse-release-gates-0.1",
                    "git_sha": COMMIT_SHA,
                    "run_key": CURRENT_RUN_KEY,
                    "workflow_ref": (
                        "HKati/pulse-release-gates-0.1/.github/workflows/pulse_ci.yml@"
                        + COMMIT_SHA
                    ),
                },
                "result": "pass",
            },
            sort_keys=True,
        )
        + "\n",
    )
    write_json(
        package_dir / "artifacts" / "external" / "llamaguard_evaluator_manifest_v0.json",
        {
            "schema_version": "llamaguard_evaluator_manifest_v0",
            "run": {
                "repository": "HKati/pulse-release-gates-0.1",
                "git_sha": COMMIT_SHA,
                "run_key": CURRENT_RUN_KEY,
            },
            "evaluator": "llamaguard",
        },
    )
    write_json(
        package_dir / "artifacts" / "external" / "llamaguard_summary.json",
        {
            "schema_version": "llamaguard_summary_v0",
            "summary": {
                "status": "pass",
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "external" / "llamaguard_summary.bundle.json",
        {
            "schema_version": "llamaguard_summary_bundle_v0",
            "bundle": {
                "status": "present",
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "external" / "llamaguard_summary.envelope.json",
        {
            "schema_version": "llamaguard_summary_envelope_v0",
            "envelope": {
                "status": "present",
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "external" / "llamaguard_attestation_verifier_v1.json",
        {
            "schema_version": "llamaguard_attestation_verifier_v1",
            "status": "verified",
            "errors": [],
        },
    )

    write_json(
        package_dir / "artifacts" / "status.json",
        {
            "schema_version": "status_v0",
            "metrics": {
                "git_sha": COMMIT_SHA,
                "run_key": CURRENT_RUN_KEY,
            },
            "gates": {
                "core_required_reference_ok": True,
            },
        },
    )
    write_json(
        package_dir / "artifacts" / "release_decision_v0.json",
        {
            "schema_version": "release_decision_v0",
            "decision": "allow",
            "ok": True,
            "source": "package-completeness-fixture",
        },
    )
    write_json(
        package_dir / "artifacts" / "artifact_provenance_binding_v0.json",
        {
            "schema_version": "artifact_provenance_binding_v0",
            "subject_name": SUBJECT_NAME,
            "subject_sha256": SUBJECT_SHA256,
            "commit_sha": COMMIT_SHA,
        },
    )
    write_json(
        package_dir / "artifacts" / "release_authority_v0.json",
        {
            "schema_version": "release_authority_v0",
            "authority_boundary": {
                "authorizes_release": False,
                "source": "fixture",
            },
            "decision_artifact": "artifacts/release_decision_v0.json",
        },
    )
    write_text(
        package_dir / "artifacts" / "report_card.html",
        "<html><body>release grade package complete</body></html>\n",
    )
    write_json(
        package_dir
        / "artifacts"
        / "recorded_release_candidates"
        / "candidate_0.json",
        {
            "schema_version": "recorded_release_candidate_v0",
            "validation": {
                "status": "passed",
            },
            "authority_boundary": {
                "creates_release_authority": False,
            },
        },
    )
    write_json(
        package_dir / "release-authority-audit-bundle" / "manifest.json",
        {
            "schema_version": "release_authority_audit_bundle_manifest_v0",
            "artifacts": ["artifacts/release_decision_v0.json"],
        },
    )
    write_json(
        package_dir / "artifacts" / "slsa" / "slsa_vsa_trusted_producer_input_packet_v0.json",
        packet_payload(),
    )
    write_json(
        package_dir / "artifacts" / "slsa" / "slsa_vsa_trusted_evidence_producer_report_v0.json",
        report_payload(),
    )

    rebuild_digest_inventory(package_dir)
    return package_dir


def remove_slsa_trusted_producer_artifacts(package_dir: Path) -> None:
    for relative in (
        "artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json",
        "artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json",
    ):
        path = package_dir / relative
        if path.exists():
            path.unlink()

    slsa_dir = package_dir / "artifacts" / "slsa"
    if slsa_dir.exists() and not any(slsa_dir.iterdir()):
        slsa_dir.rmdir()

    rebuild_digest_inventory(package_dir)


def run_tool(
    package_dir: Path,
    *,
    output: Path | None = None,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TOOL),
        "--package-dir",
        str(package_dir),
    ]

    if output is not None:
        command.extend(["--output", str(output)])

    if extra:
        command.extend(extra)

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_report(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def assert_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert report["ok"] is False
    assert any(expected_fragment in error for error in report["errors"]), report["errors"]
    return report


def test_manifest_registers_completeness_checker_exactly_once() -> None:
    entries = [
        line.split("#", 1)[0].strip()
        for line in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
    ]
    entries = [line for line in entries if line]

    assert entries.count(THIS_TEST) == 1


def test_manifest_places_checker_in_release_grade_block() -> None:
    entries = [
        line.split("#", 1)[0].strip()
        for line in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
    ]
    entries = [line for line in entries if line]

    checker_index = entries.index(THIS_TEST)
    after_index = entries.index("tests/test_release_grade_reference_package_verification_wiring_v0.py")
    before_index = entries.index("tests/test_release_grade_reference_qualification_advisory_boundary_v0.py")

    assert after_index < checker_index < before_index


def test_complete_package_passes_and_output_matches_stdout(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    output = tmp_path / "completeness_report.json"

    result = run_tool(package_dir, output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert output.exists()
    assert output.read_text(encoding="utf-8") == result.stdout

    report = parse_report(result)
    assert report["schema_version"] == "release_grade_package_completeness_v1"
    assert report["ok"] is True
    assert report["status"] == "complete"
    assert report["errors"] == []
    assert report["authority_boundary"]["authorizes_release"] is False
    assert report["authority_boundary"]["package_completeness_only"] is True
    assert report["summary"]["checks_failed"] == 0


def test_current_package_contract_without_slsa_artifacts_passes(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    remove_slsa_trusted_producer_artifacts(package_dir)

    result = run_tool(package_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    report = parse_report(result)
    assert report["ok"] is True
    assert report["status"] == "complete"
    assert any(
        check["check_id"] == "slsa_vsa.trusted_producer.current_contract_optional"
        and check["passed"] is True
        for check in report["checks"]
    )


def test_slsa_artifacts_required_when_strict_flag_is_set(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    remove_slsa_trusted_producer_artifacts(package_dir)

    assert_failure(
        run_tool(
            package_dir,
            extra=["--require-slsa-vsa-trusted-producer"],
        ),
        "slsa_vsa.required_file:artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json",
    )


def test_release_decision_stubbed_scaffold_diagnostic_vocabulary_is_allowed(
    tmp_path: Path,
) -> None:
    package_dir = make_complete_package(tmp_path)
    decision_path = package_dir / "artifacts" / "release_decision_v0.json"

    decision = read_json(decision_path)
    decision["decision_basis"] = [
        "no stubbed/scaffold diagnostics detected",
    ]
    write_json(decision_path, decision)
    rebuild_digest_inventory(package_dir)

    result = run_tool(package_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    report = parse_report(result)
    assert report["ok"] is True


def test_missing_required_file_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    (package_dir / "artifacts" / "status.json").unlink()
    rebuild_digest_inventory(package_dir)

    report = assert_failure(run_tool(package_dir), "required_file:artifacts/status.json")

    assert report["status"] == "incomplete"


def test_missing_external_evidence_file_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    (package_dir / "artifacts" / "external" / "llamaguard_summary.json").unlink()
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "required_file:artifacts/external/llamaguard_summary.json")


def test_empty_required_file_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    write_text(package_dir / "artifacts" / "report_card.html", "")
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "non_empty_file:artifacts/report_card.html")


def test_duplicate_json_key_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    write_text(
        package_dir / "artifacts" / "status.json",
        '{"schema_version": "status_v0", "schema_version": "duplicate"}\n',
    )
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "duplicate JSON key")


def test_stub_marker_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    packet = read_json(
        package_dir / "artifacts" / "slsa" / "slsa_vsa_trusted_producer_input_packet_v0.json"
    )
    packet["producer_identity"]["producer_id"] = "replace-me"
    write_json(
        package_dir / "artifacts" / "slsa" / "slsa_vsa_trusted_producer_input_packet_v0.json",
        packet,
    )
    rebuild_digest_inventory(package_dir)

    assert_failure(
        run_tool(package_dir),
        "non_stub_json:artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json",
    )


def test_digest_inventory_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)

    status_path = package_dir / "artifacts" / "status.json"
    status = read_json(status_path)
    status["metrics"]["git_sha"] = "b" * 40
    write_json(status_path, status)

    assert_failure(run_tool(package_dir), "digest_inventory.digest:artifacts/status.json")


def test_slsa_packet_report_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["run_binding"]["current_run_key"] = (
        "GITHUB_RUN_ID=9999999999|GITHUB_RUN_NUMBER=2692|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
    )
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.current_run_key")


def test_slsa_report_producer_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["producer"]["producer_id"] = "wrong-producer"
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.producer_identity")


def test_slsa_run_key_self_inconsistency_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    packet_path = (
        package_dir / "artifacts" / "slsa" / "slsa_vsa_trusted_producer_input_packet_v0.json"
    )
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )

    packet = read_json(packet_path)
    report = read_json(report_path)
    packet["run_binding"]["current_run_number"] = "9999"
    report["run_binding"]["current_run_number"] = "9999"
    write_json(packet_path, packet)
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.packet_run_key_self_consistent")


def test_slsa_artifact_flag_failure_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["artifact_binding"]["subject_digest_matches"] = False
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.artifact_flags")


def test_slsa_report_evidence_time_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["evidence"]["time_verified"] = "2026-07-05T00:00:00Z"
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.freshness")


def test_slsa_report_evidence_policy_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["policy_binding"]["evidence_policy_sha256"] = "d" * 64
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.policy_binding")


def test_slsa_report_evidence_verifier_mismatch_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["verifier_binding"]["evidence_verifier_id"] = "https://pulse.invalid/verifiers/wrong"
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.verifier_binding")


def test_slsa_failed_verification_result_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["evidence"]["verification_result"] = "FAILED"
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.verification_result")


def test_stale_or_rejected_slsa_report_fails_closed(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    report_path = (
        package_dir
        / "artifacts"
        / "slsa"
        / "slsa_vsa_trusted_evidence_producer_report_v0.json"
    )
    report = read_json(report_path)
    report["producer_decision"] = "TRUSTED_EVIDENCE_REJECTED"
    report["ok"] = False
    report["failed_checks"] = ["freshness_epoch_current"]
    report["freshness"]["freshness_result"] = "rejected_stale_vsa"
    report["freshness"]["current_run_binding_ok"] = False
    write_json(report_path, report)
    rebuild_digest_inventory(package_dir)

    assert_failure(run_tool(package_dir), "slsa_vsa.report.accepted")


def test_refuses_status_json_output(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    output = tmp_path / "status.json"

    result = run_tool(package_dir, output=output)

    assert result.returncode == 2
    assert not output.exists()

    report = parse_report(result)
    assert report["ok"] is False
    assert "refusing_to_write_status_json" in report["errors"]


def test_refuses_output_inside_package_dir(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    output = package_dir / "completeness_report.json"

    result = run_tool(package_dir, output=output)

    assert result.returncode == 2
    assert not output.exists()

    report = parse_report(result)
    assert report["ok"] is False
    assert "refusing_to_write_inside_package_dir" in report["errors"]


def test_refuses_symlink_output_targeting_package_file(tmp_path: Path) -> None:
    package_dir = make_complete_package(tmp_path)
    status_path = package_dir / "artifacts" / "status.json"
    status_before = status_path.read_text(encoding="utf-8")
    output = tmp_path / "outside_report_link.json"

    try:
        os.symlink(status_path, output)
    except (OSError, NotImplementedError):
        return

    result = run_tool(package_dir, output=output)

    assert result.returncode == 2
    assert status_path.read_text(encoding="utf-8") == status_before

    report = parse_report(result)
    assert report["ok"] is False
    assert "refusing_to_write_symlink_output" in report["errors"]


def test_tool_does_not_call_release_gate_or_materializer_engines() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = [
        "check_" + "gates.py",
        "policy_to_require_args.py",
        "fold_slsa_vsa_intake_into_status_v0.py",
        "materialize_release_required_from_verifier_v0.py",
    ]

    for marker in forbidden:
        assert marker not in source, marker


def check_check_release_grade_package_complete_v1() -> None:
    assert TOOL.exists()
    assert TOOLS_TESTS_LIST.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_manifest_registers_completeness_checker_exactly_once()
        test_manifest_places_checker_in_release_grade_block()
        test_complete_package_passes_and_output_matches_stdout(tmp_path)
        test_current_package_contract_without_slsa_artifacts_passes(tmp_path)
        test_slsa_artifacts_required_when_strict_flag_is_set(tmp_path)
        test_release_decision_stubbed_scaffold_diagnostic_vocabulary_is_allowed(tmp_path)
        test_missing_required_file_fails_closed(tmp_path)
        test_missing_external_evidence_file_fails_closed(tmp_path)
        test_empty_required_file_fails_closed(tmp_path)
        test_duplicate_json_key_fails_closed(tmp_path)
        test_stub_marker_fails_closed(tmp_path)
        test_digest_inventory_mismatch_fails_closed(tmp_path)
        test_slsa_packet_report_mismatch_fails_closed(tmp_path)
        test_slsa_report_producer_mismatch_fails_closed(tmp_path)
        test_slsa_run_key_self_inconsistency_fails_closed(tmp_path)
        test_slsa_artifact_flag_failure_fails_closed(tmp_path)
        test_slsa_report_evidence_time_mismatch_fails_closed(tmp_path)
        test_slsa_report_evidence_policy_mismatch_fails_closed(tmp_path)
        test_slsa_report_evidence_verifier_mismatch_fails_closed(tmp_path)
        test_slsa_failed_verification_result_fails_closed(tmp_path)
        test_stale_or_rejected_slsa_report_fails_closed(tmp_path)
        test_refuses_status_json_output(tmp_path)
        test_refuses_output_inside_package_dir(tmp_path)
        test_refuses_symlink_output_targeting_package_file(tmp_path)
        test_tool_does_not_call_release_gate_or_materializer_engines()


def test_check_release_grade_package_complete_v1() -> None:
    check_check_release_grade_package_complete_v1()


if __name__ == "__main__":
    check_check_release_grade_package_complete_v1()
    print("OK: check_release_grade_package_complete_v1 smoke passed")
