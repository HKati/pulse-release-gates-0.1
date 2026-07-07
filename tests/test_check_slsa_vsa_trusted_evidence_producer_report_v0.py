#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "check_slsa_vsa_trusted_evidence_producer_report_v0.py"
SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_evidence_producer_report_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_evidence_producer_report_example_v0.json"

EXPECTED_ARGS = [
    "--expect-producer-id",
    "pulse_slsa_vsa_trusted_evidence_producer_v0",
    "--expect-current-run-id",
    "1234567890",
    "--expect-current-run-key",
    "GITHUB_RUN_ID=1234567890|GITHUB_RUN_NUMBER=2692|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
    "--expect-commit-sha",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-release-candidate-id",
    "pulse-release-gates-0.1-candidate-v0",
    "--expect-artifact-subject-name",
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/heads/main",
    "--expect-artifact-sha256",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "--expect-policy-id",
    "pulse-gate-policy-v0",
    "--expect-policy-sha256",
    "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "--expect-verifier-id",
    "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0",
    "--expect-candidate-set",
    "slsa_vsa_recorded_intake_candidate",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def run_tool(
    report_path: Path = EXAMPLE,
    extra: list[str] | None = None,
    omit_expected: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(SCHEMA),
        "--report",
        str(report_path),
    ]

    if not omit_expected:
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


def parse_diagnostic(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def assert_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert any(expected_fragment in error for error in diagnostic["errors"]), diagnostic["errors"]
    return diagnostic


def test_valid_example_passes() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["tool"] == "check_slsa_vsa_trusted_evidence_producer_report_v0"
    assert diagnostic["ok"] is True
    assert diagnostic["schema_valid"] is True
    assert diagnostic["errors"] == []
    assert all(diagnostic["checks"].values())


def test_output_report_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "diagnostic.json"
    result = run_tool(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert read_json(output) == parse_diagnostic(result)


def test_rejected_report_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["ok"] = False
    report["producer_decision"] = "TRUSTED_EVIDENCE_REJECTED"
    report["failed_checks"] = ["stale_vsa_evidence"]
    report["freshness"]["freshness_result"] = "rejected_stale_vsa"
    report["freshness"]["stale_vsa_evidence"] = True

    report_path = tmp_path / "rejected_report.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "check_failed: producer_report_ok")


def test_wrong_policy_digest_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["policy_binding"]["evidence_policy_sha256"] = "e" * 64

    report_path = tmp_path / "wrong_policy_digest.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "check_failed: policy_sha256_matches")


def test_policy_digest_mismatch_flag_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["policy_binding"]["policy_digest_matches"] = False

    report_path = tmp_path / "policy_digest_mismatch.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "check_failed: policy_digest_matches")


def test_wrong_evidence_policy_id_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["policy_binding"]["evidence_policy_id"] = "wrong-policy-id"

    report_path = tmp_path / "wrong_policy_id.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "check_failed: policy_id_matches")


def test_stale_vsa_evidence_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["freshness"]["freshness_result"] = "rejected_stale_vsa"
    report["freshness"]["stale_vsa_evidence"] = True

    report_path = tmp_path / "stale_vsa.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "schema_error")


def test_previous_run_artifact_reuse_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["freshness"]["freshness_result"] = "rejected_previous_run_artifact"
    report["freshness"]["previous_run_artifact_reuse"] = True

    report_path = tmp_path / "previous_run_artifact.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "schema_error")


def test_time_verified_current_run_mismatch_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["freshness"]["freshness_result"] = "rejected_time_verified_current_run_mismatch"
    report["freshness"]["time_verified_current_run_match"] = False

    report_path = tmp_path / "time_verified_mismatch.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "schema_error")


def test_missing_evidence_digest_rejected_report_fails_but_does_not_need_fake_digest(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["ok"] = False
    report["producer_decision"] = "TRUSTED_EVIDENCE_REJECTED"
    report["failed_checks"] = ["missing_vsa_evidence"]
    report["evidence"]["evidence_path"] = None
    report["evidence"]["evidence_sha256"] = None
    report["evidence"]["evidence_schema_version"] = None
    report["evidence"]["evidence_type"] = None
    report["evidence"]["time_verified"] = None
    report["evidence"]["verification_result"] = None
    report["evidence"]["evidence_verified_levels"] = None
    report["evidence"]["verified_level_ok"] = False
    report["freshness"]["freshness_result"] = "rejected_missing_vsa_evidence"
    report["freshness"]["current_run_binding_ok"] = False

    report_path = tmp_path / "missing_evidence.json"
    write_json(report_path, report)

    diagnostic = assert_failure(run_tool(report_path), "check_failed: producer_report_ok")
    assert diagnostic["schema_valid"] is True


def test_schema_invalid_report_fails_closed(tmp_path: Path) -> None:
    report = read_json(EXAMPLE)
    report["created_utc"] = "unknown"

    report_path = tmp_path / "schema_invalid.json"
    write_json(report_path, report)

    assert_failure(run_tool(report_path), "schema_error")


def test_expectation_mismatch_fails_closed() -> None:
    result = run_tool(extra=["--expect-policy-sha256", "e" * 64])

    assert result.returncode != 0
    assert "Traceback" not in result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert "check_failed: policy_sha256_matches" in diagnostic["errors"]


def test_missing_report_file_returns_read_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    result = run_tool(report_path=missing)

    assert result.returncode == 2
    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert any("read_error:" in error for error in diagnostic["errors"])


def test_refuses_to_write_status_json(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    result = run_tool(extra=["--output", str(status_path)])

    assert result.returncode == 2
    assert not status_path.exists()

    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert "refusing_to_write_status_json" in diagnostic["errors"]


def test_tool_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"

    assert forbidden not in source


def test_tool_does_not_write_status_gates() -> None:
    source = TOOL.read_text(encoding="utf-8")

    assert "status_gates" not in source
    assert "release_required" not in source
    assert "gate_materialization" not in source


def check_check_slsa_vsa_trusted_evidence_producer_report_v0() -> None:
    assert TOOL.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_valid_example_passes()
        test_output_report_matches_stdout(tmp_path)
        test_rejected_report_fails_closed(tmp_path)
        test_wrong_policy_digest_fails_closed(tmp_path)
        test_policy_digest_mismatch_flag_fails_closed(tmp_path)
        test_wrong_evidence_policy_id_fails_closed(tmp_path)
        test_stale_vsa_evidence_fails_closed(tmp_path)
        test_previous_run_artifact_reuse_fails_closed(tmp_path)
        test_time_verified_current_run_mismatch_fails_closed(tmp_path)
        test_missing_evidence_digest_rejected_report_fails_but_does_not_need_fake_digest(tmp_path)
        test_schema_invalid_report_fails_closed(tmp_path)
        test_expectation_mismatch_fails_closed()
        test_missing_report_file_returns_read_error(tmp_path)
        test_refuses_to_write_status_json(tmp_path)
        test_tool_does_not_call_gate_checker()
        test_tool_does_not_write_status_gates()


def test_check_slsa_vsa_trusted_evidence_producer_report_v0() -> None:
    check_check_slsa_vsa_trusted_evidence_producer_report_v0()


if __name__ == "__main__":
    check_check_slsa_vsa_trusted_evidence_producer_report_v0()
    print("OK: check_slsa_vsa_trusted_evidence_producer_report_v0 passed")
