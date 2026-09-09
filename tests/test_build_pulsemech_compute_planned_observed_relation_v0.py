#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_pulsemech_compute_planned_observed_relation_v0.py"
RELATION_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
RELATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)

SUBJECT = (
    "HKati/pulse-release-gates-0.1",
    "GITHUB_RUN_ID=1|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
    "a" * 40,
    "main",
)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILDER_MODULE = load_module(
    BUILDER,
    "build_pulsemech_compute_planned_observed_relation_v0_under_test",
)
VALIDATOR_MODULE = load_module(
    RELATION_VALIDATOR,
    "check_pulsemech_compute_planned_observed_relation_v0_for_builder_test",
)


def exact_repository_identity(path: str = "tools/example.py") -> dict[str, Any]:
    return {
        "action_commit_sha": None,
        "action_ref": None,
        "action_repository": None,
        "container_image_digest": None,
        "identity_status": "exact",
        "source_kind": "repository_file",
        "source_path_or_uri": path,
        "source_revision": SUBJECT[2],
        "source_sha256": "b" * 64,
    }


def unknown_identity() -> dict[str, Any]:
    return {
        "action_commit_sha": None,
        "action_ref": None,
        "action_repository": None,
        "container_image_digest": None,
        "identity_status": "unknown",
        "source_kind": "unknown",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
    }


def execution_identity(
    *,
    node_type: str = "workflow_step",
    workflow_name: str | None = "PULSE CI",
    job_name: str | None = "pulse",
    step_name: str | None = "Example step",
    tool_id: str | None = "tools/example.py",
    command_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "command_sha256": command_sha256,
        "job_name": job_name,
        "node_type": node_type,
        "step_name": step_name,
        "tool_id": tool_id,
        "workflow_name": workflow_name,
    }


def parent_execution(*, binding_complete: bool) -> dict[str, Any]:
    return {
        "declared_role": "evidence",
        "execution_scope": "subject",
        "job_name": "pulse",
        "permitted_mutation_authority": "release_evidence",
        "run_binding": {
            "binding_complete": binding_complete,
            "execution_run_key": SUBJECT[1],
            "subject_run_key": SUBJECT[1],
        },
        "step_name": "Parent step",
        "workflow_name": "PULSE CI",
    }


def empty_consumers() -> dict[str, tuple[list[str], list[str], list[str], bool]]:
    return {}


def minimal_plan() -> dict[str, Any]:
    operation = {
        "action": "preserve",
        "component_id": "component:one",
        "reason": "target file is byte-identical to the planned source",
        "source_path": "tools/one.py",
        "source_sha256": "c" * 64,
        "source_size_bytes": 10,
        "target_path": "tools/one.py",
        "target_state": "identical",
    }
    return {
        "apply_eligible": True,
        "authority_boundary": {
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "changes_release_authority": False,
            "creates_release_decision": False,
            "write_mode": "plan_only",
            "writes_target_repository": False,
        },
        "conflicts": [],
        "operations": [operation],
        "plan_type": "pulsemech_integration_plan",
        "request_id": "request-one",
        "schema_version": "pulsemech_integration_plan_v0",
        "selection": {
            "component_sets": ["set:one"],
            "declared_gate_sets": [],
            "resolved_components": ["component:one"],
        },
        "source": {
            "component_manifest_path": "integration/manifest.json",
            "component_manifest_sha256": "d" * 64,
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_sha256": "e" * 64,
            "repository": SUBJECT[0],
            "revision": SUBJECT[2],
        },
        "summary": {
            "conflict": 0,
            "create": 0,
            "files_total": 1,
            "preserve": 1,
            "source_missing": 0,
            "unresolved": 0,
        },
        "target": {
            "declared_ci_provider": "github_actions",
            "default_branch": "main",
            "detected_ci_providers": ["github_actions"],
            "repository_id": SUBJECT[0],
        },
        "tool": "plan_pulsemech_integration_v0",
        "unresolved": [],
    }


def minimal_artifact_report() -> dict[str, Any]:
    return {
        "analysis_boundary": {
            "analysis_level": "artifact_observed",
            "analysis_run_key": "EXAMPLE",
            "observer_in_subject_totals": False,
            "subject_run_key": SUBJECT[1],
        },
        "compute_nodes": [],
        "edges": [],
        "errors": [],
        "findings": [],
        "inputs": [],
        "ok": True,
        "record_status": "example",
        "report_type": "pulsemech_compute_binding_report",
        "resource_summary": {"axes": {}},
        "schema_version": "pulsemech_compute_binding_report_v0",
        "state_nodes": [],
        "subject": {
            "active_policy_sets": ["required"],
            "decision": "ALLOW",
            "final_status_sha256": "1" * 64,
            "materialized_gate_set_sha256": None,
            "policy_id": "policy:example",
            "policy_sha256": "e" * 64,
            "release_candidate_id": SUBJECT[3],
            "release_decision_sha256": "2" * 64,
            "repository": SUBJECT[0],
            "run_mode": "prod",
            "source_commit": SUBJECT[2],
            "workflow": "PULSE CI",
            "workflow_run_attempt": 1,
            "workflow_run_id": 1,
            "workflow_run_number": 1,
        },
        "summary": {
            "advisory_bound_nodes": 0,
            "authority_binding_complete": True,
            "decision_closure_complete": True,
            "evidence_bound_nodes": 0,
            "observer_nodes": 0,
            "preservation_bound_nodes": 0,
            "resource_measurement_status": "none",
            "subject_compute_nodes": 0,
            "transition_bound_nodes": 0,
            "unbound_authoritative_mutation_count": 0,
            "unbound_nodes": 0,
            "unknown_nodes": 0,
        },
        "tool": {
            "id": "build_pulsemech_compute_binding_report_v0",
            "source_sha256": "f" * 64,
            "version": "0.1.0",
        },
    }


def runtime_packet(
    *,
    sequence: int,
    predecessor: str | None,
    coverage_status: str = "complete",
    packet_id: str | None = None,
) -> dict[str, Any]:
    return {
        "coverage": {"coverage_status": coverage_status},
        "ok": True,
        "packet_identity": {
            "packet_id": packet_id or f"runtime-observation:packet-{sequence}",
            "packet_scope": "example",
            "packet_sequence": sequence,
            "previous_packet_sha256": predecessor,
        },
        "record_status": "example",
        "subject": {
            "release_candidate_id": SUBJECT[3],
            "repository": SUBJECT[0],
            "source_commit": SUBJECT[2],
            "subject_run_key": SUBJECT[1],
        },
    }


def presence_expectation_and_relation() -> tuple[dict[str, Any], dict[str, Any]]:
    expectation_id = "expectation:presence"
    relation_id = "relation:presence"
    expectations = {
        expectation_id: {
            "expected_compute": {"execution_required": False},
            "plan_operation_refs": [{"operation_sha256": "c" * 64}],
        }
    }
    relations = {
        relation_id: {
            "evaluation": {"decisive": True},
            "expectation_id": expectation_id,
            "observation_ids": [],
            "relation_status": "planned_presence_only",
        }
    }
    return expectations, relations


def complete_axes() -> dict[str, str]:
    return {
        "authority_coverage_status": "complete",
        "declared_role_coverage_status": "complete",
        "downstream_consumption_coverage_status": "complete",
        "execution_coverage_status": "complete",
        "identity_coverage_status": "complete",
    }


def test_builder_and_validator_files_exist() -> None:
    assert BUILDER.is_file()
    assert RELATION_VALIDATOR.is_file()
    assert RELATION_SCHEMA.is_file()


def test_explicit_unverifiable_tool_revision_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        BUILDER_MODULE,
        "git_revision_contains_current_tool",
        lambda _revision: None,
    )
    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="tool_source_revision_unverifiable",
    ):
        BUILDER_MODULE.resolve_tool_source_revision(
            "a" * 40,
            record_status="observed",
        )


def test_explicit_matching_tool_revision_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        BUILDER_MODULE,
        "git_revision_contains_current_tool",
        lambda _revision: True,
    )
    assert BUILDER_MODULE.resolve_tool_source_revision(
        "A" * 40,
        record_status="observed",
    ) == "a" * 40


@pytest.mark.parametrize(
    "source",
    [
        {
            **exact_repository_identity(),
            "source_sha256": None,
        },
        {
            "action_commit_sha": None,
            "action_ref": "v4",
            "action_repository": "actions/checkout",
            "container_image_digest": None,
            "identity_status": "exact",
            "source_kind": "github_action",
            "source_path_or_uri": None,
            "source_revision": None,
            "source_sha256": None,
        },
        {
            "action_commit_sha": None,
            "action_ref": None,
            "action_repository": None,
            "container_image_digest": None,
            "identity_status": "exact",
            "source_kind": "container_image",
            "source_path_or_uri": "ghcr.io/example/image",
            "source_revision": None,
            "source_sha256": None,
        },
    ],
    ids=("repository-file", "github-action", "container-image"),
)
def test_incomplete_exact_runtime_source_is_downgraded(
    source: dict[str, Any],
) -> None:
    normalized = BUILDER_MODULE.normalize_runtime_source_identity(source)
    assert normalized["identity_status"] == "partial"


def test_complete_exact_runtime_source_remains_exact() -> None:
    assert BUILDER_MODULE.normalize_runtime_source_identity(
        exact_repository_identity()
    )["identity_status"] == "exact"

    action = {
        "action_commit_sha": "a" * 40,
        "action_ref": "v4",
        "action_repository": "actions/checkout",
        "container_image_digest": None,
        "identity_status": "exact",
        "source_kind": "github_action",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
    }
    assert BUILDER_MODULE.normalize_runtime_source_identity(action)[
        "identity_status"
    ] == "exact"


def test_external_call_inherits_incomplete_parent_run_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        BUILDER_MODULE,
        "external_service_source_identity",
        lambda _service: exact_repository_identity("service://example"),
    )
    call = {
        "call_id": "call:example",
        "capture_status": "complete",
        "parent_execution_id": "execution:parent",
        "request": {"payload": {"state_ids": []}},
        "response": {"payload": {"state_ids": []}},
        "service_identity": {},
    }
    _identifier, observation = BUILDER_MODULE.external_call_observation(
        call,
        subject=SUBJECT,
        executions={
            "execution:parent": parent_execution(binding_complete=False)
        },
        states={},
        consumers=empty_consumers(),
    )
    assert observation["binding_status"] == "partial"
    assert observation["coverage_status"] == "partial"


def test_model_inference_inherits_incomplete_parent_run_binding() -> None:
    inference = {
        "capture_status": "complete",
        "inference_id": "inference:example",
        "model_identity": {
            "model_content_digest_status": "exact_digest",
            "model_id": "example/model",
            "model_revision": "revision-one",
            "model_sha256": "d" * 64,
        },
        "parent_execution_id": "execution:parent",
        "request": {"input_state_ids": []},
        "response": {"output_state_ids": []},
    }
    _identifier, observation = BUILDER_MODULE.model_inference_observation(
        inference,
        subject=SUBJECT,
        executions={
            "execution:parent": parent_execution(binding_complete=False)
        },
        states={},
        consumers=empty_consumers(),
    )
    assert observation["binding_status"] == "partial"
    assert observation["coverage_status"] == "partial"


def test_model_inference_can_be_complete_with_complete_parent_binding() -> None:
    inference = {
        "capture_status": "complete",
        "inference_id": "inference:example",
        "model_identity": {
            "model_content_digest_status": "exact_digest",
            "model_id": "example/model",
            "model_revision": "revision-one",
            "model_sha256": "d" * 64,
        },
        "parent_execution_id": "execution:parent",
        "request": {"input_state_ids": []},
        "response": {"output_state_ids": []},
    }
    _identifier, observation = BUILDER_MODULE.model_inference_observation(
        inference,
        subject=SUBJECT,
        executions={
            "execution:parent": parent_execution(binding_complete=True)
        },
        states={},
        consumers=empty_consumers(),
    )
    assert observation["binding_status"] == "complete"
    assert observation["coverage_status"] == "complete"


def test_workflow_only_selector_is_a_valid_anchor() -> None:
    selector = execution_identity(
        node_type=None,  # type: ignore[arg-type]
        workflow_name="PULSE CI",
        job_name=None,
        step_name=None,
        tool_id=None,
    )
    expectation = {
        "expected_compute": {"selector": selector},
        "expected_declared_role": None,
        "expected_mutation_authority": None,
        "expected_source_identity": unknown_identity(),
    }
    observation = {
        "declared_role": "unknown",
        "execution_identity": execution_identity(
            workflow_name="PULSE CI",
            job_name=None,
            step_name=None,
            tool_id=None,
        ),
        "execution_scope": "subject",
        "mutation_authority": "none",
        "source_identity": unknown_identity(),
    }
    assert BUILDER_MODULE.candidate_score(expectation, observation) == 25


def test_workflow_only_selector_shares_artifact_and_runtime_relation() -> None:
    selector = execution_identity(
        node_type=None,  # type: ignore[arg-type]
        workflow_name="PULSE CI",
        job_name=None,
        step_name=None,
        tool_id=None,
    )
    expectation = {
        "expected_compute": {"selector": selector},
        "expected_declared_role": None,
        "expected_mutation_authority": None,
        "expected_source_identity": unknown_identity(),
    }
    shared_observation = {
        "declared_role": "unknown",
        "execution_identity": execution_identity(
            workflow_name="PULSE CI",
            job_name=None,
            step_name=None,
            tool_id=None,
        ),
        "execution_scope": "subject",
        "mutation_authority": "none",
        "source_identity": unknown_identity(),
    }
    observations = {
        "observation:artifact": {
            **shared_observation,
            "source_record_kind": "compute_binding_report",
        },
        "observation:runtime": {
            **shared_observation,
            "source_record_kind": "runtime_observation_packet",
        },
    }

    selected, ambiguous = BUILDER_MODULE.select_candidate_observations(
        expectation,
        observations,
        set(observations),
    )

    assert selected == [
        "observation:artifact",
        "observation:runtime",
    ]
    assert ambiguous is False


def test_node_type_alone_is_not_treated_as_a_strong_anchor() -> None:
    selector = execution_identity(
        node_type="workflow_step",
        workflow_name=None,
        job_name=None,
        step_name=None,
        tool_id=None,
    )
    expectation = {
        "expected_compute": {"selector": selector},
        "expected_declared_role": None,
        "expected_mutation_authority": None,
        "expected_source_identity": unknown_identity(),
    }
    observation = {
        "declared_role": "unknown",
        "execution_identity": execution_identity(
            node_type="workflow_step",
            workflow_name=None,
            job_name=None,
            step_name=None,
            tool_id=None,
        ),
        "execution_scope": "subject",
        "mutation_authority": "none",
        "source_identity": unknown_identity(),
    }
    assert BUILDER_MODULE.candidate_score(expectation, observation) is None


def test_presence_only_axis_coverage_marks_execution_not_required() -> None:
    axes = BUILDER_MODULE.derive_axis_coverage(
        {},
        report={},
        packets=[],
        execution_required=False,
        runtime_status="none",
        analysis_level="artifact_observed",
    )
    assert axes == {
        "authority_coverage_status": "not_required",
        "declared_role_coverage_status": "not_required",
        "downstream_consumption_coverage_status": "not_required",
        "execution_coverage_status": "not_required",
        "identity_coverage_status": "not_required",
    }


def test_missing_required_execution_still_has_unknown_coverage() -> None:
    axes = BUILDER_MODULE.derive_axis_coverage(
        {},
        report={},
        packets=[],
        execution_required=True,
        runtime_status="none",
        analysis_level="artifact_observed",
    )
    assert axes["execution_coverage_status"] == "unknown"


def test_presence_only_coverage_can_complete() -> None:
    expectations, relations = presence_expectation_and_relation()
    axes = {
        "authority_coverage_status": "not_required",
        "declared_role_coverage_status": "not_required",
        "downstream_consumption_coverage_status": "not_required",
        "execution_coverage_status": "not_required",
        "identity_coverage_status": "not_required",
    }
    coverage = BUILDER_MODULE.build_coverage(
        plan_binding={"operation_count": 1},
        expectations=expectations,
        observations={},
        relations=relations,
        axes=axes,
        runtime_status="none",
        analysis_level="artifact_observed",
    )
    assert coverage["comparison_status"] == "complete"
    assert coverage["unresolved_reasons"] == []


def test_partial_runtime_chain_blocks_complete_comparison() -> None:
    expectations, relations = presence_expectation_and_relation()
    observation_id = "observation:runtime"
    observations = {observation_id: {}}
    relations["relation:presence"]["observation_ids"] = [observation_id]

    coverage = BUILDER_MODULE.build_coverage(
        plan_binding={"operation_count": 1},
        expectations=expectations,
        observations=observations,
        relations=relations,
        axes=complete_axes(),
        runtime_status="partial",
        analysis_level="runtime_observed",
    )
    assert coverage["comparison_status"] == "partial"
    assert "runtime_coverage_partial" in coverage["unresolved_reasons"]


def test_complete_runtime_chain_can_complete_comparison() -> None:
    expectations, relations = presence_expectation_and_relation()
    observation_id = "observation:runtime"
    observations = {observation_id: {}}
    relations["relation:presence"]["observation_ids"] = [observation_id]

    coverage = BUILDER_MODULE.build_coverage(
        plan_binding={"operation_count": 1},
        expectations=expectations,
        observations=observations,
        relations=relations,
        axes=complete_axes(),
        runtime_status="complete",
        analysis_level="runtime_observed",
    )
    assert coverage["comparison_status"] == "complete"
    assert coverage["unresolved_reasons"] == []


def test_runtime_chain_without_sequence_zero_is_partial() -> None:
    packet = runtime_packet(
        sequence=1,
        predecessor="f" * 64,
    )
    raw = BUILDER_MODULE.render_json(packet).encode("utf-8")
    ordered, chain_complete = BUILDER_MODULE.verify_runtime_packet_chain(
        [(packet, raw, "example://packet-1")],
        subject=SUBJECT,
        record_status="example",
    )
    assert len(ordered) == 1
    assert chain_complete is False
    assert BUILDER_MODULE.runtime_observation_status(
        ordered,
        chain_complete=chain_complete,
    ) == "partial"


def test_contiguous_runtime_chain_with_predecessor_digest_is_complete() -> None:
    first = runtime_packet(sequence=0, predecessor=None)
    first_raw = BUILDER_MODULE.render_json(first).encode("utf-8")
    second = runtime_packet(
        sequence=1,
        predecessor=BUILDER_MODULE.sha256_bytes(first_raw),
    )
    second_raw = BUILDER_MODULE.render_json(second).encode("utf-8")
    ordered, chain_complete = BUILDER_MODULE.verify_runtime_packet_chain(
        [
            (second, second_raw, "example://packet-1"),
            (first, first_raw, "example://packet-0"),
        ],
        subject=SUBJECT,
        record_status="example",
    )
    assert [
        item[0]["packet_identity"]["packet_sequence"] for item in ordered
    ] == [0, 1]
    assert chain_complete is True
    assert BUILDER_MODULE.runtime_observation_status(
        ordered,
        chain_complete=chain_complete,
    ) == "complete"


def test_duplicate_runtime_packet_sequence_is_rejected() -> None:
    first = runtime_packet(sequence=0, predecessor=None, packet_id="runtime-observation:a")
    second = runtime_packet(sequence=0, predecessor=None, packet_id="runtime-observation:b")
    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="runtime_packet_sequence_duplicate",
    ):
        BUILDER_MODULE.verify_runtime_packet_chain(
            [
                (first, b"first", "example://first"),
                (second, b"second", "example://second"),
            ],
            subject=SUBJECT,
            record_status="example",
        )


def test_source_mismatch_dominates_parallel_match() -> None:
    expected = exact_repository_identity()
    matching = {"source_identity": exact_repository_identity()}
    conflicting_identity = exact_repository_identity()
    conflicting_identity["source_sha256"] = "c" * 64
    conflicting = {"source_identity": conflicting_identity}

    assert BUILDER_MODULE.source_identity_result(
        expected,
        [matching, conflicting],
    ) == "mismatch"


def test_execution_mismatch_dominates_parallel_match() -> None:
    selector = execution_identity()
    matching = {"execution_identity": execution_identity()}
    conflicting = {
        "execution_identity": execution_identity(node_type="workflow_job")
    }
    assert BUILDER_MODULE.selector_result(
        selector,
        [matching, conflicting],
    ) == "mismatch"


def test_presence_only_end_to_end_record_is_schema_and_semantically_valid(
    tmp_path: Path,
) -> None:
    plan = minimal_plan()
    report = minimal_artifact_report()
    plan_bytes = BUILDER_MODULE.render_json(plan).encode("utf-8")
    report_bytes = BUILDER_MODULE.render_json(report).encode("utf-8")

    relation = BUILDER_MODULE.build_relation_record(
        plan=plan,
        plan_bytes=plan_bytes,
        plan_path_or_uri="example://plan",
        report=report,
        report_bytes=report_bytes,
        report_path_or_uri="example://report",
        packets=[],
        explicit_expectations={},
        relation_id=None,
        tool_source_revision=None,
    )

    assert relation["summary"]["comparison_complete"] is True
    assert relation["coverage"]["comparison_status"] == "complete"
    assert relation["coverage"]["execution_coverage_status"] == "not_required"
    assert {
        record["relation_status"] for record in relation["relations"].values()
    } == {"planned_presence_only"}

    schema = json.loads(RELATION_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = list(
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(relation)
    )
    assert errors == []

    relation_path = tmp_path / "relation.json"
    relation_path.write_text(
        BUILDER_MODULE.render_json(relation),
        encoding="utf-8",
    )
    diagnostic, exit_code = VALIDATOR_MODULE.build_diagnostic(
        schema_path=RELATION_SCHEMA,
        relation_path=relation_path,
    )
    assert exit_code == 0
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []


def test_relation_construction_is_deterministic() -> None:
    plan = minimal_plan()
    report = minimal_artifact_report()
    kwargs = {
        "plan": plan,
        "plan_bytes": BUILDER_MODULE.render_json(plan).encode("utf-8"),
        "plan_path_or_uri": "example://plan",
        "report": report,
        "report_bytes": BUILDER_MODULE.render_json(report).encode("utf-8"),
        "report_path_or_uri": "example://report",
        "packets": [],
        "explicit_expectations": {},
        "relation_id": None,
        "tool_source_revision": None,
    }
    first = BUILDER_MODULE.build_relation_record(**kwargs)
    second = BUILDER_MODULE.build_relation_record(**kwargs)
    assert BUILDER_MODULE.render_json(first) == BUILDER_MODULE.render_json(second)


def test_read_only_output_boundary_rejects_subject_root_and_authority_names(
    tmp_path: Path,
) -> None:
    subject_root = tmp_path / "subject"
    subject_root.mkdir()
    protected = tmp_path / "input.json"
    protected.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_output_inside_subject_root",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            subject_root / "relation.json",
            protected_paths=[protected],
            subject_root=subject_root,
        )

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_authority_surface_output",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            tmp_path / "status.json",
            protected_paths=[protected],
            subject_root=subject_root,
        )


def test_existing_or_dangling_output_symlink_is_rejected(tmp_path: Path) -> None:
    subject_root = tmp_path / "subject"
    subject_root.mkdir()
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_symlink_output_path",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            link,
            protected_paths=[],
            subject_root=subject_root,
        )

    dangling = tmp_path / "dangling.json"
    dangling.symlink_to(tmp_path / "missing.json")
    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_symlink_output_path",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            dangling,
            protected_paths=[],
            subject_root=subject_root,
        )


def check_build_pulsemech_compute_planned_observed_relation_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))



# Shared full-schema runtime examples live in an already registered regression.
def _runtime_test_support():
    import importlib.util
    import hashlib
    import sys
    path = Path(__file__).with_name("test_pulsemech_compute_binding_analyzer_core_v0.py")
    name = "pulse_runtime_regression_support_" + hashlib.sha256(path.read_bytes()).hexdigest()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def test_runtime_comparison_does_not_count_projected_graph_twice():
    m=_runtime_test_support();c=m.runtime_test_synthetic_case();r,_=m.runtime_test_relation(c)
    assert len(r["observations"])==3
    assert len({o["source_record_id"] for o in r["observations"].values()})==3
    assert all(o.get("runtime_occurrence_guard")=="no_artifact_occurrence_binding" for o in r["observations"].values())


def test_runtime_comparison_resource_gap_is_separate_from_relational_completeness():
    m=_runtime_test_support();c=m.runtime_test_synthetic_case();r,_=m.runtime_test_relation(c,extent=True)
    assert r["coverage"]["runtime_observation_status"]=="partial"
    assert r["runtime_comparison"]["relational_coverage_status"]=="complete"
    assert r["summary"]["comparison_complete"] is True
    c["requirements"]["execution:synthetic-consumer"]["input_state_ids"]=[]
    bad,_=m.runtime_test_relation(c,extent=True)
    assert bad["summary"]["comparison_complete"] is False


def test_runtime_collector_is_accounted_for_without_becoming_subject_execution():
    m=_runtime_test_support();r,_=m.runtime_test_relation(m.runtime_test_synthetic_case(),extent=True)
    col=next(o for o in r["observations"].values() if o["execution_scope"]=="observation_collector")
    assert col["binding_class"]=="observer"
    assert col["subject_run_key"]=="SYNTHETIC_COLLECTOR=separate"
    assert r["coverage"]["unclassified_observation_ids"]==[]


def test_runtime_same_input_relation_bytes_are_deterministic():
    m=_runtime_test_support();c=m.runtime_test_synthetic_case()
    a,_=m.runtime_test_relation(c,extent=True);b,_=m.runtime_test_relation(c,extent=True)
    assert m.runtime_test_bytes(a)==m.runtime_test_bytes(b)



def test_runtime_source_revision_ignores_caller_path_git(tmp_path,monkeypatch):
    m=_runtime_test_support();builder=m.runtime_test_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    expected=builder.resolve_runtime_tool_source_revision(None,record_status="example")
    fake=tmp_path/"git";fake.write_text("#!/bin/sh\necho ffffffffffffffffffffffffffffffffffffffff\n");fake.chmod(0o755)
    monkeypatch.setenv("PATH",str(tmp_path))
    assert builder.resolve_runtime_tool_source_revision(None,record_status="example")==expected
    assert expected!="f"*40


def test_runtime_relation_cli_wiring_with_synthetic_captured_upstream(monkeypatch,capsys,tmp_path):
    # Only upstream acquisition is supplied by this synthetic fixture. Actual
    # report construction/replay, relation construction and independent relation
    # replay execute unchanged. This is not an observed historical CLI replay.
    import argparse
    m=_runtime_test_support();case=m.runtime_test_synthetic_case();relation,replay=m.runtime_test_relation(case,extent=True)
    builder=m.runtime_test_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    checker=m.runtime_test_module("check_pulsemech_compute_binding_report_v0.py")
    bridge=m.runtime_test_module("build_pulsemech_compute_binding_report_from_subject_input_v0.py")
    monkeypatch.setattr(builder,"_load_runtime_report_checker",lambda:checker)
    monkeypatch.setattr(checker,"runtime_inputs_from_paths",lambda **kwargs:{"bridge":bridge})
    monkeypatch.setattr(checker,"resolve_runtime_replay_inputs",lambda *args:replay["report_inputs"])
    args=argparse.Namespace(subject_input=str(tmp_path/"subject.json"),carrier=str(tmp_path/"carrier.zip"),runtime_packet=[str(tmp_path/"packet.json")],
        repository_root=str(m.ROOT),runtime_extent=None,report_validator=str(builder.DEFAULT_REPORT_VALIDATOR),
        relation_validator=str(builder.DEFAULT_RELATION_VALIDATOR),expectations=None,tool_source_revision=relation["tool"]["source_revision"],
        relation_id=relation["comparison_identity"]["relation_record_id"],output=None)
    rc=builder.runtime_profile_cli(args,report_bytes=replay["report_bytes"],plan_bytes=replay["plan_bytes"])
    assert rc==0
    result=json.loads(capsys.readouterr().out)
    assert result==relation


@pytest.mark.parametrize("outcome", ["skipped", "cancelled", "unknown"])
def test_review_2872_nonexecuted_observer_cannot_complete_comparison(outcome, tmp_path):
    m = _runtime_test_support()
    case = m.runtime_test_synthetic_case()
    packet = case["packets"][0]
    collector = next(row for row in packet["executions"]
                     if row["execution_scope"] == "observation_collector")
    observer = collector
    observer["result"].update(outcome=outcome, exit_code=None)
    # These result values are accepted by the unchanged packet contract.
    validator = m.runtime_test_module("check_pulsemech_compute_runtime_observation_packet_v0.py")
    diagnostic, rc = validator.build_diagnostic(
        schema_path=m.ROOT / "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
        packet_path=m.runtime_test_view(m.runtime_test_bytes(packet)),
    )
    assert rc == 0, diagnostic
    relation, inputs = m.runtime_test_relation(case, extent=True)
    observation_id, observation = next((key, row) for key, row in relation["observations"].items()
        if row["source_record_id"] == observer["execution_id"])
    assert observation["binding_class"] == "observer"
    assert observation["coverage_status"] != "complete"
    classified = next(row for row in relation["relations"].values()
                      if observation_id in row["observation_ids"])
    assert classified["relation_status"] == "unresolved_due_to_coverage"
    assert classified["evaluation"]["decisive"] is False
    assert relation["summary"]["comparison_complete"] is False
    checker = m.runtime_test_module("check_pulsemech_compute_planned_observed_relation_v0.py")
    schema = m.ROOT / "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json"
    diagnostic, rc = checker.build_diagnostic(schema_path=schema,
        relation_path=m.runtime_test_view(m.runtime_test_bytes(relation)), runtime_inputs=inputs)
    assert rc == 0, diagnostic  # Valid partial evidence is not a validator error.
    status_path = tmp_path / "base.json"
    status_path.write_bytes(m.runtime_test_bytes({"gates": {"existing": True}}))
    relation_path = tmp_path / "runtime-relation.json"
    relation_path.write_bytes(m.runtime_test_bytes(relation))
    materializer = m.runtime_test_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    result, rc = materializer.build_and_write_folded_status(
        status_path=status_path, relation_path=relation_path, schema_path=schema,
        validator_path=m.ROOT / "tools/check_pulsemech_compute_planned_observed_relation_v0.py",
        output_path=tmp_path / "runtime-candidate.json", runtime_inputs=inputs,
    )
    assert rc == 0 and result["candidate_all_true"] is False, result


@pytest.mark.parametrize("field,value", [
    ("command_sha256", None), ("arguments_sha256", None),
    ("command_kind", "unknown"),
])
def test_review_2872_observer_command_evidence_cannot_be_skipped(field, value):
    m = _runtime_test_support()
    case = m.runtime_test_synthetic_case()
    collector = next(row for row in case["packets"][0]["executions"]
                     if row["execution_scope"] == "observation_collector")
    collector["command_identity"][field] = value
    relation, _ = m.runtime_test_relation(case, extent=True)
    assert relation["summary"]["comparison_complete"] is False


def test_review_2872_observed_repository_claim_does_not_become_exact():
    # Adversarial observed-labelled inputs to the pure projection only. This is
    # NOT a historical observation or a source-aware subject-input proof.
    m = _runtime_test_support()
    case = m.runtime_test_synthetic_case()
    case["baseline"]["record_status"] = "observed"
    case["subject_input"]["record_status"] = "observed"
    case["packets"][0]["record_status"] = "observed"
    report, inputs = m.runtime_test_report(case)
    builder = m.runtime_test_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    observations = builder.normalize_runtime_bound_observations(
        report, [(json.loads(raw), raw, locator) for locator, raw in inputs["packet_sources"]],
        subject=builder.subject_tuple_from_report(report),
    )
    raw_records = {row["execution_id"]: row for row in case["packets"][0]["executions"]}
    for observation in observations.values():
        claimed = raw_records[observation["source_record_id"]]["source_identity"]
        assert claimed["identity_status"] == "exact"
        assert observation["source_identity"]["identity_status"] == "partial"
        assert observation["source_identity"]["source_sha256"] == claimed["source_sha256"]
        assert observation["binding_status"] != "complete"
        assert builder.source_identity_result(claimed, [observation]) == "unavailable"
    assert not any(edge["observed"] for edge in report["edges"])


def test_review_2872_runtime_constructor_uses_captured_content_locators():
    m = _runtime_test_support()
    relation, inputs = m.runtime_test_relation(m.runtime_test_synthetic_case(), extent=True)
    builder = m.runtime_test_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    rebuilt = builder.build_relation_record(
        plan=json.loads(inputs["plan_bytes"]), plan_bytes=inputs["plan_bytes"],
        plan_path_or_uri="misleading://other-plan", report=json.loads(inputs["report_bytes"]),
        report_bytes=inputs["report_bytes"], report_path_or_uri="sha256:" + "0" * 64,
        packets=[(json.loads(raw), raw, loc) for loc, raw in inputs["report_inputs"]["packet_sources"]],
        explicit_expectations={}, relation_id=relation["comparison_identity"]["relation_record_id"],
        tool_source_revision=relation["tool"]["source_revision"], expectations_bytes=None,
    )
    assert rebuilt == relation




def _bounded_unit_module(filename):
    import importlib.util, sys, hashlib
    path=Path(__file__).resolve().parents[1]/"tools"/filename
    name="_bounded_unit_"+hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def test_bounded_occurrence_selector_is_a_hard_match_boundary():
    builder=_bounded_unit_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    expectation={"expected_compute":{"selector":{"bounded_execution_id":"execution:allow:checker"}},"expected_source_identity":{}}
    observation={"execution_identity":{"bounded_execution_id":"execution:block_false:checker"},"source_identity":{}}
    assert builder.candidate_score(expectation,observation) is None
    observation["execution_identity"]["bounded_execution_id"]="execution:allow:checker"
    assert builder.candidate_score(expectation,observation)>0

def test_bounded_relation_build_requires_captured_sources_not_a_flag():
    import pytest
    builder=_bounded_unit_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    with pytest.raises(builder.BuilderError,match="raw_sources_required"):
        builder._prepare_bounded_relation(report={},report_bytes=b"{}",plan={},plan_bytes=b"{}",packets=[],explicit={},
            expectations_bytes=None,tool_source_revision=None,inputs=None)


if __name__ == "__main__":
    check_build_pulsemech_compute_planned_observed_relation_v0()
