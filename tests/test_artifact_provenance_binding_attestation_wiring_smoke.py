#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_SHA = "f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"

CORE_ATTEST_JOB = "attest_release_authority_artifact_binding"
RELEASE_ATTEST_JOB = "attest_release_grade_artifact_binding"
RELEASE_PATH_JOB = "release_grade_recorded_path"


def read_workflow() -> str:
    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def read_tools_tests_list() -> str:
    return TOOLS_TESTS_LIST.read_text(
        encoding="utf-8",
        errors="strict",
    )


def top_level_job_blocks(text: str) -> dict[str, str]:
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


def job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"

    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    raise AssertionError(f"missing job field: {field_name}")


def workflow_blocks() -> tuple[str, dict[str, str]]:
    text = read_workflow()
    blocks = top_level_job_blocks(text)

    for name in (
        "pulse",
        CORE_ATTEST_JOB,
        "attest_llamaguard_current_run_summary",
        RELEASE_PATH_JOB,
        RELEASE_ATTEST_JOB,
        "assemble_release_grade_reference_package",
        "tools-tests",
    ):
        assert name in blocks, name

    return text, blocks


def assert_attestation_permissions(job: str) -> None:
    assert "permissions:" in job
    assert "contents: read" in job
    assert "actions: read" in job
    assert "id-token: write" in job
    assert "attestations: write" in job
    assert "artifact-metadata: write" in job


def assert_binding_download_and_attestation(job: str) -> None:
    assert 'gh run download "${GITHUB_RUN_ID}"' in job
    assert '--repo "${GITHUB_REPOSITORY}"' in job
    assert '--name "release-authority-artifact-binding-v0"' in job
    assert "artifact_provenance_binding_v0.json" in job
    assert f"uses: actions/attest@{ATTEST_SHA}" in job
    assert (
        "subject-path: "
        "attestation-subject/artifact_provenance_binding_v0.json"
        in job
    )
    assert "show-summary: true" in job


def test_pulse_job_remains_read_only_for_attestation_credentials() -> None:
    _text, blocks = workflow_blocks()
    pulse = blocks["pulse"]

    assert "permissions:" in pulse
    assert "contents: read" in pulse
    assert "id-token: write" not in pulse
    assert "attestations: write" not in pulse
    assert "artifact-metadata: write" not in pulse


def test_core_binding_attestation_remains_non_release_only() -> None:
    _text, blocks = workflow_blocks()
    job = blocks[CORE_ATTEST_JOB]

    assert job_field(job, "needs") == "pulse"

    guard = job_field(job, "if")

    for token in (
        "github.event_name != 'pull_request'",
        "needs.pulse.result == 'success'",
        "!startsWith(github.ref, 'refs/tags/v')",
        "!startsWith(github.ref, 'refs/tags/V')",
        (
            "github.event_name != 'workflow_dispatch' || "
            "github.event.inputs.strict_external_evidence != 'true'"
        ),
    ):
        assert token in guard, token

    assert_attestation_permissions(job)
    assert_binding_download_and_attestation(job)


def test_release_binding_attestation_waits_for_recorded_path() -> None:
    _text, blocks = workflow_blocks()
    job = blocks[RELEASE_ATTEST_JOB]

    assert job_field(job, "needs") == RELEASE_PATH_JOB

    guard = job_field(job, "if")

    for token in (
        "github.event_name != 'pull_request'",
        "needs.release_grade_recorded_path.result == 'success'",
        "strict_external_evidence == 'true'",
        "hosted_full_runtime",
        "startsWith(github.ref, 'refs/tags/v')",
        "startsWith(github.ref, 'refs/tags/V')",
    ):
        assert token in guard, token

    assert_attestation_permissions(job)
    assert_binding_download_and_attestation(job)


def test_all_attestation_actions_use_immutable_pin() -> None:
    text = read_workflow()

    uses_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("uses: actions/attest@")
    ]

    assert uses_lines
    assert all(
        line == f"uses: actions/attest@{ATTEST_SHA}"
        for line in uses_lines
    ), uses_lines


def test_release_binding_is_materialized_before_release_attestation() -> None:
    text, blocks = workflow_blocks()
    recorded = blocks[RELEASE_PATH_JOB]

    materialize = recorded.index(
        "Materialize and verify final release authority artifact binding"
    )
    upload = recorded.index(
        "Upload final release authority artifact binding"
    )

    assert materialize < upload

    recorded_index = text.index(f"  {RELEASE_PATH_JOB}:")
    attest_index = text.index(f"  {RELEASE_ATTEST_JOB}:")

    assert recorded_index < attest_index


def test_core_binding_is_materialized_before_core_attestation() -> None:
    text, blocks = workflow_blocks()
    pulse = blocks["pulse"]

    materialize = pulse.index(
        "Release authority artifact binding v0: materialize and verify"
    )
    upload = pulse.index(
        "Upload release authority artifact binding v0"
    )

    assert materialize < upload

    pulse_index = text.index("  pulse:")
    attest_index = text.index(f"  {CORE_ATTEST_JOB}:")

    assert pulse_index < attest_index


def test_attestation_jobs_are_isolated_from_producer_jobs() -> None:
    _text, blocks = workflow_blocks()

    pulse = blocks["pulse"]
    recorded = blocks[RELEASE_PATH_JOB]

    assert "uses: actions/attest@" not in pulse
    assert "uses: actions/attest@" not in recorded

    assert (
        "Release authority artifact binding v0: attest"
        not in pulse
    )
    assert (
        "Attest final release-grade artifact binding v0"
        not in recorded
    )


def test_job_order_preserves_phase_boundary() -> None:
    text, _blocks = workflow_blocks()

    pulse_index = text.index("  pulse:")
    core_attest_index = text.index(f"  {CORE_ATTEST_JOB}:")
    llama_attest_index = text.index(
        "  attest_llamaguard_current_run_summary:"
    )
    recorded_index = text.index(f"  {RELEASE_PATH_JOB}:")
    release_attest_index = text.index(
        f"  {RELEASE_ATTEST_JOB}:"
    )
    package_index = text.index(
        "  assemble_release_grade_reference_package:"
    )
    tools_index = text.index("  tools-tests:")

    assert pulse_index < core_attest_index < tools_index
    assert (
        pulse_index
        < llama_attest_index
        < recorded_index
        < release_attest_index
        < package_index
        < tools_index
    )


def test_attestation_smoke_is_registered_in_tools_manifest() -> None:
    manifest = read_tools_tests_list()

    assert (
        "tests/"
        "test_artifact_provenance_binding_attestation_wiring_smoke.py"
        in manifest
    )


def main() -> int:
    test_pulse_job_remains_read_only_for_attestation_credentials()
    test_core_binding_attestation_remains_non_release_only()
    test_release_binding_attestation_waits_for_recorded_path()
    test_all_attestation_actions_use_immutable_pin()
    test_release_binding_is_materialized_before_release_attestation()
    test_core_binding_is_materialized_before_core_attestation()
    test_attestation_jobs_are_isolated_from_producer_jobs()
    test_job_order_preserves_phase_boundary()
    test_attestation_smoke_is_registered_in_tools_manifest()

    print(
        "OK: core and release-grade artifact-binding "
        "attestation phase boundaries locked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
