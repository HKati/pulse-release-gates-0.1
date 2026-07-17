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
    / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_planned_observed_relation_example_v0.json"
)


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_SCHEMA = load_json(SCHEMA_PATH)
_EXAMPLE = load_json(EXAMPLE_PATH)
jsonschema.Draft202012Validator.check_schema(_SCHEMA)
_VALIDATOR = jsonschema.Draft202012Validator(
    _SCHEMA,
    format_checker=jsonschema.FormatChecker(),
)


def schema() -> dict[str, Any]:
    return _SCHEMA


def example() -> dict[str, Any]:
    return copy.deepcopy(_EXAMPLE)


def validator() -> jsonschema.Draft202012Validator:
    return _VALIDATOR


def validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in sorted(
            validator().iter_errors(instance),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    ]


def validate(instance: dict[str, Any]) -> None:
    validator().validate(instance)


def expectation(record: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = record["expectations"][identifier]
    assert isinstance(selected, dict)
    return selected


def observation(record: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = record["observations"][identifier]
    assert isinstance(selected, dict)
    return selected


def relation(record: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = record["relations"][identifier]
    assert isinstance(selected, dict)
    return selected


def runtime_packet_binding(record: dict[str, Any]) -> dict[str, Any]:
    identity = record["comparison_identity"]
    return {
        "schema_version": "pulsemech_compute_runtime_observation_packet_v0",
        "packet_type": "pulsemech_compute_runtime_observation_packet",
        "record_status": record["record_status"],
        "path_or_uri": "example://runtime-observation-packet-v0.json",
        "sha256": "a" * 64,
        "packet_id": "runtime-observation:planned-observed-example-v0",
        "packet_sequence": 0,
        "packet_scope": (
            "example" if record["record_status"] == "example" else "subject_run"
        ),
        "subject_repository": identity["subject_repository"],
        "subject_run_key": identity["subject_run_key"],
        "subject_source_commit": identity["subject_source_commit"],
        "release_candidate_id": identity["release_candidate_id"],
        "ok": True,
    }


def as_observed(record: dict[str, Any]) -> dict[str, Any]:
    converted = copy.deepcopy(record)
    converted["record_status"] = "observed"
    converted["tool"]["source_revision"] = "a" * 40
    converted["comparison_identity"]["comparison_scope"] = "subject_run"
    converted["observation_bindings"]["compute_binding_report"][
        "record_status"
    ] = "observed"
    return converted


def as_runtime_observed(record: dict[str, Any]) -> dict[str, Any]:
    converted = copy.deepcopy(record)
    converted["observation_bindings"]["compute_binding_report"][
        "analysis_level"
    ] = "runtime_observed"
    converted["comparison_boundary"]["observed_analysis_level"] = (
        "runtime_observed"
    )
    converted["observation_bindings"]["runtime_observation_status"] = "partial"
    converted["observation_bindings"]["runtime_observation_packets"] = [
        runtime_packet_binding(converted)
    ]
    converted["coverage"]["runtime_observation_status"] = "partial"
    return converted


def test_contract_files_exist() -> None:
    assert SCHEMA_PATH.is_file()
    assert EXAMPLE_PATH.is_file()


def test_schema_is_valid_and_example_validates() -> None:
    validate(example())


def test_top_level_identity_fields_are_locked() -> None:
    record = example()
    record["schema_version"] = "wrong"
    assert validation_errors(record)

    record = example()
    record["relation_type"] = "wrong"
    assert validation_errors(record)

    record = example()
    record["tool"]["id"] = "wrong-tool"
    assert validation_errors(record)

    record = example()
    record["comparison_identity"]["canonicalization"] = "unspecified"
    assert validation_errors(record)


def test_example_and_observed_record_boundaries_are_explicit() -> None:
    record = example()
    assert record["record_status"] == "example"
    assert record["comparison_identity"]["comparison_scope"] == "example"
    assert (
        record["observation_bindings"]["compute_binding_report"]["record_status"]
        == "example"
    )

    record["record_status"] = "observed"
    assert validation_errors(record)

    validate(as_observed(example()))


def test_ok_controls_errors_and_success_prerequisites() -> None:
    record = example()
    record["ok"] = False
    record["errors"] = ["synthetic_contract_error"]
    record["summary"]["comparison_complete"] = False
    validate(record)

    record = example()
    record["ok"] = True
    record["errors"] = ["unexpected"]
    assert validation_errors(record)

    record = example()
    record["ok"] = False
    record["errors"] = []
    record["summary"]["comparison_complete"] = False
    assert validation_errors(record)

    record = example()
    record["comparison_boundary"]["plan_target_matches_subject_repository"] = False
    assert validation_errors(record)

    record = example()
    record["plan_binding"]["apply_eligible"] = False
    assert validation_errors(record)


def test_authority_boundary_is_non_active_and_non_authorizing() -> None:
    locked_false = (
        "writes_target_repository",
        "mutates_subject_run",
        "changes_release_authority",
        "changes_gate_policy",
        "changes_gate_semantics",
        "creates_release_decision",
        "creates_gate_result",
        "activates_compute_gate",
        "creates_compute_budget",
        "relation_record_is_release_authority",
    )

    for field in locked_false:
        record = example()
        record["authority_boundary"][field] = True
        assert validation_errors(record), field

    record = example()
    record["authority_boundary"]["write_mode"] = "apply"
    assert validation_errors(record)


def test_comparison_boundary_relations_are_locked() -> None:
    locked = {
        "presence_implies_execution": False,
        "execution_implies_downstream_consumption": False,
        "expectation_basis_required_for_execution": True,
        "observer_in_subject_totals": False,
        "comparison_writes_subject": False,
    }

    for field, expected in locked.items():
        record = example()
        record["comparison_boundary"][field] = not expected
        assert validation_errors(record), field


def test_identifier_keyed_record_surfaces_are_required() -> None:
    for field in ("expectations", "observations", "relations", "findings"):
        record = example()
        record[field] = list(record[field].values())
        assert validation_errors(record), field

    record = example()
    value = record["expectations"].pop(
        "expectation:execute-policy-materializer"
    )
    record["expectations"]["invalid-key"] = value
    assert validation_errors(record)

    record = example()
    value = record["observations"].pop("observation:policy-materializer")
    record["observations"]["invalid-key"] = value
    assert validation_errors(record)

    record = example()
    value = record["relations"].pop("relation:execute-policy-materializer")
    record["relations"]["invalid-key"] = value
    assert validation_errors(record)


def test_record_values_cannot_reintroduce_redundant_identifiers() -> None:
    record = example()
    expectation(
        record,
        "expectation:execute-policy-materializer",
    )["expectation_id"] = "expectation:duplicate"
    assert validation_errors(record)

    record = example()
    observation(
        record,
        "observation:policy-materializer",
    )["observation_id"] = "observation:duplicate"
    assert validation_errors(record)

    record = example()
    relation(
        record,
        "relation:execute-policy-materializer",
    )["relation_id"] = "relation:duplicate"
    assert validation_errors(record)


def test_analysis_level_and_runtime_admission_are_synchronized() -> None:
    record = example()
    record["comparison_boundary"]["observed_analysis_level"] = "runtime_observed"
    assert validation_errors(record)

    record = example()
    record["observation_bindings"]["compute_binding_report"][
        "analysis_level"
    ] = "runtime_observed"
    assert validation_errors(record)

    validate(as_runtime_observed(example()))


def test_runtime_status_none_rejects_runtime_observations() -> None:
    record = example()
    runtime_observation = copy.deepcopy(
        observation(record, "observation:policy-materializer")
    )
    runtime_observation.update(
        {
            "observation_kind": "runtime_execution",
            "source_record_kind": "runtime_observation_packet",
            "source_record_id": "execution:runtime-observer",
        }
    )
    record["observations"]["observation:runtime-observer"] = runtime_observation
    assert validation_errors(record)


def test_runtime_packet_binding_requires_release_candidate() -> None:
    record = as_runtime_observed(example())
    del record["observation_bindings"]["runtime_observation_packets"][0][
        "release_candidate_id"
    ]
    assert validation_errors(record)


def test_runtime_status_and_coverage_status_must_match() -> None:
    record = as_runtime_observed(example())
    record["coverage"]["runtime_observation_status"] = "complete"
    assert validation_errors(record)


def test_binding_report_action_vocabulary_is_losslessly_accepted() -> None:
    record = example()
    source = observation(
        record,
        "observation:policy-materializer",
    )["source_identity"]
    source["source_kind"] = "action"
    validate(record)


def test_exact_github_action_identity_requires_resolved_commit() -> None:
    record = example()
    source = observation(
        record,
        "observation:policy-materializer",
    )["source_identity"]
    source.update(
        {
            "source_kind": "github_action",
            "source_path_or_uri": None,
            "source_revision": None,
            "source_sha256": None,
            "action_repository": "actions/checkout",
            "action_ref": "v4",
            "action_commit_sha": None,
        }
    )
    assert validation_errors(record)

    source["action_commit_sha"] = "a" * 40
    validate(record)


def test_unknown_source_identity_cannot_carry_claimed_fields() -> None:
    record = example()
    source = observation(
        record,
        "observation:policy-materializer",
    )["source_identity"]
    source["identity_status"] = "unknown"
    assert validation_errors(record)

    source.update(
        {
            "source_kind": "unknown",
            "source_path_or_uri": None,
            "source_revision": None,
            "source_sha256": None,
            "action_repository": None,
            "action_ref": None,
            "action_commit_sha": None,
            "container_image_digest": None,
        }
    )
    validate(record)


def test_plan_operation_action_is_bound_to_target_state() -> None:
    record = example()
    operation = expectation(
        record,
        "expectation:execute-policy-materializer",
    )["plan_operation_refs"][0]
    operation["action"] = "create"
    assert validation_errors(record)

    operation["target_state"] = "missing"
    validate(record)

    operation["action"] = "preserve"
    assert validation_errors(record)


def test_presence_only_expectation_cannot_claim_execution_or_authority() -> None:
    record = example()
    expected = expectation(record, "expectation:presence-status-schema")
    expected["expected_compute"]["execution_required"] = True
    assert validation_errors(record)

    record = example()
    expected = expectation(record, "expectation:presence-status-schema")
    expected["expected_declared_role"] = "evidence"
    assert validation_errors(record)

    record = example()
    expected = expectation(record, "expectation:presence-status-schema")
    expected["expected_mutation_authority"] = "verifier_state"
    assert validation_errors(record)


def test_execution_expectation_requires_explicit_execution_basis() -> None:
    record = example()
    expected = expectation(record, "expectation:execute-policy-materializer")
    for basis in expected["basis_records"]:
        basis["supports"] = [
            support
            for support in basis["supports"]
            if support != "execution_expectation"
        ]
    assert validation_errors(record)


def test_execution_expectation_requires_selector_or_exact_source() -> None:
    record = example()
    expected = expectation(record, "expectation:execute-policy-materializer")
    expected["expected_compute"]["selector"] = {
        "node_type": "unknown",
        "workflow_name": None,
        "job_name": None,
        "step_name": None,
        "tool_id": None,
        "command_sha256": None,
    }
    expected["expected_source_identity"] = {
        "source_kind": "unknown",
        "identity_status": "unknown",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
        "action_repository": None,
        "action_ref": None,
        "action_commit_sha": None,
        "container_image_digest": None,
    }
    assert validation_errors(record)


def test_consumption_expectation_requires_explicit_consumption_basis() -> None:
    record = example()
    expected = expectation(
        record,
        "expectation:execute-status-validator-consumed",
    )
    for basis in expected["basis_records"]:
        basis["supports"] = [
            support
            for support in basis["supports"]
            if support != "downstream_consumption_expectation"
        ]
    assert validation_errors(record)


def test_declared_role_and_authority_claims_require_supporting_bases() -> None:
    record = example()
    expected = expectation(record, "expectation:execute-policy-materializer")
    for basis in expected["basis_records"]:
        basis["supports"] = [
            support for support in basis["supports"] if support != "declared_role"
        ]
    assert validation_errors(record)

    record = example()
    expected = expectation(record, "expectation:execute-policy-materializer")
    for basis in expected["basis_records"]:
        basis["supports"] = [
            support
            for support in basis["supports"]
            if support != "mutation_authority"
        ]
    assert validation_errors(record)


def test_downstream_consumption_status_controls_evidence_shape() -> None:
    record = example()
    consumed = observation(
        record,
        "observation:status-validator",
    )["downstream_consumption"]
    consumed["consumer_ids"] = []
    consumed["edge_ids"] = []
    assert validation_errors(record)

    record = example()
    consumed = observation(
        record,
        "observation:status-validator",
    )["downstream_consumption"]
    consumed["status"] = "not_observed"
    assert validation_errors(record)

    consumed["consumer_ids"] = []
    consumed["edge_ids"] = []
    validate(record)


def test_observation_kind_is_bound_to_source_record_kind() -> None:
    record = example()
    observed = observation(record, "observation:policy-materializer")
    observed["observation_kind"] = "runtime_execution"
    assert validation_errors(record)

    record = as_runtime_observed(example())
    observed = observation(record, "observation:policy-materializer")
    observed.update(
        {
            "observation_kind": "runtime_execution",
            "source_record_kind": "runtime_observation_packet",
            "source_record_id": "execution:policy-materializer",
        }
    )
    validate(record)


def test_unbound_authoritative_mutation_is_mechanically_derived() -> None:
    record = example()
    observed = observation(record, "observation:policy-materializer")
    observed["binding_status"] = "none"
    observed["binding_class"] = "unbound"
    observed["observed_mutation_classes"] = ["final_status"]
    observed["unbound_authoritative_mutation"] = False
    assert validation_errors(record)

    observed["unbound_authoritative_mutation"] = True
    validate(record)

    observed["observed_mutation_classes"] = ["advisory_output"]
    assert validation_errors(record)

    observed["unbound_authoritative_mutation"] = False
    validate(record)


def test_relation_statuses_lock_reference_and_evaluation_shapes() -> None:
    record = example()
    linked = relation(record, "relation:execute-policy-materializer")
    linked["observation_ids"] = []
    assert validation_errors(record)

    record = example()
    presence = relation(record, "relation:presence-status-schema")
    presence["observation_ids"] = ["observation:policy-materializer"]
    assert validation_errors(record)

    record = example()
    linked = relation(record, "relation:execute-policy-materializer")
    linked["relation_status"] = "source_digest_mismatch"
    assert validation_errors(record)

    linked["evaluation"]["source_identity"] = "mismatch"
    validate(record)


def test_decisive_absence_requires_complete_coverage() -> None:
    record = example()
    linked = relation(record, "relation:execute-policy-materializer")
    linked.update(
        {
            "observation_ids": [],
            "relation_status": "planned_but_not_observed",
        }
    )
    linked["evaluation"] = {
        "execution_observation": "not_observed",
        "execution_identity": "not_required",
        "source_identity": "not_required",
        "run_binding": "not_required",
        "declared_role": "not_required",
        "authority_class": "not_required",
        "downstream_consumption": "not_required",
        "coverage": "partial",
        "decisive": True,
    }
    assert validation_errors(record)

    linked["evaluation"]["coverage"] = "complete"
    validate(record)


def test_ambiguous_and_coverage_unresolved_relations_are_non_decisive() -> None:
    record = example()
    ambiguous = relation(record, "relation:execute-policy-materializer")
    ambiguous["relation_status"] = "ambiguous_observation_match"
    ambiguous["observation_ids"] = [
        "observation:policy-materializer",
        "observation:status-validator",
    ]
    ambiguous["evaluation"]["execution_observation"] = "unresolved"
    ambiguous["evaluation"]["decisive"] = True
    assert validation_errors(record)

    ambiguous["evaluation"]["decisive"] = False
    validate(record)

    record = example()
    unresolved = relation(record, "relation:execute-policy-materializer")
    unresolved["relation_status"] = "unresolved_due_to_coverage"
    unresolved["evaluation"]["execution_observation"] = "unresolved"
    unresolved["evaluation"]["coverage"] = "complete"
    unresolved["evaluation"]["decisive"] = False
    assert validation_errors(record)

    unresolved["evaluation"]["coverage"] = "partial"
    validate(record)


def test_complete_coverage_rejects_explicit_gaps() -> None:
    mutations = (
        ("missing_plan_operation_refs", ["plan-operation:missing"]),
        (
            "unclassified_expectation_ids",
            ["expectation:execute-policy-materializer"],
        ),
        (
            "unclassified_observation_ids",
            ["observation:policy-materializer"],
        ),
        ("unresolved_reasons", ["artifact_coverage_partial"]),
    )

    for field, value in mutations:
        record = example()
        record["coverage"][field] = value
        assert validation_errors(record), field

    for field in (
        "identity_coverage_status",
        "execution_coverage_status",
        "declared_role_coverage_status",
        "authority_coverage_status",
        "downstream_consumption_coverage_status",
    ):
        record = example()
        record["coverage"][field] = "partial"
        assert validation_errors(record), field


def test_comparison_complete_rejects_unresolved_summary_counts() -> None:
    for field in (
        "ambiguous_observation_match",
        "unresolved_due_to_coverage",
        "unresolved_relations",
    ):
        record = example()
        record["summary"][field] = 1
        assert validation_errors(record), field

    record = example()
    record["coverage"]["comparison_status"] = "partial"
    assert validation_errors(record)


def test_sha_and_commit_lengths_are_enforced() -> None:
    record = example()
    record["comparison_identity"]["subject_source_commit"] = "a" * 39
    assert validation_errors(record)

    record = example()
    record["plan_binding"]["sha256"] = "b" * 63
    assert validation_errors(record)

    record = example()
    expected = expectation(record, "expectation:execute-policy-materializer")
    expected["plan_operation_refs"][0]["operation_sha256"] = "c" * 63
    assert validation_errors(record)


def test_nested_extra_properties_are_rejected() -> None:
    paths = (
        ("tool",),
        ("comparison_identity",),
        ("plan_binding",),
        ("comparison_boundary",),
        ("coverage",),
        ("summary",),
        ("authority_boundary",),
    )

    for path in paths:
        record = example()
        record[path[0]]["extra"] = "not allowed"
        assert validation_errors(record), path

    record = example()
    expectation(
        record,
        "expectation:execute-policy-materializer",
    )["extra"] = "not allowed"
    assert validation_errors(record)

    record = example()
    observation(
        record,
        "observation:policy-materializer",
    )["extra"] = "not allowed"
    assert validation_errors(record)

    record = example()
    relation(
        record,
        "relation:execute-policy-materializer",
    )["extra"] = "not allowed"
    assert validation_errors(record)


def test_example_has_no_active_gate_budget_or_decision_surface() -> None:
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
        "release_decision",
    }
    assert forbidden.isdisjoint(example())


def check_pulsemech_compute_planned_observed_relation_schema_v0() -> None:
    test_contract_files_exist()
    test_schema_is_valid_and_example_validates()
    test_top_level_identity_fields_are_locked()
    test_example_and_observed_record_boundaries_are_explicit()
    test_ok_controls_errors_and_success_prerequisites()
    test_authority_boundary_is_non_active_and_non_authorizing()
    test_comparison_boundary_relations_are_locked()
    test_identifier_keyed_record_surfaces_are_required()
    test_record_values_cannot_reintroduce_redundant_identifiers()
    test_analysis_level_and_runtime_admission_are_synchronized()
    test_runtime_status_none_rejects_runtime_observations()
    test_runtime_packet_binding_requires_release_candidate()
    test_runtime_status_and_coverage_status_must_match()
    test_binding_report_action_vocabulary_is_losslessly_accepted()
    test_exact_github_action_identity_requires_resolved_commit()
    test_unknown_source_identity_cannot_carry_claimed_fields()
    test_plan_operation_action_is_bound_to_target_state()
    test_presence_only_expectation_cannot_claim_execution_or_authority()
    test_execution_expectation_requires_explicit_execution_basis()
    test_execution_expectation_requires_selector_or_exact_source()
    test_consumption_expectation_requires_explicit_consumption_basis()
    test_declared_role_and_authority_claims_require_supporting_bases()
    test_downstream_consumption_status_controls_evidence_shape()
    test_observation_kind_is_bound_to_source_record_kind()
    test_unbound_authoritative_mutation_is_mechanically_derived()
    test_relation_statuses_lock_reference_and_evaluation_shapes()
    test_decisive_absence_requires_complete_coverage()
    test_ambiguous_and_coverage_unresolved_relations_are_non_decisive()
    test_complete_coverage_rejects_explicit_gaps()
    test_comparison_complete_rejects_unresolved_summary_counts()
    test_sha_and_commit_lengths_are_enforced()
    test_nested_extra_properties_are_rejected()
    test_example_has_no_active_gate_budget_or_decision_surface()


def test_pulsemech_compute_planned_observed_relation_schema_v0() -> None:
    check_pulsemech_compute_planned_observed_relation_schema_v0()


if __name__ == "__main__":
    check_pulsemech_compute_planned_observed_relation_schema_v0()
    print("OK: PULSEmech planned-observed relation schema v0 contract passed")
