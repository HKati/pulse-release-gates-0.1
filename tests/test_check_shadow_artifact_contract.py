from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_shadow_artifact_contract.py"
FIXTURES = ROOT / "tests" / "fixtures" / "shadow_artifact_common_v0"


def _run(input_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(input_path), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def test_pass_fixture_is_valid() -> None:
    result = _run(
        FIXTURES / "pass.json",
        "--expected-layer-id",
        "relational_gain_shadow",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["run_reality_state"] == "real"
    assert payload["verdict"] == "pass"


def test_degraded_fixture_is_valid() -> None:
    result = _run(
        FIXTURES / "degraded.json",
        "--expected-layer-id",
        "epf_shadow_experiment_v0",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["run_reality_state"] == "degraded"
    assert payload["verdict"] == "warn"


def test_absent_fixture_is_valid() -> None:
    result = _run(
        FIXTURES / "absent.json",
        "--expected-layer-id",
        "relational_gain_shadow",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["run_reality_state"] == "absent"
    assert payload["verdict"] == "absent"


def test_invalid_absent_verdict_fails() -> None:
    result = _run(
        FIXTURES / "invalid_bad_verdict_for_absent.json",
        "--expected-layer-id",
        "relational_gain_shadow",
    )
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "verdict" and "absent runs must use verdict=absent" in issue["message"]
        for issue in payload["errors"]
    )


def test_if_input_present_preserves_neutral_absence_for_missing_file() -> None:
    result = _run(
        FIXTURES / "does_not_exist.json",
        "--expected-layer-id",
        "relational_gain_shadow",
        "--if-input-present",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is True
    assert payload["run_reality_state"] == "absent"
    assert payload["verdict"] == "absent"


def test_layer_id_mismatch_fails() -> None:
    result = _run(
        FIXTURES / "pass.json",
        "--expected-layer-id",
        "wrong_layer",
    )
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(issue["path"] == "layer_id" for issue in payload["errors"])
