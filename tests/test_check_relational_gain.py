from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_relational_gain.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "relational_gain_v0"


def _run_checker(input_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--input",
            str(input_path),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_exit", "expected_verdict"),
    [
        ("pass.json", 0, "PASS"),
        ("warn.json", 0, "WARN"),
        ("fail_edge.json", 1, "FAIL"),
        ("fail_cycle.json", 1, "FAIL"),
    ],
)
def test_relational_gain_fixtures(
    fixture_name: str,
    expected_exit: int,
    expected_verdict: str,
) -> None:
    result = _run_checker(FIXTURES / fixture_name)

    assert result.returncode == expected_exit, result.stderr
    payload = json.loads(result.stdout)

    assert payload["verdict"] == expected_verdict
    assert payload["checker_version"] == "relational_gain_v0"
    assert "metrics" in payload
    assert "checked_edges" in payload["metrics"]
    assert "checked_cycles" in payload["metrics"]


def test_writes_output_artifact(tmp_path: Path) -> None:
    out_path = tmp_path / "relational_gain_shadow_v0.json"

    result = _run_checker(FIXTURES / "pass.json", "--out", str(out_path))

    assert result.returncode == 0, result.stderr
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["checker_version"] == "relational_gain_v0"
    assert payload["input"]["path"].endswith("pass.json")


def test_mixed_schema_sources_are_combined(tmp_path: Path) -> None:
    input_path = tmp_path / "mixed_schema.json"
    input_path.write_text(
        json.dumps(
            {
                "edge_gains": [0.42, 0.88],
                "metrics": {
                    "relational_gain": {
                        "cycle_gains": [0.73, 1.04],
                    },
                    "relational_gain_warn_threshold": 0.95,
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run_checker(input_path)

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)

    assert payload["verdict"] == "FAIL"
    assert payload["metrics"]["max_edge_gain"] == 0.88
    assert payload["metrics"]["max_cycle_gain"] == 1.04
    assert payload["metrics"]["checked_edges"] == 2
    assert payload["metrics"]["checked_cycles"] == 2


def test_duplicate_key_locations_fail_closed(tmp_path: Path) -> None:
    input_path = tmp_path / "ambiguous_schema.json"
    input_path.write_text(
        json.dumps(
            {
                "edge_gains": [0.42],
                "metrics": {
                    "relational_gain": {
                        "edge_gains": [1.08],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run_checker(input_path)

    assert result.returncode == 2
    assert "ambiguous schema" in result.stderr


def test_require_data_fails_when_no_gain_lists_are_present(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.json"
    input_path.write_text(json.dumps({"metrics": {}}), encoding="utf-8")

    result = _run_checker(input_path, "--require-data")

    assert result.returncode == 2
    assert "no relational gain data found" in result.stderr
