#!/usr/bin/env python3
"""
Smoke test for tools/policy_to_require_args.py.

Locks down:
- multiline list parsing
- inline list parsing
- advisory optional behavior (missing/empty => rc 0, no output)
- all non-advisory gate sets fail closed when missing/empty
- arbitrary declared gate-set materialization
- repository SLSA VSA candidate-set materialization
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
REPO_POLICY = ROOT / "pulse_gate_policy_v0.yml"

EXPECTED_SLSA_VSA_CANDIDATE = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]


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
        td_path = pathlib.Path(td)

        # 1) Happy path: multiline required + inline core_required +
        # inline release_required + empty advisory + arbitrary declared set.
        policy1 = td_path / "policy1.yml"
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
                  release_required: [gate_rel_a, gate_rel_b]
                  custom_candidate:
                    - candidate_a
                    - candidate_b
                  inline_candidate: [inline_a, inline_b]
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

        p = _run(policy1, "release_required", "newline")
        _assert_rc(p, 0)
        assert _stdout_lines(p) == ["gate_rel_a", "gate_rel_b"]

        p = _run(policy1, "custom_candidate", "newline")
        _assert_rc(p, 0)
        assert _stdout_lines(p) == ["candidate_a", "candidate_b"]

        p = _run(policy1, "inline_candidate", "space")
        _assert_rc(p, 0)
        assert (p.stdout or "").strip() == "inline_a inline_b"

        p = _run(policy1, "advisory", "newline")
        _assert_rc(p, 0)
        assert (p.stdout or "").strip() == ""

        # 2) Advisory missing key is OK (rc 0, no output).
        policy2 = td_path / "policy2.yml"
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

        # 3) Missing non-advisory set => fail closed (non-zero).
        policy3 = td_path / "policy3_missing_required.yml"
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

        p = _run(policy3, "custom_candidate", "newline")
        _assert_rc(p, 3)
        assert "Gate set not found: custom_candidate" in (p.stderr or "")

        # 4) Empty non-advisory set => fail closed (non-zero).
        policy4 = td_path / "policy4_empty_required.yml"
        policy4.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required: []
                  core_required: [gate_a]
                  custom_candidate: []
                  advisory: []
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy4, "required", "newline")
        _assert_rc(p, 3)

        p = _run(policy4, "custom_candidate", "newline")
        _assert_rc(p, 3)
        assert "Gate set is empty: custom_candidate" in (p.stderr or "")

        # 5) release_required missing set => fail closed (non-zero).
        policy5 = td_path / "policy5_missing_release_required.yml"
        policy5.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required: [gate_x, gate_y]
                  core_required: [gate_x]
                  advisory: [note_only]
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy5, "release_required", "newline")
        _assert_rc(p, 3)

        # 6) release_required empty => fail closed (non-zero).
        policy6 = td_path / "policy6_empty_release_required.yml"
        policy6.write_text(
            textwrap.dedent(
                """\
                policy:
                  id: test
                  version: "0.0.0"
                gates:
                  required: [gate_x, gate_y]
                  core_required: [gate_x]
                  release_required: []
                  advisory: []
                """
            ),
            encoding="utf-8",
        )
        p = _run(policy6, "release_required", "newline")
        _assert_rc(p, 3)

        # 7) Policy file not found => rc 2.
        missing = td_path / "does_not_exist.yml"
        p = _run(missing, "required", "newline")
        _assert_rc(p, 2)


def test_repository_slsa_vsa_candidate_set_materializes() -> None:
    assert REPO_POLICY.is_file(), f"Missing policy at: {REPO_POLICY}"

    p = _run(REPO_POLICY, "slsa_vsa_recorded_intake_candidate", "newline")
    _assert_rc(p, 0)
    assert _stdout_lines(p) == EXPECTED_SLSA_VSA_CANDIDATE


def main() -> int:
    try:
        test_policy_to_require_args_smoke()
        test_repository_slsa_vsa_candidate_set_materializes()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: policy_to_require_args smoke passed")
    return 0


def test_smoke() -> None:
    # Optional pytest entrypoint.
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
