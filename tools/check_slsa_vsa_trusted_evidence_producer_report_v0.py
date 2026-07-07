#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "check_slsa_vsa_trusted_evidence_producer_report_v0"
SCHEMA_VERSION = "slsa_vsa_trusted_evidence_producer_report_v0"
REPORT_TYPE = "slsa_vsa_trusted_evidence_producer_report"
ACCEPTED_DECISION = "TRUSTED_EVIDENCE_ACCEPTED"
CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a SLSA VSA trusted evidence producer report."
    )
    parser.add_argument("--schema", required=True, help="Path to producer report schema")
    parser.add_argument("--report", required=True, help="Path to producer report JSON")

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

    parser.add_argument("--expect-policy-id", required=True)
    parser.add_argument("--expect-policy-sha256", required=True)

    parser.add_argument("--expect-verifier-id", required=True)
    parser.add_argument("--expect-verified-level", required=True)

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
        "report_type": REPORT_TYPE,
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


def validation_errors(schema: dict[str, Any], report: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(validator.iter_errors(report), key=lambda err: list(err.path))
    ]


def _verified_level_list_contains(report: dict[str, Any], expected_level: str) -> bool:
    levels = nested_get(report, ["evidence", "evidence_verified_levels"])
    return isinstance(levels, list) and expected_level in levels


def build_checks(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, bool]:
    expected_policy_uri = nested_get(report, ["policy_binding", "expected_policy_uri"])
    evidence_policy_uri = nested_get(report, ["policy_binding", "evidence_policy_uri"])

    return {
        "schema_version_ok": report.get("schema_version") == SCHEMA_VERSION,
        "report_type_ok": report.get("report_type") == REPORT_TYPE,
        "producer_report_ok": report.get("ok") is True,
        "producer_decision_accepted": report.get("producer_decision") == ACCEPTED_DECISION,

        "producer_id_matches": nested_get(report, ["producer", "producer_id"]) == args.expect_producer_id,
        "producer_name_matches": nested_get(report, ["producer", "producer_name"]) == args.expect_producer_name,
        "producer_version_matches": nested_get(report, ["producer", "producer_version"]) == args.expect_producer_version,
        "producer_source_matches": nested_get(report, ["producer", "producer_source"]) == args.expect_producer_source,
        "producer_ci_identity_matches": (
            nested_get(report, ["producer", "ci_workflow_or_job_identity"])
            == args.expect_ci_workflow_or_job_identity
        ),

        "current_run_id_matches": nested_get(report, ["run_binding", "current_run_id"]) == args.expect_current_run_id,
        "current_run_key_matches": nested_get(report, ["run_binding", "current_run_key"]) == args.expect_current_run_key,
        "commit_sha_matches": nested_get(report, ["run_binding", "commit_sha"]) == args.expect_commit_sha,
        "run_release_candidate_matches": (
            nested_get(report, ["run_binding", "release_candidate_id"])
            == args.expect_release_candidate_id
        ),

        "artifact_subject_name_matches": (
            nested_get(report, ["artifact_binding", "subject_name"])
            == args.expect_artifact_subject_name
        ),
        "artifact_subject_sha256_matches": (
            nested_get(report, ["artifact_binding", "subject_sha256"])
            == args.expect_artifact_sha256
        ),
        "artifact_release_candidate_id_matches": (
            nested_get(report, ["artifact_binding", "release_candidate_id"])
            == args.expect_release_candidate_id
        ),
        "artifact_digest_sha256_matches": (
            nested_get(report, ["artifact_binding", "artifact_digest_sha256"])
            == args.expect_artifact_sha256
        ),
        "artifact_subject_digest_flag_matches": (
            nested_get(report, ["artifact_binding", "subject_digest_matches"]) is True
        ),
        "artifact_resource_uri_flag_matches": (
            nested_get(report, ["artifact_binding", "resource_uri_matches"]) is True
        ),
        "artifact_release_candidate_flag_matches": (
            nested_get(report, ["artifact_binding", "release_candidate_matches"]) is True
        ),
        "artifact_digest_flag_matches": (
            nested_get(report, ["artifact_binding", "artifact_digest_matches"]) is True
        ),

        "expected_policy_id_matches": (
            nested_get(report, ["policy_binding", "expected_policy_id"])
            == args.expect_policy_id
        ),
        "expected_policy_sha256_matches": (
            nested_get(report, ["policy_binding", "expected_policy_sha256"])
            == args.expect_policy_sha256
        ),
        "evidence_policy_id_matches": (
            nested_get(report, ["policy_binding", "evidence_policy_id"])
            == args.expect_policy_id
        ),
        "evidence_policy_sha256_matches": (
            nested_get(report, ["policy_binding", "evidence_policy_sha256"])
            == args.expect_policy_sha256
        ),
        "policy_uri_self_consistent": (
            isinstance(expected_policy_uri, str)
            and isinstance(evidence_policy_uri, str)
            and expected_policy_uri == evidence_policy_uri
        ),
        "policy_identity_matches": (
            nested_get(report, ["policy_binding", "policy_identity_matches"]) is True
        ),
        "policy_digest_matches": (
            nested_get(report, ["policy_binding", "policy_digest_matches"]) is True
        ),

        "expected_verifier_id_matches": (
            nested_get(report, ["verifier_binding", "expected_verifier_id"])
            == args.expect_verifier_id
        ),
        "evidence_verifier_id_matches": (
            nested_get(report, ["verifier_binding", "evidence_verifier_id"])
            == args.expect_verifier_id
        ),
        "verifier_trusted": nested_get(report, ["verifier_binding", "verifier_trusted"]) is True,

        "candidate_set_matches": report.get("candidate_set") == args.expect_candidate_set,
        "recorded_signal_mode_ok": report.get("recorded_signal_mode") == "recorded_signal_only",

        "freshness_current_run": nested_get(report, ["freshness", "freshness_result"]) == "fresh_current_run",
        "not_stale_vsa_evidence": nested_get(report, ["freshness", "stale_vsa_evidence"]) is False,
        "no_previous_run_artifact_reuse": nested_get(report, ["freshness", "previous_run_artifact_reuse"]) is False,
        "time_verified_current_run_matches": (
            nested_get(report, ["freshness", "time_verified_current_run_match"]) is True
        ),
        "current_run_binding_ok": nested_get(report, ["freshness", "current_run_binding_ok"]) is True,

        "evidence_sha256_present": isinstance(nested_get(report, ["evidence", "evidence_sha256"]), str),
        "evidence_time_verified_present": isinstance(nested_get(report, ["evidence", "time_verified"]), str),
        "vsa_verification_passed": nested_get(report, ["evidence", "verification_result"]) == "PASSED",
        "expected_verified_level_matches": (
            nested_get(report, ["evidence", "expected_verified_level"])
            == args.expect_verified_level
        ),
        "expected_verified_level_listed": _verified_level_list_contains(report, args.expect_verified_level),
        "verified_level_ok": nested_get(report, ["evidence", "verified_level_ok"]) is True,

        "no_failed_checks": report.get("failed_checks") == [],
    }


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        schema = load_json(Path(args.schema))
        producer_report = load_json(Path(args.report))
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

    errors = validation_errors(schema, producer_report)
    schema_valid = not errors

    if not isinstance(producer_report, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["producer_report_not_object"],
        )
        return diagnostic, 1

    checks = build_checks(args, producer_report)

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
