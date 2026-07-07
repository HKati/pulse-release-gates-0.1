#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "schemas" / "slsa_vsa_trusted_evidence_producer_report_v0.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_evidence_producer_report_example_v0.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema() -> dict[str, Any]:
    return _load_json(SCHEMA_PATH)


def _accepted_report() -> dict[str, Any]:
    return _load_json(EXAMPLE_PATH)


def _validator() -> jsonschema.Draft202012Validator:
    schema = _schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def _validate(instance: dict[str, Any]) -> None:
    _validator().validate(instance)


def _validation_errors(instance: dict[str, Any]) -> list[str]:
    return [error.message for error in _validator().iter_errors(instance)]


def _rejected_report(failed_check: str) -> dict[str, Any]:
    report = _accepted_report()
    report["ok"] = False
    report["producer_decision"] = "TRUSTED_EVIDENCE_REJECTED"
    report["failed_checks"] = [failed_check]
    return report


def test_schema_and_example_exist() -> None:
    assert SCHEMA_PATH.exists()
    assert EXAMPLE_PATH.exists()


def test_example_validates() -> None:
    _validate(_accepted_report())


def test_schema_version_and_report_type_are_locked() -> None:
    report = _accepted_report()
    report["schema_version"] = "wrong"
    assert _validation_errors(report)

    report = _accepted_report()
    report["report_type"] = "wrong"
    assert _validation_errors(report)


def test_created_utc_requires_date_time() -> None:
    report = _accepted_report()
    report["created_utc"] = "unknown"

    errors = _validation_errors(report)

    assert errors


def test_candidate_set_and_recorded_signal_mode_are_locked() -> None:
    report = _accepted_report()
    report["candidate_set"] = "slsa_vsa_release_required_candidate"
    assert _validation_errors(report)

    report = _accepted_report()
    report["recorded_signal_mode"] = "cryptographic_signature_verified"
    assert _validation_errors(report)


def test_ok_true_requires_accepted_decision_and_no_failed_checks() -> None:
    report = _accepted_report()
    report["producer_decision"] = "TRUSTED_EVIDENCE_REJECTED"
    assert _validation_errors(report)

    report = _accepted_report()
    report["failed_checks"] = ["synthetic_failure"]
    assert _validation_errors(report)


def test_rejected_report_requires_failed_checks() -> None:
    report = _rejected_report("synthetic_failure")

    _validate(report)

    report["failed_checks"] = []
    assert _validation_errors(report)


def test_release_authority_words_are_not_producer_decisions() -> None:
    for bad_decision in ["PASS", "ALLOW", "PROD-PASS", "VERIFIED", "FAILED"]:
        report = _accepted_report()
        report["producer_decision"] = bad_decision
        assert _validation_errors(report), bad_decision


def test_policy_digest_binding_is_required() -> None:
    for field in ["expected_policy_sha256", "evidence_policy_sha256"]:
        report = _accepted_report()
        del report["policy_binding"][field]
        assert _validation_errors(report), field


def test_evidence_policy_identity_is_required() -> None:
    report = _accepted_report()
    del report["policy_binding"]["evidence_policy_id"]

    errors = _validation_errors(report)

    assert errors


def test_policy_uri_only_binding_is_rejected() -> None:
    report = _accepted_report()
    report["policy_binding"]["evidence_policy_id"] = None
    report["policy_binding"]["evidence_policy_sha256"] = None

    errors = _validation_errors(report)

    assert errors


def test_policy_digest_mismatch_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["policy_binding"]["policy_digest_matches"] = False

    errors = _validation_errors(report)

    assert errors


def test_policy_identity_mismatch_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["policy_binding"]["policy_identity_matches"] = False

    errors = _validation_errors(report)

    assert errors


def test_time_verified_requires_date_time() -> None:
    report = _accepted_report()
    report["evidence"]["time_verified"] = "unknown"

    errors = _validation_errors(report)

    assert errors


def test_stale_vsa_evidence_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["freshness"]["freshness_result"] = "rejected_stale_vsa"
    report["freshness"]["stale_vsa_evidence"] = True

    errors = _validation_errors(report)

    assert errors


def test_previous_run_artifact_reuse_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["freshness"]["freshness_result"] = "rejected_previous_run_artifact"
    report["freshness"]["previous_run_artifact_reuse"] = True

    errors = _validation_errors(report)

    assert errors


def test_time_verified_current_run_mismatch_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["freshness"]["freshness_result"] = "rejected_time_verified_current_run_mismatch"
    report["freshness"]["time_verified_current_run_match"] = False

    errors = _validation_errors(report)

    assert errors


def test_artifact_binding_mismatches_cannot_be_accepted() -> None:
    for field in [
        "subject_digest_matches",
        "resource_uri_matches",
        "release_candidate_matches",
        "artifact_digest_matches",
    ]:
        report = _accepted_report()
        report["artifact_binding"][field] = False
        assert _validation_errors(report), field


def test_unknown_verifier_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["verifier_binding"]["verifier_trusted"] = False

    errors = _validation_errors(report)

    assert errors


def test_failed_vsa_verification_result_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["evidence"]["verification_result"] = "FAILED"

    errors = _validation_errors(report)

    assert errors


def test_missing_verified_level_cannot_be_accepted() -> None:
    report = _accepted_report()
    report["evidence"]["verified_level_ok"] = False

    errors = _validation_errors(report)

    assert errors


def test_required_sha_fields_use_expected_lengths() -> None:
    bad_values = [
        ("run_binding", "commit_sha", "a" * 39),
        ("artifact_binding", "subject_sha256", "b" * 63),
        ("artifact_binding", "artifact_digest_sha256", "b" * 63),
        ("policy_binding", "expected_policy_sha256", "c" * 63),
        ("policy_binding", "evidence_policy_sha256", "c" * 63),
        ("evidence", "evidence_sha256", "d" * 63),
    ]

    for section, field, value in bad_values:
        report = _accepted_report()
        report[section][field] = value
        assert _validation_errors(report), f"{section}.{field}"


def test_manual_status_boolean_input_is_not_allowed() -> None:
    report = _accepted_report()
    report["status_gates"] = {
        "slsa_vsa_present": True
    }

    errors = _validation_errors(report)

    assert errors


def test_release_required_activation_fields_are_not_allowed() -> None:
    for field in [
        "required",
        "core_required",
        "release_required",
        "prod_required",
        "stage_required",
        "blocking",
        "release_blocking",
        "gate_materialization",
    ]:
        report = _accepted_report()
        report[field] = ["slsa_vsa_present"]
        assert _validation_errors(report), field


def test_nested_extra_properties_are_rejected() -> None:
    sections = [
        "producer",
        "run_binding",
        "artifact_binding",
        "policy_binding",
        "verifier_binding",
        "evidence",
        "freshness",
    ]

    for section in sections:
        report = _accepted_report()
        report[section]["extra"] = "not allowed"
        assert _validation_errors(report), section


def test_rejected_report_allows_missing_evidence_digest() -> None:
    report = _rejected_report("missing_vsa_evidence")
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

    _validate(report)


def test_rejected_report_allows_unreadable_evidence_digest_absence() -> None:
    report = _rejected_report("unreadable_vsa_evidence")
    report["evidence"]["evidence_sha256"] = None
    report["evidence"]["time_verified"] = None
    report["freshness"]["freshness_result"] = "rejected_unreadable_vsa_evidence"
    report["freshness"]["current_run_binding_ok"] = False

    _validate(report)


def test_rejected_stale_report_shape_validates_when_failed_checks_exist() -> None:
    report = _rejected_report("stale_vsa_evidence")
    report["freshness"]["freshness_result"] = "rejected_stale_vsa"
    report["freshness"]["stale_vsa_evidence"] = True

    _validate(report)


def test_rejected_policy_digest_mismatch_report_shape_validates_when_failed_checks_exist() -> None:
    report = _rejected_report("policy_digest_mismatch")
    report["policy_binding"]["policy_digest_matches"] = False

    _validate(report)


def test_rejected_policy_identity_absent_report_shape_validates_when_failed_checks_exist() -> None:
    report = _rejected_report("missing_evidence_policy_identity")
    report["policy_binding"]["evidence_policy_id"] = None
    report["policy_binding"]["policy_identity_matches"] = False

    _validate(report)


def test_example_has_no_release_required_activation_surface() -> None:
    report = _accepted_report()
    forbidden = {
        "required",
        "core_required",
        "release_required",
        "prod_required",
        "stage_required",
        "blocking",
        "release_blocking",
        "gate_materialization",
        "status_gates",
    }

    assert forbidden.isdisjoint(report.keys())


def check_slsa_vsa_trusted_evidence_producer_report_schema_v0() -> None:
    test_schema_and_example_exist()
    test_example_validates()
    test_schema_version_and_report_type_are_locked()
    test_created_utc_requires_date_time()
    test_candidate_set_and_recorded_signal_mode_are_locked()
    test_ok_true_requires_accepted_decision_and_no_failed_checks()
    test_rejected_report_requires_failed_checks()
    test_release_authority_words_are_not_producer_decisions()
    test_policy_digest_binding_is_required()
    test_evidence_policy_identity_is_required()
    test_policy_uri_only_binding_is_rejected()
    test_policy_digest_mismatch_cannot_be_accepted()
    test_policy_identity_mismatch_cannot_be_accepted()
    test_time_verified_requires_date_time()
    test_stale_vsa_evidence_cannot_be_accepted()
    test_previous_run_artifact_reuse_cannot_be_accepted()
    test_time_verified_current_run_mismatch_cannot_be_accepted()
    test_artifact_binding_mismatches_cannot_be_accepted()
    test_unknown_verifier_cannot_be_accepted()
    test_failed_vsa_verification_result_cannot_be_accepted()
    test_missing_verified_level_cannot_be_accepted()
    test_required_sha_fields_use_expected_lengths()
    test_manual_status_boolean_input_is_not_allowed()
    test_release_required_activation_fields_are_not_allowed()
    test_nested_extra_properties_are_rejected()
    test_rejected_report_allows_missing_evidence_digest()
    test_rejected_report_allows_unreadable_evidence_digest_absence()
    test_rejected_stale_report_shape_validates_when_failed_checks_exist()
    test_rejected_policy_digest_mismatch_report_shape_validates_when_failed_checks_exist()
    test_rejected_policy_identity_absent_report_shape_validates_when_failed_checks_exist()
    test_example_has_no_release_required_activation_surface()


def test_slsa_vsa_trusted_evidence_producer_report_schema_v0() -> None:
    check_slsa_vsa_trusted_evidence_producer_report_schema_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_evidence_producer_report_schema_v0()
    print("OK: SLSA VSA trusted evidence producer report schema passed")
