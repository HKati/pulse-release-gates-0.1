#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"error_code":"isolated_python_runtime_required",'
    '"member_path":null,'
    '"ok":false,'
    '"stage":"runtime",'
    '"tool":"check_pulsemech_compute_post_run_producer_input_capture_v0",'
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
import copy
import datetime as dt
import hashlib
import inspect
import json
import math
import os
import re
import stat
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

import jsonschema

try:
    from referencing import Registry as ReferencingRegistry
    from referencing.exceptions import NoSuchResource
except ImportError:  # pragma: no cover - supported jsonschema fallback
    ReferencingRegistry = None
    NoSuchResource = None


TOOL_NAME = "check_pulsemech_compute_post_run_producer_input_capture_v0"
TOOL_VERSION = "0.1.0"
DOCUMENT_TYPE = "pulsemech_compute_post_run_producer_input_capture_manifest"
SCHEMA_VERSION = "pulsemech_compute_post_run_producer_input_capture_manifest_v0"
CONTRACT_ID = "pulsemech_compute_post_run_producer_input_capture_v0"
CONTRACT_VERSION = "0.1.0"

REPOSITORY = "HKati/pulse-release-gates-0.1"
REPOSITORY_ID = 1_061_766_508
SUBJECT_WORKFLOW_NAME = "PULSE CI"
SUBJECT_WORKFLOW_ID = 191_471_316
SUBJECT_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
SUBJECT_RUN_ID = 29_249_887_581
SUBJECT_RUN_NUMBER = 6066
SUBJECT_RUN_ATTEMPT = 1
SUBJECT_EVENT = "workflow_dispatch"
SUBJECT_HEAD_BRANCH = "main"
SUBJECT_SOURCE_REF = "refs/heads/main"
SUBJECT_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
SUBJECT_RUN_CREATED_UTC = "2026-07-13T12:26:52Z"
SUBJECT_RUN_STARTED_UTC = "2026-07-13T12:26:52Z"
SUBJECT_RUN_UPDATED_UTC = "2026-07-13T12:32:21Z"
SUBJECT_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_OBSERVED_JOB_COUNT = 8

SCHEMA_PATH = (
    "schemas/"
    "pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json"
)
CONTRACT_PATH = "contracts/pulsemech_compute_post_run_producer_input_capture_v0.json"
CAPTURE_TOOL_PATH = "tools/capture_pulsemech_compute_post_run_producer_input_v0.py"
CAPTURE_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_post_run_producer_input_capture_v0.yml"
)
EXAMPLE_PATH = (
    "examples/compute/"
    "pulsemech_compute_post_run_producer_input_capture_manifest_example_v0.json"
)

EXPECTED_SCHEMA_SIZE = 71_861
EXPECTED_SCHEMA_SHA256 = (
    "65a29a18f1b9090f3dd338f9c4c1484b4d851df68ff19758670a4c53c58057bb"
)
EXPECTED_SCHEMA_GIT_BLOB_SHA1 = "f7256747704e87a4df312af6d20dad1c8bea6148"
EXPECTED_CONTRACT_SIZE = 38_745
EXPECTED_CONTRACT_SHA256 = (
    "ec3e31c9526f3bf931c633292bbff77efdf9cfbc61a0be634b6239c4acaccfbe"
)
EXPECTED_CONTRACT_GIT_BLOB_SHA1 = "66e03ebe4b7571888e0a8ac5322561353be2e892"

API_SCHEME = "https"
API_HOST = "api.github.com"
API_VERSION = "2022-11-28"
ACCEPT = "application/vnd.github+json"
ACCEPT_ENCODING = "identity"
USER_AGENT = "pulsemech-compute-post-run-capture-v0/0.1.0"
TOKEN_ENV = "GH_TOKEN"

RUN_REQUEST_PATH = (
    "/repos/HKati/pulse-release-gates-0.1/"
    "actions/runs/29249887581/attempts/1"
)
JOBS_REQUEST_PATH = RUN_REQUEST_PATH + "/jobs"
FIRST_JOBS_REQUEST_TARGET = JOBS_REQUEST_PATH + "?per_page=100&page=1"

RAW_DIRECTORY = "raw"
METADATA_DIRECTORY = "metadata"
RUN_BODY_PATH = "raw/run_attempt_response.json"
RUN_METADATA_PATH = "metadata/run_attempt_exchange_v0.json"
JOBS_BODY_TEMPLATE = "raw/jobs_page_%04d_response.json"
JOBS_METADATA_TEMPLATE = "metadata/jobs_page_%04d_exchange_v0.json"
OBSERVED_MANIFEST_NAME = (
    "pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json"
)
EXAMPLE_MANIFEST_NAME = (
    "pulsemech_compute_post_run_producer_input_capture_manifest_example_v0.json"
)
OBSERVED_CAPTURE_ROOT = (
    "preservation/pulse_ci_6066/post_run_producer_input_capture_v0/"
)
EXAMPLE_CAPTURE_ROOT = "examples/compute/post_run_producer_input_capture_example_v0/"

MAX_RESPONSE_BODY_BYTES = 8 * 1024 * 1024
MAX_EXCHANGE_METADATA_BYTES = 1 * 1024 * 1024
MAX_TOTAL_CAPTURE_BYTES = 64 * 1024 * 1024
MAX_JOBS_PAGE_COUNT = 100
MAX_JOBS_PER_PAGE = 100
MAX_STEP_RECORDS_PER_JOB = 10_000
MAX_STEP_RECORDS_PER_PAGE = 100_000
MAX_TOTAL_STEP_RECORDS = 1_000_000
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_SCHEMA_BYTES = 8 * 1024 * 1024
MAX_CONTRACT_BYTES = 8 * 1024 * 1024
MAX_CAPTURE_TOOL_BYTES = 8 * 1024 * 1024
MAX_WORKFLOW_BYTES = 1 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
MAX_GIT_STDERR_BYTES = 64 * 1024
GIT_TIMEOUT_SECONDS = 30
EXPECTED_CAPTURE_DIRECTORY_MODE = 0o700
EXPECTED_CAPTURE_FILE_MODE = 0o600

SELECTED_RESPONSE_HEADER_KEYS = (
    "content_encoding",
    "content_type",
    "deprecation",
    "etag",
    "link",
    "sunset",
    "x_github_request_id",
)

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ERROR_CODE_RE = re.compile(r"^[a-z0-9_]+$")
CANONICAL_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)
CANONICAL_POSITIVE_DECIMAL_RE = re.compile(r"^[1-9][0-9]*$")
SAFE_LEAF_RE = re.compile(r"^[A-Za-z0-9._-]+$")
KNOWN_GITHUB_TOKEN_RE = re.compile(
    rb"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"
)
SCHEMA_REFERENCE_KEYWORDS = frozenset({"$ref", "$dynamicRef", "$recursiveRef"})

TRUSTED_GIT_CANDIDATES = (
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

GIT_LOCAL_ONLY_CONFIG = (
    ("core.fsmonitor", "false"),
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

_NETWORK_AUDIT_EVENTS = frozenset(
    {
        "http.client.connect",
        "http.client.send",
        "socket.__new__",
        "socket.bind",
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
        "socket.gethostbyaddr",
        "socket.gethostbyname",
        "socket.gethostbyname_ex",
        "socket.getnameinfo",
        "socket.sendto",
        "urllib.Request",
    }
)
_NETWORK_AUDIT_GUARD_INSTALLED = False


class StrictJsonError(ValueError):
    pass


class ValidationError(RuntimeError):
    """One deterministic fail-closed offline validation rejection."""

    def __init__(
        self,
        error_code: str,
        *,
        stage: str,
        member_path: str | None = None,
    ) -> None:
        if ERROR_CODE_RE.fullmatch(error_code) is None:
            error_code = "invalid_internal_error_code"
        if ERROR_CODE_RE.fullmatch(stage) is None:
            stage = "runtime"
        if member_path is not None:
            try:
                member_path = _safe_relative_path(member_path).as_posix()
            except Exception:
                member_path = None
        super().__init__(error_code)
        self.error_code = error_code
        self.stage = stage
        self.member_path = member_path


@dataclass(frozen=True)
class RepositoryObject:
    role: str
    path: str
    source_revision: str
    exact_bytes: bytes
    size_bytes: int
    sha256: str
    git_blob_sha1: str
    revision_object_verified: bool
    resolved_revision: str


@dataclass(frozen=True)
class CaptureSnapshot:
    manifest_name: str
    files: Mapping[str, bytes]
    total_size_bytes: int


@dataclass(frozen=True)
class ValidationResult:
    record_status: str
    manifest_file_name: str
    manifest_sha256: str
    page_count: int
    job_count: int
    step_record_count: int
    authority_effect: str


class ClosedSchemaReferenceError(RuntimeError):
    pass


def _raise(
    error_code: str,
    *,
    stage: str,
    member_path: str | None = None,
) -> None:
    raise ValidationError(error_code, stage=stage, member_path=member_path)


def _install_network_audit_guard() -> None:
    global _NETWORK_AUDIT_GUARD_INSTALLED
    if _NETWORK_AUDIT_GUARD_INSTALLED:
        return

    def deny_network(event: str, args: tuple[Any, ...]) -> None:
        del args
        if event in _NETWORK_AUDIT_EVENTS or event.startswith("socket."):
            _raise("network_access_forbidden", stage="runtime")

    sys.addaudithook(deny_network)
    _NETWORK_AUDIT_GUARD_INSTALLED = True


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError("duplicate_key")
        result[key] = value
    return result


def _reject_float(_: str) -> None:
    raise StrictJsonError("floating_point_number")


def _reject_non_finite(_: str) -> None:
    raise StrictJsonError("non_finite_number")


def _parse_int(value: str) -> int:
    if value == "-0":
        raise StrictJsonError("negative_zero")
    return int(value, 10)


def _parse_json_object(
    payload: bytes,
    *,
    stage: str,
    member_path: str,
    allow_bom: bool,
) -> tuple[dict[str, Any], bool]:
    bom_present = payload.startswith(b"\xef\xbb\xbf")
    if bom_present and not allow_bom:
        _raise(
            "utf8_bom_forbidden",
            stage=stage,
            member_path=member_path,
        )
    parse_payload = payload[3:] if bom_present else payload
    try:
        text = parse_payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _raise("invalid_utf8", stage=stage, member_path=member_path)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_non_finite,
        )
    except (json.JSONDecodeError, StrictJsonError, ValueError):
        _raise("invalid_json", stage=stage, member_path=member_path)
    if not isinstance(value, dict):
        _raise("top_level_not_object", stage=stage, member_path=member_path)
    return value, bom_present


def _check_canonical_value(
    value: Any,
    *,
    stage: str,
    member_path: str,
) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, list):
        for item in value:
            _check_canonical_value(item, stage=stage, member_path=member_path)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _raise(
                    "canonical_json_non_string_key",
                    stage=stage,
                    member_path=member_path,
                )
            _check_canonical_value(item, stage=stage, member_path=member_path)
        return
    _raise(
        "canonical_json_unsupported_value",
        stage=stage,
        member_path=member_path,
    )


def _canonical_json_bytes(
    value: dict[str, Any],
    *,
    stage: str,
    member_path: str,
) -> bytes:
    _check_canonical_value(value, stage=stage, member_path=member_path)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (UnicodeEncodeError, ValueError, TypeError):
        _raise(
            "canonical_json_serialization_failed",
            stage=stage,
            member_path=member_path,
        )
    return rendered + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    encoded = b"blob " + str(len(payload)).encode("ascii") + b"\x00" + payload
    try:
        return hashlib.sha1(encoded, usedforsecurity=False).hexdigest()
    except TypeError:  # pragma: no cover - older Python compatibility
        return hashlib.sha1(encoded).hexdigest()


def _require_object(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _raise(error_code, stage=stage, member_path=member_path)
    return value


def _require_array(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
) -> list[Any]:
    if not isinstance(value, list):
        _raise(error_code, stage=stage, member_path=member_path)
    return value


def _require_string(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
    exact: str | None = None,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        _raise(error_code, stage=stage, member_path=member_path)
    if not allow_empty and not value:
        _raise(error_code, stage=stage, member_path=member_path)
    if "\x00" in value or "\r" in value or "\n" in value:
        _raise(error_code, stage=stage, member_path=member_path)
    if exact is not None and value != exact:
        _raise(error_code, stage=stage, member_path=member_path)
    return value


def _require_bool(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
    exact: bool | None = None,
) -> bool:
    if not isinstance(value, bool):
        _raise(error_code, stage=stage, member_path=member_path)
    if exact is not None and value is not exact:
        _raise(error_code, stage=stage, member_path=member_path)
    return value


def _require_int(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
    exact: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(error_code, stage=stage, member_path=member_path)
    if minimum is not None and value < minimum:
        _raise(error_code, stage=stage, member_path=member_path)
    if maximum is not None and value > maximum:
        _raise(error_code, stage=stage, member_path=member_path)
    if exact is not None and value != exact:
        _raise(error_code, stage=stage, member_path=member_path)
    return value


def _require_sha40(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
) -> str:
    text = _require_string(
        value,
        error_code=error_code,
        stage=stage,
        member_path=member_path,
    )
    if SHA40_RE.fullmatch(text) is None:
        _raise(error_code, stage=stage, member_path=member_path)
    return text


def _require_sha256(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
) -> str:
    text = _require_string(
        value,
        error_code=error_code,
        stage=stage,
        member_path=member_path,
    )
    if SHA256_RE.fullmatch(text) is None:
        _raise(error_code, stage=stage, member_path=member_path)
    return text


def _parse_utc(
    value: Any,
    *,
    error_code: str,
    stage: str,
    member_path: str | None = None,
) -> dt.datetime:
    text = _require_string(
        value,
        error_code=error_code,
        stage=stage,
        member_path=member_path,
    )
    if CANONICAL_UTC_RE.fullmatch(text) is None:
        _raise(error_code, stage=stage, member_path=member_path)
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        _raise(error_code, stage=stage, member_path=member_path)
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        _raise(error_code, stage=stage, member_path=member_path)
    return parsed


def _safe_relative_path(path: str) -> PurePosixPath:
    if not isinstance(path, str) or not path or len(path) > 512:
        raise ValueError("unsafe")
    if any(character in path for character in ("\\", "\x00", "\r", "\n")):
        raise ValueError("unsafe")
    pure = PurePosixPath(path)
    if pure.is_absolute() or not pure.parts:
        raise ValueError("unsafe")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe")
    try:
        path.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("unsafe") from exc
    return pure


def _safe_leaf_name(name: str) -> str:
    if not isinstance(name, str) or SAFE_LEAF_RE.fullmatch(name) is None:
        raise ValueError("unsafe")
    return name


def _secure_open_flags(*, directory: bool = False) -> int:
    required = ["O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK"]
    if directory:
        required.append("O_DIRECTORY")
    if any(not hasattr(os, name) for name in required):
        _raise("required_secure_open_flag_unavailable", stage="runtime")
    flags = os.O_RDONLY
    flags |= int(getattr(os, "O_NOFOLLOW"))
    flags |= int(getattr(os, "O_CLOEXEC"))
    flags |= int(getattr(os, "O_NONBLOCK"))
    flags |= int(getattr(os, "O_BINARY", 0))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY"))
    return flags


def _validate_runtime_platform() -> None:
    if os.name != "posix" or not sys.platform.startswith("linux"):
        _raise("supported_linux_runtime_required", stage="runtime")
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
    if any(not hasattr(os, name) for name in required):
        _raise("required_linux_filesystem_primitives_unavailable", stage="runtime")
    if any(
        function not in os.supports_dir_fd
        for function in (os.open, os.stat)
    ):
        _raise("required_dir_fd_support_unavailable", stage="runtime")
    if os.listdir not in os.supports_fd:
        _raise("required_fd_listdir_support_unavailable", stage="runtime")
    if not Path("/proc/self/fd").is_dir():
        _raise("proc_self_fd_required", stage="runtime")


def _open_absolute_directory_no_symlinks(
    path: Path,
    *,
    stage: str,
) -> int:
    candidate = path.absolute()
    if not candidate.is_absolute():
        _raise("absolute_directory_required", stage=stage)
    flags = _secure_open_flags(directory=True)
    try:
        current_fd = os.open("/", flags)
    except OSError:
        _raise("directory_root_open_failed", stage=stage)
    try:
        for part in candidate.parts[1:]:
            if not part or part in {".", ".."}:
                _raise("directory_path_component_invalid", stage=stage)
            try:
                next_fd = os.open(part, flags, dir_fd=current_fd)
            except OSError:
                _raise("directory_component_open_failed", stage=stage)
            metadata = os.fstat(next_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(next_fd)
                _raise("directory_component_not_directory", stage=stage)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _read_fd_bounded(
    fd: int,
    *,
    maximum: int,
    stage: str,
    member_path: str,
) -> bytes:
    try:
        metadata_before = os.fstat(fd)
    except OSError:
        _raise("member_identity_unavailable", stage=stage, member_path=member_path)
    if not stat.S_ISREG(metadata_before.st_mode):
        _raise("non_regular_member", stage=stage, member_path=member_path)
    if metadata_before.st_nlink != 1:
        _raise("hard_linked_member", stage=stage, member_path=member_path)
    if stat.S_IMODE(metadata_before.st_mode) != EXPECTED_CAPTURE_FILE_MODE:
        _raise("capture_member_mode_mismatch", stage=stage, member_path=member_path)
    if metadata_before.st_size < 1:
        _raise("empty_member", stage=stage, member_path=member_path)
    if metadata_before.st_size > maximum:
        _raise("member_size_limit_exceeded", stage=stage, member_path=member_path)
    parts: list[bytes] = []
    observed = 0
    while True:
        try:
            chunk = os.read(fd, min(READ_CHUNK_BYTES, maximum + 1 - observed))
        except OSError:
            _raise("member_read_failed", stage=stage, member_path=member_path)
        if not chunk:
            break
        observed += len(chunk)
        if observed > maximum:
            _raise("member_size_limit_exceeded", stage=stage, member_path=member_path)
        parts.append(chunk)
    payload = b"".join(parts)
    try:
        metadata_after = os.fstat(fd)
    except OSError:
        _raise("member_identity_unavailable", stage=stage, member_path=member_path)
    if stat.S_IMODE(metadata_after.st_mode) != EXPECTED_CAPTURE_FILE_MODE:
        _raise("capture_member_mode_mismatch", stage=stage, member_path=member_path)
    before = (
        metadata_before.st_dev,
        metadata_before.st_ino,
        metadata_before.st_mode,
        metadata_before.st_size,
        metadata_before.st_mtime_ns,
        metadata_before.st_ctime_ns,
        metadata_before.st_nlink,
    )
    after = (
        metadata_after.st_dev,
        metadata_after.st_ino,
        metadata_after.st_mode,
        metadata_after.st_size,
        metadata_after.st_mtime_ns,
        metadata_after.st_ctime_ns,
        metadata_after.st_nlink,
    )
    if before != after or len(payload) != metadata_before.st_size:
        _raise("member_changed_during_read", stage=stage, member_path=member_path)
    return payload


def _list_directory_ascii(
    fd: int,
    *,
    stage: str,
    maximum_entries: int,
    member_path: str | None = None,
) -> list[str]:
    validated: list[str] = []
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                name = entry.name
                try:
                    name.encode("ascii", errors="strict")
                    _safe_leaf_name(name)
                except (UnicodeEncodeError, ValueError):
                    _raise(
                        "unsafe_directory_entry",
                        stage=stage,
                        member_path=member_path,
                    )
                validated.append(name)
                if len(validated) > maximum_entries:
                    _raise(
                        "directory_entry_count_limit_exceeded",
                        stage=stage,
                        member_path=member_path,
                    )
    except OSError:
        _raise(
            "directory_inventory_unavailable",
            stage=stage,
            member_path=member_path,
        )
    return sorted(validated)


def _open_child_directory(
    parent_fd: int,
    name: str,
    *,
    stage: str,
) -> int:
    try:
        _safe_leaf_name(name)
        fd = os.open(name, _secure_open_flags(directory=True), dir_fd=parent_fd)
    except (OSError, ValueError):
        _raise("required_capture_directory_invalid", stage=stage, member_path=name)
    metadata = os.fstat(fd)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(fd)
        _raise("required_capture_directory_invalid", stage=stage, member_path=name)
    return fd


def _directory_identity(
    fd: int,
    *,
    stage: str,
    member_path: str | None = None,
) -> tuple[int, int, int, int, int, int, int]:
    try:
        metadata = os.fstat(fd)
    except OSError:
        _raise(
            "directory_identity_unavailable",
            stage=stage,
            member_path=member_path,
        )
    if not stat.S_ISDIR(metadata.st_mode):
        _raise(
            "directory_identity_not_directory",
            stage=stage,
            member_path=member_path,
        )
    if stat.S_IMODE(metadata.st_mode) != EXPECTED_CAPTURE_DIRECTORY_MODE:
        _raise(
            (
                "capture_root_mode_mismatch"
                if member_path is None
                else "capture_directory_mode_mismatch"
            ),
            stage=stage,
            member_path=member_path,
        )
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _snapshot_capture_root(capture_root: Path) -> CaptureSnapshot:
    stage = "capture_root"
    root_fd = _open_absolute_directory_no_symlinks(capture_root, stage=stage)
    raw_fd = -1
    metadata_fd = -1
    try:
        root_identity = _directory_identity(root_fd, stage=stage)
        root_names = _list_directory_ascii(
            root_fd,
            stage=stage,
            maximum_entries=4,
        )
        manifest_candidates = sorted(
            set(root_names).intersection({EXAMPLE_MANIFEST_NAME, OBSERVED_MANIFEST_NAME})
        )
        if len(manifest_candidates) != 1:
            _raise("capture_manifest_count_invalid", stage=stage)
        manifest_name = manifest_candidates[0]
        expected_root_entries = {RAW_DIRECTORY, METADATA_DIRECTORY, manifest_name}
        if set(root_names) != expected_root_entries:
            _raise("undeclared_extra_member", stage=stage)
        raw_fd = _open_child_directory(root_fd, RAW_DIRECTORY, stage=stage)
        metadata_fd = _open_child_directory(root_fd, METADATA_DIRECTORY, stage=stage)
        raw_identity = _directory_identity(
            raw_fd,
            stage=stage,
            member_path=RAW_DIRECTORY,
        )
        metadata_identity = _directory_identity(
            metadata_fd,
            stage=stage,
            member_path=METADATA_DIRECTORY,
        )
        raw_names = _list_directory_ascii(
            raw_fd,
            stage=stage,
            maximum_entries=1 + MAX_JOBS_PAGE_COUNT,
            member_path=RAW_DIRECTORY,
        )
        metadata_names = _list_directory_ascii(
            metadata_fd,
            stage=stage,
            maximum_entries=1 + MAX_JOBS_PAGE_COUNT,
            member_path=METADATA_DIRECTORY,
        )
        files: dict[str, bytes] = {}
        total_size = 0

        def add_member(relative_path: str, payload: bytes) -> None:
            nonlocal total_size
            if relative_path in files:
                _raise(
                    "duplicate_capture_member",
                    stage=stage,
                    member_path=relative_path,
                )
            total_size += len(payload)
            if total_size > MAX_TOTAL_CAPTURE_BYTES:
                _raise(
                    "total_capture_size_limit_exceeded",
                    stage=stage,
                    member_path=relative_path,
                )
            files[relative_path] = payload

        manifest_fd = os.open(manifest_name, _secure_open_flags(), dir_fd=root_fd)
        try:
            manifest_payload = _read_fd_bounded(
                manifest_fd,
                maximum=MAX_MANIFEST_BYTES,
                stage=stage,
                member_path=manifest_name,
            )
            add_member(manifest_name, manifest_payload)
        finally:
            os.close(manifest_fd)
        for name in raw_names:
            relative = f"{RAW_DIRECTORY}/{name}"
            try:
                file_fd = os.open(name, _secure_open_flags(), dir_fd=raw_fd)
            except OSError:
                _raise("symlinked_member", stage=stage, member_path=relative)
            try:
                payload = _read_fd_bounded(
                    file_fd,
                    maximum=MAX_RESPONSE_BODY_BYTES,
                    stage=stage,
                    member_path=relative,
                )
                add_member(relative, payload)
            finally:
                os.close(file_fd)
        for name in metadata_names:
            relative = f"{METADATA_DIRECTORY}/{name}"
            try:
                file_fd = os.open(name, _secure_open_flags(), dir_fd=metadata_fd)
            except OSError:
                _raise("symlinked_member", stage=stage, member_path=relative)
            try:
                payload = _read_fd_bounded(
                    file_fd,
                    maximum=MAX_EXCHANGE_METADATA_BYTES,
                    stage=stage,
                    member_path=relative,
                )
                add_member(relative, payload)
            finally:
                os.close(file_fd)
        if _list_directory_ascii(
            root_fd,
            stage=stage,
            maximum_entries=4,
        ) != root_names:
            _raise("capture_root_changed_during_read", stage=stage)
        if _list_directory_ascii(
            raw_fd,
            stage=stage,
            maximum_entries=1 + MAX_JOBS_PAGE_COUNT,
            member_path=RAW_DIRECTORY,
        ) != raw_names:
            _raise(
                "capture_root_changed_during_read",
                stage=stage,
                member_path=RAW_DIRECTORY,
            )
        if _list_directory_ascii(
            metadata_fd,
            stage=stage,
            maximum_entries=1 + MAX_JOBS_PAGE_COUNT,
            member_path=METADATA_DIRECTORY,
        ) != metadata_names:
            _raise(
                "capture_root_changed_during_read",
                stage=stage,
                member_path=METADATA_DIRECTORY,
            )
        if _directory_identity(root_fd, stage=stage) != root_identity:
            _raise("capture_root_changed_during_read", stage=stage)
        if _directory_identity(
            raw_fd,
            stage=stage,
            member_path=RAW_DIRECTORY,
        ) != raw_identity:
            _raise(
                "capture_root_changed_during_read",
                stage=stage,
                member_path=RAW_DIRECTORY,
            )
        if _directory_identity(
            metadata_fd,
            stage=stage,
            member_path=METADATA_DIRECTORY,
        ) != metadata_identity:
            _raise(
                "capture_root_changed_during_read",
                stage=stage,
                member_path=METADATA_DIRECTORY,
            )
        if total_size != sum(len(payload) for payload in files.values()):
            _raise("capture_size_accounting_mismatch", stage=stage)
        return CaptureSnapshot(
            manifest_name=manifest_name,
            files=files,
            total_size_bytes=total_size,
        )
    except OSError:
        _raise("capture_root_read_failed", stage=stage)
    finally:
        if metadata_fd >= 0:
            os.close(metadata_fd)
        if raw_fd >= 0:
            os.close(raw_fd)
        os.close(root_fd)


def _trusted_git_executable() -> Path:
    for candidate in TRUSTED_GIT_CANDIDATES:
        try:
            metadata = candidate.lstat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
            return candidate
    _raise("trusted_git_executable_unavailable", stage="repository_binding")


def _git_environment() -> dict[str, str]:
    environment: dict[str, str] = {}
    for name in GIT_ENV_ALLOWLIST:
        value = os.environ.get(name)
        if value:
            environment[name] = value
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
        }
    )
    return environment


def _run_git(
    root_fd: int,
    arguments: Sequence[str],
    *,
    maximum_output: int,
    allow_failure: bool = False,
) -> tuple[int, bytes]:
    git = _trusted_git_executable()
    command: list[str] = [str(git), "-C", f"/proc/self/fd/{root_fd}"]
    for key, value in GIT_LOCAL_ONLY_CONFIG:
        command.extend(["-c", f"{key}={value}"])
    command.extend(arguments)
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=_git_environment(),
            pass_fds=(root_fd,),
        )
    except (OSError, subprocess.SubprocessError):
        _raise("git_operation_failed", stage="repository_binding")
    if (
        len(completed.stdout) > maximum_output
        or len(completed.stderr) > MAX_GIT_STDERR_BYTES
    ):
        _raise("git_output_limit_exceeded", stage="repository_binding")
    if completed.returncode != 0 and not allow_failure:
        _raise("git_operation_failed", stage="repository_binding")
    return completed.returncode, completed.stdout


def _open_repository_root(repository_root: Path) -> int:
    root_fd = _open_absolute_directory_no_symlinks(
        repository_root,
        stage="repository_binding",
    )
    try:
        try:
            git_metadata = os.stat(".git", dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            _raise("repository_git_directory_unavailable", stage="repository_binding")
        if not stat.S_ISDIR(git_metadata.st_mode):
            _raise("repository_git_directory_invalid", stage="repository_binding")
        _, inside = _run_git(
            root_fd,
            ["rev-parse", "--is-inside-work-tree"],
            maximum_output=64,
        )
        if inside.decode("ascii", errors="strict").strip() != "true":
            _raise("repository_not_worktree", stage="repository_binding")
        return root_fd
    except BaseException:
        os.close(root_fd)
        raise


def _load_git_object(
    root_fd: int,
    *,
    role: str,
    path: str,
    revision: str,
    maximum: int,
    allow_example_head_fallback: bool,
) -> RepositoryObject:
    stage = "repository_binding"
    _require_sha40(revision, error_code=f"{role}_source_revision_invalid", stage=stage)
    try:
        _safe_relative_path(path)
    except ValueError:
        _raise(f"{role}_path_invalid", stage=stage)
    object_revision = revision
    size_return_code, raw_size = _run_git(
        root_fd,
        ["cat-file", "-s", f"{object_revision}:{path}"],
        maximum_output=64,
        allow_failure=True,
    )
    revision_verified = size_return_code == 0
    if not revision_verified:
        # A squash merge can leave the example's pre-merge binding revision
        # outside a shallow main-branch checkout. Only the non-authoritative
        # example may fall back to the current committed HEAD object. The
        # caller later admits that fallback only when the capture manifest is
        # byte-identical to the committed canonical example. Observed captures
        # never use this path.
        if not allow_example_head_fallback:
            _raise(f"{role}_committed_bytes_unavailable", stage=stage)
        _, raw_head = _run_git(
            root_fd,
            ["rev-parse", "HEAD"],
            maximum_output=128,
        )
        try:
            object_revision = raw_head.decode(
                "ascii",
                errors="strict",
            ).strip()
        except UnicodeDecodeError:
            _raise("repository_head_revision_invalid", stage=stage)
        _require_sha40(
            object_revision,
            error_code="repository_head_revision_invalid",
            stage=stage,
        )
        size_return_code, raw_size = _run_git(
            root_fd,
            ["cat-file", "-s", f"{object_revision}:{path}"],
            maximum_output=64,
            allow_failure=True,
        )
        if size_return_code != 0:
            _raise(f"{role}_committed_bytes_unavailable", stage=stage)
    try:
        size_text = raw_size.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError:
        _raise(f"{role}_committed_size_invalid", stage=stage)
    if not size_text.isdigit():
        _raise(f"{role}_committed_size_invalid", stage=stage)
    committed_size = int(size_text, 10)
    if committed_size < 1 or committed_size > maximum:
        _raise(f"{role}_size_invalid", stage=stage)
    _, committed = _run_git(
        root_fd,
        ["show", f"{object_revision}:{path}"],
        maximum_output=committed_size,
    )
    if len(committed) != committed_size:
        _raise(f"{role}_committed_size_mismatch", stage=stage)
    size = len(committed)
    sha256 = _sha256(committed)
    blob = _git_blob_sha1(committed)
    _, raw_blob = _run_git(
        root_fd,
        ["rev-parse", f"{object_revision}:{path}"],
        maximum_output=128,
    )
    try:
        git_blob = raw_blob.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError:
        _raise(f"{role}_git_blob_invalid", stage=stage)
    if git_blob != blob:
        _raise(f"{role}_git_blob_reconstruction_mismatch", stage=stage)
    return RepositoryObject(
        role=role,
        path=path,
        source_revision=revision,
        exact_bytes=committed,
        size_bytes=size,
        sha256=sha256,
        git_blob_sha1=blob,
        revision_object_verified=revision_verified,
        resolved_revision=object_revision,
    )


def _binding_revision(
    binding: dict[str, Any],
    *,
    role: str,
) -> str:
    return _require_sha40(
        binding.get("source_revision"),
        error_code=f"{role}_source_revision_invalid",
        stage="repository_binding",
    )


def _load_manifest_bound_schema_and_contract(
    repository_root: Path,
    manifest: dict[str, Any],
    *,
    record_status: str,
) -> tuple[RepositoryObject, RepositoryObject, dict[str, Any], dict[str, Any], int]:
    bindings = _require_object(
        manifest.get("contract_bindings"),
        error_code="contract_bindings_invalid",
        stage="repository_binding",
    )
    schema_binding = _require_object(
        bindings.get("manifest_schema"),
        error_code="schema_binding_invalid",
        stage="repository_binding",
    )
    contract_binding = _require_object(
        bindings.get("normative_contract"),
        error_code="contract_binding_invalid",
        stage="repository_binding",
    )
    expected_schema_binding = {
        "role": "manifest_schema",
        "path": SCHEMA_PATH,
        "size_bytes": EXPECTED_SCHEMA_SIZE,
        "sha256": EXPECTED_SCHEMA_SHA256,
        "git_blob_sha1": EXPECTED_SCHEMA_GIT_BLOB_SHA1,
    }
    expected_contract_binding = {
        "role": "normative_contract",
        "path": CONTRACT_PATH,
        "size_bytes": EXPECTED_CONTRACT_SIZE,
        "sha256": EXPECTED_CONTRACT_SHA256,
        "git_blob_sha1": EXPECTED_CONTRACT_GIT_BLOB_SHA1,
    }
    for field, expected in expected_schema_binding.items():
        if schema_binding.get(field) != expected:
            _raise("schema_binding_mismatch", stage="repository_binding")
    for field, expected in expected_contract_binding.items():
        if contract_binding.get(field) != expected:
            _raise("contract_binding_mismatch", stage="repository_binding")
    schema_revision = _binding_revision(schema_binding, role="manifest_schema")
    contract_revision = _binding_revision(contract_binding, role="normative_contract")
    if schema_revision != contract_revision:
        _raise("schema_contract_source_revision_mismatch", stage="repository_binding")
    root_fd = _open_repository_root(repository_root)
    try:
        allow_fallback = record_status == "example"
        schema_object = _load_git_object(
            root_fd,
            role="manifest_schema",
            path=SCHEMA_PATH,
            revision=schema_revision,
            maximum=MAX_SCHEMA_BYTES,
            allow_example_head_fallback=allow_fallback,
        )
        contract_object = _load_git_object(
            root_fd,
            role="normative_contract",
            path=CONTRACT_PATH,
            revision=contract_revision,
            maximum=MAX_CONTRACT_BYTES,
            allow_example_head_fallback=allow_fallback,
        )
        if (
            schema_object.size_bytes != EXPECTED_SCHEMA_SIZE
            or schema_object.sha256 != EXPECTED_SCHEMA_SHA256
            or schema_object.git_blob_sha1 != EXPECTED_SCHEMA_GIT_BLOB_SHA1
        ):
            _raise("schema_repository_object_mismatch", stage="repository_binding")
        if (
            contract_object.size_bytes != EXPECTED_CONTRACT_SIZE
            or contract_object.sha256 != EXPECTED_CONTRACT_SHA256
            or contract_object.git_blob_sha1 != EXPECTED_CONTRACT_GIT_BLOB_SHA1
        ):
            _raise("contract_repository_object_mismatch", stage="repository_binding")
        schema_document, _ = _parse_json_object(
            schema_object.exact_bytes,
            stage="schema",
            member_path=SCHEMA_PATH,
            allow_bom=False,
        )
        contract_document, _ = _parse_json_object(
            contract_object.exact_bytes,
            stage="contract",
            member_path=CONTRACT_PATH,
            allow_bom=False,
        )
        return (
            schema_object,
            contract_object,
            schema_document,
            contract_document,
            root_fd,
        )
    except BaseException:
        os.close(root_fd)
        raise


def _scan_schema_references(value: Any) -> None:
    pending: list[Any] = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, item in current.items():
                if key in SCHEMA_REFERENCE_KEYWORDS:
                    if not isinstance(item, str) or not item.startswith("#"):
                        _raise("external_schema_reference_forbidden", stage="schema")
                pending.append(item)
        elif isinstance(current, list):
            pending.extend(current)


def _registry_api_available() -> bool:
    if ReferencingRegistry is None or NoSuchResource is None:
        return False
    try:
        parameters = inspect.signature(
            jsonschema.Draft202012Validator.__init__
        ).parameters
    except (TypeError, ValueError):
        return False
    return "registry" in parameters


def _deny_schema_retrieval(uri: str) -> Any:
    if NoSuchResource is None:
        raise ClosedSchemaReferenceError(uri)
    raise NoSuchResource(ref=uri)


def _build_closed_schema_validator(schema: dict[str, Any]) -> Any:
    _scan_schema_references(schema)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError:
        _raise("manifest_schema_self_check_failed", stage="schema")
    common = {"format_checker": jsonschema.FormatChecker()}
    if _registry_api_available():
        registry = ReferencingRegistry(retrieve=_deny_schema_retrieval)
        return jsonschema.Draft202012Validator(
            schema,
            registry=registry,
            **common,
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver_class = getattr(jsonschema, "RefResolver", None)
    if resolver_class is None:
        _raise("closed_schema_resolver_unavailable", stage="schema")

    class ClosedResolver(resolver_class):
        def resolve_remote(self, uri: str) -> Any:
            raise ClosedSchemaReferenceError(uri)

    resolver = ClosedResolver.from_schema(schema, cache_remote=False)
    return jsonschema.Draft202012Validator(
        schema,
        resolver=resolver,
        **common,
    )


def _validate_schema_identity(schema: dict[str, Any]) -> None:
    expected = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://github.com/HKati/pulse-release-gates-0.1/"
            + SCHEMA_PATH
        ),
        "type": "object",
        "additionalProperties": False,
    }
    for field, value in expected.items():
        if schema.get(field) != value:
            _raise("manifest_schema_identity_mismatch", stage="schema")
    properties = _require_object(
        schema.get("properties"),
        error_code="manifest_schema_properties_invalid",
        stage="schema",
    )
    if properties.get("schema_version", {}).get("const") != SCHEMA_VERSION:
        _raise("manifest_schema_version_const_mismatch", stage="schema")
    if properties.get("document_type", {}).get("const") != DOCUMENT_TYPE:
        _raise("manifest_document_type_const_mismatch", stage="schema")


def _expected_subject() -> dict[str, Any]:
    return {
        "event_name": SUBJECT_EVENT,
        "head_branch": SUBJECT_HEAD_BRANCH,
        "head_repository": REPOSITORY,
        "head_repository_id": REPOSITORY_ID,
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "repository_is_fork": False,
        "run_conclusion": "success",
        "run_created_utc": SUBJECT_RUN_CREATED_UTC,
        "run_started_utc": SUBJECT_RUN_STARTED_UTC,
        "run_status": "completed",
        "run_updated_utc": SUBJECT_RUN_UPDATED_UTC,
        "same_repository_subject": True,
        "source_commit": SUBJECT_SOURCE_COMMIT,
        "source_commit_is_exact_identity": True,
        "source_ref": SUBJECT_SOURCE_REF,
        "source_ref_origin": (
            "declared_work_order_and_recorded_head_branch_reconstruction"
        ),
        "subject_class": "completed_historical_workflow_run_attempt",
        "subject_run_key": SUBJECT_RUN_KEY,
        "subject_run_key_origin": (
            "deterministic_reconstruction_from_run_id_attempt_and_workflow_name"
        ),
        "workflow_id": SUBJECT_WORKFLOW_ID,
        "workflow_name": SUBJECT_WORKFLOW_NAME,
        "workflow_path": SUBJECT_WORKFLOW_PATH,
        "workflow_run_attempt": SUBJECT_RUN_ATTEMPT,
        "workflow_run_id": SUBJECT_RUN_ID,
        "workflow_run_number": SUBJECT_RUN_NUMBER,
    }


def _expected_request_contract() -> dict[str, Any]:
    return {
        "accept": ACCEPT,
        "accept_encoding": ACCEPT_ENCODING,
        "api_version": API_VERSION,
        "authentication_environment_variable_name": TOKEN_ENV,
        "authentication_mode": "bearer_token_from_declared_environment_variable",
        "authorization_header_present": True,
        "authorization_value_recorded": False,
        "host": API_HOST,
        "jobs_per_page": MAX_JOBS_PER_PAGE,
        "jobs_query_parameter_order": ["per_page", "page"],
        "latest_attempt_resolution_allowed": False,
        "latest_run_resolution_allowed": False,
        "method": "GET",
        "non_attempt_specific_jobs_endpoint_allowed": False,
        "redirect_policy": "forbidden",
        "redirects_followed": False,
        "scheme": API_SCHEME,
        "token_value_written_to_diagnostics": False,
        "token_value_written_to_output": False,
        "user_agent": USER_AGENT,
    }


def _expected_limits() -> dict[str, Any]:
    return {
        "maximum_exchange_metadata_size_bytes": MAX_EXCHANGE_METADATA_BYTES,
        "maximum_jobs_page_count": MAX_JOBS_PAGE_COUNT,
        "maximum_jobs_per_page": MAX_JOBS_PER_PAGE,
        "maximum_response_body_size_bytes": MAX_RESPONSE_BODY_BYTES,
        "maximum_step_records_per_job": MAX_STEP_RECORDS_PER_JOB,
        "maximum_total_capture_size_bytes": MAX_TOTAL_CAPTURE_BYTES,
        "redirect_limit": 0,
    }


def _validate_exact_contract(
    contract: dict[str, Any],
    schema_object: RepositoryObject,
) -> None:
    expected_identity = {
        "document_type": "pulsemech_compute_post_run_producer_input_capture_contract",
        "record_status": "normative_contract",
        "capture_contract_id": CONTRACT_ID,
        "capture_contract_version": CONTRACT_VERSION,
    }
    for field, expected in expected_identity.items():
        if contract.get(field) != expected:
            _raise("normative_contract_identity_mismatch", stage="contract")
    work_order = _require_object(
        contract.get("work_order_binding"),
        error_code="normative_contract_work_order_invalid",
        stage="contract",
    )
    expected_work_order = {
        "repository": REPOSITORY,
        "issue": 2856,
        "step": "4A",
        "pr_position": 1,
        "pr_role": "contract_and_capture_implementation",
    }
    for field, expected in expected_work_order.items():
        if work_order.get(field) != expected:
            _raise("normative_contract_work_order_mismatch", stage="contract")
    schema_binding = _require_object(
        contract.get("schema_binding"),
        error_code="normative_contract_schema_binding_invalid",
        stage="contract",
    )
    expected_schema_binding = {
        "path": SCHEMA_PATH,
        "size_bytes": schema_object.size_bytes,
        "sha256": schema_object.sha256,
        "git_blob_sha1": schema_object.git_blob_sha1,
        "schema_version_const": SCHEMA_VERSION,
        "document_type_const": DOCUMENT_TYPE,
        "schema_dialect": "https://json-schema.org/draft/2020-12/schema",
    }
    for field, expected in expected_schema_binding.items():
        if schema_binding.get(field) != expected:
            _raise("normative_contract_schema_binding_mismatch", stage="contract")
    if contract.get("initial_reference_subject") != _expected_subject():
        _raise("normative_contract_subject_mismatch", stage="contract")
    if contract.get("request_contract") != _expected_request_contract():
        _raise("normative_contract_request_mismatch", stage="contract")
    if contract.get("limits") != _expected_limits():
        _raise("normative_contract_limits_mismatch", stage="contract")
    offline = _require_object(
        contract.get("offline_validator_contract"),
        error_code="offline_validator_contract_invalid",
        stage="contract",
    )
    expected_offline = {
        "capture_tool_import": "forbidden",
        "capture_tool_success_declaration_trusted": False,
        "network_access": "none",
        "verdict_role": "offline_capture_validation_only",
        "canonicalization_reconstruction": "separate_implementation",
        "git_blob_identity_reconstruction": (
            "sha1_of_ascii_git_blob_header_plus_exact_bytes"
        ),
    }
    for field, expected in expected_offline.items():
        if offline.get(field) != expected:
            _raise("offline_validator_contract_mismatch", stage="contract")
    input_arguments = _require_object(
        offline.get("input_arguments"),
        error_code="offline_validator_input_contract_invalid",
        stage="contract",
    )
    if input_arguments != {
        "capture_root": "--capture-root",
        "repository_root": "--repository-root",
    }:
        _raise("offline_validator_input_contract_mismatch", stage="contract")
    schema_validation = _require_object(
        offline.get("json_schema_validation"),
        error_code="offline_validator_schema_contract_invalid",
        stage="contract",
    )
    if schema_validation != {
        "dialect": "Draft_2020_12",
        "library": "jsonschema",
        "schema_check_required": True,
    }:
        _raise("offline_validator_schema_contract_mismatch", stage="contract")
    deterministic = _require_object(
        offline.get("deterministic_diagnostics"),
        error_code="offline_validator_diagnostics_contract_invalid",
        stage="contract",
    )
    if deterministic != {
        "absolute_local_paths": "forbidden",
        "error_order": "stable_stage_then_member_path_then_error_code",
        "generated_timestamps": "forbidden",
        "same_exact_input_produces_byte_identical_diagnostics": True,
    }:
        _raise("offline_validator_diagnostics_contract_mismatch", stage="contract")
    separation = _require_object(
        contract.get("implementation_separation_contract"),
        error_code="implementation_separation_contract_invalid",
        stage="contract",
    )
    if (
        separation.get("offline_validator_network_access") != "none"
        or separation.get("offline_validator_imports_capture_implementation")
        is not False
        or separation.get("capture_tool_verdict_trusted") is not False
        or separation.get("offline_validator_dependency_policy")
        != "python_standard_library_plus_jsonschema"
    ):
        _raise("implementation_separation_contract_mismatch", stage="contract")


def _manifest_branch_expected_sections(
    contract: dict[str, Any],
    record_status: str,
) -> dict[str, Any]:
    if record_status not in {"example", "observed"}:
        _raise("record_status_invalid", stage="manifest")
    temporal = copy.deepcopy(contract["temporal_boundary"])
    layout = copy.deepcopy(contract["capture_layout"])
    publication = copy.deepcopy(contract["publication_boundary"])
    authority = copy.deepcopy(contract["authority_boundary"])
    if record_status == "example":
        temporal.update(
            {
                "capture_is_platform_response_snapshot": False,
                "capture_subject_class": "contract_example",
                "capture_time_relation": "example_only",
                "reference_producer_input_eligible": False,
                "subject_run_completed_before_capture": False,
            }
        )
        layout.update(
            {
                "manifest_file_name": EXAMPLE_MANIFEST_NAME,
                "root_path": EXAMPLE_CAPTURE_ROOT,
            }
        )
        publication["publication_status"] = "example"
        authority["capture_subject_class"] = "contract_example"
    return {
        "subject": copy.deepcopy(contract["initial_reference_subject"]),
        "temporal_boundary": temporal,
        "request_contract": copy.deepcopy(contract["request_contract"]),
        "capture_layout": layout,
        "limits": copy.deepcopy(contract["limits"]),
        "implementation_boundary": copy.deepcopy(contract["implementation_boundary"]),
        "publication_boundary": publication,
        "privacy_boundary": copy.deepcopy(contract["privacy_boundary"]),
        "content_boundary": copy.deepcopy(contract["content_boundary"]),
        "availability_boundary": copy.deepcopy(contract["availability_boundary"]),
        "authority_boundary": authority,
    }


def _expected_manifest_identity(record_status: str) -> dict[str, Any]:
    if record_status == "example":
        return {
            "canonicalization": "json-sort-keys-utf8-newline",
            "capture_root": EXAMPLE_CAPTURE_ROOT,
            "capture_scope": "example",
            "manifest_file_name": EXAMPLE_MANIFEST_NAME,
            "manifest_id": "post-run-producer-input-capture:example-6066-v0",
            "manifest_self_hash_included": False,
            "member_inventory_scope": "all_capture_files_except_this_manifest",
        }
    return {
        "canonicalization": "json-sort-keys-utf8-newline",
        "capture_root": OBSERVED_CAPTURE_ROOT,
        "capture_scope": "historical_reference",
        "manifest_file_name": OBSERVED_MANIFEST_NAME,
        "manifest_id": "post-run-producer-input-capture:pulse-ci-6066-attempt-1-v0",
        "manifest_self_hash_included": False,
        "member_inventory_scope": "all_capture_files_except_this_manifest",
    }


def _expected_example_provenance() -> dict[str, Any]:
    return {
        "capture_workflow_execution_claimed": False,
        "fixture_id": (
            "fixture:pulsemech-compute-post-run-producer-input-capture-example-v0"
        ),
        "fixture_source_path": EXAMPLE_PATH,
        "intended_capture_mode": "post_run_platform_response_snapshot",
        "intended_capture_tool_path": CAPTURE_TOOL_PATH,
        "intended_capture_workflow_path": CAPTURE_WORKFLOW_PATH,
        "networked_capture_execution_claimed": False,
        "provenance_class": "checked_in_contract_example",
        "schema_identity": SCHEMA_VERSION,
    }


def _validate_observed_provenance(
    provenance: dict[str, Any],
    *,
    root_fd: int,
    bound_revision: str,
) -> None:
    stage = "repository_binding"
    if provenance.get("provenance_class") != "observed_networked_capture":
        _raise("observed_provenance_class_mismatch", stage=stage)
    implementation = _require_object(
        provenance.get("capture_implementation"),
        error_code="capture_implementation_provenance_invalid",
        stage=stage,
    )
    expected_implementation = {
        "dependency_policy": "python_standard_library_only",
        "execution_mode": "networked_capture",
        "producer_id": CONTRACT_ID,
        "producer_name": "PULSEmech compute post-run producer-input capture",
        "producer_source": CAPTURE_TOOL_PATH,
        "producer_version": "0.1.0",
    }
    for field, expected in expected_implementation.items():
        if implementation.get(field) != expected:
            _raise("capture_implementation_provenance_mismatch", stage=stage)
    implementation_revision = _require_sha40(
        implementation.get("producer_source_revision"),
        error_code="capture_implementation_revision_invalid",
        stage=stage,
    )
    if implementation_revision != bound_revision:
        _raise("capture_implementation_revision_mismatch", stage=stage)
    implementation_sha256 = _require_sha256(
        implementation.get("producer_source_sha256"),
        error_code="capture_implementation_sha256_invalid",
        stage=stage,
    )
    implementation_object = _load_git_object(
        root_fd,
        role="capture_implementation",
        path=CAPTURE_TOOL_PATH,
        revision=implementation_revision,
        maximum=MAX_CAPTURE_TOOL_BYTES,
        allow_example_head_fallback=False,
    )
    if implementation_object.sha256 != implementation_sha256:
        _raise("capture_implementation_sha256_mismatch", stage=stage)

    workflow = _require_object(
        provenance.get("capture_workflow_execution"),
        error_code="capture_workflow_provenance_invalid",
        stage=stage,
    )
    fixed_workflow = {
        "authority_effect": "none",
        "event_name": "workflow_dispatch",
        "permissions": {"actions": "read", "contents": "read"},
        "repository": REPOSITORY,
        "source_ref": "refs/heads/main",
        "workflow_name": "PULSEmech compute post-run producer-input capture",
        "workflow_path": CAPTURE_WORKFLOW_PATH,
    }
    for field, expected in fixed_workflow.items():
        if workflow.get(field) != expected:
            _raise("capture_workflow_provenance_mismatch", stage=stage)
    workflow_revision = _require_sha40(
        workflow.get("workflow_source_revision"),
        error_code="capture_workflow_revision_invalid",
        stage=stage,
    )
    if workflow_revision != bound_revision:
        _raise("capture_workflow_revision_mismatch", stage=stage)
    workflow_sha256 = _require_sha256(
        workflow.get("workflow_source_sha256"),
        error_code="capture_workflow_sha256_invalid",
        stage=stage,
    )
    workflow_object = _load_git_object(
        root_fd,
        role="capture_workflow",
        path=CAPTURE_WORKFLOW_PATH,
        revision=workflow_revision,
        maximum=MAX_WORKFLOW_BYTES,
        allow_example_head_fallback=False,
    )
    if workflow_object.sha256 != workflow_sha256:
        _raise("capture_workflow_sha256_mismatch", stage=stage)
    workflow_id = _require_int(
        workflow.get("workflow_id"),
        error_code="capture_workflow_id_invalid",
        stage=stage,
        minimum=1,
    )
    workflow_run_id = _require_int(
        workflow.get("workflow_run_id"),
        error_code="capture_workflow_run_id_invalid",
        stage=stage,
        minimum=1,
    )
    workflow_run_attempt = _require_int(
        workflow.get("workflow_run_attempt"),
        error_code="capture_workflow_run_attempt_invalid",
        stage=stage,
        minimum=1,
    )
    del workflow_id
    expected_key = (
        f"GITHUB_RUN_ID={workflow_run_id}|"
        f"GITHUB_RUN_ATTEMPT={workflow_run_attempt}|"
        "GITHUB_WORKFLOW=PULSEmech compute post-run producer-input capture"
    )
    if workflow.get("workflow_run_key") != expected_key:
        _raise("capture_workflow_run_key_mismatch", stage=stage)


def _validate_manifest_branch(
    manifest: dict[str, Any],
    *,
    record_status: str,
    manifest_name: str,
    contract: dict[str, Any],
    root_fd: int,
    bound_revision: str,
) -> None:
    stage = "boundaries"
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _raise("manifest_schema_version_mismatch", stage=stage)
    if manifest.get("document_type") != DOCUMENT_TYPE:
        _raise("manifest_document_type_mismatch", stage=stage)
    if manifest.get("record_status") != record_status:
        _raise("manifest_record_status_mismatch", stage=stage)
    if manifest.get("ok") is not True or manifest.get("errors") != []:
        _raise("manifest_success_state_invalid", stage=stage)
    expected_name = (
        EXAMPLE_MANIFEST_NAME if record_status == "example" else OBSERVED_MANIFEST_NAME
    )
    if manifest_name != expected_name:
        _raise("manifest_file_name_mismatch", stage=stage)
    identity = _require_object(
        manifest.get("manifest_identity"),
        error_code="manifest_identity_invalid",
        stage=stage,
    )
    if identity != _expected_manifest_identity(record_status):
        _raise("manifest_identity_mismatch", stage=stage)
    forbidden_identity_fields = {
        "sha256",
        "size_bytes",
        "git_blob_sha1",
        "source_revision",
    }
    if forbidden_identity_fields.intersection(identity):
        _raise("manifest_self_identity_forbidden", stage=stage)
    expected_sections = _manifest_branch_expected_sections(contract, record_status)
    for name, expected in expected_sections.items():
        if manifest.get(name) != expected:
            _raise(f"manifest_{name}_mismatch", stage=stage)
    provenance = _require_object(
        manifest.get("provenance"),
        error_code="manifest_provenance_invalid",
        stage=stage,
    )
    if record_status == "example":
        if provenance != _expected_example_provenance():
            _raise("example_provenance_mismatch", stage=stage)
    else:
        _validate_observed_provenance(
            provenance,
            root_fd=root_fd,
            bound_revision=bound_revision,
        )


def _validate_manifest_schema(
    validator: Any,
    manifest: dict[str, Any],
    *,
    manifest_name: str,
) -> None:
    try:
        errors = sorted(
            validator.iter_errors(manifest),
            key=lambda item: (
                tuple(str(part) for part in item.absolute_path),
                tuple(str(part) for part in item.absolute_schema_path),
                item.message,
            ),
        )
    except (jsonschema.SchemaError, jsonschema.ValidationError, ClosedSchemaReferenceError):
        _raise(
            "manifest_schema_validation_failed",
            stage="schema",
            member_path=manifest_name,
        )
    if errors:
        _raise(
            "manifest_schema_validation_failed",
            stage="schema",
            member_path=manifest_name,
        )


def _validate_selected_headers(
    value: Any,
    *,
    member_path: str,
) -> dict[str, Any]:
    stage = "exchange_metadata"
    selected = _require_object(
        value,
        error_code="selected_response_headers_invalid",
        stage=stage,
        member_path=member_path,
    )
    if tuple(sorted(selected)) != tuple(sorted(SELECTED_RESPONSE_HEADER_KEYS)):
        _raise(
            "selected_response_header_set_mismatch",
            stage=stage,
            member_path=member_path,
        )
    for key in SELECTED_RESPONSE_HEADER_KEYS:
        header = _require_object(
            selected.get(key),
            error_code="selected_response_header_invalid",
            stage=stage,
            member_path=member_path,
        )
        status_value = header.get("status")
        header_value = header.get("value")
        if status_value == "absent":
            if header_value is not None:
                _raise(
                    "absent_response_header_has_value",
                    stage=stage,
                    member_path=member_path,
                )
        elif status_value == "present":
            text = _require_string(
                header_value,
                error_code="present_response_header_value_invalid",
                stage=stage,
                member_path=member_path,
            )
            if len(text) > 8192:
                _raise(
                    "selected_response_header_value_too_large",
                    stage=stage,
                    member_path=member_path,
                )
        else:
            _raise(
                "selected_response_header_status_invalid",
                stage=stage,
                member_path=member_path,
            )
    content_type = selected["content_type"]
    if content_type.get("status") != "present":
        _raise("content_type_header_missing", stage=stage, member_path=member_path)
    content_type_value = _require_string(
        content_type.get("value"),
        error_code="wrong_content_type",
        stage=stage,
        member_path=member_path,
    )
    if len(content_type_value) > 256:
        _raise("wrong_content_type", stage=stage, member_path=member_path)
    if content_type_value.split(";", 1)[0].strip() != "application/json":
        _raise("wrong_content_type", stage=stage, member_path=member_path)
    content_encoding = selected["content_encoding"]
    if (
        content_encoding.get("status") == "present"
        and content_encoding.get("value") != "identity"
    ):
        _raise(
            "unsupported_content_encoding",
            stage=stage,
            member_path=member_path,
        )
    return selected


def _validate_raw_member(
    member: Any,
    payload: bytes,
    *,
    expected_role: str,
    expected_path: str,
) -> tuple[dict[str, Any], bool]:
    stage = "member_identity"
    value = _require_object(
        member,
        error_code="raw_response_member_invalid",
        stage=stage,
        member_path=expected_path,
    )
    expected_literals = {
        "role": expected_role,
        "path": expected_path,
        "media_type": "application/json",
        "byte_domain": (
            "exact_http_entity_body_returned_to_capture_implementation_"
            "before_json_parsing_or_reserialization"
        ),
        "exact_bytes_preserved": True,
        "json_normalized": False,
        "json_reformatted": False,
        "key_order_changed": False,
        "whitespace_rewritten": False,
        "newline_rewritten": False,
    }
    for field, expected in expected_literals.items():
        if value.get(field) != expected:
            _raise("raw_response_member_boundary_mismatch", stage=stage, member_path=expected_path)
    expected_identity = {
        "size_bytes": len(payload),
        "sha256": _sha256(payload),
        "git_blob_sha1": _git_blob_sha1(payload),
        "utf8_bom_present": payload.startswith(b"\xef\xbb\xbf"),
        "cr_count": payload.count(b"\r"),
        "lf_count": payload.count(b"\n"),
        "final_byte_hex": f"{payload[-1]:02x}",
        "trailing_newline_present": payload.endswith(b"\n"),
    }
    for field, expected in expected_identity.items():
        if value.get(field) != expected:
            _raise("raw_response_identity_mismatch", stage=stage, member_path=expected_path)
    parsed, bom = _parse_json_object(
        payload,
        stage="raw_response",
        member_path=expected_path,
        allow_bom=True,
    )
    return parsed, bom


def _validate_metadata_member(
    member: Any,
    payload: bytes,
    *,
    expected_role: str,
    expected_path: str,
    expected_record: dict[str, Any],
) -> None:
    stage = "member_identity"
    value = _require_object(
        member,
        error_code="exchange_metadata_member_invalid",
        stage=stage,
        member_path=expected_path,
    )
    expected_literals = {
        "role": expected_role,
        "path": expected_path,
        "media_type": "application/json",
        "canonicalization": "json-sort-keys-utf8-newline",
        "canonical_reserialization_matches": True,
        "utf8_bom_present": False,
        "cr_count": 0,
        "final_byte_hex": "0a",
        "trailing_newline_present": True,
    }
    for field, expected in expected_literals.items():
        if value.get(field) != expected:
            _raise("exchange_metadata_boundary_mismatch", stage=stage, member_path=expected_path)
    expected_bytes = _canonical_json_bytes(
        expected_record,
        stage="exchange_metadata",
        member_path=expected_path,
    )
    if payload != expected_bytes:
        _raise("exchange_metadata_canonical_bytes_mismatch", stage="exchange_metadata", member_path=expected_path)
    parsed, _ = _parse_json_object(
        payload,
        stage="exchange_metadata",
        member_path=expected_path,
        allow_bom=False,
    )
    if parsed != expected_record:
        _raise("exchange_metadata_record_mismatch", stage="exchange_metadata", member_path=expected_path)
    expected_identity = {
        "size_bytes": len(payload),
        "sha256": _sha256(payload),
        "git_blob_sha1": _git_blob_sha1(payload),
        "lf_count": payload.count(b"\n"),
    }
    for field, expected in expected_identity.items():
        if value.get(field) != expected:
            _raise("exchange_metadata_identity_mismatch", stage=stage, member_path=expected_path)


def _expected_run_request() -> dict[str, Any]:
    return {
        "accept": ACCEPT,
        "accept_encoding": ACCEPT_ENCODING,
        "api_version": API_VERSION,
        "authentication_environment_variable_name": TOKEN_ENV,
        "authentication_mode": "bearer_token_from_declared_environment_variable",
        "authorization_header_present": True,
        "authorization_value_recorded": False,
        "host": API_HOST,
        "method": "GET",
        "path": RUN_REQUEST_PATH,
        "query_parameters": [],
        "redirects_allowed": False,
        "request_target": RUN_REQUEST_PATH,
        "scheme": API_SCHEME,
        "user_agent": USER_AGENT,
    }


def _expected_jobs_request(page_number: int) -> dict[str, Any]:
    target = f"{JOBS_REQUEST_PATH}?per_page=100&page={page_number}"
    return {
        "accept": ACCEPT,
        "accept_encoding": ACCEPT_ENCODING,
        "api_version": API_VERSION,
        "authentication_environment_variable_name": TOKEN_ENV,
        "authentication_mode": "bearer_token_from_declared_environment_variable",
        "authorization_header_present": True,
        "authorization_value_recorded": False,
        "host": API_HOST,
        "method": "GET",
        "path": JOBS_REQUEST_PATH,
        "query_parameters": [
            {"name": "per_page", "value": "100"},
            {"name": "page", "value": str(page_number)},
        ],
        "redirects_allowed": False,
        "request_target": target,
        "scheme": API_SCHEME,
        "user_agent": USER_AGENT,
    }


def _validate_exchange_timing(
    value: Any,
    *,
    member_path: str,
    previous_response: dt.datetime | None,
) -> tuple[dt.datetime, dt.datetime]:
    stage = "temporal"
    timing = _require_object(
        value,
        error_code="exchange_timing_invalid",
        stage=stage,
        member_path=member_path,
    )
    started = _parse_utc(
        timing.get("capture_started_utc"),
        error_code="capture_started_utc_invalid",
        stage=stage,
        member_path=member_path,
    )
    received = _parse_utc(
        timing.get("response_received_utc"),
        error_code="response_received_utc_invalid",
        stage=stage,
        member_path=member_path,
    )
    if timing.get("response_received_not_before_capture_start") is not True:
        _raise("exchange_timing_declaration_invalid", stage=stage, member_path=member_path)
    if received < started:
        _raise("response_received_before_capture_start", stage=stage, member_path=member_path)
    if previous_response is not None and started < previous_response:
        _raise("capture_exchange_time_order_invalid", stage=stage, member_path=member_path)
    return started, received


def _repository_identity(
    value: Any,
    *,
    error_code: str,
    member_path: str,
) -> tuple[str, int, bool]:
    repository = _require_object(
        value,
        error_code=error_code,
        stage="run_subject",
        member_path=member_path,
    )
    full_name = _require_string(
        repository.get("full_name"),
        error_code=error_code,
        stage="run_subject",
        member_path=member_path,
    )
    repository_id = _require_int(
        repository.get("id"),
        error_code=error_code,
        stage="run_subject",
        member_path=member_path,
        minimum=1,
    )
    is_fork = _require_bool(
        repository.get("fork"),
        error_code=error_code,
        stage="run_subject",
        member_path=member_path,
    )
    return full_name, repository_id, is_fork


def _reconstruct_run_subject(
    raw: dict[str, Any],
    *,
    capture_started: dt.datetime,
    member_path: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    stage = "run_subject"
    run_id = _require_int(raw.get("id"), error_code="wrong_run_id", stage=stage, member_path=member_path, exact=SUBJECT_RUN_ID)
    run_number = _require_int(raw.get("run_number"), error_code="wrong_run_number", stage=stage, member_path=member_path, exact=SUBJECT_RUN_NUMBER)
    run_attempt = _require_int(raw.get("run_attempt"), error_code="wrong_run_attempt", stage=stage, member_path=member_path, exact=SUBJECT_RUN_ATTEMPT)
    workflow_name = _require_string(raw.get("name"), error_code="wrong_workflow_name", stage=stage, member_path=member_path, exact=SUBJECT_WORKFLOW_NAME)
    workflow_id = _require_int(raw.get("workflow_id"), error_code="wrong_workflow_id", stage=stage, member_path=member_path, exact=SUBJECT_WORKFLOW_ID)
    workflow_path = _require_string(raw.get("path"), error_code="wrong_workflow_path", stage=stage, member_path=member_path, exact=SUBJECT_WORKFLOW_PATH)
    event_name = _require_string(raw.get("event"), error_code="wrong_event", stage=stage, member_path=member_path, exact=SUBJECT_EVENT)
    head_branch = _require_string(raw.get("head_branch"), error_code="wrong_head_branch", stage=stage, member_path=member_path, exact=SUBJECT_HEAD_BRANCH)
    head_sha = _require_sha40(raw.get("head_sha"), error_code="wrong_source_commit", stage=stage, member_path=member_path)
    if head_sha != SUBJECT_SOURCE_COMMIT:
        _raise("wrong_source_commit", stage=stage, member_path=member_path)
    status_value = _require_string(raw.get("status"), error_code="non_completed_run", stage=stage, member_path=member_path, exact="completed")
    conclusion = _require_string(raw.get("conclusion"), error_code="non_success_reference_run", stage=stage, member_path=member_path, exact="success")
    created_at = _require_string(raw.get("created_at"), error_code="run_created_at_invalid", stage=stage, member_path=member_path, exact=SUBJECT_RUN_CREATED_UTC)
    started_at = _require_string(raw.get("run_started_at"), error_code="run_started_at_invalid", stage=stage, member_path=member_path, exact=SUBJECT_RUN_STARTED_UTC)
    updated_at = _require_string(raw.get("updated_at"), error_code="run_updated_at_invalid", stage=stage, member_path=member_path, exact=SUBJECT_RUN_UPDATED_UTC)
    created_time = _parse_utc(created_at, error_code="run_created_at_invalid", stage=stage, member_path=member_path)
    started_time = _parse_utc(started_at, error_code="run_started_at_invalid", stage=stage, member_path=member_path)
    updated_time = _parse_utc(updated_at, error_code="run_updated_at_invalid", stage=stage, member_path=member_path)
    if not (created_time <= started_time <= updated_time):
        _raise("run_timestamp_order_invalid", stage=stage, member_path=member_path)
    if capture_started < updated_time:
        _raise("capture_started_before_subject_run_completed", stage="temporal", member_path=member_path)
    repository_name, repository_id, repository_is_fork = _repository_identity(raw.get("repository"), error_code="wrong_repository_identity", member_path=member_path)
    head_repository_name, head_repository_id, head_repository_is_fork = _repository_identity(raw.get("head_repository"), error_code="wrong_head_repository_identity", member_path=member_path)
    if repository_name != REPOSITORY or repository_id != REPOSITORY_ID or repository_is_fork:
        _raise("wrong_repository_identity", stage=stage, member_path=member_path)
    if head_repository_name != REPOSITORY or head_repository_id != REPOSITORY_ID or head_repository_is_fork:
        _raise("wrong_head_repository_identity", stage=stage, member_path=member_path)
    summary = {
        "conclusion": conclusion,
        "created_at": created_at,
        "event_name": event_name,
        "head_branch": head_branch,
        "head_repository": head_repository_name,
        "head_repository_id": head_repository_id,
        "head_sha": head_sha,
        "repository": repository_name,
        "repository_id": repository_id,
        "repository_is_fork": repository_is_fork,
        "run_started_at": started_at,
        "same_repository_subject": True,
        "status": status_value,
        "updated_at": updated_at,
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    subject = {
        "event_name": event_name,
        "head_branch": head_branch,
        "head_repository": head_repository_name,
        "head_repository_id": head_repository_id,
        "repository": repository_name,
        "repository_id": repository_id,
        "repository_is_fork": repository_is_fork,
        "run_conclusion": conclusion,
        "run_created_utc": created_at,
        "run_started_utc": started_at,
        "run_status": status_value,
        "run_updated_utc": updated_at,
        "same_repository_subject": True,
        "source_commit": head_sha,
        "source_commit_is_exact_identity": True,
        "source_ref": f"refs/heads/{head_branch}",
        "source_ref_origin": "declared_work_order_and_recorded_head_branch_reconstruction",
        "subject_class": "completed_historical_workflow_run_attempt",
        "subject_run_key": f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}|GITHUB_WORKFLOW={workflow_name}",
        "subject_run_key_origin": "deterministic_reconstruction_from_run_id_attempt_and_workflow_name",
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    return summary, subject


def _validate_completed_result(
    value: dict[str, Any],
    *,
    label: str,
    member_path: str,
) -> None:
    stage = "jobs_binding"
    _require_string(value.get("status"), error_code=f"{label}_status_invalid", stage=stage, member_path=member_path, exact="completed")
    conclusion = _require_string(value.get("conclusion"), error_code=f"{label}_conclusion_invalid", stage=stage, member_path=member_path)
    if conclusion not in {"success", "skipped"}:
        _raise(f"{label}_conclusion_invalid", stage=stage, member_path=member_path)
    started = value.get("started_at")
    completed = value.get("completed_at")
    if conclusion == "success":
        start_time = _parse_utc(started, error_code=f"{label}_started_at_invalid", stage=stage, member_path=member_path)
        completed_time = _parse_utc(completed, error_code=f"{label}_completed_at_invalid", stage=stage, member_path=member_path)
        if start_time > completed_time:
            _raise(f"{label}_timestamp_order_invalid", stage=stage, member_path=member_path)
        return
    if started is None and completed is None:
        return
    if started is None or completed is None:
        _raise(f"{label}_skipped_timestamp_pair_invalid", stage=stage, member_path=member_path)
    start_time = _parse_utc(started, error_code=f"{label}_started_at_invalid", stage=stage, member_path=member_path)
    completed_time = _parse_utc(completed, error_code=f"{label}_completed_at_invalid", stage=stage, member_path=member_path)
    if start_time > completed_time:
        _raise(f"{label}_timestamp_order_invalid", stage=stage, member_path=member_path)


def _reconstruct_jobs_page(
    raw: dict[str, Any],
    *,
    page_number: int,
    subject: dict[str, Any],
    all_job_ids: set[int],
    member_path: str,
) -> tuple[dict[str, Any], int, int]:
    stage = "jobs_binding"
    total_count = _require_int(raw.get("total_count"), error_code="jobs_total_count_invalid", stage=stage, member_path=member_path, minimum=0)
    jobs = _require_array(raw.get("jobs"), error_code="jobs_array_missing", stage=stage, member_path=member_path)
    if len(jobs) > MAX_JOBS_PER_PAGE:
        _raise("jobs_per_page_limit_exceeded", stage=stage, member_path=member_path)
    page_job_ids: list[int] = []
    step_count = 0
    for job_index, raw_job in enumerate(jobs):
        job = _require_object(raw_job, error_code="job_record_not_object", stage=stage, member_path=member_path)
        job_id = _require_int(job.get("id"), error_code="job_id_invalid", stage=stage, member_path=member_path, minimum=1)
        if job_id in all_job_ids:
            _raise("duplicate_job_id", stage=stage, member_path=member_path)
        all_job_ids.add(job_id)
        page_job_ids.append(job_id)
        _require_int(job.get("run_id"), error_code="job_run_id_mismatch", stage=stage, member_path=member_path, exact=subject["workflow_run_id"])
        _require_int(job.get("run_attempt"), error_code="job_run_attempt_mismatch", stage=stage, member_path=member_path, exact=subject["workflow_run_attempt"])
        _require_string(job.get("workflow_name"), error_code="job_workflow_name_mismatch", stage=stage, member_path=member_path, exact=subject["workflow_name"])
        head_sha = _require_sha40(job.get("head_sha"), error_code="job_head_sha_mismatch", stage=stage, member_path=member_path)
        if head_sha != subject["source_commit"]:
            _raise("job_head_sha_mismatch", stage=stage, member_path=member_path)
        _require_string(job.get("name"), error_code="job_name_invalid", stage=stage, member_path=member_path)
        _validate_completed_result(job, label=f"job_{job_index}", member_path=member_path)
        raw_steps = job.get("steps")
        if raw_steps is None:
            continue
        steps = _require_array(raw_steps, error_code="job_steps_not_array", stage=stage, member_path=member_path)
        if len(steps) > MAX_STEP_RECORDS_PER_JOB:
            _raise("step_record_limit_exceeded", stage=stage, member_path=member_path)
        previous_number = 0
        seen_numbers: set[int] = set()
        for step_index, raw_step in enumerate(steps):
            step = _require_object(raw_step, error_code="step_record_not_object", stage=stage, member_path=member_path)
            number = _require_int(step.get("number"), error_code="step_number_invalid", stage=stage, member_path=member_path, minimum=1)
            if number in seen_numbers:
                _raise("duplicate_step_number", stage=stage, member_path=member_path)
            if number <= previous_number:
                _raise("step_order_invalid", stage=stage, member_path=member_path)
            seen_numbers.add(number)
            previous_number = number
            _require_string(step.get("name"), error_code="step_name_invalid", stage=stage, member_path=member_path)
            _validate_completed_result(step, label=f"job_{job_index}_step_{step_index}", member_path=member_path)
            step_count += 1
            if step_count > MAX_STEP_RECORDS_PER_PAGE:
                _raise("step_records_per_page_limit_exceeded", stage=stage, member_path=member_path)
    summary = {
        "all_jobs_match_head_sha": True,
        "all_jobs_match_run_attempt": True,
        "all_jobs_match_subject_run": True,
        "all_jobs_match_workflow_name": True,
        "job_ids": page_job_ids,
        "job_ids_unique_within_page": len(page_job_ids) == len(set(page_job_ids)),
        "jobs_on_page": len(jobs),
        "page_number": page_number,
        "per_page": MAX_JOBS_PER_PAGE,
        "reported_total_count": total_count,
        "status_conclusion_relations_valid": True,
        "step_numbers_unique_and_ordered_within_job": True,
        "step_records_on_page": step_count,
    }
    return summary, total_count, step_count


def _split_link_header(value: str, *, member_path: str) -> list[str]:
    entries: list[str] = []
    start = 0
    in_angle = False
    in_quote = False
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if in_quote and character == "\\":
            escaped = True
            continue
        if character == '"':
            in_quote = not in_quote
            continue
        if not in_quote:
            if character == "<":
                if in_angle:
                    _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
                in_angle = True
            elif character == ">":
                if not in_angle:
                    _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
                in_angle = False
            elif character == "," and not in_angle:
                entry = value[start:index].strip()
                if not entry:
                    _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
                entries.append(entry)
                start = index + 1
    if in_angle or in_quote or escaped:
        _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
    final = value[start:].strip()
    if not final:
        _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
    entries.append(final)
    return entries


def _next_target_from_selected_link(
    selected: dict[str, Any],
    *,
    current_page: int,
    member_path: str,
) -> tuple[str | None, str]:
    link = _require_object(selected.get("link"), error_code="link_header_invalid", stage="pagination", member_path=member_path)
    status_value = link.get("status")
    if status_value == "absent":
        if link.get("value") is not None:
            _raise("absent_link_header_has_value", stage="pagination", member_path=member_path)
        return None, "absent"
    if status_value != "present":
        _raise("link_header_status_invalid", stage="pagination", member_path=member_path)
    raw_value = _require_string(link.get("value"), error_code="link_header_value_invalid", stage="pagination", member_path=member_path)
    next_urls: list[str] = []
    next_relation_count = 0
    for entry in _split_link_header(raw_value, member_path=member_path):
        if not entry.startswith("<") or ">" not in entry:
            _raise("link_header_syntax_invalid", stage="pagination", member_path=member_path)
        closing = entry.find(">")
        url = entry[1:closing]
        parameter_text = entry[closing + 1 :]
        relations: list[str] = []
        for parameter in parameter_text.split(";"):
            parameter = parameter.strip()
            if not parameter:
                continue
            name, separator, raw_parameter_value = parameter.partition("=")
            if not separator or name.strip().lower() != "rel":
                continue
            relation_value = raw_parameter_value.strip()
            if len(relation_value) >= 2 and relation_value[0] == relation_value[-1] == '"':
                relation_value = relation_value[1:-1]
            relations.extend(relation_value.split())
        count = relations.count("next")
        next_relation_count += count
        if count:
            next_urls.append(url)
    if next_relation_count > 1 or len(next_urls) > 1:
        _raise("duplicate_rel_next", stage="pagination", member_path=member_path)
    if not next_urls:
        return None, "present"
    parsed = urlsplit(next_urls[0])
    if parsed.scheme != API_SCHEME or parsed.hostname != API_HOST:
        _raise("link_next_origin_mismatch", stage="pagination", member_path=member_path)
    if parsed.username is not None or parsed.password is not None:
        _raise("link_next_userinfo_forbidden", stage="pagination", member_path=member_path)
    try:
        if parsed.port is not None:
            _raise("link_next_port_forbidden", stage="pagination", member_path=member_path)
    except ValueError:
        _raise("link_next_port_invalid", stage="pagination", member_path=member_path)
    if parsed.fragment:
        _raise("link_next_fragment_forbidden", stage="pagination", member_path=member_path)
    if parsed.path != JOBS_REQUEST_PATH:
        _raise("link_next_path_mismatch", stage="pagination", member_path=member_path)
    expected_next_page = current_page + 1
    if expected_next_page > MAX_JOBS_PAGE_COUNT:
        _raise("maximum_page_count_exceeded", stage="pagination", member_path=member_path)
    expected_query = f"per_page=100&page={expected_next_page}"
    if parsed.query != expected_query:
        _raise("link_next_query_mismatch", stage="pagination", member_path=member_path)
    return parsed.path + "?" + parsed.query, "present"


def _validate_response_admission(
    response: dict[str, Any],
    *,
    member_path: str,
) -> dict[str, Any]:
    expected = {
        "http_status": 200,
        "redirect_observed": False,
        "body_complete": True,
        "body_truncated": False,
        "content_type_accepted": True,
        "content_encoding_supported": True,
    }
    for field, value in expected.items():
        if response.get(field) != value:
            _raise("response_admission_state_invalid", stage="exchange_metadata", member_path=member_path)
    return _validate_selected_headers(response.get("selected_headers"), member_path=member_path)


def _validate_run_exchange(
    manifest: dict[str, Any],
    snapshot: CaptureSnapshot,
    *,
    record_status: str,
) -> tuple[dict[str, Any], dt.datetime]:
    wrapper = _require_object(manifest.get("run_attempt_exchange"), error_code="run_attempt_exchange_invalid", stage="run_exchange")
    record = _require_object(wrapper.get("record"), error_code="run_attempt_exchange_record_invalid", stage="run_exchange", member_path=RUN_METADATA_PATH)
    expected_exchange_id = (
        "post-run-capture-exchange:example-6066-attempt-1-run"
        if record_status == "example"
        else "post-run-capture-exchange:pulse-ci-6066-attempt-1-run"
    )
    if record.get("exchange_id") != expected_exchange_id or record.get("semantic_role") != "run_attempt_exchange":
        _raise("run_attempt_exchange_identity_mismatch", stage="run_exchange", member_path=RUN_METADATA_PATH)
    if record.get("request") != _expected_run_request():
        _raise("run_attempt_request_mismatch", stage="run_exchange", member_path=RUN_METADATA_PATH)
    response = _require_object(record.get("response"), error_code="run_attempt_response_record_invalid", stage="run_exchange", member_path=RUN_METADATA_PATH)
    _validate_response_admission(response, member_path=RUN_METADATA_PATH)
    started, received = _validate_exchange_timing(response.get("timing"), member_path=RUN_METADATA_PATH, previous_response=None)
    if RUN_BODY_PATH not in snapshot.files or RUN_METADATA_PATH not in snapshot.files:
        _raise("missing_declared_member", stage="inventory")
    raw, _ = _validate_raw_member(response.get("body_member"), snapshot.files[RUN_BODY_PATH], expected_role="run_attempt_response_body", expected_path=RUN_BODY_PATH)
    summary, subject = _reconstruct_run_subject(raw, capture_started=started, member_path=RUN_BODY_PATH)
    if response.get("summary") != summary:
        _raise("run_attempt_summary_mismatch", stage="run_subject", member_path=RUN_METADATA_PATH)
    if manifest.get("subject") != subject:
        _raise("run_attempt_subject_binding_mismatch", stage="run_subject", member_path=RUN_BODY_PATH)
    if wrapper.get("metadata_record_canonical_bytes_equal_record") is not True:
        _raise("run_attempt_metadata_relation_invalid", stage="exchange_metadata", member_path=RUN_METADATA_PATH)
    _validate_metadata_member(wrapper.get("metadata_member"), snapshot.files[RUN_METADATA_PATH], expected_role="run_attempt_exchange_metadata", expected_path=RUN_METADATA_PATH, expected_record=record)
    return subject, received


def _validate_jobs_pages(
    manifest: dict[str, Any],
    snapshot: CaptureSnapshot,
    *,
    record_status: str,
    subject: dict[str, Any],
    previous_response: dt.datetime,
) -> tuple[int, int, int, list[int], set[str]]:
    exchanges = _require_array(manifest.get("jobs_page_exchanges"), error_code="jobs_page_exchanges_invalid", stage="jobs_pages")
    if not exchanges or len(exchanges) > MAX_JOBS_PAGE_COUNT:
        _raise("jobs_page_count_invalid", stage="jobs_pages")
    all_job_ids: set[int] = set()
    reported_total: int | None = None
    total_steps = 0
    page_sequence: list[int] = []
    expected_member_paths: set[str] = {RUN_BODY_PATH, RUN_METADATA_PATH}
    expected_next_request = FIRST_JOBS_REQUEST_TARGET
    for index, raw_wrapper in enumerate(exchanges, start=1):
        body_path = JOBS_BODY_TEMPLATE % index
        metadata_path = JOBS_METADATA_TEMPLATE % index
        expected_member_paths.update({body_path, metadata_path})
        if body_path not in snapshot.files or metadata_path not in snapshot.files:
            _raise("missing_jobs_page", stage="inventory", member_path=body_path)
        wrapper = _require_object(raw_wrapper, error_code="jobs_page_exchange_invalid", stage="jobs_pages", member_path=metadata_path)
        record = _require_object(wrapper.get("record"), error_code="jobs_page_exchange_record_invalid", stage="jobs_pages", member_path=metadata_path)
        prefix = "example-" if record_status == "example" else "pulse-ci-"
        expected_exchange_id = f"post-run-capture-exchange:{prefix}6066-attempt-1-jobs-page-{index}"
        if record.get("exchange_id") != expected_exchange_id or record.get("semantic_role") != "jobs_page_exchange" or record.get("page_number") != index:
            _raise("jobs_page_exchange_identity_mismatch", stage="jobs_pages", member_path=metadata_path)
        expected_request = _expected_jobs_request(index)
        if record.get("request") != expected_request:
            _raise("jobs_page_request_mismatch", stage="jobs_pages", member_path=metadata_path)
        if expected_request["request_target"] != expected_next_request:
            _raise("jobs_page_request_chain_mismatch", stage="pagination", member_path=metadata_path)
        response = _require_object(record.get("response"), error_code="jobs_page_response_record_invalid", stage="jobs_pages", member_path=metadata_path)
        selected = _validate_response_admission(response, member_path=metadata_path)
        _, received = _validate_exchange_timing(response.get("timing"), member_path=metadata_path, previous_response=previous_response)
        previous_response = received
        raw, _ = _validate_raw_member(response.get("body_member"), snapshot.files[body_path], expected_role="jobs_page_response_body", expected_path=body_path)
        summary, page_total, page_steps = _reconstruct_jobs_page(raw, page_number=index, subject=subject, all_job_ids=all_job_ids, member_path=body_path)
        if response.get("summary") != summary:
            _raise("jobs_page_summary_mismatch", stage="jobs_binding", member_path=metadata_path)
        if reported_total is None:
            reported_total = page_total
        elif page_total != reported_total:
            _raise("page_total_count_disagreement", stage="pagination", member_path=body_path)
        total_steps += page_steps
        if total_steps > MAX_TOTAL_STEP_RECORDS:
            _raise("total_step_record_limit_exceeded", stage="jobs_binding", member_path=body_path)
        next_target, link_status = _next_target_from_selected_link(selected, current_page=index, member_path=metadata_path)
        expected_relation = {
            "is_final_page": next_target is None,
            "link_header_status": link_status,
            "next_page_number": None if next_target is None else index + 1,
            "next_relation_status": "closed_by_absence" if next_target is None else "present",
            "next_request_target": next_target,
            "page_number": index,
            "relation_source": "selected_link_header",
        }
        if record.get("pagination_relation") != expected_relation:
            _raise("pagination_relation_mismatch", stage="pagination", member_path=metadata_path)
        if index < len(exchanges) and next_target is None:
            _raise("incomplete_pagination", stage="pagination", member_path=metadata_path)
        if index == len(exchanges) and next_target is not None:
            _raise("final_next_link_still_present", stage="pagination", member_path=metadata_path)
        expected_next_request = next_target or ""
        if wrapper.get("metadata_record_canonical_bytes_equal_record") is not True:
            _raise("jobs_page_metadata_relation_invalid", stage="exchange_metadata", member_path=metadata_path)
        _validate_metadata_member(wrapper.get("metadata_member"), snapshot.files[metadata_path], expected_role="jobs_page_exchange_metadata", expected_path=metadata_path, expected_record=record)
        page_sequence.append(index)
    if reported_total is None:
        _raise("reported_total_count_missing", stage="pagination")
    unique_jobs = len(all_job_ids)
    if reported_total != unique_jobs:
        _raise("reported_total_count_mismatch", stage="pagination")
    expected_page_count = max(1, math.ceil(reported_total / MAX_JOBS_PER_PAGE))
    if len(exchanges) != expected_page_count:
        _raise("pagination_page_count_relation_mismatch", stage="pagination")
    if record_status == "observed" and reported_total != EXPECTED_OBSERVED_JOB_COUNT:
        _raise("initial_reference_job_count_mismatch", stage="pagination")
    return len(exchanges), unique_jobs, total_steps, page_sequence, expected_member_paths


def _validate_counts_and_pagination(
    manifest: dict[str, Any],
    *,
    page_count: int,
    job_count: int,
    step_count: int,
    page_sequence: list[int],
) -> None:
    stage = "pagination_counts"
    expected_counts = {
        "count_relations_verified": True,
        "declared_non_manifest_member_count": 2 + (2 * page_count),
        "duplicate_job_id_count": 0,
        "duplicate_step_number_count": 0,
        "exchange_metadata_member_count": 1 + page_count,
        "jobs_page_exchange_count": page_count,
        "raw_response_member_count": 1 + page_count,
        "reconstructed_step_record_count": step_count,
        "reconstructed_unique_job_count": job_count,
        "reported_job_count": job_count,
        "run_attempt_exchange_count": 1,
    }
    if manifest.get("counts") != expected_counts:
        _raise("manifest_count_relation_mismatch", stage=stage)
    expected_pagination = {
        "closure_status": "closed",
        "final_next_link_absent": True,
        "first_page": 1,
        "link_following_mode": "exact_rel_next",
        "link_header_absence_recorded": True,
        "maximum_page_count": MAX_JOBS_PAGE_COUNT,
        "page_count": page_count,
        "page_sequence": page_sequence,
        "pagination_mode": "attempt_specific_jobs_rel_next",
        "per_page": MAX_JOBS_PER_PAGE,
        "reconstructed_unique_job_count": job_count,
        "reported_total_count": job_count,
        "reported_total_equals_reconstructed": True,
    }
    if manifest.get("pagination") != expected_pagination:
        _raise("manifest_pagination_relation_mismatch", stage=stage)


def _validate_exact_inventory(
    snapshot: CaptureSnapshot,
    *,
    expected_member_paths: set[str],
) -> None:
    expected = set(expected_member_paths)
    expected.add(snapshot.manifest_name)
    observed = set(snapshot.files)
    if observed != expected:
        missing = expected.difference(observed)
        extra = observed.difference(expected)
        if missing:
            _raise("missing_declared_member", stage="inventory", member_path=sorted(missing)[0])
        _raise("undeclared_extra_member", stage="inventory", member_path=sorted(extra)[0])


def _scan_capture_for_secret_material(snapshot: CaptureSnapshot) -> None:
    for member_path in sorted(snapshot.files):
        payload = snapshot.files[member_path]
        if b"Bearer " in payload or KNOWN_GITHUB_TOKEN_RE.search(payload):
            _raise("secret_value_in_output", stage="privacy", member_path=member_path)


def _validate_manifest_canonical_bytes(
    manifest: dict[str, Any],
    payload: bytes,
    *,
    manifest_name: str,
) -> None:
    expected = _canonical_json_bytes(
        manifest,
        stage="manifest",
        member_path=manifest_name,
    )
    if payload != expected:
        _raise("manifest_canonicalization_failure", stage="manifest", member_path=manifest_name)


def validate_capture(
    *,
    repository_root: str | os.PathLike[str],
    capture_root: str | os.PathLike[str],
) -> ValidationResult:
    _install_network_audit_guard()
    _validate_runtime_platform()
    snapshot = _snapshot_capture_root(Path(capture_root))
    manifest_payload = snapshot.files[snapshot.manifest_name]
    manifest, _ = _parse_json_object(
        manifest_payload,
        stage="manifest",
        member_path=snapshot.manifest_name,
        allow_bom=False,
    )
    _validate_manifest_canonical_bytes(
        manifest,
        manifest_payload,
        manifest_name=snapshot.manifest_name,
    )
    record_status = _require_string(
        manifest.get("record_status"),
        error_code="record_status_invalid",
        stage="manifest",
    )
    if record_status not in {"example", "observed"}:
        _raise("record_status_invalid", stage="manifest")
    (
        schema_object,
        contract_object,
        schema_document,
        contract_document,
        repository_fd,
    ) = _load_manifest_bound_schema_and_contract(
        Path(repository_root),
        manifest,
        record_status=record_status,
    )
    try:
        example_fallback_revision: str | None = None
        if record_status == "example" and (
            not schema_object.revision_object_verified
            or not contract_object.revision_object_verified
        ):
            if (
                schema_object.revision_object_verified
                != contract_object.revision_object_verified
            ):
                _raise(
                    "example_binding_revision_partial_resolution",
                    stage="repository_binding",
                )
            if schema_object.resolved_revision != contract_object.resolved_revision:
                _raise(
                    "example_binding_fallback_revision_mismatch",
                    stage="repository_binding",
                )
            example_fallback_revision = schema_object.resolved_revision
            _, raw_head = _run_git(
                repository_fd,
                ["rev-parse", "HEAD"],
                maximum_output=128,
            )
            try:
                repository_head = raw_head.decode(
                    "ascii",
                    errors="strict",
                ).strip()
            except UnicodeDecodeError:
                _raise(
                    "repository_head_revision_invalid",
                    stage="repository_binding",
                )
            _require_sha40(
                repository_head,
                error_code="repository_head_revision_invalid",
                stage="repository_binding",
            )
            canonical_example = _load_git_object(
                repository_fd,
                role="canonical_example",
                path=EXAMPLE_PATH,
                revision=repository_head,
                maximum=MAX_MANIFEST_BYTES,
                allow_example_head_fallback=False,
            )
            if canonical_example.exact_bytes != manifest_payload:
                _raise(
                    "example_unresolved_revision_not_canonical",
                    stage="repository_binding",
                    member_path=snapshot.manifest_name,
                )
        del contract_object
        _validate_schema_identity(schema_document)
        validator = _build_closed_schema_validator(schema_document)
        _validate_exact_contract(contract_document, schema_object)
        _validate_manifest_schema(
            validator,
            manifest,
            manifest_name=snapshot.manifest_name,
        )
        bound_revision = manifest["contract_bindings"]["manifest_schema"]["source_revision"]
        _validate_manifest_branch(
            manifest,
            record_status=record_status,
            manifest_name=snapshot.manifest_name,
            contract=contract_document,
            root_fd=repository_fd,
            bound_revision=bound_revision,
        )
        _scan_capture_for_secret_material(snapshot)
        subject, run_received = _validate_run_exchange(
            manifest,
            snapshot,
            record_status=record_status,
        )
        page_count, job_count, step_count, page_sequence, member_paths = _validate_jobs_pages(
            manifest,
            snapshot,
            record_status=record_status,
            subject=subject,
            previous_response=run_received,
        )
        _validate_exact_inventory(snapshot, expected_member_paths=member_paths)
        _validate_counts_and_pagination(
            manifest,
            page_count=page_count,
            job_count=job_count,
            step_count=step_count,
            page_sequence=page_sequence,
        )
        if (
            snapshot.total_size_bytes
            > contract_document["limits"]["maximum_total_capture_size_bytes"]
        ):
            _raise("total_capture_size_limit_exceeded", stage="inventory")
        if example_fallback_revision is not None:
            _, raw_final_head = _run_git(
                repository_fd,
                ["rev-parse", "HEAD"],
                maximum_output=128,
            )
            try:
                final_head = raw_final_head.decode(
                    "ascii",
                    errors="strict",
                ).strip()
            except UnicodeDecodeError:
                _raise(
                    "repository_head_revision_invalid",
                    stage="repository_binding",
                )
            if final_head != example_fallback_revision:
                _raise(
                    "repository_head_changed_during_validation",
                    stage="repository_binding",
                )
        final_snapshot = _snapshot_capture_root(Path(capture_root))
        if (
            final_snapshot.manifest_name != snapshot.manifest_name
            or final_snapshot.total_size_bytes != snapshot.total_size_bytes
            or dict(final_snapshot.files) != dict(snapshot.files)
        ):
            _raise("capture_root_changed_during_validation", stage="capture_root")
        return ValidationResult(
            record_status=record_status,
            manifest_file_name=snapshot.manifest_name,
            manifest_sha256=_sha256(manifest_payload),
            page_count=page_count,
            job_count=job_count,
            step_record_count=step_count,
            authority_effect="none",
        )
    finally:
        os.close(repository_fd)


def _success_diagnostic(result: ValidationResult) -> bytes:
    return _canonical_json_bytes(
        {
            "authority_effect": result.authority_effect,
            "job_count": result.job_count,
            "manifest_file_name": result.manifest_file_name,
            "manifest_sha256": result.manifest_sha256,
            "ok": True,
            "page_count": result.page_count,
            "record_status": result.record_status,
            "result": "validated_offline",
            "step_record_count": result.step_record_count,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        },
        stage="runtime",
        member_path="diagnostic.json",
    )


def _failure_diagnostic(error: ValidationError) -> bytes:
    return _canonical_json_bytes(
        {
            "authority_effect": "none",
            "error_code": error.error_code,
            "member_path": error.member_path,
            "ok": False,
            "stage": error.stage,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        },
        stage="runtime",
        member_path="diagnostic.json",
    )


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        _raise("command_line_invalid", stage="runtime")


def parse_args() -> argparse.Namespace:
    parser = _FailClosedArgumentParser(
        description=(
            "Validate one preserved PULSEmech post-run producer-input capture "
            "using local exact bytes only and no network access."
        )
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--capture-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = validate_capture(
        repository_root=args.repository_root,
        capture_root=args.capture_root,
    )
    sys.stdout.buffer.write(_success_diagnostic(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        sys.stderr.buffer.write(_failure_diagnostic(exc))
        raise SystemExit(2)
    except KeyboardInterrupt:
        error = ValidationError(
            "validation_interrupted",
            stage="runtime",
        )
        sys.stderr.buffer.write(_failure_diagnostic(error))
        raise SystemExit(2)
    except SystemExit:
        raise
    except BaseException:
        error = ValidationError(
            "unexpected_internal_error",
            stage="runtime",
        )
        sys.stderr.buffer.write(_failure_diagnostic(error))
        raise SystemExit(2)
