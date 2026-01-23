import json
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path() -> Path:
    return _repo_root() / "scripts" / "check_paradox_pages_source_v0_contract.py"


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_checker(in_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_script_path()), "--in", str(in_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _valid_obj() -> dict:
    return {
        "schema": "PULSE_paradox_pages_source_v0",
        "version": "v0",
        "upstream_run_id": "1234567890",
        "source": "case_study",
        "transitions_dir": "docs/examples/transitions_case_study_v0",
    }


def test_pages_source_v0_contract_ok(tmp_path: Path) -> None:
    p = tmp_path / "source_v0.json"
    _write_json(p, _valid_obj())

    r = _run_checker(p)
    assert r.returncode == 0, f"stdout:\n{r.stdout}\n\nstderr:\n{r.stderr}"
    assert "OK: source_v0 contract holds" in r.stdout


@pytest.mark.parametrize(
    "mutate, expected_err",
    [
        (lambda o: (o.pop("transitions_dir"), o)[1], "missing required keys"),
        (lambda o: (o.__setitem__("extra", 1), o)[1], "unexpected extra keys"),
        (lambda o: (o.__setitem__("schema", "WRONG"), o)[1], "schema must be"),
        (lambda o: (o.__setitem__("version", "v999"), o)[1], "version must be"),
        (lambda o: (o.__setitem__("source", "evil"), o)[1], "source must be one of"),
        (lambda o: (o.__setitem__("upstream_run_id", "   "), o)[1], "upstream_run_id must be a non-empty string"),
        (lambda o: (o.__setitem__("transitions_dir", ""), o)[1], "transitions_dir must be a non-empty string"),
        (lambda o: (o.__setitem__("transitions_dir", "ok\u0000bad"), o)[1], "contains NUL byte"),
    ],
)
def test_pages_source_v0_contract_fail_closed(tmp_path: Path, mutate, expected_err: str) -> None:
    obj = _valid_obj()
    obj = mutate(obj)

    p = tmp_path / "source_v0.json"
    _write_json(p, obj)

    r = _run_checker(p)
    assert r.returncode != 0, f"expected failure, got rc=0; stdout:\n{r.stdout}\n\nstderr:\n{r.stderr}"
    assert "CONTRACT FAIL:" in r.stderr
    assert expected_err in r.stderr
