#!/usr/bin/env python3
"""Workflow-static release-grade reference qualification boundary checks.

This test locks the release-grade reference qualification step as advisory /
non-normative / non-blocking review support.

It does not change workflow behavior. It statically verifies that the
qualification step does not become the primary artifact-bound
release-authority path.
"""

from __future__ import annotations

import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"
PYTEST_TESTS_LIST = REPO_ROOT / "ci" / "pytest-tests.list"

THIS_TEST_PATH = "tests/test_release_grade_reference_qualification_advisory_boundary_v0.py"


def _workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), f"Missing workflow: {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _extract_step(workflow: str, step_name: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*-\s+name:\s+{re.escape(step_name)}\s*$.*?"
        rf"(?=^\s*-\s+name:\s+|\Z)"
    )
    match = pattern.search(workflow)
    assert match is not None, f"Missing workflow step: {step_name}"
    return match.group(0)


def _assert_contains_all(text: str, required: list[str], label: str) -> None:
    missing = [item for item in required if item not in text]
    assert not missing, f"{label} is missing expected tokens: {missing}"


def _assert_not_contains_any(text: str, forbidden: list[str], label: str) -> None:
    present = [item for item in forbidden if item in text]
    assert not present, f"{label} contains forbidden tokens: {present}"


def _manifest_entries(path: pathlib.Path) -> list[str]:
    assert path.is_file(), f"Missing CI manifest: {path}"
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _assert_manifest_entry_once(path: pathlib.Path, entry: str) -> None:
    entries = _manifest_entries(path)
    count = entries.count(entry)
    assert count == 1, f"{entry} appears {count} times in {path}"


def _assert_failure_branch_exits_zero(qualification_step: str) -> None:
    """Lock CHECK_RC != 0 failure behavior to warning-only exit 0.

    This intentionally does not accept unrelated exit 0 skip branches.
    The exit-zero assertion is anchored to the checker failure branch that
    emits the release-grade qualification warning.
    """

    warning = (
        "::warning::release-grade reference qualification failed; "
        "release outcome unchanged"
    )
    lines = qualification_step.splitlines()

    warning_idx = next(
        (idx for idx, line in enumerate(lines) if warning in line),
        None,
    )
    assert warning_idx is not None, (
        "release-grade qualification failure warning is missing"
    )

    branch_start_candidates = [
        idx
        for idx, line in enumerate(lines[: warning_idx + 1])
        if "CHECK_RC" in line and "-ne" in line and "0" in line and "if" in line
    ]
    assert branch_start_candidates, (
        "could not find CHECK_RC != 0 failure branch before warning"
    )

    branch_start = branch_start_candidates[-1]

    branch_end = next(
        (
            idx
            for idx, line in enumerate(lines[warning_idx + 1 :], start=warning_idx + 1)
            if re.match(r"^\s*fi\s*$", line)
        ),
        len(lines),
    )

    failure_branch_after_warning = lines[warning_idx + 1 : branch_end]

    first_exit = next(
        (line.strip() for line in failure_branch_after_warning if "exit " in line),
        None,
    )
    assert first_exit is not None, (
        "CHECK_RC != 0 failure branch must contain an explicit exit"
    )
    assert first_exit == "exit 0", (
        "CHECK_RC != 0 failure branch must exit 0, "
        f"but first exit was: {first_exit!r}"
    )


def _assert_actual_check_gates_enforcement_step(enforcement_step: str) -> None:
    """Lock the real policy-derived check_gates enforcement step.

    This must not accidentally match a later reporting/export step that only
    mentions check_gates.py in summary text.
    """

    _assert_contains_all(
        enforcement_step,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
            "--status",
            "--require",
        ],
        "policy-derived check_gates.py enforcement step",
    )

    assert any(
        "check_gates.py" in line and ("python" in line or "$PYTHON" in line)
        for line in enforcement_step.splitlines()
    ), (
        "policy-derived enforcement step must invoke check_gates.py with Python, "
        "not merely mention it in summary text"
    )


def test_release_grade_reference_qualification_is_advisory_boundary_v0() -> None:
    workflow = _workflow_text()

    qualification_step = _extract_step(
        workflow,
        "Check release-grade reference run qualification (advisory)",
    )
    enforcement_step = _extract_step(
        workflow,
        "ci: enforce gates via check_gates (policy-derived)",
    )

    _assert_contains_all(
        qualification_step,
        [
            "check_release_grade_reference_run_v0.py",
            "--status",
            "--manifest",
            "--report",
            "--audit-bundle-dir",
            "CHECK_RC",
            "::warning::release-grade reference qualification failed; release outcome unchanged",
        ],
        "release-grade reference qualification step",
    )
    _assert_failure_branch_exits_zero(qualification_step)

    qualification_step_l = qualification_step.lower()
    _assert_contains_all(
        qualification_step_l,
        [
            "advisory",
            "non-normative",
            "non-blocking",
            "release outcome unchanged",
        ],
        "release-grade reference qualification boundary wording",
    )

    # The qualification step may consume audit-bundle input as qualification /
    # traceability input, but it must not become the release enforcement path.
    _assert_not_contains_any(
        qualification_step,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
            "--release-grade-materialized",
            "artifact_provenance_binding_v0.json",
            "build_artifact_provenance_binding_v0.py",
            "verify_artifact_provenance_binding_v0.py",
            "gate_materialization",
            "materialized required gate set",
            "release eligibility",
            "--out",
            "--output",
        ],
        "release-grade reference qualification step",
    )

    _assert_actual_check_gates_enforcement_step(enforcement_step)

    _assert_not_contains_any(
        enforcement_step,
        [
            "release_authority_audit_bundle",
            "release-authority-audit-bundle",
            "--audit-bundle-dir",
            "check_release_grade_reference_run_v0.py",
        ],
        "policy-derived check_gates.py enforcement step",
    )

    _assert_contains_all(
        workflow,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
        ],
        "canonical policy-derived check_gates.py enforcement path",
    )


def test_release_grade_reference_advisory_boundary_test_is_wired_into_ci_manifests() -> None:
    _assert_manifest_entry_once(TOOLS_TESTS_LIST, THIS_TEST_PATH)
    _assert_manifest_entry_once(PYTEST_TESTS_LIST, THIS_TEST_PATH)


def main() -> int:
    try:
        test_release_grade_reference_qualification_is_advisory_boundary_v0()
        test_release_grade_reference_advisory_boundary_test_is_wired_into_ci_manifests()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: release-grade reference qualification advisory boundary locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
