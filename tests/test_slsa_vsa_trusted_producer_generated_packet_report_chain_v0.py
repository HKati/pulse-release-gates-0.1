#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PACKET_BUILDER = ROOT / "tools" / "build_slsa_vsa_trusted_producer_input_packet_v0.py"
REPORT_BUILDER = ROOT / "tools" / "build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0.py"

INPUT_PACKET_CHECKER = ROOT / "tools" / "check_slsa_vsa_trusted_producer_input_packet_v0.py"
REPORT_CHECKER = ROOT / "tools" / "check_slsa_vsa_trusted_evidence_producer_report_v0.py"

EVIDENCE_SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EVIDENCE_EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

INPUT_PACKET_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
REPORT_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_evidence_producer_report_v0.schema.json"

SUBJECT_NAME = "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0"
SUBJECT_SHA256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY_ID = "pulse-gate-policy-v0"
POLICY_URI = "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json"
POLICY_SHA256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
VERIFIER_ID = "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0"
VERIFIED_LEVEL = "SLSA_BUILD_LEVEL_3"
TIME_VERIFIED = "2026-07-04T00:00:00Z"

EXPECTED_CURRENT_RUN_KEY = (
    "GITHUB_RUN_ID=1234567890"
    "|GITHUB_RUN_NUMBER=2692"
    "|GITHUB_RUN_ATTEMPT=1"
    "|GITHUB_WORKFLOW=PULSE CI"
)

PACKET_BUILDER_ARGS = [
    "--schema",
    str(INPUT_PACKET_SCHEMA),
    "--created-utc",
    "2026-07-07T00:00:00Z",
    "--producer-id",
    "pulse_slsa_vsa_trusted_evidence_producer_v0",
    "--producer-name",
    "PULSE SLSA VSA trusted evidence producer",
    "--producer-version",
    "0.1.0",
    "--producer-source",
    "github-actions",
    "--ci-workflow-or-job-identity",
    "PULSE CI / SLSA VSA trusted evidence producer",
    "--current-run-id",
    "1234567890",
    "--current-run-number",
    "2692",
    "--current-run-attempt",
    "1",
    "--workflow-name",
    "PULSE CI",
    "--job-name",
    "slsa-vsa-trusted-evidence-producer",
    "--commit-sha",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--release-candidate-id",
    "pulse-release-gates-0.1-candidate-v0",
    "--artifact-subject-name",
    SUBJECT_NAME,
    "--artifact-sha256",
    SUBJECT_SHA256,
    "--artifact-resource-uri",
    SUBJECT_NAME,
    "--policy-id",
    POLICY_ID,
    "--policy-uri",
    POLICY_URI,
    "--policy-sha256",
    POLICY_SHA256,
    "--verifier-id",
    VERIFIER_ID,
    "--verified-level",
    VERIFIED_LEVEL,
    "--time-verified",
    TIME_VERIFIED,
]

PACKET_EXPECTED_ARGS = [
    "--expect-producer-id",
    "pulse_slsa_vsa_trusted_evidence_producer_v0",
    "--expect-producer-name",
    "PULSE SLSA VSA trusted evidence producer",
    "--expect-producer-version",
    "0.1.0",
    "--expect-producer-source",
    "github-actions",
    "--expect-ci-workflow-or-job-identity",
    "PULSE CI / SLSA VSA trusted evidence producer",
    "--expect-current-run-id",
    "1234567890",
    "--expect-current-run-key",
    EXPECTED_CURRENT_RUN_KEY,
    "--expect-commit-sha",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-release-candidate-id",
    "pulse-release-gates-0.1-candidate-v0",
    "--expect-artifact-subject-name",
    SUBJECT_NAME,
    "--expect-artifact-sha256",
    SUBJECT_SHA256,
    "--expect-artifact-resource-uri",
    SUBJECT_NAME,
    "--expect-policy-id",
    POLICY_ID,
    "--expect-policy-uri",
    POLICY_URI,
    "--expect-policy-sha256",
    POLICY_SHA256,
    "--expect-verifier-id",
    VERIFIER_ID,
    "--expect-verified-level",
    VERIFIED_LEVEL,
    "--expect-time-verified",
    TIME_VERIFIED,
    "--expect-candidate-set",
    "slsa_vsa_recorded_intake_candidate",
]

REPORT_EXPECTED_ARGS = [
    "--expect-producer-id",
    "pulse_slsa_vsa_trusted_evidence_producer_v0",
    "--expect-producer-name",
    "PULSE SLSA VSA trusted evidence producer",
    "--expect-producer-version",
    "0.1.0",
    "--expect-producer-source",
    "github-actions",
    "--expect-ci-workflow-or-job-identity",
    "PULSE CI / SLSA VSA trusted evidence producer",
    "--expect-current-run-id",
    "1234567890",
    "--expect-current-run-key",
    EXPECTED_CURRENT_RUN_KEY,
    "--expect-commit-sha",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-release-candidate-id",
    "pulse-release-gates-0.1-candidate-v0",
    "--expect-artifact-subject-name",
    SUBJECT_NAME,
    "--expect-artifact-sha256",
    SUBJECT_SHA256,
    "--expect-policy-id",
    POLICY_ID,
    "--expect-policy-sha256",
    POLICY_SHA256,
    "--expect-verifier-id",
    VERIFIER_ID,
    "--expect-verified-level",
    VERIFIED_LEVEL,
    "--expect-candidate-set",
    "slsa_vsa_recorded_intake_candidate",
]


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def run_packet_builder(
    *,
    output: Path | None = None,
    freshness_epoch: str = "current_run",
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PACKET_BUILDER),
        *PACKET_BUILDER_ARGS,
        "--freshness-epoch",
        freshness_epoch,
    ]

    if output is not None:
        command.extend(["--output", str(output)])

    return run_command(command)


def run_packet_checker(packet_path: Path) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(INPUT_PACKET_CHECKER),
            "--schema",
            str(INPUT_PACKET_SCHEMA),
            "--packet",
            str(packet_path),
            *PACKET_EXPECTED_ARGS,
        ]
    )


def run_report_builder(
    *,
    packet_path: Path,
    output: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(REPORT_BUILDER),
        "--evidence-schema",
        str(EVIDENCE_SCHEMA),
        "--evidence",
        str(EVIDENCE_EXAMPLE),
        "--input-packet-schema",
        str(INPUT_PACKET_SCHEMA),
        "--input-packet",
        str(packet_path),
        "--input-packet-validator",
        str(INPUT_PACKET_CHECKER),
        "--report-schema",
        str(REPORT_SCHEMA),
        "--report-validator",
        str(REPORT_CHECKER),
        *PACKET_EXPECTED_ARGS,
    ]

    if output is not None:
        command.extend(["--output", str(output)])

    return run_command(command)


def run_report_checker(report_path: Path) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(REPORT_CHECKER),
            "--schema",
            str(REPORT_SCHEMA),
            "--report",
            str(report_path),
            *REPORT_EXPECTED_ARGS,
        ]
    )


def build_packet_to_file(tmp_path: Path, name: str = "generated_packet.json") -> Path:
    packet_path = tmp_path / name
    result = run_packet_builder(output=packet_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert packet_path.exists()
    assert packet_path.read_text(encoding="utf-8") == result.stdout

    return packet_path


def test_generated_input_packet_passes_existing_packet_checker(tmp_path: Path) -> None:
    packet_path = build_packet_to_file(tmp_path)
    packet = read_json(packet_path)

    assert packet["schema_version"] == "slsa_vsa_trusted_producer_input_packet_v0"
    assert packet["packet_type"] == "slsa_vsa_trusted_producer_input_packet"
    assert packet["recorded_signal_mode"] == "recorded_signal_only"
    assert packet["candidate_set"] == "slsa_vsa_recorded_intake_candidate"
    assert packet["run_binding"]["current_run_key"] == EXPECTED_CURRENT_RUN_KEY
    assert packet["artifact_binding"]["subject_sha256"] == SUBJECT_SHA256
    assert packet["artifact_binding"]["artifact_digest_sha256"] == SUBJECT_SHA256

    checker_result = run_packet_checker(packet_path)
    assert checker_result.returncode == 0, checker_result.stdout + checker_result.stderr

    checker_report = parse_stdout_json(checker_result)
    assert checker_report["ok"] is True
    assert checker_report["schema_valid"] is True
    assert checker_report["errors"] == []
    assert all(checker_report["checks"].values())


def test_generated_input_packet_builds_accepted_producer_report(tmp_path: Path) -> None:
    packet_path = build_packet_to_file(tmp_path)
    report_path = tmp_path / "trusted_producer_report.json"

    result = run_report_builder(packet_path=packet_path, output=report_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == result.stdout

    report = parse_stdout_json(result)
    assert report["schema_version"] == "slsa_vsa_trusted_evidence_producer_report_v0"
    assert report["report_type"] == "slsa_vsa_trusted_evidence_producer_report"
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_ACCEPTED"
    assert report["ok"] is True
    assert report["failed_checks"] == []
    assert report["recorded_signal_mode"] == "recorded_signal_only"
    assert report["candidate_set"] == "slsa_vsa_recorded_intake_candidate"

    assert report["run_binding"]["current_run_key"] == EXPECTED_CURRENT_RUN_KEY
    assert report["artifact_binding"]["subject_sha256"] == SUBJECT_SHA256
    assert report["artifact_binding"]["artifact_digest_sha256"] == SUBJECT_SHA256
    assert report["artifact_binding"]["subject_digest_matches"] is True
    assert report["artifact_binding"]["artifact_digest_matches"] is True

    assert report["policy_binding"]["expected_policy_id"] == POLICY_ID
    assert report["policy_binding"]["evidence_policy_id"] == POLICY_ID
    assert report["policy_binding"]["evidence_policy_uri"] == POLICY_URI
    assert report["policy_binding"]["evidence_policy_sha256"] == POLICY_SHA256
    assert report["policy_binding"]["policy_identity_matches"] is True
    assert report["policy_binding"]["policy_digest_matches"] is True

    assert report["verifier_binding"]["expected_verifier_id"] == VERIFIER_ID
    assert report["verifier_binding"]["evidence_verifier_id"] == VERIFIER_ID
    assert report["verifier_binding"]["verifier_trusted"] is True

    assert report["evidence"]["expected_verified_level"] == VERIFIED_LEVEL
    assert report["evidence"]["verified_level_ok"] is True

    assert report["freshness"]["freshness_result"] == "fresh_current_run"
    assert report["freshness"]["current_run_binding_ok"] is True
    assert report["freshness"]["time_verified_current_run_match"] is True

    validator_result = run_report_checker(report_path)
    assert validator_result.returncode == 0, validator_result.stdout + validator_result.stderr

    validator_report = parse_stdout_json(validator_result)
    assert validator_report["ok"] is True
    assert validator_report["errors"] == []
    assert all(validator_report["checks"].values())


def test_generated_packet_to_report_chain_is_deterministic(tmp_path: Path) -> None:
    first_packet = tmp_path / "first_packet.json"
    second_packet = tmp_path / "second_packet.json"

    first_packet_result = run_packet_builder(output=first_packet)
    second_packet_result = run_packet_builder(output=second_packet)

    assert first_packet_result.returncode == 0, first_packet_result.stdout + first_packet_result.stderr
    assert second_packet_result.returncode == 0, second_packet_result.stdout + second_packet_result.stderr
    assert first_packet_result.stdout == second_packet_result.stdout
    assert first_packet.read_text(encoding="utf-8") == second_packet.read_text(encoding="utf-8")

    first_report = tmp_path / "first_report.json"
    second_report = tmp_path / "second_report.json"

    first_report_result = run_report_builder(packet_path=first_packet, output=first_report)
    second_report_result = run_report_builder(packet_path=second_packet, output=second_report)

    assert first_report_result.returncode == 0, first_report_result.stdout + first_report_result.stderr
    assert second_report_result.returncode == 0, second_report_result.stdout + second_report_result.stderr
    assert first_report_result.stdout == second_report_result.stdout
    assert first_report.read_text(encoding="utf-8") == second_report.read_text(encoding="utf-8")


def test_generated_non_current_freshness_packet_builds_rejected_report(tmp_path: Path) -> None:
    stale_packet = tmp_path / "stale_packet.json"
    packet_result = run_packet_builder(output=stale_packet, freshness_epoch="previous_run")

    assert packet_result.returncode == 0, packet_result.stdout + packet_result.stderr
    assert stale_packet.exists()

    report_result = run_report_builder(packet_path=stale_packet)

    assert report_result.returncode != 0, report_result.stdout + report_result.stderr
    assert "Traceback" not in report_result.stderr

    report = parse_stdout_json(report_result)
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"
    assert report["ok"] is False
    assert "freshness_epoch_current" in report["failed_checks"]
    assert report["freshness"]["freshness_result"] == "rejected_stale_vsa"
    assert report["freshness"]["stale_vsa_evidence"] is True
    assert report["freshness"]["current_run_binding_ok"] is False


def test_generated_packet_report_chain_does_not_call_release_gate_authority() -> None:
    checked_sources = [
        PACKET_BUILDER.read_text(encoding="utf-8"),
        REPORT_BUILDER.read_text(encoding="utf-8"),
        Path(__file__).read_text(encoding="utf-8"),
    ]

    forbidden = [
        "status_" + "gates",
        "release_" + "required",
        "release_" + "blocking",
        "prod_" + "required",
        "stage_" + "required",
        "gate_" + "materialization",
        "materialize_" + "release_" + "required",
    ]

    for source in checked_sources:
        assert ("check_" + "gates") not in source
        for marker in forbidden:
            assert marker not in source, marker


def check_slsa_vsa_trusted_producer_generated_packet_report_chain_v0() -> None:
    assert PACKET_BUILDER.exists()
    assert REPORT_BUILDER.exists()
    assert INPUT_PACKET_CHECKER.exists()
    assert REPORT_CHECKER.exists()
    assert EVIDENCE_SCHEMA.exists()
    assert EVIDENCE_EXAMPLE.exists()
    assert INPUT_PACKET_SCHEMA.exists()
    assert REPORT_SCHEMA.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_generated_input_packet_passes_existing_packet_checker(tmp_path)
        test_generated_input_packet_builds_accepted_producer_report(tmp_path)
        test_generated_packet_to_report_chain_is_deterministic(tmp_path)
        test_generated_non_current_freshness_packet_builds_rejected_report(tmp_path)
        test_generated_packet_report_chain_does_not_call_release_gate_authority()


def test_slsa_vsa_trusted_producer_generated_packet_report_chain_v0() -> None:
    check_slsa_vsa_trusted_producer_generated_packet_report_chain_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_producer_generated_packet_report_chain_v0()
    print("OK: slsa_vsa_trusted_producer_generated_packet_report_chain_v0 smoke passed")
