#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

RECORDED_PATH_JOB = "release_grade_recorded_path"
PACKAGE_JOB = "assemble_release_grade_reference_package"
TOOLS_JOB = "tools-tests"

PACKAGE_ARTIFACT = (
    "complete-release-grade-reference-package-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

ASSEMBLER_TOOL = (
    "PULSE_safe_pack_v0/tools/"
    "assemble_release_grade_reference_package_v0.py"
)

STRICT_RELEASE_GUARD_TOKENS = (
    "github.event_name != 'pull_request'",
    "needs.release_grade_recorded_path.result == 'success'",
    "strict_external_evidence == 'true'",
    "startsWith(github.ref, 'refs/tags/v')",
    "startsWith(github.ref, 'refs/tags/V')",
)

REQUIRED_DOWNLOAD_ARTIFACTS = (
    "pulse-report",
    "release-grade-recorded-path-${{ github.run_id }}-${{ github.run_attempt }}",
    "release-authority-audit-bundle",
    "release-authority-artifact-binding-v0",
)

REQUIRED_PACKAGE_INPUT_PATHS = (
    "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json",
    "PULSE_safe_pack_v0/artifacts/status_baseline.json",
    "PULSE_safe_pack_v0/artifacts/recorded_release_candidates",
    "PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json",
    "PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json",
    "PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json",
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl",
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_evaluator_manifest_v0.json"
    ),
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json",
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json",
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.envelope.json",
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_attestation_verifier_v1.json"
    ),
    "PULSE_safe_pack_v0/artifacts/status.json",
    "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
    "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json",
    "PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
    "PULSE_safe_pack_v0/artifacts/report_card.html",
    "release-authority-audit-bundle",
)

REQUIRED_PACKAGE_OUTPUTS = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
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


def test_complete_package_job_order_and_dependencies() -> None:
    text, blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index("  attest_llamaguard_current_run_summary:")
    recorded_index = text.index(f"  {RECORDED_PATH_JOB}:")
    package_index = text.index(f"  {PACKAGE_JOB}:")
    tools_index = text.index(f"  {TOOLS_JOB}:")

    assert (
        pulse_index
        < attest_index
        < recorded_index
        < package_index
        < tools_index
    )

    _assert_job_needs(blocks[PACKAGE_JOB], RECORDED_PATH_JOB)
    _assert_job_needs(blocks[TOOLS_JOB], PACKAGE_JOB)


def test_complete_package_job_is_release_grade_only() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]
    guard = _job_field(package_job, "if")

    for token in STRICT_RELEASE_GUARD_TOKENS:
        assert token in guard, token


def test_complete_package_job_downloads_required_inputs() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]

    for artifact_name in REQUIRED_DOWNLOAD_ARTIFACTS:
        assert artifact_name in package_job, artifact_name

    for path in REQUIRED_PACKAGE_INPUT_PATHS:
        assert path in package_job, path


def test_complete_package_job_uses_canonical_assembler_tool() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]

    assert ASSEMBLER_TOOL in package_job
    assert "--repo-root" in package_job
    assert "--out-dir" in package_job
    assert "--pulse-report-dir" in package_job
    assert "--recorded-path-dir" in package_job
    assert "--audit-bundle-dir" in package_job
    assert "--artifact-binding-dir" in package_job


def test_complete_package_job_builds_fresh_directory() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]

    assert "RUNNER_TEMP" in package_job
    assert "rm -rf" in package_job
    assert "mkdir -p" in package_job
    assert "complete-release-grade-reference-package" in package_job


def test_complete_package_job_uploads_complete_package_artifact() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]

    assert PACKAGE_ARTIFACT in package_job
    assert "actions/upload-artifact@" in package_job
    assert "if-no-files-found: error" in package_job

    for output in REQUIRED_PACKAGE_OUTPUTS:
        assert output in package_job, output


def test_complete_package_job_is_non_authorizing() -> None:
    _text, blocks = _workflow_and_jobs()
    package_job = blocks[PACKAGE_JOB]

    forbidden = (
        "tools/check_gates.py",
        "tools/materialize_release_required_from_verifier_v0.py",
        "tools/check_recorded_release_evidence_v0.py",
        "build_recorded_release_candidates_v0.py",
        "new_release_decision",
        "parallel_decision",
    )

    for token in forbidden:
        assert token not in package_job, token


def test_complete_package_assembly_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_release_grade_reference_package_assembly_wiring_v0.py"
        in manifest
    )


def main() -> int:
    test_complete_package_job_order_and_dependencies()
    test_complete_package_job_is_release_grade_only()
    test_complete_package_job_downloads_required_inputs()
    test_complete_package_job_uses_canonical_assembler_tool()
    test_complete_package_job_builds_fresh_directory()
    test_complete_package_job_uploads_complete_package_artifact()
    test_complete_package_job_is_non_authorizing()
    test_complete_package_assembly_wiring_smoke_registered()
    print(
        "release-grade reference package assembly workflow wiring "
        "smoke passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
