#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "check_slsa_vsa_trusted_producer_input_packet_v0.py"
SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_producer_input_packet_example_v0.json"

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
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-artifact-sha256",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-artifact-resource-uri",
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-policy-id",
    "pulse-gate-policy-v0",
    "--expect-policy-uri",
    "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json",
    "--expect-policy-sha256",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "--expect-verifier-id",
    "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0",
    "--expect-verified-level",
    "SLSA_BUILD_LEVEL_3",
    "--expect-time-verified",
    "2026-07-04T00:00:00Z",
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


def run_tool(
    packet_path: Path = EXAMPLE,
    extra: list[str] | None = None,
    omit_expected: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(SCHEMA),
        "--packet",
        str(packet_path),
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


def mutated_packet(tmp_path: Path, name: str, path: list[str], value: Any) -> Path:
    packet = read_json(EXAMPLE)
    cursor: Any = packet

    for part in path[:-1]:
        cursor = cursor[part]

    cursor[path[-1]] = value

    packet_path = tmp_path / name
    write_json(packet_path, packet)
    return packet_path


def test_valid_example_passes() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    diagnostic = parse_diagnostic(result)
    assert diagnostic["tool"] == "check_slsa_vsa_trusted_producer_input_packet_v0"
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


def test_schema_invalid_packet_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "schema_invalid.json",
        ["created_utc"],
        "unknown",
    )

    diagnostic = assert_failure(run_tool(path), "schema_error")
    assert diagnostic["schema_valid"] is False


def test_missing_packet_file_returns_read_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = run_tool(packet_path=missing)

    assert result.returncode == 2
    diagnostic = parse_diagnostic(result)
    assert diagnostic["ok"] is False
    assert any("read_error:" in error for error in diagnostic["errors"])


def test_wrong_producer_identity_fails_closed(tmp_path: Path) -> None:
    cases = [
        ("producer_id", "wrong-producer", "producer_id_matches"),
        ("producer_name", "Wrong producer", "producer_name_matches"),
        ("producer_version", "9.9.9", "producer_version_matches"),
        ("producer_source", "manual-local", "producer_source_matches"),
        ("ci_workflow_or_job_identity", "Wrong CI / job", "producer_ci_identity_matches"),
    ]

    for field, value, expected_error in cases:
        path = mutated_packet(
            tmp_path,
            f"wrong_{field}.json",
            ["producer_identity", field],
            value,
        )

        assert_failure(run_tool(path), f"check_failed: {expected_error}")


def test_wrong_current_run_binding_fails_closed(tmp_path: Path) -> None:
    cases = [
        ("current_run_id", "9999999999", "current_run_id_matches"),
        (
            "current_run_key",
            "GITHUB_RUN_ID=9999999999|GITHUB_RUN_NUMBER=2692|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
            "current_run_key_matches",
        ),
        ("commit_sha", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "commit_sha_matches"),
        ("release_candidate_id", "wrong-candidate", "run_release_candidate_matches"),
    ]

    for field, value, expected_error in cases:
        path = mutated_packet(
            tmp_path,
            f"wrong_run_{field}.json",
            ["run_binding", field],
            value,
        )

        assert_failure(run_tool(path), f"check_failed: {expected_error}")


def test_non_self_consistent_current_run_key_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "non_self_consistent_run_key.json",
        ["run_binding", "workflow_name"],
        "Other workflow",
    )

    assert_failure(run_tool(path), "check_failed: current_run_key_self_consistent")


def test_wrong_artifact_binding_fails_closed(tmp_path: Path) -> None:
    cases = [
        ("subject_name", "git+https://example.invalid/wrong@refs/tags/v0", "artifact_subject_name_matches"),
        ("subject_sha256", "c" * 64, "artifact_subject_sha256_matches"),
        ("resource_uri", "git+https://example.invalid/wrong@refs/tags/v0", "artifact_resource_uri_matches"),
        ("release_candidate_id", "wrong-candidate", "artifact_release_candidate_matches"),
        ("artifact_digest_sha256", "d" * 64, "artifact_digest_sha256_matches"),
    ]

    for field, value, expected_error in cases:
        path = mutated_packet(
            tmp_path,
            f"wrong_artifact_{field}.json",
            ["artifact_binding", field],
            value,
        )

        assert_failure(run_tool(path), f"check_failed: {expected_error}")


def test_artifact_digest_self_mismatch_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "artifact_digest_self_mismatch.json",
        ["artifact_binding", "artifact_digest_sha256"],
        "c" * 64,
    )

    assert_failure(run_tool(path), "check_failed: artifact_digest_self_consistent")


def test_run_artifact_release_candidate_mismatch_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "run_artifact_candidate_mismatch.json",
        ["artifact_binding", "release_candidate_id"],
        "wrong-candidate",
    )

    diagnostic = assert_failure(
        run_tool(path),
        "check_failed: run_artifact_release_candidate_consistent",
    )
    assert "check_failed: artifact_release_candidate_matches" in diagnostic["errors"]


def test_wrong_policy_binding_fails_closed(tmp_path: Path) -> None:
    cases = [
        ("expected_policy_id", "wrong-policy", "policy_id_matches"),
        ("expected_policy_uri", "https://example.invalid/policies/wrong.json", "policy_uri_matches"),
        ("expected_policy_sha256", "e" * 64, "policy_sha256_matches"),
    ]

    for field, value, expected_error in cases:
        path = mutated_packet(
            tmp_path,
            f"wrong_policy_{field}.json",
            ["policy_binding", field],
            value,
        )

        assert_failure(run_tool(path), f"check_failed: {expected_error}")


def test_wrong_verifier_identity_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "wrong_verifier.json",
        ["verifier_binding", "expected_verifier_id"],
        "https://example.invalid/verifiers/wrong",
    )

    assert_failure(run_tool(path), "check_failed: verifier_id_matches")


def test_wrong_expected_verified_level_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "wrong_verified_level.json",
        ["expected_verified_level"],
        "SLSA_BUILD_LEVEL_4",
    )

    assert_failure(run_tool(path), "check_failed: expected_verified_level_matches")


def test_wrong_expected_time_verified_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "wrong_time_verified.json",
        ["freshness", "expected_time_verified"],
        "2026-07-05T00:00:00Z",
    )

    assert_failure(run_tool(path), "check_failed: expected_time_verified_matches")


def test_wrong_candidate_set_fails_closed(tmp_path: Path) -> None:
    path = mutated_packet(
        tmp_path,
        "wrong_candidate_set.json",
        ["candidate_set"],
        "slsa_vsa_release_required_candidate",
    )

    assert_failure(run_tool(path), "schema_error")


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


def check_check_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    assert TOOL.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_valid_example_passes()
        test_output_report_matches_stdout(tmp_path)
        test_schema_invalid_packet_fails_closed(tmp_path)
        test_missing_packet_file_returns_read_error(tmp_path)
        test_wrong_producer_identity_fails_closed(tmp_path)
        test_wrong_current_run_binding_fails_closed(tmp_path)
        test_non_self_consistent_current_run_key_fails_closed(tmp_path)
        test_wrong_artifact_binding_fails_closed(tmp_path)
        test_artifact_digest_self_mismatch_fails_closed(tmp_path)
        test_run_artifact_release_candidate_mismatch_fails_closed(tmp_path)
        test_wrong_policy_binding_fails_closed(tmp_path)
        test_wrong_verifier_identity_fails_closed(tmp_path)
        test_wrong_expected_verified_level_fails_closed(tmp_path)
        test_wrong_expected_time_verified_fails_closed(tmp_path)
        test_wrong_candidate_set_fails_closed(tmp_path)
        test_refuses_to_write_status_json(tmp_path)
        test_tool_does_not_call_gate_checker()
        test_tool_does_not_write_status_gates_or_activate_release_sets()


def test_check_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    check_check_slsa_vsa_trusted_producer_input_packet_v0()


if __name__ == "__main__":
    check_check_slsa_vsa_trusted_producer_input_packet_v0()
    print("OK: check_slsa_vsa_trusted_producer_input_packet_v0 smoke passed")
