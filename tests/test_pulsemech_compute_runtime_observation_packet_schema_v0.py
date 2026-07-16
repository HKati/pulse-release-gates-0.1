#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_runtime_observation_packet_example_v0.json"
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
    return json.loads(json.dumps(_EXAMPLE))


def validator() -> jsonschema.Draft202012Validator:
    return _VALIDATOR


def validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in validator().iter_errors(instance)
    ]


def validate(instance: dict[str, Any]) -> None:
    validator().validate(instance)


def first_execution(packet: dict[str, Any], execution_id: str) -> dict[str, Any]:
    return next(
        execution
        for execution in packet["executions"]
        if execution["execution_id"] == execution_id
    )


def first_measurement(packet: dict[str, Any], axis: str) -> dict[str, Any]:
    return next(
        measurement
        for measurement in packet["resource_measurements"]
        if measurement["axis"] == axis
    )


def test_contract_files_exist() -> None:
    assert SCHEMA_PATH.is_file()
    assert EXAMPLE_PATH.is_file()


def test_schema_is_valid_and_example_validates() -> None:
    validate(example())


def test_top_level_identity_fields_are_locked() -> None:
    packet = example()
    packet["schema_version"] = "wrong"
    assert validation_errors(packet)

    packet = example()
    packet["packet_type"] = "wrong"
    assert validation_errors(packet)

    packet = example()
    packet["record_status"] = "unknown"
    assert validation_errors(packet)


def test_example_identity_is_explicit() -> None:
    packet = example()

    assert packet["record_status"] == "example"
    assert packet["packet_identity"]["packet_scope"] == "example"
    assert packet["producer"]["collection_mode"] == "example"
    assert packet["observation_boundary"]["collector_mode"] == "example"
    assert packet["observation_boundary"]["target_analysis_level"] == (
        "runtime_observed"
    )


def test_example_and_observed_collection_modes_cannot_be_mixed() -> None:
    packet = example()
    packet["observation_boundary"]["collector_mode"] = "tool_wrapper"
    assert validation_errors(packet)

    packet = example()
    packet["record_status"] = "observed"
    assert validation_errors(packet)

    packet = example()
    packet["record_status"] = "observed"
    packet["producer"]["collection_mode"] = "tool_wrapper"
    packet["packet_identity"]["packet_scope"] = "subject_run"
    packet["observation_boundary"]["collector_mode"] = "tool_wrapper"
    validate(packet)


def test_packet_ok_controls_errors_only() -> None:
    packet = example()
    packet["ok"] = False
    packet["errors"] = ["synthetic_contract_error"]
    validate(packet)

    packet = example()
    packet["ok"] = True
    packet["errors"] = ["unexpected"]
    assert validation_errors(packet)

    packet = example()
    packet["ok"] = False
    packet["errors"] = []
    assert validation_errors(packet)


def test_packet_sequence_requires_an_exact_predecessor_chain() -> None:
    packet = example()
    assert packet["packet_identity"]["packet_sequence"] == 0
    assert packet["packet_identity"]["previous_packet_sha256"] is None

    packet["packet_identity"]["previous_packet_sha256"] = "a" * 64
    assert validation_errors(packet)

    packet = example()
    packet["packet_identity"]["packet_sequence"] = 1
    packet["packet_identity"]["previous_packet_sha256"] = None
    assert validation_errors(packet)

    packet["packet_identity"]["previous_packet_sha256"] = "a" * 64
    validate(packet)


def test_packet_canonicalization_is_locked() -> None:
    packet = example()
    packet["packet_identity"]["canonicalization"] = "unspecified"
    assert validation_errors(packet)


def test_all_utc_fields_require_canonical_z_notation() -> None:
    mutations = [
        ("packet_identity", "packet_created_utc"),
        ("observation_boundary", "capture_started_utc"),
        ("observation_boundary", "capture_completed_utc"),
    ]

    for section, field in mutations:
        packet = example()
        packet[section][field] = "2026-07-15T12:00:00+02:00"
        assert validation_errors(packet), (section, field)

    packet = example()
    packet["executions"][0]["timing"]["started_utc"] = (
        "2026-07-15T12:00:00+00:00"
    )
    assert validation_errors(packet)


def test_subject_and_observer_boundaries_are_locked() -> None:
    packet = example()
    packet["observation_boundary"]["observer_in_subject_totals"] = True
    assert validation_errors(packet)

    packet = example()
    packet["observation_boundary"]["subject_artifacts_mutated"] = True
    assert validation_errors(packet)

    packet = example()
    packet["observation_boundary"]["target_analysis_level"] = (
        "artifact_observed"
    )
    assert validation_errors(packet)


def test_authority_inputs_are_exact_digest_bound_records() -> None:
    expected = {
        "workflow": "workflow",
        "policy": "policy",
        "gate_registry": "gate_registry",
    }

    for section, role in expected.items():
        packet = example()
        record = packet["authority_inputs"][section]
        assert record["role"] == role
        assert len(record["source_commit"]) == 40
        assert len(record["sha256"]) == 64

        record["role"] = "other"
        assert validation_errors(packet), section

    packet = example()
    packet["authority_inputs"]["workflow"]["sha256"] = "a" * 63
    assert validation_errors(packet)


def test_privacy_boundary_forbids_raw_or_secret_material() -> None:
    forbidden_flags = [
        "raw_environment_included",
        "secret_values_included",
        "authorization_headers_included",
        "cookies_included",
        "request_bodies_included",
        "response_bodies_included",
        "raw_prompt_text_included",
        "raw_model_output_included",
    ]

    for field in forbidden_flags:
        packet = example()
        packet["privacy_boundary"][field] = True
        assert validation_errors(packet), field


def test_redaction_requires_an_exact_rule_digest() -> None:
    packet = example()
    packet["privacy_boundary"]["redaction_applied"] = True
    packet["privacy_boundary"]["redaction_rules_sha256"] = None
    assert validation_errors(packet)

    packet["privacy_boundary"]["redaction_rules_sha256"] = "d" * 64
    validate(packet)


def test_exact_github_action_identity_requires_resolved_commit() -> None:
    packet = example()
    execution = packet["executions"][0]
    execution["execution_kind"] = "github_action"
    execution["source_identity"] = {
        "source_kind": "github_action",
        "identity_status": "exact",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
        "action_repository": "actions/checkout",
        "action_ref": "v4",
        "action_commit_sha": None,
        "container_image_digest": None,
    }
    assert validation_errors(packet)

    execution["source_identity"]["action_commit_sha"] = "a" * 40
    validate(packet)


def test_partial_github_action_identity_may_preserve_mutable_ref() -> None:
    packet = example()
    execution = packet["executions"][0]
    execution["execution_kind"] = "github_action"
    execution["source_identity"] = {
        "source_kind": "github_action",
        "identity_status": "partial",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
        "action_repository": "actions/checkout",
        "action_ref": "v4",
        "action_commit_sha": None,
        "container_image_digest": None,
    }
    validate(packet)


def test_unknown_source_identity_cannot_carry_claimed_identity_fields() -> None:
    packet = example()
    source = packet["executions"][0]["source_identity"]
    source["identity_status"] = "unknown"
    assert validation_errors(packet)

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
    validate(packet)


def test_raw_command_and_environment_surfaces_are_forbidden() -> None:
    packet = example()
    packet["executions"][0]["command_identity"]["raw_command_included"] = True
    assert validation_errors(packet)

    packet = example()
    packet["executions"][0]["execution_environment"][
        "raw_environment_included"
    ] = True
    assert validation_errors(packet)


def test_observation_collector_execution_is_role_bound() -> None:
    packet = example()
    collector = first_execution(packet, "execution:runtime-observation-collector")
    collector["execution_kind"] = "workflow_step"
    assert validation_errors(packet)

    packet = example()
    collector = first_execution(packet, "execution:runtime-observation-collector")
    collector["declared_role"] = "advisory"
    assert validation_errors(packet)

    packet = example()
    collector = first_execution(packet, "execution:runtime-observation-collector")
    collector["permitted_mutation_authority"] = "release_evidence"
    assert validation_errors(packet)


def test_observer_role_cannot_be_assigned_to_subject_execution() -> None:
    packet = example()
    packet["executions"][0]["declared_role"] = "observer"
    assert validation_errors(packet)


def test_state_exact_digest_and_unavailable_states_are_distinct() -> None:
    packet = example()
    state = packet["state_observations"][0]
    state["sha256"] = None
    assert validation_errors(packet)

    packet = example()
    state = packet["state_observations"][0]
    state["content_status"] = "unavailable"
    state["sha256"] = None
    state["size_bytes"] = None
    validate(packet)

    state["sha256"] = "a" * 64
    assert validation_errors(packet)


def test_non_authority_state_cannot_claim_authoritative_mutation_class() -> None:
    packet = example()
    state = packet["state_observations"][0]
    assert state["authority_bearing"] is False
    state["mutation_class"] = "final_status"
    assert validation_errors(packet)


def test_payload_metadata_only_requires_metadata_digest() -> None:
    packet = example()
    payload = packet["external_calls"][0]["request"]["payload"]
    payload["capture_status"] = "metadata_only"
    payload["metadata_sha256"] = None
    payload["body_sha256"] = None
    payload["body_size_bytes"] = None
    assert validation_errors(packet)

    payload["metadata_sha256"] = "b" * 64
    validate(packet)

    payload["body_sha256"] = "c" * 64
    assert validation_errors(packet)


def test_payload_not_recorded_has_no_digest_size_or_state_reference() -> None:
    packet = example()
    payload = packet["external_calls"][0]["request"]["payload"]
    payload.update(
        {
            "capture_status": "not_recorded",
            "metadata_sha256": None,
            "body_sha256": None,
            "body_size_bytes": None,
            "state_ids": [],
        }
    )
    validate(packet)

    payload["state_ids"] = ["state:external-request-metadata"]
    assert validation_errors(packet)


def test_external_call_payload_forbids_raw_bodies_and_credentials() -> None:
    packet = example()
    packet["external_calls"][0]["request"][
        "authorization_material_included"
    ] = True
    assert validation_errors(packet)

    packet = example()
    packet["external_calls"][0]["request"]["cookies_included"] = True
    assert validation_errors(packet)

    packet = example()
    packet["external_calls"][0]["response"]["set_cookie_included"] = True
    assert validation_errors(packet)

    packet = example()
    packet["external_calls"][0]["request"]["payload"][
        "raw_body_included"
    ] = True
    assert validation_errors(packet)


def test_model_revision_is_not_an_exact_model_content_digest() -> None:
    packet = example()
    identity = packet["model_inferences"][0]["model_identity"]
    assert identity["model_content_digest_status"] == "provider_revision_only"
    assert identity["model_sha256"] is None

    identity["model_sha256"] = "a" * 64
    assert validation_errors(packet)

    packet = example()
    identity = packet["model_inferences"][0]["model_identity"]
    identity["model_content_digest_status"] = "exact_digest"
    identity["model_sha256"] = None
    assert validation_errors(packet)

    identity["model_sha256"] = "a" * 64
    validate(packet)


def test_recorded_model_output_requires_state_and_metadata_digest() -> None:
    packet = example()
    response = packet["model_inferences"][0]["response"]
    assert response["output_capture_status"] == "recorded"

    response["output_state_ids"] = []
    assert validation_errors(packet)

    packet = example()
    response = packet["model_inferences"][0]["response"]
    response["response_metadata_sha256"] = None
    assert validation_errors(packet)


def test_failed_model_call_can_be_recorded_without_fabricated_output() -> None:
    packet = example()
    inference = packet["model_inferences"][0]
    inference["capture_status"] = "partial"
    inference["result"] = {
        "result_status": "complete",
        "lifecycle_status": "completed",
        "outcome": "timed_out",
        "exit_code": None,
    }
    inference["response"] = {
        "output_capture_status": "no_output",
        "output_state_ids": [],
        "response_metadata_sha256": None,
        "raw_output_included": False,
    }
    validate(packet)

    inference["response"]["output_state_ids"] = [
        "state:model-response-metadata"
    ]
    assert validation_errors(packet)


def test_complete_model_inference_requires_recorded_response() -> None:
    packet = example()
    inference = packet["model_inferences"][0]
    inference["capture_status"] = "complete"
    inference["response"]["output_capture_status"] = "no_output"
    inference["response"]["output_state_ids"] = []
    assert validation_errors(packet)


def test_model_usage_complete_partial_and_unavailable_are_distinct() -> None:
    packet = example()
    usage = packet["model_inferences"][0]["usage"]
    usage.update(
        {
            "usage_status": "partial",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
    )
    assert validation_errors(packet)

    usage["input_tokens"] = 512
    validate(packet)

    packet = example()
    usage = packet["model_inferences"][0]["usage"]
    usage.update(
        {
            "usage_status": "unavailable",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
    )
    validate(packet)

    usage["output_tokens"] = 1
    assert validation_errors(packet)

    packet = example()
    usage = packet["model_inferences"][0]["usage"]
    usage["usage_status"] = "complete"
    usage["total_tokens"] = None
    assert validation_errors(packet)


def test_measurement_target_id_must_match_target_kind() -> None:
    packet = example()
    measurement = first_measurement(packet, "external_api_calls")
    measurement["target_kind"] = "execution"
    assert validation_errors(packet)

    packet = example()
    measurement = first_measurement(packet, "model_input_tokens")
    measurement["target_kind"] = "external_call"
    assert validation_errors(packet)

    packet = example()
    measurement = first_measurement(packet, "step_wall_seconds")
    measurement["target_kind"] = "model_inference"
    assert validation_errors(packet)


def test_resource_axis_unit_and_value_type_are_locked() -> None:
    packet = example()
    measurement = first_measurement(packet, "model_input_tokens")
    measurement["unit"] = "count"
    assert validation_errors(packet)

    packet = example()
    measurement = first_measurement(packet, "network_bytes_sent")
    measurement["value"] = 1.5
    assert validation_errors(packet)

    packet = example()
    measurement = first_measurement(packet, "step_wall_seconds")
    measurement["unit"] = "tokens"
    assert validation_errors(packet)


def test_resource_measurements_cannot_be_estimated() -> None:
    packet = example()
    packet["resource_measurements"][0]["estimated"] = True
    assert validation_errors(packet)


def test_complete_coverage_cannot_contain_explicit_gaps() -> None:
    packet = example()
    coverage = packet["coverage"]
    coverage["coverage_status"] = "complete"
    coverage["missing_execution_ids"] = ["execution:missing"]
    assert validation_errors(packet)

    packet = example()
    coverage = packet["coverage"]
    coverage["coverage_status"] = "complete"
    coverage["unobserved_reasons"] = ["resource_axis_unavailable"]
    assert validation_errors(packet)

    packet = example()
    coverage = packet["coverage"]
    coverage["coverage_status"] = "complete"
    coverage["expected_job_count"] = None
    assert validation_errors(packet)

    packet = example()
    coverage = packet["coverage"]
    coverage["coverage_status"] = "complete"
    coverage["expected_step_count"] = None
    assert validation_errors(packet)


def test_schema_leaves_cross_field_count_equality_to_strict_validator() -> None:
    packet = example()
    coverage = packet["coverage"]
    coverage["coverage_status"] = "complete"
    coverage["missing_execution_ids"] = []
    coverage["unobserved_reasons"] = []
    coverage["expected_job_count"] = 999
    coverage["expected_step_count"] = 999

    # Portable Draft 2020-12 JSON Schema cannot compare sibling numeric fields.
    # The strict semantic validator introduced in the next contract file must
    # reject this mismatch by recomputing the counts from execution records.
    validate(packet)


def test_identifier_prefixes_are_enforced() -> None:
    packet = example()
    packet["executions"][0]["execution_id"] = "state:not-execution"
    assert validation_errors(packet)

    packet = example()
    packet["state_observations"][0]["state_id"] = "call:not-state"
    assert validation_errors(packet)

    packet = example()
    packet["external_calls"][0]["call_id"] = "execution:not-call"
    assert validation_errors(packet)

    packet = example()
    packet["model_inferences"][0]["inference_id"] = "call:not-inference"
    assert validation_errors(packet)

    packet = example()
    packet["resource_measurements"][0]["measurement_id"] = (
        "execution:not-measurement"
    )
    assert validation_errors(packet)


def test_sha_and_commit_lengths_are_enforced() -> None:
    packet = example()
    packet["subject"]["source_commit"] = "a" * 39
    assert validation_errors(packet)

    packet = example()
    packet["producer"]["producer_source_sha256"] = "b" * 63
    assert validation_errors(packet)

    packet = example()
    packet["authority_inputs"]["policy"]["sha256"] = "c" * 65
    assert validation_errors(packet)


def test_top_level_activation_and_release_surfaces_are_not_allowed() -> None:
    forbidden = [
        "decision",
        "status_gates",
        "required",
        "release_required",
        "blocking",
        "active_compute_gates",
        "compute_budget",
        "overall_efficiency",
    ]

    for field in forbidden:
        packet = example()
        packet[field] = True
        assert validation_errors(packet), field


def test_nested_extra_properties_are_rejected() -> None:
    nested_objects = [
        "producer",
        "packet_identity",
        "subject",
        "authority_inputs",
        "observation_boundary",
        "timing_basis",
        "privacy_boundary",
        "coverage",
    ]

    for field in nested_objects:
        packet = example()
        packet[field]["extra"] = "not allowed"
        assert validation_errors(packet), field

    packet = example()
    packet["executions"][0]["extra"] = "not allowed"
    assert validation_errors(packet)

    packet = example()
    packet["state_observations"][0]["extra"] = "not allowed"
    assert validation_errors(packet)

    packet = example()
    packet["external_calls"][0]["extra"] = "not allowed"
    assert validation_errors(packet)

    packet = example()
    packet["model_inferences"][0]["extra"] = "not allowed"
    assert validation_errors(packet)

    packet = example()
    packet["resource_measurements"][0]["extra"] = "not allowed"
    assert validation_errors(packet)


def test_example_contains_no_raw_or_active_authority_surface() -> None:
    packet = example()
    forbidden = {
        "decision",
        "status_gates",
        "required",
        "core_required",
        "release_required",
        "prod_required",
        "stage_required",
        "blocking",
        "release_blocking",
        "gate_materialization",
        "active_compute_gates",
        "compute_budget",
        "overall_efficiency",
    }
    assert forbidden.isdisjoint(packet)

    assert packet["privacy_boundary"] == {
        "authorization_headers_included": False,
        "cookies_included": False,
        "raw_environment_included": False,
        "raw_model_output_included": False,
        "raw_prompt_text_included": False,
        "redaction_applied": True,
        "redaction_rules_sha256": (
            "b906a6cf6a8b6fbfc6e8a8125ffb82ddaf57b08ab000c77249afec5088a36006"
        ),
        "request_bodies_included": False,
        "response_bodies_included": False,
        "secret_values_included": False,
    }


def check_pulsemech_compute_runtime_observation_packet_schema_v0() -> None:
    test_contract_files_exist()
    test_schema_is_valid_and_example_validates()
    test_top_level_identity_fields_are_locked()
    test_example_identity_is_explicit()
    test_example_and_observed_collection_modes_cannot_be_mixed()
    test_packet_ok_controls_errors_only()
    test_packet_sequence_requires_an_exact_predecessor_chain()
    test_packet_canonicalization_is_locked()
    test_all_utc_fields_require_canonical_z_notation()
    test_subject_and_observer_boundaries_are_locked()
    test_authority_inputs_are_exact_digest_bound_records()
    test_privacy_boundary_forbids_raw_or_secret_material()
    test_redaction_requires_an_exact_rule_digest()
    test_exact_github_action_identity_requires_resolved_commit()
    test_partial_github_action_identity_may_preserve_mutable_ref()
    test_unknown_source_identity_cannot_carry_claimed_identity_fields()
    test_raw_command_and_environment_surfaces_are_forbidden()
    test_observation_collector_execution_is_role_bound()
    test_observer_role_cannot_be_assigned_to_subject_execution()
    test_state_exact_digest_and_unavailable_states_are_distinct()
    test_non_authority_state_cannot_claim_authoritative_mutation_class()
    test_payload_metadata_only_requires_metadata_digest()
    test_payload_not_recorded_has_no_digest_size_or_state_reference()
    test_external_call_payload_forbids_raw_bodies_and_credentials()
    test_model_revision_is_not_an_exact_model_content_digest()
    test_recorded_model_output_requires_state_and_metadata_digest()
    test_failed_model_call_can_be_recorded_without_fabricated_output()
    test_complete_model_inference_requires_recorded_response()
    test_model_usage_complete_partial_and_unavailable_are_distinct()
    test_measurement_target_id_must_match_target_kind()
    test_resource_axis_unit_and_value_type_are_locked()
    test_resource_measurements_cannot_be_estimated()
    test_complete_coverage_cannot_contain_explicit_gaps()
    test_schema_leaves_cross_field_count_equality_to_strict_validator()
    test_identifier_prefixes_are_enforced()
    test_sha_and_commit_lengths_are_enforced()
    test_top_level_activation_and_release_surfaces_are_not_allowed()
    test_nested_extra_properties_are_rejected()
    test_example_contains_no_raw_or_active_authority_surface()


def test_pulsemech_compute_runtime_observation_packet_schema_v0() -> None:
    check_pulsemech_compute_runtime_observation_packet_schema_v0()


if __name__ == "__main__":
    check_pulsemech_compute_runtime_observation_packet_schema_v0()
    print("OK: PULSEmech compute runtime observation packet schema v0 contract passed")
