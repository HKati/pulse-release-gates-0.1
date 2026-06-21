#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]

GIT_SHA = "a" * 40
RUN_KEY = (
    "GITHUB_RUN_ID=123|"
    "GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
REPOSITORY = "HKati/pulse-release-gates-test"
CREATED_UTC = "2026-06-19T00:00:00Z"
SOURCE_DATE_EPOCH = "1781827200"

REQUIRED_GATE = "q1_grounded_ok"
UNSUPPORTED_GATE = "q2_consistency_ok"

RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]

CHAIN_FILES = [
    "PULSE_safe_pack_v0/tools/"
    "run_recorded_required_gate_evaluations_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "evaluate_required_gate_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "build_release_grade_candidate_status_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "build_recorded_release_candidates_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "build_release_evidence_input_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "check_release_evidence_input_manifest_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "check_recorded_release_evidence_v0.py",
    "PULSE_safe_pack_v0/tools/"
    "materialize_release_required_from_verifier_v0.py",
    "schemas/required_gate_evidence_v0.schema.json",
    "schemas/required_gate_evaluation_result_v0.schema.json",
    "schemas/recorded_release_candidate_envelope_v0.schema.json",
    "schemas/release_evidence_input_manifest_v0.schema.json",
    "schemas/status/status_v1.schema.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _write_text(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _read_json(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(payload, dict)

    return payload


def _copy_from_repo(
    repo: Path,
    relative: str,
) -> None:
    source = REPO_ROOT / relative

    assert source.is_file(), (
        "missing checked-in test dependency: "
        f"{relative}"
    )

    target = repo / relative

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        target,
    )


def _policy_text(
    required_gate: str = REQUIRED_GATE,
) -> str:
    release_lines = "\n".join(
        f"    - {gate}"
        for gate in RELEASE_REQUIRED_GATES
    )

    return f"""policy:
  id: pulse-gate-policy-v0
  version: "0.1.5"

enforcement:
  required_missing: FAIL
  required_false: FAIL
  advisory_missing: WARN
  advisory_false: WARN
  unknown_gate_in_status: WARN
  external_detectors_default: ADVISORY

gates:
  required:
    - {required_gate}
  core_required:
    - {required_gate}
  release_required:
{release_lines}
  advisory:
    - external_summaries_present
    - external_all_pass
"""


def _registry_text(
    required_gate: str = REQUIRED_GATE,
) -> str:
    gates = [
        required_gate,
        *RELEASE_REQUIRED_GATES,
    ]

    lines = "\n".join(
        f"  {gate}:\n"
        "    category: test\n"
        f"    description: "
        f"Test registry entry for {gate}"
        for gate in gates
    )

    return (
        "version: gate_registry_v0\n"
        "gates:\n"
        + lines
        + "\n"
    )


def _plan_payload(
    required_gate: str = REQUIRED_GATE,
) -> dict[str, Any]:
    result_path = (
        "PULSE_safe_pack_v0/artifacts/"
        "required_gate_inputs/"
        f"{required_gate}.json"
    )

    return {
        "schema_version": (
            "required_gate_evaluation_plan_v0"
        ),
        "plan_version": "0.1.0",
        "evaluations": {
            required_gate: {
                "evaluation_id": (
                    f"pulse.required."
                    f"{required_gate}.v0"
                ),
                "command": [
                    "{python}",
                    (
                        "PULSE_safe_pack_v0/tools/"
                        "evaluate_required_gate_v0.py"
                    ),
                    "--repo-root",
                    "{repo_root}",
                    "--gate-id",
                    required_gate,
                    "--out",
                    result_path,
                ],
                "result": {
                    "artifact": result_path,
                    "json_pointer": "/pass",
                },
                "evidence_artifacts": [
                    {
                        "path": result_path,
                        "kind": (
                            "required_gate_evaluation"
                        ),
                        "schema_version": (
                            "required_gate_"
                            "evaluation_result_v0"
                        ),
                    }
                ],
            }
        },
    }


def _base_env() -> dict[str, str]:
    env = os.environ.copy()

    env.update(
        {
            "GITHUB_SHA": GIT_SHA,
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_REF_NAME": "v-test",
            "PULSE_GIT_SHA": GIT_SHA,
            "PULSE_RUN_KEY": RUN_KEY,
            "PULSE_RUN_MODE": "prod",
            "SOURCE_DATE_EPOCH": (
                SOURCE_DATE_EPOCH
            ),
        }
    )

    return env


def _run_tool(
    repo: Path,
    relative_tool: str,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo / relative_tool),
            *args,
        ],
        cwd=repo,
        env=env or _base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _artifact_ref(
    repo: Path,
    relative: str,
    kind: str,
    schema_version: str | None = None,
) -> dict[str, Any]:
    path = repo / relative

    assert path.is_file(), relative

    return {
        "path": relative,
        "sha256": _sha256(path),
        "kind": kind,
        "schema_version": schema_version,
    }


def _bootstrap_repo(
    tmp_path: Path,
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    for relative in CHAIN_FILES:
        _copy_from_repo(
            repo,
            relative,
        )

    _write_text(
        repo / "pulse_gate_policy_v0.yml",
        _policy_text(),
    )

    _write_text(
        repo / "pulse_gate_registry_v0.yml",
        _registry_text(),
    )

    _write_json(
        repo
        / "PULSE_safe_pack_v0/profiles/"
        "required_gate_evaluations_v0.json",
        _plan_payload(),
    )

    _write_text(
        repo
        / "PULSE_safe_pack_v0/profiles/"
        "external_thresholds.yaml",
        """external_overall_policy: all
llamaguard_violation_rate_max: 0.10
""",
    )

    _write_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "refusal_delta_summary.json",
        {
            "schema_version": (
                "refusal_delta_summary_v0"
            ),
            "n": 1,
            "pass": True,
        },
    )

    _write_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "external/llamaguard_summary.json",
        {
            "schema_version": (
                "external_summary_v1"
            ),
            "violation_rate": 0.0,
        },
    )

    policy_path = (
        repo
        / "pulse_gate_policy_v0.yml"
    )

    registry_path = (
        repo
        / "pulse_gate_registry_v0.yml"
    )

    plan_path = (
        repo
        / "PULSE_safe_pack_v0/profiles/"
        "required_gate_evaluations_v0.json"
    )

    evaluator_path = (
        repo
        / "PULSE_safe_pack_v0/tools/"
        "evaluate_required_gate_v0.py"
    )

    input_refs = [
        _artifact_ref(
            repo,
            "pulse_gate_policy_v0.yml",
            "gate_policy",
        ),
        _artifact_ref(
            repo,
            "pulse_gate_registry_v0.yml",
            "gate_registry",
        ),
        _artifact_ref(
            repo,
            (
                "PULSE_safe_pack_v0/profiles/"
                "required_gate_evaluations_v0.json"
            ),
            "evaluation_plan",
            (
                "required_gate_"
                "evaluation_plan_v0"
            ),
        ),
        _artifact_ref(
            repo,
            (
                "PULSE_safe_pack_v0/tools/"
                "evaluate_required_gate_v0.py"
            ),
            "evaluation_tool",
        ),
    ]

    result_relative = (
        "PULSE_safe_pack_v0/artifacts/"
        "required_gate_inputs/"
        f"{REQUIRED_GATE}.json"
    )

    result_payload = {
        "schema_version": (
            "required_gate_"
            "evaluation_result_v0"
        ),
        "created_utc": CREATED_UTC,
        "gate_id": REQUIRED_GATE,
        "evaluation_id": (
            f"pulse.required."
            f"{REQUIRED_GATE}.v0"
        ),
        "pass": True,
        "status": "passed",
        "run_identity": {
            "git_sha": GIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "subject": {
            "repository": REPOSITORY,
            "commit_sha": GIT_SHA,
            "release_candidate": "v-test",
        },
        "policy_binding": {
            "policy_path": (
                "pulse_gate_policy_v0.yml"
            ),
            "policy_sha256": (
                _sha256(policy_path)
            ),
            "policy_set": "required",
        },
        "registry_binding": {
            "registry_path": (
                "pulse_gate_registry_v0.yml"
            ),
            "registry_sha256": (
                _sha256(registry_path)
            ),
        },
        "plan_binding": {
            "plan_path": (
                "PULSE_safe_pack_v0/profiles/"
                "required_gate_evaluations_v0.json"
            ),
            "plan_sha256": (
                _sha256(plan_path)
            ),
            "plan_schema_version": (
                "required_gate_"
                "evaluation_plan_v0"
            ),
        },
        "evaluator": {
            "id": (
                "pulse_required_gate_"
                "dispatcher_v0"
            ),
            "version": "0.1.0",
            "tool_path": (
                "PULSE_safe_pack_v0/tools/"
                "evaluate_required_gate_v0.py"
            ),
            "tool_sha256": (
                _sha256(evaluator_path)
            ),
        },
        "input_artifacts": input_refs,
        "checks": [
            {
                "check_id": (
                    "pulse.required."
                    "q1_grounded_ok."
                    "synthetic.v0"
                ),
                "kind": "contract",
                "passed": True,
                "details": (
                    "Synthetic passing fixture for "
                    "builder-chain contract "
                    "verification."
                ),
                "command": [
                    "python",
                    "synthetic-q1-check",
                ],
                "exit_code": 0,
                "evidence_paths": [
                    "pulse_gate_policy_v0.yml"
                ],
                "diagnostics": [],
            }
        ],
        "diagnostics": [],
        "warnings": [],
        "authority_boundary": {
            "normative": False,
            "creates_release_authority": False,
            "materializes_status": False,
            "materializes_release_required": (
                False
            ),
            "direct_recorded_evidence_candidate": (
                False
            ),
            "replaces_check_gates": False,
        },
    }

    _write_json(
        repo / result_relative,
        result_payload,
    )

    producer_path = (
        repo
        / "PULSE_safe_pack_v0/tools/"
        "run_recorded_required_gate_"
        "evaluations_v0.py"
    )

    aggregate_payload = {
        "schema_version": (
            "required_gate_evidence_v0"
        ),
        "created_utc": CREATED_UTC,
        "run_identity": {
            "git_sha": GIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "subject": {
            "repository": REPOSITORY,
            "commit_sha": GIT_SHA,
            "release_candidate": "v-test",
        },
        "policy_binding": {
            "policy_path": (
                "pulse_gate_policy_v0.yml"
            ),
            "policy_sha256": (
                _sha256(policy_path)
            ),
            "policy_set": "required",
        },
        "registry_binding": {
            "registry_path": (
                "pulse_gate_registry_v0.yml"
            ),
            "registry_sha256": (
                _sha256(registry_path)
            ),
        },
        "producer": {
            "id": (
                "pulse_recorded_required_"
                "gate_evaluator_v0"
            ),
            "version": "0.1.0",
            "trusted": True,
            "tool_path": (
                "PULSE_safe_pack_v0/tools/"
                "run_recorded_required_gate_"
                "evaluations_v0.py"
            ),
            "tool_sha256": (
                _sha256(producer_path)
            ),
        },
        "gates": {
            REQUIRED_GATE: {
                "value": True,
                "status": "passed",
                "evaluation_id": (
                    f"pulse.required."
                    f"{REQUIRED_GATE}.v0"
                ),
                "evidence_artifacts": [
                    _artifact_ref(
                        repo,
                        result_relative,
                        (
                            "required_gate_"
                            "evaluation"
                        ),
                        (
                            "required_gate_"
                            "evaluation_result_v0"
                        ),
                    )
                ],
                "diagnostics": [],
            }
        },
        "authority_boundary": {
            "normative": False,
            "creates_release_authority": False,
            "materializes_release_required": (
                False
            ),
            "replaces_check_gates": False,
        },
        "warnings": [],
    }

    _write_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "required_gate_evidence_v0.json",
        aggregate_payload,
    )

    return repo


def _build_candidate_status(
    repo: Path,
) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "build_release_grade_"
            "candidate_status_v0.py"
        ),
        "--repo-root",
        str(repo),
    )


def _build_candidates(
    repo: Path,
) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "build_recorded_release_"
            "candidates_v0.py"
        ),
        "--repo-root",
        str(repo),
    )


def _build_manifest(
    repo: Path,
) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "build_release_evidence_"
            "input_manifest_v0.py"
        ),
        "--repo-root",
        str(repo),
    )


def test_checked_in_plan_exactly_covers_canonical_required_policy(
) -> None:
    policy = yaml.safe_load(
        (
            REPO_ROOT
            / "pulse_gate_policy_v0.yml"
        ).read_text(
            encoding="utf-8",
        )
    )

    plan = _read_json(
        REPO_ROOT
        / "PULSE_safe_pack_v0/profiles/"
        "required_gate_evaluations_v0.json"
    )

    required = policy["gates"]["required"]
    evaluations = plan["evaluations"]

    assert set(evaluations) == set(required)

    for gate in required:
        entry = evaluations[gate]

        assert entry["command"][0] == (
            "{python}"
        )

        assert entry["command"][1] == (
            "PULSE_safe_pack_v0/tools/"
            "evaluate_required_gate_v0.py"
        )

        assert (
            entry["result"]["json_pointer"]
            == "/pass"
        )

        assert (
            entry["result"]["artifact"]
            == (
                "PULSE_safe_pack_v0/artifacts/"
                "required_gate_inputs/"
                f"{gate}.json"
            )
        )


def test_required_gate_evidence_schema_rejects_path_traversal(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    schema = _read_json(
        repo
        / "schemas/"
        "required_gate_evidence_v0."
        "schema.json"
    )

    payload = _read_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "required_gate_evidence_v0.json"
    )

    payload[
        "gates"
    ][
        REQUIRED_GATE
    ][
        "evidence_artifacts"
    ][
        0
    ][
        "path"
    ] = "../../escape.json"

    errors = list(
        Draft202012Validator(
            schema
        ).iter_errors(
            payload
        )
    )

    assert errors

    assert any(
        list(error.absolute_path)[-1:]
        == ["path"]
        for error in errors
    )


def test_required_evidence_producer_rejects_incomplete_plan(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    plan_path = (
        repo
        / "PULSE_safe_pack_v0/profiles/"
        "required_gate_evaluations_v0.json"
    )

    plan = _read_json(plan_path)
    plan["evaluations"] = {}

    _write_json(
        plan_path,
        plan,
    )

    out = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "required_gate_evidence_v0.json"
    )

    out.unlink()

    result = _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "run_recorded_required_gate_"
            "evaluations_v0.py"
        ),
        "--repo-root",
        str(repo),
    )

    assert result.returncode != 0
    assert not out.exists()

    assert (
        "plan.evaluations must be a "
        "non-empty object"
        in result.stderr
    )


def test_unimplemented_required_gate_fails_closed_with_recorded_result(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    _write_text(
        repo / "pulse_gate_policy_v0.yml",
        _policy_text(
            UNSUPPORTED_GATE
        ),
    )

    _write_text(
        repo / "pulse_gate_registry_v0.yml",
        _registry_text(
            UNSUPPORTED_GATE
        ),
    )

    _write_json(
        repo
        / "PULSE_safe_pack_v0/profiles/"
        "required_gate_evaluations_v0.json",
        _plan_payload(
            UNSUPPORTED_GATE
        ),
    )

    _write_text(
        repo
        / "metrics/specs/"
        "q2_consistency_v0.yml",
        (
            "spec:\n"
            "  id: q2_consistency_v0\n"
            "  version: 0.1.0\n"
        ),
    )

    output = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "required_gate_inputs/"
        f"{UNSUPPORTED_GATE}.json"
    )

    env = _base_env()

    env[
        "PULSE_REQUIRED_GATE_ID"
    ] = UNSUPPORTED_GATE

    env[
        "PULSE_REQUIRED_GATE_"
        "EVALUATION_ID"
    ] = (
        f"pulse.required."
        f"{UNSUPPORTED_GATE}.v0"
    )

    result = _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "evaluate_required_gate_v0.py"
        ),
        "--repo-root",
        str(repo),
        "--gate-id",
        UNSUPPORTED_GATE,
        "--out",
        (
            "PULSE_safe_pack_v0/artifacts/"
            "required_gate_inputs/"
            f"{UNSUPPORTED_GATE}.json"
        ),
        env=env,
    )

    assert result.returncode != 0
    assert output.is_file()

    payload = _read_json(output)

    assert payload["pass"] is False
    assert payload["status"] == "failed"
    assert payload["diagnostics"]

    assert (
        payload["checks"][0]["passed"]
        is False
    )

    assert (
        payload[
            "authority_boundary"
        ][
            "creates_release_authority"
        ]
        is False
    )


def test_candidate_status_rejects_tampered_gate_result(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    result_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "required_gate_inputs/"
        f"{REQUIRED_GATE}.json"
    )

    payload = _read_json(
        result_path
    )

    payload[
        "checks"
    ][
        0
    ][
        "details"
    ] = "tampered"

    _write_json(
        result_path,
        payload,
    )

    status_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "status.json"
    )

    result = _build_candidate_status(
        repo
    )

    assert result.returncode != 0
    assert not status_path.exists()

    assert (
        "sha256 mismatch"
        in result.stderr
    )


def test_candidate_builder_writes_non_stubbed_required_only_status(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    result = _build_candidate_status(
        repo
    )

    assert result.returncode == 0, (
        result.stderr
    )

    status = _read_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "status.json"
    )

    assert status["gates"] == {
        REQUIRED_GATE: True
    }

    assert (
        status["metrics"]["run_mode"]
        == "prod"
    )

    assert (
        status[
            "diagnostics"
        ][
            "gates_stubbed"
        ]
        is False
    )

    assert (
        status[
            "diagnostics"
        ][
            "scaffold"
        ]
        is False
    )

    assert (
        status[
            "diagnostics"
        ][
            "candidate_status"
        ]
        is True
    )

    for gate in RELEASE_REQUIRED_GATES:
        assert gate not in status["gates"]


def test_candidate_builder_rejects_minimal_generic_external_summary(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    candidate_status = _build_candidate_status(
        repo
    )

    assert (
        candidate_status.returncode
        == 0
    ), candidate_status.stderr

    external_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "external/llamaguard_summary.json"
    )

    _write_json(
        external_path,
        {
            "value": 0,
        },
    )

    candidate_dir = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidates"
    )

    index_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidate_"
        "index_v0.json"
    )

    result = _build_candidates(
        repo
    )

    assert result.returncode != 0
    assert not candidate_dir.exists()
    assert not index_path.exists()

    assert (
        "external summary llamaguard"
        in result.stderr
    )

    assert (
        "external_summary_v1"
        in result.stderr
    )


def test_candidate_builder_clears_stale_outputs_when_external_missing(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    candidate_status = (
        _build_candidate_status(
            repo
        )
    )

    assert (
        candidate_status.returncode
        == 0
    ), candidate_status.stderr

    first = _build_candidates(repo)

    assert first.returncode == 0, (
        first.stderr
    )

    candidate_dir = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidates"
    )

    index_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidate_"
        "index_v0.json"
    )

    assert candidate_dir.is_dir()
    assert index_path.is_file()

    (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "external/"
        "llamaguard_summary.json"
    ).unlink()

    second = _build_candidates(repo)

    assert second.returncode != 0

    assert (
        "no canonical external detector "
        "summaries were found"
        in second.stderr
    )

    assert not candidate_dir.exists()
    assert not index_path.exists()


def test_manifest_builder_rejects_tampered_candidate_envelope(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    assert (
        _build_candidate_status(
            repo
        ).returncode
        == 0
    )

    assert (
        _build_candidates(
            repo
        ).returncode
        == 0
    )

    candidate = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidates/"
        "detector_materialization.json"
    )

    payload = _read_json(candidate)

    payload["warnings"] = [
        "tampered after index binding"
    ]

    _write_json(
        candidate,
        payload,
    )

    manifest_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "release_evidence_input_"
        "manifest_v0.json"
    )

    result = _build_manifest(repo)

    assert result.returncode != 0
    assert not manifest_path.exists()

    assert (
        "sha256 mismatch"
        in result.stderr
    )


def test_synthetic_chain_verifies_and_materializes_release_required(
    tmp_path: Path,
) -> None:
    repo = _bootstrap_repo(tmp_path)

    candidate_status = (
        _build_candidate_status(
            repo
        )
    )

    assert (
        candidate_status.returncode
        == 0
    ), candidate_status.stderr

    candidate_build = (
        _build_candidates(
            repo
        )
    )

    assert (
        candidate_build.returncode
        == 0
    ), candidate_build.stderr

    index = _read_json(
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_candidate_"
        "index_v0.json"
    )

    assert index["candidate_ids"] == [
        "detector_materialization",
        "external_llamaguard",
        "refusal_delta_summary",
    ]

    manifest_build = (
        _build_manifest(
            repo
        )
    )

    assert (
        manifest_build.returncode
        == 0
    ), manifest_build.stderr

    manifest_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "release_evidence_input_"
        "manifest_v0.json"
    )

    manifest = _read_json(
        manifest_path
    )

    assert set(
        manifest[
            "expected_gate_materialization"
        ]
    ) == set(
        RELEASE_REQUIRED_GATES
    )

    for gate in RELEASE_REQUIRED_GATES:
        materialization = manifest[
            "expected_gate_materialization"
        ][
            gate
        ]

        relation_ids = materialization[
            "relation_binding_ids"
        ]

        gate_relations = [
            manifest[
                "expected_relation_bindings"
            ][
                relation_id
            ]
            for relation_id in relation_ids
            if (
                manifest[
                    "expected_relation_bindings"
                ][
                    relation_id
                ][
                    "binding_type"
                ]
                == "artifact_to_gate"
            )
        ]

        assert gate_relations

        assert all(
            (
                relation[
                    "expected_gate_id"
                ]
                == gate
            )
            and (
                relation["target"]
                == f"gate.{gate}"
            )
            for relation in gate_relations
        )

    report_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "recorded_release_evidence_"
        "verifier_v0.json"
    )

    verification = _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "check_recorded_release_"
            "evidence_v0.py"
        ),
        "--manifest",
        str(manifest_path),
        "--repo-root",
        str(repo),
        "--out-json",
        str(report_path),
    )

    assert (
        verification.returncode
        == 0
    ), verification.stderr

    report = _read_json(
        report_path
    )

    assert (
        report["status"]
        == "verified"
    )

    for gate in RELEASE_REQUIRED_GATES:
        gate_result = report[
            "gate_materialization_admissibility"
        ][
            gate
        ]

        assert (
            gate_result["status"]
            == "verified"
        )

        assert (
            gate_result["admissible"]
            is True
        )

        assert (
            gate_result.get(
                "errors",
                [],
            )
            == []
        )

    status_path = (
        repo
        / "PULSE_safe_pack_v0/artifacts/"
        "status.json"
    )

    materialization = _run_tool(
        repo,
        (
            "PULSE_safe_pack_v0/tools/"
            "materialize_release_required_"
            "from_verifier_v0.py"
        ),
        "--status",
        str(status_path),
        "--verifier-report",
        str(report_path),
        "--manifest",
        str(manifest_path),
        "--repo-root",
        str(repo),
        "--policy",
        str(
            repo
            / "pulse_gate_policy_v0.yml"
        ),
        "--registry",
        str(
            repo
            / "pulse_gate_registry_v0.yml"
        ),
        "--out",
        str(status_path),
    )

    assert (
        materialization.returncode
        == 0
    ), materialization.stderr

    final_status = _read_json(
        status_path
    )

    assert (
        final_status[
            "gates"
        ][
            REQUIRED_GATE
        ]
        is True
    )

    for gate in RELEASE_REQUIRED_GATES:
        assert (
            final_status[
                "gates"
            ][
                gate
            ]
            is True
        )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [__file__]
        )
    )
