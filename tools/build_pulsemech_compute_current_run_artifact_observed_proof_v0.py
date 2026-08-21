#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"document_type":"pulsemech_compute_current_run_artifact_observed_proof",'
    '"errors":["isolated_python_runtime_required: launch with python -I"],'
    '"exit_kind":"python_runtime_boundary_error",'
    '"ok":false,'
    '"tool":"build_pulsemech_compute_current_run_artifact_observed_proof_v0",'
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
import errno
import hashlib
import importlib.util
import json
import os
import re
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import types
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

import jsonschema
import yaml


TOOL_NAME = "build_pulsemech_compute_current_run_artifact_observed_proof_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_current_run_artifact_observed_proof_v0"
DOCUMENT_TYPE = "pulsemech_compute_current_run_artifact_observed_proof"
PRODUCER_SOURCE_PATH = (
    "tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
)
PRODUCER_ID = "producer:pulsemech-current-run-artifact-observed-proof-v0"
PRODUCER_NAME = "PULSEmech current-run artifact-observed proof builder"
PRODUCTION_MODE = "current_run_artifact_observed_proof"
EXECUTION_PROFILE = "protected_linux_hpc_control_plane"
SUPPORTED_EXECUTION_PLATFORM = "linux"
SUPPORTED_OS_NAME = "posix"

INTAKE_REPORT_NAME = "candidate-bundle-intake-report.json"
CANDIDATE_MANIFEST_NAME = "candidate-output-manifest.json"
CARRIER_METADATA_NAME = "carrier.json"
EXPECTATION_NAME = "expectation.json"
PACKET_NAME = "subject-input-packet.json"
SOURCE_RESOLUTION_NAME = "source-run-resolution.json"
SOURCE_SELECTION_NAME = "source-artifact-selection.json"

REPORT_OUTPUT_NAME = "compute-binding-report.json"
PLAN_OUTPUT_NAME = "current-run-plan.json"
RELATION_OUTPUT_NAME = "planned-observed-relation.json"
MATERIALIZER_REPORT_NAME = "candidate-materializer-report.json"
FOLDED_STATUS_NAME = "folded-candidate-status.json"
PROOF_MANIFEST_NAME = "artifact-observed-proof-manifest.json"

PROOF_PAYLOAD_NAMES = (
    MATERIALIZER_REPORT_NAME,
    REPORT_OUTPUT_NAME,
    FOLDED_STATUS_NAME,
    PLAN_OUTPUT_NAME,
    RELATION_OUTPUT_NAME,
)

CANDIDATE_GATE_SET = "compute_planned_observed_relation_candidate"
CANDIDATE_GATES = (
    "compute_transition_path_complete",
    "compute_transition_authority_binding_ok",
    "compute_transition_unbound_mutation_absent",
)

SOURCE_WORKFLOW_NAME = "PULSE CI"
SOURCE_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
SOURCE_REF = "refs/heads/main"
PLAN_COMPONENT_SET_ID = "compute_current_run_artifact_observed_proof_v0"
PLAN_COMPONENT_ID = "pulse_check_gates_v0"
SUBJECT_CHECK_GATES_PATH = "PULSE_safe_pack_v0/tools/check_gates.py"
SUBJECT_POLICY_PATH = "pulse_gate_policy_v0.yml"
SUBJECT_REGISTRY_PATH = "pulse_gate_registry_v0.yml"

ROOT = Path(__file__).resolve().parents[1]

CONTROL_COMPONENT_SPECS: dict[str, tuple[str, int]] = {
    "proof_builder": (PRODUCER_SOURCE_PATH, 8 * 1024 * 1024),
    "candidate_bundle_loader": (
        "tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
        8 * 1024 * 1024,
    ),
    "subject_input_bridge": (
        "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py",
        8 * 1024 * 1024,
    ),
    "subject_input_schema": (
        "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "subject_input_validator": (
        "tools/check_pulsemech_compute_subject_input_packet_v0.py",
        8 * 1024 * 1024,
    ),
    "fixed_report_builder": (
        "tools/build_pulsemech_compute_binding_report_v0.py",
        8 * 1024 * 1024,
    ),
    "analyzer_core": (
        "tools/pulsemech_compute_binding_analyzer_core_v0.py",
        8 * 1024 * 1024,
    ),
    "report_schema": (
        "schemas/pulsemech_compute_binding_report_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "report_validator": (
        "tools/check_pulsemech_compute_binding_report_v0.py",
        8 * 1024 * 1024,
    ),
    "integration_planner": (
        "tools/plan_pulsemech_integration_v0.py",
        8 * 1024 * 1024,
    ),
    "integration_request_schema": (
        "schemas/pulsemech_integration_request_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "integration_component_manifest_schema": (
        "schemas/pulsemech_integration_component_manifest_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "integration_plan_schema": (
        "schemas/pulsemech_integration_plan_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "relation_builder": (
        "tools/build_pulsemech_compute_planned_observed_relation_v0.py",
        8 * 1024 * 1024,
    ),
    "relation_schema": (
        "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "relation_validator": (
        "tools/check_pulsemech_compute_planned_observed_relation_v0.py",
        8 * 1024 * 1024,
    ),
    "runtime_packet_schema": (
        "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
        8 * 1024 * 1024,
    ),
    "runtime_packet_validator": (
        "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
        8 * 1024 * 1024,
    ),
    "candidate_materializer": (
        "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
        8 * 1024 * 1024,
    ),
    "control_policy": ("pulse_gate_policy_v0.yml", 8 * 1024 * 1024),
    "control_registry": ("pulse_gate_registry_v0.yml", 8 * 1024 * 1024),
    "control_workflow": (
        ".github/workflows/pulse_ci.yml",
        8 * 1024 * 1024,
    ),
}

SUBJECT_COMPONENT_SPECS: dict[str, tuple[str, int]] = {
    "subject_workflow": (SOURCE_WORKFLOW_PATH, 8 * 1024 * 1024),
    "subject_policy": (SUBJECT_POLICY_PATH, 8 * 1024 * 1024),
    "subject_registry": (SUBJECT_REGISTRY_PATH, 8 * 1024 * 1024),
    "subject_check_gates": (SUBJECT_CHECK_GATES_PATH, 8 * 1024 * 1024),
}

CLOSED_AUTHORITY_BOUNDARY = {
    "activates_compute_gate": False,
    "candidate_only": True,
    "changes_gate_policy": False,
    "changes_gate_semantics": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "materializes_active_gate_state": False,
    "mutates_subject_run": False,
    "non_active": True,
    "proof_is_release_authority": False,
    "produces_runtime_observation": False,
    "write_mode": "external_proof_bundle_only",
    "writes_subject_status": False,
    "writes_target_repository": False,
}

CLOSED_CONTENT_BOUNDARY = {
    "analysis_level": "artifact_observed",
    "candidate_values_may_be_false": True,
    "contains_compute_budget": False,
    "contains_resource_measurement": False,
    "contains_runtime_observation": False,
    "contains_secret_material": False,
    "missing_and_unresolved_states_preserved": True,
    "raw_model_inputs_included": False,
    "raw_model_outputs_included": False,
}

EXPECTED_INTAKE_AUTHORITY = {
    "activates_compute_gate": False,
    "candidate_only": True,
    "changes_gate_policy": False,
    "changes_gate_semantics": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "intake_is_release_authority": False,
    "materializes_candidate_gate_state": False,
    "mutates_subject_run": False,
    "non_active": True,
    "provider_binding_only": True,
    "produces_runtime_observation": False,
    "produces_transition_relation": False,
    "write_mode": "verified_bundle_copy_only",
    "writes_target_repository": False,
}

EXPECTED_INTAKE_CONTENT = {
    "candidate_member_bytes_materialized": True,
    "contains_compute_budget": False,
    "contains_gate_result": False,
    "contains_release_authority": False,
    "contains_release_decision_created_by_intake": False,
    "contains_runtime_observation": False,
    "outer_provider_envelope_embedded_in_report": False,
    "provider_artifact_payload_mode": "external_envelope",
    "raw_model_inputs_included": False,
    "raw_model_outputs_included": False,
    "raw_secrets_included": False,
}

EXPECTED_RELATION_AUTHORITY = {
    "activates_compute_gate": False,
    "changes_gate_policy": False,
    "changes_gate_semantics": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "mutates_subject_run": False,
    "relation_record_is_release_authority": False,
    "write_mode": "relation_only",
    "writes_target_repository": False,
}

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulse_gate_policy_v0.yml",
        "pulse_gate_registry_v0.yml",
        "pulsemech_compute_planned_observed_relation_v0.json",
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
GIT_COMMAND_CONFIG = (
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

HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS = 180
DEFAULT_MAX_PROCESS_STDOUT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_PROCESS_STDERR_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_INPUT_FILE_BYTES = 8 * 1024 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_GIT_CONFIG_BYTES = 2 * 1024 * 1024


class ProofError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_kind: str = "proof_error",
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.exit_code = exit_code


class StrictJsonError(ValueError):
    pass


class StrictYamlError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise StrictYamlError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class ComponentBinding:
    role: str
    path: str
    source_revision: str
    source_sha256: str
    size_bytes: int
    bytes_value: bytes
    worktree_path: Path


@dataclass(frozen=True)
class CapturedFile:
    name: str
    bytes_value: bytes
    sha256: str
    size_bytes: int
    inode_identity: tuple[int, int]
    full_identity: tuple[Any, ...]


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class InputBundle:
    intake_report: dict[str, Any]
    files: dict[str, CapturedFile]
    carrier_name: str
    source_subject: dict[str, Any]


def render_json(value: Any) -> bytes:
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


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _blob_sha1(value: bytes) -> str:
    header = f"blob {len(value)}\0".encode("ascii")
    return hashlib.sha1(header + value).hexdigest()


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _inode_identity(value: os.stat_result) -> tuple[int, int]:
    return (int(value.st_dev), int(value.st_ino))


def _full_identity(value: os.stat_result) -> tuple[Any, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        pass
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _paths_overlap(left: Path, right: Path) -> bool:
    return (
        _same_target(left, right)
        or _path_is_within(left, right)
        or _path_is_within(right, left)
    )


def _require_supported_execution_platform() -> None:
    if sys.platform != SUPPORTED_EXECUTION_PLATFORM or os.name != SUPPORTED_OS_NAME:
        raise ProofError(
            "unsupported_execution_platform: "
            f"profile={EXECUTION_PROFILE!r} sys_platform={sys.platform!r} "
            f"os_name={os.name!r}",
            exit_kind="platform_boundary_error",
        )
    required = (
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        os.open in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.rename in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.mkdir in os.supports_dir_fd,
        os.rmdir in os.supports_dir_fd,
    )
    if not all(required):
        raise ProofError(
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
        raise ProofError(f"{label}_invalid: {value!r}", exit_kind="input_error")
    return value


def _positive_int(value: Any, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ProofError(f"{label}_invalid: {value!r}", exit_kind="input_error")
    return value


def _canonical_sha40(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ProofError(f"{label}_invalid_sha40: {value!r}", exit_kind="input_error")
    return value


def _canonical_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ProofError(f"{label}_invalid_sha256: {value!r}", exit_kind="input_error")
    return value


def _canonical_repository(value: Any, *, label: str) -> str:
    text = _non_empty_text(value, label=label)
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text) is None:
        raise ProofError(f"{label}_invalid_repository: {text!r}")
    return text


def _canonical_relative_path(value: Any, *, label: str) -> str:
    text = _non_empty_text(value, label=label)
    if "\\" in text:
        raise ProofError(f"{label}_contains_backslash: {text!r}")
    path = PurePosixPath(text)
    if path.is_absolute() or path.as_posix() != text or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise ProofError(f"{label}_unsafe_relative_path: {text!r}")
    return text


def _parse_json_bytes(
    value: bytes,
    *,
    label: str,
    canonical_required: bool = True,
) -> dict[str, Any]:
    if value.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"{label}_utf8_bom_not_permitted")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise StrictJsonError(f"{label}_duplicate_key: {key!r}")
            result[key] = item
        return result

    def reject_non_finite(item: str) -> None:
        raise StrictJsonError(f"{label}_non_finite_value: {item}")

    try:
        parsed = json.loads(
            value.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_non_finite,
        )
    except StrictJsonError:
        raise
    except Exception as exc:
        raise StrictJsonError(f"{label}_invalid_json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise StrictJsonError(f"{label}_not_object")
    if canonical_required and value != render_json(parsed):
        raise StrictJsonError(f"{label}_not_canonical_json")
    return parsed


def _parse_yaml_bytes(value: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = yaml.load(
            value.decode("utf-8", errors="strict"),
            Loader=UniqueKeyLoader,
        )
    except Exception as exc:
        raise StrictYamlError(f"{label}_invalid_yaml: {exc}") from exc
    if not isinstance(parsed, dict):
        raise StrictYamlError(f"{label}_not_object")
    return parsed


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    label: str,
) -> None:
    observed = set(value)
    if observed != expected:
        raise ProofError(
            f"{label}_key_set_mismatch: missing={sorted(expected - observed)!r} "
            f"unexpected={sorted(observed - expected)!r}"
        )


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProofError(f"{label}_not_object")
    return value


def _require_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProofError(f"{label}_not_array")
    return value


def _write_all(fd: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(fd, value[offset:])
        if written <= 0:
            raise ProofError("output_write_returned_zero", exit_kind="output_error")
        offset += written


def _read_fd_bytes(fd: int, *, maximum: int, label: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, min(HASH_CHUNK_BYTES, maximum + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise ProofError(
                f"{label}_too_large: maximum={maximum}",
                exit_kind="resource_boundary_error",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _open_directory_chain(path: Path, *, label: str) -> tuple[int, int, str, tuple[int, int]]:
    candidate = _normalized_absolute_path(path)
    if not candidate.is_absolute() or not candidate.parts:
        raise ProofError(f"{label}_not_absolute: {candidate}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    current_fd: int | None = None
    parent_fd: int | None = None
    try:
        current_fd = os.open(candidate.parts[0], flags)
        for index, part in enumerate(candidate.parts[1:], start=1):
            if part in {"", ".", ".."}:
                raise ProofError(f"{label}_unsafe_component: {part!r}")
            next_fd = os.open(part, flags, dir_fd=current_fd)
            if index == len(candidate.parts) - 1:
                parent_fd = current_fd
                current_fd = next_fd
                break
            os.close(current_fd)
            current_fd = next_fd
        if parent_fd is None:
            parent_fd = os.dup(current_fd)
        metadata = os.fstat(current_fd)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ProofError(f"{label}_not_directory: {candidate}")
        return current_fd, parent_fd, candidate.name, _inode_identity(metadata)
    except OSError as exc:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError:
                pass
        raise ProofError(
            f"{label}_open_failed: {candidate}: {exc}",
            exit_kind="path_boundary_error",
        ) from exc


class DirectorySnapshot:
    def __init__(self, path: Path, *, label: str) -> None:
        self.path = _normalized_absolute_path(path)
        self.label = label
        self.fd, self.parent_fd, self.name, self.identity = _open_directory_chain(
            self.path,
            label=label,
        )
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        os.close(self.fd)
        os.close(self.parent_fd)

    def __enter__(self) -> "DirectorySnapshot":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def names(self) -> set[str]:
        try:
            values = os.listdir(self.fd)
        except OSError as exc:
            raise ProofError(f"{self.label}_list_failed: {exc}") from exc
        result: set[str] = set()
        for value in values:
            name = _canonical_relative_path(value, label=f"{self.label}_entry")
            if "/" in name:
                raise ProofError(f"{self.label}_nested_entry_rejected: {name}")
            if name in result:
                raise ProofError(f"{self.label}_duplicate_entry: {name}")
            result.add(name)
        return result

    def capture_file(self, name: str, *, maximum: int) -> CapturedFile:
        safe = _canonical_relative_path(name, label=f"{self.label}_file")
        if "/" in safe:
            raise ProofError(f"{self.label}_nested_file_rejected: {safe}")
        flags = os.O_RDONLY | os.O_NOFOLLOW
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        fd: int | None = None
        try:
            fd = os.open(safe, flags, dir_fd=self.fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ProofError(f"{self.label}_file_not_single_regular: {safe}")
            if before.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                raise ProofError(f"{self.label}_file_not_finalized_read_only: {safe}")
            value = _read_fd_bytes(fd, maximum=maximum, label=safe)
            after = os.fstat(fd)
            if _full_identity(before) != _full_identity(after):
                raise ProofError(f"{self.label}_file_changed_during_capture: {safe}")
            path_metadata = os.stat(safe, dir_fd=self.fd, follow_symlinks=False)
            if _inode_identity(path_metadata) != _inode_identity(after):
                raise ProofError(f"{self.label}_file_path_replaced: {safe}")
            return CapturedFile(
                name=safe,
                bytes_value=value,
                sha256=sha256_bytes(value),
                size_bytes=len(value),
                inode_identity=_inode_identity(after),
                full_identity=_full_identity(after),
            )
        except OSError as exc:
            raise ProofError(f"{self.label}_file_capture_failed: {safe}: {exc}") from exc
        finally:
            if fd is not None:
                os.close(fd)

    def verify(self) -> None:
        current = os.fstat(self.fd)
        if _inode_identity(current) != self.identity:
            raise ProofError(f"{self.label}_directory_identity_changed")
        path_metadata = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
        if _inode_identity(path_metadata) != self.identity:
            raise ProofError(f"{self.label}_directory_path_replaced")


def _validate_owned_private_directory(path: Path, *, label: str) -> Path:
    candidate = _normalized_absolute_path(path)
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise ProofError(f"{label}_unavailable: {candidate}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ProofError(f"{label}_not_regular_directory: {candidate}")
    if metadata.st_uid != os.getuid():
        raise ProofError(f"{label}_not_owned_by_current_user: {candidate}")
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ProofError(f"{label}_group_or_world_writable: {candidate}")
    return candidate


def _validate_trusted_executable(path: Path) -> Path:
    if not path.is_absolute():
        raise ProofError(f"trusted_git_not_absolute: {path}")
    normalized = _normalized_absolute_path(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ProofError(f"trusted_git_unresolvable: {path}: {exc}") from exc
    if normalized != resolved or path.is_symlink() or not resolved.is_file():
        raise ProofError(f"trusted_git_symlink_or_alias_rejected: {path}")
    if not os.access(resolved, os.X_OK):
        raise ProofError(f"trusted_git_not_executable: {resolved}")
    cursor = resolved
    while True:
        metadata = cursor.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ProofError(f"trusted_git_symlink_component: {cursor}")
        if metadata.st_uid != 0:
            raise ProofError(f"trusted_git_non_root_owned_component: {cursor}")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ProofError(f"trusted_git_writable_component: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    return resolved


def _sanitized_environment(*, trusted_git: Path | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in GIT_ENV_ALLOWLIST:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    env.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    if trusted_git is not None:
        env["PATH"] = str(trusted_git.parent)
    return env


def _run_bounded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> ProcessResult:
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise ProofError(f"process_start_failed: {command!r}: {exc}") from exc
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ProofError("process_pipe_unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", max_stdout_bytes))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", max_stderr_bytes))
    buffers: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProofError(
                    f"process_timeout: command={command!r}",
                    exit_kind="process_error",
                )
            events = selector.select(min(remaining, 0.25))
            if not events and process.poll() is not None:
                events = selector.select(0)
                if not events:
                    break
            for key, _mask in events:
                label, maximum = key.data
                try:
                    chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffer = buffers[label]
                if len(buffer) + len(chunk) > maximum:
                    raise ProofError(
                        f"process_{label}_limit_exceeded: maximum={maximum}",
                        exit_kind="resource_boundary_error",
                    )
                buffer.extend(chunk)
        remaining = max(0.0, deadline - time.monotonic())
        returncode = process.wait(timeout=remaining)
        return ProcessResult(
            returncode=returncode,
            stdout=bytes(buffers["stdout"]),
            stderr=bytes(buffers["stderr"]),
        )
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            process.kill()
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()


def _select_trusted_git(explicit: str | None) -> Path:
    candidates = (
        (Path(explicit),)
        if explicit is not None
        else LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    )
    failures: list[str] = []
    for candidate in candidates:
        if not candidate.exists():
            failures.append(f"unavailable:{candidate}")
            continue
        try:
            trusted = _validate_trusted_executable(candidate)
            result = _run_bounded_process(
                [str(trusted), "--no-lazy-fetch", "version"],
                cwd=Path("/"),
                env=_sanitized_environment(trusted_git=trusted),
                timeout_seconds=30,
                max_stdout_bytes=64 * 1024,
                max_stderr_bytes=64 * 1024,
            )
            if result.returncode != 0:
                raise ProofError(
                    "trusted_git_missing_no_lazy_fetch_capability: "
                    + result.stderr.decode("utf-8", errors="replace")
                )
            return trusted
        except Exception as exc:
            failures.append(f"{candidate}:{exc}")
    raise ProofError(
        "no_trusted_git_with_required_capability: " + " | ".join(failures),
        exit_kind="git_boundary_error",
    )


def _git_command(
    *,
    git: Path,
    repository_root: Path,
    arguments: Sequence[str],
) -> list[str]:
    command = [
        str(git),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
    ]
    for key, value in GIT_COMMAND_CONFIG:
        command.extend(("-c", f"{key}={value}"))
    command.extend(("-c", f"safe.directory={repository_root}"))
    command.extend(("-C", str(repository_root)))
    command.extend(arguments)
    return command


def _run_git(
    *,
    git: Path,
    repository_root: Path,
    arguments: Sequence[str],
    maximum: int = MAX_GIT_OUTPUT_BYTES,
) -> bytes:
    result = _run_bounded_process(
        _git_command(
            git=git,
            repository_root=repository_root,
            arguments=arguments,
        ),
        cwd=repository_root,
        env=_sanitized_environment(trusted_git=git),
        timeout_seconds=60,
        max_stdout_bytes=maximum,
        max_stderr_bytes=1024 * 1024,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProofError(
            f"git_command_failed: arguments={list(arguments)!r} detail={detail!r}",
            exit_kind="git_boundary_error",
        )
    return result.stdout


def _decode_single_line(value: bytes, *, label: str) -> str:
    try:
        text = value.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise ProofError(f"{label}_invalid_utf8: {exc}") from exc
    if not text or "\x00" in text or "\n" in text or "\r" in text:
        raise ProofError(f"{label}_invalid_single_line: {text!r}")
    return text


def _verify_repository(
    *,
    git: Path,
    root: Path,
    expected_revision: str,
    label: str,
) -> Path:
    repository_root = _normalized_absolute_path(root)
    if repository_root.is_symlink() or not repository_root.is_dir():
        raise ProofError(f"{label}_not_directory: {repository_root}")
    top = Path(
        _decode_single_line(
            _run_git(
                git=git,
                repository_root=repository_root,
                arguments=("rev-parse", "--show-toplevel"),
            ),
            label=f"{label}_toplevel",
        )
    ).resolve(strict=True)
    if not _same_target(top, repository_root):
        raise ProofError(
            f"{label}_root_mismatch: expected={repository_root} actual={top}"
        )
    head = _decode_single_line(
        _run_git(
            git=git,
            repository_root=repository_root,
            arguments=("rev-parse", "HEAD"),
        ),
        label=f"{label}_head",
    ).lower()
    if head != expected_revision:
        raise ProofError(
            f"{label}_revision_mismatch: expected={expected_revision} actual={head}"
        )
    shallow = _decode_single_line(
        _run_git(
            git=git,
            repository_root=repository_root,
            arguments=("rev-parse", "--is-shallow-repository"),
        ),
        label=f"{label}_shallow",
    )
    if shallow != "false":
        raise ProofError(f"{label}_shallow_repository_rejected")
    config = _run_git(
        git=git,
        repository_root=repository_root,
        arguments=("config", "--local", "--null", "--list"),
        maximum=MAX_GIT_CONFIG_BYTES,
    )
    entries = [item for item in config.split(b"\x00") if item]
    for raw in entries:
        text = raw.decode("utf-8", errors="replace").casefold()
        if (
            "promisor" in text
            or "partialclone" in text
            or text.startswith("core.sshcommand")
            or text.startswith("url.") and ".insteadof" in text
        ):
            raise ProofError(f"{label}_unsafe_git_config: {text!r}")
    git_dir_text = _decode_single_line(
        _run_git(
            git=git,
            repository_root=repository_root,
            arguments=("rev-parse", "--absolute-git-dir"),
        ),
        label=f"{label}_git_dir",
    )
    git_dir = Path(git_dir_text)
    for name in (
        Path("objects/info/alternates"),
        Path("objects/info/http-alternates"),
        Path("shallow"),
    ):
        if (git_dir / name).exists():
            raise ProofError(f"{label}_unsafe_git_state: {name.as_posix()}")
    return repository_root


def _verify_committed_worktree_file(
    *,
    git: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    role: str,
    maximum: int,
) -> ComponentBinding:
    path_text = _canonical_relative_path(repository_path, label=f"{role}_path")
    object_spec = f"{revision}:{path_text}"
    object_type = _decode_single_line(
        _run_git(
            git=git,
            repository_root=repository_root,
            arguments=("cat-file", "-t", object_spec),
        ),
        label=f"{role}_object_type",
    )
    if object_type != "blob":
        raise ProofError(f"{role}_object_not_blob: {object_type!r}")
    object_size = int(
        _decode_single_line(
            _run_git(
                git=git,
                repository_root=repository_root,
                arguments=("cat-file", "-s", object_spec),
            ),
            label=f"{role}_object_size",
        ),
        10,
    )
    if object_size < 0 or object_size > maximum:
        raise ProofError(
            f"{role}_object_size_invalid: size={object_size} maximum={maximum}"
        )
    committed = _run_git(
        git=git,
        repository_root=repository_root,
        arguments=("cat-file", "blob", object_spec),
        maximum=maximum,
    )
    if len(committed) != object_size:
        raise ProofError(f"{role}_git_blob_size_mismatch")
    expected_oid = _decode_single_line(
        _run_git(
            git=git,
            repository_root=repository_root,
            arguments=("rev-parse", object_spec),
        ),
        label=f"{role}_object_id",
    )
    if _blob_sha1(committed) != expected_oid:
        raise ProofError(f"{role}_git_object_rehash_mismatch")
    worktree_path = repository_root / PurePosixPath(path_text)
    cursor = repository_root
    for part in PurePosixPath(path_text).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ProofError(f"{role}_worktree_symlink_rejected: {cursor}")
    try:
        metadata = worktree_path.lstat()
    except OSError as exc:
        raise ProofError(f"{role}_worktree_file_unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ProofError(f"{role}_worktree_not_regular")
    worktree = worktree_path.read_bytes()
    if worktree != committed:
        raise ProofError(f"{role}_committed_worktree_mismatch")
    return ComponentBinding(
        role=role,
        path=path_text,
        source_revision=revision,
        source_sha256=sha256_bytes(committed),
        size_bytes=len(committed),
        bytes_value=committed,
        worktree_path=worktree_path,
    )


def _verify_component_set(
    *,
    git: Path,
    repository_root: Path,
    revision: str,
    specs: Mapping[str, tuple[str, int]],
) -> dict[str, ComponentBinding]:
    result: dict[str, ComponentBinding] = {}
    for role, (path, maximum) in specs.items():
        result[role] = _verify_committed_worktree_file(
            git=git,
            repository_root=repository_root,
            revision=revision,
            repository_path=path,
            role=role,
            maximum=maximum,
        )
    return result


def _reverify_component_set(
    *,
    git: Path,
    repository_root: Path,
    revision: str,
    expected: Mapping[str, ComponentBinding],
) -> None:
    for role, binding in expected.items():
        observed = _verify_committed_worktree_file(
            git=git,
            repository_root=repository_root,
            revision=revision,
            repository_path=binding.path,
            role=role,
            maximum=max(binding.size_bytes, 1),
        )
        if (
            observed.source_sha256 != binding.source_sha256
            or observed.size_bytes != binding.size_bytes
            or observed.bytes_value != binding.bytes_value
        ):
            raise ProofError(f"component_changed_during_proof: {role}")


def _load_module_from_component(
    component: ComponentBinding,
    *,
    module_name: str,
) -> types.ModuleType:
    try:
        code = compile(
            component.bytes_value,
            str(component.worktree_path),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise ProofError(f"component_compile_failed: {component.role}: {exc}") from exc
    previous = sys.modules.get(module_name)
    had_previous = module_name in sys.modules
    module = types.ModuleType(module_name)
    module.__file__ = str(component.worktree_path)
    module.__package__ = module_name.rpartition(".")[0]
    module.__cached__ = None
    module.__loader__ = None
    module.__spec__ = importlib.util.spec_from_loader(module_name, loader=None)
    sys.modules[module_name] = module
    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[module_name] = previous
        else:
            sys.modules.pop(module_name, None)
        raise ProofError(
            f"component_execution_failed: {component.role}: {type(exc).__name__}: {exc}"
        ) from exc
    return module


def _capture_intake_directory(
    path: Path,
    *,
    maximum_file_bytes: int,
) -> InputBundle:
    with DirectorySnapshot(path, label="intake_directory") as directory:
        names = directory.names()
        if INTAKE_REPORT_NAME not in names:
            raise ProofError("intake_report_missing")
        report_capture = directory.capture_file(
            INTAKE_REPORT_NAME,
            maximum=MAX_JSON_BYTES,
        )
        report = _parse_json_bytes(
            report_capture.bytes_value,
            label="intake_report",
        )
        expected_top = {
            "authority_boundary",
            "bundle_identity",
            "content_boundary",
            "document_type",
            "errors",
            "files",
            "inner_carrier_verification",
            "ok",
            "output_layout",
            "producer",
            "provider_binding",
            "record_status",
            "schema_version",
            "source_subject",
        }
        _require_exact_keys(report, expected_top, label="intake_report")
        if report.get("schema_version") != (
            "pulsemech_compute_current_run_export_candidate_bundle_intake_v0"
        ):
            raise ProofError("intake_report_schema_version_mismatch")
        if report.get("document_type") != (
            "pulsemech_compute_current_run_export_candidate_bundle_intake"
        ):
            raise ProofError("intake_report_document_type_mismatch")
        if report.get("record_status") != "observed":
            raise ProofError("intake_report_record_status_not_observed")
        if report.get("ok") is not True or report.get("errors") != []:
            raise ProofError("intake_report_not_ok_or_errors_present")
        if report.get("authority_boundary") != EXPECTED_INTAKE_AUTHORITY:
            raise ProofError("intake_report_authority_boundary_mismatch")
        if report.get("content_boundary") != EXPECTED_INTAKE_CONTENT:
            raise ProofError("intake_report_content_boundary_mismatch")

        bundle_identity = _require_object(
            report.get("bundle_identity"),
            label="intake_bundle_identity",
        )
        carrier_name = _canonical_relative_path(
            bundle_identity.get("carrier_name"),
            label="intake_carrier_name",
        )
        if "/" in carrier_name or not carrier_name.endswith(".zip"):
            raise ProofError(f"intake_carrier_name_invalid: {carrier_name!r}")
        rows = _require_list(report.get("files"), label="intake_files")
        declared: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(rows):
            row = _require_object(item, label=f"intake_file_{index}")
            _require_exact_keys(
                row,
                {"path", "role", "sha256", "size_bytes"},
                label=f"intake_file_{index}",
            )
            name = _canonical_relative_path(
                row.get("path"),
                label=f"intake_file_path_{index}",
            )
            if "/" in name or name in declared:
                raise ProofError(f"intake_file_path_invalid_or_duplicate: {name}")
            declared[name] = {
                "role": _non_empty_text(row.get("role"), label="intake_file_role"),
                "sha256": _canonical_sha256(
                    row.get("sha256"),
                    label=f"intake_file_sha256_{name}",
                ),
                "size_bytes": _positive_int(
                    row.get("size_bytes"),
                    label=f"intake_file_size_{name}",
                ),
            }
        expected_candidate_names = {
            CANDIDATE_MANIFEST_NAME,
            CARRIER_METADATA_NAME,
            EXPECTATION_NAME,
            PACKET_NAME,
            SOURCE_RESOLUTION_NAME,
            SOURCE_SELECTION_NAME,
            carrier_name,
        }
        if set(declared) != expected_candidate_names:
            raise ProofError(
                "intake_candidate_file_set_mismatch: "
                f"missing={sorted(expected_candidate_names - set(declared))!r} "
                f"unexpected={sorted(set(declared) - expected_candidate_names)!r}"
            )
        expected_directory_names = expected_candidate_names | {INTAKE_REPORT_NAME}
        if names != expected_directory_names:
            raise ProofError(
                "intake_directory_closure_failed: "
                f"missing={sorted(expected_directory_names - names)!r} "
                f"unexpected={sorted(names - expected_directory_names)!r}"
            )
        files: dict[str, CapturedFile] = {INTAKE_REPORT_NAME: report_capture}
        for name in sorted(expected_candidate_names):
            captured = directory.capture_file(name, maximum=maximum_file_bytes)
            row = declared[name]
            if (
                captured.sha256 != row["sha256"]
                or captured.size_bytes != row["size_bytes"]
            ):
                raise ProofError(f"intake_file_identity_mismatch: {name}")
            files[name] = captured
        output_layout = _require_object(
            report.get("output_layout"),
            label="intake_output_layout",
        )
        if output_layout.get("intake_report_path") != INTAKE_REPORT_NAME:
            raise ProofError("intake_output_layout_report_path_mismatch")
        if output_layout.get("verified_candidate_files") != sorted(
            expected_candidate_names
        ):
            raise ProofError("intake_output_layout_candidate_files_mismatch")
        subject = _require_object(
            report.get("source_subject"),
            label="intake_source_subject",
        )
        identity_checks = {
            "candidate_manifest_sha256": files[CANDIDATE_MANIFEST_NAME].sha256,
            "candidate_manifest_size_bytes": files[CANDIDATE_MANIFEST_NAME].size_bytes,
            "carrier_name": carrier_name,
            "carrier_sha256": files[carrier_name].sha256,
            "carrier_size_bytes": files[carrier_name].size_bytes,
            "expectation_sha256": files[EXPECTATION_NAME].sha256,
            "packet_sha256": files[PACKET_NAME].sha256,
            "source_run_attempt": subject.get("source_run_attempt"),
            "source_run_id": subject.get("source_run_id"),
            "subject_revision": subject.get("subject_revision"),
        }
        for field, expected in identity_checks.items():
            if bundle_identity.get(field) != expected:
                raise ProofError(
                    f"intake_bundle_identity_{field}_mismatch: "
                    f"expected={expected!r} actual={bundle_identity.get(field)!r}"
                )
        directory.verify()
        return InputBundle(
            intake_report=report,
            files=files,
            carrier_name=carrier_name,
            source_subject=subject,
        )


def _verify_intake_bindings(
    *,
    bundle: InputBundle,
    subject_repository: str,
    subject_revision: str,
    control_repository: str,
    control_revision: str,
    components: Mapping[str, ComponentBinding],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subject = bundle.source_subject
    exact_subject = {
        "repository": subject_repository,
        "subject_revision": subject_revision,
        "workflow_name": SOURCE_WORKFLOW_NAME,
        "workflow_path": SOURCE_WORKFLOW_PATH,
    }
    for field, expected in exact_subject.items():
        if subject.get(field) != expected:
            raise ProofError(
                f"intake_subject_{field}_mismatch: expected={expected!r} "
                f"actual={subject.get(field)!r}"
            )
    _positive_int(subject.get("source_run_id"), label="source_run_id")
    _positive_int(subject.get("source_run_number"), label="source_run_number")
    _positive_int(subject.get("source_run_attempt"), label="source_run_attempt")
    _non_empty_text(subject.get("source_run_key"), label="source_run_key")
    _non_empty_text(subject.get("release_candidate_id"), label="release_candidate_id")

    producer = _require_object(
        bundle.intake_report.get("producer"),
        label="intake_producer",
    )
    loader = components["candidate_bundle_loader"]
    expected_producer = {
        "producer_id": (
            "producer:pulsemech-current-run-export-candidate-bundle-intake-v0"
        ),
        "producer_name": "PULSEmech current-run export candidate bundle intake",
        "producer_source": loader.path,
        "producer_source_revision": control_revision,
        "producer_source_sha256": loader.source_sha256,
        "producer_version": "0.1.0",
        "production_mode": "current_run_export_candidate_bundle_intake",
    }
    for field, expected in expected_producer.items():
        if producer.get(field) != expected:
            raise ProofError(
                f"intake_producer_{field}_mismatch: expected={expected!r} "
                f"actual={producer.get(field)!r}"
            )

    expectation = _parse_json_bytes(
        bundle.files[EXPECTATION_NAME].bytes_value,
        label="observed_expectation",
    )
    packet = _parse_json_bytes(
        bundle.files[PACKET_NAME].bytes_value,
        label="observed_subject_input_packet",
    )
    packet_subject = _require_object(packet.get("subject"), label="packet_subject")
    if packet_subject.get("repository") != subject_repository:
        raise ProofError("packet_subject_repository_mismatch")
    if packet_subject.get("source_commit") != subject_revision:
        raise ProofError("packet_subject_revision_mismatch")
    if packet_subject.get("subject_run_key") != subject.get("source_run_key"):
        raise ProofError("packet_subject_run_key_mismatch")
    if packet.get("record_status") != "observed":
        raise ProofError("packet_record_status_not_observed")
    if expectation.get("record_status") != "observed":
        raise ProofError("expectation_record_status_not_observed")
    trusted = _require_object(
        expectation.get("trusted_control_plane"),
        label="expectation_trusted_control_plane",
    )
    if (
        trusted.get("repository") != control_repository
        or trusted.get("revision") != control_revision
    ):
        raise ProofError("expectation_control_plane_binding_mismatch")
    return expectation, packet


def _validate_json_schema(
    *,
    schema_bytes: bytes,
    value: dict[str, Any],
    label: str,
) -> None:
    schema = _parse_json_bytes(
        schema_bytes,
        label=f"{label}_schema",
        canonical_required=False,
    )
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise ProofError(f"{label}_schema_invalid: {exc}") from exc
    errors = sorted(
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(value),
        key=lambda item: (
            tuple(str(part) for part in item.path),
            item.message,
        ),
    )
    if errors:
        raise ProofError(
            f"{label}_schema_validation_failed: "
            + " | ".join(
                f"{list(error.path)}:{error.message}" for error in errors
            )
        )


def _write_file_at(
    directory_fd: int,
    name: str,
    value: bytes,
    *,
    mode: int,
) -> None:
    safe = _canonical_relative_path(name, label="output_file_name")
    if "/" in safe:
        raise ProofError(f"nested_output_file_rejected: {safe}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    fd = os.open(safe, flags, mode, dir_fd=directory_fd)
    try:
        _write_all(fd, value)
        os.fsync(fd)
        os.fchmod(fd, mode)
    finally:
        os.close(fd)


def _capture_output_file_at(
    directory_fd: int,
    name: str,
    *,
    maximum: int,
    require_canonical_json: bool,
) -> CapturedFile:
    safe = _canonical_relative_path(name, label="output_file_name")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    fd = os.open(safe, flags, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ProofError(f"output_file_not_single_regular: {safe}")
        value = _read_fd_bytes(fd, maximum=maximum, label=safe)
        after = os.fstat(fd)
        if _full_identity(before) != _full_identity(after):
            raise ProofError(f"output_file_changed_during_capture: {safe}")
        path_metadata = os.stat(safe, dir_fd=directory_fd, follow_symlinks=False)
        if _inode_identity(path_metadata) != _inode_identity(after):
            raise ProofError(f"output_file_path_replaced: {safe}")
        if require_canonical_json:
            _parse_json_bytes(value, label=safe, canonical_required=True)
        return CapturedFile(
            name=safe,
            bytes_value=value,
            sha256=sha256_bytes(value),
            size_bytes=len(value),
            inode_identity=_inode_identity(after),
            full_identity=_full_identity(after),
        )
    finally:
        os.close(fd)


def _chmod_file_at(directory_fd: int, name: str, mode: int) -> None:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    fd = os.open(name, flags, dir_fd=directory_fd)
    try:
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _process_or_fail(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
    label: str,
    max_stdout: int = DEFAULT_MAX_PROCESS_STDOUT_BYTES,
    max_stderr: int = DEFAULT_MAX_PROCESS_STDERR_BYTES,
    accepted_exit_codes: set[int] | None = None,
) -> ProcessResult:
    result = _run_bounded_process(
        command,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        max_stdout_bytes=max_stdout,
        max_stderr_bytes=max_stderr,
    )
    accepted = {0} if accepted_exit_codes is None else accepted_exit_codes
    if result.returncode not in accepted:
        raise ProofError(
            f"{label}_failed: exit={result.returncode} "
            f"stdout={result.stdout.decode('utf-8', errors='replace')!r} "
            f"stderr={result.stderr.decode('utf-8', errors='replace')!r}",
            exit_kind="process_error",
        )
    return result


def _copy_captured_input(
    directory_fd: int,
    captured: CapturedFile,
    *,
    output_name: str | None = None,
) -> str:
    name = output_name or captured.name
    _write_file_at(directory_fd, name, captured.bytes_value, mode=0o400)
    return name


def _build_dynamic_plan_inputs(
    *,
    packet: dict[str, Any],
    subject_components: Mapping[str, ComponentBinding],
) -> tuple[dict[str, Any], dict[str, Any]]:
    subject = _require_object(packet.get("subject"), label="packet_subject")
    active_sets = _require_list(
        subject.get("active_policy_sets"),
        label="subject_active_policy_sets",
    )
    if (
        not active_sets
        or any(not isinstance(item, str) or not item for item in active_sets)
        or len(active_sets) != len(set(active_sets))
    ):
        raise ProofError("subject_active_policy_sets_invalid")
    policy_component = subject_components["subject_policy"]
    policy = _parse_yaml_bytes(policy_component.bytes_value, label="subject_policy")
    gates_root = policy.get("gates")
    if not isinstance(gates_root, dict):
        raise ProofError("subject_policy_gates_not_object")
    for gate_set in active_sets:
        gates = gates_root.get(gate_set)
        if (
            not isinstance(gates, list)
            or not gates
            or any(not isinstance(gate, str) or not gate for gate in gates)
            or len(gates) != len(set(gates))
        ):
            raise ProofError(f"subject_policy_gate_set_invalid: {gate_set}")
    repository = _canonical_repository(subject.get("repository"), label="subject_repository")
    run_id = _positive_int(subject.get("workflow_run_id"), label="subject_run_id")
    run_attempt = _positive_int(
        subject.get("workflow_run_attempt"),
        label="subject_run_attempt",
    )
    request = {
        "component_sets": [PLAN_COMPONENT_SET_ID],
        "existing_file_policy": {
            "different": "conflict",
            "identical": "preserve",
            "non_regular": "conflict",
            "symlink": "conflict",
        },
        "request_id": (
            f"compute-current-run-artifact-observed-proof-{run_id}-{run_attempt}-v0"
        ),
        "request_type": "pulsemech_integration_request",
        "schema_version": "pulsemech_integration_request_v0",
        "target_repository": {
            "ci_provider": "github_actions",
            "default_branch": "main",
            "repository_id": repository,
        },
        "write_mode": "plan_only",
    }
    manifest = {
        "component_sets": [
            {
                "authority_boundary": (
                    "Planning only; no repository write, gate result, release "
                    "decision, or release-authority effect."
                ),
                "declared_gate_sets": list(active_sets),
                "description": (
                    "Current-run artifact-observed proof planning surface."
                ),
                "id": PLAN_COMPONENT_SET_ID,
                "root_components": [PLAN_COMPONENT_ID],
                "supported_ci_providers": ["github_actions"],
            }
        ],
        "components": [
            {
                "id": PLAN_COMPONENT_ID,
                "kind": "file",
                "requires": [],
                "source_path": SUBJECT_CHECK_GATES_PATH,
                "target_path": SUBJECT_CHECK_GATES_PATH,
            }
        ],
        "manifest_type": "pulsemech_integration_component_manifest",
        "policy_path": SUBJECT_POLICY_PATH,
        "schema_version": "pulsemech_integration_component_manifest_v0",
        "source_repository": repository,
    }
    return request, manifest


def _validate_report(
    report: dict[str, Any],
    *,
    packet: dict[str, Any],
    components: Mapping[str, ComponentBinding],
    analysis_run_key: str,
) -> None:
    if report.get("schema_version") != "pulsemech_compute_binding_report_v0":
        raise ProofError("compute_report_schema_version_mismatch")
    if report.get("report_type") != "pulsemech_compute_binding_report":
        raise ProofError("compute_report_type_mismatch")
    if report.get("record_status") != "observed":
        raise ProofError("compute_report_record_status_not_observed")
    if report.get("ok") is not True or report.get("errors") != []:
        raise ProofError("compute_report_not_ok_or_errors_present")
    analysis = _require_object(report.get("analysis_boundary"), label="report_analysis")
    packet_subject = _require_object(packet.get("subject"), label="packet_subject")
    if analysis.get("analysis_level") != "artifact_observed":
        raise ProofError("compute_report_analysis_level_mismatch")
    if analysis.get("analysis_run_key") != analysis_run_key:
        raise ProofError("compute_report_analysis_run_key_mismatch")
    if analysis.get("subject_run_key") != packet_subject.get("subject_run_key"):
        raise ProofError("compute_report_subject_run_key_mismatch")
    report_subject = _require_object(report.get("subject"), label="report_subject")
    expected_subject = {
        "repository": packet_subject.get("repository"),
        "workflow": packet_subject.get("workflow_name"),
        "workflow_run_id": packet_subject.get("workflow_run_id"),
        "workflow_run_number": packet_subject.get("workflow_run_number"),
        "workflow_run_attempt": packet_subject.get("workflow_run_attempt"),
        "source_commit": packet_subject.get("source_commit"),
        "release_candidate_id": packet_subject.get("release_candidate_id"),
        "run_mode": packet_subject.get("run_mode"),
        "active_policy_sets": packet_subject.get("active_policy_sets"),
        "policy_id": packet_subject.get("policy_id"),
        "policy_sha256": packet_subject.get("policy_sha256"),
        "materialized_gate_set_sha256": packet_subject.get(
            "materialized_gate_set_sha256"
        ),
        "final_status_sha256": packet_subject.get("final_status_sha256"),
        "release_decision_sha256": packet_subject.get("release_decision_sha256"),
        "decision": packet_subject.get("decision"),
    }
    if report_subject != expected_subject:
        raise ProofError("compute_report_subject_mismatch")
    tool = _require_object(report.get("tool"), label="report_tool")
    if tool.get("id") != "build_pulsemech_compute_binding_report_v0":
        raise ProofError("compute_report_tool_id_mismatch")
    if tool.get("source_sha256") != components["fixed_report_builder"].source_sha256:
        raise ProofError("compute_report_builder_source_mismatch")


def _extract_final_status(
    *,
    packet: dict[str, Any],
    carrier_bytes: bytes,
    packet_validator_component: ComponentBinding,
) -> bytes:
    validator = _load_module_from_component(
        packet_validator_component,
        module_name="pulsemech_subject_input_validator_for_current_run_proof_v0",
    )
    try:
        ok, complete, artifacts, errors = validator._verify_artifact_graph(
            packet,
            carrier_bytes=carrier_bytes,
        )
    except Exception as exc:
        raise ProofError(f"packet_artifact_graph_reconstruction_failed: {exc}") from exc
    if ok is not True or complete is not True or errors:
        raise ProofError(
            "packet_artifact_graph_reconstruction_rejected: "
            + json.dumps(errors, ensure_ascii=False, sort_keys=True)
        )
    bindings = _require_object(packet.get("role_bindings"), label="packet_role_bindings")
    final_status_id = bindings.get("final_status")
    if not isinstance(final_status_id, str) or final_status_id not in artifacts:
        raise ProofError("packet_final_status_binding_unresolved")
    value = artifacts[final_status_id]
    subject = _require_object(packet.get("subject"), label="packet_subject")
    if sha256_bytes(value) != subject.get("final_status_sha256"):
        raise ProofError("packet_final_status_digest_mismatch")
    _parse_json_bytes(value, label="base_final_status", canonical_required=True)
    return value


def _validate_plan(
    plan: dict[str, Any],
    *,
    packet: dict[str, Any],
    request: dict[str, Any],
    component_manifest: dict[str, Any],
) -> None:
    if plan.get("schema_version") != "pulsemech_integration_plan_v0":
        raise ProofError("current_run_plan_schema_version_mismatch")
    if plan.get("plan_type") != "pulsemech_integration_plan":
        raise ProofError("current_run_plan_type_mismatch")
    if plan.get("tool") != "plan_pulsemech_integration_v0":
        raise ProofError("current_run_plan_tool_mismatch")
    if plan.get("request_id") != request["request_id"]:
        raise ProofError("current_run_plan_request_id_mismatch")
    if plan.get("apply_eligible") is not True:
        raise ProofError("current_run_plan_not_apply_eligible")
    if plan.get("conflicts") != [] or plan.get("unresolved") != []:
        raise ProofError("current_run_plan_conflict_or_unresolved_present")
    subject = _require_object(packet.get("subject"), label="packet_subject")
    source = _require_object(plan.get("source"), label="plan_source")
    target = _require_object(plan.get("target"), label="plan_target")
    selection = _require_object(plan.get("selection"), label="plan_selection")
    if source.get("repository") != subject.get("repository"):
        raise ProofError("current_run_plan_source_repository_mismatch")
    if source.get("revision") != subject.get("source_commit"):
        raise ProofError("current_run_plan_source_revision_mismatch")
    if source.get("policy_sha256") != subject.get("policy_sha256"):
        raise ProofError("current_run_plan_policy_digest_mismatch")
    if target.get("repository_id") != subject.get("repository"):
        raise ProofError("current_run_plan_target_repository_mismatch")
    if target.get("default_branch") != "main":
        raise ProofError("current_run_plan_target_branch_mismatch")
    if selection.get("component_sets") != [PLAN_COMPONENT_SET_ID]:
        raise ProofError("current_run_plan_component_set_mismatch")
    if selection.get("resolved_components") != [PLAN_COMPONENT_ID]:
        raise ProofError("current_run_plan_component_mismatch")
    operations = _require_list(plan.get("operations"), label="plan_operations")
    if len(operations) != 1:
        raise ProofError("current_run_plan_operation_count_mismatch")
    operation = _require_object(operations[0], label="plan_operation")
    expected_operation = {
        "action": "preserve",
        "component_id": PLAN_COMPONENT_ID,
        "source_path": SUBJECT_CHECK_GATES_PATH,
        "target_path": SUBJECT_CHECK_GATES_PATH,
        "target_state": "identical",
    }
    for field, expected in expected_operation.items():
        if operation.get(field) != expected:
            raise ProofError(
                f"current_run_plan_operation_{field}_mismatch: "
                f"expected={expected!r} actual={operation.get(field)!r}"
            )
    expected_manifest_sha = sha256_bytes(render_json(component_manifest))
    if source.get("component_manifest_sha256") != expected_manifest_sha:
        raise ProofError("current_run_plan_component_manifest_digest_mismatch")


def _validate_relation(
    relation: dict[str, Any],
    *,
    report: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    if relation.get("schema_version") != (
        "pulsemech_compute_planned_observed_relation_v0"
    ):
        raise ProofError("relation_schema_version_mismatch")
    if relation.get("relation_type") != "pulsemech_compute_planned_observed_relation":
        raise ProofError("relation_type_mismatch")
    if relation.get("record_status") != "observed":
        raise ProofError("relation_record_status_not_observed")
    if relation.get("ok") is not True or relation.get("errors") != []:
        raise ProofError("relation_not_ok_or_errors_present")
    if relation.get("authority_boundary") != EXPECTED_RELATION_AUTHORITY:
        raise ProofError("relation_authority_boundary_mismatch")
    comparison = _require_object(
        relation.get("comparison_boundary"),
        label="relation_comparison_boundary",
    )
    if comparison.get("observed_analysis_level") != "artifact_observed":
        raise ProofError("relation_analysis_level_mismatch")
    identity = _require_object(
        relation.get("comparison_identity"),
        label="relation_comparison_identity",
    )
    subject = _require_object(report.get("subject"), label="report_subject")
    expected_identity = {
        "subject_repository": subject.get("repository"),
        "subject_source_commit": subject.get("source_commit"),
        "release_candidate_id": subject.get("release_candidate_id"),
    }
    for field, expected in expected_identity.items():
        if identity.get(field) != expected:
            raise ProofError(f"relation_{field}_mismatch")
    plan_binding = _require_object(relation.get("plan_binding"), label="plan_binding")
    if plan_binding.get("sha256") != sha256_bytes(render_json(plan)):
        raise ProofError("relation_plan_digest_mismatch")
    observations = _require_object(relation.get("observations"), label="observations")
    relations = _require_object(relation.get("relations"), label="relations")
    findings = _require_object(relation.get("findings"), label="findings")
    coverage = _require_object(relation.get("coverage"), label="coverage")
    if not observations or not relations:
        raise ProofError("relation_observation_or_relation_surface_empty")
    if coverage.get("runtime_observation_status") not in {
        "absent",
        "not_provided",
        "not_required",
    }:
        # Preserve current contract evolution while rejecting a false complete runtime claim.
        if coverage.get("runtime_observation_status") == "complete":
            raise ProofError("relation_false_runtime_complete_claim")
    # Findings, unresolved reasons and false candidate consequences are intentionally retained.
    if not isinstance(findings, dict):
        raise ProofError("relation_findings_not_object")


def _validate_materialization(
    *,
    report: dict[str, Any],
    base_status: dict[str, Any],
    folded_status: dict[str, Any],
) -> dict[str, bool]:
    if report.get("tool") != (
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0"
    ):
        raise ProofError("candidate_materializer_tool_mismatch")
    if report.get("version") != "0.1.0":
        raise ProofError("candidate_materializer_version_mismatch")
    if report.get("ok") is not True:
        raise ProofError("candidate_materializer_not_ok")
    if report.get("relation_validated") is not True:
        raise ProofError("candidate_materializer_relation_not_validated")
    if report.get("output_status_written") is not True:
        raise ProofError("candidate_materializer_output_not_written")
    if report.get("errors") != []:
        raise ProofError("candidate_materializer_errors_present")
    if report.get("candidate_gate_set") != CANDIDATE_GATE_SET:
        raise ProofError("candidate_materializer_gate_set_mismatch")
    gates = _require_object(
        report.get("candidate_gates"),
        label="candidate_materializer_gates",
    )
    if set(gates) != set(CANDIDATE_GATES) or any(
        type(value) is not bool for value in gates.values()
    ):
        raise ProofError("candidate_materializer_gate_map_invalid")
    if report.get("candidate_all_true") is not all(gates.values()):
        raise ProofError("candidate_materializer_all_true_mismatch")
    if report.get("folded_gates") != list(CANDIDATE_GATES):
        raise ProofError("candidate_materializer_folded_gate_list_mismatch")
    expected = copy.deepcopy(base_status)
    base_gates = _require_object(expected.get("gates"), label="base_status_gates")
    for gate in CANDIDATE_GATES:
        base_gates[gate] = gates[gate]
    if folded_status != expected:
        raise ProofError("folded_candidate_status_content_mismatch")
    return {gate: bool(gates[gate]) for gate in CANDIDATE_GATES}


def _make_proof_manifest(
    *,
    bundle: InputBundle,
    packet: dict[str, Any],
    report: dict[str, Any],
    plan: dict[str, Any],
    relation: dict[str, Any],
    materializer_report: dict[str, Any],
    candidate_gates: dict[str, bool],
    output_files: Sequence[CapturedFile],
    request: dict[str, Any],
    component_manifest: dict[str, Any],
    producer: ComponentBinding,
    control_repository: str,
    control_revision: str,
    analysis_run_key: str,
    producer_run_key: str,
    ci_identity: str,
) -> dict[str, Any]:
    packet_subject = _require_object(packet.get("subject"), label="packet_subject")
    coverage = _require_object(relation.get("coverage"), label="relation_coverage")
    findings = _require_object(relation.get("findings"), label="relation_findings")
    summary = _require_object(relation.get("summary"), label="relation_summary")
    return {
        "authority_boundary": dict(CLOSED_AUTHORITY_BOUNDARY),
        "content_boundary": dict(CLOSED_CONTENT_BOUNDARY),
        "document_type": DOCUMENT_TYPE,
        "errors": [],
        "input_bindings": {
            "candidate_bundle_intake_report": {
                "path": INTAKE_REPORT_NAME,
                "sha256": bundle.files[INTAKE_REPORT_NAME].sha256,
                "size_bytes": bundle.files[INTAKE_REPORT_NAME].size_bytes,
            },
            "carrier": {
                "path": bundle.carrier_name,
                "sha256": bundle.files[bundle.carrier_name].sha256,
                "size_bytes": bundle.files[bundle.carrier_name].size_bytes,
            },
            "expectation": {
                "path": EXPECTATION_NAME,
                "sha256": bundle.files[EXPECTATION_NAME].sha256,
                "size_bytes": bundle.files[EXPECTATION_NAME].size_bytes,
            },
            "provider_binding": bundle.intake_report.get("provider_binding"),
            "subject_input_packet": {
                "path": PACKET_NAME,
                "sha256": bundle.files[PACKET_NAME].sha256,
                "size_bytes": bundle.files[PACKET_NAME].size_bytes,
            },
        },
        "ok": True,
        "output_layout": {
            "file_count": len(output_files),
            "files": [
                {
                    "path": item.name,
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                }
                for item in sorted(output_files, key=lambda row: row.name)
            ],
            "manifest_scope": "all_proof_files_except_this_manifest",
            "proof_manifest_path": PROOF_MANIFEST_NAME,
        },
        "plan_generation": {
            "component_manifest": component_manifest,
            "component_manifest_sha256": sha256_bytes(render_json(component_manifest)),
            "request": request,
            "request_sha256": sha256_bytes(render_json(request)),
        },
        "producer": {
            "ci_workflow_or_job_identity": ci_identity,
            "producer_id": PRODUCER_ID,
            "producer_name": PRODUCER_NAME,
            "producer_run_key": producer_run_key,
            "producer_source": producer.path,
            "producer_source_revision": control_revision,
            "producer_source_sha256": producer.source_sha256,
            "producer_version": TOOL_VERSION,
            "production_mode": PRODUCTION_MODE,
        },
        "proof_identity": {
            "analysis_run_key": analysis_run_key,
            "canonicalization": "json-sort-keys-utf8-newline",
            "proof_id": (
                "artifact-observed-proof:"
                f"{packet_subject.get('repository')}/"
                f"{packet_subject.get('workflow_run_id')}/"
                f"{packet_subject.get('workflow_run_attempt')}/v0"
            ),
            "subject_run_key": packet_subject.get("subject_run_key"),
        },
        "record_status": "observed",
        "result": {
            "analysis_level": report.get("analysis_boundary", {}).get("analysis_level"),
            "candidate_all_true": all(candidate_gates.values()),
            "candidate_gate_set": CANDIDATE_GATE_SET,
            "candidate_gates": candidate_gates,
            "finding_types": sorted(
                {
                    item.get("finding_type")
                    for item in findings.values()
                    if isinstance(item, dict)
                    and isinstance(item.get("finding_type"), str)
                }
            ),
            "relation_comparison_status": coverage.get("comparison_status"),
            "relation_summary": summary,
            "unresolved_reasons": coverage.get("unresolved_reasons"),
        },
        "schema_version": SCHEMA_VERSION,
        "subject": {
            "active_policy_sets": packet_subject.get("active_policy_sets"),
            "decision": packet_subject.get("decision"),
            "release_candidate_id": packet_subject.get("release_candidate_id"),
            "repository": packet_subject.get("repository"),
            "source_commit": packet_subject.get("source_commit"),
            "subject_run_key": packet_subject.get("subject_run_key"),
            "workflow_name": packet_subject.get("workflow_name"),
            "workflow_run_attempt": packet_subject.get("workflow_run_attempt"),
            "workflow_run_id": packet_subject.get("workflow_run_id"),
            "workflow_run_number": packet_subject.get("workflow_run_number"),
        },
        "trusted_control_plane": {
            "repository": control_repository,
            "revision": control_revision,
            "separate_from_subject_checkout": True,
            "subject_may_select_revision": False,
            "trust_mode": "protected_exact_revision",
        },
    }


def _remove_directory_by_fd(
    parent_fd: int,
    name: str,
    *,
    expected_identity: tuple[int, int] | None,
) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if expected_identity is not None and _inode_identity(metadata) != expected_identity:
        return
    if not stat.S_ISDIR(metadata.st_mode):
        return
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        for child in os.listdir(fd):
            child_metadata = os.stat(child, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(child_metadata.st_mode):
                _remove_directory_by_fd(
                    fd,
                    child,
                    expected_identity=_inode_identity(child_metadata),
                )
            elif stat.S_ISREG(child_metadata.st_mode):
                try:
                    child_fd = os.open(
                        child,
                        os.O_RDONLY | os.O_NOFOLLOW,
                        dir_fd=fd,
                    )
                    try:
                        os.fchmod(child_fd, 0o600)
                    finally:
                        os.close(child_fd)
                except OSError:
                    pass
                os.unlink(child, dir_fd=fd)
        try:
            os.fchmod(fd, 0o700)
        except OSError:
            pass
    finally:
        os.close(fd)
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError:
        pass


def _build(args: argparse.Namespace) -> bytes:
    _require_supported_execution_platform()
    subject_repository = _canonical_repository(
        args.subject_repository,
        label="subject_repository",
    )
    subject_revision = _canonical_sha40(
        args.subject_revision,
        label="subject_revision",
    )
    control_repository = _canonical_repository(
        args.control_plane_repository,
        label="control_plane_repository",
    )
    control_revision = _canonical_sha40(
        args.control_plane_revision,
        label="control_plane_revision",
    )
    analysis_run_key = _non_empty_text(args.analysis_run_key, label="analysis_run_key")
    producer_run_key = _non_empty_text(args.producer_run_key, label="producer_run_key")
    ci_identity = _non_empty_text(
        args.ci_workflow_or_job_identity,
        label="ci_workflow_or_job_identity",
    )
    if analysis_run_key == producer_run_key:
        raise ProofError("analysis_run_key_must_differ_from_producer_run_key")

    trusted_git = _select_trusted_git(args.trusted_git)
    subject_root = _verify_repository(
        git=trusted_git,
        root=Path(args.subject_root),
        expected_revision=subject_revision,
        label="subject_repository",
    )
    control_root = _verify_repository(
        git=trusted_git,
        root=Path(args.control_plane_root),
        expected_revision=control_revision,
        label="control_plane_repository",
    )
    if _paths_overlap(subject_root, control_root):
        raise ProofError("subject_and_control_plane_roots_must_be_separate")

    control_components = _verify_component_set(
        git=trusted_git,
        repository_root=control_root,
        revision=control_revision,
        specs=CONTROL_COMPONENT_SPECS,
    )
    subject_components = _verify_component_set(
        git=trusted_git,
        repository_root=subject_root,
        revision=subject_revision,
        specs=SUBJECT_COMPONENT_SPECS,
    )

    intake_path = _normalized_absolute_path(Path(args.intake_directory))
    output_directory = _normalized_absolute_path(Path(args.output_directory))
    if output_directory.name.casefold() in PROTECTED_OUTPUT_NAMES_CASEFOLDED:
        raise ProofError("output_directory_protected_name_rejected")
    if output_directory.exists() or output_directory.is_symlink():
        raise ProofError("output_directory_already_exists")
    output_parent = _validate_owned_private_directory(
        output_directory.parent,
        label="output_parent",
    )
    output_directory = output_parent / output_directory.name
    for protected in (
        intake_path,
        subject_root,
        control_root,
        control_components["proof_builder"].worktree_path,
    ):
        if _paths_overlap(output_directory, protected):
            raise ProofError(f"output_directory_overlaps_protected_input: {protected}")

    input_bundle = _capture_intake_directory(
        intake_path,
        maximum_file_bytes=args.max_input_file_bytes,
    )
    expectation, packet = _verify_intake_bindings(
        bundle=input_bundle,
        subject_repository=subject_repository,
        subject_revision=subject_revision,
        control_repository=control_repository,
        control_revision=control_revision,
        components=control_components,
    )
    packet_subject = _require_object(packet.get("subject"), label="packet_subject")
    if analysis_run_key == packet_subject.get("subject_run_key"):
        raise ProofError("analysis_run_key_must_differ_from_subject_run_key")

    parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent_flags |= int(getattr(os, "O_CLOEXEC", 0))
    parent_fd = os.open(output_parent, parent_flags)
    parent_identity = _inode_identity(os.fstat(parent_fd))
    temp_name = f".{output_directory.name}.{secrets.token_hex(16)}.tmp"
    temp_fd: int | None = None
    input_fd: int | None = None
    proof_fd: int | None = None
    proof_identity: tuple[int, int] | None = None
    published_identity: tuple[int, int] | None = None
    try:
        os.mkdir(temp_name, 0o700, dir_fd=parent_fd)
        temp_fd = os.open(temp_name, parent_flags, dir_fd=parent_fd)
        temp_identity = _inode_identity(os.fstat(temp_fd))
        os.mkdir("inputs", 0o700, dir_fd=temp_fd)
        os.mkdir("proof", 0o700, dir_fd=temp_fd)
        input_fd = os.open("inputs", parent_flags, dir_fd=temp_fd)
        proof_fd = os.open("proof", parent_flags, dir_fd=temp_fd)
        proof_identity = _inode_identity(os.fstat(proof_fd))

        carrier_input_name = _copy_captured_input(
            input_fd,
            input_bundle.files[input_bundle.carrier_name],
        )
        packet_input_name = _copy_captured_input(
            input_fd,
            input_bundle.files[PACKET_NAME],
        )
        _copy_captured_input(input_fd, input_bundle.files[EXPECTATION_NAME])
        _copy_captured_input(input_fd, input_bundle.files[INTAKE_REPORT_NAME])

        request, component_manifest = _build_dynamic_plan_inputs(
            packet=packet,
            subject_components=subject_components,
        )
        _validate_json_schema(
            schema_bytes=control_components["integration_request_schema"].bytes_value,
            value=request,
            label="generated_integration_request",
        )
        _validate_json_schema(
            schema_bytes=control_components[
                "integration_component_manifest_schema"
            ].bytes_value,
            value=component_manifest,
            label="generated_component_manifest",
        )
        _write_file_at(
            input_fd,
            "current-run-integration-request.json",
            render_json(request),
            mode=0o400,
        )
        _write_file_at(
            input_fd,
            "current-run-component-manifest.json",
            render_json(component_manifest),
            mode=0o400,
        )

        input_path = output_parent / temp_name / "inputs"
        proof_path = output_parent / temp_name / "proof"
        process_env = _sanitized_environment(trusted_git=trusted_git)
        process_env["PATH"] = str(trusted_git.parent)

        bridge_result = _process_or_fail(
            [
                sys.executable,
                "-I",
                str(control_components["subject_input_bridge"].worktree_path),
                "--packet",
                str(input_path / packet_input_name),
                "--carrier",
                str(input_path / carrier_input_name),
                "--repository-root",
                str(subject_root),
                "--analysis-run-key",
                analysis_run_key,
            ],
            cwd=control_root,
            env=process_env,
            timeout_seconds=args.subprocess_timeout_seconds,
            label="subject_input_report_bridge",
        )
        report = _parse_json_bytes(
            bridge_result.stdout,
            label="compute_binding_report",
            canonical_required=True,
        )
        _validate_json_schema(
            schema_bytes=control_components["report_schema"].bytes_value,
            value=report,
            label="compute_binding_report",
        )
        _validate_report(
            report,
            packet=packet,
            components=control_components,
            analysis_run_key=analysis_run_key,
        )
        _write_file_at(
            proof_fd,
            REPORT_OUTPUT_NAME,
            bridge_result.stdout,
            mode=0o400,
        )

        final_status_bytes = _extract_final_status(
            packet=packet,
            carrier_bytes=input_bundle.files[input_bundle.carrier_name].bytes_value,
            packet_validator_component=control_components["subject_input_validator"],
        )
        _write_file_at(
            input_fd,
            "base-status.json",
            final_status_bytes,
            mode=0o400,
        )

        planner_result = _process_or_fail(
            [
                sys.executable,
                "-I",
                str(control_components["integration_planner"].worktree_path),
                "--request",
                str(input_path / "current-run-integration-request.json"),
                "--request-schema",
                str(control_components["integration_request_schema"].worktree_path),
                "--component-manifest",
                str(input_path / "current-run-component-manifest.json"),
                "--component-manifest-schema",
                str(
                    control_components[
                        "integration_component_manifest_schema"
                    ].worktree_path
                ),
                "--plan-schema",
                str(control_components["integration_plan_schema"].worktree_path),
                "--source-root",
                str(subject_root),
                "--target-root",
                str(subject_root),
                "--output",
                str(proof_path / PLAN_OUTPUT_NAME),
            ],
            cwd=control_root,
            env=process_env,
            timeout_seconds=args.subprocess_timeout_seconds,
            label="current_run_integration_planner",
        )
        plan_capture = _capture_output_file_at(
            proof_fd,
            PLAN_OUTPUT_NAME,
            maximum=MAX_JSON_BYTES,
            require_canonical_json=True,
        )
        if planner_result.stdout and planner_result.stdout != plan_capture.bytes_value:
            raise ProofError("planner_stdout_output_mismatch")
        plan = _parse_json_bytes(plan_capture.bytes_value, label="current_run_plan")
        _validate_json_schema(
            schema_bytes=control_components["integration_plan_schema"].bytes_value,
            value=plan,
            label="current_run_plan",
        )
        _validate_plan(
            plan,
            packet=packet,
            request=request,
            component_manifest=component_manifest,
        )
        _chmod_file_at(proof_fd, PLAN_OUTPUT_NAME, 0o400)

        relation_id = (
            "planned-observed:current-run-"
            f"{packet_subject.get('workflow_run_id')}-"
            f"{packet_subject.get('workflow_run_attempt')}/artifact-observed/v0"
        )
        relation_result = _process_or_fail(
            [
                sys.executable,
                "-I",
                str(control_components["relation_builder"].worktree_path),
                "--plan",
                str(proof_path / PLAN_OUTPUT_NAME),
                "--compute-report",
                str(proof_path / REPORT_OUTPUT_NAME),
                "--relation-id",
                relation_id,
                "--tool-source-revision",
                control_revision,
                "--plan-schema",
                str(control_components["integration_plan_schema"].worktree_path),
                "--report-schema",
                str(control_components["report_schema"].worktree_path),
                "--runtime-packet-schema",
                str(control_components["runtime_packet_schema"].worktree_path),
                "--relation-schema",
                str(control_components["relation_schema"].worktree_path),
                "--report-validator",
                str(control_components["report_validator"].worktree_path),
                "--runtime-packet-validator",
                str(control_components["runtime_packet_validator"].worktree_path),
                "--relation-validator",
                str(control_components["relation_validator"].worktree_path),
                "--subject-root",
                str(subject_root),
                "--output",
                str(proof_path / RELATION_OUTPUT_NAME),
            ],
            cwd=control_root,
            env=process_env,
            timeout_seconds=args.subprocess_timeout_seconds,
            label="planned_observed_relation_builder",
        )
        relation_capture = _capture_output_file_at(
            proof_fd,
            RELATION_OUTPUT_NAME,
            maximum=MAX_JSON_BYTES,
            require_canonical_json=True,
        )
        if relation_result.stdout != relation_capture.bytes_value:
            raise ProofError("relation_stdout_output_mismatch")
        relation = _parse_json_bytes(
            relation_capture.bytes_value,
            label="planned_observed_relation",
        )
        _validate_json_schema(
            schema_bytes=control_components["relation_schema"].bytes_value,
            value=relation,
            label="planned_observed_relation",
        )
        _validate_relation(relation, report=report, plan=plan)
        _chmod_file_at(proof_fd, RELATION_OUTPUT_NAME, 0o400)

        materializer_result = _process_or_fail(
            [
                sys.executable,
                "-I",
                str(control_components["candidate_materializer"].worktree_path),
                "--status",
                str(input_path / "base-status.json"),
                "--relation",
                str(proof_path / RELATION_OUTPUT_NAME),
                "--schema",
                str(control_components["relation_schema"].worktree_path),
                "--validator",
                str(control_components["relation_validator"].worktree_path),
                "--output",
                str(proof_path / FOLDED_STATUS_NAME),
            ],
            cwd=control_root,
            env=process_env,
            timeout_seconds=args.subprocess_timeout_seconds,
            label="candidate_status_materializer",
        )
        materializer_report = _parse_json_bytes(
            materializer_result.stdout,
            label="candidate_materializer_report",
            canonical_required=True,
        )
        _write_file_at(
            proof_fd,
            MATERIALIZER_REPORT_NAME,
            materializer_result.stdout,
            mode=0o400,
        )
        folded_capture = _capture_output_file_at(
            proof_fd,
            FOLDED_STATUS_NAME,
            maximum=MAX_JSON_BYTES,
            require_canonical_json=True,
        )
        base_status = _parse_json_bytes(final_status_bytes, label="base_status")
        folded_status = _parse_json_bytes(
            folded_capture.bytes_value,
            label="folded_candidate_status",
        )
        candidate_gates = _validate_materialization(
            report=materializer_report,
            base_status=base_status,
            folded_status=folded_status,
        )
        _chmod_file_at(proof_fd, FOLDED_STATUS_NAME, 0o400)

        captures: list[CapturedFile] = []
        for name in PROOF_PAYLOAD_NAMES:
            captures.append(
                _capture_output_file_at(
                    proof_fd,
                    name,
                    maximum=MAX_JSON_BYTES,
                    require_canonical_json=True,
                )
            )
        proof_manifest = _make_proof_manifest(
            bundle=input_bundle,
            packet=packet,
            report=report,
            plan=plan,
            relation=relation,
            materializer_report=materializer_report,
            candidate_gates=candidate_gates,
            output_files=captures,
            request=request,
            component_manifest=component_manifest,
            producer=control_components["proof_builder"],
            control_repository=control_repository,
            control_revision=control_revision,
            analysis_run_key=analysis_run_key,
            producer_run_key=producer_run_key,
            ci_identity=ci_identity,
        )
        rendered_manifest = render_json(proof_manifest)
        _write_file_at(
            proof_fd,
            PROOF_MANIFEST_NAME,
            rendered_manifest,
            mode=0o400,
        )

        expected_proof_names = set(PROOF_PAYLOAD_NAMES) | {PROOF_MANIFEST_NAME}
        observed_proof_names = set(os.listdir(proof_fd))
        if observed_proof_names != expected_proof_names:
            raise ProofError(
                "proof_output_closure_failed: "
                f"missing={sorted(expected_proof_names - observed_proof_names)!r} "
                f"unexpected={sorted(observed_proof_names - expected_proof_names)!r}"
            )
        for name in expected_proof_names:
            _chmod_file_at(proof_fd, name, 0o444)
        os.fsync(proof_fd)
        os.fchmod(proof_fd, 0o555)

        _reverify_component_set(
            git=trusted_git,
            repository_root=control_root,
            revision=control_revision,
            expected=control_components,
        )
        _reverify_component_set(
            git=trusted_git,
            repository_root=subject_root,
            revision=subject_revision,
            expected=subject_components,
        )
        with DirectorySnapshot(intake_path, label="intake_directory_final") as intake:
            if intake.names() != set(input_bundle.files):
                raise ProofError("intake_directory_changed_during_proof")
            for name, expected in input_bundle.files.items():
                observed = intake.capture_file(
                    name,
                    maximum=max(expected.size_bytes, 1),
                )
                if (
                    observed.sha256 != expected.sha256
                    or observed.size_bytes != expected.size_bytes
                ):
                    raise ProofError(f"intake_file_changed_during_proof: {name}")
            intake.verify()

        if _inode_identity(os.fstat(parent_fd)) != parent_identity:
            raise ProofError("output_parent_identity_changed")
        temp_path_meta = os.stat(temp_name, dir_fd=parent_fd, follow_symlinks=False)
        if _inode_identity(temp_path_meta) != temp_identity:
            raise ProofError("temporary_work_directory_path_replaced")
        proof_meta = os.stat("proof", dir_fd=temp_fd, follow_symlinks=False)
        if _inode_identity(proof_meta) != proof_identity:
            raise ProofError("proof_directory_path_replaced_before_publish")
        if output_directory.name in os.listdir(parent_fd):
            raise ProofError("output_directory_appeared_before_publish")

        os.rename(
            "proof",
            output_directory.name,
            src_dir_fd=temp_fd,
            dst_dir_fd=parent_fd,
        )
        published_meta = os.stat(
            output_directory.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        published_identity = _inode_identity(published_meta)
        if published_identity != proof_identity:
            raise ProofError("published_proof_directory_identity_mismatch")
        os.fsync(parent_fd)

        published_fd = os.open(output_directory.name, parent_flags, dir_fd=parent_fd)
        try:
            if _inode_identity(os.fstat(published_fd)) != published_identity:
                raise ProofError("published_proof_directory_reopen_mismatch")
            if set(os.listdir(published_fd)) != expected_proof_names:
                raise ProofError("published_proof_directory_closure_failed")
            for item in captures:
                observed = _capture_output_file_at(
                    published_fd,
                    item.name,
                    maximum=max(item.size_bytes, 1),
                    require_canonical_json=True,
                )
                if observed.sha256 != item.sha256 or observed.size_bytes != item.size_bytes:
                    raise ProofError(f"published_proof_file_identity_mismatch: {item.name}")
            observed_manifest = _capture_output_file_at(
                published_fd,
                PROOF_MANIFEST_NAME,
                maximum=MAX_JSON_BYTES,
                require_canonical_json=True,
            )
            if observed_manifest.bytes_value != rendered_manifest:
                raise ProofError("published_proof_manifest_bytes_mismatch")
        finally:
            os.close(published_fd)

        _reverify_component_set(
            git=trusted_git,
            repository_root=control_root,
            revision=control_revision,
            expected=control_components,
        )
        _reverify_component_set(
            git=trusted_git,
            repository_root=subject_root,
            revision=subject_revision,
            expected=subject_components,
        )

        # Remove private captured-input work after successful proof publication.
        input_identity = _inode_identity(os.fstat(input_fd))
        os.close(input_fd)
        input_fd = None
        _remove_directory_by_fd(temp_fd, "inputs", expected_identity=input_identity)
        os.close(proof_fd)
        proof_fd = None
        os.close(temp_fd)
        temp_fd = None
        _remove_directory_by_fd(parent_fd, temp_name, expected_identity=temp_identity)
        return rendered_manifest
    except Exception:
        if proof_fd is not None:
            try:
                os.close(proof_fd)
            except OSError:
                pass
        if input_fd is not None:
            try:
                os.close(input_fd)
            except OSError:
                pass
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if published_identity is not None:
            _remove_directory_by_fd(
                parent_fd,
                output_directory.name,
                expected_identity=published_identity,
            )
        try:
            temp_metadata = os.stat(temp_name, dir_fd=parent_fd, follow_symlinks=False)
            temp_expected = _inode_identity(temp_metadata)
        except OSError:
            temp_expected = None
        _remove_directory_by_fd(parent_fd, temp_name, expected_identity=temp_expected)
        raise
    finally:
        os.close(parent_fd)


def make_failure_diagnostic(*, error: str, exit_kind: str) -> dict[str, Any]:
    return {
        "authority_effect": "none",
        "document_type": DOCUMENT_TYPE,
        "errors": [error],
        "exit_kind": exit_kind,
        "ok": False,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }


def _arg_positive_int(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consume one exact verified Step 3G candidate-bundle intake, drive "
            "the existing artifact-observed analyzer, integration planner, "
            "planned-observed relation builder and non-active candidate "
            "materializer, then publish one checksum-closed external proof "
            "bundle without changing release authority."
        )
    )
    parser.add_argument("--intake-directory", required=True)
    parser.add_argument("--subject-root", required=True)
    parser.add_argument("--subject-repository", required=True)
    parser.add_argument("--subject-revision", required=True)
    parser.add_argument(
        "--control-plane-root",
        default=str(ROOT),
    )
    parser.add_argument("--control-plane-repository", required=True)
    parser.add_argument("--control-plane-revision", required=True)
    parser.add_argument("--analysis-run-key", required=True)
    parser.add_argument("--producer-run-key", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--trusted-git")
    parser.add_argument(
        "--subprocess-timeout-seconds",
        type=_arg_positive_int,
        default=DEFAULT_SUBPROCESS_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--max-input-file-bytes",
        type=_arg_positive_int,
        default=DEFAULT_MAX_INPUT_FILE_BYTES,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rendered = _build(args)
    except ProofError as exc:
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
                    error=f"unhandled_proof_error: {type(exc).__name__}: {exc}",
                    exit_kind="unhandled_error",
                )
            )
        )
        return 2
    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
