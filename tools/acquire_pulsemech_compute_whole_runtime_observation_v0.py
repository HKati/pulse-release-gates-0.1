#!/usr/bin/env python3
"""Acquire one exact Step 5C current-run whole-runtime observation input set.

The tool is the networked acquisition component of the Step 5C reference
workflow.  It validates an independently checked prelaunch plan, dispatches the
reviewed hosted release-grade PULSE CI subject, receives the exact run identity
from the version-pinned GitHub REST response, waits for that exact attempt,
collects bounded run/job/artifact metadata, downloads the three selected subject
terminal artifacts, dispatches the existing Step 3F provider with the exact
subject run ID, and downloads the exact Step 3F candidate envelope.

It does not build the final capture carrier, construct a runtime-observation
packet, run the compute analyzer, materialize gates, alter status, create a
release decision, or change release authority.  All output is staged privately
and published to one absent directory only after the complete acquisition has
succeeded.

Run the production CLI with isolated Python on Linux::

    python -I tools/acquire_pulsemech_compute_whole_runtime_observation_v0.py \
      --repository-root . \
      --source-commit <40-hex commit> \
      --plan <prelaunch-plan.json> \
      --plan-diagnostic <prelaunch-plan-diagnostic.json> \
      --expected-plan-sha256 <64-hex digest> \
      --output-directory <absent directory>

The live CLI requires the canonical GitHub Actions environment and a token in
``GITHUB_TOKEN`` (or the variable selected by ``--token-env``).  Permanent
regressions call :func:`acquire_observation` with a deterministic fake transport;
they do not dispatch live workflows.
"""
from __future__ import annotations

import sys

if __name__ == "__main__" and not (
    sys.flags.isolated == 1
    and sys.flags.ignore_environment == 1
    and sys.flags.no_user_site == 1
    and getattr(sys.flags, "safe_path", False)
):
    sys.stderr.write(
        '{"active_gate_eligible":false,"authority_effect":"none",'
        '"error_code":"isolated_python_required","ok":false,'
        '"same_run_release_authority_eligible":false,'
        '"tool":"acquire_pulsemech_compute_whole_runtime_observation_v0"}\n'
    )
    raise SystemExit(2)

import argparse
import ctypes
import errno
import hashlib
import http.client
import json
import math
import os
import re
import shutil
import ssl
import stat
import subprocess
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import SplitResult, urlsplit

import jsonschema


TOOL_ID = "acquire_pulsemech_compute_whole_runtime_observation_v0"
TOOL_VERSION = "0.1.0"
ACQUISITION_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_acquisition_v0"
)
EXPECTED_CONTEXT_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_expected_context_v0"
)
EVIDENCE_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_evidence_v0"
)
PLAN_RECORD_TYPE = "prelaunch_plan"
PLAN_DIAGNOSTIC_VERSION = (
    "pulsemech_compute_whole_runtime_observation_plan_check_v0"
)
PROFILE = "pulse_ci_hosted_release_grade_v0"
SCOPE = "one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
OWNER = "HKati"
REPOSITORY_NAME = "pulse-release-gates-0.1"
SOURCE_REF = "refs/heads/main"
DISPATCH_REF = "main"

REFERENCE_WORKFLOW_NAME = (
    "PULSEmech compute whole-runtime observation reference"
)
REFERENCE_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_whole_runtime_observation_reference.yml"
)
SUBJECT_WORKFLOW_NAME = "PULSE CI"
SUBJECT_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
PROVIDER_WORKFLOW_NAME = "PULSEmech compute current-run export candidate"
PROVIDER_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)

ACQUIRE_PATH = "tools/acquire_pulsemech_compute_whole_runtime_observation_v0.py"
PLAN_CHECKER_PATH = (
    "tools/check_pulsemech_compute_whole_runtime_observation_plan_v0.py"
)
SCHEMA_PATH = (
    "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"
)

API_HOST = "api.github.com"
API_BASE_URL = "https://api.github.com"
API_VERSION = "2026-03-10"
API_ACCEPT = "application/vnd.github+json"
USER_AGENT = "pulsemech-step5c-acquisition/0.1.0"
SUBJECT_DISPATCH_ENDPOINT = (
    "repos/HKati/pulse-release-gates-0.1/actions/workflows/pulse_ci.yml/dispatches"
)
PROVIDER_DISPATCH_ENDPOINT = (
    "repos/HKati/pulse-release-gates-0.1/actions/workflows/"
    "pulsemech_compute_current_run_export_candidate.yml/dispatches"
)
MAIN_REF_ENDPOINT = (
    "repos/HKati/pulse-release-gates-0.1/git/ref/heads/main"
)

SUBJECT_DISPATCH_INPUTS = {
    "strict_external_evidence": "true",
    "llamaguard_evidence_mode": "hosted_full_runtime",
}

SUBJECT_TERMINAL_ARTIFACT_TEMPLATES = (
    (
        "complete_release_grade_reference_package",
        "complete-release-grade-reference-package-{run_id}-1",
        "subject/artifacts/complete-release-grade-reference-package.zip",
    ),
    (
        "package_completeness_report",
        "release-grade-package-completeness-{run_id}-1",
        "subject/artifacts/release-grade-package-completeness.zip",
    ),
    (
        "package_verification_report",
        "release-grade-reference-package-verification-{run_id}-1",
        "subject/artifacts/release-grade-reference-package-verification.zip",
    ),
)
PROVIDER_ARTIFACT_TEMPLATE = (
    "pulsemech-compute-current-run-export-candidate-{subject_run_id}-1"
)
PROVIDER_ARTIFACT_MEMBER = "provider/step3f-candidate-envelope.zip"

EXPECTED_SUBJECT_JOB_COUNT = 8
EXPECTED_PROVIDER_JOB_COUNT = 1
EXPECTED_SUBJECT_SUCCESSFUL_JOBS = 7
EXPECTED_SUBJECT_SKIPPED_JOBS = 1

DEFAULT_API_REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_SUBJECT_WAIT_SECONDS = 5400
DEFAULT_PROVIDER_WAIT_SECONDS = 2700
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_MAX_JOBS = 64
DEFAULT_MAX_PLATFORM_STEP_RECORDS = 2048
DEFAULT_MAX_ARTIFACTS = 256
DEFAULT_MAX_API_JSON_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_SINGLE_ARTIFACT_BYTES = 768 * 1024 * 1024
DEFAULT_MAX_AGGREGATE_ARTIFACT_BYTES = 1536 * 1024 * 1024
DEFAULT_MAX_CAPTURE_MEMBERS = 8192
DEFAULT_MAX_CAPTURE_UNCOMPRESSED_BYTES = 2048 * 1024 * 1024

SUBJECT_DIRECTORY = "subject"
PROVIDER_DIRECTORY = "provider"
CONTROL_DIRECTORY = "control"
EXPECTED_CONTEXT_MEMBER = "expected_context.json"
ACQUISITION_INDEX_MEMBER = "acquisition-index.json"
SUBJECT_MAIN_REF_MEMBER = "control/main-before-subject-dispatch.json"
PROVIDER_MAIN_REF_MEMBER = "control/main-before-provider-dispatch.json"
SUBJECT_DISPATCH_REQUEST_MEMBER = "subject/dispatch-request.json"
SUBJECT_DISPATCH_RESPONSE_MEMBER = "subject/dispatch-response.json"
SUBJECT_DISPATCH_RECEIPT_MEMBER = "subject/dispatch-receipt.json"
SUBJECT_RUN_RESPONSE_MEMBER = "subject/run-response.json"
PROVIDER_DISPATCH_REQUEST_MEMBER = "provider/dispatch-request.json"
PROVIDER_DISPATCH_RESPONSE_MEMBER = "provider/dispatch-response.json"
PROVIDER_DISPATCH_RECEIPT_MEMBER = "provider/dispatch-receipt.json"
PROVIDER_RUN_RESPONSE_MEMBER = "provider/run-response.json"

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
POSITIVE_DECIMAL_RE = re.compile(r"^[1-9][0-9]*$")
UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?Z$"
)
MEMBER_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*\\)(?!.*\x00)"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$"
)
ACQUISITION_ID_RE = re.compile(r"^step5c-acquisition:[A-Za-z0-9._:-]+$")

AUTHORITY_BOUNDARY: dict[str, Any] = {
    "authority_effect": "none",
    "same_run_release_authority_eligible": False,
    "active_gate_eligible": False,
    "changes_gate_policy": False,
    "changes_gate_registry": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "introduces_resource_measurement": False,
    "observer_in_subject_totals": False,
    "subject_artifacts_mutated": False,
    "writes_subject_status": False,
}

PRIVACY_BOUNDARY: dict[str, Any] = {
    "raw_environment_included": False,
    "secret_values_included": False,
    "authorization_headers_included": False,
    "cookies_included": False,
    "request_bodies_included": False,
    "response_bodies_included": False,
    "raw_prompt_text_included": False,
    "raw_model_output_included": False,
    "private_or_arbitrary_user_prompt_admitted": False,
    "opaque_controlled_fixture_payloads_present": True,
    "redaction_applied": False,
    "redaction_rules_sha256": None,
}

TRUST_BOUNDARY: dict[str, list[str]] = {
    "trusted_components": sorted(
        [
            "step5c_supervisor",
            "step5c_plan_builder",
            "step5c_plan_checker",
            "step5c_acquisition_tool",
            "step5c_capture_tool",
            "step5c_verifier",
            "cpython_runtime",
            "github_hosted_runner",
            "host_kernel",
            "github_control_plane",
            "pulse_ci_components",
            "step3f_components",
        ]
    ),
    "not_proven": sorted(
        [
            "privileged_host_integrity",
            "runner_image_integrity",
            "interpreter_integrity_against_privileged_host",
            "observer_integrity_against_privileged_host",
            "github_control_plane_integrity",
            "provider_internal_execution",
            "complete_network_activity",
            "complete_package_manager_activity",
        ]
    ),
}


class AcquisitionError(RuntimeError):
    """Fail-closed acquisition error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        stage: str = "acquisition",
    ) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.stage = stage


class StrictJsonError(AcquisitionError):
    pass


@dataclass(frozen=True)
class CapturedFile:
    path: Path
    data: bytes
    device: int
    inode: int
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class HttpExchange:
    status: int
    headers: Mapping[str, str]
    body: bytes
    requested_utc: str
    received_utc: str


@dataclass(frozen=True)
class DownloadResult:
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class AcquisitionLimits:
    api_request_timeout_seconds: int
    subject_wait_seconds: int
    provider_wait_seconds: int
    max_jobs: int
    max_platform_step_records: int
    max_artifacts: int
    max_api_json_bytes: int
    max_single_artifact_bytes: int
    max_aggregate_artifact_bytes: int
    max_capture_members: int
    max_capture_uncompressed_bytes: int


@dataclass(frozen=True)
class ReferenceContext:
    record_status: str
    repository: str
    workflow_name: str
    workflow_path: str
    workflow_ref: str
    event_name: str
    ref: str
    source_commit: str
    run_id: int
    run_number: int
    run_attempt: int
    acquisition_id: str
    collector_run_key: str
    collector_execution_id: str


@dataclass(frozen=True)
class RunResult:
    summary: dict[str, Any]
    raw_body: bytes


@dataclass(frozen=True)
class PageCollection:
    rows: list[dict[str, Any]]
    members: list[str]
    total_count: int


@dataclass(frozen=True)
class ArtifactSelection:
    role: str
    metadata: dict[str, Any]
    member: str
    downloaded_sha256: str
    downloaded_size_bytes: int


class GitHubTransport(Protocol):
    """Transport interface used by production and deterministic tests."""

    def request(
        self,
        *,
        method: str,
        endpoint: str,
        body: bytes | None,
        max_response_bytes: int,
    ) -> HttpExchange:
        ...

    def download_artifact(
        self,
        *,
        endpoint: str,
        destination: Path,
        max_bytes: int,
    ) -> DownloadResult:
        ...


def _require(
    condition: bool,
    code: str,
    detail: str | None = None,
    *,
    stage: str = "acquisition",
) -> None:
    if not condition:
        raise AcquisitionError(code, detail, stage=stage)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    _require_canonical_tree(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _require_canonical_tree(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        _require(math.isfinite(value), "non_finite_json_number", path, stage="json")
        return
    if isinstance(value, str):
        _require(
            unicodedata.normalize("NFC", value) == value,
            "non_nfc_json_string",
            path,
            stage="json",
        )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_canonical_tree(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), "json_key_not_string", path, stage="json")
            _require(
                unicodedata.normalize("NFC", key) == key,
                "non_nfc_json_key",
                f"{path}.{key}",
                stage="json",
            )
            _require_canonical_tree(item, f"{path}.{key}")
        return
    raise AcquisitionError("unsupported_json_value", type(value).__name__, stage="json")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError("duplicate_json_key", key, stage="json")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise StrictJsonError("non_finite_json_number", value, stage="json")


def _reject_fractional(value: str) -> None:
    raise StrictJsonError("fractional_json_number_rejected", value, stage="json")


def _strict_json_object(data: bytes, *, label: str) -> dict[str, Any]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "json_bom_rejected", label, stage="json")
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
            parse_float=_reject_fractional,
        )
    except AcquisitionError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AcquisitionError(
            "invalid_json",
            f"{label}:{type(exc).__name__}",
            stage="json",
        ) from exc
    _require(isinstance(value, dict), "json_object_required", label, stage="json")
    _require_canonical_tree(value, label)
    return value


def _parse_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), "utc_string_required", label, stage="time")
    _require(UTC_RE.fullmatch(value) is not None, "invalid_utc_timestamp", label, stage="time")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise AcquisitionError("invalid_calendar_timestamp", label, stage="time") from exc


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _positive_int(value: Any, *, label: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        "positive_integer_required",
        label,
    )
    return int(value)


def _canonical_sha40(value: str, *, label: str) -> str:
    normalized = str(value).strip().lower()
    _require(SHA40_RE.fullmatch(normalized) is not None, "sha40_required", label)
    return normalized


def _canonical_sha256(value: str, *, label: str) -> str:
    normalized = str(value).strip().lower()
    _require(SHA256_RE.fullmatch(normalized) is not None, "sha256_required", label)
    return normalized


def _canonical_member(value: str, *, label: str) -> str:
    _require(isinstance(value, str), "member_name_required", label, stage="path")
    _require(MEMBER_RE.fullmatch(value) is not None, "unsafe_member_name", label, stage="path")
    return value


def _git_environment(root: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": str(root),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def _git(root: Path, args: Sequence[str], *, timeout: int = 30) -> bytes:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "--no-replace-objects", "-C", str(root), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=_git_environment(root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcquisitionError("git_execution_failed", type(exc).__name__, stage="source") from exc
    _require(
        result.returncode == 0,
        "git_command_failed",
        " ".join(args[:3]),
        stage="source",
    )
    return result.stdout


def _validate_repository_root(value: Path) -> Path:
    root = Path(os.path.abspath(os.fspath(value)))
    _require(root.is_dir(), "repository_root_not_directory", str(root), stage="path")
    _require(not root.is_symlink(), "repository_root_symlink_rejected", str(root), stage="path")
    return root


def _secure_open_constants() -> tuple[int, int]:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    missing = [name for name in required if not hasattr(os, name)]
    _require(
        os.name == "posix" and not missing and os.open in os.supports_dir_fd,
        "secure_read_unavailable",
        ",".join(missing) if missing else "dir_fd_unavailable",
        stage="path",
    )
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    return directory_flags, file_flags


def _capture_regular_file(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> CapturedFile:
    absolute = Path(os.path.abspath(os.fspath(path)))
    directory_flags, file_flags = _secure_open_constants()
    parts = absolute.parts
    _require(absolute.is_absolute() and len(parts) >= 2, "absolute_path_required", label, stage="path")

    directory_fd = os.open(parts[0], directory_flags)
    file_fd: int | None = None
    try:
        for component in parts[1:-1]:
            _require(component not in {"", ".", ".."}, "unsafe_path_component", label, stage="path")
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd

        basename = parts[-1]
        _require(basename not in {"", ".", ".."}, "unsafe_path_basename", label, stage="path")
        file_fd = os.open(basename, file_flags, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        _require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
            "regular_single_link_input_required",
            label,
            stage="input",
        )
        _require(0 <= before.st_size <= max_bytes, "input_size_limit_exceeded", label, stage="input")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(file_fd, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            _require(total <= max_bytes, "input_size_limit_exceeded", label, stage="input")
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        _require(
            before_identity == after_identity and len(data) == after.st_size,
            "input_changed_during_capture",
            label,
            stage="input",
        )
        named = os.stat(basename, dir_fd=directory_fd, follow_symlinks=False)
        named_identity = (
            named.st_dev,
            named.st_ino,
            named.st_size,
            named.st_mtime_ns,
            named.st_ctime_ns,
            named.st_nlink,
        )
        _require(
            named_identity == after_identity,
            "input_replaced_during_capture",
            label,
            stage="input",
        )
        return CapturedFile(
            path=absolute,
            data=data,
            device=after.st_dev,
            inode=after.st_ino,
            size_bytes=len(data),
            sha256=_sha256(data),
        )
    except OSError as exc:
        raise AcquisitionError(
            "secure_input_open_failed",
            f"{label}:{exc.errno}",
            stage="input",
        ) from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def _git_blob_bytes(root: Path, revision: str, relative: str) -> tuple[str, bytes]:
    _canonical_member(relative, label="git_relative_path")
    entry = _git(root, ["ls-tree", "-z", revision, "--", relative])
    _require(entry.count(b"\0") == 1, "git_path_entry_count_invalid", relative, stage="source")
    _require(
        entry.startswith((b"100644 blob ", b"100755 blob "))
        and entry.endswith(b"\t" + relative.encode("utf-8") + b"\0"),
        "git_source_not_regular_blob",
        relative,
        stage="source",
    )
    fields = entry[:-1].split(b"\t", 1)[0].split()
    _require(len(fields) == 3, "git_source_entry_invalid", relative, stage="source")
    blob_sha1 = fields[2].decode("ascii", errors="strict").lower()
    _require(SHA40_RE.fullmatch(blob_sha1) is not None, "git_blob_sha1_invalid", relative, stage="source")
    data = _git(root, ["cat-file", "blob", f"{revision}:{relative}"])
    return blob_sha1, data


def _verify_installed_source(
    *,
    root: Path,
    revision: str,
    relative: str,
    expected_sha256: str | None = None,
) -> CapturedFile:
    expected_path = root / relative
    capture = _capture_regular_file(
        expected_path,
        label=f"installed_source:{relative}",
        max_bytes=8 * 1024 * 1024,
    )
    _blob_sha1, committed = _git_blob_bytes(root, revision, relative)
    _require(
        capture.data == committed,
        "installed_source_mismatch",
        relative,
        stage="source",
    )
    if expected_sha256 is not None:
        _require(
            capture.sha256 == expected_sha256,
            "installed_source_digest_mismatch",
            relative,
            stage="source",
        )
    return capture


def _validate_output_destination(value: Path) -> tuple[Path, Path]:
    output = Path(os.path.abspath(os.fspath(value)))
    _require(output.is_absolute(), "output_path_must_be_absolute", stage="path")
    _require(output.name not in {"", ".", ".."}, "unsafe_output_basename", stage="path")
    parent = output.parent
    _require(parent.is_dir(), "output_parent_not_directory", str(parent), stage="path")
    _require(not parent.is_symlink(), "output_parent_symlink_rejected", str(parent), stage="path")

    directory_flags, _file_flags = _secure_open_constants()
    parts = parent.parts
    fd = os.open(parts[0], directory_flags)
    try:
        for component in parts[1:]:
            _require(component not in {"", ".", ".."}, "unsafe_output_parent_component", stage="path")
            next_fd = os.open(component, directory_flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        try:
            os.stat(output.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise AcquisitionError("output_already_exists", str(output), stage="publication")
    finally:
        os.close(fd)
    return output, parent


def _write_new_file(root: Path, member: str, data: bytes, *, mode: int = 0o600) -> Path:
    relative = _canonical_member(member, label="output_member")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _require(not path.exists() and not path.is_symlink(), "output_member_already_exists", relative, stage="publication")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags, mode)
    try:
        view = memoryview(data)
        written = 0
        while written < len(view):
            count = os.write(fd, view[written:])
            _require(count > 0, "output_write_failed", relative, stage="publication")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    _require(path.is_file() and not path.is_symlink(), "output_member_not_regular", relative, stage="publication")
    _require(path.stat().st_nlink == 1, "output_member_link_count_invalid", relative, stage="publication")
    return path


def _descriptor(root: Path, member: str) -> dict[str, Any]:
    relative = _canonical_member(member, label="descriptor_member")
    path = root / relative
    _require(path.is_file() and not path.is_symlink(), "descriptor_input_missing", relative, stage="publication")
    return {
        "member": relative,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _set_tree_read_only(root: Path) -> None:
    files: list[Path] = []
    directories: list[Path] = []
    for path in root.rglob("*"):
        _require(not path.is_symlink(), "staging_symlink_rejected", str(path), stage="publication")
        if path.is_file():
            _require(path.stat().st_nlink == 1, "staging_file_link_count_invalid", str(path), stage="publication")
            files.append(path)
        elif path.is_dir():
            directories.append(path)
        else:
            raise AcquisitionError("staging_nonregular_entry", str(path), stage="publication")
    for path in files:
        path.chmod(0o444)
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def _rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    _require(renameat2 is not None, "rename_noreplace_unavailable", stage="publication")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    result = renameat2(
        at_fdcwd,
        os.fsencode(source),
        at_fdcwd,
        os.fsencode(destination),
        rename_noreplace,
    )
    if result == 0:
        return
    err = ctypes.get_errno()
    if err in {errno.EEXIST, errno.ENOTEMPTY}:
        raise AcquisitionError("output_already_exists", str(destination), stage="publication")
    raise AcquisitionError("atomic_publication_failed", str(err), stage="publication")


def _sanitize_environment(token_env: str) -> str:
    _require(
        re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", token_env) is not None,
        "token_environment_name_invalid",
        stage="authentication",
    )
    token = os.environ.get(token_env)
    _require(isinstance(token, str) and token.strip() != "", "github_token_missing", token_env, stage="authentication")
    _require("\n" not in token and "\r" not in token and "\x00" not in token, "github_token_invalid", token_env, stage="authentication")
    return token.strip()


def _canonical_endpoint(endpoint: str) -> str:
    _require(isinstance(endpoint, str) and endpoint != "", "api_endpoint_missing", stage="network")
    _require(not endpoint.startswith("http"), "absolute_api_endpoint_rejected", stage="network")
    normalized = endpoint[1:] if endpoint.startswith("/") else endpoint
    _require(
        normalized.startswith(f"repos/{OWNER}/{REPOSITORY_NAME}/"),
        "api_endpoint_repository_mismatch",
        stage="network",
    )
    _require(".." not in normalized.split("/"), "api_endpoint_traversal_rejected", stage="network")
    _require("\n" not in normalized and "\r" not in normalized, "api_endpoint_newline_rejected", stage="network")
    return "/" + normalized


class LiveGitHubTransport:
    """Minimal version-pinned GitHub REST transport.

    Authentication is held in memory and sent only to ``api.github.com``.  A
    signed artifact redirect is followed without forwarding the Authorization
    header to the storage host.  Redirect URLs and headers are never persisted.
    """

    def __init__(
        self,
        *,
        token: str,
        timeout_seconds: int,
        now: Callable[[], str] = _utc_now,
    ) -> None:
        _require(timeout_seconds > 0, "api_timeout_invalid", stage="network")
        self._token = token
        self._timeout_seconds = timeout_seconds
        self._now = now
        self._ssl_context = ssl.create_default_context()

    def _connection(self, host: str, port: int | None = None) -> http.client.HTTPSConnection:
        return http.client.HTTPSConnection(
            host,
            port=port,
            timeout=self._timeout_seconds,
            context=self._ssl_context,
        )

    def request(
        self,
        *,
        method: str,
        endpoint: str,
        body: bytes | None,
        max_response_bytes: int,
    ) -> HttpExchange:
        path = _canonical_endpoint(endpoint)
        _require(method in {"GET", "POST"}, "api_method_not_allowed", method, stage="network")
        _require(max_response_bytes > 0, "api_response_limit_invalid", stage="network")
        headers = {
            "Accept": API_ACCEPT,
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        requested = self._now()
        connection = self._connection(API_HOST)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            content_encoding = response.getheader("Content-Encoding")
            _require(
                content_encoding in {None, "", "identity"},
                "unexpected_api_content_encoding",
                stage="network",
            )
            declared_length = response.getheader("Content-Length")
            if declared_length is not None:
                try:
                    declared = int(declared_length, 10)
                except ValueError as exc:
                    raise AcquisitionError("invalid_api_content_length", stage="network") from exc
                _require(0 <= declared <= max_response_bytes, "api_response_too_large", stage="network")
            payload = response.read(max_response_bytes + 1)
            _require(len(payload) <= max_response_bytes, "api_response_too_large", stage="network")
            received = self._now()
            response_headers = {
                key.lower(): value
                for key, value in response.getheaders()
                if key.lower() in {"content-type", "content-length", "etag", "x-github-request-id"}
            }
            return HttpExchange(
                status=int(response.status),
                headers=response_headers,
                body=payload,
                requested_utc=requested,
                received_utc=received,
            )
        except AcquisitionError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise AcquisitionError(
                "github_api_request_failed",
                type(exc).__name__,
                stage="network",
            ) from exc
        finally:
            connection.close()

    @staticmethod
    def _validate_redirect_url(value: str) -> SplitResult:
        parsed = urlsplit(value)
        _require(parsed.scheme == "https", "artifact_redirect_not_https", stage="network")
        _require(parsed.hostname is not None, "artifact_redirect_host_missing", stage="network")
        _require(parsed.username is None and parsed.password is None, "artifact_redirect_userinfo_rejected", stage="network")
        _require(parsed.fragment == "", "artifact_redirect_fragment_rejected", stage="network")
        _require(parsed.port in {None, 443}, "artifact_redirect_port_rejected", stage="network")
        _require(parsed.path.startswith("/"), "artifact_redirect_path_invalid", stage="network")
        return parsed

    def download_artifact(
        self,
        *,
        endpoint: str,
        destination: Path,
        max_bytes: int,
    ) -> DownloadResult:
        _require(max_bytes > 0, "artifact_download_limit_invalid", stage="network")
        api_path = _canonical_endpoint(endpoint)
        target = SplitResult("https", API_HOST, api_path, "", "")
        first_request = True
        redirects = 0
        connection: http.client.HTTPSConnection | None = None
        fd: int | None = None
        digest = hashlib.sha256()
        total = 0
        try:
            while True:
                host = target.hostname
                _require(host is not None, "artifact_download_host_missing", stage="network")
                path = target.path or "/"
                if target.query:
                    path += "?" + target.query
                headers = {
                    "Accept": "application/octet-stream",
                    "User-Agent": USER_AGENT,
                }
                if first_request:
                    headers["Authorization"] = f"Bearer {self._token}"
                    headers["X-GitHub-Api-Version"] = API_VERSION
                connection = self._connection(host, target.port)
                connection.request("GET", path, headers=headers)
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.getheader("Location")
                    redirect_body = response.read(65537)
                    _require(
                        len(redirect_body) <= 65536,
                        "artifact_redirect_body_too_large",
                        stage="network",
                    )
                    connection.close()
                    connection = None
                    _require(isinstance(location, str) and location != "", "artifact_redirect_location_missing", stage="network")
                    redirects += 1
                    _require(redirects <= 5, "artifact_redirect_limit_exceeded", stage="network")
                    target = self._validate_redirect_url(location)
                    first_request = False
                    continue

                _require(response.status == 200, "artifact_download_http_status", str(response.status), stage="network")
                content_encoding = response.getheader("Content-Encoding")
                _require(content_encoding in {None, "", "identity"}, "unexpected_artifact_content_encoding", stage="network")
                declared_length = response.getheader("Content-Length")
                if declared_length is not None:
                    try:
                        declared = int(declared_length, 10)
                    except ValueError as exc:
                        raise AcquisitionError("invalid_artifact_content_length", stage="network") from exc
                    _require(0 < declared <= max_bytes, "artifact_download_size_limit_exceeded", stage="network")

                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
                fd = os.open(destination, flags, 0o600)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    _require(total <= max_bytes, "artifact_download_size_limit_exceeded", stage="network")
                    digest.update(chunk)
                    view = memoryview(chunk)
                    offset = 0
                    while offset < len(view):
                        count = os.write(fd, view[offset:])
                        _require(count > 0, "artifact_download_write_failed", stage="network")
                        offset += count
                _require(total > 0, "artifact_download_empty", stage="network")
                os.fsync(fd)
                os.close(fd)
                fd = None
                connection.close()
                connection = None
                _require(destination.is_file() and not destination.is_symlink(), "artifact_download_not_regular", stage="network")
                _require(destination.stat().st_nlink == 1, "artifact_download_link_count_invalid", stage="network")
                return DownloadResult(size_bytes=total, sha256=digest.hexdigest())
        except AcquisitionError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise AcquisitionError(
                "artifact_download_failed",
                type(exc).__name__,
                stage="network",
            ) from exc
        finally:
            if fd is not None:
                os.close(fd)
            if connection is not None:
                connection.close()
            if destination.exists() and (
                not destination.is_file() or destination.stat().st_size != total
            ):
                try:
                    destination.unlink()
                except OSError:
                    pass


def _source_inventory_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = plan.get("source_inventory")
    _require(isinstance(rows, list), "plan_source_inventory_missing", stage="plan")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "plan_source_inventory_row_invalid", stage="plan")
        path = row.get("path")
        _require(isinstance(path, str) and path not in result, "plan_source_inventory_duplicate", str(path), stage="plan")
        result[path] = row
    return result


def _limits_from_plan(plan: dict[str, Any]) -> AcquisitionLimits:
    raw = plan.get("finite_limits")
    _require(isinstance(raw, dict), "plan_finite_limits_missing", stage="plan")
    expected = {
        "api_request_timeout_seconds": DEFAULT_API_REQUEST_TIMEOUT_SECONDS,
        "subject_wait_seconds": DEFAULT_SUBJECT_WAIT_SECONDS,
        "provider_wait_seconds": DEFAULT_PROVIDER_WAIT_SECONDS,
        "max_jobs": DEFAULT_MAX_JOBS,
        "max_platform_step_records": DEFAULT_MAX_PLATFORM_STEP_RECORDS,
        "max_artifacts": DEFAULT_MAX_ARTIFACTS,
        "max_api_json_bytes": DEFAULT_MAX_API_JSON_BYTES,
        "max_single_artifact_bytes": DEFAULT_MAX_SINGLE_ARTIFACT_BYTES,
        "max_aggregate_artifact_bytes": DEFAULT_MAX_AGGREGATE_ARTIFACT_BYTES,
        "max_capture_members": DEFAULT_MAX_CAPTURE_MEMBERS,
        "max_capture_uncompressed_bytes": DEFAULT_MAX_CAPTURE_UNCOMPRESSED_BYTES,
    }
    _require(raw == expected, "plan_finite_limits_mismatch", stage="plan")
    return AcquisitionLimits(**expected)


def _validate_plan_contract(
    *,
    plan_capture: CapturedFile,
    diagnostic_capture: CapturedFile,
    expected_plan_sha256: str,
    source_commit: str,
    record_status: str,
) -> tuple[dict[str, Any], AcquisitionLimits]:
    _require(plan_capture.sha256 == expected_plan_sha256, "plan_digest_mismatch", stage="plan")
    plan = _strict_json_object(plan_capture.data, label="prelaunch_plan")
    _require(plan.get("schema_version") == EVIDENCE_SCHEMA_VERSION, "plan_schema_version_mismatch", stage="plan")
    _require(plan.get("record_type") == PLAN_RECORD_TYPE, "plan_record_type_mismatch", stage="plan")
    _require(plan.get("record_status") == record_status, "plan_record_status_mismatch", stage="plan")
    identity = plan.get("plan_identity")
    _require(isinstance(identity, dict), "plan_identity_missing", stage="plan")
    _require(identity.get("profile") == PROFILE, "plan_profile_mismatch", stage="plan")
    _require(identity.get("scope") == SCOPE, "plan_scope_mismatch", stage="plan")
    _require(identity.get("repository") == REPOSITORY, "plan_repository_mismatch", stage="plan")
    _require(identity.get("source_commit") == source_commit, "plan_source_mismatch", stage="plan")
    _require(identity.get("source_ref") == SOURCE_REF, "plan_source_ref_mismatch", stage="plan")
    _require(plan.get("authority_boundary") == AUTHORITY_BOUNDARY, "plan_authority_boundary_mismatch", stage="plan")
    _require(plan.get("privacy_boundary") == PRIVACY_BOUNDARY, "plan_privacy_boundary_mismatch", stage="plan")

    subject_dispatch = plan.get("subject_dispatch")
    provider_dispatch = plan.get("provider_dispatch")
    expected_subject = {
        "api_version": API_VERSION,
        "method": "POST",
        "accept": API_ACCEPT,
        "endpoint": SUBJECT_DISPATCH_ENDPOINT,
        "ref": DISPATCH_REF,
        "inputs": dict(SUBJECT_DISPATCH_INPUTS),
        "response_contract": {
            "http_status": 200,
            "required_fields": ["workflow_run_id", "run_url", "html_url"],
            "run_list_fallback_allowed": False,
            "accepted_attempt": 1,
        },
    }
    expected_provider = {
        "api_version": API_VERSION,
        "method": "POST",
        "accept": API_ACCEPT,
        "endpoint": PROVIDER_DISPATCH_ENDPOINT,
        "ref": DISPATCH_REF,
        "input_bindings": {"source_run_id": "subject_dispatch.workflow_run_id"},
        "response_contract": {
            "http_status": 200,
            "required_fields": ["workflow_run_id", "run_url", "html_url"],
            "run_list_fallback_allowed": False,
            "accepted_attempt": 1,
        },
    }
    _require(subject_dispatch == expected_subject, "plan_subject_dispatch_mismatch", stage="plan")
    _require(provider_dispatch == expected_provider, "plan_provider_dispatch_mismatch", stage="plan")

    diagnostic = _strict_json_object(diagnostic_capture.data, label="prelaunch_plan_diagnostic")
    _require(diagnostic.get("schema_version") == PLAN_DIAGNOSTIC_VERSION, "plan_diagnostic_version_mismatch", stage="plan")
    _require(diagnostic.get("ok") is True and diagnostic.get("record_status") == "verified", "plan_diagnostic_not_verified", stage="plan")
    plan_diag = diagnostic.get("plan")
    _require(isinstance(plan_diag, dict), "plan_diagnostic_plan_missing", stage="plan")
    _require(plan_diag.get("sha256") == expected_plan_sha256, "plan_diagnostic_digest_mismatch", stage="plan")
    _require(plan_diag.get("source_commit") == source_commit, "plan_diagnostic_source_mismatch", stage="plan")
    _require(plan_diag.get("record_status") == record_status, "plan_diagnostic_record_status_mismatch", stage="plan")
    _require(plan_diag.get("byte_identical_to_independent_reconstruction") is True, "plan_diagnostic_reconstruction_missing", stage="plan")
    _require(diagnostic.get("authority_boundary") == AUTHORITY_BOUNDARY, "plan_diagnostic_authority_boundary_mismatch", stage="plan")
    return plan, _limits_from_plan(plan)


def _rerun_plan_checker(
    *,
    root: Path,
    source_commit: str,
    plan_capture: CapturedFile,
    diagnostic_capture: CapturedFile,
    expected_plan_sha256: str,
    record_status: str,
) -> None:
    checker = root / PLAN_CHECKER_PATH
    executable_dir = str(Path(sys.executable).resolve().parent)
    environment = {
        "PATH": executable_dir + ":/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": str(root),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(checker),
                "--repository-root",
                str(root),
                "--plan",
                str(plan_capture.path),
                "--expected-source-commit",
                source_commit,
                "--expected-plan-sha256",
                expected_plan_sha256,
                "--expected-record-status",
                record_status,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=180,
            cwd=root,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcquisitionError(
            "plan_checker_execution_failed",
            type(exc).__name__,
            stage="plan",
        ) from exc
    _require(len(result.stdout) <= 4 * 1024 * 1024, "plan_checker_stdout_too_large", stage="plan")
    _require(len(result.stderr) <= 1024 * 1024, "plan_checker_stderr_too_large", stage="plan")
    _require(result.returncode == 0, "plan_checker_rejected", stage="plan")
    _require(result.stderr == b"", "plan_checker_unexpected_stderr", stage="plan")
    _require(
        result.stdout == diagnostic_capture.data,
        "plan_diagnostic_reconstruction_mismatch",
        stage="plan",
    )


def _reference_context_from_environment(
    *,
    source_commit: str,
    record_status: str,
    environment: Mapping[str, str],
) -> ReferenceContext:
    _require(record_status == "observed", "live_record_status_must_be_observed", stage="context")
    repository = environment.get("GITHUB_REPOSITORY", "")
    workflow = environment.get("GITHUB_WORKFLOW", "")
    workflow_ref = environment.get("GITHUB_WORKFLOW_REF", "")
    event_name = environment.get("GITHUB_EVENT_NAME", "")
    ref = environment.get("GITHUB_REF", "")
    sha = str(environment.get("GITHUB_SHA", "")).lower()
    workflow_sha = str(environment.get("GITHUB_WORKFLOW_SHA", "")).lower()
    run_id_text = environment.get("GITHUB_RUN_ID", "")
    run_number_text = environment.get("GITHUB_RUN_NUMBER", "")
    run_attempt_text = environment.get("GITHUB_RUN_ATTEMPT", "")

    _require(repository == REPOSITORY, "reference_repository_mismatch", stage="context")
    _require(workflow == REFERENCE_WORKFLOW_NAME, "reference_workflow_name_mismatch", stage="context")
    expected_workflow_ref = f"{REPOSITORY}/{REFERENCE_WORKFLOW_PATH}@refs/heads/main"
    _require(workflow_ref == expected_workflow_ref, "reference_workflow_ref_mismatch", stage="context")
    _require(event_name == "workflow_dispatch", "reference_event_mismatch", stage="context")
    _require(ref == SOURCE_REF, "reference_ref_mismatch", stage="context")
    _require(sha == source_commit, "reference_source_mismatch", stage="context")
    _require(workflow_sha == source_commit, "reference_workflow_source_mismatch", stage="context")
    _require(POSITIVE_DECIMAL_RE.fullmatch(run_id_text) is not None, "reference_run_id_invalid", stage="context")
    _require(POSITIVE_DECIMAL_RE.fullmatch(run_number_text) is not None, "reference_run_number_invalid", stage="context")
    _require(run_attempt_text == "1", "reference_run_attempt_mismatch", stage="context")
    run_id = int(run_id_text, 10)
    run_number = int(run_number_text, 10)
    acquisition_id = f"step5c-acquisition:{run_id}-1"
    collector_run_key = (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT=1|"
        f"GITHUB_WORKFLOW={REFERENCE_WORKFLOW_NAME}"
    )
    return ReferenceContext(
        record_status=record_status,
        repository=repository,
        workflow_name=workflow,
        workflow_path=REFERENCE_WORKFLOW_PATH,
        workflow_ref=workflow_ref,
        event_name=event_name,
        ref=ref,
        source_commit=source_commit,
        run_id=run_id,
        run_number=run_number,
        run_attempt=1,
        acquisition_id=acquisition_id,
        collector_run_key=collector_run_key,
        collector_execution_id="execution:step5c:collector:post-run-platform-export",
    )


def _validate_reference_context(context: ReferenceContext) -> None:
    _require(context.record_status in {"example", "observed"}, "record_status_invalid", stage="context")
    _require(context.repository == REPOSITORY, "reference_repository_mismatch", stage="context")
    _require(context.workflow_name == REFERENCE_WORKFLOW_NAME, "reference_workflow_name_mismatch", stage="context")
    _require(context.workflow_path == REFERENCE_WORKFLOW_PATH, "reference_workflow_path_mismatch", stage="context")
    _require(context.event_name == "workflow_dispatch", "reference_event_mismatch", stage="context")
    _require(context.ref == SOURCE_REF, "reference_ref_mismatch", stage="context")
    _canonical_sha40(context.source_commit, label="reference_source_commit")
    _positive_int(context.run_id, label="reference_run_id")
    _positive_int(context.run_number, label="reference_run_number")
    _require(context.run_attempt == 1, "reference_run_attempt_mismatch", stage="context")
    _require(ACQUISITION_ID_RE.fullmatch(context.acquisition_id) is not None, "acquisition_id_invalid", stage="context")
    expected_run_key = (
        f"GITHUB_RUN_ID={context.run_id}|GITHUB_RUN_ATTEMPT=1|"
        f"GITHUB_WORKFLOW={REFERENCE_WORKFLOW_NAME}"
    )
    _require(context.collector_run_key == expected_run_key, "collector_run_key_mismatch", stage="context")
    _require(
        context.collector_execution_id
        == "execution:step5c:collector:post-run-platform-export",
        "collector_execution_id_mismatch",
        stage="context",
    )


def _expected_context_document(
    *,
    context: ReferenceContext,
    expected_plan_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": EXPECTED_CONTEXT_SCHEMA_VERSION,
        "record_status": context.record_status,
        "repository": context.repository,
        "source_commit": context.source_commit,
        "source_ref": context.ref,
        "reference_workflow_name": context.workflow_name,
        "reference_workflow_path": context.workflow_path,
        "reference_workflow_ref": context.workflow_ref,
        "reference_event_name": context.event_name,
        "reference_run_id": context.run_id,
        "reference_run_number": context.run_number,
        "reference_run_attempt": context.run_attempt,
        "collector_run_key": context.collector_run_key,
        "collector_execution_id": context.collector_execution_id,
        "acquisition_id": context.acquisition_id,
        "expected_plan_sha256": expected_plan_sha256,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [],
        "ok": True,
    }


def _request_json(
    transport: GitHubTransport,
    *,
    method: str,
    endpoint: str,
    body: bytes | None,
    max_bytes: int,
    expected_status: int = 200,
    label: str,
) -> tuple[HttpExchange, dict[str, Any]]:
    exchange = transport.request(
        method=method,
        endpoint=endpoint,
        body=body,
        max_response_bytes=max_bytes,
    )
    _require(exchange.status == expected_status, "github_api_http_status", f"{label}:{exchange.status}", stage="network")
    value = _strict_json_object(exchange.body, label=label)
    return exchange, value


def _validate_main_ref(value: dict[str, Any], *, source_commit: str) -> None:
    _require(value.get("ref") == SOURCE_REF, "main_ref_name_mismatch", stage="dispatch")
    obj = value.get("object")
    _require(isinstance(obj, dict), "main_ref_object_missing", stage="dispatch")
    _require(obj.get("type") == "commit", "main_ref_not_commit", stage="dispatch")
    observed = str(obj.get("sha", "")).lower()
    _require(observed == source_commit, "main_head_mismatch", f"expected={source_commit} actual={observed}", stage="dispatch")


def _dispatch_response(
    value: dict[str, Any],
    *,
    role: str,
) -> dict[str, Any]:
    required = {"workflow_run_id", "run_url", "html_url"}
    if not required.issubset(value):
        raise AcquisitionError("dispatch_run_details_unavailable", role, stage="dispatch")
    run_id = _positive_int(value.get("workflow_run_id"), label=f"{role}_workflow_run_id")
    expected_api_url = f"{API_BASE_URL}/repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/{run_id}"
    expected_html_url = f"https://github.com/{OWNER}/{REPOSITORY_NAME}/actions/runs/{run_id}"
    run_url = value.get("run_url")
    html_url = value.get("html_url")
    _require(run_url == expected_api_url, "dispatch_receipt_mismatch", f"{role}:run_url", stage="dispatch")
    _require(html_url == expected_html_url, "dispatch_receipt_mismatch", f"{role}:html_url", stage="dispatch")
    return {
        "http_status": 200,
        "workflow_run_id": run_id,
        "run_url": run_url,
        "html_url": html_url,
    }


def _schema_validate_record(schema: dict[str, Any], record: dict[str, Any], *, label: str) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        errors = sorted(validator.iter_errors(record), key=lambda item: list(item.absolute_path))
    except Exception as exc:
        raise AcquisitionError("evidence_schema_validation_failed", f"{label}:{type(exc).__name__}", stage="schema") from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path)
        raise AcquisitionError(
            "evidence_record_schema_rejected",
            f"{label}:{location}:{first.validator}",
            stage="schema",
        )


def _dispatch(
    *,
    transport: GitHubTransport,
    staging: Path,
    schema: dict[str, Any],
    source_commit: str,
    record_status: str,
    role: str,
    request_document: dict[str, Any],
    endpoint: str,
    workflow_name: str,
    workflow_path: str,
    request_member: str,
    response_member: str,
    receipt_member: str,
    max_json_bytes: int,
    subject_workflow_run_id: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    request_bytes = _canonical_json_bytes(request_document)
    _write_new_file(staging, request_member, request_bytes)
    exchange = transport.request(
        method="POST",
        endpoint=endpoint,
        body=request_bytes,
        max_response_bytes=max_json_bytes,
    )
    if exchange.status != 200:
        if exchange.status == 204 or exchange.body == b"":
            raise AcquisitionError("dispatch_run_details_unavailable", role, stage="dispatch")
        raise AcquisitionError("dispatch_http_status", f"{role}:{exchange.status}", stage="dispatch")
    if exchange.body == b"":
        raise AcquisitionError("dispatch_run_details_unavailable", role, stage="dispatch")
    _write_new_file(staging, response_member, exchange.body)
    parsed = _strict_json_object(exchange.body, label=f"{role}_dispatch_response")
    response = _dispatch_response(parsed, role=role)
    requested = _parse_utc(exchange.requested_utc, label=f"{role}.requested_utc")
    received = _parse_utc(exchange.received_utc, label=f"{role}.received_utc")
    _require(received >= requested, "dispatch_time_order_invalid", role, stage="dispatch")

    receipt: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "record_type": "dispatch_receipt",
        "record_status": record_status,
        "receipt_role": "subject" if role == "subject" else "step3f_provider",
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "api_version": API_VERSION,
        "method": "POST",
        "accept": API_ACCEPT,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "endpoint": endpoint,
        "request": request_document,
        "response": response,
        "request_body_sha256": _sha256(request_bytes),
        "response_body_sha256": _sha256(exchange.body),
        "requested_utc": exchange.requested_utc,
        "received_utc": exchange.received_utc,
        "run_list_fallback_used": False,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [],
        "ok": True,
    }
    if role == "provider":
        _require(subject_workflow_run_id is not None, "provider_subject_run_id_missing", stage="dispatch")
        receipt["subject_workflow_run_id"] = subject_workflow_run_id
    _schema_validate_record(schema, receipt, label=f"{role}_dispatch_receipt")
    _write_new_file(staging, receipt_member, _canonical_json_bytes(receipt))
    return receipt, response


def _run_identity_checks(
    value: dict[str, Any],
    *,
    role: str,
    run_id: int,
    source_commit: str,
    workflow_name: str,
    workflow_path: str,
    expected_run_url: str,
    expected_html_url: str,
    require_terminal: bool,
) -> None:
    _require(value.get("id") == run_id, "cross_run_context", f"{role}:id", stage="run")
    _require(value.get("name") == workflow_name, "subject_context_mismatch" if role == "subject" else "provider_context_mismatch", f"{role}:name", stage="run")
    _require(value.get("path") == workflow_path, "subject_context_mismatch" if role == "subject" else "provider_context_mismatch", f"{role}:path", stage="run")
    _require(value.get("event") == "workflow_dispatch", "subject_context_mismatch" if role == "subject" else "provider_context_mismatch", f"{role}:event", stage="run")
    _require(value.get("head_branch") == "main", "subject_context_mismatch" if role == "subject" else "provider_context_mismatch", f"{role}:head_branch", stage="run")
    _require(str(value.get("head_sha", "")).lower() == source_commit, "subject_source_mismatch" if role == "subject" else "provider_source_mismatch", stage="run")
    _require(value.get("run_attempt") == 1, "subject_attempt_mismatch" if role == "subject" else "provider_attempt_mismatch", stage="run")
    _positive_int(value.get("run_number"), label=f"{role}_run_number")
    _require(value.get("url") == expected_run_url, "cross_run_context", f"{role}:url", stage="run")
    _require(value.get("html_url") == expected_html_url, "cross_run_context", f"{role}:html_url", stage="run")
    repository = value.get("repository")
    head_repository = value.get("head_repository")
    _require(isinstance(repository, dict) and repository.get("full_name") == REPOSITORY, "cross_run_context", f"{role}:repository", stage="run")
    _require(isinstance(head_repository, dict) and head_repository.get("full_name") == REPOSITORY, "cross_run_context", f"{role}:head_repository", stage="run")
    if require_terminal:
        _require(value.get("status") == "completed", "run_not_terminal", role, stage="run")
        _require(value.get("conclusion") == "success", "subject_not_successful" if role == "subject" else "provider_not_successful", stage="run")
        for field in ("created_at", "run_started_at", "updated_at"):
            _parse_utc(value.get(field), label=f"{role}.{field}")
        created = _parse_utc(value.get("created_at"), label=f"{role}.created_at")
        started = _parse_utc(value.get("run_started_at"), label=f"{role}.run_started_at")
        updated = _parse_utc(value.get("updated_at"), label=f"{role}.updated_at")
        _require(created <= started <= updated, "run_time_order_invalid", role, stage="run")


def _run_summary(
    value: dict[str, Any],
    *,
    workflow_name: str,
    workflow_path: str,
) -> dict[str, Any]:
    repository = value.get("repository")
    _require(isinstance(repository, dict), "run_repository_missing", stage="run")
    return {
        "repository": repository.get("full_name"),
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "event": value.get("event"),
        "head_branch": value.get("head_branch"),
        "head_sha": str(value.get("head_sha", "")).lower(),
        "run_id": value.get("id"),
        "run_number": value.get("run_number"),
        "run_attempt": value.get("run_attempt"),
        "status": value.get("status"),
        "conclusion": value.get("conclusion"),
        "run_url": value.get("url"),
        "html_url": value.get("html_url"),
        "created_at": value.get("created_at"),
        "run_started_at": value.get("run_started_at"),
        "updated_at": value.get("updated_at"),
    }


def _wait_for_run(
    *,
    transport: GitHubTransport,
    role: str,
    run_id: int,
    source_commit: str,
    workflow_name: str,
    workflow_path: str,
    expected_run_url: str,
    expected_html_url: str,
    wait_seconds: int,
    max_json_bytes: int,
    poll_interval_seconds: int,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> RunResult:
    _require(wait_seconds > 0, "run_wait_limit_invalid", role, stage="run")
    _require(1 <= poll_interval_seconds <= 60, "poll_interval_invalid", stage="run")
    deadline = monotonic() + wait_seconds
    endpoint = f"repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/{run_id}"
    allowed_nonterminal = {"queued", "in_progress", "waiting", "pending", "requested"}
    while True:
        exchange, value = _request_json(
            transport,
            method="GET",
            endpoint=endpoint,
            body=None,
            max_bytes=max_json_bytes,
            label=f"{role}_run_response",
        )
        _run_identity_checks(
            value,
            role=role,
            run_id=run_id,
            source_commit=source_commit,
            workflow_name=workflow_name,
            workflow_path=workflow_path,
            expected_run_url=expected_run_url,
            expected_html_url=expected_html_url,
            require_terminal=False,
        )
        status_value = value.get("status")
        if status_value == "completed":
            _run_identity_checks(
                value,
                role=role,
                run_id=run_id,
                source_commit=source_commit,
                workflow_name=workflow_name,
                workflow_path=workflow_path,
                expected_run_url=expected_run_url,
                expected_html_url=expected_html_url,
                require_terminal=True,
            )
            return RunResult(summary=_run_summary(value, workflow_name=workflow_name, workflow_path=workflow_path), raw_body=exchange.body)
        _require(status_value in allowed_nonterminal, "run_status_invalid", f"{role}:{status_value!r}", stage="run")
        remaining = deadline - monotonic()
        _require(remaining > 0, "subject_wait_timeout" if role == "subject" else "provider_wait_timeout", stage="run")
        sleep(min(float(poll_interval_seconds), remaining))


def _collect_pages(
    *,
    transport: GitHubTransport,
    staging: Path,
    role: str,
    endpoint_prefix: str,
    array_key: str,
    member_prefix: str,
    max_items: int,
    max_json_bytes: int,
    id_field: str,
) -> PageCollection:
    _require(max_items > 0, "pagination_limit_invalid", role, stage="pagination")
    rows: list[dict[str, Any]] = []
    members: list[str] = []
    seen_ids: set[int] = set()
    expected_total: int | None = None
    page = 1
    while True:
        endpoint = f"{endpoint_prefix}?per_page=100&page={page}"
        exchange, value = _request_json(
            transport,
            method="GET",
            endpoint=endpoint,
            body=None,
            max_bytes=max_json_bytes,
            label=f"{role}_{array_key}_page_{page}",
        )
        total = value.get("total_count")
        page_rows = value.get(array_key)
        _require(isinstance(total, int) and not isinstance(total, bool) and total >= 0, "pagination_total_invalid", role, stage="pagination")
        _require(isinstance(page_rows, list), "pagination_rows_invalid", role, stage="pagination")
        if expected_total is None:
            expected_total = total
            _require(expected_total <= max_items, "pagination_item_limit_exceeded", role, stage="pagination")
        else:
            _require(total == expected_total, "pagination_total_changed", role, stage="pagination")
        member = f"{member_prefix}-page-{page:04d}.json"
        _write_new_file(staging, member, exchange.body)
        members.append(member)

        for row in page_rows:
            _require(isinstance(row, dict), "pagination_row_not_object", role, stage="pagination")
            identifier = _positive_int(row.get(id_field), label=f"{role}_{array_key}_{id_field}")
            _require(identifier not in seen_ids, "pagination_duplicate_identifier", f"{role}:{identifier}", stage="pagination")
            seen_ids.add(identifier)
            rows.append(row)
        _require(len(rows) <= max_items, "pagination_item_limit_exceeded", role, stage="pagination")
        _require(len(rows) <= expected_total, "pagination_overrun", role, stage="pagination")
        if len(rows) == expected_total:
            break
        _require(page_rows != [], "pagination_not_closed", role, stage="pagination")
        page += 1
        _require(page <= (max_items // 100) + 2, "pagination_page_limit_exceeded", role, stage="pagination")
    return PageCollection(rows=rows, members=members, total_count=expected_total or 0)


def _validate_job_collection(
    collection: PageCollection,
    *,
    role: str,
    run_id: int,
    source_commit: str,
) -> None:
    expected_count = EXPECTED_SUBJECT_JOB_COUNT if role == "subject" else EXPECTED_PROVIDER_JOB_COUNT
    _require(collection.total_count == expected_count, "job_extent_mismatch", f"{role}:{collection.total_count}", stage="jobs")
    raw_steps = 0
    conclusions: list[str] = []
    for row in collection.rows:
        _require(row.get("run_id") == run_id, "cross_run_context", f"{role}:job_run_id", stage="jobs")
        _require(row.get("run_attempt") == 1, "subject_attempt_mismatch" if role == "subject" else "provider_attempt_mismatch", stage="jobs")
        _require(str(row.get("head_sha", "")).lower() == source_commit, "subject_source_mismatch" if role == "subject" else "provider_source_mismatch", stage="jobs")
        _require(row.get("status") == "completed", "job_not_terminal", role, stage="jobs")
        conclusion = row.get("conclusion")
        _require(conclusion in {"success", "skipped"}, "job_terminal_result_invalid", f"{role}:{conclusion!r}", stage="jobs")
        conclusions.append(str(conclusion))
        steps = row.get("steps")
        _require(isinstance(steps, list), "job_steps_missing", role, stage="jobs")
        raw_steps += len(steps)
    _require(raw_steps <= DEFAULT_MAX_PLATFORM_STEP_RECORDS, "platform_step_limit_exceeded", role, stage="jobs")
    if role == "subject":
        _require(conclusions.count("success") == EXPECTED_SUBJECT_SUCCESSFUL_JOBS, "job_extent_mismatch", "subject_success_count", stage="jobs")
        _require(conclusions.count("skipped") == EXPECTED_SUBJECT_SKIPPED_JOBS, "job_extent_mismatch", "subject_skipped_count", stage="jobs")
    else:
        _require(conclusions == ["success"] or conclusions.count("success") == 1, "provider_job_not_successful", stage="jobs")


def _artifact_metadata(
    row: dict[str, Any],
    *,
    expected_run_id: int,
    source_commit: str,
    max_single_bytes: int,
) -> dict[str, Any]:
    artifact_id = _positive_int(row.get("id"), label="artifact_id")
    name = row.get("name")
    _require(isinstance(name, str) and 0 < len(name) <= 256, "artifact_name_invalid", stage="artifact")
    size = _positive_int(row.get("size_in_bytes"), label="artifact_size")
    _require(size <= max_single_bytes, "artifact_size_limit_exceeded", name, stage="artifact")
    digest = row.get("digest")
    _require(isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None, "artifact_digest_invalid", name, stage="artifact")
    _require(row.get("expired") is False, "artifact_expired", name, stage="artifact")
    created = row.get("created_at")
    expires = row.get("expires_at")
    _parse_utc(created, label=f"artifact:{name}:created_at")
    _parse_utc(expires, label=f"artifact:{name}:expires_at")
    _require(_parse_utc(expires, label=f"artifact:{name}:expires_at") > _parse_utc(created, label=f"artifact:{name}:created_at"), "artifact_retention_window_invalid", name, stage="artifact")
    workflow_run = row.get("workflow_run")
    if workflow_run is not None:
        _require(isinstance(workflow_run, dict), "artifact_workflow_run_invalid", name, stage="artifact")
        _require(workflow_run.get("id") == expected_run_id, "artifact_binding_mismatch", f"{name}:run_id", stage="artifact")
        head_sha = workflow_run.get("head_sha")
        if head_sha is not None:
            _require(str(head_sha).lower() == source_commit, "artifact_binding_mismatch", f"{name}:head_sha", stage="artifact")
        head_branch = workflow_run.get("head_branch")
        if head_branch is not None:
            _require(head_branch == "main", "artifact_binding_mismatch", f"{name}:head_branch", stage="artifact")
    return {
        "id": artifact_id,
        "name": name,
        "size_bytes": size,
        "sha256": digest.removeprefix("sha256:"),
        "created_utc": created,
        "expires_utc": expires,
        "expired": False,
    }


def _select_artifact(
    rows: Sequence[dict[str, Any]],
    *,
    expected_name: str,
    expected_run_id: int,
    source_commit: str,
    max_single_bytes: int,
) -> dict[str, Any]:
    matches = [row for row in rows if row.get("name") == expected_name]
    _require(len(matches) == 1, "artifact_binding_mismatch", f"{expected_name}:matches={len(matches)}", stage="artifact")
    return _artifact_metadata(
        matches[0],
        expected_run_id=expected_run_id,
        source_commit=source_commit,
        max_single_bytes=max_single_bytes,
    )


def _download_selected_artifact(
    *,
    transport: GitHubTransport,
    staging: Path,
    selection_role: str,
    metadata: dict[str, Any],
    member: str,
    max_bytes: int,
) -> ArtifactSelection:
    relative = _canonical_member(member, label="artifact_member")
    destination = staging / relative
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _require(not destination.exists(), "output_member_already_exists", relative, stage="artifact")
    endpoint = f"repos/{OWNER}/{REPOSITORY_NAME}/actions/artifacts/{metadata['id']}/zip"
    result = transport.download_artifact(
        endpoint=endpoint,
        destination=destination,
        max_bytes=max_bytes,
    )
    _require(result.size_bytes == metadata["size_bytes"], "artifact_binding_mismatch", f"{metadata['name']}:size", stage="artifact")
    _require(result.sha256 == metadata["sha256"], "artifact_binding_mismatch", f"{metadata['name']}:sha256", stage="artifact")
    destination.chmod(0o444)
    return ArtifactSelection(
        role=selection_role,
        metadata=metadata,
        member=relative,
        downloaded_sha256=result.sha256,
        downloaded_size_bytes=result.size_bytes,
    )


def _file_inventory(root: Path, *, exclude: set[str]) -> list[dict[str, Any]]:
    members: list[str] = []
    for path in root.rglob("*"):
        _require(not path.is_symlink(), "acquisition_symlink_rejected", str(path), stage="publication")
        if path.is_dir():
            continue
        _require(path.is_file() and path.stat().st_nlink == 1, "acquisition_nonregular_file", str(path), stage="publication")
        relative = path.relative_to(root).as_posix()
        if relative not in exclude:
            members.append(relative)
    return [_descriptor(root, member) for member in sorted(members)]


def _artifact_index_row(selection: ArtifactSelection, *, source_run_kind: str, source_run_id: int) -> dict[str, Any]:
    return {
        "role": selection.role,
        "source_run_kind": source_run_kind,
        "artifact_id": selection.metadata["id"],
        "artifact_name": selection.metadata["name"],
        "source_run_id": source_run_id,
        "source_run_attempt": 1,
        "created_utc": selection.metadata["created_utc"],
        "expires_utc": selection.metadata["expires_utc"],
        "size_bytes": selection.metadata["size_bytes"],
        "github_sha256": selection.metadata["sha256"],
        "downloaded_member": selection.member,
        "downloaded_sha256": selection.downloaded_sha256,
        "downloaded_size_bytes": selection.downloaded_size_bytes,
    }


def _validate_aggregate_downloads(
    selections: Sequence[ArtifactSelection],
    *,
    maximum: int,
) -> None:
    total = sum(item.downloaded_size_bytes for item in selections)
    _require(total <= maximum, "aggregate_artifact_size_limit_exceeded", str(total), stage="artifact")


def acquire_observation(
    *,
    repository_root: Path,
    source_commit: str,
    plan_path: Path,
    plan_diagnostic_path: Path,
    expected_plan_sha256: str,
    output_directory: Path,
    record_status: str,
    reference_context: ReferenceContext,
    transport: GitHubTransport,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Acquire and atomically publish one complete raw Step 5C input set."""

    root = _validate_repository_root(repository_root)
    revision = _canonical_sha40(source_commit, label="source_commit")
    expected_digest = _canonical_sha256(expected_plan_sha256, label="expected_plan_sha256")
    _validate_reference_context(reference_context)
    _require(reference_context.source_commit == revision, "reference_source_mismatch", stage="context")
    _require(reference_context.record_status == record_status, "reference_record_status_mismatch", stage="context")
    _require(record_status in {"example", "observed"}, "record_status_invalid", stage="context")
    _require(poll_interval_seconds >= 1 and poll_interval_seconds <= 60, "poll_interval_invalid", stage="run")

    object_type = _git(root, ["cat-file", "-t", revision]).decode("ascii", errors="strict")
    _require(object_type == "commit\n", "source_commit_object_required", stage="source")
    head = _git(root, ["rev-parse", "HEAD"]).decode("ascii", errors="strict").strip().lower()
    _require(head == revision, "checked_out_head_mismatch", f"head={head} source={revision}", stage="source")

    plan_capture = _capture_regular_file(plan_path, label="prelaunch_plan", max_bytes=16 * 1024 * 1024)
    diagnostic_capture = _capture_regular_file(
        plan_diagnostic_path,
        label="prelaunch_plan_diagnostic",
        max_bytes=4 * 1024 * 1024,
    )
    plan, limits = _validate_plan_contract(
        plan_capture=plan_capture,
        diagnostic_capture=diagnostic_capture,
        expected_plan_sha256=expected_digest,
        source_commit=revision,
        record_status=record_status,
    )
    source_inventory = _source_inventory_map(plan)
    self_row = source_inventory.get(ACQUIRE_PATH)
    checker_row = source_inventory.get(PLAN_CHECKER_PATH)
    schema_row = source_inventory.get(SCHEMA_PATH)
    _require(isinstance(self_row, dict), "plan_acquisition_source_missing", stage="source")
    _require(isinstance(checker_row, dict), "plan_checker_source_missing", stage="source")
    _require(isinstance(schema_row, dict), "plan_schema_source_missing", stage="source")

    self_capture = _verify_installed_source(
        root=root,
        revision=revision,
        relative=ACQUIRE_PATH,
        expected_sha256=str(self_row.get("sha256")),
    )
    _verify_installed_source(
        root=root,
        revision=revision,
        relative=PLAN_CHECKER_PATH,
        expected_sha256=str(checker_row.get("sha256")),
    )
    schema_capture = _verify_installed_source(
        root=root,
        revision=revision,
        relative=SCHEMA_PATH,
        expected_sha256=str(schema_row.get("sha256")),
    )
    schema = _strict_json_object(schema_capture.data, label="step5c_evidence_schema")

    _rerun_plan_checker(
        root=root,
        source_commit=revision,
        plan_capture=plan_capture,
        diagnostic_capture=diagnostic_capture,
        expected_plan_sha256=expected_digest,
        record_status=record_status,
    )

    output, parent = _validate_output_destination(output_directory)
    staging = Path(tempfile.mkdtemp(prefix=".step5c-acquisition.", dir=parent))
    staging.chmod(0o700)
    published = False
    try:
        for directory in (CONTROL_DIRECTORY, SUBJECT_DIRECTORY, PROVIDER_DIRECTORY, "subject/artifacts"):
            (staging / directory).mkdir(parents=True, exist_ok=True, mode=0o700)

        expected_context = _expected_context_document(
            context=reference_context,
            expected_plan_sha256=expected_digest,
        )
        _write_new_file(
            staging,
            EXPECTED_CONTEXT_MEMBER,
            _canonical_json_bytes(expected_context),
        )

        subject_main_exchange, subject_main = _request_json(
            transport,
            method="GET",
            endpoint=MAIN_REF_ENDPOINT,
            body=None,
            max_bytes=limits.max_api_json_bytes,
            label="main_before_subject_dispatch",
        )
        _validate_main_ref(subject_main, source_commit=revision)
        _write_new_file(staging, SUBJECT_MAIN_REF_MEMBER, subject_main_exchange.body)

        subject_request = {
            "ref": DISPATCH_REF,
            "inputs": dict(SUBJECT_DISPATCH_INPUTS),
        }
        subject_receipt, subject_dispatch_response = _dispatch(
            transport=transport,
            staging=staging,
            schema=schema,
            source_commit=revision,
            record_status=record_status,
            role="subject",
            request_document=subject_request,
            endpoint=SUBJECT_DISPATCH_ENDPOINT,
            workflow_name=SUBJECT_WORKFLOW_NAME,
            workflow_path=SUBJECT_WORKFLOW_PATH,
            request_member=SUBJECT_DISPATCH_REQUEST_MEMBER,
            response_member=SUBJECT_DISPATCH_RESPONSE_MEMBER,
            receipt_member=SUBJECT_DISPATCH_RECEIPT_MEMBER,
            max_json_bytes=limits.max_api_json_bytes,
        )
        subject_run_id = int(subject_dispatch_response["workflow_run_id"])
        subject_run = _wait_for_run(
            transport=transport,
            role="subject",
            run_id=subject_run_id,
            source_commit=revision,
            workflow_name=SUBJECT_WORKFLOW_NAME,
            workflow_path=SUBJECT_WORKFLOW_PATH,
            expected_run_url=str(subject_dispatch_response["run_url"]),
            expected_html_url=str(subject_dispatch_response["html_url"]),
            wait_seconds=limits.subject_wait_seconds,
            max_json_bytes=limits.max_api_json_bytes,
            poll_interval_seconds=poll_interval_seconds,
            monotonic=monotonic,
            sleep=sleep,
        )
        _write_new_file(staging, SUBJECT_RUN_RESPONSE_MEMBER, subject_run.raw_body)

        subject_jobs = _collect_pages(
            transport=transport,
            staging=staging,
            role="subject",
            endpoint_prefix=(
                f"repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/"
                f"{subject_run_id}/attempts/1/jobs"
            ),
            array_key="jobs",
            member_prefix="subject/jobs",
            max_items=limits.max_jobs,
            max_json_bytes=limits.max_api_json_bytes,
            id_field="id",
        )
        _validate_job_collection(
            subject_jobs,
            role="subject",
            run_id=subject_run_id,
            source_commit=revision,
        )

        subject_artifacts = _collect_pages(
            transport=transport,
            staging=staging,
            role="subject",
            endpoint_prefix=(
                f"repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/"
                f"{subject_run_id}/artifacts"
            ),
            array_key="artifacts",
            member_prefix="subject/artifacts",
            max_items=limits.max_artifacts,
            max_json_bytes=limits.max_api_json_bytes,
            id_field="id",
        )

        downloads: list[ArtifactSelection] = []
        for role_name, name_template, member in SUBJECT_TERMINAL_ARTIFACT_TEMPLATES:
            metadata = _select_artifact(
                subject_artifacts.rows,
                expected_name=name_template.format(run_id=subject_run_id),
                expected_run_id=subject_run_id,
                source_commit=revision,
                max_single_bytes=limits.max_single_artifact_bytes,
            )
            downloads.append(
                _download_selected_artifact(
                    transport=transport,
                    staging=staging,
                    selection_role=role_name,
                    metadata=metadata,
                    member=member,
                    max_bytes=limits.max_single_artifact_bytes,
                )
            )
            _validate_aggregate_downloads(
                downloads,
                maximum=limits.max_aggregate_artifact_bytes,
            )

        provider_main_exchange, provider_main = _request_json(
            transport,
            method="GET",
            endpoint=MAIN_REF_ENDPOINT,
            body=None,
            max_bytes=limits.max_api_json_bytes,
            label="main_before_provider_dispatch",
        )
        _validate_main_ref(provider_main, source_commit=revision)
        _write_new_file(staging, PROVIDER_MAIN_REF_MEMBER, provider_main_exchange.body)

        provider_request = {
            "ref": DISPATCH_REF,
            "inputs": {"source_run_id": str(subject_run_id)},
        }
        provider_receipt, provider_dispatch_response = _dispatch(
            transport=transport,
            staging=staging,
            schema=schema,
            source_commit=revision,
            record_status=record_status,
            role="provider",
            request_document=provider_request,
            endpoint=PROVIDER_DISPATCH_ENDPOINT,
            workflow_name=PROVIDER_WORKFLOW_NAME,
            workflow_path=PROVIDER_WORKFLOW_PATH,
            request_member=PROVIDER_DISPATCH_REQUEST_MEMBER,
            response_member=PROVIDER_DISPATCH_RESPONSE_MEMBER,
            receipt_member=PROVIDER_DISPATCH_RECEIPT_MEMBER,
            max_json_bytes=limits.max_api_json_bytes,
            subject_workflow_run_id=subject_run_id,
        )
        provider_run_id = int(provider_dispatch_response["workflow_run_id"])
        _require(provider_run_id != subject_run_id, "provider_subject_run_id_collision", stage="dispatch")
        provider_run = _wait_for_run(
            transport=transport,
            role="provider",
            run_id=provider_run_id,
            source_commit=revision,
            workflow_name=PROVIDER_WORKFLOW_NAME,
            workflow_path=PROVIDER_WORKFLOW_PATH,
            expected_run_url=str(provider_dispatch_response["run_url"]),
            expected_html_url=str(provider_dispatch_response["html_url"]),
            wait_seconds=limits.provider_wait_seconds,
            max_json_bytes=limits.max_api_json_bytes,
            poll_interval_seconds=poll_interval_seconds,
            monotonic=monotonic,
            sleep=sleep,
        )
        _write_new_file(staging, PROVIDER_RUN_RESPONSE_MEMBER, provider_run.raw_body)

        provider_jobs = _collect_pages(
            transport=transport,
            staging=staging,
            role="provider",
            endpoint_prefix=(
                f"repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/"
                f"{provider_run_id}/attempts/1/jobs"
            ),
            array_key="jobs",
            member_prefix="provider/jobs",
            max_items=limits.max_jobs,
            max_json_bytes=limits.max_api_json_bytes,
            id_field="id",
        )
        _validate_job_collection(
            provider_jobs,
            role="provider",
            run_id=provider_run_id,
            source_commit=revision,
        )

        provider_artifacts = _collect_pages(
            transport=transport,
            staging=staging,
            role="provider",
            endpoint_prefix=(
                f"repos/{OWNER}/{REPOSITORY_NAME}/actions/runs/"
                f"{provider_run_id}/artifacts"
            ),
            array_key="artifacts",
            member_prefix="provider/artifacts",
            max_items=limits.max_artifacts,
            max_json_bytes=limits.max_api_json_bytes,
            id_field="id",
        )
        expected_provider_artifact_name = PROVIDER_ARTIFACT_TEMPLATE.format(
            subject_run_id=subject_run_id
        )
        provider_metadata = _select_artifact(
            provider_artifacts.rows,
            expected_name=expected_provider_artifact_name,
            expected_run_id=provider_run_id,
            source_commit=revision,
            max_single_bytes=limits.max_single_artifact_bytes,
        )
        provider_download = _download_selected_artifact(
            transport=transport,
            staging=staging,
            selection_role="step3f_candidate_envelope",
            metadata=provider_metadata,
            member=PROVIDER_ARTIFACT_MEMBER,
            max_bytes=limits.max_single_artifact_bytes,
        )
        downloads.append(provider_download)
        _validate_aggregate_downloads(
            downloads,
            maximum=limits.max_aggregate_artifact_bytes,
        )

        inventory_without_index = _file_inventory(
            staging,
            exclude={ACQUISITION_INDEX_MEMBER},
        )
        _require(
            len(inventory_without_index) <= limits.max_capture_members,
            "acquisition_member_limit_exceeded",
            stage="publication",
        )
        total_uncompressed = sum(row["size_bytes"] for row in inventory_without_index)
        _require(
            total_uncompressed <= limits.max_capture_uncompressed_bytes,
            "acquisition_byte_limit_exceeded",
            stage="publication",
        )

        index = {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "record_status": record_status,
            "tool": {
                "tool_id": TOOL_ID,
                "version": TOOL_VERSION,
                "source_path": ACQUIRE_PATH,
                "source_revision": revision,
                "source_sha256": self_capture.sha256,
            },
            "repository": REPOSITORY,
            "source_commit": revision,
            "source_ref": SOURCE_REF,
            "profile": PROFILE,
            "scope": SCOPE,
            "acquisition_id": reference_context.acquisition_id,
            "plan_binding": {
                "plan_sha256": plan_capture.sha256,
                "plan_size_bytes": plan_capture.size_bytes,
                "plan_diagnostic_sha256": diagnostic_capture.sha256,
                "plan_diagnostic_size_bytes": diagnostic_capture.size_bytes,
                "expected_plan_sha256": expected_digest,
                "independent_plan_diagnostic_reproduced": True,
            },
            "reference_context": expected_context,
            "subject_dispatch_receipt": _descriptor(staging, SUBJECT_DISPATCH_RECEIPT_MEMBER),
            "provider_dispatch_receipt": _descriptor(staging, PROVIDER_DISPATCH_RECEIPT_MEMBER),
            "subject": subject_run.summary,
            "provider": provider_run.summary,
            "subject_jobs": {
                "total_count": subject_jobs.total_count,
                "page_members": sorted(subject_jobs.members),
            },
            "subject_artifacts": {
                "total_count": subject_artifacts.total_count,
                "page_members": sorted(subject_artifacts.members),
            },
            "provider_jobs": {
                "total_count": provider_jobs.total_count,
                "page_members": sorted(provider_jobs.members),
            },
            "provider_artifacts": {
                "total_count": provider_artifacts.total_count,
                "page_members": sorted(provider_artifacts.members),
            },
            "downloaded_artifacts": sorted(
                [
                    _artifact_index_row(
                        selection,
                        source_run_kind=(
                            "provider"
                            if selection.role == "step3f_candidate_envelope"
                            else "subject"
                        ),
                        source_run_id=(
                            provider_run_id
                            if selection.role == "step3f_candidate_envelope"
                            else subject_run_id
                        ),
                    )
                    for selection in downloads
                ],
                key=lambda row: (row["source_run_kind"], row["artifact_name"]),
            ),
            "collection_boundary": {
                "collection_mode": "post_run_platform_export",
                "pagination_closed": True,
                "latest_run_lookup_used": False,
                "run_list_correlation_used": False,
                "subject_attempt": 1,
                "provider_attempt": 1,
                "observer_in_subject_totals": False,
                "subject_artifacts_mutated": False,
            },
            "member_inventory": {
                "manifest_scope": "all_acquisition_files_except_this_index",
                "member_count": len(inventory_without_index),
                "total_size_bytes": total_uncompressed,
                "members": inventory_without_index,
            },
            "privacy_boundary": dict(PRIVACY_BOUNDARY),
            "trust_boundary": {
                "trusted_components": list(TRUST_BOUNDARY["trusted_components"]),
                "not_proven": list(TRUST_BOUNDARY["not_proven"]),
            },
            "authority_boundary": dict(AUTHORITY_BOUNDARY),
            "errors": [],
            "ok": True,
        }
        _write_new_file(staging, ACQUISITION_INDEX_MEMBER, _canonical_json_bytes(index))

        complete_inventory = _file_inventory(staging, exclude=set())
        _require(
            len(complete_inventory) == len(inventory_without_index) + 1,
            "acquisition_inventory_closure_failed",
            stage="publication",
        )
        _set_tree_read_only(staging)
        _rename_noreplace(staging, output)
        published = True

        return {
            "tool": TOOL_ID,
            "version": TOOL_VERSION,
            "record_status": record_status,
            "ok": True,
            "output_directory": str(output),
            "acquisition_id": reference_context.acquisition_id,
            "subject_run_id": subject_run_id,
            "subject_run_number": subject_run.summary["run_number"],
            "subject_run_attempt": 1,
            "provider_run_id": provider_run_id,
            "provider_run_number": provider_run.summary["run_number"],
            "provider_run_attempt": 1,
            "provider_artifact_id": provider_metadata["id"],
            "provider_artifact_name": provider_metadata["name"],
            "downloaded_artifact_count": len(downloads),
            "authority_boundary": dict(AUTHORITY_BOUNDARY),
            "errors": [],
        }
    finally:
        if not published and staging.exists():
            try:
                for path in staging.rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        path.chmod(0o600)
                    elif path.is_dir() and not path.is_symlink():
                        path.chmod(0o700)
                staging.chmod(0o700)
                shutil.rmtree(staging)
            except OSError:
                pass


def _failure_diagnostic(error: AcquisitionError, *, exit_code: int) -> dict[str, Any]:
    return {
        "tool": TOOL_ID,
        "version": TOOL_VERSION,
        "record_status": "rejected",
        "ok": False,
        "stage": error.stage,
        "error_code": error.code,
        "detail": error.detail,
        "authority_effect": "none",
        "same_run_release_authority_eligible": False,
        "active_gate_eligible": False,
        "errors": [error.code],
        "exit_code": exit_code,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dispatch and acquire one exact Step 5C hosted release-grade "
            "PULSE CI subject and its exact Step 3F provider handoff."
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Exact repository root; checked-out HEAD must equal --source-commit.",
    )
    parser.add_argument(
        "--source-commit",
        required=True,
        help="Owner-reviewed lowercase 40-hex source commit.",
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Canonical independently validated Step 5C prelaunch plan.",
    )
    parser.add_argument(
        "--plan-diagnostic",
        required=True,
        help="Canonical success diagnostic emitted by the independent plan checker.",
    )
    parser.add_argument(
        "--expected-plan-sha256",
        required=True,
        help="Externally supplied SHA-256 of the exact plan bytes.",
    )
    parser.add_argument(
        "--output-directory",
        required=True,
        help="Absent destination for the complete raw acquisition directory.",
    )
    parser.add_argument(
        "--record-status",
        choices=("observed",),
        default="observed",
        help="Live CLI acquisitions are always observed records.",
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable containing the GitHub token; never persisted.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Bounded direct-run polling interval, from 1 through 60 seconds.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        source_commit = _canonical_sha40(str(args.source_commit), label="source_commit")
        context = _reference_context_from_environment(
            source_commit=source_commit,
            record_status=str(args.record_status),
            environment=os.environ,
        )
        token = _sanitize_environment(str(args.token_env))
        transport = LiveGitHubTransport(
            token=token,
            timeout_seconds=DEFAULT_API_REQUEST_TIMEOUT_SECONDS,
        )
        result = acquire_observation(
            repository_root=Path(args.repository_root),
            source_commit=source_commit,
            plan_path=Path(args.plan),
            plan_diagnostic_path=Path(args.plan_diagnostic),
            expected_plan_sha256=str(args.expected_plan_sha256),
            output_directory=Path(args.output_directory),
            record_status=str(args.record_status),
            reference_context=context,
            transport=transport,
            poll_interval_seconds=int(args.poll_interval_seconds),
        )
        sys.stdout.buffer.write(_canonical_json_bytes(result))
        return 0
    except AcquisitionError as exc:
        sys.stderr.buffer.write(
            _canonical_json_bytes(_failure_diagnostic(exc, exit_code=1))
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - fail closed without ambient values
        wrapped = AcquisitionError(
            "unexpected_acquisition_failure",
            type(exc).__name__,
            stage="unexpected",
        )
        sys.stderr.buffer.write(
            _canonical_json_bytes(_failure_diagnostic(wrapped, exit_code=2))
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
