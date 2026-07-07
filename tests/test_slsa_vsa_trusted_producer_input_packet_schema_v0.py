#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "schemas" / "slsa_vsa_trusted_producer_input_packet_v0.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "slsa" / "slsa_vsa_trusted_producer_input_packet_example_v0.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema() -> dict[str, Any]:
    return _load_json(SCHEMA_PATH)


def _packet() -> dict[str, Any]:
    return _load_json(EXAMPLE_PATH)


def _validator() -> jsonschema.Draft202012Validator:
    schema = _schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def _validate(instance: dict[str, Any]) -> None:
    _validator().validate(instance)


def _validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in _validator().iter_errors(instance)
    ]


def test_schema_and_example_exist() -> None:
    assert SCHEMA_PATH.exists()
    assert EXAMPLE_PATH.exists()


def test_example_validates() -> None:
    _validate(_packet())


def test_schema_version_is_locked() -> None:
    packet = _packet()
    packet["schema_version"] = "wrong"

    assert _validation_errors(packet)


def test_packet_type_is_locked() -> None:
    packet = _packet()
    packet["packet_type"] = "wrong"

    assert _validation_errors(packet)


def test_created_utc_requires_date_time() -> None:
    packet = _packet()
    packet["created_utc"] = "unknown"

    assert _validation_errors(packet)


def test_recorded_signal_mode_is_locked() -> None:
    packet = _packet()
    packet["recorded_signal_mode"] = "cryptographic_signature_verified"

    assert _validation_errors(packet)


def test_candidate_set_is_locked() -> None:
    packet = _packet()
    packet["candidate_set"] = "slsa_vsa_release_required_candidate"

    assert _validation_errors(packet)


def test_producer_identity_fields_are_required() -> None:
    required_fields = [
        "producer_id",
        "producer_name",
        "producer_version",
        "producer_source",
        "ci_workflow_or_job_identity",
    ]

    for field in required_fields:
        packet = _packet()
        del packet["producer_identity"][field]

        assert _validation_errors(packet), field


def test_run_binding_fields_are_required() -> None:
    required_fields = [
        "current_run_id",
        "current_run_number",
        "current_run_attempt",
        "current_run_key",
        "workflow_name",
        "job_name",
        "commit_sha",
        "release_candidate_id",
    ]

    for field in required_fields:
        packet = _packet()
        del packet["run_binding"][field]

        assert _validation_errors(packet), field


def test_current_run_key_has_expected_shape() -> None:
    packet = _packet()
    packet["run_binding"]["current_run_key"] = "1234567890"

    assert _validation_errors(packet)


def test_commit_sha_must_be_40_character_hex() -> None:
    bad_values = [
        "a" * 39,
        "a" * 41,
        "g" * 40,
        "",
    ]

    for value in bad_values:
        packet = _packet()
        packet["run_binding"]["commit_sha"] = value

        assert _validation_errors(packet), value


def test_artifact_sha_fields_must_be_64_character_hex() -> None:
    fields = [
        "subject_sha256",
        "artifact_digest_sha256",
    ]

    bad_values = [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "",
    ]

    for field in fields:
        for value in bad_values:
            packet = _packet()
            packet["artifact_binding"][field] = value

            assert _validation_errors(packet), f"{field}={value!r}"


def test_artifact_binding_fields_are_required() -> None:
    required_fields = [
        "subject_name",
        "subject_sha256",
        "resource_uri",
        "release_candidate_id",
        "artifact_digest_sha256",
    ]

    for field in required_fields:
        packet = _packet()
        del packet["artifact_binding"][field]

        assert _validation_errors(packet), field


def test_policy_binding_fields_are_required() -> None:
    required_fields = [
        "expected_policy_id",
        "expected_policy_uri",
        "expected_policy_sha256",
    ]

    for field in required_fields:
        packet = _packet()
        del packet["policy_binding"][field]

        assert _validation_errors(packet), field


def test_policy_digest_must_be_64_character_hex() -> None:
    bad_values = [
        "b" * 63,
        "b" * 65,
        "g" * 64,
        "",
    ]

    for value in bad_values:
        packet = _packet()
        packet["policy_binding"]["expected_policy_sha256"] = value

        assert _validation_errors(packet), value


def test_policy_uri_only_packet_is_rejected() -> None:
    packet = _packet()
    del packet["policy_binding"]["expected_policy_sha256"]

    assert _validation_errors(packet)


def test_verifier_identity_is_required() -> None:
    packet = _packet()
    del packet["verifier_binding"]["expected_verifier_id"]

    assert _validation_errors(packet)


def test_expected_verified_level_is_required() -> None:
    packet = _packet()
    del packet["expected_verified_level"]

    assert _validation_errors(packet)


def test_expected_time_verified_requires_date_time() -> None:
    packet = _packet()
    packet["freshness"]["expected_time_verified"] = "unknown"

    assert _validation_errors(packet)


def test_freshness_fields_are_required() -> None:
    required_fields = [
        "expected_time_verified",
        "freshness_epoch",
    ]

    for field in required_fields:
        packet = _packet()
        del packet["freshness"][field]

        assert _validation_errors(packet), field


def test_extra_top_level_fields_are_rejected() -> None:
    packet = _packet()
    packet["extra"] = "not allowed"

    assert _validation_errors(packet)


def test_release_decision_fields_are_rejected() -> None:
    forbidden_fields = [
        "status",
        "status_gates",
        "required",
        "core_required",
        "release_required",
        "prod_required",
        "stage_required",
        "blocking",
        "release_blocking",
        "gate_materialization",
        "release_authority",
        "producer_decision",
        "ok",
        "failed_checks",
    ]

    for field in forbidden_fields:
        packet = _packet()
        packet[field] = True

        assert _validation_errors(packet), field


def test_nested_extra_properties_are_rejected() -> None:
    sections = [
        "producer_identity",
        "run_binding",
        "artifact_binding",
        "policy_binding",
        "verifier_binding",
        "freshness",
    ]

    for section in sections:
        packet = _packet()
        packet[section]["extra"] = "not allowed"

        assert _validation_errors(packet), section


def check_slsa_vsa_trusted_producer_input_packet_schema_v0() -> None:
    test_schema_and_example_exist()
    test_example_validates()
    test_schema_version_is_locked()
    test_packet_type_is_locked()
    test_created_utc_requires_date_time()
    test_recorded_signal_mode_is_locked()
    test_candidate_set_is_locked()
    test_producer_identity_fields_are_required()
    test_run_binding_fields_are_required()
    test_current_run_key_has_expected_shape()
    test_commit_sha_must_be_40_character_hex()
    test_artifact_sha_fields_must_be_64_character_hex()
    test_artifact_binding_fields_are_required()
    test_policy_binding_fields_are_required()
    test_policy_digest_must_be_64_character_hex()
    test_policy_uri_only_packet_is_rejected()
    test_verifier_identity_is_required()
    test_expected_verified_level_is_required()
    test_expected_time_verified_requires_date_time()
    test_freshness_fields_are_required()
    test_extra_top_level_fields_are_rejected()
    test_release_decision_fields_are_rejected()
    test_nested_extra_properties_are_rejected()


def test_slsa_vsa_trusted_producer_input_packet_schema_v0() -> None:
    check_slsa_vsa_trusted_producer_input_packet_schema_v0()


if __name__ == "__main__":
    check_slsa_vsa_trusted_producer_input_packet_schema_v0()
    print("OK: slsa_vsa_trusted_producer_input_packet_schema_v0 smoke passed")
