#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"document_type":"pulsemech_compute_subject_input_packet_current_run_wrapper",'
    '"errors":["isolated_python_runtime_required: launch with python -I"],'
    '"exit_kind":"python_runtime_boundary_error",'
    '"ok":false,'
    '"tool":"build_pulsemech_compute_subject_input_packet_current_run_v0",'
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
import errno
import hashlib
import importlib.machinery
import io
import json
import os
import re
import selectors
import stat
import subprocess
import sysconfig
import tempfile
import time
import types
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


TOOL_NAME = "build_pulsemech_compute_subject_input_packet_current_run_v0"
TOOL_VERSION = "0.1.0"
DOCUMENT_TYPE = "pulsemech_compute_subject_input_packet_current_run_wrapper"
OUTPUT_SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
OUTPUT_PACKET_TYPE = "pulsemech_compute_subject_input_packet"

SUPPORTED_EXECUTION_PLATFORM = "linux"
SUPPORTED_OS_NAME = "posix"
EXECUTION_PROFILE = "protected_linux_hpc_control_plane"

WRAPPER_SOURCE_PATH = (
    "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py"
)
CARRIER_LOADER_SOURCE_PATH = (
    "tools/load_pulsemech_compute_current_run_export_carrier_v0.py"
)
EXPECTATION_BUILDER_SOURCE_PATH = (
    "tools/build_pulsemech_compute_current_run_export_expectation_v0.py"
)
EXPECTATION_SCHEMA_SOURCE_PATH = (
    "schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json"
)
EXPECTATION_VALIDATOR_SOURCE_PATH = (
    "tools/check_pulsemech_compute_current_run_export_expectation_v0.py"
)
SUBJECT_INPUT_SCHEMA_SOURCE_PATH = (
    "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
)
SUBJECT_INPUT_VALIDATOR_SOURCE_PATH = (
    "tools/check_pulsemech_compute_subject_input_packet_v0.py"
)
PRODUCER_CORE_SOURCE_PATH = (
    "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
CONTROL_PLANE_WORKFLOW_SOURCE_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)

CONTROL_PLANE_COMPONENT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("carrier_loader", CARRIER_LOADER_SOURCE_PATH, "0.1.0"),
    ("control_plane_workflow", CONTROL_PLANE_WORKFLOW_SOURCE_PATH, "0.1.0"),
    ("expectation_builder", EXPECTATION_BUILDER_SOURCE_PATH, "0.1.0"),
    ("expectation_schema", EXPECTATION_SCHEMA_SOURCE_PATH, "0"),
    ("expectation_validator", EXPECTATION_VALIDATOR_SOURCE_PATH, "0.1.0"),
    ("subject_input_producer_core", PRODUCER_CORE_SOURCE_PATH, "0.1.0"),
    ("subject_input_producer_wrapper", WRAPPER_SOURCE_PATH, "0.1.0"),
    ("subject_input_schema", SUBJECT_INPUT_SCHEMA_SOURCE_PATH, "0"),
    ("subject_input_validator", SUBJECT_INPUT_VALIDATOR_SOURCE_PATH, "0.1.0"),
)

EXPECTED_PACKET_CONTRACT = {
    "artifact_payload_mode": "external_carrier",
    "carrier_kind": "current_run_export_archive",
    "packet_scope": "current_run",
    "packet_type": OUTPUT_PACKET_TYPE,
    "production_mode": "current_run_export",
    "record_status": "observed",
    "schema_version": OUTPUT_SCHEMA_VERSION,
    "write_mode": "subject_input_only",
}

EXPECTED_EXPECTATION_CONTENT_BOUNDARY = {
    "consumer_must_verify_carrier_bytes": True,
    "contains_artifact_payloads": False,
    "contains_resource_measurement": False,
    "contains_runtime_observation": False,
    "contains_secret_material": False,
    "expectation_payload_mode": "metadata_only",
}

EXPECTED_EXPECTATION_AUTHORITY_BOUNDARY = {
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

EXPECTED_PACKET_AUTHORITY_BOUNDARY = {
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
}

EXPECTED_PACKET_CONTENT_BOUNDARY = {
    "artifact_bytes_embedded": False,
    "carrier_required_for_verification": True,
    "packet_payload_mode": "metadata_only",
    "raw_model_inputs_included": False,
    "raw_model_outputs_included": False,
    "raw_secrets_included": False,
}

PRESERVATION_AUTHORITY_BOUNDARY = {
    "alters_preserved_artifacts": False,
    "creates_release_authority": False,
    "preservation_copy_only": True,
    "replaces_original_github_attestations": False,
    "replaces_primary_ci_decision": False,
}

COMPLETENESS_REPORT_TOOL = {
    "name": "check_release_grade_package_complete_v1",
    "version": "0.1.2",
}

COMPLETENESS_REPORT_AUTHORITY_BOUNDARY = {
    "read_only": True,
    "authorizes_release": False,
    "blocks_release": False,
    "creates_release_authority": False,
    "materializes_status": False,
    "materializes_required_gates": False,
    "calls_gate_checker": False,
    "package_completeness_only": True,
}

VERIFICATION_REPORT_TOOL = {
    "name": "verify_release_grade_reference_package_v0.py",
    "version": "0.1.0",
}

VERIFICATION_REPORT_AUTHORITY_BOUNDARY = {
    "read_only": True,
    "creates_release_authority": False,
    "authorizes_release": False,
    "blocks_release": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "verifies_recorded_release_evidence_as_authority": False,
    "replaces_check_gates": False,
    "package_acceptance_only": True,
}

PROVIDER_ARCHIVE_ROLES = {
    "complete": "complete_release_grade_reference_package",
    "completeness": "structural_package_completeness_report",
    "verification": "independent_package_verification_report",
}

PACKAGE_REQUIRED_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_raw.jsonl",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/report_card.html",
)

PACKAGE_REQUIRED_DIRS: tuple[str, ...] = (
    "artifacts/recorded_release_candidates",
    "release-authority-audit-bundle",
)

PACKAGE_JSON_OBJECT_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
)

PACKAGE_JSONL_FILES: tuple[str, ...] = (
    "artifacts/external/llamaguard_raw.jsonl",
)

SLSA_PACKET_PATH = (
    "artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json"
)
SLSA_REPORT_PATH = (
    "artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json"
)
SLSA_TRUSTED_PRODUCER_FILES = (SLSA_PACKET_PATH, SLSA_REPORT_PATH)

STUB_MARKERS = (
    "todo",
    "tbd",
    "stub",
    "placeholder",
    "not implemented",
    "replace-me",
    "fill me",
    "example.invalid",
)
STUB_SCAN_EXEMPT_PATH_PREFIXES: tuple[tuple[str, str], ...] = (
    ("artifacts/release_decision_v0.json", "$.decision_basis"),
)
STUB_SCAN_EXEMPT_NORMALIZED_PATHS: tuple[tuple[str, str], ...] = (
    (
        "artifacts/external/llamaguard_summary.bundle.json",
        "$.verificationMaterial.tlogEntries[*].canonicalizedBody",
    ),
)
JSON_ARRAY_INDEX_RE = re.compile(r"\[\d+\]")
REPORT_CARD_NON_STUB_MARKERS = tuple(
    marker for marker in STUB_MARKERS if marker != "stub"
)
REPORT_CARD_ACTIVE_STUB_PHRASES = (
    "stubbed/scaffold evidence state",
    "stub/scaffold markers recorded",
)
REPORT_CARD_CLEAR_MARKER_SEQUENCE = "stub/scaffold marker state clear"

CANONICAL_PACKET_SOURCE_IDS = {
    "workflow": "source:workflow:pulse-ci",
    "policy": "source:policy:pulse-gate-policy-v0",
    "gate_registry": "source:registry:gate-registry-v0",
}
GENERIC_EXPECTATION_SOURCE_IDS = {
    "workflow": "source:workflow",
    "policy": "source:policy",
    "gate_registry": "source:gate-registry",
}
CANONICAL_ADDITIONAL_SOURCE_IDS = {
    ("external_signer_policy", "policy/external_signers_v1.yml"): (
        "source:policy:external-signers-v1"
    ),
    ("threshold_policy", "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"): (
        "source:policy:external-thresholds"
    ),
}

ROOT = Path(__file__).resolve().parents[1]

MAX_EXPECTATION_BYTES = 8 * 1024 * 1024
MAX_SCHEMA_BYTES = 2 * 1024 * 1024
MAX_COMPONENT_BYTES = 32 * 1024 * 1024
MAX_AUTHORITY_SOURCE_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_CARRIER_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 4096
MAX_ARCHIVE_MEMBER_BYTES = 256 * 1024 * 1024
MAX_GIT_CONFIG_BYTES = 1024 * 1024
MAX_GIT_DIAGNOSTIC_BYTES = 64 * 1024
GIT_CAPTURE_CHUNK_BYTES = 64 * 1024
READ_CHUNK_BYTES = 1024 * 1024

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
    }
)
PROTECTED_OUTPUT_NAMES_CASEFOLDED = frozenset(
    name.casefold() for name in PROTECTED_OUTPUT_NAMES
)


class WrapperError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_kind: str = "wrapper_error",
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.exit_code = exit_code


class StrictJsonError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedFile:
    role: str
    repository_root: Path
    revision: str
    repository_path: str
    path: Path
    payload: bytes
    git_blob_sha1: str
    sha256: str


@dataclass(frozen=True)
class CurrentRunBundle:
    archive_path: Path
    archive_sha256: str
    archive_size: int
    manifest_path: Path
    manifest_bytes: bytes
    manifest: dict[str, Any]
    readme_path: Path
    readme_bytes: bytes
    sha256sums_path: Path
    sha256sums_bytes: bytes
    sha256sums: dict[str, str]
    artifact_archives: dict[str, bytes]
    complete_package_members: dict[str, bytes]
    package_inventory: dict[str, Any]
    package_inventory_rows: dict[str, dict[str, Any]]
    completeness_report_bytes: bytes
    completeness_report: dict[str, Any]
    verification_report_bytes: bytes
    verification_report: dict[str, Any]


@dataclass
class UncompressedByteBudget:
    maximum: int
    consumed: int = 0

    def __post_init__(self) -> None:
        positive_int(self.maximum, label="aggregate_uncompressed_byte_budget")
        if (
            not isinstance(self.consumed, int)
            or isinstance(self.consumed, bool)
            or self.consumed < 0
            or self.consumed > self.maximum
        ):
            raise WrapperError(
                "aggregate_uncompressed_byte_budget_consumed_invalid: "
                f"consumed={self.consumed!r} maximum={self.maximum}",
                exit_kind="carrier_content_error",
            )

    @property
    def remaining(self) -> int:
        return self.maximum - self.consumed

    def reserve(self, amount: int, *, label: str) -> None:
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise WrapperError(
                f"{label}_uncompressed_size_invalid: {amount!r}",
                exit_kind="carrier_content_error",
            )
        proposed = self.consumed + amount
        if proposed > self.maximum:
            raise WrapperError(
                f"{label}_aggregate_uncompressed_too_large: "
                f"consumed={self.consumed} requested={amount} "
                f"maximum={self.maximum}",
                exit_kind="carrier_content_error",
            )
        self.consumed = proposed


# ---------------------------------------------------------------------------
# Canonical values and filesystem identities
# ---------------------------------------------------------------------------


def render_json(value: Mapping[str, Any]) -> bytes:
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


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def parse_json_bytes(payload: bytes, *, label: str) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise WrapperError(
            f"{label}_utf8_bom_not_permitted",
            exit_kind="strict_json_error",
        )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"{label}_invalid_utf8: {exc}",
            exit_kind="strict_json_error",
        ) from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except (ValueError, StrictJsonError) as exc:
        raise WrapperError(
            f"{label}_invalid_json: {exc}",
            exit_kind="strict_json_error",
        ) from exc


def parse_json_object(payload: bytes, *, label: str) -> dict[str, Any]:
    value = parse_json_bytes(payload, label=label)
    if not isinstance(value, dict):
        raise WrapperError(
            f"{label}_not_object",
            exit_kind="strict_json_error",
        )
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


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


def paths_overlap(left: Path, right: Path) -> bool:
    return (
        same_target(left, right)
        or path_is_within(left, right)
        or path_is_within(right, left)
    )


def canonical_sha40(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise WrapperError(
            f"{label}_not_canonical_sha40: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def canonical_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise WrapperError(
            f"{label}_not_canonical_sha256: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def non_empty_text(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise WrapperError(
            f"{label}_invalid: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def positive_int(value: Any, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise WrapperError(
            f"{label}_not_positive_integer: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def canonical_member_path(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or "\x00" in value
    ):
        raise WrapperError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    pure = PurePosixPath(value)
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise WrapperError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    canonical = pure.as_posix()
    if canonical != value:
        raise WrapperError(
            f"{label}_not_canonical_relative_path: {value!r}",
            exit_kind="input_boundary_error",
        )
    return canonical


def canonical_directory_prefix(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("/"):
        raise WrapperError(
            f"{label}_not_canonical_directory_prefix: {value!r}",
            exit_kind="input_boundary_error",
        )
    return canonical_member_path(value[:-1], label=label) + "/"


def canonical_leaf_name(value: Any, *, label: str) -> str:
    text = non_empty_text(value, label=label)
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise WrapperError(
            f"{label}_not_canonical_leaf_name: {value!r}",
            exit_kind="input_boundary_error",
        )
    return text


def parse_utc(value: Any, *, label: str) -> datetime:
    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
            r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            value,
        )
        is None
    ):
        raise WrapperError(
            f"{label}_not_canonical_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WrapperError(
            f"{label}_invalid_datetime: {value!r}",
            exit_kind="input_boundary_error",
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise WrapperError(
            f"{label}_not_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    return parsed


def require_equal(actual: Any, expected: Any, *, label: str) -> None:
    if actual != expected:
        raise WrapperError(
            f"{label}_mismatch: expected={expected!r} actual={actual!r}",
            exit_kind="binding_error",
        )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WrapperError(message, exit_kind="binding_error")


def _require_supported_execution_platform() -> None:
    if sys.platform != SUPPORTED_EXECUTION_PLATFORM or os.name != SUPPORTED_OS_NAME:
        raise WrapperError(
            "unsupported_execution_platform: "
            f"profile={EXECUTION_PROFILE!r} "
            f"required_sys_platform={SUPPORTED_EXECUTION_PLATFORM!r} "
            f"required_os_name={SUPPORTED_OS_NAME!r} "
            f"observed_sys_platform={sys.platform!r} "
            f"observed_os_name={os.name!r}",
            exit_kind="platform_boundary_error",
        )
    capabilities = (
        os.open in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.rename in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.link in os.supports_dir_fd,
        os.link in os.supports_follow_symlinks,
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
    )
    if not all(capabilities):
        raise WrapperError(
            "protected_descriptor_profile_unavailable",
            exit_kind="platform_boundary_error",
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


@dataclass
class DirectoryChain:
    absolute_path: Path
    label: str
    fds: list[int]
    identities: list[tuple[Any, ...]]
    link_names: list[str]
    _closed: bool = False

    @classmethod
    def open(cls, path: Path, *, label: str) -> "DirectoryChain":
        candidate = _normalized_absolute_path(path)
        if not candidate.is_absolute() or not candidate.parts:
            raise WrapperError(
                f"{label}_path_not_absolute: {candidate}",
                exit_kind="input_boundary_error",
            )
        chain = cls(candidate, label, [], [], [])
        try:
            root_fd = os.open(candidate.parts[0], _directory_flags())
            root_state = os.fstat(root_fd)
            if not stat.S_ISDIR(root_state.st_mode):
                raise WrapperError(
                    f"{label}_root_not_directory: {candidate.parts[0]}",
                    exit_kind="input_boundary_error",
                )
            chain.fds.append(root_fd)
            chain.identities.append(_directory_identity(root_state))
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
            raise WrapperError(
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
            raise WrapperError(
                f"{self.label}_directory_component_invalid: {name!r}",
                exit_kind="input_boundary_error",
            )
        try:
            descriptor = os.open(name, _directory_flags(), dir_fd=self.final_fd)
        except OSError as exc:
            raise WrapperError(
                f"{self.label}_directory_component_open_failed: "
                f"component={name!r} error={exc}",
                exit_kind="input_boundary_error",
            ) from exc
        try:
            state = os.fstat(descriptor)
            if not stat.S_ISDIR(state.st_mode):
                raise WrapperError(
                    f"{self.label}_component_not_directory: {name!r}",
                    exit_kind="input_boundary_error",
                )
        except Exception:
            os.close(descriptor)
            raise
        self.link_names.append(name)
        self.fds.append(descriptor)
        self.identities.append(_directory_identity(state))

    def verify(self) -> None:
        if self._closed:
            raise WrapperError(
                f"{self.label}_directory_chain_closed",
                exit_kind="input_boundary_error",
            )
        if len(self.fds) != len(self.identities):
            raise WrapperError(
                f"{self.label}_directory_chain_internal_mismatch",
                exit_kind="input_boundary_error",
            )
        for index, descriptor in enumerate(self.fds):
            current = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(current.st_mode)
                or _directory_identity(current) != self.identities[index]
            ):
                raise WrapperError(
                    f"{self.label}_directory_identity_changed: index={index}",
                    exit_kind="input_boundary_error",
                )
        for index, name in enumerate(self.link_names):
            try:
                current = os.stat(
                    name,
                    dir_fd=self.fds[index],
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise WrapperError(
                    f"{self.label}_directory_link_unavailable: "
                    f"component={name!r} error={exc}",
                    exit_kind="input_boundary_error",
                ) from exc
            if (
                not stat.S_ISDIR(current.st_mode)
                or _directory_identity(current) != self.identities[index + 1]
            ):
                raise WrapperError(
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
        self.identities.clear()
        self.link_names.clear()

    def __enter__(self) -> "DirectoryChain":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()


def _validated_directory_root(path: Path, *, label: str) -> Path:
    candidate = _normalized_absolute_path(path)
    with DirectoryChain.open(candidate, label=label):
        pass
    try:
        state = candidate.lstat()
    except OSError as exc:
        raise WrapperError(
            f"{label}_unavailable: {candidate}: {exc}",
            exit_kind="input_boundary_error",
        ) from exc
    if stat.S_ISLNK(state.st_mode) or not stat.S_ISDIR(state.st_mode):
        raise WrapperError(
            f"{label}_not_protected_directory: {candidate}",
            exit_kind="input_boundary_error",
        )
    return candidate


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
        chunk = os.read(descriptor, min(READ_CHUNK_BYTES, max_bytes + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise WrapperError(
                f"{label}_too_large_during_read: size>{max_bytes}",
                exit_kind="input_boundary_error",
            )
        chunks.append(chunk)
    payload = b"".join(chunks)
    if expected_size is not None and len(payload) != expected_size:
        raise WrapperError(
            f"{label}_size_changed_during_read: "
            f"expected={expected_size} actual={len(payload)}",
            exit_kind="input_boundary_error",
        )
    return payload


def read_regular_file(path: Path, *, label: str, max_bytes: int) -> bytes:
    candidate = _normalized_absolute_path(path)
    if candidate == candidate.parent or not candidate.name:
        raise WrapperError(
            f"{label}_path_has_no_leaf: {candidate}",
            exit_kind="input_boundary_error",
        )
    with DirectoryChain.open(candidate.parent, label=f"{label}_parent") as chain:
        try:
            descriptor = os.open(candidate.name, _read_flags(), dir_fd=chain.final_fd)
        except OSError as exc:
            raise WrapperError(
                f"{label}_open_failed: {candidate}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise WrapperError(
                    f"{label}_not_regular_file: {candidate}",
                    exit_kind="input_boundary_error",
                )
            if before.st_size < 0 or before.st_size > max_bytes:
                raise WrapperError(
                    f"{label}_too_large: size={before.st_size} maximum={max_bytes}",
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
                raise WrapperError(
                    f"{label}_changed_during_read: {candidate}",
                    exit_kind="input_boundary_error",
                )
            chain.verify()
            path_state = os.stat(
                candidate.name,
                dir_fd=chain.final_fd,
                follow_symlinks=False,
            )
            if _file_identity(path_state) != _file_identity(after):
                raise WrapperError(
                    f"{label}_path_binding_changed: {candidate}",
                    exit_kind="input_boundary_error",
                )
            return payload
        finally:
            os.close(descriptor)


# ---------------------------------------------------------------------------
# Protected local-only Git bootstrap
# ---------------------------------------------------------------------------


def _validated_trusted_git(path: Path) -> Path:
    _require_supported_execution_platform()
    if not path.is_absolute():
        raise WrapperError(
            f"trusted_git_not_absolute: {path}",
            exit_kind="trusted_git_error",
        )
    candidate = _normalized_absolute_path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WrapperError(
            f"trusted_git_unresolvable: {candidate}: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if os.path.normcase(str(candidate)) != os.path.normcase(str(resolved)):
        raise WrapperError(
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
            state = component.lstat()
        except OSError as exc:
            raise WrapperError(
                f"trusted_git_component_unavailable: {component}: {exc}",
                exit_kind="trusted_git_error",
            ) from exc
        if stat.S_ISLNK(state.st_mode):
            raise WrapperError(
                f"trusted_git_symlink_component_rejected: {component}",
                exit_kind="trusted_git_error",
            )
        if component == resolved:
            if not stat.S_ISREG(state.st_mode):
                raise WrapperError(
                    f"trusted_git_not_regular_file: {component}",
                    exit_kind="trusted_git_error",
                )
        elif not stat.S_ISDIR(state.st_mode):
            raise WrapperError(
                f"trusted_git_parent_not_directory: {component}",
                exit_kind="trusted_git_error",
            )
        if state.st_uid != 0:
            raise WrapperError(
                f"trusted_git_unprotected_owner_rejected: component={component} uid={state.st_uid}",
                exit_kind="trusted_git_error",
            )
        if state.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise WrapperError(
                f"trusted_git_writable_component_rejected: {component}",
                exit_kind="trusted_git_error",
            )
    if not os.access(resolved, os.X_OK):
        raise WrapperError(
            f"trusted_git_not_executable: {resolved}",
            exit_kind="trusted_git_error",
        )
    approved = {
        os.path.normcase(str(_normalized_absolute_path(candidate_path)))
        for candidate_path in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    }
    if os.path.normcase(str(resolved)) not in approved:
        raise WrapperError(
            f"trusted_git_unapproved_candidate: {resolved}",
            exit_kind="trusted_git_error",
        )
    return resolved


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


def _local_only_git_config_arguments() -> list[str]:
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
        *_local_only_git_config_arguments(),
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
        raise WrapperError(
            f"{label}_capture_limit_invalid",
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
            raise WrapperError(
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
                raise WrapperError(
                    f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                    exit_kind="trusted_git_error",
                )
            events = selector.select(remaining)
            if not events:
                continue
            for key, _mask in events:
                stream_name, maximum = key.data
                buffer = buffers[stream_name]
                capacity = maximum - len(buffer)
                read_size = min(GIT_CAPTURE_CHUNK_BYTES, max(1, capacity + 1))
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
                    raise WrapperError(
                        f"{label}_{stream_name}_capture_limit_exceeded: "
                        f"observed_at_least={len(buffer)} maximum={maximum}",
                        exit_kind="trusted_git_error",
                    )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_subprocess(process)
            raise WrapperError(
                f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                exit_kind="trusted_git_error",
            )
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _terminate_subprocess(process)
            raise WrapperError(
                f"{label}_execution_timed_out: timeout_seconds={timeout_seconds}",
                exit_kind="trusted_git_error",
            ) from exc
        stdout = bytes(buffers["stdout"])
        stderr = bytes(buffers["stderr"])
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise WrapperError(
                f"{label}_failed: returncode={returncode} detail={detail!r}",
                exit_kind="trusted_git_error",
            )
        return stdout
    except WrapperError:
        if process is not None:
            _terminate_subprocess(process)
        raise
    except OSError as exc:
        if process is not None:
            _terminate_subprocess(process)
        raise WrapperError(
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
        raise WrapperError(
            "trusted_git_version_probe_invalid_output",
            exit_kind="trusted_git_error",
        )


def _select_trusted_git(explicit: str | None) -> Path:
    if explicit is not None:
        selected = _validated_trusted_git(Path(explicit))
        _require_trusted_git_local_only_support(selected)
        return selected
    errors: list[str] = []
    for candidate in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES:
        if not candidate.exists():
            errors.append(f"unavailable:{candidate}")
            continue
        try:
            selected = _validated_trusted_git(candidate)
            _require_trusted_git_local_only_support(selected)
        except WrapperError as exc:
            errors.append(str(exc))
            continue
        return selected
    raise WrapperError(
        "trusted_git_unavailable_or_incapable: "
        + json.dumps(errors, sort_keys=True),
        exit_kind="trusted_git_error",
    )


def _decode_single_line(data: bytes, *, label: str) -> str:
    try:
        value = data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"{label}_invalid_utf8",
            exit_kind="trusted_git_error",
        ) from exc
    if not value or "\x00" in value or "\n" in value or "\r" in value:
        raise WrapperError(
            f"{label}_invalid_output: {value!r}",
            exit_kind="trusted_git_error",
        )
    return value


def _verify_git_repository(
    *,
    git_path: Path,
    repository_root: Path,
    expected_revision: str,
    label: str,
) -> None:
    canonical_sha40(expected_revision, label=f"{label}_expected_revision")
    top_level = Path(
        _decode_single_line(
            _run_git(
                git_path=git_path,
                repository_root=repository_root,
                arguments=("rev-parse", "--show-toplevel"),
                label=f"{label}_top_level",
                max_stdout_bytes=64 * 1024,
            ),
            label=f"{label}_top_level",
        )
    )
    if not same_target(top_level, repository_root):
        raise WrapperError(
            f"{label}_repository_root_mismatch: "
            f"expected={repository_root} observed={top_level}",
            exit_kind="trusted_git_error",
        )
    head = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "HEAD"),
            label=f"{label}_head",
            max_stdout_bytes=4096,
        ),
        label=f"{label}_head",
    ).lower()
    canonical_sha40(head, label=f"{label}_head")
    if head != expected_revision:
        raise WrapperError(
            f"{label}_head_mismatch: expected={expected_revision} observed={head}",
            exit_kind="trusted_git_error",
        )


def _parse_scoped_git_config(
    raw: bytes,
    *,
    label: str,
) -> list[tuple[str, str, str]]:
    if len(raw) > MAX_GIT_CONFIG_BYTES:
        raise WrapperError(
            f"{label}_git_config_too_large: "
            f"size={len(raw)} maximum={MAX_GIT_CONFIG_BYTES}",
            exit_kind="trusted_git_error",
        )
    parts = raw.split(b"\x00")
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) % 2 != 0:
        raise WrapperError(
            f"{label}_git_config_record_structure_invalid",
            exit_kind="trusted_git_error",
        )
    rows: list[tuple[str, str, str]] = []
    for index in range(0, len(parts), 2):
        scope_raw = parts[index]
        entry_raw = parts[index + 1]
        key_raw, separator, value_raw = entry_raw.partition(b"\n")
        if not separator or not key_raw:
            raise WrapperError(
                f"{label}_git_config_entry_invalid: index={index // 2}",
                exit_kind="trusted_git_error",
            )
        try:
            scope = scope_raw.decode("ascii", errors="strict")
            key = key_raw.decode("utf-8", errors="strict")
            value = value_raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise WrapperError(
                f"{label}_git_config_entry_encoding_invalid: index={index // 2}",
                exit_kind="trusted_git_error",
            ) from exc
        rows.append((scope, key, value))
    return rows


def _dangerous_git_config_key(key: str) -> bool:
    normalized = key.casefold()
    return (
        normalized in {"core.sshcommand", "extensions.partialclone"}
        or re.fullmatch(r"remote\..+\.promisor", normalized) is not None
        or re.fullmatch(r"remote\..+\.partialclonefilter", normalized) is not None
    )


def _decode_git_path(
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


def _optional_git_path(
    *,
    git_path: Path,
    repository_root: Path,
    relative_name: str,
    label: str,
) -> Path:
    value = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-path", relative_name),
            label=label,
            max_stdout_bytes=64 * 1024,
        ),
        label=label,
    )
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return _normalized_absolute_path(candidate)


def _reject_nonempty_optional_git_file(path: Path, *, label: str) -> None:
    try:
        state = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise WrapperError(
            f"{label}_unavailable: {path}: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if stat.S_ISLNK(state.st_mode) or not stat.S_ISREG(state.st_mode):
        raise WrapperError(
            f"{label}_not_protected_regular_file: {path}",
            exit_kind="trusted_git_error",
        )
    payload = read_regular_file(path, label=label, max_bytes=1024 * 1024)
    if payload.strip():
        raise WrapperError(
            f"{label}_rejected: {path}",
            exit_kind="trusted_git_error",
        )


def _reject_promisor_markers(object_store: Path, *, label: str) -> None:
    pack_dir = object_store / "pack"
    try:
        state = pack_dir.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise WrapperError(
            f"{label}_pack_directory_unavailable: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if stat.S_ISLNK(state.st_mode) or not stat.S_ISDIR(state.st_mode):
        raise WrapperError(
            f"{label}_pack_directory_not_protected",
            exit_kind="trusted_git_error",
        )
    with DirectoryChain.open(pack_dir, label=f"{label}_pack_directory") as chain:
        try:
            with os.scandir(chain.final_fd) as entries:
                for entry in entries:
                    if entry.name.casefold().endswith(".promisor"):
                        raise WrapperError(
                            f"{label}_promisor_pack_marker_rejected",
                            exit_kind="trusted_git_error",
                        )
        except WrapperError:
            raise
        except OSError as exc:
            raise WrapperError(
                f"{label}_pack_directory_scan_failed: {exc}",
                exit_kind="trusted_git_error",
            ) from exc


def _verify_git_local_only_repository_state(
    *,
    git_path: Path,
    repository_root: Path,
    label: str,
) -> tuple[Path, Path]:
    common_dir = _decode_git_path(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-common-dir"),
            label=f"{label}_git_common_dir",
            max_stdout_bytes=64 * 1024,
        ),
        repository_root=repository_root,
        label=f"{label}_git_common_dir",
    )
    object_store = _decode_git_path(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", "--git-path", "objects"),
            label=f"{label}_git_object_store",
            max_stdout_bytes=64 * 1024,
        ),
        repository_root=repository_root,
        label=f"{label}_git_object_store",
    )
    config_raw = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("config", "--null", "--show-scope", "--list"),
        label=f"{label}_git_config",
        max_stdout_bytes=MAX_GIT_CONFIG_BYTES,
    )
    for scope, key, value in _parse_scoped_git_config(
        config_raw,
        label=label,
    ):
        if scope in {"local", "worktree"} and _dangerous_git_config_key(key):
            raise WrapperError(
                f"{label}_git_remote_object_boundary_config_rejected: "
                f"scope={scope!r} key={key!r} value={value!r}",
                exit_kind="trusted_git_error",
            )
    for alternate in ("objects/info/alternates", "objects/info/http-alternates"):
        _reject_nonempty_optional_git_file(
            _optional_git_path(
                git_path=git_path,
                repository_root=repository_root,
                relative_name=alternate,
                label=f"{label}_{alternate.replace('/', '_')}_path",
            ),
            label=f"{label}_{alternate.replace('/', '_')}",
        )
    _reject_nonempty_optional_git_file(
        _optional_git_path(
            git_path=git_path,
            repository_root=repository_root,
            relative_name="shallow",
            label=f"{label}_shallow_path",
        ),
        label=f"{label}_shallow_repository",
    )
    _reject_promisor_markers(object_store, label=label)
    return common_dir, object_store


def _verify_independent_git_storage(
    *,
    subject_storage: tuple[Path, Path],
    control_storage: tuple[Path, Path],
    subject_root: Path,
    control_root: Path,
) -> None:
    for subject_path in subject_storage:
        for control_path in control_storage:
            if paths_overlap(subject_path, control_path):
                raise WrapperError(
                    "subject_and_control_plane_git_storage_must_be_independent: "
                    f"subject={subject_path} control_plane={control_path}",
                    exit_kind="trusted_git_error",
                )
    for subject_path in subject_storage:
        if path_is_within(subject_path, control_root):
            raise WrapperError(
                f"subject_git_storage_inside_control_plane_checkout: {subject_path}",
                exit_kind="trusted_git_error",
            )
    for control_path in control_storage:
        if path_is_within(control_path, subject_root):
            raise WrapperError(
                f"control_plane_git_storage_inside_subject_checkout: {control_path}",
                exit_kind="trusted_git_error",
            )


def _verified_repository_blob(
    *,
    git_path: Path,
    repository_root: Path,
    revision: str,
    repository_path: str,
    label: str,
    max_bytes: int,
    require_working_tree_equality: bool = True,
    preflight: bool = False,
) -> VerifiedFile:
    canonical_sha40(revision, label=f"{label}_revision")
    canonical = canonical_member_path(repository_path, label=f"{label}_path")
    if preflight:
        _verify_git_repository(
            git_path=git_path,
            repository_root=repository_root,
            expected_revision=revision,
            label=label,
        )
        _verify_git_local_only_repository_state(
            git_path=git_path,
            repository_root=repository_root,
            label=label,
        )
    object_id = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("rev-parse", f"{revision}:{canonical}"),
            label=f"{label}_object_id",
            max_stdout_bytes=4096,
        ),
        label=f"{label}_object_id",
    ).lower()
    canonical_sha40(object_id, label=f"{label}_object_id")
    object_type = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("cat-file", "-t", object_id),
            label=f"{label}_object_type",
            max_stdout_bytes=4096,
        ),
        label=f"{label}_object_type",
    )
    if object_type != "blob":
        raise WrapperError(
            f"{label}_object_not_blob: observed={object_type!r}",
            exit_kind="trusted_git_error",
        )
    size_text = _decode_single_line(
        _run_git(
            git_path=git_path,
            repository_root=repository_root,
            arguments=("cat-file", "-s", object_id),
            label=f"{label}_object_size",
            max_stdout_bytes=4096,
        ),
        label=f"{label}_object_size",
    )
    try:
        size = int(size_text, 10)
    except ValueError as exc:
        raise WrapperError(
            f"{label}_object_size_invalid: {size_text!r}",
            exit_kind="trusted_git_error",
        ) from exc
    if size < 0 or size > max_bytes:
        raise WrapperError(
            f"{label}_object_size_out_of_bounds: size={size} maximum={max_bytes}",
            exit_kind="trusted_git_error",
        )
    payload = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("cat-file", "blob", object_id),
        label=f"{label}_object_content",
        max_stdout_bytes=size,
    )
    if len(payload) != size:
        raise WrapperError(
            f"{label}_object_size_changed: declared={size} actual={len(payload)}",
            exit_kind="trusted_git_error",
        )
    if git_blob_sha1(payload) != object_id:
        raise WrapperError(
            f"{label}_object_id_mismatch",
            exit_kind="trusted_git_error",
        )
    path = repository_root / PurePosixPath(canonical)
    if require_working_tree_equality:
        working = read_regular_file(path, label=f"{label}_working_tree", max_bytes=max_bytes)
        if working != payload:
            raise WrapperError(
                f"{label}_working_tree_differs_from_exact_revision",
                exit_kind="trusted_git_error",
            )
    return VerifiedFile(
        role=label,
        repository_root=repository_root,
        revision=revision,
        repository_path=canonical,
        path=path,
        payload=payload,
        git_blob_sha1=object_id,
        sha256=sha256_bytes(payload),
    )


# ---------------------------------------------------------------------------
# Verified module loading and dependency-origin closure
# ---------------------------------------------------------------------------


def _interpreter_roots() -> tuple[Path, ...]:
    candidates: list[Path] = []
    for value in sysconfig.get_paths().values():
        if isinstance(value, str) and value:
            candidates.append(_normalized_absolute_path(Path(value)))
    for value in (sys.base_prefix, sys.base_exec_prefix, sys.prefix, sys.exec_prefix):
        if value:
            candidates.append(_normalized_absolute_path(Path(value)))
    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return tuple(result)


def _prepare_protected_import_environment(
    *,
    subject_root: Path,
    control_root: Path,
    staging_root: Path,
) -> tuple[Path, ...]:
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise WrapperError(
            "isolated_python_runtime_required: launch with python -I",
            exit_kind="python_runtime_boundary_error",
        )
    for name in tuple(sys.modules):
        if name in {"jsonschema", "yaml"} or name.startswith(
            ("jsonschema.", "yaml.")
        ):
            raise WrapperError(
                f"validation_dependency_preloaded: {name}",
                exit_kind="python_runtime_boundary_error",
            )
    roots = _interpreter_roots()
    for root in roots:
        if (
            paths_overlap(root, subject_root)
            or paths_overlap(root, control_root)
            or paths_overlap(root, staging_root)
        ):
            raise WrapperError(
                f"interpreter_root_overlaps_untrusted_surface: {root}",
                exit_kind="python_runtime_boundary_error",
            )
    approved_sys_path: list[str] = []
    for raw in sys.path:
        if not raw:
            continue
        candidate = _normalized_absolute_path(Path(raw))
        if any(path_is_within(candidate, root) or same_target(candidate, root) for root in roots):
            approved_sys_path.append(str(candidate))
    if not approved_sys_path:
        raise WrapperError(
            "protected_interpreter_search_path_empty",
            exit_kind="python_runtime_boundary_error",
        )
    sys.path[:] = approved_sys_path
    sys.path_importer_cache.clear()
    sys.meta_path[:] = [
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        importlib.machinery.PathFinder,
    ]
    sys.dont_write_bytecode = True
    return roots


def _load_verified_module(
    *,
    verified: VerifiedFile,
    module_name: str,
) -> Any:
    previous = sys.modules.get(module_name)
    had_previous = module_name in sys.modules
    module = types.ModuleType(module_name)
    module.__file__ = str(verified.path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = verified.sha256
    module.__pulsemech_verified_revision__ = verified.revision
    sys.modules[module_name] = module
    try:
        code = compile(
            verified.payload,
            str(verified.path),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[module_name] = previous
        else:
            sys.modules.pop(module_name, None)
        raise WrapperError(
            f"verified_module_load_failed: module={module_name!r} "
            f"error={type(exc).__name__}: {exc}",
            exit_kind="module_bootstrap_error",
        ) from exc
    return module


def _verify_loaded_module_origins(
    *,
    before_modules: set[str],
    approved_roots: tuple[Path, ...],
    approved_exact_paths: Iterable[Path],
) -> None:
    exact = {
        os.path.normcase(str(_normalized_absolute_path(path)))
        for path in approved_exact_paths
    }
    for name in sorted(set(sys.modules) - before_modules):
        module = sys.modules.get(name)
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or not origin:
            continue
        candidate = _normalized_absolute_path(Path(origin))
        key = os.path.normcase(str(candidate))
        if key in exact:
            continue
        if not any(path_is_within(candidate, root) or same_target(candidate, root) for root in approved_roots):
            raise WrapperError(
                f"loaded_module_origin_outside_protected_roots: "
                f"module={name!r} origin={candidate}",
                exit_kind="module_bootstrap_error",
            )


def _require_callable(module: Any, name: str, *, label: str) -> Callable[..., Any]:
    value = getattr(module, name, None)
    if not callable(value):
        raise WrapperError(
            f"{label}_callable_missing: {name}",
            exit_kind="module_bootstrap_error",
        )
    return value


def _verify_module_identities(
    *,
    carrier_module: Any,
    expectation_validator: Any,
    subject_validator: Any,
    producer_core: Any,
) -> None:
    identities = (
        (
            carrier_module,
            {
                "TOOL_NAME": "load_pulsemech_compute_current_run_export_carrier_v0",
                "TOOL_VERSION": "0.1.0",
                "DOCUMENT_TYPE": "pulsemech_compute_current_run_export_carrier",
            },
            "carrier_loader",
        ),
        (
            expectation_validator,
            {
                "TOOL_NAME": "check_pulsemech_compute_current_run_export_expectation_v0",
                "TOOL_VERSION": "0.1.0",
                "SCHEMA_VERSION": "pulsemech_compute_current_run_export_expectation_v0",
                "DOCUMENT_TYPE": "pulsemech_compute_current_run_export_expectation",
            },
            "expectation_validator",
        ),
        (
            subject_validator,
            {
                "TOOL_NAME": "check_pulsemech_compute_subject_input_packet_v0",
                "SCHEMA_VERSION": OUTPUT_SCHEMA_VERSION,
                "PACKET_TYPE": OUTPUT_PACKET_TYPE,
            },
            "subject_input_validator",
        ),
        (
            producer_core,
            {
                "TOOL_ID": "build_pulsemech_compute_subject_input_packet_v0",
                "TOOL_VERSION": "0.1.0",
                "SCHEMA_VERSION": OUTPUT_SCHEMA_VERSION,
                "PACKET_TYPE": OUTPUT_PACKET_TYPE,
            },
            "producer_core",
        ),
    )
    for module, expected, label in identities:
        for field, value in expected.items():
            if getattr(module, field, None) != value:
                raise WrapperError(
                    f"{label}_{field}_mismatch: "
                    f"expected={value!r} actual={getattr(module, field, None)!r}",
                    exit_kind="module_bootstrap_error",
                )
    for module, names, label in (
        (
            carrier_module,
            (
                "OpenedCarrier",
                "_slug",
                "_atomic_write_external",
            ),
            "carrier_loader",
        ),
        (
            expectation_validator,
            (
                "validate_instance",
                "semantic_checks",
                "build_diagnostic",
                "render_json",
            ),
            "expectation_validator",
        ),
        (
            subject_validator,
            (
                "load_json_bytes",
                "load_yaml_bytes",
                "parse_utc",
                "schema_errors",
                "build_diagnostic",
            ),
            "subject_input_validator",
        ),
        (
            producer_core,
            (
                "ProducerProfile",
                "PacketInputs",
                "validate_profile",
                "build_artifacts",
                "role_bindings",
                "build_subject_and_sources",
                "producer_identity",
                "build_packet",
                "validate_generated_packet",
                "render_json",
            ),
            "producer_core",
        ),
    ):
        for name in names:
            _require_callable(module, name, label=label)


# ---------------------------------------------------------------------------
# Exact expectation and control-plane binding
# ---------------------------------------------------------------------------


def _expected_component_map(expectation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    control = expectation.get("trusted_control_plane")
    if not isinstance(control, dict):
        raise WrapperError("expectation_trusted_control_plane_not_object")
    components = control.get("components")
    if not isinstance(components, dict):
        raise WrapperError("expectation_control_plane_components_not_object")
    return components


def _verify_expectation_header(
    *,
    expectation: dict[str, Any],
    expectation_bytes: bytes,
    expectation_sha256: str,
    subject_repository: str,
    subject_revision: str,
    control_repository: str,
    control_revision: str,
    producer_run_key: str,
    packet_created_utc: str,
) -> None:
    if expectation_bytes != render_json(expectation):
        raise WrapperError(
            "expectation_not_canonical_json",
            exit_kind="strict_json_error",
        )
    require_equal(
        sha256_bytes(expectation_bytes),
        expectation_sha256,
        label="expectation_sha256",
    )
    require_equal(
        expectation.get("schema_version"),
        "pulsemech_compute_current_run_export_expectation_v0",
        label="expectation_schema_version",
    )
    require_equal(
        expectation.get("document_type"),
        "pulsemech_compute_current_run_export_expectation",
        label="expectation_document_type",
    )
    require_equal(expectation.get("record_status"), "observed", label="record_status")
    require_equal(expectation.get("ok"), True, label="expectation_ok")
    require_equal(expectation.get("errors"), [], label="expectation_errors")
    require_equal(
        expectation.get("packet_contract"),
        EXPECTED_PACKET_CONTRACT,
        label="packet_contract",
    )
    require_equal(
        expectation.get("content_boundary"),
        EXPECTED_EXPECTATION_CONTENT_BOUNDARY,
        label="expectation_content_boundary",
    )
    require_equal(
        expectation.get("authority_boundary"),
        EXPECTED_EXPECTATION_AUTHORITY_BOUNDARY,
        label="expectation_authority_boundary",
    )
    if "fixture_provenance" in expectation:
        raise WrapperError("observed_expectation_must_not_contain_fixture_provenance")

    subject = expectation.get("subject")
    if not isinstance(subject, dict):
        raise WrapperError("expectation_subject_not_object")
    require_equal(subject.get("repository"), subject_repository, label="subject_repository")
    require_equal(subject.get("source_commit"), subject_revision, label="subject_revision")
    require_equal(
        subject.get("subject_run_key"),
        producer_run_key,
        label="subject_run_key",
    )
    identity = expectation.get("expectation_identity")
    if not isinstance(identity, dict):
        raise WrapperError("expectation_identity_not_object")
    require_equal(
        identity.get("expectation_scope"),
        "current_run_export",
        label="expectation_scope",
    )
    require_equal(
        identity.get("subject_run_key"),
        producer_run_key,
        label="expectation_subject_run_key",
    )
    expectation_time = parse_utc(
        identity.get("expectation_created_utc"),
        label="expectation_created_utc",
    )
    packet_time = parse_utc(packet_created_utc, label="packet_created_utc")
    if packet_time < expectation_time:
        raise WrapperError(
            "packet_created_before_expectation: "
            f"packet={packet_created_utc} expectation={identity.get('expectation_created_utc')}",
            exit_kind="time_binding_error",
        )

    control = expectation.get("trusted_control_plane")
    if not isinstance(control, dict):
        raise WrapperError("expectation_trusted_control_plane_not_object")
    require_equal(control.get("repository"), control_repository, label="control_repository")
    require_equal(control.get("revision"), control_revision, label="control_revision")
    require_equal(control.get("trust_mode"), "protected_exact_revision", label="control_trust_mode")
    require_equal(control.get("checkout_role"), "protected_control_plane", label="control_checkout_role")
    require_equal(control.get("separate_from_subject_checkout"), True, label="control_separation")
    require_equal(control.get("subject_may_select_revision"), False, label="control_subject_selection")


def _verify_control_plane_components(
    *,
    expectation: dict[str, Any],
    git_path: Path,
    control_root: Path,
    control_revision: str,
) -> dict[str, VerifiedFile]:
    components = _expected_component_map(expectation)
    expected_names = {name for name, _path, _version in CONTROL_PLANE_COMPONENT_SPECS}
    if set(components) != expected_names:
        raise WrapperError(
            "control_plane_component_set_mismatch: "
            f"expected={sorted(expected_names)!r} actual={sorted(components)!r}",
            exit_kind="component_binding_error",
        )
    result: dict[str, VerifiedFile] = {}
    for name, expected_path, expected_version in CONTROL_PLANE_COMPONENT_SPECS:
        binding = components.get(name)
        if not isinstance(binding, dict):
            raise WrapperError(
                f"control_plane_component_not_object: {name}",
                exit_kind="component_binding_error",
            )
        require_equal(binding.get("path"), expected_path, label=f"{name}_path")
        require_equal(
            binding.get("source_revision"),
            control_revision,
            label=f"{name}_revision",
        )
        require_equal(binding.get("version"), expected_version, label=f"{name}_version")
        expected_sha = canonical_sha256(binding.get("sha256"), label=f"{name}_sha256")
        verified = _verified_repository_blob(
            git_path=git_path,
            repository_root=control_root,
            revision=control_revision,
            repository_path=expected_path,
            label=f"control_component_{name}",
            max_bytes=MAX_COMPONENT_BYTES,
        )
        require_equal(verified.sha256, expected_sha, label=f"{name}_sha256")
        result[name] = verified

    executed = _normalized_absolute_path(Path(__file__))
    wrapper = result["subject_input_producer_wrapper"]
    if os.path.normcase(str(executed)) != os.path.normcase(str(wrapper.path)):
        raise WrapperError(
            f"executed_wrapper_path_mismatch: executed={executed} expected={wrapper.path}",
            exit_kind="component_binding_error",
        )
    if read_regular_file(executed, label="executed_wrapper", max_bytes=MAX_COMPONENT_BYTES) != wrapper.payload:
        raise WrapperError(
            "executed_wrapper_bytes_differ_from_exact_control_plane_revision",
            exit_kind="component_binding_error",
        )

    expectation_producer = expectation.get("expectation_producer")
    if not isinstance(expectation_producer, dict):
        raise WrapperError("expectation_producer_not_object")
    builder = result["expectation_builder"]
    require_equal(
        expectation_producer.get("producer_source"),
        builder.repository_path,
        label="expectation_producer_source",
    )
    require_equal(
        expectation_producer.get("producer_source_revision"),
        control_revision,
        label="expectation_producer_revision",
    )
    require_equal(
        expectation_producer.get("producer_source_sha256"),
        builder.sha256,
        label="expectation_producer_sha256",
    )
    require_equal(
        expectation_producer.get("producer_version"),
        "0.1.0",
        label="expectation_producer_version",
    )
    require_equal(
        expectation_producer.get("production_mode"),
        "current_run_expectation_builder",
        label="expectation_producer_mode",
    )
    return result


def _authority_source_rows(expectation: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    sources = expectation.get("authority_sources")
    if not isinstance(sources, dict):
        raise WrapperError("expectation_authority_sources_not_object")
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in ("workflow", "policy", "gate_registry"):
        value = sources.get(name)
        if not isinstance(value, dict):
            raise WrapperError(f"expectation_authority_source_not_object: {name}")
        rows.append((name, value))
    additional = sources.get("additional_sources")
    if not isinstance(additional, list):
        raise WrapperError("expectation_additional_sources_not_array")
    for index, value in enumerate(additional):
        if not isinstance(value, dict):
            raise WrapperError(
                f"expectation_additional_source_not_object: index={index}"
            )
        rows.append((f"additional_sources[{index}]", value))
    return rows


def _verify_subject_authority_sources(
    *,
    expectation: dict[str, Any],
    git_path: Path,
    subject_root: Path,
    subject_revision: str,
) -> dict[str, VerifiedFile]:
    result: dict[str, VerifiedFile] = {}
    source_ids: set[str] = set()
    for label, row in _authority_source_rows(expectation):
        source_id = non_empty_text(row.get("source_id"), label=f"{label}_source_id")
        if source_id in source_ids:
            raise WrapperError(
                f"duplicate_authority_source_id: {source_id}",
                exit_kind="authority_source_binding_error",
            )
        source_ids.add(source_id)
        require_equal(
            row.get("source_revision"),
            subject_revision,
            label=f"{label}_source_revision",
        )
        path = canonical_member_path(row.get("path_or_uri"), label=f"{label}_path")
        expected_sha = canonical_sha256(row.get("sha256"), label=f"{label}_sha256")
        expected_size = row.get("size_bytes")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise WrapperError(
                f"{label}_size_invalid: {expected_size!r}",
                exit_kind="authority_source_binding_error",
            )
        verified = _verified_repository_blob(
            git_path=git_path,
            repository_root=subject_root,
            revision=subject_revision,
            repository_path=path,
            label=f"subject_authority_source_{label}",
            max_bytes=MAX_AUTHORITY_SOURCE_BYTES,
        )
        require_equal(verified.sha256, expected_sha, label=f"{label}_sha256")
        require_equal(len(verified.payload), expected_size, label=f"{label}_size")
        result[source_id] = verified
    return result


def _canonical_packet_authority_sources(
    expectation_sources: Any,
) -> dict[str, Any]:
    if not isinstance(expectation_sources, Mapping):
        raise WrapperError(
            "expectation_authority_sources_not_object",
            exit_kind="authority_source_binding_error",
        )
    result: dict[str, Any] = {}
    used_ids: set[str] = set()
    for name in ("workflow", "policy", "gate_registry"):
        row = expectation_sources.get(name)
        if not isinstance(row, Mapping):
            raise WrapperError(
                f"expectation_authority_source_not_object: {name}",
                exit_kind="authority_source_binding_error",
            )
        require_equal(
            row.get("source_id"),
            GENERIC_EXPECTATION_SOURCE_IDS[name],
            label=f"expectation_{name}_source_id",
        )
        projected = dict(row)
        projected["source_id"] = CANONICAL_PACKET_SOURCE_IDS[name]
        if projected["source_id"] in used_ids:
            raise WrapperError(
                f"canonical_packet_source_id_duplicate: {projected['source_id']}",
                exit_kind="authority_source_binding_error",
            )
        used_ids.add(projected["source_id"])
        result[name] = projected

    additional = expectation_sources.get("additional_sources")
    if not isinstance(additional, list):
        raise WrapperError(
            "expectation_additional_sources_not_array",
            exit_kind="authority_source_binding_error",
        )
    projected_additional: list[dict[str, Any]] = []
    for index, row in enumerate(additional):
        if not isinstance(row, Mapping):
            raise WrapperError(
                f"expectation_additional_source_not_object: index={index}",
                exit_kind="authority_source_binding_error",
            )
        role = non_empty_text(
            row.get("role"),
            label=f"expectation_additional_source_role_{index}",
        )
        path = canonical_member_path(
            row.get("path_or_uri"),
            label=f"expectation_additional_source_path_{index}",
        )
        source_id = CANONICAL_ADDITIONAL_SOURCE_IDS.get((role, path))
        if source_id is None:
            raise WrapperError(
                "expectation_additional_source_has_no_canonical_packet_identity: "
                f"role={role!r} path={path!r}",
                exit_kind="authority_source_binding_error",
            )
        if source_id in used_ids:
            raise WrapperError(
                f"canonical_packet_source_id_duplicate: {source_id}",
                exit_kind="authority_source_binding_error",
            )
        used_ids.add(source_id)
        projected = dict(row)
        projected["source_id"] = source_id
        projected_additional.append(projected)
    projected_additional.sort(key=lambda row: str(row["source_id"]))
    result["additional_sources"] = projected_additional
    return result


# ---------------------------------------------------------------------------
# Generic current-run preservation carrier verification
# ---------------------------------------------------------------------------


def _zip_member_name(value: str, *, label: str) -> str:
    if not value or "\x00" in value or "\\" in value or value.endswith("/"):
        raise WrapperError(
            f"{label}_member_name_invalid: {value!r}",
            exit_kind="carrier_content_error",
        )
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise WrapperError(
            f"{label}_member_path_unsafe: {value!r}",
            exit_kind="carrier_content_error",
        )
    if pure.as_posix() != value:
        raise WrapperError(
            f"{label}_member_path_noncanonical: {value!r}",
            exit_kind="carrier_content_error",
        )
    return value


def _zip_entry_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _read_zip_payloads(
    payload: bytes,
    *,
    label: str,
    budget: UncompressedByteBudget,
) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise WrapperError(
            f"{label}_invalid_zip: {exc}",
            exit_kind="carrier_content_error",
        ) from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            raise WrapperError(
                f"{label}_too_many_members: count={len(infos)} maximum={MAX_ARCHIVE_MEMBERS}",
                exit_kind="carrier_content_error",
            )
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise WrapperError(
                f"{label}_duplicate_member",
                exit_kind="carrier_content_error",
            )
        result: dict[str, bytes] = {}
        for info in infos:
            name = _zip_member_name(info.filename, label=label)
            if info.is_dir():
                raise WrapperError(
                    f"{label}_directory_member: {name}",
                    exit_kind="carrier_content_error",
                )
            if _zip_entry_is_symlink(info):
                raise WrapperError(
                    f"{label}_symlink_member: {name}",
                    exit_kind="carrier_content_error",
                )
            if info.flag_bits & 0x1:
                raise WrapperError(
                    f"{label}_encrypted_member: {name}",
                    exit_kind="carrier_content_error",
                )
            if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise WrapperError(
                    f"{label}_unsupported_compression: member={name!r} type={info.compress_type}",
                    exit_kind="carrier_content_error",
                )
            if info.file_size < 0 or info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                raise WrapperError(
                    f"{label}_member_too_large: member={name!r} size={info.file_size}",
                    exit_kind="carrier_content_error",
                )
            budget.reserve(
                info.file_size,
                label=f"{label}_member_{name}",
            )
            try:
                with archive.open(info, "r") as member:
                    chunks: list[bytes] = []
                    total = 0
                    while True:
                        chunk = member.read(
                            min(
                                READ_CHUNK_BYTES,
                                MAX_ARCHIVE_MEMBER_BYTES - total + 1,
                            )
                        )
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > info.file_size or total > MAX_ARCHIVE_MEMBER_BYTES:
                            raise WrapperError(
                                f"{label}_member_expanded_beyond_declared_size: {name}",
                                exit_kind="carrier_content_error",
                            )
                        chunks.append(chunk)
                    member_payload = b"".join(chunks)
            except zipfile.BadZipFile as exc:
                raise WrapperError(
                    f"{label}_member_crc_failure: member={name!r} error={exc}",
                    exit_kind="carrier_content_error",
                ) from exc
            if len(member_payload) != info.file_size:
                raise WrapperError(
                    f"{label}_member_size_mismatch: member={name!r} "
                    f"declared={info.file_size} actual={len(member_payload)}",
                    exit_kind="carrier_content_error",
                )
            result[name] = member_payload
        return result


def _parse_sha256sums(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"preservation_sha256sums_invalid_utf8: {exc}",
            exit_kind="carrier_content_error",
        ) from exc
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        digest, separator, path = line.partition("  ")
        if separator != "  ":
            raise WrapperError(
                f"preservation_sha256sums_invalid_line: {raw_line!r}",
                exit_kind="carrier_content_error",
            )
        canonical_sha256(digest.lower(), label="preservation_sha256sum")
        canonical_member_path(path, label="preservation_sha256sum_path")
        if path in result:
            raise WrapperError(
                f"preservation_sha256sums_duplicate_path: {path}",
                exit_kind="carrier_content_error",
            )
        result[path] = digest.lower()
    return result


def _validate_preservation_manifest(
    *,
    manifest: dict[str, Any],
    expectation: dict[str, Any],
    provider_names: dict[str, str],
    provider_payloads: dict[str, bytes],
) -> dict[str, dict[str, Any]]:
    subject = expectation["subject"]
    require_equal(
        manifest.get("schema_id"),
        "pulse_ci_release_grade_artifact_preservation_manifest_v0",
        label="preservation_manifest_schema_id",
    )
    require_equal(
        manifest.get("schema_version"),
        "0.1.0",
        label="preservation_manifest_schema_version",
    )
    bindings = (
        ("repository", subject.get("repository")),
        ("workflow", subject.get("workflow_name")),
        ("workflow_run_id", subject.get("workflow_run_id")),
        ("workflow_run_number", subject.get("workflow_run_number")),
        ("workflow_run_attempt", subject.get("workflow_run_attempt")),
        ("source_commit", subject.get("source_commit")),
        ("source_ref", subject.get("source_ref")),
        ("run_mode", subject.get("run_mode")),
        ("active_policy_sets", subject.get("active_policy_sets")),
    )
    for field, expected in bindings:
        require_equal(
            manifest.get(field),
            expected,
            label=f"preservation_manifest_{field}",
        )
    expected_primary = "allow" if subject.get("decision") == "ALLOW" else "block"
    require_equal(
        manifest.get("primary_gate_result"),
        expected_primary,
        label="preservation_manifest_primary_gate_result",
    )
    require_equal(
        manifest.get("authority_boundary"),
        PRESERVATION_AUTHORITY_BOUNDARY,
        label="preservation_manifest_authority_boundary",
    )
    rows = manifest.get("github_artifacts")
    if not isinstance(rows, list):
        raise WrapperError(
            "preservation_manifest_github_artifacts_not_array",
            exit_kind="carrier_content_error",
        )
    indexed: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(rows):
        if not isinstance(value, dict):
            raise WrapperError(
                f"preservation_manifest_artifact_not_object: index={index}",
                exit_kind="carrier_content_error",
            )
        name = canonical_leaf_name(
            value.get("file_name"),
            label=f"provider_file_name_{index}",
        )
        if name in indexed:
            raise WrapperError(
                f"preservation_manifest_duplicate_artifact: {name}",
                exit_kind="carrier_content_error",
            )
        indexed[name] = value
    if set(indexed) != set(provider_names.values()):
        raise WrapperError(
            "preservation_manifest_provider_names_mismatch: "
            f"expected={sorted(provider_names.values())!r} actual={sorted(indexed)!r}",
            exit_kind="carrier_content_error",
        )
    for role_name, file_name in provider_names.items():
        row = indexed[file_name]
        require_equal(
            row.get("role"),
            PROVIDER_ARCHIVE_ROLES[role_name],
            label=f"provider_role_{role_name}",
        )
        payload = provider_payloads[file_name]
        digest = sha256_bytes(payload)
        size = len(payload)
        require_equal(row.get("github_sha256"), digest, label=f"provider_sha_{file_name}")
        require_equal(row.get("downloaded_sha256"), digest, label=f"provider_downloaded_sha_{file_name}")
        require_equal(row.get("size_bytes"), size, label=f"provider_size_{file_name}")
        require_equal(row.get("downloaded_size_bytes"), size, label=f"provider_downloaded_size_{file_name}")
        require_equal(row.get("github_digest_match"), True, label=f"provider_digest_match_{file_name}")
        require_equal(row.get("github_size_match"), True, label=f"provider_size_match_{file_name}")
        if not isinstance(row.get("artifact_id"), (int, str)):
            raise WrapperError(
                f"provider_artifact_id_invalid: {file_name}",
                exit_kind="carrier_content_error",
            )
        non_empty_text(row.get("artifact_name"), label=f"provider_artifact_name_{file_name}")
        parse_utc(row.get("created_at"), label=f"provider_created_at_{file_name}")
        parse_utc(row.get("expires_at"), label=f"provider_expires_at_{file_name}")
    return indexed


def _validate_package_inventory(
    *,
    members: dict[str, bytes],
    inventory: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require_equal(
        inventory.get("schema_version"),
        "release_grade_reference_package_digest_inventory_v0",
        label="package_inventory_schema_version",
    )
    require_equal(inventory.get("algorithm"), "sha256", label="package_inventory_algorithm")
    rows = inventory.get("files")
    if not isinstance(rows, list):
        raise WrapperError(
            "package_inventory_files_not_array",
            exit_kind="carrier_content_error",
        )
    require_equal(inventory.get("file_count"), len(rows), label="package_inventory_file_count")
    indexed: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(rows):
        if not isinstance(value, dict):
            raise WrapperError(
                f"package_inventory_row_not_object: index={index}",
                exit_kind="carrier_content_error",
            )
        path = canonical_member_path(value.get("path"), label=f"package_inventory_path_{index}")
        if path in indexed:
            raise WrapperError(
                f"package_inventory_duplicate_path: {path}",
                exit_kind="carrier_content_error",
            )
        if path not in members:
            raise WrapperError(
                f"package_inventory_member_missing: {path}",
                exit_kind="carrier_content_error",
            )
        payload = members[path]
        require_equal(value.get("size_bytes"), len(payload), label=f"package_inventory_size_{path}")
        require_equal(value.get("sha256"), sha256_bytes(payload), label=f"package_inventory_sha256_{path}")
        indexed[path] = value
    if set(members) != set(indexed) | {"package_digest_inventory_v0.json"}:
        raise WrapperError(
            "complete_package_member_set_mismatch",
            exit_kind="carrier_content_error",
        )
    return indexed


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppressed_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.lower() in {"script", "style"}:
            self._suppressed_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._suppressed_depth > 0:
            self._suppressed_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth == 0 and data.strip():
            self.parts.append(data)


def _visible_html_text(value: str) -> str:
    parser = _VisibleTextExtractor()
    parser.feed(value)
    parser.close()
    return " ".join(" ".join(parser.parts).split()).lower()


def _iter_string_values(
    value: Any,
    path: str = "$",
) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, str):
        result.append((path, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.extend(_iter_string_values(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            result.extend(_iter_string_values(item, f"{path}.{key}"))
    return result


def _stub_scan_exempt(relative: str, json_path: str) -> bool:
    if any(
        relative == exempt_relative and json_path.startswith(exempt_prefix)
        for exempt_relative, exempt_prefix in STUB_SCAN_EXEMPT_PATH_PREFIXES
    ):
        return True
    normalized = JSON_ARRAY_INDEX_RE.sub("[*]", json_path)
    return any(
        relative == exempt_relative and normalized == exempt_path
        for exempt_relative, exempt_path in STUB_SCAN_EXEMPT_NORMALIZED_PATHS
    )


def _require_non_stub_json(
    document: Mapping[str, Any],
    *,
    relative: str,
) -> None:
    hits: list[str] = []
    for json_path, value in _iter_string_values(document):
        if _stub_scan_exempt(relative, json_path):
            continue
        lowered = value.lower()
        for marker in STUB_MARKERS:
            if marker in lowered:
                hits.append(f"{json_path}:{marker}")
    if hits:
        raise WrapperError(
            f"package_non_stub_json_failed: path={relative!r} hits={hits[:20]!r}",
            exit_kind="carrier_content_error",
        )


def _nested_get(value: Any, path: Sequence[str]) -> Any:
    current = value
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def _canonical_slsa_run_key(binding: Any) -> str | None:
    if not isinstance(binding, Mapping):
        return None
    values = tuple(
        _as_text(binding.get(field))
        for field in (
            "current_run_id",
            "current_run_number",
            "current_run_attempt",
            "workflow_name",
        )
    )
    if not all(isinstance(value, str) and value for value in values):
        return None
    run_id, run_number, run_attempt, workflow_name = values
    return (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_NUMBER={run_number}"
        f"|GITHUB_RUN_ATTEMPT={run_attempt}|GITHUB_WORKFLOW={workflow_name}"
    )


def _report_checks_by_id(
    *,
    document: dict[str, Any],
    label: str,
) -> dict[str, dict[str, Any]]:
    checks = document.get("checks")
    if not isinstance(checks, list) or not checks:
        raise WrapperError(
            f"{label}_checks_missing_or_empty",
            exit_kind="carrier_content_error",
        )
    indexed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            raise WrapperError(
                f"{label}_check_not_object: index={index}",
                exit_kind="carrier_content_error",
            )
        check_id = non_empty_text(
            item.get("check_id"),
            label=f"{label}_check_id_{index}",
        )
        if check_id in indexed:
            raise WrapperError(
                f"{label}_duplicate_check_id: {check_id}",
                exit_kind="carrier_content_error",
            )
        if item.get("passed") is not True:
            raise WrapperError(
                f"{label}_check_failed: {check_id}",
                exit_kind="carrier_content_error",
            )
        non_empty_text(
            item.get("details"),
            label=f"{label}_check_details_{check_id}",
        )
        indexed[check_id] = item

    summary = document.get("summary")
    if not isinstance(summary, dict):
        raise WrapperError(
            f"{label}_summary_not_object",
            exit_kind="carrier_content_error",
        )
    require_equal(
        summary.get("checks_total"),
        len(checks),
        label=f"{label}_checks_total",
    )
    require_equal(
        summary.get("checks_failed"),
        0,
        label=f"{label}_checks_failed",
    )
    return indexed


def _inventory_check_ids(
    *,
    inventory_rows: Mapping[str, Mapping[str, Any]],
    report_kind: str,
) -> set[str]:
    if report_kind == "completeness":
        result = {
            "digest_inventory.schema_version",
            "digest_inventory.algorithm",
            "digest_inventory.unique_paths",
            "digest_inventory.file_count",
            "digest_inventory.exact_coverage",
        }
    elif report_kind == "verification":
        result = {
            "digest_inventory.schema",
            "digest_inventory.algorithm",
            "digest_inventory.unique_paths",
            "digest_inventory.file_count",
            "digest_inventory.no_missing_files",
        }
    else:
        raise WrapperError(
            f"report_kind_invalid: {report_kind!r}",
            exit_kind="carrier_content_error",
        )
    for path in inventory_rows:
        canonical = canonical_member_path(
            path,
            label=f"{report_kind}_inventory_check_path",
        )
        result.add(f"digest_inventory.digest:{canonical}")
        result.add(f"digest_inventory.size_bytes:{canonical}")
    return result


def _parse_jsonl_objects(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"{label}_invalid_utf8: {exc}",
            exit_kind="carrier_content_error",
        ) from exc
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        value = parse_json_bytes(
            raw.encode("utf-8"),
            label=f"{label}_line_{line_number}",
        )
        if not isinstance(value, dict):
            raise WrapperError(
                f"{label}_line_not_object: line={line_number}",
                exit_kind="carrier_content_error",
            )
        records.append(value)
    if not records:
        raise WrapperError(
            f"{label}_empty",
            exit_kind="carrier_content_error",
        )
    return records


def _require_member(
    members: Mapping[str, bytes],
    path: str,
    *,
    non_empty: bool = False,
) -> bytes:
    payload = members.get(path)
    if payload is None:
        raise WrapperError(
            f"package_required_member_missing: {path}",
            exit_kind="carrier_content_error",
        )
    if non_empty and not payload:
        raise WrapperError(
            f"package_required_member_empty: {path}",
            exit_kind="carrier_content_error",
        )
    return payload


def _require_directory_members(
    members: Mapping[str, bytes],
    directory: str,
) -> None:
    prefix = canonical_member_path(
        directory,
        label="package_required_directory",
    ) + "/"
    if not any(path.startswith(prefix) for path in members):
        raise WrapperError(
            f"package_required_directory_empty: {directory}",
            exit_kind="carrier_content_error",
        )


def _replay_slsa_completeness(
    *,
    members: Mapping[str, bytes],
    loaded: dict[str, dict[str, Any]],
) -> set[str]:
    present = {path: path in members for path in SLSA_TRUSTED_PRODUCER_FILES}
    if not any(present.values()):
        return {"slsa_vsa.trusted_producer.current_contract_optional"}
    if not all(present.values()):
        raise WrapperError(
            "slsa_vsa_trusted_producer_pair_incomplete",
            exit_kind="carrier_content_error",
        )

    result: set[str] = set()
    for path in SLSA_TRUSTED_PRODUCER_FILES:
        result.add(f"slsa_vsa.required_file:{path}")
        document = parse_json_object(
            _require_member(members, path, non_empty=True),
            label=f"slsa_vsa_{path}",
        )
        _require_non_stub_json(document, relative=path)
        loaded[path] = document
        result.add(f"json_object:{path}")
        result.add(f"non_stub_json:{path}")

    packet = loaded[SLSA_PACKET_PATH]
    report = loaded[SLSA_REPORT_PATH]
    require_equal(
        packet.get("schema_version"),
        "slsa_vsa_trusted_producer_input_packet_v0",
        label="slsa_packet_schema_version",
    )
    require_equal(
        packet.get("packet_type"),
        "slsa_vsa_trusted_producer_input_packet",
        label="slsa_packet_type",
    )
    require_equal(
        packet.get("recorded_signal_mode"),
        "recorded_signal_only",
        label="slsa_packet_recorded_signal_mode",
    )
    require_equal(
        packet.get("candidate_set"),
        "slsa_vsa_recorded_intake_candidate",
        label="slsa_packet_candidate_set",
    )
    require_equal(
        report.get("schema_version"),
        "slsa_vsa_trusted_evidence_producer_report_v0",
        label="slsa_report_schema_version",
    )
    require_equal(
        report.get("report_type"),
        "slsa_vsa_trusted_evidence_producer_report",
        label="slsa_report_type",
    )
    require(
        report.get("ok") is True
        and report.get("producer_decision") == "TRUSTED_EVIDENCE_ACCEPTED"
        and report.get("failed_checks") == [],
        "slsa_report_not_accepted",
    )
    require_equal(
        report.get("recorded_signal_mode"),
        "recorded_signal_only",
        label="slsa_report_recorded_signal_mode",
    )
    require_equal(
        report.get("candidate_set"),
        "slsa_vsa_recorded_intake_candidate",
        label="slsa_report_candidate_set",
    )

    producer_fields = (
        "producer_id",
        "producer_name",
        "producer_version",
        "producer_source",
        "ci_workflow_or_job_identity",
    )
    packet_producer = packet.get("producer_identity")
    report_producer = report.get("producer")
    require(
        isinstance(packet_producer, Mapping)
        and isinstance(report_producer, Mapping)
        and all(
            isinstance(packet_producer.get(field), str)
            and packet_producer.get(field) == report_producer.get(field)
            for field in producer_fields
        ),
        "slsa_producer_identity_mismatch",
    )

    packet_run = packet.get("run_binding")
    report_run = report.get("run_binding")
    packet_run_key = _nested_get(packet, ("run_binding", "current_run_key"))
    report_run_key = _nested_get(report, ("run_binding", "current_run_key"))
    require_equal(
        packet_run_key,
        _canonical_slsa_run_key(packet_run),
        label="slsa_packet_run_key",
    )
    require_equal(
        report_run_key,
        _canonical_slsa_run_key(report_run),
        label="slsa_report_run_key",
    )
    require_equal(packet_run_key, report_run_key, label="slsa_current_run_key")
    run_fields = (
        "current_run_id",
        "current_run_number",
        "current_run_attempt",
        "workflow_name",
        "job_name",
        "commit_sha",
        "release_candidate_id",
    )
    require(
        isinstance(packet_run, Mapping)
        and isinstance(report_run, Mapping)
        and all(
            _as_text(packet_run.get(field)) is not None
            and _as_text(packet_run.get(field)) == _as_text(report_run.get(field))
            for field in run_fields
        ),
        "slsa_run_fields_mismatch",
    )

    packet_artifact = packet.get("artifact_binding")
    report_artifact = report.get("artifact_binding")
    require(
        isinstance(packet_artifact, Mapping)
        and isinstance(report_artifact, Mapping)
        and _nested_get(packet, ("artifact_binding", "subject_name"))
        == _nested_get(report, ("artifact_binding", "subject_name"))
        and _nested_get(packet, ("artifact_binding", "resource_uri"))
        == _nested_get(report, ("artifact_binding", "resource_uri"))
        and _nested_get(packet, ("artifact_binding", "release_candidate_id"))
        == _nested_get(report, ("artifact_binding", "release_candidate_id"))
        and _nested_get(packet, ("artifact_binding", "subject_sha256"))
        == _nested_get(packet, ("artifact_binding", "artifact_digest_sha256"))
        == _nested_get(report, ("artifact_binding", "subject_sha256"))
        == _nested_get(report, ("artifact_binding", "artifact_digest_sha256")),
        "slsa_artifact_identity_mismatch",
    )
    require(
        report_artifact.get("subject_digest_matches") is True
        and report_artifact.get("resource_uri_matches") is True
        and report_artifact.get("release_candidate_matches") is True
        and report_artifact.get("artifact_digest_matches") is True,
        "slsa_artifact_flags_invalid",
    )

    packet_policy = packet.get("policy_binding")
    report_policy = report.get("policy_binding")
    require(
        isinstance(packet_policy, Mapping)
        and isinstance(report_policy, Mapping)
        and _nested_get(packet, ("policy_binding", "expected_policy_id"))
        == _nested_get(report, ("policy_binding", "expected_policy_id"))
        == _nested_get(report, ("policy_binding", "evidence_policy_id"))
        and _nested_get(packet, ("policy_binding", "expected_policy_uri"))
        == _nested_get(report, ("policy_binding", "expected_policy_uri"))
        == _nested_get(report, ("policy_binding", "evidence_policy_uri"))
        and _nested_get(packet, ("policy_binding", "expected_policy_sha256"))
        == _nested_get(report, ("policy_binding", "expected_policy_sha256"))
        == _nested_get(report, ("policy_binding", "evidence_policy_sha256"))
        and report_policy.get("policy_identity_matches") is True
        and report_policy.get("policy_digest_matches") is True,
        "slsa_policy_binding_mismatch",
    )
    require(
        _nested_get(packet, ("verifier_binding", "expected_verifier_id"))
        == _nested_get(report, ("verifier_binding", "expected_verifier_id"))
        == _nested_get(report, ("verifier_binding", "evidence_verifier_id"))
        and _nested_get(report, ("verifier_binding", "verifier_trusted")) is True,
        "slsa_verifier_binding_mismatch",
    )
    require_equal(
        _nested_get(report, ("evidence", "verification_result")),
        "PASSED",
        label="slsa_verification_result",
    )
    packet_level = packet.get("expected_verified_level")
    require(
        isinstance(packet_level, str)
        and packet_level == _nested_get(report, ("evidence", "expected_verified_level"))
        and isinstance(_nested_get(report, ("evidence", "evidence_verified_levels")), list)
        and packet_level in _nested_get(report, ("evidence", "evidence_verified_levels"))
        and _nested_get(report, ("evidence", "verified_level_ok")) is True,
        "slsa_verified_level_mismatch",
    )
    require(
        _nested_get(packet, ("freshness", "expected_time_verified"))
        == _nested_get(report, ("evidence", "time_verified"))
        and _nested_get(report, ("freshness", "freshness_result"))
        == "fresh_current_run"
        and _nested_get(report, ("freshness", "current_run_binding_ok")) is True
        and _nested_get(
            report,
            ("freshness", "time_verified_current_run_match"),
        ) is True,
        "slsa_freshness_mismatch",
    )

    result.update(
        {
            "slsa_vsa.packet.schema_version",
            "slsa_vsa.packet.packet_type",
            "slsa_vsa.packet.recorded_signal_mode",
            "slsa_vsa.packet.candidate_set",
            "slsa_vsa.report.schema_version",
            "slsa_vsa.report.report_type",
            "slsa_vsa.report.accepted",
            "slsa_vsa.report.recorded_signal_mode",
            "slsa_vsa.report.candidate_set",
            "slsa_vsa.producer_identity",
            "slsa_vsa.packet_run_key_self_consistent",
            "slsa_vsa.report_run_key_self_consistent",
            "slsa_vsa.current_run_key",
            "slsa_vsa.run_fields",
            "slsa_vsa.artifact_digest",
            "slsa_vsa.artifact_flags",
            "slsa_vsa.policy_binding",
            "slsa_vsa.verifier_binding",
            "slsa_vsa.verification_result",
            "slsa_vsa.verified_level",
            "slsa_vsa.freshness",
        }
    )
    return result


def _replay_completeness_semantics(
    *,
    members: Mapping[str, bytes],
    inventory: Mapping[str, Any],
    inventory_rows: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    result: set[str] = set()
    for path in PACKAGE_REQUIRED_FILES:
        _require_member(members, path, non_empty=True)
        result.add(f"required_file:{path}")
        result.add(f"non_empty_file:{path}")
    for directory in PACKAGE_REQUIRED_DIRS:
        _require_directory_members(members, directory)
        result.add(f"required_dir:{directory}")

    loaded: dict[str, dict[str, Any]] = {}
    for path in PACKAGE_JSON_OBJECT_FILES:
        document = parse_json_object(
            _require_member(members, path, non_empty=True),
            label=f"package_json_{path}",
        )
        _require_non_stub_json(document, relative=path)
        loaded[path] = document
        result.add(f"json_object:{path}")
        result.add(f"non_stub_json:{path}")
    for path in PACKAGE_JSONL_FILES:
        _parse_jsonl_objects(
            _require_member(members, path, non_empty=True),
            label=f"package_jsonl_{path}",
        )
        result.add(f"jsonl:{path}")

    status = loaded["artifacts/status.json"]
    gates = status.get("gates")
    diagnostics = status.get("diagnostics")
    require(
        isinstance(gates, Mapping)
        and gates.get("detectors_materialized_ok") is True,
        "package_status_detectors_not_materialized",
    )
    require(
        isinstance(diagnostics, Mapping)
        and diagnostics.get("gates_stubbed") is False,
        "package_status_gates_stubbed",
    )
    require(
        isinstance(diagnostics, Mapping)
        and diagnostics.get("scaffold") is False,
        "package_status_scaffolded",
    )
    result.update(
        {
            "status.release_grade.detectors_materialized_ok",
            "status.release_grade.gates_stubbed_false",
            "status.release_grade.scaffold_false",
        }
    )

    try:
        report_card = _require_member(
            members,
            "artifacts/report_card.html",
            non_empty=True,
        ).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"report_card_invalid_utf8: {exc}",
            exit_kind="carrier_content_error",
        ) from exc
    visible = _visible_html_text(report_card)
    require(
        REPORT_CARD_CLEAR_MARKER_SEQUENCE in visible,
        "report_card_marker_state_not_clear",
    )
    marker_hits = [
        marker for marker in REPORT_CARD_NON_STUB_MARKERS if marker in visible
    ]
    active_hits = [
        phrase for phrase in REPORT_CARD_ACTIVE_STUB_PHRASES if phrase in visible
    ]
    require(
        not marker_hits and not active_hits,
        f"report_card_active_stub_state: markers={marker_hits!r} phrases={active_hits!r}",
    )
    result.update({"report_card.marker_state_clear", "report_card.non_stub"})

    result.update(
        _inventory_check_ids(
            inventory_rows=inventory_rows,
            report_kind="completeness",
        )
    )
    require_equal(
        inventory.get("schema_version"),
        "release_grade_reference_package_digest_inventory_v0",
        label="completeness_inventory_schema",
    )
    require_equal(
        inventory.get("algorithm"),
        "sha256",
        label="completeness_inventory_algorithm",
    )
    require_equal(
        inventory.get("file_count"),
        len(inventory_rows),
        label="completeness_inventory_file_count",
    )
    require_equal(
        set(members),
        set(inventory_rows) | {"package_digest_inventory_v0.json"},
        label="completeness_inventory_coverage",
    )

    candidate_prefix = "artifacts/recorded_release_candidates/"
    candidates = sorted(
        path
        for path in members
        if path.startswith(candidate_prefix) and path.endswith(".json")
    )
    require(bool(candidates), "recorded_release_candidates_empty")
    result.add("recorded_candidates.non_empty")
    for path in candidates:
        document = parse_json_object(
            _require_member(members, path, non_empty=True),
            label=f"recorded_candidate_{path}",
        )
        validation = document.get("validation")
        require(
            isinstance(validation, Mapping)
            and validation.get("status") in {"passed", "verified", "accepted"},
            f"recorded_candidate_not_validated: {path}",
        )
        result.add(f"recorded_candidate.json:{path}")
        result.add(f"recorded_candidate.validation:{path}")

    result.update(_replay_slsa_completeness(members=members, loaded=loaded))
    return result


def _expected_verification_identity(subject: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "repository": non_empty_text(
            subject.get("repository"),
            label="verification_subject_repository",
        ),
        "git_sha": canonical_sha40(
            subject.get("source_commit"),
            label="verification_subject_git_sha",
        ),
        "workflow_ref": non_empty_text(
            subject.get("workflow_ref"),
            label="verification_subject_workflow_ref",
        ),
        "run_id": positive_int(
            subject.get("workflow_run_id"),
            label="verification_subject_run_id",
        ),
        "run_attempt": positive_int(
            subject.get("workflow_run_attempt"),
            label="verification_subject_run_attempt",
        ),
        "run_key": non_empty_text(
            subject.get("subject_run_key"),
            label="verification_subject_run_key",
        ),
    }


def _replay_verification_semantics(
    *,
    members: Mapping[str, bytes],
    inventory: Mapping[str, Any],
    inventory_rows: Mapping[str, Mapping[str, Any]],
    subject: Mapping[str, Any],
) -> set[str]:
    result: set[str] = set()
    expected = _expected_verification_identity(subject)
    for path in PACKAGE_REQUIRED_FILES:
        _require_member(members, path, non_empty=True)
        result.add(f"required_file:{path}")
    for directory in PACKAGE_REQUIRED_DIRS:
        _require_directory_members(members, directory)
        result.add(f"required_dir:{directory}")

    loaded: dict[str, dict[str, Any]] = {}
    for path in PACKAGE_JSON_OBJECT_FILES:
        loaded[path] = parse_json_object(
            _require_member(members, path, non_empty=True),
            label=f"verification_json_{path}",
        )
        result.add(f"json:{path}")

    result.update(
        _inventory_check_ids(
            inventory_rows=inventory_rows,
            report_kind="verification",
        )
    )
    require_equal(
        inventory.get("schema_version"),
        "release_grade_reference_package_digest_inventory_v0",
        label="verification_inventory_schema",
    )
    require_equal(
        inventory.get("algorithm"),
        "sha256",
        label="verification_inventory_algorithm",
    )
    require_equal(
        inventory.get("file_count"),
        len(inventory_rows),
        label="verification_inventory_file_count",
    )
    require_equal(
        set(members),
        set(inventory_rows) | {"package_digest_inventory_v0.json"},
        label="verification_inventory_coverage",
    )

    metadata = loaded["run_metadata_v0.json"]
    for field in ("repository", "workflow_ref", "run_key"):
        require_equal(
            metadata.get(field),
            expected[field],
            label=f"verification_metadata_{field}",
        )
        result.add(f"metadata.{field}")
    require_equal(
        str(metadata.get("git_sha", "")).lower(),
        expected["git_sha"],
        label="verification_metadata_git_sha",
    )
    result.add("metadata.git_sha")
    require_equal(
        metadata.get("run_id"),
        expected["run_id"],
        label="verification_metadata_run_id",
    )
    require_equal(
        metadata.get("run_attempt"),
        expected["run_attempt"],
        label="verification_metadata_run_attempt",
    )
    result.update({"metadata.run_id", "metadata.run_attempt"})
    metadata_boundary = metadata.get("authority_boundary")
    require(
        isinstance(metadata_boundary, Mapping)
        and metadata_boundary.get("authorizes_release") is False
        and metadata_boundary.get("package_only") is True,
        "verification_metadata_authority_boundary_invalid",
    )
    result.add("metadata.authority_boundary")

    raw_records = _parse_jsonl_objects(
        _require_member(
            members,
            "artifacts/external/llamaguard_raw.jsonl",
            non_empty=True,
        ),
        label="verification_llamaguard_raw",
    )
    result.add("llamaguard.raw.record_count")
    for index, record in enumerate(raw_records):
        run = record.get("run")
        require(isinstance(run, Mapping), f"llamaguard_raw_run_missing:{index}")
        for field, expected_field in (
            ("repository", "repository"),
            ("git_sha", "git_sha"),
            ("run_key", "run_key"),
            ("workflow_ref", "workflow_ref"),
        ):
            actual = run.get(field)
            target = expected[expected_field]
            if field == "git_sha" and isinstance(actual, str):
                actual = actual.lower()
            require_equal(
                actual,
                target,
                label=f"verification_llamaguard_raw_{index}_{field}",
            )
            result.add(f"llamaguard.raw[{index}].{field}")

    evaluator_path = "artifacts/external/llamaguard_evaluator_manifest_v0.json"
    evaluator = loaded[evaluator_path]
    evaluator_run = evaluator.get("run")
    require(isinstance(evaluator_run, Mapping), "llamaguard_evaluator_run_missing")
    for field, expected_field in (
        ("repository", "repository"),
        ("git_sha", "git_sha"),
        ("run_key", "run_key"),
        ("workflow_ref", "workflow_ref"),
    ):
        actual = evaluator_run.get(field)
        target = expected[expected_field]
        if field == "git_sha" and isinstance(actual, str):
            actual = actual.lower()
        require_equal(
            actual,
            target,
            label=f"verification_llamaguard_evaluator_{field}",
        )
        result.add(f"llamaguard.evaluator.{field}")

    summary_path = "artifacts/external/llamaguard_summary.json"
    summary = loaded[summary_path]
    summary_extensions = summary.get("extensions")
    require(
        isinstance(summary_extensions, Mapping),
        "llamaguard_summary_extensions_missing",
    )
    require_equal(
        summary_extensions.get("repository"),
        expected["repository"],
        label="verification_llamaguard_summary_repository",
    )
    require_equal(
        str(summary_extensions.get("source_commit", "")).lower(),
        expected["git_sha"],
        label="verification_llamaguard_summary_source_commit",
    )
    result.update(
        {"llamaguard.summary.repository", "llamaguard.summary.source_commit"}
    )
    summary_run = summary.get("run")
    require(isinstance(summary_run, Mapping), "llamaguard_summary_run_missing")
    require_equal(
        summary_run.get("run_id"),
        expected["run_key"],
        label="verification_llamaguard_summary_run_key",
    )
    result.add("llamaguard.summary.run_key")

    envelope_path = "artifacts/external/llamaguard_summary.envelope.json"
    envelope = loaded[envelope_path]
    envelope_extensions = envelope.get("extensions")
    require(
        isinstance(envelope_extensions, Mapping),
        "llamaguard_envelope_extensions_missing",
    )
    for field, expected_field in (
        ("repository", "repository"),
        ("source_commit", "git_sha"),
        ("workflow_ref", "workflow_ref"),
    ):
        actual = envelope_extensions.get(field)
        target = expected[expected_field]
        if field == "source_commit" and isinstance(actual, str):
            actual = actual.lower()
        require_equal(
            actual,
            target,
            label=f"verification_llamaguard_envelope_{field}",
        )
        result.add(f"llamaguard.envelope.{field}")

    raw_path = "artifacts/external/llamaguard_raw.jsonl"
    raw_payload = members[raw_path]
    evaluator_payload = members[evaluator_path]
    summary_payload = members[summary_path]
    bundle_path = "artifacts/external/llamaguard_summary.bundle.json"
    bundle_payload = members[bundle_path]
    envelope_payload = members[envelope_path]
    evidence = summary.get("evidence")
    require(isinstance(evidence, Mapping), "llamaguard_summary_evidence_missing")
    require(
        evidence.get("raw_artifact_uri")
        in {raw_path, "PULSE_safe_pack_v0/" + raw_path},
        "llamaguard_summary_raw_path_invalid",
    )
    require_equal(
        evidence.get("raw_artifact_digest"),
        sha256_bytes(raw_payload),
        label="verification_llamaguard_summary_raw_digest",
    )
    result.update({"llamaguard.summary.raw_path", "llamaguard.summary.raw_digest"})
    evaluator_digest = summary_extensions.get("evaluator_manifest_sha256")
    if evaluator_digest is None:
        evaluator_digest = summary_extensions.get("evaluator_sha256")
    require_equal(
        evaluator_digest,
        sha256_bytes(evaluator_payload),
        label="verification_llamaguard_summary_evaluator_digest",
    )
    result.add("llamaguard.summary.evaluator_digest")

    summary_digest = envelope.get("summary_digest")
    require(isinstance(summary_digest, Mapping), "envelope_summary_digest_missing")
    require(
        summary_digest.get("algorithm") == "sha256"
        and summary_digest.get("value") == sha256_bytes(summary_payload),
        "envelope_summary_digest_invalid",
    )
    result.add("llamaguard.envelope.summary_digest")
    signing = envelope.get("signing")
    require(isinstance(signing, Mapping), "envelope_signing_missing")
    require(
        signing.get("bundle_uri")
        in {bundle_path, "PULSE_safe_pack_v0/" + bundle_path},
        "envelope_bundle_uri_invalid",
    )
    result.add("llamaguard.envelope.bundle_uri")
    require_equal(
        envelope_extensions.get("bundle_sha256"),
        sha256_bytes(bundle_payload),
        label="verification_envelope_bundle_sha256",
    )
    require_equal(
        envelope_extensions.get("raw_evidence_sha256"),
        sha256_bytes(raw_payload),
        label="verification_envelope_raw_sha256",
    )
    result.update(
        {
            "llamaguard.envelope.bundle_sha256",
            "llamaguard.envelope.raw_evidence_sha256",
        }
    )

    attestation = loaded[
        "artifacts/external/llamaguard_attestation_verifier_v1.json"
    ]
    require_equal(
        attestation.get("status"),
        "verified",
        label="verification_attestation_status",
    )
    require_equal(
        attestation.get("errors"),
        [],
        label="verification_attestation_errors",
    )
    report_summary = attestation.get("summary")
    report_envelope = attestation.get("envelope")
    require(
        isinstance(report_summary, Mapping)
        and report_summary.get("sha256") == sha256_bytes(summary_payload),
        "verification_attestation_summary_digest_invalid",
    )
    require(
        isinstance(report_envelope, Mapping)
        and report_envelope.get("sha256") == sha256_bytes(envelope_payload),
        "verification_attestation_envelope_digest_invalid",
    )
    result.update(
        {
            "llamaguard.attestation_report.status",
            "llamaguard.attestation_report.errors",
            "llamaguard.attestation_report.summary_digest",
            "llamaguard.attestation_report.envelope_digest",
        }
    )

    candidate_prefix = "artifacts/recorded_release_candidates/"
    candidates = sorted(
        path
        for path in members
        if path.startswith(candidate_prefix) and path.endswith(".json")
    )
    require(bool(candidates), "verification_recorded_candidates_empty")
    result.add("recorded_candidates.non_empty")
    for path in candidates:
        candidate = parse_json_object(
            members[path],
            label=f"verification_candidate_{path}",
        )
        require(
            isinstance(candidate.get("validation"), Mapping)
            and candidate["validation"].get("status") == "passed",
            f"verification_candidate_not_passed:{path}",
        )
        boundary = candidate.get("authority_boundary")
        require(
            isinstance(boundary, Mapping)
            and boundary.get("creates_release_authority") is False
            and boundary.get("eligible_without_verifier") is False,
            f"verification_candidate_authority_boundary_invalid:{path}",
        )
        result.add(f"recorded_candidate.validation:{path}")
        result.add(f"recorded_candidate.authority_boundary:{path}")

    recorded_verifier = loaded[
        "artifacts/recorded_release_evidence_verifier_v0.json"
    ]
    require(
        (recorded_verifier.get("status") or recorded_verifier.get("decision"))
        in {"VERIFIED", "verified", "passed"},
        "recorded_verifier_status_invalid",
    )
    result.add("recorded_verifier.status")
    if "errors" in recorded_verifier:
        require_equal(
            recorded_verifier.get("errors"),
            [],
            label="recorded_verifier_errors",
        )
        result.add("recorded_verifier.errors")
    require(
        bool(loaded["artifacts/release_evidence_input_manifest_v0.json"]),
        "verification_input_manifest_empty",
    )
    require(
        bool(loaded["artifacts/recorded_release_candidate_index_v0.json"]),
        "verification_candidate_index_empty",
    )
    result.update({"input_manifest.object", "candidate_index.object"})

    status = loaded["artifacts/status.json"]
    baseline = loaded["artifacts/status_baseline.json"]
    for label, document, prefix in (
        ("status", status, "status"),
        ("baseline", baseline, "baseline"),
    ):
        metrics = document.get("metrics")
        require(isinstance(metrics, Mapping), f"verification_{label}_metrics_missing")
        require_equal(
            str(metrics.get("git_sha", "")).lower(),
            expected["git_sha"],
            label=f"verification_{label}_git_sha",
        )
        require_equal(
            metrics.get("run_key"),
            expected["run_key"],
            label=f"verification_{label}_run_key",
        )
        result.add(f"{prefix}.git_sha")
        result.add(f"{prefix}.run_key")
    require(
        bool(loaded["artifacts/release_decision_v0.json"]),
        "verification_release_decision_empty",
    )
    require(
        bool(loaded["artifacts/artifact_provenance_binding_v0.json"]),
        "verification_artifact_provenance_empty",
    )
    require(
        bool(loaded["artifacts/release_authority_v0.json"]),
        "verification_release_authority_empty",
    )
    result.update(
        {
            "release_decision.object",
            "artifact_provenance_binding.object",
            "release_authority_manifest.object",
        }
    )
    return result


def _validate_check_report(
    *,
    document: dict[str, Any],
    schema_version: str,
    status_field: str,
    status_value: Any,
    label: str,
    report_kind: str,
    members: Mapping[str, bytes],
    inventory: Mapping[str, Any],
    inventory_rows: Mapping[str, Mapping[str, Any]],
    subject: Mapping[str, Any],
) -> None:
    require_equal(
        document.get("schema_version"),
        schema_version,
        label=f"{label}_schema_version",
    )
    require_equal(
        document.get(status_field),
        status_value,
        label=f"{label}_{status_field}",
    )
    require_equal(document.get("errors"), [], label=f"{label}_errors")

    if report_kind == "completeness":
        require_equal(
            document.get("tool"),
            COMPLETENESS_REPORT_TOOL,
            label=f"{label}_tool",
        )
        require_equal(
            document.get("authority_boundary"),
            COMPLETENESS_REPORT_AUTHORITY_BOUNDARY,
            label=f"{label}_authority_boundary",
        )
        require_equal(document.get("ok"), True, label=f"{label}_ok")
        required_ids = _replay_completeness_semantics(
            members=members,
            inventory=inventory,
            inventory_rows=inventory_rows,
        )
        summary = document.get("summary")
        require(
            isinstance(summary, Mapping),
            f"{label}_summary_not_object",
        )
        require_equal(
            summary.get("required_files"),
            len(PACKAGE_REQUIRED_FILES),
            label=f"{label}_required_files",
        )
        require_equal(
            summary.get("required_dirs"),
            len(PACKAGE_REQUIRED_DIRS),
            label=f"{label}_required_dirs",
        )
    elif report_kind == "verification":
        require_equal(
            document.get("tool"),
            VERIFICATION_REPORT_TOOL,
            label=f"{label}_tool",
        )
        require_equal(
            document.get("authority_boundary"),
            VERIFICATION_REPORT_AUTHORITY_BOUNDARY,
            label=f"{label}_authority_boundary",
        )
        require_equal(document.get("verified"), True, label=f"{label}_verified")
        parse_utc(document.get("checked_utc"), label=f"{label}_checked_utc")
        required_ids = _replay_verification_semantics(
            members=members,
            inventory=inventory,
            inventory_rows=inventory_rows,
            subject=subject,
        )
    else:
        raise WrapperError(
            f"report_kind_invalid: {report_kind!r}",
            exit_kind="carrier_content_error",
        )

    package = document.get("package")
    if not isinstance(package, dict):
        raise WrapperError(
            f"{label}_package_not_object",
            exit_kind="carrier_content_error",
        )
    non_empty_text(package.get("path"), label=f"{label}_package_path")

    checks_by_id = _report_checks_by_id(document=document, label=label)
    observed_ids = set(checks_by_id)
    missing = sorted(required_ids - observed_ids)
    unexpected = sorted(observed_ids - required_ids)
    if missing or unexpected:
        raise WrapperError(
            f"{label}_check_identity_set_mismatch: "
            f"missing={missing!r} unexpected={unexpected!r}",
            exit_kind="carrier_content_error",
        )

def _single_member_archive(
    *,
    payload: bytes,
    expected_member: str,
    label: str,
    budget: UncompressedByteBudget,
) -> bytes:
    members = _read_zip_payloads(
        payload,
        label=label,
        budget=budget,
    )
    if set(members) != {expected_member}:
        raise WrapperError(
            f"{label}_member_set_mismatch: {sorted(members)!r}",
            exit_kind="carrier_content_error",
        )
    return members[expected_member]

def load_current_run_bundle(
    *,
    carrier_path: Path,
    carrier_bytes: bytes,
    expectation: dict[str, Any],
    max_total_uncompressed_bytes: int,
) -> CurrentRunBundle:
    budget = UncompressedByteBudget(
        maximum=positive_int(
            max_total_uncompressed_bytes,
            label="max_total_uncompressed_bytes",
        )
    )
    carrier = expectation["carrier"]
    layout = expectation["archive_layout"]
    outer_prefix = canonical_directory_prefix(layout.get("outer_prefix"), label="archive_outer_prefix")
    original_prefix = canonical_directory_prefix(
        layout.get("original_artifacts_prefix"),
        label="archive_original_artifacts_prefix",
    )
    if not original_prefix.startswith(outer_prefix):
        raise WrapperError(
            "archive_original_prefix_outside_outer_prefix",
            exit_kind="carrier_content_error",
        )
    require_equal(carrier.get("root_prefix"), outer_prefix, label="carrier_root_prefix")
    require_equal(layout.get("layout_id"), "pulsemech_current_run_export_layout_v0", label="archive_layout_id")
    require_equal(layout.get("layout_version"), "0.1.0", label="archive_layout_version")
    require_equal(layout.get("artifact_count_derivation"), "provider_plus_non_provider", label="artifact_count_derivation")

    visible = layout.get("visible_members")
    if not isinstance(visible, dict):
        raise WrapperError("archive_visible_members_not_object", exit_kind="carrier_content_error")
    manifest_name = canonical_leaf_name(
        visible.get("preservation_manifest_name"),
        label="preservation_manifest_name",
    )
    readme_name = canonical_leaf_name(
        visible.get("preservation_readme_name"),
        label="preservation_readme_name",
    )
    sums_name = canonical_leaf_name(
        visible.get("preservation_checksums_name"),
        label="preservation_checksums_name",
    )
    provider_names = {
        "complete": canonical_leaf_name(layout.get("complete_package_name"), label="complete_package_name"),
        "completeness": canonical_leaf_name(layout.get("completeness_archive_name"), label="completeness_archive_name"),
        "verification": canonical_leaf_name(layout.get("verification_archive_name"), label="verification_archive_name"),
    }
    if len(set(provider_names.values())) != len(provider_names):
        raise WrapperError("provider_archive_names_not_unique", exit_kind="carrier_content_error")
    require_equal(
        layout.get("expected_provider_artifact_count"),
        len(provider_names),
        label="expected_provider_artifact_count",
    )

    outer = _read_zip_payloads(
        carrier_bytes,
        label="current_run_export_carrier",
        budget=budget,
    )
    visible_paths = {
        "manifest": outer_prefix + manifest_name,
        "readme": outer_prefix + readme_name,
        "sums": outer_prefix + sums_name,
    }
    provider_paths = {
        name: original_prefix + file_name
        for name, file_name in provider_names.items()
    }
    expected_outer = set(visible_paths.values()) | set(provider_paths.values())
    if set(outer) != expected_outer:
        raise WrapperError(
            "current_run_export_outer_member_set_mismatch: "
            f"expected={sorted(expected_outer)!r} actual={sorted(outer)!r}",
            exit_kind="carrier_content_error",
        )
    manifest_bytes = outer[visible_paths["manifest"]]
    readme_bytes = outer[visible_paths["readme"]]
    sums_bytes = outer[visible_paths["sums"]]
    try:
        readme_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WrapperError(
            f"preservation_readme_invalid_utf8: {exc}",
            exit_kind="carrier_content_error",
        ) from exc
    if not readme_bytes:
        raise WrapperError("preservation_readme_empty", exit_kind="carrier_content_error")

    provider_payloads = {
        file_name: outer[provider_paths[role]]
        for role, file_name in provider_names.items()
    }
    manifest = parse_json_object(manifest_bytes, label="preservation_manifest")
    provider_rows = _validate_preservation_manifest(
        manifest=manifest,
        expectation=expectation,
        provider_names=provider_names,
        provider_payloads=provider_payloads,
    )
    sums = _parse_sha256sums(sums_bytes)
    original_relative_prefix = original_prefix[len(outer_prefix) :]
    if not original_relative_prefix:
        raise WrapperError(
            "archive_original_prefix_not_nested_below_outer_prefix",
            exit_kind="carrier_content_error",
        )
    expected_sums = {
        manifest_name: sha256_bytes(manifest_bytes),
        readme_name: sha256_bytes(readme_bytes),
        **{
            original_relative_prefix + file_name: sha256_bytes(payload)
            for file_name, payload in provider_payloads.items()
        },
    }
    require_equal(sums, expected_sums, label="preservation_sha256sums")

    complete_members = _read_zip_payloads(
        provider_payloads[provider_names["complete"]],
        label="complete_release_grade_reference_package",
        budget=budget,
    )
    inventory_payload = complete_members.get("package_digest_inventory_v0.json")
    if inventory_payload is None:
        raise WrapperError(
            "package_digest_inventory_missing",
            exit_kind="carrier_content_error",
        )
    inventory = parse_json_object(inventory_payload, label="package_inventory")
    inventory_rows = _validate_package_inventory(
        members=complete_members,
        inventory=inventory,
    )

    completeness_bytes = _single_member_archive(
        payload=provider_payloads[provider_names["completeness"]],
        expected_member="release_grade_package_completeness_v1.json",
        label="package_completeness_archive",
        budget=budget,
    )
    completeness = parse_json_object(
        completeness_bytes,
        label="package_completeness_report",
    )
    require_equal(completeness.get("status"), "complete", label="completeness_status")
    require_equal(completeness.get("ok"), True, label="completeness_ok")
    _validate_check_report(
        document=completeness,
        schema_version="release_grade_package_completeness_v1",
        status_field="status",
        status_value="complete",
        label="package_completeness",
        report_kind="completeness",
        members=complete_members,
        inventory=inventory,
        inventory_rows=inventory_rows,
        subject=expectation["subject"],
    )

    verification_bytes = _single_member_archive(
        payload=provider_payloads[provider_names["verification"]],
        expected_member="release_grade_reference_package_verification_v0.json",
        label="package_verification_archive",
        budget=budget,
    )
    verification = parse_json_object(
        verification_bytes,
        label="package_verification_report",
    )
    require_equal(verification.get("status"), "verified", label="verification_status")
    require_equal(verification.get("verified"), True, label="verification_verified")
    _validate_check_report(
        document=verification,
        schema_version="release_grade_reference_package_verification_v0",
        status_field="status",
        status_value="verified",
        label="package_verification",
        report_kind="verification",
        members=complete_members,
        inventory=inventory,
        inventory_rows=inventory_rows,
        subject=expectation["subject"],
    )

    expected_non_provider = positive_int(
        layout.get("expected_non_provider_artifact_count"),
        label="expected_non_provider_artifact_count",
    )
    observed_non_provider = 3 + len(complete_members) + 2
    require_equal(
        observed_non_provider,
        expected_non_provider,
        label="non_provider_artifact_count",
    )
    local = manifest.get("local_verification")
    if not isinstance(local, dict):
        raise WrapperError(
            "preservation_manifest_local_verification_not_object",
            exit_kind="carrier_content_error",
        )
    for field in (
        "all_outer_artifact_digests_match_github",
        "all_outer_artifact_sizes_match_github",
        "structural_completeness_ok",
        "independent_verification_verified",
    ):
        require_equal(local.get(field), True, label=f"manifest_local_{field}")
    if "complete_package_zip_members" in local:
        require_equal(
            local.get("complete_package_zip_members"),
            len(complete_members),
            label="manifest_complete_package_members",
        )
    if "complete_package_inventory_entries" in local:
        require_equal(
            local.get("complete_package_inventory_entries"),
            len(inventory_rows),
            label="manifest_inventory_entries",
        )
    if "structural_completeness_checks_total" in local:
        require_equal(
            local.get("structural_completeness_checks_total"),
            len(completeness["checks"]),
            label="manifest_completeness_checks_total",
        )
    if "independent_verification_checks_total" in local:
        require_equal(
            local.get("independent_verification_checks_total"),
            len(verification["checks"]),
            label="manifest_verification_checks_total",
        )

    with tempfile.TemporaryDirectory(prefix="pulsemech-current-run-visible-") as raw:
        temporary = Path(raw)
        manifest_path = temporary / manifest_name
        readme_path = temporary / readme_name
        sums_path = temporary / sums_name
        manifest_path.write_bytes(manifest_bytes)
        readme_path.write_bytes(readme_bytes)
        sums_path.write_bytes(sums_bytes)
        # These paths are diagnostic only. All bytes retained in the returned
        # bundle come from the exact in-memory carrier snapshot.
        return CurrentRunBundle(
            archive_path=carrier_path,
            archive_sha256=sha256_bytes(carrier_bytes),
            archive_size=len(carrier_bytes),
            manifest_path=manifest_path,
            manifest_bytes=manifest_bytes,
            manifest=manifest,
            readme_path=readme_path,
            readme_bytes=readme_bytes,
            sha256sums_path=sums_path,
            sha256sums_bytes=sums_bytes,
            sha256sums=sums,
            artifact_archives=provider_payloads,
            complete_package_members=complete_members,
            package_inventory=inventory,
            package_inventory_rows=inventory_rows,
            completeness_report_bytes=completeness_bytes,
            completeness_report=completeness,
            verification_report_bytes=verification_bytes,
            verification_report=verification,
        )


# ---------------------------------------------------------------------------
# Profile derivation and core/validator trust adapters
# ---------------------------------------------------------------------------


def _derive_producer_profile(
    *,
    expectation: dict[str, Any],
    producer_core: Any,
    carrier_path: Path,
) -> Any:
    profile = expectation.get("packet_producer_profile")
    carrier = expectation.get("carrier")
    layout = expectation.get("archive_layout")
    subject = expectation.get("subject")
    if not all(isinstance(value, dict) for value in (profile, carrier, layout, subject)):
        raise WrapperError("expectation_profile_carrier_layout_or_subject_invalid")
    expected_profile = {
        "expected_producer_source_path": WRAPPER_SOURCE_PATH,
        "expected_production_mode": "current_run_export",
        "expected_packet_scope": "current_run",
        "expected_packet_identity_mode": "current-run",
        "expected_carrier_kind": "current_run_export_archive",
        "expected_carrier_media_type": "application/zip",
        "expected_carrier_artifact_payload_mode": "external_carrier",
        "expected_repository": subject.get("repository"),
        "expected_source_commit": subject.get("source_commit"),
        "expected_subject_run_key": subject.get("subject_run_key"),
        "expected_archive_layout_id": "pulsemech_current_run_export_layout_v0",
    }
    for field, expected in expected_profile.items():
        require_equal(profile.get(field), expected, label=f"packet_producer_profile_{field}")
    require_equal(profile.get("expected_signer_policy_path"), "policy/external_signers_v1.yml", label="profile_signer_policy_path")
    provider_count = positive_int(
        layout.get("expected_provider_artifact_count"),
        label="expected_provider_artifact_count",
    )
    non_provider_count = positive_int(
        layout.get("expected_non_provider_artifact_count"),
        label="expected_non_provider_artifact_count",
    )
    profile_class = producer_core.ProducerProfile
    derived = profile_class(
        profile_id=non_empty_text(profile.get("profile_id"), label="profile_id"),
        producer_source_path=WRAPPER_SOURCE_PATH,
        default_carrier=carrier_path,
        production_mode="current_run_export",
        packet_scope="current_run",
        packet_identity_mode="current-run",
        carrier_id_namespace=non_empty_text(
            profile.get("expected_carrier_id_namespace"),
            label="carrier_id_namespace",
        ),
        carrier_kind="current_run_export_archive",
        carrier_media_type="application/zip",
        carrier_artifact_payload_mode="external_carrier",
        expected_carrier_sha256=canonical_sha256(
            carrier.get("sha256"),
            label="carrier_sha256",
        ),
        expected_carrier_size=positive_int(
            carrier.get("size_bytes"),
            label="carrier_size_bytes",
        ),
        expected_repository=non_empty_text(subject.get("repository"), label="subject_repository"),
        expected_source_commit=canonical_sha40(subject.get("source_commit"), label="subject_source_commit"),
        expected_run_key=non_empty_text(subject.get("subject_run_key"), label="subject_run_key"),
        outer_prefix=canonical_directory_prefix(layout.get("outer_prefix"), label="outer_prefix"),
        original_prefix=canonical_directory_prefix(
            layout.get("original_artifacts_prefix"),
            label="original_artifacts_prefix",
        ),
        complete_package_name=canonical_leaf_name(layout.get("complete_package_name"), label="complete_package_name"),
        completeness_archive_name=canonical_leaf_name(layout.get("completeness_archive_name"), label="completeness_archive_name"),
        verification_archive_name=canonical_leaf_name(layout.get("verification_archive_name"), label="verification_archive_name"),
        expected_provider_artifact_count=provider_count,
        expected_artifact_count=provider_count + non_provider_count,
        expected_signer_policy_path="policy/external_signers_v1.yml",
    )
    return producer_core.validate_profile(derived)


def _bind_hardened_git_interfaces(
    *,
    producer_core: Any,
    subject_validator: Any,
    trusted_git: Path,
    subject_root: Path,
    subject_revision: str,
    control_root: Path,
    control_revision: str,
    control_files: Mapping[str, VerifiedFile],
    authority_files: Mapping[str, VerifiedFile],
) -> None:
    subject_key = os.path.normcase(str(subject_root))
    control_key = os.path.normcase(str(control_root))

    def expected_revision_for_root(root: Path, supplied: str | None = None) -> str:
        normalized = os.path.normcase(str(_normalized_absolute_path(root)))
        if normalized == subject_key:
            expected = subject_revision
        elif normalized == control_key:
            expected = control_revision
        else:
            raise WrapperError(
                f"hardened_git_repository_root_unrecognized: {root}",
                exit_kind="trusted_git_error",
            )
        if supplied is not None and supplied != expected:
            raise WrapperError(
                f"hardened_git_revision_mismatch: expected={expected} supplied={supplied}",
                exit_kind="trusted_git_error",
            )
        return expected

    def verified_root(root: Path) -> Path:
        candidate = _validated_directory_root(Path(root), label="adapter_repository_root")
        revision = expected_revision_for_root(candidate)
        _verify_git_repository(
            git_path=trusted_git,
            repository_root=candidate,
            expected_revision=revision,
            label="adapter_repository",
        )
        _verify_git_local_only_repository_state(
            git_path=trusted_git,
            repository_root=candidate,
            label="adapter_repository",
        )
        return candidate

    control_by_path = {
        item.repository_path: item for item in control_files.values()
    }
    subject_by_path = {
        item.repository_path: item for item in authority_files.values()
    }

    def blob_bytes(root: Path, *, revision: str, path: str) -> bytes:
        candidate = _validated_directory_root(Path(root), label="adapter_repository_root")
        canonical = canonical_member_path(path, label="adapter_git_blob_path")
        normalized = os.path.normcase(str(candidate))

        # The committed subject-input validator has one repository_root argument
        # for both subject authority-source replay and observed producer
        # provenance.  Route the one exact producer-source lookup to the
        # separately preverified control-plane checkout; every other lookup
        # remains rooted in the supplied checkout and exact revision.
        producer_lookup = (
            revision == control_revision
            and canonical == WRAPPER_SOURCE_PATH
            and canonical in control_by_path
        )
        if producer_lookup:
            if normalized not in {subject_key, control_key}:
                raise WrapperError(
                    f"adapter_producer_repository_root_unrecognized: {candidate}",
                    exit_kind="trusted_git_error",
                )
            record = control_by_path[canonical]
            expected = control_revision
        elif normalized == subject_key:
            expected = expected_revision_for_root(candidate, revision)
            record = subject_by_path.get(canonical)
        elif normalized == control_key:
            expected = expected_revision_for_root(candidate, revision)
            record = control_by_path.get(canonical)
        else:
            raise WrapperError(
                f"hardened_git_repository_root_unrecognized: {candidate}",
                exit_kind="trusted_git_error",
            )
        if record is None or record.revision != expected:
            raise WrapperError(
                "adapter_git_blob_not_preverified: "
                f"root={candidate} revision={revision} path={canonical!r}",
                exit_kind="trusted_git_error",
            )
        working = read_regular_file(
            record.path,
            label="adapter_git_blob_working_tree",
            max_bytes=max(MAX_COMPONENT_BYTES, MAX_AUTHORITY_SOURCE_BYTES),
        )
        if working != record.payload:
            raise WrapperError(
                f"adapter_git_blob_working_tree_changed: {canonical}",
                exit_kind="trusted_git_error",
            )
        return record.payload

    def run_isolated_git(
        root: Path,
        *,
        arguments: list[str],
        failure_prefix: str,
    ) -> bytes:
        candidate = verified_root(root)
        return _run_git(
            git_path=trusted_git,
            repository_root=candidate,
            arguments=tuple(arguments),
            label=f"adapter_{failure_prefix}",
            max_stdout_bytes=MAX_AUTHORITY_SOURCE_BYTES,
        )

    def validate_git(candidate: Path) -> Path:
        resolved = _validated_trusted_git(Path(candidate))
        require_equal(resolved, trusted_git, label="adapter_trusted_git")
        return resolved

    def trusted_git_selector() -> Path:
        return trusted_git

    for module in (producer_core, subject_validator):
        setattr(module, "_verified_git_repository_root", verified_root)
        setattr(module, "_git_blob_bytes", blob_bytes)
        setattr(module, "_run_isolated_git", run_isolated_git)
        setattr(module, "_validate_trusted_git_executable", validate_git)
        setattr(module, "_trusted_git_executable", trusted_git_selector)


def _bind_current_run_slug(*, producer_core: Any, carrier_module: Any) -> None:
    carrier_slug = _require_callable(carrier_module, "_slug", label="carrier_loader")
    builder_error = getattr(producer_core, "BuilderError", RuntimeError)

    def current_run_slug(value: str) -> str:
        try:
            return str(carrier_slug(value))
        except Exception as exc:
            raise builder_error(f"current_run_workflow_slug_invalid: {exc}") from exc

    setattr(producer_core, "slug", current_run_slug)


# ---------------------------------------------------------------------------
# Packet construction, final equivalence, and transactional output
# ---------------------------------------------------------------------------


def _carrier_snapshot_bytes(opened: Any, *, max_bytes: int) -> bytes:
    opened.verify_unchanged()
    os.lseek(opened.file_fd, 0, os.SEEK_SET)
    payload = _read_descriptor_bytes(
        opened.file_fd,
        label="current_run_carrier_snapshot",
        max_bytes=max_bytes,
        expected_size=opened.size_bytes,
    )
    opened.verify_unchanged()
    return payload


def _verify_packet_equivalence(
    *,
    packet: dict[str, Any],
    expectation: dict[str, Any],
    carrier_digest: str,
    carrier_size: int,
    profile: Any,
) -> None:
    require_equal(packet.get("schema_version"), OUTPUT_SCHEMA_VERSION, label="packet_schema_version")
    require_equal(packet.get("packet_type"), OUTPUT_PACKET_TYPE, label="packet_type")
    require_equal(packet.get("record_status"), "observed", label="packet_record_status")
    require_equal(packet.get("ok"), True, label="packet_ok")
    require_equal(packet.get("errors"), [], label="packet_errors")
    require_equal(packet.get("subject"), expectation.get("subject"), label="packet_subject")
    require_equal(
        packet.get("authority_sources"),
        _canonical_packet_authority_sources(
            expectation.get("authority_sources")
        ),
        label="packet_authority_sources",
    )
    require_equal(
        packet.get("authority_boundary"),
        EXPECTED_PACKET_AUTHORITY_BOUNDARY,
        label="packet_authority_boundary",
    )
    require_equal(
        packet.get("content_boundary"),
        EXPECTED_PACKET_CONTENT_BOUNDARY,
        label="packet_content_boundary",
    )
    packet_carrier = packet.get("carrier")
    expected_carrier = expectation.get("carrier")
    if not isinstance(packet_carrier, dict) or not isinstance(expected_carrier, dict):
        raise WrapperError("packet_or_expectation_carrier_not_object")
    comparisons = (
        ("carrier_id", expected_carrier.get("carrier_id")),
        ("carrier_kind", "current_run_export_archive"),
        ("path_or_uri", expected_carrier.get("staged_relative_path")),
        ("media_type", "application/zip"),
        ("sha256", carrier_digest),
        ("size_bytes", carrier_size),
        ("root_prefix", str(expected_carrier.get("root_prefix", "")).rstrip("/")),
        ("immutable", True),
        ("artifact_payload_mode", "external_carrier"),
        ("provider_binding", None),
    )
    for field, expected in comparisons:
        require_equal(packet_carrier.get(field), expected, label=f"packet_carrier_{field}")
    require_equal(
        packet.get("packet_identity", {}).get("subject_run_key"),
        expectation.get("subject", {}).get("subject_run_key"),
        label="packet_identity_subject_run_key",
    )
    require_equal(
        packet.get("packet_identity", {}).get("carrier_id"),
        expected_carrier.get("carrier_id"),
        label="packet_identity_carrier_id",
    )
    producer = packet.get("producer")
    if not isinstance(producer, dict):
        raise WrapperError("packet_producer_not_object")
    require_equal(producer.get("producer_source"), WRAPPER_SOURCE_PATH, label="packet_producer_source")
    require_equal(producer.get("production_mode"), "current_run_export", label="packet_production_mode")
    require_equal(producer.get("producer_run_key"), profile.expected_run_key, label="packet_producer_run_key")


def _reject_unsafe_output(
    output: Path | None,
    *,
    subject_root: Path,
    control_root: Path,
    staging_root: Path,
    protected_paths: Iterable[Path],
) -> Path | None:
    if output is None:
        return None
    candidate = _normalized_absolute_path(output)
    if not candidate.name or candidate.name in {".", ".."}:
        raise WrapperError(
            f"output_leaf_name_invalid: {candidate}",
            exit_kind="output_boundary_error",
        )
    if candidate.name.casefold() in PROTECTED_OUTPUT_NAMES_CASEFOLDED:
        raise WrapperError(
            f"output_name_protected: {candidate.name}",
            exit_kind="output_boundary_error",
        )
    for root in (subject_root, control_root, staging_root):
        if path_is_within(candidate, root):
            raise WrapperError(
                f"output_inside_protected_root: output={candidate} root={root}",
                exit_kind="output_boundary_error",
            )
    for protected in protected_paths:
        if same_target(candidate, protected):
            raise WrapperError(
                f"output_overwrites_protected_input: {protected}",
                exit_kind="output_boundary_error",
            )
    if candidate.exists():
        state = candidate.lstat()
        if stat.S_ISLNK(state.st_mode) or not stat.S_ISREG(state.st_mode):
            raise WrapperError(
                f"output_existing_target_not_regular_file: {candidate}",
                exit_kind="output_boundary_error",
            )
    return candidate


def _validate_expectation_exact(
    *,
    expectation_validator: Any,
    expectation: dict[str, Any],
    expectation_bytes: bytes,
    expectation_path: Path,
    expectation_schema: dict[str, Any],
    subject_schema: dict[str, Any],
    subject_root: Path,
    expectation_schema_path: Path,
    subject_schema_path: Path,
) -> None:
    valid, schema_errors = expectation_validator.validate_instance(
        expectation_schema,
        expectation,
        label="current_run_expectation",
    )
    if not valid:
        raise WrapperError(
            "expectation_schema_invalid: " + " | ".join(schema_errors),
            exit_kind="expectation_validation_error",
        )
    checks, semantic_errors, _derived = expectation_validator.semantic_checks(
        expectation,
        expectation_text=expectation_bytes.decode("utf-8", errors="strict"),
        expectation_path=expectation_path,
        repository_root=subject_root,
        expectation_schema=expectation_schema,
        subject_input_schema=subject_schema,
    )
    if not checks or not all(checks.values()) or semantic_errors:
        raise WrapperError(
            "expectation_semantic_validation_failed: "
            + json.dumps(
                {
                    "checks": dict(sorted(checks.items())),
                    "errors": sorted(set(semantic_errors)),
                },
                sort_keys=True,
                ensure_ascii=False,
            ),
            exit_kind="expectation_validation_error",
        )
    diagnostic, exit_code = expectation_validator.build_diagnostic(
        schema_path=expectation_schema_path,
        expectation_path=expectation_path,
        subject_input_schema_path=subject_schema_path,
        repository_root=subject_root,
    )
    if (
        exit_code != 0
        or diagnostic.get("ok") is not True
        or diagnostic.get("record_status") != "observed"
        or diagnostic.get("authority_effect") != "none"
    ):
        raise WrapperError(
            "expectation_validator_diagnostic_failed: "
            + json.dumps(diagnostic, sort_keys=True, ensure_ascii=False),
            exit_kind="expectation_validation_error",
        )


def _make_failure(error: WrapperError) -> dict[str, Any]:
    return {
        "authority_effect": "none",
        "document_type": DOCUMENT_TYPE,
        "errors": [str(error)],
        "exit_kind": error.exit_kind,
        "ok": False,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }


# ---------------------------------------------------------------------------
# CLI and complete protected execution
# ---------------------------------------------------------------------------


def _positive_cli_int(value: str) -> int:
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
            "Build one observed PULSEmech current-run subject-input packet from "
            "an exact current-run expectation and finalized carrier, while "
            "reusing the existing packet producer core."
        )
    )
    parser.add_argument("--expectation", required=True)
    parser.add_argument("--expectation-sha256", required=True)
    parser.add_argument("--staging-root", required=True)
    parser.add_argument("--subject-root", required=True)
    parser.add_argument("--subject-repository", required=True)
    parser.add_argument("--subject-revision", required=True)
    parser.add_argument("--control-plane-root", default=str(ROOT))
    parser.add_argument("--control-plane-repository", required=True)
    parser.add_argument("--control-plane-revision", required=True)
    parser.add_argument("--packet-created-utc", required=True)
    parser.add_argument("--producer-run-key", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument("--trusted-git")
    parser.add_argument(
        "--max-carrier-bytes",
        type=_positive_cli_int,
        default=DEFAULT_MAX_CARRIER_BYTES,
    )
    parser.add_argument(
        "--max-total-uncompressed-bytes",
        type=_positive_cli_int,
        default=DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
    )
    parser.add_argument("--output")
    return parser.parse_args()


def _build(args: argparse.Namespace) -> bytes:
    _require_supported_execution_platform()
    subject_root = _validated_directory_root(Path(args.subject_root), label="subject_root")
    control_root = _validated_directory_root(
        Path(args.control_plane_root),
        label="control_plane_root",
    )
    staging_root = _validated_directory_root(Path(args.staging_root), label="staging_root")
    for left_label, left, right_label, right in (
        ("subject", subject_root, "control_plane", control_root),
        ("subject", subject_root, "staging", staging_root),
        ("control_plane", control_root, "staging", staging_root),
    ):
        if paths_overlap(left, right):
            raise WrapperError(
                f"protected_roots_must_be_independent: "
                f"{left_label}={left} {right_label}={right}",
                exit_kind="input_boundary_error",
            )

    subject_repository = non_empty_text(args.subject_repository, label="subject_repository")
    subject_revision = canonical_sha40(str(args.subject_revision).lower(), label="subject_revision")
    control_repository = non_empty_text(args.control_plane_repository, label="control_plane_repository")
    control_revision = canonical_sha40(str(args.control_plane_revision).lower(), label="control_plane_revision")
    producer_run_key = non_empty_text(args.producer_run_key, label="producer_run_key")
    execution_identity = non_empty_text(
        args.ci_workflow_or_job_identity,
        label="ci_workflow_or_job_identity",
    )
    packet_created_utc = non_empty_text(args.packet_created_utc, label="packet_created_utc")
    parse_utc(packet_created_utc, label="packet_created_utc")
    expectation_sha = canonical_sha256(args.expectation_sha256, label="expectation_sha256")

    trusted_git = _select_trusted_git(args.trusted_git)
    _verify_git_repository(
        git_path=trusted_git,
        repository_root=subject_root,
        expected_revision=subject_revision,
        label="subject",
    )
    _verify_git_repository(
        git_path=trusted_git,
        repository_root=control_root,
        expected_revision=control_revision,
        label="control_plane",
    )
    subject_storage = _verify_git_local_only_repository_state(
        git_path=trusted_git,
        repository_root=subject_root,
        label="subject",
    )
    control_storage = _verify_git_local_only_repository_state(
        git_path=trusted_git,
        repository_root=control_root,
        label="control_plane",
    )
    _verify_independent_git_storage(
        subject_storage=subject_storage,
        control_storage=control_storage,
        subject_root=subject_root,
        control_root=control_root,
    )

    expectation_path = _normalized_absolute_path(Path(args.expectation))
    if any(
        path_is_within(expectation_path, root)
        for root in (subject_root, control_root, staging_root)
    ):
        raise WrapperError(
            f"expectation_inside_protected_root: {expectation_path}",
            exit_kind="input_boundary_error",
        )
    expectation_bytes = read_regular_file(
        expectation_path,
        label="expectation",
        max_bytes=MAX_EXPECTATION_BYTES,
    )
    expectation = parse_json_object(expectation_bytes, label="expectation")
    _verify_expectation_header(
        expectation=expectation,
        expectation_bytes=expectation_bytes,
        expectation_sha256=expectation_sha,
        subject_repository=subject_repository,
        subject_revision=subject_revision,
        control_repository=control_repository,
        control_revision=control_revision,
        producer_run_key=producer_run_key,
        packet_created_utc=packet_created_utc,
    )

    control_files = _verify_control_plane_components(
        expectation=expectation,
        git_path=trusted_git,
        control_root=control_root,
        control_revision=control_revision,
    )
    authority_files = _verify_subject_authority_sources(
        expectation=expectation,
        git_path=trusted_git,
        subject_root=subject_root,
        subject_revision=subject_revision,
    )

    import_roots = _prepare_protected_import_environment(
        subject_root=subject_root,
        control_root=control_root,
        staging_root=staging_root,
    )
    modules_before = set(sys.modules)
    carrier_module = _load_verified_module(
        verified=control_files["carrier_loader"],
        module_name="pulsemech_current_run_carrier_loader_v0_verified",
    )
    expectation_validator = _load_verified_module(
        verified=control_files["expectation_validator"],
        module_name="pulsemech_current_run_expectation_validator_v0_verified",
    )
    subject_validator = _load_verified_module(
        verified=control_files["subject_input_validator"],
        module_name="pulsemech_subject_input_validator_v0_verified",
    )
    producer_core = _load_verified_module(
        verified=control_files["subject_input_producer_core"],
        module_name="pulsemech_subject_input_producer_core_v0_verified",
    )
    _verify_loaded_module_origins(
        before_modules=modules_before,
        approved_roots=import_roots,
        approved_exact_paths=(
            control_files["carrier_loader"].path,
            control_files["expectation_validator"].path,
            control_files["subject_input_validator"].path,
            control_files["subject_input_producer_core"].path,
        ),
    )
    _verify_module_identities(
        carrier_module=carrier_module,
        expectation_validator=expectation_validator,
        subject_validator=subject_validator,
        producer_core=producer_core,
    )
    _bind_hardened_git_interfaces(
        producer_core=producer_core,
        subject_validator=subject_validator,
        trusted_git=trusted_git,
        subject_root=subject_root,
        subject_revision=subject_revision,
        control_root=control_root,
        control_revision=control_revision,
        control_files=control_files,
        authority_files=authority_files,
    )
    _bind_current_run_slug(
        producer_core=producer_core,
        carrier_module=carrier_module,
    )

    expectation_schema = parse_json_object(
        control_files["expectation_schema"].payload,
        label="expectation_schema",
    )
    subject_schema = parse_json_object(
        control_files["subject_input_schema"].payload,
        label="subject_input_schema",
    )
    _validate_expectation_exact(
        expectation_validator=expectation_validator,
        expectation=expectation,
        expectation_bytes=expectation_bytes,
        expectation_path=expectation_path,
        expectation_schema=expectation_schema,
        subject_schema=subject_schema,
        subject_root=subject_root,
        expectation_schema_path=control_files["expectation_schema"].path,
        subject_schema_path=control_files["subject_input_schema"].path,
    )

    carrier = expectation.get("carrier")
    if not isinstance(carrier, dict):
        raise WrapperError("expectation_carrier_not_object")
    require_equal(carrier.get("path_base"), "current_run_export_staging_root", label="carrier_path_base")
    require_equal(carrier.get("carrier_kind"), "current_run_export_archive", label="carrier_kind")
    require_equal(carrier.get("media_type"), "application/zip", label="carrier_media_type")
    require_equal(carrier.get("artifact_payload_mode"), "external_carrier", label="carrier_payload_mode")
    require_equal(carrier.get("immutable"), True, label="carrier_immutable")
    require_equal(carrier.get("finalized"), True, label="carrier_finalized")
    require_equal(carrier.get("provider_binding"), None, label="carrier_provider_binding")
    parse_utc(carrier.get("finalized_utc"), label="carrier_finalized_utc")
    staged_relative_path = canonical_member_path(
        carrier.get("staged_relative_path"),
        label="carrier_staged_relative_path",
    )
    carrier_path = staging_root / PurePosixPath(staged_relative_path)
    profile = _derive_producer_profile(
        expectation=expectation,
        producer_core=producer_core,
        carrier_path=carrier_path,
    )
    carrier_producer = carrier.get("producer")
    if not isinstance(carrier_producer, dict):
        raise WrapperError("carrier_producer_not_object")
    carrier_component = control_files["carrier_loader"]
    require_equal(carrier_producer.get("producer_source"), CARRIER_LOADER_SOURCE_PATH, label="carrier_producer_source")
    require_equal(carrier_producer.get("producer_source_revision"), control_revision, label="carrier_producer_revision")
    require_equal(carrier_producer.get("producer_source_sha256"), carrier_component.sha256, label="carrier_producer_sha256")
    require_equal(carrier_producer.get("producer_version"), "0.1.0", label="carrier_producer_version")
    require_equal(carrier_producer.get("producer_run_key"), producer_run_key, label="carrier_producer_run_key")
    require_equal(carrier_producer.get("production_mode"), "current_run_export_carrier_builder", label="carrier_producer_mode")

    protected_paths = [
        expectation_path,
        carrier_path,
        trusted_git,
        *(item.path for item in control_files.values()),
        *(item.path for item in authority_files.values()),
    ]
    output = _reject_unsafe_output(
        Path(args.output) if args.output else None,
        subject_root=subject_root,
        control_root=control_root,
        staging_root=staging_root,
        protected_paths=protected_paths,
    )

    opened_class = carrier_module.OpenedCarrier
    with opened_class.open(
        staging_root=staging_root,
        staged_relative_path=staged_relative_path,
        max_bytes=int(args.max_carrier_bytes),
    ) as opened:
        digest, size = opened.hash_once()
        require_equal(digest, profile.expected_carrier_sha256, label="carrier_sha256")
        require_equal(size, profile.expected_carrier_size, label="carrier_size")
        carrier_bytes = _carrier_snapshot_bytes(
            opened,
            max_bytes=int(args.max_carrier_bytes),
        )
        require_equal(sha256_bytes(carrier_bytes), digest, label="consumer_carrier_sha256")
        bundle = load_current_run_bundle(
            carrier_path=carrier_path,
            carrier_bytes=carrier_bytes,
            expectation=expectation,
            max_total_uncompressed_bytes=int(args.max_total_uncompressed_bytes),
        )
        artifacts, documents = producer_core.build_artifacts(
            carrier=staged_relative_path,
            bundle=bundle,
            validator=subject_validator,
            profile=profile,
        )
        bindings = producer_core.role_bindings(artifacts)
        inputs = producer_core.PacketInputs(
            profile=profile,
            carrier_path=carrier_path,
            carrier_location=staged_relative_path,
            carrier_bytes=carrier_bytes,
            bundle=bundle,
            artifacts=artifacts,
            role_bindings=bindings,
            documents=documents,
        )
        subject, sources = producer_core.build_subject_and_sources(
            inputs=inputs,
            repository_root=subject_root,
            validator=subject_validator,
        )
        producer = producer_core.producer_identity(
            repository_root=control_root,
            revision=control_revision,
            source_path=control_files["subject_input_producer_wrapper"].path,
            execution_identity=execution_identity,
            producer_run_key=producer_run_key,
            profile=profile,
        )
        packet = producer_core.build_packet(
            inputs=inputs,
            subject=subject,
            sources=sources,
            producer=producer,
            packet_created_utc=packet_created_utc,
        )
        rendered_text = producer_core.render_json(packet)
        if not isinstance(rendered_text, str):
            raise WrapperError("producer_core_render_json_did_not_return_text")
        rendered = rendered_text.encode("utf-8")
        _verify_packet_equivalence(
            packet=packet,
            expectation=expectation,
            carrier_digest=digest,
            carrier_size=size,
            profile=profile,
        )
        producer_core.validate_generated_packet(
            packet=packet,
            rendered=rendered_text,
            carrier_path=carrier_path,
            schema_path=control_files["subject_input_schema"].path,
            repository_root=subject_root,
            validator=subject_validator,
        )
        if rendered != render_json(packet):
            raise WrapperError("generated_packet_not_canonical_json")

        def verify_inputs() -> None:
            opened.verify_unchanged()
            if read_regular_file(
                expectation_path,
                label="expectation_recheck",
                max_bytes=MAX_EXPECTATION_BYTES,
            ) != expectation_bytes:
                raise WrapperError(
                    "expectation_changed_after_binding",
                    exit_kind="input_boundary_error",
                )
            _verify_git_repository(
                git_path=trusted_git,
                repository_root=subject_root,
                expected_revision=subject_revision,
                label="subject_recheck",
            )
            _verify_git_repository(
                git_path=trusted_git,
                repository_root=control_root,
                expected_revision=control_revision,
                label="control_plane_recheck",
            )
            _verify_git_local_only_repository_state(
                git_path=trusted_git,
                repository_root=subject_root,
                label="subject_recheck",
            )
            _verify_git_local_only_repository_state(
                git_path=trusted_git,
                repository_root=control_root,
                label="control_plane_recheck",
            )
            for item in control_files.values():
                current = _verified_repository_blob(
                    git_path=trusted_git,
                    repository_root=control_root,
                    revision=control_revision,
                    repository_path=item.repository_path,
                    label=f"control_recheck_{item.role}",
                    max_bytes=MAX_COMPONENT_BYTES,
                )
                require_equal(current.payload, item.payload, label=f"control_recheck_{item.role}")
            for source_id, item in authority_files.items():
                current = _verified_repository_blob(
                    git_path=trusted_git,
                    repository_root=subject_root,
                    revision=subject_revision,
                    repository_path=item.repository_path,
                    label=f"authority_recheck_{source_id}",
                    max_bytes=MAX_AUTHORITY_SOURCE_BYTES,
                )
                require_equal(current.payload, item.payload, label=f"authority_recheck_{source_id}")

        verify_inputs()
        if output is not None:
            carrier_module._atomic_write_external(
                output,
                rendered,
                verify_inputs=verify_inputs,
                finalize_inputs=opened.finalize,
            )
        else:
            verify_inputs()
            opened.finalize()
        return rendered


def main() -> int:
    try:
        rendered = _build(parse_args())
    except WrapperError as exc:
        sys.stderr.buffer.write(render_json(_make_failure(exc)))
        return exc.exit_code
    except Exception as exc:
        inherited_kind = getattr(exc, "exit_kind", None)
        inherited_code = getattr(exc, "exit_code", None)
        error = WrapperError(
            (
                str(exc)
                if isinstance(inherited_kind, str) and inherited_kind
                else f"unexpected_error: {type(exc).__name__}: {exc}"
            ),
            exit_kind=(
                inherited_kind
                if isinstance(inherited_kind, str) and inherited_kind
                else "unexpected_error"
            ),
            exit_code=(
                inherited_code
                if isinstance(inherited_code, int) and inherited_code != 0
                else 2
            ),
        )
        sys.stderr.buffer.write(render_json(_make_failure(error)))
        return error.exit_code
    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
