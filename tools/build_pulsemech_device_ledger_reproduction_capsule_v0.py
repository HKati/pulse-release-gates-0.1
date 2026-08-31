#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import io
import json
import os
import platform
import secrets
import stat
import struct
import sys
import sysconfig
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

TOOL_NAME = "build_pulsemech_device_ledger_reproduction_capsule_v0"
TOOL_VERSION = "0.1.0"
TOOL_SOURCE_PATH = (
    "tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py"
)

OUTPUT_CAPSULE_NAME = "pulsemech_device_ledger_reproduction_capsule_v0.zip"

MANIFEST_SCHEMA_PATH = (
    "schemas/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
)
CAPSULE_CONTRACT_PATH = (
    "contracts/pulsemech_device_ledger_reproduction_capsule_v0.json"
)
CANONICAL_MANIFEST_SOURCE_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json"
)
CANONICALIZATION_PROFILE_PATH = (
    "contracts/pulsemech_device_canonical_json_v0.json"
)
CANONICAL_LEDGER_SOURCE_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
STANDALONE_VERIFIER_SOURCE_PATH = "tools/verify_pulsemech_device_ledger_v0.py"
EXPECTED_REPORT_SOURCE_PATH = (
    "examples/device_transition_ledger/"
    "pulsemech_device_transition_ledger_reference_verification_v0.json"
)

MANIFEST_MEMBER_PATH = (
    "manifest/"
    "pulsemech_device_ledger_reproduction_capsule_manifest_v0.json"
)
CANONICAL_LEDGER_MEMBER_PATH = (
    "artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
STANDALONE_VERIFIER_MEMBER_PATH = (
    "verifier/verify_pulsemech_device_ledger_v0.py"
)
EXPECTED_REPORT_MEMBER_PATH = (
    "expected/"
    "pulsemech_device_transition_ledger_reference_verification_v0.json"
)

EXPECTED_OBSERVER_FINGERPRINT_SHA256 = (
    "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
)

FIXED_MEMBER_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_DOS_TIME = 0
FIXED_DOS_DATE = 33
FIXED_CREATOR_SYSTEM = 3
FIXED_CREATOR_VERSION = 20
FIXED_VERSION_NEEDED = 20
FIXED_FILE_MODE = stat.S_IFREG | 0o644
FIXED_EXTERNAL_ATTRIBUTES = FIXED_FILE_MODE << 16
FIXED_INTERNAL_ATTRIBUTES = 0
FIXED_GENERAL_PURPOSE_FLAGS = 0
FIXED_COMPRESSION_METHOD = zipfile.ZIP_STORED
FIXED_COMPRESSION_METHOD_CODE = 0
FIXED_DISK_NUMBER = 0

LOCAL_FILE_HEADER_SIGNATURE = 0x04034B50
CENTRAL_DIRECTORY_HEADER_SIGNATURE = 0x02014B50
END_OF_CENTRAL_DIRECTORY_SIGNATURE = 0x06054B50
LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
CENTRAL_DIRECTORY_HEADER = struct.Struct("<IHHHHHHIIIHHHHHII")
END_OF_CENTRAL_DIRECTORY = struct.Struct("<IHHHHIIH")


class BuildError(RuntimeError):
    def __init__(self, code: str, context: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


class _DuplicateJSONKey(ValueError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    relative_path: str
    size_bytes: int
    sha256: str
    git_blob_sha1: str | None = None


@dataclass(frozen=True)
class MemberSpec:
    archive_ordinal: int
    capsule_path: str
    source_path: str
    size_bytes: int
    sha256: str
    media_type: str
    role: str


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
class FileSystemIdentity:
    device: int
    inode: int


MANIFEST_SCHEMA_SPEC = SourceSpec(
    relative_path=MANIFEST_SCHEMA_PATH,
    size_bytes=32581,
    sha256="a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c",
    git_blob_sha1="6a0dabff2e5f725c6ef8e586f9cae7fff566030b",
)
CAPSULE_CONTRACT_SPEC = SourceSpec(
    relative_path=CAPSULE_CONTRACT_PATH,
    size_bytes=15947,
    sha256="ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67",
    git_blob_sha1="d15fddbe9250de0ed76b3b7ebb7d679383a867b4",
)
CANONICAL_MANIFEST_SPEC = SourceSpec(
    relative_path=CANONICAL_MANIFEST_SOURCE_PATH,
    size_bytes=8989,
    sha256="cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf",
    git_blob_sha1="b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b",
)
CANONICALIZATION_PROFILE_SPEC = SourceSpec(
    relative_path=CANONICALIZATION_PROFILE_PATH,
    size_bytes=2719,
    sha256="ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
)
CANONICAL_LEDGER_SPEC = SourceSpec(
    relative_path=CANONICAL_LEDGER_SOURCE_PATH,
    size_bytes=133568,
    sha256="a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3",
)
STANDALONE_VERIFIER_SPEC = SourceSpec(
    relative_path=STANDALONE_VERIFIER_SOURCE_PATH,
    size_bytes=126419,
    sha256="0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7",
)
EXPECTED_REPORT_SPEC = SourceSpec(
    relative_path=EXPECTED_REPORT_SOURCE_PATH,
    size_bytes=15328,
    sha256="5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4",
)

PROTECTED_SOURCE_SPECS: tuple[SourceSpec, ...] = (
    MANIFEST_SCHEMA_SPEC,
    CAPSULE_CONTRACT_SPEC,
    CANONICAL_MANIFEST_SPEC,
    CANONICALIZATION_PROFILE_SPEC,
    CANONICAL_LEDGER_SPEC,
    STANDALONE_VERIFIER_SPEC,
    EXPECTED_REPORT_SPEC,
)

CAPSULE_MEMBER_SPECS: tuple[MemberSpec, ...] = (
    MemberSpec(
        archive_ordinal=1,
        capsule_path=MANIFEST_MEMBER_PATH,
        source_path=CANONICAL_MANIFEST_SOURCE_PATH,
        size_bytes=CANONICAL_MANIFEST_SPEC.size_bytes,
        sha256=CANONICAL_MANIFEST_SPEC.sha256,
        media_type="application/json",
        role="capsule_manifest",
    ),
    MemberSpec(
        archive_ordinal=2,
        capsule_path=CANONICAL_LEDGER_MEMBER_PATH,
        source_path=CANONICAL_LEDGER_SOURCE_PATH,
        size_bytes=CANONICAL_LEDGER_SPEC.size_bytes,
        sha256=CANONICAL_LEDGER_SPEC.sha256,
        media_type="application/zip",
        role="canonical_pulseledger",
    ),
    MemberSpec(
        archive_ordinal=3,
        capsule_path=STANDALONE_VERIFIER_MEMBER_PATH,
        source_path=STANDALONE_VERIFIER_SOURCE_PATH,
        size_bytes=STANDALONE_VERIFIER_SPEC.size_bytes,
        sha256=STANDALONE_VERIFIER_SPEC.sha256,
        media_type="text/x-python",
        role="standalone_verifier",
    ),
    MemberSpec(
        archive_ordinal=4,
        capsule_path=EXPECTED_REPORT_MEMBER_PATH,
        source_path=EXPECTED_REPORT_SOURCE_PATH,
        size_bytes=EXPECTED_REPORT_SPEC.size_bytes,
        sha256=EXPECTED_REPORT_SPEC.sha256,
        media_type="application/json",
        role="canonical_expected_positive_report",
    ),
)

CAPSULE_MEMBER_ORDER: tuple[str, ...] = tuple(
    spec.capsule_path for spec in CAPSULE_MEMBER_SPECS
)

EXPECTED_ARCHIVE_PROFILE: dict[str, Any] = {
    "allow_zip64": False,
    "archive_comment": "empty",
    "archive_format": "zip",
    "central_directory_start_disk_number": 0,
    "central_directory_version_made_by": 788,
    "central_directory_version_needed": 20,
    "compression_level": "not_applicable_for_stored",
    "compression_method": "ZIP_STORED",
    "compression_method_code": 0,
    "crc32_policy": "computed_from_exact_member_bytes",
    "creator_system": 3,
    "creator_version": 20,
    "data_descriptors": "forbidden",
    "directory_entries": "forbidden",
    "duplicate_member_names": "forbidden",
    "encrypted_members": "forbidden",
    "end_of_central_directory_disk_number": 0,
    "external_attributes": 2175008768,
    "extra_fields": "empty",
    "file_mode": 33188,
    "general_purpose_bit_flags": 0,
    "internal_attributes": 0,
    "local_header_version_needed": 20,
    "member_comments": "empty",
    "member_disk_number_start": 0,
    "member_name_encoding": "ASCII",
    "member_order_semantics": "exact_sequence",
    "member_timestamp": [1980, 1, 1, 0, 0, 0],
    "size_fields": "computed_from_exact_member_bytes",
    "strict_timestamps": True,
    "trailing_data": "forbidden",
    "zip64": "forbidden",
}

EXPECTED_REFERENCE_ENVIRONMENT: dict[str, Any] = {
    "archive_implementation": {
        "boundary": "cpython_standard_library_bound_to_exact_python_micro_version",
        "module": "zipfile",
    },
    "container_image": (
        "docker.io/library/python:3.11.9-slim-bookworm@sha256:"
        "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
    ),
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

# In-container operating-system and interpreter properties cannot establish an
# OCI image digest. The outer launcher must verify the local RepoDigest, select
# the exact digest for launch, and supply the fixed read-only attestation below.
EXPECTED_CONTAINER_IMAGE_DIGEST = (
    "sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
REFERENCE_ENVIRONMENT_ATTESTATION_MAX_BYTES = 4096
EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION: dict[str, Any] = {
    "attestation_mount": "read_only",
    "attestation_role": "reference_environment_precondition",
    "attestation_source": "outer_reference_environment_launcher",
    "authority_effect": "none",
    "container_image": EXPECTED_REFERENCE_ENVIRONMENT["container_image"],
    "container_image_digest": EXPECTED_CONTAINER_IMAGE_DIGEST,
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
EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SIZE_BYTES = 843
EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SHA256 = (
    "9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca"
)

EXPECTED_CAPSULE_SIZE_BYTES = (
    sum(spec.size_bytes for spec in CAPSULE_MEMBER_SPECS)
    + len(CAPSULE_MEMBER_SPECS)
    * (LOCAL_FILE_HEADER.size + CENTRAL_DIRECTORY_HEADER.size)
    + 2 * sum(len(path.encode("ascii")) for path in CAPSULE_MEMBER_ORDER)
    + END_OF_CENTRAL_DIRECTORY.size
)


# This tool constructs one deterministic carrier only. It does not import or
# execute the Device Ledger verifier and does not produce a reproduction verdict.


def _validate_implementation_constants() -> None:
    implemented_profile = {
        "allow_zip64": False,
        "archive_comment": "empty",
        "archive_format": "zip",
        "central_directory_start_disk_number": FIXED_DISK_NUMBER,
        "central_directory_version_made_by": (
            (FIXED_CREATOR_SYSTEM << 8) | FIXED_CREATOR_VERSION
        ),
        "central_directory_version_needed": FIXED_VERSION_NEEDED,
        "compression_level": "not_applicable_for_stored",
        "compression_method": "ZIP_STORED",
        "compression_method_code": FIXED_COMPRESSION_METHOD_CODE,
        "crc32_policy": "computed_from_exact_member_bytes",
        "creator_system": FIXED_CREATOR_SYSTEM,
        "creator_version": FIXED_CREATOR_VERSION,
        "data_descriptors": "forbidden",
        "directory_entries": "forbidden",
        "duplicate_member_names": "forbidden",
        "encrypted_members": "forbidden",
        "end_of_central_directory_disk_number": FIXED_DISK_NUMBER,
        "external_attributes": FIXED_EXTERNAL_ATTRIBUTES,
        "extra_fields": "empty",
        "file_mode": FIXED_FILE_MODE,
        "general_purpose_bit_flags": FIXED_GENERAL_PURPOSE_FLAGS,
        "internal_attributes": FIXED_INTERNAL_ATTRIBUTES,
        "local_header_version_needed": FIXED_VERSION_NEEDED,
        "member_comments": "empty",
        "member_disk_number_start": FIXED_DISK_NUMBER,
        "member_name_encoding": "ASCII",
        "member_order_semantics": "exact_sequence",
        "member_timestamp": list(FIXED_MEMBER_TIMESTAMP),
        "size_fields": "computed_from_exact_member_bytes",
        "strict_timestamps": True,
        "trailing_data": "forbidden",
        "zip64": "forbidden",
    }
    if implemented_profile != EXPECTED_ARCHIVE_PROFILE:
        raise BuildError("builder_archive_profile_constant_mismatch")
    if FIXED_COMPRESSION_METHOD != zipfile.ZIP_STORED:
        raise BuildError("builder_compression_constant_mismatch")
    if FIXED_COMPRESSION_METHOD_CODE != zipfile.ZIP_STORED:
        raise BuildError("builder_compression_code_mismatch")
    if tuple(spec.archive_ordinal for spec in CAPSULE_MEMBER_SPECS) != (1, 2, 3, 4):
        raise BuildError("builder_member_ordinal_mismatch")
    if len(set(CAPSULE_MEMBER_ORDER)) != len(CAPSULE_MEMBER_ORDER):
        raise BuildError("builder_duplicate_member_path")
    expected_attestation_bytes = canonical_json_bytes(
        EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION
    )
    if (
        len(expected_attestation_bytes)
        != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SIZE_BYTES
    ):
        raise BuildError("reference_environment_attestation_size_constant_mismatch")
    if (
        sha256_bytes(expected_attestation_bytes)
        != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SHA256
    ):
        raise BuildError("reference_environment_attestation_sha256_constant_mismatch")
    expected_image = EXPECTED_REFERENCE_ENVIRONMENT["container_image"]
    if not isinstance(expected_image, str) or not expected_image.endswith(
        "@" + EXPECTED_CONTAINER_IMAGE_DIGEST
    ):
        raise BuildError("reference_container_image_digest_constant_mismatch")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(prefix + payload, usedforsecurity=False).hexdigest()


def _require_safe_relative_posix_path(value: str, label: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise BuildError(f"{label}_unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise BuildError(f"{label}_unsafe")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise BuildError(f"{label}_unsafe")
    try:
        value.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise BuildError(f"{label}_not_ascii") from exc
    return path


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
    return FileSystemIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def _absolute_without_symlink_resolution(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _resolve_repository_root(repository_root: Path) -> Path:
    candidate = _absolute_without_symlink_resolution(repository_root)
    try:
        resolved = candidate.resolve(strict=True)
        metadata = candidate.lstat()
    except OSError as exc:
        raise BuildError("repository_root_unavailable") from exc
    if candidate != resolved:
        raise BuildError("repository_root_symlink_or_noncanonical")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BuildError("repository_root_not_directory")
    return candidate


def _require_repository_working_directory(root: Path) -> None:
    current = _absolute_without_symlink_resolution(Path.cwd())
    try:
        resolved = current.resolve(strict=True)
        metadata = current.lstat()
    except OSError as exc:
        raise BuildError("working_directory_unavailable") from exc
    if current != resolved:
        raise BuildError("working_directory_symlink_or_noncanonical")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise BuildError("working_directory_not_directory")
    if current != root:
        raise BuildError("working_directory_not_repository_root")


def _require_safe_source_path(root: Path, relative_path: str) -> Path:
    relative = _require_safe_relative_posix_path(
        relative_path,
        "source_path",
    )
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise BuildError("source_parent_unavailable", relative_path) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise BuildError("source_parent_not_canonical_directory", relative_path)

    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BuildError("source_missing", relative_path) from exc
    if candidate != resolved:
        raise BuildError("source_symlink_or_noncanonical", relative_path)
    return candidate


def _open_readonly_nofollow(path: Path, relative_path: str) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    cloexec = getattr(os, "O_CLOEXEC", None)
    if nofollow is None or cloexec is None:
        raise BuildError("required_open_flags_unavailable")
    try:
        return os.open(path, os.O_RDONLY | nofollow | cloexec)
    except OSError as exc:
        raise BuildError("source_open_failed", relative_path) from exc


def _read_exact_source(root: Path, spec: SourceSpec) -> SourceSnapshot:
    path = _require_safe_source_path(root, spec.relative_path)
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise BuildError("source_lstat_failed", spec.relative_path) from exc
    if stat.S_ISLNK(path_metadata.st_mode):
        raise BuildError("source_symlink_forbidden", spec.relative_path)
    if not stat.S_ISREG(path_metadata.st_mode):
        raise BuildError("source_not_regular_file", spec.relative_path)
    if path_metadata.st_nlink != 1:
        raise BuildError("source_hard_link_state_forbidden", spec.relative_path)

    descriptor = _open_readonly_nofollow(path, spec.relative_path)
    try:
        before = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise BuildError("source_changed_before_read", spec.relative_path)
        if not stat.S_ISREG(before.st_mode):
            raise BuildError("source_not_regular_file", spec.relative_path)
        if before.st_nlink != 1:
            raise BuildError("source_hard_link_state_forbidden", spec.relative_path)
        if before.st_size != spec.size_bytes:
            raise BuildError("source_size_mismatch", spec.relative_path)

        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(spec.size_bytes + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if _stable_stat(before) != _stable_stat(after):
        raise BuildError("source_changed_during_read", spec.relative_path)
    if len(payload) != spec.size_bytes:
        raise BuildError("source_size_mismatch", spec.relative_path)
    if sha256_bytes(payload) != spec.sha256:
        raise BuildError("source_sha256_mismatch", spec.relative_path)
    if spec.git_blob_sha1 is not None and git_blob_sha1(payload) != spec.git_blob_sha1:
        raise BuildError("source_git_blob_sha1_mismatch", spec.relative_path)

    try:
        final_metadata = path.lstat()
    except OSError as exc:
        raise BuildError("source_lstat_failed_after_read", spec.relative_path) from exc
    if _stable_stat(final_metadata) != _stable_stat(after):
        raise BuildError("source_changed_after_read", spec.relative_path)

    return SourceSnapshot(
        spec=spec,
        payload=payload,
        metadata=_stable_stat(after),
    )


def _read_protected_sources(root: Path) -> dict[str, SourceSnapshot]:
    snapshots: dict[str, SourceSnapshot] = {}
    for spec in PROTECTED_SOURCE_SPECS:
        if spec.relative_path in snapshots:
            raise BuildError("duplicate_protected_source_spec", spec.relative_path)
        snapshots[spec.relative_path] = _read_exact_source(root, spec)
    return snapshots


def _require_sources_unchanged(
    root: Path,
    baseline: Mapping[str, SourceSnapshot],
) -> None:
    if tuple(baseline) != tuple(spec.relative_path for spec in PROTECTED_SOURCE_SPECS):
        raise BuildError("protected_source_baseline_order_mismatch")
    for spec in PROTECTED_SOURCE_SPECS:
        current = _read_exact_source(root, spec)
        expected = baseline[spec.relative_path]
        if current.payload != expected.payload:
            raise BuildError("protected_source_bytes_changed", spec.relative_path)
        if current.metadata != expected.metadata:
            raise BuildError("protected_source_metadata_changed", spec.relative_path)


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


def _load_strict_json_object(payload: bytes, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise BuildError(f"{label}_utf8_bom_forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_int=_parse_json_integer,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise BuildError(f"{label}_invalid_json") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label}_not_object")
    return value


def _normalize_json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 256:
        raise BuildError("canonical_json_depth_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -(2**63) or value > 2**63 - 1:
            raise BuildError("canonical_integer_out_of_range")
        return value
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise BuildError("canonical_string_not_unicode_scalar") from exc
        for character in value:
            code = ord(character)
            if 0xD800 <= code <= 0xDFFF:
                raise BuildError("canonical_string_not_unicode_scalar")
            if unicodedata.category(character) == "Cn":
                raise BuildError("canonical_string_unassigned_code_point")
        normalized = unicodedata.normalize("NFC", value)
        if normalized != value:
            raise BuildError("canonical_string_not_nfc")
        return value
    if isinstance(value, list):
        return [_normalize_json_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise BuildError("canonical_key_not_string")
            try:
                key.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise BuildError("canonical_key_not_unicode_scalar") from exc
            for character in key:
                code = ord(character)
                if 0xD800 <= code <= 0xDFFF:
                    raise BuildError("canonical_key_not_unicode_scalar")
                if unicodedata.category(character) == "Cn":
                    raise BuildError("canonical_key_unassigned_code_point")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise BuildError("canonical_key_collision")
            normalized[normalized_key] = _normalize_json_value(
                item,
                depth=depth + 1,
            )
        return normalized
    raise BuildError("canonical_json_type_unsupported")


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
            raise BuildError("canonical_string_not_unicode_scalar")
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
        raise BuildError("canonical_json_depth_exceeded")
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
    raise BuildError("canonical_json_type_unsupported")


def canonical_json_bytes(value: Any) -> bytes:
    normalized = _normalize_json_value(value)
    return _canonical_json_text(normalized).encode("utf-8")


def _read_reference_environment_attestation(
    path: Path,
    repository_root: Path,
) -> ExternalAttestationSnapshot:
    candidate = _absolute_without_symlink_resolution(path)
    try:
        resolved = candidate.resolve(strict=True)
        path_metadata = candidate.lstat()
    except OSError as exc:
        raise BuildError("reference_environment_attestation_unavailable") from exc
    if candidate != resolved:
        raise BuildError("reference_environment_attestation_symlink_or_noncanonical")
    if _is_within(candidate, repository_root):
        raise BuildError("reference_environment_attestation_inside_repository")
    if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISREG(
        path_metadata.st_mode
    ):
        raise BuildError("reference_environment_attestation_not_regular_file")
    if path_metadata.st_nlink != 1:
        raise BuildError("reference_environment_attestation_hard_link_forbidden")
    if path_metadata.st_size > REFERENCE_ENVIRONMENT_ATTESTATION_MAX_BYTES:
        raise BuildError("reference_environment_attestation_too_large")

    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise BuildError("reference_environment_attestation_open_failed") from exc
    try:
        before = os.fstat(descriptor)
        if _filesystem_identity(before) != _filesystem_identity(path_metadata):
            raise BuildError("reference_environment_attestation_changed_before_read")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise BuildError("reference_environment_attestation_file_state_invalid")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(REFERENCE_ENVIRONMENT_ATTESTATION_MAX_BYTES + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if _stable_stat(before) != _stable_stat(after):
        raise BuildError("reference_environment_attestation_changed_during_read")
    if len(payload) > REFERENCE_ENVIRONMENT_ATTESTATION_MAX_BYTES:
        raise BuildError("reference_environment_attestation_too_large")
    expected_bytes = canonical_json_bytes(
        EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION
    )
    if len(payload) != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SIZE_BYTES:
        raise BuildError("reference_environment_attestation_size_mismatch")
    if sha256_bytes(payload) != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SHA256:
        raise BuildError("reference_environment_attestation_sha256_mismatch")
    observed = _load_strict_json_object(
        payload,
        "reference_environment_attestation",
    )
    if observed != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION:
        raise BuildError("reference_environment_attestation_content_mismatch")
    if payload != expected_bytes:
        raise BuildError("reference_environment_attestation_noncanonical")

    try:
        final_metadata = candidate.lstat()
    except OSError as exc:
        raise BuildError(
            "reference_environment_attestation_lstat_failed_after_read"
        ) from exc
    if _stable_stat(final_metadata) != _stable_stat(after):
        raise BuildError("reference_environment_attestation_changed_after_read")
    return ExternalAttestationSnapshot(
        path=candidate,
        payload=payload,
        metadata=_stable_stat(after),
    )


def _require_reference_environment_attestation_unchanged(
    repository_root: Path,
    baseline: ExternalAttestationSnapshot,
) -> None:
    current = _read_reference_environment_attestation(
        baseline.path,
        repository_root,
    )
    if current.payload != baseline.payload:
        raise BuildError("reference_environment_attestation_bytes_changed")
    if current.metadata != baseline.metadata:
        raise BuildError("reference_environment_attestation_metadata_changed")


def _require_exact_mapping(
    observed: Any,
    expected: Mapping[str, Any],
    error_code: str,
) -> None:
    if observed != expected:
        raise BuildError(error_code)


def _validate_contract_projection(
    contract: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    projection = contract.get("manifest_projection")
    if not isinstance(projection, dict):
        raise BuildError("contract_manifest_projection_missing")

    copied_sections = projection.get("copied_sections")
    if not isinstance(copied_sections, list) or not all(
        isinstance(item, str) for item in copied_sections
    ):
        raise BuildError("contract_copied_sections_invalid")
    for section in copied_sections:
        if section not in contract or section not in manifest:
            raise BuildError("contract_manifest_projection_section_missing", section)
        if manifest[section] != contract[section]:
            raise BuildError("contract_manifest_projection_mismatch", section)

    literal_fields = projection.get("literal_fields")
    if not isinstance(literal_fields, dict):
        raise BuildError("contract_literal_fields_invalid")
    for key, expected in literal_fields.items():
        if manifest.get(key) != expected:
            raise BuildError("contract_manifest_literal_mismatch", key)

    computed_fields = projection.get("computed_fields")
    if computed_fields != {
        "capsule_contract_binding": "exact_contract_file_bytes"
    }:
        raise BuildError("contract_computed_fields_invalid")

    expected_contract_binding = {
        "byte_identity": "exact_file_bytes",
        "path": CAPSULE_CONTRACT_SPEC.relative_path,
        "sha256": CAPSULE_CONTRACT_SPEC.sha256,
        "size_bytes": CAPSULE_CONTRACT_SPEC.size_bytes,
    }
    _require_exact_mapping(
        manifest.get("capsule_contract_binding"),
        expected_contract_binding,
        "manifest_contract_binding_mismatch",
    )


def _validate_manifest_surface(
    snapshots: Mapping[str, SourceSnapshot],
) -> dict[str, Any]:
    schema_payload = snapshots[MANIFEST_SCHEMA_PATH].payload
    contract_payload = snapshots[CAPSULE_CONTRACT_PATH].payload
    manifest_payload = snapshots[CANONICAL_MANIFEST_SOURCE_PATH].payload
    canonicalization_payload = snapshots[CANONICALIZATION_PROFILE_PATH].payload

    _load_strict_json_object(schema_payload, "manifest_schema")
    contract = _load_strict_json_object(contract_payload, "capsule_contract")
    _load_strict_json_object(
        canonicalization_payload,
        "canonicalization_profile",
    )
    manifest = _load_strict_json_object(manifest_payload, "canonical_manifest")

    if b"\r" in manifest_payload or b"\n" in manifest_payload:
        raise BuildError("canonical_manifest_line_break_forbidden")
    if manifest_payload != canonical_json_bytes(manifest):
        raise BuildError("canonical_manifest_reserialization_mismatch")

    if contract.get("record_status") != "normative_contract":
        raise BuildError("capsule_contract_record_status_mismatch")
    if manifest.get("record_status") != "synthetic_reference":
        raise BuildError("canonical_manifest_record_status_mismatch")

    _validate_contract_projection(contract, manifest)

    expected_schema_binding = {
        "byte_identity": "exact_file_bytes",
        "path": MANIFEST_SCHEMA_SPEC.relative_path,
        "sha256": MANIFEST_SCHEMA_SPEC.sha256,
        "size_bytes": MANIFEST_SCHEMA_SPEC.size_bytes,
    }
    _require_exact_mapping(
        manifest.get("schema_binding"),
        expected_schema_binding,
        "manifest_schema_binding_mismatch",
    )

    expected_canonicalization_binding = {
        "byte_identity": "exact_file_bytes",
        "path": CANONICALIZATION_PROFILE_SPEC.relative_path,
        "sha256": CANONICALIZATION_PROFILE_SPEC.sha256,
        "size_bytes": CANONICALIZATION_PROFILE_SPEC.size_bytes,
    }
    _require_exact_mapping(
        manifest.get("canonicalization_binding"),
        expected_canonicalization_binding,
        "manifest_canonicalization_binding_mismatch",
    )

    _require_exact_mapping(
        manifest.get("archive_profile"),
        EXPECTED_ARCHIVE_PROFILE,
        "manifest_archive_profile_mismatch",
    )
    _require_exact_mapping(
        manifest.get("reference_environment"),
        EXPECTED_REFERENCE_ENVIRONMENT,
        "manifest_reference_environment_mismatch",
    )

    if manifest.get("expected_observer_fingerprint_sha256") != (
        EXPECTED_OBSERVER_FINGERPRINT_SHA256
    ):
        raise BuildError("manifest_observer_fingerprint_mismatch")

    implementation_boundary = manifest.get("implementation_boundary")
    expected_implementation_boundary = {
        "existing_verifier_modification": "forbidden",
        "new_verifier": "none",
        "producer_verdict_trusted": False,
        "runner_role": "orchestration_only",
        "verification_semantics_change": "none",
        "verifier_execution": "separate_process",
        "verifier_import_by_runner": "forbidden",
    }
    _require_exact_mapping(
        implementation_boundary,
        expected_implementation_boundary,
        "manifest_implementation_boundary_mismatch",
    )

    authority_boundary = manifest.get("authority_boundary")
    if not isinstance(authority_boundary, dict):
        raise BuildError("manifest_authority_boundary_invalid")
    if authority_boundary.get("authority_effect") != "none":
        raise BuildError("manifest_authority_effect_mismatch")
    authority_true_values = [
        key
        for key, value in authority_boundary.items()
        if key != "authority_effect" and value is not False
    ]
    if authority_true_values:
        raise BuildError("manifest_authority_boundary_not_none")

    layout = manifest.get("capsule_layout")
    if not isinstance(layout, dict):
        raise BuildError("manifest_capsule_layout_invalid")
    if layout.get("archive_filename") != OUTPUT_CAPSULE_NAME:
        raise BuildError("manifest_archive_filename_mismatch")
    if layout.get("archive_format") != "zip":
        raise BuildError("manifest_archive_format_mismatch")
    if layout.get("capsule_member_count") != len(CAPSULE_MEMBER_SPECS):
        raise BuildError("manifest_member_count_mismatch")
    if layout.get("payload_member_count") != len(CAPSULE_MEMBER_SPECS) - 1:
        raise BuildError("manifest_payload_member_count_mismatch")
    if layout.get("member_order") != list(CAPSULE_MEMBER_ORDER):
        raise BuildError("manifest_member_order_mismatch")

    expected_manifest_member = {
        "archive_ordinal": 1,
        "byte_identity_location": "outside_manifest",
        "media_type": "application/json",
        "path": MANIFEST_MEMBER_PATH,
        "role": "capsule_manifest",
        "self_inventory": "excluded_to_avoid_circularity",
    }
    _require_exact_mapping(
        layout.get("manifest_member"),
        expected_manifest_member,
        "manifest_member_contract_mismatch",
    )

    expected_payload_members = [
        {
            "archive_ordinal": spec.archive_ordinal,
            "byte_identity": "exact_source_bytes",
            "capsule_path": spec.capsule_path,
            "media_type": spec.media_type,
            "role": spec.role,
            "sha256": spec.sha256,
            "size_bytes": spec.size_bytes,
            "source_path": spec.source_path,
        }
        for spec in CAPSULE_MEMBER_SPECS[1:]
    ]
    if layout.get("payload_members") != expected_payload_members:
        raise BuildError("manifest_payload_members_mismatch")

    payload_source = manifest.get("payload_source")
    expected_payload_source = {
        "commit_sha": "0108e2c0da98c8a1fe5e739aa0f137ba6a3464e1",
        "repository": "HKati/pulse-release-gates-0.1",
        "source_role": "canonical_preexisting_input_baseline",
    }
    _require_exact_mapping(
        payload_source,
        expected_payload_source,
        "manifest_payload_source_mismatch",
    )

    return manifest


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    try:
        payload = path.read_text(encoding="utf-8", errors="strict")
    except OSError as exc:
        raise BuildError("reference_os_release_unavailable") from exc
    values: dict[str, str] = {}
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _verify_measurable_reference_runtime(
    attestation: ExternalAttestationSnapshot,
) -> None:
    if (
        len(attestation.payload)
        != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SIZE_BYTES
        or sha256_bytes(attestation.payload)
        != EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION_SHA256
    ):
        raise BuildError("reference_environment_attestation_identity_mismatch")
    if os.name != "posix" or platform.system() != "Linux":
        raise BuildError("reference_operating_system_mismatch")
    if platform.machine() != "x86_64":
        raise BuildError("reference_architecture_mismatch")
    if platform.python_implementation() != "CPython":
        raise BuildError("reference_python_implementation_mismatch")
    if tuple(sys.version_info[:3]) != (3, 11, 9):
        raise BuildError("reference_python_version_mismatch")
    if unicodedata.unidata_version != "14.0.0":
        raise BuildError("reference_unicode_data_version_mismatch")

    expected_environment = EXPECTED_REFERENCE_ENVIRONMENT["environment_variables"]
    for key, expected in expected_environment.items():
        if os.environ.get(key) != expected:
            raise BuildError("reference_environment_variable_mismatch", key)
    if not sys.dont_write_bytecode:
        raise BuildError("reference_bytecode_policy_mismatch")

    os_release = _read_os_release()
    if os_release.get("ID") != "debian":
        raise BuildError("reference_os_distribution_mismatch")
    if os_release.get("VERSION_CODENAME") != "bookworm":
        raise BuildError("reference_os_version_mismatch")

    stdlib_path = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    zipfile_path = Path(zipfile.__file__).resolve(strict=True)
    if zipfile_path != stdlib_path / "zipfile.py":
        raise BuildError("reference_archive_implementation_mismatch")

    required_os_constants = (
        "O_CLOEXEC",
        "O_DIRECTORY",
        "O_NOFOLLOW",
    )
    for name in required_os_constants:
        if getattr(os, name, None) is None:
            raise BuildError("reference_os_capability_missing", name)
    if getattr(ctypes.CDLL(None), "renameat2", None) is None:
        raise BuildError("atomic_noreplace_publish_unavailable")


def _build_member_payloads(
    snapshots: Mapping[str, SourceSnapshot],
) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for spec in CAPSULE_MEMBER_SPECS:
        _require_safe_relative_posix_path(spec.capsule_path, "capsule_member_path")
        source = snapshots.get(spec.source_path)
        if source is None:
            raise BuildError("capsule_member_source_missing", spec.source_path)
        if len(source.payload) != spec.size_bytes:
            raise BuildError("capsule_member_source_size_mismatch", spec.source_path)
        if sha256_bytes(source.payload) != spec.sha256:
            raise BuildError("capsule_member_source_sha256_mismatch", spec.source_path)
        if spec.capsule_path in members:
            raise BuildError("duplicate_capsule_member_path", spec.capsule_path)
        members[spec.capsule_path] = source.payload
    if tuple(members) != CAPSULE_MEMBER_ORDER:
        raise BuildError("capsule_member_order_internal_mismatch")
    return members


def _deterministic_zip(members: Mapping[str, bytes]) -> bytes:
    if tuple(members) != CAPSULE_MEMBER_ORDER:
        raise BuildError("capsule_member_order_mismatch")

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=FIXED_COMPRESSION_METHOD,
        allowZip64=False,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for path in CAPSULE_MEMBER_ORDER:
            payload = members[path]
            info = zipfile.ZipInfo(path, date_time=FIXED_MEMBER_TIMESTAMP)
            info.compress_type = FIXED_COMPRESSION_METHOD
            info.create_system = FIXED_CREATOR_SYSTEM
            info.create_version = FIXED_CREATOR_VERSION
            info.extract_version = FIXED_VERSION_NEEDED
            info.reserved = 0
            info.flag_bits = FIXED_GENERAL_PURPOSE_FLAGS
            info.volume = FIXED_DISK_NUMBER
            info.internal_attr = FIXED_INTERNAL_ATTRIBUTES
            info.external_attr = FIXED_EXTERNAL_ATTRIBUTES
            info.extra = b""
            info.comment = b""
            archive.writestr(
                info,
                payload,
                compress_type=FIXED_COMPRESSION_METHOD,
            )
    capsule = buffer.getvalue()
    if len(capsule) != EXPECTED_CAPSULE_SIZE_BYTES:
        raise BuildError("capsule_size_formula_mismatch")
    return capsule


def _require_available(
    payload: bytes,
    offset: int,
    size: int,
    error_code: str,
) -> None:
    if offset < 0 or size < 0 or offset + size > len(payload):
        raise BuildError(error_code)


def _inspect_capsule_binary(
    capsule: bytes,
    members: Mapping[str, bytes],
) -> None:
    local_offsets: dict[str, int] = {}
    offset = 0

    for path in CAPSULE_MEMBER_ORDER:
        expected_payload = members[path]
        expected_name = path.encode("ascii")
        _require_available(
            capsule,
            offset,
            LOCAL_FILE_HEADER.size,
            "capsule_local_header_truncated",
        )
        (
            signature,
            version_needed,
            flags,
            compression_method,
            modified_time,
            modified_date,
            crc32_value,
            compressed_size,
            uncompressed_size,
            filename_length,
            extra_length,
        ) = LOCAL_FILE_HEADER.unpack_from(capsule, offset)
        if signature != LOCAL_FILE_HEADER_SIGNATURE:
            raise BuildError("capsule_local_header_signature_mismatch", path)
        if version_needed != FIXED_VERSION_NEEDED:
            raise BuildError("capsule_local_version_needed_mismatch", path)
        if flags != FIXED_GENERAL_PURPOSE_FLAGS:
            raise BuildError("capsule_local_flags_mismatch", path)
        if flags & 0x0001:
            raise BuildError("capsule_encryption_forbidden", path)
        if flags & 0x0008:
            raise BuildError("capsule_data_descriptor_forbidden", path)
        if compression_method != FIXED_COMPRESSION_METHOD_CODE:
            raise BuildError("capsule_local_compression_mismatch", path)
        if modified_time != FIXED_DOS_TIME or modified_date != FIXED_DOS_DATE:
            raise BuildError("capsule_local_timestamp_mismatch", path)
        expected_crc32 = zlib.crc32(expected_payload) & 0xFFFFFFFF
        if crc32_value != expected_crc32:
            raise BuildError("capsule_local_crc32_mismatch", path)
        if compressed_size != len(expected_payload):
            raise BuildError("capsule_local_compressed_size_mismatch", path)
        if uncompressed_size != len(expected_payload):
            raise BuildError("capsule_local_uncompressed_size_mismatch", path)
        if filename_length != len(expected_name):
            raise BuildError("capsule_local_filename_length_mismatch", path)
        if extra_length != 0:
            raise BuildError("capsule_local_extra_field_forbidden", path)

        name_offset = offset + LOCAL_FILE_HEADER.size
        _require_available(
            capsule,
            name_offset,
            filename_length,
            "capsule_local_filename_truncated",
        )
        observed_name = capsule[name_offset : name_offset + filename_length]
        if observed_name != expected_name:
            raise BuildError("capsule_local_filename_mismatch", path)

        data_offset = name_offset + filename_length
        _require_available(
            capsule,
            data_offset,
            compressed_size,
            "capsule_member_payload_truncated",
        )
        observed_payload = capsule[data_offset : data_offset + compressed_size]
        if observed_payload != expected_payload:
            raise BuildError("capsule_member_payload_mismatch", path)

        local_offsets[path] = offset
        offset = data_offset + compressed_size

    central_directory_offset = offset
    for path in CAPSULE_MEMBER_ORDER:
        expected_payload = members[path]
        expected_name = path.encode("ascii")
        _require_available(
            capsule,
            offset,
            CENTRAL_DIRECTORY_HEADER.size,
            "capsule_central_header_truncated",
        )
        (
            signature,
            version_made_by,
            version_needed,
            flags,
            compression_method,
            modified_time,
            modified_date,
            crc32_value,
            compressed_size,
            uncompressed_size,
            filename_length,
            extra_length,
            comment_length,
            disk_number_start,
            internal_attributes,
            external_attributes,
            local_header_offset,
        ) = CENTRAL_DIRECTORY_HEADER.unpack_from(capsule, offset)
        if signature != CENTRAL_DIRECTORY_HEADER_SIGNATURE:
            raise BuildError("capsule_central_header_signature_mismatch", path)
        if version_made_by != 788:
            raise BuildError("capsule_version_made_by_mismatch", path)
        if version_needed != FIXED_VERSION_NEEDED:
            raise BuildError("capsule_central_version_needed_mismatch", path)
        if flags != FIXED_GENERAL_PURPOSE_FLAGS:
            raise BuildError("capsule_central_flags_mismatch", path)
        if flags & 0x0001:
            raise BuildError("capsule_encryption_forbidden", path)
        if flags & 0x0008:
            raise BuildError("capsule_data_descriptor_forbidden", path)
        if compression_method != FIXED_COMPRESSION_METHOD_CODE:
            raise BuildError("capsule_central_compression_mismatch", path)
        if modified_time != FIXED_DOS_TIME or modified_date != FIXED_DOS_DATE:
            raise BuildError("capsule_central_timestamp_mismatch", path)
        expected_crc32 = zlib.crc32(expected_payload) & 0xFFFFFFFF
        if crc32_value != expected_crc32:
            raise BuildError("capsule_central_crc32_mismatch", path)
        if compressed_size != len(expected_payload):
            raise BuildError("capsule_central_compressed_size_mismatch", path)
        if uncompressed_size != len(expected_payload):
            raise BuildError("capsule_central_uncompressed_size_mismatch", path)
        if filename_length != len(expected_name):
            raise BuildError("capsule_central_filename_length_mismatch", path)
        if extra_length != 0:
            raise BuildError("capsule_central_extra_field_forbidden", path)
        if comment_length != 0:
            raise BuildError("capsule_member_comment_forbidden", path)
        if disk_number_start != FIXED_DISK_NUMBER:
            raise BuildError("capsule_member_disk_number_mismatch", path)
        if internal_attributes != FIXED_INTERNAL_ATTRIBUTES:
            raise BuildError("capsule_internal_attributes_mismatch", path)
        if external_attributes != FIXED_EXTERNAL_ATTRIBUTES:
            raise BuildError("capsule_external_attributes_mismatch", path)
        if local_header_offset != local_offsets[path]:
            raise BuildError("capsule_local_header_offset_mismatch", path)
        if (
            compressed_size == 0xFFFFFFFF
            or uncompressed_size == 0xFFFFFFFF
            or local_header_offset == 0xFFFFFFFF
        ):
            raise BuildError("capsule_zip64_forbidden", path)

        name_offset = offset + CENTRAL_DIRECTORY_HEADER.size
        _require_available(
            capsule,
            name_offset,
            filename_length,
            "capsule_central_filename_truncated",
        )
        observed_name = capsule[name_offset : name_offset + filename_length]
        if observed_name != expected_name:
            raise BuildError("capsule_central_filename_mismatch", path)
        offset = name_offset + filename_length

    central_directory_size = offset - central_directory_offset
    _require_available(
        capsule,
        offset,
        END_OF_CENTRAL_DIRECTORY.size,
        "capsule_eocd_truncated",
    )
    (
        signature,
        disk_number,
        central_directory_start_disk,
        entries_on_disk,
        total_entries,
        observed_central_directory_size,
        observed_central_directory_offset,
        comment_length,
    ) = END_OF_CENTRAL_DIRECTORY.unpack_from(capsule, offset)
    if signature != END_OF_CENTRAL_DIRECTORY_SIGNATURE:
        raise BuildError("capsule_eocd_signature_mismatch")
    if disk_number != FIXED_DISK_NUMBER:
        raise BuildError("capsule_eocd_disk_number_mismatch")
    if central_directory_start_disk != FIXED_DISK_NUMBER:
        raise BuildError("capsule_central_directory_start_disk_mismatch")
    if entries_on_disk != len(CAPSULE_MEMBER_ORDER):
        raise BuildError("capsule_entries_on_disk_mismatch")
    if total_entries != len(CAPSULE_MEMBER_ORDER):
        raise BuildError("capsule_total_entries_mismatch")
    if observed_central_directory_size != central_directory_size:
        raise BuildError("capsule_central_directory_size_mismatch")
    if observed_central_directory_offset != central_directory_offset:
        raise BuildError("capsule_central_directory_offset_mismatch")
    if comment_length != 0:
        raise BuildError("capsule_archive_comment_forbidden")
    if entries_on_disk == 0xFFFF or total_entries == 0xFFFF:
        raise BuildError("capsule_zip64_forbidden")
    if observed_central_directory_size == 0xFFFFFFFF:
        raise BuildError("capsule_zip64_forbidden")
    if observed_central_directory_offset == 0xFFFFFFFF:
        raise BuildError("capsule_zip64_forbidden")

    offset += END_OF_CENTRAL_DIRECTORY.size
    if offset != len(capsule):
        raise BuildError("capsule_trailing_data_forbidden")


def _inspect_capsule_zipfile(
    capsule: bytes,
    members: Mapping[str, bytes],
) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(capsule), mode="r") as archive:
            if archive.comment != b"":
                raise BuildError("capsule_archive_comment_forbidden")
            infos = archive.infolist()
            names = tuple(info.filename for info in infos)
            if names != CAPSULE_MEMBER_ORDER:
                raise BuildError("capsule_zipfile_member_order_mismatch")
            if len(set(names)) != len(names):
                raise BuildError("capsule_duplicate_member_name")
            if archive.testzip() is not None:
                raise BuildError("capsule_zipfile_crc32_failure")

            for info, expected_spec in zip(
                infos,
                CAPSULE_MEMBER_SPECS,
                strict=True,
            ):
                path = expected_spec.capsule_path
                expected_payload = members[path]
                if info.is_dir() or info.filename.endswith("/"):
                    raise BuildError("capsule_directory_entry_forbidden", path)
                if info.date_time != FIXED_MEMBER_TIMESTAMP:
                    raise BuildError("capsule_zipfile_timestamp_mismatch", path)
                if info.compress_type != FIXED_COMPRESSION_METHOD:
                    raise BuildError("capsule_zipfile_compression_mismatch", path)
                if info.create_system != FIXED_CREATOR_SYSTEM:
                    raise BuildError("capsule_zipfile_creator_system_mismatch", path)
                if info.create_version != FIXED_CREATOR_VERSION:
                    raise BuildError("capsule_zipfile_creator_version_mismatch", path)
                if info.extract_version != FIXED_VERSION_NEEDED:
                    raise BuildError("capsule_zipfile_version_needed_mismatch", path)
                if info.flag_bits != FIXED_GENERAL_PURPOSE_FLAGS:
                    raise BuildError("capsule_zipfile_flags_mismatch", path)
                if info.volume != FIXED_DISK_NUMBER:
                    raise BuildError("capsule_zipfile_disk_number_mismatch", path)
                if info.internal_attr != FIXED_INTERNAL_ATTRIBUTES:
                    raise BuildError("capsule_zipfile_internal_attr_mismatch", path)
                if info.external_attr != FIXED_EXTERNAL_ATTRIBUTES:
                    raise BuildError("capsule_zipfile_external_attr_mismatch", path)
                if info.extra != b"":
                    raise BuildError("capsule_zipfile_extra_field_forbidden", path)
                if info.comment != b"":
                    raise BuildError("capsule_zipfile_member_comment_forbidden", path)
                if info.file_size != len(expected_payload):
                    raise BuildError("capsule_zipfile_file_size_mismatch", path)
                if info.compress_size != len(expected_payload):
                    raise BuildError("capsule_zipfile_compress_size_mismatch", path)
                if info.CRC != (zlib.crc32(expected_payload) & 0xFFFFFFFF):
                    raise BuildError("capsule_zipfile_crc32_mismatch", path)
                if archive.read(info) != expected_payload:
                    raise BuildError("capsule_zipfile_payload_mismatch", path)
    except zipfile.BadZipFile as exc:
        raise BuildError("capsule_bad_zip") from exc


def _inspect_capsule(
    capsule: bytes,
    members: Mapping[str, bytes],
) -> None:
    if len(capsule) != EXPECTED_CAPSULE_SIZE_BYTES:
        raise BuildError("capsule_size_mismatch")
    _inspect_capsule_binary(capsule, members)
    _inspect_capsule_zipfile(capsule, members)


def build_reproduction_capsule(
    repository_root: Path,
    reference_environment_attestation: Path,
) -> tuple[
    Path,
    bytes,
    dict[str, SourceSnapshot],
    ExternalAttestationSnapshot,
]:
    _validate_implementation_constants()
    root = _resolve_repository_root(repository_root)
    _require_repository_working_directory(root)
    attestation = _read_reference_environment_attestation(
        reference_environment_attestation,
        root,
    )
    _verify_measurable_reference_runtime(attestation)
    snapshots = _read_protected_sources(root)
    _validate_manifest_surface(snapshots)
    members = _build_member_payloads(snapshots)
    capsule = _deterministic_zip(members)
    _inspect_capsule(capsule, members)
    _require_sources_unchanged(root, snapshots)
    _require_reference_environment_attestation_unchanged(root, attestation)
    return root, capsule, snapshots, attestation


def _resolve_output_directory(
    output_directory: Path,
    repository_root: Path,
) -> tuple[Path, Path]:
    destination = _absolute_without_symlink_resolution(output_directory)
    parent = destination.parent
    try:
        resolved_parent = parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as exc:
        raise BuildError("output_parent_unavailable") from exc
    if parent != resolved_parent:
        raise BuildError("output_parent_symlink_or_noncanonical")
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(
        parent_metadata.st_mode
    ):
        raise BuildError("output_parent_not_directory")
    if _is_within(destination, repository_root):
        raise BuildError("output_directory_inside_repository")
    if os.path.lexists(destination):
        raise BuildError("output_directory_exists")
    temporary = parent / (
        f".{destination.name}.{TOOL_NAME}.{secrets.token_hex(16)}.tmp"
    )
    if os.path.lexists(temporary):
        raise BuildError("temporary_output_collision")
    return destination, temporary


def _open_output_parent(parent: Path) -> tuple[int, FileSystemIdentity]:
    try:
        path_metadata = parent.lstat()
    except OSError as exc:
        raise BuildError("output_parent_lstat_failed") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(parent, flags)
    except OSError as exc:
        raise BuildError("output_parent_open_failed") from exc
    try:
        opened_metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(opened_metadata.st_mode):
            raise BuildError("output_parent_not_directory")
        if _filesystem_identity(opened_metadata) != _filesystem_identity(
            path_metadata
        ):
            raise BuildError("output_parent_changed_before_open")
        return descriptor, _filesystem_identity(opened_metadata)
    except BaseException:
        os.close(descriptor)
        raise


def _rename_directory_noreplace(
    parent_descriptor: int,
    source_name: str,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise BuildError("atomic_noreplace_publish_unavailable")
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    rename_noreplace = 1
    result = renameat2(
        parent_descriptor,
        os.fsencode(source_name),
        parent_descriptor,
        os.fsencode(destination_name),
        rename_noreplace,
    )
    if result == 0:
        return
    observed_errno = ctypes.get_errno()
    if observed_errno == errno.EEXIST:
        raise BuildError("output_directory_exists_before_publish")
    raise BuildError(
        "atomic_output_publish_failed",
        str(observed_errno),
    )


def _fsync_directory_descriptor(
    descriptor: int,
    error_code: str,
) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise BuildError(error_code) from exc


def _read_owned_capsule(
    directory_descriptor: int,
    expected: bytes,
    expected_identity: FileSystemIdentity,
) -> None:
    try:
        path_metadata = os.stat(
            OUTPUT_CAPSULE_NAME,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise BuildError("published_capsule_missing") from exc
    if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISREG(
        path_metadata.st_mode
    ):
        raise BuildError("published_capsule_not_regular_file")
    if path_metadata.st_nlink != 1:
        raise BuildError("published_capsule_hard_link_state_forbidden")
    if _filesystem_identity(path_metadata) != expected_identity:
        raise BuildError("published_capsule_identity_mismatch")

    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(
            OUTPUT_CAPSULE_NAME,
            flags,
            dir_fd=directory_descriptor,
        )
    except OSError as exc:
        raise BuildError("published_capsule_open_failed") from exc
    try:
        before = os.fstat(descriptor)
        if _filesystem_identity(before) != expected_identity:
            raise BuildError("published_capsule_identity_mismatch")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(len(expected) + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if _stable_stat(before) != _stable_stat(after):
        raise BuildError("published_capsule_changed_during_read")
    if payload != expected:
        raise BuildError("published_capsule_readback_mismatch")


def _remove_owned_output_directory(
    *,
    parent_descriptor: int,
    directory_descriptor: int,
    directory_name: str,
    directory_identity: FileSystemIdentity,
    capsule_identity: FileSystemIdentity | None,
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
        raise BuildError("owned_output_cleanup_target_unavailable") from exc
    if not stat.S_ISDIR(path_metadata.st_mode):
        raise BuildError("owned_output_cleanup_target_invalid")
    if _filesystem_identity(path_metadata) != directory_identity:
        raise BuildError("owned_output_cleanup_identity_mismatch")

    opened_metadata = os.fstat(directory_descriptor)
    if not stat.S_ISDIR(opened_metadata.st_mode):
        raise BuildError("owned_output_cleanup_descriptor_invalid")
    if _filesystem_identity(opened_metadata) != directory_identity:
        raise BuildError("owned_output_cleanup_descriptor_identity_mismatch")

    try:
        entries = os.listdir(directory_descriptor)
    except OSError as exc:
        raise BuildError("owned_output_cleanup_list_failed") from exc
    expected_entries = [] if capsule_identity is None else [OUTPUT_CAPSULE_NAME]
    if entries != expected_entries:
        raise BuildError("owned_output_cleanup_contents_changed")

    if capsule_identity is not None:
        try:
            entry_metadata = os.stat(
                OUTPUT_CAPSULE_NAME,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise BuildError("owned_output_cleanup_entry_unavailable") from exc
        if not stat.S_ISREG(entry_metadata.st_mode):
            raise BuildError("owned_output_cleanup_entry_invalid")
        if entry_metadata.st_nlink != 1:
            raise BuildError("owned_output_cleanup_entry_hard_link_forbidden")
        if _filesystem_identity(entry_metadata) != capsule_identity:
            raise BuildError("owned_output_cleanup_entry_identity_mismatch")

    os.fchmod(directory_descriptor, 0o700)
    if capsule_identity is not None:
        os.unlink(OUTPUT_CAPSULE_NAME, dir_fd=directory_descriptor)
    _fsync_directory_descriptor(
        directory_descriptor,
        "owned_output_cleanup_directory_fsync_failed",
    )

    path_metadata = os.stat(
        directory_name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if _filesystem_identity(path_metadata) != directory_identity:
        raise BuildError("owned_output_cleanup_identity_changed")
    os.rmdir(directory_name, dir_fd=parent_descriptor)


def _publish_capsule(
    *,
    repository_root: Path,
    output_directory: Path,
    capsule: bytes,
    snapshots: Mapping[str, SourceSnapshot],
    attestation: ExternalAttestationSnapshot,
) -> None:
    destination, temporary = _resolve_output_directory(
        output_directory,
        repository_root,
    )
    parent_descriptor = -1
    directory_descriptor = -1
    directory_identity: FileSystemIdentity | None = None
    capsule_identity: FileSystemIdentity | None = None
    published = False
    try:
        parent_descriptor, _ = _open_output_parent(destination.parent)
        os.mkdir(temporary.name, 0o700, dir_fd=parent_descriptor)
        directory_path_metadata = os.stat(
            temporary.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(directory_path_metadata.st_mode):
            raise BuildError("temporary_output_not_directory")
        directory_identity = _filesystem_identity(directory_path_metadata)

        directory_flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
        )
        directory_descriptor = os.open(
            temporary.name,
            directory_flags,
            dir_fd=parent_descriptor,
        )
        if _filesystem_identity(os.fstat(directory_descriptor)) != directory_identity:
            raise BuildError("temporary_output_identity_mismatch")

        file_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
        )
        try:
            descriptor = os.open(
                OUTPUT_CAPSULE_NAME,
                file_flags,
                0o600,
                dir_fd=directory_descriptor,
            )
        except OSError as exc:
            raise BuildError("temporary_capsule_create_failed") from exc
        try:
            capsule_identity = _filesystem_identity(os.fstat(descriptor))
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                descriptor = -1
                handle.write(capsule)
                handle.flush()
                os.fsync(handle.fileno())
                os.fchmod(handle.fileno(), 0o444)
                os.fsync(handle.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)

        _read_owned_capsule(
            directory_descriptor,
            capsule,
            capsule_identity,
        )
        os.fchmod(directory_descriptor, 0o555)
        _fsync_directory_descriptor(
            directory_descriptor,
            "temporary_output_directory_fsync_failed",
        )
        _require_sources_unchanged(repository_root, snapshots)
        _require_reference_environment_attestation_unchanged(
            repository_root,
            attestation,
        )

        _rename_directory_noreplace(
            parent_descriptor,
            temporary.name,
            destination.name,
        )
        published = True
        _fsync_directory_descriptor(
            parent_descriptor,
            "output_parent_fsync_after_publish_failed",
        )

        published_metadata = os.stat(
            destination.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if _filesystem_identity(published_metadata) != directory_identity:
            raise BuildError("published_output_directory_identity_mismatch")
        _read_owned_capsule(
            directory_descriptor,
            capsule,
            capsule_identity,
        )
        _require_sources_unchanged(repository_root, snapshots)
        _require_reference_environment_attestation_unchanged(
            repository_root,
            attestation,
        )
    except BaseException:
        if (
            parent_descriptor >= 0
            and directory_descriptor >= 0
            and directory_identity is not None
        ):
            cleanup_name = destination.name if published else temporary.name
            try:
                _remove_owned_output_directory(
                    parent_descriptor=parent_descriptor,
                    directory_descriptor=directory_descriptor,
                    directory_name=cleanup_name,
                    directory_identity=directory_identity,
                    capsule_identity=capsule_identity,
                )
                _fsync_directory_descriptor(
                    parent_descriptor,
                    "output_parent_fsync_after_cleanup_failed",
                )
            except BaseException:
                pass
        raise
    finally:
        if directory_descriptor >= 0:
            os.close(directory_descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def _success_summary(
    capsule: bytes,
    attestation: ExternalAttestationSnapshot,
) -> dict[str, Any]:
    return {
        "archive_filename": OUTPUT_CAPSULE_NAME,
        "authority_effect": "none",
        "capsule_member_count": len(CAPSULE_MEMBER_SPECS),
        "capsule_sha256": sha256_bytes(capsule),
        "capsule_size_bytes": len(capsule),
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "ok": True,
        "protected_source_count": len(PROTECTED_SOURCE_SPECS),
        "reference_environment_attestation": {
            "container_image": EXPECTED_REFERENCE_ENVIRONMENT["container_image"],
            "sha256": sha256_bytes(attestation.payload),
            "size_bytes": len(attestation.payload),
            "source": "outer_reference_environment_launcher",
            "verification_method": (
                EXPECTED_REFERENCE_ENVIRONMENT_ATTESTATION[
                    "verification_method"
                ]
            ),
            "verified": True,
        },
        "result": "capsule_constructed_only",
        "tool": TOOL_NAME,
        "tool_source_path": TOOL_SOURCE_PATH,
        "tool_version": TOOL_VERSION,
        "verifier_executed": False,
    }


def _failure_summary(error: BuildError) -> dict[str, Any]:
    output: dict[str, Any] = {
        "authority_effect": "none",
        "error_code": error.code,
        "ok": False,
        "tool": TOOL_NAME,
        "tool_source_path": TOOL_SOURCE_PATH,
        "tool_version": TOOL_VERSION,
    }
    if error.context is not None:
        output["error_context"] = error.context
    return output


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Construct one deterministic four-member PULSEmech Device Ledger "
            "Reproduction Capsule from exact protected repository inputs."
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Exact repository root. The default is the current directory.",
    )
    parser.add_argument(
        "--output-directory",
        required=True,
        help=(
            "New output directory outside the repository. It must not already "
            "exist; the fixed Capsule filename is created inside it."
        ),
    )
    parser.add_argument(
        "--reference-environment-attestation",
        required=True,
        help=(
            "Exact canonical outer-launcher attestation created only after the "
            "digest-pinned reference image is verified and selected for launch."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root, capsule, snapshots, attestation = build_reproduction_capsule(
            Path(args.repository_root),
            Path(args.reference_environment_attestation),
        )
        _publish_capsule(
            repository_root=root,
            output_directory=Path(args.output_directory),
            capsule=capsule,
            snapshots=snapshots,
            attestation=attestation,
        )
        sys.stdout.buffer.write(
            canonical_json_bytes(_success_summary(capsule, attestation)) + b"\n"
        )
        return 0
    except BuildError as exc:
        sys.stderr.buffer.write(canonical_json_bytes(_failure_summary(exc)) + b"\n")
        return 2
    except Exception as exc:
        error = BuildError(
            "unexpected_bounded_builder_failure",
            str(getattr(exc, "errno", "none")),
        )
        sys.stderr.buffer.write(canonical_json_bytes(_failure_summary(error)) + b"\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
