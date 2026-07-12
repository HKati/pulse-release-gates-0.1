#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_JOB = "attest_llamaguard_current_run_summary"
RELEASE_PATH_JOB = "release_grade_recorded_path"
RELEASE_BINDING_ATTEST_JOB = "attest_release_grade_artifact_binding"
PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"

PRE_ATTESTATION_UPLOAD_ARTIFACT = (
    "pulse-pre-attestation-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

PRE_ATTESTATION_DOWNLOAD_ARTIFACT = (
    "pulse-pre-attestation-"
    "${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
)

ATTESTED_DOWNLOAD_ARTIFACT = (
    "llamaguard-attested-current-run-"
    "${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
)

HOSTED_MODE_GUARD_TOKEN = (
    "github.event.inputs.llamaguard_evidence_mode == 'hosted_full_runtime'"
)

NON_RELEASE_STEP_GUARD = (
    "steps.release_mode.outputs.is_release != '1'"
)

PRE_ATTESTATION_RELEASE_TOOLS = (
    "tools/build_recorded_release_candidates_v0.py",
    "tools/build_release_evidence_input_manifest_v0.py",
    "tools/check_recorded_release_evidence_v0.py",
    "tools/materialize_release_required_from_verifier_v0.py",
)

ATTESTED_EXTERNAL_FILENAMES = (
    "llamaguard_raw.jsonl",
    "llamaguard_evaluator_manifest_v0.json",
    "llamaguard_summary.json",
    "llamaguard_summary.bundle.json",
    "llamaguard_summary.envelope.json",
    "llamaguard_attestation_verifier_v1.json",
)


def _read_workflow() -> str:
    if not WORKFLOW.is_file():
        raise AssertionError(f"missing workflow: {WORKFLOW}")

    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _read_tools_manifest() -> str:
    if not TOOLS_TESTS_LIST.is_file():
        raise AssertionError(
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


def _job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"

    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    raise AssertionError(f"missing job field: {field_name}")


def _step_block(job_block: str, step_name: str) -> str:
    marker = f"      - name: {step_name}"
    start = job_block.find(marker)

    if start < 0:
        raise AssertionError(f"missing workflow step: {step_name}")

    next_start = job_block.find(
        "\n      - name:",
        start + len(marker),
    )

    if next_start < 0:
        return job_block[start:]

    return job_block[start:next_start]


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    required_jobs = (
        "pulse",
        ATTEST_JOB,
        RELEASE_PATH_JOB,
        RELEASE_BINDING_ATTEST_JOB,
        PACKAGE_JOB,
        VERIFY_JOB,
        "tools-tests",
    )

    for name in required_jobs:
        if name not in blocks:
            raise AssertionError(f"missing workflow job: {name}")

    return text, blocks


def test_release_grade_job_order() -> None:
    text, _blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index(f"  {ATTEST_JOB}:")
    release_path_index = text.index(f"  {RELEASE_PATH_JOB}:")
    binding_attest_index = text.index(
        f"  {RELEASE_BINDING_ATTEST_JOB}:"
    )
    package_index = text.index(f"  {PACKAGE_JOB}:")
    verify_index = text.index(f"  {VERIFY_JOB}:")
    tools_index = text.index("  tools-tests:")

    assert (
        pulse_index
        < attest_index
        < release_path_index
        < binding_attest_index
        < package_index
        < verify_index
        < tools_index
    )


def test_attestation_job_is_hosted_external_model_only() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[ATTEST_JOB]

    assert _job_field(job, "needs") == "pulse"

    guard = _job_field(job, "if")

    for token in (
        "github.event_name != 'pull_request'",
        "needs.pulse.result == 'success'",
        "strict_external_evidence == 'true'",
        "startsWith(github.ref, 'refs/tags/v')",
        "startsWith(github.ref, 'refs/tags/V')",
        HOSTED_MODE_GUARD_TOKEN,
    ):
        assert token in guard, token


def test_pre_attestation_artifact_is_uploaded_fail_closed() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    postconditions = _step_block(
        pulse,
        "release-grade pre-attestation artifact postconditions",
    )
    upload = _step_block(
        pulse,
        "Upload release-grade pre-attestation pulse artifacts",
    )

    assert PRE_ATTESTATION_UPLOAD_ARTIFACT in upload
    assert "if-no-files-found: error" in upload
    assert "retention-days: 30" in upload

    for required in (
        "status.json",
        "status_baseline.json",
        "status_summary_baseline.md",
        "status_summary_baseline.json",
        "required_gate_evidence_v0.json",
        "self_contained_pulse_evidence_floor_v0.json",
        "refusal_delta_summary.json",
        "llamaguard_raw.jsonl",
        "llamaguard_evaluator_manifest_v0.json",
        "llamaguard_summary.json",
    ):
        assert required in postconditions, required
        assert required in upload, required


def test_recorded_path_downloads_pre_attestation_artifact() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    download = _step_block(
        job,
        "Download pre-attestation pulse artifacts",
    )

    assert PRE_ATTESTATION_DOWNLOAD_ARTIFACT in download
    assert '--repo "${GITHUB_REPOSITORY}"' in download

    for required in (
        "status.json",
        "status_baseline.json",
        "status_summary_baseline.md",
        "status_summary_baseline.json",
        "required_gate_evidence_v0.json",
        "self_contained_pulse_evidence_floor_v0.json",
        "refusal_delta_summary.json",
    ):
        assert required in download, required


def test_release_grade_candidate_tools_remain_after_attestation() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]
    recorded = blocks[RELEASE_PATH_JOB]

    for tool in PRE_ATTESTATION_RELEASE_TOOLS:
        assert tool not in pulse, tool
        assert tool in recorded, tool


def test_pre_attestation_final_authority_steps_are_core_only() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    step_names = (
        "Build release authority manifest (audit-only)",
        '"ci: enforce gates via check_gates (policy-derived)"',
        '"Release decision v0: materialize artifact"',
        (
            '"Release authority artifact binding v0: '
            'materialize and verify"'
        ),
        "Export JUnit and SARIF from final status",
        "Upload artifacts",
    )

    for step_name in step_names:
        block = _step_block(pulse, step_name)
        assert NON_RELEASE_STEP_GUARD in block, step_name


def test_recorded_path_restores_attested_evidence_before_verification() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    step_name = "Download attested LlamaGuard external evidence"
    download = _step_block(job, step_name)
    download_step_index = job.index(f"      - name: {step_name}")

    first_tool_index = min(
        job.index(tool)
        for tool in PRE_ATTESTATION_RELEASE_TOOLS
    )

    assert download_step_index < first_tool_index
    assert ATTESTED_DOWNLOAD_ARTIFACT in download
    assert (
        'CANONICAL_EXTERNAL="${GITHUB_WORKSPACE}/'
        'PULSE_safe_pack_v0/artifacts/external"'
        in download
    )
    assert "restore_external_artifact" in download

    for filename in ATTESTED_EXTERNAL_FILENAMES:
        assert f'"{filename}"' in download, filename
        destination = f'"${{CANONICAL_EXTERNAL}}/{filename}"'
        assert destination in download, destination

    for token in (
        'if [[ -z "${src}" ]]',
        'if [[ -L "${src}" ]]',
        'if [[ ! -f "${artifact}" || -L "${artifact}" || ! -s "${artifact}" ]]',
        'sha256sum "${artifact}"',
    ):
        assert token in download, token


def test_recorded_path_materializes_before_combined_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    materializer = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    schema = job.index("release_grade_status_v1.schema.json")
    no_stub = job.index("ci/check_release_no_stub_status.py")
    enforcement = job.index(
        "release-grade enforce required and release-required gates"
    )

    assert materializer < schema < no_stub < enforcement

    enforcement_block = _step_block(
        job,
        "release-grade enforce required and release-required gates via check_gates",
    )

    for token in (
        "--set required",
        "--set release_required",
        "EFFECTIVE_GATES",
        "tools/check_gates.py",
        '--status "${STATUS}"',
        '--require "${EFFECTIVE_GATES[@]}"',
    ):
        assert token in enforcement_block, token


def test_final_authority_artifacts_follow_gate_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    enforcement = job.index(
        "release-grade enforce required and release-required gates"
    )

    ordered_steps = (
        "Render final release-grade Quality Ledger",
        "Export final release-grade status summary",
        "Materialize final release decision v0",
        "Build and verify final release authority manifest",
        "Verify final Quality Ledger and status parity",
        (
            "Materialize and verify final release authority "
            "artifact binding"
        ),
        "Stage final release authority audit bundle",
        "Release-grade final artifact postconditions",
    )

    positions = [
        job.index(f"      - name: {name}")
        for name in ordered_steps
    ]

    assert enforcement < positions[0]
    assert positions == sorted(positions)


def test_recorded_path_uploads_final_package_inputs() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    for artifact_name in (
        "release-authority-v0",
        "release-authority-audit-bundle",
        "release-authority-artifact-binding-v0",
        "release-decision-v0",
        "pulse-report",
        (
            "release-grade-recorded-path-"
            "${{ github.run_id }}-${{ github.run_attempt }}"
        ),
    ):
        assert artifact_name in job, artifact_name

    for required_path in (
        "release_decision_v0.json",
        "artifact_provenance_binding_v0.json",
        "release_authority_v0.json",
        "report_card.html",
        "recorded_release_evidence_verifier_v0.json",
    ):
        assert required_path in job, required_path


def test_release_path_does_not_introduce_parallel_decision_engines() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    for forbidden in (
        "new_release_decision",
        "parallel_decision",
        "alternate_check_gates",
        "llamaguard_materializer",
        "llamaguard_verifier",
    ):
        assert forbidden not in job, forbidden


def test_downstream_package_dependency_chain_is_preserved() -> None:
    _text, blocks = _workflow_and_jobs()

    package = blocks[PACKAGE_JOB]

    assert _job_field(
        package,
        "needs",
    ) == (
        "[release_grade_recorded_path, "
        "attest_release_grade_artifact_binding]"
    )

    package_guard = _job_field(
        package,
        "if",
    )

    for token in (
        "needs.release_grade_recorded_path.result == 'success'",
        (
            "needs.attest_release_grade_artifact_binding.result "
            "== 'success'"
        ),
    ):
        assert token in package_guard, token

    assert _job_field(
        blocks[VERIFY_JOB],
        "needs",
    ) == PACKAGE_JOB

    assert _job_field(
        blocks["tools-tests"],
        "needs",
    ) == VERIFY_JOB


def test_workflow_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_llamaguard_attested_release_path_wiring_v0.py"
        in manifest
    )


def main() -> int:
    test_release_grade_job_order()
    test_attestation_job_is_hosted_external_model_only()
    test_pre_attestation_artifact_is_uploaded_fail_closed()
    test_recorded_path_downloads_pre_attestation_artifact()
    test_release_grade_candidate_tools_remain_after_attestation()
    test_pre_attestation_final_authority_steps_are_core_only()
    test_recorded_path_restores_attested_evidence_before_verification()
    test_recorded_path_materializes_before_combined_enforcement()
    test_final_authority_artifacts_follow_gate_enforcement()
    test_recorded_path_uploads_final_package_inputs()
    test_release_path_does_not_introduce_parallel_decision_engines()
    test_downstream_package_dependency_chain_is_preserved()
    test_workflow_wiring_smoke_registered()

    print(
        "OK: attested release-grade phase boundary and "
        "final authority wiring locked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
