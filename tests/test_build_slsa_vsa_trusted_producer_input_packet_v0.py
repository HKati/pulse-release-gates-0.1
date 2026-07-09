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

TOOL = ROOT / "tools" / "build_slsa_vsa_trusted_producer_input_packet_v0.py"

EVIDENCE_SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EVIDENCE_EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

INPUT_PACKET_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
INPUT_PACKET_VALIDATOR = ROOT / "tools" / "check_slsa_vsa_trusted_producer_input_packet_v0.py"

CREATED_UTC = "2026-07-07T00:00:00Z"

PRODUCER_ID = "pulse_slsa_vsa_trusted_evidence_producer_v0"
PRODUCER_NAME = "PULSE SLSA VSA trusted evidence producer"
PRODUCER_VERSION = "0.1.0"
PRODUCER_SOURCE = "github-actions"
CI_IDENTITY = "PULSE CI / SLSA VSA trusted evidence producer"

CURRENT_RUN_ID = "1234567890"
CURRENT_RUN_NUMBER = "2692"
CURRENT_RUN_ATTEMPT = "1"
WORKFLOW_NAME = "PULSE CI"
JOB_NAME = "slsa-vsa-trusted-evidence-producer"
CURRENT_RUN_KEY = (
    "GITHUB_RUN_ID=1234567890"
    "|GITHUB_RUN_NUMBER=2692"
    "|GITHUB_RUN_ATTEMPT=1"
    "|GITHUB_WORKFLOW=PULSE CI"
)
COMMIT_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
RELEASE_CANDIDATE_ID = "pulse-release-gates-0.1-candidate-v0"

SUBJECT_NAME = "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0"
SUBJECT_SHA256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
RESOURCE_URI = SUBJECT_NAME

POLICY_ID = "pulse-gate-policy-v0"
POLICY_URI = "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json"
POLICY_SHA256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

VERIFIER_ID = "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0"
VERIFIED_LEVEL = "SLSA_BUILD_LEVEL_3"
TIME_VERIFIED = "2026-07-04T00:00:00Z"

CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def base_args(*, evidence: Path, output: Path | None) -> list[str]:
    args = [
        "--evidence-schema",
        str(EVIDENCE_SCHEMA),
        "--evidence",
        str(evidence),
        "--input-packet-schema",
        str(INPUT_PACKET_SCHEMA),
        "--input-packet-validator",
        str(INPUT_PACKET_VALIDATOR),
        "--created-utc",
        CREATED_UTC,
        "--expect-producer-id",
        PRODUCER_ID,
        "--expect-producer-name",
        PRODUCER_NAME,
        "--expect-producer-version",
        PRODUCER_VERSION,
        "--expect-producer-source",
        PRODUCER_SOURCE,
        "--expect-ci-workflow-or-job-identity",
        CI_IDENTITY,
        "--expect-current-run-id",
        CURRENT_RUN_ID,
        "--expect-current-run-number",
        CURRENT_RUN_NUMBER,
        "--expect-current-run-attempt",
        CURRENT_RUN_ATTEMPT,
        "--expect-current-run-key",
        CURRENT_RUN_KEY,
        "--expect-workflow-name",
        WORKFLOW_NAME,
        "--expect-job-name",
        JOB_NAME,
        "--expect-commit-sha",
        COMMIT_SHA,
        "--expect-release-candidate-id",
        RELEASE_CANDIDATE_ID,
        "--expect-artifact-subject-name",
        SUBJECT_NAME,
        "--expect-artifact-sha256",
        SUBJECT_SHA256,
        "--expect-artifact-resource-uri",
        RESOURCE_URI,
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
        "--freshness-epoch",
        "current_run",
        "--expect-candidate-set",
        CANDIDATE_SET,
    ]

    if output is not None:
        args.extend(["--output", str(output)])

    return args


def replace_arg(args: list[str], option: str, value: str) -> None:
    index = args.index(option)
    args[index + 1] = value


def remove_options(args: list[str], options: set[str]) -> list[str]:
    filtered: list[str] = []
    index = 0

    while index < len(args):
        item = args[index]
        if item in options:
            index += 2
            continue

        filtered.append(item)
        index += 1

    return filtered


def run_builder(
    *,
    evidence: Path = EVIDENCE_EXAMPLE,
    output: Path | None,
    replacements: dict[str, str] | None = None,
    omit: set[str] | None = None,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = base_args(evidence=evidence, output=output)

    for option, value in (replacements or {}).items():
        replace_arg(args, option, value)

    if omit:
        args = remove_options(args, omit)

    if extra:
        args.extend(extra)

    cmd = [
        sys.executable,
        str(TOOL),
        *args,
    ]

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


def input_packet_validator() -> jsonschema.Draft202012Validator:
    schema = read_json(INPUT_PACKET_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def assert_packet_schema_valid(packet: dict[str, Any]) -> None:
    errors = sorted(
        input_packet_validator().iter_errors(packet),
        key=lambda error: list(error.path),
    )
    assert not errors, [error.message for error in errors]


def run_existing_input_packet_validator(packet_path: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(INPUT_PACKET_VALIDATOR),
        "--schema",
        str(INPUT_PACKET_SCHEMA),
        "--packet",
        str(packet_path),
        "--expect-producer-id",
        PRODUCER_ID,
        "--expect-producer-name",
        PRODUCER_NAME,
        "--expect-producer-version",
        PRODUCER_VERSION,
        "--expect-producer-source",
        PRODUCER_SOURCE,
        "--expect-ci-workflow-or-job-identity",
        CI_IDENTITY,
        "--expect-current-run-id",
        CURRENT_RUN_ID,
        "--expect-current-run-key",
        CURRENT_RUN_KEY,
        "--expect-commit-sha",
        COMMIT_SHA,
        "--expect-release-candidate-id",
        RELEASE_CANDIDATE_ID,
        "--expect-artifact-subject-name",
        SUBJECT_NAME,
        "--expect-artifact-sha256",
        SUBJECT_SHA256,
        "--expect-artifact-resource-uri",
        RESOURCE_URI,
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
        CANDIDATE_SET,
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
    output: Path,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists(), f"failure wrote output packet: {output}"

    diagnostic = parse_json_stdout(result)
    assert diagnostic["ok"] is False

    errors = diagnostic.get("errors")
    assert isinstance(errors, list)
    assert any(expected_fragment in str(error) for error in errors), errors

    return diagnostic


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


def malformed_json(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_text("{not-json", encoding="utf-8")
    return target


def test_valid_evidence_builds_schema_valid_input_packet(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    result = run_builder(output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert output.exists()

    packet = parse_json_stdout(result)
    assert read_json(output) == packet

    assert_packet_schema_valid(packet)

    assert packet["schema_version"] == "slsa_vsa_trusted_producer_input_packet_v0"
    assert packet["packet_type"] == "slsa_vsa_trusted_producer_input_packet"
    assert packet["created_utc"] == CREATED_UTC
    assert packet["recorded_signal_mode"] == "recorded_signal_only"
    assert packet["candidate_set"] == CANDIDATE_SET

    assert packet["producer_identity"]["producer_id"] == PRODUCER_ID
    assert packet["producer_identity"]["producer_name"] == PRODUCER_NAME
    assert packet["producer_identity"]["producer_version"] == PRODUCER_VERSION
    assert packet["producer_identity"]["producer_source"] == PRODUCER_SOURCE
    assert packet["producer_identity"]["ci_workflow_or_job_identity"] == CI_IDENTITY

    assert packet["run_binding"]["current_run_id"] == CURRENT_RUN_ID
    assert packet["run_binding"]["current_run_number"] == CURRENT_RUN_NUMBER
    assert packet["run_binding"]["current_run_attempt"] == CURRENT_RUN_ATTEMPT
    assert packet["run_binding"]["current_run_key"] == CURRENT_RUN_KEY
    assert packet["run_binding"]["workflow_name"] == WORKFLOW_NAME
    assert packet["run_binding"]["job_name"] == JOB_NAME
    assert packet["run_binding"]["commit_sha"] == COMMIT_SHA
    assert packet["run_binding"]["release_candidate_id"] == RELEASE_CANDIDATE_ID

    assert packet["artifact_binding"]["subject_name"] == SUBJECT_NAME
    assert packet["artifact_binding"]["subject_sha256"] == SUBJECT_SHA256
    assert packet["artifact_binding"]["resource_uri"] == RESOURCE_URI
    assert packet["artifact_binding"]["release_candidate_id"] == RELEASE_CANDIDATE_ID
    assert packet["artifact_binding"]["artifact_digest_sha256"] == SUBJECT_SHA256

    assert packet["policy_binding"]["expected_policy_id"] == POLICY_ID
    assert packet["policy_binding"]["expected_policy_uri"] == POLICY_URI
    assert packet["policy_binding"]["expected_policy_sha256"] == POLICY_SHA256

    assert packet["verifier_binding"]["expected_verifier_id"] == VERIFIER_ID
    assert packet["expected_verified_level"] == VERIFIED_LEVEL
    assert packet["freshness"]["expected_time_verified"] == TIME_VERIFIED
    assert packet["freshness"]["freshness_epoch"] == "current_run"


def test_generated_packet_passes_existing_input_packet_validator(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    result = run_builder(output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()

    validator_result = run_existing_input_packet_validator(output)
    assert validator_result.returncode == 0, (
        validator_result.stdout + validator_result.stderr
    )


def test_output_is_required(tmp_path: Path) -> None:
    result = run_builder(output=None)

    assert result.returncode != 0
    assert "--output" in result.stderr
    assert "Traceback" not in result.stderr


def test_status_json_output_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "status.json"
    result = run_builder(output=output)

    diagnostic = assert_rejected(result, "refusing_to_write_status_json", output)
    assert diagnostic["exit_kind"] == "refused_output_path"


def test_missing_evidence_returns_deterministic_diagnostic(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    missing = tmp_path / "missing_vsa.json"

    first = run_builder(evidence=missing, output=output)
    second = run_builder(evidence=missing, output=output)

    first_report = assert_rejected(first, "evidence_read_error", output)
    second_report = assert_rejected(second, "evidence_read_error", output)

    assert first_report == second_report


def test_malformed_evidence_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    evidence = malformed_json(tmp_path, "malformed_vsa.json")

    assert_rejected(run_builder(evidence=evidence, output=output), "evidence_read_error", output)


def test_schema_invalid_evidence_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    evidence = deleted_json_field(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="missing_policy_id.json",
        path=["vsa", "predicate", "policy", "id"],
    )

    assert_rejected(run_builder(evidence=evidence, output=output), "evidence_schema", output)


def test_required_explicit_inputs_are_cli_required(tmp_path: Path) -> None:
    required_options = [
        "--created-utc",
        "--expect-producer-id",
        "--expect-producer-name",
        "--expect-producer-version",
        "--expect-producer-source",
        "--expect-ci-workflow-or-job-identity",
        "--expect-current-run-id",
        "--expect-current-run-number",
        "--expect-current-run-attempt",
        "--expect-current-run-key",
        "--expect-workflow-name",
        "--expect-job-name",
        "--expect-commit-sha",
        "--expect-release-candidate-id",
        "--expect-artifact-subject-name",
        "--expect-artifact-sha256",
        "--expect-artifact-resource-uri",
        "--expect-policy-id",
        "--expect-policy-uri",
        "--expect-policy-sha256",
        "--expect-verifier-id",
        "--expect-verified-level",
        "--expect-time-verified",
        "--freshness-epoch",
    ]

    for option in required_options:
        output = tmp_path / f"{option.removeprefix('--').replace('-', '_')}.json"
        result = run_builder(output=output, omit={option})

        assert result.returncode != 0, option
        assert not output.exists(), option
        assert "Traceback" not in result.stderr, option
        assert option in result.stderr, result.stderr


def test_current_run_key_must_match_explicit_components(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={
            "--expect-current-run-key": (
                "GITHUB_RUN_ID=1234567890"
                "|GITHUB_RUN_NUMBER=wrong"
                "|GITHUB_RUN_ATTEMPT=1"
                "|GITHUB_WORKFLOW=PULSE CI"
            )
        },
    )

    assert_rejected(result, "current_run_key_matches_components", output)


def test_freshness_epoch_must_be_current_run(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={"--freshness-epoch": "previous_run"},
    )

    assert_rejected(result, "freshness_epoch_current_run", output)


def test_evidence_policy_id_must_match_explicit_expected_policy_id(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"
    evidence = mutated_json(
        source=EVIDENCE_EXAMPLE,
        tmp_path=tmp_path,
        name="wrong_policy_id.json",
        path=["vsa", "predicate", "policy", "id"],
        value="wrong-policy",
    )

    diagnostic = assert_rejected(
        run_builder(evidence=evidence, output=output),
        "evidence_policy_id_matches_expected",
        output,
    )

    assert any("wrong-policy" in str(error) for error in diagnostic["errors"])


def test_evidence_policy_uri_must_match_explicit_expected_policy_uri(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={
            "--expect-policy-uri": "https://example.invalid/policies/wrong-policy.json",
        },
    )

    assert_rejected(result, "evidence_policy_uri_matches_expected", output)


def test_evidence_policy_digest_must_match_explicit_expected_policy_sha256(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={"--expect-policy-sha256": "c" * 64},
    )

    assert_rejected(result, "evidence_policy_sha256_matches_expected", output)


def test_evidence_verifier_id_must_match_explicit_expected_verifier_id(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={
            "--expect-verifier-id": "https://example.invalid/verifiers/wrong",
        },
    )

    assert_rejected(result, "evidence_verifier_id_matches_expected", output)


def test_evidence_verified_levels_must_contain_expected_verified_level(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={"--expect-verified-level": "SLSA_BUILD_LEVEL_4"},
    )

    assert_rejected(result, "evidence_verified_level_contains_expected", output)


def test_evidence_time_verified_must_match_explicit_expected_time_verified(
    tmp_path: Path,
) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={"--expect-time-verified": "2026-07-05T00:00:00Z"},
    )

    assert_rejected(result, "evidence_time_verified_matches_expected", output)


def test_artifact_subject_name_must_match_evidence_subject(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={
            "--expect-artifact-subject-name": (
                "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/wrong"
            )
        },
    )

    assert_rejected(result, "evidence_subject_name_matches_expected", output)


def test_artifact_digest_must_match_evidence_subject_digest(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={"--expect-artifact-sha256": "d" * 64},
    )

    assert_rejected(result, "evidence_subject_sha256_matches_expected", output)


def test_artifact_resource_uri_must_match_evidence_resource_uri(tmp_path: Path) -> None:
    output = tmp_path / "trusted_producer_input_packet.json"

    result = run_builder(
        output=output,
        replacements={
            "--expect-artifact-resource-uri": (
                "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/wrong"
            )
        },
    )

    assert_rejected(result, "evidence_resource_uri_matches_expected", output)


def test_tool_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"

    assert forbidden not in source


def test_tool_does_not_write_status_gates_or_activate_release_sets() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden_markers = [
        "status.gates",
        "status_" + "gates",
        "release_" + "required",
        "release_" + "blocking",
        "prod_" + "required",
        "stage_" + "required",
        "policy_to_require_args.py",
        "fold_slsa_vsa_intake_into_status_v0.py",
        "materialize_release_required_from_verifier_v0.py",
    ]

    for marker in forbidden_markers:
        assert marker not in source, marker


def test_status_json_source_reference_is_refusal_only() -> None:
    source = TOOL.read_text(encoding="utf-8")
    status_lines = [line.strip() for line in source.splitlines() if "status.json" in line]

    assert status_lines
    assert any("output.name" in line and "status.json" in line for line in status_lines)
    assert all("write_text" not in line for line in status_lines)


def check_build_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    assert TOOL.exists()
    assert EVIDENCE_SCHEMA.exists()
    assert EVIDENCE_EXAMPLE.exists()
    assert INPUT_PACKET_SCHEMA.exists()
    assert INPUT_PACKET_VALIDATOR.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        test_valid_evidence_builds_schema_valid_input_packet(tmp_path)
        test_generated_packet_passes_existing_input_packet_validator(tmp_path)
        test_output_is_required(tmp_path)
        test_status_json_output_is_refused(tmp_path)
        test_missing_evidence_returns_deterministic_diagnostic(tmp_path)
        test_malformed_evidence_fails_closed(tmp_path)
        test_schema_invalid_evidence_fails_closed(tmp_path)
        test_required_explicit_inputs_are_cli_required(tmp_path)
        test_current_run_key_must_match_explicit_components(tmp_path)
        test_freshness_epoch_must_be_current_run(tmp_path)
        test_evidence_policy_id_must_match_explicit_expected_policy_id(tmp_path)
        test_evidence_policy_uri_must_match_explicit_expected_policy_uri(tmp_path)
        test_evidence_policy_digest_must_match_explicit_expected_policy_sha256(tmp_path)
        test_evidence_verifier_id_must_match_explicit_expected_verifier_id(tmp_path)
        test_evidence_verified_levels_must_contain_expected_verified_level(tmp_path)
        test_evidence_time_verified_must_match_explicit_expected_time_verified(tmp_path)
        test_artifact_subject_name_must_match_evidence_subject(tmp_path)
        test_artifact_digest_must_match_evidence_subject_digest(tmp_path)
        test_artifact_resource_uri_must_match_evidence_resource_uri(tmp_path)
        test_tool_does_not_call_gate_checker()
        test_tool_does_not_write_status_gates_or_activate_release_sets()
        test_status_json_source_reference_is_refusal_only()


def test_build_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    check_build_slsa_vsa_trusted_producer_input_packet_v0()


if __name__ == "__main__":
    check_build_slsa_vsa_trusted_producer_input_packet_v0()
    print("OK: build_slsa_vsa_trusted_producer_input_packet_v0 smoke passed")
