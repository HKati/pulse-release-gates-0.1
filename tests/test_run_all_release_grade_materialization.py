#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "check_release_grade_reference_run_v0.py"
)

RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def valid_status() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "created_utc": "2026-01-01T00:00:00Z",
        "metrics": {
            "run_mode": "prod",
        },
        "gates": {
            "detectors_materialized_ok": True,
            "external_summaries_present": True,
            "external_all_pass": True,
            "refusal_delta_evidence_present": True,
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
        },
    }


def valid_manifest() -> dict[str, Any]:
    return {
        "schema_version": "release_authority_v0",
        "run_identity": {
            "run_mode": "prod",
        },
        "authority": {
            "policy_set": "required+release_required",
            "release_required_materialized": True,
            "effective_required_gates": list(RELEASE_REQUIRED_GATES),
        },
        "evaluation": {
            "failed_required_gates": [],
            "missing_required_gates": [],
        },
        "decision": {
            "state": "PROD-PASS",
            "fail_closed": True,
        },
        "diagnostics": {
            "shadow_surfaces_non_normative": True,
        },
    }


def run_checker(
    tmp_path: pathlib.Path,
    status: dict[str, Any],
    manifest: dict[str, Any],
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    status_path = tmp_path / "status.json"
    manifest_path = tmp_path / "release_authority_v0.json"

    write_json(status_path, status)
    write_json(manifest_path, manifest)

    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
            *extra_args,
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_valid_release_grade_reference_run_passes(tmp_path: pathlib.Path) -> None:
    result = run_checker(tmp_path, valid_status(), valid_manifest())

    assert result.returncode == 0, result.stderr
    assert "OK: release-grade reference run criteria satisfied" in result.stdout


def test_non_prod_status_fails_reference_run_check(tmp_path: pathlib.Path) -> None:
    status = valid_status()
    status["metrics"]["run_mode"] = "core"

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.metrics.run_mode must be 'prod'" in result.stderr


def test_stubbed_gate_surface_fails_reference_run_check(
    tmp_path: pathlib.Path,
) -> None:
    status = valid_status()
    status["diagnostics"]["gates_stubbed"] = True

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.diagnostics.gates_stubbed must be explicit false" in result.stderr


def test_scaffold_surface_fails_reference_run_check(
    tmp_path: pathlib.Path,
) -> None:
    status = valid_status()
    status["diagnostics"]["scaffold"] = True

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.diagnostics.scaffold must be explicit false" in result.stderr


@pytest.mark.parametrize("bad_diagnostics", [[], False, "", 0, None])
def test_malformed_status_diagnostics_fails_reference_run_check(
    tmp_path: pathlib.Path,
    bad_diagnostics: object,
) -> None:
    status = valid_status()
    status["diagnostics"] = bad_diagnostics

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert (
        "status.diagnostics must be an object for a release-grade reference run"
        in result.stderr
    )


@pytest.mark.parametrize("gate", RELEASE_REQUIRED_GATES)
def test_missing_or_false_release_required_status_gate_fails(
    tmp_path: pathlib.Path,
    gate: str,
) -> None:
    status = valid_status()
    status["gates"][gate] = False

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert f"status.gates.{gate} must be literal true" in result.stderr


def test_missing_status_metrics_section_fails(tmp_path: pathlib.Path) -> None:
    status = valid_status()
    status.pop("metrics")

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.metrics must be an object" in result.stderr


def test_missing_status_gates_section_fails(tmp_path: pathlib.Path) -> None:
    status = valid_status()
    status.pop("gates")

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.gates must be an object" in result.stderr


def test_manifest_schema_version_must_match(tmp_path: pathlib.Path) -> None:
    manifest = valid_manifest()
    manifest["schema_version"] = "wrong_schema"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.schema_version must be 'release_authority_v0'" in result.stderr


def test_manifest_run_mode_must_be_prod(tmp_path: pathlib.Path) -> None:
    manifest = valid_manifest()
    manifest["run_identity"]["run_mode"] = "core"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.run_identity.run_mode must be 'prod'" in result.stderr


def test_manifest_policy_set_must_be_release_grade(tmp_path: pathlib.Path) -> None:
    manifest = valid_manifest()
    manifest["authority"]["policy_set"] = "core_required"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert (
        "manifest.authority.policy_set must be 'required+release_required'"
        in result.stderr
    )


def test_manifest_release_required_materialized_must_be_true(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["authority"]["release_required_materialized"] = False

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert (
        "manifest.authority.release_required_materialized must be true"
        in result.stderr
    )


def test_manifest_effective_required_gates_must_be_array(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["authority"]["effective_required_gates"] = "not-an-array"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.authority.effective_required_gates must be an array" in result.stderr


def test_manifest_effective_required_gates_must_include_release_required(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["authority"]["effective_required_gates"] = [
        gate
        for gate in RELEASE_REQUIRED_GATES
        if gate != "refusal_delta_evidence_present"
    ]

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert (
        "manifest.authority.effective_required_gates must include release-required gates"
        in result.stderr
    )
    assert "refusal_delta_evidence_present" in result.stderr


def test_manifest_failed_required_gates_must_be_empty(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["evaluation"]["failed_required_gates"] = ["external_all_pass"]

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.evaluation.failed_required_gates must be empty" in result.stderr


def test_manifest_missing_required_gates_must_be_empty(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["evaluation"]["missing_required_gates"] = [
        "refusal_delta_evidence_present"
    ]

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.evaluation.missing_required_gates must be empty" in result.stderr


def test_manifest_decision_state_must_be_pass_state(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["decision"]["state"] = "FAIL"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.decision.state must be PASS or PROD-PASS" in result.stderr


def test_manifest_decision_fail_closed_must_be_true(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["decision"]["fail_closed"] = False

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.decision.fail_closed must be true" in result.stderr


def test_manifest_optional_diagnostics_must_be_object_when_present(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["diagnostics"] = []

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.diagnostics must be an object when present" in result.stderr


def test_manifest_optional_diagnostics_must_mark_shadow_surfaces_non_normative(
    tmp_path: pathlib.Path,
) -> None:
    manifest = valid_manifest()
    manifest["diagnostics"]["shadow_surfaces_non_normative"] = False

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert (
        "manifest.diagnostics.shadow_surfaces_non_normative must be true"
        in result.stderr
    )


def test_optional_report_and_audit_bundle_checks(tmp_path: pathlib.Path) -> None:
    report = tmp_path / "report_card.html"
    report.write_text("<html><body>ledger</body></html>\n", encoding="utf-8")

    bundle = tmp_path / "release_authority_audit_bundle"
    bundle.mkdir()
    (bundle / "report_card.html").write_text("ledger\n", encoding="utf-8")
    (bundle / "release_authority_v0.json").write_text("{}\n", encoding="utf-8")
    (bundle / "status.json").write_text("{}\n", encoding="utf-8")

    result = run_checker(
        tmp_path,
        valid_status(),
        valid_manifest(),
        "--report",
        str(report),
        "--audit-bundle-dir",
        str(bundle),
    )

    assert result.returncode == 0, result.stderr


def test_missing_optional_report_fails_when_supplied(tmp_path: pathlib.Path) -> None:
    missing_report = tmp_path / "missing_report_card.html"

    result = run_checker(
        tmp_path,
        valid_status(),
        valid_manifest(),
        "--report",
        str(missing_report),
    )

    assert result.returncode != 0
    assert "Quality Ledger report not found" in result.stderr


def test_missing_audit_bundle_dir_fails_when_supplied(
    tmp_path: pathlib.Path,
) -> None:
    missing_bundle = tmp_path / "missing_bundle"

    result = run_checker(
        tmp_path,
        valid_status(),
        valid_manifest(),
        "--audit-bundle-dir",
        str(missing_bundle),
    )

    assert result.returncode != 0
    assert "release authority audit bundle directory not found" in result.stderr


def test_missing_audit_bundle_member_fails_when_supplied(
    tmp_path: pathlib.Path,
) -> None:
    bundle = tmp_path / "release_authority_audit_bundle"
    bundle.mkdir()
    (bundle / "report_card.html").write_text("ledger\n", encoding="utf-8")
    (bundle / "status.json").write_text("{}\n", encoding="utf-8")

    result = run_checker(
        tmp_path,
        valid_status(),
        valid_manifest(),
        "--audit-bundle-dir",
        str(bundle),
    )

    assert result.returncode != 0
    assert (
        "release authority audit bundle missing release_authority_v0.json"
        in result.stderr
    )


def test_missing_manifest_file_fails(tmp_path: pathlib.Path) -> None:
    status_path = tmp_path / "status.json"
    manifest_path = tmp_path / "missing_release_authority_v0.json"

    write_json(status_path, valid_status())

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "release_authority_v0.json not found" in result.stderr


def test_missing_status_file_fails(tmp_path: pathlib.Path) -> None:
    status_path = tmp_path / "missing_status.json"
    manifest_path = tmp_path / "release_authority_v0.json"

    write_json(manifest_path, valid_manifest())

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "status.json not found" in result.stderr


def test_malformed_status_json_fails(tmp_path: pathlib.Path) -> None:
    status_path = tmp_path / "status.json"
    manifest_path = tmp_path / "release_authority_v0.json"

    status_path.write_text("{not valid json", encoding="utf-8")
    write_json(manifest_path, valid_manifest())

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "status.json is not valid JSON" in result.stderr


def test_malformed_manifest_json_fails(tmp_path: pathlib.Path) -> None:
    status_path = tmp_path / "status.json"
    manifest_path = tmp_path / "release_authority_v0.json"

    write_json(status_path, valid_status())
    manifest_path.write_text("{not valid json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "release_authority_v0.json is not valid JSON" in result.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
