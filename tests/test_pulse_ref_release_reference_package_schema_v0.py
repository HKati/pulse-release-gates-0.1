from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_release_reference_package_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_manifest() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_release_reference_package_v0",
        "package_id": "pulse-ref-ra1-example",
        "created_utc": "2026-05-09T00:00:00Z",
        "run_key": "example-run-key",
        "git_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "status_artifact": {
            "path": "status/status.json",
            "sha256": "0" * 64
        },
        "gate_policy": {
            "path": "policy/pulse_gate_policy_v0.yml",
            "sha256": "1" * 64
        },
        "gate_registry": {
            "path": "policy/pulse_gate_registry_v0.yml",
            "sha256": "2" * 64
        },
        "materialized_gate_sets": {
            "path": "gates/materialized_gate_sets.json",
            "sha256": "3" * 64
        },
        "operator_handoff_report": {
            "path": "handoff/operator_handoff_report.json",
            "sha256": "4" * 64
        },
        "release_authority_manifest": {
            "path": "release_authority/release_authority_manifest.json",
            "sha256": "5" * 64
        },
        "ci_outcome": {
            "path": "ci/ci_outcome.json",
            "sha256": "6" * 64
        },
        "package_digests": {
            "path": "digests/package_digests.json",
            "sha256": "7" * 64
        },
        "authority_boundary": {
            "normative_decision_path": (
                "status.json -> declared gate policy -> materialized required gates "
                "-> strict gate checking -> CI outcome"
            ),
            "package_role": "audit_preservation_reconstruction",
            "creates_release_authority": False
        }
    }


def _errors(instance: dict[str, Any]) -> list[str]:
    validator = _validator()
    return [error.message for error in validator.iter_errors(instance)]


def test_schema_self_validates() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_valid_minimum_manifest_passes() -> None:
    assert _errors(_valid_manifest()) == []


def test_missing_required_artifact_fails() -> None:
    manifest = _valid_manifest()
    manifest.pop("status_artifact")

    errors = _errors(manifest)

    assert any("status_artifact" in error for error in errors)


def test_bad_sha256_fails() -> None:
    manifest = _valid_manifest()
    manifest["status_artifact"]["sha256"] = "not-a-sha"

    errors = _errors(manifest)

    assert any("does not match" in error for error in errors)


def test_absolute_path_fails() -> None:
    manifest = _valid_manifest()
    manifest["status_artifact"]["path"] = "/status/status.json"

    errors = _errors(manifest)

    assert any("does not match" in error for error in errors)


def test_parent_directory_path_fails() -> None:
    manifest = _valid_manifest()
    manifest["status_artifact"]["path"] = "../status/status.json"

    errors = _errors(manifest)

    assert any("does not match" in error for error in errors)


def test_authority_boundary_cannot_create_release_authority() -> None:
    manifest = _valid_manifest()
    manifest["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(manifest)

    assert any("False was expected" in error for error in errors)


def test_authority_boundary_role_is_fixed() -> None:
    manifest = _valid_manifest()
    manifest["authority_boundary"]["package_role"] = "release_decision_engine"

    errors = _errors(manifest)

    assert any("audit_preservation_reconstruction" in error for error in errors)


def test_schema_id_is_fixed() -> None:
    manifest = _valid_manifest()
    manifest["schema"] = "other_schema"

    errors = _errors(manifest)

    assert any("pulse_ref_release_reference_package_v0" in error for error in errors)


def main() -> int:
    try:
        test_schema_self_validates()
        test_valid_minimum_manifest_passes()
        test_missing_required_artifact_fails()
        test_bad_sha256_fails()
        test_absolute_path_fails()
        test_parent_directory_path_fails()
        test_authority_boundary_cannot_create_release_authority()
        test_authority_boundary_role_is_fixed()
        test_schema_id_is_fixed()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 release-reference package schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
