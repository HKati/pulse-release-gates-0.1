from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_package_verifier_report_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_check(
    artifact_path: str = "package_manifest.json",
    schema_path: str = "schemas/pulse_ref_release_reference_package_v0.schema.json",
    ok: bool = True,
) -> dict[str, Any]:
    return {
        "artifact_path": artifact_path,
        "schema_path": schema_path,
        "ok": ok,
    }


def _digest_check(
    artifact_path: str = "status/status.json",
    expected_sha256: str = "0" * 64,
    actual_sha256: str | None = "0" * 64,
    ok: bool = True,
    source: str = "package_manifest",
) -> dict[str, Any]:
    return {
        "artifact_path": artifact_path,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "ok": ok,
        "source": source,
    }


def _cross_check(name: str = "status_digest_matches_handoff", ok: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "path": "handoff/operator_handoff_report.json",
        "message": "status digest matches handoff report",
    }


def _valid_success_report() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_package_verifier_report_v0",
        "ok": True,
        "package_root": "tests/fixtures/pulse_ref_ra1_package_minimal",
        "package_id": "pulse-ref-ra1-minimal",
        "run_key": "pulse-ref-ra1-minimal-fixture",
        "git_sha": "a" * 40,
        "checked_utc": "2026-05-09T00:00:00Z",
        "schemas_validated": [
            _schema_check(),
        ],
        "artifact_digests_checked": [
            _digest_check(),
        ],
        "cross_artifact_checks": [
            _cross_check(),
        ],
        "warnings": [],
        "errors": [],
        "authority_boundary": {
            "verifier_role": "external_reconstruction_check",
            "creates_release_authority": False,
        },
    }


def _valid_failure_report() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_package_verifier_report_v0",
        "ok": False,
        "package_root": "tests/fixtures/pulse_ref_ra1_package_minimal",
        "package_id": "pulse-ref-ra1-minimal",
        "run_key": "pulse-ref-ra1-minimal-fixture",
        "git_sha": "a" * 40,
        "checked_utc": "2026-05-09T00:00:00Z",
        "schemas_validated": [
            _schema_check(ok=True),
        ],
        "artifact_digests_checked": [
            _digest_check(
                artifact_path="handoff/operator_handoff_report.json",
                expected_sha256="1" * 64,
                actual_sha256="2" * 64,
                ok=False,
                source="package_digests",
            ),
        ],
        "cross_artifact_checks": [
            {
                "name": "handoff_digest_mismatch",
                "ok": False,
                "path": "handoff/operator_handoff_report.json",
                "message": "handoff digest mismatch",
            }
        ],
        "warnings": [],
        "errors": [
            "handoff/operator_handoff_report.json digest mismatch",
        ],
        "authority_boundary": {
            "verifier_role": "external_reconstruction_check",
            "creates_release_authority": False,
        },
    }


def _errors(instance: dict[str, Any]) -> list[ValidationError]:
    return list(_validator().iter_errors(instance))


def _has_error(
    errors: list[ValidationError],
    *,
    path: list[str | int] | None = None,
    validator: str | None = None,
) -> bool:
    for error in errors:
        if path is not None and list(error.absolute_path) != path:
            continue
        if validator is not None and error.validator != validator:
            continue
        return True

    return False


def test_schema_self_validates() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_valid_success_report_passes() -> None:
    assert _errors(_valid_success_report()) == []


def test_valid_failure_report_passes() -> None:
    assert _errors(_valid_failure_report()) == []


def test_schema_id_is_fixed() -> None:
    report = _valid_success_report()
    report["schema"] = "other_schema"

    errors = _errors(report)

    assert _has_error(errors, path=["schema"], validator="const")


def test_ok_true_requires_empty_errors() -> None:
    report = _valid_success_report()
    report["errors"] = ["unexpected error"]

    errors = _errors(report)

    assert _has_error(errors, path=["errors"], validator="maxItems")


def test_ok_false_requires_non_empty_errors() -> None:
    report = _valid_failure_report()
    report["errors"] = []

    errors = _errors(report)

    assert _has_error(errors, path=["errors"], validator="minItems")


def test_package_root_is_required() -> None:
    report = _valid_success_report()
    report.pop("package_root")

    errors = _errors(report)

    assert _has_error(errors, validator="required")


def test_checked_utc_is_required() -> None:
    report = _valid_success_report()
    report.pop("checked_utc")

    errors = _errors(report)

    assert _has_error(errors, validator="required")


def test_git_sha_must_be_40_lowercase_hex_chars_when_present() -> None:
    report = _valid_success_report()
    report["git_sha"] = "not-a-sha"

    errors = _errors(report)

    assert _has_error(errors, path=["git_sha"], validator="pattern")


def test_uppercase_git_sha_fails_when_present() -> None:
    report = _valid_success_report()
    report["git_sha"] = "A" * 40

    errors = _errors(report)

    assert _has_error(errors, path=["git_sha"], validator="pattern")


def test_schema_check_requires_artifact_path() -> None:
    report = _valid_success_report()
    report["schemas_validated"][0].pop("artifact_path")

    errors = _errors(report)

    assert _has_error(errors, path=["schemas_validated", 0], validator="required")


def test_schema_check_rejects_absolute_artifact_path() -> None:
    report = _valid_success_report()
    report["schemas_validated"][0]["artifact_path"] = "/package_manifest.json"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["schemas_validated", 0, "artifact_path"],
        validator="pattern",
    )


def test_schema_check_rejects_parent_directory_artifact_path() -> None:
    report = _valid_success_report()
    report["schemas_validated"][0]["artifact_path"] = "../package_manifest.json"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["schemas_validated", 0, "artifact_path"],
        validator="pattern",
    )


def test_schema_check_rejects_windows_separator_artifact_path() -> None:
    report = _valid_success_report()
    report["schemas_validated"][0]["artifact_path"] = "status\\status.json"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["schemas_validated", 0, "artifact_path"],
        validator="pattern",
    )


def test_digest_check_requires_expected_sha256() -> None:
    report = _valid_success_report()
    report["artifact_digests_checked"][0].pop("expected_sha256")

    errors = _errors(report)

    assert _has_error(errors, path=["artifact_digests_checked", 0], validator="required")


def test_digest_check_rejects_bad_expected_sha256() -> None:
    report = _valid_success_report()
    report["artifact_digests_checked"][0]["expected_sha256"] = "not-a-sha"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["artifact_digests_checked", 0, "expected_sha256"],
        validator="pattern",
    )


def test_digest_check_allows_null_actual_sha256_for_missing_artifact() -> None:
    report = _valid_failure_report()
    report["artifact_digests_checked"][0]["actual_sha256"] = None

    assert _errors(report) == []


def test_digest_source_accepts_package_manifest_and_package_digests() -> None:
    for source in ["package_manifest", "package_digests"]:
        report = _valid_success_report()
        report["artifact_digests_checked"][0]["source"] = source

        assert _errors(report) == []


def test_digest_source_rejects_unknown_value() -> None:
    report = _valid_success_report()
    report["artifact_digests_checked"][0]["source"] = "other_source"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["artifact_digests_checked", 0, "source"],
        validator="enum",
    )


def test_cross_artifact_check_requires_name() -> None:
    report = _valid_success_report()
    report["cross_artifact_checks"][0].pop("name")

    errors = _errors(report)

    assert _has_error(errors, path=["cross_artifact_checks", 0], validator="required")


def test_cross_artifact_check_rejects_empty_name() -> None:
    report = _valid_success_report()
    report["cross_artifact_checks"][0]["name"] = ""

    errors = _errors(report)

    assert _has_error(errors, path=["cross_artifact_checks", 0, "name"], validator="minLength")


def test_warning_messages_must_not_be_empty() -> None:
    report = _valid_success_report()
    report["warnings"] = [""]

    errors = _errors(report)

    assert _has_error(errors, path=["warnings", 0], validator="minLength")


def test_error_messages_must_not_be_empty() -> None:
    report = _valid_failure_report()
    report["errors"] = [""]

    errors = _errors(report)

    assert _has_error(errors, path=["errors", 0], validator="minLength")


def test_authority_boundary_cannot_create_release_authority() -> None:
    report = _valid_success_report()
    report["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["authority_boundary", "creates_release_authority"],
        validator="const",
    )


def test_authority_boundary_role_is_fixed() -> None:
    report = _valid_success_report()
    report["authority_boundary"]["verifier_role"] = "release_decision_engine"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["authority_boundary", "verifier_role"],
        validator="const",
    )


def test_additional_top_level_property_fails() -> None:
    report = _valid_success_report()
    report["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, validator="additionalProperties")


def test_additional_schema_check_property_fails() -> None:
    report = _valid_success_report()
    report["schemas_validated"][0]["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, path=["schemas_validated", 0], validator="additionalProperties")


def test_additional_digest_check_property_fails() -> None:
    report = _valid_success_report()
    report["artifact_digests_checked"][0]["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, path=["artifact_digests_checked", 0], validator="additionalProperties")


def test_additional_authority_boundary_property_fails() -> None:
    report = _valid_success_report()
    report["authority_boundary"]["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, path=["authority_boundary"], validator="additionalProperties")


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_success_report_passes,
        test_valid_failure_report_passes,
        test_schema_id_is_fixed,
        test_ok_true_requires_empty_errors,
        test_ok_false_requires_non_empty_errors,
        test_package_root_is_required,
        test_checked_utc_is_required,
        test_git_sha_must_be_40_lowercase_hex_chars_when_present,
        test_uppercase_git_sha_fails_when_present,
        test_schema_check_requires_artifact_path,
        test_schema_check_rejects_absolute_artifact_path,
        test_schema_check_rejects_parent_directory_artifact_path,
        test_schema_check_rejects_windows_separator_artifact_path,
        test_digest_check_requires_expected_sha256,
        test_digest_check_rejects_bad_expected_sha256,
        test_digest_check_allows_null_actual_sha256_for_missing_artifact,
        test_digest_source_accepts_package_manifest_and_package_digests,
        test_digest_source_rejects_unknown_value,
        test_cross_artifact_check_requires_name,
        test_cross_artifact_check_rejects_empty_name,
        test_warning_messages_must_not_be_empty,
        test_error_messages_must_not_be_empty,
        test_authority_boundary_cannot_create_release_authority,
        test_authority_boundary_role_is_fixed,
        test_additional_top_level_property_fails,
        test_additional_schema_check_property_fails,
        test_additional_digest_check_property_fails,
        test_additional_authority_boundary_property_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 package verifier report schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
