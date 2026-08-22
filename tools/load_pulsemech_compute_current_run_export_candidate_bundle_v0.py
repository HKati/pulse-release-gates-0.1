#!/usr/bin/env python3
from __future__ import annotations

import sys

_ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC = (
    '{"authority_effect":"none",'
    '"document_type":"pulsemech_compute_current_run_export_candidate_bundle_intake",'
    '"errors":["isolated_python_runtime_required: launch with python -I"],'
    '"exit_kind":"python_runtime_boundary_error",'
    '"ok":false,'
    '"tool":"load_pulsemech_compute_current_run_export_candidate_bundle_v0",'
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
import io
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable, Mapping, Sequence


TOOL_NAME = "load_pulsemech_compute_current_run_export_candidate_bundle_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = (
    "pulsemech_compute_current_run_export_candidate_bundle_intake_v0"
)
DOCUMENT_TYPE = (
    "pulsemech_compute_current_run_export_candidate_bundle_intake"
)

PRODUCER_SOURCE_PATH = (
    "tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
PRODUCER_ID = (
    "producer:pulsemech-current-run-export-candidate-bundle-intake-v0"
)
PRODUCER_NAME = (
    "PULSEmech current-run export candidate bundle intake"
)
PRODUCTION_MODE = "current_run_export_candidate_bundle_intake"

SUPPORTED_EXECUTION_PLATFORM = "linux"
SUPPORTED_OS_NAME = "posix"
EXECUTION_PROFILE = "protected_linux_hpc_control_plane"

PROVIDER_NAME = "github_actions"
PROVIDER_WORKFLOW_NAME = "PULSEmech compute current-run export candidate"
PROVIDER_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)
SOURCE_WORKFLOW_NAME = "PULSE CI"
SOURCE_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
SOURCE_REF = "refs/heads/main"

CANDIDATE_MANIFEST_NAME = "candidate-output-manifest.json"
CARRIER_METADATA_NAME = "carrier.json"
EXPECTATION_NAME = "expectation.json"
PACKET_NAME = "subject-input-packet.json"
SOURCE_RESOLUTION_NAME = "source-run-resolution.json"
SOURCE_SELECTION_NAME = "source-artifact-selection.json"
INTAKE_REPORT_NAME = "candidate-bundle-intake-report.json"

FIXED_CANDIDATE_FILES = frozenset(
    {
        CARRIER_METADATA_NAME,
        EXPECTATION_NAME,
        PACKET_NAME,
        SOURCE_RESOLUTION_NAME,
        SOURCE_SELECTION_NAME,
    }
)

EXPECTED_MANIFEST_AUTHORITY = {
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

EXPECTED_SOURCE_RESOLUTION_AUTHORITY = {
    "activates_compute_gate": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "creates_gate_result": False,
    "creates_release_decision": False,
    "source_resolution_only": True,
}

EXPECTED_SELECTION_AUTHORITY = {
    "activates_compute_gate": False,
    "changes_release_authority": False,
    "downloads_source_artifacts_only": True,
}

EXPECTED_EXPECTATION_AUTHORITY = {
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

EXPECTED_EXPECTATION_CONTENT = {
    "consumer_must_verify_carrier_bytes": True,
    "contains_artifact_payloads": False,
    "contains_resource_measurement": False,
    "contains_runtime_observation": False,
    "contains_secret_material": False,
    "expectation_payload_mode": "metadata_only",
}

EXPECTED_PACKET_AUTHORITY = {
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

EXPECTED_PACKET_ANALYSIS = {
    "current_repository_state_substitution_allowed": False,
    "observer_in_subject_totals": False,
    "packet_is_compute_report": False,
    "packet_is_runtime_observation": False,
    "runtime_observation_included": False,
    "runtime_observation_required_for_runtime_classification": True,
    "target_analysis_level": "artifact_observed",
}

EXPECTED_PACKET_CONTENT = {
    "artifact_bytes_embedded": False,
    "carrier_required_for_verification": True,
    "packet_payload_mode": "metadata_only",
    "raw_model_inputs_included": False,
    "raw_model_outputs_included": False,
    "raw_secrets_included": False,
}

EXPECTED_PRESERVATION_AUTHORITY = {
    "alters_preserved_artifacts": False,
    "creates_release_authority": False,
    "preservation_copy_only": True,
    "replaces_original_github_attestations": False,
    "replaces_primary_ci_decision": False,
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

CLOSED_CONTENT_BOUNDARY = {
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

SOURCE_ARTIFACT_ROLES = {
    "complete": "complete_release_grade_reference_package",
    "completeness": "structural_package_completeness_report",
    "verification": "independent_package_verification_report",
}

SOURCE_ARTIFACT_NAME_PREFIXES = {
    "complete": "complete-release-grade-reference-package",
    "completeness": "release-grade-package-completeness",
    "verification": "release-grade-reference-package-verification",
}

CANDIDATE_FILE_ROLES = {
    CANDIDATE_MANIFEST_NAME: "candidate_output_manifest",
    CARRIER_METADATA_NAME: "carrier_metadata",
    EXPECTATION_NAME: "observed_current_run_expectation",
    PACKET_NAME: "observed_subject_input_packet",
    SOURCE_RESOLUTION_NAME: "source_run_resolution",
    SOURCE_SELECTION_NAME: "source_artifact_selection",
}

GENERIC_EXPECTATION_SOURCE_IDS = {
    "workflow": "source:workflow",
    "policy": "source:policy",
    "gate_registry": "source:gate-registry",
}
CANONICAL_PACKET_SOURCE_IDS = {
    "workflow": "source:workflow:pulse-ci",
    "policy": "source:policy:pulse-gate-policy-v0",
    "gate_registry": "source:registry:gate-registry-v0",
}
CANONICAL_ADDITIONAL_SOURCE_IDS = {
    ("external_signer_policy", "policy/external_signers_v1.yml"): (
        "source:policy:external-signers-v1"
    ),
    ("threshold_policy", "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"): (
        "source:policy:external-thresholds"
    ),
}

CORE_SINGLETON_ROLE_BINDINGS: dict[str, str] = {
    "preservation_manifest": "preservation_manifest",
    "preservation_readme": "preservation_readme",
    "preservation_checksums": "preservation_checksums",
    "complete_package": "complete_package",
    "package_inventory": "package_inventory",
    "package_completeness_report": "package_completeness_report",
    "independent_verification_report": "independent_verification_report",
    "run_metadata": "run_metadata",
    "final_status": "final_status",
    "status_baseline": "status_baseline",
    "release_decision": "release_decision",
    "release_authority": "release_authority",
    "artifact_binding": "artifact_binding",
    "evidence_manifest": "evidence_manifest",
    "recorded_verifier_report": "recorded_verifier_report",
    "required_gate_evidence": "required_gate_evidence",
    "candidate_index": "candidate_index",
}
LIST_ROLE_BINDINGS: dict[str, set[str]] = {
    "candidate_records": {"candidate_record"},
    "external_evidence_records": {
        "external_evidence",
        "external_evaluator_manifest",
        "external_raw_evidence",
        "external_summary",
    },
    "attestation_records": {
        "attestation_bundle",
        "attestation_envelope",
        "attestation_verifier_report",
    },
    "reader_surfaces": {
        "quality_ledger",
        "report_card",
        "reader_surface",
    },
}
PACKET_ARTIFACT_KEYS = frozenset(
    {
        "artifact_id",
        "role",
        "content_kind",
        "media_type",
        "container_artifact_id",
        "member_path",
        "display_path_or_uri",
        "sha256",
        "size_bytes",
        "required_for_analysis",
        "digest_verified",
        "size_verified",
        "container_path_verified",
        "provider_binding",
    }
)
PACKET_COVERAGE_KEYS = frozenset(
    {
        "coverage_status",
        "source_bindings_complete",
        "carrier_binding_complete",
        "artifact_graph_complete",
        "role_bindings_complete",
        "artifacts_total",
        "provider_artifacts_total",
        "provider_artifacts_bound",
        "role_bindings_total",
        "role_bindings_resolved",
        "missing_roles",
        "unresolved_artifact_ids",
    }
)
PACKET_RETAINED_ROLES = frozenset(
    {
        "preservation_manifest",
        "package_inventory",
        "package_completeness_report",
        "independent_verification_report",
        "run_metadata",
        "final_status",
        "release_decision",
    }
)

NON_ANALYSIS_ROLES = frozenset(
    {"quality_ledger", "report_card", "reader_surface", "other"}
)

ROLE_BY_PACKAGE_MEMBER: Mapping[str, str] = {
    "artifacts/artifact_provenance_binding_v0.json": "artifact_binding",
    "artifacts/external/llamaguard_attestation_verifier_v1.json": (
        "attestation_verifier_report"
    ),
    "artifacts/external/llamaguard_evaluator_manifest_v0.json": (
        "external_evaluator_manifest"
    ),
    "artifacts/external/llamaguard_raw.jsonl": "external_raw_evidence",
    "artifacts/external/llamaguard_summary.bundle.json": "attestation_bundle",
    "artifacts/external/llamaguard_summary.envelope.json": "attestation_envelope",
    "artifacts/external/llamaguard_summary.json": "external_summary",
    "artifacts/recorded_release_candidate_index_v0.json": "candidate_index",
    "artifacts/recorded_release_evidence_verifier_v0.json": (
        "recorded_verifier_report"
    ),
    "artifacts/release_authority_v0.json": "release_authority",
    "artifacts/release_decision_v0.json": "release_decision",
    "artifacts/release_evidence_input_manifest_v0.json": "evidence_manifest",
    "artifacts/report_card.html": "quality_ledger",
    "artifacts/required_gate_evidence_v0.json": "required_gate_evidence",
    "artifacts/status.json": "final_status",
    "artifacts/status_baseline.json": "status_baseline",
    "package_digest_inventory_v0.json": "package_inventory",
    "release-authority-audit-bundle/report_card.html": "reader_surface",
    "run_metadata_v0.json": "run_metadata",
}

ROOT = Path(__file__).resolve().parents[1]

HASH_CHUNK_BYTES = 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_PRODUCER_SOURCE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_ENVELOPE_BYTES = 768 * 1024 * 1024
DEFAULT_MAX_MEMBER_BYTES = 640 * 1024 * 1024
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 768 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_OUTER_MEMBERS = 16
MAX_INNER_MEMBERS = 4096
MAX_INNER_MEMBER_BYTES = 256 * 1024 * 1024
MAX_INNER_TOTAL_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024
MAX_SHA256SUMS_BYTES = 2 * 1024 * 1024
MAX_PRESERVATION_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_PRESERVATION_README_BYTES = 2 * 1024 * 1024

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
        "pulsemech_compute_current_run_export_candidate_bundle_v0.json",
        "pulsemech_compute_current_run_export_expectation_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    }
)
PROTECTED_OUTPUT_NAMES_CASEFOLDED = frozenset(
    name.casefold() for name in PROTECTED_OUTPUT_NAMES
)


class BundleError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_kind: str = "candidate_bundle_intake_error",
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.exit_kind = exit_kind
        self.exit_code = exit_code


class StrictJsonError(ValueError):
    pass


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    mode: int
    links: int
    uid: int
    gid: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True)
class DirectoryIdentity:
    path: Path
    device: int
    inode: int
    mode: int
    uid: int
    gid: int


@dataclass(frozen=True)
class MaterializedFile:
    path: str
    role: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class SourceSubject:
    repository: str
    source_run_id: int
    source_run_number: int
    source_run_attempt: int
    source_run_key: str
    subject_revision: str
    source_updated_utc: str
    release_candidate_id: str


@dataclass(frozen=True)
class ProviderArtifact:
    repository: str
    workflow_name: str
    workflow_path: str
    workflow_run_id: int
    workflow_run_number: int
    workflow_run_attempt: int
    workflow_run_key: str
    workflow_revision: str
    workflow_updated_utc: str
    artifact_id: int
    artifact_name: str
    artifact_created_utc: str
    artifact_expires_utc: str
    artifact_sha256: str
    artifact_size_bytes: int
    source_run_id_from_name: int
    source_run_attempt_from_name: int


@dataclass(frozen=True)
class SourceBinding:
    source_sha256: str
    source_bytes: bytes
    source_path: Path


@dataclass(frozen=True)
class PacketVerification:
    artifact_index: Mapping[str, Mapping[str, Any]]
    retained_artifact_bytes: Mapping[str, bytes]
    archive_members: Mapping[str | None, tuple[str, ...]]
    role_bindings: Mapping[str, Any]
    artifacts_total: int
    provider_artifacts_total: int
    provider_artifacts_bound: int
    role_bindings_total: int
    role_bindings_resolved: int
    missing_roles: tuple[str, ...]
    unresolved_artifact_ids: tuple[str, ...]


class RetainedByteBudget:
    def __init__(self, maximum: int) -> None:
        if maximum <= 0:
            raise BundleError(
                f"retained_byte_budget_invalid: {maximum}",
                exit_kind="resource_boundary_error",
            )
        self.maximum = maximum
        self.used = 0

    def reserve(self, amount: int, *, label: str) -> None:
        if amount < 0 or amount > self.maximum - self.used:
            raise BundleError(
                f"{label}_retained_byte_budget_exceeded: "
                f"used={self.used} requested={amount} maximum={self.maximum}",
                exit_kind="resource_boundary_error",
            )
        self.used += amount


class OpenedInput:
    def __init__(
        self,
        *,
        path: Path | None,
        descriptor: int,
        identity: FileIdentity,
        directory_chain: tuple[DirectoryIdentity, ...],
        parent_descriptor: int | None = None,
        parent_identity: tuple[int, int] | None = None,
        leaf_name: str | None = None,
    ) -> None:
        self.path = path
        self.descriptor = descriptor
        self.identity = identity
        self.directory_chain = directory_chain
        self.parent_descriptor = parent_descriptor
        self.parent_identity = parent_identity
        self.leaf_name = leaf_name
        self._closed = False

    @classmethod
    def open(
        cls,
        path: Path,
        *,
        label: str,
        max_bytes: int,
        require_read_only: bool,
        require_single_link: bool,
    ) -> "OpenedInput":
        candidate = _normalized_absolute_path(path)
        descriptor, chain = _open_regular_nofollow(candidate, label=label)
        try:
            identity = cls._validated_identity(
                descriptor,
                label=label,
                max_bytes=max_bytes,
                require_read_only=require_read_only,
                require_single_link=require_single_link,
            )
            return cls(
                path=candidate,
                descriptor=descriptor,
                identity=identity,
                directory_chain=chain,
            )
        except Exception:
            os.close(descriptor)
            raise

    @classmethod
    def open_at(
        cls,
        directory_descriptor: int,
        name: str,
        *,
        label: str,
        max_bytes: int,
        require_read_only: bool,
        require_single_link: bool,
    ) -> "OpenedInput":
        leaf = _canonical_flat_member(name, label=f"{label}_leaf")
        parent_descriptor = os.dup(directory_descriptor)
        flags = os.O_RDONLY | os.O_NOFOLLOW
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        try:
            parent_meta = os.fstat(parent_descriptor)
            if not stat.S_ISDIR(parent_meta.st_mode):
                raise BundleError(
                    f"{label}_parent_not_directory",
                    exit_kind="input_boundary_error",
                )
            descriptor = os.open(
                leaf,
                flags,
                dir_fd=parent_descriptor,
            )
            try:
                identity = cls._validated_identity(
                    descriptor,
                    label=label,
                    max_bytes=max_bytes,
                    require_read_only=require_read_only,
                    require_single_link=require_single_link,
                )
                observed = os.stat(
                    leaf,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISLNK(observed.st_mode) or _file_identity(observed) != identity:
                    raise BundleError(
                        f"{label}_relative_path_identity_mismatch: {leaf}",
                        exit_kind="input_boundary_error",
                    )
                return cls(
                    path=None,
                    descriptor=descriptor,
                    identity=identity,
                    directory_chain=(),
                    parent_descriptor=parent_descriptor,
                    parent_identity=(int(parent_meta.st_dev), int(parent_meta.st_ino)),
                    leaf_name=leaf,
                )
            except Exception:
                os.close(descriptor)
                raise
        except Exception:
            os.close(parent_descriptor)
            raise

    @staticmethod
    def _validated_identity(
        descriptor: int,
        *,
        label: str,
        max_bytes: int,
        require_read_only: bool,
        require_single_link: bool,
    ) -> FileIdentity:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise BundleError(
                f"{label}_not_regular_file",
                exit_kind="input_boundary_error",
            )
        if metadata.st_size <= 0:
            raise BundleError(
                f"{label}_empty",
                exit_kind="input_boundary_error",
            )
        if metadata.st_size > max_bytes:
            raise BundleError(
                f"{label}_too_large: size={metadata.st_size} maximum={max_bytes}",
                exit_kind="resource_boundary_error",
            )
        if require_read_only and metadata.st_mode & (
            stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        ):
            raise BundleError(
                f"{label}_not_finalized_read_only: mode={oct(metadata.st_mode)}",
                exit_kind="input_boundary_error",
            )
        if require_single_link and metadata.st_nlink != 1:
            raise BundleError(
                f"{label}_link_count_invalid: {metadata.st_nlink}",
                exit_kind="input_boundary_error",
            )
        return _file_identity(metadata)

    def duplicate_binary_reader(self) -> BinaryIO:
        if self._closed:
            raise BundleError("input_descriptor_already_closed")
        return os.fdopen(os.dup(self.descriptor), "rb", closefd=True)

    def read_bytes(self, *, label: str, max_bytes: int) -> bytes:
        if self.identity.size > max_bytes:
            raise BundleError(
                f"{label}_too_large: size={self.identity.size} maximum={max_bytes}",
                exit_kind="resource_boundary_error",
            )
        chunks: list[bytes] = []
        offset = 0
        while offset < self.identity.size:
            chunk = os.pread(
                self.descriptor,
                min(HASH_CHUNK_BYTES, self.identity.size - offset),
                offset,
            )
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
        payload = b"".join(chunks)
        if len(payload) != self.identity.size:
            raise BundleError(
                f"{label}_short_read: expected={self.identity.size} actual={len(payload)}",
                exit_kind="input_boundary_error",
            )
        self.verify_unchanged(label=label)
        return payload

    def hash_once(self, *, label: str) -> tuple[str, int]:
        digest = hashlib.sha256()
        offset = 0
        while offset < self.identity.size:
            chunk = os.pread(
                self.descriptor,
                min(HASH_CHUNK_BYTES, self.identity.size - offset),
                offset,
            )
            if not chunk:
                break
            digest.update(chunk)
            offset += len(chunk)
        if offset != self.identity.size:
            raise BundleError(
                f"{label}_short_hash_read: expected={self.identity.size} actual={offset}",
                exit_kind="input_boundary_error",
            )
        self.verify_unchanged(label=label)
        return digest.hexdigest(), offset

    def verify_unchanged(self, *, label: str) -> None:
        if self._closed:
            raise BundleError(f"{label}_descriptor_closed")
        current = _file_identity(os.fstat(self.descriptor))
        if current != self.identity:
            raise BundleError(
                f"{label}_descriptor_changed",
                exit_kind="input_boundary_error",
            )
        if self.parent_descriptor is not None:
            if self.parent_identity is None or self.leaf_name is None:
                raise BundleError(
                    f"{label}_relative_binding_incomplete",
                    exit_kind="input_boundary_error",
                )
            parent = os.fstat(self.parent_descriptor)
            if (
                not stat.S_ISDIR(parent.st_mode)
                or (int(parent.st_dev), int(parent.st_ino)) != self.parent_identity
            ):
                raise BundleError(
                    f"{label}_parent_descriptor_changed",
                    exit_kind="input_boundary_error",
                )
            try:
                leaf = os.stat(
                    self.leaf_name,
                    dir_fd=self.parent_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise BundleError(
                    f"{label}_relative_path_unavailable: {self.leaf_name}: {exc}",
                    exit_kind="input_boundary_error",
                ) from exc
            if stat.S_ISLNK(leaf.st_mode) or _file_identity(leaf) != self.identity:
                raise BundleError(
                    f"{label}_relative_path_identity_changed: {self.leaf_name}",
                    exit_kind="input_boundary_error",
                )
            return

        _verify_directory_chain(self.directory_chain, label=label)
        if self.path is None:
            raise BundleError(
                f"{label}_path_binding_missing",
                exit_kind="input_boundary_error",
            )
        try:
            leaf = self.path.lstat()
        except OSError as exc:
            raise BundleError(
                f"{label}_path_unavailable_after_open: {self.path}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        if stat.S_ISLNK(leaf.st_mode) or _file_identity(leaf) != self.identity:
            raise BundleError(
                f"{label}_path_identity_changed: {self.path}",
                exit_kind="input_boundary_error",
            )

    def close(self) -> None:
        if not self._closed:
            os.close(self.descriptor)
            if self.parent_descriptor is not None:
                os.close(self.parent_descriptor)
            self._closed = True

    def __enter__(self) -> "OpenedInput":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def parse_json_bytes(
    payload: bytes,
    *,
    label: str,
    canonical_required: bool,
) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise BundleError(
            f"{label}_utf8_bom_not_permitted",
            exit_kind="strict_json_error",
        )
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BundleError(
            f"{label}_invalid_utf8: {exc}",
            exit_kind="strict_json_error",
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise BundleError(
            f"{label}_invalid_json: {exc}",
            exit_kind="strict_json_error",
        ) from exc
    if not isinstance(value, dict):
        raise BundleError(
            f"{label}_not_object",
            exit_kind="strict_json_error",
        )
    if canonical_required and payload != render_json(value):
        raise BundleError(
            f"{label}_not_canonical_json",
            exit_kind="strict_json_error",
        )
    return value


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _file_identity(value: os.stat_result) -> FileIdentity:
    return FileIdentity(
        device=int(value.st_dev),
        inode=int(value.st_ino),
        mode=int(value.st_mode),
        links=int(value.st_nlink),
        uid=int(value.st_uid),
        gid=int(value.st_gid),
        size=int(value.st_size),
        mtime_ns=int(value.st_mtime_ns),
        ctime_ns=int(value.st_ctime_ns),
    )


def _directory_identity(path: Path, value: os.stat_result) -> DirectoryIdentity:
    return DirectoryIdentity(
        path=path,
        device=int(value.st_dev),
        inode=int(value.st_ino),
        mode=int(value.st_mode),
        uid=int(value.st_uid),
        gid=int(value.st_gid),
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
        raise BundleError(
            "unsupported_execution_platform: "
            f"profile={EXECUTION_PROFILE!r} "
            f"required_sys_platform={SUPPORTED_EXECUTION_PLATFORM!r} "
            f"required_os_name={SUPPORTED_OS_NAME!r} "
            f"observed_sys_platform={sys.platform!r} "
            f"observed_os_name={os.name!r}",
            exit_kind="platform_boundary_error",
        )
    required = (
        os.open in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.mkdir in os.supports_dir_fd,
        os.rename in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.rmdir in os.supports_dir_fd,
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        hasattr(os, "pread"),
    )
    if not all(required):
        raise BundleError(
            "protected_descriptor_profile_unavailable",
            exit_kind="platform_boundary_error",
        )


def _open_regular_nofollow(
    path: Path,
    *,
    label: str,
) -> tuple[int, tuple[DirectoryIdentity, ...]]:
    candidate = _normalized_absolute_path(path)
    parts = candidate.parts
    if not candidate.is_absolute() or len(parts) < 2:
        raise BundleError(
            f"{label}_path_not_absolute_file: {candidate}",
            exit_kind="input_boundary_error",
        )

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_flags |= int(getattr(os, "O_CLOEXEC", 0))
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    file_flags |= int(getattr(os, "O_CLOEXEC", 0))

    current_fd: int | None = None
    chain: list[DirectoryIdentity] = []
    try:
        current_fd = os.open(parts[0], directory_flags)
        root_path = Path(parts[0])
        root_meta = os.fstat(current_fd)
        chain.append(_directory_identity(root_path, root_meta))
        current_path = root_path
        for part in parts[1:-1]:
            if part in {"", ".", ".."}:
                raise BundleError(
                    f"{label}_unsafe_path_component: {part!r}",
                    exit_kind="input_boundary_error",
                )
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
            current_path = current_path / part
            chain.append(_directory_identity(current_path, os.fstat(current_fd)))
        leaf = parts[-1]
        if leaf in {"", ".", ".."}:
            raise BundleError(
                f"{label}_unsafe_leaf: {leaf!r}",
                exit_kind="input_boundary_error",
            )
        descriptor = os.open(leaf, file_flags, dir_fd=current_fd)
        return descriptor, tuple(chain)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise BundleError(
                f"{label}_symlink_or_non_directory_component_rejected: "
                f"{candidate}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        if exc.errno == errno.ENOENT:
            raise BundleError(
                f"{label}_missing: {candidate}",
                exit_kind="input_boundary_error",
            ) from exc
        raise BundleError(
            f"{label}_open_failed: {candidate}: {exc}",
            exit_kind="input_boundary_error",
        ) from exc
    finally:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass



def _open_directory_nofollow(
    path: Path,
    *,
    label: str,
) -> tuple[int, tuple[DirectoryIdentity, ...]]:
    candidate = _normalized_absolute_path(path)
    parts = candidate.parts
    if not candidate.is_absolute() or not parts:
        raise BundleError(
            f"{label}_path_not_absolute_directory: {candidate}",
            exit_kind="output_boundary_error",
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    current_fd: int | None = None
    chain: list[DirectoryIdentity] = []
    try:
        current_fd = os.open(parts[0], flags)
        current_path = Path(parts[0])
        chain.append(_directory_identity(current_path, os.fstat(current_fd)))
        for part in parts[1:]:
            if part in {"", ".", ".."}:
                raise BundleError(
                    f"{label}_unsafe_path_component: {part!r}",
                    exit_kind="output_boundary_error",
                )
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
            current_path = current_path / part
            chain.append(_directory_identity(current_path, os.fstat(current_fd)))
        result = current_fd
        current_fd = None
        return result, tuple(chain)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise BundleError(
                f"{label}_symlink_or_non_directory_component_rejected: "
                f"{candidate}: {exc}",
                exit_kind="output_boundary_error",
            ) from exc
        raise BundleError(
            f"{label}_open_failed: {candidate}: {exc}",
            exit_kind="output_boundary_error",
        ) from exc
    finally:
        if current_fd is not None:
            os.close(current_fd)


class StagedOutputDirectory:
    def __init__(
        self,
        *,
        final_path: Path,
        parent_descriptor: int,
        parent_chain: tuple[DirectoryIdentity, ...],
        temporary_name: str,
        directory_descriptor: int,
        directory_identity: tuple[int, int],
    ) -> None:
        self.final_path = final_path
        self.parent_descriptor = parent_descriptor
        self.parent_chain = parent_chain
        self.temporary_name = temporary_name
        self.final_name = final_path.name
        self.directory_descriptor = directory_descriptor
        self.directory_identity = directory_identity
        self.published = False
        self.owned_files: dict[str, tuple[int, int]] = {}
        self.closed = False

    @classmethod
    def create(cls, final_path: Path) -> "StagedOutputDirectory":
        final = _normalized_absolute_path(final_path)
        parent_fd, chain = _open_directory_nofollow(
            final.parent,
            label="output_parent",
        )
        try:
            parent_meta = os.fstat(parent_fd)
            if (
                parent_meta.st_uid != os.geteuid()
                or parent_meta.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                raise BundleError(
                    "output_parent_not_exclusively_owned: "
                    f"uid={parent_meta.st_uid} mode={oct(parent_meta.st_mode)}",
                    exit_kind="output_boundary_error",
                )
            cls._require_name_absent(parent_fd, final.name, label="output_final")
            for _attempt in range(128):
                temporary_name = (
                    f".{final.name}.{secrets.token_hex(16)}.tmp"
                )
                try:
                    os.mkdir(
                        temporary_name,
                        mode=0o700,
                        dir_fd=parent_fd,
                    )
                except FileExistsError:
                    continue
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                flags |= int(getattr(os, "O_CLOEXEC", 0))
                try:
                    directory_fd = os.open(
                        temporary_name,
                        flags,
                        dir_fd=parent_fd,
                    )
                except Exception:
                    try:
                        os.rmdir(temporary_name, dir_fd=parent_fd)
                    except OSError:
                        pass
                    raise
                meta = os.fstat(directory_fd)
                if not stat.S_ISDIR(meta.st_mode):
                    os.close(directory_fd)
                    os.rmdir(temporary_name, dir_fd=parent_fd)
                    raise BundleError(
                        "temporary_output_not_directory",
                        exit_kind="output_boundary_error",
                    )
                result = cls(
                    final_path=final,
                    parent_descriptor=parent_fd,
                    parent_chain=chain,
                    temporary_name=temporary_name,
                    directory_descriptor=directory_fd,
                    directory_identity=(int(meta.st_dev), int(meta.st_ino)),
                )
                result.verify_name_binding(temporary=True)
                return result
            raise BundleError(
                "temporary_output_name_exhausted",
                exit_kind="output_boundary_error",
            )
        except Exception:
            os.close(parent_fd)
            raise

    @staticmethod
    def _require_name_absent(parent_fd: int, name: str, *, label: str) -> None:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise BundleError(
                f"{label}_state_unavailable: {name}: {exc}",
                exit_kind="output_boundary_error",
            ) from exc
        raise BundleError(
            f"{label}_already_exists: {name}",
            exit_kind="output_boundary_error",
        )

    def verify_parent(self) -> None:
        if self.closed:
            raise BundleError("staged_output_already_closed")
        _verify_directory_chain(self.parent_chain, label="output_parent")
        meta = os.fstat(self.parent_descriptor)
        expected = self.parent_chain[-1]
        if (
            not stat.S_ISDIR(meta.st_mode)
            or int(meta.st_dev) != expected.device
            or int(meta.st_ino) != expected.inode
        ):
            raise BundleError(
                "output_parent_descriptor_identity_changed",
                exit_kind="output_boundary_error",
            )

    def verify_name_binding(self, *, temporary: bool) -> None:
        self.verify_parent()
        name = self.temporary_name if temporary else self.final_name
        try:
            meta = os.stat(
                name,
                dir_fd=self.parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise BundleError(
                f"output_directory_name_unavailable: {name}: {exc}",
                exit_kind="output_boundary_error",
            ) from exc
        if (
            stat.S_ISLNK(meta.st_mode)
            or not stat.S_ISDIR(meta.st_mode)
            or (int(meta.st_dev), int(meta.st_ino)) != self.directory_identity
        ):
            raise BundleError(
                f"output_directory_name_identity_changed: {name}",
                exit_kind="output_boundary_error",
            )
        current = os.fstat(self.directory_descriptor)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (int(current.st_dev), int(current.st_ino)) != self.directory_identity
        ):
            raise BundleError(
                "output_directory_descriptor_identity_changed",
                exit_kind="output_boundary_error",
            )

    def create_file(self, name: str) -> int:
        leaf = _canonical_flat_member(name, label="output_member")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        try:
            descriptor = os.open(
                leaf,
                flags,
                0o600,
                dir_fd=self.directory_descriptor,
            )
        except OSError as exc:
            raise BundleError(
                f"output_file_create_failed: name={leaf!r}: {exc}",
                exit_kind="output_boundary_error",
            ) from exc
        meta = os.fstat(descriptor)
        self.owned_files[leaf] = (int(meta.st_dev), int(meta.st_ino))
        return descriptor

    def list_names(self) -> set[str]:
        return set(os.listdir(self.directory_descriptor))

    def publish(self) -> None:
        if self.published:
            raise BundleError(
                "output_directory_already_published",
                exit_kind="output_boundary_error",
            )
        os.fsync(self.directory_descriptor)
        os.fchmod(self.directory_descriptor, 0o555)
        self.verify_name_binding(temporary=True)
        self._require_name_absent(
            self.parent_descriptor,
            self.final_name,
            label="output_final",
        )
        os.rename(
            self.temporary_name,
            self.final_name,
            src_dir_fd=self.parent_descriptor,
            dst_dir_fd=self.parent_descriptor,
        )
        self.published = True
        os.fsync(self.parent_descriptor)
        self.verify_name_binding(temporary=False)

    def cleanup(self) -> None:
        if self.closed:
            return
        try:
            try:
                os.fchmod(self.directory_descriptor, 0o700)
            except OSError:
                pass
            for name, identity in sorted(self.owned_files.items()):
                try:
                    meta = os.stat(
                        name,
                        dir_fd=self.directory_descriptor,
                        follow_symlinks=False,
                    )
                except OSError:
                    continue
                if (
                    stat.S_ISREG(meta.st_mode)
                    and not stat.S_ISLNK(meta.st_mode)
                    and (int(meta.st_dev), int(meta.st_ino)) == identity
                ):
                    try:
                        os.unlink(name, dir_fd=self.directory_descriptor)
                    except OSError:
                        pass
            target_name = self.final_name if self.published else self.temporary_name
            try:
                meta = os.stat(
                    target_name,
                    dir_fd=self.parent_descriptor,
                    follow_symlinks=False,
                )
            except OSError:
                meta = None
            if (
                meta is not None
                and stat.S_ISDIR(meta.st_mode)
                and not stat.S_ISLNK(meta.st_mode)
                and (int(meta.st_dev), int(meta.st_ino)) == self.directory_identity
            ):
                try:
                    os.rmdir(target_name, dir_fd=self.parent_descriptor)
                    os.fsync(self.parent_descriptor)
                except OSError:
                    pass
        finally:
            self.close()

    def close(self) -> None:
        if not self.closed:
            os.close(self.directory_descriptor)
            os.close(self.parent_descriptor)
            self.closed = True


def _verify_directory_chain(
    chain: Sequence[DirectoryIdentity],
    *,
    label: str,
) -> None:
    for expected in chain:
        try:
            observed = expected.path.lstat()
        except OSError as exc:
            raise BundleError(
                f"{label}_directory_chain_unavailable: {expected.path}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
            raise BundleError(
                f"{label}_directory_chain_type_changed: {expected.path}",
                exit_kind="input_boundary_error",
            )
        current = _directory_identity(expected.path, observed)
        if current != expected:
            raise BundleError(
                f"{label}_directory_chain_identity_changed: {expected.path}",
                exit_kind="input_boundary_error",
            )


def _validated_directory_root(path: Path, *, label: str) -> Path:
    candidate = _normalized_absolute_path(path)
    cursor = candidate
    while True:
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise BundleError(
                f"{label}_component_unavailable: {cursor}: {exc}",
                exit_kind="input_boundary_error",
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise BundleError(
                f"{label}_symlink_component_rejected: {cursor}",
                exit_kind="input_boundary_error",
            )
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    if not candidate.is_dir():
        raise BundleError(
            f"{label}_not_directory: {candidate}",
            exit_kind="input_boundary_error",
        )
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise BundleError(
            f"{label}_unresolvable: {candidate}: {exc}",
            exit_kind="input_boundary_error",
        ) from exc


def _non_empty_text(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise BundleError(
            f"{label}_invalid_text: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _positive_int(value: Any, *, label: str) -> int:
    if type(value) is int:
        parsed = value
    elif isinstance(value, str):
        if re.fullmatch(r"[1-9][0-9]*", value) is None:
            raise BundleError(
                f"{label}_not_canonical_positive_integer: {value!r}",
                exit_kind="input_boundary_error",
            )
        parsed = int(value, 10)
    else:
        raise BundleError(
            f"{label}_not_positive_integer: {value!r}",
            exit_kind="input_boundary_error",
        )
    if parsed <= 0:
        raise BundleError(
            f"{label}_not_positive_integer: {value!r}",
            exit_kind="input_boundary_error",
        )
    return parsed


def _arg_positive_int(value: str) -> int:
    try:
        return _positive_int(value, label="argument")
    except BundleError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _canonical_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise BundleError(
            f"{label}_not_sha256: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _canonical_sha40(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise BundleError(
            f"{label}_not_sha40: {value!r}",
            exit_kind="input_boundary_error",
        )
    return value


def _canonical_repository(value: Any, *, label: str) -> str:
    text = _non_empty_text(value, label=label)
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text) is None:
        raise BundleError(
            f"{label}_not_repository_id: {text!r}",
            exit_kind="input_boundary_error",
        )
    return text


def _parse_utc(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
        value,
    ) is None:
        raise BundleError(
            f"{label}_not_canonical_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BundleError(
            f"{label}_invalid_utc: {value!r}: {exc}",
            exit_kind="input_boundary_error",
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise BundleError(
            f"{label}_not_utc: {value!r}",
            exit_kind="input_boundary_error",
        )
    return parsed


def _canonical_flat_member(value: Any, *, label: str) -> str:
    text = _non_empty_text(value, label=label)
    if (
        "/" in text
        or "\\" in text
        or text in {".", ".."}
        or PurePosixPath(text).name != text
    ):
        raise BundleError(
            f"{label}_not_canonical_flat_member: {text!r}",
            exit_kind="archive_boundary_error",
        )
    return text


def _canonical_archive_member(value: Any, *, label: str) -> str:
    text = _non_empty_text(value, label=label)
    if "\\" in text or text.endswith("/"):
        raise BundleError(
            f"{label}_unsafe_member: {text!r}",
            exit_kind="archive_boundary_error",
        )
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError(
            f"{label}_unsafe_member: {text!r}",
            exit_kind="archive_boundary_error",
        )
    if path.as_posix() != text:
        raise BundleError(
            f"{label}_noncanonical_member: {text!r}",
            exit_kind="archive_boundary_error",
        )
    return text


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: Iterable[str],
    *,
    label: str,
) -> None:
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        raise BundleError(
            f"{label}_key_set_mismatch: "
            f"missing={sorted(expected_set - actual)!r} "
            f"unexpected={sorted(actual - expected_set)!r}",
            exit_kind="contract_boundary_error",
        )


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BundleError(
            f"{label}_not_object",
            exit_kind="contract_boundary_error",
        )
    return value


def _require_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise BundleError(
            f"{label}_not_array",
            exit_kind="contract_boundary_error",
        )
    return value


def _require_bool(value: Any, *, label: str) -> bool:
    if type(value) is not bool:
        raise BundleError(
            f"{label}_not_boolean: {value!r}",
            exit_kind="contract_boundary_error",
        )
    return value


def _expected_run_key(
    *,
    run_id: int,
    run_attempt: int,
    workflow_name: str,
) -> str:
    return (
        f"GITHUB_RUN_ID={run_id}"
        f"|GITHUB_RUN_ATTEMPT={run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
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


def _validated_trusted_git(path: Path) -> Path:
    if not path.is_absolute():
        raise BundleError(
            f"trusted_git_not_absolute: {path}",
            exit_kind="trusted_git_error",
        )
    candidate = _normalized_absolute_path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BundleError(
            f"trusted_git_unresolvable: {candidate}: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if os.path.normcase(str(candidate)) != os.path.normcase(str(resolved)):
        raise BundleError(
            f"trusted_git_alias_rejected: supplied={candidate} resolved={resolved}",
            exit_kind="trusted_git_error",
        )

    cursor = resolved
    while True:
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise BundleError(
                f"trusted_git_component_unavailable: {cursor}: {exc}",
                exit_kind="trusted_git_error",
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise BundleError(
                f"trusted_git_symlink_component_rejected: {cursor}",
                exit_kind="trusted_git_error",
            )
        if cursor == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise BundleError(
                    f"trusted_git_not_regular_file: {cursor}",
                    exit_kind="trusted_git_error",
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise BundleError(
                f"trusted_git_parent_not_directory: {cursor}",
                exit_kind="trusted_git_error",
            )
        if metadata.st_uid != 0:
            raise BundleError(
                f"trusted_git_unprotected_owner_rejected: {cursor}",
                exit_kind="trusted_git_error",
            )
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise BundleError(
                f"trusted_git_writable_component_rejected: {cursor}",
                exit_kind="trusted_git_error",
            )
        if cursor == cursor.parent:
            break
        cursor = cursor.parent

    approved = {
        os.path.normcase(str(_normalized_absolute_path(item)))
        for item in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    }
    if os.path.normcase(str(resolved)) not in approved:
        raise BundleError(
            f"trusted_git_unapproved_candidate: {resolved}",
            exit_kind="trusted_git_error",
        )
    if not os.access(resolved, os.X_OK):
        raise BundleError(
            f"trusted_git_not_executable: {resolved}",
            exit_kind="trusted_git_error",
        )
    return resolved


def _select_trusted_git(explicit: str | None) -> Path:
    if explicit is not None:
        return _validated_trusted_git(Path(explicit))
    errors: list[str] = []
    for candidate in LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES:
        if not candidate.exists():
            errors.append(f"missing:{candidate}")
            continue
        try:
            return _validated_trusted_git(candidate)
        except BundleError as exc:
            errors.append(str(exc))
    raise BundleError(
        "trusted_git_unavailable: " + json.dumps(errors, sort_keys=True),
        exit_kind="trusted_git_error",
    )


def _git_command(
    *,
    git_path: Path,
    repository_root: Path,
    arguments: Sequence[str],
) -> list[str]:
    command = [
        str(git_path),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
    ]
    for key, value in GIT_LOCAL_ONLY_COMMAND_CONFIG:
        command.extend(("-c", f"{key}={value}"))
    command.extend(("-c", f"safe.directory={repository_root}"))
    command.extend(("-C", str(repository_root)))
    command.extend(arguments)
    return command


def _run_git(
    *,
    git_path: Path,
    repository_root: Path,
    arguments: Sequence[str],
    label: str,
    max_output_bytes: int = MAX_GIT_OUTPUT_BYTES,
    timeout_seconds: int = 60,
) -> bytes:
    command = _git_command(
        git_path=git_path,
        repository_root=repository_root,
        arguments=arguments,
    )
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
        raise BundleError(
            f"{label}_git_execution_failed: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if len(result.stdout) > max_output_bytes:
        raise BundleError(
            f"{label}_git_stdout_too_large: "
            f"size={len(result.stdout)} maximum={max_output_bytes}",
            exit_kind="resource_boundary_error",
        )
    if len(result.stderr) > 64 * 1024:
        raise BundleError(
            f"{label}_git_stderr_too_large: {len(result.stderr)}",
            exit_kind="resource_boundary_error",
        )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BundleError(
            f"{label}_git_failed: returncode={result.returncode} detail={detail!r}",
            exit_kind="trusted_git_error",
        )
    return result.stdout


def _require_trusted_git_capability(git_path: Path) -> None:
    try:
        result = subprocess.run(
            [str(git_path), "--no-lazy-fetch", "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            env=_git_environment(git_path),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BundleError(
            f"trusted_git_capability_probe_failed: {exc}",
            exit_kind="trusted_git_error",
        ) from exc
    if result.returncode != 0:
        raise BundleError(
            "trusted_git_no_lazy_fetch_unsupported: "
            + result.stderr.decode("utf-8", errors="replace").strip(),
            exit_kind="trusted_git_error",
        )


def _verify_git_repository(
    *,
    git_path: Path,
    repository_root: Path,
    expected_revision: str,
) -> None:
    top = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("rev-parse", "--show-toplevel"),
        label="control_plane_top_level",
        max_output_bytes=4096,
    )
    try:
        observed_root = Path(top.decode("utf-8", errors="strict").strip())
    except UnicodeDecodeError as exc:
        raise BundleError(
            "control_plane_top_level_invalid_utf8",
            exit_kind="trusted_git_error",
        ) from exc
    if not same_target(observed_root, repository_root):
        raise BundleError(
            "control_plane_repository_root_mismatch: "
            f"expected={repository_root} actual={observed_root}",
            exit_kind="trusted_git_error",
        )
    head = _run_git(
        git_path=git_path,
        repository_root=repository_root,
        arguments=("rev-parse", "HEAD"),
        label="control_plane_head",
        max_output_bytes=4096,
    ).decode("ascii", errors="strict").strip().lower()
    if head != expected_revision:
        raise BundleError(
            f"control_plane_head_mismatch: expected={expected_revision} actual={head}",
            exit_kind="trusted_git_error",
        )


def _git_blob_sha1(payload: bytes) -> str:
    framed = b"blob " + str(len(payload)).encode("ascii") + b"\x00" + payload
    return hashlib.sha1(framed).hexdigest()


def _verify_producer_source(
    *,
    git_path: Path,
    control_plane_root: Path,
    control_plane_revision: str,
) -> SourceBinding:
    expected_path = control_plane_root / PurePosixPath(PRODUCER_SOURCE_PATH)
    executed_path = Path(__file__).resolve(strict=True)
    if not same_target(executed_path, expected_path):
        raise BundleError(
            "producer_invocation_path_mismatch: "
            f"expected={expected_path} actual={executed_path}",
            exit_kind="producer_binding_error",
        )

    tree_row = _run_git(
        git_path=git_path,
        repository_root=control_plane_root,
        arguments=(
            "ls-tree",
            "-z",
            control_plane_revision,
            "--",
            PRODUCER_SOURCE_PATH,
        ),
        label="producer_ls_tree",
        max_output_bytes=16 * 1024,
    )
    rows = [row for row in tree_row.split(b"\x00") if row]
    if len(rows) != 1:
        raise BundleError(
            f"producer_tree_entry_count_invalid: {len(rows)}",
            exit_kind="producer_binding_error",
        )
    try:
        metadata, raw_path = rows[0].split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split(" ")
        repository_path = raw_path.decode("utf-8", errors="strict")
    except Exception as exc:
        raise BundleError(
            f"producer_tree_entry_invalid: {exc}",
            exit_kind="producer_binding_error",
        ) from exc
    if (
        mode not in {"100644", "100755"}
        or object_type != "blob"
        or re.fullmatch(r"[0-9a-f]{40}", object_id) is None
        or repository_path != PRODUCER_SOURCE_PATH
    ):
        raise BundleError(
            "producer_tree_entry_mismatch: "
            f"mode={mode!r} type={object_type!r} id={object_id!r} "
            f"path={repository_path!r}",
            exit_kind="producer_binding_error",
        )

    size_text = _run_git(
        git_path=git_path,
        repository_root=control_plane_root,
        arguments=("cat-file", "-s", object_id),
        label="producer_blob_size",
        max_output_bytes=4096,
    ).decode("ascii", errors="strict").strip()
    size = _positive_int(size_text, label="producer_blob_size")
    if size > MAX_PRODUCER_SOURCE_BYTES:
        raise BundleError(
            f"producer_source_too_large: size={size} maximum={MAX_PRODUCER_SOURCE_BYTES}",
            exit_kind="resource_boundary_error",
        )
    committed = _run_git(
        git_path=git_path,
        repository_root=control_plane_root,
        arguments=("cat-file", "blob", object_id),
        label="producer_blob",
        max_output_bytes=MAX_PRODUCER_SOURCE_BYTES,
    )
    if len(committed) != size or _git_blob_sha1(committed) != object_id:
        raise BundleError(
            "producer_blob_identity_mismatch",
            exit_kind="producer_binding_error",
        )

    with OpenedInput.open(
        expected_path,
        label="producer_worktree_source",
        max_bytes=MAX_PRODUCER_SOURCE_BYTES,
        require_read_only=False,
        require_single_link=False,
    ) as opened:
        working = opened.read_bytes(
            label="producer_worktree_source",
            max_bytes=MAX_PRODUCER_SOURCE_BYTES,
        )
    if working != committed:
        raise BundleError(
            "producer_worktree_bytes_do_not_match_committed_blob",
            exit_kind="producer_binding_error",
        )
    return SourceBinding(
        source_sha256=sha256_bytes(committed),
        source_bytes=committed,
        source_path=expected_path,
    )


def _reverify_producer_source(
    *,
    git_path: Path,
    control_plane_root: Path,
    control_plane_revision: str,
    expected: SourceBinding,
) -> None:
    current = _verify_producer_source(
        git_path=git_path,
        control_plane_root=control_plane_root,
        control_plane_revision=control_plane_revision,
    )
    if (
        current.source_sha256 != expected.source_sha256
        or current.source_bytes != expected.source_bytes
        or not same_target(current.source_path, expected.source_path)
    ):
        raise BundleError(
            "producer_source_changed_during_intake",
            exit_kind="producer_binding_error",
        )


def _provider_artifact_from_args(args: argparse.Namespace) -> ProviderArtifact:
    repository = _canonical_repository(args.repository, label="repository")
    workflow_name = _non_empty_text(
        args.provider_workflow_name,
        label="provider_workflow_name",
    )
    workflow_path = _non_empty_text(
        args.provider_workflow_path,
        label="provider_workflow_path",
    )
    if workflow_name != PROVIDER_WORKFLOW_NAME:
        raise BundleError(
            f"provider_workflow_name_mismatch: {workflow_name!r}",
            exit_kind="provider_binding_error",
        )
    if workflow_path != PROVIDER_WORKFLOW_PATH:
        raise BundleError(
            f"provider_workflow_path_mismatch: {workflow_path!r}",
            exit_kind="provider_binding_error",
        )
    exact_provider_fields = {
        "provider_workflow_event": (args.provider_workflow_event, "workflow_dispatch"),
        "provider_workflow_head_branch": (args.provider_workflow_head_branch, "main"),
        "provider_workflow_status": (args.provider_workflow_status, "completed"),
        "provider_workflow_conclusion": (args.provider_workflow_conclusion, "success"),
    }
    for label, (actual, expected) in exact_provider_fields.items():
        if actual != expected:
            raise BundleError(
                f"{label}_mismatch: expected={expected!r} actual={actual!r}",
                exit_kind="provider_binding_error",
            )

    run_id = _positive_int(args.provider_workflow_run_id, label="provider_workflow_run_id")
    run_number = _positive_int(
        args.provider_workflow_run_number,
        label="provider_workflow_run_number",
    )
    run_attempt = _positive_int(
        args.provider_workflow_run_attempt,
        label="provider_workflow_run_attempt",
    )
    workflow_revision = _canonical_sha40(
        args.provider_workflow_revision,
        label="provider_workflow_revision",
    )
    workflow_updated = _non_empty_text(
        args.provider_workflow_updated_utc,
        label="provider_workflow_updated_utc",
    )
    _parse_utc(workflow_updated, label="provider_workflow_updated_utc")

    artifact_id = _positive_int(args.provider_artifact_id, label="provider_artifact_id")
    artifact_name = _non_empty_text(
        args.provider_artifact_name,
        label="provider_artifact_name",
    )
    match = re.fullmatch(
        r"pulsemech-compute-current-run-export-candidate-([1-9][0-9]*)-([1-9][0-9]*)",
        artifact_name,
    )
    if match is None:
        raise BundleError(
            f"provider_artifact_name_invalid: {artifact_name!r}",
            exit_kind="provider_binding_error",
        )
    source_run_id = int(match.group(1), 10)
    source_run_attempt = int(match.group(2), 10)

    created_utc = _non_empty_text(
        args.provider_artifact_created_utc,
        label="provider_artifact_created_utc",
    )
    expires_utc = _non_empty_text(
        args.provider_artifact_expires_utc,
        label="provider_artifact_expires_utc",
    )
    created = _parse_utc(created_utc, label="provider_artifact_created_utc")
    expires = _parse_utc(expires_utc, label="provider_artifact_expires_utc")
    if created >= expires:
        raise BundleError(
            "provider_artifact_time_window_invalid: created_utc must precede expires_utc",
            exit_kind="provider_binding_error",
        )
    if args.provider_artifact_expired != "false":
        raise BundleError(
            f"provider_artifact_expired_or_unknown: {args.provider_artifact_expired!r}",
            exit_kind="provider_binding_error",
        )

    artifact_sha256 = _canonical_sha256(
        args.provider_artifact_sha256,
        label="provider_artifact_sha256",
    )
    artifact_size = _positive_int(
        args.provider_artifact_size_bytes,
        label="provider_artifact_size_bytes",
    )
    run_key = _expected_run_key(
        run_id=run_id,
        run_attempt=run_attempt,
        workflow_name=workflow_name,
    )
    return ProviderArtifact(
        repository=repository,
        workflow_name=workflow_name,
        workflow_path=workflow_path,
        workflow_run_id=run_id,
        workflow_run_number=run_number,
        workflow_run_attempt=run_attempt,
        workflow_run_key=run_key,
        workflow_revision=workflow_revision,
        workflow_updated_utc=workflow_updated,
        artifact_id=artifact_id,
        artifact_name=artifact_name,
        artifact_created_utc=created_utc,
        artifact_expires_utc=expires_utc,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size,
        source_run_id_from_name=source_run_id,
        source_run_attempt_from_name=source_run_attempt,
    )


def _validate_zip_info(
    info: zipfile.ZipInfo,
    *,
    label: str,
    flat: bool,
    max_member_bytes: int,
) -> str:
    name = (
        _canonical_flat_member(info.filename, label=label)
        if flat
        else _canonical_archive_member(info.filename, label=label)
    )
    mode = (info.external_attr >> 16) & 0xFFFF
    if info.is_dir() or (mode and not stat.S_ISREG(mode)):
        raise BundleError(
            f"{label}_non_regular_member: {name}",
            exit_kind="archive_boundary_error",
        )
    if info.flag_bits & 0x1:
        raise BundleError(
            f"{label}_encrypted_member: {name}",
            exit_kind="archive_boundary_error",
        )
    if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        raise BundleError(
            f"{label}_unsupported_compression: {name}",
            exit_kind="archive_boundary_error",
        )
    if info.file_size < 0 or info.file_size > max_member_bytes:
        raise BundleError(
            f"{label}_member_size_invalid: name={name!r} size={info.file_size} "
            f"maximum={max_member_bytes}",
            exit_kind="resource_boundary_error",
        )
    if info.compress_size < 0:
        raise BundleError(
            f"{label}_compressed_size_invalid: {name}",
            exit_kind="archive_boundary_error",
        )
    return name


def _zip_info_map(
    archive: zipfile.ZipFile,
    *,
    label: str,
    flat: bool,
    max_members: int,
    max_member_bytes: int,
    max_total_uncompressed_bytes: int,
) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if not infos or len(infos) > max_members:
        raise BundleError(
            f"{label}_member_count_invalid: count={len(infos)} maximum={max_members}",
            exit_kind="archive_boundary_error",
        )
    result: dict[str, zipfile.ZipInfo] = {}
    total = 0
    for info in infos:
        name = _validate_zip_info(
            info,
            label=label,
            flat=flat,
            max_member_bytes=max_member_bytes,
        )
        if name in result:
            raise BundleError(
                f"{label}_duplicate_member: {name}",
                exit_kind="archive_boundary_error",
            )
        total += info.file_size
        if total > max_total_uncompressed_bytes:
            raise BundleError(
                f"{label}_aggregate_uncompressed_size_exceeded: "
                f"size={total} maximum={max_total_uncompressed_bytes}",
                exit_kind="resource_boundary_error",
            )
        result[name] = info
    return result


def _read_zip_member_bytes(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    if info.file_size > max_bytes:
        raise BundleError(
            f"{label}_too_large: size={info.file_size} maximum={max_bytes}",
            exit_kind="resource_boundary_error",
        )
    chunks: list[bytes] = []
    total = 0
    try:
        with archive.open(info, "r") as stream:
            while True:
                chunk = stream.read(min(HASH_CHUNK_BYTES, max_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise BundleError(
                        f"{label}_too_large_during_read: size>{max_bytes}",
                        exit_kind="resource_boundary_error",
                    )
                chunks.append(chunk)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise BundleError(
            f"{label}_zip_member_read_failed: {exc}",
            exit_kind="archive_boundary_error",
        ) from exc
    payload = b"".join(chunks)
    if len(payload) != info.file_size:
        raise BundleError(
            f"{label}_size_mismatch: expected={info.file_size} actual={len(payload)}",
            exit_kind="archive_boundary_error",
        )
    return payload


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise BundleError(
                "output_write_returned_zero",
                exit_kind="output_boundary_error",
            )
        offset += written


def _copy_zip_member_to_output(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    output: StagedOutputDirectory,
    output_name: str,
    label: str,
    retain_bytes: bool,
    max_retained_bytes: int,
) -> tuple[str, int, bytes | None]:
    descriptor = output.create_file(output_name)
    digest = hashlib.sha256()
    total = 0
    retained: list[bytes] = []
    try:
        try:
            with archive.open(info, "r") as stream:
                while True:
                    chunk = stream.read(HASH_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > info.file_size:
                        raise BundleError(
                            f"{label}_expanded_past_declared_size",
                            exit_kind="archive_boundary_error",
                        )
                    digest.update(chunk)
                    _write_all(descriptor, chunk)
                    if retain_bytes:
                        if total > max_retained_bytes:
                            raise BundleError(
                                f"{label}_retained_bytes_exceeded: "
                                f"size={total} maximum={max_retained_bytes}",
                                exit_kind="resource_boundary_error",
                            )
                        retained.append(chunk)
        except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
            raise BundleError(
                f"{label}_zip_member_read_failed: {exc}",
                exit_kind="archive_boundary_error",
            ) from exc
        if total != info.file_size:
            raise BundleError(
                f"{label}_size_mismatch: expected={info.file_size} actual={total}",
                exit_kind="archive_boundary_error",
            )
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        meta = os.fstat(descriptor)
        expected_identity = output.owned_files[output_name]
        if (int(meta.st_dev), int(meta.st_ino)) != expected_identity:
            raise BundleError(
                f"{label}_output_descriptor_identity_changed",
                exit_kind="output_boundary_error",
            )
        named = os.stat(
            output_name,
            dir_fd=output.directory_descriptor,
            follow_symlinks=False,
        )
        if (
            stat.S_ISLNK(named.st_mode)
            or (int(named.st_dev), int(named.st_ino)) != expected_identity
        ):
            raise BundleError(
                f"{label}_output_name_identity_changed",
                exit_kind="output_boundary_error",
            )
    finally:
        os.close(descriptor)
    return digest.hexdigest(), total, b"".join(retained) if retain_bytes else None


def _validate_candidate_manifest(
    manifest: dict[str, Any],
    *,
    provider: ProviderArtifact,
    outer_member_names: set[str],
) -> tuple[dict[str, dict[str, Any]], str]:
    _require_exact_keys(
        manifest,
        {
            "authority_boundary",
            "control_plane_revision",
            "document_type",
            "file_count",
            "files",
            "manifest_scope",
            "ok",
            "schema_version",
            "source_run_attempt",
            "source_run_id",
            "subject_revision",
        },
        label="candidate_manifest",
    )
    if manifest.get("schema_version") != (
        "pulsemech_compute_current_run_export_candidate_output_manifest_v0"
    ):
        raise BundleError("candidate_manifest_schema_version_mismatch")
    if manifest.get("document_type") != (
        "pulsemech_compute_current_run_export_candidate_output_manifest"
    ):
        raise BundleError("candidate_manifest_document_type_mismatch")
    if manifest.get("ok") is not True:
        raise BundleError("candidate_manifest_not_ok")
    if manifest.get("manifest_scope") != "all_candidate_files_except_this_manifest":
        raise BundleError("candidate_manifest_scope_mismatch")
    if manifest.get("authority_boundary") != EXPECTED_MANIFEST_AUTHORITY:
        raise BundleError("candidate_manifest_authority_boundary_mismatch")
    if manifest.get("control_plane_revision") != provider.workflow_revision:
        raise BundleError("candidate_manifest_provider_revision_mismatch")
    if manifest.get("source_run_id") != provider.source_run_id_from_name:
        raise BundleError("candidate_manifest_source_run_id_mismatch")
    if manifest.get("source_run_attempt") != provider.source_run_attempt_from_name:
        raise BundleError("candidate_manifest_source_run_attempt_mismatch")
    _canonical_sha40(manifest.get("subject_revision"), label="candidate_subject_revision")

    rows = _require_list(manifest.get("files"), label="candidate_manifest_files")
    if manifest.get("file_count") != len(rows) or len(rows) != 6:
        raise BundleError(
            f"candidate_manifest_file_count_mismatch: "
            f"declared={manifest.get('file_count')!r} actual={len(rows)}"
        )
    declared: dict[str, dict[str, Any]] = {}
    ordered_paths: list[str] = []
    for index, item in enumerate(rows):
        row = _require_object(item, label=f"candidate_manifest_file_{index}")
        _require_exact_keys(
            row,
            {"path", "sha256", "size_bytes"},
            label=f"candidate_manifest_file_{index}",
        )
        path = _canonical_flat_member(
            row.get("path"),
            label=f"candidate_manifest_path_{index}",
        )
        if path in declared:
            raise BundleError(f"candidate_manifest_duplicate_path: {path}")
        digest = _canonical_sha256(
            row.get("sha256"),
            label=f"candidate_manifest_sha256_{path}",
        )
        size = _positive_int(
            row.get("size_bytes"),
            label=f"candidate_manifest_size_{path}",
        )
        declared[path] = {
            "path": path,
            "sha256": digest,
            "size_bytes": size,
        }
        ordered_paths.append(path)
    if ordered_paths != sorted(ordered_paths):
        raise BundleError("candidate_manifest_rows_not_sorted")
    if not FIXED_CANDIDATE_FILES.issubset(declared):
        raise BundleError(
            "candidate_manifest_fixed_files_missing: "
            f"{sorted(FIXED_CANDIDATE_FILES - set(declared))!r}"
        )
    carrier_names = sorted(set(declared) - FIXED_CANDIDATE_FILES)
    if len(carrier_names) != 1:
        raise BundleError(
            f"candidate_manifest_carrier_count_invalid: {carrier_names!r}"
        )
    carrier_name = carrier_names[0]
    expected_carrier_name = (
        f"pulsemech-current-run-export-{provider.source_run_id_from_name}-"
        f"{provider.source_run_attempt_from_name}-v0.zip"
    )
    if carrier_name != expected_carrier_name:
        raise BundleError(
            f"candidate_manifest_carrier_name_mismatch: "
            f"expected={expected_carrier_name!r} actual={carrier_name!r}"
        )
    expected_outer = set(declared) | {CANDIDATE_MANIFEST_NAME}
    if outer_member_names != expected_outer:
        raise BundleError(
            "provider_envelope_member_set_mismatch: "
            f"missing={sorted(expected_outer - outer_member_names)!r} "
            f"unexpected={sorted(outer_member_names - expected_outer)!r}"
        )
    return declared, carrier_name


def _validate_source_resolution(
    document: dict[str, Any],
    *,
    provider: ProviderArtifact,
) -> SourceSubject:
    _require_exact_keys(
        document,
        {
            "authority_boundary",
            "control_plane",
            "document_type",
            "ok",
            "schema_version",
            "source_run",
        },
        label="source_resolution",
    )
    if document.get("schema_version") != (
        "pulsemech_compute_current_run_candidate_source_resolution_v0"
    ):
        raise BundleError("source_resolution_schema_version_mismatch")
    if document.get("document_type") != (
        "pulsemech_compute_current_run_candidate_source_resolution"
    ):
        raise BundleError("source_resolution_document_type_mismatch")
    if document.get("ok") is not True:
        raise BundleError("source_resolution_not_ok")
    if document.get("authority_boundary") != EXPECTED_SOURCE_RESOLUTION_AUTHORITY:
        raise BundleError("source_resolution_authority_boundary_mismatch")

    control = _require_object(
        document.get("control_plane"),
        label="source_resolution_control_plane",
    )
    _require_exact_keys(
        control,
        {"repository", "revision", "workflow_ref"},
        label="source_resolution_control_plane",
    )
    expected_provider_workflow_ref = (
        f"{provider.repository}/{PROVIDER_WORKFLOW_PATH}@refs/heads/main"
    )
    if control != {
        "repository": provider.repository,
        "revision": provider.workflow_revision,
        "workflow_ref": expected_provider_workflow_ref,
    }:
        raise BundleError("source_resolution_control_plane_mismatch")

    source = _require_object(document.get("source_run"), label="source_run")
    _require_exact_keys(
        source,
        {
            "event",
            "head_branch",
            "html_url",
            "release_candidate_id",
            "repository",
            "run_attempt",
            "run_id",
            "run_key",
            "run_number",
            "source_ref",
            "subject_revision",
            "updated_utc",
            "workflow_name",
            "workflow_path",
        },
        label="source_run",
    )
    run_id = _positive_int(source.get("run_id"), label="source_run_id")
    run_number = _positive_int(source.get("run_number"), label="source_run_number")
    run_attempt = _positive_int(
        source.get("run_attempt"),
        label="source_run_attempt",
    )
    if run_id != provider.source_run_id_from_name:
        raise BundleError("source_resolution_run_id_artifact_name_mismatch")
    if run_attempt != provider.source_run_attempt_from_name:
        raise BundleError("source_resolution_attempt_artifact_name_mismatch")
    expected_run_key = _expected_run_key(
        run_id=run_id,
        run_attempt=run_attempt,
        workflow_name=SOURCE_WORKFLOW_NAME,
    )
    subject_revision = _canonical_sha40(
        source.get("subject_revision"),
        label="source_subject_revision",
    )
    updated_utc = _non_empty_text(
        source.get("updated_utc"),
        label="source_updated_utc",
    )
    _parse_utc(updated_utc, label="source_updated_utc")
    release_candidate_id = f"pulse-ci-current-run:{run_id}:{run_attempt}"
    exact = {
        "event": "workflow_dispatch",
        "head_branch": "main",
        "release_candidate_id": release_candidate_id,
        "repository": provider.repository,
        "run_key": expected_run_key,
        "source_ref": SOURCE_REF,
        "workflow_name": SOURCE_WORKFLOW_NAME,
        "workflow_path": SOURCE_WORKFLOW_PATH,
    }
    for field, expected in exact.items():
        if source.get(field) != expected:
            raise BundleError(
                f"source_resolution_{field}_mismatch: "
                f"expected={expected!r} actual={source.get(field)!r}"
            )
    html_url = source.get("html_url")
    if html_url is not None and not isinstance(html_url, str):
        raise BundleError("source_resolution_html_url_invalid")
    return SourceSubject(
        repository=provider.repository,
        source_run_id=run_id,
        source_run_number=run_number,
        source_run_attempt=run_attempt,
        source_run_key=expected_run_key,
        subject_revision=subject_revision,
        source_updated_utc=updated_utc,
        release_candidate_id=release_candidate_id,
    )


def _validate_source_selection(
    document: dict[str, Any],
    *,
    subject: SourceSubject,
) -> dict[str, dict[str, Any]]:
    _require_exact_keys(
        document,
        {
            "artifacts",
            "authority_boundary",
            "document_type",
            "ok",
            "schema_version",
            "source_run_attempt",
            "source_run_id",
        },
        label="source_selection",
    )
    if document.get("schema_version") != (
        "pulsemech_compute_current_run_candidate_artifact_selection_v0"
    ):
        raise BundleError("source_selection_schema_version_mismatch")
    if document.get("document_type") != (
        "pulsemech_compute_current_run_candidate_artifact_selection"
    ):
        raise BundleError("source_selection_document_type_mismatch")
    if document.get("ok") is not True:
        raise BundleError("source_selection_not_ok")
    if document.get("authority_boundary") != EXPECTED_SELECTION_AUTHORITY:
        raise BundleError("source_selection_authority_boundary_mismatch")
    if document.get("source_run_id") != subject.source_run_id:
        raise BundleError("source_selection_run_id_mismatch")
    if document.get("source_run_attempt") != subject.source_run_attempt:
        raise BundleError("source_selection_attempt_mismatch")

    artifacts = _require_list(document.get("artifacts"), label="source_artifacts")
    if len(artifacts) != 3:
        raise BundleError(f"source_artifact_count_invalid: {len(artifacts)}")
    rows: dict[str, dict[str, Any]] = {}
    observed_keys: list[str] = []
    artifact_ids: set[int] = set()
    for index, item in enumerate(artifacts):
        row = _require_object(item, label=f"source_artifact_{index}")
        _require_exact_keys(
            row,
            {
                "artifact_id",
                "artifact_name",
                "created_at",
                "download_file_name",
                "expires_at",
                "expected_sha256",
                "expected_size_bytes",
                "key",
                "role",
            },
            label=f"source_artifact_{index}",
        )
        key = _non_empty_text(row.get("key"), label=f"source_artifact_key_{index}")
        if key not in SOURCE_ARTIFACT_ROLES or key in rows:
            raise BundleError(f"source_artifact_key_invalid_or_duplicate: {key!r}")
        expected_name = (
            f"{SOURCE_ARTIFACT_NAME_PREFIXES[key]}-"
            f"{subject.source_run_id}-{subject.source_run_attempt}"
        )
        expected_file_name = expected_name + ".zip"
        exact = {
            "artifact_name": expected_name,
            "download_file_name": expected_file_name,
            "role": SOURCE_ARTIFACT_ROLES[key],
        }
        for field, expected in exact.items():
            if row.get(field) != expected:
                raise BundleError(
                    f"source_artifact_{key}_{field}_mismatch: "
                    f"expected={expected!r} actual={row.get(field)!r}"
                )
        artifact_id = _positive_int(
            row.get("artifact_id"),
            label=f"source_artifact_{key}_id",
        )
        if artifact_id in artifact_ids:
            raise BundleError(f"source_artifact_id_duplicate: {artifact_id}")
        artifact_ids.add(artifact_id)
        _positive_int(
            row.get("expected_size_bytes"),
            label=f"source_artifact_{key}_size",
        )
        _canonical_sha256(
            row.get("expected_sha256"),
            label=f"source_artifact_{key}_sha256",
        )
        created = _parse_utc(
            row.get("created_at"),
            label=f"source_artifact_{key}_created_at",
        )
        expires = _parse_utc(
            row.get("expires_at"),
            label=f"source_artifact_{key}_expires_at",
        )
        if created >= expires:
            raise BundleError(f"source_artifact_{key}_time_window_invalid")
        rows[key] = row
        observed_keys.append(key)
    if observed_keys != sorted(SOURCE_ARTIFACT_ROLES):
        raise BundleError(
            f"source_artifact_order_mismatch: {observed_keys!r}"
        )
    return rows


def _validate_carrier_metadata(
    document: dict[str, Any],
    *,
    subject: SourceSubject,
    provider_revision: str,
    carrier_name: str,
    carrier_sha256: str,
    carrier_size: int,
) -> None:
    _require_exact_keys(
        document,
        {
            "artifact_payload_mode",
            "carrier_id",
            "carrier_kind",
            "finalized",
            "finalized_utc",
            "immutable",
            "media_type",
            "path_base",
            "producer",
            "provider_binding",
            "root_prefix",
            "sha256",
            "size_bytes",
            "staged_relative_path",
        },
        label="carrier_metadata",
    )
    expected_root_prefix = (
        f"pulsemech-current-run-export-{subject.source_run_id}-"
        f"{subject.source_run_attempt}-v0/"
    )
    expected_carrier_id = (
        "carrier:pulsemech/current-run-export/"
        f"pulse-ci-{subject.source_run_number}/v0"
    )
    exact = {
        "artifact_payload_mode": "external_carrier",
        "carrier_id": expected_carrier_id,
        "carrier_kind": "current_run_export_archive",
        "finalized": True,
        "finalized_utc": subject.source_updated_utc,
        "immutable": True,
        "media_type": "application/zip",
        "path_base": "current_run_export_staging_root",
        "provider_binding": None,
        "root_prefix": expected_root_prefix,
        "sha256": carrier_sha256,
        "size_bytes": carrier_size,
        "staged_relative_path": f"exports/{carrier_name}",
    }
    for field, expected in exact.items():
        if document.get(field) != expected:
            raise BundleError(
                f"carrier_metadata_{field}_mismatch: "
                f"expected={expected!r} actual={document.get(field)!r}"
            )
    producer = _require_object(document.get("producer"), label="carrier_producer")
    _require_exact_keys(
        producer,
        {
            "ci_workflow_or_job_identity",
            "producer_id",
            "producer_name",
            "producer_run_key",
            "producer_source",
            "producer_source_revision",
            "producer_source_sha256",
            "producer_version",
            "production_mode",
        },
        label="carrier_producer",
    )
    _non_empty_text(
        producer.get("ci_workflow_or_job_identity"),
        label="carrier_producer_ci_identity",
    )
    expected_producer = {
        "producer_id": "producer:pulsemech-current-run-export-carrier-loader-v0",
        "producer_name": "PULSEmech current-run export carrier loader",
        "producer_run_key": subject.source_run_key,
        "producer_source": "tools/load_pulsemech_compute_current_run_export_carrier_v0.py",
        "producer_source_revision": provider_revision,
        "producer_version": "0.1.0",
        "production_mode": "current_run_export_carrier_builder",
    }
    for field, expected in expected_producer.items():
        if producer.get(field) != expected:
            raise BundleError(
                f"carrier_producer_{field}_mismatch: "
                f"expected={expected!r} actual={producer.get(field)!r}"
            )
    _canonical_sha256(
        producer.get("producer_source_sha256"),
        label="carrier_producer_source_sha256",
    )


def _validate_subject(
    subject_document: dict[str, Any],
    *,
    subject: SourceSubject,
) -> None:
    _require_exact_keys(
        subject_document,
        {
            "active_policy_sets",
            "decision",
            "event_name",
            "final_status_sha256",
            "materialized_gate_set_sha256",
            "policy_id",
            "policy_sha256",
            "release_candidate_id",
            "release_decision_sha256",
            "repository",
            "run_mode",
            "source_commit",
            "source_ref",
            "subject_run_key",
            "workflow_name",
            "workflow_path",
            "workflow_ref",
            "workflow_run_attempt",
            "workflow_run_id",
            "workflow_run_number",
        },
        label="expectation_subject",
    )
    exact = {
        "active_policy_sets": ["required", "release_required"],
        "decision": "ALLOW",
        "event_name": "workflow_dispatch",
        "materialized_gate_set_sha256": None,
        "release_candidate_id": subject.release_candidate_id,
        "repository": subject.repository,
        "run_mode": "prod",
        "source_commit": subject.subject_revision,
        "source_ref": SOURCE_REF,
        "subject_run_key": subject.source_run_key,
        "workflow_name": SOURCE_WORKFLOW_NAME,
        "workflow_path": SOURCE_WORKFLOW_PATH,
        "workflow_ref": (
            f"{subject.repository}/{SOURCE_WORKFLOW_PATH}@refs/heads/main"
        ),
        "workflow_run_attempt": subject.source_run_attempt,
        "workflow_run_id": subject.source_run_id,
        "workflow_run_number": subject.source_run_number,
    }
    for field, expected in exact.items():
        if subject_document.get(field) != expected:
            raise BundleError(
                f"expectation_subject_{field}_mismatch: "
                f"expected={expected!r} actual={subject_document.get(field)!r}"
            )
    for field in (
        "final_status_sha256",
        "policy_sha256",
        "release_decision_sha256",
    ):
        _canonical_sha256(subject_document.get(field), label=f"subject_{field}")
    _non_empty_text(subject_document.get("policy_id"), label="subject_policy_id")


def _validate_expectation(
    document: dict[str, Any],
    *,
    subject: SourceSubject,
    carrier_metadata: dict[str, Any],
    provider_revision: str,
    selection: dict[str, dict[str, Any]],
) -> None:
    _require_exact_keys(
        document,
        {
            "archive_layout",
            "authority_boundary",
            "authority_sources",
            "carrier",
            "content_boundary",
            "document_type",
            "errors",
            "expectation_identity",
            "expectation_producer",
            "ok",
            "packet_contract",
            "packet_producer_profile",
            "record_status",
            "schema_version",
            "subject",
            "trusted_control_plane",
        },
        label="expectation",
    )
    if document.get("schema_version") != (
        "pulsemech_compute_current_run_export_expectation_v0"
    ):
        raise BundleError("expectation_schema_version_mismatch")
    if document.get("document_type") != (
        "pulsemech_compute_current_run_export_expectation"
    ):
        raise BundleError("expectation_document_type_mismatch")
    if document.get("record_status") != "observed":
        raise BundleError("expectation_record_status_not_observed")
    if document.get("ok") is not True or document.get("errors") != []:
        raise BundleError("expectation_not_ok_or_errors_present")
    if document.get("authority_boundary") != EXPECTED_EXPECTATION_AUTHORITY:
        raise BundleError("expectation_authority_boundary_mismatch")
    if document.get("content_boundary") != EXPECTED_EXPECTATION_CONTENT:
        raise BundleError("expectation_content_boundary_mismatch")
    if document.get("carrier") != carrier_metadata:
        raise BundleError("expectation_carrier_object_mismatch")

    subject_document = _require_object(document.get("subject"), label="expectation_subject")
    _validate_subject(subject_document, subject=subject)

    identity = _require_object(
        document.get("expectation_identity"),
        label="expectation_identity",
    )
    _require_exact_keys(
        identity,
        {
            "canonicalization",
            "expectation_created_utc",
            "expectation_id",
            "expectation_scope",
            "subject_run_key",
        },
        label="expectation_identity",
    )
    expected_expectation_id = (
        f"current-run-export-expectation:{subject.repository}/"
        f"{subject.source_run_id}/{subject.source_run_attempt}"
    )
    expected_identity = {
        "canonicalization": "json-sort-keys-utf8-newline",
        "expectation_created_utc": subject.source_updated_utc,
        "expectation_id": expected_expectation_id,
        "expectation_scope": "current_run_export",
        "subject_run_key": subject.source_run_key,
    }
    if identity != expected_identity:
        raise BundleError("expectation_identity_mismatch")

    producer = _require_object(
        document.get("expectation_producer"),
        label="expectation_producer",
    )
    _require_exact_keys(
        producer,
        {
            "ci_workflow_or_job_identity",
            "producer_id",
            "producer_name",
            "producer_run_key",
            "producer_source",
            "producer_source_revision",
            "producer_source_sha256",
            "producer_version",
            "production_mode",
        },
        label="expectation_producer",
    )
    _non_empty_text(
        producer.get("ci_workflow_or_job_identity"),
        label="expectation_producer_ci_identity",
    )
    expected_producer = {
        "producer_id": "producer:pulsemech-current-run-export-expectation-builder-v0",
        "producer_name": "PULSEmech current-run export expectation builder",
        "producer_run_key": subject.source_run_key,
        "producer_source": "tools/build_pulsemech_compute_current_run_export_expectation_v0.py",
        "producer_source_revision": provider_revision,
        "producer_version": "0.1.0",
        "production_mode": "current_run_expectation_builder",
    }
    for field, expected in expected_producer.items():
        if producer.get(field) != expected:
            raise BundleError(
                f"expectation_producer_{field}_mismatch: "
                f"expected={expected!r} actual={producer.get(field)!r}"
            )
    _canonical_sha256(
        producer.get("producer_source_sha256"),
        label="expectation_producer_source_sha256",
    )

    packet_contract = document.get("packet_contract")
    if packet_contract != {
        "artifact_payload_mode": "external_carrier",
        "carrier_kind": "current_run_export_archive",
        "packet_scope": "current_run",
        "packet_type": "pulsemech_compute_subject_input_packet",
        "production_mode": "current_run_export",
        "record_status": "observed",
        "schema_version": "pulsemech_compute_subject_input_packet_v0",
        "write_mode": "subject_input_only",
    }:
        raise BundleError("expectation_packet_contract_mismatch")

    trusted = _require_object(
        document.get("trusted_control_plane"),
        label="trusted_control_plane",
    )
    _require_exact_keys(
        trusted,
        {
            "checkout_role",
            "components",
            "repository",
            "revision",
            "separate_from_subject_checkout",
            "subject_may_select_revision",
            "trust_mode",
        },
        label="trusted_control_plane",
    )
    if (
        trusted.get("checkout_role") != "protected_control_plane"
        or trusted.get("repository") != subject.repository
        or trusted.get("revision") != provider_revision
        or trusted.get("separate_from_subject_checkout") is not True
        or trusted.get("subject_may_select_revision") is not False
        or trusted.get("trust_mode") != "protected_exact_revision"
    ):
        raise BundleError("expectation_trusted_control_plane_mismatch")
    components = _require_object(
        trusted.get("components"),
        label="trusted_control_plane_components",
    )
    required_components = {
        "carrier_loader": "tools/load_pulsemech_compute_current_run_export_carrier_v0.py",
        "control_plane_workflow": PROVIDER_WORKFLOW_PATH,
        "expectation_builder": "tools/build_pulsemech_compute_current_run_export_expectation_v0.py",
        "expectation_schema": "schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json",
        "expectation_validator": "tools/check_pulsemech_compute_current_run_export_expectation_v0.py",
        "subject_input_producer_core": "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py",
        "subject_input_producer_wrapper": "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py",
        "subject_input_schema": "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
        "subject_input_validator": "tools/check_pulsemech_compute_subject_input_packet_v0.py",
    }
    if set(components) != set(required_components):
        raise BundleError("expectation_control_plane_component_set_mismatch")
    for role, path in required_components.items():
        component = _require_object(
            components.get(role),
            label=f"control_plane_component_{role}",
        )
        if component.get("path") != path:
            raise BundleError(f"control_plane_component_{role}_path_mismatch")
        if component.get("source_revision") != provider_revision:
            raise BundleError(f"control_plane_component_{role}_revision_mismatch")
        _canonical_sha256(
            component.get("sha256"),
            label=f"control_plane_component_{role}_sha256",
        )
        _non_empty_text(
            component.get("version"),
            label=f"control_plane_component_{role}_version",
        )

    carrier_producer = _require_object(
        carrier_metadata.get("producer"),
        label="carrier_producer_component_binding",
    )
    if carrier_producer.get("producer_source_sha256") != components[
        "carrier_loader"
    ].get("sha256"):
        raise BundleError("carrier_producer_component_digest_mismatch")
    if producer.get("producer_source_sha256") != components[
        "expectation_builder"
    ].get("sha256"):
        raise BundleError("expectation_producer_component_digest_mismatch")

    archive_layout = _require_object(
        document.get("archive_layout"),
        label="expectation_archive_layout",
    )
    expected_outer = carrier_metadata["root_prefix"]
    expected_original = expected_outer + "original-github-artifacts/"
    if (
        archive_layout.get("layout_id") != "pulsemech_current_run_export_layout_v0"
        or archive_layout.get("layout_version") != "0.1.0"
        or archive_layout.get("outer_prefix") != expected_outer
        or archive_layout.get("original_artifacts_prefix") != expected_original
        or archive_layout.get("expected_provider_artifact_count") != 3
        or archive_layout.get("complete_package_name")
        != selection["complete"]["download_file_name"]
        or archive_layout.get("completeness_archive_name")
        != selection["completeness"]["download_file_name"]
        or archive_layout.get("verification_archive_name")
        != selection["verification"]["download_file_name"]
    ):
        raise BundleError("expectation_archive_layout_mismatch")

    profile = _require_object(
        document.get("packet_producer_profile"),
        label="packet_producer_profile",
    )
    expected_profile = {
        "expected_archive_layout_id": "pulsemech_current_run_export_layout_v0",
        "expected_carrier_artifact_payload_mode": "external_carrier",
        "expected_carrier_id_namespace": "pulsemech/current-run-export",
        "expected_carrier_kind": "current_run_export_archive",
        "expected_carrier_media_type": "application/zip",
        "expected_packet_identity_mode": "current-run",
        "expected_packet_scope": "current_run",
        "expected_producer_source_path": "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py",
        "expected_production_mode": "current_run_export",
        "expected_repository": subject.repository,
        "expected_signer_policy_path": "policy/external_signers_v1.yml",
        "expected_source_commit": subject.subject_revision,
        "expected_subject_run_key": subject.source_run_key,
        "profile_id": "pulsemech_current_run_export_candidate_v0",
    }
    if profile != expected_profile:
        raise BundleError("expectation_packet_producer_profile_mismatch")

    authority_sources = _require_object(
        document.get("authority_sources"),
        label="expectation_authority_sources",
    )
    workflow_source = _require_object(
        authority_sources.get("workflow"),
        label="expectation_workflow_source",
    )
    policy_source = _require_object(
        authority_sources.get("policy"),
        label="expectation_policy_source",
    )
    registry_source = _require_object(
        authority_sources.get("gate_registry"),
        label="expectation_registry_source",
    )
    if (
        workflow_source.get("path_or_uri") != SOURCE_WORKFLOW_PATH
        or workflow_source.get("source_revision") != subject.subject_revision
        or workflow_source.get("workflow_name") != SOURCE_WORKFLOW_NAME
        or workflow_source.get("workflow_ref")
        != f"{subject.repository}/{SOURCE_WORKFLOW_PATH}@refs/heads/main"
    ):
        raise BundleError("expectation_workflow_source_mismatch")
    if (
        policy_source.get("path_or_uri") != "pulse_gate_policy_v0.yml"
        or policy_source.get("source_revision") != subject.subject_revision
        or policy_source.get("policy_id") != subject_document.get("policy_id")
        or policy_source.get("sha256") != subject_document.get("policy_sha256")
    ):
        raise BundleError("expectation_policy_source_mismatch")
    if (
        registry_source.get("path_or_uri") != "pulse_gate_registry_v0.yml"
        or registry_source.get("source_revision") != subject.subject_revision
    ):
        raise BundleError("expectation_registry_source_mismatch")


def _canonical_packet_authority_sources(
    expectation_sources: Any,
) -> dict[str, Any]:
    sources = _require_object(
        expectation_sources,
        label="expectation_authority_sources_projection",
    )
    result: dict[str, Any] = {}
    used: set[str] = set()
    for name in ("workflow", "policy", "gate_registry"):
        row = _require_object(
            sources.get(name),
            label=f"expectation_authority_source_{name}",
        )
        if row.get("source_id") != GENERIC_EXPECTATION_SOURCE_IDS[name]:
            raise BundleError(
                f"expectation_authority_source_{name}_id_mismatch"
            )
        projected = dict(row)
        projected["source_id"] = CANONICAL_PACKET_SOURCE_IDS[name]
        if projected["source_id"] in used:
            raise BundleError(
                f"canonical_packet_source_id_duplicate: {projected['source_id']}"
            )
        used.add(projected["source_id"])
        result[name] = projected

    additional = _require_list(
        sources.get("additional_sources"),
        label="expectation_additional_sources",
    )
    projected_additional: list[dict[str, Any]] = []
    for index, item in enumerate(additional):
        row = _require_object(
            item,
            label=f"expectation_additional_source_{index}",
        )
        role = _non_empty_text(
            row.get("role"),
            label=f"expectation_additional_source_role_{index}",
        )
        source_path = _canonical_archive_member(
            row.get("path_or_uri"),
            label=f"expectation_additional_source_path_{index}",
        )
        source_id = CANONICAL_ADDITIONAL_SOURCE_IDS.get((role, source_path))
        if source_id is None:
            raise BundleError(
                "expectation_additional_source_has_no_canonical_packet_identity: "
                f"role={role!r} path={source_path!r}"
            )
        if source_id in used:
            raise BundleError(f"canonical_packet_source_id_duplicate: {source_id}")
        used.add(source_id)
        projected = dict(row)
        projected["source_id"] = source_id
        projected_additional.append(projected)
    projected_additional.sort(key=lambda row: str(row["source_id"]))
    result["additional_sources"] = projected_additional
    return result


def _validate_packet_authority_sources(
    packet_sources: Any,
    *,
    expectation_sources: Any,
    subject: SourceSubject,
) -> bool:
    expected = _canonical_packet_authority_sources(expectation_sources)
    actual = _require_object(packet_sources, label="packet_authority_sources")
    if actual != expected:
        raise BundleError("packet_authority_sources_projection_mismatch")

    expected_roles = {
        "workflow": "workflow",
        "policy": "policy",
        "gate_registry": "gate_registry",
    }
    source_ids: list[str] = []
    for name, role in expected_roles.items():
        row = _require_object(actual.get(name), label=f"packet_source_{name}")
        source_ids.append(_non_empty_text(row.get("source_id"), label=f"{name}_id"))
        if (
            row.get("role") != role
            or row.get("source_revision") != subject.subject_revision
        ):
            raise BundleError(f"packet_source_{name}_identity_mismatch")
        _canonical_archive_member(
            row.get("path_or_uri"),
            label=f"packet_source_{name}_path",
        )
        _canonical_sha256(row.get("sha256"), label=f"packet_source_{name}_sha256")
        size = row.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise BundleError(f"packet_source_{name}_size_invalid: {size!r}")

    additional = _require_list(
        actual.get("additional_sources"),
        label="packet_additional_sources",
    )
    additional_ids: list[str] = []
    observed_role_paths: set[tuple[str, str]] = set()
    for index, item in enumerate(additional):
        row = _require_object(item, label=f"packet_additional_source_{index}")
        source_id = _non_empty_text(
            row.get("source_id"),
            label=f"packet_additional_source_id_{index}",
        )
        additional_ids.append(source_id)
        role = _non_empty_text(
            row.get("role"),
            label=f"packet_additional_source_role_{index}",
        )
        source_path = _canonical_archive_member(
            row.get("path_or_uri"),
            label=f"packet_additional_source_path_{index}",
        )
        if (
            row.get("source_revision") != subject.subject_revision
            or CANONICAL_ADDITIONAL_SOURCE_IDS.get((role, source_path)) != source_id
        ):
            raise BundleError(
                f"packet_additional_source_identity_mismatch: {source_id}"
            )
        _canonical_sha256(
            row.get("sha256"),
            label=f"packet_additional_source_sha256_{index}",
        )
        size = row.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise BundleError(
                f"packet_additional_source_size_invalid: {index}: {size!r}"
            )
        observed_role_paths.add((role, source_path))
    if additional_ids != sorted(additional_ids):
        raise BundleError("packet_additional_sources_not_sorted")
    if observed_role_paths != set(CANONICAL_ADDITIONAL_SOURCE_IDS):
        raise BundleError("packet_additional_source_role_path_set_mismatch")
    all_ids = source_ids + additional_ids
    if len(all_ids) != len(set(all_ids)):
        raise BundleError("packet_authority_source_id_duplicate")
    return True


def _expected_packet_carrier(
    carrier_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    root_prefix = _non_empty_text(
        carrier_metadata.get("root_prefix"),
        label="carrier_metadata_root_prefix",
    )
    if not root_prefix.endswith("/"):
        raise BundleError("carrier_metadata_root_prefix_missing_slash")
    return {
        "artifact_payload_mode": "external_carrier",
        "carrier_id": carrier_metadata.get("carrier_id"),
        "carrier_kind": "current_run_export_archive",
        "immutable": True,
        "media_type": "application/zip",
        "path_or_uri": carrier_metadata.get("staged_relative_path"),
        "provider_binding": None,
        "root_prefix": root_prefix[:-1],
        "sha256": carrier_metadata.get("sha256"),
        "size_bytes": carrier_metadata.get("size_bytes"),
    }


def _artifact_expected_id(artifact: Mapping[str, Any]) -> str | None:
    member_path = artifact.get("member_path")
    parent = artifact.get("container_artifact_id")
    if not isinstance(member_path, str):
        return None
    if parent is None:
        return f"artifact:{member_path}"
    if not isinstance(parent, str):
        return None
    return f"{parent}/{member_path}"


def _artifact_expected_display(
    artifact: Mapping[str, Any],
    *,
    carrier_location: str,
    artifact_index: Mapping[str, Mapping[str, Any]],
) -> str | None:
    member_path = artifact.get("member_path")
    parent = artifact.get("container_artifact_id")
    if not isinstance(member_path, str):
        return None
    if parent is None:
        return f"{carrier_location}!/{member_path}"
    if not isinstance(parent, str):
        return None
    parent_row = artifact_index.get(parent)
    if not isinstance(parent_row, Mapping):
        return None
    parent_display = parent_row.get("display_path_or_uri")
    if not isinstance(parent_display, str):
        return None
    return f"{parent_display}!/{member_path}"


def _packet_container_graph_acyclic(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> bool:
        if identifier in visited:
            return True
        if identifier in visiting:
            return False
        visiting.add(identifier)
        parent = artifacts[identifier].get("container_artifact_id")
        if isinstance(parent, str):
            if parent not in artifacts or not visit(parent):
                return False
        visiting.remove(identifier)
        visited.add(identifier)
        return True

    return all(visit(identifier) for identifier in artifacts)


def _packet_content_identity(member_path: str) -> tuple[str, str]:
    lower = member_path.lower()
    if lower.endswith(".zip"):
        return "archive", "application/zip"
    if lower.endswith(".json"):
        return "json", "application/json"
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return "jsonl", "application/x-ndjson"
    if lower.endswith(".yaml") or lower.endswith(".yml"):
        return "yaml", "application/yaml"
    if lower.endswith(".html") or lower.endswith(".htm"):
        return "html", "text/html"
    if lower.endswith(".md"):
        return "text", "text/markdown"
    return "text", "text/plain"


def _expected_packet_artifact_roles(
    *,
    packet_carrier: Mapping[str, Any],
    selection: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    root = _non_empty_text(
        packet_carrier.get("root_prefix"),
        label="packet_carrier_root_prefix_for_roles",
    ).rstrip("/") + "/"
    original = root + "original-github-artifacts/"
    top_roles = {
        root + "PRESERVATION_MANIFEST_v0.json": "preservation_manifest",
        root + "README.md": "preservation_readme",
        root + "SHA256SUMS": "preservation_checksums",
        original + str(selection["complete"].get("download_file_name")): (
            "complete_package"
        ),
        original + str(selection["completeness"].get("download_file_name")): (
            "provider_artifact_archive"
        ),
        original + str(selection["verification"].get("download_file_name")): (
            "provider_artifact_archive"
        ),
    }
    parent_kinds = {
        "artifact:" + original + str(
            selection["complete"].get("download_file_name")
        ): "complete",
        "artifact:" + original + str(
            selection["completeness"].get("download_file_name")
        ): "completeness",
        "artifact:" + original + str(
            selection["verification"].get("download_file_name")
        ): "verification",
    }
    return top_roles, parent_kinds


def _expected_packet_artifact_role(
    *,
    member_path: str,
    parent: str | None,
    top_roles: Mapping[str, str],
    parent_kinds: Mapping[str, str],
) -> str:
    if parent is None:
        role = top_roles.get(member_path)
        if role is None:
            raise BundleError(
                f"packet_unexpected_top_level_artifact: {member_path}"
            )
        return role
    parent_kind = parent_kinds.get(parent)
    if parent_kind == "complete":
        exact = ROLE_BY_PACKAGE_MEMBER.get(member_path)
        if exact is not None:
            return exact
        if (
            member_path.startswith("artifacts/recorded_release_candidates/")
            and member_path.endswith(".json")
        ):
            return "candidate_record"
        return "other"
    if parent_kind == "completeness":
        if member_path != "release_grade_package_completeness_v1.json":
            raise BundleError(
                f"packet_unexpected_completeness_archive_member: {member_path}"
            )
        return "package_completeness_report"
    if parent_kind == "verification":
        if member_path != (
            "release_grade_reference_package_verification_v0.json"
        ):
            raise BundleError(
                f"packet_unexpected_verification_archive_member: {member_path}"
            )
        return "independent_verification_report"
    raise BundleError(
        f"packet_unexpected_nested_artifact_parent: "
        f"parent={parent!r} member={member_path!r}"
    )


def _validate_packet_artifact_rows(
    rows_value: Any,
    *,
    packet_carrier: Mapping[str, Any],
    selection: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows = _require_list(rows_value, label="packet_artifacts")
    if not rows:
        raise BundleError("packet_artifacts_empty")
    artifacts: dict[str, dict[str, Any]] = {}
    identifiers: list[str] = []
    locations: set[tuple[str | None, str]] = set()
    for index, item in enumerate(rows):
        row = _require_object(item, label=f"packet_artifact_{index}")
        _require_exact_keys(row, PACKET_ARTIFACT_KEYS, label=f"packet_artifact_{index}")
        artifact_id = _non_empty_text(
            row.get("artifact_id"),
            label=f"packet_artifact_id_{index}",
        )
        if re.fullmatch(r"artifact:[A-Za-z0-9._:/@+-]+", artifact_id) is None:
            raise BundleError(f"packet_artifact_id_invalid: {artifact_id!r}")
        if artifact_id in artifacts:
            raise BundleError(f"packet_artifact_id_duplicate: {artifact_id}")
        identifiers.append(artifact_id)
        member_path = _canonical_archive_member(
            row.get("member_path"),
            label=f"packet_artifact_member_path_{index}",
        )
        parent = row.get("container_artifact_id")
        if parent is not None:
            parent = _non_empty_text(
                parent,
                label=f"packet_artifact_parent_{index}",
            )
        location = (parent, member_path)
        if location in locations:
            raise BundleError(
                f"packet_artifact_container_member_duplicate: {location!r}"
            )
        locations.add(location)
        _non_empty_text(row.get("role"), label=f"packet_artifact_role_{index}")
        kind = _non_empty_text(
            row.get("content_kind"),
            label=f"packet_artifact_content_kind_{index}",
        )
        media_type = _non_empty_text(
            row.get("media_type"),
            label=f"packet_artifact_media_type_{index}",
        )
        if kind == "archive" and media_type != "application/zip":
            raise BundleError(f"packet_archive_media_type_mismatch: {artifact_id}")
        _canonical_sha256(
            row.get("sha256"),
            label=f"packet_artifact_sha256_{index}",
        )
        size = row.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise BundleError(f"packet_artifact_size_invalid: {artifact_id}: {size!r}")
        for flag in (
            "required_for_analysis",
            "digest_verified",
            "size_verified",
            "container_path_verified",
        ):
            if not isinstance(row.get(flag), bool):
                raise BundleError(f"packet_artifact_{flag}_not_boolean: {artifact_id}")
        if (
            row.get("digest_verified") is not True
            or row.get("size_verified") is not True
            or row.get("container_path_verified") is not True
        ):
            raise BundleError(f"packet_artifact_verification_flags_not_true: {artifact_id}")
        artifacts[artifact_id] = row

    if identifiers != sorted(identifiers):
        raise BundleError("packet_artifacts_not_sorted_by_id")
    if not _packet_container_graph_acyclic(artifacts):
        raise BundleError("packet_artifact_graph_cycle_or_unresolved_parent")

    carrier_location = _non_empty_text(
        packet_carrier.get("path_or_uri"),
        label="packet_carrier_path_or_uri",
    )
    root_prefix = _non_empty_text(
        packet_carrier.get("root_prefix"),
        label="packet_carrier_root_prefix",
    )
    top_roles, parent_kinds = _expected_packet_artifact_roles(
        packet_carrier=packet_carrier,
        selection=selection,
    )
    for artifact_id, row in artifacts.items():
        if artifact_id != _artifact_expected_id(row):
            raise BundleError(f"packet_artifact_id_path_mismatch: {artifact_id}")
        if row.get("display_path_or_uri") != _artifact_expected_display(
            row,
            carrier_location=carrier_location,
            artifact_index=artifacts,
        ):
            raise BundleError(f"packet_artifact_display_path_mismatch: {artifact_id}")
        parent = row.get("container_artifact_id")
        member_path = row["member_path"]
        expected_kind, expected_media = _packet_content_identity(member_path)
        if (
            row.get("content_kind") != expected_kind
            or row.get("media_type") != expected_media
        ):
            raise BundleError(
                f"packet_artifact_content_identity_mismatch: {artifact_id}: "
                f"expected={(expected_kind, expected_media)!r} "
                f"actual={(row.get('content_kind'), row.get('media_type'))!r}"
            )
        expected_role = _expected_packet_artifact_role(
            member_path=member_path,
            parent=parent if isinstance(parent, str) else None,
            top_roles=top_roles,
            parent_kinds=parent_kinds,
        )
        if row.get("role") != expected_role:
            raise BundleError(
                f"packet_artifact_role_mismatch: {artifact_id}: "
                f"expected={expected_role!r} actual={row.get('role')!r}"
            )
        expected_required = expected_role not in NON_ANALYSIS_ROLES
        if row.get("required_for_analysis") is not expected_required:
            raise BundleError(
                f"packet_artifact_required_for_analysis_mismatch: {artifact_id}"
            )
        if expected_role not in {
            "complete_package",
            "provider_artifact_archive",
        } and row.get("provider_binding") is not None:
            raise BundleError(
                f"packet_artifact_unexpected_provider_binding: {artifact_id}"
            )
        if parent is None and not member_path.startswith(root_prefix + "/"):
            raise BundleError(f"packet_artifact_outside_carrier_root: {artifact_id}")
        if isinstance(parent, str):
            parent_row = artifacts.get(parent)
            if parent_row is None:
                raise BundleError(f"packet_artifact_parent_missing: {artifact_id}")
            if (
                parent_row.get("content_kind") != "archive"
                or parent_row.get("media_type") != "application/zip"
            ):
                raise BundleError(f"packet_artifact_parent_not_archive: {artifact_id}")
    return artifacts


class PacketArchiveResolver:
    def __init__(
        self,
        *,
        outer_input: OpenedInput,
        artifacts: Mapping[str, Mapping[str, Any]],
        max_total_retained_bytes: int,
    ) -> None:
        self.outer_input = outer_input
        self.artifacts = artifacts
        self.budget = RetainedByteBudget(max_total_retained_bytes)
        self.identities: dict[str, tuple[str, int]] = {}
        self.retained: dict[str, bytes] = {}
        self.archive_members: dict[str | None, tuple[str, ...]] = {}
        self.archives: dict[
            str | None,
            tuple[BinaryIO | io.BytesIO, zipfile.ZipFile, dict[str, zipfile.ZipInfo]],
        ] = {}
        self.active: set[str] = set()

    def close(self) -> None:
        for stream, archive, _table in self.archives.values():
            try:
                archive.close()
            finally:
                stream.close()
        self.archives.clear()

    def __enter__(self) -> "PacketArchiveResolver":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _open_archive(
        self,
        container_id: str | None,
    ) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
        cached = self.archives.get(container_id)
        if cached is not None:
            return cached[1], cached[2]
        if container_id is None:
            stream: BinaryIO | io.BytesIO = self.outer_input.duplicate_binary_reader()
            label = "packet_outer_carrier"
        else:
            self.resolve(container_id)
            payload = self.retained.get(container_id)
            if payload is None:
                raise BundleError(
                    f"packet_archive_container_bytes_not_retained: {container_id}"
                )
            stream = io.BytesIO(payload)
            label = f"packet_archive_{container_id}"
        try:
            archive = zipfile.ZipFile(stream, "r")
            table = _zip_info_map(
                archive,
                label=label,
                flat=False,
                max_members=MAX_INNER_MEMBERS,
                max_member_bytes=MAX_INNER_MEMBER_BYTES,
                max_total_uncompressed_bytes=MAX_INNER_TOTAL_UNCOMPRESSED_BYTES,
            )
        except Exception:
            stream.close()
            raise
        self.archive_members[container_id] = tuple(sorted(table))
        self.archives[container_id] = (stream, archive, table)
        return archive, table

    def resolve(self, artifact_id: str) -> tuple[str, int]:
        cached = self.identities.get(artifact_id)
        if cached is not None:
            return cached
        if artifact_id in self.active:
            raise BundleError(f"packet_artifact_container_cycle: {artifact_id}")
        row = self.artifacts.get(artifact_id)
        if row is None:
            raise BundleError(f"packet_artifact_missing: {artifact_id}")
        self.active.add(artifact_id)
        try:
            parent = row.get("container_artifact_id")
            if parent is not None and not isinstance(parent, str):
                raise BundleError(f"packet_artifact_parent_invalid: {artifact_id}")
            archive, table = self._open_archive(parent)
            member_path = row.get("member_path")
            if not isinstance(member_path, str) or member_path not in table:
                raise BundleError(
                    f"packet_artifact_member_missing: {artifact_id}: {member_path!r}"
                )
            info = table[member_path]
            declared_size = row.get("size_bytes")
            if info.file_size != declared_size:
                raise BundleError(
                    f"packet_artifact_zip_size_mismatch: {artifact_id}: "
                    f"declared={declared_size!r} zip={info.file_size}"
                )
            retain = (
                row.get("content_kind") == "archive"
                or row.get("role") in PACKET_RETAINED_ROLES
            )
            self.budget.reserve(
                info.file_size,
                label=f"packet_artifact_{artifact_id}",
            )
            digest = hashlib.sha256()
            total = 0
            chunks: list[bytes] = []
            try:
                with archive.open(info, "r") as source:
                    while True:
                        chunk = source.read(HASH_CHUNK_BYTES)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > info.file_size:
                            raise BundleError(
                                f"packet_artifact_expanded_past_declared_size: {artifact_id}"
                            )
                        digest.update(chunk)
                        if retain:
                            chunks.append(chunk)
            except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                raise BundleError(
                    f"packet_artifact_read_failed: {artifact_id}: {exc}",
                    exit_kind="archive_boundary_error",
                ) from exc
            observed = digest.hexdigest()
            if total != declared_size or observed != row.get("sha256"):
                raise BundleError(
                    f"packet_artifact_identity_mismatch: {artifact_id}: "
                    f"declared_sha={row.get('sha256')!r} observed_sha={observed} "
                    f"declared_size={declared_size!r} observed_size={total}"
                )
            if retain:
                self.retained[artifact_id] = b"".join(chunks)
            self.identities[artifact_id] = (observed, total)
            return observed, total
        finally:
            self.active.remove(artifact_id)

    def resolve_all(self) -> None:
        for artifact_id in sorted(self.artifacts):
            self.resolve(artifact_id)
        containers: list[str | None] = [None]
        containers.extend(
            artifact_id
            for artifact_id, row in self.artifacts.items()
            if row.get("content_kind") == "archive"
            and row.get("media_type") == "application/zip"
        )
        for container_id in containers:
            _archive, table = self._open_archive(container_id)
            actual = set(table)
            declared = {
                str(row.get("member_path"))
                for row in self.artifacts.values()
                if row.get("container_artifact_id") == container_id
            }
            if actual != declared:
                raise BundleError(
                    "packet_archive_member_closure_mismatch: "
                    f"container={container_id!r} "
                    f"missing={sorted(declared - actual)!r} "
                    f"unexpected={sorted(actual - declared)!r}"
                )


def _verify_packet_provider_binding(
    binding: Any,
    *,
    artifact_sha256: str,
    artifact_size: int,
    label: str,
) -> tuple[bool, bool]:
    if binding is None:
        return True, False
    row = _require_object(binding, label=f"provider_binding_{label}")
    _require_exact_keys(
        row,
        {
            "provider",
            "provider_artifact_id",
            "provider_artifact_name",
            "provider_sha256",
            "provider_size_bytes",
            "created_utc",
            "expires_utc",
            "downloaded_sha256_matches",
            "downloaded_size_matches",
        },
        label=f"provider_binding_{label}",
    )
    _non_empty_text(row.get("provider"), label=f"provider_binding_{label}_provider")
    _non_empty_text(
        row.get("provider_artifact_id"),
        label=f"provider_binding_{label}_artifact_id",
    )
    _non_empty_text(
        row.get("provider_artifact_name"),
        label=f"provider_binding_{label}_artifact_name",
    )
    provider_sha = _canonical_sha256(
        row.get("provider_sha256"),
        label=f"provider_binding_{label}_sha256",
    )
    provider_size = row.get("provider_size_bytes")
    if (
        not isinstance(provider_size, int)
        or isinstance(provider_size, bool)
        or provider_size < 0
    ):
        raise BundleError(f"provider_binding_{label}_size_invalid")
    if (
        provider_sha != artifact_sha256
        or provider_size != artifact_size
        or row.get("downloaded_sha256_matches") is not True
        or row.get("downloaded_size_matches") is not True
    ):
        raise BundleError(f"provider_binding_{label}_identity_mismatch")
    created = _parse_utc(
        row.get("created_utc"),
        label=f"provider_binding_{label}_created_utc",
    )
    expires = _parse_utc(
        row.get("expires_utc"),
        label=f"provider_binding_{label}_expires_utc",
    )
    if created >= expires:
        raise BundleError(f"provider_binding_{label}_retention_window_invalid")
    return True, True


def _validate_packet_provider_selection_bindings(
    artifacts: Mapping[str, Mapping[str, Any]],
    *,
    selection: Mapping[str, Mapping[str, Any]],
    carrier_root_prefix: str,
) -> None:
    carrier_prefix = carrier_root_prefix.rstrip("/") + "/"
    original_prefix = carrier_prefix + "original-github-artifacts/"
    provider_rows = {
        artifact_id: row
        for artifact_id, row in artifacts.items()
        if row.get("provider_binding") is not None
    }
    if len(provider_rows) != len(SOURCE_ARTIFACT_ROLES):
        raise BundleError(
            "packet_provider_artifact_count_mismatch: "
            f"expected={len(SOURCE_ARTIFACT_ROLES)} actual={len(provider_rows)}"
        )

    matched: set[str] = set()
    for key in sorted(SOURCE_ARTIFACT_ROLES):
        selected = selection.get(key)
        if not isinstance(selected, Mapping):
            raise BundleError(f"packet_provider_selection_missing: {key}")
        expected_member_path = original_prefix + str(
            selected.get("download_file_name")
        )
        candidates = [
            (artifact_id, row)
            for artifact_id, row in provider_rows.items()
            if row.get("container_artifact_id") is None
            and row.get("member_path") == expected_member_path
        ]
        if len(candidates) != 1:
            raise BundleError(
                "packet_provider_selection_member_resolution_failed: "
                f"key={key!r} member_path={expected_member_path!r} "
                f"matches={len(candidates)}"
            )
        artifact_id, row = candidates[0]
        if artifact_id in matched:
            raise BundleError(
                f"packet_provider_selection_artifact_reused: {artifact_id}"
            )
        matched.add(artifact_id)

        expected_row_identity = {
            "sha256": selected.get("expected_sha256"),
            "size_bytes": selected.get("expected_size_bytes"),
        }
        for field, expected in expected_row_identity.items():
            if row.get(field) != expected:
                raise BundleError(
                    "packet_provider_selected_artifact_identity_mismatch: "
                    f"key={key!r} field={field!r} "
                    f"expected={expected!r} actual={row.get(field)!r}"
                )

        binding = _require_object(
            row.get("provider_binding"),
            label=f"packet_provider_selection_binding_{key}",
        )
        expected_binding = {
            "created_utc": selected.get("created_at"),
            "downloaded_sha256_matches": True,
            "downloaded_size_matches": True,
            "expires_utc": selected.get("expires_at"),
            "provider": PROVIDER_NAME,
            "provider_artifact_id": str(selected.get("artifact_id")),
            "provider_artifact_name": selected.get("artifact_name"),
            "provider_sha256": selected.get("expected_sha256"),
            "provider_size_bytes": selected.get("expected_size_bytes"),
        }
        if binding != expected_binding:
            raise BundleError(
                "packet_provider_selection_binding_mismatch: "
                f"key={key!r} expected={expected_binding!r} actual={binding!r}"
            )

    if matched != set(provider_rows):
        raise BundleError(
            "packet_provider_selection_unmatched_artifacts: "
            f"{sorted(set(provider_rows) - matched)!r}"
        )


def _validate_packet_provider_bindings(
    packet_carrier: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, Any]],
) -> tuple[int, int]:
    if packet_carrier.get("provider_binding") is not None:
        _verify_packet_provider_binding(
            packet_carrier.get("provider_binding"),
            artifact_sha256=str(packet_carrier.get("sha256")),
            artifact_size=int(packet_carrier.get("size_bytes")),
            label="carrier",
        )
    total = 0
    bound = 0
    identities: set[tuple[str, str]] = set()
    for artifact_id, row in artifacts.items():
        binding = row.get("provider_binding")
        if binding is None:
            continue
        total += 1
        binding_row = _require_object(
            binding,
            label=f"provider_binding_{artifact_id}",
        )
        identity = (
            str(binding_row.get("provider")),
            str(binding_row.get("provider_artifact_id")),
        )
        if identity in identities:
            raise BundleError(
                f"packet_provider_artifact_identity_duplicate: {identity!r}"
            )
        identities.add(identity)
        _ok, fully_bound = _verify_packet_provider_binding(
            binding_row,
            artifact_sha256=str(row.get("sha256")),
            artifact_size=int(row.get("size_bytes")),
            label=artifact_id,
        )
        if fully_bound:
            bound += 1
    return total, bound


def _validate_packet_role_bindings(
    bindings_value: Any,
    *,
    artifacts: Mapping[str, Mapping[str, Any]],
) -> tuple[int, int, tuple[str, ...], tuple[str, ...]]:
    bindings = _require_object(bindings_value, label="packet_role_bindings")
    _require_exact_keys(
        bindings,
        set(CORE_SINGLETON_ROLE_BINDINGS) | set(LIST_ROLE_BINDINGS),
        label="packet_role_bindings",
    )
    total = 0
    resolved = 0
    missing: set[str] = set()
    unresolved: set[str] = set()

    for name, expected_role in CORE_SINGLETON_ROLE_BINDINGS.items():
        reference = bindings.get(name)
        expected_ids = sorted(
            artifact_id
            for artifact_id, row in artifacts.items()
            if row.get("role") == expected_role
        )
        if not isinstance(reference, str):
            missing.add(name)
            continue
        total += 1
        row = artifacts.get(reference)
        if row is None:
            unresolved.add(reference)
            continue
        if row.get("role") != expected_role:
            raise BundleError(
                f"packet_role_binding_semantic_mismatch: {name}: {reference}"
            )
        resolved += 1
        if expected_ids != [reference]:
            missing.add(name)

    for name, allowed_roles in LIST_ROLE_BINDINGS.items():
        references = _require_list(
            bindings.get(name),
            label=f"packet_role_binding_{name}",
        )
        if (
            not all(isinstance(value, str) and value for value in references)
            or references != sorted(references)
            or len(references) != len(set(references))
        ):
            raise BundleError(
                f"packet_role_binding_list_not_sorted_unique: {name}"
            )
        expected_ids = sorted(
            artifact_id
            for artifact_id, row in artifacts.items()
            if row.get("role") in allowed_roles
        )
        total += len(references)
        resolved_here: list[str] = []
        for reference in references:
            row = artifacts.get(reference)
            if row is None:
                unresolved.add(reference)
                continue
            if row.get("role") not in allowed_roles:
                raise BundleError(
                    f"packet_role_binding_semantic_mismatch: {name}: {reference}"
                )
            resolved += 1
            resolved_here.append(reference)
        if name == "candidate_records" and not references:
            missing.add(name)
        if sorted(resolved_here) != expected_ids:
            if expected_ids or name == "candidate_records":
                missing.add(name)

    for row in artifacts.values():
        parent = row.get("container_artifact_id")
        if isinstance(parent, str) and parent not in artifacts:
            unresolved.add(parent)
    return total, resolved, tuple(sorted(missing)), tuple(sorted(unresolved))


def _validate_packet(
    document: dict[str, Any],
    *,
    subject: SourceSubject,
    carrier_metadata: dict[str, Any],
    expectation: dict[str, Any],
    provider_revision: str,
    selection: Mapping[str, Mapping[str, Any]],
    carrier_directory_descriptor: int,
    carrier_name: str,
    max_total_uncompressed_bytes: int,
) -> PacketVerification:
    expected_top_level = {
        "analysis_boundary",
        "artifacts",
        "authority_boundary",
        "authority_sources",
        "carrier",
        "content_boundary",
        "coverage",
        "errors",
        "ok",
        "packet_identity",
        "packet_type",
        "producer",
        "record_status",
        "role_bindings",
        "schema_version",
        "subject",
    }
    _require_exact_keys(document, expected_top_level, label="subject_input_packet")
    if document.get("schema_version") != "pulsemech_compute_subject_input_packet_v0":
        raise BundleError("packet_schema_version_mismatch")
    if document.get("packet_type") != "pulsemech_compute_subject_input_packet":
        raise BundleError("packet_type_mismatch")
    if document.get("record_status") != "observed":
        raise BundleError("packet_record_status_not_observed")
    if document.get("ok") is not True or document.get("errors") != []:
        raise BundleError("packet_not_ok_or_errors_present")
    if document.get("analysis_boundary") != EXPECTED_PACKET_ANALYSIS:
        raise BundleError("packet_analysis_boundary_mismatch")
    if document.get("authority_boundary") != EXPECTED_PACKET_AUTHORITY:
        raise BundleError("packet_authority_boundary_mismatch")
    if document.get("content_boundary") != EXPECTED_PACKET_CONTENT:
        raise BundleError("packet_content_boundary_mismatch")
    if document.get("subject") != expectation.get("subject"):
        raise BundleError("packet_subject_expectation_mismatch")

    packet_carrier = _require_object(document.get("carrier"), label="packet_carrier")
    expected_packet_carrier = _expected_packet_carrier(carrier_metadata)
    if packet_carrier != expected_packet_carrier:
        raise BundleError(
            "packet_carrier_projection_mismatch: "
            f"expected={expected_packet_carrier!r} actual={packet_carrier!r}"
        )
    source_complete = _validate_packet_authority_sources(
        document.get("authority_sources"),
        expectation_sources=expectation.get("authority_sources"),
        subject=subject,
    )

    packet_identity = _require_object(
        document.get("packet_identity"),
        label="packet_identity",
    )
    if (
        packet_identity.get("packet_scope") != "current_run"
        or packet_identity.get("subject_run_key") != subject.source_run_key
        or packet_identity.get("carrier_id") != carrier_metadata.get("carrier_id")
        or packet_identity.get("packet_created_utc") != subject.source_updated_utc
        or packet_identity.get("canonicalization")
        != "json-sort-keys-utf8-newline"
    ):
        raise BundleError("packet_identity_mismatch")
    packet_id = _non_empty_text(packet_identity.get("packet_id"), label="packet_id")
    if not packet_id.startswith("subject-input:"):
        raise BundleError(f"packet_id_namespace_mismatch: {packet_id!r}")

    producer = _require_object(document.get("producer"), label="packet_producer")
    expected_producer = {
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": "PULSEmech compute subject-input packet producer",
        "producer_run_key": subject.source_run_key,
        "producer_source": "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py",
        "producer_source_revision": provider_revision,
        "producer_version": "0.1.0",
        "production_mode": "current_run_export",
    }
    for field, expected in expected_producer.items():
        if producer.get(field) != expected:
            raise BundleError(
                f"packet_producer_{field}_mismatch: "
                f"expected={expected!r} actual={producer.get(field)!r}"
            )
    packet_producer_sha256 = _canonical_sha256(
        producer.get("producer_source_sha256"),
        label="packet_producer_source_sha256",
    )
    trusted_components = _require_object(
        _require_object(
            expectation.get("trusted_control_plane"),
            label="packet_expectation_trusted_control_plane",
        ).get("components"),
        label="packet_expectation_control_plane_components",
    )
    wrapper_component = _require_object(
        trusted_components.get("subject_input_producer_wrapper"),
        label="packet_wrapper_component",
    )
    if packet_producer_sha256 != wrapper_component.get("sha256"):
        raise BundleError("packet_producer_component_digest_mismatch")
    _non_empty_text(
        producer.get("ci_workflow_or_job_identity"),
        label="packet_producer_ci_identity",
    )

    artifacts = _validate_packet_artifact_rows(
        document.get("artifacts"),
        packet_carrier=packet_carrier,
        selection=selection,
    )
    provider_total, provider_bound = _validate_packet_provider_bindings(
        packet_carrier,
        artifacts,
    )
    _validate_packet_provider_selection_bindings(
        artifacts,
        selection=selection,
        carrier_root_prefix=str(packet_carrier.get("root_prefix")),
    )
    role_total, role_resolved, missing_roles, unresolved_ids = (
        _validate_packet_role_bindings(
            document.get("role_bindings"),
            artifacts=artifacts,
        )
    )

    with OpenedInput.open_at(
        carrier_directory_descriptor,
        carrier_name,
        label="packet_carrier_bytes",
        max_bytes=int(carrier_metadata["size_bytes"]),
        require_read_only=True,
        require_single_link=True,
    ) as carrier_input:
        observed_sha, observed_size = carrier_input.hash_once(
            label="packet_carrier_bytes"
        )
        if (
            observed_sha != packet_carrier.get("sha256")
            or observed_size != packet_carrier.get("size_bytes")
        ):
            raise BundleError("packet_carrier_byte_identity_mismatch")
        with PacketArchiveResolver(
            outer_input=carrier_input,
            artifacts=artifacts,
            max_total_retained_bytes=max_total_uncompressed_bytes,
        ) as resolver:
            resolver.resolve_all()
            carrier_input.verify_unchanged(label="packet_carrier_bytes")
            retained = dict(resolver.retained)
            archive_members = dict(resolver.archive_members)

    graph_complete = len(artifacts) > 0
    role_complete = not missing_roles and not unresolved_ids
    derived_coverage = {
        "artifact_graph_complete": graph_complete,
        "artifacts_total": len(artifacts),
        "carrier_binding_complete": True,
        "coverage_status": (
            "complete"
            if source_complete and graph_complete and role_complete
            else "partial"
        ),
        "missing_roles": list(missing_roles),
        "provider_artifacts_bound": provider_bound,
        "provider_artifacts_total": provider_total,
        "role_bindings_complete": role_complete,
        "role_bindings_resolved": role_resolved,
        "role_bindings_total": role_total,
        "source_bindings_complete": source_complete,
        "unresolved_artifact_ids": list(unresolved_ids),
    }
    coverage = _require_object(document.get("coverage"), label="packet_coverage")
    _require_exact_keys(coverage, PACKET_COVERAGE_KEYS, label="packet_coverage")
    if coverage != derived_coverage:
        raise BundleError(
            "packet_coverage_not_derived_from_verified_graph: "
            f"expected={derived_coverage!r} actual={coverage!r}"
        )
    if derived_coverage["coverage_status"] != "complete":
        raise BundleError("packet_derived_coverage_not_complete")

    return PacketVerification(
        artifact_index=artifacts,
        retained_artifact_bytes=retained,
        archive_members=archive_members,
        role_bindings=_require_object(
            document.get("role_bindings"),
            label="packet_role_bindings_result",
        ),
        artifacts_total=len(artifacts),
        provider_artifacts_total=provider_total,
        provider_artifacts_bound=provider_bound,
        role_bindings_total=role_total,
        role_bindings_resolved=role_resolved,
        missing_roles=missing_roles,
        unresolved_artifact_ids=unresolved_ids,
    )


def _parse_sha256sums(payload: bytes) -> dict[str, str]:
    if len(payload) > MAX_SHA256SUMS_BYTES:
        raise BundleError("preservation_sha256sums_too_large")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BundleError(
            f"preservation_sha256sums_invalid_utf8: {exc}",
            exit_kind="archive_boundary_error",
        ) from exc
    result: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\x00\r\n]+)", line)
        if match is None:
            raise BundleError(
                f"preservation_sha256sums_line_invalid: {line_number}: {line!r}"
            )
        digest, path = match.groups()
        canonical = _canonical_archive_member(
            path,
            label=f"preservation_sha256sums_path_{line_number}",
        )
        if canonical in result:
            raise BundleError(f"preservation_sha256sums_duplicate_path: {canonical}")
        result[canonical] = digest
    if not result or not payload.endswith(b"\n"):
        raise BundleError("preservation_sha256sums_empty_or_missing_final_lf")
    return result


def _hash_inner_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    label: str,
) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    try:
        with archive.open(info, "r") as stream:
            while True:
                chunk = stream.read(HASH_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > info.file_size:
                    raise BundleError(f"{label}_expanded_past_declared_size")
                digest.update(chunk)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise BundleError(
            f"{label}_read_failed: {exc}",
            exit_kind="archive_boundary_error",
        ) from exc
    if total != info.file_size:
        raise BundleError(
            f"{label}_size_mismatch: expected={info.file_size} actual={total}"
        )
    return digest.hexdigest(), total


def _packet_bound_artifact_id(
    verification: PacketVerification,
    binding_name: str,
) -> str:
    reference = verification.role_bindings.get(binding_name)
    if not isinstance(reference, str):
        raise BundleError(f"packet_required_role_binding_missing: {binding_name}")
    if reference not in verification.artifact_index:
        raise BundleError(
            f"packet_required_role_binding_unresolved: {binding_name}: {reference}"
        )
    return reference


def _packet_bound_json(
    verification: PacketVerification,
    binding_name: str,
) -> dict[str, Any]:
    artifact_id = _packet_bound_artifact_id(verification, binding_name)
    payload = verification.retained_artifact_bytes.get(artifact_id)
    if payload is None:
        raise BundleError(
            f"packet_required_role_bytes_not_retained: {binding_name}: {artifact_id}"
        )
    return parse_json_bytes(
        payload,
        label=f"packet_bound_{binding_name}",
        canonical_required=False,
    )


def _validate_positive_report_count(value: Any, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BundleError(f"{label}_invalid: {value!r}")
    return value


def _derive_preservation_local_verification(
    verification: PacketVerification,
) -> dict[str, Any]:
    complete_package_id = _packet_bound_artifact_id(
        verification,
        "complete_package",
    )
    inventory_id = _packet_bound_artifact_id(
        verification,
        "package_inventory",
    )
    inventory = _packet_bound_json(verification, "package_inventory")
    rows = _require_list(inventory.get("files"), label="package_inventory_files")
    if not rows:
        raise BundleError("package_inventory_files_empty")

    child_rows = {
        str(row.get("member_path")): row
        for row in verification.artifact_index.values()
        if row.get("container_artifact_id") == complete_package_id
    }
    inventory_artifact = verification.artifact_index[inventory_id]
    inventory_member_path = str(inventory_artifact.get("member_path"))
    expected_inventory_paths = set(child_rows) - {inventory_member_path}
    observed_inventory_paths: set[str] = set()
    for index, item in enumerate(rows):
        row = _require_object(item, label=f"package_inventory_file_{index}")
        member_path = _canonical_archive_member(
            row.get("path"),
            label=f"package_inventory_path_{index}",
        )
        if member_path in observed_inventory_paths:
            raise BundleError(f"package_inventory_duplicate_path: {member_path}")
        observed_inventory_paths.add(member_path)
        artifact = child_rows.get(member_path)
        if artifact is None:
            raise BundleError(f"package_inventory_artifact_unresolved: {member_path}")
        if (
            row.get("sha256") != artifact.get("sha256")
            or row.get("size_bytes") != artifact.get("size_bytes")
        ):
            raise BundleError(
                f"package_inventory_artifact_identity_mismatch: {member_path}"
            )
    if observed_inventory_paths != expected_inventory_paths:
        raise BundleError(
            "package_inventory_closure_mismatch: "
            f"missing={sorted(expected_inventory_paths - observed_inventory_paths)!r} "
            f"unexpected={sorted(observed_inventory_paths - expected_inventory_paths)!r}"
        )

    actual_complete_members = set(
        verification.archive_members.get(complete_package_id, ())
    )
    expected_complete_members = set(child_rows)
    if actual_complete_members != expected_complete_members:
        raise BundleError(
            "complete_package_packet_graph_member_closure_mismatch"
        )

    completeness = _packet_bound_json(
        verification,
        "package_completeness_report",
    )
    completeness_summary = _require_object(
        completeness.get("summary"),
        label="package_completeness_summary",
    )
    completeness_errors = completeness.get("errors")
    if completeness_errors != []:
        raise BundleError(
            f"package_completeness_errors_present: {completeness_errors!r}"
        )
    completeness_total = _validate_positive_report_count(
        completeness_summary.get("checks_total"),
        label="package_completeness_checks_total",
    )
    completeness_failed = completeness_summary.get("checks_failed")
    if (
        completeness.get("status") != "complete"
        or completeness.get("ok") is not True
        or completeness_failed != 0
    ):
        raise BundleError(
            "package_completeness_report_failed: "
            f"status={completeness.get('status')!r} "
            f"ok={completeness.get('ok')!r} "
            f"checks_failed={completeness_failed!r}"
        )
    checks_passed = completeness_summary.get("checks_passed")
    if checks_passed is not None and checks_passed != completeness_total:
        raise BundleError("package_completeness_checks_passed_mismatch")

    independent = _packet_bound_json(
        verification,
        "independent_verification_report",
    )
    independent_summary = _require_object(
        independent.get("summary"),
        label="independent_verification_summary",
    )
    independent_errors = independent.get("errors")
    if independent_errors != []:
        raise BundleError(
            f"independent_verification_errors_present: {independent_errors!r}"
        )
    independent_total = _validate_positive_report_count(
        independent_summary.get("checks_total"),
        label="independent_verification_checks_total",
    )
    independent_failed = independent_summary.get("checks_failed")
    if independent_failed is not None and independent_failed != 0:
        raise BundleError(
            f"independent_verification_checks_failed: {independent_failed!r}"
        )
    if (
        independent.get("status") != "verified"
        or independent.get("verified") is not True
    ):
        raise BundleError(
            "independent_verification_report_failed: "
            f"status={independent.get('status')!r} "
            f"verified={independent.get('verified')!r}"
        )
    independent_passed = independent_summary.get("checks_passed")
    if independent_passed is not None and independent_passed != independent_total:
        raise BundleError("independent_verification_checks_passed_mismatch")

    return {
        "all_outer_artifact_digests_match_github": True,
        "all_outer_artifact_sizes_match_github": True,
        "complete_package_inventory_entries": len(rows),
        "complete_package_inventory_errors": [],
        "complete_package_unlisted_members_excluding_inventory": [],
        "complete_package_zip_members": len(actual_complete_members),
        "independent_verification_checks_total": independent_total,
        "independent_verification_errors": [],
        "independent_verification_status": "verified",
        "independent_verification_verified": True,
        "structural_completeness_checks_failed": 0,
        "structural_completeness_checks_total": completeness_total,
        "structural_completeness_ok": True,
        "structural_completeness_status": "complete",
    }


def _validate_preservation_manifest(
    manifest: dict[str, Any],
    *,
    subject: SourceSubject,
    selection: dict[str, dict[str, Any]],
    packet_verification: PacketVerification,
) -> dict[str, dict[str, Any]]:
    required_exact = {
        "active_policy_sets": ["required", "release_required"],
        "authority_boundary": EXPECTED_PRESERVATION_AUTHORITY,
        "created_utc": subject.source_updated_utc,
        "llamaguard_evidence_mode": "hosted_full_runtime",
        "primary_gate_result": "allow",
        "release_decision": "PROD-PASS",
        "repository": subject.repository,
        "run_mode": "prod",
        "schema_id": "pulse_ci_release_grade_artifact_preservation_manifest_v0",
        "schema_version": "0.1.0",
        "source_commit": subject.subject_revision,
        "source_ref": SOURCE_REF,
        "strict_external_evidence": True,
        "workflow": SOURCE_WORKFLOW_NAME,
        "workflow_run_attempt": subject.source_run_attempt,
        "workflow_run_id": subject.source_run_id,
        "workflow_run_number": subject.source_run_number,
    }
    for field, expected in required_exact.items():
        if manifest.get(field) != expected:
            raise BundleError(
                f"preservation_manifest_{field}_mismatch: "
                f"expected={expected!r} actual={manifest.get(field)!r}"
            )

    derived_local_verification = _derive_preservation_local_verification(
        packet_verification
    )
    local_verification = _require_object(
        manifest.get("local_verification"),
        label="preservation_manifest_local_verification",
    )
    if local_verification != derived_local_verification:
        raise BundleError(
            "preservation_manifest_local_verification_mismatch: "
            f"expected={derived_local_verification!r} "
            f"actual={local_verification!r}"
        )

    retention = _require_object(
        manifest.get("retention_risk"),
        label="preservation_manifest_retention_risk",
    )
    _require_exact_keys(
        retention,
        {
            "earliest_expiry_utc",
            "original_github_artifacts_expire",
            "reason_for_preservation",
        },
        label="preservation_manifest_retention_risk",
    )
    expected_earliest_expiry = min(
        selection[key]["expires_at"] for key in SOURCE_ARTIFACT_ROLES
    )
    if (
        retention.get("earliest_expiry_utc") != expected_earliest_expiry
        or retention.get("original_github_artifacts_expire") is not True
    ):
        raise BundleError("preservation_manifest_retention_binding_mismatch")
    _non_empty_text(
        retention.get("reason_for_preservation"),
        label="preservation_manifest_retention_reason",
    )

    rows = _require_list(
        manifest.get("github_artifacts"),
        label="preservation_github_artifacts",
    )
    if len(rows) != 3:
        raise BundleError("preservation_github_artifact_count_invalid")
    by_file: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(rows):
        row = _require_object(item, label=f"preservation_artifact_{index}")
        _require_exact_keys(
            row,
            {
                "artifact_id",
                "artifact_name",
                "created_at",
                "downloaded_sha256",
                "downloaded_size_bytes",
                "expires_at",
                "file_name",
                "github_digest_match",
                "github_sha256",
                "github_size_match",
                "role",
                "size_bytes",
            },
            label=f"preservation_artifact_{index}",
        )
        file_name = _canonical_flat_member(
            row.get("file_name"),
            label=f"preservation_artifact_file_{index}",
        )
        if file_name in by_file:
            raise BundleError(f"preservation_artifact_duplicate_file: {file_name}")
        by_file[file_name] = row
    if list(by_file) != sorted(by_file):
        raise BundleError("preservation_artifact_rows_not_sorted_by_file_name")

    expected_files = {
        selection[key]["download_file_name"]: selection[key]
        for key in SOURCE_ARTIFACT_ROLES
    }
    if set(by_file) != set(expected_files):
        raise BundleError("preservation_artifact_file_set_mismatch")
    for file_name, selected in expected_files.items():
        row = by_file[file_name]
        expected = {
            "artifact_id": selected["artifact_id"],
            "artifact_name": selected["artifact_name"],
            "created_at": selected["created_at"],
            "downloaded_sha256": selected["expected_sha256"],
            "downloaded_size_bytes": selected["expected_size_bytes"],
            "expires_at": selected["expires_at"],
            "file_name": selected["download_file_name"],
            "github_digest_match": True,
            "github_sha256": selected["expected_sha256"],
            "github_size_match": True,
            "role": selected["role"],
            "size_bytes": selected["expected_size_bytes"],
        }
        if row != expected:
            raise BundleError(
                f"preservation_artifact_binding_mismatch: {file_name}"
            )
    return by_file


def _validate_inner_carrier(
    carrier_directory_descriptor: int,
    carrier_name: str,
    *,
    subject: SourceSubject,
    carrier_metadata: dict[str, Any],
    selection: dict[str, dict[str, Any]],
    packet_verification: PacketVerification,
) -> dict[str, Any]:
    root_prefix = carrier_metadata["root_prefix"]
    original_prefix = root_prefix + "original-github-artifacts/"
    expected_provider_names = {
        selection[key]["download_file_name"] for key in SOURCE_ARTIFACT_ROLES
    }
    expected_members = {
        root_prefix + "PRESERVATION_MANIFEST_v0.json",
        root_prefix + "README.md",
        root_prefix + "SHA256SUMS",
        *{original_prefix + name for name in expected_provider_names},
    }

    with OpenedInput.open_at(
        carrier_directory_descriptor,
        carrier_name,
        label="materialized_carrier",
        max_bytes=_positive_int(
            carrier_metadata.get("size_bytes"),
            label="carrier_metadata_size_bytes",
        ),
        require_read_only=True,
        require_single_link=True,
    ) as opened:
        observed_sha, observed_size = opened.hash_once(label="materialized_carrier")
        if observed_sha != carrier_metadata["sha256"]:
            raise BundleError("materialized_carrier_digest_mismatch")
        if observed_size != carrier_metadata["size_bytes"]:
            raise BundleError("materialized_carrier_size_mismatch")
        try:
            with opened.duplicate_binary_reader() as reader:
                with zipfile.ZipFile(reader, "r") as archive:
                    infos = _zip_info_map(
                        archive,
                        label="current_run_carrier",
                        flat=False,
                        max_members=MAX_INNER_MEMBERS,
                        max_member_bytes=MAX_INNER_MEMBER_BYTES,
                        max_total_uncompressed_bytes=(
                            MAX_INNER_TOTAL_UNCOMPRESSED_BYTES
                        ),
                    )
                    if set(infos) != expected_members:
                        raise BundleError(
                            "current_run_carrier_member_set_mismatch: "
                            f"missing={sorted(expected_members - set(infos))!r} "
                            f"unexpected={sorted(set(infos) - expected_members)!r}"
                        )
                    manifest_name = root_prefix + "PRESERVATION_MANIFEST_v0.json"
                    readme_name = root_prefix + "README.md"
                    sums_name = root_prefix + "SHA256SUMS"
                    manifest_bytes = _read_zip_member_bytes(
                        archive,
                        infos[manifest_name],
                        label="preservation_manifest",
                        max_bytes=MAX_PRESERVATION_MANIFEST_BYTES,
                    )
                    readme_bytes = _read_zip_member_bytes(
                        archive,
                        infos[readme_name],
                        label="preservation_readme",
                        max_bytes=MAX_PRESERVATION_README_BYTES,
                    )
                    sums_bytes = _read_zip_member_bytes(
                        archive,
                        infos[sums_name],
                        label="preservation_sha256sums",
                        max_bytes=MAX_SHA256SUMS_BYTES,
                    )
                    preservation_manifest = parse_json_bytes(
                        manifest_bytes,
                        label="preservation_manifest",
                        canonical_required=True,
                    )
                    _validate_preservation_manifest(
                        preservation_manifest,
                        subject=subject,
                        selection=selection,
                        packet_verification=packet_verification,
                    )
                    sums = _parse_sha256sums(sums_bytes)
                    expected_sum_paths = {
                        "PRESERVATION_MANIFEST_v0.json",
                        "README.md",
                        *{
                            "original-github-artifacts/" + name
                            for name in expected_provider_names
                        },
                    }
                    if set(sums) != expected_sum_paths:
                        raise BundleError("preservation_sha256sums_path_set_mismatch")
                    if sums["PRESERVATION_MANIFEST_v0.json"] != sha256_bytes(
                        manifest_bytes
                    ):
                        raise BundleError("preservation_manifest_checksum_mismatch")
                    if sums["README.md"] != sha256_bytes(readme_bytes):
                        raise BundleError("preservation_readme_checksum_mismatch")

                    provider_bindings: list[dict[str, Any]] = []
                    for key in sorted(SOURCE_ARTIFACT_ROLES):
                        selected = selection[key]
                        file_name = selected["download_file_name"]
                        member_name = original_prefix + file_name
                        digest, size = _hash_inner_member(
                            archive,
                            infos[member_name],
                            label=f"preserved_provider_artifact_{key}",
                        )
                        if digest != selected["expected_sha256"]:
                            raise BundleError(
                                f"preserved_provider_artifact_{key}_digest_mismatch"
                            )
                        if size != selected["expected_size_bytes"]:
                            raise BundleError(
                                f"preserved_provider_artifact_{key}_size_mismatch"
                            )
                        if sums["original-github-artifacts/" + file_name] != digest:
                            raise BundleError(
                                f"preserved_provider_artifact_{key}_checksum_mismatch"
                            )
                        provider_bindings.append(
                            {
                                "artifact_id": selected["artifact_id"],
                                "artifact_name": selected["artifact_name"],
                                "role": selected["role"],
                                "sha256": digest,
                                "size_bytes": size,
                            }
                        )
        except zipfile.BadZipFile as exc:
            raise BundleError(
                f"current_run_carrier_invalid_zip: {exc}",
                exit_kind="archive_boundary_error",
            ) from exc
        opened.verify_unchanged(label="materialized_carrier")
    return {
        "member_count": len(expected_members),
        "packet_artifact_graph_verified": True,
        "packet_artifacts_total": packet_verification.artifacts_total,
        "packet_provider_artifacts_bound": (
            packet_verification.provider_artifacts_bound
        ),
        "packet_provider_artifacts_total": (
            packet_verification.provider_artifacts_total
        ),
        "packet_role_bindings_resolved": (
            packet_verification.role_bindings_resolved
        ),
        "packet_role_bindings_total": packet_verification.role_bindings_total,
        "preservation_manifest_sha256": sha256_bytes(manifest_bytes),
        "preservation_readme_sha256": sha256_bytes(readme_bytes),
        "preservation_sha256sums_sha256": sha256_bytes(sums_bytes),
        "provider_artifacts": provider_bindings,
        "provider_artifacts_bound": len(provider_bindings),
        "provider_artifacts_total": 3,
        "root_prefix": root_prefix,
        "source_package_semantics_verified": True,
    }


def _reject_unsafe_output_directory(
    output_directory: Path,
    *,
    artifact_path: Path,
    control_plane_root: Path,
    source_path: Path,
) -> Path:
    candidate = _normalized_absolute_path(output_directory)
    if candidate.name in {"", ".", ".."}:
        raise BundleError(
            f"output_directory_name_invalid: {candidate}",
            exit_kind="output_boundary_error",
        )
    if candidate.name.casefold() in PROTECTED_OUTPUT_NAMES_CASEFOLDED:
        raise BundleError(
            f"output_directory_protected_name_rejected: {candidate.name}",
            exit_kind="output_boundary_error",
        )
    if candidate.exists() or candidate.is_symlink():
        raise BundleError(
            f"output_directory_already_exists: {candidate}",
            exit_kind="output_boundary_error",
        )
    parent = _validated_directory_root(candidate.parent, label="output_parent")
    candidate = parent / candidate.name
    for protected in (artifact_path, control_plane_root, source_path):
        if _paths_overlap(candidate, protected):
            raise BundleError(
                f"output_directory_overlaps_protected_input: {protected}",
                exit_kind="output_boundary_error",
            )
    return candidate


def _verify_materialized_output(
    output: StagedOutputDirectory,
    *,
    expected_files: Mapping[str, tuple[str, int]],
    report_bytes: bytes,
) -> None:
    output.verify_name_binding(temporary=not output.published)
    actual_names = output.list_names()
    expected_names = set(expected_files) | {INTAKE_REPORT_NAME}
    if actual_names != expected_names:
        raise BundleError(
            "materialized_output_closure_failed: "
            f"missing={sorted(expected_names - actual_names)!r} "
            f"unexpected={sorted(actual_names - expected_names)!r}",
            exit_kind="output_boundary_error",
        )
    for name, (expected_sha, expected_size) in expected_files.items():
        with OpenedInput.open_at(
            output.directory_descriptor,
            name,
            label=f"published_output_{name}",
            max_bytes=max(expected_size, 1),
            require_read_only=True,
            require_single_link=True,
        ) as opened:
            observed_sha, observed_size = opened.hash_once(
                label=f"published_output_{name}"
            )
        if observed_sha != expected_sha or observed_size != expected_size:
            raise BundleError(
                f"published_output_identity_mismatch: {name}",
                exit_kind="output_boundary_error",
            )
    with OpenedInput.open_at(
        output.directory_descriptor,
        INTAKE_REPORT_NAME,
        label="published_intake_report",
        max_bytes=MAX_JSON_BYTES,
        require_read_only=True,
        require_single_link=True,
    ) as report:
        observed = report.read_bytes(
            label="published_intake_report",
            max_bytes=MAX_JSON_BYTES,
        )
    if observed != report_bytes:
        raise BundleError(
            "published_intake_report_bytes_mismatch",
            exit_kind="output_boundary_error",
        )
    output.verify_name_binding(temporary=not output.published)


def _provider_binding(provider: ProviderArtifact) -> dict[str, Any]:
    return {
        "artifact": {
            "created_utc": provider.artifact_created_utc,
            "expired": False,
            "expires_utc": provider.artifact_expires_utc,
            "id": provider.artifact_id,
            "name": provider.artifact_name,
            "sha256": provider.artifact_sha256,
            "size_bytes": provider.artifact_size_bytes,
        },
        "provider": PROVIDER_NAME,
        "repository": provider.repository,
        "workflow_run": {
            "attempt": provider.workflow_run_attempt,
            "conclusion": "success",
            "event": "workflow_dispatch",
            "head_branch": "main",
            "id": provider.workflow_run_id,
            "number": provider.workflow_run_number,
            "revision": provider.workflow_revision,
            "run_key": provider.workflow_run_key,
            "status": "completed",
            "updated_utc": provider.workflow_updated_utc,
            "workflow_name": provider.workflow_name,
            "workflow_path": provider.workflow_path,
        },
    }


def _producer_record(
    *,
    source_binding: SourceBinding,
    control_plane_revision: str,
    producer_run_key: str,
    ci_workflow_or_job_identity: str,
) -> dict[str, Any]:
    return {
        "ci_workflow_or_job_identity": ci_workflow_or_job_identity,
        "producer_id": PRODUCER_ID,
        "producer_name": PRODUCER_NAME,
        "producer_run_key": producer_run_key,
        "producer_source": PRODUCER_SOURCE_PATH,
        "producer_source_revision": control_plane_revision,
        "producer_source_sha256": source_binding.source_sha256,
        "producer_version": TOOL_VERSION,
        "production_mode": PRODUCTION_MODE,
    }


def _make_report(
    *,
    provider: ProviderArtifact,
    subject: SourceSubject,
    producer: dict[str, Any],
    files: Sequence[MaterializedFile],
    carrier_name: str,
    manifest_sha256: str,
    manifest_size: int,
    carrier_sha256: str,
    carrier_size: int,
    expectation_sha256: str,
    packet_sha256: str,
    inner_verification: dict[str, Any],
) -> dict[str, Any]:
    sorted_files = sorted(files, key=lambda row: row.path)
    return {
        "authority_boundary": dict(CLOSED_AUTHORITY_BOUNDARY),
        "bundle_identity": {
            "candidate_manifest_sha256": manifest_sha256,
            "candidate_manifest_size_bytes": manifest_size,
            "carrier_name": carrier_name,
            "carrier_sha256": carrier_sha256,
            "carrier_size_bytes": carrier_size,
            "expectation_sha256": expectation_sha256,
            "packet_sha256": packet_sha256,
            "provider_artifact_sha256": provider.artifact_sha256,
            "provider_artifact_size_bytes": provider.artifact_size_bytes,
            "provider_workflow_revision": provider.workflow_revision,
            "source_run_attempt": subject.source_run_attempt,
            "source_run_id": subject.source_run_id,
            "subject_revision": subject.subject_revision,
        },
        "content_boundary": dict(CLOSED_CONTENT_BOUNDARY),
        "document_type": DOCUMENT_TYPE,
        "errors": [],
        "files": [
            {
                "path": row.path,
                "role": row.role,
                "sha256": row.sha256,
                "size_bytes": row.size_bytes,
            }
            for row in sorted_files
        ],
        "inner_carrier_verification": inner_verification,
        "ok": True,
        "output_layout": {
            "intake_report_path": INTAKE_REPORT_NAME,
            "verified_candidate_files": [row.path for row in sorted_files],
        },
        "producer": producer,
        "provider_binding": _provider_binding(provider),
        "record_status": "observed",
        "schema_version": SCHEMA_VERSION,
        "source_subject": {
            "release_candidate_id": subject.release_candidate_id,
            "repository": subject.repository,
            "source_run_attempt": subject.source_run_attempt,
            "source_run_id": subject.source_run_id,
            "source_run_key": subject.source_run_key,
            "source_run_number": subject.source_run_number,
            "source_updated_utc": subject.source_updated_utc,
            "subject_revision": subject.subject_revision,
            "workflow_name": SOURCE_WORKFLOW_NAME,
            "workflow_path": SOURCE_WORKFLOW_PATH,
        },
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
            "Bind one downloaded GitHub Actions artifact to the exact Step 3F "
            "provider run and artifact metadata, verify its checksum-closed "
            "current-run candidate bundle, materialize exact read-only member "
            "bytes for downstream artifact-observed analysis, and emit one "
            "canonical non-authoritative intake report."
        )
    )
    parser.add_argument("--artifact-envelope", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument(
        "--provider-workflow-name",
        required=True,
    )
    parser.add_argument(
        "--provider-workflow-path",
        required=True,
    )
    parser.add_argument(
        "--provider-workflow-run-id",
        required=True,
        type=_arg_positive_int,
    )
    parser.add_argument(
        "--provider-workflow-run-number",
        required=True,
        type=_arg_positive_int,
    )
    parser.add_argument(
        "--provider-workflow-run-attempt",
        required=True,
        type=_arg_positive_int,
    )
    parser.add_argument("--provider-workflow-event", required=True)
    parser.add_argument("--provider-workflow-head-branch", required=True)
    parser.add_argument("--provider-workflow-revision", required=True)
    parser.add_argument("--provider-workflow-status", required=True)
    parser.add_argument("--provider-workflow-conclusion", required=True)
    parser.add_argument("--provider-workflow-updated-utc", required=True)
    parser.add_argument(
        "--provider-artifact-id",
        required=True,
        type=_arg_positive_int,
    )
    parser.add_argument("--provider-artifact-name", required=True)
    parser.add_argument("--provider-artifact-created-utc", required=True)
    parser.add_argument("--provider-artifact-expires-utc", required=True)
    parser.add_argument(
        "--provider-artifact-expired",
        required=True,
        choices=("false", "true"),
    )
    parser.add_argument("--provider-artifact-sha256", required=True)
    parser.add_argument(
        "--provider-artifact-size-bytes",
        required=True,
        type=_arg_positive_int,
    )
    parser.add_argument("--producer-run-key", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument(
        "--control-plane-root",
        default=str(ROOT),
        help="Protected exact Step 3G control-plane checkout root.",
    )
    parser.add_argument(
        "--control-plane-revision",
        required=True,
        help="Exact lowercase SHA-40 revision containing this intake tool.",
    )
    parser.add_argument(
        "--trusted-git",
        help=(
            "Optional approved absolute Linux system Git executable. "
            "When omitted, the first available protected candidate is used."
        ),
    )
    parser.add_argument("--output-directory", required=True)
    parser.add_argument(
        "--max-envelope-bytes",
        type=_arg_positive_int,
        default=DEFAULT_MAX_ENVELOPE_BYTES,
    )
    parser.add_argument(
        "--max-member-bytes",
        type=_arg_positive_int,
        default=DEFAULT_MAX_MEMBER_BYTES,
    )
    parser.add_argument(
        "--max-total-uncompressed-bytes",
        type=_arg_positive_int,
        default=DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
    )
    return parser.parse_args()


def _build(args: argparse.Namespace) -> bytes:
    _require_supported_execution_platform()
    provider = _provider_artifact_from_args(args)
    producer_run_key = _non_empty_text(
        args.producer_run_key,
        label="producer_run_key",
    )
    ci_identity = _non_empty_text(
        args.ci_workflow_or_job_identity,
        label="ci_workflow_or_job_identity",
    )
    control_plane_revision = _canonical_sha40(
        args.control_plane_revision,
        label="control_plane_revision",
    )
    control_plane_root = _validated_directory_root(
        Path(args.control_plane_root),
        label="control_plane_root",
    )

    trusted_git = _select_trusted_git(args.trusted_git)
    _require_trusted_git_capability(trusted_git)
    _verify_git_repository(
        git_path=trusted_git,
        repository_root=control_plane_root,
        expected_revision=control_plane_revision,
    )
    source_binding = _verify_producer_source(
        git_path=trusted_git,
        control_plane_root=control_plane_root,
        control_plane_revision=control_plane_revision,
    )

    artifact_path = _normalized_absolute_path(Path(args.artifact_envelope))
    output_directory = _reject_unsafe_output_directory(
        Path(args.output_directory),
        artifact_path=artifact_path,
        control_plane_root=control_plane_root,
        source_path=source_binding.source_path,
    )

    output = StagedOutputDirectory.create(output_directory)
    try:
        with OpenedInput.open(
            artifact_path,
            label="provider_artifact_envelope",
            max_bytes=args.max_envelope_bytes,
            require_read_only=True,
            require_single_link=True,
        ) as envelope:
            if envelope.identity.size != provider.artifact_size_bytes:
                raise BundleError(
                    "provider_artifact_declared_size_mismatch: "
                    f"expected={provider.artifact_size_bytes} "
                    f"actual={envelope.identity.size}",
                    exit_kind="provider_binding_error",
                )
            envelope_sha256, envelope_size = envelope.hash_once(
                label="provider_artifact_envelope"
            )
            if envelope_sha256 != provider.artifact_sha256:
                raise BundleError(
                    "provider_artifact_declared_digest_mismatch: "
                    f"expected={provider.artifact_sha256} actual={envelope_sha256}",
                    exit_kind="provider_binding_error",
                )

            try:
                with envelope.duplicate_binary_reader() as reader:
                    with zipfile.ZipFile(reader, "r") as archive:
                        infos = _zip_info_map(
                            archive,
                            label="provider_candidate_envelope",
                            flat=True,
                            max_members=MAX_OUTER_MEMBERS,
                            max_member_bytes=args.max_member_bytes,
                            max_total_uncompressed_bytes=(
                                args.max_total_uncompressed_bytes
                            ),
                        )
                        if CANDIDATE_MANIFEST_NAME not in infos:
                            raise BundleError(
                                "provider_candidate_manifest_missing",
                                exit_kind="archive_boundary_error",
                            )
                        manifest_bytes = _read_zip_member_bytes(
                            archive,
                            infos[CANDIDATE_MANIFEST_NAME],
                            label="candidate_manifest",
                            max_bytes=MAX_JSON_BYTES,
                        )
                        manifest = parse_json_bytes(
                            manifest_bytes,
                            label="candidate_manifest",
                            canonical_required=True,
                        )
                        declared, carrier_name = _validate_candidate_manifest(
                            manifest,
                            provider=provider,
                            outer_member_names=set(infos),
                        )

                        retained_json: dict[str, bytes] = {}
                        materialized: list[MaterializedFile] = []
                        expected_output_identities: dict[str, tuple[str, int]] = {}
                        for name in sorted(infos):
                            retain = name.endswith(".json")
                            digest, size, payload = _copy_zip_member_to_output(
                                archive,
                                infos[name],
                                output=output,
                                output_name=name,
                                label=f"candidate_member_{name}",
                                retain_bytes=retain,
                                max_retained_bytes=MAX_JSON_BYTES,
                            )
                            if name == CANDIDATE_MANIFEST_NAME:
                                expected_digest = sha256_bytes(manifest_bytes)
                                expected_size = len(manifest_bytes)
                            else:
                                row = declared[name]
                                expected_digest = row["sha256"]
                                expected_size = row["size_bytes"]
                            if digest != expected_digest or size != expected_size:
                                raise BundleError(
                                    f"candidate_member_identity_mismatch: {name}"
                                )
                            role = CANDIDATE_FILE_ROLES.get(name)
                            if role is None:
                                role = "finalized_current_run_carrier"
                            materialized.append(
                                MaterializedFile(
                                    path=name,
                                    role=role,
                                    sha256=digest,
                                    size_bytes=size,
                                )
                            )
                            expected_output_identities[name] = (digest, size)
                            if retain:
                                if payload is None:
                                    raise BundleError(
                                        f"candidate_json_member_not_retained: {name}"
                                    )
                                retained_json[name] = payload

            except zipfile.BadZipFile as exc:
                raise BundleError(
                    f"provider_candidate_envelope_invalid_zip: {exc}",
                    exit_kind="archive_boundary_error",
                ) from exc

            envelope.verify_unchanged(label="provider_artifact_envelope")
            second_sha, second_size = envelope.hash_once(
                label="provider_artifact_envelope_reverification"
            )
            if second_sha != envelope_sha256 or second_size != envelope_size:
                raise BundleError(
                    "provider_artifact_envelope_changed_during_intake",
                    exit_kind="provider_binding_error",
                )

            source_resolution = parse_json_bytes(
                retained_json[SOURCE_RESOLUTION_NAME],
                label="source_resolution",
                canonical_required=True,
            )
            subject = _validate_source_resolution(
                source_resolution,
                provider=provider,
            )
            if manifest.get("subject_revision") != subject.subject_revision:
                raise BundleError("candidate_manifest_subject_revision_mismatch")

            source_selection = parse_json_bytes(
                retained_json[SOURCE_SELECTION_NAME],
                label="source_selection",
                canonical_required=True,
            )
            selection = _validate_source_selection(
                source_selection,
                subject=subject,
            )

            carrier_metadata = parse_json_bytes(
                retained_json[CARRIER_METADATA_NAME],
                label="carrier_metadata",
                canonical_required=True,
            )
            carrier_row = declared[carrier_name]
            _validate_carrier_metadata(
                carrier_metadata,
                subject=subject,
                provider_revision=provider.workflow_revision,
                carrier_name=carrier_name,
                carrier_sha256=carrier_row["sha256"],
                carrier_size=carrier_row["size_bytes"],
            )

            expectation = parse_json_bytes(
                retained_json[EXPECTATION_NAME],
                label="expectation",
                canonical_required=True,
            )
            _validate_expectation(
                expectation,
                subject=subject,
                carrier_metadata=carrier_metadata,
                provider_revision=provider.workflow_revision,
                selection=selection,
            )

            packet = parse_json_bytes(
                retained_json[PACKET_NAME],
                label="subject_input_packet",
                canonical_required=True,
            )
            packet_verification = _validate_packet(
                packet,
                subject=subject,
                carrier_metadata=carrier_metadata,
                expectation=expectation,
                provider_revision=provider.workflow_revision,
                selection=selection,
                carrier_directory_descriptor=output.directory_descriptor,
                carrier_name=carrier_name,
                max_total_uncompressed_bytes=(
                    args.max_total_uncompressed_bytes
                ),
            )

            inner_verification = _validate_inner_carrier(
                output.directory_descriptor,
                carrier_name,
                subject=subject,
                carrier_metadata=carrier_metadata,
                selection=selection,
                packet_verification=packet_verification,
            )

            producer = _producer_record(
                source_binding=source_binding,
                control_plane_revision=control_plane_revision,
                producer_run_key=producer_run_key,
                ci_workflow_or_job_identity=ci_identity,
            )
            report = _make_report(
                provider=provider,
                subject=subject,
                producer=producer,
                files=materialized,
                carrier_name=carrier_name,
                manifest_sha256=sha256_bytes(manifest_bytes),
                manifest_size=len(manifest_bytes),
                carrier_sha256=carrier_row["sha256"],
                carrier_size=carrier_row["size_bytes"],
                expectation_sha256=declared[EXPECTATION_NAME]["sha256"],
                packet_sha256=declared[PACKET_NAME]["sha256"],
                inner_verification=inner_verification,
            )
            rendered = render_json(report)
            report_descriptor = output.create_file(INTAKE_REPORT_NAME)
            try:
                _write_all(report_descriptor, rendered)
                os.fsync(report_descriptor)
                os.fchmod(report_descriptor, 0o444)
                report_meta = os.fstat(report_descriptor)
                if (
                    int(report_meta.st_dev),
                    int(report_meta.st_ino),
                ) != output.owned_files[INTAKE_REPORT_NAME]:
                    raise BundleError(
                        "intake_report_descriptor_identity_changed",
                        exit_kind="output_boundary_error",
                    )
            finally:
                os.close(report_descriptor)

            _verify_materialized_output(
                output,
                expected_files=expected_output_identities,
                report_bytes=rendered,
            )
            _reverify_producer_source(
                git_path=trusted_git,
                control_plane_root=control_plane_root,
                control_plane_revision=control_plane_revision,
                expected=source_binding,
            )
            envelope.verify_unchanged(label="provider_artifact_envelope")

            output.publish()
            _verify_materialized_output(
                output,
                expected_files=expected_output_identities,
                report_bytes=rendered,
            )
            _reverify_producer_source(
                git_path=trusted_git,
                control_plane_root=control_plane_root,
                control_plane_revision=control_plane_revision,
                expected=source_binding,
            )
            envelope.verify_unchanged(label="provider_artifact_envelope")
            output.close()
            return rendered
    except Exception:
        output.cleanup()
        raise


def main() -> int:
    args = parse_args()
    try:
        rendered = _build(args)
    except BundleError as exc:
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
                    error=f"unhandled_candidate_bundle_error: "
                    f"{type(exc).__name__}: {exc}",
                    exit_kind="unhandled_error",
                )
            )
        )
        return 2

    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
