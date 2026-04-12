from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_epf_paradox_summary_contract.py"
FIXTURES = ROOT / "tests" / "fixtures" / "epf_paradox_summary_v0"


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
    assert payload["deps_rc"] == 0
    assert payload["runall_rc"] == 0
    assert payload["baseline_rc"] == 0
    assert payload["epf_rc"] == 0
    assert payload["total_gates"] == 18
    assert payload["changed"] == 2


def test_changed_exceeds_total_gates_fixture_fails() -> None:
    result = _run(FIXTURES / "changed_exceeds_total_gates.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "changed" and "changed must not exceed total_gates" in issue["message"]
        for issue in payload["errors"]
    )


def test_changed_positive_without_examples_fixture_fails() -> None:
    result = _run(FIXTURES / "changed_positive_without_examples.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "examples" and "examples must be non-empty when changed is greater than 0" in issue["message"]
        for issue in payload["errors"]
    )


def test_missing_input_is_neutral_with_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json", "--if-input-present")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is True
    assert payload["changed"] is None
    assert payload["total_gates"] is None


def test_missing_input_fails_without_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json")
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert payload["neutral"] is False
    assert any(issue["path"] == "input" for issue in payload["errors"])


def test_examples_must_be_empty_when_changed_is_zero(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["changed"] = 0

    path = tmp_path / "changed_zero_with_examples.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "examples" and "examples must be empty when changed is 0" in issue["message"]
        for issue in payload["errors"]
    )


def test_examples_length_must_not_exceed_changed(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["changed"] = 1

    path = tmp_path / "examples_longer_than_changed.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "examples" and "examples length must not exceed changed" in issue["message"]
        for issue in payload["errors"]
    )


def test_duplicate_gate_examples_fail(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["total_gates"] = 3
    fixture["changed"] = 2
    fixture["examples"] = [
        {
            "gate": "q1_grounded_ok",
            "baseline": True,
            "epf": False,
        },
        {
            "gate": "q1_grounded_ok",
            "baseline": False,
            "epf": True,
        },
    ]

    path = tmp_path / "duplicate_gate_examples.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "examples[1].gate" and "duplicate gate example" in issue["message"]
        for issue in payload["errors"]
    )


def test_baseline_and_epf_must_differ_inside_example(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["examples"][0]["epf"] = fixture["examples"][0]["baseline"]

    path = tmp_path / "example_without_difference.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "examples[0]" and "baseline and epf must differ" in issue["message"]
        for issue in payload["errors"]
    )


def test_rc_fields_must_be_integer_strings(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    fixture["epf_rc"] = "success"

    path = tmp_path / "invalid_rc_string.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "epf_rc" and "must match ^-?[0-9]+$" in issue["message"]
        for issue in payload["errors"]
    )
