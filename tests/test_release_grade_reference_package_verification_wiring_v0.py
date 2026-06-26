#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

RECORDED_PATH_JOB = "release_grade_recorded_path"
PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"
TOOLS_JOB = "tools-tests"

PACKAGE_ARTIFACT = (
    "complete-release-grade-reference-package-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)
VERIFY_ARTIFACT = (
    "release-grade-reference-package-verification-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

VERIFY_TOOL = (
    "PULSE_safe_pack_v0/tools/"
    "verify_release_grade_reference_package_v0.py"
)
VERIFY_TOOL_PATH = REPO_ROOT / VERIFY_TOOL

VERIFY_REPORT = (
    "release_grade_reference_package_verification_v0.json"
)

STRICT_RELEASE_GUARD_TOKENS = (
    "github.event_name != 'pull_request'",
    "needs.assemble_release_grade_reference_package.result == 'success'",
    "strict_external_evidence == 'true'",
    "startsWith(github.ref, 'refs/tags/v')",
    "startsWith(github.ref, 'refs/tags/V')",
)

REQUIRED_VERIFY_INPUTS = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidates",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_raw.jsonl",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/report_card.html",
    "release-authority-audit-bundle",
)


def _read_workflow() -> str:
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _read_tools_manifest() -> str:
    assert TOOLS_TESTS_LIST.is_file(), (
        f"missing tools manifest: {TOOLS_TESTS_LIST}"
    )
    return TOOLS_TESTS_LIST.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _top_level_job_blocks(text: str) -> dict[str, str]:
    starts: list[tuple[str, int]] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        if (
            line.startswith("  ")
            and not line.startswith("    ")
            and line.strip().endswith(":")
        ):
            starts.append((line.strip()[:-1], offset))

        offset += len(line)

    blocks: dict[str, str] = {}

    for index, (name, start) in enumerate(starts):
        end = (
            starts[index + 1][1]
            if index + 1 < len(starts)
            else len(text)
        )
        blocks[name] = text[start:end]

    return blocks


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    for name in (
        "pulse",
        "attest_llamaguard_current_run_summary",
        RECORDED_PATH_JOB,
        PACKAGE_JOB,
        VERIFY_JOB,
        TOOLS_JOB,
    ):
        assert name in blocks, f"missing workflow job: {name}"

    return text, blocks


def _job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"

    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    raise AssertionError(f"missing job field: {field_name}")


def _assert_job_needs(job_block: str, expected: str) -> None:
    needs = _job_field(job_block, "needs")
    assert expected in needs, (
        f"job needs must include {expected!r}; got {needs!r}"
    )


def test_complete_package_verification_job_order_and_dependencies() -> None:
    text, blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index("  attest_llamaguard_current_run_summary:")
    recorded_index = text.index(f"  {RECORDED_PATH_JOB}:")
    package_index = text.index(f"  {PACKAGE_JOB}:")
    verify_index = text.index(f"  {VERIFY_JOB}:")
    tools_index = text.index(f"  {TOOLS_JOB}:")

    assert (
        pulse_index
        < attest_index
        < recorded_index
        < package_index
        < verify_index
        < tools_index
    )

    _assert_job_needs(blocks[PACKAGE_JOB], RECORDED_PATH_JOB)
    _assert_job_needs(blocks[VERIFY_JOB], PACKAGE_JOB)
    _assert_job_needs(blocks[TOOLS_JOB], VERIFY_JOB)


def test_complete_package_verification_job_is_release_grade_only() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]
    guard = _job_field(verify_job, "if")

    for token in STRICT_RELEASE_GUARD_TOKENS:
        assert token in guard, token


def test_complete_package_verification_downloads_complete_package() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert PACKAGE_ARTIFACT in verify_job
    assert "gh run download" in verify_job
    assert "complete-release-grade-reference-package" in verify_job

    for required in REQUIRED_VERIFY_INPUTS:
        assert required in verify_job, required


def test_complete_package_verification_uses_canonical_read_only_tool() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert VERIFY_TOOL_PATH.is_file(), (
        f"missing canonical verifier tool: {VERIFY_TOOL_PATH}"
    )
    assert VERIFY_TOOL in verify_job
    assert "--repo-root" in verify_job
    assert "--package-dir" in verify_job
    assert "--out" in verify_job
    assert "--repository" in verify_job
    assert "--git-sha" in verify_job
    assert "--workflow-ref" in verify_job
    assert "--run-id" in verify_job
    assert "--run-attempt" in verify_job
    assert "--run-key" in verify_job


def test_complete_package_verification_uploads_report_artifact() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert VERIFY_REPORT in verify_job
    assert VERIFY_ARTIFACT in verify_job
    assert "actions/upload-artifact@" in verify_job
    assert "if-no-files-found: error" in verify_job


def test_complete_package_verification_is_non_authorizing() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    forbidden = (
        "tools/check_gates.py",
        "tools/materialize_release_required_from_verifier_v0.py",
        "tools/check_recorded_release_evidence_v0.py",
        "build_recorded_release_candidates_v0.py",
        "build_release_evidence_input_manifest_v0.py",
        "new_release_decision",
        "parallel_decision",
        "authorize_release",
    )

    for token in forbidden:
        assert token not in verify_job, token


def test_complete_package_verification_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_release_grade_reference_package_verification_wiring_v0.py"
        in manifest
    )


def main() -> int:
    test_complete_package_verification_job_order_and_dependencies()
    test_complete_package_verification_job_is_release_grade_only()
    test_complete_package_verification_downloads_complete_package()
    test_complete_package_verification_uses_canonical_read_only_tool()
    test_complete_package_verification_uploads_report_artifact()
    test_complete_package_verification_is_non_authorizing()
    test_complete_package_verification_wiring_smoke_registered()
    print(
        "release-grade reference package verification workflow wiring "
        "smoke passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
