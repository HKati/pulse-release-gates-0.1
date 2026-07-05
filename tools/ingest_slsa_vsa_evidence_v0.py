#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator


TOOL_NAME = "ingest_slsa_vsa_evidence_v0"

SCHEMA_VERSION = "slsa_vsa_evidence_v0"
EVIDENCE_TYPE = "slsa_vsa"
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
            "Validate a PULSEmech SLSA / in-toto VSA evidence record and "
            "emit a deterministic intake report."
        )
    )
    parser.add_argument("--schema", required=True, help="Path to slsa_vsa_evidence_v0.schema.json")
    parser.add_argument("--evidence", required=True, help="Path to a slsa_vsa_evidence_v0 JSON record")
    parser.add_argument("--expect-subject-name")
    parser.add_argument("--expect-subject-sha256")
    parser.add_argument("--expect-resource-uri")
    parser.add_argument("--expect-verifier-id")
    parser.add_argument("--expect-policy-sha256")
    parser.add_argument("--expect-verified-level")
    parser.add_argument("--output", help="Optional path for the deterministic JSON intake report")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_from_digest(digest: Any) -> Optional[str]:
    if isinstance(digest, dict):
        value = digest.get("sha256")
        if isinstance(value, str):
            return value
    return None


def subject_matches(subjects: Any, expected_name: str, expected_sha256: str) -> bool:
    if not isinstance(subjects, list):
        return False

    for subject in subjects:
        if not isinstance(subject, dict):
            continue

        name_ok = subject.get("name") == expected_name
        digest_ok = sha256_from_digest(subject.get("digest")) == expected_sha256

        if name_ok and digest_ok:
            return True

    return False


def policy_digest_matches(policy: Any, expected_sha256: str) -> bool:
    if not isinstance(policy, dict):
        return False

    return sha256_from_digest(policy.get("digest")) == expected_sha256


def verified_level_ok(verified_levels: Any, expected_level: str) -> bool:
    return isinstance(verified_levels, list) and expected_level in verified_levels


def literal_boolean_signals(signals: Any) -> bool:
    if not isinstance(signals, dict):
        return False

    return all(isinstance(signals.get(signal), bool) for signal in REQUIRED_PULSE_SIGNALS)


def required_signals_true(signals: Any) -> bool:
    if not isinstance(signals, dict):
        return False

    return all(signals.get(signal) is True for signal in REQUIRED_PULSE_SIGNALS)


def make_report(
    *,
    ok: bool,
    schema_version: Optional[str],
    evidence_type: Optional[str],
    checks: dict[str, bool],
    pulse_signals: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": ok,
        "schema_version": schema_version,
        "evidence_type": evidence_type,
        "signature_verification_mode": "recorded_signal_only",
        "checks": checks,
        "pulse_signals": pulse_signals,
        "errors": errors,
    }


def empty_checks() -> dict[str, bool]:
    return {
        "schema_valid": False,
        "evidence_valid": False,
        "contract_fields_ok": False,
        "predicate_type_ok": False,
        "verification_result_passed": False,
        "subject_matches_artifact": False,
        "resource_uri_matches": False,
        "verifier_trusted": False,
        "policy_digest_matches": False,
        "verified_level_ok": False,
        "pulse_signals_literal_booleans": False,
        "pulse_signals_required_true": False,
        "pulse_signals_consistent": False,
    }


def emit_report(report: dict[str, Any], output: Optional[Path]) -> None:
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def validation_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.path)
    return path or "<root>"


def schema_validation_errors(schema: dict[str, Any], evidence: Any) -> list[str]:
    validator = Draft202012Validator(schema)
    validation_errors = sorted(
        validator.iter_errors(evidence),
        key=lambda err: tuple(str(part) for part in err.path),
    )

    return [
        f"evidence_invalid[{validation_path(error)}]: {error.message}"
        for error in validation_errors
    ]


def require_expectation(value: Optional[str], flag_name: str, errors: list[str]) -> Optional[str]:
    if value is None:
        errors.append(f"expectation_missing: {flag_name}")
        return None

    return value


def build_intake_report(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    checks = empty_checks()
    errors: list[str] = []

    try:
        schema = load_json(Path(args.schema))
        evidence = load_json(Path(args.evidence))
    except Exception as exc:
        errors.append(f"read_error: {exc}")
        report = make_report(
            ok=False,
            schema_version=None,
            evidence_type=None,
            checks=checks,
            pulse_signals={},
            errors=errors,
        )
        return report, 2

    schema_version = evidence.get("schema_version") if isinstance(evidence, dict) else None
    evidence_type = evidence.get("evidence_type") if isinstance(evidence, dict) else None
    pulse_signals = evidence.get("pulse_signals", {}) if isinstance(evidence, dict) else {}

    try:
        Draft202012Validator.check_schema(schema)
        checks["schema_valid"] = True
    except Exception as exc:
        errors.append(f"schema_invalid: {exc}")

    if checks["schema_valid"]:
        evidence_errors = schema_validation_errors(schema, evidence)
        if evidence_errors:
            errors.extend(evidence_errors)
        else:
            checks["evidence_valid"] = True

    raw_vsa = evidence.get("vsa") if isinstance(evidence, dict) else None
    if not isinstance(raw_vsa, dict):
        errors.append("vsa_not_object")
        vsa: dict[str, Any] = {}
    else:
        vsa = raw_vsa

    raw_predicate = vsa.get("predicate")
    if not isinstance(raw_predicate, dict):
        errors.append("predicate_not_object")
        predicate: dict[str, Any] = {}
    else:
        predicate = raw_predicate

    checks["contract_fields_ok"] = (
        schema_version == SCHEMA_VERSION
        and evidence_type == EVIDENCE_TYPE
        and vsa.get("_type") == IN_TOTO_STATEMENT_V1
        and vsa.get("predicateType") == SLSA_VSA_PREDICATE_TYPE_V1
    )

    checks["predicate_type_ok"] = vsa.get("predicateType") == SLSA_VSA_PREDICATE_TYPE_V1
    checks["verification_result_passed"] = predicate.get("verificationResult") == "PASSED"

    expected_subject_name = require_expectation(
        args.expect_subject_name,
        "--expect-subject-name",
        errors,
    )
    expected_subject_sha256 = require_expectation(
        args.expect_subject_sha256,
        "--expect-subject-sha256",
        errors,
    )

    if expected_subject_name is not None and expected_subject_sha256 is not None:
        checks["subject_matches_artifact"] = subject_matches(
            vsa.get("subject"),
            expected_subject_name,
            expected_subject_sha256,
        )
    else:
        checks["subject_matches_artifact"] = False

    expected_resource_uri = require_expectation(
        args.expect_resource_uri,
        "--expect-resource-uri",
        errors,
    )
    if expected_resource_uri is not None:
        checks["resource_uri_matches"] = predicate.get("resourceUri") == expected_resource_uri
    else:
        checks["resource_uri_matches"] = False

    raw_verifier = predicate.get("verifier")
    if not isinstance(raw_verifier, dict):
        errors.append("verifier_not_object")
        verifier: dict[str, Any] = {}
    else:
        verifier = raw_verifier

    expected_verifier_id = require_expectation(
        args.expect_verifier_id,
        "--expect-verifier-id",
        errors,
    )
    if expected_verifier_id is not None:
        checks["verifier_trusted"] = verifier.get("id") == expected_verifier_id
    else:
        checks["verifier_trusted"] = False

    raw_policy = predicate.get("policy")
    if not isinstance(raw_policy, dict):
        errors.append("policy_not_object")
        policy: dict[str, Any] = {}
    else:
        policy = raw_policy

    expected_policy_sha256 = require_expectation(
        args.expect_policy_sha256,
        "--expect-policy-sha256",
        errors,
    )
    if expected_policy_sha256 is not None:
        checks["policy_digest_matches"] = policy_digest_matches(
            policy,
            expected_policy_sha256,
        )
    else:
        checks["policy_digest_matches"] = False

    expected_verified_level = require_expectation(
        args.expect_verified_level,
        "--expect-verified-level",
        errors,
    )
    if expected_verified_level is not None:
        checks["verified_level_ok"] = verified_level_ok(
            predicate.get("verifiedLevels"),
            expected_verified_level,
        )
    else:
        checks["verified_level_ok"] = False

    checks["pulse_signals_literal_booleans"] = literal_boolean_signals(pulse_signals)
    checks["pulse_signals_required_true"] = required_signals_true(pulse_signals)

    expected_signal_values = {
        "slsa_vsa_present": True,
        "slsa_vsa_subject_matches_artifact": checks["subject_matches_artifact"],
        "slsa_vsa_predicate_type_ok": checks["predicate_type_ok"],
        "slsa_vsa_verifier_trusted": checks["verifier_trusted"],
        "slsa_vsa_resource_uri_matches": checks["resource_uri_matches"],
        "slsa_vsa_policy_digest_matches": checks["policy_digest_matches"],
        "slsa_vsa_result_passed": checks["verification_result_passed"],
        "slsa_vsa_verified_level_ok": checks["verified_level_ok"],
    }

    signal_consistency_errors: list[str] = []
    if isinstance(pulse_signals, dict):
        for signal, expected_value in expected_signal_values.items():
            if pulse_signals.get(signal) is not expected_value:
                signal_consistency_errors.append(
                    "pulse_signal_inconsistent: "
                    f"{signal} recorded={pulse_signals.get(signal)!r} expected={expected_value!r}"
                )

        if pulse_signals.get("slsa_vsa_signature_ok") is not True:
            signal_consistency_errors.append(
                "pulse_signal_inconsistent: "
                "slsa_vsa_signature_ok must be recorded as literal true for this intake"
            )
    else:
        signal_consistency_errors.append("pulse_signals_not_object")

    if signal_consistency_errors:
        errors.extend(signal_consistency_errors)
    else:
        checks["pulse_signals_consistent"] = True

    for check_name, passed in checks.items():
        if not passed:
            errors.append(f"check_failed: {check_name}")

    ok = not errors

    report = make_report(
        ok=ok,
        schema_version=schema_version if isinstance(schema_version, str) else None,
        evidence_type=evidence_type if isinstance(evidence_type, str) else None,
        checks=checks,
        pulse_signals=pulse_signals if isinstance(pulse_signals, dict) else {},
        errors=errors,
    )

    return report, 0 if ok else 1


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else None

    if output is not None and output.name == "status.json":
        report = make_report(
            ok=False,
            schema_version=None,
            evidence_type=None,
            checks=empty_checks(),
            pulse_signals={},
            errors=["refusing_to_write_status_json"],
        )
        emit_report(report, None)
        return 2

    report, exit_code = build_intake_report(args)
    emit_report(report, output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
