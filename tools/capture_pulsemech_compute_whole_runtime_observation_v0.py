#!/usr/bin/env python3
"""Build one deterministic Step 5C whole-runtime observation capture carrier.

The tool consumes an independently checked prelaunch plan and one completed raw
acquisition directory produced by
``acquire_pulsemech_compute_whole_runtime_observation_v0.py``.  It rechecks the
closed acquisition inventory, dispatch receipts, run/job/step topology, selected
artifact bindings, the exact Step 3F candidate envelope, and the transitive
current-run carrier bindings.  It then writes one deterministic ``ZIP_STORED``
capture whose self-closing ``capture.json`` manifest is valid against the Step 5C
evidence schema.

The capture contains preserved inputs only.  It does not construct the generic
runtime-observation packet, invoke the compute analyzer or relation engine,
materialize a gate, modify status, create a release decision, or change release
authority.

Production CLI usage on Linux::

    python -I tools/capture_pulsemech_compute_whole_runtime_observation_v0.py \
      --repository-root . \
      --source-commit <40-hex commit> \
      --plan <prelaunch-plan.json> \
      --plan-diagnostic <prelaunch-plan-diagnostic.json> \
      --expected-plan-sha256 <64-hex digest> \
      --acquisition-directory <completed acquisition directory> \
      --output <absent capture.zip> \
      --record-status observed

The output path must be absent.  No existing pathname is replaced or deleted.
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
        '"tool":"capture_pulsemech_compute_whole_runtime_observation_v0"}\n'
    )
    raise SystemExit(2)

import argparse
import ctypes
import errno
import hashlib
import io
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable, Mapping, Sequence

import jsonschema


TOOL_ID = "capture_pulsemech_compute_whole_runtime_observation_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_whole_runtime_observation_evidence_v0"
RECORD_TYPE = "capture_manifest"
ACQUISITION_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_acquisition_v0"
)
EXPECTED_CONTEXT_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_expected_context_v0"
)
PLAN_DIAGNOSTIC_VERSION = (
    "pulsemech_compute_whole_runtime_observation_plan_check_v0"
)
PROFILE = "pulse_ci_hosted_release_grade_v0"
SCOPE = "one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
SOURCE_REF = "refs/heads/main"

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

CAPTURE_PATH = "tools/capture_pulsemech_compute_whole_runtime_observation_v0.py"
ACQUIRE_PATH = "tools/acquire_pulsemech_compute_whole_runtime_observation_v0.py"
PLAN_CHECKER_PATH = (
    "tools/check_pulsemech_compute_whole_runtime_observation_plan_v0.py"
)
SCHEMA_PATH = (
    "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"
)

CAPTURE_MANIFEST_MEMBER = "capture.json"
PREPARED_PLAN_MEMBER = "prepared/prelaunch-plan.json"
PREPARED_PLAN_DIAGNOSTIC_MEMBER = "prepared/prelaunch-plan-diagnostic.json"
PREPARED_EXPECTED_PLAN_MEMBER = "prepared/expected-plan.sha256"
ACQUISITION_PREFIX = "acquisition/"
ACQUISITION_INDEX_MEMBER = "acquisition-index.json"
EXPECTED_CONTEXT_MEMBER = "expected_context.json"
SUBJECT_DISPATCH_REQUEST_MEMBER = "subject/dispatch-request.json"
SUBJECT_DISPATCH_RESPONSE_MEMBER = "subject/dispatch-response.json"
SUBJECT_DISPATCH_RECEIPT_MEMBER = "subject/dispatch-receipt.json"
SUBJECT_RUN_RESPONSE_MEMBER = "subject/run-response.json"
PROVIDER_DISPATCH_REQUEST_MEMBER = "provider/dispatch-request.json"
PROVIDER_DISPATCH_RESPONSE_MEMBER = "provider/dispatch-response.json"
PROVIDER_DISPATCH_RECEIPT_MEMBER = "provider/dispatch-receipt.json"
PROVIDER_RUN_RESPONSE_MEMBER = "provider/run-response.json"
PROVIDER_ENVELOPE_MEMBER = "provider/step3f-candidate-envelope.zip"

EXPECTED_JOB_COUNT = 8
EXPECTED_SUCCESSFUL_JOB_COUNT = 7
EXPECTED_SKIPPED_JOB_COUNT = 1
EXPECTED_STEP_TEMPLATE_COUNT = 147
EXPECTED_INSTANTIATED_STEP_COUNT = 145
EXPECTED_SUCCESSFUL_STEP_COUNT = 101
EXPECTED_SKIPPED_STEP_COUNT = 44
EXPECTED_UNINSTANTIATED_STEP_COUNT = 2
EXPECTED_SUBJECT_EXECUTION_COUNT = 153
EXPECTED_COLLECTOR_EXECUTION_COUNT = 1
EXPECTED_TOTAL_RUNTIME_EXECUTION_COUNT = 154
EXPECTED_MODEL_INFERENCE_COUNT = 6
EXPECTED_RESOURCE_MEASUREMENT_COUNT = 0

MAX_PLAN_BYTES = 16 * 1024 * 1024
MAX_PLAN_DIAGNOSTIC_BYTES = 4 * 1024 * 1024
MAX_SCHEMA_BYTES = 4 * 1024 * 1024
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_CANDIDATE_FILES = 16
MAX_CANDIDATE_FILE_BYTES = 805_306_368
MAX_CARRIER_MEMBERS = 4096
MAX_CARRIER_MEMBER_BYTES = 805_306_368
MAX_CAPTURE_MEMBERS = 8192
MAX_CAPTURE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_MODE = 0o100444

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?Z$"
)
MEMBER_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*\\)(?!.*\x00)"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$"
)
CAPTURE_ID_RE = re.compile(r"^step5c-capture:[A-Za-z0-9._:-]+$")
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

CAPTURE_CONTENT_BOUNDARY: dict[str, bool] = {
    "raw_dispatch_responses_included": True,
    "raw_run_responses_included": True,
    "raw_job_responses_included": True,
    "raw_artifact_responses_included": True,
    "opaque_provider_envelope_included": True,
    "verifier_verdict_included": False,
    "runtime_packet_included": False,
    "derived_outputs_included": False,
}

EXPECTED_ACQUISITION_COLLECTION_BOUNDARY: dict[str, Any] = {
    "collection_mode": "post_run_platform_export",
    "pagination_closed": True,
    "latest_run_lookup_used": False,
    "run_list_correlation_used": False,
    "subject_attempt": 1,
    "provider_attempt": 1,
    "observer_in_subject_totals": False,
    "subject_artifacts_mutated": False,
}

EXPECTED_CANDIDATE_AUTHORITY_BOUNDARY: dict[str, Any] = {
    "activates_compute_gate": False,
    "candidate_only": True,
    "changes_gate_policy": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "non_active": True,
    "produces_runtime_observation": False,
    "produces_transition_relation": False,
}

EXPECTED_LIFECYCLE_NAMES = {
    "Set up job",
    "Complete job",
    "Post Checkout",
    "Post Set up Python",
}

SUBJECT_DOWNLOAD_ROLES = {
    "complete_release_grade_reference_package": (
        "complete_release_grade_reference_package",
        "complete_package_name",
    ),
    "package_completeness_report": (
        "package_completeness_report",
        "completeness_archive_name",
    ),
    "package_verification_report": (
        "package_verification_report",
        "verification_archive_name",
    ),
}


class CaptureError(RuntimeError):
    """Stable fail-closed capture error."""

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        stage: str = "capture",
    ) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.stage = stage


class StrictJsonError(CaptureError):
    pass


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    relative: str
    size_bytes: int
    sha256: str
    identity: tuple[int, ...]


@dataclass(frozen=True)
class CaptureMember:
    member: str
    snapshot: FileSnapshot | None
    literal: bytes | None
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ZipEntryBinding:
    name: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ProviderEnvelopeBinding:
    carrier_member_bindings: list[dict[str, Any]]
    candidate_prefix: str
    carrier_candidate_member: str
    carrier_sha256: str
    carrier_size_bytes: int


def _require(
    condition: bool,
    code: str,
    detail: str | None = None,
    *,
    stage: str = "capture",
) -> None:
    if not condition:
        raise CaptureError(code, detail, stage=stage)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha40(value: Any, *, label: str) -> str:
    text = str(value).strip().lower()
    _require(SHA40_RE.fullmatch(text) is not None, f"{label}_not_sha40", stage="identity")
    return text


def _canonical_sha256(value: Any, *, label: str) -> str:
    text = str(value).strip().lower()
    _require(
        SHA256_RE.fullmatch(text) is not None,
        f"{label}_not_sha256",
        stage="identity",
    )
    return text


def _positive_int(value: Any, *, label: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        f"{label}_not_positive_integer",
        stage="identity",
    )
    return int(value)


def _require_canonical_tree(value: Any, *, label: str = "json") -> None:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        raise StrictJsonError("fractional_json_number_rejected", label, stage="json")
    if isinstance(value, str):
        _require(
            unicodedata.normalize("NFC", value) == value,
            "non_nfc_json_string",
            label,
            stage="json",
        )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_canonical_tree(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), "json_key_not_string", label, stage="json")
            _require_canonical_tree(key, label=f"{label}.key")
            _require_canonical_tree(item, label=f"{label}.{key}")
        return
    raise StrictJsonError("unsupported_json_value", label, stage="json")


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


def _json_object(
    data: bytes,
    *,
    label: str,
    canonical: bool = False,
) -> dict[str, Any]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "utf8_bom_rejected", label, stage="json")
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
            parse_float=_reject_fractional,
        )
    except CaptureError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise StrictJsonError("invalid_json", label, stage="json") from exc
    _require(isinstance(value, dict), "json_object_required", label, stage="json")
    _require_canonical_tree(value, label=label)
    if canonical:
        _require(
            _canonical_json_bytes(value) == data,
            "noncanonical_json",
            label,
            stage="json",
        )
    return value


def _parse_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and UTC_RE.fullmatch(value) is not None, "invalid_utc", label, stage="time")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CaptureError("invalid_utc", label, stage="time") from exc
    _require(parsed.tzinfo is not None, "utc_timezone_missing", label, stage="time")
    return parsed.astimezone(timezone.utc)


def _safe_member(value: Any, *, label: str) -> str:
    _require(isinstance(value, str), "member_name_not_string", label, stage="path")
    _require(MEMBER_RE.fullmatch(value) is not None, "unsafe_member_name", value, stage="path")
    _require(len(value) <= 300, "member_name_too_long", value, stage="path")
    return value


def _normalized_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path, *, label: str) -> None:
    absolute = _normalized_absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise CaptureError("path_component_unavailable", f"{label}:{current}", stage="path") from exc
        _require(not stat.S_ISLNK(metadata.st_mode), "symlink_path_component_rejected", f"{label}:{current}", stage="path")


def _snapshot_file(
    path: Path,
    *,
    relative: str,
    maximum: int,
    require_read_only: bool,
) -> FileSnapshot:
    candidate = _normalized_absolute(path)
    _reject_symlink_components(candidate, label=relative)
    try:
        before = candidate.stat(follow_symlinks=False)
    except OSError as exc:
        raise CaptureError("input_file_unavailable", relative, stage="input") from exc
    _require(stat.S_ISREG(before.st_mode), "input_not_regular_file", relative, stage="input")
    _require(before.st_nlink == 1, "input_link_count_invalid", relative, stage="input")
    _require(0 <= before.st_size <= maximum, "input_size_out_of_range", relative, stage="input")
    if require_read_only:
        _require(
            before.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) == 0,
            "input_not_finalized_read_only",
            relative,
            stage="input",
        )
    digest = hashlib.sha256()
    read_total = 0
    try:
        with candidate.open("rb", buffering=0) as stream:
            while True:
                chunk = stream.read(HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
                read_total += len(chunk)
    except OSError as exc:
        raise CaptureError("input_read_failed", relative, stage="input") from exc
    after = candidate.stat(follow_symlinks=False)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    _require(identity_after == identity_before, "input_changed_during_hash", relative, stage="input")
    _require(read_total == before.st_size, "input_short_read", relative, stage="input")
    return FileSnapshot(
        path=candidate,
        relative=relative,
        size_bytes=before.st_size,
        sha256=digest.hexdigest(),
        identity=identity_before,
    )


def _verify_snapshot_unchanged(snapshot: FileSnapshot) -> None:
    metadata = snapshot.path.stat(follow_symlinks=False)
    identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
    _require(identity == snapshot.identity, "input_changed_after_capture", snapshot.relative, stage="input")


def _descriptor(member: str, sha256: str, size_bytes: int) -> dict[str, Any]:
    return {
        "member": _safe_member(member, label="descriptor.member"),
        "sha256": _canonical_sha256(sha256, label="descriptor.sha256"),
        "size_bytes": int(size_bytes),
    }


def _snapshot_descriptor(snapshot: FileSnapshot, *, member: str) -> dict[str, Any]:
    return _descriptor(member, snapshot.sha256, snapshot.size_bytes)


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


def _git(root: Path, arguments: Sequence[str], *, timeout: int = 30) -> bytes:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "--no-replace-objects", "-C", str(root), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=_git_environment(root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("git_execution_failed", type(exc).__name__, stage="source") from exc
    _require(result.returncode == 0, "git_command_failed", " ".join(arguments), stage="source")
    _require(len(result.stdout) <= 16 * 1024 * 1024, "git_output_too_large", stage="source")
    return result.stdout


def _validate_repository_root(path: Path) -> Path:
    root = _normalized_absolute(path)
    _reject_symlink_components(root, label="repository_root")
    _require(root.is_dir(), "repository_root_not_directory", str(root), stage="source")
    return root


def _git_blob(root: Path, revision: str, relative: str) -> tuple[str, bytes]:
    _safe_member(relative, label="source_path")
    listing = _git(root, ["ls-tree", "-z", revision, "--", relative])
    _require(listing.endswith(b"\0") and listing.count(b"\0") == 1, "source_tree_entry_missing_or_ambiguous", relative, stage="source")
    try:
        metadata, encoded_path = listing[:-1].split(b"\t", 1)
        mode, kind, blob_sha = metadata.decode("ascii").split(" ")
        path = encoded_path.decode("utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise CaptureError("source_tree_entry_malformed", relative, stage="source") from exc
    _require(path == relative, "source_tree_path_mismatch", relative, stage="source")
    _require(kind == "blob" and mode in {"100644", "100755"}, "source_not_regular_blob", relative, stage="source")
    _require(SHA40_RE.fullmatch(blob_sha) is not None, "source_blob_sha_invalid", relative, stage="source")
    data = _git(root, ["cat-file", "blob", blob_sha], timeout=60)
    return blob_sha, data


def _source_inventory(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = plan.get("source_inventory")
    _require(isinstance(rows, list), "plan_source_inventory_missing", stage="plan")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "plan_source_inventory_row_invalid", stage="plan")
        path = row.get("path")
        _require(isinstance(path, str) and path not in result, "plan_source_inventory_duplicate", str(path), stage="plan")
        result[path] = row
    return result


def _verify_installed_source(
    *,
    root: Path,
    revision: str,
    relative: str,
    expected_row: Mapping[str, Any],
    maximum: int,
) -> FileSnapshot:
    blob_sha, git_bytes = _git_blob(root, revision, relative)
    expected_sha = _canonical_sha256(expected_row.get("sha256"), label=f"{relative}.plan_sha256")
    _require(expected_row.get("revision") == revision, "plan_source_revision_mismatch", relative, stage="source")
    _require(expected_row.get("git_blob_sha1") == blob_sha, "plan_source_blob_mismatch", relative, stage="source")
    _require(expected_row.get("size_bytes") == len(git_bytes), "plan_source_size_mismatch", relative, stage="source")
    _require(_sha256(git_bytes) == expected_sha, "plan_source_digest_mismatch", relative, stage="source")
    snapshot = _snapshot_file(
        root / relative,
        relative=relative,
        maximum=maximum,
        require_read_only=False,
    )
    _require(snapshot.sha256 == expected_sha and snapshot.size_bytes == len(git_bytes), "installed_source_mismatch", relative, stage="source")
    try:
        installed_bytes = snapshot.path.read_bytes()
    except OSError as exc:
        raise CaptureError("installed_source_read_failed", relative, stage="source") from exc
    _require(installed_bytes == git_bytes, "installed_source_bytes_mismatch", relative, stage="source")
    return snapshot


def _schema_validate(schema: dict[str, Any], record: dict[str, Any], *, label: str) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(record),
            key=lambda item: [str(part) for part in item.absolute_path],
        )
    except Exception as exc:
        raise CaptureError("evidence_schema_validation_failed", f"{label}:{type(exc).__name__}", stage="schema") from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CaptureError(
            "evidence_record_schema_rejected",
            f"{label}:{location}:{first.validator}",
            stage="schema",
        )


def _plan_contract(
    *,
    plan_snapshot: FileSnapshot,
    diagnostic_snapshot: FileSnapshot,
    expected_plan_sha256: str,
    source_commit: str,
    record_status: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    _require(plan_snapshot.sha256 == expected_plan_sha256, "plan_digest_mismatch", stage="plan")
    plan = _json_object(plan_snapshot.path.read_bytes(), label="prelaunch_plan", canonical=True)
    _schema_validate(schema, plan, label="prelaunch_plan")
    _require(plan.get("record_type") == "prelaunch_plan", "plan_record_type_mismatch", stage="plan")
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
    _require(plan.get("trust_boundary") == TRUST_BOUNDARY, "plan_trust_boundary_mismatch", stage="plan")
    terminal = plan.get("terminal_counts")
    _require(
        terminal
        == {
            "job_templates": EXPECTED_JOB_COUNT,
            "successful_jobs": EXPECTED_SUCCESSFUL_JOB_COUNT,
            "permitted_skipped_jobs": EXPECTED_SKIPPED_JOB_COUNT,
            "step_templates": EXPECTED_STEP_TEMPLATE_COUNT,
            "instantiated_steps": EXPECTED_INSTANTIATED_STEP_COUNT,
            "successful_steps": EXPECTED_SUCCESSFUL_STEP_COUNT,
            "permitted_skipped_steps": EXPECTED_SKIPPED_STEP_COUNT,
            "uninstantiated_steps": EXPECTED_UNINSTANTIATED_STEP_COUNT,
            "model_inference_occurrences": EXPECTED_MODEL_INFERENCE_COUNT,
        },
        "plan_terminal_counts_mismatch",
        stage="plan",
    )
    diagnostic = _json_object(
        diagnostic_snapshot.path.read_bytes(),
        label="prelaunch_plan_diagnostic",
        canonical=True,
    )
    _require(diagnostic.get("schema_version") == PLAN_DIAGNOSTIC_VERSION, "plan_diagnostic_version_mismatch", stage="plan")
    _require(diagnostic.get("ok") is True and diagnostic.get("record_status") == "verified", "plan_diagnostic_not_verified", stage="plan")
    diag_plan = diagnostic.get("plan")
    _require(isinstance(diag_plan, dict), "plan_diagnostic_plan_missing", stage="plan")
    _require(diag_plan.get("sha256") == expected_plan_sha256, "plan_diagnostic_digest_mismatch", stage="plan")
    _require(diag_plan.get("source_commit") == source_commit, "plan_diagnostic_source_mismatch", stage="plan")
    _require(diag_plan.get("record_status") == record_status, "plan_diagnostic_record_status_mismatch", stage="plan")
    _require(diag_plan.get("byte_identical_to_independent_reconstruction") is True, "plan_diagnostic_reconstruction_missing", stage="plan")
    _require(diagnostic.get("authority_boundary") == AUTHORITY_BOUNDARY, "plan_diagnostic_authority_boundary_mismatch", stage="plan")
    return plan


def _walk_acquisition(
    directory: Path,
    *,
    max_members: int,
    max_total_bytes: int,
) -> dict[str, FileSnapshot]:
    root = _normalized_absolute(directory)
    _reject_symlink_components(root, label="acquisition_directory")
    _require(root.is_dir(), "acquisition_directory_not_directory", str(root), stage="acquisition")
    files: dict[str, FileSnapshot] = {}
    total = 0
    try:
        paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
    except OSError as exc:
        raise CaptureError("acquisition_walk_failed", str(root), stage="acquisition") from exc
    for path in paths:
        metadata = path.lstat()
        _require(not stat.S_ISLNK(metadata.st_mode), "acquisition_symlink_rejected", str(path), stage="acquisition")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        _require(stat.S_ISREG(metadata.st_mode), "acquisition_nonregular_member", str(path), stage="acquisition")
        relative = _safe_member(path.relative_to(root).as_posix(), label="acquisition.member")
        _require(relative not in files, "acquisition_duplicate_member", relative, stage="acquisition")
        snapshot = _snapshot_file(
            path,
            relative=relative,
            maximum=max_total_bytes,
            require_read_only=True,
        )
        files[relative] = snapshot
        total += snapshot.size_bytes
        _require(len(files) <= max_members, "acquisition_member_limit_exceeded", stage="acquisition")
        _require(total <= max_total_bytes, "acquisition_byte_limit_exceeded", stage="acquisition")
    _require(ACQUISITION_INDEX_MEMBER in files, "acquisition_index_missing", stage="acquisition")
    return files


def _descriptor_map(rows: Any, *, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(rows, list), f"{label}_not_array", stage="acquisition")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), f"{label}_row_not_object", stage="acquisition")
        member = _safe_member(row.get("member"), label=f"{label}.member")
        _require(member not in result, f"{label}_duplicate_member", member, stage="acquisition")
        _canonical_sha256(row.get("sha256"), label=f"{label}.sha256")
        _require(isinstance(row.get("size_bytes"), int) and not isinstance(row.get("size_bytes"), bool) and row["size_bytes"] >= 0, f"{label}_size_invalid", member, stage="acquisition")
        result[member] = row
    return result


def _validate_member_inventory(
    *,
    acquisition_files: Mapping[str, FileSnapshot],
    index: dict[str, Any],
) -> None:
    inventory = index.get("member_inventory")
    _require(isinstance(inventory, dict), "acquisition_member_inventory_missing", stage="acquisition")
    _require(inventory.get("manifest_scope") == "all_acquisition_files_except_this_index", "acquisition_manifest_scope_mismatch", stage="acquisition")
    declared = _descriptor_map(inventory.get("members"), label="acquisition_member_inventory")
    actual_names = set(acquisition_files) - {ACQUISITION_INDEX_MEMBER}
    _require(set(declared) == actual_names, "acquisition_inventory_mismatch", stage="acquisition")
    _require(inventory.get("member_count") == len(actual_names), "acquisition_member_count_mismatch", stage="acquisition")
    expected_total = sum(acquisition_files[name].size_bytes for name in actual_names)
    _require(inventory.get("total_size_bytes") == expected_total, "acquisition_total_size_mismatch", stage="acquisition")
    for member, row in declared.items():
        snapshot = acquisition_files[member]
        _require(row.get("sha256") == snapshot.sha256, "acquisition_member_digest_mismatch", member, stage="acquisition")
        _require(row.get("size_bytes") == snapshot.size_bytes, "acquisition_member_size_mismatch", member, stage="acquisition")


def _expected_context(
    *,
    snapshot: FileSnapshot,
    source_commit: str,
    expected_plan_sha256: str,
    record_status: str,
) -> dict[str, Any]:
    context = _json_object(snapshot.path.read_bytes(), label="expected_context", canonical=True)
    expected_fixed = {
        "schema_version": EXPECTED_CONTEXT_SCHEMA_VERSION,
        "record_status": record_status,
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "source_ref": SOURCE_REF,
        "reference_workflow_name": REFERENCE_WORKFLOW_NAME,
        "reference_workflow_path": REFERENCE_WORKFLOW_PATH,
        "reference_event_name": "workflow_dispatch",
        "reference_run_attempt": 1,
        "collector_execution_id": "execution:step5c:collector:post-run-platform-export",
        "expected_plan_sha256": expected_plan_sha256,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
        "ok": True,
    }
    for key, expected in expected_fixed.items():
        _require(context.get(key) == expected, "expected_context_mismatch", key, stage="context")
    _positive_int(context.get("reference_run_id"), label="reference_run_id")
    _positive_int(context.get("reference_run_number"), label="reference_run_number")
    acquisition_id = context.get("acquisition_id")
    _require(isinstance(acquisition_id, str) and ACQUISITION_ID_RE.fullmatch(acquisition_id) is not None, "acquisition_id_invalid", stage="context")
    collector_run_key = context.get("collector_run_key")
    _require(isinstance(collector_run_key, str) and collector_run_key != "", "collector_run_key_invalid", stage="context")
    workflow_ref = context.get("reference_workflow_ref")
    _require(
        workflow_ref
        == f"{REPOSITORY}/{REFERENCE_WORKFLOW_PATH}@refs/heads/main",
        "reference_workflow_ref_mismatch",
        stage="context",
    )
    return context


def _run_summary_from_raw(
    value: dict[str, Any],
    *,
    workflow_name: str,
    workflow_path: str,
) -> dict[str, Any]:
    repository = value.get("repository")
    _require(isinstance(repository, dict), "run_repository_missing", workflow_name, stage="run")
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


def _validate_run_summary(
    summary: Any,
    *,
    source_commit: str,
    workflow_name: str,
    workflow_path: str,
    role: str,
) -> dict[str, Any]:
    _require(isinstance(summary, dict), f"{role}_summary_missing", stage="run")
    expected = {
        "repository": REPOSITORY,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "event": "workflow_dispatch",
        "head_branch": "main",
        "head_sha": source_commit,
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
    }
    for key, value in expected.items():
        _require(summary.get(key) == value, f"{role}_summary_mismatch", key, stage="run")
    _positive_int(summary.get("run_id"), label=f"{role}_run_id")
    _positive_int(summary.get("run_number"), label=f"{role}_run_number")
    for key in ("created_at", "run_started_at", "updated_at"):
        _parse_utc(summary.get(key), label=f"{role}.{key}")
    _require(
        _parse_utc(summary["created_at"], label=f"{role}.created_at")
        <= _parse_utc(summary["run_started_at"], label=f"{role}.run_started_at")
        <= _parse_utc(summary["updated_at"], label=f"{role}.updated_at"),
        f"{role}_time_order_invalid",
        stage="run",
    )
    expected_api = f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{summary['run_id']}"
    expected_html = f"https://github.com/{REPOSITORY}/actions/runs/{summary['run_id']}"
    _require(summary.get("run_url") == expected_api, f"{role}_run_url_mismatch", stage="run")
    _require(summary.get("html_url") == expected_html, f"{role}_html_url_mismatch", stage="run")
    return dict(summary)


def _validate_dispatch_receipt(
    *,
    acquisition_files: Mapping[str, FileSnapshot],
    member: str,
    request_member: str,
    response_member: str,
    schema: dict[str, Any],
    record_status: str,
    source_commit: str,
    role: str,
    subject_run_id: int | None = None,
) -> dict[str, Any]:
    receipt = _json_object(acquisition_files[member].path.read_bytes(), label=member, canonical=True)
    _schema_validate(schema, receipt, label=member)
    _require(receipt.get("record_status") == record_status, "dispatch_receipt_record_status_mismatch", role, stage="dispatch")
    _require(receipt.get("source_commit") == source_commit, "dispatch_receipt_source_mismatch", role, stage="dispatch")
    _require(receipt.get("authority_boundary") == AUTHORITY_BOUNDARY, "dispatch_receipt_authority_mismatch", role, stage="dispatch")
    request_bytes = acquisition_files[request_member].path.read_bytes()
    response_bytes = acquisition_files[response_member].path.read_bytes()
    _require(receipt.get("request_body_sha256") == _sha256(request_bytes), "dispatch_request_digest_mismatch", role, stage="dispatch")
    _require(receipt.get("response_body_sha256") == _sha256(response_bytes), "dispatch_response_digest_mismatch", role, stage="dispatch")
    _require(_canonical_json_bytes(receipt.get("request")) == request_bytes, "dispatch_request_bytes_mismatch", role, stage="dispatch")
    response = _json_object(response_bytes, label=response_member, canonical=False)
    receipt_response = receipt.get("response")
    _require(isinstance(receipt_response, dict), "dispatch_response_record_missing", role, stage="dispatch")
    _require(response.get("workflow_run_id") == receipt_response.get("workflow_run_id"), "dispatch_receipt_mismatch", f"{role}:run_id", stage="dispatch")
    _require(response.get("run_url") == receipt_response.get("run_url"), "dispatch_receipt_mismatch", f"{role}:run_url", stage="dispatch")
    _require(response.get("html_url") == receipt_response.get("html_url"), "dispatch_receipt_mismatch", f"{role}:html_url", stage="dispatch")
    _require(receipt_response.get("http_status") == 200, "dispatch_http_status_mismatch", role, stage="dispatch")
    run_id = _positive_int(receipt_response.get("workflow_run_id"), label=f"{role}_dispatch_run_id")
    if subject_run_id is not None:
        _require(receipt.get("subject_workflow_run_id") == subject_run_id, "provider_subject_run_id_mismatch", stage="dispatch")
        request = receipt.get("request")
        _require(isinstance(request, dict) and request.get("inputs", {}).get("source_run_id") == str(subject_run_id), "provider_dispatch_input_mismatch", stage="dispatch")
    _require(receipt.get("run_list_fallback_used") is False, "run_list_fallback_used", role, stage="dispatch")
    _require(
        _parse_utc(receipt.get("requested_utc"), label=f"{role}.requested_utc")
        <= _parse_utc(receipt.get("received_utc"), label=f"{role}.received_utc"),
        "dispatch_time_order_invalid",
        role,
        stage="dispatch",
    )
    return {"receipt": receipt, "run_id": run_id}


def _load_paginated_rows(
    *,
    acquisition_files: Mapping[str, FileSnapshot],
    members: Any,
    expected_total: Any,
    array_key: str,
    role: str,
) -> list[dict[str, Any]]:
    _require(isinstance(members, list) and members, "pagination_members_missing", role, stage="pagination")
    normalized = [_safe_member(item, label=f"{role}.{array_key}.page") for item in members]
    _require(normalized == sorted(normalized) and len(normalized) == len(set(normalized)), "pagination_member_order_or_duplicate", role, stage="pagination")
    rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    observed_total: int | None = None
    for page_number, member in enumerate(normalized, start=1):
        _require(member in acquisition_files, "pagination_member_missing", member, stage="pagination")
        page = _json_object(acquisition_files[member].path.read_bytes(), label=member, canonical=False)
        total = page.get("total_count")
        page_rows = page.get(array_key)
        _require(isinstance(total, int) and not isinstance(total, bool) and total >= 0, "pagination_total_invalid", role, stage="pagination")
        _require(isinstance(page_rows, list), "pagination_rows_invalid", role, stage="pagination")
        if observed_total is None:
            observed_total = total
        else:
            _require(total == observed_total, "pagination_total_changed", role, stage="pagination")
        for row in page_rows:
            _require(isinstance(row, dict), "pagination_row_not_object", role, stage="pagination")
            identifier = _positive_int(row.get("id"), label=f"{role}_{array_key}_id")
            _require(identifier not in seen_ids, "pagination_duplicate_identifier", f"{role}:{identifier}", stage="pagination")
            seen_ids.add(identifier)
            rows.append(row)
        _require(len(rows) <= total, "pagination_overrun", role, stage="pagination")
        if page_number < len(normalized):
            _require(page_rows != [], "pagination_empty_nonterminal_page", role, stage="pagination")
    _require(observed_total == expected_total == len(rows), "pagination_not_closed", role, stage="pagination")
    return rows


def _match_subject_jobs(plan: dict[str, Any], rows: Sequence[dict[str, Any]], *, subject_run_id: int, source_commit: str) -> dict[str, int]:
    jobs = plan.get("jobs")
    _require(isinstance(jobs, list) and len(jobs) == EXPECTED_JOB_COUNT, "plan_jobs_invalid", stage="jobs")
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row.get("name")
        _require(isinstance(name, str) and name not in by_name, "job_identity_conflict", str(name), stage="jobs")
        by_name[name] = row
    plan_names = [job.get("display_name") for job in jobs]
    _require(all(isinstance(name, str) for name in plan_names), "plan_job_display_name_invalid", stage="jobs")
    _require(set(plan_names) == set(by_name), "job_extent_mismatch", stage="jobs")

    success_jobs = 0
    skipped_jobs = 0
    raw_platform_steps = 0
    lifecycle_steps = 0
    declared_steps = 0
    successful_steps = 0
    skipped_steps = 0

    for job in jobs:
        display_name = str(job["display_name"])
        platform = by_name[display_name]
        _require(platform.get("run_id") == subject_run_id, "cross_run_context", f"job:{display_name}", stage="jobs")
        _require(platform.get("run_attempt") == 1, "subject_attempt_mismatch", f"job:{display_name}", stage="jobs")
        _require(str(platform.get("head_sha", "")).lower() == source_commit, "subject_source_mismatch", f"job:{display_name}", stage="jobs")
        _require(platform.get("status") == "completed", "job_not_terminal", display_name, stage="jobs")
        expected_job_result = job.get("expected_terminal_result")
        _require(platform.get("conclusion") == expected_job_result, "job_terminal_result_mismatch", display_name, stage="jobs")
        if expected_job_result == "success":
            success_jobs += 1
        elif expected_job_result == "skipped":
            skipped_jobs += 1
        else:
            raise CaptureError("plan_job_result_invalid", display_name, stage="jobs")

        platform_steps = platform.get("steps")
        _require(isinstance(platform_steps, list), "job_steps_missing", display_name, stage="steps")
        raw_platform_steps += len(platform_steps)
        expected_steps = [
            step
            for step in job.get("steps", [])
            if isinstance(step, dict) and step.get("expected_runtime_presence") is True
        ]
        if expected_job_result == "skipped":
            _require(expected_steps == [], "skipped_job_has_instantiated_plan_steps", display_name, stage="steps")
            _require(platform_steps == [], "skipped_job_platform_steps_present", display_name, stage="steps")
            continue

        expected_index = 0
        for platform_step in platform_steps:
            _require(isinstance(platform_step, dict), "platform_step_not_object", display_name, stage="steps")
            name = platform_step.get("name")
            _require(isinstance(name, str) and name != "", "platform_step_name_invalid", display_name, stage="steps")
            _require(platform_step.get("status") == "completed", "platform_step_not_terminal", name, stage="steps")
            if expected_index < len(expected_steps) and name == expected_steps[expected_index].get("name"):
                expected = expected_steps[expected_index]
                expected_result = expected.get("expected_terminal_result")
                _require(platform_step.get("conclusion") == expected_result, "step_condition_result_mismatch", str(expected.get("occurrence_id")), stage="steps")
                declared_steps += 1
                if expected_result == "success":
                    successful_steps += 1
                elif expected_result == "skipped":
                    skipped_steps += 1
                else:
                    raise CaptureError("plan_step_result_invalid", str(expected.get("occurrence_id")), stage="steps")
                expected_index += 1
                continue
            _require(name in EXPECTED_LIFECYCLE_NAMES, "unexpected_platform_step", f"{display_name}:{name}", stage="steps")
            _require(platform_step.get("conclusion") in {"success", "skipped"}, "platform_lifecycle_result_invalid", name, stage="steps")
            lifecycle_steps += 1
        _require(expected_index == len(expected_steps), "step_extent_mismatch", display_name, stage="steps")

    _require(success_jobs == EXPECTED_SUCCESSFUL_JOB_COUNT, "job_extent_mismatch", "success_count", stage="jobs")
    _require(skipped_jobs == EXPECTED_SKIPPED_JOB_COUNT, "job_extent_mismatch", "skipped_count", stage="jobs")
    _require(declared_steps == EXPECTED_INSTANTIATED_STEP_COUNT, "step_extent_mismatch", "declared_count", stage="steps")
    _require(successful_steps == EXPECTED_SUCCESSFUL_STEP_COUNT, "step_extent_mismatch", "success_count", stage="steps")
    _require(skipped_steps == EXPECTED_SKIPPED_STEP_COUNT, "step_extent_mismatch", "skipped_count", stage="steps")
    _require(raw_platform_steps == declared_steps + lifecycle_steps, "platform_step_partition_mismatch", stage="steps")
    return {
        "raw_platform_step_record_count": raw_platform_steps,
        "platform_lifecycle_record_count": lifecycle_steps,
    }


def _validate_provider_job(rows: Sequence[dict[str, Any]], *, provider_run_id: int, source_commit: str) -> None:
    _require(len(rows) == 1, "provider_job_extent_mismatch", stage="jobs")
    row = rows[0]
    _require(row.get("run_id") == provider_run_id, "provider_cross_run_context", stage="jobs")
    _require(row.get("run_attempt") == 1, "provider_attempt_mismatch", stage="jobs")
    _require(str(row.get("head_sha", "")).lower() == source_commit, "provider_source_mismatch", stage="jobs")
    _require(row.get("status") == "completed" and row.get("conclusion") == "success", "provider_job_not_successful", stage="jobs")


def _artifact_bindings(
    *,
    acquisition_files: Mapping[str, FileSnapshot],
    downloaded: Any,
    subject_run_id: int,
    provider_run_id: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _require(isinstance(downloaded, list) and len(downloaded) == 4, "downloaded_artifact_count_mismatch", stage="artifact")
    result: list[dict[str, Any]] = []
    by_role: dict[str, dict[str, Any]] = {}
    for row in downloaded:
        _require(isinstance(row, dict), "downloaded_artifact_row_invalid", stage="artifact")
        role = row.get("role")
        _require(isinstance(role, str) and role not in by_role, "downloaded_artifact_role_conflict", str(role), stage="artifact")
        by_role[role] = row
        source_kind = row.get("source_run_kind")
        expected_run = provider_run_id if source_kind == "provider" else subject_run_id
        _require(row.get("source_run_id") == expected_run, "artifact_binding_mismatch", f"{role}:run", stage="artifact")
        _require(row.get("source_run_attempt") == 1, "artifact_binding_mismatch", f"{role}:attempt", stage="artifact")
        member = _safe_member(row.get("downloaded_member"), label=f"artifact:{role}:member")
        _require(member in acquisition_files, "artifact_download_missing", member, stage="artifact")
        snapshot = acquisition_files[member]
        github_sha = _canonical_sha256(row.get("github_sha256"), label=f"artifact:{role}:github_sha256")
        downloaded_sha = _canonical_sha256(row.get("downloaded_sha256"), label=f"artifact:{role}:downloaded_sha256")
        _require(github_sha == downloaded_sha == snapshot.sha256, "artifact_binding_mismatch", f"{role}:sha256", stage="artifact")
        _require(row.get("size_bytes") == row.get("downloaded_size_bytes") == snapshot.size_bytes, "artifact_binding_mismatch", f"{role}:size", stage="artifact")
        _parse_utc(row.get("created_utc"), label=f"artifact:{role}:created")
        _parse_utc(row.get("expires_utc"), label=f"artifact:{role}:expires")
        _require(_parse_utc(row["expires_utc"], label=f"artifact:{role}:expires") > _parse_utc(row["created_utc"], label=f"artifact:{role}:created"), "artifact_retention_window_invalid", role, stage="artifact")
        artifact_role = "step3f_candidate_envelope" if role == "step3f_candidate_envelope" else "subject_terminal_artifact"
        expected_kind = "provider" if artifact_role == "step3f_candidate_envelope" else "subject"
        _require(source_kind == expected_kind, "artifact_source_kind_mismatch", role, stage="artifact")
        result.append(
            {
                "artifact_role": artifact_role,
                "source_run_kind": source_kind,
                "artifact_id": _positive_int(row.get("artifact_id"), label=f"artifact:{role}:id"),
                "artifact_name": row.get("artifact_name"),
                "source_run_id": expected_run,
                "source_run_attempt": 1,
                "created_utc": row.get("created_utc"),
                "expires_utc": row.get("expires_utc"),
                "expired": False,
                "size_bytes": snapshot.size_bytes,
                "github_sha256": github_sha,
                "exact_bytes_in_capture": True,
                "downloaded_member": ACQUISITION_PREFIX + member,
                "downloaded_sha256": snapshot.sha256,
                "downloaded_size_bytes": snapshot.size_bytes,
            }
        )
    expected_roles = set(SUBJECT_DOWNLOAD_ROLES) | {"step3f_candidate_envelope"}
    _require(set(by_role) == expected_roles, "downloaded_artifact_role_set_mismatch", stage="artifact")
    return sorted(result, key=lambda row: (row["source_run_kind"], row["artifact_name"])), by_role


def _zip_safe_name(info: zipfile.ZipInfo, *, label: str, allow_directory: bool) -> str | None:
    name = info.filename
    _require(isinstance(name, str) and name != "", "zip_member_name_invalid", label, stage="zip")
    _require("\\" not in name and "\x00" not in name, "zip_member_name_unsafe", name, stage="zip")
    path = PurePosixPath(name)
    _require(not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts), "zip_member_name_unsafe", name, stage="zip")
    mode = (info.external_attr >> 16) & 0xFFFF
    _require(not stat.S_ISLNK(mode), "zip_symlink_member_rejected", name, stage="zip")
    _require(info.flag_bits & 0x1 == 0, "zip_encrypted_member_rejected", name, stage="zip")
    _require(info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "zip_compression_unsupported", name, stage="zip")
    if info.is_dir() or name.endswith("/"):
        _require(allow_directory, "zip_directory_member_rejected", name, stage="zip")
        return None
    _require(info.file_size >= 0 and info.file_size <= MAX_CANDIDATE_FILE_BYTES, "zip_member_size_out_of_range", name, stage="zip")
    return name


def _zip_file_infos(archive: zipfile.ZipFile, *, label: str, maximum: int, allow_directories: bool) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    _require(0 < len(infos) <= maximum, "zip_member_count_invalid", label, stage="zip")
    result: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = _zip_safe_name(info, label=label, allow_directory=allow_directories)
        if name is None:
            continue
        _require(name not in result, "zip_duplicate_member", name, stage="zip")
        result[name] = info
    _require(result, "zip_has_no_file_members", label, stage="zip")
    return result


def _read_zip_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    label: str,
    maximum: int,
) -> bytes:
    _require(info.file_size <= maximum, "zip_member_size_out_of_range", label, stage="zip")
    try:
        payload = archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise CaptureError("zip_member_read_failed", label, stage="zip") from exc
    _require(len(payload) == info.file_size, "zip_member_size_mismatch", label, stage="zip")
    return payload


def _hash_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, *, label: str) -> ZipEntryBinding:
    digest = hashlib.sha256()
    total = 0
    try:
        with archive.open(info, "r") as stream:
            while True:
                chunk = stream.read(HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise CaptureError("zip_member_read_failed", label, stage="zip") from exc
    _require(total == info.file_size, "zip_member_size_mismatch", label, stage="zip")
    return ZipEntryBinding(name=info.filename, sha256=digest.hexdigest(), size_bytes=total)


def _spool_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, *, label: str) -> tuple[BinaryIO, ZipEntryBinding]:
    spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    digest = hashlib.sha256()
    total = 0
    try:
        with archive.open(info, "r") as source:
            while True:
                chunk = source.read(HASH_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                _require(total <= MAX_CANDIDATE_FILE_BYTES, "zip_member_size_out_of_range", label, stage="zip")
                digest.update(chunk)
                spool.write(chunk)
        _require(total == info.file_size, "zip_member_size_mismatch", label, stage="zip")
        spool.seek(0)
        return spool, ZipEntryBinding(info.filename, digest.hexdigest(), total)
    except Exception:
        spool.close()
        raise


def _candidate_prefix(infos: Mapping[str, zipfile.ZipInfo]) -> tuple[str, str]:
    candidates = [name for name in infos if name == "candidate-output-manifest.json" or name.endswith("/candidate-output-manifest.json")]
    _require(len(candidates) == 1, "candidate_manifest_not_unique", stage="provider")
    manifest_member = candidates[0]
    prefix = manifest_member[: -len("candidate-output-manifest.json")]
    return prefix, manifest_member


def _validate_candidate_manifest(
    *,
    archive: zipfile.ZipFile,
    infos: Mapping[str, zipfile.ZipInfo],
    prefix: str,
    manifest_member: str,
    subject_run_id: int,
    source_commit: str,
) -> tuple[dict[str, ZipEntryBinding], dict[str, bytes], BinaryIO, ZipEntryBinding]:
    manifest_bytes = _read_zip_member(
        archive,
        infos[manifest_member],
        label="candidate-output-manifest.json",
        maximum=MAX_JSON_BYTES,
    )
    manifest = _json_object(manifest_bytes, label="candidate_output_manifest", canonical=True)
    _require(manifest.get("schema_version") == "pulsemech_compute_current_run_export_candidate_output_manifest_v0", "candidate_manifest_version_mismatch", stage="provider")
    _require(manifest.get("document_type") == "pulsemech_compute_current_run_export_candidate_output_manifest", "candidate_manifest_type_mismatch", stage="provider")
    _require(manifest.get("manifest_scope") == "all_candidate_files_except_this_manifest", "candidate_manifest_scope_mismatch", stage="provider")
    _require(manifest.get("authority_boundary") == EXPECTED_CANDIDATE_AUTHORITY_BOUNDARY, "candidate_manifest_authority_mismatch", stage="provider")
    _require(manifest.get("source_run_id") == subject_run_id, "provider_subject_mismatch", "candidate_manifest.run_id", stage="provider")
    _require(manifest.get("source_run_attempt") == 1, "provider_subject_mismatch", "candidate_manifest.attempt", stage="provider")
    _require(manifest.get("subject_revision") == source_commit, "provider_subject_mismatch", "candidate_manifest.source", stage="provider")
    rows = manifest.get("files")
    _require(isinstance(rows, list) and manifest.get("file_count") == len(rows) == 6, "candidate_manifest_file_count_mismatch", stage="provider")
    declared: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "candidate_manifest_row_invalid", stage="provider")
        name = row.get("path")
        _require(isinstance(name, str) and "/" not in name and "\\" not in name and name != "", "candidate_manifest_path_invalid", str(name), stage="provider")
        _require(name not in declared, "candidate_manifest_duplicate_path", name, stage="provider")
        declared[name] = row
    expected_static = {
        "carrier.json",
        "expectation.json",
        "subject-input-packet.json",
        "source-run-resolution.json",
        "source-artifact-selection.json",
    }
    zip_names = {name for name in declared if name.endswith(".zip")}
    _require(set(declared) == expected_static | zip_names and len(zip_names) == 1, "candidate_manifest_file_set_mismatch", stage="provider")
    actual_files = {name[len(prefix):] for name in infos if name.startswith(prefix) and name != manifest_member}
    _require(actual_files == set(declared), "candidate_envelope_inventory_mismatch", stage="provider")

    bindings: dict[str, ZipEntryBinding] = {}
    small_payloads: dict[str, bytes] = {}
    carrier_spool: BinaryIO | None = None
    carrier_binding: ZipEntryBinding | None = None
    for name, row in sorted(declared.items()):
        member = prefix + name
        _require(member in infos, "candidate_member_missing", member, stage="provider")
        info = infos[member]
        if name.endswith(".zip"):
            carrier_spool, binding = _spool_zip_member(archive, info, label=member)
            carrier_binding = binding
        else:
            payload = _read_zip_member(archive, info, label=member, maximum=MAX_JSON_BYTES)
            small_payloads[name] = payload
            binding = ZipEntryBinding(member, _sha256(payload), len(payload))
        _require(row.get("sha256") == binding.sha256, "candidate_member_digest_mismatch", name, stage="provider")
        _require(row.get("size_bytes") == binding.size_bytes, "candidate_member_size_mismatch", name, stage="provider")
        bindings[name] = binding
    _require(carrier_spool is not None and carrier_binding is not None, "candidate_carrier_missing", stage="provider")
    return bindings, small_payloads, carrier_spool, carrier_binding


def _parse_sha256sums(data: bytes) -> dict[str, str]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "carrier_checksums_bom_rejected", stage="provider")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise CaptureError("carrier_checksums_invalid_utf8", stage="provider") from exc
    _require(text.endswith("\n"), "carrier_checksums_final_lf_missing", stage="provider")
    result: dict[str, str] = {}
    previous: str | None = None
    for raw in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
        _require(match is not None, "carrier_checksums_line_invalid", raw, stage="provider")
        digest, path = match.groups()
        _safe_member(path, label="carrier.checksum_path")
        _require(path not in result, "carrier_checksums_duplicate_path", path, stage="provider")
        if previous is not None:
            _require(previous < path, "carrier_checksums_not_sorted", stage="provider")
        previous = path
        result[path] = digest
    _require(result, "carrier_checksums_empty", stage="provider")
    return result


def _validate_provider_envelope(
    *,
    provider_envelope: FileSnapshot,
    subject_run_id: int,
    source_commit: str,
    artifact_rows: Mapping[str, dict[str, Any]],
) -> ProviderEnvelopeBinding:
    try:
        outer = zipfile.ZipFile(provider_envelope.path, "r", allowZip64=True)
    except (OSError, zipfile.BadZipFile) as exc:
        raise CaptureError("provider_envelope_invalid_zip", stage="provider") from exc
    with outer:
        infos = _zip_file_infos(
            outer,
            label="provider_envelope",
            maximum=MAX_CANDIDATE_FILES + 16,
            allow_directories=True,
        )
        prefix, manifest_member = _candidate_prefix(infos)
        bindings, payloads, carrier_spool, carrier_binding = _validate_candidate_manifest(
            archive=outer,
            infos=infos,
            prefix=prefix,
            manifest_member=manifest_member,
            subject_run_id=subject_run_id,
            source_commit=source_commit,
        )
        try:
            carrier_meta = _json_object(payloads["carrier.json"], label="step3f_carrier_metadata", canonical=True)
            expectation = _json_object(payloads["expectation.json"], label="step3f_expectation", canonical=True)
            packet = _json_object(payloads["subject-input-packet.json"], label="step3f_subject_input_packet", canonical=True)
            _require(carrier_meta.get("sha256") == carrier_binding.sha256, "provider_carrier_digest_mismatch", stage="provider")
            _require(carrier_meta.get("size_bytes") == carrier_binding.size_bytes, "provider_carrier_size_mismatch", stage="provider")
            carrier_filename = next(name for name in bindings if name.endswith(".zip"))
            staged = carrier_meta.get("staged_relative_path")
            _require(isinstance(staged, str) and PurePosixPath(staged).name == carrier_filename, "provider_carrier_path_mismatch", stage="provider")
            for label, document in (("expectation", expectation), ("packet", packet)):
                carrier = document.get("carrier")
                _require(isinstance(carrier, dict), f"{label}_carrier_missing", stage="provider")
                _require(carrier.get("sha256") == carrier_binding.sha256, f"{label}_carrier_digest_mismatch", stage="provider")
                _require(carrier.get("size_bytes") == carrier_binding.size_bytes, f"{label}_carrier_size_mismatch", stage="provider")
            _require(expectation.get("record_status") == "observed", "expectation_not_observed", stage="provider")
            _require(packet.get("record_status") == "observed", "subject_packet_not_observed", stage="provider")
            subject = expectation.get("subject")
            _require(isinstance(subject, dict), "expectation_subject_missing", stage="provider")
            _require(subject.get("workflow_run_id") == subject_run_id, "provider_subject_mismatch", "expectation.run_id", stage="provider")
            _require(subject.get("workflow_run_attempt") == 1, "provider_subject_mismatch", "expectation.attempt", stage="provider")
            _require(subject.get("source_commit") == source_commit, "provider_subject_mismatch", "expectation.source", stage="provider")
            _require(packet.get("subject") == subject, "provider_packet_subject_mismatch", stage="provider")
            archive_layout = expectation.get("archive_layout")
            _require(isinstance(archive_layout, dict), "provider_archive_layout_missing", stage="provider")
            root_prefix = archive_layout.get("outer_prefix")
            original_prefix = archive_layout.get("original_artifacts_prefix")
            _require(isinstance(root_prefix, str) and root_prefix.endswith("/"), "provider_root_prefix_invalid", stage="provider")
            _require(isinstance(original_prefix, str) and original_prefix == root_prefix + "original-github-artifacts/", "provider_original_prefix_invalid", stage="provider")

            try:
                carrier_archive = zipfile.ZipFile(carrier_spool, "r", allowZip64=True)
            except zipfile.BadZipFile as exc:
                raise CaptureError("current_run_carrier_invalid_zip", stage="provider") from exc
            with carrier_archive:
                carrier_infos = _zip_file_infos(
                    carrier_archive,
                    label="current_run_carrier",
                    maximum=MAX_CARRIER_MEMBERS,
                    allow_directories=False,
                )
                _require(all(name.startswith(root_prefix) for name in carrier_infos), "current_run_carrier_root_prefix_mismatch", stage="provider")
                checksum_member = root_prefix + "SHA256SUMS"
                _require(checksum_member in carrier_infos, "current_run_carrier_checksums_missing", stage="provider")
                checksum_bytes = _read_zip_member(
                    carrier_archive,
                    carrier_infos[checksum_member],
                    label=checksum_member,
                    maximum=2 * 1024 * 1024,
                )
                checksums = _parse_sha256sums(checksum_bytes)
                expected_checksum_paths = {
                    name[len(root_prefix):]
                    for name in carrier_infos
                    if name != checksum_member
                }
                _require(set(checksums) == expected_checksum_paths, "current_run_carrier_checksum_inventory_mismatch", stage="provider")
                for relative, expected_digest in checksums.items():
                    full = root_prefix + relative
                    binding = _hash_zip_member(carrier_archive, carrier_infos[full], label=full)
                    _require(binding.sha256 == expected_digest, "current_run_carrier_checksum_mismatch", relative, stage="provider")

                carrier_rows: list[dict[str, Any]] = []
                for acquisition_role, (binding_role, layout_field) in SUBJECT_DOWNLOAD_ROLES.items():
                    file_name = archive_layout.get(layout_field)
                    _require(isinstance(file_name, str) and "/" not in file_name and "\\" not in file_name, "archive_layout_artifact_name_invalid", layout_field, stage="provider")
                    full_member = original_prefix + file_name
                    _require(full_member in carrier_infos, "current_run_carrier_artifact_missing", full_member, stage="provider")
                    inner = _hash_zip_member(carrier_archive, carrier_infos[full_member], label=full_member)
                    acquisition = artifact_rows[acquisition_role]
                    _require(inner.sha256 == acquisition.get("downloaded_sha256"), "provider_subject_artifact_digest_mismatch", acquisition_role, stage="provider")
                    _require(inner.size_bytes == acquisition.get("downloaded_size_bytes"), "provider_subject_artifact_size_mismatch", acquisition_role, stage="provider")
                    carrier_rows.append(
                        {
                            "role": binding_role,
                            "container_artifact_role": "step3f_candidate_envelope",
                            "member": full_member,
                            "sha256": inner.sha256,
                            "size_bytes": inner.size_bytes,
                        }
                    )

            carrier_rows.extend(
                [
                    {
                        "role": "step3f_expectation",
                        "container_artifact_role": "step3f_candidate_envelope",
                        "member": prefix + "expectation.json",
                        "sha256": bindings["expectation.json"].sha256,
                        "size_bytes": bindings["expectation.json"].size_bytes,
                    },
                    {
                        "role": "step3f_subject_input_packet",
                        "container_artifact_role": "step3f_candidate_envelope",
                        "member": prefix + "subject-input-packet.json",
                        "sha256": bindings["subject-input-packet.json"].sha256,
                        "size_bytes": bindings["subject-input-packet.json"].size_bytes,
                    },
                    {
                        "role": "step3f_current_run_carrier",
                        "container_artifact_role": "step3f_candidate_envelope",
                        "member": prefix + carrier_filename,
                        "sha256": carrier_binding.sha256,
                        "size_bytes": carrier_binding.size_bytes,
                    },
                ]
            )
            _require(len(carrier_rows) == 6, "carrier_member_binding_count_mismatch", stage="provider")
            return ProviderEnvelopeBinding(
                carrier_member_bindings=sorted(carrier_rows, key=lambda row: row["role"]),
                candidate_prefix=prefix,
                carrier_candidate_member=prefix + carrier_filename,
                carrier_sha256=carrier_binding.sha256,
                carrier_size_bytes=carrier_binding.size_bytes,
            )
        finally:
            carrier_spool.close()


def _raw_response_bindings(
    *,
    acquisition_files: Mapping[str, FileSnapshot],
    index: dict[str, Any],
) -> list[dict[str, Any]]:
    fixed = [
        ("subject_dispatch_request", SUBJECT_DISPATCH_REQUEST_MEMBER),
        ("subject_dispatch_response", SUBJECT_DISPATCH_RESPONSE_MEMBER),
        ("subject_run_response", SUBJECT_RUN_RESPONSE_MEMBER),
        ("provider_dispatch_request", PROVIDER_DISPATCH_REQUEST_MEMBER),
        ("provider_dispatch_response", PROVIDER_DISPATCH_RESPONSE_MEMBER),
        ("provider_run_response", PROVIDER_RUN_RESPONSE_MEMBER),
    ]
    dynamic = [
        ("subject_jobs_page", index["subject_jobs"]["page_members"]),
        ("subject_artifacts_page", index["subject_artifacts"]["page_members"]),
        ("provider_jobs_page", index["provider_jobs"]["page_members"]),
        ("provider_artifacts_page", index["provider_artifacts"]["page_members"]),
    ]
    rows: list[dict[str, Any]] = []
    for role, member in fixed:
        snapshot = acquisition_files[member]
        rows.append(
            {
                "role": role,
                "descriptor": _snapshot_descriptor(snapshot, member=ACQUISITION_PREFIX + member),
            }
        )
    for role, members in dynamic:
        _require(isinstance(members, list), "raw_response_page_members_invalid", role, stage="capture")
        for member_value in members:
            member = _safe_member(member_value, label=f"{role}.member")
            snapshot = acquisition_files[member]
            rows.append(
                {
                    "role": role,
                    "descriptor": _snapshot_descriptor(snapshot, member=ACQUISITION_PREFIX + member),
                }
            )
    return rows


def _capture_members(
    *,
    plan_snapshot: FileSnapshot,
    diagnostic_snapshot: FileSnapshot,
    expected_plan_sha256: str,
    acquisition_files: Mapping[str, FileSnapshot],
) -> list[CaptureMember]:
    expected_bytes = (expected_plan_sha256 + "\n").encode("ascii")
    members: list[CaptureMember] = [
        CaptureMember(
            member=PREPARED_PLAN_MEMBER,
            snapshot=plan_snapshot,
            literal=None,
            sha256=plan_snapshot.sha256,
            size_bytes=plan_snapshot.size_bytes,
        ),
        CaptureMember(
            member=PREPARED_PLAN_DIAGNOSTIC_MEMBER,
            snapshot=diagnostic_snapshot,
            literal=None,
            sha256=diagnostic_snapshot.sha256,
            size_bytes=diagnostic_snapshot.size_bytes,
        ),
        CaptureMember(
            member=PREPARED_EXPECTED_PLAN_MEMBER,
            snapshot=None,
            literal=expected_bytes,
            sha256=_sha256(expected_bytes),
            size_bytes=len(expected_bytes),
        ),
    ]
    for relative, snapshot in acquisition_files.items():
        members.append(
            CaptureMember(
                member=ACQUISITION_PREFIX + relative,
                snapshot=snapshot,
                literal=None,
                sha256=snapshot.sha256,
                size_bytes=snapshot.size_bytes,
            )
        )
    members = sorted(members, key=lambda item: item.member)
    _require(len({item.member for item in members}) == len(members), "capture_member_name_conflict", stage="capture")
    _require(len(members) <= MAX_CAPTURE_MEMBERS - 1, "capture_member_limit_exceeded", stage="capture")
    total = sum(item.size_bytes for item in members)
    _require(total <= MAX_CAPTURE_UNCOMPRESSED_BYTES, "capture_byte_limit_exceeded", str(total), stage="capture")
    return members


def _zip_info(member: str, *, size_bytes: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=_safe_member(member, label="capture_zip_member"), date_time=ZIP_TIMESTAMP)
    info.create_system = 3
    info.external_attr = ZIP_MODE << 16
    info.compress_type = zipfile.ZIP_STORED
    info.comment = b""
    info.extra = b""
    info.flag_bits = 0
    info.file_size = size_bytes
    return info


def _write_member(zf: zipfile.ZipFile, member: CaptureMember) -> None:
    info = _zip_info(member.member, size_bytes=member.size_bytes)
    digest = hashlib.sha256()
    total = 0
    with zf.open(info, mode="w", force_zip64=member.size_bytes >= zipfile.ZIP64_LIMIT) as target:
        if member.literal is not None:
            target.write(member.literal)
            digest.update(member.literal)
            total = len(member.literal)
        else:
            _require(member.snapshot is not None, "capture_member_source_missing", member.member, stage="publication")
            _verify_snapshot_unchanged(member.snapshot)
            with member.snapshot.path.open("rb", buffering=0) as source:
                while True:
                    chunk = source.read(HASH_CHUNK_BYTES)
                    if not chunk:
                        break
                    target.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
            _verify_snapshot_unchanged(member.snapshot)
    _require(total == member.size_bytes, "capture_member_size_changed", member.member, stage="publication")
    _require(digest.hexdigest() == member.sha256, "capture_member_digest_changed", member.member, stage="publication")


def _rename_noreplace(source: Path, destination: Path) -> None:
    if os.name != "posix":
        raise CaptureError("no_replace_primitive_unavailable", os.name, stage="publication")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise CaptureError("renameat2_unavailable", stage="publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    AT_FDCWD = -100
    RENAME_NOREPLACE = 1
    result = renameat2(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise CaptureError("output_already_exists", str(destination), stage="publication")
        if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
            raise CaptureError("no_replace_primitive_unavailable", os.strerror(error), stage="publication")
        raise CaptureError("output_publication_failed", os.strerror(error), stage="publication")


def _validate_output(path: Path) -> tuple[Path, Path]:
    output = _normalized_absolute(path)
    _require(output.name not in {"", ".", ".."}, "output_name_invalid", stage="publication")
    parent = output.parent
    _reject_symlink_components(parent, label="output_parent")
    _require(parent.is_dir(), "output_parent_not_directory", str(parent), stage="publication")
    _require(not output.exists() and not output.is_symlink(), "output_already_exists", str(output), stage="publication")
    return output, parent


def _write_capture_zip(
    *,
    output: Path,
    parent: Path,
    members: Sequence[CaptureMember],
    manifest_bytes: bytes,
) -> tuple[str, int]:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=parent)
    os.close(fd)
    temporary = Path(temporary_name)
    published = False
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
            strict_timestamps=True,
        ) as archive:
            manifest_member = CaptureMember(
                member=CAPTURE_MANIFEST_MEMBER,
                snapshot=None,
                literal=manifest_bytes,
                sha256=_sha256(manifest_bytes),
                size_bytes=len(manifest_bytes),
            )
            for member in sorted([*members, manifest_member], key=lambda item: item.member):
                _write_member(archive, member)
            archive.comment = b""
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.chmod(0o444)
        _rename_noreplace(temporary, output)
        published = True
        output_snapshot = _snapshot_file(
            output,
            relative=output.name,
            maximum=MAX_CAPTURE_UNCOMPRESSED_BYTES + 64 * 1024 * 1024,
            require_read_only=True,
        )
        return output_snapshot.sha256, output_snapshot.size_bytes
    finally:
        if not published and temporary.exists():
            try:
                temporary.chmod(0o600)
                temporary.unlink()
            except OSError:
                pass


def build_capture(
    *,
    repository_root: Path,
    source_commit: str,
    plan_path: Path,
    plan_diagnostic_path: Path,
    expected_plan_sha256: str,
    acquisition_directory: Path,
    output_path: Path,
    record_status: str,
) -> dict[str, Any]:
    """Validate one raw acquisition and publish a deterministic capture ZIP."""

    root = _validate_repository_root(repository_root)
    revision = _canonical_sha40(source_commit, label="source_commit")
    expected_plan = _canonical_sha256(expected_plan_sha256, label="expected_plan_sha256")
    _require(record_status in {"example", "observed"}, "record_status_invalid", stage="context")
    _require(_git(root, ["cat-file", "-t", revision]) == b"commit\n", "source_commit_object_required", stage="source")
    head = _git(root, ["rev-parse", "HEAD"]).decode("ascii", errors="strict").strip().lower()
    _require(head == revision, "checked_out_head_mismatch", f"head={head} source={revision}", stage="source")

    plan_snapshot = _snapshot_file(
        plan_path,
        relative="prelaunch-plan.json",
        maximum=MAX_PLAN_BYTES,
        require_read_only=False,
    )
    diagnostic_snapshot = _snapshot_file(
        plan_diagnostic_path,
        relative="prelaunch-plan-diagnostic.json",
        maximum=MAX_PLAN_DIAGNOSTIC_BYTES,
        require_read_only=False,
    )
    preliminary_plan = _json_object(plan_snapshot.path.read_bytes(), label="prelaunch_plan", canonical=True)
    source_inventory = _source_inventory(preliminary_plan)
    for required_path in (CAPTURE_PATH, ACQUIRE_PATH, PLAN_CHECKER_PATH, SCHEMA_PATH):
        _require(required_path in source_inventory, "plan_required_source_missing", required_path, stage="source")
    self_snapshot = _verify_installed_source(
        root=root,
        revision=revision,
        relative=CAPTURE_PATH,
        expected_row=source_inventory[CAPTURE_PATH],
        maximum=8 * 1024 * 1024,
    )
    _verify_installed_source(
        root=root,
        revision=revision,
        relative=ACQUIRE_PATH,
        expected_row=source_inventory[ACQUIRE_PATH],
        maximum=8 * 1024 * 1024,
    )
    schema_snapshot = _verify_installed_source(
        root=root,
        revision=revision,
        relative=SCHEMA_PATH,
        expected_row=source_inventory[SCHEMA_PATH],
        maximum=MAX_SCHEMA_BYTES,
    )
    # The schema is exact, verified repository source, not a generated record.
    # Preserve its original bytes; do not impose record serialization on it.
    schema = _json_object(schema_snapshot.path.read_bytes(), label="step5c_evidence_schema", canonical=False)
    plan = _plan_contract(
        plan_snapshot=plan_snapshot,
        diagnostic_snapshot=diagnostic_snapshot,
        expected_plan_sha256=expected_plan,
        source_commit=revision,
        record_status=record_status,
        schema=schema,
    )

    finite = plan.get("finite_limits")
    _require(isinstance(finite, dict), "plan_finite_limits_missing", stage="plan")
    max_members = int(finite.get("max_capture_members", MAX_CAPTURE_MEMBERS))
    max_bytes = int(finite.get("max_capture_uncompressed_bytes", MAX_CAPTURE_UNCOMPRESSED_BYTES))
    _require(1 <= max_members <= MAX_CAPTURE_MEMBERS, "plan_capture_member_limit_invalid", stage="plan")
    _require(1 <= max_bytes <= MAX_CAPTURE_UNCOMPRESSED_BYTES, "plan_capture_byte_limit_invalid", stage="plan")

    acquisition_files = _walk_acquisition(
        acquisition_directory,
        max_members=max_members,
        max_total_bytes=max_bytes,
    )
    index_snapshot = acquisition_files[ACQUISITION_INDEX_MEMBER]
    _require(index_snapshot.size_bytes <= MAX_INDEX_BYTES, "acquisition_index_too_large", stage="acquisition")
    index = _json_object(index_snapshot.path.read_bytes(), label="acquisition_index", canonical=True)
    fixed_index = {
        "schema_version": ACQUISITION_SCHEMA_VERSION,
        "record_status": record_status,
        "repository": REPOSITORY,
        "source_commit": revision,
        "source_ref": SOURCE_REF,
        "profile": PROFILE,
        "scope": SCOPE,
        "privacy_boundary": PRIVACY_BOUNDARY,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
        "ok": True,
    }
    for key, expected in fixed_index.items():
        _require(index.get(key) == expected, "acquisition_index_mismatch", key, stage="acquisition")
    _require(index.get("collection_boundary") == EXPECTED_ACQUISITION_COLLECTION_BOUNDARY, "acquisition_collection_boundary_mismatch", stage="acquisition")
    _validate_member_inventory(acquisition_files=acquisition_files, index=index)

    expected_context = _expected_context(
        snapshot=acquisition_files[EXPECTED_CONTEXT_MEMBER],
        source_commit=revision,
        expected_plan_sha256=expected_plan,
        record_status=record_status,
    )
    _require(index.get("reference_context") == expected_context, "acquisition_reference_context_mismatch", stage="context")
    _require(index.get("acquisition_id") == expected_context["acquisition_id"], "acquisition_id_mismatch", stage="context")
    plan_binding = index.get("plan_binding")
    _require(isinstance(plan_binding, dict), "acquisition_plan_binding_missing", stage="plan")
    _require(plan_binding.get("plan_sha256") == plan_snapshot.sha256 and plan_binding.get("plan_size_bytes") == plan_snapshot.size_bytes, "acquisition_plan_binding_mismatch", stage="plan")
    _require(plan_binding.get("plan_diagnostic_sha256") == diagnostic_snapshot.sha256 and plan_binding.get("plan_diagnostic_size_bytes") == diagnostic_snapshot.size_bytes, "acquisition_plan_diagnostic_binding_mismatch", stage="plan")
    _require(plan_binding.get("expected_plan_sha256") == expected_plan and plan_binding.get("independent_plan_diagnostic_reproduced") is True, "acquisition_plan_verification_missing", stage="plan")

    subject = _validate_run_summary(
        index.get("subject"),
        source_commit=revision,
        workflow_name=SUBJECT_WORKFLOW_NAME,
        workflow_path=SUBJECT_WORKFLOW_PATH,
        role="subject",
    )
    provider = _validate_run_summary(
        index.get("provider"),
        source_commit=revision,
        workflow_name=PROVIDER_WORKFLOW_NAME,
        workflow_path=PROVIDER_WORKFLOW_PATH,
        role="provider",
    )
    subject_run_id = int(subject["run_id"])
    provider_run_id = int(provider["run_id"])
    _require(provider_run_id != subject_run_id, "provider_subject_run_id_collision", stage="run")

    subject_receipt = _validate_dispatch_receipt(
        acquisition_files=acquisition_files,
        member=SUBJECT_DISPATCH_RECEIPT_MEMBER,
        request_member=SUBJECT_DISPATCH_REQUEST_MEMBER,
        response_member=SUBJECT_DISPATCH_RESPONSE_MEMBER,
        schema=schema,
        record_status=record_status,
        source_commit=revision,
        role="subject",
    )
    _require(subject_receipt["run_id"] == subject_run_id, "subject_dispatch_run_mismatch", stage="dispatch")
    provider_receipt = _validate_dispatch_receipt(
        acquisition_files=acquisition_files,
        member=PROVIDER_DISPATCH_RECEIPT_MEMBER,
        request_member=PROVIDER_DISPATCH_REQUEST_MEMBER,
        response_member=PROVIDER_DISPATCH_RESPONSE_MEMBER,
        schema=schema,
        record_status=record_status,
        source_commit=revision,
        role="provider",
        subject_run_id=subject_run_id,
    )
    _require(provider_receipt["run_id"] == provider_run_id, "provider_dispatch_run_mismatch", stage="dispatch")

    raw_subject = _json_object(acquisition_files[SUBJECT_RUN_RESPONSE_MEMBER].path.read_bytes(), label=SUBJECT_RUN_RESPONSE_MEMBER)
    raw_provider = _json_object(acquisition_files[PROVIDER_RUN_RESPONSE_MEMBER].path.read_bytes(), label=PROVIDER_RUN_RESPONSE_MEMBER)
    _require(_run_summary_from_raw(raw_subject, workflow_name=SUBJECT_WORKFLOW_NAME, workflow_path=SUBJECT_WORKFLOW_PATH) == subject, "subject_run_summary_mismatch", stage="run")
    _require(_run_summary_from_raw(raw_provider, workflow_name=PROVIDER_WORKFLOW_NAME, workflow_path=PROVIDER_WORKFLOW_PATH) == provider, "provider_run_summary_mismatch", stage="run")

    subject_jobs_info = index.get("subject_jobs")
    subject_artifacts_info = index.get("subject_artifacts")
    provider_jobs_info = index.get("provider_jobs")
    provider_artifacts_info = index.get("provider_artifacts")
    for value, label in (
        (subject_jobs_info, "subject_jobs"),
        (subject_artifacts_info, "subject_artifacts"),
        (provider_jobs_info, "provider_jobs"),
        (provider_artifacts_info, "provider_artifacts"),
    ):
        _require(isinstance(value, dict), f"{label}_index_missing", stage="pagination")

    subject_job_rows = _load_paginated_rows(
        acquisition_files=acquisition_files,
        members=subject_jobs_info["page_members"],
        expected_total=subject_jobs_info["total_count"],
        array_key="jobs",
        role="subject_jobs",
    )
    platform = _match_subject_jobs(
        plan,
        subject_job_rows,
        subject_run_id=subject_run_id,
        source_commit=revision,
    )
    provider_job_rows = _load_paginated_rows(
        acquisition_files=acquisition_files,
        members=provider_jobs_info["page_members"],
        expected_total=provider_jobs_info["total_count"],
        array_key="jobs",
        role="provider_jobs",
    )
    _validate_provider_job(provider_job_rows, provider_run_id=provider_run_id, source_commit=revision)
    _load_paginated_rows(
        acquisition_files=acquisition_files,
        members=subject_artifacts_info["page_members"],
        expected_total=subject_artifacts_info["total_count"],
        array_key="artifacts",
        role="subject_artifacts",
    )
    _load_paginated_rows(
        acquisition_files=acquisition_files,
        members=provider_artifacts_info["page_members"],
        expected_total=provider_artifacts_info["total_count"],
        array_key="artifacts",
        role="provider_artifacts",
    )

    artifact_bindings, artifact_rows = _artifact_bindings(
        acquisition_files=acquisition_files,
        downloaded=index.get("downloaded_artifacts"),
        subject_run_id=subject_run_id,
        provider_run_id=provider_run_id,
    )
    provider_envelope = acquisition_files[PROVIDER_ENVELOPE_MEMBER]
    provider_binding = _validate_provider_envelope(
        provider_envelope=provider_envelope,
        subject_run_id=subject_run_id,
        source_commit=revision,
        artifact_rows=artifact_rows,
    )

    capture_members = _capture_members(
        plan_snapshot=plan_snapshot,
        diagnostic_snapshot=diagnostic_snapshot,
        expected_plan_sha256=expected_plan,
        acquisition_files=acquisition_files,
    )
    inventory = [
        _descriptor(item.member, item.sha256, item.size_bytes)
        for item in capture_members
    ]
    capture_started = subject_receipt["receipt"]["requested_utc"]
    capture_completed = provider["updated_at"]
    _require(
        _parse_utc(capture_started, label="capture_started_utc")
        <= _parse_utc(capture_completed, label="capture_completed_utc"),
        "capture_time_order_invalid",
        stage="time",
    )
    capture_id = f"step5c-capture:{subject_run_id}:1"
    _require(CAPTURE_ID_RE.fullmatch(capture_id) is not None, "capture_id_invalid", stage="identity")
    subject_run_key = (
        f"GITHUB_RUN_ID={subject_run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={SUBJECT_WORKFLOW_NAME}"
    )
    provider_run_key = (
        f"GITHUB_RUN_ID={provider_run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={PROVIDER_WORKFLOW_NAME}"
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "record_status": record_status,
        "capture_identity": {
            "capture_id": capture_id,
            "acquisition_id": expected_context["acquisition_id"],
            "profile": PROFILE,
            "scope": SCOPE,
            "repository": REPOSITORY,
            "source_commit": revision,
            "reference_workflow_name": REFERENCE_WORKFLOW_NAME,
            "reference_workflow_path": REFERENCE_WORKFLOW_PATH,
            "reference_run_id": expected_context["reference_run_id"],
            "reference_run_number": expected_context["reference_run_number"],
            "reference_run_attempt": 1,
            "collector_run_key": expected_context["collector_run_key"],
            "collector_execution_id": expected_context["collector_execution_id"],
            "subject_run_key": subject_run_key,
            "provider_run_key": provider_run_key,
            "capture_started_utc": capture_started,
            "capture_completed_utc": capture_completed,
            "manifest_created_utc": capture_completed,
        },
        "plan_binding": {
            "plan": _snapshot_descriptor(plan_snapshot, member=PREPARED_PLAN_MEMBER),
            "plan_diagnostic": _snapshot_descriptor(
                diagnostic_snapshot,
                member=PREPARED_PLAN_DIAGNOSTIC_MEMBER,
            ),
            "expected_plan_sha256": expected_plan,
        },
        "subject_dispatch_receipt": _snapshot_descriptor(
            acquisition_files[SUBJECT_DISPATCH_RECEIPT_MEMBER],
            member=ACQUISITION_PREFIX + SUBJECT_DISPATCH_RECEIPT_MEMBER,
        ),
        "provider_dispatch_receipt": _snapshot_descriptor(
            acquisition_files[PROVIDER_DISPATCH_RECEIPT_MEMBER],
            member=ACQUISITION_PREFIX + PROVIDER_DISPATCH_RECEIPT_MEMBER,
        ),
        "subject": subject,
        "provider": provider,
        "raw_response_bindings": _raw_response_bindings(
            acquisition_files=acquisition_files,
            index=index,
        ),
        "artifact_bindings": artifact_bindings,
        "carrier_member_bindings": provider_binding.carrier_member_bindings,
        "platform_counts": {
            "expected_job_count": EXPECTED_JOB_COUNT,
            "observed_job_count": EXPECTED_JOB_COUNT,
            "successful_job_count": EXPECTED_SUCCESSFUL_JOB_COUNT,
            "skipped_job_count": EXPECTED_SKIPPED_JOB_COUNT,
            "expected_step_template_count": EXPECTED_STEP_TEMPLATE_COUNT,
            "expected_instantiated_step_count": EXPECTED_INSTANTIATED_STEP_COUNT,
            "observed_declared_step_count": EXPECTED_INSTANTIATED_STEP_COUNT,
            "successful_declared_step_count": EXPECTED_SUCCESSFUL_STEP_COUNT,
            "skipped_declared_step_count": EXPECTED_SKIPPED_STEP_COUNT,
            "uninstantiated_step_template_count": EXPECTED_UNINSTANTIATED_STEP_COUNT,
            "raw_platform_step_record_count": platform["raw_platform_step_record_count"],
            "platform_lifecycle_record_count": platform["platform_lifecycle_record_count"],
            "subject_execution_record_count": EXPECTED_SUBJECT_EXECUTION_COUNT,
            "collector_execution_record_count": EXPECTED_COLLECTOR_EXECUTION_COUNT,
            "total_runtime_execution_record_count": EXPECTED_TOTAL_RUNTIME_EXECUTION_COUNT,
            "model_inference_record_count": EXPECTED_MODEL_INFERENCE_COUNT,
            "resource_measurement_record_count": EXPECTED_RESOURCE_MEASUREMENT_COUNT,
        },
        "collection_boundary": dict(EXPECTED_ACQUISITION_COLLECTION_BOUNDARY),
        "content_boundary": dict(CAPTURE_CONTENT_BOUNDARY),
        "member_inventory": {
            "manifest_scope": "all_capture_members_except_this_manifest",
            "member_count": len(inventory),
            "members": inventory,
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
    _schema_validate(schema, manifest, label="capture_manifest")
    manifest_bytes = _canonical_json_bytes(manifest)

    output, parent = _validate_output(output_path)
    output_sha256, output_size = _write_capture_zip(
        output=output,
        parent=parent,
        members=capture_members,
        manifest_bytes=manifest_bytes,
    )
    return {
        "tool": TOOL_ID,
        "version": TOOL_VERSION,
        "record_status": record_status,
        "ok": True,
        "output": str(output),
        "output_sha256": output_sha256,
        "output_size_bytes": output_size,
        "capture_manifest_sha256": _sha256(manifest_bytes),
        "capture_manifest_size_bytes": len(manifest_bytes),
        "capture_member_count": len(inventory) + 1,
        "subject_run_id": subject_run_id,
        "subject_run_attempt": 1,
        "provider_run_id": provider_run_id,
        "provider_run_attempt": 1,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [],
    }


def _failure(error: CaptureError, *, exit_code: int) -> dict[str, Any]:
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
        "exit_code": exit_code,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build one deterministic Step 5C whole-runtime observation capture carrier."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-diagnostic", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--acquisition-directory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--record-status",
        choices=("example", "observed"),
        default="observed",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        result = build_capture(
            repository_root=Path(args.repository_root),
            source_commit=str(args.source_commit),
            plan_path=Path(args.plan),
            plan_diagnostic_path=Path(args.plan_diagnostic),
            expected_plan_sha256=str(args.expected_plan_sha256),
            acquisition_directory=Path(args.acquisition_directory),
            output_path=Path(args.output),
            record_status=str(args.record_status),
        )
    except CaptureError as exc:
        sys.stdout.write(_canonical_json_bytes(_failure(exc, exit_code=1)).decode("utf-8"))
        return 1
    except Exception as exc:  # noqa: BLE001
        unexpected = CaptureError(
            "unexpected_capture_failure",
            type(exc).__name__,
            stage="internal",
        )
        sys.stdout.write(_canonical_json_bytes(_failure(unexpected, exit_code=2)).decode("utf-8"))
        return 2
    sys.stdout.write(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
