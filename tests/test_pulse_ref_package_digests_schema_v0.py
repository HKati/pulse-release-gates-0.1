from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_package_digests_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_digests() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_package_digests_v0",
        "algorithm": "sha256",
        "created_utc": "2026-05-09T00:00:00Z",
        "package_id": "pulse-ref-ra1-example",
        "artifacts": {
            "status/status.json": "0" * 64,
            "policy/pulse_gate_policy_v0.yml": "1" * 64,
            "gates/materialized_gate_sets.json": "2" * 64,
            "handoff/operator_handoff_report.json": "3" * 64,
            "ci/ci_outcome.json": "4" * 64,
        },
        "authority_boundary": {
            "digest_role": "artifact_integrity_verification",
            "creates_release_authority": False,
        },
    }


def _errors(instance: dict[str, Any]) -> list[ValidationError]:
    return list(_validator().iter_errors(instance))


def _has_error(
    errors: list[ValidationError],
    *,
    path: list[str] | None = None,
    validator: str | None = None,
    message_contains: str | None = None,
) -> bool:
    for error in errors:
        if path is not None and list(error.absolute_path) != path:
            continue
        if validator is not None and error.validator != validator:
            continue
        if message_contains is not None and message_contains not in error.message:
            continue
        return True

    return False


def test_schema_self_validates() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_valid_package_digests_pass() -> None:
    assert _errors(_valid_digests()) == []


def test_optional_metadata_can_be_omitted() -> None:
    digests = _valid_digests()
    digests.pop("created_utc")
    digests.pop("package_id")

    assert _errors(digests) == []


def test_schema_id_is_fixed() -> None:
    digests = _valid_digests()
    digests["schema"] = "other_schema"

    errors = _errors(digests)

    assert _has_error(errors, path=["schema"], validator="const")


def test_algorithm_is_fixed_to_sha256() -> None:
    digests = _valid_digests()
    digests["algorithm"] = "sha512"

    errors = _errors(digests)

    assert _has_error(errors, path=["algorithm"], validator="const")


def test_artifacts_is_required() -> None:
    digests = _valid_digests()
    digests.pop("artifacts")

    errors = _errors(digests)

    assert _has_error(errors, validator="required")


def test_artifacts_must_not_be_empty() -> None:
    digests = _valid_digests()
    digests["artifacts"] = {}

    errors = _errors(digests)

    assert _has_error(errors, path=["artifacts"], validator="minProperties")


def test_bad_sha256_value_fails() -> None:
    digests = _valid_digests()
    digests["artifacts"]["status/status.json"] = "not-a-sha"

    errors = _errors(digests)

    assert _has_error(
        errors,
        path=["artifacts", "status/status.json"],
        validator="pattern",
    )


def test_uppercase_sha256_value_fails() -> None:
    digests = _valid_digests()
    digests["artifacts"]["status/status.json"] = "A" * 64

    errors = _errors(digests)

    assert _has_error(
        errors,
        path=["artifacts", "status/status.json"],
        validator="pattern",
    )


def test_absolute_artifact_path_fails() -> None:
    digests = _valid_digests()
    digests["artifacts"] = {
        "/status/status.json": "0" * 64,
    }

    errors = _errors(digests)

    assert _has_error(errors, validator="pattern", message_contains="does not match")


def test_parent_directory_artifact_path_fails() -> None:
    digests = _valid_digests()
    digests["artifacts"] = {
        "../status/status.json": "0" * 64,
    }

    errors = _errors(digests)

    assert _has_error(errors, validator="pattern", message_contains="does not match")


def test_windows_separator_artifact_path_fails() -> None:
    digests = _valid_digests()
    digests["artifacts"] = {
        "status\\status.json": "0" * 64,
    }

    errors = _errors(digests)

    assert _has_error(errors, validator="pattern", message_contains="does not match")


def test_empty_package_id_fails_when_present() -> None:
    digests = _valid_digests()
    digests["package_id"] = ""

    errors = _errors(digests)

    assert _has_error(errors, path=["package_id"], validator="minLength")


def test_authority_boundary_is_required() -> None:
    digests = _valid_digests()
    digests.pop("authority_boundary")

    errors = _errors(digests)

    assert _has_error(errors, validator="required")


def test_authority_boundary_cannot_create_release_authority() -> None:
    digests = _valid_digests()
    digests["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(digests)

    assert _has_error(
        errors,
        path=["authority_boundary", "creates_release_authority"],
        validator="const",
    )


def test_authority_boundary_digest_role_is_fixed() -> None:
    digests = _valid_digests()
    digests["authority_boundary"]["digest_role"] = "release_decision_engine"

    errors = _errors(digests)

    assert _has_error(
        errors,
        path=["authority_boundary", "digest_role"],
        validator="const",
    )


def test_additional_top_level_property_fails() -> None:
    digests = _valid_digests()
    digests["extra"] = "not allowed"

    errors = _errors(digests)

    assert _has_error(errors, validator="additionalProperties")


def test_additional_authority_boundary_property_fails() -> None:
    digests = _valid_digests()
    digests["authority_boundary"]["extra"] = "not allowed"

    errors = _errors(digests)

    assert _has_error(
        errors,
        path=["authority_boundary"],
        validator="additionalProperties",
    )


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_package_digests_pass,
        test_optional_metadata_can_be_omitted,
        test_schema_id_is_fixed,
        test_algorithm_is_fixed_to_sha256,
        test_artifacts_is_required,
        test_artifacts_must_not_be_empty,
        test_bad_sha256_value_fails,
        test_uppercase_sha256_value_fails,
        test_absolute_artifact_path_fails,
        test_parent_directory_artifact_path_fails,
        test_windows_separator_artifact_path_fails,
        test_empty_package_id_fails_when_present,
        test_authority_boundary_is_required,
        test_authority_boundary_cannot_create_release_authority,
        test_authority_boundary_digest_role_is_fixed,
        test_additional_top_level_property_fails,
        test_additional_authority_boundary_property_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 package digests schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
