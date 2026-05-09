from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_operator_handoff_report_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _command_record(name: str = "check_gates_release-grade", ok: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "cmd": [
            "python",
            "PULSE_safe_pack_v0/tools/check_gates.py",
            "--status",
            "status/status.json",
            "--require",
            "pass_controls_refusal",
        ],
        "env_overrides": {},
        "started_utc": "2026-05-09T00:00:00Z",
        "finished_utc": "2026-05-09T00:00:01Z",
        "returncode": 0 if ok else 1,
        "stdout": "",
        "stderr": "",
        "ok": ok,
    }


def _file_entry() -> dict[str, Any]:
    return {
        "path": "status/status.json",
        "exists": True,
        "sha256": "0" * 64,
    }


def _valid_materialized_report() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_operator_handoff_report_v0",
        "ok": True,
        "created_utc": "2026-05-09T00:00:00Z",
        "repo_root": "/repo",
        "gate_mode": "release-grade",
        "status_source": {
            "mode": "existing",
            "status_path": "status/status.json",
            "status_exists_before_run": True,
            "status_sha256_before_run": "0" * 64,
            "status_exists_after_generation": True,
            "status_sha256_after_generation": "0" * 64,
            "status_exists_after_run": True,
            "status_sha256_after_run": "0" * 64,
        },
        "materialized_gate_sets": {
            "required": [
                "pass_controls_refusal",
                "q1_grounded_ok",
            ],
            "release_required": [
                "detectors_materialized_ok",
                "refusal_delta_evidence_present",
            ],
        },
        "effective_required_gates": [
            "pass_controls_refusal",
            "q1_grounded_ok",
            "detectors_materialized_ok",
            "refusal_delta_evidence_present",
        ],
        "files": [
            _file_entry(),
        ],
        "commands": [
            _command_record(),
        ],
        "warnings": [],
        "errors": [],
        "authority_boundary": {
            "handoff_role": "release_grade_reconstruction",
            "creates_release_authority": False,
        },
    }


def _valid_early_fail_closed_report() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_operator_handoff_report_v0",
        "ok": False,
        "created_utc": "2026-05-09T00:00:00Z",
        "repo_root": "/repo",
        "gate_mode": "release-grade",
        "status_source": {
            "mode": "existing",
            "status_path": "missing_status.json",
            "status_exists_before_run": False,
            "status_sha256_before_run": None,
            "status_exists_after_generation": False,
            "status_sha256_after_generation": None,
            "status_exists_after_run": False,
            "status_sha256_after_run": None,
        },
        "materialized_gate_sets": {},
        "effective_required_gates": [],
        "files": [
            {
                "path": "missing_status.json",
                "exists": False,
                "sha256": None,
            }
        ],
        "commands": [],
        "warnings": [
            "status-source=existing was selected, but the status artifact did not exist before this smoke run."
        ],
        "errors": [
            "status artifact missing: missing_status.json"
        ],
        "authority_boundary": {
            "handoff_role": "release_grade_reconstruction",
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


def test_valid_materialized_report_passes() -> None:
    assert _errors(_valid_materialized_report()) == []


def test_valid_early_fail_closed_report_passes() -> None:
    assert _errors(_valid_early_fail_closed_report()) == []


def test_schema_id_is_fixed_when_present() -> None:
    report = _valid_materialized_report()
    report["schema"] = "other_schema"

    errors = _errors(report)

    assert _has_error(errors, path=["schema"], validator="const")


def test_schema_field_can_be_omitted_for_current_tool_output() -> None:
    report = _valid_materialized_report()
    report.pop("schema")

    assert _errors(report) == []


def test_gate_mode_must_be_release_grade() -> None:
    report = _valid_materialized_report()
    report["gate_mode"] = "core"

    errors = _errors(report)

    assert _has_error(errors, path=["gate_mode"], validator="const")


def test_status_source_mode_must_be_existing() -> None:
    report = _valid_materialized_report()
    report["status_source"]["mode"] = "generate-core"

    errors = _errors(report)

    assert _has_error(errors, path=["status_source", "mode"], validator="const")


def test_bad_status_digest_fails() -> None:
    report = _valid_materialized_report()
    report["status_source"]["status_sha256_before_run"] = "not-a-sha"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["status_source", "status_sha256_before_run"],
        validator="oneOf",
    )


def test_null_status_digest_is_allowed_for_missing_status() -> None:
    report = _valid_early_fail_closed_report()

    assert report["status_source"]["status_sha256_before_run"] is None
    assert _errors(report) == []


def test_early_fail_closed_report_requires_ok_false() -> None:
    report = _valid_early_fail_closed_report()
    report["ok"] = True

    errors = _errors(report)

    assert _has_error(errors, path=["ok"], validator="const")


def test_early_fail_closed_report_requires_empty_effective_gates() -> None:
    report = _valid_early_fail_closed_report()
    report["effective_required_gates"] = ["pass_controls_refusal"]

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["effective_required_gates"],
        validator="maxItems",
    )


def test_materialized_report_requires_non_empty_effective_gates() -> None:
    report = _valid_materialized_report()
    report["effective_required_gates"] = []

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["effective_required_gates"],
        validator="minItems",
    )


def test_materialized_report_rejects_empty_required_set() -> None:
    report = _valid_materialized_report()
    report["materialized_gate_sets"]["required"] = []

    errors = _errors(report)

    assert _has_error(errors, path=["materialized_gate_sets"], validator="oneOf")


def test_materialized_report_rejects_empty_release_required_set() -> None:
    report = _valid_materialized_report()
    report["materialized_gate_sets"]["release_required"] = []

    errors = _errors(report)

    assert _has_error(errors, path=["materialized_gate_sets"], validator="oneOf")


def test_materialized_report_rejects_duplicate_effective_gate() -> None:
    report = _valid_materialized_report()
    report["effective_required_gates"] = [
        "pass_controls_refusal",
        "pass_controls_refusal",
    ]

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["effective_required_gates"],
        validator="uniqueItems",
    )


def test_materialized_report_rejects_bad_effective_gate_id() -> None:
    report = _valid_materialized_report()
    report["effective_required_gates"] = ["bad gate id"]

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["effective_required_gates", 0],
        validator="pattern",
    )


def test_materialized_gate_sets_must_be_object() -> None:
    report = _valid_materialized_report()
    report["materialized_gate_sets"] = []

    errors = _errors(report)

    assert _has_error(errors, path=["materialized_gate_sets"], validator="oneOf")


def test_file_inventory_entry_requires_sha256_field() -> None:
    report = _valid_materialized_report()
    report["files"][0].pop("sha256")

    errors = _errors(report)

    assert _has_error(errors, path=["files", 0], validator="required")


def test_file_inventory_allows_null_sha256_for_missing_file() -> None:
    report = _valid_materialized_report()
    report["files"][0] = {
        "path": "missing_status.json",
        "exists": False,
        "sha256": None,
    }

    assert _errors(report) == []


def test_command_record_requires_cmd() -> None:
    report = _valid_materialized_report()
    report["commands"][0].pop("cmd")

    errors = _errors(report)

    assert _has_error(errors, path=["commands", 0], validator="required")


def test_command_record_cmd_must_not_be_empty() -> None:
    report = _valid_materialized_report()
    report["commands"][0]["cmd"] = []

    errors = _errors(report)

    assert _has_error(errors, path=["commands", 0, "cmd"], validator="minItems")


def test_command_record_rejects_additional_property() -> None:
    report = _valid_materialized_report()
    report["commands"][0]["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, path=["commands", 0], validator="additionalProperties")


def test_authority_boundary_cannot_create_release_authority() -> None:
    report = _valid_materialized_report()
    report["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["authority_boundary", "creates_release_authority"],
        validator="const",
    )


def test_authority_boundary_role_is_fixed() -> None:
    report = _valid_materialized_report()
    report["authority_boundary"]["handoff_role"] = "release_decision_engine"

    errors = _errors(report)

    assert _has_error(
        errors,
        path=["authority_boundary", "handoff_role"],
        validator="const",
    )


def test_authority_boundary_can_be_omitted_for_current_tool_output() -> None:
    report = _valid_materialized_report()
    report.pop("authority_boundary")

    assert _errors(report) == []


def test_additional_top_level_property_fails() -> None:
    report = _valid_materialized_report()
    report["extra"] = "not allowed"

    errors = _errors(report)

    assert _has_error(errors, validator="additionalProperties")


def test_missing_required_top_level_field_fails() -> None:
    report = _valid_materialized_report()
    report.pop("status_source")

    errors = _errors(report)

    assert _has_error(errors, validator="required")


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_materialized_report_passes,
        test_valid_early_fail_closed_report_passes,
        test_schema_id_is_fixed_when_present,
        test_schema_field_can_be_omitted_for_current_tool_output,
        test_gate_mode_must_be_release_grade,
        test_status_source_mode_must_be_existing,
        test_bad_status_digest_fails,
        test_null_status_digest_is_allowed_for_missing_status,
        test_early_fail_closed_report_requires_ok_false,
        test_early_fail_closed_report_requires_empty_effective_gates,
        test_materialized_report_requires_non_empty_effective_gates,
        test_materialized_report_rejects_empty_required_set,
        test_materialized_report_rejects_empty_release_required_set,
        test_materialized_report_rejects_duplicate_effective_gate,
        test_materialized_report_rejects_bad_effective_gate_id,
        test_materialized_gate_sets_must_be_object,
        test_file_inventory_entry_requires_sha256_field,
        test_file_inventory_allows_null_sha256_for_missing_file,
        test_command_record_requires_cmd,
        test_command_record_cmd_must_not_be_empty,
        test_command_record_rejects_additional_property,
        test_authority_boundary_cannot_create_release_authority,
        test_authority_boundary_role_is_fixed,
        test_authority_boundary_can_be_omitted_for_current_tool_output,
        test_additional_top_level_property_fails,
        test_missing_required_top_level_field_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 operator handoff report schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
