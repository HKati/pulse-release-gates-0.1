from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_authority_manifest_v0.py"
SCHEMA = ROOT / "schemas" / "release_authority_v0.schema.json"
FIXTURES = ROOT / "tests" / "fixtures" / "release_authority_v0"


def run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--manifest",
            str(path),
            "--schema",
            str(SCHEMA),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def write_fixture(tmp_path: Path, name: str, data: dict) -> Path:
    out = tmp_path / name
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def test_core_pass_fixture_validates() -> None:
    result = run_checker(FIXTURES / "core_pass.json")
    assert result.returncode == 0, result.stderr


def test_core_fail_missing_gate_fixture_validates() -> None:
    result = run_checker(FIXTURES / "core_fail_missing_gate.json")
    assert result.returncode == 0, result.stderr


def test_missing_required_gate_must_be_recorded(tmp_path: Path) -> None:
    data = load_fixture("core_fail_missing_gate.json")
    data["evaluation"]["missing_required_gates"] = []

    path = write_fixture(tmp_path, "missing_not_recorded.json", data)
    result = run_checker(path)

    assert result.returncode != 0
    assert "not listed in missing_required_gates" in result.stderr


def test_missing_required_gate_must_fail_decision(tmp_path: Path) -> None:
    data = load_fixture("core_fail_missing_gate.json")
    data["decision"]["state"] = "PASS"

    path = write_fixture(tmp_path, "missing_but_pass.json", data)
    result = run_checker(path)

    assert result.returncode != 0
    assert "decision.state must be FAIL" in result.stderr


def test_false_required_gate_must_be_listed_as_failed(tmp_path: Path) -> None:
    data = load_fixture("core_pass.json")
    data["evaluation"]["required_gate_results"]["q4_slo_ok"] = False

    path = write_fixture(tmp_path, "false_not_failed.json", data)
    result = run_checker(path)

    assert result.returncode != 0
    assert "not listed in failed_required_gates" in result.stderr


def test_diagnostic_surface_must_not_be_normative(tmp_path: Path) -> None:
    data = load_fixture("core_pass.json")
    data["diagnostics"]["shadow_surfaces_present"] = [
        {
            "name": "relational_gain_shadow",
            "role": "shadow",
            "path": "PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json",
            "normative": True,
        }
    ]

    path = write_fixture(tmp_path, "normative_shadow.json", data)
    result = run_checker(path)

    assert result.returncode != 0
    assert "normative" in result.stderr


def test_non_object_top_level_sections_report_errors(tmp_path: Path) -> None:
    data = load_fixture("core_pass.json")
    data["authority"] = "oops"

    path = write_fixture(tmp_path, "non_object_authority.json", data)
    result = run_checker(path)

    assert result.returncode != 0
    assert "authority must be an object" in result.stderr
    assert "Traceback" not in result.stderr


def test_null_top_level_sections_report_errors(tmp_path: Path) -> None:
    for section in ("authority", "evaluation", "decision", "diagnostics"):
        data = load_fixture("core_pass.json")
        data[section] = None

        path = write_fixture(tmp_path, f"null_{section}.json", data)
        result = run_checker(path)

        assert result.returncode != 0
        assert f"{section} must be an object" in result.stderr
        assert "Traceback" not in result.stderr

if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
