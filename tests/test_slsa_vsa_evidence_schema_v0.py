import json
from pathlib import Path

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
    "slsa_vsa_verified_level_ok"
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_slsa_vsa_evidence_schema_v0() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)

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


def test_slsa_vsa_evidence_schema_v0() -> None:
    check_slsa_vsa_evidence_schema_v0()


if __name__ == "__main__":
    check_slsa_vsa_evidence_schema_v0()
    print("OK: slsa_vsa_evidence_v0 schema and example are valid")
