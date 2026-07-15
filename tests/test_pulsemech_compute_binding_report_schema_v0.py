#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_compute_binding_report_v0.schema.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_binding_report_6066_example_v0.json"
)


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH)


def example() -> dict[str, Any]:
    return load_json(EXAMPLE_PATH)


def validator() -> jsonschema.Draft202012Validator:
    loaded_schema = schema()
    jsonschema.Draft202012Validator.check_schema(loaded_schema)
    return jsonschema.Draft202012Validator(
        loaded_schema,
        format_checker=jsonschema.FormatChecker(),
    )


def validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in validator().iter_errors(instance)
    ]


def validate(instance: dict[str, Any]) -> None:
    validator().validate(instance)


def test_contract_files_exist() -> None:
    assert SCHEMA_PATH.exists()
    assert EXAMPLE_PATH.exists()


def test_schema_is_valid_and_example_validates() -> None:
    validate(example())


def test_identity_fields_are_locked() -> None:
    report = example()
    report["schema_version"] = "wrong"
    assert validation_errors(report)

    report = example()
    report["report_type"] = "wrong"
    assert validation_errors(report)

    report = example()
    report["tool"]["id"] = "wrong-builder"
    assert validation_errors(report)


def test_example_status_is_explicit() -> None:
    report = example()
    assert report["record_status"] == "example"

    report["record_status"] = "unknown"
    assert validation_errors(report)


def test_allow_and_block_are_report_values_not_report_ok_values() -> None:
    report = example()
    report["subject"]["decision"] = "BLOCK"
    validate(report)

    for invalid in ["PASS", "PROD-PASS", "FAILED", "UNKNOWN"]:
        report = example()
        report["subject"]["decision"] = invalid
        assert validation_errors(report), invalid


def test_report_ok_controls_errors_only() -> None:
    report = example()
    report["ok"] = False
    report["errors"] = ["synthetic_contract_error"]
    validate(report)

    report = example()
    report["ok"] = True
    report["errors"] = ["unexpected"]
    assert validation_errors(report)

    report = example()
    report["ok"] = False
    report["errors"] = []
    assert validation_errors(report)


def test_observer_is_excluded_from_subject_totals_by_contract() -> None:
    report = example()
    report["analysis_boundary"]["observer_in_subject_totals"] = True
    assert validation_errors(report)


def test_unknown_and_unbound_are_distinct_contract_values() -> None:
    binding_classes = (
        schema()["$defs"]["compute_node"]["properties"]["binding_class"]["enum"]
    )
    binding_statuses = (
        schema()["$defs"]["compute_node"]["properties"]["binding_status"]["enum"]
    )

    assert "unknown" in binding_classes
    assert "unbound" in binding_classes
    assert "unknown" in binding_statuses
    assert "none" in binding_statuses
    assert "unknown" != "unbound"


def test_resource_axes_are_explicit_and_do_not_allow_overall_scalar() -> None:
    report = example()
    report["resource_summary"]["overall_efficiency"] = 0.9
    assert validation_errors(report)

    report = example()
    report["resource_summary"]["axes"]["overall_compute"] = {
        "unit": "score"
    }
    assert validation_errors(report)


def test_resource_axis_unit_is_locked_to_axis_identity() -> None:
    report = example()
    report["resource_summary"]["axes"]["runner_wall_seconds"]["unit"] = "tokens"
    assert validation_errors(report)


def test_resource_axis_requires_separate_categories_and_coverage() -> None:
    report = example()
    del report["resource_summary"]["axes"]["runner_wall_seconds"][
        "observer_overhead"
    ]
    assert validation_errors(report)

    report = example()
    del report["resource_summary"]["axes"]["runner_wall_seconds"][
        "measurement_coverage_ratio"
    ]
    assert validation_errors(report)

    report = example()
    del report["resource_summary"]["axes"]["runner_wall_seconds"][
        "ratios"
    ]["unknown"]
    assert validation_errors(report)


def test_sha_and_commit_lengths_are_enforced() -> None:
    report = example()
    report["subject"]["source_commit"] = "a" * 39
    assert validation_errors(report)

    report = example()
    report["subject"]["policy_sha256"] = "b" * 63
    assert validation_errors(report)

    report = example()
    report["compute_nodes"][0]["source_identity"]["source_sha256"] = "c" * 63
    assert validation_errors(report)


def test_identifier_prefixes_are_enforced() -> None:
    report = example()
    report["compute_nodes"][0]["node_id"] = "state:not-compute"
    assert validation_errors(report)

    report = example()
    report["state_nodes"][0]["state_id"] = "compute:not-state"
    assert validation_errors(report)

    report = example()
    report["edges"][0]["edge_id"] = "not-edge"
    assert validation_errors(report)


def test_finding_identity_and_severity_are_closed_vocabularies() -> None:
    report = example()
    report["findings"][0]["finding_id"] = "invented_finding"
    assert validation_errors(report)

    report = example()
    report["findings"][0]["severity"] = "blocking"
    assert validation_errors(report)


def test_activation_and_status_mutation_surfaces_are_not_allowed() -> None:
    forbidden = [
        "required",
        "release_required",
        "blocking",
        "status_gates",
        "compute_budget",
        "active_compute_gates",
    ]

    for field in forbidden:
        report = example()
        report[field] = True
        assert validation_errors(report), field


def test_nested_extra_properties_are_rejected() -> None:
    mutations = [
        ("tool",),
        ("analysis_boundary",),
        ("subject",),
        ("summary",),
    ]

    for path in mutations:
        report = example()
        report[path[0]]["extra"] = "not allowed"
        assert validation_errors(report), path

    report = example()
    report["compute_nodes"][0]["extra"] = "not allowed"
    assert validation_errors(report)

    report = example()
    report["state_nodes"][0]["extra"] = "not allowed"
    assert validation_errors(report)

    report = example()
    report["edges"][0]["extra"] = "not allowed"
    assert validation_errors(report)


def test_example_has_no_active_compute_gate_or_budget_surface() -> None:
    report = example()
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
        "compute_budget",
        "active_compute_gates",
    }
    assert forbidden.isdisjoint(report)


def check_pulsemech_compute_binding_report_schema_v0() -> None:
    test_contract_files_exist()
    test_schema_is_valid_and_example_validates()
    test_identity_fields_are_locked()
    test_example_status_is_explicit()
    test_allow_and_block_are_report_values_not_report_ok_values()
    test_report_ok_controls_errors_only()
    test_observer_is_excluded_from_subject_totals_by_contract()
    test_unknown_and_unbound_are_distinct_contract_values()
    test_resource_axes_are_explicit_and_do_not_allow_overall_scalar()
    test_resource_axis_unit_is_locked_to_axis_identity()
    test_resource_axis_requires_separate_categories_and_coverage()
    test_sha_and_commit_lengths_are_enforced()
    test_identifier_prefixes_are_enforced()
    test_finding_identity_and_severity_are_closed_vocabularies()
    test_activation_and_status_mutation_surfaces_are_not_allowed()
    test_nested_extra_properties_are_rejected()
    test_example_has_no_active_compute_gate_or_budget_surface()


def test_pulsemech_compute_binding_report_schema_v0() -> None:
    check_pulsemech_compute_binding_report_schema_v0()


if __name__ == "__main__":
    check_pulsemech_compute_binding_report_schema_v0()
    print("OK: PULSEmech compute-binding report schema v0 contract passed")
