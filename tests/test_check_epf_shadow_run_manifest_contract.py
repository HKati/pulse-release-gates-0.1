from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_epf_shadow_run_manifest_contract.py"
FIXTURES = ROOT / "tests" / "fixtures" / "epf_shadow_run_manifest_v0"


def _run(input_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(input_path), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stdout)


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_pass_fixture_is_valid() -> None:
    result = _run(FIXTURES / "pass.json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["artifact_version"] == "epf_shadow_run_manifest_v0"
    assert payload["run_reality_state"] == "real"
    assert payload["verdict"] == "pass"


def test_changed_without_warn_fixture_fails() -> None:
    result = _run(FIXTURES / "changed_without_warn.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "verdict" and "must use verdict" in issue["message"]
        for issue in payload["errors"]
    )


def test_changed_exceeds_total_gates_fixture_fails() -> None:
    result = _run(FIXTURES / "changed_exceeds_total_gates.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "payload.comparison.changed"
        and "changed must not exceed total_gates" in issue["message"]
        for issue in payload["errors"]
    )


def test_example_count_exceeds_changed_fixture_fails() -> None:
    result = _run(FIXTURES / "example_count_exceeds_changed.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "payload.comparison.example_count"
        and "example_count must not exceed changed" in issue["message"]
        for issue in payload["errors"]
    )


def test_real_zero_changed_wrong_verdict_fixture_fails() -> None:
    result = _run(FIXTURES / "real_zero_changed_wrong_verdict.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "verdict"
        and "must use verdict='pass' when changed=0" in issue["message"]
        for issue in payload["errors"]
    )


def test_missing_input_is_neutral_with_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json", "--if-input-present")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is True
    assert payload["artifact_version"] is None
    assert payload["run_reality_state"] is None
    assert payload["verdict"] is None


def test_missing_input_fails_without_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json")
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert payload["neutral"] is False
    assert any(issue["path"] == "input" for issue in payload["errors"])


def test_baseline_and_epf_status_paths_must_differ(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["payload"]["artifacts"]["epf_status_path"] = fixture["payload"]["artifacts"]["baseline_status_path"]

    path = tmp_path / "same_status_paths.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "payload.artifacts"
        and "baseline_status_path and epf_status_path must differ" in issue["message"]
        for issue in payload["errors"]
    )


def test_source_artifacts_must_cover_payload_artifacts(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["source_artifacts"] = [
        item
        for item in fixture["source_artifacts"]
        if item["path"] != "epf_report.txt"
    ]

    path = tmp_path / "missing_epf_report_source_artifact.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "source_artifacts"
        and "epf_report.txt" in issue["message"]
        for issue in payload["errors"]
    )


def test_invalid_overall_state_requires_invalid_branch(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["run_reality_state"] = "invalid"
    fixture["verdict"] = "invalid"
    fixture["payload"]["branch_states"]["baseline_state"] = "real"
    fixture["payload"]["branch_states"]["epf_state"] = "real"

    path = tmp_path / "invalid_overall_without_invalid_branch.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "payload.branch_states"
        and "at least one branch must be invalid" in issue["message"]
        for issue in payload["errors"]
    )
