#!/usr/bin/env python3
"""
Smoke test for tools/policy_to_require_args.py

Locks down:
- multiline list parsing
- inline list parsing
- advisory optional behavior (missing/empty => rc 0, no output)
- required/core_required fail-closed behavior (missing/empty => non-zero)
- file-not-found exit code
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "policy_to_require_args.py"


def _run(policy_path: pathlib.Path, gate_set: str, fmt: str = "newline") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--policy",
            str(policy_path),
            "--set",
            gate_set,
            "--format",
            fmt,
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_rc(p: subprocess.CompletedProcess[str], expected: int) -> None:
    if p.returncode != expected:
        raise AssertionError(
            f"Unexpected return code: expected={expected} got={p.returncode}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def _stdout_lines(p: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()]


def test_policy_to_require_args_smoke() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # 1) Happy path: multiline required + inline core_required + empty advisory
        policy1 = td / "policy1.yml"
        policy1.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required:
                    - gate_a
                    - gate_b  # inline comment should be ignored
                  core_required: [gate_a]
                  advisory: []
                """
            ),
            encoding="utf-8",
        )

        p = _run(policy1, "required", "newline")
        _assert_rc(p, 0)
        assert _stdout_lines(p) == ["gate_a", "gate_b"]

        p = _run(policy1, "core_required", "space")
        _assert_rc(p, 0)
        assert (p.stdout or "").strip() == "gate_a"

        p = _run(policy1, "advisory", "newline")
        _assert_rc(p, 0)
        assert (p.stdout or "").strip() == ""

        # 2) Advisory missing key is OK (rc 0, no output)
        policy2 = td / "policy2.yml"
        policy2.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required: [gate_x, gate_y]
                  core_required: [gate_x]
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy2, "advisory", "newline")
        _assert_rc(p, 0)
        assert (p.stdout or "").strip() == ""

        # 3) Required missing set => fail closed (non-zero)
        policy3 = td / "policy3_missing_required.yml"
        policy3.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  core_required: [gate_a]
                  advisory: [note_only]
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy3, "required", "newline")
        _assert_rc(p, 3)

        # 4) Required empty => fail closed (non-zero)
        policy4 = td / "policy4_empty_required.yml"
        policy4.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required: []
                  core_required: [gate_a]
                  advisory: []
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy4, "required", "newline")
        _assert_rc(p, 3)

        # 5) Policy file not found => rc 2
        missing = td / "does_not_exist.yml"
        p = _run(missing, "required", "newline")
        _assert_rc(p, 2)


def main() -> int:
    try:
        test_policy_to_require_args_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: policy_to_require_args smoke passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
