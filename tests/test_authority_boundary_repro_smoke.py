#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPRO_ROOT = ROOT / "studies" / "authority-boundary" / "repro"
CASES_DIR = REPRO_ROOT / "cases"
EXPECTED_DIR = REPRO_ROOT / "expected"
SCHEMA = ROOT / "schemas" / "status" / "status_v1.schema.json"
POLICY = ROOT / "pulse_gate_policy_v0.yml"
POLICY_SET = "core_required"
VALIDATE_TOOL = ROOT / "tools" / "validate_status_schema.py"
POLICY_TOOL = ROOT / "tools" / "policy_to_require_args.py"
CHECK_GATES_TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"

SCHEMA_VALID_CASES = [
    "core_pass",
    "core_missing_q4",
    "core_false_q4",
    "core_diag_variant_a",
    "core_diag_variant_b",
]
SCHEMA_INVALID_CASE = "schema_invalid_non_boolean_gate"
EXPECTED_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "pass_controls_refusal",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PULSE_STATUS", None)
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )


def _combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in [proc.stdout or "", proc.stderr or ""] if part)


def _assert_rc(proc: subprocess.CompletedProcess[str], expected: int) -> None:
    if proc.returncode != expected:
        raise AssertionError(
            f"Unexpected return code: expected={expected} got={proc.returncode}\n"
            f"CMD: {' '.join(proc.args) if isinstance(proc.args, list) else proc.args}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}\n"
        )


def _load_expected(case_name: str) -> dict[str, Any]:
    path = EXPECTED_DIR / f"{case_name}.expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _status_path(case_name: str) -> pathlib.Path:
    return CASES_DIR / f"{case_name}.status.json"


def _assert_expected_streams(
    proc: subprocess.CompletedProcess[str], expected_block: dict[str, Any]
) -> None:
    if "stdout_exact" in expected_block:
        assert (proc.stdout or "").strip() == expected_block["stdout_exact"]
    if "stdout_contains" in expected_block:
        stdout = proc.stdout or ""
        for needle in expected_block["stdout_contains"]:
            assert needle in stdout, f"Missing stdout fragment: {needle!r}\n{stdout}"
    if "stderr_exact" in expected_block:
        assert (proc.stderr or "").strip() == expected_block["stderr_exact"]
    if "stderr_contains" in expected_block:
        stderr = proc.stderr or ""
        for needle in expected_block["stderr_contains"]:
            assert needle in stderr, f"Missing stderr fragment: {needle!r}\n{stderr}"


def _validate_status(status_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    rel_status = status_path.relative_to(ROOT)
    rel_schema = SCHEMA.relative_to(ROOT)
    return _run(
        [
            sys.executable,
            str(VALIDATE_TOOL),
            "--schema",
            str(rel_schema),
            "--status",
            str(rel_status),
        ]
    )


def _materialize_required() -> subprocess.CompletedProcess[str]:
    rel_policy = POLICY.relative_to(ROOT)
    return _run(
        [
            sys.executable,
            str(POLICY_TOOL),
            "--policy",
            str(rel_policy),
            "--set",
            POLICY_SET,
            "--format",
            "space",
        ]
    )


def _evaluate(
    status_path: pathlib.Path, required: list[str]
) -> subprocess.CompletedProcess[str]:
    rel_status = status_path.relative_to(ROOT)
    return _run(
        [
            sys.executable,
            str(CHECK_GATES_TOOL),
            "--status",
            str(rel_status),
            "--require",
            *required,
        ]
    )


def _assert_repo_paths_exist() -> None:
    assert VALIDATE_TOOL.is_file(), f"Missing tool: {VALIDATE_TOOL}"
    assert POLICY_TOOL.is_file(), f"Missing tool: {POLICY_TOOL}"
    assert CHECK_GATES_TOOL.is_file(), f"Missing tool: {CHECK_GATES_TOOL}"
    assert SCHEMA.is_file(), f"Missing schema: {SCHEMA}"
    assert POLICY.is_file(), f"Missing policy: {POLICY}"


def _assert_schema_valid_case(case_name: str) -> None:
    expected_doc = _load_expected(case_name)
    expected = expected_doc["expected"]
    status_path = _status_path(case_name)

    assert expected_doc["canonical_study_pin"]["policy_set"] == POLICY_SET

    validate_proc = _validate_status(status_path)
    _assert_rc(validate_proc, expected["schema_validation"]["exit_code"])
    _assert_expected_streams(validate_proc, expected["schema_validation"])

    policy_proc = _materialize_required()
    _assert_rc(policy_proc, expected["policy_materialization"]["exit_code"])
    _assert_expected_streams(policy_proc, expected["policy_materialization"])

    required = (policy_proc.stdout or "").strip().split()
    assert required == EXPECTED_REQUIRED_GATES, (
        f"Unexpected required gate list:\n"
        f"expected={EXPECTED_REQUIRED_GATES}\n"
        f"got={required}"
    )

    eval_proc = _evaluate(status_path, required)
    _assert_rc(eval_proc, expected["gate_evaluation"]["exit_code"])
    _assert_expected_streams(eval_proc, expected["gate_evaluation"])


def test_authority_boundary_repro_smoke() -> None:
    _assert_repo_paths_exist()

    for case_name in SCHEMA_VALID_CASES:
        _assert_schema_valid_case(case_name)

    expected_doc = _load_expected(SCHEMA_INVALID_CASE)
    expected = expected_doc["expected"]
    status_path = _status_path(SCHEMA_INVALID_CASE)

    assert expected_doc["canonical_study_pin"]["policy_set"] == POLICY_SET

    validate_proc = _validate_status(status_path)
    _assert_rc(validate_proc, expected["schema_validation"]["exit_code"])
    _assert_expected_streams(validate_proc, expected["schema_validation"])

    assert expected["policy_materialization"]["skipped"] is True
    assert expected["gate_evaluation"]["skipped"] is True


def test_authority_boundary_repro_diagnostic_non_override_pair() -> None:
    variant_a = json.loads(_status_path("core_diag_variant_a").read_text(encoding="utf-8"))
    variant_b = json.loads(_status_path("core_diag_variant_b").read_text(encoding="utf-8"))

    assert variant_a["gates"] == variant_b["gates"]

    eval_a = _evaluate(_status_path("core_diag_variant_a"), EXPECTED_REQUIRED_GATES)
    eval_b = _evaluate(_status_path("core_diag_variant_b"), EXPECTED_REQUIRED_GATES)

    _assert_rc(eval_a, 0)
    _assert_rc(eval_b, 0)
    assert (eval_a.stdout or "").strip() == (eval_b.stdout or "").strip()
    assert (eval_a.stderr or "").strip() == (eval_b.stderr or "").strip()


def main() -> int:
    try:
        test_authority_boundary_repro_smoke()
        test_authority_boundary_repro_diagnostic_non_override_pair()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: authority-boundary repro smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
