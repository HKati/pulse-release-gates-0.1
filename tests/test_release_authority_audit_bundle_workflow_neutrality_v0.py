#!/usr/bin/env python3
"""Workflow-static audit-bundle neutrality checks for PULSE v0.

This test locks the release authority audit bundle as a review /
traceability surface.

It does not change workflow behavior. It statically verifies that the
primary workflow keeps audit-bundle staging/upload separate from the
artifact-bound release-authority path.

The workflow may contain more than one policy-derived check_gates.py
enforcement step. For example:

- core gate enforcement in the pulse job;
- release_required enforcement in the attested release-grade path.

That is valid. The invariant here is not "exactly one enforcement step".
The invariant is that no policy-derived check_gates enforcement step may
consume the audit bundle as a release-authority carrier.
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
    label: str,
) -> list[str]:
    step_pattern = re.compile(
        r"(?ms)^\s*-\s+name:\s+.*?$.*?(?=^\s*-\s+name:\s+|\Z)"
    )
    matches = [
        match.group(0)
        for match in step_pattern.finditer(workflow)
        if all(token in match.group(0) for token in required_tokens)
    ]

    assert matches, (
        f"Expected at least one {label} step containing {required_tokens}, "
        "found 0"
    )
    return matches


def _assert_contains_all(
    text: str,
    required: list[str],
    label: str,
) -> None:
    missing = [item for item in required if item not in text]
    assert not missing, f"{label} is missing expected tokens: {missing}"


def _assert_exact_audit_bundle_upload_path(upload_step: str) -> None:
    expected_path = "${{ env.PACK_DIR }}/artifacts/release_authority_audit_bundle/"

    assert re.search(
        rf"(?m)^\s*path:\s*{re.escape(expected_path)}\s*$",
        upload_step,
    ), (
        "audit bundle upload path must remain the exact artifacts path: "
        f"{expected_path}"
    )


def test_release_authority_audit_bundle_workflow_neutrality_v0() -> None:
    workflow = _workflow_text()

    stage_step = _extract_step(
        workflow,
        "Stage release authority audit bundle (audit-only)",
    )
    upload_step = _extract_step(
        workflow,
        "Upload release authority audit bundle (audit-only)",
    )
    enforcement_steps = _extract_steps_containing(
        workflow,
        ["policy_to_require_args.py", "check_gates.py"],
        "policy-derived check_gates enforcement",
    )

    _assert_contains_all(
        stage_step,
        [
            "release_authority_audit_bundle",
            "report_card.html",
            "release_authority_v0.json",
            "status.json",
        ],
        "audit bundle staging step",
    )

    stage_step_l = stage_step.lower()
    _assert_contains_all(
        stage_step_l,
        [
            "review",
            "traceability",
            "non-normative",
            "non-blocking",
        ],
        "audit bundle staging boundary wording",
    )

    _assert_contains_all(
        upload_step,
        [
            "name: release-authority-audit-bundle",
            "continue-on-error: true",
            "if-no-files-found: warn",
        ],
        "audit bundle upload step",
    )
    _assert_exact_audit_bundle_upload_path(upload_step)

    _assert_contains_all(
        workflow,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
        ],
        "primary policy-derived check_gates enforcement path",
    )

    forbidden_stage_or_upload_tokens = [
        "policy_to_require_args.py",
        "check_gates.py",
        "--release-grade-materialized",
        "--audit-bundle-dir",
    ]

    for token in forbidden_stage_or_upload_tokens:
        assert token not in stage_step, (
            "audit bundle staging must not contain enforcement / authority "
            f"token: {token}"
        )
        assert token not in upload_step, (
            "audit bundle upload must not contain enforcement / authority "
            f"token: {token}"
        )

    forbidden_enforcement_tokens = [
        "release_authority_audit_bundle",
        "release-authority-audit-bundle",
        "--audit-bundle-dir",
    ]

    for enforcement_step in enforcement_steps:
        for token in forbidden_enforcement_tokens:
            assert token not in enforcement_step, (
                "policy-derived check_gates enforcement must not consume the "
                f"audit bundle as a release-authority carrier: {token}"
            )

    assert "name: release-authority-audit-bundle" in upload_step
    assert "name: status.json" not in upload_step
    assert "name: release-authority-v0" not in upload_step
    assert "name: release-decision" not in upload_step


def main() -> int:
    try:
        test_release_authority_audit_bundle_workflow_neutrality_v0()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: release authority audit bundle workflow neutrality locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
