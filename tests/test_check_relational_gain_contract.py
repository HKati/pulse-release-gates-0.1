from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_relational_gain_contract.py"
FIXTURES = ROOT / "tests" / "fixtures" / "relational_gain_shadow_v0"


def _run(input_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(input_path), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def test_pass_fixture_is_valid() -> None:
    result = _run(FIXTURES / "pass.json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["artifact_checker_version"] == "relational_gain_v0"
    assert payload["verdict"] == "PASS"


def test_warn_fixture_is_valid() -> None:
    result = _run(FIXTURES / "warn.json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["artifact_checker_version"] == "relational_gain_v0"
    assert payload["verdict"] == "WARN"


def test_fail_fixture_is_valid() -> None:
    result = _run(FIXTURES / "fail.json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["artifact_checker_version"] == "relational_gain_v0"
    assert payload["verdict"] == "FAIL"


def test_missing_input_is_neutral_with_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json", "--if-input-present")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is True
    assert payload["artifact_checker_version"] is None
    assert payload["verdict"] is None


def test_missing_input_fails_without_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json")
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert payload["neutral"] is False
    assert any(issue["path"] == "input" for issue in payload["errors"])


def test_warn_requires_near_boundary_signal(tmp_path: Path) -> None:
    fixture = json.loads((FIXTURES / "warn.json").read_text(encoding="utf-8"))
    fixture["metrics"]["near_boundary_edges"] = []
    fixture["metrics"]["max_edge_gain"] = 0.94

    path = tmp_path / "invalid_warn_missing_boundary.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(issue["path"] == "verdict" for issue in payload["errors"])


def test_fail_requires_offending_signal(tmp_path: Path) -> None:
    fixture = json.loads((FIXTURES / "fail.json").read_text(encoding="utf-8"))
    fixture["metrics"]["offending_edges"] = []
    fixture["metrics"]["max_edge_gain"] = 0.91
    fixture["verdict"] = "FAIL"

    path = tmp_path / "invalid_fail_without_offending.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(issue["path"] == "verdict" for issue in payload["errors"])


def test_exact_checker_version_is_required(tmp_path: Path) -> None:
    fixture = json.loads((FIXTURES / "pass.json").read_text(encoding="utf-8"))
    fixture["checker_version"] = "relational_gain_v0_dev"

    path = tmp_path / "invalid_checker_version.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(issue["path"] == "checker_version" for issue in payload["errors"])


def test_pass_must_not_contain_near_boundary_entries(tmp_path: Path) -> None:
    fixture = json.loads((FIXTURES / "pass.json").read_text(encoding="utf-8"))
    fixture["metrics"]["near_boundary_edges"] = [0.96]
    fixture["metrics"]["max_edge_gain"] = 0.96

    path = tmp_path / "invalid_pass_with_boundary.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(issue["path"] == "verdict" for issue in payload["errors"])
