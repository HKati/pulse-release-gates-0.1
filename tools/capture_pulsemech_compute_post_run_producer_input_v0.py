#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"error_code":"isolated_python_runtime_required",'
    '"ok":false,'
    '"tool":"capture_pulsemech_compute_post_run_producer_input_v0",'
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
import ctypes
import datetime as dt
import errno
import hashlib
import http.client
import json
import math
import os
import re
import secrets
import signal
import ssl
import stat
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol, Sequence


TOOL_NAME = "capture_pulsemech_compute_post_run_producer_input_v0"
TOOL_VERSION = "0.1.0"
PRODUCER_ID = "pulsemech_compute_post_run_producer_input_capture_v0"
PRODUCER_NAME = "PULSEmech compute post-run producer-input capture"
DOCUMENT_TYPE = "pulsemech_compute_post_run_producer_input_capture_manifest"
SCHEMA_VERSION = "pulsemech_compute_post_run_producer_input_capture_manifest_v0"

SUPPORTED_PLATFORM_PREFIX = "linux"
SUPPORTED_OS_NAME = "posix"

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
EXPECTED_JOB_COUNT = 8

CAPTURE_WORKFLOW_NAME = "PULSEmech compute post-run producer-input capture"
CAPTURE_WORKFLOW_PATH = (
    ".github/workflows/"
    "pulsemech_compute_post_run_producer_input_capture_v0.yml"
)
CAPTURE_WORKFLOW_ID_ENV = "PULSEMECH_CAPTURE_WORKFLOW_ID"
CAPTURE_SOURCE_REF = "refs/heads/main"

SCHEMA_PATH = (
    "schemas/"
    "pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json"
)
CONTRACT_PATH = (
    "contracts/pulsemech_compute_post_run_producer_input_capture_v0.json"
)
TOOL_PATH = "tools/capture_pulsemech_compute_post_run_producer_input_v0.py"
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
REQUEST_TIMEOUT_SECONDS = 30

RUN_REQUEST_PATH = (
    "/repos/HKati/pulse-release-gates-0.1/"
    "actions/runs/29249887581/attempts/1"
)
JOBS_REQUEST_PATH = RUN_REQUEST_PATH + "/jobs"
FIRST_JOBS_REQUEST_TARGET = JOBS_REQUEST_PATH + "?per_page=100&page=1"

MAX_RESPONSE_BODY_BYTES = 8 * 1024 * 1024
MAX_EXCHANGE_METADATA_BYTES = 1 * 1024 * 1024
MAX_TOTAL_CAPTURE_BYTES = 64 * 1024 * 1024
MAX_JOBS_PAGE_COUNT = 100
MAX_JOBS_PER_PAGE = 100
MAX_STEP_RECORDS_PER_JOB = 10_000
MAX_STEP_RECORDS_PER_PAGE = 100_000
MAX_TOTAL_STEP_RECORDS = 1_000_000
MAX_SOURCE_FILE_BYTES = 8 * 1024 * 1024
MAX_WORKFLOW_FILE_BYTES = 1 * 1024 * 1024
MAX_TOKEN_BYTES = 4096
MIN_TOKEN_BYTES = 20
HTTP_READ_CHUNK_BYTES = 64 * 1024

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

SELECTED_RESPONSE_HEADERS = (
    "Content-Encoding",
    "Content-Type",
    "Deprecation",
    "ETag",
    "Link",
    "Sunset",
    "X-GitHub-Request-Id",
)

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
ERROR_CODE_RE = re.compile(r"^[a-z0-9_]+$")
# Enforce time-of-day ranges before fromisoformat can normalize them.
CANONICAL_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?Z$"
)
CANONICAL_POSITIVE_DECIMAL_RE = re.compile(r"^[1-9][0-9]*$")
SAFE_LEAF_RE = re.compile(r"^[A-Za-z0-9._-]+$")

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


class CaptureError(RuntimeError):
    """One deterministic fail-closed capture rejection."""

    def __init__(self, error_code: str) -> None:
        if ERROR_CODE_RE.fullmatch(error_code) is None:
            error_code = "invalid_internal_error_code"
        super().__init__(error_code)
        self.error_code = error_code


class StrictJsonError(ValueError):
    pass


@dataclass(frozen=True)
class RepositoryObject:
    role: str
    path: str
    source_revision: str
    exact_bytes: bytes
    size_bytes: int
    sha256: str
    git_blob_sha1: str


@dataclass(frozen=True)
class SourceSet:
    repository_root: Path
    source_revision: str
    schema: RepositoryObject
    contract: RepositoryObject
    tool: RepositoryObject
    workflow: RepositoryObject | None
    contract_document: dict[str, Any]


@dataclass(frozen=True)
class WorkflowExecutionIdentity:
    workflow_id: int
    workflow_run_id: int
    workflow_run_attempt: int
    workflow_run_key: str


@dataclass(frozen=True)
class TransportResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    clean_eof: bool = True
    redirect_observed: bool = False


@dataclass(frozen=True)
class CapturedHttpResponse:
    status: int
    selected_headers: dict[str, Any]
    body: bytes
    parsed_body: dict[str, Any]
    capture_started_utc: str
    response_received_utc: str


@dataclass(frozen=True)
class PageCapture:
    page_number: int
    request_target: str
    response: CapturedHttpResponse
    response_summary: dict[str, Any]
    pagination_relation: dict[str, Any]
    exchange_record: dict[str, Any]
    exchange_wrapper: dict[str, Any]
    metadata_bytes: bytes


@dataclass(frozen=True)
class CaptureResult:
    record_status: str
    manifest_file_name: str
    manifest_bytes: bytes
    manifest_sha256: str
    page_count: int
    job_count: int
    step_record_count: int
    authority_effect: str


class HttpTransport(Protocol):
    def get(
        self,
        *,
        request_target: str,
        headers: Sequence[tuple[str, str]],
        timeout_seconds: int,
        maximum_body_bytes: int,
    ) -> TransportResponse:
        ...


class CaptureClock(Protocol):
    def now(self) -> dt.datetime:
        ...


class SystemUtcClock:
    def now(self) -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)


class StdlibHttpsTransport:
    """One-request-per-connection HTTPS transport with no redirect handling."""

    def __init__(self) -> None:
        context = ssl.create_default_context()
        if hasattr(ssl, "TLSVersion"):
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._context = context

    def get(
        self,
        *,
        request_target: str,
        headers: Sequence[tuple[str, str]],
        timeout_seconds: int,
        maximum_body_bytes: int,
    ) -> TransportResponse:
        connection = http.client.HTTPSConnection(
            API_HOST,
            timeout=timeout_seconds,
            context=self._context,
        )
        response: http.client.HTTPResponse | None = None
        try:
            header_map: dict[str, str] = {}
            for name, value in headers:
                if name in header_map:
                    raise CaptureError("application_request_header_duplicate")
                header_map[name] = value
            connection.request(
                "GET",
                request_target,
                body=None,
                headers=header_map,
                encode_chunked=False,
            )
            response = connection.getresponse()
            response_headers = tuple(response.getheaders())
            payload_parts: list[bytes] = []
            observed_size = 0
            while True:
                chunk = response.read(HTTP_READ_CHUNK_BYTES)
                if not chunk:
                    break
                observed_size += len(chunk)
                if observed_size > maximum_body_bytes:
                    raise CaptureError("response_body_size_limit_exceeded")
                payload_parts.append(chunk)
            payload = b"".join(payload_parts)
            return TransportResponse(
                status=response.status,
                headers=response_headers,
                body=payload,
                clean_eof=True,
                redirect_observed=300 <= response.status <= 399,
            )
        except CaptureError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException):
            raise CaptureError("network_request_failed") from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            try:
                connection.close()
            except Exception:
                pass


def _raise(error_code: str) -> None:
    raise CaptureError(error_code)


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
    label: str,
) -> dict[str, Any]:
    parse_payload = payload
    if payload.startswith(b"\xef\xbb\xbf"):
        parse_payload = payload[3:]
    try:
        text = parse_payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _raise(f"{label}_invalid_utf8")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_non_finite,
        )
    except (json.JSONDecodeError, StrictJsonError, ValueError):
        _raise(f"{label}_invalid_json")
    if not isinstance(value, dict):
        _raise(f"{label}_top_level_not_object")
    return value


def _check_canonical_value(value: Any) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        _raise("canonical_json_float_forbidden")
    if isinstance(value, list):
        for item in value:
            _check_canonical_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _raise("canonical_json_non_string_key")
            _check_canonical_value(item)
        return
    _raise("canonical_json_unsupported_value")


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    _check_canonical_value(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (UnicodeEncodeError, ValueError, TypeError):
        _raise("canonical_json_serialization_failed")
    return rendered + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    prefix = b"blob " + str(len(payload)).encode("ascii") + b"\x00"
    return hashlib.sha1(prefix + payload).hexdigest()


def _byte_properties(
    payload: bytes,
    *,
    role: str,
    path: str,
    canonical: bool,
) -> dict[str, Any]:
    if not payload:
        _raise("empty_output_member_forbidden")
    final_byte = payload[-1]
    properties: dict[str, Any] = {
        "role": role,
        "path": path,
        "size_bytes": len(payload),
        "sha256": _sha256(payload),
        "git_blob_sha1": _git_blob_sha1(payload),
        "media_type": "application/json",
        "utf8_bom_present": payload.startswith(b"\xef\xbb\xbf"),
        "cr_count": payload.count(b"\r"),
        "lf_count": payload.count(b"\n"),
        "final_byte_hex": f"{final_byte:02x}",
        "trailing_newline_present": final_byte == 0x0A,
    }
    if canonical:
        properties.update(
            {
                "canonicalization": "json-sort-keys-utf8-newline",
                "canonical_reserialization_matches": True,
            }
        )
    else:
        properties.update(
            {
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
        )
    return properties


def _require_object(value: Any, *, error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _raise(error_code)
    return value


def _require_array(value: Any, *, error_code: str) -> list[Any]:
    if not isinstance(value, list):
        _raise(error_code)
    return value


def _require_string(
    value: Any,
    *,
    error_code: str,
    exact: str | None = None,
) -> str:
    if not isinstance(value, str) or not value:
        _raise(error_code)
    if "\r" in value or "\n" in value or "\x00" in value:
        _raise(error_code)
    if exact is not None and value != exact:
        _raise(error_code)
    return value


def _require_bool(value: Any, *, error_code: str) -> bool:
    if not isinstance(value, bool):
        _raise(error_code)
    return value


def _require_int(
    value: Any,
    *,
    error_code: str,
    minimum: int | None = None,
    exact: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(error_code)
    if minimum is not None and value < minimum:
        _raise(error_code)
    if exact is not None and value != exact:
        _raise(error_code)
    return value


def _require_sha40(value: Any, *, error_code: str) -> str:
    text = _require_string(value, error_code=error_code)
    if SHA40_RE.fullmatch(text) is None:
        _raise(error_code)
    return text


def _parse_utc(value: Any, *, error_code: str) -> dt.datetime:
    text = _require_string(value, error_code=error_code)
    if CANONICAL_UTC_RE.fullmatch(text) is None:
        _raise(error_code)
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        _raise(error_code)
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        _raise(error_code)
    return parsed


def _format_utc(value: dt.datetime) -> str:
    if not isinstance(value, dt.datetime):
        _raise("capture_clock_value_invalid")
    if value.tzinfo is None or value.utcoffset() != dt.timedelta(0):
        _raise("capture_clock_not_utc")
    normalized = value.astimezone(dt.timezone.utc)
    return normalized.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _safe_relative_path(path: str) -> PurePosixPath:
    if not isinstance(path, str) or not path or len(path) > 512:
        _raise("unsafe_relative_path")
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        _raise("unsafe_relative_path")
    if "\\" in path or "\x00" in path or path.startswith("/") or "//" in path:
        _raise("unsafe_relative_path")
    pure = PurePosixPath(path)
    if any(part in {"", ".", ".."} for part in pure.parts):
        _raise("unsafe_relative_path")
    return pure


def _safe_leaf_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 200
        or SAFE_LEAF_RE.fullmatch(name) is None
        or name in {".", ".."}
    ):
        _raise("unsafe_output_leaf_name")
    return name


def _secure_open_flags(*, directory: bool = False, write: bool = False) -> int:
    required = ["O_NOFOLLOW", "O_CLOEXEC"]
    if directory:
        required.append("O_DIRECTORY")
    for name in required:
        if not hasattr(os, name):
            _raise("required_secure_open_flag_unavailable")
    flags = os.O_WRONLY if write else os.O_RDONLY
    flags |= int(getattr(os, "O_NOFOLLOW"))
    flags |= int(getattr(os, "O_CLOEXEC"))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY"))
    flags |= int(getattr(os, "O_BINARY", 0))
    return flags


def _open_absolute_directory_no_symlinks(path: Path) -> int:
    candidate = path.absolute()
    if not candidate.is_absolute():
        _raise("absolute_directory_required")
    flags = _secure_open_flags(directory=True)
    current_fd = os.open("/", flags)
    try:
        for part in candidate.parts[1:]:
            if not part or part in {".", ".."}:
                _raise("directory_path_component_invalid")
            next_fd = os.open(part, flags, dir_fd=current_fd)
            metadata = os.fstat(next_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(next_fd)
                _raise("directory_component_not_directory")
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _read_fd_bounded(fd: int, *, maximum: int, error_prefix: str) -> bytes:
    metadata_before = os.fstat(fd)
    if not stat.S_ISREG(metadata_before.st_mode):
        _raise(f"{error_prefix}_not_regular_file")
    if metadata_before.st_nlink != 1:
        _raise(f"{error_prefix}_hard_link_rejected")
    if metadata_before.st_size < 1 or metadata_before.st_size > maximum:
        _raise(f"{error_prefix}_size_invalid")
    parts: list[bytes] = []
    observed = 0
    while True:
        chunk = os.read(fd, min(HTTP_READ_CHUNK_BYTES, maximum + 1 - observed))
        if not chunk:
            break
        observed += len(chunk)
        if observed > maximum:
            _raise(f"{error_prefix}_size_limit_exceeded")
        parts.append(chunk)
    payload = b"".join(parts)
    metadata_after = os.fstat(fd)
    identity_before = (
        metadata_before.st_dev,
        metadata_before.st_ino,
        metadata_before.st_size,
        metadata_before.st_mtime_ns,
        metadata_before.st_ctime_ns,
    )
    identity_after = (
        metadata_after.st_dev,
        metadata_after.st_ino,
        metadata_after.st_size,
        metadata_after.st_mtime_ns,
        metadata_after.st_ctime_ns,
    )
    if identity_before != identity_after or len(payload) != metadata_before.st_size:
        _raise(f"{error_prefix}_changed_during_read")
    return payload


def _read_relative_file_secure(
    root_fd: int,
    relative_path: str,
    *,
    maximum: int,
    error_prefix: str,
) -> bytes:
    pure = _safe_relative_path(relative_path)
    directory_fd = os.dup(root_fd)
    try:
        directory_flags = _secure_open_flags(directory=True)
        for part in pure.parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            metadata = os.fstat(next_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(next_fd)
                _raise(f"{error_prefix}_parent_not_directory")
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            pure.parts[-1],
            _secure_open_flags(),
            dir_fd=directory_fd,
        )
        try:
            return _read_fd_bounded(
                file_fd,
                maximum=maximum,
                error_prefix=error_prefix,
            )
        finally:
            os.close(file_fd)
    except FileNotFoundError:
        _raise(f"{error_prefix}_missing")
    except OSError:
        _raise(f"{error_prefix}_open_failed")
    finally:
        os.close(directory_fd)


def _trusted_git_executable() -> Path:
    for candidate in TRUSTED_GIT_CANDIDATES:
        try:
            metadata = candidate.lstat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
            return candidate
    _raise("trusted_git_executable_unavailable")


def _git_environment() -> dict[str, str]:
    environment: dict[str, str] = {}
    for name in GIT_ENV_ALLOWLIST:
        value = os.environ.get(name)
        if value:
            environment[name] = value
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
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
    error_code: str,
) -> bytes:
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
            timeout=30,
            check=False,
            env=_git_environment(),
            pass_fds=(root_fd,),
        )
    except (OSError, subprocess.SubprocessError):
        _raise(error_code)
    if completed.returncode != 0:
        _raise(error_code)
    if len(completed.stdout) > maximum_output or len(completed.stderr) > 64 * 1024:
        _raise(error_code)
    return completed.stdout


def _load_repository_object(
    *,
    root_fd: int,
    revision: str,
    role: str,
    path: str,
    maximum: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    expected_git_blob_sha1: str | None = None,
) -> RepositoryObject:
    if SHA40_RE.fullmatch(revision) is None:
        _raise(f"{role}_source_revision_invalid")
    _safe_relative_path(path)
    committed = _run_git(
        root_fd,
        ["show", f"{revision}:{path}"],
        maximum_output=maximum,
        error_code=f"{role}_committed_bytes_unavailable",
    )
    if not committed or len(committed) > maximum:
        _raise(f"{role}_committed_size_invalid")
    worktree = _read_relative_file_secure(
        root_fd,
        path,
        maximum=maximum,
        error_prefix=f"{role}_worktree",
    )
    if worktree != committed:
        _raise(f"{role}_worktree_differs_from_commit")
    size = len(committed)
    sha256 = _sha256(committed)
    blob = _git_blob_sha1(committed)
    git_blob = _run_git(
        root_fd,
        ["rev-parse", f"{revision}:{path}"],
        maximum_output=128,
        error_code=f"{role}_git_blob_unavailable",
    ).decode("ascii", errors="strict").strip()
    if git_blob != blob:
        _raise(f"{role}_git_blob_reconstruction_mismatch")
    if expected_size is not None and size != expected_size:
        _raise(f"{role}_size_mismatch")
    if expected_sha256 is not None and sha256 != expected_sha256:
        _raise(f"{role}_sha256_mismatch")
    if expected_git_blob_sha1 is not None and blob != expected_git_blob_sha1:
        _raise(f"{role}_git_blob_mismatch")
    return RepositoryObject(
        role=role,
        path=path,
        source_revision=revision,
        exact_bytes=committed,
        size_bytes=size,
        sha256=sha256,
        git_blob_sha1=blob,
    )


def _validate_runtime_platform() -> None:
    if os.name != SUPPORTED_OS_NAME or not sys.platform.startswith(
        SUPPORTED_PLATFORM_PREFIX
    ):
        _raise("supported_linux_runtime_required")
    required = (
        "O_DIRECTORY",
        "O_NOFOLLOW",
        "O_CLOEXEC",
        "supports_dir_fd",
        "supports_fd",
    )
    if any(not hasattr(os, name) for name in required):
        _raise("required_linux_filesystem_primitives_unavailable")
    dir_fd_functions = (os.open, os.stat, os.mkdir, os.unlink, os.rmdir)
    if any(function not in os.supports_dir_fd for function in dir_fd_functions):
        _raise("required_dir_fd_support_unavailable")
    if os.listdir not in os.supports_fd:
        _raise("required_fd_listdir_support_unavailable")
    if not hasattr(signal, "pthread_sigmask"):
        _raise("pthread_signal_mask_required")
    if not Path("/proc/self/fd").is_dir():
        _raise("proc_self_fd_required")


def _environment_value(name: str, *, exact: str | None = None) -> str:
    value = os.environ.get(name, "")
    if not value or "\x00" in value or "\r" in value or "\n" in value:
        _raise(f"{name.lower()}_missing_or_invalid")
    if exact is not None and value != exact:
        _raise(f"{name.lower()}_mismatch")
    return value


def _positive_environment_int(name: str) -> int:
    text = _environment_value(name)
    if CANONICAL_POSITIVE_DECIMAL_RE.fullmatch(text) is None:
        _raise(f"{name.lower()}_invalid")
    return int(text)


def _load_sources(
    repository_root: Path,
    *,
    revision: str,
    include_workflow: bool,
) -> SourceSet:
    root = repository_root.absolute()
    root_fd = _open_absolute_directory_no_symlinks(root)
    try:
        metadata = os.fstat(root_fd)
        if not stat.S_ISDIR(metadata.st_mode):
            _raise("repository_root_not_directory")
        try:
            git_admin = os.stat(
                ".git",
                dir_fd=root_fd,
                follow_symlinks=False,
            )
        except OSError:
            _raise("repository_git_admin_directory_unavailable")
        if not stat.S_ISDIR(git_admin.st_mode):
            _raise("repository_git_admin_directory_invalid")
        inside_worktree = _run_git(
            root_fd,
            ["rev-parse", "--is-inside-work-tree"],
            maximum_output=64,
            error_code="repository_worktree_state_unavailable",
        ).decode("ascii", errors="strict").strip()
        if inside_worktree != "true":
            _raise("repository_not_worktree")
        head = _run_git(
            root_fd,
            ["rev-parse", "HEAD"],
            maximum_output=128,
            error_code="repository_head_unavailable",
        ).decode("ascii", errors="strict").strip()
        if head != revision:
            _raise("repository_head_revision_mismatch")
        schema_object = _load_repository_object(
            root_fd=root_fd,
            revision=revision,
            role="manifest_schema",
            path=SCHEMA_PATH,
            maximum=MAX_SOURCE_FILE_BYTES,
            expected_size=EXPECTED_SCHEMA_SIZE,
            expected_sha256=EXPECTED_SCHEMA_SHA256,
            expected_git_blob_sha1=EXPECTED_SCHEMA_GIT_BLOB_SHA1,
        )
        contract_object = _load_repository_object(
            root_fd=root_fd,
            revision=revision,
            role="normative_contract",
            path=CONTRACT_PATH,
            maximum=MAX_SOURCE_FILE_BYTES,
            expected_size=EXPECTED_CONTRACT_SIZE,
            expected_sha256=EXPECTED_CONTRACT_SHA256,
            expected_git_blob_sha1=EXPECTED_CONTRACT_GIT_BLOB_SHA1,
        )
        tool_object = _load_repository_object(
            root_fd=root_fd,
            revision=revision,
            role="capture_implementation",
            path=TOOL_PATH,
            maximum=MAX_SOURCE_FILE_BYTES,
        )
        try:
            executing_path = Path(__file__).absolute()
            repository_tool_path = root / TOOL_PATH
            executing_metadata = executing_path.lstat()
            if (
                executing_path != repository_tool_path
                or stat.S_ISLNK(executing_metadata.st_mode)
                or not stat.S_ISREG(executing_metadata.st_mode)
                or executing_metadata.st_nlink != 1
                or not os.path.samefile(executing_path, repository_tool_path)
            ):
                _raise("executing_capture_tool_path_mismatch")
        except OSError:
            _raise("executing_capture_tool_path_unavailable")
        workflow_object: RepositoryObject | None = None
        if include_workflow:
            workflow_object = _load_repository_object(
                root_fd=root_fd,
                revision=revision,
                role="capture_workflow",
                path=CAPTURE_WORKFLOW_PATH,
                maximum=MAX_WORKFLOW_FILE_BYTES,
            )
        contract_document = _parse_json_object(
            contract_object.exact_bytes,
            label="normative_contract",
        )
        _validate_exact_contract(contract_document, schema_object)
        return SourceSet(
            repository_root=root,
            source_revision=revision,
            schema=schema_object,
            contract=contract_object,
            tool=tool_object,
            workflow=workflow_object,
            contract_document=contract_document,
        )
    finally:
        os.close(root_fd)


def _validate_exact_contract(
    contract: dict[str, Any],
    schema_object: RepositoryObject,
) -> None:
    expected_top_level = {
        "document_type": "pulsemech_compute_post_run_producer_input_capture_contract",
        "record_status": "normative_contract",
        "capture_contract_id": "pulsemech_compute_post_run_producer_input_capture_v0",
        "capture_contract_version": "0.1.0",
    }
    for field, expected in expected_top_level.items():
        if contract.get(field) != expected:
            _raise("normative_contract_identity_mismatch")
    work_order = _require_object(
        contract.get("work_order_binding"),
        error_code="normative_contract_work_order_invalid",
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
            _raise("normative_contract_work_order_mismatch")
    schema_binding = _require_object(
        contract.get("schema_binding"),
        error_code="normative_contract_schema_binding_invalid",
    )
    expected_schema_binding = {
        "path": SCHEMA_PATH,
        "size_bytes": schema_object.size_bytes,
        "sha256": schema_object.sha256,
        "git_blob_sha1": schema_object.git_blob_sha1,
        "schema_version_const": SCHEMA_VERSION,
        "document_type_const": DOCUMENT_TYPE,
    }
    for field, expected in expected_schema_binding.items():
        if schema_binding.get(field) != expected:
            _raise("normative_contract_schema_binding_mismatch")
    if contract.get("initial_reference_subject") != _expected_subject():
        _raise("normative_contract_subject_mismatch")
    if contract.get("request_contract") != _expected_request_contract():
        _raise("normative_contract_request_mismatch")
    if contract.get("limits") != _expected_limits():
        _raise("normative_contract_limits_mismatch")
    capture_layout = _require_object(
        contract.get("capture_layout"),
        error_code="normative_contract_capture_layout_invalid",
    )
    expected_layout = {
        "root_path": OBSERVED_CAPTURE_ROOT,
        "raw_directory": "raw/",
        "metadata_directory": "metadata/",
        "run_attempt_body_path": RUN_BODY_PATH,
        "run_attempt_metadata_path": RUN_METADATA_PATH,
        "jobs_body_name_template": JOBS_BODY_TEMPLATE,
        "jobs_metadata_name_template": JOBS_METADATA_TEMPLATE,
        "manifest_file_name": OBSERVED_MANIFEST_NAME,
        "member_inventory_scope": "all_capture_files_except_this_manifest",
        "directory_entries_allowed": False,
        "symlinks_allowed": False,
        "hard_links_allowed": False,
        "non_regular_members_allowed": False,
        "undeclared_members_allowed": False,
        "existing_output_overwrite_allowed": False,
        "transactional_publication_required": True,
    }
    if capture_layout != expected_layout:
        _raise("normative_contract_capture_layout_mismatch")
    required_sections = (
        "temporal_boundary",
        "implementation_boundary",
        "publication_boundary",
        "privacy_boundary",
        "content_boundary",
        "availability_boundary",
        "authority_boundary",
    )
    for name in required_sections:
        if not isinstance(contract.get(name), dict):
            _raise("normative_contract_manifest_projection_invalid")
    canonicalization = _require_object(
        contract.get("canonicalization_contract"),
        error_code="normative_contract_canonicalization_invalid",
    )
    if (
        canonicalization.get("canonicalization_profile")
        != "json-sort-keys-utf8-newline"
        or canonicalization.get("raw_response_body_canonicalization")
        != "forbidden"
        or canonicalization.get("raw_response_body_reserialization")
        != "forbidden"
    ):
        _raise("normative_contract_canonicalization_mismatch")
    transaction = _require_object(
        contract.get("transactional_publication_contract"),
        error_code="normative_contract_publication_invalid",
    )
    if (
        transaction.get("atomic_no_replace_primitive")
        != "linux_renameat2_RENAME_NOREPLACE_or_fail_closed"
        or transaction.get("cleanup_exception_boundary") != "BaseException"
        or transaction.get("final_readback_validation")
        != "required_before_exit_zero"
    ):
        _raise("normative_contract_publication_mismatch")


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


def _revalidate_sources(sources: SourceSet) -> None:
    root_fd = _open_absolute_directory_no_symlinks(sources.repository_root)
    try:
        for source in (
            sources.schema,
            sources.contract,
            sources.tool,
            sources.workflow,
        ):
            if source is None:
                continue
            current = _read_relative_file_secure(
                root_fd,
                source.path,
                maximum=(
                    MAX_WORKFLOW_FILE_BYTES
                    if source.role == "capture_workflow"
                    else MAX_SOURCE_FILE_BYTES
                ),
                error_prefix=f"{source.role}_revalidation",
            )
            if current != source.exact_bytes:
                _raise(f"{source.role}_drift_detected")
    finally:
        os.close(root_fd)


def _validate_token(token: str) -> bytes:
    if not isinstance(token, str):
        _raise("gh_token_missing_or_invalid")
    try:
        token_bytes = token.encode("ascii", errors="strict")
    except UnicodeEncodeError:
        _raise("gh_token_missing_or_invalid")
    if (
        len(token_bytes) < MIN_TOKEN_BYTES
        or len(token_bytes) > MAX_TOKEN_BYTES
        or any(byte < 0x21 or byte > 0x7E for byte in token_bytes)
    ):
        _raise("gh_token_missing_or_invalid")
    return token_bytes


def _load_production_environment(
    repository_root: Path,
) -> tuple[SourceSet, WorkflowExecutionIdentity, str]:
    _validate_runtime_platform()
    _environment_value("GITHUB_ACTIONS", exact="true")
    _environment_value("GITHUB_REPOSITORY", exact=REPOSITORY)
    _environment_value("GITHUB_REPOSITORY_ID", exact=str(REPOSITORY_ID))
    _environment_value("GITHUB_WORKFLOW", exact=CAPTURE_WORKFLOW_NAME)
    _environment_value("GITHUB_EVENT_NAME", exact="workflow_dispatch")
    _environment_value("GITHUB_REF", exact=CAPTURE_SOURCE_REF)
    _environment_value("GITHUB_REF_TYPE", exact="branch")
    _environment_value("GITHUB_REF_NAME", exact="main")
    _environment_value("GITHUB_API_URL", exact="https://api.github.com")
    _environment_value("GITHUB_SERVER_URL", exact="https://github.com")
    source_revision = _environment_value("GITHUB_SHA")
    if SHA40_RE.fullmatch(source_revision) is None:
        _raise("github_sha_invalid")
    workflow_sha = _environment_value("GITHUB_WORKFLOW_SHA")
    if workflow_sha != source_revision:
        _raise("github_workflow_sha_mismatch")
    workflow_ref = _environment_value("GITHUB_WORKFLOW_REF")
    expected_workflow_ref = f"{REPOSITORY}/{CAPTURE_WORKFLOW_PATH}@refs/heads/main"
    if workflow_ref != expected_workflow_ref:
        _raise("github_workflow_ref_mismatch")
    workspace = Path(_environment_value("GITHUB_WORKSPACE")).absolute()
    try:
        if not os.path.samefile(workspace, repository_root.absolute()):
            _raise("github_workspace_repository_root_mismatch")
    except OSError:
        _raise("github_workspace_unavailable")
    workflow_run_id = _positive_environment_int("GITHUB_RUN_ID")
    workflow_run_attempt = _positive_environment_int("GITHUB_RUN_ATTEMPT")
    workflow_id = _positive_environment_int(CAPTURE_WORKFLOW_ID_ENV)
    token = _environment_value(TOKEN_ENV)
    _validate_token(token)
    sources = _load_sources(
        repository_root,
        revision=source_revision,
        include_workflow=True,
    )
    if sources.workflow is None:
        _raise("capture_workflow_source_missing")
    workflow_run_key = (
        f"GITHUB_RUN_ID={workflow_run_id}|"
        f"GITHUB_RUN_ATTEMPT={workflow_run_attempt}|"
        f"GITHUB_WORKFLOW={CAPTURE_WORKFLOW_NAME}"
    )
    return (
        sources,
        WorkflowExecutionIdentity(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            workflow_run_attempt=workflow_run_attempt,
            workflow_run_key=workflow_run_key,
        ),
        token,
    )


def _application_request_headers(token: str) -> tuple[tuple[str, str], ...]:
    _validate_token(token)
    return (
        ("Accept", ACCEPT),
        ("Accept-Encoding", ACCEPT_ENCODING),
        ("Authorization", f"Bearer {token}"),
        ("User-Agent", USER_AGENT),
        ("X-GitHub-Api-Version", API_VERSION),
    )


def _request_record(*, request_target: str, page_number: int | None) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(request_target)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        _raise("request_target_not_origin_form")
    if page_number is None:
        if request_target != RUN_REQUEST_PATH or parsed.query:
            _raise("run_attempt_request_target_mismatch")
        query_parameters: list[dict[str, str]] = []
    else:
        expected = f"{JOBS_REQUEST_PATH}?per_page=100&page={page_number}"
        if request_target != expected:
            _raise("jobs_page_request_target_mismatch")
        query_parameters = [
            {"name": "per_page", "value": "100"},
            {"name": "page", "value": str(page_number)},
        ]
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
        "path": parsed.path,
        "query_parameters": query_parameters,
        "redirects_allowed": False,
        "request_target": request_target,
        "scheme": API_SCHEME,
        "user_agent": USER_AGENT,
    }


def _selected_response_headers(
    headers: Sequence[tuple[str, str]],
) -> tuple[dict[str, Any], int | None]:
    by_lower_name: dict[str, list[str]] = {}
    for raw_name, raw_value in headers:
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            _raise("response_header_type_invalid")
        name = raw_name.strip()
        value = raw_value
        if not name or any(character in name for character in "\r\n\x00"):
            _raise("response_header_name_invalid")
        if any(character in value for character in "\r\n\x00"):
            _raise("response_header_value_invalid")
        if len(value) > 8192:
            _raise("selected_response_header_value_too_large")
        by_lower_name.setdefault(name.lower(), []).append(value)

    selected: dict[str, Any] = {}
    for canonical_name in SELECTED_RESPONSE_HEADERS:
        values = by_lower_name.get(canonical_name.lower(), [])
        if len(values) > 1:
            _raise("duplicate_allowlisted_response_header")
        key = canonical_name.lower().replace("-", "_")
        if not values:
            if canonical_name == "Content-Type":
                _raise("content_type_header_missing")
            selected[key] = {"status": "absent", "value": None}
        else:
            if not values[0]:
                _raise("selected_response_header_value_empty")
            selected[key] = {"status": "present", "value": values[0]}

    content_type = selected["content_type"]["value"]
    if not isinstance(content_type, str):
        _raise("content_type_header_missing")
    if len(content_type) > 256:
        _raise("wrong_content_type")
    media_type = content_type.split(";", 1)[0].strip()
    if media_type != "application/json":
        _raise("wrong_content_type")

    content_encoding = selected["content_encoding"]
    if (
        content_encoding["status"] == "present"
        and content_encoding["value"] != "identity"
    ):
        _raise("unsupported_content_encoding")

    content_length_values = by_lower_name.get("content-length", [])
    if len(content_length_values) > 1:
        _raise("duplicate_content_length_header")
    content_length: int | None = None
    if content_length_values:
        value = content_length_values[0].strip()
        if not value.isdigit():
            _raise("content_length_header_invalid")
        content_length = int(value)
    return selected, content_length


def _capture_response(
    *,
    transport: HttpTransport,
    clock: CaptureClock,
    token: str,
    request_target: str,
    label: str,
) -> CapturedHttpResponse:
    request_headers = _application_request_headers(token)
    capture_started = clock.now()
    response = transport.get(
        request_target=request_target,
        headers=request_headers,
        timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        maximum_body_bytes=MAX_RESPONSE_BODY_BYTES,
    )
    response_received = clock.now()
    if isinstance(response.status, bool) or not isinstance(response.status, int):
        _raise("response_status_type_invalid")
    if not isinstance(response.body, bytes):
        _raise("response_body_type_invalid")
    if not isinstance(response.clean_eof, bool):
        _raise("response_eof_state_invalid")
    if not isinstance(response.redirect_observed, bool):
        _raise("response_redirect_state_invalid")
    if response_received < capture_started:
        _raise("response_received_before_capture_start")
    if response.redirect_observed or 300 <= response.status <= 399:
        _raise("redirect_admission_rejected")
    if response.status != 200:
        _raise("non_200_response_rejected")
    if not response.clean_eof:
        _raise("truncated_response_body")
    if not response.body:
        _raise("empty_response_body")
    if len(response.body) > MAX_RESPONSE_BODY_BYTES:
        _raise("response_body_size_limit_exceeded")
    selected_headers, content_length = _selected_response_headers(response.headers)
    if content_length is not None and content_length != len(response.body):
        _raise("content_length_body_size_mismatch")
    parsed_body = _parse_json_object(
        response.body,
        label=label,
    )
    return CapturedHttpResponse(
        status=response.status,
        selected_headers=selected_headers,
        body=response.body,
        parsed_body=parsed_body,
        capture_started_utc=_format_utc(capture_started),
        response_received_utc=_format_utc(response_received),
    )


def _repository_identity(value: Any, *, error_code: str) -> tuple[str, int, bool]:
    repository = _require_object(value, error_code=error_code)
    full_name = _require_string(
        repository.get("full_name"),
        error_code=error_code,
    )
    repository_id = _require_int(
        repository.get("id"),
        error_code=error_code,
        minimum=1,
    )
    is_fork = _require_bool(repository.get("fork"), error_code=error_code)
    return full_name, repository_id, is_fork


def _validate_run_response(
    response: CapturedHttpResponse,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value = response.parsed_body
    run_id = _require_int(
        value.get("id"),
        error_code="wrong_run_id",
        exact=SUBJECT_RUN_ID,
    )
    run_number = _require_int(
        value.get("run_number"),
        error_code="wrong_run_number",
        exact=SUBJECT_RUN_NUMBER,
    )
    run_attempt = _require_int(
        value.get("run_attempt"),
        error_code="wrong_run_attempt",
        exact=SUBJECT_RUN_ATTEMPT,
    )
    workflow_name = _require_string(
        value.get("name"),
        error_code="wrong_workflow_name",
        exact=SUBJECT_WORKFLOW_NAME,
    )
    workflow_id = _require_int(
        value.get("workflow_id"),
        error_code="wrong_workflow_id",
        exact=SUBJECT_WORKFLOW_ID,
    )
    workflow_path = _require_string(
        value.get("path"),
        error_code="wrong_workflow_path",
        exact=SUBJECT_WORKFLOW_PATH,
    )
    event_name = _require_string(
        value.get("event"),
        error_code="wrong_event",
        exact=SUBJECT_EVENT,
    )
    head_branch = _require_string(
        value.get("head_branch"),
        error_code="wrong_head_branch",
        exact=SUBJECT_HEAD_BRANCH,
    )
    head_sha = _require_sha40(value.get("head_sha"), error_code="wrong_source_commit")
    if head_sha != SUBJECT_SOURCE_COMMIT:
        _raise("wrong_source_commit")
    status_value = _require_string(
        value.get("status"),
        error_code="non_completed_run",
        exact="completed",
    )
    conclusion = _require_string(
        value.get("conclusion"),
        error_code="non_success_reference_run",
        exact="success",
    )
    created_at = _require_string(
        value.get("created_at"),
        error_code="run_created_at_invalid",
        exact=SUBJECT_RUN_CREATED_UTC,
    )
    run_started_at = _require_string(
        value.get("run_started_at"),
        error_code="run_started_at_invalid",
        exact=SUBJECT_RUN_STARTED_UTC,
    )
    updated_at = _require_string(
        value.get("updated_at"),
        error_code="run_updated_at_invalid",
        exact=SUBJECT_RUN_UPDATED_UTC,
    )
    created_time = _parse_utc(created_at, error_code="run_created_at_invalid")
    started_time = _parse_utc(run_started_at, error_code="run_started_at_invalid")
    updated_time = _parse_utc(updated_at, error_code="run_updated_at_invalid")
    if not (created_time <= started_time <= updated_time):
        _raise("run_timestamp_order_invalid")
    capture_start = _parse_utc(
        response.capture_started_utc,
        error_code="capture_started_utc_invalid",
    )
    if capture_start < updated_time:
        _raise("capture_started_before_subject_run_completed")

    repository_name, repository_id, repository_is_fork = _repository_identity(
        value.get("repository"),
        error_code="wrong_repository_identity",
    )
    head_repository_name, head_repository_id, head_repository_is_fork = (
        _repository_identity(
            value.get("head_repository"),
            error_code="wrong_head_repository_identity",
        )
    )
    if repository_name != REPOSITORY or repository_id != REPOSITORY_ID:
        _raise("wrong_repository_identity")
    if repository_is_fork:
        _raise("fork_subject")
    if (
        head_repository_name != REPOSITORY
        or head_repository_id != REPOSITORY_ID
        or head_repository_is_fork
    ):
        _raise("wrong_head_repository_identity")

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
        "run_started_at": run_started_at,
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
    subject = _expected_subject()
    # Reconstruct explicitly rather than trusting a producer-side declaration.
    reconstructed_subject = {
        "event_name": event_name,
        "head_branch": head_branch,
        "head_repository": head_repository_name,
        "head_repository_id": head_repository_id,
        "repository": repository_name,
        "repository_id": repository_id,
        "repository_is_fork": repository_is_fork,
        "run_conclusion": conclusion,
        "run_created_utc": created_at,
        "run_started_utc": run_started_at,
        "run_status": status_value,
        "run_updated_utc": updated_at,
        "same_repository_subject": True,
        "source_commit": head_sha,
        "source_commit_is_exact_identity": True,
        "source_ref": f"refs/heads/{head_branch}",
        "source_ref_origin": (
            "declared_work_order_and_recorded_head_branch_reconstruction"
        ),
        "subject_class": "completed_historical_workflow_run_attempt",
        "subject_run_key": (
            f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}|"
            f"GITHUB_WORKFLOW={workflow_name}"
        ),
        "subject_run_key_origin": (
            "deterministic_reconstruction_from_run_id_attempt_and_workflow_name"
        ),
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    if reconstructed_subject != subject:
        _raise("run_attempt_subject_binding_mismatch")
    return summary, reconstructed_subject


def _validate_completed_result(
    value: dict[str, Any],
    *,
    label: str,
) -> None:
    _require_string(
        value.get("status"),
        error_code=f"{label}_status_invalid",
        exact="completed",
    )
    conclusion = _require_string(
        value.get("conclusion"),
        error_code=f"{label}_conclusion_invalid",
    )
    if conclusion not in {"success", "skipped"}:
        _raise(f"{label}_conclusion_invalid")
    started = value.get("started_at")
    completed = value.get("completed_at")
    if conclusion == "success":
        start_time = _parse_utc(started, error_code=f"{label}_started_at_invalid")
        completed_time = _parse_utc(
            completed,
            error_code=f"{label}_completed_at_invalid",
        )
        if start_time > completed_time:
            _raise(f"{label}_timestamp_order_invalid")
    else:
        if started is None and completed is None:
            return
        if started is None or completed is None:
            _raise(f"{label}_skipped_timestamp_pair_invalid")
        start_time = _parse_utc(started, error_code=f"{label}_started_at_invalid")
        completed_time = _parse_utc(
            completed,
            error_code=f"{label}_completed_at_invalid",
        )
        if start_time > completed_time:
            _raise(f"{label}_timestamp_order_invalid")


def _validate_jobs_page(
    response: CapturedHttpResponse,
    *,
    page_number: int,
    subject: dict[str, Any],
    all_job_ids: set[int],
) -> tuple[dict[str, Any], int, int]:
    value = response.parsed_body
    total_count = _require_int(
        value.get("total_count"),
        error_code="jobs_total_count_invalid",
        minimum=0,
    )
    jobs = _require_array(value.get("jobs"), error_code="jobs_array_missing")
    if len(jobs) > MAX_JOBS_PER_PAGE:
        _raise("jobs_per_page_limit_exceeded")
    page_job_ids: list[int] = []
    step_record_count = 0
    for job_index, raw_job in enumerate(jobs):
        job = _require_object(
            raw_job,
            error_code="job_record_not_object",
        )
        job_id = _require_int(
            job.get("id"),
            error_code="job_id_invalid",
            minimum=1,
        )
        if job_id in all_job_ids:
            _raise("duplicate_job_id")
        all_job_ids.add(job_id)
        page_job_ids.append(job_id)
        _require_int(
            job.get("run_id"),
            error_code="job_run_id_mismatch",
            exact=subject["workflow_run_id"],
        )
        _require_int(
            job.get("run_attempt"),
            error_code="job_run_attempt_mismatch",
            exact=subject["workflow_run_attempt"],
        )
        _require_string(
            job.get("workflow_name"),
            error_code="job_workflow_name_mismatch",
            exact=subject["workflow_name"],
        )
        job_head_sha = _require_sha40(
            job.get("head_sha"),
            error_code="job_head_sha_mismatch",
        )
        if job_head_sha != subject["source_commit"]:
            _raise("job_head_sha_mismatch")
        _require_string(job.get("name"), error_code="job_name_invalid")
        _validate_completed_result(job, label=f"job_{job_index}")

        raw_steps = job.get("steps")
        if raw_steps is None:
            continue
        steps = _require_array(raw_steps, error_code="job_steps_not_array")
        if len(steps) > MAX_STEP_RECORDS_PER_JOB:
            _raise("step_record_limit_exceeded")
        previous_number = 0
        seen_numbers: set[int] = set()
        for step_index, raw_step in enumerate(steps):
            step = _require_object(
                raw_step,
                error_code="step_record_not_object",
            )
            step_number = _require_int(
                step.get("number"),
                error_code="step_number_invalid",
                minimum=1,
            )
            if step_number in seen_numbers:
                _raise("duplicate_step_number")
            if step_number <= previous_number:
                _raise("step_order_invalid")
            seen_numbers.add(step_number)
            previous_number = step_number
            _require_string(step.get("name"), error_code="step_name_invalid")
            _validate_completed_result(
                step,
                label=f"job_{job_index}_step_{step_index}",
            )
            step_record_count += 1
            if step_record_count > MAX_STEP_RECORDS_PER_PAGE:
                _raise("step_records_per_page_limit_exceeded")

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
        "step_records_on_page": step_record_count,
    }
    return summary, total_count, step_record_count


def _split_link_header(value: str) -> list[str]:
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
                    _raise("link_header_syntax_invalid")
                in_angle = True
            elif character == ">":
                if not in_angle:
                    _raise("link_header_syntax_invalid")
                in_angle = False
            elif character == "," and not in_angle:
                entry = value[start:index].strip()
                if not entry:
                    _raise("link_header_syntax_invalid")
                entries.append(entry)
                start = index + 1
    if in_angle or in_quote or escaped:
        _raise("link_header_syntax_invalid")
    final = value[start:].strip()
    if not final:
        _raise("link_header_syntax_invalid")
    entries.append(final)
    return entries


def _link_next_target(
    selected_headers: dict[str, Any],
    *,
    current_page: int,
) -> tuple[str | None, str]:
    link = selected_headers["link"]
    if link["status"] == "absent":
        return None, "absent"
    raw_value = _require_string(
        link.get("value"),
        error_code="link_header_value_invalid",
    )
    next_urls: list[str] = []
    next_relation_count = 0
    for entry in _split_link_header(raw_value):
        if not entry.startswith("<") or ">" not in entry:
            _raise("link_header_syntax_invalid")
        closing = entry.find(">")
        url = entry[1:closing]
        parameter_text = entry[closing + 1 :]
        relations: list[str] = []
        for parameter in parameter_text.split(";"):
            parameter = parameter.strip()
            if not parameter:
                continue
            name, separator, raw_parameter_value = parameter.partition("=")
            if not separator:
                continue
            if name.strip().lower() != "rel":
                continue
            relation_value = raw_parameter_value.strip()
            if (
                len(relation_value) >= 2
                and relation_value[0] == relation_value[-1] == '"'
            ):
                relation_value = relation_value[1:-1]
            relations.extend(relation_value.split())
        relation_next_count = relations.count("next")
        next_relation_count += relation_next_count
        if relation_next_count:
            next_urls.append(url)
    if next_relation_count > 1 or len(next_urls) > 1:
        _raise("duplicate_rel_next")
    if not next_urls:
        return None, "present"

    parsed = urllib.parse.urlsplit(next_urls[0])
    if parsed.scheme != API_SCHEME or parsed.hostname != API_HOST:
        _raise("link_next_origin_mismatch")
    if parsed.username is not None or parsed.password is not None:
        _raise("link_next_userinfo_forbidden")
    try:
        if parsed.port is not None:
            _raise("link_next_port_forbidden")
    except ValueError:
        _raise("link_next_port_invalid")
    if parsed.fragment:
        _raise("link_next_fragment_forbidden")
    if parsed.path != JOBS_REQUEST_PATH:
        _raise("link_next_path_mismatch")
    expected_next_page = current_page + 1
    expected_query = f"per_page=100&page={expected_next_page}"
    if parsed.query != expected_query:
        _raise("link_next_query_mismatch")
    if expected_next_page > MAX_JOBS_PAGE_COUNT:
        _raise("maximum_page_count_exceeded")
    return parsed.path + "?" + parsed.query, "present"


def _exchange_timing(response: CapturedHttpResponse) -> dict[str, Any]:
    return {
        "capture_started_utc": response.capture_started_utc,
        "response_received_not_before_capture_start": True,
        "response_received_utc": response.response_received_utc,
    }


def _run_exchange(
    *,
    response: CapturedHttpResponse,
    summary: dict[str, Any],
    record_status: str,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    body_member = _byte_properties(
        response.body,
        role="run_attempt_response_body",
        path=RUN_BODY_PATH,
        canonical=False,
    )
    prefix = "example-" if record_status == "example" else "pulse-ci-"
    record = {
        "exchange_id": (
            f"post-run-capture-exchange:{prefix}6066-attempt-1-run"
        ),
        "request": _request_record(
            request_target=RUN_REQUEST_PATH,
            page_number=None,
        ),
        "response": {
            "body_complete": True,
            "body_member": body_member,
            "body_truncated": False,
            "content_encoding_supported": True,
            "content_type_accepted": True,
            "http_status": response.status,
            "redirect_observed": False,
            "selected_headers": response.selected_headers,
            "summary": summary,
            "timing": _exchange_timing(response),
        },
        "semantic_role": "run_attempt_exchange",
    }
    metadata_bytes = _canonical_json_bytes(record)
    if len(metadata_bytes) > MAX_EXCHANGE_METADATA_BYTES:
        _raise("exchange_metadata_size_limit_exceeded")
    metadata_member = _byte_properties(
        metadata_bytes,
        role="run_attempt_exchange_metadata",
        path=RUN_METADATA_PATH,
        canonical=True,
    )
    wrapper = {
        "metadata_member": metadata_member,
        "metadata_record_canonical_bytes_equal_record": True,
        "record": record,
    }
    return wrapper, metadata_bytes, body_member


def _jobs_exchange(
    *,
    page_number: int,
    request_target: str,
    response: CapturedHttpResponse,
    summary: dict[str, Any],
    next_target: str | None,
    link_header_status: str,
    record_status: str,
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    body_path = JOBS_BODY_TEMPLATE % page_number
    metadata_path = JOBS_METADATA_TEMPLATE % page_number
    body_member = _byte_properties(
        response.body,
        role="jobs_page_response_body",
        path=body_path,
        canonical=False,
    )
    is_final_page = next_target is None
    pagination_relation = {
        "is_final_page": is_final_page,
        "link_header_status": link_header_status,
        "next_page_number": None if is_final_page else page_number + 1,
        "next_relation_status": (
            "closed_by_absence" if is_final_page else "present"
        ),
        "next_request_target": next_target,
        "page_number": page_number,
        "relation_source": "selected_link_header",
    }
    prefix = "example-" if record_status == "example" else "pulse-ci-"
    record = {
        "exchange_id": (
            f"post-run-capture-exchange:{prefix}6066-attempt-1-jobs-page-"
            f"{page_number}"
        ),
        "page_number": page_number,
        "pagination_relation": pagination_relation,
        "request": _request_record(
            request_target=request_target,
            page_number=page_number,
        ),
        "response": {
            "body_complete": True,
            "body_member": body_member,
            "body_truncated": False,
            "content_encoding_supported": True,
            "content_type_accepted": True,
            "http_status": response.status,
            "redirect_observed": False,
            "selected_headers": response.selected_headers,
            "summary": summary,
            "timing": _exchange_timing(response),
        },
        "semantic_role": "jobs_page_exchange",
    }
    metadata_bytes = _canonical_json_bytes(record)
    if len(metadata_bytes) > MAX_EXCHANGE_METADATA_BYTES:
        _raise("exchange_metadata_size_limit_exceeded")
    metadata_member = _byte_properties(
        metadata_bytes,
        role="jobs_page_exchange_metadata",
        path=metadata_path,
        canonical=True,
    )
    wrapper = {
        "metadata_member": metadata_member,
        "metadata_record_canonical_bytes_equal_record": True,
        "record": record,
    }
    return wrapper, metadata_bytes, body_member, pagination_relation


def _repository_binding(source: RepositoryObject) -> dict[str, Any]:
    return {
        "git_blob_sha1": source.git_blob_sha1,
        "path": source.path,
        "role": source.role,
        "sha256": source.sha256,
        "size_bytes": source.size_bytes,
        "source_revision": source.source_revision,
    }


def _observed_provenance(
    sources: SourceSet,
    workflow_execution: WorkflowExecutionIdentity,
) -> dict[str, Any]:
    workflow = sources.workflow
    if workflow is None:
        _raise("capture_workflow_source_missing")
    return {
        "capture_implementation": {
            "dependency_policy": "python_standard_library_only",
            "execution_mode": "networked_capture",
            "producer_id": PRODUCER_ID,
            "producer_name": PRODUCER_NAME,
            "producer_source": TOOL_PATH,
            "producer_source_revision": sources.source_revision,
            "producer_source_sha256": sources.tool.sha256,
            "producer_version": TOOL_VERSION,
        },
        "capture_workflow_execution": {
            "authority_effect": "none",
            "event_name": "workflow_dispatch",
            "permissions": {"actions": "read", "contents": "read"},
            "repository": REPOSITORY,
            "source_ref": CAPTURE_SOURCE_REF,
            "workflow_id": workflow_execution.workflow_id,
            "workflow_name": CAPTURE_WORKFLOW_NAME,
            "workflow_path": CAPTURE_WORKFLOW_PATH,
            "workflow_run_attempt": workflow_execution.workflow_run_attempt,
            "workflow_run_id": workflow_execution.workflow_run_id,
            "workflow_run_key": workflow_execution.workflow_run_key,
            "workflow_source_revision": sources.source_revision,
            "workflow_source_sha256": workflow.sha256,
        },
        "provenance_class": "observed_networked_capture",
    }


def _example_provenance() -> dict[str, Any]:
    return {
        "capture_workflow_execution_claimed": False,
        "fixture_id": (
            "fixture:pulsemech-compute-post-run-producer-input-capture-example-v0"
        ),
        "fixture_source_path": EXAMPLE_PATH,
        "intended_capture_mode": "post_run_platform_response_snapshot",
        "intended_capture_tool_path": TOOL_PATH,
        "intended_capture_workflow_path": CAPTURE_WORKFLOW_PATH,
        "networked_capture_execution_claimed": False,
        "provenance_class": "checked_in_contract_example",
        "schema_identity": SCHEMA_VERSION,
    }


def _construct_manifest(
    *,
    sources: SourceSet,
    record_status: str,
    provenance: dict[str, Any],
    subject: dict[str, Any],
    run_exchange: dict[str, Any],
    page_captures: Sequence[PageCapture],
    reported_total_count: int,
    unique_job_count: int,
    step_record_count: int,
) -> dict[str, Any]:
    if record_status not in {"example", "observed"}:
        _raise("record_status_invalid")
    contract = sources.contract_document
    manifest_identity = {
        "canonicalization": "json-sort-keys-utf8-newline",
        "capture_root": (
            EXAMPLE_CAPTURE_ROOT
            if record_status == "example"
            else OBSERVED_CAPTURE_ROOT
        ),
        "capture_scope": (
            "example" if record_status == "example" else "historical_reference"
        ),
        "manifest_file_name": (
            EXAMPLE_MANIFEST_NAME
            if record_status == "example"
            else OBSERVED_MANIFEST_NAME
        ),
        "manifest_id": (
            "post-run-producer-input-capture:example-6066-v0"
            if record_status == "example"
            else "post-run-producer-input-capture:pulse-ci-6066-attempt-1-v0"
        ),
        "manifest_self_hash_included": False,
        "member_inventory_scope": "all_capture_files_except_this_manifest",
    }
    temporal_boundary = json.loads(json.dumps(contract["temporal_boundary"]))
    capture_layout = json.loads(json.dumps(contract["capture_layout"]))
    publication_boundary = json.loads(json.dumps(contract["publication_boundary"]))
    authority_boundary = json.loads(json.dumps(contract["authority_boundary"]))
    if record_status == "example":
        temporal_boundary.update(
            {
                "capture_is_platform_response_snapshot": False,
                "capture_subject_class": "contract_example",
                "capture_time_relation": "example_only",
                "reference_producer_input_eligible": False,
                "subject_run_completed_before_capture": False,
            }
        )
        capture_layout.update(
            {
                "manifest_file_name": EXAMPLE_MANIFEST_NAME,
                "root_path": EXAMPLE_CAPTURE_ROOT,
            }
        )
        publication_boundary["publication_status"] = "example"
        authority_boundary["capture_subject_class"] = "contract_example"
    page_count = len(page_captures)
    page_sequence = [page.page_number for page in page_captures]
    manifest = {
        "authority_boundary": authority_boundary,
        "availability_boundary": json.loads(
            json.dumps(contract["availability_boundary"])
        ),
        "capture_layout": capture_layout,
        "content_boundary": json.loads(json.dumps(contract["content_boundary"])),
        "contract_bindings": {
            "manifest_schema": _repository_binding(sources.schema),
            "normative_contract": _repository_binding(sources.contract),
        },
        "counts": {
            "count_relations_verified": True,
            "declared_non_manifest_member_count": 2 + (2 * page_count),
            "duplicate_job_id_count": 0,
            "duplicate_step_number_count": 0,
            "exchange_metadata_member_count": 1 + page_count,
            "jobs_page_exchange_count": page_count,
            "raw_response_member_count": 1 + page_count,
            "reconstructed_step_record_count": step_record_count,
            "reconstructed_unique_job_count": unique_job_count,
            "reported_job_count": reported_total_count,
            "run_attempt_exchange_count": 1,
        },
        "document_type": DOCUMENT_TYPE,
        "errors": [],
        "implementation_boundary": json.loads(
            json.dumps(contract["implementation_boundary"])
        ),
        "jobs_page_exchanges": [page.exchange_wrapper for page in page_captures],
        "limits": json.loads(json.dumps(contract["limits"])),
        "manifest_identity": manifest_identity,
        "ok": True,
        "pagination": {
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
            "reconstructed_unique_job_count": unique_job_count,
            "reported_total_count": reported_total_count,
            "reported_total_equals_reconstructed": True,
        },
        "privacy_boundary": json.loads(json.dumps(contract["privacy_boundary"])),
        "provenance": provenance,
        "publication_boundary": publication_boundary,
        "record_status": record_status,
        "request_contract": json.loads(json.dumps(contract["request_contract"])),
        "run_attempt_exchange": run_exchange,
        "schema_version": SCHEMA_VERSION,
        "subject": subject,
        "temporal_boundary": temporal_boundary,
    }
    return manifest


def _validate_constructed_manifest(
    manifest: dict[str, Any],
    *,
    record_status: str,
    page_count: int,
    job_count: int,
    step_record_count: int,
) -> bytes:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _raise("manifest_schema_version_mismatch")
    if manifest.get("document_type") != DOCUMENT_TYPE:
        _raise("manifest_document_type_mismatch")
    if manifest.get("record_status") != record_status:
        _raise("manifest_record_status_mismatch")
    if manifest.get("ok") is not True or manifest.get("errors") != []:
        _raise("manifest_success_state_invalid")
    if manifest.get("subject") != _expected_subject():
        _raise("manifest_subject_mismatch")
    identity = _require_object(
        manifest.get("manifest_identity"),
        error_code="manifest_identity_invalid",
    )
    forbidden_identity_fields = {
        "sha256",
        "size_bytes",
        "git_blob_sha1",
        "source_revision",
    }
    if forbidden_identity_fields.intersection(identity):
        _raise("manifest_self_identity_forbidden")
    if identity.get("manifest_self_hash_included") is not False:
        _raise("manifest_self_hash_forbidden")
    counts = _require_object(
        manifest.get("counts"),
        error_code="manifest_counts_invalid",
    )
    expected_counts = {
        "jobs_page_exchange_count": page_count,
        "raw_response_member_count": 1 + page_count,
        "exchange_metadata_member_count": 1 + page_count,
        "declared_non_manifest_member_count": 2 + 2 * page_count,
        "reported_job_count": job_count,
        "reconstructed_unique_job_count": job_count,
        "reconstructed_step_record_count": step_record_count,
        "duplicate_job_id_count": 0,
        "duplicate_step_number_count": 0,
        "count_relations_verified": True,
        "run_attempt_exchange_count": 1,
    }
    if counts != expected_counts:
        _raise("manifest_count_relation_mismatch")
    pagination = _require_object(
        manifest.get("pagination"),
        error_code="manifest_pagination_invalid",
    )
    if (
        pagination.get("page_count") != page_count
        or pagination.get("page_sequence") != list(range(1, page_count + 1))
        or pagination.get("reported_total_count") != job_count
        or pagination.get("reconstructed_unique_job_count") != job_count
        or pagination.get("final_next_link_absent") is not True
        or pagination.get("closure_status") != "closed"
    ):
        _raise("manifest_pagination_relation_mismatch")
    authority = _require_object(
        manifest.get("authority_boundary"),
        error_code="manifest_authority_boundary_invalid",
    )
    if (
        authority.get("authority_effect") != "none"
        or authority.get("capture_is_release_authority") is not False
        or authority.get("capture_is_release_decision") is not False
        or authority.get("capture_is_runtime_observation") is not False
        or authority.get("capture_is_runtime_observation_packet") is not False
        or authority.get("same_run_release_authority_eligible") is not False
    ):
        _raise("manifest_authority_boundary_mismatch")
    rendered = _canonical_json_bytes(manifest)
    reparsed = _parse_json_object(rendered, label="constructed_manifest")
    if reparsed != manifest or _canonical_json_bytes(reparsed) != rendered:
        _raise("manifest_canonicalization_failure")
    return rendered


def _scan_secret_bytes(files: Mapping[str, bytes], token_bytes: bytes) -> None:
    authorization_bytes = b"Bearer " + token_bytes
    for payload in files.values():
        if token_bytes in payload or authorization_bytes in payload:
            _raise("secret_value_in_output")


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath([str(path), str(parent)]) == str(parent)
    except ValueError:
        return False


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            written = os.write(fd, payload[offset:])
        except OSError:
            _raise("output_write_failed")
        if written <= 0:
            _raise("output_write_failed")
        offset += written


def _create_directory_at(parent_fd: int, name: str, mode: int) -> int:
    _safe_leaf_name(name)
    fd = -1
    try:
        os.mkdir(name, mode=mode, dir_fd=parent_fd)
        fd = os.open(name, _secure_open_flags(directory=True), dir_fd=parent_fd)
        os.fchmod(fd, mode)
    except OSError:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        _raise("output_directory_creation_failed")
    try:
        metadata = os.fstat(fd)
    except OSError:
        os.close(fd)
        _raise("output_directory_identity_unavailable")
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != mode:
        os.close(fd)
        _raise("output_directory_mode_invalid")
    return fd


def _write_file_at(directory_fd: int, name: str, payload: bytes) -> None:
    _safe_leaf_name(name)
    flags = _secure_open_flags(write=True) | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
    except OSError:
        _raise("output_file_creation_failed")
    try:
        _write_all(fd, payload)
        try:
            os.fsync(fd)
            metadata = os.fstat(fd)
        except OSError:
            _raise("output_file_write_failed")
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size != len(payload)
        ):
            _raise("output_file_identity_invalid")
    finally:
        os.close(fd)


def _rename_directory_noreplace(
    parent_fd: int,
    source_name: str,
    target_name: str,
) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError):
        _raise("renameat2_noreplace_unavailable")
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(target_name),
        1,
    )
    if result == 0:
        return
    observed_errno = ctypes.get_errno()
    if observed_errno == errno.EEXIST:
        _raise("existing_output_replacement_forbidden")
    if observed_errno in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
        _raise("renameat2_noreplace_unavailable")
    _raise("atomic_publication_failed")


def _read_file_at(directory_fd: int, name: str, *, maximum: int) -> bytes:
    try:
        fd = os.open(name, _secure_open_flags(), dir_fd=directory_fd)
    except OSError:
        _raise("published_member_open_failed")
    try:
        return _read_fd_bounded(
            fd,
            maximum=maximum,
            error_prefix="published_member",
        )
    finally:
        os.close(fd)


def _verify_exact_directory_inventory(
    root_fd: int,
    expected_files: Mapping[str, bytes],
) -> None:
    expected_root = {RAW_DIRECTORY, METADATA_DIRECTORY}
    expected_root.update(
        PurePosixPath(path).name
        for path in expected_files
        if len(PurePosixPath(path).parts) == 1
    )
    if set(os.listdir(root_fd)) != expected_root:
        _raise("published_root_inventory_mismatch")
    raw_fd = os.open(
        RAW_DIRECTORY,
        _secure_open_flags(directory=True),
        dir_fd=root_fd,
    )
    metadata_fd = os.open(
        METADATA_DIRECTORY,
        _secure_open_flags(directory=True),
        dir_fd=root_fd,
    )
    try:
        for fd in (raw_fd, metadata_fd):
            metadata = os.fstat(fd)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                _raise("published_directory_mode_invalid")
        expected_raw = {
            PurePosixPath(path).name
            for path in expected_files
            if PurePosixPath(path).parts[0] == RAW_DIRECTORY
        }
        expected_metadata = {
            PurePosixPath(path).name
            for path in expected_files
            if PurePosixPath(path).parts[0] == METADATA_DIRECTORY
        }
        if set(os.listdir(raw_fd)) != expected_raw:
            _raise("published_raw_inventory_mismatch")
        if set(os.listdir(metadata_fd)) != expected_metadata:
            _raise("published_metadata_inventory_mismatch")
        for relative_path, expected in expected_files.items():
            pure = PurePosixPath(relative_path)
            if len(pure.parts) == 1:
                directory_fd = root_fd
                leaf = pure.parts[0]
            elif pure.parts[0] == RAW_DIRECTORY and len(pure.parts) == 2:
                directory_fd = raw_fd
                leaf = pure.parts[1]
            elif pure.parts[0] == METADATA_DIRECTORY and len(pure.parts) == 2:
                directory_fd = metadata_fd
                leaf = pure.parts[1]
            else:
                _raise("published_member_path_invalid")
            observed = _read_file_at(
                directory_fd,
                leaf,
                maximum=MAX_TOTAL_CAPTURE_BYTES,
            )
            if observed != expected:
                _raise("published_member_byte_mismatch")
    finally:
        os.close(raw_fd)
        os.close(metadata_fd)


def _cleanup_owned_staging(
    *,
    parent_fd: int,
    staging_fd: int,
    staging_name: str,
    staging_identity: tuple[int, int],
) -> None:
    # Every known child is removed through the retained staging descriptor.
    # The random top-level directory is removed only if its name still denotes
    # the exact device/inode captured at creation; otherwise it is retained.
    try:
        for directory_name in (RAW_DIRECTORY, METADATA_DIRECTORY):
            try:
                child_fd = os.open(
                    directory_name,
                    _secure_open_flags(directory=True),
                    dir_fd=staging_fd,
                )
            except OSError:
                continue
            try:
                for name in os.listdir(child_fd):
                    try:
                        metadata = os.stat(
                            name,
                            dir_fd=child_fd,
                            follow_symlinks=False,
                        )
                    except OSError:
                        continue
                    if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                        try:
                            os.unlink(name, dir_fd=child_fd)
                        except OSError:
                            pass
            finally:
                os.close(child_fd)
            try:
                os.rmdir(directory_name, dir_fd=staging_fd)
            except OSError:
                pass
        for name in os.listdir(staging_fd):
            try:
                metadata = os.stat(
                    name,
                    dir_fd=staging_fd,
                    follow_symlinks=False,
                )
            except OSError:
                continue
            if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                try:
                    os.unlink(name, dir_fd=staging_fd)
                except OSError:
                    pass
        try:
            name_metadata = os.stat(
                staging_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except OSError:
            return
        if (
            stat.S_ISDIR(name_metadata.st_mode)
            and (name_metadata.st_dev, name_metadata.st_ino) == staging_identity
            and not os.listdir(staging_fd)
        ):
            try:
                os.rmdir(staging_name, dir_fd=parent_fd)
            except OSError:
                pass
    except BaseException:
        return


def _publish_capture(
    *,
    sources: SourceSet,
    output_directory: Path,
    files: Mapping[str, bytes],
) -> None:
    _validate_runtime_platform()
    target = output_directory.absolute()
    parent = target.parent
    target_name = _safe_leaf_name(target.name)
    if _path_is_within(target, sources.repository_root.absolute()):
        _raise("protected_repository_source_write_forbidden")
    parent_fd = _open_absolute_directory_no_symlinks(parent)
    staging_fd = -1
    staging_name = ""
    staging_identity = (-1, -1)
    published = False
    raw_fd = -1
    metadata_fd = -1
    try:
        try:
            os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError:
            _raise("output_target_state_unavailable")
        else:
            _raise("existing_output_replacement_forbidden")

        blocked_signals: set[signal.Signals] = {
            signal.SIGINT,
            signal.SIGTERM,
        }
        previous_mask: set[signal.Signals] | None = None
        if hasattr(signal, "pthread_sigmask"):
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked_signals)
        try:
            for _ in range(128):
                candidate = f".{target_name}.tmp-{secrets.token_hex(16)}"
                try:
                    os.mkdir(candidate, 0o700, dir_fd=parent_fd)
                except FileExistsError:
                    continue
                staging_name = candidate
                metadata = os.stat(
                    staging_name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                staging_fd = os.open(
                    staging_name,
                    _secure_open_flags(directory=True),
                    dir_fd=parent_fd,
                )
                os.fchmod(staging_fd, 0o700)
                opened = os.fstat(staging_fd)
                staging_identity = (opened.st_dev, opened.st_ino)
                if staging_identity != (metadata.st_dev, metadata.st_ino):
                    _raise("staging_directory_identity_mismatch")
                if stat.S_IMODE(opened.st_mode) != 0o700:
                    _raise("staging_directory_mode_invalid")
                break
            else:
                _raise("staging_directory_name_exhausted")
        finally:
            if previous_mask is not None:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

        raw_fd = _create_directory_at(staging_fd, RAW_DIRECTORY, 0o700)
        metadata_fd = _create_directory_at(staging_fd, METADATA_DIRECTORY, 0o700)
        for relative_path, payload in files.items():
            pure = _safe_relative_path(relative_path)
            if len(pure.parts) == 1:
                directory_fd = staging_fd
                leaf = pure.parts[0]
            elif len(pure.parts) == 2 and pure.parts[0] == RAW_DIRECTORY:
                directory_fd = raw_fd
                leaf = pure.parts[1]
            elif len(pure.parts) == 2 and pure.parts[0] == METADATA_DIRECTORY:
                directory_fd = metadata_fd
                leaf = pure.parts[1]
            else:
                _raise("output_member_path_outside_contract")
            _write_file_at(directory_fd, leaf, payload)
        os.fsync(raw_fd)
        os.fsync(metadata_fd)
        os.fsync(staging_fd)
        _verify_exact_directory_inventory(staging_fd, files)
        publication_mask: set[signal.Signals] | None = None
        if hasattr(signal, "pthread_sigmask"):
            publication_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK,
                {signal.SIGINT, signal.SIGTERM},
            )
        try:
            _rename_directory_noreplace(parent_fd, staging_name, target_name)
            published = True
        finally:
            if publication_mask is not None:
                signal.pthread_sigmask(signal.SIG_SETMASK, publication_mask)
        os.fsync(parent_fd)
        final_fd = os.open(
            target_name,
            _secure_open_flags(directory=True),
            dir_fd=parent_fd,
        )
        try:
            final_metadata = os.fstat(final_fd)
            if (final_metadata.st_dev, final_metadata.st_ino) != staging_identity:
                _raise("published_directory_identity_mismatch")
            _verify_exact_directory_inventory(final_fd, files)
            # Source admission is part of publication, while the owned output
            # and its parent still have retained descriptors for rollback.
            _revalidate_sources(sources)
        finally:
            os.close(final_fd)
    except BaseException:
        if staging_fd >= 0:
            cleanup_name = target_name if published else staging_name
            _cleanup_owned_staging(
                parent_fd=parent_fd,
                staging_fd=staging_fd,
                staging_name=cleanup_name,
                staging_identity=staging_identity,
            )
        raise
    finally:
        for fd in (raw_fd, metadata_fd, staging_fd, parent_fd):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass


def _capture_core(
    *,
    sources: SourceSet,
    output_directory: Path,
    token: str,
    transport: HttpTransport,
    clock: CaptureClock,
    record_status: str,
    workflow_execution: WorkflowExecutionIdentity | None,
) -> CaptureResult:
    token_bytes = _validate_token(token)
    if record_status == "observed":
        if workflow_execution is None:
            _raise("observed_capture_workflow_identity_required")
        provenance = _observed_provenance(sources, workflow_execution)
    elif record_status == "example":
        if workflow_execution is not None:
            _raise("example_capture_workflow_identity_forbidden")
        provenance = _example_provenance()
    else:
        _raise("record_status_invalid")

    _revalidate_sources(sources)
    run_response = _capture_response(
        transport=transport,
        clock=clock,
        token=token,
        request_target=RUN_REQUEST_PATH,
        label="run_attempt_response",
    )
    run_summary, subject = _validate_run_response(run_response)
    run_exchange, run_metadata_bytes, _ = _run_exchange(
        response=run_response,
        summary=run_summary,
        record_status=record_status,
    )

    all_job_ids: set[int] = set()
    page_captures: list[PageCapture] = []
    reported_total_count: int | None = None
    total_steps = 0
    accumulated_capture_bytes = len(run_response.body) + len(run_metadata_bytes)
    if accumulated_capture_bytes > MAX_TOTAL_CAPTURE_BYTES:
        _raise("total_capture_size_limit_exceeded")
    current_page = 1
    request_target = FIRST_JOBS_REQUEST_TARGET
    previous_response_time = _parse_utc(
        run_response.response_received_utc,
        error_code="run_response_received_utc_invalid",
    )
    while True:
        if current_page > MAX_JOBS_PAGE_COUNT:
            _raise("maximum_page_count_exceeded")
        page_response = _capture_response(
            transport=transport,
            clock=clock,
            token=token,
            request_target=request_target,
            label=f"jobs_page_{current_page}_response",
        )
        page_start = _parse_utc(
            page_response.capture_started_utc,
            error_code="jobs_page_capture_started_utc_invalid",
        )
        if page_start < previous_response_time:
            _raise("capture_exchange_time_order_invalid")
        previous_response_time = _parse_utc(
            page_response.response_received_utc,
            error_code="jobs_page_response_received_utc_invalid",
        )
        summary, page_total_count, page_step_count = _validate_jobs_page(
            page_response,
            page_number=current_page,
            subject=subject,
            all_job_ids=all_job_ids,
        )
        if reported_total_count is None:
            reported_total_count = page_total_count
        elif page_total_count != reported_total_count:
            _raise("page_total_count_disagreement")
        next_target, link_header_status = _link_next_target(
            page_response.selected_headers,
            current_page=current_page,
        )
        wrapper, metadata_bytes, _, pagination_relation = _jobs_exchange(
            page_number=current_page,
            request_target=request_target,
            response=page_response,
            summary=summary,
            next_target=next_target,
            link_header_status=link_header_status,
            record_status=record_status,
        )
        accumulated_capture_bytes += len(page_response.body) + len(metadata_bytes)
        if accumulated_capture_bytes > MAX_TOTAL_CAPTURE_BYTES:
            _raise("total_capture_size_limit_exceeded")
        page_captures.append(
            PageCapture(
                page_number=current_page,
                request_target=request_target,
                response=page_response,
                response_summary=summary,
                pagination_relation=pagination_relation,
                exchange_record=wrapper["record"],
                exchange_wrapper=wrapper,
                metadata_bytes=metadata_bytes,
            )
        )
        total_steps += page_step_count
        if total_steps > MAX_TOTAL_STEP_RECORDS:
            _raise("total_step_record_limit_exceeded")
        if next_target is None:
            break
        request_target = next_target
        current_page += 1

    if reported_total_count is None:
        _raise("reported_total_count_missing")
    unique_job_count = len(all_job_ids)
    if reported_total_count != unique_job_count:
        _raise("reported_total_count_mismatch")
    expected_page_count = max(
        1,
        math.ceil(reported_total_count / MAX_JOBS_PER_PAGE),
    )
    if len(page_captures) != expected_page_count:
        _raise("pagination_page_count_relation_mismatch")
    if record_status == "observed" and reported_total_count != EXPECTED_JOB_COUNT:
        _raise("initial_reference_job_count_mismatch")

    manifest = _construct_manifest(
        sources=sources,
        record_status=record_status,
        provenance=provenance,
        subject=subject,
        run_exchange=run_exchange,
        page_captures=page_captures,
        reported_total_count=reported_total_count,
        unique_job_count=unique_job_count,
        step_record_count=total_steps,
    )
    manifest_bytes = _validate_constructed_manifest(
        manifest,
        record_status=record_status,
        page_count=len(page_captures),
        job_count=unique_job_count,
        step_record_count=total_steps,
    )
    manifest_name = (
        EXAMPLE_MANIFEST_NAME
        if record_status == "example"
        else OBSERVED_MANIFEST_NAME
    )
    output_files: dict[str, bytes] = {
        RUN_BODY_PATH: run_response.body,
        RUN_METADATA_PATH: run_metadata_bytes,
        manifest_name: manifest_bytes,
    }
    for page in page_captures:
        output_files[JOBS_BODY_TEMPLATE % page.page_number] = page.response.body
        output_files[JOBS_METADATA_TEMPLATE % page.page_number] = page.metadata_bytes
    if set(output_files) != {
        RUN_BODY_PATH,
        RUN_METADATA_PATH,
        manifest_name,
        *[JOBS_BODY_TEMPLATE % page.page_number for page in page_captures],
        *[JOBS_METADATA_TEMPLATE % page.page_number for page in page_captures],
    }:
        _raise("output_member_inventory_mismatch")
    total_size = sum(len(payload) for payload in output_files.values())
    if total_size > MAX_TOTAL_CAPTURE_BYTES:
        _raise("total_capture_size_limit_exceeded")
    _scan_secret_bytes(output_files, token_bytes)
    _revalidate_sources(sources)
    _publish_capture(
        sources=sources,
        output_directory=output_directory,
        files=output_files,
    )
    return CaptureResult(
        record_status=record_status,
        manifest_file_name=manifest_name,
        manifest_bytes=manifest_bytes,
        manifest_sha256=_sha256(manifest_bytes),
        page_count=len(page_captures),
        job_count=unique_job_count,
        step_record_count=total_steps,
        authority_effect="none",
    )


def capture_with_injected_dependencies_for_test(
    *,
    repository_root: str | os.PathLike[str],
    output_directory: str | os.PathLike[str],
    token: str,
    transport: HttpTransport,
    clock: CaptureClock,
    source_revision: str | None = None,
) -> CaptureResult:
    """In-process fixture entrypoint; never exposed through the CLI.

    The output always uses the example provenance branch and cannot claim an
    observed platform-response snapshot or reference-producer-input status.
    """

    _validate_runtime_platform()
    root = Path(repository_root).absolute()
    if source_revision is None:
        root_fd = _open_absolute_directory_no_symlinks(root)
        try:
            source_revision = _run_git(
                root_fd,
                ["rev-parse", "HEAD"],
                maximum_output=128,
                error_code="fixture_repository_head_unavailable",
            ).decode("ascii", errors="strict").strip()
        finally:
            os.close(root_fd)
    if SHA40_RE.fullmatch(source_revision) is None:
        _raise("fixture_source_revision_invalid")
    sources = _load_sources(
        root,
        revision=source_revision,
        include_workflow=False,
    )
    return _capture_core(
        sources=sources,
        output_directory=Path(output_directory),
        token=token,
        transport=transport,
        clock=clock,
        record_status="example",
        workflow_execution=None,
    )


def _success_diagnostic(result: CaptureResult) -> bytes:
    return _canonical_json_bytes(
        {
            "authority_effect": result.authority_effect,
            "job_count": result.job_count,
            "manifest_file_name": result.manifest_file_name,
            "manifest_sha256": result.manifest_sha256,
            "ok": True,
            "page_count": result.page_count,
            "record_status": result.record_status,
            "step_record_count": result.step_record_count,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        }
    )


def _failure_diagnostic(error_code: str) -> bytes:
    return _canonical_json_bytes(
        {
            "authority_effect": "none",
            "error_code": error_code,
            "ok": False,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        }
    )


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        _raise("command_line_invalid")


def _install_termination_handler() -> None:
    def handle_termination(
        signum: int,
        frame: object,
    ) -> None:
        del signum, frame
        _raise("capture_interrupted")

    try:
        signal.signal(signal.SIGTERM, handle_termination)
    except (OSError, RuntimeError, ValueError):
        _raise("termination_handler_installation_failed")


def parse_args() -> argparse.Namespace:
    parser = _FailClosedArgumentParser(
        description=(
            "Capture the exact attempt-specific GitHub Actions platform-response "
            "entity bodies for the fixed historical PULSE CI #6066 reference."
        )
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output-directory", required=True)
    return parser.parse_args()


def main() -> int:
    _install_termination_handler()
    args = parse_args()
    repository_root = Path(args.repository_root).absolute()
    output_directory = Path(args.output_directory).absolute()
    sources, workflow_execution, token = _load_production_environment(
        repository_root
    )
    result = _capture_core(
        sources=sources,
        output_directory=output_directory,
        token=token,
        transport=StdlibHttpsTransport(),
        clock=SystemUtcClock(),
        record_status="observed",
        workflow_execution=workflow_execution,
    )
    sys.stdout.buffer.write(_success_diagnostic(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        sys.stderr.buffer.write(_failure_diagnostic(exc.error_code))
        raise SystemExit(2)
    except KeyboardInterrupt:
        sys.stderr.buffer.write(_failure_diagnostic("capture_interrupted"))
        raise SystemExit(2)
    except SystemExit:
        raise
    except BaseException:
        sys.stderr.buffer.write(_failure_diagnostic("unexpected_internal_error"))
        raise SystemExit(2)
