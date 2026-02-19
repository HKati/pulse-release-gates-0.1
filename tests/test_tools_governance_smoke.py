#!/usr/bin/env python3
"""
Governance tools smoke tests.

Goal:
- Ensure repo-level governance checks run in CI without depending on the PULSE pack.
- Lock down fail-closed semantics (negative cases) so regressions can't slip through.

We intentionally run tools as subprocesses (as CI does) and assert return codes.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
POLICY = ROOT / "pulse_gate_policy_v0.yml"

TOOL_REG_SYNC = ROOT / "tools" / "check_gate_registry_sync.py"
TOOL_POLICY_REG = ROOT / "tools" / "tools" / "check_policy_registry_consistency.py"


def run_ok(cmd: list[str]) -> None:
    subprocess.check_call(cmd, cwd=str(ROOT))


def run_rc(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)


def assert_rc(res: subprocess.CompletedProcess[str], expected: int) -> None:
    if res.returncode != expected:
        raise AssertionError(
            "Unexpected return code\n"
            f"expected={expected} got={res.returncode}\n"
            "=== STDOUT ===\n"
            f"{res.stdout}\n"
            "=== STDERR ===\n"
            f"{res.stderr}\n"
        )


def _write_status(path: Path, gates: dict) -> None:
    status = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": gates,
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_gate_registry_sync_smoke() -> None:
    """Happy path: registry covers all gates in fixture."""
    assert TOOL_REG_SYNC.is_file(), f"Missing tool: {TOOL_REG_SYNC}"
    assert REGISTRY.is_file(), f"Missing registry: {REGISTRY}"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        status_path = td / "status.json"
        _write_status(
            status_path,
            {
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
                "psf_monotonicity_ok": True,
                "external_all_pass": True,
                "refusal_delta_pass": True,
            },
        )

        run_ok(
            [
                sys.executable,
                str(TOOL_REG_SYNC),
                "--status",
                str(status_path),
                "--registry",
                str(REGISTRY),
            ]
        )


def test_gate_registry_sync_fails_on_unknown_gate() -> None:
    """Negative: an unknown gate in status must fail closed (exit 2)."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        status_path = td / "status.json"
        _write_status(
            status_path,
            {
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
                "definitely_missing_gate_xyz": True,  # not in registry
            },
        )

        res = run_rc(
            [
                sys.executable,
                str(TOOL_REG_SYNC),
                "--status",
                str(status_path),
                "--registry",
                str(REGISTRY),
            ]
        )
        assert_rc(res, 2)
        out = (res.stdout or "") + (res.stderr or "")
        assert "definitely_missing_gate_xyz" in out


def test_policy_registry_consistency_smoke() -> None:
    """Happy path: repo default policy/registry is consistent for required set."""
    assert TOOL_POLICY_REG.is_file(), f"Missing tool: {TOOL_POLICY_REG}"
    assert REGISTRY.is_file(), f"Missing registry: {REGISTRY}"
    assert POLICY.is_file(), f"Missing policy: {POLICY}"

    run_ok(
        [
            sys.executable,
            str(TOOL_POLICY_REG),
            "--registry",
            str(REGISTRY),
            "--policy",
            str(POLICY),
            "--sets",
            "required",
        ]
    )


def test_policy_registry_rejects_missing_gate() -> None:
    """Negative: policy referencing a missing gate must fail closed (exit 2)."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        policy_path = td / "policy_missing_gate.yml"

        policy_path.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test-policy
                  version: "0.0.0"
                gates:
                  required:
                    - missing_gate_foo
                  advisory: []
                """
            ),
            encoding="utf-8",
        )

        res = run_rc(
            [
                sys.executable,
                str(TOOL_POLICY_REG),
                "--registry",
                str(REGISTRY),
                "--policy",
                str(policy_path),
                "--sets",
                "required",
            ]
        )
        assert_rc(res, 2)
        out = (res.stdout or "") + (res.stderr or "")
        assert "missing_gate_foo" in out


def test_policy_registry_rejects_non_normative_required_gate() -> None:
    """
    Negative: policy requiring a default_non_normative gate must fail closed (exit 2).
    We use epf_hazard_ok which is marked default_normative: false in the registry.
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        policy_path = td / "policy_non_normative.yml"

        policy_path.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test-policy
                  version: "0.0.0"
                gates:
                  required:
                    - epf_hazard_ok
                  advisory: []
                """
            ),
            encoding="utf-8",
        )

        res = run_rc(
            [
                sys.executable,
                str(TOOL_POLICY_REG),
                "--registry",
                str(REGISTRY),
                "--policy",
                str(policy_path),
                "--sets",
                "required",
            ]
        )
        assert_rc(res, 2)
        out = (res.stdout or "") + (res.stderr or "")
        assert "epf_hazard_ok" in out


def main() -> int:
    test_gate_registry_sync_smoke()
    test_gate_registry_sync_fails_on_unknown_gate()
    test_policy_registry_consistency_smoke()
    test_policy_registry_rejects_missing_gate()
    test_policy_registry_rejects_non_normative_required_gate()
    print("OK: governance tools smoke tests passed")
    return 0


def test_smoke() -> None:
    # pytest entrypoint (optional)
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
