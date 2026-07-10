#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"
TOOLS_JOB = "tools-tests"

COMPLETENESS_TOOL = "tools/check_release_grade_package_complete_v1.py"
DEEP_VERIFY_TOOL = (
    "PULSE_safe_pack_v0/tools/"
    "verify_release_grade_reference_package_v0.py"
)

COMPLETENESS_REPORT = "release_grade_package_completeness_v1.json"
COMPLETENESS_REPORT_PATH = (
    "${{runner.temp}}/release_grade_package_completeness_v1.json"
)
PACKAGE_DIR = "${{runner.temp}}/complete-release-grade-reference-package"
COMPLETENESS_ARTIFACT = (
    "release-grade-package-completeness-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

THIS_TEST = "tests/test_release_grade_package_completeness_workflow_wiring_v1.py"


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


def _manifest_entries() -> list[str]:
    entries: list[str] = []

    for raw in _read_tools_manifest().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)

    return entries


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
        end = starts[index + 1][1] if index + 1 < len(starts) else len(text)
        blocks[name] = text[start:end]

    return blocks


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    for name in (
        PACKAGE_JOB,
        VERIFY_JOB,
        TOOLS_JOB,
    ):
        assert name in blocks, f"missing workflow job: {name}"

    return text, blocks


def _step_index(job_block: str, step_name: str) -> int:
    marker = f"      - name: {step_name}"
    assert marker in job_block, f"missing workflow step: {step_name}"
    return job_block.index(marker)


def test_completeness_preflight_is_inside_release_grade_verify_job() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert COMPLETENESS_TOOL in verify_job
    assert DEEP_VERIFY_TOOL in verify_job

    download_index = _step_index(
        verify_job,
        "Download complete release-grade reference package",
    )
    completeness_index = _step_index(
        verify_job,
        "Check release-grade package completeness",
    )
    completeness_upload_index = _step_index(
        verify_job,
        "Upload release-grade package completeness report",
    )
    deep_verify_index = _step_index(
        verify_job,
        "Verify complete release-grade reference package",
    )
    deep_upload_index = _step_index(
        verify_job,
        "Upload release-grade reference package verification report",
    )

    assert (
        download_index
        < completeness_index
        < completeness_upload_index
        < deep_verify_index
        < deep_upload_index
    )


def test_completeness_preflight_uses_safe_explicit_paths() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert f'python "{COMPLETENESS_TOOL}"' in verify_job
    assert f'--package-dir "{PACKAGE_DIR}"' in verify_job
    assert f'--output "{COMPLETENESS_REPORT_PATH}"' in verify_job
    assert "--require-slsa-vsa-trusted-producer" not in verify_job

    assert '--output "status.json"' not in verify_job
    assert f'--output "{PACKAGE_DIR}/' not in verify_job
    assert f'--output "./complete-release-grade-reference-package/' not in verify_job


def test_completeness_report_is_uploaded_after_preflight_with_always() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    completeness_index = _step_index(
        verify_job,
        "Check release-grade package completeness",
    )
    upload_index = _step_index(
        verify_job,
        "Upload release-grade package completeness report",
    )

    assert completeness_index < upload_index

    upload_block = verify_job[upload_index:]
    deep_verify_index = upload_block.index(
        "      - name: Verify complete release-grade reference package"
    )
    upload_block = upload_block[:deep_verify_index]

    assert "uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in upload_block
    assert "if: ${{ always() }}" in upload_block
    assert COMPLETENESS_ARTIFACT in upload_block
    assert f"path: {COMPLETENESS_REPORT_PATH}" in upload_block
    assert "if-no-files-found: error" in upload_block
    assert "retention-days: 30" in upload_block


def test_completeness_wiring_preserves_release_grade_only_boundary() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert "github.event_name != 'pull_request'" in verify_job
    assert "needs.assemble_release_grade_reference_package.result == 'success'" in verify_job
    assert "strict_external_evidence == 'true'" in verify_job
    assert "hosted_full_runtime" in verify_job

    assert "needs: assemble_release_grade_reference_package" in verify_job


def test_completeness_wiring_does_not_create_release_authority() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    completeness_index = _step_index(
        verify_job,
        "Check release-grade package completeness",
    )
    upload_index = _step_index(
        verify_job,
        "Upload release-grade package completeness report",
    )
    deep_verify_index = _step_index(
        verify_job,
        "Verify complete release-grade reference package",
    )

    completeness_region = verify_job[completeness_index:deep_verify_index]
    upload_region = verify_job[upload_index:deep_verify_index]

    forbidden = (
        "check_gates.py",
        "PULSE_safe_pack_v0/tools/check_gates.py",
        "policy_to_require_args.py",
        "fold_slsa_vsa_intake_into_status_v0.py",
        "materialize_release_required_from_verifier_v0.py",
        "build_release_authority_manifest_v0.py",
        "release_required",
        "release_blocking",
        "prod_required",
        "stage_required",
        "gate_materialization",
        "required_gates",
        "status.gates",
        "status_gates",
        "status.json",
    )

    for token in forbidden:
        assert token not in completeness_region, token

    assert "actions/upload-artifact" in upload_region
    assert "if: ${{ always() }}" in upload_region


def test_completeness_wiring_smoke_registered_exactly_once() -> None:
    entries = _manifest_entries()

    assert entries.count(THIS_TEST) == 1


def test_completeness_wiring_smoke_placement() -> None:
    entries = _manifest_entries()

    this_index = entries.index(THIS_TEST)
    boundary_index = entries.index(
        "tests/test_release_grade_package_completeness_checker_ci_boundary_v1.py"
    )
    next_index = entries.index(
        "tests/test_release_grade_reference_qualification_advisory_boundary_v0.py"
    )

    assert boundary_index < this_index < next_index


def check_release_grade_package_completeness_workflow_wiring_v1() -> None:
    test_completeness_preflight_is_inside_release_grade_verify_job()
    test_completeness_preflight_uses_safe_explicit_paths()
    test_completeness_report_is_uploaded_after_preflight_with_always()
    test_completeness_wiring_preserves_release_grade_only_boundary()
    test_completeness_wiring_does_not_create_release_authority()
    test_completeness_wiring_smoke_registered_exactly_once()
    test_completeness_wiring_smoke_placement()


def test_release_grade_package_completeness_workflow_wiring_v1() -> None:
    check_release_grade_package_completeness_workflow_wiring_v1()


if __name__ == "__main__":
    check_release_grade_package_completeness_workflow_wiring_v1()
    print("OK: release-grade package completeness workflow wiring passed")
