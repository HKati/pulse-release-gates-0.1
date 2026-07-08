from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("schemas/slsa_vsa_evidence_v0.schema.json")
EXAMPLE_PATH = Path("examples/slsa/slsa_vsa_evidence_example_v0.json")

REQUIRED_PULSE_SIGNALS = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]

EXPECTED_POLICY = {
    "id": "pulse-gate-policy-v0",
    "uri": "https://example.invalid/policies/pulse-slsa-vsa-policy-v0.json",
    "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_example() -> dict[str, Any]:
    return load_json(EXAMPLE_PATH)


def validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in validator().iter_errors(instance)
    ]


def policy_object(example: dict[str, Any]) -> dict[str, Any]:
    return example["vsa"]["predicate"]["policy"]


def subject_digest(example: dict[str, Any]) -> dict[str, Any]:
    return example["vsa"]["subject"][0]["digest"]


def input_attestation_digest(example: dict[str, Any]) -> dict[str, Any]:
    return example["vsa"]["predicate"]["inputAttestations"][0]["digest"]


def check_slsa_vsa_evidence_schema_v0() -> None:
    example = load_example()

    validator().validate(example)

    assert example["schema_version"] == "slsa_vsa_evidence_v0"
    assert example["evidence_type"] == "slsa_vsa"

    vsa = example["vsa"]
    assert vsa["_type"] == "https://in-toto.io/Statement/v1"
    assert vsa["predicateType"] == "https://slsa.dev/verification_summary/v1"

    predicate = vsa["predicate"]
    assert predicate["verificationResult"] == "PASSED"
    assert "SLSA_BUILD_LEVEL_3" in predicate["verifiedLevels"]

    verifier = predicate["verifier"]
    assert verifier["id"] == "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0"
    assert verifier["id"] != "https://github.com/slsa-framework/slsa-verifier"
    assert isinstance(verifier["version"], dict)
    assert verifier["version"]["slsa-verifier"] == "v2.7.0"

    policy = predicate["policy"]
    assert policy["id"] == EXPECTED_POLICY["id"]
    assert policy["uri"] == EXPECTED_POLICY["uri"]
    assert policy["digest"]["sha256"] == EXPECTED_POLICY["sha256"]

    input_attestations = predicate["inputAttestations"]
    assert input_attestations
    for attestation in input_attestations:
        assert "digest" in attestation
        assert "sha256" in attestation["digest"]
        assert isinstance(attestation["digest"]["sha256"], str)
        assert attestation["digest"]["sha256"]

    dependency_levels = predicate["dependencyLevels"]
    assert isinstance(dependency_levels, dict)
    assert dependency_levels
    assert all(isinstance(value, int) for value in dependency_levels.values())
    assert all(value >= 0 for value in dependency_levels.values())

    pulse_signals = example["pulse_signals"]
    for signal in REQUIRED_PULSE_SIGNALS:
        assert signal in pulse_signals
        assert pulse_signals[signal] is True


def test_example_validates() -> None:
    validator().validate(load_example())


def test_policy_identity_is_required() -> None:
    example = load_example()
    del policy_object(example)["id"]

    assert validation_errors(example)


def test_policy_identity_must_be_non_empty() -> None:
    example = load_example()
    policy_object(example)["id"] = ""

    assert validation_errors(example)


def test_policy_uri_is_still_required() -> None:
    example = load_example()
    del policy_object(example)["uri"]

    assert validation_errors(example)


def test_policy_digest_is_still_required() -> None:
    example = load_example()
    del policy_object(example)["digest"]

    assert validation_errors(example)


def test_policy_digest_sha256_is_required() -> None:
    example = load_example()
    del policy_object(example)["digest"]["sha256"]

    assert validation_errors(example)


def test_policy_digest_sha256_must_be_64_character_hex() -> None:
    bad_values = [
        "b" * 63,
        "b" * 65,
        "g" * 64,
        "",
    ]

    for value in bad_values:
        example = load_example()
        policy_object(example)["digest"]["sha256"] = value

        assert validation_errors(example), value


def test_policy_uri_only_evidence_is_rejected() -> None:
    example = load_example()
    policy = policy_object(example)
    policy.clear()
    policy["uri"] = EXPECTED_POLICY["uri"]

    assert validation_errors(example)


def test_policy_identity_without_digest_is_rejected() -> None:
    example = load_example()
    policy = policy_object(example)
    policy.clear()
    policy["id"] = EXPECTED_POLICY["id"]
    policy["uri"] = EXPECTED_POLICY["uri"]

    assert validation_errors(example)


def test_policy_digest_without_identity_is_rejected() -> None:
    example = load_example()
    policy = policy_object(example)
    policy.clear()
    policy["uri"] = EXPECTED_POLICY["uri"]
    policy["digest"] = {
        "sha256": EXPECTED_POLICY["sha256"],
    }

    assert validation_errors(example)


def test_subject_digest_map_remains_algorithm_generic() -> None:
    example = load_example()
    subject_digest(example).clear()
    subject_digest(example)["sha512"] = "nonempty-sha512-placeholder"

    validator().validate(example)


def test_input_attestation_digest_map_remains_algorithm_generic() -> None:
    example = load_example()
    input_attestation_digest(example).clear()
    input_attestation_digest(example)["sha512"] = "nonempty-sha512-placeholder"

    validator().validate(example)


def test_policy_digest_map_requires_sha256_even_if_other_digest_exists() -> None:
    example = load_example()
    policy_digest = policy_object(example)["digest"]
    policy_digest.clear()
    policy_digest["sha512"] = "nonempty-sha512-placeholder"

    assert validation_errors(example)


def test_slsa_vsa_evidence_schema_v0() -> None:
    check_slsa_vsa_evidence_schema_v0()


def check_policy_identity_binding_tests() -> None:
    test_example_validates()
    test_policy_identity_is_required()
    test_policy_identity_must_be_non_empty()
    test_policy_uri_is_still_required()
    test_policy_digest_is_still_required()
    test_policy_digest_sha256_is_required()
    test_policy_digest_sha256_must_be_64_character_hex()
    test_policy_uri_only_evidence_is_rejected()
    test_policy_identity_without_digest_is_rejected()
    test_policy_digest_without_identity_is_rejected()
    test_subject_digest_map_remains_algorithm_generic()
    test_input_attestation_digest_map_remains_algorithm_generic()
    test_policy_digest_map_requires_sha256_even_if_other_digest_exists()


if __name__ == "__main__":
    check_slsa_vsa_evidence_schema_v0()
    check_policy_identity_binding_tests()
    print("OK: slsa_vsa_evidence_v0 schema and example are valid")
