#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
)
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "pulsemech_device_ledger_reproduction_capsule_v0.json"
)
CANONICALIZATION_PATH = (
    ROOT
    / "contracts"
    / "pulsemech_device_canonical_json_v0.json"
)
REFERENCE_ROOT = ROOT / "examples" / "device_transition_ledger"
REFERENCE_MANIFEST_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json"
)
REFERENCE_LEDGER_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_transition_ledger_reference_v0.pulseledger"
)
REFERENCE_REPORT_PATH = (
    REFERENCE_ROOT
    / "pulsemech_device_transition_ledger_reference_verification_v0.json"
)
VERIFIER_PATH = ROOT / "tools" / "verify_pulsemech_device_ledger_v0.py"

EXPECTED_SCHEMA_IDENTITY = (
    32581,
    "a1b8a3734214824883e8a65dbb9dc7c33ca585e0761c312fd85f4db3787ea85c",
    "6a0dabff2e5f725c6ef8e586f9cae7fff566030b",
)
EXPECTED_CONTRACT_IDENTITY = (
    15947,
    "ea45871d8f173729b2429944a949bc1edd9a06b78ffb438863d7c8d0d7687a67",
    "d15fddbe9250de0ed76b3b7ebb7d679383a867b4",
)
EXPECTED_MANIFEST_IDENTITY = (
    8989,
    "cda4218f279820640590a71c78b85a29cb11de3fc7d29a96727d669c30cdbcbf",
    "b9c4aeb2cc2133e54c83ae81e45ab8358c5b0d3b",
)
EXPECTED_CANONICALIZATION_IDENTITY = (
    2719,
    "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
)
EXPECTED_LEDGER_IDENTITY = (
    133568,
    "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3",
)
EXPECTED_VERIFIER_IDENTITY = (
    126419,
    "0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7",
)
EXPECTED_REPORT_IDENTITY = (
    15328,
    "5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4",
)
EXPECTED_OBSERVER_FINGERPRINT = (
    "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
)
EXPECTED_PAYLOAD_SOURCE_COMMIT = (
    "0108e2c0da98c8a1fe5e739aa0f137ba6a3464e1"
)
EXPECTED_CONTAINER_IMAGE = (
    "docker.io/library/python:3.11.9-slim-bookworm@"
    "sha256:2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
EXPECTED_MEMBER_ORDER = (
    "manifest/pulsemech_device_ledger_reproduction_capsule_manifest_v0.json",
    "artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger",
    "verifier/verify_pulsemech_device_ledger_v0.py",
    "expected/pulsemech_device_transition_ledger_reference_verification_v0.json",
)
EXPECTED_POSITIVE_REQUIREMENTS = (
    "schema_is_valid_draft_2020_12",
    "contract_json_is_strict",
    "canonical_manifest_is_strict_and_canonical",
    "canonical_manifest_satisfies_schema",
    "exact_four_member_layout",
    "exact_three_payload_member_inventory",
    "exact_member_order",
    "exact_payload_sizes_and_sha256",
    "exact_observer_fingerprint",
    "acyclic_identity_graph",
    "complete_archive_profile",
    "complete_reference_environment",
    "positive_reproduction_contract",
    "repeated_construction_contract",
    "negative_reproduction_contract",
    "runner_verifier_separation",
    "claim_boundary",
    "authority_boundary",
)
EXPECTED_NEGATIVE_CASES = (
    "missing_member",
    "extra_member",
    "duplicate_member_path",
    "wrong_member_order",
    "absolute_member_path",
    "parent_traversal",
    "directory_member",
    "unsupported_compression",
    "non_fixed_timestamp",
    "non_empty_extra_field",
    "non_empty_archive_comment",
    "source_size_mismatch",
    "source_sha256_mismatch",
    "wrong_observer_fingerprint",
    "wrong_container_image",
    "wrong_architecture",
    "wrong_os_distribution",
    "wrong_os_version",
    "wrong_python_version",
    "volatile_manifest_field",
    "manifest_self_hash",
    "final_capsule_hash_inside_manifest",
    "wrong_mutation_target",
    "wrong_failed_check_expectation",
    "authority_effect_expansion",
    "new_verifier_claim",
)
FORBIDDEN_MANIFEST_KEYS = {
    "capsule_sha256",
    "capsule_size_bytes",
    "created_at",
    "created_unix_ns",
    "generated_at",
    "generated_unix_ns",
    "git_commit",
    "manifest_sha256",
    "manifest_size_bytes",
    "random_id",
    "run_id",
    "workflow_run_id",
}


class StrictJSONError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _parse_int(raw: str) -> int:
    if raw == "-0":
        raise StrictJSONError("negative_zero_forbidden")
    value = int(raw, 10)
    if value < -(2**63) or value > 2**63 - 1:
        raise StrictJSONError("integer_out_of_signed_64_bit_range")
    return value


def _reject_float(raw: str) -> Any:
    raise StrictJSONError(f"floating_point_forbidden:{raw}")


def _reject_constant(raw: str) -> Any:
    raise StrictJSONError(f"non_finite_number_forbidden:{raw}")


def _object_pairs_no_duplicates(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate_decoded_key:{key}")
        result[key] = value
    return result


def strict_json_loads(payload: bytes, *, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise StrictJSONError(f"{label}:utf8_bom_forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJSONError(f"{label}:malformed_utf8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs_no_duplicates,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(f"{label}:strict_json_invalid:{exc}") from exc
    if not isinstance(value, dict):
        raise StrictJSONError(f"{label}:top_level_must_be_object")
    return value


def _normalize_string(value: str, *, label: str) -> str:
    for char in value:
        code_point = ord(char)
        if 0xD800 <= code_point <= 0xDFFF:
            raise StrictJSONError(f"{label}:unpaired_surrogate_forbidden")
        if code_point > 0x7F:
            if unicodedata.unidata_version != "14.0.0":
                raise StrictJSONError(
                    f"{label}:unicode_14_required_for_non_ascii_manifest_string"
                )
            if unicodedata.category(char) == "Cn":
                raise StrictJSONError(f"{label}:unassigned_code_point_forbidden")
    return unicodedata.normalize("NFC", value)


def _normalize_value(value: Any, *, path: str = "$", depth: int = 0) -> Any:
    if depth > 256:
        raise StrictJSONError(f"{path}:maximum_depth_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -(2**63) or value > 2**63 - 1:
            raise StrictJSONError(f"{path}:integer_out_of_signed_64_bit_range")
        return value
    if isinstance(value, str):
        return _normalize_string(value, label=path)
    if isinstance(value, list):
        return [
            _normalize_value(item, path=f"{path}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise StrictJSONError(f"{path}:object_key_not_string")
            normalized_key = _normalize_string(key, label=f"{path}:key")
            if normalized_key in normalized:
                raise StrictJSONError(
                    f"{path}:normalized_key_collision:{normalized_key}"
                )
            normalized[normalized_key] = _normalize_value(
                item,
                path=f"{path}.{normalized_key}",
                depth=depth + 1,
            )
        return normalized
    raise StrictJSONError(f"{path}:unsupported_json_type:{type(value).__name__}")


def _canonical_string(value: str) -> str:
    output: list[str] = ['"']
    required_escapes = {
        0x08: "\\b",
        0x09: "\\t",
        0x0A: "\\n",
        0x0C: "\\f",
        0x0D: "\\r",
        0x22: '\\"',
        0x5C: "\\\\",
    }
    for char in value:
        code_point = ord(char)
        if code_point in required_escapes:
            output.append(required_escapes[code_point])
        elif code_point <= 0x1F:
            output.append(f"\\u00{code_point:02x}")
        else:
            output.append(char)
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
    normalized = _normalize_value(dict(value))
    return _canonical_text(normalized).encode("utf-8")


def _read_strict_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"required file missing: {path.relative_to(ROOT)}")
    return strict_json_loads(path.read_bytes(), label=str(path.relative_to(ROOT)))


def _assert_exact_identity(
    path: Path,
    expected_size: int,
    expected_sha256: str,
    *,
    expected_git_blob_sha1: str | None = None,
) -> None:
    if not path.is_file():
        raise AssertionError(f"required file missing: {path.relative_to(ROOT)}")
    payload = path.read_bytes()
    observed_size = len(payload)
    observed_sha256 = sha256_bytes(payload)
    if observed_size != expected_size or observed_sha256 != expected_sha256:
        trailing_lf = payload.endswith(b"\n")
        raise AssertionError(
            f"exact identity mismatch for {path.relative_to(ROOT)}:\n"
            f"- expected size:   {expected_size}\n"
            f"- observed size:   {observed_size}\n"
            f"- expected sha256: {expected_sha256}\n"
            f"- observed sha256: {observed_sha256}\n"
            f"- observed trailing LF: {trailing_lf}"
        )
    if expected_git_blob_sha1 is not None:
        observed_blob = git_blob_sha1(payload)
        assert observed_blob == expected_git_blob_sha1, (
            f"Git blob identity mismatch for {path.relative_to(ROOT)}: "
            f"expected {expected_git_blob_sha1}, observed {observed_blob}"
        )


def _iter_keys(value: Any, *, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}"
            yield current, key
            yield from _iter_keys(child, path=current)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_keys(child, path=f"{path}[{index}]")


def _assert_safe_relative_posix_path(value: str) -> None:
    assert value
    assert value.encode("ascii", errors="strict").decode("ascii") == value
    assert "\\" not in value
    assert "\x00" not in value
    assert not value.startswith("/")
    path = PurePosixPath(value)
    assert not path.is_absolute()
    assert all(part not in {"", ".", ".."} for part in path.parts)
    assert not value.endswith("/")


def _schema_errors(
    validator: jsonschema.Draft202012Validator,
    value: Mapping[str, Any],
) -> list[jsonschema.ValidationError]:
    return sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )


def _mutate_missing_member(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"].pop()


def _mutate_extra_member(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"].append(
        copy.deepcopy(value["capsule_layout"]["payload_members"][-1])
    )


def _mutate_duplicate_member_path(value: dict[str, Any]) -> None:
    layout = value["capsule_layout"]
    layout["member_order"][2] = layout["member_order"][1]


def _mutate_wrong_member_order(value: dict[str, Any]) -> None:
    order = value["capsule_layout"]["member_order"]
    order[1], order[2] = order[2], order[1]


def _mutate_absolute_member_path(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"][0]["capsule_path"] = (
        "/artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger"
    )


def _mutate_parent_traversal(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"][0]["capsule_path"] = (
        "../artifact/pulsemech_device_transition_ledger_reference_v0.pulseledger"
    )


def _mutate_directory_member(value: dict[str, Any]) -> None:
    value["capsule_layout"]["manifest_member"]["path"] = "manifest/"


def _mutate_unsupported_compression(value: dict[str, Any]) -> None:
    value["archive_profile"]["compression_method"] = "ZIP_DEFLATED"


def _mutate_non_fixed_timestamp(value: dict[str, Any]) -> None:
    value["archive_profile"]["member_timestamp"][-1] = 1


def _mutate_non_empty_extra_field(value: dict[str, Any]) -> None:
    value["archive_profile"]["extra_fields"] = "present"


def _mutate_non_empty_archive_comment(value: dict[str, Any]) -> None:
    value["archive_profile"]["archive_comment"] = "present"


def _mutate_source_size_mismatch(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"][0]["size_bytes"] += 1


def _mutate_source_sha256_mismatch(value: dict[str, Any]) -> None:
    value["capsule_layout"]["payload_members"][1]["sha256"] = "0" * 64


def _mutate_wrong_observer_fingerprint(value: dict[str, Any]) -> None:
    value["expected_observer_fingerprint_sha256"] = "0" * 64


def _mutate_wrong_container_image(value: dict[str, Any]) -> None:
    value["reference_environment"]["container_image"] = (
        "docker.io/library/python:3.11.9-slim-bookworm@sha256:" + "0" * 64
    )


def _mutate_wrong_architecture(value: dict[str, Any]) -> None:
    value["reference_environment"]["operating_system"]["architecture"] = (
        "aarch64"
    )


def _mutate_wrong_os_distribution(value: dict[str, Any]) -> None:
    value["reference_environment"]["operating_system"]["distribution"] = (
        "alpine"
    )


def _mutate_wrong_os_version(value: dict[str, Any]) -> None:
    value["reference_environment"]["operating_system"]["version"] = (
        "bookworm"
    )


def _mutate_wrong_python_version(value: dict[str, Any]) -> None:
    value["reference_environment"]["python"]["version"] = "3.99.99"


def _mutate_volatile_manifest_field(value: dict[str, Any]) -> None:
    value["generated_unix_ns"] = 0


def _mutate_manifest_self_hash(value: dict[str, Any]) -> None:
    value["manifest_sha256"] = "0" * 64


def _mutate_final_capsule_hash_inside_manifest(value: dict[str, Any]) -> None:
    value["capsule_sha256"] = "0" * 64


def _mutate_wrong_mutation_target(value: dict[str, Any]) -> None:
    value["negative_reproduction_contract"]["target_inner_member_path"] = (
        "signatures/checkpoint-signature-v0.json"
    )


def _mutate_wrong_failed_check_expectation(value: dict[str, Any]) -> None:
    value["negative_reproduction_contract"]["expected_failed_check_ids"] = [
        "zip_crc32_valid"
    ]


def _mutate_authority_effect_expansion(value: dict[str, Any]) -> None:
    value["authority_boundary"]["authority_effect"] = "release"


def _mutate_new_verifier_claim(value: dict[str, Any]) -> None:
    value["implementation_boundary"]["new_verifier"] = "introduced"


NEGATIVE_MUTATIONS: tuple[
    tuple[str, Callable[[dict[str, Any]], None]], ...
] = (
    ("missing_member", _mutate_missing_member),
    ("extra_member", _mutate_extra_member),
    ("duplicate_member_path", _mutate_duplicate_member_path),
    ("wrong_member_order", _mutate_wrong_member_order),
    ("absolute_member_path", _mutate_absolute_member_path),
    ("parent_traversal", _mutate_parent_traversal),
    ("directory_member", _mutate_directory_member),
    ("unsupported_compression", _mutate_unsupported_compression),
    ("non_fixed_timestamp", _mutate_non_fixed_timestamp),
    ("non_empty_extra_field", _mutate_non_empty_extra_field),
    ("non_empty_archive_comment", _mutate_non_empty_archive_comment),
    ("source_size_mismatch", _mutate_source_size_mismatch),
    ("source_sha256_mismatch", _mutate_source_sha256_mismatch),
    ("wrong_observer_fingerprint", _mutate_wrong_observer_fingerprint),
    ("wrong_container_image", _mutate_wrong_container_image),
    ("wrong_architecture", _mutate_wrong_architecture),
    ("wrong_os_distribution", _mutate_wrong_os_distribution),
    ("wrong_os_version", _mutate_wrong_os_version),
    ("wrong_python_version", _mutate_wrong_python_version),
    ("volatile_manifest_field", _mutate_volatile_manifest_field),
    ("manifest_self_hash", _mutate_manifest_self_hash),
    (
        "final_capsule_hash_inside_manifest",
        _mutate_final_capsule_hash_inside_manifest,
    ),
    ("wrong_mutation_target", _mutate_wrong_mutation_target),
    (
        "wrong_failed_check_expectation",
        _mutate_wrong_failed_check_expectation,
    ),
    ("authority_effect_expansion", _mutate_authority_effect_expansion),
    ("new_verifier_claim", _mutate_new_verifier_claim),
)


def test_schema_contract_and_manifest_exact_identities() -> None:
    _assert_exact_identity(
        SCHEMA_PATH,
        EXPECTED_SCHEMA_IDENTITY[0],
        EXPECTED_SCHEMA_IDENTITY[1],
        expected_git_blob_sha1=EXPECTED_SCHEMA_IDENTITY[2],
    )
    _assert_exact_identity(
        CONTRACT_PATH,
        EXPECTED_CONTRACT_IDENTITY[0],
        EXPECTED_CONTRACT_IDENTITY[1],
        expected_git_blob_sha1=EXPECTED_CONTRACT_IDENTITY[2],
    )
    _assert_exact_identity(
        REFERENCE_MANIFEST_PATH,
        EXPECTED_MANIFEST_IDENTITY[0],
        EXPECTED_MANIFEST_IDENTITY[1],
        expected_git_blob_sha1=EXPECTED_MANIFEST_IDENTITY[2],
    )


def test_protected_preexisting_source_identities() -> None:
    _assert_exact_identity(
        CANONICALIZATION_PATH,
        EXPECTED_CANONICALIZATION_IDENTITY[0],
        EXPECTED_CANONICALIZATION_IDENTITY[1],
    )
    _assert_exact_identity(
        REFERENCE_LEDGER_PATH,
        EXPECTED_LEDGER_IDENTITY[0],
        EXPECTED_LEDGER_IDENTITY[1],
    )
    _assert_exact_identity(
        VERIFIER_PATH,
        EXPECTED_VERIFIER_IDENTITY[0],
        EXPECTED_VERIFIER_IDENTITY[1],
    )
    _assert_exact_identity(
        REFERENCE_REPORT_PATH,
        EXPECTED_REPORT_IDENTITY[0],
        EXPECTED_REPORT_IDENTITY[1],
    )


def test_schema_is_valid_draft_2020_12_and_uses_only_internal_refs() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)

    def walk(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "$ref":
                    assert isinstance(child, str)
                    yield child
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    refs = list(walk(schema))
    assert refs
    assert all(ref.startswith("#/") for ref in refs)


def test_contract_is_strict_and_declares_exact_regression_surface() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    assert contract["work_order_binding"] == {
        "issue": 2850,
        "issue_role": "three_pr_reproduction_capsule_work_order",
        "repository": "HKati/pulse-release-gates-0.1",
    }
    assert contract["schema_binding"] == {
        "byte_identity": "exact_file_bytes",
        "path": (
            "schemas/"
            "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
        ),
        "sha256": EXPECTED_SCHEMA_IDENTITY[1],
        "size_bytes": EXPECTED_SCHEMA_IDENTITY[0],
    }
    canonical_contract = contract["canonical_manifest_contract"]
    assert canonical_contract["stored_bytes"] == (
        "must_equal_canonical_reserialization"
    )
    assert canonical_contract["trailing_newline"] is False
    assert canonical_contract["manifest_self_hash"] == "forbidden"
    assert canonical_contract["manifest_self_size"] == "forbidden"
    assert canonical_contract["final_capsule_sha256_inside_manifest"] == (
        "forbidden"
    )
    assert canonical_contract["final_capsule_size_inside_manifest"] == (
        "forbidden"
    )
    assert canonical_contract["manifest_identity_location"] == (
        "external_reproduction_result"
    )
    assert canonical_contract["capsule_final_identity_location"] == (
        "external_reproduction_result"
    )

    regression = contract["regression_contract"]
    assert tuple(regression["positive_requirements"]) == EXPECTED_POSITIVE_REQUIREMENTS
    assert tuple(regression["negative_cases"]) == EXPECTED_NEGATIVE_CASES
    assert tuple(name for name, _ in NEGATIVE_MUTATIONS) == EXPECTED_NEGATIVE_CASES
    assert regression["tools_test_manifest_registration"] == "exactly_once"


def test_canonical_manifest_is_strict_and_exactly_canonical() -> None:
    payload = REFERENCE_MANIFEST_PATH.read_bytes()
    manifest = strict_json_loads(payload, label=str(REFERENCE_MANIFEST_PATH))
    expected = canonical_json_bytes(manifest)
    if payload != expected:
        trailing_lf = payload.endswith(b"\n")
        raise AssertionError(
            "canonical manifest stored bytes differ from Device Canonical JSON "
            "reserialization:\n"
            f"- stored size:       {len(payload)}\n"
            f"- canonical size:    {len(expected)}\n"
            f"- stored sha256:     {sha256_bytes(payload)}\n"
            f"- canonical sha256:  {sha256_bytes(expected)}\n"
            f"- stored trailing LF: {trailing_lf}"
        )
    assert not payload.endswith(b"\n")
    assert b"\r" not in payload


def test_canonical_manifest_validates_against_schema() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    errors = _schema_errors(validator, manifest)
    assert not errors, "\n".join(
        f"{list(error.absolute_path)}: {error.message}" for error in errors
    )


def test_manifest_is_exact_contract_projection() -> None:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = strict_json_loads(contract_bytes, label=str(CONTRACT_PATH))
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)

    projection = contract["manifest_projection"]
    expected: dict[str, Any] = copy.deepcopy(projection["literal_fields"])
    for section in projection["copied_sections"]:
        expected[section] = copy.deepcopy(contract[section])
    expected["capsule_contract_binding"] = {
        "byte_identity": "exact_file_bytes",
        "path": "contracts/pulsemech_device_ledger_reproduction_capsule_v0.json",
        "sha256": sha256_bytes(contract_bytes),
        "size_bytes": len(contract_bytes),
    }

    assert manifest == expected


def test_exact_layout_paths_and_payload_bindings() -> None:
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    layout = manifest["capsule_layout"]

    assert layout["archive_filename"] == (
        "pulsemech_device_ledger_reproduction_capsule_v0.zip"
    )
    assert layout["archive_format"] == "zip"
    assert layout["capsule_member_count"] == 4
    assert layout["payload_member_count"] == 3
    assert tuple(layout["member_order"]) == EXPECTED_MEMBER_ORDER
    assert len(set(layout["member_order"])) == 4

    manifest_member = layout["manifest_member"]
    assert manifest_member == {
        "archive_ordinal": 1,
        "byte_identity_location": "outside_manifest",
        "media_type": "application/json",
        "path": EXPECTED_MEMBER_ORDER[0],
        "role": "capsule_manifest",
        "self_inventory": "excluded_to_avoid_circularity",
    }

    payload_members = layout["payload_members"]
    assert [member["archive_ordinal"] for member in payload_members] == [2, 3, 4]
    assert [member["capsule_path"] for member in payload_members] == list(
        EXPECTED_MEMBER_ORDER[1:]
    )
    assert [member["role"] for member in payload_members] == [
        "canonical_pulseledger",
        "standalone_verifier",
        "canonical_expected_positive_report",
    ]

    for member in payload_members:
        _assert_safe_relative_posix_path(member["capsule_path"])
        _assert_safe_relative_posix_path(member["source_path"])
        source = ROOT / member["source_path"]
        _assert_exact_identity(
            source,
            member["size_bytes"],
            member["sha256"],
        )


def test_bindings_are_exact_and_identity_graph_is_acyclic() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)

    assert manifest["schema_binding"] == {
        "byte_identity": "exact_file_bytes",
        "path": (
            "schemas/"
            "pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json"
        ),
        "sha256": EXPECTED_SCHEMA_IDENTITY[1],
        "size_bytes": EXPECTED_SCHEMA_IDENTITY[0],
    }
    assert manifest["capsule_contract_binding"] == {
        "byte_identity": "exact_file_bytes",
        "path": "contracts/pulsemech_device_ledger_reproduction_capsule_v0.json",
        "sha256": EXPECTED_CONTRACT_IDENTITY[1],
        "size_bytes": EXPECTED_CONTRACT_IDENTITY[0],
    }
    assert manifest["canonicalization_binding"] == {
        "byte_identity": "exact_file_bytes",
        "path": "contracts/pulsemech_device_canonical_json_v0.json",
        "sha256": EXPECTED_CANONICALIZATION_IDENTITY[1],
        "size_bytes": EXPECTED_CANONICALIZATION_IDENTITY[0],
    }

    graph = contract["identity_graph"]
    order = graph["construction_order"]
    assert order == [
        "manifest_schema",
        "normative_capsule_contract",
        "canonical_manifest",
        "reproduction_capsule",
        "external_reproduction_result",
    ]
    positions = {name: index for index, name in enumerate(order)}
    for binding in graph["required_bindings"]:
        assert positions[binding["from"]] > positions[binding["to"]]
    assert len(order) == len(set(order))

    observed_keys = {key for _, key in _iter_keys(manifest)}
    assert observed_keys.isdisjoint(FORBIDDEN_MANIFEST_KEYS)
    assert graph["forbidden_bindings"] == [
        "contract_self_hash",
        "contract_self_size",
        "manifest_self_hash",
        "manifest_self_size",
        "manifest_to_final_capsule_hash",
        "manifest_to_final_capsule_size",
        "manifest_to_containing_git_commit",
    ]


def test_archive_profile_is_fully_fixed() -> None:
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    profile = manifest["archive_profile"]

    assert profile == {
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


def test_reference_environment_is_exact_and_non_networked() -> None:
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    environment = manifest["reference_environment"]

    assert environment["container_image"] == EXPECTED_CONTAINER_IMAGE
    assert re.fullmatch(
        r"[A-Za-z0-9._/-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}",
        environment["container_image"],
    )
    assert environment["operating_system"] == {
        "architecture": "x86_64",
        "distribution": "debian",
        "version": "bookworm-slim",
    }
    assert environment["python"] == {
        "implementation": "CPython",
        "unicode_data_version": "14.0.0",
        "version": "3.11.9",
    }
    assert environment["archive_implementation"] == {
        "boundary": "cpython_standard_library_bound_to_exact_python_micro_version",
        "module": "zipfile",
    }
    assert environment["environment_variables"] == {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    }
    assert environment["dependency_policy"] == "python_standard_library_only"
    assert environment["network_access"] == "forbidden"
    assert environment["runtime_downloads"] == "forbidden"
    assert environment["working_directory_policy"] == "repository_root"
    assert environment["temporary_directory_policy"] == (
        "isolated_per_construction_outside_protected_sources"
    )


def test_positive_repeated_and_negative_contracts_are_exact() -> None:
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)

    positive = manifest["positive_reproduction_contract"]
    assert positive == {
        "artifact_capsule_path": EXPECTED_MEMBER_ORDER[1],
        "expected_check_count": 49,
        "expected_checkpoint_signature_status": "verified",
        "expected_exit_status": 0,
        "expected_failed_check_ids": [],
        "expected_failure_stage": None,
        "expected_ok": True,
        "expected_package_signature_status": "verified",
        "expected_producer_code_imported": False,
        "expected_report_capsule_path": EXPECTED_MEMBER_ORDER[3],
        "expected_report_comparison": "exact_stdout_bytes",
        "expected_report_sha256": EXPECTED_REPORT_IDENTITY[1],
        "expected_report_size_bytes": EXPECTED_REPORT_IDENTITY[0],
        "expected_result": "verified_with_declared_unavailability",
        "expected_stderr": "empty",
        "expected_verifier_implementation_relation": (
            "separate_from_producer_code"
        ),
        "producer_verdict_trusted": False,
        "verifier_capsule_path": EXPECTED_MEMBER_ORDER[2],
        "verifier_execution_relation": "separate_process",
    }

    repeated = manifest["repeated_construction_contract"]
    assert repeated == {
        "capsule_a_reused_by_capsule_b": False,
        "capsule_byte_relation": "required_equal",
        "capsule_final_identity_location": "external_reproduction_result",
        "capsule_member_byte_relation": "required_equal",
        "capsule_member_order_relation": "required_equal",
        "capsule_sha256_relation": "required_equal",
        "capsule_size_relation": "required_equal",
        "construction_count": 2,
        "positive_report_byte_relation": "both_equal_canonical_expected_report",
        "workspace_relation": "isolated_no_reuse",
    }

    negative = manifest["negative_reproduction_contract"]
    assert negative["target_capsule_member_path"] == EXPECTED_MEMBER_ORDER[1]
    assert negative["target_inner_member_path"] == (
        "signatures/package-signature-v0.json"
    )
    assert negative["field"] == "signature_base64"
    assert negative["mutation_class"] == "replace_first_character"
    assert negative["original_character"] == "O"
    assert negative["replacement_character"] == "P"
    assert negative["canonical_reference_artifact_mutated"] is False
    assert negative["recompute_local_header_crc32"] is True
    assert negative["recompute_central_directory_crc32"] is True
    assert negative["expected_exit_status"] == 2
    assert negative["expected_ok"] is False
    assert negative["expected_result"] == "rejected"
    assert negative["expected_failure_stage"] == "package_signature"
    assert negative["expected_failed_check_ids"] == ["package_signature_valid"]
    assert negative["expected_error"] == {
        "check_id": "package_signature_valid",
        "error_code": "signature_verification_failed",
        "member_path": "signatures/package-signature-v0.json",
    }
    assert negative["required_preceding_checks"] == [
        {"check_id": "zip_crc32_valid", "expected_result": "passed"},
        {
            "check_id": "package_signature_document_valid",
            "expected_result": "passed",
        },
        {
            "check_id": "package_signature_subject_valid",
            "expected_result": "passed",
        },
    ]


def test_existing_positive_report_matches_declared_expectations() -> None:
    report = _read_strict_object(REFERENCE_REPORT_PATH)
    assert report["ok"] is True
    assert report["result"] == "verified_with_declared_unavailability"
    assert report["failure_stage"] is None
    assert report["failed_check_ids"] == []
    assert len(report["checks"]) == 49
    assert set(report["checks"].values()) == {"passed"}
    assert report["signature_verification"]["checkpoint"]["signature_status"] == (
        "verified"
    )
    assert report["signature_verification"]["package"]["signature_status"] == (
        "verified"
    )
    assert report["observer_verification"]["reconstructed_fingerprint_sha256"] == (
        EXPECTED_OBSERVER_FINGERPRINT
    )
    assert report["reproduction_context"]["verifier_implementation_relation"] == (
        "separate_from_producer_code"
    )
    assert report["authority_boundary"]["authority_effect"] == "none"


def test_payload_source_and_non_authority_boundaries_are_exact() -> None:
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    assert manifest["payload_source"] == {
        "commit_sha": EXPECTED_PAYLOAD_SOURCE_COMMIT,
        "repository": "HKati/pulse-release-gates-0.1",
        "source_role": "canonical_preexisting_input_baseline",
    }
    assert manifest["record_status"] == "synthetic_reference"
    assert manifest["expected_observer_fingerprint_sha256"] == (
        EXPECTED_OBSERVER_FINGERPRINT
    )
    assert manifest["implementation_boundary"] == {
        "existing_verifier_modification": "forbidden",
        "new_verifier": "none",
        "producer_verdict_trusted": False,
        "runner_role": "orchestration_only",
        "verification_semantics_change": "none",
        "verifier_execution": "separate_process",
        "verifier_import_by_runner": "forbidden",
    }
    assert manifest["claim_boundary"] == {
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
    assert manifest["authority_boundary"] == {
        "authority_effect": "none",
        "capsule_is_release_authority": False,
        "changes_release_authority": False,
        "creates_device_control_authority": False,
        "creates_gate_result": False,
        "creates_release_decision": False,
        "external_operator_approval_required": False,
        "reproduction_result_is_release_authority": False,
    }


@pytest.mark.parametrize(
    ("case_name", "mutator"),
    NEGATIVE_MUTATIONS,
    ids=[name for name, _ in NEGATIVE_MUTATIONS],
)
def test_schema_rejects_declared_negative_cases(
    case_name: str,
    mutator: Callable[[dict[str, Any]], None],
) -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    manifest = _read_strict_object(REFERENCE_MANIFEST_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    mutated = copy.deepcopy(manifest)
    mutator(mutated)
    errors = _schema_errors(validator, mutated)
    assert errors, f"schema accepted declared negative case: {case_name}"
