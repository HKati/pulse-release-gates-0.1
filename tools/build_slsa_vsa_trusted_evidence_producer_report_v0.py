#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "slsa_vsa_trusted_evidence_producer_report_v0"
REPORT_TYPE = "slsa_vsa_trusted_evidence_producer_report"
ACCEPTED = "TRUSTED_EVIDENCE_ACCEPTED"
REJECTED = "TRUSTED_EVIDENCE_REJECTED"
RECORDED_MODE = "recorded_signal_only"
CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"

EVIDENCE_SCHEMA = "slsa_vsa_evidence_v0"
EVIDENCE_TYPE = "slsa_vsa"
IN_TOTO_V1 = "https://in-toto.io/Statement/v1"
VSA_PREDICATE = "https://slsa.dev/verification_summary/v1"

SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
DATE_TIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"
)

REQUIRED_SIGNALS = [
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
    p = argparse.ArgumentParser(
        description="Build a deterministic SLSA VSA trusted evidence producer report."
    )
    p.add_argument("--evidence", required=True)
    p.add_argument("--created-utc", required=True)
    p.add_argument("--producer-id", required=True)
    p.add_argument("--producer-name", required=True)
    p.add_argument("--producer-version", required=True)
    p.add_argument("--producer-source", required=True)
    p.add_argument("--ci-workflow-or-job-identity", required=True)
    p.add_argument("--current-run-id", required=True)
    p.add_argument("--current-run-number", required=True)
    p.add_argument("--current-run-attempt", required=True)
    p.add_argument("--workflow-name", required=True)
    p.add_argument("--job-name", required=True)
    p.add_argument("--commit-sha", required=True)
    p.add_argument("--release-candidate-id", required=True)
    p.add_argument("--artifact-subject-name", required=True)
    p.add_argument("--artifact-sha256", required=True)
    p.add_argument("--artifact-resource-uri", required=True)
    p.add_argument("--policy-id", required=True)
    p.add_argument("--policy-uri", required=True)
    p.add_argument("--policy-sha256", required=True)
    p.add_argument("--verifier-id", required=True)
    p.add_argument("--expected-verified-level", required=True)
    p.add_argument("--expect-time-verified", required=True)
    p.add_argument("--output")
    return p.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def is_date_time(value: Any) -> bool:
    return isinstance(value, str) and DATE_TIME.fullmatch(value) is not None


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def digest_sha256(value: Any) -> str | None:
    if isinstance(value, dict) and is_sha256(value.get("sha256")):
        return value["sha256"]
    return None


def get(data: Any, *path: str) -> Any:
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def run_key(a: argparse.Namespace) -> str:
    return (
        f"GITHUB_RUN_ID={a.current_run_id}"
        f"|GITHUB_RUN_NUMBER={a.current_run_number}"
        f"|GITHUB_RUN_ATTEMPT={a.current_run_attempt}"
        f"|GITHUB_WORKFLOW={a.workflow_name}"
    )


def first_subject(subjects: Any) -> dict[str, Any]:
    if isinstance(subjects, list):
        for subject in subjects:
            if isinstance(subject, dict):
                return subject
    return {}


def subject_named(subjects: Any, name: str) -> dict[str, Any]:
    if isinstance(subjects, list):
        for subject in subjects:
            if isinstance(subject, dict) and subject.get("name") == name:
                return subject
    return {}


def string_list(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value
    return None


def signals_present(signals: Any) -> bool:
    return isinstance(signals, dict) and all(name in signals for name in REQUIRED_SIGNALS)


def signals_boolean(signals: Any) -> bool:
    return isinstance(signals, dict) and all(isinstance(signals.get(name), bool) for name in REQUIRED_SIGNALS)


def signals_match(signals: Any, expected: dict[str, bool]) -> bool:
    if not isinstance(signals, dict):
        return False
    return all(signals.get(name) is value for name, value in expected.items())


def evidence_parts(evidence: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Any]:
    vsa = evidence.get("vsa") if isinstance(evidence, dict) else None
    vsa = vsa if isinstance(vsa, dict) else {}
    predicate = vsa.get("predicate")
    predicate = predicate if isinstance(predicate, dict) else {}
    policy = predicate.get("policy")
    policy = policy if isinstance(policy, dict) else {}
    verifier = predicate.get("verifier")
    verifier = verifier if isinstance(verifier, dict) else {}
    return vsa, predicate, policy, verifier, evidence.get("pulse_signals") if isinstance(evidence, dict) else None


def build_checks(a: argparse.Namespace, evidence: dict[str, Any] | None, readable: bool) -> dict[str, bool]:
    vsa, pred, policy, verifier, signals = evidence_parts(evidence)
    subject = subject_named(vsa.get("subject"), a.artifact_subject_name)
    subject_sha = digest_sha256(subject.get("digest")) if subject else None
    subject_ok = bool(subject) and subject_sha == a.artifact_sha256
    levels = pred.get("verifiedLevels")
    policy_uri = policy.get("uri")
    policy_sha = digest_sha256(policy.get("digest"))

    checks = {
        "evidence_readable": readable,
        "schema_version_ok": get(evidence, "schema_version") == EVIDENCE_SCHEMA,
        "evidence_type_ok": get(evidence, "evidence_type") == EVIDENCE_TYPE,
        "in_toto_statement_ok": vsa.get("_type") == IN_TOTO_V1,
        "predicate_type_ok": vsa.get("predicateType") == VSA_PREDICATE,
        "verification_result_passed": pred.get("verificationResult") == "PASSED",
        "subject_name_matches": bool(subject),
        "subject_sha256_matches": subject_sha == a.artifact_sha256,
        "resource_uri_matches": pred.get("resourceUri") == a.artifact_resource_uri,
        "release_candidate_present": bool(a.release_candidate_id),
        "artifact_digest_matches": subject_ok,
        "policy_id_bound": bool(a.policy_id) and policy_uri == a.policy_uri,
        "policy_uri_matches": policy_uri == a.policy_uri,
        "policy_digest_matches": policy_sha == a.policy_sha256,
        "verifier_id_matches": verifier.get("id") == a.verifier_id,
        "verified_level_present": isinstance(levels, list) and bool(levels),
        "verified_level_ok": isinstance(levels, list) and a.expected_verified_level in levels,
        "time_verified_present": is_date_time(pred.get("timeVerified")),
        "time_verified_current_run_match": pred.get("timeVerified") == a.expect_time_verified,
        "pulse_signals_present": signals_present(signals),
        "pulse_signals_literal_booleans": signals_boolean(signals),
    }

    expected_signals = {
        "slsa_vsa_present": True,
        "slsa_vsa_signature_ok": True,
        "slsa_vsa_subject_matches_artifact": subject_ok,
        "slsa_vsa_predicate_type_ok": checks["predicate_type_ok"],
        "slsa_vsa_verifier_trusted": checks["verifier_id_matches"],
        "slsa_vsa_resource_uri_matches": checks["resource_uri_matches"],
        "slsa_vsa_policy_digest_matches": checks["policy_digest_matches"],
        "slsa_vsa_result_passed": checks["verification_result_passed"],
        "slsa_vsa_verified_level_ok": checks["verified_level_ok"],
    }

    checks["pulse_signals_consistent"] = signals_match(signals, expected_signals)
    checks["recorded_signal_mode_ok"] = RECORDED_MODE == "recorded_signal_only"
    checks["candidate_set_ok"] = CANDIDATE_SET == "slsa_vsa_recorded_intake_candidate"
    checks["current_run_binding_ok"] = (
        checks["evidence_readable"]
        and checks["time_verified_current_run_match"]
        and checks["subject_name_matches"]
        and checks["subject_sha256_matches"]
        and checks["resource_uri_matches"]
        and checks["artifact_digest_matches"]
    )
    return checks


def freshness(path: Path, readable: bool, checks: dict[str, bool]) -> tuple[str, bool]:
    if not readable:
        return ("rejected_unreadable_vsa_evidence", False) if path.exists() else ("rejected_missing_vsa_evidence", False)
    if not checks["time_verified_present"]:
        return "rejected_ambiguous_freshness", False
    if not checks["time_verified_current_run_match"]:
        return "rejected_time_verified_current_run_mismatch", False
    artifact_reuse = not (
        checks["subject_name_matches"]
        and checks["subject_sha256_matches"]
        and checks["resource_uri_matches"]
        and checks["artifact_digest_matches"]
    )
    return ("rejected_previous_run_artifact", True) if artifact_reuse else ("fresh_current_run", False)


def report_value(value: Any, expected: str) -> str | None:
    return value if value == expected else None


def make_report(
    a: argparse.Namespace,
    evidence: dict[str, Any] | None,
    path: str | None,
    evidence_sha: str | None,
    checks: dict[str, bool],
    failed: list[str],
    freshness_result: str,
    artifact_reuse: bool,
) -> dict[str, Any]:
    vsa, pred, policy, verifier, _signals = evidence_parts(evidence)
    subject = subject_named(vsa.get("subject"), a.artifact_subject_name) or first_subject(vsa.get("subject"))
    subject_name = subject.get("name") if isinstance(subject.get("name"), str) and subject.get("name") else a.artifact_subject_name
    subject_sha = digest_sha256(subject.get("digest")) or a.artifact_sha256
    policy_uri = policy.get("uri") if isinstance(policy.get("uri"), str) and policy.get("uri") else None
    policy_sha = digest_sha256(policy.get("digest"))
    verifier_id = verifier.get("id") if isinstance(verifier.get("id"), str) and verifier.get("id") else None
    time_verified = pred.get("timeVerified") if is_date_time(pred.get("timeVerified")) else None
    result = pred.get("verificationResult") if pred.get("verificationResult") in ["PASSED", "FAILED"] else None

    ok = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "created_utc": a.created_utc,
        "producer": {
            "producer_id": a.producer_id,
            "producer_name": a.producer_name,
            "producer_version": a.producer_version,
            "producer_source": a.producer_source,
            "ci_workflow_or_job_identity": a.ci_workflow_or_job_identity,
        },
        "run_binding": {
            "current_run_id": a.current_run_id,
            "current_run_number": a.current_run_number,
            "current_run_attempt": a.current_run_attempt,
            "current_run_key": run_key(a),
            "workflow_name": a.workflow_name,
            "job_name": a.job_name,
            "commit_sha": a.commit_sha,
            "release_candidate_id": a.release_candidate_id,
        },
        "artifact_binding": {
            "subject_name": subject_name,
            "subject_sha256": subject_sha,
            "resource_uri": a.artifact_resource_uri,
            "release_candidate_id": a.release_candidate_id,
            "artifact_digest_sha256": a.artifact_sha256,
            "subject_digest_matches": checks.get("subject_name_matches", False) and checks.get("subject_sha256_matches", False),
            "resource_uri_matches": checks.get("resource_uri_matches", False),
            "release_candidate_matches": checks.get("release_candidate_present", False),
            "artifact_digest_matches": checks.get("artifact_digest_matches", False),
        },
        "policy_binding": {
            "expected_policy_id": a.policy_id,
            "expected_policy_uri": a.policy_uri,
            "expected_policy_sha256": a.policy_sha256,
            "evidence_policy_id": a.policy_id if checks.get("policy_id_bound", False) else None,
            "evidence_policy_uri": policy_uri,
            "evidence_policy_sha256": policy_sha,
            "policy_identity_matches": checks.get("policy_id_bound", False) and checks.get("policy_uri_matches", False),
            "policy_digest_matches": checks.get("policy_digest_matches", False),
        },
        "verifier_binding": {
            "expected_verifier_id": a.verifier_id,
            "evidence_verifier_id": verifier_id,
            "verifier_trusted": checks.get("verifier_id_matches", False),
        },
        "evidence": {
            "evidence_path": path,
            "evidence_sha256": evidence_sha,
            "evidence_schema_version": report_value(get(evidence, "schema_version"), EVIDENCE_SCHEMA),
            "evidence_type": report_value(get(evidence, "evidence_type"), EVIDENCE_TYPE),
            "time_verified": time_verified,
            "verification_result": result,
            "expected_verified_level": a.expected_verified_level,
            "evidence_verified_levels": string_list(pred.get("verifiedLevels")),
            "verified_level_ok": checks.get("verified_level_ok", False),
        },
        "freshness": {
            "freshness_result": freshness_result,
            "stale_vsa_evidence": freshness_result == "rejected_stale_vsa",
            "previous_run_artifact_reuse": artifact_reuse,
            "time_verified_current_run_match": checks.get("time_verified_current_run_match", False),
            "current_run_binding_ok": checks.get("current_run_binding_ok", False),
        },
        "recorded_signal_mode": RECORDED_MODE,
        "candidate_set": CANDIDATE_SET,
        "producer_decision": ACCEPTED if ok else REJECTED,
        "ok": ok,
        "failed_checks": failed,
        "warnings": [],
    }


def emit(report: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    sys.stdout.write(text)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def build_report(a: argparse.Namespace) -> tuple[dict[str, Any], int]:
    evidence_path = Path(a.evidence)
    evidence: dict[str, Any] | None = None
    readable = False

    try:
        loaded = read_json(evidence_path)
        if isinstance(loaded, dict):
            evidence = loaded
            readable = True
    except Exception:
        pass

    checks = build_checks(a, evidence, readable)
    failed = [name for name, passed in checks.items() if not passed]
    freshness_result, artifact_reuse = freshness(evidence_path, readable, checks)
    report = make_report(
        a,
        evidence,
        str(evidence_path) if readable else None,
        file_sha256(evidence_path) if readable else None,
        checks,
        failed,
        freshness_result,
        artifact_reuse,
    )
    return report, 0 if report["ok"] else 1


def refusal_report(a: argparse.Namespace) -> dict[str, Any]:
    checks = build_checks(a, None, False)
    return make_report(
        a,
        None,
        None,
        None,
        checks,
        ["refusing_to_write_status_json"],
        "rejected_missing_vsa_evidence",
        False,
    )


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None
    if output is not None and output.name == "status.json":
        emit(refusal_report(args), None)
        return 2

    report, code = build_report(args)
    emit(report, output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
