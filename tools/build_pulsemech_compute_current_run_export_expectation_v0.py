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
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

import jsonschema
import yaml


TOOL_NAME = "build_pulsemech_compute_current_run_export_expectation_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_current_run_export_expectation_v0"
DOCUMENT_TYPE = "pulsemech_compute_current_run_export_expectation"

# The current-run expectation producer v0 belongs to the protected Linux
# execution profile used by the PULSEmech HPC and Linux CI control plane.
#
# Windows is not a target platform, compatibility target, or fallback execution
# path for this producer. A different operating-system substrate requires a
# separate producer identity, implementation, and mechanical trust proof.
SUPPORTED_EXECUTION_PLATFORM = "linux"
SUPPORTED_OS_NAME = "posix"
EXECUTION_PROFILE = "protected_linux_hpc_control_plane"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTATION_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_current_run_export_expectation_v0.schema.json"
)
DEFAULT_EXPECTATION_VALIDATOR = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_current_run_export_expectation_v0.py"
)
DEFAULT_SUBJECT_INPUT_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_subject_input_packet_v0.schema.json"
)

EXPECTATION_BUILDER_PATH = (
    "tools/build_pulsemech_compute_current_run_export_expectation_v0.py"
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
SUBJECT_INPUT_PRODUCER_WRAPPER_PATH = (
    "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py"
)
SUBJECT_INPUT_PRODUCER_CORE_PATH = (
    "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
CURRENT_RUN_CARRIER_LOADER_PATH = (
    "tools/load_pulsemech_compute_current_run_export_carrier_v0.py"
)
CONTROL_PLANE_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)
STATUS_SCHEMA_PATH = "schemas/status/status_v1.schema.json"
RELEASE_DECISION_SCHEMA_PATH = "schemas/release_decision_v0.schema.json"
POLICY_PATH = "pulse_gate_policy_v0.yml"
GATE_REGISTRY_PATH = "pulse_gate_registry_v0.yml"
EXTERNAL_SIGNER_POLICY_PATH = "policy/external_signers_v1.yml"
MATERIALIZED_GATE_SET_SCHEMA = "pulse_ref_materialized_gate_sets_v0"

RELEASE_DECISION_SCHEMA = "pulse_release_decision_v0"
RELEASE_DECISION_VERSION = "0.1.0"
RELEASE_DECISION_PRODUCER_NAME = "materialize_release_decision.py"

STUB_FLAG_PATHS = (
    "diagnostics.gates_stubbed",
    "metrics.gates_stubbed",
    "meta.diagnostics.gates_stubbed",
)
SCAFFOLD_FLAG_PATHS = (
    "diagnostics.scaffold",
    "metrics.scaffold",
    "meta.diagnostics.scaffold",
)
STUB_PROFILE_PATHS = (
    "diagnostics.stub_profile",
    "metrics.stub_profile",
    "meta.diagnostics.stub_profile",
)
NEUTRAL_STUB_PROFILES = {
    "",
    "none",
    "false",
    "real",
    "not_stubbed",
}
_MISSING = object()

# This is the contract-complete protected component set, not an inventory of
# files already present in the repository revision that introduces this builder.
# The carrier loader, current-run packet wrapper, and candidate workflow are
# deliberate activation prerequisites. Their absence must keep observed
# expectation production fail closed; weakening this set would allow an
# incomplete control plane to claim protected_exact_revision.
CONTROL_PLANE_COMPONENT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("carrier_loader", CURRENT_RUN_CARRIER_LOADER_PATH, "0.1.0"),
    ("control_plane_workflow", CONTROL_PLANE_WORKFLOW_PATH, "0.1.0"),
    ("expectation_builder", EXPECTATION_BUILDER_PATH, TOOL_VERSION),
    ("expectation_schema", EXPECTATION_SCHEMA_PATH, "0"),
    ("expectation_validator", EXPECTATION_VALIDATOR_PATH, "0.1.0"),
    ("subject_input_producer_core", SUBJECT_INPUT_PRODUCER_CORE_PATH, "0.1.0"),
    (
        "subject_input_producer_wrapper",
        SUBJECT_INPUT_PRODUCER_WRAPPER_PATH,
        "0.1.0",
    ),
    ("subject_input_schema", SUBJECT_INPUT_SCHEMA_PATH, "0"),
    ("subject_input_validator", SUBJECT_INPUT_VALIDATOR_PATH, "0.1.0"),
)

EXPECTATION_PRODUCER_ID = (
    "producer:pulsemech-current-run-export-expectation-builder-v0"
)
EXPECTATION_PRODUCER_NAME = (
    "PULSEmech current-run export expectation builder"
)

PACKET_CONTRACT = {
    "artifact_payload_mode": "external_carrier",
    "carrier_kind": "current_run_export_archive",
    "packet_scope": "current_run",
    "packet_type": "pulsemech_compute_subject_input_packet",
    "production_mode": "current_run_export",
    "record_status": "observed",
    "schema_version": "pulsemech_compute_subject_input_packet_v0",
    "write_mode": "subject_input_only",
}

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

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_SCHEMA_BYTES = 2 * 1024 * 1024
MAX_COMPONENT_BYTES = 32 * 1024 * 1024
MAX_AUTHORITY_ARTIFACT_BYTES = 64 * 1024 * 1024

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_decision_v0.schema.json",
        "release_authority_v0.json",
        "pulse_gate_policy_v0.yml",
        "pulse_gate_registry_v0.yml",
        "status_v1.schema.json",
        "pulsemech_compute_current_run_export_expectation_v0.schema.json",
        "pulsemech_compute_subject_input_packet_v0.json",
        "pulsemech_compute_subject_input_packet_v0.schema.json",
    }
)
PROTECTED_OUTPUT_NAMES_CASEFOLDED = frozenset(
    name.casefold() for name in PROTECTED_OUTPUT_NAMES
)


LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES = (
    Path("/usr/bin/git"),
    Path("/usr/local/bin/git"),
)

GIT_ENV_ALLOWLIST = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TEMP",
    "TMP",
    "TMPDIR",
)


class BuilderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_kind: str = "build_error",
        exit_code: int = 1,
    ) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.exit_code = exit_code


class StrictJsonError(ValueError):
    pass


class StrictYamlError(ValueError):
    pass


def _require_supported_execution_platform() -> None:
    if (
        sys.platform != SUPPORTED_EXECUTION_PLATFORM
        or os.name != SUPPORTED_OS_NAME
    ):
        raise BuilderError(
            "unsupported_execution_platform: "
            f"profile={EXECUTION_PROFILE!r} "
            f"required_sys_platform={SUPPORTED_EXECUTION_PLATFORM!r} "
            f"required_os_name={SUPPORTED_OS_NAME!r} "
            f"observed_sys_platform={sys.platform!r} "
            f"observed_os_name={os.name!r}",
            exit_kind="platform_boundary_error",
            exit_code=2,
        )


class _StrictSafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_yaml_mapping(
    loader: _StrictSafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as exc:
            raise StrictYamlError(
                f"unhashable YAML mapping key: {key!r}"
            ) from exc
        if key in result:
            raise StrictYamlError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_yaml_mapping,
)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def render_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


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


def _strict_descriptor_snapshot_available() -> bool:
    return (
        os.open in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _strict_output_descriptor_binding_available() -> bool:
    return (
        _strict_descriptor_snapshot_available()
        and os.rename in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def reject_symlink_components(path: Path, *, label: str) -> None:
    cursor = _normalized_absolute_path(path)
    while True:
        try:
            metadata = cursor.lstat()
        except FileNotFoundError as exc:
            raise BuilderError(
                f"{label}_component_missing: {cursor}",
                exit_kind="input_boundary_error",
                exit_code=2,
            ) from exc
        except OSError as exc:
            raise BuilderError(
                f"{label}_component_unavailable: {cursor}: {exc}",
                exit_kind="input_boundary_error",
                exit_code=2,
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise BuilderError(
                f"{label}_symlink_rejected: {cursor}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def _open_nofollow_posix(path: Path, *, label: str) -> int:
    candidate = _normalized_absolute_path(path)
    parts = candidate.parts
    if not candidate.is_absolute() or not parts:
        raise BuilderError(
            f"{label}_path_not_absolute: {candidate}",
            exit_kind="input_boundary_error",
            exit_code=2,
        )

    directory_flags = os.O_RDONLY
    directory_flags |= int(getattr(os, "O_DIRECTORY", 0))
    directory_flags |= int(getattr(os, "O_CLOEXEC", 0))
    directory_flags |= int(getattr(os, "O_NOFOLLOW", 0))
    file_flags = os.O_RDONLY
    file_flags |= int(getattr(os, "O_CLOEXEC", 0))
    file_flags |= int(getattr(os, "O_NOFOLLOW", 0))

    current_fd: int | None = None
    try:
        current_fd = os.open(parts[0], directory_flags)
        for part in parts[1:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        if len(parts) == 1:
            raise BuilderError(
                f"{label}_path_is_root: {candidate}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
        return os.open(parts[-1], file_flags, dir_fd=current_fd)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise BuilderError(
                f"{label}_symlink_or_non_directory_component_rejected: "
                f"{candidate}: {exc}",
                exit_kind="input_boundary_error",
                exit_code=2,
            ) from exc
        if exc.errno == errno.ENOENT:
            raise BuilderError(
                f"{label}_missing: {candidate}",
                exit_kind="input_boundary_error",
                exit_code=2,
            ) from exc
        raise BuilderError(
            f"{label}_open_failed: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc
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
        raise BuilderError(
            f"{label}_unavailable: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc
    if not stat.S_ISREG(before.st_mode):
        raise BuilderError(
            f"{label}_not_regular_file: {candidate}",
            exit_kind="input_boundary_error",
            exit_code=2,
        )

    flags = os.O_RDONLY
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise BuilderError(
            f"{label}_open_failed: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc

    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or _stat_identity(before) != _stat_identity(opened)
        ):
            raise BuilderError(
                f"{label}_changed_before_read: {candidate}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def read_regular_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    candidate = _normalized_absolute_path(path)
    descriptor = (
        _open_nofollow_posix(candidate, label=label)
        if _strict_descriptor_snapshot_available()
        else _open_nofollow_fallback(candidate, label=label)
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BuilderError(
                f"{label}_not_regular_file: {candidate}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
        if before.st_size > max_bytes:
            raise BuilderError(
                f"{label}_too_large: size={before.st_size} maximum={max_bytes}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise BuilderError(
                    f"{label}_too_large_during_read: size>{max_bytes}",
                    exit_kind="input_boundary_error",
                    exit_code=2,
                )
            chunks.append(chunk)

        after = os.fstat(descriptor)
        if _stat_identity(before) != _stat_identity(after):
            raise BuilderError(
                f"{label}_changed_during_read: {candidate}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise BuilderError(
                f"{label}_size_changed_during_read: "
                f"expected={before.st_size} actual={len(payload)}",
                exit_kind="input_boundary_error",
                exit_code=2,
            )
        return payload
    except OSError as exc:
        raise BuilderError(
            f"{label}_read_failed: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc
    finally:
        os.close(descriptor)


def parse_json_bytes(payload: bytes, *, label: str) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise BuilderError(
            f"{label}_utf8_bom_not_permitted",
            exit_kind="strict_json_error",
            exit_code=2,
        )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_invalid_utf8: {exc}",
            exit_kind="strict_json_error",
            exit_code=2,
        ) from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise BuilderError(
            f"{label}_invalid_json: {exc}",
            exit_kind="strict_json_error",
            exit_code=2,
        ) from exc


def parse_yaml_object(payload: bytes, *, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise BuilderError(
            f"{label}_utf8_bom_not_permitted",
            exit_kind="strict_yaml_error",
            exit_code=2,
        )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_invalid_utf8: {exc}",
            exit_kind="strict_yaml_error",
            exit_code=2,
        ) from exc
    try:
        value = yaml.load(text, Loader=_StrictSafeLoader)
    except (yaml.YAMLError, StrictYamlError) as exc:
        raise BuilderError(
            f"{label}_invalid_yaml: {exc}",
            exit_kind="strict_yaml_error",
            exit_code=2,
        ) from exc
    if not isinstance(value, dict):
        raise BuilderError(
            f"{label}_not_object",
            exit_kind="strict_yaml_error",
            exit_code=2,
        )
    return value


def load_json_object(
    path: Path,
    *,
    label: str,
    max_bytes: int,
    canonical_required: bool = False,
) -> tuple[dict[str, Any], bytes]:
    payload = read_regular_file(path, label=label, max_bytes=max_bytes)
    value = parse_json_bytes(payload, label=label)
    if not isinstance(value, dict):
        raise BuilderError(
            f"{label}_not_object",
            exit_kind="strict_json_error",
            exit_code=2,
        )
    if canonical_required and payload != render_json(value):
        raise BuilderError(
            f"{label}_not_canonical_json",
            exit_kind="strict_json_error",
            exit_code=2,
        )
    return value, payload


def _validated_directory_root(path: Path, *, label: str) -> Path:
    candidate = _normalized_absolute_path(path)
    reject_symlink_components(candidate, label=label)
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise BuilderError(
            f"{label}_unavailable: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise BuilderError(
            f"{label}_not_directory: {candidate}",
            exit_kind="input_boundary_error",
            exit_code=2,
        )
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise BuilderError(
            f"{label}_unresolvable: {candidate}: {exc}",
            exit_kind="input_boundary_error",
            exit_code=2,
        ) from exc


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


def path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _canonical_repository_path(value: Any) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or value.startswith("/")
        or value.endswith("/")
    ):
        return None
    pure = PurePosixPath(value)
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    canonical = pure.as_posix()
    return canonical if canonical == value else None


def _relative_path(path: Path, root: Path) -> str | None:
    try:
        candidate = _normalized_absolute_path(path)
        return candidate.relative_to(root.resolve(strict=True)).as_posix()
    except (OSError, ValueError):
        return None


def _subject_run_key(subject: dict[str, Any]) -> str:
    return (
        f"GITHUB_RUN_ID={subject.get('workflow_run_id')}"
        f"|GITHUB_RUN_ATTEMPT={subject.get('workflow_run_attempt')}"
        f"|GITHUB_WORKFLOW={subject.get('workflow_name')}"
    )


def _workflow_ref(subject: dict[str, Any]) -> str:
    return (
        f"{subject.get('repository')}/{subject.get('workflow_path')}"
        f"@{subject.get('source_ref')}"
    )


def _trusted_git_candidates() -> tuple[Path, ...]:
    _require_supported_execution_platform()
    return LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES


def _validated_trusted_git(path: Path) -> Path:
    _require_supported_execution_platform()
    if not path.is_absolute():
        raise BuilderError(
            f"trusted_git_not_absolute: {path}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    candidate = _normalized_absolute_path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BuilderError(
            f"trusted_git_unresolvable: {candidate}: {exc}",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if os.path.normcase(str(candidate)) != os.path.normcase(str(resolved)):
        raise BuilderError(
            f"trusted_git_alias_rejected: supplied={candidate} resolved={resolved}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    components: list[Path] = [resolved]
    cursor = resolved.parent
    while True:
        components.append(cursor)
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    for component in components:
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise BuilderError(
                f"trusted_git_component_unavailable: {component}: {exc}",
                exit_kind="trusted_git_error",
                exit_code=2,
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise BuilderError(
                f"trusted_git_symlink_component_rejected: {component}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
        if component == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise BuilderError(
                    f"trusted_git_not_regular_file: {component}",
                    exit_kind="trusted_git_error",
                    exit_code=2,
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise BuilderError(
                f"trusted_git_parent_not_directory: {component}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
        if metadata.st_uid != 0:
            raise BuilderError(
                "trusted_git_unprotected_owner_rejected: "
                f"component={component} uid={metadata.st_uid}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise BuilderError(
                f"trusted_git_writable_component_rejected: {component}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
    if not os.access(resolved, os.X_OK):
        raise BuilderError(
            f"trusted_git_not_executable: {resolved}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    approved = {
        os.path.normcase(str(_normalized_absolute_path(candidate_path)))
        for candidate_path in _trusted_git_candidates()
    }
    if os.path.normcase(str(resolved)) not in approved:
        raise BuilderError(
            f"trusted_git_unapproved_candidate: {resolved}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    return resolved


def _select_trusted_git(explicit: str | None) -> Path:
    if explicit is not None:
        return _validated_trusted_git(Path(explicit))
    unavailable: list[str] = []
    untrusted: list[str] = []
    for candidate in _trusted_git_candidates():
        if not candidate.exists():
            unavailable.append(str(candidate))
            continue
        try:
            return _validated_trusted_git(candidate)
        except BuilderError as exc:
            untrusted.append(str(exc))
    raise BuilderError(
        "trusted_git_unavailable: "
        + json.dumps(
            {"unavailable": unavailable, "untrusted": untrusted},
            sort_keys=True,
        ),
        exit_kind="trusted_git_error",
        exit_code=2,
    )


def _git_environment(git_path: Path) -> dict[str, str]:
    environment = {
        key: value
        for key in GIT_ENV_ALLOWLIST
        if (value := os.environ.get(key)) is not None
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": str(git_path.parent),
        }
    )
    return environment


def _run_git(
    *,
    git_path: Path,
    repository_root: Path,
    arguments: Sequence[str],
    label: str,
    timeout_seconds: int = 60,
) -> bytes:
    command = [
        str(git_path),
        "--no-pager",
        "--no-replace-objects",
        "-c",
        f"safe.directory={repository_root}",
        "-C",
        str(repository_root),
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
            env=_git_environment(git_path),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuilderError(
            f"{label}_git_execution_failed: {exc}",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuilderError(
            f"{label}_git_failed: returncode={result.returncode} detail={detail!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    return result.stdout


def _verify_git_repository(
    *,
    git_path: Path,
    repository_root: Path,
    expected_revision: str,
    label: str,
) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", expected_revision) is None:
        raise BuilderError(
            f"{label}_expected_revision_not_sha40: {expected_revision!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    top_level_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("rev-parse", "--show-toplevel"),
        label=f"{label}_top_level",
    )
    try:
        top_level = Path(top_level_raw.decode("utf-8", errors="strict").strip())
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_top_level_invalid_utf8",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if not same_target(top_level, repository_root):
        raise BuilderError(
            f"{label}_repository_root_mismatch: "
            f"expected={repository_root} observed={top_level}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    head_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("rev-parse", "HEAD"),
        label=f"{label}_head",
    )
    try:
        head = head_raw.decode("ascii", errors="strict").strip().lower()
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_head_not_ascii",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise BuilderError(
            f"{label}_head_not_sha40: {head!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    if head != expected_revision:
        raise BuilderError(
            f"{label}_head_mismatch: expected={expected_revision} observed={head}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    return head


def _decode_git_storage_path(
    raw: bytes,
    *,
    repository_root: Path,
    label: str,
) -> Path:
    try:
        value = raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_invalid_utf8",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if not value or "\x00" in value:
        raise BuilderError(
            f"{label}_invalid_path: {value!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return _validated_directory_root(candidate, label=label)


def _git_storage_identity(
    *,
    git_path: Path,
    repository_root: Path,
    label: str,
) -> tuple[Path, Path]:
    common_dir = _decode_git_storage_path(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-common-dir"),
            label=f"{label}_git_common_dir",
        ),
        repository_root=repository_root,
        label=f"{label}_git_common_dir",
    )
    object_store = _decode_git_storage_path(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-path", "objects"),
            label=f"{label}_git_object_store",
        ),
        repository_root=repository_root,
        label=f"{label}_git_object_store",
    )

    for alternate_name in ("alternates", "http-alternates"):
        alternate_raw = _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=(
                "rev-parse",
                "--git-path",
                f"objects/info/{alternate_name}",
            ),
            label=f"{label}_git_{alternate_name}_path",
        )
        try:
            alternate_value = alternate_raw.decode(
                "utf-8",
                errors="strict",
            ).strip()
        except UnicodeDecodeError as exc:
            raise BuilderError(
                f"{label}_git_{alternate_name}_path_invalid_utf8",
                exit_kind="trusted_git_error",
                exit_code=2,
            ) from exc
        if not alternate_value or "\x00" in alternate_value:
            raise BuilderError(
                f"{label}_git_{alternate_name}_path_invalid: "
                f"{alternate_value!r}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
        alternate_path = Path(alternate_value)
        if not alternate_path.is_absolute():
            alternate_path = repository_root / alternate_path
        alternate_path = _normalized_absolute_path(alternate_path)
        if alternate_path.exists():
            payload = read_regular_file(
                alternate_path,
                label=f"{label}_git_{alternate_name}",
                max_bytes=1024 * 1024,
            )
            if payload.strip():
                raise BuilderError(
                    f"{label}_git_object_alternates_rejected: "
                    f"{alternate_path}",
                    exit_kind="trusted_git_error",
                    exit_code=2,
                )

    return common_dir, object_store


def _paths_overlap(left: Path, right: Path) -> bool:
    return (
        same_target(left, right)
        or path_is_within(left, right)
        or path_is_within(right, left)
    )


def _verify_independent_git_storage(
    *,
    git_path: Path,
    subject_root: Path,
    control_plane_root: Path,
) -> None:
    subject_common, subject_objects = _git_storage_identity(
        git_path=git_path,
        repository_root=subject_root,
        label="subject",
    )
    control_common, control_objects = _git_storage_identity(
        git_path=git_path,
        repository_root=control_plane_root,
        label="control_plane",
    )

    subject_stores = (subject_common, subject_objects)
    control_stores = (control_common, control_objects)
    for subject_store in subject_stores:
        for control_store in control_stores:
            if _paths_overlap(subject_store, control_store):
                raise BuilderError(
                    "subject_and_control_plane_git_storage_must_be_independent: "
                    f"subject={subject_store} control_plane={control_store}",
                    exit_kind="trusted_git_error",
                    exit_code=2,
                )

    for subject_store in subject_stores:
        if path_is_within(subject_store, control_plane_root):
            raise BuilderError(
                "subject_git_storage_inside_control_plane_checkout: "
                f"{subject_store}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )
    for control_store in control_stores:
        if path_is_within(control_store, subject_root):
            raise BuilderError(
                "control_plane_git_storage_inside_subject_checkout: "
                f"{control_store}",
                exit_kind="trusted_git_error",
                exit_code=2,
            )


def _git_blob(
    *,
    git_path: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    label: str,
    max_bytes: int,
    blob_cache: dict[tuple[str, str, str], bytes] | None = None,
) -> bytes:
    canonical = _canonical_repository_path(repository_path)
    if canonical is None:
        raise BuilderError(
            f"{label}_repository_path_not_canonical: {repository_path!r}"
        )

    cache_key = (
        os.path.normcase(str(repository_root)),
        revision,
        canonical,
    )
    if blob_cache is not None and cache_key in blob_cache:
        cached = blob_cache[cache_key]
        if len(cached) > max_bytes:
            raise BuilderError(
                f"{label}_committed_blob_too_large: "
                f"size={len(cached)} maximum={max_bytes}"
            )
        return cached

    object_name = f"{revision}:{canonical}"
    object_type_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("cat-file", "-t", object_name),
        label=f"{label}_type",
    )
    try:
        object_type = object_type_raw.decode(
            "ascii",
            errors="strict",
        ).strip()
    except UnicodeDecodeError as exc:
        raise BuilderError(
            f"{label}_object_type_not_ascii",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if object_type != "blob":
        raise BuilderError(
            f"{label}_object_not_blob: observed={object_type!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    size_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("cat-file", "-s", object_name),
        label=f"{label}_size",
    )
    try:
        declared_size = int(
            size_raw.decode("ascii", errors="strict").strip(),
            10,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuilderError(
            f"{label}_blob_size_invalid",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if declared_size < 0:
        raise BuilderError(
            f"{label}_blob_size_negative: {declared_size}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    if declared_size > max_bytes:
        raise BuilderError(
            f"{label}_committed_blob_too_large: "
            f"size={declared_size} maximum={max_bytes}"
        )

    committed = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("cat-file", "blob", object_name),
        label=f"{label}_content",
    )
    if len(committed) != declared_size:
        raise BuilderError(
            f"{label}_blob_size_changed_or_misreported: "
            f"declared={declared_size} observed={len(committed)}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    if blob_cache is not None:
        blob_cache[cache_key] = committed
    return committed


def _verify_committed_worktree_file(
    *,
    git_path: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    label: str,
    max_bytes: int,
    blob_cache: dict[tuple[str, str, str], bytes] | None = None,
) -> bytes:
    committed = _git_blob(
        git_path=git_path,
        repository_root=repository_root,
        revision=revision,
        repository_path=repository_path,
        label=f"{label}_committed_blob",
        max_bytes=max_bytes,
        blob_cache=blob_cache,
    )
    working = read_regular_file(
        repository_root / repository_path,
        label=f"{label}_working_tree",
        max_bytes=max_bytes,
    )
    if working != committed:
        raise BuilderError(f"{label}_working_tree_differs_from_exact_revision")
    return committed


def _load_verified_validator_module(
    *,
    source: bytes,
    source_path: Path,
) -> Any:
    module_name = "_pulsemech_current_run_expectation_validator_v0_verified"
    module = types.ModuleType(module_name)
    module.__file__ = str(source_path)
    module.__package__ = ""
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        code = compile(
            source,
            str(source_path),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, module.__dict__)
    except Exception as exc:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise BuilderError(
            f"verified_validator_load_failed: {type(exc).__name__}: {exc}",
            exit_kind="validator_bootstrap_error",
            exit_code=2,
        ) from exc

    expected_identity = {
        "TOOL_NAME": "check_pulsemech_compute_current_run_export_expectation_v0",
        "TOOL_VERSION": "0.1.0",
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "DOCUMENT_TYPE": DOCUMENT_TYPE,
    }
    for field, expected in expected_identity.items():
        actual = getattr(module, field, None)
        if actual != expected:
            raise BuilderError(
                f"verified_validator_{field.lower()}_mismatch: "
                f"expected={expected!r} actual={actual!r}",
                exit_kind="validator_bootstrap_error",
                exit_code=2,
            )
    for required_callable in (
        "atomic_write",
        "build_diagnostic",
        "render_json",
        "schema_reference_policy_errors",
        "semantic_checks",
        "validate_instance",
    ):
        if not callable(getattr(module, required_callable, None)):
            raise BuilderError(
                f"verified_validator_callable_missing: {required_callable}",
                exit_kind="validator_bootstrap_error",
                exit_code=2,
            )
    return module


def _expectation_input_schema(
    expectation_schema: dict[str, Any],
) -> dict[str, Any]:
    definitions = expectation_schema.get("$defs")
    if not isinstance(definitions, dict):
        raise BuilderError("expectation_schema_missing_defs")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": copy.deepcopy(definitions),
        "type": "object",
        "additionalProperties": False,
        "required": [
            "archive_layout",
            "authority_sources",
            "carrier",
            "packet_producer_profile",
            "subject",
        ],
        "properties": {
            "archive_layout": {"$ref": "#/$defs/archive_layout"},
            "authority_sources": {"$ref": "#/$defs/authority_sources"},
            "carrier": {
                "allOf": [
                    {"$ref": "#/$defs/carrier"},
                    {
                        "properties": {
                            "carrier_kind": {
                                "const": "current_run_export_archive"
                            },
                            "producer": {"$ref": "#/$defs/carrier_producer"},
                        },
                        "required": ["carrier_kind", "producer"],
                    },
                ]
            },
            "packet_producer_profile": {
                "$ref": "#/$defs/packet_producer_profile"
            },
            "subject": {"$ref": "#/$defs/subject"},
        },
    }


def _verify_control_plane_components(
    *,
    git_path: Path,
    control_plane_root: Path,
    control_plane_revision: str,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    executed_relative = _relative_path(Path(__file__), control_plane_root)
    if executed_relative != EXPECTATION_BUILDER_PATH:
        raise BuilderError(
            "executed_builder_path_mismatch: "
            f"expected={EXPECTATION_BUILDER_PATH!r} actual={executed_relative!r}"
        )

    components: dict[str, Any] = {}
    payloads: dict[str, bytes] = {}
    seen_paths: set[str] = set()
    retained_payload_roles = {
        "expectation_schema",
        "expectation_validator",
        "subject_input_schema",
    }
    for role, repository_path, version in CONTROL_PLANE_COMPONENT_SPECS:
        canonical = _canonical_repository_path(repository_path)
        if canonical is None or canonical in seen_paths:
            raise BuilderError(
                "control_plane_component_path_invalid_or_duplicate: "
                f"role={role!r} path={repository_path!r}"
            )
        seen_paths.add(canonical)
        committed = _verify_committed_worktree_file(
            git_path=git_path,
            repository_root=control_plane_root,
            revision=control_plane_revision,
            repository_path=canonical,
            label=f"control_plane_component_{role}",
            max_bytes=MAX_COMPONENT_BYTES,
        )
        if role in retained_payload_roles:
            payloads[role] = committed
        components[role] = {
            "path": canonical,
            "sha256": sha256_bytes(committed),
            "source_revision": control_plane_revision,
            "version": version,
        }
    return components, payloads


def _flatten_authority_sources(
    authority_sources: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in ("workflow", "policy", "gate_registry"):
        value = authority_sources.get(name)
        if isinstance(value, dict):
            rows.append((name, value))
    additional = authority_sources.get("additional_sources")
    if isinstance(additional, list):
        for index, value in enumerate(additional):
            if isinstance(value, dict):
                rows.append((f"additional_sources[{index}]", value))
    return rows


def _external_signer_policy_source_path(
    authority_sources: dict[str, Any],
) -> str:
    additional = authority_sources.get("additional_sources")
    if not isinstance(additional, list):
        raise BuilderError("external_signer_policy_source_missing")

    matches = [
        source
        for source in additional
        if (
            isinstance(source, dict)
            and source.get("role") == "external_signer_policy"
        )
    ]
    if not matches:
        raise BuilderError("external_signer_policy_source_missing")
    if len(matches) != 1:
        raise BuilderError(
            "external_signer_policy_source_ambiguous: "
            f"count={len(matches)}"
        )

    path_value = matches[0].get("path_or_uri")
    canonical = _canonical_repository_path(path_value)
    if canonical is None:
        raise BuilderError(
            "external_signer_policy_source_path_not_canonical: "
            f"{path_value!r}"
        )
    if canonical != EXTERNAL_SIGNER_POLICY_PATH:
        raise BuilderError(
            "external_signer_policy_source_path_mismatch: "
            f"expected={EXTERNAL_SIGNER_POLICY_PATH!r} "
            f"actual={canonical!r}"
        )
    return canonical


def _verify_authority_sources(
    *,
    git_path: Path,
    subject_root: Path,
    subject_revision: str,
    authority_sources: dict[str, Any],
    trusted_workflow_name: str,
    trusted_workflow_path: str,
    trusted_workflow_ref: str,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    verified = copy.deepcopy(authority_sources)
    additional = verified.get("additional_sources")
    if isinstance(additional, list):
        verified["additional_sources"] = sorted(
            additional,
            key=lambda row: (
                row.get("source_id", "") if isinstance(row, dict) else ""
            ),
        )

    source_ids: list[str] = []
    verified_path_payloads: dict[str, bytes] = {}
    retained_payloads: dict[str, bytes] = {}
    for label, source in _flatten_authority_sources(verified):
        source_id = source.get("source_id")
        path_value = source.get("path_or_uri")
        revision = source.get("source_revision")
        canonical = _canonical_repository_path(path_value)
        if not isinstance(source_id, str) or not source_id.startswith("source:"):
            raise BuilderError(f"{label}_source_id_invalid: {source_id!r}")
        source_ids.append(source_id)
        if revision != subject_revision:
            raise BuilderError(
                f"{label}_source_revision_mismatch: "
                f"expected={subject_revision} actual={revision!r}"
            )
        if canonical is None:
            raise BuilderError(
                f"{label}_source_path_not_canonical: {path_value!r}"
            )

        if label == "workflow" and canonical != trusted_workflow_path:
            raise BuilderError(
                "workflow_source_path_mismatch: "
                f"expected={trusted_workflow_path!r} actual={canonical!r}"
            )
        if label == "policy" and canonical != POLICY_PATH:
            raise BuilderError(
                "policy_source_path_mismatch: "
                f"expected={POLICY_PATH!r} actual={canonical!r}"
            )
        if label == "gate_registry" and canonical != GATE_REGISTRY_PATH:
            raise BuilderError(
                "gate_registry_source_path_mismatch: "
                f"expected={GATE_REGISTRY_PATH!r} actual={canonical!r}"
            )

        committed = verified_path_payloads.get(canonical)
        if committed is None:
            committed = _verify_committed_worktree_file(
                git_path=git_path,
                repository_root=subject_root,
                revision=subject_revision,
                repository_path=canonical,
                label=f"authority_source_{label}",
                max_bytes=MAX_COMPONENT_BYTES,
            )
            verified_path_payloads[canonical] = committed
        observed_sha = sha256_bytes(committed)
        observed_size = len(committed)
        if source.get("sha256") != observed_sha:
            raise BuilderError(
                f"{label}_source_sha256_mismatch: "
                f"expected={source.get('sha256')!r} observed={observed_sha!r}"
            )
        if source.get("size_bytes") != observed_size:
            raise BuilderError(
                f"{label}_source_size_mismatch: "
                f"expected={source.get('size_bytes')!r} "
                f"observed={observed_size}"
            )
        if label in {"workflow", "policy", "gate_registry"}:
            retained_payloads[label] = committed

    if len(source_ids) != len(set(source_ids)):
        raise BuilderError("authority_source_ids_not_unique")
    for required in ("workflow", "policy", "gate_registry"):
        if required not in retained_payloads:
            raise BuilderError(f"verified_{required}_payload_missing")

    workflow_source = verified.get("workflow")
    if not isinstance(workflow_source, dict):
        raise BuilderError("verified_workflow_source_missing")
    if workflow_source.get("workflow_name") != trusted_workflow_name:
        raise BuilderError(
            "workflow_source_name_mismatch: "
            f"expected={trusted_workflow_name!r} "
            f"actual={workflow_source.get('workflow_name')!r}"
        )
    if workflow_source.get("workflow_ref") != trusted_workflow_ref:
        raise BuilderError(
            "workflow_source_ref_mismatch: "
            f"expected={trusted_workflow_ref!r} "
            f"actual={workflow_source.get('workflow_ref')!r}"
        )
    workflow = parse_yaml_object(
        retained_payloads["workflow"],
        label="verified_workflow",
    )
    if workflow.get("name") != trusted_workflow_name:
        raise BuilderError(
            "verified_workflow_name_mismatch: "
            f"expected={trusted_workflow_name!r} "
            f"actual={workflow.get('name')!r}"
        )

    registry_source = verified.get("gate_registry")
    if not isinstance(registry_source, dict):
        raise BuilderError("verified_gate_registry_source_missing")
    registry = parse_yaml_object(
        retained_payloads["gate_registry"],
        label="verified_gate_registry",
    )
    registry_version = registry.get("version")
    if not isinstance(registry_version, str) or not registry_version:
        raise BuilderError(
            f"verified_gate_registry_version_invalid: {registry_version!r}"
        )
    if registry_version != registry_source.get("registry_id"):
        raise BuilderError(
            "verified_gate_registry_identity_mismatch: "
            f"document={registry_version!r} "
            f"source={registry_source.get('registry_id')!r}"
        )

    return verified, retained_payloads


def _load_hashed_json_with_bytes(
    *,
    path: Path,
    expected_sha256: str,
    label: str,
    object_required: bool,
) -> tuple[Any, bytes]:
    payload = read_regular_file(
        path,
        label=label,
        max_bytes=MAX_AUTHORITY_ARTIFACT_BYTES,
    )
    observed = sha256_bytes(payload)
    if observed != expected_sha256:
        raise BuilderError(
            f"{label}_sha256_mismatch: "
            f"expected={expected_sha256!r} observed={observed!r}"
        )
    value = parse_json_bytes(payload, label=label)
    if object_required and not isinstance(value, dict):
        raise BuilderError(f"{label}_not_object")
    return value, payload


def _load_hashed_json(
    *,
    path: Path,
    expected_sha256: str,
    label: str,
    object_required: bool,
) -> Any:
    value, _payload = _load_hashed_json_with_bytes(
        path=path,
        expected_sha256=expected_sha256,
        label=label,
        object_required=object_required,
    )
    return value


def _parse_utc(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BuilderError(f"{label}_not_canonical_utc: {value!r}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BuilderError(f"{label}_invalid_datetime: {value!r}") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != timezone.utc.utcoffset(parsed)
    ):
        raise BuilderError(f"{label}_not_utc: {value!r}")
    return parsed


def _verify_trusted_current_run_binding(
    *,
    subject: dict[str, Any],
    subject_repository: str,
    subject_revision: str,
    workflow_name: str,
    workflow_path: str,
    workflow_run_id: int,
    workflow_run_number: int,
    workflow_run_attempt: int,
    source_ref: str,
    event_name: str,
    release_candidate_id: str,
    run_mode: str,
    active_policy_sets: Sequence[str],
) -> None:
    expected_run_key = (
        f"GITHUB_RUN_ID={workflow_run_id}"
        f"|GITHUB_RUN_ATTEMPT={workflow_run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
    )
    expected_workflow_ref = (
        f"{subject_repository}/{workflow_path}@{source_ref}"
    )
    expected = {
        "repository": subject_repository,
        "source_commit": subject_revision,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_run_id": workflow_run_id,
        "workflow_run_number": workflow_run_number,
        "workflow_run_attempt": workflow_run_attempt,
        "subject_run_key": expected_run_key,
        "workflow_ref": expected_workflow_ref,
        "source_ref": source_ref,
        "event_name": event_name,
        "release_candidate_id": release_candidate_id,
        "run_mode": run_mode,
        "active_policy_sets": list(active_policy_sets),
    }
    for field, expected_value in expected.items():
        actual = subject.get(field)
        if actual != expected_value:
            raise BuilderError(
                f"trusted_current_run_{field}_mismatch: "
                f"expected={expected_value!r} actual={actual!r}"
            )


def _ordered_unique_non_empty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _json_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _get_path_or_missing(value: Any, dotted: str) -> Any:
    current = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _blocking_flag_present(value: Any, *paths: str) -> bool:
    for path in paths:
        observed = _get_path_or_missing(value, path)
        if observed is _MISSING or observed is False:
            continue
        if observed is True:
            return True
        return True
    return False


def _stub_profile_blocks(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in NEUTRAL_STUB_PROFILES
    if value is False:
        return False
    if value is True:
        return True
    return True


def _status_stubbed(status: dict[str, Any]) -> bool:
    if _blocking_flag_present(status, *STUB_FLAG_PATHS):
        return True
    for path in STUB_PROFILE_PATHS:
        value = _get_path_or_missing(status, path)
        if value is _MISSING:
            continue
        if _stub_profile_blocks(value):
            return True
    return False


def _status_scaffold(status: dict[str, Any]) -> bool:
    return _blocking_flag_present(status, *SCAFFOLD_FLAG_PATHS)


def _release_gate_result(
    final_status: dict[str, Any],
    gate_id: str,
) -> dict[str, Any]:
    status_gates = final_status.get("gates")
    if not isinstance(status_gates, dict):
        return {
            "gate_id": gate_id,
            "passed": False,
            "present": False,
            "reason": "status.gates is missing or not an object",
            "value_type": "missing",
        }
    if gate_id not in status_gates:
        return {
            "gate_id": gate_id,
            "passed": False,
            "present": False,
            "reason": "missing required gate",
            "value_type": "missing",
        }
    observed = status_gates[gate_id]
    passed = observed is True
    return {
        "gate_id": gate_id,
        "passed": passed,
        "present": True,
        "reason": None if passed else "gate value is not literal true",
        "value_type": _json_value_type(observed),
    }


def _release_gate_passed(final_status: dict[str, Any], gate_id: str) -> bool:
    return _release_gate_result(final_status, gate_id)["passed"] is True


def _policy_gate_set(policy: dict[str, Any], name: str) -> list[str]:
    gates = policy.get("gates")
    if not isinstance(gates, dict):
        raise BuilderError("verified_policy_gates_not_object")
    values = gates.get(name)
    if not isinstance(values, list):
        raise BuilderError(f"verified_policy_gate_set_missing: {name}")
    result: list[str] = []
    for index, item in enumerate(values):
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise BuilderError(
                "verified_policy_gate_invalid: "
                f"set={name!r} index={index} value={item!r}"
            )
        result.append(item)
    if len(result) != len(set(result)):
        raise BuilderError(f"verified_policy_gate_set_not_unique: {name}")
    return result


def _active_gate_sets_for_target(target: str) -> list[str]:
    if target == "stage":
        return ["required"]
    if target == "prod":
        return ["required", "release_required"]
    raise BuilderError(f"release_decision_target_invalid: {target!r}")


def _effective_required_gates(
    policy: dict[str, Any],
    active_gate_sets: Sequence[str],
) -> list[str]:
    combined: list[str] = []
    for gate_set in active_gate_sets:
        combined.extend(_policy_gate_set(policy, gate_set))
    return _unique_preserve_order(combined)


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _status_schema_validation(
    *,
    final_status: dict[str, Any],
    status_schema: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(status_schema)
    try:
        validation_errors = sorted(
            validator.iter_errors(final_status),
            key=lambda item: list(item.path),
        )
    except Exception as exc:
        errors.append(str(exc))
    else:
        for error in validation_errors:
            path = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{path}: {error.message}")
    return {
        "errors": errors,
        "mode": "validated",
        "ok": not errors,
        "schema_path": STATUS_SCHEMA_PATH,
    }


def _parse_verified_policy(
    *,
    policy_bytes: bytes,
    policy_source: dict[str, Any],
    subject: dict[str, Any],
) -> dict[str, Any]:
    policy = parse_yaml_object(policy_bytes, label="verified_policy")
    header = policy.get("policy")
    if not isinstance(header, dict):
        raise BuilderError("verified_policy_header_not_object")
    policy_id = header.get("id")
    policy_version = header.get("version")
    expected_policy_id = policy_source.get("policy_id")
    if policy_id != expected_policy_id or policy_id != subject.get("policy_id"):
        raise BuilderError(
            "verified_policy_id_mismatch: "
            f"document={policy_id!r} source={expected_policy_id!r} "
            f"subject={subject.get('policy_id')!r}"
        )
    if policy_source.get("sha256") != subject.get("policy_sha256"):
        raise BuilderError(
            "verified_policy_subject_digest_mismatch: "
            f"source={policy_source.get('sha256')!r} "
            f"subject={subject.get('policy_sha256')!r}"
        )
    if not isinstance(policy_version, str) or not policy_version:
        raise BuilderError(
            f"verified_policy_version_invalid: {policy_version!r}"
        )
    return policy


def _derive_release_decision_projection(
    *,
    final_status: dict[str, Any],
    policy: dict[str, Any],
    target: str,
    status_schema_validation: dict[str, Any],
) -> dict[str, Any]:
    active_gate_sets = _active_gate_sets_for_target(target)
    effective_required_gates = _effective_required_gates(
        policy,
        active_gate_sets,
    )

    blocking_reasons: list[str] = []
    decision_basis: list[str] = []
    gate_results: list[dict[str, Any]] = []
    for gate_id in effective_required_gates:
        result = _release_gate_result(final_status, gate_id)
        gate_results.append(result)
        if result["passed"] is not True:
            reason = result["reason"] or "gate did not pass"
            _add_reason(blocking_reasons, f"{gate_id}: {reason}")

    detectors_materialized_ok = _release_gate_passed(
        final_status,
        "detectors_materialized_ok",
    )
    external_summaries_present = _release_gate_passed(
        final_status,
        "external_summaries_present",
    )
    external_all_pass = _release_gate_passed(
        final_status,
        "external_all_pass",
    )
    stubbed = _status_stubbed(final_status)
    scaffold = _status_scaffold(final_status)
    no_stubbed_gates = not stubbed and not scaffold

    if target == "stage":
        if not detectors_materialized_ok:
            _add_reason(
                blocking_reasons,
                "detectors_materialized_ok: required for STAGE-PASS and not literal true",
            )
        external_evidence_mode = "advisory"
        decision_basis.append(
            "stage target uses required gate set plus stage release conditions"
        )
    else:
        external_evidence_mode = "required"
        decision_basis.append(
            "prod target uses required + release_required gate sets"
        )

    if stubbed:
        _add_reason(blocking_reasons, "stubbed diagnostics are present")
    if scaffold:
        _add_reason(blocking_reasons, "scaffold diagnostics are present")

    if status_schema_validation.get("ok") is False:
        schema_errors = status_schema_validation.get("errors")
        if not isinstance(schema_errors, list):
            raise BuilderError("derived_status_schema_errors_not_list")
        for error in schema_errors:
            if not isinstance(error, str) or not error:
                raise BuilderError(
                    f"derived_status_schema_error_invalid: {error!r}"
                )
            _add_reason(
                blocking_reasons,
                f"status schema validation failed: {error}",
            )

    required_gates_passed = bool(effective_required_gates) and all(
        row["passed"] is True for row in gate_results
    )
    if not effective_required_gates:
        _add_reason(blocking_reasons, "effective required gate set is empty")

    if blocking_reasons:
        release_level = "FAIL"
    elif target == "stage":
        release_level = "STAGE-PASS"
    else:
        release_level = "PROD-PASS"

    if required_gates_passed:
        decision_basis.append("all effective required gates are literal true")
    else:
        decision_basis.append(
            "one or more effective required gates failed or were missing"
        )
    if no_stubbed_gates:
        decision_basis.append("no stubbed/scaffold diagnostics detected")
    else:
        decision_basis.append(
            "stubbed/scaffold diagnostics block release-level pass"
        )
    if detectors_materialized_ok:
        decision_basis.append("detectors_materialized_ok is literal true")
    if target == "prod" and external_summaries_present and external_all_pass:
        decision_basis.append(
            "external evidence is present and aggregate external pass is true"
        )

    return {
        "active_gate_sets": active_gate_sets,
        "blocking_reasons": blocking_reasons,
        "conditions": {
            "detectors_materialized_ok": detectors_materialized_ok,
            "external_all_pass": external_all_pass,
            "external_evidence_mode": external_evidence_mode,
            "external_summaries_present": external_summaries_present,
            "no_stubbed_gates": no_stubbed_gates,
            "scaffold": scaffold,
            "stubbed": stubbed,
        },
        "decision_basis": decision_basis,
        "effective_required_gates": effective_required_gates,
        "gate_results": gate_results,
        "release_level": release_level,
        "required_gates_passed": required_gates_passed,
        "status_schema_validation": status_schema_validation,
    }


def _verify_release_decision_projection(
    decision: dict[str, Any],
    *,
    expected: dict[str, Any],
) -> None:
    for field in (
        "active_gate_sets",
        "effective_required_gates",
        "gate_results",
        "required_gates_passed",
        "conditions",
        "status_schema_validation",
        "blocking_reasons",
        "decision_basis",
        "release_level",
    ):
        actual = decision.get(field)
        expected_value = expected[field]
        if actual != expected_value:
            raise BuilderError(
                f"release_decision_{field}_mismatch: "
                f"expected={expected_value!r} actual={actual!r}"
            )


def _verify_release_decision_header(decision: dict[str, Any]) -> datetime:
    if decision.get("schema") != RELEASE_DECISION_SCHEMA:
        raise BuilderError("release_decision_schema_identity_mismatch")
    if decision.get("version") != RELEASE_DECISION_VERSION:
        raise BuilderError("release_decision_version_mismatch")
    producer = decision.get("producer")
    expected_producer = {
        "name": RELEASE_DECISION_PRODUCER_NAME,
        "version": RELEASE_DECISION_VERSION,
    }
    if producer != expected_producer:
        raise BuilderError(
            "release_decision_producer_mismatch: "
            f"expected={expected_producer!r} actual={producer!r}"
        )
    return _parse_utc(
        decision.get("created_utc"),
        label="release_decision_created_utc",
    )


def _verify_observed_artifact_time_order(
    *,
    release_decision_created_utc: datetime,
    carrier_finalized_utc: datetime,
    expectation_created_utc: datetime,
) -> None:
    if release_decision_created_utc > carrier_finalized_utc:
        raise BuilderError(
            "release_decision_created_after_carrier_finalization: "
            f"release_decision_created_utc="
            f"{release_decision_created_utc.isoformat()} "
            f"carrier_finalized_utc={carrier_finalized_utc.isoformat()}"
        )
    if carrier_finalized_utc > expectation_created_utc:
        raise BuilderError(
            "carrier_finalized_after_expectation_creation: "
            f"carrier_finalized_utc={carrier_finalized_utc.isoformat()} "
            f"expectation_created_utc={expectation_created_utc.isoformat()}"
        )


def _verify_subject_artifacts(
    *,
    git_path: Path,
    subject_root: Path,
    subject_revision: str,
    validator_module: Any,
    subject: dict[str, Any],
    authority_sources: dict[str, Any],
    authority_payloads: dict[str, bytes],
    final_status_path: Path,
    release_decision_path: Path,
    materialized_gate_set_path: Path | None,
    carrier: dict[str, Any],
    expectation_created_utc: str,
    release_target: str,
    workflow_active_policy_sets: Sequence[str],
) -> None:
    final_status = _load_hashed_json(
        path=final_status_path,
        expected_sha256=subject["final_status_sha256"],
        label="final_status",
        object_required=True,
    )
    metrics = final_status.get("metrics")
    gate_registry = authority_sources.get("gate_registry")
    policy_source = authority_sources.get("policy")
    if not isinstance(metrics, dict):
        raise BuilderError("final_status_metrics_not_object")
    if not isinstance(gate_registry, dict):
        raise BuilderError("verified_gate_registry_source_missing")
    if not isinstance(policy_source, dict):
        raise BuilderError("verified_policy_source_missing")

    expected_status_bindings = {
        "run_mode": subject.get("run_mode"),
        "git_sha": subject.get("source_commit"),
        "run_key": subject.get("subject_run_key"),
        "gate_policy_sha256": subject.get("policy_sha256"),
        "gate_registry_sha256": gate_registry.get("sha256"),
    }
    for field, expected in expected_status_bindings.items():
        actual = metrics.get(field)
        if actual != expected:
            raise BuilderError(
                f"final_status_{field}_mismatch: "
                f"expected={expected!r} actual={actual!r}"
            )

    policy_bytes = authority_payloads.get("policy")
    if policy_bytes is None:
        raise BuilderError("verified_policy_payload_missing")
    policy = _parse_verified_policy(
        policy_bytes=policy_bytes,
        policy_source=policy_source,
        subject=subject,
    )
    for gate_set in workflow_active_policy_sets:
        _policy_gate_set(policy, gate_set)

    status_schema_bytes = _verify_committed_worktree_file(
        git_path=git_path,
        repository_root=subject_root,
        revision=subject_revision,
        repository_path=STATUS_SCHEMA_PATH,
        label="status_schema",
        max_bytes=MAX_SCHEMA_BYTES,
    )
    status_schema = parse_json_bytes(
        status_schema_bytes,
        label="status_schema",
    )
    if not isinstance(status_schema, dict):
        raise BuilderError("status_schema_not_object")
    reference_errors = validator_module.schema_reference_policy_errors(
        status_schema,
        label="status_schema",
    )
    if reference_errors:
        raise BuilderError(
            "status_schema_reference_policy_invalid: "
            + " | ".join(reference_errors)
        )
    try:
        jsonschema.Draft202012Validator.check_schema(status_schema)
    except Exception as exc:
        raise BuilderError(
            f"status_schema_draft202012_invalid: {type(exc).__name__}: {exc}"
        ) from exc
    status_validation = _status_schema_validation(
        final_status=final_status,
        status_schema=status_schema,
    )

    decision = _load_hashed_json(
        path=release_decision_path,
        expected_sha256=subject["release_decision_sha256"],
        label="release_decision",
        object_required=True,
    )
    release_decision_schema_bytes = _verify_committed_worktree_file(
        git_path=git_path,
        repository_root=subject_root,
        revision=subject_revision,
        repository_path=RELEASE_DECISION_SCHEMA_PATH,
        label="release_decision_schema",
        max_bytes=MAX_SCHEMA_BYTES,
    )
    release_decision_schema = parse_json_bytes(
        release_decision_schema_bytes,
        label="release_decision_schema",
    )
    if not isinstance(release_decision_schema, dict):
        raise BuilderError("release_decision_schema_not_object")
    release_reference_errors = validator_module.schema_reference_policy_errors(
        release_decision_schema,
        label="release_decision_schema",
    )
    if release_reference_errors:
        raise BuilderError(
            "release_decision_schema_reference_policy_invalid: "
            + " | ".join(release_reference_errors)
        )
    try:
        jsonschema.Draft202012Validator.check_schema(release_decision_schema)
    except Exception as exc:
        raise BuilderError(
            "release_decision_schema_draft202012_invalid: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    decision_valid, decision_errors = validator_module.validate_instance(
        release_decision_schema,
        decision,
        label="release_decision",
    )
    if not decision_valid:
        raise BuilderError(
            "release_decision_schema_invalid: " + " | ".join(decision_errors)
        )
    release_decision_created_utc = _verify_release_decision_header(decision)
    carrier_finalized_utc = _parse_utc(
        carrier.get("finalized_utc"),
        label="carrier_finalized_utc",
    )
    protected_expectation_created_utc = _parse_utc(
        expectation_created_utc,
        label="expectation_created_utc",
    )
    _verify_observed_artifact_time_order(
        release_decision_created_utc=release_decision_created_utc,
        carrier_finalized_utc=carrier_finalized_utc,
        expectation_created_utc=protected_expectation_created_utc,
    )

    materialized_sha = subject.get("materialized_gate_set_sha256")
    if materialized_sha is None:
        if materialized_gate_set_path is not None:
            raise BuilderError(
                "materialized_gate_set_path_present_but_subject_digest_is_null"
            )
    else:
        if materialized_gate_set_path is None:
            raise BuilderError(
                "materialized_gate_set_path_required_for_non_null_subject_digest"
            )
        materialized, materialized_bytes = _load_hashed_json_with_bytes(
            path=materialized_gate_set_path,
            expected_sha256=materialized_sha,
            label="materialized_gate_set",
            object_required=True,
        )
        expected_materialized = {
            "authority_boundary": {
                "creates_release_authority": False,
                "materialization_role": "required_gate_set_reconstruction",
                "source": "declared_gate_policy",
            },
            "effective_required_gates": _effective_required_gates(
                policy,
                workflow_active_policy_sets,
            ),
            "policy_path": POLICY_PATH,
            "policy_sha256": subject.get("policy_sha256"),
            "schema": MATERIALIZED_GATE_SET_SCHEMA,
            "sets": {
                "release_required": _policy_gate_set(
                    policy,
                    "release_required",
                ),
                "required": _policy_gate_set(policy, "required"),
            },
        }
        if materialized != expected_materialized:
            raise BuilderError(
                "materialized_gate_set_content_mismatch: "
                f"expected={expected_materialized!r} actual={materialized!r}"
            )
        expected_materialized_bytes = render_json(expected_materialized)
        if materialized_bytes != expected_materialized_bytes:
            raise BuilderError("materialized_gate_set_not_canonical_or_exact")

    decision_run_mode = decision.get("run_mode")
    if decision_run_mode != subject.get("run_mode"):
        raise BuilderError(
            "release_decision_run_mode_mismatch: "
            f"subject={subject.get('run_mode')!r} "
            f"decision={decision_run_mode!r}"
        )

    if decision.get("target") != release_target:
        raise BuilderError(
            "release_decision_target_mismatch: "
            f"trusted={release_target!r} actual={decision.get('target')!r}"
        )

    expected_projection = _derive_release_decision_projection(
        final_status=final_status,
        policy=policy,
        target=release_target,
        status_schema_validation=status_validation,
    )
    _verify_release_decision_projection(
        decision,
        expected=expected_projection,
    )

    release_level = expected_projection["release_level"]
    expected_subject_decision = (
        "BLOCK" if release_level == "FAIL" else "ALLOW"
    )
    if subject.get("decision") != expected_subject_decision:
        raise BuilderError(
            "subject_decision_mismatch: "
            f"expected={expected_subject_decision!r} "
            f"actual={subject.get('decision')!r}"
        )

    if decision.get("policy_path") != POLICY_PATH:
        raise BuilderError(
            "release_decision_policy_path_mismatch: "
            f"expected={POLICY_PATH!r} "
            f"actual={decision.get('policy_path')!r}"
        )
    status_path = decision.get("status_path")
    if not isinstance(status_path, str) or not status_path:
        raise BuilderError(
            f"release_decision_status_path_invalid: {status_path!r}"
        )

    exact_equalities = (
        ("git_sha", subject.get("source_commit")),
        ("status_sha256", subject.get("final_status_sha256")),
        ("policy_sha256", subject.get("policy_sha256")),
    )
    for field, expected in exact_equalities:
        actual = decision.get(field)
        if actual != expected:
            raise BuilderError(
                f"release_decision_{field}_mismatch: "
                f"expected={expected!r} actual={actual!r}"
            )


def _verify_carrier_producer(
    *,
    carrier: dict[str, Any],
    subject: dict[str, Any],
    control_plane_revision: str,
    components: dict[str, Any],
) -> None:
    producer = carrier.get("producer")
    loader = components.get("carrier_loader")
    if not isinstance(producer, dict) or not isinstance(loader, dict):
        raise BuilderError("carrier_producer_or_loader_binding_missing")
    required_equalities = {
        "producer_source": loader.get("path"),
        "producer_source_revision": loader.get("source_revision"),
        "producer_source_sha256": loader.get("sha256"),
        "producer_version": loader.get("version"),
        "producer_run_key": subject.get("subject_run_key"),
        "production_mode": "current_run_export_carrier_builder",
    }
    for field, expected in required_equalities.items():
        if producer.get(field) != expected:
            raise BuilderError(
                f"carrier_producer_{field}_mismatch: "
                f"expected={expected!r} actual={producer.get(field)!r}"
            )
    if producer.get("producer_source_revision") != control_plane_revision:
        raise BuilderError("carrier_producer_control_plane_revision_mismatch")


def _expectation_id(subject: dict[str, Any]) -> str:
    return (
        "current-run-export-expectation:"
        f"{subject.get('repository')}/"
        f"{subject.get('workflow_run_id')}/"
        f"{subject.get('workflow_run_attempt')}"
    )


def build_expectation(
    *,
    builder_input: dict[str, Any],
    control_plane_repository: str,
    control_plane_revision: str,
    components: dict[str, Any],
    authority_sources: dict[str, Any],
    expectation_created_utc: str,
    ci_workflow_or_job_identity: str,
) -> dict[str, Any]:
    subject = copy.deepcopy(builder_input["subject"])
    profile = copy.deepcopy(builder_input["packet_producer_profile"])
    carrier = copy.deepcopy(builder_input["carrier"])
    archive_layout = copy.deepcopy(builder_input["archive_layout"])
    builder_component = components["expectation_builder"]

    return {
        "archive_layout": archive_layout,
        "authority_boundary": copy.deepcopy(CLOSED_AUTHORITY_BOUNDARY),
        "authority_sources": authority_sources,
        "carrier": carrier,
        "content_boundary": copy.deepcopy(CLOSED_CONTENT_BOUNDARY),
        "document_type": DOCUMENT_TYPE,
        "errors": [],
        "expectation_identity": {
            "canonicalization": "json-sort-keys-utf8-newline",
            "expectation_created_utc": expectation_created_utc,
            "expectation_id": _expectation_id(subject),
            "expectation_scope": "current_run_export",
            "subject_run_key": subject["subject_run_key"],
        },
        "expectation_producer": {
            "ci_workflow_or_job_identity": ci_workflow_or_job_identity,
            "producer_id": EXPECTATION_PRODUCER_ID,
            "producer_name": EXPECTATION_PRODUCER_NAME,
            "producer_run_key": subject["subject_run_key"],
            "producer_source": builder_component["path"],
            "producer_source_revision": builder_component[
                "source_revision"
            ],
            "producer_source_sha256": builder_component["sha256"],
            "producer_version": builder_component["version"],
            "production_mode": "current_run_expectation_builder",
        },
        "ok": True,
        "packet_contract": copy.deepcopy(PACKET_CONTRACT),
        "packet_producer_profile": profile,
        "record_status": "observed",
        "schema_version": SCHEMA_VERSION,
        "subject": subject,
        "trusted_control_plane": {
            "checkout_role": "protected_control_plane",
            "components": components,
            "repository": control_plane_repository,
            "revision": control_plane_revision,
            "separate_from_subject_checkout": True,
            "subject_may_select_revision": False,
            "trust_mode": "protected_exact_revision",
        },
    }


def _strict_validate_generated_expectation(
    *,
    validator_module: Any,
    expectation_schema: dict[str, Any],
    subject_input_schema: dict[str, Any],
    expectation: dict[str, Any],
    subject_root: Path,
) -> None:
    rendered = validator_module.render_json(expectation)
    valid, errors = validator_module.validate_instance(
        expectation_schema,
        expectation,
        label="generated_expectation",
    )
    if not valid:
        raise BuilderError(
            "generated_expectation_schema_invalid: " + " | ".join(errors),
            exit_kind="generated_expectation_schema_error",
        )
    checks, semantic_errors, _derived = validator_module.semantic_checks(
        expectation,
        expectation_text=rendered,
        expectation_path=Path("/non-authoritative/generated-expectation.json"),
        repository_root=subject_root,
        expectation_schema=expectation_schema,
        subject_input_schema=subject_input_schema,
    )
    if (
        not checks
        or not all(checks.values())
        or semantic_errors
        or expectation.get("record_status") != "observed"
    ):
        detail = {
            "checks": dict(sorted(checks.items())),
            "errors": sorted(set(semantic_errors)),
        }
        raise BuilderError(
            "generated_expectation_strict_validation_failed: "
            + json.dumps(detail, ensure_ascii=False, sort_keys=True),
            exit_kind="strict_validation_error",
        )

    rendered_bytes = rendered.encode("utf-8")
    with tempfile.TemporaryDirectory(
        prefix="pulsemech-current-run-expectation-validation-"
    ) as temporary_directory:
        expectation_path = Path(temporary_directory) / "expectation.json"
        expectation_path.write_bytes(rendered_bytes)
        diagnostic, exit_code = validator_module.build_diagnostic(
            schema_path=validator_module.DEFAULT_SCHEMA,
            expectation_path=expectation_path,
            subject_input_schema_path=(
                validator_module.DEFAULT_SUBJECT_INPUT_SCHEMA
            ),
            repository_root=subject_root,
        )

    boundary = diagnostic.get("verification_boundary")
    identities = diagnostic.get("input_identities")
    expectation_identity = (
        identities.get("expectation")
        if isinstance(identities, dict)
        else None
    )
    if (
        exit_code != 0
        or diagnostic.get("ok") is not True
        or diagnostic.get("record_status") != "observed"
        or diagnostic.get("authority_effect") != "none"
        or not isinstance(boundary, dict)
        or boundary.get("contract_semantics_verified") is not True
        or boundary.get("canonical_contract_semantics_verified") is not True
        or not isinstance(expectation_identity, dict)
        or expectation_identity.get("sha256") != sha256_bytes(rendered_bytes)
        or expectation_identity.get("size_bytes") != len(rendered_bytes)
    ):
        raise BuilderError(
            "generated_expectation_validator_diagnostic_not_verified: "
            + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True),
            exit_kind="strict_validation_error",
        )


def _reject_missing_parent_symlinks(path: Path, *, label: str) -> None:
    cursor = _normalized_absolute_path(path)
    while not cursor.exists():
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    reject_symlink_components(cursor, label=label)


def _reject_unsafe_output(
    output: Path | None,
    *,
    protected_paths: Iterable[Path],
    protected_roots: Sequence[Path],
) -> None:
    if output is None:
        return
    candidate = _normalized_absolute_path(output)
    if not candidate.name or candidate.name in {".", ".."}:
        raise BuilderError(
            f"output_leaf_name_invalid: {candidate}",
            exit_kind="output_boundary_error",
            exit_code=2,
        )
    if candidate.name.casefold() in PROTECTED_OUTPUT_NAMES_CASEFOLDED:
        raise BuilderError(
            f"output_name_protected: {candidate.name}",
            exit_kind="output_boundary_error",
            exit_code=2,
        )
    for protected in protected_paths:
        if same_target(candidate, protected):
            raise BuilderError(
                f"output_overwrites_protected_input: {protected}",
                exit_kind="output_boundary_error",
                exit_code=2,
            )
    for root in protected_roots:
        if path_is_within(candidate, root):
            raise BuilderError(
                "output_inside_protected_repository: "
                f"output={candidate} root={root}",
                exit_kind="output_boundary_error",
                exit_code=2,
            )
    _reject_missing_parent_symlinks(candidate.parent, label="output_parent")
    if candidate.exists() and candidate.is_symlink():
        raise BuilderError(
            f"output_symlink_rejected: {candidate}",
            exit_kind="output_boundary_error",
            exit_code=2,
        )


def make_failure_diagnostic(
    *,
    error: str,
    exit_kind: str,
) -> dict[str, Any]:
    return {
        "authority_effect": "none",
        "document_type": DOCUMENT_TYPE,
        "errors": [error],
        "exit_kind": exit_kind,
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a machine-produced PULSEmech current-run export "
            "expectation from canonical metadata, exact subject artifacts, "
            "and a separate protected Linux control-plane checkout for "
            "HPC and Linux CI execution."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Canonical current-run expectation builder input JSON.",
    )
    parser.add_argument(
        "--expectation-schema",
        default=str(DEFAULT_EXPECTATION_SCHEMA),
        help="Canonical current-run expectation schema path.",
    )
    parser.add_argument(
        "--expectation-validator",
        default=str(DEFAULT_EXPECTATION_VALIDATOR),
        help="Canonical strict current-run expectation validator path.",
    )
    parser.add_argument(
        "--subject-input-schema",
        default=str(DEFAULT_SUBJECT_INPUT_SCHEMA),
        help="Canonical downstream subject-input packet schema path.",
    )
    parser.add_argument(
        "--subject-root",
        required=True,
        help="Exact subject repository checkout root.",
    )
    parser.add_argument("--subject-repository", required=True)
    parser.add_argument("--subject-revision", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-path", required=True)
    parser.add_argument("--workflow-run-id", required=True, type=int)
    parser.add_argument("--workflow-run-number", required=True, type=int)
    parser.add_argument("--workflow-run-attempt", required=True, type=int)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--release-candidate-id", required=True)
    parser.add_argument(
        "--run-mode",
        required=True,
        choices=("demo", "core", "prod"),
    )
    parser.add_argument(
        "--release-target",
        required=True,
        choices=("stage", "prod"),
        help="Independently supplied protected current-run release target.",
    )
    parser.add_argument(
        "--active-policy-set",
        dest="active_policy_sets",
        action="append",
        required=True,
        help=(
            "Workflow-effective policy set actually enforced by the source "
            "run. Repeat in exact enforcement order."
        ),
    )
    parser.add_argument("--expectation-created-utc", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument(
        "--control-plane-root",
        default=str(ROOT),
        help="Separate protected control-plane checkout root.",
    )
    parser.add_argument(
        "--control-plane-repository",
        required=True,
        help="Protected control-plane repository identity.",
    )
    parser.add_argument(
        "--control-plane-revision",
        required=True,
        help="Protected exact SHA-40 control-plane revision.",
    )
    parser.add_argument(
        "--trusted-git",
        help=(
            "Optional approved absolute Linux system Git executable. "
            "When omitted, the builder selects the first available protected "
            "Linux candidate."
        ),
    )
    parser.add_argument(
        "--final-status",
        required=True,
        help="Current-run final status JSON bound by subject.final_status_sha256.",
    )
    parser.add_argument(
        "--release-decision",
        required=True,
        help=(
            "Current-run release decision JSON bound by "
            "subject.release_decision_sha256."
        ),
    )
    parser.add_argument(
        "--materialized-gate-set",
        help=(
            "Materialized gate-set JSON; required exactly when the subject "
            "carries a non-null materialized_gate_set_sha256."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional external path for the canonical expectation JSON. "
            "Repository-local output is rejected."
        ),
    )
    return parser.parse_args()


def _build(args: argparse.Namespace) -> bytes:
    _require_supported_execution_platform()

    input_path = Path(args.input)
    expectation_schema_path = Path(args.expectation_schema)
    expectation_validator_path = Path(args.expectation_validator)
    subject_input_schema_path = Path(args.subject_input_schema)

    subject_root = _validated_directory_root(
        Path(args.subject_root),
        label="subject_root",
    )
    control_plane_root = _validated_directory_root(
        Path(args.control_plane_root),
        label="control_plane_root",
    )
    if same_target(subject_root, control_plane_root):
        raise BuilderError("subject_and_control_plane_roots_must_be_separate")
    if path_is_within(subject_root, control_plane_root) or path_is_within(
        control_plane_root,
        subject_root,
    ):
        raise BuilderError("subject_and_control_plane_roots_must_not_be_nested")

    control_plane_repository = str(args.control_plane_repository).strip()
    control_plane_revision = str(args.control_plane_revision).strip().lower()
    if not control_plane_repository:
        raise BuilderError("control_plane_repository_empty")
    if re.fullmatch(r"[0-9a-f]{40}", control_plane_revision) is None:
        raise BuilderError("control_plane_revision_not_sha40")

    trusted_git = _select_trusted_git(args.trusted_git)
    final_status_path = Path(args.final_status)
    release_decision_path = Path(args.release_decision)
    materialized_gate_set_path = (
        Path(args.materialized_gate_set)
        if args.materialized_gate_set is not None
        else None
    )
    output_path = Path(args.output) if args.output is not None else None

    canonical_path_bindings = (
        (
            expectation_schema_path,
            control_plane_root / EXPECTATION_SCHEMA_PATH,
            "expectation_schema_path",
        ),
        (
            expectation_validator_path,
            control_plane_root / EXPECTATION_VALIDATOR_PATH,
            "expectation_validator_path",
        ),
        (
            subject_input_schema_path,
            control_plane_root / SUBJECT_INPUT_SCHEMA_PATH,
            "subject_input_schema_path",
        ),
    )
    for supplied, expected, label in canonical_path_bindings:
        if not same_target(supplied, expected):
            raise BuilderError(
                f"{label}_mismatch: supplied={supplied} expected={expected}"
            )

    protected_paths = [
        Path(__file__),
        input_path,
        expectation_schema_path,
        expectation_validator_path,
        subject_input_schema_path,
        final_status_path,
        release_decision_path,
    ]
    if materialized_gate_set_path is not None:
        protected_paths.append(materialized_gate_set_path)
    _reject_unsafe_output(
        output_path,
        protected_paths=protected_paths,
        protected_roots=(subject_root, control_plane_root),
    )

    builder_input, _input_bytes = load_json_object(
        input_path,
        label="builder_input",
        max_bytes=MAX_INPUT_BYTES,
        canonical_required=True,
    )
    subject = builder_input.get("subject")
    if not isinstance(subject, dict):
        raise BuilderError(
            "builder_input_subject_not_object",
            exit_kind="input_schema_error",
        )
    subject_revision = str(args.subject_revision).strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", subject_revision) is None:
        raise BuilderError(
            "trusted_subject_revision_not_sha40",
            exit_kind="input_schema_error",
        )
    subject_repository = str(args.subject_repository).strip()
    workflow_name = str(args.workflow_name).strip()
    workflow_path = str(args.workflow_path).strip()
    source_ref = str(args.source_ref).strip()
    event_name = str(args.event_name).strip()
    release_candidate_id = str(args.release_candidate_id).strip()
    ci_workflow_or_job_identity = str(
        args.ci_workflow_or_job_identity
    ).strip()
    expectation_created_utc = str(args.expectation_created_utc).strip()
    release_target = str(args.release_target).strip()
    active_policy_sets = list(args.active_policy_sets or [])
    if (
        not active_policy_sets
        or any(
            not isinstance(value, str)
            or not value
            or value != value.strip()
            for value in active_policy_sets
        )
        or len(active_policy_sets) != len(set(active_policy_sets))
    ):
        raise BuilderError("trusted_active_policy_sets_invalid")
    for label, value in (
        ("subject_repository", subject_repository),
        ("workflow_name", workflow_name),
        ("workflow_path", workflow_path),
        ("source_ref", source_ref),
        ("event_name", event_name),
        ("release_candidate_id", release_candidate_id),
        ("ci_workflow_or_job_identity", ci_workflow_or_job_identity),
    ):
        if not value:
            raise BuilderError(f"trusted_{label}_empty")
    if _canonical_repository_path(workflow_path) is None:
        raise BuilderError("trusted_workflow_path_not_canonical")
    if (
        args.workflow_run_id <= 0
        or args.workflow_run_number <= 0
        or args.workflow_run_attempt <= 0
    ):
        raise BuilderError("trusted_workflow_run_identity_not_positive")
    _parse_utc(
        expectation_created_utc,
        label="expectation_created_utc",
    )
    _verify_trusted_current_run_binding(
        subject=subject,
        subject_repository=subject_repository,
        subject_revision=subject_revision,
        workflow_name=workflow_name,
        workflow_path=workflow_path,
        workflow_run_id=args.workflow_run_id,
        workflow_run_number=args.workflow_run_number,
        workflow_run_attempt=args.workflow_run_attempt,
        source_ref=source_ref,
        event_name=event_name,
        release_candidate_id=release_candidate_id,
        run_mode=args.run_mode,
        active_policy_sets=active_policy_sets,
    )

    _verify_git_repository(
        git_path=trusted_git,
        repository_root=control_plane_root,
        expected_revision=control_plane_revision,
        label="control_plane",
    )
    _verify_git_repository(
        git_path=trusted_git,
        repository_root=subject_root,
        expected_revision=subject_revision,
        label="subject",
    )
    _verify_independent_git_storage(
        git_path=trusted_git,
        subject_root=subject_root,
        control_plane_root=control_plane_root,
    )

    components, component_payloads = _verify_control_plane_components(
        git_path=trusted_git,
        control_plane_root=control_plane_root,
        control_plane_revision=control_plane_revision,
    )
    expectation_schema_bytes = component_payloads["expectation_schema"]
    subject_input_schema_bytes = component_payloads["subject_input_schema"]
    validator_bytes = component_payloads["expectation_validator"]

    expectation_schema = parse_json_bytes(
        expectation_schema_bytes,
        label="expectation_schema",
    )
    subject_input_schema = parse_json_bytes(
        subject_input_schema_bytes,
        label="subject_input_schema",
    )
    if not isinstance(expectation_schema, dict):
        raise BuilderError("expectation_schema_not_object")
    if not isinstance(subject_input_schema, dict):
        raise BuilderError("subject_input_schema_not_object")

    validator_module = _load_verified_validator_module(
        source=validator_bytes,
        source_path=control_plane_root / EXPECTATION_VALIDATOR_PATH,
    )
    for label, schema in (
        ("expectation_schema", expectation_schema),
        ("subject_input_schema", subject_input_schema),
    ):
        reference_errors = validator_module.schema_reference_policy_errors(
            schema,
            label=label,
        )
        if reference_errors:
            raise BuilderError(
                f"{label}_reference_policy_invalid: "
                + " | ".join(reference_errors)
            )
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except Exception as exc:
            raise BuilderError(
                f"{label}_draft202012_invalid: {type(exc).__name__}: {exc}"
            ) from exc

    input_schema = _expectation_input_schema(expectation_schema)
    input_valid, input_errors = validator_module.validate_instance(
        input_schema,
        builder_input,
        label="builder_input",
    )
    if not input_valid:
        raise BuilderError(
            "builder_input_schema_invalid: " + " | ".join(input_errors),
            exit_kind="input_schema_error",
        )

    if subject["subject_run_key"] != _subject_run_key(subject):
        raise BuilderError("subject_run_key_not_canonical")
    if subject["workflow_ref"] != _workflow_ref(subject):
        raise BuilderError("subject_workflow_ref_not_canonical")

    trusted_workflow_ref = (
        f"{subject_repository}/{workflow_path}@{source_ref}"
    )
    verified_sources, authority_payloads = _verify_authority_sources(
        git_path=trusted_git,
        subject_root=subject_root,
        subject_revision=subject_revision,
        authority_sources=builder_input["authority_sources"],
        trusted_workflow_name=workflow_name,
        trusted_workflow_path=workflow_path,
        trusted_workflow_ref=trusted_workflow_ref,
    )
    verified_external_signer_policy_path = (
        _external_signer_policy_source_path(verified_sources)
    )
    _verify_subject_artifacts(
        git_path=trusted_git,
        subject_root=subject_root,
        subject_revision=subject_revision,
        validator_module=validator_module,
        subject=subject,
        authority_sources=verified_sources,
        authority_payloads=authority_payloads,
        final_status_path=final_status_path,
        release_decision_path=release_decision_path,
        materialized_gate_set_path=materialized_gate_set_path,
        carrier=builder_input["carrier"],
        expectation_created_utc=expectation_created_utc,
        release_target=release_target,
        workflow_active_policy_sets=active_policy_sets,
    )
    _verify_carrier_producer(
        carrier=builder_input["carrier"],
        subject=subject,
        control_plane_revision=control_plane_revision,
        components=components,
    )

    profile = builder_input["packet_producer_profile"]
    if profile["expected_producer_source_path"] != (
        components["subject_input_producer_wrapper"]["path"]
    ):
        raise BuilderError("packet_profile_subject_input_wrapper_mismatch")
    if (
        profile["expected_signer_policy_path"]
        != verified_external_signer_policy_path
    ):
        raise BuilderError(
            "packet_profile_signer_policy_path_mismatch: "
            f"expected={verified_external_signer_policy_path!r} "
            f"actual={profile['expected_signer_policy_path']!r}"
        )
    if profile["expected_repository"] != subject["repository"]:
        raise BuilderError("packet_profile_subject_repository_mismatch")
    if profile["expected_source_commit"] != subject_revision:
        raise BuilderError("packet_profile_subject_revision_mismatch")
    if profile["expected_subject_run_key"] != subject["subject_run_key"]:
        raise BuilderError("packet_profile_subject_run_key_mismatch")
    if profile["expected_archive_layout_id"] != builder_input[
        "archive_layout"
    ]["layout_id"]:
        raise BuilderError("packet_profile_archive_layout_mismatch")

    expectation = build_expectation(
        builder_input=builder_input,
        control_plane_repository=control_plane_repository,
        control_plane_revision=control_plane_revision,
        components=components,
        authority_sources=verified_sources,
        expectation_created_utc=expectation_created_utc,
        ci_workflow_or_job_identity=ci_workflow_or_job_identity,
    )
    _strict_validate_generated_expectation(
        validator_module=validator_module,
        expectation_schema=expectation_schema,
        subject_input_schema=subject_input_schema,
        expectation=expectation,
        subject_root=subject_root,
    )

    rendered = render_json(expectation)
    if output_path is not None:
        validator_module.atomic_write(output_path, rendered.decode("utf-8"))
        written = read_regular_file(
            output_path,
            label="written_output",
            max_bytes=MAX_INPUT_BYTES,
        )
        if written != rendered:
            raise BuilderError(
                "written_output_bytes_mismatch",
                exit_kind="output_write_error",
                exit_code=2,
            )
    return rendered


def main() -> int:
    args = parse_args()
    try:
        rendered = _build(args)
    except BuilderError as exc:
        diagnostic = make_failure_diagnostic(
            error=str(exc),
            exit_kind=exc.exit_kind,
        )
        sys.stderr.buffer.write(render_json(diagnostic))
        return exc.exit_code
    except Exception as exc:
        diagnostic = make_failure_diagnostic(
            error=f"unhandled_builder_error: {type(exc).__name__}: {exc}",
            exit_kind="unhandled_error",
        )
        sys.stderr.buffer.write(render_json(diagnostic))
        return 2

    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
