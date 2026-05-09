from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_publication_snapshot_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_snapshot() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_publication_snapshot_v0",
        "snapshot_created_utc": "2026-05-09T00:00:00Z",
        "package_id": "pulse-ref-ra1-example",
        "run_key": "example-run-key",
        "git_sha": "a" * 40,
        "quality_ledger_url": "https://hkati.github.io/pulse-release-gates-0.1/",
        "status_json_url": "https://hkati.github.io/pulse-release-gates-0.1/status.json",
        "release_authority_manifest_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/"
            "release_authority_manifest.json"
        ),
        "audit_bundle_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/audit_bundle/"
        ),
        "operator_handoff_report_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/"
            "operator_handoff_report.json"
        ),
        "ci_outcome_url": (
            "https://github.com/HKati/pulse-release-gates-0.1/actions/runs/123"
        ),
        "package_manifest_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/package_manifest.json"
        ),
        "package_digests_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/package_digests.json"
        ),
        "publication_surface": "github_pages",
        "creates_release_authority": False,
    }


def _minimum_snapshot() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_publication_snapshot_v0",
        "snapshot_created_utc": "2026-05-09T00:00:00Z",
        "quality_ledger_url": "https://hkati.github.io/pulse-release-gates-0.1/",
        "status_json_url": "https://hkati.github.io/pulse-release-gates-0.1/status.json",
        "release_authority_manifest_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/"
            "release_authority_manifest.json"
        ),
        "audit_bundle_url": (
            "https://hkati.github.io/pulse-release-gates-0.1/audit_bundle/"
        ),
        "creates_release_authority": False,
    }


def _errors(instance: dict[str, Any]) -> list[ValidationError]:
    return list(_validator().iter_errors(instance))


def _has_error(
    errors: list[ValidationError],
    *,
    path: list[str] | None = None,
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


def test_valid_publication_snapshot_passes() -> None:
    assert _errors(_valid_snapshot()) == []


def test_valid_minimum_publication_snapshot_passes() -> None:
    assert _errors(_minimum_snapshot()) == []


def test_schema_id_is_fixed() -> None:
    snapshot = _valid_snapshot()
    snapshot["schema"] = "other_schema"

    errors = _errors(snapshot)

    assert _has_error(errors, path=["schema"], validator="const")


def test_snapshot_created_utc_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("snapshot_created_utc")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_quality_ledger_url_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("quality_ledger_url")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_status_json_url_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("status_json_url")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_release_authority_manifest_url_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("release_authority_manifest_url")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_audit_bundle_url_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("audit_bundle_url")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_creates_release_authority_is_required() -> None:
    snapshot = _valid_snapshot()
    snapshot.pop("creates_release_authority")

    errors = _errors(snapshot)

    assert _has_error(errors, validator="required")


def test_creates_release_authority_must_be_false() -> None:
    snapshot = _valid_snapshot()
    snapshot["creates_release_authority"] = True

    errors = _errors(snapshot)

    assert _has_error(errors, path=["creates_release_authority"], validator="const")


def test_publication_urls_must_be_https() -> None:
    url_fields = [
        "quality_ledger_url",
        "status_json_url",
        "release_authority_manifest_url",
        "audit_bundle_url",
        "operator_handoff_report_url",
        "ci_outcome_url",
        "package_manifest_url",
        "package_digests_url",
    ]

    for field in url_fields:
        snapshot = _valid_snapshot()
        snapshot[field] = "http://example.com/not-https"

        errors = _errors(snapshot)

        assert _has_error(errors, path=[field], validator="pattern")


def test_empty_url_fails() -> None:
    snapshot = _valid_snapshot()
    snapshot["status_json_url"] = ""

    errors = _errors(snapshot)

    assert _has_error(errors, path=["status_json_url"], validator="minLength")


def test_git_sha_must_be_40_lowercase_hex_chars() -> None:
    snapshot = _valid_snapshot()
    snapshot["git_sha"] = "not-a-sha"

    errors = _errors(snapshot)

    assert _has_error(errors, path=["git_sha"], validator="pattern")


def test_uppercase_git_sha_fails() -> None:
    snapshot = _valid_snapshot()
    snapshot["git_sha"] = "A" * 40

    errors = _errors(snapshot)

    assert _has_error(errors, path=["git_sha"], validator="pattern")


def test_optional_package_id_must_not_be_empty_when_present() -> None:
    snapshot = _valid_snapshot()
    snapshot["package_id"] = ""

    errors = _errors(snapshot)

    assert _has_error(errors, path=["package_id"], validator="minLength")


def test_optional_run_key_must_not_be_empty_when_present() -> None:
    snapshot = _valid_snapshot()
    snapshot["run_key"] = ""

    errors = _errors(snapshot)

    assert _has_error(errors, path=["run_key"], validator="minLength")


def test_optional_publication_surface_must_not_be_empty_when_present() -> None:
    snapshot = _valid_snapshot()
    snapshot["publication_surface"] = ""

    errors = _errors(snapshot)

    assert _has_error(errors, path=["publication_surface"], validator="minLength")


def test_additional_top_level_property_fails() -> None:
    snapshot = _valid_snapshot()
    snapshot["extra"] = "not allowed"

    errors = _errors(snapshot)

    assert _has_error(errors, validator="additionalProperties")


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_publication_snapshot_passes,
        test_valid_minimum_publication_snapshot_passes,
        test_schema_id_is_fixed,
        test_snapshot_created_utc_is_required,
        test_quality_ledger_url_is_required,
        test_status_json_url_is_required,
        test_release_authority_manifest_url_is_required,
        test_audit_bundle_url_is_required,
        test_creates_release_authority_is_required,
        test_creates_release_authority_must_be_false,
        test_publication_urls_must_be_https,
        test_empty_url_fails,
        test_git_sha_must_be_40_lowercase_hex_chars,
        test_uppercase_git_sha_fails,
        test_optional_package_id_must_not_be_empty_when_present,
        test_optional_run_key_must_not_be_empty_when_present,
        test_optional_publication_surface_must_not_be_empty_when_present,
        test_additional_top_level_property_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 publication snapshot schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
