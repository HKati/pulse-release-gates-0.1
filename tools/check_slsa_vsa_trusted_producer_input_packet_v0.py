#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "check_slsa_vsa_trusted_producer_input_packet_v0"
SCHEMA_VERSION = "slsa_vsa_trusted_producer_input_packet_v0"
PACKET_TYPE = "slsa_vsa_trusted_producer_input_packet"
RECORDED_SIGNAL_MODE = "recorded_signal_only"
CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a SLSA VSA trusted producer input packet."
    )

    parser.add_argument("--schema", required=True, help="Path to input packet schema")
    parser.add_argument("--packet", required=True, help="Path to input packet JSON")

    parser.add_argument("--expect-producer-id", required=True)
    parser.add_argument("--expect-producer-name", required=True)
    parser.add_argument("--expect-producer-version", required=True)
    parser.add_argument("--expect-producer-source", required=True)
    parser.add_argument("--expect-ci-workflow-or-job-identity", required=True)

    parser.add_argument("--expect-current-run-id", required=True)
    parser.add_argument("--expect-current-run-key", required=True)
    parser.add_argument("--expect-commit-sha", required=True)
    parser.add_argument("--expect-release-candidate-id", required=True)

    parser.add_argument("--expect-artifact-subject-name", required=True)
    parser.add_argument("--expect-artifact-sha256", required=True)
    parser.add_argument("--expect-artifact-resource-uri", required=True)

    parser.add_argument("--expect-policy-id", required=True)
    parser.add_argument("--expect-policy-uri", required=True)
    parser.add_argument("--expect-policy-sha256", required=True)

    parser.add_argument("--expect-verifier-id", required=True)
    parser.add_argument("--expect-verified-level", required=True)
    parser.add_argument("--expect-time-verified", required=True)

    parser.add_argument("--expect-candidate-set", default=CANDIDATE_SET)
    parser.add_argument("--output", help="Optional path for deterministic diagnostic report")

    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nested_get(data: Any, path: list[str]) -> Any:
    cursor = data
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def expected_current_run_key_from_packet(packet: dict[str, Any]) -> str | None:
    run_binding = packet.get("run_binding")
    if not isinstance(run_binding, dict):
        return None

    current_run_id = run_binding.get("current_run_id")
    current_run_number = run_binding.get("current_run_number")
    current_run_attempt = run_binding.get("current_run_attempt")
    workflow_name = run_binding.get("workflow_name")

    required_values = [
        current_run_id,
        current_run_number,
        current_run_attempt,
        workflow_name,
    ]

    if not all(isinstance(value, str) and value for value in required_values):
        return None

    return (
        f"GITHUB_RUN_ID={current_run_id}"
        f"|GITHUB_RUN_NUMBER={current_run_number}"
        f"|GITHUB_RUN_ATTEMPT={current_run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
    )


def validation_errors(schema: dict[str, Any], packet: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )

    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(validator.iter_errors(packet), key=lambda err: list(err.path))
    ]


def make_diagnostic(
    *,
    ok: bool,
    schema_valid: bool,
    checks: dict[str, bool],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": ok,
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "schema_valid": schema_valid,
        "checks": checks,
        "errors": errors,
    }


def emit_report(report: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def build_checks(args: argparse.Namespace, packet: dict[str, Any]) -> dict[str, bool]:
    packet_run_key = nested_get(packet, ["run_binding", "current_run_key"])
    expected_run_key_from_packet = expected_current_run_key_from_packet(packet)

    run_release_candidate = nested_get(packet, ["run_binding", "release_candidate_id"])
    artifact_release_candidate = nested_get(packet, ["artifact_binding", "release_candidate_id"])
    subject_sha256 = nested_get(packet, ["artifact_binding", "subject_sha256"])
    artifact_digest_sha256 = nested_get(packet, ["artifact_binding", "artifact_digest_sha256"])

    return {
        "schema_version_ok": packet.get("schema_version") == SCHEMA_VERSION,
        "packet_type_ok": packet.get("packet_type") == PACKET_TYPE,
        "recorded_signal_mode_ok": packet.get("recorded_signal_mode") == RECORDED_SIGNAL_MODE,
        "candidate_set_matches": packet.get("candidate_set") == args.expect_candidate_set,

        "producer_id_matches": (
            nested_get(packet, ["producer_identity", "producer_id"])
            == args.expect_producer_id
        ),
        "producer_name_matches": (
            nested_get(packet, ["producer_identity", "producer_name"])
            == args.expect_producer_name
        ),
        "producer_version_matches": (
            nested_get(packet, ["producer_identity", "producer_version"])
            == args.expect_producer_version
        ),
        "producer_source_matches": (
            nested_get(packet, ["producer_identity", "producer_source"])
            == args.expect_producer_source
        ),
        "producer_ci_identity_matches": (
            nested_get(packet, ["producer_identity", "ci_workflow_or_job_identity"])
            == args.expect_ci_workflow_or_job_identity
        ),

        "current_run_id_matches": (
            nested_get(packet, ["run_binding", "current_run_id"])
            == args.expect_current_run_id
        ),
        "current_run_key_matches": packet_run_key == args.expect_current_run_key,
        "current_run_key_self_consistent": (
            isinstance(expected_run_key_from_packet, str)
            and packet_run_key == expected_run_key_from_packet
        ),
        "commit_sha_matches": (
            nested_get(packet, ["run_binding", "commit_sha"])
            == args.expect_commit_sha
        ),
        "run_release_candidate_matches": (
            run_release_candidate == args.expect_release_candidate_id
        ),

        "artifact_subject_name_matches": (
            nested_get(packet, ["artifact_binding", "subject_name"])
            == args.expect_artifact_subject_name
        ),
        "artifact_subject_sha256_matches": subject_sha256 == args.expect_artifact_sha256,
        "artifact_resource_uri_matches": (
            nested_get(packet, ["artifact_binding", "resource_uri"])
            == args.expect_artifact_resource_uri
        ),
        "artifact_release_candidate_matches": (
            artifact_release_candidate == args.expect_release_candidate_id
        ),
        "artifact_digest_sha256_matches": artifact_digest_sha256 == args.expect_artifact_sha256,
        "artifact_digest_self_consistent": (
            isinstance(subject_sha256, str)
            and isinstance(artifact_digest_sha256, str)
            and subject_sha256 == artifact_digest_sha256
        ),
        "run_artifact_release_candidate_consistent": (
            isinstance(run_release_candidate, str)
            and run_release_candidate == artifact_release_candidate
        ),

        "policy_id_matches": (
            nested_get(packet, ["policy_binding", "expected_policy_id"])
            == args.expect_policy_id
        ),
        "policy_uri_matches": (
            nested_get(packet, ["policy_binding", "expected_policy_uri"])
            == args.expect_policy_uri
        ),
        "policy_sha256_matches": (
            nested_get(packet, ["policy_binding", "expected_policy_sha256"])
            == args.expect_policy_sha256
        ),

        "verifier_id_matches": (
            nested_get(packet, ["verifier_binding", "expected_verifier_id"])
            == args.expect_verifier_id
        ),

        "expected_verified_level_matches": (
            packet.get("expected_verified_level") == args.expect_verified_level
        ),
        "expected_time_verified_matches": (
            nested_get(packet, ["freshness", "expected_time_verified"])
            == args.expect_time_verified
        ),
    }


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        schema = load_json(Path(args.schema))
        packet = load_json(Path(args.packet))
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"read_error: {exc}"],
        )
        return diagnostic, 2

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"schema_invalid: {exc}"],
        )
        return diagnostic, 2

    errors = validation_errors(schema, packet)
    schema_valid = not errors

    if not isinstance(packet, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["packet_not_object"],
        )
        return diagnostic, 1

    checks = build_checks(args, packet)

    for check_name, passed in checks.items():
        if not passed:
            errors.append(f"check_failed: {check_name}")

    ok = schema_valid and not errors

    diagnostic = make_diagnostic(
        ok=ok,
        schema_valid=schema_valid,
        checks=checks,
        errors=errors,
    )

    return diagnostic, 0 if ok else 1


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None

    if output is not None and output.name == "status.json":
        report = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=["refusing_to_write_status_json"],
        )
        emit_report(report, None)
        return 2

    report, exit_code = build_report(args)
    emit_report(report, output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
