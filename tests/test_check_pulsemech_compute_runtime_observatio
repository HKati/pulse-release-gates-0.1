#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "check_pulsemech_compute_runtime_observation_packet_v0.py"
SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_runtime_observation_packet_example_v0.json"
)
GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

EXPECTED_CHECKS = {
    "authority_input_bindings_ok",
    "capture_window_and_packet_time_ok",
    "collector_boundary_ok",
    "coverage_capture_summaries_match",
    "coverage_record_counts_match",
    "coverage_status_semantics_ok",
    "derived_duration_measurements_match_timing",
    "deterministic_ordering_ok",
    "exact_github_action_identity_pinned",
    "execution_graph_acyclic",
    "execution_parent_references_resolve",
    "execution_state_references_resolve",
    "external_call_relations_ok",
    "missing_execution_ids_are_unobserved",
    "model_inference_relations_ok",
    "model_token_measurements_match_usage",
    "mutation_authority_relations_ok",
    "packet_ok_errors_semantics_ok",
    "packet_sequence_chain_ok",
    "packet_type_ok",
    "privacy_boundary_ok",
    "record_identifiers_unique",
    "record_status_collection_modes_ok",
    "redaction_rules_binding_ok",
    "resource_axis_coverage_partition_ok",
    "resource_measurement_relations_ok",
    "runtime_timings_consistent",
    "schema_version_ok",
    "state_authority_and_privacy_ok",
    "state_execution_references_resolve",
    "state_producer_relations_ok",
    "subject_execution_run_binding_ok",
    "subject_run_binding_consistent",
    "workflow_job_step_shape_ok",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_BASE_PACKET = load_json(EXAMPLE)


def packet() -> dict[str, Any]:
    return json.loads(json.dumps(_BASE_PACKET))


def write_packet(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def import_tool_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_runtime_observation_validator_v0_under_test",
        TOOL,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = import_tool_module()


def run_tool(
    *,
    packet_path: Path = EXAMPLE,
    schema_path: Path = SCHEMA,
    output: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(schema_path),
        "--packet",
        str(packet_path),
    ]
    if output is not None:
        command.extend(["--output", str(output)])

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_json_text(text: str) -> dict[str, Any]:
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def assert_cli_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int | None = None,
    stream: str = "stdout",
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    if expected_returncode is not None:
        assert result.returncode == expected_returncode
    assert "Traceback" not in result.stderr

    text = result.stdout if stream == "stdout" else result.stderr
    assert text, result.stdout + result.stderr
    diagnostic = parse_json_text(text)
    assert diagnostic["ok"] is False
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def diagnostic_for(
    value: dict[str, Any],
    tmp_path: Path,
) -> tuple[dict[str, Any], int]:
    packet_path = tmp_path / "packet.json"
    write_packet(packet_path, value)
    return TOOL_MODULE.build_diagnostic(
        schema_path=SCHEMA,
        packet_path=packet_path,
    )


def assert_semantic_failure(
    value: dict[str, Any],
    tmp_path: Path,
    check_name: str,
) -> dict[str, Any]:
    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 1, diagnostic
    assert diagnostic["schema_valid"] is True, diagnostic
    assert diagnostic["checks"][check_name] is False, diagnostic
    assert any(
        f"check_failed: {check_name}" in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def assert_schema_failure(
    value: dict[str, Any],
    tmp_path: Path,
    expected_fragment: str = "schema_error",
) -> dict[str, Any]:
    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 1, diagnostic
    assert diagnostic["schema_valid"] is False, diagnostic
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def execution(value: dict[str, Any], execution_id: str) -> dict[str, Any]:
    return next(
        row
        for row in value["executions"]
        if row["execution_id"] == execution_id
    )


def state(value: dict[str, Any], state_id: str) -> dict[str, Any]:
    return next(
        row
        for row in value["state_observations"]
        if row["state_id"] == state_id
    )


def measurement(value: dict[str, Any], axis: str) -> dict[str, Any]:
    return next(
        row
        for row in value["resource_measurements"]
        if row["axis"] == axis
    )


def snapshot(path: Path) -> tuple[int, str]:
    return path.stat().st_size, sha256_file(path)


# ---------------------------------------------------------------------------
# Positive path and deterministic diagnostics
# ---------------------------------------------------------------------------


def test_contract_files_exist() -> None:
    for path in (TOOL, SCHEMA, EXAMPLE):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_valid_example_passes_all_semantic_checks() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")

    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["tool"] == (
        "check_pulsemech_compute_runtime_observation_packet_v0"
    )
    assert diagnostic["schema_version"] == (
        "pulsemech_compute_runtime_observation_packet_v0"
    )
    assert diagnostic["packet_type"] == (
        "pulsemech_compute_runtime_observation_packet"
    )
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert set(diagnostic["checks"]) == EXPECTED_CHECKS
    assert all(diagnostic["checks"].values())


def test_diagnostic_output_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "diagnostic.json"
    result = run_tool(output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert output.is_file()
    assert output.read_text(encoding="utf-8") == result.stdout
    assert parse_json_text(output.read_text(encoding="utf-8")) == (
        parse_json_text(result.stdout)
    )


def test_identical_inputs_emit_byte_identical_diagnostics(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    first_result = run_tool(output=first)
    second_result = run_tool(output=second)

    assert first_result.returncode == 0
    assert second_result.returncode == 0
    assert first_result.stdout == second_result.stdout
    assert first.read_bytes() == second.read_bytes()


def test_observed_collection_modes_validate(tmp_path: Path) -> None:
    value = packet()
    value["record_status"] = "observed"
    value["producer"]["collection_mode"] = "tool_wrapper"
    value["packet_identity"]["packet_scope"] = "subject_run"
    value["observation_boundary"]["collector_mode"] = "tool_wrapper"

    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 0, diagnostic
    assert diagnostic["ok"] is True
    assert diagnostic["checks"]["record_status_collection_modes_ok"] is True


def test_packet_error_state_is_independent_from_validator_success(
    tmp_path: Path,
) -> None:
    value = packet()
    value["ok"] = False
    value["errors"] = ["synthetic_packet_error"]

    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 0, diagnostic
    assert diagnostic["ok"] is True
    assert diagnostic["schema_valid"] is True
    assert diagnostic["checks"]["packet_ok_errors_semantics_ok"] is True


def test_metadata_only_external_payload_with_digest_validates(
    tmp_path: Path,
) -> None:
    value = packet()
    call = value["external_calls"][0]
    payload = call["request"]["payload"]
    payload["capture_status"] = "metadata_only"
    payload["body_sha256"] = None
    payload["body_size_bytes"] = None
    call["capture_status"] = "partial"
    value["coverage"]["external_call_capture_status"] = "partial"

    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 0, diagnostic
    assert diagnostic["checks"]["external_call_relations_ok"] is True
    assert diagnostic["checks"]["coverage_capture_summaries_match"] is True


def test_failed_or_usage_only_model_inference_needs_no_fabricated_output(
    tmp_path: Path,
) -> None:
    value = packet()
    inference = value["model_inferences"][0]
    inference["capture_status"] = "partial"
    inference["response"]["output_capture_status"] = "no_output"
    inference["response"]["output_state_ids"] = []
    inference["response"]["response_metadata_sha256"] = None
    value["coverage"]["model_inference_capture_status"] = "partial"

    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 0, diagnostic
    assert diagnostic["checks"]["model_inference_relations_ok"] is True
    assert diagnostic["checks"]["coverage_capture_summaries_match"] is True


# ---------------------------------------------------------------------------
# Strict parsing and schema fail-closed behavior
# ---------------------------------------------------------------------------


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    packet_path = tmp_path / "duplicate.json"
    packet_path.write_text(
        '{"schema_version": "pulsemech_compute_runtime_observation_packet_v0", '
        '"schema_version": "duplicate"}\n',
        encoding="utf-8",
    )

    result = run_tool(packet_path=packet_path)
    diagnostic = assert_cli_failure(
        result,
        "duplicate JSON key",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False


def test_non_finite_json_values_fail_closed(tmp_path: Path) -> None:
    packet_path = tmp_path / "non-finite.json"
    packet_path.write_text('{"value": NaN}\n', encoding="utf-8")

    result = run_tool(packet_path=packet_path)
    diagnostic = assert_cli_failure(
        result,
        "non-finite JSON value",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False


def test_schema_invalid_packet_fails_closed(tmp_path: Path) -> None:
    value = packet()
    value["packet_identity"]["packet_created_utc"] = (
        "2026-07-15T12:00:00+02:00"
    )

    diagnostic = assert_schema_failure(value, tmp_path)
    assert diagnostic["checks"] == {
        "semantic_checks_skipped_due_to_schema_errors": False
    }


def test_exact_github_action_requires_resolved_commit(tmp_path: Path) -> None:
    value = packet()
    source = value["executions"][0]["source_identity"]
    source.update(
        {
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
    )

    assert_schema_failure(value, tmp_path, "action_commit_sha")

    source["identity_status"] = "partial"
    diagnostic, exit_code = diagnostic_for(value, tmp_path)
    assert exit_code == 0, diagnostic
    assert diagnostic["checks"]["exact_github_action_identity_pinned"] is True


def test_measurement_target_kind_must_match_target_id_prefix(
    tmp_path: Path,
) -> None:
    value = packet()
    value["resource_measurements"][0]["target_kind"] = "execution"

    assert_schema_failure(value, tmp_path, "does not match")


def test_packet_predecessor_chain_is_schema_enforced(tmp_path: Path) -> None:
    value = packet()
    value["packet_identity"]["packet_sequence"] = 1
    value["packet_identity"]["previous_packet_sha256"] = None

    assert_schema_failure(value, tmp_path, "previous_packet_sha256")


def test_redaction_requires_rule_digest(tmp_path: Path) -> None:
    value = packet()
    value["privacy_boundary"]["redaction_applied"] = True
    value["privacy_boundary"]["redaction_rules_sha256"] = None

    assert_schema_failure(value, tmp_path, "redaction_rules_sha256")


def test_observed_packet_rejects_example_collector_mode(tmp_path: Path) -> None:
    value = packet()
    value["record_status"] = "observed"
    value["producer"]["collection_mode"] = "tool_wrapper"
    value["packet_identity"]["packet_scope"] = "subject_run"
    value["observation_boundary"]["collector_mode"] = "example"

    assert_schema_failure(value, tmp_path, "collector_mode")


def test_partial_token_usage_requires_at_least_one_token_value(
    tmp_path: Path,
) -> None:
    value = packet()
    usage = value["model_inferences"][0]["usage"]
    usage["usage_status"] = "partial"
    usage["input_tokens"] = None
    usage["output_tokens"] = None
    usage["total_tokens"] = None

    assert_schema_failure(value, tmp_path, "usage")


def test_privacy_flags_cannot_claim_raw_secret_surfaces(tmp_path: Path) -> None:
    value = packet()
    value["privacy_boundary"]["authorization_headers_included"] = True

    assert_schema_failure(value, tmp_path)


# ---------------------------------------------------------------------------
# Runtime identity, graph, state, and authority semantics
# ---------------------------------------------------------------------------


def test_duplicate_runtime_identifier_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["executions"].append(json.loads(json.dumps(value["executions"][0])))

    diagnostic = assert_semantic_failure(
        value,
        tmp_path,
        "record_identifiers_unique",
    )
    assert any(
        "execution_identifier_duplicate" in str(error)
        for error in diagnostic["errors"]
    )


def test_non_deterministic_record_order_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["executions"][0], value["executions"][1] = (
        value["executions"][1],
        value["executions"][0],
    )

    assert_semantic_failure(value, tmp_path, "deterministic_ordering_ok")


def test_subject_run_binding_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["state_observations"][0]["subject_run_key"] = "OTHER_RUN"

    assert_semantic_failure(
        value,
        tmp_path,
        "subject_run_binding_consistent",
    )


def test_collector_identity_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["producer"]["producer_execution_id"] = (
        "execution:check-gates-step"
    )

    assert_semantic_failure(value, tmp_path, "collector_boundary_ok")


def test_subject_execution_run_binding_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    subject_execution = next(
        row
        for row in value["executions"]
        if row["execution_scope"] == "subject"
    )
    subject_execution["run_binding"]["execution_run_key"] = "OTHER_RUN"

    assert_semantic_failure(
        value,
        tmp_path,
        "subject_execution_run_binding_ok",
    )


def test_authority_input_digest_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["authority_inputs"]["policy"]["sha256"] = "a" * 64

    assert_semantic_failure(value, tmp_path, "authority_input_bindings_ok")


def test_missing_execution_parent_is_rejected(tmp_path: Path) -> None:
    value = packet()
    execution(value, "execution:check-gates-step")["parent_execution_id"] = (
        "execution:missing"
    )

    assert_semantic_failure(
        value,
        tmp_path,
        "execution_parent_references_resolve",
    )


def test_execution_parent_cycle_is_rejected(tmp_path: Path) -> None:
    value = packet()
    collector = execution(value, "execution:runtime-observation-collector")
    collector["parent_execution_id"] = collector["execution_id"]

    assert_semantic_failure(value, tmp_path, "execution_graph_acyclic")


def test_workflow_job_step_shape_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    execution(value, "execution:check-gates-step")["job_id"] = 999999

    assert_semantic_failure(value, tmp_path, "workflow_job_step_shape_ok")


def test_dangling_execution_state_reference_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    target = execution(value, "execution:check-gates-step")
    target["input_state_ids"] = sorted(
        target["input_state_ids"] + ["state:missing"]
    )

    assert_semantic_failure(
        value,
        tmp_path,
        "execution_state_references_resolve",
    )


def test_state_observer_reference_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["state_observations"][0]["observer_execution_id"] = (
        "execution:check-gates-step"
    )

    assert_semantic_failure(
        value,
        tmp_path,
        "state_execution_references_resolve",
    )


def test_state_producer_relation_drift_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["state_observations"][0]["producer_execution_id"] = (
        "execution:check-gates-step"
    )

    assert_semantic_failure(value, tmp_path, "state_producer_relations_ok")


def test_mutation_authority_escalation_is_rejected(tmp_path: Path) -> None:
    value = packet()
    execution(value, "execution:check-gates-step")[
        "permitted_mutation_authority"
    ] = "final_status"

    assert_semantic_failure(
        value,
        tmp_path,
        "mutation_authority_relations_ok",
    )


# ---------------------------------------------------------------------------
# External call, model inference, measurement, and timing semantics
# ---------------------------------------------------------------------------


def test_external_call_parent_relation_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    execution(value, "execution:llamaguard-step")["external_call_ids"] = []

    assert_semantic_failure(value, tmp_path, "external_call_relations_ok")


def test_model_usage_total_mismatch_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["model_inferences"][0]["usage"]["total_tokens"] = 999

    assert_semantic_failure(value, tmp_path, "model_inference_relations_ok")


def test_resource_measurement_back_reference_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    execution(value, "execution:check-gates-step")[
        "resource_measurement_ids"
    ] = []

    assert_semantic_failure(
        value,
        tmp_path,
        "resource_measurement_relations_ok",
    )


def test_model_token_measurement_mismatch_is_rejected(tmp_path: Path) -> None:
    value = packet()
    measurement(value, "model_input_tokens")["value"] += 1

    assert_semantic_failure(
        value,
        tmp_path,
        "model_token_measurements_match_usage",
    )


def test_derived_duration_measurement_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    measurement(value, "step_wall_seconds")["value"] += 1.0

    assert_semantic_failure(
        value,
        tmp_path,
        "derived_duration_measurements_match_timing",
    )


def test_runtime_timing_inconsistency_is_rejected(tmp_path: Path) -> None:
    value = packet()
    execution(value, "execution:check-gates-step")["timing"][
        "completed_utc"
    ] = "2026-07-13T12:30:19Z"

    assert_semantic_failure(value, tmp_path, "runtime_timings_consistent")


def test_capture_window_or_packet_time_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = packet()
    value["packet_identity"]["packet_created_utc"] = (
        "2026-07-13T12:29:00Z"
    )

    assert_semantic_failure(
        value,
        tmp_path,
        "capture_window_and_packet_time_ok",
    )


# ---------------------------------------------------------------------------
# Coverage reconstruction
# ---------------------------------------------------------------------------


def test_coverage_record_count_mismatch_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["coverage"]["observed_job_count"] = 2

    assert_semantic_failure(value, tmp_path, "coverage_record_counts_match")


def test_missing_execution_id_must_not_reference_observed_execution(
    tmp_path: Path,
) -> None:
    value = packet()
    value["coverage"]["missing_execution_ids"] = [
        "execution:check-gates-step"
    ]

    assert_semantic_failure(
        value,
        tmp_path,
        "missing_execution_ids_are_unobserved",
    )


def test_resource_axis_partition_mismatch_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["coverage"]["resource_axes_unavailable"] = value["coverage"][
        "resource_axes_unavailable"
    ][1:]

    assert_semantic_failure(
        value,
        tmp_path,
        "resource_axis_coverage_partition_ok",
    )


def test_capture_summary_mismatch_is_rejected(tmp_path: Path) -> None:
    value = packet()
    value["coverage"]["model_inference_capture_status"] = "complete"

    assert_semantic_failure(
        value,
        tmp_path,
        "coverage_capture_summaries_match",
    )


def test_complete_coverage_recomputes_cross_field_count_and_gap_semantics(
    tmp_path: Path,
) -> None:
    value = packet()
    value["coverage"]["coverage_status"] = "complete"
    value["coverage"]["unobserved_reasons"] = []

    assert_semantic_failure(value, tmp_path, "coverage_status_semantics_ok")


# ---------------------------------------------------------------------------
# Read-only diagnostic output boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("output_name", ["status.json", "release_decision_v0.json"])
def test_authority_surface_output_names_are_rejected(
    tmp_path: Path,
    output_name: str,
) -> None:
    output = tmp_path / output_name
    result = run_tool(output=output)

    diagnostic = assert_cli_failure(
        result,
        "refusing_authority_surface_output",
        expected_returncode=2,
        stream="stderr",
    )
    assert result.stdout == ""
    assert diagnostic["schema_valid"] is False
    assert not output.exists()


@pytest.mark.parametrize(
    "protected_path",
    [SCHEMA, EXAMPLE, TOOL, GATE_POLICY, GATE_REGISTRY, PULSE_WORKFLOW],
    ids=lambda value: value.name,
)
def test_input_and_authority_source_overwrite_is_rejected(
    protected_path: Path,
) -> None:
    before = snapshot(protected_path)

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_to_overwrite_input",
    ):
        TOOL_MODULE.reject_unsafe_output(
            protected_path,
            schema_path=SCHEMA,
            packet_path=EXAMPLE,
        )

    assert snapshot(protected_path) == before


def test_existing_and_dangling_output_symlinks_are_rejected(
    tmp_path: Path,
) -> None:
    existing_target = tmp_path / "existing-target.json"
    existing_target.write_text("{}\n", encoding="utf-8")
    existing_link = tmp_path / "existing-link.json"

    try:
        existing_link.symlink_to(existing_target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            existing_link,
            schema_path=SCHEMA,
            packet_path=EXAMPLE,
        )
    assert existing_target.read_text(encoding="utf-8") == "{}\n"

    missing_target = tmp_path / "missing-target.json"
    dangling_link = tmp_path / "dangling-link.json"
    dangling_link.symlink_to(missing_target)

    assert dangling_link.is_symlink()
    assert not dangling_link.exists()
    assert not missing_target.exists()

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            dangling_link,
            schema_path=SCHEMA,
            packet_path=EXAMPLE,
        )

    assert dangling_link.is_symlink()
    assert not dangling_link.exists()
    assert not missing_target.exists()


def test_output_through_symlink_parent_is_rejected(tmp_path: Path) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked"

    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink unsupported: {exc}")

    output = linked_directory / "diagnostic.json"
    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            output,
            schema_path=SCHEMA,
            packet_path=EXAMPLE,
        )

    assert not (real_directory / "diagnostic.json").exists()


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_pulsemech_compute_runtime_observation_packet_validator_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_pulsemech_compute_runtime_observation_packet_validator_v0()
