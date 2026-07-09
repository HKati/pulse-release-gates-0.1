#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "build_slsa_vsa_trusted_producer_input_packet_v0"
SCHEMA_VERSION = "slsa_vsa_trusted_producer_input_packet_v0"
PACKET_TYPE = "slsa_vsa_trusted_producer_input_packet"
RECORDED_SIGNAL_MODE = "recorded_signal_only"
CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic SLSA VSA trusted producer input packet."
        )
    )

    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to trusted producer input packet schema",
    )
    parser.add_argument("--created-utc", required=True)

    parser.add_argument("--producer-id", required=True)
    parser.add_argument("--producer-name", required=True)
    parser.add_argument("--producer-version", required=True)
    parser.add_argument("--producer-source", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)

    parser.add_argument("--current-run-id", required=True)
    parser.add_argument("--current-run-number", required=True)
    parser.add_argument("--current-run-attempt", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--release-candidate-id", required=True)

    parser.add_argument("--artifact-subject-name", required=True)
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--artifact-resource-uri", required=True)

    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--policy-uri", required=True)
    parser.add_argument("--policy-sha256", required=True)

    parser.add_argument("--verifier-id", required=True)
    parser.add_argument("--verified-level", required=True)
    parser.add_argument("--time-verified", required=True)
    parser.add_argument("--freshness-epoch", default="current_run")

    parser.add_argument("--output")

    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def current_run_key(args: argparse.Namespace) -> str:
    return (
        f"GITHUB_RUN_ID={args.current_run_id}"
        f"|GITHUB_RUN_NUMBER={args.current_run_number}"
        f"|GITHUB_RUN_ATTEMPT={args.current_run_attempt}"
        f"|GITHUB_WORKFLOW={args.workflow_name}"
    )


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "created_utc": args.created_utc,
        "producer_identity": {
            "producer_id": args.producer_id,
            "producer_name": args.producer_name,
            "producer_version": args.producer_version,
            "producer_source": args.producer_source,
            "ci_workflow_or_job_identity": args.ci_workflow_or_job_identity,
        },
        "run_binding": {
            "current_run_id": args.current_run_id,
            "current_run_number": args.current_run_number,
            "current_run_attempt": args.current_run_attempt,
            "current_run_key": current_run_key(args),
            "workflow_name": args.workflow_name,
            "job_name": args.job_name,
            "commit_sha": args.commit_sha,
            "release_candidate_id": args.release_candidate_id,
        },
        "artifact_binding": {
            "subject_name": args.artifact_subject_name,
            "subject_sha256": args.artifact_sha256,
            "resource_uri": args.artifact_resource_uri,
            "release_candidate_id": args.release_candidate_id,
            "artifact_digest_sha256": args.artifact_sha256,
        },
        "policy_binding": {
            "expected_policy_id": args.policy_id,
            "expected_policy_uri": args.policy_uri,
            "expected_policy_sha256": args.policy_sha256,
        },
        "verifier_binding": {
            "expected_verifier_id": args.verifier_id,
        },
        "expected_verified_level": args.verified_level,
        "freshness": {
            "expected_time_verified": args.time_verified,
            "freshness_epoch": args.freshness_epoch,
        },
        "recorded_signal_mode": RECORDED_SIGNAL_MODE,
        "candidate_set": CANDIDATE_SET,
    }


def validation_errors(schema: dict[str, Any], packet: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )

    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(validator.iter_errors(packet), key=lambda err: list(err.path))
    ]


def make_diagnostic(errors: list[str], exit_kind: str = "build_error") -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "exit_kind": exit_kind,
        "errors": errors,
    }


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def emit_json(data: dict[str, Any], output: Path | None) -> None:
    rendered = render_json(data)
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        schema = load_json(Path(args.schema))
    except Exception as exc:
        return make_diagnostic([f"schema_read_error: {exc}"]), 2

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return make_diagnostic([f"schema_invalid: {exc}"]), 2

    packet = build_packet(args)
    errors = validation_errors(schema, packet)

    if errors:
        return make_diagnostic(errors, exit_kind="generated_packet_schema_invalid"), 1

    return packet, 0


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None

    if output is not None and output.name == "status.json":
        diagnostic = make_diagnostic(
            ["refusing_to_write_status_json"],
            exit_kind="output_refused",
        )
        emit_json(diagnostic, None)
        return 2

    result, exit_code = build(args)
    emit_json(result, output if exit_code == 0 else None)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
