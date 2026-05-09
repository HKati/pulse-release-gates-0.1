from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pulse_ref_materialized_gate_sets_v0.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_gate_sets() -> dict[str, Any]:
    return {
        "schema": "pulse_ref_materialized_gate_sets_v0",
        "policy_path": "policy/pulse_gate_policy_v0.yml",
        "policy_sha256": "0" * 64,
        "sets": {
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
        "authority_boundary": {
            "source": "declared_gate_policy",
            "materialization_role": "required_gate_set_reconstruction",
            "creates_release_authority": False,
        },
    }


def _errors(instance: dict[str, Any]) -> list[ValidationError]:
    validator = _validator()
    return list(validator.iter_errors(instance))


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


def test_valid_materialized_gate_sets_pass() -> None:
    assert _errors(_valid_gate_sets()) == []


def test_empty_required_gate_set_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["sets"]["required"] = []

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["sets", "required"], validator="minItems")


def test_empty_release_required_gate_set_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["sets"]["release_required"] = []

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["sets", "release_required"], validator="minItems")


def test_empty_effective_required_gates_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["effective_required_gates"] = []

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["effective_required_gates"], validator="minItems")


def test_duplicate_required_gate_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["sets"]["required"] = [
        "pass_controls_refusal",
        "pass_controls_refusal",
    ]

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["sets", "required"], validator="uniqueItems")


def test_duplicate_effective_required_gate_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["effective_required_gates"] = [
        "pass_controls_refusal",
        "pass_controls_refusal",
    ]

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["effective_required_gates"], validator="uniqueItems")


def test_bad_gate_id_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["sets"]["required"] = ["bad gate id"]

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["sets", "required", 0], validator="pattern")


def test_bad_policy_sha256_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["policy_sha256"] = "not-a-sha"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["policy_sha256"], validator="pattern")


def test_absolute_policy_path_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["policy_path"] = "/policy/pulse_gate_policy_v0.yml"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["policy_path"], validator="pattern")


def test_parent_directory_policy_path_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["policy_path"] = "../policy/pulse_gate_policy_v0.yml"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["policy_path"], validator="pattern")


def test_windows_separator_policy_path_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["policy_path"] = "policy\\pulse_gate_policy_v0.yml"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["policy_path"], validator="pattern")


def test_missing_sets_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets.pop("sets")

    errors = _errors(gate_sets)

    assert _has_error(errors, validator="required")


def test_missing_effective_required_gates_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets.pop("effective_required_gates")

    errors = _errors(gate_sets)

    assert _has_error(errors, validator="required")


def test_authority_boundary_cannot_create_release_authority() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["authority_boundary"]["creates_release_authority"] = True

    errors = _errors(gate_sets)

    assert _has_error(
        errors,
        path=["authority_boundary", "creates_release_authority"],
        validator="const",
    )


def test_authority_boundary_source_is_fixed() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["authority_boundary"]["source"] = "operator_report"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["authority_boundary", "source"], validator="const")


def test_authority_boundary_role_is_fixed() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["authority_boundary"]["materialization_role"] = "release_decision_engine"

    errors = _errors(gate_sets)

    assert _has_error(
        errors,
        path=["authority_boundary", "materialization_role"],
        validator="const",
    )


def test_schema_id_is_fixed() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["schema"] = "other_schema"

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["schema"], validator="const")


def test_additional_top_level_property_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["extra"] = "not allowed"

    errors = _errors(gate_sets)

    assert _has_error(errors, validator="additionalProperties")


def test_additional_set_property_fails() -> None:
    gate_sets = _valid_gate_sets()
    gate_sets["sets"]["advisory"] = ["external_all_pass"]

    errors = _errors(gate_sets)

    assert _has_error(errors, path=["sets"], validator="additionalProperties")


def main() -> int:
    tests = [
        test_schema_self_validates,
        test_valid_materialized_gate_sets_pass,
        test_empty_required_gate_set_fails,
        test_empty_release_required_gate_set_fails,
        test_empty_effective_required_gates_fails,
        test_duplicate_required_gate_fails,
        test_duplicate_effective_required_gate_fails,
        test_bad_gate_id_fails,
        test_bad_policy_sha256_fails,
        test_absolute_policy_path_fails,
        test_parent_directory_policy_path_fails,
        test_windows_separator_policy_path_fails,
        test_missing_sets_fails,
        test_missing_effective_required_gates_fails,
        test_authority_boundary_cannot_create_release_authority,
        test_authority_boundary_source_is_fixed,
        test_authority_boundary_role_is_fixed,
        test_schema_id_is_fixed,
        test_additional_top_level_property_fails,
        test_additional_set_property_fails,
    ]

    try:
        for test in tests:
            test()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 materialized gate sets schema smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
