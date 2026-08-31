#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import os
import platform
import re
import secrets
import stat
import struct
import subprocess
import sys
import sysconfig
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

TOOL_NAME = "run_pulsemech_device_ledger_reproduction_capsule_v0"
TOOL_VERSION = "0.1.0"
TOOL_SOURCE_PATH = (
    "tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py"
)

OUTPUT_CAPSULE_NAME = "pulsemech_device_ledger_reproduction_capsule_v0.zip"
OUTPUT_RESULT_NAME = (
    "pulsemech_device_ledger_reproduction_result_reference_v0.json"
)

MANIFEST_SCHEMA_PATH = (
    "schemas/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
)
CAPSULE_CONTRACT_PATH = (
    "contracts/pulsemech_device_ledger_reproduction_capsule_v0.json"
)
CANONICAL_MANIFEST_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json"
)
CANONICALIZATION_PROFILE_PATH = (
    "contracts/pulsemech_device_canonical_json_v0.json"
)
CANONICAL_LEDGER_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
STANDALONE_VERIFIER_PATH = "tools/verify_pulsemech_device_ledger_v0.py"
CANONICAL_EXPECTED_REPORT_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_transition_ledger_reference_verification_v0.json"
)
RESULT_SCHEMA_PATH = (
    "schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json"
)
CAPSULE_BUILDER_PATH = (
    "tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py"
)
CANONICAL_CAPSULE_REPOSITORY_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_ledger_reproduction_capsule_v0.zip"
)
CANONICAL_RESULT_REPOSITORY_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_ledger_reproduction_result_reference_v0.json"
)

MANIFEST_MEMBER_PATH = (
    "manifest/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_v0.json"
)
CAPSULE_LEDGER_MEMBER_PATH = (
    "artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
CAPSULE_VERIFIER_MEMBER_PATH = (
    "verifier/verify_pulsemech_device_ledger_v0.py"
)
CAPSULE_EXPECTED_REPORT_MEMBER_PATH = (
    "expected/"
    "pulsemech_device_transition_ledger_reference_verification_v0.json"
)
CAPSULE_MEMBER_ORDER = (
    MANIFEST_MEMBER_PATH,
    CAPSULE_LEDGER_MEMBER_PATH,
    CAPSULE_VERIFIER_MEMBER_PATH,
    CAPSULE_EXPECTED_REPORT_MEMBER_PATH,
)

PULSELEDGER_MEMBER_ORDER = (
    "contracts/pulsemech_device_canonical_json_v0.json",
    "contracts/pulsemech_ios_observation_contract_v0.json",
    "keys/observer-public-key-v0.bin",
    "ledger/pulsemech_device_transition_ledger_v0.json",
    "manifest/pulsemech_device_ledger_manifest_v0.json",
    "schemas/pulsemech_device_ledger_manifest_v0.schema.json",
    "schemas/pulsemech_device_signature_v0.schema.json",
    "schemas/pulsemech_device_transition_ledger_v0.schema.json",
    "signatures/checkpoint-signature-v0.json",
    "signatures/package-signature-v0.json",
)
PACKAGE_SIGNATURE_MEMBER_PATH = "signatures/package-signature-v0.json"

EXPECTED_OBSERVER_FINGERPRINT_SHA256 = (
    "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
)
EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)

REFERENCE_CONTAINER_IMAGE = (
    "docker.io/library/python:3.11.9-slim-bookworm@sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
REFERENCE_CONTAINER_DIGEST = (
    "sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
REFERENCE_ATTESTATION_SIZE_BYTES = 843
REFERENCE_ATTESTATION_SHA256 = (
    "9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca"
)
REFERENCE_ATTESTATION_MAX_BYTES = 4096
REFERENCE_ATTESTATION: dict[str, Any] = {
    "attestation_mount": "read_only",
    "attestation_role": "reference_environment_precondition",
    "attestation_source": "outer_reference_environment_launcher",
    "authority_effect": "none",
    "container_image": REFERENCE_CONTAINER_IMAGE,
    "container_image_digest": REFERENCE_CONTAINER_DIGEST,
    "container_image_repo_digest_verified": True,
    "container_launch_by_exact_digest": True,
    "document_type": "pulsemech_reference_environment_attestation",
    "network_mode": "none",
    "output_mount": "separate_writable",
    "repository_mount": "read_only",
    "schema_version": "pulsemech_reference_environment_attestation_v0",
    "verification_method": (
        "host_container_runtime_repo_digest_match_before_exact_digest_launch"
    ),
    "verified_before_container_start": True,
}

REFERENCE_ENVIRONMENT: dict[str, Any] = {
    "archive_implementation": {
        "boundary": "cpython_standard_library_bound_to_exact_python_micro_version",
        "module": "zipfile",
    },
    "container_image": REFERENCE_CONTAINER_IMAGE,
    "dependency_policy": "python_standard_library_only",
    "environment_variables": {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    },
    "network_access": "forbidden",
    "operating_system": {
        "architecture": "x86_64",
        "distribution": "debian",
        "version": "bookworm-slim",
    },
    "python": {
        "implementation": "CPython",
        "unicode_data_version": "14.0.0",
        "version": "3.11.9",
    },
    "runtime_downloads": "forbidden",
    "temporary_directory_policy": (
        "isolated_per_construction_outside_protected_sources"
    ),
    "working_directory_policy": "repository_root",
}

REQUIRED_PROCESS_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
}

EXPECTED_CAPSULE_SIZE_BYTES = 285144
EXPECTED_CAPSULE_MEMBER_COUNT = 4
EXPECTED_PROTECTED_SOURCE_COUNT = 10
PROCESS_TIMEOUT_SECONDS = 120
MAX_PROCESS_STDOUT_BYTES = 1_048_576
MAX_PROCESS_STDERR_BYTES = 65_536
MAX_ZIP_MEMBER_COUNT = 64
MAX_ZIP_BYTES = 1_048_576
MAX_CLEANUP_DEPTH = 16
MAX_CLEANUP_ENTRIES = 256

FIXED_DOS_TIME = 0
FIXED_DOS_DATE = 33
FIXED_CREATOR_SYSTEM = 3
FIXED_CREATOR_VERSION = 20
FIXED_VERSION_NEEDED = 20
FIXED_GENERAL_PURPOSE_FLAGS = 0
FIXED_COMPRESSION_METHOD = 0
FIXED_INTERNAL_ATTRIBUTES = 0
FIXED_EXTERNAL_ATTRIBUTES = (stat.S_IFREG | 0o644) << 16

LOCAL_FILE_HEADER_SIGNATURE = 0x04034B50
CENTRAL_DIRECTORY_HEADER_SIGNATURE = 0x02014B50
END_OF_CENTRAL_DIRECTORY_SIGNATURE = 0x06054B50
LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
CENTRAL_DIRECTORY_HEADER = struct.Struct("<IHHHHHHIIIHHHHHII")
END_OF_CENTRAL_DIRECTORY = struct.Struct("<IHHHHIIH")


class RunnerError(RuntimeError):
    def __init__(self, code: str, context: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


class SchemaMismatch(ValueError):
    pass


class _DuplicateJSONKey(ValueError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    relative_path: str
    size_bytes: int
    sha256: str
    git_blob_sha1: str


@dataclass(frozen=True)
class StableStat:
    device: int
    inode: int
    mode: int
    link_count: int
    size_bytes: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class FileSystemIdentity:
    device: int
    inode: int


@dataclass(frozen=True)
class SourceSnapshot:
    spec: SourceSpec
    payload: bytes
    metadata: StableStat


@dataclass(frozen=True)
class ExternalAttestationSnapshot:
    path: Path
    payload: bytes
    metadata: StableStat


@dataclass(frozen=True)
class ProcessCapture:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class ZipMemberRecord:
    name: str
    local_header_offset: int
    central_header_offset: int
    payload_offset: int
    payload_size: int
    crc32: int
    version_made_by: int
    version_needed: int
    flags: int
    compression: int
    dos_time: int
    dos_date: int
    internal_attributes: int
    external_attributes: int


@dataclass(frozen=True)
class ParsedZip:
    payload: bytes
    members: tuple[ZipMemberRecord, ...]
    central_directory_offset: int
    central_directory_size: int

    def member(self, name: str) -> ZipMemberRecord:
        matches = [member for member in self.members if member.name == name]
        if len(matches) != 1:
            raise RunnerError("zip_member_lookup_failed", name)
        return matches[0]

    def member_bytes(self, name: str) -> bytes:
        member = self.member(name)
        start = member.payload_offset
        return self.payload[start : start + member.payload_size]


@dataclass(frozen=True)
class CapsuleObservation:
    payload: bytes
    sha256: str
    git_blob_sha1: str
    parsed: ParsedZip
    members: Mapping[str, bytes]


@dataclass(frozen=True)
class ConstructionObservation:
    construction_id: str
    builder_capture: ProcessCapture
    builder_summary: Mapping[str, Any]
    capsule: CapsuleObservation


@dataclass(frozen=True)
class PositiveObservation:
    run_id: str
    construction_id: str
    capture: ProcessCapture
    report: Mapping[str, Any]
    report_summary: Mapping[str, Any]


@dataclass(frozen=True)
class MutationObservation:
    payload: bytes
    sha256: str
    source_sha256: str
    inner_member_order: tuple[str, ...]


MANIFEST_SCHEMA_SPEC = SourceSpec(
    MANIFEST_SCHEMA_PATH,
    32581,
    "a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c",
    "6a0dabff2e5f725c6ef8e586f9cae7fff566030b",
)
CAPSULE_CONTRACT_SPEC = SourceSpec(
    CAPSULE_CONTRACT_PATH,
    15947,
    "ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67",
    "d15fddbe9250de0ed76b3b7ebb7d679383a867b4",
)
CANONICAL_MANIFEST_SPEC = SourceSpec(
    CANONICAL_MANIFEST_PATH,
    8989,
    "cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf",
    "b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b",
)
CANONICALIZATION_PROFILE_SPEC = SourceSpec(
    CANONICALIZATION_PROFILE_PATH,
    2719,
    "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
    "89d866c8f7a0dc9ddfd2f7d53ff171530dffc18f",
)
CANONICAL_LEDGER_SPEC = SourceSpec(
    CANONICAL_LEDGER_PATH,
    133568,
    "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3",
    "8d9ecb2c6d42f8fd5afb10face6495ef67874b2d",
)
STANDALONE_VERIFIER_SPEC = SourceSpec(
    STANDALONE_VERIFIER_PATH,
    126419,
    "0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7",
    "6f5ac6323c56d22e6a908d6a2419f253617382b0",
)
CANONICAL_EXPECTED_REPORT_SPEC = SourceSpec(
    CANONICAL_EXPECTED_REPORT_PATH,
    15328,
    "5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4",
    "e79e70a243ff104e4d0f17d09379ae1e3962230a",
)
RESULT_SCHEMA_SPEC = SourceSpec(
    RESULT_SCHEMA_PATH,
    71112,
    "83b89d5c8315033a654e717ae017ff5964ac63685e4f65f2d9e18f225c780ca0",
    "833f876f3bdd703c3fab7aa93aacb14bca47f01b",
)
CAPSULE_BUILDER_SPEC = SourceSpec(
    CAPSULE_BUILDER_PATH,
    75083,
    "4878da3e3adb82697fc0aa25b48e439a52c2601bb1a8ceca595eb939f079b01d",
    "d37dc25ef68a08d0b076ffa4e5bcd48442858cde",
)

FIXED_PROTECTED_SOURCE_SPECS = (
    MANIFEST_SCHEMA_SPEC,
    CAPSULE_CONTRACT_SPEC,
    CANONICAL_MANIFEST_SPEC,
    CANONICALIZATION_PROFILE_SPEC,
    CANONICAL_LEDGER_SPEC,
    STANDALONE_VERIFIER_SPEC,
    CANONICAL_EXPECTED_REPORT_SPEC,
    RESULT_SCHEMA_SPEC,
    CAPSULE_BUILDER_SPEC,
)

CAPSULE_MEMBER_SPECS = (
    (
        1,
        MANIFEST_MEMBER_PATH,
        CANONICAL_MANIFEST_PATH,
        CANONICAL_MANIFEST_SPEC.size_bytes,
        CANONICAL_MANIFEST_SPEC.sha256,
        "application/json",
        "capsule_manifest",
    ),
    (
        2,
        CAPSULE_LEDGER_MEMBER_PATH,
        CANONICAL_LEDGER_PATH,
        CANONICAL_LEDGER_SPEC.size_bytes,
        CANONICAL_LEDGER_SPEC.sha256,
        "application/zip",
        "canonical_pulseledger",
    ),
    (
        3,
        CAPSULE_VERIFIER_MEMBER_PATH,
        STANDALONE_VERIFIER_PATH,
        STANDALONE_VERIFIER_SPEC.size_bytes,
        STANDALONE_VERIFIER_SPEC.sha256,
        "text/x-python",
        "standalone_verifier",
    ),
    (
        4,
        CAPSULE_EXPECTED_REPORT_MEMBER_PATH,
        CANONICAL_EXPECTED_REPORT_PATH,
        CANONICAL_EXPECTED_REPORT_SPEC.size_bytes,
        CANONICAL_EXPECTED_REPORT_SPEC.sha256,
        "application/json",
        "canonical_expected_positive_report",
    ),
)


# The runner orchestrates exact processes and byte relations only. It does not
# import verifier internals, implement signature verification, or create release
# authority.


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    try:
        return hashlib.sha1(
            prefix + payload,
            usedforsecurity=False,
        ).hexdigest()
    except TypeError:
        return hashlib.sha1(prefix + payload).hexdigest()


def _stable_stat(metadata: os.stat_result) -> StableStat:
    return StableStat(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        link_count=metadata.st_nlink,
        size_bytes=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


def _filesystem_identity(metadata: os.stat_result) -> FileSystemIdentity:
    return FileSystemIdentity(metadata.st_dev, metadata.st_ino)


def _absolute_without_symlink_resolution(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _require_safe_relative_posix_path(value: str, label: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise RunnerError(f"{label}_unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise RunnerError(f"{label}_unsafe")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise RunnerError(f"{label}_unsafe")
    try:
        value.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise RunnerError(f"{label}_not_ascii") from exc
    return path


def _resolve_repository_root(repository_root: Path) -> Path:
    candidate = _absolute_without_symlink_resolution(repository_root)
    try:
        resolved = candidate.resolve(strict=True)
        metadata = candidate.lstat()
    except OSError as exc:
        raise RunnerError("repository_root_unavailable") from exc
    if candidate != resolved:
        raise RunnerError("repository_root_symlink_or_noncanonical")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RunnerError("repository_root_not_directory")
    return candidate


def _require_repository_working_directory(root: Path) -> None:
    current = _absolute_without_symlink_resolution(Path.cwd())
    try:
        resolved = current.resolve(strict=True)
        metadata = current.lstat()
    except OSError as exc:
        raise RunnerError("working_directory_unavailable") from exc
    if current != resolved:
        raise RunnerError("working_directory_symlink_or_noncanonical")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RunnerError("working_directory_not_directory")
    if current != root:
        raise RunnerError("working_directory_not_repository_root")


def _require_safe_source_path(root: Path, relative_path: str) -> Path:
    relative = _require_safe_relative_posix_path(relative_path, "source_path")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise RunnerError("source_parent_unavailable", relative_path) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError(
                "source_parent_not_canonical_directory",
                relative_path,
            )
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RunnerError("source_missing", relative_path) from exc
    if candidate != resolved:
        raise RunnerError("source_symlink_or_noncanonical", relative_path)
    return candidate


def _open_readonly_nofollow(path: Path, label: str) -> int:
    required = ("O_NOFOLLOW", "O_CLOEXEC")
    if any(getattr(os, name, None) is None for name in required):
        raise RunnerError("required_open_flags_unavailable")
    try:
        return os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise RunnerError("source_open_failed", label) from exc


def _read_stable_regular_file(
    path: Path,
    *,
    label: str,
    expected_size: int | None,
    maximum_size: int,
) -> tuple[bytes, StableStat]:
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise RunnerError("source_lstat_failed", label) from exc
    if stat.S_ISLNK(path_metadata.st_mode):
        raise RunnerError("source_symlink_forbidden", label)
    if not stat.S_ISREG(path_metadata.st_mode):
        raise RunnerError("source_not_regular_file", label)
    if path_metadata.st_nlink != 1:
        raise RunnerError("source_hard_link_state_forbidden", label)
    if expected_size is not None and path_metadata.st_size != expected_size:
        raise RunnerError("source_size_mismatch", label)
    if path_metadata.st_size < 1 or path_metadata.st_size > maximum_size:
        raise RunnerError("source_size_out_of_bounds", label)

    descriptor = _open_readonly_nofollow(path, label)
    try:
        before = os.fstat(descriptor)
        if _filesystem_identity(before) != _filesystem_identity(path_metadata):
            raise RunnerError("source_changed_before_read", label)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RunnerError("source_file_state_invalid", label)
        read_limit = (
            expected_size + 1
            if expected_size is not None
            else maximum_size + 1
        )
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(read_limit)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if _stable_stat(before) != _stable_stat(after):
        raise RunnerError("source_changed_during_read", label)
    if expected_size is not None and len(payload) != expected_size:
        raise RunnerError("source_size_mismatch", label)
    if len(payload) < 1 or len(payload) > maximum_size:
        raise RunnerError("source_size_out_of_bounds", label)
    try:
        final_metadata = path.lstat()
    except OSError as exc:
        raise RunnerError("source_lstat_failed_after_read", label) from exc
    if _stable_stat(final_metadata) != _stable_stat(after):
        raise RunnerError("source_changed_after_read", label)
    return payload, _stable_stat(after)


def _read_exact_source(root: Path, spec: SourceSpec) -> SourceSnapshot:
    path = _require_safe_source_path(root, spec.relative_path)
    payload, metadata = _read_stable_regular_file(
        path,
        label=spec.relative_path,
        expected_size=spec.size_bytes,
        maximum_size=max(spec.size_bytes, 1),
    )
    if sha256_bytes(payload) != spec.sha256:
        raise RunnerError("source_sha256_mismatch", spec.relative_path)
    if git_blob_sha1(payload) != spec.git_blob_sha1:
        raise RunnerError("source_git_blob_sha1_mismatch", spec.relative_path)
    return SourceSnapshot(spec, payload, metadata)


def _runner_source_spec(root: Path) -> SourceSpec:
    source_path = _require_safe_source_path(root, TOOL_SOURCE_PATH)
    runtime_source = _absolute_without_symlink_resolution(Path(__file__))
    try:
        runtime_resolved = runtime_source.resolve(strict=True)
    except OSError as exc:
        raise RunnerError("runner_source_unavailable") from exc
    if runtime_source != runtime_resolved or runtime_source != source_path:
        raise RunnerError("runner_source_path_mismatch")
    payload, _ = _read_stable_regular_file(
        source_path,
        label=TOOL_SOURCE_PATH,
        expected_size=None,
        maximum_size=1_048_576,
    )
    return SourceSpec(
        TOOL_SOURCE_PATH,
        len(payload),
        sha256_bytes(payload),
        git_blob_sha1(payload),
    )


def _protected_source_specs(root: Path) -> tuple[SourceSpec, ...]:
    runner_spec = _runner_source_spec(root)
    specs = FIXED_PROTECTED_SOURCE_SPECS + (runner_spec,)
    if len(specs) != EXPECTED_PROTECTED_SOURCE_COUNT:
        raise RunnerError("protected_source_count_constant_mismatch")
    if len({spec.relative_path for spec in specs}) != len(specs):
        raise RunnerError("duplicate_protected_source_spec")
    return specs


def _read_protected_sources(
    root: Path,
    specs: Sequence[SourceSpec],
) -> dict[str, SourceSnapshot]:
    snapshots: dict[str, SourceSnapshot] = {}
    for spec in specs:
        snapshots[spec.relative_path] = _read_exact_source(root, spec)
    return snapshots


def _require_sources_unchanged(
    root: Path,
    specs: Sequence[SourceSpec],
    baseline: Mapping[str, SourceSnapshot],
) -> dict[str, SourceSnapshot]:
    if tuple(baseline) != tuple(spec.relative_path for spec in specs):
        raise RunnerError("protected_source_baseline_order_mismatch")
    current: dict[str, SourceSnapshot] = {}
    for spec in specs:
        observed = _read_exact_source(root, spec)
        expected = baseline[spec.relative_path]
        if observed.payload != expected.payload:
            raise RunnerError("protected_source_bytes_changed", spec.relative_path)
        if observed.metadata != expected.metadata:
            raise RunnerError(
                "protected_source_metadata_changed",
                spec.relative_path,
            )
        current[spec.relative_path] = observed
    return current


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise _DuplicateJSONKey(key)
        output[key] = value
    return output


def _parse_json_integer(token: str) -> int:
    if token == "-0":
        raise ValueError("negative_zero_forbidden")
    value = int(token, 10)
    if value < -(2**63) or value > 2**63 - 1:
        raise ValueError("integer_out_of_range")
    return value


def _reject_json_float(_token: str) -> float:
    raise ValueError("floating_point_forbidden")


def _reject_json_constant(_token: str) -> None:
    raise ValueError("non_finite_number_forbidden")


def _load_strict_json(payload: bytes, label: str) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise RunnerError(f"{label}_utf8_bom_forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_int=_parse_json_integer,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RunnerError(f"{label}_invalid_json") from exc


def _load_strict_json_object(payload: bytes, label: str) -> dict[str, Any]:
    value = _load_strict_json(payload, label)
    if not isinstance(value, dict):
        raise RunnerError(f"{label}_not_object")
    return value


def _normalize_json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 256:
        raise RunnerError("canonical_json_depth_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -(2**63) or value > 2**63 - 1:
            raise RunnerError("canonical_integer_out_of_range")
        return value
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise RunnerError("canonical_string_not_unicode_scalar") from exc
        for character in value:
            code = ord(character)
            if 0xD800 <= code <= 0xDFFF:
                raise RunnerError("canonical_string_not_unicode_scalar")
            if unicodedata.category(character) == "Cn":
                raise RunnerError("canonical_string_unassigned_code_point")
        normalized = unicodedata.normalize("NFC", value)
        if normalized != value:
            raise RunnerError("canonical_string_not_nfc")
        return value
    if isinstance(value, list):
        return [_normalize_json_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RunnerError("canonical_key_not_string")
            try:
                key.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise RunnerError("canonical_key_not_unicode_scalar") from exc
            for character in key:
                code = ord(character)
                if 0xD800 <= code <= 0xDFFF:
                    raise RunnerError("canonical_key_not_unicode_scalar")
                if unicodedata.category(character) == "Cn":
                    raise RunnerError("canonical_key_unassigned_code_point")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise RunnerError("canonical_key_collision")
            normalized[normalized_key] = _normalize_json_value(
                item,
                depth=depth + 1,
            )
        return normalized
    raise RunnerError("canonical_json_type_unsupported")


def _canonical_json_string(value: str) -> str:
    output = ['"']
    escapes = {
        0x08: "\\b",
        0x09: "\\t",
        0x0A: "\\n",
        0x0C: "\\f",
        0x0D: "\\r",
        0x22: '\\"',
        0x5C: "\\\\",
    }
    for character in value:
        code = ord(character)
        if 0xD800 <= code <= 0xDFFF:
            raise RunnerError("canonical_string_not_unicode_scalar")
        if code in escapes:
            output.append(escapes[code])
        elif code <= 0x1F:
            output.append(f"\\u00{code:02x}")
        else:
            output.append(character)
    output.append('"')
    return "".join(output)


def _canonical_json_text(value: Any, *, depth: int = 0) -> str:
    if depth > 256:
        raise RunnerError("canonical_json_depth_exceeded")
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return _canonical_json_string(value)
    if isinstance(value, list):
        return "[" + ",".join(
            _canonical_json_text(item, depth=depth + 1) for item in value
        ) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: key.encode("utf-8"))
        return "{" + ",".join(
            _canonical_json_string(key)
            + ":"
            + _canonical_json_text(value[key], depth=depth + 1)
            for key in keys
        ) + "}"
    raise RunnerError("canonical_json_type_unsupported")


def canonical_json_bytes(value: Any) -> bytes:
    normalized = _normalize_json_value(value)
    return _canonical_json_text(normalized).encode("utf-8")


def _load_canonical_json_object(payload: bytes, label: str) -> dict[str, Any]:
    value = _load_strict_json_object(payload, label)
    if canonical_json_bytes(value) != payload:
        raise RunnerError(f"{label}_not_canonical_json")
    return value


def _json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _resolve_json_pointer(root: Mapping[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise SchemaMismatch("nonlocal_ref")
    current: Any = root
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise SchemaMismatch("unresolved_ref")
        current = current[part]
    return current


def _instance_matches_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    if expected == "number":
        return (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
        )
    return False


def _validate_json_schema(
    instance: Any,
    schema: Any,
    *,
    root: Mapping[str, Any],
    path: str = "$",
    depth: int = 0,
) -> None:
    if depth > 512:
        raise SchemaMismatch(f"{path}:depth")
    if schema is True:
        return
    if schema is False:
        raise SchemaMismatch(f"{path}:false_schema")
    if not isinstance(schema, dict):
        raise SchemaMismatch(f"{path}:schema_not_object")

    if "$ref" in schema:
        target = _resolve_json_pointer(root, schema["$ref"])
        _validate_json_schema(
            instance,
            target,
            root=root,
            path=path,
            depth=depth + 1,
        )

    for child in schema.get("allOf", []):
        _validate_json_schema(
            instance,
            child,
            root=root,
            path=path,
            depth=depth + 1,
        )

    if "not" in schema:
        try:
            _validate_json_schema(
                instance,
                schema["not"],
                root=root,
                path=path,
                depth=depth + 1,
            )
        except SchemaMismatch:
            pass
        else:
            raise SchemaMismatch(f"{path}:not")

    if "const" in schema and not _json_equal(instance, schema["const"]):
        raise SchemaMismatch(f"{path}:const")
    if "enum" in schema and not any(
        _json_equal(instance, candidate) for candidate in schema["enum"]
    ):
        raise SchemaMismatch(f"{path}:enum")

    if "type" in schema:
        types = schema["type"]
        expected_types = [types] if isinstance(types, str) else list(types)
        if not any(_instance_matches_type(instance, item) for item in expected_types):
            raise SchemaMismatch(f"{path}:type")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise SchemaMismatch(f"{path}:missing:{key}")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise SchemaMismatch(f"{path}:properties")
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                _validate_json_schema(
                    value,
                    properties[key],
                    root=root,
                    path=f"{path}/{key}",
                    depth=depth + 1,
                )
            elif additional is False:
                raise SchemaMismatch(f"{path}:additional:{key}")
            elif isinstance(additional, dict):
                _validate_json_schema(
                    value,
                    additional,
                    root=root,
                    path=f"{path}/{key}",
                    depth=depth + 1,
                )

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaMismatch(f"{path}:minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaMismatch(f"{path}:maxItems")
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(prefix):
            if index < len(instance):
                _validate_json_schema(
                    instance[index],
                    child,
                    root=root,
                    path=f"{path}/{index}",
                    depth=depth + 1,
                )
        items = schema.get("items", True)
        if len(instance) > len(prefix):
            if items is False:
                raise SchemaMismatch(f"{path}:items")
            if isinstance(items, dict):
                for index in range(len(prefix), len(instance)):
                    _validate_json_schema(
                        instance[index],
                        items,
                        root=root,
                        path=f"{path}/{index}",
                        depth=depth + 1,
                    )
        if schema.get("uniqueItems") is True:
            seen: set[bytes] = set()
            for item in instance:
                encoded = canonical_json_bytes(item)
                if encoded in seen:
                    raise SchemaMismatch(f"{path}:uniqueItems")
                seen.add(encoded)

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaMismatch(f"{path}:minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SchemaMismatch(f"{path}:maxLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise SchemaMismatch(f"{path}:pattern")

    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaMismatch(f"{path}:minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaMismatch(f"{path}:maximum")


def _read_reference_attestation(
    path: Path,
    repository_root: Path,
) -> ExternalAttestationSnapshot:
    candidate = _absolute_without_symlink_resolution(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RunnerError("reference_attestation_unavailable") from exc
    if candidate != resolved:
        raise RunnerError("reference_attestation_symlink_or_noncanonical")
    if _is_within(candidate, repository_root):
        raise RunnerError("reference_attestation_inside_repository")
    payload, metadata = _read_stable_regular_file(
        candidate,
        label="reference_environment_attestation",
        expected_size=REFERENCE_ATTESTATION_SIZE_BYTES,
        maximum_size=REFERENCE_ATTESTATION_MAX_BYTES,
    )
    if sha256_bytes(payload) != REFERENCE_ATTESTATION_SHA256:
        raise RunnerError("reference_attestation_sha256_mismatch")
    observed = _load_canonical_json_object(payload, "reference_attestation")
    if observed != REFERENCE_ATTESTATION:
        raise RunnerError("reference_attestation_content_mismatch")
    return ExternalAttestationSnapshot(candidate, payload, metadata)


def _require_attestation_unchanged(
    baseline: ExternalAttestationSnapshot,
    repository_root: Path,
) -> ExternalAttestationSnapshot:
    current = _read_reference_attestation(baseline.path, repository_root)
    if current.payload != baseline.payload or current.metadata != baseline.metadata:
        raise RunnerError("reference_attestation_changed")
    return current


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except OSError as exc:
        raise RunnerError("reference_os_release_unavailable") from exc
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        values[key] = value
    return values


def _mount_is_read_only(path: Path) -> bool:
    readonly_flag = getattr(os, "ST_RDONLY", 1)
    try:
        return bool(os.statvfs(path).f_flag & readonly_flag)
    except OSError as exc:
        raise RunnerError("mount_state_unavailable", os.fspath(path)) from exc


def _descriptor_mount_is_read_only(descriptor: int, label: str) -> bool:
    readonly_flag = getattr(os, "ST_RDONLY", 1)
    try:
        return bool(os.fstatvfs(descriptor).f_flag & readonly_flag)
    except OSError as exc:
        raise RunnerError(f"{label}_mount_state_unavailable") from exc


def _verify_network_none() -> None:
    interfaces = Path("/sys/class/net")
    try:
        names = sorted(entry.name for entry in interfaces.iterdir())
    except OSError as exc:
        raise RunnerError("network_interface_state_unavailable") from exc
    if names != ["lo"]:
        raise RunnerError("network_mode_not_none", ",".join(names))
    route_path = Path("/proc/net/route")
    try:
        route_lines = route_path.read_text(encoding="ascii").splitlines()
    except OSError as exc:
        raise RunnerError("network_route_state_unavailable") from exc
    if any(line.strip() for line in route_lines[1:]):
        raise RunnerError("network_route_present")


def _verify_reference_runtime(
    repository_root: Path,
    attestation: ExternalAttestationSnapshot,
    output_parent: Path,
    output_parent_descriptor: int,
    output_parent_identity: FileSystemIdentity,
) -> Path:
    if os.name != "posix" or platform.system() != "Linux":
        raise RunnerError("reference_operating_system_mismatch")
    if platform.machine() != "x86_64":
        raise RunnerError("reference_architecture_mismatch")
    if sys.implementation.name != "cpython":
        raise RunnerError("reference_python_implementation_mismatch")
    if platform.python_version() != "3.11.9":
        raise RunnerError("reference_python_version_mismatch")
    if unicodedata.unidata_version != "14.0.0":
        raise RunnerError("reference_unicode_version_mismatch")
    if sysconfig.get_platform() != "linux-x86_64":
        raise RunnerError("reference_python_platform_mismatch")
    for key, expected in REQUIRED_PROCESS_ENVIRONMENT.items():
        if os.environ.get(key) != expected:
            raise RunnerError("reference_environment_variable_mismatch", key)
    os_release = _read_os_release()
    if os_release.get("ID") != "debian":
        raise RunnerError("reference_os_distribution_mismatch")
    if os_release.get("VERSION_CODENAME") != "bookworm":
        raise RunnerError("reference_os_version_mismatch")
    if not _mount_is_read_only(repository_root):
        raise RunnerError("repository_mount_not_read_only")
    if not _mount_is_read_only(attestation.path):
        raise RunnerError("attestation_mount_not_read_only")
    _require_open_directory_path_identity(
        output_parent,
        output_parent_descriptor,
        output_parent_identity,
        "output_parent",
    )
    if _descriptor_mount_is_read_only(
        output_parent_descriptor,
        "output_parent",
    ):
        raise RunnerError("output_mount_not_writable")
    _verify_network_none()
    executable = _absolute_without_symlink_resolution(Path(sys.executable))
    try:
        resolved = executable.resolve(strict=True)
    except OSError as exc:
        raise RunnerError("python_executable_unavailable") from exc
    if not resolved.is_file():
        raise RunnerError("python_executable_not_file")
    return resolved


def _validate_implementation_constants() -> None:
    attestation_bytes = canonical_json_bytes(REFERENCE_ATTESTATION)
    if len(attestation_bytes) != REFERENCE_ATTESTATION_SIZE_BYTES:
        raise RunnerError("reference_attestation_size_constant_mismatch")
    if sha256_bytes(attestation_bytes) != REFERENCE_ATTESTATION_SHA256:
        raise RunnerError("reference_attestation_sha256_constant_mismatch")
    if not REFERENCE_CONTAINER_IMAGE.endswith("@" + REFERENCE_CONTAINER_DIGEST):
        raise RunnerError("reference_container_digest_constant_mismatch")
    if tuple(item[1] for item in CAPSULE_MEMBER_SPECS) != CAPSULE_MEMBER_ORDER:
        raise RunnerError("capsule_member_order_constant_mismatch")
    if len(PULSELEDGER_MEMBER_ORDER) != 10:
        raise RunnerError("pulseledger_member_order_constant_mismatch")


def _resolve_output_destination(
    output_directory: Path,
    repository_root: Path,
    attestation: ExternalAttestationSnapshot,
) -> tuple[Path, Path]:
    destination = _absolute_without_symlink_resolution(output_directory)
    parent = destination.parent
    try:
        resolved_parent = parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as exc:
        raise RunnerError("output_parent_unavailable") from exc
    if parent != resolved_parent:
        raise RunnerError("output_parent_symlink_or_noncanonical")
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(
        parent_metadata.st_mode
    ):
        raise RunnerError("output_parent_not_directory")
    if _is_within(destination, repository_root):
        raise RunnerError("output_directory_inside_repository")
    if _is_within(destination, attestation.path.parent):
        raise RunnerError("output_directory_inside_attestation_mount")
    if os.path.lexists(destination):
        raise RunnerError("output_directory_exists")
    return destination, parent


def _open_directory_nofollow(path: Path, label: str) -> tuple[int, FileSystemIdentity]:
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise RunnerError(f"{label}_lstat_failed") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RunnerError(f"{label}_open_failed") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISDIR(opened.st_mode):
            raise RunnerError(f"{label}_not_directory")
        if _filesystem_identity(opened) != _filesystem_identity(path_metadata):
            raise RunnerError(f"{label}_identity_mismatch")
        return descriptor, _filesystem_identity(opened)
    except BaseException:
        os.close(descriptor)
        raise


def _require_open_directory_path_identity(
    path: Path,
    descriptor: int,
    identity: FileSystemIdentity,
    label: str,
) -> None:
    try:
        path_metadata = path.lstat()
        opened = os.fstat(descriptor)
    except OSError as exc:
        raise RunnerError(f"{label}_identity_recheck_failed") from exc
    if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISDIR(
        path_metadata.st_mode
    ):
        raise RunnerError(f"{label}_identity_recheck_not_directory")
    if _filesystem_identity(path_metadata) != identity:
        raise RunnerError(f"{label}_path_identity_changed")
    if _filesystem_identity(opened) != identity:
        raise RunnerError(f"{label}_descriptor_identity_changed")


def _mkdir_owned(
    parent_descriptor: int,
    name: str,
    mode: int = 0o700,
) -> tuple[int, FileSystemIdentity]:
    if not name or "/" in name or name in {".", ".."}:
        raise RunnerError("owned_directory_name_invalid")
    created = False
    descriptor = -1
    identity: FileSystemIdentity | None = None
    try:
        os.mkdir(name, mode, dir_fd=parent_descriptor)
        created = True
        metadata = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(metadata.st_mode):
            raise RunnerError("owned_directory_not_directory", name)
        identity = _filesystem_identity(metadata)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        if _filesystem_identity(os.fstat(descriptor)) != identity:
            raise RunnerError("owned_directory_identity_mismatch", name)
        result = (descriptor, identity)
        descriptor = -1
        return result
    except OSError as exc:
        error: BaseException = RunnerError(
            "owned_directory_create_or_open_failed",
            name,
        )
        error.__cause__ = exc
    except BaseException as exc:
        error = exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if created and identity is not None:
        try:
            current = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                stat.S_ISDIR(current.st_mode)
                and _filesystem_identity(current) == identity
            ):
                os.rmdir(name, dir_fd=parent_descriptor)
        except BaseException:
            pass
    raise error


def _fsync_directory(descriptor: int, code: str) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise RunnerError(code) from exc


def _rename_directory_noreplace(
    parent_descriptor: int,
    source_name: str,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RunnerError("atomic_noreplace_publish_unavailable")
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_descriptor,
        os.fsencode(source_name),
        parent_descriptor,
        os.fsencode(destination_name),
        1,
    )
    if result == 0:
        return
    observed_errno = ctypes.get_errno()
    if observed_errno == errno.EEXIST:
        raise RunnerError("output_directory_exists_before_publish")
    raise RunnerError("atomic_output_publish_failed", str(observed_errno))


def _safe_recursive_delete_contents(
    directory_descriptor: int,
    *,
    depth: int = 0,
    counter: list[int] | None = None,
) -> None:
    if depth > MAX_CLEANUP_DEPTH:
        raise RunnerError("cleanup_depth_exceeded")
    if counter is None:
        counter = [0]
    try:
        entries = sorted(os.listdir(directory_descriptor))
    except OSError as exc:
        raise RunnerError("cleanup_list_failed") from exc
    for name in entries:
        counter[0] += 1
        if counter[0] > MAX_CLEANUP_ENTRIES:
            raise RunnerError("cleanup_entry_limit_exceeded")
        if not name or "/" in name or name in {".", ".."}:
            raise RunnerError("cleanup_entry_name_invalid")
        metadata = os.stat(
            name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if stat.S_ISDIR(metadata.st_mode):
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
            child = os.open(name, flags, dir_fd=directory_descriptor)
            try:
                if _filesystem_identity(os.fstat(child)) != _filesystem_identity(
                    metadata
                ):
                    raise RunnerError("cleanup_child_identity_mismatch")
                os.fchmod(child, 0o700)
                _safe_recursive_delete_contents(
                    child,
                    depth=depth + 1,
                    counter=counter,
                )
                _fsync_directory(child, "cleanup_child_fsync_failed")
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=directory_descriptor)
        else:
            os.unlink(name, dir_fd=directory_descriptor)


def _remove_named_owned_directory(
    *,
    parent_descriptor: int,
    directory_descriptor: int,
    directory_name: str,
    directory_identity: FileSystemIdentity,
) -> None:
    try:
        path_metadata = os.stat(
            directory_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RunnerError("cleanup_target_unavailable") from exc
    if not stat.S_ISDIR(path_metadata.st_mode):
        raise RunnerError("cleanup_target_not_directory")
    if _filesystem_identity(path_metadata) != directory_identity:
        raise RunnerError("cleanup_target_identity_mismatch")
    opened = os.fstat(directory_descriptor)
    if _filesystem_identity(opened) != directory_identity:
        raise RunnerError("cleanup_descriptor_identity_mismatch")
    os.fchmod(directory_descriptor, 0o700)
    _safe_recursive_delete_contents(directory_descriptor)
    _fsync_directory(directory_descriptor, "cleanup_directory_fsync_failed")
    current = os.stat(
        directory_name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if _filesystem_identity(current) != directory_identity:
        raise RunnerError("cleanup_target_identity_changed")
    os.rmdir(directory_name, dir_fd=parent_descriptor)


def _create_child_directory(parent: Path, name: str) -> Path:
    candidate = parent / name
    try:
        os.mkdir(candidate, 0o700)
    except OSError as exc:
        raise RunnerError("workspace_child_create_failed", name) from exc
    metadata = candidate.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise RunnerError("workspace_child_not_directory", name)
    return candidate


def _write_exact_file(path: Path, payload: bytes, mode: int = 0o444) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise RunnerError("materialized_file_create_failed", path.name) from exc
    try:
        identity = _filesystem_identity(os.fstat(descriptor))
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            written = handle.write(payload)
            if written != len(payload):
                raise RunnerError("file_write_incomplete", path.name)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    observed, metadata = _read_stable_regular_file(
        path,
        label=path.name,
        expected_size=len(payload),
        maximum_size=max(1, len(payload)),
    )
    if observed != payload or _filesystem_identity_from_stable(metadata) != identity:
        raise RunnerError("materialized_file_readback_mismatch", path.name)


def _filesystem_identity_from_stable(metadata: StableStat) -> FileSystemIdentity:
    return FileSystemIdentity(metadata.device, metadata.inode)


def _read_bounded_process_stream(
    payload: bytes,
    *,
    maximum: int,
    label: str,
) -> bytes:
    if len(payload) > maximum:
        raise RunnerError(f"{label}_too_large")
    return payload


def _run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    expected_exit_status: int,
) -> ProcessCapture:
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise RunnerError("process_command_invalid")
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(REQUIRED_PROCESS_ENVIRONMENT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=PROCESS_TIMEOUT_SECONDS,
            check=False,
            close_fds=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError("process_timeout") from exc
    except OSError as exc:
        raise RunnerError("process_start_failed") from exc
    stdout = _read_bounded_process_stream(
        completed.stdout,
        maximum=MAX_PROCESS_STDOUT_BYTES,
        label="process_stdout",
    )
    stderr = _read_bounded_process_stream(
        completed.stderr,
        maximum=MAX_PROCESS_STDERR_BYTES,
        label="process_stderr",
    )
    if completed.returncode != expected_exit_status:
        raise RunnerError(
            "process_exit_status_mismatch",
            str(completed.returncode),
        )
    return ProcessCapture(completed.returncode, stdout, stderr)


def _process_stream_identity(payload: bytes, framing: str) -> dict[str, Any]:
    return {
        "byte_identity": "exact_process_stream_bytes",
        "framing": framing,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _empty_process_stream_identity() -> dict[str, Any]:
    return _process_stream_identity(b"", "empty")


def _parse_stored_zip(
    payload: bytes,
    *,
    expected_order: Sequence[str],
    label: str,
    require_outer_profile: bool,
) -> ParsedZip:
    if len(payload) < END_OF_CENTRAL_DIRECTORY.size or len(payload) > MAX_ZIP_BYTES:
        raise RunnerError(f"{label}_size_out_of_bounds")
    eocd_offset = len(payload) - END_OF_CENTRAL_DIRECTORY.size
    try:
        (
            signature,
            disk_number,
            central_disk,
            entries_on_disk,
            total_entries,
            central_size,
            central_offset,
            comment_length,
        ) = END_OF_CENTRAL_DIRECTORY.unpack_from(payload, eocd_offset)
    except struct.error as exc:
        raise RunnerError(f"{label}_eocd_truncated") from exc
    if signature != END_OF_CENTRAL_DIRECTORY_SIGNATURE:
        raise RunnerError(f"{label}_eocd_signature_invalid")
    if any((disk_number, central_disk)) or entries_on_disk != total_entries:
        raise RunnerError(f"{label}_multidisk_forbidden")
    if comment_length != 0:
        raise RunnerError(f"{label}_archive_comment_forbidden")
    if total_entries != len(expected_order) or total_entries > MAX_ZIP_MEMBER_COUNT:
        raise RunnerError(f"{label}_member_count_mismatch")
    if central_offset + central_size != eocd_offset:
        raise RunnerError(f"{label}_central_directory_bounds_invalid")

    members: list[ZipMemberRecord] = []
    cursor = central_offset
    seen_names: set[str] = set()
    for expected_name in expected_order:
        central_header_offset = cursor
        if cursor + CENTRAL_DIRECTORY_HEADER.size > eocd_offset:
            raise RunnerError(f"{label}_central_header_truncated")
        try:
            fields = CENTRAL_DIRECTORY_HEADER.unpack_from(payload, cursor)
        except struct.error as exc:
            raise RunnerError(f"{label}_central_header_truncated") from exc
        (
            central_signature,
            version_made_by,
            version_needed,
            flags,
            compression,
            dos_time,
            dos_date,
            crc32_value,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
            member_comment_length,
            disk_start,
            internal_attributes,
            external_attributes,
            local_header_offset,
        ) = fields
        if central_signature != CENTRAL_DIRECTORY_HEADER_SIGNATURE:
            raise RunnerError(f"{label}_central_header_signature_invalid")
        if any(
            value == 0xFFFFFFFF
            for value in (
                compressed_size,
                uncompressed_size,
                local_header_offset,
            )
        ):
            raise RunnerError(f"{label}_zip64_forbidden")
        cursor += CENTRAL_DIRECTORY_HEADER.size
        end_name = cursor + name_length
        end_extra = end_name + extra_length
        end_comment = end_extra + member_comment_length
        if end_comment > eocd_offset:
            raise RunnerError(f"{label}_central_variable_fields_truncated")
        name_bytes = payload[cursor:end_name]
        try:
            name = name_bytes.decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise RunnerError(f"{label}_member_name_not_ascii") from exc
        _require_safe_relative_posix_path(name, f"{label}_member_name")
        if name != expected_name:
            raise RunnerError(f"{label}_member_order_mismatch", name)
        if name in seen_names:
            raise RunnerError(f"{label}_duplicate_member_name", name)
        seen_names.add(name)
        if extra_length != 0 or member_comment_length != 0:
            raise RunnerError(f"{label}_member_metadata_not_empty", name)
        if disk_start != 0:
            raise RunnerError(f"{label}_member_disk_start_invalid", name)
        if flags != 0:
            raise RunnerError(f"{label}_member_flags_invalid", name)
        if compression != 0 or compressed_size != uncompressed_size:
            raise RunnerError(f"{label}_member_compression_invalid", name)
        if name.endswith("/"):
            raise RunnerError(f"{label}_directory_entry_forbidden", name)
        if require_outer_profile:
            expected_version_made = (
                (FIXED_CREATOR_SYSTEM << 8) | FIXED_CREATOR_VERSION
            )
            if version_made_by != expected_version_made:
                raise RunnerError(f"{label}_version_made_by_mismatch", name)
            if version_needed != FIXED_VERSION_NEEDED:
                raise RunnerError(f"{label}_version_needed_mismatch", name)
            if dos_time != FIXED_DOS_TIME or dos_date != FIXED_DOS_DATE:
                raise RunnerError(f"{label}_timestamp_mismatch", name)
            if internal_attributes != FIXED_INTERNAL_ATTRIBUTES:
                raise RunnerError(f"{label}_internal_attributes_mismatch", name)
            if external_attributes != FIXED_EXTERNAL_ATTRIBUTES:
                raise RunnerError(f"{label}_external_attributes_mismatch", name)

        if local_header_offset + LOCAL_FILE_HEADER.size > central_offset:
            raise RunnerError(f"{label}_local_header_bounds_invalid", name)
        try:
            local_fields = LOCAL_FILE_HEADER.unpack_from(payload, local_header_offset)
        except struct.error as exc:
            raise RunnerError(f"{label}_local_header_truncated", name) from exc
        (
            local_signature,
            local_version_needed,
            local_flags,
            local_compression,
            local_time,
            local_date,
            local_crc32,
            local_compressed_size,
            local_uncompressed_size,
            local_name_length,
            local_extra_length,
        ) = local_fields
        if local_signature != LOCAL_FILE_HEADER_SIGNATURE:
            raise RunnerError(f"{label}_local_header_signature_invalid", name)
        local_name_start = local_header_offset + LOCAL_FILE_HEADER.size
        local_name_end = local_name_start + local_name_length
        local_extra_end = local_name_end + local_extra_length
        payload_end = local_extra_end + local_compressed_size
        if payload_end > central_offset:
            raise RunnerError(f"{label}_member_payload_bounds_invalid", name)
        if payload[local_name_start:local_name_end] != name_bytes:
            raise RunnerError(f"{label}_local_central_name_mismatch", name)
        if local_extra_length != 0:
            raise RunnerError(f"{label}_local_extra_forbidden", name)
        if (
            local_version_needed != version_needed
            or local_flags != flags
            or local_compression != compression
            or local_time != dos_time
            or local_date != dos_date
            or local_crc32 != crc32_value
            or local_compressed_size != compressed_size
            or local_uncompressed_size != uncompressed_size
        ):
            raise RunnerError(f"{label}_local_central_mismatch", name)
        member_payload = payload[local_extra_end:payload_end]
        if zlib.crc32(member_payload) & 0xFFFFFFFF != crc32_value:
            raise RunnerError(f"{label}_crc32_mismatch", name)
        members.append(
            ZipMemberRecord(
                name=name,
                local_header_offset=local_header_offset,
                central_header_offset=central_header_offset,
                payload_offset=local_extra_end,
                payload_size=uncompressed_size,
                crc32=crc32_value,
                version_made_by=version_made_by,
                version_needed=version_needed,
                flags=flags,
                compression=compression,
                dos_time=dos_time,
                dos_date=dos_date,
                internal_attributes=internal_attributes,
                external_attributes=external_attributes,
            )
        )
        cursor = end_comment

    if cursor != eocd_offset:
        raise RunnerError(f"{label}_central_directory_size_mismatch")
    local_members = sorted(members, key=lambda item: item.local_header_offset)
    if [member.name for member in local_members] != list(expected_order):
        raise RunnerError(f"{label}_local_member_order_mismatch")
    local_cursor = 0
    for member in local_members:
        if member.local_header_offset != local_cursor:
            raise RunnerError(f"{label}_local_layout_not_contiguous")
        local_cursor = member.payload_offset + member.payload_size
    if local_cursor != central_offset:
        raise RunnerError(f"{label}_local_region_size_mismatch")

    try:
        with zipfile.ZipFile(io_bytes(payload), "r", allowZip64=False) as archive:
            infos = archive.infolist()
            if [info.filename for info in infos] != list(expected_order):
                raise RunnerError(f"{label}_zipfile_member_order_mismatch")
            if archive.comment != b"":
                raise RunnerError(f"{label}_zipfile_archive_comment_forbidden")
            if archive.testzip() is not None:
                raise RunnerError(f"{label}_zipfile_crc32_failure")
            for info, member in zip(infos, members):
                if (
                    info.compress_type != zipfile.ZIP_STORED
                    or info.file_size != member.payload_size
                    or info.compress_size != member.payload_size
                    or info.CRC != member.crc32
                    or info.extra != b""
                    or info.comment != b""
                    or info.flag_bits != 0
                    or info.is_dir()
                ):
                    raise RunnerError(f"{label}_zipfile_metadata_mismatch", info.filename)
    except zipfile.BadZipFile as exc:
        raise RunnerError(f"{label}_zipfile_parse_failed") from exc

    return ParsedZip(payload, tuple(members), central_offset, central_size)


def io_bytes(payload: bytes):
    import io

    return io.BytesIO(payload)


def _inspect_capsule(
    payload: bytes,
    protected: Mapping[str, SourceSnapshot],
) -> CapsuleObservation:
    if len(payload) != EXPECTED_CAPSULE_SIZE_BYTES:
        raise RunnerError("capsule_size_mismatch")
    parsed = _parse_stored_zip(
        payload,
        expected_order=CAPSULE_MEMBER_ORDER,
        label="capsule",
        require_outer_profile=True,
    )
    members = {name: parsed.member_bytes(name) for name in CAPSULE_MEMBER_ORDER}
    expected_sources = {
        MANIFEST_MEMBER_PATH: protected[CANONICAL_MANIFEST_PATH].payload,
        CAPSULE_LEDGER_MEMBER_PATH: protected[CANONICAL_LEDGER_PATH].payload,
        CAPSULE_VERIFIER_MEMBER_PATH: protected[STANDALONE_VERIFIER_PATH].payload,
        CAPSULE_EXPECTED_REPORT_MEMBER_PATH: protected[
            CANONICAL_EXPECTED_REPORT_PATH
        ].payload,
    }
    for name in CAPSULE_MEMBER_ORDER:
        if members[name] != expected_sources[name]:
            raise RunnerError("capsule_member_bytes_mismatch", name)
    return CapsuleObservation(
        payload,
        sha256_bytes(payload),
        git_blob_sha1(payload),
        parsed,
        members,
    )


def _read_builder_output(path: Path) -> bytes:
    payload, _ = _read_stable_regular_file(
        path,
        label="builder_output_capsule",
        expected_size=EXPECTED_CAPSULE_SIZE_BYTES,
        maximum_size=EXPECTED_CAPSULE_SIZE_BYTES,
    )
    return payload


def _validate_builder_summary(
    capture: ProcessCapture,
    capsule: CapsuleObservation,
) -> dict[str, Any]:
    if capture.stderr != b"":
        raise RunnerError("builder_stderr_not_empty")
    if not capture.stdout.endswith(b"\n") or capture.stdout.endswith(b"\n\n"):
        raise RunnerError("builder_stdout_framing_invalid")
    body = capture.stdout[:-1]
    if b"\n" in body or b"\r" in body:
        raise RunnerError("builder_stdout_contains_raw_line_break")
    summary = _load_canonical_json_object(body, "builder_stdout")
    expected = {
        "archive_filename": OUTPUT_CAPSULE_NAME,
        "authority_effect": "none",
        "capsule_member_count": 4,
        "capsule_sha256": capsule.sha256,
        "capsule_size_bytes": EXPECTED_CAPSULE_SIZE_BYTES,
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "ok": True,
        "protected_source_count": 7,
        "reference_environment_attestation": {
            "container_image": REFERENCE_CONTAINER_IMAGE,
            "sha256": REFERENCE_ATTESTATION_SHA256,
            "size_bytes": REFERENCE_ATTESTATION_SIZE_BYTES,
            "source": "outer_reference_environment_launcher",
            "verification_method": (
                "host_container_runtime_repo_digest_match_before_exact_digest_launch"
            ),
            "verified": True,
        },
        "result": "capsule_constructed_only",
        "tool": "build_pulsemech_device_ledger_reproduction_capsule_v0",
        "tool_source_path": CAPSULE_BUILDER_PATH,
        "tool_version": "0.1.0",
        "verifier_executed": False,
    }
    if summary != expected:
        raise RunnerError("builder_summary_mismatch")
    return summary


def _run_builder(
    *,
    construction_id: str,
    repository_root: Path,
    workspace: Path,
    python_executable: Path,
    attestation: ExternalAttestationSnapshot,
    protected: Mapping[str, SourceSnapshot],
) -> ConstructionObservation:
    output_directory = workspace / "builder-output"
    if os.path.lexists(output_directory):
        raise RunnerError("builder_output_preexists", construction_id)
    command = (
        os.fspath(python_executable),
        "-P",
        os.fspath(repository_root / CAPSULE_BUILDER_PATH),
        "--repository-root",
        os.fspath(repository_root),
        "--output-directory",
        os.fspath(output_directory),
        "--reference-environment-attestation",
        os.fspath(attestation.path),
    )
    capture = _run_process(
        command,
        cwd=repository_root,
        expected_exit_status=0,
    )
    output_path = output_directory / OUTPUT_CAPSULE_NAME
    capsule_payload = _read_builder_output(output_path)
    capsule = _inspect_capsule(capsule_payload, protected)
    summary = _validate_builder_summary(capture, capsule)
    return ConstructionObservation(
        construction_id,
        capture,
        summary,
        capsule,
    )


def _materialize_positive_members(
    workspace: Path,
    capsule: CapsuleObservation,
) -> tuple[Path, Path, Path, dict[str, bytes]]:
    materialized = {
        "ledger": capsule.members[CAPSULE_LEDGER_MEMBER_PATH],
        "verifier": capsule.members[CAPSULE_VERIFIER_MEMBER_PATH],
        "expected": capsule.members[CAPSULE_EXPECTED_REPORT_MEMBER_PATH],
    }
    ledger = workspace / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
    verifier = workspace / "verify_pulsemech_device_ledger_v0.py"
    expected = workspace / "expected-verification.json"
    _write_exact_file(ledger, materialized["ledger"])
    _write_exact_file(verifier, materialized["verifier"])
    _write_exact_file(expected, materialized["expected"])
    return ledger, verifier, expected, materialized


def _require_materialized_unchanged(
    paths_and_bytes: Mapping[Path, bytes],
) -> None:
    for path, expected in paths_and_bytes.items():
        payload, _ = _read_stable_regular_file(
            path,
            label=path.name,
            expected_size=len(expected),
            maximum_size=max(1, len(expected)),
        )
        if payload != expected:
            raise RunnerError("materialized_source_changed", path.name)


def _positive_report_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    try:
        checks = report["checks"]
        errors = report["errors"]
        failed = report["failed_check_ids"]
        subject = report["subject"]
        signatures = report["signature_verification"]
        tool = report["tool"]
        context = report["reproduction_context"]
        claim = report["claim_boundary"]
        authority = report["authority_boundary"]
        semantic = report["semantic_summary"]
    except (KeyError, TypeError) as exc:
        raise RunnerError("positive_report_surface_missing") from exc
    if not isinstance(checks, dict) or len(checks) != 49:
        raise RunnerError("positive_report_check_count_mismatch")
    if any(value != "passed" for value in checks.values()):
        raise RunnerError("positive_report_nonpassed_check")
    if errors != [] or failed != [] or report.get("failure_stage") is not None:
        raise RunnerError("positive_report_failure_surface_present")
    if report.get("ok") is not True:
        raise RunnerError("positive_report_not_ok")
    if report.get("result") != "verified_with_declared_unavailability":
        raise RunnerError("positive_report_result_mismatch")
    if report.get("record_status") != "synthetic_reference":
        raise RunnerError("positive_report_record_status_mismatch")
    if subject != {
        "carrier_file_name": "pulsemech_device_transition_ledger_reference_v0.pulseledger",
        "carrier_sha256": CANONICAL_LEDGER_SPEC.sha256,
        "carrier_size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
        "media_type": "application/zip",
        "package_format": "pulseledger_zip_v0",
    }:
        raise RunnerError("positive_report_subject_mismatch")
    if signatures["checkpoint"].get("signature_status") != "verified":
        raise RunnerError("positive_checkpoint_signature_not_verified")
    if signatures["package"].get("signature_status") != "verified":
        raise RunnerError("positive_package_signature_not_verified")
    if tool.get("producer_code_imported") is not False:
        raise RunnerError("positive_report_producer_code_imported")
    if tool.get("source_sha256") != STANDALONE_VERIFIER_SPEC.sha256:
        raise RunnerError("positive_report_verifier_identity_mismatch")
    if context.get("producer_environment_available_to_verifier") is not True:
        raise RunnerError("positive_report_producer_environment_mismatch")
    if context.get("reproduction_class") != "same_environment":
        raise RunnerError("positive_report_reproduction_class_mismatch")
    if context.get("verifier_implementation_relation") != (
        "separate_from_producer_code"
    ):
        raise RunnerError("positive_report_verifier_relation_mismatch")
    if claim.get("external_validation_claim") != "none":
        raise RunnerError("positive_report_external_validation_claim_mismatch")
    if authority.get("authority_effect") != "none":
        raise RunnerError("positive_report_authority_effect_mismatch")
    if semantic.get("declared_unavailability_present") is not True:
        raise RunnerError("positive_report_unavailability_mismatch")
    return {
        "authority_effect": "none",
        "checkpoint_signature_status": "verified",
        "check_count": 49,
        "declared_unavailability_present": True,
        "errors": [],
        "external_validation_claim": "none",
        "failed_check_ids": [],
        "failure_stage": None,
        "ok": True,
        "package_signature_status": "verified",
        "passed_check_count": 49,
        "producer_code_imported": False,
        "producer_environment_available_to_verifier": True,
        "record_status": "synthetic_reference",
        "reproduction_class": "same_environment",
        "result": "verified_with_declared_unavailability",
        "subject": {
            "carrier_file_name": (
                "pulsemech_device_transition_ledger_reference_v0.pulseledger"
            ),
            "carrier_sha256": CANONICAL_LEDGER_SPEC.sha256,
            "carrier_size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
        },
        "verifier_implementation_relation": "separate_from_producer_code",
    }


def _run_positive_verifier(
    *,
    run_id: str,
    construction: ConstructionObservation,
    workspace: Path,
    python_executable: Path,
) -> PositiveObservation:
    ledger, verifier, expected, materialized = _materialize_positive_members(
        workspace,
        construction.capsule,
    )
    expected_bytes = materialized["expected"]
    _load_canonical_json_object(expected_bytes, "canonical_expected_report")
    command = (
        os.fspath(python_executable),
        "-P",
        os.fspath(verifier),
        os.fspath(ledger),
        "--expected-observer-fingerprint",
        EXPECTED_OBSERVER_FINGERPRINT_SHA256,
        "--reproduction-class",
        "same_environment",
        "--producer-environment-available",
    )
    capture = _run_process(command, cwd=workspace, expected_exit_status=0)
    if capture.stderr != b"":
        raise RunnerError("positive_verifier_stderr_not_empty", run_id)
    if capture.stdout != expected_bytes:
        raise RunnerError("positive_verifier_stdout_mismatch", run_id)
    report = _load_canonical_json_object(capture.stdout, "positive_verifier_stdout")
    summary = _positive_report_summary(report)
    _require_materialized_unchanged(
        {
            ledger: materialized["ledger"],
            verifier: materialized["verifier"],
            expected: materialized["expected"],
        }
    )
    return PositiveObservation(
        run_id,
        construction.construction_id,
        capture,
        report,
        summary,
    )


def _mutate_package_signature(source: bytes) -> MutationObservation:
    if len(source) != CANONICAL_LEDGER_SPEC.size_bytes:
        raise RunnerError("mutation_source_size_mismatch")
    if sha256_bytes(source) != CANONICAL_LEDGER_SPEC.sha256:
        raise RunnerError("mutation_source_sha256_mismatch")
    parsed = _parse_stored_zip(
        source,
        expected_order=PULSELEDGER_MEMBER_ORDER,
        label="mutation_source_pulseledger",
        require_outer_profile=False,
    )
    target = parsed.member(PACKAGE_SIGNATURE_MEMBER_PATH)
    original_payload = parsed.member_bytes(PACKAGE_SIGNATURE_MEMBER_PATH)
    original_document = _load_canonical_json_object(
        original_payload,
        "package_signature_document",
    )
    signature = original_document.get("signature_base64")
    if not isinstance(signature, str) or not signature.startswith("O"):
        raise RunnerError("package_signature_mutation_precondition_failed")
    mutated_document = copy.deepcopy(original_document)
    mutated_document["signature_base64"] = "P" + signature[1:]
    mutated_payload = canonical_json_bytes(mutated_document)
    if len(mutated_payload) != len(original_payload):
        raise RunnerError("package_signature_mutation_size_changed")
    differences = [
        index
        for index, (before, after) in enumerate(
            zip(original_payload, mutated_payload)
        )
        if before != after
    ]
    if len(differences) != 1:
        raise RunnerError("package_signature_mutation_not_single_byte")
    before_without_signature = dict(original_document)
    after_without_signature = dict(mutated_document)
    del before_without_signature["signature_base64"]
    del after_without_signature["signature_base64"]
    if before_without_signature != after_without_signature:
        raise RunnerError("package_signature_subject_changed")

    mutable = bytearray(source)
    start = target.payload_offset
    mutable[start : start + target.payload_size] = mutated_payload
    new_crc32 = zlib.crc32(mutated_payload) & 0xFFFFFFFF
    struct.pack_into("<I", mutable, target.local_header_offset + 14, new_crc32)
    struct.pack_into("<I", mutable, target.central_header_offset + 16, new_crc32)
    mutated = bytes(mutable)
    if len(mutated) != len(source):
        raise RunnerError("mutated_carrier_size_changed")
    if mutated == source:
        raise RunnerError("mutated_carrier_unchanged")

    reparsed = _parse_stored_zip(
        mutated,
        expected_order=PULSELEDGER_MEMBER_ORDER,
        label="mutated_pulseledger",
        require_outer_profile=False,
    )
    if tuple(member.name for member in reparsed.members) != PULSELEDGER_MEMBER_ORDER:
        raise RunnerError("mutated_member_order_changed")
    for name in PULSELEDGER_MEMBER_ORDER:
        if name == PACKAGE_SIGNATURE_MEMBER_PATH:
            continue
        if reparsed.member_bytes(name) != parsed.member_bytes(name):
            raise RunnerError("mutation_changed_nontarget_member", name)
    reparsed_document = _load_canonical_json_object(
        reparsed.member_bytes(PACKAGE_SIGNATURE_MEMBER_PATH),
        "mutated_package_signature_document",
    )
    if reparsed_document != mutated_document:
        raise RunnerError("mutated_package_signature_content_mismatch")

    allowed_offsets = set(
        range(target.local_header_offset + 14, target.local_header_offset + 18)
    )
    allowed_offsets.update(
        range(target.central_header_offset + 16, target.central_header_offset + 20)
    )
    allowed_offsets.add(start + differences[0])
    observed_differences = {
        index
        for index, (before, after) in enumerate(zip(source, mutated))
        if before != after
    }
    if not observed_differences or not observed_differences.issubset(allowed_offsets):
        raise RunnerError("mutation_changed_unexpected_carrier_bytes")

    return MutationObservation(
        payload=mutated,
        sha256=sha256_bytes(mutated),
        source_sha256=sha256_bytes(source),
        inner_member_order=PULSELEDGER_MEMBER_ORDER,
    )


def _negative_report_summary(
    report: Mapping[str, Any],
    mutation: MutationObservation,
) -> dict[str, Any]:
    try:
        checks = report["checks"]
        errors = report["errors"]
        failed = report["failed_check_ids"]
        subject = report["subject"]
        tool = report["tool"]
        context = report["reproduction_context"]
        claim = report["claim_boundary"]
        authority = report["authority_boundary"]
    except (KeyError, TypeError) as exc:
        raise RunnerError("negative_report_surface_missing") from exc
    actual_expected_error = {
        "check_id": "package_signature_valid",
        "error_code": "signature_verification_failed",
        "member_path": PACKAGE_SIGNATURE_MEMBER_PATH,
        "record_sequence_index": None,
        "stage": "package_signature",
    }
    result_error = {
        "check_id": "package_signature_valid",
        "error_code": "signature_verification_failed",
        "member_path": PACKAGE_SIGNATURE_MEMBER_PATH,
        "stage": "package_signature",
    }
    if report.get("ok") is not False or report.get("result") != "rejected":
        raise RunnerError("negative_report_result_mismatch")
    if report.get("failure_stage") != "package_signature":
        raise RunnerError("negative_report_failure_stage_mismatch")
    if failed != ["package_signature_valid"]:
        raise RunnerError("negative_report_failed_check_set_mismatch")
    if errors != [actual_expected_error]:
        raise RunnerError("negative_report_error_mismatch")
    if not isinstance(checks, dict):
        raise RunnerError("negative_report_checks_not_object")
    required_preceding = {
        "zip_crc32_valid": "passed",
        "package_signature_document_valid": "passed",
        "package_signature_subject_valid": "passed",
    }
    for check_id, expected in required_preceding.items():
        if checks.get(check_id) != expected:
            raise RunnerError("negative_report_preceding_check_failed", check_id)
    if checks.get("package_signature_valid") != "failed":
        raise RunnerError("negative_report_target_check_not_failed")
    expected_subject = {
        "carrier_file_name": "pulsemech_device_transition_ledger_reference_v0.pulseledger",
        "carrier_sha256": mutation.sha256,
        "carrier_size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
        "media_type": "application/zip",
        "package_format": "pulseledger_zip_v0",
    }
    if subject != expected_subject:
        raise RunnerError("negative_report_subject_mismatch")
    if report.get("record_status") != "synthetic_reference":
        raise RunnerError("negative_report_record_status_mismatch")
    if tool.get("producer_code_imported") is not False:
        raise RunnerError("negative_report_producer_code_imported")
    if tool.get("source_sha256") != STANDALONE_VERIFIER_SPEC.sha256:
        raise RunnerError("negative_report_verifier_identity_mismatch")
    if context.get("verifier_implementation_relation") != (
        "separate_from_producer_code"
    ):
        raise RunnerError("negative_report_verifier_relation_mismatch")
    if claim.get("external_validation_claim") != "none":
        raise RunnerError("negative_report_external_validation_claim_mismatch")
    if authority.get("authority_effect") != "none":
        raise RunnerError("negative_report_authority_effect_mismatch")
    return {
        "authority_effect": "none",
        "error": result_error,
        "error_count": 1,
        "external_validation_claim": "none",
        "failed_check": {
            "check_id": "package_signature_valid",
            "result": "failed",
        },
        "failed_check_ids": ["package_signature_valid"],
        "failure_stage": "package_signature",
        "ok": False,
        "producer_code_imported": False,
        "record_status": "synthetic_reference",
        "required_preceding_checks": {
            "package_signature_document_valid": "passed",
            "package_signature_subject_valid": "passed",
            "zip_crc32_valid": "passed",
        },
        "result": "rejected",
        "subject": {
            "carrier_file_name": (
                "pulsemech_device_transition_ledger_reference_v0.pulseledger"
            ),
            "carrier_sha256": mutation.sha256,
            "carrier_size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
        },
        "subject_matches_mutated_artifact": True,
        "verifier_implementation_relation": "separate_from_producer_code",
    }


def _run_negative_verifier(
    *,
    capsule: CapsuleObservation,
    mutation: MutationObservation,
    workspace: Path,
    python_executable: Path,
) -> tuple[ProcessCapture, dict[str, Any], dict[str, Any]]:
    ledger = workspace / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
    verifier = workspace / "verify_pulsemech_device_ledger_v0.py"
    verifier_bytes = capsule.members[CAPSULE_VERIFIER_MEMBER_PATH]
    _write_exact_file(ledger, mutation.payload)
    _write_exact_file(verifier, verifier_bytes)
    command = (
        os.fspath(python_executable),
        "-P",
        os.fspath(verifier),
        os.fspath(ledger),
        "--expected-observer-fingerprint",
        EXPECTED_OBSERVER_FINGERPRINT_SHA256,
        "--reproduction-class",
        "same_environment",
        "--producer-environment-available",
    )
    capture = _run_process(command, cwd=workspace, expected_exit_status=2)
    if capture.stderr != b"":
        raise RunnerError("negative_verifier_stderr_not_empty")
    if capture.stdout.endswith(b"\n") or b"\r" in capture.stdout:
        raise RunnerError("negative_verifier_stdout_framing_invalid")
    report = _load_canonical_json_object(capture.stdout, "negative_verifier_stdout")
    summary = _negative_report_summary(report, mutation)
    _require_materialized_unchanged(
        {
            ledger: mutation.payload,
            verifier: verifier_bytes,
        }
    )
    return capture, report, summary


def _source_binding(spec: SourceSpec) -> dict[str, Any]:
    return {
        "byte_identity": "exact_repository_file_bytes",
        "git_blob_sha1": spec.git_blob_sha1,
        "path": spec.relative_path,
        "sha256": spec.sha256,
        "size_bytes": spec.size_bytes,
    }


def _tool_binding(
    spec: SourceSpec,
    *,
    implementation_role: str,
    tool_id: str,
) -> dict[str, Any]:
    binding = _source_binding(spec)
    binding.update(
        {
            "implementation_role": implementation_role,
            "tool_id": tool_id,
            "tool_version": "0.1.0",
        }
    )
    return binding


def _snapshot_bindings(specs: Sequence[SourceSpec]) -> list[dict[str, Any]]:
    return [_source_binding(spec) for spec in specs]


def _capsule_member_contract() -> dict[str, Any]:
    members = []
    for ordinal, capsule_path, source_path, size, digest, media_type, role in (
        CAPSULE_MEMBER_SPECS
    ):
        members.append(
            {
                "archive_ordinal": ordinal,
                "byte_identity": "exact_source_bytes",
                "capsule_path": capsule_path,
                "media_type": media_type,
                "role": role,
                "sha256": digest,
                "size_bytes": size,
                "source_path": source_path,
            }
        )
    return {
        "archive_filename": OUTPUT_CAPSULE_NAME,
        "capsule_member_count": 4,
        "capsule_size_bytes": EXPECTED_CAPSULE_SIZE_BYTES,
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "members": members,
        "payload_member_count": 3,
    }


def _builder_process_record(
    observation: ConstructionObservation,
) -> dict[str, Any]:
    return {
        "execution_relation": "separate_process",
        "exit_status": 0,
        "process_role": "deterministic_capsule_builder",
        "source_relation": "exact_repository_builder_bytes",
        "stderr": _empty_process_stream_identity(),
        "stdout": _process_stream_identity(
            observation.builder_capture.stdout,
            "canonical_json_then_single_lf",
        ),
        "summary": dict(observation.builder_summary),
    }


def _capsule_identity(observation: CapsuleObservation) -> dict[str, Any]:
    return {
        "archive_filename": OUTPUT_CAPSULE_NAME,
        "archive_profile_valid": True,
        "byte_identity": "exact_capsule_bytes",
        "capsule_member_count": 4,
        "member_contract_valid": True,
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "package_format": "pulsemech_device_ledger_reproduction_capsule_v0",
        "sha256": observation.sha256,
        "size_bytes": EXPECTED_CAPSULE_SIZE_BYTES,
    }


def _construction_record(
    observation: ConstructionObservation,
) -> dict[str, Any]:
    return {
        "builder_process": _builder_process_record(observation),
        "capsule": _capsule_identity(observation.capsule),
        "construction_id": observation.construction_id,
        "output_relation": "new_directory_outside_repository",
        "repository_access": "read_only",
        "workspace_role": "isolated_clean_workspace",
    }


def _positive_process_record(
    observation: PositiveObservation,
) -> dict[str, Any]:
    return {
        "artifact_relation": "capsule_carried_exact_pulseledger",
        "canonical_expected_report_bytes_equal": True,
        "execution_relation": "separate_process",
        "exit_status": 0,
        "expected_observer_fingerprint_sha256": (
            EXPECTED_OBSERVER_FINGERPRINT_SHA256
        ),
        "process_role": "standalone_device_ledger_verifier",
        "producer_verdict_trusted": False,
        "report": dict(observation.report_summary),
        "source_relation": "capsule_carried_exact_verifier",
        "stderr": _empty_process_stream_identity(),
        "stdout": _process_stream_identity(
            observation.capture.stdout,
            "canonical_json_no_trailing_newline",
        ),
    }


def _positive_reproduction_record(
    observation: PositiveObservation,
) -> dict[str, Any]:
    return {
        "capsule_construction_id": observation.construction_id,
        "materialization": {
            "artifact_member_path": CAPSULE_LEDGER_MEMBER_PATH,
            "bounded_known_members_only": True,
            "exact_member_bytes": True,
            "expected_report_member_path": CAPSULE_EXPECTED_REPORT_MEMBER_PATH,
            "materialized_member_count": 3,
            "reused_from_other_positive_run": False,
            "verifier_member_path": CAPSULE_VERIFIER_MEMBER_PATH,
            "workspace_role": "isolated_temporary_materialization",
        },
        "run_id": observation.run_id,
        "verifier_process": _positive_process_record(observation),
    }


def _build_result(
    *,
    specs: Sequence[SourceSpec],
    before: Mapping[str, SourceSnapshot],
    after: Mapping[str, SourceSnapshot],
    construction_a: ConstructionObservation,
    construction_b: ConstructionObservation,
    positive_a: PositiveObservation,
    positive_b: PositiveObservation,
    mutation: MutationObservation,
    negative_capture: ProcessCapture,
    negative_summary: Mapping[str, Any],
) -> dict[str, Any]:
    specs_by_path = {spec.relative_path: spec for spec in specs}
    runner_spec = specs_by_path[TOOL_SOURCE_PATH]
    if tuple(before) != tuple(after):
        raise RunnerError("protected_source_snapshot_order_changed")
    if any(before[path].payload != after[path].payload for path in before):
        raise RunnerError("protected_source_snapshot_bytes_changed")
    if construction_a.capsule.payload != construction_b.capsule.payload:
        raise RunnerError("capsule_a_b_bytes_differ")
    if construction_a.builder_capture.stdout != construction_b.builder_capture.stdout:
        raise RunnerError("builder_stdout_a_b_differ")
    if positive_a.capture.stdout != positive_b.capture.stdout:
        raise RunnerError("positive_stdout_a_b_differ")
    expected_report = before[CANONICAL_EXPECTED_REPORT_PATH].payload
    if positive_a.capture.stdout != expected_report:
        raise RunnerError("positive_stdout_not_canonical_expected_report")

    canonical_capsule = construction_a.capsule
    identity_bindings = {
        "all_exact_identities_verified": True,
        "canonical_expected_positive_report": _source_binding(
            CANONICAL_EXPECTED_REPORT_SPEC
        ),
        "canonical_manifest": _source_binding(CANONICAL_MANIFEST_SPEC),
        "canonical_pulseledger": _source_binding(CANONICAL_LEDGER_SPEC),
        "canonicalization_profile": _source_binding(
            CANONICALIZATION_PROFILE_SPEC
        ),
        "capsule_builder": _tool_binding(
            CAPSULE_BUILDER_SPEC,
            implementation_role="deterministic_capsule_construction_only",
            tool_id="build_pulsemech_device_ledger_reproduction_capsule_v0",
        ),
        "capsule_contract": _source_binding(CAPSULE_CONTRACT_SPEC),
        "manifest_schema": _source_binding(MANIFEST_SCHEMA_SPEC),
        "reproduction_result_schema": _source_binding(RESULT_SCHEMA_SPEC),
        "reproduction_runner": _tool_binding(
            runner_spec,
            implementation_role="orchestration_only",
            tool_id=TOOL_NAME,
        ),
        "standalone_verifier": _tool_binding(
            STANDALONE_VERIFIER_SPEC,
            implementation_role="separate_from_producer_code",
            tool_id="verify_pulsemech_device_ledger_v0",
        ),
    }

    result = {
        "authority_boundary": {
            "authority_effect": "none",
            "capsule_is_release_authority": False,
            "changes_release_authority": False,
            "creates_device_control_authority": False,
            "creates_gate_result": False,
            "creates_release_decision": False,
            "external_operator_approval_required": False,
            "reproduction_result_is_release_authority": False,
        },
        "canonical_capsule": {
            "byte_identity": "exact_canonical_capsule_bytes",
            "bytes_equal_capsule_a": True,
            "bytes_equal_capsule_b": True,
            "git_blob_sha1": canonical_capsule.git_blob_sha1,
            "repository_path": CANONICAL_CAPSULE_REPOSITORY_PATH,
            "selected_construction_id": "capsule_a",
            "sha256": canonical_capsule.sha256,
            "size_bytes": EXPECTED_CAPSULE_SIZE_BYTES,
        },
        "canonical_result_storage": {
            "canonicalization": "pulsemech_device_canonical_json_v0",
            "cr_characters": 0,
            "generated_or_volatile_fields": "forbidden",
            "identity_location": "outside_result_to_avoid_self_reference",
            "lf_characters": 0,
            "repository_path": CANONICAL_RESULT_REPOSITORY_PATH,
            "result_self_hash": "forbidden",
            "result_self_size": "forbidden",
            "stored_bytes": "must_equal_canonical_reserialization",
            "strict_utf8": True,
            "trailing_newline": False,
            "utf8_bom": "absent",
        },
        "capsule_constructions": {
            "capsule_a": _construction_record(construction_a),
            "capsule_b": _construction_record(construction_b),
            "construction_count": 2,
            "isolation": {
                "capsule_a_computed_archive_bytes_reused_by_b": False,
                "capsule_a_materialized_members_reused_by_b": False,
                "capsule_a_output_reused_by_b": False,
                "capsule_a_temporary_files_reused_by_b": False,
                "separate_builder_processes": True,
                "separate_output_directories": True,
                "separate_temporary_workspaces": True,
            },
        },
        "capsule_format": "pulsemech_device_ledger_reproduction_capsule_v0",
        "capsule_member_contract": _capsule_member_contract(),
        "carrier_class": "diagnostic_shadow",
        "claim_boundary": {
            "causal_completion_claim": "none",
            "continuous_monitoring_claim": "none",
            "device_security_claim": "none",
            "external_validation_claim": "none",
            "hardware_backed_identity_claim": "none",
            "identity_scope": "fixture_installation",
            "key_origin_profile": "fixture_software_p256",
            "live_observation_claim": "none",
            "malware_claim": "none",
            "physical_measurement_claim": "none",
            "production_device_claim": "none",
            "production_readiness_claim": "none",
            "universal_cross_platform_reproducibility_claim": "none",
        },
        "document_type": "pulsemech_device_ledger_reproduction_result",
        "execution_boundary": {
            "bounded_reproduction_phase": "reference_container",
            "container_image_identity_attestation": (
                "host_container_runtime_repo_digest_match_before_exact_digest_launch"
            ),
            "container_image_identity_verified": True,
            "container_image_pull_relation": (
                "completed_before_bounded_reproduction_phase"
            ),
            "dependency_installation_during_reproduction": "forbidden",
            "network_mode": "none",
            "output_mount": "separate_writable",
            "repository_mount": "read_only",
            "runtime_downloads_during_reproduction": "forbidden",
            "temporary_workspace_relation": "isolated_per_construction_no_reuse",
        },
        "expected_observer_fingerprint_sha256": (
            EXPECTED_OBSERVER_FINGERPRINT_SHA256
        ),
        "identity_bindings": identity_bindings,
        "implementation_boundary": {
            "existing_verifier_modification": "forbidden",
            "new_verifier": "none",
            "producer_verdict_trusted": False,
            "reproduction_result_role": (
                "orchestration_evidence_not_verifier_verdict"
            ),
            "runner_role": "orchestration_only",
            "verification_semantics_change": "none",
            "verifier_execution": "separate_process",
            "verifier_import_by_runner": "forbidden",
        },
        "negative_reproduction": {
            "artifact_relation": "isolated_mutated_pulseledger_from_capsule_a",
            "earlier_failure_satisfies_contract": False,
            "exact_failure_satisfied": True,
            "mutation_relation": "targeted_mutation_recorded_by_result",
            "verifier_process": {
                "execution_relation": "separate_process",
                "exit_status": 2,
                "expected_observer_fingerprint_sha256": (
                    EXPECTED_OBSERVER_FINGERPRINT_SHA256
                ),
                "process_role": "standalone_device_ledger_verifier",
                "producer_verdict_trusted": False,
                "report": dict(negative_summary),
                "source_relation": "capsule_carried_exact_verifier",
                "stderr": _empty_process_stream_identity(),
                "stdout": _process_stream_identity(
                    negative_capture.stdout,
                    "canonical_json_no_trailing_newline",
                ),
            },
        },
        "ok": True,
        "positive_reproductions": [
            _positive_reproduction_record(positive_a),
            _positive_reproduction_record(positive_b),
        ],
        "proof_scope": "bounded_reference_reproduction",
        "protected_source_preservation": {
            "after": _snapshot_bindings(specs),
            "all_exact_bytes_unchanged": True,
            "all_git_blob_identities_unchanged": True,
            "before": _snapshot_bindings(specs),
            "drift_detected": False,
            "repository_source_write_attempted": False,
            "source_count": EXPECTED_PROTECTED_SOURCE_COUNT,
        },
        "record_status": "synthetic_reference",
        "reference_environment": copy.deepcopy(REFERENCE_ENVIRONMENT),
        "reference_environment_attestation": {
            "attestation": copy.deepcopy(REFERENCE_ATTESTATION),
            "builder_admission": "verified_before_construction",
            "byte_identity": "exact_external_attestation_bytes",
            "sha256": REFERENCE_ATTESTATION_SHA256,
            "size_bytes": REFERENCE_ATTESTATION_SIZE_BYTES,
            "source_relation": "outer_reference_environment_launcher",
        },
        "repeated_construction": {
            "builder_stdout_bytes_equal": True,
            "canonical_pulseledger_bytes_equal_across_capsules": True,
            "canonical_pulseledger_bytes_equal_checked_in_source": True,
            "capsule_bytes_equal": True,
            "capsule_sha256_equal": True,
            "capsule_size_equal": True,
            "member_bytes_equal": True,
            "member_inventory_equal": True,
            "member_order_equal": True,
            "positive_report_bytes_equal": True,
            "positive_reports_equal_canonical_expected_report": True,
            "reference_environment_attestation_bytes_equal": True,
        },
        "repository_context": {
            "containing_commit_binding": "excluded_to_avoid_circularity",
            "payload_source_commit_sha": (
                "0108e2c0da98c8a1fe5e739aa0f137ba6a3464e1"
            ),
            "pr_position": 2,
            "repository": "HKati/pulse-release-gates-0.1",
            "required_base_commit_sha": (
                "722fe4e85acfaac67c283862645ac9e42c831236"
            ),
            "work_order_issue_number": 2850,
        },
        "result": "bounded_reference_reproduction_completed",
        "result_role": "orchestration_evidence",
        "schema_version": "pulsemech_device_ledger_reproduction_result_v0",
        "targeted_mutation": {
            "canonical_reference_artifact_mutated": False,
            "changed_properties": [
                "package_signature_content",
                "package_ecdsa_equation_result",
                "carrier_sha256",
            ],
            "crc32_repair": {
                "central_directory_crc32_recomputed": True,
                "local_header_crc32_recomputed": True,
            },
            "field": "signature_base64",
            "inner_member_order": list(mutation.inner_member_order),
            "mutation_class": "replace_first_character",
            "mutation_workspace": "isolated_temporary_copy",
            "mutated_artifact": {
                "byte_identity": "exact_mutated_pulseledger_bytes",
                "file_name": (
                    "pulsemech_device_transition_ledger_reference_v0.pulseledger"
                ),
                "sha256": mutation.sha256,
                "size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
            },
            "original_character": "O",
            "positive_capsules_mutated": False,
            "preservation": {
                "canonical_package_signature_json_structure_preserved": True,
                "carrier_size_preserved": True,
                "matching_crc32_fields_preserved": True,
                "member_count_preserved": True,
                "member_names_preserved": True,
                "member_order_preserved": True,
                "non_target_member_bytes_preserved": True,
                "package_manifest_binding_preserved": True,
                "package_signature_subject_preserved": True,
                "valid_zip_structure_preserved": True,
            },
            "replacement_character": "P",
            "source_artifact": {
                "byte_identity": "exact_canonical_pulseledger_bytes",
                "file_name": (
                    "pulsemech_device_transition_ledger_reference_v0.pulseledger"
                ),
                "sha256": CANONICAL_LEDGER_SPEC.sha256,
                "size_bytes": CANONICAL_LEDGER_SPEC.size_bytes,
            },
            "source_capsule_construction_id": "capsule_a",
            "target_capsule_member_path": CAPSULE_LEDGER_MEMBER_PATH,
            "target_inner_member_path": PACKAGE_SIGNATURE_MEMBER_PATH,
        },
    }
    return result


def _validate_and_render_result(
    result: Mapping[str, Any],
    schema_payload: bytes,
) -> bytes:
    schema = _load_strict_json_object(schema_payload, "reproduction_result_schema")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise RunnerError("reproduction_result_schema_dialect_mismatch")
    if schema.get("$id") != (
        "https://github.com/HKati/pulse-release-gates-0.1/"
        "schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json"
    ):
        raise RunnerError("reproduction_result_schema_id_mismatch")
    try:
        _validate_json_schema(result, schema, root=schema)
    except SchemaMismatch as exc:
        raise RunnerError("reproduction_result_schema_validation_failed", str(exc))
    rendered = canonical_json_bytes(dict(result))
    if rendered.startswith(b"\xef\xbb\xbf"):
        raise RunnerError("reproduction_result_bom_present")
    if b"\r" in rendered or b"\n" in rendered:
        raise RunnerError("reproduction_result_raw_line_break_present")
    if canonical_json_bytes(
        _load_strict_json_object(rendered, "rendered_reproduction_result")
    ) != rendered:
        raise RunnerError("reproduction_result_roundtrip_failed")
    return rendered


def _write_publish_file(
    directory_descriptor: int,
    name: str,
    payload: bytes,
) -> FileSystemIdentity:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_descriptor)
    except OSError as exc:
        raise RunnerError("publish_file_create_failed", name) from exc
    try:
        identity = _filesystem_identity(os.fstat(descriptor))
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            written = handle.write(payload)
            if written != len(payload):
                raise RunnerError("publish_file_write_incomplete", name)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o444)
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return identity


def _require_directory_entry_set(
    directory_descriptor: int,
    expected: Sequence[str],
    code: str,
) -> None:
    try:
        observed = sorted(os.listdir(directory_descriptor))
    except OSError as exc:
        raise RunnerError(code) from exc
    if observed != sorted(expected):
        raise RunnerError(code)


def _read_publish_file(
    directory_descriptor: int,
    name: str,
    expected: bytes,
    identity: FileSystemIdentity,
) -> None:
    metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RunnerError("published_file_state_invalid", name)
    if stat.S_IMODE(metadata.st_mode) != 0o444:
        raise RunnerError("published_file_mode_mismatch", name)
    if _filesystem_identity(metadata) != identity:
        raise RunnerError("published_file_identity_mismatch", name)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    try:
        before = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(len(expected) + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if _stable_stat(before) != _stable_stat(after):
        raise RunnerError("published_file_changed_during_read", name)
    if payload != expected:
        raise RunnerError("published_file_readback_mismatch", name)


def _publish_outputs(
    *,
    destination: Path,
    parent_descriptor: int,
    parent_identity: FileSystemIdentity,
    capsule: bytes,
    result: bytes,
    repository_root: Path,
    specs: Sequence[SourceSpec],
    baseline: Mapping[str, SourceSnapshot],
    attestation: ExternalAttestationSnapshot,
) -> None:
    _require_open_directory_path_identity(
        destination.parent,
        parent_descriptor,
        parent_identity,
        "output_parent",
    )
    staging_name = (
        f".{destination.name}.{TOOL_NAME}.{secrets.token_hex(16)}.publish.tmp"
    )
    if os.path.lexists(destination.parent / staging_name):
        raise RunnerError("publish_staging_collision")
    staging_fd = -1
    staging_identity: FileSystemIdentity | None = None
    published = False
    try:
        staging_fd, staging_identity = _mkdir_owned(
            parent_descriptor,
            staging_name,
        )
        capsule_identity = _write_publish_file(
            staging_fd,
            OUTPUT_CAPSULE_NAME,
            capsule,
        )
        result_identity = _write_publish_file(
            staging_fd,
            OUTPUT_RESULT_NAME,
            result,
        )
        _read_publish_file(
            staging_fd,
            OUTPUT_CAPSULE_NAME,
            capsule,
            capsule_identity,
        )
        _read_publish_file(
            staging_fd,
            OUTPUT_RESULT_NAME,
            result,
            result_identity,
        )
        _require_directory_entry_set(
            staging_fd,
            (OUTPUT_CAPSULE_NAME, OUTPUT_RESULT_NAME),
            "publish_staging_entry_set_mismatch",
        )
        os.fchmod(staging_fd, 0o555)
        _fsync_directory(staging_fd, "publish_staging_fsync_failed")
        _require_sources_unchanged(repository_root, specs, baseline)
        _require_attestation_unchanged(attestation, repository_root)
        _require_open_directory_path_identity(
            destination.parent,
            parent_descriptor,
            parent_identity,
            "output_parent",
        )
        _rename_directory_noreplace(
            parent_descriptor,
            staging_name,
            destination.name,
        )
        published = True
        _fsync_directory(parent_descriptor, "output_parent_fsync_failed")
        published_metadata = os.stat(
            destination.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if _filesystem_identity(published_metadata) != staging_identity:
            raise RunnerError("published_output_directory_identity_mismatch")
        if stat.S_IMODE(published_metadata.st_mode) != 0o555:
            raise RunnerError("published_output_directory_mode_mismatch")
        _require_directory_entry_set(
            staging_fd,
            (OUTPUT_CAPSULE_NAME, OUTPUT_RESULT_NAME),
            "published_output_entry_set_mismatch",
        )
        _read_publish_file(
            staging_fd,
            OUTPUT_CAPSULE_NAME,
            capsule,
            capsule_identity,
        )
        _read_publish_file(
            staging_fd,
            OUTPUT_RESULT_NAME,
            result,
            result_identity,
        )
        _require_sources_unchanged(repository_root, specs, baseline)
        _require_attestation_unchanged(attestation, repository_root)
        _require_open_directory_path_identity(
            destination.parent,
            parent_descriptor,
            parent_identity,
            "output_parent",
        )
    except BaseException:
        if staging_fd >= 0 and staging_identity is not None:
            cleanup_name = destination.name if published else staging_name
            try:
                _remove_named_owned_directory(
                    parent_descriptor=parent_descriptor,
                    directory_descriptor=staging_fd,
                    directory_name=cleanup_name,
                    directory_identity=staging_identity,
                )
                _fsync_directory(
                    parent_descriptor,
                    "output_parent_cleanup_fsync_failed",
                )
            except BaseException:
                pass
        raise
    finally:
        if staging_fd >= 0:
            os.close(staging_fd)


def _success_summary(capsule: bytes, result: bytes) -> dict[str, Any]:
    return {
        "authority_effect": "none",
        "capsule_filename": OUTPUT_CAPSULE_NAME,
        "capsule_sha256": sha256_bytes(capsule),
        "capsule_size_bytes": len(capsule),
        "ok": True,
        "result": "bounded_reference_reproduction_completed",
        "result_filename": OUTPUT_RESULT_NAME,
        "result_sha256": sha256_bytes(result),
        "result_size_bytes": len(result),
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }


def _failure_summary(error: RunnerError) -> dict[str, Any]:
    output: dict[str, Any] = {
        "authority_effect": "none",
        "error_code": error.code,
        "ok": False,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }
    if error.context is not None:
        output["error_context"] = error.context
    return output


def run_reproduction(
    *,
    repository_root: Path,
    output_directory: Path,
    reference_environment_attestation: Path,
) -> tuple[bytes, bytes]:
    _validate_implementation_constants()
    root = _resolve_repository_root(repository_root)
    _require_repository_working_directory(root)
    attestation = _read_reference_attestation(
        reference_environment_attestation,
        root,
    )
    destination, output_parent = _resolve_output_destination(
        output_directory,
        root,
        attestation,
    )
    parent_fd = -1
    parent_identity: FileSystemIdentity | None = None
    workspace_fd = -1
    workspace_identity: FileSystemIdentity | None = None
    workspace_name = (
        f".{destination.name}.{TOOL_NAME}.{secrets.token_hex(16)}.work.tmp"
    )
    try:
        parent_fd, parent_identity = _open_directory_nofollow(
            output_parent,
            "output_parent",
        )
        python_executable = _verify_reference_runtime(
            root,
            attestation,
            output_parent,
            parent_fd,
            parent_identity,
        )
        specs = _protected_source_specs(root)
        before = _read_protected_sources(root, specs)
        schema_payload = before[RESULT_SCHEMA_PATH].payload
        canonical_expected_report = before[
            CANONICAL_EXPECTED_REPORT_PATH
        ].payload
        _positive_report_summary(
            _load_canonical_json_object(
                canonical_expected_report,
                "canonical_expected_report",
            )
        )
        _require_open_directory_path_identity(
            output_parent,
            parent_fd,
            parent_identity,
            "output_parent",
        )
        if os.path.lexists(output_parent / workspace_name):
            raise RunnerError("workspace_collision")
        workspace_fd, workspace_identity = _mkdir_owned(parent_fd, workspace_name)
        workspace_root = output_parent / workspace_name

        construction_a_workspace = _create_child_directory(
            workspace_root,
            "construction-a",
        )
        construction_b_workspace = _create_child_directory(
            workspace_root,
            "construction-b",
        )
        construction_a = _run_builder(
            construction_id="capsule_a",
            repository_root=root,
            workspace=construction_a_workspace,
            python_executable=python_executable,
            attestation=attestation,
            protected=before,
        )
        _require_sources_unchanged(root, specs, before)
        _require_attestation_unchanged(attestation, root)
        construction_b = _run_builder(
            construction_id="capsule_b",
            repository_root=root,
            workspace=construction_b_workspace,
            python_executable=python_executable,
            attestation=attestation,
            protected=before,
        )
        if construction_a.capsule.payload != construction_b.capsule.payload:
            raise RunnerError("capsule_a_b_bytes_differ")
        if construction_a.builder_capture.stdout != construction_b.builder_capture.stdout:
            raise RunnerError("builder_stdout_a_b_differ")

        positive_a_workspace = _create_child_directory(
            workspace_root,
            "positive-a",
        )
        positive_b_workspace = _create_child_directory(
            workspace_root,
            "positive-b",
        )
        positive_a = _run_positive_verifier(
            run_id="positive_a",
            construction=construction_a,
            workspace=positive_a_workspace,
            python_executable=python_executable,
        )
        positive_b = _run_positive_verifier(
            run_id="positive_b",
            construction=construction_b,
            workspace=positive_b_workspace,
            python_executable=python_executable,
        )
        if positive_a.capture.stdout != positive_b.capture.stdout:
            raise RunnerError("positive_stdout_a_b_differ")

        mutation = _mutate_package_signature(
            construction_a.capsule.members[CAPSULE_LEDGER_MEMBER_PATH]
        )
        negative_workspace = _create_child_directory(
            workspace_root,
            "negative",
        )
        negative_capture, _, negative_summary = _run_negative_verifier(
            capsule=construction_a.capsule,
            mutation=mutation,
            workspace=negative_workspace,
            python_executable=python_executable,
        )

        after = _require_sources_unchanged(root, specs, before)
        _require_attestation_unchanged(attestation, root)
        result_object = _build_result(
            specs=specs,
            before=before,
            after=after,
            construction_a=construction_a,
            construction_b=construction_b,
            positive_a=positive_a,
            positive_b=positive_b,
            mutation=mutation,
            negative_capture=negative_capture,
            negative_summary=negative_summary,
        )
        result_bytes = _validate_and_render_result(result_object, schema_payload)
        capsule_bytes = construction_a.capsule.payload

        _remove_named_owned_directory(
            parent_descriptor=parent_fd,
            directory_descriptor=workspace_fd,
            directory_name=workspace_name,
            directory_identity=workspace_identity,
        )
        os.close(workspace_fd)
        workspace_fd = -1
        _fsync_directory(parent_fd, "output_parent_workspace_cleanup_fsync_failed")

        _publish_outputs(
            destination=destination,
            parent_descriptor=parent_fd,
            parent_identity=parent_identity,
            capsule=capsule_bytes,
            result=result_bytes,
            repository_root=root,
            specs=specs,
            baseline=before,
            attestation=attestation,
        )
        return capsule_bytes, result_bytes
    except BaseException:
        if (
            parent_fd >= 0
            and workspace_fd >= 0
            and workspace_identity is not None
        ):
            try:
                _remove_named_owned_directory(
                    parent_descriptor=parent_fd,
                    directory_descriptor=workspace_fd,
                    directory_name=workspace_name,
                    directory_identity=workspace_identity,
                )
                _fsync_directory(
                    parent_fd,
                    "output_parent_workspace_failure_cleanup_fsync_failed",
                )
            except BaseException:
                pass
        raise
    finally:
        if workspace_fd >= 0:
            os.close(workspace_fd)
        if parent_fd >= 0:
            os.close(parent_fd)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the bounded PULSEmech Device Ledger Reproduction Capsule "
            "v0 proof using two isolated Capsule constructions, two exact "
            "positive standalone-verifier runs, and one targeted fail-closed "
            "package-signature mutation."
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Exact read-only repository root; default is the current directory.",
    )
    parser.add_argument(
        "--output-directory",
        required=True,
        help=(
            "New output directory on the separate writable output mount. The "
            "canonical Capsule and canonical reproduction result are published "
            "inside it only after the complete proof succeeds."
        ),
    )
    parser.add_argument(
        "--reference-environment-attestation",
        required=True,
        help=(
            "Exact read-only canonical outer-launcher attestation created only "
            "after host-runtime RepoDigest verification and exact-digest launch "
            "selection."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    os.umask(0o077)
    args = parse_args(argv)
    try:
        capsule, result = run_reproduction(
            repository_root=Path(args.repository_root),
            output_directory=Path(args.output_directory),
            reference_environment_attestation=Path(
                args.reference_environment_attestation
            ),
        )
        sys.stdout.buffer.write(
            canonical_json_bytes(_success_summary(capsule, result)) + b"\n"
        )
        return 0
    except RunnerError as exc:
        sys.stderr.buffer.write(
            canonical_json_bytes(_failure_summary(exc)) + b"\n"
        )
        return 2
    except Exception as exc:
        error = RunnerError(
            "unexpected_bounded_runner_failure",
            str(getattr(exc, "errno", "none")),
        )
        sys.stderr.buffer.write(
            canonical_json_bytes(_failure_summary(error)) + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
