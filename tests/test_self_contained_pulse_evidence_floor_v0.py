#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools import (  # noqa: E402
    build_self_contained_pulse_evidence_floor_v0 as floor,
)


REPOSITORY = "HKati/pulse-release-gates-0.1"
GIT_SHA = "d" * 40
RUN_KEY = "GITHUB_RUN_ID=123|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
WORKFLOW_REF = (
    "HKati/pulse-release-gates-0.1/"
    ".github/workflows/pulse_ci.yml@refs/heads/main"
)
CREATED_UTC = "2026-06-27T00:00:00Z"

SAFE_PACK_SCHEMA = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "schemas"
    / "self_contained_pulse_evidence_floor_v0.schema.json"
)
ROOT_SCHEMA = (
    REPO_ROOT
    / "schemas"
    / "self_contained_pulse_evidence_floor_v0.schema.json"
)

MANDATORY_ARTIFACT_ROLES = {
    "status",
    "gate_policy",
    "gate_registry",
    "required_gate_evidence",
}

MANDATORY_CHECK_IDS = {
    "status_artifact_present_and_bound",
    "policy_and_registry_digest_bound",
    "required_gate_status_literal_true",
    "required_gate_evidence_literal_pass",
    "external_model_not_required_for_tier0",
}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            payload,
            sort_keys=True,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _schema() -> dict:
    assert SAFE_PACK_SCHEMA.is_file(), (
        f"missing bundled schema: {SAFE_PACK_SCHEMA}"
    )
    return json.loads(SAFE_PACK_SCHEMA.read_text(encoding="utf-8"))


def _schema_errors(payload: dict) -> list[str]:
    validator = Draft202012Validator(
        _schema(),
        format_checker=FormatChecker(),
    )
    return sorted(error.message for error in validator.iter_errors(payload))


def _bootstrap(tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()

    required_gates = [
        "pass_controls_refusal",
        "refusal_delta_pass",
    ]

    policy = {
        "policy": {
            "id": "pulse-gate-policy-v0",
            "version": "test",
        },
        "gates": {
            "required": required_gates,
            "release_required": [
                "external_summaries_present",
            ],
        },
    }
    registry = {
        "gates": {
            gate: {
                "id": gate,
                "normative": True,
            }
            for gate in [
                *required_gates,
                "external_summaries_present",
            ]
        }
    }
    status = {
        "version": "1.0.0",
        "created_utc": CREATED_UTC,
        "gates": {
            "pass_controls_refusal": True,
            "refusal_delta_pass": True,
        },
        "metrics": {
            "git_sha": GIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
    }
    evidence = {
        "schema_version": "required_gate_evidence_v0",
        "run_identity": {
            "git_sha": GIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "subject": {
            "repository": REPOSITORY,
            "commit_sha": GIT_SHA,
            "release_candidate": "main",
        },
        "gates": {
            gate: {
                "value": True,
                "status": "passed",
                "evaluation_id": f"{gate}_unit_evaluation",
                "evidence_artifacts": [
                    {
                        "path": (
                            "PULSE_safe_pack_v0/artifacts/"
                            f"required_gate_inputs/{gate}.json"
                        ),
                        "sha256": "a" * 64,
                        "kind": "unit_fixture",
                        "schema_version": (
                            "required_gate_evaluation_result_v0"
                        ),
                    }
                ],
                "diagnostics": [],
            }
            for gate in required_gates
        },
    }

    paths = {
        "repo": repo,
        "policy": repo / floor.DEFAULT_POLICY,
        "registry": repo / floor.DEFAULT_REGISTRY,
        "status": repo / floor.DEFAULT_STATUS,
        "evidence": repo / floor.DEFAULT_REQUIRED_EVIDENCE,
        "out": repo / floor.DEFAULT_OUT,
    }

    _write_yaml(paths["policy"], policy)
    _write_yaml(paths["registry"], registry)
    _write_json(paths["status"], status)
    _write_json(paths["evidence"], evidence)

    return paths


def _args(repo: Path, **overrides: str) -> list[str]:
    values = {
        "repository": REPOSITORY,
        "git_sha": GIT_SHA,
        "run_key": RUN_KEY,
        "workflow_ref": WORKFLOW_REF,
        "created_utc": CREATED_UTC,
    }
    values.update(overrides)

    return [
        "--repo-root",
        str(repo),
        "--repository",
        values["repository"],
        "--git-sha",
        values["git_sha"],
        "--run-key",
        values["run_key"],
        "--workflow-ref",
        values["workflow_ref"],
        "--created-utc",
        values["created_utc"],
    ]


def _valid_floor_payload(tmp_path: Path) -> dict:
    paths = _bootstrap(tmp_path)

    result = floor.main(_args(paths["repo"]))

    assert result == 0
    assert paths["out"].is_file()
    return json.loads(paths["out"].read_text(encoding="utf-8"))


def test_build_self_contained_floor_writes_schema_valid_artifact(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)

    result = floor.main(_args(paths["repo"]))

    assert result == 0
    assert paths["out"].is_file()
    assert not paths["out"].is_symlink()

    payload = json.loads(paths["out"].read_text(encoding="utf-8"))

    assert payload["schema_version"] == "self_contained_pulse_evidence_floor_v0"
    assert payload["repository"] == REPOSITORY
    assert payload["git_sha"] == GIT_SHA
    assert payload["run_key"] == RUN_KEY
    assert payload["floor"]["tier"] == 0
    assert payload["external_model_evidence"]["status"] == "not_required_for_tier0"
    assert payload["external_model_evidence"]["release_contribution"] == "none"
    assert payload["compute_admission"] == {
        "verdict": "ROUTE",
        "route": "self_contained_floor",
        "diagnostic_state": "OK",
        "reason": payload["compute_admission"]["reason"],
    }
    assert all(
        item["passed"] is True
        for item in payload["self_contained_checks"]
    )
    assert payload["authority_boundary"] == floor.AUTHORITY_BOUNDARY
    assert {item["role"] for item in payload["artifacts"]} == (
        MANDATORY_ARTIFACT_ROLES
    )
    assert {item["check_id"] for item in payload["self_contained_checks"]} == (
        MANDATORY_CHECK_IDS
    )
    assert _schema_errors(payload) == []


def test_schema_copy_is_published_at_advertised_id() -> None:
    assert SAFE_PACK_SCHEMA.is_file(), (
        f"missing bundled schema: {SAFE_PACK_SCHEMA}"
    )
    assert ROOT_SCHEMA.is_file(), (
        f"missing root-published schema copy: {ROOT_SCHEMA}"
    )
    assert SAFE_PACK_SCHEMA.read_text(encoding="utf-8") == (
        ROOT_SCHEMA.read_text(encoding="utf-8")
    )


def test_schema_rejects_failed_self_contained_check(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["self_contained_checks"][0]["passed"] = False

    errors = _schema_errors(payload)

    assert errors, "schema must reject a failed Tier 0 check"


def test_schema_rejects_missing_mandatory_artifact_role(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["artifacts"] = [
        item
        for item in payload["artifacts"]
        if item["role"] != "required_gate_evidence"
    ]

    errors = _schema_errors(payload)

    assert errors, "schema must require the required_gate_evidence artifact"


def test_schema_rejects_unrelated_artifact_role(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["artifacts"][0]["role"] = "placeholder"

    errors = _schema_errors(payload)

    assert errors, "schema must reject arbitrary artifact roles"


def test_schema_rejects_empty_check_evidence_paths(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["self_contained_checks"][0]["evidence_paths"] = []

    errors = _schema_errors(payload)

    assert errors, "schema must require each check to cite evidence paths"


def test_schema_rejects_missing_mandatory_check_id(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["self_contained_checks"] = [
        item
        for item in payload["self_contained_checks"]
        if item["check_id"] != "required_gate_status_literal_true"
    ]

    errors = _schema_errors(payload)

    assert errors, "schema must require required_gate_status_literal_true"


def test_schema_rejects_unrelated_check_id(
    tmp_path: Path,
) -> None:
    payload = _valid_floor_payload(tmp_path)
    payload["self_contained_checks"][0]["check_id"] = "placeholder_check"

    errors = _schema_errors(payload)

    assert errors, "schema must reject arbitrary check IDs"


def test_build_self_contained_floor_rejects_missing_required_gate(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)
    status = json.loads(paths["status"].read_text(encoding="utf-8"))
    status["gates"]["refusal_delta_pass"] = False
    _write_json(paths["status"], status)

    result = floor.main(_args(paths["repo"]))

    assert result == 1
    assert not paths["out"].exists()


def test_build_self_contained_floor_rejects_run_key_mismatch(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    evidence["run_identity"]["run_key"] = "other"
    _write_json(paths["evidence"], evidence)

    result = floor.main(_args(paths["repo"]))

    assert result == 1
    assert not paths["out"].exists()


def test_build_self_contained_floor_rejects_legacy_pass_only_gate_evidence(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))

    for entry in evidence["gates"].values():
        entry.pop("value")
        entry["pass"] = True

    _write_json(paths["evidence"], evidence)

    result = floor.main(_args(paths["repo"]))

    assert result == 1
    assert not paths["out"].exists()


def test_build_self_contained_floor_rejects_unregistered_required_gate(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)
    registry = yaml.safe_load(paths["registry"].read_text(encoding="utf-8"))
    del registry["gates"]["refusal_delta_pass"]
    _write_yaml(paths["registry"], registry)

    result = floor.main(_args(paths["repo"]))

    assert result == 1
    assert not paths["out"].exists()


def test_build_self_contained_floor_rejects_external_model_as_authority(
    tmp_path: Path,
) -> None:
    paths = _bootstrap(tmp_path)

    result = floor.main(
        [
            *_args(paths["repo"]),
            "--external-model-status",
            "not_required_for_tier0",
        ]
    )

    assert result == 0
    payload = json.loads(paths["out"].read_text(encoding="utf-8"))
    assert payload["external_model_evidence"]["release_contribution"] == "none"
    assert payload["authority_boundary"]["requires_external_model_runtime"] is False
