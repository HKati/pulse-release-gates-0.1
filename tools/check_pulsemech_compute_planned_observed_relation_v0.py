#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import jsonschema


TOOL_NAME = "check_pulsemech_compute_planned_observed_relation_v0"
SCHEMA_VERSION = "pulsemech_compute_planned_observed_relation_v0"
RELATION_TYPE = "pulsemech_compute_planned_observed_relation"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
DEFAULT_RELATION = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_planned_observed_relation_example_v0.json"
)
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

OPERATION_DIGEST_FIELDS = (
    "action",
    "component_id",
    "reason",
    "source_path",
    "source_sha256",
    "source_size_bytes",
    "target_path",
    "target_state",
)

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

EXPECTATION_KINDS = (
    "planned_presence_only",
    "planned_execution_expected",
    "planned_execution_and_consumption_expected",
)

RELATION_STATUSES = (
    "planned_presence_only",
    "planned_and_observed",
    "planned_but_not_observed",
    "observed_but_not_planned",
    "execution_identity_mismatch",
    "source_digest_mismatch",
    "run_binding_mismatch",
    "declared_role_mismatch",
    "authority_class_mismatch",
    "downstream_consumption_missing",
    "ambiguous_observation_match",
    "unresolved_due_to_coverage",
)

UNRESOLVED_RELATION_STATUSES = {
    "ambiguous_observation_match",
    "unresolved_due_to_coverage",
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


def load_json(path: Path) -> tuple[Any, str]:
    text = path.read_text(encoding="utf-8")
    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    return value, text


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


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    relation_path: Path,
) -> None:
    if output is None:
        return

    protected = (
        schema_path,
        relation_path,
        Path(__file__),
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    )
    for path in protected:
        if same_target(output, path):
            raise SemanticError(f"refusing_to_overwrite_input: {path}")

    if output.name in {
        "status.json",
        "release_decision_v0.json",
        "pulsemech_compute_planned_observed_relation_v0.json",
    }:
        raise SemanticError(
            f"refusing_authority_or_contract_surface_output: {output.name}"
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
        "relation_type": RELATION_TYPE,
        "ok": ok,
        "schema_valid": schema_valid,
        "checks": dict(sorted(checks.items())),
        "errors": sorted(set(errors)),
    }


def _sorted_unique_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(item, str) for item in values)
        and values == sorted(values)
        and len(values) == len(set(values))
    )


def _mapping_keys_sorted(value: Any) -> bool:
    return isinstance(value, dict) and list(value) == sorted(value)


def _all_object_keys_sorted(value: Any) -> bool:
    if isinstance(value, dict):
        return (
            list(value) == sorted(value)
            and all(_all_object_keys_sorted(item) for item in value.values())
        )
    if isinstance(value, list):
        return all(_all_object_keys_sorted(item) for item in value)
    return True


def _incomplete_coverage_result(coverage: dict[str, Any]) -> str:
    fields = (
        "identity_coverage_status",
        "execution_coverage_status",
        "declared_role_coverage_status",
        "authority_coverage_status",
        "downstream_consumption_coverage_status",
    )
    statuses = {coverage.get(field) for field in fields}
    if "unknown" in statuses:
        return "unknown"
    if "partial" in statuses:
        return "partial"
    return "unknown"


def _subject_tuple(value: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        value.get("subject_repository"),
        value.get("subject_run_key"),
        value.get("subject_source_commit"),
        value.get("release_candidate_id"),
    )


def _operation_digest(operation: dict[str, Any]) -> str:
    payload = {
        field: operation.get(field)
        for field in OPERATION_DIGEST_FIELDS
    }
    return sha256_bytes(canonical_json_bytes(payload))


def _source_kind(value: Any) -> Any:
    if value in {"action", "github_action"}:
        return "action"
    return value


def _source_identity_result(
    expected: dict[str, Any],
    observations: list[dict[str, Any]],
) -> str:
    if expected.get("identity_status") == "unknown":
        return "unavailable"
    if not observations:
        return "not_required"

    comparable_fields = (
        "source_path_or_uri",
        "source_revision",
        "source_sha256",
        "action_repository",
        "action_ref",
        "action_commit_sha",
        "container_image_digest",
    )

    results: list[str] = []
    for observation in observations:
        observed = observation.get("source_identity", {})
        expected_kind = _source_kind(expected.get("source_kind"))
        observed_kind = _source_kind(observed.get("source_kind"))
        if expected_kind != observed_kind:
            results.append("mismatch")
            continue

        unavailable = False
        mismatch = False
        for field in comparable_fields:
            expected_value = expected.get(field)
            if expected_value is None:
                continue
            observed_value = observed.get(field)
            if observed_value is None:
                unavailable = True
                continue
            if observed_value != expected_value:
                mismatch = True

        if mismatch:
            results.append("mismatch")
        elif unavailable:
            results.append("unavailable")
        else:
            results.append("match")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def _selector_result(
    selector: dict[str, Any],
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"

    fields = (
        "node_type",
        "workflow_name",
        "job_name",
        "step_name",
        "tool_id",
        "command_sha256",
    )
    expected = {
        field: selector.get(field)
        for field in fields
        if selector.get(field) is not None
    }
    if not expected:
        return "not_required"

    results: list[str] = []
    for observation in observations:
        actual = observation.get("execution_identity", {})
        mismatch = False
        unavailable = False
        for field, expected_value in expected.items():
            actual_value = actual.get(field)
            if actual_value is None:
                unavailable = True
            elif actual_value != expected_value:
                mismatch = True
        if mismatch:
            results.append("mismatch")
        elif unavailable:
            results.append("unavailable")
        else:
            results.append("match")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def _run_binding_result(
    expected_subject: tuple[Any, Any, Any, Any],
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"
    expected_run = expected_subject[1:]
    return (
        "match"
        if all(
            (
                observation.get("subject_run_key"),
                observation.get("subject_source_commit"),
                observation.get("release_candidate_id"),
            )
            == expected_run
            for observation in observations
        )
        else "mismatch"
    )


def _field_match_result(
    expected: Any,
    observations: list[dict[str, Any]],
    field: str,
) -> str:
    if expected is None:
        return "not_required"
    if not observations:
        return "not_required"
    results: list[str] = []
    for observation in observations:
        actual = observation.get(field)
        if actual in {None, "unknown"}:
            results.append("unavailable")
        elif actual == expected:
            results.append("match")
        else:
            results.append("mismatch")

    if "mismatch" in results:
        return "mismatch"
    if "match" in results:
        return "match"
    return "unavailable"


def _downstream_result(
    required: bool,
    observations: list[dict[str, Any]],
) -> str:
    if not observations:
        return "not_required"

    statuses = {
        observation.get("downstream_consumption", {}).get("status")
        for observation in observations
    }
    if "observed" in statuses:
        return "observed"
    if not required:
        return "not_required"
    if "unresolved" in statuses:
        return "unresolved"
    return "not_observed"


def _relation_coverage_result(
    observations: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> str:
    if not observations:
        status = coverage.get("execution_coverage_status")
        if status == "complete":
            return "complete"
        if status == "unknown":
            return "unknown"
        return "partial"

    statuses = {
        observation.get("coverage_status")
        for observation in observations
    }
    if statuses == {"complete"}:
        return "complete"
    if "unknown" in statuses:
        return "unknown"
    return "partial"


def _relation_expected_evaluation(
    *,
    relation_status: str,
    expectation: dict[str, Any] | None,
    observations: list[dict[str, Any]],
    comparison_subject: tuple[Any, Any, Any, Any],
    coverage: dict[str, Any],
) -> dict[str, Any] | None:
    if relation_status == "ambiguous_observation_match":
        return {
            "execution_observation": "unresolved",
            "decisive": False,
        }

    if relation_status == "unresolved_due_to_coverage":
        return {
            "execution_observation": "unresolved",
            "coverage": _incomplete_coverage_result(coverage),
            "decisive": False,
        }

    if relation_status == "observed_but_not_planned":
        run_result = _run_binding_result(comparison_subject, observations)
        coverage_result = _relation_coverage_result(observations, coverage)
        return {
            "execution_observation": "observed",
            "execution_identity": "not_required",
            "source_identity": "not_required",
            "run_binding": run_result,
            "declared_role": "not_required",
            "authority_class": "not_required",
            "downstream_consumption": "not_required",
            "coverage": coverage_result,
            "decisive": coverage_result == "complete" and run_result == "match",
        }

    if expectation is None:
        return None

    kind = expectation.get("expectation_kind")
    if kind == "planned_presence_only":
        return {
            "execution_observation": "not_required",
            "execution_identity": "not_required",
            "source_identity": "not_required",
            "run_binding": "not_required",
            "declared_role": "not_required",
            "authority_class": "not_required",
            "downstream_consumption": "not_required",
            "coverage": "complete",
            "decisive": True,
        }

    if not observations:
        if coverage.get("execution_coverage_status") == "complete":
            return {
                "execution_observation": "not_observed",
                "execution_identity": "not_required",
                "source_identity": "not_required",
                "run_binding": "not_required",
                "declared_role": "not_required",
                "authority_class": "not_required",
                "downstream_consumption": "not_required",
                "coverage": "complete",
                "decisive": True,
            }
        return {
            "execution_observation": "unresolved",
            "coverage": _incomplete_coverage_result(coverage),
            "decisive": False,
        }

    scope = expectation.get("expectation_scope", {})
    expected_subject = (
        comparison_subject
        if scope.get("scope_kind") != "subject_run"
        else (
            comparison_subject[0],
            scope.get("subject_run_key"),
            scope.get("subject_source_commit"),
            scope.get("release_candidate_id"),
        )
    )
    expected_compute = expectation.get("expected_compute", {})
    coverage_result = _relation_coverage_result(observations, coverage)
    result = {
        "execution_observation": "observed",
        "execution_identity": _selector_result(
            expected_compute.get("selector", {}),
            observations,
        ),
        "source_identity": _source_identity_result(
            expectation.get("expected_source_identity", {}),
            observations,
        ),
        "run_binding": _run_binding_result(expected_subject, observations),
        "declared_role": _field_match_result(
            expectation.get("expected_declared_role"),
            observations,
            "declared_role",
        ),
        "authority_class": _field_match_result(
            expectation.get("expected_mutation_authority"),
            observations,
            "mutation_authority",
        ),
        "downstream_consumption": _downstream_result(
            bool(expected_compute.get("downstream_consumption_required")),
            observations,
        ),
        "coverage": coverage_result,
    }
    result["decisive"] = (
        coverage_result == "complete"
        and result["execution_identity"] != "unavailable"
        and result["source_identity"] != "unavailable"
        and result["run_binding"] != "unavailable"
        and result["declared_role"] != "unavailable"
        and result["authority_class"] != "unavailable"
        and result["downstream_consumption"] != "unresolved"
    )
    return result


def _string_lists(
    relation: dict[str, Any],
) -> Iterable[tuple[str, Any]]:
    coverage = relation.get("coverage", {})
    yield "errors", relation.get("errors")
    for field in (
        "missing_plan_operation_refs",
        "unclassified_expectation_ids",
        "unclassified_observation_ids",
        "unresolved_reasons",
    ):
        yield f"coverage.{field}", coverage.get(field)

    for expectation_id, expectation in relation.get("expectations", {}).items():
        yield f"expectations.{expectation_id}.evidence_refs", expectation.get(
            "evidence_refs"
        )
        for basis in expectation.get("basis_records", []):
            basis_id = basis.get("basis_id", "<invalid>")
            yield (
                f"expectations.{expectation_id}.basis_records.{basis_id}.supports",
                basis.get("supports"),
            )
            yield (
                f"expectations.{expectation_id}.basis_records.{basis_id}.evidence_refs",
                basis.get("evidence_refs"),
            )

    for observation_id, observation in relation.get("observations", {}).items():
        for field in (
            "input_state_ids",
            "output_state_ids",
            "evidence_refs",
            "observed_mutation_classes",
        ):
            yield f"observations.{observation_id}.{field}", observation.get(field)
        downstream = observation.get("downstream_consumption", {})
        for field in ("consumer_ids", "edge_ids", "evidence_refs"):
            yield (
                f"observations.{observation_id}.downstream_consumption.{field}",
                downstream.get(field),
            )

    for relation_id, record in relation.get("relations", {}).items():
        yield f"relations.{relation_id}.observation_ids", record.get(
            "observation_ids"
        )
        yield f"relations.{relation_id}.evidence_refs", record.get("evidence_refs")

    for finding_id, finding in relation.get("findings", {}).items():
        yield f"findings.{finding_id}.observation_ids", finding.get(
            "observation_ids"
        )
        yield f"findings.{finding_id}.evidence_refs", finding.get("evidence_refs")


def semantic_checks(
    relation: dict[str, Any],
    *,
    relation_text: str,
) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def record(name: str, condition: bool, detail: str | None = None) -> None:
        checks[name] = bool(condition)
        if not condition:
            suffix = f": {detail}" if detail else ""
            errors.append(f"check_failed: {name}{suffix}")

    record(
        "schema_version_ok",
        relation.get("schema_version") == SCHEMA_VERSION,
    )
    record(
        "relation_type_ok",
        relation.get("relation_type") == RELATION_TYPE,
    )
    record(
        "canonical_json_key_ordering_ok",
        _all_object_keys_sorted(relation),
    )
    record(
        "canonical_json_newline_termination_ok",
        relation_text.endswith("\n") and not relation_text.endswith("\n\n"),
    )

    expectations = relation.get("expectations", {})
    observations = relation.get("observations", {})
    relations = relation.get("relations", {})
    findings = relation.get("findings", {})
    coverage = relation.get("coverage", {})
    summary = relation.get("summary", {})
    identity = relation.get("comparison_identity", {})
    plan = relation.get("plan_binding", {})
    bindings = relation.get("observation_bindings", {})
    report = bindings.get("compute_binding_report", {})
    packets = bindings.get("runtime_observation_packets", [])
    boundary = relation.get("comparison_boundary", {})

    maps_ok = all(
        isinstance(value, dict)
        for value in (expectations, observations, relations, findings)
    )
    record("identifier_keyed_record_maps_ok", maps_ok)
    if not maps_ok:
        return checks, errors

    record(
        "record_map_ordering_ok",
        all(
            _mapping_keys_sorted(value)
            for value in (expectations, observations, relations, findings)
        ),
    )

    string_list_failures = [
        label
        for label, values in _string_lists(relation)
        if not _sorted_unique_strings(values)
    ]
    record(
        "deterministic_string_list_ordering_ok",
        not string_list_failures,
        ", ".join(string_list_failures[:8]) or None,
    )

    nested_ordering_ok = True
    basis_ids_ok = True
    operation_digest_ok = True
    operation_identity_ok = True
    operation_by_digest: dict[str, dict[str, Any]] = {}
    referenced_operation_digests: set[str] = set()

    for expectation_id, expectation in expectations.items():
        basis_records = expectation.get("basis_records", [])
        basis_ids = [basis.get("basis_id") for basis in basis_records]
        if basis_ids != sorted(basis_ids) or len(basis_ids) != len(set(basis_ids)):
            nested_ordering_ok = False
            basis_ids_ok = False

        operation_refs = expectation.get("plan_operation_refs", [])
        operation_keys = [
            (
                operation.get("component_id"),
                operation.get("target_path"),
                operation.get("operation_sha256"),
            )
            for operation in operation_refs
        ]
        if operation_keys != sorted(operation_keys):
            nested_ordering_ok = False

        component_id = expectation.get("component_id")
        for operation in operation_refs:
            digest = operation.get("operation_sha256")
            if digest != _operation_digest(operation):
                operation_digest_ok = False
            if operation.get("component_id") != component_id:
                operation_identity_ok = False
            if isinstance(digest, str):
                referenced_operation_digests.add(digest)
                existing = operation_by_digest.get(digest)
                if existing is None:
                    operation_by_digest[digest] = operation
                elif existing != operation:
                    operation_identity_ok = False

        integration_basis_digests = {
            basis.get("source_sha256")
            for basis in basis_records
            if basis.get("basis_kind") == "integration_plan_operation"
        }
        operation_digests = {
            operation.get("operation_sha256")
            for operation in operation_refs
        }
        if not integration_basis_digests.issubset(operation_digests):
            operation_identity_ok = False

    packet_keys = [
        (
            packet.get("packet_sequence"),
            packet.get("packet_id"),
            packet.get("sha256"),
        )
        for packet in packets
    ]
    if packet_keys != sorted(packet_keys):
        nested_ordering_ok = False

    record("nested_record_ordering_ok", nested_ordering_ok)
    record("basis_identifiers_unique_within_expectation", basis_ids_ok)
    record("plan_operation_digests_recompute", operation_digest_ok)
    record("plan_operation_identity_consistent", operation_identity_ok)

    subject = _subject_tuple(identity)
    report_subject_ok = _subject_tuple(report) == subject
    record("compute_report_subject_binding_ok", report_subject_ok)

    packet_ids = [packet.get("packet_id") for packet in packets]
    packet_bindings_ok = (
        len(packet_ids) == len(set(packet_ids))
        and all(_subject_tuple(packet) == subject for packet in packets)
    )
    record("runtime_packet_subject_bindings_ok", packet_bindings_ok)

    plan_target_matches = plan.get("target_repository_id") == identity.get(
        "subject_repository"
    )
    record(
        "plan_target_subject_binding_ok",
        plan_target_matches
        and boundary.get("plan_target_matches_subject_repository")
        is plan_target_matches,
    )

    report_level = report.get("analysis_level")
    runtime_status = bindings.get("runtime_observation_status")
    runtime_observations = [
        observation
        for observation in observations.values()
        if observation.get("source_record_kind") == "runtime_observation_packet"
        or observation.get("observation_kind")
        in {"runtime_execution", "external_call", "model_inference"}
    ]
    runtime_semantics_ok = (
        boundary.get("observed_analysis_level") == report_level
        and coverage.get("runtime_observation_status") == runtime_status
    )
    if report_level == "artifact_observed":
        runtime_semantics_ok = runtime_semantics_ok and (
            runtime_status == "none"
            and packets == []
            and runtime_observations == []
        )
    elif report_level == "runtime_observed":
        runtime_semantics_ok = runtime_semantics_ok and (
            runtime_status in {"partial", "complete"}
            and len(packets) > 0
        )
    else:
        runtime_semantics_ok = False
    record("analysis_level_and_runtime_admission_ok", runtime_semantics_ok)

    expectation_scope_ok = True
    expectation_basis_ok = True
    for expectation in expectations.values():
        scope = expectation.get("expectation_scope", {})
        if scope.get("scope_kind") == "subject_run":
            scoped_subject = (
                identity.get("subject_repository"),
                scope.get("subject_run_key"),
                scope.get("subject_source_commit"),
                scope.get("release_candidate_id"),
            )
            if scoped_subject != subject:
                expectation_scope_ok = False

        for basis in expectation.get("basis_records", []):
            basis_run_key = basis.get("subject_run_key")
            if basis_run_key is not None and basis_run_key != identity.get(
                "subject_run_key"
            ):
                expectation_basis_ok = False

    record("expectation_subject_scope_bindings_ok", expectation_scope_ok)
    record("expectation_basis_run_bindings_ok", expectation_basis_ok)

    observer_boundary_ok = True
    unbound_authority_flags_ok = True
    for observation in observations.values():
        scope = observation.get("execution_scope")
        role = observation.get("declared_role")
        binding_class = observation.get("binding_class")
        mutation_authority = observation.get("mutation_authority")
        mutation_classes = set(observation.get("observed_mutation_classes", []))

        if scope in {"analysis_observer", "observation_collector"}:
            if (
                role != "observer"
                or binding_class != "observer"
                or mutation_authority
                not in {"none", "advisory_output", "preservation_output"}
                or bool(mutation_classes & AUTHORITATIVE_MUTATION_CLASSES)
            ):
                observer_boundary_ok = False
        elif scope == "subject" and (
            role == "observer" or binding_class == "observer"
        ):
            observer_boundary_ok = False

        expected_unbound_authority = (
            binding_class == "unbound"
            and bool(mutation_classes & AUTHORITATIVE_MUTATION_CLASSES)
        )
        if observation.get("unbound_authoritative_mutation") is not (
            expected_unbound_authority
        ):
            unbound_authority_flags_ok = False

    record("observer_boundary_ok", observer_boundary_ok)
    record("unbound_authority_flags_derived_ok", unbound_authority_flags_ok)

    expectation_ref_counter: Counter[str] = Counter()
    observation_ref_counter: Counter[str] = Counter()
    relation_references_ok = True
    relation_candidates: set[tuple[Any, tuple[Any, ...]]] = set()
    relation_candidates_unique = True
    relation_evaluations_ok = True
    relation_kind_compatibility_ok = True

    for relation_id, relation_record in relations.items():
        expectation_id = relation_record.get("expectation_id")
        observation_ids = relation_record.get("observation_ids", [])
        relation_status = relation_record.get("relation_status")

        expectation: dict[str, Any] | None = None
        if expectation_id is not None:
            expectation_ref_counter[expectation_id] += 1
            expectation = expectations.get(expectation_id)
            if expectation is None:
                relation_references_ok = False

        selected_observations: list[dict[str, Any]] = []
        for observation_id in observation_ids:
            observation_ref_counter[observation_id] += 1
            observation = observations.get(observation_id)
            if observation is None:
                relation_references_ok = False
            else:
                selected_observations.append(observation)

        candidate = (expectation_id, tuple(observation_ids))
        if candidate in relation_candidates:
            relation_candidates_unique = False
        relation_candidates.add(candidate)

        if expectation is not None:
            kind = expectation.get("expectation_kind")
            if relation_status == "planned_presence_only":
                relation_kind_compatibility_ok &= kind == "planned_presence_only"
            elif relation_status in set(RELATION_STATUSES) - {"planned_presence_only"}:
                relation_kind_compatibility_ok &= kind != "planned_presence_only"

        expected_evaluation = _relation_expected_evaluation(
            relation_status=str(relation_status),
            expectation=expectation,
            observations=selected_observations,
            comparison_subject=subject,
            coverage=coverage,
        )
        actual_evaluation = relation_record.get("evaluation", {})
        if expected_evaluation is None:
            relation_evaluations_ok = False
        else:
            for field, expected_value in expected_evaluation.items():
                if actual_evaluation.get(field) != expected_value:
                    relation_evaluations_ok = False

        if relation_status == "planned_but_not_observed" and (
            coverage.get("execution_coverage_status") != "complete"
        ):
            relation_evaluations_ok = False
        if relation_status == "downstream_consumption_missing" and (
            coverage.get("downstream_consumption_coverage_status")
            != "complete"
        ):
            relation_evaluations_ok = False
        if relation_status == "unresolved_due_to_coverage":
            incomplete_axes = {
                coverage.get(field)
                for field in (
                    "identity_coverage_status",
                    "execution_coverage_status",
                    "declared_role_coverage_status",
                    "authority_coverage_status",
                    "downstream_consumption_coverage_status",
                )
            }
            if not incomplete_axes.intersection({"partial", "unknown"}):
                relation_evaluations_ok = False

    record("relation_references_resolve", relation_references_ok)
    record("relation_candidates_unique", relation_candidates_unique)
    record("relation_expectation_kind_compatibility_ok", relation_kind_compatibility_ok)
    record("relation_evaluations_recompute", relation_evaluations_ok)

    expectation_multiplicity_ok = all(
        count <= 1 for count in expectation_ref_counter.values()
    )
    observation_multiplicity_ok = all(
        count <= 1 for count in observation_ref_counter.values()
    )
    record("expectation_relation_multiplicity_ok", expectation_multiplicity_ok)
    record("observation_relation_multiplicity_ok", observation_multiplicity_ok)

    classified_expectations = set(expectation_ref_counter) & set(expectations)
    classified_observations = set(observation_ref_counter) & set(observations)
    unclassified_expectations = sorted(set(expectations) - classified_expectations)
    unclassified_observations = sorted(set(observations) - classified_observations)

    referenced_operation_count = len(referenced_operation_digests)
    total_operations = plan.get("operation_count")
    missing_operation_count = (
        total_operations - referenced_operation_count
        if isinstance(total_operations, int)
        else -1
    )

    coverage_counts_ok = (
        coverage.get("plan_operations_total") == total_operations
        and coverage.get("plan_operations_referenced")
        == referenced_operation_count
        and missing_operation_count >= 0
        and len(coverage.get("missing_plan_operation_refs", []))
        == missing_operation_count
        and coverage.get("expectations_total") == len(expectations)
        and coverage.get("expectations_classified")
        == len(classified_expectations)
        and coverage.get("unclassified_expectation_ids")
        == unclassified_expectations
        and coverage.get("observations_total") == len(observations)
        and coverage.get("observations_classified")
        == len(classified_observations)
        and coverage.get("unclassified_observation_ids")
        == unclassified_observations
        and coverage.get("relations_total") == len(relations)
    )
    record("coverage_counts_recompute", coverage_counts_ok)

    relation_status_counts = Counter(
        record_value.get("relation_status")
        for record_value in relations.values()
    )
    expectation_kind_counts = Counter(
        record_value.get("expectation_kind")
        for record_value in expectations.values()
    )
    decisive_count = sum(
        1
        for record_value in relations.values()
        if record_value.get("evaluation", {}).get("decisive") is True
    )
    unresolved_count = sum(
        1
        for record_value in relations.values()
        if record_value.get("evaluation", {}).get("decisive") is False
    )
    authority_findings = sum(
        1
        for finding in findings.values()
        if finding.get("severity") == "authority_integrity_candidate"
    )

    summary_counts_ok = (
        summary.get("plan_operations") == total_operations
        and summary.get("expectations") == len(expectations)
        and summary.get("observations") == len(observations)
        and summary.get("relations") == len(relations)
        and all(
            summary.get(kind) == expectation_kind_counts.get(kind, 0)
            for kind in EXPECTATION_KINDS
        )
        and all(
            summary.get(status) == relation_status_counts.get(status, 0)
            for status in RELATION_STATUSES
        )
        and summary.get("decisive_relations") == decisive_count
        and summary.get("unresolved_relations") == unresolved_count
        and summary.get("authority_integrity_candidate_count")
        == authority_findings
    )
    record("summary_counts_recompute", summary_counts_ok)

    finding_references_ok = True
    finding_fingerprints: set[tuple[Any, ...]] = set()
    finding_fingerprints_unique = True
    for finding in findings.values():
        expectation_id = finding.get("expectation_id")
        relation_id = finding.get("relation_id")
        observation_ids = finding.get("observation_ids", [])
        if expectation_id is not None and expectation_id not in expectations:
            finding_references_ok = False
        if relation_id is not None and relation_id not in relations:
            finding_references_ok = False
        if any(observation_id not in observations for observation_id in observation_ids):
            finding_references_ok = False

        fingerprint = (
            finding.get("finding_type"),
            finding.get("severity"),
            expectation_id,
            relation_id,
            tuple(observation_ids),
        )
        if fingerprint in finding_fingerprints:
            finding_fingerprints_unique = False
        finding_fingerprints.add(fingerprint)

    record("finding_references_resolve", finding_references_ok)
    record("finding_fingerprints_unique", finding_fingerprints_unique)

    authority_findings_cover_flags = True
    for observation_id, observation in observations.items():
        if observation.get("unbound_authoritative_mutation") is not True:
            continue
        covered = any(
            finding.get("severity") == "authority_integrity_candidate"
            and observation_id in finding.get("observation_ids", [])
            for finding in findings.values()
        )
        if not covered:
            authority_findings_cover_flags = False
    record(
        "unbound_authority_findings_present",
        authority_findings_cover_flags,
    )

    complete_conditions = (
        coverage.get("missing_plan_operation_refs") == []
        and unclassified_expectations == []
        and unclassified_observations == []
        and coverage.get("unresolved_reasons") == []
        and all(
            coverage.get(field) in {"complete", "not_required"}
            for field in (
                "identity_coverage_status",
                "execution_coverage_status",
                "declared_role_coverage_status",
                "authority_coverage_status",
                "downstream_consumption_coverage_status",
            )
        )
        and unresolved_count == 0
        and relation_status_counts.get("ambiguous_observation_match", 0) == 0
        and relation_status_counts.get("unresolved_due_to_coverage", 0) == 0
    )
    comparison_complete_expected = (
        coverage.get("comparison_status") == "complete"
        and complete_conditions
    )
    record(
        "comparison_complete_semantics_ok",
        summary.get("comparison_complete") is comparison_complete_expected,
    )

    if coverage.get("comparison_status") == "complete":
        coverage_status_ok = complete_conditions
    elif coverage.get("comparison_status") in {"partial", "unknown"}:
        coverage_status_ok = not complete_conditions
    else:
        coverage_status_ok = False
    record("coverage_status_semantics_ok", coverage_status_ok)

    errors_field = relation.get("errors")
    ok_field = relation.get("ok")
    record_ok_semantics = (
        isinstance(errors_field, list)
        and (
            (ok_field is True and errors_field == [])
            or (ok_field is False and len(errors_field) > 0)
        )
    )
    record("record_ok_errors_semantics_ok", record_ok_semantics)

    return checks, errors


def build_diagnostic(
    *,
    schema_path: Path,
    relation_path: Path,
) -> tuple[dict[str, Any], int]:
    try:
        schema, _schema_text = load_json(schema_path)
        relation, relation_text = load_json(relation_path)
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

    errors = schema_errors(schema, relation)
    schema_valid = not errors

    if not isinstance(relation, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["relation_not_object"],
        )
        return diagnostic, 1

    checks: dict[str, bool] = {}
    if schema_valid:
        semantic, semantic_errors_list = semantic_checks(
            relation,
            relation_text=relation_text,
        )
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
            "Validate a PULSEmech compute planned-observed relation v0 "
            "against its strict JSON Schema and semantic contract."
        )
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the planned-observed relation schema.",
    )
    parser.add_argument(
        "--relation",
        default=str(DEFAULT_RELATION),
        help="Path to the planned-observed relation JSON.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the deterministic diagnostic JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_path = Path(args.schema)
    relation_path = Path(args.relation)
    output = Path(args.output) if args.output else None

    try:
        reject_unsafe_output(
            output,
            schema_path=schema_path,
            relation_path=relation_path,
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
        relation_path=relation_path,
    )
    rendered = render_json(diagnostic)
    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
