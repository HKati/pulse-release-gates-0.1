from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPTS_DIR = REPO_ROOT / "scripts"
SCHEMAS_DIR = REPO_ROOT / "schemas"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "paradox_diagram_v0"

BUILDER = SCRIPTS_DIR / "paradox_diagram_from_core_v0.py"
CONTRACT = SCRIPTS_DIR / "check_paradox_diagram_v0_contract.py"
SCHEMA = SCHEMAS_DIR / "PULSE_paradox_diagram_v0.schema.json"

CORE_FIXTURE_REL = Path("tests/fixtures/paradox_diagram_v0/core_k2.json")
EXPECTED_FIXTURE = FIXTURES_DIR / "expected_paradox_diagram_v0.json"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _canon_json(obj: object) -> str:
    # Canonical dump for stable diffs in asserts
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _assert_json_equal(actual: object, expected: object, *, label: str) -> None:
    if actual == expected:
        return

    a = _canon_json(actual).splitlines(keepends=True)
    e = _canon_json(expected).splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            e,
            a,
            fromfile=f"expected:{label}",
            tofile=f"actual:{label}",
        )
    )
    raise AssertionError(f"JSON mismatch for {label}:\n{diff}")


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_paradox_diagram_v0_builder_and_contract(tmp_path: Path) -> None:
    # Preconditions
    assert BUILDER.exists(), f"Missing builder script: {BUILDER}"
    assert CONTRACT.exists(), f"Missing contract script: {CONTRACT}"
    assert SCHEMA.exists(), f"Missing schema: {SCHEMA}"
    assert EXPECTED_FIXTURE.exists(), f"Missing expected fixture: {EXPECTED_FIXTURE}"

    core_abs = (REPO_ROOT / CORE_FIXTURE_REL).resolve()
    assert core_abs.exists(), f"Missing core fixture: {core_abs}"

    # Load expected fixture
    expected_obj = json.loads(EXPECTED_FIXTURE.read_text(encoding="utf-8"))

    # Fail-closed guard: expected fixture must record the real core_k2.json SHA-256
    expected_sha = (
        expected_obj.get("inputs", {})
        .get("paradox_core_v0", {})
        .get("sha256")
    )
    actual_sha = _sha256_hex(core_abs)
    assert expected_sha == actual_sha, (
        "Expected fixture core SHA-256 mismatch:\n"
        f" - expected fixture: {expected_sha}\n"
        f" - actual core_k2.json: {actual_sha}\n"
        "Update tests/fixtures/paradox_diagram_v0/expected_paradox_diagram_v0.json inputs.paradox_core_v0.sha256"
    )

    # Generate diagram via builder (use RELATIVE core path to keep path_hint stable)
    out_path = tmp_path / "paradox_diagram_v0.generated.json"

    cmd_build = [
        sys.executable,
        str(BUILDER),
        "--core",
        str(CORE_FIXTURE_REL.as_posix()),
        "--out",
        str(out_path),
    ]
    res = _run(cmd_build, cwd=REPO_ROOT)
    assert res.returncode == 0, (
        "Builder failed:\n"
        f"cmd: {' '.join(cmd_build)}\n"
        f"stdout:\n{res.stdout}\n"
        f"stderr:\n{res.stderr}\n"
    )
    assert out_path.exists(), "Builder did not produce output file."

    actual_obj = json.loads(out_path.read_text(encoding="utf-8"))

    # Compare generated JSON to expected canonical fixture
    _assert_json_equal(actual_obj, expected_obj, label="paradox_diagram_v0")

    # Contract check on generated output
    cmd_contract_gen = [
        sys.executable,
        str(CONTRACT),
        "--in",
        str(out_path),
        "--schema",
        str(SCHEMA),
    ]
    res2 = _run(cmd_contract_gen, cwd=REPO_ROOT)
    assert res2.returncode == 0, (
        "Contract check failed on generated output:\n"
        f"cmd: {' '.join(cmd_contract_gen)}\n"
        f"stdout:\n{res2.stdout}\n"
        f"stderr:\n{res2.stderr}\n"
    )

    # Contract check on expected fixture as well (keeps fixtures honest)
    cmd_contract_exp = [
        sys.executable,
        str(CONTRACT),
        "--in",
        str(EXPECTED_FIXTURE),
        "--schema",
        str(SCHEMA),
    ]
    res3 = _run(cmd_contract_exp, cwd=REPO_ROOT)
    assert res3.returncode == 0, (
        "Contract check failed on expected fixture:\n"
        f"cmd: {' '.join(cmd_contract_exp)}\n"
        f"stdout:\n{res3.stdout}\n"
        f"stderr:\n{res3.stderr}\n"
    )
