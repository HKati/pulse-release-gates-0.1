#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import os
import stat
import struct
import subprocess
import sys
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "examples" / "device_transition_ledger"

CANONICAL_MANIFEST_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json"
)
CANONICALIZATION_PROFILE_PATH = (
    ROOT / "contracts" / "pulsemech_device_canonical_json_v0.json"
)
CANONICAL_LEDGER_PATH = (
    REFERENCE_ROOT / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
STANDALONE_VERIFIER_PATH = ROOT / "tools" / "verify_pulsemech_device_ledger_v0.py"
CANONICAL_EXPECTED_REPORT_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_transition_ledger_reference_verification_v0.json"
)
RESULT_SCHEMA_PATH = (
    ROOT / "schemas" / "pulsemech_device_ledger_reproduction_result_v0.schema.json"
)
CAPSULE_BUILDER_PATH = (
    ROOT / "tools" / "build_pulsemech_device_ledger_reproduction_capsule_v0.py"
)
REPRODUCTION_RUNNER_PATH = (
    ROOT / "tools" / "run_pulsemech_device_ledger_reproduction_capsule_v0.py"
)
CANONICAL_CAPSULE_PATH = (
    REFERENCE_ROOT / "pulsemech_device_ledger_reproduction_capsule_v0.zip"
)
CANONICAL_RESULT_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_ledger_reproduction_result_reference_v0.json"
)

MANIFEST_MEMBER_PATH = (
    "manifest/pulsemech_device_ledger_reproduction_capsule_manifest_v0.json"
)
CAPSULE_LEDGER_MEMBER_PATH = (
    "artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
CAPSULE_VERIFIER_MEMBER_PATH = "verifier/verify_pulsemech_device_ledger_v0.py"
CAPSULE_EXPECTED_REPORT_MEMBER_PATH = (
    "expected/pulsemech_device_transition_ledger_reference_verification_v0.json"
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
EXPECTED_EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
EXPECTED_REFERENCE_IMAGE = (
    "docker.io/library/python:3.11.9-slim-bookworm@sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
EXPECTED_REFERENCE_DIGEST = (
    "sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
EXPECTED_ATTESTATION_IDENTITY = (
    843,
    "9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca",
)

EXPECTED_IDENTITIES = {
    CANONICAL_MANIFEST_PATH: (
        8989,
        "cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf",
        "b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b",
    ),
    CANONICALIZATION_PROFILE_PATH: (
        2719,
        "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
        "89d866c8f7a0dc9ddfd2f7d53ff171530dffc18f",
    ),
    CANONICAL_LEDGER_PATH: (
        133568,
        "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3",
        "8d9ecb2c6d42f8fd5afb10face6495ef67874b2d",
    ),
    STANDALONE_VERIFIER_PATH: (
        126419,
        "0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7",
        "6f5ac6323c56d22e6a908d6a2419f253617382b0",
    ),
    CANONICAL_EXPECTED_REPORT_PATH: (
        15328,
        "5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4",
        "e79e70a243ff104e4d0f17d09379ae1e3962230a",
    ),
    RESULT_SCHEMA_PATH: (
        71112,
        "83b89d5c8315033a654e717ae017ff5964ac63685e4f65f2d9e18f225c780ca0",
        "833f876f3bdd703c3fab7aa93aacb14bca47f01b",
    ),
    CAPSULE_BUILDER_PATH: (
        75083,
        "4878da3e3adb82697fc0aa25b48e439a52c2601bb1a8ceca595eb939f079b01d",
        "d37dc25ef68a08d0b076ffa4e5bcd48442858cde",
    ),
    REPRODUCTION_RUNNER_PATH: (
        121181,
        "d5d4971f2e4feb18481253a197478128bcd14fbf2dbcd7a64c1debbe1e1be97b",
        "10aa09a65a185072657f1eb158c00e99c2ee9c6e",
    ),
    CANONICAL_CAPSULE_PATH: (
        285144,
        "49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678",
        "5b2647823e59bde24cf9125851c1490e3149dfab",
    ),
    CANONICAL_RESULT_PATH: (
        31188,
        "d20dd0926932f911141f0cd68201471dfd1f5c03dc16a5159e9f89693d3fbc4d",
        "5de756a85e695d6d8655b95565faf3d15fd24dc8",
    ),
}

EXPECTED_PR1_BINDINGS = {
    "manifest_schema": {
        "git_blob_sha1": "6a0dabff2e5f725c6ef8e586f9cae7fff566030b",
        "path": (
            "schemas/"
            "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
        ),
        "sha256": (
            "a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c"
        ),
        "size_bytes": 32581,
    },
    "capsule_contract": {
        "git_blob_sha1": "d15fddbe9250de0ed76b3b7ebb7d679383a867b4",
        "path": "contracts/pulsemech_device_ledger_reproduction_capsule_v0.json",
        "sha256": (
            "ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67"
        ),
        "size_bytes": 15947,
    },
}

EXPECTED_MUTATED_LEDGER_SHA256 = (
    "4712365d309df49bc42e5cb73d98e37f2bbfc98ef7522b87320612d106157cab"
)
EXPECTED_NEGATIVE_STDOUT_IDENTITY = (
    15352,
    "b701c06c9b6836689f86c6983a4b4723f8524fbf0d4065e47a41c4cbabec65fd",
)

FIXED_VERSION_MADE_BY = (3 << 8) | 20
FIXED_VERSION_NEEDED = 20
FIXED_FLAGS = 0
FIXED_COMPRESSION = 0
FIXED_DOS_TIME = 0
FIXED_DOS_DATE = 33
FIXED_INTERNAL_ATTRIBUTES = 0
FIXED_EXTERNAL_ATTRIBUTES = (stat.S_IFREG | 0o644) << 16

LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
CENTRAL_DIRECTORY_HEADER = struct.Struct("<IHHHHHHIIIHHHHHII")
END_OF_CENTRAL_DIRECTORY = struct.Struct("<IHHHHIIH")
LOCAL_FILE_HEADER_SIGNATURE = 0x04034B50
CENTRAL_DIRECTORY_HEADER_SIGNATURE = 0x02014B50
END_OF_CENTRAL_DIRECTORY_SIGNATURE = 0x06054B50

PROCESS_TIMEOUT_SECONDS = 120
MAX_PROCESS_STREAM_BYTES = 1_048_576


class StrictJSONError(ValueError):
    pass


@dataclass(frozen=True)
class ZipMember:
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
    members: tuple[ZipMember, ...]
    central_directory_offset: int
    central_directory_size: int

    def member(self, name: str) -> ZipMember:
        matches = [member for member in self.members if member.name == name]
        if len(matches) != 1:
            raise AssertionError(f"expected one ZIP member {name!r}, got {len(matches)}")
        return matches[0]

    def member_bytes(self, name: str) -> bytes:
        member = self.member(name)
        start = member.payload_offset
        return self.payload[start : start + member.payload_size]


@dataclass(frozen=True)
class ProcessCapture:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class ExecutedProof:
    capsule_a: bytes
    capsule_b: bytes
    builder_stdout_a: bytes
    builder_stdout_b: bytes
    positive_a: ProcessCapture
    positive_b: ProcessCapture
    mutated_ledger: bytes
    negative: ProcessCapture


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def _parse_int(raw: str) -> int:
    if raw == "-0":
        raise StrictJSONError("negative_zero_forbidden")
    value = int(raw, 10)
    if value < -(2**63) or value > 2**63 - 1:
        raise StrictJSONError("integer_outside_signed_64_bit")
    return value


def _reject_float(raw: str) -> Any:
    raise StrictJSONError(f"floating_point_forbidden:{raw}")


def _reject_constant(raw: str) -> Any:
    raise StrictJSONError(f"non_finite_forbidden:{raw}")


def _reject_duplicate_pairs(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise StrictJSONError(f"duplicate_decoded_key:{key}")
        output[key] = value
    return output


def strict_json_object(payload: bytes, *, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise StrictJSONError(f"{label}:utf8_bom_forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(f"{label}:strict_json_invalid:{exc}") from exc
    if not isinstance(value, dict):
        raise StrictJSONError(f"{label}:top_level_object_required")
    return value


def _normalize_string(value: str, *, label: str) -> str:
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise StrictJSONError(f"{label}:unpaired_surrogate_forbidden")
        if codepoint > 0x7F:
            if unicodedata.unidata_version != "14.0.0":
                raise StrictJSONError(f"{label}:unicode_14_required")
            if unicodedata.category(character) == "Cn":
                raise StrictJSONError(f"{label}:unassigned_codepoint_forbidden")
    return unicodedata.normalize("NFC", value)


def _normalize_json(value: Any, *, path: str = "$", depth: int = 0) -> Any:
    if depth > 256:
        raise StrictJSONError(f"{path}:maximum_depth_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -(2**63) or value > 2**63 - 1:
            raise StrictJSONError(f"{path}:integer_outside_signed_64_bit")
        return value
    if isinstance(value, str):
        return _normalize_string(value, label=path)
    if isinstance(value, list):
        return [
            _normalize_json(item, path=f"{path}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise StrictJSONError(f"{path}:object_key_not_string")
            key = _normalize_string(raw_key, label=f"{path}:key")
            if key in output:
                raise StrictJSONError(f"{path}:normalized_key_collision:{key}")
            output[key] = _normalize_json(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return output
    raise StrictJSONError(f"{path}:unsupported_type:{type(value).__name__}")


def _canonical_string(value: str) -> str:
    escapes = {
        0x08: "\\b",
        0x09: "\\t",
        0x0A: "\\n",
        0x0C: "\\f",
        0x0D: "\\r",
        0x22: '\\"',
        0x5C: "\\\\",
    }
    output = ['"']
    for character in value:
        codepoint = ord(character)
        if codepoint in escapes:
            output.append(escapes[codepoint])
        elif codepoint <= 0x1F:
            output.append(f"\\u00{codepoint:02x}")
        else:
            output.append(character)
    output.append('"')
    return "".join(output)


def _canonical_text(value: Any, *, depth: int = 0) -> str:
    if depth > 256:
        raise StrictJSONError("canonical_json_depth_exceeded")
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return _canonical_string(value)
    if isinstance(value, list):
        return "[" + ",".join(
            _canonical_text(item, depth=depth + 1) for item in value
        ) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: key.encode("utf-8"))
        return "{" + ",".join(
            _canonical_string(key)
            + ":"
            + _canonical_text(value[key], depth=depth + 1)
            for key in keys
        ) + "}"
    raise StrictJSONError(f"unsupported_canonical_type:{type(value).__name__}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    normalized = _normalize_json(dict(value))
    return _canonical_text(normalized).encode("utf-8")


def _assert_exact_identity(path: Path) -> bytes:
    assert path in EXPECTED_IDENTITIES, f"identity not declared for {path}"
    expected_size, expected_sha256, expected_blob = EXPECTED_IDENTITIES[path]
    assert path.exists(), f"required file missing: {path.relative_to(ROOT)}"
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode), (
        f"regular file required: {path.relative_to(ROOT)}"
    )
    assert not path.is_symlink(), f"symlink forbidden: {path.relative_to(ROOT)}"
    assert metadata.st_nlink == 1, f"hard link forbidden: {path.relative_to(ROOT)}"
    payload = path.read_bytes()
    assert len(payload) == expected_size
    assert sha256_bytes(payload) == expected_sha256
    assert git_blob_sha1(payload) == expected_blob
    return payload


def _assert_binding_matches_file(binding: Mapping[str, Any], path: Path) -> None:
    payload = _assert_exact_identity(path)
    assert binding["byte_identity"] == "exact_repository_file_bytes"
    assert binding["path"] == path.relative_to(ROOT).as_posix()
    assert binding["size_bytes"] == len(payload)
    assert binding["sha256"] == sha256_bytes(payload)
    assert binding["git_blob_sha1"] == git_blob_sha1(payload)


def _decode_member_name(raw: bytes) -> str:
    name = raw.decode("utf-8", errors="strict")
    assert name
    assert "\\" not in name
    assert "\x00" not in name
    assert not name.startswith("/")
    assert not name.endswith("/")
    assert all(part not in {"", ".", ".."} for part in name.split("/"))
    return name


def parse_stored_zip(
    payload: bytes,
    *,
    expected_order: Sequence[str],
    require_outer_profile: bool,
) -> ParsedZip:
    assert len(payload) >= END_OF_CENTRAL_DIRECTORY.size
    eocd_offset = len(payload) - END_OF_CENTRAL_DIRECTORY.size
    (
        signature,
        disk_number,
        central_disk,
        disk_entry_count,
        total_entry_count,
        central_size,
        central_offset,
        comment_length,
    ) = END_OF_CENTRAL_DIRECTORY.unpack_from(payload, eocd_offset)
    assert signature == END_OF_CENTRAL_DIRECTORY_SIGNATURE
    assert disk_number == 0
    assert central_disk == 0
    assert disk_entry_count == len(expected_order)
    assert total_entry_count == len(expected_order)
    assert comment_length == 0
    assert central_offset + central_size == eocd_offset

    members: list[ZipMember] = []
    cursor = central_offset
    for expected_name in expected_order:
        assert cursor + CENTRAL_DIRECTORY_HEADER.size <= eocd_offset
        fields = CENTRAL_DIRECTORY_HEADER.unpack_from(payload, cursor)
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
        assert central_signature == CENTRAL_DIRECTORY_HEADER_SIGNATURE
        assert compressed_size == uncompressed_size
        assert extra_length == 0
        assert member_comment_length == 0
        assert disk_start == 0
        name_start = cursor + CENTRAL_DIRECTORY_HEADER.size
        name_end = name_start + name_length
        assert name_end <= eocd_offset
        name = _decode_member_name(payload[name_start:name_end])
        assert name == expected_name

        local_fields = LOCAL_FILE_HEADER.unpack_from(payload, local_header_offset)
        (
            local_signature,
            local_version_needed,
            local_flags,
            local_compression,
            local_dos_time,
            local_dos_date,
            local_crc32,
            local_compressed_size,
            local_uncompressed_size,
            local_name_length,
            local_extra_length,
        ) = local_fields
        assert local_signature == LOCAL_FILE_HEADER_SIGNATURE
        assert local_version_needed == version_needed
        assert local_flags == flags
        assert local_compression == compression
        assert local_dos_time == dos_time
        assert local_dos_date == dos_date
        assert local_crc32 == crc32_value
        assert local_compressed_size == compressed_size
        assert local_uncompressed_size == uncompressed_size
        assert local_extra_length == 0
        local_name_start = local_header_offset + LOCAL_FILE_HEADER.size
        local_name_end = local_name_start + local_name_length
        assert _decode_member_name(payload[local_name_start:local_name_end]) == name
        payload_offset = local_name_end
        payload_end = payload_offset + uncompressed_size
        assert payload_end <= central_offset
        member_payload = payload[payload_offset:payload_end]
        assert zlib.crc32(member_payload) & 0xFFFFFFFF == crc32_value

        assert flags == FIXED_FLAGS
        assert compression == FIXED_COMPRESSION
        assert version_needed == FIXED_VERSION_NEEDED
        if require_outer_profile:
            assert version_made_by == FIXED_VERSION_MADE_BY
            assert dos_time == FIXED_DOS_TIME
            assert dos_date == FIXED_DOS_DATE
            assert internal_attributes == FIXED_INTERNAL_ATTRIBUTES
            assert external_attributes == FIXED_EXTERNAL_ATTRIBUTES

        members.append(
            ZipMember(
                name=name,
                local_header_offset=local_header_offset,
                central_header_offset=cursor,
                payload_offset=payload_offset,
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
        cursor = name_end

    assert cursor == eocd_offset
    assert len({member.name for member in members}) == len(members)
    assert tuple(member.name for member in members) == tuple(expected_order)
    expected_local_offset = 0
    for member in members:
        assert member.local_header_offset == expected_local_offset
        expected_local_offset = member.payload_offset + member.payload_size
    assert expected_local_offset == central_offset

    with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
        assert tuple(archive.namelist()) == tuple(expected_order)
        assert archive.comment == b""
        assert archive.testzip() is None

    return ParsedZip(
        payload=payload,
        members=tuple(members),
        central_directory_offset=central_offset,
        central_directory_size=central_size,
    )


def _capsule_source_payloads() -> tuple[bytes, ...]:
    return (
        CANONICAL_MANIFEST_PATH.read_bytes(),
        CANONICAL_LEDGER_PATH.read_bytes(),
        STANDALONE_VERIFIER_PATH.read_bytes(),
        CANONICAL_EXPECTED_REPORT_PATH.read_bytes(),
    )


def build_capsule_independently() -> bytes:
    output = bytearray()
    central_rows: list[tuple[bytes, int, int, int]] = []
    for name, member_payload in zip(CAPSULE_MEMBER_ORDER, _capsule_source_payloads()):
        name_bytes = name.encode("utf-8")
        crc32_value = zlib.crc32(member_payload) & 0xFFFFFFFF
        local_offset = len(output)
        output.extend(
            LOCAL_FILE_HEADER.pack(
                LOCAL_FILE_HEADER_SIGNATURE,
                FIXED_VERSION_NEEDED,
                FIXED_FLAGS,
                FIXED_COMPRESSION,
                FIXED_DOS_TIME,
                FIXED_DOS_DATE,
                crc32_value,
                len(member_payload),
                len(member_payload),
                len(name_bytes),
                0,
            )
        )
        output.extend(name_bytes)
        output.extend(member_payload)
        central_rows.append(
            (name_bytes, crc32_value, len(member_payload), local_offset)
        )

    central_offset = len(output)
    for name_bytes, crc32_value, member_size, local_offset in central_rows:
        output.extend(
            CENTRAL_DIRECTORY_HEADER.pack(
                CENTRAL_DIRECTORY_HEADER_SIGNATURE,
                FIXED_VERSION_MADE_BY,
                FIXED_VERSION_NEEDED,
                FIXED_FLAGS,
                FIXED_COMPRESSION,
                FIXED_DOS_TIME,
                FIXED_DOS_DATE,
                crc32_value,
                member_size,
                member_size,
                len(name_bytes),
                0,
                0,
                0,
                FIXED_INTERNAL_ATTRIBUTES,
                FIXED_EXTERNAL_ATTRIBUTES,
                local_offset,
            )
        )
        output.extend(name_bytes)

    central_size = len(output) - central_offset
    output.extend(
        END_OF_CENTRAL_DIRECTORY.pack(
            END_OF_CENTRAL_DIRECTORY_SIGNATURE,
            0,
            0,
            len(central_rows),
            len(central_rows),
            central_size,
            central_offset,
            0,
        )
    )
    return bytes(output)


def _write_exclusive(path: Path, payload: bytes, *, mode: int = 0o444) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        written = handle.write(payload)
        assert written == len(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)


def _child_build(output_path: Path) -> int:
    payload = build_capsule_independently()
    _write_exclusive(output_path, payload)
    summary = {
        "authority_effect": "none",
        "capsule_filename": output_path.name,
        "capsule_sha256": sha256_bytes(payload),
        "capsule_size_bytes": len(payload),
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "ok": True,
        "result": "independent_regression_capsule_constructed",
        "tool": "test_pulsemech_device_ledger_reproduction_capsule_execution_v0",
        "tool_version": "0.1.0",
    }
    sys.stdout.buffer.write(canonical_json_bytes(summary) + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _child_main(arguments: Sequence[str]) -> int:
    if len(arguments) != 2 or arguments[0] != "--child-build":
        print("usage: test file --child-build OUTPUT", file=sys.stderr)
        return 64
    return _child_build(Path(arguments[1]))


def _process_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
        }
    )
    return environment


def _run_process(command: Sequence[str], *, cwd: Path) -> ProcessCapture:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=_process_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=PROCESS_TIMEOUT_SECONDS,
    )
    assert len(completed.stdout) <= MAX_PROCESS_STREAM_BYTES
    assert len(completed.stderr) <= MAX_PROCESS_STREAM_BYTES
    return ProcessCapture(completed.returncode, completed.stdout, completed.stderr)


def _run_child_builder(workspace: Path) -> tuple[bytes, bytes]:
    output_path = workspace / "proof" / "pulsemech_device_ledger_reproduction_capsule_v0.zip"
    capture = _run_process(
        (
            sys.executable,
            "-P",
            os.fspath(Path(__file__).resolve()),
            "--child-build",
            os.fspath(output_path),
        ),
        cwd=ROOT,
    )
    assert capture.returncode == 0
    assert capture.stderr == b""
    assert capture.stdout.endswith(b"\n")
    assert capture.stdout.count(b"\n") == 1
    summary = strict_json_object(capture.stdout[:-1], label="child_builder_summary")
    payload = output_path.read_bytes()
    assert summary == {
        "authority_effect": "none",
        "capsule_filename": output_path.name,
        "capsule_sha256": sha256_bytes(payload),
        "capsule_size_bytes": len(payload),
        "member_order": list(CAPSULE_MEMBER_ORDER),
        "ok": True,
        "result": "independent_regression_capsule_constructed",
        "tool": "test_pulsemech_device_ledger_reproduction_capsule_execution_v0",
        "tool_version": "0.1.0",
    }
    return payload, capture.stdout


def _materialize_positive_members(
    capsule: bytes,
    workspace: Path,
) -> tuple[Path, Path, bytes]:
    parsed = parse_stored_zip(
        capsule,
        expected_order=CAPSULE_MEMBER_ORDER,
        require_outer_profile=True,
    )
    ledger = workspace / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
    verifier = workspace / "verify_pulsemech_device_ledger_v0.py"
    expected = parsed.member_bytes(CAPSULE_EXPECTED_REPORT_MEMBER_PATH)
    _write_exclusive(ledger, parsed.member_bytes(CAPSULE_LEDGER_MEMBER_PATH))
    _write_exclusive(verifier, parsed.member_bytes(CAPSULE_VERIFIER_MEMBER_PATH))
    return ledger, verifier, expected


def _verifier_command(verifier: Path, ledger: Path) -> tuple[str, ...]:
    return (
        sys.executable,
        "-P",
        os.fspath(verifier),
        os.fspath(ledger),
        "--expected-observer-fingerprint",
        EXPECTED_OBSERVER_FINGERPRINT_SHA256,
        "--reproduction-class",
        "same_environment",
        "--producer-environment-available",
    )


def _run_positive(capsule: bytes, workspace: Path) -> ProcessCapture:
    ledger, verifier, expected = _materialize_positive_members(capsule, workspace)
    capture = _run_process(_verifier_command(verifier, ledger), cwd=workspace)
    assert capture.returncode == 0
    assert capture.stderr == b""
    assert capture.stdout == expected
    report = strict_json_object(capture.stdout, label="positive_verifier_report")
    assert canonical_json_bytes(report) == capture.stdout
    assert report["ok"] is True
    assert report["result"] == "verified_with_declared_unavailability"
    assert report["failed_check_ids"] == []
    assert report["failure_stage"] is None
    assert len(report["checks"]) == 49
    assert set(report["checks"].values()) == {"passed"}
    assert report["tool"]["producer_code_imported"] is False
    assert report["reproduction_context"]["verifier_implementation_relation"] == (
        "separate_from_producer_code"
    )
    assert report["authority_boundary"]["authority_effect"] == "none"
    return capture


def mutate_package_signature(source: bytes) -> bytes:
    parsed = parse_stored_zip(
        source,
        expected_order=PULSELEDGER_MEMBER_ORDER,
        require_outer_profile=False,
    )
    target = parsed.member(PACKAGE_SIGNATURE_MEMBER_PATH)
    original_payload = parsed.member_bytes(PACKAGE_SIGNATURE_MEMBER_PATH)
    original = strict_json_object(original_payload, label="package_signature")
    assert canonical_json_bytes(original) == original_payload
    signature = original["signature_base64"]
    assert isinstance(signature, str)
    assert signature.startswith("O")

    mutated_document = copy.deepcopy(original)
    mutated_document["signature_base64"] = "P" + signature[1:]
    mutated_payload = canonical_json_bytes(mutated_document)
    assert len(mutated_payload) == len(original_payload)
    differences = [
        index
        for index, (before, after) in enumerate(zip(original_payload, mutated_payload))
        if before != after
    ]
    assert len(differences) == 1
    original_subject = dict(original)
    mutated_subject = dict(mutated_document)
    del original_subject["signature_base64"]
    del mutated_subject["signature_base64"]
    assert original_subject == mutated_subject

    mutable = bytearray(source)
    start = target.payload_offset
    mutable[start : start + target.payload_size] = mutated_payload
    crc32_value = zlib.crc32(mutated_payload) & 0xFFFFFFFF
    struct.pack_into("<I", mutable, target.local_header_offset + 14, crc32_value)
    struct.pack_into("<I", mutable, target.central_header_offset + 16, crc32_value)
    mutated = bytes(mutable)
    assert len(mutated) == len(source)
    assert sha256_bytes(mutated) == EXPECTED_MUTATED_LEDGER_SHA256

    reparsed = parse_stored_zip(
        mutated,
        expected_order=PULSELEDGER_MEMBER_ORDER,
        require_outer_profile=False,
    )
    assert reparsed.member_bytes(PACKAGE_SIGNATURE_MEMBER_PATH) == mutated_payload
    for name in PULSELEDGER_MEMBER_ORDER:
        if name != PACKAGE_SIGNATURE_MEMBER_PATH:
            assert reparsed.member_bytes(name) == parsed.member_bytes(name)

    allowed_offsets = set(
        range(target.local_header_offset + 14, target.local_header_offset + 18)
    )
    allowed_offsets.update(
        range(target.central_header_offset + 16, target.central_header_offset + 20)
    )
    allowed_offsets.add(start + differences[0])
    changed_offsets = {
        index
        for index, (before, after) in enumerate(zip(source, mutated))
        if before != after
    }
    assert changed_offsets
    assert changed_offsets.issubset(allowed_offsets)
    return mutated


def _run_negative(capsule: bytes, mutated: bytes, workspace: Path) -> ProcessCapture:
    parsed = parse_stored_zip(
        capsule,
        expected_order=CAPSULE_MEMBER_ORDER,
        require_outer_profile=True,
    )
    ledger = workspace / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
    verifier = workspace / "verify_pulsemech_device_ledger_v0.py"
    _write_exclusive(ledger, mutated)
    _write_exclusive(verifier, parsed.member_bytes(CAPSULE_VERIFIER_MEMBER_PATH))
    capture = _run_process(_verifier_command(verifier, ledger), cwd=workspace)
    assert capture.returncode == 2
    assert capture.stderr == b""
    expected_size, expected_sha256 = EXPECTED_NEGATIVE_STDOUT_IDENTITY
    assert len(capture.stdout) == expected_size
    assert sha256_bytes(capture.stdout) == expected_sha256
    assert not capture.stdout.endswith(b"\n")
    assert b"\r" not in capture.stdout
    report = strict_json_object(capture.stdout, label="negative_verifier_report")
    assert canonical_json_bytes(report) == capture.stdout
    assert report["ok"] is False
    assert report["result"] == "rejected"
    assert report["failure_stage"] == "package_signature"
    assert report["failed_check_ids"] == ["package_signature_valid"]
    assert report["checks"]["zip_crc32_valid"] == "passed"
    assert report["checks"]["package_signature_document_valid"] == "passed"
    assert report["checks"]["package_signature_subject_valid"] == "passed"
    assert report["checks"]["package_signature_valid"] == "failed"
    assert report["errors"] == [
        {
            "check_id": "package_signature_valid",
            "error_code": "signature_verification_failed",
            "member_path": PACKAGE_SIGNATURE_MEMBER_PATH,
            "record_sequence_index": None,
            "stage": "package_signature",
        }
    ]
    assert report["subject"]["carrier_sha256"] == EXPECTED_MUTATED_LEDGER_SHA256
    assert report["tool"]["producer_code_imported"] is False
    assert report["reproduction_context"]["verifier_implementation_relation"] == (
        "separate_from_producer_code"
    )
    assert report["authority_boundary"]["authority_effect"] == "none"
    return capture


@pytest.fixture(scope="module")
def executed_proof(tmp_path_factory: pytest.TempPathFactory) -> ExecutedProof:
    root = tmp_path_factory.mktemp("device-ledger-reproduction-execution-v0")
    workspace_a = root / "construction-a"
    workspace_b = root / "construction-b"
    workspace_a.mkdir()
    workspace_b.mkdir()
    capsule_a, builder_stdout_a = _run_child_builder(workspace_a)
    capsule_b, builder_stdout_b = _run_child_builder(workspace_b)

    positive_a_workspace = root / "positive-a"
    positive_b_workspace = root / "positive-b"
    positive_a_workspace.mkdir()
    positive_b_workspace.mkdir()
    positive_a = _run_positive(capsule_a, positive_a_workspace)
    positive_b = _run_positive(capsule_b, positive_b_workspace)

    parsed_a = parse_stored_zip(
        capsule_a,
        expected_order=CAPSULE_MEMBER_ORDER,
        require_outer_profile=True,
    )
    mutated = mutate_package_signature(
        parsed_a.member_bytes(CAPSULE_LEDGER_MEMBER_PATH)
    )
    negative_workspace = root / "negative"
    negative_workspace.mkdir()
    negative = _run_negative(capsule_a, mutated, negative_workspace)

    return ExecutedProof(
        capsule_a=capsule_a,
        capsule_b=capsule_b,
        builder_stdout_a=builder_stdout_a,
        builder_stdout_b=builder_stdout_b,
        positive_a=positive_a,
        positive_b=positive_b,
        mutated_ledger=mutated,
        negative=negative,
    )


def _load_canonical_result() -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    result_bytes = _assert_exact_identity(CANONICAL_RESULT_PATH)
    assert not result_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in result_bytes
    assert b"\n" not in result_bytes
    result = strict_json_object(result_bytes, label="canonical_reproduction_result")
    assert canonical_json_bytes(result) == result_bytes
    schema_bytes = _assert_exact_identity(RESULT_SCHEMA_PATH)
    schema = strict_json_object(schema_bytes, label="reproduction_result_schema")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(result)
    return result_bytes, result, schema


def test_recorded_execution_objects_have_exact_identities_and_schema() -> None:
    for path in EXPECTED_IDENTITIES:
        _assert_exact_identity(path)
    result_bytes, result, _schema = _load_canonical_result()
    capsule = _assert_exact_identity(CANONICAL_CAPSULE_PATH)
    assert result["canonical_capsule"] == {
        "byte_identity": "exact_canonical_capsule_bytes",
        "bytes_equal_capsule_a": True,
        "bytes_equal_capsule_b": True,
        "git_blob_sha1": git_blob_sha1(capsule),
        "repository_path": CANONICAL_CAPSULE_PATH.relative_to(ROOT).as_posix(),
        "selected_construction_id": "capsule_a",
        "sha256": sha256_bytes(capsule),
        "size_bytes": len(capsule),
    }
    assert result["canonical_result_storage"] == {
        "canonicalization": "pulsemech_device_canonical_json_v0",
        "cr_characters": 0,
        "generated_or_volatile_fields": "forbidden",
        "identity_location": "outside_result_to_avoid_self_reference",
        "lf_characters": 0,
        "repository_path": CANONICAL_RESULT_PATH.relative_to(ROOT).as_posix(),
        "result_self_hash": "forbidden",
        "result_self_size": "forbidden",
        "stored_bytes": "must_equal_canonical_reserialization",
        "strict_utf8": True,
        "trailing_newline": False,
        "utf8_bom": "absent",
    }
    assert len(result_bytes) == EXPECTED_IDENTITIES[CANONICAL_RESULT_PATH][0]


def test_two_isolated_independent_constructions_equal_canonical_capsule(
    executed_proof: ExecutedProof,
) -> None:
    canonical = _assert_exact_identity(CANONICAL_CAPSULE_PATH)
    assert executed_proof.capsule_a == executed_proof.capsule_b == canonical
    assert executed_proof.builder_stdout_a == executed_proof.builder_stdout_b
    parsed = parse_stored_zip(
        canonical,
        expected_order=CAPSULE_MEMBER_ORDER,
        require_outer_profile=True,
    )
    for name, source_payload in zip(CAPSULE_MEMBER_ORDER, _capsule_source_payloads()):
        assert parsed.member_bytes(name) == source_payload
    assert len(canonical) == 285144
    assert sha256_bytes(canonical) == (
        "49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678"
    )


def test_two_positive_verifier_processes_match_canonical_report(
    executed_proof: ExecutedProof,
) -> None:
    expected = _assert_exact_identity(CANONICAL_EXPECTED_REPORT_PATH)
    assert executed_proof.positive_a.returncode == 0
    assert executed_proof.positive_b.returncode == 0
    assert executed_proof.positive_a.stderr == b""
    assert executed_proof.positive_b.stderr == b""
    assert executed_proof.positive_a.stdout == expected
    assert executed_proof.positive_b.stdout == expected
    assert executed_proof.positive_a.stdout == executed_proof.positive_b.stdout


def test_targeted_crc_consistent_mutation_reaches_exact_signature_failure(
    executed_proof: ExecutedProof,
) -> None:
    canonical_ledger = _assert_exact_identity(CANONICAL_LEDGER_PATH)
    assert executed_proof.mutated_ledger != canonical_ledger
    assert len(executed_proof.mutated_ledger) == len(canonical_ledger)
    assert sha256_bytes(executed_proof.mutated_ledger) == (
        EXPECTED_MUTATED_LEDGER_SHA256
    )
    assert executed_proof.negative.returncode == 2
    assert executed_proof.negative.stderr == b""
    assert len(executed_proof.negative.stdout) == EXPECTED_NEGATIVE_STDOUT_IDENTITY[0]
    assert sha256_bytes(executed_proof.negative.stdout) == (
        EXPECTED_NEGATIVE_STDOUT_IDENTITY[1]
    )


def test_canonical_result_matches_the_executed_relations(
    executed_proof: ExecutedProof,
) -> None:
    _result_bytes, result, _schema = _load_canonical_result()
    assert result["document_type"] == "pulsemech_device_ledger_reproduction_result"
    assert result["schema_version"] == (
        "pulsemech_device_ledger_reproduction_result_v0"
    )
    assert result["record_status"] == "synthetic_reference"
    assert result["proof_scope"] == "bounded_reference_reproduction"
    assert result["carrier_class"] == "diagnostic_shadow"
    assert result["result_role"] == "orchestration_evidence"
    assert result["result"] == "bounded_reference_reproduction_completed"
    assert result["ok"] is True

    context = result["repository_context"]
    assert context == {
        "containing_commit_binding": "excluded_to_avoid_circularity",
        "payload_source_commit_sha": "0108e2c0da98c8a1fe5e739aa0f137ba6a3464e1",
        "pr_position": 2,
        "repository": "HKati/pulse-release-gates-0.1",
        "required_base_commit_sha": "722fe4e85acfaac67c283862645ac9e42c831236",
        "work_order_issue_number": 2850,
    }

    bindings = result["identity_bindings"]
    assert bindings["all_exact_identities_verified"] is True
    _assert_binding_matches_file(bindings["canonical_manifest"], CANONICAL_MANIFEST_PATH)
    _assert_binding_matches_file(
        bindings["canonicalization_profile"], CANONICALIZATION_PROFILE_PATH
    )
    _assert_binding_matches_file(bindings["canonical_pulseledger"], CANONICAL_LEDGER_PATH)
    _assert_binding_matches_file(
        bindings["standalone_verifier"], STANDALONE_VERIFIER_PATH
    )
    _assert_binding_matches_file(
        bindings["canonical_expected_positive_report"],
        CANONICAL_EXPECTED_REPORT_PATH,
    )
    _assert_binding_matches_file(
        bindings["reproduction_result_schema"], RESULT_SCHEMA_PATH
    )
    _assert_binding_matches_file(bindings["capsule_builder"], CAPSULE_BUILDER_PATH)
    _assert_binding_matches_file(
        bindings["reproduction_runner"], REPRODUCTION_RUNNER_PATH
    )
    for name, expected in EXPECTED_PR1_BINDINGS.items():
        binding = bindings[name]
        assert binding["byte_identity"] == "exact_repository_file_bytes"
        assert {
            key: binding[key]
            for key in ("git_blob_sha1", "path", "sha256", "size_bytes")
        } == expected

    assert result["reference_environment"]["container_image"] == (
        EXPECTED_REFERENCE_IMAGE
    )
    attestation = result["reference_environment_attestation"]
    assert (attestation["size_bytes"], attestation["sha256"]) == (
        EXPECTED_ATTESTATION_IDENTITY
    )
    assert attestation["attestation"]["container_image_digest"] == (
        EXPECTED_REFERENCE_DIGEST
    )
    assert attestation["attestation"]["container_image_repo_digest_verified"] is True
    assert attestation["attestation"]["container_launch_by_exact_digest"] is True
    assert result["execution_boundary"] == {
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
    }

    assert all(result["repeated_construction"].values())
    constructions = result["capsule_constructions"]
    assert constructions["construction_count"] == 2
    assert constructions["isolation"] == {
        "capsule_a_computed_archive_bytes_reused_by_b": False,
        "capsule_a_materialized_members_reused_by_b": False,
        "capsule_a_output_reused_by_b": False,
        "capsule_a_temporary_files_reused_by_b": False,
        "separate_builder_processes": True,
        "separate_output_directories": True,
        "separate_temporary_workspaces": True,
    }
    for construction_id in ("capsule_a", "capsule_b"):
        construction = constructions[construction_id]
        assert construction["construction_id"] == construction_id
        assert construction["capsule"]["sha256"] == sha256_bytes(
            executed_proof.capsule_a
        )
        assert construction["capsule"]["size_bytes"] == len(
            executed_proof.capsule_a
        )
        assert construction["builder_process"]["exit_status"] == 0
        assert construction["builder_process"]["stderr"] == {
            "byte_identity": "exact_process_stream_bytes",
            "framing": "empty",
            "sha256": EXPECTED_EMPTY_SHA256,
            "size_bytes": 0,
        }

    positives = result["positive_reproductions"]
    assert [item["run_id"] for item in positives] == ["positive_a", "positive_b"]
    for item, capture in zip(
        positives,
        (executed_proof.positive_a, executed_proof.positive_b),
    ):
        process = item["verifier_process"]
        assert process["exit_status"] == capture.returncode == 0
        assert process["stdout"]["size_bytes"] == len(capture.stdout)
        assert process["stdout"]["sha256"] == sha256_bytes(capture.stdout)
        assert process["stderr"]["size_bytes"] == 0
        assert process["stderr"]["sha256"] == EXPECTED_EMPTY_SHA256
        assert process["report"]["passed_check_count"] == 49
        assert process["report"]["check_count"] == 49
        assert process["report"]["failed_check_ids"] == []
        assert process["producer_verdict_trusted"] is False

    mutation = result["targeted_mutation"]
    assert mutation["original_character"] == "O"
    assert mutation["replacement_character"] == "P"
    assert mutation["target_inner_member_path"] == PACKAGE_SIGNATURE_MEMBER_PATH
    assert mutation["crc32_repair"] == {
        "central_directory_crc32_recomputed": True,
        "local_header_crc32_recomputed": True,
    }
    assert all(mutation["preservation"].values())
    assert mutation["mutated_artifact"]["sha256"] == sha256_bytes(
        executed_proof.mutated_ledger
    )
    assert mutation["mutated_artifact"]["size_bytes"] == len(
        executed_proof.mutated_ledger
    )

    negative = result["negative_reproduction"]
    process = negative["verifier_process"]
    assert process["exit_status"] == executed_proof.negative.returncode == 2
    assert process["stdout"]["size_bytes"] == len(executed_proof.negative.stdout)
    assert process["stdout"]["sha256"] == sha256_bytes(
        executed_proof.negative.stdout
    )
    assert process["stderr"]["size_bytes"] == 0
    assert process["report"]["failed_check_ids"] == ["package_signature_valid"]
    assert process["report"]["failure_stage"] == "package_signature"
    assert process["report"]["error"] == {
        "check_id": "package_signature_valid",
        "error_code": "signature_verification_failed",
        "member_path": PACKAGE_SIGNATURE_MEMBER_PATH,
        "stage": "package_signature",
    }

    preservation = result["protected_source_preservation"]
    assert preservation["before"] == preservation["after"]
    assert preservation["source_count"] == 10
    assert preservation["all_exact_bytes_unchanged"] is True
    assert preservation["all_git_blob_identities_unchanged"] is True
    assert preservation["drift_detected"] is False
    assert preservation["repository_source_write_attempted"] is False


def _mutate_result_for_schema_case(
    result: dict[str, Any],
    case: str,
) -> None:
    if case == "top_level_ok_false":
        result["ok"] = False
    elif case == "authority_expansion":
        result["authority_boundary"]["authority_effect"] = "release_authority"
    elif case == "capsule_equality_false":
        result["repeated_construction"]["capsule_bytes_equal"] = False
    elif case == "positive_exit_nonzero":
        result["positive_reproductions"][0]["verifier_process"]["exit_status"] = 1
    elif case == "negative_failed_check_changed":
        result["negative_reproduction"]["verifier_process"]["report"][
            "failed_check_ids"
        ] = ["zip_crc32_valid"]
    elif case == "container_identity_unverified":
        result["execution_boundary"]["container_image_identity_verified"] = False
    elif case == "source_drift_true":
        result["protected_source_preservation"]["drift_detected"] = True
    elif case == "unexpected_field":
        result["generated_at"] = "2026-08-31T00:00:00Z"
    else:
        raise AssertionError(f"unknown schema mutation case: {case}")


@pytest.mark.parametrize(
    "case",
    (
        "top_level_ok_false",
        "authority_expansion",
        "capsule_equality_false",
        "positive_exit_nonzero",
        "negative_failed_check_changed",
        "container_identity_unverified",
        "source_drift_true",
        "unexpected_field",
    ),
)
def test_result_schema_rejects_incomplete_or_expanded_relations(case: str) -> None:
    _result_bytes, canonical, schema = _load_canonical_result()
    mutated = copy.deepcopy(canonical)
    _mutate_result_for_schema_case(mutated, case)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(mutated))
    assert errors, f"schema accepted forbidden mutation: {case}"


def _imported_module_names(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_builder_runner_and_verifier_implementation_boundaries_remain_separate() -> None:
    builder = _assert_exact_identity(CAPSULE_BUILDER_PATH)
    runner = _assert_exact_identity(REPRODUCTION_RUNNER_PATH)
    verifier = _assert_exact_identity(STANDALONE_VERIFIER_PATH)
    builder_tree = ast.parse(builder, filename=str(CAPSULE_BUILDER_PATH))
    runner_tree = ast.parse(runner, filename=str(REPRODUCTION_RUNNER_PATH))
    ast.parse(verifier, filename=str(STANDALONE_VERIFIER_PATH))
    for modules in (
        _imported_module_names(builder_tree),
        _imported_module_names(runner_tree),
    ):
        assert "verify_pulsemech_device_ledger_v0" not in modules
        assert all(
            not module.endswith(".verify_pulsemech_device_ledger_v0")
            for module in modules
        )
    assert b"subprocess" in runner
    assert b"tools/verify_pulsemech_device_ledger_v0.py" in runner
    _result_bytes, result, _schema = _load_canonical_result()
    assert result["implementation_boundary"] == {
        "existing_verifier_modification": "forbidden",
        "new_verifier": "none",
        "producer_verdict_trusted": False,
        "reproduction_result_role": "orchestration_evidence_not_verifier_verdict",
        "runner_role": "orchestration_only",
        "verification_semantics_change": "none",
        "verifier_execution": "separate_process",
        "verifier_import_by_runner": "forbidden",
    }


def test_claim_and_authority_boundaries_remain_exactly_non_authoritative() -> None:
    _result_bytes, result, _schema = _load_canonical_result()
    assert result["claim_boundary"] == {
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
    }
    assert result["authority_boundary"] == {
        "authority_effect": "none",
        "capsule_is_release_authority": False,
        "changes_release_authority": False,
        "creates_device_control_authority": False,
        "creates_gate_result": False,
        "creates_release_decision": False,
        "external_operator_approval_required": False,
        "reproduction_result_is_release_authority": False,
    }


if __name__ == "__main__":
    raise SystemExit(_child_main(sys.argv[1:]))
