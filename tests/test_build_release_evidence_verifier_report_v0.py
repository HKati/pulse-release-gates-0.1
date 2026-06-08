#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_release_evidence_verifier_report_v0.py"
)

HEX40 = "a" * 40


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            *args,
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_build_failed_report_without_inputs(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--repository",
        "HKati/pulse-release-gates-0.1",
        "--commit-sha",
        HEX40,
        "--run-key",
        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI",
        "--release-candidate",
        "candidate-v0",
    )

    assert result.returncode == 0, result.stderr
    assert "OK: wrote fail-closed release evidence verifier report" in result.stdout

    report = _load_json(out_path)
    assert report["schema_version"] == "release_evidence_verifier_report_v0"
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}
    assert any("does not verify evidence yet" in item for item in report["failed_checks"])
    assert any("no verified relation bindings present" in item for item in report["failed_checks"])


def test_candidate_evidence_is_recorded_but_not_verified(tmp_path: pathlib.Path) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_payload = {
        "schema_version": "detector_report_v0",
        "result": "candidate-only",
    }
    evidence_path.write_text(json.dumps(evidence_payload), encoding="utf-8")
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--repository",
        "HKati/pulse-release-gates-0.1",
        "--commit-sha",
        HEX40,
        "--run-key",
        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI",
        "--release-candidate",
        "candidate-v0",
        "--evidence",
        f"detector_evidence={evidence_path}",
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    assert len(report["evidence_inputs"]) == 1
    evidence_input = report["evidence_inputs"][0]
    assert evidence_input["kind"] == "detector_evidence"
    assert evidence_input["sha256"] == hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest()
    assert evidence_input["schema_version"] == "detector_report_v0"
    assert evidence_input["provenance"]["trusted"] is False
    assert evidence_input["provenance"]["verification_status"] == "not_verified"


def test_invalid_evidence_kind_fails_closed(tmp_path: pathlib.Path) -> None:
    evidence_path = tmp_path / "detector_report.json"
    evidence_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
        "--evidence",
        f"unsupported_kind={evidence_path}",
    )

    assert result.returncode != 0
    assert "unsupported evidence kind" in result.stderr
    assert not out_path.exists()


def test_missing_evidence_file_fails_closed(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"
    missing = tmp_path / "missing_detector_report.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
        "--evidence",
        f"detector_evidence={missing}",
    )

    assert result.returncode != 0
    assert "candidate evidence file not found" in result.stderr
    assert not out_path.exists()


def test_pass_or_allow_are_never_emitted(tmp_path: pathlib.Path) -> None:
    out_path = tmp_path / "release_evidence_verifier_report_v0.json"

    result = _run_tool(
        "--out",
        str(out_path),
        "--commit-sha",
        HEX40,
    )

    assert result.returncode == 0, result.stderr

    report = _load_json(out_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verifier_decision"] not in {"PASS", "ALLOW", "PROD-PASS"}
