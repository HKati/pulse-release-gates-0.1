#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "build_slsa_vsa_trusted_producer_input_packet_v0.py"
CHECKER = ROOT / "tools" / "check_slsa_vsa_trusted_producer_input_packet_v0.py"
SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_producer_input_packet_example_v0.json"

EXPECTED_CURRENT_RUN_KEY = (
    "GITHUB_RUN_ID=1234567890"
    "|GITHUB_RUN_NUMBER=2692"
    "|GITHUB_RUN_ATTEMPT=1"
    "|GITHUB_WORKFLOW=PULSE CI"
)

BUILDER_ARGS = [
    "--schema",
    str(SCHEMA),
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
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--artifact-sha256",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--artifact-resource-uri",
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--policy-id",
    "pulse-gate-policy-v0",
    "--policy-uri",
    "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json",
    "--policy-sha256",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "--verifier-id",
    "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0",
    "--verified-level",
    "SLSA_BUILD_LEVEL_3",
    "--time-verified",
    "2026-07-04T00:00:00Z",
]

CHECKER_EXPECTED_ARGS = [
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


def replaced_arg(args: list[str], flag: str, value: str) -> list[str]:
    updated = list(args)
    index = updated.index(flag)
    updated[index + 1] = value
    return updated


def run_builder(
    *,
    extra: list[str] | None = None,
    args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        *(args if args is not None else BUILDER_ARGS),
    ]

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


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def assert_builder_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    diagnostic = parse_stdout(result)
    assert diagnostic["ok"] is False
    assert any(expected_fragment in error for error in diagnostic["errors"]), diagnostic["errors"]
    return diagnostic


def run_checker(packet_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--schema",
            str(SCHEMA),
            "--packet",
            str(packet_path),
            *CHECKER_EXPECTED_ARGS,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_valid_cli_inputs_produce_example_contract_shape() -> dict[str, Any]:
    result = run_builder()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    packet = parse_stdout(result)
    assert packet == read_json(EXAMPLE)
    return packet


def assert_current_run_key_is_computed_by_builder(packet: dict[str, Any]) -> None:
    assert "--current-run-key" not in BUILDER_ARGS
    assert packet["run_binding"]["current_run_key"] == EXPECTED_CURRENT_RUN_KEY


def assert_artifact_digest_binding_is_consistent(packet: dict[str, Any]) -> None:
    artifact_sha256 = BUILDER_ARGS[BUILDER_ARGS.index("--artifact-sha256") + 1]
    artifact = packet["artifact_binding"]

    assert artifact["subject_sha256"] == artifact_sha256
    assert artifact["artifact_digest_sha256"] == artifact_sha256


def assert_generated_packet_passes_existing_checker(
    tmp_path: Path,
    packet: dict[str, Any],
) -> None:
    packet_path = tmp_path / "packet.json"
    write_json(packet_path, packet)

    checker_result = run_checker(packet_path)
    assert checker_result.returncode == 0, checker_result.stdout + checker_result.stderr

    checker_report = json.loads(checker_result.stdout)
    assert checker_report["ok"] is True
    assert all(checker_report["checks"].values())


def assert_output_file_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "packet-output.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert output.read_text(encoding="utf-8") == result.stdout
    assert read_json(output) == parse_stdout(result)


def assert_invalid_commit_sha_fails_closed() -> None:
    args = replaced_arg(BUILDER_ARGS, "--commit-sha", "not-a-sha40")
    diagnostic = assert_builder_failure(run_builder(args=args), "schema_error")
    assert diagnostic["exit_kind"] == "generated_packet_schema_invalid"


def assert_invalid_artifact_sha256_fails_closed() -> None:
    args = replaced_arg(BUILDER_ARGS, "--artifact-sha256", "not-a-sha256")
    diagnostic = assert_builder_failure(run_builder(args=args), "schema_error")
    assert diagnostic["exit_kind"] == "generated_packet_schema_invalid"


def assert_refuses_to_write_status_json(tmp_path: Path) -> None:
    output = tmp_path / "status.json"
    result = run_builder(extra=["--output", str(output)])

    assert result.returncode == 2
    assert not output.exists()

    diagnostic = parse_stdout(result)
    assert diagnostic["ok"] is False
    assert "refusing_to_write_status_json" in diagnostic["errors"]


def assert_builder_source_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"

    assert forbidden not in source


def assert_builder_source_does_not_write_status_gates_or_activate_release_sets() -> None:
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


def check_build_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    assert TOOL.exists()
    assert CHECKER.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp)

        packet = assert_valid_cli_inputs_produce_example_contract_shape()
        assert_current_run_key_is_computed_by_builder(packet)
        assert_artifact_digest_binding_is_consistent(packet)
        assert_generated_packet_passes_existing_checker(tmp_path, packet)
        assert_output_file_matches_stdout(tmp_path)
        assert_invalid_commit_sha_fails_closed()
        assert_invalid_artifact_sha256_fails_closed()
        assert_refuses_to_write_status_json(tmp_path)
        assert_builder_source_does_not_call_gate_checker()
        assert_builder_source_does_not_write_status_gates_or_activate_release_sets()


def test_build_slsa_vsa_trusted_producer_input_packet_v0() -> None:
    check_build_slsa_vsa_trusted_producer_input_packet_v0()


if __name__ == "__main__":
    check_build_slsa_vsa_trusted_producer_input_packet_v0()
    print("OK: build_slsa_vsa_trusted_producer_input_packet_v0 smoke passed")
