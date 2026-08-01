#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
from referencing import Registry
from referencing.exceptions import NoSuchResource


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

CANONICAL_EXPECTATION_SCHEMA_GIT_BLOB_SHA1 = (
    "c0bc5a21f5bf46c529341d2e805f26525c70c7f4"
)
CANONICAL_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1 = (
    "e1f982ffaf900c6c17745624d80f9f38b374448b"
)
SCHEMA_REFERENCE_KEYWORDS = frozenset(
    {"$ref", "$dynamicRef", "$recursiveRef"}
)
SCHEMA_REFERENCE_POLICY = "internal_fragment_only"

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

ROLE_BINDING_SCALAR_KEYS = (
    "preservation_manifest",
    "preservation_readme",
    "preservation_checksums",
    "complete_package",
    "package_inventory",
    "package_completeness_report",
    "independent_verification_report",
    "run_metadata",
    "final_status",
    "status_baseline",
    "release_decision",
    "release_authority",
    "artifact_binding",
    "evidence_manifest",
    "recorded_verifier_report",
    "required_gate_evidence",
    "candidate_index",
)

ROLE_BINDING_LIST_KEYS = (
    "candidate_records",
    "external_evidence_records",
    "attestation_records",
    "reader_surfaces",
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


def _strict_descriptor_snapshot_available() -> bool:
    return (
        os.name != "nt"
        and os.open in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _strict_output_descriptor_binding_available() -> bool:
    return (
        _strict_descriptor_snapshot_available()
        and os.rename in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def _input_snapshot_mode() -> str:
    return (
        "posix_descriptor_chain"
        if _strict_descriptor_snapshot_available()
        else "path_identity_fallback"
    )


def _external_output_mode() -> str:
    return (
        "posix_directory_descriptor_atomic_replace"
        if _strict_output_descriptor_binding_available()
        else "path_atomic_replace_fallback"
    )


def _deny_schema_retrieval(uri: str) -> Any:
    raise NoSuchResource(ref=uri)


CLOSED_SCHEMA_REGISTRY = Registry(retrieve=_deny_schema_retrieval)


def _json_pointer(parts: tuple[Any, ...]) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1")
        for part in parts
    )


def schema_reference_policy_errors(
    value: Any,
    *,
    label: str,
    path: tuple[Any, ...] = (),
) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            item = value[key]
            item_path = path + (key,)
            if key in SCHEMA_REFERENCE_KEYWORDS:
                if not isinstance(item, str):
                    errors.append(
                        f"{label}_reference_not_string"
                        f"[{_json_pointer(item_path)}]"
                    )
                elif not item.startswith("#"):
                    errors.append(
                        f"{label}_external_reference_not_permitted"
                        f"[{_json_pointer(item_path)}]: {item!r}"
                    )
            errors.extend(
                schema_reference_policy_errors(
                    item,
                    label=label,
                    path=item_path,
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(
                schema_reference_policy_errors(
                    item,
                    label=label,
                    path=path + (index,),
                )
            )
    return errors


def git_blob_sha1(payload: bytes) -> str:
    encoded = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(encoded, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(encoded).hexdigest()


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _validated_directory_root(path: Path, *, label: str) -> Path:
    candidate = _normalized_absolute_path(path)
    reject_symlink_components(candidate, label=label)
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise SemanticError(f"{label}_unavailable: {candidate}: {exc}") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise SemanticError(f"{label}_not_directory: {candidate}")
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise SemanticError(f"{label}_unresolvable: {candidate}: {exc}") from exc


def _stat_identity(value: os.stat_result) -> tuple[Any, ...]:
    return tuple(
        getattr(value, name, None)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    )


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
            raise SemanticError(
                f"{label}_component_unavailable: {cursor}: {exc}"
            ) from exc

        if stat.S_ISLNK(metadata.st_mode):
            raise SemanticError(f"{label}_symlink_rejected: {cursor}")
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def _open_nofollow_posix(path: Path, *, label: str) -> int:
    candidate = _normalized_absolute_path(path)
    parts = candidate.parts
    if not candidate.is_absolute() or not parts:
        raise SemanticError(f"{label}_path_not_absolute: {candidate}")

    directory_flags = os.O_RDONLY
    directory_flags |= int(getattr(os, "O_DIRECTORY", 0))
    directory_flags |= int(getattr(os, "O_CLOEXEC", 0))
    directory_flags |= int(getattr(os, "O_NOFOLLOW", 0))
    file_flags = os.O_RDONLY
    file_flags |= int(getattr(os, "O_CLOEXEC", 0))
    file_flags |= int(getattr(os, "O_NOFOLLOW", 0))
    file_flags |= int(getattr(os, "O_BINARY", 0))

    current_fd: int | None = None
    try:
        current_fd = os.open(parts[0], directory_flags)
        for part in parts[1:-1]:
            next_fd = os.open(
                part,
                directory_flags,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        if len(parts) == 1:
            raise SemanticError(f"{label}_path_is_root: {candidate}")
        return os.open(parts[-1], file_flags, dir_fd=current_fd)
    except OSError as exc:
        if exc.errno in {
            errno.ELOOP,
            errno.ENOTDIR,
        }:
            raise SemanticError(
                f"{label}_symlink_or_non_directory_component_rejected: "
                f"{candidate}: {exc}"
            ) from exc
        if exc.errno == errno.ENOENT:
            raise SemanticError(f"{label}_missing: {candidate}") from exc
        raise SemanticError(f"{label}_open_failed: {candidate}: {exc}") from exc
    finally:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass


def _open_nofollow_fallback(path: Path, *, label: str) -> int:
    candidate = _normalized_absolute_path(path)
    reject_symlink_components(candidate, label=label)
    try:
        before = candidate.lstat()
    except OSError as exc:
        raise SemanticError(f"{label}_unavailable: {candidate}: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise SemanticError(f"{label}_not_regular_file: {candidate}")

    flags = os.O_RDONLY
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    flags |= int(getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise SemanticError(f"{label}_open_failed: {candidate}: {exc}") from exc

    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _stat_identity(before) != _stat_identity(opened)
        ):
            raise SemanticError(f"{label}_changed_before_read: {candidate}")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _open_nofollow(path: Path, *, label: str) -> int:
    if _strict_descriptor_snapshot_available():
        return _open_nofollow_posix(path, label=label)
    return _open_nofollow_fallback(path, label=label)


def read_regular_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    candidate = _normalized_absolute_path(path)
    descriptor = _open_nofollow(candidate, label=label)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SemanticError(f"{label}_not_regular_file: {candidate}")
        if before.st_size > max_bytes:
            raise SemanticError(
                f"{label}_too_large: size={before.st_size} maximum={max_bytes}"
            )

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise SemanticError(
                    f"{label}_too_large_during_read: "
                    f"size>{max_bytes}"
                )
            chunks.append(chunk)

        after = os.fstat(descriptor)
        if _stat_identity(before) != _stat_identity(after):
            raise SemanticError(f"{label}_changed_during_read: {candidate}")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise SemanticError(
                f"{label}_size_changed_during_read: "
                f"expected={before.st_size} actual={len(payload)}"
            )
        return payload
    except OSError as exc:
        raise SemanticError(f"{label}_read_failed: {candidate}: {exc}") from exc
    finally:
        os.close(descriptor)


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


def validate_instance(
    schema: dict[str, Any],
    value: Any,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    reference_errors = schema_reference_policy_errors(
        schema,
        label=f"{label}_schema",
    )
    if reference_errors:
        return False, reference_errors

    try:
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
            registry=CLOSED_SCHEMA_REGISTRY,
        )
        validation_errors = sorted(
            list(validator.iter_errors(value)),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    except Exception as exc:
        detail = " ".join(str(exc).split())
        return False, [
            f"{label}_validation_failed: {type(exc).__name__}: {detail}"
        ]

    errors = [
        f"{label}_error[{list(error.path)}]: {error.message}"
        for error in validation_errors
    ]
    return not errors, errors


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


def _canonical_component_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    if value.startswith("/") or value.endswith("/") or "\x00" in value:
        return None
    pure = PurePosixPath(value)
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    canonical = pure.as_posix()
    return canonical if canonical == value else None


def _subject_input_observed_witness(
    expectation: dict[str, Any],
    *,
    packet_contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    subject = copy.deepcopy(expectation.get("subject", {}))
    authority_sources = copy.deepcopy(
        expectation.get("authority_sources", {})
    )
    carrier = expectation.get("carrier", {})
    identity = expectation.get("expectation_identity", {})
    components = expectation.get("trusted_control_plane", {}).get(
        "components",
        {},
    )
    producer_component = (
        components.get("subject_input_producer_wrapper", {})
        if isinstance(components, dict)
        else {}
    )
    layout = expectation.get("archive_layout", {})
    visible = layout.get("visible_members", {})

    artifact_id = "artifact:current-run-export-compatibility-probe/manifest"
    manifest_name = (
        visible.get("preservation_manifest_name")
        if isinstance(visible, dict)
        else None
    ) or "PRESERVATION_MANIFEST_v0.json"
    root_prefix = carrier.get("root_prefix") or "current-run-export-probe/"
    member_path = f"{root_prefix}{manifest_name}"

    role_bindings: dict[str, Any] = {
        key: None for key in ROLE_BINDING_SCALAR_KEYS
    }
    role_bindings["preservation_manifest"] = artifact_id
    role_bindings.update({key: [] for key in ROLE_BINDING_LIST_KEYS})

    missing_roles = sorted(
        key
        for key in ROLE_BINDING_SCALAR_KEYS
        if key != "preservation_manifest"
    ) + list(ROLE_BINDING_LIST_KEYS)

    producer_version = producer_component.get("version")
    if not isinstance(producer_version, str):
        producer_version = "0.1.0"

    return {
        "analysis_boundary": {
            "current_repository_state_substitution_allowed": False,
            "observer_in_subject_totals": False,
            "packet_is_compute_report": False,
            "packet_is_runtime_observation": False,
            "runtime_observation_included": False,
            "runtime_observation_required_for_runtime_classification": True,
            "target_analysis_level": "artifact_observed",
        },
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "container_artifact_id": None,
                "container_path_verified": True,
                "content_kind": "json",
                "digest_verified": True,
                "display_path_or_uri": (
                    f"{carrier.get('staged_relative_path', 'carrier.zip')}!/{member_path}"
                ),
                "media_type": "application/json",
                "member_path": member_path,
                "provider_binding": None,
                "required_for_analysis": True,
                "role": "preservation_manifest",
                "sha256": hashlib.sha256(
                    b"current-run-export-compatibility-probe"
                ).hexdigest(),
                "size_bytes": 1,
                "size_verified": True,
            }
        ],
        "authority_boundary": {
            "activates_compute_gate": False,
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "changes_release_authority": False,
            "creates_compute_budget": False,
            "creates_gate_result": False,
            "creates_release_decision": False,
            "mutates_carrier": False,
            "packet_is_release_authority": False,
            "write_mode": "subject_input_only",
            "writes_subject_run": False,
            "writes_target_repository": False,
        },
        "authority_sources": authority_sources,
        "carrier": {
            "artifact_payload_mode": "external_carrier",
            "carrier_id": carrier.get("carrier_id"),
            "carrier_kind": "current_run_export_archive",
            "immutable": True,
            "media_type": "application/zip",
            "path_or_uri": carrier.get(
                "staged_relative_path",
                "current-run-export-probe.zip",
            ),
            "provider_binding": copy.deepcopy(
                carrier.get("provider_binding")
            ),
            "root_prefix": carrier.get("root_prefix"),
            "sha256": carrier.get("sha256"),
            "size_bytes": carrier.get("size_bytes"),
        },
        "content_boundary": {
            "artifact_bytes_embedded": False,
            "carrier_required_for_verification": True,
            "packet_payload_mode": "metadata_only",
            "raw_model_inputs_included": False,
            "raw_model_outputs_included": False,
            "raw_secrets_included": False,
        },
        "coverage": {
            "artifact_graph_complete": False,
            "artifacts_total": 1,
            "carrier_binding_complete": True,
            "coverage_status": "partial",
            "missing_roles": missing_roles,
            "provider_artifacts_bound": 0,
            "provider_artifacts_total": 0,
            "role_bindings_complete": False,
            "role_bindings_resolved": 1,
            "role_bindings_total": (
                len(ROLE_BINDING_SCALAR_KEYS)
                + len(ROLE_BINDING_LIST_KEYS)
            ),
            "source_bindings_complete": True,
            "unresolved_artifact_ids": [],
        },
        "errors": [],
        "ok": True,
        "packet_identity": {
            "canonicalization": "json-sort-keys-utf8-newline",
            "carrier_id": carrier.get("carrier_id"),
            "packet_created_utc": identity.get("expectation_created_utc"),
            "packet_id": "subject-input:current-run-export-compatibility-probe",
            "packet_scope": "current_run",
            "subject_run_key": subject.get("subject_run_key"),
        },
        "packet_type": packet_contract.get("packet_type"),
        "producer": {
            "ci_workflow_or_job_identity": (
                "current-run-export-cross-contract-probe"
            ),
            "producer_id": "producer:current-run-export-cross-contract-probe",
            "producer_name": "PULSEmech current-run export cross-contract probe",
            "producer_run_key": subject.get("subject_run_key"),
            "producer_source": profile.get("expected_producer_source_path"),
            "producer_source_revision": producer_component.get(
                "source_revision"
            ),
            "producer_source_sha256": producer_component.get("sha256"),
            "producer_version": producer_version,
            "production_mode": "current_run_export",
        },
        "record_status": "observed",
        "role_bindings": role_bindings,
        "schema_version": packet_contract.get("schema_version"),
        "subject": subject,
    }


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
    expectation: dict[str, Any],
    expectation_schema: dict[str, Any],
    subject_input_schema: dict[str, Any],
    packet_contract: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[bool, list[str], bool]:
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

    witness = _subject_input_observed_witness(
        expectation,
        packet_contract=packet_contract,
        profile=profile,
    )
    witness_valid, witness_errors = validate_instance(
        subject_input_schema,
        witness,
        label="subject_input_observed_branch_witness",
    )
    errors.extend(witness_errors)

    return not errors, errors, witness_valid


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
    canonical_component_paths = [
        _canonical_component_path(path) for path in component_paths
    ]
    component_paths_canonical_ok = all(
        path is not None for path in canonical_component_paths
    )
    record(
        "control_plane_component_paths_canonical_ok",
        component_paths_canonical_ok,
    )
    record(
        "control_plane_component_paths_unique_ok",
        component_paths_canonical_ok
        and len(canonical_component_paths)
        == len(set(canonical_component_paths)),
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

    carrier_id = carrier.get("carrier_id")
    carrier_prefix = (
        f"carrier:{profile.get('expected_carrier_id_namespace')}/"
    )
    carrier_suffix = (
        carrier_id[len(carrier_prefix):]
        if isinstance(carrier_id, str)
        and carrier_id.startswith(carrier_prefix)
        else None
    )
    record(
        "carrier_id_namespace_binding_ok",
        isinstance(carrier_suffix, str)
        and bool(carrier_suffix)
        and _canonical_component_path(carrier_suffix) is not None,
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

    (
        cross_contract_ok,
        cross_contract_errors,
        observed_branch_witness_ok,
    ) = _subject_input_cross_contract(
        expectation=expectation,
        expectation_schema=expectation_schema,
        subject_input_schema=subject_input_schema,
        packet_contract=packet_contract,
        profile=profile,
    )
    record(
        "subject_input_observed_branch_witness_ok",
        observed_branch_witness_ok,
        " | ".join(cross_contract_errors) or None,
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
    expectation_instance_valid: bool = False,
    subject_input_observed_branch_valid: bool = False,
    expectation_schema_reference_policy_valid: bool = False,
    subject_input_schema_reference_policy_valid: bool = False,
    canonical_expectation_schema_path_verified: bool = False,
    canonical_expectation_schema_git_blob_verified: bool = False,
    canonical_subject_input_schema_path_verified: bool = False,
    canonical_subject_input_schema_git_blob_verified: bool = False,
    supplied_contract_semantics_verified: bool = False,
) -> dict[str, Any]:
    canonical_contract_semantics_verified = bool(
        supplied_contract_semantics_verified
        and canonical_expectation_schema_path_verified
        and canonical_expectation_schema_git_blob_verified
        and canonical_subject_input_schema_path_verified
        and canonical_subject_input_schema_git_blob_verified
    )
    return {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "document_type": DOCUMENT_TYPE,
        "record_status": record_status,
        "ok": ok,
        "expectation_schema_valid": expectation_schema_valid,
        "expectation_schema_reference_policy_valid": (
            expectation_schema_reference_policy_valid
        ),
        "expectation_instance_valid": expectation_instance_valid,
        "subject_input_schema_valid": subject_input_schema_valid,
        "subject_input_schema_reference_policy_valid": (
            subject_input_schema_reference_policy_valid
        ),
        "subject_input_observed_branch_valid": (
            subject_input_observed_branch_valid
        ),
        "checks": dict(sorted(checks.items())),
        "derived": dict(sorted(derived.items())),
        "input_identities": dict(sorted(input_identities.items())),
        "verification_boundary": {
            "canonical_contract_semantics_verified": (
                canonical_contract_semantics_verified
            ),
            "canonical_expectation_schema_git_blob_verified": (
                canonical_expectation_schema_git_blob_verified
            ),
            "canonical_expectation_schema_path_verified": (
                canonical_expectation_schema_path_verified
            ),
            "canonical_subject_input_schema_git_blob_verified": (
                canonical_subject_input_schema_git_blob_verified
            ),
            "canonical_subject_input_schema_path_verified": (
                canonical_subject_input_schema_path_verified
            ),
            "carrier_bytes_verified": False,
            "contract_semantics_verified": (
                canonical_contract_semantics_verified
            ),
            "control_plane_component_bytes_verified": False,
            "external_output_mode": _external_output_mode(),
            "external_schema_retrieval_allowed": False,
            "input_snapshot_mode": _input_snapshot_mode(),
            "schema_reference_policy": SCHEMA_REFERENCE_POLICY,
            "strict_descriptor_snapshot_verified": (
                _strict_descriptor_snapshot_available()
            ),
            "strict_output_descriptor_binding_available": (
                _strict_output_descriptor_binding_available()
            ),
            "subject_authority_source_bytes_verified": False,
            "supplied_contract_semantics_verified": (
                supplied_contract_semantics_verified
            ),
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
    values: dict[str, Any] = {}
    texts: dict[str, str] = {}
    payloads: dict[str, bytes] = {}
    errors: list[str] = []
    read_failure = False

    input_specs = (
        (
            "expectation_schema",
            schema_path,
            MAX_EXPECTATION_SCHEMA_BYTES,
        ),
        (
            "subject_input_schema",
            subject_input_schema_path,
            MAX_SUBJECT_INPUT_SCHEMA_BYTES,
        ),
        (
            "expectation",
            expectation_path,
            MAX_EXPECTATION_BYTES,
        ),
    )
    for label, path, maximum in input_specs:
        try:
            value, text_value, payload = load_json(
                path,
                label=label,
                max_bytes=maximum,
            )
            values[label] = value
            texts[label] = text_value
            payloads[label] = payload
        except Exception as exc:
            read_failure = True
            detail = " ".join(str(exc).split())
            errors.append(
                f"read_error: {label}: {type(exc).__name__}: {detail}"
            )

    expectation_schema = values.get("expectation_schema")
    subject_input_schema = values.get("subject_input_schema")
    expectation = values.get("expectation")
    expectation_text = texts.get("expectation", "")
    schema_bytes = payloads.get("expectation_schema")
    packet_schema_bytes = payloads.get("subject_input_schema")
    expectation_bytes = payloads.get("expectation")

    canonical_expectation_schema_path_verified = bool(
        schema_bytes is not None
        and same_target(schema_path, DEFAULT_SCHEMA)
    )
    canonical_subject_input_schema_path_verified = bool(
        packet_schema_bytes is not None
        and same_target(
            subject_input_schema_path,
            DEFAULT_SUBJECT_INPUT_SCHEMA,
        )
    )

    expectation_schema_git_blob = (
        git_blob_sha1(schema_bytes) if schema_bytes is not None else None
    )
    subject_input_schema_git_blob = (
        git_blob_sha1(packet_schema_bytes)
        if packet_schema_bytes is not None
        else None
    )
    canonical_expectation_schema_git_blob_verified = (
        expectation_schema_git_blob
        == CANONICAL_EXPECTATION_SCHEMA_GIT_BLOB_SHA1
    )
    canonical_subject_input_schema_git_blob_verified = (
        subject_input_schema_git_blob
        == CANONICAL_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1
    )

    input_identities: dict[str, Any] = {}
    if expectation_bytes is not None:
        input_identities["expectation"] = {
            "sha256": hashlib.sha256(expectation_bytes).hexdigest(),
            "size_bytes": len(expectation_bytes),
        }
    if schema_bytes is not None:
        input_identities["expectation_schema"] = {
            "git_blob_sha1": expectation_schema_git_blob,
            "reviewed_git_blob_sha1": (
                CANONICAL_EXPECTATION_SCHEMA_GIT_BLOB_SHA1
            ),
            "sha256": hashlib.sha256(schema_bytes).hexdigest(),
            "size_bytes": len(schema_bytes),
        }
    if packet_schema_bytes is not None:
        input_identities["subject_input_schema"] = {
            "git_blob_sha1": subject_input_schema_git_blob,
            "reviewed_git_blob_sha1": (
                CANONICAL_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1
            ),
            "sha256": hashlib.sha256(packet_schema_bytes).hexdigest(),
            "size_bytes": len(packet_schema_bytes),
        }

    expectation_schema_is_object = isinstance(expectation_schema, dict)
    subject_input_schema_is_object = isinstance(subject_input_schema, dict)
    expectation_is_object = isinstance(expectation, dict)

    expectation_schema_reference_errors: list[str] = []
    subject_input_schema_reference_errors: list[str] = []
    expectation_schema_errors: list[str] = []
    subject_input_schema_errors: list[str] = []

    if "expectation_schema" in values:
        if not expectation_schema_is_object:
            expectation_schema_errors.append("expectation_schema_not_object")
        else:
            expectation_schema_reference_errors = (
                schema_reference_policy_errors(
                    expectation_schema,
                    label="expectation_schema",
                )
            )
            try:
                jsonschema.Draft202012Validator.check_schema(
                    expectation_schema
                )
            except Exception as exc:
                detail = " ".join(str(exc).split())
                expectation_schema_errors.append(
                    "expectation_schema_invalid: "
                    f"{type(exc).__name__}: {detail}"
                )

    if "subject_input_schema" in values:
        if not subject_input_schema_is_object:
            subject_input_schema_errors.append(
                "subject_input_schema_not_object"
            )
        else:
            subject_input_schema_reference_errors = (
                schema_reference_policy_errors(
                    subject_input_schema,
                    label="subject_input_schema",
                )
            )
            try:
                jsonschema.Draft202012Validator.check_schema(
                    subject_input_schema
                )
            except Exception as exc:
                detail = " ".join(str(exc).split())
                subject_input_schema_errors.append(
                    "subject_input_schema_invalid: "
                    f"{type(exc).__name__}: {detail}"
                )

    expectation_schema_valid = bool(
        expectation_schema_is_object and not expectation_schema_errors
    )
    subject_input_schema_valid = bool(
        subject_input_schema_is_object and not subject_input_schema_errors
    )
    expectation_schema_reference_policy_valid = bool(
        expectation_schema_is_object
        and not expectation_schema_reference_errors
    )
    subject_input_schema_reference_policy_valid = bool(
        subject_input_schema_is_object
        and not subject_input_schema_reference_errors
    )

    errors.extend(expectation_schema_errors)
    errors.extend(subject_input_schema_errors)
    errors.extend(expectation_schema_reference_errors)
    errors.extend(subject_input_schema_reference_errors)

    expectation_instance_valid = False
    if (
        expectation_schema_valid
        and expectation_schema_reference_policy_valid
        and "expectation" in values
    ):
        expectation_instance_valid, instance_errors = validate_instance(
            expectation_schema,
            expectation,
            label="expectation_instance",
        )
        errors.extend(instance_errors)

    if "expectation" in values and not expectation_is_object:
        errors.append("expectation_not_object")

    checks: dict[str, bool] = {}
    derived: dict[str, Any] = {}
    subject_input_observed_branch_valid = False
    if (
        expectation_is_object
        and expectation_instance_valid
        and subject_input_schema_valid
        and subject_input_schema_reference_policy_valid
    ):
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
        subject_input_observed_branch_valid = bool(
            checks.get("subject_input_observed_branch_witness_ok")
        )
    else:
        checks[
            "semantic_checks_skipped_due_to_invalid_contract_inputs"
        ] = False

    ok = (
        not read_failure
        and expectation_schema_valid
        and expectation_schema_reference_policy_valid
        and expectation_instance_valid
        and subject_input_schema_valid
        and subject_input_schema_reference_policy_valid
        and subject_input_observed_branch_valid
        and bool(checks)
        and all(checks.values())
        and not errors
    )
    diagnostic = make_diagnostic(
        ok=ok,
        expectation_schema_valid=expectation_schema_valid,
        expectation_schema_reference_policy_valid=(
            expectation_schema_reference_policy_valid
        ),
        expectation_instance_valid=expectation_instance_valid,
        subject_input_schema_valid=subject_input_schema_valid,
        subject_input_schema_reference_policy_valid=(
            subject_input_schema_reference_policy_valid
        ),
        subject_input_observed_branch_valid=(
            subject_input_observed_branch_valid
        ),
        canonical_expectation_schema_path_verified=(
            canonical_expectation_schema_path_verified
        ),
        canonical_subject_input_schema_path_verified=(
            canonical_subject_input_schema_path_verified
        ),
        canonical_expectation_schema_git_blob_verified=(
            canonical_expectation_schema_git_blob_verified
        ),
        canonical_subject_input_schema_git_blob_verified=(
            canonical_subject_input_schema_git_blob_verified
        ),
        supplied_contract_semantics_verified=ok,
        record_status=(
            expectation.get("record_status")
            if expectation_is_object
            else None
        ),
        checks=checks,
        derived=derived,
        input_identities=input_identities,
        errors=errors,
    )

    structural_failure = (
        read_failure
        or (
            "expectation_schema" in values
            and not expectation_schema_is_object
        )
        or (
            "subject_input_schema" in values
            and not subject_input_schema_is_object
        )
    )
    return diagnostic, 0 if ok else (2 if structural_failure else 1)


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        pass
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def reject_unsafe_output(
    output: Path | None,
    *,
    schema_path: Path,
    expectation_path: Path,
    subject_input_schema_path: Path,
    repository_roots: tuple[Path, ...],
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
        resolved_candidate = candidate.resolve(strict=False)
    except OSError as exc:
        raise SemanticError(
            f"output_path_unresolvable: {candidate}: {exc}"
        ) from exc

    for repository_root in repository_roots:
        try:
            resolved_candidate.relative_to(repository_root)
        except ValueError:
            continue
        raise SemanticError(
            f"refusing_output_inside_repository: {resolved_candidate}"
        )


def _open_or_create_directory_posix(path: Path, *, label: str) -> int:
    candidate = _normalized_absolute_path(path)
    parts = candidate.parts
    if not candidate.is_absolute() or not parts:
        raise SemanticError(f"{label}_path_not_absolute: {candidate}")

    flags = os.O_RDONLY
    flags |= int(getattr(os, "O_DIRECTORY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))

    current_fd: int | None = None
    try:
        current_fd = os.open(parts[0], flags)
        for part in parts[1:]:
            try:
                next_fd = os.open(part, flags, dir_fd=current_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        if current_fd is None:
            raise SemanticError(f"{label}_open_failed: {candidate}")
        result = current_fd
        current_fd = None
        return result
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise SemanticError(
                f"{label}_symlink_or_non_directory_component_rejected: "
                f"{candidate}: {exc}"
            ) from exc
        raise SemanticError(f"{label}_open_failed: {candidate}: {exc}") from exc
    finally:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise SemanticError("output_write_returned_zero")
        offset += written


def _atomic_write_posix(path: Path, payload: bytes) -> None:
    candidate = _normalized_absolute_path(path)
    if not candidate.name or candidate.name in {".", ".."}:
        raise SemanticError(f"output_leaf_name_invalid: {candidate}")
    parent_fd = _open_or_create_directory_posix(
        candidate.parent,
        label="output_parent",
    )
    temp_name = f".{candidate.name}.{secrets.token_hex(16)}.tmp"
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        flags |= int(getattr(os, "O_NOFOLLOW", 0))
        flags |= int(getattr(os, "O_BINARY", 0))
        descriptor = os.open(
            temp_name,
            flags,
            0o600,
            dir_fd=parent_fd,
        )
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(
            temp_name,
            candidate.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        finally:
            os.close(parent_fd)


def _atomic_write_fallback(path: Path, text: str) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(parent, label="output_parent")
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
        reject_symlink_components(parent, label="output_parent")
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def atomic_write(path: Path, text: str) -> None:
    candidate = _normalized_absolute_path(path)
    payload = text.encode("utf-8")
    if _strict_output_descriptor_binding_available():
        _atomic_write_posix(candidate, payload)
        return
    _atomic_write_fallback(candidate, text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a PULSEmech current-run export expectation v0 against "
            "its Draft 2020-12 schema, semantic cross-bindings, and the "
            "existing subject-input packet contract under an "
            "internal-fragment-only schema-reference policy."
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
    repository_root_argument = Path(args.repository_root)
    output = Path(args.output) if args.output else None

    try:
        repository_root = _validated_directory_root(
            repository_root_argument,
            label="repository_root",
        )
        validator_repository_root = _validated_directory_root(
            ROOT,
            label="validator_repository_root",
        )
        reject_unsafe_output(
            output,
            schema_path=schema_path,
            expectation_path=expectation_path,
            subject_input_schema_path=subject_input_schema_path,
            repository_roots=tuple(
                dict.fromkeys(
                    (validator_repository_root, repository_root)
                )
            ),
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
            failure = copy.deepcopy(diagnostic)
            failure["ok"] = False
            failure["errors"] = sorted(
                set(
                    list(failure.get("errors", []))
                    + [f"output_write_failed: {exc}"]
                )
            )
            sys.stderr.write(render_json(failure))
            return 2

    sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
