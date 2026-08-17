#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"document_type":"pulsemech_compute_current_run_export_carrier",'
    '"errors":["isolated_python_runtime_required: launch with python -I"],'
    '"exit_kind":"python_runtime_boundary_error",'
    '"ok":false,'
    '"tool":"load_pulsemech_compute_current_run_export_carrier_v0",'
    '"tool_version":"0.1.0"}\n'
)

if __name__ == "__main__" and (
    sys.flags.isolated != 1
    or sys.flags.ignore_environment != 1
    or sys.flags.no_user_site != 1
    or not bool(getattr(sys.flags, "safe_path", False))
):
    sys.stderr.write(_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC)
    raise SystemExit(2)

import argparse
import hashlib
import json
import os
import re
import secrets
import selectors
import stat
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence


TOOL_NAME = "load_pulsemech_compute_current_run_export_carrier_v0"
TOOL_VERSION = "0.1.0"
DOCUMENT_TYPE = "pulsemech_compute_current_run_export_carrier"

PRODUCER_SOURCE_PATH = (
    "tools/load_pulsemech_compute_current_run_export_carrier_v0.py"
)
PRODUCER_ID = "producer:pulsemech-current-run-export-carrier-loader-v0"
PRODUCER_NAME = "PULSEmech current-run export carrier loader"
PRODUCTION_MODE = "current_run_export_carrier_builder"

CARRIER_KIND = "current_run_export_archive"
PATH_BASE = "current_run_export_staging_root"
MEDIA_TYPE = "application/zip"
ARTIFACT_PAYLOAD_MODE = "external_carrier"

SUPPORTED_EXECUTION_PLATFORM = "linux"
SUPPORTED_OS_NAME = "posix"
EXECUTION_PROFILE = "protected_linux_hpc_control_plane"

ROOT = Path(__file__).resolve().parents[1]

HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_CARRIER_BYTES = 8 * 1024 * 1024 * 1024
MAX_PRODUCER_SOURCE_BYTES = 4 * 1024 * 1024
MAX_GIT_CONFIG_BYTES = 1024 * 1024
MAX_GIT_DIAGNOSTIC_BYTES = 64 * 1024
GIT_CAPTURE_CHUNK_BYTES = 64 * 1024
MAX_PROC_PIDS = 131072
MAX_SAME_USER_PROC_FDS = 131072

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

GIT_LOCAL_ONLY_COMMAND_CONFIG = (
    ("core.fsmonitor", "false"),
    ("core.sshCommand", "/bin/false"),
    ("credential.helper", ""),
    ("credential.interactive", "false"),
    ("protocol.allow", "never"),
    ("protocol.ext.allow", "never"),
    ("protocol.file.allow", "never"),
    ("protocol.git.allow", "never"),
    ("protocol.http.allow", "never"),
    ("protocol.https.allow", "never"),
    ("protocol.ssh.allow", "never"),
)

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulse_gate_policy_v0.yml",
        "pulse_gate_registry_v0.yml",
        "pulsemech_compute_current_run_export_carrier_v0.json",
        "pulsemech_compute_current_run_export_expectation_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    }
)
PROTECTED_OUTPUT_NAMES_CASEFOLDED = frozenset(
    name.casefold() for name in PROTECTED_OUTPUT_NAMES
)


class CarrierError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_kind: str = "carrier_error",
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.exit_code = exit_code


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


def _file_identity(value: os.stat_result) -> tuple[Any, ...]:
    return tuple(
        getattr(value, name, None)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    )


def _inode_identity(value: os.stat_result) -> tuple[Any, Any]:
    return (getattr(value, "st_dev", None), getattr(value, "st_ino", None))


def _directory_identity(value: os.stat_result) -> tuple[Any, ...]:
    return tuple(
        getattr(value, name, None)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
        )
    )


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


def _paths_overlap(left: Path, right: Path) -> bool:
    return (
        same_target(left, right)
        or path_is_within(left, right)
        or path_is_within(right, left)
    )


def _require_supported_execution_platform() -> None:
    if (
        sys.platform != SUPPORTED_EXECUTION_PLATFORM
        or os.name != SUPPORTED_OS_NAME
    ):
        raise CarrierError(
            "unsupported_execution_platform: "
            f"profile={EXECUTION_PROFILE!r} "
            f"required_sys_platform={SUPPORTED_EXECUTION_PLATFORM!r} "
            f"required_os_name={SUPPORTED_OS_NAME!r} "
            f"observed_sys_platform={sys.platform!r} "
            f"observed_os_name={os.name!r}",
            exit_kind="platform_boundary_error",
        )

    required_capabilities = (
        os.open in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.rename in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.link in os.supports_dir_fd,
        os.link in os.supports_follow_symlinks,
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
    )
    if not all(required_capabilities):
        raise CarrierError(
            "protected_descriptor_profile_unavailable",
            exit_kind="platform_boundary_error",
        )


def _non_empty_text(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise CarrierError(
            f"{label}_invalid: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _canonical_sha40(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise CarrierError(
            f"{label}_not_canonical_sha40: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _canonical_member_path(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or "\x00" in value
    ):
        raise CarrierError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    pure = PurePosixPath(value)
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise CarrierError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    canonical = pure.as_posix()
    if canonical != value:
        raise CarrierError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    return canonical


def _canonical_directory_prefix(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("/"):
        raise CarrierError(
            f"{label}_not_canonical_directory_prefix: {value!r}",
            exit_kind="input_boundary_error",
        )
    base = _canonical_member_path(value[:-1], label=label)
    return base + "/"


def _canonical_carrier_id_namespace(value: Any) -> str:
    value = _non_empty_text(value, label="carrier_id_namespace")
    parts = value.split("/")
    if any(
        not part
        or re.fullmatch(r"[A-Za-z0-9._:@+-]+", part) is None
        for part in parts
    ):
        raise CarrierError(
            f"carrier_id_namespace_not_canonical: {value!r}",
            exit_kind="input_boundary_error",
        )
    return "/".join(parts)


def _parse_utc(value: Any, *, label: str) -> datetime:
    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
            r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            value,
        )
        is None
    ):
        raise CarrierError(
            f"{label}_not_canonical_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CarrierError(
            f"{label}_invalid_datetime: {value!r}",
            exit_kind="input_boundary_error",
        ) from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != timezone.utc.utcoffset(parsed)
    ):
        raise CarrierError(
            f"{label}_not_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    return parsed


def _positive_int(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _slug(value: str) -> str:
    chars: list[str] = []
    dash = False
    for char in value:
        if char.isascii() and (char.isalnum() or char in "._+"):
            chars.append(char.lower())
            dash = False
        elif not dash:
            chars.append("-")
            dash = True
    result = "".join(chars).strip("-")
    if not result:
        raise CarrierError(
            f"workflow_identity_slug_empty: {value!r}",
            exit_kind="input_boundary_error",
        )
    return result


def _subject_run_key(
    *,
    workflow_run_id: int,
    workflow_run_attempt: int,
    workflow_name: str,
) -> str:
    return (
        f"GITHUB_RUN_ID={workflow_run_id}"
        f"|GITHUB_RUN_ATTEMPT={workflow_run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
    )


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | int(getattr(os, "O_DIRECTORY", 0))
        | int(getattr(os, "O_CLOEXEC", 0))
        | int(getattr(os, "O_NOFOLLOW", 0))
    )


def _read_flags() -> int:
    return (
        os.O_RDONLY
        | int(getattr(os, "O_CLOEXEC", 0))
        | int(getattr(os, "O_NOFOLLOW", 0))
    )


def _proc_fd_access_mode(fdinfo_path: Path) -> int:
    try:
        text = fdinfo_path.read_text(encoding="ascii", errors="strict")
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise CarrierError(
            f"carrier_open_writer_fdinfo_unavailable: {fdinfo_path}: {exc}",
            exit_kind="carrier_boundary_error",
        ) from exc
    for line in text.splitlines():
        if not line.startswith("flags:"):
            continue
        raw = line.split(":", 1)[1].strip()
        try:
            return int(raw, 8) & os.O_ACCMODE
        except ValueError as exc:
            raise CarrierError(
                f"carrier_open_writer_flags_invalid: "
                f"path={fdinfo_path} flags={raw!r}",
                exit_kind="carrier_boundary_error",
            ) from exc
    raise CarrierError(
        f"carrier_open_writer_flags_missing: {fdinfo_path}",
        exit_kind="carrier_boundary_error",
    )


def _assert_no_same_user_writable_open_handle(
    carrier_identity: tuple[Any, ...],
) -> None:
    proc_root = Path("/proc")
    try:
        proc_metadata = proc_root.stat()
    except OSError as exc:
        raise CarrierError(
            f"carrier_open_writer_scan_unavailable: {exc}",
            exit_kind="carrier_boundary_error",
        ) from exc
    if not stat.S_ISDIR(proc_metadata.st_mode):
        raise CarrierError(
            "carrier_open_writer_scan_unavailable: /proc is not a directory",
            exit_kind="carrier_boundary_error",
        )

    carrier_device = carrier_identity[0]
    carrier_inode = carrier_identity[1]
    effective_uid = os.geteuid()
    observed_fd_count = 0

    process_entries: list[Path] = []
    try:
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            process_entries.append(entry)
            if len(process_entries) > MAX_PROC_PIDS:
                raise CarrierError(
                    "carrier_open_writer_process_scan_limit_exceeded: "
                    f"observed>{MAX_PROC_PIDS}",
                    exit_kind="carrier_boundary_error",
                )
    except CarrierError:
        raise
    except OSError as exc:
        raise CarrierError(
            f"carrier_open_writer_process_scan_failed: {exc}",
            exit_kind="carrier_boundary_error",
        ) from exc
    process_entries.sort(key=lambda entry: int(entry.name))

    for process_path in process_entries:
        try:
            process_metadata = process_path.stat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CarrierError(
                f"carrier_open_writer_process_stat_failed: "
                f"path={process_path} error={exc}",
                exit_kind="carrier_boundary_error",
            ) from exc
        if process_metadata.st_uid != effective_uid:
            continue

        fd_directory = process_path / "fd"
        fd_entries: list[Path] = []
        try:
            for fd_path in fd_directory.iterdir():
                if not fd_path.name.isdigit():
                    continue
                observed_fd_count += 1
                if observed_fd_count > MAX_SAME_USER_PROC_FDS:
                    raise CarrierError(
                        "carrier_open_writer_scan_limit_exceeded: "
                        f"observed>{MAX_SAME_USER_PROC_FDS}",
                        exit_kind="carrier_boundary_error",
                    )
                fd_entries.append(fd_path)
        except FileNotFoundError:
            continue
        except CarrierError:
            raise
        except PermissionError as exc:
            raise CarrierError(
                f"carrier_open_writer_same_user_fd_scan_denied: "
                f"path={fd_directory} error={exc}",
                exit_kind="carrier_boundary_error",
            ) from exc
        except OSError as exc:
            raise CarrierError(
                f"carrier_open_writer_fd_scan_failed: "
                f"path={fd_directory} error={exc}",
                exit_kind="carrier_boundary_error",
            ) from exc
        fd_entries.sort(key=lambda entry: int(entry.name))

        for fd_path in fd_entries:
            try:
                opened = fd_path.stat()
            except FileNotFoundError:
                continue
            except PermissionError as exc:
                raise CarrierError(
                    f"carrier_open_writer_same_user_fd_stat_denied: "
                    f"path={fd_path} error={exc}",
                    exit_kind="carrier_boundary_error",
                ) from exc
            except OSError:
                # Descriptor tables change concurrently. A vanished entry is
                # ignored; a surviving carrier-bound entry is checked below.
                continue
            if opened.st_dev != carrier_device or opened.st_ino != carrier_inode:
                continue

            try:
                access_mode = _proc_fd_access_mode(
                    process_path / "fdinfo" / fd_path.name
                )
            except FileNotFoundError:
                continue
            if access_mode in {os.O_WRONLY, os.O_RDWR}:
                raise CarrierError(
                    "carrier_open_for_writing: "
                    f"pid={process_path.name} fd={fd_path.name}",
                    exit_kind="carrier_boundary_error",
                )


@dataclass
class DirectoryChain:
    absolute_path: Path
    label: str
    fds: list[int] = field(default_factory=list)
    link_names: list[str] = field(default_factory=list)
    identities: list[tuple[Any, ...]] = field(default_factory=list)
    _closed: bool = False

    @classmethod
    def open(cls, path: Path, *, label: str) -> "DirectoryChain":
        candidate = _normalized_absolute_path(path)
        if not candidate.is_absolute() or not candidate.parts:
            raise CarrierError(
                f"{label}_path_not_absolute: {candidate}",
                exit_kind="input_boundary_error",
            )

        chain = cls(absolute_path=candidate, label=label)
        try:
            root_fd = os.open(candidate.parts[0], _directory_flags())
            root_metadata = os.fstat(root_fd)
            if not stat.S_ISDIR(root_metadata.st_mode):
                raise CarrierError(
                    f"{label}_root_not_directory: {candidate.parts[0]}",
                    exit_kind="input_boundary_error",
                )
            chain.fds.append(root_fd)
            chain.identities.append(_directory_identity(root_metadata))

            for part in candidate.parts[1:]:
                chain.open_child(part)
            chain.verify()
            return chain
        except Exception:
            chain.close()
            raise

    @property
    def final_fd(self) -> int:
        if self._closed or not self.fds:
            raise CarrierError(
                f"{self.label}_directory_chain_closed",
                exit_kind="input_boundary_error",
            )
        return self.fds[-1]

    def open_child(self, name: str) -> None:
        if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or "\x00" in name
        ):
            raise CarrierError(
                f"{self.label}_directory_component_invalid: {name!r}",
                exit_kind="input_boundary_error",
            )
        try:
            child_fd = os.open(name, _directory_flags(), dir_fd=self.final_fd)
        except OSError as exc:
            raise CarrierError(
                f"{self.label}_directory_component_open_failed: "
                f"component={name!r} error={exc}",
                exit_kind="input_boundary_error",
            ) from exc
        try:
            metadata = os.fstat(child_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                raise CarrierError(
                    f"{self.label}_component_not_directory: {name!r}",
                    exit_kind="input_boundary_error",
                )
        except Exception:
            os.close(child_fd)
            raise
        self.link_names.append(name)
        self.fds.append(child_fd)
        self.identities.append(_directory_identity(metadata))

    def verify(self) -> None:
        if self._closed:
            raise CarrierError(
                f"{self.label}_directory_chain_closed",
                exit_kind="input_boundary_error",
            )
        if len(self.fds) != len(self.identities):
            raise CarrierError(
                f"{self.label}_directory_chain_internal_mismatch",
                exit_kind="input_boundary_error",
            )
        if len(self.link_names) != max(0, len(self.fds) - 1):
            raise CarrierError(
                f"{self.label}_directory_chain_link_mismatch",
                exit_kind="input_boundary_error",
            )

        for index, descriptor in enumerate(self.fds):
            current = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(current.st_mode)
                or _directory_identity(current) != self.identities[index]
            ):
                raise CarrierError(
                    f"{self.label}_directory_identity_changed: index={index}",
                    exit_kind="input_boundary_error",
                )

        for index, name in enumerate(self.link_names):
            try:
                observed = os.stat(
                    name,
                    dir_fd=self.fds[index],
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise CarrierError(
                    f"{self.label}_directory_link_unavailable: "
                    f"component={name!r} error={exc}",
                    exit_kind="input_boundary_error",
                ) from exc
            if (
                not stat.S_ISDIR(observed.st_mode)
                or _directory_identity(observed) != self.identities[index + 1]
            ):
                raise CarrierError(
                    f"{self.label}_directory_link_changed: component={name!r}",
                    exit_kind="input_boundary_error",
                )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for descriptor in reversed(self.fds):
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.fds.clear()
        self.link_names.clear()
        self.identities.clear()

    def __enter__(self) -> "DirectoryChain":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()


def _read_descriptor_bytes(
    descriptor: int,
    *,
    label: str,
    max_bytes: int,
    expected_size: int | None = None,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(HASH_CHUNK_BYTES, max_bytes + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise CarrierError(
                f"{label}_too_large_during_read: size>{max_bytes}",
                exit_kind="input_boundary_error",
            )
        chunks.append(chunk)
    payload = b"".join(chunks)
    if expected_size is not None and len(payload) != expected_size:
        raise CarrierError(
            f"{label}_size_changed_during_read: "
            f"expected={expected_size} actual={len(payload)}",
            exit_kind="input_boundary_error",
        )
    return payload


def read_regular_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    candidate = _normalized_absolute_path(path)
    if candidate == candidate.parent or not candidate.name:
        raise CarrierError(
            f"{label}_path_has_no_leaf: {candidate}",
            exit_kind="input_boundary_error",
        )

    with DirectoryChain.open(candidate.parent, label=f"{label}_parent") as chain:
        try:
            descriptor = os.open(candidate.name, _read_flags(), dir_fd=chain.final_fd)
        except OSError as exc:
            raise CarrierError(
                f"{label}_open_failed: {candidate}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise CarrierError(
                    f"{label}_not_regular_file: {candidate}",
                    exit_kind="input_boundary_error",
                )
            if before.st_size < 0 or before.st_size > max_bytes:
                raise CarrierError(
                    f"{label}_too_large: "
                    f"size={before.st_size} maximum={max_bytes}",
                    exit_kind="input_boundary_error",
                )
            payload = _read_descriptor_bytes(
                descriptor,
                label=label,
                max_bytes=max_bytes,
                expected_size=before.st_size,
            )
            after = os.fstat(descriptor)
            if _file_identity(after) != _file_identity(before):
                raise CarrierError(
                    f"{label}_changed_during_read: {candidate}",
                    exit_kind="input_boundary_error",
                )
            chain.verify()
            observed = os.stat(
                candidate.name,
                dir_fd=chain.final_fd,
                follow_symlinks=False,
            )
            if _file_identity(observed) != _file_identity(before):
                raise CarrierError(
                    f"{label}_path_binding_changed: {candidate}",
                    exit_kind="input_boundary_error",
                )
            return payload
        finally:
            os.close(descriptor)


@dataclass
class OpenedCarrier:
    staging_root: Path
    staged_relative_path: str
    max_bytes: int
    chain: DirectoryChain
    file_fd: int
    leaf_name: str
    identity: tuple[Any, ...]
    digest: str | None = None
    size_bytes: int | None = None
    _closed: bool = False

    @classmethod
    def open(
        cls,
        *,
        staging_root: Path,
        staged_relative_path: str,
        max_bytes: int,
    ) -> "OpenedCarrier":
        root = _normalized_absolute_path(staging_root)
        parts = PurePosixPath(staged_relative_path).parts
        if not parts:
            raise CarrierError(
                "staged_relative_path_has_no_leaf",
                exit_kind="carrier_boundary_error",
            )
        if not parts[-1].endswith(".zip"):
            raise CarrierError(
                "carrier_leaf_must_end_with_lowercase_zip: " + repr(parts[-1]),
                exit_kind="carrier_boundary_error",
            )

        chain = DirectoryChain.open(root, label="staging_root")
        descriptor: int | None = None
        try:
            for part in parts[:-1]:
                chain.open_child(part)
            leaf = parts[-1]
            try:
                descriptor = os.open(leaf, _read_flags(), dir_fd=chain.final_fd)
            except OSError as exc:
                raise CarrierError(
                    f"carrier_open_failed: path={staged_relative_path!r} "
                    f"error={exc}",
                    exit_kind="carrier_boundary_error",
                ) from exc

            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise CarrierError(
                    "carrier_not_regular_file",
                    exit_kind="carrier_boundary_error",
                )
            if metadata.st_size <= 0:
                raise CarrierError(
                    f"carrier_empty: size={metadata.st_size}",
                    exit_kind="carrier_boundary_error",
                )
            if metadata.st_size > max_bytes:
                raise CarrierError(
                    f"carrier_too_large: size={metadata.st_size} maximum={max_bytes}",
                    exit_kind="carrier_boundary_error",
                )
            if metadata.st_nlink != 1:
                raise CarrierError(
                    f"carrier_hardlink_count_rejected: nlink={metadata.st_nlink}",
                    exit_kind="carrier_boundary_error",
                )
            if metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                raise CarrierError(
                    "carrier_not_finalized_read_only: write_bits_present",
                    exit_kind="carrier_boundary_error",
                )

            identity = _file_identity(metadata)
            _assert_no_same_user_writable_open_handle(identity)
            opened = cls(
                staging_root=root,
                staged_relative_path=staged_relative_path,
                max_bytes=max_bytes,
                chain=chain,
                file_fd=descriptor,
                leaf_name=leaf,
                identity=identity,
            )
            descriptor = None
            opened.verify_unchanged()
            return opened
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            chain.close()
            raise

    @property
    def path(self) -> Path:
        return self.staging_root / PurePosixPath(self.staged_relative_path)

    def verify_unchanged(self) -> None:
        if self._closed:
            raise CarrierError(
                "carrier_snapshot_closed",
                exit_kind="carrier_boundary_error",
            )
        current = os.fstat(self.file_fd)
        if _file_identity(current) != self.identity:
            raise CarrierError(
                "carrier_identity_changed_after_open",
                exit_kind="carrier_boundary_error",
            )
        self.chain.verify()
        try:
            observed = os.stat(
                self.leaf_name,
                dir_fd=self.chain.final_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise CarrierError(
                f"carrier_path_binding_unavailable: {exc}",
                exit_kind="carrier_boundary_error",
            ) from exc
        if _file_identity(observed) != self.identity:
            raise CarrierError(
                "carrier_path_binding_changed",
                exit_kind="carrier_boundary_error",
            )
        _assert_no_same_user_writable_open_handle(self.identity)

    def hash_once(self) -> tuple[str, int]:
        if self.digest is not None or self.size_bytes is not None:
            raise CarrierError(
                "carrier_digest_already_materialized",
                exit_kind="carrier_boundary_error",
            )
        self.verify_unchanged()
        os.lseek(self.file_fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(self.file_fd, HASH_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > self.max_bytes:
                raise CarrierError(
                    f"carrier_too_large_during_hash: size>{self.max_bytes}",
                    exit_kind="carrier_boundary_error",
                )
            digest.update(chunk)

        expected_size = int(self.identity[6])
        if total != expected_size:
            raise CarrierError(
                f"carrier_size_changed_during_hash: "
                f"expected={expected_size} actual={total}",
                exit_kind="carrier_boundary_error",
            )
        self.verify_unchanged()
        self.digest = digest.hexdigest()
        self.size_bytes = total
        return self.digest, self.size_bytes

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self.file_fd)
        except OSError:
            pass
        self.chain.close()

    def __enter__(self) -> "OpenedCarrier":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()


def _validated_trusted_git(path: Path) -> Path:
    _require_supported_execution_platform()
    if not path.is_absolute():
        raise CarrierError(
            f"trusted_git_not_absolute: {path}",
            exit_kind="trusted_git_error",
        )
    candidate = _normalized_absolute_path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CarrierError(
            f"trusted_git_unresolvable: {candidate}: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if os.path.normcase(str(candidate)) != os.path.normcase(str(resolved)):
        raise CarrierError(
            f"trusted_git_alias_rejected: supplied={candidate} resolved={resolved}",
            exit_kind="trusted_git_error",
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
            raise CarrierError(
                f"trusted_git_component_unavailable: {component}: {exc}",
                exit_kind="trusted_git_error",
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise CarrierError(
                f"trusted_git_symlink_component_rejected: {component}",
                exit_kind="trusted_git_error",
            )
        if component == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise CarrierError(
                    f"trusted_git_not_regular_file: {component}",
                    exit_kind="trusted_git_error",
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise CarrierError(
                f"trusted_git_parent_not_directory: {component}",
                exit_kind="trusted_git_error",
            )
        if metadata.st_uid != 0:
            raise CarrierError(
                "trusted_git_unprotected_owner_rejected: "
                f"component={component} uid={metadata.st_uid}",
                exit_kind="trusted_git_error",
            )
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise CarrierError(
                f"trusted_git_writable_component_rejected: {component}",
                exit_kind="trusted_git_error",
            )

    if not os.access(resolved, os.X_OK):
        raise CarrierError(
            f"trusted_git_not_executable: {resolved}",
            exit_kind="trusted_git_error",
        )

    approved = {
        os.path.normcase(str(_normalized_absolute_path(candidate_path)))
        for candidate_path in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    }
    if os.path.normcase(str(resolved)) not in approved:
        raise CarrierError(
            f"trusted_git_unapproved_candidate: {resolved}",
            exit_kind="trusted_git_error",
        )
    return resolved


def _select_trusted_git(explicit: str | None) -> Path:
    if explicit is not None:
        return _validated_trusted_git(Path(explicit))
    unavailable: list[str] = []
    untrusted: list[str] = []
    for candidate in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES:
        if not candidate.exists():
            unavailable.append(str(candidate))
            continue
        try:
            return _validated_trusted_git(candidate)
        except CarrierError as exc:
            untrusted.append(str(exc))
    raise CarrierError(
        "trusted_git_unavailable: "
        + json.dumps(
            {"unavailable": unavailable, "untrusted": untrusted},
            sort_keys=True,
        ),
        exit_kind="trusted_git_error",
    )


def _git_environment(git_path: Path) -> dict[str, str]:
    environment = {
        key: value
        for key in GIT_ENV_ALLOWLIST
        if (value := os.environ.get(key)) is not None
    }
    environment.update(
        {
            "GIT_ALLOW_PROTOCOL": "",
            "GIT_ASKPASS": "/bin/false",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PROTOCOL_FROM_USER": "0",
            "GIT_SSH_COMMAND": "/bin/false",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": str(git_path.parent),
            "SSH_ASKPASS": "/bin/false",
        }
    )
    return environment


def _local_only_git_command_config_arguments() -> list[str]:
    arguments: list[str] = []
    for key, value in GIT_LOCAL_ONLY_COMMAND_CONFIG:
        arguments.extend(("-c", f"{key}={value}"))
    return arguments


def _git_command(
    *,
    git_path: Path,
    repository_root: Path,
    arguments: Sequence[str],
) -> list[str]:
    return [
        str(git_path),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
        *_local_only_git_command_config_arguments(),
        "-c",
        f"safe.directory={repository_root}",
        "-C",
        str(repository_root),
        *arguments,
    ]


def _terminate_subprocess(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def _run_bounded_command(
    *,
    command: Sequence[str],
    environment: dict[str, str],
    label: str,
    max_stdout_bytes: int,
    max_stderr_bytes: int = MAX_GIT_DIAGNOSTIC_BYTES,
    timeout_seconds: int = 60,
) -> bytes:
    if max_stdout_bytes < 0 or max_stderr_bytes < 0:
        raise CarrierError(
            f"{label}_capture_limit_invalid: "
            f"stdout={max_stdout_bytes} stderr={max_stderr_bytes}",
            exit_kind="trusted_git_error",
        )

    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            bufsize=0,
            close_fds=True,
        )
        if process.stdout is None or process.stderr is None:
            raise CarrierError(
                f"{label}_capture_pipe_unavailable",
                exit_kind="trusted_git_error",
            )

        os.set_blocking(process.stdout.fileno(), False)
        os.set_blocking(process.stderr.fileno(), False)
        selector.register(
            process.stdout,
            selectors.EVENT_READ,
            ("stdout", max_stdout_bytes),
        )
        selector.register(
            process.stderr,
            selectors.EVENT_READ,
            ("stderr", max_stderr_bytes),
        )
        deadline = time.monotonic() + timeout_seconds

        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_subprocess(process)
                raise CarrierError(
                    f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                    exit_kind="trusted_git_error",
                )
            events = selector.select(remaining)
            if not events:
                continue
            for key, _mask in events:
                stream_name, maximum = key.data
                buffer = buffers[stream_name]
                remaining_capacity = maximum - len(buffer)
                read_size = min(
                    GIT_CAPTURE_CHUNK_BYTES,
                    max(1, remaining_capacity + 1),
                )
                try:
                    chunk = os.read(key.fileobj.fileno(), read_size)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                buffer.extend(chunk)
                if len(buffer) > maximum:
                    _terminate_subprocess(process)
                    raise CarrierError(
                        f"{label}_{stream_name}_capture_limit_exceeded: "
                        f"observed_at_least={len(buffer)} maximum={maximum}",
                        exit_kind="trusted_git_error",
                    )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_subprocess(process)
            raise CarrierError(
                f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                exit_kind="trusted_git_error",
            )
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _terminate_subprocess(process)
            raise CarrierError(
                f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                exit_kind="trusted_git_error",
            ) from exc

        stdout = bytes(buffers["stdout"])
        stderr = bytes(buffers["stderr"])
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise CarrierError(
                f"{label}_failed: returncode={returncode} detail={detail!r}",
                exit_kind="trusted_git_error",
            )
        return stdout
    except CarrierError:
        if process is not None:
            _terminate_subprocess(process)
        raise
    except OSError as exc:
        if process is not None:
            _terminate_subprocess(process)
        raise CarrierError(
            f"{label}_execution_failed: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    finally:
        selector.close()
        if process is not None:
            for pipe in (process.stdout, process.stderr):
                if pipe is not None and not pipe.closed:
                    try:
                        pipe.close()
                    except OSError:
                        pass
            _terminate_subprocess(process)


def _run_git(
    *,
    git_path: Path,
    repository_root: Path,
    arguments: Sequence[str],
    label: str,
    max_stdout_bytes: int,
    timeout_seconds: int = 60,
) -> bytes:
    return _run_bounded_command(
        command=_git_command(
            git_path=git_path,
            repository_root=repository_root,
            arguments=arguments,
        ),
        environment=_git_environment(git_path),
        label=label,
        max_stdout_bytes=max_stdout_bytes,
        timeout_seconds=timeout_seconds,
    )


def _require_trusted_git_local_only_support(git_path: Path) -> None:
    output = _run_bounded_command(
        command=(
            str(git_path),
            "--no-pager",
            "--no-replace-objects",
            "--no-lazy-fetch",
            "--version",
        ),
        environment=_git_environment(git_path),
        label="trusted_git_local_only_capability_probe",
        max_stdout_bytes=4096,
        timeout_seconds=10,
    )
    if not output.startswith(b"git version "):
        raise CarrierError(
            "trusted_git_version_probe_invalid_output",
            exit_kind="trusted_git_error",
        )


def _decode_single_line(data: bytes, *, label: str) -> str:
    try:
        value = data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise CarrierError(
            f"{label}_invalid_utf8",
            exit_kind="trusted_git_error",
        ) from exc
    if not value or "\x00" in value or "\n" in value or "\r" in value:
        raise CarrierError(
            f"{label}_invalid_output: {value!r}",
            exit_kind="trusted_git_error",
        )
    return value


def _verify_git_repository(
    *,
    git_path: Path,
    repository_root: Path,
    expected_revision: str,
) -> None:
    top_level = Path(
        _decode_single_line(
            _run_git(
                git_path=git_path,
                repository_root=repository_root,
                arguments=("rev-parse", "--show-toplevel"),
                label="control_plane_top_level",
                max_stdout_bytes=64 * 1024,
            ),
            label="control_plane_top_level",
        )
    )
    if not same_target(top_level, repository_root):
        raise CarrierError(
            "control_plane_repository_root_mismatch: "
            f"expected={repository_root} observed={top_level}",
            exit_kind="trusted_git_error",
        )

    head = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "HEAD"),
            label="control_plane_head",
            max_stdout_bytes=4096,
        ),
        label="control_plane_head",
    ).lower()
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise CarrierError(
            f"control_plane_head_not_sha40: {head!r}",
            exit_kind="trusted_git_error",
        )
    if head != expected_revision:
        raise CarrierError(
            "control_plane_head_mismatch: "
            f"expected={expected_revision} observed={head}",
            exit_kind="trusted_git_error",
        )


def _decode_git_storage_path(
    raw: bytes,
    *,
    repository_root: Path,
    label: str,
) -> Path:
    value = _decode_single_line(raw, label=label)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    candidate = _normalized_absolute_path(candidate)
    with DirectoryChain.open(candidate, label=label):
        pass
    return candidate


def _parse_scoped_git_config(
    raw: bytes,
    *,
    label: str,
) -> list[tuple[str, str, str]]:
    if len(raw) > MAX_GIT_CONFIG_BYTES:
        raise CarrierError(
            f"{label}_git_config_too_large: "
            f"size={len(raw)} maximum={MAX_GIT_CONFIG_BYTES}",
            exit_kind="trusted_git_error",
        )
    parts = raw.split(b"\x00")
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) % 2 != 0:
        raise CarrierError(
            f"{label}_git_config_record_structure_invalid",
            exit_kind="trusted_git_error",
        )

    rows: list[tuple[str, str, str]] = []
    for index in range(0, len(parts), 2):
        scope_raw = parts[index]
        entry_raw = parts[index + 1]
        key_raw, separator, value_raw = entry_raw.partition(b"\n")
        if not separator or not key_raw:
            raise CarrierError(
                f"{label}_git_config_entry_invalid: index={index // 2}",
                exit_kind="trusted_git_error",
            )
        try:
            scope = scope_raw.decode("ascii", errors="strict")
            key = key_raw.decode("utf-8", errors="strict")
            value = value_raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise CarrierError(
                f"{label}_git_config_entry_encoding_invalid: index={index // 2}",
                exit_kind="trusted_git_error",
            ) from exc
        if scope not in {"system", "global", "local", "worktree", "command"}:
            raise CarrierError(
                f"{label}_git_config_scope_invalid: {scope!r}",
                exit_kind="trusted_git_error",
            )
        rows.append((scope, key, value))
    return rows


def _git_config_key_opens_remote_object_boundary(key: str) -> bool:
    normalized = key.casefold()
    return (
        normalized in {"core.sshcommand", "extensions.partialclone"}
        or re.fullmatch(r"remote\..+\.promisor", normalized) is not None
        or re.fullmatch(r"remote\..+\.partialclonefilter", normalized) is not None
    )


def _optional_git_path(
    *,
    git_path: Path,
    repository_root: Path,
    relative_name: str,
    label: str,
) -> Path:
    raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("rev-parse", "--git-path", relative_name),
        label=label,
        max_stdout_bytes=64 * 1024,
    )
    value = _decode_single_line(raw, label=label)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return _normalized_absolute_path(candidate)


def _reject_nonempty_optional_git_file(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CarrierError(
            f"{label}_unavailable: {path}: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise CarrierError(
            f"{label}_not_protected_regular_file: {path}",
            exit_kind="trusted_git_error",
        )
    payload = read_regular_file(path, label=label, max_bytes=1024 * 1024)
    if payload.strip():
        raise CarrierError(
            f"{label}_rejected: {path}",
            exit_kind="trusted_git_error",
        )


def _reject_git_promisor_pack_markers(object_store: Path) -> None:
    pack_directory = object_store / "pack"
    try:
        metadata = pack_directory.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise CarrierError(
            f"control_plane_git_pack_directory_unavailable: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise CarrierError(
            "control_plane_git_pack_directory_not_protected_directory",
            exit_kind="trusted_git_error",
        )
    with DirectoryChain.open(
        pack_directory,
        label="control_plane_git_pack_directory",
    ) as chain:
        try:
            with os.scandir(chain.final_fd) as entries:
                for entry in entries:
                    if entry.name.casefold().endswith(".promisor"):
                        raise CarrierError(
                            "control_plane_git_promisor_pack_marker_rejected",
                            exit_kind="trusted_git_error",
                        )
        except CarrierError:
            raise
        except OSError as exc:
            raise CarrierError(
                f"control_plane_git_pack_directory_scan_failed: {exc}",
                exit_kind="trusted_git_error",
            ) from exc


def _verify_git_local_only_repository_state(
    *,
    git_path: Path,
    repository_root: Path,
) -> None:
    object_store = _decode_git_storage_path(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-path", "objects"),
            label="control_plane_git_object_store",
            max_stdout_bytes=64 * 1024,
        ),
        repository_root=repository_root,
        label="control_plane_git_object_store",
    )

    config_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("config", "--null", "--show-scope", "--list"),
        label="control_plane_git_config",
        max_stdout_bytes=MAX_GIT_CONFIG_BYTES,
    )
    rejected = sorted(
        {
            f"{scope}:{key}"
            for scope, key, _value in _parse_scoped_git_config(
                config_raw,
                label="control_plane",
            )
            if scope in {"local", "worktree"}
            and _git_config_key_opens_remote_object_boundary(key)
        }
    )
    if rejected:
        raise CarrierError(
            "control_plane_git_local_only_config_rejected: "
            + json.dumps(rejected, ensure_ascii=False, sort_keys=True),
            exit_kind="trusted_git_error",
        )

    _reject_git_promisor_pack_markers(object_store)
    for relative_name, label in (
        ("objects/info/alternates", "control_plane_git_alternates"),
        ("objects/info/http-alternates", "control_plane_git_http_alternates"),
        ("shallow", "control_plane_git_shallow_boundary"),
    ):
        path = _optional_git_path(
            git_path=git_path,
            repository_root=repository_root,
            relative_name=relative_name,
            label=f"{label}_path",
        )
        _reject_nonempty_optional_git_file(path, label=label)


def _verify_producer_source(
    *,
    git_path: Path,
    control_plane_root: Path,
    control_plane_revision: str,
) -> tuple[str, bytes, Path]:
    executed_path = _normalized_absolute_path(Path(__file__))
    expected_path = _normalized_absolute_path(
        control_plane_root / PurePosixPath(PRODUCER_SOURCE_PATH)
    )
    if os.path.normcase(str(executed_path)) != os.path.normcase(str(expected_path)):
        raise CarrierError(
            "executed_carrier_loader_path_mismatch: "
            f"expected={expected_path} actual={executed_path}",
            exit_kind="producer_binding_error",
        )

    object_name = f"{control_plane_revision}:{PRODUCER_SOURCE_PATH}"
    object_type = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=control_plane_root,
            arguments=("cat-file", "-t", object_name),
            label="carrier_loader_source_type",
            max_stdout_bytes=4096,
        ),
        label="carrier_loader_source_type",
    )
    if object_type != "blob":
        raise CarrierError(
            f"carrier_loader_source_not_blob: observed={object_type!r}",
            exit_kind="producer_binding_error",
        )

    declared_size_raw = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=control_plane_root,
            arguments=("cat-file", "-s", object_name),
            label="carrier_loader_source_size",
            max_stdout_bytes=4096,
        ),
        label="carrier_loader_source_size",
    )
    try:
        declared_size = int(declared_size_raw, 10)
    except ValueError as exc:
        raise CarrierError(
            f"carrier_loader_source_size_invalid: {declared_size_raw!r}",
            exit_kind="producer_binding_error",
        ) from exc
    if declared_size <= 0 or declared_size > MAX_PRODUCER_SOURCE_BYTES:
        raise CarrierError(
            "carrier_loader_source_size_out_of_bounds: "
            f"size={declared_size} maximum={MAX_PRODUCER_SOURCE_BYTES}",
            exit_kind="producer_binding_error",
        )

    committed = _run_git(
        git_path=git_path,
        repository_root=control_plane_root,
        arguments=("cat-file", "blob", object_name),
        label="carrier_loader_source_content",
        max_stdout_bytes=declared_size,
    )
    if len(committed) != declared_size:
        raise CarrierError(
            "carrier_loader_source_size_changed_or_misreported: "
            f"declared={declared_size} observed={len(committed)}",
            exit_kind="producer_binding_error",
        )

    working = read_regular_file(
        expected_path,
        label="carrier_loader_working_tree",
        max_bytes=MAX_PRODUCER_SOURCE_BYTES,
    )
    if working != committed:
        raise CarrierError(
            "carrier_loader_working_tree_differs_from_exact_revision",
            exit_kind="producer_binding_error",
        )
    return sha256_bytes(committed), committed, expected_path


def _reverify_producer_binding(
    *,
    git_path: Path,
    control_plane_root: Path,
    control_plane_revision: str,
    expected_source: bytes,
    source_path: Path,
) -> None:
    _verify_git_repository(
        git_path=git_path,
        repository_root=control_plane_root,
        expected_revision=control_plane_revision,
    )
    _verify_git_local_only_repository_state(
        git_path=git_path,
        repository_root=control_plane_root,
    )
    working = read_regular_file(
        source_path,
        label="carrier_loader_working_tree_recheck",
        max_bytes=MAX_PRODUCER_SOURCE_BYTES,
    )
    if working != expected_source:
        raise CarrierError(
            "carrier_loader_source_changed_after_binding",
            exit_kind="producer_binding_error",
        )


def _reject_unsafe_output(
    output: Path | None,
    *,
    staging_root: Path,
    control_plane_root: Path,
    carrier_path: Path,
    source_path: Path,
) -> Path | None:
    if output is None:
        return None
    candidate = _normalized_absolute_path(output)
    if not candidate.name or candidate.name in {".", ".."}:
        raise CarrierError(
            f"output_leaf_name_invalid: {candidate}",
            exit_kind="output_boundary_error",
        )
    if candidate.name.casefold() in PROTECTED_OUTPUT_NAMES_CASEFOLDED:
        raise CarrierError(
            f"output_name_protected: {candidate.name}",
            exit_kind="output_boundary_error",
        )
    if path_is_within(candidate, staging_root):
        raise CarrierError(
            f"output_inside_staging_root: {candidate}",
            exit_kind="output_boundary_error",
        )
    if path_is_within(candidate, control_plane_root):
        raise CarrierError(
            f"output_inside_control_plane_root: {candidate}",
            exit_kind="output_boundary_error",
        )
    if same_target(candidate, carrier_path) or same_target(candidate, source_path):
        raise CarrierError(
            f"output_overwrites_protected_input: {candidate}",
            exit_kind="output_boundary_error",
        )
    if candidate.exists():
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise CarrierError(
                f"output_unavailable: {candidate}: {exc}",
                exit_kind="output_boundary_error",
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise CarrierError(
                f"output_existing_target_not_regular_file: {candidate}",
                exit_kind="output_boundary_error",
            )
    return candidate


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise CarrierError(
                "output_write_made_no_progress",
                exit_kind="output_write_error",
            )
        offset += written


def _output_target_snapshot(
    *,
    chain: DirectoryChain,
    final_name: str,
    candidate: Path,
) -> os.stat_result | None:
    try:
        observed = os.stat(
            final_name,
            dir_fd=chain.final_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CarrierError(
            f"output_target_stat_failed: {candidate}: {exc}",
            exit_kind="output_boundary_error",
        ) from exc
    if not stat.S_ISREG(observed.st_mode):
        raise CarrierError(
            f"output_existing_target_not_regular_file: {candidate}",
            exit_kind="output_boundary_error",
        )
    return observed


def _verify_output_target_unchanged(
    *,
    chain: DirectoryChain,
    final_name: str,
    candidate: Path,
    expected: os.stat_result | None,
) -> None:
    observed = _output_target_snapshot(
        chain=chain,
        final_name=final_name,
        candidate=candidate,
    )
    if expected is None:
        if observed is not None:
            raise CarrierError(
                f"output_target_appeared_before_publish: {candidate}",
                exit_kind="output_boundary_error",
            )
        return
    if observed is None or _file_identity(observed) != _file_identity(expected):
        raise CarrierError(
            f"output_target_changed_before_publish: {candidate}",
            exit_kind="output_boundary_error",
        )


def _verify_output_payload_at_name(
    *,
    chain: DirectoryChain,
    name: str,
    payload: bytes,
    label: str,
) -> tuple[Any, ...]:
    read_fd = os.open(name, _read_flags(), dir_fd=chain.final_fd)
    try:
        before = os.fstat(read_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != len(payload):
            raise CarrierError(
                f"{label}_identity_invalid",
                exit_kind="output_write_error",
            )
        observed = _read_descriptor_bytes(
            read_fd,
            label=label,
            max_bytes=len(payload),
            expected_size=len(payload),
        )
        after = os.fstat(read_fd)
        if _file_identity(before) != _file_identity(after):
            raise CarrierError(
                f"{label}_changed_during_readback",
                exit_kind="output_write_error",
            )
        if observed != payload:
            raise CarrierError(
                f"{label}_bytes_mismatch",
                exit_kind="output_write_error",
            )
        path_state = os.stat(
            name,
            dir_fd=chain.final_fd,
            follow_symlinks=False,
        )
        if _file_identity(path_state) != _file_identity(after):
            raise CarrierError(
                f"{label}_path_binding_changed",
                exit_kind="output_write_error",
            )
        return _file_identity(after)
    except OSError as exc:
        raise CarrierError(
            f"{label}_readback_failed: {exc}",
            exit_kind="output_write_error",
        ) from exc
    finally:
        os.close(read_fd)


def _atomic_write_external(
    path: Path,
    payload: bytes,
    *,
    verify_inputs: Callable[[], None],
) -> None:
    candidate = _normalized_absolute_path(path)
    parent = candidate.parent
    with DirectoryChain.open(parent, label="output_parent") as chain:
        final_name = candidate.name
        initial_target = _output_target_snapshot(
            chain=chain,
            final_name=final_name,
            candidate=candidate,
        )

        temporary_name = f".{final_name}.{secrets.token_hex(16)}.tmp"
        backup_name: str | None = None
        temporary_created = False
        backup_created = False
        published = False
        staged_inode: tuple[Any, Any] | None = None
        descriptor: int | None = None
        try:
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | int(getattr(os, "O_CLOEXEC", 0))
                | int(getattr(os, "O_NOFOLLOW", 0))
            )
            descriptor = os.open(
                temporary_name,
                flags,
                0o600,
                dir_fd=chain.final_fd,
            )
            temporary_created = True
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o644)
            os.close(descriptor)
            descriptor = None

            staged_identity = _verify_output_payload_at_name(
                chain=chain,
                name=temporary_name,
                payload=payload,
                label="staged_output",
            )
            staged_inode = (staged_identity[0], staged_identity[1])
            chain.verify()

            # All protected inputs are reverified only after the output bytes
            # have been completely staged and read back, but before the
            # destination path can be replaced.
            verify_inputs()

            chain.verify()
            staged_before_publish = _verify_output_payload_at_name(
                chain=chain,
                name=temporary_name,
                payload=payload,
                label="staged_output_before_publish",
            )
            if (
                (staged_before_publish[0], staged_before_publish[1])
                != staged_inode
            ):
                raise CarrierError(
                    "staged_output_inode_changed_before_publish",
                    exit_kind="output_write_error",
                )
            _verify_output_target_unchanged(
                chain=chain,
                final_name=final_name,
                candidate=candidate,
                expected=initial_target,
            )

            # Preserve an existing destination inode until publication and the
            # post-publication input/path checks have all succeeded. This
            # permits exact rollback instead of leaving stale output behind.
            if initial_target is not None:
                backup_name = (
                    f".{final_name}.{secrets.token_hex(16)}.rollback"
                )
                try:
                    os.link(
                        final_name,
                        backup_name,
                        src_dir_fd=chain.final_fd,
                        dst_dir_fd=chain.final_fd,
                        follow_symlinks=False,
                    )
                except OSError as exc:
                    raise CarrierError(
                        f"output_backup_link_failed: {candidate}: {exc}",
                        exit_kind="output_write_error",
                    ) from exc
                backup_created = True
                backup_state = os.stat(
                    backup_name,
                    dir_fd=chain.final_fd,
                    follow_symlinks=False,
                )
                current_target = os.stat(
                    final_name,
                    dir_fd=chain.final_fd,
                    follow_symlinks=False,
                )
                if (
                    _inode_identity(backup_state)
                    != _inode_identity(current_target)
                    or _inode_identity(current_target)
                    != _inode_identity(initial_target)
                ):
                    raise CarrierError(
                        "output_target_changed_while_creating_rollback_link",
                        exit_kind="output_write_error",
                    )
                os.fsync(chain.final_fd)

            os.rename(
                temporary_name,
                final_name,
                src_dir_fd=chain.final_fd,
                dst_dir_fd=chain.final_fd,
            )
            temporary_created = False
            published = True
            os.fsync(chain.final_fd)

            published_identity = _verify_output_payload_at_name(
                chain=chain,
                name=final_name,
                payload=payload,
                label="written_output",
            )
            chain.verify()
            path_after_chain_verification = os.stat(
                final_name,
                dir_fd=chain.final_fd,
                follow_symlinks=False,
            )
            if (
                _file_identity(path_after_chain_verification)
                != published_identity
            ):
                raise CarrierError(
                    "written_output_path_binding_changed_after_directory_verification",
                    exit_kind="output_write_error",
                )

            # Reverify once more after publication. Any input change detected
            # across the rename/readback interval rolls the destination back to
            # its exact previous inode, or removes the newly created output.
            verify_inputs()
            final_identity = _verify_output_payload_at_name(
                chain=chain,
                name=final_name,
                payload=payload,
                label="written_output_after_final_input_verification",
            )
            if final_identity != published_identity:
                raise CarrierError(
                    "written_output_identity_changed_after_final_input_verification",
                    exit_kind="output_write_error",
                )
            chain.verify()

            if backup_created and backup_name is not None:
                os.unlink(backup_name, dir_fd=chain.final_fd)
                backup_created = False
        except Exception as exc:
            rollback_error: Exception | None = None
            try:
                if published:
                    if backup_created and backup_name is not None:
                        os.rename(
                            backup_name,
                            final_name,
                            src_dir_fd=chain.final_fd,
                            dst_dir_fd=chain.final_fd,
                        )
                        backup_created = False
                        os.fsync(chain.final_fd)
                    elif staged_inode is not None:
                        try:
                            current_target = os.stat(
                                final_name,
                                dir_fd=chain.final_fd,
                                follow_symlinks=False,
                            )
                        except FileNotFoundError:
                            current_target = None
                        if (
                            current_target is not None
                            and _inode_identity(current_target) == staged_inode
                        ):
                            os.unlink(final_name, dir_fd=chain.final_fd)
                            os.fsync(chain.final_fd)
            except Exception as rollback_exc:
                rollback_error = rollback_exc

            if rollback_error is not None:
                raise CarrierError(
                    "output_publish_failed_and_rollback_failed: "
                    f"publish_error={type(exc).__name__}: {exc}; "
                    f"rollback_error={type(rollback_error).__name__}: "
                    f"{rollback_error}",
                    exit_kind="output_write_error",
                ) from exc
            raise
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary_created:
                try:
                    os.unlink(temporary_name, dir_fd=chain.final_fd)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
            if backup_created and backup_name is not None:
                try:
                    os.unlink(backup_name, dir_fd=chain.final_fd)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass


def _carrier_id(
    *,
    namespace: str,
    workflow_name: str,
    workflow_run_number: int,
) -> str:
    value = (
        f"carrier:{namespace}/"
        f"{_slug(workflow_name)}-{workflow_run_number}/v0"
    )
    if re.fullmatch(r"carrier:[A-Za-z0-9._:/@+-]+", value) is None:
        raise CarrierError(
            f"derived_carrier_id_not_schema_safe: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _producer_record(
    *,
    ci_workflow_or_job_identity: str,
    subject_run_key: str,
    control_plane_revision: str,
    producer_source_sha256: str,
) -> dict[str, Any]:
    return {
        "ci_workflow_or_job_identity": ci_workflow_or_job_identity,
        "producer_id": PRODUCER_ID,
        "producer_name": PRODUCER_NAME,
        "producer_run_key": subject_run_key,
        "producer_source": PRODUCER_SOURCE_PATH,
        "producer_source_revision": control_plane_revision,
        "producer_source_sha256": producer_source_sha256,
        "producer_version": TOOL_VERSION,
        "production_mode": PRODUCTION_MODE,
    }


def _carrier_record(
    *,
    carrier_id: str,
    staged_relative_path: str,
    root_prefix: str,
    finalized_utc: str,
    carrier_sha256: str,
    carrier_size_bytes: int,
    producer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_payload_mode": ARTIFACT_PAYLOAD_MODE,
        "carrier_id": carrier_id,
        "carrier_kind": CARRIER_KIND,
        "finalized": True,
        "finalized_utc": finalized_utc,
        "immutable": True,
        "media_type": MEDIA_TYPE,
        "path_base": PATH_BASE,
        "producer": producer,
        "provider_binding": None,
        "root_prefix": root_prefix,
        "sha256": carrier_sha256,
        "size_bytes": carrier_size_bytes,
        "staged_relative_path": staged_relative_path,
    }


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
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load one finalized PULSEmech current-run export ZIP carrier, "
            "materialize its sole authoritative SHA-256 identity, and emit "
            "the canonical carrier object required by the current-run "
            "expectation contract. Carrier payload interpretation remains a "
            "separate downstream responsibility."
        )
    )
    parser.add_argument(
        "--staging-root",
        required=True,
        help="Current-run export staging-root directory.",
    )
    parser.add_argument(
        "--staged-relative-path",
        required=True,
        help="Canonical relative path of the finalized ZIP under staging root.",
    )
    parser.add_argument(
        "--root-prefix",
        required=True,
        help="Canonical outer archive prefix, including its trailing slash.",
    )
    parser.add_argument(
        "--carrier-id-namespace",
        required=True,
        help="Slash-separated carrier ID namespace expected by the packet profile.",
    )
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-run-id", required=True, type=_positive_int)
    parser.add_argument("--workflow-run-number", required=True, type=_positive_int)
    parser.add_argument("--workflow-run-attempt", required=True, type=_positive_int)
    parser.add_argument(
        "--subject-run-key",
        required=True,
        help=(
            "Exact canonical subject run key; independently reconstructed "
            "and checked."
        ),
    )
    parser.add_argument("--finalized-utc", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument(
        "--control-plane-root",
        default=str(ROOT),
        help="Protected exact control-plane checkout root.",
    )
    parser.add_argument(
        "--control-plane-revision",
        required=True,
        help="Protected exact lowercase SHA-40 control-plane revision.",
    )
    parser.add_argument(
        "--trusted-git",
        help=(
            "Optional approved absolute Linux system Git executable. "
            "When omitted, the first available protected candidate is used."
        ),
    )
    parser.add_argument(
        "--max-carrier-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_CARRIER_BYTES,
        help=(
            "Fail-closed carrier capture bound in bytes "
            f"(default: {DEFAULT_MAX_CARRIER_BYTES})."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional external path for the canonical carrier JSON. "
            "Output inside staging or control-plane roots is rejected."
        ),
    )
    return parser.parse_args()


def _build(args: argparse.Namespace) -> bytes:
    _require_supported_execution_platform()

    staged_relative_path = _canonical_member_path(
        args.staged_relative_path,
        label="staged_relative_path",
    )
    root_prefix = _canonical_directory_prefix(
        args.root_prefix,
        label="root_prefix",
    )
    carrier_id_namespace = _canonical_carrier_id_namespace(
        args.carrier_id_namespace
    )
    workflow_name = _non_empty_text(args.workflow_name, label="workflow_name")
    ci_identity = _non_empty_text(
        args.ci_workflow_or_job_identity,
        label="ci_workflow_or_job_identity",
    )
    supplied_run_key = _non_empty_text(
        args.subject_run_key,
        label="subject_run_key",
    )
    expected_run_key = _subject_run_key(
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
        workflow_name=workflow_name,
    )
    if supplied_run_key != expected_run_key:
        raise CarrierError(
            "subject_run_key_mismatch: "
            f"expected={expected_run_key!r} actual={supplied_run_key!r}",
            exit_kind="input_boundary_error",
        )

    finalized_utc = _non_empty_text(args.finalized_utc, label="finalized_utc")
    _parse_utc(finalized_utc, label="finalized_utc")
    control_plane_revision = _canonical_sha40(
        args.control_plane_revision,
        label="control_plane_revision",
    )

    staging_root = _normalized_absolute_path(Path(args.staging_root))
    control_plane_root = _normalized_absolute_path(Path(args.control_plane_root))
    with DirectoryChain.open(staging_root, label="staging_root"):
        pass
    with DirectoryChain.open(control_plane_root, label="control_plane_root"):
        pass
    if _paths_overlap(staging_root, control_plane_root):
        raise CarrierError(
            "staging_root_and_control_plane_root_must_be_separate",
            exit_kind="input_boundary_error",
        )

    trusted_git = _select_trusted_git(args.trusted_git)
    _require_trusted_git_local_only_support(trusted_git)
    _verify_git_repository(
        git_path=trusted_git,
        repository_root=control_plane_root,
        expected_revision=control_plane_revision,
    )
    _verify_git_local_only_repository_state(
        git_path=trusted_git,
        repository_root=control_plane_root,
    )
    producer_source_sha256, producer_source, source_path = (
        _verify_producer_source(
            git_path=trusted_git,
            control_plane_root=control_plane_root,
            control_plane_revision=control_plane_revision,
        )
    )

    carrier_path = staging_root / PurePosixPath(staged_relative_path)
    output_path = _reject_unsafe_output(
        Path(args.output) if args.output is not None else None,
        staging_root=staging_root,
        control_plane_root=control_plane_root,
        carrier_path=carrier_path,
        source_path=source_path,
    )

    carrier_id = _carrier_id(
        namespace=carrier_id_namespace,
        workflow_name=workflow_name,
        workflow_run_number=args.workflow_run_number,
    )

    with OpenedCarrier.open(
        staging_root=staging_root,
        staged_relative_path=staged_relative_path,
        max_bytes=args.max_carrier_bytes,
    ) as opened:
        carrier_sha256, carrier_size_bytes = opened.hash_once()
        producer = _producer_record(
            ci_workflow_or_job_identity=ci_identity,
            subject_run_key=supplied_run_key,
            control_plane_revision=control_plane_revision,
            producer_source_sha256=producer_source_sha256,
        )
        carrier = _carrier_record(
            carrier_id=carrier_id,
            staged_relative_path=staged_relative_path,
            root_prefix=root_prefix,
            finalized_utc=finalized_utc,
            carrier_sha256=carrier_sha256,
            carrier_size_bytes=carrier_size_bytes,
            producer=producer,
        )
        rendered = render_json(carrier)

        def verify_final_inputs_before_publish() -> None:
            _reverify_producer_binding(
                git_path=trusted_git,
                control_plane_root=control_plane_root,
                control_plane_revision=control_plane_revision,
                expected_source=producer_source,
                source_path=source_path,
            )
            opened.verify_unchanged()

        if output_path is not None:
            _atomic_write_external(
                output_path,
                rendered,
                verify_inputs=verify_final_inputs_before_publish,
            )
        else:
            verify_final_inputs_before_publish()
        return rendered


def main() -> int:
    args = parse_args()
    try:
        rendered = _build(args)
    except CarrierError as exc:
        sys.stderr.buffer.write(
            render_json(
                make_failure_diagnostic(
                    error=str(exc),
                    exit_kind=exc.exit_kind,
                )
            )
        )
        return exc.exit_code
    except Exception as exc:
        sys.stderr.buffer.write(
            render_json(
                make_failure_diagnostic(
                    error=f"unhandled_carrier_error: {type(exc).__name__}: {exc}",
                    exit_kind="unhandled_error",
                )
            )
        )
        return 2

    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
