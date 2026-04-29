from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_grade_reference_run_v0.py"


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def valid_status() -> dict:
    return {
        "version": "test",
        "created_utc": "2026-04-27T00:00:00Z",
        "metrics": {"run_mode": "prod"},
        "gates": {
            "detectors_materialized_ok": True,
            "external_summaries_present": True,
            "external_all_pass": True,
        },
        "diagnostics": {
            "gates_stubbed": False,
        },
    }


def valid_manifest() -> dict:
    return {
        "schema_version": "release_authority_v0",
        "created_utc": "2026-04-27T00:00:00Z",
        "run_identity": {
            "run_mode": "prod",
            "workflow_name": "PULSE CI",
            "event_name": "workflow_dispatch",
            "ref": "refs/heads/main",
            "git_sha": "0" * 40,
        },
        "inputs": {},
        "authority": {
            "policy_set": "required+release_required",
            "effective_required_gates": [
                "pass_controls_refusal",
                "q1_grounded_ok",
                "q4_slo_ok",
                "detectors_materialized_ok",
                "external_summaries_present",
                "external_all_pass",
            ],
            "release_required_materialized": True,
        },
        "evaluation": {
            "required_gate_results": {
                "detectors_materialized_ok": True,
                "external_summaries_present": True,
                "external_all_pass": True,
            },
            "failed_required_gates": [],
            "missing_required_gates": [],
        },
        "decision": {
            "state": "PASS",
            "fail_closed": True,
        },
        "diagnostics": {
            "shadow_surfaces_present": [],
            "shadow_surfaces_non_normative": True,
            "status_meta_foldins": [],
            "advisory_gates_present": [],
            "publication_surfaces_present": [],
        },
    }


def run_checker(
    tmp_path: Path,
    status: dict,
    manifest: dict,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    status_path = write_json(tmp_path / "status.json", status)
    manifest_path = write_json(tmp_path / "release_authority_v0.json", manifest)

    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--status",
            str(status_path),
            "--manifest",
            str(manifest_path),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_release_grade_reference_run_passes(tmp_path: Path) -> None:
    result = run_checker(tmp_path, valid_status(), valid_manifest())

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_core_run_mode_fails_reference_run_check(tmp_path: Path) -> None:
    status = valid_status()
    status["metrics"]["run_mode"] = "core"

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "run_mode must be 'prod'" in result.stderr


def test_stubbed_gate_surface_fails_reference_run_check(tmp_path: Path) -> None:
    status = valid_status()
    status["diagnostics"]["gates_stubbed"] = True

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "gates_stubbed must not be true" in result.stderr


@pytest.mark.parametrize("bad_diagnostics", [[], False, "", 0, None])
def test_malformed_status_diagnostics_fails_reference_run_check(
    tmp_path: Path,
    bad_diagnostics: object,
) -> None:
    status = valid_status()
    status["diagnostics"] = bad_diagnostics

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "status.diagnostics must be an object when present" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_release_required_gate_fails_reference_run_check(tmp_path: Path) -> None:
    status = valid_status()
    status["gates"]["external_all_pass"] = False

    result = run_checker(tmp_path, status, valid_manifest())

    assert result.returncode != 0
    assert "external_all_pass" in result.stderr


def test_manifest_must_use_release_grade_policy_set(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["authority"]["policy_set"] = "core_required"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "required+release_required" in result.stderr


def test_manifest_must_materialize_release_required(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["authority"]["release_required_materialized"] = False

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "release_required_materialized must be true" in result.stderr


def test_manifest_must_not_have_failed_or_missing_required_gates(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["evaluation"]["missing_required_gates"] = ["q4_slo_ok"]
    manifest["decision"]["state"] = "FAIL"

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "missing_required_gates must be empty" in result.stderr
    assert "PASS or PROD-PASS" in result.stderr


def test_manifest_must_include_release_required_gates(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["authority"]["effective_required_gates"] = [
        "pass_controls_refusal",
        "q1_grounded_ok",
    ]

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "must include release-required gates" in result.stderr


@pytest.mark.parametrize("bad_diagnostics", [[], False, "", 0, None])
def test_malformed_manifest_diagnostics_fails_reference_run_check(
    tmp_path: Path,
    bad_diagnostics: object,
) -> None:
    manifest = valid_manifest()
    manifest["diagnostics"] = bad_diagnostics

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "manifest.diagnostics must be an object when present" in result.stderr
    assert "Traceback" not in result.stderr


def test_empty_manifest_diagnostics_fails_non_normative_invariant(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["diagnostics"] = {}

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "shadow_surfaces_non_normative must be true" in result.stderr


def test_manifest_diagnostics_must_be_non_normative(tmp_path: Path) -> None:
    manifest = valid_manifest()
    manifest["diagnostics"]["shadow_surfaces_non_normative"] = False

    result = run_checker(tmp_path, valid_status(), manifest)

    assert result.returncode != 0
    assert "shadow_surfaces_non_normative must be true" in result.stderr


def test_optional_report_and_audit_bundle_checks(tmp_path: Path) -> None:
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


def test_optional_audit_bundle_missing_file_fails(tmp_path: Path) -> None:
    report = tmp_path / "report_card.html"
    report.write_text("<html><body>ledger</body></html>\n", encoding="utf-8")

    bundle = tmp_path / "release_authority_audit_bundle"
    bundle.mkdir()
    (bundle / "report_card.html").write_text("ledger\n", encoding="utf-8")
    (bundle / "release_authority_v0.json").write_text("{}\n", encoding="utf-8")

    result = run_checker(
        tmp_path,
        valid_status(),
        valid_manifest(),
        "--report",
        str(report),
        "--audit-bundle-dir",
        str(bundle),
    )

    assert result.returncode != 0
    assert "audit bundle missing status.json" in result.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
