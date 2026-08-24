#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import io
import os
import stat
import sys
import secrets
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

TOOL_NAME = "build_pulsemech_device_ledger_reference_v0"
TOOL_VERSION = "0.1.0"
TOOL_SOURCE_PATH = "tools/build_pulsemech_device_ledger_reference_v0.py"

CANONICALIZATION_PROFILE_PATH = "contracts/pulsemech_device_canonical_json_v0.json"
OBSERVATION_CONTRACT_PATH = "contracts/pulsemech_ios_observation_contract_v0.json"
MANIFEST_SCHEMA_PATH = "schemas/pulsemech_device_ledger_manifest_v0.schema.json"
SIGNATURE_SCHEMA_PATH = "schemas/pulsemech_device_signature_v0.schema.json"
LEDGER_SCHEMA_PATH = "schemas/pulsemech_device_transition_ledger_v0.schema.json"

OBSERVER_PUBLIC_KEY_PATH = "keys/observer-public-key-v0.bin"
LEDGER_PATH = "ledger/pulsemech_device_transition_ledger_v0.json"
MANIFEST_PATH = "manifest/pulsemech_device_ledger_manifest_v0.json"
CHECKPOINT_SIGNATURE_PATH = "signatures/checkpoint-signature-v0.json"
PACKAGE_SIGNATURE_PATH = "signatures/package-signature-v0.json"

OUTPUT_CARRIER_NAME = "pulsemech_device_transition_ledger_reference_v0.pulseledger"
OUTPUT_LEDGER_NAME = "pulsemech_device_transition_ledger_reference_v0.json"
OUTPUT_MANIFEST_NAME = "pulsemech_device_ledger_manifest_reference_v0.json"

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

CONTRACT_SPECS: tuple[tuple[str, str, int], ...] = (
    (CANONICALIZATION_PROFILE_PATH, CANONICALIZATION_PROFILE_SHA256, CANONICALIZATION_PROFILE_BYTES),
    (OBSERVATION_CONTRACT_PATH, OBSERVATION_CONTRACT_SHA256, OBSERVATION_CONTRACT_BYTES),
    (MANIFEST_SCHEMA_PATH, MANIFEST_SCHEMA_SHA256, MANIFEST_SCHEMA_BYTES),
    (SIGNATURE_SCHEMA_PATH, SIGNATURE_SCHEMA_SHA256, SIGNATURE_SCHEMA_BYTES),
    (LEDGER_SCHEMA_PATH, LEDGER_SCHEMA_SHA256, LEDGER_SCHEMA_BYTES),
)

PACKAGE_MEMBER_ORDER: tuple[str, ...] = (
    CANONICALIZATION_PROFILE_PATH,
    OBSERVATION_CONTRACT_PATH,
    OBSERVER_PUBLIC_KEY_PATH,
    LEDGER_PATH,
    MANIFEST_PATH,
    MANIFEST_SCHEMA_PATH,
    SIGNATURE_SCHEMA_PATH,
    LEDGER_SCHEMA_PATH,
    CHECKPOINT_SIGNATURE_PATH,
    PACKAGE_SIGNATURE_PATH,
)

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

LEDGER_ID = "device-ledger:iphone-synthetic-reference-v0"
RECORD_STATUS = "synthetic_reference"
CHECKPOINT_SIGNATURE_DOMAIN = "PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0"
PACKAGE_SIGNATURE_DOMAIN = "PULSEMECH-DEVICE-LEDGER-PACKAGE-V0"
SIGNATURE_SUITE = "ecdsa-p256-sha256"

AUTHORITY_BOUNDARY = {
    "authority_effect": "none",
    "changes_release_authority": False,
    "creates_device_control_authority": False,
    "creates_release_decision": False,
}
LEDGER_CLAIM_BOUNDARY = {
    "causal_completion_claim": "none",
    "continuous_monitoring_claim": "none",
    "device_security_claim": "none",
    "malware_claim": "none",
    "physical_measurement_claim": "none",
    "release_authority_effect": "none",
    "system_wide_network_claim": "none",
}
PACKAGE_CLAIM_BOUNDARY = {
    "causal_completion_claim": "none",
    "continuous_monitoring_claim": "none",
    "device_security_claim": "none",
    "external_validation_claim": "none",
    "malware_claim": "none",
    "physical_measurement_claim": "none",
}

P256_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
P256_A = P256_P - 3
P256_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
P256_GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
P256_GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5
P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
P256_G = (P256_GX, P256_GY)
FIXTURE_PRIVATE_KEY_SEED = b"PULSEmech Device Transition Ledger fixture signing key v0"

BASE_WALL_TIME_NS = 1_700_000_000_000_000_000
WALL_TIME_STEP_NS = 1_000_000

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


class BuildError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_ascii(value: str, label: str) -> None:
    try:
        value.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise BuildError(f"{label}_not_ascii") from exc


def _canonical_string(value: str) -> str:
    _require_ascii(value, "canonical_string")
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
    for char in value:
        code = ord(char)
        if code in escapes:
            output.append(escapes[code])
        elif code <= 0x1F:
            output.append(f"\\u00{code:02x}")
        else:
            output.append(char)
    output.append('"')
    return "".join(output)


def _normalize_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 256:
        raise BuildError("canonical_json_depth_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -(2**63) or value > 2**63 - 1:
            raise BuildError("canonical_integer_out_of_range")
        return value
    if isinstance(value, str):
        _require_ascii(value, "canonical_string")
        normalized = unicodedata.normalize("NFC", value)
        if normalized != value:
            raise BuildError("canonical_string_not_nfc")
        return value
    if isinstance(value, list):
        return [_normalize_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise BuildError("canonical_key_not_string")
            _require_ascii(key, "canonical_key")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise BuildError("canonical_key_collision")
            normalized[normalized_key] = _normalize_value(item, depth=depth + 1)
        return normalized
    raise BuildError("canonical_json_type_unsupported")


def _canonical_text(value: Any, *, depth: int = 0) -> str:
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
        return _canonical_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_text(item, depth=depth + 1) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: key.encode("utf-8"))
        return "{" + ",".join(
            _canonical_string(key) + ":" + _canonical_text(value[key], depth=depth + 1)
            for key in keys
        ) + "}"
    raise BuildError("canonical_json_type_unsupported")


def canonical_json_bytes(value: Any) -> bytes:
    return _canonical_text(_normalize_value(value)).encode("utf-8")


def _inverse(value: int, modulus: int) -> int:
    if value % modulus == 0:
        raise BuildError("inverse_of_zero")
    return pow(value, -1, modulus)


def _point_add(
    left: tuple[int, int] | None,
    right: tuple[int, int] | None,
) -> tuple[int, int] | None:
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
        slope = ((y2 - y1) * _inverse(x2 - x1, P256_P)) % P256_P
    x3 = (slope * slope - x1 - x2) % P256_P
    y3 = (slope * (x1 - x3) - y1) % P256_P
    return x3, y3


def _scalar_mult(scalar: int, point: tuple[int, int] | None) -> tuple[int, int] | None:
    if scalar < 0:
        raise BuildError("negative_scalar")
    result: tuple[int, int] | None = None
    addend = point
    value = scalar
    while value:
        if value & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        value >>= 1
    return result


def _fixture_private_scalar() -> int:
    value = int.from_bytes(hashlib.sha256(FIXTURE_PRIVATE_KEY_SEED).digest(), "big")
    return value % (P256_N - 1) + 1


def _public_key_bytes(private_scalar: int) -> bytes:
    point = _scalar_mult(private_scalar, P256_G)
    if point is None:
        raise BuildError("fixture_public_key_at_infinity")
    x, y = point
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def _rfc6979_nonce(private_scalar: int, digest: bytes) -> int:
    if len(digest) != 32:
        raise BuildError("signature_digest_size_invalid")
    x = private_scalar.to_bytes(32, "big")
    z = int.from_bytes(digest, "big") % P256_N
    h1 = z.to_bytes(32, "big")
    v = b"\x01" * 32
    k = b"\x00" * 32
    k = hmac.new(k, v + b"\x00" + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        candidate = int.from_bytes(v, "big")
        if 1 <= candidate < P256_N:
            return candidate
        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def _sign_digest(private_scalar: int, digest: bytes) -> bytes:
    nonce = _rfc6979_nonce(private_scalar, digest)
    while True:
        point = _scalar_mult(nonce, P256_G)
        if point is None:
            nonce = (nonce + 1) % P256_N or 1
            continue
        r = point[0] % P256_N
        if r == 0:
            nonce = (nonce + 1) % P256_N or 1
            continue
        z = int.from_bytes(digest, "big")
        s = (_inverse(nonce, P256_N) * (z + r * private_scalar)) % P256_N
        if s == 0:
            nonce = (nonce + 1) % P256_N or 1
            continue
        if s > P256_N // 2:
            s = P256_N - s
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _signature_subject(
    *,
    ledger_id: str,
    observer_fingerprint: str,
    signed_object_sha256: str,
) -> dict[str, str]:
    return {
        "ledger_id": ledger_id,
        "observer_public_key_fingerprint_sha256": observer_fingerprint,
        "signature_suite": SIGNATURE_SUITE,
        "signed_object_sha256": signed_object_sha256,
    }


def _signature_digest(
    *,
    domain: str,
    ledger_id: str,
    observer_fingerprint: str,
    signed_object_sha256: str,
) -> bytes:
    subject = _signature_subject(
        ledger_id=ledger_id,
        observer_fingerprint=observer_fingerprint,
        signed_object_sha256=signed_object_sha256,
    )
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json_bytes(subject)).digest()


def _signature_document(
    *,
    private_scalar: int,
    ledger_id: str,
    observer_fingerprint: str,
    signature_domain: str,
    signature_role: str,
    signed_object_sha256: str,
    signed_object_type: str,
) -> dict[str, Any]:
    digest = _signature_digest(
        domain=signature_domain,
        ledger_id=ledger_id,
        observer_fingerprint=observer_fingerprint,
        signed_object_sha256=signed_object_sha256,
    )
    signature = _sign_digest(private_scalar, digest)
    return {
        "authority_effect": "none",
        "curve": "secp256r1",
        "document_type": "pulsemech_device_signature",
        "ecdsa_s_rule": "low_s_required",
        "ecdsa_scalar_range": "one_to_curve_order_minus_one",
        "hash_algorithm": "SHA-256",
        "ledger_id": ledger_id,
        "observer_public_key_fingerprint_sha256": observer_fingerprint,
        "public_key_encoding": "x963_uncompressed",
        "public_key_fingerprint_subject": "exact_65_byte_x963_uncompressed_public_key",
        "public_key_size_bytes": 65,
        "schema_version": "pulsemech_device_signature_v0",
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "signature_domain": signature_domain,
        "signature_encoding": "ieee_p1363_fixed_width",
        "signature_role": signature_role,
        "signature_size_bytes": 64,
        "signature_subject_canonicalization": "pulsemech_device_canonical_json_v0",
        "signature_subject_framing": "ascii_domain_separator_then_0x00_then_canonical_subject_json",
        "signature_subject_version": "pulsemech_device_signature_subject_v0",
        "signature_suite": SIGNATURE_SUITE,
        "signed_object_sha256": signed_object_sha256,
        "signed_object_type": signed_object_type,
    }


def _record_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record["record_id"],
        "record_sha256": record["record_sha256"],
        "sequence_index": record["sequence_index"],
    }


def _network_state(*, used: str, expensive: bool) -> dict[str, Any]:
    available = ["wifi", "cellular"]
    used_values = [used]
    if available != sorted(available, key=AVAILABLE_INTERFACE_ORDER.__getitem__):
        raise BuildError("fixture_available_interface_order_invalid")
    if used_values != sorted(used_values, key=USED_INTERFACE_ORDER.__getitem__):
        raise BuildError("fixture_used_interface_order_invalid")
    return {
        "available_interface_types": available,
        "is_constrained": False,
        "is_expensive": expensive,
        "status": "satisfied",
        "supports_dns": True,
        "supports_ipv4": True,
        "supports_ipv6": True,
        "used_interface_types": used_values,
    }


def _app_surface() -> dict[str, Any]:
    return {
        "availability": "observed",
        "source_interface": "UIKit UIScene.activationState and UISceneDelegate lifecycle callbacks",
        "state": {"activation_state": "foreground_active"},
        "surface_id": "app_lifecycle",
    }


def _network_surface(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "availability": "observed",
        "source_interface": "Network.framework NWPathMonitor.pathUpdateHandler",
        "state": dict(state),
        "surface_id": "network_path",
    }


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


def _relation_changes(
    *,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    observation_status: str,
) -> list[dict[str, Any]]:
    before = _flatten_network_state(source)
    after = _flatten_network_state(target)
    return [
        {
            "after": after[path],
            "before": before[path],
            "field_path": path,
            "observation_status": observation_status,
            "surface_id": "network_path",
        }
        for path in NETWORK_FIELD_PATHS
        if before[path] != after[path]
    ]


def _wall_time(sequence_index: int) -> int:
    return BASE_WALL_TIME_NS + sequence_index * WALL_TIME_STEP_NS


def _add_record(
    records: list[dict[str, Any]],
    *,
    record_id: str,
    record_type: str,
    payload: Mapping[str, Any],
    observer_fingerprint: str,
    session_id: str | None,
    clock_epoch_id: str | None,
    monotonic_time_ns: int | None,
) -> dict[str, Any]:
    sequence_index = len(records)
    record: dict[str, Any] = {
        "authority_effect": "none",
        "canonicalization_profile_sha256": CANONICALIZATION_PROFILE_SHA256,
        "claim_boundary": dict(LEDGER_CLAIM_BOUNDARY),
        "clock_epoch_id": clock_epoch_id,
        "document_type": "pulsemech_device_ledger_record",
        "ledger_id": LEDGER_ID,
        "monotonic_time_ns": monotonic_time_ns,
        "observation_contract_sha256": OBSERVATION_CONTRACT_SHA256,
        "observer_public_key_fingerprint_sha256": observer_fingerprint,
        "payload": dict(payload),
        "previous_record_sha256": records[-1]["record_sha256"] if records else None,
        "record_id": record_id,
        "record_status": RECORD_STATUS,
        "record_type": record_type,
        "recorded_wall_time_unix_ns": _wall_time(sequence_index),
        "schema_version": "pulsemech_device_ledger_record_v0",
        "sequence_index": sequence_index,
        "session_id": session_id,
    }
    record["record_sha256"] = sha256_bytes(canonical_json_bytes(record))
    records.append(record)
    return record


def _build_ledger(public_key: bytes, observer_fingerprint: str) -> tuple[dict[str, Any], dict[str, Any]]:
    session_a = "session:synthetic-a"
    session_b = "session:synthetic-b"
    epoch_a = "clock-epoch:synthetic-a"
    epoch_b = "clock-epoch:synthetic-b"
    wifi_state = _network_state(used="wifi", expensive=False)
    cellular_state = _network_state(used="cellular", expensive=True)
    records: list[dict[str, Any]] = []

    open_a = _add_record(
        records,
        record_id="record:000-session-open-a",
        record_type="session_boundary",
        payload={
            "boundary_id": "boundary:open-a",
            "boundary_kind": "opened",
            "duplicate_boundary_rule": "not_applicable_new_session",
            "lifecycle_event": "scene_did_become_active",
            "network_surface_after_boundary": "unavailable_until_fresh_path_update",
            "observation_window_state": "open",
            "payload_type": "session_boundary",
            "previous_session_id": None,
            "session_terminal": False,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=1_000,
    )
    event_wifi_a = _add_record(
        records,
        record_id="record:001-path-wifi-a",
        record_type="observation_event",
        payload={
            "accepted_while_window_open": True,
            "event_id": "event:path-wifi-a",
            "event_role": "surface_observation",
            "event_type": "path_update_received",
            "initiating_cause_claim": "none",
            "payload_type": "observation_event",
            "platform_event_time_unix_ns": None,
            "source_interface": "Network.framework NWPathMonitor.pathUpdateHandler",
            "surface_id": "network_path",
            "target_projection": wifi_state,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=2_000,
    )
    snapshot_wifi_a = _add_record(
        records,
        record_id="record:002-snapshot-wifi-a",
        record_type="state_snapshot",
        payload={
            "network_freshness_status": "fresh_callback_bound_in_same_session",
            "payload_type": "state_snapshot",
            "snapshot_id": "snapshot:wifi-a",
            "snapshot_role": "source_endpoint",
            "source_event_binding": _record_ref(event_wifi_a),
            "surfaces": [_app_surface(), _network_surface(wifi_state)],
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=3_000,
    )
    event_cellular_a = _add_record(
        records,
        record_id="record:003-path-cellular-a",
        record_type="observation_event",
        payload={
            "accepted_while_window_open": True,
            "event_id": "event:path-cellular-a",
            "event_role": "surface_observation",
            "event_type": "path_update_received",
            "initiating_cause_claim": "none",
            "payload_type": "observation_event",
            "platform_event_time_unix_ns": None,
            "source_interface": "Network.framework NWPathMonitor.pathUpdateHandler",
            "surface_id": "network_path",
            "target_projection": cellular_state,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=4_000,
    )
    snapshot_cellular_a = _add_record(
        records,
        record_id="record:004-snapshot-cellular-a",
        record_type="state_snapshot",
        payload={
            "network_freshness_status": "fresh_callback_bound_in_same_session",
            "payload_type": "state_snapshot",
            "snapshot_id": "snapshot:cellular-a",
            "snapshot_role": "target_endpoint",
            "source_event_binding": _record_ref(event_cellular_a),
            "surfaces": [_app_surface(), _network_surface(cellular_state)],
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=5_000,
    )
    coverage_continuous = _add_record(
        records,
        record_id="record:005-coverage-continuous",
        record_type="coverage_interval",
        payload={
            "boundary_basis": "same_session_consecutive_bound_endpoints",
            "coverage_status": "continuous",
            "gap_end_boundary": None,
            "gap_start_boundary": None,
            "intermediate_path_status": "observed_continuous",
            "interval_id": "coverage:continuous-a",
            "network_freshness_rule": "same_session_event_projection_bound",
            "observer_execution_status": "observed_active",
            "payload_type": "coverage_interval",
            "source_clock_epoch_id": epoch_a,
            "source_session_id": session_a,
            "source_snapshot": _record_ref(snapshot_wifi_a),
            "target_clock_epoch_id": epoch_a,
            "target_session_id": session_a,
            "target_snapshot": _record_ref(snapshot_cellular_a),
        },
        observer_fingerprint=observer_fingerprint,
        session_id=None,
        clock_epoch_id=None,
        monotonic_time_ns=None,
    )
    _add_record(
        records,
        record_id="record:006-transition-event-bound",
        record_type="transition",
        payload={
            "axes": {
                "alternative_path_closure_status": "not_evaluated",
                "causal_necessity_status": "not_established",
                "causal_sufficiency_status": "not_established",
                "endpoint_binding_status": "verified",
                "endpoint_observation_source_binding_status": "all_bound",
                "observation_coverage_status": "continuous",
                "relation_change_observation_status": "all_event_observed",
                "time_order_status": "monotonic_and_sequence_verified",
                "transition_path_verification_status": "observation_event_bound",
            },
            "coverage_binding": _record_ref(coverage_continuous),
            "endpoint_selection_rule": "immediate_eligible_network_snapshots_around_event",
            "event_binding": _record_ref(event_cellular_a),
            "event_consumption_rule": "one_transition_per_event_no_intervening_network_event",
            "initiating_event_unix_ns": None,
            "initiating_source_identity": None,
            "initiating_source_status": "unavailable_from_platform",
            "payload_type": "transition",
            "relation_changes": _relation_changes(
                source=wifi_state,
                target=cellular_state,
                observation_status="event_observed",
            ),
            "source_snapshot": _record_ref(snapshot_wifi_a),
            "target_snapshot": _record_ref(snapshot_cellular_a),
            "transition_class": "event_bound",
            "transition_id": "transition:event-bound-wifi-to-cellular",
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=6_000,
    )
    close_a = _add_record(
        records,
        record_id="record:007-session-close-a",
        record_type="session_boundary",
        payload={
            "boundary_id": "boundary:close-a",
            "boundary_kind": "observation_window_closed",
            "duplicate_boundary_rule": "idempotent_no_second_gap_start",
            "lifecycle_event": "scene_will_resign_active",
            "network_surface_after_boundary": "last_bound_value_retained_for_gap_source_only",
            "observation_window_state": "closed",
            "payload_type": "session_boundary",
            "previous_session_id": session_a,
            "session_terminal": False,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_a,
        clock_epoch_id=epoch_a,
        monotonic_time_ns=7_000,
    )
    open_b = _add_record(
        records,
        record_id="record:008-session-open-b",
        record_type="session_boundary",
        payload={
            "boundary_id": "boundary:open-b",
            "boundary_kind": "opened",
            "duplicate_boundary_rule": "not_applicable_new_session",
            "lifecycle_event": "scene_did_become_active",
            "network_surface_after_boundary": "unavailable_until_fresh_path_update",
            "observation_window_state": "open",
            "payload_type": "session_boundary",
            "previous_session_id": session_a,
            "session_terminal": False,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_b,
        clock_epoch_id=epoch_b,
        monotonic_time_ns=1_000,
    )
    event_wifi_b = _add_record(
        records,
        record_id="record:009-path-wifi-b",
        record_type="observation_event",
        payload={
            "accepted_while_window_open": True,
            "event_id": "event:path-wifi-b",
            "event_role": "surface_observation",
            "event_type": "path_update_received",
            "initiating_cause_claim": "none",
            "payload_type": "observation_event",
            "platform_event_time_unix_ns": None,
            "source_interface": "Network.framework NWPathMonitor.pathUpdateHandler",
            "surface_id": "network_path",
            "target_projection": wifi_state,
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_b,
        clock_epoch_id=epoch_b,
        monotonic_time_ns=2_000,
    )
    snapshot_wifi_b = _add_record(
        records,
        record_id="record:010-snapshot-wifi-b",
        record_type="state_snapshot",
        payload={
            "network_freshness_status": "fresh_callback_bound_in_same_session",
            "payload_type": "state_snapshot",
            "snapshot_id": "snapshot:wifi-b",
            "snapshot_role": "target_endpoint",
            "source_event_binding": _record_ref(event_wifi_b),
            "surfaces": [_app_surface(), _network_surface(wifi_state)],
        },
        observer_fingerprint=observer_fingerprint,
        session_id=session_b,
        clock_epoch_id=epoch_b,
        monotonic_time_ns=3_000,
    )
    coverage_interrupted = _add_record(
        records,
        record_id="record:011-coverage-interrupted",
        record_type="coverage_interval",
        payload={
            "boundary_basis": "last_bound_before_close_to_first_fresh_bound_after_reopen",
            "coverage_status": "interrupted",
            "gap_end_boundary": _record_ref(open_b),
            "gap_start_boundary": _record_ref(close_a),
            "intermediate_path_status": "unobserved",
            "interval_id": "coverage:interrupted-a-to-b",
            "network_freshness_rule": "fresh_post_reopen_callback_required_before_target_snapshot",
            "observer_execution_status": "execution_unavailable_between_bounds",
            "payload_type": "coverage_interval",
            "source_clock_epoch_id": epoch_a,
            "source_session_id": session_a,
            "source_snapshot": _record_ref(snapshot_cellular_a),
            "target_clock_epoch_id": epoch_b,
            "target_session_id": session_b,
            "target_snapshot": _record_ref(snapshot_wifi_b),
        },
        observer_fingerprint=observer_fingerprint,
        session_id=None,
        clock_epoch_id=None,
        monotonic_time_ns=None,
    )
    transition_gap = _add_record(
        records,
        record_id="record:012-transition-endpoint-difference",
        record_type="transition",
        payload={
            "axes": {
                "alternative_path_closure_status": "open",
                "causal_necessity_status": "not_established",
                "causal_sufficiency_status": "not_established",
                "endpoint_binding_status": "verified",
                "endpoint_observation_source_binding_status": "all_bound",
                "observation_coverage_status": "gap_between_endpoints",
                "relation_change_observation_status": "all_endpoint_difference_observed",
                "time_order_status": "sequence_verified",
                "transition_path_verification_status": "endpoint_difference_only",
            },
            "coverage_binding": _record_ref(coverage_interrupted),
            "endpoint_selection_rule": "last_bound_before_gap_and_first_fresh_bound_after_reopen",
            "event_binding": None,
            "event_consumption_rule": "no_event_binding_permitted",
            "initiating_event_unix_ns": None,
            "initiating_source_identity": None,
            "initiating_source_status": "unavailable_from_platform",
            "payload_type": "transition",
            "relation_changes": _relation_changes(
                source=cellular_state,
                target=wifi_state,
                observation_status="endpoint_difference_observed",
            ),
            "source_snapshot": _record_ref(snapshot_cellular_a),
            "target_snapshot": _record_ref(snapshot_wifi_b),
            "transition_class": "endpoint_difference_only",
            "transition_id": "transition:endpoint-difference-cellular-to-wifi",
        },
        observer_fingerprint=observer_fingerprint,
        session_id=None,
        clock_epoch_id=None,
        monotonic_time_ns=None,
    )

    checkpoint_sequence = len(records)
    checkpoint_payload = {
        "canonicalization_profile_sha256": CANONICALIZATION_PROFILE_SHA256,
        "checkpoint_id": "checkpoint:synthetic-reference-v0",
        "checkpoint_signature_required": True,
        "clock_epoch_count": 2,
        "closed_record_count": len(records),
        "coverage_summary": {
            "continuous_intervals": 1,
            "interrupted_intervals": 1,
        },
        "created_unix_ns": _wall_time(checkpoint_sequence),
        "first_record": _record_ref(open_a),
        "ledger_id": LEDGER_ID,
        "observation_contract_sha256": OBSERVATION_CONTRACT_SHA256,
        "observer_public_key_fingerprint_sha256": observer_fingerprint,
        "payload_type": "checkpoint",
        "record_type_counts": {
            "coverage_interval": 2,
            "observation_event": 3,
            "session_boundary": 3,
            "state_snapshot": 3,
            "transition": 2,
        },
        "session_count": 2,
        "signature_schema_sha256": SIGNATURE_SCHEMA_SHA256,
        "terminal_record": _record_ref(transition_gap),
        "terminal_sequence_index": transition_gap["sequence_index"],
        "transition_summary": {
            "endpoint_difference_only": 1,
            "event_bound": 1,
        },
    }
    checkpoint = _add_record(
        records,
        record_id="record:013-checkpoint",
        record_type="checkpoint",
        payload=checkpoint_payload,
        observer_fingerprint=observer_fingerprint,
        session_id=None,
        clock_epoch_id=None,
        monotonic_time_ns=None,
    )

    ledger = {
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "canonicalization_profile": {
            "digest_algorithm": "SHA-256",
            "digest_subject": "exact_package_member_bytes",
            "member_path": CANONICALIZATION_PROFILE_PATH,
            "profile_id": "pulsemech_device_canonical_json_v0",
            "profile_sha256": CANONICALIZATION_PROFILE_SHA256,
            "profile_version": "0.1.0",
        },
        "claim_boundary": dict(LEDGER_CLAIM_BOUNDARY),
        "document_type": "pulsemech_device_transition_ledger",
        "ledger_identity": {
            "created_unix_ns": records[0]["recorded_wall_time_unix_ns"],
            "ledger_id": LEDGER_ID,
        },
        "ledger_summary": {
            "checkpoint_record_sha256": checkpoint["record_sha256"],
            "clock_epoch_count": 2,
            "coverage_interval_count": 2,
            "observation_event_count": 3,
            "record_count": len(records),
            "session_boundary_count": 3,
            "session_count": 2,
            "snapshot_count": 3,
            "terminal_record_sha256": checkpoint["record_sha256"],
            "transition_count": 2,
        },
        "observation_contract": {
            "contract_id": "pulsemech_ios_observation_contract_v0",
            "contract_sha256": OBSERVATION_CONTRACT_SHA256,
            "contract_version": "0.1.0",
            "digest_algorithm": "SHA-256",
            "digest_subject": "exact_package_member_bytes",
            "member_path": OBSERVATION_CONTRACT_PATH,
        },
        "observer_identity": {
            "device_class": "iphone",
            "identity_scope": "fixture_installation",
            "key_origin_profile": "fixture_software_p256",
            "platform": "ios",
            "platform_attestation_status": "not_present",
            "public_key_base64": base64.b64encode(public_key).decode("ascii"),
            "public_key_encoding": "x963_uncompressed",
            "public_key_fingerprint_sha256": observer_fingerprint,
            "public_key_size_bytes": 65,
            "signature_encoding": "ieee_p1363_fixed_width",
            "signature_suite": SIGNATURE_SUITE,
        },
        "record_status": RECORD_STATUS,
        "records": records,
        "reference_device_class": "iphone",
        "reference_platform": "ios",
        "schema_version": "pulsemech_device_transition_ledger_v0",
        "signature_schema": {
            "digest_algorithm": "SHA-256",
            "digest_subject": "exact_package_member_bytes",
            "member_path": SIGNATURE_SCHEMA_PATH,
            "schema_id": "pulsemech_device_signature_v0",
            "schema_sha256": SIGNATURE_SCHEMA_SHA256,
            "schema_version": "pulsemech_device_signature_v0",
        },
    }
    return ledger, checkpoint


def _carrier_contract() -> dict[str, Any]:
    return {
        "archive_comment": "forbidden",
        "archive_format": "zip",
        "archive_member_set": "exact_payload_paths_plus_manifest_and_package_signature",
        "carrier_identity_location": "verifier_report_only",
        "compression_method": "stored",
        "crc32": "required_and_verified",
        "data_descriptors": "forbidden",
        "directory_entries": "forbidden",
        "duplicate_member_names": "forbidden",
        "encrypted_members": "forbidden",
        "extra_fields": "forbidden",
        "file_extension": ".pulseledger",
        "local_central_directory_consistency": "required",
        "max_carrier_bytes": 33554432,
        "max_member_bytes": 16777216,
        "max_total_uncompressed_bytes": 33554432,
        "member_comments": "forbidden",
        "member_name_encoding": "ASCII",
        "member_name_policy": "relative_posix_no_dot_segments_no_backslash_no_nul",
        "member_order_semantics": "not_authority_bearing_exact_carrier_hash_records_instance_order",
        "non_regular_members": "forbidden",
        "symlinks": "forbidden",
        "timestamp_policy": "fixed_1980_01_01_00_00_00",
        "trailing_data": "forbidden",
        "zip64": "forbidden",
    }


def _build_manifest(
    *,
    members: Mapping[str, bytes],
    ledger: Mapping[str, Any],
    ledger_bytes: bytes,
    checkpoint: Mapping[str, Any],
    observer_fingerprint: str,
) -> dict[str, Any]:
    payload_members = [
        {
            "byte_identity": "exact_member_bytes",
            "media_type": media_type,
            "path": path,
            "role": role,
            "sha256": sha256_bytes(members[path]),
            "size_bytes": len(members[path]),
        }
        for path, role, media_type in PAYLOAD_MEMBER_SPECS
    ]
    return {
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "carrier_contract": _carrier_contract(),
        "claim_boundary": dict(PACKAGE_CLAIM_BOUNDARY),
        "created_unix_ns": checkpoint["payload"]["created_unix_ns"],
        "document_type": "pulsemech_device_ledger_manifest",
        "ledger_binding": {
            "checkpoint_record_sha256": checkpoint["record_sha256"],
            "ledger_id": ledger["ledger_identity"]["ledger_id"],
            "ledger_member_path": LEDGER_PATH,
            "ledger_schema_member_path": LEDGER_SCHEMA_PATH,
            "ledger_schema_sha256": LEDGER_SCHEMA_SHA256,
            "ledger_sha256": sha256_bytes(ledger_bytes),
            "ledger_size_bytes": len(ledger_bytes),
            "record_count": len(ledger["records"]),
            "terminal_record_sha256": checkpoint["record_sha256"],
        },
        "manifest_contract": {
            "canonicalization": "pulsemech_device_canonical_json_v0",
            "digest_algorithm": "SHA-256",
            "digest_subject": "exact_canonical_manifest_bytes",
            "manifest_path": MANIFEST_PATH,
            "manifest_self_inventory": "excluded_to_avoid_circularity",
            "package_signature_inventory": "excluded_to_avoid_circularity",
            "package_signature_path": PACKAGE_SIGNATURE_PATH,
        },
        "observer_binding": {
            "fingerprint_algorithm": "SHA-256",
            "fingerprint_subject": "exact_65_byte_x963_uncompressed_public_key",
            "observer_public_key_fingerprint_sha256": observer_fingerprint,
            "public_key_encoding": "x963_uncompressed",
            "public_key_member_path": OBSERVER_PUBLIC_KEY_PATH,
            "public_key_size_bytes": 65,
            "signature_suite": SIGNATURE_SUITE,
        },
        "package_format": "pulseledger_zip_v0",
        "package_member_count": 10,
        "payload_member_count": 8,
        "payload_members": payload_members,
        "record_status": RECORD_STATUS,
        "reference_device_class": "iphone",
        "reference_platform": "ios",
        "schema_version": "pulsemech_device_ledger_manifest_v0",
        "signature_contract": {
            "checkpoint_signature_path": CHECKPOINT_SIGNATURE_PATH,
            "checkpoint_signed_object_type": "checkpoint_record_sha256",
            "package_signature_path": PACKAGE_SIGNATURE_PATH,
            "package_signature_subject": "SHA-256_of_exact_canonical_manifest_bytes",
            "package_signed_object_type": "ledger_manifest_sha256",
            "signature_schema_member_path": SIGNATURE_SCHEMA_PATH,
            "signature_schema_sha256": SIGNATURE_SCHEMA_SHA256,
            "signature_suite": SIGNATURE_SUITE,
        },
    }


def _deterministic_zip(members: Mapping[str, bytes]) -> bytes:
    if tuple(members) != PACKAGE_MEMBER_ORDER:
        raise BuildError("package_member_order_mismatch")
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for path in PACKAGE_MEMBER_ORDER:
            if PurePosixPath(path).as_posix() != path or path.startswith("/") or ".." in PurePosixPath(path).parts:
                raise BuildError("unsafe_package_member_path")
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            info.flag_bits = 0
            archive.writestr(info, members[path])
    return buffer.getvalue()


def _read_exact_contracts(repository_root: Path) -> tuple[Path, dict[str, bytes]]:
    root = repository_root.resolve(strict=True)
    if not root.is_dir():
        raise BuildError("repository_root_not_directory")
    output: dict[str, bytes] = {}
    for relative, expected_sha, expected_size in CONTRACT_SPECS:
        path = root / PurePosixPath(relative)
        try:
            resolved = path.resolve(strict=True)
            metadata = path.lstat()
        except OSError as exc:
            raise BuildError(f"contract_missing:{relative}") from exc
        if resolved != path or not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise BuildError(f"contract_not_regular_or_canonical:{relative}")
        payload = path.read_bytes()
        if len(payload) != expected_size or sha256_bytes(payload) != expected_sha:
            raise BuildError(f"contract_identity_mismatch:{relative}")
        output[relative] = payload
    return root, output


def build_reference_package(repository_root: Path) -> tuple[Path, bytes, bytes, bytes, dict[str, Any]]:
    root, contracts = _read_exact_contracts(repository_root)
    private_scalar = _fixture_private_scalar()
    public_key = _public_key_bytes(private_scalar)
    observer_fingerprint = sha256_bytes(public_key)
    ledger, checkpoint = _build_ledger(public_key, observer_fingerprint)
    ledger_bytes = canonical_json_bytes(ledger)
    checkpoint_signature = _signature_document(
        private_scalar=private_scalar,
        ledger_id=LEDGER_ID,
        observer_fingerprint=observer_fingerprint,
        signature_domain=CHECKPOINT_SIGNATURE_DOMAIN,
        signature_role="ledger_checkpoint",
        signed_object_sha256=checkpoint["record_sha256"],
        signed_object_type="checkpoint_record_sha256",
    )
    checkpoint_signature_bytes = canonical_json_bytes(checkpoint_signature)
    members_before_manifest: dict[str, bytes] = {
        CANONICALIZATION_PROFILE_PATH: contracts[CANONICALIZATION_PROFILE_PATH],
        OBSERVATION_CONTRACT_PATH: contracts[OBSERVATION_CONTRACT_PATH],
        OBSERVER_PUBLIC_KEY_PATH: public_key,
        LEDGER_PATH: ledger_bytes,
        MANIFEST_SCHEMA_PATH: contracts[MANIFEST_SCHEMA_PATH],
        SIGNATURE_SCHEMA_PATH: contracts[SIGNATURE_SCHEMA_PATH],
        LEDGER_SCHEMA_PATH: contracts[LEDGER_SCHEMA_PATH],
        CHECKPOINT_SIGNATURE_PATH: checkpoint_signature_bytes,
    }
    manifest = _build_manifest(
        members=members_before_manifest,
        ledger=ledger,
        ledger_bytes=ledger_bytes,
        checkpoint=checkpoint,
        observer_fingerprint=observer_fingerprint,
    )
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_sha = sha256_bytes(manifest_bytes)
    package_signature = _signature_document(
        private_scalar=private_scalar,
        ledger_id=LEDGER_ID,
        observer_fingerprint=observer_fingerprint,
        signature_domain=PACKAGE_SIGNATURE_DOMAIN,
        signature_role="ledger_package",
        signed_object_sha256=manifest_sha,
        signed_object_type="ledger_manifest_sha256",
    )
    package_signature_bytes = canonical_json_bytes(package_signature)
    members: dict[str, bytes] = {
        CANONICALIZATION_PROFILE_PATH: contracts[CANONICALIZATION_PROFILE_PATH],
        OBSERVATION_CONTRACT_PATH: contracts[OBSERVATION_CONTRACT_PATH],
        OBSERVER_PUBLIC_KEY_PATH: public_key,
        LEDGER_PATH: ledger_bytes,
        MANIFEST_PATH: manifest_bytes,
        MANIFEST_SCHEMA_PATH: contracts[MANIFEST_SCHEMA_PATH],
        SIGNATURE_SCHEMA_PATH: contracts[SIGNATURE_SCHEMA_PATH],
        LEDGER_SCHEMA_PATH: contracts[LEDGER_SCHEMA_PATH],
        CHECKPOINT_SIGNATURE_PATH: checkpoint_signature_bytes,
        PACKAGE_SIGNATURE_PATH: package_signature_bytes,
    }
    carrier = _deterministic_zip(members)
    summary = {
        "authority_effect": "none",
        "carrier_sha256": sha256_bytes(carrier),
        "carrier_size_bytes": len(carrier),
        "checkpoint_record_sha256": checkpoint["record_sha256"],
        "checkpoint_signature_sha256": sha256_bytes(checkpoint_signature_bytes),
        "ledger_id": LEDGER_ID,
        "ledger_sha256": sha256_bytes(ledger_bytes),
        "ledger_size_bytes": len(ledger_bytes),
        "manifest_sha256": manifest_sha,
        "manifest_size_bytes": len(manifest_bytes),
        "observer_public_key_fingerprint_sha256": observer_fingerprint,
        "package_signature_sha256": sha256_bytes(package_signature_bytes),
        "record_count": len(ledger["records"]),
        "record_status": RECORD_STATUS,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }
    return root, carrier, ledger_bytes, manifest_bytes, summary


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _publish_output_directory(
    *,
    repository_root: Path,
    output_directory: Path,
    carrier: bytes,
    ledger_bytes: bytes,
    manifest_bytes: bytes,
) -> None:
    destination = output_directory.resolve(strict=False)
    parent = destination.parent.resolve(strict=True)
    if not parent.is_dir():
        raise BuildError("output_parent_not_directory")
    if destination.exists():
        raise BuildError(f"output_directory_exists:{destination}")
    if _is_within(destination, repository_root):
        raise BuildError("output_directory_inside_repository")
    temporary = parent / f".{destination.name}.{secrets.token_hex(16)}.tmp"
    if temporary.exists():
        raise BuildError("temporary_output_collision")
    os.mkdir(temporary, 0o700)
    published = False
    try:
        outputs = {
            OUTPUT_CARRIER_NAME: carrier,
            OUTPUT_LEDGER_NAME: ledger_bytes,
            OUTPUT_MANIFEST_NAME: manifest_bytes,
        }
        for name, payload in outputs.items():
            path = temporary / name
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= int(getattr(os, "O_CLOEXEC", 0))
            descriptor = os.open(path, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb", closefd=True) as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            os.chmod(path, 0o444)
        directory_descriptor = os.open(
            temporary,
            os.O_RDONLY | os.O_DIRECTORY | int(getattr(os, "O_CLOEXEC", 0)),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        os.rename(temporary, destination)
        published = True
        parent_descriptor = os.open(
            parent,
            os.O_RDONLY | os.O_DIRECTORY | int(getattr(os, "O_CLOEXEC", 0)),
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
        observed = {path.name: path.read_bytes() for path in destination.iterdir()}
        if observed != outputs:
            raise BuildError("published_output_readback_mismatch")
        os.chmod(destination, 0o555)
    finally:
        if not published and temporary.exists():
            for child in temporary.iterdir():
                child.chmod(0o600)
                child.unlink()
            temporary.rmdir()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the deterministic synthetic PULSEmech iPhone Device Transition Ledger reference package."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--output-directory",
        required=True,
        help="New output directory outside the repository; it must not already exist.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root, carrier, ledger_bytes, manifest_bytes, summary = build_reference_package(
            Path(args.repository_root)
        )
        _publish_output_directory(
            repository_root=root,
            output_directory=Path(args.output_directory),
            carrier=carrier,
            ledger_bytes=ledger_bytes,
            manifest_bytes=manifest_bytes,
        )
        sys.stdout.buffer.write(canonical_json_bytes(summary) + b"\n")
        return 0
    except (BuildError, OSError, ValueError, zipfile.BadZipFile) as exc:
        diagnostic = {
            "authority_effect": "none",
            "error": str(exc),
            "ok": False,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        }
        sys.stderr.buffer.write(canonical_json_bytes(diagnostic) + b"\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
