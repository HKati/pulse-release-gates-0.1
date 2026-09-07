#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable


TOOL_NAME = "check_pulsemech_compute_binding_report_v0"
SCHEMA_VERSION = "pulsemech_compute_binding_report_v0"
REPORT_TYPE = "pulsemech_compute_binding_report"

RESOURCE_AXIS_UNITS: dict[str, str] = {
    "runner_wall_seconds": "seconds",
    "job_wall_seconds": "seconds",
    "step_wall_seconds": "seconds",
    "cpu_seconds": "seconds",
    "gpu_seconds": "seconds",
    "memory_gb_seconds": "GB-seconds",
    "network_bytes_sent": "bytes",
    "network_bytes_received": "bytes",
    "storage_bytes_written": "bytes",
    "artifact_bytes_uploaded": "bytes",
    "external_api_calls": "calls",
    "model_input_tokens": "tokens",
    "model_output_tokens": "tokens",
    "retry_count": "count",
    "rerun_count": "count",
}

RESOURCE_CLASSES = (
    "transition_bound",
    "evidence_bound",
    "preservation_bound",
    "advisory_bound",
    "unbound",
    "unknown",
)

SUMMARY_COUNT_FIELDS: dict[str, str] = {
    "transition_bound": "transition_bound_nodes",
    "evidence_bound": "evidence_bound_nodes",
    "preservation_bound": "preservation_bound_nodes",
    "advisory_bound": "advisory_bound_nodes",
    "unbound": "unbound_nodes",
    "unknown": "unknown_nodes",
}

ROLE_TO_COMPLETE_CLASS: dict[str, str] = {
    "transition": "transition_bound",
    "evidence": "evidence_bound",
    "preservation": "preservation_bound",
    "advisory": "advisory_bound",
    "observer": "observer",
    "unknown": "unknown",
}

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

FORBIDDEN_ACTIVATION_FIELDS = {
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

FLOAT_TOLERANCE = 1e-9


class StrictJsonError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PULSEmech compute-binding report v0."
    )
    parser.add_argument("--schema", required=True, help="Path to report schema")
    parser.add_argument("--report", required=True, help="Path to report JSON")
    parser.add_argument(
        "--output",
        help="Optional path for the deterministic validator diagnostic",
    )
    parser.add_argument("--subject-input")
    parser.add_argument("--carrier")
    parser.add_argument("--repository-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--runtime-packet", action="append", default=[])
    parser.add_argument("--runtime-extent")
    return parser.parse_args()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def load_json_strict(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )


def same_target(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True

    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass

    return False


def make_diagnostic(
    *,
    ok: bool,
    schema_valid: bool,
    checks: dict[str, bool],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": ok,
        "schema_version": SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "schema_valid": schema_valid,
        "checks": checks,
        "errors": sorted(set(errors)),
    }


def emit_diagnostic(diagnostic: dict[str, Any], output: Path | None) -> None:
    rendered = (
        json.dumps(
            diagnostic,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def schema_validation_errors(
    schema: dict[str, Any],
    report: Any,
) -> list[str]:
    import jsonschema

    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(
            validator.iter_errors(report),
            key=lambda error: (list(error.path), error.message),
        )
    ]


def sorted_unique_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(value, str) for value in values)
        and values == sorted(set(values))
    )


def add_check(
    checks: dict[str, bool],
    errors: list[str],
    name: str,
    category_errors: Iterable[str],
) -> None:
    normalized = sorted(set(category_errors))
    checks[name] = not normalized
    errors.extend(normalized)


def get_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def get_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def close_enough(left: float, right: float) -> bool:
    return math.isclose(
        float(left),
        float(right),
        rel_tol=FLOAT_TOLERANCE,
        abs_tol=FLOAT_TOLERANCE,
    )


def expected_binding_class(node: dict[str, Any]) -> str:
    role = node.get("declared_role")
    status = node.get("binding_status")
    scope = node.get("execution_scope")

    if scope == "analysis_observer" or role == "observer":
        return "observer"

    if status == "complete":
        return ROLE_TO_COMPLETE_CLASS.get(str(role), "unknown")

    if status == "none":
        return "unbound"

    return "unknown"


def check_identity_and_boundary(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("identity_error: schema_version_mismatch")

    if report.get("report_type") != REPORT_TYPE:
        errors.append("identity_error: report_type_mismatch")

    boundary = get_dict(report.get("analysis_boundary"))
    subject_key = boundary.get("subject_run_key")
    analysis_key = boundary.get("analysis_run_key")

    if boundary.get("observer_in_subject_totals") is not False:
        errors.append("boundary_error: observer_in_subject_totals_must_be_false")

    if not isinstance(subject_key, str) or not subject_key:
        errors.append("boundary_error: subject_run_key_missing")

    if not isinstance(analysis_key, str) or not analysis_key:
        errors.append("boundary_error: analysis_run_key_missing")

    if isinstance(subject_key, str) and subject_key == analysis_key:
        errors.append("boundary_error: analysis_run_key_must_differ_from_subject_run_key")

    return errors


def check_deterministic_ordering(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    active_sets = get_list(get_dict(report.get("subject")).get("active_policy_sets"))
    if active_sets != sorted(active_sets):
        errors.append("ordering_error: active_policy_sets_not_sorted")

    inputs = get_list(report.get("inputs"))
    input_keys = [
        (
            str(get_dict(item).get("role", "")),
            str(get_dict(item).get("path_or_uri", "")),
            str(get_dict(item).get("sha256", "")),
        )
        for item in inputs
    ]
    if input_keys != sorted(input_keys):
        errors.append("ordering_error: inputs_not_sorted")

    compute_nodes = get_list(report.get("compute_nodes"))
    node_ids = [str(get_dict(node).get("node_id", "")) for node in compute_nodes]
    if node_ids != sorted(node_ids):
        errors.append("ordering_error: compute_nodes_not_sorted")

    state_nodes = get_list(report.get("state_nodes"))
    state_ids = [str(get_dict(state).get("state_id", "")) for state in state_nodes]
    if state_ids != sorted(state_ids):
        errors.append("ordering_error: state_nodes_not_sorted")

    edges = get_list(report.get("edges"))
    edge_ids = [str(get_dict(edge).get("edge_id", "")) for edge in edges]
    if edge_ids != sorted(edge_ids):
        errors.append("ordering_error: edges_not_sorted")

    for node in compute_nodes:
        item = get_dict(node)
        node_id = item.get("node_id")
        for field in (
            "input_state_ids",
            "output_state_ids",
            "observed_mutation_classes",
        ):
            if not sorted_unique_strings(item.get(field)):
                errors.append(
                    f"ordering_error: {node_id}.{field}_not_sorted_unique"
                )

        usage = get_dict(item.get("resource_usage"))
        if list(usage) != sorted(usage):
            errors.append(
                f"ordering_error: {node_id}.resource_usage_keys_not_sorted"
            )

    for edge in edges:
        item = get_dict(edge)
        edge_id = item.get("edge_id")
        for field in ("evidence_digests", "notes"):
            if not sorted_unique_strings(item.get(field)):
                errors.append(
                    f"ordering_error: {edge_id}.{field}_not_sorted_unique"
                )

    axes = get_dict(get_dict(report.get("resource_summary")).get("axes"))
    if list(axes) != sorted(axes):
        errors.append("ordering_error: resource_axes_not_sorted")

    findings = get_list(report.get("findings"))

    def finding_key(value: Any) -> tuple[str, str, str, str, str]:
        finding = get_dict(value)
        return (
            str(finding.get("finding_id", "")),
            str(finding.get("node_id") or ""),
            str(finding.get("state_id") or ""),
            str(finding.get("edge_id") or ""),
            str(finding.get("message", "")),
        )

    if [finding_key(value) for value in findings] != sorted(
        finding_key(value) for value in findings
    ):
        errors.append("ordering_error: findings_not_sorted")

    for finding in findings:
        item = get_dict(finding)
        if not sorted_unique_strings(item.get("evidence_refs")):
            errors.append(
                "ordering_error: "
                f"{item.get('finding_id')}.evidence_refs_not_sorted_unique"
            )

    report_errors = report.get("errors")
    if not sorted_unique_strings(report_errors):
        errors.append("ordering_error: report_errors_not_sorted_unique")

    return errors


def check_unique_ids_and_references(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    compute_nodes = [get_dict(node) for node in get_list(report.get("compute_nodes"))]
    state_nodes = [get_dict(state) for state in get_list(report.get("state_nodes"))]
    edges = [get_dict(edge) for edge in get_list(report.get("edges"))]

    compute_ids = [str(node.get("node_id", "")) for node in compute_nodes]
    state_ids = [str(state.get("state_id", "")) for state in state_nodes]
    edge_ids = [str(edge.get("edge_id", "")) for edge in edges]

    if len(compute_ids) != len(set(compute_ids)):
        errors.append("reference_error: duplicate_compute_node_id")

    if len(state_ids) != len(set(state_ids)):
        errors.append("reference_error: duplicate_state_node_id")

    if len(edge_ids) != len(set(edge_ids)):
        errors.append("reference_error: duplicate_edge_id")

    compute_id_set = set(compute_ids)
    state_id_set = set(state_ids)
    edge_id_set = set(edge_ids)
    all_ids = compute_id_set | state_id_set

    for node in compute_nodes:
        node_id = node.get("node_id")
        for field in ("input_state_ids", "output_state_ids"):
            for state_id in get_list(node.get(field)):
                if state_id not in state_id_set:
                    errors.append(
                        f"reference_error: {node_id}.{field}_missing:{state_id}"
                    )

    for state in state_nodes:
        state_id = state.get("state_id")
        producer_id = state.get("producer_node_id")
        if producer_id is not None and producer_id not in compute_id_set:
            errors.append(
                f"reference_error: {state_id}.producer_missing:{producer_id}"
            )

    for edge in edges:
        edge_id = edge.get("edge_id")
        from_id = edge.get("from_id")
        to_id = edge.get("to_id")

        if from_id not in all_ids:
            errors.append(
                f"reference_error: {edge_id}.from_id_missing:{from_id}"
            )

        if to_id not in all_ids:
            errors.append(
                f"reference_error: {edge_id}.to_id_missing:{to_id}"
            )

        direction = (
            from_id in state_id_set and to_id in compute_id_set,
            from_id in compute_id_set and to_id in state_id_set,
        )
        if direction not in ((True, False), (False, True)):
            errors.append(
                f"reference_error: {edge_id}.must_connect_one_compute_and_one_state"
            )

    for finding in get_list(report.get("findings")):
        item = get_dict(finding)
        finding_id = item.get("finding_id")
        refs = (
            ("node_id", compute_id_set),
            ("state_id", state_id_set),
            ("edge_id", edge_id_set),
        )
        for field, valid_ids in refs:
            value = item.get(field)
            if value is not None and value not in valid_ids:
                errors.append(
                    f"reference_error: finding:{finding_id}.{field}_missing:{value}"
                )

    return errors


def check_binding_classes_and_run_bindings(
    report: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    boundary = get_dict(report.get("analysis_boundary"))
    subject_key = boundary.get("subject_run_key")
    analysis_key = boundary.get("analysis_run_key")

    for raw_node in get_list(report.get("compute_nodes")):
        node = get_dict(raw_node)
        node_id = node.get("node_id")
        scope = node.get("execution_scope")
        role = node.get("declared_role")
        binding_class = node.get("binding_class")
        expected_class = expected_binding_class(node)

        if binding_class != expected_class:
            errors.append(
                "binding_error: "
                f"{node_id}.binding_class={binding_class!r}"
                f" expected={expected_class!r}"
            )

        run_binding = get_dict(node.get("run_binding"))
        if run_binding.get("subject_run_key") != subject_key:
            errors.append(
                f"binding_error: {node_id}.subject_run_key_mismatch"
            )

        if scope == "subject":
            if role == "observer" or binding_class == "observer":
                errors.append(
                    f"binding_error: {node_id}.subject_scope_cannot_be_observer"
                )
            if run_binding.get("binding_mode") != "current_subject_run":
                errors.append(
                    f"binding_error: {node_id}.subject_binding_mode_mismatch"
                )
            if run_binding.get("execution_run_key") != subject_key:
                errors.append(
                    f"binding_error: {node_id}.subject_execution_run_key_mismatch"
                )

        elif scope == "analysis_observer":
            if role != "observer" or binding_class != "observer":
                errors.append(
                    f"binding_error: {node_id}.observer_scope_role_mismatch"
                )
            if run_binding.get("binding_mode") not in {
                "offline_observer",
                "post_decision_observer",
            }:
                errors.append(
                    f"binding_error: {node_id}.observer_binding_mode_mismatch"
                )
            if (
                run_binding.get("binding_mode") == "offline_observer"
                and run_binding.get("execution_run_key") != analysis_key
            ):
                errors.append(
                    f"binding_error: {node_id}.offline_observer_run_key_mismatch"
                )

        elif scope == "observation_collector":
            if role != "observer" or binding_class != "observer" or "runtime_origin" not in node:
                errors.append(f"binding_error: {node_id}.collector_scope_invalid")
            if run_binding.get("binding_mode") not in {"post_run_observer", "external_export", "current_subject_run"}:
                errors.append(f"binding_error: {node_id}.collector_mode_invalid")

        if run_binding.get("binding_complete") is not True:
            errors.append(
                f"binding_error: {node_id}.run_binding_not_complete"
            )

    return errors


def check_node_edge_relations(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    analysis_level = get_dict(
        report.get("analysis_boundary")
    ).get("analysis_level")
    compute_nodes = {
        str(get_dict(node).get("node_id")): get_dict(node)
        for node in get_list(report.get("compute_nodes"))
    }
    state_nodes = {
        str(get_dict(state).get("state_id")): get_dict(state)
        for state in get_list(report.get("state_nodes"))
    }
    edges = [get_dict(edge) for edge in get_list(report.get("edges"))]

    related_inputs: set[tuple[str, str]] = set()
    related_outputs: set[tuple[str, str]] = set()
    observed_inputs: set[tuple[str, str]] = set()
    observed_outputs: set[tuple[str, str]] = set()

    for edge in edges:
        from_id = edge.get("from_id")
        to_id = edge.get("to_id")
        declared_or_observed = (
            edge.get("declared") is True
            or edge.get("observed") is True
        )

        if from_id in state_nodes and to_id in compute_nodes:
            relation = (str(to_id), str(from_id))
            if declared_or_observed:
                related_inputs.add(relation)
            if edge.get("observed") is True:
                observed_inputs.add(relation)

        elif from_id in compute_nodes and to_id in state_nodes:
            relation = (str(from_id), str(to_id))
            if declared_or_observed:
                related_outputs.add(relation)
            if edge.get("observed") is True:
                observed_outputs.add(relation)

        if (
            edge.get("binding_status") == "complete"
            and edge.get("observed") is not True
        ):
            errors.append(
                f"relation_error: {edge.get('edge_id')}.complete_edge_not_observed"
            )

        if (
            edge.get("observed") is True
            and edge.get("binding_status") == "complete"
            and not get_list(edge.get("evidence_digests"))
        ):
            errors.append(
                f"relation_error: {edge.get('edge_id')}.observed_edge_missing_digest"
            )

        if (
            analysis_level == "structural_declared"
            and edge.get("observed") is True
        ):
            errors.append(
                f"relation_error: {edge.get('edge_id')}.structural_level_cannot_claim_observed_edge"
            )

    for node_id, node in compute_nodes.items():
        declared_inputs = {
            (node_id, str(state_id))
            for state_id in get_list(node.get("input_state_ids"))
        }
        declared_outputs = {
            (node_id, str(state_id))
            for state_id in get_list(node.get("output_state_ids"))
        }

        missing_input_relations = declared_inputs - related_inputs
        missing_output_relations = declared_outputs - related_outputs
        extra_input_relations = {
            relation for relation in related_inputs if relation[0] == node_id
        } - declared_inputs
        extra_output_relations = {
            relation for relation in related_outputs if relation[0] == node_id
        } - declared_outputs

        for _, state_id in sorted(missing_input_relations):
            errors.append(
                f"relation_error: {node_id}.input_edge_missing:{state_id}"
            )

        for _, state_id in sorted(missing_output_relations):
            errors.append(
                f"relation_error: {node_id}.output_edge_missing:{state_id}"
            )

        for _, state_id in sorted(extra_input_relations):
            errors.append(
                f"relation_error: {node_id}.undeclared_relation_input:{state_id}"
            )

        for _, state_id in sorted(extra_output_relations):
            errors.append(
                f"relation_error: {node_id}.undeclared_relation_output:{state_id}"
            )

        if node.get("binding_status") == "complete":
            if analysis_level == "structural_declared" and node.get(
                "execution_scope"
            ) == "subject":
                errors.append(
                    f"relation_error: {node_id}.structural_level_cannot_claim_complete_binding"
                )

            missing_observed_inputs = declared_inputs - observed_inputs
            missing_observed_outputs = declared_outputs - observed_outputs

            for _, state_id in sorted(missing_observed_inputs):
                errors.append(
                    f"relation_error: {node_id}.complete_input_not_observed:{state_id}"
                )

            for _, state_id in sorted(missing_observed_outputs):
                errors.append(
                    f"relation_error: {node_id}.complete_output_not_observed:{state_id}"
                )

            for state_id in sorted(
                set(node.get("input_state_ids", []))
                | set(node.get("output_state_ids", []))
            ):
                state = state_nodes.get(str(state_id), {})
                if state.get("sha256") is None:
                    errors.append(
                        f"relation_error: {node_id}.complete_state_digest_missing:{state_id}"
                    )

    for state_id, state in state_nodes.items():
        producer_id = state.get("producer_node_id")
        if producer_id is None:
            continue

        relation = (str(producer_id), state_id)
        if relation not in related_outputs:
            errors.append(
                f"relation_error: {state_id}.producer_edge_missing:{producer_id}"
            )

        producer = compute_nodes.get(str(producer_id), {})
        if (
            producer.get("binding_status") == "complete"
            and relation not in observed_outputs
        ):
            errors.append(
                f"relation_error: {state_id}.complete_producer_edge_not_observed:{producer_id}"
            )

    return errors

def check_mutation_authority(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for raw_node in get_list(report.get("compute_nodes")):
        node = get_dict(raw_node)
        node_id = node.get("node_id")
        authority = node.get("mutation_authority")
        observed = set(get_list(node.get("observed_mutation_classes")))
        status = node.get("binding_status")
        flags = get_dict(node.get("flags"))

        if "runtime_origin" in node:
            if "runtime_binding" not in report:
                errors.append(f"mutation_error: {node_id}.runtime_origin_requires_bound_profile")
                continue
            expected_unbound = bool(observed & AUTHORITATIVE_MUTATION_CLASSES) and status != "complete"
            if node.get("unbound_authoritative_mutation") is not expected_unbound:
                errors.append(f"mutation_error: {node_id}.runtime_mutation_flag_mismatch")
            if flags.get("mutation_authority_present") is not (authority != "none"):
                errors.append(f"mutation_error: {node_id}.runtime_permission_flag_mismatch")
            continue

        expected_authority_flag = authority != "none"
        if flags.get("mutation_authority_present") is not expected_authority_flag:
            errors.append(
                f"mutation_error: {node_id}.mutation_authority_present_mismatch"
            )

        if authority == "none" and observed:
            errors.append(
                f"mutation_error: {node_id}.observed_mutation_without_authority"
            )

        if authority != "none" and observed - {authority}:
            errors.append(
                f"mutation_error: {node_id}.observed_mutation_class_mismatch"
            )

        if status == "complete" and authority != "none" and observed != {authority}:
            errors.append(
                f"mutation_error: {node_id}.complete_binding_missing_observed_mutation"
            )

        authoritative_observed = bool(
            observed & AUTHORITATIVE_MUTATION_CLASSES
        )
        expected_unbound = authoritative_observed and status != "complete"

        if (
            node.get("unbound_authoritative_mutation")
            is not expected_unbound
        ):
            errors.append(
                f"mutation_error: {node_id}.unbound_authoritative_mutation_mismatch"
            )

    return errors


def check_summary_counts(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = [get_dict(node) for node in get_list(report.get("compute_nodes"))]
    summary = get_dict(report.get("summary"))

    subject_nodes = [
        node for node in nodes if node.get("execution_scope") == "subject"
    ]
    observer_nodes = [
        node
        for node in nodes
        if node.get("execution_scope") in {"analysis_observer", "observation_collector"}
    ]

    if summary.get("subject_compute_nodes") != len(subject_nodes):
        errors.append("summary_error: subject_compute_nodes_mismatch")

    if summary.get("observer_nodes") != len(observer_nodes):
        errors.append("summary_error: observer_nodes_mismatch")

    class_counts = Counter(
        str(node.get("binding_class")) for node in subject_nodes
    )

    for binding_class, field in SUMMARY_COUNT_FIELDS.items():
        if summary.get(field) != class_counts.get(binding_class, 0):
            errors.append(f"summary_error: {field}_mismatch")

    classified_total = sum(
        class_counts.get(binding_class, 0)
        for binding_class in RESOURCE_CLASSES
    )
    if classified_total != len(subject_nodes):
        errors.append("summary_error: subject_classification_total_mismatch")

    mutation_count = sum(
        1
        for node in subject_nodes
        if node.get("unbound_authoritative_mutation") is True
    )
    if (
        summary.get("unbound_authoritative_mutation_count")
        != mutation_count
    ):
        errors.append(
            "summary_error: unbound_authoritative_mutation_count_mismatch"
        )

    return errors


def check_resource_axes(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = [get_dict(node) for node in get_list(report.get("compute_nodes"))]
    subject_nodes = [
        node for node in nodes if node.get("execution_scope") == "subject"
    ]
    observer_nodes = [
        node
        for node in nodes
        if node.get("execution_scope") in {"analysis_observer", "observation_collector"}
    ]
    axes = get_dict(get_dict(report.get("resource_summary")).get("axes"))
    summary = get_dict(report.get("summary"))
    axis_names = set(axes)

    for node in nodes:
        node_id = node.get("node_id")
        usage = get_dict(node.get("resource_usage"))
        unknown_axes = set(usage) - set(RESOURCE_AXIS_UNITS)
        for axis in sorted(unknown_axes):
            errors.append(
                f"resource_error: {node_id}.unknown_resource_axis:{axis}"
            )

        expected_partial = set(usage) != axis_names
        flags = get_dict(node.get("flags"))
        if (
            flags.get("resource_measurement_partial")
            is not expected_partial
        ):
            errors.append(
                f"resource_error: {node_id}.resource_measurement_partial_mismatch"
            )

    for axis_name, raw_axis in axes.items():
        axis = get_dict(raw_axis)
        expected_unit = RESOURCE_AXIS_UNITS.get(axis_name)

        if expected_unit is None:
            errors.append(f"resource_error: unknown_axis:{axis_name}")
            continue

        if axis.get("unit") != expected_unit:
            errors.append(
                f"resource_error: {axis_name}.unit_mismatch"
            )

        measured_subject_nodes = [
            node
            for node in subject_nodes
            if axis_name in get_dict(node.get("resource_usage"))
        ]
        measured_observer_nodes = [
            node
            for node in observer_nodes
            if axis_name in get_dict(node.get("resource_usage"))
        ]

        expected_categories: dict[str, float] = {
            binding_class: 0.0 for binding_class in RESOURCE_CLASSES
        }
        for node in measured_subject_nodes:
            binding_class = str(node.get("binding_class"))
            if binding_class not in expected_categories:
                errors.append(
                    f"resource_error: {axis_name}.unsupported_binding_class:{binding_class}"
                )
                continue

            value = get_dict(node.get("resource_usage")).get(axis_name)
            expected_categories[binding_class] += float(value)

        expected_total = sum(expected_categories.values())
        expected_observer = sum(
            float(get_dict(node.get("resource_usage")).get(axis_name))
            for node in measured_observer_nodes
        )

        if not close_enough(axis.get("measured_total", -1), expected_total):
            errors.append(
                f"resource_error: {axis_name}.measured_total_mismatch"
            )

        for binding_class, expected_value in expected_categories.items():
            if not close_enough(
                axis.get(binding_class, -1),
                expected_value,
            ):
                errors.append(
                    f"resource_error: {axis_name}.{binding_class}_mismatch"
                )

        if not close_enough(
            axis.get("observer_overhead", -1),
            expected_observer,
        ):
            errors.append(
                f"resource_error: {axis_name}.observer_overhead_mismatch"
            )

        if axis.get("nodes_with_measurement") != len(measured_subject_nodes):
            errors.append(
                f"resource_error: {axis_name}.nodes_with_measurement_mismatch"
            )

        if axis.get("total_subject_nodes") != len(subject_nodes):
            errors.append(
                f"resource_error: {axis_name}.total_subject_nodes_mismatch"
            )

        expected_coverage = (
            len(measured_subject_nodes) / len(subject_nodes)
            if subject_nodes
            else 0.0
        )
        if not close_enough(
            axis.get("measurement_coverage_ratio", -1),
            expected_coverage,
        ):
            errors.append(
                f"resource_error: {axis_name}.measurement_coverage_ratio_mismatch"
            )

        ratios = get_dict(axis.get("ratios"))
        for binding_class, expected_value in expected_categories.items():
            expected_ratio = (
                expected_value / expected_total
                if expected_total
                else 0.0
            )
            if not close_enough(
                ratios.get(binding_class, -1),
                expected_ratio,
            ):
                errors.append(
                    f"resource_error: {axis_name}.ratios.{binding_class}_mismatch"
                )

        category_total = sum(
            float(axis.get(binding_class, 0))
            for binding_class in RESOURCE_CLASSES
        )
        if not close_enough(
            category_total,
            float(axis.get("measured_total", -1)),
        ):
            errors.append(
                f"resource_error: {axis_name}.category_total_mismatch"
            )

    if not axes:
        expected_status = "none"
    elif all(
        close_enough(
            get_dict(axis).get("measurement_coverage_ratio", -1),
            1.0,
        )
        for axis in axes.values()
    ):
        expected_status = "complete"
    else:
        expected_status = "partial"

    if summary.get("resource_measurement_status") != expected_status:
        errors.append(
            "resource_error: resource_measurement_status_mismatch"
        )

    return errors


def check_findings_and_non_activation(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    forbidden = FORBIDDEN_ACTIVATION_FIELDS & set(report)
    for field in sorted(forbidden):
        errors.append(f"boundary_error: forbidden_activation_field:{field}")

    findings = [get_dict(value) for value in get_list(report.get("findings"))]
    finding_ids = [str(finding.get("finding_id", "")) for finding in findings]

    if len(finding_ids) != len(set(
        (
            finding.get("finding_id"),
            finding.get("node_id"),
            finding.get("state_id"),
            finding.get("edge_id"),
            finding.get("message"),
        )
        for finding in findings
    )):
        errors.append("finding_error: duplicate_finding_record")

    report_errors = get_list(report.get("errors"))
    if report.get("ok") is True and report_errors:
        errors.append("report_error: ok_true_with_errors")

    if report.get("ok") is False and not report_errors:
        errors.append("report_error: ok_false_without_errors")

    subject = get_dict(report.get("subject"))
    if subject.get("decision") not in {"ALLOW", "BLOCK"}:
        errors.append("report_error: invalid_terminal_decision")

    return errors


def build_diagnostic(
    schema_path: Path,
    report_path: Path,
    *, runtime_inputs: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    try:
        schema = load_json_strict(schema_path)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"schema_read_error: {exc}"],
        )
        return diagnostic, 2

    try:
        report = load_json_strict(report_path)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"report_read_error: {exc}"],
        )
        return diagnostic, 2

    try:
        import jsonschema

        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"schema_invalid: {exc}"],
        )
        return diagnostic, 2

    errors = schema_validation_errors(schema, report)
    schema_valid = not errors

    if not isinstance(report, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["report_not_object"],
        )
        return diagnostic, 1

    checks: dict[str, bool] = {}

    semantic_checks: tuple[
        tuple[str, Callable[[dict[str, Any]], list[str]]],
        ...
    ] = (
        ("identity_and_boundary_ok", check_identity_and_boundary),
        ("deterministic_ordering_ok", check_deterministic_ordering),
        ("references_ok", check_unique_ids_and_references),
        ("binding_classes_and_run_bindings_ok", check_binding_classes_and_run_bindings),
        ("node_edge_relations_ok", check_node_edge_relations),
        ("mutation_authority_ok", check_mutation_authority),
        ("summary_counts_ok", check_summary_counts),
        ("resource_axes_ok", check_resource_axes),
        ("findings_and_non_activation_ok", check_findings_and_non_activation),
    )

    if schema_valid:
        for name, function in semantic_checks:
            add_check(checks, errors, name, function(report))
    else:
        for name, _ in semantic_checks:
            checks[name] = False

    if schema_valid and ("runtime_binding" in report or (report.get("record_status") == "observed" and report.get("analysis_boundary", {}).get("analysis_level") == "runtime_observed")):
        add_check(checks, errors, "runtime_source_replay_ok", check_runtime_source_replay(report, runtime_inputs))

    normalized_errors = sorted(set(errors))
    ok = schema_valid and all(checks.values()) and not normalized_errors

    diagnostic = make_diagnostic(
        ok=ok,
        schema_valid=schema_valid,
        checks=checks,
        errors=normalized_errors,
    )
    return diagnostic, 0 if ok else 1


def main() -> int:
    args = parse_args()

    schema_path = Path(args.schema)
    report_path = Path(args.report)
    output_path = Path(args.output) if args.output else None

    if output_path is not None:
        refusal_errors: list[str] = []

        if output_path.name == "status.json":
            refusal_errors.append("refusing_to_write_status_json")

        if same_target(output_path, schema_path):
            refusal_errors.append("refusing_to_overwrite_schema")

        if same_target(output_path, report_path):
            refusal_errors.append("refusing_to_overwrite_report")

        if refusal_errors:
            diagnostic = make_diagnostic(
                ok=False,
                schema_valid=False,
                checks={},
                errors=refusal_errors,
            )
            emit_diagnostic(diagnostic, None)
            return 2

    runtime_inputs = None
    try:
        report_view = capture_diagnostic_document(report_path)
        schema_view = capture_diagnostic_document(schema_path, max_bytes=1024 * 1024)
        document = load_json_strict(report_view)
        if isinstance(document, dict) and "runtime_binding" in document:
            if output_path is not None:
                raise ValueError("runtime_diagnostic_stdout_only")
            if not args.subject_input or not args.carrier or not args.runtime_packet:
                raise ValueError("runtime_source_inputs_required")
            if output_path is not None:
                protected = [Path(args.subject_input), Path(args.carrier), *map(Path, args.runtime_packet)]
                if args.runtime_extent:
                    protected.append(Path(args.runtime_extent))
                if any(same_target(output_path, p) for p in protected):
                    raise ValueError("refusing_to_overwrite_runtime_input")
            captures = runtime_inputs_from_paths(
                subject_input_path=Path(args.subject_input), carrier_path=Path(args.carrier),
                repository_root=Path(args.repository_root), packet_paths=list(map(Path, args.runtime_packet)),
                extent_path=Path(args.runtime_extent) if args.runtime_extent else None,
            )
            runtime_inputs = resolve_runtime_replay_inputs(captures, document["analysis_boundary"]["analysis_run_key"])
    except Exception as exc:
        diagnostic = make_diagnostic(ok=False, schema_valid=False, checks={}, errors=["runtime_intake_failed:" + str(exc)])
        emit_diagnostic(diagnostic, None)
        return 1
    diagnostic, exit_code = build_diagnostic(
        schema_view, report_view, runtime_inputs=runtime_inputs,
    )
    emit_diagnostic(diagnostic, output_path)
    return exit_code


# ---------------------------------------------------------------------------
# Runtime profile: exact upstream replay plus independent graph invariants.
# The replay reuses the one analyzer; it is not a second analyzer implementation.
# ---------------------------------------------------------------------------

RUNTIME_REPORT_PROFILE = "pulsemech_runtime_report_binding_v0"


class RuntimeBytesView:
    """Immutable read-only document view; never reopens its display path."""

    def __init__(self, data: bytes, label: str = "captured-document") -> None:
        self.data = data
        self.label = label

    def read_bytes(self) -> bytes:
        return self.data

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self.data.decode(encoding, errors)

    def __str__(self) -> str:
        return self.label


def capture_diagnostic_document(path: Path, *, max_bytes: int = 64 * 1024 * 1024) -> RuntimeBytesView:
    import os
    import stat
    absolute = Path(os.path.abspath(path))
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        # Preserve the legacy document-only CLI on other platforms. The new
        # runtime path still requires the bridge's descriptor-based capture.
        if not absolute.is_file() or absolute.is_symlink() or absolute.stat().st_size > max_bytes:
            raise ValueError("diagnostic_input_not_bounded_regular_file")
        data = absolute.read_bytes()
        if len(data) > max_bytes:
            raise ValueError("diagnostic_input_too_large")
        return RuntimeBytesView(data, str(absolute))
    dflags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(absolute.anchor, dflags)
    filefd = None
    try:
        for part in absolute.parts[1:-1]:
            nextfd = os.open(part, dflags, dir_fd=fd)
            os.close(fd)
            fd = nextfd
        filefd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        before = os.fstat(filefd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError("diagnostic_input_not_bounded_regular_file")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            part = os.read(filefd, min(1024 * 1024, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        after = os.fstat(filefd)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or len(data) != before.st_size or len(data) > max_bytes):
            raise ValueError("diagnostic_input_changed_during_capture")
        return RuntimeBytesView(data, str(absolute))
    finally:
        if filefd is not None:
            os.close(filefd)
        os.close(fd)


def _runtime_hash(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _runtime_module(path: Path, name: str, *, expected_sha256: str | None = None) -> Any:
    import os
    import stat
    import types
    cursor = path.absolute()
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ValueError("runtime_dependency_symlink")
        cursor = cursor.parent
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024 * 1024:
            raise ValueError("runtime_dependency_not_bounded_regular_file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("runtime_dependency_changed_during_capture")
    finally:
        os.close(fd)
    if len(raw) != before.st_size or (expected_sha256 is not None and _runtime_hash(raw) != expected_sha256):
        raise ValueError("runtime_dependency_digest_mismatch:" + path.name)
    name = name + "_" + _runtime_hash(raw)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__cached__ = None
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    module.__pulsemech_source_sha256__ = _runtime_hash(raw)
    return module


def runtime_inputs_from_paths(
    *, subject_input_path: Path, carrier_path: Path, repository_root: Path,
    packet_paths: list[Path], extent_path: Path | None = None,
) -> dict[str, Any]:
    """Capture once and run the unchanged artifact bridge before runtime replay.

    No network, fixture substitution, or missing-Git-object downgrade is allowed.
    The caller chooses the protected local tool installation, not the report.
    """
    root = Path(__file__).resolve().parents[1]
    bridge = _runtime_module(root / "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py", "runtime_bridge_for_check")
    subject = bridge.capture_regular_file(subject_input_path, label="runtime_subject_input", max_bytes=8 * 1024 * 1024)
    carrier = bridge.capture_regular_file(carrier_path, label="runtime_subject_carrier", max_bytes=64 * 1024 * 1024)
    if not packet_paths or len(packet_paths) > 128:
        raise ValueError("runtime_packet_count_invalid")
    packets = [bridge.capture_regular_file(p, label="runtime_packet", max_bytes=8 * 1024 * 1024) for p in packet_paths]
    if sum(len(p.data) for p in packets) > 64 * 1024 * 1024:
        raise ValueError("runtime_packet_total_too_large")
    extent = bridge.capture_regular_file(extent_path, label="runtime_extent", max_bytes=1024 * 1024) if extent_path is not None else None
    # The analysis key is part of reconstruction and is supplied separately by
    # the report caller below, never mistaken for a subject run key.
    return {"bridge": bridge, "subject_capture": subject, "carrier_capture": carrier,
            "packet_captures": packets, "extent_capture": extent, "repository_root": repository_root}


def resolve_runtime_replay_inputs(captures: dict[str, Any], analysis_run_key: str) -> dict[str, Any]:
    bridge = captures["bridge"]
    baseline = bridge.build_from_captured_inputs(
        packet_capture=captures["subject_capture"], carrier_capture=captures["carrier_capture"],
        repository_root=captures["repository_root"], analysis_run_key=analysis_run_key,
    ).encode("utf-8")
    return {"baseline_bytes": baseline, "subject_input_bytes": captures["subject_capture"].data,
            "carrier_bytes": captures["carrier_capture"].data,
            "packet_sources": [("sha256:" + p.sha256, p.data) for p in captures["packet_captures"]],
            "extent_bytes": captures["extent_capture"].data if captures["extent_capture"] else None,
            "repository_root": captures["repository_root"]}


def check_runtime_source_replay(report: dict[str, Any], inputs: dict[str, Any] | None) -> list[str]:
    if "runtime_binding" not in report:
        if report.get("record_status") == "observed" and report.get("analysis_boundary", {}).get("analysis_level") == "runtime_observed":
            return ["runtime_binding_required_for_observed_report"]
        return []
    if inputs is None:
        return ["runtime_source_inputs_required"]
    try:
        root = Path(__file__).resolve().parents[1]
        binding = report["runtime_binding"]
        if binding["profile"] != RUNTIME_REPORT_PROFILE:
            raise ValueError("runtime_report_profile_invalid")
        construction = binding["construction"]
        # Pins are checked before executing the protected replay implementation.
        core = _runtime_module(root / "tools/pulsemech_compute_binding_analyzer_core_v0.py", "runtime_core_for_check", expected_sha256=construction["analyzer_sha256"])
        bridge_path = root / "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py"
        bridge = _runtime_module(bridge_path, "runtime_bridge_source_for_check", expected_sha256=construction["entrypoint_sha256"])
        schema_cap = bridge.capture_regular_file(root / "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json", label="runtime_schema", max_bytes=1024 * 1024)
        validator_cap = bridge.capture_regular_file(root / "tools/check_pulsemech_compute_runtime_observation_packet_v0.py", label="runtime_validator", max_bytes=8 * 1024 * 1024)
        validator = bridge.load_module_from_capture(validator_cap, "unchanged_runtime_packet_validator_for_report")
        baseline_view = RuntimeBytesView(inputs["baseline_bytes"], "artifact-baseline")
        report_schema = bridge.capture_regular_file(root / "schemas/pulsemech_compute_binding_report_v0.schema.json", label="report_schema", max_bytes=1024 * 1024)
        baseline_diag, baseline_rc = build_diagnostic(bridge.CapturedPathView(report_schema), baseline_view)
        if baseline_rc != 0:
            raise ValueError("runtime_baseline_validation_failed")
        if report["record_status"] == "observed":
            repository_root = inputs.get("repository_root")
            if not isinstance(repository_root, Path):
                raise ValueError("runtime_historical_source_repository_required")
            def captured(data: bytes, label: str) -> Any:
                return bridge.CapturedFile(path=repository_root / label, data=data, device=0, inode=0,
                                           size_bytes=len(data), sha256=_runtime_hash(data))
            # Reconstruct the artifact baseline through the existing source-aware
            # bridge. Supplying a plausible B plus its hash cannot bypass S/C/Git.
            reconstructed = bridge.build_from_captured_inputs(
                packet_capture=captured(inputs["subject_input_bytes"], "captured-subject-input.json"),
                carrier_capture=captured(inputs["carrier_bytes"], "captured-carrier.zip"),
                repository_root=repository_root,
                analysis_run_key=report["analysis_boundary"]["analysis_run_key"],
            ).encode("utf-8")
            if reconstructed != inputs["baseline_bytes"]:
                raise ValueError("runtime_artifact_baseline_reconstruction_mismatch")
        if not inputs["packet_sources"] or len(inputs["packet_sources"]) > 128:
            raise ValueError("runtime_packet_count_invalid")
        if sum(len(raw) for _, raw in inputs["packet_sources"]) > 64 * 1024 * 1024:
            raise ValueError("runtime_packet_total_too_large")
        sources = []
        for locator, raw in inputs["packet_sources"]:
            if type(raw) is not bytes or len(raw) > 8 * 1024 * 1024:
                raise ValueError("runtime_packet_bytes_invalid")
            cap = bridge.CapturedFile(path=Path(locator), data=raw, device=0, inode=0, size_bytes=len(raw), sha256=_runtime_hash(raw))
            diagnostic, rc = validator.build_diagnostic(schema_path=bridge.CapturedPathView(schema_cap), packet_path=bridge.CapturedPathView(cap))
            if rc != 0 or diagnostic.get("ok") is not True:
                raise ValueError("runtime_packet_strict_validation_failed")
            sources.append(core.RuntimePacketSource(locator, raw))
        expected = core.build_runtime_report(
            baseline_bytes=inputs["baseline_bytes"], subject_input_bytes=inputs["subject_input_bytes"],
            carrier_bytes=inputs["carrier_bytes"], packet_sources=sources,
            entrypoint_sha256=construction["entrypoint_sha256"], analyzer_sha256=construction["analyzer_sha256"],
            extent_bytes=inputs.get("extent_bytes"),
        )
        if report != expected:
            return ["runtime_source_replay_mismatch"]
        # Independent checks: exact baseline preservation and one representation
        # per runtime occurrence. Replay equality alone is not the only check.
        baseline = json.loads(inputs["baseline_bytes"])
        for key, id_key in (("compute_nodes", "node_id"), ("state_nodes", "state_id")):
            original = [row for row in report[key] if "runtime_origin" not in row]
            if original != baseline[key]:
                raise ValueError("runtime_baseline_graph_changed:" + key)
            ids = [row["runtime_origin"]["record_id"] for row in report[key] if "runtime_origin" in row]
            if len(ids) != len(set(ids)):
                raise ValueError("runtime_occurrence_count_duplicated")
        origins = binding["edge_origins"]
        base_edges = [e for e in report["edges"] if origins[e["edge_id"]]["evidence_kind"] == "artifact_observed"]
        if base_edges != baseline["edges"]:
            raise ValueError("runtime_baseline_edges_changed")
        if report["resource_summary"] != baseline["resource_summary"]:
            raise ValueError("runtime_resource_measurement_invented")
        if report["record_status"] == "observed" and binding["coverage"]["extent_status"] == "complete":
            raise ValueError("runtime_observed_extent_unsupported")
        return []
    except Exception as exc:
        return ["runtime_source_validation_failed:" + str(exc)]


if __name__ == "__main__":
    raise SystemExit(main())
