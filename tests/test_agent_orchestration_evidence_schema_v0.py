from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA = ROOT / "schemas" / "agent_orchestration_evidence_v0.schema.json"
EXAMPLE = (
    ROOT
    / "examples"
    / "agent_orchestration_evidence_v0"
    / "symphony_work_evidence.example.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_validator() -> jsonschema.Draft202012Validator:
    schema = load_json(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def validation_errors(payload: dict) -> list[jsonschema.ValidationError]:
    validator = make_validator()
    return sorted(validator.iter_errors(payload), key=lambda error: list(error.path))


def assert_valid(payload: dict) -> None:
    errors = validation_errors(payload)
    assert not errors, [error.message for error in errors]


def assert_invalid(payload: dict) -> None:
    errors = validation_errors(payload)
    assert errors, "payload unexpectedly validated"


def minimal_valid_payload() -> dict:
    return {
        "schema_version": "agent_orchestration_evidence_v0",
        "source": "symphony",
        "evidence_role": "diagnostic",
        "normative": False,
        "release_authority": False,
        "created_utc": "2026-04-27T00:00:00Z",
        "task": {
            "task_id": "TASK-123"
        },
        "agent_run": {
            "agent_run_id": "agent-run-001",
            "workspace_id": "workspace-001",
            "execution_mode": "isolated",
            "status": "completed"
        },
        "proof_of_work": {
            "proof_of_work_present": True,
            "ci_status": "pass",
            "review_status": "approved"
        },
        "human_review": {
            "human_accepted": True
        },
        "pulse_ingestion": {
            "recommended_fold_in_target": "status.meta.agent_work_evidence",
            "gate_promotion": False,
            "release_decision_claim": "none",
            "authority_boundary": "Agent orchestration evidence is diagnostic by default and carries no release authority unless explicitly promoted by declared gate policy."
        }
    }


def test_agent_orchestration_evidence_schema_and_example_exist() -> None:
    assert SCHEMA.is_file()
    assert EXAMPLE.is_file()


def test_agent_orchestration_evidence_schema_is_valid_json_schema() -> None:
    schema = load_json(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)


def test_symphony_work_evidence_example_validates() -> None:
    payload = load_json(EXAMPLE)
    assert_valid(payload)


def test_minimal_documented_payload_validates() -> None:
    payload = minimal_valid_payload()
    assert_valid(payload)


def test_task_tracker_and_title_are_optional_metadata() -> None:
    payload = minimal_valid_payload()
    payload["task"]["tracker"] = "linear"
    payload["task"]["title"] = "Example task"
    payload["task"]["task_url"] = "https://example.invalid/tasks/TASK-123"

    assert_valid(payload)


def test_reviewer_notes_are_optional_metadata() -> None:
    payload = minimal_valid_payload()
    assert_valid(payload)

    payload["human_review"]["reviewer_notes"] = (
        "Example payload only. Human acceptance records task-level review context, "
        "not PULSE release authority."
    )
    assert_valid(payload)


def test_schema_rejects_normative_agent_evidence() -> None:
    payload = minimal_valid_payload()
    payload["normative"] = True

    assert_invalid(payload)


def test_schema_rejects_release_authority_claim() -> None:
    payload = minimal_valid_payload()
    payload["release_authority"] = True

    assert_invalid(payload)


def test_schema_rejects_gate_promotion() -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["gate_promotion"] = True

    assert_invalid(payload)


def test_schema_rejects_release_decision_claim() -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["release_decision_claim"] = "PASS"

    assert_invalid(payload)


def test_schema_rejects_fold_in_under_gates() -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["recommended_fold_in_target"] = (
        "status.gates.agent_work_evidence"
    )

    assert_invalid(payload)


def test_schema_rejects_non_diagnostic_evidence_role() -> None:
    payload = minimal_valid_payload()
    payload["evidence_role"] = "required"

    assert_invalid(payload)


def test_schema_rejects_missing_required_sections() -> None:
    payload = minimal_valid_payload()
    del payload["proof_of_work"]

    assert_invalid(payload)


def test_schema_rejects_missing_task_id() -> None:
    payload = minimal_valid_payload()
    del payload["task"]["task_id"]

    assert_invalid(payload)


def test_schema_rejects_empty_task_id() -> None:
    payload = minimal_valid_payload()
    payload["task"]["task_id"] = ""

    assert_invalid(payload)


def test_schema_rejects_missing_human_accepted() -> None:
    payload = minimal_valid_payload()
    del payload["human_review"]["human_accepted"]

    assert_invalid(payload)


def test_schema_rejects_unexpected_top_level_properties() -> None:
    payload = minimal_valid_payload()
    payload["unexpected"] = "not allowed"

    assert_invalid(payload)


def test_schema_rejects_unexpected_nested_properties() -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["unexpected"] = "not allowed"

    assert_invalid(payload)


def test_schema_rejects_invalid_ci_status() -> None:
    payload = minimal_valid_payload()
    payload["proof_of_work"]["ci_status"] = "green"

    assert_invalid(payload)


def test_schema_rejects_invalid_review_status() -> None:
    payload = minimal_valid_payload()
    payload["proof_of_work"]["review_status"] = "accepted"

    assert_invalid(payload)


def test_schema_rejects_invalid_agent_run_status() -> None:
    payload = minimal_valid_payload()
    payload["agent_run"]["status"] = "done"

    assert_invalid(payload)


def test_schema_rejects_invalid_execution_mode() -> None:
    payload = minimal_valid_payload()
    payload["agent_run"]["execution_mode"] = "background"

    assert_invalid(payload)


def test_schema_keeps_authority_boundary_fields_fixed() -> None:
    payload = minimal_valid_payload()

    assert payload["evidence_role"] == "diagnostic"
    assert payload["normative"] is False
    assert payload["release_authority"] is False
    assert payload["pulse_ingestion"]["recommended_fold_in_target"] == (
        "status.meta.agent_work_evidence"
    )
    assert payload["pulse_ingestion"]["gate_promotion"] is False
    assert payload["pulse_ingestion"]["release_decision_claim"] == "none"

    assert_valid(payload)


def test_example_payload_can_be_reduced_to_documented_minimal_shape() -> None:
    payload = load_json(EXAMPLE)

    reduced = deepcopy(payload)
    reduced["task"] = {
        "task_id": payload["task"]["task_id"]
    }
    reduced["proof_of_work"] = {
        "proof_of_work_present": payload["proof_of_work"]["proof_of_work_present"],
        "ci_status": payload["proof_of_work"]["ci_status"],
        "review_status": payload["proof_of_work"]["review_status"],
    }
    reduced["human_review"] = {
        "human_accepted": payload["human_review"]["human_accepted"]
    }

    assert_valid(reduced)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
