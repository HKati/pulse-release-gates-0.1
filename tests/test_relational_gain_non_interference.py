from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_relational_gain_shadow.py"
CHECK_GATES = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"
INPUT_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "relational_gain_v0"


def _run_runner(
    status_path: Path,
    input_path: Path,
    *,
    artifact_out: Path,
    status_out: Path,
    if_input_present: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--status",
        str(status_path),
        "--input",
        str(input_path),
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    ]
    if if_input_present:
        cmd.append("--if-input-present")

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_check_gates(status_path: Path, *required: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_GATES),
            "--status",
            str(status_path),
            "--require",
            *required,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _minimal_status() -> dict[str, Any]:
    return {
        "schema_version": "status_v0",
        "gates": {
            "gate_ok": True,
            "gate_fail": False,
        },
        "meta": {
            "existing_shadow": {
                "note": "preserve me",
            }
        },
    }


@pytest.mark.parametrize("input_fixture", ["pass.json", "warn.json", "fail_edge.json"])
def test_relational_gain_shadow_does_not_change_passing_release_outcome(
    tmp_path: Path,
    input_fixture: str,
) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    before = _run_check_gates(status_path, "gate_ok")
    assert before.returncode == 0, before.stdout + before.stderr

    runner = _run_runner(
        status_path,
        INPUT_FIXTURES / input_fixture,
        artifact_out=artifact_out,
        status_out=status_out,
    )
    assert runner.returncode == 0, runner.stdout + runner.stderr

    after = _run_check_gates(status_out, "gate_ok")
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    assert after.stderr == before.stderr

    original = json.loads(status_path.read_text(encoding="utf-8"))
    folded = json.loads(status_out.read_text(encoding="utf-8"))
    assert folded["gates"] == original["gates"]


@pytest.mark.parametrize("input_fixture", ["pass.json", "warn.json", "fail_edge.json"])
def test_relational_gain_shadow_does_not_change_failing_release_outcome(
    tmp_path: Path,
    input_fixture: str,
) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    before = _run_check_gates(status_path, "gate_fail")
    assert before.returncode == 1, before.stdout + before.stderr

    runner = _run_runner(
        status_path,
        INPUT_FIXTURES / input_fixture,
        artifact_out=artifact_out,
        status_out=status_out,
    )
    assert runner.returncode == 0, runner.stdout + runner.stderr

    after = _run_check_gates(status_out, "gate_fail")
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    assert after.stderr == before.stderr

    original = json.loads(status_path.read_text(encoding="utf-8"))
    folded = json.loads(status_out.read_text(encoding="utf-8"))
    assert folded["gates"] == original["gates"]


def test_relational_gain_shadow_does_not_change_missing_gate_outcome(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    before = _run_check_gates(status_path, "missing_gate")
    assert before.returncode == 2, before.stdout + before.stderr

    runner = _run_runner(
        status_path,
        INPUT_FIXTURES / "warn.json",
        artifact_out=artifact_out,
        status_out=status_out,
    )
    assert runner.returncode == 0, runner.stdout + runner.stderr

    after = _run_check_gates(status_out, "missing_gate")
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    assert after.stderr == before.stderr

    original = json.loads(status_path.read_text(encoding="utf-8"))
    folded = json.loads(status_out.read_text(encoding="utf-8"))
    assert folded["gates"] == original["gates"]


def test_neutral_absence_path_does_not_change_release_outcome(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"
    missing_input = tmp_path / "missing_input.json"

    status_payload = _minimal_status()
    status_payload["meta"]["relational_gain_shadow"] = {
        "verdict": "WARN",
        "max_edge_gain": 0.97,
        "max_cycle_gain": 0.91,
        "warn_threshold": 0.95,
        "checked_edges": 3,
        "checked_cycles": 2,
        "artifact": {
            "path": "old/path.json",
            "sha256": "oldhash",
        },
    }
    _write_json(status_path, status_payload)
    artifact_out.write_text('{"stale": true}\n', encoding="utf-8")

    before = _run_check_gates(status_path, "gate_ok")
    assert before.returncode == 0, before.stdout + before.stderr

    runner = _run_runner(
        status_path,
        missing_input,
        artifact_out=artifact_out,
        status_out=status_out,
        if_input_present=True,
    )
    assert runner.returncode == 0, runner.stdout + runner.stderr

    after = _run_check_gates(status_out, "gate_ok")
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    assert after.stderr == before.stderr

    folded = json.loads(status_out.read_text(encoding="utf-8"))
    assert folded["gates"] == status_payload["gates"]
    assert "relational_gain_shadow" not in folded.get("meta", {})
    assert folded["meta"]["existing_shadow"] == {"note": "preserve me"}
