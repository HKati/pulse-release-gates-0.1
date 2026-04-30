from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_DIR = ROOT / "examples" / "agent_orchestration_evidence_v0"
README = EXAMPLE_DIR / "README.md"
PAYLOAD = EXAMPLE_DIR / "symphony_work_evidence.example.json"
BRIDGE_DOC = ROOT / "docs" / "AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md"


def load_payload() -> dict:
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


def test_agent_orchestration_evidence_example_files_exist() -> None:
    assert README.is_file()
    assert PAYLOAD.is_file()
    assert BRIDGE_DOC.is_file()


def test_agent_orchestration_evidence_payload_is_valid_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "json.tool",
            str(PAYLOAD),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_agent_orchestration_evidence_payload_declares_non_authority_boundary() -> None:
    payload = load_payload()

    assert payload["schema_version"] == "agent_orchestration_evidence_v0"
    assert payload["source"] == "symphony"
    assert payload["evidence_role"] == "diagnostic"
    assert payload["normative"] is False
    assert payload["release_authority"] is False

    pulse_ingestion = payload["pulse_ingestion"]
    assert pulse_ingestion["recommended_fold_in_target"] == "status.meta.agent_work_evidence"
    assert pulse_ingestion["gate_promotion"] is False
    assert pulse_ingestion["release_decision_claim"] == "none"

    authority_boundary = pulse_ingestion["authority_boundary"]
    assert "diagnostic" in authority_boundary
    assert "release authority" in authority_boundary
    assert "explicitly promoted" in authority_boundary


def test_agent_orchestration_evidence_payload_contains_work_evidence_shape() -> None:
    payload = load_payload()

    assert payload["task"]["task_id"]
    assert payload["task"]["tracker"]
    assert payload["agent_run"]["agent_run_id"]
    assert payload["agent_run"]["workspace_id"]
    assert payload["agent_run"]["execution_mode"] == "isolated"
    assert payload["agent_run"]["status"] == "completed"

    proof_of_work = payload["proof_of_work"]
    assert proof_of_work["proof_of_work_present"] is True
    assert proof_of_work["pr_url"]
    assert proof_of_work["ci_status"] == "pass"
    assert proof_of_work["review_status"] == "approved"
    assert proof_of_work["walkthrough_artifact"]

    human_review = payload["human_review"]
    assert human_review["human_accepted"] is True
    assert "not PULSE release authority" in human_review["reviewer_notes"]


def test_agent_orchestration_evidence_readme_references_existing_surfaces() -> None:
    text = README.read_text(encoding="utf-8")

    assert "symphony_work_evidence.example.json" in text
    assert "docs/AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md" in text
    assert "status.meta.agent_work_evidence" in text
    assert "status.gates" in text
    assert "diagnostic / advisory" in text or "diagnostic" in text
    assert "release authority" in text


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
