#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import os
import re
import stat
import struct
import sys
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

TOOL_NAME = "verify_pulsemech_device_ledger_v0"
TOOL_VERSION = "0.1.0"
TOOL_SOURCE_PATH = "tools/verify_pulsemech_device_ledger_v0.py"
REPORT_SCHEMA_VERSION = "pulsemech_device_ledger_verification_report_v0"
REPORT_DOCUMENT_TYPE = "pulsemech_device_ledger_verification_report"

PACKAGE_FORMAT = "pulseledger_zip_v0"
SIGNATURE_SUITE = "ecdsa-p256-sha256"
PUBLIC_KEY_ENCODING = "x963_uncompressed"
SIGNATURE_ENCODING = "ieee_p1363_fixed_width"

CANONICALIZATION_PROFILE_PATH = "contracts/pulsemech_device_canonical_json_v0.json"
OBSERVATION_CONTRACT_PATH = "contracts/pulsemech_ios_observation_contract_v0.json"
OBSERVER_PUBLIC_KEY_PATH = "keys/observer-public-key-v0.bin"
LEDGER_PATH = "ledger/pulsemech_device_transition_ledger_v0.json"
MANIFEST_PATH = "manifest/pulsemech_device_ledger_manifest_v0.json"
MANIFEST_SCHEMA_PATH = "schemas/pulsemech_device_ledger_manifest_v0.schema.json"
SIGNATURE_SCHEMA_PATH = "schemas/pulsemech_device_signature_v0.schema.json"
LEDGER_SCHEMA_PATH = "schemas/pulsemech_device_transition_ledger_v0.schema.json"
CHECKPOINT_SIGNATURE_PATH = "signatures/checkpoint-signature-v0.json"
PACKAGE_SIGNATURE_PATH = "signatures/package-signature-v0.json"

EXPECTED_MEMBER_SPECS: tuple[tuple[str, str, str], ...] = (
    (CANONICALIZATION_PROFILE_PATH, "canonicalization_profile", "application/json"),
    (OBSERVATION_CONTRACT_PATH, "ios_observation_contract", "application/json"),
    (OBSERVER_PUBLIC_KEY_PATH, "observer_public_key", "application/octet-stream"),
    (LEDGER_PATH, "transition_ledger", "application/json"),
    (MANIFEST_PATH, "ledger_manifest", "application/json"),
    (MANIFEST_SCHEMA_PATH, "ledger_manifest_schema", "application/schema+json"),
    (SIGNATURE_SCHEMA_PATH, "signature_schema", "application/schema+json"),
    (LEDGER_SCHEMA_PATH, "transition_ledger_schema", "application/schema+json"),
    (CHECKPOINT_SIGNATURE_PATH, "checkpoint_signature", "application/json"),
    (PACKAGE_SIGNATURE_PATH, "package_signature", "application/json"),
)
EXPECTED_MEMBERS = frozenset(path for path, _, _ in EXPECTED_MEMBER_SPECS)
PAYLOAD_MEMBER_SPECS: tuple[tuple[str, str, str], ...] = (
    (CANONICALIZATION_PROFILE_PATH, "canonicalization_profile", "application/json"),
    (OBSERVATION_CONTRACT_PATH, "ios_observation_contract", "application/json"),
    (OBSERVER_PUBLIC_KEY_PATH, "observer_public_key", "application/octet-stream"),
    (LEDGER_PATH, "transition_ledger", "application/json"),
    (MANIFEST_SCHEMA_PATH, "ledger_manifest_schema", "application/schema+json"),
    (SIGNATURE_SCHEMA_PATH, "signature_schema", "application/schema+json"),
    (LEDGER_SCHEMA_PATH, "transition_ledger_schema", "application/schema+json"),
    (CHECKPOINT_SIGNATURE_PATH, "checkpoint_signature", "application/json"),
)

CANONICALIZATION_PROFILE_SHA256 = "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550"
CANONICALIZATION_PROFILE_BYTES = 2719
OBSERVATION_CONTRACT_SHA256 = "e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2"
OBSERVATION_CONTRACT_BYTES = 9893
MANIFEST_SCHEMA_SHA256 = "bf8126db9a9c5c40f1dbe3ad835ae7711a98d77fa8b3a59016f4ebd406d0ce3d"
MANIFEST_SCHEMA_BYTES = 19913
SIGNATURE_SCHEMA_SHA256 = "80304b08b73f3c05092909e7917240af94121e2c15b9305440a7e01460c049c0"
SIGNATURE_SCHEMA_BYTES = 5031
LEDGER_SCHEMA_SHA256 = "58eddf75d9c89fef4aa3787e3e4db4d86624f4a387b2a33a3c2fd1f972d6c07f"
LEDGER_SCHEMA_BYTES = 54069

CONTRACT_BINDINGS = {
    "canonicalization_profile": (
        CANONICALIZATION_PROFILE_PATH,
        CANONICALIZATION_PROFILE_SHA256,
        CANONICALIZATION_PROFILE_BYTES,
        "canonicalization_profile_binding_valid",
    ),
    "ios_observation_contract": (
        OBSERVATION_CONTRACT_PATH,
        OBSERVATION_CONTRACT_SHA256,
        OBSERVATION_CONTRACT_BYTES,
        "ios_observation_contract_binding_valid",
    ),
    "ledger_manifest_schema": (
        MANIFEST_SCHEMA_PATH,
        MANIFEST_SCHEMA_SHA256,
        MANIFEST_SCHEMA_BYTES,
        "manifest_schema_binding_valid",
    ),
    "signature_schema": (
        SIGNATURE_SCHEMA_PATH,
        SIGNATURE_SCHEMA_SHA256,
        SIGNATURE_SCHEMA_BYTES,
        "signature_schema_binding_valid",
    ),
    "transition_ledger_schema": (
        LEDGER_SCHEMA_PATH,
        LEDGER_SCHEMA_SHA256,
        LEDGER_SCHEMA_BYTES,
        "transition_ledger_schema_binding_valid",
    ),
}

MAX_CARRIER_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_JSON_DEPTH = 256
MAX_RECORDS = 100_000
SIGNED_64_MIN = -(2**63)
SIGNED_64_MAX = 2**63 - 1

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
ASCII_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:/+\-]+$")
SAFE_MEMBER_RE = re.compile(r"^[A-Za-z0-9._/+\-]+$")
CARRIER_NAME_RE = re.compile(r"^[A-Za-z0-9._+\-]+\.pulseledger$")
ERROR_CODE_RE = re.compile(r"^[a-z0-9_]{1,128}$")

P256_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
P256_A = P256_P - 3
P256_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
P256_GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
P256_GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5
P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
P256_G = (P256_GX, P256_GY)

CHECKPOINT_SIGNATURE_DOMAIN = b"PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0"
PACKAGE_SIGNATURE_DOMAIN = b"PULSEMECH-DEVICE-LEDGER-PACKAGE-V0"

CHECK_IDS: tuple[str, ...] = (
    "input_regular_file",
    "input_not_symlink",
    "carrier_size_within_limit",
    "zip_end_of_central_directory_valid",
    "zip_member_names_valid",
    "zip_exact_member_set_valid",
    "zip_member_types_valid",
    "zip_compression_valid",
    "zip_timestamp_policy_valid",
    "zip_crc32_valid",
    "zip_local_central_directory_consistent",
    "zip_no_trailing_data",
    "manifest_strict_json_valid",
    "manifest_canonical_json_valid",
    "manifest_schema_valid",
    "manifest_payload_inventory_valid",
    "manifest_ledger_binding_valid",
    "manifest_observer_binding_valid",
    "manifest_signature_contract_valid",
    "payload_member_digests_valid",
    "payload_member_sizes_valid",
    "canonicalization_profile_binding_valid",
    "ios_observation_contract_binding_valid",
    "manifest_schema_binding_valid",
    "signature_schema_binding_valid",
    "transition_ledger_schema_binding_valid",
    "observer_public_key_encoding_valid",
    "observer_public_key_curve_membership_valid",
    "observer_public_key_fingerprint_valid",
    "ledger_strict_json_valid",
    "ledger_canonical_json_valid",
    "ledger_schema_valid",
    "ledger_identity_binding_valid",
    "record_digests_valid",
    "record_chain_valid",
    "record_sequence_valid",
    "session_relations_valid",
    "coverage_relations_valid",
    "event_endpoint_bindings_valid",
    "transition_relations_valid",
    "checkpoint_closure_valid",
    "checkpoint_signature_document_valid",
    "checkpoint_signature_subject_valid",
    "checkpoint_signature_valid",
    "package_signature_document_valid",
    "package_signature_subject_valid",
    "package_signature_valid",
    "claim_boundary_preserved",
    "authority_boundary_preserved",
)
CHECK_INDEX = {check_id: index for index, check_id in enumerate(CHECK_IDS)}

FAILURE_STAGES: tuple[str, ...] = (
    "input_boundary",
    "zip_structure",
    "manifest_admission",
    "payload_identity",
    "contract_binding",
    "observer_identity",
    "ledger_admission",
    "record_chain",
    "semantic_relations",
    "checkpoint_signature",
    "package_signature",
    "claim_boundary",
    "authority_boundary",
)
STAGE_INDEX = {stage: index for index, stage in enumerate(FAILURE_STAGES)}

EXPECTED_AUTHORITY_BOUNDARY = {
    "authority_effect": "none",
    "changes_release_authority": False,
    "creates_device_control_authority": False,
    "creates_release_decision": False,
}
EXPECTED_LEDGER_CLAIM_BOUNDARY = {
    "causal_completion_claim": "none",
    "continuous_monitoring_claim": "none",
    "device_security_claim": "none",
    "malware_claim": "none",
    "physical_measurement_claim": "none",
    "release_authority_effect": "none",
    "system_wide_network_claim": "none",
}
EXPECTED_PACKAGE_CLAIM_BOUNDARY = {
    "causal_completion_claim": "none",
    "continuous_monitoring_claim": "none",
    "device_security_claim": "none",
    "external_validation_claim": "none",
    "malware_claim": "none",
    "physical_measurement_claim": "none",
}

RECORD_TYPES = (
    "session_boundary",
    "state_snapshot",
    "observation_event",
    "coverage_interval",
    "transition",
    "checkpoint",
)
NETWORK_FIELD_PATHS = (
    "/network_path/available_interface_types",
    "/network_path/is_constrained",
    "/network_path/is_expensive",
    "/network_path/status",
    "/network_path/supports_dns",
    "/network_path/supports_ipv4",
    "/network_path/supports_ipv6",
    "/network_path/used_interface_types",
)
AVAILABLE_INTERFACE_ORDER = {
    "wifi": 0,
    "cellular": 1,
    "wired_ethernet": 2,
    "loopback": 3,
    "other": 4,
    "unknown": 5,
}
USED_INTERFACE_ORDER = {
    "wifi": 0,
    "cellular": 1,
    "wired_ethernet": 2,
    "loopback": 3,
    "other": 4,
}


class VerificationError(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        check_id: str,
        error_code: str,
        member_path: str | None = None,
        record_sequence_index: int | None = None,
    ) -> None:
        super().__init__(error_code)
        self.stage = stage
        self.check_id = check_id
        self.error_code = error_code
        self.member_path = member_path
        self.record_sequence_index = record_sequence_index


class StrictJsonError(ValueError):
    pass


class CanonicalizationError(ValueError):
    pass


class SchemaValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ZipMember:
    path: str
    crc32: int
    compressed_size: int
    uncompressed_size: int
    local_header_offset: int
    data_offset: int
    data_end: int
    payload: bytes
    compression_method: int
    flags: int
    dos_time: int
    dos_date: int
    create_system: int
    external_attr: int


@dataclass(frozen=True)
class PackageData:
    carrier_bytes: bytes
    carrier_sha256: str
    members: dict[str, ZipMember]
    total_uncompressed_bytes: int


@dataclass
class LedgerResult:
    ledger_id: str
    record_status: str
    ledger_sha256: str
    ledger_size_bytes: int
    record_count: int
    record_type_counts: dict[str, int]
    first_record_sha256: str
    terminal_record_sha256: str
    checkpoint_record_sha256: str
    checkpoint_record: Mapping[str, Any]
    continuous_coverage_interval_count: int
    interrupted_coverage_interval_count: int
    event_bound_transition_count: int
    endpoint_difference_only_transition_count: int
    unavailable_initiating_source_transition_count: int


@dataclass
class VerificationState:
    carrier_path: Path
    reproduction_class: str
    producer_environment_available: bool
    source_revision: str | None
    expected_observer_fingerprint: str | None
    verifier_source_sha256: str
    checks: dict[str, str] = field(
        default_factory=lambda: {check_id: "not_reached" for check_id in CHECK_IDS}
    )
    errors: list[dict[str, Any]] = field(default_factory=list)
    failure_stage: str | None = None
    carrier_sha256: str | None = None
    carrier_size_bytes: int | None = None
    package: PackageData | None = None
    manifest: Mapping[str, Any] | None = None
    manifest_sha256: str | None = None
    manifest_size_bytes: int | None = None
    ledger: Mapping[str, Any] | None = None
    ledger_result: LedgerResult | None = None
    observer_public_key: bytes | None = None
    observer_point: tuple[int, int] | None = None
    observer_fingerprint: str | None = None
    checkpoint_signature_document: Mapping[str, Any] | None = None
    checkpoint_signature_document_sha256: str | None = None
    checkpoint_signature_document_size: int | None = None
    checkpoint_signature_input_sha256: str | None = None
    package_signature_document: Mapping[str, Any] | None = None
    package_signature_document_sha256: str | None = None
    package_signature_document_size: int | None = None
    package_signature_input_sha256: str | None = None
    contract_bindings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def pass_check(self, check_id: str) -> None:
        self.checks[check_id] = "passed"

    def fail(
        self,
        *,
        stage: str,
        check_id: str,
        error_code: str,
        member_path: str | None = None,
        record_sequence_index: int | None = None,
    ) -> None:
        if stage not in STAGE_INDEX:
            raise RuntimeError(f"unknown failure stage: {stage}")
        if check_id not in CHECK_INDEX:
            raise RuntimeError(f"unknown check id: {check_id}")
        if ERROR_CODE_RE.fullmatch(error_code) is None:
            raise RuntimeError(f"invalid error code: {error_code}")
        self.checks[check_id] = "failed"
        if self.failure_stage is None or STAGE_INDEX[stage] < STAGE_INDEX[self.failure_stage]:
            self.failure_stage = stage
        self.errors.append(
            {
                "stage": stage,
                "check_id": check_id,
                "error_code": error_code,
                "member_path": member_path,
                "record_sequence_index": record_sequence_index,
            }
        )
        raise VerificationError(
            stage=stage,
            check_id=check_id,
            error_code=error_code,
            member_path=member_path,
            record_sequence_index=record_sequence_index,
        )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require(condition: bool, *, state: VerificationState, stage: str, check_id: str, error_code: str, member_path: str | None = None, record_sequence_index: int | None = None) -> None:
    if not condition:
        state.fail(
            stage=stage,
            check_id=check_id,
            error_code=error_code,
            member_path=member_path,
            record_sequence_index=record_sequence_index,
        )


def _require_mapping(value: Any, *, code: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{code}_not_object")
    return value


def _require_exact_keys(value: Any, expected: Iterable[str], *, code: str) -> Mapping[str, Any]:
    mapping = _require_mapping(value, code=code)
    expected_set = set(expected)
    if set(mapping) != expected_set:
        raise ValueError(f"{code}_key_set_mismatch")
    return mapping


def _require_ascii_string(value: Any, *, code: str, maximum: int | None = None) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{code}_not_nonempty_string")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"{code}_too_long")
    if any(ord(character) > 0x7F for character in value):
        raise ValueError(f"{code}_not_ascii")
    return value


def _require_identifier(value: Any, *, code: str) -> str:
    text = _require_ascii_string(value, code=code, maximum=256)
    if ASCII_IDENTIFIER_RE.fullmatch(text) is None:
        raise ValueError(f"{code}_invalid")
    return text


def _require_sha256(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{code}_invalid")
    return value


def _require_i63(value: Any, *, code: str, positive: bool = False) -> int:
    if not _is_int(value):
        raise ValueError(f"{code}_not_integer")
    minimum = 1 if positive else 0
    if value < minimum or value > SIGNED_64_MAX:
        raise ValueError(f"{code}_out_of_range")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise StrictJsonError("duplicate_decoded_key")
        output[key] = value
    return output


def _parse_int64(token: str) -> int:
    if token == "-0":
        raise StrictJsonError("negative_zero_forbidden")
    value = int(token, 10)
    if value < SIGNED_64_MIN or value > SIGNED_64_MAX:
        raise StrictJsonError("integer_outside_signed_64_bit")
    return value


def _reject_float(token: str) -> None:
    raise StrictJsonError("floating_point_forbidden")


def _reject_constant(token: str) -> None:
    raise StrictJsonError("non_finite_forbidden")


def _normalize_json_value(value: Any, *, ascii_only: bool, depth: int = 0) -> Any:
    if depth > MAX_JSON_DEPTH:
        raise StrictJsonError("maximum_json_depth_exceeded")
    if value is None or isinstance(value, bool) or _is_int(value):
        return value
    if isinstance(value, float):
        raise StrictJsonError("floating_point_forbidden")
    if isinstance(value, str):
        for character in value:
            codepoint = ord(character)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise StrictJsonError("unpaired_surrogate_forbidden")
            if ascii_only and codepoint > 0x7F:
                raise StrictJsonError("non_ascii_string_forbidden_in_v0_domain")
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [
            _normalize_json_value(item, ascii_only=ascii_only, depth=depth + 1)
            for item in value
        ]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise StrictJsonError("non_string_object_key")
            key = _normalize_json_value(raw_key, ascii_only=ascii_only, depth=depth + 1)
            if key in output:
                raise StrictJsonError("normalized_key_collision")
            output[key] = _normalize_json_value(
                raw_value,
                ascii_only=ascii_only,
                depth=depth + 1,
            )
        return output
    raise StrictJsonError("unsupported_json_value")


def decode_strict_json(data: bytes, *, source: str, ascii_only: bool) -> Mapping[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError("utf8_bom_forbidden")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJsonError("malformed_utf8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_int=_parse_int64,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except StrictJsonError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError("malformed_json") from exc
    if not isinstance(value, dict):
        raise StrictJsonError("top_level_object_required")
    normalized = _normalize_json_value(value, ascii_only=ascii_only)
    if not isinstance(normalized, dict):
        raise StrictJsonError("top_level_object_required")
    return normalized


def _canonical_string(value: str) -> str:
    pieces = ['"']
    short = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
    }
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise CanonicalizationError("unpaired_surrogate_forbidden")
        if character in short:
            pieces.append(short[character])
        elif codepoint <= 0x1F:
            pieces.append(f"\\u{codepoint:04x}")
        else:
            pieces.append(character)
    pieces.append('"')
    return "".join(pieces)


def _canonical_text(value: Any, *, depth: int = 0) -> str:
    if depth > MAX_JSON_DEPTH:
        raise CanonicalizationError("maximum_json_depth_exceeded")
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if _is_int(value):
        if value < SIGNED_64_MIN or value > SIGNED_64_MAX:
            raise CanonicalizationError("integer_outside_signed_64_bit")
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError("floating_point_forbidden")
    if isinstance(value, str):
        return _canonical_string(value)
    if isinstance(value, list):
        return "[" + ",".join(
            _canonical_text(item, depth=depth + 1) for item in value
        ) + "]"
    if isinstance(value, dict):
        entries: list[str] = []
        keys = sorted(value, key=lambda item: item.encode("utf-8"))
        for key in keys:
            if not isinstance(key, str):
                raise CanonicalizationError("non_string_object_key")
            entries.append(
                _canonical_string(key)
                + ":"
                + _canonical_text(value[key], depth=depth + 1)
            )
        return "{" + ",".join(entries) + "}"
    raise CanonicalizationError("unsupported_json_value")


def canonical_json_bytes(value: Any) -> bytes:
    return _canonical_text(value).encode("utf-8")


def parse_canonical_json(data: bytes, *, source: str) -> Mapping[str, Any]:
    value = decode_strict_json(data, source=source, ascii_only=True)
    rendered = canonical_json_bytes(value)
    if data != rendered:
        raise CanonicalizationError("stored_bytes_not_canonical")
    return value


def _json_pointer(root: Any, reference: str) -> Any:
    if not reference.startswith("#/"):
        raise SchemaValidationError("external_or_nonlocal_ref_forbidden")
    cursor = root
    for raw in reference[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(cursor, dict) or token not in cursor:
            raise SchemaValidationError("unresolved_internal_ref")
        cursor = cursor[token]
    return cursor


def _schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return _is_int(value)
    if expected == "number":
        return (_is_int(value) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _schema_equal(left: Any, right: Any) -> bool:
    if _is_int(left) and _is_int(right):
        return left == right
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    return left == right


def validate_schema(instance: Any, schema: Any, *, root: Mapping[str, Any], path: str = "$", depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise SchemaValidationError("schema_validation_depth_exceeded")
    if schema is True:
        return
    if schema is False:
        raise SchemaValidationError(f"false_schema:{path}")
    if not isinstance(schema, dict):
        raise SchemaValidationError("schema_node_not_object")
    if "$ref" in schema:
        target = _json_pointer(root, schema["$ref"])
        validate_schema(instance, target, root=root, path=path, depth=depth + 1)
        siblings = {key: value for key, value in schema.items() if key != "$ref"}
        if siblings:
            validate_schema(instance, siblings, root=root, path=path, depth=depth + 1)
        return
    if "allOf" in schema:
        for branch in schema["allOf"]:
            validate_schema(instance, branch, root=root, path=path, depth=depth + 1)
    if "anyOf" in schema:
        successes = 0
        for branch in schema["anyOf"]:
            try:
                validate_schema(instance, branch, root=root, path=path, depth=depth + 1)
            except SchemaValidationError:
                continue
            successes += 1
        if successes == 0:
            raise SchemaValidationError(f"any_of_failed:{path}")
    if "oneOf" in schema:
        successes = 0
        for branch in schema["oneOf"]:
            try:
                validate_schema(instance, branch, root=root, path=path, depth=depth + 1)
            except SchemaValidationError:
                continue
            successes += 1
        if successes != 1:
            raise SchemaValidationError(f"one_of_failed:{path}:{successes}")
    if "if" in schema:
        condition_matches = True
        try:
            validate_schema(instance, schema["if"], root=root, path=path, depth=depth + 1)
        except SchemaValidationError:
            condition_matches = False
        if condition_matches and "then" in schema:
            validate_schema(instance, schema["then"], root=root, path=path, depth=depth + 1)
        if not condition_matches and "else" in schema:
            validate_schema(instance, schema["else"], root=root, path=path, depth=depth + 1)
    if "type" in schema:
        expected_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_schema_type_matches(instance, expected) for expected in expected_types):
            raise SchemaValidationError(f"type_mismatch:{path}")
    if "const" in schema and not _schema_equal(instance, schema["const"]):
        raise SchemaValidationError(f"const_mismatch:{path}")
    if "enum" in schema and not any(_schema_equal(instance, candidate) for candidate in schema["enum"]):
        raise SchemaValidationError(f"enum_mismatch:{path}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaValidationError(f"min_length:{path}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SchemaValidationError(f"max_length:{path}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise SchemaValidationError(f"pattern_mismatch:{path}")
    if _is_int(instance) or isinstance(instance, float):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"minimum:{path}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"maximum:{path}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SchemaValidationError(f"min_items:{path}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaValidationError(f"max_items:{path}")
        if schema.get("uniqueItems") is True:
            seen: set[bytes] = set()
            for item in instance:
                identity = canonical_json_bytes(item)
                if identity in seen:
                    raise SchemaValidationError(f"unique_items:{path}")
                seen.add(identity)
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            for index, subschema in enumerate(prefix):
                if index >= len(instance):
                    break
                validate_schema(instance[index], subschema, root=root, path=f"{path}[{index}]", depth=depth + 1)
            if schema.get("items") is False and len(instance) > len(prefix):
                raise SchemaValidationError(f"additional_items_forbidden:{path}")
            if isinstance(schema.get("items"), dict):
                for index in range(len(prefix), len(instance)):
                    validate_schema(instance[index], schema["items"], root=root, path=f"{path}[{index}]", depth=depth + 1)
        elif isinstance(schema.get("items"), dict):
            for index, item in enumerate(instance):
                validate_schema(item, schema["items"], root=root, path=f"{path}[{index}]", depth=depth + 1)
        elif schema.get("items") is False and instance:
            raise SchemaValidationError(f"items_forbidden:{path}")
    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise SchemaValidationError(f"required_missing:{path}/{key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, subschema in properties.items():
                if key in instance:
                    validate_schema(instance[key], subschema, root=root, path=f"{path}/{key}", depth=depth + 1)
        additional = schema.get("additionalProperties", True)
        if additional is False:
            unexpected = set(instance) - set(properties)
            if unexpected:
                raise SchemaValidationError(f"additional_properties:{path}")
        elif isinstance(additional, dict):
            for key in set(instance) - set(properties):
                validate_schema(instance[key], additional, root=root, path=f"{path}/{key}", depth=depth + 1)


def _read_stable_carrier(path: Path, state: VerificationState) -> bytes:
    try:
        metadata = os.lstat(path)
    except OSError:
        state.fail(
            stage="input_boundary",
            check_id="input_regular_file",
            error_code="input_stat_failed",
        )
    if not stat.S_ISREG(metadata.st_mode):
        state.fail(
            stage="input_boundary",
            check_id="input_regular_file",
            error_code="input_not_regular_file",
        )
    state.pass_check("input_regular_file")
    if stat.S_ISLNK(metadata.st_mode):
        state.fail(
            stage="input_boundary",
            check_id="input_not_symlink",
            error_code="input_symlink_forbidden",
        )
    state.pass_check("input_not_symlink")
    if metadata.st_size <= 0 or metadata.st_size > MAX_CARRIER_BYTES:
        state.fail(
            stage="input_boundary",
            check_id="carrier_size_within_limit",
            error_code="carrier_size_out_of_bounds",
        )
    state.pass_check("carrier_size_within_limit")

    flags = os.O_RDONLY | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError:
        state.fail(
            stage="input_boundary",
            check_id="input_not_symlink",
            error_code="input_open_failed",
        )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            state.fail(
                stage="input_boundary",
                check_id="input_regular_file",
                error_code="opened_input_not_regular",
            )
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            state.fail(
                stage="input_boundary",
                check_id="input_not_symlink",
                error_code="input_identity_changed_before_read",
            )
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_CARRIER_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_CARRIER_BYTES:
                state.fail(
                    stage="input_boundary",
                    check_id="carrier_size_within_limit",
                    error_code="carrier_size_out_of_bounds",
                )
        after = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            state.fail(
                stage="input_boundary",
                check_id="input_regular_file",
                error_code="input_changed_during_read",
            )
        payload = b"".join(chunks)
        if len(payload) != after.st_size:
            state.fail(
                stage="input_boundary",
                check_id="carrier_size_within_limit",
                error_code="carrier_size_changed_during_read",
            )
        return payload
    finally:
        os.close(descriptor)


def _safe_member_name(name: str) -> bool:
    if not name or len(name) > 256:
        return False
    if name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    if SAFE_MEMBER_RE.fullmatch(name) is None:
        return False
    pure = PurePosixPath(name)
    if pure.is_absolute() or pure.as_posix() != name:
        return False
    return all(part not in {"", ".", ".."} for part in pure.parts)


def _find_eocd(carrier: bytes, state: VerificationState) -> tuple[int, int, int]:
    signature = b"PK\x05\x06"
    position = carrier.rfind(signature)
    if position < 0 or position + 22 > len(carrier):
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_eocd_missing",
        )
    try:
        (
            disk_number,
            central_disk,
            entries_on_disk,
            total_entries,
            central_size,
            central_offset,
            comment_length,
        ) = struct.unpack_from("<HHHHIIH", carrier, position + 4)
    except struct.error:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_eocd_truncated",
        )
    if position + 22 + comment_length != len(carrier):
        state.fail(
            stage="zip_structure",
            check_id="zip_no_trailing_data",
            error_code="zip_trailing_data_or_comment",
        )
    if comment_length != 0:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_archive_comment_forbidden",
        )
    if disk_number != 0 or central_disk != 0 or entries_on_disk != total_entries:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_multidisk_forbidden",
        )
    if total_entries in {0xFFFF} or central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip64_forbidden",
        )
    if total_entries != len(EXPECTED_MEMBERS):
        state.fail(
            stage="zip_structure",
            check_id="zip_exact_member_set_valid",
            error_code="zip_member_count_mismatch",
        )
    if central_offset + central_size != position:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_central_directory_bounds_invalid",
        )
    if central_offset < 0 or central_size < 0 or position > len(carrier):
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_central_directory_bounds_invalid",
        )
    state.pass_check("zip_end_of_central_directory_valid")
    state.pass_check("zip_no_trailing_data")
    return central_offset, central_size, total_entries


def _parse_zip(carrier: bytes, state: VerificationState) -> PackageData:
    central_offset, central_size, total_entries = _find_eocd(carrier, state)
    cursor = central_offset
    central_end = central_offset + central_size
    central_rows: list[dict[str, Any]] = []
    names: list[str] = []
    for _index in range(total_entries):
        if cursor + 46 > central_end or carrier[cursor:cursor + 4] != b"PK\x01\x02":
            state.fail(
                stage="zip_structure",
                check_id="zip_end_of_central_directory_valid",
                error_code="zip_central_entry_invalid",
            )
        try:
            values = struct.unpack_from("<6H3I5H2I", carrier, cursor + 4)
        except struct.error:
            state.fail(
                stage="zip_structure",
                check_id="zip_end_of_central_directory_valid",
                error_code="zip_central_entry_truncated",
            )
        (
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
            comment_length,
            disk_start,
            internal_attr,
            external_attr,
            local_offset,
        ) = values
        row_end = cursor + 46 + name_length + extra_length + comment_length
        if row_end > central_end:
            state.fail(
                stage="zip_structure",
                check_id="zip_end_of_central_directory_valid",
                error_code="zip_central_entry_truncated",
            )
        name_bytes = carrier[cursor + 46:cursor + 46 + name_length]
        extra = carrier[cursor + 46 + name_length:cursor + 46 + name_length + extra_length]
        comment = carrier[cursor + 46 + name_length + extra_length:row_end]
        try:
            name = name_bytes.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_names_valid",
                error_code="zip_member_name_not_ascii",
            )
        names.append(name)
        central_rows.append(
            {
                "name": name,
                "name_bytes": name_bytes,
                "version_made_by": version_made_by,
                "version_needed": version_needed,
                "flags": flags,
                "compression": compression,
                "dos_time": dos_time,
                "dos_date": dos_date,
                "crc32": crc32_value,
                "compressed_size": compressed_size,
                "uncompressed_size": uncompressed_size,
                "extra": extra,
                "comment": comment,
                "disk_start": disk_start,
                "internal_attr": internal_attr,
                "external_attr": external_attr,
                "local_offset": local_offset,
            }
        )
        cursor = row_end
    if cursor != central_end:
        state.fail(
            stage="zip_structure",
            check_id="zip_end_of_central_directory_valid",
            error_code="zip_central_directory_size_mismatch",
        )

    if len(names) != len(set(names)):
        state.fail(
            stage="zip_structure",
            check_id="zip_member_names_valid",
            error_code="zip_duplicate_member_name",
        )
    if not all(_safe_member_name(name) for name in names):
        state.fail(
            stage="zip_structure",
            check_id="zip_member_names_valid",
            error_code="zip_unsafe_member_name",
        )
    state.pass_check("zip_member_names_valid")
    if set(names) != EXPECTED_MEMBERS:
        state.fail(
            stage="zip_structure",
            check_id="zip_exact_member_set_valid",
            error_code="zip_exact_member_set_mismatch",
        )
    state.pass_check("zip_exact_member_set_valid")

    members: dict[str, ZipMember] = {}
    local_ranges: list[tuple[int, int, str]] = []
    total_uncompressed = 0
    for row in central_rows:
        name = row["name"]
        create_system = row["version_made_by"] >> 8
        mode = (row["external_attr"] >> 16) & 0xFFFF
        if create_system != 3 or not stat.S_ISREG(mode):
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_non_regular_member",
                member_path=name,
            )
        if row["disk_start"] != 0 or row["extra"] != b"" or row["comment"] != b"":
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_member_metadata_forbidden",
                member_path=name,
            )
        if row["flags"] & 0x0001:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_encrypted_member_forbidden",
                member_path=name,
            )
        if row["flags"] & 0x0008:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_data_descriptor_forbidden",
                member_path=name,
            )
        if row["flags"] & ~0x0800:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_unsupported_flag_bits",
                member_path=name,
            )
        if row["version_needed"] >= 45:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip64_or_unsupported_version",
                member_path=name,
            )
        state.pass_check("zip_member_types_valid")
        if row["compression"] != 0 or row["compressed_size"] != row["uncompressed_size"]:
            state.fail(
                stage="zip_structure",
                check_id="zip_compression_valid",
                error_code="zip_compression_not_stored",
                member_path=name,
            )
        state.pass_check("zip_compression_valid")
        if row["dos_time"] != 0 or row["dos_date"] != 0x0021:
            state.fail(
                stage="zip_structure",
                check_id="zip_timestamp_policy_valid",
                error_code="zip_timestamp_policy_mismatch",
                member_path=name,
            )
        state.pass_check("zip_timestamp_policy_valid")
        if row["uncompressed_size"] <= 0 or row["uncompressed_size"] > MAX_MEMBER_BYTES:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_member_size_out_of_bounds",
                member_path=name,
            )
        total_uncompressed += row["uncompressed_size"]
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            state.fail(
                stage="zip_structure",
                check_id="zip_member_types_valid",
                error_code="zip_total_uncompressed_size_exceeded",
            )

        local_offset = row["local_offset"]
        if local_offset < 0 or local_offset + 30 > central_offset:
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_header_offset_invalid",
                member_path=name,
            )
        if carrier[local_offset:local_offset + 4] != b"PK\x03\x04":
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_header_signature_invalid",
                member_path=name,
            )
        try:
            (
                local_version,
                local_flags,
                local_compression,
                local_time,
                local_date,
                local_crc,
                local_compressed,
                local_uncompressed,
                local_name_length,
                local_extra_length,
            ) = struct.unpack_from("<5H3I2H", carrier, local_offset + 4)
        except struct.error:
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_header_truncated",
                member_path=name,
            )
        local_name_start = local_offset + 30
        local_name_end = local_name_start + local_name_length
        local_extra_end = local_name_end + local_extra_length
        data_start = local_extra_end
        data_end = data_start + local_compressed
        if data_end > central_offset:
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_member_bounds_invalid",
                member_path=name,
            )
        local_name = carrier[local_name_start:local_name_end]
        local_extra = carrier[local_name_end:local_extra_end]
        if (
            local_version != row["version_needed"]
            or local_flags != row["flags"]
            or local_compression != row["compression"]
            or local_time != row["dos_time"]
            or local_date != row["dos_date"]
            or local_crc != row["crc32"]
            or local_compressed != row["compressed_size"]
            or local_uncompressed != row["uncompressed_size"]
            or local_name != row["name_bytes"]
            or local_extra != b""
        ):
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_central_metadata_mismatch",
                member_path=name,
            )
        payload = carrier[data_start:data_end]
        observed_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if observed_crc != row["crc32"]:
            state.fail(
                stage="zip_structure",
                check_id="zip_crc32_valid",
                error_code="zip_crc32_mismatch",
                member_path=name,
            )
        local_ranges.append((local_offset, data_end, name))
        members[name] = ZipMember(
            path=name,
            crc32=row["crc32"],
            compressed_size=row["compressed_size"],
            uncompressed_size=row["uncompressed_size"],
            local_header_offset=local_offset,
            data_offset=data_start,
            data_end=data_end,
            payload=payload,
            compression_method=row["compression"],
            flags=row["flags"],
            dos_time=row["dos_time"],
            dos_date=row["dos_date"],
            create_system=create_system,
            external_attr=row["external_attr"],
        )

    local_ranges.sort()
    expected_offset = 0
    for start, end, name in local_ranges:
        if start != expected_offset or end <= start:
            state.fail(
                stage="zip_structure",
                check_id="zip_local_central_directory_consistent",
                error_code="zip_local_member_gap_or_overlap",
                member_path=name,
            )
        expected_offset = end
    if expected_offset != central_offset:
        state.fail(
            stage="zip_structure",
            check_id="zip_local_central_directory_consistent",
            error_code="zip_unaccounted_local_bytes",
        )
    state.pass_check("zip_local_central_directory_consistent")
    state.pass_check("zip_crc32_valid")

    return PackageData(
        carrier_bytes=carrier,
        carrier_sha256=sha256_bytes(carrier),
        members=members,
        total_uncompressed_bytes=total_uncompressed,
    )


def _inverse(value: int, modulus: int) -> int:
    try:
        return pow(value, -1, modulus)
    except ValueError as exc:
        raise ValueError("modular_inverse_failed") from exc


def _point_add(left: tuple[int, int] | None, right: tuple[int, int] | None) -> tuple[int, int] | None:
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 + y2) % P256_P == 0:
        return None
    if left == right:
        if y1 == 0:
            return None
        slope = ((3 * x1 * x1 + P256_A) * _inverse(2 * y1, P256_P)) % P256_P
    else:
        slope = ((y2 - y1) * _inverse((x2 - x1) % P256_P, P256_P)) % P256_P
    x3 = (slope * slope - x1 - x2) % P256_P
    y3 = (slope * (x1 - x3) - y1) % P256_P
    return x3, y3


def _scalar_mult(scalar: int, point: tuple[int, int] | None) -> tuple[int, int] | None:
    if point is None or scalar % P256_N == 0:
        return None
    if scalar < 0:
        x, y = point
        return _scalar_mult(-scalar, (x, (-y) % P256_P))
    result: tuple[int, int] | None = None
    addend = point
    value = scalar
    while value:
        if value & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        value >>= 1
    return result


def _decode_public_key(data: bytes) -> tuple[int, int]:
    if len(data) != 65 or data[0] != 0x04:
        raise ValueError("public_key_encoding_invalid")
    x = int.from_bytes(data[1:33], "big")
    y = int.from_bytes(data[33:65], "big")
    if x >= P256_P or y >= P256_P:
        raise ValueError("public_key_coordinate_out_of_range")
    if (y * y - (x * x * x + P256_A * x + P256_B)) % P256_P != 0:
        raise ValueError("public_key_not_on_curve")
    return x, y


def _decode_signature(value: Any) -> bytes:
    text = _require_ascii_string(value, code="signature_base64", maximum=88)
    if len(text) != 88 or re.fullmatch(r"[A-Za-z0-9+/]{86}==", text) is None:
        raise ValueError("signature_base64_shape_invalid")
    try:
        data = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("signature_base64_invalid") from exc
    if len(data) != 64 or base64.b64encode(data).decode("ascii") != text:
        raise ValueError("signature_base64_noncanonical")
    return data


def _decode_p1363(data: bytes) -> tuple[int, int]:
    if len(data) != 64:
        raise ValueError("signature_size_invalid")
    r = int.from_bytes(data[:32], "big")
    s = int.from_bytes(data[32:], "big")
    if not (1 <= r < P256_N):
        raise ValueError("signature_r_out_of_range")
    if not (1 <= s < P256_N):
        raise ValueError("signature_s_out_of_range")
    if s > P256_N // 2:
        raise ValueError("signature_high_s_rejected")
    return r, s


def _verify_p256(public_key: tuple[int, int], digest: bytes, signature: bytes) -> None:
    if len(digest) != 32:
        raise ValueError("signature_digest_size_invalid")
    r, s = _decode_p1363(signature)
    z = int.from_bytes(digest, "big")
    w = _inverse(s, P256_N)
    u1 = (z * w) % P256_N
    u2 = (r * w) % P256_N
    point = _point_add(_scalar_mult(u1, P256_G), _scalar_mult(u2, public_key))
    if point is None or point[0] % P256_N != r:
        raise ValueError("signature_equation_invalid")


def _signature_subject(document: Mapping[str, Any]) -> dict[str, str]:
    return {
        "ledger_id": _require_identifier(document.get("ledger_id"), code="signature_ledger_id"),
        "observer_public_key_fingerprint_sha256": _require_sha256(
            document.get("observer_public_key_fingerprint_sha256"),
            code="signature_observer_fingerprint",
        ),
        "signature_suite": _require_ascii_string(
            document.get("signature_suite"),
            code="signature_suite",
        ),
        "signed_object_sha256": _require_sha256(
            document.get("signed_object_sha256"),
            code="signature_signed_object",
        ),
    }


def _signature_digest(domain: bytes, document: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(domain + b"\x00" + canonical_json_bytes(_signature_subject(document))).digest()


def _record_ref(value: Any, *, code: str) -> tuple[str, str, int]:
    mapping = _require_exact_keys(value, {"record_id", "record_sha256", "sequence_index"}, code=code)
    return (
        _require_identifier(mapping["record_id"], code=f"{code}_record_id"),
        _require_sha256(mapping["record_sha256"], code=f"{code}_record_sha256"),
        _require_i63(mapping["sequence_index"], code=f"{code}_sequence_index"),
    )


def _record_binding(record: Mapping[str, Any]) -> tuple[str, str, int]:
    return (
        _require_identifier(record["record_id"], code="record_id"),
        _require_sha256(record["record_sha256"], code="record_sha256"),
        _require_i63(record["sequence_index"], code="sequence_index"),
    )


def _network_state_from_snapshot(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    payload = record["payload"]
    surfaces = payload["surfaces"]
    network = surfaces[1]
    if network["availability"] != "observed":
        return None
    return _require_mapping(network["state"], code="network_state")


def _flatten_network_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "/network_path/available_interface_types": state["available_interface_types"],
        "/network_path/is_constrained": state["is_constrained"],
        "/network_path/is_expensive": state["is_expensive"],
        "/network_path/status": state["status"],
        "/network_path/supports_dns": state["supports_dns"],
        "/network_path/supports_ipv4": state["supports_ipv4"],
        "/network_path/supports_ipv6": state["supports_ipv6"],
        "/network_path/used_interface_types": state["used_interface_types"],
    }

def _validate_network_state_semantics(state: Mapping[str, Any]) -> None:
    available = state["available_interface_types"]
    used = state["used_interface_types"]
    if available != sorted(available, key=AVAILABLE_INTERFACE_ORDER.__getitem__):
        raise ValueError("available_interface_order_mismatch")
    if used != sorted(used, key=USED_INTERFACE_ORDER.__getitem__):
        raise ValueError("used_interface_order_mismatch")
    if not set(used).issubset(set(available)):
        raise ValueError("used_interface_not_available")


def _validate_contract_bindings(state: VerificationState, members: Mapping[str, ZipMember]) -> None:
    for binding_name, (path, expected_sha, expected_size, check_id) in CONTRACT_BINDINGS.items():
        member = members[path]
        observed_sha = sha256_bytes(member.payload)
        observed_size = len(member.payload)
        status_value = "verified" if observed_sha == expected_sha and observed_size == expected_size else "mismatch"
        state.contract_bindings[binding_name] = {
            "binding_status": status_value,
            "byte_identity": "exact_package_member_bytes",
            "expected_sha256": expected_sha,
            "expected_size_bytes": expected_size,
            "member_path": path,
            "observed_sha256": observed_sha,
            "observed_size_bytes": observed_size,
        }
        if status_value != "verified":
            state.fail(
                stage="contract_binding",
                check_id=check_id,
                error_code="contract_member_identity_mismatch",
                member_path=path,
            )
        state.pass_check(check_id)


def _parse_schema_member(member: ZipMember, *, code: str) -> Mapping[str, Any]:
    try:
        return decode_strict_json(member.payload, source=member.path, ascii_only=False)
    except StrictJsonError as exc:
        raise ValueError(f"{code}_strict_json_invalid") from exc


def _validate_manifest(
    state: VerificationState,
    members: Mapping[str, ZipMember],
) -> Mapping[str, Any]:
    manifest_member = members[MANIFEST_PATH]
    try:
        manifest = decode_strict_json(
            manifest_member.payload,
            source=MANIFEST_PATH,
            ascii_only=True,
        )
    except StrictJsonError:
        state.fail(
            stage="manifest_admission",
            check_id="manifest_strict_json_valid",
            error_code="manifest_strict_json_invalid",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_strict_json_valid")
    try:
        if canonical_json_bytes(manifest) != manifest_member.payload:
            raise CanonicalizationError("noncanonical")
    except CanonicalizationError:
        state.fail(
            stage="manifest_admission",
            check_id="manifest_canonical_json_valid",
            error_code="manifest_canonical_json_invalid",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_canonical_json_valid")

    try:
        schema = _parse_schema_member(members[MANIFEST_SCHEMA_PATH], code="manifest_schema")
        validate_schema(manifest, schema, root=schema)
    except (ValueError, SchemaValidationError):
        state.fail(
            stage="manifest_admission",
            check_id="manifest_schema_valid",
            error_code="manifest_schema_validation_failed",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_schema_valid")

    rows = manifest["payload_members"]
    expected_rows = []
    for path, role, media_type in PAYLOAD_MEMBER_SPECS:
        member = members[path]
        expected_rows.append(
            {
                "byte_identity": "exact_member_bytes",
                "media_type": media_type,
                "path": path,
                "role": role,
                "sha256": sha256_bytes(member.payload),
                "size_bytes": len(member.payload),
            }
        )
    if rows != expected_rows:
        state.fail(
            stage="manifest_admission",
            check_id="manifest_payload_inventory_valid",
            error_code="manifest_payload_inventory_mismatch",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_payload_inventory_valid")

    ledger_member = members[LEDGER_PATH]
    ledger_binding = manifest["ledger_binding"]
    if (
        ledger_binding["ledger_member_path"] != LEDGER_PATH
        or ledger_binding["ledger_schema_member_path"] != LEDGER_SCHEMA_PATH
        or ledger_binding["ledger_schema_sha256"] != LEDGER_SCHEMA_SHA256
        or ledger_binding["ledger_sha256"] != sha256_bytes(ledger_member.payload)
        or ledger_binding["ledger_size_bytes"] != len(ledger_member.payload)
    ):
        state.fail(
            stage="manifest_admission",
            check_id="manifest_ledger_binding_valid",
            error_code="manifest_ledger_binding_mismatch",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_ledger_binding_valid")

    observer_binding = manifest["observer_binding"]
    public_key_member = members[OBSERVER_PUBLIC_KEY_PATH]
    public_key_sha = sha256_bytes(public_key_member.payload)
    if (
        observer_binding["public_key_member_path"] != OBSERVER_PUBLIC_KEY_PATH
        or observer_binding["public_key_size_bytes"] != 65
        or observer_binding["observer_public_key_fingerprint_sha256"] != public_key_sha
    ):
        state.fail(
            stage="manifest_admission",
            check_id="manifest_observer_binding_valid",
            error_code="manifest_observer_binding_mismatch",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_observer_binding_valid")

    signature_contract = manifest["signature_contract"]
    if (
        signature_contract["checkpoint_signature_path"] != CHECKPOINT_SIGNATURE_PATH
        or signature_contract["package_signature_path"] != PACKAGE_SIGNATURE_PATH
        or signature_contract["signature_schema_member_path"] != SIGNATURE_SCHEMA_PATH
        or signature_contract["signature_schema_sha256"] != SIGNATURE_SCHEMA_SHA256
        or signature_contract["signature_suite"] != SIGNATURE_SUITE
    ):
        state.fail(
            stage="manifest_admission",
            check_id="manifest_signature_contract_valid",
            error_code="manifest_signature_contract_mismatch",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("manifest_signature_contract_valid")

    for row in rows:
        path = row["path"]
        if row["sha256"] != sha256_bytes(members[path].payload):
            state.fail(
                stage="payload_identity",
                check_id="payload_member_digests_valid",
                error_code="payload_member_digest_mismatch",
                member_path=path,
            )
    state.pass_check("payload_member_digests_valid")
    for row in rows:
        path = row["path"]
        if row["size_bytes"] != len(members[path].payload):
            state.fail(
                stage="payload_identity",
                check_id="payload_member_sizes_valid",
                error_code="payload_member_size_mismatch",
                member_path=path,
            )
    state.pass_check("payload_member_sizes_valid")
    return manifest


def _validate_observer(state: VerificationState, manifest: Mapping[str, Any], members: Mapping[str, ZipMember]) -> tuple[bytes, tuple[int, int], str]:
    public_key = members[OBSERVER_PUBLIC_KEY_PATH].payload
    if len(public_key) != 65 or public_key[:1] != b"\x04":
        state.fail(
            stage="observer_identity",
            check_id="observer_public_key_encoding_valid",
            error_code="observer_public_key_encoding_invalid",
            member_path=OBSERVER_PUBLIC_KEY_PATH,
        )
    state.pass_check("observer_public_key_encoding_valid")
    try:
        point = _decode_public_key(public_key)
    except ValueError:
        state.fail(
            stage="observer_identity",
            check_id="observer_public_key_curve_membership_valid",
            error_code="observer_public_key_curve_invalid",
            member_path=OBSERVER_PUBLIC_KEY_PATH,
        )
    state.pass_check("observer_public_key_curve_membership_valid")
    fingerprint = sha256_bytes(public_key)
    declared = manifest["observer_binding"]["observer_public_key_fingerprint_sha256"]
    if fingerprint != declared:
        state.fail(
            stage="observer_identity",
            check_id="observer_public_key_fingerprint_valid",
            error_code="observer_public_key_fingerprint_mismatch",
            member_path=OBSERVER_PUBLIC_KEY_PATH,
        )
    if state.expected_observer_fingerprint is not None:
        if SHA256_RE.fullmatch(state.expected_observer_fingerprint) is None or state.expected_observer_fingerprint != fingerprint:
            state.fail(
                stage="observer_identity",
                check_id="observer_public_key_fingerprint_valid",
                error_code="expected_observer_fingerprint_mismatch",
                member_path=OBSERVER_PUBLIC_KEY_PATH,
            )
    state.pass_check("observer_public_key_fingerprint_valid")
    return public_key, point, fingerprint


def _binding_map(records: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, int], Mapping[str, Any]]:
    output: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for record in records:
        binding = _record_binding(record)
        if binding in output:
            raise ValueError("duplicate_record_binding")
        output[binding] = record
    return output


def _resolve_ref(value: Any, records_by_binding: Mapping[tuple[str, str, int], Mapping[str, Any]], *, code: str) -> Mapping[str, Any]:
    binding = _record_ref(value, code=code)
    if binding not in records_by_binding:
        raise ValueError(f"{code}_unresolved")
    return records_by_binding[binding]


def _validate_relation_changes(
    changes: Any,
    *,
    source_state: Mapping[str, Any],
    target_state: Mapping[str, Any],
    observation_status: str,
) -> None:
    if not isinstance(changes, list) or not changes:
        raise ValueError("relation_changes_invalid")
    before = _flatten_network_state(source_state)
    after = _flatten_network_state(target_state)
    expected_paths = [path for path in NETWORK_FIELD_PATHS if before[path] != after[path]]
    observed_paths: list[str] = []
    for row in changes:
        mapping = _require_exact_keys(
            row,
            {"after", "before", "field_path", "observation_status", "surface_id"},
            code="relation_change",
        )
        path = mapping["field_path"]
        if path not in NETWORK_FIELD_PATHS:
            raise ValueError("relation_change_path_invalid")
        observed_paths.append(path)
        if mapping["surface_id"] != "network_path":
            raise ValueError("relation_change_surface_mismatch")
        if mapping["observation_status"] != observation_status:
            raise ValueError("relation_change_observation_status_mismatch")
        if mapping["before"] != before[path] or mapping["after"] != after[path]:
            raise ValueError("relation_change_value_mismatch")
    if observed_paths != expected_paths:
        raise ValueError("relation_change_set_or_order_mismatch")


def _validate_ledger_semantics(
    state: VerificationState,
    ledger: Mapping[str, Any],
    manifest: Mapping[str, Any],
    observer_public_key: bytes,
    observer_fingerprint: str,
    ledger_bytes: bytes,
) -> LedgerResult:
    ledger_id = _require_identifier(ledger["ledger_identity"]["ledger_id"], code="ledger_id")
    record_status = ledger["record_status"]
    if ledger["authority_boundary"] != EXPECTED_AUTHORITY_BOUNDARY:
        state.fail(
            stage="authority_boundary",
            check_id="authority_boundary_preserved",
            error_code="ledger_authority_boundary_mismatch",
            member_path=LEDGER_PATH,
        )
    if ledger["claim_boundary"] != EXPECTED_LEDGER_CLAIM_BOUNDARY:
        state.fail(
            stage="claim_boundary",
            check_id="claim_boundary_preserved",
            error_code="ledger_claim_boundary_mismatch",
            member_path=LEDGER_PATH,
        )
    observer_identity = ledger["observer_identity"]
    try:
        public_key_from_ledger = base64.b64decode(observer_identity["public_key_base64"], validate=True)
    except (binascii.Error, ValueError):
        public_key_from_ledger = b""
    if (
        public_key_from_ledger != observer_public_key
        or base64.b64encode(public_key_from_ledger).decode("ascii") != observer_identity["public_key_base64"]
        or observer_identity["public_key_fingerprint_sha256"] != observer_fingerprint
    ):
        state.fail(
            stage="ledger_admission",
            check_id="ledger_identity_binding_valid",
            error_code="ledger_observer_identity_mismatch",
            member_path=LEDGER_PATH,
        )
    if (
        ledger["canonicalization_profile"]["profile_sha256"] != CANONICALIZATION_PROFILE_SHA256
        or ledger["observation_contract"]["contract_sha256"] != OBSERVATION_CONTRACT_SHA256
        or ledger["signature_schema"]["schema_sha256"] != SIGNATURE_SCHEMA_SHA256
    ):
        state.fail(
            stage="ledger_admission",
            check_id="ledger_identity_binding_valid",
            error_code="ledger_contract_identity_mismatch",
            member_path=LEDGER_PATH,
        )
    if (
        manifest["ledger_binding"]["ledger_id"] != ledger_id
        or manifest["record_status"] != record_status
    ):
        state.fail(
            stage="ledger_admission",
            check_id="ledger_identity_binding_valid",
            error_code="ledger_manifest_identity_mismatch",
            member_path=LEDGER_PATH,
        )
    state.pass_check("ledger_identity_binding_valid")

    records = ledger["records"]
    if not isinstance(records, list) or len(records) < 2 or len(records) > MAX_RECORDS:
        state.fail(
            stage="record_chain",
            check_id="record_sequence_valid",
            error_code="ledger_record_count_invalid",
            member_path=LEDGER_PATH,
        )
    ids: set[str] = set()
    previous_sha: str | None = None
    records_by_sequence: dict[int, Mapping[str, Any]] = {}
    epoch_last_monotonic: dict[str, int] = {}
    session_epoch: dict[str, str] = {}
    counts = {record_type: 0 for record_type in RECORD_TYPES}

    digest_valid = True
    chain_valid = True
    sequence_valid = True
    for index, record in enumerate(records):
        try:
            sequence = _require_i63(record["sequence_index"], code="sequence_index")
            record_id = _require_identifier(record["record_id"], code="record_id")
            record_sha = _require_sha256(record["record_sha256"], code="record_sha256")
        except ValueError:
            state.fail(
                stage="record_chain",
                check_id="record_sequence_valid",
                error_code="record_identity_invalid",
                member_path=LEDGER_PATH,
                record_sequence_index=index,
            )
        if sequence != index or sequence in records_by_sequence or record_id in ids:
            sequence_valid = False
        ids.add(record_id)
        records_by_sequence[sequence] = record
        subject = dict(record)
        del subject["record_sha256"]
        if sha256_bytes(canonical_json_bytes(subject)) != record_sha:
            digest_valid = False
        if record["previous_record_sha256"] != previous_sha:
            chain_valid = False
        previous_sha = record_sha
        if (
            record["ledger_id"] != ledger_id
            or record["record_status"] != record_status
            or record["observer_public_key_fingerprint_sha256"] != observer_fingerprint
            or record["canonicalization_profile_sha256"] != CANONICALIZATION_PROFILE_SHA256
            or record["observation_contract_sha256"] != OBSERVATION_CONTRACT_SHA256
            or record["authority_effect"] != "none"
            or record["claim_boundary"] != EXPECTED_LEDGER_CLAIM_BOUNDARY
        ):
            state.fail(
                stage="ledger_admission",
                check_id="ledger_identity_binding_valid",
                error_code="record_common_binding_mismatch",
                member_path=LEDGER_PATH,
                record_sequence_index=index,
            )
        record_type = record["record_type"]
        counts[record_type] += 1
        session_id = record["session_id"]
        epoch_id = record["clock_epoch_id"]
        monotonic = record["monotonic_time_ns"]
        if session_id is not None:
            if session_id in session_epoch and session_epoch[session_id] != epoch_id:
                state.fail(
                    stage="semantic_relations",
                    check_id="session_relations_valid",
                    error_code="session_clock_epoch_changed",
                    member_path=LEDGER_PATH,
                    record_sequence_index=index,
                )
            session_epoch[session_id] = epoch_id
        if epoch_id is not None:
            if epoch_id in epoch_last_monotonic and monotonic <= epoch_last_monotonic[epoch_id]:
                state.fail(
                    stage="record_chain",
                    check_id="record_sequence_valid",
                    error_code="monotonic_time_not_increasing",
                    member_path=LEDGER_PATH,
                    record_sequence_index=index,
                )
            epoch_last_monotonic[epoch_id] = monotonic
    if not digest_valid:
        state.fail(
            stage="record_chain",
            check_id="record_digests_valid",
            error_code="record_digest_mismatch",
            member_path=LEDGER_PATH,
        )
    state.pass_check("record_digests_valid")
    if not chain_valid:
        state.fail(
            stage="record_chain",
            check_id="record_chain_valid",
            error_code="record_previous_digest_mismatch",
            member_path=LEDGER_PATH,
        )
    state.pass_check("record_chain_valid")
    if not sequence_valid:
        state.fail(
            stage="record_chain",
            check_id="record_sequence_valid",
            error_code="record_sequence_or_identity_invalid",
            member_path=LEDGER_PATH,
        )
    state.pass_check("record_sequence_valid")

    records_by_binding = _binding_map(records)
    session_order: list[str] = []
    session_states: dict[str, dict[str, Any]] = {}
    events: list[Mapping[str, Any]] = []
    snapshots: list[Mapping[str, Any]] = []
    coverages: list[Mapping[str, Any]] = []
    transitions: list[Mapping[str, Any]] = []
    checkpoint_records: list[Mapping[str, Any]] = []

    try:
        for record in records:
            record_type = record["record_type"]
            seq = record["sequence_index"]
            session_id = record["session_id"]
            if record_type == "session_boundary":
                payload = record["payload"]
                kind = payload["boundary_kind"]
                if kind == "opened":
                    if session_id in session_states:
                        raise ValueError("session_reopened_with_same_id")
                    if session_order:
                        prior = session_states[session_order[-1]]
                        if prior["window"] == "open" and not prior["terminal"]:
                            raise ValueError("new_session_opened_before_previous_close")
                        expected_previous = session_order[-1]
                    else:
                        expected_previous = None
                    if payload["previous_session_id"] != expected_previous:
                        raise ValueError("opened_previous_session_mismatch")
                    if record["clock_epoch_id"] in {session_states[s]["epoch"] for s in session_states}:
                        raise ValueError("clock_epoch_reused")
                    session_order.append(session_id)
                    session_states[session_id] = {
                        "epoch": record["clock_epoch_id"],
                        "open_seq": seq,
                        "window": "open",
                        "terminal": False,
                        "close_record": None,
                        "terminal_record": None,
                        "events": [],
                        "snapshots": [],
                        "latest_event": None,
                        "fresh_callback_received": False,
                    }
                else:
                    if session_id not in session_states:
                        raise ValueError("boundary_for_unknown_session")
                    if (
                        not session_order
                        or session_id != session_order[-1]
                    ):
                        raise ValueError("boundary_for_non_current_session")
                    session = session_states[session_id]
                    if payload["previous_session_id"] != session_id:
                        raise ValueError("closing_boundary_previous_session_mismatch")
                    if kind == "observation_window_closed":
                        if session["window"] != "open" or session["close_record"] is not None or session["terminal"]:
                            raise ValueError("duplicate_or_invalid_window_close")
                        session["window"] = "closed"
                        session["close_record"] = record
                    elif kind == "session_terminated":
                        if session["terminal"]:
                            raise ValueError("duplicate_session_termination")
                        session["terminal"] = True
                        session["window"] = "terminal"
                        session["terminal_record"] = record
            elif record_type in {"observation_event", "state_snapshot"}:
                if session_id not in session_states:
                    raise ValueError("session_record_without_open_boundary")
                session = session_states[session_id]
                if session["window"] != "open" or session["terminal"]:
                    raise ValueError("session_record_outside_open_window")
                if record["clock_epoch_id"] != session["epoch"]:
                    raise ValueError("session_record_epoch_mismatch")
                if record_type == "observation_event":
                    _validate_network_state_semantics(
                        _require_mapping(
                            record["payload"]["target_projection"],
                            code="event_target_projection",
                        )
                    )
                    session["events"].append(record)
                    session["latest_event"] = record
                    session["fresh_callback_received"] = True
                    events.append(record)
                else:
                    network = record["payload"]["surfaces"][1]
                    if network["availability"] == "observed":
                        _validate_network_state_semantics(
                            _require_mapping(network["state"], code="snapshot_network_state")
                        )
                    freshness = record["payload"]["network_freshness_status"]
                    source_binding = record["payload"]["source_event_binding"]
                    if freshness == "fresh_callback_bound_in_same_session":
                        if not session["fresh_callback_received"] or source_binding is None:
                            raise ValueError("snapshot_without_fresh_callback")
                        event = _resolve_ref(source_binding, records_by_binding, code="snapshot_source_event")
                        if event["record_type"] != "observation_event" or event["session_id"] != session_id:
                            raise ValueError("snapshot_source_event_invalid")
                        if event["sequence_index"] >= seq:
                            raise ValueError("snapshot_source_event_order_invalid")
                        if event["payload"]["target_projection"] != network["state"]:
                            raise ValueError("snapshot_event_projection_mismatch")
                        later_events = [
                            item for item in session["events"]
                            if event["sequence_index"] < item["sequence_index"] < seq
                        ]
                        if later_events:
                            raise ValueError("snapshot_stale_event_binding")
                    elif freshness == "unavailable_awaiting_callback":
                        if session["fresh_callback_received"] or source_binding is not None or network["availability"] != "unavailable":
                            raise ValueError("unavailable_snapshot_after_callback")
                        expected_reason = (
                            "awaiting_first_path_update"
                            if len(session_order) == 1 and session_order[0] == session_id
                            else "awaiting_fresh_post_reopen_path_update"
                        )
                        if network["reason"] != expected_reason:
                            raise ValueError("unavailable_snapshot_reason_mismatch")
                    session["snapshots"].append(record)
                    snapshots.append(record)
            elif record_type == "coverage_interval":
                coverages.append(record)
            elif record_type == "transition":
                transitions.append(record)
            elif record_type == "checkpoint":
                checkpoint_records.append(record)
    except ValueError:
        state.fail(
            stage="semantic_relations",
            check_id="session_relations_valid",
            error_code="session_relation_invalid",
            member_path=LEDGER_PATH,
        )
    state.pass_check("session_relations_valid")

    coverage_by_binding: dict[tuple[str, str, int], dict[str, Any]] = {}
    try:
        for coverage in coverages:
            payload = coverage["payload"]
            source = _resolve_ref(payload["source_snapshot"], records_by_binding, code="coverage_source")
            target = _resolve_ref(payload["target_snapshot"], records_by_binding, code="coverage_target")
            if source["record_type"] != "state_snapshot" or target["record_type"] != "state_snapshot":
                raise ValueError("coverage_endpoint_not_snapshot")
            if source["sequence_index"] >= target["sequence_index"]:
                raise ValueError("coverage_endpoint_order_invalid")
            if _network_state_from_snapshot(source) is None or _network_state_from_snapshot(target) is None:
                raise ValueError("coverage_endpoint_network_unobserved")
            if payload["coverage_status"] == "continuous":
                if source["session_id"] != target["session_id"] or source["clock_epoch_id"] != target["clock_epoch_id"]:
                    raise ValueError("continuous_coverage_session_mismatch")
                for item in records[source["sequence_index"] + 1:target["sequence_index"]]:
                    if item["record_type"] == "session_boundary" and item["payload"]["boundary_kind"] != "opened":
                        raise ValueError("continuous_coverage_boundary_between_endpoints")
            else:
                start_boundary = _resolve_ref(
                    payload["gap_start_boundary"],
                    records_by_binding,
                    code="gap_start",
                )
                end_boundary = _resolve_ref(
                    payload["gap_end_boundary"],
                    records_by_binding,
                    code="gap_end",
                )
                if start_boundary["record_type"] != "session_boundary":
                    raise ValueError("gap_start_not_session_boundary")
                if (
                    end_boundary["record_type"] != "session_boundary"
                    or end_boundary["payload"]["boundary_kind"] != "opened"
                ):
                    raise ValueError("gap_end_not_session_open")
                if start_boundary["session_id"] != source["session_id"]:
                    raise ValueError("gap_start_session_mismatch")
                if end_boundary["session_id"] != target["session_id"]:
                    raise ValueError("gap_end_session_mismatch")

                source_session = session_states[source["session_id"]]
                target_session = session_states[target["session_id"]]
                start_kind = start_boundary["payload"]["boundary_kind"]

                if start_kind == "observation_window_closed":
                    expected_start = source_session["close_record"]
                elif start_kind == "session_terminated":
                    if source_session["close_record"] is not None:
                        raise ValueError(
                            "terminal_gap_start_after_window_close"
                        )
                    expected_start = source_session["terminal_record"]
                else:
                    raise ValueError("gap_start_boundary_kind_invalid")

                if (
                    expected_start is None
                    or _record_binding(start_boundary)
                    != _record_binding(expected_start)
                ):
                    raise ValueError("gap_start_boundary_mismatch")

                if (
                    end_boundary["sequence_index"]
                    != target_session["open_seq"]
                ):
                    raise ValueError("gap_end_boundary_mismatch")

                if not (
                    source["sequence_index"]
                    < start_boundary["sequence_index"]
                    < end_boundary["sequence_index"]
                    < target["sequence_index"]
                ):
                    raise ValueError(
                        "interrupted_coverage_boundary_order_invalid"
                    )

                if (
                    payload["source_session_id"] != source["session_id"]
                    or payload["target_session_id"]
                    != target["session_id"]
                ):
                    raise ValueError(
                        "interrupted_coverage_session_binding_mismatch"
                    )
                source_session_snapshots = [
                    item for item in snapshots
                    if item["session_id"] == source["session_id"]
                    and item["sequence_index"] < start_boundary["sequence_index"]
                    and _network_state_from_snapshot(item) is not None
                ]
                target_session_snapshots = [
                    item for item in snapshots
                    if item["session_id"] == target["session_id"]
                    and item["sequence_index"] > end_boundary["sequence_index"]
                    and _network_state_from_snapshot(item) is not None
                ]
                if not source_session_snapshots or source is not max(source_session_snapshots, key=lambda item: item["sequence_index"]):
                    raise ValueError("interrupted_coverage_source_not_last_bound")
                if not target_session_snapshots or target is not min(target_session_snapshots, key=lambda item: item["sequence_index"]):
                    raise ValueError("interrupted_coverage_target_not_first_fresh")
                if session_order.index(target["session_id"]) != session_order.index(source["session_id"]) + 1:
                    raise ValueError("interrupted_coverage_nonadjacent_sessions")
            coverage_by_binding[_record_binding(coverage)] = {
                "record": coverage,
                "source": source,
                "target": target,
                "status": payload["coverage_status"],
            }
    except (ValueError, KeyError):
        state.fail(
            stage="semantic_relations",
            check_id="coverage_relations_valid",
            error_code="coverage_relation_invalid",
            member_path=LEDGER_PATH,
        )
    state.pass_check("coverage_relations_valid")

    consumed_events: set[tuple[str, str, int]] = set()
    consumed_endpoint_relations: set[
        tuple[
            tuple[str, str, int],
            str,
            tuple[str, str, int],
            tuple[str, str, int],
        ]
    ] = set()
    event_endpoint_valid = True
    transition_valid = True
    event_bound_count = 0
    endpoint_count = 0
    unavailable_source_count = 0
    try:
        for transition in transitions:
            payload = transition["payload"]
            source = _resolve_ref(payload["source_snapshot"], records_by_binding, code="transition_source")
            target = _resolve_ref(payload["target_snapshot"], records_by_binding, code="transition_target")
            coverage_record = _resolve_ref(payload["coverage_binding"], records_by_binding, code="transition_coverage")
            coverage = coverage_by_binding.get(_record_binding(coverage_record))
            if coverage is None or coverage["source"] is not source or coverage["target"] is not target:
                raise ValueError("transition_coverage_binding_mismatch")
            source_state = _network_state_from_snapshot(source)
            target_state = _network_state_from_snapshot(target)
            if source_state is None or target_state is None:
                raise ValueError("transition_endpoint_state_unavailable")
            if payload["initiating_source_status"] == "unavailable_from_platform":
                unavailable_source_count += 1
            if payload["transition_class"] == "event_bound":
                event_bound_count += 1
                if coverage["status"] != "continuous":
                    raise ValueError("event_transition_not_continuous")
                event = _resolve_ref(payload["event_binding"], records_by_binding, code="transition_event")
                binding = _record_binding(event)
                if binding in consumed_events:
                    raise ValueError("event_consumed_more_than_once")
                consumed_events.add(binding)
                if event["record_type"] != "observation_event":
                    raise ValueError("transition_event_not_observation_event")
                if not (source["sequence_index"] < event["sequence_index"] < target["sequence_index"]):
                    raise ValueError("event_transition_order_invalid")
                if source["session_id"] != event["session_id"] or target["session_id"] != event["session_id"]:
                    raise ValueError("event_transition_session_mismatch")
                if event["payload"]["target_projection"] != target_state:
                    raise ValueError("event_transition_target_projection_mismatch")
                if _record_ref(target["payload"]["source_event_binding"], code="target_source_event") != binding:
                    raise ValueError("target_snapshot_not_bound_to_event")
                eligible_before = [
                    item for item in snapshots
                    if item["session_id"] == event["session_id"]
                    and item["sequence_index"] < event["sequence_index"]
                    and _network_state_from_snapshot(item) is not None
                ]
                eligible_after = [
                    item for item in snapshots
                    if item["session_id"] == event["session_id"]
                    and item["sequence_index"] > event["sequence_index"]
                    and _network_state_from_snapshot(item) is not None
                ]
                if not eligible_before or source is not max(eligible_before, key=lambda item: item["sequence_index"]):
                    raise ValueError("event_transition_source_not_immediate")
                if not eligible_after or target is not min(eligible_after, key=lambda item: item["sequence_index"]):
                    raise ValueError("event_transition_target_not_immediate")
                intervening_events = [
                    item for item in events
                    if source["sequence_index"] < item["sequence_index"] < target["sequence_index"]
                ]
                if intervening_events != [event]:
                    raise ValueError("event_transition_intervening_event")
                _validate_relation_changes(
                    payload["relation_changes"],
                    source_state=source_state,
                    target_state=target_state,
                    observation_status="event_observed",
                )
            else:
                if coverage["status"] != "interrupted" or payload["event_binding"] is not None:
                    raise ValueError("endpoint_transition_binding_invalid")
                _validate_relation_changes(
                    payload["relation_changes"],
                    source_state=source_state,
                    target_state=target_state,
                    observation_status="endpoint_difference_observed",
                )
                relation_key = (
                    _record_binding(coverage_record),
                    payload["transition_class"],
                    _record_binding(source),
                    _record_binding(target),
                )
                consumed_endpoint_relations.add(relation_key)
                endpoint_count += 1
    except (ValueError, KeyError):
        event_endpoint_valid = False
        transition_valid = False
    if endpoint_count != len(consumed_endpoint_relations):
        transition_valid = False
    if not event_endpoint_valid:
        state.fail(
            stage="semantic_relations",
            check_id="event_endpoint_bindings_valid",
            error_code="event_endpoint_binding_invalid",
            member_path=LEDGER_PATH,
        )
    state.pass_check("event_endpoint_bindings_valid")
    if not transition_valid:
        state.fail(
            stage="semantic_relations",
            check_id="transition_relations_valid",
            error_code="transition_relation_invalid",
            member_path=LEDGER_PATH,
        )
    state.pass_check("transition_relations_valid")

    if len(checkpoint_records) != 1 or records[-1] is not checkpoint_records[0]:
        state.fail(
            stage="semantic_relations",
            check_id="checkpoint_closure_valid",
            error_code="checkpoint_terminal_cardinality_invalid",
            member_path=LEDGER_PATH,
        )
    checkpoint = checkpoint_records[0]
    checkpoint_payload = checkpoint["payload"]
    first = records[0]
    terminal_before_checkpoint = records[-2]
    if ledger["ledger_identity"]["created_unix_ns"] != first["recorded_wall_time_unix_ns"]:
        state.fail(
            stage="ledger_admission",
            check_id="ledger_identity_binding_valid",
            error_code="ledger_created_time_mismatch",
            member_path=LEDGER_PATH,
            record_sequence_index=first["sequence_index"],
        )
    coverage_continuous = sum(1 for item in coverages if item["payload"]["coverage_status"] == "continuous")
    coverage_interrupted = sum(1 for item in coverages if item["payload"]["coverage_status"] == "interrupted")
    expected_non_checkpoint_counts = {
        "coverage_interval": counts["coverage_interval"],
        "observation_event": counts["observation_event"],
        "session_boundary": counts["session_boundary"],
        "state_snapshot": counts["state_snapshot"],
        "transition": counts["transition"],
    }
    try:
        if _record_ref(checkpoint_payload["first_record"], code="checkpoint_first") != _record_binding(first):
            raise ValueError("checkpoint_first_record_mismatch")
        if _record_ref(checkpoint_payload["terminal_record"], code="checkpoint_terminal") != _record_binding(terminal_before_checkpoint):
            raise ValueError("checkpoint_terminal_record_mismatch")
        if checkpoint_payload["closed_record_count"] != len(records) - 1:
            raise ValueError("checkpoint_closed_record_count_mismatch")
        if checkpoint_payload["terminal_sequence_index"] != len(records) - 2:
            raise ValueError("checkpoint_terminal_sequence_mismatch")
        if checkpoint_payload["record_type_counts"] != expected_non_checkpoint_counts:
            raise ValueError("checkpoint_record_type_counts_mismatch")
        if checkpoint_payload["session_count"] != len(session_order):
            raise ValueError("checkpoint_session_count_mismatch")
        if checkpoint_payload["clock_epoch_count"] != len({session_states[item]["epoch"] for item in session_order}):
            raise ValueError("checkpoint_epoch_count_mismatch")
        if checkpoint_payload["coverage_summary"] != {
            "continuous_intervals": coverage_continuous,
            "interrupted_intervals": coverage_interrupted,
        }:
            raise ValueError("checkpoint_coverage_summary_mismatch")
        if checkpoint_payload["transition_summary"] != {
            "endpoint_difference_only": endpoint_count,
            "event_bound": event_bound_count,
        }:
            raise ValueError("checkpoint_transition_summary_mismatch")
        if checkpoint_payload["created_unix_ns"] != checkpoint["recorded_wall_time_unix_ns"]:
            raise ValueError("checkpoint_created_time_mismatch")
        if checkpoint_payload["ledger_id"] != ledger_id or checkpoint_payload["observer_public_key_fingerprint_sha256"] != observer_fingerprint:
            raise ValueError("checkpoint_identity_mismatch")
    except (ValueError, KeyError):
        state.fail(
            stage="semantic_relations",
            check_id="checkpoint_closure_valid",
            error_code="checkpoint_closure_mismatch",
            member_path=LEDGER_PATH,
            record_sequence_index=checkpoint["sequence_index"],
        )

    summary = ledger["ledger_summary"]
    expected_summary = {
        "checkpoint_record_sha256": checkpoint["record_sha256"],
        "clock_epoch_count": len({session_states[item]["epoch"] for item in session_order}),
        "coverage_interval_count": counts["coverage_interval"],
        "observation_event_count": counts["observation_event"],
        "record_count": len(records),
        "session_boundary_count": counts["session_boundary"],
        "session_count": len(session_order),
        "snapshot_count": counts["state_snapshot"],
        "terminal_record_sha256": checkpoint["record_sha256"],
        "transition_count": counts["transition"],
    }
    if summary != expected_summary:
        state.fail(
            stage="semantic_relations",
            check_id="checkpoint_closure_valid",
            error_code="ledger_summary_mismatch",
            member_path=LEDGER_PATH,
        )
    manifest_binding = manifest["ledger_binding"]
    if (
        manifest_binding["checkpoint_record_sha256"] != checkpoint["record_sha256"]
        or manifest_binding["terminal_record_sha256"] != checkpoint["record_sha256"]
        or manifest_binding["record_count"] != len(records)
        or manifest["created_unix_ns"] != checkpoint_payload["created_unix_ns"]
    ):
        state.fail(
            stage="semantic_relations",
            check_id="checkpoint_closure_valid",
            error_code="manifest_checkpoint_binding_mismatch",
            member_path=MANIFEST_PATH,
        )
    state.pass_check("checkpoint_closure_valid")

    return LedgerResult(
        ledger_id=ledger_id,
        record_status=record_status,
        ledger_sha256=sha256_bytes(ledger_bytes),
        ledger_size_bytes=len(ledger_bytes),
        record_count=len(records),
        record_type_counts=counts,
        first_record_sha256=first["record_sha256"],
        terminal_record_sha256=checkpoint["record_sha256"],
        checkpoint_record_sha256=checkpoint["record_sha256"],
        checkpoint_record=checkpoint,
        continuous_coverage_interval_count=coverage_continuous,
        interrupted_coverage_interval_count=coverage_interrupted,
        event_bound_transition_count=event_bound_count,
        endpoint_difference_only_transition_count=endpoint_count,
        unavailable_initiating_source_transition_count=unavailable_source_count,
    )


def _validate_signature_document(
    state: VerificationState,
    *,
    member: ZipMember,
    schema: Mapping[str, Any],
    expected_role: str,
    expected_domain: str,
    expected_signed_object_type: str,
    expected_object_sha256: str,
    expected_ledger_id: str,
    expected_observer_fingerprint: str,
    document_check: str,
    subject_check: str,
    signature_check: str,
    stage: str,
    public_key: tuple[int, int],
) -> tuple[Mapping[str, Any], str, str]:
    try:
        document = decode_strict_json(member.payload, source=member.path, ascii_only=True)
        if canonical_json_bytes(document) != member.payload:
            raise CanonicalizationError("noncanonical")
        validate_schema(document, schema, root=schema)
        signature_bytes = _decode_signature(document["signature_base64"])
    except (StrictJsonError, CanonicalizationError, SchemaValidationError, ValueError, KeyError):
        state.fail(
            stage=stage,
            check_id=document_check,
            error_code="signature_document_invalid",
            member_path=member.path,
        )
    state.pass_check(document_check)
    if (
        document["signature_role"] != expected_role
        or document["signature_domain"] != expected_domain
        or document["signed_object_type"] != expected_signed_object_type
        or document["signed_object_sha256"] != expected_object_sha256
        or document["ledger_id"] != expected_ledger_id
        or document["observer_public_key_fingerprint_sha256"] != expected_observer_fingerprint
        or document["signature_suite"] != SIGNATURE_SUITE
    ):
        state.fail(
            stage=stage,
            check_id=subject_check,
            error_code="signature_subject_binding_mismatch",
            member_path=member.path,
        )
    domain = expected_domain.encode("ascii")
    digest = _signature_digest(domain, document)
    state.pass_check(subject_check)
    try:
        _verify_p256(public_key, digest, signature_bytes)
    except ValueError:
        state.fail(
            stage=stage,
            check_id=signature_check,
            error_code="signature_verification_failed",
            member_path=member.path,
        )
    state.pass_check(signature_check)
    return document, sha256_bytes(member.payload), digest.hex()


def _default_contract_bindings() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, (path, expected_sha, expected_size, _check_id) in CONTRACT_BINDINGS.items():
        output[name] = {
            "binding_status": "not_reached",
            "byte_identity": "exact_package_member_bytes",
            "expected_sha256": expected_sha,
            "expected_size_bytes": expected_size,
            "member_path": path,
            "observed_sha256": None,
            "observed_size_bytes": None,
        }
    return output


def _member_results(state: VerificationState) -> list[dict[str, Any]]:
    if state.package is None:
        return []
    output: list[dict[str, Any]] = []
    for path, role, media_type in EXPECTED_MEMBER_SPECS:
        member = state.package.members.get(path)
        if member is None:
            output.append(
                {
                    "compressed_size_bytes": None,
                    "compression_method": "not_reached",
                    "crc32_hex": None,
                    "media_type": media_type,
                    "member_type": "missing",
                    "path": path,
                    "role": role,
                    "sha256": None,
                    "size_bytes": None,
                    "verification_status": "missing",
                }
            )
            continue
        output.append(
            {
                "compressed_size_bytes": member.compressed_size,
                "compression_method": "stored",
                "crc32_hex": f"{member.crc32:08x}",
                "media_type": media_type,
                "member_type": "regular_file",
                "path": path,
                "role": role,
                "sha256": sha256_bytes(member.payload),
                "size_bytes": len(member.payload),
                "verification_status": "verified",
            }
        )
    return output



def _component_status(state: VerificationState, check_ids: Sequence[str]) -> str:
    statuses = [state.checks[check_id] for check_id in check_ids]
    if all(status == "not_reached" for status in statuses):
        return "not_reached"
    if all(status == "passed" for status in statuses):
        return "verified"
    return "rejected"

def _signature_report(
    *,
    member_path: str,
    domain: str,
    role: str,
    object_type: str,
    document: Mapping[str, Any] | None,
    document_sha: str | None,
    document_size: int | None,
    reconstructed_object_sha: str | None,
    signature_input_sha: str | None,
    verified: bool,
) -> dict[str, Any]:
    return {
        "declared_signed_object_sha256": (
            document.get("signed_object_sha256")
            if document is not None and isinstance(document.get("signed_object_sha256"), str)
            else None
        ),
        "document_sha256": document_sha,
        "document_size_bytes": document_size,
        "member_path": member_path,
        "reconstructed_signature_input_sha256": signature_input_sha,
        "reconstructed_signed_object_sha256": reconstructed_object_sha,
        "signature_domain": domain,
        "signature_role": role,
        "signature_status": "verified" if verified else ("rejected" if document is not None else "not_reached"),
        "signature_subject_canonicalization": "pulsemech_device_canonical_json_v0",
        "signature_subject_framing": "ascii_domain_separator_then_0x00_then_canonical_subject_json",
        "signature_suite": SIGNATURE_SUITE,
        "signed_object_type": object_type,
    }


def _sorted_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(item) for item in errors],
        key=lambda item: (
            STAGE_INDEX[item["stage"]],
            CHECK_INDEX[item["check_id"]],
            item["error_code"],
            item["member_path"] or "",
            -1 if item["record_sequence_index"] is None else item["record_sequence_index"],
        ),
    )


def build_report(state: VerificationState) -> dict[str, Any]:
    errors = _sorted_errors(state.errors)
    failed_check_ids = [check_id for check_id in CHECK_IDS if state.checks[check_id] == "failed"]
    success = not errors and all(state.checks[check_id] == "passed" for check_id in CHECK_IDS)
    ledger_result = state.ledger_result
    unavailable_present = bool(
        ledger_result is not None
        and (
            ledger_result.interrupted_coverage_interval_count > 0
            or ledger_result.unavailable_initiating_source_transition_count > 0
        )
    )
    result = (
        "verified_with_declared_unavailability"
        if success and unavailable_present
        else "verified"
        if success
        else "rejected"
    )
    carrier_name = state.carrier_path.name
    if CARRIER_NAME_RE.fullmatch(carrier_name) is None or len(carrier_name) < 13:
        carrier_name = "rejected-input.pulseledger"

    package = state.package
    manifest = state.manifest
    public_key_sha = sha256_bytes(state.observer_public_key) if state.observer_public_key is not None else None
    contract_bindings = state.contract_bindings or _default_contract_bindings()
    carrier_status = _component_status(state, CHECK_IDS[:12])
    manifest_status = _component_status(state, CHECK_IDS[12:21])
    observer_status = _component_status(state, CHECK_IDS[26:29])
    ledger_status = _component_status(state, CHECK_IDS[29:41])
    report = {
        "authority_boundary": {
            "authority_effect": "none",
            "changes_release_authority": False,
            "creates_device_control_authority": False,
            "creates_gate_result": False,
            "creates_release_decision": False,
            "verifier_report_is_release_authority": False,
        },
        "carrier_verification": {
            "carrier_sha256": state.carrier_sha256,
            "carrier_size_bytes": state.carrier_size_bytes,
            "manifest_member_path": MANIFEST_PATH,
            "member_results": _member_results(state),
            "observed_package_member_count": len(package.members) if package is not None else None,
            "observed_payload_member_count": (
                len([path for path in package.members if path not in {MANIFEST_PATH, PACKAGE_SIGNATURE_PATH}])
                if package is not None
                else None
            ),
            "package_signature_member_path": PACKAGE_SIGNATURE_PATH,
            "status": carrier_status,
            "total_uncompressed_bytes": package.total_uncompressed_bytes if package is not None else None,
        },
        "checks": dict(state.checks),
        "claim_boundary": dict(EXPECTED_PACKAGE_CLAIM_BOUNDARY),
        "contract_bindings": contract_bindings,
        "diagnostic_contract": {
            "error_order": "stage_then_check_id_then_error_code_then_member_path_then_record_sequence_index",
            "failed_check_id_order": "verification_check_contract_order",
            "free_text_diagnostics": "forbidden",
        },
        "document_type": REPORT_DOCUMENT_TYPE,
        "errors": errors,
        "failed_check_ids": failed_check_ids,
        "failure_stage": None if success else state.failure_stage,
        "ledger_verification": {
            "checkpoint_record_sha256": ledger_result.checkpoint_record_sha256 if ledger_result else None,
            "first_record_sha256": ledger_result.first_record_sha256 if ledger_result else None,
            "ledger_id": ledger_result.ledger_id if ledger_result else None,
            "ledger_sha256": ledger_result.ledger_sha256 if ledger_result else None,
            "ledger_size_bytes": ledger_result.ledger_size_bytes if ledger_result else None,
            "member_path": LEDGER_PATH,
            "record_count": ledger_result.record_count if ledger_result else None,
            "record_type_counts": {
                record_type: ledger_result.record_type_counts[record_type] if ledger_result else None
                for record_type in RECORD_TYPES
            },
            "schema_member_path": LEDGER_SCHEMA_PATH,
            "schema_sha256": LEDGER_SCHEMA_SHA256,
            "schema_size_bytes": LEDGER_SCHEMA_BYTES,
            "status": ledger_status,
            "terminal_record_sha256": ledger_result.terminal_record_sha256 if ledger_result else None,
        },
        "manifest_verification": {
            "declared_package_member_count": manifest.get("package_member_count") if manifest else None,
            "declared_payload_member_count": manifest.get("payload_member_count") if manifest else None,
            "manifest_sha256": state.manifest_sha256,
            "manifest_size_bytes": state.manifest_size_bytes,
            "member_path": MANIFEST_PATH,
            "schema_member_path": MANIFEST_SCHEMA_PATH,
            "schema_sha256": MANIFEST_SCHEMA_SHA256,
            "schema_size_bytes": MANIFEST_SCHEMA_BYTES,
            "status": manifest_status,
        },
        "observer_verification": {
            "curve": "secp256r1",
            "declared_fingerprint_sha256": (
                manifest["observer_binding"]["observer_public_key_fingerprint_sha256"]
                if manifest
                else None
            ),
            "fingerprint_algorithm": "SHA-256",
            "fingerprint_subject": "exact_65_byte_x963_uncompressed_public_key",
            "member_path": OBSERVER_PUBLIC_KEY_PATH,
            "public_key_encoding": PUBLIC_KEY_ENCODING,
            "public_key_sha256": public_key_sha,
            "public_key_size_bytes": len(state.observer_public_key) if state.observer_public_key is not None else None,
            "reconstructed_fingerprint_sha256": state.observer_fingerprint,
            "signature_suite": SIGNATURE_SUITE,
            "status": observer_status,
        },
        "ok": success,
        "record_status": ledger_result.record_status if ledger_result else "unknown",
        "report_contract": {
            "canonicalization": "pulsemech_device_canonical_json_v0",
            "generated_time_field": "forbidden",
            "stored_bytes": "must_equal_canonical_reserialization",
            "trailing_newline": False,
        },
        "reproduction_context": {
            "external_validation_claim": "none",
            "producer_environment_available_to_verifier": state.producer_environment_available,
            "reproduction_class": state.reproduction_class,
            "same_project_implementation": True,
            "verifier_implementation_relation": "separate_from_producer_code",
        },
        "result": result,
        "schema_version": REPORT_SCHEMA_VERSION,
        "semantic_summary": {
            "causal_necessity_established_count": 0,
            "causal_sufficiency_established_count": 0,
            "continuous_coverage_interval_count": ledger_result.continuous_coverage_interval_count if ledger_result else None,
            "declared_unavailability_present": unavailable_present,
            "device_security_claim_count": 0,
            "endpoint_difference_only_transition_count": ledger_result.endpoint_difference_only_transition_count if ledger_result else None,
            "event_bound_transition_count": ledger_result.event_bound_transition_count if ledger_result else None,
            "interrupted_coverage_interval_count": ledger_result.interrupted_coverage_interval_count if ledger_result else None,
            "physical_measurement_claim_count": 0,
            "retention_completeness_status": "package_local_only" if success else "unresolved",
            "unavailable_initiating_source_transition_count": ledger_result.unavailable_initiating_source_transition_count if ledger_result else None,
        },
        "signature_verification": {
            "checkpoint": _signature_report(
                member_path=CHECKPOINT_SIGNATURE_PATH,
                domain="PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0",
                role="ledger_checkpoint",
                object_type="checkpoint_record_sha256",
                document=state.checkpoint_signature_document,
                document_sha=state.checkpoint_signature_document_sha256,
                document_size=state.checkpoint_signature_document_size,
                reconstructed_object_sha=ledger_result.checkpoint_record_sha256 if ledger_result else None,
                signature_input_sha=state.checkpoint_signature_input_sha256,
                verified=state.checks["checkpoint_signature_valid"] == "passed",
            ),
            "package": _signature_report(
                member_path=PACKAGE_SIGNATURE_PATH,
                domain="PULSEMECH-DEVICE-LEDGER-PACKAGE-V0",
                role="ledger_package",
                object_type="ledger_manifest_sha256",
                document=state.package_signature_document,
                document_sha=state.package_signature_document_sha256,
                document_size=state.package_signature_document_size,
                reconstructed_object_sha=state.manifest_sha256,
                signature_input_sha=state.package_signature_input_sha256,
                verified=state.checks["package_signature_valid"] == "passed",
            ),
            "signature_schema_member_path": SIGNATURE_SCHEMA_PATH,
            "signature_schema_sha256": SIGNATURE_SCHEMA_SHA256,
            "signature_schema_size_bytes": SIGNATURE_SCHEMA_BYTES,
        },
        "subject": {
            "carrier_file_name": carrier_name,
            "carrier_sha256": state.carrier_sha256,
            "carrier_size_bytes": state.carrier_size_bytes,
            "media_type": "application/zip",
            "package_format": PACKAGE_FORMAT,
        },
        "tool": {
            "dependency_profile": "python_standard_library_only",
            "id": TOOL_NAME,
            "implementation_language": "python3",
            "producer_code_imported": False,
            "source_path": TOOL_SOURCE_PATH,
            "source_revision": state.source_revision,
            "source_sha256": state.verifier_source_sha256,
            "version": TOOL_VERSION,
        },
        "verification_identity": {
            "carrier_sha256": state.carrier_sha256,
            "identity_derivation": "carrier_sha256_then_verifier_source_sha256",
            "verification_contract": "pulsemech_device_ledger_verification_v0",
            "verification_id": (
                f"device-ledger-verification:{state.carrier_sha256}:{state.verifier_source_sha256}:v0"
                if state.carrier_sha256 is not None
                else None
            ),
            "verifier_source_sha256": state.verifier_source_sha256,
        },
        "verification_scope": {
            "carrier_bytes_in_scope": True,
            "checkpoint_signature_in_scope": True,
            "external_device_state_in_scope": False,
            "external_validation_in_scope": False,
            "ledger_schema_in_scope": True,
            "ledger_semantics_in_scope": True,
            "manifest_semantics_in_scope": True,
            "package_signature_in_scope": True,
            "payload_member_bytes_in_scope": True,
            "physical_measurement_validity_in_scope": False,
            "zip_structure_in_scope": True,
        },
    }
    return report


def verify_package(
    path: Path,
    *,
    expected_observer_fingerprint: str | None = None,
    reproduction_class: str = "same_environment",
    producer_environment_available: bool = True,
    source_revision: str | None = None,
) -> dict[str, Any]:
    try:
        source_bytes = Path(__file__).read_bytes()
    except OSError:
        source_bytes = b"unavailable-verifier-source"
    source_sha = sha256_bytes(source_bytes)
    state = VerificationState(
        carrier_path=path,
        reproduction_class=reproduction_class,
        producer_environment_available=producer_environment_available,
        source_revision=source_revision,
        expected_observer_fingerprint=expected_observer_fingerprint,
        verifier_source_sha256=source_sha,
        contract_bindings=_default_contract_bindings(),
    )
    try:
        carrier = _read_stable_carrier(path, state)
        state.carrier_sha256 = sha256_bytes(carrier)
        state.carrier_size_bytes = len(carrier)
        package = _parse_zip(carrier, state)
        state.package = package
        _validate_contract_bindings(state, package.members)
        manifest = _validate_manifest(state, package.members)
        state.manifest = manifest
        state.manifest_sha256 = sha256_bytes(package.members[MANIFEST_PATH].payload)
        state.manifest_size_bytes = len(package.members[MANIFEST_PATH].payload)
        public_key_bytes, public_key_point, observer_fingerprint = _validate_observer(
            state,
            manifest,
            package.members,
        )
        state.observer_public_key = public_key_bytes
        state.observer_point = public_key_point
        state.observer_fingerprint = observer_fingerprint

        ledger_member = package.members[LEDGER_PATH]
        try:
            ledger = decode_strict_json(ledger_member.payload, source=LEDGER_PATH, ascii_only=True)
        except StrictJsonError:
            state.fail(
                stage="ledger_admission",
                check_id="ledger_strict_json_valid",
                error_code="ledger_strict_json_invalid",
                member_path=LEDGER_PATH,
            )
        state.pass_check("ledger_strict_json_valid")
        try:
            if canonical_json_bytes(ledger) != ledger_member.payload:
                raise CanonicalizationError("noncanonical")
        except CanonicalizationError:
            state.fail(
                stage="ledger_admission",
                check_id="ledger_canonical_json_valid",
                error_code="ledger_canonical_json_invalid",
                member_path=LEDGER_PATH,
            )
        state.pass_check("ledger_canonical_json_valid")
        try:
            ledger_schema = _parse_schema_member(package.members[LEDGER_SCHEMA_PATH], code="ledger_schema")
            validate_schema(ledger, ledger_schema, root=ledger_schema)
        except (ValueError, SchemaValidationError):
            state.fail(
                stage="ledger_admission",
                check_id="ledger_schema_valid",
                error_code="ledger_schema_validation_failed",
                member_path=LEDGER_PATH,
            )
        state.pass_check("ledger_schema_valid")
        state.ledger = ledger
        ledger_result = _validate_ledger_semantics(
            state,
            ledger,
            manifest,
            public_key_bytes,
            observer_fingerprint,
            ledger_member.payload,
        )
        state.ledger_result = ledger_result

        signature_schema = _parse_schema_member(package.members[SIGNATURE_SCHEMA_PATH], code="signature_schema")
        checkpoint_member = package.members[CHECKPOINT_SIGNATURE_PATH]
        checkpoint_doc, checkpoint_doc_sha, checkpoint_input_sha = _validate_signature_document(
            state,
            member=checkpoint_member,
            schema=signature_schema,
            expected_role="ledger_checkpoint",
            expected_domain="PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0",
            expected_signed_object_type="checkpoint_record_sha256",
            expected_object_sha256=ledger_result.checkpoint_record_sha256,
            expected_ledger_id=ledger_result.ledger_id,
            expected_observer_fingerprint=observer_fingerprint,
            document_check="checkpoint_signature_document_valid",
            subject_check="checkpoint_signature_subject_valid",
            signature_check="checkpoint_signature_valid",
            stage="checkpoint_signature",
            public_key=public_key_point,
        )
        state.checkpoint_signature_document = checkpoint_doc
        state.checkpoint_signature_document_sha256 = checkpoint_doc_sha
        state.checkpoint_signature_document_size = len(checkpoint_member.payload)
        state.checkpoint_signature_input_sha256 = checkpoint_input_sha

        package_signature_member = package.members[PACKAGE_SIGNATURE_PATH]
        package_doc, package_doc_sha, package_input_sha = _validate_signature_document(
            state,
            member=package_signature_member,
            schema=signature_schema,
            expected_role="ledger_package",
            expected_domain="PULSEMECH-DEVICE-LEDGER-PACKAGE-V0",
            expected_signed_object_type="ledger_manifest_sha256",
            expected_object_sha256=state.manifest_sha256,
            expected_ledger_id=ledger_result.ledger_id,
            expected_observer_fingerprint=observer_fingerprint,
            document_check="package_signature_document_valid",
            subject_check="package_signature_subject_valid",
            signature_check="package_signature_valid",
            stage="package_signature",
            public_key=public_key_point,
        )
        state.package_signature_document = package_doc
        state.package_signature_document_sha256 = package_doc_sha
        state.package_signature_document_size = len(package_signature_member.payload)
        state.package_signature_input_sha256 = package_input_sha

        if manifest["claim_boundary"] != EXPECTED_PACKAGE_CLAIM_BOUNDARY:
            state.fail(
                stage="claim_boundary",
                check_id="claim_boundary_preserved",
                error_code="manifest_claim_boundary_mismatch",
                member_path=MANIFEST_PATH,
            )
        state.pass_check("claim_boundary_preserved")
        if manifest["authority_boundary"] != EXPECTED_AUTHORITY_BOUNDARY:
            state.fail(
                stage="authority_boundary",
                check_id="authority_boundary_preserved",
                error_code="manifest_authority_boundary_mismatch",
                member_path=MANIFEST_PATH,
            )
        state.pass_check("authority_boundary_preserved")
    except VerificationError:
        pass
    except Exception:
        if not state.errors:
            try:
                state.fail(
                    stage="input_boundary",
                    check_id="input_regular_file",
                    error_code="internal_verifier_error",
                )
            except VerificationError:
                pass
    return build_report(state)


def _write_output(path: Path, payload: bytes, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise OSError("output_exists")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        metadata = None
    if metadata is not None and (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode)):
        raise OSError("unsafe_output_target")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify one bounded PULSEmech iPhone Device Transition Ledger "
            ".pulseledger carrier without importing producer code."
        )
    )
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--expected-observer-fingerprint")
    parser.add_argument(
        "--reproduction-class",
        choices=("same_environment", "same_operator_clean_room", "external_operator"),
        default="same_environment",
    )
    parser.add_argument(
        "--producer-environment-available",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--source-revision")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.source_revision is not None and SHA40_RE.fullmatch(args.source_revision) is None:
        raise SystemExit("--source-revision must be a lowercase 40-hex Git commit")
    report = verify_package(
        args.ledger,
        expected_observer_fingerprint=args.expected_observer_fingerprint,
        reproduction_class=args.reproduction_class,
        producer_environment_available=args.producer_environment_available,
        source_revision=args.source_revision,
    )
    rendered = canonical_json_bytes(report)
    if args.output is not None:
        try:
            output_resolved = args.output.resolve(strict=False)
            protected_outputs = {
                args.ledger.resolve(strict=False),
                Path(__file__).resolve(strict=False),
            }
            if output_resolved in protected_outputs:
                raise OSError("output_aliases_protected_input")
            _write_output(args.output, rendered, force=args.force)
        except OSError:
            sys.stderr.buffer.write(rendered)
            return 2
    sys.stdout.buffer.write(rendered)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
