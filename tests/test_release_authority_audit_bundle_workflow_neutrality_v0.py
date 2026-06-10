#!/usr/bin/env python3
"""Workflow-static audit-bundle neutrality checks for PULSE v0.

This test locks the release authority audit bundle as a review /
traceability surface.

It does not change workflow behavior. It statically verifies that the
primary workflow keeps audit-bundle staging/upload separate from the
artifact-bound release-authority path.
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


def _assert_contains_all(text: str, required: list[str], label: str) -> None:
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

    # The audit bundle is staged into the dedicated artifacts workspace and
    # contains review / traceability copies only.
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
            "audit",
            "traceability",
            "non-normative",
            "non-blocking",
        ],
        "audit bundle staging boundary wording",
    )

    # Upload must remain artifact-only / warning-only. A missing bundle must
    # not become a release-authority signal.
 
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

    # Primary release enforcement remains policy-derived and separate from
    # audit-bundle staging/upload.
    _assert_contains_all(
        workflow,
        [
            "policy_to_require_args.py",
            "check_gates.py",
            "pulse_gate_policy_v0.yml",
        ],
        "primary policy-derived check_gates enforcement path",
    )

    # The audit bundle steps must not be the enforcement carrier.
    forbidden_stage_tokens = [
        "policy_to_require_args.py",
        "check_gates.py",
        "--release-grade-materialized",
        "gate_materialization",
        "materialized required gate",
        "release eligibility",
        "second decision engine",
    ]

    for token in forbidden_stage_tokens:
        assert token not in stage_step, (
            "audit bundle staging must not contain enforcement / authority "
            f"token: {token}"
        )
        assert token not in upload_step, (
            "audit bundle upload must not contain enforcement / authority "
            f"token: {token}"
        )

    # The upload artifact name must remain the audit-bundle artifact, not a
    # status, gate, policy, or release-decision artifact.
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
