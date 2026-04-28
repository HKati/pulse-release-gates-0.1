from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "insert_release_authority_manifest_ledger_section.py"


def write_report(tmp_path: Path) -> Path:
    report = tmp_path / "report_card.html"
    report.write_text("<html><body><h1>PULSE Quality Ledger</h1></body></html>\n", encoding="utf-8")
    return report


def write_manifest(tmp_path: Path) -> Path:
    manifest = {
        "schema_version": "release_authority_v0",
        "created_utc": "2026-04-27T00:00:00Z",
        "run_identity": {
            "run_mode": "core",
            "workflow_name": "PULSE CI",
            "event_name": "pull_request",
            "ref": "refs/pull/1/merge",
            "git_sha": "0" * 40,
        },
        "inputs": {},
        "authority": {
            "policy_set": "core_required",
            "effective_required_gates": [
                "pass_controls_refusal",
                "pass_controls_sanit",
                "sanitization_effective",
                "q1_grounded_ok",
                "q4_slo_ok",
            ],
        },
        "evaluation": {
            "failed_required_gates": [],
            "missing_required_gates": [],
        },
        "decision": {
            "state": "PASS",
            "fail_closed": True,
        },
        "diagnostics": {
            "shadow_surfaces_non_normative": True,
            "advisory_gates_present": [
                "external_summaries_present",
                "external_all_pass",
            ],
        },
    }
    path = tmp_path / "release_authority_v0.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def run_tool(report: Path, manifest: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--report",
            str(report),
            "--manifest",
            str(manifest),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_inserts_release_authority_manifest_section(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    manifest = write_manifest(tmp_path)

    result = run_tool(report, manifest)
    assert result.returncode == 0, result.stderr

    html = report.read_text(encoding="utf-8")
    assert 'id="release-authority-manifest"' in html
    assert "Release authority manifest" in html
    assert "release_authority_v0.json" in html
    assert "Audit-only surface" in html
    assert "Non-normative / non-blocking" in html
    assert "core_required" in html
    assert "PASS" in html
    assert "</body>" in html


def test_insertion_is_idempotent(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    manifest = write_manifest(tmp_path)

    first = run_tool(report, manifest)
    second = run_tool(report, manifest)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    html = report.read_text(encoding="utf-8")
    assert html.count('id="release-authority-manifest"') == 1


def test_missing_manifest_inserts_missing_status(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    missing = tmp_path / "does_not_exist.json"

    result = run_tool(report, missing)
    assert result.returncode == 0, result.stderr

    html = report.read_text(encoding="utf-8")
    assert "MISSING/UNKNOWN" in html
    assert "Audit / traceability sidecar" in html


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
