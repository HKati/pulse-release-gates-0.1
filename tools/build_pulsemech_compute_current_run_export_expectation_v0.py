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
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Sequence

import jsonschema


TOOL_NAME = "build_pulsemech_compute_current_run_export_expectation_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_current_run_export_expectation_v0"
DOCUMENT_TYPE = "pulsemech_compute_current_run_export_expectation"

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
        "release_authority_v0.json",
        "pulse_gate_policy_v0.yml",
        "pulse_gate_registry_v0.yml",
        "pulsemech_compute_current_run_export_expectation_v0.schema.json",
        "pulsemech_compute_subject_input_packet_v0.json",
        "pulsemech_compute_subject_input_packet_v0.schema.json",
    }
)


POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES = (
    Path("/usr/bin/git"),
    Path("/usr/local/bin/git"),
    Path("/opt/local/bin/git"),
)
WINDOWS_CURRENT_VERSION_REGISTRY_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
)
WINDOWS_PROGRAM_FILES_REGISTRY_VALUES = (
    "ProgramFilesDir",
    "ProgramFilesDir (x86)",
)
WINDOWS_GIT_RELATIVE_EXECUTABLES = (
    PureWindowsPath("Git/cmd/git.exe"),
    PureWindowsPath("Git/bin/git.exe"),
)

GIT_ENV_ALLOWLIST = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
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
    file_flags |= int(getattr(os, "O_BINARY", 0))

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
    flags |= int(getattr(os, "O_BINARY", 0))
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


def _dedupe_windows_paths(
    values: Iterable[PureWindowsPath],
) -> tuple[PureWindowsPath, ...]:
    result: list[PureWindowsPath] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).rstrip("\\/").casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _windows_system_directory() -> PureWindowsPath:
    if os.name != "nt":
        raise BuilderError("windows_system_directory_unavailable: not_windows")
    try:
        import ctypes

        buffer_size = 32768
        buffer = ctypes.create_unicode_buffer(buffer_size)
        length = ctypes.windll.kernel32.GetSystemWindowsDirectoryW(
            buffer,
            buffer_size,
        )
    except Exception as exc:
        raise BuilderError(
            f"windows_system_directory_unavailable: {exc}",
            exit_kind="trusted_git_error",
            exit_code=2,
        ) from exc
    if length <= 0 or length >= buffer_size:
        raise BuilderError(
            "windows_system_directory_unavailable: "
            f"invalid_length={length}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    directory = PureWindowsPath(buffer.value)
    if not directory.is_absolute() or not directory.drive or not directory.root:
        raise BuilderError(
            f"windows_system_directory_invalid: {str(directory)!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )
    return directory


def _windows_registry_program_files_roots() -> tuple[PureWindowsPath, ...]:
    if os.name != "nt":
        return ()
    try:
        import winreg
    except ImportError:
        return ()

    views: list[int] = [winreg.KEY_READ]
    for flag_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        flag = getattr(winreg, flag_name, 0)
        access = winreg.KEY_READ | flag
        if access not in views:
            views.append(access)

    roots: list[PureWindowsPath] = []
    accepted_types = {winreg.REG_SZ, winreg.REG_EXPAND_SZ}
    for access in views:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                WINDOWS_CURRENT_VERSION_REGISTRY_KEY,
                0,
                access,
            )
        except OSError:
            continue
        with key:
            for value_name in WINDOWS_PROGRAM_FILES_REGISTRY_VALUES:
                try:
                    raw_value, value_type = winreg.QueryValueEx(key, value_name)
                except OSError:
                    continue
                if (
                    value_type not in accepted_types
                    or not isinstance(raw_value, str)
                ):
                    continue
                value = raw_value.strip()
                if not value or "%" in value:
                    continue
                candidate = PureWindowsPath(value)
                if (
                    candidate.is_absolute()
                    and candidate.drive
                    and candidate.root
                ):
                    roots.append(candidate)
    return _dedupe_windows_paths(roots)


def _windows_trusted_git_candidate_strings(
    *,
    system_windows_directory: str,
    registry_program_files_roots: Iterable[str] = (),
) -> tuple[str, ...]:
    system_directory = PureWindowsPath(system_windows_directory)
    if (
        not system_directory.is_absolute()
        or not system_directory.drive
        or not system_directory.root
    ):
        raise BuilderError(
            f"windows_system_directory_invalid: {system_windows_directory!r}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    roots: list[PureWindowsPath] = []
    for value in registry_program_files_roots:
        root = PureWindowsPath(value)
        if root.is_absolute() and root.drive and root.root and "%" not in value:
            roots.append(root)
    system_drive_root = PureWindowsPath(system_directory.anchor)
    roots.extend(
        (
            system_drive_root / "Program Files",
            system_drive_root / "Program Files (x86)",
        )
    )

    candidates: list[PureWindowsPath] = []
    for root in _dedupe_windows_paths(roots):
        candidates.extend(
            root / relative for relative in WINDOWS_GIT_RELATIVE_EXECUTABLES
        )
    return tuple(str(value) for value in _dedupe_windows_paths(candidates))


def _trusted_git_candidates() -> tuple[Path, ...]:
    if os.name != "nt":
        return POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    system_directory = _windows_system_directory()
    registry_roots = _windows_registry_program_files_roots()
    return tuple(
        Path(value)
        for value in _windows_trusted_git_candidate_strings(
            system_windows_directory=str(system_directory),
            registry_program_files_roots=(str(root) for root in registry_roots),
        )
    )


def _validated_trusted_git(path: Path) -> Path:
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
        if os.name != "nt" and metadata.st_mode & (
            stat.S_IWGRP | stat.S_IWOTH
        ):
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


def _git_blob(
    *,
    git_path: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    label: str,
) -> bytes:
    canonical = _canonical_repository_path(repository_path)
    if canonical is None:
        raise BuilderError(
            f"{label}_repository_path_not_canonical: {repository_path!r}"
        )
    return _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("cat-file", "blob", f"{revision}:{canonical}"),
        label=label,
    )


def _verify_committed_worktree_file(
    *,
    git_path: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    label: str,
    max_bytes: int,
) -> bytes:
    committed = _git_blob(
        git_path=git_path,
        repository_root=repository_root,
        revision=revision,
        repository_path=repository_path,
        label=f"{label}_committed_blob",
    )
    if len(committed) > max_bytes:
        raise BuilderError(
            f"{label}_committed_blob_too_large: "
            f"size={len(committed)} maximum={max_bytes}"
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


def _verify_authority_sources(
    *,
    git_path: Path,
    subject_root: Path,
    subject_revision: str,
    authority_sources: dict[str, Any],
) -> dict[str, Any]:
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
        committed = _verify_committed_worktree_file(
            git_path=git_path,
            repository_root=subject_root,
            revision=subject_revision,
            repository_path=canonical,
            label=f"authority_source_{label}",
            max_bytes=MAX_COMPONENT_BYTES,
        )
        observed_sha = sha256_bytes(committed)
        if source.get("sha256") != observed_sha:
            raise BuilderError(
                f"{label}_source_sha256_mismatch: "
                f"expected={source.get('sha256')!r} observed={observed_sha!r}"
            )
        if source.get("size_bytes") != len(committed):
            raise BuilderError(
                f"{label}_source_size_mismatch: "
                f"expected={source.get('size_bytes')!r} "
                f"observed={len(committed)}"
            )
    if len(source_ids) != len(set(source_ids)):
        raise BuilderError("authority_source_ids_not_unique")
    return verified


def _load_hashed_json(
    *,
    path: Path,
    expected_sha256: str,
    label: str,
    object_required: bool,
) -> Any:
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
    }
    for field, expected_value in expected.items():
        actual = subject.get(field)
        if actual != expected_value:
            raise BuilderError(
                f"trusted_current_run_{field}_mismatch: "
                f"expected={expected_value!r} actual={actual!r}"
            )


def _verify_subject_artifacts(
    *,
    subject: dict[str, Any],
    final_status_path: Path,
    release_decision_path: Path,
    materialized_gate_set_path: Path | None,
) -> None:
    final_status = _load_hashed_json(
        path=final_status_path,
        expected_sha256=subject["final_status_sha256"],
        label="final_status",
        object_required=True,
    )
    metrics = final_status.get("metrics")
    if (
        not isinstance(metrics, dict)
        or metrics.get("run_mode") != subject.get("run_mode")
    ):
        raise BuilderError("final_status_run_mode_mismatch")
    decision = _load_hashed_json(
        path=release_decision_path,
        expected_sha256=subject["release_decision_sha256"],
        label="release_decision",
        object_required=True,
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
        _load_hashed_json(
            path=materialized_gate_set_path,
            expected_sha256=materialized_sha,
            label="materialized_gate_set",
            object_required=False,
        )

    release_level = decision.get("release_level")
    if release_level not in {"FAIL", "STAGE-PASS", "PROD-PASS"}:
        raise BuilderError(
            f"release_decision_level_unsupported: {release_level!r}"
        )
    expected_decision = "BLOCK" if release_level == "FAIL" else "ALLOW"
    if subject.get("decision") != expected_decision:
        raise BuilderError(
            f"subject_decision_mismatch: expected={expected_decision!r} "
            f"actual={subject.get('decision')!r}"
        )
    if decision.get("required_gates_passed") is not (
        expected_decision == "ALLOW"
    ):
        raise BuilderError("release_decision_required_gates_passed_mismatch")
    target = decision.get("target")
    if isinstance(target, str) and subject.get("run_mode") != target:
        raise BuilderError(
            "release_decision_target_mismatch: "
            f"subject={subject.get('run_mode')!r} decision={target!r}"
        )
    active_sets = decision.get("active_gate_sets")
    if isinstance(active_sets, list) and active_sets != subject.get(
        "active_policy_sets"
    ):
        raise BuilderError("release_decision_active_gate_sets_mismatch")

    optional_equalities = (
        ("git_sha", subject.get("source_commit")),
        ("status_sha256", subject.get("final_status_sha256")),
        ("policy_sha256", subject.get("policy_sha256")),
    )
    for field, expected in optional_equalities:
        actual = decision.get(field)
        if actual is not None and actual != expected:
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
    if candidate.name in PROTECTED_OUTPUT_NAMES:
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
            "and a separate protected control-plane checkout."
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
            "Optional approved absolute Git executable. When omitted, the "
            "builder selects the first available protected system candidate."
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

    verified_sources = _verify_authority_sources(
        git_path=trusted_git,
        subject_root=subject_root,
        subject_revision=subject_revision,
        authority_sources=builder_input["authority_sources"],
    )
    _verify_subject_artifacts(
        subject=subject,
        final_status_path=final_status_path,
        release_decision_path=release_decision_path,
        materialized_gate_set_path=materialized_gate_set_path,
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
