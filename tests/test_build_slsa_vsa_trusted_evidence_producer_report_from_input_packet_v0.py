#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0.py"

EVIDENCE_SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EVIDENCE_EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

INPUT_PACKET_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
INPUT_PACKET_EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_producer_input_packet_example_v0.json"
INPUT_PACKET_VALIDATOR = ROOT / "tools" / "check_slsa_vsa_trusted_producer_input_packet_v0.py"

REPORT_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_evidence_producer_report_v0.schema.json"
REPORT_VALIDATOR = ROOT / "tools" / "check_slsa_vsa_trusted_evidence_producer_report_v0.py"

SUBJECT_NAME = "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0"
SUBJECT_SHA256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY_ID = "pulse-gate-policy-v0"
POLICY_URI = "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json"
POLICY_SHA256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
VERIFIER_ID = "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0"
VERIFIED_LEVEL = "SLSA_BUILD_LEVEL_3"
TIME_VERIFIED = "2026-07-04T00:00:00Z"

EXPECTED_ARGS = [
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
    "GITHUB_RUN_ID=1234567890|GITHUB_RUN_NUMBER=2692|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_builder(
    *,
    evidence: Path = EVIDENCE_EXAMPLE,
    packet: Path = INPUT_PACKET_EXAMPLE,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        "--evidence-schema",
        str(EVIDENCE_SCHEMA),
        "--evidence",
        str(evidence),
        "--input-packet-schema",
        str(INPUT_PACKET_SCHEMA),
        "--input-packet",
        str(packet),
        "--input-packet-validator",
        str(INPUT_PACKET_VALIDATOR),
        "--report-schema",
        str(REPORT_SCHEMA),
        "--report-validator",
        str(REPORT_VALIDATOR),
    ]
    cmd.extend(EXPECTED_ARGS)

    if extra:
        cmd.extend(extra)

    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def report_validator() -> jsonschema.Draft202012Validator:
    schema = read_json(REPORT_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def assert_report_schema_valid(report: dict[str, Any]) -> None:
    errors = sorted(
        report_validator().iter_errors(report),
        key=lambda error: list(error.path),
    )
    assert not errors, [error.message for error in errors]


def run_existing_report_validator(report_path: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(REPORT_VALIDATOR),
        "--schema",
        str(REPORT_SCHEMA),
        "--report",
        str(report_path),
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
        "GITHUB_RUN_ID=1234567890|GITHUB_RUN_NUMBER=2692|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
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

    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_rejected(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_json_stdout(result)
    assert report["ok"] is False

    if report.get("producer_decision") == "TRUSTED_EVIDENCE_REJECTED":
        assert_report_schema_valid(report)
        errors = report["failed_checks"]
    else:
        errors = report["errors"]

    assert any(expected_fragment in error for error in errors), errors
    return report


def mutated_json(
    *,
    source: Path,
    tmp_path: Path,
    name: str,
    path: list[str | int],
    value: Any,
) -> Path:
    data = read_json(source)
    cursor: Any = data

    for part in path[:-1]:
        cursor = cursor[part]

    cursor[path[-1]] = value

    target = tmp_path / name
    write_json(target, data)
    return target


def deleted_json_field(
    *,
    source: Path,
    tmp_path: Path,
    name: str,
    path: list[str | int],
) -> Path:
    data = read_json(source)
    cursor: Any = data

    for part in path[:-1]:
        cursor = cursor[part]

    del cursor[path[-1]]

    target = tmp_path / name
    write_json(target, data)
    return target


def test_valid_evidence_and_input_packet_build_accepted_report() -> None:
    result = run_builder()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_json_stdout(result)
    assert_report_schema_valid(report)

    assert report["schema_version"] == "slsa_vsa_trusted_evidence_producer_report_v0"
    assert report["report_type"] == "slsa_vsa_trusted_evidence_producer_report"
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_ACCEPTED"
    assert report["ok"] is True
    assert report["failed_checks"] == []
    assert report["recorded_signal_mode"] == "recorded_signal_only"
    assert report["candidate_set"] == "slsa_vsa_recorded_intake_candidate"

    assert report["policy_binding"]["expected_policy_id"] == POLICY_ID
    assert report["policy_binding"]["evidence_policy_id"] == POLICY_ID
    assert report["policy_binding"]["evidence_policy_uri"] == POLICY_URI
    assert report["policy_binding"]["evidence_policy_sha256"] == POLICY_SHA256
    assert report["policy_binding"]["policy_identity_matches"] is True
    assert report["policy_binding"]["policy_digest_matches"] is True

    assert report["freshness"]["freshness_result"] == "fresh_current_run"
    assert report["freshness"]["current_run_binding_ok"] is True


def test_output_report_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "producer_report.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert read_json(output) == parse_json_stdout(result)


def test_accepted_report_passes_existing_report_validator(tmp_path: Path) -> None:
    output = tmp_path / "producer_report.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr

    validator_result = run_existing_report_validator(output)
    assert validator_result.returncode == 0, validator_result.stdout + validator_result.stderr


def test_missing_evidence_returns_deterministic_diagnostic(tmp_path: Path) -> None:
    missing = tmp_path / "missing_vsa.json"

    first = run_builder(evidence=missing)
    second = run_builder(evidence=missing)

    first_report = assert_rejected(first, "evidence_read_error")
    second_report = assert_rejected(second, "evidence_read_error")

    assert first_report == second_report
    assert first_report["exit_kind"] == "build_error"


def test_schema_invalid_evidence_fails_closed(tmp_path: Path) -> None:
    bad_evidence = deleted_json_field(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="missing_policy_id.json",
        path=["vsa", "predicate", "policy", "id"],
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "evidence_schema_valid")

    assert "TRUSTED_EVIDENCE_REJECTED" == report["producer_decision"]
    assert any("evidence_schema_error" in item for item in report["failed_checks"])


def test_wrong_input_packet_identity_fails_closed(tmp_path: Path) -> None:
    bad_packet = mutated_json(
        source=INPUT_PACKET_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_producer_id.json",
        path=["producer_identity", "producer_id"],
        value="wrong-producer",
    )

    report = assert_rejected(run_builder(packet=bad_packet), "input_packet_validator")

    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"


def test_wrong_evidence_policy_identity_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_policy_id.json",
        path=["vsa", "predicate", "policy", "id"],
        value="wrong-policy",
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "policy_identity_matches")

    assert report["policy_binding"]["evidence_policy_id"] == "wrong-policy"
    assert report["policy_binding"]["expected_policy_id"] == POLICY_ID
    assert report["policy_binding"]["policy_identity_matches"] is False


def test_wrong_evidence_policy_digest_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_policy_digest.json",
        path=["vsa", "predicate", "policy", "digest", "sha256"],
        value="c" * 64,
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "policy_digest_matches")

    assert report["policy_binding"]["evidence_policy_sha256"] == "c" * 64
    assert report["policy_binding"]["expected_policy_sha256"] == POLICY_SHA256
    assert report["policy_binding"]["policy_digest_matches"] is False


def test_wrong_verifier_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_verifier.json",
        path=["vsa", "predicate", "verifier", "id"],
        value="https://example.invalid/verifiers/wrong",
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "verifier_trusted")

    assert report["verifier_binding"]["verifier_trusted"] is False


def test_wrong_verified_level_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_verified_level.json",
        path=["vsa", "predicate", "verifiedLevels"],
        value=["SLSA_BUILD_LEVEL_1"],
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "verified_level_ok")

    assert report["evidence"]["verified_level_ok"] is False


def test_wrong_time_verified_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_time_verified.json",
        path=["vsa", "predicate", "timeVerified"],
        value="2026-07-05T00:00:00Z",
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "time_verified_current_run_match")

    assert report["freshness"]["freshness_result"] == "rejected_time_verified_current_run_mismatch"


def test_non_current_freshness_epoch_fails_closed(tmp_path: Path) -> None:
    bad_packet = mutated_json(
        source=INPUT_PACKET_EXAMPLE,
        tmp_path=tmp_path,
        name="previous_run_freshness_epoch.json",
        path=["freshness", "freshness_epoch"],
        value="previous_run",
    )

    report = assert_rejected(run_builder(packet=bad_packet), "freshness_epoch_current")

    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"
    assert report["ok"] is False
    assert "freshness_epoch_current" in report["failed_checks"]
    assert report["freshness"]["freshness_result"] == "rejected_stale_vsa"
    assert report["freshness"]["stale_vsa_evidence"] is True
    assert report["freshness"]["current_run_binding_ok"] is False


def test_wrong_artifact_digest_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_artifact_digest.json",
        path=["vsa", "subject", 0, "digest", "sha256"],
        value="d" * 64,
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "artifact_digest_matches")

    assert report["artifact_binding"]["artifact_digest_matches"] is False
    assert report["freshness"]["freshness_result"] == "rejected_previous_run_artifact"


def test_pulse_signal_mismatch_fails_closed(tmp_path: Path) -> None:
    bad_evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="pulse_signal_mismatch.json",
        path=["pulse_signals", "slsa_vsa_policy_digest_matches"],
        value=False,
    )

    report = assert_rejected(run_builder(evidence=bad_evidence), "pulse_signals_consistent")

    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"


def test_status_output_is_refused(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    result = run_builder(extra=["--output", str(status_path)])

    assert result.returncode == 2, result.stdout + result.stderr
    assert not status_path.exists()

    diagnostic = parse_json_stdout(result)
    assert diagnostic["ok"] is False
    assert "refusing_to_write_status_json" in diagnostic["errors"]


def test_tool_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"

    assert forbidden not in source


def test_tool_does_not_write_status_gates_or_activate_release_sets() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = [
        "status_" + "gates",
        "release_" + "required",
        "release_" + "blocking",
        "prod_" + "required",
        "stage_" + "required",
        "gate_" + "materialization",
    ]

    for marker in forbidden:
        assert marker not in source, marker


def check_build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0() -> None:
    assert TOOL.exists()
    assert EVIDENCE_SCHEMA.exists()
    assert EVIDENCE_EXAMPLE.exists()
    assert INPUT_PACKET_SCHEMA.exists()
    assert INPUT_PACKET_EXAMPLE.exists()
    assert INPUT_PACKET_VALIDATOR.exists()
    assert REPORT_SCHEMA.exists()
    assert REPORT_VALIDATOR.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_valid_evidence_and_input_packet_build_accepted_report()
        test_output_report_matches_stdout(tmp_path)
        test_accepted_report_passes_existing_report_validator(tmp_path)
        test_missing_evidence_returns_deterministic_diagnostic(tmp_path)
        test_schema_invalid_evidence_fails_closed(tmp_path)
        test_wrong_input_packet_identity_fails_closed(tmp_path)
        test_wrong_evidence_policy_identity_fails_closed(tmp_path)
        test_wrong_evidence_policy_digest_fails_closed(tmp_path)
        test_wrong_verifier_fails_closed(tmp_path)
        test_wrong_verified_level_fails_closed(tmp_path)
        test_wrong_time_verified_fails_closed(tmp_path)
        test_non_current_freshness_epoch_fails_closed(tmp_path)
        test_wrong_artifact_digest_fails_closed(tmp_path)
        test_pulse_signal_mismatch_fails_closed(tmp_path)
        test_status_output_is_refused(tmp_path)
        test_tool_does_not_call_gate_checker()
        test_tool_does_not_write_status_gates_or_activate_release_sets()


def test_build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0() -> None:
    check_build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0()


if __name__ == "__main__":
    check_build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0()
    print("OK: build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0 smoke passed")
