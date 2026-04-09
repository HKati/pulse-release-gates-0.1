from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_relational_gain_shadow.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "relational_gain_v0"


def _run_runner(
    status_path: Path,
    input_path: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--status",
            str(status_path),
            "--input",
            str(input_path),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _minimal_status() -> dict[str, Any]:
    return {
        "schema_version": "status_v0",
        "gates": {
            "pass": True,
        },
        "meta": {
            "existing_shadow": {
                "note": "preserve me",
            }
        },
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pass_fixture_runs_and_folds_shadow_result(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    result = _run_runner(
        status_path,
        FIXTURES / "pass.json",
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    )

    assert result.returncode == 0, result.stderr
    assert artifact_out.exists()
    assert status_out.exists()

    folded = json.loads(status_out.read_text(encoding="utf-8"))
    rg = folded["meta"]["relational_gain_shadow"]

    assert rg["verdict"] == "PASS"
    assert rg["max_edge_gain"] == 0.88
    assert rg["max_cycle_gain"] == 0.79
    assert rg["warn_threshold"] == 0.95
    assert rg["checked_edges"] == 3
    assert rg["checked_cycles"] == 2
    assert rg["artifact"]["path"] == str(artifact_out)
    assert rg["artifact"]["sha256"] == _sha256_file(artifact_out)

    assert folded["meta"]["existing_shadow"] == {"note": "preserve me"}
    assert folded["gates"] == {"pass": True}


def test_warn_fixture_runs_and_folds_warn_result(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    result = _run_runner(
        status_path,
        FIXTURES / "warn.json",
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    )

    assert result.returncode == 0, result.stderr
    folded = json.loads(status_out.read_text(encoding="utf-8"))

    rg = folded["meta"]["relational_gain_shadow"]
    assert rg["verdict"] == "WARN"
    assert rg["max_edge_gain"] == 0.97
    assert rg["max_cycle_gain"] == 0.91


def test_fail_fixture_remains_shadow_and_runner_exits_zero(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())

    result = _run_runner(
        status_path,
        FIXTURES / "fail_edge.json",
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    )

    # FAIL is a valid shadow outcome here; runner success means orchestration succeeded.
    assert result.returncode == 0, result.stderr

    folded = json.loads(status_out.read_text(encoding="utf-8"))
    rg = folded["meta"]["relational_gain_shadow"]

    assert rg["verdict"] == "FAIL"
    assert rg["max_edge_gain"] == 1.08
    assert rg["max_cycle_gain"] == 0.91


def test_missing_input_without_if_input_present_fails_closed(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    missing_input = tmp_path / "missing_input.json"

    _write_json(status_path, _minimal_status())

    result = _run_runner(status_path, missing_input)

    assert result.returncode == 2
    assert "relational gain input not found" in result.stderr


def test_if_input_present_missing_input_clears_stale_shadow_and_stale_artifact(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    missing_input = tmp_path / "missing_input.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

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

    result = _run_runner(
        status_path,
        missing_input,
        "--if-input-present",
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    )

    assert result.returncode == 0, result.stderr
    assert not artifact_out.exists()

    folded = json.loads(status_out.read_text(encoding="utf-8"))
    assert "relational_gain_shadow" not in folded.get("meta", {})
    assert folded["meta"]["existing_shadow"] == {"note": "preserve me"}


def test_require_data_bubbles_up_checker_error(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    status_out = tmp_path / "status.out.json"
    input_path = tmp_path / "empty_input.json"
    artifact_out = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())
    _write_json(input_path, {"metrics": {}})

    result = _run_runner(
        status_path,
        input_path,
        "--require-data",
        "--artifact-out",
        str(artifact_out),
        "--status-out",
        str(status_out),
    )

    assert result.returncode == 2
    assert "no relational gain data found" in result.stderr
    assert not status_out.exists()
