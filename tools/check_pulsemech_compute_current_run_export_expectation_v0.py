#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


TOOL_NAME = "check_pulsemech_compute_current_run_export_expectation_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_current_run_export_expectation_v0"
DOCUMENT_TYPE = "pulsemech_compute_current_run_export_expectation"
SUBJECT_INPUT_SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
SUBJECT_INPUT_PACKET_TYPE = "pulsemech_compute_subject_input_packet"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_current_run_export_expectation_v0.schema.json"
)
DEFAULT_EXPECTATION = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_current_run_export_expectation_example_v0.json"
)
DEFAULT_SUBJECT_INPUT_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_subject_input_packet_v0.schema.json"
)

EXPECTATION_SCHEMA_PATH = (
    "schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json"
)
EXPECTATION_VALIDATOR_PATH = (
    "tools/check_pulsemech_compute_current_run_export_expectation_v0.py"
)
SUBJECT_INPUT_SCHEMA_PATH = (
    "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
)
SUBJECT_INPUT_VALIDATOR_PATH = (
    "tools/check_pulsemech_compute_subject_input_packet_v0.py"
)
SUBJECT_INPUT_PRODUCER_CORE_PATH = (
    "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py"
)

CONTROL_PLANE_COMPONENT_KEYS = (
    "carrier_loader",
    "control_plane_workflow",
    "expectation_builder",
    "expectation_schema",
    "expectation_validator",
    "subject_input_producer_core",
    "subject_input_producer_wrapper",
    "subject_input_schema",
    "subject_input_validator",
)

CLOSED_CONTENT_BOUNDARY = {
    "consumer_must_verify_carrier_bytes": True,
    "contains_artifact_payloads": False,
    "contains_resource_measurement": False,
    "contains_runtime_observation": False,
    "contains_secret_material": False,
    "expectation_payload_mode": "metadata_only",
}

CLOSED_AUTHORITY_BOUNDARY = {
    "activates_compute_gate": False,
    "changes_gate_policy": False,
    "changes_gate_semantics": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "expectation_is_release_authority": False,
    "mutates_carrier": False,
    "produced_packet_is_release_authority": False,
    "write_mode": "expectation_only",
    "writes_subject_run": False,
    "writes_target_repository": False,
}

MAX_EXPECTATION_SCHEMA_BYTES = 1024 * 1024
MAX_SUBJECT_INPUT_SCHEMA_BYTES = 1024 * 1024
MAX_EXPECTATION_BYTES = 8 * 1024 * 1024

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulsemech_compute_current_run_export_expectation_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    }
)


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


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def reject_symlink_components(path: Path, *, label: str) -> None:
    cursor = _normalized_absolute_path(path)
    while True:
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            if cursor == _normalized_absolute_path(path):
                raise SemanticError(f"{label}_missing: {cursor}")
            raise SemanticError(f"{label}_parent_missing: {cursor}")
        except OSError as exc:
            raise SemanticError(f"{label}_component_unavailable: {cursor}: {exc}") from exc

        if stat.S_ISLNK(metadata.st_mode):
            raise SemanticError(f"{label}_symlink_rejected: {cursor}")
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def read_regular_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    candidate = _normalized_absolute_path(path)
    reject_symlink_components(candidate, label=label)
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise SemanticError(f"{label}_unavailable: {candidate}: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise SemanticError(f"{label}_not_regular_file: {candidate}")
    if metadata.st_size > max_bytes:
        raise SemanticError(
            f"{label}_too_large: size={metadata.st_size} maximum={max_bytes}"
        )
    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        raise SemanticError(f"{label}_read_failed: {candidate}: {exc}") from exc
    if len(payload) != metadata.st_size:
        raise SemanticError(
            f"{label}_size_changed_during_read: "
            f"expected={metadata.st_size} actual={len(payload)}"
        )
    return payload


def load_json(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> tuple[Any, str, bytes]:
    payload = read_regular_file(path, label=label, max_bytes=max_bytes)
    if payload.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"{label}: UTF-8 BOM is not permitted")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"{label}: invalid UTF-8: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        if isinstance(exc, StrictJsonError):
            raise
        raise StrictJsonError(f"{label}: invalid JSON: {exc}") from exc
    return value, text, payload


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


def _all_object_keys_sorted(value: Any) -> bool:
    if isinstance(value, dict):
        return (
            list(value) == sorted(value)
            and all(_all_object_keys_sorted(item) for item in value.values())
        )
    if isinstance(value, list):
        return all(_all_object_keys_sorted(item) for item in value)
    return True


def _ordered_unique_non_empty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _sorted_unique_non_empty_strings(value: Any) -> bool:
    return (
        _ordered_unique_non_empty_strings(value)
        and value == sorted(value)
    )


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"not canonical UTC: {value!r}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"not UTC: {value!r}")
    return parsed


def _canonical_subject_run_key(subject: dict[str, Any]) -> str:
    return (
        f"GITHUB_RUN_ID={subject.get('workflow_run_id')}"
        f"|GITHUB_RUN_ATTEMPT={subject.get('workflow_run_attempt')}"
        f"|GITHUB_WORKFLOW={subject.get('workflow_name')}"
    )


def _canonical_workflow_ref(subject: dict[str, Any]) -> str:
    return (
        f"{subject.get('repository')}/{subject.get('workflow_path')}"
        f"@{subject.get('source_ref')}"
    )


def _flatten_authority_sources(
    expectation: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    authority_sources = expectation.get("authority_sources", {})
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in ("workflow", "policy", "gate_registry"):
        value = authority_sources.get(name)
        if isinstance(value, dict):
            rows.append((name, value))
    additional = authority_sources.get("additional_sources", [])
    if isinstance(additional, list):
        for index, value in enumerate(additional):
            if isinstance(value, dict):
                rows.append((f"additional_sources[{index}]", value))
    return rows


def _relative_path(path: Path, repository_root: Path) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        root = repository_root.resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
    except (OSError, ValueError):
        return None
    return relative


def _nested_value(value: dict[str, Any], *parts: str) -> Any:
    cursor: Any = value
    for part in parts:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _fullmatch(pattern: Any, value: Any) -> bool:
    return (
        isinstance(pattern, str)
        and isinstance(value, str)
        and re.fullmatch(pattern, value) is not None
    )


def _carrier_digest_key_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(
            (1 if key == "carrier_sha256" else 0)
            + _carrier_digest_key_count(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return sum(_carrier_digest_key_count(item) for item in value)
    return 0


def _provider_binding_ok(
    carrier: dict[str, Any],
) -> tuple[bool, str | None]:
    provider = carrier.get("provider_binding")
    if provider is None:
        return True, None
    if not isinstance(provider, dict):
        return False, "provider_binding_not_object_or_null"

    carrier_sha = carrier.get("sha256")
    carrier_size = carrier.get("size_bytes")
    provider_sha = provider.get("provider_sha256")
    provider_size = provider.get("provider_size_bytes")
    sha_match = provider.get("downloaded_sha256_matches")
    size_match = provider.get("downloaded_size_matches")

    if provider_sha is None:
        if sha_match is not None:
            return False, "provider_sha_absent_but_match_state_present"
    elif provider_sha != carrier_sha or sha_match is not True:
        return False, "provider_sha_binding_mismatch"

    if provider_size is None:
        if size_match is not None:
            return False, "provider_size_absent_but_match_state_present"
    elif provider_size != carrier_size or size_match is not True:
        return False, "provider_size_binding_mismatch"

    try:
        finalized = _parse_utc(carrier.get("finalized_utc"))
        created_value = provider.get("created_utc")
        expires_value = provider.get("expires_utc")
        if created_value is not None and _parse_utc(created_value) > finalized:
            return False, "provider_created_after_carrier_finalization"
        if expires_value is not None and finalized > _parse_utc(expires_value):
            return False, "carrier_finalized_after_provider_expiration"
    except Exception as exc:
        return False, f"provider_time_binding_invalid: {exc}"

    return True, None


def _subject_input_cross_contract(
    *,
    expectation_schema: dict[str, Any],
    subject_input_schema: dict[str, Any],
    packet_contract: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    expected_values = {
        "schema_version": _nested_value(
            subject_input_schema,
            "properties",
            "schema_version",
            "const",
        ),
        "packet_type": _nested_value(
            subject_input_schema,
            "properties",
            "packet_type",
            "const",
        ),
        "record_status": "observed",
        "production_mode": "current_run_export",
        "packet_scope": "current_run",
        "carrier_kind": "current_run_export_archive",
        "artifact_payload_mode": _nested_value(
            subject_input_schema,
            "$defs",
            "carrier",
            "properties",
            "artifact_payload_mode",
            "const",
        ),
        "write_mode": _nested_value(
            subject_input_schema,
            "$defs",
            "authority_boundary",
            "properties",
            "write_mode",
            "const",
        ),
    }
    for field, expected in expected_values.items():
        if packet_contract.get(field) != expected:
            errors.append(
                f"packet_contract_{field}_mismatch: "
                f"expected={expected!r} actual={packet_contract.get(field)!r}"
            )

    record_statuses = _nested_value(
        subject_input_schema,
        "properties",
        "record_status",
        "enum",
    )
    if not isinstance(record_statuses, list) or "observed" not in record_statuses:
        errors.append("observed_status_not_supported_by_subject_input_schema")

    production_modes = _nested_value(
        subject_input_schema,
        "$defs",
        "producer",
        "properties",
        "production_mode",
        "enum",
    )
    if (
        not isinstance(production_modes, list)
        or profile.get("expected_production_mode") not in production_modes
    ):
        errors.append("current_run_export_not_supported_by_subject_input_schema")

    packet_scopes = _nested_value(
        subject_input_schema,
        "$defs",
        "packet_identity",
        "properties",
        "packet_scope",
        "enum",
    )
    if (
        not isinstance(packet_scopes, list)
        or profile.get("expected_packet_scope") not in packet_scopes
    ):
        errors.append("current_run_scope_not_supported_by_subject_input_schema")

    carrier_kinds = _nested_value(
        subject_input_schema,
        "$defs",
        "carrier",
        "properties",
        "carrier_kind",
        "enum",
    )
    if (
        not isinstance(carrier_kinds, list)
        or profile.get("expected_carrier_kind") not in carrier_kinds
    ):
        errors.append("current_run_carrier_kind_not_supported_by_subject_input_schema")

    expectation_source_pattern = _nested_value(
        expectation_schema,
        "$defs",
        "source_id",
        "pattern",
    )
    packet_source_pattern = _nested_value(
        subject_input_schema,
        "$defs",
        "source_id",
        "pattern",
    )
    if expectation_source_pattern != packet_source_pattern:
        errors.append("source_id_pattern_cross_contract_mismatch")

    carrier_pattern = _nested_value(
        subject_input_schema,
        "$defs",
        "carrier_id",
        "pattern",
    )
    derived_carrier_id = (
        f"carrier:{profile.get('expected_carrier_id_namespace')}/generated-suffix"
    )
    if not _fullmatch(carrier_pattern, derived_carrier_id):
        errors.append(
            f"derived_carrier_id_not_packet_safe: {derived_carrier_id!r}"
        )

    return not errors, errors


def semantic_checks(
    expectation: dict[str, Any],
    *,
    expectation_text: str,
    expectation_path: Path,
    repository_root: Path,
    expectation_schema: dict[str, Any],
    subject_input_schema: dict[str, Any],
) -> tuple[dict[str, bool], list[str], dict[str, Any]]:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def record(name: str, condition: bool, detail: str | None = None) -> None:
        checks[name] = bool(condition)
        if not condition:
            suffix = f": {detail}" if detail else ""
            errors.append(f"check_failed: {name}{suffix}")

    record(
        "schema_version_ok",
        expectation.get("schema_version") == SCHEMA_VERSION,
    )
    record(
        "document_type_ok",
        expectation.get("document_type") == DOCUMENT_TYPE,
    )
    record(
        "canonical_json_key_ordering_ok",
        _all_object_keys_sorted(expectation),
    )
    record(
        "canonical_json_bytes_ok",
        expectation_text == render_json(expectation),
    )

    status = expectation.get("record_status")
    identity = expectation.get("expectation_identity", {})
    fixture = expectation.get("fixture_provenance")
    expectation_producer = expectation.get("expectation_producer")
    subject = expectation.get("subject", {})
    control_plane = expectation.get("trusted_control_plane", {})
    components = control_plane.get("components", {})
    profile = expectation.get("packet_producer_profile", {})
    carrier = expectation.get("carrier", {})
    carrier_producer = carrier.get("producer")
    layout = expectation.get("archive_layout", {})
    sources = expectation.get("authority_sources", {})
    packet_contract = expectation.get("packet_contract", {})

    branch_ok = False
    if status == "example":
        branch_ok = (
            isinstance(fixture, dict)
            and expectation_producer is None
            and identity.get("expectation_scope") == "example"
            and carrier.get("carrier_kind") == "example_archive"
            and carrier_producer is None
            and fixture.get("expectation_producer_execution_claimed") is False
        )
    elif status == "observed":
        branch_ok = (
            fixture is None
            and isinstance(expectation_producer, dict)
            and identity.get("expectation_scope") == "current_run_export"
            and carrier.get("carrier_kind") == "current_run_export_archive"
            and isinstance(carrier_producer, dict)
        )
    record("record_status_branch_ok", branch_ok)

    if status == "example" and isinstance(fixture, dict):
        actual_relative = _relative_path(expectation_path, repository_root)
        record(
            "fixture_source_path_binding_ok",
            actual_relative == fixture.get("fixture_source_path"),
            (
                f"declared={fixture.get('fixture_source_path')!r} "
                f"actual={actual_relative!r}"
            ),
        )
        record(
            "fixture_schema_identity_ok",
            fixture.get("schema_identity") == expectation.get("schema_version"),
        )
    else:
        record("fixture_source_path_binding_ok", status == "observed")
        record("fixture_schema_identity_ok", status == "observed")

    canonical_run_key = _canonical_subject_run_key(subject)
    run_keys = (
        identity.get("subject_run_key"),
        subject.get("subject_run_key"),
        profile.get("expected_subject_run_key"),
    )
    record(
        "subject_run_key_binding_ok",
        len(set(run_keys)) == 1 and run_keys[0] is not None,
        repr(run_keys),
    )
    record(
        "subject_run_key_canonical_ok",
        subject.get("subject_run_key") == canonical_run_key,
        f"expected={canonical_run_key!r}",
    )

    expected_workflow_ref = _canonical_workflow_ref(subject)
    record(
        "subject_workflow_ref_ok",
        subject.get("workflow_ref") == expected_workflow_ref,
        f"expected={expected_workflow_ref!r}",
    )

    record(
        "producer_profile_subject_binding_ok",
        profile.get("expected_repository") == subject.get("repository")
        and profile.get("expected_source_commit") == subject.get("source_commit")
        and profile.get("expected_subject_run_key")
        == subject.get("subject_run_key"),
    )
    record(
        "producer_profile_layout_binding_ok",
        profile.get("expected_archive_layout_id") == layout.get("layout_id"),
    )
    record(
        "packet_contract_profile_binding_ok",
        packet_contract.get("production_mode")
        == profile.get("expected_production_mode")
        and packet_contract.get("packet_scope")
        == profile.get("expected_packet_scope")
        and packet_contract.get("carrier_kind")
        == profile.get("expected_carrier_kind")
        and packet_contract.get("artifact_payload_mode")
        == profile.get("expected_carrier_artifact_payload_mode"),
    )

    workflow = sources.get("workflow", {})
    workflow_ok = (
        workflow.get("source_id") == "source:workflow"
        and workflow.get("role") == "workflow"
        and workflow.get("path_or_uri") == subject.get("workflow_path")
        and workflow.get("source_revision") == subject.get("source_commit")
        and workflow.get("workflow_name") == subject.get("workflow_name")
        and workflow.get("workflow_ref") == subject.get("workflow_ref")
    )
    record("workflow_source_binding_ok", workflow_ok)

    policy = sources.get("policy", {})
    policy_ok = (
        policy.get("source_id") == "source:policy"
        and policy.get("role") == "policy"
        and policy.get("source_revision") == subject.get("source_commit")
        and policy.get("policy_id") == subject.get("policy_id")
        and policy.get("sha256") == subject.get("policy_sha256")
    )
    record("policy_source_binding_ok", policy_ok)

    registry = sources.get("gate_registry", {})
    registry_ok = (
        registry.get("source_id") == "source:gate-registry"
        and registry.get("role") == "gate_registry"
        and registry.get("source_revision") == subject.get("source_commit")
    )
    record("gate_registry_source_binding_ok", registry_ok)

    flattened_sources = _flatten_authority_sources(expectation)
    source_ids = [row.get("source_id") for _label, row in flattened_sources]
    record(
        "authority_source_ids_unique_ok",
        all(isinstance(value, str) for value in source_ids)
        and len(source_ids) == len(set(source_ids)),
    )

    expectation_source_pattern = _nested_value(
        expectation_schema,
        "$defs",
        "source_id",
        "pattern",
    )
    record(
        "authority_source_ids_namespace_ok",
        all(_fullmatch(expectation_source_pattern, value) for value in source_ids),
    )

    record(
        "authority_source_revisions_ok",
        all(
            row.get("source_revision") == subject.get("source_commit")
            for _label, row in flattened_sources
        ),
    )

    additional_sources = sources.get("additional_sources", [])
    additional_ids = (
        [row.get("source_id") for row in additional_sources]
        if isinstance(additional_sources, list)
        else []
    )
    record(
        "additional_sources_ordering_ok",
        isinstance(additional_sources, list)
        and additional_ids == sorted(additional_ids),
    )

    signer_rows = [
        row
        for row in additional_sources
        if isinstance(row, dict)
        and row.get("role") == "external_signer_policy"
        and row.get("path_or_uri") == profile.get("expected_signer_policy_path")
    ]
    record(
        "signer_policy_source_binding_ok",
        len(signer_rows) == 1,
        f"matches={len(signer_rows)}",
    )

    component_keys_ok = (
        isinstance(components, dict)
        and tuple(sorted(components)) == CONTROL_PLANE_COMPONENT_KEYS
    )
    record("control_plane_component_set_ok", component_keys_ok)

    component_rows = [
        row for row in components.values() if isinstance(row, dict)
    ] if isinstance(components, dict) else []
    record(
        "control_plane_component_revisions_ok",
        len(component_rows) == len(CONTROL_PLANE_COMPONENT_KEYS)
        and all(
            row.get("source_revision") == control_plane.get("revision")
            for row in component_rows
        ),
    )
    component_paths = [row.get("path") for row in component_rows]
    record(
        "control_plane_component_paths_unique_ok",
        all(isinstance(path, str) for path in component_paths)
        and len(component_paths) == len(set(component_paths)),
    )

    component_path_bindings_ok = (
        isinstance(components, dict)
        and components.get("expectation_schema", {}).get("path")
        == EXPECTATION_SCHEMA_PATH
        and components.get("expectation_validator", {}).get("path")
        == EXPECTATION_VALIDATOR_PATH
        and components.get("subject_input_schema", {}).get("path")
        == SUBJECT_INPUT_SCHEMA_PATH
        and components.get("subject_input_validator", {}).get("path")
        == SUBJECT_INPUT_VALIDATOR_PATH
        and components.get("subject_input_producer_core", {}).get("path")
        == SUBJECT_INPUT_PRODUCER_CORE_PATH
        and components.get("subject_input_producer_wrapper", {}).get("path")
        == profile.get("expected_producer_source_path")
    )
    record(
        "control_plane_component_path_bindings_ok",
        component_path_bindings_ok,
    )

    observed_producer_ok = True
    if status == "observed":
        builder_component = components.get("expectation_builder", {})
        observed_producer_ok = (
            isinstance(expectation_producer, dict)
            and expectation_producer.get("producer_run_key")
            == subject.get("subject_run_key")
            and expectation_producer.get("producer_source")
            == builder_component.get("path")
            and expectation_producer.get("producer_source_revision")
            == builder_component.get("source_revision")
            == control_plane.get("revision")
            and expectation_producer.get("producer_source_sha256")
            == builder_component.get("sha256")
            and expectation_producer.get("producer_version")
            == builder_component.get("version")
            and isinstance(carrier_producer, dict)
            and carrier_producer.get("producer_run_key")
            == subject.get("subject_run_key")
            and carrier_producer.get("producer_source_revision")
            == control_plane.get("revision")
        )
    record("observed_producer_bindings_ok", observed_producer_ok)

    record(
        "carrier_id_namespace_binding_ok",
        isinstance(carrier.get("carrier_id"), str)
        and carrier.get("carrier_id").startswith(
            f"carrier:{profile.get('expected_carrier_id_namespace')}/"
        ),
    )
    record(
        "carrier_layout_binding_ok",
        carrier.get("root_prefix") == layout.get("outer_prefix"),
    )

    try:
        carrier_finalized = _parse_utc(carrier.get("finalized_utc"))
        expectation_created = _parse_utc(identity.get("expectation_created_utc"))
        finalization_order_ok = carrier_finalized <= expectation_created
        finalization_detail = None
    except Exception as exc:
        finalization_order_ok = False
        finalization_detail = str(exc)
    record(
        "carrier_finalization_order_ok",
        finalization_order_ok,
        finalization_detail,
    )

    provider_ok, provider_detail = _provider_binding_ok(carrier)
    record("provider_binding_semantics_ok", provider_ok, provider_detail)

    outer_prefix = layout.get("outer_prefix")
    original_prefix = layout.get("original_artifacts_prefix")
    visible = layout.get("visible_members", {})
    visible_names = list(visible.values()) if isinstance(visible, dict) else []
    package_names = [
        layout.get("complete_package_name"),
        layout.get("completeness_archive_name"),
        layout.get("verification_archive_name"),
    ]
    archive_layout_ok = (
        isinstance(outer_prefix, str)
        and isinstance(original_prefix, str)
        and original_prefix.startswith(outer_prefix)
        and original_prefix != outer_prefix
        and outer_prefix.endswith("/")
        and original_prefix.endswith("/")
        and len(visible_names) == 3
        and len(visible_names) == len(set(visible_names))
        and all(isinstance(value, str) and value for value in package_names)
        and len(package_names) == len(set(package_names))
        and all(str(value).endswith(".zip") for value in package_names)
        and not set(visible_names).intersection(package_names)
    )
    record("archive_layout_semantics_ok", archive_layout_ok)

    provider_count = layout.get("expected_provider_artifact_count")
    non_provider_count = layout.get("expected_non_provider_artifact_count")
    derived_artifact_count = (
        provider_count + non_provider_count
        if isinstance(provider_count, int)
        and isinstance(non_provider_count, int)
        else None
    )
    record(
        "artifact_count_derivation_ok",
        layout.get("artifact_count_derivation") == "provider_plus_non_provider"
        and isinstance(provider_count, int)
        and provider_count >= 1
        and isinstance(non_provider_count, int)
        and non_provider_count >= len(visible_names)
        and "expected_artifact_count" not in layout,
    )

    record(
        "single_authoritative_carrier_digest_ok",
        isinstance(carrier.get("sha256"), str)
        and _carrier_digest_key_count(expectation) == 0,
    )

    cross_contract_ok, cross_contract_errors = _subject_input_cross_contract(
        expectation_schema=expectation_schema,
        subject_input_schema=subject_input_schema,
        packet_contract=packet_contract,
        profile=profile,
    )
    record(
        "subject_input_cross_contract_ok",
        cross_contract_ok,
        " | ".join(cross_contract_errors) or None,
    )

    record(
        "content_boundary_closed_ok",
        expectation.get("content_boundary") == CLOSED_CONTENT_BOUNDARY,
    )
    record(
        "authority_boundary_closed_ok",
        expectation.get("authority_boundary") == CLOSED_AUTHORITY_BOUNDARY,
    )

    errors_field = expectation.get("errors")
    ok_field = expectation.get("ok")
    record(
        "record_errors_ordering_ok",
        _sorted_unique_non_empty_strings(errors_field),
    )
    record(
        "record_ok_errors_semantics_ok",
        isinstance(errors_field, list)
        and (
            (ok_field is True and errors_field == [])
            or (ok_field is False and len(errors_field) > 0)
        ),
    )
    record(
        "active_policy_sets_identity_shape_ok",
        _ordered_unique_non_empty_strings(subject.get("active_policy_sets")),
    )

    derived = {
        "artifact_count": derived_artifact_count,
        "authority_effect": "none",
        "carrier_id_prefix": (
            f"carrier:{profile.get('expected_carrier_id_namespace')}/"
        ),
        "control_plane_component_count": len(component_rows),
        "record_status": status,
        "source_count": len(flattened_sources),
        "subject_run_key": subject.get("subject_run_key"),
        "workflow_ref": subject.get("workflow_ref"),
    }
    return checks, errors, derived


def make_diagnostic(
    *,
    ok: bool,
    expectation_schema_valid: bool,
    subject_input_schema_valid: bool,
    record_status: Any,
    checks: dict[str, bool],
    derived: dict[str, Any],
    input_identities: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "document_type": DOCUMENT_TYPE,
        "record_status": record_status,
        "ok": ok,
        "expectation_schema_valid": expectation_schema_valid,
        "subject_input_schema_valid": subject_input_schema_valid,
        "checks": dict(sorted(checks.items())),
        "derived": dict(sorted(derived.items())),
        "input_identities": dict(sorted(input_identities.items())),
        "verification_boundary": {
            "carrier_bytes_verified": False,
            "control_plane_component_bytes_verified": False,
            "contract_semantics_verified": bool(ok),
            "subject_authority_source_bytes_verified": False,
        },
        "authority_effect": "none",
        "errors": sorted(set(errors)),
    }


def build_diagnostic(
    *,
    schema_path: Path,
    expectation_path: Path,
    subject_input_schema_path: Path,
    repository_root: Path,
) -> tuple[dict[str, Any], int]:
    try:
        expectation_schema, _schema_text, schema_bytes = load_json(
            schema_path,
            label="expectation_schema",
            max_bytes=MAX_EXPECTATION_SCHEMA_BYTES,
        )
        subject_input_schema, _packet_schema_text, packet_schema_bytes = load_json(
            subject_input_schema_path,
            label="subject_input_schema",
            max_bytes=MAX_SUBJECT_INPUT_SCHEMA_BYTES,
        )
        expectation, expectation_text, expectation_bytes = load_json(
            expectation_path,
            label="expectation",
            max_bytes=MAX_EXPECTATION_BYTES,
        )
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            expectation_schema_valid=False,
            subject_input_schema_valid=False,
            record_status=None,
            checks={},
            derived={},
            input_identities={},
            errors=[f"read_error: {exc}"],
        )
        return diagnostic, 2

    input_identities = {
        "expectation": {
            "sha256": hashlib.sha256(expectation_bytes).hexdigest(),
            "size_bytes": len(expectation_bytes),
        },
        "expectation_schema": {
            "sha256": hashlib.sha256(schema_bytes).hexdigest(),
            "size_bytes": len(schema_bytes),
        },
        "subject_input_schema": {
            "sha256": hashlib.sha256(packet_schema_bytes).hexdigest(),
            "size_bytes": len(packet_schema_bytes),
        },
    }

    if not isinstance(expectation_schema, dict):
        diagnostic = make_diagnostic(
            ok=False,
            expectation_schema_valid=False,
            subject_input_schema_valid=False,
            record_status=(
                expectation.get("record_status")
                if isinstance(expectation, dict)
                else None
            ),
            checks={},
            derived={},
            input_identities=input_identities,
            errors=["expectation_schema_not_object"],
        )
        return diagnostic, 2

    if not isinstance(subject_input_schema, dict):
        diagnostic = make_diagnostic(
            ok=False,
            expectation_schema_valid=False,
            subject_input_schema_valid=False,
            record_status=(
                expectation.get("record_status")
                if isinstance(expectation, dict)
                else None
            ),
            checks={},
            derived={},
            input_identities=input_identities,
            errors=["subject_input_schema_not_object"],
        )
        return diagnostic, 2

    expectation_schema_errors: list[str] = []
    subject_input_schema_errors: list[str] = []
    try:
        jsonschema.Draft202012Validator.check_schema(expectation_schema)
    except Exception as exc:
        expectation_schema_errors.append(f"expectation_schema_invalid: {exc}")
    try:
        jsonschema.Draft202012Validator.check_schema(subject_input_schema)
    except Exception as exc:
        subject_input_schema_errors.append(f"subject_input_schema_invalid: {exc}")

    expectation_schema_valid = not expectation_schema_errors
    subject_input_schema_valid = not subject_input_schema_errors
    errors = expectation_schema_errors + subject_input_schema_errors

    if expectation_schema_valid:
        errors.extend(schema_errors(expectation_schema, expectation))
    record_schema_valid = (
        expectation_schema_valid
        and not any(error.startswith("schema_error[") for error in errors)
    )

    if not isinstance(expectation, dict):
        diagnostic = make_diagnostic(
            ok=False,
            expectation_schema_valid=record_schema_valid,
            subject_input_schema_valid=subject_input_schema_valid,
            record_status=None,
            checks={},
            derived={},
            input_identities=input_identities,
            errors=errors + ["expectation_not_object"],
        )
        return diagnostic, 1

    checks: dict[str, bool] = {}
    derived: dict[str, Any] = {}
    if record_schema_valid and subject_input_schema_valid:
        semantic, semantic_errors_list, derived = semantic_checks(
            expectation,
            expectation_text=expectation_text,
            expectation_path=expectation_path,
            repository_root=repository_root,
            expectation_schema=expectation_schema,
            subject_input_schema=subject_input_schema,
        )
        checks.update(semantic)
        errors.extend(semantic_errors_list)
    else:
        checks["semantic_checks_skipped_due_to_schema_errors"] = False

    ok = (
        record_schema_valid
        and subject_input_schema_valid
        and bool(checks)
        and all(checks.values())
        and not errors
    )
    diagnostic = make_diagnostic(
        ok=ok,
        expectation_schema_valid=record_schema_valid,
        subject_input_schema_valid=subject_input_schema_valid,
        record_status=expectation.get("record_status"),
        checks=checks,
        derived=derived,
        input_identities=input_identities,
        errors=errors,
    )
    return diagnostic, 0 if ok else 1


def same_target(left: Path, right: Path) -> bool:
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return False


def reject_unsafe_output(
    output: Path | None,
    *,
    schema_path: Path,
    expectation_path: Path,
    subject_input_schema_path: Path,
    repository_root: Path,
) -> None:
    if output is None:
        return

    for protected in (
        schema_path,
        expectation_path,
        subject_input_schema_path,
        Path(__file__),
    ):
        if same_target(output, protected):
            raise SemanticError(f"refusing_to_overwrite_input: {protected}")

    if output.name in PROTECTED_OUTPUT_NAMES:
        raise SemanticError(
            f"refusing_authority_or_contract_surface_output: {output.name}"
        )

    candidate = _normalized_absolute_path(output)
    cursor = candidate
    while True:
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            metadata = None
        except OSError as exc:
            raise SemanticError(
                f"output_path_component_unavailable: {cursor}: {exc}"
            ) from exc
        if metadata is not None and stat.S_ISLNK(metadata.st_mode):
            raise SemanticError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent

    try:
        candidate.resolve(strict=False).relative_to(
            repository_root.resolve(strict=True)
        )
    except (OSError, ValueError):
        return
    raise SemanticError(f"refusing_output_inside_repository: {candidate}")


def atomic_write(path: Path, text: str) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if not parent.is_dir():
        raise SemanticError(f"output_parent_not_directory: {parent}")

    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(parent),
    )
    temp = Path(raw_temp)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a PULSEmech current-run export expectation v0 against "
            "its Draft 2020-12 schema, semantic cross-bindings, and the "
            "existing subject-input packet contract."
        )
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the current-run export expectation schema.",
    )
    parser.add_argument(
        "--expectation",
        default=str(DEFAULT_EXPECTATION),
        help="Path to the current-run export expectation JSON.",
    )
    parser.add_argument(
        "--subject-input-schema",
        default=str(DEFAULT_SUBJECT_INPUT_SCHEMA),
        help="Path to the downstream subject-input packet schema.",
    )
    parser.add_argument(
        "--repository-root",
        default=str(ROOT),
        help=(
            "Repository root used only for checked-in fixture-path binding "
            "and output non-interference."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional external path for the deterministic diagnostic JSON. "
            "Repository-local output is rejected."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_path = Path(args.schema)
    expectation_path = Path(args.expectation)
    subject_input_schema_path = Path(args.subject_input_schema)
    repository_root = Path(args.repository_root)
    output = Path(args.output) if args.output else None

    try:
        reject_unsafe_output(
            output,
            schema_path=schema_path,
            expectation_path=expectation_path,
            subject_input_schema_path=subject_input_schema_path,
            repository_root=repository_root,
        )
    except SemanticError as exc:
        diagnostic = make_diagnostic(
            ok=False,
            expectation_schema_valid=False,
            subject_input_schema_valid=False,
            record_status=None,
            checks={},
            derived={},
            input_identities={},
            errors=[str(exc)],
        )
        sys.stderr.write(render_json(diagnostic))
        return 2

    diagnostic, exit_code = build_diagnostic(
        schema_path=schema_path,
        expectation_path=expectation_path,
        subject_input_schema_path=subject_input_schema_path,
        repository_root=repository_root,
    )
    rendered = render_json(diagnostic)

    if output is not None:
        try:
            atomic_write(output, rendered)
        except Exception as exc:
            failure = make_diagnostic(
                ok=False,
                expectation_schema_valid=diagnostic.get(
                    "expectation_schema_valid",
                    False,
                ),
                subject_input_schema_valid=diagnostic.get(
                    "subject_input_schema_valid",
                    False,
                ),
                record_status=diagnostic.get("record_status"),
                checks=diagnostic.get("checks", {}),
                derived=diagnostic.get("derived", {}),
                input_identities=diagnostic.get("input_identities", {}),
                errors=list(diagnostic.get("errors", []))
                + [f"output_write_failed: {exc}"],
            )
            sys.stderr.write(render_json(failure))
            return 2

    sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
