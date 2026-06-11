#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "release_evidence_verifier_report_v0.schema.json"
FAILED_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "release_evidence_verifier_report_v0.failed.example.json"
)

HEX40 = "a" * 40
HEX64 = "b" * 64
RUN_KEY = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verified_artifact() -> dict[str, Any]:
    return {
        "path": "artifacts/detectors/detector_report.json",
        "sha256": HEX64,
        "schema_version": "detector_report_v0",
        "verified": True,
    }


def _relation_binding() -> dict[str, Any]:
    return {
        "relation_id": "detector_report_to_subject_commit",
        "binding_type": "artifact_to_subject",
        "source": "artifacts/detectors/detector_report.json",
        "target": "subject.commit_sha",
        "verified": True,
        "evidence": [
            _verified_artifact()
        ],
        "failure_reason": None,
    }


def _minimal_verified_report() -> dict[str, Any]:
    return {
        "schema_version": "release_evidence_verifier_report_v0",
        "created_utc": "2026-01-01T00:00:00Z",
        "verifier_id": "pulse_release_evidence_verifier_v0",
        "verifier_version": "0.1.0",
        "verifier_decision": "VERIFIED",
        "run_identity": {
            "run_mode": "prod",
            "run_key": RUN_KEY,
            "git_sha": HEX40,
        },
        "subject": {
            "repository": "HKati/pulse-release-gates-0.1",
            "commit_sha": HEX40,
            "release_candidate": "candidate-v0",
        },
        "policy_binding": {
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_sha256": HEX64,
            "policy_set": "required+release_required",
        },
        "registry_binding": {
            "registry_path": "pulse_gate_registry_v0.yml",
            "registry_sha256": HEX64,
        },
        "evidence_inputs": [
            {
                "kind": "detector_evidence",
                "path": "artifacts/detectors/detector_report.json",
                "sha256": HEX64,
                "schema_version": "detector_report_v0",
                "subject_binding": {
                    "git_sha": HEX40,
                    "run_key": RUN_KEY,
                },
                "provenance": {
                    "producer": "unit-test"
                },
            }
        ],
        "verified_artifacts": [
            _verified_artifact()
        ],
        "relation_bindings": [
            _relation_binding()
        ],
        "gate_materialization": {
            "detectors_materialized_ok": {
                "value": True,
                "source": "release_evidence_verifier_report_v0",
                "verified": True,
                "evidence_artifacts": [
                    _verified_artifact()
                ],
                "relation_bindings": [
                    "detector_report_to_subject_commit"
                ],
                "policy_relation": "release_required",
            }
        },
        "failed_checks": [],
        "warnings": [],
    }


def _validate(instance: dict[str, Any]) -> None:
    schema = _load_json(SCHEMA_PATH)

    if jsonschema is not None:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)
        return

    for key in schema["required"]:
        assert key in instance
    assert instance["schema_version"] == "release_evidence_verifier_report_v0"
    assert instance["verifier_decision"] in {"VERIFIED", "FAILED"}

    if instance["verifier_decision"] == "FAILED":
        assert instance["failed_checks"]
        assert instance["gate_materialization"] == {}

    if instance["verifier_decision"] == "VERIFIED":
        assert instance["failed_checks"] == []
        assert instance["gate_materialization"]
        assert instance["verified_artifacts"]
        assert instance["relation_bindings"]

        for relation in instance["relation_bindings"]:
            assert relation["verified"] is True
            assert relation["evidence"]
            assert relation.get("failure_reason") is None

        for gate in instance["gate_materialization"].values():
            assert gate["source"] == "release_evidence_verifier_report_v0"
            assert gate["verified"] is True
            assert gate["evidence_artifacts"]
            assert gate["relation_bindings"]


def _validation_errors(instance: dict[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA_PATH)

    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(schema)
        return [error.message for error in validator.iter_errors(instance)]

    try:
        _validate(instance)
    except AssertionError as exc:
        return [str(exc)]
    return []


def test_release_evidence_verifier_schema_and_failed_example_exist() -> None:
    assert SCHEMA_PATH.exists()
    assert FAILED_EXAMPLE_PATH.exists()


def test_failed_example_validates() -> None:
    _validate(_load_json(FAILED_EXAMPLE_PATH))


def test_minimal_verified_report_validates() -> None:
    _validate(_minimal_verified_report())


def test_release_authority_words_are_not_verifier_decisions() -> None:
    report = _minimal_verified_report()
    report["verifier_decision"] = "PASS"

    errors = _validation_errors(report)

    assert errors


def test_allow_is_not_a_verifier_decision() -> None:
    report = _minimal_verified_report()
    report["verifier_decision"] = "ALLOW"

    errors = _validation_errors(report)

    assert errors


def test_prod_pass_is_not_a_verifier_decision() -> None:
    report = _minimal_verified_report()
    report["verifier_decision"] = "PROD-PASS"

    errors = _validation_errors(report)

    assert errors


def test_failed_report_requires_failed_checks() -> None:
    report = _load_json(FAILED_EXAMPLE_PATH)
    report["failed_checks"] = []

    errors = _validation_errors(report)

    assert errors


def test_verified_report_requires_gate_materialization() -> None:
    report = _minimal_verified_report()
    report["gate_materialization"] = {}

    errors = _validation_errors(report)

    assert errors


def test_verified_report_requires_relation_bindings() -> None:
    report = _minimal_verified_report()
    report["relation_bindings"] = []

    errors = _validation_errors(report)

    assert errors


def test_verified_relation_binding_must_be_verified() -> None:
    report = _minimal_verified_report()
    report["relation_bindings"][0]["verified"] = False

    errors = _validation_errors(report)

    assert errors


def test_verified_relation_binding_requires_evidence() -> None:
    report = _minimal_verified_report()
    report["relation_bindings"][0]["evidence"] = []

    errors = _validation_errors(report)

    assert errors


def test_verified_relation_binding_failure_reason_must_be_null() -> None:
    report = _minimal_verified_report()
    report["relation_bindings"][0]["failure_reason"] = "stale relation"

    errors = _validation_errors(report)

    assert errors


def test_gate_materialization_source_is_verifier_report_only() -> None:
    report = _minimal_verified_report()
    report["gate_materialization"]["detectors_materialized_ok"]["source"] = (
        "detector_materialization_v0.json"
    )

    errors = _validation_errors(report)

    assert errors


def test_gate_materialization_requires_verified_artifact_binding() -> None:
    report = _minimal_verified_report()
    report["gate_materialization"]["detectors_materialized_ok"][
        "evidence_artifacts"
    ] = []

    errors = _validation_errors(report)

    assert errors


def test_gate_materialization_requires_relation_binding_ids() -> None:
    report = _minimal_verified_report()
    report["gate_materialization"]["detectors_materialized_ok"][
        "relation_bindings"
    ] = []

    errors = _validation_errors(report)

    assert errors


def test_verified_artifact_must_be_marked_verified() -> None:
    report = _minimal_verified_report()
    report["verified_artifacts"][0]["verified"] = False

    errors = _validation_errors(report)

    assert errors


def _failed_report_with_candidate_schema_validation(
    status: str = "failed",
    duplicate_key_status: str | None = None,
) -> dict[str, Any]:
    report = _minimal_verified_report()

    report["verifier_decision"] = "FAILED"
    report["verified_artifacts"] = []
    report["relation_bindings"] = []
    report["gate_materialization"] = {}
    report["failed_checks"] = [
        "candidate schema validation draft is diagnostic-only"
    ]

    candidate_schema_validation: dict[str, Any] = {
        "status": status,
        "schema_path": "schemas/detector_report_v0.schema.json",
        "schema_version": "detector_report_v0",
        "errors": [
            {
                "code": "schema_validation_failed",
                "message": "candidate evidence schema validation is diagnostic-only",
                "instance_path": "/",
                "schema_path": "#",
            }
        ],
    }

    if duplicate_key_status is not None:
        candidate_schema_validation["duplicate_key_validation"] = {
            "status": duplicate_key_status,
            "errors": [
                {
                    "code": "duplicate_key_validation_failed",
                    "message": "duplicate-key validation is diagnostic-only",
                    "instance_path": "/",
                    "schema_path": "#",
                }
            ],
        }

    report["evidence_inputs"][0]["provenance"] = {
        "producer": "unit-test",
        "trusted": False,
        "verification_status": "not_verified",
        "candidate_schema_validation": candidate_schema_validation,
    }

    return report


@pytest.mark.parametrize("status", ["not_run", "unavailable", "failed"])
def test_candidate_schema_validation_draft_accepts_diagnostic_statuses(
    status: str,
) -> None:
    report = _failed_report_with_candidate_schema_validation(status=status)

    _validate(report)


@pytest.mark.parametrize(
    "bad_status",
    [
        "valid",
        "passed",
        "success",
        "schema_valid",
        "verified",
        "trusted",
    ],
)
def test_candidate_schema_validation_draft_rejects_promotion_statuses(
    bad_status: str,
) -> None:
    report = _failed_report_with_candidate_schema_validation(
        status=bad_status,
    )

    errors = _validation_errors(report)

    assert errors


@pytest.mark.parametrize("status", ["not_run", "unavailable", "failed"])
def test_duplicate_key_validation_draft_accepts_diagnostic_statuses(
    status: str,
) -> None:
    report = _failed_report_with_candidate_schema_validation(
        status="failed",
        duplicate_key_status=status,
    )

    _validate(report)


@pytest.mark.parametrize(
    "bad_status",
    [
        "valid",
        "passed",
        "success",
        "schema_valid",
        "verified",
        "trusted",
    ],
)
def test_duplicate_key_validation_draft_rejects_promotion_statuses(
    bad_status: str,
) -> None:
    report = _failed_report_with_candidate_schema_validation(
        status="failed",
        duplicate_key_status=bad_status,
    )

    errors = _validation_errors(report)

    assert errors


def test_candidate_schema_validation_draft_does_not_make_verified_report_valid() -> None:
    report = _failed_report_with_candidate_schema_validation(status="failed")
    report["verifier_decision"] = "VERIFIED"
    report["failed_checks"] = []

    errors = _validation_errors(report)

    assert errors


def test_candidate_schema_validation_draft_keeps_failed_report_non_materialized() -> None:
    report = _failed_report_with_candidate_schema_validation(status="failed")

    _validate(report)

    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}
    assert report["evidence_inputs"][0]["provenance"]["trusted"] is False
    assert (
        report["evidence_inputs"][0]["provenance"]["verification_status"]
        == "not_verified"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
