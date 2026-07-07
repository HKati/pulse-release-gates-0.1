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

TOOL = ROOT / "tools" / "build_slsa_vsa_trusted_evidence_producer_report_v0.py"
CHECKER = ROOT / "tools" / "check_slsa_vsa_trusted_evidence_producer_report_v0.py"
REPORT_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_evidence_producer_report_v0.schema.json"
EVIDENCE_EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

SUBJECT_NAME = "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0"
SUBJECT_SHA256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
POLICY_URI = "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json"
POLICY_SHA256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
VERIFIER_ID = "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0"
VERIFIED_LEVEL = "SLSA_BUILD_LEVEL_3"

BUILDER_ARGS = {
    "--created-utc": "2026-07-07T00:00:00Z",
    "--producer-id": "pulse_slsa_vsa_trusted_evidence_producer_v0",
    "--producer-name": "PULSE SLSA VSA trusted evidence producer",
    "--producer-version": "0.1.0",
    "--producer-source": "github-actions",
    "--ci-workflow-or-job-identity": "PULSE CI / SLSA VSA trusted evidence producer",
    "--current-run-id": "1234567890",
    "--current-run-number": "2692",
    "--current-run-attempt": "1",
    "--workflow-name": "PULSE CI",
    "--job-name": "slsa-vsa-trusted-evidence-producer",
    "--commit-sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--release-candidate-id": "pulse-release-gates-0.1-candidate-v0",
    "--artifact-subject-name": SUBJECT_NAME,
    "--artifact-sha256": SUBJECT_SHA256,
    "--artifact-resource-uri": SUBJECT_NAME,
    "--policy-id": "pulse-gate-policy-v0",
    "--policy-uri": POLICY_URI,
    "--policy-sha256": POLICY_SHA256,
    "--verifier-id": VERIFIER_ID,
    "--expected-verified-level": VERIFIED_LEVEL,
    "--expect-time-verified": "2026-07-04T00:00:00Z",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def expected_current_run_key() -> str:
    return (
        "GITHUB_RUN_ID=1234567890"
        "|GITHUB_RUN_NUMBER=2692"
        "|GITHUB_RUN_ATTEMPT=1"
        "|GITHUB_WORKFLOW=PULSE CI"
    )


def build_args(
    evidence: Path = EVIDENCE_EXAMPLE,
    overrides: dict[str, str | None] | None = None,
) -> list[str]:
    values = dict(BUILDER_ARGS)
    if overrides:
        values.update(overrides)

    args = [
        sys.executable,
        str(TOOL),
        "--evidence",
        str(evidence),
    ]

    for key in sorted(values):
        value = values[key]
        if value is not None:
            args.extend([key, value])

    return args


def run_builder(
    evidence: Path = EVIDENCE_EXAMPLE,
    overrides: dict[str, str | None] | None = None,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = build_args(evidence=evidence, overrides=overrides)
    if extra:
        args.extend(extra)

    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def checker_args(report: Path) -> list[str]:
    return [
        sys.executable,
        str(CHECKER),
        "--schema",
        str(REPORT_SCHEMA),
        "--report",
        str(report),
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
        expected_current_run_key(),
        "--expect-commit-sha",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "--expect-release-candidate-id",
        "pulse-release-gates-0.1-candidate-v0",
        "--expect-artifact-subject-name",
        SUBJECT_NAME,
        "--expect-artifact-sha256",
        SUBJECT_SHA256,
        "--expect-policy-id",
        "pulse-gate-policy-v0",
        "--expect-policy-sha256",
        POLICY_SHA256,
        "--expect-verifier-id",
        VERIFIER_ID,
        "--expect-verified-level",
        VERIFIED_LEVEL,
        "--expect-candidate-set",
        "slsa_vsa_recorded_intake_candidate",
    ]


def run_checker(report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        checker_args(report),
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_report(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def report_schema_validator() -> jsonschema.Draft202012Validator:
    schema = read_json(REPORT_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def assert_report_schema_valid(report: dict[str, Any]) -> None:
    validator = report_schema_validator()
    errors = sorted(
        validator.iter_errors(report),
        key=lambda error: list(error.path),
    )
    assert not errors, [error.message for error in errors]


def assert_rejected(
    result: subprocess.CompletedProcess[str],
    expected_check: str,
) -> dict[str, Any]:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert_report_schema_valid(report)

    assert report["ok"] is False
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"
    assert expected_check in report["failed_checks"], report["failed_checks"]
    assert report["failed_checks"]

    return report


def mutated_evidence(tmp_dir: Path, name: str, patch: dict[str, Any]) -> Path:
    evidence = read_json(EVIDENCE_EXAMPLE)

    for dotted_path, value in patch.items():
        cursor: Any = evidence
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            cursor = cursor[part]
        cursor[parts[-1]] = value

    path = tmp_dir / name
    write_json(path, evidence)
    return path


def check_valid_evidence_builds_accepted_producer_report() -> None:
    result = run_builder()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert_report_schema_valid(report)

    assert report["schema_version"] == "slsa_vsa_trusted_evidence_producer_report_v0"
    assert report["report_type"] == "slsa_vsa_trusted_evidence_producer_report"
    assert report["ok"] is True
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_ACCEPTED"
    assert report["failed_checks"] == []
    assert report["candidate_set"] == "slsa_vsa_recorded_intake_candidate"
    assert report["recorded_signal_mode"] == "recorded_signal_only"
    assert report["run_binding"]["current_run_key"] == expected_current_run_key()
    assert report["freshness"]["freshness_result"] == "fresh_current_run"


def check_accepted_report_passes_report_validator(tmp_dir: Path) -> None:
    output = tmp_dir / "producer_report.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()

    checker_result = run_checker(output)

    assert checker_result.returncode == 0, checker_result.stdout + checker_result.stderr


def check_output_report_matches_stdout(tmp_dir: Path) -> None:
    output = tmp_dir / "producer_report.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert read_json(output) == parse_report(result)


def check_missing_evidence_returns_deterministic_rejected_report(tmp_dir: Path) -> None:
    missing = tmp_dir / "missing_vsa.json"

    first = run_builder(evidence=missing)
    second = run_builder(evidence=missing)

    first_report = assert_rejected(first, "evidence_readable")
    second_report = assert_rejected(second, "evidence_readable")

    assert first_report == second_report
    assert first_report["freshness"]["freshness_result"] == "rejected_missing_vsa_evidence"
    assert first_report["evidence"]["evidence_path"] is None
    assert first_report["evidence"]["evidence_sha256"] is None


def check_wrong_artifact_digest_rejects() -> None:
    report = assert_rejected(
        run_builder(overrides={"--artifact-sha256": "d" * 64}),
        "subject_sha256_matches",
    )

    assert "artifact_digest_matches" in report["failed_checks"]


def check_wrong_artifact_subject_rejects() -> None:
    assert_rejected(
        run_builder(overrides={"--artifact-subject-name": "git+https://example.invalid/wrong@refs/tags/v0"}),
        "subject_name_matches",
    )


def check_wrong_resource_uri_rejects() -> None:
    assert_rejected(
        run_builder(overrides={"--artifact-resource-uri": "git+https://example.invalid/wrong@refs/tags/v0"}),
        "resource_uri_matches",
    )


def check_wrong_policy_digest_rejects() -> None:
    assert_rejected(
        run_builder(overrides={"--policy-sha256": "e" * 64}),
        "policy_digest_matches",
    )


def check_wrong_verifier_rejects() -> None:
    assert_rejected(
        run_builder(overrides={"--verifier-id": "https://example.invalid/verifiers/wrong"}),
        "verifier_id_matches",
    )


def check_wrong_verified_level_rejects() -> None:
    assert_rejected(
        run_builder(overrides={"--expected-verified-level": "SLSA_BUILD_LEVEL_4"}),
        "verified_level_ok",
    )


def check_failed_verification_result_rejects(tmp_dir: Path) -> None:
    failed = mutated_evidence(
        tmp_dir,
        "failed_vsa.json",
        {
            "vsa.predicate.verificationResult": "FAILED",
        },
    )

    assert_rejected(run_builder(evidence=failed), "verification_result_passed")


def check_time_verified_current_run_mismatch_rejects() -> None:
    report = assert_rejected(
        run_builder(overrides={"--expect-time-verified": "2026-07-05T00:00:00Z"}),
        "time_verified_current_run_match",
    )

    assert report["freshness"]["freshness_result"] == "rejected_time_verified_current_run_mismatch"


def check_recorded_pulse_signal_mismatch_rejects(tmp_dir: Path) -> None:
    mismatch = mutated_evidence(
        tmp_dir,
        "signal_mismatch.json",
        {
            "pulse_signals.slsa_vsa_policy_digest_matches": False,
        },
    )

    assert_rejected(run_builder(evidence=mismatch), "pulse_signals_consistent")


def check_status_output_is_refused(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status.json"
    result = run_builder(extra=["--output", str(status_path)])

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert not status_path.exists()

    report = parse_report(result)
    assert_report_schema_valid(report)
    assert report["ok"] is False
    assert report["producer_decision"] == "TRUSTED_EVIDENCE_REJECTED"
    assert "refusing_to_write_status_json" in report["failed_checks"]


def check_tool_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"

    assert forbidden not in source


def check_tool_does_not_write_status_gates_or_activate_release_sets() -> None:
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


def check_build_slsa_vsa_trusted_evidence_producer_report_v0() -> None:
    assert TOOL.exists()
    assert CHECKER.exists()
    assert REPORT_SCHEMA.exists()
    assert EVIDENCE_EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)

        check_valid_evidence_builds_accepted_producer_report()
        check_accepted_report_passes_report_validator(tmp_dir)
        check_output_report_matches_stdout(tmp_dir)
        check_missing_evidence_returns_deterministic_rejected_report(tmp_dir)
        check_wrong_artifact_digest_rejects()
        check_wrong_artifact_subject_rejects()
        check_wrong_resource_uri_rejects()
        check_wrong_policy_digest_rejects()
        check_wrong_verifier_rejects()
        check_wrong_verified_level_rejects()
        check_failed_verification_result_rejects(tmp_dir)
        check_time_verified_current_run_mismatch_rejects()
        check_recorded_pulse_signal_mismatch_rejects(tmp_dir)
        check_status_output_is_refused(tmp_dir)
        check_tool_does_not_call_gate_checker()
        check_tool_does_not_write_status_gates_or_activate_release_sets()


def test_build_slsa_vsa_trusted_evidence_producer_report_v0() -> None:
    check_build_slsa_vsa_trusted_evidence_producer_report_v0()


if __name__ == "__main__":
    check_build_slsa_vsa_trusted_evidence_producer_report_v0()
    print("OK: build_slsa_vsa_trusted_evidence_producer_report_v0 smoke passed")
