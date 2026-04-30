from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_agent_orchestration_evidence_v0.py"
SCHEMA = ROOT / "schemas" / "agent_orchestration_evidence_v0.schema.json"
EXAMPLE = (
    ROOT
    / "examples"
    / "agent_orchestration_evidence_v0"
    / "symphony_work_evidence.example.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


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
            "authority_boundary": (
                "Agent orchestration evidence is diagnostic by default and carries "
                "no release authority unless explicitly promoted by declared gate policy."
            )
        }
    }


def run_checker(input_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--input",
            str(input_path),
            "--schema",
            str(SCHEMA),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_fails_with(payload: object, tmp_path: Path, expected: str) -> None:
    path = write_json(tmp_path / "payload.json", payload)
    result = run_checker(path)

    assert result.returncode != 0
    assert expected in result.stderr
    assert "Traceback" not in result.stderr


def test_agent_orchestration_evidence_checker_py_compiles() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(TOOL),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_agent_orchestration_evidence_checker_default_example_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: agent orchestration evidence payload is valid" in result.stdout


def test_agent_orchestration_evidence_checker_example_passes() -> None:
    result = run_checker(EXAMPLE)

    assert result.returncode == 0, result.stderr
    assert "OK: agent orchestration evidence payload is valid" in result.stdout


def test_agent_orchestration_evidence_checker_minimal_payload_passes(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    path = write_json(tmp_path / "minimal_payload.json", payload)

    result = run_checker(path)

    assert result.returncode == 0, result.stderr
    assert "OK: agent orchestration evidence payload is valid" in result.stdout


def test_checker_rejects_missing_input(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    result = run_checker(missing)

    assert result.returncode != 0
    assert "not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_checker_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{not json", encoding="utf-8")

    result = run_checker(path)

    assert result.returncode != 0
    assert "not valid JSON" in result.stderr
    assert "Traceback" not in result.stderr


def test_checker_rejects_non_object_payload(tmp_path: Path) -> None:
    assert_fails_with([], tmp_path, "payload must be a JSON object")


def test_checker_rejects_non_diagnostic_evidence_role(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["evidence_role"] = "required"

    assert_fails_with(payload, tmp_path, "evidence_role must be diagnostic")


def test_checker_rejects_normative_agent_evidence(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["normative"] = True

    assert_fails_with(payload, tmp_path, "normative must be false")


def test_checker_rejects_release_authority_claim(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["release_authority"] = True

    assert_fails_with(payload, tmp_path, "release_authority must be false")


def test_checker_rejects_gate_promotion(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["gate_promotion"] = True

    assert_fails_with(payload, tmp_path, "pulse_ingestion.gate_promotion must be false")


def test_checker_rejects_release_decision_claim(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["release_decision_claim"] = "PASS"

    assert_fails_with(payload, tmp_path, "pulse_ingestion.release_decision_claim must be none")


def test_checker_rejects_fold_in_under_gates(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["recommended_fold_in_target"] = (
        "status.gates.agent_work_evidence"
    )

    assert_fails_with(
        payload,
        tmp_path,
        "pulse_ingestion.recommended_fold_in_target must be status.meta.agent_work_evidence",
    )


def test_checker_rejects_missing_pulse_ingestion(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    del payload["pulse_ingestion"]

    assert_fails_with(payload, tmp_path, "pulse_ingestion must be an object")


def test_checker_rejects_malformed_pulse_ingestion(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"] = []

    assert_fails_with(payload, tmp_path, "pulse_ingestion must be an object")


def test_checker_rejects_missing_authority_boundary(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    del payload["pulse_ingestion"]["authority_boundary"]

    assert_fails_with(
        payload,
        tmp_path,
        "pulse_ingestion.authority_boundary must be a non-empty string",
    )


def test_checker_rejects_empty_authority_boundary(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["pulse_ingestion"]["authority_boundary"] = ""

    assert_fails_with(
        payload,
        tmp_path,
        "pulse_ingestion.authority_boundary must be a non-empty string",
    )


def test_checker_accepts_optional_descriptive_metadata(tmp_path: Path) -> None:
    payload = minimal_valid_payload()
    payload["task"]["tracker"] = "linear"
    payload["task"]["title"] = "Example agent-produced implementation task"
    payload["task"]["task_url"] = "https://example.invalid/tasks/TASK-123"
    payload["human_review"]["reviewer_notes"] = (
        "Example payload only. Human acceptance records task-level review context, "
        "not PULSE release authority."
    )
    payload["proof_of_work"]["pr_url"] = "https://example.invalid/pull/123"
    payload["proof_of_work"]["walkthrough_artifact"] = (
        "https://example.invalid/artifacts/walkthrough-123"
    )
    payload["proof_of_work"]["complexity_summary"] = (
        "Example implementation completed in an isolated agent workspace."
    )

    path = write_json(tmp_path / "metadata_payload.json", payload)
    result = run_checker(path)

    assert result.returncode == 0, result.stderr


def test_checker_rejects_example_if_boundary_is_promoted(tmp_path: Path) -> None:
    payload = deepcopy(load_json(EXAMPLE))
    payload["release_authority"] = True
    payload["pulse_ingestion"]["gate_promotion"] = True
    payload["pulse_ingestion"]["release_decision_claim"] = "PASS"

    path = write_json(tmp_path / "promoted_example.json", payload)
    result = run_checker(path)

    assert result.returncode != 0
    assert "release_authority must be false" in result.stderr
    assert "pulse_ingestion.gate_promotion must be false" in result.stderr
    assert "pulse_ingestion.release_decision_claim must be none" in result.stderr
    assert "Traceback" not in result.stderr


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
