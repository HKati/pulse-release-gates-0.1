#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "check_pulsemech_compute_runtime_observation_packet_v0"
SCHEMA_VERSION = "pulsemech_compute_runtime_observation_packet_v0"
PACKET_TYPE = "pulsemech_compute_runtime_observation_packet"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
DEFAULT_PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_runtime_observation_packet_example_v0.json"
)
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

RESOURCE_AXES = {
    "runner_wall_seconds",
    "job_wall_seconds",
    "step_wall_seconds",
    "cpu_seconds",
    "gpu_seconds",
    "memory_gb_seconds",
    "network_bytes_sent",
    "network_bytes_received",
    "storage_bytes_written",
    "artifact_bytes_uploaded",
    "external_api_calls",
    "model_input_tokens",
    "model_output_tokens",
    "retry_count",
    "rerun_count",
}

AXIS_UNITS = {
    "runner_wall_seconds": "seconds",
    "job_wall_seconds": "seconds",
    "step_wall_seconds": "seconds",
    "cpu_seconds": "seconds",
    "gpu_seconds": "seconds",
    "memory_gb_seconds": "gb_seconds",
    "network_bytes_sent": "bytes",
    "network_bytes_received": "bytes",
    "storage_bytes_written": "bytes",
    "artifact_bytes_uploaded": "bytes",
    "external_api_calls": "count",
    "model_input_tokens": "tokens",
    "model_output_tokens": "tokens",
    "retry_count": "count",
    "rerun_count": "count",
}

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

AUTHORITY_MUTATION_RANK = {
    "release_evidence": 10,
    "candidate_state": 20,
    "verifier_state": 30,
    "materialized_gate_set": 40,
    "final_status": 50,
    "release_decision": 60,
}

class StrictJsonError(ValueError):
    pass


class SemanticError(RuntimeError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )


def render_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def schema_errors(schema: dict[str, Any], value: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(
            validator.iter_errors(value),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    ]


def parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError(f"not canonical UTC: {value}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None:
        raise ValueError(f"timezone missing: {value}")
    return parsed.astimezone(timezone.utc)


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        pass

    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass

    return False


def reject_unsafe_output(
    output: Path | None,
    *,
    schema_path: Path,
    packet_path: Path,
) -> None:
    if output is None:
        return

    protected = (
        schema_path,
        packet_path,
        Path(__file__),
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    )
    for path in protected:
        if same_target(output, path):
            raise SemanticError(f"refusing_to_overwrite_input: {path}")

    if output.name in {"status.json", "release_decision_v0.json"}:
        raise SemanticError(
            f"refusing_authority_surface_output: {output.name}"
        )

    cursor = output
    while True:
        if cursor.is_symlink():
            raise SemanticError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def make_diagnostic(
    *,
    ok: bool,
    schema_valid: bool,
    checks: dict[str, bool],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "ok": ok,
        "schema_valid": schema_valid,
        "checks": dict(sorted(checks.items())),
        "errors": sorted(set(errors)),
    }


def _index(
    rows: list[dict[str, Any]],
    key: str,
    *,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        identifier = row.get(key)
        if not isinstance(identifier, str):
            errors.append(f"{label}_identifier_invalid: {identifier!r}")
            continue
        if identifier in result:
            errors.append(f"{label}_identifier_duplicate: {identifier}")
            continue
        result[identifier] = row
    return result


def _sorted_unique_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(item, str) for item in values)
        and values == sorted(values)
        and len(values) == len(set(values))
    )


def _all_reference_lists_sorted(packet: dict[str, Any]) -> bool:
    top_lists = [
        packet.get("subject", {}).get("active_policy_sets"),
        packet.get("coverage", {}).get("missing_execution_ids"),
        packet.get("coverage", {}).get("unobserved_reasons"),
        packet.get("coverage", {}).get("resource_axes_observed"),
        packet.get("coverage", {}).get("resource_axes_unavailable"),
        packet.get("errors"),
    ]

    for execution in packet.get("executions", []):
        top_lists.extend(
            [
                execution.get("input_state_ids"),
                execution.get("output_state_ids"),
                execution.get("external_call_ids"),
                execution.get("model_inference_ids"),
                execution.get("resource_measurement_ids"),
            ]
        )

    for call in packet.get("external_calls", []):
        top_lists.extend(
            [
                call.get("request", {}).get("payload", {}).get("state_ids"),
                call.get("response", {}).get("payload", {}).get("state_ids"),
                call.get("resource_measurement_ids"),
            ]
        )

    for inference in packet.get("model_inferences", []):
        top_lists.extend(
            [
                inference.get("request", {}).get("input_state_ids"),
                inference.get("response", {}).get("output_state_ids"),
                inference.get("resource_measurement_ids"),
            ]
        )

    for measurement in packet.get("resource_measurements", []):
        top_lists.append(measurement.get("evidence_state_ids"))

    return all(_sorted_unique_strings(values) for values in top_lists)


def _rows_sorted(rows: list[dict[str, Any]], key: str) -> bool:
    identifiers = [row.get(key) for row in rows]
    return (
        all(isinstance(identifier, str) for identifier in identifiers)
        and identifiers == sorted(identifiers)
    )


def _timing_valid(
    timing: dict[str, Any],
    *,
    timestamp_resolution_ms: float,
) -> bool:
    status = timing.get("timing_status")
    started = timing.get("started_utc")
    completed = timing.get("completed_utc")
    duration_ms = timing.get("duration_ms")

    if status == "unknown":
        return (
            started is None
            and completed is None
            and duration_ms is None
            and timing.get("timestamp_source") == "unknown"
            and timing.get("duration_source") == "unknown"
        )

    if started is not None and completed is not None:
        try:
            start_dt = parse_utc(started)
            complete_dt = parse_utc(completed)
        except Exception:
            return False
        if complete_dt < start_dt:
            return False

        if duration_ms is not None and timing.get("duration_source") == (
            "derived_from_timestamps"
        ):
            observed = (complete_dt - start_dt).total_seconds() * 1000.0
            tolerance = max(float(timestamp_resolution_ms), 0.001)
            if not math.isclose(
                float(duration_ms),
                observed,
                rel_tol=0.0,
                abs_tol=tolerance,
            ):
                return False

    if status == "complete":
        return (
            isinstance(started, str)
            and isinstance(completed, str)
            and isinstance(duration_ms, (int, float))
            and not isinstance(duration_ms, bool)
            and float(duration_ms) >= 0
        )

    if status == "partial":
        return any(value is not None for value in (started, completed, duration_ms))

    return False


def _time_window_valid(
    started: str | None,
    completed: str | None,
) -> bool:
    if started is None and completed is None:
        return True
    if not isinstance(started, str) or not isinstance(completed, str):
        return False
    try:
        return parse_utc(completed) >= parse_utc(started)
    except Exception:
        return False


def _within_capture(
    value: str | None,
    *,
    capture_started: datetime,
    capture_completed: datetime,
) -> bool:
    if value is None:
        return True
    try:
        point = parse_utc(value)
    except Exception:
        return False
    return capture_started <= point <= capture_completed


def _execution_graph_acyclic(
    executions: dict[str, dict[str, Any]],
) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> bool:
        if identifier in visited:
            return True
        if identifier in visiting:
            return False
        visiting.add(identifier)
        parent = executions[identifier].get("parent_execution_id")
        if isinstance(parent, str) and parent in executions:
            if not visit(parent):
                return False
        visiting.remove(identifier)
        visited.add(identifier)
        return True

    return all(visit(identifier) for identifier in executions)


def _derived_capture_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "none"
    statuses = [row.get("capture_status") for row in rows]
    if all(status == "complete" for status in statuses):
        return "complete"
    if all(status == "unknown" for status in statuses):
        return "unknown"
    return "partial"


def _derived_state_digest_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "none"
    statuses = [row.get("content_status") for row in rows]
    if all(status == "exact_digest" for status in statuses):
        return "complete"
    if all(status == "unavailable" for status in statuses):
        return "unknown"
    return "partial"


def _unit_and_value_ok(measurement: dict[str, Any]) -> bool:
    axis = measurement.get("axis")
    unit = measurement.get("unit")
    value = measurement.get("value")
    if axis not in AXIS_UNITS or unit != AXIS_UNITS[axis]:
        return False
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if value < 0:
        return False
    if unit in {"bytes", "count", "tokens"} and not isinstance(value, int):
        return False
    return True


def _payload_semantics_ok(payload: dict[str, Any]) -> bool:
    status = payload.get("capture_status")
    metadata = payload.get("metadata_sha256")
    body = payload.get("body_sha256")
    size = payload.get("body_size_bytes")
    states = payload.get("state_ids")

    if status == "exact_digest":
        return (
            isinstance(body, str)
            and isinstance(size, int)
            and size >= 0
            and isinstance(states, list)
        )
    if status == "metadata_only":
        return (
            isinstance(metadata, str)
            and body is None
            and size is None
            and isinstance(states, list)
        )
    if status == "not_recorded":
        return metadata is None and body is None and size is None and states == []
    return False


def _model_usage_ok(usage: dict[str, Any]) -> bool:
    status = usage.get("usage_status")
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")

    values = (input_tokens, output_tokens, total_tokens)
    for value in values:
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            return False

    if status == "unavailable":
        return all(value is None for value in values)
    if status == "partial":
        if all(value is None for value in values):
            return False
    elif status == "complete":
        if any(value is None for value in values):
            return False
    else:
        return False

    if (
        input_tokens is not None
        and output_tokens is not None
        and total_tokens is not None
        and total_tokens != input_tokens + output_tokens
    ):
        return False
    return True


def semantic_checks(packet: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def record(name: str, condition: bool, detail: str | None = None) -> None:
        checks[name] = bool(condition)
        if not condition:
            suffix = f": {detail}" if detail else ""
            errors.append(f"check_failed: {name}{suffix}")

    executions_list = packet.get("executions", [])
    states_list = packet.get("state_observations", [])
    calls_list = packet.get("external_calls", [])
    inferences_list = packet.get("model_inferences", [])
    measurements_list = packet.get("resource_measurements", [])

    if not all(
        isinstance(value, list)
        for value in (
            executions_list,
            states_list,
            calls_list,
            inferences_list,
            measurements_list,
        )
    ):
        return checks, ["semantic_input_arrays_invalid"]

    executions = _index(
        executions_list,
        "execution_id",
        label="execution",
        errors=errors,
    )
    states = _index(
        states_list,
        "state_id",
        label="state",
        errors=errors,
    )
    calls = _index(
        calls_list,
        "call_id",
        label="external_call",
        errors=errors,
    )
    inferences = _index(
        inferences_list,
        "inference_id",
        label="model_inference",
        errors=errors,
    )
    measurements = _index(
        measurements_list,
        "measurement_id",
        label="resource_measurement",
        errors=errors,
    )

    record(
        "schema_version_ok",
        packet.get("schema_version") == SCHEMA_VERSION,
    )
    record(
        "packet_type_ok",
        packet.get("packet_type") == PACKET_TYPE,
    )

    unique_ok = (
        len(executions) == len(executions_list)
        and len(states) == len(states_list)
        and len(calls) == len(calls_list)
        and len(inferences) == len(inferences_list)
        and len(measurements) == len(measurements_list)
    )
    record("record_identifiers_unique", unique_ok)

    order_ok = (
        _rows_sorted(executions_list, "execution_id")
        and _rows_sorted(states_list, "state_id")
        and _rows_sorted(calls_list, "call_id")
        and _rows_sorted(inferences_list, "inference_id")
        and _rows_sorted(measurements_list, "measurement_id")
        and _all_reference_lists_sorted(packet)
    )
    record("deterministic_ordering_ok", order_ok)

    subject = packet.get("subject", {})
    packet_identity = packet.get("packet_identity", {})
    observation = packet.get("observation_boundary", {})
    producer = packet.get("producer", {})
    coverage = packet.get("coverage", {})
    timing_basis = packet.get("timing_basis", {})
    privacy = packet.get("privacy_boundary", {})
    authority_inputs = packet.get("authority_inputs", {})

    subject_run_key = subject.get("subject_run_key")
    collector_run_key = observation.get("collector_run_key")
    collector_id = observation.get("collector_execution_id")

    run_key_ok = (
        isinstance(subject_run_key, str)
        and packet_identity.get("subject_run_key") == subject_run_key
        and observation.get("subject_run_key") == subject_run_key
        and all(
            row.get("subject_run_key") == subject_run_key
            for row in states_list + calls_list + inferences_list + measurements_list
        )
        and all(
            execution.get("run_binding", {}).get("subject_run_key")
            == subject_run_key
            for execution in executions_list
        )
    )
    record("subject_run_binding_consistent", run_key_ok)

    collector = executions.get(collector_id) if isinstance(collector_id, str) else None
    collector_binding = (
        collector.get("run_binding", {})
        if isinstance(collector, dict)
        else {}
    )
    collector_mode = collector_binding.get("binding_mode")
    collector_execution_key = collector_binding.get("execution_run_key")
    collector_run_relation_ok = (
        (
            collector_mode == "current_subject_run"
            and collector_run_key == subject_run_key
            and collector_execution_key == subject_run_key
        )
        or (
            collector_mode in {"post_run_observer", "external_export"}
            and collector_execution_key == collector_run_key
        )
    )
    collector_source = (
        collector.get("source_identity", {})
        if isinstance(collector, dict)
        else {}
    )
    collector_ok = (
        isinstance(collector, dict)
        and producer.get("producer_execution_id") == collector_id
        and collector.get("execution_scope") == "observation_collector"
        and collector.get("execution_kind") == "observer_execution"
        and collector.get("declared_role") == "observer"
        and collector.get("permitted_mutation_authority") == "advisory_output"
        and collector_binding.get("subject_run_key") == subject_run_key
        and collector_run_relation_ok
        and producer.get("producer_source")
        == collector_source.get("source_path_or_uri")
        and producer.get("producer_source_sha256")
        == collector_source.get("source_sha256")
        and observation.get("observer_in_subject_totals") is False
        and observation.get("subject_artifacts_mutated") is False
    )
    record("collector_boundary_ok", collector_ok)

    subject_execution_binding_ok = all(
        execution.get("run_binding", {}).get("execution_run_key")
        == subject_run_key
        and execution.get("run_binding", {}).get("subject_run_key")
        == subject_run_key
        and execution.get("run_binding", {}).get("binding_mode")
        == "current_subject_run"
        for execution in executions_list
        if execution.get("execution_scope") == "subject"
    )
    record("subject_execution_run_binding_ok", subject_execution_binding_ok)

    authority_ok = True
    authority_state_map = {
        "workflow": "workflow_source",
        "policy": "policy",
        "gate_registry": "gate_registry",
    }
    for authority_name, state_type in authority_state_map.items():
        authority = authority_inputs.get(authority_name)
        if not isinstance(authority, dict):
            authority_ok = False
            continue
        if authority.get("source_commit") != subject.get("source_commit"):
            authority_ok = False
        matching = [
            state
            for state in states_list
            if state.get("state_type") == state_type
            and state.get("path_or_uri") == authority.get("path")
        ]
        if len(matching) != 1:
            authority_ok = False
            continue
        state = matching[0]
        if (
            state.get("sha256") != authority.get("sha256")
            or state.get("content_status") != "exact_digest"
            or state.get("authority_bearing") is not True
        ):
            authority_ok = False
    record("authority_input_bindings_ok", authority_ok)

    parent_refs_ok = all(
        execution.get("parent_execution_id") is None
        or execution.get("parent_execution_id") in executions
        for execution in executions_list
    )
    record("execution_parent_references_resolve", parent_refs_ok)
    record("execution_graph_acyclic", _execution_graph_acyclic(executions))

    workflow_shape_ok = True
    for execution in executions_list:
        kind = execution.get("execution_kind")
        parent_id = execution.get("parent_execution_id")
        if kind == "workflow_job":
            workflow_shape_ok &= (
                parent_id is None
                and execution.get("step_name") is None
                and execution.get("step_number") is None
            )
        if kind == "workflow_step":
            parent = executions.get(parent_id)
            workflow_shape_ok &= (
                isinstance(parent, dict)
                and parent.get("execution_kind") == "workflow_job"
                and execution.get("step_name") is not None
                and execution.get("step_number") is not None
                and execution.get("workflow_name") == parent.get("workflow_name")
                and execution.get("job_name") == parent.get("job_name")
                and execution.get("job_id") == parent.get("job_id")
                and execution.get("job_attempt") == parent.get("job_attempt")
            )
    record("workflow_job_step_shape_ok", workflow_shape_ok)

    execution_state_refs_ok = all(
        all(state_id in states for state_id in execution.get("input_state_ids", []))
        and all(
            state_id in states
            for state_id in execution.get("output_state_ids", [])
        )
        and set(execution.get("input_state_ids", [])).isdisjoint(
            execution.get("output_state_ids", [])
        )
        for execution in executions_list
    )
    record("execution_state_references_resolve", execution_state_refs_ok)

    internal_states_by_execution: dict[str, set[str]] = {
        execution_id: set() for execution_id in executions
    }
    for call in calls_list:
        parent_id = call.get("parent_execution_id")
        if parent_id in internal_states_by_execution:
            internal_states_by_execution[parent_id].update(
                call.get("request", {}).get("payload", {}).get("state_ids", [])
            )
            internal_states_by_execution[parent_id].update(
                call.get("response", {}).get("payload", {}).get("state_ids", [])
            )
    for inference in inferences_list:
        parent_id = inference.get("parent_execution_id")
        if parent_id in internal_states_by_execution:
            internal_states_by_execution[parent_id].update(
                inference.get("request", {}).get("input_state_ids", [])
            )
            internal_states_by_execution[parent_id].update(
                inference.get("response", {}).get("output_state_ids", [])
            )

    state_execution_refs_ok = True
    state_producer_relation_ok = True
    for state in states_list:
        producer_id = state.get("producer_execution_id")
        observer_id = state.get("observer_execution_id")
        if producer_id is not None and producer_id not in executions:
            state_execution_refs_ok = False
        if observer_id not in executions:
            state_execution_refs_ok = False
        if observer_id != collector_id:
            state_execution_refs_ok = False
        if producer_id is not None:
            producer_execution = executions.get(producer_id, {})
            related_states = (
                set(producer_execution.get("input_state_ids", []))
                | set(producer_execution.get("output_state_ids", []))
                | internal_states_by_execution.get(producer_id, set())
            )
            if state.get("state_id") not in related_states:
                state_producer_relation_ok = False
    for execution in executions_list:
        for state_id in execution.get("output_state_ids", []):
            if states.get(state_id, {}).get("producer_execution_id") != execution.get(
                "execution_id"
            ):
                state_producer_relation_ok = False
    record("state_execution_references_resolve", state_execution_refs_ok)
    record("state_producer_relations_ok", state_producer_relation_ok)

    mutation_authority_ok = True
    for execution in executions_list:
        permitted = execution.get("permitted_mutation_authority")
        permitted_rank = AUTHORITY_MUTATION_RANK.get(permitted)
        for state_id in execution.get("output_state_ids", []):
            mutation = states.get(state_id, {}).get("mutation_class")
            if permitted == "none" and mutation not in {None, "none"}:
                mutation_authority_ok = False
            elif permitted == "advisory_output" and mutation not in {
                None,
                "none",
                "advisory_output",
            }:
                mutation_authority_ok = False
            elif permitted == "preservation_output" and mutation not in {
                None,
                "none",
                "preservation_output",
            }:
                mutation_authority_ok = False
            elif mutation in AUTHORITATIVE_MUTATION_CLASSES:
                mutation_rank = AUTHORITY_MUTATION_RANK.get(mutation)
                if (
                    permitted_rank is None
                    or mutation_rank is None
                    or mutation_rank > permitted_rank
                ):
                    mutation_authority_ok = False
    record("mutation_authority_relations_ok", mutation_authority_ok)

    state_authority_ok = all(
        (
            state.get("authority_bearing") is True
            or state.get("mutation_class")
            in {"none", "advisory_output", "preservation_output"}
        )
        and state.get("secret_material_included") is False
        for state in states_list
    )
    record("state_authority_and_privacy_ok", state_authority_ok)

    call_refs_ok = True
    for call in calls_list:
        parent_id = call.get("parent_execution_id")
        parent = executions.get(parent_id)
        if (
            not isinstance(parent, dict)
            or call.get("call_id") not in parent.get("external_call_ids", [])
        ):
            call_refs_ok = False
        for payload_name in ("request", "response"):
            payload = call.get(payload_name, {}).get("payload", {})
            if not _payload_semantics_ok(payload):
                call_refs_ok = False
            for state_id in payload.get("state_ids", []):
                if state_id not in states:
                    call_refs_ok = False
        if call.get("request", {}).get("authorization_material_included") is not False:
            call_refs_ok = False
        if call.get("request", {}).get("cookies_included") is not False:
            call_refs_ok = False
        if call.get("response", {}).get("set_cookie_included") is not False:
            call_refs_ok = False
    for execution in executions_list:
        for call_id in execution.get("external_call_ids", []):
            if calls.get(call_id, {}).get("parent_execution_id") != execution.get(
                "execution_id"
            ):
                call_refs_ok = False
    record("external_call_relations_ok", call_refs_ok)

    inference_refs_ok = True
    for inference in inferences_list:
        parent_id = inference.get("parent_execution_id")
        parent = executions.get(parent_id)
        if (
            not isinstance(parent, dict)
            or inference.get("inference_id")
            not in parent.get("model_inference_ids", [])
        ):
            inference_refs_ok = False

        request_states = inference.get("request", {}).get("input_state_ids", [])
        response = inference.get("response", {})
        output_states = response.get("output_state_ids", [])
        if not all(state_id in states for state_id in request_states + output_states):
            inference_refs_ok = False
        if not set(request_states).issubset(parent.get("input_state_ids", [])):
            inference_refs_ok = False
        if not set(output_states).issubset(parent.get("output_state_ids", [])):
            inference_refs_ok = False

        output_status = response.get("output_capture_status")
        if output_status == "recorded":
            if not output_states or not isinstance(
                response.get("response_metadata_sha256"), str
            ):
                inference_refs_ok = False
        elif output_status in {"no_output", "not_recorded"}:
            if output_states:
                inference_refs_ok = False
        else:
            inference_refs_ok = False

        if inference.get("capture_status") == "complete" and output_status != (
            "recorded"
        ):
            inference_refs_ok = False
        if inference.get("request", {}).get("raw_prompt_included") is not False:
            inference_refs_ok = False
        if response.get("raw_output_included") is not False:
            inference_refs_ok = False
        if not _model_usage_ok(inference.get("usage", {})):
            inference_refs_ok = False

    for execution in executions_list:
        for inference_id in execution.get("model_inference_ids", []):
            if inferences.get(inference_id, {}).get("parent_execution_id") != (
                execution.get("execution_id")
            ):
                inference_refs_ok = False
    record("model_inference_relations_ok", inference_refs_ok)

    exact_action_identity_ok = all(
        not (
            execution.get("source_identity", {}).get("source_kind")
            == "github_action"
            and execution.get("source_identity", {}).get("identity_status")
            == "exact"
        )
        or isinstance(
            execution.get("source_identity", {}).get("action_commit_sha"),
            str,
        )
        for execution in executions_list
    )
    record("exact_github_action_identity_pinned", exact_action_identity_ok)

    measurement_refs_ok = True
    resource_ids_by_target: dict[str, set[str]] = {}
    for measurement in measurements_list:
        target_kind = measurement.get("target_kind")
        target_id = measurement.get("target_id")
        expected_prefix = {
            "execution": "execution:",
            "external_call": "call:",
            "model_inference": "inference:",
        }.get(target_kind)
        target_map = {
            "execution": executions,
            "external_call": calls,
            "model_inference": inferences,
        }.get(target_kind, {})
        if (
            not isinstance(target_id, str)
            or expected_prefix is None
            or not target_id.startswith(expected_prefix)
            or target_id not in target_map
        ):
            measurement_refs_ok = False
            continue
        resource_ids_by_target.setdefault(target_id, set()).add(
            measurement.get("measurement_id")
        )
        if not _unit_and_value_ok(measurement):
            measurement_refs_ok = False
        if measurement.get("estimated") is not False:
            measurement_refs_ok = False
        if not all(
            state_id in states
            for state_id in measurement.get("evidence_state_ids", [])
        ):
            measurement_refs_ok = False
        target_record = target_map[target_id]
        if measurement.get("measurement_id") not in target_record.get(
            "resource_measurement_ids", []
        ):
            measurement_refs_ok = False

    for target_map in (executions, calls, inferences):
        for target_id, target in target_map.items():
            if set(target.get("resource_measurement_ids", [])) != (
                resource_ids_by_target.get(target_id, set())
            ):
                measurement_refs_ok = False
    record("resource_measurement_relations_ok", measurement_refs_ok)

    token_measurements_ok = True
    for measurement in measurements_list:
        axis = measurement.get("axis")
        if axis not in {"model_input_tokens", "model_output_tokens"}:
            continue
        inference = inferences.get(measurement.get("target_id"))
        if not inference:
            token_measurements_ok = False
            continue
        expected = inference.get("usage", {}).get(
            "input_tokens" if axis == "model_input_tokens" else "output_tokens"
        )
        if expected is None or measurement.get("value") != expected:
            token_measurements_ok = False
    record("model_token_measurements_match_usage", token_measurements_ok)

    duration_measurements_ok = True
    for measurement in measurements_list:
        if measurement.get("measurement_source") != (
            "derived_from_recorded_timestamps"
        ):
            continue
        if measurement.get("axis") not in {
            "runner_wall_seconds",
            "job_wall_seconds",
            "step_wall_seconds",
        }:
            continue
        target = executions.get(measurement.get("target_id"))
        duration_ms = target.get("timing", {}).get("duration_ms") if target else None
        if duration_ms is None or not math.isclose(
            float(measurement.get("value")),
            float(duration_ms) / 1000.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            duration_measurements_ok = False
    record("derived_duration_measurements_match_timing", duration_measurements_ok)

    timestamp_resolution_ms = timing_basis.get("timestamp_resolution_ms", 0.0)
    try:
        timestamp_resolution_ms = float(timestamp_resolution_ms)
    except Exception:
        timestamp_resolution_ms = 0.0

    timings_ok = all(
        _timing_valid(
            row.get("timing", {}),
            timestamp_resolution_ms=timestamp_resolution_ms,
        )
        for row in executions_list + calls_list + inferences_list
    )
    record("runtime_timings_consistent", timings_ok)

    try:
        capture_started = parse_utc(observation.get("capture_started_utc"))
        capture_completed = parse_utc(observation.get("capture_completed_utc"))
        capture_window_ok = capture_completed >= capture_started
    except Exception:
        capture_started = datetime.min.replace(tzinfo=timezone.utc)
        capture_completed = datetime.max.replace(tzinfo=timezone.utc)
        capture_window_ok = False

    if capture_window_ok:
        packet_created = packet_identity.get("packet_created_utc")
        try:
            capture_window_ok &= parse_utc(packet_created) >= capture_completed
        except Exception:
            capture_window_ok = False

        for row in executions_list + calls_list + inferences_list:
            timing = row.get("timing", {})
            capture_window_ok &= _within_capture(
                timing.get("started_utc"),
                capture_started=capture_started,
                capture_completed=capture_completed,
            )
            capture_window_ok &= _within_capture(
                timing.get("completed_utc"),
                capture_started=capture_started,
                capture_completed=capture_completed,
            )
        for state in states_list:
            capture_window_ok &= _within_capture(
                state.get("observed_at_utc"),
                capture_started=capture_started,
                capture_completed=capture_completed,
            )
        for measurement in measurements_list:
            capture_window_ok &= _time_window_valid(
                measurement.get("window_started_utc"),
                measurement.get("window_completed_utc"),
            )
            capture_window_ok &= _within_capture(
                measurement.get("window_started_utc"),
                capture_started=capture_started,
                capture_completed=capture_completed,
            )
            capture_window_ok &= _within_capture(
                measurement.get("window_completed_utc"),
                capture_started=capture_started,
                capture_completed=capture_completed,
            )
    record("capture_window_and_packet_time_ok", capture_window_ok)

    sequence = packet_identity.get("packet_sequence")
    previous = packet_identity.get("previous_packet_sha256")
    chain_ok = (
        isinstance(sequence, int)
        and not isinstance(sequence, bool)
        and sequence >= 0
        and ((sequence == 0 and previous is None) or (sequence >= 1 and isinstance(previous, str)))
    )
    record("packet_sequence_chain_ok", chain_ok)

    redaction_ok = (
        privacy.get("redaction_applied") is not True
        or isinstance(privacy.get("redaction_rules_sha256"), str)
    )
    record("redaction_rules_binding_ok", redaction_ok)

    privacy_ok = all(
        privacy.get(name) is False
        for name in (
            "raw_environment_included",
            "secret_values_included",
            "authorization_headers_included",
            "cookies_included",
            "request_bodies_included",
            "response_bodies_included",
            "raw_prompt_text_included",
            "raw_model_output_included",
        )
    ) and all(
        execution.get("command_identity", {}).get("raw_command_included") is False
        and execution.get("execution_environment", {}).get(
            "raw_environment_included"
        )
        is False
        for execution in executions_list
    )
    record("privacy_boundary_ok", privacy_ok)

    record_status = packet.get("record_status")
    mode_ok = True
    mode_values = (
        producer.get("collection_mode"),
        packet_identity.get("packet_scope"),
        observation.get("collector_mode"),
    )
    if record_status == "example":
        mode_ok = mode_values == ("example", "example", "example")
    elif record_status == "observed":
        mode_ok = all(value != "example" for value in mode_values)
    else:
        mode_ok = False
    record("record_status_collection_modes_ok", mode_ok)

    observed_jobs = sum(
        1
        for execution in executions_list
        if execution.get("execution_scope") == "subject"
        and execution.get("execution_kind") == "workflow_job"
    )
    observed_steps = sum(
        1
        for execution in executions_list
        if execution.get("execution_scope") == "subject"
        and execution.get("execution_kind") == "workflow_step"
    )
    counts_ok = (
        coverage.get("observed_job_count") == observed_jobs
        and coverage.get("observed_step_count") == observed_steps
        and coverage.get("execution_records") == len(executions_list)
        and coverage.get("state_records") == len(states_list)
        and coverage.get("external_call_records") == len(calls_list)
        and coverage.get("model_inference_records") == len(inferences_list)
        and coverage.get("resource_measurement_records")
        == len(measurements_list)
    )
    record("coverage_record_counts_match", counts_ok)

    missing_execution_ids = coverage.get("missing_execution_ids", [])
    missing_ok = set(missing_execution_ids).isdisjoint(executions)
    record("missing_execution_ids_are_unobserved", missing_ok)

    axes_observed = set(coverage.get("resource_axes_observed", []))
    axes_unavailable = set(coverage.get("resource_axes_unavailable", []))
    measured_axes = {measurement.get("axis") for measurement in measurements_list}
    axes_ok = (
        axes_observed == measured_axes
        and axes_observed.isdisjoint(axes_unavailable)
        and axes_observed | axes_unavailable == RESOURCE_AXES
    )
    record("resource_axis_coverage_partition_ok", axes_ok)

    capture_summaries_ok = (
        coverage.get("external_call_capture_status")
        == _derived_capture_status(calls_list)
        and coverage.get("model_inference_capture_status")
        == _derived_capture_status(inferences_list)
        and coverage.get("state_digest_capture_status")
        == _derived_state_digest_status(states_list)
    )
    record("coverage_capture_summaries_match", capture_summaries_ok)

    coverage_status = coverage.get("coverage_status")
    complete_conditions = (
        coverage.get("expected_job_count") == observed_jobs
        and coverage.get("expected_step_count") == observed_steps
        and missing_execution_ids == []
        and coverage.get("unobserved_reasons") == []
        and axes_unavailable == set()
        and coverage.get("external_call_capture_status") in {"complete", "none"}
        and coverage.get("model_inference_capture_status") in {"complete", "none"}
        and coverage.get("state_digest_capture_status") in {"complete", "none"}
    )
    explicit_gap = (
        coverage.get("expected_job_count") is None
        or coverage.get("expected_step_count") is None
        or coverage.get("expected_job_count") != observed_jobs
        or coverage.get("expected_step_count") != observed_steps
        or bool(missing_execution_ids)
        or bool(coverage.get("unobserved_reasons"))
        or bool(axes_unavailable)
        or coverage.get("external_call_capture_status") in {"partial", "unknown"}
        or coverage.get("model_inference_capture_status") in {"partial", "unknown"}
        or coverage.get("state_digest_capture_status") in {"partial", "unknown"}
    )
    if coverage_status == "complete":
        coverage_semantics_ok = complete_conditions
    elif coverage_status == "partial":
        coverage_semantics_ok = explicit_gap and not complete_conditions
    elif coverage_status == "unknown":
        coverage_semantics_ok = explicit_gap
    else:
        coverage_semantics_ok = False
    record("coverage_status_semantics_ok", coverage_semantics_ok)

    errors_field = packet.get("errors")
    ok_field = packet.get("ok")
    packet_ok_semantics = (
        isinstance(errors_field, list)
        and ((ok_field is True and errors_field == []) or (ok_field is False and len(errors_field) > 0))
    )
    record("packet_ok_errors_semantics_ok", packet_ok_semantics)

    return checks, errors


def build_diagnostic(
    *,
    schema_path: Path,
    packet_path: Path,
) -> tuple[dict[str, Any], int]:
    try:
        schema = load_json(schema_path)
        packet = load_json(packet_path)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"read_error: {exc}"],
        )
        return diagnostic, 2

    if not isinstance(schema, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=["schema_not_object"],
        )
        return diagnostic, 2

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"schema_invalid: {exc}"],
        )
        return diagnostic, 2

    errors = schema_errors(schema, packet)
    schema_valid = not errors

    if not isinstance(packet, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["packet_not_object"],
        )
        return diagnostic, 1

    checks: dict[str, bool] = {}
    if schema_valid:
        semantic, semantic_errors_list = semantic_checks(packet)
        checks.update(semantic)
        errors.extend(semantic_errors_list)
    else:
        checks["semantic_checks_skipped_due_to_schema_errors"] = False

    ok = schema_valid and all(checks.values()) and not errors
    diagnostic = make_diagnostic(
        ok=ok,
        schema_valid=schema_valid,
        checks=checks,
        errors=errors,
    )
    return diagnostic, 0 if ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a PULSEmech compute runtime observation packet v0 "
            "against its strict JSON Schema and semantic contract."
        )
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the runtime-observation packet schema.",
    )
    parser.add_argument(
        "--packet",
        default=str(DEFAULT_PACKET),
        help="Path to the runtime-observation packet JSON.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the deterministic diagnostic JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_path = Path(args.schema)
    packet_path = Path(args.packet)
    output = Path(args.output) if args.output else None

    try:
        reject_unsafe_output(
            output,
            schema_path=schema_path,
            packet_path=packet_path,
        )
    except SemanticError as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[str(exc)],
        )
        sys.stderr.write(render_json(diagnostic))
        return 2

    diagnostic, exit_code = build_diagnostic(
        schema_path=schema_path,
        packet_path=packet_path,
    )
    rendered = render_json(diagnostic)
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
