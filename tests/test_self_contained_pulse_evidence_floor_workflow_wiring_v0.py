#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

TEST_PATH = (
    "tests/test_self_contained_pulse_evidence_floor_workflow_wiring_v0.py"
)

FLOOR_TOOL = (
    "${PACK_DIR}/tools/"
    "build_self_contained_pulse_evidence_floor_v0.py"
)
FLOOR_ARTIFACT = (
    "PULSE_safe_pack_v0/artifacts/"
    "self_contained_pulse_evidence_floor_v0.json"
)
FLOOR_ARTIFACT_ENV = (
    "${PACK_DIR}/artifacts/"
    "self_contained_pulse_evidence_floor_v0.json"
)

REQUIRED_ORDER = (
    "release-grade record current-run required-gate evidence",
    "release-grade build non-stubbed prod candidate status",
    "Preserve baseline status.json (pre-augment)",
    '"ci: schema validate status_baseline.json (status_v1)"',
    '"ci: require prod run_mode on release-grade runs"',
    "release-grade initialize current-run evidence identity",
    "release-grade build self-contained PULSE evidence floor",
    "upload self-contained PULSE evidence floor",
    "release-grade initialize LlamaGuard runtime identity",
    "release-grade install pinned LlamaGuard runtime",
    "release-grade produce current-run LlamaGuard raw evidence",
    "release-grade build canonical LlamaGuard summary",
)

FORBIDDEN_IN_FLOOR_STEP = (
    "check_gates.py",
    "materialize_release_decision.py",
    "materialize_release_required_from_verifier_v0.py",
    "check_recorded_release_evidence_v0.py",
    "actions/attest",
    "HF_TOKEN",
    "huggingface",
    "Hugging Face",
    "LlamaGuard",
    "run_llamaguard_current_evidence_v0.py",
    "llamaguard_ingest.py",
)


def _workflow() -> str:
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _manifest_entries() -> list[str]:
    assert TOOLS_TESTS_LIST.is_file(), (
        f"missing tools-test manifest: {TOOLS_TESTS_LIST}"
    )
    return [
        line.strip()
        for line in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _step_marker(step_name: str) -> str:
    return f"      - name: {step_name}"


def _step_index(text: str, step_name: str) -> int:
    marker = _step_marker(step_name)
    assert marker in text, f"missing workflow step: {step_name}"
    return text.index(marker)


def _step_block(text: str, step_name: str) -> str:
    start = _step_index(text, step_name)
    next_start = text.find("\n      - name:", start + 1)
    if next_start == -1:
        return text[start:]
    return text[start:next_start]


def test_self_contained_floor_workflow_order() -> None:
    text = _workflow()

    indices = [
        _step_index(text, step_name)
        for step_name in REQUIRED_ORDER
    ]

    assert indices == sorted(indices), (
        "self-contained floor must run after release-grade status and "
        "run-mode validation, after generalized identity, and before "
        "hosted LlamaGuard runtime"
    )


def test_current_run_identity_step_is_generalized() -> None:
    text = _workflow()

    assert (
        "release-grade initialize current-run LlamaGuard identity"
        not in text
    ), "shared current-run identity step must not be LlamaGuard-specific"

    block = _step_block(
        text,
        "release-grade initialize current-run evidence identity",
    )

    for token in (
        "PULSE_CREATED_UTC",
        "PULSE_RELEASE_CANDIDATE",
        "PULSE_EXTERNAL_SIGNER_IDENTITY",
        "$GITHUB_ENV",
    ):
        assert token in block, token

    assert "LLAMAGUARD_VERSION" not in block
    assert "HF_TOKEN" not in block
    assert "huggingface" not in block.lower()


def test_llamaguard_runtime_identity_remains_separate() -> None:
    text = _workflow()
    block = _step_block(
        text,
        "release-grade initialize LlamaGuard runtime identity",
    )

    assert "LLAMAGUARD_VERSION" in block
    assert "PULSE_CREATED_UTC" not in block
    assert "PULSE_RELEASE_CANDIDATE" not in block
    assert "PULSE_EXTERNAL_SIGNER_IDENTITY" not in block


def test_self_contained_floor_build_step_invokes_canonical_builder() -> None:
    text = _workflow()
    block = _step_block(
        text,
        "release-grade build self-contained PULSE evidence floor",
    )

    assert "steps.release_mode.outputs.is_release == '1'" in block
    assert FLOOR_TOOL in block
    assert "--repo-root" in block
    assert '"${GITHUB_WORKSPACE}"' in block
    assert "--status" in block
    assert '"${PACK_DIR}/artifacts/status.json"' in block
    assert "--policy" in block
    assert '"pulse_gate_policy_v0.yml"' in block
    assert "--registry" in block
    assert '"pulse_gate_registry_v0.yml"' in block
    assert "--required-gate-evidence" in block
    assert '"${PACK_DIR}/artifacts/required_gate_evidence_v0.json"' in block
    assert "--out" in block
    assert f'"{FLOOR_ARTIFACT_ENV}"' in block
    assert "--repository" in block
    assert '"${GITHUB_REPOSITORY}"' in block
    assert "--git-sha" in block
    assert '"${GITHUB_SHA}"' in block
    assert "--run-key" in block
    assert '"${PULSE_RUN_KEY}"' in block
    assert "--workflow-ref" in block
    assert '"${GITHUB_WORKFLOW_REF}"' in block
    assert "--created-utc" in block
    assert '"${PULSE_CREATED_UTC}"' in block
    assert "--external-model-status" in block
    assert '"not_required_for_tier0"' in block

    for token in FORBIDDEN_IN_FLOOR_STEP:
        assert token not in block, token


def test_self_contained_floor_artifact_upload_is_fail_closed() -> None:
    text = _workflow()
    block = _step_block(
        text,
        "upload self-contained PULSE evidence floor",
    )

    assert "steps.release_mode.outputs.is_release == '1'" in block
    assert "uses: actions/upload-artifact@" in block
    assert "self-contained-pulse-evidence-floor-v0-" in block
    assert FLOOR_ARTIFACT in block
    assert "if-no-files-found: error" in block
    assert "retention-days: 30" in block


def test_release_grade_reset_clears_stale_floor_artifact() -> None:
    text = _workflow()
    block = _step_block(
        text,
        "release-grade reset candidate evidence outputs",
    )

    assert FLOOR_ARTIFACT_ENV in block


def test_workflow_wiring_smoke_registered() -> None:
    entries = _manifest_entries()

    assert entries.count(TEST_PATH) == 1, (
        f"{TEST_PATH} must appear exactly once in ci/tools-tests.list"
    )


def main() -> int:
    test_self_contained_floor_workflow_order()
    test_current_run_identity_step_is_generalized()
    test_llamaguard_runtime_identity_remains_separate()
    test_self_contained_floor_build_step_invokes_canonical_builder()
    test_self_contained_floor_artifact_upload_is_fail_closed()
    test_release_grade_reset_clears_stale_floor_artifact()
    test_workflow_wiring_smoke_registered()
    print("OK: self-contained PULSE evidence floor workflow wiring locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
