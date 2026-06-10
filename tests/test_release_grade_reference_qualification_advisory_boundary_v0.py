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


def _extract_steps_containing(
    workflow: str,
    required_tokens: list[str],
) -> list[str]:
    step_pattern = re.compile(
        r"(?ms)^\s*-\s+name:\s+.*?$.*?(?=^\s*-\s+name:\s+|\Z)"
    )
    return [
        match.group(0)
        for match in step_pattern.finditer(workflow)
        if all(token in match.group(0) for token in required_tokens)
    ]


def _assert_contains_all(text: str, required: list[str], label: str) -> None:
    missing = [item for item in required if item not in text]
    assert not missing, f"{label} is missing expected tokens: {missing}"


def _assert_not_contains_any(text: str, forbidden: list[str], label: str) -> None:
    present = [item for item in forbidden if item in text]
    assert not present, f"{label} contains forbidden tokens: {present}"


def test_release_grade_reference_qualification_is_advisory_boundary_v0() -> None:
    workflow = _workflow_text()

    qualification_step = _extract_step(
        workflow,
        "Check release-grade reference run qualification (advisory)",
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
            "exit 0",
            "::warning::release-grade reference qualification failed; release outcome unchanged",
        ],
        "release-grade reference qualification step",
    )

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

    enforcement_steps = _extract_steps_containing(
        workflow,
        ["policy_to_require_args.py", "check_gates.py"],
    )
    assert enforcement_steps, (
        "Expected at least one policy-derived check_gates.py enforcement step"
    )

    for enforcement_step in enforcement_steps:
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

    # The workflow must still contain the canonical policy-derived enforcement
    # ingredients separately from the advisory qualification step.
    _assert_contains_all(
        workflow,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
        ],
        "canonical policy-derived check_gates.py enforcement path",
    )


def main() -> int:
    try:
        test_release_grade_reference_qualification_is_advisory_boundary_v0()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: release-grade reference qualification advisory boundary locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
