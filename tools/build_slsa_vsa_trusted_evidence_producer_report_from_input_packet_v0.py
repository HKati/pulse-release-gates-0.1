#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "build_slsa_vsa_trusted_evidence_producer_report_from_input_packet_v0"

EVIDENCE_SCHEMA_VERSION = "slsa_vsa_evidence_v0"
EVIDENCE_TYPE = "slsa_vsa"

REPORT_SCHEMA_VERSION = "slsa_vsa_trusted_evidence_producer_report_v0"
REPORT_TYPE = "slsa_vsa_trusted_evidence_producer_report"

ACCEPTED_DECISION = "TRUSTED_EVIDENCE_ACCEPTED"
REJECTED_DECISION = "TRUSTED_EVIDENCE_REJECTED"

RECORDED_SIGNAL_MODE = "recorded_signal_only"
CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"

IN_TOTO_STATEMENT_V1 = "https://in-toto.io/Statement/v1"
SLSA_VSA_PREDICATE_TYPE_V1 = "https://slsa.dev/verification_summary/v1"


REQUIRED_PULSE_SIGNALS = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a SLSA VSA trusted evidence producer report from "
            "schema-valid evidence and a validated input packet."
        )
    )

    parser.add_argument("--evidence-schema", required=True)
    parser.add_argument("--evidence", required=True)

    parser.add_argument("--input-packet-schema", required=True)
    parser.add_argument("--input-packet", required=True)
    parser.add_argument("--input-packet-validator", required=True)

    parser.add_argument("--report-schema", required=True)
    parser.add_argument("--report-validator", required=True)

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
    parser.add_argument("--output")

    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def nested_get(data: Any, path: list[str]) -> Any:
    cursor = data
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def digest_sha256(digest: Any) -> str | None:
    if not isinstance(digest, dict):
        return None

    value = digest.get("sha256")
    if isinstance(value, str) and value:
        return value

    return None


def string_list(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value

    return None


def validation_errors(schema: dict[str, Any], instance: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )

    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    ]


def load_and_validate(
    *,
    schema_path: Path,
    instance_path: Path,
    label: str,
) -> tuple[Any | None, bool, list[str]]:
    try:
        schema = load_json(schema_path)
        instance = load_json(instance_path)
    except Exception as exc:
        return None, False, [f"{label}_read_error: {exc}"]

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return instance, False, [f"{label}_schema_invalid: {exc}"]

    errors = validation_errors(schema, instance)
    return instance, not errors, [f"{label}_{error}" for error in errors]


def make_diagnostic(errors: list[str], exit_kind: str = "build_error") -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": False,
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "exit_kind": exit_kind,
        "errors": errors,
    }


def emit_json(data: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def run_command_json(command: list[str]) -> tuple[bool, dict[str, Any] | None, list[str]]:
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as exc:
        return False, None, [f"subprocess_error: {exc}"]

    parsed: dict[str, Any] | None = None
    parse_errors: list[str] = []

    if result.stdout:
        try:
            loaded = json.loads(result.stdout)
            if isinstance(loaded, dict):
                parsed = loaded
            else:
                parse_errors.append("subprocess_stdout_not_object")
        except Exception as exc:
            parse_errors.append(f"subprocess_stdout_json_error: {exc}")
    else:
        parse_errors.append("subprocess_stdout_empty")

    errors: list[str] = []
    if result.returncode != 0:
        errors.append(f"subprocess_exit_code: {result.returncode}")

    if result.stderr and "Traceback" in result.stderr:
        errors.append("subprocess_traceback_seen")

    errors.extend(parse_errors)

    ok = result.returncode == 0 and not errors
    return ok, parsed, errors


def packet_validator_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(Path(args.input_packet_validator)),
        "--schema",
        args.input_packet_schema,
        "--packet",
        args.input_packet,
        "--expect-producer-id",
        args.expect_producer_id,
        "--expect-producer-name",
        args.expect_producer_name,
        "--expect-producer-version",
        args.expect_producer_version,
        "--expect-producer-source",
        args.expect_producer_source,
        "--expect-ci-workflow-or-job-identity",
        args.expect_ci_workflow_or_job_identity,
        "--expect-current-run-id",
        args.expect_current_run_id,
        "--expect-current-run-key",
        args.expect_current_run_key,
        "--expect-commit-sha",
        args.expect_commit_sha,
        "--expect-release-candidate-id",
        args.expect_release_candidate_id,
        "--expect-artifact-subject-name",
        args.expect_artifact_subject_name,
        "--expect-artifact-sha256",
        args.expect_artifact_sha256,
        "--expect-artifact-resource-uri",
        args.expect_artifact_resource_uri,
        "--expect-policy-id",
        args.expect_policy_id,
        "--expect-policy-uri",
        args.expect_policy_uri,
        "--expect-policy-sha256",
        args.expect_policy_sha256,
        "--expect-verifier-id",
        args.expect_verifier_id,
        "--expect-verified-level",
        args.expect_verified_level,
        "--expect-time-verified",
        args.expect_time_verified,
        "--expect-candidate-set",
        args.expect_candidate_set,
    ]


def report_validator_command(args: argparse.Namespace, report_path: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(args.report_validator)),
        "--schema",
        args.report_schema,
        "--report",
        str(report_path),
        "--expect-producer-id",
        args.expect_producer_id,
        "--expect-producer-name",
        args.expect_producer_name,
        "--expect-producer-version",
        args.expect_producer_version,
        "--expect-producer-source",
        args.expect_producer_source,
        "--expect-ci-workflow-or-job-identity",
        args.expect_ci_workflow_or_job_identity,
        "--expect-current-run-id",
        args.expect_current_run_id,
        "--expect-current-run-key",
        args.expect_current_run_key,
        "--expect-commit-sha",
        args.expect_commit_sha,
        "--expect-release-candidate-id",
        args.expect_release_candidate_id,
        "--expect-artifact-subject-name",
        args.expect_artifact_subject_name,
        "--expect-artifact-sha256",
        args.expect_artifact_sha256,
        "--expect-policy-id",
        args.expect_policy_id,
        "--expect-policy-sha256",
        args.expect_policy_sha256,
        "--expect-verifier-id",
        args.expect_verifier_id,
        "--expect-verified-level",
        args.expect_verified_level,
        "--expect-candidate-set",
        args.expect_candidate_set,
    ]


def find_subject(vsa: dict[str, Any], expected_name: str) -> dict[str, Any]:
    subjects = vsa.get("subject")
    if not isinstance(subjects, list):
        return {}

    for subject in subjects:
        if isinstance(subject, dict) and subject.get("name") == expected_name:
            return subject

    return {}


def evidence_parts(evidence: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
    vsa = evidence.get("vsa") if isinstance(evidence, dict) else None
    vsa = vsa if isinstance(vsa, dict) else {}

    predicate = vsa.get("predicate")
    predicate = predicate if isinstance(predicate, dict) else {}

    policy = predicate.get("policy")
    policy = policy if isinstance(policy, dict) else {}

    verifier = predicate.get("verifier")
    verifier = verifier if isinstance(verifier, dict) else {}

    pulse_signals = evidence.get("pulse_signals") if isinstance(evidence, dict) else None

    return vsa, predicate, policy, verifier, pulse_signals


def packet_parts(packet: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    producer = packet.get("producer_identity") if isinstance(packet, dict) else None
    run_binding = packet.get("run_binding") if isinstance(packet, dict) else None
    artifact_binding = packet.get("artifact_binding") if isinstance(packet, dict) else None
    policy_binding = packet.get("policy_binding") if isinstance(packet, dict) else None
    verifier_binding = packet.get("verifier_binding") if isinstance(packet, dict) else None

    return (
        producer if isinstance(producer, dict) else {},
        run_binding if isinstance(run_binding, dict) else {},
        artifact_binding if isinstance(artifact_binding, dict) else {},
        policy_binding if isinstance(policy_binding, dict) else {},
        verifier_binding if isinstance(verifier_binding, dict) else {},
    )


def signals_are_booleans(signals: Any) -> bool:
    if not isinstance(signals, dict):
        return False

    return all(isinstance(signals.get(signal), bool) for signal in REQUIRED_PULSE_SIGNALS)


def signals_match(signals: Any, expected: dict[str, bool]) -> bool:
    if not isinstance(signals, dict):
        return False

    return all(signals.get(signal) is expected_value for signal, expected_value in expected.items())


def build_checks(
    *,
    evidence: dict[str, Any],
    packet: dict[str, Any],
    evidence_schema_valid: bool,
    packet_validator_ok: bool,
) -> dict[str, bool]:
    vsa, predicate, policy, verifier, signals = evidence_parts(evidence)
    _producer, run_binding, artifact_binding, policy_binding, verifier_binding = packet_parts(packet)

    subject_name = artifact_binding.get("subject_name")
    subject = find_subject(vsa, subject_name if isinstance(subject_name, str) else "")
    subject_sha256 = digest_sha256(subject.get("digest")) if subject else None

    artifact_subject_sha256 = artifact_binding.get("subject_sha256")
    artifact_digest_sha256 = artifact_binding.get("artifact_digest_sha256")
    artifact_resource_uri = artifact_binding.get("resource_uri")

    evidence_policy_id = policy.get("id")
    evidence_policy_uri = policy.get("uri")
    evidence_policy_sha256 = digest_sha256(policy.get("digest"))

    expected_policy_id = policy_binding.get("expected_policy_id")
    expected_policy_uri = policy_binding.get("expected_policy_uri")
    expected_policy_sha256 = policy_binding.get("expected_policy_sha256")

    evidence_verifier_id = verifier.get("id")
    expected_verifier_id = verifier_binding.get("expected_verifier_id")

    evidence_verified_levels = predicate.get("verifiedLevels")
    expected_verified_level = packet.get("expected_verified_level")

    time_verified = predicate.get("timeVerified")
    expected_time_verified = nested_get(packet, ["freshness", "expected_time_verified"])
    freshness_epoch = nested_get(packet, ["freshness", "freshness_epoch"])
    freshness_epoch_current = freshness_epoch == "current_run"

    subject_name_matches = isinstance(subject_name, str) and bool(subject)
    subject_sha256_matches = (
        isinstance(artifact_subject_sha256, str)
        and subject_sha256 == artifact_subject_sha256
    )
    artifact_digest_matches = (
        isinstance(artifact_digest_sha256, str)
        and subject_sha256 == artifact_digest_sha256
    )
    resource_uri_matches = predicate.get("resourceUri") == artifact_resource_uri
    release_candidate_matches = (
        artifact_binding.get("release_candidate_id") == run_binding.get("release_candidate_id")
    )

    policy_identity_matches = (
        isinstance(evidence_policy_id, str)
        and evidence_policy_id == expected_policy_id
        and isinstance(evidence_policy_uri, str)
        and evidence_policy_uri == expected_policy_uri
    )
    policy_digest_matches = (
        isinstance(evidence_policy_sha256, str)
        and evidence_policy_sha256 == expected_policy_sha256
    )
    verifier_trusted = (
        isinstance(evidence_verifier_id, str)
        and evidence_verifier_id == expected_verifier_id
    )
    verified_level_ok = (
        isinstance(evidence_verified_levels, list)
        and isinstance(expected_verified_level, str)
        and expected_verified_level in evidence_verified_levels
    )
    verification_result_passed = predicate.get("verificationResult") == "PASSED"
    predicate_type_ok = vsa.get("predicateType") == SLSA_VSA_PREDICATE_TYPE_V1
    contract_fields_ok = (
        evidence.get("schema_version") == EVIDENCE_SCHEMA_VERSION
        and evidence.get("evidence_type") == EVIDENCE_TYPE
        and vsa.get("_type") == IN_TOTO_STATEMENT_V1
        and predicate_type_ok
    )
    time_verified_matches = (
        isinstance(time_verified, str)
        and time_verified == expected_time_verified
    )

    expected_signals = {
        "slsa_vsa_present": True,
        "slsa_vsa_signature_ok": True,
        "slsa_vsa_subject_matches_artifact": subject_name_matches and subject_sha256_matches,
        "slsa_vsa_predicate_type_ok": predicate_type_ok,
        "slsa_vsa_verifier_trusted": verifier_trusted,
        "slsa_vsa_resource_uri_matches": resource_uri_matches,
        "slsa_vsa_policy_digest_matches": policy_digest_matches,
        "slsa_vsa_result_passed": verification_result_passed,
        "slsa_vsa_verified_level_ok": verified_level_ok,
    }

    return {
        "evidence_schema_valid": evidence_schema_valid,
        "input_packet_validator_ok": packet_validator_ok,
        "contract_fields_ok": contract_fields_ok,
        "subject_name_matches": subject_name_matches,
        "subject_sha256_matches": subject_sha256_matches,
        "resource_uri_matches": resource_uri_matches,
        "release_candidate_matches": release_candidate_matches,
        "artifact_digest_matches": artifact_digest_matches,
        "policy_identity_matches": policy_identity_matches,
        "policy_digest_matches": policy_digest_matches,
        "verifier_trusted": verifier_trusted,
        "verification_result_passed": verification_result_passed,
        "verified_level_ok": verified_level_ok,
        "time_verified_current_run_match": time_verified_matches,
        "freshness_epoch_current": freshness_epoch_current,
        "pulse_signals_literal_booleans": signals_are_booleans(signals),
        "pulse_signals_consistent": signals_match(signals, expected_signals),
        "recorded_signal_mode_ok": packet.get("recorded_signal_mode") == RECORDED_SIGNAL_MODE,
        "candidate_set_matches": packet.get("candidate_set") == CANDIDATE_SET,
    }


def freshness_result(checks: dict[str, bool]) -> tuple[str, bool]:
    if not checks.get("evidence_schema_valid", False):
        return "rejected_ambiguous_freshness", False

    if not checks.get("freshness_epoch_current", False):
        return "rejected_stale_vsa", False

    if not checks.get("time_verified_current_run_match", False):
        return "rejected_time_verified_current_run_mismatch", False

    artifact_ok = (
        checks.get("subject_name_matches", False)
        and checks.get("subject_sha256_matches", False)
        and checks.get("resource_uri_matches", False)
        and checks.get("artifact_digest_matches", False)
    )

    if not artifact_ok:
        return "rejected_previous_run_artifact", True

    return "fresh_current_run", False


def build_report(
    *,
    args: argparse.Namespace,
    evidence: dict[str, Any],
    packet: dict[str, Any],
    evidence_sha256: str | None,
    failed_checks: list[str],
    checks: dict[str, bool],
) -> dict[str, Any]:
    producer, run_binding, artifact_binding, policy_binding, verifier_binding = packet_parts(packet)
    _vsa, predicate, policy, verifier, _signals = evidence_parts(evidence)

    evidence_policy_id = policy.get("id") if isinstance(policy.get("id"), str) else None
    evidence_policy_uri = policy.get("uri") if isinstance(policy.get("uri"), str) else None
    evidence_policy_sha256 = digest_sha256(policy.get("digest"))

    evidence_verifier_id = verifier.get("id") if isinstance(verifier.get("id"), str) else None

    freshness, previous_run_artifact_reuse = freshness_result(checks)
    ok = not failed_checks

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "created_utc": packet.get("created_utc"),
        "producer": {
            "producer_id": producer.get("producer_id"),
            "producer_name": producer.get("producer_name"),
            "producer_version": producer.get("producer_version"),
            "producer_source": producer.get("producer_source"),
            "ci_workflow_or_job_identity": producer.get("ci_workflow_or_job_identity"),
        },
        "run_binding": {
            "current_run_id": run_binding.get("current_run_id"),
            "current_run_number": run_binding.get("current_run_number"),
            "current_run_attempt": run_binding.get("current_run_attempt"),
            "current_run_key": run_binding.get("current_run_key"),
            "workflow_name": run_binding.get("workflow_name"),
            "job_name": run_binding.get("job_name"),
            "commit_sha": run_binding.get("commit_sha"),
            "release_candidate_id": run_binding.get("release_candidate_id"),
        },
        "artifact_binding": {
            "subject_name": artifact_binding.get("subject_name"),
            "subject_sha256": artifact_binding.get("subject_sha256"),
            "resource_uri": artifact_binding.get("resource_uri"),
            "release_candidate_id": artifact_binding.get("release_candidate_id"),
            "artifact_digest_sha256": artifact_binding.get("artifact_digest_sha256"),
            "subject_digest_matches": (
                checks.get("subject_name_matches", False)
                and checks.get("subject_sha256_matches", False)
            ),
            "resource_uri_matches": checks.get("resource_uri_matches", False),
            "release_candidate_matches": checks.get("release_candidate_matches", False),
            "artifact_digest_matches": checks.get("artifact_digest_matches", False),
        },
        "policy_binding": {
            "expected_policy_id": policy_binding.get("expected_policy_id"),
            "expected_policy_uri": policy_binding.get("expected_policy_uri"),
            "expected_policy_sha256": policy_binding.get("expected_policy_sha256"),
            "evidence_policy_id": evidence_policy_id,
            "evidence_policy_uri": evidence_policy_uri,
            "evidence_policy_sha256": evidence_policy_sha256,
            "policy_identity_matches": checks.get("policy_identity_matches", False),
            "policy_digest_matches": checks.get("policy_digest_matches", False),
        },
        "verifier_binding": {
            "expected_verifier_id": verifier_binding.get("expected_verifier_id"),
            "evidence_verifier_id": evidence_verifier_id,
            "verifier_trusted": checks.get("verifier_trusted", False),
        },
        "evidence": {
            "evidence_path": args.evidence,
            "evidence_sha256": evidence_sha256,
            "evidence_schema_version": evidence.get("schema_version"),
            "evidence_type": evidence.get("evidence_type"),
            "time_verified": predicate.get("timeVerified"),
            "verification_result": predicate.get("verificationResult"),
            "expected_verified_level": packet.get("expected_verified_level"),
            "evidence_verified_levels": string_list(predicate.get("verifiedLevels")),
            "verified_level_ok": checks.get("verified_level_ok", False),
        },
        "freshness": {
            "freshness_result": freshness,
            "stale_vsa_evidence": freshness == "rejected_stale_vsa",
            "previous_run_artifact_reuse": previous_run_artifact_reuse,
            "time_verified_current_run_match": checks.get("time_verified_current_run_match", False),
            "current_run_binding_ok": (
                checks.get("input_packet_validator_ok", False)
                and checks.get("freshness_epoch_current", False)
                and checks.get("time_verified_current_run_match", False)
                and freshness == "fresh_current_run"
            ),
        },
        "recorded_signal_mode": RECORDED_SIGNAL_MODE,
        "candidate_set": CANDIDATE_SET,
        "producer_decision": ACCEPTED_DECISION if ok else REJECTED_DECISION,
        "ok": ok,
        "failed_checks": failed_checks,
        "warnings": [],
    }


def report_schema_errors(args: argparse.Namespace, report: dict[str, Any]) -> list[str]:
    try:
        schema = load_json(Path(args.report_schema))
    except Exception as exc:
        return [f"report_schema_read_error: {exc}"]

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return [f"report_schema_invalid: {exc}"]

    return validation_errors(schema, report)


def run_report_validator(args: argparse.Namespace, report: dict[str, Any]) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory() as raw_tmp:
        report_path = Path(raw_tmp) / "producer_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        ok, diagnostic, errors = run_command_json(report_validator_command(args, report_path))

    if diagnostic is not None and diagnostic.get("ok") is not True:
        for error in diagnostic.get("errors", []):
            if isinstance(error, str):
                errors.append(f"producer_report_validator: {error}")

    return ok, errors


def build(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    evidence_path = Path(args.evidence)
    packet_path = Path(args.input_packet)

    packet, packet_schema_valid, packet_schema_errors = load_and_validate(
        schema_path=Path(args.input_packet_schema),
        instance_path=packet_path,
        label="input_packet",
    )
    if not packet_schema_valid or not isinstance(packet, dict):
        return make_diagnostic(packet_schema_errors or ["input_packet_not_object"]), 1

    evidence, evidence_schema_valid, evidence_schema_errors = load_and_validate(
        schema_path=Path(args.evidence_schema),
        instance_path=evidence_path,
        label="evidence",
    )
    if not isinstance(evidence, dict):
        return make_diagnostic(evidence_schema_errors or ["evidence_not_object"]), 1

    packet_validator_ok, packet_validator_report, packet_validator_errors = run_command_json(
        packet_validator_command(args)
    )
    if packet_validator_report is not None and packet_validator_report.get("ok") is not True:
        for error in packet_validator_report.get("errors", []):
            if isinstance(error, str):
                packet_validator_errors.append(f"input_packet_validator: {error}")

    checks = build_checks(
        evidence=evidence,
        packet=packet,
        evidence_schema_valid=evidence_schema_valid,
        packet_validator_ok=packet_validator_ok,
    )

    failed_checks = [name for name, passed in checks.items() if not passed]

    for error in evidence_schema_errors:
        failed_checks.append(error)

    for error in packet_validator_errors:
        failed_checks.append(error)

    report = build_report(
        args=args,
        evidence=evidence,
        packet=packet,
        evidence_sha256=sha256_file(evidence_path),
        failed_checks=failed_checks,
        checks=checks,
    )

    schema_errors = report_schema_errors(args, report)
    if schema_errors:
        return make_diagnostic(schema_errors, exit_kind="generated_report_schema_error"), 1

    if report["ok"] is True:
        validator_ok, validator_errors = run_report_validator(args, report)
        if not validator_ok:
            failed = ["producer_report_validator_ok"] + validator_errors
            report = build_report(
                args=args,
                evidence=evidence,
                packet=packet,
                evidence_sha256=sha256_file(evidence_path),
                failed_checks=failed,
                checks={
                    **checks,
                    "producer_report_validator_ok": False,
                },
            )

            schema_errors = report_schema_errors(args, report)
            if schema_errors:
                return make_diagnostic(schema_errors, exit_kind="generated_rejected_report_schema_error"), 1

            return report, 1

    return report, 0 if report["ok"] else 1


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None

    if output is not None and output.name == "status.json":
        diagnostic = make_diagnostic(["refusing_to_write_status_json"])
        emit_json(diagnostic, None)
        return 2

    report, exit_code = build(args)
    emit_json(report, output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
